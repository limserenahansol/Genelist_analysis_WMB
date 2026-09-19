"""Which genes actually do the work of naming a cell type, and which are dead weight for it.

Companion to panel_celltype_classification.py. That script asks whether a panel CAN
name a cell type; this one asks WHICH genes make that possible.

Method: fit the same multinomial logistic classifier on standardised features over the
v7+base gene set, then take max |coefficient| across classes per gene. On standardised
inputs that is a fair cross-gene comparison of discriminative contribution. A gene near
zero contributes nothing to JOB 2 (naming the cell type).

IMPORTANT: a low score here is NOT grounds for cutting a gene. Most of the panel exists
for JOB 3 - profiling the cell type once named (GPCR level, TF level, plasticity level,
IEG induction, morphine response). Those genes are supposed to be read as levels, not
used as classifiers. This output is only for deciding whether the JOB 2 subset is
adequate, and for spotting genes that serve NEITHER job.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from panel_celltype_classification import CAP, MIN_CELLS, SEED, load, subsample

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"


def main() -> None:
    X, genes, md = load()
    gi = {g: i for i, g in enumerate(genes)}
    base = set(pd.read_csv(O / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    v7 = pd.read_excel(O / "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx", "SHARED_PANEL_ORDER")
    block = dict(zip(v7.gene.astype(str), v7.block.astype(str)))
    S = set(v7.gene.astype(str)) | base
    cols = np.array(sorted(gi[g] for g in S if g in gi))
    names = [genes[i] for i in cols]

    keep = md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS
    y_all = md.subclass[keep].to_numpy()
    X_all = X[keep.to_numpy()][:, cols]
    sel = subsample(y_all)
    y, Xk = y_all[sel], X_all[sel]
    print(f"fitting on {Xk.shape[0]:,} cells x {Xk.shape[1]} genes, "
          f"{len(set(y))} classes (cap {CAP}/class)", flush=True)

    tr, te, ytr, yte = train_test_split(Xk, y, test_size=0.3, random_state=SEED, stratify=y)
    sc = StandardScaler().fit(tr)
    clf = LogisticRegression(max_iter=1000, n_jobs=-1, C=1.0).fit(sc.transform(tr), ytr)
    W = np.abs(clf.coef_)                       # classes x genes
    imp = W.max(axis=0)
    mean_imp = W.mean(axis=0)

    d = pd.DataFrame({
        "gene": names,
        "max_abs_coef": np.round(imp, 4),
        "mean_abs_coef": np.round(mean_imp, 4),
        "rank": (-imp).argsort().argsort() + 1,
        "on_base_free": [g in base for g in names],
        "on_v7_order": [g in block for g in names],
        "block": [block.get(g, "(base only)") for g in names],
    }).sort_values("max_abs_coef", ascending=False)

    cust = d[d.on_v7_order & ~d.on_base_free]
    print(f"\ntop 25 cell-type-calling genes overall:")
    print(d.head(25)[["gene", "max_abs_coef", "block"]].to_string(index=False))
    print(f"\nv7 CUSTOM genes contributing least to naming a cell type "
          f"(check each has a JOB 3 reason):")
    print(cust.tail(30)[["gene", "max_abs_coef", "block"]].to_string(index=False))

    with pd.ExcelWriter(O / "PANEL_gene_importance.xlsx", engine="openpyxl") as w:
        pd.DataFrame({"item": ["What this is", "How to read it", "What it is NOT"],
                      "detail": [
            "Per-gene contribution to naming a cell type, from a multinomial logistic "
            "classifier fitted on standardised expression of the v7+base gene set.",
            "max_abs_coef is the largest standardised coefficient that gene gets for any "
            "cell type. High = it discriminates. Near zero = it does not help name a type.",
            "NOT a cut list. Most panel genes exist to PROFILE a named cell type (GPCR, TF, "
            "plasticity, IEG, morphine level), where a flat profile across types is normal "
            "and expected. Only cut a low scorer if it also has no profiling role.",
        ]}).to_excel(w, "READ_ME", index=False)
        d.to_excel(w, "per_gene", index=False)
    print(f"\nwrote {O / 'PANEL_gene_importance.xlsx'}")


if __name__ == "__main__":
    main()
