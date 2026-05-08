#!/usr/bin/env python
"""
A05_marker_based_cluster_recall.py

Module A: Marker-based cluster recall for anatomically-broad ROI dissections.

PROBLEM:
    Allen WMB-10X dissects at the ROI level (HY = entire hypothalamus,
    TH = entire thalamus, sAMY = striatum-like amygdalar). For brain regions
    where the user intends a specific subregion (LM = Lateral Mammillary,
    RE = Reuniens, BMAp = Posterior BMA), the closest Allen subclass anchor
    (e.g., 144 MM Foxb1 Glut for LM) covers a transcriptomic class that
    spans the entire mammillary body, not just LM.

SOLUTION:
    Use the user's PAPER-DEFINED markers to recall specific Allen clusters
    that match the marker signature. Within the broad ROI dissection, find
    the clusters whose cells express the paper markers (positive markers)
    and lack the exclusion markers (negative markers) - those are the
    sub-cluster-level anatomical match.

INPUT:
    v3/inputs/curated_marker_template.csv (24 cell types, paper-defined
        marker_genes + exclusion_markers per row).

OUTPUT:
    v3/outputs/marker_recall/MarkerBased_Cluster_Recall.csv
        (every cluster scored against every applicable cell type)
    v3/outputs/marker_recall/MarkerBased_Cluster_Recall_TopN.csv
        (top N clusters per cell type, ranked by net marker score)
    v3/inputs/celltype_to_cluster_anchor.csv
        (auto-generated cluster-level anchor CSV for D02 to consume)

Algorithm per (region_user, cell_type_label):
    1. Get positive markers and negative markers for the cell type.
    2. For each cluster within the user region's ROI dissection:
       a. n_cells_in_cluster = count
       b. mean_pos = mean log2 expression of positive markers across all cells
                     in the cluster (averaged first per marker, then over markers).
       c. mean_neg = same for negative markers.
       d. pct_pos = mean(% cells expressing each positive marker > 0)
       e. pct_neg = mean(% cells expressing each negative marker > 0)
       f. n_pos_above_30 = number of positive markers with pct_expressing >= 30%.
       g. frac_pos_above_30 = n_pos_above_30 / n_positive_markers
       h. net_score = mean_pos - mean_neg + 0.5 * frac_pos_above_30
       i. specificity = mean_pos / (mean_neg + 0.1)
    3. Rank clusters by net_score (descending).
    4. Select top N (default 5) clusters for the auto-generated anchor CSV
       if their net_score is above a configurable threshold.

Restricted to user regions defined in --target_regions (default: LM RE BMAp).
The other regions (CP, ORBm, AId, CA) are not processed because their
Allen ROI dissection is already anatomically narrow enough.
"""
from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_config, open_abc_cache, write_run_log  # noqa: E402


def _detect_gene_symbol_col(gene: pd.DataFrame) -> str:
    for c in ("gene_symbol", "symbol", "gene_name", "name"):
        if c in gene.columns:
            return c
    return gene.columns[0]


def _split_marker_list(s) -> list[str]:
    if pd.isna(s):
        return []
    return [g.strip() for g in str(s).split(",") if g.strip()]


def _get_gene_data_with_retry(cache, all_cells, gene, genes, data_type, chunk_size, retries=8, sleep=20):
    from abc_atlas_access.abc_atlas_cache.anndata_utils import get_gene_data

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            expr = get_gene_data(
                abc_atlas_cache=cache,
                all_cells=all_cells,
                all_genes=gene,
                selected_genes=genes,
                data_type=data_type,
                chunk_size=chunk_size,
            )
            gc.collect()
            return expr
        except PermissionError as e:
            last_err = e
            gc.collect()
            print(f"[WARN] PermissionError attempt {attempt}/{retries}: {e}; sleep {sleep}s")
            time.sleep(sleep)
    raise last_err  # type: ignore[misc]


