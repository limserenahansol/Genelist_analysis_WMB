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


def build_final_probe_panel(allen: pd.DataFrame, markers: pd.DataFrame, paper: pd.DataFrame) -> pd.DataFrame:
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
    # paper evidence join
    paper_lookup = {}
    if not paper.empty and {"gene", "mean_expr"}.issubset(paper.columns):
        for _, r in paper.iterrows():
            paper_lookup[str(r["gene"]).strip()] = (
                float(r.get("mean_expr") or 0.0),
                float(r.get("pct_expr") or 0.0),
            )
        base["paper_mean_expr"] = base["gpcr_gene"].map(lambda g: paper_lookup.get(str(g), (None, None))[0])
        base["paper_pct_expr"] = base["gpcr_gene"].map(lambda g: paper_lookup.get(str(g), (None, None))[1])
    else:
        base["paper_mean_expr"] = pd.NA
        base["paper_pct_expr"] = pd.NA
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
        panel_parts.append(build_final_probe_panel(df, markers, paper))
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
        ]
    )

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        readme.to_excel(w, sheet_name="README", index=False)
        if not mapping.empty:
            mapping.to_excel(w, sheet_name="Region_Mapping_Final", index=False)
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
        },
    )
    print(f"[DONE] {out_xlsx}")


if __name__ == "__main__":
    main()
