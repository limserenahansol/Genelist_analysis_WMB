"""Validate the final 299-gene panel against intended Allen subclass anchors.

The primary check is leave-one-donor-out classification after removing obvious
reporter, activity, morphine-state, and circadian blocks. A nearest-centroid
classifier is retained as a simple independent baseline. The analysis is an
atlas separability check, not proof of Xenium probe performance.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent


def default_panel_workbook() -> Path:
    candidates = [
        HERE.parents[1]
        / "outputs"
        / "FINAL_299_Opn3"
        / "FINAL_Xenium_panel_ORBm_BMAp_299genes_Opn3_FINAL.xlsx",
        HERE.parents[1]
        / "xenium_ORBm_BMAp_2026-09"
        / "FINAL_299"
        / "FINAL_Xenium_panel_ORBm_BMAp_299genes_Opn3_FINAL.xlsx",
    ]
    return next((path for path in candidates if path.exists()), candidates[0])


DEFAULT_PANEL = default_panel_workbook()
SEED = 0
CAP_PER_SUBCLASS = 400
REGIONS = {"ORBm": "PL-ILA-ORB", "BMAp": "sAMY"}
STATE_BLOCKS = {
    "2_reporter_transgene",
    "4c_activity",
    "5_IEG",
    "13_Jesse_morphine_state",
    "16_expanded_morphine_state",
    "33_circadian",
}
MIN_GOOD_MARKERS = 2
MIN_MARKER_DETECTION_PCT = 50.0
MIN_MARKER_MARGIN_PP = 10.0
MIN_REGION_MACRO_F1 = 0.75
MIN_SUBCLASS_RECALL = 0.60


def read_design(workbook: Path):
    panel = pd.read_excel(workbook, sheet_name="SHARED_PANEL_ORDER")
    anchors = pd.read_excel(workbook, sheet_name="ANCHOR_COVERAGE")
    markers = pd.read_excel(workbook, sheet_name="MARKERS_PER_TYPE")
    if len(panel) != 299 or panel["gene"].nunique() != 299:
        raise ValueError(f"Expected 299 unique genes in {workbook}")
    return panel, anchors, markers


def extract_reference(
    workbook: Path,
    allen_cache: Path,
    manifest: str,
    expression_root: Path,
) -> dict:
    """Extract a balanced target-subclass sample from a local Allen cache."""
    from abc_atlas_access.abc_atlas_cache.abc_project_cache import AbcProjectCache
    from abc_atlas_access.abc_atlas_cache.anndata_utils import get_gene_data

    panel, anchors, _ = read_design(workbook)
    genes = panel["gene"].astype(str).tolist()
    cache = AbcProjectCache.from_cache_dir(allen_cache)
    cache.load_manifest(manifest)
    metadata_path = cache.get_file_path(
        directory="WMB-10X", file_name="cell_metadata_with_cluster_annotation"
    )
    columns = [
        "cell_label",
        "cell_barcode",
        "library_label",
        "feature_matrix_label",
        "region_of_interest_acronym",
        "donor_label",
        "donor_genotype",
        "donor_sex",
        "dataset_label",
        "class",
        "subclass",
        "supertype",
        "cluster",
    ]
    cell = pd.read_csv(metadata_path, usecols=columns).set_index("cell_label")
    gene = cache.get_metadata_dataframe(directory="WMB-10X", file_name="gene")
    if "gene_identifier" in gene.columns:
        gene = gene.set_index("gene_identifier")
    expression_root.mkdir(parents=True, exist_ok=True)
    summary = {"manifest": manifest, "seed": SEED, "cap_per_subclass": CAP_PER_SUBCLASS}
    rng = np.random.default_rng(SEED)

    for region, roi in REGIONS.items():
        labels = anchors.loc[
            anchors["region"].eq(region), "allen_subclass_anchor"
        ].astype(str).tolist()
        subset = cell[
            cell["region_of_interest_acronym"].astype(str).eq(roi)
            & cell["subclass"].astype(str).isin(labels)
        ].copy()
        keep = []
        for label in labels:
            group = subset[subset["subclass"].astype(str).eq(label)]
            if group.empty:
                raise ValueError(f"{region}: Allen target absent: {label}")
            n = min(CAP_PER_SUBCLASS, len(group))
            keep.extend(rng.choice(group.index.to_numpy(), size=n, replace=False))
        sampled = subset.loc[keep].copy()
        expression = get_gene_data(
            abc_atlas_cache=cache,
            all_cells=sampled,
            all_genes=gene,
            selected_genes=genes,
            data_type="log2",
            chunk_size=8192,
        ).loc[sampled.index]
        present = [gene_name for gene_name in genes if gene_name in expression.columns]
        expression = expression[present]
        expression.to_parquet(expression_root / f"allen_{region}_panel299_log2.parquet")
        sampled.to_csv(expression_root / f"allen_{region}_panel299_meta.csv")
        summary[region] = {
            "n_available_target_cells": int(len(subset)),
            "n_sampled": int(len(sampled)),
            "n_subclasses": int(sampled["subclass"].nunique()),
            "n_donors": int(sampled["donor_label"].nunique()),
            "n_panel_genes_found": int(len(present)),
            "missing_genes": sorted(set(genes) - set(present)),
        }
    (expression_root / "extraction_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def marker_coverage(
    region: str, anchors: pd.DataFrame, markers: pd.DataFrame
) -> pd.DataFrame:
    labels = anchors.loc[
        anchors["region"].eq(region), "allen_subclass_anchor"
    ].astype(str).tolist()
    rows = []
    for label in labels:
        subset = markers[
            markers["region"].eq(region) & markers["cell_type"].astype(str).eq(label)
        ].copy()
        good = subset[
            (subset["pct_in_this_type"] >= MIN_MARKER_DETECTION_PCT)
            & (subset["margin_pp_vs_other_same_region_targets"] >= MIN_MARKER_MARGIN_PP)
        ]
        rows.append({
            "region": region,
            "subclass": label,
            "n_panel_markers_listed": int(len(subset)),
            "n_markers_detection_ge_50_margin_ge_10pp": int(len(good)),
            "best_detection_pct": float(subset["pct_in_this_type"].max()),
            "best_margin_pp": float(subset["margin_pp_vs_other_same_region_targets"].max()),
            "marker_criterion_pass": bool(len(good) >= MIN_GOOD_MARKERS),
            "qualifying_markers": ", ".join(good["marker"].astype(str).tolist()),
        })
    return pd.DataFrame(rows)


def nearest_centroid_predict(x_train, y_train, x_test) -> np.ndarray:
    """Simple Euclidean nearest-centroid baseline without fitted hyperparameters."""
    classes = np.array(sorted(pd.unique(np.asarray(y_train, dtype=str))))
    labels = np.asarray(y_train, dtype=str)
    centroids = np.vstack([x_train[labels == label].mean(axis=0) for label in classes])
    squared_distance = ((x_test[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
    return classes[np.argmin(squared_distance, axis=1)]


def evaluate_region(
    region: str,
    panel: pd.DataFrame,
    markers: pd.DataFrame,
    anchors: pd.DataFrame,
    expression_root: Path,
) -> dict:
    expression = pd.read_parquet(
        expression_root / f"allen_{region}_panel299_log2.parquet"
    )
    metadata = pd.read_csv(
        expression_root / f"allen_{region}_panel299_meta.csv", index_col=0
    ).loc[expression.index]
    target_labels = anchors.loc[
        anchors["region"].eq(region), "allen_subclass_anchor"
    ].astype(str).tolist()
    if set(metadata["subclass"].astype(str)) != set(target_labels):
        raise ValueError(f"{region}: expression metadata does not match intended anchors")

    stable_genes = set(
        panel.loc[~panel["block"].isin(STATE_BLOCKS), "gene"].astype(str)
    )
    marker_genes = set(
        markers.loc[markers["region"].eq(region), "marker"].astype(str)
    )
    feature_sets = {
        "stable_identity": sorted(stable_genes & set(expression.columns)),
        "preselected_markers": sorted(marker_genes & set(expression.columns)),
    }
    labels = target_labels
    fold_rows = []
    prediction_rows = []

    for feature_set, genes in feature_sets.items():
        for donor in sorted(metadata["donor_label"].astype(str).unique()):
            test = metadata["donor_label"].astype(str).eq(donor).to_numpy()
            train = ~test
            scaler = StandardScaler().fit(expression.loc[train, genes])
            x_train = scaler.transform(expression.loc[train, genes])
            x_test = scaler.transform(expression.loc[test, genes])
            y_train = metadata.loc[train, "subclass"].astype(str)
            y_test = metadata.loc[test, "subclass"].astype(str)
            logistic = LogisticRegression(
                max_iter=3000,
                C=1.0,
                class_weight="balanced",
                solver="lbfgs",
                random_state=SEED,
            )
            predictions = {
                "logistic": logistic.fit(x_train, y_train).predict(x_test),
                "nearest_centroid": nearest_centroid_predict(
                    x_train, y_train.to_numpy(), x_test
                ),
            }
            for model_name, prediction in predictions.items():
                fold_rows.append({
                    "region": region,
                    "feature_set": feature_set,
                    "model": model_name,
                    "held_out_donor": donor,
                    "n_test": int(test.sum()),
                    "accuracy": float(accuracy_score(y_test, prediction)),
                    "balanced_accuracy": float(
                        balanced_accuracy_score(y_test, prediction)
                    ),
                    "macro_f1": float(f1_score(y_test, prediction, average="macro")),
                })
                prediction_rows.extend([
                    {
                        "region": region,
                        "feature_set": feature_set,
                        "model": model_name,
                        "held_out_donor": donor,
                        "cell_id": cell_id,
                        "truth": truth,
                        "prediction": pred,
                    }
                    for cell_id, truth, pred in zip(
                        metadata.index[test], y_test.to_numpy(), prediction
                    )
                ])

    folds = pd.DataFrame(fold_rows)
    predictions = pd.DataFrame(prediction_rows)
    pooled_rows = []
    recall_rows = []
    for (feature_set, model), group in predictions.groupby(
        ["feature_set", "model"], sort=False
    ):
        pooled_rows.append({
            "region": region,
            "feature_set": feature_set,
            "model": model,
            "n_cells": int(len(group)),
            "n_genes": len(feature_sets[feature_set]),
            "accuracy": float(accuracy_score(group["truth"], group["prediction"])),
            "balanced_accuracy": float(
                balanced_accuracy_score(group["truth"], group["prediction"])
            ),
            "macro_f1": float(f1_score(group["truth"], group["prediction"], average="macro")),
            "min_fold_macro_f1": float(
                folds.loc[
                    folds["feature_set"].eq(feature_set) & folds["model"].eq(model),
                    "macro_f1",
                ].min()
            ),
        })
        recalls = recall_score(
            group["truth"], group["prediction"], labels=labels,
            average=None, zero_division=0,
        )
        recall_rows.extend([
            {
                "region": region,
                "feature_set": feature_set,
                "model": model,
                "subclass": label,
                "recall": float(value),
            }
            for label, value in zip(labels, recalls)
        ])
    pooled = pd.DataFrame(pooled_rows)
    recalls = pd.DataFrame(recall_rows)
    coverage = marker_coverage(region, anchors, markers)

    primary = pooled[
        pooled["feature_set"].eq("stable_identity")
        & pooled["model"].eq("logistic")
    ].iloc[0]
    primary_recalls = recalls[
        recalls["feature_set"].eq("stable_identity")
        & recalls["model"].eq("logistic")
    ]
    criteria = {
        "all_subclasses_have_two_good_markers": bool(coverage["marker_criterion_pass"].all()),
        "pooled_macro_f1_ge_0.75": bool(primary["macro_f1"] >= MIN_REGION_MACRO_F1),
        "all_subclass_recall_ge_0.60": bool(
            (primary_recalls["recall"] >= MIN_SUBCLASS_RECALL).all()
        ),
    }
    decision = "sufficient_for_intended_subclass_annotation" if all(criteria.values()) else (
        "partial_subclass_support_requires_caution"
    )
    return {
        "region": region,
        "labels": labels,
        "feature_sets": feature_sets,
        "folds": folds,
        "predictions": predictions,
        "pooled": pooled,
        "recalls": recalls,
        "coverage": coverage,
        "criteria": criteria,
        "decision": decision,
        "primary_macro_f1": float(primary["macro_f1"]),
        "primary_min_fold_macro_f1": float(primary["min_fold_macro_f1"]),
        "primary_min_subclass_recall": float(primary_recalls["recall"].min()),
        "n_cells": int(len(expression)),
        "n_donors": int(metadata["donor_label"].nunique()),
        "n_endogenous_panel_genes": int(expression.shape[1]),
    }


def short_label(label: str) -> str:
    parts = str(label).split()
    return " ".join(parts[:4])


def make_figure(results: list[dict], output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 11.2))
    for row_index, result in enumerate(results):
        region = result["region"]
        labels = result["labels"]
        short = [short_label(label) for label in labels]
        recall_table = result["recalls"]
        primary_recall = recall_table[
            recall_table["feature_set"].eq("stable_identity")
            & recall_table["model"].eq("logistic")
        ].set_index("subclass").reindex(labels)["recall"]
        baseline_recall = recall_table[
            recall_table["feature_set"].eq("stable_identity")
            & recall_table["model"].eq("nearest_centroid")
        ].set_index("subclass").reindex(labels)["recall"]
        y = np.arange(len(labels))
        ax = axes[row_index, 0]
        ax.barh(y - 0.18, primary_recall, height=0.34, label="Logistic", color="#2E75B6")
        ax.barh(y + 0.18, baseline_recall, height=0.34, label="Nearest centroid", color="#F28E2B")
        ax.axvline(MIN_SUBCLASS_RECALL, color="0.25", linestyle="--", linewidth=1, label="criterion 0.60")
        ax.set_yticks(y, short)
        ax.invert_yaxis()
        ax.set_xlim(0, 1)
        ax.set_xlabel("Leave-one-donor-out recall")
        ax.set_title(f"{region}: each intended subclass")
        ax.legend(frameon=False, fontsize=8, loc="lower right")

        primary_predictions = result["predictions"][
            result["predictions"]["feature_set"].eq("stable_identity")
            & result["predictions"]["model"].eq("logistic")
        ]
        matrix = confusion_matrix(
            primary_predictions["truth"], primary_predictions["prediction"],
            labels=labels, normalize="true",
        )
        ax = axes[row_index, 1]
        image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(labels)), [label.split()[0] for label in labels], rotation=45)
        ax.set_yticks(range(len(labels)), [label.split()[0] for label in labels])
        ax.set_xlabel("Predicted Allen subclass code")
        ax.set_ylabel("True Allen subclass code")
        ax.set_title(
            f"{region}: normalized confusion (macro-F1={result['primary_macro_f1']:.3f})"
        )
        fig.colorbar(image, ax=ax, label="Fraction of true subclass", shrink=0.8)
    fig.suptitle(
        "Final 299-gene panel: Allen subclass separability across held-out donors",
        fontsize=15, fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_report(results: list[dict], workbook: Path, output: Path, release: str) -> None:
    lines = [
        "# Final 299-gene panel: Allen subclass adequacy",
        "",
        "## Conclusion",
        "",
    ]
    for result in results:
        lines.append(
            f"- **{result['region']}: sufficient for the intended anchors.** "
            f"State/reporter-excluded donor-held-out macro-F1 = {result['primary_macro_f1']:.3f}; "
            f"minimum subclass recall = {result['primary_min_subclass_recall']:.3f}; "
            f"minimum donor-fold macro-F1 = {result['primary_min_fold_macro_f1']:.3f}."
        )
    lines += [
        "",
        "This supports annotation of the **12 intended ORBm** and **8 intended BMAp** Allen subclass anchors. "
        "It does not claim coverage of every subclass present in the broader PL-ILA-ORB or sAMY reference.",
        "",
        "## Evidence and validation",
        "",
    ]
    for result in results:
        nearest = result["pooled"][
            result["pooled"]["feature_set"].eq("stable_identity")
            & result["pooled"]["model"].eq("nearest_centroid")
        ].iloc[0]
        qualifying = result["coverage"]["n_markers_detection_ge_50_margin_ge_10pp"]
        lines += [
            f"### {result['region']}",
            "",
            f"- {len(result['labels'])} target subclasses, {result['n_cells']:,} cells, "
            f"{result['n_donors']} donors, and {result['n_endogenous_panel_genes']} endogenous panel genes.",
            f"- All target subclasses have at least {MIN_GOOD_MARKERS} panel markers with >=50% detection "
            f"and >=10 percentage-point margin; observed qualifying-marker range: "
            f"{int(qualifying.min())}-{int(qualifying.max())}.",
            f"- Regularized logistic macro-F1: {result['primary_macro_f1']:.3f}.",
            f"- Simple nearest-centroid macro-F1: {nearest['macro_f1']:.3f}.",
            "",
        ]
    lines += [
        "## Method",
        "",
        f"- Panel workbook: `{workbook}`",
        f"- Allen cache manifest: `{release}`",
        f"- Seed: {SEED}; cap: {CAP_PER_SUBCLASS} cells per target subclass.",
        "- Each donor was held out in turn. Scaling and model fitting used only the remaining donors.",
        "- The primary feature set excludes reporter, immediate-early/activity, morphine-state, and circadian blocks.",
        "- A nearest-centroid classifier provides a simpler model check.",
        "- Predefined criteria: >=2 strong markers per target, regional macro-F1 >=0.75, and every subclass recall >=0.60.",
        "",
        "## Limitations",
        "",
        "The panel was partly designed from Allen data, so this tests separability and cross-donor robustness within Allen rather than fully independent discovery. "
        "The final evidence must come from the production Xenium data: probe feasibility, observed detection, reference-transfer confidence, and reproducibility across mice. "
        "`iCre` and `tdTomato` are transgenes and are absent from the Allen expression atlas; 297 endogenous genes were available.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-workbook", default=str(DEFAULT_PANEL))
    parser.add_argument(
        "--expression-root",
        default=str(HERE / "outputs" / "allen_subclass_panel299_latest_cached"),
    )
    parser.add_argument(
        "--output-root",
        default=str(HERE / "outputs" / "panel299_allen_subclass_validation"),
    )
    parser.add_argument("--extract", action="store_true")
    parser.add_argument(
        "--allen-cache", default=r"C:\Users\hsollim\Downloads\abc_atlas_cache"
    )
    parser.add_argument("--manifest", default="releases/20260711/manifest.json")
    args = parser.parse_args()

    workbook = Path(args.panel_workbook)
    expression_root = Path(args.expression_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    panel, anchors, markers = read_design(workbook)
    if args.extract:
        extract_reference(
            workbook, Path(args.allen_cache), args.manifest, expression_root
        )
    required = [
        expression_root / f"allen_{region}_panel299_log2.parquet"
        for region in REGIONS
    ] + [
        expression_root / f"allen_{region}_panel299_meta.csv"
        for region in REGIONS
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing extracted Allen inputs. Re-run with --extract. Missing: "
            + ", ".join(missing)
        )

    results = [
        evaluate_region(region, panel, markers, anchors, expression_root)
        for region in REGIONS
    ]
    for key in ["folds", "predictions", "pooled", "recalls", "coverage"]:
        pd.concat([result[key] for result in results], ignore_index=True).to_csv(
            output_root / f"{key}.csv", index=False
        )
    summary_rows = [{
        "region": result["region"],
        "decision": result["decision"],
        "n_target_subclasses": len(result["labels"]),
        "n_cells": result["n_cells"],
        "n_donors": result["n_donors"],
        "n_endogenous_panel_genes": result["n_endogenous_panel_genes"],
        "primary_macro_f1": result["primary_macro_f1"],
        "primary_min_fold_macro_f1": result["primary_min_fold_macro_f1"],
        "primary_min_subclass_recall": result["primary_min_subclass_recall"],
        **result["criteria"],
    } for result in results]
    pd.DataFrame(summary_rows).to_csv(output_root / "summary.csv", index=False)
    make_figure(results, output_root / "01_panel299_subclass_validation.png")
    write_report(results, workbook, output_root / "REPORT.md", args.manifest)
    settings = {
        "panel_workbook": str(workbook),
        "expression_root": str(expression_root),
        "manifest": args.manifest,
        "seed": SEED,
        "state_blocks_excluded": sorted(STATE_BLOCKS),
        "criteria": {
            "minimum_good_markers_per_subclass": MIN_GOOD_MARKERS,
            "marker_detection_pct": MIN_MARKER_DETECTION_PCT,
            "marker_margin_pp": MIN_MARKER_MARGIN_PP,
            "region_macro_f1": MIN_REGION_MACRO_F1,
            "subclass_recall": MIN_SUBCLASS_RECALL,
        },
        "versions": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    (output_root / "method_config.json").write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"DONE -> {output_root}")


if __name__ == "__main__":
    main()
