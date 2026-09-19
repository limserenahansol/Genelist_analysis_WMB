"""Build the final ORBm/BMAp Xenium standalone panel (v8).

Design goal, taken from SOW2 Aim 1: Xenium has to resolve the BMA and ORB
populations that dissociate volitional from yoked-passive seeking at the ~24 h
post-test window, and hand off a 3-5 gene marker panel for rat RNAscope. So the
panel must (a) call cell types AND sub-populations, (b) read the activity /
pCREB / clock state the SOW names, (c) map the GPCRs the SOW names, and
(d) not waste probes on transcripts that are not detectable here.

Two metrics, because the panel does two different jobs (earlier versions used
only the first, which is why low-detection subtype markers were wrongly cut and
low-detection dead probes were wrongly kept):

  identity genes   must SEPARATE: subclass_gap (20 anchors) or supertype_gap
                   (siblings inside one anchor, n>=100 cells)
  state genes      must be VISIBLE: anchor_max_pct over the 20 anchors
  glia/vascular    scored against their own population, never against the
                   20 anchors, which are all neuronal

Inclusion rules, applied in this order:

  R0  TRAP reporters and SOW-named genes are never filtered.
  R1  Subclass unique separators (call the 20 target types) are kept.
  R2  Subtype separators are kept when gap>=25pp, pct_in>=50%, n>=100 cells;
      selected greedily to give every separable supertype >=2 markers.
  R3  Class / E-I backbone and one specific marker per non-neuronal population
      are kept (SOW names E/I balance five times; glia must be excludable).
  R4  GPCRs are kept when anchor_max_pct>=50, or they pass R2, or SOW names them.
  R5  IEG / pCREB-target genes are exempt from the detection bar, because the
      Allen atlas is resting tissue and induction is the measurement. Redundant
      family members are capped.
  R6  Plasticity and TF genes are kept when anchor_max_pct>=50 and the gene has
      a named mechanism.
  R7  Morphine-state genes are kept when they name a mechanism and are visible;
      broad housekeeping DEGs with no interpretable readout are dropped.
  R8  Everything else with anchor_max_pct<50 and no separating power is dropped.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path(r"c:\Users\hsollim\Downloads")
DST = OUT / "PANEL_FINAL_v8_ORBm_BMAp.xlsx"

VIS = 50.0          # anchor detection bar for state genes
SUB_GAP = 25.0      # supertype separation bar
SUB_PCT = 50.0
SUB_N = 100
TARGET_PER_SUPERTYPE = 2

# ---------------------------------------------------------------- R0
TRAP = ["tdTomato", "iCre"]
# Verbatim from SOW2: "immediate-early like Fos and Arc, clock genes like PER2,
# and pCREB-target genes"; "SATB2 identity, FOS, PER2" rat pilot panel;
# "largely mu-opioid-receptor-negative"; "sharing the same GPCRs
# (e.g., beta1-adrenergic, 5-HT2A)".
SOW = {
    "Satb2": "SOW: SATB2 identity, named in the rat RNAscope pilot panel",
    "Fos": "SOW: immediate-early, named; rat pilot panel",
    "Arc": "SOW: immediate-early, named",
    "Per2": "SOW: clock genes like PER2, named; rat pilot panel",
    "Creb1": "SOW: pCREB-target genes - Creb1 anchors the axis",
    "Adrb1": "SOW: beta1-adrenergic, named as a shared-GPCR test",
    "Htr2a": "SOW: 5-HT2A, named as a shared-GPCR test",
    "Oprm1": "SOW: populations are 'largely mu-opioid-receptor-negative' - needs the probe to show it",
}

# ---------------------------------------------------------------- R3
EI_BACKBONE = {
    "Slc17a7": "VGLUT1, cortical excitatory - E/I numerator",
    "Slc17a6": "VGLUT2, subcortical excitatory",
    "Gad1": "GAD67, inhibitory - E/I denominator",
    "Gad2": "GAD65, inhibitory",
    "Slc32a1": "VGAT, obligate GABA/glycine vesicular transporter",
    "Slc6a1": "GAT1, GABA reuptake",
    "Camk2a": "excitatory principal-neuron identity",
    "Pvalb": "fast-spiking interneuron class",
    "Sst": "SST interneuron class",
    "Vip": "VIP interneuron class",
    "Lamp5": "Lamp5 interneuron class",
    "Npy": "NPY interneuron / neuropeptide",
    "Nos1": "nNOS interneuron class; 99.7% in 120 MEA Otp Foxp2 Glut",
    "Calb1": "interneuron/projection subdivision",
    "Calb2": "calretinin subdivision",
}
# One highly specific marker per non-neuronal population, scored on that
# population (NONNEURONAL_scores.xlsx), never on the neuronal anchors.
GLIA = {
    "Gja1": "astrocyte, 99.7% in astro and 8.9% in neurons (+91pp)",
    "Aqp4": "astrocyte end-foot, +91pp over neurons",
    "Pdgfra": "OPC, 99.9% in OPC and 1.3% in neurons (+99pp)",
    "Sox10": "oligodendrocyte lineage, +90pp over neurons",
    "Mog": "mature oligodendrocyte (canonical; Oligo NN cells are absent from the "
           "downloaded shards so this one is literature-based, not measured here)",
    "Csf1r": "microglia, 99.8% in microglia and 1.9% in neurons (+98pp)",
    "Cx3cr1": "microglia, second marker, +89pp over neurons",
    "Cldn5": "endothelial (canonical; Endo NN cells absent from the shards)",
    "Rgs5": "pericyte, 99.7% in pericytes and 5.6% in neurons (+94pp)",
    "Vtn": "pericyte, second marker, +98pp over neurons",
    "Acta2": "smooth muscle, +95pp over neurons",
    "Dcn": "VLMC / meninges, +98pp over neurons",
}
# SABV: SOW commits to "Both sexes included throughout; a dedicated
# sex-difference analysis where the data support it".
SEX_QC = {
    "Xist": "SABV: X-inactivation transcript, sexes the section in situ",
    "Eif2s3y": "SABV: Y-linked confirmation",
}

# ---------------------------------------------------------------- R5
# Canonical activity / pCREB-target set. Exempt from the detection bar.
IEG = {
    "Fos": "AP-1, canonical activity marker",
    "Fosb": "AP-1, longer-lived",
    "Junb": "AP-1 partner",
    "Jun": "AP-1 partner",
    "Jund": "AP-1 partner, constitutive arm",
    "Arc": "activity-regulated cytoskeletal, synaptic scaling",
    "Npas4": "activity-dependent, inhibitory-synapse specific - E/I readout",
    "Egr1": "zif268, pCREB target",
    "Egr2": "Krox20, later-wave IEG",
    "Egr3": "later-wave IEG",
    "Nr4a1": "Nur77, pCREB target",
    "Nr4a2": "Nurr1",
    "Nr4a3": "Nor1",
    "Bdnf": "activity-dependent, pCREB target",
    "Nptx2": "narp, activity-regulated synaptic",
    "Scg2": "secretogranin II, activity-regulated neuropeptide",
    "Vgf": "VGF, activity-regulated neuropeptide, pCREB target",
    "Sgk1": "activity/stress-regulated kinase",
    "Btg2": "PC3/Tis21, IEG",
    "Ier2": "immediate-early response 2",
    "Sik1": "salt-inducible kinase 1, activity-dependent",
    "Dusp1": "MAPK phosphatase, IEG feedback",
    "Crem": "ICER, CREB-family repressor - the pCREB feedback arm",
    "Rgs2": "activity-regulated GPCR signalling brake",
    "Homer1": "Homer1a activity-regulated scaffold",
    "Per1": "pCREB-target clock IEG",
}
# Clock module. SOW names "clock genes like PER2" (plural) but removed the
# dedicated circadian (ZT) cohort, so this is deliberately compact.
CLOCK = {
    "Per2": "SOW-named clock gene; Jesse's top ORB morphine DEG (13 clusters)",
    "Per1": "second Per, pCREB target, Jesse DEG",
    "Arntl": "BMAL1, positive limb",
    "Clock": "CLOCK, positive limb",
    "Cry2": "negative limb",
    "Nr1d2": "Rev-erb-beta, output arm",
    "Bhlhe40": "DEC1, Jesse morphine DEG",
}

# ---------------------------------------------------------------- R6
PLASTICITY = {
    "Gria1": "AMPA GluA1 - the trafficking subunit in opioid plasticity",
    "Gria2": "AMPA GluA2 - Ca permeability switch",
    "Gria3": "AMPA GluA3",
    "Gria4": "AMPA GluA4",
    "Grin1": "NMDA obligatory subunit",
    "Grin2a": "NMDA GluN2A, mature",
    "Grin2b": "NMDA GluN2B, plasticity-permissive",
    "Camk2a": "CaMKII alpha, LTP",
    "Camk2b": "CaMKII beta",
    "Camk2g": "CaMKII gamma, nuclear Ca signalling; Jesse morphine DEG",
    "Syngap1": "Ras-GAP at the PSD",
    "Shank3": "PSD scaffold",
    "Dlg4": "PSD-95",
    "Nlgn1": "neuroligin-1, excitatory synapse",
    "Nrxn1": "neurexin-1",
    "Nrxn3": "neurexin-3",
    "Lrrtm2": "excitatory synapse organiser",
    "Ntrk2": "TrkB, the BDNF receptor",
    "Ntrk3": "TrkC",
    "Arhgap32": "p250GAP, NMDA-linked Rho signalling",
    "Pak1": "PAK1, spine actin",
    "Cdh8": "cadherin-8, synapse specification",
    "Pcdh8": "arcadlin, activity-regulated cadherin",
    "Syp": "synaptophysin, presynaptic load",
    "Syn1": "synapsin I",
    "Syt1": "synaptotagmin-1, release sensor",
    "Gphn": "gephyrin, inhibitory postsynaptic scaffold - E/I readout",
    "Nptx2": "narp, excitatory drive onto PV cells",
}

# ---------------------------------------------------------------- R7
MORPHINE_STATE = {
    "Pcsk1": "PC1/3, proneuropeptide processing; Jesse DEG in 11/12 ORBm clusters",
    "Sema3e": "axon-guidance remodelling; Jesse DEG",
    "Penk": "proenkephalin, opioid-peptide tone",
    "Pdyn": "prodynorphin, kappa arm",
    "Pnoc": "prepronociceptin, the OPRL1 ligand",
    "Tac1": "substance P",
    "Cartpt": "CART, reward peptide",
    "Adcyap1": "PACAP, stress/reward peptide",
    "Crh": "CRF, withdrawal axis",
    "Trh": "TRH",
}
# Jesse DEGs that are broad and housekeeping-like: high detection but no readout
# that can be interpreted in a spatial map. Explicitly not ordered.
DROP_UNINTERPRETABLE = {
    "Chd2", "Fxr1", "Vps13a", "Hspa5", "Ahctf1", "Banp", "Mbnl2", "Acsl4",
    "Zdbf2", "Hsd17b12", "Omg", "Zfp933", "Rbms3", "Maml3", "Maml2", "Zbtb25",
    "Zbtb40", "Zfp580", "Gabpa", "Hsf5", "Sox12", "Stk40", "Nckap5", "Myo1b",
    "Igf1", "Nbl1", "Spon1", "Trpm3", "Zfp804b", "Masp1", "Kitl", "Osgin2",
    "Rel", "Rnf128", "Hunk", "Cdkn1a", "Tiparp", "Ep300", "St8sia2",
}
# Probes with no job here: not detectable at the 20 anchors, no trustworthy
# separation, not SOW, not an IEG, not a glial counter-stain.
FORCE_DROP = {
    "WPRE": "AAV element - this design crosses TRAP2 with a tdTomato reporter, no virus",
    "mCherry": "AAV-DIO-hM4Di-mCherry element - not used in the Xenium cohort",
    "EGFP": "no EGFP transgene in this design",
    "Sstr4": "1.4% of cells at the best anchor, no separation - empty map",
    "Gpr63": "2.7% of cells, no separation - empty map",
    "Htr6": "5.2% of cells, no separation - empty map",
    "Slc6a3": "DAT, 4.6% - no dopaminergic cell bodies in ORBm/BMAp to report",
    "Slc18a2": "VMAT2, 34% and 0 of 20 anchors above 50%",
    "Slc17a8": "VGLUT3, 44% and 0 of 20 anchors above 50%",
    "Chat": "12.2% - no cholinergic cell bodies among the 20 target populations",
    "Slc5a7": "12% as a cholinergic marker, but it is the only qualifying separator for "
              "0177 Vip Gaba_5 (79.9% in, +29.8pp over siblings), so pass 2 takes it back",
    "Ddc": "44.8% and best at a non-target population",
    "Vipr2": "8.2%, no separation",
    "C1ql2": "10.1%, no separation",
    "C1ql1": "12.4%, no separation",
    "Mgp": "15.8%, no separation",
    "Sfrp1": "21.1%, no separation, Jesse DEG with no readout",
    "Glipr1": "22.0%, no separation, Jesse DEG with no readout",
    "Vdr_": "placeholder, never used",
    "Upk1b": "17.6%, no separation",
    "Ctxn3": "15.8%, no separation",
    "Hcrtr1": "15.9%, best supertype has only 45 cells",
    "S1pr3": "24.3%, no separation",
    "Gpr3": "23.4%, no separation",
    "Ackr3": "21.3%, no separation",
    "Cd44": "19.7% - astrocyte/reactive marker, covered by Gja1/Aqp4",
    "Abca8a": "32.0%, subclass gap 27.5pp but only 5.2pp at supertype level; Dan gene with a weak map",
    "Tspan18": "26.8%, gap 22.7pp below the 25pp bar",
    "Gabre": "32.0%, gap 23.3pp below the 25pp bar",
    "Gpr12": "47.9%, gap 23.8pp below the 25pp bar",
    "Gpr68": "43.6%, gap 10.9pp - Jesse ORB-enriched but relative enrichment only",
    "Mas1": "44.8%, best supertype has 62 cells - Jesse ORB-enriched, unstable map",
    "Mchr1": "32.0%, gap 10.3pp",
    "Tacr3": "30.1%, gap 13.1pp",
    "Dusp4": "18.2%, gap 12.2pp - Dusp1 already covers the MAPK-phosphatase arm",
    "Dusp5": "40.6%, best supertype has 62 cells - Dusp1 covers this arm",
    "Piezo2": "20.2% at the anchors; it does qualify for 0531 SI-MA-LPO-LHA Skor1 Glut_2 "
              "(59.4% in, +26.1pp) but Masp1 separates the same sub-population better "
              "(59.9% in, +35.2pp)",
    "Sp8": "31.6%, best supertype has 61 cells",
    "Chrd": "48.6%, best supertype has 62 cells",
    "Emx1": "41.2%, gap 19.6pp - Satb2/Slc17a7 already give cortical identity",
    "Mbp": "90.2% at a neuronal anchor - ambient myelin contamination makes it a "
           "bad oligodendrocyte call; replaced by Sox10 and Mog",
    "Slc1a2": "100% at the anchors and 82% in neurons - only +18pp over neurons, "
              "useless as an astrocyte counter-stain; replaced by Gja1 and Aqp4",
    "Sox8": "86% in OPC but only +28pp over neurons; replaced by Pdgfra",
    "P2ry12": "99.6% in microglia but Csf1r and Cx3cr1 are more specific",
    "Cd36": "69.6%, best in border-associated macrophages - not a target population",
    "Tgfb2": "66.7%, best in smooth muscle - covered by Acta2",
    "Vegfd": "27% and no named axis",
    "Oxt": "1.2% - oxytocin cell bodies are in PVH/SON, not in ORBm or BMAp",
    "Htr1a": "28.3% at the anchors; its best supertype reaches 49.7%, just under the "
             "50% bar. The SOW names 5-HT2A, not 5-HT1A, so it is listed in "
             "BORDERLINE_not_ordered for Mark/Greg to override rather than ordered",
}

# Weak anchors: 005 L5 IT CTX Glut, 073 MEA-BST Sox6 Gaba and 121 MEA-BST Otp Zic2 Glut
# had 1-3 unique separators, so the best remaining candidates for each were taken
# straight from the Allen subclass matrix. L5 IT is transcriptionally continuous with
# L2/3 IT and L4/5 IT, which is why its best available gap is only ~17pp.
ANCHOR_REINFORCE = {
    "Adam19": "005 L5 IT CTX Glut: 57.7% in, +17.1pp over the next anchor",
    "Man2a1": "005 L5 IT CTX Glut: 76.9% in, +16.3pp",
    "Ldlrad3": "005 L5 IT CTX Glut: 68.7% in, +16.2pp",
    "Vipr1": "005 L5 IT CTX Glut: 66.7% in, +11.6pp; also a VIP-receptor readout",
    "Chn2": "073 MEA-BST Sox6 Gaba: 88.8% in, +14.8pp (that anchor had only 3)",
    "Zic4": "121 MEA-BST Otp Zic2 Glut: 50.7% in, +35.4pp",
    "Zfp521": "121 MEA-BST Otp Zic2 Glut: 75.5% in, +29.5pp",
    "Pcolce2": "121 MEA-BST Otp Zic2 Glut: 75.1% in, +29.1pp",
}


def score_from_cache(genes: list[str]) -> pd.DataFrame:
    """Anchor and supertype metrics for any gene, straight from the cached matrices.

    Needed because the genes added in this build (anchor reinforcement and new
    subtype separators) are not in the union of the earlier panels, so they would
    otherwise arrive with blank detection columns in the deliverable.
    """
    z = np.load(OUT / "anchor_subtype_cache.npz", allow_pickle=True)
    gsym = [str(x) for x in z["genes"]]
    gi = {g: j for j, g in enumerate(gsym)}
    P = z["anchor_pct"]
    names = [str(x) for x in z["anchor_names"]]
    ac = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                       "ANCHOR_COVERAGE")
    reg = dict(zip(ac.allen_subclass_anchor, ac.region))
    orb = [i for i, a in enumerate(names) if reg.get(a) == "ORBm"]
    bma = [i for i, a in enumerate(names) if reg.get(a) == "BMAp"]
    anchors = [str(x) for x in z["sup_keys"]]

    rows = []
    for g in genes:
        j = gi.get(g)
        if j is None:
            rows.append({"gene": g, "scored": False})
            continue
        col = P[:, j]
        gaps = [col[i] - np.delete(col, i).max() for i in range(len(names))]
        bi, pi = int(np.argmax(gaps)), int(np.argmax(col))
        sg, sp, sn, sl, spar = -np.inf, np.nan, np.nan, None, None
        for anc in anchors:
            M, lab, nn = z[f"sup_pct__{anc}"], z[f"sup_lab__{anc}"], z[f"sup_n__{anc}"]
            for i in range(M.shape[0]):
                v = M[i, j] - np.delete(M[:, j], i).max()
                if v > sg:
                    sg, sp, sn, sl, spar = v, M[i, j], int(nn[i]), str(lab[i]), anc
        rows.append({
            "gene": g, "scored": True,
            "anchor_max_pct": round(float(col[pi]), 1), "anchor_max_name": names[pi],
            "n_anchors_ge50": int((col >= 50).sum()),
            "median_pct_20": round(float(np.median(col)), 1),
            "max_pct_ORBm": round(float(col[orb].max()), 1),
            "max_pct_BMAp": round(float(col[bma].max()), 1),
            "subclass_gap_pp": round(float(gaps[bi]), 1), "subclass_gap_at": names[bi],
            "subclass_gap_pct_in": round(float(col[bi]), 1),
            "supertype_gap_pp": round(float(sg), 1),
            "supertype_gap_pct_in": round(float(sp), 1),
            "supertype_n_cells": sn, "supertype": sl, "supertype_parent": spar,
        })
    return pd.DataFrame(rows)


def main() -> None:
    t = pd.read_excel(OUT / "ALL_PANELS_anchor_and_subtype_scores.xlsx", "gene_scores")
    t["is_unique_separator"] = t["is_unique_separator"].fillna(0).astype(bool)
    t["sub_ok"] = ((t.supertype_gap_pp >= SUB_GAP) & (t.supertype_gap_pct_in >= SUB_PCT)
                   & (t.supertype_n_cells >= SUB_N))
    t["cls_ok"] = (t.subclass_gap_pp >= 20) & (t.subclass_gap_pct_in >= 40)
    S = t.set_index("gene")

    sep = pd.read_excel(OUT / "SUBTYPE_SEPARATORS_genomewide.xlsx", "candidates")
    nn = pd.read_excel(OUT / "NONNEURONAL_scores.xlsx", "all_genes").set_index("gene")

    ac = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                       "ANCHOR_COVERAGE")
    subclass_sep = set()
    for s in ac.unique_separators_on_shared_panel.fillna(""):
        subclass_sep |= {x.strip() for x in str(s).split(",") if x.strip()}

    # inherit role labels from the three richest earlier versions
    role = {}
    for fn, col in [("FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx", "block"),
                    ("PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx", "block")]:
        d = pd.read_excel(DL / fn, "SHARED_PANEL_ORDER")
        for r in d.itertuples():
            role.setdefault(str(r.gene), {})[fn[:12]] = (str(getattr(r, col)), str(r.serves))
    ideal = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                          "BY_CATEGORY")
    ideal_cat = ideal.groupby("gene").category.apply(lambda s: sorted(set(s))).to_dict()

    def is_gpcr(g: str) -> bool:
        if "2_GPCR" in ideal_cat.get(g, []):
            return True
        return any("GPCR" in b for b, _ in role.get(g, {}).values())

    # -------------------------------------------------- R2 greedy subtype cover
    # Measured separating power outranks curatorial judgement: a gene on a drop list
    # is ranked last but is still taken when it is the only marker that can resolve a
    # sub-population. Four sub-populations (0013 L6 IT CTX Glut_1 with 3397 cells,
    # 0177 Vip Gaba_5, 0214 Sst Gaba_1, 0531 SI-MA-LPO-LHA Skor1 Glut_2) have exactly
    # one or two qualifying markers in the whole atlas, and they are on those lists.
    ok = sep[(sep.gap_pp >= SUB_GAP) & (sep.pct_in >= SUB_PCT) & (sep.n_cells >= SUB_N)]
    supertypes = sorted(set(zip(ok.parent_anchor, ok.supertype)))
    on301 = set(t[t.on_g301].gene.astype(str))
    deprioritised = set(FORCE_DROP) | DROP_UNINTERPRETABLE
    reach = {g: set(zip(d.parent_anchor, d.supertype)) for g, d in ok.groupby("gene")}
    best_gap = ok.groupby("gene").gap_pp.max().to_dict()

    need = {st: TARGET_PER_SUPERTYPE for st in supertypes}
    chosen: dict[str, str] = {}

    def describe(g: str, hit: list) -> str:
        return ("subtype separator for " +
                "; ".join(f"{s} (gap "
                          f"{ok[(ok.gene == g) & (ok.supertype == s)].gap_pp.max():.0f}pp)"
                          for _, s in hit[:3]))

    def greedy(pool_genes: set[str], stop_when_covered: bool) -> None:
        while True:
            pool = [g for g in pool_genes if g not in chosen
                    and any(need.get(st, 0) > 0 for st in reach[g])]
            if not pool:
                return
            g = max(pool, key=lambda x: (sum(1 for st in reach[x] if need.get(st, 0) > 0),
                                         x in on301, best_gap[x]))
            hit = sorted(st for st in reach[g] if need.get(st, 0) > 0)
            chosen[g] = describe(g, hit)
            for st in hit:
                need[st] -= 1
            if stop_when_covered and not any(v > 0 for v in need.values()):
                return

    # pass 1: reach TARGET_PER_SUPERTYPE using clean genes only
    greedy({g for g in reach if g not in deprioritised}, stop_when_covered=True)
    # pass 2: any sub-population still at zero markers is filled from the full pool,
    # drop list included, because no clean alternative exists in the atlas
    need = {st: (1 if need.get(st, 0) == TARGET_PER_SUPERTYPE else 0) for st in supertypes}
    greedy(set(reach), stop_when_covered=True)

    # -------------------------------------------------- assemble
    keep: dict[str, tuple[str, str]] = {}          # gene -> (primary block, why)
    roles: dict[str, set[str]] = {}                # gene -> every category it serves

    def add(g: str, block: str, why: str, cat: str) -> None:
        roles.setdefault(g, set()).add(cat)
        if g not in keep:
            keep[g] = (block, why)

    for g in TRAP:
        add(g, "01_TRAP_reporter",
            "TRAP readout: marks the 4-OHT-tagged POST ensemble", "6_TRAP_reporter")
    for g, w in SOW.items():
        cat = ("7_IEG" if g in ("Fos", "Arc") else
               "8_morphine_related" if g in ("Per2", "Creb1") else
               "3_GPCR" if g in ("Adrb1", "Htr2a", "Oprm1") else "1_cell_type_marker")
        add(g, "02_SOW_named", w, cat)
    for g, w in EI_BACKBONE.items():
        add(g, "03_class_EI_backbone", w, "1_cell_type_marker")
    for g, w in GLIA.items():
        add(g, "04_nonneuronal_counterstain", w, "1_cell_type_marker")
    # R1 is absolute: a unique separator is never removed by a curatorial drop.
    for g in sorted(subclass_sep):
        if g in FORCE_DROP and g in ("Mbp",):          # documented replacement only
            continue
        r = S.loc[g] if g in S.index else None
        add(g, "05_subclass_separator",
            "unique separator for one of the 20 anchors"
            + (f"; {r.anchor_max_pct:.0f}% at {r.anchor_max_name}" if r is not None else ""),
            "1_cell_type_marker")
    for g, w in ANCHOR_REINFORCE.items():
        add(g, "05_subclass_separator", "anchor reinforcement - " + w, "1_cell_type_marker")
    for g, w in sorted(chosen.items()):
        add(g, "06_subtype_separator", w, "2_subtype_marker")
    for g, w in IEG.items():
        add(g, "07_IEG_pCREB_target",
            w + " (exempt from the detection bar: the atlas is resting tissue)", "7_IEG")
    for g, w in CLOCK.items():
        add(g, "08_clock_module", w, "8_morphine_related")
    for g, w in PLASTICITY.items():
        if g in FORCE_DROP:
            continue
        p = S.anchor_max_pct.get(g, np.nan)
        if np.isnan(p) or p >= VIS:
            add(g, "09_plasticity", f"{w}; {p:.0f}% of cells at the best anchor",
                "5_plasticity")
    for g, w in MORPHINE_STATE.items():
        p = S.anchor_max_pct.get(g, np.nan)
        if g not in FORCE_DROP and (np.isnan(p) or p >= VIS or S.sub_ok.get(g, False)):
            add(g, "10_morphine_state", f"{w}; {p:.0f}% at the best anchor",
                "8_morphine_related")

    # R4 GPCRs and R6 TFs, pooled from every earlier version. Genes that already
    # earned a slot still collect the extra role label here.
    for g in sorted(set(t.gene.astype(str))):
        if g in FORCE_DROP or g not in S.index or not S.scored.get(g, False):
            continue
        r = S.loc[g]
        visible = r.anchor_max_pct >= VIS
        if is_gpcr(g) and (visible or r.sub_ok):
            add(g, "11_GPCR_map",
                f"GPCR; {r.anchor_max_pct:.0f}% at {r.anchor_max_name}, "
                f">=50% in {r.n_anchors_ge50} of 20 anchors", "3_GPCR")
        if "4_TF" in ideal_cat.get(g, []) and (visible or r.sub_ok or r.cls_ok):
            add(g, "12_TF", f"transcription factor; {r.anchor_max_pct:.0f}% at "
                            f"{r.anchor_max_name}", "4_TF")
        if g in keep or g in DROP_UNINTERPRETABLE:
            continue
        if (r.cls_ok or r.sub_ok) and r.anchor_max_pct >= 20:
            add(g, "06_subtype_separator",
                f"separator kept on measured specificity: subclass gap "
                f"{r.subclass_gap_pp:.0f}pp, supertype gap "
                f"{0 if pd.isna(r.supertype_gap_pp) else r.supertype_gap_pp:.0f}pp",
                "2_subtype_marker")

    # Jesse / Dan provenance, carried as extra role labels
    jesse = set()
    for fn in ["mPFC_GPCRDEGs.csv", "mPFC_TFDEGs.csv", "mPFC_IEGDEGs.csv",
               "mPFC_SynPlast.csv"]:
        p = (V3 / "inputs" / "Jesse_ORB" /
             "OpioidDependenceDEG_genesets_forHansol090926" / fn)
        if p.exists():
            jesse |= set(pd.read_csv(p).iloc[:, 0].astype(str))
    dan = {"Col23a1", "Slc29a4", "Cck", "Gfra1", "Sp8", "Abca8a", "Calcrl", "Lamb3",
           "Syndig1l", "Tspan18", "Gabre", "Nos1", "Oprl1", "Dnah5"}
    for g in list(keep):
        if g in jesse:
            roles[g].add("8_morphine_related")

    panel = pd.DataFrame([{"gene": g, "block": b, "why": w,
                           "roles": ", ".join(sorted(roles[g])),
                           "n_roles": len(roles[g]),
                           "source_Jesse_morphine_DEG": g in jesse,
                           "source_Dan_GSE283418": g in dan,
                           "SOW_named": g in SOW}
                          for g, (b, w) in keep.items()])
    # Genes introduced in this build are not in t, so score them from the cache and
    # append, otherwise the deliverable would show blank detection for them.
    new = sorted(set(keep) - set(t.gene.astype(str)))
    if new:
        extra = score_from_cache(new)
        for c in t.columns:
            if c not in extra.columns:
                extra[c] = False if c.startswith("on_") else None
        t = pd.concat([t, extra[t.columns]], ignore_index=True)
        t["sub_ok"] = ((t.supertype_gap_pp >= SUB_GAP) & (t.supertype_gap_pct_in >= SUB_PCT)
                       & (t.supertype_n_cells >= SUB_N))
        t["cls_ok"] = (t.subclass_gap_pp >= 20) & (t.subclass_gap_pct_in >= 40)
        t["is_unique_separator"] = t.is_unique_separator.fillna(False).astype(bool)
        S = t.set_index("gene")
        print(f"scored {len(new)} genes newly introduced by this build")

    m = panel.merge(t, on="gene", how="left").sort_values(["block", "gene"])
    m.insert(0, "order_rank", range(1, len(m) + 1))

    # -------------------------------------------------- audit every candidate
    allg = sorted(set(t.gene.astype(str)) | set(keep) | set(reach))
    fate = []
    for g in allg:
        r = S.loc[g] if g in S.index else None
        if g in keep:
            f, why = "KEEP", keep[g][1]
        elif g in FORCE_DROP:
            f, why = "DROP", FORCE_DROP[g]
        elif g in DROP_UNINTERPRETABLE:
            f, why = "DROP", ("broad DEG with no interpretable spatial readout "
                              "(high detection but reports no named mechanism)")
        elif r is not None and r.scored and r.anchor_max_pct < VIS:
            f, why = "DROP", (f"{r.anchor_max_pct:.0f}% at the best of 20 anchors and no "
                              f"trustworthy separation")
        else:
            f, why = "NOT_ORDERED", "candidate not required by any of the eight rules"
        fate.append({
            "gene": g, "fate": f, "block": keep.get(g, ("", ""))[0], "reason": why,
            "anchor_max_pct": None if r is None else r.anchor_max_pct,
            "n_anchors_ge50": None if r is None else r.n_anchors_ge50,
            "subclass_gap_pp": None if r is None else r.subclass_gap_pp,
            "supertype_gap_pp": None if r is None else r.supertype_gap_pp,
            "supertype_n_cells": None if r is None else r.supertype_n_cells,
            "nonneuronal_best_pop": nn.best_pop.get(g),
            "nonneuronal_pct": nn.best_pop_pct.get(g),
            "nonneuronal_gap_vs_neurons": nn.gap_vs_neurons.get(g),
            **{f"on_{k}": (bool(r[f"on_{k}"]) if r is not None else False)
               for k in ["IDEAL_178", "pruned_197", "v7_252", "g301"]},
        })
    audit = pd.DataFrame(fate)

    # -------------------------------------------------- verification
    G = set(m.gene)
    cov = (ok.assign(on=ok.gene.isin(G)).groupby(["parent_anchor", "supertype", "n_cells"])
             .agg(n_markers_on_panel=("on", "sum"), n_candidates=("gene", "nunique"),
                  markers=("gene", lambda s: ", ".join(sorted(set(s) & G)) or "NONE"))
             .reset_index())
    # Recomputed on the v8 gene list rather than inherited from the earlier file, so
    # that anchor-reinforcement genes count. A gene is credited to an anchor when its
    # single best subclass gap lands there at >=10pp and it is detected in >=30% of
    # that anchor's cells.
    onpanel = m[m.scored == True]
    cred = onpanel[(onpanel.subclass_gap_pp >= 10) & (onpanel.subclass_gap_pct_in >= 30)]
    by_anchor = cred.groupby("subclass_gap_at").gene.apply(lambda s: sorted(s)).to_dict()
    anchor_chk = ac[["region", "cell_type_label", "allen_subclass_anchor", "n_cells"]].copy()
    anchor_chk["v8_separators"] = [", ".join(by_anchor.get(a, []))
                                   for a in anchor_chk.allen_subclass_anchor]
    anchor_chk["n_v8_separators"] = [len(by_anchor.get(a, []))
                                     for a in anchor_chk.allen_subclass_anchor]
    anchor_chk["inherited_separators_kept"] = [
        len({x.strip() for x in str(s).split(",") if x.strip()} & G)
        for s in ac.unique_separators_on_shared_panel.fillna("")]
    anchor_chk["callable"] = np.where(anchor_chk.n_v8_separators >= 2, "yes (>=2 markers)",
                                      np.where(anchor_chk.n_v8_separators == 1,
                                               "yes (1 marker)", "NO"))

    exempt = set(IEG) | set(SOW) | set(GLIA)

    def metrics(name: str, gg: set[str]) -> dict:
        s = t[t.gene.isin(gg) & (t.scored == True)]
        lo = s[s.anchor_max_pct < VIS]
        # low detection is only a problem when the probe also cannot separate
        # anything and has no exemption - otherwise a low percentage is the
        # expected signature of a sub-population-specific marker
        sep_ok = (lo.sub_ok.fillna(False).astype(bool)
                  | lo.cls_ok.fillna(False).astype(bool)
                  | lo.is_unique_separator.fillna(False).astype(bool))
        empty = lo[~sep_ok & ~lo.gene.isin(exempt)]
        c = ok.assign(on=ok.gene.isin(gg)).groupby(["parent_anchor", "supertype"]).on.sum()
        return {"panel": name, "n_genes": len(gg),
                "median_detection_pct": round(s.anchor_max_pct.median(), 1),
                "n_below_50pct": len(lo),
                "of_those_separate_a_population": int(sep_ok.sum()),
                "of_those_exempt_IEG_SOW_glia": int(lo.gene.isin(exempt).sum()),
                "n_EMPTY_MAP_probes": len(empty),
                "empty_map_genes": ", ".join(sorted(empty.gene))[:180],
                "supertypes_with_1plus_marker": int((c >= 1).sum()),
                "supertypes_with_2plus_markers": int((c >= 2).sum())}

    cmp_rows = [metrics(n, set(t[t[f"on_{k}"]].gene.astype(str)))
                for k, n in [("IDEAL_178", "IDEAL 178"), ("pruned_197", "pruned 197"),
                             ("v7_252", "v7 252"), ("g301", "301")]]
    cmp_rows.append(metrics("v8 FINAL", G))
    cmpdf = pd.DataFrame(cmp_rows)
    s = m[m.scored == True]
    nojob_genes = set(cmp_rows[-1]["empty_map_genes"].replace(" ", "").split(",")) - {""}
    nojob = s[s.gene.isin(nojob_genes)]

    cols = ["order_rank", "gene", "block", "roles", "why", "SOW_named",
            "source_Jesse_morphine_DEG", "source_Dan_GSE283418",
            "anchor_max_pct", "anchor_max_name", "n_anchors_ge50",
            "max_pct_ORBm", "max_pct_BMAp", "subclass_gap_pp", "subclass_gap_at",
            "supertype_gap_pp", "supertype_gap_pct_in", "supertype_n_cells",
            "supertype", "supertype_parent", "is_unique_separator",
            "on_IDEAL_178", "on_pruned_197", "on_v7_252", "on_g301"]
    order = m[cols]
    orb = order[(order.max_pct_ORBm.fillna(100) >= 20) | order.gene.isin(TRAP)]
    bma = order[(order.max_pct_BMAp.fillna(100) >= 20) | order.gene.isin(TRAP)]

    bc = (m.groupby("block").gene.agg(n_genes="count",
                                      genes=lambda s: ", ".join(sorted(s)))
            .reset_index())
    cat_rows = [{"category": c, "gene": g,
                 "is_primary_role": keep[g][0].split("_", 1)[1],
                 "anchor_max_pct": S.anchor_max_pct.get(g),
                 "why": keep[g][1]}
                for g in keep for c in sorted(roles[g])]
    bycat = pd.DataFrame(cat_rows).sort_values(["category", "gene"])
    catcount = (bycat.groupby("category").gene.nunique()
                  .rename("n_genes").reset_index())

    # Detection exemptions, listed openly so nothing is hidden.
    low = s[s.anchor_max_pct < VIS][
        ["gene", "block", "roles", "anchor_max_pct", "subclass_gap_pp",
         "supertype_gap_pp", "supertype_gap_pct_in", "supertype_n_cells", "why"]]
    borderline = pd.DataFrame([
        {"gene": g, "reason_not_ordered": w,
         "anchor_max_pct": S.anchor_max_pct.get(g),
         "supertype_gap_pp": S.supertype_gap_pp.get(g)}
        for g, w in FORCE_DROP.items() if g in S.index])

    # ---- ordering practicalities -------------------------------------------
    # 10x tiers standalone custom panels at 1-50 / 51-100 / 101-300 / 301-480, so
    # crossing 300 changes the part number. Rank the marginal value of every subtype
    # separator so the exact trim to <=300 is a stated choice rather than a guess.
    st_count = (ok[ok.gene.isin(G)].groupby(["parent_anchor", "supertype"])
                  .gene.nunique().to_dict())
    trim = []
    # only genes whose sole job is subtype separation are trim candidates; a gene that
    # is also an IEG, GPCR, TF, plasticity or morphine readout is not cut for a price tier
    pure_subtype = [g for g in m[m.block == "06_subtype_separator"].gene
                    if roles[g] == {"2_subtype_marker"}]
    for g in pure_subtype:
        mine = [st for st in zip(ok[ok.gene == g].parent_anchor, ok[ok.gene == g].supertype)
                if st in st_count]
        if not mine:
            continue
        # a marker is expendable only where every sub-population it serves keeps >=2
        spare = min((st_count[st] for st in mine), default=0)
        trim.append({"gene": g, "n_supertypes_served": len(mine),
                     "min_markers_left_if_cut": spare - 1,
                     "best_gap_pp": ok[ok.gene == g].gap_pp.max(),
                     "anchor_max_pct": S.anchor_max_pct.get(g),
                     "safe_to_cut": spare - 1 >= 2})
    trimdf = (pd.DataFrame(trim).sort_values(
        ["safe_to_cut", "min_markers_left_if_cut", "best_gap_pp"],
        ascending=[False, False, True]))
    n_over = max(0, len(m) - 300)
    trimdf["cut_for_300_gene_tier"] = False
    if n_over:
        trimdf.iloc[:n_over, trimdf.columns.get_loc("cut_for_300_gene_tier")] = True

    # 10x asks for 10-20 spares to substitute when a probe fails design.
    spare_pool = audit[(audit.fate == "NOT_ORDERED") & audit.anchor_max_pct.notna()]
    backups = (spare_pool.nlargest(20, "supertype_gap_pp")
               [["gene", "anchor_max_pct", "subclass_gap_pp", "supertype_gap_pp",
                 "supertype_n_cells"]]
               .assign(role="substitute if a designed probe fails 10x probe design"))

    readme = pd.DataFrame([
        ("Ordering format", "Xenium v1 STANDALONE custom panel. %d genes falls in the "
                            "301-480 tier (PN-1000644 / 1000647); 101-300 is the tier "
                            "below. TRIM_TO_300 names the exact genes to cut if you "
                            "want the cheaper tier and what it costs you."
                            % len(m)),
        ("tdTomato and iCre need the advanced workflow",
         "They are transgene sequences, not mm10 genes, so they are advanced custom "
         "targets and need the Advanced Panel Upgrade (PN-1000664) on top of the "
         "standalone panel. Flag this to your 10x rep when you submit."),
        ("Backup genes", "BACKUP_GENES gives 20 spares, which is what 10x asks for in "
                         "case a probe fails their design step"),
        ("What to order", "PANEL_ORDER - %d genes, standalone custom Xenium "
                          "(no 248-gene base panel, every probe is designed)" % len(m)),
        ("Categories you asked for", "BY_CATEGORY / BY_CATEGORY_COUNTS. A gene can serve "
                                     "more than one job, so it appears under every "
                                     "category it serves; its primary block is in "
                                     "PANEL_ORDER.block"),
        ("Why this differs from the earlier files",
         "Identity genes and state genes were judged on different metrics. Identity "
         "genes must SEPARATE (gap between a population and its neighbours); state "
         "genes must be VISIBLE (percent of cells detected). Earlier versions used "
         "detection alone, which cut real subtype markers such as Vdr (11% of the "
         "subclass but 95% of one 483-cell sub-population) and kept probes that are "
         "invisible here such as Sstr4 (1.4%)."),
        ("Detection reference", "Allen WMB-10X, 226,886 cells (ORBm 106,122 / "
                                "BMAp 120,764), measured at the 20 target subclasses in "
                                "their own dissection - not across all 79 subclasses "
                                "present in the dissection"),
        ("Glia are scored separately", "The 20 anchors are all neuronal, so glial and "
                                       "vascular markers were scored against their own "
                                       "populations. That is why Rgs5 and Vtn are on the "
                                       "list at 21% and 0.8% of neurons: they are 99.7% "
                                       "and 98.5% of pericytes."),
        ("IEGs are exempt", "The Allen atlas is resting tissue, so low baseline is the "
                            "expected result for Fos, Arc, Npas4, Egr2, Btg2, Ier2, "
                            "Sik1. Induction is the measurement."),
        ("Verification", "ANCHOR_COVERAGE_20types (all 20 target types still callable), "
                         "SUBTYPE_COVERAGE (how many of the separable sub-populations "
                         "have >=2 markers), VERSION_COMPARISON (this panel against the "
                         "four earlier ones on the same metrics)"),
        ("Every candidate accounted for", "AUDIT_every_candidate gives a KEEP / DROP "
                                          "decision and a reason for all %d genes that "
                                          "any version proposed" % len(audit)),
        ("Open decisions", "BORDERLINE_not_ordered lists genes that were deliberately "
                           "left off with the measurement behind each call, so they can "
                           "be added back on request"),
        ("CONFIRM before ordering", "the tdTomato reporter strain (Ai9 007909 or Ai14 "
                                    "007908/007914 are the documented tdTomato lines) - "
                                    "if the line carries a different fluorophore this "
                                    "probe reads nothing"),
    ], columns=["item", "detail"])

    with pd.ExcelWriter(DST) as xw:
        readme.to_excel(xw, sheet_name="READ_ME", index=False)
        order.to_excel(xw, sheet_name="PANEL_ORDER", index=False)
        bycat.to_excel(xw, sheet_name="BY_CATEGORY", index=False)
        catcount.to_excel(xw, sheet_name="BY_CATEGORY_COUNTS", index=False)
        bc.to_excel(xw, sheet_name="BY_BLOCK", index=False)
        cmpdf.to_excel(xw, sheet_name="VERSION_COMPARISON", index=False)
        anchor_chk.to_excel(xw, sheet_name="ANCHOR_COVERAGE_20types", index=False)
        cov.to_excel(xw, sheet_name="SUBTYPE_COVERAGE", index=False)
        low.to_excel(xw, sheet_name="KEPT_BELOW_50pct", index=False)
        trimdf.to_excel(xw, sheet_name="TRIM_TO_300", index=False)
        backups.to_excel(xw, sheet_name="BACKUP_GENES", index=False)
        borderline.to_excel(xw, sheet_name="BORDERLINE_not_ordered", index=False)
        audit.to_excel(xw, sheet_name="AUDIT_every_candidate", index=False)
        orb.to_excel(xw, sheet_name="ORBm_view", index=False)
        bma.to_excel(xw, sheet_name="BMAp_view", index=False)
    print("wrote", DST)

    print(f"\nv8 panel: {len(m)} genes")
    print(bc[["block", "n_genes"]].to_string(index=False))
    print("\ncategories (a gene can serve several):")
    print(catcount.to_string(index=False))
    print("\n" + cmpdf.to_string(index=False))
    print(f"\n20 target types callable on v8: "
          f">=1 marker {int((anchor_chk.n_v8_separators >= 1).sum())}/20, "
          f">=2 markers {int((anchor_chk.n_v8_separators >= 2).sum())}/20 "
          f"(min {int(anchor_chk.n_v8_separators.min())})")
    print(f"genes kept below 50% detection: {len(low)}  "
          f"(of which no-job: {len(nojob)})")
    if len(nojob):
        print(nojob[["gene", "block", "anchor_max_pct"]].to_string(index=False))
    print(f"audit: KEEP={int((audit.fate == 'KEEP').sum())} "
          f"DROP={int((audit.fate == 'DROP').sum())} "
          f"NOT_ORDERED={int((audit.fate == 'NOT_ORDERED').sum())}")


if __name__ == "__main__":
    main()
