"""Visual validation of the right-sized v9 panel.

Left   what each panel size actually buys: dead probes and wasted ubiquitous probes
       against the number of sub-populations resolved
Right  v9 gene by gene: is every low-detection probe low because it is
       sub-population specific, rather than because it is undetectable
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "outputs"
F = OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx"
DST = OUT / "PANEL_v9_validation.png"
VIS, SUB_GAP = 50.0, 25.0

cmp = pd.read_excel(F, "VERSION_COMPARISON")
m = pd.read_excel(F, "PANEL_ORDER")

fig, ax = plt.subplots(1, 2, figsize=(16, 7.6))
a, b = ax

x = np.arange(len(cmp))
w = 0.34
useful = cmp.n_genes - cmp.n_EMPTY_MAP_probes - cmp.n_ubiquitous_no_contrast
a.bar(x - w / 2, useful, w, color="#2a7ab0", label="probes doing a measured job")
a.bar(x - w / 2, cmp.n_ubiquitous_no_contrast, w, bottom=useful, color="#e59866",
      label="ubiquitous, no contrast (>$95\\%$ in $\\geq$18 of 20 types, gap <12pp)")
a.bar(x - w / 2, cmp.n_EMPTY_MAP_probes, w,
      bottom=useful + cmp.n_ubiquitous_no_contrast, color="#c0392b",
      label="empty map (undetectable and non-separating)")
for i, r in cmp.iterrows():
    a.text(i - w / 2, r.n_genes + 7, f"{r.n_genes}", ha="center", fontsize=9,
           fontweight="bold")
    wasted = r.n_EMPTY_MAP_probes + r.n_ubiquitous_no_contrast
    if wasted:
        a.text(i - w / 2, r.n_genes + 22, f"{wasted} wasted", ha="center",
               color="#a04000", fontsize=8.5)
a.set_ylabel("probes on the panel")
a.set_xlabel("panel version")
a.set_xticks(x)
a.set_xticklabels(cmp.panel, rotation=12)
a.set_ylim(0, 390)

a2 = a.twinx()
a2.plot(x + w / 2, cmp.subpops_meeting_target, "o-", color="#1e8449", lw=2.3, ms=8,
        label="sub-populations at full marker target")
a2.plot(x + w / 2, cmp.subpops_with_1plus, "s--", color="#7dcea0", lw=2, ms=7,
        label="sub-populations with $\\geq$1 marker")
a2.axhline(86, color="grey", ls=":", lw=1.3)
a2.text(-0.35, 88, "all 86 separable sub-populations", fontsize=8.5, color="grey",
        ha="left")
a2.set_ylabel("Allen supertypes resolved (of 86)", color="#1e8449")
a2.tick_params(axis="y", labelcolor="#1e8449")
a2.set_ylim(0, 108)

h1, l1 = a.get_legend_handles_labels()
h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.13),
         fontsize=8.5, ncol=1, framealpha=0.95)
a.set_title("v9 keeps all of the resolution of the 318-gene panel\n"
            "with 79 fewer probes and nothing wasted", fontsize=12)

# ---------------------------------------------------------------- right
s = m[m.anchor_max_pct.notna()].copy()
s["best_gap"] = s[["subclass_gap_pp", "supertype_gap_pp"]].max(axis=1)
ident = s.block.isin(["05_celltype_separator", "06_subtype_separator",
                      "03b_taxonomy_backbone"])
glia = s.block == "04_nonneuronal_counterstain"
ieg = s.block == "07_IEG_pCREB_target"
state = ~(ident | glia | ieg)

b.axvspan(0, VIS, color="#fdebd0", zorder=0)
b.axhline(SUB_GAP, color="grey", ls="--", lw=1.2)
b.axvline(VIS, color="grey", ls="--", lw=1.2)
b.text(25, 99, "low detection", ha="center", fontsize=9.5, color="#b9770e")
b.text(1.5, SUB_GAP + 2, f"separation bar {SUB_GAP:.0f}pp", fontsize=8.5, color="grey")
b.add_patch(plt.Rectangle((0, 0), VIS, SUB_GAP, facecolor="#c0392b", alpha=0.10,
                          zorder=0))
b.text(25, 7, "dead zone: undetectable AND non-separating\n"
              "only Drd2 sits here, kept on pharmacological grounds\n"
              "(IEGs here are exempt: the atlas is resting tissue)",
       ha="center", fontsize=8.5, color="#c0392b")

for mask, c, lab, mk in [
        (ident, "#2471a3", "identity: cell type, taxonomy, sub-population", "o"),
        (state, "#7d3c98", "state: GPCR, plasticity, clock, morphine", "^"),
        (ieg, "#d68910", "IEG / pCREB target (exempt: atlas is resting tissue)", "s"),
        (glia, "#148f77", "glia / vascular (scored on its own population)", "D")]:
    b.scatter(s.anchor_max_pct[mask], s.best_gap[mask], s=44, c=c, marker=mk,
              alpha=0.82, edgecolor="white", linewidth=0.5, label=lab)
b.annotate("glia are scored against the 20 NEURONAL target\ntypes, so they belong on the "
           "left by construction",
           xy=(5, 12), xytext=(8, 74), fontsize=8.5, color="#148f77",
           arrowprops=dict(arrowstyle="->", color="#148f77", lw=1.1,
                           connectionstyle="arc3,rad=-0.25"))

for g in ["Oprk1", "Rgs5", "Npas4", "Fos", "Satb2", "Adrb1", "Oprm1",
          "Drd2", "Piezo2", "Fezf2", "Sox6", "Htr2a"]:
    r = s[s.gene == g]
    if len(r):
        b.annotate(g, (r.anchor_max_pct.iloc[0], r.best_gap.iloc[0]),
                   textcoords="offset points", xytext=(6, 5), fontsize=8.5)

b.set_xlabel("detection: % of cells positive at the best of the 20 ORBm/BMAp "
             "target cell types")
b.set_ylabel("separation: best gap versus neighbouring populations (percentage points)")
b.set_xlim(-3, 105)
b.set_ylim(-4, 105)
b.legend(loc="upper right", fontsize=8.5, framealpha=0.95)
b.set_title("v9, every probe: low detection only where the gene is\n"
            "sub-population specific or a deliberate exception", fontsize=12)

fig.suptitle(f"Final ORBm/BMAp Xenium panel v9 ({len(m)} genes) - validated on Allen "
             "WMB-10X, 226,886 cells (ORBm 106,122 / BMAp 120,764)",
             fontsize=13, y=1.005)
fig.tight_layout()
fig.savefig(DST, dpi=170, bbox_inches="tight")
print("wrote", DST)

dead = s[(s.anchor_max_pct < VIS) & (s.best_gap < SUB_GAP) & ~(glia | ieg)]
print(f"dead-zone genes: {len(dead)}")
print(dead[["gene", "block", "anchor_max_pct", "best_gap"]].to_string(index=False))
