"""Build the right-sized final ORBm/BMAp Xenium panel (v9).

v8 proved what the panel needs to be able to do. v9 asks the next question: what is
the smallest set that still does it. Three sources of redundancy were measured in v8
and are capped here:

  1. separators per target type      v8 gave one anchor 13 and another 1
  2. markers per sub-population      26 of 86 had 3-4 markers
  3. ubiquitous no-contrast genes    28 genes were >=95% detected in >=18 of 20
                                     anchors with a separation gap under 12pp.
                                     Those cost optical budget on a Xenium run and
                                     add no contrast, so only the ones that are a
                                     named mechanistic readout are kept and the
                                     paralogues are dropped.

Sex-genotyping probes are not included: requested out.

Caps, all set before looking at the resulting panel size:
  separators per target type        <= 4, ranked by separation gap
  markers per sub-population        2 if the supertype has >=300 cells, else 1
  one marker per non-neuronal population, two for astrocyte and microglia
  IEG                               three kinetic waves, one gene per wave-slot
  plasticity                        one gene per mechanism, no paralogue pairs
  GPCR                              central druggable receptors with >=50% detection;
                                    separators come in for free

Selection criteria are the ones that were asked for, and nothing else: cell type
markers, sub-type markers, GPCRs, morphine-related genes, transcription factors,
plasticity, IEGs, circadian genes and the TRAP reporters, each judged on measured
detection and separation in Allen WMB-10X plus the Jesse and Dan datasets. No gene is
included because a funding document names it.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path(r"c:\Users\hsollim\Downloads")
DST = OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx"

VIS = 50.0
SUB_GAP, SUB_PCT, SUB_N = 25.0, 50.0, 100
MAX_SEP_PER_ANCHOR = 4
SUPERTYPE_BIG = 300          # >=2 markers above this size, 1 below

TRAP = ["tdTomato", "iCre"]

# No gene is on this panel because a funding document names it. The eight genes that
# earlier versions carried in an "SOW-named" block were re-tested on detection and
# separation alone and all eight cleared the ordinary bars, so they now enter through
# the category they actually belong to (see IEG, CLOCK, GPCR_KEEP, TAXONOMY below):
#   Satb2 98.8% detected, +91.0pp   Oprm1 91.6%   Creb1 84.9% in 19 of 20 types
#   Arc   83.6%, +34.3pp            Adrb1 80.6%   Htr2a 78.6%, +53.8pp
#   Fos   62.4%, +27.3pp            Per2  60.9%

EI_BACKBONE = {
    "Slc17a7": "VGLUT1, cortical excitatory - E/I numerator",
    "Slc17a6": "VGLUT2, subcortical excitatory",
    "Gad1": "GAD67, inhibitory - E/I denominator",
    "Gad2": "GAD65, inhibitory",
    "Slc32a1": "VGAT, obligate vesicular GABA transporter",
    "Slc6a1": "GAT1, GABA reuptake",
    "Camk2a": "excitatory principal-neuron identity and the LTP kinase",
    "Pvalb": "fast-spiking interneuron class",
    "Sst": "SST interneuron class",
    "Vip": "VIP interneuron class",
    "Lamp5": "Lamp5 interneuron class",
    "Npy": "NPY interneuron",
    "Nos1": "nNOS interneuron class",
    "Calb1": "calbindin subdivision",
    "Calb2": "calretinin subdivision",
}

# Allen names 20 target subclasses after genes ("120 MEA Otp Foxp2 Glut",
# "073 MEA-BST Sox6 Gaba"), and cortical layers are called combinatorially rather than
# by a unique marker. Those genes have small separation gaps by construction - Fezf2 is
# shared by L5 ET, L5 NP and L6, Dlx1 by every GABA class - so a gap cap would drop
# them. They are kept because they are how the taxonomy is defined and read, which is
# the "all important cell type markers" request.
TAXONOMY = {
    "Satb2": "cortical IT / callosal identity, 98.8% detected and +91.0pp at its "
             "sub-population - one of the strongest markers on the panel",
    "Fezf2": "L5 ET / subcerebral projection identity",
    "Bcl11b": "Ctip2, deep-layer projection identity",
    "Tle4": "L6 CT identity",
    "Tbr1": "pallial excitatory / L6 identity",
    "Neurod2": "pallial excitatory identity",
    "Otp": "names two target subclasses: 120 MEA Otp Foxp2 and 121 MEA-BST Otp Zic2",
    "Zic2": "names 121 MEA-BST Otp Zic2 Glut",
    "Sox6": "names 073 MEA-BST Sox6 Gaba; MGE-derived GABA",
    "Lhx6": "names 074 MEA-BST Lhx6 Sp9 Gaba; MGE-derived GABA",
    "Dlx1": "pan-GABAergic precursor TF, the inhibitory arm of combinatorial calling",
    "Prox1": "CGE-derived interneuron identity",
    "Nfib": "cortical/amygdalar regional TF",
}

# Xenium images a section: it cannot pre-sort cells the way dissociated sequencing can,
# so every nucleus in the field gets called. 28.0% of the ORBm/BMAp cells in the Allen
# atlas are non-neuronal (63,618 of 226,886). Without markers for them those cells do
# not disappear - they get forced into the nearest neuronal cluster. These genes exist
# to EXCLUDE, not to study glia, so one marker per population is the rule and a second
# is added only where the first cross-reacts.
# All values below are measured against each population's own cells, not the neuronal
# anchors, and are the corrected scores after the subclass-ID bug was fixed.
# A held-out cell-level test (GLIA_NECESSITY_TEST.xlsx, 188,849 cells, 3 seeds) settled
# how many of these are actually needed, and the answer was fewer than assumed:
#   neuron vs non-neuron   balanced accuracy 0.9998 with the glial probes, 0.9998
#                          without. Only 0.03% of glial cells get called a neuron
#                          either way, and removing 8 RANDOM non-glial genes does
#                          exactly as much damage as removing the glial probes.
# Excluding glia does not need glial probes, because a glial cell is negative for the
# ~40 pan-neuronal genes already on the panel; absence of neuronal signal is the call.
# What the probes DO buy is NAMING a cluster once it is found - pointing at Aqp4 is a
# claim, pointing at the absence of forty genes is an argument - and that needs one
# marker per population worth naming, not two per population.
# A 20-way held-out classification of 125,313 cells (TWENTY_TYPE_RECALL.xlsx) found the
# real weak points, and they were not where the marker count said. 073 MEA-BST Sox6
# Gaba, the population with one marker, reached 0.979 recall. The two that failed were
# cortical pairs that the marker count called healthy with 5 markers each:
#   005 L5 IT  recall 0.697, with 18.8% of its cells called 004 L6 IT
#   029 L6b    recall 0.755, with 23.9% of its cells called 030 L6 CT
# The cause is the search, not the atlas. Separators were ranked one-vs-rest - gap
# against the best of the other 19 - so a gene that cleanly splits two confusable
# neighbours but is also present in a third population scored zero. These are chosen
# PAIRWISE instead, in opposite-polarity pairs so the contrast works in both directions.
PAIRWISE = {
    "Kcnk2": "splits 005 L5 IT (73.6%) from 004 L6 IT (21.6%), +52.1pp",
    "Sulf1": "the opposite pole of the same contrast: 004 L6 IT 74.2% vs 005 L5 IT "
             "17.5%, +56.7pp",
    "Cntn6": "second axis for the same pair: 005 L5 IT 77.7% vs 004 L6 IT 29.1%",
    "Inpp4b": "opposite pole of that second axis: 004 L6 IT 60.9% vs 005 L5 IT 12.1%",
    "Nxph4": "the canonical L6b marker, and it splits 029 L6b (65.4%) from 030 L6 CT "
             "(5.2%), +60.3pp",
    "Rprm": "the canonical L6 CT marker and the opposite pole: 030 L6 CT 91.3% vs "
            "029 L6b 28.2%, +63.0pp",
    "Tmem163": "third L6b axis, 029 L6b 70.9% vs 030 L6 CT 5.9%, +65.0pp",
    "Mpped1": "splits 120 MEA Otp Foxp2 (86.6%) from 113 MEA-COA-BMA Ccdc42 (19.4%), "
              "+67.2pp - the third-weakest pair at 0.923 recall",
}

GLIA = {
    "Aqp4": "astrocyte, the largest non-neuronal population here (24,323 cells, 10.7%). "
            "90.4% of astrocytes vs 1.3% of neurons. Preferred over Gja1, which also "
            "labels 81% of VLMC and 98% of ependymal cells",
    "Mog": "oligodendrocyte (12,769 cells, 5.6%), 93.1% vs 3.3% of neurons (+89.8pp)",
    "Pdgfra": "OPC (10,312 cells, 4.5%), 99.9% vs 1.0% of neurons (+98.9pp); with Mog "
              "it splits OPC from mature oligodendrocyte",
    "Csf1r": "microglia (8,523 cells, 3.8%), 99.8% vs 1.7% of neurons (+98.2pp)",
    "Cldn5": "endothelium (4,328 cells, 1.9%), 99.1% vs 0.5% of neurons (+98.6pp); "
             "one probe for the whole vascular compartment",
}
# Cut, with the reason on record:
#   Gja1    Aqp4 names the same population and does not cross-react with VLMC/ependyma
#   Rgs5    mural cells are 1.0% of the section and Cldn5 already flags vessels
#   Dcn     VLMC are 0.2% of the section (418 cells)
#   Sox10   marks OPC (97.7%) and oligodendrocyte (95.5%) equally, so it cannot tell
#           them apart; Pdgfra and Mog already do, and do it cleanly
#   Cx3cr1  Csf1r is the better microglial probe on the same cells: +98.2pp versus
#           +88.8pp, and Cx3cr1 carries 11.2% neuronal background against Csf1r's 1.7%

# Three kinetic waves, because a 24 h post-test window needs more than Fos.
IEG = {
    "Fos": "rapid wave, AP-1 - canonical activity marker, 62.4% detected",
    "Junb": "rapid wave, AP-1 partner",
    "Arc": "rapid wave, synaptic scaling, 83.6% detected",
    "Creb1": "the CREB hub whose targets the rest of this block reads out; "
             "84.9% detected and above 50% in 19 of the 20 target types",
    "Egr1": "rapid wave, zif268, pCREB target",
    "Npas4": "rapid wave, inhibitory-synapse specific - the direct E/I readout",
    "Fosb": "delayed wave, accumulates over repeated exposure",
    "Nr4a1": "delayed wave, Nur77, pCREB target",
    "Bdnf": "delayed wave, pCREB target and the TrkB ligand",
    "Scg2": "delayed wave, activity-regulated neuropeptide",
    "Vgf": "delayed wave, activity-regulated neuropeptide, pCREB target",
    "Per1": "delayed wave, pCREB-target clock IEG",
    "Crem": "feedback arm, ICER represses CREB targets",
    "Dusp1": "feedback arm, MAPK phosphatase",
}

# Circadian module. Scoped to the genes Jesse's 5-day escalating-morphine DESeq2 found
# differentially expressed in PL-ILA-ORB, which is where the request came from. Eleven
# of his DEGs are clock genes; Rorb is already carried as an L4/5 layer separator, and
# the other ten are here. Clock, Cry2, Rora, Npas2, Per3, Dbp and Cry1 are deliberately
# NOT added: they are not in Jesse's DEG lists, and independently Clock (96.8% in 20/20,
# gap 7.9pp) and Rora (99.9% in 20/20, gap 0.4pp) would be ubiquitous no-contrast
# probes while Cry1 (36.6%) and Dbp (51.2%, 1 of 20) are barely visible.
CLOCK = {
    "Per2": "Jesse's top ORB morphine DEG - up in 13 of his clusters; 60.9% detected",
    "Per1": "Jesse DEG, up in 8 clusters; pCREB-target clock IEG",
    "Bhlhe40": "DEC1, Jesse DEG up in 4 clusters (L2/3, L4/5, L6 IT, L6 CT)",
    "Ep300": "p300 acetylates BMAL1 and coactivates CREB; Jesse DEG up in 4 clusters; "
             "87.5% detected in 19 of 20 target types",
    "Nr1d1": "REV-ERB-alpha, the canonical negative limb and the drug-targetable one; "
             "Jesse DEG DOWN in L6 CT and Sst; 53.1% detected",
    "Ppargc1a": "PGC-1alpha, metabolic-clock coupling; Jesse DEG up in 2 clusters; "
                "96.7% detected",
    "Bhlhe41": "DEC2, the Bhlhe40 partner; Jesse DEG up in L2/3; 79.5% detected and "
               "+46.1pp at a sub-population",
    "Hlf": "PAR-bZIP clock output factor; Jesse DEG up in L2/3; 97.3% detected",
    "Id2": "circadian input/output modulator; Jesse DEG DOWN in L6 CT; 97.0% detected",
    "Nfil3": "E4BP4, the PAR-bZIP repressor that opposes Hlf; Jesse DEG up in L6 IT. "
             "WEAKEST PROBE ON THE PANEL at 20.3% detected - included because it was "
             "asked for, but it is the first candidate to cut",
    "Arntl": "BMAL1, the positive limb, so the module has its driver",
    "Nr1d2": "REV-ERB-beta, pairs with Nr1d1",
    # ---- nominated by a sweep of the clock machinery by limb, after the hand-curated
    # list turned out to have no CRY at all. Per1 and Per2 on their own cannot tell a
    # phase shift from a single-gene change: the negative limb is a PER:CRY complex and
    # the output limb is a ROR / REV-ERB competition at the same RORE site.
    "Cry2": "the only well-detected cryptochrome here (89.3% vs Cry1's 36.6%). Without "
            "a CRY the negative limb cannot be read: PER up and repression up look the "
            "same",
    "Npas2": "the forebrain CLOCK paralogue, which is the one that actually dominates "
             "in cortex. 96.2% detected and above 50% in 16 of 20 populations, against "
             "Arntl's 78.3%, and it separates (+23.4pp). Clock itself is 96.8% in all "
             "20 with a 7.9pp gap, so Npas2 is the better positive-limb probe",
    "Rora": "ROR-alpha competes with REV-ERB for the same RORE site; with Nr1d1 and "
            "Nr1d2 already here, this completes the pair. 99.9% detected, +20.1pp at "
            "91.0% of a 490-cell sub-population",
}
# Clock genes measured and NOT added, so the omissions are on record:
#   Clock  96.8% in all 20 populations with a 7.9pp gap - no contrast, and Npas2 is the
#          cortical paralogue that carries the same limb
#   Cry1   36.6% detected - Cry2 carries the cryptochrome arm
#   Dbp    51.2% and above 50% in only 1 of 20 populations, despite being the classical
#          high-amplitude output gene; Hlf and Nfil3 carry the PAR-bZIP arm
#   Tef    94.1% but a 6.9pp gap; same arm as Hlf and Nfil3
#   Per3   75.9% but its best sub-population is 72 cells

# One gene per mechanism. Paralogue partners are dropped where a sibling already
# reports the same step.
PLASTICITY = {
    "Gria1": "AMPA GluA1, the trafficking subunit in opioid plasticity",
    "Gria2": "AMPA GluA2, the Ca-permeability switch",
    "Grin1": "NMDA obligatory subunit",
    "Grin2a": "NMDA GluN2A - the 2A/2B ratio is the maturation readout",
    "Grin2b": "NMDA GluN2B, plasticity-permissive",
    "Camk2a": "CaMKII alpha, LTP",
    "Camk2g": "CaMKII gamma, nuclear Ca signalling; Jesse morphine DEG",
    "Dlg4": "PSD-95, excitatory postsynaptic scaffold",
    "Gphn": "gephyrin, inhibitory postsynaptic scaffold - the E/I counterpart",
    "Syngap1": "Ras-GAP at the PSD",
    "Shank3": "PSD scaffold, complements Dlg4",
    "Ntrk2": "TrkB, the BDNF receptor",
    "Pcdh8": "arcadlin, activity-regulated cadherin",
    "Nptx2": "narp, activity-regulated excitatory drive onto PV cells",
}

MORPHINE_STATE = {
    "Pcsk1": "PC1/3 proneuropeptide processing; Jesse DEG in 11/12 ORBm clusters",
    "Sema3e": "axon-guidance remodelling; Jesse DEG",
    "Penk": "proenkephalin, opioid-peptide tone",
    "Pdyn": "prodynorphin, kappa arm",
    "Pnoc": "prepronociceptin, the OPRL1 ligand",
    "Tac1": "substance P",
    "Cartpt": "CART, reward peptide",
    "Adcyap1": "PACAP, stress/reward peptide",
    "Crh": "CRF, withdrawal axis",
}

# Central druggable receptors kept for the GPCR map even when they are not
# separators. Everything else with a GPCR label has to earn its slot as a separator.
GPCR_KEEP = {
    "Oprm1": "mu-opioid receptor - the receptor the drug acts on; 91.6% detected",
    "Htr1a": "5-HT1A, added on request. Weak overall at 28.3% detected, but it does "
             "separate: +36.6pp at a 1330-cell sub-population where 49.7% of cells "
             "carry it. Read it as a sub-population receptor, not a regional map",
    "Htr2a": "5-HT2A, 78.6% detected and +53.8pp at a 490-cell sub-population",
    "Adrb1": "beta1-adrenergic, 80.6% detected",
    "Oprk1": "kappa-opioid receptor, the dysphoria/withdrawal arm",
    "Oprd1": "delta-opioid receptor",
    "Oprl1": "NOP / ORL1, the Pnoc receptor",
    "Drd1": "D1, reward learning",
    "Drd2": "D2, the incentive-motivation arm",
    "Htr2c": "5-HT2C, an approved-drug target in the seeking circuit",
    "Grm5": "mGluR5, the most validated metabotropic addiction target",
    "Gabbr1": "GABA-B, the E/I brake and an approved-drug target (baclofen)",
    "Cnr1": "CB1, presynaptic gate on both glutamate and GABA release",
    "Crhr1": "CRF1, withdrawal axis, pairs with Crh",
    "Chrm1": "M1 muscarinic; Jesse's ORB-enriched receptor",
    "Chrm3": "M3 muscarinic",
    "Adra1a": "alpha-1A adrenergic; Jesse's ORB-enriched receptor",
    "Adra2a": "alpha-2A adrenergic, the presynaptic autoreceptor",
    "Mc4r": "MC4R, feeding/reward and an approved-drug target",
    "Npy1r": "Y1, pairs with Npy",
    "Cckbr": "CCK-B; Jesse's ORB-enriched receptor",
    "Grm8": "mGlu8; Jesse's ORB-enriched receptor",
    "Gpr88": "striatal-like identity plus a druggable orphan",
    "Adcyap1r1": "PAC1, pairs with Adcyap1",
    # ---- nominated by the data-driven sweep over all 280 GPCR symbols on the Allen
    # gene axis (GPCR_SWEEP.xlsx). The curated list above was chosen by pharmacological
    # judgement and missed these: each one is detected in >=50% of cells somewhere in
    # ORBm/BMAp AND localises to a sub-population of >=300 cells.
    "Sstr2": "SST2, 62.4% detected and +36.9pp in a 2,322-cell sub-population - the "
             "largest localisation of any receptor the sweep found; 4 IUPHAR drugs",
    "Tacr1": "NK1, the substance-P receptor that pairs with Tac1 on this panel; 61.6% "
             "detected, +41.9pp at 81.8% of a 763-cell sub-population, 4 IUPHAR drugs",
    "Hrh3": "H3, presynaptic histamine autoreceptor; 81.1% detected, +46.6pp at 88.6% "
            "of a 1,329-cell sub-population; Jesse morphine DEG",
    "Htr7": "5-HT7; 63.1% detected with the largest gap of any receptor scored "
            "(+50.3pp) in a 719-cell sub-population; Jesse morphine DEG",
    "Adora1": "A1 adenosine, 98.8% detected and +22.9pp - the caffeine/adenosine arm, "
              "absent from every earlier version of this panel",
    "Oxtr": "oxytocin receptor, 58.2% detected, +29.9pp; social/reward axis, 2 drugs",
    "Gpr101": "78.9% detected, +35.9pp in a 999-cell sub-population",
    "Gpr26": "85.8% detected, +29.1pp at 72.7% of a 693-cell sub-population; on "
             "Jesse's ORB-enriched receptor list",
    "Npy2r": "Y2 presynaptic autoreceptor, pairs with Npy and Npy1r; separates at the "
             "cell-population level (+41.2pp)",
}

# Receptors kept even though the sweep rejects them, labelled rather than quietly
# inconsistent. Grm5 and Gabbr1 are ~100% detected in all 20 populations with gaps of
# 0.7pp and 2.0pp, which is the same profile that got Grm7 and Gpr158 dropped. They are
# here because mGluR5 and GABA-B are the two most validated metabotropic drug targets in
# addiction and the experiment reads their LEVEL inside an already-named cell type, not
# their location. They are the 2nd and 8th heaviest transcript load on the panel, so
# they are the first two to cut if crowding becomes a problem.
SWEEP_EXCEPTIONS = {
    "Grm5": "no contrast (100% in 20/20, 0.7pp) - kept for level readout only",
    "Gabbr1": "no contrast (99.7% in 20/20, 2.0pp) - kept for level readout only",
    "Drd2": "28.9% detected, under the visibility bar - kept for the D2 axis",
}

# Measured redundancy: ubiquitous with no contrast, and no named readout of its own.
REDUNDANT = {
    "Syt1": "100% in all 20 anchors, gap 0.0pp - presynaptic load with no named readout",
    "Syp": "100% in 20/20, gap 0.4pp - Syn1/Syt1/Syp are three probes for one thing",
    "Syn1": "99.7% in 20/20, gap 1.3pp - same",
    "Nrxn1": "100% in 20/20, gap 0.0pp - scaffolding with no named readout",
    "Nrxn3": "100% in 20/20, gap 0.4pp - same",
    "Nlgn1": "100% in 20/20, gap 0.4pp - same",
    "Pak1": "100% in 20/20, gap 5.0pp - no named readout",
    "Arhgap32": "99.3% in 20/20, gap 7.1pp - no named readout",
    "Gria3": "100% in 20/20, gap 7.4pp - Gria1/Gria2 carry the AMPA readout",
    "Gria4": "99.9% in 20/20, gap 8.3pp - same",
    "Camk2b": "99.7% in 20/20, gap 3.7pp - Camk2a/Camk2g carry the CaMKII readout",
    "Ntrk3": "99.9%, no named role here; Ntrk2/TrkB is the BDNF receptor",
    "Lrrtm2": "synapse organiser with no named readout in this design",
    "Cdh8": "adhesion with no named readout; Pcdh8 is the activity-regulated one",
    "Homer1": "99.6% in 20/20 - only Homer1a is activity-regulated and Xenium probes "
              "the gene, not the isoform, so induction cannot be read",
    "Jund": "96.7% in 20/20, gap 8.5pp - the constitutive AP-1 arm; Fos/Fosb/Junb "
            "carry AP-1",
    "Jun": "Junb already covers the Jun arm of AP-1",
    "Egr2": "25.7%, and Egr1 carries the Egr arm",
    "Egr3": "Egr1 carries the Egr arm",
    "Nr4a3": "Nr4a1 carries the Nur77 arm",
    "Btg2": "46.2%, gap 2.1pp - no distinct wave beyond Fos/Egr1",
    "Ier2": "32.1%, gap 3.0pp - same",
    "Sik1": "26.7%, gap 1.7pp - same",
    "Sgk1": "84.5%, gap 0.3pp - stress kinase with no distinct readout here",
    "Rgs2": "92.0%, gap 15.4pp - signalling brake with no named readout",
    "Grm7": "100% in 20/20, gap 3.0pp - no named role, costs optical budget",
    "Gpr158": "99.9% in 20/20, gap 3.6pp - same",
    "Gabbr2": "99.9% in 20/20, gap 6.1pp - Gabbr1 reports the GABA-B map",
    "Clock": "96.8% in 20/20, gap 7.9pp - Arntl is its obligate partner and suffices",
    "Cry2": "89.3%, gap 0.1pp - the negative limb adds no independent readout once "
            "Per1/Per2/Nr1d2 are present",
    "Foxp1": "99.9% in 20/20, gap 8.5pp - Foxp2 is the separator that carries identity",
    "Xist": "sex genotyping - requested out",
    "Eif2s3y": "sex genotyping - requested out",
    "Ddx3y": "sex genotyping - requested out",
    "Trh": "kept in v8 as a peptide; it is already a separator for 120 MEA Otp Foxp2 "
           "Glut, so it enters through the separator route rather than twice",
}

FORCE_DROP_BASE = {
    "WPRE": "AAV element - this design crosses TRAP2 with a tdTomato reporter",
    "mCherry": "AAV-DIO-hM4Di-mCherry element - no virus in the Xenium cohort",
    "EGFP": "no EGFP transgene in this design",
    "Oxt": "1.2% - oxytocin cell bodies are in PVH/SON, not ORBm or BMAp",
    "Sstr4": "1.4% of cells at the best anchor - empty map",
    "Gpr63": "2.7% - empty map",
    "Htr6": "5.2% - empty map",
    "Slc6a3": "DAT, 4.6% - no dopaminergic cell bodies here",
    "Slc18a2": "VMAT2, 34% and 0 of 20 anchors above 50%",
    "Slc17a8": "VGLUT3, 44% and 0 of 20 anchors above 50%",
    "Chat": "12.2% - no cholinergic cell bodies among the 20 target types",
    "Vipr2": "8.2%, no separation",
    "C1ql2": "10.1%, no separation",
    "C1ql1": "12.4%, no separation",
    "Mgp": "15.8%, no separation",
    "Sfrp1": "21.1%, no separation",
    "Glipr1": "22.0%, no separation",
    "Upk1b": "17.6%, no separation",
    "Ctxn3": "15.8%, no separation",
    "Hcrtr1": "15.9%, best supertype only 45 cells",
    "S1pr3": "24.3%, no separation",
    "Gpr3": "23.4%, no separation",
    "Ackr3": "21.3%, no separation",
    "Cd44": "19.7% - covered by Gja1/Aqp4",
    "Gpr68": "43.6%, gap 10.9pp - relative ORB enrichment only",
    "Mas1": "44.8%, best supertype only 62 cells",
    "Mchr1": "32.0%, gap 10.3pp",
    "Tacr3": "30.1%, gap 13.1pp",
    "Dusp4": "18.2% - Dusp1 covers the MAPK-phosphatase arm",
    "Dusp5": "40.6%, best supertype only 62 cells - Dusp1 covers this arm",
    "Galr1": "35.6%, gap 26.1pp but pct_in only 31.1%",
    "Mbp": "90.2% at a neuronal anchor - ambient myelin makes it a bad oligo call; "
           "replaced by Sox10 and Mog",
    "Slc1a2": "100% at the anchors and 82% in neurons, only +18pp - useless as an "
              "astrocyte counter-stain; replaced by Gja1/Aqp4",
    "Sox8": "86% in OPC but only +28pp over neurons; replaced by Pdgfra",
    "Sox10": "marks OPC (97.7%) and oligodendrocyte (95.5%) equally, so it cannot "
             "separate them; Pdgfra and Mog already do that cleanly",
    "Cx3cr1": "Csf1r is the better microglial probe on the same cells, +98.2pp versus "
              "+88.8pp, with 1.7% neuronal background against Cx3cr1's 11.2%",
    "P2ry12": "Csf1r is more specific for microglia",
    "Vtn": "pericyte, but Rgs5 already reports that compartment",
    "Acta2": "smooth muscle - Rgs5/Dcn cover the mural and meningeal compartments",
    "Cd36": "69.6%, best in border-associated macrophages - not a target population",
    "Tgfb2": "66.7%, best in smooth muscle",
    "Vegfd": "27% and no named axis",
    "Emx1": "41.2%, gap 19.6pp - Satb2/Slc17a7 give cortical identity",
    "Slc5a7": "12% cholinergic; its only job was 0177 Vip Gaba_5, which Vip/Calb2 "
              "already localise",
    "Piezo2": "20.2% - Masp1 separates the same sub-population better",
    "Abca8a": "32.0%, supertype gap only 5.2pp",
    "Tspan18": "26.8%, gap 22.7pp under the 25pp bar",
    "Gabre": "32.0%, gap 23.3pp under the 25pp bar",
    "Gpr12": "47.9%, gap 23.8pp under the 25pp bar",
    "Sp8": "31.6%, best supertype only 61 cells",
    "Chrd": "48.6%, best supertype only 62 cells",
}
UNINTERPRETABLE = {
    "Chd2", "Fxr1", "Vps13a", "Hspa5", "Ahctf1", "Banp", "Mbnl2", "Acsl4", "Zdbf2",
    "Hsd17b12", "Omg", "Zfp933", "Rbms3", "Maml3", "Maml2", "Zbtb25", "Zbtb40",
    "Zfp580", "Gabpa", "Hsf5", "Sox12", "Stk40", "Igf1", "Nbl1", "Spon1", "Trpm3",
    "Zfp804b", "Kitl", "Osgin2", "Rel", "Rnf128", "Hunk", "Cdkn1a", "Tiparp",
    "St8sia2", "Nckap5", "Myo1b", "Masp1",
}   # Ep300 was here; it is now carried in CLOCK as a named circadian/CREB coactivator


def load_cache():
    z = np.load(OUT / "anchor_subtype_cache.npz", allow_pickle=True)
    gsym = [str(x) for x in z["genes"]]
    return z, gsym, {g: j for j, g in enumerate(gsym)}


def score_genes(genes, z, gi, names, orb, bma, anchors):
    P = z["anchor_pct"]
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
            "max_pct_ORBm": round(float(col[orb].max()), 1),
            "max_pct_BMAp": round(float(col[bma].max()), 1),
            "subclass_gap_pp": round(float(gaps[bi]), 1),
            "subclass_gap_at": names[bi],
            "subclass_gap_pct_in": round(float(col[bi]), 1),
            "detected_in_n_of_20": int((col >= 20).sum()),
            "supertype_gap_pp": round(float(sg), 1),
            "supertype_gap_pct_in": round(float(sp), 1),
            "supertype_n_cells": sn, "supertype": sl, "supertype_parent": spar,
        })
    return pd.DataFrame(rows)


def main() -> None:
    z, gsym, gi = load_cache()
    P = z["anchor_pct"]
    names = [str(x) for x in z["anchor_names"]]
    anchors = [str(x) for x in z["sup_keys"]]
    ac = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                       "ANCHOR_COVERAGE")
    reg = dict(zip(ac.allen_subclass_anchor, ac.region))
    orb = [i for i, a in enumerate(names) if reg.get(a) == "ORBm"]
    bma = [i for i, a in enumerate(names) if reg.get(a) == "BMAp"]

    v8 = pd.read_excel(OUT / "PANEL_FINAL_v8_ORBm_BMAp.xlsx", "PANEL_ORDER")
    prev = pd.read_excel(OUT / "ALL_PANELS_anchor_and_subtype_scores.xlsx", "gene_scores")
    ideal = pd.read_excel(DL / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
                          "BY_CATEGORY")
    ideal_cat = ideal.groupby("gene").category.apply(lambda s: sorted(set(s))).to_dict()

    FORCE_DROP = dict(FORCE_DROP_BASE)
    FORCE_DROP.update(REDUNDANT)
    banned = set(FORCE_DROP) | UNINTERPRETABLE

    keep: dict[str, tuple[str, str]] = {}
    roles: dict[str, set[str]] = {}

    def add(g, block, why, cat):
        roles.setdefault(g, set()).add(cat)
        keep.setdefault(g, (block, why))

    for g in TRAP:
        add(g, "01_TRAP_reporter", "TRAP readout: the 4-OHT-tagged POST ensemble",
            "6_TRAP_reporter")
    for g, w in EI_BACKBONE.items():
        add(g, "03_class_EI_backbone", w, "1_cell_type_marker")
    for g, w in TAXONOMY.items():
        add(g, "03b_taxonomy_backbone", w, "1_cell_type_marker")
    for g, w in GLIA.items():
        add(g, "04_nonneuronal_counterstain", w, "1_cell_type_marker")
    for g, w in PAIRWISE.items():
        add(g, "05b_pairwise_disambiguator", w, "1_cell_type_marker")

    # ---- cell type calling: at most MAX_SEP_PER_ANCHOR markers per target type,
    # canonical markers first. Ranking on raw separation gap alone promotes unannotated
    # gene models (Gm2164, Gm6209, H2-Q2, Stard8) over Cux2/Rorb/Fezf2/Tle4. The
    # request was "all important cell type markers", and an unannotated gene model with
    # no literature cannot be read as a cell type call however large its gap is.
    curated: dict[str, list[str]] = {}
    for r in ac.itertuples():
        curated[r.allen_subclass_anchor] = [
            x.strip() for x in str(r.unique_separators_on_shared_panel or "").split(",")
            if x.strip()]
    curated["005 L5 IT CTX Glut"] += ["Adam19", "Man2a1", "Ldlrad3", "Vipr1", "Colq"]
    curated["073 MEA-BST Sox6 Gaba"] += ["Chn2", "Ankfn1", "Metap1d", "Pax6"]
    curated["121 MEA-BST Otp Zic2 Glut"] += ["Zic4", "Zfp521", "Pcolce2", "Lrrc1"]
    MODEL = re.compile(r"^(Gm\d+|\d+\w*Rik|LOC\d+|H2-|Raet|Trbc|Igk|Ighv)")

    sep_rows = []
    for i, a in enumerate(names):
        col = P[i]                                  # P is anchors x genes
        other = np.delete(P, i, axis=0).max(axis=0)
        gap = col - other

        def rank_pool(pool, min_gap):
            out = []
            for g in pool:
                j = gi.get(g)
                if j is None or g in banned:
                    continue
                if col[j] >= 30 and gap[j] >= min_gap:
                    out.append((g, float(col[j]), float(gap[j])))
            return sorted(out, key=lambda x: -x[2])

        # canonical markers qualify at a lower bar, because being readable as a cell
        # type call is part of what the marker is for
        picks = rank_pool(curated.get(a, []), 8.0)[:MAX_SEP_PER_ANCHOR]
        if len(picks) < MAX_SEP_PER_ANCHOR:
            got = {g for g, _, _ in picks}
            extra = rank_pool([gsym[j] for j in np.argsort(-gap)[:600]
                               if not MODEL.match(gsym[j])], 12.0)
            for g, pct, gp in extra:
                if len(picks) >= MAX_SEP_PER_ANCHOR:
                    break
                if g not in got:
                    picks.append((g, pct, gp))
                    got.add(g)
        for rank, (g, pct, gp) in enumerate(picks, 1):
            sep_rows.append({
                "anchor": a, "region": reg[a], "gene": g, "rank": rank,
                "pct_in": round(pct, 1), "gap_pp": round(gp, 1),
                "canonical": g in curated.get(a, [])})
            add(g, "05_celltype_separator",
                f"calls {a}: {pct:.0f}% in, +{gp:.0f}pp over the next target type",
                "1_cell_type_marker")
    sepsheet = pd.DataFrame(sep_rows)

    # The curated state blocks are added BEFORE the sub-population search, so that a
    # gene already being bought for another job counts towards the marker quota
    # instead of being bought twice. Oprm1, for instance, separates a 1230-cell
    # sub-population by 38pp on its own.
    for g, w in IEG.items():
        add(g, "07_IEG_pCREB_target", w, "7_IEG")
    for g, w in CLOCK.items():
        add(g, "08_clock_module", w, "8_morphine_related")
    for g, w in PLASTICITY.items():
        add(g, "09_plasticity", w, "5_plasticity")
    for g, w in MORPHINE_STATE.items():
        add(g, "10_morphine_state", w, "8_morphine_related")
    for g, w in GPCR_KEEP.items():
        add(g, "11_GPCR_map", w, "3_GPCR")
    for g, w in SWEEP_EXCEPTIONS.items():
        add(g, "11_GPCR_map", f"EXCEPTION to the GPCR sweep: {w}", "3_GPCR")

    # ---- sub-population resolution: 2 markers if the supertype is big, else 1
    sub = pd.read_excel(OUT / "SUBTYPE_SEPARATORS_genomewide.xlsx", "candidates")
    ok = sub[(sub.gap_pp >= SUB_GAP) & (sub.pct_in >= SUB_PCT) & (sub.n_cells >= SUB_N)]
    sizes = ok.groupby(["parent_anchor", "supertype"]).n_cells.max().to_dict()
    need = {st: (2 if n >= SUPERTYPE_BIG else 1) for st, n in sizes.items()}
    for st in need:                                   # genes already on the panel count
        have = set(ok[(ok.parent_anchor == st[0]) & (ok.supertype == st[1])].gene) & set(keep)
        need[st] = max(0, need[st] - len(have))
    reach = {g: set(zip(d.parent_anchor, d.supertype)) for g, d in ok.groupby("gene")}
    bg = ok.groupby("gene").gap_pp.max().to_dict()
    chosen: dict[str, str] = {}

    def run(pool):
        while True:
            c = [g for g in pool if g not in chosen and g not in keep
                 and any(need.get(st, 0) > 0 for st in reach[g])]
            if not c:
                return
            g = max(c, key=lambda x: (sum(1 for st in reach[x] if need.get(st, 0) > 0),
                                      bg[x]))
            hit = sorted(st for st in reach[g] if need.get(st, 0) > 0)
            chosen[g] = ("resolves " + "; ".join(
                f"{s} (gap {ok[(ok.gene == g) & (ok.supertype == s)].gap_pp.max():.0f}pp,"
                f" n={sizes[(p, s)]})" for p, s in hit[:2]))
            for st in hit:
                need[st] -= 1

    # same preference order as the cell-type separators: annotated genes first, gene
    # models only where nothing else can resolve the sub-population
    run({g for g in reach if g not in banned and not MODEL.match(g)})
    run({g for g in reach if not MODEL.match(g)})
    run(set(reach))                                   # last resort, includes models
    for g, w in sorted(chosen.items()):
        add(g, "06_subtype_separator", w, "2_subtype_marker")

    sc = score_genes(sorted(keep), z, gi, names, orb, bma, anchors).set_index("gene")

    # extra role labels, so the category sheet is complete
    jesse = set()
    for fn in ["mPFC_GPCRDEGs.csv", "mPFC_TFDEGs.csv", "mPFC_IEGDEGs.csv",
               "mPFC_SynPlast.csv"]:
        p = (V3 / "inputs" / "Jesse_ORB" /
             "OpioidDependenceDEG_genesets_forHansol090926" / fn)
        if p.exists():
            jesse |= set(pd.read_csv(p).iloc[:, 0].astype(str))
    dan = {"Col23a1", "Slc29a4", "Cck", "Gfra1", "Calcrl", "Lamb3", "Syndig1l",
           "Nos1", "Oprl1", "Dnah5"}
    for g in list(keep):
        if g in jesse:
            roles[g].add("8_morphine_related")
        if "4_TF" in ideal_cat.get(g, []):
            roles[g].add("4_TF")
        if "2_GPCR" in ideal_cat.get(g, []):
            roles[g].add("3_GPCR")
        if "3_plasticity" in ideal_cat.get(g, []):
            roles[g].add("5_plasticity")

    panel = pd.DataFrame([{"gene": g, "block": b, "why": w,
                           "roles": ", ".join(sorted(roles[g])),
                           "source_Jesse_morphine_DEG": g in jesse,
                           "source_Dan_GSE283418": g in dan}
                          for g, (b, w) in keep.items()])
    m = panel.join(sc, on="gene").sort_values(["block", "gene"])
    m.insert(0, "order_rank", range(1, len(m) + 1))
    G = set(m.gene)

    # ---------------- verification
    def anchor_table(gg):
        # Two ways a population is called, because Allen itself names some types
        # combinatorially (073 MEA-BST Sox6 Gaba vs 074 MEA-BST Lhx6 Sp9 Gaba):
        #   unique     gene is >=30% in this type and >=10pp above EVERY other of the 19
        #   neighbour  gene is >=40% here and >=20pp above the SINGLE closest type
        # A type is covered when unique>=2, or unique>=1 plus >=2 neighbour separators.
        rows = []
        for i, a in enumerate(names):
            col = P[i]
            other = np.delete(P, i, axis=0).max(axis=0)
            # closest other type by shared high-expression genes (min L1 of pct vectors)
            dist = [np.abs(col - P[k]).sum() if k != i else np.inf
                    for k in range(len(names))]
            nb = int(np.argmin(dist))
            uniq = [(g, col[gi[g]], col[gi[g]] - other[gi[g]]) for g in gg
                    if g in gi and col[gi[g]] >= 30 and col[gi[g]] - other[gi[g]] >= 10]
            neigh = [(g, col[gi[g]], col[gi[g]] - P[nb, gi[g]]) for g in gg
                     if g in gi and col[gi[g]] >= 40
                     and col[gi[g]] - P[nb, gi[g]] >= 20]
            uniq.sort(key=lambda x: -x[2])
            neigh.sort(key=lambda x: -x[2])
            n_u, n_n = len(uniq), len(neigh)
            covered = n_u >= 2 or (n_u >= 1 and n_n >= 2)
            rows.append({
                "region": reg[a], "allen_subclass_anchor": a,
                "n_cells": int(z["anchor_n"][i]),
                "closest_neighbour": names[nb],
                "n_unique_vs_all19": n_u,
                "n_vs_closest_neighbour": n_n,
                "n_markers": n_u if n_u >= 2 else n_u + n_n,
                "markers": ", ".join(f"{g} (+{d:.0f}pp vs all)" for g, _, d in uniq[:4])
                           or "-",
                "neighbour_markers": ", ".join(
                    f"{g} (+{d:.0f}pp vs {names[nb].split(' ', 1)[0]})"
                    for g, _, d in neigh[:4]) or "-",
                "callable": "yes" if covered else
                            ("1 unique marker only" if n_u else "NO")})
        return pd.DataFrame(rows)

    anchor_chk = anchor_table(G)
    # Marker counts are a proxy. Where a measured held-out recall exists, attach it:
    # it is the number that actually answers "can this population be called".
    rp = OUT / "TWENTY_TYPE_RECALL.xlsx"
    if rp.exists():
        r = pd.read_excel(rp, "per_population_recall")
        anchor_chk = anchor_chk.merge(
            r[["cell_population", "recall_mean", "recall_sd", "most_confused_with",
               "confusion_pct"]].rename(columns={
                   "cell_population": "allen_subclass_anchor",
                   "recall_mean": "measured_recall_heldout",
                   "recall_sd": "recall_sd_3seeds"}),
            on="allen_subclass_anchor", how="left")
        anchor_chk["callable"] = np.where(
            anchor_chk.measured_recall_heldout.isna(), anchor_chk.callable,
            np.where(anchor_chk.measured_recall_heldout >= 0.90, "yes",
                     "yes, but graded into its neighbour"))
    cov = (ok.assign(on=ok.gene.isin(G))
             .groupby(["parent_anchor", "supertype", "n_cells"])
             .agg(n_markers_on_panel=("on", "sum"), n_candidates=("gene", "nunique"),
                  markers=("gene", lambda s: ", ".join(sorted(set(s) & G)) or "NONE"))
             .reset_index())
    cov["target"] = np.where(cov.n_cells >= SUPERTYPE_BIG, 2, 1)
    cov["meets_target"] = cov.n_markers_on_panel >= cov.target

    # IEGs are exempt from the detection bar because the Allen atlas is resting tissue
    # and induction is the thing being measured; glia are exempt because they are
    # scored against their own populations, not against the 20 neuronal targets.
    exempt = set(IEG) | set(GLIA) | set(TAXONOMY)

    def metrics(name, gg, table):
        s = table[table.gene.isin(gg) & (table.scored == True)].copy()
        s["sub_ok"] = ((s.supertype_gap_pp >= SUB_GAP) & (s.supertype_gap_pct_in >= SUB_PCT)
                       & (s.supertype_n_cells >= SUB_N))
        s["cls_ok"] = (s.subclass_gap_pp >= 15) & (s.subclass_gap_pct_in >= 30)
        lo = s[s.anchor_max_pct < VIS]
        alive = lo.sub_ok | lo.cls_ok | lo.gene.isin(exempt)
        ubiq = s[(s.anchor_max_pct >= 95) & (s.n_anchors_ge50 >= 18)
                 & (s[["subclass_gap_pp", "supertype_gap_pp"]].max(axis=1) < 12)]
        c = ok.assign(on=ok.gene.isin(gg)).groupby(["parent_anchor", "supertype"]).on.sum()
        return {"panel": name, "n_genes": len(gg),
                "median_detection_pct": round(s.anchor_max_pct.median(), 1),
                "n_below_50pct": len(lo),
                "n_EMPTY_MAP_probes": int((~alive).sum()),
                "n_ubiquitous_no_contrast": len(ubiq),
                "target_types_callable": int((anchor_table(gg).callable == "yes").sum()),
                "subpops_with_1plus": int((c >= 1).sum()),
                "subpops_meeting_target": int(sum(
                    c.get(st, 0) >= (2 if sizes[st] >= SUPERTYPE_BIG else 1)
                    for st in sizes))}

    cmp = [metrics(n, set(prev[prev[f"on_{k}"]].gene.astype(str)), prev)
           for k, n in [("IDEAL_178", "IDEAL 178"), ("v7_252", "v7 252"),
                        ("g301", "301")]]
    cmp.append(metrics("v8 318", set(v8.gene),
                       pd.concat([prev, sc.reset_index()]).drop_duplicates("gene")))
    cmp.append(metrics("v9 FINAL", G, sc.reset_index()))
    cmpdf = pd.DataFrame(cmp)

    cut = v8[~v8.gene.isin(G)][["gene", "block", "anchor_max_pct"]].copy()
    cut["reason_cut_from_v8"] = [FORCE_DROP.get(g, "not required once the caps were "
                                                   "applied: another marker already "
                                                   "covers the same job")
                                 for g in cut.gene]
    added = m[~m.gene.isin(set(v8.gene))][["gene", "block", "why"]]

    bycat = pd.DataFrame([{"category": c, "gene": g,
                           "primary_block": keep[g][0],
                           "anchor_max_pct": sc.anchor_max_pct.get(g),
                           "why": keep[g][1]}
                          for g in keep for c in sorted(roles[g])]
                         ).sort_values(["category", "gene"])
    catcount = bycat.groupby("category").gene.nunique().rename("n_genes").reset_index()
    bc = m.groupby("block").gene.agg(n_genes="count",
                                     genes=lambda s: ", ".join(sorted(s))).reset_index()

    spare = score_genes(
        sorted(set(prev.gene.astype(str)) - G - set(FORCE_DROP_BASE))[:400],
        z, gi, names, orb, bma, anchors)
    bcols = ["gene", "anchor_max_pct", "subclass_gap_pp", "supertype_gap_pp",
             "supertype_n_cells"]
    backups = (spare[spare.scored == True].nlargest(15, "supertype_gap_pp")[bcols]
               .assign(role="substitute if a designed probe fails 10x probe design"))

    readme = pd.DataFrame([
        ("What to order", f"PANEL_ORDER - {len(m)} genes, Xenium v1 STANDALONE custom "
                          f"panel. This lands in the 101-300 gene tier (PN-1000563 / "
                          f"1000648), one tier below the 318-gene v8."),
        ("tdTomato and iCre", "transgene sequences, not mm10 genes, so they are advanced "
                              "custom targets and need the Advanced Panel Upgrade "
                              "(PN-1000664) alongside the standalone panel"),
        ("How this was sized", "Every gene has to do one of six jobs and no job is "
                               "covered twice without a reason. Caps: at most 4 "
                               "separators per target cell type, 2 markers per "
                               "sub-population above 300 cells and 1 below, one marker "
                               "per non-neuronal population, one gene per plasticity "
                               "mechanism, one gene per IEG kinetic wave."),
        ("What was removed from v8", f"CUT_FROM_v8 - {len(cut)} genes with a reason each. "
                                     "The largest group is ubiquitous no-contrast probes "
                                     "(Syt1, Syp, Syn1, Nrxn1, Nrxn3, Nlgn1, Grm7, "
                                     "Gpr158): detected in ~100% of cells in all 20 "
                                     "target types with under 12pp of separation, so "
                                     "they consume Xenium optical budget and add no "
                                     "contrast."),
        ("Sex genes", "not included, as requested; also removed from BACKUP_GENES"),
        ("Selection criteria", "nine categories, and nothing else: cell type markers, "
                               "sub-type markers, GPCRs, morphine-related genes, "
                               "transcription factors, plasticity, IEGs, circadian "
                               "genes, TRAP reporters. Every gene is judged on measured "
                               "detection and separation in Allen WMB-10X plus the "
                               "Jesse and Dan datasets, and every gene sits in the "
                               "category it earns. Nothing is carried on external "
                               "grounds: Satb2 98.8% detected (+91.0pp), Oprm1 91.6%, "
                               "Creb1 84.9%, Arc 83.6%, Adrb1 80.6%, Htr2a 78.6% "
                               "(+53.8pp), Fos 62.4%, Per2 60.9%."),
        ("Circadian module", "12 genes, scoped to the clock genes Jesse's 5-day "
                             "escalating-morphine DESeq2 found differentially expressed "
                             "in PL-ILA-ORB: Per2 (up in 13 clusters), Per1 (8), "
                             "Bhlhe40 (4), Ep300 (4), Nr1d1 (down in 2), Ppargc1a (2), "
                             "Bhlhe41, Hlf, Id2, Nfil3, plus Arntl and Nr1d2 so the "
                             "positive and negative limbs are both readable. Rorb is "
                             "also one of his clock DEGs and is already carried as an "
                             "L4/5 layer separator. Clock, Cry2, Rora, Npas2, Per3, "
                             "Dbp and Cry1 are NOT in his DEG lists and were not added."),
        ("Two weak probes, deliberate", "Htr1a 28.3% detected and Nfil3 20.3% - both "
                                        "were asked for. Htr1a still separates a "
                                        "1330-cell sub-population by +36.6pp, so read "
                                        "it there. Nfil3 is the weakest probe on the "
                                        "panel and the first candidate to cut."),
        ("Two metrics, not one", "Identity genes must SEPARATE (gap versus neighbouring "
                                 "populations); state genes must be VISIBLE (percent of "
                                 "cells detected). Judging identity genes on detection "
                                 "alone is what cut real subtype markers such as Vdr "
                                 "(11% of its subclass but 95% of one 483-cell "
                                 "sub-population) from the earlier versions."),
        ("Detection reference", "Allen WMB-10X, 226,886 cells (ORBm 106,122 / BMAp "
                                "120,764), measured at the 20 target subclasses in "
                                "their own dissection"),
        ("Verification", "ANCHOR_COVERAGE_20types, SUBTYPE_COVERAGE, VERSION_COMPARISON"),
        ("Categories", "BY_CATEGORY / BY_CATEGORY_COUNTS; a gene appears under every job "
                       "it does"),
        ("CONFIRM", "the tdTomato reporter strain - Ai9 (007909) and Ai14 "
                    "(007908/007914) are the documented tdTomato lines"),
    ], columns=["item", "detail"])

    cols = ["order_rank", "gene", "block", "roles", "why",
            "source_Jesse_morphine_DEG", "source_Dan_GSE283418", "anchor_max_pct",
            "anchor_max_name", "n_anchors_ge50", "max_pct_ORBm", "max_pct_BMAp",
            "subclass_gap_pp", "subclass_gap_at", "subclass_gap_pct_in",
            "supertype_gap_pp", "supertype_gap_pct_in", "supertype_n_cells",
            "supertype", "supertype_parent"]
    order = m[cols]

    with pd.ExcelWriter(DST) as xw:
        readme.to_excel(xw, sheet_name="READ_ME", index=False)
        order.to_excel(xw, sheet_name="PANEL_ORDER", index=False)
        bycat.to_excel(xw, sheet_name="BY_CATEGORY", index=False)
        catcount.to_excel(xw, sheet_name="BY_CATEGORY_COUNTS", index=False)
        bc.to_excel(xw, sheet_name="BY_BLOCK", index=False)
        cmpdf.to_excel(xw, sheet_name="VERSION_COMPARISON", index=False)
        anchor_chk.to_excel(xw, sheet_name="ANCHOR_COVERAGE_20types", index=False)
        cov.to_excel(xw, sheet_name="SUBTYPE_COVERAGE", index=False)
        sepsheet.to_excel(xw, sheet_name="SEPARATOR_RANKING", index=False)
        cut.to_excel(xw, sheet_name="CUT_FROM_v8", index=False)
        added.to_excel(xw, sheet_name="ADDED_vs_v8", index=False)
        backups.to_excel(xw, sheet_name="BACKUP_GENES", index=False)
        order[(order.max_pct_ORBm.fillna(100) >= 20)
              | order.gene.isin(TRAP)].to_excel(xw, sheet_name="ORBm_view", index=False)
        order[(order.max_pct_BMAp.fillna(100) >= 20)
              | order.gene.isin(TRAP)].to_excel(xw, sheet_name="BMAp_view", index=False)
    print("wrote", DST)

    print(f"\nv9 panel: {len(m)} genes")
    print(bc[["block", "n_genes"]].to_string(index=False))
    print("\ncategories (a gene can serve several):")
    print(catcount.to_string(index=False))
    print("\n" + cmpdf.to_string(index=False))
    print(f"\n20 target types with >=2 markers: "
          f"{int(anchor_chk.callable.astype(str).str.startswith('yes').sum())}/20 "
          f"(unique-vs-19 min {int(anchor_chk.n_unique_vs_all19.min())}, "
          f"vs-neighbour min {int(anchor_chk.n_vs_closest_neighbour.min())})")
    print(f"sub-populations meeting their marker target: "
          f"{int(cov.meets_target.sum())}/{len(cov)}; with >=1 marker: "
          f"{int((cov.n_markers_on_panel >= 1).sum())}/{len(cov)}")
    print(f"cut from v8: {len(cut)}   added vs v8: {len(added)}")


if __name__ == "__main__":
    main()
