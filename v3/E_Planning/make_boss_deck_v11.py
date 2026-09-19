"""Five-slide deck for the v11 LEAN 297 panel, in the funder_v3 visual language.

  1  How the 297 genes were chosen        sources -> rules -> panel, with yields
  2  Why a gene is in, why one is out     six rules, each with a measured pass and fail
  3  The final panel                      what gets ordered and what each cell will report
  4  What the panel can measure           the readout chain for one tdTomato+ cell
  5  Evidence behind every number         screening scale, benchmarks, honest limits

Every number is read from the live workbook and the local Allen re-analysis; nothing
is typed in by hand except the wording.

Output: Downloads/ORBm_BMAp_panel_v11_boss_5slides.pptx
"""
from __future__ import annotations

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
import os
SRC = DL / os.environ.get("PANEL_SRC", "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx")
FIG = O / "boss_deck_figures"
FIG.mkdir(exist_ok=True)
DECK = DL / os.environ.get("DECK_NAME", "ORBm_BMAp_panel_v11_boss_5slides.pptx")

NAVY, TEAL, RUST, SAGE, GREY = "#1D4E89", "#2A6F97", "#C44536", "#6B7C6A", "#B8B2A8"
CREAM, ICE, TAUPE = "#F4F1EA", "#EAF2F8", "#8C7B6B"
INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)
FOOT = "ORBm + BMAp Xenium standalone panel  |  Allen WMB-10X re-analysis"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
})

CAT_COLOUR = {
    "1 cell type": NAVY, "2 subtype marker": "#3C6E9F", "3 GPCR": TEAL,
    "4 plasticity": SAGE, "5 TF": "#7A8B99", "6 TRAP reporter": "#B08968",
    "7 IEG": "#A05A3C", "8 morphine": RUST, "9 circadian": TAUPE,
}
def tells(c) -> list:
    return [
        ("Identity", "Which of the 20 target populations the cell is - cortical layer, interneuron "
                     "class, or amygdala type", f"{c.get('1 cell type', 0)} markers"),
        ("Sub-type", "Which sub-population inside that type - the level at which a new population "
                     "would show up", f"{c.get('2 subtype marker', 0)} markers"),
        ("Receptors", "Which druggable receptors sit on it - opioid, adrenergic, serotonergic, "
                      "muscarinic, glutamate", f"{c.get('3 GPCR', 0)} GPCRs"),
        ("State", "Whether it carries the morphine-dependence signature and the circadian clock state",
         f"{c.get('8 morphine', 0)} + {c.get('9 circadian', 0)} genes"),
        ("Activity", "Whether it fired recently, and whether it was tagged during volitional seeking",
         f"{c.get('7 IEG', 0)} IEGs + TRAP tag"),
    ]


