"""Allen sAMY -> Xenium BLA/CEA annotation validation.

Uses Seurat anchor transfer as the requested primary validation and a regularized
multinomial classifier as an independent check. It does not alter primary labels.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 0


def read_query(paths: list[Path], anatomy: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    count_frames: list[pd.DataFrame] = []
    meta_frames: list[pd.DataFrame] = []
    for path in paths:
        obj = ad.read_h5ad(path)
        roi = path.parent.name
        matrix = obj.layers["counts"]
        matrix = matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)
        keys = pd.Index([f"{roi}::{cell}" for cell in obj.obs_names.astype(str)], name="cell_key")
        count_frames.append(pd.DataFrame(matrix, index=keys, columns=obj.var_names.astype(str)))
        keep = [c for c in ["x_centroid", "y_centroid", "module", "leiden"] if c in obj.obs]
        meta = obj.obs[keep].copy()
        meta.index = keys
        meta["cell_id"] = obj.obs_names.astype(str)
        meta["roi"] = roi
        meta["anatomy"] = anatomy
        meta_frames.append(meta)
    # ROI exports can differ by a few control/blank features.  Missing measured
    # features are true zero counts, not unknown values.
    return pd.concat(count_frames).fillna(0), pd.concat(meta_frames)


def map_coarse(subclass: str, anatomy: str) -> str:
    s = str(subclass)
    if "Astro" in s:
        return "astrocyte"
    if "Oligo" in s and "OPC" not in s:
        return "oligo"
    if "OPC" in s:
        return "OPC"
    if any(x in s for x in ["Endo", "VLMC", "Peri", "SMC"]):
        return "vascular"
    if any(x in s for x in ["Microglia", "PVM", "BAM"]):
        return "microglia"
    if anatomy == "BLA":
        if s.startswith("014 LA-BLA-BMA-PA"):
            return "BLA_principal"
        if s.startswith("051 Pvalb") or s.startswith("052 Pvalb"):
            return "BLA_Pvalb_GABA"
        if s.startswith("053 Sst") or s.startswith("056 Sst"):
            return "BLA_Sst_GABA"
        if any(s.startswith(x) for x in ["046 Vip", "047 Sncg", "048 RHP-COA Ndnf", "049 Lamp5", "050 Lamp5"]):
            return "BLA_Vip_Lamp5_GABA"
    if anatomy == "CEA":
        mapping = {
            "077 CEA-BST Gal Avp": "CEA_Gal_Avp_like",
            "079 CEA-BST Six3 Cyp26b1": "CEA_Six3_Cyp26b1_like",
            "080 CEA-AAA-BST Six3 Sp9": "CEA_Six3_Sp9_like",
            "082 CEA-BST Ebf1 Pdyn": "CEA_Ebf1_Pdyn_like",
            "083 CEA-BST Rai14 Pdyn Crh": "CEA_Rai14_Pdyn_Crh_like",
        }
        for prefix, label in mapping.items():
            if s.startswith(prefix):
                return label
    return "other"


def logistic_transfer(
    ref_log2: pd.DataFrame, ref_meta: pd.DataFrame, query: pd.DataFrame
) -> pd.DataFrame:
    genes = [g for g in ref_log2.columns if g in query.columns]
    idx = ref_log2.index.intersection(ref_meta.index)
    x_ref = ref_log2.loc[idx, genes].to_numpy(dtype=np.float32) * np.log(2.0)
    y = ref_meta.loc[idx, "subclass"].astype(str).to_numpy()
    lib = query[genes].sum(axis=1).to_numpy().reshape(-1, 1)
    x_query = np.log1p(1e4 * query[genes].to_numpy(dtype=np.float32) / np.clip(lib, 1, None))
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=500, C=1.0, random_state=SEED, solver="lbfgs"),
    )
    model.fit(x_ref, y)
    prob = model.predict_proba(x_query)
    return pd.DataFrame(
        {
            "cell_key": query.index,
            "classifier_subclass": model.classes_[prob.argmax(axis=1)],
            "classifier_score": prob.max(axis=1),
        }
    ).set_index("cell_key")


def make_figure(df: pd.DataFrame, anatomy: str, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7))
    axes[0].hist(df["seurat_score"], bins=25, color="#4C78A8", edgecolor="white")
    axes[0].axvline(0.5, color="black", linestyle="--", linewidth=1)
    axes[0].set(title=f"{anatomy}: transfer confidence", xlabel="Seurat prediction score", ylabel="Cells")

    comp = df["seurat_coarse"].value_counts(normalize=True).mul(100).sort_values()
    axes[1].barh(comp.index, comp.values, color="#59A14F")
    axes[1].set(title="Allen-transferred labels", xlabel="Cells (%)", ylabel="")

    tab = pd.crosstab(df["module"], df["seurat_coarse"], normalize="index") if "module" in df else pd.DataFrame()
    if not tab.empty:
        image = axes[2].imshow(tab.to_numpy(), aspect="auto", vmin=0, vmax=1, cmap="Blues")
        axes[2].set_xticks(range(tab.shape[1]), tab.columns, rotation=90, fontsize=7)
        axes[2].set_yticks(range(tab.shape[0]), tab.index, fontsize=7)
        axes[2].set(title="Primary module vs Allen label", xlabel="Allen label", ylabel="Primary module")
        fig.colorbar(image, ax=axes[2], label="Row fraction")
    fig.suptitle(f"{anatomy} Allen sAMY reference validation (pilot; one mouse)", fontsize=14)
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-root", required=True)
    parser.add_argument("--reference-root", required=True)
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    pipeline = Path(args.pipeline_root)
    reference = Path(args.reference_root)
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    ref_log2 = pd.read_parquet(reference / "allen_BMAp_log2.parquet")
    ref_counts = pd.read_parquet(reference / "allen_BMAp_pseudo_cpm.parquet")
    ref_meta = pd.read_csv(reference / "allen_BMAp_meta.csv", index_col=0)
    genes = [g for g in ref_counts.columns if g in ref_log2.columns]
    ref_counts = ref_counts[genes]
    ref_counts.T.to_csv(output_root / "seurat_ref_sAMY.csv")
    ref_meta.to_csv(output_root / "allen_sAMY_meta.csv")

    all_summary: dict[str, dict] = {}
    for anatomy, pattern in [("BLA", "bla_*/*_processed.h5ad"), ("CEA", "cea_*/*_processed.h5ad")]:
        paths = sorted(input_root.glob(pattern))
        if not paths:
            raise FileNotFoundError(f"no {anatomy} processed h5ad files under {input_root}")
        query, meta = read_query(paths, anatomy)
        common = [g for g in genes if g in query.columns]
        query = query[common]
        query.T.to_csv(output_root / f"seurat_query_{anatomy}.csv")
        pred_path = output_root / f"seurat_pred_{anatomy}.csv"
        subprocess.run(
            [
                "Rscript",
                str(pipeline / "run_seurat_label_transfer_generic.R"),
                str(output_root / "seurat_ref_sAMY.csv"),
                str(output_root / f"seurat_query_{anatomy}.csv"),
                str(output_root / "allen_sAMY_meta.csv"),
                str(pred_path),
            ],
            check=True,
        )
        seurat = pd.read_csv(pred_path).set_index("cell_key")
        classifier = logistic_transfer(ref_log2[common], ref_meta, query)
        result = meta.join(seurat).join(classifier)
        result["seurat_coarse"] = result["seurat_subclass"].map(lambda x: map_coarse(x, anatomy))
        result["classifier_coarse"] = result["classifier_subclass"].map(lambda x: map_coarse(x, anatomy))
        result["high_confidence"] = result["seurat_score"] >= 0.5
        comparable = (result["module"] != "unassigned") & (result["seurat_coarse"] != "other")
        comparable_high = comparable & result["high_confidence"]
        result.to_csv(output_root / f"{anatomy}_reference_validation.csv")
        pd.crosstab(result["module"], result["seurat_coarse"]).to_csv(
            output_root / f"{anatomy}_module_vs_allen_counts.csv"
        )
        summary = {
            "anatomy": anatomy,
            "n_cells": int(len(result)),
            "n_rois": int(result["roi"].nunique()),
            "n_shared_genes": int(len(common)),
            "median_seurat_score": float(result["seurat_score"].median()),
            "fraction_seurat_score_ge_0.5": float(result["high_confidence"].mean()),
            "ari_seurat_vs_classifier_subclass": float(adjusted_rand_score(result["seurat_subclass"], result["classifier_subclass"])),
            "nmi_seurat_vs_classifier_subclass": float(normalized_mutual_info_score(result["seurat_subclass"], result["classifier_subclass"])),
            "nmi_primary_module_vs_seurat_coarse": float(normalized_mutual_info_score(result["module"].astype(str), result["seurat_coarse"])),
            "fraction_exact_module_label_all_cells": float((result["module"] == result["seurat_coarse"]).mean()),
            "fraction_cells_with_comparable_nonother_labels": float(comparable.mean()),
            "fraction_exact_among_comparable_labels": float(
                (result.loc[comparable, "module"] == result.loc[comparable, "seurat_coarse"]).mean()
            ),
            "fraction_exact_among_high_confidence_comparable_labels": float(
                (result.loc[comparable_high, "module"] == result.loc[comparable_high, "seurat_coarse"]).mean()
            ),
            "seurat_coarse_counts": {str(k): int(v) for k, v in result["seurat_coarse"].value_counts().items()},
            "note": "Descriptive pilot from one mouse; reference validation is not biological replication.",
        }
        all_summary[anatomy] = summary
        make_figure(result, anatomy, output_root / f"{anatomy}_reference_validation.png")
        print(json.dumps(summary, indent=2), flush=True)

    (output_root / "reference_validation_summary.json").write_text(
        json.dumps(all_summary, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
