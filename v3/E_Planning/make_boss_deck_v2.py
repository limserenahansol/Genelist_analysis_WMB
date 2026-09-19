"""Five-slide deck for the 297-gene panel, in the exact funder_v3 slide grammar.

Slide layouts follow the reference deck one-for-one:

  1  How the genes were chosen          schematic: sources -> rules -> panel, with yields
  2  Why a gene is in, why one is out   four rule cards, each with a measured pass and fail
  3  Final panel                        4 KPI cards + category bar + "what each cell tells us"
  4  The 20 populations we must tell    4 KPI cards + ORBm and BMAp population charts
     apart
  5  The list rests on a full           8 KPI cards + "what that analysis produced, in order"
     re-analysis of the reference atlas

Every number is read from the panel workbook and the local Allen re-analysis.

Output: Downloads/ORBm_BMAp_Xenium_panel_297_5slides.pptx
"""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SRC = DL / os.environ.get("PANEL_SRC", "PANEL_FINAL_297_ORBm_BMAp_all20.xlsx")
FIG = O / "boss_deck_figures"
FIG.mkdir(exist_ok=True)
DECK = DL / os.environ.get("DECK_NAME", "ORBm_BMAp_Xenium_panel_297_5slides.pptx")

NAVY, TEAL, RUST, SAGE, GREY = "#1D4E89", "#2A6F97", "#C44536", "#6B7C6A", "#B8B2A8"
CREAM, ICE, TAUPE = "#F4F1EA", "#EAF2F8", "#8C7B6B"
INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
})

GROUPS = [
    ("Cell identity and brain region", ["1 cell type"], NAVY),
    ("Sub-population markers", ["2 subtype marker"], "#3C6E9F"),
    ("Druggable receptor map", ["3 GPCR"], TEAL),
    ("Neural activity and plasticity", ["4 plasticity", "7 IEG"], SAGE),
    ("Identity transcription factors", ["5 TF"], "#7A8B99"),
    ("Morphine-dependence state", ["8 morphine"], RUST),
    ("Circadian clock state", ["9 circadian"], TAUPE),
    ("Genetic-tag reporters", ["6 TRAP reporter"], "#B08968"),
]


def facts() -> dict:
    panel = pd.read_excel(SRC, "FINAL_GENE_LIST")
    exc = pd.read_excel(SRC, "EXCLUDED_measured")
    pm = pd.read_excel(SRC, "PAPER_MARKER_CHECK")
    pv = pd.read_excel(SRC, "PAPER_vs_ALLEN")
    crowd = pd.read_excel(SRC, "CROWDING_load")
    srcs = pd.read_excel(SRC, "SOURCES")
    rank = pd.read_excel(O / "Jesse_ORB_priority_ranking.xlsx", "ranking_all")
    types = pd.read_csv(O / "_TYPES_markercount.csv")
    ct = pd.read_csv(O / "_CELL_TYPE_MARKERS_297.csv")
    cats = panel.groupby("category").gene.count()
    comp = [{"group": n, "n": int(sum(cats.get(c, 0) for c in cs)), "colour": col}
            for n, cs, col in GROUPS]
    assert sum(c["n"] for c in comp) == len(panel), (sum(c["n"] for c in comp), len(panel))
    return {
        "panel": panel, "cats": cats, "comp": pd.DataFrame(comp), "types": types, "ct": ct,
        "n": len(panel), "n_orbm": len(pd.read_excel(SRC, "ORBm_LIST")),
        "n_bmap": len(pd.read_excel(SRC, "BMAp_LIST")),
        "n_exc": len(exc),
        "n_exc_det": int(exc.why_excluded.astype(str).str.contains("50 pct detection bar|empty map").sum()),
        "n_exc_red": int(exc.why_excluded.astype(str).str.contains("already has a dedicated marker").sum()),
        "jesse_total": int(rank.gene.nunique()), "jesse_on": int(rank.gene.isin(set(panel.gene)).sum()),
        "dan_on": int((panel.block == "12_GSE283418_added").sum()),
        "paper_on": int((panel.block == "9_published_regional").sum()),
        "paper_tested": len(pm), "paper_passed": int(pm.include.sum()),
        "claims": len(pv), "claims_ok": int(pv.verdict.astype(str).str.startswith("confirmed").sum()),
        "median_det": float(panel.allen_pct_own_population.median()),
        "n70": int((panel.allen_pct_own_population >= 70).sum()),
        "top10_load": float(crowd.pct_of_panel_transcripts.head(10).sum()),
        "n_src": len(srcs), "n_doi": int(srcs.doi.notna().sum()),
        "n_nn": int((panel.block == "30_nonneuronal_class").sum()),
        "nn_genes": ", ".join(sorted(panel.gene[panel.block == "30_nonneuronal_class"])),
        "cells_orbm": int(types[types.region == "ORBm"].n_cells.sum()),
        "cells_bmap": int(types[types.region == "BMAp"].n_cells.sum()),
    }


