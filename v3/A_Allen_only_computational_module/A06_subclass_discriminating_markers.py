#!/usr/bin/env python
"""
A06_subclass_discriminating_markers.py

Module A: Per-SUBCLASS discriminating markers + GPCR specificity tiering.

PROBLEM this fixes
------------------
curated_marker_template.csv defines markers per *cell_type_label*, but each
cell type maps to 2-3 Allen subclass anchors. So all anchors under one cell
type inherited an identical marker list, and nothing separated e.g.

    012 MEA Slc17a7 Glut        vs   113 MEA-COA-BMA Ccdc42 Glut
    120 MEA Otp Foxp2 Glut      vs   121 MEA-BST Otp Zic2 Glut
    005 L5 IT CTX Glut          vs   022 L5 ET CTX Glut  vs  032 L5 NP CTX Glut

Allen subclass NAMES already embed the discriminating gene (Ccdc42, Foxp2,
Zic2, Skor1, ...). This module verifies those against expression and finds
additional discriminating genes from the data.

METHOD
------
1. Build a candidate gene panel:
     a. gene-like tokens auto-parsed out of every Allen subclass name present
        in the target ROIs (this is where Ccdc42 / Zic2 / Skor1 come from),
     b. curated markers already in curated_marker_template.csv,
     c. a canonical panel (cortical layer/class + amygdala/striatal markers).
2. Pull log2 expression for that panel, for cells in the target ROIs only.
3. Per (region, subclass) compute mean_log2_expr and pct_expr per gene.
4. Two specificity flavours, because they answer different questions:

     specificity_log2_vs_panel     mean - max(mean over the OTHER *anchor*
                                   subclasses of the same region)
         -> "does this gene separate cell type 1 from cell type 2 and 3?"
            This is the probe-design question and is the PRIMARY criterion.

     specificity_log2_vs_neuronal  mean - max(mean over all other *neuronal*
                                   subclasses captured in the dissection ROI)
         -> "is this gene also clean against everything else the dissection
            picked up?" Secondary / informational.

   The distinction matters. Foxp2 is 9.27 (99% of cells) in 120 MEA Otp Foxp2
   Glut vs 0.38 (7.5%) in 012 MEA Slc17a7 Glut, so it is an excellent panel
   separator - but the sAMY dissection also contains striatal D1/D2 SPNs which
   are Foxp2-high, so vs_neuronal alone would wrongly discard it.

5. A gene is called discriminating for a subclass when
        specificity_log2_vs_panel >= min_specificity
    AND pct_expr >= min_pct
    AND mean_log2_expr >= min_mean
   Genes named inside the Allen subclass label get a ranking bonus so Allen's
   own chosen marker (Ccdc42, Foxp2, Zic2, Skor1, ...) surfaces first.

6. Each passing gene is labelled:
        UNIQUE_to_subclass  - passes for exactly 1 anchor in the region
        shared_within_cell_type - passes for >1 anchor of the same cell_type_label
        shared_across_cell_types - passes for anchors of different cell types
   The UNIQUE set is what actually separates cell type 1 / 2 / 3.

GPCR TIERING (second output)
----------------------------
Re-reads Allen_GPCR_Ranking_subclass.csv and labels each GPCR twice:

  panel tier (primary)  based on the fraction of *anchor* subclasses in which
                        the GPCR is detected:
                          cell_type_specific / intermediate / universal
  ROI tier (secondary)  same, over all neuronal subclasses in the dissection.

"cell_type_specific" GPCRs are usable to *identify* a cell type. "universal"
GPCRs (Grm5, Gabbr1/2, Cnr1, Oprm1, ...) are still legitimate drug targets but
carry no cell-type information, so they must be paired with a cell-type marker.

OUTPUTS
-------
  Subclass_Discriminating_Markers_long.csv   every (region, subclass, gene)
  Subclass_Discriminating_Markers_top.csv    top N discriminating per anchor
  Subclass_Marker_Panel_perAnchor.csv        one row per anchor, ready for D02
  GPCR_Specificity_Tiers.csv                 per (region, gene) universal vs specific
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_config, open_abc_cache, write_run_log  # noqa: E402

# Non-neuronal subclass name fragments (Allen "NN" class)
NONNEURONAL_PAT = re.compile(
    r"\b(Astro|Oligo|OPC|Microglia|Endo|SMC|Peri|VLMC|BAM|Ependymal|Tanycyte|CHOR|ABC|Monocyte|DC|Lymphoid)\b",
    re.IGNORECASE,
)

# Tokens in Allen subclass names that are region acronyms / class suffixes, not genes.
NAME_TOKEN_STOPLIST = {
    "Glut", "Gaba", "Chol", "Dopa", "Glyc", "Sero", "Nora", "Hist", "NN",
    "IT", "ET", "NP", "CT", "CTX", "L2", "L3", "L4", "L5", "L6", "L6b",
    "CR", "MSN", "SPN", "chandelier", "out", "in", "ant", "post", "med", "lat",
}


def _detect_gene_symbol_col(gene: pd.DataFrame) -> str:
    for c in ("gene_symbol", "symbol", "gene_name", "name"):
        if c in gene.columns:
            return c
    return gene.columns[0]


def is_nonneuronal(subclass: str) -> bool:
    return bool(NONNEURONAL_PAT.search(str(subclass)))


def parse_gene_tokens_from_subclass_names(subclasses: list[str]) -> set[str]:
    """Extract gene-symbol-looking tokens from Allen subclass names.

    Allen names look like '113 MEA-COA-BMA Ccdc42 Glut'. Gene symbols are
    Capitalised-then-lowercase tokens (Ccdc42, Foxp2, Zic2, Skor1, Pvalb);
    region acronyms are ALL-CAPS (MEA, COA, BMA, CTX) so they drop out.
    """
    out: set[str] = set()
    for name in subclasses:
        # strip leading numeric id
        body = re.sub(r"^\s*\d+\s+", "", str(name))
        for tok in re.split(r"[\s\-/]+", body):
            tok = tok.strip()
            if not tok or tok in NAME_TOKEN_STOPLIST:
                continue
            # Gene-symbol shape: starts uppercase, contains at least one lowercase
            if re.fullmatch(r"[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9\-]*", tok):
                out.add(tok)
    return out


CANONICAL_PANEL = [
    # pan-neuronal / neurotransmitter
    "Snap25", "Syt1", "Rbfox3", "Slc17a7", "Slc17a6", "Slc17a8",
    "Gad1", "Gad2", "Slc32a1", "Slc6a1",
    # cortical excitatory layer identity
    "Satb2", "Cux1", "Cux2", "Rorb", "Calb1", "Cdh13", "Fst", "Otof",
    # Lratd2 is the current symbol for the L5 ET marker formerly called Fam84b;
    # Ccn2 likewise replaces Ctgf. The old aliases are absent from Allen metadata.
    "Bcl11b", "Fezf2", "Etv1", "Crym", "Deptor", "Pde1c", "Lratd2",
    "Npnt", "Slco2a1", "Vat1l", "Chrna6", "Batf3", "Scnn1a", "Whrn",
    "Tshz2", "Hsd11b1", "Trhr", "Nxph1", "Foxp2", "Tle4", "Ntsr1",
    "Syt6", "Rprm", "Osr1", "Ccn2", "Cplx3", "Nxph4", "Moxd1",
    "Zfp804b", "Sulf1", "Oprk1", "Car3", "Tbr1", "Sla",
    # cortical inhibitory
    "Sst", "Pvalb", "Vip", "Lamp5", "Sncg", "Cck", "Npy", "Reln",
    "Adarb2", "Htr3a", "Chodl", "Nos1", "Chrna2", "Myh8", "Lhx6", "Th",
    # amygdala / BMAp / pallial
    "Slc30a3", "Tcf4", "Meis2", "Calb2", "Dcn", "Mpped1", "Tac1", "Cd36",
    "Gpr101", "Baiap3", "Trh", "Krt9", "Matn2", "Cartpt", "Otp", "Zic2",
    "Skor1", "Ccdc42", "Barhl2", "Nfib", "Nr2e1", "Sim1", "Fezf1",
    "St8sia2", "Ptpru", "C1ql2", "Sema5a", "Grem1",
    # striatal-like / sAMY inhibitory
    "Ppp1r1b", "Foxp1", "Penk", "Pax6", "Gpr88", "Tshz1", "Sox6", "Sp9",
    "Ebf1", "Pdyn", "Six3", "Cyp26b1", "Chst9", "Prkcd", "Isl1", "Lhx8",
    "Nnat", "Crh", "Gal", "Avp", "Nts", "Tac2", "Prox1", "Nrgn", "Ndnf",
    "Prdm12", "Zfhx3", "Rai14", "Mgp", "Slc22a3", "Bnc2", "Drd1", "Drd2",
    "Adora2a", "Gnb3",
]


def _get_gene_data_with_retry(cache, all_cells, gene, genes, data_type, chunk_size, retries=8, sleep=20):
    from abc_atlas_access.abc_atlas_cache.anndata_utils import get_gene_data

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            expr = get_gene_data(
                abc_atlas_cache=cache,
                all_cells=all_cells,
                all_genes=gene,
                selected_genes=genes,
                data_type=data_type,
                chunk_size=chunk_size,
            )
            gc.collect()
            return expr
        except PermissionError as e:
            last_err = e
            gc.collect()
            print(f"[WARN] PermissionError attempt {attempt}/{retries}: {e}; sleep {sleep}s")
            time.sleep(sleep)
    raise last_err  # type: ignore[misc]


def _filter_cells(cell: pd.DataFrame, mapping: pd.DataFrame, target_regions: list[str]) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for _, r in mapping.iterrows():
        region = str(r["region_user"]).strip()
        if region not in target_regions:
            continue
        col = r["allen_region_column"]
        val = str(r["allen_region_value"]).strip()
        if col not in cell.columns or not val:
            print(f"[WARN] mapping row skipped: {r.to_dict()}")
            continue
        sub = cell.loc[cell[col].astype(str) == val].copy()
        sub["region_user"] = region
        parts.append(sub)
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, axis=0)
    if "cell_label" in out.columns:
        out = out.drop_duplicates(subset=["cell_label"])
    return out


def compute_subclass_stats(
    joined: pd.DataFrame, genes: list[str], min_cells: int
) -> pd.DataFrame:
    rows: list[dict] = []
    for (region, subclass), sub in tqdm(
        joined.groupby(["region_user", "subclass"], observed=True),
        desc="subclass stats",
    ):
        n = len(sub)
        if n < min_cells:
            continue
        present = [g for g in genes if g in sub.columns]
        if not present:
            continue
        means = sub[present].mean(axis=0)
        pcts = (sub[present] > 0).mean(axis=0) * 100.0
        for g in present:
            rows.append(
                {
                    "region_user": region,
                    "subclass": str(subclass),
                    "gene": g,
                    "n_cells": int(n),
                    "mean_log2_expr": round(float(means[g]), 4),
                    "pct_expr": round(float(pcts[g]), 2),
                }
            )
    return pd.DataFrame(rows)


def _specificity_within(df: pd.DataFrame, colname: str) -> pd.DataFrame:
    """For each (region, gene): mean - max(mean over the OTHER rows of df).

    The top expressor is compared against the runner-up, everybody else against
    the top. Returns (region_user, subclass, gene, colname, runner-up info).
    """
    df = df[["region_user", "subclass", "gene", "mean_log2_expr"]].copy()
    g = df.groupby(["region_user", "gene"])["mean_log2_expr"]
    mx = g.transform("max")
    second = g.transform(lambda s: s.nlargest(2).iloc[-1] if len(s) > 1 else s.iloc[0])
    is_top = df["mean_log2_expr"].to_numpy() >= mx.to_numpy() - 1e-12
    competitor = np.where(is_top, second.to_numpy(), mx.to_numpy())
    df[colname] = (df["mean_log2_expr"].to_numpy() - competitor).round(4)
    df[f"{colname}_competitor_mean"] = np.round(competitor, 4)
    return df.drop(columns=["mean_log2_expr"])


def add_specificity(stats: pd.DataFrame, anchor_index: pd.MultiIndex) -> pd.DataFrame:
    """Attach vs_neuronal (whole dissection ROI) and vs_panel (anchors only)."""
    if stats.empty:
        return stats
    stats = stats.copy()
    stats["is_nonneuronal"] = stats["subclass"].map(is_nonneuronal)
    stats["is_anchor_subclass"] = stats.set_index(["region_user", "subclass"]).index.isin(
        anchor_index
    )

    neuro = stats.loc[~stats["is_nonneuronal"]]
    if not neuro.empty:
        stats = stats.merge(
            _specificity_within(neuro, "specificity_log2_vs_neuronal"),
            on=["region_user", "subclass", "gene"],
            how="left",
        )
    else:
        stats["specificity_log2_vs_neuronal"] = np.nan

    panel = stats.loc[stats["is_anchor_subclass"]]
    if not panel.empty:
        stats = stats.merge(
            _specificity_within(panel, "specificity_log2_vs_panel"),
            on=["region_user", "subclass", "gene"],
            how="left",
        )
    else:
        stats["specificity_log2_vs_panel"] = np.nan
    return stats


def pairwise_separators(
    stats: pd.DataFrame,
    celltype_of: dict[tuple[str, str], str],
    min_pct_high: float,
    max_pct_low: float,
    min_mean_high: float,
    min_diff: float,
    top_n: int,
) -> pd.DataFrame:
    """For every ordered pair of anchor subclasses, the genes that mark A but not B.

    This is the direct answer to "which gene separates cell type 1 from 2 and 3":
    ON in A (pct >= min_pct_high) and OFF in B (pct <= max_pct_low), ranked by
    the log2 expression gap.
    """
    panel = stats[stats["is_anchor_subclass"]]
    rows: list[dict] = []
    for region, reg in panel.groupby("region_user", observed=True):
        wide_mean = reg.pivot_table(index="subclass", columns="gene", values="mean_log2_expr")
        wide_pct = reg.pivot_table(index="subclass", columns="gene", values="pct_expr")
        subs = list(wide_mean.index)
        for a in subs:
            for b in subs:
                if a == b:
                    continue
                diff = wide_mean.loc[a] - wide_mean.loc[b]
                ok = (
                    (wide_pct.loc[a] >= min_pct_high)
                    & (wide_pct.loc[b] <= max_pct_low)
                    & (wide_mean.loc[a] >= min_mean_high)
                    & (diff >= min_diff)
                )
                sel = diff[ok].sort_values(ascending=False).head(top_n)
                for gene, d in sel.items():
                    rows.append(
                        {
                            "region_user": region,
                            "subclass_A_positive": a,
                            "subclass_B_negative": b,
                            "same_cell_type_label": celltype_of.get((region, str(a)))
                            == celltype_of.get((region, str(b))),
                            "separator_gene": gene,
                            "mean_log2_A": round(float(wide_mean.loc[a, gene]), 3),
                            "mean_log2_B": round(float(wide_mean.loc[b, gene]), 3),
                            "pct_A": round(float(wide_pct.loc[a, gene]), 1),
                            "pct_B": round(float(wide_pct.loc[b, gene]), 1),
                            "log2_gap": round(float(d), 3),
                        }
                    )
    return pd.DataFrame(rows)


def tier_gpcrs(
    gpcr: pd.DataFrame,
    target_regions: list[str],
    anchor_index: pd.MultiIndex,
    min_pct: float,
    min_mean: float,
    specific_max_frac: float,
    universal_min_frac: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (per-region tier table, per-subclass panel specificity table)."""
    df = gpcr[gpcr["region_user"].isin(target_regions)].copy()
    df["subclass"] = df["subclass"].astype(str)
    df = df.rename(columns={"gpcr_gene": "gene"})
    df["is_nonneuronal"] = df["subclass"].map(is_nonneuronal)
    df["is_anchor_subclass"] = df.set_index(["region_user", "subclass"]).index.isin(anchor_index)
    df["detected"] = (df["pct_expr"] >= min_pct) & (df["mean_log2_expr"] >= min_mean)

    def _tier(f: float) -> str:
        if f <= specific_max_frac:
            return "cell_type_specific"
        if f >= universal_min_frac:
            return "universal"
        return "intermediate"

    def _frac(sub: pd.DataFrame, label: str) -> pd.DataFrame:
        n = sub.groupby("region_user")["subclass"].nunique().rename(f"n_{label}_subclasses")
        agg = (
            sub.groupby(["region_user", "gene"])
            .agg(**{f"n_{label}_detected": ("detected", "sum")})
            .reset_index()
            .merge(n, on="region_user", how="left")
        )
        agg[f"frac_{label}_detected"] = (
            agg[f"n_{label}_detected"] / agg[f"n_{label}_subclasses"]
        ).round(3)
        agg[f"gpcr_tier_{label}"] = agg[f"frac_{label}_detected"].map(_tier)
        return agg

    panel = df[df["is_anchor_subclass"]].copy()
    neuro = df[~df["is_nonneuronal"]].copy()

    tiers = _frac(panel, "panel").merge(_frac(neuro, "roi"), on=["region_user", "gene"], how="outer")

    # best panel anchor for each GPCR
    panel_spec = panel.merge(
        _specificity_within(panel, "specificity_log2_vs_panel"),
        on=["region_user", "subclass", "gene"],
        how="left",
    )
    best = (
        panel_spec.sort_values("mean_log2_expr", ascending=False)
        .groupby(["region_user", "gene"], as_index=False)
        .first()[["region_user", "gene", "subclass", "mean_log2_expr", "pct_expr",
                  "specificity_log2_vs_panel"]]
        .rename(
            columns={
                "subclass": "top_panel_subclass",
                "mean_log2_expr": "top_panel_mean_log2",
                "pct_expr": "top_panel_pct",
                "specificity_log2_vs_panel": "top_panel_specificity_log2",
            }
        )
    )
    tiers = tiers.merge(best, on=["region_user", "gene"], how="left")
    tiers = tiers.rename(columns={"gene": "gpcr_gene"})
    return tiers, panel_spec


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None)
    p.add_argument("--out_dir", required=True)
    p.add_argument("--marker_csv", required=True)
    p.add_argument("--anchor_csv", required=True)
    p.add_argument("--region_mapping_csv", required=True)
    p.add_argument("--gpcr_subclass_csv", required=True)
    p.add_argument(
        "--extra_genes_csv",
        default=None,
        help=(
            "Optional CSV with a gene_symbol column (e.g. inputs/expanded_panel_universe.csv). "
            "Its genes are added to the expression panel so that TF / plasticity / IEG / "
            "reporter / class-backbone categories get the same per-subclass statistics as "
            "the curated cell-type markers."
        ),
    )
    p.add_argument("--target_regions", nargs="+", default=["BMAp", "ORBm"])
    p.add_argument("--min_cells", type=int, default=30)
    p.add_argument("--top_n", type=int, default=12)
    p.add_argument("--min_specificity", type=float, default=0.5)
    p.add_argument("--min_pct", type=float, default=25.0)
    p.add_argument("--min_mean", type=float, default=0.5)
    # GPCR tiering
    p.add_argument("--gpcr_min_pct", type=float, default=20.0)
    p.add_argument("--gpcr_min_mean", type=float, default=0.5)
    p.add_argument("--gpcr_specific_max_frac", type=float, default=0.30)
    p.add_argument("--gpcr_universal_min_frac", type=float, default=0.70)
    p.add_argument("--pair_max_pct_low", type=float, default=15.0)
    p.add_argument("--pair_min_gap", type=float, default=1.0)
    p.add_argument("--refresh_expression", action="store_true")
    args = p.parse_args()

    cfg = load_config(args.config)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = open_abc_cache(cfg)

    anchors = pd.read_csv(args.anchor_csv)
    anchors = anchors[anchors["region_user"].isin(args.target_regions)].copy()
    markers_tpl = pd.read_csv(args.marker_csv)
    markers_tpl = markers_tpl[markers_tpl["region_user"].isin(args.target_regions)]

    gpcr = pd.read_csv(args.gpcr_subclass_csv)
    roi_subclasses = sorted(
        gpcr.loc[gpcr["region_user"].isin(args.target_regions), "subclass"].astype(str).unique()
    )
    print(f"[INFO] subclasses in target ROIs: {len(roi_subclasses)}")

    # ---- candidate gene panel
    from_names = parse_gene_tokens_from_subclass_names(roi_subclasses)
    print(f"[INFO] gene tokens parsed from subclass names: {len(from_names)}")
    from_curated: set[str] = set()
    for col in ("marker_genes", "exclusion_markers"):
        if col in markers_tpl.columns:
            for v in markers_tpl[col].dropna():
                from_curated.update(g.strip() for g in str(v).split(",") if g.strip())
    from_extra: set[str] = set()
    if args.extra_genes_csv:
        extra = pd.read_csv(args.extra_genes_csv)
        col = "gene_symbol" if "gene_symbol" in extra.columns else extra.columns[0]
        from_extra = {str(g).strip() for g in extra[col].dropna() if str(g).strip()}
        print(f"[INFO] extra universe genes: {len(from_extra)} from {args.extra_genes_csv}")
    candidates = sorted(from_names | from_curated | from_extra | set(CANONICAL_PANEL))
    print(f"[INFO] candidate panel before Allen validation: {len(candidates)}")

    print("[INFO] loading WMB-10X cell metadata + gene metadata")
    cell = cache.get_metadata_dataframe("WMB-10X", "cell_metadata_with_cluster_annotation")
    gene = cache.get_metadata_dataframe("WMB-10X", "gene")
    if "cell_label" in cell.columns:
        cell = cell.set_index("cell_label", drop=False)
    gsym = _detect_gene_symbol_col(gene)
    available = set(gene[gsym].dropna().astype(str).str.strip())
    genes = [g for g in candidates if g in available]
    missing = [g for g in candidates if g not in available]
    print(f"[INFO] panel present in Allen: {len(genes)}; not found: {len(missing)} {missing[:20]}")

    mapping = pd.read_csv(args.region_mapping_csv)
    cell_sub = _filter_cells(cell, mapping, args.target_regions)
    if cell_sub.empty:
        raise SystemExit(f"[ERROR] no cells for regions {args.target_regions}")
    print(f"[INFO] cells: {len(cell_sub)}")
    print(cell_sub.groupby("region_user").size().to_string())

    # Loading the Isocortex/STR h5ad shards costs ~2 min, so cache the panel.
    panel_key = hashlib.md5(
        ("|".join(sorted(genes)) + "||" + "|".join(sorted(args.target_regions))).encode()
    ).hexdigest()[:12]
    expr_cache = out / f"_expr_cache_{panel_key}.parquet"
    if expr_cache.exists() and not args.refresh_expression:
        print(f"[INFO] reusing cached expression panel {expr_cache.name}")
        expr = pd.read_parquet(expr_cache)
    else:
        expr = _get_gene_data_with_retry(
            cache=cache,
            all_cells=cell_sub,
            gene=gene,
            genes=genes,
            data_type=cfg.expression_data_type,
            chunk_size=cfg.chunk_size,
        )
        if not isinstance(expr, pd.DataFrame):
            expr = pd.DataFrame(expr)
        expr.to_parquet(expr_cache)
    print(f"[INFO] expression matrix: {expr.shape}")
    joined = cell_sub.join(expr, how="left")

    anchor_index = anchors.set_index(["region_user", "allen_subclass_anchor"]).index
    celltype_of = {
        (str(r["region_user"]), str(r["allen_subclass_anchor"])): str(r["cell_type_label"])
        for _, r in anchors.iterrows()
    }
    role_of = {
        (str(r["region_user"]), str(r["allen_subclass_anchor"])): str(r.get("role", "target"))
        for _, r in anchors.iterrows()
    }

    stats = compute_subclass_stats(joined, genes, args.min_cells)
    stats = add_specificity(stats, anchor_index)
    name_gene_map = {
        sc: parse_gene_tokens_from_subclass_names([sc]) for sc in stats["subclass"].unique()
    }
    stats["in_subclass_name"] = [
        g in name_gene_map.get(sc, set()) for sc, g in zip(stats["subclass"], stats["gene"])
    ]

    long_path = out / "Subclass_Discriminating_Markers_long.csv"
    stats.to_csv(long_path, index=False)
    print(f"[OK] {long_path} rows={len(stats)}")

    # ---- discriminating selection: PANEL specificity is the primary criterion
    disc = stats[
        stats["is_anchor_subclass"]
        & (stats["specificity_log2_vs_panel"] >= args.min_specificity)
        & (stats["pct_expr"] >= args.min_pct)
        & (stats["mean_log2_expr"] >= args.min_mean)
    ].copy()
    disc["cell_type_label"] = [
        celltype_of.get((r, s), "") for r, s in zip(disc["region_user"], disc["subclass"])
    ]
    disc["role"] = [role_of.get((r, s), "") for r, s in zip(disc["region_user"], disc["subclass"])]

    # uniqueness: how many anchors / cell types does this gene pass for?
    n_anchor = disc.groupby(["region_user", "gene"])["subclass"].transform("nunique")
    n_ct = disc.groupby(["region_user", "gene"])["cell_type_label"].transform("nunique")
    disc["n_anchors_passing"] = n_anchor
    disc["uniqueness"] = np.where(
        n_anchor == 1,
        "UNIQUE_to_subclass",
        np.where(n_ct == 1, "shared_within_cell_type", "shared_across_cell_types"),
    )

    # Allen's own label gene wins ties, then unique separators, then specificity
    disc["rank_key"] = (
        disc["specificity_log2_vs_panel"]
        + disc["in_subclass_name"].astype(float) * 100.0
        + (disc["uniqueness"] == "UNIQUE_to_subclass").astype(float) * 20.0
    )
    disc = disc.sort_values(["region_user", "subclass", "rank_key"], ascending=[True, True, False])
    disc["rank_within_subclass"] = (
        disc.groupby(["region_user", "subclass"], observed=True).cumcount() + 1
    )
    # A gene can be unique *within the anchor panel* and still be contaminated by a
    # non-anchor population that the same dissection captured. vs_neuronal catches that.
    disc["roi_clean"] = disc["specificity_log2_vs_neuronal"] >= args.min_specificity
    top_roi_expressor = (
        stats[~stats["is_nonneuronal"]]
        .sort_values("mean_log2_expr", ascending=False)
        .groupby(["region_user", "gene"], as_index=False)
        .first()
        .set_index(["region_user", "gene"])[["subclass", "mean_log2_expr", "pct_expr"]]
    )
    contam: list[str] = []
    for r in disc.itertuples():
        if r.roi_clean:
            contam.append("")
            continue
        try:
            t = top_roi_expressor.loc[(r.region_user, r.gene)]
        except KeyError:
            contam.append("")
            continue
        if str(t["subclass"]) == str(r.subclass):
            contam.append("")
        else:
            contam.append(
                f"{t['subclass']} in same dissection is higher "
                f"({t['mean_log2_expr']:.2f}, {t['pct_expr']:.0f}%)"
            )
    disc["contaminating_subclass_in_roi"] = contam
    top = disc[disc["rank_within_subclass"] <= args.top_n].copy()
    top_path = out / "Subclass_Discriminating_Markers_top.csv"
    top.to_csv(top_path, index=False)
    print(f"[OK] {top_path} rows={len(top)}")

    # ---- pairwise separators (which gene tells anchor A from anchor B)
    pairs = pairwise_separators(
        stats,
        celltype_of,
        min_pct_high=args.min_pct,
        max_pct_low=args.pair_max_pct_low,
        min_mean_high=args.min_mean,
        min_diff=args.pair_min_gap,
        top_n=args.top_n,
    )
    pair_path = out / "Subclass_Pairwise_Separators.csv"
    pairs.to_csv(pair_path, index=False)
    print(f"[OK] {pair_path} rows={len(pairs)}")
    if not pairs.empty:
        blind = (
            pairs.groupby(["region_user", "subclass_A_positive", "subclass_B_negative"])
            .size()
            .reset_index(name="n")
        )
        print(f"[INFO] anchor pairs with >=1 separator: {len(blind)}")

    # ---- GPCR tiers
    tiers, gpcr_panel = tier_gpcrs(
        gpcr,
        args.target_regions,
        anchor_index,
        args.gpcr_min_pct,
        args.gpcr_min_mean,
        args.gpcr_specific_max_frac,
        args.gpcr_universal_min_frac,
    )
    tiers_path = out / "GPCR_Specificity_Tiers.csv"
    tiers.to_csv(tiers_path, index=False)
    print(f"[OK] {tiers_path} rows={len(tiers)}")
    print(tiers.groupby(["region_user", "gpcr_tier_panel"]).size().to_string())

    # ---- per-anchor rollups
    n_cells_lookup = (
        stats[["region_user", "subclass", "n_cells"]]
        .drop_duplicates()
        .set_index(["region_user", "subclass"])["n_cells"]
        .to_dict()
    )
    disc_lookup: dict[tuple[str, str], pd.DataFrame] = {
        k: v for k, v in top.groupby(["region_user", "subclass"], observed=True)
    }
    gpcr_t = gpcr_panel.merge(
        tiers[["region_user", "gpcr_gene", "gpcr_tier_panel", "gpcr_tier_roi",
               "frac_panel_detected", "frac_roi_detected"]].rename(columns={"gpcr_gene": "gene"}),
        on=["region_user", "gene"],
        how="left",
    )

    anchor_rows: list[dict] = []
    for _, a in anchors.iterrows():
        region = str(a["region_user"]).strip()
        sc = str(a["allen_subclass_anchor"]).strip()
        d = disc_lookup.get((region, sc))
        if d is not None and not d.empty:
            uniq = d[d["uniqueness"] == "UNIQUE_to_subclass"]
            in_name = d[d["in_subclass_name"]]["gene"].tolist()
            disc_str = "; ".join(
                f"{r.gene} (panel_spec={r.specificity_log2_vs_panel:.2f}, "
                f"{r.pct_expr:.0f}% of cells, {r.uniqueness})"
                for r in d.itertuples()
            )
            disc_genes = ", ".join(d["gene"].tolist())
            uniq_genes = ", ".join(uniq["gene"].tolist())
            shared_genes = ", ".join(d[d["uniqueness"] != "UNIQUE_to_subclass"]["gene"].tolist())
            best_genes = ", ".join(uniq[uniq["roi_clean"]]["gene"].tolist())
            contam_notes = "; ".join(
                f"{r.gene}: {r.contaminating_subclass_in_roi}"
                for r in uniq.itertuples()
                if r.contaminating_subclass_in_roi
            )
        else:
            in_name, disc_str, disc_genes, uniq_genes, shared_genes = [], "", "", "", ""
            best_genes, contam_notes = "", ""

        g_det = gpcr_t[
            (gpcr_t["region_user"] == region)
            & (gpcr_t["subclass"] == sc)
            & (gpcr_t["pct_expr"] >= args.gpcr_min_pct)
            & (gpcr_t["mean_log2_expr"] >= args.gpcr_min_mean)
        ]
        spec_g = g_det[g_det["gpcr_tier_panel"] == "cell_type_specific"].sort_values(
            "specificity_log2_vs_panel", ascending=False
        )
        inter_g = g_det[g_det["gpcr_tier_panel"] == "intermediate"].sort_values(
            "specificity_log2_vs_panel", ascending=False
        )
        univ_g = g_det[g_det["gpcr_tier_panel"] == "universal"].sort_values(
            "mean_log2_expr", ascending=False
        )
        # GPCRs where THIS anchor is the top expressor of the panel by a margin
        enriched = g_det[g_det["specificity_log2_vs_panel"] >= args.min_specificity].sort_values(
            "specificity_log2_vs_panel", ascending=False
        )

        # explicit "to tell me apart from my sibling subclasses, use X"
        sib = pairs[
            (pairs["region_user"] == region)
            & (pairs["subclass_A_positive"] == sc)
            & pairs["same_cell_type_label"]
        ] if not pairs.empty else pd.DataFrame()
        recipe = "; ".join(
            f"vs {b}: {', '.join(grp.sort_values('log2_gap', ascending=False)['separator_gene'].head(3))}"
            for b, grp in sib.groupby("subclass_B_negative", sort=False)
        )

        # When no single gene is unique, spell out a POSITIVE + NEGATIVE gate combination
        # against every other anchor in the region, not just same-cell-type siblings.
        # Built from the pairwise table (not from `disc`), because an anchor needing a
        # combination may have NO gene clearing the panel-specificity threshold at all.
        combo = ""
        if not uniq_genes and not pairs.empty:
            reg_pairs = pairs[pairs["region_user"] == region]
            mine = reg_pairs[reg_pairs["subclass_A_positive"] == sc]
            pos_rank = (
                mine.groupby("separator_gene")
                .agg(n_excluded=("subclass_B_negative", "nunique"),
                     mean_gap=("log2_gap", "mean"),
                     pct=("pct_A", "max"))
                .sort_values(["n_excluded", "mean_gap"], ascending=False)
                .head(4)
            )
            pos = [
                f"{g}+ ({r.pct:.0f}% of cells, excludes {int(r.n_excluded)} of the other anchors)"
                for g, r in pos_rank.iterrows()
            ]
            gates = []
            for other, grp in reg_pairs[reg_pairs["subclass_B_negative"] == sc].groupby(
                "subclass_A_positive", sort=False
            ):
                g = grp.sort_values("log2_gap", ascending=False).iloc[0]
                gates.append(f"{g['separator_gene']}- rules out {other}")
            combo = (
                "No single gene is unique to this subclass. "
                f"POSITIVE core (shared with siblings): {'; '.join(pos)}. "
                f"NEGATIVE gates required: {'; '.join(gates)}"
            )

        anchor_rows.append(
            {
                "region_user": region,
                "cell_type_label": a["cell_type_label"],
                "allen_subclass_anchor": sc,
                "role": a.get("role", "target"),
                "n_cells": int(n_cells_lookup.get((region, sc), 0)),
                "UNIQUE_separator_genes": uniq_genes,
                "BEST_separators_also_clean_in_whole_ROI": best_genes,
                "roi_contamination_warning": contam_notes,
                "how_to_separate_from_siblings": recipe,
                "needs_marker_combination": "YES" if not uniq_genes else "NO",
                "marker_combination_recipe": combo,
                "allen_name_embedded_markers_verified": ", ".join(in_name),
                "shared_marker_genes": shared_genes,
                "discriminating_markers_ranked": disc_genes,
                "discriminating_markers_with_stats": disc_str,
                "GPCRs_enriched_in_this_subclass": ", ".join(
                    f"{r.gene} (panel_spec={r.specificity_log2_vs_panel:.2f}, {r.pct_expr:.0f}%)"
                    for r in enriched.itertuples()
                ),
                "cell_type_specific_GPCRs": ", ".join(spec_g["gene"].tolist()),
                "intermediate_GPCRs": ", ".join(inter_g["gene"].tolist()),
                "universal_GPCRs": ", ".join(univ_g["gene"].tolist()),
                "n_unique_separators": int(len(uniq)) if d is not None and not d.empty else 0,
                "n_specific_GPCRs": int(len(spec_g)),
                "n_universal_GPCRs": int(len(univ_g)),
            }
        )

    anchor_df = pd.DataFrame(anchor_rows)
    anchor_path = out / "Subclass_Marker_Panel_perAnchor.csv"
    anchor_df.to_csv(anchor_path, index=False)
    print(f"[OK] {anchor_path} rows={len(anchor_df)}")

    write_run_log(
        out,
        "A06_subclass_discriminating_markers",
        {
            "manifest_version": cfg.manifest_version,
            "target_regions": args.target_regions,
            "n_candidate_genes": len(candidates),
            "n_genes_in_allen": len(genes),
            "genes_not_found": missing,
            "n_cells": int(len(cell_sub)),
            "n_subclasses_scored": int(stats[["region_user", "subclass"]].drop_duplicates().shape[0]),
            "n_anchor_rows": int(len(anchor_df)),
            "n_pairwise_separator_rows": int(len(pairs)),
            "anchors_without_unique_separator": anchor_df.loc[
                anchor_df["needs_marker_combination"] == "YES", "allen_subclass_anchor"
            ].tolist(),
            "thresholds": {
                "min_specificity": args.min_specificity,
                "min_pct": args.min_pct,
                "min_mean": args.min_mean,
                "gpcr_specific_max_frac": args.gpcr_specific_max_frac,
                "gpcr_universal_min_frac": args.gpcr_universal_min_frac,
            },
        },
    )
    print("[DONE] A06 complete")


if __name__ == "__main__":
    main()
