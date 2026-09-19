"""Visual validation of the v8 panel against the earlier versions.

Left  - does every probe have a job? empty-map probes vs sub-population coverage
Right - for v8, is every low-detection gene low because it is sub-population
        specific (high separation gap) rather than because it is undetectable?
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
F = OUT / "PANEL_FINAL_v8_ORBm_BMAp.xlsx"
DST = OUT / "PANEL_v8_validation.png"

VIS, SUB_GAP = 50.0, 25.0

cmp = pd.read_excel(F, "VERSION_COMPARISON")
m = pd.read_excel(F, "PANEL_ORDER")

fig, ax = plt.subplots(1, 2, figsize=(15.5, 6.2))
plt.rcParams.update({"font.size": 11})

# ---------------------------------------------------------------- left
a = ax[0]
x = np.arange(len(cmp))
w = 0.38
work = cmp.n_genes - cmp.n_EMPTY_MAP_probes
a.bar(x - w / 2, work, w, color="#2a7ab0", label="probes with a measured job")
a.bar(x - w / 2, cmp.n_EMPTY_MAP_probes, w, bottom=work, color="#c0392b",
      label="empty-map probes (undetectable and non-separating)")
for i, (t_, e) in enumerate(zip(cmp.n_genes, cmp.n_EMPTY_MAP_probes)):
    a.text(i - w / 2, t_ + 6, f"{t_}", ha="center", fontsize=9)
    if e:
        a.text(i - w / 2, t_ + 20, f"{e} dead", ha="center", color="#c0392b",
               fontsize=9, fontweight="bold")
a.set_ylabel("number of probes on the panel")
a.set_xticks(x)
a.set_xticklabels(cmp.panel, rotation=15)
a.set_ylim(0, 380)
a.set_xlabel("panel version")

a2 = a.twinx()
a2.plot(x + w / 2, cmp.supertypes_with_2plus_markers, "o-", color="#1e8449", lw=2.2,
        ms=8, label="sub-populations with $\\geq$2 markers")
a2.plot(x + w / 2, cmp.supertypes_with_1plus_marker, "s--", color="#7dcea0", lw=2,
        ms=7, label="sub-populations with $\\geq$1 marker")
a2.axhline(86, color="grey", ls=":", lw=1.4)
a2.text(len(cmp) - 0.55, 88, "all 86 separable\nsub-populations", fontsize=9,
        color="grey", ha="right")
a2.set_ylabel("Allen supertypes resolved (of 86)", color="#1e8449")
a2.tick_params(axis="y", labelcolor="#1e8449")
a2.set_ylim(0, 105)

h1, l1 = a.get_legend_handles_labels()
h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, framealpha=0.95)
a.set_title("Every version traded dead probes against sub-population coverage.\n"
            "v8 gets the coverage with none of the dead probes.", fontsize=12)

# ---------------------------------------------------------------- right
b = ax[1]
s = m[m.anchor_max_pct.notna()].copy()
s["best_gap"] = s[["subclass_gap_pp", "supertype_gap_pp"]].max(axis=1)
ident = s.block.isin(["05_subclass_separator", "06_subtype_separator"])
glia = s.block == "04_nonneuronal_counterstain"
ieg = s.block == "07_IEG_pCREB_target"
state = ~(ident | glia | ieg)

b.axvspan(0, VIS, color="#fdebd0", zorder=0)
b.axhline(SUB_GAP, color="grey", ls="--", lw=1.3)
b.axvline(VIS, color="grey", ls="--", lw=1.3)
b.text(25, 97, "low detection", ha="center", fontsize=10, color="#b9770e")
b.text(2, SUB_GAP + 2, f"separation bar {SUB_GAP:.0f}pp", fontsize=9, color="grey")

for mask, c, lab, mk in [
        (ident, "#2471a3", "identity: cell type / sub-population marker", "o"),
        (state, "#7d3c98", "state: GPCR, plasticity, TF, clock, morphine", "^"),
        (ieg, "#d68910", "IEG / pCREB target (exempt: atlas is resting tissue)", "s"),
        (glia, "#148f77", "glia / vascular (scored on its own population)", "D")]:
    b.scatter(s.anchor_max_pct[mask], s.best_gap[mask], s=42, c=c, marker=mk,
              alpha=0.8, edgecolor="white", linewidth=0.5, label=lab)

for g in ["Vdr", "Th", "Oprk1", "Rgs5", "Npas4", "Fos", "Satb2", "Adrb1", "Oprm1"]:
    r = s[s.gene == g]
    if len(r):
        b.annotate(g, (r.anchor_max_pct.iloc[0], r.best_gap.iloc[0]),
                   textcoords="offset points", xytext=(6, 5), fontsize=9)

b.set_xlabel("detection: % of cells positive at the best of the 20 ORBm/BMAp target types")
b.set_ylabel("separation: best gap vs neighbouring populations (percentage points)")
b.set_xlim(-3, 105)
b.set_ylim(-3, 105)
b.legend(loc="upper right", fontsize=9, framealpha=0.95)
b.set_title("v8: no probe sits in the bottom-left dead zone.\n"
            "Low-detection genes are there because they are sub-population specific.",
            fontsize=12)

fig.suptitle("Validation of the final ORBm/BMAp Xenium panel (v8, 318 genes) - "
             "Allen WMB-10X, 226,886 cells (ORBm 106,122 / BMAp 120,764)",
             fontsize=13, y=1.0)
fig.tight_layout()
fig.savefig(DST, dpi=170, bbox_inches="tight")
print("wrote", DST)

dead = s[(s.anchor_max_pct < VIS) & (s.best_gap < SUB_GAP) & ~(glia | ieg)]
print(f"genes in the dead zone (detection<{VIS:.0f}% and gap<{SUB_GAP:.0f}pp, "
      f"excluding exempt classes): {len(dead)}")
if len(dead):
    print(dead[["gene", "block", "anchor_max_pct", "best_gap"]].to_string(index=False))
