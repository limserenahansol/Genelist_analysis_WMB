"""
Enrich mouse_6_region_celltype_GPCR_probe_list workbook using Allen WMB-10X
metadata the same way as the ABC Atlas selection example: cell_label-indexed
tables joinable to expression (see abc_atlas_selection_example notebook).

Default: cluster census per official ROI (no multi-GB h5ad download).
Optional: --compute-th-gpcr runs get_gene_data on TH-only cells (downloads ~4 GB
WMB-10Xv2-TH log2 matrix once) and writes mean log2 expression per cluster_alias.

References:
https://alleninstitute.github.io/abc_atlas_access/notebooks/abc_atlas_selection_example.html
https://alleninstitute.github.io/abc_atlas_access/notebooks/getting_started.html
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(os.environ.get("ABC_ATLAS_CACHE", r"C:\Users\hsollim\Downloads\abc_atlas_cache"))
DEFAULT_INPUT = Path(
    r"C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v6_source_audit.xlsx"
)
DEFAULT_OUTPUT = Path(
    r"C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v7_allen_clusters.xlsx"
)

# Official WMB-10X region_of_interest_acronym values (see region_of_interest_metadata.csv)
ROI_FOR_USER_REGION = {
    "BMAp": ("sAMY", "Striatum-like amygdalar nuclei (WMB ROI; includes BMA-related dissection)"),
    "LM": ("HY", "Hypothalamus (lateral mammillary is inside HY ROI)"),
    "RE": ("TH", "Thalamus (reuniens is midline thalamus)"),
    "CP": ("STRd", "Dorsal striatum (add STRv with --include-strv)"),
    "ORBm": ("PL-ILA-ORB", "Prelimbic / infralimbic / orbital (ORB overlaps)"),
    "AId": ("AI", "Agranular insular area"),
}

USECOLS = [
    "cell_label",
    "dataset_label",
    "feature_matrix_label",
    "region_of_interest_acronym",
    "cluster_alias",
    "neurotransmitter",
    "class",
    "subclass",
    "supertype",
    "cluster",
]


def _local_path(result):
    if isinstance(result, dict):
        return Path(result["local_path"])
    return Path(result)


def extract_gpcr_symbols_from_workbook(xlsx: Path, gene_symbols: set[str]) -> list[str]:
    df = pd.read_excel(xlsx, sheet_name="v6_Final_CellType_GPCR")
    cols = [c for c in df.columns if "gpcr" in c.lower() or "GPCR" in c]
    blob = " ".join(df[c].fillna("").astype(str).str.cat(sep=" ") for c in cols)
    toks = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", blob))
    g = []
    for t in toks:
        if t not in gene_symbols:
            continue
        if len(t) < 3:
            continue
        g.append(t)
    return sorted(set(g))


def build_cluster_census(cell_csv: Path, include_strv: bool) -> pd.DataFrame:
    rois = {t[0] for t in ROI_FOR_USER_REGION.values()}
    if include_strv:
        rois.add("STRv")
    parts: list[pd.DataFrame] = []
    read_kw = dict(
        usecols=USECOLS,
        chunksize=250_000,
        low_memory=False,
    )
    for chunk in pd.read_csv(cell_csv, **read_kw):
        sub = chunk[chunk["region_of_interest_acronym"].isin(rois)]
        if sub.empty:
            continue
        g = (
            sub.groupby(
                ["region_of_interest_acronym", "cluster_alias"],
                as_index=False,
            )
            .agg(
                n_cells=("cell_label", "count"),
                dataset_label=("dataset_label", "first"),
                feature_matrix_label=("feature_matrix_label", "first"),
                neurotransmitter=("neurotransmitter", "first"),
                cls=("class", "first"),
                subclass=("subclass", "first"),
                supertype=("supertype", "first"),
                cluster=("cluster", "first"),
            )
        )
        parts.append(g)
    if not parts:
        return pd.DataFrame()
    all_p = pd.concat(parts, ignore_index=True)
    census = (
        all_p.groupby(
            ["region_of_interest_acronym", "cluster_alias"],
            as_index=False,
        )
        .agg(
            n_cells=("n_cells", "sum"),
            dataset_label=("dataset_label", "first"),
            feature_matrix_label=("feature_matrix_label", "first"),
            neurotransmitter=("neurotransmitter", "first"),
            cls=("cls", "first"),
            subclass=("subclass", "first"),
            supertype=("supertype", "first"),
            cluster=("cluster", "first"),
        )
    )
    census = census.rename(columns={"cls": "class"})
    inv = {v[0]: k for k, v in ROI_FOR_USER_REGION.items()}
    census["user_region_hint"] = census["region_of_interest_acronym"].map(inv)
    return census.sort_values(
        ["region_of_interest_acronym", "n_cells"], ascending=[True, False]
    ).reset_index(drop=True)


def matrix_files_per_roi(census: pd.DataFrame) -> pd.DataFrame:
    """Which expression matrix (h5ad stem) appears in each ROI census."""
    u = (
        census.groupby("region_of_interest_acronym", as_index=False)
        .agg(
            n_cluster_rows=("cluster_alias", "count"),
            feature_matrix_labels=(
                "feature_matrix_label",
                lambda s: "; ".join(sorted(set(s.dropna().astype(str)))),
            ),
        )
        .sort_values("region_of_interest_acronym")
    )
    return u


def merge_taxonomy_labels(census: pd.DataFrame, taxonomy_cluster_csv: Path) -> pd.DataFrame:
    tax = pd.read_csv(taxonomy_cluster_csv)
    tax = tax.rename(
        columns={
            "label": "taxonomy_id",
            "number_of_cells": "taxonomy_cells_atlas_wide",
        }
    )
    out = census.merge(
        tax[["cluster_alias", "taxonomy_id", "taxonomy_cells_atlas_wide"]],
        on="cluster_alias",
        how="left",
    )
    return out


def compute_th_gpcr_cluster_means(
    cell_csv: Path,
    genes: list[str],
    abc_cache,
) -> pd.DataFrame:
    from abc_atlas_access.abc_atlas_cache.anndata_utils import get_gene_data

    usecols = ["cell_label", "dataset_label", "feature_matrix_label", "cluster_alias"]
    rows = []
    for ch in pd.read_csv(
        cell_csv, usecols=usecols, chunksize=300_000, low_memory=False
    ):
        sub = ch[ch["feature_matrix_label"] == "WMB-10Xv2-TH"]
        if not sub.empty:
            rows.append(sub)
    if not rows:
        raise RuntimeError("No cells with feature_matrix_label == WMB-10Xv2-TH")
    th = pd.concat(rows, ignore_index=True)
    th = th.drop_duplicates(subset=["cell_label"])
    all_cells = th.set_index("cell_label")[["dataset_label", "feature_matrix_label"]]
    gene_df = abc_cache.get_metadata_dataframe("WMB-10X", "gene").set_index(
        "gene_identifier"
    )
    expr = get_gene_data(
        abc_cache,
        all_cells,
        gene_df,
        selected_genes=genes,
        data_type="log2",
        chunk_size=4096,
    )
    m = th.set_index("cell_label")["cluster_alias"]
    expr = expr.assign(cluster_alias=m)
    gmean = expr.groupby("cluster_alias", observed=True)[genes].mean().reset_index()
    return gmean


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument(
        "--include-strv",
        action="store_true",
        help="Include STRv ROI rows in census (ventral striatum).",
    )
    ap.add_argument(
        "--compute-th-gpcr",
        action="store_true",
        help="Download WMB-10Xv2-TH log2 h5ad (~4 GB) and add TH demo GPCR matrix.",
    )
    ap.add_argument(
        "--max-gpcr-genes",
        type=int,
        default=45,
        help="Cap number of GPCR symbols passed to get_gene_data (runtime).",
    )
    args = ap.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(args.input)

    from abc_atlas_access.abc_atlas_cache.abc_project_cache import AbcProjectCache

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    abc = AbcProjectCache.from_cache_dir(CACHE_DIR)
    manifest = abc.current_manifest

    cell_path = _local_path(
        abc.get_file_path("WMB-10X", "cell_metadata_with_cluster_annotation")
    )
    tax_cluster = CACHE_DIR / "metadata" / "WMB-taxonomy" / "20231215" / "cluster.csv"
    if not tax_cluster.exists():
        for p in abc.get_directory_metadata("WMB-taxonomy"):
            if p.name == "cluster.csv":
                tax_cluster = p
                break

    print("Building cluster census from:", cell_path)
    census = build_cluster_census(cell_path, include_strv=args.include_strv)
    census = merge_taxonomy_labels(census, tax_cluster)
    matrix_roi = matrix_files_per_roi(census)

    selection_note = pd.DataFrame(
        [
            {
                "step": "1",
                "detail": (
                    "ABC Atlas UI: select cells and export CSV with `Sample Id` "
                    "(= abc_sample_id for MERFISH) or use WMB-10X cell_label in metadata."
                ),
            },
            {
                "step": "2",
                "detail": (
                    "Join exported cells to `cell_metadata` on abc_sample_id "
                    "(see abc_atlas_selection_example notebook)."
                ),
            },
            {
                "step": "3",
                "detail": (
                    "For 10X WMB expression, use get_gene_data() with cells indexed by "
                    "cell_label and gene table indexed by gene_identifier (10x tutorial)."
                ),
            },
        ]
    )

    methodology = pd.DataFrame(
        [
            {
                "topic": "ABC Atlas selection example",
                "detail": (
                    "Official pattern: cell_label + metadata join expression "
                    "(see abc_atlas_selection_example). WMB-10X "
                    "cell_metadata_with_cluster_annotation carries taxonomy fields "
                    "and region_of_interest_acronym per cell."
                ),
            },
            {
                "topic": "Manifest",
                "detail": manifest,
            },
            {
                "topic": "v7 census sheet",
                "detail": (
                    "Aggregated n_cells per (region_of_interest_acronym, cluster_alias) "
                    "for ROIs mapped to your six regions. cluster_alias is the numeric "
                    "cluster ID in the WMB taxonomy."
                ),
            },
            {
                "topic": "GPCR expression",
                "detail": (
                    "Full per-cluster GPCR means across all six ROIs require iterating "
                    "each regional h5ad (multi-GB each). This workbook includes a "
                    "TH-only demo table when you run with --compute-th-gpcr "
                    "(uses WMB-10Xv2-TH log2; RE / thalamus-related clusters in that slice)."
                ),
            },
            {
                "topic": "Notebook URLs",
                "detail": (
                    "https://alleninstitute.github.io/abc_atlas_access/notebooks/"
                    "abc_atlas_selection_example.html ; "
                    "https://alleninstitute.github.io/abc_atlas_access/notebooks/"
                    "general_accessing_10x_snRNASeq_tutorial.html"
                ),
            },
        ]
    )

    roi_legend = pd.DataFrame(
        [
            {"user_region": u, "WMB_ROI_acronym": t[0], "note": t[1]}
            for u, t in ROI_FOR_USER_REGION.items()
        ]
    )

    gpcr_path = _local_path(abc.get_file_path("WMB-10X", "gene"))
    gene_table = pd.read_csv(gpcr_path)
    valid_symbols = set(gene_table["gene_symbol"].astype(str))

    gpcr_genes = extract_gpcr_symbols_from_workbook(args.input, valid_symbols)[
        : args.max_gpcr_genes
    ]

    th_demo = None
    if args.compute_th_gpcr:
        print("Computing TH GPCR cluster means (large download)...")
        th_demo = compute_th_gpcr_cluster_means(cell_path, gpcr_genes, abc)

    summary = pd.DataFrame(
        [
            {"metric": "Census rows (ROI x cluster_alias)", "value": len(census)},
            {"metric": "GPCR symbols (Allen-valid, capped)", "value": len(gpcr_genes)},
            {
                "metric": "TH demo expression",
                "value": "yes" if th_demo is not None else "no (run --compute-th-gpcr)",
            },
        ]
    )

    xl_in = pd.ExcelFile(args.input)
    with pd.ExcelWriter(args.output, engine="openpyxl") as w:
        for sheet in xl_in.sheet_names:
            pd.read_excel(args.input, sheet_name=sheet).to_excel(
                w, sheet_name=sheet, index=False
            )
        methodology.to_excel(w, sheet_name="v7_Allen_Methodology", index=False)
        selection_note.to_excel(w, sheet_name="v7_ABC_Selection_Example_Notes", index=False)
        summary.to_excel(w, sheet_name="v7_Summary", index=False)
        roi_legend.to_excel(w, sheet_name="v7_UserRegion_ROI_map", index=False)
        census.to_excel(w, sheet_name="v7_Allen_Cluster_Census", index=False)
        matrix_roi.to_excel(w, sheet_name="v7_MatrixFiles_per_ROI", index=False)
        pd.DataFrame({"gene_symbol": gpcr_genes}).to_excel(
            w, sheet_name="v7_GPCR_gene_list_used", index=False
        )
        if th_demo is not None:
            th_demo.to_excel(w, sheet_name="v7_TH_GPCR_mean_log2_demo", index=False)

    print("Wrote", args.output)
    print("Census rows:", len(census))
    print("GPCR genes listed for optional expr:", len(gpcr_genes))


if __name__ == "__main__":
    main()