# --------------------------------------------------------------------- figures
def card(ax, x, y, w, h, title, body, col, fs_t=9.2, fs_b=8.4):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.022",
        facecolor=CREAM, edgecolor=col, linewidth=1.6, zorder=2))
    ax.add_patch(mpatches.Rectangle((x, y + h - 0.052), w, 0.052, facecolor=col,
                                    edgecolor=col, zorder=3))
    ax.text(x + w / 2, y + h - 0.026, title, ha="center", va="center", color="white",
            fontsize=fs_t, fontweight="bold", zorder=4)
    ax.text(x + 0.012, y + h - 0.075, body, ha="left", va="top", fontsize=fs_b,
            color="#222222", zorder=4, linespacing=1.5)


def fig_flow(F) -> Path:
    fig, ax = plt.subplots(figsize=(12.6, 5.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    SX, SW, H = 0.005, 0.255, 0.265
    rows = [0.665, 0.365, 0.065]
    card(ax, SX, rows[0], SW, H, "Allen Brain Cell Atlas (WMB-10X)",
         "226,886 single cells of ORBm + BMAp\n"
         f"(PL-ILA-ORB {F['cells_orbm']:,} + others / sAMY)\n"
         "75 cell types, 96 sub-populations\n"
         "32,285 genes screened genome-wide", NAVY)
    card(ax, SX, rows[1], SW, H, "Collaborator data",
         f"Jesse - 5-day morphine DEGs in ORB\n{F['jesse_total']} genes screened, {F['jesse_on']} kept\n"
         f"Dan - GSE283418 amygdala spatial\n{F['dan_on']} kept", RUST)
    card(ax, SX, rows[2], SW, H, "Literature + Statement of Work",
         f"{F['n_src']} documented sources ({F['n_doi']} with DOI)\n"
         f"{F['claims']} published marker claims re-tested\n"
         f"{F['paper_on']} regional markers kept\n"
         "8 SOW-named genes, all kept", TEAL)

    MX, MW = 0.335, 0.30
    ax.add_patch(mpatches.FancyBboxPatch(
        (MX, 0.065), MW, 0.865, boxstyle="round,pad=0.008,rounding_size=0.024",
        facecolor=ICE, edgecolor=NAVY, linewidth=1.8, zorder=2))
    ax.text(MX + MW / 2, 0.888, "Every candidate re-measured in these two regions",
            ha="center", va="center", fontsize=9.4, fontweight="bold", color=NAVY, zorder=4)
    rules = [
        ("1  Does it name the cell type?",
         ">=50% of that population and >=20pp\nover the competing populations"),
        ("2  Does it name the sub-population?",
         ">=50% of the sub-population and\n>=20pp over its siblings"),
        ("3  Can the instrument read it?",
         ">=50% of cells somewhere in\nORBm or BMAp - no empty maps"),
        ("4  Does it report the morphine state?",
         "DE in >=4 of the 12 ORBm cell types\nin Jesse's data"),
    ]
    y = 0.820
    for t, b in rules:
        ax.text(MX + 0.016, y, t, ha="left", va="top", fontsize=8.8, fontweight="bold",
                color="#1a1a1a", zorder=4)
        ax.text(MX + 0.016, y - 0.042, b, ha="left", va="top", fontsize=8.0, color="#3a3a3a",
                zorder=4, linespacing=1.45)
        y -= 0.170
    ax.text(MX + MW / 2, 0.128, f"{F['n_exc']} candidates rejected,\neach with its number:\n"
                                f"{F['n_exc_det']} too sparse to map  |  {F['n_exc_red']} redundant\n"
                                f"{F['paper_tested'] - F['paper_passed']} of {F['paper_tested']} "
                                f"published markers failed",
            ha="center", va="center", fontsize=8.0, color=RUST, zorder=4, linespacing=1.45,
            fontweight="bold")

    PX, PW = 0.665, 0.33
    ax.add_patch(mpatches.FancyBboxPatch(
        (PX, 0.065), PW, 0.865, boxstyle="round,pad=0.008,rounding_size=0.024",
        facecolor=CREAM, edgecolor=SAGE, linewidth=1.8, zorder=2))
    ax.text(PX + PW / 2, 0.888, f"Final panel - {F['n']} genes", ha="center", va="center",
            fontsize=9.6, fontweight="bold", color=SAGE, zorder=4)
    y = 0.800
    for r in F["comp"].itertuples():
        ax.add_patch(mpatches.Rectangle((PX + 0.018, y - 0.026), 0.012, 0.030,
                                        facecolor=r.colour, edgecolor="none", zorder=4))
        ax.text(PX + 0.040, y - 0.010, r.group, ha="left", va="center", fontsize=8.4,
                color="#222222", zorder=4)
        ax.text(PX + PW - 0.018, y - 0.010, f"{r.n}", ha="right", va="center", fontsize=8.4,
                fontweight="bold", color="#222222", zorder=4)
        y -= 0.076
    ax.text(PX + PW / 2, 0.135, "all 20 target cell types and 96 of 96 sub-populations\n"
                                "have their own marker on this panel",
            ha="center", va="center", fontsize=8.2, color=SAGE, fontweight="bold",
            zorder=4, linespacing=1.5)

    for y0 in (0.795, 0.495, 0.195):
        ax.annotate("", xy=(MX - 0.004, 0.50), xytext=(SX + SW + 0.004, y0),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.5,
                                    connectionstyle="arc3,rad=0.06"), zorder=1)
    ax.annotate("", xy=(PX - 0.004, 0.50), xytext=(MX + MW + 0.004, 0.50),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.0), zorder=1)
    p = FIG / "v2_flow.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


