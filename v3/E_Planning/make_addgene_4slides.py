"""English 3-slide deck: Dan + Jesse (why considered) and the final add list."""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path.home() / "Downloads"
FONT = "Calibri"

NAVY = RGBColor(0x1D, 0x4E, 0x89)
TEAL = RGBColor(0x2A, 0x6F, 0x97)
RUST = RGBColor(0xC4, 0x45, 0x36)
GOLD = RGBColor(0xB0, 0x89, 0x68)
INK = RGBColor(0x2C, 0x2C, 0x2C)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = RGBColor(0xF4, 0xF1, 0xEA)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def set_run(p, text, size=16, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = FONT
    return r


def add_bar(slide, color=NAVY):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.1))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()


def add_footer(slide, n, total=3):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(7.18), Inches(12.4), Inches(0.26))
    set_run(
        box.text_frame.paragraphs[0],
        f"Xenium ORBm + BMAp add-on  |  Dan GSE283418  ·  Jesse PL-ILA-ORB  ·  Allen WMB-10X  |  {n}/{total}",
        11,
        False,
        MUTED,
    )


def add_title(slide, text):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(0.22), Inches(12.4), Inches(0.44))
    set_run(box.text_frame.paragraphs[0], text, 26, True, NAVY)


def add_sub(slide, text):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(0.66), Inches(12.4), Inches(0.32))
    set_run(box.text_frame.paragraphs[0], text, 14, False, MUTED)


def card(slide, l, t, w, h, title, body, color=NAVY):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = WHITE
    sh.line.color.rgb = color
    head = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(0.4))
    head.fill.solid()
    head.fill.fore_color.rgb = color
    head.line.fill.background()
    hb = slide.shapes.add_textbox(Inches(l + 0.12), Inches(t + 0.06), Inches(w - 0.2), Inches(0.3))
    set_run(hb.text_frame.paragraphs[0], title, 13, True, WHITE)
    bb = slide.shapes.add_textbox(Inches(l + 0.14), Inches(t + 0.5), Inches(w - 0.28), Inches(h - 0.6))
    tf = bb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(body.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, line, 13, False, INK)


def add_table(slide, rows, left, top, width, height, col_w):
    table = slide.shapes.add_table(
        len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(height)
    ).table
    for i, w in enumerate(col_w):
        table.columns[i].width = Inches(w)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            set_run(cell.text_frame.paragraphs[0], str(val), 13 if i == 0 else 12, i == 0, WHITE if i == 0 else INK)
            cell.text_frame.word_wrap = True
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if i == 0 else (WHITE if i % 2 == 0 else PALE)


# ----- 1 Dan -----
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL)
add_title(s, "Dan  |  genes considered, and why")
add_sub(s, "GSE283418  ·  Berg / Scherrer  ·  Resolve 98-gene smFISH in amygdala  ·  re-scored in our Allen BMAp ROI")
card(
    s, 0.4, 1.1, 4.2, 5.7, "What the data are",
    "Not a cell-type atlas.\nA spatial 98-gene panel from\namygdala sections.\n\n38 / 98 were already on our\nshared 144 (Foxp2, Cartpt,\nPdyn, Oprm1, Slc17a7…).\n\nWe asked: which of the\nremaining genes are still\ninformative in our BMAp\nmapped cells?",
    TEAL,
)
card(
    s, 4.75, 1.1, 4.2, 5.7, "Why these 14 were considered",
    "They were missing from the\n144 and detectable in the\nAllen BMAp-mapped ROI.\n\nClosest to true BMAp\n  Lamb3   (113 Ccdc42)\n\nBMA / MEA VGLUT1 border\n  Cck  Col23a1  Slc29a4\n  Abca8a  Dnah5\n\nMEA / BST neighbors\n  Calcrl  Nos1  Oprl1\n  Gfra1  Sp8\n\nCEA / other  (weakest)\n  Syndig1l  Gabre  Tspan18",
    TEAL,
)
card(
    s, 9.1, 1.1, 3.8, 5.7, "Status",
    "Already added to\nMSGS111\nranks 145–158.\n\nThey do not redo\ncell-type ID.\nThey add amygdala\nspatial genes Dan\nalready uses.\n\nIf the 100-slot cap\nis hard: keep Lamb3\n+ the 012-border set;\ncut the CEA genes\nfirst.",
    GOLD,
)
add_footer(s, 1)

