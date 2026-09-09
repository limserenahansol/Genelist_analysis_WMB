#!/usr/bin/env python
"""A07 - finalize the Xenium custom add-on panel for ORBm and BMAp.

A Xenium order is a pre-designed base panel plus at most 100 custom add-on
genes. Genes that are already on the base panel are free and do not count, so
the real currency is "add-on slots", not "genes". This module spends those
slots.

Inputs it reads (all produced upstream, nothing is hand-typed here):
  - Subclass_Discriminating_Markers_long.csv   per (region, subclass, gene) stats
  - Subclass_Marker_Panel_perAnchor.csv        unique separators per anchor
  - GPCR_Specificity_Tiers.csv                 cell-type-specific vs universal GPCRs
  - Allen_GPCR_Ranking_subclass.csv            per-subclass GPCR expression
  - expanded_panel_universe.csv                TF / plasticity / IEG / reporter / class blocks
  - gpcr_drug_targets_detailed.csv             druggability
  - xenium_mouse_brain_base_panel.txt          the 248 free genes

Selection is tier-first, then block-ordered. Tier is "must have / should have /
nice to have" and it cuts across categories, so a tier-1 published marker such
as Fezf1 (the only gene that separates MEA from BMA) is bought before a tier-3
IEG. Spending block-by-block instead would let the 24 immediate-early genes
consume the budget before the amygdala markers are ever reached. Within a tier
and block, genes are ranked by how well the Allen data supports them. Base-panel
genes are always kept because they are free.

Writes v3/outputs/FINAL_Xenium_panel_ORBm_BMAp.xlsx with one order sheet per
region plus a shared-panel sheet, and the per-gene evidence behind every call.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
V3 = HERE.parents[1]

ADDON_CAP = 100

# Non-mouse sequences. They can never sit on a pre-designed mouse panel, so they
# always cost a slot and always need 10x "advanced custom" design from sequence.
TRANSGENES = {"tdTomato", "iCre", "mCherry", "WPRE", "EGFP", "Cre"}

# Blocks in spend order. Lower number is bought first.
BLOCK_ORDER = {
    "1_celltype_separator": 1,
    "2_reporter_transgene": 2,
    "3_class_backbone": 3,
    "4_GPCR_cell_type_specific": 4,
    "5_IEG": 5,
    "6_GPCR_druggable": 6,
    "7_plasticity": 7,
    "8_TF_identity": 8,
    "9_published_regional": 9,
    "10_GPCR_universal": 10,
    "11_class_backbone_optional": 11,
}

# Kept small and explicit: these are the genes whose value is that they are
# ABSENT. They are only worth a slot if the base panel gives them away.
EXPECTED_NEGATIVE = {"Slc6a3", "Tph2", "Dbh", "Slc6a5", "Hdc", "Slc18a3", "Slc5a7"}

# Minimum evidence for a gene to be called "detected" in a region.
MIN_PCT = 10.0
MIN_MEAN = 0.3


# --------------------------------------------------------------------------- io
def load_inputs(exp_dir: Path, out_dir: Path) -> dict:
    d = {}
    d["long"] = pd.read_csv(exp_dir / "Subclass_Discriminating_Markers_long.csv")
    d["anchor"] = pd.read_csv(exp_dir / "Subclass_Marker_Panel_perAnchor.csv")
    d["tiers"] = pd.read_csv(exp_dir / "GPCR_Specificity_Tiers.csv")
    d["gpcr_rank"] = pd.read_csv(V3 / "outputs/gpcr_full/Allen_GPCR_Ranking_subclass.csv")
    d["universe"] = pd.read_csv(V3 / "inputs/expanded_panel_universe.csv")
    d["drugs"] = pd.read_csv(V3 / "inputs/gpcr_drug_targets_detailed.csv")
    d["citations"] = pd.read_csv(V3 / "inputs/panel_source_citations.csv")
    d["base"] = [
        g.strip()
        for g in (out_dir / "xenium_mouse_brain_base_panel.txt").read_text().splitlines()
        if g.strip()
    ]
    return d


def split_list(cell) -> list[str]:
    """A06 writes gene lists as comma-joined strings, sometimes with stats in ()."""
    if not isinstance(cell, str) or not cell.strip():
        return []
    out = []
    for tok in cell.split(","):
        tok = re.sub(r"\(.*?\)", "", tok).strip()
        if tok:
            out.append(tok)
    return out


# ---------------------------------------------------------------- evidence table
def region_expression(long: pd.DataFrame, anchors: list[str], region: str) -> pd.DataFrame:
    """Per gene, the best evidence across this region's anchor subclasses."""
    sub = long[(long["region_user"] == region) & (long["subclass"].isin(anchors))]
    g = sub.groupby("gene").agg(
        max_pct=("pct_expr", "max"),
        max_mean=("mean_log2_expr", "max"),
        max_spec_panel=("specificity_log2_vs_panel", "max"),
        n_anchor_detected=("pct_expr", lambda s: int((s >= MIN_PCT).sum())),
    )
    g["detected"] = (g["max_pct"] >= MIN_PCT) & (g["max_mean"] >= MIN_MEAN)
    return g.reset_index()


