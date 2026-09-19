"""Data-driven GPCR sweep over the whole Allen gene axis.

The v9 panel carried a hand-curated list of 20 receptors. That was a real gap: the
central aim of the experiment is cell-type-specific GPCRs, so the receptors should be
nominated by the data and then filtered, not chosen by pharmacological taste first.

Rule, fixed before looking at the result. A receptor is kept if it is
  (a) NOT ubiquitous-with-no-contrast: >=95% detected in >=18 of the 20 target
      populations with a best gap under 12pp. Those cost transcript budget and tell you
      nothing about location - Grm7 is the worst case at 100% in 20/20 with a 3.0pp gap
      and 2.3% of the whole panel's predicted transcript load.
  (b) detected in >=50% of cells somewhere in ORBm/BMAp, so the level is readable, AND
  (c) informative about WHERE it sits: a gap >=20pp against neighbouring populations or
      sub-populations, with >=50% of the cells in that sub-population carrying it and
      >=300 cells in it.
A receptor that fails (c) but is a named drug target is reported separately rather than
added silently, because "we could not see where it is" is a real limitation.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path(r"c:\Users\hsollim\Downloads")
DST = OUT / "GPCR_SWEEP.xlsx"

spec = importlib.util.spec_from_file_location("b", V3 / "E_Planning" /
                                              "build_panel_v9_minimal.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

# Mouse GPCR symbol families. Htr3 is excluded on purpose: it is a ligand-gated ion
# channel, not a GPCR. Ramp/Fzd/Smo/Celsr/Lgr are left out as accessory or
# developmental rather than the druggable neuromodulator set this panel is about.
PAT = re.compile(
    r"^(Adra\d|Adrb\d|Adora\d|Adgr[a-l]\d|Agtr\d|Avpr\d|Brs3|Calcr|Calcrl|Cckar|Cckbr|"
    r"Chrm\d|Cnr\d|Crhr\d|Drd\d|Ednra|Ednrb|F2r|Ffar\d|Gabbr\d|Galr\d|Gcgr|Ghsr|Gipr|"
    r"Glp\dr|Gnrhr|Gpbar1|Gpr\d+|Gpr[a-z]+\d*|Grm\d|Hcar\d|Hcrtr\d|Hrh\d|Htr[124567]|"
    r"Kiss1r|Lpar\d|Mc\dr|Mchr\d|Mlnr|Npbwr\d|Npffr\d|Npsr1|Npy\dr|Ntsr\d|Opn\d|"
    r"Oprd1|Oprk1|Oprl1|Oprm1|Oxer1|Oxgr1|Oxtr|P2ry\d+|Pth\dr|Ptger\d|Ptgdr|Ptgfr|"
    r"Ptgir|Prlhr|Prokr\d|Qrfpr|Rxfp\d|S1pr\d|Sctr|Sstr\d|Taar\d|Tacr\d|Tbxa2r|Trhr|"
    r"Tshr|Vipr\d|Adcyap1r1|Ackr\d|Cmklr1|Cysltr\d|Ccr\d|Cxcr\d|C3ar1|C5ar\d|Mrgpr[a-z]+)$")


def main() -> None:
    z, gsym, gi = b.load_cache()
    ac = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                       "ANCHOR_COVERAGE")
    reg = dict(zip(ac.allen_subclass_anchor, ac.region))
    names = [str(x) for x in z["anchor_names"]]
    anchors = [str(x) for x in z["sup_keys"]]
    orb = [i for i, a in enumerate(names) if reg.get(a) == "ORBm"]
    bma = [i for i, a in enumerate(names) if reg.get(a) == "BMAp"]

    universe = sorted({g for g in gsym if PAT.match(g)})
    print(f"GPCR symbols found on the Allen gene axis: {len(universe)}")

    s = b.score_genes(universe, z, gi, names, orb, bma, anchors)
    s = s[s.scored == True].copy()
    s["best_gap"] = s[["subclass_gap_pp", "supertype_gap_pp"]].max(axis=1)

    drugs = pd.read_csv(V3 / "inputs" / "gpcr_drug_targets.csv")
    named = set(drugs.gene_symbol.astype(str))
    detail = pd.read_csv(V3 / "inputs" / "gpcr_drug_targets_detailed.csv")
    ndrug = detail.groupby("gene_symbol").drug_name.nunique()
    s["drug_target"] = s.gene.isin(named)
    s["n_drugs_iuphar"] = s.gene.map(ndrug).fillna(0).astype(int)

    jesse = set()
    p = (V3 / "inputs" / "Jesse_ORB" /
         "OpioidDependenceDEG_genesets_forHansol090926" / "mPFC_GPCRDEGs.csv")
    if p.exists():
        jesse = set(pd.read_csv(p).iloc[:, 0].astype(str))
    s["jesse_morphine_DEG"] = s.gene.isin(jesse)

    s["ubiquitous_no_contrast"] = ((s.anchor_max_pct >= 95) & (s.n_anchors_ge50 >= 18)
                                   & (s.best_gap < 12))
    s["visible"] = s.anchor_max_pct >= 50
    s["localises"] = ((s.best_gap >= 20)
                      & (s.supertype_gap_pct_in.fillna(0) >= 50)
                      & (s.supertype_n_cells.fillna(0) >= 300)) | (s.subclass_gap_pp >= 20)
    s["PASS"] = ~s.ubiquitous_no_contrast & s.visible & s.localises

    v11 = pd.read_excel(DL / "PANEL_FINAL_v11_ORBm_BMAp_LEAN.xlsx", "FINAL_GENE_LIST")
    mine = pd.read_excel(DL / "FINAL_PANEL_243genes_ORBm_BMAp.xlsx", "PANEL_ORDER")
    s["on_v11"] = s.gene.isin(set(v11.gene))
    s["on_v9_243"] = s.gene.isin(set(mine.gene))

    cols = ["gene", "anchor_max_pct", "n_anchors_ge50", "max_pct_ORBm", "max_pct_BMAp",
            "best_gap", "subclass_gap_pp", "supertype_gap_pp", "supertype_gap_pct_in",
            "supertype_n_cells", "supertype", "drug_target", "n_drugs_iuphar",
            "jesse_morphine_DEG", "ubiquitous_no_contrast", "visible", "localises",
            "PASS", "on_v9_243", "on_v11"]
    s = s[cols].sort_values(["PASS", "anchor_max_pct"], ascending=[False, False])

    p_ = s[s.PASS]
    add = p_[~p_.on_v9_243]
    drop = s[s.on_v9_243 & ~s.PASS]
    seen_no_loc = s[s.visible & ~s.ubiquitous_no_contrast & ~s.localises
                    & s.drug_target & ~s.on_v9_243]

    with pd.ExcelWriter(DST) as xw:
        s.to_excel(xw, sheet_name="all_GPCRs_scored", index=False)
        p_.to_excel(xw, sheet_name="PASS", index=False)
        add.to_excel(xw, sheet_name="ADD_to_v9", index=False)
        drop.to_excel(xw, sheet_name="on_v9_but_fails", index=False)
        seen_no_loc.to_excel(xw, sheet_name="visible_but_no_location", index=False)

    pd.set_option("display.width", 300)
    print(f"\nscored {len(s)} receptors | PASS {len(p_)} | "
          f"already on v9 {int(p_.on_v9_243.sum())} | new {len(add)}")
    print(f"\nNOMINATED FOR ADDITION ({len(add)}):")
    print(add[["gene", "anchor_max_pct", "best_gap", "supertype_gap_pct_in",
               "supertype_n_cells", "drug_target", "n_drugs_iuphar",
               "jesse_morphine_DEG", "on_v11"]].to_string(index=False))
    print(f"\nON v9 BUT FAILS THE SWEEP ({len(drop)}):")
    print(drop[["gene", "anchor_max_pct", "best_gap", "ubiquitous_no_contrast",
                "visible", "drug_target"]].to_string(index=False))
    print(f"\nVISIBLE DRUG TARGETS WE CANNOT LOCALISE ({len(seen_no_loc)}) - reported, "
          f"not added:")
    print(seen_no_loc[["gene", "anchor_max_pct", "best_gap", "supertype_gap_pct_in",
                       "supertype_n_cells", "on_v11"]].to_string(index=False))
    print("\nwrote", DST)


if __name__ == "__main__":
    main()
