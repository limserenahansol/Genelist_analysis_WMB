"""
Compute Allen WMB log2 GPCR expression and within-group rankings for cells in
the six-region ROI set, then patch the v6 audit workbook (with backup).

Ranks:
  - rank_in_cluster: among GPCR genes, rank by mean log2 within each
    (region_of_interest_acronym, cluster_alias).
  - rank_in_subclass_roi: same, pooled within (ROI, Allen subclass string).

Does not map free-text v6 rows to clusters; use subclass/cluster tables to
interpret which GPCRs dominate each Allen population.
"""
from __future__ import annotations

import argparse
import gc
import os
import re
import shutil
import time
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(os.environ.get("ABC_ATLAS_CACHE", r"C:\Users\hsollim\Downloads\abc_atlas_cache"))
DEFAULT_XLSX = Path(
    r"C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v6_source_audit.xlsx"
)

ROI_SET = frozenset({"sAMY", "HY", "TH", "STRd", "STRv", "PL-ILA-ORB", "AI"})
CELL_COLS = [
    "cell_label",
    "dataset_label",
    "feature_matrix_label",
    "region_of_interest_acronym",
    "cluster_alias",
    "subclass",
    "supertype",
    "class",
]


def _local_path(result):
    if isinstance(result, dict):
        return Path(result["local_path"])
    return Path(result)


def load_roi_cells(cell_csv: Path) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for ch in pd.read_csv(
        cell_csv,
        usecols=CELL_COLS,
        chunksize=400_000,
        low_memory=False,
    ):
        s = ch[ch["region_of_interest_acronym"].isin(ROI_SET)]
        if not s.empty:
            parts.append(s)
    if not parts:
        raise RuntimeError("No cells in ROI set")
    out = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["cell_label"])
    return out


def extract_gpcr_genes(xlsx: Path, valid: set[str]) -> list[str]:
    df = pd.read_excel(xlsx, sheet_name="v6_Final_CellType_GPCR")
    cols = [c for c in df.columns if "gpcr" in c.lower() or "GPCR" in c]
    blob = " ".join(df[c].fillna("").astype(str).str.cat(sep=" ") for c in cols)
    toks = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", blob))
    g = sorted(t for t in toks if t in valid and len(t) >= 3)
    return g


def pull_expression_for_matrix(
    abc, gene_df: pd.DataFrame, genes: list[str], cells_frame: pd.DataFrame
) -> pd.DataFrame:
    from abc_atlas_access.abc_atlas_cache.anndata_utils import get_gene_data

    all_cells = cells_frame.set_index("cell_label")[
        ["dataset_label", "feature_matrix_label"]
    ]
    last_err: Exception | None = None
    for attempt in range(1, 13):
        try:
            expr = get_gene_data(
                abc,
                all_cells,
                gene_df,
                selected_genes=genes,
                data_type="log2",
                chunk_size=4096,
            )
            break
        except PermissionError as e:
            last_err = e
            gc.collect()
            print(
                f"  PermissionError (file lock?), retry {attempt}/12 in 30s: {e}"
            )
            time.sleep(30)
    else:
        raise last_err  # type: ignore[misc]

    gc.collect()
    meta = cells_frame.set_index("cell_label")
    joined = expr.join(
        meta[
            [
                "region_of_interest_acronym",
                "cluster_alias",
                "subclass",
                "supertype",
                "class",
            ]
        ],
        how="inner",
    )
    return joined


