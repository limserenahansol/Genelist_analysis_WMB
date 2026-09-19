"""Score genes against the NON-NEURONAL populations of the two dissections.

The 20 ORBm/BMAp anchors are all neuronal, so an anchor-based detection filter
scores every astrocyte / oligo / microglia / vascular marker near zero and would
delete the counter-stain the panel needs to exclude glia from TRAP+ calls. Those
genes have to be judged against their own population instead.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
GW = OUT / "allen_genomewide"
DST = OUT / "NONNEURONAL_scores.xlsx"

# Allen WMB non-neuronal subclasses, grouped to the populations a panel must exclude.
# Subclass IDs verified against the labels actually present in the downloaded ORBm/BMAp
# shards. An earlier version guessed these and silently dropped Oligodendrocytes
# (327, 12,769 cells) and Endothelium (333, 4,328 cells) from the comparison, which made
# Mog and Cldn5 look unscorable when they were simply never tested.
GROUPS = {
    "Astrocyte": ["318 Astro-NT NN", "319 Astro-TE NN", "320 Astro-OLF NN",
                  "321 Astroependymal NN"],
    "Oligo": ["327 Oligo NN"],
    "OPC": ["326 OPC NN"],
    "Microglia": ["334 Microglia NN"],
    "Endothelial": ["333 Endo NN"],
    "Pericyte": ["331 Peri NN"],
    "SMC": ["332 SMC NN"],
    "VLMC": ["330 VLMC NN"],
    "Ependymal": ["323 Ependymal NN"],
    "BAM": ["335 BAM NN"],
    "Immune": ["338 Lymphoid NN", "336 Monocytes NN"],
}


def main() -> None:
    acc_nnz, acc_n, axis, ens = {}, {}, None, None
    for f in sorted(GW.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        g, e = [str(x) for x in z["genes"]], [str(x) for x in z["ensembl"]]
        if axis is None:
            axis, ens = g, e
        for i, lab in enumerate([str(x) for x in z["subclass_labels"]]):
            if lab not in acc_nnz:
                acc_nnz[lab] = np.zeros(len(axis))
                acc_n[lab] = 0
            acc_nnz[lab] += z["subclass_nnz"][i]
            acc_n[lab] += int(z["subclass_n"][i])

    present = {k: [s for s in v if acc_n.get(s, 0) >= 30] for k, v in GROUPS.items()}
    missing = {k: [s for s in v if acc_n.get(s, 0) < 30] for k, v in GROUPS.items()}
    print("populations found:")
    for k, v in present.items():
        print(f"  {k:12} n_cells={sum(acc_n[s] for s in v):7}  {v}")
    print("not found / too few cells:", {k: v for k, v in missing.items() if v})

    grp_pct, grp_n = {}, {}
    for k, subs in present.items():
        if not subs:
            continue
        nnz = np.sum([acc_nnz[s] for s in subs], axis=0)
        n = sum(acc_n[s] for s in subs)
        grp_pct[k], grp_n[k] = nnz / n * 100.0, n

    names = list(grp_pct)
    M = np.vstack([grp_pct[k] for k in names])

    # neuronal reference: everything that is not in one of these groups
    nn_subs = {s for v in present.values() for s in v}
    neu = [s for s in acc_nnz if s not in nn_subs and acc_n[s] >= 30]
    neu_nnz = np.sum([acc_nnz[s] for s in neu], axis=0)
    neu_pct = neu_nnz / sum(acc_n[s] for s in neu) * 100.0

    df = pd.DataFrame({"gene": axis, "ens": ens, "pct_neuronal_all": neu_pct})
    for k in names:
        df[f"pct_{k}"] = grp_pct[k]
    df["best_pop"] = [names[i] for i in M.argmax(axis=0)]
    df["best_pop_pct"] = M.max(axis=0)
    other = np.vstack([np.delete(M, i, axis=0).max(axis=0) for i in range(len(names))])
    df["gap_vs_other_nonneuronal"] = M.max(axis=0) - other[M.argmax(axis=0), np.arange(M.shape[1])]
    df["gap_vs_neurons"] = df.best_pop_pct - df.pct_neuronal_all
    df = df.sort_values("best_pop_pct", ascending=False).drop_duplicates("gene")

    sc = pd.read_excel(OUT / "ALL_PANELS_anchor_and_subtype_scores.xlsx", "gene_scores")
    pc = [c for c in sc.columns if c.startswith("on_")]
    df["on_any_panel"] = df.gene.isin(set(sc[sc[pc].any(axis=1)].gene.astype(str)))
    df["on_g301"] = df.gene.isin(set(sc[sc.on_g301].gene.astype(str)))
    df["on_v7"] = df.gene.isin(set(sc[sc.on_v7_252].gene.astype(str)))

    with pd.ExcelWriter(DST) as xw:
        df.to_excel(xw, sheet_name="all_genes", index=False)
        pd.DataFrame({"population": names,
                      "n_cells": [grp_n[k] for k in names]}).to_excel(
            xw, sheet_name="populations", index=False)
        best = []
        for k in names:
            q = df[(df.best_pop == k) & (df.gap_vs_neurons >= 40) & (df.best_pop_pct >= 60)]
            best.append(q.nlargest(12, "gap_vs_other_nonneuronal")[
                ["gene", "best_pop", "best_pop_pct", "gap_vs_other_nonneuronal",
                 "gap_vs_neurons", "pct_neuronal_all", "on_any_panel", "on_g301", "on_v7"]])
        pd.concat(best).to_excel(xw, sheet_name="top_per_population", index=False)
    print("\nwrote", DST)

    print("\ntop specific markers per non-neuronal population "
          "(pct in pop >=60, >=40pp above neurons):")
    for k in names:
        q = df[(df.best_pop == k) & (df.gap_vs_neurons >= 40) & (df.best_pop_pct >= 60)]
        q = q.nlargest(6, "gap_vs_other_nonneuronal")
        s = ", ".join(f"{r.gene}({r.best_pop_pct:.0f}%,+{r.gap_vs_other_nonneuronal:.0f}"
                      f"{'*' if r.on_any_panel else ''})" for r in q.itertuples())
        print(f"  {k:12} {s}")
    print("\n* = already on at least one panel version")


if __name__ == "__main__":
    main()
