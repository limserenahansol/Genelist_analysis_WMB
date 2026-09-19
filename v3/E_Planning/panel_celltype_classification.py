"""Can the panel actually NAME the cell type of a cell? Measured, on held-out cells.

This is the load-bearing claim of the whole design and it had never been tested
directly. Every previous metric asked "does some gene mark population X with a big
gap" - but cell types are called COMBINATORIALLY, so a single-marker test both
understates the panel and is insensitive to it (23/79 for the 178-, 232- and
252-gene panels alike).

The honest test: train a classifier on Allen cells using ONLY the genes a given
panel measures, then ask it to label held-out cells. Accuracy on the held-out set
is a fair estimate of "given Xenium measurements of these genes, can I assign this
tdTomato+ cell to a cell type". The gene set is fixed before the split, so this is
not the selection-data circularity that invalidated the earlier 96/96 figure.

Two readouts:
  subclass level   can I name the cell TYPE (the 20 anchors + everything else present)
  supertype level  can I split a big anchor into SUB-populations - the "find new
                   sub-types of TRAP+ cells" goal

Also reported in a Xenium-pessimistic binarised mode (detected / not detected),
since Xenium yields far fewer transcripts per cell than 10x scRNA-seq. Absolute
numbers here are optimistic relative to real Xenium; the comparison BETWEEN gene
sets is the point.
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
EX = O / "allen_extract"
GAP = O / "allen_extract_gap"
SEED = 0
MIN_CELLS = 60


def load() -> tuple[np.ndarray, list[str], pd.DataFrame]:
    mats, metas, genes = [], [], None
    for f in sorted(EX.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        g = [str(x) for x in z["genes"]]
        shard = f.stem
        gf = GAP / f"{_shard_name(shard)}.npz"
        X = z["X"]
        if gf.exists():
            zg = np.load(gf, allow_pickle=True)
            assert list(zg["cell"]) == list(z["cell"]), f"{f.name}: cell order differs"
            X = np.hstack([X, zg["X"]])
            g = g + [str(x) for x in zg["genes"]]
        if genes is None:
            genes = g
        elif g != genes:
            raise SystemExit(f"{f.name}: gene order differs")
        mats.append(X)
        metas.append(pd.DataFrame({
            "roi": [str(x) for x in z["roi"]],
            "subclass": [str(x) for x in z["subclass"]],
            "supertype": [str(x) for x in z["supertype"]],
        }))
        print(f"  {f.name}: {X.shape}", flush=True)
    return np.vstack(mats), genes, pd.concat(metas, ignore_index=True)


def _shard_name(stem: str) -> str:
    m = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
         "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
         "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
         "STR": "WMB-10Xv3-STR"}
    return m.get(stem, stem)


CAP = 1200   # cells per class, so a 40,000-cell anchor cannot drown a 200-cell one


def subsample(y: np.ndarray, cap: int = CAP) -> np.ndarray:
    """Index of a class-balanced subsample - keeps the fits tractable and makes
    balanced accuracy a fair statistic rather than one dominated by L6 CT."""
    rng = np.random.RandomState(SEED)
    keep = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        keep.append(idx if len(idx) <= cap else rng.choice(idx, cap, replace=False))
    return np.sort(np.concatenate(keep))


def score(X, y, cols, binary=False):
    """Balanced accuracy on a held-out 30% split, using only columns `cols`."""
    Xs = (X[:, cols] > 0).astype(np.float32) if binary else X[:, cols]
    tr, te, ytr, yte = train_test_split(Xs, y, test_size=0.3, random_state=SEED, stratify=y)
    sc = StandardScaler().fit(tr)
    clf = LogisticRegression(max_iter=1000, n_jobs=-1, C=1.0)
    clf.fit(sc.transform(tr), ytr)
    pred = clf.predict(sc.transform(te))
    return balanced_accuracy_score(yte, pred), pred, yte


def main() -> None:
    X, genes, md = load()
    gi = {g: i for i, g in enumerate(genes)}
    print(f"combined: {X.shape[0]:,} cells x {X.shape[1]} genes\n", flush=True)

    base = set(pd.read_csv(O / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    SETS = {
        "base only (248, free)": base,
        "IDEAL 178 + base": set(pd.read_excel(O / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                                              "SHARED_PANEL_ORDER").gene.astype(str)) | base,
        "v6 232 + base": set(pd.read_excel(O / "PANEL_FINAL_v6_ORBm_BMAp_complete.xlsx",
                                           "SHARED_PANEL_ORDER").gene.astype(str)) | base,
        "v7 252 + base": set(pd.read_excel(O / "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx",
                                           "SHARED_PANEL_ORDER").gene.astype(str)) | base,
        "ALL extracted (ceiling)": set(genes),
    }

    # ---------- subclass level, all cells in the section ----------
    keep = md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS
    y_all = md.subclass[keep].to_numpy()
    X_all = X[keep.to_numpy()]
    sel = subsample(y_all)
    y_sub, Xk = y_all[sel], X_all[sel]
    print(f"SUBCLASS task: {Xk.shape[0]:,} cells (capped at {CAP}/class from "
          f"{X_all.shape[0]:,}), {len(set(y_sub))} classes (>= {MIN_CELLS} cells)\n", flush=True)

    rows = []
    for nm, S in SETS.items():
        cols = np.array(sorted(gi[g] for g in S if g in gi))
        acc, _, _ = score(Xk, y_sub, cols)
        accb, _, _ = score(Xk, y_sub, cols, binary=True)
        rows.append({"gene_set": nm, "n_genes_measured": len(cols),
                     "subclass_balanced_acc": round(acc, 4),
                     "subclass_binarised": round(accb, 4)})
        print(f"  {nm:26s} {len(cols):4d} genes -> balanced acc {acc:.3f} "
              f"| binarised {accb:.3f}", flush=True)

    # ---------- supertype level, inside the big anchors ----------
    ac = pd.read_excel(O / "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx", "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}
    print("\nSUPERTYPE task (splitting each anchor into its sub-populations):", flush=True)
    sup_rows = []
    for a, roi in roi_of.items():
        m = ((md.subclass == a) & (md.roi == roi)).to_numpy()
        sub = md.supertype[m]
        vc = sub.value_counts()
        vc = vc[vc >= MIN_CELLS]
        if len(vc) < 2:
            continue
        mm = m.copy()
        mm[mm] = sub.isin(vc.index).to_numpy()
        ys_all = md.supertype[mm].to_numpy()
        Xs_all = X[mm]
        ssel = subsample(ys_all)
        ys, Xs = ys_all[ssel], Xs_all[ssel]
        rec = {"anchor": a, "n_cells": int(mm.sum()), "n_supertypes": len(vc)}
        for nm, S in SETS.items():
            cols = np.array(sorted(gi[g] for g in S if g in gi))
            try:
                acc, _, _ = score(Xs, ys, cols)
            except ValueError:
                acc = float("nan")
            rec[nm] = round(acc, 3)
        sup_rows.append(rec)
        print(f"  {a[:36]:36s} n={rec['n_cells']:6,d} k={len(vc):2d}  " +
              "  ".join(f"{nm.split()[0]}:{rec[nm]:.2f}" for nm in SETS), flush=True)

    sup = pd.DataFrame(sup_rows)
    res = pd.DataFrame(rows)
    if len(sup):
        for nm in SETS:
            res.loc[res.gene_set == nm, "supertype_mean_acc"] = round(float(sup[nm].mean()), 4)

    with pd.ExcelWriter(O / "PANEL_celltype_classification.xlsx", engine="openpyxl") as w:
        pd.DataFrame({"item": ["What this measures", "Why it is the right test",
                               "Split", "Caveat"],
                      "detail": [
            "Balanced accuracy of a multinomial logistic classifier that sees ONLY the genes a "
            "given panel measures, labelling held-out Allen cells with their subclass (cell type) "
            "or supertype (sub-population).",
            "The panel's job is to let you name the cell type of a tdTomato+ cell. Cell types are "
            "called from gene COMBINATIONS, so a single-marker gap test is the wrong instrument - "
            "it scored 23/79 identically for the 178-, 232- and 252-gene panels.",
            "Stratified 70/30 train/test, seed 0. The gene set is fixed before the split, so this "
            "is not selection-data circularity.",
            "Trained on 10x scRNA-seq. Real Xenium has far fewer transcripts per cell and "
            "segmentation error, so absolute accuracy here is optimistic. The comparison BETWEEN "
            "gene sets is what this supports.",
        ]}).to_excel(w, "READ_ME", index=False)
        res.to_excel(w, "summary", index=False)
        if len(sup):
            sup.to_excel(w, "per_anchor_supertype", index=False)
    print(f"\nwrote {O / 'PANEL_celltype_classification.xlsx'}")


if __name__ == "__main__":
    main()
