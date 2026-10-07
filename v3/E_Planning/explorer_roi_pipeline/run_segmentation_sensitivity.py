"""Check whether key ROI results survive a nucleus-only transcript analysis.

This is a sensitivity analysis for nucleus-expansion segmentation. It leaves the
primary cell segmentation untouched and reads raw Xenium outputs non-destructively.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import scanpy as sc
from scipy import sparse
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from run_from_explorer import (
    LEIDEN_RES,
    MODULES,
    N_NEIGHBORS,
    N_PCS,
    SEED,
    STATE_REPORTER_GENES,
    module_scores,
    run_leiden,
    savefig,
)

HERE = Path(__file__).resolve().parent


def dense(x):
    return x.toarray() if sparse.issparse(x) else np.asarray(x)


def correlation(x, y) -> float | None:
    value = spearmanr(np.asarray(x), np.asarray(y), nan_policy="omit").statistic
    return None if not np.isfinite(value) else float(value)


def aggregate_transcripts(
    transcript_path: Path, cell_ids: list[str], genes: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return all assigned-gene and nucleus-overlapping count matrices."""
    dataset = ds.dataset(str(transcript_path), format="parquet")
    filt = ds.field("is_gene") == True  # noqa: E712 - pyarrow expression
    # The cell-feature matrix contains high-quality decoded transcripts (QV >= 20).
    # Apply the same threshold before validating reconstruction or nuclear overlap.
    filt = filt & (ds.field("qv") >= 20)
    filt = filt & ds.field("cell_id").isin(cell_ids)
    table = dataset.to_table(
        columns=["cell_id", "feature_name", "overlaps_nucleus"],
        filter=filt,
    ).to_pandas()
    table["cell_id"] = table["cell_id"].astype(str)
    table["feature_name"] = table["feature_name"].astype(str)
    table = table[table["feature_name"].isin(genes)].copy()

    def pivot(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(0, index=cell_ids, columns=genes, dtype=np.int32)
        counts = frame.groupby(["cell_id", "feature_name"], observed=True).size()
        return (
            counts.unstack(fill_value=0)
            .reindex(index=cell_ids, columns=genes, fill_value=0)
            .astype(np.int32)
        )

    all_counts = pivot(table)
    nucleus_counts = pivot(table[table["overlaps_nucleus"].astype(int) == 1])
    return all_counts, nucleus_counts


def nucleus_only_labels(
    counts: pd.DataFrame,
    obs: pd.DataFrame,
    module_set: str,
) -> tuple[pd.Series, pd.Series]:
    """Create marker-module calls and identity-only Leiden labels."""
    obj = ad.AnnData(
        X=sparse.csr_matrix(counts.to_numpy(dtype=np.float32)),
        obs=obs.copy(),
    )
    obj.var_names = counts.columns.astype(str)
    obj.layers["counts"] = obj.X.copy()
    sc.pp.filter_genes(obj, min_cells=3)
    sc.pp.normalize_total(obj, target_sum=1e4)
    sc.pp.log1p(obj)
    _, modules = module_scores(obj, MODULES[module_set])
    module_labels = pd.Series(modules.to_numpy(), index=obj.obs_names, name="nucleus_module")

    obj.raw = obj
    if sparse.issparse(obj.X):
        obj.X = obj.X.toarray()
    sc.pp.scale(obj, max_value=10)
    identity_mask = np.array([
        str(g).lower() not in STATE_REPORTER_GENES for g in obj.var_names
    ])
    if obj.n_obs < 20 or identity_mask.sum() < 10:
        return module_labels, pd.Series(dtype=str, name="nucleus_leiden")
    obj.X[:, ~identity_mask] = 0.0
    n_pcs = min(N_PCS, obj.n_obs - 2, int(identity_mask.sum()) - 1)
    n_neighbors = min(N_NEIGHBORS, obj.n_obs - 1)
    sc.tl.pca(obj, n_comps=n_pcs, svd_solver="arpack", random_state=SEED)
    sc.pp.neighbors(obj, n_neighbors=n_neighbors, n_pcs=n_pcs, random_state=SEED)
    run_leiden(obj, LEIDEN_RES, "nucleus_leiden")
    cluster_labels = obj.obs["nucleus_leiden"].astype(str).copy()
    return module_labels, cluster_labels


def process_roi(
    roi: dict,
    processed_root: Path,
    output_root: Path,
    min_counts: int,
    min_genes: int,
) -> dict:
    name = roi["roi_name"]
    source = processed_root / name / f"{name}_processed.h5ad"
    obj = ad.read_h5ad(source)
    cell_ids = obj.obs_names.astype(str).tolist()
    genes = obj.var_names.astype(str).tolist()
    matrix_counts = pd.DataFrame(
        dense(obj.layers["counts"]), index=cell_ids, columns=genes
    )
    all_tx, nuclear = aggregate_transcripts(
        Path(roi["xenium"]) / "transcripts.parquet", cell_ids, genes
    )
    reconstruction_difference = all_tx.to_numpy(dtype=float) - matrix_counts.to_numpy(dtype=float)
    n_reconstruction_mismatches = int(np.count_nonzero(reconstruction_difference))
    max_reconstruction_abs_difference = float(
        np.max(np.abs(reconstruction_difference))
    )
    if n_reconstruction_mismatches:
        raise ValueError(
            f"{name}: QV>=20 transcript reconstruction differs from the cell-feature "
            f"matrix at {n_reconstruction_mismatches} cell-gene entries "
            f"(max absolute difference {max_reconstruction_abs_difference})"
        )

    matrix_totals = matrix_counts.sum(axis=1)
    reconstructed_totals = all_tx.sum(axis=1)
    nuclear_totals = nuclear.sum(axis=1)
    nuclear_genes = (nuclear > 0).sum(axis=1)
    same_qc = (nuclear_totals >= min_counts) & (nuclear_genes >= min_genes)

    per_cell = pd.DataFrame({
        "cell_id": cell_ids,
        "matrix_gene_counts": matrix_totals.to_numpy(),
        "transcript_parquet_gene_counts": reconstructed_totals.to_numpy(),
        "nucleus_only_gene_counts": nuclear_totals.to_numpy(),
        "nucleus_only_genes_detected": nuclear_genes.to_numpy(),
        "nuclear_fraction": np.divide(
            nuclear_totals.to_numpy(),
            reconstructed_totals.to_numpy(),
            out=np.zeros(len(cell_ids), dtype=float),
            where=reconstructed_totals.to_numpy() > 0,
        ),
        "passes_same_qc_nucleus_only": same_qc.to_numpy(),
        "full_leiden": obj.obs["leiden"].astype(str).to_numpy(),
        "full_module": obj.obs["module"].astype(str).to_numpy(),
    }).set_index("cell_id")

    gene_all_mean = all_tx.mean(axis=0)
    gene_nuclear_mean = nuclear.mean(axis=0)
    per_gene = pd.DataFrame({
        "gene": genes,
        "all_assigned_mean_per_cell": gene_all_mean.to_numpy(),
        "nucleus_only_mean_per_cell": gene_nuclear_mean.to_numpy(),
        "all_assigned_detection_fraction": (all_tx > 0).mean(axis=0).to_numpy(),
        "nucleus_only_detection_fraction": (nuclear > 0).mean(axis=0).to_numpy(),
    })
    per_gene["nuclear_fraction"] = np.divide(
        per_gene["nucleus_only_mean_per_cell"],
        per_gene["all_assigned_mean_per_cell"],
        out=np.zeros(len(per_gene), dtype=float),
        where=per_gene["all_assigned_mean_per_cell"] > 0,
    )

    module_agreement = module_nmi = cluster_ari = cluster_nmi = None
    kept_ids = per_cell.index[per_cell["passes_same_qc_nucleus_only"]].tolist()
    if len(kept_ids) >= 20:
        nucleus_modules, nucleus_clusters = nucleus_only_labels(
            nuclear.loc[kept_ids], obj.obs.loc[kept_ids], roi["module_set"]
        )
        per_cell.loc[nucleus_modules.index, "nucleus_module"] = nucleus_modules
        module_agreement = float(
            np.mean(
                per_cell.loc[nucleus_modules.index, "full_module"].astype(str).to_numpy()
                == nucleus_modules.astype(str).to_numpy()
            )
        )
        module_nmi = float(normalized_mutual_info_score(
            per_cell.loc[nucleus_modules.index, "full_module"].astype(str),
            nucleus_modules.astype(str),
        ))
        if len(nucleus_clusters):
            per_cell.loc[nucleus_clusters.index, "nucleus_leiden"] = nucleus_clusters
            cluster_ari = float(adjusted_rand_score(
                per_cell.loc[nucleus_clusters.index, "full_leiden"].astype(str),
                nucleus_clusters.astype(str),
            ))
            cluster_nmi = float(normalized_mutual_info_score(
                per_cell.loc[nucleus_clusters.index, "full_leiden"].astype(str),
                nucleus_clusters.astype(str),
            ))

    output = output_root / name
    output.mkdir(parents=True, exist_ok=True)
    per_cell.to_csv(output / "nucleus_only_per_cell.csv")
    per_gene.to_csv(output / "nucleus_only_per_gene.csv", index=False)

    cell_rho = correlation(matrix_totals, nuclear_totals)
    gene_rho = correlation(gene_all_mean, gene_nuclear_mean)
    matrix_reconstruction_rho = correlation(matrix_totals, reconstructed_totals)
    matrix_reconstruction_relative_difference = float(
        abs(reconstructed_totals.sum() - matrix_totals.sum())
        / max(float(matrix_totals.sum()), 1.0)
    )
    summary = {
        "roi_name": name,
        "anatomy": roi["anatomy"],
        "n_cells_primary_qc": int(len(per_cell)),
        "same_qc_thresholds": {"min_gene_counts": min_counts, "min_genes": min_genes},
        "n_cells_passing_same_qc_nucleus_only": int(same_qc.sum()),
        "fraction_cells_passing_same_qc_nucleus_only": float(same_qc.mean()),
        "median_nuclear_fraction": float(per_cell["nuclear_fraction"].median()),
        "cell_count_spearman_all_vs_nucleus": cell_rho,
        "gene_mean_spearman_all_vs_nucleus": gene_rho,
        "module_exact_agreement": module_agreement,
        "module_nmi": module_nmi,
        "leiden_ari_all_vs_nucleus": cluster_ari,
        "leiden_nmi_all_vs_nucleus": cluster_nmi,
        "input_validation": {
            "exact_cell_by_gene_reconstruction": True,
            "n_mismatched_cell_gene_entries": n_reconstruction_mismatches,
            "max_absolute_count_difference": max_reconstruction_abs_difference,
            "cell_total_spearman_matrix_vs_transcript_parquet": matrix_reconstruction_rho,
            "relative_total_count_difference": matrix_reconstruction_relative_difference,
        },
        "interpretation": (
            "Sensitivity analysis only. Lower nuclear counts are expected. Robust marker/module "
            "and clustering results reduce concern about 5-µm nucleus expansion; disagreement "
            "must be reported and investigated, not corrected by count subtraction."
        ),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2))
    axes[0].scatter(
        np.log1p(matrix_totals), np.log1p(nuclear_totals),
        s=9, alpha=0.45, color="#2E75B6", linewidths=0,
    )
    axes[0].set_xlabel("log1p(all gene transcripts / cell)")
    axes[0].set_ylabel("log1p(nucleus-only transcripts / cell)")
    axes[0].set_title(f"Cell signal retention\nSpearman ρ={cell_rho:.2f}")

    axes[1].scatter(
        np.log1p(gene_all_mean), np.log1p(gene_nuclear_mean),
        s=13, alpha=0.55, color="#C74334", linewidths=0,
    )
    axes[1].set_xlabel("log1p(all mean transcripts / cell)")
    axes[1].set_ylabel("log1p(nucleus-only mean / cell)")
    axes[1].set_title(f"Gene-level preservation\nSpearman ρ={gene_rho:.2f}")

    metric_names = ["Cells retained", "Module agreement", "Leiden ARI"]
    metric_values = [float(same_qc.mean()), module_agreement, cluster_ari]
    shown_values = [0 if value is None else value for value in metric_values]
    bars = axes[2].bar(metric_names, shown_values, color=["#59A14F", "#F28E2B", "#4E79A7"])
    axes[2].set_ylim(0, 1)
    axes[2].set_ylabel("Fraction or agreement score")
    axes[2].tick_params(axis="x", rotation=25)
    axes[2].bar_label(bars, labels=["NA" if v is None else f"{v:.2f}" for v in metric_values])
    axes[2].set_title("Same-threshold sensitivity")
    fig.suptitle(f"{name}: nucleus-only segmentation sensitivity", fontweight="bold")
    fig.tight_layout()
    savefig(fig, output / "01_nucleus_only_sensitivity.png")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_current.json"))
    parser.add_argument("--processed-root", default=str(HERE / "outputs"))
    parser.add_argument(
        "--output-root", default=str(HERE / "outputs" / "segmentation_sensitivity")
    )
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    qc = config.get("qc", {})
    min_counts = int(qc.get("min_gene_counts", 20))
    min_genes = int(qc.get("min_genes", 5))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    np.random.seed(SEED)
    rows = [
        process_roi(
            roi, Path(args.processed_root), output_root, min_counts, min_genes
        )
        for roi in config["rois"]
    ]
    pd.DataFrame(rows).to_csv(output_root / "segmentation_sensitivity_summary.csv", index=False)
    (output_root / "run_summary.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    print(f"DONE: {len(rows)} ROIs -> {output_root}")


if __name__ == "__main__":
    main()