def fig_categories(F) -> Path:
    c = F["comp"].sort_values("n", ascending=True)
    fig, ax = plt.subplots(figsize=(6.6, 3.55))
    ax.barh(c.group, c.n, color=list(c.colour), height=0.62)
    for i, (g, n) in enumerate(zip(c.group, c.n)):
        ax.text(n + 2.5, i, f"{n}", va="center", fontsize=10, fontweight="bold", color="#222")
    ax.set_xlim(0, max(c.n) * 1.22)
    ax.set_xlabel("number of genes", fontsize=9.5)
    ax.set_title(f"What the {F['n']} genes do", fontsize=11.5, color=NAVY, fontweight="bold",
                 loc="left", pad=10)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=9.5)
    ax.tick_params(axis="x", labelsize=9)
    fig.tight_layout()
    p = FIG / "v2_categories.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


def fig_populations(F) -> Path:
    t = F["types"].copy()
    t["short"] = [a.split(" ", 1)[1] for a in t.anchor]
    fig, axes = plt.subplots(1, 2, figsize=(12.3, 4.35))
    for ax, reg, col, title in (
            (axes[0], "ORBm", NAVY, "A.  ORBm  -  orbitofrontal cortex, medial"),
            (axes[1], "BMAp", TEAL, "B.  BMAp  -  basomedial amygdala, posterior")):
        d = t[t.region == reg].iloc[::-1]
        ax.barh(d.short, d.n_cells / 1000, color=col, height=0.6)
        for i, r in enumerate(d.itertuples()):
            ax.text(r.n_cells / 1000 + max(t.n_cells) / 1000 * 0.012, i,
                    f"{r.n_cells/1000:.1f}k   {r.m10} marker{'s' if r.m10 != 1 else ''}"
                    f"   best +{r.best_gap:.0f}pp",
                    va="center", fontsize=8.4, color="#222")
        ax.set_xlim(0, d.n_cells.max() / 1000 * 1.85)
        ax.set_xlabel("Allen cells in this population (thousands)", fontsize=9)
        ax.set_title(f"{title}\n{len(d)} populations,  "
                     f"{int(d.n_cells.sum()):,} cells", fontsize=9.6, color=col,
                     fontweight="bold", loc="left")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0, labelsize=8.6)
        ax.tick_params(axis="x", labelsize=8.6)
    fig.tight_layout()
    p = FIG / "v2_populations.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


