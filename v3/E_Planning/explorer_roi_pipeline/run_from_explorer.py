"""Explorer ROI → Story 1/4/5/6. Does not modify Xenium folders. Seed 0.

Input: a JSON config pointing at Explorer *_cells_stats.csv downloads or an
Explorer polygon-coordinate CSV from which cell IDs can be derived.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
import scanpy as sc
from scipy import sparse
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.neighbors import NearestNeighbors

SEED = 0
MIN_COUNTS = 20
MIN_GENES = 5
MIN_CELLS_PER_GENE = 3
N_PCS = 20
N_NEIGHBORS = 15
LEIDEN_RES = 1.0
AREA_IQR_K = 3.0
LOGFC_MIN = 0.5
PADJ_MAX = 0.05
FRAC_MIN = 0.25
DELTA_FRAC_MIN = 0.15
NHOOD_PERMUTATIONS = 499
MIN_NHOOD_GROUP = 20
HERE = Path(__file__).resolve().parent

# These genes report labeling or transient state.  They remain available for
# plots and differential expression, but cannot create the cell-identity
# clusters used to ask which cell type overlaps TRAP+ neurons.
STATE_REPORTER_GENES = {
    "tdtomato", "icre", "cre", "fos", "fosb", "fosl2", "arc", "egr1",
    "egr2", "egr3", "egr4", "junb", "npas4", "nr4a1", "nr4a2",
    "nr4a3", "dusp1", "dusp4", "dusp5", "btg2", "ier2", "per1",
    "per2", "bdnf", "ptgs2", "gadd45g",
}

MODULES = {
    "ORBm_layers": {
        "L2_3": ["Cux2", "Calb1"],
        "L4": ["Rorb", "Rspo1"],
        "L5": ["Fezf2", "Deptor"],
        "L6": ["Syt6", "Foxp2", "Tle4"],
        "L6b": ["Ccn2", "Cplx3"],
        "gabaergic": ["Gad1", "Gad2"],
        "astrocyte": ["Gfap", "Aqp4"],
        "oligo": ["Sox10", "Opalin", "Gjc3"],
        "OPC": ["Pdgfra", "Cspg4"],
        "endothelial": ["Cldn5", "Pecam1", "Kdr"],
        "VLMC": ["Dcn", "Col1a1"],
        "microglia": ["Trem2", "Cd68", "Siglech"],
    },
    "BMAp_classes": {
        "glutamatergic": ["Slc17a7", "Slc17a6"],
        "gabaergic": ["Gad1", "Gad2"],
        "astrocyte": ["Gfap", "Aqp4"],
        "oligo": ["Sox10", "Opalin", "Gjc3"],
        "OPC": ["Pdgfra", "Cspg4"],
        "endothelial": ["Cldn5", "Pecam1", "Kdr"],
        "VLMC": ["Dcn", "Col1a1"],
        "microglia": ["Trem2", "Cd68", "Siglech"],
        "striatal_like": ["Ppp1r1b", "Penk"],
    },
    "BLA_types": {
        "BLA_principal": [
            "Slc17a7", "Nrn1", "Bhlhe22", "Zfpm2", "Prdm8", "Pdzrn3",
            "Adamtsl1", "Nwd2", "Neurod6", "Rorb",
        ],
        "BLA_Pvalb_GABA": ["Gad1", "Gad2", "Pvalb", "Syt2", "Gucy1a1", "Igfbp6"],
        "BLA_Sst_GABA": ["Gad1", "Gad2", "Sst", "Chodl", "Grik3", "Necab1"],
        "BLA_Vip_Lamp5_GABA": ["Gad1", "Gad2", "Vip", "Lamp5", "Sncg", "Calb2", "Cplx3"],
        "astrocyte": ["Gfap", "Aqp4"],
        "oligo": ["Sox10", "Opalin", "Gjc3"],
        "OPC": ["Pdgfra", "Cspg4", "Gpr17"],
        "vascular": ["Cldn5", "Pecam1", "Kdr", "Dcn", "Col1a1"],
        "microglia": ["Trem2", "Cd68", "Siglech"],
    },
    "CEA_types": {
        "CEA_Gal_Avp_like": [
            "Rspo1", "Calb2", "Syt6", "Parm1", "Igfbp5", "Plch1", "Vwc2l",
            "Gfra2", "Nxph3", "Chrm2",
        ],
        "CEA_Six3_Cyp26b1_like": [
            "Arhgap6", "Penk", "Calb1", "Gm19410", "Strip2", "Kctd12",
            "Trpc4", "Pcsk5", "Sema3e",
        ],
        "CEA_Six3_Sp9_like": [
            "Foxp2", "Grik3", "Nts", "Sema5b", "Rnf152", "Ndst4", "Prox1",
        ],
        "CEA_Ebf1_Pdyn_like": ["Plcxd2", "Sst", "Unc13c", "Sema6a", "Cdh20"],
        "CEA_Rai14_Pdyn_Crh_like": [
            "Hs3st2", "Sntb1", "Pdyn", "Col6a1", "Htr1f", "Necab2",
            "Ppp1r1b", "Crh",
        ],
        "astrocyte": ["Gfap", "Aqp4"],
        "oligo": ["Sox10", "Opalin", "Gjc3"],
        "OPC": ["Pdgfra", "Cspg4", "Gpr17"],
        "vascular": ["Cldn5", "Pecam1", "Kdr", "Dcn", "Col1a1"],
        "microglia": ["Trem2", "Cd68", "Siglech"],
    },
}

DOTPLOT = {
    "ORBm_layers": [
        "Slc17a7", "Cux2", "Calb1", "Rorb", "Rspo1", "Deptor", "Fezf2",
        "Syt6", "Foxp2", "Tle4", "Ccn2", "Gad1", "Gad2", "Pvalb", "Sst",
        "Vip", "Lamp5", "Gfap", "Aqp4", "Sox10", "Pdgfra", "Cldn5", "Trem2",
    ],
    "BMAp_classes": [
        "Slc17a7", "Slc17a6", "Gad1", "Gad2", "Pvalb", "Sst", "Vip", "Lamp5",
        "Calb2", "Meis2", "Ppp1r1b", "Penk", "Nr2f2", "Cdh9", "Gfap", "Aqp4",
        "Sox10", "Opalin", "Pdgfra", "Cldn5", "Dcn", "Trem2",
    ],
    "BLA_types": [
        "Slc17a7", "Nrn1", "Bhlhe22", "Prdm8", "Pdzrn3", "Neurod6",
        "Gad1", "Gad2", "Pvalb", "Sst", "Vip", "Lamp5", "Gfap", "Sox10",
        "Pdgfra", "Cldn5", "Trem2",
    ],
    "CEA_types": [
        "Gad1", "Gad2", "Rspo1", "Calb2", "Arhgap6", "Penk", "Foxp2",
        "Nts", "Plcxd2", "Sst", "Hs3st2", "Pdyn", "Crh", "Gfap", "Sox10",
        "Pdgfra", "Cldn5", "Trem2",
    ],
}

SPATIAL_GENES = {
    "ORBm_layers": ["Cux2", "Rorb", "Fezf2", "Deptor", "Gad1", "Slc17a7"],
    "BMAp_classes": ["Slc17a7", "Gad1", "Nr2f2", "Cdh9", "Ppp1r1b", "Sox10"],
    "BLA_types": ["Slc17a7", "Pdzrn3", "Neurod6", "Gad1", "Pvalb", "Sst"],
    "CEA_types": ["Gad1", "Rspo1", "Arhgap6", "Foxp2", "Sst", "Pdyn"],
}

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 8,
    "figure.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})


def tukey_hi(x, k=AREA_IQR_K):
    q1, q3 = np.nanpercentile(x, [25, 75])
    return q3 + k * (q3 - q1)


def cat_sort(vals):
    def key(v):
        s = str(v).replace("Cluster ", "")
        try:
            return (0, int(s))
        except ValueError:
            return (1, str(v))
    return sorted(vals, key=key)


def palette_map(cats):
    colors = plt.colormaps["tab20"].colors
    ordered = cat_sort(cats)
    return {c: colors[i % 20] for i, c in enumerate(ordered)}


def savefig(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def resolve_under(xenium: Path, path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path
    return xenium / path


def read_explorer_cells(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, comment="#")
    df.columns = [c.strip() for c in df.columns]
    if "Cell ID" not in df.columns:
        raise ValueError(f"No Cell ID column in {path}: {list(df.columns)}")
    df["Cell ID"] = df["Cell ID"].astype(str)
    if df["Cell ID"].duplicated().any():
        raise ValueError(f"Duplicate Cell IDs in {path}")
    return df


def read_polygon_coordinates(path: Path, selection_name: str | None = None):
    """Read one Explorer polygon and reject ambiguous multi-selection files."""
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, comment="#")
    df.columns = [c.strip() for c in df.columns]
    selection_col = next((c for c in df.columns if c.lower() == "selection"), None)
    if selection_col:
        selections = df[selection_col].dropna().astype(str).unique().tolist()
        if selection_name:
            df = df[df[selection_col].astype(str) == str(selection_name)].copy()
            if df.empty:
                raise ValueError(f"Selection {selection_name!r} is absent from {path}")
        elif len(selections) > 1:
            raise ValueError(
                f"{path} contains multiple selections {selections}; set selection_name"
            )
    cols = {c.lower().strip(): c for c in df.columns}
    xcol = cols.get("x") or cols.get("x (µm)") or cols.get("x (um)")
    ycol = cols.get("y") or cols.get("y (µm)") or cols.get("y (um)")
    if xcol is None or ycol is None:
        raise ValueError(f"No X/Y columns in {path}: {list(df.columns)}")
    xy = df[[xcol, ycol]].astype(float).to_numpy()
    if len(xy) < 3:
        raise ValueError(f"Polygon in {path} has fewer than three vertices")
    return xy


def derive_explorer_cells_from_polygon(
    xenium: Path, coordinates_path: Path, selection_name: str | None = None
) -> pd.DataFrame:
    """Select cell centroids inside one polygon and attach XOA clusters."""
    polygon = read_polygon_coordinates(coordinates_path, selection_name)
    meta = pd.read_parquet(
        xenium / "cells.parquet",
        columns=["cell_id", "x_centroid", "y_centroid"],
    )
    points = meta[["x_centroid", "y_centroid"]].astype(float).to_numpy()
    inside = MplPath(polygon, closed=True).contains_points(points, radius=1e-9)
    selected = meta.loc[inside, ["cell_id"]].copy()
    if selected.empty:
        raise ValueError(f"No cell centroids fall inside {coordinates_path}")

    cluster_path = (
        xenium / "analysis" / "clustering" / "gene_expression_graphclust" / "clusters.csv"
    )
    clusters = pd.read_csv(cluster_path, dtype=str)
    clusters.columns = [c.strip() for c in clusters.columns]
    if not {"Barcode", "Cluster"}.issubset(clusters.columns):
        raise ValueError(f"Unexpected cluster schema in {cluster_path}")
    cluster_map = clusters.set_index("Barcode")["Cluster"]
    selected["Cell ID"] = selected.pop("cell_id").astype(str)
    selected["Cluster"] = selected["Cell ID"].map(cluster_map)
    missing_cluster = selected["Cluster"].isna()
    selected.loc[~missing_cluster, "Cluster"] = (
        "Cluster " + selected.loc[~missing_cluster, "Cluster"].astype(str)
    )
    selected.loc[missing_cluster, "Cluster"] = "Cluster unassigned"
    return selected


def load_xenium(xenium: Path):
    adata = sc.read_10x_h5(xenium / "cell_feature_matrix.h5", gex_only=False)
    adata.var_names_make_unique()
    adata.obs_names = adata.obs_names.astype(str)
    meta = pd.read_parquet(xenium / "cells.parquet")
    meta["cell_id"] = meta["cell_id"].astype(str)
    meta = meta.set_index("cell_id")
    missing = adata.obs_names.difference(meta.index)
    if len(missing):
        raise ValueError(f"{len(missing)} barcodes missing from cells.parquet")
    adata.obs = adata.obs.join(meta.loc[adata.obs_names])
    return adata


def module_scores(adata, modules):
    X = adata.X.toarray() if sparse.issparse(adata.X) else np.asarray(adata.X)
    names = list(adata.var_names)
    scores = {}
    for mod, genes in modules.items():
        idx = [names.index(g) for g in genes if g in names]
        if not idx:
            raise ValueError(f"No genes on panel for module {mod}: {genes}")
        scores[mod] = np.asarray(X[:, idx].mean(axis=1)).ravel()
    score_df = pd.DataFrame(scores, index=adata.obs_names)
    top = score_df.idxmax(axis=1)
    top_val = score_df.max(axis=1)
    second = score_df.apply(lambda r: r.nlargest(2).iloc[-1], axis=1)
    floor = score_df.median(axis=1)
    assigned = top.where(
        (top_val > floor) & (top_val >= 1.2 * second.clip(lower=1e-8)),
        "unassigned",
    )
    return score_df, assigned


def knn_indices(xy, k):
    """Return exactly k neighbors per cell, excluding the query cell itself."""
    if len(xy) < 2:
        raise ValueError("At least two cells are required for a neighborhood analysis")
    k_use = min(int(k), len(xy) - 1)
    nn = NearestNeighbors(n_neighbors=k_use + 1, algorithm="kd_tree").fit(xy)
    # Passing the query explicitly guarantees that self is column zero.
    return nn.kneighbors(xy, return_distance=False)[:, 1:]


def spatial_label_agreement(xy, labels, k=6, n_perm=199, seed=SEED):
    neigh = knn_indices(xy, k)
    lab = np.asarray(labels)
    obs = np.mean(lab[neigh] == lab[:, None])
    rng = np.random.default_rng(seed)
    perm_vals = []
    for _ in range(n_perm):
        shuf = rng.permutation(lab)
        perm_vals.append(np.mean(shuf[neigh] == shuf[:, None]))
    perm_vals = np.asarray(perm_vals)
    return float(obs), float(perm_vals.mean()), float(perm_vals.std())


def nhood_enrichment(xy, labels, k=8, n_perm=NHOOD_PERMUTATIONS, seed=SEED):
    """Directed kNN label enrichment under a global label-permutation null.

    This is a within-section spatial description.  Neighbor edges are not
    biological replicates, so the permutation p-values must not be reported as
    an animal-level treatment test.
    """
    neigh = knn_indices(xy, k)
    labs = np.asarray(labels).astype(str)
    types = cat_sort(np.unique(labs))
    idx = {t: i for i, t in enumerate(types)}
    li = np.array([idx[t] for t in labs])
    n = len(types)
    src = np.repeat(np.arange(len(li)), neigh.shape[1])
    dst = neigh.ravel()

    def pair_counts(encoded):
        pair = encoded[src] * n + encoded[dst]
        return np.bincount(pair, minlength=n * n).reshape(n, n).astype(float)

    obs = pair_counts(li)
    rng = np.random.default_rng(seed)
    null = np.zeros((n_perm, n, n), dtype=float)
    for p in range(n_perm):
        null[p] = pair_counts(rng.permutation(li))
    mu, sd = null.mean(axis=0), null.std(axis=0)
    z = (obs - mu) / np.where(sd < 1e-8, np.nan, sd)
    log2oe = np.log2((obs + 0.5) / (mu + 0.5))
    # Two-sided empirical p-value. Add one to avoid zero p-values.
    p_hi = (1 + (null >= obs).sum(axis=0)) / (n_perm + 1)
    p_lo = (1 + (null <= obs).sum(axis=0)) / (n_perm + 1)
    p_two = np.minimum(1.0, 2 * np.minimum(p_hi, p_lo))
    return types, z, log2oe, p_two, obs, mu


def run_leiden(adata, res, key):
    try:
        sc.tl.leiden(adata, resolution=res, random_state=SEED, flavor="igraph", key_added=key)
    except (ImportError, ModuleNotFoundError):
        sc.tl.leiden(adata, resolution=res, random_state=SEED, flavor="leidenalg", key_added=key)


def scatter_cats(ax, x, y, cats, cmap, s=10, title="", xlabel="", ylabel="", invert=True):
    cats = pd.Series(cats).astype(str)
    for cat in cat_sort(cats.unique()):
        m = cats == cat
        ax.scatter(x[m], y[m], s=s, c=[cmap[cat]], label=str(cat), linewidths=0, rasterized=True)
    ax.set_aspect("equal")
    if invert:
        ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def polygon_from_coords_csv(path: Path, selection_name: str | None = None):
    if not path or not Path(path).exists():
        return None
    xy = read_polygon_coordinates(Path(path), selection_name)
    x, y = xy[:, 0], xy[:, 1]
    if len(x) >= 2 and (x[0] != x[-1] or y[0] != y[-1]):
        x = np.r_[x, x[0]]
        y = np.r_[y, y[0]]
    return x, y


def load_reference_labels(cfg, cell_ids):
    """Load optional Allen/reference-transfer labels by cell ID."""
    ref_path = cfg.get("reference_labels_csv")
    if not ref_path:
        return None
    ref_path = Path(ref_path)
    if not ref_path.exists():
        raise FileNotFoundError(f"reference_labels_csv does not exist: {ref_path}")
    ref = pd.read_csv(ref_path)
    id_col = cfg.get("reference_id_column", "cell_id")
    if id_col not in ref.columns:
        unnamed = [c for c in ref.columns if str(c).startswith("Unnamed:")]
        if unnamed:
            id_col = unnamed[0]
        else:
            raise ValueError(f"No cell-ID column in {ref_path}")
    label_col = cfg.get("reference_label_column", "seurat_coarse")
    if label_col not in ref.columns:
        raise ValueError(f"No {label_col!r} column in {ref_path}")
    ref[id_col] = ref[id_col].astype(str)
    if ref[id_col].duplicated().any():
        raise ValueError(f"Duplicate cell IDs in {ref_path}")
    labels = ref.set_index(id_col)[label_col].reindex(pd.Index(cell_ids).astype(str))
    return labels.astype("string")


def read_biology_gene_sets(workbook: Path, available_genes):
    """Read panel blocks and return compact GPCR, state/plasticity, and TF sets."""
    if not workbook.exists():
        return {}
    tab = pd.read_excel(workbook, sheet_name="SHARED_PANEL_ORDER")
    tab = tab.dropna(subset=["gene", "block"]).copy()
    tab["gene"] = tab["gene"].astype(str)
    tab["block"] = tab["block"].astype(str).str.lower()
    available = set(map(str, available_genes))
    rules = {
        "GPCR": r"gpcr|receptor_map|cholinergic",
        "Activity / plasticity": r"activity|ieg|plasticity|morphine|circadian",
        "TF": r"tf_identity",
    }
    out = {}
    for label, pattern in rules.items():
        genes = tab.loc[tab["block"].str.contains(pattern, regex=True), "gene"]
        out[label] = [g for g in dict.fromkeys(genes) if g in available]
    return {k: v for k, v in out.items() if v}


def cluster_annotation_table(obs):
    counts = pd.crosstab(obs["leiden"], obs["module"])
    prop = counts.div(counts.sum(axis=1), axis=0)
    rows = []
    for cl in counts.index:
        winner = prop.loc[cl].idxmax()
        rows.append({
            "leiden": str(cl),
            "n_cells": int(counts.loc[cl].sum()),
            "majority_module": str(winner),
            "module_purity": float(prop.loc[cl, winner]),
            "mixed": bool(prop.loc[cl, winner] < 0.5 or winner == "unassigned"),
        })
    return pd.DataFrame(rows)


def process_roi(cfg: dict, out_root: Path) -> dict:
    roi = cfg["roi_name"]
    xenium = Path(cfg["xenium"])
    out = out_root / roi
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    module_set = cfg["module_set"]
    modules = MODULES[module_set]

    explorer_cells_path = resolve_under(xenium, cfg.get("explorer_cells_csv"))
    if explorer_cells_path:
        explorer = read_explorer_cells(explorer_cells_path)
        roi_cell_source = "explorer_cells_stats"
    else:
        coordinates_path = resolve_under(xenium, cfg.get("explorer_coordinates_csv"))
        if coordinates_path is None:
            raise ValueError(
                f"{roi}: provide explorer_cells_csv or explorer_coordinates_csv"
            )
        explorer = derive_explorer_cells_from_polygon(
            xenium, coordinates_path, cfg.get("selection_name")
        )
        roi_cell_source = "polygon_centroids_plus_xoa_clusters"
        explorer.to_csv(out / f"{roi}_derived_cells.csv", index=False)
    roi_ids = explorer["Cell ID"].tolist()
    adata_all = load_xenium(xenium)
    n_region = adata_all.n_obs
    missing_ids = [i for i in roi_ids if i not in adata_all.obs_names]
    if missing_ids:
        raise ValueError(f"{roi}: {len(missing_ids)} Explorer Cell IDs not in matrix")

    adata = adata_all[roi_ids].copy()
    adata.obs["onboard_cluster"] = (
        explorer.set_index("Cell ID").loc[adata.obs_names, "Cluster"].astype(str)
    )
    gene_mask = adata.var["feature_types"].astype(str) == "Gene Expression"
    genes_on_panel = list(adata.var_names[gene_mask])
    has_tdtom = any(g.lower() == "tdtomato" for g in genes_on_panel)

    adata.obs["n_counts_gene"] = np.asarray(adata[:, gene_mask].X.sum(axis=1)).ravel()
    adata.obs["n_genes"] = np.asarray((adata[:, gene_mask].X > 0).sum(axis=1)).ravel()
    region_counts = adata_all.obs["transcript_counts"].astype(float)
    roi_counts = adata.obs["transcript_counts"].astype(float)
    area_cut = tukey_hi(adata.obs["cell_area"].to_numpy())
    keep = (
        (adata.obs["n_counts_gene"] >= MIN_COUNTS)
        & (adata.obs["n_genes"] >= MIN_GENES)
        & (adata.obs["cell_area"] <= area_cut)
    )
    n_pre = adata.n_obs
    n_drop_counts = int((adata.obs["n_counts_gene"] < MIN_COUNTS).sum())
    n_drop_genes = int((adata.obs["n_genes"] < MIN_GENES).sum())
    n_drop_area = int((adata.obs["cell_area"] > area_cut).sum())
    adata.obs["pass_qc"] = keep.astype(bool)
    adata_raw = adata.copy()
    adata = adata[keep].copy()
    adata = adata[:, gene_mask].copy()
    sc.pp.filter_genes(adata, min_cells=MIN_CELLS_PER_GENE)
    adata.layers["counts"] = adata.X.copy()
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    score_df, assigned = module_scores(adata, modules)
    for col in score_df.columns:
        adata.obs[f"score_{col}"] = score_df[col].to_numpy()
    adata.obs["module"] = assigned.astype(str)

    reference_labels = load_reference_labels(cfg, adata.obs_names)
    if reference_labels is not None:
        adata.obs["reference_label"] = reference_labels.to_numpy()

    adata.raw = adata
    if sparse.issparse(adata.X):
        adata.X = adata.X.toarray()
    sc.pp.scale(adata, max_value=10)
    identity_mask = np.array([
        str(g).lower() not in STATE_REPORTER_GENES for g in adata.var_names
    ])
    if identity_mask.sum() < 10:
        raise ValueError(f"{roi}: fewer than 10 identity genes remain after state/reporter exclusion")
    adata.var["used_for_identity_clustering"] = identity_mask
    # Keep state/reporter genes in adata.raw and counts, but remove their
    # contribution to PCA so tdTom/Fos-like signals cannot define cell types.
    adata.X[:, ~identity_mask] = 0.0
    n_pcs = min(N_PCS, adata.n_obs - 2, int(identity_mask.sum()) - 1)
    sc.tl.pca(adata, n_comps=n_pcs, svd_solver="arpack", random_state=SEED)
    sc.pp.neighbors(adata, n_neighbors=N_NEIGHBORS, n_pcs=n_pcs, random_state=SEED)
    sc.tl.umap(adata, random_state=SEED)
    run_leiden(adata, LEIDEN_RES, "leiden")
    run_leiden(adata, 0.5, "leiden_0.5")
    run_leiden(adata, 1.5, "leiden_1.5")
    sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon", use_raw=True)

    Xraw = adata.raw.X
    present = (Xraw > 0)
    gene_index = {g: i for i, g in enumerate(adata.raw.var_names)}
    de_rows = []
    marker_rows = []
    for cl in adata.obs["leiden"].cat.categories:
        df = sc.get.rank_genes_groups_df(adata, group=cl)
        df.insert(0, "cluster", cl)
        in_cl = (adata.obs["leiden"] == cl).to_numpy()
        idxs = [gene_index[g] for g in df["names"]]
        if sparse.issparse(present):
            frac = np.asarray(present[in_cl][:, idxs].mean(axis=0)).ravel()
            frac_out = np.asarray(present[~in_cl][:, idxs].mean(axis=0)).ravel()
        else:
            frac = np.asarray(present[in_cl][:, idxs].mean(axis=0)).ravel()
            frac_out = np.asarray(present[~in_cl][:, idxs].mean(axis=0)).ravel()
        df["pct_in_cluster"] = frac
        df["pct_out_cluster"] = frac_out
        df["delta_pct"] = frac - frac_out
        de_rows.append(df.head(15))
        hit = df[
            (df["pvals_adj"] < PADJ_MAX)
            & (df["logfoldchanges"] > LOGFC_MIN)
            & (df["pct_in_cluster"] > FRAC_MIN)
            & (df["delta_pct"] > DELTA_FRAC_MIN)
        ].copy()
        marker_rows.append(hit.head(8))
    de = pd.concat(de_rows, ignore_index=True)
    markers = pd.concat(marker_rows, ignore_index=True) if marker_rows else de.head(0)

    majority = pd.crosstab(adata.obs["leiden"], adata.obs["module"]).idxmax(axis=1)
    purity = pd.crosstab(adata.obs["leiden"], adata.obs["module"], normalize="index").max(axis=1)
    adata.obs["group"] = [
        f"{cl}_{majority[cl]}" if purity[cl] >= 0.5 else f"{cl}_mixed"
        for cl in adata.obs["leiden"]
    ]
    nmi_mod = normalized_mutual_info_score(adata.obs["leiden"], adata.obs["module"])
    ari_onboard = adjusted_rand_score(adata.obs["leiden"], adata.obs["onboard_cluster"])
    nmi_onboard = normalized_mutual_info_score(adata.obs["leiden"], adata.obs["onboard_cluster"])
    ari_res_low = adjusted_rand_score(adata.obs["leiden"], adata.obs["leiden_0.5"])
    ari_res_high = adjusted_rand_score(adata.obs["leiden"], adata.obs["leiden_1.5"])
    ref_ari = ref_nmi = None
    if "reference_label" in adata.obs:
        valid_ref = adata.obs["reference_label"].notna()
        if valid_ref.sum() >= 20:
            ref_ari = adjusted_rand_score(
                adata.obs.loc[valid_ref, "leiden"], adata.obs.loc[valid_ref, "reference_label"]
            )
            ref_nmi = normalized_mutual_info_score(
                adata.obs.loc[valid_ref, "leiden"], adata.obs.loc[valid_ref, "reference_label"]
            )
    xy = adata.obs[["x_centroid", "y_centroid"]].to_numpy()
    spat_obs, spat_perm, spat_sd = spatial_label_agreement(xy, adata.obs["leiden"].to_numpy())
    types, zmat, log2oe, nhood_p, nhood_obs, nhood_exp = nhood_enrichment(
        xy, adata.obs["module"].to_numpy()
    )
    annotation = cluster_annotation_table(adata.obs)

    # ---- figures ----
    coordinates_path = resolve_under(xenium, cfg.get("explorer_coordinates_csv"))
    poly = (
        polygon_from_coords_csv(coordinates_path, cfg.get("selection_name"))
        if coordinates_path else None
    )
    obs = adata.obs
    cmap_l = palette_map(obs["leiden"].astype(str).unique())
    cmap_m = palette_map(obs["module"].astype(str).unique())
    cmap_o = palette_map(obs["onboard_cluster"].astype(str).unique())

    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.8))
    axes[0].hist(np.log1p(region_counts), bins=40, density=True, alpha=0.5,
                 color="#8a8a8a", label=f"full section (n={n_region})")
    axes[0].hist(np.log1p(roi_counts), bins=30, density=True, alpha=0.75,
                 color="#2c5aa0", label=f"Explorer ROI (n={n_pre})")
    axes[0].set_title(f"{roi}: transcripts / cell before QC")
    axes[0].set_xlabel("log1p(transcript_counts)")
    axes[0].set_ylabel("Density")
    axes[0].legend(frameon=False)
    axes[1].hist(adata_raw.obs["n_counts_gene"], bins=40, color="#2c5aa0")
    axes[1].axvline(MIN_COUNTS, color="0.15", ls="--", lw=1.2, label=f"min {MIN_COUNTS}")
    axes[1].set_title("Gene-feature counts in ROI")
    axes[1].set_xlabel("Gene transcripts / cell")
    axes[1].set_ylabel("Cells")
    axes[1].legend(frameon=False)
    axes[2].hist(adata_raw.obs["cell_area"], bins=40, color="#2c5aa0")
    axes[2].axvline(area_cut, color="0.15", ls="--", lw=1.2, label=f"Tukey high {area_cut:.0f} µm²")
    axes[2].set_title("Cell area in ROI")
    axes[2].set_xlabel("Cell area (µm²)")
    axes[2].set_ylabel("Cells")
    axes[2].legend(frameon=False)
    savefig(fig, figdir / "01_qc.png")

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 16.2), sharex=True, sharey=True)
    scatter_cats(axes[0], obs["x_centroid"], obs["y_centroid"], obs["leiden"], cmap_l,
                 title=f"{roi} Leiden (res=1.0, n={adata.n_obs})",
                 xlabel="x centroid (µm)", ylabel="y centroid (µm)")
    axes[0].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False,
                   markerscale=1.6, title="Leiden", fontsize=8)
    scatter_cats(axes[1], obs["x_centroid"], obs["y_centroid"], obs["module"], cmap_m,
                 title="Marker-module baseline (same expression matrix)",
                 xlabel="x centroid (µm)", ylabel="y centroid (µm)")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False,
                   markerscale=1.6, title="Module", fontsize=8)
    scatter_cats(axes[2], obs["x_centroid"], obs["y_centroid"], obs["onboard_cluster"], cmap_o,
                 title="Explorer onboard graphclust",
                 xlabel="x centroid (µm)", ylabel="y centroid (µm)")
    axes[2].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False,
                   markerscale=1.6, title="Onboard", fontsize=7)
    if poly is not None:
        for ax in axes:
            ax.plot(poly[0], poly[1], color="0.15", lw=0.8, alpha=0.8)
    fig.tight_layout()
    savefig(fig, figdir / "02_spatial_labels.png")

    um = adata.obsm["X_umap"]
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6))
    for cat in cat_sort(obs["leiden"].astype(str).unique()):
        m = obs["leiden"].astype(str) == cat
        axes[0].scatter(um[m.values, 0], um[m.values, 1], s=11, c=[cmap_l[cat]],
                        label=cat, linewidths=0)
    axes[0].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, title="Leiden", fontsize=7)
    axes[0].set_title("UMAP by Leiden")
    axes[0].set_xlabel("UMAP-1")
    axes[0].set_ylabel("UMAP-2")
    for cat in cat_sort(obs["module"].astype(str).unique()):
        m = obs["module"].astype(str) == cat
        axes[1].scatter(um[m.values, 0], um[m.values, 1], s=11, c=[cmap_m[cat]],
                        label=cat, linewidths=0)
    axes[1].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, title="Module", fontsize=7)
    axes[1].set_title("UMAP by marker module (not used to cluster)")
    axes[1].set_xlabel("UMAP-1")
    axes[1].set_ylabel("UMAP-2")
    fig.tight_layout()
    savefig(fig, figdir / "03_umap.png")

    genes_use = [g for g in DOTPLOT[module_set] if g in adata.var_names]
    dp = sc.pl.dotplot(
        adata, genes_use, groupby="leiden", standard_scale="var", use_raw=True,
        colorbar_title="Mean expression\n(scaled per gene)",
        size_title="Fraction of cells",
        title=f"{roi}: curated marker expression by Leiden cluster",
        show=False, return_fig=True,
    )
    dp.savefig(figdir / "04_dotplot_markers.png", dpi=200, bbox_inches="tight")
    plt.close("all")

    # z-scored mean of top filtered markers
    if len(markers):
        top_genes = []
        for cl, sub in markers.groupby("cluster", sort=False):
            for g in sub["names"].head(3):
                if g not in top_genes:
                    top_genes.append(g)
        Xlog = adata.raw.X
        if sparse.issparse(Xlog):
            Xlog = Xlog.toarray()
        gidx = [list(adata.raw.var_names).index(g) for g in top_genes]
        means = []
        clusters = list(adata.obs["leiden"].cat.categories)
        for cl in clusters:
            m = (adata.obs["leiden"] == cl).to_numpy()
            means.append(Xlog[m][:, gidx].mean(axis=0))
        mean_df = pd.DataFrame(means, index=clusters, columns=top_genes)
        z = mean_df.apply(lambda col: (col - col.mean()) / (col.std() if col.std() > 1e-8 else 1.0), axis=0)
        fig, ax = plt.subplots(figsize=(max(7.5, 0.42 * len(top_genes) + 2.8), max(4.2, 0.32 * len(clusters) + 2)))
        im = ax.imshow(z.to_numpy(), aspect="auto", cmap="RdBu_r", vmin=-2.2, vmax=2.2)
        ax.set_xticks(range(len(top_genes)), top_genes, rotation=90, fontsize=8)
        ax.set_yticks(range(len(clusters)), [f"{c}  {majority[c]}" for c in clusters], fontsize=8)
        fig.colorbar(im, ax=ax, label="Z-score of cluster-mean log-normalized expression")
        ax.set_title(
            f"{roi}: specific markers (adj.p<{PADJ_MAX}, logFC>{LOGFC_MIN}, "
            f"frac>{FRAC_MIN}, Δfrac>{DELTA_FRAC_MIN})"
        )
        ax.set_xlabel("Gene")
        ax.set_ylabel("Leiden cluster (majority module)")
        savefig(fig, figdir / "05_zscore_heatmap.png")
    else:
        z = None

    sgenes = [g for g in SPATIAL_GENES[module_set] if g in adata.raw.var_names]
    fig, axes = plt.subplots(2, 3, figsize=(12.6, 8.0), sharex=True, sharey=True)
    Xcounts = adata.layers["counts"].toarray() if sparse.issparse(adata.layers["counts"]) else np.asarray(adata.layers["counts"])
    names = list(adata.raw.var_names)
    for ax, g in zip(axes.ravel(), sgenes):
        val = Xcounts[:, names.index(g)]
        positive = val[val > 0]
        vmax = np.percentile(positive, 99) if len(positive) else 1
        ax.scatter(obs["x_centroid"], obs["y_centroid"], c="#d9d9d9", s=7,
                   linewidths=0, rasterized=True)
        pos = val > 0
        sca = ax.scatter(obs.loc[pos, "x_centroid"], obs.loc[pos, "y_centroid"],
                         c=val[pos], s=9, cmap="magma", vmin=1,
                         vmax=max(vmax, 1), linewidths=0, rasterized=True)
        ax.set_aspect("equal")
        ax.set_title(g)
        fig.colorbar(sca, ax=ax, fraction=0.046, pad=0.04, label="transcripts / cell")
        if poly is not None:
            ax.plot(poly[0], poly[1], color="0.85", lw=0.8, alpha=0.9)
    if sgenes:
        axes.ravel()[0].invert_yaxis()
    for ax in axes.ravel()[len(sgenes):]:
        ax.axis("off")
    fig.suptitle(
        f"{roi}: spatial expression (gray = 0; color capped at positive-cell 99th percentile)",
        y=1.01,
    )
    fig.supxlabel("x centroid (µm)")
    fig.supylabel("y centroid (µm)")
    fig.tight_layout()
    savefig(fig, figdir / "06_spatial_marker_genes.png")

    xtab = pd.crosstab(obs["leiden"], obs["module"])
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    im = ax.imshow(xtab.to_numpy(), aspect="auto", cmap="Blues")
    ax.set_xticks(range(xtab.shape[1]), xtab.columns, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(xtab.shape[0]), xtab.index, fontsize=8)
    for i in range(xtab.shape[0]):
        for j in range(xtab.shape[1]):
            ax.text(j, i, str(xtab.iloc[i, j]), ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="Cells")
    ax.set_title(f"{roi}: Leiden vs marker-module baseline (counts)")
    ax.set_xlabel("Marker module")
    ax.set_ylabel("Leiden cluster")
    savefig(fig, figdir / "07_composition_counts.png")

    type_counts = pd.Series(adata.obs["module"].astype(str)).value_counts()
    keep_types = [
        i for i, t in enumerate(types)
        if t != "unassigned" and type_counts.get(t, 0) >= MIN_NHOOD_GROUP
    ]
    shown_types = [types[i] for i in keep_types]
    shown_oe = log2oe[np.ix_(keep_types, keep_types)]
    lim = max(0.5, float(np.nanpercentile(np.abs(shown_oe), 98))) if shown_oe.size else 1.0
    fig, ax = plt.subplots(
        figsize=(max(6.2, 0.62 * len(shown_types) + 2), max(5.2, 0.55 * len(shown_types) + 2))
    )
    im = ax.imshow(shown_oe, cmap="RdBu_r", vmin=-lim, vmax=lim)
    ax.set_xticks(range(len(shown_types)), shown_types, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(shown_types)), shown_types, fontsize=8)
    fig.colorbar(im, ax=ax, label="log2(observed / permuted expected)")
    ax.set_title(f"{roi}: within-section neighbors (k=8; n≥{MIN_NHOOD_GROUP}/group)")
    ax.set_xlabel("Neighbor module")
    ax.set_ylabel("Index cell module")
    savefig(fig, figdir / "08_neighborhood_z.png")

    # rank-gene table figure
    show = markers.groupby("cluster", sort=False).head(3) if len(markers) else de.groupby("cluster").head(2)
    fig, ax = plt.subplots(figsize=(10.2, max(3.5, 0.28 * len(show) + 1.6)))
    ax.axis("off")
    col_labels = ["cluster", "gene", "logFC", "adj. p", "frac in", "frac out", "Δ fraction"]
    cell = []
    for _, r in show.iterrows():
        cell.append([
            str(r["cluster"]),
            str(r["names"]),
            f"{r['logfoldchanges']:.2f}",
            f"{r['pvals_adj']:.1e}",
            f"{r['pct_in_cluster']:.2f}",
            f"{r['pct_out_cluster']:.2f}",
            f"{r['delta_pct']:.2f}",
        ])
    table = ax.table(cellText=cell, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.25)
    ax.set_title(
        f"{roi}: top cluster-specific genes after filters "
        f"(adj.p<{PADJ_MAX}, logFC>{LOGFC_MIN}, frac>{FRAC_MIN}, Δfrac>{DELTA_FRAC_MIN})",
        pad=16,
    )
    savefig(fig, figdir / "09_top_markers_table.png")

    # One compact figure for PI-facing review: where the types are, how common
    # they are, and which Leiden labels are uncertain.
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.8))
    scatter_cats(
        axes[0], obs["x_centroid"], obs["y_centroid"], obs["module"], cmap_m,
        s=9, title="Where are the broad cell classes?", xlabel="x (µm)", ylabel="y (µm)",
    )
    axes[0].legend(
        loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False,
        markerscale=1.5, fontsize=7,
    )
    comp = obs["module"].astype(str).value_counts(normalize=True).sort_values()
    comp_colors = [cmap_m.get(x, "#bdbdbd") for x in comp.index]
    axes[1].barh(comp.index, 100 * comp.values, color=comp_colors)
    axes[1].set_xlabel("Cells in ROI (%)")
    axes[1].set_title("Cell-class composition")
    axes[1].grid(axis="x", color="0.9", lw=0.8)
    ann_plot = annotation.sort_values("leiden", key=lambda s: s.map(lambda x: int(x)))
    ann_colors = [cmap_m.get(x, "#bdbdbd") for x in ann_plot["majority_module"]]
    axes[2].scatter(
        ann_plot["module_purity"], ann_plot["leiden"],
        s=np.clip(ann_plot["n_cells"], 20, 180), c=ann_colors,
        edgecolor="0.25", linewidth=0.5,
    )
    axes[2].axvline(0.5, color="0.3", ls="--", lw=1)
    axes[2].set_xlim(0, 1.03)
    axes[2].set_xlabel("Fraction in majority marker class")
    axes[2].set_ylabel("Leiden cluster")
    axes[2].set_title("Annotation confidence\n(dot size = cells)")
    axes[2].grid(axis="x", color="0.9", lw=0.8)
    fig.suptitle(f"{roi}: cell-identity overview", fontweight="bold")
    fig.tight_layout()
    savefig(fig, figdir / "10_cell_identity_overview.png")

    panel_workbook = Path(cfg.get(
        "panel_workbook", HERE.parent / "FINAL_Xenium_panel_ORBm_BMAp_298genes_FINAL.xlsx"
    ))
    biology_sets = read_biology_gene_sets(panel_workbook, adata.raw.var_names)
    biology_rows = []
    if biology_sets:
        raw_counts = adata.layers["counts"]
        if sparse.issparse(raw_counts):
            raw_counts = raw_counts.toarray()
        raw_counts = np.asarray(raw_counts)
        modules_show = [
            m for m, n in obs["module"].astype(str).value_counts().items()
            if m != "unassigned" and n >= 10
        ]
        genes_plot, boundaries = [], []
        for category, genes in biology_sets.items():
            # Keep at most six genes per category, prioritized by detection in this ROI.
            ranked = sorted(
                genes,
                key=lambda g: float((raw_counts[:, names.index(g)] > 0).mean()),
                reverse=True,
            )[:6]
            genes_plot.extend(ranked)
            boundaries.append((category, len(genes_plot)))
        if genes_plot and modules_show:
            frac_mat = np.zeros((len(modules_show), len(genes_plot)))
            mean_mat = np.zeros_like(frac_mat)
            for i, mod in enumerate(modules_show):
                m = (obs["module"].astype(str) == mod).to_numpy()
                for j, gene in enumerate(genes_plot):
                    vals = raw_counts[m, names.index(gene)]
                    frac_mat[i, j] = 100 * np.mean(vals > 0)
                    mean_mat[i, j] = np.mean(vals)
                    biology_rows.append({
                        "module": mod, "category": next(
                            c for c, end in boundaries if j < end
                        ), "gene": gene, "pct_detected": frac_mat[i, j],
                        "mean_transcripts": mean_mat[i, j],
                    })
            fig, ax = plt.subplots(figsize=(max(10, 0.65 * len(genes_plot) + 3), max(4.8, 0.48 * len(modules_show) + 2)))
            xx, yy = np.meshgrid(np.arange(len(genes_plot)), np.arange(len(modules_show)))
            sca = ax.scatter(
                xx.ravel(), yy.ravel(), s=8 + 1.7 * frac_mat.ravel(),
                c=np.log1p(mean_mat.ravel()), cmap="viridis", edgecolor="0.25", linewidth=0.25,
            )
            ax.set_xticks(range(len(genes_plot)), genes_plot, rotation=45, ha="right")
            ax.set_yticks(range(len(modules_show)), modules_show)
            start = 0
            for category, end in boundaries:
                ax.text(
                    (start + end - 1) / 2, 1.02, category,
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontweight="bold",
                )
                if end < len(genes_plot):
                    ax.axvline(end - 0.5, color="0.8", lw=1)
                start = end
            fig.colorbar(sca, ax=ax, label="log1p(mean transcripts / cell)")
            for pct in (25, 50, 75):
                ax.scatter([], [], s=8 + 1.7 * pct, c="0.65", edgecolor="0.25", label=f"{pct}%")
            ax.legend(title="Detected cells", bbox_to_anchor=(1.17, 0.02), loc="lower left", frameon=False)
            ax.set_title(
                f"{roi}: GPCR, state/plasticity, and TF expression by broad cell class",
                y=1.14, fontweight="bold",
            )
            ax.set_xlabel("Highest-detection genes available in this pilot ROI")
            ax.set_ylabel("Marker-defined cell class")
            ax.grid(color="0.92", lw=0.6)
            fig.tight_layout()
            savefig(fig, figdir / "11_gpcr_state_tf_overview.png")

    fail_ids = adata_raw.obs_names[~adata_raw.obs["pass_qc"]].astype(str)
    explorer_out = pd.concat([
        pd.DataFrame({"cell_id": adata.obs_names.astype(str), "group": adata.obs["group"].astype(str)}),
        pd.DataFrame({"cell_id": fail_ids, "group": "qc_fail"}),
    ], ignore_index=True)
    explorer_out.to_csv(out / "cell_groups.csv", index=False)
    de.to_csv(out / "leiden_rank_genes.csv", index=False)
    markers.to_csv(out / "cluster_specific_genes_filtered.csv", index=False)
    xtab.to_csv(out / "leiden_vs_module_counts.csv")
    annotation.to_csv(out / "cluster_annotation_summary.csv", index=False)
    if biology_rows:
        pd.DataFrame(biology_rows).to_csv(out / "biology_gene_set_summary.csv", index=False)
    obs.to_csv(out / "cells_annotated.csv")
    pd.DataFrame(zmat, index=types, columns=types).to_csv(out / "neighborhood_z_modules.csv")
    pd.DataFrame(log2oe, index=types, columns=types).to_csv(out / "neighborhood_log2oe_modules.csv")
    pd.DataFrame(nhood_p, index=types, columns=types).to_csv(out / "neighborhood_permutation_p_modules.csv")

    summary = {
        "roi_name": roi,
        "anatomy": cfg["anatomy"],
        "animal_id": cfg.get("animal_id"),
        "xenium": str(xenium),
        "explorer_cells_csv": cfg.get("explorer_cells_csv"),
        "roi_cell_source": roi_cell_source,
        "panel_n_gene_features_in_roi_matrix": int(gene_mask.sum()) if hasattr(gene_mask, "sum") else int(np.sum(gene_mask)),
        "tdTomato_on_panel": bool(has_tdtom),
        "n_region_cells": int(n_region),
        "n_roi_export": int(len(roi_ids)),
        "expected_explorer_cell_count": cfg.get("expected_explorer_cell_count"),
        "polygon_count_difference": (
            int(len(roi_ids) - cfg["expected_explorer_cell_count"])
            if cfg.get("expected_explorer_cell_count") is not None else None
        ),
        "n_polygon_cells_without_xoa_cluster": int(
            (explorer["Cluster"] == "Cluster unassigned").sum()
        ),
        "n_after_qc": int(adata.n_obs),
        "qc": {
            "min_gene_counts": MIN_COUNTS,
            "min_genes": MIN_GENES,
            "area_tukey_k": AREA_IQR_K,
            "area_cut_um2": float(area_cut),
            "n_drop_counts": n_drop_counts,
            "n_drop_genes": n_drop_genes,
            "n_drop_area": n_drop_area,
        },
        "baseline_transcripts": {
            "region_median": float(np.median(region_counts)),
            "roi_median": float(np.median(roi_counts)),
            "roi_after_qc_median_gene_counts": float(np.median(adata.obs["n_counts_gene"])),
        },
        "clustering": {
            "n_pcs": int(n_pcs),
            "leiden_n": int(obs["leiden"].nunique()),
            "leiden_0.5_n": int(obs["leiden_0.5"].nunique()),
            "leiden_1.5_n": int(obs["leiden_1.5"].nunique()),
            "n_identity_genes_used": int(identity_mask.sum()),
            "n_state_reporter_genes_excluded": int((~identity_mask).sum()),
            "ari_res1_vs_res0.5": float(ari_res_low),
            "ari_res1_vs_res1.5": float(ari_res_high),
        },
        "same_matrix_concordance": {
            "nmi_leiden_vs_module": float(nmi_mod),
            "ari_leiden_vs_onboard": float(ari_onboard),
            "nmi_leiden_vs_onboard": float(nmi_onboard),
        },
        "reference_validation": {
            "reference_label_column": cfg.get("reference_label_column") if reference_labels is not None else None,
            "n_reference_labeled": int(adata.obs["reference_label"].notna().sum()) if reference_labels is not None else 0,
            "ari_leiden_vs_reference": float(ref_ari) if ref_ari is not None else None,
            "nmi_leiden_vs_reference": float(ref_nmi) if ref_nmi is not None else None,
        },
        "spatial_description": {
            "spatial_neighbor_same_leiden": spat_obs,
            "spatial_neighbor_same_leiden_perm_mean": spat_perm,
            "spatial_neighbor_same_leiden_perm_sd": spat_sd,
            "neighborhood_permutations": NHOOD_PERMUTATIONS,
            "note": "Within-section descriptive analysis; neighbor edges are not biological replicates.",
        },
        "n_filtered_cluster_specific_rows": int(len(markers)),
        "module_counts": {k: int(v) for k, v in obs["module"].value_counts().items()},
        "stories_runnable": {
            "S1_celltype_genes": True,
            "S2_tdtom": bool(has_tdtom),
            "S3_mouse_ab": False,
            "S4_neighborhood": True,
            "S5_composition": True,
            "S6_roi_qc": True,
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    adata.write_h5ad(out / f"{roi}_processed.h5ad")
    print(json.dumps({"roi": roi, "n_after_qc": adata.n_obs, "n_leiden": int(obs["leiden"].nunique())}))
    return summary


def write_story_skips(out_root: Path, summaries: list[dict], genes_union: list[str]):
    s2 = out_root / "story2_tdtom"
    s3 = out_root / "story3_mouse_ab"
    s2.mkdir(parents=True, exist_ok=True)
    s3.mkdir(parents=True, exist_ok=True)
    tdtom = any(s["tdTomato_on_panel"] for s in summaries)
    anatomies = {s["anatomy"] for s in summaries}
    animals = {s.get("animal_id") for s in summaries}

    if tdtom:
        (s2 / "STATUS.md").write_text("tdTomato present — run DE per class; see PIPELINE_LATER_REAL_DATA.md\n", encoding="utf-8")
    else:
        text = (
            "# Story 2 SKIPPED — tdTom+ vs tdTom−\n\n"
            "tdTomato is not among gene features on the current Explorer-linked matrices.\n\n"
            f"ROIs checked: {', '.join(s['roi_name'] for s in summaries)}\n\n"
            "Do not gate on DAPI. Wait for the reporter-aware production run. See PIPELINE_LATER_REAL_DATA.md.\n"
        )
        (s2 / "SKIPPED.md").write_text(text, encoding="utf-8")
        fig, ax = plt.subplots(figsize=(8.4, 4.2))
        ax.axis("off")
        ax.text(0.02, 0.75, "Story 2 not runnable on current data", fontsize=16, fontweight="bold", transform=ax.transAxes)
        ax.text(0.02, 0.48, "Need: tdTomato in cell_feature_matrix.h5 after a custom-panel run.",
                fontsize=11, transform=ax.transAxes)
        ax.text(0.02, 0.28, "Current panel: mBrain v1.1 247 genes, DAPI morphology only.",
                fontsize=11, transform=ax.transAxes)
        ax.text(0.02, 0.10, "Explorer ROI exports are ready to reuse; only the matrix changes.",
                fontsize=11, transform=ax.transAxes)
        savefig(fig, s2 / "SKIPPED_story2.png")

    same_anatomy_two_animals = len(anatomies) == 1 and len(animals) >= 2
    if same_anatomy_two_animals:
        (s3 / "STATUS.md").write_text("Two animals, same anatomy — run pseudobulk. See PIPELINE_LATER_REAL_DATA.md\n", encoding="utf-8")
    else:
        lines = [
            "# Story 3 SKIPPED — mouse A vs mouse B",
            "",
            "Need two animals with the **same** anatomy field.",
            "",
            "Current Explorer ROIs:",
        ]
        for s in summaries:
            lines.append(f"- {s['roi_name']}: anatomy={s['anatomy']}, animal_id={s.get('animal_id')}")
        lines += [
            "",
            "These slides are different regions (ORBm vs BMAp), not biological replicates.",
            "Do not test cells as independent replicates. See PIPELINE_LATER_REAL_DATA.md.",
        ]
        (s3 / "SKIPPED.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        fig, ax = plt.subplots(figsize=(8.8, 4.4))
        ax.axis("off")
        ax.text(0.02, 0.78, "Story 3 not runnable on current data", fontsize=16, fontweight="bold", transform=ax.transAxes)
        ax.text(0.02, 0.52, "Current pair: ORBm (slide 0063814) and BMAp (slide 0063817).",
                fontsize=11, transform=ax.transAxes)
        ax.text(0.02, 0.34, "That is two Story 1 jobs, not mouse A vs mouse B.",
                fontsize=11, transform=ax.transAxes)
        ax.text(0.02, 0.16, "Later: same anatomy, animal_id A and B, then pseudobulk (animal × type).",
                fontsize=11, transform=ax.transAxes)
        savefig(fig, s3 / "SKIPPED_story3.png")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(HERE / "rois_current.json"))
    p.add_argument("--output-root", default=str(HERE / "outputs"))
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out_root = Path(args.output_root)
    out_root.mkdir(parents=True, exist_ok=True)
    sc.settings.verbosity = 1
    np.random.seed(SEED)
    summaries = [process_roi(roi, out_root) for roi in cfg["rois"]]
    write_story_skips(out_root, summaries, [])
    (out_root / "run_summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print("DONE", out_root)


if __name__ == "__main__":
    main()
