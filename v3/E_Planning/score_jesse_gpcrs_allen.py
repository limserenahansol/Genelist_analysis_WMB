"""Score Jesse ORB-high GPCRs in Allen WMB-10X ORBm (absolute % expressing)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

V3 = Path(__file__).resolve().parents[1]
if str(V3) not in sys.path:
    sys.path.insert(0, str(V3))

from A_Allen_only_computational_module.A06_subclass_discriminating_markers import (  # noqa: E402
    _detect_gene_symbol_col,
    _filter_cells,
    _get_gene_data_with_retry,
    compute_subclass_stats,
)
from common.config import load_config, open_abc_cache  # noqa: E402

GENES = [
    "Mas1",
    "Gpr68",
    "Mchr1",
    "Chrm1",
    "Grm8",
    "Gpr26",
    "Cckbr",
    "Hcrtr2",
    "Rxfp1",
    "Camk2g",
    "Fxr1",
    "Vps13a",
]
ORBM_ANCHORS = [
    "004 L6 IT CTX Glut",
    "005 L5 IT CTX Glut",
    "006 L4/5 IT CTX Glut",
    "007 L2/3 IT CTX Glut",
    "022 L5 ET CTX Glut",
    "029 L6b CTX Glut",
    "030 L6 CT CTX Glut",
    "032 L5 NP CTX Glut",
    "046 Vip Gaba",
    "049 Lamp5 Gaba",
    "052 Pvalb Gaba",
    "053 Sst Gaba",
]


def main() -> None:
    cfg = load_config()
    out = V3 / "outputs" / "jesse_allen_gpcr_abundance"
    out.mkdir(parents=True, exist_ok=True)
    cache = open_abc_cache(cfg)

    print("[INFO] loading cell + gene metadata")
    cell = cache.get_metadata_dataframe("WMB-10X", "cell_metadata_with_cluster_annotation")
    gene = cache.get_metadata_dataframe("WMB-10X", "gene")
    if "cell_label" in cell.columns:
        cell = cell.set_index("cell_label", drop=False)
    gsym = _detect_gene_symbol_col(gene)
    available = set(gene[gsym].dropna().astype(str).str.strip())
    genes = [g for g in GENES if g in available]
    missing = [g for g in GENES if g not in available]
    print("[INFO] in Allen gene table:", genes)
    print("[INFO] missing from gene table:", missing)

    mapping = pd.read_csv(V3 / "outputs/region_mapping/Region_Mapping_Auto_Draft.csv")
    cell_sub = _filter_cells(cell, mapping, ["ORBm"])
    print(f"[INFO] ORBm cells: {len(cell_sub)}")
    print(cell_sub.groupby("region_user").size().to_string())

    print("[INFO] pulling expression for", len(genes), "genes")
    expr = _get_gene_data_with_retry(
        cache=cache,
        all_cells=cell_sub,
        gene=gene,
        genes=genes,
        data_type=cfg.expression_data_type,
        chunk_size=cfg.chunk_size,
    )
    if not isinstance(expr, pd.DataFrame):
        expr = pd.DataFrame(expr)
    print("[INFO] expr", expr.shape, list(expr.columns))
    joined = cell_sub.join(expr, how="left")

    stats = compute_subclass_stats(joined, genes, min_cells=30)
    stats["is_orbm_anchor"] = stats["subclass"].isin(ORBM_ANCHORS)
    long_path = out / "Jesse_GPCR_Allen_ORBm_long.csv"
    stats.to_csv(long_path, index=False)
    print("[OK]", long_path, "rows", len(stats))

    anc = stats[stats["is_orbm_anchor"]].copy()
    rows = []
    for g in genes:
        d = anc[anc.gene == g]
        if d.empty:
            rows.append({"gene": g, "status": "no_anchor_rows"})
            continue
        top = d.sort_values("pct_expr", ascending=False).iloc[0]
        rows.append(
            {
                "gene": g,
                "n_anchors": int(d.subclass.nunique()),
                "n_anchors_pct_ge_5": int((d.pct_expr >= 5).sum()),
                "n_anchors_pct_ge_20": int((d.pct_expr >= 20).sum()),
                "n_anchors_pct_ge_50": int((d.pct_expr >= 50).sum()),
                "max_pct": float(d.pct_expr.max()),
                "max_pct_subclass": top["subclass"],
                "max_mean_log2": float(d.mean_log2_expr.max()),
                "median_pct": float(d.pct_expr.median()),
                "mean_pct_across_anchors": float(d.pct_expr.mean()),
            }
        )
    summary = pd.DataFrame(rows)
    sum_path = out / "Jesse_GPCR_Allen_ORBm_summary.csv"
    summary.to_csv(sum_path, index=False)
    print(summary.to_string(index=False))
    print("[OK]", sum_path)

    pivot = anc.pivot_table(index="subclass", columns="gene", values="pct_expr")
    pivot = pivot.reindex(ORBM_ANCHORS)
    pivot_path = out / "Jesse_GPCR_Allen_ORBm_anchor_pct.csv"
    pivot.to_csv(pivot_path)
    print("[OK]", pivot_path)
    print(pivot.round(1).to_string())


if __name__ == "__main__":
    main()
