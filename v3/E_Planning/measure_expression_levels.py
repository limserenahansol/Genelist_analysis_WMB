"""Expression LEVEL, not just detection rate, for every measured gene.

"Is this gene expressed well enough in ORBm/BMAp to be usable?" needs the mean
log2(CPM+1) inside the population, not only the percent of cells with a nonzero
count. A gene can be detected in 60 pct of cells at a level that is one transcript
per cell, which in Xenium is indistinguishable from background.

Writes:
  _MEAS_mean_by_anchor.csv     mean log2 expression in each of the 20 target populations
  _MEAS_mean_by_subclass.csv   the same for all 75 subclasses present
  _MEAS_level_summary.csv      per gene: best anchor level, pooled ORBm level, pooled BMAp
                               level, and a usable/marginal/too-low verdict
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


def load() -> tuple[np.ndarray, list[str], pd.DataFrame]:
    X = np.load(O / "_cacheX2.npy")
    genes = (O / "_cacheG2.txt").read_text().split()
    md = pd.read_parquet(O / "_cacheMD.parquet")
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
    return np.hstack([X, np.vstack(parts)]), genes + gj, md


def main() -> None:
    X, genes, md = load()
    print(f"{X.shape[0]:,} cells x {X.shape[1]} genes", flush=True)
    ac = pd.read_excel(O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx", "ANCHOR_COVERAGE")
    anchor_roi = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
                  for r in ac.itertuples()}

    rows = []
    for sc, idx in md.groupby("subclass").indices.items():
        if len(idx) < MIN_CELLS:
            continue
        rows.append(pd.Series(X[idx].mean(0), index=genes, name=sc))
    bysc = pd.DataFrame(rows)
    bysc.index.name = "subclass"
    bysc.round(3).to_csv(O / "_MEAS_mean_by_subclass.csv")

    rows = []
    for a, roi in anchor_roi.items():
        m = ((md.subclass == a) & (md.roi == roi)).to_numpy()
        if m.sum() < MIN_CELLS:
            continue
        rows.append(pd.Series(X[m].mean(0), index=genes, name=a))
    byan = pd.DataFrame(rows)
    byan.index.name = "anchor"
    byan.round(3).to_csv(O / "_MEAS_mean_by_anchor.csv")

    orb = (md.roi == "PL-ILA-ORB").to_numpy()
    bma = (md.roi == "sAMY").to_numpy()
    det = pd.read_csv(O / "_MEAS_by_anchor.csv", index_col=0)
    out = []
    for i, g in enumerate(genes):
        lv = byan[g]
        top = lv.sort_values(ascending=False)
        pct = det[g] if g in det.columns else pd.Series(dtype=float)
        best_pct = float(pct.max()) if len(pct) else np.nan
        lvl = float(top.iloc[0])
        # level bands: log2(CPM+1) means of the cells in the population
        if lvl >= 2.0 and best_pct >= 50:
            verdict = "usable - strong"
        elif lvl >= 1.0 and best_pct >= 50:
            verdict = "usable - moderate"
        elif best_pct >= 50:
            verdict = "marginal - detected in most cells but low level"
        elif lvl >= 1.0:
            verdict = "marginal - decent level in a minority of cells"
        else:
            verdict = "too low to map reliably"
        out.append({"gene": g,
                    "best_anchor_by_level": top.index[0],
                    "mean_log2_at_best_anchor": round(lvl, 3),
                    "mean_log2_ORBm_all_cells": round(float(X[orb, i].mean()), 3),
                    "mean_log2_BMAp_all_cells": round(float(X[bma, i].mean()), 3),
                    "max_pct_any_anchor": round(best_pct, 1) if not np.isnan(best_pct) else np.nan,
                    "level_verdict": verdict})
    pd.DataFrame(out).to_csv(O / "_MEAS_level_summary.csv", index=False)
    print(pd.DataFrame(out).level_verdict.value_counts().to_string(), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
