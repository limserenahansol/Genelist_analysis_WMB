#!/usr/bin/env python
"""
D02_create_final_probe_workbook.py

Module D: Final integration module.

Reads:
- Allen GPCR ranking CSV(s) from A03 (one or more taxonomy levels).
- Optional: published marker long table from B01.
- Optional: paper GPCR ranking from C03.
- Optional: standardized region mapping CSV.
- Optional: existing curated workbook (current v6 / candidate list).

Writes a single Excel with:
- README              : provenance, thresholds, run timestamp.
- Region_Mapping_Final
- Computed_GPCR_Subclass / _Supertype / _Cluster (one per level present)
- Published_Marker_Backbone (optional)
- Paper_Data_Validation (optional)
- Final_Probe_Panel   : ONE row per (region_user, level group, gene) with the
  full set of evidence columns + final_recommendation derived from
  thresholds in project_config.yaml.
- Removed_or_Downgraded : subset of Final_Probe_Panel where the rule fired.
- Final_Summary        : ONE row per (region_user, cell_type_label) with the
  Allen subclass anchor, top GPCRs to choose, and curated cell-type marker
  genes. This is the human-readable "what to put on the probe order"
  sheet. Driven by an optional --celltype_anchor_csv mapping.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import Thresholds, load_config, write_run_log  # noqa: E402


def _read_optional(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        print(f"[WARN] missing {p}")
        return pd.DataFrame()
    if p.suffix.lower() in (".parquet", ".pq"):
        return pd.read_parquet(p)
    return pd.read_csv(p)


def classify(df: pd.DataFrame, t: Thresholds) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["validation_status"] = "candidate_to_review"
    needed = {"n_cells", "mean_log2_expr", "pct_expr"}
    if needed.issubset(out.columns):
        strong = (
            (out.n_cells >= t.min_cells)
            & (out.mean_log2_expr >= t.strong_mean_log2_expr)
            & (out.pct_expr >= t.strong_pct_expr)
        )
        candidate = (
            (out.n_cells >= t.min_cells)
            & (out.mean_log2_expr >= t.min_mean_log2_expr_candidate)
            & (out.pct_expr >= t.min_pct_expr_candidate)
        )
        out.loc[candidate, "validation_status"] = "supported_by_expression"
        out.loc[strong, "validation_status"] = "final_keep"
        out.loc[out.n_cells < t.min_cells, "validation_status"] = "too_few_cells"
        weak = (out.mean_log2_expr < t.min_mean_log2_expr_candidate / 2.0) & (
            out.pct_expr < t.min_pct_expr_candidate / 2.0
        )
        out.loc[weak, "validation_status"] = "downgrade_low_expression"
    if "specificity_log2" in out.columns:
        # ubiquitous: low specificity even if abundant
        out.loc[out["specificity_log2"] < 0.0, "validation_status"] = out.loc[
            out["specificity_log2"] < 0.0, "validation_status"
        ].where(
            out.loc[out["specificity_log2"] < 0.0, "validation_status"].isin(
                ["too_few_cells", "downgrade_low_expression"]
            ),
            "downgrade_low_specificity",
        )
    return out


def _markers_for(markers: pd.DataFrame, region: str, cell_type: str, role: str) -> list[str]:
    if markers.empty or not {"region_user", "cell_type_label", "gene", "gene_role"}.issubset(markers.columns):
        return []
    sel = markers[
        (markers["region_user"].astype(str) == region)
        & (markers["cell_type_label"].astype(str) == cell_type)
        & (markers["gene_role"].astype(str) == role)
    ]
    return sorted(dict.fromkeys(sel["gene"].astype(str).tolist()))


def _build_paper_lookup(paper_sugg: pd.DataFrame) -> dict[tuple[str, str, str], list[str]]:
    """Build dict {(region_user, cell_type_label, gene): sorted unique source list}."""
    lookup: dict[tuple[str, str, str], set[str]] = {}
    if paper_sugg.empty:
        return {}
    needed = {"region_user", "cell_type_label", "gene", "paper_source"}
    if not needed.issubset(paper_sugg.columns):
        return {}
    for _, r in paper_sugg.iterrows():
        key = (str(r["region_user"]).strip(), str(r["cell_type_label"]).strip(), str(r["gene"]).strip())
        sources = {s.strip() for s in str(r["paper_source"]).replace(",", ";").split(";") if s.strip()}
        lookup.setdefault(key, set()).update(sources)
    return {k: sorted(v) for k, v in lookup.items()}


def _paper_genes_for(paper_lookup: dict, region: str, cell_type: str) -> dict[str, list[str]]:
    """Return {gene: [sources]} dict for a (region, cell_type)."""
    return {
        g: srcs
        for (r, ct, g), srcs in paper_lookup.items()
        if r == region and ct == cell_type
    }


def _format_top_gpcrs(rows: pd.DataFrame, top_n: int, with_status: bool = True) -> str:
    """Render top GPCR rows as 'Gene(spec=2.1, log2=8.3, pct=87%, status=keep)' joined by '; '."""
    if rows.empty:
        return ""
    out = []
    for _, r in rows.head(top_n).iterrows():
        spec = float(r.get("specificity_log2", 0.0) or 0.0)
        log2 = float(r.get("mean_log2_expr", 0.0) or 0.0)
        pct = float(r.get("pct_expr", 0.0) or 0.0)
        if with_status:
            rec = str(r.get("final_recommendation", "") or "")
            out.append(
                f"{r['gpcr_gene']}(spec={spec:.2f}, log2={log2:.2f}, pct={pct:.0f}%, status={rec})"
            )
        else:
            out.append(f"{r['gpcr_gene']}(log2={log2:.2f}, pct={pct:.0f}%, spec={spec:.2f})")
    return "; ".join(out)


REGION_DISSECTION_WARNINGS: dict[str, str] = {
    # Each entry explains the gap between the user-defined anatomical region
    # and the Allen WMB-10X dissection ROI used to select cells. These warnings
    # are propagated into Final_Summary and FINAL_Recommendations so the user
    # knows when the underlying cell pool is BROADER than their stated target.
    "CP": "OK: Allen ROI = STRd (dorsal striatum); aligns with user CP.",
    "BMAp": (
        "PARTIAL: Allen ROI = sAMY (striatum-like amygdalar); subclass with "
        "'BMA' in name is closest available match. Cells may include MEA/COA "
        "boundary."
    ),
    "RE": (
        "PARTIAL: Allen ROI = TH (entire thalamus); subclass `152 RE-Xi Nox4 "
        "Glut` is the most RE-specific transcriptomic class but it covers "
        "both nucleus reuniens AND xiphoid nucleus."
    ),
    "LM": (
        "BROAD: Allen ROI = HY (entire hypothalamus). Subclass `144 MM Foxb1 "
        "Glut` and `143 MM-ant Foxb1 Glut` cover the WHOLE mammillary body "
        "(lateral + medial + supramammillary) - NOT lateral-specific. To "
        "restrict to LM, dissect lateral mammillary nucleus directly OR "
        "co-stain with LM-discriminating markers (Lhx5, Cck, Calb2 vs "
        "medial-mammillary markers)."
    ),
    "ORBm": "OK: Allen ROI = PL-ILA-ORB (orbital + prelimbic + infralimbic).",
    "AId": "OK: Allen ROI = AI (agranular insular).",
    "CA": (
        "GOOD: Allen ROI = HIP (hippocampus); subclass anchors split "
        "CA1 (016 CA1-ProS), CA2 (025 CA2-FC-IG), CA3 (017 CA3), and "
        "DG (037 DG) cleanly."
    ),
}


def build_final_summary(
    panel: pd.DataFrame,
    markers: pd.DataFrame,
    anchors: pd.DataFrame,
    paper_lookup: dict[tuple[str, str, str], list[str]] | None = None,
    drug_lookup: dict[str, dict[str, str]] | None = None,
    drug_ref_lookup: dict[str, list[dict[str, str]]] | None = None,
    thresholds: Thresholds | None = None,
    top_n: int = 8,
) -> pd.DataFrame:
    """Build the human-readable Final_Summary sheet.

    For each row in `anchors` (region_user, cell_type_label, allen_subclass_anchor),
    look up the Allen subclass stats + top GPCRs from `panel` (filtered to
    final_recommendation in keep / keep_validate_spatially / candidate_to_validate
    and specificity_log2 > 0), and join the curated positive / exclusion markers
    from `markers`.
    """
    if panel.empty or anchors.empty:
        return pd.DataFrame()
    if "subclass" not in panel.columns or "taxonomy_level" not in panel.columns:
        return pd.DataFrame()

    sub = panel[panel["taxonomy_level"] == "subclass"].copy()
    keep_recs = {"keep", "keep_validate_spatially", "candidate_to_validate"}
    paper_lookup = paper_lookup or {}
    drug_lookup = drug_lookup or {}
    drug_ref_lookup = drug_ref_lookup or {}
    t = thresholds

    rows: list[dict] = []
    # Parallel list with structured tier-tagged genes per cell type, used by
    # build_final_recommendations() to make the conclusive picks sheet without
    # re-parsing the verbose combined_GPCRs_for_probe string.
    rec_rows: list[dict] = []
    for (region, cell_type), grp in anchors.groupby(["region_user", "cell_type_label"], sort=False):
        # Paper-suggested GPCRs are anchored to (region, cell_type), not subclass.
        paper_genes = _paper_genes_for(paper_lookup, region, cell_type)
        paper_set = set(paper_genes.keys())
        paper_str = ", ".join(sorted(paper_set)) if paper_set else ""

        for _, anc in grp.iterrows():
            anchor = str(anc["allen_subclass_anchor"]).strip()
            confidence = str(anc.get("confidence", "")).strip()
            note = str(anc.get("notes", "")).strip()
            role = str(anc.get("role", "target") or "target").strip().lower()
            is_exclusion = role in ("neighbor_control", "exclusion_counterstain")

            region_warn = REGION_DISSECTION_WARNINGS.get(region, "")

            tile = sub[(sub["region_user"] == region) & (sub["subclass"] == anchor)]
            if tile.empty:
                rows.append(
                    {
                        "region_user": region,
                        "cell_type_label": cell_type,
                        "allen_subclass_anchor": anchor,
                        "anchor_confidence": confidence,
                        "anchor_role": role,
                        "anchor_notes": note,
                        "region_dissection_warning": region_warn,
                        "n_cells_in_anchor": 0,
                        "cell_type_marker_genes": ", ".join(_markers_for(markers, region, cell_type, "positive_marker")),
                        "exclusion_markers": ", ".join(_markers_for(markers, region, cell_type, "exclusion_marker")),
                        "paper_suggested_gpcrs": paper_str,
                        "allen_validated_top_picks": "",
                        "allen_top_GPCRs_by_expression": "",
                        "combined_GPCRs_for_probe": "",
                        "combined_evidence_summary": "",
                        "n_GPCRs_keep": 0,
                        "n_broadly_detectable": 0,
                        "existing_drugs_for_picks": "",
                        "drugs_with_sources_per_picks": "",
                        "warning": "anchor subclass not found in computed panel",
                    }
                )
                rec_rows.append(
                    {
                        "region_user": region,
                        "cell_type_label": cell_type,
                        "allen_subclass_anchor": anchor,
                        "n_cells_in_anchor": 0,
                        "role": role,
                        "region_dissection_warning": region_warn,
                        "cell_type_marker_genes": _markers_for(markers, region, cell_type, "positive_marker"),
                        "exclusion_markers": _markers_for(markers, region, cell_type, "exclusion_marker"),
                        "agreed_keep": [],
                        "allen_only_keep": [],
                        "paper_with_broad": [],
                        "allen_only_broad": [],
                        "tile_stats": {},
                    }
                )
                continue

            n_cells = int(tile["n_cells"].iloc[0]) if "n_cells" in tile.columns else 0
            keep_rows = tile[tile["final_recommendation"].isin(keep_recs)].sort_values(
                ["combined_rank_score", "specificity_log2"], ascending=[True, False]
            )
            top_keep = _format_top_gpcrs(keep_rows, top_n, with_status=True)

            # Fallback: top GPCRs by raw mean expression regardless of recommendation,
            # so every cell type gets a non-empty list to consider for probe ordering.
            by_expr = tile.sort_values(
                ["mean_log2_expr", "pct_expr"], ascending=[False, False]
            )
            top_expr = _format_top_gpcrs(by_expr, top_n, with_status=False)

            # Agreement vs paper: which paper genes did Allen pipeline keep,
            # which are paper-only (allen downgraded or absent), and which are
            # Allen-specific keeps not in paper list.
            keep_genes = set(keep_rows["gpcr_gene"].astype(str))
            both = sorted(paper_set & keep_genes)
            paper_only = sorted(paper_set - keep_genes)
            allen_only = sorted(keep_genes - paper_set)
            agreement_parts = []
            if both:
                agreement_parts.append(f"both: {', '.join(both)}")
            if paper_only:
                # Annotate paper-only with why Allen downgraded them
                detail = []
                for g in paper_only:
                    grow = tile[tile["gpcr_gene"] == g]
                    if grow.empty:
                        detail.append(f"{g}(not_in_universe_or_no_data)")
                    else:
                        rec = str(grow["final_recommendation"].iloc[0])
                        spec = float(grow["specificity_log2"].iloc[0])
                        log2 = float(grow["mean_log2_expr"].iloc[0])
                        detail.append(f"{g}({rec},spec={spec:+.2f},log2={log2:.2f})")
                agreement_parts.append(f"paper_only: {'; '.join(detail)}")
            if allen_only:
                agreement_parts.append(f"allen_only_keep: {', '.join(allen_only)}")
            agreement = " | ".join(agreement_parts)

            # Build a single union list (combined_GPCRs_for_probe) tagged
            # by evidence source, sorted by evidence strength:
            #   1. paper+allen_keep                    (paper agrees + Allen keep)
            #   2. allen_only_keep                     (Allen-only specific finding)
            #   3. paper+allen_broadly_detectable      (paper agrees + reliable Allen signal but not specific)
            #   4. allen_only_broadly_detectable       (Allen-only broadly expressed signal)
            #   5. paper_only_allen_downgrade          (paper said yes, Allen has no detectable signal)
            keep_set = {str(g) for g in keep_rows["gpcr_gene"]}
            tile_sorted = tile.sort_values("specificity_log2", ascending=False)
            tile_lookup = {str(r["gpcr_gene"]): r for _, r in tile_sorted.iterrows()}

            # broadly-detectable rows (NOT in keep already)
            broad_set: set[str] = set()
            if t is not None:
                broad_mask = (
                    (tile["pct_expr"] >= t.broad_min_pct_expr)
                    & (tile["mean_log2_expr"] >= t.broad_min_mean_log2_expr)
                    & (tile["specificity_log2"] >= t.broad_min_specificity_log2)
                    & (~tile["gpcr_gene"].astype(str).isin(keep_set))
                )
                broad_set = set(tile.loc[broad_mask, "gpcr_gene"].astype(str))

            agreed_keep = [g for g in keep_rows["gpcr_gene"].astype(str) if g in paper_set]
            allen_only_keep_list = [g for g in keep_rows["gpcr_gene"].astype(str) if g not in paper_set]
            paper_with_broad = sorted(paper_set & broad_set)
            allen_only_broad = sorted(broad_set - paper_set)
            paper_only_seen = sorted(paper_set - keep_set - broad_set)

            def _fmt_g(g: str, tag: str) -> str:
                r = tile_lookup.get(g)
                drug_info = drug_lookup.get(g) or {}
                approved = (drug_info.get("approved_drugs") or "").strip().rstrip("-")
                drug_str = f"; drugs: {approved}" if approved and approved != "-" else "; drugs: research_only_or_none"
                if r is None:
                    return f"{g}[{tag}, no_allen_data{drug_str}]"
                spec = float(r.get("specificity_log2", 0.0) or 0.0)
                log2 = float(r.get("mean_log2_expr", 0.0) or 0.0)
                pct = float(r.get("pct_expr", 0.0) or 0.0)
                return f"{g}[{tag}, spec={spec:+.2f}, log2={log2:.2f}, pct={pct:.0f}%{drug_str}]"

            combined_parts: list[str] = []
            for g in agreed_keep:
                combined_parts.append(_fmt_g(g, "paper+allen_keep"))
            for g in allen_only_keep_list:
                combined_parts.append(_fmt_g(g, "allen_only_keep"))
            for g in paper_with_broad:
                combined_parts.append(_fmt_g(g, "paper+allen_broadly_detectable"))
            for g in allen_only_broad:
                combined_parts.append(_fmt_g(g, "allen_only_broadly_detectable"))
            for g in paper_only_seen:
                combined_parts.append(_fmt_g(g, "paper_only_allen_downgrade"))
            combined_for_probe = "; ".join(combined_parts)

            agreement_parts = []
            if agreed_keep:
                agreement_parts.append(f"both_keep: {', '.join(agreed_keep)}")
            if allen_only_keep_list:
                agreement_parts.append(f"allen_only_keep: {', '.join(allen_only_keep_list)}")
            if paper_with_broad:
                agreement_parts.append(f"paper+broadly_detectable: {', '.join(paper_with_broad)}")
            if allen_only_broad:
                agreement_parts.append(f"allen_only_broadly_detectable: {', '.join(allen_only_broad)}")
            if paper_only_seen:
                detail = []
                for g in paper_only_seen:
                    grow = tile[tile["gpcr_gene"] == g]
                    if grow.empty:
                        detail.append(f"{g}(not_in_universe_or_no_data)")
                    else:
                        rec = str(grow["final_recommendation"].iloc[0])
                        spec = float(grow["specificity_log2"].iloc[0])
                        log2 = float(grow["mean_log2_expr"].iloc[0])
                        detail.append(f"{g}({rec},spec={spec:+.2f},log2={log2:.2f})")
                agreement_parts.append(f"paper_only: {'; '.join(detail)}")
            combined_evidence_summary = " | ".join(agreement_parts)

            warnings: list[str] = []
            if n_cells < 30:
                warnings.append("anchor has < 30 cells; treat with caution")
            if not top_keep and not broad_set:
                warnings.append("no GPCR passes keep/validate or broadly_detectable thresholds; using expression fallback")
            elif not top_keep and broad_set:
                warnings.append(
                    f"no cell-type-specific GPCR; relying on {len(broad_set)} broadly_expressed_detectable candidates"
                )

            # drugs for any gene in the union (keep + broad + paper-only)
            union_genes_for_drugs: list[str] = []
            for g in agreed_keep + allen_only_keep_list + paper_with_broad + allen_only_broad + paper_only_seen:
                if g not in union_genes_for_drugs:
                    union_genes_for_drugs.append(g)
            drug_lines = []
            for g in union_genes_for_drugs:
                d = drug_lookup.get(g) or {}
                approved = (d.get("approved_drugs") or "").strip()
                exper = (d.get("experimental_or_research") or "").strip()
                ind = (d.get("clinical_indications") or "").strip()
                if not approved and not exper:
                    continue
                bits = [g]
                if approved and approved not in {"-", "–", ""}:
                    bits.append(f"FDA: {approved}")
                if exper and exper not in {"-", "–", ""}:
                    bits.append(f"clinical/research: {exper}")
                if ind:
                    bits.append(f"indication: {ind}")
                drug_lines.append(" | ".join(bits))
            existing_drugs_str = " || ".join(drug_lines)

            # Per-drug citation lines from the long-format drug references CSV.
            # Each gene → one cell with bullet-style "DrugName [status, year] :: DrugBank :: PubMed PMID URL"
            ref_lines: list[str] = []
            for g in union_genes_for_drugs:
                drugs_for_gene = drug_ref_lookup.get(g) or []
                if not drugs_for_gene:
                    continue
                ref_lines.append(f"== {g} ==")
                for entry in drugs_for_gene:
                    name = entry.get("drug_name") or ""
                    status = entry.get("drug_status") or ""
                    year = entry.get("year_approved_or_published") or ""
                    db_id = entry.get("drugbank_id") or ""
                    db_url = entry.get("drugbank_url") or ""
                    pmid = entry.get("key_pmid") or ""
                    pm_url = entry.get("pubmed_url") or ""
                    ind_e = entry.get("indication") or ""
                    src_bits: list[str] = []
                    if db_id and db_url:
                        src_bits.append(f"DrugBank: {db_id} ({db_url})")
                    elif db_id:
                        src_bits.append(f"DrugBank: {db_id}")
                    fda_app = entry.get("fda_application") or ""
                    if fda_app:
                        src_bits.append(f"FDA: {fda_app}")
                    if pmid and pm_url:
                        src_bits.append(f"PMID:{pmid} ({pm_url})")
                    elif pmid:
                        src_bits.append(f"PMID:{pmid}")
                    head_bits = [name]
                    if status:
                        head_bits.append(f"[{status}{', ' + year if year else ''}]")
                    if ind_e:
                        head_bits.append(f"-> {ind_e}")
                    line = " ".join(head_bits)
                    if src_bits:
                        line += "  ::  " + " ; ".join(src_bits)
                    ref_lines.append(line)
            drugs_with_sources_str = "\n".join(ref_lines)

            rows.append(
                {
                    "region_user": region,
                    "cell_type_label": cell_type,
                    "allen_subclass_anchor": anchor,
                    "anchor_confidence": confidence,
                    "anchor_role": role,
                    "anchor_notes": note,
                    "region_dissection_warning": region_warn,
                    "n_cells_in_anchor": n_cells,
                    "cell_type_marker_genes": ", ".join(
                        _markers_for(markers, region, cell_type, "positive_marker")
                    ),
                    "exclusion_markers": ", ".join(
                        _markers_for(markers, region, cell_type, "exclusion_marker")
                    ),
                    "paper_suggested_gpcrs": paper_str,
                    "allen_validated_top_picks": top_keep,
                    "allen_top_GPCRs_by_expression": top_expr,
                    "combined_GPCRs_for_probe": combined_for_probe,
                    "combined_evidence_summary": combined_evidence_summary,
                    "n_GPCRs_keep": int(len(keep_rows)),
                    "n_broadly_detectable": int(len(broad_set)),
                    "existing_drugs_for_picks": existing_drugs_str,
                    "drugs_with_sources_per_picks": drugs_with_sources_str,
                    "warning": "; ".join(warnings),
                }
            )

            # Stat-augmented gene-tier lookup for build_final_recommendations.
            tile_stats = {
                str(rrr["gpcr_gene"]): {
                    "spec": float(rrr.get("specificity_log2", 0.0) or 0.0),
                    "log2": float(rrr.get("mean_log2_expr", 0.0) or 0.0),
                    "pct": float(rrr.get("pct_expr", 0.0) or 0.0),
                }
                for _, rrr in tile.iterrows()
            }
            rec_rows.append(
                {
                    "region_user": region,
                    "cell_type_label": cell_type,
                    "allen_subclass_anchor": anchor,
                    "n_cells_in_anchor": n_cells,
                    "role": role,
                    "region_dissection_warning": region_warn,
                    "cell_type_marker_genes": _markers_for(markers, region, cell_type, "positive_marker"),
                    "exclusion_markers": _markers_for(markers, region, cell_type, "exclusion_marker"),
                    "agreed_keep": list(agreed_keep),
                    "allen_only_keep": list(allen_only_keep_list),
                    "paper_with_broad": list(paper_with_broad),
                    "allen_only_broad": list(allen_only_broad),
                    "tile_stats": tile_stats,
                }
            )
    return pd.DataFrame(rows), rec_rows


def build_final_recommendations(
    rec_rows: list[dict],
    drug_ref_lookup: dict[str, list[dict[str, str]]] | None = None,
    max_genes: int = 5,
) -> pd.DataFrame:
    """Build a clean, conclusive recommendations sheet (one row per cell type).

    Picks at most `max_genes` GPCRs per cell type using the tier priority:
        1. paper+allen_keep (gold)
        2. allen_only_keep
        3. paper+allen_broadly_detectable
        4. allen_only_broadly_detectable
    Genes within a tier are kept in original order (sorted by spec/expression
    upstream). For each gene, picks the FIRST FDA-approved drug from the
    long-format drug references; falls back to first clinical/research drug
    if no FDA approval exists; "—" if no drug is curated.
    """
    drug_ref_lookup = drug_ref_lookup or {}

    def _pick_top_drug(gene: str) -> tuple[str, str]:
        """Return (drug_label, drugbank_id_or_empty)."""
        entries = drug_ref_lookup.get(gene) or []
        if not entries:
            return "—", ""
        # Prefer FDA-approved
        fda = [e for e in entries if "FDA-approved" in (e.get("drug_status") or "")]
        chosen = fda[0] if fda else entries[0]
        name = chosen.get("drug_name") or "—"
        year = chosen.get("year_approved_or_published") or ""
        status = chosen.get("drug_status") or ""
        # Compact status mark
        if "FDA-approved" in status:
            mark = f"FDA{(' ' + year) if year and year.replace('-', '').isdigit() else ''}"
        elif "withdrawn" in status:
            mark = "withdrawn"
        elif "clinical-trial" in status:
            mark = "clinical-trial"
        elif "approved-Japan" in status:
            mark = "Japan-only"
        elif "approved-EU" in status:
            mark = "EU-only"
        else:
            mark = "research"
        label = f"{name} ({mark})"
        return label, (chosen.get("drugbank_id") or "").strip()

    out: list[dict] = []
    for row in rec_rows:
        region = row["region_user"]
        ct = row["cell_type_label"]
        anchor = row["allen_subclass_anchor"]
        n_cells = row["n_cells_in_anchor"]
        role = str(row.get("role", "target") or "target").lower()
        is_exclusion = role in ("neighbor_control", "exclusion_counterstain")
        agreed = list(row["agreed_keep"])
        allen_keep = list(row["allen_only_keep"])
        paper_broad = list(row["paper_with_broad"])
        allen_broad = list(row["allen_only_broad"])

        # Tier-priority filling up to max_genes.
        ranked: list[tuple[str, str]] = []
        for g in agreed:
            ranked.append((g, "paper+allen_keep"))
        for g in allen_keep:
            ranked.append((g, "allen_only_keep"))
        for g in paper_broad:
            ranked.append((g, "paper+allen_broadly_detectable"))
        for g in allen_broad:
            ranked.append((g, "allen_only_broadly_detectable"))
        ranked = ranked[:max_genes]

        gene_panel = ", ".join([g for g, _ in ranked])
        tier_str = "; ".join([f"{g}={t}" for g, t in ranked])

        # gene-keyed drug list
        drug_pairs = []
        for g, _ in ranked:
            label, _db = _pick_top_drug(g)
            drug_pairs.append(f"{g}: {label}")
        drugs_str = " | ".join(drug_pairs)

        # what-to-do summary - separate verdict for exclusion counter-stain rows
        if is_exclusion:
            action = "NEIGHBOR CONTROL (validation counter-stain; not a primary probe target)"
            drugs_str = "(neighbor control / counter-stain; drugs not recommended)"
        else:
            n_keep = sum(1 for _, t in ranked if t.endswith("keep"))
            n_broad = sum(1 for _, t in ranked if "broadly" in t)
            if n_keep >= 1:
                action = "ORDER (cell-type-specific picks available)"
            elif n_broad >= 1:
                action = "ORDER WITH SPATIAL CONSTRAINT (broadly detectable only)"
            elif n_cells == 0:
                action = "REVIEW - anchor subclass not found"
            else:
                action = "REVIEW - no GPCR passed any threshold"

        out.append(
            {
                "region": region,
                "cell_type": ct,
                "allen_subclass": anchor,
                "role": role,
                "n_cells_in_anchor": n_cells,
                "region_dissection_warning": row.get("region_dissection_warning", ""),
                "cell_type_marker_genes": ", ".join(row.get("cell_type_marker_genes") or []),
                "exclusion_markers": ", ".join(row.get("exclusion_markers") or []),
                "recommended_GPCR_panel": gene_panel,
                "recommended_drugs_per_gene": drugs_str,
                "n_genes_recommended": len(ranked),
                "evidence_tier_per_gene": tier_str,
                "what_to_do": action,
            }
        )
    return pd.DataFrame(out)


def build_final_probe_panel(
    allen: pd.DataFrame,
    markers: pd.DataFrame,
    paper: pd.DataFrame,
    paper_sugg_lookup: dict[tuple[str, str, str], list[str]] | None = None,
) -> pd.DataFrame:
    if allen.empty:
        return pd.DataFrame()
    base = allen.copy()
    # marker role lookup: by (region_user, gene)
    marker_role = {}
    if not markers.empty and {"region_user", "gene", "gene_role"}.issubset(markers.columns):
        for _, r in markers.iterrows():
            key = (str(r["region_user"]).strip(), str(r["gene"]).strip())
            roles = marker_role.setdefault(key, set())
            roles.add(str(r.get("gene_role", "")).strip())
        base["marker_role"] = base.apply(
            lambda r: ", ".join(sorted(marker_role.get((str(r["region_user"]), str(r["gpcr_gene"])), set()))),
            axis=1,
        )
    else:
        base["marker_role"] = ""
    # paper evidence join (legacy: numeric paper means)
    paper_num_lookup = {}
    if not paper.empty and {"gene", "mean_expr"}.issubset(paper.columns):
        for _, r in paper.iterrows():
            paper_num_lookup[str(r["gene"]).strip()] = (
                float(r.get("mean_expr") or 0.0),
                float(r.get("pct_expr") or 0.0),
            )
        base["paper_mean_expr"] = base["gpcr_gene"].map(lambda g: paper_num_lookup.get(str(g), (None, None))[0])
        base["paper_pct_expr"] = base["gpcr_gene"].map(lambda g: paper_num_lookup.get(str(g), (None, None))[1])
    else:
        base["paper_mean_expr"] = pd.NA
        base["paper_pct_expr"] = pd.NA

    # paper_suggested flag + paper_source per (region, gene). Note: the panel is
    # at (region, subclass, gene) granularity but paper suggestions are at
    # (region, cell_type, gene). We aggregate sources across cell_types within a
    # region so a gene flagged in any cell_type is still discoverable.
    if paper_sugg_lookup:
        per_region_gene: dict[tuple[str, str], set[str]] = {}
        for (r, ct, g), srcs in paper_sugg_lookup.items():
            key = (r, g)
            per_region_gene.setdefault(key, set()).update(srcs)
        per_region_gene_sorted = {k: sorted(v) for k, v in per_region_gene.items()}
        base["paper_suggested"] = base.apply(
            lambda r: (str(r["region_user"]), str(r["gpcr_gene"])) in per_region_gene_sorted,
            axis=1,
        )
        base["paper_source"] = base.apply(
            lambda r: "; ".join(per_region_gene_sorted.get((str(r["region_user"]), str(r["gpcr_gene"])), [])),
            axis=1,
        )
    else:
        base["paper_suggested"] = False
        base["paper_source"] = ""
    return base


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None)
    p.add_argument("--out_xlsx", required=True)
    p.add_argument("--allen_subclass_csv", default=None)
    p.add_argument("--allen_supertype_csv", default=None)
    p.add_argument("--allen_cluster_csv", default=None)
    p.add_argument("--published_marker_csv", default=None)
    p.add_argument("--paper_gpcr_csv", default=None)
    p.add_argument("--region_mapping_csv", default=None)
    p.add_argument("--old_candidates_csv", default=None)
    p.add_argument(
        "--celltype_anchor_csv",
        default=None,
        help="CSV with columns region_user, cell_type_label, allen_subclass_anchor, confidence, notes",
    )
    p.add_argument(
        "--paper_suggestions_csv",
        default=None,
        help="CSV with columns region_user, cell_type_label, gene, paper_source, notes",
    )
    p.add_argument(
        "--drug_targets_csv",
        default=None,
        help=(
            "Wide CSV listing existing drugs that target each GPCR; columns: "
            "gene_symbol, approved_drugs, experimental_or_research, primary_mechanism, "
            "clinical_indications, notes."
        ),
    )
    p.add_argument(
        "--drug_references_csv",
        default=None,
        help=(
            "Long CSV (one row per drug) with full source citations; columns: "
            "gene_symbol, iuphar_receptor, drug_name, drug_status, drug_class, "
            "year_approved_or_published, indication, drugbank_id, drugbank_url, "
            "fda_application, key_pmid, pubmed_url, notes."
        ),
    )
    p.add_argument("--top_n_gpcrs_in_summary", type=int, default=8)
    args = p.parse_args()

    cfg = load_config(args.config)

    allen_levels = {
        "subclass": _read_optional(args.allen_subclass_csv),
        "supertype": _read_optional(args.allen_supertype_csv),
        "cluster": _read_optional(args.allen_cluster_csv),
    }
    markers = _read_optional(args.published_marker_csv)
    paper = _read_optional(args.paper_gpcr_csv)
    mapping = _read_optional(args.region_mapping_csv)
    old = _read_optional(args.old_candidates_csv)
    anchors = _read_optional(args.celltype_anchor_csv)
    paper_sugg = _read_optional(args.paper_suggestions_csv)
    paper_lookup = _build_paper_lookup(paper_sugg)
    print(f"[INFO] paper_suggestions_csv: {len(paper_sugg)} rows, lookup keys: {len(paper_lookup)}")

    drug_targets = _read_optional(args.drug_targets_csv)
    drug_lookup: dict[str, dict[str, str]] = {}
    if not drug_targets.empty and "gene_symbol" in drug_targets.columns:
        for _, r in drug_targets.iterrows():
            drug_lookup[str(r["gene_symbol"]).strip()] = {
                k: ("" if pd.isna(r.get(k)) else str(r.get(k)))
                for k in (
                    "approved_drugs",
                    "experimental_or_research",
                    "primary_mechanism",
                    "clinical_indications",
                    "notes",
                )
            }
    print(f"[INFO] drug_targets_csv: {len(drug_targets)} rows, lookup keys: {len(drug_lookup)}")

    drug_refs = _read_optional(args.drug_references_csv)
    # Normalize numeric-looking columns that pandas autocast to float
    # (PMIDs lose precision and gain trailing ".0"). Force int strings.
    if not drug_refs.empty and "key_pmid" in drug_refs.columns:
        def _clean_pmid(v):
            if pd.isna(v):
                return ""
            try:
                return str(int(float(v)))
            except (TypeError, ValueError):
                return str(v).strip()
        drug_refs["key_pmid"] = drug_refs["key_pmid"].apply(_clean_pmid)
    drug_ref_lookup: dict[str, list[dict[str, str]]] = {}
    if not drug_refs.empty and "gene_symbol" in drug_refs.columns:
        for _, r in drug_refs.iterrows():
            gene = str(r["gene_symbol"]).strip()
            entry = {
                k: ("" if pd.isna(r.get(k)) else str(r.get(k)).strip())
                for k in (
                    "drug_name",
                    "drug_status",
                    "drug_class",
                    "year_approved_or_published",
                    "indication",
                    "drugbank_id",
                    "drugbank_url",
                    "fda_application",
                    "key_pmid",
                    "pubmed_url",
                    "notes",
                )
            }
            drug_ref_lookup.setdefault(gene, []).append(entry)
    print(
        f"[INFO] drug_references_csv: {len(drug_refs)} rows, "
        f"genes covered: {len(drug_ref_lookup)}"
    )

    classified_levels: dict[str, pd.DataFrame] = {}
    for lvl, df in allen_levels.items():
        if df.empty:
            continue
        classified_levels[lvl] = classify(df, cfg.thresholds)

    # Final probe panel = union across levels, with level column kept
    panel_parts: list[pd.DataFrame] = []
    for lvl, df in classified_levels.items():
        if "taxonomy_level" not in df.columns:
            df = df.copy()
            df["taxonomy_level"] = lvl
        panel_parts.append(build_final_probe_panel(df, markers, paper, paper_lookup))
    panel = pd.concat(panel_parts, ignore_index=True) if panel_parts else pd.DataFrame()

    if not panel.empty:
        panel["final_recommendation"] = panel["validation_status"].map(
            {
                "final_keep": "keep",
                "supported_by_expression": "keep_validate_spatially",
                "candidate_to_review": "candidate_to_validate",
                "downgrade_low_expression": "downgrade",
                "downgrade_low_specificity": "downgrade",
                "too_few_cells": "needs_more_cells",
            }
        ).fillna("candidate_to_validate")

    out_xlsx = Path(args.out_xlsx)
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)

    readme = pd.DataFrame(
        [
            {"item": "purpose", "value": "Final evidence-aware GPCR/cell-marker probe planning workbook"},
            {"item": "rule", "value": "Candidate GPCRs are not final until computed expression and region/cell-type evidence support them."},
            {"item": "manifest_version", "value": cfg.manifest_version or "<latest>"},
            {"item": "min_cells", "value": cfg.thresholds.min_cells},
            {"item": "min_mean_log2_expr_candidate", "value": cfg.thresholds.min_mean_log2_expr_candidate},
            {"item": "min_pct_expr_candidate", "value": cfg.thresholds.min_pct_expr_candidate},
            {"item": "strong_mean_log2_expr", "value": cfg.thresholds.strong_mean_log2_expr},
            {"item": "strong_pct_expr", "value": cfg.thresholds.strong_pct_expr},
            {"item": "broad_min_pct_expr", "value": cfg.thresholds.broad_min_pct_expr},
            {"item": "broad_min_mean_log2_expr", "value": cfg.thresholds.broad_min_mean_log2_expr},
            {"item": "broad_min_specificity_log2", "value": cfg.thresholds.broad_min_specificity_log2},
            {
                "item": "tier_definition_keep",
                "value": "specificity_log2 > 0 AND pct >= strong_pct_expr AND log2 >= strong_mean_log2_expr (cell-type-specific probes)",
            },
            {
                "item": "tier_definition_broadly_detectable",
                "value": (
                    "pct >= broad_min_pct_expr AND log2 >= broad_min_mean_log2_expr AND specificity_log2 >= broad_min_specificity_log2 "
                    "(reliable FISH signal but NOT cell-type specific; use only if region/spatial is constrained)"
                ),
            },
        ]
    )

    summary, rec_rows = build_final_summary(
        panel,
        markers,
        anchors,
        paper_lookup=paper_lookup,
        drug_lookup=drug_lookup,
        drug_ref_lookup=drug_ref_lookup,
        thresholds=cfg.thresholds,
        top_n=args.top_n_gpcrs_in_summary,
    )
    recommendations = build_final_recommendations(rec_rows, drug_ref_lookup=drug_ref_lookup)

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        readme.to_excel(w, sheet_name="README", index=False)
        if not recommendations.empty:
            recommendations.to_excel(w, sheet_name="FINAL_Recommendations", index=False)
        if not summary.empty:
            summary.to_excel(w, sheet_name="Final_Summary", index=False)
        if not mapping.empty:
            mapping.to_excel(w, sheet_name="Region_Mapping_Final", index=False)
        if not anchors.empty:
            anchors.to_excel(w, sheet_name="CellType_Subclass_Anchors", index=False)
        if not paper_sugg.empty:
            paper_sugg.to_excel(w, sheet_name="Paper_GPCR_Suggestions", index=False)
        if not drug_targets.empty:
            drug_targets.to_excel(w, sheet_name="GPCR_Drug_Targets", index=False)
        if not drug_refs.empty:
            drug_refs.to_excel(w, sheet_name="GPCR_Drug_References", index=False)
        for lvl, df in classified_levels.items():
            df.to_excel(w, sheet_name=f"Computed_GPCR_{lvl}", index=False)
        if not markers.empty:
            markers.to_excel(w, sheet_name="Published_Marker_Backbone", index=False)
        if not paper.empty:
            paper.to_excel(w, sheet_name="Paper_Data_Validation", index=False)
        if not panel.empty:
            panel.to_excel(w, sheet_name="Final_Probe_Panel", index=False)
            removed = panel[panel["final_recommendation"].isin(["downgrade", "needs_more_cells"])]
            if not removed.empty:
                removed.to_excel(w, sheet_name="Removed_or_Downgraded", index=False)
        if not old.empty:
            old.to_excel(w, sheet_name="Old_Candidates", index=False)

    write_run_log(
        out_xlsx.parent,
        "D02_create_final_probe_workbook",
        {
            "out_xlsx": str(out_xlsx),
            "thresholds": cfg.thresholds.__dict__,
            "levels_present": list(classified_levels.keys()),
            "n_panel_rows": int(len(panel)),
            "n_summary_rows": int(len(summary)),
            "celltype_anchor_csv": args.celltype_anchor_csv,
        },
    )
    print(f"[DONE] {out_xlsx}")


if __name__ == "__main__":
    main()
