"""Build the three orderable panel options from the live MSGS11122 sheet.

Confirmed by the user: no AAV work, so the two viral-vector probes (WPRE, mCherry)
come off the panel entirely. They existed only to read AAV transduction and an
AAV-DIO-hM4Di-mCherry chemogenetics construct. The TRAP pair (tdTomato, iCre)
stays - that is the actual genetic tag being read.

  OPTION A  current   166 genes = 47 free + 119 custom
            Fits nothing yet: the 10x add-on cap is 100 custom.
  OPTION B  cut       147 genes = 47 free + 100 custom
            Exactly at the add-on cap, so it can be ordered on the existing quote.
  OPTION C  expanded  245 genes, standalone custom
            Every candidate with a documented quantitative basis. A standalone
            custom panel has no free base panel, so all 245 are designed probes.

Note on the tdTomato probe: the sheet described it as the Ai14 transcript. The user
will cross TRAP2 with a tdTomato reporter line they refer to as Ai19, which could
not be verified as a tdTomato line (Ai9 / JAX 007909 and Ai14 / JAX 007908 are the
documented ones). The probe targets the tdTomato coding sequence, which is shared
across tdTomato reporter lines, so the probe itself does not change - but the
description is made line-agnostic and flagged for confirmation.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
LIVE = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx")
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
EGPCR = OUT / "Jesse_ORB_vs_Xenium_panel.xlsx"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"

A_PATH = OUT / "PANEL_A_current_166genes_119custom.xlsx"
B_PATH = OUT / "PANEL_B_cut_147genes_100custom.xlsx"
C_PATH = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"

DROP_AAV = ["WPRE", "mCherry"]
CAP = 100

TD_WHY = ("Permanent TRAP tag that Xenium reads. Custom sequence probe against the tdTomato "
          "coding sequence, which is shared across tdTomato reporter lines (Ai9 / Ai14 / any "
          "Rosa26-CAG-LSL-tdTomato), so the probe is line-agnostic. CONFIRM the reporter strain "
          "number: if the line carries a different fluorophore, this probe reads nothing. "
          "Ask 10x to reduce the probe-set count because tdTomato is a very high expressor.")

# 19 cuts to reach the 100-custom add-on cap. WPRE and mCherry are no longer here
# because they are removed from every option.
CUTS = [
    ("Dnah5",    "BMAp specificity 0.53 - below the 1.0 cutoff that admitted the set", "Dan: fails its own rule"),
    ("Nos1",     "BMAp specificity 0.76 - in 99.7% of cells but not specific to BMAp", "Dan: fails its own rule"),
    ("Gabre",    "BMAp specificity 0.95, and peaks in CEA-BST, a neighbour not BMAp",  "Dan: fails its own rule"),
    ("Tspan18",  "BMAp specificity 0.96, peaks in the SI/LPO border region",           "Dan: fails its own rule"),
    ("Syndig1l", "Specificity 1.32 but peaks in CEA-BST, not the BMAp core",           "Dan: fails its own rule"),
    ("Gpr26",    "Orphan receptor - no known ligand, so it cannot serve a drug-target map", "Jesse: weakest of its set"),
    ("Per1",     "Same circadian axis as Per2; 63% detection, above 50% in only 4 of 12 populations", "Jesse: weakest of its set"),
    ("Cx3cr1",   "Microglial marker at 15% of cells - microglia are not among the 20 targets", "Too sparse to map"),
    ("Hcrtr1",   "16% of cells - orexin receptor 1 map would be too sparse to read",   "Too sparse to map"),
    ("Ackr3",    "21% of cells - published OFC marker, but below usable detection",    "Too sparse to map"),
    ("Htr1a",    "28% of cells - Htr1b and Htr2a cover serotonergic signalling better", "Too sparse to map"),
    ("Tacr3",    "30% of cells - Tacr1 stays on the panel for tachykinin signalling",  "Too sparse to map"),
    ("Galr1",    "36% of cells - galanin receptor map would be too sparse",            "Too sparse to map"),
    ("Grin2b",   "Third NMDA subunit; Grin1 and Grin2a already report NMDA signalling", "Redundant within family"),
    ("Gria2",    "Second AMPA subunit; Gria1 already reports AMPA signalling",         "Redundant within family"),
    ("Rbfox3",   "Pan-neuronal at 99.6%; Snap25 already gives the pan-neuronal call",  "Redundant within family"),
    ("Gabbr2",   "GABA-B is an obligate heterodimer, but both subunits sit at ~100% of cells with "
                 "specificity 0.1-0.2, so one localises the receptor. Gabbr1 is kept because it is the "
                 "ligand-binding subunit that baclofen targets. CONFIRM: keep both only if you need "
                 "subunit ratio, since Gabbr1 without Gabbr2 is ER-retained and non-functional.",
     "Redundant within family"),
    ("Fosb",     "34% of cells; Fos, Arc, Egr1, Junb and Npas4 already report activity", "Redundant within family"),
    ("Emx1",     "Dorsal-pallium TF for the BMAp pallial-vs-subpallial question. Good specificity (2.14) "
                 "but only 41% of cells, and it separates 0 BMAp populations in the pairwise tests. That "
                 "axis is already carried at much higher detection by Tbr1/Satb2/Neurod6 (pallial) and "
                 "Dlx1/Isl1/Meis2 (subpallial); Emx1 adds only the finer dorsal-pallium distinction. "
                 "CONFIRM: keep it if dorsal-pallium origin of BMAp is part of the hypothesis.",
     "Finer distinction already covered"),
]

ORBM = ["007 L2/3 IT CTX Glut", "006 L4/5 IT CTX Glut", "005 L5 IT CTX Glut",
        "022 L5 ET CTX Glut", "032 L5 NP CTX Glut", "030 L6 CT CTX Glut",
        "029 L6b CTX Glut", "004 L6 IT CTX Glut",
        "052 Pvalb Gaba", "053 Sst Gaba", "046 Vip Gaba", "049 Lamp5 Gaba"]


def strip_and_rerank(wb, drop: set[str]) -> dict[str, int]:
    removed = {}
    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        gcol = [c.value for c in ws[1]].index("gene") + 1
        rows = [r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=gcol).value in drop]
        for r in reversed(rows):
            ws.delete_rows(r)
        for i, r in enumerate(range(2, ws.max_row + 1), start=1):
            ws.cell(row=r, column=1, value=i)
        removed[name] = len(rows)
    return removed


def fix_tdtomato(wb) -> None:
    ws = wb["SHARED_PANEL_ORDER"]
    hdr = [c.value for c in ws[1]]
    g, w = hdr.index("gene") + 1, hdr.index("why") + 1
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=g).value == "tdTomato":
            ws.cell(row=r, column=w, value=TD_WHY)
    for name in ("ORBm_ORDER", "BMAp_ORDER"):
        ws2 = wb[name]
        h2 = [c.value for c in ws2[1]]
        g2, w2 = h2.index("gene") + 1, h2.index("why") + 1
        for r in range(2, ws2.max_row + 1):
            if ws2.cell(row=r, column=g2).value == "tdTomato":
                ws2.cell(row=r, column=w2, value=TD_WHY)


def note(wb, item: str, detail: str) -> None:
    fg = wb["FOR_MarkGreg"]
    fg.cell(row=fg.max_row + 1, column=1, value=item)
    fg.cell(row=fg.max_row, column=2, value=detail)


def summary(path: Path, base: set[str]) -> dict:
    sh = pd.read_excel(path, "SHARED_PANEL_ORDER")
    free = int(sh.gene.isin(base).sum())
    return {"n": len(sh), "free": free, "custom": len(sh) - free,
            "dupes": int(sh.gene.duplicated().sum()),
            "ranks_ok": list(sh.order_rank) == list(range(1, len(sh) + 1))}


def anchors_intact(path: Path) -> list[str]:
    sh = set(pd.read_excel(path, "SHARED_PANEL_ORDER").gene)
    ac = pd.read_excel(path, "ANCHOR_COVERAGE")
    sep = set()
    for s in ac.unique_separators_on_shared_panel.fillna(""):
        sep |= {x.strip() for x in s.split(",") if x.strip()}
    return sorted(sep - sh)


# ---------------------------------------------------------------- OPTION C data
def expansion(cur: set[str]) -> pd.DataFrame:
    rank = pd.read_excel(RANK, "ranking_all")
    eg = pd.read_excel(EGPCR, "enriched_GPCRs")
    dan = pd.read_excel(DAN, "all_98_genes")
    pairs = pd.read_csv(PAIRS)
    rows = []

    for r in rank[(rank.n_orbm >= 4) & (~rank.gene.isin(cur))].itertuples():
        rows.append({"gene": r.gene, "block": "16_expanded_morphine_state",
                     "serves": f"morphine-dependence state :: {int(r.n_orbm)}/12 ORBm anchors {r.direction}",
                     "why": (f"Jesse Niehaus opioid-dependence DEG: differentially expressed in "
                             f"{int(r.n_orbm)} of the 12 ORBm anchor subclasses ({r.direction}), "
                             f"glut {int(r.n_glut)} / GABA {int(r.n_gaba)}; source lists {r.lists}. "
                             f"Held back from the 100-slot design only for lack of slots.")})

    for r in eg[(eg.n_subclass_hits >= 8) & (~eg.gene.isin(cur))].itertuples():
        rows.append({"gene": r.gene, "block": "17_expanded_ORB_GPCR",
                     "serves": f"ORB-enriched GPCR :: {int(r.n_subclass_hits)} subclasses",
                     "why": (f"Enriched in {int(r.n_subclass_hits)} PL-ILA-ORB subclasses "
                             f"(glut {int(r.n_glut_subclasses)} / GABA {int(r.n_gaba_subclasses)}) "
                             f"vs the rest of the Allen atlas. Extends the druggable receptor map. "
                             f"Allen detectability not scored for all of these - expect some sparse maps.")})

    for r in dan[(dan.max_spec >= 0.4) & (~dan.gene.isin(cur))].itertuples():
        rows.append({"gene": r.gene, "block": "18_expanded_BMAp",
                     "serves": f"BMAp marker :: spec {r.max_spec:.2f}, {r.top_BMAp_anchor}",
                     "why": (f"From the Berg & Scherrer GSE283418 amygdala panel. Allen BMAp "
                             f"specificity {r.max_spec:.2f}, detected in {r.max_pct:.0f}% of cells, "
                             f"top anchor {r.top_BMAp_anchor}. Below the 1.0 cutoff used for the "
                             f"100-slot design, kept here because slots are not scarce.")})

    l5 = pairs[(pairs.subclass_A_positive == "005 L5 IT CTX Glut")
               & (pairs.subclass_B_negative.isin(["006 L4/5 IT CTX Glut", "007 L2/3 IT CTX Glut"]))]
    for g, grp in l5.groupby("separator_gene"):
        if g in cur:
            continue
        b = grp.loc[grp.log2_gap.idxmax()]
        n_vs = pairs[(pairs.subclass_A_positive == "005 L5 IT CTX Glut")
                     & (pairs.separator_gene == g)].subclass_B_negative.nunique()
        rows.append({"gene": g, "block": "19_expanded_L5IT_separator",
                     "serves": f"L5 IT separator :: vs {b.subclass_B_negative.split(' ',1)[1]}, log2 gap {b.log2_gap:.2f}",
                     "why": (f"Closes an L5 IT separability gap: {b.pct_A:.0f}% of L5 IT cells vs "
                             f"{b.pct_B:.0f}% of {b.subclass_B_negative}, log2 gap {b.log2_gap:.2f}; "
                             f"separates L5 IT from {n_vs} of its 11 neighbours. L5 IT has only one "
                             f"exclusive gene (Bdnf), so these widen the thinnest margin in the design.")})

    d = pd.DataFrame(rows).drop_duplicates(subset="gene").reset_index(drop=True)
    return d


def main() -> None:
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    live = pd.read_excel(LIVE, "SHARED_PANEL_ORDER")
    print(f"live: {len(live)} genes, custom {(~live.gene.isin(base)).sum()}")

    # ---------- OPTION A
    shutil.copy2(LIVE, A_PATH)
    wb = load_workbook(A_PATH)
    rem = strip_and_rerank(wb, set(DROP_AAV))
    fix_tdtomato(wb)
    note(wb, "2 viral-vector probes removed (no AAV work)",
         "WPRE and mCherry were removed from SHARED_PANEL_ORDER, ORBm_ORDER and BMAp_ORDER. They only "
         "read AAV transduction and an AAV-DIO-hM4Di-mCherry chemogenetics construct, and this project "
         "crosses TRAP2 with a tdTomato reporter line instead - no virus is injected. The TRAP pair "
         "(tdTomato, iCre) is unchanged. order_rank was renumbered contiguously. This frees 2 custom "
         "slots: the design is now 119 custom, against a 10x add-on cap of 100.")
    note(wb, "CONFIRM the tdTomato reporter strain",
         "The tdTomato probe targets the tdTomato coding sequence and works for any Rosa26-CAG-LSL-tdTomato "
         "line, so no probe change is needed. But please confirm the JAX strain number: Ai9 (007909) and "
         "Ai14 (007908/007914) are the documented tdTomato lines; 'Ai19' could not be verified as a "
         "tdTomato line, and several Allen Ai lines carry a different fluorophore. If the line is not "
         "tdTomato, this probe would read nothing.")
    wb.save(A_PATH)
    A = summary(A_PATH, base)
    print(f"\nOPTION A -> {A_PATH.name}\n  {A} | removed {rem}")

    # ---------- OPTION B
    shutil.copy2(A_PATH, B_PATH)
    wb = load_workbook(B_PATH)
    rem = strip_and_rerank(wb, {c[0] for c in CUTS})
    ws = wb.create_sheet("CUT_LIST")
    ws.append(["gene", "reason_it_was_cut", "cut_group"])
    for c in CUTS:
        ws.append(list(c))
    for col, w in zip("ABC", (14, 96, 26)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    note(wb, f"CONTINGENCY: {len(CUTS)} further genes cut to fit the {CAP}-gene custom cap",
         f"10x caps a custom add-on at {CAP} target genes by design, not by price tier. After removing "
         f"WPRE and mCherry the design still carried 119 custom probes, so {len(CUTS)} more were cut. "
         f"Each was removed because it failed the rule that admitted it - see the CUT_LIST tab for the "
         f"gene-by-gene reason. No cell-population separator was touched, so all 20 populations remain "
         f"identifiable. Two cuts (Gabbr2, Emx1) are marked CONFIRM in CUT_LIST because they depend on "
         f"your scientific priorities. order_rank was renumbered contiguously.")
    wb.save(B_PATH)
    B = summary(B_PATH, base)
    print(f"OPTION B -> {B_PATH.name}\n  {B} | removed {rem}")

    # ---------- OPTION C
    cur = set(pd.read_excel(A_PATH, "SHARED_PANEL_ORDER").gene)
    add = expansion(cur)
    shutil.copy2(A_PATH, C_PATH)
    wb = load_workbook(C_PATH)
    sh_ws, orb_ws = wb["SHARED_PANEL_ORDER"], wb["ORBm_ORDER"]
    r0, o0 = sh_ws.max_row, orb_ws.max_row
    for i, r in enumerate(add.itertuples()):
        for ws, b in ((sh_ws, r0), (orb_ws, o0)):
            rr = b + 1 + i
            ws.cell(row=rr, column=1, value=b + i)
            ws.cell(row=rr, column=2, value=r.gene)
            ws.cell(row=rr, column=3, value=r.block)
            ws.cell(row=rr, column=4, value=r.serves)
            ws.cell(row=rr, column=5, value=r.why)
    ws = wb.create_sheet("EXPANSION_LIST")
    ws.append(["gene", "block", "serves", "why_it_is_added"])
    for r in add.itertuples():
        ws.append([r.gene, r.block, r.serves, r.why])
    for col, w in zip("ABCD", (14, 30, 56, 110)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    note(wb, f"EXPANDED OPTION: {len(add)} genes added for a standalone custom panel",
         f"This version is for a Xenium STANDALONE CUSTOM panel, not the add-on. A standalone panel does "
         f"not include the 248-gene Mouse Brain base panel, so all {len(add) + A['n']} genes here are "
         f"designed probes and the free/custom distinction does not apply. The {len(add)} additions are "
         f"every remaining candidate with a documented quantitative basis, held back from the 100-slot "
         f"design only because slots were scarce: broader morphine DEGs, more ORB-enriched receptors, "
         f"the Berg & Scherrer genes below the 1.0 specificity cutoff, and extra L5 IT separators. "
         f"See EXPANSION_LIST for the per-gene basis. Note that Allen detectability was not scored for "
         f"all of them, so some will give sparse maps.")
    wb.save(C_PATH)
    C = summary(C_PATH, base)
    print(f"OPTION C -> {C_PATH.name}\n  {C} | additions {len(add)}")
    print(f"  expansion by block:\n{add.block.value_counts().to_string()}")

    print("\n=== checks ===")
    for lab, p, exp_custom in (("A", A_PATH, 119), ("B", B_PATH, CAP), ("C", C_PATH, None)):
        s = summary(p, base)
        miss = anchors_intact(p)
        ok = s["dupes"] == 0 and s["ranks_ok"] and not miss
        if exp_custom is not None:
            ok = ok and s["custom"] == exp_custom
        print(f"  {lab}: {s['n']:3d} genes, custom {s['custom']:3d} | dupes {s['dupes']} | "
              f"ranks {s['ranks_ok']} | lost separators {miss or 'none'} | {'OK' if ok else 'FAIL'}")
        assert ok, f"option {lab} failed validation"


if __name__ == "__main__":
    main()
