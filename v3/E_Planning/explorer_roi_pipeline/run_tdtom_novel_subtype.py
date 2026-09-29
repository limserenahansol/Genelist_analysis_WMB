"""Unbiased search for a reproducible tdTom-associated candidate subtype.

The reporter defines the comparison but never enters the identity clustering.
Cells are first restricted to an established parent cell type. Candidate subtype
status requires an unsupervised identity-gene cluster, reproducible non-state
markers, tdTom enrichment across animals, and resolution stability.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
from scipy import sparse
from sklearn.metrics import roc_auc_score

from run_from_explorer import STATE_REPORTER_GENES

HERE = Path(__file__).resolve().parent
SEED = 0
DEFAULT_TDTOM_THRESHOLD = 2
MIN_CELLS_PER_STATUS_ANIMAL = 10
MIN_PARENT_CELLS = 80
MIN_CLUSTER_CELLS_PER_ANIMAL = 10
MIN_ANIMALS_CANDIDATE = 3
ANIMAL_CONSISTENCY = 0.75
MARKER_LOG2FC_MIN = 0.5
MARKER_DETECTION_DIFF_MIN = 0.15
CLUSTER_LOG2_ODDS_MIN = 1.0
RESOLUTION_RECOVERY_MIN = 0.5
LOMO_AUC_MIN = 0.65
RESOLUTIONS = (0.5, 1.0, 1.5)


def dense(matrix):
    return matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "group"


def gene_index(var_names, target):
    return {str(g).lower(): i for i, g in enumerate(var_names)}.get(target.lower())


def log_normalize(counts):
    counts = counts.astype(float, copy=False)
    totals = counts.sum(axis=1, keepdims=True)
    scaled = counts / np.maximum(totals, 1.0) * 1e4
    return np.log1p(scaled)


def per_animal_effects(counts, positive, animals, genes, min_per_status=MIN_CELLS_PER_STATUS_ANIMAL):
    rows = []
    for animal in sorted(pd.unique(animals.astype(str))):
        in_animal = animals.astype(str) == animal
        pos = in_animal & positive
        neg = in_animal & ~positive
        if pos.sum() < min_per_status or neg.sum() < min_per_status:
            continue
        xp, xn = counts[pos], counts[neg]
        mean_p, mean_n = xp.mean(axis=0), xn.mean(axis=0)
        det_p, det_n = (xp > 0).mean(axis=0), (xn > 0).mean(axis=0)
        for index, gene in enumerate(genes):
            rows.append({
                "animal_id": animal,
                "gene": gene,
                "n_positive": int(pos.sum()),
                "n_negative": int(neg.sum()),
                "log2_mean_ratio": float(np.log2((mean_p[index] + 0.1) / (mean_n[index] + 0.1))),
                "detection_difference": float(det_p[index] - det_n[index]),
            })
    return pd.DataFrame(rows)


def aggregate_effects(effect_df, min_animals, excluded_lower):
    columns = [
        "gene", "n_animals", "median_log2_mean_ratio", "median_detection_difference",
        "positive_direction_fraction", "stable_identity_marker",
    ]
    if effect_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for gene, sub in effect_df.groupby("gene", sort=False):
        n_animals = sub["animal_id"].nunique()
        med_lfc = float(sub["log2_mean_ratio"].median())
        med_det = float(sub["detection_difference"].median())
        direction = float((sub["log2_mean_ratio"] > 0).mean())
        stable = (
            n_animals >= min_animals
            and gene.lower() not in excluded_lower
            and med_lfc >= MARKER_LOG2FC_MIN
            and med_det >= MARKER_DETECTION_DIFF_MIN
            and direction >= ANIMAL_CONSISTENCY
        )
        rows.append({
            "gene": gene,
            "n_animals": int(n_animals),
            "median_log2_mean_ratio": med_lfc,
            "median_detection_difference": med_det,
            "positive_direction_fraction": direction,
            "stable_identity_marker": bool(stable),
        })
    return pd.DataFrame(rows).sort_values(
        ["stable_identity_marker", "median_log2_mean_ratio", "median_detection_difference"],
        ascending=[False, False, False],
    )


def run_leiden(adata, resolution, key):
    try:
        sc.tl.leiden(adata, resolution=resolution, random_state=SEED, flavor="igraph", key_added=key)
    except (ImportError, ModuleNotFoundError):
        sc.tl.leiden(adata, resolution=resolution, random_state=SEED, flavor="leidenalg", key_added=key)


def cluster_resolution_recovery(primary, alternate, cluster):
    """Recover a primary cluster after allowed merge/split changes.

    At finer resolution, one biological cluster may split into several pure
    child clusters. Their union is compared with the primary cluster. If no
    alternate cluster has at least 80% of its cells inside the target, fall
    back to the best single-cluster Jaccard score.
    """
    target = np.asarray(primary).astype(str) == str(cluster)
    best = 0.0
    recovered = np.zeros_like(target, dtype=bool)
    for other in pd.unique(np.asarray(alternate).astype(str)):
        candidate = np.asarray(alternate).astype(str) == other
        intersection = np.logical_and(target, candidate).sum()
        if candidate.sum() and intersection / candidate.sum() >= 0.8:
            recovered |= candidate
        union = np.logical_or(target, candidate).sum()
        if union:
            best = max(best, float(intersection / union))
    recovered_union = np.logical_or(target, recovered).sum()
    if recovered_union:
        best = max(best, float(np.logical_and(target, recovered).sum() / recovered_union))
    return best


def load_reporter_data(config, processed_root):
    datasets = []
    missing_reporter = []
    for roi in config["rois"]:
        roi_name = roi["roi_name"]
        source = processed_root / roi_name / f"{roi_name}_processed.h5ad"
        if not source.exists():
            raise FileNotFoundError(f"Run run_from_explorer.py first; missing {source}")
        original = sc.read_h5ad(source)
        idx = gene_index(original.var_names, "tdTomato")
        if idx is None:
            missing_reporter.append(roi_name)
            continue
        counts = dense(original.layers["counts"] if "counts" in original.layers else original.X)
        default_class = "reference_label" if (
            "reference_label" in original.obs
            and original.obs["reference_label"].notna().sum() >= 20
        ) else "module"
        class_col = roi.get("cell_class_column", default_class)
        if class_col not in original.obs:
            raise ValueError(f"{roi_name}: cell class column {class_col!r} is absent")
        threshold = int(roi.get("tdtom_min_counts", DEFAULT_TDTOM_THRESHOLD))
        obs = original.obs.copy()
        obs["roi_name"] = roi_name
        obs["animal_id"] = str(roi.get("animal_id", "missing_animal"))
        obs["condition"] = str(roi.get("condition", "unspecified"))
        obs["anatomy"] = str(roi.get("anatomy", "unspecified"))
        obs["section_id"] = str(roi.get("section_id", roi_name))
        obs["parent_cell_type"] = original.obs[class_col].astype("string").fillna("unassigned").astype(str)
        obs["tdTomato_counts"] = counts[:, idx]
        obs["tdTom_positive"] = counts[:, idx] >= threshold
        item = ad.AnnData(X=sparse.csr_matrix(counts), obs=obs, var=pd.DataFrame(index=original.var_names.astype(str)))
        item.layers["counts"] = item.X.copy()
        datasets.append(item)
    if not datasets:
        return None, missing_reporter
    combined = ad.concat(datasets, join="inner", merge="same", index_unique="::")
    combined.var_names_make_unique()
    return combined, missing_reporter


def process_parent_group(group, anatomy, parent, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    counts = dense(group.layers["counts"])
    genes = np.asarray(group.var_names.astype(str))
    animals = group.obs["animal_id"].astype(str).to_numpy()
    tdtom_positive = group.obs["tdTom_positive"].astype(bool).to_numpy()
    excluded_lower = {gene.lower() for gene in STATE_REPORTER_GENES} | {"tdtomato", "icre", "cre"}
    n_animals = len(pd.unique(animals))
    required_consistent_animals = max(
        MIN_ANIMALS_CANDIDATE,
        int(math.ceil(ANIMAL_CONSISTENCY * n_animals)),
    )

    tdtom_effects = per_animal_effects(counts, tdtom_positive, animals, genes)
    tdtom_effects.to_csv(output_dir / "tdtom_vs_negative_effects_by_animal.csv", index=False)
    stable_tdtom = aggregate_effects(tdtom_effects, required_consistent_animals, excluded_lower)
    stable_tdtom.to_csv(output_dir / "stable_tdtom_identity_markers.csv", index=False)

    detected = np.asarray((counts > 0).sum(axis=0)).ravel() >= 5
    identity_mask = detected & np.array([gene.lower() not in excluded_lower for gene in genes])
    if identity_mask.sum() < 5:
        raise ValueError(f"{anatomy}/{parent}: fewer than five identity genes remain")
    identity = ad.AnnData(
        X=sparse.csr_matrix(counts[:, identity_mask]),
        obs=group.obs.copy(),
        var=pd.DataFrame(index=genes[identity_mask]),
    )
    sc.pp.normalize_total(identity, target_sum=1e4)
    sc.pp.log1p(identity)
    identity.X = dense(identity.X)
    sc.pp.scale(identity, max_value=10)
    n_pcs = min(20, identity.n_vars - 1, identity.n_obs - 1)
    sc.tl.pca(identity, n_comps=n_pcs, random_state=SEED)
    sc.pp.neighbors(identity, n_neighbors=min(15, identity.n_obs - 1), n_pcs=n_pcs, random_state=SEED)
    for resolution in RESOLUTIONS:
        run_leiden(identity, resolution, f"identity_leiden_{resolution:g}")
    sc.tl.umap(identity, random_state=SEED)

    primary = identity.obs["identity_leiden_1"].astype(str).to_numpy()
    alternate_low = identity.obs["identity_leiden_0.5"].astype(str).to_numpy()
    alternate_high = identity.obs["identity_leiden_1.5"].astype(str).to_numpy()
    cluster_enrichment_rows = []
    candidate_rows = []
    cluster_marker_tables = []
    for cluster in sorted(pd.unique(primary)):
        in_cluster = primary == cluster
        for animal in sorted(pd.unique(animals)):
            in_animal = animals == animal
            cluster_mask = in_animal & in_cluster
            rest_mask = in_animal & ~in_cluster
            if cluster_mask.sum() < MIN_CLUSTER_CELLS_PER_ANIMAL or rest_mask.sum() < MIN_CLUSTER_CELLS_PER_ANIMAL:
                continue
            a = int(np.sum(cluster_mask & tdtom_positive))
            b = int(np.sum(cluster_mask & ~tdtom_positive))
            c = int(np.sum(rest_mask & tdtom_positive))
            d = int(np.sum(rest_mask & ~tdtom_positive))
            log2_odds = float(np.log2(((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))))
            cluster_enrichment_rows.append({
                "cluster": cluster,
                "animal_id": animal,
                "n_cluster": int(cluster_mask.sum()),
                "n_rest": int(rest_mask.sum()),
                "pct_tdtom_cluster": 100 * a / max(1, a + b),
                "pct_tdtom_rest": 100 * c / max(1, c + d),
                "log2_tdtom_odds_cluster_vs_rest": log2_odds,
            })

        marker_effects = per_animal_effects(counts, in_cluster, animals, genes)
        marker_summary = aggregate_effects(
            marker_effects, required_consistent_animals, excluded_lower
        )
        marker_summary.insert(0, "cluster", cluster)
        cluster_marker_tables.append(marker_summary)
        stable_markers = marker_summary.loc[
            marker_summary["stable_identity_marker"], "gene"
        ].tolist()
        enrich = pd.DataFrame(cluster_enrichment_rows)
        enrich = enrich[enrich["cluster"] == cluster] if not enrich.empty else enrich
        animals_present = int(enrich["animal_id"].nunique()) if not enrich.empty else 0
        median_log2_odds = float(enrich["log2_tdtom_odds_cluster_vs_rest"].median()) if not enrich.empty else np.nan
        positive_fraction = float((enrich["log2_tdtom_odds_cluster_vs_rest"] > 0).mean()) if not enrich.empty else np.nan
        low_recovery = cluster_resolution_recovery(primary, alternate_low, cluster)
        high_recovery = cluster_resolution_recovery(primary, alternate_high, cluster)
        min_recovery = min(low_recovery, high_recovery)
        meets = (
            animals_present >= required_consistent_animals
            and median_log2_odds >= CLUSTER_LOG2_ODDS_MIN
            and positive_fraction >= ANIMAL_CONSISTENCY
            and len(stable_markers) >= 2
            and min_recovery >= RESOLUTION_RECOVERY_MIN
        )
        candidate_rows.append({
            "anatomy": anatomy,
            "parent_cell_type": parent,
            "cluster": cluster,
            "n_cells": int(in_cluster.sum()),
            "animals_present_with_min_cells": animals_present,
            "median_log2_tdtom_odds": median_log2_odds,
            "positive_odds_animal_fraction": positive_fraction,
            "cluster_recovery_vs_resolution_0.5": low_recovery,
            "cluster_recovery_vs_resolution_1.5": high_recovery,
            "n_stable_identity_markers": len(stable_markers),
            "top_stable_identity_markers": ";".join(stable_markers[:10]),
            "candidate_novel_subtype": bool(meets),
        })

    enrichment_df = pd.DataFrame(cluster_enrichment_rows)
    enrichment_df.to_csv(output_dir / "unbiased_cluster_tdtom_enrichment_by_animal.csv", index=False)
    cluster_markers = pd.concat(cluster_marker_tables, ignore_index=True) if cluster_marker_tables else pd.DataFrame()
    cluster_markers.to_csv(output_dir / "unbiased_cluster_stable_markers.csv", index=False)
    candidates = pd.DataFrame(candidate_rows)

    normalized = log_normalize(counts)
    lomo_rows = []
    for held_out in sorted(pd.unique(animals)):
        train = tdtom_effects[tdtom_effects["animal_id"] != held_out]
        n_train_animals = train["animal_id"].nunique()
        min_train = max(2, int(math.ceil(ANIMAL_CONSISTENCY * n_train_animals)))
        train_markers = aggregate_effects(train, min_train, excluded_lower)
        marker_names = train_markers.loc[train_markers["stable_identity_marker"], "gene"].tolist()
        held = animals == held_out
        held_status = tdtom_positive[held]
        if len(marker_names) < 2 or len(np.unique(held_status)) < 2:
            auc = np.nan
        else:
            marker_indices = [int(np.where(genes == gene)[0][0]) for gene in marker_names]
            score = normalized[held][:, marker_indices].mean(axis=1)
            auc = float(roc_auc_score(held_status, score))
        lomo_rows.append({
            "held_out_animal": held_out,
            "n_train_animals": int(n_train_animals),
            "n_markers_selected_without_held_out": len(marker_names),
            "marker_score_auc_for_tdtom_in_held_out": auc,
            "markers": ";".join(marker_names[:20]),
        })
    lomo = pd.DataFrame(lomo_rows)
    lomo.to_csv(output_dir / "leave_one_mouse_out_marker_validation.csv", index=False)
    evaluable_lomo = lomo["marker_score_auc_for_tdtom_in_held_out"].notna()
    n_lomo_evaluable = int(evaluable_lomo.sum())
    median_lomo_auc = float(
        lomo.loc[evaluable_lomo, "marker_score_auc_for_tdtom_in_held_out"].median()
    ) if n_lomo_evaluable else np.nan
    lomo_pass_fraction = float(
        (lomo.loc[evaluable_lomo, "marker_score_auc_for_tdtom_in_held_out"] >= LOMO_AUC_MIN).mean()
    ) if n_lomo_evaluable else np.nan
    lomo_pass = (
        n_lomo_evaluable >= required_consistent_animals
        and median_lomo_auc >= LOMO_AUC_MIN
        and lomo_pass_fraction >= ANIMAL_CONSISTENCY
    )
    candidates["n_leave_one_mouse_out_evaluable"] = n_lomo_evaluable
    candidates["median_leave_one_mouse_out_auc"] = median_lomo_auc
    candidates["leave_one_mouse_out_auc_pass_fraction"] = lomo_pass_fraction
    candidates["leave_one_mouse_out_validation_pass"] = bool(lomo_pass)
    candidates["candidate_novel_subtype"] = (
        candidates["candidate_novel_subtype"] & bool(lomo_pass)
    )
    candidates.to_csv(output_dir / "candidate_clusters.csv", index=False)

    assignments = identity.obs[[
        "roi_name", "animal_id", "condition", "anatomy", "section_id",
        "parent_cell_type", "tdTomato_counts", "tdTom_positive",
        "identity_leiden_0.5", "identity_leiden_1", "identity_leiden_1.5",
    ]].copy()
    assignments.to_csv(output_dir / "cell_assignments.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    umap = identity.obsm["X_umap"]
    axes[0].scatter(umap[:, 0], umap[:, 1], c=pd.Categorical(primary).codes, s=7, cmap="tab20", linewidths=0)
    axes[0].set_title("Unbiased identity-gene clusters")
    axes[1].scatter(umap[~tdtom_positive, 0], umap[~tdtom_positive, 1], c="0.82", s=6, linewidths=0, label="tdTom−")
    axes[1].scatter(umap[tdtom_positive, 0], umap[tdtom_positive, 1], c="#C74334", s=9, linewidths=0, label="tdTom+")
    axes[1].set_title("Reporter overlaid after clustering")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.set_xlabel("UMAP-1")
        ax.set_ylabel("UMAP-2")
    fig.suptitle(f"{anatomy} · {parent}: unbiased candidate-subtype search", fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_dir / "01_unbiased_clusters_and_reporter_overlay.png", dpi=200)
    plt.close(fig)

    stable_rows = stable_tdtom[stable_tdtom["stable_identity_marker"]].head(15)
    if not stable_rows.empty and not tdtom_effects.empty:
        matrix = tdtom_effects[tdtom_effects["gene"].isin(stable_rows["gene"])].pivot(
            index="gene", columns="animal_id", values="log2_mean_ratio"
        ).reindex(stable_rows["gene"])
        fig, ax = plt.subplots(figsize=(max(6, 1.1 * matrix.shape[1] + 3), max(3.5, 0.38 * matrix.shape[0] + 2)))
        image = ax.imshow(matrix, cmap="coolwarm", aspect="auto", vmin=-np.nanmax(np.abs(matrix.to_numpy())), vmax=np.nanmax(np.abs(matrix.to_numpy())))
        ax.set_xticks(range(matrix.shape[1]), matrix.columns, rotation=30, ha="right")
        ax.set_yticks(range(matrix.shape[0]), matrix.index)
        ax.set_title("Stable tdTom-associated identity-marker effects by mouse")
        fig.colorbar(image, ax=ax, label="log2 mean ratio: tdTom+ / tdTom−")
        fig.tight_layout()
        fig.savefig(output_dir / "02_stable_marker_reproduction_by_mouse.png", dpi=200)
        plt.close(fig)

    n_candidate = int(candidates["candidate_novel_subtype"].sum())
    n_stable_tdtom = int(stable_tdtom["stable_identity_marker"].sum())
    if n_animals < MIN_ANIMALS_CANDIDATE:
        decision = "insufficient_independent_animals"
    elif n_candidate:
        decision = "candidate_novel_subtype_requires_external_validation"
    elif n_stable_tdtom >= 2:
        decision = "reporter_associated_program_without_reproducible_unbiased_cluster"
    else:
        decision = "no_reproducible_reporter_subtype_evidence"
    return {
        "anatomy": anatomy,
        "parent_cell_type": parent,
        "n_cells": int(group.n_obs),
        "n_animals": n_animals,
        "n_tdtom_positive": int(tdtom_positive.sum()),
        "n_tdtom_negative": int((~tdtom_positive).sum()),
        "n_stable_tdtom_identity_markers": n_stable_tdtom,
        "n_candidate_unbiased_clusters": n_candidate,
        "decision": decision,
        "interpretation": "candidate only; never confirmed novel type without independent reference/spatial validation",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "rois_later_template.json"))
    parser.add_argument("--processed-root", default=str(HERE / "outputs"))
    parser.add_argument("--output-root", default=str(HERE / "outputs" / "story2_novel_subtype"))
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    processed_root = Path(args.processed_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for stale in ["SKIPPED.md", "decision_summary.csv"]:
        (output_root / stale).unlink(missing_ok=True)

    combined, missing_reporter = load_reporter_data(config, processed_root)
    if combined is None:
        note = (
            "SKIPPED: tdTomato is absent from every processed matrix. Run this module on the "
            "reporter-aware production panel. Missing reporter ROIs: " + ", ".join(missing_reporter) + "\n"
        )
        (output_root / "SKIPPED.md").write_text(note, encoding="utf-8")
        print(note.strip())
        return

    decisions = []
    for (anatomy, parent), indices in combined.obs.groupby(
        ["anatomy", "parent_cell_type"], observed=True
    ).indices.items():
        group = combined[np.asarray(indices)].copy()
        status = group.obs["tdTom_positive"].astype(bool)
        if group.n_obs < MIN_PARENT_CELLS or status.sum() < 20 or (~status).sum() < 20:
            continue
        destination = output_root / safe_name(anatomy) / safe_name(parent)
        decisions.append(process_parent_group(group, str(anatomy), str(parent), destination))

    decision_df = pd.DataFrame(decisions)
    decision_df.to_csv(output_root / "decision_summary.csv", index=False)
    if decision_df.empty:
        note = "No parent cell type had enough tdTom+ and tdTom− cells for subtype analysis.\n"
        (output_root / "SKIPPED.md").write_text(note, encoding="utf-8")
        print(note.strip())
    else:
        print(f"DONE: {len(decision_df)} parent cell-type analyses -> {output_root}")


if __name__ == "__main__":
    main()