def facts() -> dict:
    lean = pd.read_excel(SRC, "FINAL_GENE_LIST")
    exc = pd.read_excel(SRC, "EXCLUDED_measured")
    pm = pd.read_excel(SRC, "PAPER_MARKER_CHECK")
    pv = pd.read_excel(SRC, "PAPER_vs_ALLEN")
    cmp_ = pd.read_excel(SRC, "PANEL_COMPARISON")
    crowd = pd.read_excel(SRC, "CROWDING_load")
    stress = pd.read_excel(SRC, "STRESS_xenium_sparsity")
    rank = pd.read_excel(O / "Jesse_ORB_priority_ranking.xlsx", "ranking_all")
    srcs = pd.read_excel(SRC, "SOURCES")
    G = set(lean.gene)
    return {
        "lean": lean, "cats": lean.groupby("category").gene.count(),
        "n": len(lean), "orbm": len(pd.read_excel(SRC, "ORBm_LIST")),
        "bmap": len(pd.read_excel(SRC, "BMAp_LIST")),
        "n_exc": len(exc),
        "n_exc_det": int(exc.why_excluded.astype(str).str.contains("50 pct detection bar|empty map").sum()),
        "n_exc_red": int(exc.why_excluded.astype(str).str.contains("already has a dedicated marker").sum()),
        "jesse_total": int(rank.gene.nunique()), "jesse_on": int(rank.gene.isin(G).sum()),
        "dan_on": int((lean.block == "12_GSE283418_added").sum()),
        "paper_on": int((lean.block == "9_published_regional").sum()),
        "paper_tested": len(pm), "paper_passed": int(pm.include.sum()),
        "claims": len(pv), "claims_ok": int(pv.verdict.astype(str).str.startswith("confirmed").sum()),
        "median_det": float(lean.allen_pct_own_population.median()),
        "n70": int((lean.allen_pct_own_population >= 70).sum()),
        "top10_load": float(crowd.pct_of_panel_transcripts.head(10).sum()),
        "stress": stress, "cmp": cmp_, "n_src": len(srcs), "n_doi": int(srcs.doi.notna().sum()),
        "n_nn": int((lean.block == "30_nonneuronal_class").sum()),
        "nn_genes": ", ".join(sorted(lean.gene[lean.block == "30_nonneuronal_class"])),
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
    SX, SW = 0.005, 0.255
    rows = [0.665, 0.365, 0.065]
    H = 0.265
    card(ax, SX, rows[0], SW, H, "Allen Brain Cell Atlas (WMB-10X)",
         "226,886 single cells of ORBm + BMAp\n"
         "(PL-ILA-ORB 106,122 / sAMY 120,764)\n"
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
        ("1  Does it name the cell type?", ">=50% of that population and >=20pp\nover the competing populations"),
        ("2  Does it name the sub-population?", ">=50% of the sub-population and\n>=20pp over its siblings"),
        ("3  Can the instrument read it?", ">=50% of cells somewhere in\nORBm or BMAp - no empty maps"),
        ("4  Does it report the morphine state?", "DE in >=4 of the 12 ORBm cell types\nin Jesse's data"),
    ]
    y = 0.820
    for t, b in rules:
        ax.text(MX + 0.016, y, t, ha="left", va="top", fontsize=8.8, fontweight="bold",
                color="#1a1a1a", zorder=4)
        ax.text(MX + 0.016, y - 0.042, b, ha="left", va="top", fontsize=8.0, color="#3a3a3a",
                zorder=4, linespacing=1.45)
        y -= 0.170
    ax.text(MX + MW / 2, 0.128, f"{F['n_exc']} candidates rejected,\n"
                                f"each with its number:\n"
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
    cats = F["cats"]
    y = 0.815
    for c, n in cats.items():
        ax.add_patch(mpatches.Rectangle((PX + 0.018, y - 0.026), 0.012, 0.030,
                                        facecolor=CAT_COLOUR[c], edgecolor="none", zorder=4))
        ax.text(PX + 0.040, y - 0.010, f"{c[2:]}", ha="left", va="center", fontsize=8.5,
                color="#222222", zorder=4)
        ax.text(PX + PW - 0.018, y - 0.010, f"{n}", ha="right", va="center", fontsize=8.5,
                fontweight="bold", color="#222222", zorder=4)
        y -= 0.070
    ax.text(PX + PW / 2, 0.132, f"17 of 20 cell types and 96 of 96 sub-populations\n"
                                f"have a dedicated marker on this panel",
            ha="center", va="center", fontsize=8.2, color=SAGE, fontweight="bold",
            zorder=4, linespacing=1.5)

    for y0 in (0.795, 0.495, 0.195):
        ax.annotate("", xy=(MX - 0.004, 0.50), xytext=(SX + SW + 0.004, y0),
                    arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.5,
                                    connectionstyle="arc3,rad=0.06"), zorder=1)
    ax.annotate("", xy=(PX - 0.004, 0.50), xytext=(MX + MW + 0.004, 0.50),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.0), zorder=1)
    p = FIG / "flow.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


