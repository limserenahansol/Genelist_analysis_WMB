"""Inventory six Xenium bundles, XOA QC metrics, and Explorer ROI exports."""
from __future__ import annotations

import argparse
import csv
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


def read_first_summary_table(path: Path) -> pd.DataFrame:
    """Read the first table from an Explorer combined-stats CSV."""
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    block = []
    for line in lines:
        if block and not line.strip():
            break
        if line.strip():
            block.append(line)
    if len(block) < 2:
        return pd.DataFrame()
    return pd.DataFrame(csv.DictReader(block))


def classify_export(path: Path) -> str | None:
    name = path.name.lower()
    if name.endswith("_cells_stats.csv"):
        return "cell_ids"
    if "combined_stats" in name or name.startswith("all_selections"):
        return "combined_summary"
    if name.endswith("coordinates.csv") or name in {"coordinates.csv", "bla_left_right.csv"}:
        return "polygon_coordinates"
    if name.endswith(".geojson"):
        return "geojson"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "six_xenium_bundles.json"))
    parser.add_argument("--output", default=str(HERE / "outputs" / "six_bundle_inventory"))
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = Path(args.output)
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)

    metrics_rows = []
    export_rows = []
    roi_rows = []

    for bundle in cfg["bundles"]:
        xenium = Path(bundle["xenium"])
        metrics = pd.read_csv(xenium / "metrics_summary.csv").iloc[0].to_dict()
        row = {k: bundle[k] for k in ["animal_id", "anatomy", "section_id", "xenium"]}
        row.update(metrics)
        metrics_rows.append(row)

        for path in sorted(xenium.iterdir()):
            if not path.is_file():
                continue
            export_type = classify_export(path)
            if export_type is None:
                continue
            export_rows.append({
                "animal_id": bundle["animal_id"],
                "anatomy": bundle["anatomy"],
                "section_id": bundle["section_id"],
                "file": path.name,
                "export_type": export_type,
                "modified": path.stat().st_mtime,
                "bytes": path.stat().st_size,
            })
            if export_type == "cell_ids":
                cells = pd.read_csv(path, comment="#")
                selection = path.name.removesuffix("_cells_stats.csv")
                roi_rows.append({
                    "animal_id": bundle["animal_id"],
                    "anatomy": bundle["anatomy"],
                    "section_id": bundle["section_id"],
                    "selection": selection,
                    "n_cells": len(cells),
                    "source": "cell-ID export",
                    "file": path.name,
                })
            elif export_type == "combined_summary":
                summary = read_first_summary_table(path)
                for _, record in summary.iterrows():
                    if "Annotation Name" not in record or "Cell Count" not in record:
                        continue
                    roi_rows.append({
                        "animal_id": bundle["animal_id"],
                        "anatomy": bundle["anatomy"],
                        "section_id": bundle["section_id"],
                        "selection": str(record["Annotation Name"]),
                        "n_cells": int(float(record["Cell Count"])),
                        "source": "combined summary",
                        "file": path.name,
                    })

    metrics_df = pd.DataFrame(metrics_rows)
    exports_df = pd.DataFrame(export_rows)
    rois_df = pd.DataFrame(roi_rows)
    fp_column = "estimated_number_of_false_positive_transcripts_per_cell"
    metrics_df["estimated_false_positive_pct_of_median_transcripts"] = (
        100
        * pd.to_numeric(metrics_df[fp_column])
        / pd.to_numeric(metrics_df["median_transcripts_per_cell"])
    )
    metrics_df.to_csv(out / "bundle_metrics.csv", index=False)
    exports_df.to_csv(out / "explorer_export_inventory.csv", index=False)
    rois_df.to_csv(out / "roi_selection_inventory.csv", index=False)

    metrics_df["short_section"] = metrics_df["section_id"].str.replace("00", "", regex=False)
    colors = metrics_df["anatomy"].map({"ORBm": "#2E75B6", "BMAp": "#C74334"})
    plot_specs = [
        ("num_cells_detected", "Cells detected", 1.0),
        ("median_transcripts_per_cell", "Median transcripts / cell", 1.0),
        ("fraction_transcripts_assigned", "Transcripts assigned (%)", 100.0),
        ("fraction_transcripts_decoded_q20", "Decoded Q20 (%)", 100.0),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.2))
    for ax, (column, title, scale) in zip(axes.flat, plot_specs):
        values = pd.to_numeric(metrics_df[column]) * scale
        bars = ax.bar(metrics_df["short_section"], values, color=colors)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=35)
        ax.bar_label(bars, fmt="%.1f" if scale == 100 else "%.0f", fontsize=8, padding=2)
    fig.suptitle("Six Xenium bundles: XOA quality overview", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(figdir / "01_six_bundle_qc_overview.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.1))
    line_specs = [
        ("median_genes_per_cell", "Median genes / cell"),
        ("median_transcripts_per_cell", "Median transcripts / cell"),
        ("fraction_transcripts_assigned", "Transcripts assigned (%)"),
    ]
    for ax, (column, title) in zip(axes, line_specs):
        for anatomy, sub in metrics_df.groupby("anatomy", sort=False):
            region_number = sub["section_id"].str.extract(r"Region_(\d+)")[0].astype(int)
            values = pd.to_numeric(sub[column])
            if column.startswith("fraction_"):
                values = values * 100
            ax.plot(region_number, values, marker="o", linewidth=2, label=anatomy)
        ax.set_title(title)
        ax.set_xlabel("Region / section")
        ax.set_xticks([1, 2, 3])
    axes[0].set_ylabel("Observed value")
    axes[-1].legend(frameon=False)
    fig.suptitle("Within-slide section consistency (descriptive)", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(figdir / "02_section_consistency.png", dpi=200)
    plt.close(fig)

    target = rois_df[rois_df["selection"].str.lower().str.contains("orbm|bmap", regex=True)].copy()
    if not target.empty:
        target["label"] = target["section_id"] + " · " + target["selection"]
        target = target.sort_values(["anatomy", "section_id", "selection"])
        fig, ax = plt.subplots(figsize=(10, max(3.6, 0.48 * len(target))))
        bar_colors = target["anatomy"].map({"ORBm": "#2E75B6", "BMAp": "#C74334"})
        bars = ax.barh(target["label"], target["n_cells"], color=bar_colors)
        ax.invert_yaxis()
        ax.set_xlabel("Cells reported by Explorer")
        ax.set_title("Available ORBm/BMAp ROI exports")
        ax.bar_label(bars, padding=3, fontsize=9)
        fig.tight_layout()
        fig.savefig(figdir / "03_target_roi_inventory.png", dpi=200)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2))
    fp_values = pd.to_numeric(metrics_df[fp_column])
    fp_pct = pd.to_numeric(metrics_df["estimated_false_positive_pct_of_median_transcripts"])
    for ax, values, title, ylabel, fmt in [
        (axes[0], fp_values, "Run-level false-positive estimate", "Transcripts / cell", "%.3f"),
        (axes[1], fp_pct, "Estimate relative to median signal", "% of median transcripts / cell", "%.2f"),
    ]:
        bars = ax.bar(metrics_df["short_section"], values, color=colors)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=35)
        ax.bar_label(bars, fmt=fmt, fontsize=8, padding=2)
    fig.suptitle("Negative-control estimate is reported, not subtracted", fontweight="bold")
    fig.tight_layout()
    fig.savefig(figdir / "04_false_positive_qc.png", dpi=200)
    plt.close(fig)

    q20 = pd.to_numeric(metrics_df["fraction_transcripts_decoded_q20"])
    assigned = pd.to_numeric(metrics_df["fraction_transcripts_assigned"])
    notes = [
        "# Six-bundle inventory",
        "",
        f"- Bundles found: {len(metrics_df)} / {len(cfg['bundles'])}",
        f"- XOA cells detected: {int(pd.to_numeric(metrics_df['num_cells_detected']).sum()):,} total",
        f"- Decoded Q20 range: {100*q20.min():.1f}%–{100*q20.max():.1f}%",
        f"- Transcript assignment range: {100*assigned.min():.1f}%–{100*assigned.max():.1f}%",
        f"- Estimated false positives: {fp_values.min():.3f}–{fp_values.max():.3f} transcripts/cell "
        f"({fp_pct.min():.2f}%–{fp_pct.max():.2f}% of each section median)",
        "- False-positive estimates are run-level negative-control metrics; report them and do not subtract them from genes or cells.",
        f"- Explorer-derived files catalogued: {len(exports_df)}",
        "",
        "Sections are nested within animal. They support section-level QC and more stable",
        "within-mouse summaries, but they do not increase the biological replicate count.",
        "Region 3 of 0063817 currently has no top-level Explorer ROI export.",
    ]
    (out / "SUMMARY.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print(f"DONE: {out}")


if __name__ == "__main__":
    main()