def _filter_cells_to_target_regions(cell: pd.DataFrame, mapping: pd.DataFrame, target_regions: list[str]) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for _, r in mapping.iterrows():
        region = str(r["region_user"]).strip()
        if region not in target_regions:
            continue
        col = r["allen_region_column"]
        val = str(r["allen_region_value"]).strip()
        if col not in cell.columns or not val:
            print(f"[WARN] mapping row skipped (missing col or empty value): {r.to_dict()}")
            continue
        sub = cell.loc[cell[col].astype(str) == val].copy()
        sub["region_user"] = region
        parts.append(sub)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, axis=0)
    if "cell_label" in out.columns:
        out = out.drop_duplicates(subset=["cell_label"])
    return out


def _score_cluster(
    cluster_expr: pd.DataFrame,
    pos_markers: list[str],
    neg_markers: list[str],
) -> dict[str, float]:
    """Return marker-signature stats for one cluster.

    cluster_expr is a DataFrame whose columns are (a subset of) all_genes in
    log2(CPM) space and whose rows are cells in the cluster.
    """
    pos_present = [g for g in pos_markers if g in cluster_expr.columns]
    neg_present = [g for g in neg_markers if g in cluster_expr.columns]

    if pos_present:
        pos_mean_per_gene = cluster_expr[pos_present].mean(axis=0).to_numpy()
        pos_pct_per_gene = (cluster_expr[pos_present] > 0).mean(axis=0).to_numpy() * 100.0
        mean_pos = float(np.nanmean(pos_mean_per_gene))
        pct_pos = float(np.nanmean(pos_pct_per_gene))
        n_pos_above_30 = int(np.sum(pos_pct_per_gene >= 30.0))
        frac_pos_above_30 = n_pos_above_30 / max(1, len(pos_present))
    else:
        mean_pos = 0.0
        pct_pos = 0.0
        n_pos_above_30 = 0
        frac_pos_above_30 = 0.0

    if neg_present:
        neg_mean_per_gene = cluster_expr[neg_present].mean(axis=0).to_numpy()
        neg_pct_per_gene = (cluster_expr[neg_present] > 0).mean(axis=0).to_numpy() * 100.0
        mean_neg = float(np.nanmean(neg_mean_per_gene))
        pct_neg = float(np.nanmean(neg_pct_per_gene))
    else:
        mean_neg = 0.0
        pct_neg = 0.0

    net_score = mean_pos - mean_neg + 0.5 * frac_pos_above_30
    specificity = mean_pos / (mean_neg + 0.1)

    return {
        "n_pos_markers_total": len(pos_markers),
        "n_pos_markers_in_data": len(pos_present),
        "n_neg_markers_in_data": len(neg_present),
        "mean_pos_log2": round(mean_pos, 4),
        "mean_neg_log2": round(mean_neg, 4),
        "pct_pos_avg": round(pct_pos, 2),
        "pct_neg_avg": round(pct_neg, 2),
        "n_pos_above_30pct": n_pos_above_30,
        "frac_pos_above_30pct": round(frac_pos_above_30, 3),
        "net_score": round(net_score, 4),
        "specificity": round(specificity, 4),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None)
    p.add_argument("--out_dir", required=True, help="Output directory")
    p.add_argument("--marker_csv", required=True, help="curated_marker_template.csv")
    p.add_argument("--anchor_csv", required=True, help="celltype_to_subclass_anchor.csv (to read role column)")
    p.add_argument("--region_mapping_csv", required=True, help="Region_Mapping_Auto_Draft.csv")
    p.add_argument("--target_regions", nargs="+", default=["LM", "RE", "BMAp"])
    p.add_argument("--top_n", type=int, default=5, help="Top N clusters per cell type")
    p.add_argument("--min_cells_per_cluster", type=int, default=10)
    p.add_argument("--min_net_score_for_anchor", type=float, default=0.5,
                   help="Minimum net_score to include cluster in auto-generated anchor CSV")
    p.add_argument("--cluster_anchor_out", required=True,
                   help="Where to write the auto-generated cluster-level anchor CSV")
    args = p.parse_args()

    cfg = load_config(args.config)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = open_abc_cache(cfg)

    print(f"[INFO] target regions: {args.target_regions}")
    markers = pd.read_csv(args.marker_csv)
    markers = markers[markers["region_user"].isin(args.target_regions)].copy()
    print(f"[INFO] cell types to recall: {len(markers)} (regions: {markers['region_user'].unique().tolist()})")

    anchors = pd.read_csv(args.anchor_csv)
    role_lookup: dict[tuple[str, str], str] = {}
    for _, r in anchors.iterrows():
        key = (str(r["region_user"]).strip(), str(r["cell_type_label"]).strip())
        role_lookup.setdefault(key, str(r.get("role", "target") or "target").lower())

    all_marker_genes: set[str] = set()
    for _, r in markers.iterrows():
        all_marker_genes.update(_split_marker_list(r.get("marker_genes")))
        all_marker_genes.update(_split_marker_list(r.get("exclusion_markers")))
    print(f"[INFO] unique marker genes to query: {len(all_marker_genes)}")

    print("[INFO] loading WMB-10X cell metadata + gene metadata")
    cell = cache.get_metadata_dataframe("WMB-10X", "cell_metadata_with_cluster_annotation")
    gene = cache.get_metadata_dataframe("WMB-10X", "gene")
    if "cell_label" in cell.columns:
        cell = cell.set_index("cell_label", drop=False)

    gene_symbol_col = _detect_gene_symbol_col(gene)
    available = set(gene[gene_symbol_col].dropna().astype(str).str.strip())
    genes = sorted([g for g in all_marker_genes if g in available])
    missing = sorted([g for g in all_marker_genes if g not in available])
    print(f"[INFO] marker genes present in Allen: {len(genes)}; missing: {len(missing)} {missing}")

    mapping = pd.read_csv(args.region_mapping_csv)
    cell_sub = _filter_cells_to_target_regions(cell, mapping, args.target_regions)
    if cell_sub.empty:
        raise SystemExit(f"[ERROR] No cells matched target regions {args.target_regions}")
    print(f"[INFO] cells in target regions: {len(cell_sub)}")
    print(cell_sub.groupby("region_user").size().to_string())

    print("[INFO] loading expression for marker genes (this may take a few minutes)")
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
    print(f"[INFO] expression matrix shape: {expr.shape}")

    joined = cell_sub.join(expr, how="left")

    # group key per cluster
    cluster_col = "cluster"
    if cluster_col not in joined.columns:
        raise SystemExit(f"[ERROR] expected column '{cluster_col}' in cell metadata; got {list(joined.columns)[:30]}")

    print("[INFO] scoring clusters per cell type")
    rows: list[dict] = []
    for _, ct_row in tqdm(markers.iterrows(), total=len(markers), desc="cell types"):
        region = str(ct_row["region_user"]).strip()
        cell_type = str(ct_row["cell_type_label"]).strip()
        pos_markers = _split_marker_list(ct_row.get("marker_genes"))
        neg_markers = _split_marker_list(ct_row.get("exclusion_markers"))
        role = role_lookup.get((region, cell_type), "target")

        region_cells = joined[joined["region_user"] == region]
        if region_cells.empty:
            continue

        for cluster_id, cluster_cells in region_cells.groupby(cluster_col, observed=True):
            n = len(cluster_cells)
            if n < args.min_cells_per_cluster:
                continue
            cluster_expr = cluster_cells[[c for c in cluster_cells.columns if c in genes]]
            scores = _score_cluster(cluster_expr, pos_markers, neg_markers)
            subclass_val = ""
            supertype_val = ""
            if "subclass" in cluster_cells.columns:
                subclass_val = str(cluster_cells["subclass"].iloc[0])
            if "supertype" in cluster_cells.columns:
                supertype_val = str(cluster_cells["supertype"].iloc[0])
            rows.append(
                {
                    "region_user": region,
                    "cell_type_label": cell_type,
                    "role": role,
                    "cluster": str(cluster_id),
                    "subclass": subclass_val,
                    "supertype": supertype_val,
                    "n_cells_in_cluster": n,
                    **scores,
                }
            )

    df_all = pd.DataFrame(rows)
    if df_all.empty:
        raise SystemExit("[ERROR] No cluster-level scores produced.")

    # rank within (region_user, cell_type_label)
    df_all = df_all.sort_values(
        ["region_user", "cell_type_label", "net_score"],
        ascending=[True, True, False],
    )
    df_all["rank_within_celltype"] = df_all.groupby(
        ["region_user", "cell_type_label"], observed=True
    )["net_score"].rank(method="dense", ascending=False).astype(int)

    full_path = out / "MarkerBased_Cluster_Recall.csv"
    df_all.to_csv(full_path, index=False)
    print(f"[OK] full recall table: {full_path}  rows={len(df_all)}")

    top_n = df_all[df_all["rank_within_celltype"] <= args.top_n].copy()
    top_path = out / "MarkerBased_Cluster_Recall_TopN.csv"
    top_n.to_csv(top_path, index=False)
    print(f"[OK] top-{args.top_n} recall table: {top_path}  rows={len(top_n)}")

    # Auto-generate cluster-level anchor CSV (filtered by min_net_score)
    accepted = top_n[top_n["net_score"] >= args.min_net_score_for_anchor].copy()
    anchor_rows: list[dict] = []
    for (region, ct, role), grp in accepted.groupby(
        ["region_user", "cell_type_label", "role"], observed=True
    ):
        for _, r in grp.iterrows():
            confidence = "high" if r["frac_pos_above_30pct"] >= 0.6 else "medium"
            note_parts = [
                f"marker-recall rank {int(r['rank_within_celltype'])}",
                f"net_score={r['net_score']:.2f}",
                f"{int(r['n_pos_above_30pct'])}/{int(r['n_pos_markers_in_data'])} pos markers >=30%",
            ]
            anchor_rows.append(
                {
                    "region_user": region,
                    "cell_type_label": ct,
                    "allen_cluster_anchor": r["cluster"],
                    "allen_subclass_of_cluster": r["subclass"],
                    "n_cells": int(r["n_cells_in_cluster"]),
                    "confidence": confidence,
                    "role": role,
                    "marker_recall_net_score": r["net_score"],
                    "marker_recall_pct_pos_avg": r["pct_pos_avg"],
                    "marker_recall_pct_neg_avg": r["pct_neg_avg"],
                    "notes": "; ".join(note_parts),
                }
            )

    cluster_anchor_df = pd.DataFrame(anchor_rows)
    cluster_anchor_path = Path(args.cluster_anchor_out)
    cluster_anchor_path.parent.mkdir(parents=True, exist_ok=True)
    cluster_anchor_df.to_csv(cluster_anchor_path, index=False)
    print(f"[OK] auto-generated cluster anchor CSV: {cluster_anchor_path}  rows={len(cluster_anchor_df)}")

    write_run_log(
        out,
        "A05_marker_based_cluster_recall",
        {
            "manifest_version": cfg.manifest_version,
            "target_regions": args.target_regions,
            "n_cell_types": int(len(markers)),
            "n_marker_genes": len(genes),
            "missing_markers": missing,
            "n_cells": int(len(cell_sub)),
            "n_clusters_scored": int(df_all[["region_user", "cluster"]].drop_duplicates().shape[0]),
            "n_anchor_rows_after_filter": int(len(cluster_anchor_df)),
            "min_cells_per_cluster": args.min_cells_per_cluster,
            "min_net_score_for_anchor": args.min_net_score_for_anchor,
            "top_n": args.top_n,
        },
    )
    print("[DONE] A05 complete")


if __name__ == "__main__":
    main()
