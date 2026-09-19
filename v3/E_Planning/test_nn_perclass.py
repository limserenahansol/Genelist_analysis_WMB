"""Per non-neuronal class recall, with and without the 8 dedicated probes.

The section-level test said the 8 probes change nothing (non-neuronal cells are
never called neurons either way, because a glial cell reads zero for every neuronal
gene on the panel and the classifier uses that). The question that remains is
whether you can still name WHICH non-neuronal class a cell is - astrocyte vs
microglia vs pericyte - without a positive marker for it.
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
NN_PROBES = base.NN_PROBES
SEED, MIN_CELLS, CAP = 0, 60, 1200


def main() -> None:
    X, genes, md = base.load()
    gi = {}
    for i, g in enumerate(genes):
        gi.setdefault(g, i)
    lean = pd.read_excel(DL / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx", "FINAL_GENE_LIST")
    keep = (md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS).to_numpy()
    y, Xk = md.subclass[keep].to_numpy(), X[keep]
    idx_tr, idx_te = train_test_split(np.arange(len(y)), test_size=0.3, random_state=SEED, stratify=y)
    rng = np.random.RandomState(SEED)
    idx_tr = np.sort(np.concatenate([
        (w if len(w) <= CAP else rng.choice(w, CAP, replace=False))
        for w in (idx_tr[y[idx_tr] == c] for c in np.unique(y[idx_tr]))]))

    out = {}
    for name, drop in (("with the 8 probes", []), ("without them", NN_PROBES)):
        cols = np.array(sorted({gi[g] for g in lean.gene if g in gi and g not in drop}))
        sc = StandardScaler().fit(Xk[idx_tr][:, cols])
        clf = LogisticRegression(max_iter=1000, C=1.0).fit(sc.transform(Xk[idx_tr][:, cols]), y[idx_tr])
        pred = clf.predict(sc.transform(Xk[idx_te][:, cols]))
        yte = y[idx_te]
        rec = {}
        for c in sorted({s for s in yte if s.endswith("NN")}):
            m = yte == c
            rec[c] = round(float((pred[m] == c).mean() * 100), 1)
        out[name] = rec
        print(f"{name}: done", flush=True)
    t = pd.DataFrame(out)
    t["change (pp)"] = (t["without them"] - t["with the 8 probes"]).round(1)
    t["n_cells_tested"] = [int((y[idx_te] == c).sum()) for c in t.index]
    t.index.name = "non-neuronal class"
    t.to_csv(O / "_TEST_nn_perclass.csv")
    print("\n" + t.to_string())


if __name__ == "__main__":
    main()
