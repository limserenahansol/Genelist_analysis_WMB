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

STEPS = [
    (NAVY, "1", "Start with the data", [
        "Allen atlas of these two regions",
        "   226,886 cells in ORBm + BMAp",
        "Jesse: 5-day morphine in cortex",
        "Dan: amygdala spatial panel",
    ]),
    (BLUE, "2", "Ask one question per gene", [
        "Does it name one of the 20",
        "   cell types in these regions?",
        "Or does it report morphine,",
        "   circadian, or receptor state?",
    ]),
    (RED, "3", "Drop genes that cannot help", [
        "On in every cell (no contrast)",
        "Too rare for the instrument",
        "   to make a usable map",
        "Same job as a gene already kept",
    ]),
    (GREEN, "4", "Keep only what earned a slot", [
        "259 genes on one shared panel",
        "All 20 cell types can be named",
        "Sub-types inside them too",
        "Read from the same mouse",
    ]),
]
X0, W, GAP = 1.4, 21.6, 2.4
for i, (col, num, head, lines) in enumerate(STEPS):
    x = X0 + i * (W + GAP)
    card(ax, x, 12, W, 78, col, fill="white", lw=1.8)
    circ = plt.Circle((x + 2.4, 82.6), 1.7, fc=col, ec="none", zorder=3)
    ax.add_patch(circ)
    ax.text(x + 2.4, 82.6, num, ha="center", va="center", fontsize=12,
            color="white", fontweight="bold", zorder=4)
    ax.text(x + 4.8, 82.6, head, ha="left", va="center", fontsize=12.2,
            color=col, fontweight="bold")
    yy = 70
    for ln in lines:
        ax.text(x + 1.4, yy, ln, ha="left", va="top", fontsize=11,
                color=DARK if not ln.startswith("   ") else GREY)
        yy -= 11.5
    if i < 3:
        ax.add_patch(FancyArrowPatch((x + W + 0.25, 51), (x + W + GAP - 0.25, 51),
                                     arrowstyle="-|>", mutation_scale=18,
                                     color="#9AA5B1", lw=1.8))

ax.text(50, 5.5, "Read left to right: data  →  question  →  drop  →  the 259-gene list.",
        ha="center", fontsize=12, color=NAVY, fontweight="bold")
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
