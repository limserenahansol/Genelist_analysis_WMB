"""Are all 20 target cell types actually callable, and do 4 extra markers help?

"17 of 20 have a dedicated marker" is a statement about SINGLE genes, and it depends
on what you compare against. Against all 75 subclasses in the section it is 17/20;
against the other 19 TARGET types - which is the comparison that matters once glia
and non-target cells are already excluded - three types are the hard ones:
006 L4/5 IT, 005 L5 IT and 073 MEA-BST Sox6 Gaba.

This measures what actually matters: per-type recall and precision on held-out cells
at true prevalence, for the 291-gene panel and for 291 + the best available markers
for those three types (Tnnc1, Adam19, Man2a1, Chn2).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import test_nonneuronal_need as base

O = Path(base.O)
DL = Path(r"C:\Users\hsollim\Downloads")
ADD = ["Tnnc1", "Adam19", "Man2a1", "Chn2"]
SEED, MIN_CELLS, CAP = 0, 60, 1200


def main() -> None:
    X, genes, md = base.load()
    gi = {}
    for i, g in enumerate(genes):
        gi.setdefault(g, i)
    panel = pd.read_excel(DL / "PANEL_FINAL_291_ORBm_BMAp_minNN.xlsx", "FINAL_GENE_LIST")
    ac = pd.read_excel(DL / "PANEL_FINAL_291_ORBm_BMAp_minNN.xlsx", "ANCHOR_COVERAGE")
    anchors = [a for a in ac.allen_subclass_anchor]
    print("extra markers available per-cell:", [g for g in ADD if g in gi], flush=True)

    keep = (md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS).to_numpy()
    y, Xk = md.subclass[keep].to_numpy(), X[keep]
    idx_tr, idx_te = train_test_split(np.arange(len(y)), test_size=0.3, random_state=SEED, stratify=y)
    rng = np.random.RandomState(SEED)
    idx_tr = np.sort(np.concatenate([
        (w if len(w) <= CAP else rng.choice(w, CAP, replace=False))
        for w in (idx_tr[y[idx_tr] == c] for c in np.unique(y[idx_tr]))]))

    res = {}
    for name, extra in (("291 panel", []), ("291 + 4 markers", [g for g in ADD if g in gi])):
        cols = np.array(sorted({gi[g] for g in list(panel.gene) + extra if g in gi}))
        sc = StandardScaler().fit(Xk[idx_tr][:, cols])
        clf = LogisticRegression(max_iter=1000, C=1.0).fit(sc.transform(Xk[idx_tr][:, cols]), y[idx_tr])
        pred = clf.predict(sc.transform(Xk[idx_te][:, cols]))
        yte = y[idx_te]
        rows = {}
        for a in anchors:
            m = yte == a
            if m.sum() == 0:
                continue
            rec = float((pred[m] == a).mean() * 100)
            called = pred == a
            prec = float((yte[called] == a).mean() * 100) if called.sum() else float("nan")
            rows[a] = {"n_cells_tested": int(m.sum()), "recall_%": round(rec, 1),
                       "precision_%": round(prec, 1)}
        res[name] = pd.DataFrame(rows).T
        print(f"{name}: {len(cols)} genes | mean recall {res[name]['recall_%'].mean():.1f} | "
              f"mean precision {res[name]['precision_%'].mean():.1f}", flush=True)

    t = res["291 panel"].join(res["291 + 4 markers"], lsuffix=" (291)", rsuffix=" (+4)")
    t["recall gain (pp)"] = (t["recall_% (+4)"] - t["recall_% (291)"]).round(1)
    t["precision gain (pp)"] = (t["precision_% (+4)"] - t["precision_% (291)"]).round(1)
    t = t[["n_cells_tested (291)", "recall_% (291)", "recall_% (+4)", "recall gain (pp)",
           "precision_% (291)", "precision_% (+4)", "precision gain (pp)"]]
    t.index.name = "target cell type"
    t.to_csv(O / "_TEST_all20_coverage.csv")
    print("\n" + t.to_string())


if __name__ == "__main__":
    main()
