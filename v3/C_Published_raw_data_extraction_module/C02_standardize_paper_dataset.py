#!/usr/bin/env python
"""
C02_standardize_paper_dataset.py

Module C: Published raw-data extraction module.
Purpose:
- Convert a paper dataset into a standard format:
  1) expression matrix: cells x genes
  2) metadata: cells x annotations

Supported template inputs:
- CSV expression matrix
- CSV metadata

For h5ad/rds/mtx formats, add per-paper adapters.
"""
from pathlib import Path
import argparse
import pandas as pd


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expression_csv', required=True)
    p.add_argument('--metadata_csv', required=True)
    p.add_argument('--cell_id_col', default='cell_id')
    p.add_argument('--out_dir', required=True)
    args=p.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    expr=pd.read_csv(args.expression_csv)
    meta=pd.read_csv(args.metadata_csv)
    if args.cell_id_col not in expr.columns or args.cell_id_col not in meta.columns:
        raise ValueError('cell_id_col must exist in both expression and metadata CSV files.')
    common=sorted(set(expr[args.cell_id_col]).intersection(set(meta[args.cell_id_col])))
    expr=expr[expr[args.cell_id_col].isin(common)]
    meta=meta[meta[args.cell_id_col].isin(common)]
    expr.to_parquet(out/'Paper_Expression_Standardized.parquet', index=False)
    meta.to_parquet(out/'Paper_Metadata_Standardized.parquet', index=False)
    pd.DataFrame({'n_common_cells':[len(common)], 'n_genes':[expr.shape[1]-1]}).to_csv(out/'Paper_Standardization_Summary.csv', index=False)
    print('[DONE] standardized paper dataset')

if __name__ == '__main__':
    main()
