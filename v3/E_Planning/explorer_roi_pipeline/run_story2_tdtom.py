"""Story 2: Ai14 tdTomato overlap and within-cell-class expression summaries.

The tdTom gate is a technical classification, not a biological replicate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
from scipy import sparse
from sklearn.neighbors import NearestNeighbors

HERE = Path(__file__).resolve().parent
DEFAULT_THRESHOLD = 2
MIN_PER_STATUS = 20


def wilson_interval(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return center - half, center + half


def get_gene_index(var_names, target):
    return {str(g).lower(): i for i, g in enumerate(var_names)}.get(target.lower())


def counts_matrix(adata):
    x = adata.layers["counts"] if "counts" in adata.layers else adata.X
    return x.toarray() if sparse.issparse(x) else np.asarray(x)


def neighbor_bleed_flag(xy, tdtom_counts, positive, k=6):
    if len(xy) < 2:
        return np.zeros(len(xy), dtype=bool)
    k_use = min(k, len(xy) - 1)
    nn = NearestNeighbors(n_neighbors=k_use + 1).fit(xy)
    nbr = nn.kneighbors(xy, return_distance=False)[:, 1:]
    return (tdtom_counts == 1) & (positive[nbr].mean(axis=1) > 0.5)


def process_roi(roi, out_root):
    roi_name = roi["roi_name"]
    source = HERE / "outputs" / roi_name / f"{roi_name}_processed.h5ad"
    if not source.exists():
        raise FileNotFoundError(f"Run run_from_explorer.py first; missing {source}")
    adata = sc.read_h5ad(source)
    idx = get_gene_index(adata.var_names, "tdTomato")
    if idx is None:
        return None

    out = out_root / roi_name
    out.mkdir(parents=True, exist_ok=True)
    x = counts_matrix(adata)
    tdtom = np.asarray(x[:, idx]).ravel()
    threshold = int(roi.get("tdtom_min_counts", DEFAULT_THRESHOLD))
    positive = tdtom >= threshold
    xy = adata.obs[["x_centroid", "y_centroid"]].to_numpy()
    bleed_flag = neighbor_bleed_flag(xy, tdtom, positive)

    default_class = "reference_label" if (
        "reference_label" in adata.obs and adata.obs["reference_label"].notna().sum() >= 20
    ) else "module"
    class_col = roi.get("cell_class_column", default_class)
    if class_col not in adata.obs:
        raise ValueError(f"{roi_name}: cell class column {class_col!r} is absent")
    classes = adata.obs[class_col].astype("string").fillna("unassigned").astype(str)

    per_cell = pd.DataFrame({
        "cell_id": adata.obs_names.astype(str),
        "animal_id": roi.get("animal_id"),
        "condition": roi.get("condition", "unspecified"),
        "anatomy": roi.get("anatomy"),
        "cell_class": classes.to_numpy(),
        "leiden": adata.obs["leiden"].astype(str).to_numpy(),
        "module": adata.obs["module"].astype(str).to_numpy(),
        "tdTomato_counts": tdtom,
        "tdTom_positive": positive,
        "one_count_neighbor_flag": bleed_flag,
        "x_centroid": adata.obs["x_centroid"].to_numpy(),
        "y_centroid": adata.obs["y_centroid"].to_numpy(),
    })
    per_cell.to_csv(out / "tdtom_cells.csv", index=False)
    pd.DataFrame({
        "cell_id": per_cell["cell_id"],
        "group": np.where(positive, "tdTom_positive", "tdTom_negative"),
    }).to_csv(out / "cell_groups_tdtom.csv", index=False)

    rows = []
    for cls, sub in per_cell.groupby("cell_class"):
        n = len(sub)
        k = int(sub["tdTom_positive"].sum())
        lo, hi = wilson_interval(k, n)
        rows.append({
            "roi_name": roi_name, "animal_id": roi.get("animal_id"),
            "anatomy": roi.get("anatomy"), "cell_class": cls,
            "n_cells": n, "n_positive": k, "pct_positive": 100 * k / n,
            "wilson95_low_pct": 100 * lo, "wilson95_high_pct": 100 * hi,
            "n_negative": n - k,
        })
    rate = pd.DataFrame(rows).sort_values("pct_positive", ascending=False)
    rate.to_csv(out / "tdtom_rate_by_cell_class.csv", index=False)

    effects = []
    excluded = {"tdtomato", "icre", "cre"}
    eligible = rate.loc[
        (rate.n_positive >= MIN_PER_STATUS) & (rate.n_negative >= MIN_PER_STATUS),
        "cell_class",
    ]
    for cls in eligible:
        m_cls = classes.to_numpy() == cls
        pos, neg = m_cls & positive, m_cls & ~positive
        for j, gene in enumerate(adata.var_names.astype(str)):
            if gene.lower() in excluded:
                continue
            vp, vn = x[pos, j], x[neg, j]
            effects.append({
                "roi_name": roi_name, "animal_id": roi.get("animal_id"),
                "anatomy": roi.get("anatomy"), "cell_class": cls, "gene": gene,
                "n_positive": int(pos.sum()), "n_negative": int(neg.sum()),
                "mean_positive": float(vp.mean()), "mean_negative": float(vn.mean()),
                "pct_detected_positive": float(100 * np.mean(vp > 0)),
                "pct_detected_negative": float(100 * np.mean(vn > 0)),
                "log2_mean_ratio": float(np.log2((vp.mean() + 0.1) / (vn.mean() + 0.1))),
                "delta_detected_pct": float(100 * (np.mean(vp > 0) - np.mean(vn > 0))),
                "inference": "descriptive_within_animal",
            })
    effect_df = pd.DataFrame(effects)
    effect_df.to_csv(out / "tdtom_within_class_effects_descriptive.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    axes[0].scatter(per_cell.x_centroid, per_cell.y_centroid, c="#d9d9d9", s=7, linewidths=0)
    shown = tdtom > 0
    sca = axes[0].scatter(
        per_cell.loc[shown, "x_centroid"], per_cell.loc[shown, "y_centroid"],
        c=tdtom[shown], s=10, cmap="magma", linewidths=0,
    )
    axes[0].invert_yaxis()
    axes[0].set_aspect("equal")
    axes[0].set_title(f"Ai14 tdTomato transcripts\n(gate >= {threshold})")
    axes[0].set_xlabel("x (um)")
    axes[0].set_ylabel("y (um)")
    fig.colorbar(sca, ax=axes[0], label="transcripts / cell")

    plot_rate = rate[rate.n_cells >= 10].sort_values("pct_positive")
    err = np.vstack([
        plot_rate.pct_positive - plot_rate.wilson95_low_pct,
        plot_rate.wilson95_high_pct - plot_rate.pct_positive,
    ])
    axes[1].barh(plot_rate.cell_class, plot_rate.pct_positive, color="#d95f5f")
    axes[1].errorbar(
        plot_rate.pct_positive, plot_rate.cell_class, xerr=err,
        fmt="none", ecolor="0.2", capsize=2,
    )
    axes[1].set_xlim(0, 100)
    axes[1].set_xlabel("tdTom+ cells (%) with 95% binomial CI")
    axes[1].set_title("Which cell classes overlap TRAP labeling?")
    axes[1].grid(axis="x", color="0.9")
    fig.suptitle(f"{roi_name}: reporter overlap", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "01_tdtom_overlap_summary.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    sensitivity = []
    for cutoff in (1, 2, 3):
        for cls in sorted(set(classes)):
            m = classes.to_numpy() == cls
            sensitivity.append({
                "roi_name": roi_name, "cell_class": cls, "threshold": cutoff,
                "n_cells": int(m.sum()),
                "pct_positive": float(100 * np.mean(tdtom[m] >= cutoff)),
            })
    pd.DataFrame(sensitivity).to_csv(out / "tdtom_threshold_sensitivity.csv", index=False)

    cluster_rows = []
    overall_pos = int(positive.sum())
    overall_neg = int((~positive).sum())
    leiden = adata.obs["leiden"].astype(str).to_numpy()
    for cluster in sorted(set(leiden), key=lambda value: int(value)):
        inside = leiden == cluster
        a = int((inside & positive).sum())
        b = int((inside & ~positive).sum())
        c = overall_pos - a
        d = overall_neg - b
        odds = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
        class_counts = classes[inside].value_counts(normalize=True)
        majority_class = str(class_counts.index[0])
        purity = float(class_counts.iloc[0])
        cluster_rows.append({
            "roi_name": roi_name, "animal_id": roi.get("animal_id"),
            "condition": roi.get("condition", "unspecified"), "anatomy": roi.get("anatomy"),
            "leiden": cluster, "n_cells": int(inside.sum()), "n_positive": a,
            "pct_positive": float(100 * a / inside.sum()),
            "tdtom_odds_ratio_cluster_vs_rest": float(odds),
            "majority_reference_or_module_class": majority_class,
            "class_purity": purity,
            "interpretation": (
                "enriched_cluster_within_known_class" if purity >= 0.7
                else "mixed_or_low_confidence_cluster_review"
            ),
        })
    cluster_df = pd.DataFrame(cluster_rows)
    cluster_df.to_csv(out / "tdtom_enrichment_by_leiden_cluster.csv", index=False)
    return per_cell, rate, effect_df, cluster_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_current.json"))
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out_root = HERE / "outputs" / "story2_tdtom"
    out_root.mkdir(parents=True, exist_ok=True)

    results = []
    for roi in cfg["rois"]:
        result = process_roi(roi, out_root)
        if result is not None:
            results.append((roi, result))
    if not results:
        msg = (
            "SKIPPED Story 2. tdTomato is absent from the processed matrices. "
            "Ai14 requires a custom tdTomato probe in the real panel."
        )
        (out_root / "SKIPPED.md").write_text(msg + "\n", encoding="utf-8")
        print(msg)
        return

    pd.concat([r[1][1] for r in results], ignore_index=True).to_csv(
        out_root / "all_rois_tdtom_rate_by_cell_class.csv", index=False
    )
    all_cells = pd.concat([r[1][0] for r in results], ignore_index=True)
    all_cells.to_csv(out_root / "all_rois_tdtom_cells.csv", index=False)
    pd.concat([r[1][3] for r in results], ignore_index=True).to_csv(
        out_root / "all_rois_tdtom_enrichment_by_leiden_cluster.csv", index=False
    )

    enrichment_rows = []
    animal_cols = ["animal_id", "condition", "anatomy"]
    for keys, animal_df in all_cells.groupby(animal_cols, dropna=False):
        animal_id, condition, anatomy = keys
        total_pos = int(animal_df["tdTom_positive"].sum())
        total_neg = int((~animal_df["tdTom_positive"]).sum())
        for cell_class, sub in animal_df.groupby("cell_class"):
            pos = int(sub["tdTom_positive"].sum())
            neg = int((~sub["tdTom_positive"]).sum())
            other_pos = total_pos - pos
            other_neg = total_neg - neg
            comp_pos = (pos + 0.5) / (total_pos + 0.5 * animal_df["cell_class"].nunique())
            comp_neg = (neg + 0.5) / (total_neg + 0.5 * animal_df["cell_class"].nunique())
            odds = ((pos + 0.5) * (other_neg + 0.5)) / ((neg + 0.5) * (other_pos + 0.5))
            enrichment_rows.append({
                "animal_id": animal_id, "condition": condition, "anatomy": anatomy,
                "cell_class": cell_class, "n_cells": int(len(sub)),
                "n_tdtom_positive": pos, "n_tdtom_negative": neg,
                "pct_positive_within_class": float(100 * pos / len(sub)),
                "pct_of_all_positive_cells": float(100 * pos / total_pos) if total_pos else np.nan,
                "pct_of_all_negative_cells": float(100 * neg / total_neg) if total_neg else np.nan,
                "log2_composition_enrichment_positive_vs_negative": float(np.log2(comp_pos / comp_neg)),
                "odds_ratio_tdtom_positive_for_class_vs_other_classes": float(odds),
            })
    enrichment = pd.DataFrame(enrichment_rows)
    enrichment.to_csv(out_root / "cell_type_tdtom_enrichment_by_animal.csv", index=False)

    if len(enrichment):
        for anatomy, sub in enrichment.groupby("anatomy"):
            order = (
                sub.groupby("cell_class")["log2_composition_enrichment_positive_vs_negative"]
                .mean().sort_values().index
            )
            fig, ax = plt.subplots(figsize=(max(7.5, 0.75 * sub["condition"].nunique() + 5), max(4.8, 0.4 * len(order) + 2)))
            conditions = list(dict.fromkeys(sub["condition"].astype(str)))
            offsets = np.linspace(-0.22, 0.22, max(1, len(conditions)))
            condition_colors = plt.colormaps["Set1"].colors
            y_lookup = {name: i for i, name in enumerate(order)}
            for condition_index, (offset, condition) in enumerate(zip(offsets, conditions)):
                condition_df = sub[sub["condition"].astype(str) == condition]
                for cell_class, class_df in condition_df.groupby("cell_class"):
                    y = y_lookup[cell_class] + offset
                    ax.scatter(
                        class_df["log2_composition_enrichment_positive_vs_negative"],
                        np.full(len(class_df), y), s=34, alpha=0.75,
                        color=condition_colors[condition_index % len(condition_colors)],
                        label=condition if cell_class == order[0] else None,
                    )
                    ax.plot(
                        [class_df["log2_composition_enrichment_positive_vs_negative"].mean()],
                        [y], marker="D", color="black", ms=5,
                    )
            ax.axvline(0, color="0.35", lw=1, ls="--")
            ax.set_yticks(range(len(order)), order)
            ax.set_xlabel("log2 composition enrichment in tdTom+ versus tdTom−")
            ax.set_ylabel("Existing cell class")
            ax.set_title(f"{anatomy}: which cell classes preferentially contain tdTom+ cells?")
            if len(conditions) > 1:
                ax.legend(title="Condition", frameon=False)
            ax.grid(axis="x", color="0.9")
            fig.tight_layout()
            fig.savefig(out_root / f"02_{anatomy}_tdtom_cell_type_enrichment.png", dpi=200, bbox_inches="tight")
            plt.close(fig)
    all_effects = [r[1][2] for r in results if len(r[1][2])]
    if all_effects:
        pd.concat(all_effects, ignore_index=True).to_csv(
            out_root / "all_rois_effects_descriptive.csv", index=False
        )
    note = (
        "Ai14 tdTomato was gated from raw transcript counts. Threshold sensitivity (1/2/3) "
        "is exported. Calibrate the final cutoff with Cre-negative or no-induction controls. "
        "Per-cell effects are descriptive; biological inference requires animal-level replication. "
        "iCre need not remain expressed when permanent Ai14 tdTomato is measured.\n"
    )
    (out_root / "README.md").write_text(note, encoding="utf-8")
    print(f"DONE Story 2: {out_root}")


if __name__ == "__main__":
    main()
