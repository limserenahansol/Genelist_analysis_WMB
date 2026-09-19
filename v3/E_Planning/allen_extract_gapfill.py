"""Extract per-cell values for the panel genes missing from outputs/allen_extract.

The 443-gene extraction predates v7, so 64 of v7's genes have no per-cell data. A
per-cell matrix is needed for the only test that directly answers the project's
question: given Xenium-like measurements of panel genes ONLY, can a classifier
recover the Allen subclass label of a held-out neuron? That is exactly "can I name
the cell type of a tdTomato+ cell", and it cannot be answered from per-subclass
aggregates.

Writes outputs/allen_extract_gap/<shard>.npz with the same layout as the original
extraction so the two can be concatenated column-wise per shard.
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
DST = OUT / "allen_extract_gap"
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
    base = set(pd.read_csv(OUT / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    want = set(base)
    for fn in ("PANEL_FINAL_v6_ORBm_BMAp_complete.xlsx",
               "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
               "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx"):
        want |= set(pd.read_excel(OUT / fn, "SHARED_PANEL_ORDER").gene.astype(str))
    # candidate pool that a goal-aligned rebuild might reach for
    want |= {
        "Cx3cr1", "P2ry12", "Csf1r", "Hexb", "Siglech", "Trem2", "Laptm5", "Cd53",
        "Acsbg1", "Ntsr2", "Gjc3", "Sox10", "Gpr17", "Opalin", "Cldn5", "Ly6a",
        "Col1a1", "Aldh1a2", "Pln", "Acta2", "Rgs5", "Vtn", "Pdgfrb",
        "Clock", "Npas2", "Arntl", "Cry1", "Cry2", "Per3", "Nr1d1", "Nr1d2", "Dbp", "Bhlhe41",
        "Xist", "Eif2s3y", "Ddx3y", "Uty", "Kdm5d",
        "Slc30a3", "Zbtb20", "Sulf1", "Lhx9", "Esr1", "Adcyap1", "Ddc", "St8sia2",
        "Chat", "Slc5a7", "Adra2a", "Htr1a", "Grm2", "Galr1", "Adrb2",
        "Ntrk3", "Lrrtm2", "Nrxn3", "Arhgap32", "Cdh8", "Pcdh8", "Pak1",
        "Syndig1l", "Rxfp1", "Gabre", "Tspan18", "Abca8a", "Mgp", "S1pr3",
        "Sfrp1", "Ntsr1", "Sp8", "Calb1", "Calb2", "Pvalb", "Sst", "Vip", "Lamp5",
        "Slc17a7", "Slc17a6", "Slc32a1", "Gad1", "Gad2", "Snap25", "Rbfox3",
    }
    have = set()
    ex = sorted((OUT / "allen_extract").glob("*.npz"))
    if ex:
        have = {str(x) for x in np.load(ex[0], allow_pickle=True)["genes"]}
    return sorted(want - have)


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
    print(f"{shard}: {len(md):,} target cells, {len(got)}/{len(genes)} genes found", flush=True)

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
        print(f"  {shard} rows {s + len(idx):,}/{len(rows_sorted):,}", flush=True)

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
