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
    (NAVY, "1", "The data", [
        "Allen atlas of ORBm + BMAp",
        "(226,886 cells in these",
        "two regions only)",
        "",
        "Jesse: 5-day morphine",
        "in orbitofrontal cortex",
        "",
        "Dan: amygdala spatial panel",
    ]),
    (BLUE, "2", "The question", [
        "Does this gene name one",
        "of the 20 cell types?",
        "",
        "Or does it report",
        "morphine, circadian,",
        "or receptor state?",
        "",
        "If neither: it is out.",
    ]),
    (RED, "3", "What we drop", [
        "On in every cell",
        "(no contrast — e.g. Clock)",
        "",
        "Too rare to make a map",
        "(e.g. Sstr4 at 1%)",
        "",
        "Same job as a gene",
        "already on the list",
    ]),
    (GREEN, "4", "What we keep", [
        "259 genes",
        "one shared panel",
        "",
        "All 20 cell types named",
        "12 cortex + 8 amygdala",
        "",
        "Read from the same mouse",
        "on the same slide",
    ]),
]
X0, W, GAP = 2.0, 22.0, 2.2
for i, (col, num, head, lines) in enumerate(STEPS):
    x = X0 + i * (W + GAP)
    card(ax, x, 10, W, 80, col, fill="white", lw=1.8)
    ax.add_patch(FancyBboxPatch((x, 76), W, 14,
                                boxstyle="round,pad=0,rounding_size=0.5",
                                fc=col, ec=col, lw=0, zorder=3))
    ax.text(x + 3.3, 83, num, ha="center", va="center", fontsize=14,
            color="white", fontweight="bold", zorder=4)
    ax.text(x + 6.2, 83, head, ha="left", va="center", fontsize=13.5,
            color="white", fontweight="bold", zorder=4)
    yy = 70
    for ln in lines:
        ax.text(x + 1.6, yy, ln, ha="left", va="top", fontsize=11.2, color=DARK)
        yy -= 7.0
    if i < 3:
        ax.add_patch(FancyArrowPatch((x + W + 0.2, 50), (x + W + GAP - 0.2, 50),
                                     arrowstyle="-|>", mutation_scale=16,
                                     color="#9AA5B1", lw=1.8))

ax.text(50, 4.5, "Read left to right: data  →  question  →  drop  →  259-gene list.",
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
# Plain-language roster: 12 cortex types | 8 amygdala types. One naming gene each.
ORBM = [
    ("Layer 2/3 excitatory", "Ccbe1", "upper layers"),
    ("Layer 4/5 excitatory", "Tnnc1", "middle layers"),
    ("Layer 5 IT excitatory", "Colq", "local output"),
    ("Layer 5 ET output", "L3mbtl4", "long-range output"),
    ("Layer 5 NP excitatory", "Abi3bp", "near-projecting"),
    ("Layer 6 CT excitatory", "Syt6", "to thalamus"),
    ("Layer 6b excitatory", "Ccn2", "deepest layer"),
    ("Layer 6 IT excitatory", "Blnk", "deep local"),
    ("Pvalb inhibitory", "Pvalb", "fast-spiking"),
    ("Sst inhibitory", "Sst", "somatostatin"),
    ("Vip inhibitory", "Vip", "VIP class"),
    ("Lamp5 inhibitory", "Hapln1", "Lamp5 class"),
]
BMAP = [
    ("VGLUT1 excitatory", "Krt2", "pallial amygdala"),
    ("Ccdc42 excitatory", "Ccdc42", "BMA glutamatergic"),
    ("Otp Foxp2 excitatory", "Stc1", "VGLUT2-like"),
    ("Otp Zic2 excitatory", "Sim1", "VGLUT2-like"),
    ("Skor1 excitatory", "Skor1", "hypothalamus border"),
    ("Sox6 inhibitory", "Prox1", "vs Lhx6 neighbour"),
    ("Lhx6 Sp9 inhibitory", "Lhx6", "Sox6 neighbour"),
    ("Ebf1 Pdyn inhibitory", "Isl1", "striatal-like GABA"),
]

fig, ax = plt.subplots(figsize=(12.50, 5.05))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

def roster(x, title, n, color, rows, row_h):
    card(ax, x, 8, 48.2, 88, color, fill="white", lw=1.8)
    ax.add_patch(FancyBboxPatch((x, 83), 48.2, 13, boxstyle="round,pad=0,rounding_size=0.4",
                                fc=color, ec=color, lw=0, zorder=3))
    ax.text(x + 24.1, 89.5, f"{title}   ·   {n} cell types", ha="center", va="center",
            fontsize=13.5, color="white", fontweight="bold", zorder=4)
    for i, (name, gene, note) in enumerate(rows):
        y = 77.5 - i * row_h
        ax.text(x + 1.8, y, name, ha="left", va="center", fontsize=11.4,
                color=DARK, fontweight="bold")
        ax.text(x + 27.8, y, gene, ha="left", va="center", fontsize=11.4,
                color=color, fontweight="bold", fontstyle="italic")
        ax.text(x + 36.2, y, note, ha="left", va="center", fontsize=10.0, color=GREY)

roster(1.2, "ORBm  ·  orbitofrontal cortex", 12, NAVY, ORBM, 5.85)
roster(50.6, "BMAp  ·  basomedial amygdala", 8, RED, BMAP, 7.4)
ax.text(52.6, 16.0, "All 8 amygdala types are named.", ha="left", va="center",
        fontsize=11.2, color=RED, fontweight="bold")
ax.text(52.6, 11.5, "Closest pair: Sox6 vs Lhx6 Sp9. Prox1 splits them.",
        ha="left", va="center", fontsize=10.2, color=GREY)
ax.text(50, 1.2, "Each line is one cell type. The gene in colour is an example of how that type is named on the panel.",
        ha="center", fontsize=10.5, color=NAVY)
fig.savefig(FIG / "s4_populations.png", dpi=190, bbox_inches="tight",
            facecolor="white", pad_inches=0.06)
plt.close(fig)

print("wrote 3 figures to", FIG)
for f in sorted(FIG.glob("*.png")):
    print(" ", f.name)
