"""Does the 301-panel's 'Allen supertype discovery' block actually help aim 1?

Aim 1 of the SOW is to find the cell type(s) - new or existing - that the TRAP+
neurons belong to. At subclass level that is "name the type"; at supertype level it
is "split an anchor into sub-populations", which is the discovery question.

The 56-gene discovery block in FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx was
chosen from per-subclass aggregates; 46 of the 56 had never been measured per cell,
so its contribution was never tested. This scores, on held-out cells, 3 seeds:

  base only            the 10x Mouse Brain base panel (reference floor)
  v8 237               the goal-aligned panel
  v8 237 + disc46      v8 plus the unmeasured discovery genes
  301 panel            the discovery-heavy alternative
  ceiling              every gene extracted (560)
"""
from __future__ import annotations

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
SEEDS = [0, 1, 2]
MIN_CELLS = 60
CAP = 1200

SHARD = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
         "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
         "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
         "STR": "WMB-10Xv3-STR"}


def load():
    mats, metas, genes = [], [], None
    for f in sorted((O / "allen_extract").glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        X = z["X"]
        g = [str(x) for x in z["genes"]]
        for d in ("allen_extract_gap", "allen_extract_disc"):
            p = O / d / f"{SHARD[f.stem]}.npz"
            if p.exists():
                zz = np.load(p, allow_pickle=True)
                assert list(zz["cell"]) == list(z["cell"]), f"{f.name}/{d}: cell order differs"
                X = np.hstack([X, zz["X"]])
                g += [str(x) for x in zz["genes"]]
        if genes is None:
            genes = g
        elif g != genes:
            raise SystemExit(f"{f.name}: gene order differs")
        mats.append(X)
        metas.append(pd.DataFrame({"roi": [str(x) for x in z["roi"]],
                                   "subclass": [str(x) for x in z["subclass"]],
                                   "supertype": [str(x) for x in z["supertype"]]}))
    return np.vstack(mats), genes, pd.concat(metas, ignore_index=True)


def subsample(y, seed):
    rng = np.random.RandomState(seed)
    keep = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        keep.append(idx if len(idx) <= CAP else rng.choice(idx, CAP, replace=False))
    return np.sort(np.concatenate(keep))


def score(X, y, cols, seed):
    tr, te, ytr, yte = train_test_split(X[:, cols], y, test_size=0.3,
                                        random_state=seed, stratify=y)
    sc = StandardScaler().fit(tr)
    clf = LogisticRegression(max_iter=1000, n_jobs=-1, C=1.0).fit(sc.transform(tr), ytr)
    return balanced_accuracy_score(yte, clf.predict(sc.transform(te)))


def main() -> None:
    X, genes, md = load()
    gi = {g: i for i, g in enumerate(genes)}
    print(f"matrix {X.shape[0]:,} cells x {X.shape[1]} genes", flush=True)

    base = set(pd.read_csv(O / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    v8 = set(pd.read_excel(O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx",
                           "SHARED_PANEL_ORDER").gene.astype(str))
    s301 = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx", "SHARED_PANEL_ORDER")
    p301 = set(s301.gene.astype(str))
    disc = set(s301[s301.block == "20_Allen_supertype_discovery"].gene.astype(str))
    disc_new = sorted(g for g in disc if g in gi and g not in v8)
    print(f"discovery genes measurable and not in v8: {len(disc_new)}", flush=True)

    SETS = {
        "base only (248)": base,
        "v8 237 + base": v8 | base,
        "v8 237 + disc + base": v8 | base | set(disc_new),
        "301 panel + base": p301 | base,
        "ceiling (all extracted)": set(genes),
    }
    for nm, S in SETS.items():
        print(f"  {nm:26s} {len([g for g in S if g in gi]):4d} genes measured", flush=True)

    # ---- subclass level ----
    keep = (md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS).to_numpy()
    y_all, X_all = md.subclass[keep].to_numpy(), X[keep]
    rows = []
    for nm, S in SETS.items():
        cols = np.array(sorted(gi[g] for g in S if g in gi))
        accs = []
        for sd in SEEDS:
            sel = subsample(y_all, sd)
            accs.append(score(X_all[sel], y_all[sel], cols, sd))
        rows.append({"gene_set": nm, "n_genes": len(cols), "level": "subclass",
                     "mean": round(float(np.mean(accs)), 4), "sd": round(float(np.std(accs)), 4)})
        print(f"SUBCLASS {nm:26s} {np.mean(accs):.4f} +- {np.std(accs):.4f}", flush=True)

    # ---- supertype level, inside each anchor ----
    ac = pd.read_excel(O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx", "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}
    per = []
    for a, roi in roi_of.items():
        m = ((md.subclass == a) & (md.roi == roi)).to_numpy()
        vc = md.supertype[m].value_counts()
        vc = vc[vc >= MIN_CELLS]
        if len(vc) < 2:
            continue
        mm = m.copy()
        mm[mm] = md.supertype[m].isin(vc.index).to_numpy()
        ys_all, Xs_all = md.supertype[mm].to_numpy(), X[mm]
        rec = {"anchor": a, "n_cells": int(mm.sum()), "n_supertypes": len(vc)}
        for nm, S in SETS.items():
            cols = np.array(sorted(gi[g] for g in S if g in gi))
            accs = []
            for sd in SEEDS:
                sel = subsample(ys_all, sd)
                accs.append(score(Xs_all[sel], ys_all[sel], cols, sd))
            rec[nm] = round(float(np.mean(accs)), 4)
        per.append(rec)
        print("  " + f"{a[:34]:34s} " + " ".join(f"{nm.split()[0]}:{rec[nm]:.3f}" for nm in SETS),
              flush=True)
    per = pd.DataFrame(per)
    for nm in SETS:
        rows.append({"gene_set": nm, "n_genes": len([g for g in SETS[nm] if g in gi]),
                     "level": "supertype (mean over anchors)",
                     "mean": round(float(per[nm].mean()), 4), "sd": None})
        print(f"SUPERTYPE {nm:26s} {per[nm].mean():.4f}", flush=True)

    with pd.ExcelWriter(O / "BENCH_discovery_vs_v8.xlsx", engine="openpyxl") as w:
        pd.DataFrame(rows).to_excel(w, "summary", index=False)
        per.to_excel(w, "per_anchor_supertype", index=False)
        pd.DataFrame({"discovery_gene_added": disc_new}).to_excel(w, "disc_genes_added", index=False)
    print("wrote", O / "BENCH_discovery_vs_v8.xlsx")


if __name__ == "__main__":
    main()
