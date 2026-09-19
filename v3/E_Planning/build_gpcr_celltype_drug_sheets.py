"""Receptor-by-cell-type map and the drug layer, built against the final panel.

This is the deliverable the experiment is actually for: for each of the 20 target
populations, which receptors on the panel sit on it, and which of those already have a
drug. Two views, because they answer different questions:

  GPCR_PER_CELLTYPE   one row per cell population - what can I pharmacologically reach
                      in this population
  GPCR_BY_CELLTYPE    one row per receptor - where does this drug target live
  GPCR_DRUGS          one row per receptor with an agent, from IUPHAR / DrugBank
  GPCR_DRUGS_DETAIL   one row per receptor-drug pair

Every percentage is measured in Allen WMB-10X cells from ORBm and BMAp only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path(r"c:\Users\hsollim\Downloads")
DST = OUT / "GPCR_CELLTYPE_AND_DRUGS.xlsx"

spec = importlib.util.spec_from_file_location("b", V3 / "E_Planning" /
                                              "build_panel_v9_minimal.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

# Receptors added by the sweep that the local IUPHAR table did not yet cover.
EXTRA_DRUGS = [
    ("Sstr2", "Somatostatin SST2 receptor", "octreotide", "approved", "peptide agonist",
     1988, "acromegaly, neuroendocrine tumour", "DB00104"),
    ("Sstr2", "Somatostatin SST2 receptor", "lanreotide", "approved", "peptide agonist",
     2007, "acromegaly, neuroendocrine tumour", "DB06791"),
    ("Sstr2", "Somatostatin SST2 receptor", "pasireotide", "approved",
     "peptide agonist", 2012, "Cushing disease", "DB06663"),
    ("Tacr1", "Neurokinin NK1 receptor", "aprepitant", "approved",
     "small-molecule antagonist", 2003, "chemotherapy-induced nausea", "DB00673"),
    ("Tacr1", "Neurokinin NK1 receptor", "fosaprepitant", "approved",
     "small-molecule antagonist", 2008, "chemotherapy-induced nausea", "DB06716"),
    ("Tacr1", "Neurokinin NK1 receptor", "rolapitant", "approved",
     "small-molecule antagonist", 2015, "chemotherapy-induced nausea", "DB09291"),
    ("Hrh3", "Histamine H3 receptor", "pitolisant", "approved",
     "inverse agonist / antagonist", 2016, "narcolepsy", "DB11642"),
    ("Htr7", "5-HT7 receptor", "amisulpride", "approved", "antagonist", 1986,
     "schizophrenia; 5-HT7 is a secondary target", "DB06288"),
    ("Htr7", "5-HT7 receptor", "SB-269970", "research", "selective antagonist", 2000,
     "research tool for 5-HT7", ""),
    ("Adora1", "Adenosine A1 receptor", "caffeine", "approved",
     "non-selective antagonist", 1900, "stimulant; A1/A2A antagonist", "DB00201"),
    ("Adora1", "Adenosine A1 receptor", "istradefylline", "approved",
     "A2A antagonist, A1-adjacent", 2019, "Parkinson disease", "DB11757"),
    ("Adora1", "Adenosine A1 receptor", "DPCPX", "research", "selective antagonist",
     1987, "research tool for A1", ""),
    ("Oxtr", "Oxytocin receptor", "oxytocin", "approved", "peptide agonist", 1962,
     "labour induction; investigated for social behaviour", "DB00107"),
    ("Oxtr", "Oxytocin receptor", "atosiban", "approved", "peptide antagonist", 2000,
     "preterm labour", "DB06813"),
    ("Npy2r", "Neuropeptide Y Y2 receptor", "BIIE0246", "research",
     "selective antagonist", 1999, "research tool for Y2", ""),
    ("Gpr101", "GPR101 (orphan)", "-", "orphan", "no ligand in clinical use", 0,
     "orphan receptor; X-LAG acrogigantism gene", ""),
    ("Gpr26", "GPR26 (orphan)", "-", "orphan", "no ligand in clinical use", 0,
     "orphan; constitutively active, cAMP-coupled", ""),
]
DCOLS = ["gene_symbol", "iuphar_receptor", "drug_name", "drug_status", "drug_class",
         "year_approved_or_published", "indication", "drugbank_id"]


def main() -> None:
    panel = pd.read_excel(OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx", "PANEL_ORDER")
    bycat = pd.read_excel(OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx", "BY_CATEGORY")
    gpcrs = sorted(set(bycat[bycat.category == "3_GPCR"].gene))
    print(f"GPCRs on the panel: {len(gpcrs)}")

    z, gsym, gi = b.load_cache()
    P = z["anchor_pct"]
    names = [str(x) for x in z["anchor_names"]]
    ncell = {n: int(c) for n, c in zip(names, z["anchor_n"])}
    ac = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                       "ANCHOR_COVERAGE")
    reg = dict(zip(ac.allen_subclass_anchor, ac.region))
    present = [g for g in gpcrs if g in gi]
    missing = [g for g in gpcrs if g not in gi]
    M = np.vstack([P[:, gi[g]] for g in present]).T            # anchors x receptors

    # ---------------------------------------------------- per receptor
    rows = []
    for j, g in enumerate(present):
        col = M[:, j]
        o = np.argsort(-col)
        med = float(np.median(col))
        rows.append({
            "gpcr": g,
            "top1_celltype": names[o[0]], "top1_pct": round(float(col[o[0]]), 1),
            "top2_celltype": names[o[1]], "top2_pct": round(float(col[o[1]]), 1),
            "top3_celltype": names[o[2]], "top3_pct": round(float(col[o[2]]), 1),
            "median_pct_across_20": round(med, 1),
            "gap_top1_vs_median_pp": round(float(col[o[0]]) - med, 1),
            "n_celltypes_ge50pct": int((col >= 50).sum()),
            "reads_as": ("broad level readout" if (col >= 50).sum() >= 15
                         else "cell-type restricted" if (col >= 50).sum() <= 5
                         else "partially restricted"),
        })
    by_gpcr = pd.DataFrame(rows).sort_values("gap_top1_vs_median_pp", ascending=False)

    # ---------------------------------------------------- per cell type
    rows = []
    for i, a in enumerate(names):
        col = M[i]
        other = np.delete(M, i, axis=0).max(axis=0)
        enr = [(present[j], col[j], col[j] - other[j]) for j in range(len(present))
               if col[j] >= 30 and col[j] - other[j] >= 10]
        enr.sort(key=lambda x: -x[2])
        top = sorted(((present[j], col[j]) for j in range(len(present))),
                     key=lambda x: -x[1])[:8]
        rows.append({
            "region": reg.get(a), "cell_type": a, "n_Allen_cells": ncell[a],
            "n_GPCRs_detected_ge50pct": int((col >= 50).sum()),
            "n_GPCRs_enriched_here": len(enr),
            "GPCRs_enriched_in_this_type":
                ", ".join(f"{g} (+{d:.0f}pp, {p:.0f}%)" for g, p, d in enr[:6]) or "-",
            "top_GPCRs_by_detection":
                ", ".join(f"{g} {p:.0f}%" for g, p in top),
        })
    per_type = pd.DataFrame(rows).sort_values(["region", "n_GPCRs_enriched_here"],
                                              ascending=[True, False])

    # ---------------------------------------------------- drug layer
    det = pd.read_csv(V3 / "inputs" / "gpcr_drug_targets_detailed.csv")
    det = det[[c for c in DCOLS if c in det.columns]].copy()
    for c in DCOLS:
        if c not in det.columns:
            det[c] = ""
    det = pd.concat([det[DCOLS], pd.DataFrame(EXTRA_DRUGS, columns=DCOLS)],
                    ignore_index=True)
    det = det[det.gene_symbol.isin(gpcrs)].drop_duplicates(["gene_symbol", "drug_name"])
    det["on_panel"] = True
    det = det.merge(by_gpcr[["gpcr", "top1_celltype", "top1_pct", "reads_as"]],
                    left_on="gene_symbol", right_on="gpcr", how="left").drop(
                    columns="gpcr")
    det = det.sort_values(["gene_symbol", "drug_status", "drug_name"])

    summ = pd.read_csv(V3 / "inputs" / "gpcr_drug_targets.csv")
    summ = summ[summ.gene_symbol.isin(gpcrs)]
    agg = (det[det.drug_status.astype(str).str.contains("approved", case=False)]
           .groupby("gene_symbol").drug_name.apply(lambda s: ", ".join(sorted(set(s)))))
    drugs = pd.DataFrame({"gene_symbol": gpcrs})
    drugs = drugs.merge(summ, on="gene_symbol", how="left")
    drugs["approved_drugs_resolved"] = drugs.gene_symbol.map(agg)
    drugs = drugs.merge(by_gpcr[["gpcr", "top1_celltype", "top1_pct",
                                 "n_celltypes_ge50pct", "reads_as"]],
                        left_on="gene_symbol", right_on="gpcr",
                        how="left").drop(columns="gpcr")
    drugs["has_any_agent"] = drugs.gene_symbol.isin(set(det.gene_symbol))

    readme = pd.DataFrame([
        ("What this is", f"The receptor layer of the {len(panel)}-gene panel: "
                         f"{len(gpcrs)} GPCRs, where each sits among the 20 target cell "
                         f"populations, and which of them already have a drug."),
        ("GPCR_PER_CELLTYPE", "One row per target cell population. 'enriched here' "
                              "means detected in >=30% of that population and >=10 "
                              "percentage points above every other target population."),
        ("GPCR_BY_CELLTYPE", "One row per receptor, with its top three populations. "
                             "'reads_as' says how to use it: a receptor above 50% in "
                             "15+ of 20 populations is a level readout inside an "
                             "already-named cell type, not a location marker."),
        ("GPCR_DRUGS / _DETAIL", "IUPHAR/BPS Guide to PHARMACOLOGY and DrugBank. "
                                 f"{det.gene_symbol.nunique()} of the {len(gpcrs)} "
                                 f"receptors have a named agent, across {len(det)} "
                                 f"receptor-drug pairs."),
        ("Measurement", "Allen WMB-10X, ORBm and BMAp cells only (226,886 cells; "
                        "124,115 inside the 20 target populations). Percentages are "
                        "the fraction of cells in that population with a non-zero "
                        "count."),
        ("Caveat", "These are 10x single-cell percentages. Xenium recovers fewer "
                   "transcripts per cell, so treat them as a ranking between "
                   "receptors, not as a promised per-cell sensitivity."),
        ("Not scored", ", ".join(missing) if missing else
                        "all panel GPCRs were found on the Allen gene axis"),
    ], columns=["item", "detail"])

    with pd.ExcelWriter(DST) as xw:
        readme.to_excel(xw, sheet_name="READ_ME", index=False)
        per_type.to_excel(xw, sheet_name="GPCR_PER_CELLTYPE", index=False)
        by_gpcr.to_excel(xw, sheet_name="GPCR_BY_CELLTYPE", index=False)
        drugs.to_excel(xw, sheet_name="GPCR_DRUGS", index=False)
        det.to_excel(xw, sheet_name="GPCR_DRUGS_DETAIL", index=False)

    pd.set_option("display.width", 300)
    print(f"\nreceptor-drug pairs: {len(det)} across "
          f"{det.gene_symbol.nunique()}/{len(gpcrs)} receptors")
    print(f"\nGPCRs per cell type:")
    print(per_type[["region", "cell_type", "n_GPCRs_detected_ge50pct",
                    "n_GPCRs_enriched_here"]].to_string(index=False))
    print(f"\nmost cell-type-restricted receptors:")
    print(by_gpcr.head(10)[["gpcr", "top1_celltype", "top1_pct",
                            "gap_top1_vs_median_pp", "reads_as"]].to_string(index=False))
    print("\nwrote", DST)


if __name__ == "__main__":
    main()
