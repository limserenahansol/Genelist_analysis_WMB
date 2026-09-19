"""Build the final panel from every verified result in this analysis.

Architecture decision, and why: keep the ADD-ON route (10x Mouse Brain base panel +
custom probes) rather than a standalone custom panel. The disjoint-gene control
showed the base panel's own genes mark 45.6 of the 96 markable supertypes at a
matched 97-gene budget, versus 25.0 for the genes unique to the standalone design.
The base panel is not filler - it is the strongest single contributor to
sub-population discovery, and on the add-on route it is free.

So the final list = 248 base genes (free, all measured) + a custom set built from:

  1  TRAP tags                 tdTomato, iCre - not mouse genes, must be custom
  2  Cell-type separators      load-bearing anchors from the existing design, off-base
  3  Genome-wide anchor rescue the best markers for anchors the current panel covers
                               badly, taken from the full 32,285-gene screen
  4  Morphine state            verified detectable and broad across the 12 ORBm anchors
  5  Receptor map              existing druggable GPCRs plus the newly verified ones
  6  Sub-population discovery  the greedy minimum set covering every markable supertype
  7  BMAp depth                Berg & Scherrer genes that clear specificity 1.0

Every gene carries its provenance, its measured detectability, and the rule that
admitted it. Detectability is the region-restricted figure computed from the
locally cached Allen matrices (226,886 cells), not an estimate.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PA = OUT / "PANEL_A_current_166genes_119custom.xlsx"
PC = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"
DET = OUT / "allen_detectability_all_candidates.xlsx"
GW = OUT / "allen_genomewide_marker_search.xlsx"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"
RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
DST = OUT / "FINAL_ULTIMATE_PANEL.xlsx"

DETECT = 50.0     # percent-of-cells bar, measured in Allen
TRAP = ["tdTomato", "iCre"]


def main() -> None:
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    cur = pd.read_excel(PA, "SHARED_PANEL_ORDER")
    ac = pd.read_excel(PA, "ANCHOR_COVERAGE")
    det = pd.read_excel(DET, "summary").set_index("gene")
    anch_mk = pd.read_excel(GW, "anchor_markers")
    sup_mk = pd.read_excel(GW, "supertype_markers")
    mini = pd.read_excel(GW, "minimum_gene_set")
    dan = pd.read_excel(DAN, "all_98_genes")
    rank = pd.read_excel(RANK, "ranking_all").set_index("gene")

    def pct(g):
        return float(det.max_pct.get(g, np.nan))

    picks = {}   # gene -> dict

    def add(gene, block, why, rule):
        if gene in picks:
            picks[gene]["why"] += f" ALSO: {why}"
            return
        picks[gene] = {"gene": gene, "block": block, "rule": rule, "why": why,
                       "allen_max_pct": pct(gene), "on_base_free": gene in base}

    # 1 TRAP tags
    for g in TRAP:
        add(g, "1_TRAP_tag",
            "Reads the genetic tag directly. tdTomato is the permanent TRAP label; iCre is the "
            "Fos2A-iCreER driver transcript and an independent confirmation of the same cells. "
            "CONFIRM the reporter strain number - the probe targets the tdTomato coding sequence, "
            "so any Rosa26-CAG-LSL-tdTomato line works, but a different fluorophore would read nothing.",
            "mandatory: not a mouse gene, cannot come from the base panel")

    # 2 load-bearing cell-type separators from the existing design
    sep = set()
    for s in ac.unique_separators_on_shared_panel.fillna(""):
        sep |= {x.strip() for x in s.split(",") if x.strip()}
    for g in sorted(sep):
        serves = cur.loc[cur.gene == g, "serves"]
        add(g, "2_celltype_separator",
            f"Dedicated separator in ANCHOR_COVERAGE for {serves.iat[0] if len(serves) else 'a target population'}. "
            f"Detected in {pct(g):.0f}% of cells at its best anchor.",
            "identifies one of the 20 target populations")

    # 3 genome-wide rescue for anchors the current design covers badly
    weak = anch_mk.groupby("group").on_panel_C.sum()
    weak = [a for a in weak.index if weak[a] <= 1]
    for a in weak:
        cand = anch_mk[(anch_mk.group == a) & (~anch_mk.on_panel_C)].nlargest(3, "gap")
        for r in cand.itertuples():
            add(r.gene, "3_genomewide_anchor_rescue",
                f"Best genome-wide marker for {a}: detected in {r.pct_in:.0f}% of its cells versus "
                f"{r.pct_out_max:.0f}% in the nearest competing population, a {r.gap:.0f} point margin. "
                f"The current design has at most one marker for this population.",
                "closes a population the existing panel identifies weakly")

    # 4 morphine state, measured
    mor = rank[(rank.n_orbm >= 4)].copy()
    mor["pct"] = [pct(g) for g in mor.index]
    mor = mor[(mor.pct >= DETECT)].sort_values(["n_orbm", "pct"], ascending=False)
    # No head(N) cut: the first build silently dropped Camk2g, the only DOWN gene,
    # and Bhlhe40. Every gene clearing both bars is taken.
    for g, r in mor.iterrows():
        add(g, "4_morphine_state",
            f"Differentially expressed in {int(r.n_orbm)} of the 12 ORBm populations ({r.direction}), "
            f"glut {int(r.n_glut)} / GABA {int(r.n_gaba)}, detected in {r.pct:.0f}% of cells. "
            f"Source: Jesse Niehaus 5-day escalating morphine, DESeq2 subclass pseudobulk.",
            "reports the morphine-dependent state")

    # 5 receptor map: keep existing druggable GPCRs, add the newly verified ones
    for g in sorted(cur.loc[cur.block.str.contains("GPCR"), "gene"]):
        if pct(g) >= DETECT or g in base:
            add(g, "5_receptor_map",
                f"Druggable receptor already on the design; detected in {pct(g):.0f}% of cells.",
                "maps a drug target in place")
    for g in ["Chrm3", "Adra1a", "Hrh3", "Adra1b", "Hrh1"]:
        if pct(g) >= DETECT:
            add(g, "5_receptor_map",
                f"Receptor family with no coverage on the current panel. Detected in {pct(g):.0f}% "
                f"of cells - verified from the Allen matrices, not estimated. "
                f"{'M3 muscarinic; the panel had only M2 and M1.' if g == 'Chrm3' else ''}"
                f"{'Alpha-1A adrenergic; the panel has no adrenergic receptor at all.' if g == 'Adra1a' else ''}"
                f"{'Histamine H3; the panel has no histamine receptor.' if g == 'Hrh3' else ''}",
                "opens a receptor family the panel cannot currently see")

    # 6 sub-population discovery: the greedy minimum set
    for r in mini.itertuples():
        n_cov = int(r.new_supertypes_covered)
        add(r.gene, "6_subpopulation_discovery",
            f"From the genome-wide screen of all 32,285 atlas genes: marks {n_cov} sub-population(s) "
            f"(Allen supertypes) that no other selected gene marks. Detected in "
            f"{pct(r.gene) if not np.isnan(pct(r.gene)) else float('nan'):.0f}% of cells where scored. "
            f"This is the axis the previous 701-gene shortlist never searched.",
            "splits a known population into sub-populations")

    # 4b Class backbone - without these you cannot even call a cell a neuron.
    # The first build omitted this block entirely, dropping Snap25/Rbfox3/Slc32a1
    # despite 99-100% detection.
    for g in sorted(cur.loc[cur.block.str.contains("class_backbone"), "gene"]):
        if pct(g) >= DETECT:
            add(g, "4b_class_backbone",
                f"Class backbone: {cur.loc[cur.gene==g,'serves'].iat[0]}. Detected in {pct(g):.0f}% "
                f"of cells. Without these a cell cannot be called a neuron, or split glutamatergic "
                f"from GABAergic, before any finer typing is attempted.",
                "establishes cell class before subtype")

    # 4c Activity and plasticity - the panel's second job, also omitted first time.
    # IEGs are exempt from the detectability bar: the Allen atlas is mostly resting
    # tissue, so a low baseline percentage understates an activity-induced gene.
    for g in sorted(cur.loc[cur.block == "5_IEG", "gene"]):
        add(g, "4c_activity_IEG",
            f"Immediate-early gene reporting recent activity, paired with the TRAP tag. "
            f"Baseline detection {pct(g):.0f}% - deliberately NOT filtered on this, because the "
            f"atlas measures resting tissue and an activity-induced gene is low at rest by "
            f"definition. Filtering IEGs on baseline detectability would be a category error.",
            "reports whether the cell was recently active")
    for g in sorted(cur.loc[cur.block == "7_plasticity", "gene"]):
        if pct(g) >= DETECT:
            add(g, "4d_plasticity",
                f"Synaptic plasticity machinery: {cur.loc[cur.gene==g,'serves'].iat[0]}. "
                f"Detected in {pct(g):.0f}% of cells.",
                "reports synaptic state alongside activity")

    # 4e Identity transcription factors and published regional markers
    for blk, lab, rule in (("8_TF_identity", "4e_identity_TF", "lineage and laminar identity"),
                           ("9_published_regional", "4f_regional_marker",
                            "published region marker, re-verified in Allen")):
        for g in sorted(cur.loc[cur.block == blk, "gene"]):
            if pct(g) >= DETECT:
                add(g, lab,
                    f"{cur.loc[cur.gene==g,'serves'].iat[0]}. Detected in {pct(g):.0f}% of cells; "
                    f"carried over from the MSGS111 design and re-verified against the Allen matrices.",
                    rule)

    # 7 BMAp depth that clears the specificity bar
    for r in dan[dan.max_spec >= 1.0].itertuples():
        add(r.gene, "7_BMAp_depth",
            f"Berg & Scherrer GSE283418 amygdala panel. Allen BMAp specificity {r.max_spec:.2f} "
            f"(above the 1.0 bar, so it beats what the panel already carries for "
            f"{r.top_BMAp_anchor}), detected in {r.max_pct:.0f}% of cells.",
            "adds amygdala resolution above the specificity cutoff")

    df = pd.DataFrame(picks.values())
    df["slot"] = np.where(df.on_base_free, "free (on 10x base panel)", "custom probe")
    order = {"1_TRAP_tag": 0, "2_celltype_separator": 1, "3_genomewide_anchor_rescue": 2,
             "4_morphine_state": 3, "4b_class_backbone": 4, "4c_activity_IEG": 5,
             "4d_plasticity": 6, "4e_identity_TF": 7, "4f_regional_marker": 8,
             "5_receptor_map": 9, "6_subpopulation_discovery": 10, "7_BMAp_depth": 11}
    df = df.sort_values(["block", "gene"], key=lambda s: s.map(order) if s.name == "block" else s)
    df.insert(0, "order_rank", range(1, len(df) + 1))

    custom = df[~df.on_base_free]
    free = df[df.on_base_free]
    measured = len(base | set(df.gene)) + len([g for g in TRAP])  # base + customs + transgenes

    print(f"=== FINAL PANEL ===")
    print(f"  genes in the curated list : {len(df)}")
    print(f"    already free on base    : {len(free)}")
    print(f"    custom probes needed    : {len(custom)}")
    print(f"  TOTAL MEASURED per section: {len(base)} base + {len(custom)} custom = "
          f"{len(base) + len(custom)}")
    print(f"\nby block:")
    print(df.groupby("block").agg(genes=("gene", "size"),
                                  custom=("on_base_free", lambda s: int((~s).sum()))).to_string())

    # coverage check
    sup_all = sup_mk.group.nunique()
    covered = sup_mk[sup_mk.gene.isin(set(df.gene) | base)].group.nunique()
    prevC = sup_mk[sup_mk.gene.isin(set(pd.read_excel(PC, "SHARED_PANEL_ORDER").gene))].group.nunique()
    print(f"\nsub-population coverage (of {sup_all} markable supertypes):")
    print(f"  previous Option C : {prevC}")
    print(f"  THIS panel        : {covered}")
    lost = sep - set(df.gene)
    print(f"\nload-bearing separators retained: {len(sep)-len(lost)}/{len(sep)}"
          f"{'  LOST: ' + ', '.join(sorted(lost)) if lost else ''}")

    with pd.ExcelWriter(DST, engine="openpyxl") as w:
        pd.DataFrame({"item": [
            "What this is", "Architecture", "Total measured", "Custom probes",
            "Sub-population coverage", "How detectability was measured", "Open items"],
            "detail": [
                "The final ORBm/BMAp Xenium gene list, built from the full analysis: a genome-wide "
                "screen of all 32,285 Allen atlas genes, measured detectability for every candidate, "
                "and a controlled comparison of panel architectures.",
                f"Add-on route: the 248-gene 10x Mouse Brain base panel plus {len(custom)} custom "
                "probes. The base panel is kept because a disjoint-gene control showed its own genes "
                "mark 45.6 of 96 markable sub-populations at a matched budget, versus 25.0 for the "
                "genes unique to a standalone design. On this route the base panel is free.",
                f"{len(base)} base + {len(custom)} custom = {len(base)+len(custom)} genes per section.",
                f"{len(custom)}. NOTE: 10x caps a custom add-on at 100 genes, so this exceeds the cap "
                f"by {max(0, len(custom)-100)}. Trimming guidance is in the by_block sheet - drop from "
                "block 7 then block 6's lowest-coverage entries first.",
                f"{covered} of {sup_all} markable Allen supertypes, against {prevC} for the previous "
                "245-gene design.",
                "Percent of cells with a nonzero log2(CPM+1) value, computed from the locally cached "
                "Allen WMB-10X matrices over 226,886 cells in PL-ILA-ORB and sAMY. Each anchor is "
                "scored only within its own region.",
                "Confirm the tdTomato reporter strain number. Confirm the custom-probe count against "
                "the 10x cap and decide between trimming and a standalone panel.",
            ]}).to_excel(w, "READ_ME", index=False)
        df.to_excel(w, "FINAL_PANEL", index=False)
        custom.to_excel(w, "custom_probes_only", index=False)
        df.groupby("block").agg(genes=("gene", "size"),
                                custom=("on_base_free", lambda s: int((~s).sum()))).to_excel(w, "by_block")
    print(f"\nwrote {DST}")


if __name__ == "__main__":
    main()