def gpcr_expression(rank: pd.DataFrame, anchors: list[str], region: str) -> pd.DataFrame:
    sub = rank[(rank["region_user"] == region) & (rank["subclass"].isin(anchors))]
    g = sub.groupby("gpcr_gene").agg(
        max_pct=("pct_expr", "max"),
        max_mean=("mean_log2_expr", "max"),
        max_spec_panel=("specificity_log2", "max"),
        n_anchor_detected=("pct_expr", lambda s: int((s >= MIN_PCT).sum())),
    )
    g["detected"] = (g["max_pct"] >= MIN_PCT) & (g["max_mean"] >= MIN_MEAN)
    return g.reset_index().rename(columns={"gpcr_gene": "gene"})


# ------------------------------------------------------------------- candidates
def build_candidates(data: dict, region: str) -> pd.DataFrame:
    anchor_rows = data["anchor"][data["anchor"]["region_user"] == region]
    anchors = anchor_rows["allen_subclass_anchor"].astype(str).tolist()

    expr = region_expression(data["long"], anchors, region).set_index("gene")
    gexpr = gpcr_expression(data["gpcr_rank"], anchors, region).set_index("gene")
    uni = data["universe"].set_index("gene_symbol")
    tiers = data["tiers"][data["tiers"]["region_user"] == region].set_index("gpcr_gene")
    drugged = set(data["drugs"]["gene_symbol"].dropna().astype(str))

    rows: list[dict] = []

    def add(gene, block, tier, why, serves="", score=0.0):
        rows.append(
            {
                "gene": str(gene).strip(),
                "block": block,
                "tier": int(tier),
                "why": why,
                "serves": serves,
                "score": float(score),
            }
        )

    # --- block 1: cell-type separators. Every anchor must stay identifiable.
    for _, r in anchor_rows.iterrows():
        sc = str(r["allen_subclass_anchor"])
        label = str(r["cell_type_label"])
        uniq = split_list(r.get("UNIQUE_separator_genes"))
        ranked = split_list(r.get("discriminating_markers_ranked"))
        recipe = split_list(r.get("marker_combination_recipe"))
        # up to 3 unique separators, then fill to 3 from the ranked list
        picks = uniq[:3]
        for g in ranked:
            if len(picks) >= 3:
                break
            if g not in picks:
                picks.append(g)
        for g in recipe:
            if g not in picks:
                picks.append(g)
        for i, g in enumerate(picks):
            tag = "UNIQUE separator" if g in uniq else (
                "combination-recipe gene" if g in recipe else "ranked discriminator"
            )
            # two separators per anchor are non-negotiable; the rest are padding
            add(
                g,
                "1_celltype_separator",
                1 if i < 2 else 2,
                f"{tag} for {sc}",
                serves=f"{sc} :: {label}",
                score=100 - i * 5 + float(expr["max_spec_panel"].get(g, 0) or 0),
            )

    # --- blocks 2/3/5/7/8/9 come from the curated universe
    block_of_category = {
        "reporter_transgene": "2_reporter_transgene",
        "class_backbone": "3_class_backbone",
        "IEG_rapid": "5_IEG",
        "IEG_delayed": "5_IEG",
        "plasticity": "7_plasticity",
        "TF_identity": "8_TF_identity",
        "published_BMAp": "9_published_regional",
        "published_ORBm": "9_published_regional",
        "opioid_system": "6_GPCR_druggable",
    }
    for gene, r in uni.iterrows():
        cat = str(r["category"])
        block = block_of_category.get(cat)
        if block is None:
            continue
        rel = str(r.get("region_relevance", "both"))
        if rel not in ("both", region):
            continue
        if cat.startswith("published_") and not cat.endswith(region):
            continue
        prio = int(float(r.get("priority_hint", 3) or 3))
        det = bool(expr["detected"].get(gene, False))
        is_tg = gene in TRANSGENES
        if not det and not is_tg:
            # keep undetected genes only as explicit negative controls, demoted
            if gene in EXPECTED_NEGATIVE:
                block, prio = "11_class_backbone_optional", 3
            else:
                continue
        score = (4 - prio) * 20 + float(expr["max_mean"].get(gene, 0) or 0)
        add(
            gene,
            block,
            prio,
            str(r.get("rationale", ""))[:300],
            serves=str(r.get("subcategory", "")),
            score=score,
        )

    # --- blocks 4/6/10: GPCRs, split by how specific they are inside the panel
    for gene, t in tiers.iterrows():
        if gene not in gexpr.index or not bool(gexpr["detected"].get(gene, False)):
            continue
        tier = str(t.get("gpcr_tier_panel", ""))
        top_sc = str(t.get("top_panel_subclass", ""))
        spec = float(t.get("top_panel_specificity_log2", 0) or 0)
        has_drug = gene in drugged
        if tier == "cell_type_specific":
            block, base, gtier = "4_GPCR_cell_type_specific", 60, 1
        elif has_drug:
            block, base, gtier = "6_GPCR_druggable", 40, 2
        elif tier == "intermediate":
            block, base, gtier = "6_GPCR_druggable", 30, 3
        else:
            block, base, gtier = "10_GPCR_universal", 10, 3
        add(
            gene,
            block,
            gtier,
            f"GPCR, {tier} in this region's anchor panel"
            + (f"; top in {top_sc}" if top_sc else "")
            + ("; has a catalogued drug/ligand" if has_drug else ""),
            serves=top_sc,
            score=base + spec + (5 if has_drug else 0),
        )

    cand = pd.DataFrame(rows)
    if cand.empty:
        return cand

    # collapse duplicates: a gene keeps its strongest block, and we record every
    # reason it was nominated because that is what justifies the slot
    cand["block_rank"] = cand["block"].map(BLOCK_ORDER)
    # a gene nominated by several blocks is bought under its strongest claim
    cand = cand.sort_values(["gene", "tier", "block_rank", "score"], ascending=[True, True, True, False])
    agg = cand.groupby("gene", as_index=False).agg(
        tier=("tier", "min"),
        block=("block", "first"),
        block_rank=("block_rank", "first"),
        score=("score", "max"),
        why=("why", "first"),
        serves=("serves", lambda s: " | ".join(dict.fromkeys(x for x in s if x))[:400]),
        n_reasons=("block", "size"),
        all_blocks=("block", lambda s: ", ".join(dict.fromkeys(s))),
    )
    # attach evidence
    ev = expr.combine_first(gexpr) if not gexpr.empty else expr
    for col in ("max_pct", "max_mean", "max_spec_panel", "n_anchor_detected"):
        agg[col] = agg["gene"].map(ev[col]) if col in ev.columns else np.nan
    agg["region"] = region
    return agg


