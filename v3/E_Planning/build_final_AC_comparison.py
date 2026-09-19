"""Final two-slide comparison: Option A (367 genes, add-on) vs Option C (245 genes, standalone).

The point this deck has to make, because it is counter-intuitive: a standalone
custom panel costs about twice as much and measures FEWER total genes. The add-on
route keeps the whole 248-gene Mouse Brain base panel riding along for free, so

  add-on route    248 base + custom        -> 348-367 genes measured
  standalone      only what we design      -> 245 genes measured

Option C buys 98 more *curated* genes but gives up 201 base-panel genes, at double
the panel cost. That trade is stated plainly rather than buried.

Fully editable: native shapes and native charts, no images.

Output: FINAL_option_A_vs_C.pptx
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PA = OUT / "PANEL_A_current_166genes_119custom.xlsx"
PB = OUT / "PANEL_B_cut_147genes_100custom.xlsx"
PC = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"
DECK = OUT / "FINAL_option_A_vs_C.pptx"

NAVY, TEAL, RUST, SAGE, GOLD = "1D4E89", "2A6F97", "C44536", "6B7C6A", "B08968"
GREY, CREAM, ICE, WH = "B8B2A8", "F4F1EA", "EAF2F8", "FFFFFF"
INK, MUTED = "1F2937", "5B6472"
CAP = 100

# Panel-only cost from the existing quote, and the standalone estimate.
QUOTE_BASE_PANEL = 483      # 1000462, 2 rxn x2, after 30%
QUOTE_ADDON = 2825          # 1000651, 4 rxn, after 50%
ADDON_LIST = 5650           # list on the quote
STANDALONE_RATIO = 13676.47 / 6890.49   # GSA list 101-300 vs 51-100


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


def tile(s, x, y, w, big, lab, col, h=1.08, bigsize=25):
    rrect(s, x, y, w, h, CREAM, col, 1.3)
    tbox(s, x + 0.08, y + 0.04, w - 0.16, 0.52, big, bigsize, True, col, PP_ALIGN.CENTER)
    tbox(s, x + 0.08, y + 0.55, w - 0.16, 0.48, lab, 10.5, False, MUTED, PP_ALIGN.CENTER, space=0)


def slide(prs, title, sub, footer, tcol=NAVY):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rrect(s, 0, 0, 13.333, 0.12, NAVY, None, shape=MSO_SHAPE.RECTANGLE)
    tbox(s, 0.40, 0.18, 12.5, 0.44, title, 23, True, tcol)
    if sub:
        tbox(s, 0.40, 0.60, 12.5, 0.36, sub, 13, False, MUTED)
    tbox(s, 0.40, 7.16, 12.5, 0.26, footer, 10.5, False, MUTED)
    return s


def stacked(s, x, y, w, h, title):
    """Curated vs base-panel genes riding along, per route."""
    cd = CategoryChartData()
    cd.categories = ["Option A\nadd-on route", "Option C\nstandalone"]
    cd.add_series("genes I chose and justified", (166, 245))
    cd.add_series("base-panel genes included free", (201, 0))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(x), Inches(y),
                            Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.font.size, ch.font.name = Pt(11), "Calibri"
    ch.has_title = True
    ch.chart_title.text_frame.text = title
    r = ch.chart_title.text_frame.paragraphs[0].runs[0]
    r.font.size, r.font.bold, r.font.name = Pt(12), True, "Calibri"
    r.font.color.rgb = C(NAVY)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(10)
    pl = ch.plots[0]
    pl.gap_width = 90
    pl.has_data_labels = True
    pl.data_labels.font.size, pl.data_labels.font.bold = Pt(11), True
    pl.data_labels.font.name = "Calibri"
    for i, col in enumerate((NAVY, GREY)):
        pl.series[i].format.fill.solid()
        pl.series[i].format.fill.fore_color.rgb = C(col)
    ch.value_axis.visible = False
    ch.value_axis.has_major_gridlines = False
    ch.category_axis.has_major_gridlines = False
    ch.category_axis.format.line.color.rgb = C(GREY)


def main() -> None:
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    A = pd.read_excel(PA, "SHARED_PANEL_ORDER")
    Cc = pd.read_excel(PC, "SHARED_PANEL_ORDER")
    a_cust = int((~A.gene.isin(base)).sum())
    a_meas = len(base) + a_cust
    c_meas = len(Cc)
    sa_list = round(ADDON_LIST * STANDALONE_RATIO)
    sa_50 = round(sa_list * 0.5)
    now = QUOTE_BASE_PANEL + QUOTE_ADDON
    print(f"A: {a_meas} measured ({len(base)} base + {a_cust} custom), {len(A)} curated, "
          f"{a_cust - CAP} over cap")
    print(f"C: {c_meas} measured, all curated")
    print(f"panel cost now ${now:,} | standalone 101-300 est. list ${sa_list:,}, at 50% ${sa_50:,}")

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    FT = "ORBm + BMAp Xenium panel  ·  final options  |  "

    # ---------------- slide 1: Option A
    s = slide(prs, f"Option A  -  {a_meas} genes via the add-on route",
              "The standard Mouse Brain panel is included, so its 248 genes are all measured "
              "and only the extra probes are paid for.", FT + "1/2")
    for i, (big, lab, col) in enumerate([
            (str(a_meas), "genes measured\nper tissue section", NAVY),
            ("248", "from the Mouse Brain\nbase panel, included", SAGE),
            (str(a_cust), "custom probes\nI designed", TEAL),
            (f"{a_cust - CAP} over", f"the {CAP}-gene add-on cap\n- needs trimming", RUST)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col, bigsize=24)

    rrect(s, 0.42, 2.34, 6.16, 2.34, WH, SAGE, 1.5)
    tbox(s, 0.62, 2.44, 5.80, 0.28, "What this buys", 13, True, SAGE)
    tbox(s, 0.62, 2.78, 5.80, 1.80,
         f"All 248 base-panel genes are measured whether or not I used them in the design, so the "
         f"section reports {a_meas} genes in total.\n\n"
         f"{len(A)} of those are genes I specifically justified: 47 taken from the base panel plus "
         f"{a_cust} custom probes.\n\n"
         "All 20 target cell populations remain individually identifiable.",
         11, False, INK, space=2)
    rrect(s, 6.76, 2.34, 6.16, 2.34, WH, RUST, 1.5)
    tbox(s, 6.96, 2.44, 5.80, 0.28, "The one problem", 13, True, RUST)
    tbox(s, 6.96, 2.78, 5.80, 1.80,
         f"10x caps a custom add-on at {CAP} genes by design, not by price. This version needs "
         f"{a_cust}, so it is {a_cust - CAP} over.\n\n"
         f"Trimming {a_cust - CAP} genes gives {len(base) + CAP} measured genes and fits the quote I "
         f"already have. Each removed gene failed the rule that admitted it, and no cell-population "
         f"marker is touched.",
         11, False, INK, space=2)
    rrect(s, 0.42, 4.84, 12.50, 2.04, ICE, NAVY, 1.3)
    tbox(s, 0.62, 4.94, 12.1, 0.28, "Cost - no change to the existing quote", 13, True, NAVY)
    tbox(s, 0.62, 5.28, 12.1, 1.50,
         f"Mouse Brain panel ${QUOTE_BASE_PANEL:,} after discount, plus the Add-on Custom 51-100 "
         f"(part 1000651) at ${QUOTE_ADDON:,} after a 50% discount - ${now:,} for the panel, inside a "
         f"${14438:,} order.\n\n"
         "Everything else on the quote - decoding consumables, slides, reagents, the cell segmentation "
         "kit - is unaffected by which panel option is chosen.",
         11, False, INK, space=2)

    # ---------------- slide 2: Option C
    s = slide(prs, f"Option C  -  {c_meas} genes via a standalone custom panel",
              "Every candidate that passed my analysis, with no cap - but the base panel is no longer "
              "included, which cuts the total gene count.", FT + "2/2", TEAL)
    for i, (big, lab, col) in enumerate([
            (str(c_meas), "genes measured\nper tissue section", TEAL),
            ("0", "base-panel genes\n- none included", RUST),
            (str(c_meas), "all of them genes I\nchose and justified", NAVY),
            ("~2x", "the panel cost,\nwith 50% discount", GOLD)]):
        tile(s, 0.42 + i * 3.16, 1.06, 2.94, big, lab, col, bigsize=24)

    stacked(s, 0.30, 2.34, 6.20, 3.24, "Total genes measured, by route")
    rrect(s, 6.76, 2.34, 6.16, 3.24, WH, RUST, 1.6)
    tbox(s, 6.96, 2.44, 5.80, 0.30, "Read this before deciding", 13.5, True, RUST)
    tbox(s, 6.96, 2.82, 5.80, 2.64,
         f"Paying about twice as much measures FEWER genes, not more: {c_meas} against "
         f"{len(base) + CAP} on the trimmed add-on version.\n\n"
         f"A standalone panel replaces the pre-designed panel, so the 248 base-panel genes stop coming "
         f"along for free and all {c_meas} become probes I design and pay for.\n\n"
         f"What it does buy is {c_meas - (47 + CAP)} more genes that I specifically chose - broader "
         f"morphine-response genes, more ORB-enriched receptors, extra amygdala markers and two more "
         f"L5 IT separators.\n\n"
         "Several of those additions have unscored detectability, so some will map sparsely.",
         11, False, INK, space=2)
    rrect(s, 0.42, 5.72, 12.50, 1.16, CREAM, GREY, 1.2)
    tbox(s, 0.62, 5.80, 12.1, 0.28, "Cost, at the 50% discount", 13, True, NAVY)
    tbox(s, 0.62, 6.12, 12.1, 0.72,
         f"Standalone Custom 101-300 (part 1000648) lists at roughly ${sa_list:,} on the same basis as "
         f"my current quote; at 50% that is about ${sa_50:,}. The base-panel line "
         f"(${QUOTE_BASE_PANEL:,}) drops out, so the panel goes from ${now:,} to about ${sa_50:,} - "
         f"an increase of roughly ${sa_50 - now:,}. My recommendation is the trimmed add-on version "
         f"unless the {c_meas - (47 + CAP)} extra curated genes are worth measuring "
         f"{len(base) + CAP - c_meas} fewer genes overall.",
         11, False, INK, space=2)

    prs.save(DECK)
    pics = sum(1 for sl in prs.slides for sh in sl.shapes if sh.shape_type == 13)
    bad = [i for i, sl in enumerate(prs.slides, 1)
           if max((sh.top + sh.height) / 914400 for sh in sl.shapes if sh.height) > 7.45
           or max((sh.left + sh.width) / 914400 for sh in sl.shapes if sh.height) > 13.34]
    print(f"\n{DECK.name}: slides={len(prs.slides._sldIdLst)} pictures={pics} "
          f"off-slide={bad or 'none'} {'OK' if pics == 0 and not bad else 'FAIL'}")
    assert pics == 0 and not bad


if __name__ == "__main__":
    main()
