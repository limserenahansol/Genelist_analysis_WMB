"""Measure every candidate gene in the ORBm/BMAp Allen cells - one source of truth.

Writes, for all 585 genes with per-cell data (226,886 cells; ORBm = PL-ILA-ORB
106,122, BMAp = sAMY 120,764):
  _MEAS_by_subclass.csv    detection % in each of the 79 subclasses present
  _MEAS_by_anchor.csv      detection % in each of the 20 target populations
  _MEAS_gene_summary.csv   best subclass / best anchor / gap / n>=50%
  _MEAS_supertype.csv      per gene x supertype inside an anchor: in-%, out-% and gap
                           (the measured version of "can this gene split an anchor")
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
SH = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
      "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
      "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
      "STR": "WMB-10Xv3-STR"}
MIN_CELLS = 60


def main() -> None:
    X = np.load(O / "_cacheX2.npy")
    genes = (O / "_cacheG2.txt").read_text().split()
    md = pd.read_parquet(O / "_cacheMD.parquet")
    # + the Jesse n_orbm=3 block extracted last
    parts, gj = [], None
    for f in sorted(glob.glob(str(O / "allen_extract" / "*.npz"))):
        z = np.load(f, allow_pickle=True)
        zz = np.load(O / "allen_extract_jesse3" / f"{SH[os.path.basename(f)[:-4]]}.npz",
                     allow_pickle=True)
        assert list(zz["cell"]) == list(z["cell"])
        parts.append(zz["X"])
        g = [str(x) for x in zz["genes"]]
        gj = g if gj is None else gj
        assert g == gj
    X = np.hstack([X, np.vstack(parts)])
    genes = genes + gj
    print(f"{X.shape[0]:,} cells x {X.shape[1]} genes", flush=True)

    det = X > 0
    del X

    ac = pd.read_excel(O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx", "ANCHOR_COVERAGE")
    anchor_roi = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
                  for r in ac.itertuples()}

    # ---- per subclass (all 79 present, both ROIs pooled) ----
    rows = []
    for sc, idx in md.groupby("subclass").indices.items():
        if len(idx) < MIN_CELLS:
            continue
        rows.append(pd.Series(det[idx].mean(0) * 100, index=genes, name=sc))
    bysc = pd.DataFrame(rows)
    bysc.index.name = "subclass"
    bysc.round(2).to_csv(O / "_MEAS_by_subclass.csv")
    print(f"subclasses >= {MIN_CELLS} cells: {len(bysc)}", flush=True)

    # ---- per anchor (subclass restricted to its own region) ----
    rows, ncell = [], {}
    for a, roi in anchor_roi.items():
        m = ((md.subclass == a) & (md.roi == roi)).to_numpy()
        if m.sum() < MIN_CELLS:
            continue
        ncell[a] = int(m.sum())
        rows.append(pd.Series(det[m].mean(0) * 100, index=genes, name=a))
    byan = pd.DataFrame(rows)
    byan.index.name = "anchor"
    byan.round(2).to_csv(O / "_MEAS_by_anchor.csv")

    # ---- gene summary ----
    out = []
    for g in genes:
        s, a = bysc[g], byan[g]
        top = s.sort_values(ascending=False)
        ta = a.sort_values(ascending=False)
        out.append({
            "gene": g,
            "best_subclass": top.index[0], "best_subclass_pct": round(float(top.iloc[0]), 1),
            "gap_vs_median_subclass_pp": round(float(top.iloc[0] - s.median()), 1),
            "n_subclasses_ge50": int((s >= 50).sum()), "n_subclasses": len(s),
            "best_anchor": ta.index[0], "best_anchor_pct": round(float(ta.iloc[0]), 1),
            "n_anchors_ge50": int((a >= 50).sum()), "n_anchors": len(a),
            "pct_all_cells": round(float(det[:, genes.index(g)].mean() * 100), 1),
        })
    summ = pd.DataFrame(out)
    summ.to_csv(O / "_MEAS_gene_summary.csv", index=False)

    # ---- supertype resolution inside each anchor ----
    srows = []
    for a, roi in anchor_roi.items():
        m = ((md.subclass == a) & (md.roi == roi)).to_numpy()
        if m.sum() < MIN_CELLS:
            continue
        sup = md.supertype[m].to_numpy()
        Dm = det[m]
        vc = pd.Series(sup).value_counts()
        vc = vc[vc >= MIN_CELLS]
        if len(vc) < 2:
            continue
        for s in vc.index:
            inm = sup == s
            pin = Dm[inm].mean(0) * 100
            pout = Dm[~inm].mean(0) * 100
            for gi2, g in enumerate(genes):
                if pin[gi2] >= 50 and pin[gi2] - pout[gi2] >= 20:
                    srows.append({"anchor": a, "supertype": s, "n_cells": int(inm.sum()),
                                  "gene": g, "pct_in": round(float(pin[gi2]), 1),
                                  "pct_rest_of_anchor": round(float(pout[gi2]), 1),
                                  "gap_pp": round(float(pin[gi2] - pout[gi2]), 1)})
    sup = pd.DataFrame(srows)
    sup.to_csv(O / "_MEAS_supertype.csv", index=False)
    print(f"supertype separator hits: {len(sup)} over "
          f"{sup.supertype.nunique() if len(sup) else 0} supertypes", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
