#!/usr/bin/env python
"""
C03_compute_paper_gpcr_marker_validation.py

Module C: Published raw-data extraction module.
Purpose:
- Given standardized paper expression + metadata, compute GPCR/marker expression by paper cell type.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expression_parquet', required=True)
    p.add_argument('--metadata_parquet', required=True)
    p.add_argument('--gpcr_csv', required=True)
    p.add_argument('--cell_id_col', default='cell_id')
    p.add_argument('--cell_type_col', required=True)
    p.add_argument('--region_col', default=None)
    p.add_argument('--out_dir', required=True)
    p.add_argument('--min_cells', type=int, default=20)
    args=p.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    expr=pd.read_parquet(args.expression_parquet)
    meta=pd.read_parquet(args.metadata_parquet)
    gpcr=pd.read_csv(args.gpcr_csv)
    gpcr_col='mouse_gene_symbol' if 'mouse_gene_symbol' in gpcr.columns else gpcr.columns[0]
    genes=[g for g in gpcr[gpcr_col].dropna().astype(str).str.strip() if g in expr.columns]
    df=meta.merge(expr[[args.cell_id_col]+genes], on=args.cell_id_col, how='inner')
    group_cols=[args.cell_type_col]
    if args.region_col and args.region_col in df.columns:
        group_cols=[args.region_col, args.cell_type_col]
    rows=[]
    for keys, sub in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple): keys=(keys,)
        if len(sub) < args.min_cells: continue
        for g in genes:
            vals=sub[g].to_numpy()
            rows.append({**dict(zip(group_cols,keys)), 'gene':g, 'n_cells':len(sub), 'mean_expr':float(np.nanmean(vals)), 'pct_expr':float(np.mean(vals>0)*100)})
    res=pd.DataFrame(rows)
    if not res.empty:
        res['evidence_source']='Paper_dataset_computed'
    res.to_csv(out/'Paper_GPCR_Ranking.csv', index=False)
    print('[DONE] Paper_GPCR_Ranking.csv', res.shape)

if __name__ == '__main__':
    main()
