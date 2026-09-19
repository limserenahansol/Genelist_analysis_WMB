"""Final funder deck (5 slides, Option A / 119 custom) + a 2-slide scenario deck.

Fully editable: native PowerPoint shapes and native PowerPoint charts only, no
images, so every box, label and chart value can be changed in PowerPoint.

  FINAL_funder_deck_119custom.pptx      5 slides - the design we are presenting
  SCENARIOS_100_vs_245.pptx             1 slide per alternative:
                                          slide 1  cut to 100 custom - what is discarded
                                          slide 2  expand to 245 - what is added

Gabbr2 and Emx1 are confirmed cut in the 100-gene version. They remain in the
119-custom design, which is the complete one being presented.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
A = OUT / "PANEL_A_current_166genes_119custom.xlsx"
B = OUT / "PANEL_B_cut_147genes_100custom.xlsx"
Cx = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
LONG = OUT / "subclass_markers_expanded" / "Subclass_Discriminating_Markers_long.csv"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"
DECK_MAIN = OUT / "FINAL_funder_deck_119custom.pptx"
DECK_SCEN = OUT / "SCENARIOS_100_vs_245.pptx"

NAVY, TEAL, RUST, SAGE, GOLD = "1D4E89", "2A6F97", "C44536", "6B7C6A", "B08968"
GREY, CREAM, ICE, WH = "B8B2A8", "F4F1EA", "EAF2F8", "FFFFFF"
INK, MUTED = "1F2937", "5B6472"
CAP = 100

GROUPS = [
    ("Cell identity and region", ["1_celltype_separator", "3_class_backbone",
                                  "11_class_backbone_optional", "8_TF_identity",
                                  "9_published_regional", "12_GSE283418_added",
                                  "18_expanded_BMAp", "19_expanded_L5IT_separator"], NAVY),
    ("Druggable receptor map", ["6_GPCR_druggable", "4_GPCR_cell_type_specific",
                                "14_Jesse_ORB_GPCR", "17_expanded_ORB_GPCR"], TEAL),
    ("Activity and plasticity", ["5_IEG", "7_plasticity"], SAGE),
    ("Morphine-dependence state", ["13_Jesse_morphine_state", "16_expanded_morphine_state"], RUST),
    ("TRAP genetic tag", ["2_reporter_transgene"], GOLD),
]


def C(h):
    return RGBColor.from_string(h)


def tbox(s, x, y, w, h, body, size=13, bold=False, colour=INK, align=PP_ALIGN.LEFT,
         space=3, anchor=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    if anchor:
        tf.vertical_anchor = anchor
    for i, line in enumerate(str(body).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
        r.font.color.rgb = C(colour)
    return tb


def rrect(s, x, y, w, h, fill, line, lw=1.5, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = C(fill)
    if line:
        sp.line.color.rgb = C(line)
        sp.line.width = Pt(lw)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    sp.text_frame.word_wrap = True
    return sp


def inlabel(sp, text, size=13, bold=False, colour=INK):
    tf = sp.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
        r.font.color.rgb = C(colour)


def connect(s, x1, y1, x2, y2, colour, lw=1.5):
    cn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                Inches(x2), Inches(y2))
    cn.line.color.rgb = C(colour)
    cn.line.width = Pt(lw)


def tile(s, x, y, w, big, lab, col, h=1.10, bigsize=26):
    rrect(s, x, y, w, h, CREAM, col, 1.3)
    tbox(s, x + 0.08, y + 0.04, w - 0.16, 0.52, big, bigsize, True, col, PP_ALIGN.CENTER)
    tbox(s, x + 0.08, y + 0.56, w - 0.16, 0.50, lab, 10.5, False, MUTED, PP_ALIGN.CENTER, space=0)


def bars(s, x, y, w, h, cats, vals, cols, title, gap=60):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("genes", vals)
    ch = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y),
                            Inches(w), Inches(h), cd).chart
    ch.has_legend = False
    ch.font.size, ch.font.name = Pt(11), "Calibri"
    ch.has_title = True
    ch.chart_title.text_frame.text = title
    r = ch.chart_title.text_frame.paragraphs[0].runs[0]
    r.font.size, r.font.bold, r.font.name = Pt(12), True, "Calibri"
    r.font.color.rgb = C(NAVY)
    pl = ch.plots[0]
    pl.gap_width = gap
    pl.has_data_labels = True
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    pl.data_labels.font.size, pl.data_labels.font.bold = Pt(11), True
    pl.data_labels.font.name = "Calibri"
    for i, col in enumerate(cols):
        pt = pl.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = C(col)
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    ch.category_axis.has_major_gridlines = False
    ch.category_axis.format.line.color.rgb = C(GREY)


def slide(prs, title, sub, footer, tcol=NAVY):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rrect(s, 0, 0, 13.333, 0.12, NAVY, None, shape=MSO_SHAPE.RECTANGLE)
    tbox(s, 0.40, 0.18, 12.5, 0.44, title, 23, True, tcol)
    if sub:
        tbox(s, 0.40, 0.60, 12.5, 0.36, sub, 13, False, MUTED)
    tbox(s, 0.40, 7.16, 12.5, 0.26, footer, 10.5, False, MUTED)
    return s


def facts(path: Path) -> dict:
    sh = pd.read_excel(path, "SHARED_PANEL_ORDER")
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    sh["free"] = sh.gene.isin(base)
    ac = pd.read_excel(path, "ANCHOR_COVERAGE")
    ac["n_sep"] = ac.unique_separators_on_shared_panel.fillna("").apply(
        lambda s: len([x for x in s.split(",") if x.strip()]))
    comp = pd.DataFrame([{"group": n, "n": len(sh[sh.block.isin(b)]), "colour": c}
                         for n, b, c in GROUPS])
    assert comp.n.sum() == len(sh), f"{path.name}: {comp.n.sum()} of {len(sh)}"

    def bucket(b):
        if b.startswith(("12_", "18_")):
            return "dan"
        if b.startswith(("13_", "14_", "16_", "17_")):
            return "jesse"
        return "core"

    sh["src"] = sh.block.apply(bucket)
    long = pd.read_csv(LONG)
    return dict(sh=sh, ac=ac, comp=comp, n=len(sh), free=int(sh.free.sum()),
                custom=int((~sh.free).sum()), yld=sh.groupby("src").size(),
                n_sub=long.subclass.nunique(), n_measure=len(long),
                n_pairs=len(pd.read_csv(PAIRS)),
                n_sources=len(pd.read_excel(path, "SOURCES")))


def schematic(s, F):
    tbox(s, 0.42, 1.06, 3.4, 0.26, "WHERE THE CANDIDATES CAME FROM", 9.5, True, NAVY)
    tbox(s, 4.90, 1.06, 4.5, 0.26, "FOUR DECISION RULES", 9.5, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.72, 1.06, 3.2, 0.26, "WHAT WE ORDER", 9.5, True, NAVY, PP_ALIGN.CENTER)
    y_ = F["yld"]
    srcs = [("OUR MARKER SCREEN", f"Allen atlas + {F['n_sources']} documented sources",
             "311 screened", int(y_.get("core", 0)), NAVY),
            ("JESSE NIEHAUS", "Morphine-dependence expression\nin orbitofrontal cortex",
             "431 screened", int(y_.get("jesse", 0)), RUST),
            ("BERG & SCHERRER", "Published amygdala spatial panel\n(GSE283418)",
             "98 screened", int(y_.get("dan", 0)), TEAL)]
    SY, SH_, SG = 1.40, 1.40, 0.18
    for i, (t, b, scr, kep, col) in enumerate(srcs):
        y = SY + i * (SH_ + SG)
        rrect(s, 0.42, y, 3.28, SH_, CREAM, col, 1.5)
        inlabel(rrect(s, 0.42, y, 3.28, 0.34, col, None, shape=MSO_SHAPE.RECTANGLE), t, 11, True, WH)
        tbox(s, 0.56, y + 0.40, 3.00, 0.62, b, 9.5, False, INK, space=1)
        tbox(s, 0.56, y + SH_ - 0.30, 1.6, 0.24, scr, 9.5, True, col)
        connect(s, 3.70, y + SH_ / 2, 9.70, 3.52, col)
        tbox(s, 3.80, y + SH_ / 2 - 0.30, 1.0, 0.24, f"{kep} kept", 10, True, col)
    for i, (n, q, col) in enumerate([
            ("1", "Does it identify the cell type?", NAVY),
            ("2", "Is it a druggable receptor we cannot already see?", TEAL),
            ("3", "Does it report the morphine-dependent state?", RUST),
            ("4", "Will the instrument actually detect it?", SAGE)]):
        y = 1.40 + i * 0.98
        rrect(s, 4.90, y, 4.52, 0.84, WH, col, 1.4)
        inlabel(rrect(s, 5.02, y + 0.27, 0.30, 0.30, col, None, shape=MSO_SHAPE.OVAL), n, 11.5, True, WH)
        tbox(s, 5.42, y + 0.08, 3.86, 0.68, q, 11, True, col, space=0, anchor=MSO_ANCHOR.MIDDLE)
    rrect(s, 4.90, 5.34, 4.52, 0.94, ICE, NAVY, 1.3)
    tbox(s, 5.00, 5.42, 4.32, 0.24, "Every rule measured in the Allen atlas",
         10.5, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 5.00, 5.68, 4.32, 0.54,
         f"226,886 cells  ·  {F['n_sub']} subclasses\n"
         f"{F['n_measure']:,} measurements  ·  {F['n_pairs']:,} pairwise tests",
         9.5, False, INK, PP_ALIGN.CENTER, space=0)
    rrect(s, 9.70, 1.40, 3.22, 4.88, ICE, NAVY, 2.1)
    tbox(s, 9.80, 1.50, 3.02, 0.26, "FINAL PANEL", 11, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.80, 1.80, 3.02, 0.80, str(F["n"]), 42, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.80, 2.58, 3.02, 0.24, "genes on one section", 10, False, MUTED, PP_ALIGN.CENTER)
    connect(s, 9.88, 2.96, 12.74, 2.96, GREY, 1.0)
    tbox(s, 9.80, 3.04, 3.02, 0.90,
         f"{int(y_.get('core',0))} our marker screen\n{int(y_.get('dan',0))} Berg & Scherrer\n"
         f"{int(y_.get('jesse',0))} Jesse Niehaus", 10.5, False, INK, PP_ALIGN.CENTER, space=1)
    connect(s, 9.88, 4.08, 12.74, 4.08, GREY, 1.0)
    tbox(s, 9.80, 4.16, 3.02, 0.72,
         f"{F['free']} free on the base panel\n{F['custom']} custom probes",
         10.5, True, NAVY, PP_ALIGN.CENTER, space=1)
    connect(s, 9.88, 5.02, 12.74, 5.02, GREY, 1.0)
    tbox(s, 9.80, 5.10, 3.02, 1.02, "2 brain regions\n20 cell populations\n1 section, 1 animal",
         10.5, True, NAVY, PP_ALIGN.CENTER, space=1)
    rrect(s, 0.42, 5.34, 4.10, 0.94, "F7F5F2", GREY, 1.0)
    tbox(s, 0.52, 5.42, 3.90, 0.24, f"701 candidates  ->  {F['n']} selected",
         10.5, True, INK, PP_ALIGN.CENTER)
    tbox(s, 0.52, 5.68, 3.90, 0.54,
         "Each keeps its evidence and the rule\nthat admitted it.", 9.5, False, MUTED,
         PP_ALIGN.CENTER, space=0)


def rules_slide(s):
    for i, (n, h, m, k, d, col) in enumerate([
            ("1", "Does it identify the cell type?",
             "Specificity against genes the panel already carries; must beat them",
             "Col23a1   3.7x more specific than any equal marker",
             "Sfrp1   0.9x - a panel gene already does it better", NAVY),
            ("2", "Is it a druggable receptor we cannot see?",
             "Regional enrichment, plus whether the family is already covered",
             "Chrm1   M1 receptor - we could only see M2 before",
             "Gpr26   orphan receptor, no known ligand", TEAL),
            ("3", "Does it report the morphine-dependent state?",
             "Differential expression counted only in our 12 ORBm populations",
             "Per2   changes in 11 of 12 populations",
             "Nr4a3   8 clusters overall, but only 5 of ours", RUST),
            ("4", "Will the instrument actually detect it?",
             "Fraction of cells expressing it; sparse probes give unusable maps",
             "Grm8   99% of cells, >50% in 8 of 12 populations",
             "Mas1   most enriched of all, but only 45% of cells", SAGE)]):
        x, y = 0.42 + (i % 2) * 6.30, 1.10 + (i // 2) * 1.72
        rrect(s, x, y, 6.16, 1.60, WH, col, 1.4)
        inlabel(rrect(s, x + 0.14, y + 0.12, 0.30, 0.30, col, None, shape=MSO_SHAPE.OVAL),
                n, 11.5, True, WH)
        tbox(s, x + 0.52, y + 0.09, 5.52, 0.30, h, 12.5, True, col, space=0)
        tbox(s, x + 0.16, y + 0.46, 5.86, 0.30, m, 10, False, MUTED, space=0)
        tbox(s, x + 0.16, y + 0.83, 5.86, 0.30, "IN     " + k, 10, False, SAGE, space=0)
        tbox(s, x + 0.16, y + 1.18, 5.86, 0.30, "OUT   " + d, 10, False, RUST, space=0)


def build_main(F) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    FT = f"ORBm + BMAp Xenium panel  ·  {F['n']} genes, {F['custom']} custom  |  "

    s = slide(prs, "How the gene panel was selected",
              "Every probe slot has to be earned. Four rules decided which genes earned one.",
              FT + "1/5")
    schematic(s, F)

    s = slide(prs, "Why a gene is in - and why a similar one is out",
              "Each rule is a measurement with a cutoff, so any gene's inclusion can be re-checked.",
              FT + "2/5", RUST)
    rules_slide(s)
    rrect(s, 0.42, 4.66, 12.50, 2.22, ICE, NAVY, 1.2)
    tbox(s, 0.62, 4.78, 12.1, 0.28, "The constraint that forces all of this", 13.5, True, NAVY)
    tbox(s, 0.62, 5.12, 5.95, 1.64,
         "The standard 10x Mouse Brain panel gives 248 genes at no extra cost, and the custom add-on is "
         f"capped at 100 genes by design.\n\nSo {F['n']} justified genes means {F['free']} taken free and "
         f"{F['custom']} custom - and roughly three of every four candidates screened were turned down.",
         11, False, INK, space=2)
    tbox(s, 6.90, 5.12, 5.95, 1.64,
         "The four rules are independent, and that is deliberate.\n\nA receptor earns its slot by showing "
         "where a drug target sits, whether or not morphine changes it. One panel therefore serves the "
         "pharmacology aim and the addiction aim at once, instead of forcing a choice.",
         11, False, INK, space=2)

    s = slide(prs, f"The panel  -  {F['n']} genes, one section, two regions",
              "One shared panel read from the same mouse. All 20 target populations remain separable.",
              FT + "3/5", TEAL)
    for i, (big, lab, col) in enumerate([
            (str(F["n"]), "genes on the\nshared panel", NAVY),
            ("20 / 20", "cell populations\nstill separable", TEAL),
            (str(F["free"]), "free on the 10x\nbase panel", SAGE),
            ("12 + 8", "populations in\nORBm  +  BMAp", RUST)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col)
    c = F["comp"]
    bars(s, 0.30, 2.38, 7.05, 3.90, list(c.group), [int(v) for v in c.n], list(c.colour),
         f"What the {F['n']} genes do")
    tbox(s, 7.62, 2.40, 5.30, 0.28, "What each cell will tell us", 14, True, NAVY)
    for i, (h, b, col) in enumerate([
            ("Identity", "Which of the 20 populations it is - layer, interneuron class, "
                         "amygdala subtype", NAVY),
            ("Activity", "Whether it was recently active - Fos and Arc, plus the TRAP2 tag", TEAL),
            ("State", "Whether it carries the morphine-dependence signature", RUST),
            ("Receptors", "Which druggable receptors sit on it - opioid, muscarinic, "
                          "glutamate, relaxin", SAGE)]):
        y = 2.82 + i * 0.92
        tbox(s, 7.62, y, 5.30, 0.26, h, 12.5, True, col, space=0)
        tbox(s, 7.62, y + 0.26, 5.30, 0.60, b, 10.5, False, INK, space=0)
    tbox(s, 7.62, 6.54, 5.30, 0.34,
         "The State row is the new capability this panel adds.", 11, True, RUST)

    s = slide(prs, "The 20 populations we must tell apart",
              "Target list from the Allen Brain Cell Atlas taxonomy: 12 in ORBm, 8 in BMAp.",
              FT + "4/5")
    ac = F["ac"]
    for i, (big, lab, col) in enumerate([
            ("12", "ORBm populations\n83,406 Allen cells", NAVY),
            ("8", "BMAp populations\n40,709 Allen cells", TEAL),
            (f"{ac.n_cells.sum():,}", "cells in the 20\ntarget populations", SAGE),
            ("20 / 20", "have a dedicated\nmarker on the panel", RUST)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col)
    for reg, col, x in (("ORBm", NAVY, 0.30), ("BMAp", TEAL, 6.75)):
        g = ac[ac.region == reg]
        bars(s, x, 2.38, 6.30, 4.30,
             [r.allen_subclass_anchor.split(" ", 1)[1] for r in g.itertuples()],
             [int(r.n_cells) for r in g.itertuples()], [col] * len(g),
             f"{reg}  -  {len(g)} populations, {g.n_cells.sum():,} cells", gap=45)
    tbox(s, 0.42, 6.74, 12.5, 0.34,
         "Marker counts in the workbook are genes EXCLUSIVE to one population - the strictest test. "
         "Identification is combinatorial: L5 IT has 1 exclusive gene yet is separable from 9 of its 11 "
         "neighbours using panel genes.", 10.5, False, MUTED)

    s = slide(prs, "The list rests on a full re-analysis of the reference atlas",
              "No gene was taken on a paper's word; every candidate was re-scored in these two regions.",
              FT + "5/5", TEAL)
    for i, (big, lab, col) in enumerate([
            ("226,886", "single cells scored across\nthe two target regions", NAVY),
            (f"{F['n_sub']}", "cell subclasses profiled,\nnot only the 20 targets", TEAL),
            (f"{F['n_measure']:,}", "abundance and specificity\nmeasurements", SAGE),
            (f"{F['n_pairs']:,}", "pairwise tests: can gene X\nseparate type A from B?", RUST)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col)
    rrect(s, 0.42, 2.40, 12.50, 4.42, CREAM, GREY, 1.0)
    tbox(s, 0.64, 2.54, 12.1, 0.30, "What that analysis produced, in order", 14, True, NAVY)
    for i, (h, b) in enumerate([
            ("1.  Region-restricted expression matrices",
             "ORBm and BMAp cells were pulled out of the whole-brain atlas, so every abundance and "
             "specificity number describes these two regions - not a brain-wide average."),
            ("2.  Per-population marker ranking",
             "For each of the 20 targets, every candidate was ranked by how much of that population "
             "expresses it and how tightly it is restricted to it."),
            ("3.  Pairwise separability testing",
             f"{F['n_pairs']:,} tests confirmed that neighbouring populations - L5 IT vs L5 ET, MEA vs "
             f"BMA - stay distinguishable using only the genes actually on the panel."),
            ("4.  Receptor and drug-target layer",
             f"Receptors were tiered by specificity and cross-referenced to the IUPHAR pharmacology "
             f"database, so the map covers targets that drugs already exist for. {F['n_sources']} "
             f"sources are documented.")]):
        y = 2.98 + i * 0.95
        tbox(s, 0.64, y, 12.1, 0.28, h, 12.5, True, NAVY, space=0)
        tbox(s, 0.92, y + 0.28, 11.8, 0.56, b, 11, False, INK, space=0)

    prs.save(DECK_MAIN)
    return DECK_MAIN


def build_scenarios(FA, FB, FC) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # ---- slide 1: cut to 100
    s = slide(prs, f"Alternative 1  -  cut to the {CAP}-gene custom cap",
              f"If 10x will not go above the {CAP}-gene add-on limit, {FA['custom'] - CAP} genes come off. "
              f"Nothing that identifies a cell population is touched.",
              "SCENARIO  ·  what is discarded  |  1/2", RUST)
    for i, (big, lab, col) in enumerate([
            (f"{FA['n']} -> {FB['n']}", "genes on the\nshared panel", NAVY),
            (f"{FA['custom']} -> {FB['custom']}", "custom probes\n(now at the cap)", SAGE),
            (f"-{FA['custom'] - CAP}", "genes discarded", RUST),
            ("20 / 20", "populations still\nseparable", TEAL)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col, bigsize=22)
    cut = pd.read_excel(B, "CUT_LIST")
    LEFT = [("Dan: fails its own rule", TEAL), ("Jesse: weakest of its set", RUST),
            ("Finer distinction already covered", GOLD)]
    RIGHT = [("Too sparse to map", SAGE), ("Redundant within family", GOLD)]
    SHORT = {
        "Dnah5": "BMAp specificity 0.53", "Nos1": "specificity 0.76, in 99.7% of cells",
        "Gabre": "0.95, peaks in CEA not BMAp", "Tspan18": "0.96, peaks in SI/LPO border",
        "Syndig1l": "1.32, peaks in CEA not BMAp",
        "Gpr26": "orphan receptor, no known ligand", "Per1": "same clock axis as Per2, 63% of cells",
        "Cx3cr1": "15% of cells, microglia not a target", "Hcrtr1": "16% of cells",
        "Ackr3": "21% of cells", "Htr1a": "28%, Htr1b and Htr2a cover it",
        "Tacr3": "30%, Tacr1 stays", "Galr1": "36% of cells",
        "Grin2b": "3rd NMDA subunit, Grin1 and Grin2a stay",
        "Gria2": "2nd AMPA subunit, Gria1 stays", "Rbfox3": "Snap25 gives the pan-neuronal call",
        "Gabbr2": "GABA-B partner, Gabbr1 binds baclofen", "Fosb": "34%, five IEGs already on panel",
        "Emx1": "41%, Tbr1/Satb2 and Dlx1/Isl1 cover the axis",
    }
    HEAD, ROW, GAP, TOP = 0.32, 0.25, 0.12, 2.40
    for x, column in ((0.42, LEFT), (6.72, RIGHT)):
        y = TOP
        for grp, col in column:
            items = cut[cut.cut_group == grp]
            if not len(items):
                continue
            h = HEAD + ROW * len(items) + 0.10
            rrect(s, x, y, 6.18, h, WH, col, 1.4)
            tbox(s, x + 0.14, y + 0.04, 5.90, 0.24,
                 f"{grp}   ({len(items)})", 11, True, col, space=0)
            for k, g in enumerate(items.gene):
                tbox(s, x + 0.20, y + HEAD + k * ROW, 5.84, 0.23,
                     f"{g}   -   {SHORT.get(g, '')}", 9.5, False, INK, space=0)
            y += h + GAP
        assert y <= 6.60, f"column overflow {y:.2f}"
    rrect(s, 0.42, 6.06, 12.50, 0.82, ICE, NAVY, 1.2)
    tbox(s, 0.62, 6.14, 12.1, 0.66,
         "What survives: all 54 custom cell-population separators, the morphine layer "
         "(Per2 11 of 12 populations, Pcsk1 9 of 12, Camk2g as the only DOWN gene), and the two "
         "receptor-family gaps we closed (Chrm1, Grm8). Cost is unchanged - this fits the existing quote.",
         11, False, INK, space=2)

    # ---- slide 2: expand to 245
    s = slide(prs, f"Alternative 2  -  expand to {FC['n']} genes",
              "If a standalone custom panel is affordable, every candidate with a documented basis "
              "comes back in. No cap applies, but there is no free base panel either.",
              "SCENARIO  ·  what is added  |  2/2", TEAL)
    for i, (big, lab, col) in enumerate([
            (f"{FA['n']} -> {FC['n']}", "genes on the\npanel", NAVY),
            (f"+{FC['n'] - FA['n']}", "genes added back", TEAL),
            ("no cap", "standalone custom\nreplaces the add-on", SAGE),
            ("all designed", f"no free base panel:\nall {FC['n']} are probes", RUST)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col, bigsize=22)
    add = pd.read_excel(Cx, "EXPANSION_LIST")
    cats = [("16_expanded_morphine_state", "Broader morphine-dependence genes", RUST,
             "DE in 4 or more of our 12 ORBm populations. Includes Arid5b (8 of 12, the only broad "
             "gene besides Per2 that reaches interneurons) and Vps13a (7 of 12 at 95% detection)."),
            ("17_expanded_ORB_GPCR", "More ORB-enriched receptors", TEAL,
             "Enriched in 8 or more PL-ILA-ORB subclasses. Includes Chrm3 (11 subclasses, wider than "
             "Chrm1), Mas1, Mchr1, Adra1a, Hrh3. Detectability is unscored for several of these."),
            ("18_expanded_BMAp", "Berg & Scherrer genes below the cutoff", SAGE,
             "Specificity 0.4 to 1.0 - they do not beat an existing panel gene, but they add BMAp "
             "depth when slots are not scarce. Includes Sfrp1, Glipr1, Vdr, Mgp."),
            ("19_expanded_L5IT_separator", "Extra L5 IT separators", GOLD,
             "L5 IT has only one exclusive gene (Bdnf). These close the two remaining gaps against the "
             "adjacent IT layers: Sema5a covers both, Rai14 gives the widest margin.")]
    for i, (blk, head, col, body) in enumerate(cats):
        n = int((add.block == blk).sum())
        x, y = 0.42 + (i % 2) * 6.30, 2.40 + (i // 2) * 1.62
        rrect(s, x, y, 6.16, 1.50, WH, col, 1.4)
        inlabel(rrect(s, x + 0.14, y + 0.14, 0.62, 0.34, col, None), f"+{n}", 13, True, WH)
        tbox(s, x + 0.86, y + 0.14, 5.16, 0.32, head, 12.5, True, col, space=0)
        tbox(s, x + 0.16, y + 0.56, 5.86, 0.86, body, 10, False, INK, space=0)
    rrect(s, 0.42, 5.72, 12.50, 1.16, CREAM, GREY, 1.2)
    tbox(s, 0.62, 5.80, 12.1, 0.26, "The trade", 12.5, True, NAVY)
    tbox(s, 0.62, 6.08, 12.1, 0.76,
         "A standalone custom panel has no 100-gene cap, but it replaces the pre-designed panel, so the "
         f"{FA['free']} genes we currently get free become paid probes. 245 genes sits in a band above "
         "101; the 301-480 band (part 1000647) lists near $21,000 for 4 reactions, which is more panel "
         "than we need - the 101-300 band is the number to ask the rep for. Several additions also have "
         "unscored detectability, so some maps will be sparse.", 11, False, INK, space=2)

    prs.save(DECK_SCEN)
    return DECK_SCEN


def main() -> None:
    FA, FB, FC = facts(A), facts(B), facts(Cx)
    for lab, F in (("A", FA), ("B", FB), ("C", FC)):
        print(f"  {lab}: {F['n']:3d} genes, {F['free']} free + {F['custom']} custom")
    for p in (build_main(FA), build_scenarios(FA, FB, FC)):
        prs = Presentation(p)
        pics = sum(1 for s in prs.slides for sh in s.shapes if sh.shape_type == 13)
        bad = [i for i, s in enumerate(prs.slides, 1)
               if max((sh.top + sh.height) / 914400 for sh in s.shapes if sh.height) > 7.45
               or max((sh.left + sh.width) / 914400 for sh in s.shapes if sh.height) > 13.34]
        print(f"{p.name}: slides={len(prs.slides._sldIdLst)} pictures={pics} "
              f"off-slide={bad or 'none'} {'OK' if pics == 0 and not bad else 'FAIL'}")
        assert pics == 0 and not bad


if __name__ == "__main__":
    main()
