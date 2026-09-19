"""Five-slide funder deck, matching the layout and palette of the v3 deck."""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

OUT = Path(__file__).resolve().parents[1] / "outputs"
FIG = OUT / "funder_figs"
DST = OUT / "ORBm_BMAp_Xenium_panel_funder_v4.pptx"

NAVY, BLUE, RED, GREEN = "1D4E89", "2A6F97", "C44536", "6B7C6A"
GREY, DARK, CREAM, LBLUE, EDGE = "5B6472", "1F2937", "F4F1EA", "EAF2F8", "B8B2A8"
FOOT = "ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {}/5"


def rgb(h):
    return RGBColor.from_string(h)


def tb(sl, x, y, w, h, lines, size=11, color=GREY, bold=False, align=PP_ALIGN.LEFT,
       space=2):
    box = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate(lines if isinstance(lines, list) else [lines]):
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


def slide(prs, n, title, lead, title_color=NAVY):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    tb(sl, 0.40, 0.18, 12.5, 0.42, title, 24, title_color, True)
    tb(sl, 0.40, 0.58, 12.5, 0.34, lead, 13, GREY)
    tb(sl, 0.40, 7.18, 12.5, 0.24, FOOT.format(n), 11, GREY)
    return sl


def kpi(sl, x, y, big, lines, color):
    rrect(sl, x, y, 2.95, 1.12, color, CREAM)
    tb(sl, x + 0.12, y + 0.05, 2.71, 0.52, big, 26, color, True, PP_ALIGN.CENTER)
    tb(sl, x + 0.12, y + 0.57, 2.71, 0.50, lines, 11.5, GREY, False, PP_ALIGN.CENTER,
       space=0)


def rule_card(sl, x, y, num, color, head, method, yes, no, w=6.17, h=1.72):
    rrect(sl, x, y, w, h, color)
    o = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12),
                            Inches(0.34), Inches(0.34))
    o.fill.solid()
    o.fill.fore_color.rgb = rgb(color)
    o.line.fill.background()
    o.shadow.inherit = False
    tb(sl, x + 0.15, y + 0.16, 0.33, 0.30, num, 14, "FFFFFF", True, PP_ALIGN.CENTER)
    tb(sl, x + 0.56, y + 0.12, w - 0.72, 0.36, head, 13.5, color, True)
    tb(sl, x + 0.16, y + 0.52, w - 0.30, 0.34, method, 11, GREY)
    tb(sl, x + 0.16, y + 0.94, w - 0.30, 0.34, yes, 11, GREEN)
    tb(sl, x + 0.16, y + 1.28, w - 0.30, 0.34, no, 11, RED)