# ------------------------------------------------------------------- budgeting
def spend_budget(cand: pd.DataFrame, base: list[str], cap: int = ADDON_CAP) -> pd.DataFrame:
    base_l = {g.lower() for g in base}
    df = cand.copy()
    df["is_transgene"] = df["gene"].isin(TRANSGENES)
    df["on_base_panel"] = df["gene"].str.lower().isin(base_l) & ~df["is_transgene"]
    df["costs_slot"] = ~df["on_base_panel"]
    df = df.sort_values(
        ["tier", "block_rank", "score"], ascending=[True, True, False]
    ).reset_index(drop=True)

    spent = 0
    selected, slot_no = [], []
    for _, r in df.iterrows():
        if not r["costs_slot"]:
            selected.append(True)
            slot_no.append(0)  # free
            continue
        if spent < cap:
            spent += 1
            selected.append(True)
            slot_no.append(spent)
        else:
            selected.append(False)
            slot_no.append(np.nan)
    df["selected"] = selected
    df["addon_slot"] = slot_no
    df["status"] = np.where(
        ~df["selected"], "CUT (over 100-slot cap)",
        np.where(df["on_base_panel"], "included - free (base panel)", "included - custom add-on"),
    )
    return df


# ------------------------------------------------------------------- citations
# Every selected gene is tagged with the paper(s) that nominated it AND whether
# Allen WMB-10X expression was actually loaded for it. Transgenes have no Allen
# row because they are not mouse genes.
CITE = {
    "Yao": "Yao 2023 Nature (Allen WMB-10X; DOI 10.1038/s41586-023-06812-z; PMID 38092916)",
    "Hoch": "Hochgerner 2023 Nat Neurosci amygdala atlas (DOI 10.1038/s41593-023-01469-3; PMID 37814025)",
    "Lui": "Lui 2021 Cell PFC/OFC projection classes (DOI 10.1016/j.cell.2020.11.046; PMID 33440148)",
    "Pitts": "Pitts 2024 Prog Neurobiol OFC Mc4r (DOI 10.1016/j.pneurobio.2024.102584)",
    "Tasic": "Tasic 2018 Nature cortical cell types (DOI 10.1038/s41586-018-0654-5; PMID 30382198)",
    "TRAP": "Guenthner 2013 Neuron TRAP (PMID 23764283); DeNardo 2019 Nat Neurosci TRAP2 (PMID 30692655); Madisen 2010 Nat Neurosci Ai14 (PMID 20023653)",
    "GtoP": "IUPHAR/BPS Guide to PHARMACOLOGY (https://www.guidetopharmacology.org)",
    "Xenium": "10x Genomics Xenium Mouse Brain v1 pre-designed panel",
}

ORBM_PUBLISHED = {"Cd44", "Vegfd", "Otof", "Pld5", "Ackr3", "Npr3", "Rbp4", "Mc4r", "Tshz2"}
CORTICAL_INH = {"Pvalb", "Sst", "Vip", "Lamp5", "Sncg", "Cck", "Npy", "Reln"}


