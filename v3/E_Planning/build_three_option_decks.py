"""One fully editable 3-slide deck per panel option (A current, B cut, C expanded).

Every deck is built from native PowerPoint shapes and native PowerPoint charts -
no images anywhere - so the PI can move, recolour and retype everything, and edit
the chart data in PowerPoint.

Numbers are read from each option's own workbook, so a deck can never disagree
with the sheet it describes.

  A  PANEL_A_current_166genes_119custom.xlsx   scientifically complete, 19 over the add-on cap
  B  PANEL_B_cut_147genes_100custom.xlsx       orderable today on the existing quote
  C  PANEL_C_expanded_standalone_245genes.xlsx standalone custom, different SKU and price
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
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
LONG = OUT / "subclass_markers_expanded" / "Subclass_Discriminating_Markers_long.csv"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"

NAVY, TEAL, RUST, SAGE, GOLD = "1D4E89", "2A6F97", "C44536", "6B7C6A", "B08968"
GREY, CREAM, ICE, WH = "B8B2A8", "F4F1EA", "EAF2F8", "FFFFFF"
INK, MUTED = "1F2937", "5B6472"
CAP = 100

GROUPS = [
    ("Cell identity and region", ["1_celltype_separator", "3_class_backbone",
                                  "11_class_backbone_optional", "8_TF_identity",
                                  "9_published_regional", "12_GSE283418_added",
                                  "18_expanded_BMAp", "15_L5IT_separator_added",
                                  "19_expanded_L5IT_separator"], NAVY),
    ("Druggable receptor map", ["6_GPCR_druggable", "4_GPCR_cell_type_specific",
                                "14_Jesse_ORB_GPCR", "14_ORB_enriched_GPCR",
                                "17_expanded_ORB_GPCR"], TEAL),
    ("Activity and plasticity", ["5_IEG", "7_plasticity"], SAGE),
    ("Morphine-dependence state", ["13_Jesse_morphine_state", "16_expanded_morphine_state"], RUST),
    ("TRAP genetic tag", ["2_reporter_transgene"], GOLD),
]

OPTIONS = [
    dict(key="A", path=OUT / "PANEL_A_current_166genes_119custom.xlsx",
         deck=OUT / "OPTION_A_current_119custom.pptx",
         title="Option A  -  the complete add-on design",
         tag="OPTION A  ·  166 genes, 119 custom",
         headline="Every gene we can justify, as an add-on to the standard mouse brain panel.",
         status=("NOT ORDERABLE AS-IS", RUST,
                 "10x caps a custom add-on at 100 target genes by design. This design needs 119, "
                 "so it is 19 over. Option B is the same design cut to the cap; Option C moves to a "
                 "different product that has room for all of it."),
         cost=("On the existing quote", "Xenium Mouse Brain panel + Add-on Custom 51-100 (part 1000651). "
               "No price change - but only if the custom count comes down to 100.")),
    dict(key="B", path=OUT / "PANEL_B_cut_147genes_100custom.xlsx",
         deck=OUT / "OPTION_B_cut_to_100custom.pptx",
         title="Option B  -  cut to the 100-gene custom cap",
         tag="OPTION B  ·  147 genes, 100 custom",
         headline="The same design trimmed to exactly the add-on cap, so it can be ordered today.",
         status=("ORDERABLE NOW", SAGE,
                 "Exactly at the 100-gene custom cap. 19 genes were removed, each because it failed the "
                 "rule that admitted it. No cell-population marker was touched, so all 20 populations "
                 "remain identifiable."),
         cost=("No change to the quote", "Xenium Mouse Brain panel + Add-on Custom 51-100 (part 1000651), "
               "list $5,650, quoted at $2,825 after discount. Nothing further to negotiate.")),
    dict(key="C", path=OUT / "PANEL_C_expanded_standalone_245genes.xlsx",
         deck=OUT / "OPTION_C_expanded_standalone_245.pptx",
         title="Option C  -  expanded standalone custom panel",
         tag="OPTION C  ·  245 genes, standalone custom",
         headline="Every candidate with a documented basis, on a standalone custom panel with no cap problem.",
         status=("NEEDS A DIFFERENT PRODUCT AND QUOTE", TEAL,
                 "A standalone custom panel replaces the pre-designed panel rather than adding to it, so "
                 "there is no 100-gene cap - but also no free base panel: all 245 genes become designed "
                 "probes. 79 genes held back purely for lack of slots come back in."),
         cost=("New quote required", "245 genes falls in a standalone-custom band above 101. The "
               "301-480 band (part 1000647) lists at about $21,007 for 4 reactions, which is more panel "
               "than we need - ask the rep for the 101-300 band instead. Pricing must be confirmed.")),
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
    return cn


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
    return ch


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
    comp = pd.DataFrame([{"group": n, "n": len(sh[sh.block.isin(b)]), "colour": c}
                         for n, b, c in GROUPS])
    assert comp.n.sum() == len(sh), f"{path.name}: groups cover {comp.n.sum()} of {len(sh)}"
    long = pd.read_csv(LONG)

    def bucket(b):
        if b.startswith(("12_", "18_")):
            return "dan"
        if b.startswith(("13_", "14_", "16_", "17_")):
            return "jesse"
        return "core"

    sh["src"] = sh.block.apply(bucket)
    return dict(sh=sh, ac=ac, comp=comp, n=len(sh), free=int(sh.free.sum()),
                custom=int((~sh.free).sum()), yld=sh.groupby("src").size(),
                n_sub=long.subclass.nunique(), n_measure=len(long),
                n_pairs=len(pd.read_csv(PAIRS)),
                n_sources=len(pd.read_excel(path, "SOURCES")))


def schematic(s, F, standalone: bool):
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
        inlabel(rrect(s, 0.42, y, 3.28, 0.34, col, None, shape=MSO_SHAPE.RECTANGLE),
                t, 11, True, WH)
        tbox(s, 0.56, y + 0.40, 3.00, 0.62, b, 9.5, False, INK, space=1)
        tbox(s, 0.56, y + SH_ - 0.30, 1.6, 0.24, scr, 9.5, True, col)
        connect(s, 3.70, y + SH_ / 2, 9.70, 3.52, col)
        tbox(s, 3.80, y + SH_ / 2 - 0.30, 1.0, 0.24, f"{kep} kept", 10, True, col)
    rules = [("1", "Does it identify the cell type?", NAVY),
             ("2", "Is it a druggable receptor we cannot already see?", TEAL),
             ("3", "Does it report the morphine-dependent state?", RUST),
             ("4", "Will the instrument actually detect it?", SAGE)]
    RY, RH_, RG = 1.40, 0.84, 0.14
    for i, (n, q, col) in enumerate(rules):
        y = RY + i * (RH_ + RG)
        rrect(s, 4.90, y, 4.52, RH_, WH, col, 1.4)
        inlabel(rrect(s, 5.02, y + (RH_ - 0.30) / 2, 0.30, 0.30, col, None,
                      shape=MSO_SHAPE.OVAL), n, 11.5, True, WH)
        tbox(s, 5.42, y + 0.08, 3.86, RH_ - 0.16, q, 11, True, col, space=0,
             anchor=MSO_ANCHOR.MIDDLE)
    rrect(s, 4.90, 5.34, 4.52, 0.94, ICE, NAVY, 1.3)
    tbox(s, 5.00, 5.42, 4.32, 0.24, "Every rule measured in the Allen atlas",
         10.5, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 5.00, 5.68, 4.32, 0.54,
         f"226,886 cells  ·  {F['n_sub']} subclasses\n"
         f"{F['n_measure']:,} measurements  ·  {F['n_pairs']:,} pairwise tests",
         9.5, False, INK, PP_ALIGN.CENTER, space=0)
    rrect(s, 9.70, 1.40, 3.22, 4.88, ICE, NAVY, 2.1)
    tbox(s, 9.80, 1.50, 3.02, 0.26, "THIS OPTION", 11, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.80, 1.80, 3.02, 0.80, str(F["n"]), 42, True, NAVY, PP_ALIGN.CENTER)
    tbox(s, 9.80, 2.58, 3.02, 0.24, "genes on one section", 10, False, MUTED, PP_ALIGN.CENTER)
    connect(s, 9.88, 2.96, 12.74, 2.96, GREY, 1.0)
    tbox(s, 9.80, 3.04, 3.02, 0.90,
         f"{int(y_.get('core',0))} our marker screen\n{int(y_.get('dan',0))} Berg & Scherrer\n"
         f"{int(y_.get('jesse',0))} Jesse Niehaus", 10.5, False, INK, PP_ALIGN.CENTER, space=1)
    connect(s, 9.88, 4.08, 12.74, 4.08, GREY, 1.0)
    tbox(s, 9.80, 4.16, 3.02, 0.72,
         "all 245 designed\n(standalone: no free\nbase panel)" if standalone
         else f"{F['free']} free on the base panel\n{F['custom']} custom probes",
         10.5, True, NAVY, PP_ALIGN.CENTER, space=1)
    connect(s, 9.88, 5.02, 12.74, 5.02, GREY, 1.0)
    tbox(s, 9.80, 5.10, 3.02, 1.02,
         "2 brain regions\n20 cell populations\n1 section, 1 animal",
         10.5, True, NAVY, PP_ALIGN.CENTER, space=1)
    rrect(s, 0.42, 5.34, 4.10, 0.94, "F7F5F2", GREY, 1.0)
    tbox(s, 0.52, 5.42, 3.90, 0.24,
         f"701 candidates  ->  {F['n']} selected", 10.5, True, INK, PP_ALIGN.CENTER)
    tbox(s, 0.52, 5.68, 3.90, 0.54,
         "Each keeps its evidence and the rule\nthat admitted it.",
         9.5, False, MUTED, PP_ALIGN.CENTER, space=0)


def build(opt) -> Path:
    F = facts(opt["path"])
    standalone = opt["key"] == "C"
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    FT = opt["tag"] + "  |  ORBm + BMAp Xenium  |  "

    s = slide(prs, opt["title"], opt["headline"], FT + "1/3")
    schematic(s, F, standalone)

    s = slide(prs, "Why a gene is in - and why a similar one is out",
              "Each rule is a measurement with a cutoff, so any gene's inclusion can be re-checked.",
              FT + "2/3", RUST)
    cards = [("1", "Does it identify the cell type?",
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
              "Mas1   most enriched of all, but only 45% of cells", SAGE)]
    for i, (n, h, m, k, d, col) in enumerate(cards):
        x, y = 0.42 + (i % 2) * 6.30, 1.10 + (i // 2) * 1.70
        rrect(s, x, y, 6.16, 1.58, WH, col, 1.4)
        inlabel(rrect(s, x + 0.14, y + 0.12, 0.30, 0.30, col, None, shape=MSO_SHAPE.OVAL),
                n, 11.5, True, WH)
        tbox(s, x + 0.52, y + 0.09, 5.52, 0.30, h, 12.5, True, col, space=0)
        tbox(s, x + 0.16, y + 0.46, 5.86, 0.30, m, 10, False, MUTED, space=0)
        tbox(s, x + 0.16, y + 0.82, 5.86, 0.30, "IN     " + k, 10, False, SAGE, space=0)
        tbox(s, x + 0.16, y + 1.16, 5.86, 0.30, "OUT   " + d, 10, False, RUST, space=0)
    head, col, body = opt["status"]
    rrect(s, 0.42, 4.60, 12.50, 1.16, WH, col, 1.6)
    tbox(s, 0.62, 4.70, 12.1, 0.28, head, 13.5, True, col)
    tbox(s, 0.62, 5.02, 12.1, 0.68, body, 11, False, INK, space=2)
    ch, cb = opt["cost"]
    rrect(s, 0.42, 5.90, 12.50, 0.98, ICE, NAVY, 1.2)
    tbox(s, 0.62, 5.99, 12.1, 0.26, ch, 12.5, True, NAVY)
    tbox(s, 0.62, 6.27, 12.1, 0.54, cb, 11, False, INK, space=2)

    s = slide(prs, f"What Option {opt['key']} delivers",
              "Composition and measurement capability of this version.", FT + "3/3", TEAL)
    tiles = ([(str(F["n"]), "genes, all designed\n(standalone custom)", NAVY),
              ("20 / 20", "cell populations\nstill separable", TEAL),
              ("245", "no cap - the add-on\n100 limit does not apply", SAGE),
              ("12 + 8", "populations in\nORBm  +  BMAp", RUST)] if standalone else
             [(str(F["n"]), "genes on the\nshared panel", NAVY),
              ("20 / 20", "cell populations\nstill separable", TEAL),
              (f"{F['custom']} / {CAP}", "custom probes against\nthe 10x add-on cap",
               SAGE if F["custom"] <= CAP else RUST),
              ("12 + 8", "populations in\nORBm  +  BMAp", RUST)])
    for i, (big, lab, col) in enumerate(tiles):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col)
    c = F["comp"]
    bars(s, 0.30, 2.38, 7.05, 3.90, list(c.group), [int(v) for v in c.n], list(c.colour),
         f"What the {F['n']} genes do")
    tbox(s, 7.62, 2.40, 5.30, 0.28, "What each cell will tell us", 14, True, NAVY)
    for i, (h, b, col) in enumerate([
        ("Identity", "Which of the 20 populations it is - layer, interneuron class, "
                     "amygdala subtype", NAVY),
        ("Activity", "Whether it was recently active - Fos and Arc, plus the TRAP2 tag "
                     "(tdTomato and iCre)", TEAL),
        ("State", "Whether it carries the morphine-dependence signature", RUST),
        ("Receptors", "Which druggable receptors sit on it - opioid, muscarinic, "
                      "glutamate, relaxin", SAGE),
    ]):
        y = 2.82 + i * 0.92
        tbox(s, 7.62, y, 5.30, 0.26, h, 12.5, True, col, space=0)
        tbox(s, 7.62, y + 0.26, 5.30, 0.60, b, 10.5, False, INK, space=0)
    tbox(s, 7.62, 6.56, 5.30, 0.34,
         "No AAV probes: this project crosses TRAP2 with a tdTomato reporter line.",
         10.5, True, MUTED)

    prs.save(opt["deck"])
    return opt["deck"]


def main() -> None:
    for opt in OPTIONS:
        F = facts(opt["path"])
        p = build(opt)
        prs = Presentation(p)
        pics = sum(1 for s in prs.slides for sh in s.shapes if sh.shape_type == 13)
        bad = []
        for i, s in enumerate(prs.slides, 1):
            b = [((sh.left + sh.width) / 914400, (sh.top + sh.height) / 914400)
                 for sh in s.shapes if sh.height]
            if max(y for _, y in b) > 7.45 or max(x for x, _ in b) > 13.34:
                bad.append(i)
        print(f"Option {opt['key']}: {F['n']:3d} genes, custom {F['custom']:3d} -> {p.name}")
        print(f"   slides={len(prs.slides._sldIdLst)} pictures={pics} "
              f"off-slide={bad or 'none'} {'OK' if pics == 0 and not bad else 'FAIL'}")
        assert pics == 0 and not bad


if __name__ == "__main__":
    main()
