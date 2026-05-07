#!/usr/bin/env python
"""
A03_allen_gpcr_expression.py

Module A: Allen-only computational module.

Pulls log2 expression for a curated GPCR universe from Allen WMB-10X for cells
in user regions, then summarises per-group means / pct expressing / specificity
at three taxonomy levels (subclass, supertype, cluster).

Critical fixes vs earlier draft
-------------------------------
1. ``get_gene_data`` is now called with the **filtered** cell set so it only
   triggers downloads for the matrices that actually contain target cells
   (the original draft passed the full 4M cell metadata, which forces every
   regional h5ad to be loaded).
2. Windows ``PermissionError`` (file lock) on ``.h5ad`` is caught with an
   exponential ``gc.collect`` + sleep retry loop.
3. Output is split per taxonomy level so downstream rules are not stuck with
   one ultra-fine grouping.
4. A specificity column is added: ``specificity_log2 = group mean - max(other
   group means at the same taxonomy level)``. Combined with mean/pct ranks,
   D02 can drop ubiquitous receptors via ``downgrade_low_specificity``.
"""
from __future__ import annotations

import argparse
import gc
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

LEVELS = ("subclass", "supertype", "cluster")


def _detect_gene_symbol_col(gene: pd.DataFrame) -> str:
    for c in ("gene_symbol", "symbol", "gene_name", "name"):
        if c in gene.columns:
            return c
    return gene.columns[0]


def _load_region_mapping(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["region_user", "allen_region_column", "allen_region_value"])
    df = pd.read_csv(path)
    if "allen_region_value" in df.columns:
        df = df[df["allen_region_value"].astype(str).str.strip() != ""].copy()
    return df


def _filter_cells(cell: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    if mapping.empty:
        return pd.DataFrame()
    parts: list[pd.DataFrame] = []
    for _, r in mapping.iterrows():
        col = r["allen_region_column"]
        val = str(r["allen_region_value"]).strip()
        if col not in cell.columns or not val:
            print(f"[WARN] mapping row skipped (missing col or empty value): {r.to_dict()}")
            continue
        sub = cell.loc[cell[col].astype(str) == val].copy()
        sub["region_user"] = r["region_user"]
        parts.append(sub)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, axis=0).drop_duplicates(subset=["cell_label"]) if "cell_label" in parts[0].columns else pd.concat(parts, axis=0)


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


