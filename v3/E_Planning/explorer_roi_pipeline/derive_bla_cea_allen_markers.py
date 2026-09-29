"""Derive BLA/CEA marker scores from local Allen WMB data for a measured panel."""
from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse

TARGET_SUBCLASSES = [
    "014 LA-BLA-BMA-PA Glut",
    "077 CEA-BST Gal Avp Gaba",
    "079 CEA-BST Six3 Cyp26b1 Gaba",
    "080 CEA-AAA-BST Six3 Sp9 Gaba",
    "082 CEA-BST Ebf1 Pdyn Gaba",
    "083 CEA-BST Rai14 Pdyn Crh Gaba",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allen-cache", required=True)
    parser.add_argument("--panel-h5ad", required=True,
                        help="Processed Xenium h5ad whose var_names define measured genes")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--chunk-size", type=int, default=2000)
    args = parser.parse_args()
    cache = Path(args.allen_cache)
    metadata = cache / "metadata" / "WMB-10X" / "20231215" / "views" / "cell_metadata_with_cluster_annotation.csv"
    matrix = cache / "expression_matrices" / "WMB-10Xv3" / "20230630" / "WMB-10Xv3-STR-log2.h5ad"
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    panel = ad.read_h5ad(args.panel_h5ad, backed="r")
    panel_genes = list(map(str, panel.var_names))
    columns = ["cell_label", "feature_matrix_label", "region_of_interest_acronym",
               "subclass", "supertype", "cluster"]
    meta = pd.read_csv(metadata, usecols=columns)
    meta = meta[
        (meta["feature_matrix_label"] == "WMB-10Xv3-STR")
        & meta["subclass"].isin(TARGET_SUBCLASSES)
    ].copy()

    allen = ad.read_h5ad(matrix, backed="r")
    symbols = allen.var["gene_symbol"].astype(str).to_numpy()
    symbol_index = {gene: index for index, gene in enumerate(symbols)}
    genes = [gene for gene in panel_genes if gene in symbol_index]
    gene_columns = np.array([symbol_index[gene] for gene in genes], dtype=int)
    observation_index = pd.Series(np.arange(allen.n_obs), index=allen.obs_names.astype(str))
    rows = observation_index.reindex(meta["cell_label"].astype(str)).dropna().astype(int)
    meta = meta.set_index("cell_label").loc[rows.index]
    order = np.argsort(rows.to_numpy())
    rows = rows.to_numpy()[order]
    meta = meta.iloc[order].copy()

    expression = np.empty((len(rows), len(genes)), dtype=np.float32)
    for start in range(0, len(rows), args.chunk_size):
        selected = rows[start:start + args.chunk_size]
        block = allen[selected, :].to_memory().X[:, gene_columns]
        expression[start:start + len(selected)] = (
            block.toarray() if sparse.issparse(block) else np.asarray(block)
        )

    records = []
    for level in ["subclass", "supertype"]:
        labels = meta[level].astype(str).to_numpy()
        valid_labels = [label for label in sorted(pd.unique(labels)) if np.sum(labels == label) >= 20]
        detection_by_label = {
            label: (expression[labels == label] > 0).mean(axis=0) * 100
            for label in valid_labels
        }
        for label in valid_labels:
            mask = labels == label
            detected = detection_by_label[label]
            mean = expression[mask].mean(axis=0)
            other = [value for key, value in detection_by_label.items() if key != label]
            max_other = np.vstack(other).max(axis=0) if other else np.zeros_like(detected)
            gap = detected - max_other
            for gene, pct, average, difference in zip(genes, detected, mean, gap):
                records.append({
                    "level": level,
                    "label": label,
                    "n_cells": int(mask.sum()),
                    "gene": gene,
                    "pct_detected": float(pct),
                    "mean_log2_expression": float(average),
                    "gap_vs_best_other_pp": float(difference),
                    "marker_score": float(average * max(difference, 0) / 100),
                })
    result = pd.DataFrame(records)
    result.to_csv(output_root / "allen_bla_cea_measured_panel_marker_scores.csv", index=False)
    top = result[
        (result["pct_detected"] >= 20)
        & (result["gap_vs_best_other_pp"] >= 5)
    ].sort_values(
        ["level", "label", "marker_score"], ascending=[True, True, False]
    ).groupby(["level", "label"], observed=True).head(15)
    top.to_csv(output_root / "allen_bla_cea_measured_panel_top_markers.csv", index=False)
    print(f"DONE: {len(meta):,} Allen cells, {len(genes)} measured genes -> {output_root}")


if __name__ == "__main__":
    main()
