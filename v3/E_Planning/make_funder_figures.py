"""Three figures for the funder deck, in the same palette as the v3 deck."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "outputs"
FIG = OUT / "funder_figs"
FIG.mkdir(exist_ok=True)
SRC = OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx"

NAVY, BLUE, RED, GREEN = "#1D4E89", "#2A6F97", "#C44536", "#6B7C6A"
GREY, DARK, CREAM = "#5B6472", "#1F2937", "#F4F1EA"
plt.rcParams.update({"font.family": "Calibri", "font.size": 10})

d = pd.read_excel(SRC, None)
m = d["PANEL_ORDER"]
ac = d["ANCHOR_COVERAGE_20types"]
cov = d["SUBTYPE_COVERAGE"]


def card(ax, x, y, w, h, edge, fill="white", lw=1.6, r=0.035):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fill, ec=edge, lw=lw, zorder=2))


# ------------------------------------------------------------------ 1. workflow
fig, ax = plt.subplots(figsize=(12.6, 5.28))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

STAGES = [
    (NAVY, "SOURCES", [
        ("Allen WMB-10X atlas", "32,245 genes x 226,886 cells\nfrom ORBm and BMAp"),
        ("Jesse Niehaus", "5-day escalating morphine\nDESeq2, PL-ILA-ORB"),
        ("Dan Berg GSE283418", "amygdala spatial panel"),
        ("Literature + IUPHAR", "canonical markers,\ndruggable receptors")]),
    (BLUE, "RESTRICT TO THE TARGET", [
        ("20 cell populations", "12 in ORBm, 8 in BMAp\n124,115 cells"),
        ("86 sub-populations", "Allen supertypes inside\nthose 20"),
        ("Scored in-region only", "not a whole-brain average")]),
    (GREEN, "MEASURE EVERY GENE TWICE", [
        ("Can it SEPARATE?", "gap in % positive vs the\nneighbouring populations"),
        ("Is it DETECTED?", "% of cells carrying it\nin its best population"),
        ("Judged by its job", "identity genes need the 1st,\nstate genes need the 2nd")]),
    (RED, "APPLY CAPS, SET IN ADVANCE", [
        ("<= 4 markers", "per cell population"),
        ("2 or 1 markers", "per sub-population,\nby its size"),
        ("1 gene per mechanism", "no paralogue pairs"),
        ("Drop no-contrast genes", "~100% everywhere with\n<12pp separation")]),
]
X0, W, GAPX = 1.2, 18.6, 2.0
for si, (col, head, items) in enumerate(STAGES):
    x = X0 + si * (W + GAPX)
    ax.text(x + W / 2, 95.5, head, ha="center", va="center", fontsize=11,
            color=col, fontweight="bold")
    y = 88
    for t, sub in items:
        h = 9.4 + 3.4 * sub.count("\n")
        y -= h + 1.8
        card(ax, x, y, W, h, col, fill="white")
        ax.text(x + 1.0, y + h - 2.3, t, fontsize=9.8, color=col, fontweight="bold",
                va="top")
        ax.text(x + 1.0, y + h - 5.3, sub, fontsize=8.3, color=GREY, va="top")
    if si < len(STAGES) - 1:
        ax.add_patch(FancyArrowPatch((x + W + 0.3, 52), (x + W + GAPX - 0.3, 52),
                                     arrowstyle="-|>", mutation_scale=16,
                                     color="#9AA5B1", lw=1.7))

xr, WR = X0 + 4 * (W + GAPX), 15.0
card(ax, xr, 12, WR, 80, NAVY, fill=CREAM, lw=2.2)
cx = xr + WR / 2
ax.text(cx, 86, "FINAL PANEL", ha="center", fontsize=10.5, color=NAVY,
        fontweight="bold")
ax.text(cx, 75, "259", ha="center", fontsize=33, color=NAVY, fontweight="bold")
ax.text(cx, 68.5, "genes", ha="center", fontsize=10, color=GREY)
for i, (n, lab) in enumerate([("20 / 20", "populations called\n(held-out recall)"),
                              ("86 / 86", "sub-populations\nresolved"),
                              ("10", "probes with no\ncontrast, down from 28")]):
    yy = 58 - i * 16
    ax.text(cx, yy, n, ha="center", fontsize=14.5, color=BLUE, fontweight="bold")
    ax.text(cx, yy - 4.6, lab, ha="center", fontsize=8.2, color=GREY, va="top")

ax.text(50, 6.5, "Nothing is included because a document names it. Every gene on the "
                 "panel has a measured number attached to a stated job.",
        ha="center", fontsize=10.5, color=DARK, style="italic")
fig.savefig(FIG / "s1_workflow.png", dpi=190, bbox_inches="tight",
            facecolor="white", pad_inches=0.08)
plt.close(fig)

# --------------------------------------------------- 2. what the panel is made of
CAT = {"01_TRAP_reporter": "TRAP reporter",
       "03_class_EI_backbone": "Cell class (E / I)",
       "03b_taxonomy_backbone": "Cell type marker",
       "04_nonneuronal_counterstain": "Non-neuronal",
       "05_celltype_separator": "Cell type marker",
       "05b_pairwise_disambiguator": "Cell type marker",
       "06_subtype_separator": "Sub-type marker",
       "07_IEG_pCREB_target": "Activity (IEG)",
       "08_clock_module": "Circadian",
       "09_plasticity": "Synaptic plasticity",
       "10_morphine_state": "Morphine state",
       "11_GPCR_map": "GPCR"}
COL = {"Cell type marker": NAVY, "Sub-type marker": BLUE, "Cell class (E / I)": NAVY,
       "Non-neuronal": GREY, "GPCR": RED, "Activity (IEG)": GREEN,
       "TRAP reporter": GREEN, "Synaptic plasticity": GREEN, "Circadian": RED,
       "Morphine state": RED}
s = m.assign(cat=m.block.map(CAT)).groupby("cat").gene.count().sort_values()

fig, ax = plt.subplots(figsize=(7.05, 3.28))
b = ax.barh(s.index, s.values, color=[COL[c] for c in s.index], height=0.72)
ax.bar_label(b, padding=3, fontsize=10, color=DARK, fontweight="bold")
ax.set_xlim(0, max(s.values) * 1.16)
ax.set_xlabel("genes on the panel", fontsize=9.5, color=GREY)
ax.tick_params(labelsize=9.5, colors=GREY, length=0)
for sp in ("top", "right", "left", "bottom"):
    ax.spines[sp].set_visible(False)
ax.grid(axis="x", color="#E5E7EB", lw=0.8)
ax.set_axisbelow(True)
ax.set_title("259 genes, by the job each one does", fontsize=11.5, color=NAVY,
             fontweight="bold", loc="left", pad=8)
fig.tight_layout()
fig.savefig(FIG / "s3_categories.png", dpi=190, facecolor="white")
plt.close(fig)

# ------------------------------------------------------- 3. the 20 populations
a = ac.copy()
nsub = cov.groupby("parent_anchor").supertype.nunique()
a["n_sep"] = a[["n_unique_vs_all19", "n_vs_closest_neighbour"]].max(axis=1)
a["n_sub"] = a.allen_subclass_anchor.map(nsub).fillna(0).astype(int)
a = a.sort_values(["region", "n_sep"], ascending=[True, True])
y = np.arange(len(a))

fig, ax = plt.subplots(figsize=(11.1, 4.55))
cols = [RED if r == "BMAp" else NAVY for r in a.region]
b1 = ax.barh(y, a.n_sep, color=cols, height=0.62, label="separators on the panel")
b2 = ax.barh(y, a.n_sub, left=a.n_sep, color="#BFD3E6", height=0.62,
             label="sub-populations resolved inside it")
ax.bar_label(b1, labels=[f"{v}" for v in a.n_sep], label_type="center",
             fontsize=8.5, color="white", fontweight="bold")
ax.bar_label(b2, labels=[f"{v} sub" if v else "" for v in a.n_sub], padding=3,
             fontsize=8.5, color=GREY)
ax.set_yticks(y)
ax.set_yticklabels([f"{r.allen_subclass_anchor}   ({r.n_cells:,} cells)"
                    for r in a.itertuples()], fontsize=8.8)
ax.tick_params(colors=GREY, length=0)
for t, r in zip(ax.get_yticklabels(), a.region):
    t.set_color(RED if r == "BMAp" else NAVY)
ax.set_xlabel("separators on the panel that address this population", fontsize=9.5,
              color=GREY)
ax.set_xlim(0, (a.n_sep + a.n_sub).max() * 1.12)
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color("#D6D3CC")
ax.grid(axis="x", color="#EEF0F2", lw=0.8)
ax.set_axisbelow(True)
h, l = ax.get_legend_handles_labels()
h += [plt.Line2D([], [], color=NAVY, lw=6), plt.Line2D([], [], color=RED, lw=6)]
l += ["ORBm population", "BMAp population"]
ax.legend(h, l, loc="lower right", fontsize=8.8, frameon=False)
ax.set_title("All 20 target populations have separators; most are split further "
             "into sub-populations",
             fontsize=11, color=NAVY, fontweight="bold", loc="left", pad=8)
fig.tight_layout()
fig.savefig(FIG / "s4_populations.png", dpi=190, facecolor="white")
plt.close(fig)

print("wrote 3 figures to", FIG)
for f in sorted(FIG.glob("*.png")):
    print(" ", f.name)
