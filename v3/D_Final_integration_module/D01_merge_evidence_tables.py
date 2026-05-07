#!/usr/bin/env python
"""
D01_merge_evidence_tables.py

Module D: Final integration module.
Purpose:
- Merge Allen-computed, published-marker, paper-computed, and old candidate evidence.
"""
from pathlib import Path
import argparse
import pandas as pd


def read_csv_optional(path):
    if not path:
        return pd.DataFrame()
    p=Path(path)
    if not p.exists():
        print(f'[WARN] missing {p}')
        return pd.DataFrame()
    return pd.read_csv(p)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--allen_gpcr_csv', default=None)
    p.add_argument('--marker_long_csv', default=None)
    p.add_argument('--paper_gpcr_csv', default=None)
    p.add_argument('--old_candidates_csv', default=None)
    p.add_argument('--out_dir', required=True)
    args=p.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    allen=read_csv_optional(args.allen_gpcr_csv)
    markers=read_csv_optional(args.marker_long_csv)
    paper=read_csv_optional(args.paper_gpcr_csv)
    old=read_csv_optional(args.old_candidates_csv)

    if not allen.empty:
        allen['evidence_layer']='Allen_computed'
    if not paper.empty:
        paper['evidence_layer']='Paper_computed'
    if not markers.empty:
        markers['evidence_layer']='Published_marker'
    if not old.empty:
        old['evidence_layer']='Old_candidate_workbook'

    summary=pd.DataFrame([
        {'table':'Allen GPCR', 'rows':len(allen)},
        {'table':'Published markers', 'rows':len(markers)},
        {'table':'Paper GPCR', 'rows':len(paper)},
        {'table':'Old candidates', 'rows':len(old)},
    ])
    summary.to_csv(out/'Integration_Input_Summary.csv', index=False)

    # Standard outputs are separate; D02 will write workbook.
    if not allen.empty: allen.to_csv(out/'Integrated_Allen_GPCR.csv', index=False)
    if not markers.empty: markers.to_csv(out/'Integrated_Published_Markers.csv', index=False)
    if not paper.empty: paper.to_csv(out/'Integrated_Paper_GPCR.csv', index=False)
    if not old.empty: old.to_csv(out/'Integrated_Old_Candidates.csv', index=False)
    print('[DONE] integration files written')

if __name__ == '__main__':
    main()