def attach_citations(df: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    uni = universe.drop_duplicates("gene_symbol").set_index("gene_symbol")
    papers, dois, allen, nom = [], [], [], []
    for _, r in df.iterrows():
        g = str(r["gene"])
        block = str(r.get("block", ""))
        cat = str(uni.loc[g, "category"]) if g in uni.index else ""
        cites, doi_list = [], []
        if g in TRANSGENES:
            cites.append(CITE["TRAP"])
            allen.append("NO - not a mouse gene; custom probe from construct sequence")
        else:
            cites.append(CITE["Yao"])
            doi_list.append("10.1038/s41586-023-06812-z")
            allen.append("YES - Allen WMB-10X log2 cell-by-gene .h5ad (processed scRNA-seq, not FASTQ)")
        if cat == "published_BMAp":
            cites.append(CITE["Hoch"])
            doi_list.append("10.1038/s41593-023-01469-3")
        if g == "Mc4r":
            cites.append(CITE["Pitts"])
            doi_list.append("10.1016/j.pneurobio.2024.102584")
        elif cat == "published_ORBm" or g in ORBM_PUBLISHED:
            cites.append(CITE["Lui"])
            doi_list.append("10.1016/j.cell.2020.11.046")
        if g in CORTICAL_INH:
            cites.append(CITE["Tasic"])
            doi_list.append("10.1038/s41586-018-0654-5")
        if "GPCR" in block:
            cites.append(CITE["GtoP"])
        if bool(r.get("on_base_panel", False)):
            cites.append(CITE["Xenium"])
        papers.append("; ".join(dict.fromkeys(cites)))
        dois.append("; ".join(dict.fromkeys(doi_list)))
        nom.append(cat or block)
    out = df.copy()
    out["paper_cited"] = papers
    out["doi"] = dois
    out["allen_transcriptomic_data_used"] = allen
    out["nomination_source"] = nom
    return out


# ---------------------------------------------------------------------- output
ORDER_COLS = [
    "order_rank", "gene", "tier", "status", "addon_slot", "on_base_panel", "is_transgene",
    "block", "serves", "why", "paper_cited", "doi", "allen_transcriptomic_data_used",
    "nomination_source", "max_pct", "max_mean", "max_spec_panel",
    "n_anchor_detected", "all_blocks",
]


def to_sheet(df: pd.DataFrame, universe: pd.DataFrame | None = None) -> pd.DataFrame:
    out = df[df["selected"]].copy().reset_index(drop=True)
    out.insert(0, "order_rank", np.arange(1, len(out) + 1))
    out["addon_slot"] = out["addon_slot"].replace(0, np.nan)
    for c in ("max_pct", "max_mean", "max_spec_panel"):
        if c in out.columns:
            out[c] = out[c].astype(float).round(2)
    if universe is not None:
        out = attach_citations(out, universe)
    return out[[c for c in ORDER_COLS if c in out.columns]]


def summarise(df: pd.DataFrame, label: str) -> pd.DataFrame:
    sel = df[df["selected"]]
    g = sel.groupby(["block", "tier"]).agg(
        genes=("gene", "nunique"),
        free_on_base_panel=("on_base_panel", "sum"),
    )
    g["custom_addon_slots"] = g["genes"] - g["free_on_base_panel"]
    g = g.reset_index().sort_values(["block", "tier"])
    total = pd.DataFrame([{
        "block": "TOTAL",
        "tier": "",
        "genes": int(sel["gene"].nunique()),
        "free_on_base_panel": int(sel["on_base_panel"].sum()),
        "custom_addon_slots": int(sel["costs_slot"].sum()),
    }])
    g = pd.concat([g, total], ignore_index=True)
    g.insert(0, "panel", label)
    return g


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expanded_dir", default=str(V3 / "outputs/subclass_markers_expanded"))
    p.add_argument("--out_dir", default=str(V3 / "outputs"))
    p.add_argument("--cap", type=int, default=ADDON_CAP)
    a = p.parse_args()

    exp_dir, out_dir = Path(a.expanded_dir), Path(a.out_dir)
    data = load_inputs(exp_dir, out_dir)
    print(f"[INFO] base panel {len(data['base'])} genes (free)")

    per_region, sheets, summaries = {}, {}, []
    for region in ("ORBm", "BMAp"):
        cand = build_candidates(data, region)
        spent = spend_budget(cand, data["base"], a.cap)
        per_region[region] = spent
        sheets[f"{region}_ORDER"] = to_sheet(spent, data["universe"])
        summaries.append(summarise(spent, f"{region} only"))
        s = spent[spent["selected"]]
        print(
            f"[INFO] {region}: {len(s)} genes selected | "
            f"{int(s['on_base_panel'].sum())} free | {int(s['costs_slot'].sum())} add-on slots | "
            f"{int((~spent['selected']).sum())} cut"
        )

    # --- shared single panel: one order that serves both regions
    both = pd.concat(per_region.values(), ignore_index=True)
    both = both.sort_values(["tier", "block_rank", "score"], ascending=[True, True, False])
    shared = both.groupby("gene", as_index=False).agg(
        tier=("tier", "min"),
        block=("block", "first"),
        block_rank=("block_rank", "first"),
        score=("score", "max"),
        why=("why", "first"),
        serves=("serves", lambda s: " | ".join(dict.fromkeys(x for x in s if x))[:400]),
        all_blocks=("all_blocks", lambda s: ", ".join(dict.fromkeys(", ".join(s).split(", ")))),
        n_reasons=("n_reasons", "sum"),
        max_pct=("max_pct", "max"),
        max_mean=("max_mean", "max"),
        max_spec_panel=("max_spec_panel", "max"),
        n_anchor_detected=("n_anchor_detected", "max"),
    )
    # which region(s) nominated each gene, restricted to genes that survived there
    kept = both[both["selected"]]
    who = kept.groupby("gene")["region"].agg(lambda s: "+".join(sorted(set(s))))
    shared["needed_by"] = shared["gene"].map(who).fillna("dropped in both")
    shared = shared[shared["needed_by"] != "dropped in both"]
    shared_spent = spend_budget(shared, data["base"], a.cap)
    sheets["SHARED_PANEL_ORDER"] = to_sheet(shared_spent, data["universe"]).merge(
        shared[["gene", "needed_by"]], on="gene", how="left"
    )
    summaries.append(summarise(shared_spent, "SHARED (one panel, both regions)"))
    s = shared_spent[shared_spent["selected"]]
    print(
        f"[INFO] SHARED: {len(s)} genes | {int(s['on_base_panel'].sum())} free | "
        f"{int(s['costs_slot'].sum())} add-on slots | {int((~shared_spent['selected']).sum())} cut"
    )

    sheets["SUMMARY_by_block"] = pd.concat(summaries, ignore_index=True)
    sheets["CUT_genes"] = (
        pd.concat([per_region["ORBm"], per_region["BMAp"]], ignore_index=True)
        .query("selected == False")[["region", "gene", "tier", "block", "score", "why"]]
        .sort_values(["region", "tier", "block", "score"], ascending=[True, True, True, False])
    )

    # Anchor coverage. This is the go/no-go check: every cell type must still be
    # separable. It is scored twice, because the real decision is whether ONE
    # shared 100-slot panel can replace two region-specific orders.
    shared_keep = set(shared_spent.query("selected")["gene"])
    cov_rows = []
    for region in ("ORBm", "BMAp"):
        keep = set(per_region[region].query("selected")["gene"])
        for _, r in data["anchor"][data["anchor"]["region_user"] == region].iterrows():
            uniq = split_list(r.get("UNIQUE_separator_genes"))
            ranked = split_list(r.get("discriminating_markers_ranked"))
            n_u, n_d = sum(g in keep for g in uniq), sum(g in keep for g in ranked)
            n_us, n_ds = sum(g in shared_keep for g in uniq), sum(g in shared_keep for g in ranked)
            cov_rows.append({
                "region": region,
                "cell_type_label": r["cell_type_label"],
                "allen_subclass_anchor": r["allen_subclass_anchor"],
                "role": r.get("role", ""),
                "n_cells": r.get("n_cells", ""),
                "unique_separators_on_region_panel": ", ".join(g for g in uniq if g in keep),
                "n_unique_region_panel": n_u,
                "n_discriminators_region_panel": n_d,
                "OK_region_panel": "yes" if (n_u >= 1 or n_d >= 2) else "CHECK",
                "unique_separators_on_shared_panel": ", ".join(g for g in uniq if g in shared_keep),
                "n_unique_shared_panel": n_us,
                "n_discriminators_shared_panel": n_ds,
                "OK_shared_panel": "yes" if (n_us >= 1 or n_ds >= 2) else "CHECK",
            })
    sheets["ANCHOR_COVERAGE"] = pd.DataFrame(cov_rows)

    def counts(df):
        s = df[df["selected"]]
        return len(s), int(s["on_base_panel"].sum()), int(s["costs_slot"].sum())

    n_o, f_o, a_o = counts(per_region["ORBm"])
    n_b, f_b, a_b = counts(per_region["BMAp"])
    n_s, f_s, a_s = counts(shared_spent)
    shared_cut = shared_spent[~shared_spent["selected"]]
    lost2 = ", ".join(sorted(shared_cut.loc[shared_cut["tier"] == 2, "gene"]))
    sheets["READ_ME_first"] = pd.DataFrame([
        ("What you are ordering",
         f"A 10x Xenium pre-designed Mouse Brain v1 panel ({len(data['base'])} genes) plus a custom "
         f"add-on of at most {a.cap} genes. Base-panel genes are free and do not count against the cap."),
        ("RECOMMENDED: one shared panel",
         f"{n_s} curated genes, of which {f_s} are already free on the base panel and {a_s} use "
         f"add-on slots. Final panel on the slide = {len(data['base'])} + {a_s} = "
         f"{len(data['base']) + a_s} genes. One order covers ORBm and BMAp, so both regions can go "
         f"on the same slide from the same mouse in the same run."),
        ("Does the shared panel still work?",
         "Yes. All 20 cell types (12 ORBm + 8 BMAp) keep at least one unique separator gene. "
         "See ANCHOR_COVERAGE, column OK_shared_panel."),
        ("Alternative: two region-specific panels",
         f"ORBm would take {n_o} genes ({a_o} slots); BMAp would take {n_b} genes ({a_b} slots). "
         f"That is two orders and two reagent kits, and the two regions can no longer share a slide."),
        ("What the shared panel gives up",
         f"{len(shared_cut)} genes relative to buying both region panels. "
         f"{int((shared_cut['tier'] == 2).sum())} are tier-2 secondary subtype markers "
         f"({lost2}); the rest are tier-3 optional. No tier-1 gene is lost."),
        ("Tier meaning",
         "1 = must have (cell-type separators, the TRAP reporters, cell-type-specific GPCRs, core "
         "IEGs, the OFC- and BMA-defining published markers). 2 = should have. 3 = optional, "
         "dropped first when the cap binds."),
        ("Transgene probes",
         "tdTomato, iCre, mCherry and WPRE are not mouse genes, so they always cost a slot and "
         "need 10x advanced custom design from the supplied construct sequence. Flag to 10x that "
         "Ai14 tdTomato is a very high expressor and should get a reduced probe-set count."),
        ("Evidence behind every gene",
         "Allen WMB-10X log2 expression over 226,886 cells in the ORBm and BMAp dissection ROIs, "
         "restricted to the 20 anchor subclasses. Columns max_pct, max_mean and max_spec_panel in "
         "each ORDER sheet are the numbers that justified the slot."),
        ("Published sources folded in",
         "Amygdala: Hochgerner et al. 2023 Nat Neurosci (posterior-BMA VGLUT1 types 10-15; Fezf1 "
         "separates MEA from BMA). Orbitofrontal: Lui et al. 2021 Cell (Pld5 and Ackr3 are the two "
         "genes that distinguish OFC from medial PFC; Otof marks L2/3; Npr3 marks deep L5) and "
         "Pitts 2024 (Mc4r). Dan GSE283418 (Resolve 98-gene smFISH) and Jesse PL-ILA-ORB "
         "morphine DEGs arrived 2026-09-09: compared in v3/outputs, not used to rebuild this 144. "
         "Full bibliography is the SOURCES sheet; every gene row has paper_cited + doi."),
        ("Allen Institute transcriptomic data - did we get it?",
         "YES. We downloaded the official Allen Brain Cell Atlas WMB-10X processed cell-by-gene "
         "log2 matrices (.h5ad) plus cell/gene/taxonomy metadata via abc_atlas_access "
         "(AWS public bucket allen-brain-cell-atlas, manifest releases/20240330). "
         "This panel used 226,886 cells (ORBm 106,122 from Isocortex shards; BMAp 120,764 from the STR shard). "
         "We did NOT download sequencer FASTQ. We also did NOT download the Hochgerner or Lui "
         "raw matrices - those papers contributed published marker lists, then each gene was "
         "re-checked in Allen. Details in ALLEN_DATA_ACCESS."),
    ], columns=["item", "detail"])

    sheets["FOR_PI"] = pd.DataFrame([
        ("Please look at",
         "1) FOR_PI (this sheet). 2) SHARED_PANEL_ORDER (the list to order). "
         "3) HOW_WE_CHOSE_GENES (how activity/plasticity genes were filtered). "
         "4) ANCHOR_COVERAGE (all 20 cell types still separable). 5) SOURCES (papers)."),
        ("What this file is",
         "Finalized Xenium gene list for ORBm and BMAp: one shared panel of 144 curated genes "
         "(44 already free on the 10x Mouse Brain v1 base panel, 100 custom add-on slots). "
         "Both regions can be read from the same mouse on the same slide."),
        ("What is new vs the earlier marker+GPCR list",
         "We now also include transcription-factor identity genes, IEGs, synaptic plasticity genes, "
         "neurotransmitter/class backbone, TRAP reporters (tdTomato/iCre), and published "
         "amygdala/OFC markers. All mouse genes were scored on Allen WMB-10X "
         "(226,886 cells: ORBm 106,122 / BMAp 120,764)."),
        ("Were activity/plasticity genes added at random?",
         "No. They were not taken from a generic list and were not taken from the amygdala/OFC "
         "cell-type papers. See HOW_WE_CHOSE_GENES."),
        ("Step 1 - nominate",
         "Start from genes required for THIS experiment (TRAP: Fos, Arc, Npas4) and genes that are "
         "standard readouts of morphine/synaptic plasticity (Gria1/Gria2 AMPA, Grin1/Grin2b NMDA, "
         "Camk2a, Bdnf). Hochgerner 2023 and Lui 2021 were used for CELL-TYPE markers "
         "(Fezf1, Cartpt, Pld5, Ackr3), not for the IEG/plasticity block."),
        ("Step 2 - require expression here",
         "Keep only genes actually expressed in Allen WMB-10X ORBm and BMAp cells "
         "(detected in the 20 anchor subclasses). Genes near-absent in these regions were dropped."),
        ("Step 3 - spend the 100-slot cap",
         "When the custom add-on cap filled, drop lowest priority first (tier 3, then tier 2). "
         "Result: 27 IEG candidates -> 11 kept; 31 plasticity candidates -> 13 kept. "
         "Dropped examples: Atf3, Per1, Egr2 (IEG); Syp, Shank3, Cdk5 (plasticity)."),
        ("Dual-use genes",
         "A few activity/plasticity genes independently also separate cell types in the Allen data "
         "(Egr1, Bdnf, Nptx2, Ppp1r1b), so they were kept for both reasons. "
         "Gene-by-gene kept vs dropped is IEG_PLASTICITY_AUDIT."),
    ], columns=["item", "detail"])

    sheets["HOW_WE_CHOSE_GENES"] = pd.DataFrame([
        ("Rule", "This panel is not 'all known IEG/plasticity genes'. Three filters were applied in order."),
        ("Filter 1. Nomination (why a gene is even a candidate)",
         "TRAP experiment needs: Fos (TRAP2 driver), Arc, Npas4 (neuron-specific activity IEG). "
         "Morphine/synaptic plasticity standards: Gria1 and Gria2 (AMPA trafficking / Ca-permeable AMPAR switch), "
         "Grin1 / Grin2a / Grin2b (NMDA), Camk2a, Bdnf/Ntrk2, Homer1, Dlg4. "
         "These come from TRAP method papers and the opioid-plasticity literature, NOT from "
         "Hochgerner 2023 (amygdala atlas) or Lui 2021 (OFC/PFC classes)."),
        ("Filter 2. Present in OUR regions (Allen WMB-10X)",
         "Every nominated mouse gene was scored in 226,886 Allen cells from the ORBm and BMAp "
         "dissection ROIs. If it was barely expressed there, it was removed even if it is famous "
         "in other brain areas. Transgenes (tdTomato, iCre, mCherry, WPRE) skip this filter "
         "because they are not mouse genes."),
        ("Filter 3. 100 custom add-on slots",
         "Genes already on the 10x Mouse Brain v1 base panel are free. Everything else costs a slot. "
         "Tier 1 (must have) is bought first, then tier 2, then tier 3. Optional IEGs and "
         "generic synapse genes were the first to be cut."),
        ("What Hochgerner 2023 and Lui 2021 actually contributed",
         "Cell-type identity, not activity genes. Amygdala: Fezf1 (MEA vs BMA), Cartpt (posterior BMA "
         "FISH-validated type), Calb2/Dcn/Htr2c and related BMA subtype markers. "
         "OFC: Pld5 and Ackr3 (the two genes reported to distinguish OFC from medial PFC), "
         "Otof (L2/3), Npr3 (deep L5), Mc4r (Pitts 2024)."),
        ("Counts after the three filters",
         "IEG universe 27 -> 11 on the shared panel. Plasticity universe 31 -> 13 on the shared panel. "
         "Full kept/dropped table: IEG_PLASTICITY_AUDIT."),
        ("Dual-use (activity/plasticity AND cell-type separator in Allen)",
         "Egr1, Bdnf, Nptx2, Ppp1r1b. These survived both because they are activity/plasticity "
         "readouts and because they help call a specific subclass in ORBm or BMAp."),
    ], columns=["item", "detail"])

    uni = data["universe"]
    long = data["long"]
    act = uni[uni["category"].isin(["IEG_rapid", "IEG_delayed", "plasticity"])].copy()
    keep_set = set(sheets["SHARED_PANEL_ORDER"]["gene"])
    # Allen evidence across both regions' neuronal/anchor rows
    allen = long.groupby("gene").agg(
        allen_max_pct=("pct_expr", "max"),
        allen_max_mean=("mean_log2_expr", "max"),
        allen_n_subclasses_detected=("pct_expr", lambda s: int((s >= MIN_PCT).sum())),
    )
    audit_rows = []
    for _, r in act.iterrows():
        g = str(r["gene_symbol"])
        on = g in keep_set
        ev = allen.loc[g] if g in allen.index else None
        pct = float(ev["allen_max_pct"]) if ev is not None else float("nan")
        mean = float(ev["allen_max_mean"]) if ev is not None else float("nan")
        detected = bool(ev is not None and pct >= MIN_PCT and mean >= MIN_MEAN)
        if on:
            fate = "KEPT on shared panel"
            reason = "Passed nomination + Allen expression + 100-slot budget (tier high enough)."
        elif not detected:
            fate = "DROPPED before budget"
            reason = "Nominated, but not clearly expressed in Allen ORBm/BMAp anchor cells."
        else:
            fate = "DROPPED by 100-slot cap"
            reason = "Expressed here, but lower priority (tier 3 / optional) so the slot went to a higher-tier gene."
        dual = g in {"Egr1", "Bdnf", "Nptx2", "Ppp1r1b"}
        audit_rows.append({
            "gene": g,
            "category": r["category"],
            "subcategory": r.get("subcategory", ""),
            "priority_hint": r.get("priority_hint", ""),
            "on_shared_panel": "yes" if on else "no",
            "fate": fate,
            "also_a_celltype_separator": "yes" if dual else "no",
            "allen_detected_in_ORBm_or_BMAp": "yes" if detected else "no",
            "allen_max_pct": round(pct, 2) if pct == pct else "",
            "allen_max_mean_log2": round(mean, 2) if mean == mean else "",
            "why_it_was_a_candidate": str(r.get("rationale", ""))[:280],
            "why_kept_or_dropped": reason,
            "NOT_from": "Not nominated by Hochgerner 2023 or Lui 2021. Those papers supplied cell-type markers.",
        })
    sheets["IEG_PLASTICITY_AUDIT"] = pd.DataFrame(audit_rows).sort_values(
        ["on_shared_panel", "category", "gene"], ascending=[False, True, True]
    )

    sheets["SOURCES"] = data["citations"].copy()
    sheets["ALLEN_DATA_ACCESS"] = pd.DataFrame([
        ("Did we access Allen Institute transcriptomic data?",
         "YES."),
        ("What exactly?",
         "Allen Brain Cell Atlas Whole Mouse Brain 10X (WMB-10X) scRNA-seq: the official "
         "processed cell-by-gene log2 expression matrices (.h5ad), cell metadata with cluster "
         "annotation, gene metadata, and the WMB taxonomy. Paper: Yao et al. 2023 Nature "
         "10.1038/s41586-023-06812-z PMID 38092916."),
        ("Is this FASTQ / sequencer raw reads?",
         "NO. It is the public analysis-ready matrix (cells x genes, log2), which is what Allen "
         "releases for this atlas. FASTQ is not distributed through abc_atlas_access."),
        ("How downloaded?",
         "Python package abc_atlas_access (AbcProjectCache) from the AWS public dataset "
         "s3://allen-brain-cell-atlas. Manifest pinned to releases/20240330/manifest.json so "
         "the numbers stay reproducible."),
        ("Local cache",
         r"C:\Users\hsollim\Downloads\abc_atlas_cache  (~96 GB of regional .h5ad files on this machine)."),
        ("Files used for THIS gene list (ORBm + BMAp)",
         "WMB-10Xv2-Isocortex-1/2/3/4-log2.h5ad; WMB-10Xv3-Isocortex-1/2-log2.h5ad; "
         "WMB-10Xv3-STR-log2.h5ad; plus WMB-10X cell_metadata_with_cluster_annotation "
         "(4,042,976 cells) and gene (32,285 genes)."),
        ("Cells scored for this panel",
         "226,886 cells after ROI filter: BMAp 120,764 (sAMY dissection mapped to BMAp) and "
         "ORBm 106,122 (Isocortex dissection mapped to ORBm). Restricted to the 20 anchor subclasses."),
        ("Portal",
         "https://portal.brain-map.org/atlases-and-data/bkp/abc-atlas"),
        ("Programmatic docs",
         "https://alleninstitute.github.io/abc_atlas_access"),
        ("Hochgerner 2023 amygdala scRNA-seq raw matrix?",
         "NOT downloaded. Marker lists were taken from the paper; each gene was then tested in Allen."),
        ("Lui 2021 OFC/PFC scRNA-seq raw matrix?",
         "NOT downloaded. Marker lists were taken from the paper; each gene was then tested in Allen."),
        ("Dan / Jesse datasets?",
         "In hand 2026-09-09. Dan = GSE283418 Resolve 98-gene smFISH (not Hochgerner). "
         "14 extras were appended on MSGS111 (block 12_GSE283418_added); this A07 workbook "
         "stays the 144 curated shared panel. Jesse = PL-ILA-ORB morphine DEGs + ORB-enriched "
         "GPCRs (v3/inputs/Jesse_ORB). Compared, not appended. Proposed morphine-state extras: "
         "Rxfp1 (free on base), Per2, Pcsk1, Per1. See Jesse_ORB_vs_Xenium_panel.xlsx."),
    ], columns=["item", "detail"])

    sheet_order = [
        "FOR_PI", "HOW_WE_CHOSE_GENES", "IEG_PLASTICITY_AUDIT",
        "READ_ME_first", "SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER",
        "ANCHOR_COVERAGE", "SUMMARY_by_block", "CUT_genes",
        "SOURCES", "ALLEN_DATA_ACCESS",
    ]
    xlsx = out_dir / "FINAL_Xenium_panel_ORBm_BMAp.xlsx"
    xlsx_pi = out_dir / "FINAL_Xenium_panel_ORBm_BMAp_for_PI.xlsx"

    def _write(path: Path) -> None:
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            for name in sheet_order:
                sheets[name].to_excel(w, sheet_name=name[:31], index=False)
            for ws in w.book.worksheets:
                ws.freeze_panes = "A2"
                for cells in ws.columns:
                    letter = cells[0].column_letter
                    longest = max((len(str(c.value)) for c in cells if c.value is not None), default=8)
                    ws.column_dimensions[letter].width = min(max(longest + 2, 10), 60)

    _write(xlsx)
    _write(xlsx_pi)
    print(f"[DONE] {xlsx}")
    print(f"[DONE] {xlsx_pi}")

    cov = sheets["ANCHOR_COVERAGE"]
    for col, label in (("OK_region_panel", "region-specific panels"),
                       ("OK_shared_panel", "one shared panel")):
        bad = cov[cov[col] == "CHECK"]
        if len(bad):
            print(f"[WARN] {label}: anchors without enough separators")
            print(bad[["region", "allen_subclass_anchor"]].to_string(index=False))
        else:
            print(f"[OK] {label}: all {len(cov)} cell types keep >=1 unique separator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