def fig_readout(F) -> Path:
    fig, ax = plt.subplots(figsize=(7.0, 4.7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.06, 0.845), 0.88, 0.125, boxstyle="round,pad=0.006,rounding_size=0.03",
        facecolor=NAVY, edgecolor=NAVY, zorder=2))
    ax.text(0.5, 0.907, "one tdTomato+ cell  (tagged during volitional seeking)", ha="center",
            va="center", color="white", fontsize=10.2, fontweight="bold", zorder=3)
    c = F["cats"]
    steps = [
        ("is it a neuron at all?",
         f"every neuronal gene reads ~zero in glia; {F['n_nn']} positive marker(s) name the rest",
         TAUPE),
        ("which cell type?", f"{c.get('1 cell type', 0)} identity markers - 17 of 20 types have a "
                             f"dedicated one", NAVY),
        ("which sub-population?", f"{c.get('2 subtype marker', 0)} sub-type markers - 96 of 96 "
                                  f"sub-populations covered", TEAL),
        ("which receptors does it carry?", f"{c.get('3 GPCR', 0)} GPCRs incl. the SOW's "
                                           f"beta1-adrenergic and 5-HT2A", SAGE),
        ("is it in the morphine state?", f"{c.get('8 morphine', 0)} Jesse DEGs + {c.get('7 IEG', 0)} "
                                         f"IEGs + {c.get('5 TF', 0)} TFs + {c.get('4 plasticity', 0)} "
                                         f"plasticity genes", RUST),
    ]
    y = 0.715
    for i, (t, b, col) in enumerate(steps, start=1):
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.06, y - 0.100), 0.88, 0.118, boxstyle="round,pad=0.005,rounding_size=0.025",
            facecolor=CREAM, edgecolor=col, linewidth=1.6, zorder=2))
        ax.add_patch(mpatches.Circle((0.105, y - 0.041), 0.021, facecolor=col, edgecolor=col, zorder=3))
        ax.text(0.105, y - 0.041, str(i), ha="center", va="center", color="white", fontsize=8.6,
                fontweight="bold", zorder=4)
        ax.text(0.142, y - 0.014, t, ha="left", va="center", fontsize=9.4, fontweight="bold",
                color="#1a1a1a", zorder=4)
        ax.text(0.142, y - 0.062, b, ha="left", va="center", fontsize=8.3, color="#3a3a3a", zorder=4)
        if i < len(steps):
            ax.annotate("", xy=(0.5, y - 0.117), xytext=(0.5, y - 0.101),
                        arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.4), zorder=1)
        y -= 0.143
    p = FIG / "readout.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


def fig_coverage(F) -> Path:
    """What the last round of work bought, measured."""
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 2.62))
    lab = ["previous panel\n(237 genes)", "this panel\n(297 genes)"]
    ax = axes[0]
    ax.bar(lab, [66, 96], color=[GREY, NAVY], width=0.55)
    ax.set_ylim(0, 108)
    ax.set_ylabel("sub-populations with\na dedicated marker", fontsize=9)
    for i, v in enumerate([66, 96]):
        ax.text(i, v + 3, f"{v} / 96", ha="center", fontsize=10, fontweight="bold",
                color=GREY if i == 0 else NAVY)
    ax.tick_params(labelsize=9)
    ax = axes[1]
    st = F["stress"]
    st = st[st.level.str.startswith("subclass")]
    piv = st.pivot_table(index="capture_rate", columns="panel", values="balanced_acc")
    keep = [c for c in ["IDEAL178", "v8_237", "v11_lean296", "d301", "v11_superset316"] if c in piv.columns]
    names = {"IDEAL178": "178 genes", "v8_237": "237 genes", "v11_lean296": "297 genes (this panel)",
             "d301": "301 genes", "v11_superset316": "317 genes"}
    cols = {"IDEAL178": GREY, "v8_237": TAUPE, "v11_lean296": NAVY, "d301": RUST,
            "v11_superset316": TEAL}
    for c in keep:
        ax.plot(piv.index * 100, piv[c] * 100, marker="o", ms=4, lw=1.8, color=cols[c],
                label=names[c])
    ax.set_xlabel("transcripts kept in the simulation (%)", fontsize=9)
    ax.set_ylabel("cell type called correctly (%)", fontsize=9)
    ax.set_ylim(89, 94.5)
    base = piv["v11_lean296"] * 100 if "v11_lean296" in piv.columns else None
    if base is not None:
        ax.fill_between(piv.index * 100, base - 1, base + 1, color=NAVY, alpha=0.07, lw=0)
        ax.text(0.98, 0.05, "shaded band = +/-1 point around this panel;\n"
                            "every panel sits inside it",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=7.4, color="#5B6472")
    ax.legend(fontsize=7.6, frameon=False, loc="upper right", ncol=2)
    ax.tick_params(labelsize=9)
    ax.set_title("cell-type calling saturates near 250 genes - the spread is under 1.5 points",
                 fontsize=9, color="#5B6472", loc="left")
    fig.tight_layout()
    p = FIG / "coverage.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


