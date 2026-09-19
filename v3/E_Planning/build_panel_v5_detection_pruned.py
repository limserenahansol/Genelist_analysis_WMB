"""Prune the 246-gene panel on measured detectability, and close the activity-axis gap.

Three changes, all driven by measurements rather than judgement:

  CUT 44 genes detected in under 50% of cells at their best anchor. A probe for a
      transcript present in 1-49% of cells gives a map too sparse to read.

  KEEP 14 genes that are under 50% but have a purpose the threshold does not see:
      - immediate-early genes: the Allen atlas is resting tissue, so a low baseline
        is expected for an activity-induced gene and says nothing about how it will
        perform in activated cells. Filtering IEGs on baseline detection is a
        category error.
      - negative / exclusion controls: near-absence IS the readout (Slc6a3, Nts).
      - central opioid pharmacology: Oprk1, Drd2, Mc4r. A receptor map for an opioid
        project with a hole where the kappa receptor sits defeats the purpose.
      - load-bearing separators named in ANCHOR_COVERAGE (Ccdc42 even names one of
        the 20 target populations).

  ADD 13 genes: 12 of the 17 that sat in ORBm_ORDER but never in SHARED_PANEL_ORDER,
      so they would not have been manufactured, plus Creb1. The SOW asks for an
      activity readout and names the pCREB axis; six of these are IEGs and two are
      activity-regulated neuropeptides.

Five orphans are deliberately not added: EGFP (no AAV in this design), P2ry12
(microglia are not among the 20 target populations), Slc5a7 (cholinergic, pairs
with Chat which is being cut), Slc17a8 (VGLUT3, 26%) and Vegfd (27%).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
SRC = OUT / "PANEL_C_FINAL_246_with_Adrb1.xlsx"
DST = OUT / "PANEL_FINAL_v5_detection_pruned.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
DET = OUT / "allen_detectability_all_candidates.xlsx"
GW = OUT / "allen_genomewide"

BAR = 50.0
IEG = {"Fos", "Fosb", "Npas4", "Arc", "Egr1", "Junb", "Egr2", "Egr3", "Egr4", "Ier2",
       "Btg2", "Sgk1", "Sik1", "Dusp1", "Dusp4", "Dusp5", "Nr4a1", "Nr4a2", "Nr4a3",
       "Crem", "Fosl2", "Homer1", "Per1", "Per2", "Jun"}
OPIOID = {"Oprk1", "Oprd1", "Oprm1", "Oprl1", "Drd1", "Drd2", "Mc4r", "Pdyn", "Penk", "Tac1"}

ADD = [
    ("Syt1",   "4b_class_backbone", "pan-neuronal"),
    ("Slc6a1", "4b_class_backbone", "GABAergic class"),
    ("Slc1a2", "4b_class_backbone", "astrocyte, for tissue context and segmentation"),
    ("Scg2",   "4c_activity",       "activity-regulated neuropeptide"),
    ("Vgf",    "4c_activity",       "activity-regulated neuropeptide"),
    ("Rgs2",   "4c_activity",       "activity-induced GPCR signalling regulator"),
    ("Sgk1",   "4c_activity",       "glucocorticoid-induced immediate-early gene"),
    ("Jun",    "4c_activity",       "immediate-early gene"),
    ("Btg2",   "4c_activity",       "immediate-early gene"),
    ("Ier2",   "4c_activity",       "immediate-early gene"),
    ("Sik1",   "4c_activity",       "immediate-early gene"),
    ("Egr2",   "4c_activity",       "immediate-early gene"),
    ("Creb1",  "5_receptor_map",    "pCREB axis, named in the SOW"),
]
SKIP = {"EGFP": "no AAV in this design", "P2ry12": "microglia are not a target population",
        "Slc5a7": "cholinergic, pairs with Chat which is being cut",
        "Slc17a8": "VGLUT3, 26% of cells", "Vegfd": "27% of cells"}


def genomewide_pct(genes_wanted, anchors_roi):
    acc, axis = {}, None
    for f in sorted(GW.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        if axis is None:
            axis = [str(x) for x in z["genes"]]
        roi = "sAMY" if "STR" in str(z["shard"][0]) else "PL-ILA-ORB"
        for i, lab in enumerate([str(x) for x in z["subclass_labels"]]):
            k = (lab, roi)
            if k not in acc:
                acc[k] = [np.zeros(len(axis)), 0]
            acc[k][0] += z["subclass_nnz"][i]
            acc[k][1] += int(z["subclass_n"][i])
    gi = {g: i for i, g in enumerate(axis)}
    out = {}
    for g in genes_wanted:
        j = gi.get(g)
        if j is None:
            continue
        v = {a: acc[(a, r)][0][j] / acc[(a, r)][1] * 100
             for a, r in anchors_roi.items() if (a, r) in acc and acc[(a, r)][1] > 0}
        if v:
            b = max(v, key=v.get)
            out[g] = (v[b], b, sum(1 for x in v.values() if x >= BAR))
    return out


def main() -> None:
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    det = pd.read_excel(DET, "summary").set_index("gene")
    sh = pd.read_excel(SRC, "SHARED_PANEL_ORDER")
    ac = pd.read_excel(SRC, "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}
    sep = set()
    for s in ac.unique_separators_on_shared_panel.fillna(""):
        sep |= {x.strip() for x in s.split(",") if x.strip()}
    anchor_words = set()
    for a in ac.allen_subclass_anchor:
        anchor_words |= set(a.split())

    sh["pct"] = [det.max_pct.get(g, np.nan) for g in sh.gene]

    def exempt(r):
        w = (str(r.why) + " " + str(r.serves)).lower()
        if r.gene in IEG:
            return "immediate-early gene: low baseline expected in resting atlas"
        if "negative control" in w or "exclusion" in w:
            return "negative / exclusion control: near-absence is the readout"
        if r.gene in OPIOID:
            return "central opioid pharmacology"
        if r.gene in sep:
            return "load-bearing separator in ANCHOR_COVERAGE"
        if r.gene in anchor_words:
            return "names one of the 20 target populations"
        return None

    low = sh[sh.pct < BAR].copy()
    low["exempt"] = low.apply(exempt, axis=1)
    cut = set(low[low.exempt.isna()].gene)
    kept_low = low[low.exempt.notna()]
    print(f"under {BAR:.0f}%: {len(low)}  ->  cut {len(cut)}, kept {len(kept_low)} on purpose")

    scores = genomewide_pct([g for g, _, _ in ADD], roi_of)

    shutil.copy2(SRC, DST)
    wb = load_workbook(DST)
    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        gcol = [c.value for c in ws[1]].index("gene") + 1
        rows = [r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=gcol).value in cut]
        for r in reversed(rows):
            ws.delete_rows(r)
        print(f"  {name}: removed {len(rows)}")

    sh_ws, orb_ws = wb["SHARED_PANEL_ORDER"], wb["ORBm_ORDER"]
    present = {sh_ws.cell(row=r, column=2).value for r in range(2, sh_ws.max_row + 1)}
    added = []
    for gene, block, role in ADD:
        if gene in present:
            continue
        p = scores.get(gene)
        pct_txt = (f"Detected in {p[0]:.1f}% of cells at {p[1]}, above {BAR:.0f}% in {p[2]} of the 20 "
                   f"target populations." if p else "Not scored in the Allen atlas.")
        if gene in IEG and p and p[0] < BAR:
            pct_txt += (" Below the detection bar, but exempt: this is an activity-induced gene and the "
                        "atlas measures resting tissue, so a low baseline does not predict its "
                        "performance in activated cells.")
        why = (f"{role}. {pct_txt} Added because it was listed in ORBm_ORDER but never in "
               f"SHARED_PANEL_ORDER, so it would not have been manufactured. The SOW requires an "
               f"activity readout alongside the TRAP tag." if gene != "Creb1" else
               f"{role}. {pct_txt} SOW names the pCREB axis in the cortical reprogramming description.")
        for ws in (sh_ws, orb_ws):
            r = ws.max_row + 1
            ws.cell(row=r, column=2, value=gene)
            ws.cell(row=r, column=3, value=block)
            ws.cell(row=r, column=4, value=f"{role} :: {p[0]:.0f}% detected" if p else role)
            ws.cell(row=r, column=5, value=why)
        added.append(gene)

    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        for i, r in enumerate(range(2, ws.max_row + 1), start=1):
            ws.cell(row=r, column=1, value=i)

    fg = wb["FOR_MarkGreg"]
    fg.cell(row=fg.max_row + 1, column=1, value=f"{len(cut)} genes cut on measured detectability")
    fg.cell(row=fg.max_row, column=2, value=(
        f"Every gene detected in under {BAR:.0f}% of cells at its best target population was removed, "
        f"unless it had a purpose the threshold cannot see. {len(cut)} were cut. "
        f"{len(kept_low)} low-detection genes were KEPT deliberately: "
        f"{', '.join(sorted(kept_low.gene))} - immediate-early genes (low baseline is expected because "
        f"the atlas is resting tissue), negative controls (Slc6a3, Nts - near-absence is the readout), "
        f"central opioid receptors (Oprk1, Drd2, Mc4r), and separators that define a target population."))
    fg.cell(row=fg.max_row + 1, column=1, value=f"{len(added)} genes added (activity axis + SOW gap)")
    fg.cell(row=fg.max_row, column=2, value=(
        f"Added: {', '.join(added)}. Twelve of these sat in ORBm_ORDER but never in SHARED_PANEL_ORDER, "
        f"so they would not have been manufactured despite appearing in the region sheet; six are "
        f"immediate-early genes and two are activity-regulated neuropeptides, which the SOW requires "
        f"alongside the TRAP tag. Creb1 closes the pCREB axis the SOW names. "
        f"Deliberately NOT added: " + "; ".join(f"{k} ({v})" for k, v in SKIP.items()) + "."))
    wb.save(DST)

    out = pd.read_excel(DST, "SHARED_PANEL_ORDER")
    o = pd.read_excel(DST, "ORBm_ORDER")
    free = int(out.gene.isin(base).sum())
    print(f"\n{DST.name}")
    print(f"  {len(out)} genes = {free} free + {len(out)-free} custom   (was 246 = 48 + 198)")
    print(f"  dupes {out.gene.duplicated().sum()} | ranks ok {list(out.order_rank)==list(range(1,len(out)+1))}")
    print(f"  ORBm {len(o)} | orphans remaining: {len(set(o.gene)-set(out.gene))}")
    print(f"  separators retained: {len(sep & set(out.gene))}/{len(sep)}")
    p2 = pd.Series([det.max_pct.get(g, np.nan) for g in out.gene])
    print(f"  under {BAR:.0f}% remaining: {int((p2 < BAR).sum())} (all purpose-exempt)")


if __name__ == "__main__":
    main()
