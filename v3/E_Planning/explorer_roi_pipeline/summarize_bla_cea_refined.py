"""Summarize Allen-informed BLA/CEA marker-module refinement."""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
COLORS = {"BLA": "#4C78A8", "CEA": "#E45756"}


def load_summary(root: Path, roi: str) -> dict:
    return json.loads((root / roi / "summary.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_bla_cea_refined.json"))
    parser.add_argument("--baseline-root", default=str(HERE / "outputs"))
    parser.add_argument("--refined-root", default=str(HERE / "outputs_bla_cea_refined"))
    parser.add_argument("--output-root", default=str(HERE / "outputs_bla_cea_refined" / "summary"))
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    baseline_root, refined_root = Path(args.baseline_root), Path(args.refined_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    metric_rows, composition_rows = [], []
    for roi in config["rois"]:
        name, anatomy = roi["roi_name"], roi["anatomy"]
        before, after = load_summary(baseline_root, name), load_summary(refined_root, name)
        n_cells = int(after["n_after_qc"])
        before_unassigned = int(before["module_counts"].get("unassigned", 0))
        after_unassigned = int(after["module_counts"].get("unassigned", 0))
        metric_rows.append({
            "roi_name": name,
            "anatomy": anatomy,
            "n_cells": n_cells,
            "baseline_nmi_leiden_vs_module": before["same_matrix_concordance"]["nmi_leiden_vs_module"],
            "refined_nmi_leiden_vs_module": after["same_matrix_concordance"]["nmi_leiden_vs_module"],
            "baseline_assigned_fraction": 1 - before_unassigned / n_cells,
            "refined_assigned_fraction": 1 - after_unassigned / n_cells,
            "spatial_same_leiden_observed": after["spatial_description"]["spatial_neighbor_same_leiden"],
            "spatial_same_leiden_permuted": after["spatial_description"]["spatial_neighbor_same_leiden_perm_mean"],
        })
        for module, count in after["module_counts"].items():
            composition_rows.append({
                "roi_name": name,
                "anatomy": anatomy,
                "module": module,
                "n_cells": int(count),
                "fraction": int(count) / n_cells,
            })
    metrics = pd.DataFrame(metric_rows)
    composition = pd.DataFrame(composition_rows)
    metrics.to_csv(output_root / "refinement_metrics.csv", index=False)
    composition.to_csv(output_root / "refined_module_composition.csv", index=False)

    distance_rows = []
    for anatomy, sub in composition.groupby("anatomy"):
        pivot = sub.pivot(index="roi_name", columns="module", values="fraction").fillna(0)
        for left, right in combinations(pivot.index, 2):
            distance_rows.append({
                "anatomy": anatomy,
                "roi_1": left,
                "roi_2": right,
                "total_variation_distance": 0.5 * np.abs(pivot.loc[left] - pivot.loc[right]).sum(),
            })
    distances = pd.DataFrame(distance_rows)
    distances.to_csv(output_root / "within_anatomy_composition_distance.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9.2))
    x = np.arange(len(metrics))
    for index, row in metrics.iterrows():
        color = COLORS[row["anatomy"]]
        axes[0, 0].plot([0, 1], [row["baseline_nmi_leiden_vs_module"], row["refined_nmi_leiden_vs_module"]],
                        color=color, alpha=0.75, marker="o")
        axes[0, 1].plot([0, 1], [row["baseline_assigned_fraction"], row["refined_assigned_fraction"]],
                        color=color, alpha=0.75, marker="o")
    axes[0, 0].set_xticks([0, 1], ["BMAp modules", "BLA/CEA modules"])
    axes[0, 0].set_ylabel("NMI with unbiased Leiden clusters")
    axes[0, 0].set_title("A  Region-specific modules improve concordance", loc="left", fontweight="bold")
    anatomy_legend = [
        Line2D([0], [0], color=COLORS[name], marker="o", label=name)
        for name in ["BLA", "CEA"]
    ]
    axes[0, 0].legend(handles=anatomy_legend, frameon=False, loc="best")
    axes[0, 1].set_xticks([0, 1], ["BMAp modules", "BLA/CEA modules"])
    axes[0, 1].set_ylabel("Fraction assigned")
    axes[0, 1].set_ylim(0, 1)
    axes[0, 1].set_title("B  More cells receive interpretable labels", loc="left", fontweight="bold")
    axes[0, 1].legend(handles=anatomy_legend, frameon=False, loc="best")

    pivot = composition.pivot(index="roi_name", columns="module", values="fraction").fillna(0)
    ordered_rois = metrics["roi_name"].tolist()
    pivot = pivot.reindex(ordered_rois)
    bottom = np.zeros(len(pivot))
    palette = plt.colormaps["tab20"].colors
    for index, module in enumerate(pivot.columns):
        values = pivot[module].to_numpy()
        axes[1, 0].bar(np.arange(len(pivot)), values, bottom=bottom, label=module,
                       color=palette[index % len(palette)], width=0.82)
        bottom += values
    axes[1, 0].set_xticks(np.arange(len(pivot)), pivot.index, rotation=35, ha="right")
    axes[1, 0].set_ylabel("Cell fraction")
    axes[1, 0].set_ylim(0, 1)
    axes[1, 0].set_title("C  Refined BLA/CEA cell-type composition", loc="left", fontweight="bold")
    axes[1, 0].legend(frameon=False, fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")

    for anatomy, sub in distances.groupby("anatomy"):
        xpos = 0 if anatomy == "BLA" else 1
        jitter = np.linspace(-0.08, 0.08, len(sub)) if len(sub) > 1 else np.array([0.0])
        axes[1, 1].scatter(xpos + jitter, sub["total_variation_distance"],
                           color=COLORS[anatomy], s=45, alpha=0.85, label=anatomy)
        axes[1, 1].plot([xpos - 0.13, xpos + 0.13],
                        [sub["total_variation_distance"].median()] * 2,
                        color="black", linewidth=2)
    axes[1, 1].set_xticks([0, 1], ["BLA", "CEA"])
    axes[1, 1].set_ylabel("Total variation distance")
    axes[1, 1].set_ylim(bottom=0)
    axes[1, 1].set_title("D  Section/hemisphere composition variation", loc="left", fontweight="bold")
    axes[1, 1].text(0.02, 0.96, "Descriptive: all ROIs are from one animal",
                    transform=axes[1, 1].transAxes, va="top", fontsize=9)

    fig.suptitle("BLA and CEA: Allen-informed marker refinement on the 247-gene pilot",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_root / "01_bla_cea_refinement_summary.png", dpi=220,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"DONE: {output_root}")


if __name__ == "__main__":
    main()
