"""Dan figures + combined Jesse/Dan/panel-decision PowerPoint."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs")
DL = Path(r"C:\Users\hsollim\Downloads")
FIG = OUT / "jesse_dan_figures"
FIG.mkdir(exist_ok=True)

NAVY = "#1D4E89"
RUST = "#C44536"
TEAL = "#2A6F97"
TAUPE = "#8C7B6B"
SAGE = "#6B7C6A"
GOLD = "#B08968"
GLUT = "#3D5A80"
GABA = "#9A8C7A"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

dan = pd.read_excel(DL / "GSE283418_vs_BMAp_panel.xlsx", "all_98_genes")
added14 = [
    "Col23a1",
    "Slc29a4",
    "Cck",
    "Gfra1",
    "Sp8",
    "Abca8a",
    "Calcrl",
    "Lamb3",
    "Syndig1l",
    "Tspan18",
    "Gabre",
    "Nos1",
    "Oprl1",
    "Dnah5",
]
where14 = {
    "Lamb3": "113 BMA Ccdc42 (true BMAp)",
    "Col23a1": "012 VGLUT1 border",
    "Slc29a4": "012 VGLUT1 border",
    "Cck": "012 VGLUT1 border",
    "Abca8a": "012 VGLUT1 border",
    "Dnah5": "012 VGLUT1 border",
    "Calcrl": "120 MEA",
    "Nos1": "120 MEA",
    "Oprl1": "120 MEA",
    "Gfra1": "121 MEA-BST",
    "Sp8": "073 MEA-BST GABA",
    "Syndig1l": "082 CEA-BST",
    "Gabre": "082 CEA-BST",
    "Tspan18": "119 SI/border",
}


def save(fig: plt.Figure, name: str) -> Path:
    p = FIG / name
    fig.savefig(p, dpi=200, bbox_inches="tight")
    fig.savefig(DL / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)
    return p


# --- Dan Fig 1: fate of 98 genes ---
fate = {
    "Already on our panel": int((dan.on_shared_panel == "yes").sum()),
    "Added to workbook (14)": 14,
    "In BMAp, not specific": 23,
    "Low / CEA / glia": 20,
    "Not scored in Allen pull": 3,
}
fig, ax = plt.subplots(figsize=(8.8, 4.6))
labels = list(fate.keys())
vals = list(fate.values())
colors = [TEAL, NAVY, TAUPE, RUST, GOLD]
bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1])
ax.set_xlabel("Number of genes on Dan 98-gene Resolve panel")
ax.set_title("Dan GSE283418  |  how the 98 spatial genes map onto our Xenium panel")
for y, v in enumerate(vals[::-1]):
    ax.text(v + 0.6, y, str(v), va="center")
ax.set_xlim(0, 46)
fig.tight_layout()
p_d1 = save(fig, "Dan_Fig1_98gene_fate.png")

# --- Dan Fig 2: 14 added genes ---
d14 = dan[dan.gene.isin(added14)].set_index("gene").loc[added14]
fig, ax = plt.subplots(figsize=(9.2, 5.8))
y = np.arange(len(d14))
ax.barh(y, d14.max_pct.values, color=NAVY)
ax.set_yticks(y)
ax.set_yticklabels([f"{g}   {where14[g]}" for g in d14.index], fontsize=8)
ax.set_xlabel("Detection in top Allen BMAp-mapped subclass (% of cells)")
ax.set_title("14 Dan genes appended to SHARED  |  Allen re-score in BMAp-mapped ROI")
ax.set_xlim(0, 115)
for i, (pct, spec) in enumerate(zip(d14.max_pct, d14.max_spec)):
    ax.text(pct + 1.2, i, f"{pct:.0f}%  spec {spec:.2f}", va="center", fontsize=8)
fig.tight_layout()
p_d2 = save(fig, "Dan_Fig2_14added_pct.png")

# --- Decision figure ---
fig, ax = plt.subplots(figsize=(10.4, 5.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis("off")
boxes = [
    (0.3, 0.4, 3.0, 5.2, NAVY, "KEEP  |  already on panel",
     "TRAP / IEG\nFos Arc Egr1 Junb\nNr4a1 Bdnf Npas4\n\nOpioid / GPCR\nOprm1 Oprd1 Oprk1\nNtsr1 Grm5 Chrm2\n\nDan overlap 38\nCartpt Foxp2 Pdyn\nSlc17a7 Drd1/2"),
    (3.5, 0.4, 3.0, 5.2, TEAL, "ADDED  |  Dan 14",
     "On MSGS111 now\nranks 145-158\n\nLamb3  (BMA 113)\nCck Col23a1 Slc29a4\nAbca8a Dnah5\nCalcrl Nos1 Oprl1\nGfra1 Sp8\nSyndig1l Gabre\nTspan18\n\nAll cost a slot"),
    (6.7, 0.4, 3.0, 5.2, GOLD, "PROPOSED  |  Jesse",
     "Not on order sheet yet\n\nFREE first\nRxfp1\n\nBroad ORBm DEGs\nPer2 Pcsk1 Per1\nNr4a3 Dusp1 Egr3\n\nOptional GPCR\nMas1 or Gpr68\nHrh1  Grm2"),
]
for x, y0, w, h, col, title, body in boxes:
    rect = mpatches.FancyBboxPatch(
        (x, y0), w, h, boxstyle="round,pad=0.04,rounding_size=0.08",
        facecolor="white", edgecolor=col, linewidth=2,
    )
    ax.add_patch(rect)
    ax.add_patch(plt.Rectangle((x, y0 + h - 0.7), w, 0.7, facecolor=col, edgecolor=col))
    ax.text(x + w / 2, y0 + h - 0.35, title, ha="center", va="center", color="white",
            fontsize=9, fontweight="bold")
    ax.text(x + 0.18, y0 + h - 1.0, body, ha="left", va="top", fontsize=8.2, color="#222",
            family="DejaVu Sans")
ax.set_title("Panel decision  |  keep core  |  Dan added  |  Jesse proposed", fontsize=12, pad=8)
fig.tight_layout()
p_dec = save(fig, "Decision_keep_Dan_Jesse.png")

# --- PPT ---
NAVY_RGB = RGBColor(0x1D, 0x4E, 0x89)
TEAL_RGB = RGBColor(0x2A, 0x6F, 0x97)
RUST_RGB = RGBColor(0xC4, 0x45, 0x36)
GOLD_RGB = RGBColor(0xB0, 0x89, 0x68)
INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x5B, 0x64, 0x72)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD0, 0xD5, 0xDD)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def add_bar(slide, color):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()


def add_footer(slide, n, total=20):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(7.18), Inches(12.3), Inches(0.28))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = f"ORBm + BMAp Xenium add-on  |  Jesse Niehaus  +  Daniel Berg / Scherrer  |  {n}/{total}"
    p.font.size = Pt(10)
    p.font.color.rgb = MUTED


def set_run(p, text, size=18, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Calibri"
    return r


def add_title(slide, text, y=0.28):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(12.3), Inches(0.55))
    tf = box.text_frame
    tf.word_wrap = True
    set_run(tf.paragraphs[0], text, 28, True, NAVY_RGB)


def add_sub(slide, text, y=0.78):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(12.3), Inches(0.4))
    set_run(box.text_frame.paragraphs[0], text, 14, False, MUTED)


def bullets(slide, items, left=0.55, top=1.3, width=12.2, height=5.5, size=18):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.font.size = Pt(size)
        p.font.color.rgb = INK
        p.font.name = "Calibri"
        p.space_after = Pt(10)


def card(slide, l, t, w, h, title, body, color=NAVY_RGB):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = WHITE
    sh.line.color.rgb = color
    head = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(0.42))
    head.fill.solid()
    head.fill.fore_color.rgb = color
    head.line.fill.background()
    hb = slide.shapes.add_textbox(Inches(l + 0.12), Inches(t + 0.06), Inches(w - 0.2), Inches(0.32))
    set_run(hb.text_frame.paragraphs[0], title, 13, True, WHITE)
    bb = slide.shapes.add_textbox(Inches(l + 0.14), Inches(t + 0.52), Inches(w - 0.28), Inches(h - 0.62))
    tf = bb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(body.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(13)
        p.font.color.rgb = INK
        p.font.name = "Calibri"


# 1 title
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
box = s.shapes.add_textbox(Inches(0.7), Inches(2.1), Inches(12), Inches(1.2))
set_run(box.text_frame.paragraphs[0], "Xenium custom add-on for ORBm and BMAp", 34, True, NAVY_RGB)
box = s.shapes.add_textbox(Inches(0.7), Inches(3.3), Inches(12), Inches(1.4))
tf = box.text_frame
tf.word_wrap = True
set_run(tf.paragraphs[0], "Jesse Niehaus (PL-ILA-ORB morphine DEGs + enriched GPCRs)", 20, False, INK)
p = tf.add_paragraph()
p.text = "Daniel Berg / Scherrer (GSE283418 amygdala spatial 98-gene panel)"
p.font.size = Pt(20)
p.font.color.rgb = INK
p = tf.add_paragraph()
p.text = "What is already on the panel, what we added from Dan, what we propose from Jesse"
p.font.size = Pt(16)
p.font.color.rgb = MUTED
box = s.shapes.add_textbox(Inches(0.7), Inches(5.6), Inches(12), Inches(0.8))
set_run(box.text_frame.paragraphs[0], "Hansol Lim  |  Schnitzer + Scherrer  |  HEAL / TRAP2 x Ai14  |  9 September 2026", 14, False, MUTED)
add_footer(s, 1)

# 2 take-home
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Take-home")
add_sub(s, "One shared Xenium add-on. Two collaborator datasets. Three decisions.")
card(s, 0.5, 1.4, 4.0, 5.2, "1. Core panel stays",
     "The 144-gene shared list\nalready covers TRAP / IEG\nand opioid receptors.\n\nFos Arc Egr1 Junb\nNr4a1 Oprm1 Ntsr1\nGrm5 Cartpt Foxp2\n\nAll 20 cell types remain\nseparable.", NAVY_RGB)
card(s, 4.7, 1.4, 4.0, 5.2, "2. Dan 14  ADDED",
     "GSE283418 Resolve\n98-gene smFISH.\n\n38 already on panel.\n14 informative extras\nare now on MSGS111\n(ranks 145-158).\n\nLamb3 is the closest\ntrue BMAp gene.\nOthers are MEA/CEA\nborders.", TEAL_RGB)
card(s, 8.9, 1.4, 4.0, 5.2, "3. Jesse  PROPOSED",
     "Morphine-dependence\nsignature, not cell-type ID.\n\nAdd only if that state\nis a Xenium readout.\n\nFirst: Rxfp1 (FREE)\nThen: Per2 Pcsk1 Per1\nThen: Nr4a3 Dusp1 Egr3\n\nDo not swap Fos/Arc.", GOLD_RGB)
add_footer(s, 2)

# 3 two datasets
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "The two collaborator datasets")
add_sub(s, "Different questions. Both re-checked in Allen WMB-10X for our ORBm / BMAp ROIs.")
card(s, 0.5, 1.4, 6.1, 5.3, "Jesse Niehaus  |  ORBm / mPFC",
     "5 days escalating morphine.\nDESeq2 pseudobulk, padj 0.1.\nPL-ILA-ORB subclasses.\n\nIEG 77   TF 179\nPlasticity 45   GPCR DEG 34\n+ GPCRs enriched in PL-ILA-ORB\nvs the rest of the 4M-cell atlas.\n\nAsk: which genes change in\nopioid dependence in ORB?\n\nNot a cell-type marker list.", NAVY_RGB)
card(s, 6.8, 1.4, 6.0, 5.3, "Daniel Berg / Scherrer  |  BMAp",
     "GEO GSE283418.\nResolve Molecular Cartography.\n98-gene smFISH, amygdala sections\nbregma -1.155 to -1.955.\nPain unpleasantness study.\n\nNOT Hochgerner Visium.\nRAW 8.3 GB images not downloaded.\nGene list from GPL35157 is enough.\n\nAsk: which of Dan's spatial genes\nare informative in our BMAp ROI?", TEAL_RGB)
add_footer(s, 3)

# 4 current panel
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Current shared panel on MSGS111")
add_sub(s, "Xenium Mouse Brain v1 base (~248 genes) is free. Custom add-on cap is 100.")
bullets(s, [
    "Original curated shared list: 144 genes  |  44 free on base  |  100 custom  |  20/20 cell types separable",
    "After Dan append: 158 genes  |  44 free  |  114 custom if all 14 are kept",
    "ORBm_ORDER 140 (unchanged by Dan).  BMAp_ORDER 140 (126 + 14).",
    "Blocks: cell-type separators, reporter/transgene, class backbone, IEG, GPCRs, TFs, plasticity, published regional, then 12_GSE283418_added.",
    "TRAP2 x Ai14, Active vs yoked Passive, tag at Post. PIs: Mark Schnitzer and Gregory Scherrer.",
], top=1.35, size=17)
add_footer(s, 4)

# 5 Dan experiment
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL_RGB)
add_title(s, "Dan  |  GSE283418 spatial transcriptomics")
add_sub(s, "Berg + Scherrer  |  Resolve Molecular Cartography  |  98-gene panel GPL35157")
bullets(s, [
    "Paper: Spatial molecular profiling of amygdalar neurons enables precision pharmacology against pain unpleasantness.",
    "Method: smFISH (Resolve), not Visium, not Xenium. Amygdala coronal sections.",
    "We used the 98-gene platform table, then re-scored every gene in Allen BMAp-mapped subclasses.",
    "38 / 98 already on our shared panel (Foxp2, Cartpt, Ebf1, Pdyn, Oprm1, Slc17a7, Drd1/2 ...).",
    "14 were BMAp-informative and missing  —  these are now appended to MSGS111.",
    "The rest are weak in BMAp anchors or mark CEA / glia / immune  —  do not add.",
], top=1.3, size=17)
add_footer(s, 5)

# 6 Dan fig 1
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL_RGB)
add_title(s, "Dan  |  fate of the 98 spatial genes")
add_sub(s, "Source: GSE283418 GPL35157 vs our shared panel, re-scored in Allen BMAp-mapped ROI.")
s.shapes.add_picture(str(p_d1), Inches(1.4), Inches(1.25), Inches(10.5), Inches(5.5))
add_footer(s, 6)

# 7 Dan fig 2
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL_RGB)
add_title(s, "Dan  |  the 14 genes we added")
add_sub(s, "Already on MSGS111 SHARED ranks 145-158, block 12_GSE283418_added. All 14 cost a custom slot.")
s.shapes.add_picture(str(p_d2), Inches(0.7), Inches(1.2), Inches(12.0), Inches(5.6))
add_footer(s, 7)

# 8 Dan anatomy caveat
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL_RGB)
add_title(s, "Dan 14  |  not all are BMAp nucleus")
add_sub(s, "Allen re-score is in our BMAp-mapped ROI, which includes MEA / CEA neighbors.")
card(s, 0.5, 1.35, 4.0, 5.2, "Closest to true BMAp",
     "Lamb3\n113 MEA-COA-BMA Ccdc42\n\nCck, Col23a1, Slc29a4\nAbca8a, Dnah5\n012 MEA Slc17a7\nVGLUT1 border\n(BMA / MEA overlap)", TEAL_RGB)
card(s, 4.7, 1.35, 4.0, 5.2, "MEA / BST neighbors",
     "Calcrl, Nos1, Oprl1\n120 MEA Otp Foxp2\n\nGfra1\n121 MEA-BST Otp Zic2\n\nSp8\n073 MEA-BST Sox6 GABA", GOLD_RGB)
card(s, 8.9, 1.35, 4.0, 5.2, "CEA / other  |  keep only if wanted",
     "Syndig1l, Gabre\n082 CEA-BST Ebf1 Pdyn\n\nTspan18\n119 SI-MA-LPO-LHA Skor1\n\nUseful if the slide\nincludes CEA/MEA.\nNot required for\nBMAp cell-type ID.", RUST_RGB)
add_footer(s, 8)

# 9 Jesse experiment
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Jesse  |  PL-ILA-ORB morphine dependence")
add_sub(s, "OpioidDependenceDEG genesets  |  5-day escalating morphine  |  DESeq2 padj 0.1")
bullets(s, [
    "Four DEG lists: IEG (77), transcription factors (179), synaptic plasticity (45), GPCRs (34).",
    "Plus GPCRs enriched in PL-ILA-ORB vs the rest of the Allen 4M-cell atlas (Fisher, FDR 0.05).",
    "Most IEG / plasticity genes are Up. The hottest cells are 004 L6 IT, 030 L6 CT, 006 L4/5 IT, 022 L5 ET.",
    "Classic activity IEGs (Fos, Arc, Egr1, Junb, Nr4a1) are already on our panel.",
    "What is new: delayed / circadian IEGs (Per2, Pcsk1, Per1) and ORB-enriched GPCRs (Rxfp1, Mas1, Gpr68).",
    "Jesse: check abundance on their MERFISH before adding many TFs.",
], top=1.3, size=17)
add_footer(s, 9)

# 10-13 Jesse figures
for i, (fn, title, sub, n) in enumerate([
    ("Jesse_Fig1_DEG_overview.png", "Jesse  |  DEG list size and direction",
     "TF list is largest. IEG and plasticity are mostly Up. GPCR DEGs split Up/Down.", 10),
    ("Jesse_Fig2_top_IEG_plasticity.png", "Jesse  |  widest IEG and plasticity DEGs",
     "Per2 and Pcsk1 hit more ORBm subclasses than Fos/Arc. Camk2g is the widest Down plasticity gene.", 11),
    ("Jesse_Fig3_IEG_by_subclass.png", "Jesse  |  which cell types change IEG",
     "Morphine IEG response is glutamatergic-cortical. GABA (Pvalb / Vip / Sst) is weaker.", 12),
    ("Jesse_Fig4_enriched_GPCRs.png", "Jesse  |  GPCRs enriched in PL-ILA-ORB vs atlas",
     "This is who lives in ORB, not necessarily what morphine changes. Rxfp1 is free on the Xenium base panel.", 13),
    ("Jesse_Fig5_IEG_subclass_matrix.png", "Jesse  |  top 20 IEG DEGs x subclass",
     "Filled = differentially expressed. Per2 / Pcsk1 / Arc / Fos cut across the main ORBm excitatory types.", 14),
], start=0):
    s = prs.slides.add_slide(BLANK)
    add_bar(s, NAVY_RGB)
    add_title(s, title)
    add_sub(s, sub)
    img = DL / fn
    s.shapes.add_picture(str(img), Inches(0.9), Inches(1.2), Inches(11.5), Inches(5.6))
    add_footer(s, n)

# 15 Jesse vs panel
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Jesse vs current panel")
add_sub(s, "Core dependence genes are already covered. The missing layer is morphine-state extras.")
card(s, 0.5, 1.35, 6.1, 5.3, "Already on SHARED",
     "IEG: Fos Arc Egr1 Junb Nr4a1\nNr4a2 Fosb Npas4 Bdnf\n\nGPCR / opioid: Oprm1 Oprd1\nOprk1 Oprl1 Ntsr1 Grm5\nHtr1b Chrm2 Htr1a Htr2c\n\nEnriched ORB GPCRs: 28 / 127\nincluding Cnr1 Drd1/2 Cckbr Oxtr", NAVY_RGB)
card(s, 6.8, 1.35, 6.0, 5.3, "Missing and worth a slot",
     "FREE: Rxfp1 (19 subclasses)\nSema3e   Bhlhe40\n\nBroad ORBm DEGs:\nPer2 (11)  Pcsk1 (9)  Per1 (8)\nNr4a3  Dusp1  Egr3  Crem\n\nOptional: Mas1  Gpr68\nHrh1  Grm2  Camk2g\n\nSkip most of the 160 TFs\nunless MERFISH is high.", GOLD_RGB)
add_footer(s, 15)

# 16 decision figure
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Decision  |  keep  /  added  /  proposed")
add_sub(s, "Dan 14 are already on the workbook. Jesse shortlist is the only open add.")
s.shapes.add_picture(str(p_dec), Inches(0.6), Inches(1.15), Inches(12.1), Inches(5.7))
add_footer(s, 16)

# 17 add list
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Genes to add on the custom probe panel")
add_sub(s, "Green = already written onto MSGS111. Gold = recommended next, not yet appended.")
rows = [
    ["Status", "Gene", "Source", "Why", "Slot"],
    ["ADDED", "Lamb3", "Dan GSE283418", "Closest true BMAp (113 Ccdc42)", "1 custom"],
    ["ADDED", "Cck, Col23a1, Slc29a4, Abca8a, Dnah5", "Dan", "012 VGLUT1 BMA/MEA border", "5 custom"],
    ["ADDED", "Calcrl, Nos1, Oprl1, Gfra1, Sp8", "Dan", "MEA / BST neighbors on the slide", "5 custom"],
    ["ADDED", "Syndig1l, Gabre, Tspan18", "Dan", "CEA / SI border; optional", "3 custom"],
    ["PROPOSED", "Rxfp1", "Jesse enriched GPCR", "19 PL-ILA-ORB subclasses", "FREE (base)"],
    ["PROPOSED", "Per2, Pcsk1, Per1", "Jesse IEG DEG", "Widest ORBm morphine DEGs we lack", "3 custom"],
    ["PROPOSED", "Nr4a3, Dusp1, Egr3", "Jesse IEG", "IEG family we only partly cover", "3 custom"],
    ["PROPOSED", "Mas1 or Gpr68; Hrh1; Grm2", "Jesse GPCR / plast.", "Optional morphine + ORB GPCR layer", "3-4 custom"],
]
table = s.shapes.add_table(len(rows), 5, Inches(0.4), Inches(1.25), Inches(12.5), Inches(5.6)).table
widths = [1.3, 3.6, 2.4, 3.7, 1.5]
for i, w in enumerate(widths):
    table.columns[i].width = Inches(w)
for r, row in enumerate(rows):
    for c, val in enumerate(row):
        cell = table.cell(r, c)
        cell.text = val
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(11)
            p.font.name = "Calibri"
            p.font.bold = r == 0
            p.font.color.rgb = WHITE if r == 0 else INK
        if r == 0:
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY_RGB
        elif row[0] == "ADDED":
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xE8, 0xF1, 0xF8)
        else:
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xF7, 0xF0, 0xE6)
add_footer(s, 17)

# 18 slots
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Slot budget")
add_sub(s, "10x Xenium custom add-on cap = 100. Transgenes always cost a slot.")
bullets(s, [
    "Original shared order: 100 custom + 44 free base = 144 curated genes.",
    "Dan 14 are all custom  ->  114 custom if we keep every Dan gene.",
    "Jesse Rxfp1 is FREE (already on Mouse Brain v1 base). Adding it does not use a slot.",
    "Jesse Per2 + Pcsk1 + Per1 + Nr4a3 + Dusp1 + Egr3 = 6 more custom  ->  120 if stacked on Dan 14.",
    "If 10x will not go over 100: keep the original 100, add Rxfp1 for free, and swap (do not append) for any Jesse DEG.",
    "Do not drop Fos, Arc, Egr1, Oprm1, Ntsr1, or unique cell-type separators to make room.",
], top=1.3, size=17)
add_footer(s, 18)

# 19 do not add
s = prs.slides.add_slide(BLANK)
add_bar(s, RUST_RGB)
add_title(s, "Do not add")
card(s, 0.5, 1.35, 6.1, 5.3, "From Dan 98",
     "Low / CEA / glia / immune\nAdora2a  Prkcd  Ptprc\nS100b  Itgal  Blnk  Lgals1\n\nPresent but not specific\nRbms3  Rnd2  Pnoc  Lpl\nSfrp1  C1ql1/2  Bcan\n\nThese do not improve\nBMAp cell-type ID.", RUST_RGB)
card(s, 6.8, 1.35, 6.0, 5.3, "From Jesse lists",
     "Most of 160 missing TFs\nArid5b Banp Chd2 zinc-fingers\nunless MERFISH is abundant.\n\nDo not replace Fos / Arc /\nOprm1 / Ntsr1 with TFs.\n\nGO plasticity can explode.\nKeep the short list only.", GOLD_RGB)
add_footer(s, 19)

# 20 ask
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "What we need from Mark / Greg")
add_sub(s, "The science is set. The only open choice is slot math and whether morphine-state genes are in-scope.")
bullets(s, [
    "Keep the original 144. That panel already IDs all 20 types and covers TRAP + opioid receptors.",
    "Confirm keeping the 14 Dan extras on the order (114 custom), or pick a subset (Lamb3 + Cck/Col23a1 first).",
    "Decide whether the Xenium experiment should read a 5-day morphine signature in ORBm.",
    "If yes: add Rxfp1 (free) plus Per2, Pcsk1, Per1. That is the highest-value Jesse block.",
    "If the cap is hard 100: keep 144, add only Rxfp1, and do not append Dan or Jesse without swaps.",
], top=1.35, size=18)
add_footer(s, 20)

ppt_path = DL / "ORBm_BMAp_Jesse_Dan_panel_decision.pptx"
also = OUT / "ORBm_BMAp_Jesse_Dan_panel_decision.pptx"
prs.save(ppt_path)
prs.save(also)
print("PPT", ppt_path)
print("PPT", also)
print("slides", len(prs.slides))
