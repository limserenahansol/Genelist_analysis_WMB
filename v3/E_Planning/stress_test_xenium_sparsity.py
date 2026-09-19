"""Does the panel still name cell types when the data are Xenium-sparse, not 10x-deep?

Every percentage in this project comes from 10x scRNA-seq, which sees far more
transcripts per cell than Xenium. That makes the numbers an upper bound, and it
leaves one question unanswered: a big panel and a lean panel may be equivalent at
10x depth yet diverge when each gene is measured with a tenth of the counts.

This simulates that. The cached values are log2(CPM+1); they are converted back to
a rate, Poisson-sampled at capture fractions 1.0 / 0.3 / 0.1 (i.e. 100 / 30 / 10 pct
of the transcripts), re-logged, and a classifier is refit per panel per rate on
held-out cells. rate=1.0 reproduces the earlier numbers as a control.

Writes _STRESS_xenium_sparsity.csv.
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
SH = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
      "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
      "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
      "STR": "WMB-10Xv3-STR"}
CAP = 1200
MIN_CELLS = 60
SEED = 0
RATES = [1.0, 0.3, 0.1]
PANELS = ["v11_lean296", "v11_superset316", "v7_252", "d301", "ULTIMATE261", "IDEAL178", "v8_237"]
SUP_PANELS = ["v11_lean296", "v11_superset316", "d301", "v7_252"]


def load():
    X = np.load(O / "_cacheX2.npy")
    genes = (O / "_cacheG2.txt").read_text().split()
    md = pd.read_parquet(O / "_cacheMD.parquet")
    for extra in ("allen_extract_jesse3", "allen_extract_v9gap", "allen_extract_paper"):
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


def subsample(y, seed=SEED, cap=CAP):
    rng = np.random.RandomState(seed)
    keep = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        keep.append(idx if len(idx) <= cap else rng.choice(idx, cap, replace=False))
    return np.sort(np.concatenate(keep))


def sparsify(Xs: np.ndarray, rate: float, seed: int) -> np.ndarray:
    """log2(CPM+1) -> rate -> Poisson at `rate` of the depth -> log2(x+1)."""
    if rate >= 1.0:
        return Xs
    lam = (np.power(2.0, Xs) - 1.0) * rate
    rng = np.random.RandomState(seed)
    return np.log2(rng.poisson(np.maximum(lam, 0)).astype(np.float32) + 1.0)


def score(X, y, seed=SEED):
    tr, te, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    sc = StandardScaler().fit(tr)
    clf = LogisticRegression(max_iter=1000, C=1.0).fit(sc.transform(tr), ytr)
    return balanced_accuracy_score(yte, clf.predict(sc.transform(te)))


def main() -> None:
    X, genes, md = load()
    gi = {g: i for i, g in enumerate(genes)}
    print(f"{X.shape[0]:,} cells x {X.shape[1]} genes", flush=True)
    sets = {}
    for p in PANELS:
        g = pd.read_csv(O / "_panel_csv" / f"{p}.csv").gene.astype(str)
        sets[p] = np.array(sorted({gi[x] for x in g if x in gi}))
        print(f"  {p:16s} {len(sets[p]):3d}/{len(set(g))} genes have per-cell data", flush=True)

    keep = (md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS).to_numpy()
    y_all = md.subclass[keep].to_numpy()
    sel = subsample(y_all)
    y = y_all[sel]
    Xk = X[keep][sel]

    ac = pd.read_excel(O / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx", "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}

    rows = []
    for rate in RATES:
        Xr = sparsify(Xk, rate, SEED)
        for p, cols in sets.items():
            acc = score(Xr[:, cols], y)
            rows.append({"panel": p, "n_genes_measured": len(cols), "capture_rate": rate,
                         "level": "subclass (cell type)", "balanced_acc": round(float(acc), 4)})
            print(f"  rate {rate:<4} {p:16s} subclass {acc:.4f}", flush=True)

    for rate in [1.0, 0.1]:
        per = {p: [] for p in SUP_PANELS}
        for a, roi in roi_of.items():
            m = ((md.subclass == a) & (md.roi == roi)).to_numpy()
            if m.sum() < MIN_CELLS:
                continue
            sup = md.supertype[m]
            vc = sup.value_counts()
            vc = vc[vc >= MIN_CELLS]
            if len(vc) < 2:
                continue
            mm = m.copy()
            mm[mm] = sup.isin(vc.index).to_numpy()
            ys_all = md.supertype[mm].to_numpy()
            ssel = subsample(ys_all)
            ys = ys_all[ssel]
            Xs = sparsify(X[mm][ssel], rate, SEED)
            for p in SUP_PANELS:
                try:
                    per[p].append(score(Xs[:, sets[p]], ys))
                except ValueError:
                    pass
        for p in SUP_PANELS:
            if per[p]:
                rows.append({"panel": p, "n_genes_measured": len(sets[p]), "capture_rate": rate,
                             "level": "supertype (sub-population, mean over cell types)",
                             "balanced_acc": round(float(np.mean(per[p])), 4)})
                print(f"  rate {rate:<4} {p:16s} supertype {np.mean(per[p]):.4f}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(O / "_STRESS_xenium_sparsity.csv", index=False)
    print("\n" + out.pivot_table(index=["level", "panel", "n_genes_measured"],
                                 columns="capture_rate", values="balanced_acc").to_string())
    print("\nwrote", O / "_STRESS_xenium_sparsity.csv")


if __name__ == "__main__":
    main()
