"""Score every gene proposed by any panel version on the metrics that matter here.

Two different questions need two different metrics, and the earlier files mixed them:

  Identity genes (cell type, subtype) must be DISTINGUISHABLE.
    subclass_gap   pct in its best anchor minus the highest pct among the other 19
    supertype_gap  pct in its best supertype minus the highest pct among sibling
                   supertypes of the SAME parent subclass. This is the subset-
                   clustering metric: it says whether the gene can split a known
                   type into sub-populations.

  GPCR / plasticity / TF / IEG / morphine genes only have to be VISIBLE.
    anchor_max_pct percent of cells detected at the best of the 20 ORBm/BMAp anchors
    n_anchors_ge50 how many of the 20 anchors are above 50 percent

Everything is restricted to the 20 target anchors in their own region
(ORBm anchors on PL-ILA-ORB cells, BMAp anchors on sAMY cells). PANEL_FINAL_v7
reported detection over all ~79 subclasses present in the two dissections, which
credits genes for hypothalamic, cholinergic and vascular populations that are not
among the 20 targets.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
GW = OUT / "allen_genomewide"
DL = Path(r"c:\Users\hsollim\Downloads")
DST = OUT / "ALL_PANELS_anchor_and_subtype_scores.xlsx"

PANELS = {
    "A_166": "PANEL_A_current_166genes_119custom.xlsx",
    "MSGS_168": "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx",
    "C_246": "PANEL_C_FINAL_246_with_Adrb1.xlsx",
    "standalone_246": "FINAL_Xenium_panel_ORBm_BMAp_standalone_246genes.xlsx",
    "pruned_197": "FINAL_Xenium_panel_ORBm_BMAp_standalone_197genes.xlsx",
    "IDEAL_178": "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx",
    "v7_252": "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx",
    "g301": "FINAL_Xenium_panel_ORBm_BMAp_301genes.xlsx",
}

MIN_CELLS = 40
BAR = 50.0


def load_level(level: str):
    """Accumulate nnz and n per (label, roi) across shards."""
    acc_nnz, acc_n, axis, ens = {}, {}, None, None
    for f in sorted(GW.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        g = [str(x) for x in z["genes"]]
        e = [str(x) for x in z["ensembl"]]
        if axis is None:
            axis, ens = g, e
        elif e != ens:
            raise SystemExit(f"{f.name}: gene axis differs")
        roi = "sAMY" if "STR" in str(z["shard"][0]) else "PL-ILA-ORB"
        for i, lab in enumerate([str(x) for x in z[f"{level}_labels"]]):
            k = (lab, roi)
            if k not in acc_nnz:
                acc_nnz[k] = np.zeros(len(axis), dtype=np.float64)
                acc_n[k] = 0
            acc_nnz[k] += z[f"{level}_nnz"][i]
            acc_n[k] += int(z[f"{level}_n"][i])
    return acc_nnz, acc_n, axis


def collapse(axis, ens, ref_pct):
    """One row per gene symbol: keep the Ensembl row with the highest detection."""
    df = pd.DataFrame({"gene": axis, "ens": ens, "s": ref_pct})
    keep = df.sort_values("s", ascending=False).drop_duplicates("gene").index
    return sorted(keep)


def parent_of(supertype: str) -> str:
    """'0014 L6 IT CTX Glut_2' -> 'L6 IT CTX Glut' (matches anchor text after its number)."""
    body = supertype.split(" ", 1)[1] if " " in supertype else supertype
    return body.rsplit("_", 1)[0]


def main() -> None:
    panel_genes, panel_tables = {}, {}
    for key, fn in PANELS.items():
        p = DL / fn
        if not p.exists():
            p = OUT / fn
        df = pd.read_excel(p, "SHARED_PANEL_ORDER")
        panel_tables[key] = df
        panel_genes[key] = set(df.gene.astype(str))
        print(f"{key:16} {len(df):4} genes   {p.name}")

    ac = pd.read_excel(DL / PANELS["IDEAL_178"], "ANCHOR_COVERAGE")
    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}
    region_of_anchor = dict(zip(ac.allen_subclass_anchor, ac.region))
    sep = set()
    for s in ac.unique_separators_on_shared_panel.fillna(""):
        sep |= {x.strip() for x in str(s).split(",") if x.strip()}

    # ---------------- subclass level, 20 anchors only
    nnz, ncell, axis = load_level("subclass")
    ens = [str(x) for x in np.load(sorted(GW.glob("*.npz"))[0], allow_pickle=True)["ensembl"]]
    keys = [(a, roi_of[a]) for a in roi_of if (a, roi_of[a]) in nnz and ncell[(a, roi_of[a])] > 0]
    print(f"anchors resolved {len(keys)}/20")
    P = np.vstack([nnz[k] / ncell[k] * 100.0 for k in keys])          # 20 x G
    keep_idx = collapse(axis, ens, P.max(axis=0))
    P = P[:, keep_idx]
    gsym = [axis[i] for i in keep_idx]
    gi = {g: j for j, g in enumerate(gsym)}

    anchor_names = [k[0] for k in keys]
    orb_rows = [i for i, a in enumerate(anchor_names) if region_of_anchor[a] == "ORBm"]
    bma_rows = [i for i, a in enumerate(anchor_names) if region_of_anchor[a] == "BMAp"]

    # subclass specificity: best (pct_in - max pct among the other 19)
    gap_mat = np.empty_like(P)
    for i in range(P.shape[0]):
        other = np.delete(P, i, axis=0).max(axis=0)
        gap_mat[i] = P[i] - other
    best_gap_i = gap_mat.argmax(axis=0)
    best_pct_i = P.argmax(axis=0)

    # ---------------- supertype level, siblings within the same parent anchor
    nnz2, ncell2, axis2 = load_level("supertype")
    anchor_body = {a.split(" ", 1)[1]: a for a in roi_of}
    groups: dict[str, list[tuple]] = {}
    for (lab, roi), n in ncell2.items():
        par = parent_of(lab)
        anc = anchor_body.get(par)
        if anc is None or roi_of[anc] != roi or n < MIN_CELLS:
            continue
        groups.setdefault(anc, []).append((lab, roi))
    usable = {a: v for a, v in groups.items() if len(v) >= 2}
    print(f"anchors with >=2 supertypes of >={MIN_CELLS} cells: {len(usable)}/20")

    sup_gap = np.full(len(gsym), np.nan)
    sup_pct = np.full(len(gsym), np.nan)
    sup_nc = np.full(len(gsym), np.nan)
    sup_lbl = np.array([""] * len(gsym), dtype=object)
    sup_par = np.array([""] * len(gsym), dtype=object)
    sup_cache = {}
    for anc, mem in usable.items():
        M = np.vstack([nnz2[k] / ncell2[k] * 100.0 for k in mem])[:, keep_idx]
        sup_cache[anc] = (M, [k[0] for k in mem], [ncell2[k] for k in mem])
        for i, k in enumerate(mem):
            other = np.delete(M, i, axis=0).max(axis=0)
            g = M[i] - other
            better = np.isnan(sup_gap) | (g > sup_gap)
            sup_gap[better] = g[better]
            sup_pct[better] = M[i][better]
            sup_nc[better] = ncell2[k]
            sup_lbl[better] = k[0]
            sup_par[better] = anc

    np.savez_compressed(
        OUT / "anchor_subtype_cache.npz",
        genes=np.array(gsym, dtype=object),
        anchor_pct=P.astype(np.float32),
        anchor_names=np.array(anchor_names, dtype=object),
        anchor_n=np.array([ncell[k] for k in keys]),
        sup_keys=np.array(list(sup_cache), dtype=object),
        **{f"sup_pct__{a}": sup_cache[a][0].astype(np.float32) for a in sup_cache},
        **{f"sup_lab__{a}": np.array(sup_cache[a][1], dtype=object) for a in sup_cache},
        **{f"sup_n__{a}": np.array(sup_cache[a][2]) for a in sup_cache},
    )

    union = sorted(set().union(*panel_genes.values()))
    rows = []
    for g in union:
        j = gi.get(g)
        if j is None:
            rows.append({"gene": g, "scored": False})
            continue
        bi, pi = int(best_gap_i[j]), int(best_pct_i[j])
        rows.append({
            "gene": g,
            "scored": True,
            "anchor_max_pct": round(float(P[pi, j]), 1),
            "anchor_max_name": anchor_names[pi],
            "n_anchors_ge50": int((P[:, j] >= BAR).sum()),
            "median_pct_20": round(float(np.median(P[:, j])), 1),
            "max_pct_ORBm": round(float(P[orb_rows, j].max()), 1),
            "max_pct_BMAp": round(float(P[bma_rows, j].max()), 1),
            "subclass_gap_pp": round(float(gap_mat[bi, j]), 1),
            "subclass_gap_at": anchor_names[bi],
            "subclass_gap_pct_in": round(float(P[bi, j]), 1),
            "supertype_gap_pp": None if np.isnan(sup_gap[j]) else round(float(sup_gap[j]), 1),
            "supertype_gap_pct_in": None if np.isnan(sup_pct[j]) else round(float(sup_pct[j]), 1),
            "supertype_n_cells": None if np.isnan(sup_nc[j]) else int(sup_nc[j]),
            "supertype": sup_lbl[j] or None,
            "supertype_parent": sup_par[j] or None,
            "is_unique_separator": g in sep,
        })
    t = pd.DataFrame(rows)
    for key in PANELS:
        t[f"on_{key}"] = t.gene.isin(panel_genes[key])
    t["n_panels"] = t[[f"on_{k}" for k in PANELS]].sum(axis=1)

    with pd.ExcelWriter(DST) as xw:
        t.to_excel(xw, "gene_scores", index=False)
        pd.DataFrame({"panel": list(PANELS), "n_genes": [len(panel_genes[k]) for k in PANELS],
                      "file": list(PANELS.values())}).to_excel(xw, "panels", index=False)
    print("wrote", DST, len(t), "genes")

    # quick summary
    sc = t[t.scored]
    print("\nunscored (not in Allen axis):", sorted(t[~t.scored].gene))
    print("\nper-panel detection at the 20 anchors:")
    for k in PANELS:
        s = sc[sc[f"on_{k}"]]
        n_un = int((~t.scored & t[f"on_{k}"]).sum())
        print(f"  {k:16} n={len(s)+n_un:4} scored={len(s):4} "
              f"median={s.anchor_max_pct.median():5.1f} "
              f"lt50={int((s.anchor_max_pct < 50).sum()):3} "
              f"lt20={int((s.anchor_max_pct < 20).sum()):3} "
              f"sep={int(s.is_unique_separator.sum()):3} "
              f"unscored={n_un}")


if __name__ == "__main__":
    main()
