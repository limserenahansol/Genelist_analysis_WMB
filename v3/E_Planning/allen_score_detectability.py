"""Score Xenium detectability for every panel candidate, from the local Allen matrices.

This closes the gap the panel design left open: of the 245 Option C candidates, 68 had
never been scored for detectability because the earlier pass only covered ~271 genes.
The raw Allen matrices were in fact cached locally all along, so every candidate can
be scored on the same footing.

Definition used, matching the existing panel columns:
  max_pct = the highest per-anchor-subclass percentage of cells with a nonzero value,
            taken over the 20 ORBm/BMAp anchor subclasses.
  Matrices are the ABC Atlas log2(CPM+1) values, so "detected" is value > 0.

Outputs outputs/allen_detectability_all_candidates.xlsx with
  per_anchor        gene x 20 anchors, percent of cells detected
  summary           per gene: max_pct, median across anchors, n anchors >= 50%, region split
  newly_scored      the genes that had no detectability figure before
  panel_membership  which of Panel A / B / C each gene belongs to
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
EX = OUT / "allen_extract"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PA = OUT / "PANEL_A_current_166genes_119custom.xlsx"
PB = OUT / "PANEL_B_cut_147genes_100custom.xlsx"
PC = OUT / "PANEL_C_expanded_standalone_245genes.xlsx"
DST = OUT / "allen_detectability_all_candidates.xlsx"


def load_all() -> tuple[np.ndarray, list[str], pd.DataFrame]:
    files = sorted(EX.glob("*.npz"))
    if not files:
        raise SystemExit(f"no extracted matrices in {EX}")
    mats, metas, genes = [], [], None
    for f in files:
        z = np.load(f, allow_pickle=True)
        g = [str(x) for x in z["genes"]]
        if genes is None:
            genes = g
        elif g != genes:
            raise SystemExit(f"{f.name}: gene order differs from {files[0].name}")
        mats.append(z["X"])
        metas.append(pd.DataFrame({
            "cell": [str(x) for x in z["cell"]],
            "roi": [str(x) for x in z["roi"]],
            "subclass": [str(x) for x in z["subclass"]],
            "supertype": [str(x) for x in z["supertype"]],
            "cluster": [str(x) for x in z["cluster"]],
        }))
        print(f"  {f.name}: {mats[-1].shape[0]:,} cells", flush=True)
    X = np.vstack(mats)
    md = pd.concat(metas, ignore_index=True)
    print(f"combined: {X.shape[0]:,} cells x {X.shape[1]} genes", flush=True)
    if md.cell.duplicated().any():
        print(f"  WARNING {int(md.cell.duplicated().sum())} duplicate cell labels", flush=True)
    return X, genes, md


def main() -> None:
    X, genes, md = load_all()
    ac = pd.read_excel(PA, "ANCHOR_COVERAGE")[["region", "allen_subclass_anchor", "n_cells"]]
    anchors = list(ac.allen_subclass_anchor)

    # Anchors are region-specific: an ORBm anchor means that subclass IN PL-ILA-ORB.
    # Pooling both ROIs diluted four interneuron anchors (Lamp5 18.3%, Vip 11.8%,
    # Sst 3.2%, Pvalb 2.1% of their pooled cells came from the other region).
    region_of = dict(zip(ac.allen_subclass_anchor,
                         ac.region.map({"ORBm": "PL-ILA-ORB", "BMAp": "sAMY"})))
    det = (X > 0)
    rows = {}
    for a in anchors:
        m = ((md.subclass == a) & (md.roi == region_of[a])).to_numpy()
        if not m.any():
            print(f"  WARNING no cells for anchor {a}", flush=True)
            rows[a] = np.full(len(genes), np.nan)
            continue
        rows[a] = det[m].mean(axis=0) * 100.0
    per = pd.DataFrame(rows, index=genes)
    per.index.name = "gene"

    orb = [a for a in anchors if ac.set_index("allen_subclass_anchor").loc[a, "region"] == "ORBm"]
    bma = [a for a in anchors if a not in orb]
    summ = pd.DataFrame({
        "gene": genes,
        "max_pct": per.max(axis=1).values,
        "max_pct_anchor": per.idxmax(axis=1).values,
        "median_pct_across_anchors": per.median(axis=1).values,
        "n_anchors_ge50": (per >= 50).sum(axis=1).values,
        "max_pct_ORBm": per[orb].max(axis=1).values,
        "max_pct_BMAp": per[bma].max(axis=1).values,
    })

    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    A = set(pd.read_excel(PA, "SHARED_PANEL_ORDER").gene.astype(str))
    B = set(pd.read_excel(PB, "SHARED_PANEL_ORDER").gene.astype(str))
    Cg = set(pd.read_excel(PC, "SHARED_PANEL_ORDER").gene.astype(str))
    summ["on_xenium_base"] = summ.gene.isin(base)
    summ["in_panel_A"] = summ.gene.isin(A)
    summ["in_panel_B"] = summ.gene.isin(B)
    summ["in_panel_C"] = summ.gene.isin(Cg)
    summ["measured_in_B"] = summ.gene.isin(base | B)

    # which genes had no prior detectability figure
    prior = set()
    try:
        ab = pd.read_csv(OUT / "jesse_allen_gpcr_abundance" / "Jesse_GPCR_Allen_ORBm_summary.csv")
        prior |= set(ab.gene.astype(str))
    except Exception:
        pass
    for f, sheet, col in ((PA, "SHARED_PANEL_ORDER", "max_pct"),):
        d = pd.read_excel(f, sheet)
        prior |= set(d.loc[d[col].notna(), "gene"].astype(str))
    try:
        dan = pd.read_excel(OUT / "GSE283418_vs_BMAp_panel.xlsx", "all_98_genes")
        prior |= set(dan.loc[dan.max_pct.notna(), "gene"].astype(str))
    except Exception:
        pass
    summ["was_scored_before"] = summ.gene.isin(prior)

    newly = summ[(~summ.was_scored_before) & summ.in_panel_C].sort_values("max_pct", ascending=False)
    print(f"\n=== newly scored, in Panel C: {len(newly)} genes ===", flush=True)
    print(newly[["gene", "max_pct", "max_pct_anchor", "n_anchors_ge50"]].head(40).to_string(index=False))
    print(f"\n  of these, >=50% in at least one anchor : {int((newly.max_pct >= 50).sum())}")
    print(f"           <50% everywhere (sparse)       : {int((newly.max_pct < 50).sum())}")

    with pd.ExcelWriter(DST, engine="openpyxl") as w:
        pd.DataFrame({
            "item": ["What this is", "Detected", "Anchors", "Cells", "Why it exists"],
            "detail": [
                "Xenium detectability for every panel candidate, computed from the locally cached "
                "Allen WMB-10X matrices (97 GB, abc_atlas_cache).",
                "A cell counts as detected when its log2(CPM+1) value is > 0. Percentages are per "
                "anchor subclass.",
                "The 20 ORBm/BMAp anchor subclasses from ANCHOR_COVERAGE.",
                f"{X.shape[0]:,} cells in PL-ILA-ORB or sAMY. Each anchor is counted only "
                "within its own region, so ORBm anchors exclude sAMY cells of the same subclass.",
                "The panel design had scored only ~271 genes, leaving 68 Panel C candidates "
                "unscored. This closes that gap so every candidate is judged on the same basis.",
            ],
        }).to_excel(w, "READ_ME", index=False)
        summ.sort_values("max_pct", ascending=False).to_excel(w, "summary", index=False)
        per.round(2).to_excel(w, "per_anchor")
        newly.to_excel(w, "newly_scored", index=False)
    print(f"\nwrote {DST}", flush=True)


if __name__ == "__main__":
    main()
