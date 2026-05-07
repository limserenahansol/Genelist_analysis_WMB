#!/usr/bin/env python
"""
B02_validate_marker_presence_in_allen.py

Module B: Published-marker input module.
Purpose:
- Check if curated/published marker genes are present in Allen gene metadata.
"""
from pathlib import Path
import argparse
import pandas as pd
from abc_atlas_access.abc_atlas_cache.abc_project_cache import AbcProjectCache


def detect_gene_symbol_col(gene):
    for c in ['gene_symbol','symbol','gene_name','name']:
        if c in gene.columns:
            return c
    return gene.columns[0]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cache_dir', required=True)
    p.add_argument('--marker_long_csv', required=True)
    p.add_argument('--out_dir', required=True)
    args=p.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    cache=AbcProjectCache.from_cache_dir(Path(args.cache_dir))
    gene=cache.get_metadata_dataframe('WMB-10X','gene')
    col=detect_gene_symbol_col(gene)
    available=set(gene[col].dropna().astype(str).str.strip())
    markers=pd.read_csv(args.marker_long_csv)
    markers['present_in_allen_gene_metadata']=markers['gene'].astype(str).str.strip().isin(available)
    markers.to_csv(out/'Marker_Presence_In_Allen.csv', index=False)
    print('[DONE] Marker_Presence_In_Allen.csv')

if __name__ == '__main__':
    main()