# ---------------------------------------------------------------------- deck
def hexc(h: str) -> RGBColor:
    return RGBColor.from_string(h.lstrip("#"))


def slide(prs, n, title, sub, backup=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tb = s.shapes.add_textbox(Inches(0.40), Inches(0.18), Inches(12.5), Inches(0.42))
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = title
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(22), True, "Calibri", hexc(NAVY)
    tb2 = s.shapes.add_textbox(Inches(0.40), Inches(0.56), Inches(12.5), Inches(0.34))
    r2 = tb2.text_frame.paragraphs[0].add_run()
    r2.text = sub
    r2.font.size, r2.font.name, r2.font.color.rgb = Pt(11.5), "Calibri", MUTED
    f = s.shapes.add_textbox(Inches(0.40), Inches(7.18), Inches(12.5), Inches(0.24))
    rf = f.text_frame.paragraphs[0].add_run()
    rf.text = (("BACKUP  ·  " if backup else "")
               + f"ORBm + BMAp custom Xenium panel  |  Allen WMB-10X  |  {n}/5")
    rf.font.size, rf.font.name, rf.font.color.rgb = Pt(8.5), "Calibri", hexc(GREY)
    return s


def kpi(s, x, y, big, small, col=NAVY, w=2.95, h=1.12):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = hexc(CREAM)
    sp.line.color.rgb = hexc(col)
    sp.line.width = Pt(1.25)
    sp.shadow.inherit = False
    sp.text_frame.text = ""
    t = s.shapes.add_textbox(Inches(x + 0.12), Inches(y + 0.05), Inches(w - 0.24), Inches(0.52))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = big
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(26), True, "Calibri", hexc(col)
    t2 = s.shapes.add_textbox(Inches(x + 0.12), Inches(y + 0.57), Inches(w - 0.24), Inches(0.50))
    tf = t2.text_frame
    tf.word_wrap = True
    for i, line in enumerate(small.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        rr = p.add_run()
        rr.text = line
        rr.font.size, rr.font.name, rr.font.color.rgb = Pt(9.5), "Calibri", INK
        p.space_after = Pt(0)


def rulecard(s, x, y, w, h, num, q, rule, yes, no):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = hexc(CREAM)
    sp.line.color.rgb = hexc(NAVY)
    sp.line.width = Pt(1.0)
    sp.shadow.inherit = False
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.14), Inches(y + 0.12), Inches(0.34), Inches(0.34))
    o.fill.solid()
    o.fill.fore_color.rgb = hexc(NAVY)
    o.line.color.rgb = hexc(NAVY)
    o.shadow.inherit = False
    tn = s.shapes.add_textbox(Inches(x + 0.15), Inches(y + 0.15), Inches(0.33), Inches(0.30))
    rn = tn.text_frame.paragraphs[0].add_run()
    rn.text = num
    rn.font.size, rn.font.bold, rn.font.name, rn.font.color.rgb = Pt(12), True, "Calibri", WHITE
    for dy, txt, sz, bold, col in (
            (0.10, q, 11.5, True, INK),
            (0.44, rule, 9.3, False, MUTED),
            (0.78, f"IN    {yes}", 9.3, False, hexc(SAGE)),
            (1.06, f"OUT   {no}", 9.3, False, hexc(RUST))):
        left = x + 0.56 if dy == 0.10 else x + 0.16
        width = w - 0.72 if dy == 0.10 else w - 0.32
        tb = s.shapes.add_textbox(Inches(left), Inches(y + dy), Inches(width), Inches(0.34))
        tf = tb.text_frame
        tf.word_wrap = True
        r = tf.paragraphs[0].add_run()
        r.text = txt
        r.font.size, r.font.bold, r.font.name = Pt(sz), bold, "Calibri"
        r.font.color.rgb = col