def means_and_ranks(
    full: pd.DataFrame, genes: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    gcols = [c for c in genes if c in full.columns]
    if not gcols:
        raise RuntimeError("No GPCR columns in expression frame")

    # cluster level
    cg = full.groupby(
        ["region_of_interest_acronym", "cluster_alias"], observed=True
    )[gcols].mean()
    rk_c = cg.rank(axis=1, ascending=False, method="min")
    mean_c = cg.reset_index().melt(
        id_vars=["region_of_interest_acronym", "cluster_alias"],
        var_name="gene_symbol",
        value_name="mean_log2",
    )
    rank_c = rk_c.reset_index().melt(
        id_vars=["region_of_interest_acronym", "cluster_alias"],
        var_name="gene_symbol",
        value_name="rank_high_to_low_in_cluster",
    )
    cluster_long = mean_c.merge(
        rank_c,
        on=["region_of_interest_acronym", "cluster_alias", "gene_symbol"],
    )

    # subclass within ROI
    sg = full.groupby(
        ["region_of_interest_acronym", "subclass"], observed=True
    )[gcols].mean()
    rk_s = sg.rank(axis=1, ascending=False, method="min")
    mean_s = sg.reset_index().melt(
        id_vars=["region_of_interest_acronym", "subclass"],
        var_name="gene_symbol",
        value_name="mean_log2",
    )
    rank_s = rk_s.reset_index().melt(
        id_vars=["region_of_interest_acronym", "subclass"],
        var_name="gene_symbol",
        value_name="rank_high_to_low_in_subclass",
    )
    subclass_long = mean_s.merge(
        rank_s,
        on=["region_of_interest_acronym", "subclass", "gene_symbol"],
    )

    # compact: top 5 GPCRs per cluster
    top_c = (
        cluster_long.sort_values(
            ["region_of_interest_acronym", "cluster_alias", "rank_high_to_low_in_cluster"]
        )
        .groupby(["region_of_interest_acronym", "cluster_alias"], group_keys=False)
        .head(5)
    )

    top_s = (
        subclass_long.sort_values(
            ["region_of_interest_acronym", "subclass", "rank_high_to_low_in_subclass"]
        )
        .groupby(["region_of_interest_acronym", "subclass"], group_keys=False)
        .head(5)
    )

    return cluster_long, subclass_long, top_c, top_s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX, help="Input workbook (read-only if --output set)")
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write merged workbook here. Recommended if Excel may lock the input file. "
        "If omitted, results are written back to --xlsx (in-place).",
    )
    ap.add_argument("--max-genes", type=int, default=0, help="0 = all valid GPCRs from sheet")
    args = ap.parse_args()

    if not args.xlsx.exists():
        raise FileNotFoundError(args.xlsx)

    out_path = args.output if args.output is not None else args.xlsx
    in_place = args.output is None or args.output.resolve() == args.xlsx.resolve()

    from abc_atlas_access.abc_atlas_cache.abc_project_cache import AbcProjectCache

    if in_place:
        backup = args.xlsx.with_suffix(".pre_gpcr_compute_backup.xlsx")
        if not backup.exists():
            shutil.copy2(args.xlsx, backup)
            print("Backup:", backup)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        print("Output file (separate from input):", out_path)

    abc = AbcProjectCache.from_cache_dir(CACHE_DIR)
    cell_path = _local_path(
        abc.get_file_path("WMB-10X", "cell_metadata_with_cluster_annotation")
    )
    gene_df = abc.get_metadata_dataframe("WMB-10X", "gene").set_index("gene_identifier")
    valid = set(gene_df["gene_symbol"].astype(str))

    genes = extract_gpcr_genes(args.xlsx, valid)
    if args.max_genes > 0:
        genes = genes[: args.max_genes]
    print("GPCR genes:", len(genes))

    cells = load_roi_cells(cell_path)
    print("Cells in ROI union:", len(cells))

    matrices = cells["feature_matrix_label"].dropna().unique().tolist()
    print("Matrices to load:", len(matrices))

    parts: list[pd.DataFrame] = []
    for m in sorted(matrices):
        sub = cells[cells["feature_matrix_label"] == m]
        if sub.empty:
            continue
        print("Matrix", m, "cells", len(sub))
        parts.append(pull_expression_for_matrix(abc, gene_df, genes, sub))
        gc.collect()
        time.sleep(8)

    full = pd.concat(parts, axis=0)
    print("Joined expression rows:", len(full))

    cluster_long, subclass_long, top_c, top_s = means_and_ranks(full, genes)

    note = pd.DataFrame(
        [
            {
                "item": "Data",
                "detail": "Allen WMB-10X log2 expression; AbcProjectCache get_gene_data.",
            },
            {
                "item": "rank_high_to_low_in_cluster",
                "detail": "1 = highest mean log2 among listed GPCRs in that ROI x cluster_alias.",
            },
            {
                "item": "rank_high_to_low_in_subclass",
                "detail": "1 = highest among GPCRs pooled across cells in that ROI x Allen subclass.",
            },
            {
                "item": "v6_Final_CellType_GPCR",
                "detail": (
                    "Curated free-text populations are not auto-linked to cluster_alias; "
                    "use subclass/cluster tables to relate biology to ranks."
                ),
            },
        ]
    )

    xl = pd.ExcelFile(args.xlsx)
    out_sheets: dict[str, pd.DataFrame] = {}
    for sheet in xl.sheet_names:
        if sheet.startswith("Computed_GPCR"):
            continue
        out_sheets[sheet] = pd.read_excel(args.xlsx, sheet_name=sheet)
    v6 = out_sheets["v6_Final_CellType_GPCR"]
    v6["GPCR_Allen_ranking_sheets"] = (
        "Computed_GPCR_rank_note; Computed_GPCR_cluster_long; "
        "Computed_GPCR_subclass_long; Computed_GPCR_top5_per_cluster; "
        "Computed_GPCR_top5_per_subclass"
    )
    out_sheets["v6_Final_CellType_GPCR"] = v6

    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        for name, df in out_sheets.items():
            df.to_excel(w, sheet_name=name, index=False)

        note.to_excel(w, sheet_name="Computed_GPCR_rank_note", index=False)
        cluster_long.to_excel(w, sheet_name="Computed_GPCR_cluster_long", index=False)
        subclass_long.to_excel(w, sheet_name="Computed_GPCR_subclass_long", index=False)
        top_c.to_excel(w, sheet_name="Computed_GPCR_top5_per_cluster", index=False)
        top_s.to_excel(w, sheet_name="Computed_GPCR_top5_per_subclass", index=False)

    print("Updated:", out_path)


if __name__ == "__main__":
    main()
