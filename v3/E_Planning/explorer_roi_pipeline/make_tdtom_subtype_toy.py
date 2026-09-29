"""Generate a clearly labeled synthetic demonstration of candidate-subtype outputs."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 20260929


def make_fixture(root: Path) -> Path:
    rng = np.random.default_rng(SEED)
    processed = root / "processed"
    genes = ["tdTomato", "Fos", "Arc", "SubtypeA", "SubtypeB", "SubtypeC"] + [
        f"Identity{i:02d}" for i in range(24)
    ]
    rois = []
    for mouse_index in range(4):
        animal = f"mouse{mouse_index + 1}"
        roi = f"{animal}_bla"
        n_cells = 160
        is_subtype = np.zeros(n_cells, dtype=bool)
        is_subtype[rng.choice(n_cells, size=48, replace=False)] = True
        counts = rng.poisson(0.8, size=(n_cells, len(genes))).astype(np.float32)
        counts[is_subtype, 0] = 4
        counts[~is_subtype, 0] = 0
        counts[is_subtype, 1:3] += rng.poisson(3.0, size=(is_subtype.sum(), 2))
        counts[is_subtype, 3:6] += rng.poisson(8.0, size=(is_subtype.sum(), 3))
        counts[~is_subtype, 3:6] = rng.binomial(1, 0.08, size=((~is_subtype).sum(), 3))
        # Add broad identity variation that is unrelated to reporter status.
        nuisance = rng.integers(0, 4, size=n_cells)
        for group in range(4):
            hit = nuisance == group
            start = 6 + group * 4
            counts[hit, start:start + 4] += rng.poisson(2.0, size=(hit.sum(), 4))
        x = rng.normal(0, 1.3, n_cells)
        y = rng.normal(0, 1.1, n_cells)
        x[is_subtype] = rng.normal(3.5, 0.55, is_subtype.sum())
        y[is_subtype] = rng.normal(2.6, 0.50, is_subtype.sum())
        obs = pd.DataFrame({
            "module": "BLA_principal",
            "x_centroid": x + mouse_index * 8,
            "y_centroid": y,
        }, index=[f"{roi}_cell{i:03d}" for i in range(n_cells)])
        obj = ad.AnnData(X=counts, obs=obs, var=pd.DataFrame(index=genes))
        obj.layers["counts"] = counts.copy()
        destination = processed / roi / f"{roi}_processed.h5ad"
        destination.parent.mkdir(parents=True, exist_ok=True)
        obj.write_h5ad(destination)
        rois.append({
            "roi_name": roi,
            "animal_id": animal,
            "condition": "Active" if mouse_index < 2 else "Passive",
            "anatomy": "BLA",
            "section_id": roi,
            "cell_class_column": "module",
            "tdtom_min_counts": 2,
        })
    config = root / "toy_config.json"
    config.write_text(json.dumps({"rois": rois}, indent=2) + "\n", encoding="utf-8")
    return config


def make_summary(results: Path, destination: Path) -> None:
    group = results / "BLA" / "BLA_principal"
    assignments = pd.read_csv(group / "cell_assignments.csv", index_col=0)
    candidates = pd.read_csv(group / "candidate_clusters.csv")
    effects = pd.read_csv(group / "tdtom_vs_negative_effects_by_animal.csv")
    stable = pd.read_csv(group / "stable_tdtom_identity_markers.csv")
    enrichment = pd.read_csv(group / "unbiased_cluster_tdtom_enrichment_by_animal.csv")
    lomo = pd.read_csv(group / "leave_one_mouse_out_marker_validation.csv")
    candidate = str(candidates.loc[candidates["candidate_novel_subtype"], "cluster"].iloc[0])
    stable_genes = stable.loc[stable["stable_identity_marker"], "gene"].head(8).tolist()

    fig, axes = plt.subplots(2, 2, figsize=(12, 9.2))
    cluster = assignments["identity_leiden_1"].astype(str)
    codes = pd.Categorical(cluster).codes
    axes[0, 0].scatter(assignments["UMAP1"], assignments["UMAP2"], c=codes,
                       cmap="tab20", s=10, linewidths=0)
    hit = cluster == candidate
    axes[0, 0].scatter(assignments.loc[hit, "UMAP1"], assignments.loc[hit, "UMAP2"],
                       facecolors="none", edgecolors="#111111", s=28, linewidths=0.8,
                       label="candidate cluster")
    axes[0, 0].set_title("A  Identity-gene clustering (reporter hidden)", loc="left", fontweight="bold")
    axes[0, 0].legend(frameon=False, loc="best")

    positive = assignments["tdTom_positive"].astype(str).str.lower().eq("true")
    axes[0, 1].scatter(assignments.loc[~positive, "UMAP1"], assignments.loc[~positive, "UMAP2"],
                       c="0.82", s=8, linewidths=0, label="tdTom−")
    axes[0, 1].scatter(assignments.loc[positive, "UMAP1"], assignments.loc[positive, "UMAP2"],
                       c="#C74334", s=11, linewidths=0, label="tdTom+")
    axes[0, 1].set_title("B  Reporter revealed after clustering", loc="left", fontweight="bold")
    axes[0, 1].legend(frameon=False)

    matrix = effects[effects["gene"].isin(stable_genes)].pivot(
        index="gene", columns="animal_id", values="log2_mean_ratio"
    ).reindex(stable_genes)
    vmax = max(1.0, float(np.nanmax(np.abs(matrix.to_numpy()))))
    image = axes[1, 0].imshow(matrix, cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
    axes[1, 0].set_xticks(range(matrix.shape[1]), matrix.columns)
    axes[1, 0].set_yticks(range(matrix.shape[0]), matrix.index)
    axes[1, 0].set_title("C  Stable markers reproduce in each mouse", loc="left", fontweight="bold")
    fig.colorbar(image, ax=axes[1, 0], label="log2 mean ratio: tdTom+ / tdTom−", shrink=0.82)

    candidate_enrichment = enrichment[enrichment["cluster"].astype(str) == candidate]
    x = np.arange(len(candidate_enrichment))
    axes[1, 1].bar(x - 0.17, candidate_enrichment["log2_tdtom_odds_cluster_vs_rest"],
                   width=0.34, color="#4C78A8", label="cluster tdTom log2 odds")
    axes[1, 1].axhline(1.0, color="#4C78A8", linestyle="--", linewidth=1)
    ax2 = axes[1, 1].twinx()
    ax2.bar(x + 0.17, lomo["marker_score_auc_for_tdtom_in_held_out"],
            width=0.34, color="#F58518", label="held-out marker AUC")
    ax2.axhline(0.65, color="#F58518", linestyle="--", linewidth=1)
    axes[1, 1].set_xticks(x, candidate_enrichment["animal_id"])
    axes[1, 1].set_ylabel("log2 odds")
    ax2.set_ylabel("leave-one-mouse-out AUC")
    ax2.set_ylim(0, 1.05)
    axes[1, 1].set_title("D  Enrichment and held-out validation", loc="left", fontweight="bold")
    handles1, labels1 = axes[1, 1].get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    axes[1, 1].legend(handles1 + handles2, labels1 + labels2, frameon=False, loc="upper left")

    for ax in axes[0]:
        ax.set_xlabel("UMAP-1")
        ax.set_ylabel("UMAP-2")
    fig.suptitle(
        "SIMULATED DATA — what a tdTom-associated candidate novel subtype would look like\n"
        "Candidate status requires an unbiased cluster, stable identity markers, cross-mouse enrichment, and held-out prediction",
        fontsize=15, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(HERE / "toy_candidate_subtype"))
    args = parser.parse_args()
    root = Path(args.output_root)
    config = make_fixture(root)
    results = root / "results"
    subprocess.run([
        sys.executable, str(HERE / "run_tdtom_novel_subtype.py"),
        "--config", str(config),
        "--processed-root", str(root / "processed"),
        "--output-root", str(results),
    ], check=True)
    make_summary(results, root / "tdtom_candidate_subtype_SIMULATED.png")
    print(f"DONE: {root}")


if __name__ == "__main__":
    main()
