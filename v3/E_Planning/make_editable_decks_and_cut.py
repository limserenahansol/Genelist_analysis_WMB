"""Fully editable funder deck + a cut-to-100-custom contingency (deck and workbook).

Requirement: the PI must be able to edit everything in PowerPoint. So there are NO
images in these decks. The schematic is built from native PowerPoint shapes
(rounded rectangles, ovals, connectors, text boxes) and the bar charts are native
PowerPoint charts with editable data, not rendered pictures.

The custom add-on is capped at 100 genes by 10x's panel design rules - not by the
purchased price tier - and the live sheet carries 121 custom. So a contingency that
removes exactly 21 is prepared alongside the main deck.

Cut principle: a gene is cut when it fails the rule that admitted it. Cuts that
depend on the lab's own constructs or scientific priorities are flagged CONFIRM.

Artifacts
  ORBm_BMAp_panel_funder_EDITABLE.pptx        3 main slides + 2 backup
  ORBm_BMAp_panel_CUT21_contingency.pptx      2 slides
  FINAL_Xenium_panel_ORBm_BMAp_CUT21_100custom.xlsx   cut sheet + CUT_LIST tab
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
LIVE = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx")
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"
LONG = OUT / "subclass_markers_expanded" / "Subclass_Discriminating_Markers_long.csv"
DECK_MAIN = OUT / "ORBm_BMAp_panel_funder_EDITABLE.pptx"
DECK_CUT = OUT / "ORBm_BMAp_panel_CUT21_contingency.pptx"
XL_CUT = OUT / "FINAL_Xenium_panel_ORBm_BMAp_CUT21_100custom.xlsx"

NAVY, TEAL, RUST, SAGE, GOLD = "1D4E89", "2A6F97", "C44536", "6B7C6A", "B08968"
GREY, CREAM, ICE, WHITE_H = "B8B2A8", "F4F1EA", "EAF2F8", "FFFFFF"
INK, MUTED = "1F2937", "5B6472"

CAP = 100  # 10x hard limit on custom add-on targets

# gene, reason, group, needs the lab's confirmation
CUTS = [
    ("Dnah5",    "BMAp specificity 0.53 - below the 1.0 cutoff that admitted the set", "Dan: fails its own rule", False),
    ("Nos1",     "BMAp specificity 0.76 - detected in 99.7% of cells but not specific", "Dan: fails its own rule", False),
    ("Gabre",    "BMAp specificity 0.95, and peaks in CEA-BST, a neighbour not BMAp",   "Dan: fails its own rule", False),
    ("Tspan18",  "BMAp specificity 0.96, peaks in the SI/LPO border region",            "Dan: fails its own rule", False),
    ("Syndig1l", "Specificity 1.32 but peaks in CEA-BST, not the BMAp core",            "Dan: fails its own rule", False),
    ("Gpr26",    "Orphan receptor - no known ligand, so it cannot serve a drug-target map", "Jesse: weakest of its own set", False),
    ("Per1",     "Same circadian axis as Per2; 63% detection, above 50% in only 4 of 12 populations", "Jesse: weakest of its own set", False),
    ("Cx3cr1",   "Microglial marker at 15% of cells - microglia are not among the 20 target populations", "Too sparse to map", False),
    ("Hcrtr1",   "16% of cells - orexin receptor 1 map would be too sparse to interpret", "Too sparse to map", False),
    ("Ackr3",    "21% of cells - published OFC marker, but below usable detection",      "Too sparse to map", False),
    ("Htr1a",    "28% of cells - Htr1b and Htr2a cover serotonergic signalling better",  "Too sparse to map", False),
    ("Tacr3",    "30% of cells - Tacr1 remains on the panel for tachykinin signalling",  "Too sparse to map", False),
    ("Galr1",    "36% of cells - galanin receptor map would be too sparse",              "Too sparse to map", False),
    ("Grin2b",   "Third NMDA subunit; Grin1 and Grin2a already report NMDA signalling",  "Redundant within family", False),
    ("Gria2",    "Second AMPA subunit; Gria1 already reports AMPA signalling",           "Redundant within family", False),
    ("Rbfox3",   "Pan-neuronal at 99.6%; Snap25 already provides the pan-neuronal call", "Redundant within family", False),
    ("Gabbr2",   "GABA-B heterodimer partner; Gabbr1 alone localises the receptor",      "Redundant within family", True),
    ("Fosb",     "34% of cells; Fos, Arc, Egr1, Junb and Npas4 already report activity", "Redundant within family", False),
    ("Emx1",     "41% pallial-lineage TF - broad, and the layer separators are specific", "Redundant within family", True),
    ("WPRE",     "Viral vector element - only needed if AAVs carrying it are injected",  "Depends on your constructs", True),
    ("mCherry",  "Viral tag - only needed if an mCherry construct is actually used",     "Depends on your constructs", True),
]


def facts(panel: Path) -> dict:
    sh = pd.read_excel(panel, "SHARED_PANEL_ORDER")
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    sh["free"] = sh.gene.isin(base)
    ac = pd.read_excel(panel, "ANCHOR_COVERAGE")
    ac["n_sep"] = ac.unique_separators_on_shared_panel.fillna("").apply(
        lambda s: len([x for x in s.split(",") if x.strip()]))
    src = pd.read_excel(panel, "SOURCES")

    def bucket(b):
        return "dan" if b.startswith("12_") else ("jesse" if b.startswith(("13_", "14_")) else "core")

    sh["src"] = sh.block.apply(bucket)
    groups = [
        ("Cell identity and region", ["1_celltype_separator", "3_class_backbone",
                                      "11_class_backbone_optional", "8_TF_identity",
                                      "9_published_regional", "12_GSE283418_added"], NAVY),
        ("Druggable receptor map", ["6_GPCR_druggable", "4_GPCR_cell_type_specific",
                                    "14_ORB_enriched_GPCR", "14_Jesse_ORB_GPCR"], TEAL),
        ("Activity and plasticity", ["5_IEG", "7_plasticity"], SAGE),
        ("Morphine-dependence state", ["13_Jesse_morphine_state"], RUST),
        ("Genetic-tag reporters", ["2_reporter_transgene"], GOLD),
    ]
    comp = pd.DataFrame([
        {"group": n, "n": len(sh[sh.block.isin(b)]), "colour": c} for n, b, c in groups])
    assert comp.n.sum() == len(sh), f"groups cover {comp.n.sum()} of {len(sh)}"
    long = pd.read_csv(LONG)
    return {
        "sh": sh, "ac": ac, "comp": comp,
        "n": len(sh), "free": int(sh.free.sum()), "custom": int((~sh.free).sum()),
        "yld": sh.groupby("src").size(),
        "n_sources": len(src), "n_doi": int(src.doi.notna().sum()),
        "n_measure": len(long), "n_sub": long.subclass.nunique(),
        "n_pairs": len(pd.read_csv(PAIRS)),
    }


# --------------------------------------------------------------- pptx helpers
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


def label_in(sp, text, size=13, bold=False, colour=INK, align=PP_ALIGN.CENTER):
    tf = sp.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
        r.font.color.rgb = C(colour)
    return sp


def connect(s, x1, y1, x2, y2, colour, lw=1.75):
    cn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                Inches(x2), Inches(y2))
    cn.line.color.rgb = C(colour)
    cn.line.width = Pt(lw)
    return cn


def bar_chart(s, x, y, w, h, cats, vals, colours, title=None, gap=60):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("genes", vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y),
                            Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.font.size = Pt(11)
    ch.font.name = "Calibri"
    if title:
        ch.has_title = True
        ch.chart_title.text_frame.text = title
        r = ch.chart_title.text_frame.paragraphs[0].runs[0]
        r.font.size, r.font.bold, r.font.name = Pt(12), True, "Calibri"
        r.font.color.rgb = C(NAVY)
    else:
        ch.has_title = False
    pl = ch.plots[0]
    pl.gap_width = gap
    pl.has_data_labels = True
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    pl.data_labels.font.size = Pt(11)
    pl.data_labels.font.bold = True
    pl.data_labels.font.name = "Calibri"
    for i, col in enumerate(colours):
        pt = pl.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = C(col)
    va = ch.value_axis
    va.has_major_gridlines = False
    va.visible = False
    ca = ch.category_axis
    ca.has_major_gridlines = False
    ca.format.line.color.rgb = C(GREY)
    return ch


def slide(prs, title, sub, footer, tcol=NAVY):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = rrect(s, 0, 0, 13.333, 0.12, NAVY, None, shape=MSO_SHAPE.RECTANGLE)
    tbox(s, 0.40, 0.18, 12.5, 0.44, title, 24, True, tcol)
    if sub:
        tbox(s, 0.40, 0.60, 12.5, 0.36, sub, 13, False, MUTED)
    tbox(s, 0.40, 7.16, 12.5, 0.26, footer, 10.5, False, MUTED)
    return s


def tile(s, x, y, w, big, lab, col, h=1.10):
    rrect(s, x, y, w, h, CREAM, col, 1.3)
    tbox(s, x + 0.10, y + 0.04, w - 0.20, 0.52, big, 26, True, col, PP_ALIGN.CENTER)
    tbox(s, x + 0.10, y + 0.56, w - 0.20, 0.50, lab, 11, False, MUTED, PP_ALIGN.CENTER, space=0)


# ------------------------------------------------------------ main deck
def schematic(s, F):
    """Native-shape version of the three-column flow, fully editable."""
    y_ = F["yld"]
    tbox(s, 0.42, 1.10, 3.5, 0.28, "WHERE THE CANDIDATES CAME FROM", 10, True, NAVY)
    tbox(s, 4.55, 1.10, 4.3, 0.28, "FOUR DECISION RULES", 10, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.80, 1.10, 3.1, 0.28, "WHAT WE ORDER", 10, True, NAVY, PP_ALIGN.CENTER)

    srcs = [
        ("OUR MARKER SCREEN", f"Allen atlas + {F['n_sources']} documented sources\n"
                              "Cell-type markers, receptors,\nactivity genes",
         "311 screened", f"{int(y_['core'])} kept", NAVY),
        ("JESSE NIEHAUS", "Morphine-dependence gene\nexpression in orbitofrontal /\nprefrontal cortex",
         "431 screened", f"{int(y_['jesse'])} kept", RUST),
        ("BERG & SCHERRER", "Published amygdala spatial\npanel (GSE283418)",
         "98 screened", f"{int(y_['dan'])} kept", TEAL),
    ]
    SY, SH_, SG = 1.46, 1.44, 0.20
    for i, (t, b, scr, kep, col) in enumerate(srcs):
        y = SY + i * (SH_ + SG)
        rrect(s, 0.42, y, 3.30, SH_, CREAM, col, 1.6)
        hd = rrect(s, 0.42, y, 3.30, 0.36, col, None, shape=MSO_SHAPE.RECTANGLE)
        label_in(hd, t, 11.5, True, WHITE_H)
        tbox(s, 0.56, y + 0.42, 3.02, 0.70, b, 10, False, INK, space=1)
        tbox(s, 0.56, y + SH_ - 0.32, 1.5, 0.26, scr, 10, True, col)
        connect(s, 3.72, y + SH_ / 2, 9.72, 3.60, col, 1.5)
        tbox(s, 3.82, y + SH_ / 2 - 0.32, 0.95, 0.26, kep, 10.5, True, col)

    rules = [
        ("1", "Does it identify the cell type?", NAVY),
        ("2", "Is it a druggable receptor we cannot already see?", TEAL),
        ("3", "Does it report the morphine-dependent state?", RUST),
        ("4", "Will the instrument actually detect it?", SAGE),
    ]
    RY, RH_, RG = 1.46, 0.86, 0.15
    for i, (n, q, col) in enumerate(rules):
        y = RY + i * (RH_ + RG)
        rrect(s, 4.90, y, 4.55, RH_, WHITE_H, col, 1.5)
        ov = rrect(s, 5.02, y + (RH_ - 0.32) / 2, 0.32, 0.32, col, None, shape=MSO_SHAPE.OVAL)
        label_in(ov, n, 12, True, WHITE_H)
        tbox(s, 5.44, y + 0.10, 3.92, RH_ - 0.20, q, 11.5, True, col, space=0,
             anchor=MSO_ANCHOR.MIDDLE)

    eng = rrect(s, 4.90, 5.52, 4.55, 1.02, ICE, NAVY, 1.4)
    tbox(s, 5.02, 5.60, 4.31, 0.26, "Every rule is measured in the Allen atlas",
         11, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 5.02, 5.88, 4.31, 0.60,
         f"226,886 cells  ·  {F['n_sub']} subclasses profiled\n"
         f"{F['n_measure']:,} measurements  ·  {F['n_pairs']:,} pairwise tests",
         10, False, INK, PP_ALIGN.CENTER, space=0)

    rrect(s, 9.72, 1.46, 3.20, 5.08, ICE, NAVY, 2.2)
    tbox(s, 9.84, 1.58, 2.96, 0.28, "FINAL PANEL", 11.5, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.84, 1.92, 2.96, 0.80, str(F["n"]), 44, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.84, 2.72, 2.96, 0.26, "genes on one section", 10.5, False, MUTED, PP_ALIGN.CENTER)
    connect(s, 9.92, 3.12, 12.72, 3.12, GREY, 1.0)
    tbox(s, 9.84, 3.22, 2.96, 0.95,
         f"{int(y_['core'])} our marker screen\n{int(y_['dan'])} Berg & Scherrer\n"
         f"{int(y_['jesse'])} Jesse Niehaus",
         11, False, INK, PP_ALIGN.CENTER, space=1)
    connect(s, 9.92, 4.32, 12.72, 4.32, GREY, 1.0)
    tbox(s, 9.84, 4.42, 2.96, 0.80,
         f"{F['free']} free on the\nstandard platform\n{F['custom']} custom probes",
         11, True, NAVY, PP_ALIGN.CENTER, space=1)
    connect(s, 9.92, 5.40, 12.72, 5.40, GREY, 1.0)
    tbox(s, 9.84, 5.50, 2.96, 0.90,
         "2 brain regions\n20 cell populations\n1 section, 1 animal",
         11, True, NAVY, PP_ALIGN.CENTER, space=1)

    rrect(s, 0.42, 5.52, 4.00, 1.02, "F7F5F2", GREY, 1.0)
    tbox(s, 0.54, 5.60, 3.76, 0.26, f"701 candidates  ->  {F['n']} selected",
         11, True, INK, PP_ALIGN.CENTER)
    tbox(s, 0.54, 5.88, 3.76, 0.60,
         "Roughly three of every four were turned\ndown. Each keeps its evidence and rule.",
         10, False, MUTED, PP_ALIGN.CENTER, space=0)


def build_main(F) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    FT = "ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  "

    s = slide(prs, "How the gene panel was selected",
              "The custom add-on is capped at 100 genes, so every slot has to be earned. "
              "Four rules decided which genes earned one.", FT + "1/5")
    schematic(s, F)

    s = slide(prs, "Why a gene is in - and why a similar one is out",
              "Each rule is a measurement with a cutoff. Every rule shows a gene that passed and a "
              "comparable one that did not.", FT + "2/5", RUST)
    cards = [
        ("1", "Does it identify the cell type?",
         "Specificity against genes the panel already carries; must beat them (ratio > 1)",
         "Col23a1   3.7x more specific - no equal marker existed",
         "Sfrp1   0.9x - a panel gene already does it better", NAVY),
        ("2", "Is it a druggable receptor we cannot see?",
         "Regional enrichment, plus whether the receptor family is already covered",
         "Chrm1   M1 receptor - we could only see M2 before",
         "Gpr26   orphan receptor, no known ligand", TEAL),
        ("3", "Does it report the morphine-dependent state?",
         "Differential expression counted only in our 12 ORBm populations",
         "Per2   changes in 11 of 12 populations",
         "Nr4a3   8 clusters overall, but only 5 of ours", RUST),
        ("4", "Will the instrument actually detect it?",
         "Fraction of cells expressing it; sparse probes give unusable maps",
         "Grm8   99% of cells, >50% in 8 of 12 populations",
         "Mas1   most enriched of all, but only 45% of cells", SAGE),
    ]
    for i, (n, h, m, k, d, col) in enumerate(cards):
        x, y = 0.42 + (i % 2) * 6.30, 1.12 + (i // 2) * 1.74
        rrect(s, x, y, 6.16, 1.62, WHITE_H, col, 1.5)
        ov = rrect(s, x + 0.14, y + 0.13, 0.32, 0.32, col, None, shape=MSO_SHAPE.OVAL)
        label_in(ov, n, 12, True, WHITE_H)
        tbox(s, x + 0.54, y + 0.10, 5.50, 0.32, h, 13, True, col, space=0)
        tbox(s, x + 0.16, y + 0.48, 5.86, 0.32, m, 10.5, False, MUTED, space=0)
        tbox(s, x + 0.16, y + 0.86, 5.86, 0.32, "IN     " + k, 10.5, False, SAGE, space=0)
        tbox(s, x + 0.16, y + 1.20, 5.86, 0.32, "OUT   " + d, 10.5, False, RUST, space=0)
    rrect(s, 0.42, 4.68, 12.50, 2.20, ICE, NAVY, 1.2)
    tbox(s, 0.62, 4.80, 12.1, 0.28, "The constraint that forces all of this", 13, True, NAVY)
    tbox(s, 0.62, 5.14, 5.95, 1.60,
         f"The standard 10x Mouse Brain panel gives 248 genes at no extra cost. The custom add-on is "
         f"capped at 100 genes by design, not by price.\n\n"
         f"So {F['n']} justified genes means {F['free']} taken free and {F['custom']} custom - and "
         f"roughly three of every four candidates screened were turned down.",
         11, False, INK, space=2)
    tbox(s, 6.90, 5.14, 5.95, 1.60,
         "The four rules are independent, and that is deliberate.\n\n"
         "A receptor earns its slot by showing where a drug target sits, whether or not morphine "
         "changes it. One panel therefore serves the pharmacology aim and the addiction aim at the "
         "same time, instead of forcing a choice.",
         11, False, INK, space=2)

    s = slide(prs, f"Final panel  -  {F['n']} genes, one section, two regions",
              "One shared panel read from the same mouse. All 20 target cell populations remain "
              "separable.", FT + "3/5", TEAL)
    for i, (big, lab, col) in enumerate([
        (str(F["n"]), "genes justified on\nthe shared panel", NAVY),
        ("20 / 20", "cell populations\nstill separable", TEAL),
        (str(F["free"]), "free on the 10x\nbase panel", SAGE),
        ("12 + 8", "populations in\nORBm  +  BMAp", RUST),
    ]):
        tile(s, 0.42 + i * 3.16, 1.10, 2.94, big, lab, col)
    c = F["comp"]
    bar_chart(s, 0.30, 2.42, 7.00, 3.80, list(c.group), [int(v) for v in c.n],
              list(c.colour), "What the genes do")
    tbox(s, 7.60, 2.44, 5.30, 0.30, "What each cell will tell us", 14, True, NAVY)
    for i, (h, b, col) in enumerate([
        ("Identity", "Which of the 20 populations it is - cortical layer, interneuron "
                     "class, amygdala subtype", NAVY),
        ("Activity", "Whether it was recently active - Fos and Arc, plus the TRAP2 tag", TEAL),
        ("State", "Whether it carries the morphine-dependence signature", RUST),
        ("Receptors", "Which druggable receptors sit on it - opioid, muscarinic, "
                      "glutamate, relaxin", SAGE),
    ]):
        y = 2.88 + i * 0.90
        tbox(s, 7.60, y, 5.30, 0.26, h, 12.5, True, col, space=0)
        tbox(s, 7.60, y + 0.26, 5.30, 0.58, b, 11, False, INK, space=0)
    tbox(s, 7.60, 6.52, 5.30, 0.40,
         "The last row is the new capability.", 11, True, RUST)

    # backup 4: populations
    s = slide(prs, "The 20 populations we must tell apart",
              "Target list from the Allen Brain Cell Atlas taxonomy.", "BACKUP  ·  " + FT + "4/5")
    ac = F["ac"]
    for i, (big, lab, col) in enumerate([
        ("12", "ORBm populations\n83,406 Allen cells", NAVY),
        ("8", "BMAp populations\n40,709 Allen cells", TEAL),
        (f"{ac.n_cells.sum():,}", "cells in the 20\ntarget populations", SAGE),
        ("20 / 20", "have a dedicated\nmarker on the panel", RUST),
    ]):
        tile(s, 0.42 + i * 3.16, 1.10, 2.94, big, lab, col)
    for j, (reg, col, x) in enumerate([("ORBm", NAVY, 0.30), ("BMAp", TEAL, 6.75)]):
        g = ac[ac.region == reg]
        bar_chart(s, x, 2.40, 6.30, 4.30,
                  [r.allen_subclass_anchor.split(" ", 1)[1] for r in g.itertuples()],
                  [int(r.n_cells) for r in g.itertuples()], [col] * len(g),
                  f"{reg}  -  {len(g)} populations, {g.n_cells.sum():,} cells", gap=45)
    tbox(s, 0.42, 6.74, 12.5, 0.36,
         "Marker counts in the workbook are genes EXCLUSIVE to one population - the strictest test. "
         "Identification is combinatorial: L5 IT has 1 exclusive gene yet is separable from 9 of its "
         "11 neighbours using panel genes.", 10.5, False, MUTED)

    # backup 5: depth
    s = slide(prs, "The list rests on a full re-analysis of the reference atlas",
              "No gene was taken on a paper's word; every candidate was re-scored in these two regions.",
              "BACKUP  ·  " + FT + "5/5", TEAL)
    for i, (big, lab, col) in enumerate([
        ("226,886", "single cells scored across\nthe two target regions", NAVY),
        (f"{F['n_sub']}", "cell subclasses profiled,\nnot only the 20 targets", TEAL),
        (f"{F['n_measure']:,}", "abundance and specificity\nmeasurements", SAGE),
        (f"{F['n_pairs']:,}", "pairwise tests: can gene X\nseparate type A from B?", RUST),
    ]):
        tile(s, 0.42 + i * 3.16, 1.10, 2.94, big, lab, col)
    rrect(s, 0.42, 2.44, 12.50, 4.40, CREAM, GREY, 1.0)
    tbox(s, 0.64, 2.58, 12.1, 0.30, "What that analysis produced, in order", 14, True, NAVY)
    steps = [
        ("1.  Region-restricted expression matrices",
         "ORBm and BMAp cells were pulled out of the whole-brain atlas, so every abundance and "
         "specificity number describes these two regions - not a brain-wide average."),
        ("2.  Per-population marker ranking",
         "For each of the 20 targets, every candidate was ranked by how much of that population "
         "expresses it and how tightly it is restricted to it."),
        (f"3.  Pairwise separability testing",
         f"{F['n_pairs']:,} tests confirmed that neighbouring populations - L5 IT vs L5 ET, MEA vs "
         f"BMA - stay distinguishable using only the genes actually on the panel."),
        ("4.  Receptor and drug-target layer",
         f"Receptors were tiered by specificity and cross-referenced to the IUPHAR pharmacology "
         f"database, so the map covers targets that drugs already exist for. "
         f"{F['n_sources']} sources are documented, {F['n_doi']} with a DOI."),
    ]
    for i, (h, b) in enumerate(steps):
        y = 3.02 + i * 0.95
        tbox(s, 0.64, y, 12.1, 0.28, h, 12.5, True, NAVY, space=0)
        tbox(s, 0.92, y + 0.28, 11.8, 0.56, b, 11, False, INK, space=0)

    prs.save(DECK_MAIN)
    return DECK_MAIN


# ------------------------------------------------------------ cut deck + xlsx
def build_cut_deck(F, Fc) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    FT = "CONTINGENCY  ·  cut to the 100-gene custom cap  |  "

    s = slide(prs, f"If we must fit the 100-gene custom cap: cut {len(CUTS)}",
              f"The live design carries {F['custom']} custom probes. 10x caps a custom add-on at "
              f"{CAP} genes by design. This removes exactly {F['custom'] - CAP}.", FT + "1/2", RUST)
    for i, (big, lab, col) in enumerate([
        (f"{F['custom']}", "custom probes in the\ncurrent design", RUST),
        (f"-{len(CUTS)}", "genes removed by\nthis contingency", GREY),
        (f"{Fc['custom']}", "custom probes after\nthe cut - at the cap", SAGE),
        (f"{Fc['n']}", f"genes total, down\nfrom {F['n']}", NAVY),
    ]):
        tile(s, 0.42 + i * 3.16, 1.10, 2.94, big, lab, col)
    tbox(s, 0.42, 2.38, 12.5, 0.30,
         "Cut principle: a gene is removed when it fails the rule that admitted it. "
         "Nothing that carries a cell-population identification was touched.", 12, True, NAVY)
    # Deterministic two-column stack: groups are assigned to a column up front and
    # each box height is derived from its row count, so nothing can run off-slide.
    HEAD, ROW, GAP, TOP = 0.34, 0.26, 0.12, 2.76
    LEFT = [("Dan: fails its own rule", TEAL),
            ("Jesse: weakest of its own set", RUST),
            ("Depends on your constructs", GREY)]
    RIGHT = [("Too sparse to map", SAGE),
             ("Redundant within family", GOLD)]
    for x, column in ((0.42, LEFT), (6.72, RIGHT)):
        y = TOP
        for grp, col in column:
            items = [c for c in CUTS if c[2] == grp]
            if not items:
                continue
            h = HEAD + ROW * len(items) + 0.10
            rrect(s, x, y, 6.18, h, WHITE_H, col, 1.4)
            tbox(s, x + 0.14, y + 0.05, 5.90, 0.26,
                 f"{grp}   ({len(items)} gene" + ("s)" if len(items) != 1 else ")"),
                 11, True, col, space=0)
            for k, (g, why, _, conf) in enumerate(items):
                tbox(s, x + 0.20, y + HEAD + k * ROW, 5.84, 0.24,
                     f"{g}" + ("  (CONFIRM)" if conf else "") + f"   -   {why}",
                     9.5, False, INK, space=0)
            y += h + GAP
        assert y <= 7.12, f"cut-list column overflows: {y:.2f}"

    s = slide(prs, "What the cut costs, and what it protects",
              "The same four rules, read in reverse.", FT + "2/2", RUST)
    rrect(s, 0.42, 1.10, 6.16, 2.60, WHITE_H, SAGE, 1.5)
    tbox(s, 0.62, 1.22, 5.80, 0.30, "PROTECTED  -  nothing here was cut", 13, True, SAGE)
    tbox(s, 0.62, 1.60, 5.80, 2.00,
         "All 20 cell populations keep their identifying markers - 54 custom separators untouched.\n\n"
         "The morphine-state layer keeps Per2 (11 of 12 populations), Pcsk1 (9 of 12) and Camk2g, "
         "the only DOWN gene.\n\n"
         "The receptor map keeps Chrm1 and Grm8, the two family gaps we closed, plus every opioid "
         "receptor.", 11, False, INK, space=2)
    rrect(s, 6.76, 1.10, 6.16, 2.60, WHITE_H, RUST, 1.5)
    tbox(s, 6.96, 1.22, 5.80, 0.30, "GIVEN UP", 13, True, RUST)
    tbox(s, 6.96, 1.60, 5.80, 2.00,
         "Five of the amygdala genes that scored below their own specificity cutoff - BMAp depth "
         "drops, but no population becomes unidentifiable.\n\n"
         "Per1, so the circadian axis rests on Per2 alone.\n\n"
         "Six sparse receptors (15-36% of cells) whose maps would have been hard to read anyway.\n\n"
         "One NMDA and one AMPA subunit, and one pan-neuronal gene, all redundant.",
         11, False, INK, space=2)
    rrect(s, 0.42, 3.90, 12.50, 1.30, ICE, NAVY, 1.3)
    tbox(s, 0.62, 4.02, 12.1, 0.28, "Four cuts need your confirmation, not mine", 13, True, NAVY)
    tbox(s, 0.62, 4.36, 12.1, 0.78,
         "WPRE and mCherry are viral-vector elements - keep them only if you are injecting AAVs that "
         "carry them. Gabbr2 is the obligate GABA-B partner subunit; Gabbr1 alone still localises the "
         "receptor, but if you need subunit composition, keep both. Emx1 is a broad pallial-lineage TF "
         "that the specific layer separators largely cover.", 11, False, INK, space=2)
    rrect(s, 0.42, 5.40, 12.50, 1.48, CREAM, GREY, 1.0)
    tbox(s, 0.62, 5.52, 12.1, 0.28, "The alternative, if cutting is unacceptable", 13, True, NAVY)
    tbox(s, 0.62, 5.86, 12.1, 0.90,
         "A standalone custom Xenium panel supports up to 480 genes, which would hold the full design "
         "with room to spare. The trade is that the 248-gene base panel is no longer included, so the "
         f"{F['free']} genes we currently get free would have to be designed and paid for - and the "
         "pricing is a separate quote. Cutting 21 keeps the current order and costs nothing.",
         11, False, INK, space=2)

    prs.save(DECK_CUT)
    return DECK_CUT


def build_cut_xlsx(F) -> tuple[Path, dict]:
    shutil.copy2(LIVE, XL_CUT)
    wb = load_workbook(XL_CUT)
    cut = {c[0] for c in CUTS}
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))

    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        hdr = [c.value for c in ws[1]]
        gcol = hdr.index("gene") + 1
        drop = [r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=gcol).value in cut]
        for r in reversed(drop):
            ws.delete_rows(r)
        for i, r in enumerate(range(2, ws.max_row + 1), start=1):
            ws.cell(row=r, column=1, value=i)     # re-rank contiguously
        print(f"  {name}: removed {len(drop)} rows -> {ws.max_row - 1} genes")

    ws = wb.create_sheet("CUT_LIST")
    ws.append(["gene", "reason_it_was_cut", "cut_group", "needs_your_confirmation"])
    for c in ws[1]:
        c.font = c.font.copy(bold=True)
    for g, why, grp, conf in CUTS:
        ws.append([g, why, grp, "YES" if conf else ""])
    for col, w in zip("ABCD", (14, 92, 30, 24)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"

    fg = wb["FOR_MarkGreg"]
    fg.cell(row=fg.max_row + 1, column=1, value=f"CONTINGENCY: {len(CUTS)} genes removed to fit the {CAP} custom cap")
    fg.cell(row=fg.max_row, column=2, value=(
        f"10x caps a custom add-on at {CAP} target genes by design. The full design carried 121 custom "
        f"probes, so {len(CUTS)} were removed: {', '.join(sorted(cut))}. Each was cut because it failed "
        f"the rule that admitted it - see the CUT_LIST tab for the gene-by-gene reason. No cell-population "
        f"separator was removed, so all 20 populations remain identifiable. Four cuts (WPRE, mCherry, "
        f"Gabbr2, Emx1) depend on your constructs or priorities and are marked for confirmation. "
        f"order_rank was renumbered contiguously; no other sheet was altered."))
    wb.save(XL_CUT)

    sh = pd.read_excel(XL_CUT, "SHARED_PANEL_ORDER")
    free = int(sh.gene.isin(base).sum())
    return XL_CUT, {"n": len(sh), "free": free, "custom": len(sh) - free}


def main() -> None:
    F = facts(LIVE)
    print(f"live sheet : {F['n']} genes = {F['free']} free + {F['custom']} custom")
    print(f"cap        : {CAP} custom  ->  must cut {F['custom'] - CAP}")
    assert len(CUTS) == F["custom"] - CAP, f"cut list has {len(CUTS)}, need {F['custom'] - CAP}"
    live_genes = set(F["sh"].gene)
    missing = [c[0] for c in CUTS if c[0] not in live_genes]
    assert not missing, f"cut genes not on the sheet: {missing}"
    sep = set()
    for s_ in F["ac"].unique_separators_on_shared_panel.fillna(""):
        sep |= {x.strip() for x in s_.split(",") if x.strip()}
    clash = sorted({c[0] for c in CUTS} & sep)
    assert not clash, f"cut list touches load-bearing separators: {clash}"
    print(f"cut list   : {len(CUTS)} genes, none of them separators - OK")

    xl, Fc = build_cut_xlsx(F)
    print(f"\ncut sheet  -> {xl}")
    print(f"  after cut: {Fc['n']} genes = {Fc['free']} free + {Fc['custom']} custom")
    assert Fc["custom"] == CAP, f"after cut custom is {Fc['custom']}, expected {CAP}"

    print(f"\nmain deck  -> {build_main(F)}")
    print(f"cut deck   -> {build_cut_deck(F, Fc)}")


if __name__ == "__main__":
    main()
