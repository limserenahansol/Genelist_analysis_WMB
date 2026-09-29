"""Prepare the tdTom status x Active/Passive factorial analysis.

Outputs animal-level pseudobulk counts and an explicit contrast plan. The Python
script never treats cells as biological replicates.
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

HERE = Path(__file__).resolve().parent
MIN_CELLS_PER_PSEUDOBULK = 20
PREFERRED_ANIMALS_PER_CONDITION = 3


def counts_matrix(adata):
    x = adata.layers["counts"] if "counts" in adata.layers else adata.X
    return x.toarray() if sparse.issparse(x) else np.asarray(x)


def gene_index(var_names, target):
    return {str(g).lower(): i for i, g in enumerate(var_names)}.get(target.lower())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_later_template.json"))
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = HERE / "outputs" / "factorial_tdtom_active_passive"
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for roi in cfg["rois"]:
        roi_name = roi["roi_name"]
        animal = roi.get("animal_id")
        condition = roi.get("condition")
        anatomy = roi.get("anatomy")
        if not animal or not condition:
            raise ValueError(f"{roi_name}: animal_id and condition are required")
        source = HERE / "outputs" / roi_name / f"{roi_name}_processed.h5ad"
        if not source.exists():
            raise FileNotFoundError(f"Run run_from_explorer.py first; missing {source}")
        adata = sc.read_h5ad(source)
        tdtom_idx = gene_index(adata.var_names, "tdTomato")
        if tdtom_idx is None:
            raise ValueError(f"{roi_name}: tdTomato is absent")
        x = counts_matrix(adata)
        tdtom = x[:, tdtom_idx]
        threshold = int(roi.get("tdtom_min_counts", 2))
        status = np.where(tdtom >= threshold, "positive", "negative")

        default_class = "reference_label" if (
            "reference_label" in adata.obs and adata.obs["reference_label"].notna().sum() >= 20
        ) else "module"
        class_col = roi.get("cell_class_column", default_class)
        if class_col not in adata.obs:
            raise ValueError(f"{roi_name}: cell class column {class_col!r} is absent")
        classes = adata.obs[class_col].astype("string").fillna("unassigned").astype(str).to_numpy()

        for cell_class in sorted(set(classes)):
            for reporter_status in ("negative", "positive"):
                mask = (classes == cell_class) & (status == reporter_status)
                if not mask.any():
                    continue
                summed = np.asarray(x[mask].sum(axis=0)).ravel()
                row = {
                    "roi_name": roi_name, "animal_id": animal, "condition": str(condition),
                    "anatomy": anatomy, "cell_class": cell_class,
                    "tdtom_status": reporter_status, "n_cells": int(mask.sum()),
                    "tdtom_threshold": threshold,
                }
                row.update(dict(zip(map(str, adata.var_names), map(float, summed))))
                rows.append(row)

    roi_pb = pd.DataFrame(rows)
    if roi_pb.empty:
        raise ValueError("No tdTomato pseudobulk samples were produced")
    meta_cols = [
        "roi_name", "animal_id", "condition", "anatomy", "cell_class",
        "tdtom_status", "n_cells", "tdtom_threshold",
    ]
    gene_cols = [c for c in roi_pb.columns if c not in meta_cols]
    roi_pb[gene_cols] = roi_pb[gene_cols].fillna(0)
    roi_pb = roi_pb.copy()

    group_cols = ["animal_id", "condition", "anatomy", "cell_class", "tdtom_status"]
    pb = roi_pb.groupby(group_cols, as_index=False)[gene_cols + ["n_cells"]].sum()
    pb["eligible_min_cells"] = pb["n_cells"] >= MIN_CELLS_PER_PSEUDOBULK
    pb["sample_id"] = (
        pb["animal_id"].astype(str) + "__" + pb["anatomy"].astype(str) + "__"
        + pb["cell_class"].astype(str).str.replace(r"\W+", "_", regex=True) + "__tdTom_"
        + pb["tdtom_status"].astype(str)
    )
    sample_meta = pb[
        ["sample_id", "animal_id", "condition", "anatomy", "cell_class",
         "tdtom_status", "n_cells", "eligible_min_cells"]
    ].copy()
    count_table = pb.set_index("sample_id")[gene_cols].T
    count_table.index.name = "gene"
    sample_meta.to_csv(out / "factorial_sample_metadata.csv", index=False)
    count_table.to_csv(out / "factorial_pseudobulk_counts_genes_by_sample.csv")
    roi_pb[meta_cols].to_csv(out / "roi_level_cell_counts.csv", index=False)

    workbook = Path(cfg.get(
        "panel_workbook", HERE.parent / "FINAL_Xenium_panel_ORBm_BMAp_298genes_FINAL.xlsx"
    ))
    if workbook.exists():
        panel = pd.read_excel(workbook, sheet_name="SHARED_PANEL_ORDER")
        panel = panel.dropna(subset=["gene", "block"])[["gene", "block"]].copy()
        panel["gene"] = panel["gene"].astype(str)
        block_lower = panel["block"].astype(str).str.lower()
        panel["analysis_category"] = np.select(
            [
                block_lower.str.contains("gpcr|receptor_map|cholinergic", regex=True),
                block_lower.str.contains("tf_identity", regex=True),
                block_lower.str.contains("activity|ieg|plasticity|morphine|circadian", regex=True),
                block_lower.str.contains("celltype|class_backbone|anchor|subtype|identity|separator", regex=True),
            ],
            ["GPCR", "TF", "activity_plasticity_state", "cell_identity"],
            default="other",
        )
        panel.drop_duplicates("gene").to_csv(out / "gene_categories.csv", index=False)

    contrast_rows = []
    for (anatomy, cell_class), sub in sample_meta.groupby(["anatomy", "cell_class"]):
        sub = sub[sub["eligible_min_cells"]]
        conditions = sorted(sub["condition"].unique())
        lower_to_original = {str(value).lower(): value for value in conditions}
        if {"active", "passive"}.issubset(lower_to_original):
            conditions = [lower_to_original["passive"], lower_to_original["active"]]
        if len(conditions) != 2:
            contrast_rows.append({
                "anatomy": anatomy, "cell_class": cell_class,
                "contrast": "factorial_design", "ready": False,
                "reason": f"need exactly two conditions; found {conditions}",
            })
            continue
        c0, c1 = conditions
        animal_status = (
            sub.groupby(["condition", "animal_id"])["tdtom_status"]
            .agg(lambda values: set(values))
        )
        paired = {
            condition: sum({"positive", "negative"}.issubset(statuses)
                           for (cond, _), statuses in animal_status.items() if cond == condition)
            for condition in conditions
        }
        by_status = {
            (condition, reporter): sub[
                (sub["condition"] == condition) & (sub["tdtom_status"] == reporter)
            ]["animal_id"].nunique()
            for condition in conditions for reporter in ("negative", "positive")
        }
        definitions = [
            (f"tdTom_positive_vs_negative_in_{c0}", paired[c0]),
            (f"tdTom_positive_vs_negative_in_{c1}", paired[c1]),
            (f"{c1}_vs_{c0}_within_tdTom_positive", min(by_status[(c0, "positive")], by_status[(c1, "positive")])),
            (f"{c1}_vs_{c0}_within_tdTom_negative", min(by_status[(c0, "negative")], by_status[(c1, "negative")])),
            (f"interaction_({c1}-{c0})x(positive-negative)", min(paired.values())),
        ]
        for name, n_min in definitions:
            contrast_rows.append({
                "anatomy": anatomy, "cell_class": cell_class, "contrast": name,
                "condition_reference": c0, "condition_comparison": c1,
                "minimum_animals_per_required_cell": int(n_min),
                "ready": bool(n_min >= PREFERRED_ANIMALS_PER_CONDITION),
                "reason": (
                    "ready for animal-level model" if n_min >= PREFERRED_ANIMALS_PER_CONDITION
                    else f"prefer >= {PREFERRED_ANIMALS_PER_CONDITION} animals in every required condition/status cell"
                ),
            })
    contrast_plan = pd.DataFrame(contrast_rows)
    contrast_plan.to_csv(out / "contrast_plan.csv", index=False)

    cell_counts = (
        sample_meta.groupby(["animal_id", "condition", "anatomy", "cell_class", "tdtom_status"], as_index=False)
        ["n_cells"].sum()
    )
    totals = cell_counts.groupby(
        ["animal_id", "condition", "anatomy", "tdtom_status"]
    )["n_cells"].transform("sum")
    cell_counts["composition_percent_within_status"] = 100 * cell_counts["n_cells"] / totals
    cell_counts.to_csv(out / "cell_type_composition_by_animal_status.csv", index=False)

    for anatomy, sub in cell_counts.groupby("anatomy"):
        positive = sub[sub["tdtom_status"] == "positive"]
        classes = (
            positive.groupby("cell_class")["composition_percent_within_status"]
            .mean().sort_values().index
        )
        conditions = sorted(positive["condition"].unique())
        fig, ax = plt.subplots(figsize=(max(8, 1.2 * len(conditions) + 5), max(4.8, 0.42 * len(classes) + 2)))
        offsets = np.linspace(-0.18, 0.18, max(1, len(conditions)))
        colors = plt.colormaps["Set1"].colors
        for offset, color, condition in zip(offsets, colors, conditions):
            cond = positive[positive["condition"] == condition]
            for i, cell_class in enumerate(classes):
                values = cond.loc[
                    cond["cell_class"] == cell_class, "composition_percent_within_status"
                ]
                if len(values):
                    ax.scatter(values, np.full(len(values), i + offset), color=color, s=28, alpha=0.75)
                    ax.plot(values.mean(), i + offset, marker="D", color="black", ms=5)
            ax.scatter([], [], color=color, label=condition)
        ax.set_yticks(range(len(classes)), classes)
        ax.set_xlabel("Composition among tdTom+ cells (%)")
        ax.set_ylabel("Existing cell class")
        ax.set_title(f"{anatomy}: tdTom+ cell-type composition by condition")
        ax.legend(title="Condition", frameon=False)
        ax.grid(axis="x", color="0.9")
        fig.tight_layout()
        fig.savefig(out / f"01_{anatomy}_tdtom_positive_composition_active_passive.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    summary = {
        "analysis_unit": "animal-level pseudobulk",
        "design": "condition x tdTom status, within anatomy and cell class",
        "minimum_cells_per_pseudobulk": MIN_CELLS_PER_PSEUDOBULK,
        "preferred_animals_per_condition": PREFERRED_ANIMALS_PER_CONDITION,
        "contrasts": [
            "tdTom+ vs tdTom- within Active",
            "tdTom+ vs tdTom- within Passive",
            "Active vs Passive within tdTom+",
            "Active vs Passive within tdTom-",
            "condition x tdTom interaction",
        ],
        "new_cell_type_rule": (
            "Do not define a new type from tdTom enrichment or state DE alone. Require a stable "
            "identity-gene cluster, poor fit to known reference types, multiple coherent identity "
            "markers, spatial coherence, and replication across independent animals."
        ),
    }
    (out / "analysis_plan.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"DONE factorial export: {out}")


if __name__ == "__main__":
    main()
