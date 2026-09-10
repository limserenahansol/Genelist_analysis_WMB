"""English 4-slide deck combining r3's argument with readable data figures.

Slide 1  Jesse DEGs on OUR 12 ORBm anchors (r3 metric, fixed typography)
Slide 2  Jesse ORB GPCRs vs Allen absolute % (the missing half of Jesse)
Slide 3  Dan 98-gene re-check (r3 specificity rule)
Slide 4  Final add list (best of both)

Figures use DejaVu Sans only so titles keep their spaces.
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
FIG = OUT / "combined_decision_figures"
FIG.mkdir(exist_ok=True)
DL = Path.home() / "Downloads"

RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"
ALLEN = OUT / "jesse_allen_gpcr_abundance" / "Jesse_GPCR_Allen_ORBm_summary.csv"
PANEL = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"

NAVY, TEAL, RUST, GOLD, SAGE, GREY = (
    "#1D4E89",
    "#2A6F97",
    "#C44536",
    "#B08968",
    "#6B7C6A",
    "#B8B2A8",
)
ADDED14 = [
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

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.sans-serif": ["DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def save(fig, name: str) -> Path:
    p = FIG / name
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def fig_jesse_degs(rank: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.35), gridspec_kw={"width_ratios": [1.3, 1]})
    top = rank.nlargest(14, ["n_orbm", "n_DE_clusters"]).iloc[::-1]
    cols = {"already on panel": SAGE, "FREE on base": TEAL, "1 custom slot": RUST}
    ax = axes[0]
    y = np.arange(len(top))
    ax.barh(y, top.n_orbm, color=[cols[c] for c in top.slot_cost], height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(list(top.gene), fontsize=9)
    for i, (n, d) in enumerate(zip(top.n_orbm, top.direction)):
        ax.text(n + 0.15, i, f"{int(n)}  {d}", va="center", fontsize=8, color="#444")
    ax.set_xlim(0, 14)
    ax.set_xlabel("ORBm anchors with DE  (of 12)")
    ax.set_title("A.  Broadest morphine DEGs in our 12 ORBm cell types")
    present = [k for k in cols if (top.slot_cost == k).any()]
    ax.legend(
        [plt.Rectangle((0, 0), 1, 1, color=cols[k]) for k in present],
        present,
        fontsize=8,
        loc="lower right",
        frameon=False,
    )

    picks = ["Per2", "Pcsk1", "Per1", "Arid5b", "Camk2g", "Bhlhe40", "Sema3e"]
    sub = rank[rank.gene.isin(picks)].set_index("gene")
    sub = sub.reindex([g for g in picks if g in sub.index]).iloc[::-1]
    ax = axes[1]
    y = np.arange(len(sub))
    ax.barh(y + 0.18, sub.n_glut, height=0.34, color=NAVY, label="Glut  (of 8)")
    ax.barh(y - 0.18, sub.n_gaba, height=0.34, color=GOLD, label="GABA  (of 4)")
    ax.set_yticks(y)
    ax.set_yticklabels(list(sub.index), fontsize=9)
    ax.set_xlabel("ORBm anchors with DE")
    ax.set_title("B.  Do they change in both classes?")
    ax.legend(fontsize=8, loc="lower right", frameon=False)

    fig.suptitle(
        "Jesse Niehaus  |  5-day morphine  |  DESeq2  |  recounted on our 12 ORBm anchors",
        fontsize=9,
        color="#555",
        y=1.02,
    )
    fig.tight_layout()
    return save(fig, "C_Fig1_jesse_DEGs.png")


def fig_jesse_gpcrs(allen: pd.DataFrame) -> Path:
    """Jesse relative rank vs Allen absolute % — why Chrm1/Grm8 beat Mas1."""
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.35))

    # Jesse glut enrichment ranks (from conversation / CSVs)
    j = pd.DataFrame(
        {
            "gene": ["Mas1", "Rxfp1", "Gpr68", "Mchr1", "Grm8", "Cckbr", "Chrm1", "Gpr26", "Hcrtr2"],
            "n_glut": [17, 15, 11, 10, 9, 8, 8, 8, 4],
            "on_panel": [False, False, False, False, False, True, False, False, True],
        }
    )
    j = j.sort_values("n_glut")
    ax = axes[0]
    y = np.arange(len(j))
    colors = [SAGE if on else RUST for on in j.on_panel]
    colors = [TEAL if g == "Rxfp1" else c for g, c in zip(j.gene, colors)]
    ax.barh(y, j.n_glut, color=colors, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(list(j.gene), fontsize=9)
    ax.set_xlabel("PL-ILA-ORB glut subclasses enriched  (Jesse)")
    ax.set_title("A.  Jesse: which GPCRs live in ORB  (relative)")
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color=SAGE, label="already on panel"),
            plt.Rectangle((0, 0), 1, 1, color=TEAL, label="Rxfp1  free on base"),
            plt.Rectangle((0, 0), 1, 1, color=RUST, label="not on panel"),
        ],
        fontsize=8,
        loc="lower right",
        frameon=False,
    )

    a = allen.set_index("gene")
    order = ["Chrm1", "Grm8", "Gpr26", "Cckbr", "Hcrtr2", "Mas1", "Rxfp1", "Gpr68", "Mchr1"]
    order = [g for g in order if g in a.index]
    ax = axes[1]
    y = np.arange(len(order))
    vals = [float(a.loc[g, "max_pct"]) for g in order]
    cols = []
    for g in order:
        if g in ("Cckbr", "Hcrtr2"):
            cols.append(SAGE)
        elif g == "Rxfp1":
            cols.append(TEAL)
        elif g in ("Chrm1", "Grm8"):
            cols.append(RUST)
        else:
            cols.append(GREY)
    ax.barh(y, vals, color=cols, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=9)
    ax.axvline(50, color="#333", lw=1, ls=(0, (4, 3)))
    ax.text(51, len(order) - 0.7, "50%", fontsize=8, color="#333")
    ax.set_xlim(0, 110)
    ax.set_xlabel("Allen ORBm  max % expressing  (12 anchors)")
    ax.set_title("B.  Allen: will Xenium actually see it?  (absolute)")
    for i, v in enumerate(vals):
        ax.text(v + 1.5, i, f"{v:.0f}%", va="center", fontsize=8, color="#444")

    fig.suptitle(
        "Relative enrichment is not the same as abundance.  106,122 Allen ORBm cells.",
        fontsize=9,
        color="#555",
        y=1.02,
    )
    fig.tight_layout()
    return save(fig, "C_Fig2_jesse_GPCRs_Allen.png")


def fig_dan(dan: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.2), gridspec_kw={"width_ratios": [1, 1.15]})
    panel = set(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str))
    d = dan.copy()
    d["ON"] = d.gene.isin(panel)
    off = d[~d.ON]
    labels = [
        "Already on panel\n(includes the 14 added earlier)",
        "Off panel,\nmax spec below 0.9",
        "Off panel,\nnot scored in Allen",
    ]
    vals = [int(d.ON.sum()), int(off.max_spec.notna().sum()), int(off.max_spec.isna().sum())]
    ax = axes[0]
    bars = ax.barh(labels[::-1], vals[::-1], color=[GREY, GOLD, SAGE][::-1], height=0.58)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 1.0, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=10)
    ax.set_xlim(0, 68)
    ax.set_xlabel("genes  (of 98)")
    ax.set_title("A.  Fate of Dan's 98 genes vs the current panel")
    ax.tick_params(axis="y", labelsize=8)

    a14 = d[d.gene.isin(ADDED14)].sort_values("max_spec", ascending=False)
    best = off.nlargest(4, "max_spec")
    ax = axes[1]
    ya = np.arange(len(a14))[::-1]
    ax.barh(ya, a14.max_spec, color=NAVY, height=0.62, label="added earlier (14)")
    yb = np.arange(len(best)) - len(best) - 0.55
    ax.barh(yb, best.max_spec, color=RUST, height=0.62, label="best not added (4)")
    ax.set_yticks(list(ya) + list(yb))
    ax.set_yticklabels(list(a14.gene) + list(best.gene), fontsize=8)
    ax.axvline(1.0, color="#333", lw=1.2, ls=(0, (4, 3)))
    ax.text(1.05, float(ya.max()) + 0.7, "spec = 1.0", fontsize=8, color="#333")
    ax.axhline((float(yb.max()) + float(ya.min())) / 2, color="#888", lw=0.8)
    ax.set_xlabel("max specificity vs the panel  (Allen BMAp)")
    ax.set_title("B.  Earlier 14 vs the best genes left out")
    ax.legend(fontsize=8, loc="lower right", frameon=False)

    fig.suptitle(
        "Daniel Berg / Scherrer  |  GSE283418  |  98-gene Resolve smFISH  |  re-scored in Allen BMAp",
        fontsize=9,
        color="#555",
        y=1.02,
    )
    fig.tight_layout()
    return save(fig, "C_Fig3_dan.png")


# ----- PPT -----
INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x5B, 0x64, 0x72)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = RGBColor(0xF4, 0xF1, 0xEA)
NAVY_R = RGBColor(0x1D, 0x4E, 0x89)
RUST_R = RGBColor(0xC4, 0x45, 0x36)
TEAL_R = RGBColor(0x2A, 0x6F, 0x97)


def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def set_run(p, text, size=16, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Calibri"
    return r


def new_slide(prs, title, sub, n, bar=NAVY):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.1))
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb(bar)
    sh.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.4), Inches(0.18), Inches(12.5), Inches(0.4))
    set_run(tb.text_frame.paragraphs[0], title, 24, True, rgb(bar))
    sb = s.shapes.add_textbox(Inches(0.4), Inches(0.56), Inches(12.5), Inches(0.32))
    set_run(sb.text_frame.paragraphs[0], sub, 13, False, MUTED)
    fb = s.shapes.add_textbox(Inches(0.4), Inches(7.18), Inches(12.5), Inches(0.26))
    set_run(
        fb.text_frame.paragraphs[0],
        f"ORBm + BMAp Xenium  |  Jesse Niehaus  +  Daniel Berg / Scherrer  +  Allen WMB-10X  |  {n}/4",
        11,
        False,
        MUTED,
    )
    return s


def add_table(slide, rows, left, top, width, height, col_w, header=NAVY_R):
    table = slide.shapes.add_table(
        len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(height)
    ).table
    for i, w in enumerate(col_w):
        table.columns[i].width = Inches(w)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            set_run(cell.text_frame.paragraphs[0], str(val), 12, i == 0, WHITE if i == 0 else INK)
            cell.text_frame.word_wrap = True
            cell.fill.solid()
            cell.fill.fore_color.rgb = header if i == 0 else (WHITE if i % 2 == 0 else PALE)


def main() -> None:
    rank = pd.read_excel(RANK, "ranking_all")
    dan = pd.read_excel(DAN, "all_98_genes")
    allen = pd.read_csv(ALLEN)

    p1 = fig_jesse_degs(rank)
    p2 = fig_jesse_gpcrs(allen)
    p3 = fig_dan(dan)
    print("figs", p1.name, p2.name, p3.name)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    s = new_slide(
        prs,
        "Jesse  |  how the morphine DEGs look",
        "Recounted on the 12 ORBm cell types we image, not Jesse's raw PL-ILA-ORB cluster count.  Lamp5 has no DEG, so 11/12 is the ceiling.",
        1,
    )
    s.shapes.add_picture(str(p1), Inches(0.35), Inches(0.95), Inches(12.6), Inches(5.0))
    cap = s.shapes.add_textbox(Inches(0.4), Inches(6.05), Inches(12.5), Inches(1.0))
    tf = cap.text_frame
    tf.word_wrap = True
    set_run(
        tf.paragraphs[0],
        "Per2 (11/12) and Pcsk1 (9/12) are the broadest genes in the whole dataset and were both missing.  "
        "Fos / Arc / Egr1 / Junb start at 8/12 — the activity core is already on the 144.",
        14,
        False,
        INK,
    )
    p = tf.add_paragraph()
    set_run(
        p,
        "Considered from this figure:  Per2, Pcsk1, Per1  (clock / peptide program).  "
        "Arid5b is equally broad (8/12) but is a chromatin TF — a weaker use of a custom slot.  "
        "Camk2g is the strongest Down gene (6/12 glut only).",
        14,
        False,
        INK,
    )

    s = new_slide(
        prs,
        "Jesse  |  how the ORB GPCRs look  —  relative vs absolute",
        "Left: Jesse's enrichment vs the rest of the atlas.  Right: % expressing in 106,122 Allen ORBm cells.  These are different questions.",
        2,
    )
    s.shapes.add_picture(str(p2), Inches(0.35), Inches(0.95), Inches(12.6), Inches(5.05))
    cap = s.shapes.add_textbox(Inches(0.4), Inches(6.08), Inches(12.5), Inches(1.0))
    tf = cap.text_frame
    tf.word_wrap = True
    set_run(
        tf.paragraphs[0],
        "Cckbr and Hcrtr2 are already on the panel and are abundant.  Rxfp1 is Jesse's #2 and free on the Xenium base panel (Allen 34%).",
        14,
        False,
        INK,
    )
    p = tf.add_paragraph()
    set_run(
        p,
        "Mas1 is Jesse's #1 by enrichment, but only 45% in L5 ET and ~1% in GABA.  "
        "Chrm1 (92%) and Grm8 (99%) were never in our 40-GPCR pull — they are the genes Xenium will actually see.",
        14,
        False,
        INK,
    )

    s = new_slide(
        prs,
        "Dan  |  how the 98-gene spatial panel looks",
        "GSE283418 Resolve smFISH.  52/98 already on the 158-gene sheet.  Rule: add only if max_spec > 1.0 (beats a gene we already carry).",
        3,
        bar=TEAL,
    )
    s.shapes.add_picture(str(p3), Inches(0.35), Inches(0.95), Inches(12.6), Inches(4.95))
    cap = s.shapes.add_textbox(Inches(0.4), Inches(6.02), Inches(12.5), Inches(1.05))
    tf = cap.text_frame
    tf.word_wrap = True
    set_run(
        tf.paragraphs[0],
        "Nothing further from Dan.  Best leftover is Sfrp1 at spec 0.89.  "
        "Honest caveat: Nos1 (0.76), Oprl1 (0.57) and Dnah5 (0.53) already on the sheet sit below Sfrp1 / Glipr1 / Vdr.  "
        "Those three were kept for pharmacology, not specificity.",
        14,
        False,
        INK,
    )
    p = tf.add_paragraph()
    set_run(
        p,
        "Glipr1 (0.88) marks true BMAp (113 Ccdc42), but that anchor already has Penk (2.31) and Lamb3 (1.51).  Do not add a third, weaker probe.",
        14,
        False,
        INK,
    )

    s = new_slide(
        prs,
        "Final decision  |  genes added to the panel",
        "Jesse DEGs ranked on our 12 anchors  +  Jesse GPCRs filtered by Allen abundance  +  Dan stopped at the 14 already on MSGS111.",
        4,
        bar="#C44536",
    )
    add_table(
        s,
        [
            ["Decision", "Genes", "Why  (from the figures)", "Slots"],
            [
                "Already on sheet",
                "Dan 14   +   Fos Arc Egr1  Cckbr Hcrtr2",
                "Cell-type 144 and Dan extras stay.  No Dan gene added this round.",
                "done",
            ],
            [
                "ADD  now",
                "Per2    Pcsk1    Per1",
                "Slide 1: broadest missing IEGs (11 / 9 / 8 of 12).  Morphine-state clock / peptide program.",
                "3 custom",
            ],
            [
                "ADD  now",
                "Chrm1    Grm8    Rxfp1",
                "Slide 2: ORB GPCRs that Allen actually sees (92% / 99% / free 34%).  Chrm2 and Grm5 are already on.",
                "2 + 0",
            ],
            [
                "Optional",
                "Camk2g",
                "Slide 1: strongest Down gene, 93% abundant.  Add only if you want a direction control.",
                "1 custom",
            ],
            [
                "Free extras",
                "Sema3e    Bhlhe40",
                "On the Xenium base panel.  Cheap to curate.  Not required for the argument.",
                "0",
            ],
            [
                "Do not add",
                "Arid5b   Gadd45a   Mas1   Mchr1   more Dan",
                "TF / 1-anchor / low Allen % / spec < 1.0.  Spend the slot on Chrm1/Grm8 instead of Arid5b.",
                "—",
            ],
        ],
        0.35,
        1.0,
        12.6,
        5.15,
        [2.0, 3.15, 6.25, 1.2],
        header=RUST_R,
    )
    box = s.shapes.add_textbox(Inches(0.4), Inches(6.25), Inches(12.5), Inches(0.8))
    tf = box.text_frame
    tf.word_wrap = True
    set_run(
        tf.paragraphs[0],
        "Final new add:    Per2   Pcsk1   Per1    +    Chrm1   Grm8    +    Rxfp1 (free)",
        18,
        True,
        RUST_R,
    )
    p = tf.add_paragraph()
    set_run(
        p,
        "Five custom slots on top of Dan 14  →  119 if every Dan gene is kept.  Original cap is 100 — confirm with 10x, or drop CEA-border Dan genes first.",
        13,
        False,
        INK,
    )

    ppt = OUT / "ORBm_BMAp_panel_decision_combined_EN.pptx"
    prs.save(ppt)
    print("PPT", ppt, ppt.stat().st_size)
    for dest in (
        DL / "ORBm_BMAp_panel_decision_combined_EN.pptx",
        DL / "Add_genes_Dan_Jesse_final_EN.pptx",
    ):
        try:
            prs.save(dest)
            print("also", dest.name)
        except OSError as e:
            print("skip", dest.name, type(e).__name__)


if __name__ == "__main__":
    main()
