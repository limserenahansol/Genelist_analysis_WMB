#!/usr/bin/env python
"""
D03_make_removed_or_downgraded_table.py

Module D: Final integration module.
Purpose:
- Create a conservative table of genes/candidates that should be downgraded or removed.
"""
from pathlib import Path
import argparse
import pandas as pd


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--computed_gpcr_csv', required=True)
    p.add_argument('--out_csv', required=True)
    args=p.parse_args()
    df=pd.read_csv(args.computed_gpcr_csv)
    if 'validation_status' not in df.columns:
        df['validation_status']='candidate_to_review'
    flags=df[df['validation_status'].isin(['downgrade_low_expression','too_few_cells','downgrade_low_specificity','remove_wrong_region_or_celltype'])].copy()
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    flags.to_csv(args.out_csv, index=False)
    print('[DONE]', args.out_csv, flags.shape)

if __name__ == '__main__':
    main()
