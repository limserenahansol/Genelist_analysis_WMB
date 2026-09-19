"""Merged 4-slide PI deck: morphine relevance AND Xenium detectability.

This reconciles two earlier decks that disagreed.

  Add_genes_Dan_Jesse_final_EN.pptx  proposed Rxfp1 + Per2/Pcsk1/Per1 + Chrm1/Grm8.
    Its contribution: an Allen detectability filter. Every number in it checks out
    (Chrm1 92%, Grm8 99%, Mas1 45%, Gpr68 40%, Mchr1 32%). Xenium needs transcripts
    that are actually present, and that deck was the only one applying that test.

  ORBm_BMAp_panel_v2_decision_EN.pptx  proposed Per2/Pcsk1/Arid5b/Per1/Camk2g plus
    four free-on-base genes. Its contribution: counting DE only in the 12 ORBm
    anchor subclasses we actually image, and a Dan re-check.

Neither test alone is sufficient:
  - Chrm1 is not a morphine DEG at all and Grm8 is DE in 0 of our 12 anchors, so
    both fail relevance despite winning on detectability.
  - Detectability was never checked for Per2, Pcsk1, Arid5b, Bhlhe40, Sema3e or
    Gadd45a, so the v2 recommendation had an unmeasured risk.
  - Applying both tests promotes Vps13a (7/12 anchors, 95% detection) and Camk2g
    (6/12 Down, 93%), which the v2 deck had parked in Tier 2.

Detectability source: outputs/jesse_allen_gpcr_abundance/ (12 ORBm anchors) and
subclass_markers_expanded for Per1/Rxfp1. Six candidates remain unscored because
the Allen raw matrices were never downloaded - that is the one open item.

Output: outputs/ORBm_BMAp_panel_v3_merged_EN.pptx  (4 slides)
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
FIG = OUT / "panel_v3_figures"
FIG.mkdir(exist_ok=True)
DECK = OUT / "ORBm_BMAp_panel_v3_merged_EN.pptx"

RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
ABUND = OUT / "jesse_allen_gpcr_abundance" / "Jesse_GPCR_Allen_ORBm_summary.csv"
LONG = OUT / "subclass_markers_expanded" / "Subclass_Discriminating_Markers_long.csv"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"
PANEL = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"

NAVY, TEAL, RUST, GOLD, SAGE, TAUPE = ("#1D4E89", "#2A6F97", "#C44536",
                                       "#B08968", "#6B7C6A", "#8C7B6B")
GREY = "#B8B2A8"
INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.grid": False,
})

ORBM = ["007 L2/3 IT CTX Glut", "006 L4/5 IT CTX Glut", "005 L5 IT CTX Glut",
        "022 L5 ET CTX Glut", "032 L5 NP CTX Glut", "030 L6 CT CTX Glut",
        "029 L6b CTX Glut", "004 L6 IT CTX Glut",
        "052 Pvalb Gaba", "053 Sst Gaba", "046 Vip Gaba", "049 Lamp5 Gaba"]

# Final call after applying both tests. (gene, slot, note)
FINAL = [
    ("Per2",    "1 custom", "11/12 anchors Up, glut 8 / GABA 3. Broadest gene in the dataset."),
    ("Pcsk1",   "1 custom", "9/12 Up. Proenkephalin / POMC convertase."),
    ("Vps13a",  "1 custom", "7/12 Up AND 95% detection - best measured on both axes."),
    ("Camk2g",  "1 custom", "6/12 DOWN, 93% detection. Only direction control."),
    ("Arid5b",  "1 custom", "8/12 Up, glut 6 / GABA 2. Only broad gene besides Per2 reaching GABA."),
    ("Bhlhe40", "free",     "4/12 Up. Free on Xenium base."),
    ("Sema3e",  "free",     "3/12 Up. Free on base."),
    ("Gadd45a", "free",     "1/12 Up. Free on base."),
    ("Rxfp1",   "free",     "ORB-enriched GPCR (19 subclasses) but 34% detection - weak signal."),
]
REJECT = [
    ("Chrm1", "92% detection but NOT a morphine DEG at all. Detectable everywhere = no contrast."),
    ("Grm8",  "99% detection but DE in 0 of our 12 anchors (its DE was in PL/ILA)."),
    ("Per1",  "8/12 Up, but 63% max / only 4 of 12 anchors above 50%. Redundant with Per2."),
    ("Mas1 / Gpr68 / Mchr1", "ORB-enriched but 45 / 40 / 32% detection - too sparse for a slot."),
]


def detectability() -> pd.DataFrame:
    a = pd.read_csv(ABUND)[["gene", "max_pct", "mean_pct_across_anchors", "n_anchors_pct_ge_50"]]
    long = pd.read_csv(LONG)
    extra = []
    for g in ["Per1", "Rxfp1"]:
        s = long[(long.gene == g) & (long.subclass.isin(ORBM))]
        if len(s) and g not in set(a.gene):
            extra.append({"gene": g, "max_pct": s.pct_expr.max(),
                          "mean_pct_across_anchors": s.pct_expr.mean(),
                          "n_anchors_pct_ge_50": int((s.pct_expr >= 50).sum())})
    if extra:
        a = pd.concat([a, pd.DataFrame(extra)], ignore_index=True)
    return a


def fig_two_axis(rank: pd.DataFrame, det: pd.DataFrame) -> Path:
    """The reconciliation: morphine relevance (x) vs Xenium detectability (y)."""
    panel = set(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str))
    d = det.merge(rank[["gene", "n_orbm", "direction"]], on="gene", how="left")
    d["n_orbm"] = d.n_orbm.fillna(0)
    d["on_panel"] = d.gene.isin(panel)

    fig, ax = plt.subplots(figsize=(9.6, 5.9))
    # Shade only the pass-both quadrant. Shading the whole y>=50 band read as if
    # Grm8/Chrm1 were inside the accept zone, which is the opposite of the point.
    ax.add_patch(plt.Rectangle((5.5, 50), 12.6 - 5.5, 58, color="#EAF2F9", zorder=0))
    ax.axvline(5.5, color="#AAA", lw=1.0, ls=(0, (4, 3)), zorder=1)
    ax.axhline(50, color="#AAA", lw=1.0, ls=(0, (4, 3)), zorder=1)

    # Rxfp1 (34.1) and Mchr1 (32.0) sit on top of each other at x=0.
    nudge = {"Mchr1": (7, -12), "Rxfp1": (7, 3)}
    for _, r in d.iterrows():
        if r.on_panel:
            col, mk = GREY, "s"
        elif r.n_orbm >= 5.5 and r.max_pct >= 50:
            col, mk = NAVY, "o"
        elif r.max_pct >= 50:
            col, mk = RUST, "X"
        else:
            col, mk = TAUPE, "v"
        ax.scatter(r.n_orbm, r.max_pct, s=135, color=col, marker=mk,
                   edgecolor="white", linewidth=1.2, zorder=3)
        ax.annotate(r.gene, (r.n_orbm, r.max_pct), xytext=nudge.get(r.gene, (7, 5)),
                    textcoords="offset points", fontsize=8.6, color="#333", zorder=4)

    ax.set_xlim(-0.7, 12.6)
    ax.set_ylim(0, 108)
    ax.set_xlabel("MORPHINE RELEVANCE   ->   ORBm anchor cell types with DE (of 12)", fontsize=9.5)
    ax.set_ylabel("XENIUM DETECTABILITY   ->   Allen detection, % of cells", fontsize=9.5)
    ax.set_title("Both tests must pass: relevance (x) and detectability (y)",
                 fontsize=11.5, color=NAVY, pad=10)
    ax.text(12.4, 103, "PASS BOTH", ha="right", fontsize=9, color=NAVY, fontweight="bold")
    ax.text(0.0, 103, "detectable but not morphine-related", fontsize=8.6, color=RUST)
    ax.text(0.0, 3, "too sparse for a Xenium slot", fontsize=8.6, color=TAUPE)
    handles = [
        plt.Line2D([], [], marker="o", ls="", color=NAVY, label="pass both -> add"),
        plt.Line2D([], [], marker="X", ls="", color=RUST, label="detectable, not relevant -> reject"),
        plt.Line2D([], [], marker="v", ls="", color=TAUPE, label="too sparse -> reject"),
        plt.Line2D([], [], marker="s", ls="", color=GREY, label="already on panel"),
    ]
    # Lower right is the one empty region and keeps the legend out of the shaded quadrant.
    ax.legend(handles=handles, fontsize=8.4, loc="lower right", frameon=False)
    fig.text(0.5, -0.02,
             "Per2, Pcsk1, Arid5b, Bhlhe40, Sema3e and Gadd45a are NOT plotted: Allen detectability was never "
             "scored for them (raw matrices not downloaded). That is the one open item.",
             ha="center", fontsize=8.2, color="#666")
    fig.tight_layout()
    p = FIG / "v3_two_axis.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_sources(rank: pd.DataFrame, dan: pd.DataFrame) -> Path:
    """A. Jesse breadth ranking.  B. Dan specificity, added vs left out."""
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.9),
                             gridspec_kw={"width_ratios": [1.2, 1]})
    top = rank.nlargest(12, ["n_orbm", "n_DE_clusters"]).iloc[::-1]
    cols = {"already on panel": SAGE, "FREE on base": TEAL, "1 custom slot": RUST}
    ax = axes[0]
    y = np.arange(len(top))
    ax.barh(y, top.n_orbm, color=[cols[c] for c in top.slot_cost], height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(top.gene, fontsize=9)
    for i, (n, dr) in enumerate(zip(top.n_orbm, top.direction)):
        ax.text(n + 0.15, i, f"{n} {dr}", va="center", fontsize=8.2, color="#4A4A4A")
    ax.set_xlim(0, 13.5)
    ax.set_xlabel("ORBm anchor cell types with DE (of 12)", fontsize=9)
    ax.set_title("A. Jesse: morphine DEG breadth on OUR cell types", fontsize=10.5)
    present = [k for k in cols if (top.slot_cost == k).any()]
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=cols[k]) for k in present],
              present, fontsize=8, loc="lower right", frameon=False)

    panel = set(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str))
    d = dan.copy()
    d["ON"] = d.gene.isin(panel)
    a14 = ["Col23a1", "Slc29a4", "Cck", "Gfra1", "Sp8", "Abca8a", "Calcrl",
           "Lamb3", "Syndig1l", "Tspan18", "Gabre", "Nos1", "Oprl1", "Dnah5"]
    A = d[d.gene.isin(a14)].sort_values("max_spec", ascending=False)
    B = d[~d.ON].nlargest(4, "max_spec")
    ax = axes[1]
    ya = np.arange(len(A))[::-1]
    yb = np.arange(len(B)) - len(B) - 0.6
    ax.barh(ya, A.max_spec, color=NAVY, height=0.6, label="added earlier (14)")
    ax.barh(yb, B.max_spec, color=RUST, height=0.6, label="best NOT added")
    ax.set_yticks(list(ya) + list(yb))
    ax.set_yticklabels(list(A.gene) + list(B.gene), fontsize=8)
    ax.axvline(1.0, color="#333", lw=1.2, ls=(0, (4, 3)))
    ax.text(1.0, ya.max() + 0.9, "  spec = 1.0", fontsize=8, color="#333", va="bottom")
    ax.axhline((yb.max() + ya.min()) / 2, color="#8A8A8A", lw=0.9)
    ax.set_ylim(yb.min() - 0.8, ya.max() + 1.6)
    ax.set_xlabel("max specificity vs the panel", fontsize=9)
    ax.set_title("B. Dan: nothing left clears spec 1.0", fontsize=10.5)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    fig.tight_layout()
    p = FIG / "v3_sources.png"
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


def new_slide(prs, title, sub, n, total=4):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(NAVY)
    bar.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.4), Inches(0.18), Inches(12.5), Inches(0.44))
    tb.text_frame.word_wrap = True
    set_run(tb.text_frame.paragraphs[0], title, 24, True, rgb(NAVY))
    if sub:
        sb = s.shapes.add_textbox(Inches(0.4), Inches(0.62), Inches(12.5), Inches(0.34))
        sb.text_frame.word_wrap = True
        set_run(sb.text_frame.paragraphs[0], sub, 13, False, MUTED)
    fb = s.shapes.add_textbox(Inches(0.4), Inches(7.18), Inches(12.5), Inches(0.26))
    set_run(fb.text_frame.paragraphs[0],
            f"Xenium ORBm + BMAp add-on  |  Jesse Niehaus  +  Daniel Berg / Scherrer  |  {n}/{total}",
            11, False, MUTED)
    return s


def lines(slide, items, x, y, w, h, size=12, colour=INK):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, t, size, False, colour)
        p.space_after = Pt(5)
    return box


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
            if band and band[i]:
                c.fill.fore_color.rgb = rgb(band[i])
            else:
                c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 == 0 else RGBColor(0xF2, 0xF0, 0xEC)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(size), "Calibri"
                    r.font.color.rgb = INK
    return shp


def build(rank, dan, det, figs) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 1 the two source datasets
    s = new_slide(prs, "The two datasets, scored against our panel",
                  "Left: Jesse's morphine DEGs, counted only in the 12 ORBm cell types we image. "
                  "Right: Dan's 98 amygdala genes, re-scored in Allen BMAp.", 1)
    bottom = picture(s, figs["sources"], 1.02, 4.35)
    lines(s, [
        "Jesse: 304 unique DEGs; only 30 already on the panel. The two broadest genes in the whole dataset, Per2 (11/12) and "
        "Pcsk1 (9/12), were both missing. Our existing IEGs start at 8/12. Lamp5 carries no DEG at all, so 11 is the ceiling.",
        "Dan: 52 of 98 already on the panel. The best of the 46 left off scores max_spec 0.89, below the 1.0 line where a gene "
        "starts beating what the panel already carries. Glipr1 (0.88) serves anchor 113, but that anchor already has Penk (2.31) "
        "and Lamb3 (1.51). Nothing further to add from Dan.",
    ], 0.4, bottom + 0.10, 12.5, 1.3, size=11.5)

    # 2 the reconciliation
    s = new_slide(prs, "Why two earlier drafts disagreed - and the test that settles it",
                  "A gene earns a slot only if it is BOTH morphine-relevant in our cell types AND detectable enough for Xenium.", 2)
    bottom = picture(s, figs["two_axis"], 1.00, 4.55)
    lines(s, [
        "The earlier draft that proposed Chrm1 and Grm8 was right to introduce a detectability test - every number in it is correct "
        "(Chrm1 92%, Grm8 99% vs Mas1 45%, Gpr68 40%, Mchr1 32%). But both fail the other axis: Chrm1 is not a morphine DEG at all, "
        "and Grm8 is DE in 0 of our 12 anchors. Detectable everywhere means no contrast to image.",
        "Applying both tests promotes Vps13a (7/12 anchors AND 95% detection) and Camk2g (6/12 DOWN, 93%) over Chrm1 / Grm8.",
    ], 0.4, bottom + 0.10, 12.5, 1.2, size=11.5)

    # 3 final decision
    s = new_slide(prs, "FINAL  |  9 genes added, 5 custom slots",
                  "Appended as block 13_Jesse_morphine_state. No existing gene removed or re-ranked. Nothing added from Dan.", 3)
    add = pd.DataFrame([{"Gene": g, "Slot": sl, "Why": w} for g, sl, w in FINAL])
    band = ["#EAF0F6" if sl == "1 custom" else "#F0F5F2" for _, sl, _ in FINAL]
    table(s, add, 0.4, 1.02, 12.5, col_w=[1.15, 1.15, 10.2], size=11, row_h=0.375, band=band)
    rej = pd.DataFrame([{"Rejected": g, "Reason": r} for g, r in REJECT])
    table(s, rej, 0.4, 5.05, 12.5, col_w=[2.35, 10.15], size=10.5, row_h=0.36, head=RUST)
    lines(s, [
        "Panel: 158 -> 167 genes = 48 free on base + 119 custom (was 44 + 114).",
    ], 0.4, 6.9, 12.5, 0.3, size=11.5)

    # 4 open items
    s = new_slide(prs, "What needs a decision", "Two open items, one of them blocking.", 4)
    q = pd.DataFrame([
        ["1", "BLOCKING", "Custom slots go 114 -> 119, but the original vendor cap was 100 custom add-ons. "
                          "Needs confirmation before ordering.",
         "If the cap holds at 100, drop the weakest Dan genes first: Gabre (spec 0.95, CEA-BST), "
         "Tspan18 (0.96, SI/LPO border), Syndig1l (1.32, CEA-BST). They serve neighbours, not BMAp core."],
        ["2", "Data gap", "Allen detectability is unscored for Per2, Pcsk1, Arid5b, Bhlhe40, Sema3e and Gadd45a "
                          "- the raw Allen matrices were never downloaded.",
         "Per2 and Pcsk1 are the top two morphine genes and worth the risk. If detectability matters more than "
         "breadth, Fxr1 (7/12, 75% verified) is the ready substitute for Arid5b."],
    ], columns=["#", "Type", "Issue", "Option"])
    table(s, q, 0.4, 1.05, 12.5, col_w=[0.45, 1.25, 5.3, 5.5], size=11, row_h=0.95)
    lines(s, [
        "Everything else is settled and orderable: FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v2_167genes.xlsx keeps MSGS111's "
        "formatting, column widths, frozen panes and every existing row byte-identical - rows were only appended.",
        "The 9 genes report morphine-dependence state, not cell identity, so ANCHOR_COVERAGE is unchanged and all 20 cell "
        "types remain separable. New question the panel can answer: within one L5 IT cell, is the dependence signature ON or OFF?",
    ], 0.4, 3.35, 12.5, 1.4, size=12)

    prs.save(DECK)
    return DECK


def main() -> None:
    rank = pd.read_excel(RANK, "ranking_all")
    dan = pd.read_excel(DAN, "all_98_genes")
    det = detectability()
    figs = {"sources": fig_sources(rank, dan), "two_axis": fig_two_axis(rank, det)}
    deck = build(rank, dan, det, figs)
    print("detectability scored for:", ", ".join(sorted(det.gene)))
    for k, v in figs.items():
        print(f"fig {k:9s}-> {v}")
    print(f"deck        -> {deck}")


if __name__ == "__main__":
    main()
