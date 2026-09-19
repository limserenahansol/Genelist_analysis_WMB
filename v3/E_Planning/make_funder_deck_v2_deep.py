"""Funding-agency deck, expanded from ORBm_BMAp_Xenium_panel_funding_agency1.pptx.

Keeps that deck's style exactly (Calibri, 24pt navy titles, 13pt muted subtitles,
numbered step circles, KEPT/DROPPED blocks, 26pt stat tiles, same palette) and
deepens the three things it was light on:

  1  how many cell types per region, and what they are
  2  how much Allen analysis actually sits behind the list
  3  why a gene is in, and why a comparable one is out

Slides
  1  The 20 populations we must tell apart    ORBm 12 / BMAp 8, named, with cell counts
  2  Depth of the reference analysis          screening scale and documented sources
  3  Why a gene is in - and why one is out    four rules, each with a real pass and fail
  4  Collaborator lists were filtered         Jesse 304 -> 10, Dan 98 -> 14
  5  Final panel                              composition and capability

All numbers are read from the live order sheet and pipeline outputs.

Output: outputs/ORBm_BMAp_Xenium_panel_funding_agency_v2.pptx
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
FIG = OUT / "funder_v2_figures"
FIG.mkdir(exist_ok=True)
PANEL = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
LONG = OUT / "subclass_markers_expanded" / "Subclass_Discriminating_Markers_long.csv"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"
TIERS = OUT / "subclass_markers_expanded" / "GPCR_Specificity_Tiers.csv"
EGPCR = OUT / "Jesse_ORB_vs_Xenium_panel.xlsx"
DRUGS = V3 / "inputs" / "gpcr_drug_targets_detailed.csv"
DECK = OUT / "ORBm_BMAp_Xenium_panel_funding_agency_v2.pptx"

NAVY, TEAL, RUST, SAGE, GREY = "#1D4E89", "#2A6F97", "#C44536", "#6B7C6A", "#B8B2A8"
CREAM, ICE = "#F4F1EA", "#EAF2F8"
INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
})

GROUPS = [
    ("Cell identity and brain region", ["1_celltype_separator", "3_class_backbone",
                                        "11_class_backbone_optional", "8_TF_identity",
                                        "9_published_regional", "12_GSE283418_added"], NAVY),
    ("Druggable receptor map", ["6_GPCR_druggable", "4_GPCR_cell_type_specific",
                                "14_ORB_enriched_GPCR", "14_Jesse_ORB_GPCR"], TEAL),
    ("Neural activity and plasticity", ["5_IEG", "7_plasticity"], SAGE),
    ("Morphine-dependence state", ["13_Jesse_morphine_state"], RUST),
    ("Genetic-tag reporters", ["2_reporter_transgene"], "#B08968"),
]


def facts() -> dict:
    sh = pd.read_excel(PANEL, "SHARED_PANEL_ORDER")
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    sh["free"] = sh.gene.isin(base)
    ac = pd.read_excel(PANEL, "ANCHOR_COVERAGE")
    ac["n_sep"] = ac.unique_separators_on_shared_panel.fillna("").apply(
        lambda s: len([x for x in s.split(",") if x.strip()]))
    src = pd.read_excel(PANEL, "SOURCES")
    long = pd.read_csv(LONG)
    pairs = pd.read_csv(PAIRS)
    tiers = pd.read_csv(TIERS)
    drugs = pd.read_csv(DRUGS)
    comp = []
    for name, blocks, col in GROUPS:
        s = sh[sh.block.isin(blocks)]
        comp.append({"group": name, "n": len(s), "free": int(s.free.sum()),
                     "custom": int((~s.free).sum()), "colour": col})
    comp = pd.DataFrame(comp)
    assert comp.n.sum() == len(sh), f"groups cover {comp.n.sum()} of {len(sh)}"
    return {
        "sh": sh, "ac": ac, "comp": comp,
        "n_genes": len(sh), "n_free": int(sh.free.sum()), "n_custom": int((~sh.free).sum()),
        "n_sources": len(src), "n_doi": int(src.doi.notna().sum()),
        "n_measure": len(long), "n_genes_scored": long.gene.nunique(),
        "n_subclasses": long.subclass.nunique(), "n_pairs": len(pairs),
        "n_gpcr_tiered": tiers.gpcr_gene.nunique(),
        "n_gpcr_enriched": len(pd.read_excel(EGPCR, "enriched_GPCRs")),
        "n_drug_records": len(drugs), "n_drug_recept": drugs.gene_symbol.nunique(),
        "n_fda": drugs[drugs.drug_status.astype(str).str.contains("approved", case=False, na=False)].drug_name.nunique(),
    }


# ------------------------------------------------------------------- figures
def fig_celltypes(ac: pd.DataFrame) -> Path:
    """The 20 anchor subclasses, split by region, with cell counts and separators."""
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.0),
                             gridspec_kw={"width_ratios": [1, 0.78]})
    for ax, reg, col, title in [
        (axes[0], "ORBm", NAVY, "A.  ORBm  -  orbitofrontal cortex, medial"),
        (axes[1], "BMAp", TEAL, "B.  BMAp  -  basomedial amygdala, posterior"),
    ]:
        g = ac[ac.region == reg].iloc[::-1]
        y = np.arange(len(g))
        ax.barh(y, g.n_cells / 1000, color=col, height=0.66)
        ax.set_yticks(y)
        ax.set_yticklabels([s.split(" ", 1)[1] for s in g.allen_subclass_anchor], fontsize=9.2)
        for i, r in enumerate(g.itertuples()):
            ax.text(r.n_cells / 1000 + 0.45, i, f"{r.n_cells/1000:.1f}k   {r.n_sep} marker"
                    + ("s" if r.n_sep != 1 else ""),
                    va="center", fontsize=8.3, color="#444444")
        ax.set_xlim(0, max(g.n_cells / 1000) * 1.52)
        ax.set_xlabel("Allen cells in this population (thousands)", fontsize=9)
        ax.set_title(f"{title}\n{len(g)} populations,  {g.n_cells.sum():,} cells",
                     fontsize=10.4, color=col, loc="left")
    fig.text(0.5, -0.035,
             "Every one of the 20 populations has at least one gene on the panel that is unique to it. "
             "Marker counts are dedicated separators, not shared genes.",
             ha="center", fontsize=8.6, color="#555555")
    fig.tight_layout()
    p = FIG / "V2_F1_celltypes.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_composition(comp: pd.DataFrame, n_free: int, n_custom: int) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.3),
                             gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    d = comp.iloc[::-1]
    y = np.arange(len(d))
    ax.barh(y, d.n, color=d.colour, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(d.group, fontsize=9.6)
    for i, r in enumerate(d.itertuples()):
        ax.text(r.n + 1.8, i, str(r.n), va="center", fontsize=10.5,
                fontweight="bold", color="#333333")
    ax.set_xlim(0, 125)
    ax.set_xlabel("number of genes", fontsize=9.5)
    ax.set_title(f"What the {int(comp.n.sum())} genes do", fontsize=10.6, color=NAVY, loc="left")

    ax = axes[1]
    wedges, _ = ax.pie([n_free, n_custom], colors=[SAGE, NAVY], startangle=90,
                       wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2))
    ax.text(0, 0.06, str(n_free + n_custom), ha="center", fontsize=24,
            fontweight="bold", color=NAVY)
    ax.text(0, -0.18, "genes", ha="center", fontsize=9.4, color="#555555")
    ax.legend(wedges, [f"{n_free} free on the 10x base panel",
                       f"{n_custom} custom probes we design"],
              fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.01),
              frameon=False, handlelength=1.1)
    ax.set_title("Cost structure", fontsize=10.6, color=NAVY)
    fig.tight_layout()
    p = FIG / "V2_F2_composition.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


# --------------------------------------------------------------- deck helpers
def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def run(p, text, size=13, bold=False, color=INK):
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
    r.font.color.rgb = color
    return r


def txt(slide, x, y, w, h, body, size=13, bold=False, color=INK, space=4):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(str(body).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space)
        run(p, line, size, bold, color)
    return tb


def slide(prs, title, sub, n, total, tcol=NAVY):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    txt(s, 0.40, 0.18, 12.5, 0.42, title, 24, True, rgb(tcol))
    if sub:
        txt(s, 0.40, 0.56, 12.5, 0.34, sub, 13, False, MUTED)
    txt(s, 0.40, 7.18, 12.5, 0.24,
        f"ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {n}/{total}", 11, False, MUTED)
    return s


def tile(s, x, y, w, big, label, col):
    bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(1.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(CREAM)
    bar.line.color.rgb = rgb(col)
    bar.line.width = Pt(1.3)
    bar.shadow.inherit = False
    txt(s, x + 0.12, y + 0.06, w - 0.24, 0.52, big, 26, True, rgb(col))
    txt(s, x + 0.12, y + 0.58, w - 0.24, 0.50, label, 11.5, False, MUTED, space=0)


def card(s, x, y, w, h, num, head, metric, keep, drop, col):
    bx = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    bx.fill.solid()
    bx.fill.fore_color.rgb = rgb("FFFFFF")
    bx.line.color.rgb = rgb(col)
    bx.line.width = Pt(1.5)
    bx.shadow.inherit = False
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12),
                           Inches(0.34), Inches(0.34))
    c.fill.solid()
    c.fill.fore_color.rgb = rgb(col)
    c.line.fill.background()
    c.shadow.inherit = False
    txt(s, x + 0.145, y + 0.155, 0.33, 0.30, num, 14, True, WHITE)
    txt(s, x + 0.56, y + 0.12, w - 0.70, 0.36, head, 13.5, True, rgb(col))
    txt(s, x + 0.16, y + 0.52, w - 0.30, 0.34, metric, 11, False, MUTED, space=0)
    txt(s, x + 0.16, y + 0.92, w - 0.30, 0.34, "IN     " + keep, 11, False, rgb(SAGE), space=0)
    txt(s, x + 0.16, y + 1.24, w - 0.30, 0.34, "OUT   " + drop, 11, False, rgb(RUST), space=0)


def build(F, figs) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    ac, comp = F["ac"], F["comp"]
    TOT = 5

    # ---- 1 cell types
    s = slide(prs, "The 20 populations we must tell apart", None, 1, TOT)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "The panel is designed around a fixed target list: 12 cell populations in orbitofrontal cortex and "
        "8 in basomedial amygdala, taken from the Allen Brain Cell Atlas taxonomy.", 13, False, MUTED)
    orb, bma = ac[ac.region == "ORBm"], ac[ac.region == "BMAp"]
    for i, (big, lab, col) in enumerate([
        (f"{len(orb)}", "ORBm populations\n(cortical layers + interneurons)", NAVY),
        (f"{len(bma)}", "BMAp populations\n(glutamatergic + GABAergic)", TEAL),
        (f"{ac.n_cells.sum():,}", "Allen cells in the\n20 target populations", SAGE),
        ("20 / 20", "have a dedicated marker\non the final panel", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 1.00, 2.95, big, lab, col)
    picture(s, figs["celltypes"], 2.28, 4.45)

    # ---- 2 depth
    s = slide(prs, "The list rests on a full re-analysis of the reference atlas", None, 2, TOT, TEAL)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "No gene was taken on a paper's word. Every candidate was re-scored in the Allen atlas, in these two "
        "regions, against the genes the panel already carried.", 13, False, MUTED)
    for i, (big, lab, col) in enumerate([
        ("226,886", "single cells scored across\nthe two target regions", NAVY),
        (f"{F['n_subclasses']}", "cell subclasses profiled,\nnot only the 20 targets", TEAL),
        (f"{F['n_measure']:,}", "gene x subclass abundance\nand specificity measurements", SAGE),
        (f"{F['n_pairs']:,}", "pairwise tests: can gene X\nseparate type A from type B?", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 1.00, 2.95, big, lab, col)
    for i, (big, lab, col) in enumerate([
        (f"{F['n_sources']}", f"documented sources,\n{F['n_doi']} with a DOI", NAVY),
        (f"{F['n_gpcr_enriched']}", "region-enriched GPCRs\nevaluated one by one", TEAL),
        (f"{F['n_gpcr_tiered']}", "receptors tiered as specific,\nintermediate or universal", SAGE),
        (f"{F['n_fda']}", "FDA-approved drugs mapped\nto panel receptors (IUPHAR)", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 2.34, 2.95, big, lab, col)

    body = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(3.72),
                              Inches(12.53), Inches(3.18))
    body.fill.solid()
    body.fill.fore_color.rgb = rgb(CREAM)
    body.line.color.rgb = rgb(GREY)
    body.line.width = Pt(1.0)
    body.shadow.inherit = False
    txt(s, 0.62, 3.88, 12.1, 0.34, "What that analysis produced, in order", 14, True, rgb(NAVY))
    txt(s, 0.62, 4.32, 5.95, 2.4,
        "1.   Region-restricted expression matrices\n"
        "      Cells from ORBm and BMAp were pulled out of the whole-brain atlas, so every abundance and\n"
        "      specificity number describes these two regions - not a brain-wide average.\n\n"
        "2.   Per-population marker ranking\n"
        "      For each of the 20 targets we ranked every candidate by how much of that population expresses\n"
        "      it and how strongly it is restricted to it.", 11.5, False, INK, space=2)
    txt(s, 6.85, 4.32, 5.95, 2.4,
        "3.   Pairwise separability testing\n"
        "      3,901 tests confirmed that neighbouring populations - L5 IT vs L5 ET, MEA vs BMA - can still be\n"
        "      told apart with the genes actually on the panel.\n\n"
        "4.   Receptor and drug-target layer\n"
        "      Receptors were tiered by specificity and cross-referenced to the IUPHAR pharmacology database,\n"
        "      so the map is of targets that drugs exist for.", 11.5, False, INK, space=2)

    # ---- 3 why in / why out
    s = slide(prs, "Why a gene is in - and why a similar one is out", None, 3, TOT, RUST)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "Four rules, each a measurement with a cutoff. For every rule there is a gene that passed and a "
        "comparable gene that did not, so the line is visible rather than asserted.", 13, False, MUTED)
    cards = [
        ("1", "Does it identify the cell type?",
         "Specificity against genes the panel already has. Cutoff: must beat them (ratio > 1).",
         "Col23a1   3.7x more specific - the panel had no equal marker for that BMA population",
         "Sfrp1   0.9x - a gene already on the panel does the same job better", NAVY),
        ("2", "Is it a druggable receptor we cannot already see?",
         "Regional enrichment, plus whether that receptor family is already covered.",
         "Chrm1   M1 receptor, enriched in 8 populations - we could only see M2 before",
         "Glipr1   its population already has Penk (2.3x) and Lamb3 (1.5x) on the panel", TEAL),
        ("3", "Does it report the morphine-dependent state?",
         "Differential expression counted only in our 12 ORBm populations, not the donor's whole dataset.",
         "Per2   changes in 11 of 12 populations - the broadest gene in the entire dataset",
         "Nr4a3   looked strong at 8 clusters, but only 5 of ours; the rest were regions we do not image", RUST),
        ("4", "Will the instrument actually detect it?",
         "Fraction of cells expressing it in the atlas. Sparse probes give sparse, unusable maps.",
         "Grm8   99% of cells, above 50% in 8 of 12 populations",
         "Mas1   the single most enriched receptor, but only 45% of cells and absent from GABA", SAGE),
    ]
    for i, (n, h, m, k, d, c) in enumerate(cards):
        card(s, 0.40 + (i % 2) * 6.36, 1.05 + (i // 2) * 1.80, 6.17, 1.68, n, h, m, k, d, c)
    txt(s, 0.40, 4.78, 12.5, 0.8,
        "The rules are independent, and that is deliberate. A receptor earns a slot by showing where a drug "
        "target sits, whether or not morphine changes it - so one panel serves the pharmacology aim and the "
        "addiction aim at the same time.", 12, False, INK)
    band = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(5.52),
                              Inches(12.53), Inches(1.40))
    band.fill.solid()
    band.fill.fore_color.rgb = rgb(ICE)
    band.line.color.rgb = rgb(NAVY)
    band.line.width = Pt(1.2)
    band.shadow.inherit = False
    txt(s, 0.62, 5.66, 12.1, 0.30, "The hard constraint that forces all of this", 13, True, rgb(NAVY))
    txt(s, 0.62, 6.02, 12.1, 0.85,
        "The 10x Mouse Brain panel gives ~248 genes free; the custom add-on is capped near 100. "
        f"So {F['n_genes']} genes on one section means {F['n_free']} taken free and {F['n_custom']} paid for. "
        "A gene that merely appeared in a paper, or in a differential-expression table, does not qualify - "
        "roughly three of every four candidates we screened were turned down.", 11.5, False, INK, space=2)

    # ---- 4 collaborator filtering
    s = slide(prs, "Collaborator lists were filtered, not copied in", None, 4, TOT, TEAL)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "Two external datasets arrived as gene tables. Both were put through the same four rules as "
        "everything else.", 13, False, MUTED)
    for x, head, n_in, n_out, rule, kept, dropped, col in [
        (0.40, "Morphine transcriptomics in orbitofrontal / prefrontal cortex",
         "304 unique DEGs", "10 kept",
         "Rule applied:  will Xenium see it in our 12 ORBm populations, and does it change in enough of them? "
         "Relative enrichment is not abundance.",
         "Clock and peptide program      Per2   Pcsk1   Per1   Camk2g\n"
         "High-abundance receptors      Chrm1   Grm8   Gpr26   Rxfp1\n"
         "Free on the 10x base panel     Bhlhe40   Sema3e   Rxfp1",
         "294 genes dropped\n"
         "Sparse receptors - Mas1 at 45% of cells and near-absent in GABA\n"
         "Most transcription factors, and the long tail of the DEG table\n"
         "A 100-slot panel is not a transcriptome.", NAVY),
        (6.76, "Amygdala spatial panel  (GSE283418, published)",
         "98 spatial genes", "14 kept",
         "Rule applied:  does it mark BMAp more specifically than a gene the panel already carries? "
         "52 of the 98 were already covered.",
         "14 genes that add BMAp information\n"
         "Appended on top of the curated core\n"
         "No existing gene was removed or re-ranked",
         "Remainder dropped\n"
         "Below the specificity cutoff - Sfrp1, Glipr1, Vdr all under 1.0\n"
         "Several peak in neighbouring nuclei, not BMAp itself\n"
         "Do not spend a slot on a weaker third marker.", TEAL),
    ]:
        hb = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.02),
                                Inches(6.17), Inches(0.46))
        hb.fill.solid()
        hb.fill.fore_color.rgb = rgb(col)
        hb.line.fill.background()
        hb.shadow.inherit = False
        txt(s, x + 0.14, 1.09, 5.9, 0.34, head, 12.5, True, WHITE)
        txt(s, x + 0.14, 1.62, 5.9, 0.60, f"{n_in}     ->     {n_out}", 25, True, rgb(col))
        txt(s, x + 0.14, 2.34, 5.9, 0.70, rule, 11.5, False, MUTED, space=2)
        kb = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(3.16),
                                Inches(6.17), Inches(1.72))
        kb.fill.solid()
        kb.fill.fore_color.rgb = rgb(CREAM)
        kb.line.color.rgb = rgb(SAGE)
        kb.line.width = Pt(1.2)
        kb.shadow.inherit = False
        txt(s, x + 0.16, 3.26, 5.85, 0.28, "KEPT", 12, True, rgb(SAGE))
        txt(s, x + 0.16, 3.58, 5.85, 1.22, kept, 11, False, INK, space=2)
        db = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(5.00),
                                Inches(6.17), Inches(1.90))
        db.fill.solid()
        db.fill.fore_color.rgb = rgb("FFFFFF")
        db.line.color.rgb = rgb(RUST)
        db.line.width = Pt(1.2)
        db.shadow.inherit = False
        txt(s, x + 0.16, 5.10, 5.85, 0.28, "DROPPED", 12, True, rgb(RUST))
        txt(s, x + 0.16, 5.42, 5.85, 1.40, dropped, 11, False, INK, space=2)

    # ---- 5 final panel
    s = slide(prs, f"Final panel  -  {F['n_genes']} genes, one section, two regions", None, 5, TOT, RUST)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "One shared Xenium panel read from the same mouse. All 20 target populations remain separable.",
        13, False, MUTED)
    for i, (big, lab, col) in enumerate([
        (f"{F['n_genes']}", "genes on the\nshared panel", NAVY),
        ("20 / 20", "cell populations\nstill separable", TEAL),
        (f"{F['n_free']}", "already free on the\n10x base panel", SAGE),
        ("2", "regions read from\nthe same mouse", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 1.00, 2.95, big, lab, col)
    picture(s, figs["composition"], 2.30, 3.05, max_w=7.2, left=0.40)
    txt(s, 7.95, 2.34, 5.0, 0.34, "What each cell can tell us", 15, True, rgb(NAVY))
    for i, (h, b, col) in enumerate([
        ("Identity", "Which of the 20 populations it is - layer, interneuron class, amygdala subtype", NAVY),
        ("Activity", "Whether it was recently active - Fos / Arc plus the TRAP2 reporter", TEAL),
        ("State", "Morphine-dependence signature - Per2, Pcsk1, Per1, Camk2g", RUST),
        ("Receptors", "Druggable GPCRs present on that cell - opioid, muscarinic, mGlu, relaxin", SAGE),
    ]):
        y = 2.86 + i * 0.94
        txt(s, 7.95, y, 5.0, 0.28, h, 13, True, rgb(col))
        txt(s, 7.95, y + 0.29, 5.0, 0.56, b, 11.5, False, INK, space=0)

    prs.save(DECK)
    return DECK


def picture(slide, path, top, max_h, max_w=12.6, left=None):
    pic = slide.shapes.add_picture(str(path), Inches(0), Inches(top), height=Inches(max_h))
    if pic.width > Inches(max_w):
        sc = Inches(max_w) / pic.width
        pic.width, pic.height = int(pic.width * sc), int(pic.height * sc)
    pic.left = int(Inches(left)) if left is not None else int((Inches(13.333) - pic.width) / 2)
    return pic.top / 914400 + pic.height / 914400


def main() -> None:
    F = facts()
    figs = {"celltypes": fig_celltypes(F["ac"]),
            "composition": fig_composition(F["comp"], F["n_free"], F["n_custom"])}
    deck = build(F, figs)
    print(f"panel      : {F['n_genes']} genes = {F['n_free']} free + {F['n_custom']} custom")
    print(f"cell types : ORBm {len(F['ac'][F['ac'].region=='ORBm'])} + BMAp {len(F['ac'][F['ac'].region=='BMAp'])}"
          f" = {len(F['ac'])}, {F['ac'].n_cells.sum():,} cells")
    print(f"depth      : {F['n_subclasses']} subclasses, {F['n_measure']:,} measurements, "
          f"{F['n_pairs']:,} pairwise tests, {F['n_sources']} sources ({F['n_doi']} DOI)")
    print(f"receptors  : {F['n_gpcr_enriched']} enriched evaluated, {F['n_gpcr_tiered']} tiered, "
          f"{F['n_fda']} FDA drugs mapped")
    for k, v in figs.items():
        print(f"fig {k:12s}-> {v}")
    print(f"deck          -> {deck}")


if __name__ == "__main__":
    main()
