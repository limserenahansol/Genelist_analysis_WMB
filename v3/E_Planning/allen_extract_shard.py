"""Extract a candidate-gene x cell matrix for one Allen WMB-10X shard.

Why this exists: the panel design scored detectability for only ~271 genes, leaving
68 of the 245 Option C candidates unscored. The raw Allen matrices are cached
locally (97 GB), so the gap is computable. This pulls the columns we care about for
the 226,886 cells in the two target ROIs, so both the detectability question and
the sub-population benchmark can run off a small cached matrix instead of the
full 32,285-gene shards.

Design notes
  - X is backed CSR (cells x genes), so ROW slicing is cheap and COLUMN slicing is
    not. We therefore read row chunks for the target cells and subset genes in
    memory, rather than asking for gene columns from the backed object.
  - The matrices are already log2(CPM+1) per the ABC Atlas release, so "detected"
    means value > 0; no renormalisation is applied.
  - var is indexed by Ensembl ID with a gene_symbol column, so symbols are mapped
    through var.gene_symbol. Symbols that are absent or duplicated are reported
    rather than silently dropped.

Usage: python allen_extract_shard.py <shard_label> <out.npz>
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
ROIS = ["PL-ILA-ORB", "sAMY"]
CHUNK = 8000

SHARD_PATH = {
    "WMB-10Xv2-Isocortex-1": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-1-log2.h5ad",
    "WMB-10Xv2-Isocortex-2": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-2-log2.h5ad",
    "WMB-10Xv2-Isocortex-3": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-3-log2.h5ad",
    "WMB-10Xv2-Isocortex-4": "WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-4-log2.h5ad",
    "WMB-10Xv3-Isocortex-1": "WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-1-log2.h5ad",
    "WMB-10Xv3-Isocortex-2": "WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-2-log2.h5ad",
    "WMB-10Xv3-STR": "WMB-10Xv3/20230630/WMB-10Xv3-STR-log2.h5ad",
}


def candidate_genes() -> list[str]:
    """Union of every gene in any panel option, plus the Xenium base panel."""
    genes = set(pd.read_csv(OUT / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    for f in ("PANEL_A_current_166genes_119custom.xlsx",
              "PANEL_B_cut_147genes_100custom.xlsx",
              "PANEL_C_expanded_standalone_245genes.xlsx"):
        genes |= set(pd.read_excel(OUT / f, "SHARED_PANEL_ORDER").gene.astype(str))
    # Transgene probes are not mouse genes and cannot be in the atlas.
    return sorted(genes - {"tdTomato", "iCre", "WPRE", "mCherry"})


def main() -> None:
    shard, out = sys.argv[1], Path(sys.argv[2])
    path = CACHE / "expression_matrices" / SHARD_PATH[shard]

    md = pd.read_csv(META, usecols=["cell_label", "feature_matrix_label",
                                    "region_of_interest_acronym", "subclass",
                                    "supertype", "cluster", "class"])
    md = md[(md.feature_matrix_label == shard) & (md.region_of_interest_acronym.isin(ROIS))]
    print(f"{shard}: {len(md):,} target cells", flush=True)
    if not len(md):
        raise SystemExit(f"no target cells in {shard}")

    A = ad.read_h5ad(path, backed="r")
    want = candidate_genes()
    sym = A.var.gene_symbol.astype(str)
    # symbol -> first matching Ensembl row position; report ambiguity rather than hide it
    pos = {}
    dup = []
    for i, s in enumerate(sym.values):
        if s in pos:
            dup.append(s)
        else:
            pos[s] = i
    found = [g for g in want if g in pos]
    missing = [g for g in want if g not in pos]
    cols = np.array([pos[g] for g in found], dtype=np.int64)
    print(f"  genes: {len(found)} found, {len(missing)} absent from the atlas", flush=True)
    if missing:
        print(f"  absent: {', '.join(missing[:20])}{' ...' if len(missing) > 20 else ''}", flush=True)
    dup_wanted = sorted(set(dup) & set(found))
    if dup_wanted:
        print(f"  NOTE duplicate symbols in var (first occurrence used): {', '.join(dup_wanted)}", flush=True)

    obs_pos = pd.Series(np.arange(A.n_obs), index=A.obs.index.astype(str))
    rows = obs_pos.reindex(md.cell_label.astype(str)).dropna().astype(np.int64)
    kept = md.set_index("cell_label").loc[rows.index]
    order = np.argsort(rows.values)          # backed CSR needs ascending row access
    rows_sorted = rows.values[order]
    kept = kept.iloc[order]
    print(f"  matched {len(rows_sorted):,} of {len(md):,} cells in the matrix", flush=True)

    mat = np.zeros((len(rows_sorted), len(cols)), dtype=np.float32)
    for s in range(0, len(rows_sorted), CHUNK):
        idx = rows_sorted[s:s + CHUNK]
        block = A[idx, :].to_memory().X
        mat[s:s + len(idx), :] = np.asarray(
            block[:, cols].todense() if hasattr(block, "todense") else block[:, cols],
            dtype=np.float32)
        print(f"  rows {s + len(idx):,}/{len(rows_sorted):,}", flush=True)

    np.savez_compressed(
        out, X=mat, genes=np.array(found, dtype=object),
        cell=kept.index.to_numpy(dtype=object),
        roi=kept.region_of_interest_acronym.to_numpy(dtype=object),
        subclass=kept.subclass.to_numpy(dtype=object),
        supertype=kept.supertype.to_numpy(dtype=object),
        cluster=kept.cluster.to_numpy(dtype=object),
        cls=kept["class"].to_numpy(dtype=object))
    nz = float((mat > 0).mean())
    print(f"  saved {out.name}: {mat.shape[0]:,} cells x {mat.shape[1]} genes, "
          f"{nz*100:.1f}% nonzero", flush=True)


if __name__ == "__main__":
    main()
