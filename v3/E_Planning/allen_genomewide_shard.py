"""Genome-wide per-group expression statistics for one Allen shard, by streaming reduction.

Why this exists: the panel was selected from a 701-gene candidate pool, and the Allen
marker screen behind it evaluated only 311 of the atlas's 32,285 genes - 0.96% of the
transcriptome. So "245 genes is the final answer" cannot be asserted: genes outside
that shortlist were never looked at. With the matrices cached locally, all 32,285 can
be screened.

This never materialises a 226,886 x 32,285 matrix. It streams row chunks and
accumulates, per group, the number of cells with a nonzero value and the summed
expression. Memory stays at n_groups x n_genes.

Groups are computed at three taxonomy levels so both the known 20 populations and
the finer sub-populations can be scored:
  subclass   the level the 20 anchors live at
  supertype  125 sub-populations nested inside the anchors
  cluster    506 finer sub-populations

Usage: python allen_genomewide_shard.py <shard_label> <out.npz>
"""
from __future__ import annotations

import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

CACHE = Path(r"C:\Users\hsollim\Downloads\abc_atlas_cache")
META = CACHE / "metadata" / "WMB-10X" / "20231215" / "views" / "cell_metadata_with_cluster_annotation.csv"
ROIS = ["PL-ILA-ORB", "sAMY"]
CHUNK = 6000
LEVELS = ["subclass", "supertype", "cluster"]

SHARD_PATH = {
    "WMB-10Xv2-Isocortex-1": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-1-log2.h5ad",
    "WMB-10Xv2-Isocortex-2": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-2-log2.h5ad",
    "WMB-10Xv2-Isocortex-3": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-3-log2.h5ad",
    "WMB-10Xv2-Isocortex-4": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-4-log2.h5ad",
    "WMB-10Xv3-Isocortex-1": "WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-1-log2.h5ad",
    "WMB-10Xv3-Isocortex-2": "WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-2-log2.h5ad",
    "WMB-10Xv3-STR": "WMB-10Xv3/20230630/WMB-10Xv3-STR-log2.h5ad",
}


def main() -> None:
    shard, out = sys.argv[1], Path(sys.argv[2])
    path = CACHE / "expression_matrices" / SHARD_PATH[shard]

    md = pd.read_csv(META, usecols=["cell_label", "feature_matrix_label",
                                    "region_of_interest_acronym", "subclass",
                                    "supertype", "cluster"])
    md = md[(md.feature_matrix_label == shard) & (md.region_of_interest_acronym.isin(ROIS))]
    print(f"{shard}: {len(md):,} target cells", flush=True)

    A = ad.read_h5ad(path, backed="r")
    obs_pos = pd.Series(np.arange(A.n_obs), index=A.obs.index.astype(str))
    rows = obs_pos.reindex(md.cell_label.astype(str)).dropna().astype(np.int64)
    kept = md.set_index("cell_label").loc[rows.index]
    order = np.argsort(rows.values)
    rows_sorted, kept = rows.values[order], kept.iloc[order]
    print(f"  matched {len(rows_sorted):,} cells; {A.n_vars:,} genes", flush=True)

    # group codes per level, keyed on the labels actually present in this shard
    codes, labels = {}, {}
    for lv in LEVELS:
        cat = pd.Categorical(kept[lv].astype(str))
        codes[lv] = cat.codes.astype(np.int64)
        labels[lv] = np.array(cat.categories, dtype=object)
        print(f"  {lv}: {len(labels[lv])} groups", flush=True)

    nnz = {lv: np.zeros((len(labels[lv]), A.n_vars), dtype=np.float64) for lv in LEVELS}
    tot = {lv: np.zeros((len(labels[lv]), A.n_vars), dtype=np.float64) for lv in LEVELS}
    ncell = {lv: np.zeros(len(labels[lv]), dtype=np.int64) for lv in LEVELS}

    for s in range(0, len(rows_sorted), CHUNK):
        idx = rows_sorted[s:s + CHUNK]
        block = A[idx, :].to_memory().X
        if not sp.issparse(block):
            block = sp.csr_matrix(block)
        block = block.tocsr()
        binv = block.copy()
        binv.data = np.ones_like(binv.data)        # detected = nonzero
        for lv in LEVELS:
            c = codes[lv][s:s + len(idx)]
            S = sp.csr_matrix(
                (np.ones(len(c)), (c, np.arange(len(c)))),
                shape=(len(labels[lv]), len(c)))
            nnz[lv] += np.asarray((S @ binv).todense(), dtype=np.float64)
            tot[lv] += np.asarray((S @ block).todense(), dtype=np.float64)
            ncell[lv] += np.bincount(c, minlength=len(labels[lv]))
        print(f"  rows {s + len(idx):,}/{len(rows_sorted):,}", flush=True)

    payload = {"genes": np.array(A.var.gene_symbol.astype(str).values, dtype=object),
               "ensembl": np.array(A.var.index.astype(str).values, dtype=object),
               "shard": np.array([shard], dtype=object)}
    for lv in LEVELS:
        payload[f"{lv}_labels"] = labels[lv]
        payload[f"{lv}_nnz"] = nnz[lv].astype(np.float32)
        payload[f"{lv}_sum"] = tot[lv].astype(np.float32)
        payload[f"{lv}_n"] = ncell[lv]
    np.savez_compressed(out, **payload)
    print(f"  saved {out.name}: {A.n_vars:,} genes x "
          f"{{{', '.join(f'{lv} {len(labels[lv])}' for lv in LEVELS)}}} groups", flush=True)


if __name__ == "__main__":
    main()
