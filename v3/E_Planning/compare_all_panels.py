"""Score every panel version that exists against the same measured yardsticks.

Nine files were produced over three weeks under changing constraints (100 add-on
slots -> no cap -> detection pruning -> goal alignment). This scores them all on one
ruler so the last version can be justified rather than asserted:

  size                genes, and how many have any locally measured number at all
  detection           median percent of cells detected at each gene's best population,
                      and how many genes fall under 50 pct
  level               how many genes are "too low to map reliably" (mean log2 < 1 and
                      under 50 pct of cells) - the money-wasting probes
  anchor coverage     of the 20 target populations, how many have a DEDICATED marker
                      on the panel (>=50 pct in it, >=20pp above the next-highest
                      population), from the genome-wide search over 32,285 genes
  subtype coverage    the same for the 96 supertypes nested in those 20 populations
  SOW genes           the nine genes the Statement of Work names by name
  hygiene             duplicate rows, and genes listed on a region sheet but missing
                      from the sheet that actually gets ordered
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")

# The eight endogenous mouse genes the SOW actually names - four as symbols (Fos, Arc,
# PER2, SATB2) and four by protein name (mu-opioid receptor, pCREB, beta1-adrenergic,
# 5-HT2A). Verified by four independent readers of the SOW text plus two adversarial
# verifier passes each, 0 rejections, in workflow sow-gene-extraction. Slc17a7 was
# counted as a ninth SOW gene in earlier versions of this table - that was an inference
# from "IT/CT principal neurons", not a literal mention, and it is corrected here.
SOW = ["Fos", "Arc", "Per2", "Satb2", "Oprm1", "Creb1", "Adrb1", "Htr2a"]

PANELS = [
    ("A 166 (100-slot add-on, Sep 18 10:59)", DL / "PANEL_A_current_166genes_119custom.xlsx", "SHARED_PANEL_ORDER"),
    ("MSGS 168 (Sep 18 10:33)", DL / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx", "SHARED_PANEL_ORDER"),
    ("IDEAL by category (Sep 18 14:29)", DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx", "SHARED_PANEL_ORDER"),
    ("standalone 197 (Sep 18 14:19)", DL / "FINAL_Xenium_panel_ORBm_BMAp_standalone_197genes.xlsx", "SHARED_PANEL_ORDER"),
    ("C 245 expanded (Sep 18 10:59)", DL / "PANEL_C_expanded_standalone_245genes.xlsx", "SHARED_PANEL_ORDER"),
    ("standalone 246 (Sep 18 14:14)", DL / "FINAL_Xenium_panel_ORBm_BMAp_standalone_246genes.xlsx", "SHARED_PANEL_ORDER"),
    ("C 246 + Adrb1 (Sep 18 14:12)", DL / "PANEL_C_FINAL_246_with_Adrb1.xlsx", "SHARED_PANEL_ORDER"),
    ("ULTIMATE v2 261 (Sep 18 13:55)", DL / "FINAL_ULTIMATE_PANEL_v2.xlsx", "FINAL_PANEL"),
    ("v6 232 (Sep 18 14:31)", O / "PANEL_FINAL_v6_ORBm_BMAp_complete.xlsx", "SHARED_PANEL_ORDER"),
    ("v7 252 (Sep 18 15:52)", DL / "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx", "SHARED_PANEL_ORDER"),
    ("v8 237 goal-aligned (Sep 18 17:33)", O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx", "SHARED_PANEL_ORDER"),
    ("301 discovery-heavy (Sep 18 17:42)", DL / "FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx", "SHARED_PANEL_ORDER"),
    ("v9 superset 307 (no trim)", O / "PANEL_FINAL_v9_ORBm_BMAp_UNLIMITED.xlsx", "FINAL_GENE_LIST"),
    ("v10 lean, no SOW clock (287)", O / "PANEL_FINAL_v10_ORBm_BMAp_BEST.xlsx", "FINAL_GENE_LIST"),
    ("v11 LEAN 297 (recommended)", O / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx", "FINAL_GENE_LIST"),
    ("v11 SUPERSET 317 (no trim)", O / "PANEL_FINAL_v11_ORBm_BMAp_SUPERSET.xlsx", "FINAL_GENE_LIST"),
]


def score(genes: set[str], det: pd.DataFrame, lvl: pd.DataFrame,
          gw_an: pd.DataFrame, gw_sup: pd.DataFrame) -> dict:
    meas = det[det.gene.isin(genes)]
    low = lvl[lvl.gene.isin(genes)]
    an_ok = gw_an[gw_an.gene.isin(genes)].group.nunique()
    su_ok = gw_sup[gw_sup.gene.isin(genes)].group.nunique()
    return {
        "genes": len(genes),
        "measured_locally": len(meas),
        "median_det_pct_at_best_anchor": round(float(meas.best_anchor_pct.median()), 1) if len(meas) else np.nan,
        "median_det_pct_own_population": round(float(meas.best_subclass_pct.median()), 1) if len(meas) else np.nan,
        "n_under_50pct_at_best_anchor": int((meas.best_anchor_pct < 50).sum()) if len(meas) else np.nan,
        "n_under_50pct_own_population": int((meas.best_subclass_pct < 50).sum()) if len(meas) else np.nan,
        "n_too_low_to_map": int((low.level_verdict == "too low to map reliably").sum()) if len(low) else np.nan,
        "anchors_with_dedicated_marker_of_20": int(an_ok),
        "supertypes_with_dedicated_marker_of_96": int(su_ok),
        "SOW_named_genes_of_8": int(sum(g in genes for g in SOW)),
        "SOW_missing": "; ".join(g for g in SOW if g not in genes) or "-",
    }


def main() -> None:
    det = pd.read_csv(O / "_MEAS_gene_summary.csv")
    lvl = pd.read_csv(O / "_MEAS_level_summary.csv")
    gw_an = pd.read_excel(DL / "allen_genomewide_marker_search.xlsx", "anchor_markers")
    gw_sup = pd.read_excel(DL / "allen_genomewide_marker_search.xlsx", "supertype_markers")
    ac = pd.read_excel(O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx", "ANCHOR_COVERAGE")
    anchors = set(ac.allen_subclass_anchor)
    gw_an = gw_an[(gw_an.group.isin(anchors)) & (gw_an.pct_in >= 50) & (gw_an.gap >= 20)]
    gw_sup = gw_sup[(gw_sup.parent_subclass.isin(anchors)) & (gw_sup.pct_in >= 50) & (gw_sup.gap >= 20)]

    rows = []
    for name, path, sheet in PANELS:
        if not path.exists():
            print(f"skip (missing) {path.name}")
            continue
        d = pd.read_excel(path, sheet)
        g = d.gene.astype(str)
        rec = {"panel": name, "file": path.name}
        rec.update(score(set(g), det, lvl, gw_an, gw_sup))
        rec["duplicate_rows"] = int(g.duplicated().sum())
        orph = 0
        for rs in ("ORBm_ORDER", "BMAp_ORDER", "ORBm_LIST", "BMAp_LIST"):
            try:
                r = pd.read_excel(path, rs)
            except Exception:
                continue
            orph += len(set(r.gene.astype(str)) - set(g))
        rec["region_sheet_orphans"] = orph
        rows.append(rec)
        print(f"{name:38s} {rec['genes']:4d} genes  "
              f"types {rec['anchors_with_dedicated_marker_of_20']:2d}/20  "
              f"subtypes {rec['supertypes_with_dedicated_marker_of_96']:2d}/96  "
              f"SOW {rec['SOW_named_genes_of_8']}/8  "
              f"<50pct own-pop {rec['n_under_50pct_own_population']:3}  "
              f"too-low {rec['n_too_low_to_map']}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(O / "_PANEL_COMPARISON.csv", index=False)
    print("\nwrote", O / "_PANEL_COMPARISON.csv")


if __name__ == "__main__":
    main()
