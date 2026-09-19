"""Genome-wide search for the best subtype (supertype) separators inside each of the
20 ORBm/BMAp anchor subclasses.

The panel has to do two different jobs and the earlier versions only checked the first:
  (1) call the 20 known Allen subclasses  -> subclass-level unique separators, already done
  (2) split those subclasses into sub-populations so a TRAP+ ensemble can be resolved
      below subclass -> needs a marker that is high in one supertype and low in its
      siblings of the SAME parent subclass.

A separator qualifies when, within its parent subclass:
    pct in target supertype   >= PCT_IN
    pct minus best sibling    >= GAP
    target supertype size     >= MIN_N   (small supertypes give unstable percentages)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
CACHE = OUT / "anchor_subtype_cache.npz"
DST = OUT / "SUBTYPE_SEPARATORS_genomewide.xlsx"

GAP = 25.0
PCT_IN = 50.0
MIN_N = 100
TOP_PER_SUPERTYPE = 6


def main() -> None:
    z = np.load(CACHE, allow_pickle=True)
    genes = np.array([str(x) for x in z["genes"]])
    anchors = [str(x) for x in z["sup_keys"]]

    rows = []
    for anc in anchors:
        M = z[f"sup_pct__{anc}"]
        lab = [str(x) for x in z[f"sup_lab__{anc}"]]
        nn = z[f"sup_n__{anc}"]
        for i, L in enumerate(lab):
            if nn[i] < MIN_N:
                continue
            other = np.delete(M, i, axis=0).max(axis=0)
            gap = M[i] - other
            ok = np.where((gap >= GAP) & (M[i] >= PCT_IN))[0]
            ok = ok[np.argsort(-gap[ok])][:TOP_PER_SUPERTYPE]
            for j in ok:
                rows.append({
                    "parent_anchor": anc,
                    "supertype": L,
                    "n_cells": int(nn[i]),
                    "n_siblings": len(lab),
                    "gene": genes[j],
                    "pct_in": round(float(M[i, j]), 1),
                    "best_sibling_pct": round(float(other[j]), 1),
                    "gap_pp": round(float(gap[j]), 1),
                })
    sep = pd.DataFrame(rows)

    sc = pd.read_excel(OUT / "ALL_PANELS_anchor_and_subtype_scores.xlsx", "gene_scores")
    panel_cols = [c for c in sc.columns if c.startswith("on_")]
    on_any = set(sc[sc[panel_cols].any(axis=1)].gene.astype(str))
    sep["already_on_some_panel"] = sep.gene.isin(on_any)
    sep["on_301"] = sep.gene.isin(set(sc[sc.on_g301].gene.astype(str)))
    sep["on_IDEAL178"] = sep.gene.isin(set(sc[sc.on_IDEAL_178].gene.astype(str)))

    # how many qualifying supertypes each candidate gene can separate
    per_gene = (sep.groupby("gene")
                  .agg(n_supertypes_separated=("supertype", "nunique"),
                       best_gap=("gap_pp", "max"),
                       best_pct_in=("pct_in", "max"),
                       parents=("parent_anchor", lambda s: ", ".join(sorted(set(s)))))
                  .reset_index()
                  .sort_values(["n_supertypes_separated", "best_gap"], ascending=False))
    per_gene["already_on_some_panel"] = per_gene.gene.isin(on_any)

    cov = (sep.groupby(["parent_anchor", "supertype", "n_cells"])
             .agg(n_candidates=("gene", "nunique"),
                  n_on_301=("on_301", "sum"),
                  n_on_IDEAL=("on_IDEAL178", "sum"),
                  top5=("gene", lambda s: ", ".join(list(dict.fromkeys(s))[:5])))
             .reset_index().sort_values(["parent_anchor", "supertype"]))

    with pd.ExcelWriter(DST) as xw:
        sep.to_excel(xw, sheet_name="candidates", index=False)
        per_gene.to_excel(xw, sheet_name="per_gene", index=False)
        cov.to_excel(xw, sheet_name="supertype_coverage", index=False)
    print("wrote", DST)

    tot = cov.shape[0]
    print(f"\nqualifying supertypes (n>={MIN_N}, has >=1 separator at gap>={GAP:.0f}pp "
          f"and pct_in>={PCT_IN:.0f}%): {tot}")
    print(f"  covered by 301   : {(cov.n_on_301 > 0).sum():3}/{tot}  "
          f"(>=2 markers: {(cov.n_on_301 >= 2).sum()})")
    print(f"  covered by IDEAL : {(cov.n_on_IDEAL > 0).sum():3}/{tot}  "
          f"(>=2 markers: {(cov.n_on_IDEAL >= 2).sum()})")
    print("\nsupertypes with NO marker on the 301 panel:")
    miss = cov[cov.n_on_301 == 0]
    print(miss[["parent_anchor", "supertype", "n_cells", "n_candidates", "top5"]]
          .to_string(index=False) if len(miss) else "  none")


if __name__ == "__main__":
    main()
