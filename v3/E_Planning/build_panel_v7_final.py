"""Build v7: the scientifically-optimal ORBm/BMAp panel, budget ignored.

Corrections to v6 (232), each measured against the 79 subclasses actually present
in PL-ILA-ORB + sAMY (226,455 cells), not against the 20 neuronal anchors.

WHY SECTION-WIDE: v5/v6 scored every gene as "max pct across the 20 anchor
subclasses". For a gene whose population is not an anchor that number is
meaningless. Cx3cr1 read 15 pct (measured in neurons) but is 100 pct in
microglia; Pnoc read 44 pct but is 95 pct in CEA-BST Gal Avp Gaba. That is the
same category error the IEG exemption exists to avoid, applied to non-neuronal
and sparse-interneuron markers.

CUT ubiquitous genes with no mechanistic hypothesis: detected in >= 45 of the 79
subclasses AND not on one of the six named axes. A gene present in nearly every
cell can only report a global shift, which the pseudobulk DEG list already
reported; it cannot localise one. Exempt: anything on a named axis.

ADD the modules the SOW needs and v6 cannot deliver: circadian phase (v6 had
Per1/Per2/Bhlhe40 - two Per genes cannot phase-call), sex identity (the
both-sexes design had no in-situ sex verification), pericyte (the only section
population with no marker on base or custom), plus identity/GPCR/plasticity
genes verified specific here.

KEEP, against the review that produced the 178-gene IDEAL list: Gabbr2 (GABA-B
is an obligate GABBR1+GABBR2 heterodimer; GABBR1 alone is ER-retained and
non-functional), Nos1 (99.7 pct in MEA Otp Foxp2 Glut, and the Berg/Scherrer
recommendation column separated it from Rbms3 and Pnoc), Pnoc (95.4 pct in
CEA-BST Gal Avp Gaba, and it is the OPRL1 ligand while OPRL1 is on the panel),
Ep300 (the CREB coactivator; keeping Creb1 for the pCREB axis while cutting the
coactivator that is actually morphine-DE is inconsistent), Sox8 (the only
OPC-specific marker on the custom list).

Non-neuronal coverage is NOT purchased: the 248-gene base panel already carries
Siglech/Trem2/Laptm5 (immune), Acsbg1/Ntsr2 (astrocyte), Gjc3/Sox10/Gpr17
(oligo-lineage), Cldn5/Ly6a/Adgrl4 (endothelial), Col1a1/Aldh1a2 (VLMC),
Pln/Acta2 (SMC). Documented in NONNEURONAL_FREE, not ordered.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
SRC = O / "PANEL_FINAL_v6_ORBm_BMAp_complete.xlsx"
DST = O / "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx"
SEC = Path(r"C:\Users\hsollim\AppData\Local\Temp\claude\C--Users-hsollim"
           r"\d9d2f7d7-37db-459c-ab55-2ce00b74d007\scratchpad\section_subclass_pct.npz")
UBIQ = 45
# The ubiquity cut applies ONLY to the DEG-expansion blocks. A first pass applied it
# panel-wide and deleted Grin1/Gria1-4/Camk2a/Dlg4/Nlgn1/Nrxn1/Syn1/Syp/Gphn - which is
# the same category error: for a plasticity or TF gene the readout is the LEVEL per cell
# type, so being present in every neuron is the point, not a defect. Marker gap only
# matters for genes whose job is to identify a population.
CUT_BLOCKS = ("16_expanded_morphine_state", "18_expanded_BMAp")
# Exempt inside those blocks: a named-axis function beyond "it appeared in a DEG list".
CUT_EXEMPT = {
    "Arid5b": "transcription factor; DE in 8 of 12 ORBm anchors and the only one reaching GABA",
    "Ep300": "pCREB-axis coactivator (see KEEP)",
    "Camk2g": "CaMKII-gamma, a plasticity effector; the only DOWN gene in Jesse's core set",
}

KEEP = {
    "Ep300": "pCREB axis coactivator, morphine-DE in 4/12 ORBm anchors (Up); Creb1 itself is not DE",
    "Gabbr2": "GABA-B obligate heterodimer partner; GABBR1 alone is ER-retained and non-functional",
    "Nos1": "nNOS interneuron marker, 99.7 pct in 120 MEA Otp Foxp2 Glut",
    "Pnoc": "prepronociceptin, the OPRL1 ligand; 95.4 pct in 077 CEA-BST Gal Avp Gaba",
    "Sox8": "the only OPC-specific marker on the custom list (86 pct in OPC, +12pp gap)",
}

ADD = [
    ("Clock", "20_circadian", "core clock, positive limb",
     "CLOCK:BMAL1 heterodimer drives the positive limb. The SOW names clock genes as an axis of IT/CT reprogramming."),
    ("Npas2", "20_circadian", "core clock, forebrain CLOCK paralog",
     "NPAS2 substitutes for CLOCK in forebrain, so it is the relevant positive-limb factor in ORBm."),
    ("Arntl", "20_circadian", "core clock, BMAL1",
     "Obligate CLOCK/NPAS2 partner. Without it the positive limb cannot be read at all."),
    ("Cry2", "20_circadian", "core clock, negative limb",
     "The repressor arm. With only Per1/Per2 the loop has no measured repressor."),
    ("Per3", "20_circadian", "core clock, third Per",
     "Completes the Per family so a phase can be fitted rather than guessed from two genes."),
    ("Nr1d2", "20_circadian", "Rev-erb-beta",
     "Nuclear-receptor arm, opposes ROR at RORE sites. Highest-detection Rev-erb in this section."),
    ("Dbp", "20_circadian", "highest-amplitude clock output",
     "The standard phase-marker transcript. Its low mean detection IS the rhythm, not poor probe "
     "performance - the same exemption the IEGs get."),
    ("Bhlhe41", "20_circadian", "DEC2",
     "Pairs with Bhlhe40, which is already free on base AND a Jesse morphine DEG."),
    ("Xist", "21_sex_identity", "X-inactivation transcript",
     "The SOW mandates both sexes and a dedicated sex-difference analysis; the panel had no way to "
     "verify sex in situ."),
    ("Eif2s3y", "21_sex_identity", "Y-linked",
     "Highest-detection Y transcript here (76.9 pct)."),
    ("Ddx3y", "21_sex_identity", "Y-linked, redundancy",
     "Second Y gene so a sex call survives dropout of either probe."),
    ("Rgs5", "22_pericyte", "pericyte marker",
     "Pericytes are the ONLY population in the section with no marker on the base panel or on v6. "
     "99.7 pct in 331 Peri NN."),
    ("Vtn", "22_pericyte", "pericyte, second marker",
     "98.5 pct in 331 Peri NN; confirms Rgs5 rather than resting on a single probe."),
    ("Slc30a3", "23_identity", "pan-IT / cortical identity",
     "100 pct at its best population and restricted to 13 of 79 subclasses - specific, and canonical "
     "for IT neurons."),
    ("Sulf1", "23_identity", "IT EP-CLA identity",
     "94.1 pct in 002 IT EP-CLA Glut, only 9 of 79 subclasses."),
    ("Lhx9", "23_identity", "amygdalar identity",
     "79.1 pct in 114 COAa-PAA-MEA Barhl2 Glut, 5 of 79 subclasses. Directly BMAp-relevant."),
    ("Adra2a", "24_GPCR_map", "alpha-2A adrenergic",
     "Lofexidine, the FDA-approved opioid-withdrawal drug, acts here. The panel had no alpha-2 "
     "receptor at all."),
    ("Htr1a", "24_GPCR_map", "5-HT1A",
     "Major serotonergic autoreceptor and drug target. 63 pct is accepted on the same pharmacology "
     "exemption as Oprk1."),
    ("Grm2", "24_GPCR_map", "mGlu2 presynaptic autoreceptor",
     "NOT covered by Grm3: Grm3 peaks in 319 Astro-TE NN (98.8 pct), i.e. astrocytic, while Grm2 is "
     "neuronal. Different cells, not a substitute."),
    ("Galr1", "24_GPCR_map", "galanin receptor 1",
     "87.7 pct in 077 CEA-BST Gal Avp Gaba, 1 of 79 subclasses - a specific BMAp-adjacent receptor."),
    ("Ntrk3", "25_plasticity", "TrkC",
     "Pairs with Ntrk2/TrkB already on the panel, giving the neurotrophin readout a single Bdnf probe "
     "cannot."),
    ("Lrrtm2", "25_plasticity", "excitatory synapse organiser",
     "Required for AMPA-receptor retention at synapses. 97.9 pct detected."),
    ("Nrxn3", "25_plasticity", "neurexin-3",
     "Presynaptic organiser; the v6 plasticity block was postsynaptic only."),
    ("Arhgap32", "25_plasticity", "p250GAP",
     "NMDA-receptor-associated Rho GAP, the structural-plasticity effector. 100 pct detected."),
    ("Cdh8", "25_plasticity", "cadherin-8",
     "Adhesive specification of synapses. 98.7 pct detected."),
    ("Pcdh8", "25_plasticity", "arcadlin, activity-regulated cadherin",
     "Activity-induced and adhesion-linked, so it bridges the IEG and plasticity axes."),
    ("Pak1", "25_plasticity", "PAK1 kinase",
     "Spine actin remodelling downstream of Rac1. 100 pct detected."),
]

# --- orphan resolution -------------------------------------------------------------
# These sat in ORBm_ORDER / BMAp_ORDER but never in SHARED_PANEL_ORDER, so they would
# never have been manufactured. Scored section-wide, these seven earn a slot.
ORPHAN_ADD = [
    ("Esr1", "23_identity", "estrogen receptor alpha",
     "92.8 pct in 077 CEA-BST Gal Avp Gaba, 13 of 79 subclasses. The SOW mandates a sex-difference "
     "analysis and this is the receptor that mediates it; it was in BMAp_ORDER but not in "
     "SHARED_PANEL_ORDER, so it would never have been made."),
    ("Adcyap1", "24_GPCR_map", "PACAP, the ADCYAP1R1 ligand",
     "88.1 pct in 026 NLOT Rho Glut, 10 of 79 subclasses. Stress-peptide ligand with a strong "
     "amygdala literature; pairs with the receptor map."),
    ("P2ry12", "26_nonneuronal_state", "microglial homeostatic-state readout",
     "99.6 pct in 334 Microglia NN, only 2 of 79 subclasses. Not redundant with the free Siglech/Trem2: "
     "those identify microglia, P2ry12 is downregulated on activation so it reports STATE."),
    ("Chat", "27_cholinergic", "choline acetyltransferase",
     "84.4 pct in 058 PAL-STR Gaba-Chol, 1 of 79 subclasses - i.e. specific, not weak. v5 cut it on "
     "the anchor-only 50 pct bar, which is exactly the Cx3cr1 error: cholinergic cells are not one "
     "of the 20 anchors."),
    ("Slc5a7", "27_cholinergic", "high-affinity choline transporter",
     "88.8 pct in 058 PAL-STR Gaba-Chol, 1 of 79 subclasses. Confirms Chat rather than resting on one probe."),
    ("Ddc", "27_cholinergic", "DOPA decarboxylase",
     "66.8 pct in 079 CEA-BST Six3 Cyp26b1 Gaba, 5 of 79 subclasses. Monoamine-synthesis capacity."),
    ("St8sia2", "25_plasticity", "polysialyltransferase (PSA-NCAM)",
     "72.8 pct in 133 PVH-SO-PVa Otp Glut, 3 of 79 subclasses. PSA-NCAM is the classical permissive "
     "signal for structural plasticity."),
]
# Orphans deliberately left out, and removed from the region sheets so the sheets are honest:
ORPHAN_DROP = {
    "EGFP": "no AAV in this design - nothing to report",
    "Slc17a8": "VGLUT3, 44.4 pct and 0 of 79 subclasses above 50 pct",
    "Vegfd": "70 pct but no named axis; a growth factor with no hypothesis here",
    "Cd36": "69.6 pct, best in BAM - immune is already covered free by Siglech/Trem2/Laptm5/Cd53",
    "Slc18a2": "VMAT2, 34.4 pct and 0 of 79 subclasses above 50 pct",
    "Tgfb2": "66.7 pct, best in SMC - SMC already covered free by Pln/Acta2",
}

FREE_NN = [
    ("Siglech", "Microglia", 98, 45), ("Trem2", "Microglia", 94, 29),
    ("Laptm5", "Immune", 99, 95), ("Cd53", "Immune", 91, 88), ("Ikzf1", "Immune", 94, 92),
    ("Acsbg1", "Astrocyte", 95, 81), ("Ntsr2", "Astrocyte", 98, 71),
    ("Gjc3", "Oligo-lineage", 96, 91), ("Sox10", "Oligo-lineage", 96, 85),
    ("Gpr17", "OPC", 98, 81), ("Opalin", "Oligo", 79, 75),
    ("Cldn5", "Endothelial", 99, 96), ("Ly6a", "Endothelial", 94, 93),
    ("Adgrl4", "Endothelial", 99, 89),
    ("Col1a1", "VLMC", 95, 85), ("Aldh1a2", "VLMC", 87, 79),
    ("Pln", "SMC", 86, 71), ("Acta2", "SMC", 96, 51),
    ("Lyz2", "BAM", 100, 71), ("Cd68", "BAM", 87, 34),
]


def main() -> None:
    z = np.load(SEC, allow_pickle=True)
    P = z["pct"]
    L = [str(x) for x in z["labels"]]
    G = [str(x) for x in z["genes"]]
    gi = {g: i for i, g in enumerate(G)}

    def stat(g):
        j = gi.get(g)
        if j is None:
            return (float("nan"), "", 0)
        v = P[:, j]
        k = int(np.argmax(v))
        return (float(v[k]), L[k], int((v >= 50).sum()))

    base = set(pd.read_csv(O / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    sh = pd.read_excel(SRC, "SHARED_PANEL_ORDER")
    ac = pd.read_excel(SRC, "ANCHOR_COVERAGE")
    sep = set()
    for s in ac.unique_separators_on_shared_panel.fillna(""):
        sep |= {x.strip() for x in s.split(",") if x.strip()}

    rows = []
    for r in sh.itertuples():
        g = str(r.gene)
        mx, best, nsub = stat(g)
        blk = str(getattr(r, "block", ""))
        eligible = blk in CUT_BLOCKS and g not in CUT_EXEMPT and g not in KEEP \
            and g not in sep and g not in base
        rows.append({"gene": g, "block": blk, "sec_max_pct": mx, "sec_best_subclass": best,
                     "n_subclasses_ge50": nsub, "cut": bool(eligible and nsub >= UBIQ)})
    d = pd.DataFrame(rows)
    cut = d[d.cut]
    print(f"v6 = {len(d)} genes; DEG-expansion genes that are ubiquitous "
          f"and carry no axis function: {len(cut)}")
    print(cut[["gene", "block", "sec_max_pct", "n_subclasses_ge50"]]
          .sort_values("n_subclasses_ge50", ascending=False).to_string(index=False))
    print("  exempted inside those blocks: "
          + ", ".join(f"{g} ({stat(g)[2]}/79)" for g in list(CUT_EXEMPT) + list(KEEP)
                      if g in set(d.gene)))
    cutset = set(cut.gene)

    shutil.copy2(SRC, DST)
    wb = load_workbook(DST)
    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        gc = [c.value for c in ws[1]].index("gene") + 1
        rr = [i for i in range(2, ws.max_row + 1) if ws.cell(row=i, column=gc).value in cutset]
        for i in reversed(rr):
            ws.delete_rows(i)
        print(f"  {name}: removed {len(rr)}")

    # remove the orphans we are not taking, from the region sheets where they hid
    for name in ("ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        gc = [c.value for c in ws[1]].index("gene") + 1
        rr = [i for i in range(2, ws.max_row + 1) if ws.cell(row=i, column=gc).value in ORPHAN_DROP]
        for i in reversed(rr):
            ws.delete_rows(i)
        print(f"  {name}: dropped {len(rr)} un-manufacturable orphans")

    shw, orbw, bmaw = wb["SHARED_PANEL_ORDER"], wb["ORBm_ORDER"], wb["BMAp_ORDER"]
    present = {shw.cell(row=i, column=2).value for i in range(2, shw.max_row + 1)}
    added = []
    for g, blk, role, why in ADD + ORPHAN_ADD:
        if g in present:
            print(f"  skip {g}: already on v6")
            continue
        mx, best, nsub = stat(g)
        txt = (f"{why} Section-wide: detected in {mx:.1f} pct of {best}, and in >=50 pct of cells "
               f"in {nsub} of the 79 subclasses present in PL-ILA-ORB + sAMY.")
        for ws in (shw, orbw, bmaw):
            # ORPHAN_ADD genes are already in a region sheet - that is what made them
            # orphans. Only write where the gene is actually absent, or we duplicate.
            gc = [c.value for c in ws[1]].index("gene") + 1
            if any(ws.cell(row=i, column=gc).value == g for i in range(2, ws.max_row + 1)):
                continue
            i = ws.max_row + 1
            ws.cell(row=i, column=2, value=g)
            ws.cell(row=i, column=3, value=blk)
            ws.cell(row=i, column=4, value=f"{role} :: {mx:.0f} pct detected")
            if ws.max_column >= 5:
                ws.cell(row=i, column=5, value=txt)
        present.add(g)
        added.append((g, blk, role, round(mx, 1), best, nsub))

    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        for i, rw in enumerate(range(2, ws.max_row + 1), start=1):
            ws.cell(row=rw, column=1, value=i)
    wb.save(DST)

    with pd.ExcelWriter(DST, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        pd.DataFrame(added, columns=["gene", "block", "role", "sec_max_pct",
                                     "sec_best_subclass", "n_subclasses_ge50"]
                     ).to_excel(w, "ADDED_v7", index=False)
        cut[["gene", "block", "sec_max_pct", "sec_best_subclass", "n_subclasses_ge50"]
            ].to_excel(w, "CUT_v7", index=False)
        pd.DataFrame([{"gene": g, "kept_because": r, "sec_max_pct": round(stat(g)[0], 1),
                       "sec_best_subclass": stat(g)[1], "n_subclasses_ge50": stat(g)[2]}
                      for g, r in KEEP.items()]).to_excel(w, "KEPT_vs_IDEAL178", index=False)
        pd.DataFrame(FREE_NN, columns=["gene", "population", "pct_in_population", "gap_pp"]).assign(
            note="already on the 248-gene base panel: free, measured, costs no custom slot"
        ).to_excel(w, "NONNEURONAL_FREE", index=False)
        pd.DataFrame([{"gene": g, "dropped_because": r, "sec_max_pct": round(stat(g)[0], 1),
                       "sec_best_subclass": stat(g)[1], "n_subclasses_ge50": stat(g)[2]}
                      for g, r in ORPHAN_DROP.items()]).to_excel(w, "ORPHANS_DROPPED", index=False)

    out = pd.read_excel(DST, "SHARED_PANEL_ORDER")
    o = pd.read_excel(DST, "ORBm_ORDER")
    b = pd.read_excel(DST, "BMAp_ORDER")
    free = int(out.gene.isin(base).sum())
    print(f"\n{DST.name}")
    print(f"  {len(out)} genes = {free} free(base) + {len(out) - free} custom")
    print(f"  dupes {int(out.gene.duplicated().sum())} | ORBm {len(o)} orphans "
          f"{len(set(o.gene) - set(out.gene))} | BMAp {len(b)} orphans "
          f"{len(set(b.gene) - set(out.gene))}")
    print(f"  separators retained {len(sep & set(out.gene))}/{len(sep)}")
    st = [stat(g) for g in out.gene]
    print(f"  section-wide median detect {np.nanmedian([s[0] for s in st]):.1f} pct | "
          f"<50 pct: {sum(1 for s in st if s[0] < 50)}")


if __name__ == "__main__":
    main()
