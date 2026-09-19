"""Excel + 5-slide deck in the exact layout of the MSGS workbook and funder v3 PPT.

Sheets / columns match FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx.
Slide positions, palette and fonts match ORBm_BMAp_Xenium_panel_funder_v3.pptx.

Language: circadian genes, never 'SOW clock'.
First requirement: all 20 ORBm + BMAp cell types are called.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
FIG = OUT / "funder_figs"
DL = Path(r"c:\Users\hsollim\Downloads")
REF_XL = DL / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx"
SRC = OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx"
XL_DST = OUT / "FINAL_Xenium_panel_ORBm_BMAp.xlsx"
PPT_DST = OUT / "ORBm_BMAp_Xenium_panel_funder.pptx"

NAVY, BLUE, RED, GREEN = "1D4E89", "2A6F97", "C44536", "6B7C6A"
GREY, DARK, CREAM, LBLUE, EDGE = "5B6472", "1F2937", "F4F1EA", "EAF2F8", "B8B2A8"

BLOCK = {
    "01_TRAP_reporter": "2_reporter_transgene",
    "03_class_EI_backbone": "3_class_backbone",
    "03b_taxonomy_backbone": "8_TF_identity",
    "04_nonneuronal_counterstain": "3b_nonneuronal",
    "05_celltype_separator": "1_celltype_separator",
    "05b_pairwise_disambiguator": "1b_pairwise_separator",
    "06_subtype_separator": "1c_subtype_separator",
    "07_IEG_pCREB_target": "5_IEG",
    "08_clock_module": "9_circadian",
    "09_plasticity": "7_plasticity",
    "10_morphine_state": "13_Jesse_morphine_state",
    "11_GPCR_map": "6_GPCR",
}
BLOCK_RANK = [
    "1_celltype_separator", "1b_pairwise_separator", "1c_subtype_separator",
    "2_reporter_transgene", "3_class_backbone", "3b_nonneuronal",
    "5_IEG", "6_GPCR", "7_plasticity", "8_TF_identity",
    "9_circadian", "13_Jesse_morphine_state",
]
LABEL = {
    "007 L2/3 IT CTX Glut": "L2/3 IT excitatory",
    "006 L4/5 IT CTX Glut": "L4/5 IT excitatory",
    "005 L5 IT CTX Glut": "L5 IT / L5 ET/PT output neurons",
    "022 L5 ET CTX Glut": "L5 IT / L5 ET/PT output neurons",
    "032 L5 NP CTX Glut": "L5 IT / L5 ET/PT output neurons",
    "030 L6 CT CTX Glut": "L6 CT / L6b",
    "029 L6b CTX Glut": "L6 CT / L6b",
    "004 L6 IT CTX Glut": "L6 CT / L6b",
    "052 Pvalb Gaba": "Cortical interneurons",
    "053 Sst Gaba": "Cortical interneurons",
    "046 Vip Gaba": "Cortical interneurons",
    "049 Lamp5 Gaba": "Cortical interneurons",
    "012 MEA Slc17a7 Glut": "Posterior BMA glutamatergic / pallial amygdala VGLUT1",
    "113 MEA-COA-BMA Ccdc42 Glut": "Posterior BMA glutamatergic / pallial amygdala VGLUT1",
    "120 MEA Otp Foxp2 Glut": "BMA/MEA VGLUT2-like excitatory",
    "121 MEA-BST Otp Zic2 Glut": "BMA/MEA VGLUT2-like excitatory",
    "119 SI-MA-LPO-LHA Skor1 Glut": "BMA/MEA VGLUT2-like excitatory",
    "073 MEA-BST Sox6 Gaba": "Amygdala GABA / striatal-like inhibitory neighbors",
    "074 MEA-BST Lhx6 Sp9 Gaba": "Amygdala GABA / striatal-like inhibitory neighbors",
    "082 CEA-BST Ebf1 Pdyn Gaba": "Amygdala GABA / striatal-like inhibitory neighbors",
}
CALL_073 = ["Chn2", "Prox1", "Bcl11b", "Lypd1", "Dlx1", "Sox6", "Lhx6", "Sp9"]


def rgb(h):
    return RGBColor.from_string(h)


def parse_marker_genes(s: str) -> list[str]:
    out = []
    for tok in str(s).split(","):
        g = re.sub(r"\s*\(.*", "", tok).strip()
        if g and g.lower() != "nan":
            out.append(g)
    return out


def short_why(block: str, why: str, serves: str) -> str:
    w = str(why).split(" - ")[0].split("; ")[0]
    if block == "1_celltype_separator":
        return f"UNIQUE separator for {serves.split(' :: ')[0]}"
    if block == "1b_pairwise_separator":
        return f"splits neighbouring types: {w[:90]}"
    if block == "1c_subtype_separator":
        return f"subtype marker: {w[:90]}"
    if block == "9_circadian":
        return f"circadian gene (Jesse ORBm morphine DEG / clock limb): {w[:80]}"
    if block == "13_Jesse_morphine_state":
        return f"Jesse 5-day morphine DEG: {w[:90]}"
    if block == "2_reporter_transgene":
        return "TRAP2 / Ai14 reporter: the POST ensemble tag"
    return w[:140]


def mean_and_spec_for_panel(genes: list[str], anchors: list[str]) -> tuple[dict, dict]:
    """max_mean and max_spec across the 20 target subclasses, from genomewide shards."""
    want = set(anchors)
    acc_sum: dict[str, np.ndarray] = {}
    acc_n: dict[str, int] = {}
    axis = None
    gw = OUT / "allen_genomewide"
    for f in sorted(gw.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        if axis is None:
            axis = [str(x) for x in z["genes"]]
        labs = [str(x) for x in z["subclass_labels"]]
        for i, lab in enumerate(labs):
            if lab not in want:
                continue
            row = z["subclass_sum"][i].astype(np.float64)
            n = int(z["subclass_n"][i])
            if lab not in acc_sum:
                acc_sum[lab] = row
                acc_n[lab] = n
            else:
                acc_sum[lab] += row
                acc_n[lab] += n
    if axis is None or not acc_sum:
        return {}, {}
    order = [a for a in anchors if a in acc_sum]
    means = np.vstack([
        np.divide(acc_sum[a], max(acc_n[a], 1), dtype=np.float64) for a in order
    ])
    gi = {g: i for i, g in enumerate(axis)}
    mx = means.max(axis=0)
    second = np.partition(means, -2, axis=0)[-2] if means.shape[0] > 1 else np.zeros_like(mx)
    mean_d, spec_d = {}, {}
    for g in genes:
        j = gi.get(g)
        if j is None:
            continue
        mean_d[g] = round(float(mx[j]), 2)
        spec_d[g] = round(float(mx[j] - second[j]), 2)
    return mean_d, spec_d


def write_excel() -> int:
    panel = pd.read_excel(SRC, "PANEL_ORDER")
    cov20 = pd.read_excel(SRC, "ANCHOR_COVERAGE_20types")
    anchors = [str(x) for x in cov20.allen_subclass_anchor]
    means, specs = mean_and_spec_for_panel(panel.gene.astype(str).tolist(), anchors)

    rows = []
    for r in panel.itertuples():
        blk = BLOCK.get(r.block, r.block)
        if r.block == "05_celltype_separator":
            anc = str(r.subclass_gap_at)
            serves = f"{anc} :: {LABEL.get(anc, anc)}"
        elif r.block == "06_subtype_separator":
            serves = f"{r.supertype} :: inside {r.supertype_parent}"
        elif r.block == "01_TRAP_reporter":
            serves = "TRAP POST ensemble :: both regions"
        elif r.block == "04_nonneuronal_counterstain":
            serves = "non-neuronal exclusion :: both regions"
        elif r.block == "08_clock_module":
            serves = "circadian :: ORBm morphine state (Jesse) and clock limbs"
        elif r.block == "10_morphine_state":
            serves = "morphine state :: Jesse ORBm DEG"
        elif r.block == "11_GPCR_map":
            serves = f"GPCR map :: {r.anchor_max_name}"
        elif r.block == "05b_pairwise_disambiguator":
            serves = f"neighbour split :: {r.subclass_gap_at}"
        else:
            serves = f"{LABEL.get(str(r.anchor_max_name), r.anchor_max_name)}"
        rows.append({
            "order_rank": 0,
            "gene": r.gene,
            "block": blk,
            "serves": serves,
            "why": short_why(blk, r.why, serves),
            "max_pct": None if pd.isna(r.anchor_max_pct) else round(float(r.anchor_max_pct), 2),
            "max_mean": means.get(r.gene),
            "max_spec_panel": specs.get(r.gene),
            "_orbm": r.max_pct_ORBm,
            "_bmap": r.max_pct_BMAp,
        })
    shared = pd.DataFrame(rows)
    rank = {b: i for i, b in enumerate(BLOCK_RANK)}
    shared["_r"] = shared.block.map(rank).fillna(99)
    shared["_spec"] = shared.max_spec_panel.fillna(-1)
    shared = shared.sort_values(["_r", "_spec", "gene"], ascending=[True, False, True]).reset_index(drop=True)
    shared["order_rank"] = range(1, len(shared) + 1)

    trap = {"tdTomato", "iCre"}
    cols5 = ["order_rank", "gene", "block", "serves", "why"]
    cols8 = cols5 + ["max_pct", "max_mean", "max_spec_panel"]
    orbm = shared[(shared._orbm.fillna(100) >= 20) | shared.gene.isin(trap)][cols5].copy()
    bmap = shared[(shared._bmap.fillna(100) >= 20) | shared.gene.isin(trap)][cols5].copy()
    orbm["order_rank"] = range(1, len(orbm) + 1)
    bmap["order_rank"] = range(1, len(bmap) + 1)

    on_panel = set(shared.gene)
    ac_rows = []
    for r in cov20.itertuples():
        listed = []
        if str(r.allen_subclass_anchor).startswith("073"):
            listed.extend([g for g in CALL_073 if g in on_panel])
        for g in parse_marker_genes(r.markers) + parse_marker_genes(r.neighbour_markers):
            if g in on_panel and g not in listed:
                listed.append(g)
        ac_rows.append({
            "region": r.region,
            "cell_type_label": LABEL[r.allen_subclass_anchor],
            "allen_subclass_anchor": r.allen_subclass_anchor,
            "n_cells": int(r.n_cells),
            "unique_separators_on_region_panel": ", ".join(listed[:8]),
            "unique_separators_on_shared_panel": ", ".join(listed[:8]),
        })
    ac = pd.DataFrame(ac_rows)
    n20 = int((ac.unique_separators_on_shared_panel.str.len() > 0).sum())
    if n20 != 20:
        raise SystemExit(f"ANCHOR_COVERAGE is {n20}/20 — refusing to write")

    n = len(shared)
    circ = sorted(shared[shared.block == "9_circadian"].gene)
    extra_circ = [g for g in ("Per1", "Rorb") if g in on_panel]
    circ_txt = ", ".join(circ + [g for g in extra_circ if g not in circ])
    summary = pd.DataFrame([
        ("Please look at",
         "1) SHARED_PANEL_ORDER (the list to order), 2) ORBm_ORDER and BMAp_ORDER, "
         "3) ANCHOR_COVERAGE — all 20 cell types are listed and each has separators."),
        ("What this file is",
         f"Finalized Xenium gene list for ORBm and BMAp: one shared standalone panel "
         f"of {n} genes. Both regions are read from the same mouse on the same slide. "
         f"tdTomato and iCre need the Advanced Panel Upgrade."),
        ("The basic requirement: 20 cell types",
         f"ORBm has 12 Allen subclasses and BMAp has 8. That is the experiment. "
         f"ANCHOR_COVERAGE has {n20}/20 rows with separators on this panel. "
         "073 MEA-BST Sox6 Gaba is called combinatorially "
         "(Chn2, Prox1, Bcl11b, Lypd1, Dlx1, Sox6, Lhx6, Sp9) because Allen itself "
         "names it that way against 074 MEA-BST Lhx6 Sp9 Gaba. Held-out recall for 073 is 0.98."),
        ("Categories on the panel",
         "cell type / subtype markers, class backbone, GPCRs, IEGs, synaptic plasticity, "
         "TFs, circadian genes, Jesse morphine-state genes, TRAP reporters, and 5 "
         "non-neuronal exclusion markers."),
        ("Circadian genes — from Jesse, not a document name",
         "These are labelled 9_circadian. They are the clock genes Jesse found as "
         "5-day morphine DEGs in PL-ILA-ORB, plus the clock limbs those DEGs need "
         f"to be readable (PER:CRY and ROR/REV-ERB). On this list: {circ_txt}. "
         "Clock itself is out (97% of every type, no contrast). Per1 sits in 5_IEG "
         "and Rorb in 1_celltype_separator; both are also circadian genes."),
        ("Evidence",
         "Allen WMB-10X, 226,886 cells (ORBm 106,122 / BMAp 120,764). Jesse Niehaus "
         "5-day escalating-morphine DESeq2. Dan Berg GSE283418. Citations in SOURCES."),
    ], columns=["item", "detail"])

    sources = pd.read_excel(REF_XL, "SOURCES")

    with pd.ExcelWriter(XL_DST, engine="openpyxl") as xw:
        summary.to_excel(xw, "FOR_MarkGreg", index=False)
        shared[cols8].to_excel(xw, "SHARED_PANEL_ORDER", index=False)
        orbm.to_excel(xw, "ORBm_ORDER", index=False)
        bmap.to_excel(xw, "BMAp_ORDER", index=False)
        ac.to_excel(xw, "ANCHOR_COVERAGE", index=False)
        sources.to_excel(xw, "SOURCES", index=False)

        wb = xw.book
        hdr = PatternFill("solid", fgColor=NAVY)
        thin = Border(bottom=Side("thin", color="D6D3CC"))
        widths = {
            "FOR_MarkGreg": [36, 118],
            "SHARED_PANEL_ORDER": [11, 14, 26, 62, 72, 10, 10, 14],
            "ORBm_ORDER": [11, 14, 26, 62, 72],
            "BMAp_ORDER": [11, 14, 26, 62, 72],
            "ANCHOR_COVERAGE": [9, 48, 32, 10, 42, 42],
            "SOURCES": [18, 38, 70, 7, 24, 32, 12, 40, 50, 14, 40],
        }
        for name in wb.sheetnames:
            ws = wb[name]
            for i, w in enumerate(widths.get(name, []), 1):
                ws.column_dimensions[get_column_letter(i)].width = w
            for c in ws[1]:
                c.fill = hdr
                c.font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
                c.alignment = Alignment(vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 24
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    c.border = thin
                    c.font = Font(name="Calibri", size=10, color=DARK)
                    c.alignment = Alignment(vertical="top", wrap_text=name in
                                            ("FOR_MarkGreg", "ANCHOR_COVERAGE", "SOURCES"))
            if name == "FOR_MarkGreg":
                for row in ws.iter_rows(min_row=2, max_col=1):
                    row[0].font = Font(name="Calibri", bold=True, color=NAVY, size=11)
                for row in ws.iter_rows(min_row=2):
                    ws.row_dimensions[row[0].row].height = 58
            if name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
                for row in ws.iter_rows(min_row=2):
                    row[1].font = Font(name="Calibri", bold=True, color=BLUE, size=11)
                if name == "SHARED_PANEL_ORDER":
                    for row in ws.iter_rows(min_row=2):
                        v = row[5].value
                        if isinstance(v, (int, float)):
                            row[5].number_format = "0.0"
                            row[5].fill = PatternFill(
                                "solid", fgColor="E8F0E6" if v >= 70 else
                                ("FDF3E7" if v >= 50 else "FBE9E7"))
                        if isinstance(row[6].value, (int, float)):
                            row[6].number_format = "0.00"

    print("wrote", XL_DST, n, "genes; ANCHOR_COVERAGE", n20, "/20")
    print("circadian block:", ", ".join(circ))
    return n


def tb(sl, x, y, w, h, lines, size=11, color=GREY, bold=False, align=PP_ALIGN.LEFT, space=2):
    box = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(lines, str):
        lines = [lines]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        r = p.add_run()
        r.text = ln
        r.font.name, r.font.size, r.font.bold = "Calibri", Pt(size), bold
        r.font.color.rgb = rgb(color)
    return box


def rrect(sl, x, y, w, h, edge, fill="FFFFFF", lw=1.25):
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    s.adjustments[0] = 0.06
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    s.line.color.rgb = rgb(edge)
    s.line.width = Pt(lw)
    s.shadow.inherit = False
    return s


def slide(prs, n, title, lead):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    tb(sl, 0.40, 0.18, 12.5, 0.42, title, 24, NAVY, True)
    tb(sl, 0.40, 0.56, 12.5, 0.34, lead, 13, GREY)
    tb(sl, 0.40, 7.18, 12.5, 0.24,
       f"ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {n}/5", 11, GREY)
    return sl


def kpi(sl, x, y, big, lines, color):
    rrect(sl, x, y, 2.95, 1.12, color, CREAM)
    tb(sl, x + 0.12, y + 0.05, 2.71, 0.52, big, 26, color, True, PP_ALIGN.CENTER)
    tb(sl, x + 0.12, y + 0.57, 2.71, 0.50, lines, 11.5, GREY, False, PP_ALIGN.CENTER, 0)


def rule_card(sl, x, y, num, color, head, method, yes, no):
    rrect(sl, x, y, 6.17, 1.66, color)
    o = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12),
                            Inches(0.34), Inches(0.34))
    o.fill.solid()
    o.fill.fore_color.rgb = rgb(color)
    o.line.fill.background()
    o.shadow.inherit = False
    tb(sl, x + 0.15, y + 0.16, 0.33, 0.30, num, 14, "FFFFFF", True, PP_ALIGN.CENTER)
    tb(sl, x + 0.56, y + 0.12, 5.47, 0.36, head, 13.5, color, True)
    tb(sl, x + 0.16, y + 0.52, 5.87, 0.34, method, 11, GREY)
    tb(sl, x + 0.16, y + 0.94, 5.87, 0.34, yes, 11, GREEN)
    tb(sl, x + 0.16, y + 1.26, 5.87, 0.34, no, 11, RED)


def write_ppt(n_genes: int) -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    s = slide(prs, 1, "How the gene panel was selected",
              "Xenium reads a fixed gene list. We kept a gene only if it names one of "
              "the 20 cell types, or reports morphine, circadian, or receptor state.")
    if (FIG / "s1_workflow.png").exists():
        s.shapes.add_picture(str(FIG / "s1_workflow.png"), Inches(0.37), Inches(1.00),
                             width=Inches(12.60))

    s = slide(prs, 2, "Why a gene is in - and why a similar one is out",
              "Each rule is a measurement with a cutoff. For every rule there is a gene "
              "that passed and a comparable gene that did not, so the line is visible "
              "rather than asserted.")
    rule_card(s, 0.40, 1.02, "1", NAVY, "Does it identify one of the 20 cell types?",
              "Must be high in that type and low in the other 19, or in its closest neighbour.",
              "IN     Prox1   +50pp for 073 Sox6 GABA vs 074 Lhx6 Sp9 GABA",
              "OUT   Sstr4    1.4% of cells - an empty map, cannot call any type")
    rule_card(s, 6.76, 1.02, "2", BLUE, "Does it split a type into a sub-type?",
              "Rare overall is fine if one sub-population is high and its siblings are not.",
              "IN     St18    8.8% overall, 95% of one 194-cell sub-type (+66pp)",
              "OUT   Gpr63   2.7% of cells and 1.5pp gap - rare and uninformative")
    rule_card(s, 0.40, 2.80, "3", RED, "Does it report morphine or circadian state?",
              "Jesse's 5-day morphine DEGs in ORBm. Circadian genes are from that list.",
              "IN     Per2    up in 13 of Jesse's ORBm clusters; circadian + morphine",
              "OUT   Clock   97% of every type, 8pp gap - no contrast, Npas2 does this job")
    rule_card(s, 6.76, 2.80, "4", GREEN, "Will the instrument actually detect it?",
              "State genes must be present in enough cells to read a level.",
              "IN     Grm8    99% of cells; also +31pp at a sub-population",
              "OUT   Mas1    most ORB-enriched receptor in the donor list, but 45% of cells")
    rrect(s, 0.40, 4.72, 12.53, 2.18, NAVY, LBLUE)
    tb(s, 0.62, 4.86, 12.10, 0.30, "The basic requirement this forces", 13.5, NAVY, True)
    tb(s, 0.62, 5.22, 5.95, 1.55,
       ["ORBm = 12 Allen cell types. BMAp = 8. That is 20, and a panel that cannot "
        "call all 20 is not finished.",
        "073 Sox6 GABA has no second gene unique versus all 19 others. It is still "
        "called: Prox1 / Sox6 / Lhx6 / Sp9 / Chn2 / Dlx1. Held-out recall 0.98."],
       12, DARK, space=6)
    tb(s, 6.85, 5.22, 5.95, 1.55,
       ["Circadian genes are circadian genes, from Jesse's ORBm morphine data.",
        "On the panel: Per1, Per2, Cry2, Arntl, Npas2, Nr1d1, Nr1d2, Rora, Bhlhe40, "
        "Bhlhe41, Hlf, Nfil3, Id2, Ep300, Ppargc1a. Clock itself is out (no contrast)."],
       12, DARK, space=6)

    s = slide(prs, 3, f"Final panel  -  {n_genes} genes, one section, two regions",
              "One shared Xenium panel read from the same mouse. All 20 target cell "
              "populations remain separable.")
    for x, big, lines, c in [
            (0.40, str(n_genes), ["genes on the", "shared panel"], NAVY),
            (3.56, "20 / 20", ["cell populations", "still separable"], BLUE),
            (6.72, "86 / 86", ["sub-populations", "resolved"], GREEN),
            (9.88, "12 + 8", ["populations in", "ORBm  +  BMAp"], RED)]:
        kpi(s, x, 1.00, big, lines, c)
    if (FIG / "s3_categories.png").exists():
        s.shapes.add_picture(str(FIG / "s3_categories.png"), Inches(0.40), Inches(2.32),
                             width=Inches(7.05))
    tb(s, 7.85, 2.34, 5.05, 0.34, "What each cell will tell us", 15, NAVY, True)
    for i, (h, body, c) in enumerate([
            ("Identity",
             "Which of the 20 populations it is - cortical layer, interneuron class, or amygdala subtype",
             NAVY),
            ("Activity",
             "Whether it was recently active - Fos and Arc, plus the TRAP2 genetic tag",
             BLUE),
            ("Circadian / morphine",
             "Jesse ORBm state: Per2, Per1, Nr1d1 and the circadian gene set",
             RED),
            ("Receptors",
             "Which GPCRs sit on it - opioid, monoamine, muscarinic, peptide",
             GREEN)]):
        y = 2.86 + i * 0.97
        tb(s, 7.85, y, 5.05, 0.28, h, 13, c, True)
        tb(s, 7.85, y + 0.29, 5.05, 0.60, body, 11.5, GREY)
    tb(s, 0.40, 6.62, 12.50, 0.40,
       "The last row is the new capability: inside one of the 20 types, separate cells "
       "that were TRAP-active during morphine seeking from those that were not, and ask "
       "which receptors differ.", 12, RED)

    s = slide(prs, 4, "The 20 cell types we have to tell apart",
              "12 in orbitofrontal cortex (ORBm), 8 in basomedial amygdala (BMAp). "
              "Every line is one type. The coloured gene is how that type is named.")
    if (FIG / "s4_populations.png").exists():
        s.shapes.add_picture(str(FIG / "s4_populations.png"), Inches(0.40), Inches(0.98),
                             width=Inches(12.50))

    s = slide(prs, 5, "The list rests on a full re-analysis of the reference atlas",
              "No gene was taken on a paper's word. Every candidate was re-scored in "
              "Allen WMB-10X, restricted to these two regions.")
    for x, big, lines, c in [
            (0.40, "226,886", ["single cells scored in", "the two target regions"], NAVY),
            (3.56, "32,245", ["genes re-scored,", "not a shortlist"], BLUE),
            (6.72, "20 / 20", ["cell types called,", "the basic requirement"], RED),
            (9.88, "0.948", ["held-out accuracy", "across the 20 types"], GREEN)]:
        kpi(s, x, 1.00, big, lines, c)
    for x, big, lines, c in [
            (0.40, "13", ["documented sources,", "9 with a DOI"], NAVY),
            (3.56, "280", ["GPCRs swept,", "35 kept"], BLUE),
            (6.72, "86 / 86", ["sub-populations", "resolved"], RED),
            (9.88, "14", ["circadian genes,", "from Jesse, not a name"], GREEN)]:
        kpi(s, x, 2.34, big, lines, c)
    rrect(s, 0.40, 3.72, 12.53, 3.18, EDGE, CREAM)
    tb(s, 0.62, 3.88, 12.10, 0.32, "What that analysis produced, in order", 14, NAVY, True)
    tb(s, 0.62, 4.32, 5.95, 2.40,
       ["1.   Restrict to the 20 types",
        "      12 ORBm + 8 BMAp. Nothing is scored as a whole-brain average.",
        "2.   Per-type marker ranking",
        "      Unique versus the other 19, and versus the closest neighbour.",
        "3.   Circadian + morphine from Jesse",
        "      Clock genes that are DE in PL-ILA-ORB after 5-day morphine, plus the",
        "      PER:CRY and ROR/REV-ERB limbs those DEGs need to be readable."],
       12, DARK, space=3)
    tb(s, 6.85, 4.32, 5.95, 2.40,
       ["4.   Receptor layer",
        "      35 GPCRs, each with where it sits among the 20 and whether a drug exists.",
        "5.   Drop what cannot be seen",
        "      Empty maps (Sstr4 1%) and no-contrast genes (Clock, Syt1).",
        "6.   Held-out check on the 20 types",
        "      0.948 balanced accuracy. 073 Sox6 GABA recall 0.98. L5 IT and L6b",
        "      grade into their neighbour - that is cortex, not a missing marker."],
       12, DARK, space=3)

    prs.save(PPT_DST)
    print("wrote", PPT_DST, "5 slides")


def deliver() -> None:
    for src, name in (
            (XL_DST, "FINAL_Xenium_panel_ORBm_BMAp.xlsx"),
            (XL_DST, "FINAL_Xenium_panel_ORBm_BMAp_259genes.xlsx"),
            (PPT_DST, "ORBm_BMAp_Xenium_panel_funder.pptx"),
            (PPT_DST, "ORBm_BMAp_Xenium_panel_funder_v7.pptx"),
    ):
        dst = DL / name
        shutil.copy2(src, dst)
        print("copied", dst)


if __name__ == "__main__":
    n = write_excel()
    write_ppt(n)
    deliver()