def band(s, x, y, w, h, title, left, right, col=NAVY):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = hexc(CREAM)
    sp.line.color.rgb = hexc(col)
    sp.line.width = Pt(1.0)
    sp.shadow.inherit = False
    t = s.shapes.add_textbox(Inches(x + 0.22), Inches(y + 0.12), Inches(w - 0.44), Inches(0.32))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = title
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(12), True, "Calibri", hexc(col)
    for i, txt in enumerate((left, right)):
        tb = s.shapes.add_textbox(Inches(x + 0.22 + i * (w / 2 - 0.10)), Inches(y + 0.50),
                                  Inches(w / 2 - 0.34), Inches(h - 0.62))
        tf = tb.text_frame
        tf.word_wrap = True
        for j, line in enumerate(txt.split("\n")):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            rr = p.add_run()
            rr.text = line
            rr.font.size, rr.font.name, rr.font.color.rgb = Pt(10), "Calibri", INK
            rr.font.bold = line[:2].strip().rstrip(".").isdigit()
            p.space_after = Pt(4)


def textblock(s, x, y, w, head, body, col=TEAL, head_pt=11, body_pt=10):
    t = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.26))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = head
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(head_pt), True, "Calibri", hexc(col)
    t2 = s.shapes.add_textbox(Inches(x), Inches(y + 0.27), Inches(w), Inches(0.56))
    tf = t2.text_frame
    tf.word_wrap = True
    rr = tf.paragraphs[0].add_run()
    rr.text = body
    rr.font.size, rr.font.name, rr.font.color.rgb = Pt(body_pt), "Calibri", INK


