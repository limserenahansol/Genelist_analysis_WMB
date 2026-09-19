"""Extract per-cell values for Jesse morphine DEGs DE in 3 of the 12 ORBm anchors.

Originally for the 301-panel 'Allen supertype discovery' genes.

46 of them were never extracted, so the claim that they help split an anchor into
sub-populations (SOW aim 1: find cell types overlapping TRAP+ neurons) had never
been measured. Same layout as allen_extract_gap so shards concatenate column-wise.
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
DST = OUT / "allen_extract_add20"
ROIS = ["PL-ILA-ORB", "sAMY"]
CHUNK = 6000

SHARD_PATH = {
    "WMB-10Xv2-Isocortex-1": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-1-log2.h5ad",
    "WMB-10Xv2-Isocortex-2": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-2-log2.h5ad",
    "WMB-10Xv2-Isocortex-3": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-3-log2.h5ad",
    "WMB-10Xv2-Isocortex-4": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-4-log2.h5ad",
    "WMB-10Xv3-Isocortex-1": "WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-1-log2.h5ad",
    "WMB-10Xv3-Isocortex-2": "WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-2-log2.h5ad",
    "WMB-10Xv3-STR": "WMB-10Xv3/20230630/WMB-10Xv3-STR-log2.h5ad",
}


def wanted_genes() -> list[str]:
    return [x for x in (OUT / "_add20_need.txt").read_text().split()]
    want = set(pd.read_excel(
        Path(r"C:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx"),
        "SHARED_PANEL_ORDER").gene.astype(str))
    have = set()
    for d in ("allen_extract", "allen_extract_gap"):
        f = sorted((OUT / d).glob("*.npz"))
        if f:
            have |= {str(x) for x in np.load(f[0], allow_pickle=True)["genes"]}
    return sorted(want - have - {"tdTomato", "iCre"})


def main() -> None:
    shard = sys.argv[1]
    DST.mkdir(exist_ok=True)
    out = DST / f"{shard}.npz"
    if out.exists():
        print(f"{shard}: exists, skip", flush=True)
        return
    genes = wanted_genes()
    path = CACHE / "expression_matrices" / SHARD_PATH[shard]

    md = pd.read_csv(META, usecols=["cell_label", "feature_matrix_label",
                                    "region_of_interest_acronym", "subclass",
                                    "supertype", "cluster"])
    md = md[(md.feature_matrix_label == shard) & (md.region_of_interest_acronym.isin(ROIS))]
    A = ad.read_h5ad(path, backed="r")
    sym = A.var.gene_symbol.astype(str).values
    pos = {}
    for i, s in enumerate(sym):
        pos.setdefault(s, i)
    cols = np.array([pos[g] for g in genes if g in pos], dtype=np.int64)
    got = [g for g in genes if g in pos]
    print(f"{shard}: {len(md):,} cells, {len(got)}/{len(genes)} genes found", flush=True)

    obs_pos = pd.Series(np.arange(A.n_obs), index=A.obs.index.astype(str))
    rows = obs_pos.reindex(md.cell_label.astype(str)).dropna().astype(np.int64)
    kept = md.set_index("cell_label").loc[rows.index]
    order = np.argsort(rows.values)
    rows_sorted, kept = rows.values[order], kept.iloc[order]

    mat = np.zeros((len(rows_sorted), len(cols)), dtype=np.float32)
    for s in range(0, len(rows_sorted), CHUNK):
        idx = rows_sorted[s:s + CHUNK]
        block = A[idx, :].to_memory().X
        mat[s:s + len(idx), :] = np.asarray(
            block[:, cols].todense() if hasattr(block, "todense") else block[:, cols],
            dtype=np.float32)
    np.savez_compressed(
        out, X=mat, genes=np.array(got, dtype=object),
        cell=np.array(kept.index.astype(str).values, dtype=object),
        roi=np.array(kept.region_of_interest_acronym.astype(str).values, dtype=object),
        subclass=np.array(kept.subclass.astype(str).values, dtype=object),
        supertype=np.array(kept.supertype.astype(str).values, dtype=object),
        cluster=np.array(kept.cluster.astype(str).values, dtype=object))
    print(f"  saved {out.name}: {mat.shape}", flush=True)


if __name__ == "__main__":
    main()