# ----- 2 Jesse -----
s = prs.slides.add_slide(BLANK)
add_bar(s)
add_title(s, "Jesse  |  genes considered, and why")
add_sub(s, "5-day morphine DEGs in PL–ILA–ORB  +  GPCRs enriched in ORB vs the rest of the Allen atlas. Then checked as % expressing in our 106,122 ORBm cells.")
add_table(
    s,
    [
        ["Considered", "Why Jesse flagged it", "Why it is / is not a panel add"],
        ["Fos  Arc  Egr1  Junb  Nr4a1", "Top activity IEGs after morphine", "Already on the 144. Keep. Do not swap."],
        ["Per2  Pcsk1  Per1", "Widest new IEGs (13 / 11 / 8 clusters). Circadian / peptide program, not acute TRAP.", "Not on the panel. This is the morphine-state layer."],
        ["Cckbr  Hcrtr2  Chrm2  Grm5", "ORB-enriched or DEG GPCRs", "Already on the 144."],
        ["Rxfp1", "Top ORB-enriched GPCR (19 subclasses)", "Free on Xenium Mouse Brain v1. Allen 34% in L5 ET."],
        ["Chrm1  Grm8  Gpr26", "ORB-enriched; missing from our 40-GPCR pull", "Allen: 92% / 99% / 86%. High enough for Xenium."],
        ["Mas1  Gpr68  Mchr1", "Jesse Glut ranks 1, 3, 4 (relative enrichment)", "Allen absolute % is modest (45 / 40 / 32). Mchr1 too weak."],
        ["~160 TFs; Camk2g  Fxr1", "Broad chromatin or plasticity DEGs", "TFs skipped. Camk2g is abundant (93%) but not ORB-specific."],
    ],
    0.4,
    1.08,
    12.5,
    5.75,
    [3.3, 4.5, 4.7],
)
add_footer(s, 2)

# ----- 3 Final -----
s = prs.slides.add_slide(BLANK)
add_bar(s, RUST)
add_title(s, "Final decision  |  genes added to the panel")
add_sub(s, "Cell-type 144 stays. Dan 14 are already on MSGS111. Below is the Jesse + Allen add.")
add_table(
    s,
    [
        ["Decision", "Genes", "Why this is the final add", "Slots"],
        ["Already on the sheet", "Dan 14   (Lamb3, Cck, Col23a1, …)", "Amygdala spatial genes Dan uses; already ranks 145–158", "14 (done)"],
        ["ADD  (free)", "Rxfp1", "Jesse’s top ORB GPCR; already on the Xenium base panel", "0"],
        ["ADD", "Per2    Pcsk1    Per1", "Jesse’s morphine-state IEG program. Per1 is 63% in Allen ORBm.", "3"],
        ["ADD", "Chrm1    Grm8", "ORB-enriched in Jesse; highest Allen abundance (92%, 99%)", "2"],
        ["Not added", "Mas1   Gpr68   Mchr1", "Relative ORB hits, but Allen % is too low vs Chrm1/Grm8", "—"],
        ["Not added", "160 TFs   Fxr1   Vps13a", "Not cell-type or ORB-specific. Fos/Arc already cover activity.", "—"],
    ],
    0.35,
    1.08,
    12.6,
    4.85,
    [2.4, 3.5, 5.5, 1.2],
)
box = s.shapes.add_textbox(Inches(0.4), Inches(6.1), Inches(12.5), Inches(0.9))
tf = box.text_frame
tf.word_wrap = True
set_run(tf.paragraphs[0], "Final new genes:    Rxfp1   +   Per2   Pcsk1   Per1   +   Chrm1   Grm8", 20, True, RUST)
p = tf.add_paragraph()
set_run(p, "Five custom slots on top of Dan 14  →  119 custom if every Dan gene is kept.  Cap is 100; swap CEA-border Dan genes if 10x will not exceed it.", 14, False, INK)
add_footer(s, 3)

ppt = OUT / "Add_genes_Jesse_Allen_Dan_4slides.pptx"
prs.save(ppt)
print("saved", ppt.exists(), ppt.stat().st_size)
if DL.is_dir():
    alt = DL / "Add_genes_Jesse_Allen_Dan_4slides.pptx"
    try:
        prs.save(alt)
        print("downloads", alt.stat().st_size)
    except OSError as e:
        print("downloads locked", e)
