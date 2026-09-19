"""Genome-wide marker search: is the 245-gene panel actually the best available?

The panel was chosen from a 701-gene shortlist; the Allen screen behind it evaluated
311 of 32,285 atlas genes (0.96%). This asks the question that could not be asked
before: across the WHOLE transcriptome, what are the best markers for

  (a) the 20 known ORBm/BMAp anchor populations, and
  (b) the 125 supertypes nested inside them - the sub-population level the user
      actually wants to discover,

and how many of those best markers are already on the panel?

Metric, per target group g and gene j, at a given taxonomy level:
  pct_in       percent of cells in g with a nonzero value
  pct_out_max  the highest pct_in among the competing groups
  gap          pct_in - pct_out_max, in percentage points

A gene is a usable marker when it is both detectable (pct_in high) and specific
(gap large). Competitors are the other 20 anchors for level (a), and the sibling
supertypes inside the same parent subclass for level (b) - that is the comparison
that matters for splitting a known type into sub-populations.

Regions are respected: ORBm anchors are scored on PL-ILA-ORB cells only, BMAp
anchors on sAMY only. The Isocortex shards are entirely PL-ILA-ORB and the STR
shard entirely sAMY, so the split is exact.

Duplicate gene symbols (40 of 32,285) are collapsed to the Ensembl row with the
highest overall detection, and the collapse is reported rather than hidden.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
GW = OUT / "allen_genomewide"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PA = OUT / "PANEL_A_current_166genes_119custom.xlsx"
PB = OUT / "PANEL_B_cut_147genes_100custom.xlsx"
PC = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"
DST = OUT / "allen_genomewide_marker_search.xlsx"

MIN_CELLS = 40        # groups smaller than this are too noisy to rank markers for
DETECT = 50.0         # percent-of-cells bar for "the instrument will see it"
GAP = 25.0            # percentage-point margin for "it is specific"


def combine(level: str) -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict]:
    """Return (nnz, n) accumulated per group label across shards, plus gene axis."""
    files = sorted(GW.glob("*.npz"))
    if len(files) != 7:
        raise SystemExit(f"expected 7 genome-wide files, found {len(files)}")
    genes = ensembl = None
    nnz, ncell, shard_of = {}, {}, {}
    for f in files:
        z = np.load(f, allow_pickle=True)
        g = [str(x) for x in z["genes"]]
        e = [str(x) for x in z["ensembl"]]
        if genes is None:
            genes, ensembl = g, e
        elif e != ensembl:
            raise SystemExit(f"{f.name}: gene axis differs")
        shard = str(z["shard"][0])
        roi = "sAMY" if "STR" in shard else "PL-ILA-ORB"
        labels = [str(x) for x in z[f"{level}_labels"]]
        NN, NC = z[f"{level}_nnz"], z[f"{level}_n"]
        for i, lab in enumerate(labels):
            key = (lab, roi)
            if key not in nnz:
                nnz[key] = np.zeros(len(genes), dtype=np.float64)
                ncell[key] = 0
            nnz[key] += NN[i]
            ncell[key] += int(NC[i])
            shard_of.setdefault(key, set()).add(shard)
    return nnz, ncell, genes, ensembl


def collapse_dups(pct: np.ndarray, genes: list[str], ensembl: list[str]):
    """One row per gene symbol: keep the Ensembl row with the highest max detection."""
    df = pd.DataFrame({"gene": genes, "ensembl": ensembl, "score": pct})
    dup = df.gene[df.gene.duplicated()].unique()
    keep = df.sort_values("score", ascending=False).drop_duplicates("gene").index
    return sorted(keep), list(dup)


def main() -> None:
    panel_base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    A = set(pd.read_excel(PA, "SHARED_PANEL_ORDER").gene.astype(str))
    B = set(pd.read_excel(PB, "SHARED_PANEL_ORDER").gene.astype(str))
    Cg = set(pd.read_excel(PC, "SHARED_PANEL_ORDER").gene.astype(str))
    measured_B = panel_base | B
    ac = pd.read_excel(PA, "ANCHOR_COVERAGE")
    anchor_roi = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
                  for r in ac.itertuples()}

    # ---------------- level (a): the 20 anchor populations
    nnz, ncell, genes, ensembl = combine("subclass")
    keys = [(a, anchor_roi[a]) for a in anchor_roi if (a, anchor_roi[a]) in nnz]
    print(f"anchors resolved: {len(keys)}/20")
    pct = np.vstack([nnz[k] / max(ncell[k], 1) * 100.0 for k in keys])   # 20 x genes
    keep, dups = collapse_dups(pct.max(axis=0), genes, ensembl)
    print(f"duplicate gene symbols collapsed: {len(dups)}")
    pct = pct[:, keep]
    gsym = [genes[i] for i in keep]

    rows = []
    for gi, k in enumerate(keys):
        other = np.delete(pct, gi, axis=0).max(axis=0)
        gap = pct[gi] - other
        ok = (pct[gi] >= DETECT) & (gap >= GAP)
        for j in np.argsort(-gap)[:400]:
            if not ok[j]:
                continue
            rows.append({"level": "anchor", "group": k[0], "region": k[1],
                         "gene": gsym[j], "pct_in": pct[gi, j],
                         "pct_out_max": other[j], "gap": gap[j],
                         "on_panel_C": gsym[j] in Cg,
                         "measured_in_B": gsym[j] in measured_B})
    anch = pd.DataFrame(rows)
    print(f"\n=== level (a) 20 known populations: {len(anch)} genome-wide markers "
          f"passing pct>={DETECT:.0f} and gap>={GAP:.0f}pp ===")
    s = anch.groupby("group").agg(
        markers=("gene", "size"),
        on_panel_C=("on_panel_C", "sum"),
        measured_in_B=("measured_in_B", "sum"),
        best_gap=("gap", "max")).sort_values("markers", ascending=False)
    print(s.to_string())
    print(f"\n  total distinct marker genes : {anch.gene.nunique()}")
    print(f"  of those already on Panel C : {anch[anch.on_panel_C].gene.nunique()}")
    print(f"  NOT on Panel C (missed)     : {anch[~anch.on_panel_C].gene.nunique()}")

    # ---------------- level (b): supertypes inside the anchors
    nnz2, ncell2, genes2, ensembl2 = combine("supertype")
    md = pd.read_csv(Path(r"C:\Users\hsollim\Downloads\abc_atlas_cache\metadata\WMB-10X")
                     / "20231215" / "views" / "cell_metadata_with_cluster_annotation.csv",
                     usecols=["region_of_interest_acronym", "subclass", "supertype"])
    md = md[md.region_of_interest_acronym.isin(["PL-ILA-ORB", "sAMY"])]
    md = md[md.subclass.isin(anchor_roi)]
    md = md[md.apply(lambda r: anchor_roi[r.subclass] == r.region_of_interest_acronym, axis=1)]
    parent = md.groupby("supertype").subclass.agg(lambda s: s.mode().iat[0]).to_dict()

    srows = []
    for sub, grp in md.groupby("subclass"):
        sts = sorted(grp.supertype.unique())
        roi = anchor_roi[sub]
        avail = [(st, roi) for st in sts if (st, roi) in nnz2 and ncell2[(st, roi)] >= MIN_CELLS]
        if len(avail) < 2:
            continue
        P = np.vstack([nnz2[k] / ncell2[k] * 100.0 for k in avail])
        kp, _ = collapse_dups(P.max(axis=0), genes2, ensembl2)
        P = P[:, kp]
        gs = [genes2[i] for i in kp]
        for i, k in enumerate(avail):
            other = np.delete(P, i, axis=0).max(axis=0)
            gap = P[i] - other
            ok = (P[i] >= DETECT) & (gap >= GAP)
            for j in np.argsort(-gap)[:60]:
                if not ok[j]:
                    continue
                srows.append({"level": "supertype", "parent_subclass": sub, "group": k[0],
                              "n_cells": ncell2[k], "gene": gs[j], "pct_in": P[i, j],
                              "pct_out_max": other[j], "gap": gap[j],
                              "on_panel_C": gs[j] in Cg,
                              "measured_in_B": gs[j] in measured_B})
    sup = pd.DataFrame(srows)
    n_st = md.supertype.nunique()
    covered = sup.group.nunique() if len(sup) else 0
    print(f"\n=== level (b) sub-population discovery: {n_st} supertypes inside the anchors ===")
    print(f"  supertypes with >=1 usable genome-wide marker : {covered}/{n_st}")
    if len(sup):
        print(f"  distinct marker genes                        : {sup.gene.nunique()}")
        print(f"  of those on Panel C                          : {sup[sup.on_panel_C].gene.nunique()}")
        print(f"  NOT on Panel C (missed)                      : {sup[~sup.on_panel_C].gene.nunique()}")
        withC = sup[sup.on_panel_C].group.nunique()
        withB = sup[sup.measured_in_B].group.nunique()
        print(f"\n  supertypes markable using ONLY Panel C genes : {withC}/{n_st}")
        print(f"  supertypes markable using ONLY Panel B genes : {withB}/{n_st}")
        print(f"  supertypes markable only with OFF-panel genes: "
              f"{covered - sup[sup.on_panel_C | sup.measured_in_B].group.nunique()}")

    # ---------------- how many genes would a genome-wide panel need?
    greedy = []
    if len(sup):
        need = set(sup.group.unique())
        pool = sup.sort_values("gap", ascending=False)
        chosen = []
        while need:
            best, cov = None, set()
            for g, sub_ in pool.groupby("gene"):
                c = set(sub_.group) & need
                if len(c) > len(cov):
                    best, cov = g, c
            if not best:
                break
            chosen.append({"gene": best, "new_supertypes_covered": len(cov),
                           "on_panel_C": best in Cg, "measured_in_B": best in measured_B})
            need -= cov
        greedy = chosen
        onC = sum(1 for c in chosen if c["on_panel_C"])
        print(f"\n=== minimum gene set to mark every markable supertype (greedy) ===")
        print(f"  genes needed : {len(chosen)}")
        print(f"  already on Panel C : {onC}  |  new genes required : {len(chosen) - onC}")
        print("  first 25: " + ", ".join(
            f"{c['gene']}{'' if c['on_panel_C'] else '*'}" for c in chosen[:25]))
        print("  (* = not on Panel C)")

    with pd.ExcelWriter(DST, engine="openpyxl") as w:
        pd.DataFrame({"item": [
            "What this is", "Why it exists", "Metric", "Thresholds", "Regions", "Duplicates"],
            "detail": [
                "Genome-wide marker search across all 32,285 Allen atlas genes for the 20 known "
                "ORBm/BMAp populations and the 125 supertypes nested inside them.",
                "The panel was selected from a 701-gene shortlist, and the Allen screen behind it "
                "covered only 311 of 32,285 genes (0.96%). This checks whether better markers exist "
                "among the ~32,000 genes that were never evaluated.",
                "pct_in = percent of cells in the group with a nonzero value. gap = pct_in minus the "
                "highest pct_in among competing groups (other anchors, or sibling supertypes).",
                f"A gene counts as a usable marker at pct_in >= {DETECT:.0f}% and gap >= {GAP:.0f} "
                f"percentage points. Groups with fewer than {MIN_CELLS} cells are skipped.",
                "ORBm anchors scored on PL-ILA-ORB cells only, BMAp anchors on sAMY only.",
                f"{len(dups)} duplicated gene symbols collapsed to the best-detected Ensembl row.",
            ]}).to_excel(w, "READ_ME", index=False)
        anch.sort_values(["group", "gap"], ascending=[True, False]).to_excel(w, "anchor_markers", index=False)
        s.to_excel(w, "anchor_summary")
        if len(sup):
            sup.sort_values(["parent_subclass", "group", "gap"],
                            ascending=[True, True, False]).to_excel(w, "supertype_markers", index=False)
        if greedy:
            pd.DataFrame(greedy).to_excel(w, "minimum_gene_set", index=False)
    print(f"\nwrote {DST}")


if __name__ == "__main__":
    main()
