"""English 4-slide PI deck: why the Jesse/Dan genes were considered, and what was finally added.

House style matches make_jesse_dan_decision_deck.py: 13.333x7.5in, navy top bar,
Calibri 28pt bold navy title, 14pt muted subtitle, 10pt footer, DejaVu Sans
matplotlib panels labelled "A."/"B." with a 9pt grey provenance suptitle.

Slides
  1  Jesse   - DEG data and which genes rank top on OUR ORBm cell types
  2  Dan     - 98-gene re-check against the current panel; nothing further to add
  3  Selection rule and slot budget
  4  FINAL   - the 9 genes decided, and the resulting panel

Outputs
  outputs/panel_v2_figures/*.png
  outputs/ORBm_BMAp_panel_v2_decision_EN.pptx
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
FIG = OUT / "panel_v2_figures"
FIG.mkdir(exist_ok=True)

RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"
PANEL_V1 = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
DECK = OUT / "ORBm_BMAp_panel_v2_decision_EN.pptx"

NAVY, TEAL, RUST, GOLD, TAUPE, SAGE = ("#1D4E89", "#2A6F97", "#C44536",
                                       "#B08968", "#8C7B6B", "#6B7C6A")
GREY = "#B8B2A8"
PROV = ("Jesse Niehaus 5-day escalating morphine, DESeq2 subclass pseudobulk padj <= 0.1  |  "
        "Daniel Berg / Scherrer GSE283418, 98-gene Molecular Cartography panel")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.grid": False,
})

ADDED14 = ["Col23a1", "Slc29a4", "Cck", "Gfra1", "Sp8", "Abca8a", "Calcrl",
           "Lamb3", "Syndig1l", "Tspan18", "Gabre", "Nos1", "Oprl1", "Dnah5"]

# gene, ORBm anchors, direction, free-on-base, short reason
FINAL_ADD = [
    ("Per2",    11, "Up",   False, "Top DEG overall. Circadian clock."),
    ("Pcsk1",    9, "Up",   False, "Prohormone convertase 1 (proenkephalin / POMC)."),
    ("Arid5b",   8, "Up",   False, "Broad TF; also reaches interneurons."),
    ("Per1",     8, "Up",   False, "Second clock gene; confirms Per2."),
    ("Camk2g",   6, "Down", False, "Strongest DOWN gene. Direction control."),
    ("Bhlhe40",  4, "Up",   True,  "Metabolic / circadian TF. Free on base."),
    ("Sema3e",   3, "Up",   True,  "Free on base; previously missed."),
    ("Gadd45a",  1, "Up",   True,  "IEG-adjacent TF. Free on base."),
    ("Rxfp1",    0, "n/a",  True,  "ORB-enriched GPCR (19 subclasses). Circuit marker."),
]


def save(fig, name):
    p = FIG / name
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_jesse(rank: pd.DataFrame) -> Path:
    """A. breadth ranking coloured by slot cost.  B. glut vs GABA for the picks."""
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.4),
                             gridspec_kw={"width_ratios": [1.35, 1]})

    top = rank.nlargest(14, ["n_orbm", "n_DE_clusters"]).iloc[::-1]
    cols = {"already on panel": SAGE, "FREE on base": TEAL, "1 custom slot": RUST}
    ax = axes[0]
    y = np.arange(len(top))
    ax.barh(y, top.n_orbm, color=[cols[c] for c in top.slot_cost], height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(top.gene, fontsize=9)
    for i, (n, d) in enumerate(zip(top.n_orbm, top.direction)):
        ax.text(n + 0.15, i, f"{n} {d}", va="center", fontsize=8.2, color="#4A4A4A")
    ax.set_xlim(0, 13.5)
    ax.set_xlabel("ORBm anchor cell types with significant DE  (of 12)", fontsize=9)
    ax.set_title("A. Which morphine DEGs are broadest in OUR ORBm cell types", fontsize=10.5)
    # Only legend the categories that actually appear in this top-N slice: no
    # free-on-base gene reaches it, so a teal key here would point at nothing.
    present = [k for k in cols if (top.slot_cost == k).any()]
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=cols[k]) for k in present],
              present, fontsize=8, loc="lower right", frameon=False)

    picks = [g for g, *_ in FINAL_ADD if g != "Rxfp1"]
    sub = rank[rank.gene.isin(picks)].set_index("gene").loc[picks].iloc[::-1]
    ax = axes[1]
    y = np.arange(len(sub))
    ax.barh(y + 0.19, sub.n_glut, height=0.36, color=NAVY, label="Glut anchors (of 8)")
    ax.barh(y - 0.19, sub.n_gaba, height=0.36, color=GOLD, label="GABA anchors (of 4)")
    ax.set_yticks(y)
    ax.set_yticklabels(sub.index, fontsize=9)
    ax.set_xlabel("ORBm anchor cell types with significant DE", fontsize=9)
    ax.set_title("B. Do the selected genes work in both classes?", fontsize=10.5)
    ax.legend(fontsize=8, loc="lower right", frameon=False)

    fig.suptitle(PROV.split("  |  ")[0], fontsize=9, color="#555", y=1.01)
    fig.tight_layout()
    return save(fig, "v2_Fig1_jesse.png")


def fig_dan(dan: pd.DataFrame) -> Path:
    """A. fate of all 98 Dan genes.  B. specificity of added-14 vs best not added."""
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0),
                             gridspec_kw={"width_ratios": [1, 1.15]})

    panel = set(pd.read_excel(PANEL_V1, "SHARED_PANEL_ORDER").gene.astype(str))
    d = dan.copy()
    d["ON"] = d.gene.isin(panel)
    off = d[~d.ON]
    fate = {
        "Already on panel": int(d.ON.sum()),
        "Added earlier (14)": len(ADDED14),
        "Off panel, spec < 0.9": int((~d.ON & (off.max_spec.notna())).sum()),
        "Not scored in Allen": int(off.allen_BMAp.eq("not scored").sum()),
    }
    # the 14 are inside "already on panel" now, so show them as a subset, not a sum
    labels = ["Already on panel\n(incl. the 14 added earlier)", "Off panel,\nmax_spec < 0.9",
              "Off panel,\nnot scored in Allen"]
    vals = [int(d.ON.sum()), int(off.max_spec.notna().sum()), int(off.max_spec.isna().sum())]
    ax = axes[0]
    bars = ax.barh(labels[::-1], vals[::-1], color=[GREY, TAUPE, SAGE][::-1], height=0.6)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 1.0, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=10)
    ax.set_xlim(0, 62)
    ax.set_xlabel("genes (of 98)", fontsize=9)
    ax.set_title("A. Fate of Dan's 98 genes vs the current panel", fontsize=10.5)
    ax.tick_params(axis="y", labelsize=8.5)

    a14 = d[d.gene.isin(ADDED14)].sort_values("max_spec", ascending=False)
    best = off.nlargest(4, "max_spec")
    ax = axes[1]
    ya = np.arange(len(a14))[::-1]
    ax.barh(ya, a14.max_spec, color=NAVY, height=0.62, label="added earlier (14)")
    yb = np.arange(len(best)) - len(best) - 0.6
    ax.barh(yb, best.max_spec, color=RUST, height=0.62, label="best NOT added (4)")
    ax.set_yticks(list(ya) + list(yb))
    ax.set_yticklabels(list(a14.gene) + list(best.gene), fontsize=8.2)
    ax.axvline(1.0, color="#333", lw=1.2, ls=(0, (4, 3)))
    # Label sits above the tallest bar; the "what it means" sentence is on the slide.
    ax.text(1.0, ya.max() + 0.95, "  spec = 1.0", fontsize=8, color="#333",
            va="bottom", ha="left")
    # Rule goes in the gap between the two groups, not through the legend.
    ax.axhline((yb.max() + ya.min()) / 2, color="#8A8A8A", lw=0.9)
    ax.set_ylim(yb.min() - 0.8, ya.max() + 1.6)
    ax.set_xlabel("max specificity vs the panel (Allen WMB-10X)", fontsize=9)
    ax.set_title("B. Specificity overlap: the earlier 14 vs the best 4 left out", fontsize=10.5)
    ax.legend(fontsize=8, loc="lower right", frameon=False)

    fig.suptitle(PROV.split("  |  ")[1], fontsize=9, color="#555", y=1.01)
    fig.tight_layout()
    return save(fig, "v2_Fig2_dan.png")


# ------------------------------------------------------------------ deck
def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)


def set_run(p, text, size=18, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Calibri"
    return r


def new_slide(prs, title, sub, n, total=4):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(NAVY)
    bar.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.28), Inches(12.3), Inches(0.55))
    tb.text_frame.word_wrap = True
    set_run(tb.text_frame.paragraphs[0], title, 28, True, rgb(NAVY))
    if sub:
        sb = s.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(12.3), Inches(0.4))
        sb.text_frame.word_wrap = True
        set_run(sb.text_frame.paragraphs[0], sub, 14, False, MUTED)
    fb = s.shapes.add_textbox(Inches(0.5), Inches(7.18), Inches(12.3), Inches(0.28))
    set_run(fb.text_frame.paragraphs[0],
            f"ORBm + BMAp Xenium add-on  |  Jesse Niehaus  +  Daniel Berg / Scherrer  |  {n}/{total}",
            10, False, MUTED)
    return s


def picture(slide, path, top, max_h, max_w=12.45):
    """Place a figure capped at max_h/max_w, centred, and return its bottom edge.

    Sizing by width alone let slide 1's figure run to 6.88in and sit under its own
    caption, so height is the binding constraint here and the caller lays text out
    from the returned bottom.
    """
    pic = slide.shapes.add_picture(str(path), Inches(0), Inches(top), height=Inches(max_h))
    if pic.width > Inches(max_w):
        scale = Inches(max_w) / pic.width
        pic.width, pic.height = int(pic.width * scale), int(pic.height * scale)
    pic.left = int((Inches(13.333) - pic.width) / 2)
    return pic.top / 914400 + pic.height / 914400


def lines(slide, items, left, top, width, height, size=13, colour=INK):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, t, size, False, colour)
        p.space_after = Pt(6)
    return box


def table(slide, df, x, y, w, col_w, size=10.5, row_h=0.34, head=NAVY):
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
            c.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 == 0 else RGBColor(0xF2, 0xF0, 0xEC)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(size), "Calibri"
                    r.font.color.rgb = INK
    return shp


def build(rank, dan, figs) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    panel = set(pd.read_excel(PANEL_V1, "SHARED_PANEL_ORDER").gene.astype(str))
    d = dan.copy()
    d["ON"] = d.gene.isin(panel)
    off = d[~d.ON]

    # 1 Jesse
    s = new_slide(prs, "Jesse  |  which morphine genes are worth a slot",
                  "Ranked by how many of the 12 ORBm anchor cell types we image actually show DE, "
                  "not by Jesse's raw cluster count.", 1)
    bottom = picture(s, figs["jesse"], 1.30, 4.20)
    lines(s, [
        "304 unique DEGs across four lists (IEG 77, TF 179, synaptic plasticity 45, GPCR 34) plus 127 ORB-enriched GPCRs. "
        "Only 30 of the DEGs are already on our panel.",
        "The two broadest genes in the whole dataset - Per2 (11/12) and Pcsk1 (9/12) - were both missing. "
        "Our existing IEGs (Egr1, Arc, Fos, Junb) start at 8/12, so the activity core was fine but the top of the list was not.",
        "Why 11 and not 12: Lamp5 Gaba carries no DEG at all in this dataset, so 11 is the ceiling - Per2 changes in every ORBm "
        "cell type where anything changes. Re-counting on our 12 anchors drops Jesse's raw numbers by 0.13 clusters on average; "
        "the only gene it demotes out of contention is Nr4a3 (8 raw, 5 here).",
    ], 0.5, bottom + 0.10, 12.4, 1.35, size=11.5)
    return _rest(prs, s, rank, d, off, figs)


def _rest(prs, _s, rank, d, off, figs) -> Path:
    # 2 Dan
    s = new_slide(prs, "Dan  |  re-checked, nothing further to add",
                  "All 98 genes re-scored against the current 158-gene panel.", 2)
    bottom = picture(s, figs["dan"], 1.30, 4.30)
    lines(s, [
        f"{int(d.ON.sum())} of 98 are already on the panel. The best of the {len(off)} left off scores "
        f"max_spec {off.max_spec.max():.2f} - below 1.0, so none of them beats a gene the panel already carries for that anchor.",
        "Honest caveat: the 14 added earlier span max_spec 0.53-3.69, so Nos1 (0.76), Oprl1 (0.57) and Dnah5 (0.53) sit BELOW "
        "Sfrp1 (0.89), Glipr1 (0.88) and Vdr (0.87), which were left out. Those three went in on pharmacology, not specificity "
        "(Oprl1 = nociceptin receptor, Nos1 = interneuron marker).",
        "Glipr1 (0.88) looked like the one borderline case because it serves anchor 113 MEA-COA-BMA Ccdc42, the true BMAp core. "
        "But that anchor already carries Penk (2.31) and Lamb3 (1.51) on the panel, so Glipr1 would be a third, weaker probe for "
        "a cell type that is already resolved. Recommendation: add nothing from Dan.",
    ], 0.5, bottom + 0.12, 12.4, 1.05, size=11.5)

    # 3 selection rule
    s = new_slide(prs, "How the genes were selected", "One rule for Jesse, one for Dan, and a slot budget.", 3)
    rule = pd.DataFrame([
        ["Jesse (ORBm)", "DE breadth across the 12 ORBm anchor cell types",
         "8+ anchors = core add; free-on-base at any breadth = add (no slot cost)",
         "5 custom + 4 free"],
        ["Dan (BMAp)", "max specificity vs the panel in Allen WMB-10X (max_spec)",
         "max_spec > 1.0 = beats an existing panel gene. Best remaining is 0.89",
         "0 (nothing added)"],
    ], columns=["Source", "Metric", "Threshold applied", "Result"])
    table(s, rule, 0.5, 1.45, 12.35, col_w=[1.7, 3.7, 5.15, 1.8], size=11, row_h=0.52)

    budget = pd.DataFrame([
        ["Curated core (blocks 1-11)", "144", "100 custom + 44 free", "unchanged"],
        ["Dan GSE283418 (block 12)", "14", "14 custom", "unchanged"],
        ["Jesse morphine state (block 13, NEW)", "9", "5 custom + 4 free", "this round"],
        ["Total", "167", "119 custom + 48 free", "+9 genes / +5 slots"],
    ], columns=["Panel block", "Genes", "Slots", "Change"])
    table(s, budget, 0.5, 3.6, 12.35, col_w=[5.4, 1.4, 3.35, 2.2], size=11, row_h=0.42)
    lines(s, [
        "Custom count rises 114 -> 119. The original cap was 100 custom add-on slots, so 119 needs vendor confirmation "
        "before ordering - this is the one open item.",
        "These 9 genes report morphine-dependence state, not cell identity, so ANCHOR_COVERAGE is untouched and all 20 "
        "cell types remain separable.",
    ], 0.5, 5.65, 12.35, 1.3, size=12)

    # 4 final
    s = new_slide(prs, "FINAL  |  9 genes added to the panel",
                  "Appended as block 13_Jesse_morphine_state. No existing gene removed or re-ranked.", 4)
    rows = []
    for gene, n, direction, free, why in FINAL_ADD:
        r = rank[rank.gene == gene]
        gg = f"{int(r.n_glut.iloc[0])} / {int(r.n_gaba.iloc[0])}" if len(r) else "-"
        rows.append({
            "Gene": gene,
            "ORBm anchors": f"{n} / 12",
            "Glut / GABA": gg,
            "Direction": direction,
            "Slot cost": "free (base)" if free else "1 custom",
            "Why it earns a place": why,
        })
    table(s, pd.DataFrame(rows), 0.5, 1.45, 12.35,
          col_w=[1.0, 1.25, 1.15, 1.0, 1.35, 6.6], size=10.5, row_h=0.42)

    lines(s, [
        "New question the panel can now answer: within one L5 IT cell, is the morphine-dependence signature ON or OFF? "
        "Cell typing and TRAP comparison worked before; morphine state did not.",
        "Order sheet: FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v2_167genes.xlsx  -  formatting, column widths, frozen panes and "
        "every existing row are byte-identical to MSGS111; rows were only appended.",
        "Open for decision: (1) approve 119 custom slots - the original cap was 100, so this needs vendor confirmation, "
        "(2) keep Camk2g as the DOWN control. Nothing from Dan is proposed.",
    ], 0.5, 5.85, 12.35, 1.25, size=12)

    prs.save(DECK)
    return DECK


def main() -> None:
    rank = pd.read_excel(RANK, "ranking_all")
    dan = pd.read_excel(DAN, "all_98_genes")
    figs = {"jesse": fig_jesse(rank), "dan": fig_dan(dan)}
    deck = build(rank, dan, figs)
    for k, v in figs.items():
        print(f"fig {k:6s} -> {v}")
    print(f"deck       -> {deck}")


if __name__ == "__main__":
    main()
