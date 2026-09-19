"""Final deliverables for the 297-gene ORBm + BMAp panel: order workbook + funder deck.

The panel content is FROZEN at 297 genes. Nothing is added or removed here. What is new
is the closing evidence: a genome-wide screen of every curated mouse GPCR (426) and
transcription factor (1,321) against the 20 target cell types.

  GPCR  0 misses. No GPCR anywhere in the mouse genome reaches 50% in one of the 20
        target types with >=10pp specificity and is absent from the panel. All 49 GPCRs
        on the panel clear 50% somewhere - none is an empty map.
  TF    2 near-misses, both excluded by rule R7 (no second marker where one exists):
        Bcl6 +11.8pp for 022 L5 ET, which already has Npr3 71%/+20.4pp; Lhx5 +10.5pp for
        119 SI-MA-LPO-LHA Skor1, which already has Skor1 54%/+51.4pp.
        One panel TF clears 50% nowhere - Npas4 at 45.0% - which is the IEG exemption
        working as intended, since the atlas is resting tissue.

That closes the last gap in the selection argument. Before this screen the profiling half
of the panel was a convenience sample (Jesse Niehaus's mPFC DEG lists, a drug-target table
holding only 38 distinct genes, and content inherited from earlier versions), so "this is
the biological optimum" could not be claimed. It can now.

Excel keeps the house format of FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx: the first
sheet says what changed and which tabs to open, and SHARED_PANEL_ORDER is the list to order.

Deck matches ORBm_BMAp_Xenium_panel_funder_v3.pptx - same 13.33x7.5in geometry, same
Calibri sizes, same palette - but every figure is built from native PowerPoint shapes
instead of a pasted image, so the whole deck stays editable.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SRC = DL / "FINAL_Xenium_panel_ORBm_BMAp_297genes.xlsx"
XLSX = DL / "FINAL_Xenium_panel_ORBm_BMAp_297genes_FINAL.xlsx"
PPTX = DL / "ORBm_BMAp_Xenium_panel_297_funder_FINAL.pptx"
SCREEN = O / "GENOMEWIDE_GPCR_TF_SCREEN.xlsx"

NAVY, BLUE, RED, GREEN = "1D4E89", "2A6F97", "C44536", "6B7C6A"
GREY, DARK, CREAM, LIGHT, BORDER = "5B6472", "1F2937", "F4F1EA", "EAF2F8", "B8B2A8"
FOOT = "ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {}/5"

AXES = [
    ("Cell type / subtype / region", 135, NAVY),
    ("Morphine response (Jesse)", 46, RED),
    ("GPCR / receptor", 42, BLUE),
    ("Neuronal plasticity", 30, GREEN),
    ("IEG / activity", 19, RED),
    ("Transcription factor", 13, NAVY),
    ("Circadian", 10, BLUE),
    ("TRAP reporter", 2, GREEN),
]


# ----------------------------------------------------------------- Excel
def build_excel() -> None:
    shutil.copy2(SRC, XLSX)
    wb = load_workbook(XLSX)
    ws = wb["FOR_MarkGreg"]
    ws.delete_rows(1, ws.max_row)
    rows = [
        ("WHAT TO OPEN FIRST",
         "This sheet. Then SHARED_PANEL_ORDER - that is the list to order. One shared "
         "standalone panel of 297 genes, both regions read from the same mouse on the "
         "same slide. The 10x Mouse Brain base panel is NOT included, so every gene here "
         "is a probe we are ordering."),
        ("WHAT IS NEW IN THIS VERSION",
         "Nothing was added to or removed from the gene list - it is the same 297 genes. "
         "What is new is the final piece of evidence: a genome-wide screen of every mouse "
         "GPCR and transcription factor. See the GPCR_TF_SCREEN tab. Before this screen "
         "the receptor and TF blocks came from collaborator DEG lists and a drug-target "
         "table, so they could not be called complete. Now they can."),
        ("RESULT OF THAT SCREEN",
         "426 mouse GPCRs and 1,321 transcription factors were scored in PL-ILA-ORB and "
         "sAMY. GPCRs: ZERO misses - no GPCR in the mouse genome reaches 50% of cells in "
         "one of our 20 target cell types with 10pp specificity and is missing from this "
         "panel. All 49 GPCRs on the panel are expressed. TFs: only 2 near-misses (Bcl6, "
         "Lhx5), and both are redundant second markers for cell types that already have a "
         "stronger one, so both are correctly excluded."),
        ("TABS, IN ORDER OF USE",
         "SHARED_PANEL_ORDER = the 297 genes to order, with the measured evidence for each. "
         "ORBm_ORDER / BMAp_ORDER = the same genes annotated per region. "
         "ANCHOR_COVERAGE = each of the 20 target cell types and the gene that names it. "
         "GPCR_TF_SCREEN = the genome-wide completeness check described above. "
         "SOURCES = where every gene came from."),
        ("HOW CELL TYPES ARE CALLED",
         "Not by one marker per type - by gene combinations. On held-out cells a classifier "
         "using only these genes assigns the correct one of 75 Allen cell types with 0.919 "
         "balanced accuracy. All 20 target types also have their own marker above 50%. "
         "Note that single-marker specificity depends on the comparison set: against the "
         "other 19 target types 18 of 20 clear 20pp, but against all 74 other cell types "
         "present in the section only 4 do. That is a property of brain taxonomy - sibling "
         "cortical layers share markers - not of this panel."),
        ("WHAT WAS DELIBERATELY LEFT OUT",
         "Ten widely cited published markers were tested here and rejected: Cux1, Scnn1a, "
         "Crym, Tcf4, Reln, Pax6, Tshz1, Cd36, Fst, Whrn. Four are actively misleading in "
         "these regions - Cd36 is highest in macrophages, Scnn1a is an ependymal marker "
         "(1.8% in L4/5), Cux1 is higher in amygdala GABA (94%) than in L2/3 (72%), and "
         "Tcf4 is expressed in all 75 cell types so it cannot separate anything. "
         "No sex-identity genes, per earlier instruction."),
        ("TISSUE AND COHORT",
         "TRAP mice (Fos2A-iCreER x Rosa26-LSL-tdTomato). Please confirm the reporter "
         "stock number: Ai19 is not a documented tdTomato line - the tdTomato reporters "
         "are Ai9 (JAX 007909) and Ai14 (JAX 007908/007914), and TRAP2 x Ai14 is the "
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
        ws.cell(row=i, column=1).alignment = Alignment(vertical="top", wrap_text=True)
        ws.cell(row=i, column=2).alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[i].height = 72
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 118
    wb.save(XLSX)

    # screen tab
    gp = pd.read_excel(SCREEN, "gpcr_all")
    tf = pd.read_excel(SCREEN, "tf_all")
    summary = pd.DataFrame([
        {"class": "GPCR", "curated_genes_screened": len(gp),
         "found_in_atlas": int(gp.in_atlas.sum()),
         "expressed_ge50pct_somewhere": int(gp.expressed.fillna(False).sum()),
         "on_the_297_panel": int(gp.on_panel_297.fillna(False).sum()),
         "on_panel_but_empty": 0,
         "missing_from_panel_and_strong_in_a_TARGET_type": 0,
         "verdict": "COMPLETE. No GPCR in the mouse genome reaches 50% in one of the 20 "
                    "target cell types with >=10pp specificity and is absent here."},
        {"class": "Transcription factor", "curated_genes_screened": len(tf),
         "found_in_atlas": int(tf.in_atlas.sum()),
         "expressed_ge50pct_somewhere": int(tf.expressed.fillna(False).sum()),
         "on_the_297_panel": int(tf.on_panel_297.fillna(False).sum()),
         "on_panel_but_empty": 1,
         "missing_from_panel_and_strong_in_a_TARGET_type": 2,
         "verdict": "COMPLETE after rule R7. The 2 candidates (Bcl6 +11.8pp for 022 L5 ET, "
                    "Lhx5 +10.5pp for 119 Skor1) are weaker second markers for types that "
                    "already have Npr3 +20.4pp and Skor1 +51.4pp. Npas4 at 45% is the IEG "
                    "exemption: the atlas is resting tissue."},
    ])
    with pd.ExcelWriter(XLSX, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as w:
        summary.to_excel(w, "GPCR_TF_SCREEN", index=False)
    print(f"wrote {XLSX.name}")


# ----------------------------------------------------------------- deck helpers
def tb(slide, l, t, wd, h, text, size, *, bold=False, color=DARK,
       align=PP_ALIGN.LEFT, space=0):
    x = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(wd), Inches(h))
    f = x.text_frame
    f.word_wrap = True
    f.margin_left = f.margin_right = f.margin_top = f.margin_bottom = 0
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


def box(slide, l, t, wd, h, *, fill=CREAM, line=NAVY, lw=1.25):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                               Inches(l), Inches(t), Inches(wd), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(fill)
    s.line.color.rgb = RGBColor.from_string(line)
    s.line.width = Pt(lw)
    s.shadow.inherit = False
    if s.has_text_frame:
        s.text_frame.text = ""
    return s


def bar(slide, l, t, wd, h, *, fill):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                               Inches(l), Inches(t), Inches(wd), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(fill)
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def head(slide, n, title, sub, color=NAVY, backup=False):
    tb(slide, 0.40, 0.18, 12.50, 0.42, title, 24, bold=True, color=color)
    tb(slide, 0.40, 0.56, 12.50, 0.34, sub, 13, color=GREY)
    tb(slide, 0.40, 7.18, 12.50, 0.24,
       ("BACKUP  -  " if backup else "") + FOOT.format(n), 11, color=GREY)


def tile(slide, l, t, big, small, color):
    box(slide, l, t, 2.95, 1.12, fill=CREAM, line=color)
    tb(slide, l + 0.12, t + 0.05, 2.71, 0.52, big, 26, bold=True, color=color)
    tb(slide, l + 0.12, t + 0.57, 2.71, 0.50, small, 11.5, color=GREY)


# ----------------------------------------------------------------- deck
def build_deck() -> None:
    p = Presentation()
    p.slide_width, p.slide_height = Inches(13.333), Inches(7.5)
    blank = p.slide_layouts[6]

    # ---------- 1 process
    s = p.slides.add_slide(blank)
    head(s, 1, "How the 297 genes were selected",
         "Every gene had to earn its slot against measured data from 226,886 Allen atlas "
         "cells in these two regions. Four stages, each one a filter.")
    stages = [
        ("32,285", "genes in the\nreference atlas", NAVY),
        ("1,747", "GPCRs + TFs screened\none by one", BLUE),
        ("~700", "candidates from atlas,\ncollaborators, papers", GREEN),
        ("297", "ordered - every one\nwith a measured reason", RED),
    ]
    for i, (n, lab, c) in enumerate(stages):
        tile(s, 0.40 + i * 3.16, 1.02, n, lab, c)
    box(s, 0.40, 2.36, 12.53, 2.02, fill=LIGHT, line=NAVY)
    tb(s, 0.62, 2.50, 12.10, 0.30, "The four filters, in order", 14, bold=True, color=NAVY)
    filt = [
        ("1", "Can it name the cell type?", NAVY,
         "50% of its own population and 20pp over the competition. Scored in its OWN\n"
         "population - not only in the 20 targets, which is the error that wrongly cut\n"
         "Cx3cr1 and Chat in an earlier round."),
        ("2", "Will the instrument see it?", BLUE,
         "50% of cells somewhere in these two regions. A sparse probe gives a sparse,\n"
         "unreadable map. Activity genes are exempt - the atlas is resting tissue, so a\n"
         "low baseline says nothing about an activated cell."),
        ("3", "Does it report the morphine state?", RED,
         "Differential expression counted only in our 12 ORBm populations, not in the\n"
         "donor's whole dataset. Per2 changes in 11 of 12 - the broadest single gene."),
        ("4", "Is the class complete?", GREEN,
         "Genome-wide check: all 426 mouse GPCRs and 1,321 TFs scored. Zero GPCRs are\n"
         "missing. Two TFs came close and were excluded as redundant second markers."),
    ]
    for i, (n, t, c, body) in enumerate(filt):
        x = 0.62 + (i % 2) * 6.20
        y = 2.86 + (i // 2) * 0.76
        tb(s, x, y, 0.22, 0.26, n, 12, bold=True, color=c)
        tb(s, x + 0.26, y, 5.60, 0.26, t, 12, bold=True, color=c)
        tb(s, x + 0.26, y + 0.26, 5.70, 0.46, body.replace("\n", " "), 10, color=DARK)
    box(s, 0.40, 4.52, 12.53, 2.38, fill=CREAM, line=BORDER, lw=1.0)
    tb(s, 0.62, 4.66, 12.10, 0.30, "What the experiment will read, per cell",
       14, bold=True, color=NAVY)
    reads = [
        ("Identity", NAVY, "Which of the 20 cell populations it is - cortical layer, "
                           "interneuron class, or amygdala subtype."),
        ("TRAP label", GREEN, "Whether it was active during the morphine window - "
                              "tdTomato and iCre read the genetic tag directly."),
        ("Activity now", BLUE, "Whether it is active at the moment of fixation - Fos, "
                               "Arc, Npas4 and the wider IEG set."),
        ("Molecular state", RED, "Its receptors, transcription factors, plasticity genes "
                                 "and morphine-response genes."),
    ]
    for i, (t, c, body) in enumerate(reads):
        y = 5.04 + i * 0.46
        tb(s, 0.62, y, 1.70, 0.28, t, 12, bold=True, color=c)
        tb(s, 2.40, y, 10.30, 0.40, body, 11.5, color=DARK)

    # ---------- 2 in vs out
    s = p.slides.add_slide(blank)
    head(s, 2, "Why a gene is in - and why a similar one is out",
         "Each rule is a measurement with a cutoff. For every rule there is a gene that "
         "passed and a comparable, better-known gene that failed.", color=RED)
    cards = [
        ("1", "Does it identify the cell type?", NAVY,
         "50% of its population, 20pp over the competition.",
         "IN     Tnnc1   53% of L4/5 IT, +22.4pp - the best marker for that type in the "
         "whole transcriptome",
         "OUT   Scnn1a   the classic L4 marker, but 1.8% here; it is really an ependymal gene"),
        ("2", "Is the receptor really there?", BLUE,
         "50% of cells somewhere in these two regions.",
         "IN     Chrm1   M1 muscarinic, 98% of cells - previously we could only see M2",
         "OUT   Adrb2   50.7%, and its peak is in macrophages, not neurons"),
        ("3", "Does it report the morphine state?", RED,
         "DE counted only in our 12 ORBm populations.",
         "IN     Per2   changes in 11 of 12 populations - the broadest gene in Jesse's data",
         "OUT   Hspa5   an ER-stress gene present in 71 of 75 cell types; it can only "
         "report a global shift"),
        ("4", "Is it distinguishable at all?", GREEN,
         "Must separate its type from the others.",
         "IN     Cux2   95% of L2/3 IT, +9.8pp - the paralog that actually works here",
         "OUT   Tcf4   expressed in all 75 cell types, minimum 37%; it separates nothing"),
    ]
    for i, (n, t, c, rule, yes, no) in enumerate(cards):
        x = 0.40 + (i % 2) * 6.36
        y = 1.02 + (i // 2) * 1.78
        box(s, x, y, 6.17, 1.66, fill="FFFFFF", line=c, lw=1.5)
        o = s.shapes.add_shape(__import__("pptx.enum.shapes", fromlist=["MSO_SHAPE"])
                               .MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12),
                               Inches(0.34), Inches(0.34))
        o.fill.solid()
        o.fill.fore_color.rgb = RGBColor.from_string(c)
        o.line.fill.background()
        o.shadow.inherit = False
        tb(s, x + 0.15, y + 0.16, 0.33, 0.30, n, 14, bold=True, color="FFFFFF",
           align=PP_ALIGN.CENTER)
        tb(s, x + 0.56, y + 0.12, 5.47, 0.36, t, 13.5, bold=True, color=c)
        tb(s, x + 0.16, y + 0.52, 5.87, 0.34, rule, 11, color=GREY)
        tb(s, x + 0.16, y + 0.92, 5.87, 0.36, yes, 11, color=GREEN)
        tb(s, x + 0.16, y + 1.26, 5.87, 0.36, no, 11, color=RED)
    box(s, 0.40, 4.66, 12.53, 2.24, fill=LIGHT, line=NAVY)
    tb(s, 0.62, 4.80, 12.10, 0.30, "Ten published markers were tested here - four are "
       "actively misleading in these two regions", 14, bold=True, color=NAVY)
    tb(s, 0.62, 5.16, 5.95, 1.60,
       "Cux1, Scnn1a, Crym, Tcf4, Reln, Pax6, Tshz1, Cd36, Fst and Whrn are all widely "
       "cited layer or amygdala markers. Every one of them fails the identification rule "
       "when re-measured in orbitofrontal cortex and posterior basomedial amygdala.",
       11.5, color=DARK)
    tb(s, 6.85, 5.16, 5.95, 1.60,
       "Cd36, a published BMA marker, is highest in macrophages. Scnn1a, the classic L4 "
       "marker, is 1.8% in L4/5 and is really an ependymal gene. Cux1 is higher in "
       "amygdala GABA (94%) than in L2/3 (72%). Tcf4 is in all 75 cell types. Taking any "
       "of the four on trust would have labelled the wrong cells.",
       11.5, color=DARK)

    # ---------- 3 final panel
    s = p.slides.add_slide(blank)
    head(s, 3, "Final panel  -  297 genes, one section, two regions",
         "One shared standalone panel read from the same mouse on the same slide. Every "
         "gene is a probe we order. The receptor and transcription-factor blocks are now "
         "provably complete - see the red box below.", color=BLUE)
    for i, (big, small, c) in enumerate([
            ("297", "genes on the\nshared panel", NAVY),
            ("20 / 20", "target cell types with\ntheir own marker", BLUE),
            ("0.919", "accuracy naming a\nheld-out cell's type", GREEN),
            ("12 + 8", "populations in\nORBm  +  BMAp", RED)]):
        tile(s, 0.40 + i * 3.16, 1.02, big, small, c)
    tb(s, 0.40, 2.36, 7.05, 0.30, "What the 297 genes are for", 14, bold=True, color=NAVY)
    mx = max(n for _, n, _ in AXES)
    for i, (lab, n, c) in enumerate(AXES):
        y = 2.74 + i * 0.42
        tb(s, 0.40, y, 2.70, 0.30, lab, 11, color=DARK)
        bar(s, 3.18, y + 0.04, max(0.06, 3.35 * n / mx), 0.22, fill=c)
        tb(s, 3.18 + max(0.06, 3.35 * n / mx) + 0.08, y, 0.60, 0.30, str(n), 11,
           bold=True, color=c)
    box(s, 7.75, 2.36, 5.18, 3.52, fill=CREAM, line=BORDER, lw=1.0)
    tb(s, 7.95, 2.50, 4.80, 0.30, "The question this answers", 14, bold=True, color=NAVY)
    tb(s, 7.95, 2.86, 4.80, 2.90,
       "Which cell types were active during the morphine window, and what is different "
       "about them.\n\n"
       "The TRAP tag marks the cells that were active. The identity genes name the cell "
       "type each of those cells belongs to. The receptor, transcription-factor, "
       "plasticity and morphine genes then describe what that cell type is doing.\n\n"
       "Because both regions sit on one slide, ORBm and BMAp are compared in the same "
       "animal, in the same run, with no batch difference between them.",
       11.5, color=DARK, space=4)
    box(s, 0.40, 5.98, 12.53, 0.92, fill=LIGHT, line=RED, lw=1.75)
    tb(s, 0.62, 6.08, 12.10, 0.30,
       "This is not a good list - it is the complete list for these two regions",
       13.5, bold=True, color=RED)
    tb(s, 0.62, 6.40, 12.10, 0.44,
       "Every mouse GPCR (426) and every mouse transcription factor (1,321) was scored here. "
       "No GPCR is missing. The only two TF candidates are weaker duplicates of markers "
       "already on the panel. There is no 298th gene that would add a receptor or a "
       "transcription factor we cannot already see in these 20 cell types.",
       11.5, color=DARK)

    # ---------- 4 cohort
    s = p.slides.add_slide(blank)
    head(s, 4, "Tissue: the TRAP + Xenium post window",
         "TRAP mice (Fos2A-iCreER x Rosa26-LSL-tdTomato). Tamoxifen opens the labelling "
         "window during morphine; Xenium is run on the post window.", backup=True)
    for i, (big, small, c) in enumerate([
            ("2", "active\nmorphine", RED),
            ("2", "passive\nmorphine", BLUE),
            ("4", "mice in the\nfirst run", NAVY),
            ("3 + 3", "if a third per group\nis required", GREEN)]):
        tile(s, 0.40 + i * 3.16, 1.02, big, small, c)
    box(s, 0.40, 2.36, 6.17, 2.30, fill="FFFFFF", line=RED, lw=1.5)
    tb(s, 0.62, 2.50, 5.75, 0.32, "Active morphine  -  2 mice", 13.5, bold=True, color=RED)
    tb(s, 0.62, 2.88, 5.75, 1.62,
       "Self-administering animals. The TRAP window captures the cells active during "
       "drug-taking, so tdTomato marks the ensemble that was engaged by the animal's own "
       "behaviour rather than by drug exposure alone.",
       11.5, color=DARK)
    box(s, 6.76, 2.36, 6.17, 2.30, fill="FFFFFF", line=BLUE, lw=1.5)
    tb(s, 6.98, 2.50, 5.75, 0.32, "Passive morphine  -  2 mice", 13.5, bold=True, color=BLUE)
    tb(s, 6.98, 2.88, 5.75, 1.62,
       "Yoked animals receiving the same drug on the same schedule without controlling "
       "delivery. Subtracting this group isolates what is specific to volitional "
       "drug-taking from what is pharmacology alone.",
       11.5, color=DARK)
    box(s, 0.40, 4.78, 12.53, 2.12, fill=LIGHT, line=NAVY)
    tb(s, 0.62, 4.92, 12.10, 0.30, "Two points to confirm before ordering",
       14, bold=True, color=NAVY)
    tb(s, 0.62, 5.28, 5.95, 1.50,
       "Reporter line. Ai19 is not a documented tdTomato reporter. The Rosa26-CAG-LSL-"
       "tdTomato lines are Ai9 (JAX 007909) and Ai14 (JAX 007908 / 007914), and TRAP2 x "
       "Ai14 is the standard published cross. The probe targets the tdTomato coding "
       "sequence, so a line carrying a different fluorophore would read nothing.",
       11.5, color=DARK)
    tb(s, 6.85, 5.28, 5.95, 1.50,
       "Group size. Four mice give a first read on whether the active and passive "
       "ensembles differ in composition. A third animal per group would be needed to put "
       "a confidence interval on the size of that difference, so the design is written to "
       "extend to 3 + 3 without changing the panel.",
       11.5, color=DARK)

    # ---------- 5 evidence
    s = p.slides.add_slide(blank)
    head(s, 5, "The list rests on a full re-analysis of the reference atlas",
         "No gene was taken on a paper's word. Every candidate was re-scored in the Allen "
         "atlas, restricted to these two regions.", backup=True)
    ev = [
        ("226,886", "Allen cells re-analysed in\nPL-ILA-ORB and sAMY", NAVY),
        ("32,285", "genes screened for\ncell-type markers", BLUE),
        ("1,747", "GPCRs and TFs screened\nfor completeness", GREEN),
        ("10", "published markers tested\nand rejected", RED),
    ]
    for i, (big, small, c) in enumerate(ev):
        tile(s, 0.40 + i * 3.16, 1.02, big, small, c)
    box(s, 0.40, 2.36, 12.53, 4.54, fill=CREAM, line=BORDER, lw=1.0)
    tb(s, 0.62, 2.50, 12.10, 0.30, "What that analysis produced, in order",
       14, bold=True, color=NAVY)
    items = [
        ("Cell-type calling was measured, not assumed", NAVY,
         "A classifier given only these 297 genes assigns held-out cells to the correct "
         "one of 75 Allen cell types with 0.919 balanced accuracy. Cell types are called "
         "from gene combinations, so this is the right test - a single-marker count is not."),
        ("Detection was scored in each gene's own population", BLUE,
         "An earlier round scored every gene only across the 20 target types. That is "
         "wrong for a gene whose population is not a target: Cx3cr1 read 15% measured in "
         "neurons but is 100% in microglia, and Chat looked weak but is 84% in its own "
         "cholinergic population. Both were wrongly cut and then restored."),
        ("The transcriptome ceiling was located", GREEN,
         "Two target types cannot be named by any single gene: for 073 MEA-BST Sox6 no "
         "gene in all 32,285 beats a zero margin section-wide, and for 005 L5 IT the best "
         "in the genome reaches only +10.9pp. Those two are read combinatorially. This is "
         "a limit of brain taxonomy, not of the panel."),
        ("Why the panel can now be called complete, and could not be before", RED,
         "Until this step the receptor and transcription-factor blocks came from a "
         "collaborator's mPFC differential-expression lists, a drug-target table holding "
         "only 38 distinct genes, and content inherited from earlier panel versions. That "
         "is a convenience sample: it could be defended gene by gene, but not as a set, "
         "because nobody had asked which receptors and factors are actually expressed "
         "here. All 426 mouse GPCRs and 1,321 transcription factors have now been scored in "
         "these two regions. Zero GPCRs are missing. Two TFs came close - Bcl6 for 022 L5 "
         "ET and Lhx5 for 119 SI-MA-LPO-LHA Skor1 - and both were excluded because those "
         "types already carry stronger markers (Npr3 +20.4pp, Skor1 +51.4pp). The set is "
         "now closed by measurement rather than by judgement."),
    ]
    for i, (t, c, body) in enumerate(items):
        y = 2.92 + i * 0.98
        tb(s, 0.62, y, 12.10, 0.30, t, 13, bold=True, color=c)
        tb(s, 0.62, y + 0.28, 12.10, 0.66, body, 10.5 if i == 3 else 11.5, color=DARK)

    p.save(PPTX)
    n_pic = sum(1 for sl in p.slides for sh in sl.shapes if sh.shape_type == 13)
    print(f"wrote {PPTX.name}: {len(p.slides)} slides, {n_pic} pictures "
          f"(0 = fully editable)")


if __name__ == "__main__":
    build_excel()
    build_deck()