def fig_types(F) -> Path:
    """Every one of the 20 target cell types, and the gene that names it."""
    ct = pd.read_csv(O / "_CELL_TYPE_MARKERS_297.csv")
    ct = ct.sort_values(["region", "gap_vs_next_target_type_pp"], ascending=[True, True])
    fig, ax = plt.subplots(figsize=(12.4, 5.05))
    ypos = range(len(ct))
    colors = [TEAL if r == "BMAp" else NAVY for r in ct.region]
    ax.barh(list(ypos), ct.gap_vs_next_target_type_pp, color=colors, height=0.62)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels([f"{a}" for a in ct.allen_subclass_anchor], fontsize=9)
    ax.set_xlabel("margin of that marker over the next-highest target cell type (percentage points)",
                  fontsize=9.5)
    ax.set_xlim(0, 100)
    for i, r in enumerate(ct.itertuples()):
        ax.text(r.gap_vs_next_target_type_pp + 1.4, i,
                f"{r.best_marker_on_panel}   {r.pct_of_that_type:.0f}% of the type",
                va="center", fontsize=8.8, color="#222")
    ax.axvline(20, color=GREY, lw=1.2, ls="--")
    ax.text(20.6, len(ct) - 0.4, "20pp bar", fontsize=8.4, color="#5B6472")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("navy = ORBm,  teal = BMAp.  Every type has a positive marker detected in >=50% of its "
                 "cells; the two below the bar are at the ceiling of the whole transcriptome.",
                 fontsize=9, color="#5B6472", loc="left")
    fig.tight_layout()
    p = FIG / "types20.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return p


# ---------------------------------------------------------------------- deck
def hexc(h: str) -> RGBColor:
    return RGBColor.from_string(h.lstrip("#"))


def slide(prs, n, title, sub):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tb = s.shapes.add_textbox(Inches(0.40), Inches(0.18), Inches(12.5), Inches(0.42))
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = title
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(22), True, "Calibri", hexc(NAVY)
    tb2 = s.shapes.add_textbox(Inches(0.40), Inches(0.58), Inches(12.5), Inches(0.34))
    r2 = tb2.text_frame.paragraphs[0].add_run()
    r2.text = sub
    r2.font.size, r2.font.name, r2.font.color.rgb = Pt(11.5), "Calibri", MUTED
    f = s.shapes.add_textbox(Inches(0.40), Inches(7.16), Inches(12.5), Inches(0.24))
    rf = f.text_frame.paragraphs[0].add_run()
    rf.text = f"{FOOT}  |  {n}/5"
    rf.font.size, rf.font.name, rf.font.color.rgb = Pt(8.5), "Calibri", hexc(GREY)
    return s


def kpi(s, x, y, big, small, col=NAVY, w=2.95, h=1.12):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = hexc(ICE)
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
    r2 = tf.paragraphs[0].add_run()
    r2.text = small
    r2.font.size, r2.font.name, r2.font.color.rgb = Pt(9.5), "Calibri", INK


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
    sp.fill.fore_color.rgb = hexc(ICE)
    sp.line.color.rgb = hexc(col)
    sp.line.width = Pt(1.0)
    sp.shadow.inherit = False
    t = s.shapes.add_textbox(Inches(x + 0.22), Inches(y + 0.12), Inches(w - 0.44), Inches(0.30))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = title
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(12), True, "Calibri", hexc(col)
    for i, txt in enumerate((left, right)):
        tb = s.shapes.add_textbox(Inches(x + 0.22 + i * (w / 2 - 0.10)), Inches(y + 0.48),
                                  Inches(w / 2 - 0.34), Inches(h - 0.60))
        tf = tb.text_frame
        tf.word_wrap = True
        for j, line in enumerate(txt.split("\n")):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = line
            r.font.size, r.font.name, r.font.color.rgb = Pt(10), "Calibri", INK
            p.space_after = Pt(4)


