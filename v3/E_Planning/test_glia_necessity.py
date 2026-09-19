"""Do the 8 non-neuronal probes earn their slots? A held-out cell-level test.

The question is not whether glia exist. It is whether, on a Xenium section where every
nucleus gets called and 28% of them are non-neuronal, the panel can tell a glial cell
from a neuron WITHOUT dedicated glial probes. If it can, the 8 slots are waste.

Design
  unit          single cell, Allen WMB-10X, ORBm and BMAp only
  split         70/30 stratified by subclass, 3 seeds, fixed seeds 0/1/2
  task A        binary, neuron vs non-neuron - the exclusion step itself
  task B        7-way, which non-neuronal class - needed to know what you excluded
  conditions    FULL panel  vs  panel MINUS the 8 glial probes (everything else equal)
  baseline      a size-matched control that removes 8 RANDOM non-glial panel genes,
                so the comparison is not just "8 fewer genes"
  metric        balanced accuracy, plus the false-neuron rate: the fraction of glial
                cells that get called a neuron, which is the number that actually
                corrupts a neuronal cluster
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import train_test_split

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DST = OUT / "GLIA_NECESSITY_TEST.xlsx"

GLIA = ["Gja1", "Aqp4", "Pdgfra", "Mog", "Csf1r", "Cldn5", "Rgs5", "Dcn"]
NN_PREFIX = ("318 Astro", "319 Astro", "320 Astro", "321 Astro", "326 OPC", "327 Oligo",
             "330 VLMC", "331 Peri", "332 SMC", "333 Endo", "334 Micro", "335 BAM",
             "323 Ependymal", "328 OEC", "329 ABC", "336 Mono", "338 Lymphoid")
GROUP = {"Astro": "Astrocyte", "OPC": "OPC", "Oligo": "Oligodendrocyte",
         "Micro": "Microglia", "Endo": "Endothelium", "Peri": "Mural", "SMC": "Mural",
         "VLMC": "VLMC", "BAM": "BAM"}


def load_cells(panel: set[str]):
    """Union the 7 extraction runs, which hold the same cells with different genes."""
    cols, index = {}, None
    for d in sorted(Path(OUT).glob("allen_extract*")):
        if not (d / "").is_dir():
            continue
        Xs, ids, subs, gg = [], [], [], None
        for f in sorted(d.glob("*.npz")):
            z = np.load(f, allow_pickle=True)
            if "X" not in z.files:
                continue
            gg = [str(x) for x in z["genes"]]
            Xs.append(z["X"])
            ids.append([str(x) for x in z["cell"]])
            subs.append([str(x) for x in z["subclass"]])
        if not Xs:
            continue
        X = np.vstack(Xs)
        cid = np.concatenate(ids)
        sub = np.concatenate(subs)
        keep = [i for i, g in enumerate(gg) if g in panel and g not in cols]
        if index is None:
            index = pd.Index(cid)
            meta = pd.Series(sub, index=cid)
        for i in keep:
            cols[gg[i]] = pd.Series(X[:, i], index=cid).reindex(index).values
    return pd.DataFrame(cols, index=index), meta.reindex(index)


def run(X, y, feats, seed):
    tr, te = train_test_split(np.arange(len(y)), test_size=0.3, random_state=seed,
                              stratify=y)
    m = LogisticRegression(max_iter=400, n_jobs=-1, C=1.0)
    m.fit(X[np.ix_(tr, feats)], y[tr])
    p = m.predict(X[np.ix_(te, feats)])
    return y[te], p


def main() -> None:
    panel = set(pd.read_excel(OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx", "PANEL_ORDER").gene)
    df, sub = load_cells(panel)
    print(f"cells {len(df):,} | panel genes recovered {df.shape[1]} of {len(panel)}")
    have_glia = [g for g in GLIA if g in df.columns]
    print(f"glial probes available in the cell matrix: {have_glia}")

    isnn = sub.str.startswith(NN_PREFIX)
    def grp(s):
        for k, v in GROUP.items():
            if k in s:
                return v
        return "other"
    nn_group = sub[isnn].map(grp)

    keep_cells = isnn | sub.isin(set(pd.read_excel(
        OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx",
        "ANCHOR_COVERAGE_20types").allen_subclass_anchor))
    d = df[keep_cells].fillna(0.0)
    lab = np.where(isnn[keep_cells], "non-neuronal", "neuron")
    X = d.values.astype(np.float32)
    genes = list(d.columns)
    gi = {g: i for i, g in enumerate(genes)}
    print(f"test set: {len(d):,} cells, {(lab=='non-neuronal').sum():,} non-neuronal "
          f"({100*(lab=='non-neuronal').mean():.1f}%)")

    full = list(range(len(genes)))
    noglia = [i for g, i in gi.items() if g not in have_glia]
    rng = np.random.default_rng(0)

    rows = []
    for seed in (0, 1, 2):
        ctrl = sorted(rng.choice(noglia, len(genes) - len(have_glia), replace=False))
        for name, feats in [("FULL panel", full),
                            ("minus the 8 glial probes", noglia),
                            ("minus 8 RANDOM non-glial genes (size-matched control)",
                             ctrl)]:
            yt, yp = run(X, lab, feats, seed)
            nn = yt == "non-neuronal"
            rows.append({
                "condition": name, "n_features": len(feats), "seed": seed,
                "balanced_accuracy": round(balanced_accuracy_score(yt, yp), 4),
                "glia_called_NEURON_pct": round(100 * (yp[nn] == "neuron").mean(), 2),
                "neurons_called_glia_pct": round(
                    100 * (yp[~nn] == "non-neuronal").mean(), 2),
            })
    binary = pd.DataFrame(rows)
    agg = (binary.groupby(["condition", "n_features"])
           .agg(bal_acc_mean=("balanced_accuracy", "mean"),
                bal_acc_sd=("balanced_accuracy", "std"),
                glia_called_neuron_pct=("glia_called_NEURON_pct", "mean"),
                glia_called_neuron_sd=("glia_called_NEURON_pct", "std"))
           .reset_index().sort_values("bal_acc_mean", ascending=False))

    # ---- task B: which non-neuronal class
    dn = df[isnn].fillna(0.0)
    Xn = dn.values.astype(np.float32)
    yn = nn_group.values
    ok = pd.Series(yn).value_counts()
    keep = pd.Series(yn).isin(ok[ok >= 200].index).values
    Xn, yn = Xn[keep], yn[keep]
    gin = {g: i for i, g in enumerate(dn.columns)}
    rows = []
    for seed in (0, 1, 2):
        for name, feats in [("FULL panel", list(range(Xn.shape[1]))),
                            ("minus the 8 glial probes",
                             [i for g, i in gin.items() if g not in have_glia])]:
            yt, yp = run(Xn, yn, feats, seed)
            r = {"condition": name, "seed": seed,
                 "balanced_accuracy": round(balanced_accuracy_score(yt, yp), 4)}
            for c in sorted(set(yn)):
                m = yt == c
                r[c] = round(100 * (yp[m] == c).mean(), 1)
            rows.append(r)
    multi = pd.DataFrame(rows)
    magg = multi.drop(columns="seed").groupby("condition").mean().reset_index()

    with pd.ExcelWriter(DST) as xw:
        agg.to_excel(xw, sheet_name="A_neuron_vs_glia_summary", index=False)
        binary.to_excel(xw, sheet_name="A_per_seed", index=False)
        magg.to_excel(xw, sheet_name="B_which_glial_class", index=False)
        multi.to_excel(xw, sheet_name="B_per_seed", index=False)

    pd.set_option("display.width", 300)
    print("\nTASK A - neuron vs non-neuron, 3 seeds, held-out 30%")
    print(agg.to_string(index=False))
    print("\nTASK B - recall per non-neuronal class (%)")
    print(magg.to_string(index=False))
    print("\nwrote", DST)


if __name__ == "__main__":
    main()
