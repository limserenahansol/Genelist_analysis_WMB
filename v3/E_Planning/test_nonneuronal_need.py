"""Do we actually need the 8 non-neuronal probes? Measured, not argued.

The claim under test: with no marker of their own, the 28 pct of cells that are not
neurons get called as neurons, and contaminate the neuronal clusters a TRAP+ analysis
depends on.

Test: train the same classifier twice on Allen cells of ORBm + BMAp - once with the
panel as ordered, once with the 8 non-neuronal probes deleted - and score a held-out
set at TRUE prevalence (no class capping on the test side, so 28 pct of the test cells
really are non-neuronal). Then ask two questions:

  1  of the non-neuronal cells, how many are called a neuronal cell type?
  2  of the cells called into each of the 20 target populations, how many are
     actually non-neuronal? (the contamination a TRAP+ count would inherit)

Writes _TEST_nonneuronal_need.csv / .xlsx
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SH = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
      "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
      "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
      "STR": "WMB-10Xv3-STR"}
NN_PROBES = ["Aqp4", "Pdgfra", "Gjc3", "Cldn5", "Vtn", "Acta2", "Dcn", "Siglech"]
SEED, MIN_CELLS, CAP = 0, 60, 1200


def load():
    X = np.load(O / "_cacheX2.npy")
    genes = (O / "_cacheG2.txt").read_text().split()
    md = pd.read_parquet(O / "_cacheMD.parquet")
    for extra in ("allen_extract_jesse3", "allen_extract_v9gap", "allen_extract_paper",
                  "allen_extract_sow2", "allen_extract_add20"):
        d = O / extra
        if not d.exists():
            continue
        parts, gj = [], None
        for f in sorted(glob.glob(str(O / "allen_extract" / "*.npz"))):
            z = np.load(f, allow_pickle=True)
            p = d / f"{SH[os.path.basename(f)[:-4]]}.npz"
            if not p.exists():
                parts = []
                break
            zz = np.load(p, allow_pickle=True)
            assert list(zz["cell"]) == list(z["cell"])
            parts.append(zz["X"])
            g = [str(x) for x in zz["genes"]]
            gj = g if gj is None else gj
        if parts:
            X = np.hstack([X, np.vstack(parts)])
            genes = genes + gj
    return X, genes, md


def main() -> None:
    X, genes, md = load()
    gi = {}
    for i, g in enumerate(genes):
        gi.setdefault(g, i)
    lean = pd.read_excel(DL / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx", "FINAL_GENE_LIST")
    ac = pd.read_excel(DL / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx", "ANCHOR_COVERAGE")
    anchors = set(ac.allen_subclass_anchor)

    keep = (md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS).to_numpy()
    y = md.subclass[keep].to_numpy()
    Xk = X[keep]
    is_nn = np.array([s.endswith("NN") for s in y])
    print(f"cells: {len(y):,} | non-neuronal: {is_nn.sum():,} = {is_nn.mean()*100:.1f} pct", flush=True)

    idx_tr, idx_te = train_test_split(np.arange(len(y)), test_size=0.3,
                                      random_state=SEED, stratify=y)
    # cap only the TRAINING side, so the test set keeps true prevalence
    rng = np.random.RandomState(SEED)
    capped = []
    for c in np.unique(y[idx_tr]):
        w = idx_tr[y[idx_tr] == c]
        capped.append(w if len(w) <= CAP else rng.choice(w, CAP, replace=False))
    idx_tr = np.sort(np.concatenate(capped))
    print(f"train {len(idx_tr):,} (capped at {CAP}/class) | test {len(idx_te):,} at true prevalence",
          flush=True)

    rows, per_anchor = [], {}
    for name, drop in (("panel as ordered (297)", []), ("without the 8 non-neuronal probes", NN_PROBES)):
        cols = np.array(sorted({gi[g] for g in lean.gene if g in gi and g not in drop}))
        sc = StandardScaler().fit(Xk[idx_tr][:, cols])
        clf = LogisticRegression(max_iter=1000, C=1.0).fit(sc.transform(Xk[idx_tr][:, cols]), y[idx_tr])
        pred = clf.predict(sc.transform(Xk[idx_te][:, cols]))
        yte, nnte = y[idx_te], is_nn[idx_te]
        pred_is_nn = np.array([s.endswith("NN") for s in pred])

        nn_called_neuron = float((~pred_is_nn)[nnte].mean() * 100)
        nn_recall = float((pred[nnte] == yte[nnte]).mean() * 100)
        into_anchor = np.isin(pred, list(anchors))
        contam = float(nnte[into_anchor].mean() * 100)
        rows.append({"gene set": name, "n_genes_measured": len(cols),
                     "non-neuronal cells called a NEURON type (%)": round(nn_called_neuron, 1),
                     "non-neuronal cells called their own class (%)": round(nn_recall, 1),
                     "cells landing in the 20 target populations that are actually non-neuronal (%)":
                         round(contam, 2),
                     "balanced accuracy over all 75 classes": round(
                         balanced_accuracy_score(yte, pred), 4)})
        pa = {}
        for a in sorted(anchors):
            m = pred == a
            if m.sum() == 0:
                continue
            pa[a] = {"cells called this type": int(m.sum()),
                     "of them non-neuronal (%)": round(float(nnte[m].mean() * 100), 2),
                     "of them a different neuron type (%)": round(
                         float(((yte != a) & ~nnte)[m].mean() * 100), 2)}
        per_anchor[name] = pd.DataFrame(pa).T
        print(f"  {name}: NN->neuron {nn_called_neuron:.1f} pct | anchor contamination {contam:.2f} pct",
              flush=True)

    summary = pd.DataFrame(rows)
    with pd.ExcelWriter(O / "_TEST_nonneuronal_need.xlsx", engine="openpyxl") as w:
        summary.to_excel(w, "summary", index=False)
        for name, df in per_anchor.items():
            df.to_excel(w, ("with probes" if "ordered" in name else "without probes"))
    summary.to_csv(O / "_TEST_nonneuronal_need.csv", index=False)
    print("\n" + summary.to_string(index=False))
    for name, df in per_anchor.items():
        print(f"\n--- {name}: worst 6 populations by non-neuronal contamination")
        print(df.sort_values("of them non-neuronal (%)", ascending=False).head(6).to_string())


if __name__ == "__main__":
    main()