def main() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # ----------------------------------------------------------------- slide 1
    s = slide(prs, 1, "How the gene panel was selected",
              "Xenium reads a fixed set of genes per section, so every slot has to be "
              "earned. Four public and internal sources went in; four measured rules "
              "decided what came out.")
    s.shapes.add_picture(str(FIG / "s1_workflow.png"), Inches(0.20), Inches(1.02),
                         width=Inches(12.93))

    # ----------------------------------------------------------------- slide 2
    s = slide(prs, 2, "Why a gene is in - and a similar one is out",
              "Every rule is a measurement with a cutoff. For each one there is a gene "
              "that passed and a comparable gene that did not, so the line is visible "
              "rather than asserted.")
    rule_card(s, 0.40, 1.02, "1", NAVY, "Does it identify the cell population?",
              "Gap in percent of cells positive, against the 19 neighbouring "
              "populations.",
              "IN     Ccbe1    74% of L2/3 cells, +54pp over any other population",
              "OUT   Sstr4     1.4% of cells and no separation anywhere - an empty map")
    rule_card(s, 6.76, 1.02, "2", BLUE, "Does it split a population into sub-types?",
              "A gene can be rare overall and still decisive inside one "
              "sub-population.",
              "IN     St18      only 8.8% of cells, but 95% of one 194-cell sub-type "
              "(+66pp)",
              "OUT   Gpr63    2.7% of cells, 1.5pp gap - rare and uninformative")
    rule_card(s, 0.40, 2.86, "3", GREEN, "Will the instrument actually detect it?",
              "State genes report a level, so they must be present in enough cells to "
              "read.",
              "IN     Grm8      99% of cells, and +31pp at a sub-population as a bonus",
              "OUT   Mas1      most ORB-enriched receptor in the donor data, but 45% "
              "of cells")
    rule_card(s, 6.76, 2.86, "4", RED, "Is a gene already on the panel doing this job?",
              "Redundant paralogues cost optical capacity and return no extra "
              "information.",
              "IN     Gria1     the AMPA subunit that traffics in opioid plasticity",
              "OUT   Syt1       100% of cells in all 20 populations, 0.0pp gap - no "
              "contrast")

    rrect(s, 0.40, 4.78, 12.53, 2.12, NAVY, LBLUE)
    tb(s, 0.62, 4.92, 12.10, 0.30, "The two exceptions, both deliberate", 13.5, NAVY,
       True)
    tb(s, 0.62, 5.30, 5.95, 1.50,
       ["Immediate-early genes are exempt from rule 3. The reference atlas is resting "
        "tissue, so a low resting number is the expected result, not a defect - "
        "induction is what the experiment measures.",
        "Npas4 sits at 34% of cells in the atlas and stays on the panel for exactly "
        "that reason."], 11.5, DARK, space=6)
    tb(s, 6.85, 5.30, 5.95, 1.50,
       ["Glia get 5 probes, not more, and that number was tested rather than assumed. "
        "28% of the section is non-neuronal, but a held-out test on 188,849 cells put "
        "neuron-vs-glia accuracy at 0.9998 both with and without glial probes: a glial "
        "cell is already negative for the 40 pan-neuronal genes on the panel. The 5 "
        "probes are there to NAME each population, one each, not to find them.",
        "Two probes were kept knowingly below the detection bar on request: Htr1a at "
        "28% of cells and Nfil3 at 20%."], 10.5, DARK, space=6)

    # ----------------------------------------------------------------- slide 3
    s = slide(prs, 3, "Final panel  -  259 genes, one section, two regions",
              "One shared panel, read from the same mouse. Each cell returns four "
              "layers of information at once.")
    for x, big, lines, c in [
            (0.40, "259", ["genes on the", "shared panel"], NAVY),
            (3.56, "0.948", ["balanced accuracy calling", "the 20 populations"], BLUE),
            (6.72, "86 / 86", ["sub-populations", "resolved"], GREEN),
            (9.88, "12 + 8", ["populations in", "ORBm  +  BMAp"], RED)]:
        kpi(s, x, 1.00, big, lines, c)
    s.shapes.add_picture(str(FIG / "s3_categories.png"), Inches(0.40), Inches(2.32),
                         width=Inches(7.05))
    tb(s, 7.85, 2.34, 5.05, 0.34, "What each cell will tell us", 15, NAVY, True)
    for i, (h, body, c) in enumerate([
            ("Identity", "Which of the 20 populations it is, and which sub-type inside "
                         "it - cortical layer, interneuron class, amygdala subtype",
             NAVY),
            ("Activity", "Whether it was active during the POST window - the TRAP2 "
                         "tdTomato tag, plus Fos, Arc and 12 more IEGs", BLUE),
            ("State", "Whether it carries the morphine-dependence signature - Per2, "
                      "Per1, Nr1d1 and the rest of the clock module", RED),
            ("Receptors", "Which druggable receptors sit on it - opioid, monoamine, "
                          "muscarinic, metabotropic, peptide", GREEN)]):
        y = 2.86 + i * 0.97
        tb(s, 7.85, y, 5.05, 0.28, h, 13, c, True)
        tb(s, 7.85, y + 0.29, 5.05, 0.62, body, 11.5, GREY)
    tb(s, 0.40, 6.50, 12.5, 0.40,
       "The capability this buys: inside one cortical cell type, separate the cells "
       "that were active during morphine seeking from those that were not - then ask "
       "which receptors differ.", 12, RED)

    # ----------------------------------------------------------------- slide 4
    s = slide(prs, 4, "The populations the panel has to tell apart",
              "Targets come from the Allen Brain Cell Atlas taxonomy: 12 populations in "
              "orbitofrontal cortex, 8 in basomedial amygdala, and the sub-types inside "
              "each.")
    s.shapes.add_picture(str(FIG / "s4_populations.png"), Inches(0.42), Inches(0.98),
                         width=Inches(12.50))
    tb(s, 0.40, 6.44, 12.5, 0.46,
       ["Marker counts are a proxy, so the panel was tested directly: a classifier "
        "using only these genes, on 125,313 held-out cells over 3 seeds, reaches 0.948 "
        "balanced accuracy across the 20 populations, 18 of them above 0.90 recall.",
        "073 MEA-BST Sox6 Gaba, the one population with a single marker, scores 0.982 - "
        "the count was misleading. The two that fall short, 005 L5 IT and 029 L6b, are "
        "graded into their neighbours: tripling the gene set moves them by 0.01-0.02, "
        "so this is cortical biology rather than a missing probe."], 11, GREY, space=2)

    # ----------------------------------------------------------------- slide 5
    s = slide(prs, 5, "What was removed, and what the evidence rests on",
              "The panel got smaller on purpose. A 318-gene draft was cut to 259 "
              "without losing a single cell population or sub-population.")
    for x, big, lines, c in [
            (0.40, "32,245", ["genes re-scored,", "not a shortlist"], NAVY),
            (3.56, "226,886", ["ORBm and BMAp cells", "in the reference atlas"], BLUE),
            (6.72, "113", ["genes cut from the draft,", "each with a written reason"],
             RED),
            (9.88, "13", ["documented sources,", "9 with a DOI"], GREEN)]:
        kpi(s, x, 1.00, big, lines, c)

    rrect(s, 0.40, 2.34, 6.17, 2.30, RED)
    tb(s, 0.62, 2.48, 5.75, 0.30, "What came off the 318-gene draft", 13.5, RED, True)
    for i, (n, t) in enumerate([
            ("85", "another marker already covered that population or sub-type"),
            ("25", "no contrast: ~100% of cells in all 20 populations, under 12pp of "
                   "separation"),
            ("3", "too rarely detected to produce a usable map")]):
        y = 2.88 + i * 0.52
        tb(s, 0.62, y, 0.55, 0.30, n, 14, RED, True)
        tb(s, 1.22, y + 0.02, 5.15, 0.46, t, 11, GREY)

    rrect(s, 6.76, 2.34, 6.17, 2.30, NAVY)
    tb(s, 6.98, 2.48, 5.75, 0.30, "What the numbers are measured on", 13.5, NAVY, True)
    for i, (n, t) in enumerate([
            ("Allen WMB-10X", "single-cell expression for ORBm and BMAp only, so every "
                              "number describes these two regions"),
            ("Jesse Niehaus", "5-day escalating-morphine DESeq2 in PL-ILA-ORB - source "
                              "of the circadian module and the state genes"),
            ("Berg GSE283418", "amygdala spatial panel, used to check the BMAp markers")
    ]):
        y = 2.88 + i * 0.56
        tb(s, 6.98, y, 1.75, 0.30, n, 11.5, BLUE, True)
        tb(s, 8.78, y + 0.01, 3.95, 0.52, t, 10.5, GREY)

    rrect(s, 0.40, 4.78, 12.53, 2.12, EDGE, CREAM)
    tb(s, 0.62, 4.92, 12.10, 0.32, "Why the result should be trusted", 14, NAVY, True)
    tb(s, 0.62, 5.34, 5.95, 1.45,
       ["The caps were written down before the panel was assembled, so the size is a "
        "consequence of the rules rather than a target that was aimed at.",
        "Every gene carries its measured detection and separation numbers in the "
        "delivered workbook, and every removal carries a one-line reason."],
       11.5, DARK, space=6)
    tb(s, 6.85, 5.34, 5.95, 1.45,
       ["The draft and the final panel were scored with identical code, so the "
        "comparison is like for like: 318 genes to 259, with sub-population coverage "
        "going from 73 to 74 of 86 rather than down.",
        "Remaining limitation: detection is measured on dissociated single-cell data, "
        "which predicts relative detectability, not Xenium's absolute sensitivity."],
       11.5, DARK, space=6)

    prs.save(DST)
    print("wrote", DST, len(prs.slides.__iter__.__self__._sldIdLst), "slides")


if __name__ == "__main__":
    main()
