"""Extract per-cell values for the six genes that separate the 291- and 297-gene lists.

Needed because the held-out benchmark returned an IDENTICAL 0.9177 for both lists - not
because they perform the same, but because Tnnc1, Blnk, Chn2, Frem3, Man2a1 and Adam19
were absent from the 514-gene per-cell extraction, so both sets scored on the same 266
measured genes. Without these six there is no way to test whether 297 actually beats 291.

Writes outputs/allen_extract_six/<shard>.npz, cell order matched to allen_extract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd

CACHE = Path(r"C:\Users\hsollim\Downloads\abc_atlas_cache")
META = CACHE / "metadata" / "WMB-10X" / "20231215" / "views" / "cell_metadata_with_cluster_annotation.csv"
V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DST = OUT / "allen_extract_six"
ROIS = ["PL-ILA-ORB", "sAMY"]
CHUNK = 6000
GENES = ["Tnnc1", "Blnk", "Chn2", "Frem3", "Man2a1", "Adam19"]

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
    shard = sys.argv[1]
    DST.mkdir(exist_ok=True)
    out = DST / f"{shard}.npz"
    if out.exists():
        print(f"{shard}: exists, skip", flush=True)
        return

    md = pd.read_csv(META, usecols=["cell_label", "feature_matrix_label",
                                    "region_of_interest_acronym"])
    md = md[(md.feature_matrix_label == shard) & (md.region_of_interest_acronym.isin(ROIS))]
    A = ad.read_h5ad(CACHE / "expression_matrices" / SHARD_PATH[shard], backed="r")
    sym = A.var.gene_symbol.astype(str).values
    pos = {}
    for i, s in enumerate(sym):
        pos.setdefault(s, i)
    got = [g for g in GENES if g in pos]
    cols = np.array([pos[g] for g in got], dtype=np.int64)
    print(f"{shard}: {len(md):,} cells, genes found {got}", flush=True)

    obs_pos = pd.Series(np.arange(A.n_obs), index=A.obs.index.astype(str))
    rows = obs_pos.reindex(md.cell_label.astype(str)).dropna().astype(np.int64)
    labels = rows.index.to_numpy()
    order = np.argsort(rows.values)
    rows_sorted, labels = rows.values[order], labels[order]

    mat = np.zeros((len(rows_sorted), len(cols)), dtype=np.float32)
    for s in range(0, len(rows_sorted), CHUNK):
        idx = rows_sorted[s:s + CHUNK]
        block = A[idx, :].to_memory().X
        mat[s:s + len(idx), :] = np.asarray(
            block[:, cols].todense() if hasattr(block, "todense") else block[:, cols],
            dtype=np.float32)
    np.savez_compressed(out, X=mat, genes=np.array(got, dtype=object),
                        cell=np.array(labels.astype(str), dtype=object))
    print(f"  saved {out.name}: {mat.shape}", flush=True)


if __name__ == "__main__":
    main()
