"""v10 - the final ORBm + BMAp gene list: everything necessary, nothing redundant.

Every gene is here because it is biologically load-bearing for one of the categories
asked for AND measured in the Allen WMB-10X cells of these two regions - both as a
detection rate (percent of cells with a nonzero count) and as an expression LEVEL
(mean log2(CPM+1) inside the population it is meant to report). 226,886 cells:
ORBm = ROI PL-ILA-ORB 106,122, BMAp = ROI sAMY 120,764.

Rules
  R1 cell-type / subtype marker: >=50 pct of cells in the population it names AND
     >=20pp above the competing populations (anchor level) or above its sibling
     sub-populations (subtype level). This is the "distinguishable" test.
  R2 GPCR / TF / plasticity / IEG / morphine gene: may be broadly expressed - its job
     is to be read as a LEVEL inside an already-named cell type - but it must clear
     the same detection bar somewhere in ORBm/BMAp, because a probe detected in a few
     percent of cells buys an empty map.
  R3 every gene is scored in ITS OWN population, not only in the 20 neuronal anchors.
     Scoring a microglial or cholinergic gene in cortical pyramidal cells is the error
     that got Cx3cr1 and Chat wrongly cut in earlier versions.
  R4 SOW-named genes are kept even when the level is low: the SOW asks whether they are
     expressed, so a negative result is a result. Flagged sow_named = TRUE.
  R5 standalone panel: the 248-gene 10x Mouse Brain base panel is NOT included, so
     nothing is free and each non-neuronal class needs ONE marker of its own (28 pct of
     the section is non-neuronal and Xenium segments every cell). This reverses the v8
     cuts of P2ry12 / Rgs5 / Vtn, which were justified only by "free on base".
  R6 ORBm and BMAp only. MEA / CEA / BST subclasses are carried as NEIGHBOUR CONTROLS
     and are labelled as such - BMAp is not MEA/CEA.
  R7 no second marker for a population that already has one, and no circadian or sex
     genes: not asked for. Everything dropped under R7 is kept in OPTIONAL_ADD_ONS with
     its measured numbers, so any of it can go back in with one edit.

Built as v8 (237) + measured additions, then trimmed under R7:
  MORPHINE    every Jesse opioid-dependence DEG that is DE in >=4 of the 12 ORBm cell
              types AND detected in >=50 pct of cells (the n_orbm=3 tier is in
              OPTIONAL_ADD_ONS).
  SUBTYPE     the minimum set that gives each of the 96 sub-populations nested in the 20
              cell types its own dedicated marker: 66/96 had one on v8, 96/96 now.
  ANCHOR      004 L6 IT and 032 L5 NP were the only cell types with no dedicated single
              marker on v8 (they were called combinatorially): Bmp3 and Vwc2l.
  NON-NEURON  one marker per non-neuronal class.
  Rbms3       99.5 pct marker of 120 MEA Otp Foxp2 Glut, the BMAp VGLUT2 cell type.
  NOT ADDED   the 10 published markers that had never been measured (Cux1, Scnn1a, Crym,
              Tcf4, Reln, Pax6, Tshz1, Cd36, Fst, Whrn): all 10 fail R1 in the Allen
              cells - see PAPER_MARKER_CHECK. A paper naming a gene is a hypothesis.

Honest limit on the subtype block: in held-out per-cell classification (3 seeds), the
46-gene discovery block of the 301-gene file moved supertype balanced accuracy only
0.842 -> 0.845 and subclass 0.937 -> 0.939. Combinatorial calling was already at its
plateau. What these genes buy is a dedicated single marker per sub-population - what you
need to annotate a de-novo cluster or read a slide - not a large accuracy jump.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
IN = V3 / "inputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SRC = O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx"
VARIANT = os.environ.get("PANEL_VARIANT", "lean")   # "lean" | "superset" | "minnn"
DST = {"lean": O / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx",
       "superset": O / "PANEL_FINAL_v11_ORBm_BMAp_SUPERSET.xlsx",
       "minnn": O / "PANEL_FINAL_291_ORBm_BMAp_minNN.xlsx",
       "all20": O / "PANEL_FINAL_297_ORBm_BMAp_all20.xlsx"}[VARIANT]

# Measured per cell in the 20 target populations (v3/outputs/_MEAS_add20.csv): the best
# positive marker that exists anywhere in the 32,285-gene atlas for the cell types the
# panel could only call combinatorially. With these six, all 20 target types have their
# own marker. Two of them sit below the usual 20pp bar - 005 L5 IT at 17.1pp and
# 073 MEA-BST Sox6 at 14.8pp - because no gene in the transcriptome does better for
# those two types; these ARE the ceiling.
TYPE_MARKERS = [
    ("Tnnc1", "006 L4/5 IT CTX Glut", 53.5, 22.4),
    ("Adam19", "005 L5 IT CTX Glut", 57.7, 17.1),
    ("Man2a1", "005 L5 IT CTX Glut", 76.9, 16.3),
    ("Chn2", "073 MEA-BST Sox6 Gaba", 88.8, 14.8),
    ("Frem3", "074 MEA-BST Lhx6 Sp9 Gaba", 54.5, 42.4),
    ("Blnk", "004 L6 IT CTX Glut", 54.5, 36.9),
]

# Measured (v3/E_Planning/test_nonneuronal_need.py, test_nn_perclass.py): deleting the
# dedicated non-neuronal probes does NOT let glial or vascular cells be called neurons -
# 0.0 pct either way, and 0.01 pct contamination of the 20 target populations - because
# every neuronal gene on the panel reads ~zero in those cells and the classifier uses that
# absence. Per-class recall cost of dropping all eight: Astro -0.1, Oligo -0.1, OPC +0.1,
# Microglia 0.0, Endo -0.5, VLMC +0.8, BAM -0.8, Peri -2.8, SMC -3.4 pp. So the minimum
# defensible set is a positive marker for the two big classes that sit next to the target
# neurons and are not already named by Mbp: astrocytes (24,323 cells) and microglia (8,523).
MIN_NN_KEEP = ["Aqp4", "Siglech"]
MIN_NN_DROP = ["Pdgfra", "Gjc3", "Cldn5", "Vtn", "Acta2", "Dcn"]

# Trim back to only what is necessary. Each of these is a real, measured gene - it is
# dropped because a gene already on the list carries the same information, or because
# its evidence tier is the weakest one available. OPTIONAL_ADD_ONS keeps them, with
# numbers, so any of them can go back in with one edit.
TRIM = {
    "second marker for a population that already has one": [
        "Ntsr2", "Sox10", "Col1a1", "Csf1r", "Blnk", "Abi3bp"],
    "weakest morphine tier: DE in only 3 of the 12 ORBm cell types": [],  # filled at runtime
}

# The eight endogenous mouse genes the SOW literally names, verified by four independent
# readers of the SOW text with two adversarial verifier passes each (0 rejections).
# Slc17a7 was previously counted here as a ninth; it is an inference from "IT/CT principal
# neurons", not a literal mention, so it is no longer claimed as SOW-named. It stays on the
# panel on its own merits as the VGLUT1 backbone.
SOW = {"Fos", "Arc", "Per2", "Satb2", "Oprm1", "Creb1", "Adrb1", "Htr2a"}

CAT = {
    "1_celltype_separator": "1 cell type", "3_class_backbone": "1 cell type",
    "4b_class_backbone": "1 cell type", "11_class_backbone_optional": "1 cell type",
    "9_published_regional": "1 cell type", "12_GSE283418_added": "1 cell type",
    "19_expanded_L5IT_separator": "1 cell type", "18_expanded_BMAp": "1 cell type",
    "23_identity": "1 cell type", "27_cholinergic": "1 cell type",
    "29_anchor_marker": "1 cell type", "30_nonneuronal_class": "1 cell type",
    "32_paper_marker_verified": "1 cell type",
    "28_subtype_discovery": "2 subtype marker",
    "6_GPCR_druggable": "3 GPCR", "4_GPCR_cell_type_specific": "3 GPCR",
    "17_expanded_ORB_GPCR": "3 GPCR", "24_GPCR_map": "3 GPCR",
    "14_Jesse_ORB_GPCR": "3 GPCR", "5_receptor_map": "3 GPCR",
    "7_plasticity": "4 plasticity", "25_plasticity": "4 plasticity",
    "8_TF_identity": "5 TF", "2_reporter_transgene": "6 TRAP reporter",
    "5_IEG": "7 IEG", "4c_activity": "7 IEG",
    "16_expanded_morphine_state": "8 morphine", "13_Jesse_morphine_state": "8 morphine",
    "31_Jesse_morphine_extended": "8 morphine",
    "33_circadian": "9 circadian",
}
ORBM_ANCHORS = ["007 L2/3 IT CTX Glut", "006 L4/5 IT CTX Glut", "005 L5 IT CTX Glut",
                "022 L5 ET CTX Glut", "032 L5 NP CTX Glut", "030 L6 CT CTX Glut",
                "029 L6b CTX Glut", "004 L6 IT CTX Glut", "052 Pvalb Gaba",
                "053 Sst Gaba", "046 Vip Gaba", "049 Lamp5 Gaba"]

NONNEURONAL = [
    ("Aqp4", "astrocyte", "canonical astrocyte water channel"),
    ("Ntsr2", "astrocyte", "astrocyte-specific, the largest measured gap of any astrocyte gene here"),
    ("Pdgfra", "OPC", "canonical OPC"),
    ("Gjc3", "oligodendrocyte", "oligodendrocyte connexin - Mbp alone does not separate oligodendrocytes from myelin-rich neuropil"),
    ("Sox10", "oligo lineage", "pan oligodendrocyte-lineage TF, confirms the OPC and oligodendrocyte calls"),
    ("Cldn5", "endothelium", "canonical blood-brain-barrier claudin"),
    ("Vtn", "pericyte", "pericyte - re-added because this is a standalone panel, so it is no longer free on a base panel"),
    ("Acta2", "smooth muscle", "arteriolar smooth muscle"),
    ("Dcn", "VLMC / fibroblast", "VLMC decorin; also a published posterior-BMA marker (Hochgerner 2023)"),
    ("Col1a1", "VLMC / fibroblast", "collagen I, confirms Dcn"),
    ("Siglech", "microglia", "microglia-specific; v8 cut P2ry12 only because this was free on the base panel"),
    ("Csf1r", "microglia / BAM", "microglia plus border-associated macrophages"),
]
ANCHOR_FIX = [("Blnk", "004 L6 IT CTX Glut"), ("Bmp3", "004 L6 IT CTX Glut"),
              ("Vwc2l", "032 L5 NP CTX Glut"), ("Abi3bp", "032 L5 NP CTX Glut")]

GPCR_RE = re.compile(
    r"^(Gpr|Gprc|Adgr|Htr[1-7]|Adra|Adrb|Chrm|Drd\d|Opr[mdkl]|Grm\d|Gabbr|Sstr|Npy\dr|"
    r"Tacr|Cnr\d|Mc\dr|Crhr|Galr|Hcrtr|Mchr|Ntsr|Trhr|P2ry|Lpar|S1pr|Ptger|Adora|Calcr|Vipr|"
    r"Avpr|Oxtr|Rxfp|Cckar|Cckbr|Hrh\d|Glp1r|Gipr|Pth\dr|Mrgpr|Taar|Bdkrb|Kiss1r|Qrfpr|Npffr|"
    r"Nmur|Gnrhr|Cysltr|Ackr|Ccr\d|Cxcr\d|C3ar1|C5ar1|Adcyap1r1|Gpbar1|Ffar)")


def region_of(anchor: str) -> str:
    return "ORBm" if anchor in ORBM_ANCHORS else "BMAp"


def main() -> None:
    lvl = pd.read_csv(O / "_MEAS_level_summary.csv").set_index("gene")
    det_an = pd.read_csv(O / "_MEAS_by_anchor.csv", index_col=0)
    gw_sup = pd.read_excel(DL / "allen_genomewide_marker_search.xlsx", "supertype_markers")
    gw_an = pd.read_excel(DL / "allen_genomewide_marker_search.xlsx", "anchor_markers")
    rank = pd.read_excel(O / "Jesse_ORB_priority_ranking.xlsx", "ranking_all").set_index("gene")
    d301 = pd.read_csv(O / "_301only_detect.csv").set_index("gene")
    dn3 = pd.read_csv(O / "_jesse_n3_detect.csv").set_index("gene")
    nnm = pd.read_csv(O / "_nonneuronal_markers.csv")

    sh = pd.read_excel(SRC, "SHARED_PANEL_ORDER")
    orb = pd.read_excel(SRC, "ORBm_ORDER")
    bma = pd.read_excel(SRC, "BMAp_ORDER")
    on = set(sh.gene.astype(str))
    ac = pd.read_excel(SRC, "ANCHOR_COVERAGE")
    anchors = list(ac.allen_subclass_anchor)

    add = []

    # 1. morphine axis
    det = pd.concat([d301.anchor_max_pct.rename("pct"), dn3.anchor_max_pct.rename("pct")])
    best = pd.concat([d301.best_anchor.rename("a"), dn3.best_anchor.rename("a")])
    jes = rank[(rank.n_orbm >= 3) & (~rank.index.isin(on))].copy()
    jes["pct"] = det.reindex(jes.index)
    jes["best"] = best.reindex(jes.index)
    for g, r in jes[jes.pct >= 50].sort_values(["n_orbm", "pct"], ascending=False).iterrows():
        add.append({"gene": g,
                    "block": "16_expanded_morphine_state" if r.n_orbm >= 4 else "31_Jesse_morphine_extended",
                    "serves": f"Jesse morphine DEG ({r.lists}, {r.direction}) :: {r.pct:.0f} pct detected",
                    "why": f"DE after 5-day morphine in {int(r.n_orbm)} of the 12 ORBm anchor subclasses "
                           f"(Jesse opioid-dependence DEG set). Measured in {r.pct:.1f} pct of cells at "
                           f"{r.best} - clears the same 50 pct detection bar as the rest of the panel.",
                    "region": "ORBm", "evidence": "Jesse ORB DEG + Allen per-cell"})

    # 2. subtype discovery - minimum cover of the 96 supertypes
    gs = gw_sup[(gw_sup.parent_subclass.isin(anchors)) & (gw_sup.pct_in >= 50) & (gw_sup.gap >= 20)]
    n_total = gs.group.nunique()
    n_before = gs.group[gs.gene.isin(on)].nunique()
    remaining = set(gs.group) - set(gs.group[gs.gene.isin(on)])
    while remaining:
        c = (gs[gs.group.isin(remaining)].groupby("gene")
             .agg(k=("group", "nunique"), mg=("gap", "max"))
             .sort_values(["k", "mg"], ascending=False))
        g = c.index[0]
        got = set(gs.group[(gs.gene == g) & (gs.group.isin(remaining))])
        r0 = gs[(gs.gene == g) & (gs.group.isin(got))].sort_values("gap", ascending=False).iloc[0]
        add.append({"gene": g, "block": "28_subtype_discovery",
                    "serves": f"dedicated marker for {len(got)} supertype(s) of {r0.parent_subclass}",
                    "why": f"{r0.pct_in:.1f} pct of cells in {r0.group} vs {r0.pct_out_max:.1f} pct in the "
                           f"next-highest sibling supertype (gap {r0.gap:.1f} pp), from the genome-wide "
                           f"search over all 32,285 Allen genes. Without it that sub-population has no "
                           f"dedicated marker on the panel, so a de-novo cluster matching it could not be "
                           f"named from a single gene.",
                    "region": region_of(r0.parent_subclass), "evidence": "Allen genome-wide (subtype)"})
        remaining -= got

    # 3. the two anchors with no dedicated single marker
    for g, a in ANCHOR_FIX:
        r = gw_an[(gw_an.group == a) & (gw_an.gene == g)].iloc[0]
        add.append({"gene": g, "block": "29_anchor_marker",
                    "serves": f"dedicated marker for {a}",
                    "why": f"{r.pct_in:.1f} pct in {a} vs {r.pct_out_max:.1f} pct in the next-highest "
                           f"population (gap {r.gap:.1f} pp). {a} was one of only two anchors with no "
                           f"dedicated single marker on v8 - it was identified combinatorially.",
                    "region": region_of(a), "evidence": "Allen genome-wide (anchor)"})

    # 4. non-neuronal classes
    for g, cls, note in NONNEURONAL:
        r = nnm[nnm.gene == g].sort_values("gap_pp", ascending=False).iloc[0]
        add.append({"gene": g, "block": "30_nonneuronal_class",
                    "serves": f"{cls} exclusion marker :: {r.pct_in_class:.0f} pct detected",
                    "why": f"{r.pct_in_class:.1f} pct of cells in {r.subclass} ({int(r.n_cells):,} cells) "
                           f"vs {r.pct_95th_other_subclass:.1f} pct in the 95th-percentile other subclass "
                           f"(gap {r.gap_pp:.1f} pp). {note}. Xenium segments every cell, so a population "
                           f"with no marker of its own contaminates the neuronal clusters.",
                    "region": "both", "evidence": "Allen per-cell (own population)"})

    # 4b. paper-suggested markers that had never been measured, and pass on measurement
    pm_path = O / "_MEAS_paper_markers.csv"
    pm = pd.read_csv(pm_path) if pm_path.exists() else pd.DataFrame()
    for r in (pm[pm.include] if len(pm) else pd.DataFrame()).itertuples():
        add.append({"gene": r.gene, "block": "32_paper_marker_verified",
                    "serves": f"published marker of {r.best_assigned_population} :: "
                              f"{r.pct_in_assigned:.0f} pct detected",
                    "why": f"Published marker for this cell type that no earlier version had ever scored. "
                           f"Measured: {r.pct_in_assigned:.1f} pct of cells in {r.best_assigned_population} "
                           f"(mean log2 {r.mean_log2_in_assigned:.2f}) vs {r.pct_in_highest_other_population:.1f} pct "
                           f"in the highest competing population (gap {r.gap_pp:.1f} pp), so the paper's claim "
                           f"holds in the Allen cells.",
                    "region": region_of(r.best_assigned_population),
                    "evidence": "published marker + Allen per-cell"})

    # 4c. the SOW clock axis. The SOW names "clock genes like PER2" as one of the three
    # transcriptional-reprogramming readouts of the IT/CT population, alongside the IEGs
    # and the pCREB targets. Per1/Per2/Bhlhe40 were already on the list as Jesse morphine
    # DEGs, but two Per genes cannot call a circadian phase - the core loop needs both
    # limbs. Every gene below was measured in these cells first.
    SOW_CLOCK = [
        ("Clock", "positive limb - CLOCK itself"),
        ("Arntl", "positive limb - BMAL1, the CLOCK partner"),
        ("Npas2", "positive limb - forebrain CLOCK paralog, the one that actually dominates in cortex"),
        ("Cry1", "negative limb - CRY1, the Per partner"),
        ("Cry2", "negative limb - CRY2"),
        ("Per3", "negative limb - completes the Per family with Per1/Per2"),
        ("Nr1d1", "output limb - REV-ERBa"),
        ("Nr1d2", "output limb - REV-ERBb"),
        ("Dbp", "output limb - the classical high-amplitude clock output gene"),
        ("Bhlhe41", "DEC2 - pairs with Bhlhe40, which is already on the list as a Jesse morphine DEG"),
    ]
    for g, role in SOW_CLOCK:
        m = lvl.loc[g]
        add.append({"gene": g, "block": "33_circadian",
                    "serves": f"circadian clock gene :: {role} :: {m.own_pct:.0f} pct detected",
                    "why": f"The SOW names the clock axis as an IT/CT reprogramming readout "
                           f"(\"immediate-early like Fos and Arc, clock genes like PER2, and pCREB-target "
                           f"genes\", p.1). {role}. Measured {m.own_pct:.1f} pct of cells in "
                           f"{m.own_best_subclass} (mean log2 {m.own_mean_log2:.2f}), >=50 pct in "
                           f"{int(m.n_subclasses_ge50)} of 75 populations. Per1 + Per2 alone cannot "
                           f"separate a phase shift from a single-gene change.",
                    "region": "ORBm", "evidence": "SOW-named axis + Allen per-cell"})

    # 4d. one positive marker for every one of the 20 target cell types
    if VARIANT in ("all20",):
        for g, a, pct, gap in TYPE_MARKERS:
            add.append({"gene": g, "block": "29_anchor_marker",
                        "serves": f"names {a} :: {pct:.0f} pct detected",
                        "why": f"{pct:.1f} pct of cells in {a} vs {pct - gap:.1f} pct in the "
                               f"next-highest target population (gap {gap:.1f} pp), measured per cell "
                               f"in the 226,886 Allen cells of these two regions. "
                               + ("This is the best marker that exists for this cell type anywhere in "
                                  "the 32,285-gene atlas - the 20pp bar is unreachable for it."
                                  if gap < 20 else
                                  "Clears the >=50 pct / >=20pp bar against the other 19 target types."),
                        "region": region_of(a), "evidence": "Allen per-cell (target-type comparison)"})

    # 5. Rbms3
    m = lvl.loc["Rbms3"]
    add.append({"gene": "Rbms3", "block": "18_expanded_BMAp",
                "serves": f"120 MEA Otp Foxp2 Glut marker :: {m.anchor_pct:.0f} pct detected",
                "why": f"{m.anchor_pct:.1f} pct of cells in {m.best_anchor} (the BMAp VGLUT2 anchor), mean "
                       f"log2 {m.anchor_mean_log2:.2f}. Present on the 301-gene file but never scored; "
                       f"measured here.",
                "region": "BMAp", "evidence": "Allen per-cell"})

    addf = pd.DataFrame(add).drop_duplicates("gene")
    addf = addf[~addf.gene.isin(on)].reset_index(drop=True)
    print(f"v8 {len(sh)} + {len(addf)} = {len(sh) + len(addf)}")
    print(addf.groupby("block").size().to_string())

    # ---------- assemble the final list ----------
    add20_path = O / "_MEAS_add20.csv"
    add20 = (pd.read_csv(add20_path).drop_duplicates("gene").set_index("gene")
             if add20_path.exists() else pd.DataFrame())

    def mrow(g: str) -> dict:
        if len(add20) and g in add20.index and g not in lvl.index:
            r = add20.loc[g]
            return {"allen_pct_own_population": r.pct_in, "allen_own_population": r.best_target_type,
                    "allen_mean_log2_own_population": r.mean_log2_there,
                    "allen_pct_best_anchor": r.pct_in, "allen_best_anchor": r.best_target_type,
                    "allen_mean_log2_best_anchor": r.mean_log2_there,
                    "n_subclasses_ge50pct": np.nan,
                    "level_verdict": ("strong in its own population" if r.pct_in >= 70
                                      else "usable in its own population"),
                    "measured": "per-cell, in the target cell type it names"}
        if g in lvl.index:
            m = lvl.loc[g]
            return {"allen_pct_own_population": m.own_pct, "allen_own_population": m.own_best_subclass,
                    "allen_mean_log2_own_population": m.own_mean_log2,
                    "allen_pct_best_anchor": m.anchor_pct, "allen_best_anchor": m.best_anchor,
                    "allen_mean_log2_best_anchor": m.anchor_mean_log2,
                    "n_subclasses_ge50pct": m.n_subclasses_ge50,
                    "level_verdict": m.level_verdict, "measured": "per-cell, 226,886 cells"}
        a = gw_an[gw_an.gene == g].sort_values("gap", ascending=False)
        s = gw_sup[gw_sup.gene == g].sort_values("gap", ascending=False)
        src = a if len(a) else s
        if len(src):
            r = src.iloc[0]
            grp = r.group if len(a) else f"{r.group} (in {r.parent_subclass})"
            return {"allen_pct_own_population": round(float(r.pct_in), 1), "allen_own_population": grp,
                    "allen_mean_log2_own_population": np.nan,
                    "allen_pct_best_anchor": round(float(r.pct_in), 1),
                    "allen_best_anchor": r.group if len(a) else r.parent_subclass,
                    "allen_mean_log2_best_anchor": np.nan, "n_subclasses_ge50pct": np.nan,
                    "level_verdict": "detection measured genome-wide; level not computed",
                    "measured": "genome-wide aggregate"}
        return {"allen_pct_own_population": np.nan, "allen_own_population": np.nan,
                "allen_mean_log2_own_population": np.nan, "allen_pct_best_anchor": np.nan,
                "allen_best_anchor": np.nan, "allen_mean_log2_best_anchor": np.nan,
                "n_subclasses_ge50pct": np.nan, "level_verdict": "transgene - absent from the atlas",
                "measured": "transgene"}

    keep = ["gene", "block", "serves", "why"]
    final = pd.concat([sh[keep], addf[keep]], ignore_index=True)
    final["category"] = final.block.map(CAT)
    if final.category.isna().any():
        raise SystemExit(f"unmapped blocks: {sorted(set(final.block[final.category.isna()]))}")
    final = pd.concat([final, final.gene.apply(lambda g: pd.Series(mrow(g)))], axis=1)

    # a subtype marker is judged inside its own sub-population, not in the parent cell
    # type: Hpse is 88 pct of the 229 cells of 0220 Sst Gaba_7 but 11 pct of the 5,267-cell
    # Sst subclass they sit in. Same correction for the two anchor markers.
    stl_path = O / "_MEAS_subtype_level.csv"
    stl = pd.read_csv(stl_path).set_index("gene") if stl_path.exists() else pd.DataFrame()
    for g in stl.index:
        if g not in set(final.gene):
            continue
        r = stl.loc[g]
        i = final.index[final.gene == g][0]
        final.loc[i, "allen_pct_own_population"] = r.pct_in_target
        final.loc[i, "allen_own_population"] = r.target_population
        final.loc[i, "allen_mean_log2_own_population"] = r.mean_log2_in_target
        final.loc[i, "measured"] = "per-cell, in its own target population"
        final.loc[i, "level_verdict"] = (
            "strong in its own population" if r.pct_in_target >= 70 and r.mean_log2_in_target >= 2
            else "usable in its own population" if r.pct_in_target >= 50 and r.mean_log2_in_target >= 1
            else "detected in most cells but low level" if r.pct_in_target >= 50
            else "too low to map reliably")
    final["sow_named"] = final.gene.isin(SOW)
    final["keep_reason_if_low"] = np.where(
        final.sow_named, "SOW names this gene - the question is whether it is expressed, so a low or "
                         "negative result is itself the answer", "")
    TRIM["weakest morphine tier: DE in only 3 of the 12 ORBm cell types"] = sorted(
        final.gene[final.block == "31_Jesse_morphine_extended"])
    trim_reason = ({} if VARIANT == "superset"
                   else {g: why for why, gs in TRIM.items() for g in gs})
    if VARIANT == "all20":
        trim_reason.pop("Blnk", None)
    if VARIANT in ("minnn", "all20"):
        trim_reason.update({g: "minimum non-neuronal set - measured cost of dropping it is <=3.4pp "
                               "class recall, and non-neuronal cells are still never called neurons "
                               "(0.0 pct either way)" for g in MIN_NN_DROP})
    would_trim = {g: why for why, gs in TRIM.items() for g in gs}
    if VARIANT in ("minnn", "all20"):
        would_trim.update({g: "dropped in the 291-gene minimum-non-neuronal version" for g in MIN_NN_DROP})
    superset_n = len(final)
    optional = final[final.gene.isin(would_trim)].copy()
    optional["why_not_on_the_final_list"] = optional.gene.map(would_trim)
    if VARIANT == "superset":
        optional["why_not_on_the_final_list"] = (
            "INCLUDED in this superset; the lean 296-gene version drops it - "
            + optional.gene.map(would_trim))
    final = final[~final.gene.isin(trim_reason)].copy()
    final = final.sort_values(["category", "block", "gene"]).reset_index(drop=True)
    final.insert(0, "order_rank", np.arange(1, len(final) + 1))
    print(f"trimmed {superset_n} -> {len(final)} "
          f"({len(optional)} moved to OPTIONAL_ADD_ONS)")

    reg = dict(zip(addf.gene, addf.region))
    orbf = pd.concat([orb[keep], addf[addf.gene.map(reg).isin(["ORBm", "both"])][keep]], ignore_index=True)
    bmaf = pd.concat([bma[keep], addf[addf.gene.map(reg).isin(["BMAp", "both"])][keep]], ignore_index=True)
    orbf = orbf[orbf.gene.isin(set(final.gene))].reset_index(drop=True)
    bmaf = bmaf[bmaf.gene.isin(set(final.gene))].reset_index(drop=True)
    for d in (orbf, bmaf):
        d.insert(0, "order_rank", np.arange(1, len(d) + 1))

    # ---------- GPCR x cell type ----------
    gp = [g for g in final.gene if (final.set_index("gene").category.get(g) == "3 GPCR"
                                    or GPCR_RE.match(g)) and g in det_an.columns]
    gp = list(dict.fromkeys(gp))
    lvl_an = pd.read_csv(O / "_MEAS_mean_by_anchor.csv", index_col=0)
    rows = []
    for g in gp:
        v = det_an[g].sort_values(ascending=False)
        rows.append({"gpcr": g,
                     "top1_celltype": v.index[0], "top1_pct": round(float(v.iloc[0]), 1),
                     "top1_mean_log2": round(float(lvl_an.loc[v.index[0], g]), 2),
                     "top2_celltype": v.index[1], "top2_pct": round(float(v.iloc[1]), 1),
                     "top3_celltype": v.index[2], "top3_pct": round(float(v.iloc[2]), 1),
                     "gap_top1_vs_median_pp": round(float(v.iloc[0] - v.median()), 1),
                     "n_anchors_ge50pct": int((v >= 50).sum()),
                     "read_as": "enriched in the top cell type" if v.iloc[0] - v.median() >= 20
                     else "broad - read as a level inside a named type"})
    gpcr_ct = pd.DataFrame(rows).sort_values("gap_top1_vs_median_pp", ascending=False)
    per_anchor = []
    for a in det_an.index:
        v = det_an.loc[a, gp].sort_values(ascending=False)
        enr = [f"{g} {v[g]:.0f}%" for g in v.index if v[g] >= 50 and v[g] - det_an[g].median() >= 20]
        per_anchor.append({"cell_type": a, "region": region_of(a),
                           "n_GPCRs_detected_ge50pct": int((v >= 50).sum()),
                           "GPCRs_enriched_in_this_type": "; ".join(enr[:12]) or "(none >=20pp above its own cross-type median)",
                           "top_GPCRs_by_detection": "; ".join(f"{g} {v[g]:.0f}%" for g in v.index[:12])})
    gpcr_anchor = pd.DataFrame(per_anchor)

    drugs_sum = pd.read_csv(IN / "gpcr_drug_targets.csv")
    drugs_sum = drugs_sum[drugs_sum.gene_symbol.isin(final.gene)]
    drugs = pd.read_csv(IN / "gpcr_drug_targets_detailed.csv")
    drugs = drugs[drugs.gene_symbol.isin(final.gene)]

    # ---------- paper suggested vs Allen computed ----------
    cm = pd.read_csv(IN / "curated_marker_template.csv")
    cm = cm[cm.region_user.isin(["ORBm", "BMAp"])]
    a2 = pd.read_csv(IN / "celltype_to_subclass_anchor.csv")
    a2 = a2[a2.region_user.isin(["ORBm", "BMAp"])]
    pv = []

    def verdict(pct: float) -> str:
        if pd.isna(pct):
            return "not measured locally"
        if pct >= 50:
            return "confirmed - detected in >=50 pct of that cell type"
        if pct >= 10:
            return "detected but sparse (<50 pct)"
        return "not detected in that cell type"

    for r in cm.itertuples():
        anc = [a for a in a2.allen_subclass_anchor[(a2.region_user == r.region_user)
                                                   & (a2.cell_type_label == r.cell_type_label)]
               if a in det_an.index]
        for g in [x.strip() for x in str(r.marker_genes).split(",") if x.strip()]:
            pct = round(float(det_an.loc[anc, g].max()), 1) if (anc and g in det_an.columns) else np.nan
            pv.append({"region": r.region_user, "cell_type_label": r.cell_type_label,
                       "paper_suggested": g, "paper_source": r.source,
                       "allen_population_used": "; ".join(anc),
                       "allen_computed_pct": pct, "verdict": verdict(pct),
                       "on_v9": g in set(final.gene)})
    pg = pd.read_csv(IN / "paper_gpcr_suggestions.csv")
    pg = pg[pg.region_user.isin(["ORBm", "BMAp"])]
    for r in pg.itertuples():
        anc = [a for a in a2.allen_subclass_anchor[a2.region_user == r.region_user] if a in det_an.index]
        pct = round(float(det_an.loc[anc, r.gene].max()), 1) if (anc and r.gene in det_an.columns) else np.nan
        pv.append({"region": r.region_user, "cell_type_label": r.cell_type_label,
                   "paper_suggested": r.gene, "paper_source": r.paper_source,
                   "allen_population_used": f"best of the {len(anc)} {r.region_user} populations",
                   "allen_computed_pct": pct, "verdict": verdict(pct),
                   "on_v9": r.gene in set(final.gene)})
    paper_vs_allen = pd.DataFrame(pv)
    if len(pm):
        pmi = pm.set_index("gene")
        for i in paper_vs_allen.index:
            g = paper_vs_allen.at[i, "paper_suggested"]
            if g in pmi.index and pd.isna(paper_vs_allen.at[i, "allen_computed_pct"]):
                paper_vs_allen.at[i, "allen_computed_pct"] = pmi.at[g, "pct_in_assigned"]
                paper_vs_allen.at[i, "allen_population_used"] = pmi.at[g, "best_assigned_population"]
                paper_vs_allen.at[i, "verdict"] = verdict(float(pmi.at[g, "pct_in_assigned"]))
                paper_vs_allen.at[i, "on_v9"] = bool(pmi.at[g, "include"])

    # ---------- subtype coverage before / after ----------
    fin = set(final.gene)
    sup_cov = []
    for grp, d in gs.groupby("group"):
        v8g = d[d.gene.isin(on)].sort_values("gap", ascending=False)
        v9g = d[d.gene.isin(fin)].sort_values("gap", ascending=False)
        sup_cov.append({"parent_cell_type": d.parent_subclass.iloc[0], "sub_population": grp,
                        "n_cells": int(d.n_cells.iloc[0]),
                        "marker_on_v8": v8g.gene.iloc[0] if len(v8g) else "(none)",
                        "marker_on_v9": v9g.gene.iloc[0] if len(v9g) else "(none)",
                        "v9_pct_in_sub_population": round(float(v9g.pct_in.iloc[0]), 1) if len(v9g) else np.nan,
                        "v9_gap_vs_sibling_pp": round(float(v9g.gap.iloc[0]), 1) if len(v9g) else np.nan})
    sup_cov = pd.DataFrame(sup_cov).sort_values(["parent_cell_type", "sub_population"])

    # ---------- excluded, with the measured reason ----------
    exc = []
    for src, label in ((d301, None), (dn3, "Jesse morphine DEG (DE in 3 of 12 ORBm types)")):
        for g, r in src.iterrows():
            if g in fin:
                continue
            lv = lvl.loc[g] if g in lvl.index else None
            exc.append({"gene": g, "considered_for": label or r.block,
                        "allen_pct_best_anchor": r.anchor_max_pct, "best_anchor": r.best_anchor,
                        "allen_pct_own_population": None if lv is None else lv.own_pct,
                        "allen_mean_log2_own_population": None if lv is None else lv.own_mean_log2,
                        "why_excluded": "below the 50 pct detection bar - the probe would return a mostly "
                                        "empty map in ORBm/BMAp"})
    # the discovery-block genes of the 301-gene file that v9 did NOT need
    d301_disc = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx", "SHARED_PANEL_ORDER")
    for g in sorted(set(d301_disc.gene[d301_disc.block == "20_Allen_supertype_discovery"].astype(str))):
        if g in fin:
            continue
        r = gw_sup[(gw_sup.gene == g) & (gw_sup.parent_subclass.isin(anchors))].sort_values(
            "gap", ascending=False)
        lv = lvl.loc[g] if g in lvl.index else None
        tgt = f"{r.iloc[0].group} (in {r.iloc[0].parent_subclass})" if len(r) else "no ORBm/BMAp sub-population"
        exc.append({"gene": g, "considered_for": f"subtype marker for {tgt}",
                    "allen_pct_best_anchor": None if lv is None else lv.anchor_pct,
                    "best_anchor": None if lv is None else lv.best_anchor,
                    "allen_pct_own_population": round(float(r.iloc[0].pct_in), 1) if len(r) else None,
                    "allen_mean_log2_own_population": None if lv is None else lv.own_mean_log2,
                    "why_excluded": "real marker, but the sub-population it marks already has a dedicated "
                                    "marker on the list - see SUPERTYPE_COVERAGE. Adding it is harmless and "
                                    "buys a second marker for that sub-population; in held-out "
                                    "classification the whole 46-gene block moved supertype accuracy only "
                                    "0.842 -> 0.845."})
    EXC_OTHER = [("Bhlhe41", "circadian - redundant with Bhlhe40, which is already on the list"),
                 ("Xist", "sex identity"), ("Eif2s3y", "sex identity"), ("Ddx3y", "sex identity"),
                 ("Uty", "sex identity"), ("Ddc", "monoamine synthesis")]
    for g, why in EXC_OTHER:
        if g in fin:
            continue
        lv = lvl.loc[g] if g in lvl.index else None
        exc.append({"gene": g, "considered_for": why,
                    "allen_pct_best_anchor": None if lv is None else lv.anchor_pct,
                    "best_anchor": None if lv is None else lv.best_anchor,
                    "allen_pct_own_population": None if lv is None else lv.own_pct,
                    "allen_mean_log2_own_population": None if lv is None else lv.own_mean_log2,
                    "why_excluded": ("explicitly excluded on your instruction - no sex-determination genes. "
                                     "The SOW's SABV commitment is then met by animal metadata, not by a "
                                     "section-level check."
                                     if why == "sex identity" else
                                     f"detectable, but {why}. The nine core clock genes the SOW's clock axis "
                                     f"needs ARE on the list (block 33_circadian).")})
    excluded = pd.DataFrame(exc).sort_values("allen_pct_best_anchor", ascending=False)

    sow2_path = O / "_MEAS_sow2.csv"
    if sow2_path.exists():
        for r in pd.read_csv(sow2_path).itertuples():
            if r.gene in fin:
                continue
            why = {"Ciart": "core clock gene (Chrono), so a candidate for the SOW clock axis, but only "
                            "16.8 pct of cells in its best population - the other 10 clock genes carry the axis",
                   "Rspo1": "proposed as an IT/CT identity marker, but its 92.8 pct population is "
                            "077 CEA-BST Gal Avp Gaba - an amygdalar GABA type, not a cortical IT/CT cell, "
                            "so the mapping does not hold in these two regions",
                   "Ntsr1": "classic L6 CT marker in the literature, but measured 29.9 pct in 030 L6 CT CTX "
                            "Glut here; its 71.5 pct population is 059 GPe-SI Sox6 Cyp26b1 Gaba. Tle4, Foxp2 "
                            "and Syt6 carry L6 CT instead"}.get(r.gene, "measured and failed the 50 pct bar")
            exc.append({"gene": r.gene, "considered_for": "SOW class mention (clock axis / IT-CT identity)",
                        "allen_pct_best_anchor": None, "best_anchor": None,
                        "allen_pct_own_population": r.own_pct,
                        "allen_mean_log2_own_population": r.own_mean_log2,
                        "why_excluded": why})
        excluded = pd.DataFrame(exc).sort_values("allen_pct_best_anchor", ascending=False)

    sow_audit_path = O / "_SOW_GENE_AUDIT.csv"
    sow_audit = pd.read_csv(sow_audit_path) if sow_audit_path.exists() else pd.DataFrame()
    if len(sow_audit):
        sow_audit["mouse_symbols_on_this_list"] = [
            "; ".join(g for g in str(r).split(", ") if g in fin) or "-"
            for r in sow_audit.mouse_gene_symbols.fillna("")]
    stress_path = O / "_STRESS_xenium_sparsity.csv"
    stress = pd.read_csv(stress_path) if stress_path.exists() else pd.DataFrame()

    ab_path = O / "_MEAS_abundance.csv"
    crowd = pd.DataFrame()
    if ab_path.exists():
        ab = (pd.read_csv(ab_path).drop_duplicates("gene")
              .set_index("gene").mean_linear_abundance)
        on_list = ab.reindex(final.gene).dropna()
        tot = float(on_list.sum())
        crowd = (pd.DataFrame({"gene": on_list.index,
                               "mean_linear_abundance": on_list.values.round(1),
                               "pct_of_panel_transcripts": (on_list.values / tot * 100).round(2)})
                 .sort_values("pct_of_panel_transcripts", ascending=False).reset_index(drop=True))
        crowd["cumulative_pct"] = crowd.pct_of_panel_transcripts.cumsum().round(1)
        crowd = crowd.merge(final[["gene", "category", "block", "n_subclasses_ge50pct"]], on="gene", how="left")
        crowd["note"] = np.where(
            crowd.pct_of_panel_transcripts >= 2.0,
            "high load - carries >=2 pct of the panel's transcripts on its own; on Xenium that is "
            "decoding capacity and optical crowding, and a gene detected in nearly every cell also "
            "carries little cell-typing information. Drop only if its axis is covered by a partner gene.",
            "")

    bench = pd.read_excel(O / "BENCH_discovery_vs_v8.xlsx", "summary")
    sources = pd.read_excel(SRC, "SOURCES")
    cmp_path = O / "_PANEL_COMPARISON.csv"
    comparison = pd.read_csv(cmp_path) if cmp_path.exists() else pd.DataFrame()

    # the three cell types that no single gene can mark - a ceiling, not a panel fault
    ceiling = gw_an[(gw_an.pct_in >= 50) & (gw_an.gap >= 20)].group.unique()
    ceil_rows = []
    for r in ac.itertuples():
        if r.allen_subclass_anchor in ceiling:
            continue
        ceil_rows.append({"region": r.region, "cell_type_label": r.cell_type_label,
                          "allen_population": r.allen_subclass_anchor, "n_cells": r.n_cells,
                          "separators_on_v9": r.unique_separators_on_shared_panel,
                          "note": "no gene in the whole 32,285-gene atlas reaches 50 pct here with a "
                                  "20pp margin over the other populations, so this type is called "
                                  "COMBINATORIALLY from the separators listed. Adding probes cannot "
                                  "fix it - it is a property of the transcriptome, not of the panel."})
    anchor_ceiling = pd.DataFrame(ceil_rows)

    readme = pd.DataFrame({"item": [
        "What this file is", "Order this sheet", "Regions", "Panel size",
        "The categories", "Rule 1 - cell type and subtype markers must be distinguishable",
        "Rule 2 - GPCR / TF / plasticity / IEG / morphine may be broad, but must be detectable",
        "Rule 3 - every gene scored in its OWN population",
        "Rule 4 - SOW-named genes are never cut on level",
        "Rule 5 - standalone panel, so non-neuronal classes need markers",
        "Rule 6 - anatomy", "What the subtype block buys, measured",
        "Evidence: Allen", "Evidence: papers", "Evidence: Jesse", "Evidence: Dan / GSE283418",
        "How to read PANEL_COMPARISON", "Two different sub-population denominators (96 vs 107)",
        "What the SOW says about the circadian axis", "Transgene and product-tier caveats",
        "Xenium transcript load (CROWDING_load)", "Caveat on all percentages", "Pipeline",
    ], "detail": [
        "The final ORBm + BMAp gene list with no panel-size limit. Every gene is here because it is "
        "biologically load-bearing for one of the categories below AND measured in the Allen cells of "
        "these two regions - as a detection rate and as an expression LEVEL.",
        "FINAL_GENE_LIST. ORBm_LIST and BMAp_LIST are the same genes split by which region needs them; "
        "order the union, which is FINAL_GENE_LIST.",
        "ORBm = Allen ROI PL-ILA-ORB (106,122 cells). BMAp = Allen ROI sAMY (120,764 cells). Nothing here "
        "serves a region we do not image. BMAp is not MEA/CEA: the MEA/CEA/BST subclasses are carried as "
        "NEIGHBOUR CONTROLS and are labelled that way in ANCHOR_COVERAGE.",
        f"{len(final)} genes. No 10x add-on cap assumed - this is a standalone custom panel, so the "
        f"248-gene Mouse Brain base panel is NOT included and no gene is free.",
        "1 cell type, 2 subtype (finer clustering inside a cell type), 3 GPCR, 4 synaptic plasticity, "
        "5 transcription factor, 6 TRAP reporter, 7 IEG / activity, 8 morphine response (Jesse). Every "
        "gene carries exactly one category.",
        "The marker must reach >=50 pct of cells in the population it names AND sit >=20pp above the "
        "competing populations (or above its sibling sub-populations for a subtype marker). Columns "
        "allen_pct_own_population and the SUPERTYPE_COVERAGE sheet show this per gene.",
        "These are read as a LEVEL inside an already-named cell type, so broad expression is fine and a "
        "low cell-type-classifier weight is not evidence against them. They still have to clear the same "
        "50 pct detection bar somewhere in ORBm/BMAp - see EXCLUDED_measured for the ones that did not.",
        "A microglial gene is scored in microglia, a cholinergic gene in cholinergic neurons - not in "
        "cortical pyramidal cells. Scoring them only in the 20 neuronal anchors is what wrongly cut "
        "Cx3cr1 and Chat in earlier versions. Columns: allen_pct_own_population vs allen_pct_best_anchor.",
        "The SOW asks whether some genes are expressed at all (Adrb1, Htr2a, Oprm1, Creb1, Per2, Fos, Arc, "
        "Satb2, Slc17a7). A low level is then a result, not a reason to drop the probe. Column sow_named.",
        "28 pct of the section is non-neuronal and Xenium segments every cell, so astrocytes, OPC, "
        "oligodendrocytes, microglia, endothelium, pericytes, SMC and VLMC each get their own marker. "
        "This reverses the earlier cuts of P2ry12 / Rgs5 / Vtn, which were justified only by those genes "
        "being free on the 10x base panel - with no base panel that argument disappears.",
        "Every population named in this workbook was verified to belong to PL-ILA-ORB or sAMY in the "
        "Allen cell metadata before any number was computed.",
        "Held-out per-cell classification, 3 seeds: the 46-gene discovery block of the 301-gene file moved "
        "supertype balanced accuracy 0.842 -> 0.845 and subclass 0.937 -> 0.939, i.e. combinatorial "
        "cell-type calling was already at its plateau. What the subtype genes here DO buy is a dedicated "
        "single marker for each of the 96 sub-populations inside the 20 cell types (66/96 on v8) - which "
        "is what you need to annotate a de-novo cluster or to read a slide directly. Both numbers are in "
        "BENCHMARK and SUPERTYPE_COVERAGE; neither is hidden.",
        "Allen Brain Cell Atlas WMB-10X log2 matrices downloaded locally (abc_atlas_cache, ~96 GB). Every "
        "percentage and level in this workbook was computed from those cells - none is quoted from a paper.",
        "Paper-suggested genes are kept SEPARATE from computed numbers: PAPER_vs_ALLEN puts each suggested "
        "gene next to its Allen-computed detection in the cell type the paper assigned it to, with a verdict.",
        "Jesse's 5-day-morphine opioid-dependence DEG set (304 unique genes). Included when DE in >=3 of "
        "the 12 ORBm cell types AND detected in >=50 pct of cells: relative enrichment alone is not enough "
        "for Xenium. 106 of the 304 are on this list; the rest are DE in only one or two types or are "
        "undetectable - EXCLUDED_measured names them with numbers.",
        "Dan's amygdala spatial set (GSE283418) contributed the 12_GSE283418_added block. The six members "
        "below 50 pct detection are in EXCLUDED_measured with their numbers.",
        "Every panel version built for this project, scored on one ruler. Two columns need care. "
        "'n_under_50pct_at_best_anchor' scores every gene in the 20 neuronal target populations, which is "
        "unfair to a microglial, cholinergic or subtype gene; 'n_under_50pct_own_population' scores it in "
        "the population it is meant to report and is the honest number. The 'too_low_to_map' column is "
        "computed at subclass level for ALL panels so the comparison stays apples-to-apples, which means "
        "it still counts a few subtype markers that FINAL_GENE_LIST scores correctly inside their own "
        "sub-population (SUBTYPE_MARKER_CHECK has the per-cell proof for those 30 genes).",
        "SUPERTYPE_COVERAGE counts 96 sub-populations: those that have at least one qualifying marker "
        "ANYWHERE in the 32,285-gene atlas under the strict rule (>=50 pct of the sub-population AND "
        ">=20pp above the next-highest SIBLING sub-population). A looser rule - gap measured against the "
        "rest of the parent cell type pooled - yields 107 sub-populations and barely discriminates between "
        "panels (even the 10x base panel alone covers 107/107 under it). The strict number is the one that "
        "separates panels: 66/96 on v8 versus 96/96 here.",
        "Page 5: \"The EEG / non-invasive-biomarker effort and the circadian (ZT) cohort have been removed "
        "from scope. Circadian, sleep, and basic executive-function measures may still be collected "
        "opportunistically as exploratory, non-gating secondaries\". So the clock block (33_SOW_clock_axis) "
        "serves an EXPLORATORY secondary, not a gated deliverable - but PER2 is still named in the "
        "committed provisional panel (SATB2 identity, FOS, PER2) and in the IT/CT reprogramming sentence, "
        "and with no ZT cohort the only way to see a clock effect is transcriptional. Delete that one block "
        "if you disagree; nothing else depends on it.",
        "tdTomato and iCre are transgene probes: they cannot be scored in the atlas, and the tdTomato probe "
        "reads any Rosa26-CAG-LSL-tdTomato line (confirm the JAX strain). hM4Di / hM3Dq and the enhancer-AAV "
        "of SOW Aim 2 are NOT on this list: this Xenium arm images a TRAP2 x tdTomato cross, so there is no "
        "viral transcript to read. If any Xenium tissue comes from AAV-injected animals, add probes against "
        "the construct (hM4Di/hM3Dq, mCherry or WPRE) at that point. Panel-size product tiers are 10x "
        "commercial terms, not something any file here states - they are irrelevant to this list, which was "
        "built with no size cap.",
        "CROWDING_load gives each gene's predicted share of the panel's transcripts (mean linear abundance "
        "over all 226,886 cells, normalised to the panel). The top 10 genes carry roughly 39 pct of the "
        "load and the top 25 about 56 pct - Nrxn3, Nrxn1, Syt1 and Nlgn1 alone are a quarter of it. Those "
        "four are plasticity-axis genes with near-universal expression, so they cost decoding capacity and "
        "give almost no cell-typing information. Nothing was removed on this basis - it is your call - but "
        "if the run shows optical crowding, that sheet is the order in which to cut.",
        "All percentages and levels come from 10x scRNA-seq. Real Xenium has fewer transcripts per cell and "
        "segmentation error, so treat them as an upper bound and as a RANKING between genes, not as a "
        "promise of per-cell sensitivity. tdTomato and iCre are transgenes and cannot be scored in the atlas.",
        "v3/E_Planning: allen_extract_*.py -> measure_all_genes.py -> measure_expression_levels.py -> "
        "bench_discovery_vs_v8.py -> build_panel_v9_final.py -> compare_all_panels.py. Repo: "
        "Genelist_analysis_WMB.",
    ]})

    shutil.copy2(SRC, DST)
    with pd.ExcelWriter(DST, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        readme.to_excel(w, "READ_ME", index=False)
        final.to_excel(w, "FINAL_GENE_LIST", index=False)
        (final.groupby("category").gene.count().rename("n_genes").to_frame()
         .to_excel(w, "BY_CATEGORY"))
        orbf.to_excel(w, "ORBm_LIST", index=False)
        bmaf.to_excel(w, "BMAp_LIST", index=False)
        gpcr_ct.to_excel(w, "GPCR_BY_CELLTYPE", index=False)
        gpcr_anchor.to_excel(w, "GPCR_PER_CELLTYPE", index=False)
        drugs_sum.to_excel(w, "GPCR_DRUGS", index=False)
        drugs.to_excel(w, "GPCR_DRUGS_DETAIL", index=False)
        paper_vs_allen.to_excel(w, "PAPER_vs_ALLEN", index=False)
        sup_cov.to_excel(w, "SUPERTYPE_COVERAGE", index=False)
        if len(stl):
            stl.reset_index().to_excel(w, "SUBTYPE_MARKER_CHECK", index=False)
        optional.to_excel(w, "OPTIONAL_ADD_ONS", index=False)
        if len(pm):
            pm.to_excel(w, "PAPER_MARKER_CHECK", index=False)
        if len(anchor_ceiling):
            anchor_ceiling.to_excel(w, "ANCHOR_CEILING", index=False)
        addf.to_excel(w, "ADDED_v9", index=False)
        excluded.to_excel(w, "EXCLUDED_measured", index=False)
        bench.to_excel(w, "BENCHMARK", index=False)
        if len(crowd):
            crowd.to_excel(w, "CROWDING_load", index=False)
        nn_path = O / "_TEST_nn_perclass.csv"
        if nn_path.exists():
            nn = pd.read_csv(nn_path)
            nn["kept_on_this_panel"] = [", ".join(g for g in MIN_NN_KEEP) if VARIANT in ("minnn", "all20")
                                        else "all 8 dedicated probes kept"] * len(nn)
            nn.to_excel(w, "NONNEURONAL_TEST", index=False)
        if len(stress):
            stress.to_excel(w, "STRESS_xenium_sparsity", index=False)
        if len(sow_audit):
            sow_audit.to_excel(w, "SOW_GENE_AUDIT", index=False)
        if len(comparison):
            comparison.to_excel(w, "PANEL_COMPARISON", index=False)
        sources.to_excel(w, "SOURCES", index=False)

    wb = load_workbook(DST)
    for s in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER", "FOR_MarkGreg", "EXPANSION_LIST",
              "ADDED_v7", "CUT_v7", "KEPT_vs_IDEAL178", "NONNEURONAL_FREE", "ORPHANS_DROPPED",
              "CUT_v8_scope_creep", "BENCHMARK_celltype"):
        if s in wb.sheetnames:
            del wb[s]
    order = ["READ_ME", "FINAL_GENE_LIST", "BY_CATEGORY", "PANEL_COMPARISON", "ORBm_LIST",
             "BMAp_LIST", "GPCR_BY_CELLTYPE", "GPCR_PER_CELLTYPE", "GPCR_DRUGS",
             "GPCR_DRUGS_DETAIL", "PAPER_vs_ALLEN", "SUPERTYPE_COVERAGE",
             "SUBTYPE_MARKER_CHECK", "PAPER_MARKER_CHECK", "ANCHOR_COVERAGE", "ANCHOR_CEILING", "ADDED_v9",
             "OPTIONAL_ADD_ONS", "EXCLUDED_measured", "SOW_GENE_AUDIT", "BENCHMARK", "STRESS_xenium_sparsity", "CROWDING_load", "NONNEURONAL_TEST", "SOURCES"]
    wb._sheets.sort(key=lambda ws: order.index(ws.title) if ws.title in order else 99)
    wb.save(DST)
    shutil.copy2(DST, DL / DST.name)

    # ---------- audit ----------
    print(f"\n{DST.name}: {len(final)} genes")
    print(final.groupby("category").gene.count().to_string())
    assert final.gene.duplicated().sum() == 0
    for g in ("tdTomato", "iCre", "Fos", "Arc", "Npas4", "Per2", "Oprm1", "Satb2", "Adrb1",
              "Htr2a", "Creb1", "Slc17a7", "Gad1", "Snap25", "Clock", "Arntl", "Cry1"):
        assert g in fin, f"missing {g}"
    orph = (set(orbf.gene) | set(bmaf.gene)) - fin
    assert not orph, f"orphans {sorted(orph)}"
    print(f"subtype coverage: {n_before}/{n_total} on v8 -> "
          f"{gs.group[gs.gene.isin(fin)].nunique()}/{n_total} on v9")
    print(final.level_verdict.value_counts().to_string())
    print(f"ORBm list {len(orbf)} | BMAp list {len(bmaf)} | SOW-named {sum(g in fin for g in SOW)}/8")
    print(f"copied to {DL / DST.name}")


if __name__ == "__main__":
    main()
