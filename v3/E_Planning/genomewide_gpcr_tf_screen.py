"""Genome-wide GPCR and TF screen for ORBm and BMAp - the gap the 297-gene panel had.

WHY THIS EXISTS. The 32,285-gene screen behind the panel was run for CELL-TYPE MARKERS
only (JOB 2). The profiling half of the panel - 42 GPCRs, 13 TFs, 30 plasticity, 19 IEG,
46 morphine genes - was never selected from the genome. It came from Jesse Niehaus's mPFC
DEG lists, a GPCR drug-target CSV holding only 38 distinct genes, and content inherited
from earlier panel versions. Nobody had asked "of all the mouse GPCRs, which are actually
expressed in PL-ILA-ORB and sAMY?" So those blocks were a convenience sample, and the
claim "this panel is the biological optimum" could not be made.

This screens every curated mouse GPCR and TF against the measured atlas and asks three
questions:
  1 EXPRESSED    does it clear 50% of cells anywhere in the section (rule R2)?
  2 INFORMATIVE  is it cell-type restricted, or flat across all 79 subclasses?
  3 ON PANEL     if it is a strong hit and we do not have it, that is a miss.

Two different verdicts matter and must not be conflated:
  - A receptor that is expressed but FLAT is still worth having: you read its LEVEL inside
    a cell type you named some other way. Flatness is not a defect for JOB 3.
  - A receptor that clears 50% NOWHERE is an empty map and should not be ordered, unless
    it is core opioid pharmacology where absence is itself the readout.

Outputs outputs/GENOMEWIDE_GPCR_TF_SCREEN.xlsx:
  gpcr_all / tf_all      every curated gene, measured, ranked, with on-panel flag
  gpcr_misses/tf_misses  strong hits absent from the 297-gene panel  <- the actionable part
  gpcr_empty/tf_empty    genes ON the panel that clear 50% nowhere   <- candidates to drop
  family_coverage        per receptor/TF family: how many exist, how many we carry
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
SEC = Path(r"C:\Users\hsollim\AppData\Local\Temp\claude\C--Users-hsollim"
           r"\d9d2f7d7-37db-459c-ab55-2ce00b74d007\scratchpad\section_subclass_pct.npz")
PANEL = Path(r"C:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_297genes.xlsx")
LISTS = O / "_gpcr_tf_curated.json"
DST = O / "GENOMEWIDE_GPCR_TF_SCREEN.xlsx"

EXPRESSED = 50.0      # R2: must clear this somewhere in ORBm/BMAp
RESTRICTED = 45        # of 79 subclasses; at or above this the gene is "flat"
OPIOID_CORE = {"Oprm1", "Oprd1", "Oprk1", "Oprl1"}

# family assignment, longest prefix wins; used only for coverage reporting
FAM = [
    ("Adgr", "adhesion"), ("Celsr", "adhesion"), ("Adora", "adenosine"),
    ("Adra", "adrenergic"), ("Adrb", "adrenergic"), ("Chrm", "muscarinic"),
    ("Drd", "dopamine"), ("Htr", "serotonin"), ("Hrh", "histamine"),
    ("Taar", "trace amine"), ("Opr", "opioid"), ("Npy", "neuropeptide Y"),
    ("Galr", "galanin"), ("Sstr", "somatostatin"), ("Tacr", "tachykinin"),
    ("Avpr", "vasopressin/oxytocin"), ("Oxtr", "vasopressin/oxytocin"),
    ("Crhr", "CRF"), ("Mc", "melanocortin"), ("Hcrtr", "orexin"),
    ("Mchr", "MCH"), ("Rxfp", "relaxin"), ("Grm", "metabotropic glutamate"),
    ("Gabbr", "GABA-B"), ("Gprc", "class C orphan"), ("Casr", "class C other"),
    ("Fzd", "frizzled"), ("Smo", "frizzled"), ("Lgr", "frizzled"),
    ("P2ry", "purinergic"), ("Lpar", "lipid"), ("S1pr", "lipid"),
    ("Cnr", "cannabinoid"), ("Ffar", "lipid"), ("Hcar", "lipid"),
    ("Ptge", "prostanoid"), ("Ptgd", "prostanoid"), ("Ptgf", "prostanoid"),
    ("Ptgi", "prostanoid"), ("Tbxa", "prostanoid"), ("Ccr", "chemokine"),
    ("Cxcr", "chemokine"), ("Cx3cr", "chemokine"), ("Ackr", "chemokine"),
    ("Vipr", "secretin-like"), ("Adcyap1r", "secretin-like"), ("Glp", "secretin-like"),
    ("Gipr", "secretin-like"), ("Gcgr", "secretin-like"), ("Calcr", "secretin-like"),
    ("Pth", "secretin-like"), ("Sctr", "secretin-like"), ("Ghrhr", "secretin-like"),
    ("Gpr", "orphan Gpr"),
    # TF families
    ("Fox", "forkhead"), ("Sox", "SOX"), ("Hox", "homeodomain"), ("Lhx", "homeodomain"),
    ("Dlx", "homeodomain"), ("Nkx", "homeodomain"), ("Pou", "homeodomain"),
    ("Pitx", "homeodomain"), ("Otx", "homeodomain"), ("Six", "homeodomain"),
    ("Isl", "homeodomain"), ("Meis", "homeodomain"), ("Pbx", "homeodomain"),
    ("Onecut", "homeodomain"), ("Cux", "homeodomain"), ("Satb", "homeodomain"),
    ("Emx", "homeodomain"), ("Barhl", "homeodomain"),
    ("Zfp", "C2H2 zinc finger"), ("Zbtb", "C2H2 zinc finger"),
    ("Zscan", "C2H2 zinc finger"), ("Zkscan", "C2H2 zinc finger"),
    ("Zic", "C2H2 zinc finger"), ("Klf", "C2H2 zinc finger"),
    ("Egr", "C2H2 zinc finger"), ("Prdm", "C2H2 zinc finger"),
    ("Gli", "C2H2 zinc finger"), ("Sall", "C2H2 zinc finger"),
    ("Bcl11", "C2H2 zinc finger"), ("Ikzf", "C2H2 zinc finger"),
    ("Neurod", "bHLH"), ("Neurog", "bHLH"), ("Ascl", "bHLH"), ("Olig", "bHLH"),
    ("Hes", "bHLH"), ("Hey", "bHLH"), ("Bhlhe", "bHLH"), ("Npas", "bHLH"),
    ("Id", "bHLH"), ("Tcf", "bHLH/TCF"), ("Myc", "bHLH"), ("Mitf", "bHLH"),
    ("Jun", "bZIP"), ("Fos", "bZIP"), ("Atf", "bZIP"), ("Creb", "bZIP"),
    ("Maf", "bZIP"), ("Cebp", "bZIP"), ("Bach", "bZIP"), ("Nfe2", "bZIP"),
    ("Nr", "nuclear receptor"), ("Esr", "nuclear receptor"), ("Rar", "nuclear receptor"),
    ("Rxr", "nuclear receptor"), ("Ppar", "nuclear receptor"), ("Ror", "nuclear receptor"),
    ("Thr", "nuclear receptor"), ("Tbx", "T-box"), ("Ets", "ETS"), ("Etv", "ETS"),
    ("Elk", "ETS"), ("Elf", "ETS"), ("Runx", "RUNX"), ("Stat", "STAT"),
    ("Smad", "SMAD"), ("Irf", "IRF"), ("Rel", "NF-kB"), ("Nfk", "NF-kB"),
    ("Nfat", "NFAT"), ("Mef2", "MEF2"), ("Tead", "TEAD"), ("Rfx", "RFX"),
    ("Gata", "GATA"), ("Tfap2", "AP-2"), ("Nfi", "NFI"), ("Sp", "SP"),
]


def family(g: str) -> str:
    best = ""
    lab = "other"
    for pre, name in FAM:
        if g.startswith(pre) and len(pre) > len(best):
            best, lab = pre, name
    return lab


def main() -> None:
    if not LISTS.exists():
        sys.exit(f"missing {LISTS} - write the curated lists there first as "
                 '{"gpcr": [...], "tf": [...]}')
    cur = json.loads(LISTS.read_text())
    z = np.load(SEC, allow_pickle=True)
    P = z["pct"]
    L = [str(x) for x in z["labels"]]
    G = [str(x) for x in z["genes"]]
    N = z["n"]
    gi = {g: i for i, g in enumerate(G)}
    panel = set(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str))
    pblock = dict(zip(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str),
                      pd.read_excel(PANEL, "SHARED_PANEL_ORDER").block.astype(str)))

    out = {}
    for kind in ("gpcr", "tf"):
        rows = []
        for g in sorted(set(cur[kind])):
            j = gi.get(g)
            if j is None:
                rows.append({"gene": g, "in_atlas": False, "family": family(g),
                             "on_panel_297": g in panel, "panel_block": pblock.get(g, "")})
                continue
            v = P[:, j]
            k = int(np.argmax(v))
            o = float(np.delete(v, k).max())
            nsub = int((v >= EXPRESSED).sum())
            rows.append({
                "gene": g, "in_atlas": True, "family": family(g),
                "max_pct": round(float(v[k]), 1), "top_subclass": L[k],
                "top_n_cells": int(N[k]), "gap_pp": round(float(v[k]) - o, 1),
                "n_subclasses_ge50": nsub,
                "expressed": bool(v[k] >= EXPRESSED),
                "cell_type_restricted": bool(nsub < RESTRICTED),
                "on_panel_297": g in panel, "panel_block": pblock.get(g, ""),
            })
        d = pd.DataFrame(rows)
        for c in ("expressed", "cell_type_restricted", "on_panel_297"):
            d[c] = d[c].fillna(False).astype(bool)
        # A hit whose top population is non-neuronal is NOT actionable: the design
        # deliberately carries only Aqp4 + Siglech for glia/vascular, because with no
        # non-neuronal probes at all, non-neuronal cells are still never called neurons
        # (0.0%) and target-type contamination is 0.01%.
        d["top_is_neuronal"] = ~d.top_subclass.fillna("").str.contains(
            "NN$|Astro|Oligo|OPC|Microglia|VLMC|Peri|Endo|SMC|Epen|BAM", regex=True)
        n_atlas = int(d.in_atlas.sum())
        exp = d[d.expressed]
        print(f"\n=== {kind.upper()}: {len(d)} curated, {n_atlas} in atlas, "
              f"{len(exp)} clear {EXPRESSED:.0f}% somewhere ===")
        print(f"  on the 297 panel: {int(d.on_panel_297.sum())}")
        miss = exp[~exp.on_panel_297].sort_values(["gap_pp", "max_pct"], ascending=False)
        act = miss[miss.cell_type_restricted & miss.top_is_neuronal]
        print(f"  misses, all: {len(miss)} | cell-type-restricted: "
              f"{int(miss.cell_type_restricted.sum())} | of those NEURONAL "
              f"(actionable): {len(act)}")
        print(act.head(22)[
            ["gene", "family", "max_pct", "top_subclass", "gap_pp", "n_subclasses_ge50"]
        ].to_string(index=False))
        flat = miss[~miss.cell_type_restricted]
        print(f"\n  expressed but FLAT and not on panel ({len(flat)}) - legitimate JOB 3 "
              f"candidates, judged on pharmacology not on gap:")
        print(flat.head(12)[["gene", "family", "max_pct", "n_subclasses_ge50"]].to_string(index=False))
        empty = d[d.in_atlas & ~d.expressed & d.on_panel_297]
        print(f"\n  ON PANEL but clears {EXPRESSED:.0f}% NOWHERE: {len(empty)}")
        if len(empty):
            print(empty[["gene", "family", "max_pct", "top_subclass", "panel_block"]]
                  .to_string(index=False))
        fam = (d[d.in_atlas].groupby("family")
               .agg(n_in_atlas=("gene", "size"),
                    n_expressed=("expressed", "sum"),
                    n_on_panel=("on_panel_297", "sum")).reset_index()
               .sort_values("n_expressed", ascending=False))
        out[kind] = (d, miss, empty, fam, act)

    with pd.ExcelWriter(DST, engine="openpyxl") as w:
        pd.DataFrame({"item": ["Question", "Why it was needed", "R2 rule",
                               "Two verdicts", "Caveat"],
                      "detail": [
            "Of all mouse GPCRs and TFs, which are expressed in PL-ILA-ORB / sAMY, and is "
            "the 297-gene panel carrying the right ones?",
            "The 32,285-gene screen behind the panel covered cell-type MARKERS only. The "
            "GPCR/TF/plasticity/IEG/morphine half came from Jesse's mPFC DEG lists, a "
            "38-gene drug-target table and inherited panel content - a convenience sample.",
            f"A profiling gene must clear {EXPRESSED:.0f}% of cells somewhere in the two "
            "regions. Below that the map is empty.",
            "Expressed-but-flat is FINE for a receptor (you read its level in a cell type "
            f"named another way). Flat = detected in >= {RESTRICTED} of 79 subclasses. "
            "Clears 50% nowhere = not orderable, except core opioid receptors where "
            "absence is the readout.",
            "Detection is Allen 10x scRNA-seq log2(CPM+1) > 0, per subclass, in the two "
            "ROIs only. Curated gene lists were built and cross-checked by independent "
            "agents against IUPHAR/GPCRdb and AnimalTFDB/Lambert 2018.",
        ]}).to_excel(w, "READ_ME", index=False)
        for kind in ("gpcr", "tf"):
            d, miss, empty, fam, act = out[kind]
            d.sort_values("gap_pp", ascending=False).to_excel(w, f"{kind}_all", index=False)
            miss.to_excel(w, f"{kind}_misses_all", index=False)
            act.to_excel(w, f"{kind}_misses_ACTIONABLE", index=False)
            empty.to_excel(w, f"{kind}_empty_on_panel", index=False)
            fam.to_excel(w, f"{kind}_family_coverage", index=False)
    print(f"\nwrote {DST}")


if __name__ == "__main__":
    main()
