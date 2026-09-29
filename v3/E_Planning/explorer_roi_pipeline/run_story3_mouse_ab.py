"""Story 3: animal-level composition and pseudobulk export.

Cells are summarized within animal before any comparison. This script does not
turn individual cells into biological replicates.
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


def counts_matrix(adata):
    x = adata.layers["counts"] if "counts" in adata.layers else adata.X
    return x.toarray() if sparse.issparse(x) else np.asarray(x)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_current.json"))
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = HERE / "outputs" / "story3_mouse_ab"
    out.mkdir(parents=True, exist_ok=True)

    composition_rows = []
    pseudobulk_rows = []

    for roi in cfg["rois"]:
        roi_name = roi["roi_name"]
        animal = roi.get("animal_id")
        anatomy = roi.get("anatomy")
        condition = roi.get("condition", "unspecified")
        if not animal:
            raise ValueError(f"{roi_name}: animal_id is required")
        source = HERE / "outputs" / roi_name / f"{roi_name}_processed.h5ad"
        if not source.exists():
            raise FileNotFoundError(f"Run run_from_explorer.py first; missing {source}")
        adata = sc.read_h5ad(source)
        default_class = "reference_label" if (
            "reference_label" in adata.obs and adata.obs["reference_label"].notna().sum() >= 20
        ) else "module"
        class_col = roi.get("cell_class_column", default_class)
        if class_col not in adata.obs:
            raise ValueError(f"{roi_name}: {class_col!r} is absent")
        classes = adata.obs[class_col].astype("string").fillna("unassigned").astype(str)
        x = counts_matrix(adata)
        genes = list(map(str, adata.var_names))

        for cell_class in sorted(set(classes)):
            m = classes.to_numpy() == cell_class
            composition_rows.append({
                "roi_name": roi_name, "animal_id": animal, "condition": condition,
                "anatomy": anatomy, "cell_class": cell_class, "n_cells": int(m.sum()),
            })
            summed = np.asarray(x[m].sum(axis=0)).ravel()
            row = {
                "roi_name": roi_name, "animal_id": animal, "condition": condition,
                "anatomy": anatomy, "cell_class": cell_class, "n_cells": int(m.sum()),
            }
            row.update(dict(zip(genes, map(float, summed))))
            pseudobulk_rows.append(row)

    comp_roi = pd.DataFrame(composition_rows)
    pb_roi = pd.DataFrame(pseudobulk_rows)
    if comp_roi.empty:
        raise ValueError("No processed ROIs were found")

    # Multiple ROIs from one animal are nested technical/spatial samples.
    group_cols = ["animal_id", "condition", "anatomy", "cell_class"]
    comp = comp_roi.groupby(group_cols, as_index=False)["n_cells"].sum()
    totals = comp.groupby(["animal_id", "condition", "anatomy"])["n_cells"].transform("sum")
    comp["fraction"] = comp["n_cells"] / totals
    comp["percent"] = 100 * comp["fraction"]
    comp.to_csv(out / "composition_by_animal.csv", index=False)

    meta_cols = ["roi_name", "animal_id", "condition", "anatomy", "cell_class", "n_cells"]
    gene_cols = [c for c in pb_roi.columns if c not in meta_cols]
    # A gene filtered for detection in one ROI is still on the assay panel; its
    # missing pseudobulk entry is zero, not an incompatible panel.
    pb_roi[gene_cols] = pb_roi[gene_cols].fillna(0)
    pb_roi = pb_roi.copy()
    pb = pb_roi.groupby(group_cols, as_index=False)[gene_cols + ["n_cells"]].sum()
    sample_ids = (
        pb["animal_id"].astype(str) + "__" + pb["anatomy"].astype(str)
        + "__" + pb["cell_class"].astype(str)
    )
    sample_meta = pb[group_cols + ["n_cells"]].copy()
    sample_meta.insert(0, "sample_id", sample_ids)
    count_table = pb[gene_cols].T
    count_table.columns = sample_ids
    count_table.index.name = "gene"
    sample_meta.to_csv(out / "pseudobulk_sample_metadata.csv", index=False)
    count_table.to_csv(out / "pseudobulk_counts_genes_by_sample.csv")

    for anatomy, sub in comp.groupby("anatomy"):
        pivot = sub.pivot_table(
            index=["animal_id", "condition"], columns="cell_class",
            values="percent", aggfunc="sum", fill_value=0,
        )
        fig, ax = plt.subplots(figsize=(max(7, 0.8 * len(pivot) + 3), 5))
        pivot.plot(kind="bar", stacked=True, ax=ax, colormap="tab20", width=0.75)
        ax.set_ylabel("Cells (%)")
        ax.set_xlabel("Animal (condition)")
        ax.set_ylim(0, 100)
        ax.set_title(f"{anatomy}: composition summarized per animal")
        ax.legend(title="Cell class", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False)
        ax.grid(axis="y", color="0.9")
        fig.tight_layout()
        fig.savefig(out / f"01_{anatomy}_composition_by_animal.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    design = []
    for anatomy, sub in comp[["animal_id", "condition", "anatomy"]].drop_duplicates().groupby("anatomy"):
        n_by_condition = sub.groupby("condition")["animal_id"].nunique().to_dict()
        specified = set(n_by_condition) != {"unspecified"}
        ready = specified and len(n_by_condition) >= 2 and min(n_by_condition.values()) >= 3
        design.append({
            "anatomy": anatomy,
            "animals_by_condition": n_by_condition,
            "inference_ready_preferred": ready,
            "criterion": "at least 3 animals per condition; same anatomy; animal is the unit",
        })
    (out / "design_status.json").write_text(json.dumps(design, indent=2), encoding="utf-8")

    if not any(d["inference_ready_preferred"] for d in design):
        note = (
            "Descriptive outputs were produced. Do not run cell-level tests. "
            "A treatment/group comparison needs a condition field and preferably at least "
            "3 independent animals per condition within the same anatomy. Feed the exported "
            "pseudobulk matrix and sample metadata to edgeR/DESeq2 with an animal-level design.\n"
        )
        (out / "DESCRIPTIVE_ONLY.md").write_text(note, encoding="utf-8")
        print("DONE Story 3 descriptive export; design is not ready for inferential testing")
    else:
        note = (
            "Animal-level pseudobulk counts and metadata are ready for edgeR/DESeq2. "
            "Include condition and relevant batch terms; analyze each anatomy and cell class separately.\n"
        )
        (out / "READY_FOR_PSEUDOBULK_MODEL.md").write_text(note, encoding="utf-8")
        print("DONE Story 3 animal-level export")


if __name__ == "__main__":
    main()
