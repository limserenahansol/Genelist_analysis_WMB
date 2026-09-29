"""Create concise cross-ROI figures for the available expanded pilot ROIs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "figure.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
})


def total_variation(a: pd.Series, b: pd.Series) -> float:
    idx = a.index.union(b.index)
    return float(0.5 * np.abs(a.reindex(idx, fill_value=0) - b.reindex(idx, fill_value=0)).sum())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_expanded_available.json"))
    parser.add_argument("--output", default=str(HERE / "outputs" / "expanded_roi_comparison"))
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = Path(args.output)
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    rows = []
    comp_rows = []
    for roi in cfg["rois"]:
        roi_name = roi["roi_name"]
        summary_path = HERE / "outputs" / roi_name / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        label = roi_name.replace("orbm_0063814_", "ORBm ").replace(
            "bmap_0063817_", "BMAp "
        ).replace("_", " ")
        rows.append({
            "roi_name": roi_name,
            "label": label,
            "animal_id": roi["animal_id"],
            "anatomy": roi["anatomy"],
            "section_id": roi.get("section_id"),
            "cell_source": summary["roi_cell_source"],
            "n_export": summary["n_roi_export"],
            "n_after_qc": summary["n_after_qc"],
            "qc_retained_percent": 100 * summary["n_after_qc"] / summary["n_roi_export"],
            "median_gene_counts_after_qc": summary["baseline_transcripts"]["roi_after_qc_median_gene_counts"],
            "n_leiden": summary["clustering"]["leiden_n"],
            "ari_res0.5": summary["clustering"]["ari_res1_vs_res0.5"],
            "ari_res1.5": summary["clustering"]["ari_res1_vs_res1.5"],
            "allen_ari": summary["reference_validation"]["ari_leiden_vs_reference"],
            "polygon_count_difference": summary.get("polygon_count_difference"),
        })
        total = sum(summary["module_counts"].values())
        for module, count in summary["module_counts"].items():
            comp_rows.append({
                "roi_name": roi_name,
                "label": label,
                "anatomy": roi["anatomy"],
                "module": module,
                "n_cells": count,
                "percent": 100 * count / total,
            })

    roi_df = pd.DataFrame(rows)
    comp_df = pd.DataFrame(comp_rows)
    roi_df.to_csv(out / "expanded_roi_summary.csv", index=False)
    comp_df.to_csv(out / "expanded_roi_module_composition.csv", index=False)

    colors = roi_df["anatomy"].map({"ORBm": "#2E75B6", "BMAp": "#C74334"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    bars = axes[0].bar(roi_df["label"], roi_df["n_after_qc"], color=colors)
    axes[0].bar_label(bars, padding=2, fontsize=9)
    axes[0].set_title("QC-passing cells")
    axes[0].set_ylabel("Cells")
    bars = axes[1].bar(roi_df["label"], roi_df["median_gene_counts_after_qc"], color=colors)
    axes[1].bar_label(bars, padding=2, fontsize=9)
    axes[1].set_title("Median measured transcripts per cell")
    axes[1].set_ylabel("Transcripts")
    for ax in axes:
        ax.tick_params(axis="x", rotation=32)
    fig.suptitle("Expanded target ROIs: yield and expression depth", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(figdir / "01_expanded_roi_yield_and_depth.png", dpi=200)
    plt.close(fig)

    modules = sorted(comp_df["module"].unique())
    palette = {m: plt.colormaps["tab20"](i / max(1, len(modules) - 1)) for i, m in enumerate(modules)}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    for ax, anatomy in zip(axes, ["ORBm", "BMAp"]):
        sub = comp_df[comp_df["anatomy"] == anatomy]
        table = sub.pivot(index="label", columns="module", values="percent").fillna(0)
        left = np.zeros(len(table))
        for module in table.columns:
            ax.barh(table.index, table[module], left=left, color=palette[module], label=module)
            left += table[module].to_numpy()
        ax.set_title(anatomy)
        ax.set_xlabel("Cells (%)")
        ax.set_xlim(0, 100)
    handles, labels = axes[0].get_legend_handles_labels()
    handles2, labels2 = axes[1].get_legend_handles_labels()
    legend = dict(zip(labels + labels2, handles + handles2))
    fig.legend(legend.values(), legend.keys(), loc="lower center", ncol=6, frameon=False)
    fig.suptitle("Marker-module composition across available ROIs", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0.13, 1, 0.95])
    fig.savefig(figdir / "02_expanded_roi_module_composition.png", dpi=200)
    plt.close(fig)

    comp_prop = comp_df.pivot(index="roi_name", columns="module", values="percent").fillna(0) / 100
    comparisons = [
        ("ORBm R3 left vs right", "orbm_0063814_r3_left", "orbm_0063814_r3_right"),
        ("ORBm right R2 vs R3", "orbm_0063814_r2_right", "orbm_0063814_r3_right"),
        ("BMAp R1 left vs right", "bmap_0063817_r1_left", "bmap_0063817_r1_right"),
    ]
    distances = []
    for label, a, b in comparisons:
        distances.append({"comparison": label, "total_variation": total_variation(comp_prop.loc[a], comp_prop.loc[b])})
    dist_df = pd.DataFrame(distances)
    dist_df.to_csv(out / "module_composition_pairwise_total_variation.csv", index=False)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    bars = ax.barh(dist_df["comparison"], dist_df["total_variation"], color=["#2E75B6", "#5B9BD5", "#C74334"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Total variation distance (0 = identical; 1 = disjoint)")
    ax.set_title("Within-mouse ROI composition differences")
    ax.bar_label(bars, fmt="%.2f", padding=3)
    fig.tight_layout()
    fig.savefig(figdir / "03_within_mouse_composition_distance.png", dpi=200)
    plt.close(fig)

    lines = [
        "# Expanded ROI comparison",
        "",
        f"Five target ROIs produced {int(roi_df['n_after_qc'].sum()):,} QC-passing cells.",
        "All ROI comparisons are descriptive because the data represent two animals and",
        "ORBm and BMAp occur on different pilot animals.",
        "",
        "## Composition differences",
        "",
    ]
    lines.extend(
        f"- {row.comparison}: total variation = {row.total_variation:.3f}"
        for row in dist_df.itertuples(index=False)
    )
    lines.extend([
        "",
        "The Region 2 ORBm polygon selected 975 centroids versus 951 cells in the Explorer",
        "combined summary. Treat that ROI as approximate until a Cell ID stats export is available.",
    ])
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"DONE: {out}")


if __name__ == "__main__":
    main()