def _summarize(joined: pd.DataFrame, group_cols: list[str], genes: list[str], min_cells: int) -> pd.DataFrame:
    rows: list[dict] = []
    for keys, sub in tqdm(
        joined.groupby(group_cols, dropna=False, observed=True),
        desc=f"summarize {'/'.join(group_cols)}",
    ):
        if not isinstance(keys, tuple):
            keys = (keys,)
        n = len(sub)
        if n < min_cells:
            continue
        for g in genes:
            if g not in sub.columns:
                continue
            vals = sub[g].to_numpy()
            rows.append(
                {
                    **dict(zip(group_cols, keys)),
                    "gpcr_gene": g,
                    "n_cells": int(n),
                    "mean_log2_expr": float(np.nanmean(vals)),
                    "pct_expr": float(np.mean(vals > 0) * 100.0),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out

    # ranks within each (region, level)
    out["rank_mean_expr"] = out.groupby(group_cols)["mean_log2_expr"].rank(ascending=False, method="dense")
    out["rank_pct_expr"] = out.groupby(group_cols)["pct_expr"].rank(ascending=False, method="dense")
    out["combined_rank_score"] = out["rank_mean_expr"] + out["rank_pct_expr"]
    out["rank_combined"] = out.groupby(group_cols)["combined_rank_score"].rank(ascending=True, method="dense")
    return out


def _add_specificity(summary: pd.DataFrame, level_col: str) -> pd.DataFrame:
    """For each (region_user, gene) compute (this group) - max(other groups at same level)."""
    if summary.empty:
        return summary
    sort_cols = ["region_user", "gpcr_gene", "mean_log2_expr"]
    s = summary.sort_values(sort_cols, ascending=[True, True, False]).copy()
    grouped = s.groupby(["region_user", "gpcr_gene"])["mean_log2_expr"]
    # 2nd-largest within (region, gene) so the top row's "other groups max" = next-best
    second = grouped.transform(lambda x: x.shift(-1).ffill())
    rank_in_group = grouped.rank(method="first", ascending=False)
    is_top = rank_in_group == 1
    max_other = np.where(is_top, second, grouped.transform("max"))
    s["specificity_log2"] = s["mean_log2_expr"].to_numpy() - np.asarray(max_other, dtype=float)
    s["rank_specificity"] = s.groupby(["region_user", level_col])["specificity_log2"].rank(
        ascending=False, method="dense"
    )
    return s


def _run_level(joined: pd.DataFrame, region_col: str, level_col: str, genes: list[str], min_cells: int) -> pd.DataFrame:
    if level_col not in joined.columns:
        print(f"[WARN] level column missing: {level_col}; skipping")
        return pd.DataFrame()
    df = _summarize(joined, [region_col, level_col], genes, min_cells)
    if df.empty:
        return df
    df = _add_specificity(df, level_col)
    df["taxonomy_level"] = level_col
    df["evidence_source"] = "Allen_WMB_10X_computed"
    return df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None)
    p.add_argument("--out_dir", required=True)
    p.add_argument("--gpcr_csv", required=True)
    p.add_argument("--region_mapping_csv", default=None)
    p.add_argument("--levels", nargs="+", default=list(LEVELS), help="One or more of subclass/supertype/cluster")
    args = p.parse_args()

    cfg = load_config(args.config)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = open_abc_cache(cfg)

    print("[INFO] loading WMB-10X cell metadata + gene metadata")
    cell = cache.get_metadata_dataframe("WMB-10X", "cell_metadata_with_cluster_annotation")
    gene = cache.get_metadata_dataframe("WMB-10X", "gene")
    if "cell_label" in cell.columns:
        cell = cell.set_index("cell_label", drop=False)

    gpcr = pd.read_csv(args.gpcr_csv)
    gpcr_col = "mouse_gene_symbol" if "mouse_gene_symbol" in gpcr.columns else gpcr.columns[0]
    requested = sorted({str(g).strip() for g in gpcr[gpcr_col].dropna() if str(g).strip()})
    gene_symbol_col = _detect_gene_symbol_col(gene)
    available = set(gene[gene_symbol_col].dropna().astype(str).str.strip())
    genes = [g for g in requested if g in available]
    pd.DataFrame({"gpcr_gene": genes}).to_csv(out / "GPCR_Genes_Present_In_Allen.csv", index=False)
    pd.DataFrame({"gpcr_gene": [g for g in requested if g not in available]}).to_csv(
        out / "GPCR_Genes_Missing_From_Allen.csv", index=False
    )
    print(f"[INFO] GPCR universe: requested={len(requested)} present_in_Allen={len(genes)}")

    mapping = _load_region_mapping(Path(args.region_mapping_csv) if args.region_mapping_csv else None)
    cell_sub = _filter_cells(cell, mapping)
    if cell_sub.empty:
        raise SystemExit(
            "[ERROR] No cells matched region mapping. Run A02 and finalise Region_Mapping_Auto_Draft.csv."
        )
    print(f"[INFO] cells in region mapping: {len(cell_sub)} from {mapping['region_user'].nunique()} regions")

    expr = _get_gene_data_with_retry(
        cache=cache,
        all_cells=cell_sub,  # CRITICAL: only target cells
        gene=gene,
        genes=genes,
        data_type=cfg.expression_data_type,
        chunk_size=cfg.chunk_size,
    )
    if not isinstance(expr, pd.DataFrame):
        expr = pd.DataFrame(expr)
    joined = cell_sub.join(expr, how="left")

    # write per-level summaries
    out_files: list[str] = []
    for lvl in args.levels:
        df_lvl = _run_level(joined, "region_user", lvl, genes, cfg.thresholds.min_cells)
        if df_lvl.empty:
            print(f"[WARN] empty result for level {lvl}")
            continue
        path = out / f"Allen_GPCR_Ranking_{lvl}.csv"
        df_lvl.to_csv(path, index=False)
        out_files.append(str(path))
        print(f"[OK] {path} rows={len(df_lvl)}")

    write_run_log(
        out,
        "A03_allen_gpcr_expression",
        {
            "manifest_version": cfg.manifest_version,
            "n_genes": len(genes),
            "n_cells": int(len(cell_sub)),
            "regions": sorted(cell_sub["region_user"].dropna().astype(str).unique().tolist()),
            "levels": args.levels,
            "thresholds": cfg.thresholds.__dict__,
            "out_files": out_files,
        },
    )
    print("[DONE] A03 complete")


if __name__ == "__main__":
    main()
