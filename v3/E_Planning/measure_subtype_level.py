"""Per-cell detection AND level for a gene inside the SUB-POPULATION it is meant to mark.

A subtype marker is judged in its own supertype, not in the parent cell type. Hpse is
the clean example: 88 pct of the 229 cells of supertype 0220 Sst Gaba_7, but only 11
pct of the 5,267-cell 053 Sst Gaba subclass those cells sit in. Scoring it at subclass
level would call a good subtype marker "too low", which is the same category error that
wrongly cut Cx3cr1 and Chat in earlier versions.

Writes _MEAS_subtype_level.csv: gene x target supertype, pct in it, mean log2 in it,
pct in the rest of the parent cell type, and the gap.
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SH = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
      "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
      "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
      "STR": "WMB-10Xv3-STR"}
MIN_CELLS = 40


def load() -> tuple[np.ndarray, list[str], pd.DataFrame]:
    X = np.load(O / "_cacheX2.npy")
    genes = (O / "_cacheG2.txt").read_text().split()
    md = pd.read_parquet(O / "_cacheMD.parquet")
    for extra in ("allen_extract_jesse3", "allen_extract_v9gap"):
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
            assert g == gj
        if parts:
            X = np.hstack([X, np.vstack(parts)])
            genes = genes + gj
            print(f"  + {extra}: {len(gj)} genes", flush=True)
    return X, genes, md


def main() -> None:
    X, genes, md = load()
    gi = {g: i for i, g in enumerate(genes)}
    print(f"{X.shape[0]:,} cells x {X.shape[1]} genes", flush=True)

    v9 = pd.read_excel(O / "PANEL_FINAL_v9_ORBm_BMAp_UNLIMITED.xlsx", "FINAL_GENE_LIST")
    gw = pd.read_excel(DL / "allen_genomewide_marker_search.xlsx", "supertype_markers")
    gwa = pd.read_excel(DL / "allen_genomewide_marker_search.xlsx", "anchor_markers")
    ac = pd.read_excel(O / "PANEL_FINAL_v9_ORBm_BMAp_UNLIMITED.xlsx", "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}

    rows = []
    sub = v9[v9.block == "28_subtype_discovery"]
    for g in sub.gene:
        if g not in gi:
            continue
        cand = gw[(gw.gene == g) & (gw.parent_subclass.isin(roi_of))].sort_values("gap", ascending=False)
        if not len(cand):
            continue
        r = cand.iloc[0]
        a, s = r.parent_subclass, r.group
        m = ((md.subclass == a) & (md.roi == roi_of[a])).to_numpy()
        insup = m & (md.supertype == s).to_numpy()
        rest = m & ~insup
        if insup.sum() < MIN_CELLS:
            continue
        col = X[:, gi[g]]
        rows.append({"gene": g, "role": "subtype marker", "target_population": s,
                     "parent_cell_type": a, "n_cells_target": int(insup.sum()),
                     "pct_in_target": round(float((col[insup] > 0).mean() * 100), 1),
                     "mean_log2_in_target": round(float(col[insup].mean()), 2),
                     "pct_in_rest_of_parent": round(float((col[rest] > 0).mean() * 100), 1),
                     "gap_pp": round(float((col[insup] > 0).mean() * 100
                                           - (col[rest] > 0).mean() * 100), 1)})
    anc = v9[v9.block == "29_anchor_marker"]
    for g in anc.gene:
        if g not in gi:
            continue
        cand = gwa[(gwa.gene == g) & (gwa.group.isin(roi_of))].sort_values("gap", ascending=False)
        if not len(cand):
            continue
        a = cand.iloc[0].group
        m = ((md.subclass == a) & (md.roi == roi_of[a])).to_numpy()
        other = (md.subclass.isin([x for x in roi_of if x != a])).to_numpy()
        col = X[:, gi[g]]
        rows.append({"gene": g, "role": "cell-type marker", "target_population": a,
                     "parent_cell_type": a, "n_cells_target": int(m.sum()),
                     "pct_in_target": round(float((col[m] > 0).mean() * 100), 1),
                     "mean_log2_in_target": round(float(col[m].mean()), 2),
                     "pct_in_rest_of_parent": round(float((col[other] > 0).mean() * 100), 1),
                     "gap_pp": round(float((col[m] > 0).mean() * 100
                                           - (col[other] > 0).mean() * 100), 1)})
    out = pd.DataFrame(rows)
    out.to_csv(O / "_MEAS_subtype_level.csv", index=False)
    print(out.to_string(index=False), flush=True)
    print(f"\n{len(out)} genes scored in their own target population", flush=True)


if __name__ == "__main__":
    main()