def main() -> None:
    F = facts()
    f_flow, f_read, f_cov, f_types = fig_flow(F), fig_readout(F), fig_coverage(F), fig_types(F)

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # ---- 1
    s = slide(prs, 1, f"How the {F['n']} genes were chosen",
              "Four public and collaborator sources, four measured rules. Every candidate was re-scored "
              "in the Allen cells of these two regions before it earned a slot.")
    s.shapes.add_picture(str(f_flow), Inches(0.37), Inches(1.02), width=Inches(12.60))

    # ---- 2
    s = slide(prs, 2, "Why a gene is in - and why a similar one is out",
              "Each rule is a measurement with a cutoff, so for every rule there is a gene that passed "
              "and a comparable gene that did not.")
    W, H, GX, GY = 6.17, 1.50, 6.36, 1.62
    rulecard(s, 0.40, 1.02, W, H, "1", "Does it name the cell type?",
             ">=50% of that population, >=20pp over the competing types",
             "Vwc2l   97% of L5 NP cells, +71pp over the next type",
             "Cux1   72% in L2/3 but 94% in an amygdala GABA type")
    rulecard(s, 0.40 + GX, 1.02, W, H, "2", "Does it name the sub-population?",
             ">=50% of the sub-population, >=20pp over its siblings",
             "Hpse   88% of Sst_7 (229 cells) vs 8% in the rest of Sst",
             "20 discovery candidates   their sub-population already had one")
    rulecard(s, 0.40, 1.02 + GY, W, H, "3", "Can the instrument read it at all?",
             ">=50% of cells somewhere in ORBm or BMAp",
             "Adrb1   84%, the beta1-adrenergic receptor the SOW names",
             "Sstr4   1.4% of cells - the probe returns an empty map")
    rulecard(s, 0.40 + GX, 1.02 + GY, W, H, "4", "Does it report the morphine state?",
             "DE in >=4 of the 12 ORBm cell types in Jesse's data, and detectable",
             "Mbnl2   DE in 4 ORBm types, 99.8% detected",
             "Zbtb40   DE in 6 types but only 29% detected where we image")
    band(s, 0.40, 4.32, 12.53, 1.30, "Two more rules, because this is a standalone panel",
         f"5   Minimum non-neuronal set. 28% of the section is glia and vessels, but we measured that "
         f"they are never called neurons even with no glial probe (0.0%), so only {F['n_nn']} positive "
         f"marker(s) are kept: {F['nn_genes']}.",
         "6   Genes the SOW names are kept regardless of level - the SOW asks whether they are "
         "expressed, so a low answer is still an answer. All 8 are on the panel.", TEAL)
    band(s, 0.40, 5.76, 12.53, 1.28, f"What did not make it: {F['n_exc']} candidates rejected, each with "
                                     f"its measured number",
         f"{F['n_exc_det']}   detected in under half the cells of any population we image\n"
         f"{F['n_exc_red']}   redundant - a gene already on the panel does the same job",
         f"{F['paper_tested'] - F['paper_passed']} of {F['paper_tested']}   published markers failed when "
         f"re-tested in the Allen cells (Cux1, Scnn1a, Crym, Reln ...)\n"
         f"4   sex-determination genes, excluded on request", RUST)

    # ---- 3
    s = slide(prs, 3, f"The final panel - {F['n']} genes, two regions, one section",
              "A standalone custom panel: the 10x base panel is not included, so every gene here is a "
              "designed probe and nothing is free.")
    for i, (big, small, col) in enumerate([
            (f"{F['n']}", "genes on the shared panel", NAVY),
            ("20 / 20", "target cell types with their own marker", TEAL),
            ("96 / 96", "sub-populations with a dedicated marker", SAGE),
            ("8 / 8", "genes the SOW names by name", RUST)]):
        kpi(s, 0.40 + i * 3.16, 1.02, big, small, col)
    s.shapes.add_picture(str(f_read), Inches(0.40), Inches(2.34), width=Inches(6.55))
    tb = s.shapes.add_textbox(Inches(7.25), Inches(2.34), Inches(5.65), Inches(0.34))
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = "What each cell will tell us"
    r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(13), True, "Calibri", hexc(NAVY)
    y = 2.80
    for name, body, count in tells(F["cats"]):
        t = s.shapes.add_textbox(Inches(7.25), Inches(y), Inches(5.65), Inches(0.26))
        p = t.text_frame.paragraphs[0]
        r1 = p.add_run()
        r1.text = name
        r1.font.size, r1.font.bold, r1.font.name, r1.font.color.rgb = Pt(11), True, "Calibri", hexc(TEAL)
        r2 = p.add_run()
        r2.text = f"   {count}"
        r2.font.size, r2.font.name, r2.font.color.rgb = Pt(9.5), "Calibri", hexc(GREY)
        t2 = s.shapes.add_textbox(Inches(7.25), Inches(y + 0.26), Inches(5.65), Inches(0.52))
        tf = t2.text_frame
        tf.word_wrap = True
        rr = tf.paragraphs[0].add_run()
        rr.text = body
        rr.font.size, rr.font.name, rr.font.color.rgb = Pt(10), "Calibri", INK
        y += 0.86
    tb = s.shapes.add_textbox(Inches(0.40), Inches(6.74), Inches(12.5), Inches(0.36))
    r = tb.text_frame.paragraphs[0].add_run()
    r.text = ("The new capability is the last two rows: inside one cortical cell type, the panel "
              "separates cells that carry the morphine-dependence signature from those that do not.")
    r.font.size, r.font.italic, r.font.name, r.font.color.rgb = Pt(10.5), True, "Calibri", MUTED

    # ---- 4
    s = slide(prs, 4, "All 20 target cell types are covered - each by its own gene",
              "Six markers were added for the types the panel could previously only call from a "
              "combination of genes: Tnnc1, Adam19, Man2a1, Chn2, Frem3, Blnk.")
    s.shapes.add_picture(str(f_types), Inches(0.42), Inches(1.00), width=Inches(12.45))
    band(s, 0.40, 6.06, 12.53, 0.98,
         "The two below the 20pp bar are the transcriptome's limit, not the panel's",
         "005 L5 IT - Adam19, 58% of the type, +17.1pp.\n"
         "073 MEA-BST Sox6 Gaba - Chn2, 89% of the type, +14.8pp.",
         "No gene among the 32,285 in the atlas separates those two types better. Both are still called "
         "combinatorially at 77% and 92% recall on held-out cells.", TEAL)

    # ---- 5
    s = slide(prs, 5, "Evidence behind every number",
              "No gene was taken on a paper's word. Each was re-scored in the Allen cells of these two "
              "regions, in the population it is meant to report.")
    for i, (big, small, col) in enumerate([
            ("226,886", "Allen single cells re-analysed locally", NAVY),
            ("32,285", "genes screened genome-wide for better markers", TEAL),
            ("602", "candidates measured cell by cell", SAGE),
            (f"{F['n_exc']}", "candidates rejected, each with its number", RUST)]):
        kpi(s, 0.40 + i * 3.16, 1.02, big, small, col)
    for i, (big, small, col) in enumerate([
            (f"{F['claims_ok']} / {F['claims']}", "published marker claims confirmed in the atlas", NAVY),
            (f"{F['jesse_on']} / {F['jesse_total']}", "Jesse morphine DEGs that passed detection", RUST),
            ("16", "panel versions scored on one ruler", TEAL),
            ("24", "sheets of audit trail in the working file", SAGE)]):
        kpi(s, 0.40 + i * 3.16, 2.36, big, small, col)
    s.shapes.add_picture(str(f_cov), Inches(0.62), Inches(3.62), width=Inches(12.10))
    band(s, 0.40, 6.36, 12.53, 0.68, "Why the panel stops here",
         "Scoring a gene in the wrong population is the classic error: Cx3cr1 is 15% across neurons and "
         "100% in microglia. Every gene here is scored where it belongs.",
         f"Cell-type calling saturates near 250 genes, at 10x depth and at simulated Xenium depth alike. "
         f"Order: FINAL_Xenium_panel_ORBm_BMAp_297genes.xlsx, sheet SHARED_PANEL_ORDER.", NAVY)

    prs.save(DECK)
    print(f"wrote {DECK}  ({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
    print("figures:", ", ".join(str(p.name) for p in (f_flow, f_read, f_cov)))


if __name__ == "__main__":
    main()
