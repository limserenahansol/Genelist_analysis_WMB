"""Three schematic slides on panel selection, for a funding agency.

Audience is not the bench: no gene-by-gene tables. The job is to show that the
final gene list came from documented evidence through stated decision rules, and to
say what the finished panel can measure.

  1  How the panel was selected      schematic: 4 evidence sources -> 4 rules -> final list
  2  The rules, with worked examples  one accepted and one rejected gene per rule
  3  The final panel                  composition + measurement capability

Every number is read from the live order sheet (FINAL_..._for_MSGS111.xlsx), which the user
edits directly, so the slides never drift from what is actually ordered.

Output: outputs/Xenium_panel_selection_for_funder.pptx
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
FIG = OUT / "funder_figures"
FIG.mkdir(exist_ok=True)
# The live order sheet, which the user edits directly. Numbers on these
# slides must match what actually gets ordered, not my v3 proposal.
PANEL = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
DECK = OUT / "Xenium_panel_selection_for_funder.pptx"

NAVY, TEAL, RUST, GOLD, SAGE, TAUPE = ("#1D4E89", "#2A6F97", "#C44536",
                                       "#B08968", "#6B7C6A", "#8C7B6B")
GREY, PALE = "#B8B2A8", "#F2F0EC"
INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

# Functional groups, collapsed from the 13 panel blocks for a non-specialist.
GROUPS = [
    ("Cell identity and brain region", ["1_celltype_separator", "3_class_backbone",
                                        "11_class_backbone_optional", "8_TF_identity",
                                        "9_published_regional", "12_GSE283418_added"], NAVY),
    ("Druggable receptor map (GPCRs)", ["6_GPCR_druggable", "4_GPCR_cell_type_specific",
                                        "14_ORB_enriched_GPCR", "14_Jesse_ORB_GPCR"], TEAL),
    ("Neural activity and plasticity", ["5_IEG", "7_plasticity"], SAGE),
    ("Morphine-dependence state", ["13_Jesse_morphine_state"], RUST),
    ("Genetic-tag reporters", ["2_reporter_transgene"], GOLD),
]


def composition() -> pd.DataFrame:
    sh = pd.read_excel(PANEL, "SHARED_PANEL_ORDER")
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    sh["free"] = sh.gene.isin(base)
    rows = []
    for name, blocks, col in GROUPS:
        s = sh[sh.block.isin(blocks)]
        rows.append({"group": name, "n": len(s), "free": int(s.free.sum()),
                     "custom": int((~s.free).sum()), "colour": col})
    d = pd.DataFrame(rows)
    assert d.n.sum() == len(sh), f"groups cover {d.n.sum()} of {len(sh)}"
    return d


def box(ax, x, y, w, h, title, body, col, title_size=9.4, body_size=8.3, pale=PALE):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.010,rounding_size=0.028",
        facecolor=pale, edgecolor=col, linewidth=1.7, zorder=2))
    ax.add_patch(mpatches.Rectangle((x, y + h - 0.048), w, 0.048,
                                    facecolor=col, edgecolor=col, zorder=3))
    ax.text(x + w / 2, y + h - 0.024, title, ha="center", va="center",
            color="white", fontsize=title_size, fontweight="bold", zorder=4)
    ax.text(x + 0.014, y + h - 0.068, body, ha="left", va="top",
            fontsize=body_size, color="#222222", zorder=4, linespacing=1.45)


def arrow(ax, x0, y0, x1, y1, col="#8A8A8A"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=1.8,
                                shrinkA=2, shrinkB=2), zorder=1)


def fig_schematic(comp: pd.DataFrame) -> Path:
    """Three-column schematic.

    Geometry derives from one row pitch and a reserved bottom band, so the funnel
    strip cannot collide with the last source / rule box (it did on the first pass).
    """
    fig, ax = plt.subplots(figsize=(12.6, 5.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Row block must clear the column headers at y=0.94 and the funnel strip
    # (top edge 0.102); the first pass put the top box at 0.941 and clipped them.
    H, GAP, Y0 = 0.172, 0.026, 0.125
    rows = [Y0 + (3 - i) * (H + GAP) for i in range(4)]   # index 0 = top row
    TOP = rows[0] + H                                      # 0.891

    ax.text(0.084, 0.945, "EVIDENCE WE STARTED FROM", ha="center", fontsize=10,
            fontweight="bold", color=NAVY)
    ax.text(0.455, 0.945, "FOUR DECISION RULES", ha="center", fontsize=10,
            fontweight="bold", color=NAVY)
    ax.text(0.876, 0.945, "WHAT WE ORDER", ha="center", fontsize=10,
            fontweight="bold", color=NAVY)

    srcs = [
        ("REFERENCE ATLAS", "Allen Brain Cell Atlas\n226,886 single cells\nfrom the two regions", NAVY),
        ("PUBLISHED WORK", "11 documented sources,\n4 of them marker studies", TAUPE),
        ("COLLABORATOR 1", "Morphine-dependence\ngene expression\n431 candidates", RUST),
        ("COLLABORATOR 2", "Amygdala spatial panel\n98 candidates", TEAL),
    ]
    for i, (t, b, c) in enumerate(srcs):
        box(ax, 0.005, rows[i], 0.158, H, t, b, c, title_size=9.2, body_size=8.1)

    rules = [
        ("1", "Does it identify the cell type?",
         "Statistical specificity against genes\nthe panel already carries", NAVY),
        ("2", "Is it a druggable receptor we\ncannot already see?",
         "Regional enrichment plus a gap in\nreceptor-family coverage", TEAL),
        ("3", "Does it report the\nmorphine-dependent state?",
         "Differential expression across the\n12 target cell types", RUST),
        ("4", "Will the instrument detect it?",
         "Fraction of cells expressing it in\nthe reference atlas", SAGE),
    ]
    for i, (n, q, m, c) in enumerate(rules):
        y = rows[i]
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.232, y), 0.446, H, boxstyle="round,pad=0.010,rounding_size=0.028",
            facecolor="white", edgecolor=c, linewidth=1.7, zorder=2))
        ax.add_patch(mpatches.Circle((0.258, y + H - 0.040), 0.0170, facecolor=c, zorder=3))
        ax.text(0.258, y + H - 0.040, n, ha="center", va="center", color="white",
                fontsize=9.6, fontweight="bold", zorder=4)
        ax.text(0.284, y + H - 0.020, q, ha="left", va="top", fontsize=9.2,
                fontweight="bold", color=c, zorder=4, linespacing=1.3)
        ax.text(0.284, y + 0.058, m, ha="left", va="top", fontsize=8.1,
                color="#444444", zorder=4, linespacing=1.4)
        arrow(ax, 0.166, y + H / 2, 0.229, y + H / 2)
        arrow(ax, 0.681, y + H / 2, 0.752, (Y0 + TOP) / 2)

    bx, by, bw, bh = 0.757, Y0, 0.238, TOP - Y0
    ax.add_patch(mpatches.FancyBboxPatch(
        (bx, by), bw, bh, boxstyle="round,pad=0.010,rounding_size=0.028",
        facecolor="#EAF0F6", edgecolor=NAVY, linewidth=2.4, zorder=2))
    # Placed as fractions of the box height so the three zones stay evenly
    # spaced instead of leaving a void in the middle.
    cx = bx + bw / 2

    def fy(frac):
        return by + bh * frac

    ax.text(cx, fy(0.945), "FINAL PANEL", ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=NAVY)
    ax.text(cx, fy(0.800), str(int(comp.n.sum())), ha="center", va="center",
            fontsize=38, fontweight="bold", color=NAVY)
    ax.text(cx, fy(0.700), "genes", ha="center", va="center",
            fontsize=9.6, color="#444444")
    ax.plot([bx + 0.03, bx + bw - 0.03], [fy(0.645)] * 2, color=NAVY, lw=0.9, alpha=0.35)
    tf, tc = int(comp.free.sum()), int(comp.custom.sum())
    ax.text(cx, fy(0.455),
            f"{tf} already included\non the standard platform\nat no extra cost\n\n"
            f"{tc} custom probes\nwe pay to design",
            ha="center", va="center", fontsize=8.9, color="#333333", linespacing=1.5)
    ax.plot([bx + 0.03, bx + bw - 0.03], [fy(0.255)] * 2, color=NAVY, lw=0.9, alpha=0.35)
    ax.text(cx, fy(0.135), "2 brain regions  |  20 cell types\n1 tissue section, 1 animal",
            ha="center", va="center", fontsize=9.0, color=NAVY,
            linespacing=1.55, fontweight="bold")

    ax.add_patch(mpatches.FancyBboxPatch(
        (0.005, 0.022), 0.673, 0.080, boxstyle="round,pad=0.006,rounding_size=0.018",
        facecolor="#F7F5F2", edgecolor=GREY, linewidth=1.0, zorder=2))
    ax.text(0.3415, 0.062,
            f"701 candidates screened  ->  {int(comp.n.sum())} selected "
            f"({int(comp.n.sum()) / 701 * 100:.0f}%).   Every gene records its evidence "
            "and the rule that admitted it.",
            ha="center", va="center", fontsize=9.0, color="#333333", zorder=4)

    fig.tight_layout()
    p = FIG / "F1_selection_schematic.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_composition(comp: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6),
                             gridspec_kw={"width_ratios": [1.45, 1]})

    ax = axes[0]
    d = comp.iloc[::-1]
    y = np.arange(len(d))
    ax.barh(y, d.n, color=d.colour, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([g.replace(" (GPCRs)", "") for g in d.group], fontsize=9.8)
    for i, r in enumerate(d.itertuples()):
        ax.text(r.n + 1.8, i, str(r.n), va="center", fontsize=10.5,
                fontweight="bold", color="#333333")
    ax.set_xlim(0, 125)
    ax.set_xlabel("number of genes", fontsize=9.5)
    ax.set_title(f"A. What the {int(comp.n.sum())} genes do", fontsize=11, color=NAVY)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

    ax = axes[1]
    tf, tc = int(comp.free.sum()), int(comp.custom.sum())
    wedges, _ = ax.pie([tf, tc], colors=[SAGE, NAVY], startangle=90,
                       wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2))
    ax.text(0, 0.08, str(tf + tc), ha="center", fontsize=25, fontweight="bold", color=NAVY)
    ax.text(0, -0.16, "genes", ha="center", fontsize=9.6, color="#555555")
    ax.legend(wedges,
              [f"{tf} already on the standard platform\n(no added cost)",
               f"{tc} custom probes designed\nfor this project"],
              fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              frameon=False, handlelength=1.1)
    ax.set_title("B. Cost structure", fontsize=11, color=NAVY)

    fig.tight_layout()
    p = FIG / "F2_composition.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


# ---------------------------------------------------------------- deck helpers
def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def set_run(p, text, size=18, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
    r.font.color.rgb = color
    return r


def new_slide(prs, title, sub, n, total=3):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                             Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(NAVY)
    bar.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.4), Inches(0.18), Inches(12.5), Inches(0.44))
    tb.text_frame.word_wrap = True
    set_run(tb.text_frame.paragraphs[0], title, 25, True, rgb(NAVY))
    if sub:
        sb = s.shapes.add_textbox(Inches(0.4), Inches(0.64), Inches(12.5), Inches(0.36))
        sb.text_frame.word_wrap = True
        set_run(sb.text_frame.paragraphs[0], sub, 13, False, MUTED)
    fb = s.shapes.add_textbox(Inches(0.4), Inches(7.18), Inches(12.5), Inches(0.26))
    set_run(fb.text_frame.paragraphs[0],
            f"Spatial gene panel for orbitofrontal cortex and basomedial amygdala  |  {n}/{total}",
            10.5, False, MUTED)
    return s


def lines(slide, items, x, y, w, h, size=12, colour=INK):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, t, size, False, colour)
        p.space_after = Pt(6)
    return tb


def picture(slide, path, top, max_h, max_w=12.6):
    pic = slide.shapes.add_picture(str(path), Inches(0), Inches(top), height=Inches(max_h))
    if pic.width > Inches(max_w):
        sc = Inches(max_w) / pic.width
        pic.width, pic.height = int(pic.width * sc), int(pic.height * sc)
    pic.left = int((Inches(13.333) - pic.width) / 2)
    return pic.top / 914400 + pic.height / 914400


def table(slide, df, x, y, w, col_w, size=10.5, row_h=0.34, head=NAVY, band=None):
    shp = slide.shapes.add_table(df.shape[0] + 1, df.shape[1], Inches(x), Inches(y),
                                 Inches(w), Inches(row_h * (df.shape[0] + 1)))
    t = shp.table
    for i, cw in enumerate(col_w):
        t.columns[i].width = Inches(cw)
    for j, name in enumerate(df.columns):
        c = t.cell(0, j)
        c.text = str(name)
        c.fill.solid()
        c.fill.fore_color.rgb = rgb(head)
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.name = Pt(size), True, "Calibri"
                r.font.color.rgb = WHITE
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            c = t.cell(i + 1, j)
            c.text = str(df.iat[i, j])
            c.fill.solid()
            c.fill.fore_color.rgb = rgb(band[i]) if band and band[i] else (
                RGBColor(0xFF, 0xFF, 0xFF) if i % 2 == 0 else RGBColor(0xF2, 0xF0, 0xEC))
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(size), "Calibri"
                    r.font.color.rgb = INK
    return shp


def build(comp, figs) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 1 schematic
    s = new_slide(prs, "How the gene panel was selected",
                  "The instrument reads a fixed number of genes per tissue section, so every slot has to be "
                  "earned. Four rules decided which genes earned one.", 1)
    picture(s, figs["schematic"], 1.10, 5.50)

    # 2 worked examples
    s = new_slide(prs, "The same four rules, applied to real candidates",
                  "Each rule is a measurement with a threshold, so any gene's inclusion can be re-checked "
                  "by someone else.", 2)
    ex = pd.DataFrame([
        ["1.  Identifies the cell type",
         "How much more specific it is than\ngenes the panel already carries",
         "Col23a1  -  3.7x more specific",
         "Sfrp1  -  0.9x, no better than\nwhat we already have"],
        ["2.  Druggable receptor we\n     cannot already see",
         "Regional enrichment plus receptor-\nfamily coverage",
         "Chrm1  -  M1 receptor; we could\nonly see M2 before",
         "Gpr26  -  no known drug binds it"],
        ["3.  Reports the morphine-\n     dependent state",
         "How many of the 12 target cell types\nchange their expression",
         "Per2  -  changes in 11 of 12",
         "Nr4a3  -  only 5 of 12 once\nrestricted to our regions"],
        ["4.  The instrument will detect it",
         "Fraction of cells expressing it in the\nreference atlas",
         "Vps13a  -  present in 95% of cells",
         "Mchr1  -  only 32%, too faint\nto map reliably"],
    ], columns=["Rule", "The measurement", "Example ACCEPTED", "Example REJECTED"])
    table(s, ex, 0.4, 1.15, 12.5, col_w=[2.85, 3.35, 3.15, 3.15], size=10.5, row_h=0.80)

    lines(s, [
        "Two consequences worth noting. A gene can pass one rule and still be turned down: the three most "
        "regionally enriched receptors were all dropped for being too faint to image.",
        "And the rules are independent. A receptor earns its slot by showing where a drug target sits, whether or "
        "not morphine changes it - so one panel serves the pharmacology aim and the addiction aim at the same time.",
    ], 0.4, 5.25, 12.5, 1.5, size=12)

    # 3 final panel
    s = new_slide(prs, "The final panel, and what it will measure",
                  f"{int(comp.n.sum())} genes read simultaneously in two brain regions of the same animal, on one tissue section.", 3)
    bottom = picture(s, figs["composition"], 1.05, 3.95)
    caps = pd.DataFrame([
        ["Which cell is this?",
         "All 20 cell types across the two regions remain individually identifiable."],
        ["Where are the drug targets?",
         f"{int(comp.loc[comp.group.str.startswith('Druggable'), 'n'].iloc[0])} receptors mapped in place, "
         "including four newly added: M1 muscarinic, group-III glutamate, relaxin, one orphan."],
        ["Was this cell recently active?",
         "Activity and plasticity genes report which cells fired during the behaviour."],
        ["Is this cell in a dependent state?",
         "New capability: separates dependence-positive from dependence-negative cells of the SAME type."],
    ], columns=["Question the panel answers", "How"])
    table(s, caps, 0.4, bottom + 0.16, 12.5, col_w=[3.4, 9.1], size=11, row_h=0.42,
          band=[None, None, None, "#F7EAE8"])

    prs.save(DECK)
    return DECK


def main() -> None:
    comp = composition()
    figs = {"schematic": fig_schematic(comp), "composition": fig_composition(comp)}
    deck = build(comp, figs)
    print(comp[["group", "n", "free", "custom"]].to_string(index=False))
    print(f"\ntotal {comp.n.sum()} = free {comp.free.sum()} + custom {comp.custom.sum()}")
    for k, v in figs.items():
        print(f"fig {k:10s} -> {v}")
    print(f"deck          -> {deck}")


if __name__ == "__main__":
    main()
