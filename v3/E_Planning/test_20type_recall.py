"""Can the panel actually call all 20 target cell types? Held-out, per class.

Counting "markers per type" is a proxy I invented. The real question is whether a cell
from each of the 20 populations gets assigned to its own population. 073 MEA-BST Sox6
Gaba has only one positive marker above my credit bar, so it is the test case.

Two things the marker count misses:
  - NEGATIVE evidence. A gene at 5% in 073 and 90% in its neighbour 074 calls 073 just
    as well as a positive marker, but scores zero under a positive-only rule.
  - COMBINATIONS. Cell types are called by patterns, not by single genes.

Design: 70/30 stratified split, 3 seeds, multinomial logistic regression on the panel
genes recovered in the cell matrix, 20 target populations only. Report per-class recall
and the confusion partner for the weakest classes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DST = OUT / "TWENTY_TYPE_RECALL.xlsx"


def load_cells(panel: set[str]):
    cols, index, meta = {}, None, None
    for d in sorted(OUT.glob("allen_extract*")):
        Xs, ids, subs, gg = [], [], [], None
        for f in sorted(d.glob("*.npz")):
            z = np.load(f, allow_pickle=True)
            if "X" not in z.files:
                continue
            gg = [str(x) for x in z["genes"]]
            Xs.append(z["X"])
            ids.append([str(x) for x in z["cell"]])
            subs.append([str(x) for x in z["subclass"]])
        if not Xs:
            continue
        X, cid, sub = np.vstack(Xs), np.concatenate(ids), np.concatenate(subs)
        if index is None:
            index = pd.Index(cid)
            meta = pd.Series(sub, index=cid)
        for i, g in enumerate(gg):
            if g in panel and g not in cols:
                cols[g] = pd.Series(X[:, i], index=cid).reindex(index).values
    return pd.DataFrame(cols, index=index), meta.reindex(index)


def main() -> None:
    pan = pd.read_excel(OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx", "PANEL_ORDER")
    ac = pd.read_excel(OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx", "ANCHOR_COVERAGE_20types")
    targets = list(ac.allen_subclass_anchor)
    df, sub = load_cells(set(pan.gene))
    m = sub.isin(targets)
    d = df[m].fillna(0.0)
    y = sub[m].values
    X = d.values.astype(np.float32)
    print(f"cells in the 20 target populations: {len(d):,} | "
          f"panel genes recovered {d.shape[1]} of {len(set(pan.gene))}")

    recalls, cms, bas = [], [], []
    for seed in (0, 1, 2):
        tr, te = train_test_split(np.arange(len(y)), test_size=0.3, random_state=seed,
                                  stratify=y)
        clf = LogisticRegression(max_iter=600, n_jobs=-1)
        clf.fit(X[tr], y[tr])
        p = clf.predict(X[te])
        bas.append(balanced_accuracy_score(y[te], p))
        lab = sorted(set(y))
        cm = confusion_matrix(y[te], p, labels=lab)
        cms.append(cm)
        recalls.append(pd.Series(cm.diagonal() / cm.sum(1), index=lab))
    lab = sorted(set(y))
    R = pd.concat(recalls, axis=1)
    cm = np.mean(cms, axis=0)
    conf = []
    for i, L in enumerate(lab):
        row = cm[i].copy()
        row[i] = -1
        j = int(row.argmax())
        conf.append({"cell_population": L,
                     "region": dict(zip(ac.allen_subclass_anchor, ac.region))[L],
                     "n_cells": int(ac.set_index("allen_subclass_anchor").n_cells[L]),
                     "markers_on_panel":
                         int(ac.set_index("allen_subclass_anchor").n_markers[L]),
                     "recall_mean": round(float(R.loc[L].mean()), 3),
                     "recall_sd": round(float(R.loc[L].std()), 3),
                     "most_confused_with": lab[j],
                     "confusion_pct": round(100 * cm[i, j] / cm[i].sum(), 1)})
    t = pd.DataFrame(conf).sort_values("recall_mean")

    pd.set_option("display.width", 300)
    print(f"\n20-way balanced accuracy: {np.mean(bas):.4f} "
          f"(sd {np.std(bas):.4f}, 3 seeds)")
    print("\nper-population recall, worst first:")
    print(t.to_string(index=False))
    print(f"\npopulations with recall >= 0.80: {int((t.recall_mean >= 0.80).sum())}/20")
    print(f"populations with recall >= 0.90: {int((t.recall_mean >= 0.90).sum())}/20")

    with pd.ExcelWriter(DST) as xw:
        t.to_excel(xw, sheet_name="per_population_recall", index=False)
        pd.DataFrame(cm, index=lab, columns=lab).to_excel(xw, sheet_name="confusion")
    print("wrote", DST)


if __name__ == "__main__":
    main()
