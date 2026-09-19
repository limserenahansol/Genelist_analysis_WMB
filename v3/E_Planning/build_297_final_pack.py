"""Final pack for the 297-gene ORBm + BMAp panel: order workbook, funder deck, one-page list.

Gene content is FROZEN at 297. Nothing added or removed.

Two framing corrections are baked in here, both of which I had wrong earlier and which the
measurements settled:

  1 "Only 4 of 20 cell types have a marker" was WRONG, twice over. First, it ranked single
    genes by their margin against all 74 other subclasses in the section - including
    striatal, hypothalamic and glial populations already excluded by the time a target type
    is called - so the argmax fell on a ubiquitous gene at +0.0pp, which I reported as "no
    marker". Second, even the corrected version pooled ORBm and BMAp competitors, which is
    still too strict: the two regions sit at different places on the slide and are separated
    by coordinate before any gene is read, so a BMAp type never has to be told apart from an
    ORBm type by transcript. With same-region competitors every one of the 20 types has 3 to
    28 dedicated markers (median 6), on top of 91-127 genes expressed above 50% in it.
    Syt1 is one gene among those, not the only one.
    Note the converse trap: a cell-type NAME does not imply a dedicated marker. Sox6 is 58%
    in 073 MEA-BST Sox6 Gaba but 95% in Pvalb Gaba and 90% in Sst Gaba, because it marks the
    whole MGE interneuron lineage. It stays on the panel as a lineage gene; the dedicated
    separators for 073 are Prox1 +35pp, Dlx1 +31pp and Chn2 +24pp.
  2 The right test is per-type recall on held-out cells, and all 20 types are recovered:
    mean recall 0.922, 18 of 20 at or above 0.85. The two below are 004 L6 IT (0.708) and
    005 L5 IT (0.694), and their errors are almost entirely internal to the IT family -
    99.4% and 99.7% of misassigned cells are still called some IT type. So the panel answers
    "is this an IT neuron" reliably and leaves only the layer number uncertain, which in
    Xenium is set by cortical depth rather than by transcript.

Deck matches ORBm_BMAp_Xenium_panel_funder_v3.pptx: 13.33x7.5in, Calibri, same palette,
same three-column flow on slide 1 and same per-region bar charts on the populations slide.
Every figure is native PowerPoint shapes - zero images - so the whole deck stays editable.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SRC = DL / "FINAL_Xenium_panel_ORBm_BMAp_297genes.xlsx"
XLSX = DL / "FINAL_Xenium_panel_ORBm_BMAp_297_FINAL_v6.xlsx"
PPTX = DL / "ORBm_BMAp_Xenium_panel_297_FINAL_v6.pptx"
ONEPG = DL / "ORBm_BMAp_297_gene_list_ONE_PAGE_v6.pptx"

NAVY, BLUE, RED, GREEN = "1D4E89", "2A6F97", "C44536", "6B7C6A"
GREY, DARK, CREAM, LIGHT, BORDER = "5B6472", "1F2937", "F4F1EA", "EAF2F8", "B8B2A8"
NSL = 7
FOOT = "ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {}/" + str(NSL)

RECALL = {
    "007 L2/3 IT CTX Glut": 0.925, "006 L4/5 IT CTX Glut": 0.881,
    "005 L5 IT CTX Glut": 0.694, "022 L5 ET CTX Glut": 0.958,
    "032 L5 NP CTX Glut": 0.986, "030 L6 CT CTX Glut": 0.928,
    "029 L6b CTX Glut": 0.928, "004 L6 IT CTX Glut": 0.708,
    "052 Pvalb Gaba": 0.964, "053 Sst Gaba": 0.939, "046 Vip Gaba": 0.950,
    "049 Lamp5 Gaba": 0.958, "012 MEA Slc17a7 Glut": 0.994,
    "113 MEA-COA-BMA Ccdc42 Glut": 0.944, "120 MEA Otp Foxp2 Glut": 0.986,
    "121 MEA-BST Otp Zic2 Glut": 0.931, "119 SI-MA-LPO-LHA Skor1 Glut": 0.981,
    "073 MEA-BST Sox6 Gaba": 0.914, "074 MEA-BST Lhx6 Sp9 Gaba": 0.925,
    "082 CEA-BST Ebf1 Pdyn Gaba": 0.953,
}
CATS = [
    ("Cell identity, subtype and region", 135, NAVY),
    ("Morphine-dependence state", 46, RED),
    ("Druggable receptor map", 42, BLUE),
    ("Neuronal plasticity", 30, GREEN),
    ("Activity and immediate-early", 19, RED),
    ("Transcription factors", 13, NAVY),
    ("Circadian", 10, BLUE),
    ("Genetic-tag reporters", 2, GREEN),
]


# --------------------------------------------------------------- shape helpers
def tb(sl, l, t, w, h, text, size, *, bold=False, color=DARK,
       align=PP_ALIGN.LEFT, space=0, anchor=None):
    x = sl.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    f = x.text_frame
    f.word_wrap = True
    f.margin_left = f.margin_right = f.margin_top = f.margin_bottom = 0
    if anchor:
        f.vertical_anchor = anchor
    for i, ln in enumerate(str(text).split("\n")):
        p = f.paragraphs[0] if i == 0 else f.add_paragraph()
        p.alignment = align
        if space:
            p.space_after = Pt(space)
        r = p.add_run()
        r.text = ln
        r.font.name = "Calibri"
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = RGBColor.from_string(color)
    return x


def box(sl, l, t, w, h, *, fill=CREAM, line=NAVY, lw=1.25, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = sl.shapes.add_shape(shape, Inches(l), Inches(t), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(fill)
    s.line.color.rgb = RGBColor.from_string(line)
    s.line.width = Pt(lw)
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def bar(sl, l, t, w, h, *, fill):
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(fill)
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def line(sl, x1, y1, x2, y2, *, color=BLUE, lw=1.25):
    c = sl.shapes.add_connector(2, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = RGBColor.from_string(color)
    c.line.width = Pt(lw)
    return c


def head(sl, n, title, sub, *, color=NAVY, backup=False):
    tb(sl, 0.40, 0.18, 12.50, 0.42, title, 24, bold=True, color=color)
    tb(sl, 0.40, 0.58, 12.50, 0.34, sub, 12.5, color=GREY)
    tb(sl, 0.40, 7.18, 12.50, 0.24,
       ("BACKUP  -  " if backup else "") + FOOT.format(n), 11, color=GREY)


def tile(sl, l, t, big, small, color, *, w=2.95, h=1.12, fs=26, ss=11.5):
    box(sl, l, t, w, h, fill=CREAM, line=color)
    tb(sl, l + 0.12, t + 0.04, w - 0.22, h * 0.46, big, fs, bold=True, color=color)
    tb(sl, l + 0.12, t + h * 0.50, w - 0.22, h * 0.46, small, ss, color=GREY)


def capsule(sl, l, t, w, h, n, title, color, body=None):
    box(sl, l, t, w, h, fill="FFFFFF", line=color, lw=1.5)
    o = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(l + 0.16), Inches(t + (h - 0.34) / 2),
                            Inches(0.34), Inches(0.34))
    o.fill.solid()
    o.fill.fore_color.rgb = RGBColor.from_string(color)
    o.line.fill.background()
    o.shadow.inherit = False
    tb(sl, l + 0.17, t + (h - 0.34) / 2 + 0.04, 0.33, 0.30, n, 14, bold=True,
       color="FFFFFF", align=PP_ALIGN.CENTER)
    if body:
        tb(sl, l + 0.60, t + 0.12, w - 0.76, 0.32, title, 12.5, bold=True, color=color)
        tb(sl, l + 0.60, t + 0.44, w - 0.76, h - 0.56, body, 10.5, color=DARK)
    else:
        tb(sl, l + 0.60, t, w - 0.76, h, title, 12.5, bold=True, color=color,
           anchor=MSO_ANCHOR.MIDDLE)


# --------------------------------------------------------------- deck
def build_deck(anchors: dict) -> None:
    p = Presentation()
    p.slide_width, p.slide_height = Inches(13.333), Inches(7.5)
    bl = p.slide_layouts[6]

    # ============ 1  three-column selection flow
    s = p.slides.add_slide(bl)
    head(s, 1, "How the gene panel was selected",
         "Every slot had to be earned against measured data. Four rules decided which "
         "genes earned one, and a genome-wide sweep confirmed nothing was missed.")
    tb(s, 0.40, 1.00, 3.60, 0.26, "WHERE THE CANDIDATES CAME FROM", 11, bold=True,
       color=NAVY, align=PP_ALIGN.CENTER)
    tb(s, 4.60, 1.00, 4.20, 0.26, "FOUR DECISION RULES", 11, bold=True, color=NAVY,
       align=PP_ALIGN.CENTER)
    tb(s, 9.40, 1.00, 3.53, 0.26, "WHAT WE ORDER", 11, bold=True, color=NAVY,
       align=PP_ALIGN.CENTER)

    srcs = [
        ("OUR MARKER SCREEN", NAVY, "Allen Brain Cell Atlas, re-scored in these two\n"
         "regions only. Cell-type and subtype markers.", "32,285 screened", "179 kept"),
        ("GENOME-WIDE GPCR + TF", BLUE, "Every curated mouse receptor and transcription\n"
         "factor, scored here to prove the set is complete.", "1,747 screened", "58 kept"),
        ("JESSE NIEHAUS", RED, "Morphine-dependence gene expression in\n"
         "orbitofrontal / prefrontal cortex.", "431 screened", "50 kept"),
        ("BERG & SCHERRER", GREEN, "Published amygdala spatial panel\n(GSE283418).",
         "98 screened", "10 kept"),
    ]
    for i, (t, c, body, scr, kept) in enumerate(srcs):
        y = 1.34 + i * 1.06
        box(s, 0.40, y, 3.60, 0.96, fill=CREAM, line=c, lw=1.25)
        bar(s, 0.40, y, 3.60, 0.28, fill=c)
        tb(s, 0.52, y + 0.03, 3.36, 0.22, t, 10.5, bold=True, color="FFFFFF",
           align=PP_ALIGN.CENTER)
        tb(s, 0.52, y + 0.32, 3.36, 0.32, body.replace("\n", " "), 9, color=DARK)
        tb(s, 0.52, y + 0.68, 1.60, 0.22, scr, 10, bold=True, color=c)
        tb(s, 2.30, y + 0.68, 1.58, 0.22, kept, 10, bold=True, color=GREY,
           align=PP_ALIGN.RIGHT)
        line(s, 4.00, y + 0.48, 4.60, 2.30 + i * 0.02, color=c, lw=1.0)

    rules = [
        ("1", "Does it identify the cell type?", NAVY),
        ("2", "Is the receptor or factor really expressed here?", BLUE),
        ("3", "Does it report the morphine-dependent state?", RED),
        ("4", "Will the instrument actually detect it?", GREEN),
    ]
    for i, (n, t, c) in enumerate(rules):
        capsule(s, 4.60, 1.34 + i * 0.92, 4.20, 0.78, n, t, c)
    line(s, 8.80, 2.70, 9.40, 3.10, color=NAVY, lw=1.25)

    box(s, 9.40, 1.34, 3.53, 4.06, fill=LIGHT, line=NAVY, lw=1.75)
    tb(s, 9.52, 1.48, 3.29, 0.28, "FINAL PANEL", 12.5, bold=True, color=NAVY,
       align=PP_ALIGN.CENTER)
    tb(s, 9.52, 1.80, 3.29, 0.90, "297", 54, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    tb(s, 9.52, 2.72, 3.29, 0.26, "genes on one section", 11, color=GREY,
       align=PP_ALIGN.CENTER)
    bar(s, 9.70, 3.06, 2.93, 0.02, fill=BORDER)
    for i, (lab, n, c) in enumerate(CATS[:5]):
        tb(s, 9.52, 3.20 + i * 0.30, 2.50, 0.26, lab, 10, color=DARK)
        tb(s, 12.10, 3.20 + i * 0.30, 0.70, 0.26, str(n), 10, bold=True, color=c,
           align=PP_ALIGN.RIGHT)
    bar(s, 9.70, 4.76, 2.93, 0.02, fill=BORDER)
    tb(s, 9.52, 4.88, 3.29, 0.44,
       "Standalone panel - every gene\nis a probe we order", 10.5, bold=True, color=RED,
       align=PP_ALIGN.CENTER)

    box(s, 0.40, 5.64, 12.53, 1.26, fill=LIGHT, line=NAVY)
    tb(s, 0.62, 5.74, 12.10, 0.26, "Every rule is a measurement in the Allen Brain Cell "
       "Atlas, restricted to these two regions", 12.5, bold=True, color=NAVY)
    for i, (a, b) in enumerate([
            ("226,886", "cells re-analysed"), ("79", "cell types present"),
            ("20", "target populations"), ("1,747", "GPCRs + TFs swept"),
            ("0.922", "mean recall, 20 types")]):
        x = 0.70 + i * 2.48
        tb(s, x, 6.06, 2.30, 0.36, a, 18, bold=True, color=NAVY)
        tb(s, x, 6.46, 2.30, 0.26, b, 10, color=GREY)

    # ============ 2  in vs out
    s = p.slides.add_slide(bl)
    head(s, 2, "Why a gene is in - and why a similar one is out",
         "Each rule is a measurement with a cutoff. For every rule there is a gene that "
         "passed and a better-known gene that failed.", color=RED)
    cards = [
        ("1", "Does it identify the cell type?", NAVY,
         "50% of its own population, and a clear margin over the other target types.",
         "IN     Tnnc1   53% of L4/5 IT, +22pp - the best marker for that type anywhere "
         "in the transcriptome",
         "OUT   Scnn1a   the classic L4 marker, but 1.8% here; it is really an ependymal gene"),
        ("2", "Is the receptor really expressed here?", BLUE,
         "50% of cells somewhere in these two regions.",
         "IN     Chrm1   M1 muscarinic, 98% of cells - previously only M2 was visible",
         "OUT   Adrb2   50.7%, and its peak is in macrophages rather than neurons"),
        ("3", "Does it report the morphine-dependent state?", RED,
         "Differential expression counted only in our 12 ORBm populations.",
         "IN     Per2   changes in 11 of 12 populations - the broadest gene in Jesse's data",
         "OUT   Hspa5   an ER-stress gene in 71 of 75 cell types; it can only report a "
         "global shift"),
        ("4", "Will the instrument detect it?", GREEN,
         "Sparse probes give sparse maps. Activity genes are exempt.",
         "IN     Cux2   95% of L2/3 IT - the paralog that actually works in this tissue",
         "OUT   Tcf4   expressed in all 75 cell types, never below 37%; separates nothing"),
    ]
    for i, (n, t, c, rule, yes, no) in enumerate(cards):
        x = 0.40 + (i % 2) * 6.36
        y = 1.02 + (i // 2) * 1.72
        box(s, x, y, 6.17, 1.60, fill="FFFFFF", line=c, lw=1.5)
        o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12),
                               Inches(0.34), Inches(0.34))
        o.fill.solid()
        o.fill.fore_color.rgb = RGBColor.from_string(c)
        o.line.fill.background()
        o.shadow.inherit = False
        tb(s, x + 0.15, y + 0.16, 0.33, 0.30, n, 14, bold=True, color="FFFFFF",
           align=PP_ALIGN.CENTER)
        tb(s, x + 0.56, y + 0.12, 5.47, 0.34, t, 13, bold=True, color=c)
        tb(s, x + 0.16, y + 0.50, 5.87, 0.30, rule, 10.5, color=GREY)
        tb(s, x + 0.16, y + 0.86, 5.87, 0.34, yes, 10.5, color=GREEN)
        tb(s, x + 0.16, y + 1.22, 5.87, 0.34, no, 10.5, color=RED)
    box(s, 0.40, 4.54, 12.53, 2.36, fill=LIGHT, line=NAVY)
    tb(s, 0.62, 4.66, 12.10, 0.28, "Ten widely cited published markers were re-tested here "
       "- four point the wrong way in these two regions", 13, bold=True, color=NAVY)
    tb(s, 0.62, 5.02, 5.95, 1.74,
       "Cux1, Scnn1a, Crym, Tcf4, Reln, Pax6, Tshz1, Cd36, Fst and Whrn are all standard "
       "layer or amygdala markers in the literature. Every one fails the identification "
       "rule when re-measured in orbitofrontal cortex and posterior basomedial amygdala.",
       11, color=DARK)
    tb(s, 6.85, 5.02, 5.95, 1.74,
       "Cd36, a published BMA marker, is highest in macrophages and only 28% in the BMA "
       "type it is meant to mark. Scnn1a is 1.8% in L4/5 and is really ependymal. Cux1 is "
       "higher in amygdala GABA (94%) than in L2/3 (72%). Tcf4 is in all 75 cell types. "
       "Taking any of the four on trust would have labelled the wrong cells.",
       11, color=DARK)

    # ============ 3  final panel
    s = p.slides.add_slide(bl)
    head(s, 3, "Final panel  -  297 genes, one section, two regions",
         "One shared standalone panel read from the same mouse on the same slide, so ORBm "
         "and BMAp are compared with no batch difference between them.", color=BLUE)
    for i, (big, small, c) in enumerate([
            ("297", "genes on the\nshared panel", NAVY),
            ("20 / 20", "target cell types\nidentified", BLUE),
            ("0.922", "mean recall across\nthose 20 types", GREEN),
            ("12 + 8", "populations in\nORBm  +  BMAp", RED)]):
        tile(s, 0.40 + i * 3.16, 1.02, big, small, c)
    tb(s, 0.40, 2.32, 7.05, 0.28, "What the 297 genes do", 13, bold=True, color=NAVY)
    mx = max(n for _, n, _ in CATS)
    for i, (lab, n, c) in enumerate(CATS):
        y = 2.68 + i * 0.40
        tb(s, 0.40, y, 2.86, 0.28, lab, 10.5, color=DARK)
        w = max(0.06, 3.10 * n / mx)
        bar(s, 3.34, y + 0.04, w, 0.20, fill=c)
        tb(s, 3.34 + w + 0.08, y - 0.01, 0.60, 0.28, str(n), 10.5, bold=True, color=c)
    box(s, 7.75, 2.32, 5.18, 3.56, fill=CREAM, line=BORDER, lw=1.0)
    tb(s, 7.95, 2.44, 4.80, 0.28, "What each cell will tell us", 13, bold=True, color=NAVY)
    for i, (t, c, body) in enumerate([
            ("Identity", NAVY, "Which of the 20 populations it is - cortical layer, "
             "interneuron class, or amygdala subtype."),
            ("TRAP label", GREEN, "Whether it was active during the morphine window. "
             "tdTomato and iCre read the genetic tag directly."),
            ("Activity now", BLUE, "Whether it is active at fixation - Fos, Arc, Npas4 "
             "and the wider immediate-early set."),
            ("Molecular state", RED, "Its receptors, transcription factors, plasticity "
             "genes and morphine-response genes.")]):
        y = 2.80 + i * 0.76
        tb(s, 7.95, y, 4.80, 0.26, t, 12, bold=True, color=c)
        tb(s, 7.95, y + 0.26, 4.80, 0.48, body, 10.5, color=DARK)
    box(s, 0.40, 5.98, 12.53, 0.92, fill=LIGHT, line=RED, lw=1.75)
    tb(s, 0.62, 6.08, 12.10, 0.28,
       "This is not a good list - it is the complete list for these two regions",
       13, bold=True, color=RED)
    tb(s, 0.62, 6.38, 12.10, 0.46,
       "Every mouse GPCR (426) and every mouse transcription factor (1,321) was scored "
       "here. No GPCR is missing. The only two transcription factors that came close are "
       "weaker duplicates of markers the panel already carries. There is no 298th gene "
       "that would add a receptor or a factor we cannot already see in these 20 cell types.",
       11, color=DARK)

    # ============ 4  the 20 populations, two bar charts
    s = p.slides.add_slide(bl)
    head(s, 4, "The 20 populations we must tell apart",
         "The target list comes from the Allen Brain Cell Atlas taxonomy: 12 populations "
         "in orbitofrontal cortex, 8 in posterior basomedial amygdala.", backup=True)
    for i, (big, small, c) in enumerate([
            ("12", "ORBm populations\n84,604 Allen cells", NAVY),
            ("8", "BMAp populations\n40,709 Allen cells", BLUE),
            ("125,313", "cells in the 20\ntarget populations", GREEN),
            ("3 - 28", "dedicated markers per\ntype, median 6", RED)]):
        tile(s, 0.40 + i * 3.16, 1.02, big, small, c)
    orb = [(a, v) for a, v in anchors.items() if v[0] == "ORBm"]
    bma = [(a, v) for a, v in anchors.items() if v[0] == "BMAp"]
    for col, (title, data, c) in enumerate([
            ("A.  ORBm  -  orbitofrontal cortex, medial", orb, NAVY),
            ("B.  BMAp  -  basomedial amygdala, posterior", bma, BLUE)]):
        x0 = 0.40 + col * 6.46
        tb(s, x0, 2.32, 6.10, 0.28, title, 12, bold=True, color=c)
        tb(s, x0, 2.58, 6.10, 0.24,
           f"{len(data)} populations,  {sum(v[1] for _, v in data):,} cells   |   "
           f"bar = cells, label = dedicated markers and recall", 9.5, color=GREY)
        mxc = max(v[1] for _, v in data)
        for i, (a, v) in enumerate(data):
            y = 2.86 + i * 0.285
            nm = a.split(" ", 1)[1] if " " in a else a
            tb(s, x0, y, 2.06, 0.24, nm[:30], 9, color=DARK, align=PP_ALIGN.RIGHT)
            w = max(0.05, 2.30 * v[1] / mxc)
            bar(s, x0 + 2.14, y + 0.035, w, 0.175, fill=c)
            r = RECALL.get(a)
            tb(s, x0 + 2.14 + w + 0.07, y, 1.90, 0.24,
               f"{v[1]/1000:.1f}k   {v[2]} marker{'s' if v[2] != 1 else ''}"
               + (f"   r={r:.2f}" if r else ""), 9, color=GREY)
    box(s, 0.40, 6.44, 12.53, 0.46, fill=CREAM, line=BORDER, lw=1.0)
    tb(s, 0.62, 6.52, 12.10, 0.32,
       "Every one of the 20 has 3 to 28 dedicated markers, median 6, measured against the "
       "other targets IN THE SAME REGION - ORBm and BMAp sit at different places on the "
       "slide and are separated by coordinate before any gene is read. The thinnest is 073 "
       "MEA-BST Sox6 Gaba with 3 (Prox1 +35, Dlx1 +31, Chn2 +24). Note that Sox6 itself is "
       "NOT one of them: it marks the whole MGE interneuron lineage, not this one type.",
       10.5, color=DARK)

    # ============ 5  cohort
    s = p.slides.add_slide(bl)
    head(s, 5, "Tissue: the TRAP + Xenium post window",
         "TRAP mice (Fos2A-iCreER x Rosa26-LSL-tdTomato). Tamoxifen opens the labelling "
         "window during morphine; Xenium is run on the post window.", backup=True)
    for i, (big, small, c) in enumerate([
            ("2", "active\nmorphine", RED), ("2", "passive\nmorphine", BLUE),
            ("4", "mice in the\nfirst run", NAVY),
            ("3 + 3", "if a third per group\nis required", GREEN)]):
        tile(s, 0.40 + i * 3.16, 1.02, big, small, c)
    box(s, 0.40, 2.32, 6.17, 2.22, fill="FFFFFF", line=RED, lw=1.5)
    tb(s, 0.62, 2.44, 5.75, 0.30, "Active morphine  -  2 mice", 13, bold=True, color=RED)
    tb(s, 0.62, 2.80, 5.75, 1.60,
       "Self-administering animals. The TRAP window captures the cells active during "
       "drug-taking, so tdTomato marks the ensemble engaged by the animal's own behaviour "
       "rather than by drug exposure alone.", 11, color=DARK)
    box(s, 6.76, 2.32, 6.17, 2.22, fill="FFFFFF", line=BLUE, lw=1.5)
    tb(s, 6.98, 2.44, 5.75, 0.30, "Passive morphine  -  2 mice", 13, bold=True, color=BLUE)
    tb(s, 6.98, 2.80, 5.75, 1.60,
       "Yoked animals receiving the same drug on the same schedule without controlling "
       "delivery. Subtracting this group separates what is specific to volitional "
       "drug-taking from pharmacology alone.", 11, color=DARK)
    box(s, 0.40, 4.66, 12.53, 2.24, fill=LIGHT, line=NAVY)
    tb(s, 0.62, 4.78, 12.10, 0.28, "Two points to confirm before ordering", 13,
       bold=True, color=NAVY)
    tb(s, 0.62, 5.12, 5.95, 1.62,
       "Reporter line. Ai19 is not a documented tdTomato reporter. The "
       "Rosa26-CAG-LSL-tdTomato lines are Ai9 (JAX 007909) and Ai14 (JAX 007908 / "
       "007914), and TRAP2 x Ai14 is the standard published cross. The probe targets the "
       "tdTomato coding sequence, so a line carrying a different fluorophore would read "
       "nothing at all.", 11, color=DARK)
    tb(s, 6.85, 5.12, 5.95, 1.62,
       "Group size. Four mice give a first read on whether the active and passive "
       "ensembles differ in composition. A third animal per group would be needed to put "
       "a confidence interval on the size of that difference, so the design is written to "
       "extend to 3 + 3 without any change to the panel.", 11, color=DARK)

    # ============ 6  evidence
    s = p.slides.add_slide(bl)
    head(s, 6, "The list rests on a full re-analysis of the reference atlas",
         "No gene was taken on a paper's word. Every candidate was re-scored in the Allen "
         "atlas, restricted to these two regions.", backup=True)
    # 15 tiles, 3 rows x 5. Row 1 = scale of the re-analysis, row 2 = what was tested,
    # row 3 = what came out of it.
    stats = [
        ("226,886", "single cells scored across\nthe two target regions", NAVY),
        ("79", "cell types profiled,\nnot only the 20 targets", BLUE),
        ("32,285", "genes screened for\ncell-type markers", GREEN),
        ("23,305", "gene x cell-type abundance\nand specificity measurements", RED),
        ("27,730", "pairwise tests: can gene X\nseparate type A from type B?", NAVY),
        ("1,747", "receptors and factors\nswept genome-wide", BLUE),
        ("426", "receptors evaluated one by\none, 153 expressed here", GREEN),
        ("94 / 94", "same-region type pairs\nseparable at 20 points or more", RED),
        ("49", "panel receptors tiered specific,\nintermediate or universal", NAVY),
        ("13", "documented sources,\n9 of them with a DOI", BLUE),
        ("297", "genes ordered, each with\na measured reason", GREEN),
        ("0.922", "mean recall across the\n20 target cell types", RED),
        ("147", "dedicated marker-to-type\nassignments, 3 to 28 each", NAVY),
        ("59", "FDA-approved drugs mapped\nto panel receptors (IUPHAR)", BLUE),
        ("10", "published markers\ntested and rejected", GREEN),
    ]
    for i, (big, small, c) in enumerate(stats):
        tile(s, 0.40 + (i % 5) * 2.538, 1.00 + (i // 5) * 1.10, big, small, c,
             w=2.378, h=1.00, fs=19, ss=9)
    box(s, 0.40, 4.32, 12.53, 2.58, fill=CREAM, line=BORDER, lw=1.0)
    tb(s, 0.62, 4.42, 12.10, 0.28, "What that analysis produced, in order", 13,
       bold=True, color=NAVY)
    steps = [
        ("1", "Region-restricted expression matrices", NAVY,
         "ORBm and BMAp cells were pulled out of the whole-brain atlas, so every "
         "abundance and specificity number describes these two regions, not a "
         "brain-wide average."),
        ("2", "Per-population marker ranking", BLUE,
         "For each of the 20 targets, every candidate was ranked by how much of that "
         "population expresses it and how tightly it is restricted to it."),
        ("3", "Separability, tested two independent ways", GREEN,
         "All 94 same-region pairs of target types are separable - every pair has a "
         "panel gene differing by 20 points or more. And on held-out cells a classifier "
         "using only these genes recovers all 20 types, mean recall 0.922."),
        ("4", "Receptor sweep and drug-target layer", RED,
         "All 426 mouse GPCRs and 1,321 transcription factors were scored here and none "
         "is missing. Receptors were then tiered by specificity - 19 specific, 19 "
         "intermediate, 11 universal - and cross-referenced to IUPHAR."),
    ]
    for i, (n, t, c, body) in enumerate(steps):
        x = 0.62 + (i % 2) * 6.30
        y = 4.78 + (i // 2) * 1.06
        tb(s, x, y, 0.28, 0.24, n + ".", 11, bold=True, color=c)
        tb(s, x + 0.30, y, 5.60, 0.24, t, 11, bold=True, color=c)
        tb(s, x + 0.30, y + 0.26, 5.62, 0.72, body, 10, color=DARK)

    # ============ 7  what "covered" means - the comparison that settles it
    s = p.slides.add_slide(bl)
    head(s, 7, 'Four ways to ask "is this cell type covered?" - and which answer to use',
         "The same panel scores anywhere from 4 of 20 to 20 of 20 depending on what you "
         "compare against. Three of these four tests are the wrong question.", backup=True)
    cols = [(0.40, 3.15, "THE TEST"), (3.61, 2.75, "COMPARED AGAINST"),
            (6.42, 2.55, "ANSWER"), (9.03, 3.90, "SHOULD WE QUOTE IT?")]
    for x, w, t in cols:
        bar(s, x, 1.02, w, 0.30, fill=NAVY)
        tb(s, x + 0.10, 1.06, w - 0.20, 0.24, t, 10, bold=True, color="FFFFFF")
    rows = [
        ("One gene at 70% of the type\nwith a 20-point margin",
         "all 74 other cell types\nin the section",
         "4 of 20", RED,
         "NO. It counts striatal, hypothalamic and glial populations as rivals, "
         "but those are already excluded by coordinate and by the neuron / "
         "glut / GABA gate before any type is called. This is the number I "
         "quoted first, and it was wrong."),
        ("One gene at 50% of the type\nwith a 10-point margin",
         "the other 19 target\ntypes, both regions",
         "20 of 20\n1 to 11 each", BLUE,
         "Closer, but still too strict. ORBm and BMAp sit at different places on "
         "the slide, so a BMAp type never has to be told apart from an ORBm type "
         "by transcript."),
        ("One gene at 50% of the type\nwith a 10-point margin",
         "the other targets in the\nSAME region only",
         "20 of 20\n3 to 28 each", GREEN,
         "YES, for the question \"does this type have its own marker?\" Median 6 "
         "markers per type. Thinnest is 073 MEA-BST Sox6 Gaba with 3 - Prox1, "
         "Dlx1, Chn2. Listed per type in MARKERS_PER_TYPE."),
        ("A classifier using only the\n297 genes, on held-out cells",
         "all 75 cell types at\nonce, no gating",
         "20 of 20\nmean recall 0.922", NAVY,
         "YES, and this is the headline. It is how cell types are actually "
         "called - from gene combinations, not one marker at a time. 18 of the "
         "20 are above 0.85."),
    ]
    for i, (test, against, ans, c, verdict) in enumerate(rows):
        y = 1.36 + i * 1.28
        box(s, 0.40, y, 12.53, 1.20, fill="FFFFFF" if i % 2 else CREAM,
            line=BORDER, lw=0.75, shape=MSO_SHAPE.RECTANGLE)
        tb(s, 0.50, y + 0.12, 3.00, 0.60, test.replace("\n", " "), 10.5, color=DARK)
        tb(s, 3.71, y + 0.12, 2.60, 0.60, against.replace("\n", " "), 10.5, color=GREY)
        tb(s, 6.52, y + 0.10, 2.40, 0.70, ans.replace("\n", "  "), 13, bold=True, color=c)
        tb(s, 9.13, y + 0.10, 3.72, 1.00, verdict, 9.5, color=DARK)
        bar(s, 0.40, y, 0.05, 1.20, fill=c)
    box(s, 0.40, 6.50, 12.53, 0.44, fill=LIGHT, line=NAVY, lw=1.25)
    tb(s, 0.62, 6.59, 12.10, 0.28,
       "One sentence for the paper or the report:  all 20 target cell types are recovered "
       "from held-out cells with a mean recall of 0.922, and each has 3 to 28 dedicated "
       "markers of its own.", 11, bold=True, color=NAVY)

    p.save(PPTX)
    npic = sum(1 for sl in p.slides for sh in sl.shapes if sh.shape_type == 13)
    print(f"wrote {PPTX.name}: {len(p.slides)} slides, {npic} pictures")


# --------------------------------------------------------------- one-page gene list
def build_onepager(sh: pd.DataFrame) -> None:
    p = Presentation()
    p.slide_width, p.slide_height = Inches(13.333), Inches(7.5)
    s = p.slides.add_slide(p.slide_layouts[6])
    tb(s, 0.34, 0.16, 12.60, 0.34, "ORBm + BMAp Xenium panel  -  all 297 genes to order",
       19, bold=True, color=NAVY)
    tb(s, 0.34, 0.50, 12.60, 0.24,
       "One shared standalone custom panel, both regions on the same slide. Grouped by "
       "what each gene is for. Full evidence per gene is in SHARED_PANEL_ORDER of the "
       "accompanying Excel.", 10, color=GREY)

    def cat_of(b: str) -> str:
        b = str(b).lower()
        if "reporter_transgene" in b:
            return "Genetic-tag reporters"
        if "circadian" in b:
            return "Circadian"
        if "ieg" in b or "activity" in b:
            return "Activity / immediate-early"
        if "morphine" in b:
            return "Morphine-dependence state"
        if "gpcr" in b or "receptor" in b:
            return "Druggable receptor map"
        if "plasticity" in b:
            return "Neuronal plasticity"
        if "tf_identity" in b:
            return "Transcription factors"
        return "Cell identity, subtype and region"

    ORDER = ["Genetic-tag reporters", "Cell identity, subtype and region",
             "Druggable receptor map", "Morphine-dependence state",
             "Neuronal plasticity", "Activity / immediate-early",
             "Transcription factors", "Circadian"]
    COLOR = {"Genetic-tag reporters": GREEN, "Cell identity, subtype and region": NAVY,
             "Druggable receptor map": BLUE, "Morphine-dependence state": RED,
             "Neuronal plasticity": GREEN, "Activity / immediate-early": RED,
             "Transcription factors": NAVY, "Circadian": BLUE}
    sh = sh.copy()
    sh["cat"] = sh.block.map(cat_of)
    entries = []
    for c in ORDER:
        g = sorted(sh.loc[sh.cat == c, "gene"].astype(str))
        entries.append(("H", f"{c}  ({len(g)})", COLOR[c]))
        entries += [("G", x, DARK) for x in g]
        entries.append(("S", "", DARK))
    NC, ROWS = 8, 41
    cw, x0, y0, rh = 1.565, 0.34, 0.86, 0.148
    col = 0
    row = 0
    for kind, txt, c in entries:
        if row >= ROWS:
            col += 1
            row = 0
        if col >= NC:
            break
        x = x0 + col * cw
        y = y0 + row * rh
        if kind == "H":
            if row > ROWS - 3:
                col += 1
                row = 0
                x, y = x0 + col * cw, y0
            bar(s, x, y + 0.015, cw - 0.10, 0.125, fill=c)
            tb(s, x + 0.04, y + 0.012, cw - 0.18, 0.13, txt, 6.8, bold=True,
               color="FFFFFF")
        elif kind == "G":
            tb(s, x + 0.04, y, cw - 0.12, 0.14, txt, 7.8, color=c)
        row += 1
    tb(s, 0.34, 7.16, 12.60, 0.24,
       "297 genes  |  20 of 20 target cell types identified, mean held-out recall 0.922  |  "
       "all 426 mouse GPCRs and 1,321 transcription factors screened: none missing  |  "
       "Allen WMB-10X, 226,886 cells in PL-ILA-ORB + sAMY", 9, color=GREY)
    p.save(ONEPG)
    print(f"wrote {ONEPG.name}: 1 slide, "
          f"{sum(1 for sh_ in s.shapes if sh_.shape_type == 13)} pictures")


# --------------------------------------------------------------- Excel
def build_excel(anchors: dict) -> None:
    shutil.copy2(SRC, XLSX)
    wb = load_workbook(XLSX)
    ws = wb["FOR_MarkGreg"]
    ws.delete_rows(1, ws.max_row)
    rows = [
        ("WHAT TO OPEN FIRST",
         "This sheet, then SHARED_PANEL_ORDER - that is the list to order. One shared "
         "standalone panel of 297 genes, both regions read from the same mouse on the same "
         "slide. The 10x Mouse Brain base panel is NOT included, so every gene here is a "
         "probe we are ordering. A one-page version of the list is in the accompanying "
         "PowerPoint if you just want to scan the gene names."),
        ("WHAT IS NEW IN THIS VERSION",
         "The gene list is unchanged - the same 297 genes. What is new is the last piece of "
         "evidence: a genome-wide screen of every mouse GPCR and every transcription "
         "factor, in the GPCR_TF_SCREEN tab. Before this, the receptor and TF blocks came "
         "from collaborator DEG lists and a drug-target table, so they could be defended "
         "gene by gene but not as a complete set. Now they can."),
        ("RESULT OF THAT SCREEN",
         "426 mouse GPCRs and 1,321 transcription factors were scored in PL-ILA-ORB and "
         "sAMY. GPCRs: ZERO missing - no GPCR in the mouse genome reaches 50% of cells in "
         "one of our 20 target cell types with a 10-point margin and is absent from this "
         "panel, and none of the 49 GPCRs we carry is an empty map. TFs: only 2 candidates "
         "(Bcl6, Lhx5), both weaker duplicates of markers those cell types already have, "
         "so both are correctly excluded."),
        ("HOW WELL CELL TYPES ARE CALLED",
         "By gene combinations, not one marker per type. Measured on held-out cells: all 20 "
         "target cell types are recovered, mean recall 0.922, and 18 of the 20 are at or "
         "above 0.85. Per-type recall is in the ANCHOR_COVERAGE tab. Each target type also "
         "has 3 to 28 dedicated markers (median 6), measured against the other target types "
         "in the SAME region - ORBm and BMAp are separated by coordinate on the slide, so a "
         "BMAp type never has to be told apart from an ORBm type by transcript. On top of "
         "that, 91 to 127 genes are expressed above 50% in each type. Every marker and its "
         "margin is listed in the MARKERS_PER_TYPE tab."),
        ("A NOTE ON CELL-TYPE NAMES - THEY CAN MISLEAD",
         "An Allen cell-type name tells you a gene is expressed there, not that it is "
         "exclusive to it. 073 MEA-BST Sox6 Gaba is the clearest case: Sox6 is 58% in that "
         "type but 95% in Pvalb Gaba and 90% in Sst Gaba, because Sox6 marks the whole "
         "MGE interneuron lineage rather than this one type. Sox6 is on the panel and is "
         "useful as a lineage gene, but the dedicated separators for 073 are Prox1 (+35pp), "
         "Dlx1 (+31pp) and Chn2 (+24pp). The same trap applies to Cd36, Scnn1a and Cux1."),
        ("THE TWO WEAKER TYPES, STATED PLAINLY",
         "004 L6 IT (recall 0.708) and 005 L5 IT (0.694) are the two below 0.85. Their "
         "errors are almost entirely internal to the IT family: 99.4% and 99.7% of "
         "misassigned cells are still called an IT type, and only 1 cell in 360 leaves IT "
         "altogether. IT neurons form a continuous gradient across cortical layers, so no "
         "gene in the 32,285-gene atlas separates them cleanly. In Xenium the layer is set "
         "by cortical depth rather than by transcript, so this is not a practical limit."),
        ("TABS, IN ORDER OF USE",
         "SHARED_PANEL_ORDER = the 297 genes to order, with measured evidence for each. "
         "ORBm_ORDER / BMAp_ORDER = the same genes annotated per region. ANCHOR_COVERAGE = "
         "each of the 20 target cell types, the gene that names it, and its held-out "
         "recall. GPCR_TF_SCREEN = the genome-wide completeness check. SOURCES = where "
         "every gene came from."),
        ("WHAT WAS DELIBERATELY LEFT OUT",
         "Ten widely cited published markers were tested here and rejected: Cux1, Scnn1a, "
         "Crym, Tcf4, Reln, Pax6, Tshz1, Cd36, Fst, Whrn. Four point the wrong way in "
         "these regions - Cd36 is highest in macrophages and only 28% in the BMA type it "
         "is meant to mark, Scnn1a is 1.8% in L4/5 and is really ependymal, Cux1 is higher "
         "in amygdala GABA (94%) than in L2/3 (72%), and Tcf4 is expressed in all 75 cell "
         "types. No sex-identity genes, per earlier instruction."),
        ("TISSUE AND COHORT",
         "TRAP mice (Fos2A-iCreER x Rosa26-LSL-tdTomato), 2 active and 2 passive morphine, "
         "extending to 3 + 3 if a third per group is needed. Please confirm the reporter "
         "stock number: Ai19 is not a documented tdTomato line - the tdTomato reporters "
         "are Ai9 (JAX 007909) and Ai14 (JAX 007908 / 007914), and TRAP2 x Ai14 is the "
         "standard cross. The probe targets the tdTomato coding sequence, so a line "
         "carrying a different fluorophore would read nothing."),
    ]
    ws.cell(row=1, column=1, value="item").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=1, column=2, value="detail").font = Font(bold=True, color="FFFFFF")
    for c in (1, 2):
        ws.cell(row=1, column=c).fill = PatternFill("solid", fgColor=NAVY)
    for i, (a, b) in enumerate(rows, start=2):
        ws.cell(row=i, column=1, value=a).font = Font(bold=True, color=NAVY)
        ws.cell(row=i, column=2, value=b)
        for c in (1, 2):
            ws.cell(row=i, column=c).alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[i].height = 84
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 118

    ac = wb["ANCHOR_COVERAGE"]
    hdr = [c.value for c in ac[1]]
    gc = hdr.index("allen_subclass_anchor") + 1
    for col, name in ((len(hdr) + 1, "held_out_recall"),
                      (len(hdr) + 2, "n_dedicated_markers_vs_other_19")):
        ac.cell(row=1, column=col, value=name).font = Font(bold=True, color="FFFFFF")
        ac.cell(row=1, column=col).fill = PatternFill("solid", fgColor=NAVY)
    for r in range(2, ac.max_row + 1):
        a = str(ac.cell(row=r, column=gc).value)
        if a in RECALL:
            ac.cell(row=r, column=len(hdr) + 1, value=RECALL[a])
        if a in anchors:
            ac.cell(row=r, column=len(hdr) + 2, value=anchors[a][2])
    wb.save(XLSX)

    gp = pd.read_excel(O / "GENOMEWIDE_GPCR_TF_SCREEN.xlsx", "gpcr_all")
    tf = pd.read_excel(O / "GENOMEWIDE_GPCR_TF_SCREEN.xlsx", "tf_all")
    summ = pd.DataFrame([
        {"class": "GPCR", "screened": len(gp), "found_in_atlas": int(gp.in_atlas.sum()),
         "expressed_ge50pct_somewhere": int(gp.expressed.fillna(False).sum()),
         "on_the_297_panel": int(gp.on_panel_297.fillna(False).sum()),
         "on_panel_but_empty_map": 0, "missing_and_strong_in_a_TARGET_type": 0,
         "verdict": "COMPLETE. No mouse GPCR reaches 50% in one of the 20 target cell "
                    "types with a >=10pp margin and is absent from this panel."},
        {"class": "Transcription factor", "screened": len(tf),
         "found_in_atlas": int(tf.in_atlas.sum()),
         "expressed_ge50pct_somewhere": int(tf.expressed.fillna(False).sum()),
         "on_the_297_panel": int(tf.on_panel_297.fillna(False).sum()),
         "on_panel_but_empty_map": 1, "missing_and_strong_in_a_TARGET_type": 2,
         "verdict": "COMPLETE after the no-redundant-marker rule. Bcl6 (+11.8pp, 022 L5 "
                    "ET) and Lhx5 (+10.5pp, 119 Skor1) are weaker second markers for types "
                    "that already carry Npr3 +20.4pp and Skor1 +51.4pp. Npas4 at 45% is "
                    "the activity-gene exemption: the atlas is resting tissue."},
    ])
    md = pd.read_excel(O / "_marker_detail_297.xlsx")
    with pd.ExcelWriter(XLSX, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as w:
        summ.to_excel(w, "GPCR_TF_SCREEN", index=False)
        md.to_excel(w, "MARKERS_PER_TYPE", index=False)
    print(f"wrote {XLSX.name}")


if __name__ == "__main__":
    anchors = {k: tuple(v) for k, v in
               json.loads((O / "_anchor_markers_297.json").read_text()).items()}
    sh = pd.read_excel(SRC, "SHARED_PANEL_ORDER")
    build_excel(anchors)
    build_deck(anchors)
    build_onepager(sh)
