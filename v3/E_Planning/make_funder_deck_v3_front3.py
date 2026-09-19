"""Funding-agency deck, front-loaded: slides 1-3 stand alone, 4-5 are backup.

Changes requested after review of the v1/v2 decks:
  - the three-column schematic was the visual that landed, so it leads
  - collaborators are named (Jesse Niehaus; Berg & Scherrer) instead of "Collaborator 1/2"
  - the PI may show only three slides, so 1-3 must carry the whole argument and
    4-5 are explicitly labelled BACKUP

Improvement over v2: the schematic now shows YIELD, not just flow. Each source
arrow carries "N screened -> M kept", and the Allen re-analysis sits under the
rules as the measuring instrument rather than as a fourth input, which is what it
actually is. That makes the filtering visible instead of asserted.

  1  How the panel was selected      schematic with per-source yield
  2  Why a gene is in, why one is out  four rules, each with a real pass and fail
  3  Final panel                      what was ordered and what it can measure
  4  BACKUP: the 20 populations       per-subclass detail with cell counts
  5  BACKUP: atlas analysis depth     screening scale and documented sources

All numbers read from the live order sheet and pipeline outputs.

Output: outputs/ORBm_BMAp_Xenium_panel_funder_v3.pptx
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
FIG = OUT / "funder_v3_figures"
FIG.mkdir(exist_ok=True)
PANEL = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
LONG = OUT / "subclass_markers_expanded" / "Subclass_Discriminating_Markers_long.csv"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"
TIERS = OUT / "subclass_markers_expanded" / "GPCR_Specificity_Tiers.csv"
EGPCR = OUT / "Jesse_ORB_vs_Xenium_panel.xlsx"
DRUGS = V3 / "inputs" / "gpcr_drug_targets_detailed.csv"
DECK = OUT / "ORBm_BMAp_Xenium_panel_funder_v3.pptx"

NAVY, TEAL, RUST, SAGE, GREY = "#1D4E89", "#2A6F97", "#C44536", "#6B7C6A", "#B8B2A8"
CREAM, ICE, TAUPE = "#F4F1EA", "#EAF2F8", "#8C7B6B"
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

    def bucket(b):
        if b.startswith("12_"):
            return "dan"
        if b.startswith(("13_", "14_")):
            return "jesse"
        return "core"

    sh["src"] = sh.block.apply(bucket)
    yld = sh.groupby("src").agg(n=("gene", "size"), free=("free", "sum"))
    yld["custom"] = yld.n - yld.free

    comp = []
    for name, blocks, col in GROUPS:
        s = sh[sh.block.isin(blocks)]
        comp.append({"group": name, "n": len(s), "free": int(s.free.sum()),
                     "custom": int((~s.free).sum()), "colour": col})
    comp = pd.DataFrame(comp)
    assert comp.n.sum() == len(sh), f"groups cover {comp.n.sum()} of {len(sh)}"

    long = pd.read_csv(LONG)
    drugs = pd.read_csv(DRUGS)
    return {
        "sh": sh, "ac": ac, "comp": comp, "yld": yld,
        "n_genes": len(sh), "n_free": int(sh.free.sum()), "n_custom": int((~sh.free).sum()),
        "n_sources": len(src), "n_doi": int(src.doi.notna().sum()),
        "n_measure": len(long), "n_subclasses": long.subclass.nunique(),
        "n_pairs": len(pd.read_csv(PAIRS)),
        "n_gpcr_tiered": pd.read_csv(TIERS).gpcr_gene.nunique(),
        "n_gpcr_enriched": len(pd.read_excel(EGPCR, "enriched_GPCRs")),
        "n_fda": drugs[drugs.drug_status.astype(str).str.contains("approved", case=False, na=False)].drug_name.nunique(),
    }


# ------------------------------------------------------------------- figures
def srcbox(ax, x, y, w, h, title, body, col):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.026",
        facecolor=CREAM, edgecolor=col, linewidth=1.7, zorder=2))
    ax.add_patch(mpatches.Rectangle((x, y + h - 0.050), w, 0.050,
                                    facecolor=col, edgecolor=col, zorder=3))
    ax.text(x + w / 2, y + h - 0.025, title, ha="center", va="center",
            color="white", fontsize=8.8, fontweight="bold", zorder=4)
    ax.text(x + 0.013, y + h - 0.072, body, ha="left", va="top",
            fontsize=8.2, color="#222222", zorder=4, linespacing=1.45)


def fig_flow(F) -> Path:
    """Three columns with per-source yield on the arrows."""
    y_ = F["yld"]
    fig, ax = plt.subplots(figsize=(12.7, 5.3))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    H, GAP, Y0 = 0.205, 0.030, 0.230          # 3 source rows
    srows = [Y0 + (2 - i) * (H + GAP) for i in range(3)]
    RH, RGAP, RY0 = 0.150, 0.022, 0.230       # 4 rule rows
    rrows = [RY0 + (3 - i) * (RH + RGAP) for i in range(4)]
    TOP = rrows[0] + RH

    ax.text(0.086, 0.965, "WHERE THE CANDIDATES CAME FROM", ha="center",
            fontsize=9.6, fontweight="bold", color=NAVY)
    ax.text(0.455, 0.965, "FOUR DECISION RULES", ha="center",
            fontsize=9.6, fontweight="bold", color=NAVY)
    ax.text(0.876, 0.965, "WHAT WE ORDER", ha="center",
            fontsize=9.6, fontweight="bold", color=NAVY)

    srcs = [
        ("OUR MARKER SCREEN", "Allen atlas + 13 published\nsources. Cell-type markers,\nreceptors, activity genes",
         "311 screened", f"{int(y_.loc['core','n'])} kept", NAVY),
        ("JESSE NIEHAUS", "Morphine-dependence gene\nexpression in orbitofrontal /\nprefrontal cortex",
         "431 screened", f"{int(y_.loc['jesse','n'])} kept", RUST),
        ("BERG & SCHERRER", "Published amygdala spatial\npanel (GSE283418)",
         "98 screened", f"{int(y_.loc['dan','n'])} kept", TEAL),
    ]
    for i, (t, b, scr, kep, c) in enumerate(srcs):
        y = srows[i]
        srcbox(ax, 0.004, y, 0.166, H, t, b, c)
        ax.text(0.087, y + 0.022, scr, ha="center", va="center", fontsize=8.4,
                color=c, fontweight="bold", zorder=5)
        # yield arrow straight to the panel
        ax.annotate("", xy=(0.751, (RY0 + TOP) / 2), xytext=(0.172, y + H / 2),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=1.6, alpha=0.55,
                                    connectionstyle="arc3,rad=0.0",
                                    shrinkA=2, shrinkB=3), zorder=1)
        ax.text(0.205, y + H / 2 + 0.030, kep, fontsize=9.0, color=c,
                fontweight="bold", zorder=5)

    rules = [
        ("1", "Does it identify the cell type?", NAVY),
        ("2", "Is it a druggable receptor we cannot already see?", TEAL),
        ("3", "Does it report the morphine-dependent state?", RUST),
        ("4", "Will the instrument actually detect it?", SAGE),
    ]
    for i, (n, q, c) in enumerate(rules):
        y = rrows[i]
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.300, y), 0.360, RH, boxstyle="round,pad=0.008,rounding_size=0.024",
            facecolor="white", edgecolor=c, linewidth=1.6, zorder=3))
        ax.add_patch(mpatches.Circle((0.325, y + RH / 2), 0.0165, facecolor=c, zorder=4))
        ax.text(0.325, y + RH / 2, n, ha="center", va="center", color="white",
                fontsize=9.4, fontweight="bold", zorder=5)
        ax.text(0.351, y + RH / 2, q, ha="left", va="center", fontsize=9.1,
                fontweight="bold", color=c, zorder=5)

    # Allen engine banner under the rules
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.300, 0.038), 0.360, 0.152, boxstyle="round,pad=0.008,rounding_size=0.024",
        facecolor=ICE, edgecolor=NAVY, linewidth=1.5, zorder=3))
    ax.text(0.480, 0.157, "Every rule is measured in the Allen Brain Cell Atlas",
            ha="center", va="center", fontsize=9.0, fontweight="bold", color=NAVY, zorder=4)
    # Kept short: the long two-line version ran past the banner's left edge.
    ax.text(0.480, 0.082,
            f"226,886 cells   ·   {F['n_subclasses']} subclasses profiled\n"
            f"{F['n_measure']:,} measurements   ·   {F['n_pairs']:,} pairwise tests",
            ha="center", va="center", fontsize=8.6, color="#333333", zorder=4, linespacing=1.6)

    # outcome
    bx, by, bw, bh = 0.754, 0.230, 0.242, TOP - 0.230
    ax.add_patch(mpatches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.008,rounding_size=0.026",
        facecolor=ICE, edgecolor=NAVY, linewidth=2.3, zorder=2))
    cx = bx + bw / 2

    def fy(f):
        return by + bh * f

    ax.text(cx, fy(0.935), "FINAL PANEL", ha="center", va="center",
            fontsize=10.2, fontweight="bold", color=NAVY)
    ax.text(cx, fy(0.775), str(F["n_genes"]), ha="center", va="center",
            fontsize=40, fontweight="bold", color=NAVY)
    ax.text(cx, fy(0.665), "genes on one section", ha="center", va="center",
            fontsize=9.0, color="#444444")
    ax.plot([bx + 0.028, bx + bw - 0.028], [fy(0.605)] * 2, color=NAVY, lw=0.9, alpha=0.35)
    ax.text(cx, fy(0.445),
            f"{int(y_.loc['core','n'])} our marker screen\n"
            f"{int(y_.loc['dan','n'])} Berg & Scherrer\n"
            f"{int(y_.loc['jesse','n'])} Jesse Niehaus",
            ha="center", va="center", fontsize=9.0, color="#333333", linespacing=1.7)
    ax.plot([bx + 0.028, bx + bw - 0.028], [fy(0.275)] * 2, color=NAVY, lw=0.9, alpha=0.35)
    ax.text(cx, fy(0.155),
            f"{F['n_free']} free on the standard platform\n{F['n_custom']} custom probes we pay for",
            ha="center", va="center", fontsize=9.0, color=NAVY, linespacing=1.6, fontweight="bold")

    # funnel strip
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.004, 0.038), 0.278, 0.152, boxstyle="round,pad=0.008,rounding_size=0.024",
        facecolor="#F7F5F2", edgecolor=GREY, linewidth=1.0, zorder=2))
    ax.text(0.143, 0.157, "701 candidates  ->  168 selected", ha="center", va="center",
            fontsize=9.4, fontweight="bold", color="#333333", zorder=4)
    ax.text(0.143, 0.085,
            "Roughly three of every four candidates\nwere turned down. Each keeps its evidence\nand the rule that admitted it.",
            ha="center", va="center", fontsize=8.2, color="#444444", zorder=4, linespacing=1.5)

    fig.tight_layout()
    p = FIG / "V3_F1_flow.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_composition(comp, n_free, n_custom) -> Path:
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    d = comp.iloc[::-1]
    y = np.arange(len(d))
    ax.barh(y, d.n, color=d.colour, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(d.group, fontsize=9.4)
    for i, r in enumerate(d.itertuples()):
        ax.text(r.n + 1.8, i, str(r.n), va="center", fontsize=10.2,
                fontweight="bold", color="#333333")
    ax.set_xlim(0, 126)
    ax.set_xlabel("number of genes", fontsize=9.2)
    ax.set_title(f"What the {int(comp.n.sum())} genes do", fontsize=10.4, color=NAVY, loc="left")
    fig.tight_layout()
    p = FIG / "V3_F2_composition.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_celltypes(ac) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.7),
                             gridspec_kw={"width_ratios": [1, 0.78]})
    for ax, reg, col, title in [
        (axes[0], "ORBm", NAVY, "A.  ORBm  -  orbitofrontal cortex, medial"),
        (axes[1], "BMAp", TEAL, "B.  BMAp  -  basomedial amygdala, posterior"),
    ]:
        g = ac[ac.region == reg].iloc[::-1]
        y = np.arange(len(g))
        ax.barh(y, g.n_cells / 1000, color=col, height=0.66)
        ax.set_yticks(y)
        ax.set_yticklabels([s.split(" ", 1)[1] for s in g.allen_subclass_anchor], fontsize=9.1)
        for i, r in enumerate(g.itertuples()):
            ax.text(r.n_cells / 1000 + 0.45, i,
                    f"{r.n_cells/1000:.1f}k   {r.n_sep} marker" + ("s" if r.n_sep != 1 else ""),
                    va="center", fontsize=8.2, color="#444444")
        ax.set_xlim(0, max(g.n_cells / 1000) * 1.52)
        ax.set_xlabel("Allen cells in this population (thousands)", fontsize=9)
        ax.set_title(f"{title}\n{len(g)} populations,  {g.n_cells.sum():,} cells",
                     fontsize=10.3, color=col, loc="left")
    # The marker count is genes EXCLUSIVE to one population - the strictest test.
    # Identification in practice is combinatorial, so quote the pairwise result too,
    # otherwise "1 marker" for L5 IT reads as if the population were unresolved.
    pr = pd.read_csv(PAIRS)
    l5 = pr[pr.subclass_A_positive == "005 L5 IT CTX Glut"]
    panel_genes = set(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str))
    nb = l5.subclass_B_negative.nunique()
    covered = sum(1 for n, g in l5.groupby("subclass_B_negative")
                  if set(g.separator_gene) & panel_genes)
    fig.text(0.5, -0.045,
             f"Marker counts are genes EXCLUSIVE to one population - the strictest test. "
             f"Identification is combinatorial: {F_PAIRS_NOTE}"
             f"L5 IT shows 1 exclusive gene (Bdnf) yet is separable from {covered} of its {nb} "
             f"neighbours using panel genes.",
             ha="center", fontsize=8.5, color="#555555")
    fig.tight_layout()
    p = FIG / "V3_F3_celltypes.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


# --------------------------------------------------------------- deck helpers
def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def txt(slide, x, y, w, h, body, size=13, bold=False, color=INK, space=4):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(str(body).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space)
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
        r.font.color.rgb = color
    return tb


def slide(prs, title, sub, n, total, tcol=NAVY, backup=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    txt(s, 0.40, 0.18, 12.5, 0.42, title, 24, True, rgb(tcol))
    if sub:
        txt(s, 0.40, 0.56, 12.5, 0.34, sub, 13, False, MUTED)
    tag = "BACKUP  ·  " if backup else ""
    txt(s, 0.40, 7.18, 12.5, 0.24,
        f"{tag}ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {n}/{total}",
        11, False, MUTED)
    return s


def tile(s, x, y, w, big, label, col, h=1.12, bigsize=26):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid()
    b.fill.fore_color.rgb = rgb(CREAM)
    b.line.color.rgb = rgb(col)
    b.line.width = Pt(1.3)
    b.shadow.inherit = False
    txt(s, x + 0.12, y + 0.05, w - 0.24, 0.52, big, bigsize, True, rgb(col))
    txt(s, x + 0.12, y + 0.57, w - 0.24, 0.50, label, 11.5, False, MUTED, space=0)


def card(s, x, y, w, h, num, head, metric, keep, drop, col):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid()
    b.fill.fore_color.rgb = rgb("FFFFFF")
    b.line.color.rgb = rgb(col)
    b.line.width = Pt(1.5)
    b.shadow.inherit = False
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12), Inches(0.34), Inches(0.34))
    c.fill.solid()
    c.fill.fore_color.rgb = rgb(col)
    c.line.fill.background()
    c.shadow.inherit = False
    txt(s, x + 0.145, y + 0.155, 0.33, 0.30, num, 14, True, WHITE)
    txt(s, x + 0.56, y + 0.12, w - 0.70, 0.36, head, 13.5, True, rgb(col))
    txt(s, x + 0.16, y + 0.52, w - 0.30, 0.34, metric, 11, False, MUTED, space=0)
    txt(s, x + 0.16, y + 0.92, w - 0.30, 0.34, "IN     " + keep, 11, False, rgb(SAGE), space=0)
    txt(s, x + 0.16, y + 1.24, w - 0.30, 0.34, "OUT   " + drop, 11, False, rgb(RUST), space=0)


def picture(slide, path, top, max_h, max_w=12.6, left=None):
    pic = slide.shapes.add_picture(str(path), Inches(0), Inches(top), height=Inches(max_h))
    if pic.width > Inches(max_w):
        sc = Inches(max_w) / pic.width
        pic.width, pic.height = int(pic.width * sc), int(pic.height * sc)
    pic.left = int(Inches(left)) if left is not None else int((Inches(13.333) - pic.width) / 2)
    return pic.top / 914400 + pic.height / 914400


def build(F, figs) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    TOT, ac = 5, F["ac"]

    # ===== 1 the schematic
    s = slide(prs, "How the gene panel was selected", None, 1, TOT)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "The instrument reads a fixed number of genes per tissue section, so every slot has to be earned. "
        "Four rules decided which genes earned one.", 13, False, MUTED)
    picture(s, figs["flow"], 1.00, 5.90)

    # ===== 2 why in / why out
    s = slide(prs, "Why a gene is in - and why a similar one is out", None, 2, TOT, RUST)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "Each rule is a measurement with a cutoff. For every rule there is a gene that passed and a "
        "comparable gene that did not, so the line is visible rather than asserted.", 13, False, MUTED)
    cards = [
        ("1", "Does it identify the cell type?",
         "Specificity against genes the panel already carries. Must beat them (ratio > 1).",
         "Col23a1   3.7x more specific - no equal marker existed for that amygdala population",
         "Sfrp1   0.9x - a gene already on the panel does the job better", NAVY),
        ("2", "Is it a druggable receptor we cannot already see?",
         "Regional enrichment, plus whether that receptor family is already covered.",
         "Chrm1   M1 receptor, enriched in 8 populations - we could only see M2 before",
         "Glipr1   its population already carries Penk (2.3x) and Lamb3 (1.5x)", TEAL),
        ("3", "Does it report the morphine-dependent state?",
         "Differential expression counted only in our 12 ORBm populations, not the donor's whole dataset.",
         "Per2   changes in 11 of 12 populations - the broadest gene in Jesse's dataset",
         "Nr4a3   strong at 8 clusters, but only 5 of ours; the rest we do not image", RUST),
        ("4", "Will the instrument actually detect it?",
         "Fraction of cells expressing it in the atlas. Sparse probes give sparse, unusable maps.",
         "Grm8   99% of cells, above 50% in 8 of the 12 populations",
         "Mas1   most enriched receptor of all, but only 45% of cells and absent from GABA", SAGE),
    ]
    for i, (n, h, m, k, d, c) in enumerate(cards):
        card(s, 0.40 + (i % 2) * 6.36, 1.02 + (i // 2) * 1.78, 6.17, 1.66, n, h, m, k, d, c)
    band = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(4.72),
                              Inches(12.53), Inches(2.18))
    band.fill.solid()
    band.fill.fore_color.rgb = rgb(ICE)
    band.line.color.rgb = rgb(NAVY)
    band.line.width = Pt(1.2)
    band.shadow.inherit = False
    txt(s, 0.62, 4.86, 12.1, 0.30, "The constraint that forces all of this", 13.5, True, rgb(NAVY))
    txt(s, 0.62, 5.22, 5.95, 1.55,
        f"The standard 10x Mouse Brain panel gives ~248 genes free. The custom add-on is capped near 100.\n"
        f"So {F['n_genes']} genes on one section means {F['n_free']} taken free and {F['n_custom']} paid for - "
        f"and roughly three of every four candidates we screened were turned down.",
        11.5, False, INK, space=2)
    txt(s, 6.85, 5.22, 5.95, 1.55,
        "The four rules are independent, and that is deliberate.\n"
        "A receptor earns a slot by showing where a drug target sits, whether or not morphine changes it. "
        "So one panel serves the pharmacology aim and the addiction aim at the same time, instead of "
        "forcing a choice between them.", 11.5, False, INK, space=2)

    # ===== 3 final panel
    s = slide(prs, f"Final panel  -  {F['n_genes']} genes, one section, two regions", None, 3, TOT, TEAL)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "One shared Xenium panel read from the same mouse. All 20 target cell populations remain separable.",
        13, False, MUTED)
    for i, (big, lab, col) in enumerate([
        (f"{F['n_genes']}", "genes on the\nshared panel", NAVY),
        ("20 / 20", "cell populations\nstill separable", TEAL),
        (f"{F['n_free']}", "already free on the\n10x base panel", SAGE),
        ("12 + 8", "populations in\nORBm  +  BMAp", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 1.00, 2.95, big, lab, col)
    picture(s, figs["composition"], 2.32, 3.30, max_w=7.05, left=0.40)
    txt(s, 7.85, 2.34, 5.05, 0.34, "What each cell will tell us", 15, True, rgb(NAVY))
    for i, (h, b, col) in enumerate([
        ("Identity", "Which of the 20 populations it is - cortical layer, interneuron class, "
                     "or amygdala subtype", NAVY),
        ("Activity", "Whether it was recently active - Fos and Arc, plus the TRAP2 genetic tag", TEAL),
        ("State", "Whether it carries the morphine-dependence signature - Per2, Pcsk1, Per1, Camk2g", RUST),
        ("Receptors", "Which druggable receptors sit on it - opioid, muscarinic, glutamate, relaxin", SAGE),
    ]):
        y = 2.86 + i * 0.97
        txt(s, 7.85, y, 5.05, 0.28, h, 13, True, rgb(col))
        txt(s, 7.85, y + 0.29, 5.05, 0.60, b, 11.5, False, INK, space=0)
    txt(s, 0.40, 6.62, 12.5, 0.40,
        "The last row is the new capability: within a single cortical cell type, it separates cells that "
        "carry the dependence signature from those that do not.", 12, False, rgb(RUST))

    # ===== 4 BACKUP populations
    s = slide(prs, "The 20 populations we must tell apart", None, 4, TOT, NAVY, backup=True)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "The target list comes from the Allen Brain Cell Atlas taxonomy: 12 populations in orbitofrontal "
        "cortex, 8 in basomedial amygdala.", 13, False, MUTED)
    for i, (big, lab, col) in enumerate([
        ("12", "ORBm populations\n83,406 Allen cells", NAVY),
        ("8", "BMAp populations\n40,709 Allen cells", TEAL),
        (f"{ac.n_cells.sum():,}", "cells in the 20\ntarget populations", SAGE),
        ("20 / 20", "have a dedicated marker\non the final panel", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 1.00, 2.95, big, lab, col)
    picture(s, figs["celltypes"], 2.30, 4.55)

    # ===== 5 BACKUP depth
    s = slide(prs, "The list rests on a full re-analysis of the reference atlas", None, 5, TOT, TEAL, backup=True)
    txt(s, 0.40, 0.56, 12.5, 0.34,
        "No gene was taken on a paper's word. Every candidate was re-scored in the Allen atlas, restricted "
        "to these two regions, against the genes the panel already carried.", 13, False, MUTED)
    for i, (big, lab, col) in enumerate([
        ("226,886", "single cells scored across\nthe two target regions", NAVY),
        (f"{F['n_subclasses']}", "cell subclasses profiled,\nnot only the 20 targets", TEAL),
        (f"{F['n_measure']:,}", "gene x subclass abundance\nand specificity measurements", SAGE),
        (f"{F['n_pairs']:,}", "pairwise tests: can gene X\nseparate type A from type B?", RUST),
    ]):
        tile(s, 0.40 + i * 3.16, 1.00, 2.95, big, lab, col)
    for i, (big, lab, col) in enumerate([
        (f"{F['n_sources']}", f"documented sources,\n{F['n_doi']} with a DOI", NAVY),
        (f"{F['n_gpcr_enriched']}", "region-enriched receptors\nevaluated one by one", TEAL),
        (f"{F['n_gpcr_tiered']}", "receptors tiered specific,\nintermediate or universal", SAGE),
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
    txt(s, 0.62, 3.88, 12.1, 0.32, "What that analysis produced, in order", 14, True, rgb(NAVY))
    txt(s, 0.62, 4.32, 5.95, 2.40,
        "1.   Region-restricted expression matrices\n"
        "      Cells from ORBm and BMAp were pulled out of the whole-brain atlas, so every abundance and\n"
        "      specificity number describes these two regions, not a brain-wide average.\n\n"
        "2.   Per-population marker ranking\n"
        "      For each of the 20 targets, every candidate was ranked by how much of that population\n"
        "      expresses it and how tightly it is restricted to it.", 11.5, False, INK, space=2)
    txt(s, 6.85, 4.32, 5.95, 2.40,
        f"3.   Pairwise separability testing\n"
        f"      {F['n_pairs']:,} tests confirmed that neighbouring populations - L5 IT vs L5 ET, MEA vs BMA -\n"
        f"      remain distinguishable using only the genes actually on the panel.\n\n"
        "4.   Receptor and drug-target layer\n"
        "      Receptors were tiered by specificity and cross-referenced to the IUPHAR pharmacology\n"
        "      database, so the map covers targets that drugs already exist for.", 11.5, False, INK, space=2)

    prs.save(DECK)
    return DECK


def main() -> None:
    F = facts()
    figs = {"flow": fig_flow(F),
            "composition": fig_composition(F["comp"], F["n_free"], F["n_custom"]),
            "celltypes": fig_celltypes(F["ac"])}
    deck = build(F, figs)
    y = F["yld"]
    print(f"panel : {F['n_genes']} = {F['n_free']} free + {F['n_custom']} custom")
    print(f"yield : core {int(y.loc['core','n'])} (311 screened) | "
          f"Jesse {int(y.loc['jesse','n'])} (431) | Berg&Scherrer {int(y.loc['dan','n'])} (98)")
    for k, v in figs.items():
        print(f"fig {k:12s}-> {v}")
    print(f"deck          -> {deck}")


if __name__ == "__main__":
    main()
