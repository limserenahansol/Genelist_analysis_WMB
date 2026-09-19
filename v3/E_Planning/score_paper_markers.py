"""Score the paper-suggested markers that had never been measured locally.

Ten genes from the published ORBm/BMAp marker lists (Lui 2021, Hochgerner 2023, the
v6 canonical marker set) were on no panel and had no Allen number: Cd36, Crym, Cux1,
Fst, Pax6, Reln, Scnn1a, Tcf4, Tshz1, Whrn. A paper naming a gene is a hypothesis; the
Allen cells decide. Each is scored in the cell type the paper assigned it to.

include = True means it passes the same rule as every other cell-type marker here:
>=50 pct of cells in the assigned population and >=20pp above the other populations.

Writes _MEAS_paper_markers.csv.
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
IN = V3 / "inputs"
SH = {"Isocortex-v2-1": "WMB-10Xv2-Isocortex-1", "Isocortex-v2-2": "WMB-10Xv2-Isocortex-2",
      "Isocortex-3": "WMB-10Xv2-Isocortex-3", "Isocortex-v2-4": "WMB-10Xv2-Isocortex-4",
      "Isocortex-v3-1": "WMB-10Xv3-Isocortex-1", "Isocortex-v3-2": "WMB-10Xv3-Isocortex-2",
      "STR": "WMB-10Xv3-STR"}


def main() -> None:
    md = pd.read_parquet(O / "_cacheMD.parquet")
    parts, genes = [], None
    for f in sorted(glob.glob(str(O / "allen_extract" / "*.npz"))):
        z = np.load(f, allow_pickle=True)
        zz = np.load(O / "allen_extract_paper" / f"{SH[os.path.basename(f)[:-4]]}.npz",
                     allow_pickle=True)
        assert list(zz["cell"]) == list(z["cell"])
        parts.append(zz["X"])
        g = [str(x) for x in zz["genes"]]
        genes = g if genes is None else genes
        assert g == genes
    X = np.vstack(parts)
    print(f"{X.shape[0]:,} cells x {len(genes)} genes: {genes}", flush=True)

    ac = pd.read_excel(O / "PANEL_FINAL_v9_ORBm_BMAp_UNLIMITED.xlsx", "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}
    a2 = pd.read_csv(IN / "celltype_to_subclass_anchor.csv")
    a2 = a2[a2.region_user.isin(["ORBm", "BMAp"])]
    cm = pd.read_csv(IN / "curated_marker_template.csv")
    cm = cm[cm.region_user.isin(["ORBm", "BMAp"])]

    masks = {a: ((md.subclass == a) & (md.roi == roi_of[a])).to_numpy() for a in roi_of}
    rows = []
    for j, g in enumerate(genes):
        col = X[:, j]
        assigned = []
        for r in cm.itertuples():
            if g in [x.strip() for x in str(r.marker_genes).split(",")]:
                assigned += [a for a in a2.allen_subclass_anchor[
                    (a2.region_user == r.region_user) & (a2.cell_type_label == r.cell_type_label)]
                    if a in masks]
        assigned = list(dict.fromkeys(assigned))
        if not assigned:
            continue
        pct = {a: float((col[masks[a]] > 0).mean() * 100) for a in masks}
        lv = {a: float(col[masks[a]].mean()) for a in masks}
        best = max(assigned, key=lambda a: pct[a])
        others = [a for a in masks if a not in assigned]
        out_max = max(pct[a] for a in others) if others else 0.0
        rows.append({"gene": g, "assigned_cell_types": "; ".join(assigned),
                     "best_assigned_population": best,
                     "pct_in_assigned": round(pct[best], 1),
                     "mean_log2_in_assigned": round(lv[best], 2),
                     "pct_in_highest_other_population": round(out_max, 1),
                     "gap_pp": round(pct[best] - out_max, 1),
                     "include": bool(pct[best] >= 50 and pct[best] - out_max >= 20),
                     "top_population_overall": max(pct, key=pct.get),
                     "pct_top_population_overall": round(max(pct.values()), 1)})
    out = pd.DataFrame(rows).sort_values("gap_pp", ascending=False)
    out.to_csv(O / "_MEAS_paper_markers.csv", index=False)
    print(out.to_string(index=False), flush=True)
    print(f"\npass: {int(out.include.sum())} of {len(out)}", flush=True)


if __name__ == "__main__":
    main()