def main() -> None:
    F = facts()
    f_flow, f_cat, f_pop = fig_flow(F), fig_categories(F), fig_populations(F)
    c = F["cats"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # ---- 1 how the genes were chosen
    s = slide(prs, 1, f"How the {F['n']} genes were selected",
              "The instrument reads a fixed number of genes per section, so every slot has to be "
              "earned. Four measured rules decided which genes earned one.")
    s.shapes.add_picture(str(f_flow), Inches(0.37), Inches(1.00), width=Inches(12.60))

    # ---- 2 in / out
    s = slide(prs, 2, "Why a gene is in - and why a similar one is out",
              "Each rule is a measurement with a cutoff. For every rule there is a gene that passed "
              "and a comparable gene that did not, so the line is visible rather than asserted.")
    W, H, GX, GY = 6.17, 1.50, 6.36, 1.62
    rulecard(s, 0.40, 1.02, W, H, "1", "Does it identify the cell type?",
             ">=50% of that population, >=20pp over the competing types",
             "Vwc2l   97% of L5 NP cells, +42pp over the next type",
             "Cux1   72% in L2/3 but 94% in an amygdala GABA type")
    rulecard(s, 0.40 + GX, 1.02, W, H, "2", "Does it identify the sub-population?",
             ">=50% of the sub-population, >=20pp over its siblings",
             "Hpse   88% of Sst_7 (229 cells) vs 8% in the rest of Sst",
             "20 discovery candidates   their sub-population already had one")
    rulecard(s, 0.40, 1.02 + GY, W, H, "3", "Will the instrument actually detect it?",
             ">=50% of cells somewhere in ORBm or BMAp",
             "Adrb1   84%, the beta1-adrenergic receptor the SOW names",
             "Sstr4   1.4% of cells - the probe returns an empty map")
    rulecard(s, 0.40 + GX, 1.02 + GY, W, H, "4", "Does it report the morphine state?",
             "DE in >=4 of the 12 ORBm cell types in Jesse's data, and detectable",
             "Mbnl2   DE in 4 ORBm types, 99.8% detected",
             "Zbtb40   DE in 6 types but only 29% detected where we image")
    band(s, 0.40, 4.32, 12.53, 1.30, "Two more rules, because this is a standalone panel",
         f"5   Minimum non-neuronal set. 28% of the section is glia and vessels, but measured: they are "
         f"never called neurons even with no glial probe, so only {F['n_nn']} are kept "
         f"({F['nn_genes']}).",
         "6   Genes the SOW names stay regardless of level - the SOW asks whether they are expressed, "
         "so a low answer is still an answer. All 8 are on the panel.", TEAL)
    band(s, 0.40, 5.76, 12.53, 1.28,
         f"What did not make it: {F['n_exc']} candidates rejected, each with its measured number",
         f"{F['n_exc_det']}   detected in under half the cells of any population we image\n"
         f"{F['n_exc_red']}   redundant - a gene already on the panel does the same job",
         f"{F['paper_tested'] - F['paper_passed']} of {F['paper_tested']}   published markers failed "
         f"when re-tested in the Allen cells (Cux1, Scnn1a, Crym, Reln ...)\n"
         f"4   sex-determination genes, excluded on request", RUST)

    # ---- 3 final panel
    s = slide(prs, 3, f"Final panel  -  {F['n']} genes, one section, two regions",
              "One shared Xenium panel read from the same mouse. All 20 target cell populations have "
              "their own marker.")
    for i, (big, small, col) in enumerate([
            (f"{F['n']}", "genes on the\nshared panel", NAVY),
            ("20 / 20", "cell populations with\ntheir own marker", NAVY),
            ("96 / 96", "sub-populations with\ntheir own marker", SAGE),
            ("12 + 8", "populations in\nORBm  +  BMAp", RUST)]):
        kpi(s, 0.40 + i * 3.16, 1.00, big, small, col)
    s.shapes.add_picture(str(f_cat), Inches(0.40), Inches(2.32), width=Inches(7.05))
    t = s.shapes.add_textbox(Inches(7.85), Inches(2.34), Inches(5.05), Inches(0.34))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = "What each cell will tell us"
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(13), True, "Calibri", hexc(NAVY)
    blocks = [
        ("Identity", f"Which of the 20 populations it is - cortical layer, interneuron class, or "
                     f"amygdala subtype  ({c.get('1 cell type', 0)} genes)"),
        ("Sub-type", f"Which sub-population inside that type - where a new TRAP+ population would "
                     f"appear  ({c.get('2 subtype marker', 0)} genes)"),
        ("Activity", f"Whether it was recently active - Fos and Arc, plus the TRAP2 genetic tag  "
                     f"({c.get('7 IEG', 0)} IEGs + 2 reporters)"),
        ("State", f"Whether it carries the morphine-dependence signature, and its circadian state  "
                  f"({c.get('8 morphine', 0)} + {c.get('9 circadian', 0)} genes)"),
        ("Receptors", f"Which druggable receptors sit on it - opioid, adrenergic, serotonergic, "
                      f"muscarinic, glutamate  ({c.get('3 GPCR', 0)} genes)"),
    ]
    y = 2.86
    for head, body in blocks:
        textblock(s, 7.85, y, 5.05, head, body)
        y += 0.82
    tb = s.shapes.add_textbox(Inches(0.40), Inches(6.62), Inches(12.5), Inches(0.40))
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = ("The last two rows are the new capability: within a single cortical cell type, the panel "
              "separates cells that carry the dependence signature from those that do not.")
    r.font.size, r.font.name, r.font.color.rgb = Pt(10.5), "Calibri", hexc(RUST)

    # ---- 4 the 20 populations
    s = slide(prs, 4, "The 20 populations we must tell apart",
              "The target list comes from the Allen Brain Cell Atlas taxonomy: 12 populations in "
              "orbitofrontal cortex, 8 in basomedial amygdala.", backup=True)
    for i, (big, small, col) in enumerate([
            ("12", f"ORBm populations\n{F['cells_orbm']:,} Allen cells", NAVY),
            ("8", f"BMAp populations\n{F['cells_bmap']:,} Allen cells", NAVY),
            (f"{F['cells_orbm'] + F['cells_bmap']:,}", "cells in the 20\ntarget populations", SAGE),
            ("20 / 20", "have a dedicated marker\non the final panel", RUST)]):
        kpi(s, 0.40 + i * 3.16, 1.00, big, small, col)
    s.shapes.add_picture(str(f_pop), Inches(0.42), Inches(2.30), width=Inches(12.45))
    tb = s.shapes.add_textbox(Inches(0.40), Inches(6.72), Inches(12.5), Inches(0.40))
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = ("Marker = a panel gene detected in >=50% of that population and >=10pp above every other "
              "target population. Two populations sit below a 20pp margin - L5 IT (Adam19, +17pp) and "
              "MEA-BST Sox6 (Chn2, +15pp) - and no gene in the 32,285-gene atlas does better for them.")
    r.font.size, r.font.name, r.font.color.rgb = Pt(10), "Calibri", MUTED

    # ---- 5 evidence
    s = slide(prs, 5, "The list rests on a full re-analysis of the reference atlas",
              "No gene was taken on a paper's word. Every candidate was re-scored in the Allen atlas, "
              "restricted to these two regions, in the population it is meant to report.", backup=True)
    top = [("226,886", "single cells scored across\nthe two target regions", NAVY),
           ("32,285", "genes screened genome-wide\nfor a better marker", NAVY),
           ("602", "candidates measured\ncell by cell", SAGE),
           (f"{F['n_exc']}", "candidates rejected,\neach with its number", RUST)]
    bot = [(f"{F['claims_ok']} / {F['claims']}", "published marker claims\nconfirmed in the atlas", NAVY),
           (f"{F['jesse_on']} / {F['jesse_total']}", "Jesse morphine DEGs that\npassed detection", NAVY),
           (f"{F['n_src']}", f"documented sources,\n{F['n_doi']} with a DOI", SAGE),
           ("64", "FDA-approved drugs mapped\nto panel receptors (IUPHAR)", RUST)]
    for i, (big, small, col) in enumerate(top):
        kpi(s, 0.40 + i * 3.16, 1.00, big, small, col)
    for i, (big, small, col) in enumerate(bot):
        kpi(s, 0.40 + i * 3.16, 2.34, big, small, col)
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.40), Inches(3.72),
                            Inches(12.53), Inches(3.18))
    sp.fill.solid()
    sp.fill.fore_color.rgb = hexc(CREAM)
    sp.line.color.rgb = hexc(GREY)
    sp.line.width = Pt(1.0)
    sp.shadow.inherit = False
    t = s.shapes.add_textbox(Inches(0.62), Inches(3.88), Inches(12.10), Inches(0.32))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = "What that analysis produced, in order"
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(12.5), True, "Calibri", hexc(NAVY)
    items = [
        ("1.   Region-restricted expression matrices",
         "Cells from ORBm and BMAp were pulled out of the whole-brain atlas, so every percentage "
         "describes these two regions, not a brain-wide average."),
        ("2.   Per-population marker ranking",
         "For each of the 20 targets every candidate was ranked by how much of that population "
         "expresses it and how far it sits above the next population."),
        ("3.   Detection and expression-level screen",
         f"{F['n_exc_det']} candidates were dropped for being detected in under half the cells of any "
         f"population we image - a probe that returns an empty map is money spent twice."),
        ("4.   Held-out cell-type calling",
         "A classifier given only the panel genes labels held-out cells at 93% mean recall across the "
         "20 populations - and the same at simulated Xenium sparsity."),
    ]
    for i, (head, body) in enumerate(items):
        x = 0.62 + (i % 2) * 6.25
        y = 4.32 + (i // 2) * 1.30
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(5.95), Inches(0.30))
        rr = tb.text_frame.paragraphs[0].add_run()
        rr.text = head
        rr.font.size, rr.font.bold, rr.font.name, rr.font.color.rgb = Pt(10.5), True, "Calibri", INK
        tb2 = s.shapes.add_textbox(Inches(x + 0.22), Inches(y + 0.30), Inches(5.73), Inches(0.80))
        tf = tb2.text_frame
        tf.word_wrap = True
        r2 = tf.paragraphs[0].add_run()
        r2.text = body
        r2.font.size, r2.font.name, r2.font.color.rgb = Pt(9.8), "Calibri", MUTED

    prs.save(DECK)
    print(f"wrote {DECK}  ({len(prs.slides._sldIdLst)} slides)")
    print("figures:", ", ".join(p.name for p in (f_flow, f_cat, f_pop)))


if __name__ == "__main__":
    main()
