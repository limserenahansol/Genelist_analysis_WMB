"""One-slide editable clone of the sources -> rules -> panel figure.

Native PowerPoint shapes only (no PNG). Click a box to edit the text.

Slide 1 is the figure. Slide 2 is a plain-language key for each box.
Numbers on slide 1 are the current 259-gene panel (20/20 types). Circadian
genes are from Jesse; SOW is not a keep rule.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parents[1] / "outputs"
DL = Path(r"c:\Users\hsollim\Downloads")
DST = OUT / "ORBm_BMAp_panel_flow_EDITABLE.pptx"

NAVY, TEAL, RUST, SAGE = "1D4E89", "2A6F97", "C44536", "6B7C6A"
GREY, CREAM, ICE, WHITE = "B8B2A8", "F4F1EA", "EAF2F8", "FFFFFF"
INK, MUTED, GOLD, TAUPE = "1F2937", "5B6472", "B08968", "8C7B6B"
SUB = "3C6E9F"
TF = "7A8B99"


def C(h):
    return RGBColor.from_string(h)


def rrect(s, x, y, w, h, fill, line, lw=1.5):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    sp.adjustments[0] = 0.06
    sp.fill.solid()
    sp.fill.fore_color.rgb = C(fill)
    if line:
        sp.line.color.rgb = C(line)
        sp.line.width = Pt(lw)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def rect(s, x, y, w, h, fill, line=None):
    sp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = C(fill)
    if line:
        sp.line.color.rgb = C(line)
        sp.line.width = Pt(1)
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def write_tf(sp, lines, anchor=MSO_ANCHOR.TOP, margin=0.08):
    """lines: list of (text, size, bold, colour, align)."""
    tf = sp.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(0.06)
    tf.margin_bottom = Inches(0.06)
    for i, (text, size, bold, colour, align) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = "Calibri"
        r.font.color.rgb = C(colour)
    return sp


def tbox(s, x, y, w, h, lines, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    write_tf(tb, lines, anchor=anchor, margin=0.04)
    return tb


def arrow(s, x, y, w=0.28, h=0.22, colour=GREY):
    sp = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y),
                            Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = C(colour)
    sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def source_card(s, x, y, w, h, title, body, colour):
    rrect(s, x, y, w, h, WHITE, colour, lw=1.75)
    head = rect(s, x, y, w, 0.38, colour)
    write_tf(head, [(title, 13, True, WHITE, PP_ALIGN.CENTER)],
             anchor=MSO_ANCHOR.MIDDLE, margin=0.06)
    body_box = rrect(s, x + 0.04, y + 0.42, w - 0.08, h - 0.48, WHITE, None)
    body_box.line.fill.background()
    write_tf(body_box, [(ln, 12, False, INK, PP_ALIGN.LEFT) for ln in body],
             anchor=MSO_ANCHOR.TOP, margin=0.08)


def slide_figure(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tbox(s, 0.35, 0.12, 12.6, 0.38, [
        ("How the 259 genes were chosen", 24, True, NAVY, PP_ALIGN.LEFT),
    ])
    tbox(s, 0.35, 0.48, 12.6, 0.32, [
        ("Left = where a gene was proposed.  Middle = the four tests every gene had to pass.  "
         "Right = what survived, by job.", 13, False, MUTED, PP_ALIGN.LEFT),
    ])

    # LEFT sources
    x, w = 0.32, 3.42
    source_card(s, x, 0.90, w, 1.88, "Allen Brain Cell Atlas (WMB-10X)", [
        "226,886 single cells in ORBm + BMAp",
        "20 target cell types (12 cortex + 8 amygdala)",
        "86 sub-populations inside those 20",
        "32,245 genes scored in these regions only",
    ], NAVY)
    source_card(s, x, 2.92, w, 1.78, "Collaborator data", [
        "Jesse — 5-day morphine DEGs in ORB",
        "55 of those genes sit on this panel",
        "Dan — GSE283418 amygdala spatial",
        "kept only where they still name a BMAp type",
    ], RUST)
    source_card(s, x, 4.84, w, 1.78, "Literature + published markers", [
        "13 documented sources (9 with a DOI)",
        "Published markers re-tested in Allen",
        "Circadian genes from Jesse, not a document name",
        "Sex genes excluded on request",
    ], TEAL)

    arrow(s, 3.78, 1.70, 0.32, 0.22, GREY)
    arrow(s, 3.78, 3.70, 0.32, 0.22, GREY)
    arrow(s, 3.78, 5.60, 0.32, 0.22, GREY)

    # MIDDLE rules
    mx, mw, my, mh = 4.18, 4.48, 0.90, 5.72
    rrect(s, mx, my, mw, mh, ICE, NAVY, lw=2.0)
    tbox(s, mx + 0.12, my + 0.08, mw - 0.24, 0.42, [
        ("Every candidate re-measured in these two regions", 14, True, NAVY, PP_ALIGN.CENTER),
    ])
    rules = [
        ("1  Does it name the cell type?",
         "High in that type and low in the other 19, or in its closest neighbour."),
        ("2  Does it name the sub-population?",
         "High in one sub-type inside a cell type, low in its sibling sub-types."),
        ("3  Can the instrument read it?",
         "Present in enough cells to make a map. Empty maps (e.g. Sstr4 at 1%) are out."),
        ("4  Does it report morphine or circadian state?",
         "Jesse 5-day morphine DEGs in ORBm, plus the clock limbs those DEGs need to be readable."),
    ]
    y = my + 0.52
    for head, body in rules:
        tbox(s, mx + 0.18, y, mw - 0.36, 0.28, [
            (head, 13.5, True, INK, PP_ALIGN.LEFT),
        ])
        tbox(s, mx + 0.18, y + 0.28, mw - 0.36, 0.52, [
            (body, 12, False, MUTED, PP_ALIGN.LEFT),
        ])
        y += 0.88
    tbox(s, mx + 0.16, my + mh - 1.05, mw - 0.32, 0.92, [
        ("What failed a rule was dropped, with its number:", 13, True, RUST, PP_ALIGN.CENTER),
        ("empty maps  ·  no contrast (Clock, Syt1)  ·  duplicate of a gene already kept",
         12, False, RUST, PP_ALIGN.CENTER),
    ])

    arrow(s, 8.72, 3.65, 0.36, 0.26, NAVY)

    # RIGHT panel
    px, pw = 9.14, 3.86
    rrect(s, px, my, pw, mh, CREAM, SAGE, lw=2.0)
    tbox(s, px + 0.10, my + 0.08, pw - 0.20, 0.40, [
        ("Final panel  —  259 genes", 16, True, SAGE, PP_ALIGN.CENTER),
    ])
    cats = [
        ("Cell identity and brain region", 103, NAVY),
        ("Sub-population markers", 68, SUB),
        ("Druggable receptor map", 29, TEAL),
        ("Neural activity and plasticity", 26, SAGE),
        ("Identity transcription factors", 13, TF),
        ("Morphine-dependence state", 4, RUST),
        ("Circadian", 14, TAUPE),
        ("Genetic-tag reporters", 2, GOLD),
    ]
    y = my + 0.55
    for name, n, col in cats:
        sw = rrect(s, px + 0.18, y + 0.08, 0.16, 0.16, col, None)
        sw.adjustments[0] = 0.02
        tbox(s, px + 0.42, y, 2.55, 0.34, [
            (name, 12, False, INK, PP_ALIGN.LEFT),
        ])
        tbox(s, px + pw - 0.70, y, 0.50, 0.34, [
            (str(n), 13, True, INK, PP_ALIGN.RIGHT),
        ])
        y += 0.48
    tbox(s, px + 0.12, my + mh - 0.85, pw - 0.24, 0.72, [
        ("All 20 target cell types are named.", 13, True, SAGE, PP_ALIGN.CENTER),
        ("86 of 86 sub-populations have a marker on this panel.", 12, False, SAGE, PP_ALIGN.CENTER),
    ])

    tbox(s, 0.35, 7.18, 12.6, 0.24, [
        ("ORBm + BMAp custom Xenium panel  |  click any box to edit  |  259 genes, 20/20 types",
         11, False, MUTED, PP_ALIGN.LEFT),
    ])


def slide_key(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tbox(s, 0.40, 0.16, 12.5, 0.40, [
        ("What each part of that figure is saying", 24, True, NAVY, PP_ALIGN.LEFT),
    ])
    tbox(s, 0.40, 0.56, 12.5, 0.32, [
        ("The figure is a filter, not a collage. Every gene, from any source, goes through the middle.",
         14, False, MUTED, PP_ALIGN.LEFT),
    ])

    items = [
        (NAVY, "LEFT  ·  Allen atlas",
         "The measuring stick. 226,886 cells from these two regions. A gene is kept as a cell-type marker only if it is high in one of the 20 types and low in the others. Whole-brain averages are not used."),
        (RUST, "LEFT  ·  Collaborator data",
         "Jesse: which genes change after 5-day morphine in orbitofrontal cortex. Dan: which genes were used as amygdala spatial markers. These are proposals. They still have to pass the middle."),
        (TEAL, "LEFT  ·  Literature",
         "Published marker names (Vip, Pvalb, Syt6, …) and circadian genes. Each one is re-tested in Allen for these two regions. A paper name is not enough."),
        (NAVY, "MIDDLE  ·  four tests",
         "1 Names a cell type.  2 Names a sub-type inside it.  3 Is on enough cells for Xenium to see.  4 Reports morphine or circadian state from Jesse. Fail any test that matches the gene's job → out."),
        (RUST, "MIDDLE  ·  red line at the bottom",
         "Genes that were proposed and then dropped, with the reason: too rare to map, on in every cell (no contrast), or already covered by a gene on the list."),
        (SAGE, "RIGHT  ·  the 259 genes",
         "What survived, grouped by job. Identity genes tell which of the 20 types the cell is. Receptors, IEGs, circadian, morphine, and tdTomato/iCre are the extra layers on top of identity."),
    ]
    y = 0.98
    for i, (col, head, body) in enumerate(items):
        col_i = i % 2
        row = i // 2
        x = 0.40 + col_i * 6.45
        yy = y + row * 1.85
        rrect(s, x, yy, 6.20, 1.70, WHITE, col, lw=1.6)
        bar = rect(s, x, yy, 0.12, 1.70, col)
        tbox(s, x + 0.28, yy + 0.10, 5.75, 0.36, [
            (head, 14, True, col, PP_ALIGN.LEFT),
        ])
        tbox(s, x + 0.28, yy + 0.46, 5.75, 1.12, [
            (body, 13, False, INK, PP_ALIGN.LEFT),
        ])

    tbox(s, 0.40, 7.18, 12.5, 0.24, [
        ("The screenshot you sent was a 297-gene draft of the same figure. This deck is the current 259-gene panel.",
         12, False, MUTED, PP_ALIGN.LEFT),
    ])


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    slide_figure(prs)
    slide_key(prs)
    prs.save(DST)
    copied = DL / DST.name
    try:
        shutil.copy2(DST, copied)
    except PermissionError:
        copied = DL / "ORBm_BMAp_panel_flow_EDITABLE_v2.pptx"
        shutil.copy2(DST, copied)
    print("wrote", DST)
    print("copied", copied)


if __name__ == "__main__":
    main()
