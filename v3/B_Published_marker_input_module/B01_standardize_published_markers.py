#!/usr/bin/env python
"""
B01_standardize_published_markers.py

Module B: Published-marker input module.
Purpose:
- Convert curated/published marker table into long format.
- Keep marker source and confidence separated from GPCR evidence.
"""
from pathlib import Path
import argparse
import pandas as pd


def split_genes(x):
    if pd.isna(x):
        return []
    return [g.strip() for g in str(x).replace('/', ',').replace(';', ',').split(',') if g.strip()]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--markers_csv', required=True)
    p.add_argument('--out_dir', required=True)
    args=p.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    df=pd.read_csv(args.markers_csv)
    rows=[]
    for _, r in df.iterrows():
        for g in split_genes(r.get('marker_genes','')):
            rows.append({
                'region_user': r.get('region_user'),
                'cell_type_label': r.get('cell_type_label'),
                'gene': g,
                'gene_role': 'positive_marker',
                'source': r.get('source',''),
                'confidence': r.get('confidence',''),
                'notes': r.get('notes',''),
            })
        for g in split_genes(r.get('exclusion_markers','')):
            rows.append({
                'region_user': r.get('region_user'),
                'cell_type_label': r.get('cell_type_label'),
                'gene': g,
                'gene_role': 'exclusion_marker',
                'source': r.get('source',''),
                'confidence': r.get('confidence',''),
                'notes': r.get('notes',''),
            })
    long=pd.DataFrame(rows)
    long.to_csv(out/'Published_Cell_Marker_Long.csv', index=False)
    df.to_csv(out/'Published_Cell_Marker_Backbone.csv', index=False)
    print('[DONE] Published_Cell_Marker_Long.csv', long.shape)

if __name__ == '__main__':
    main()
