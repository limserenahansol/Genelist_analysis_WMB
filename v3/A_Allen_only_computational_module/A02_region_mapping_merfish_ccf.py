#!/usr/bin/env python
"""
A02_region_mapping_merfish_ccf.py

Module A: Allen-only computational module.

Maps user labels (BMAp/LM/RE/CP/ORBm/AId) to exact Allen ROI rows.

Key fix vs. earlier version
---------------------------
Old script did substring search across every text column, which over-matched
short acronyms like ``LM`` against gene symbols and cluster names.

This version:
1. Reads the official Allen ``region_of_interest_metadata.csv`` (small file,
   ~few hundred rows) and finds **exact acronym** matches first.
2. Falls back to **word-boundary** searches against canonical name fields
   (``region_of_interest_name``, ``anatomical_division`` if present).
3. Writes a manual review CSV so the human still confirms LM/AId before
   probe ordering, but with much fewer false positives to wade through.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_config, open_abc_cache, write_run_log  # noqa: E402

DEFAULT_QUERIES: dict[str, dict[str, list[str]]] = {
    "BMAp": {
        "acronyms": ["BMAp", "sAMY"],
        "name_terms": ["basomedial amygdalar", "striatum-like amygdalar"],
    },
    "LM": {
        "acronyms": ["LM", "MM", "MB"],
        "name_terms": ["lateral mammillary", "mammillary"],
    },
    "RE": {
        "acronyms": ["RE", "TH"],
        "name_terms": ["reuniens", "midline thalamus"],
    },
    "CP": {
        "acronyms": ["CP", "STRd"],
        "name_terms": ["caudoputamen", "dorsal striatum"],
    },
    "ORBm": {
        "acronyms": ["ORBm", "ORB", "PL-ILA-ORB"],
        "name_terms": ["orbital area, medial", "prelimbic", "infralimbic"],
    },
    "AId": {
        "acronyms": ["AId", "AI"],
        "name_terms": ["agranular insular", "insular"],
    },
}


def _word_boundary_contains(series: pd.Series, term: str) -> pd.Series:
    pattern = r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
    return series.fillna("").astype(str).str.contains(pattern, case=False, regex=True, na=False)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None)
    p.add_argument("--out_dir", required=True)
    p.add_argument(
        "--metadata_dir",
        default=None,
        help="Directory holding A01 parquet outputs; if missing, A02 reads from cache directly.",
    )
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config(args.config)
    cache = open_abc_cache(cfg)

    roi_meta = cache.get_metadata_dataframe("WMB-10X", "region_of_interest_metadata")
    print("[INFO] region_of_interest_metadata columns:", list(roi_meta.columns))

    acronym_col = next(
        (c for c in ["acronym", "region_of_interest_acronym"] if c in roi_meta.columns),
        roi_meta.columns[0],
    )
    name_col = next(
        (c for c in ["name", "region_of_interest_name", "anatomical_division_label"] if c in roi_meta.columns),
        None,
    )

    queries = cfg.raw.get("region_acronym_queries", DEFAULT_QUERIES)

    rows: list[dict] = []
    for user_label, q in queries.items():
        acronym_hits: list[str] = []
        name_hits: list[str] = []
        if isinstance(q, dict):
            requested = list(q.get("acronyms", []))
            terms = list(q.get("name_terms", []))
        else:
            requested = list(q)
            terms = []
        for ac in requested:
            mask = roi_meta[acronym_col].astype(str).str.casefold() == ac.casefold()
            if mask.any():
                acronym_hits.append(ac)
        if name_col is not None:
            for term in terms:
                mask = _word_boundary_contains(roi_meta[name_col], term)
                if mask.any():
                    name_hits.extend(roi_meta.loc[mask, acronym_col].astype(str).tolist())
        all_hits = sorted(set(acronym_hits) | set(name_hits))
        rows.append(
            {
                "region_user": user_label,
                "matched_allen_acronyms": ", ".join(all_hits),
                "match_kind": (
                    "exact"
                    if acronym_hits and not name_hits
                    else "exact+name_term"
                    if acronym_hits and name_hits
                    else "name_term_only"
                    if name_hits
                    else "no_match"
                ),
            }
        )

    matches_df = pd.DataFrame(rows)
    matches_df.to_csv(out / "Allen_Region_Label_Candidate_Matches.csv", index=False)

    # manual mapping table for downstream A03
    mapping_rows: list[dict] = []
    for r in rows:
        acs = [a.strip() for a in (r["matched_allen_acronyms"] or "").split(",") if a.strip()]
        if not acs:
            mapping_rows.append(
                {
                    "region_user": r["region_user"],
                    "allen_region_column": "region_of_interest_acronym",
                    "allen_region_value": "",
                    "confidence": "no_match_review_required",
                }
            )
            continue
        for ac in acs:
            mapping_rows.append(
                {
                    "region_user": r["region_user"],
                    "allen_region_column": "region_of_interest_acronym",
                    "allen_region_value": ac,
                    "confidence": (
                        "high_exact"
                        if r["match_kind"] in ("exact", "exact+name_term")
                        else "medium_name_only"
                    ),
                }
            )

    pd.DataFrame(mapping_rows).to_csv(out / "Region_Mapping_Auto_Draft.csv", index=False)

    checklist = pd.DataFrame(
        {
            "region_user": list(queries.keys()),
            "manual_review_required": [True] * len(queries),
            "final_allen_acronym": [""] * len(queries),
            "final_allen_name": [""] * len(queries),
            "confidence": ["pending"] * len(queries),
            "notes": ["Confirm exact Allen label before probe ordering."] * len(queries),
        }
    )
    checklist.to_csv(out / "Region_Mapping_Manual_Checklist.csv", index=False)

    write_run_log(
        out,
        "A02_region_mapping_merfish_ccf",
        {
            "manifest_version": cfg.manifest_version,
            "queries": list(queries.keys()),
            "n_match_rows": len(rows),
        },
    )
    print(f"[DONE] {out}/Allen_Region_Label_Candidate_Matches.csv (and auto-draft + checklist)")


if __name__ == "__main__":
    main()
