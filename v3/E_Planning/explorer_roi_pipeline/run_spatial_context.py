"""Optional spatial-context validation for processed Xenium ROIs.

Implements the neighborhood-enrichment and Moran's I checks highlighted in the
10x Python tutorial without making Squidpy a required dependency.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.neighbors import NearestNeighbors

from run_from_explorer import DOTPLOT

HERE = Path(__file__).resolve().parent
SEED = 20260929


def dense(vector):
    return vector.toarray() if sparse.issparse(vector) else np.asarray(vector)


def spatial_edges(xy: np.ndarray, k: int = 6) -> tuple[np.ndarray, np.ndarray]:
    k_use = min(k, len(xy) - 1)
    neighbors = NearestNeighbors(n_neighbors=k_use + 1, algorithm="kd_tree").fit(xy)
    indices = neighbors.kneighbors(xy, return_distance=False)[:, 1:]
    rows = np.repeat(np.arange(len(xy)), k_use)
    graph = sparse.csr_matrix((np.ones(len(rows)), (rows, indices.ravel())), shape=(len(xy), len(xy)))
    graph = graph.maximum(graph.T)
    src, dst = sparse.triu(graph, k=1).nonzero()
    return src.astype(int), dst.astype(int)


def neighborhood_z(labels: np.ndarray, src: np.ndarray, dst: np.ndarray, n_perm: int, rng) -> pd.DataFrame:
    categories = sorted(pd.unique(labels.astype(str)))
    codes = pd.Categorical(labels.astype(str), categories=categories).codes
    n = len(categories)

    def counts(values):
        matrix = np.zeros((n, n), dtype=float)
        np.add.at(matrix, (values[src], values[dst]), 1)
        np.add.at(matrix, (values[dst], values[src]), 1)
        return matrix

    observed = counts(codes)
    permutations = np.empty((n_perm, n, n), dtype=float)
    for index in range(n_perm):
        permutations[index] = counts(rng.permutation(codes))
    mean = permutations.mean(axis=0)
    sd = permutations.std(axis=0, ddof=1)
    z = np.divide(observed - mean, sd, out=np.zeros_like(observed), where=sd > 0)
    return pd.DataFrame(z, index=categories, columns=categories)


def moran_i(values: np.ndarray, src: np.ndarray, dst: np.ndarray) -> float:
    centered = values - np.mean(values)
    denominator = float(np.dot(centered, centered))
    if denominator == 0:
        return np.nan
    numerator = float(np.sum(centered[src] * centered[dst]) * 2)
    weight_sum = float(len(src) * 2)
    return len(values) / weight_sum * numerator / denominator


def process_roi(roi: dict, processed_root: Path, output_root: Path, n_perm: int) -> dict:
    name = roi["roi_name"]
    obj = ad.read_h5ad(processed_root / name / f"{name}_processed.h5ad")
    obs = obj.obs.copy()
    keep = obs["module"].astype(str) != "unassigned"
    obj = obj[keep].copy()
    labels = obj.obs["module"].astype(str).to_numpy()
    xy = obj.obs[["x_centroid", "y_centroid"]].to_numpy(dtype=float)
    src, dst = spatial_edges(xy)
    rng = np.random.default_rng(SEED)
    neighborhood = neighborhood_z(labels, src, dst, n_perm, rng)
    destination = output_root / name
    destination.mkdir(parents=True, exist_ok=True)
    neighborhood.to_csv(destination / "neighborhood_enrichment_z.csv")

    genes = [g for g in DOTPLOT[roi["module_set"]] if g in obj.raw.var_names]
    moran_rows = []
    for gene in genes:
        values = dense(obj.raw[:, gene].X).ravel().astype(float)
        observed = moran_i(values, src, dst)
        null = np.array([moran_i(rng.permutation(values), src, dst) for _ in range(n_perm)])
        p_value = (1 + np.sum(np.abs(null) >= abs(observed))) / (n_perm + 1) if np.isfinite(observed) else np.nan
        moran_rows.append({
            "roi_name": name,
            "anatomy": roi["anatomy"],
            "gene": gene,
            "moran_i": observed,
            "permutation_p_two_sided": p_value,
            "n_permutations": n_perm,
        })
    moran = pd.DataFrame(moran_rows).sort_values("moran_i", ascending=False)
    moran.to_csv(destination / "moran_i_marker_genes.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    vmax = max(2.0, float(np.nanmax(np.abs(neighborhood.to_numpy()))))
    image = axes[0].imshow(neighborhood, cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
    axes[0].set_xticks(range(len(neighborhood.columns)), neighborhood.columns, rotation=45, ha="right")
    axes[0].set_yticks(range(len(neighborhood.index)), neighborhood.index)
    axes[0].set_title("Cell-type neighborhood enrichment")
    fig.colorbar(image, ax=axes[0], label="permutation z-score", shrink=0.8)
    show = moran.head(10).sort_values("moran_i")
    axes[1].barh(show["gene"], show["moran_i"], color="#4C78A8")
    axes[1].axvline(0, color="0.3", linewidth=0.8)
    axes[1].set_xlabel("Moran's I")
    axes[1].set_title("Spatially patterned marker genes")
    fig.suptitle(f"{name}: spatial-context validation (descriptive within section)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(destination / "01_spatial_context_summary.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {
        "roi_name": name,
        "anatomy": roi["anatomy"],
        "n_assigned_cells": int(obj.n_obs),
        "n_cell_types": int(pd.Series(labels).nunique()),
        "max_neighborhood_z": float(np.nanmax(neighborhood.to_numpy())),
        "top_moran_gene": str(moran.iloc[0]["gene"]) if len(moran) else "",
        "top_moran_i": float(moran.iloc[0]["moran_i"]) if len(moran) else np.nan,
        "note": "descriptive within section; animals, not cells or neighbor edges, are biological replicates",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_bla_cea_refined.json"))
    parser.add_argument("--processed-root", default=str(HERE / "outputs_bla_cea_refined"))
    parser.add_argument("--output-root", default=str(HERE / "outputs_bla_cea_refined" / "spatial_context"))
    parser.add_argument("--permutations", type=int, default=199)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    rows = [process_roi(roi, Path(args.processed_root), output_root, args.permutations)
            for roi in config["rois"]]
    pd.DataFrame(rows).to_csv(output_root / "spatial_context_summary.csv", index=False)
    print(f"DONE: {len(rows)} ROIs -> {output_root}")


if __name__ == "__main__":
    main()
