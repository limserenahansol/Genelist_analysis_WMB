"""Pure gene selection: how many genes does naming a TRAP+ cell's type actually take?

No platform assumptions. No free-vs-custom, no base panel, no 100-gene cap. The
question is only: which genes must be measured to do the three jobs.

  JOB 1  read the TRAP tag (tdTomato, iCre)
  JOB 2  name the cell type of each tdTomato+ cell in ORBm and BMAp, incl. sub-types
  JOB 3  profile that cell type: GPCR, TF, plasticity, IEG/activity, morphine response

This script answers JOB 2 empirically. It ranks all 514 measured genes by their
contribution to a multinomial classifier over the 75 Allen subclasses present in
PL-ILA-ORB + sAMY, then evaluates cumulative top-K subsets to find where accuracy
plateaus. The plateau point IS the answer to "how many cell-type genes do I need",
and the gene list at that point is the JOB 2 core.

Ranking uses coefficients from a model fitted on the TRAINING split only, and every
evaluation is on held-out cells, so the curve is not fitted on its own test data.

JOB 3 genes are NOT selected here. They are chosen on function (a receptor is read as
a level inside a named cell type, not used to name it) and a low classifier weight is
expected and correct for them.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from panel_celltype_classification import MIN_CELLS, load, subsample

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
KS = [10, 20, 30, 40, 50, 65, 80, 100, 120, 150, 180, 220, 260, 300, 360, 430, 514]
SEEDS = [0, 1, 2]


def main() -> None:
    X, genes, md = load()
    keep = md.subclass.map(md.subclass.value_counts()) >= MIN_CELLS
    y_all = md.subclass[keep].to_numpy()
    X_all = X[keep.to_numpy()]
    sel = subsample(y_all)
    y, Xk = y_all[sel], X_all[sel]
    print(f"{Xk.shape[0]:,} cells x {Xk.shape[1]} genes, {len(set(y))} subclasses\n", flush=True)

    rows, ranked_by_seed = [], {}
    for seed in SEEDS:
        tr_i, te_i = train_test_split(np.arange(len(y)), test_size=0.3,
                                      random_state=seed, stratify=y)
        sc = StandardScaler().fit(Xk[tr_i])
        Xtr, Xte = sc.transform(Xk[tr_i]), sc.transform(Xk[te_i])
        # rank on TRAIN only - never on the cells used to score
        rank_clf = LogisticRegression(max_iter=1000, n_jobs=-1).fit(Xtr, y[tr_i])
        imp = np.abs(rank_clf.coef_).max(axis=0)
        order = np.argsort(-imp)
        ranked_by_seed[seed] = [genes[i] for i in order]
        print(f"seed {seed}: ranked; top 10 = {', '.join(genes[i] for i in order[:10])}", flush=True)
        for k in KS:
            cols = order[:k]
            clf = LogisticRegression(max_iter=1000, n_jobs=-1).fit(Xtr[:, cols], y[tr_i])
            acc = balanced_accuracy_score(y[te_i], clf.predict(Xte[:, cols]))
            rows.append({"seed": seed, "k": k, "balanced_acc": acc})
            print(f"   k={k:4d}  acc={acc:.4f}", flush=True)

    d = pd.DataFrame(rows)
    curve = d.groupby("k").balanced_acc.agg(["mean", "std"]).reset_index()
    curve.columns = ["n_genes", "mean_balanced_acc", "sd"]
    best = curve.mean_balanced_acc.max()
    curve["pct_of_max"] = (curve.mean_balanced_acc / best * 100).round(1)
    print("\n=== JOB 2 saturation curve ===")
    print(curve.to_string(index=False))

    # smallest k reaching 99% and 99.5% of the achievable maximum
    for thr in (0.98, 0.99, 0.995):
        hit = curve[curve.mean_balanced_acc >= best * thr]
        if len(hit):
            print(f"  {thr*100:.1f}% of max ({best*thr:.4f}) reached at "
                  f"{int(hit.n_genes.iloc[0])} genes", flush=True)

    # consensus JOB 2 core: mean rank across seeds
    pos = {g: [] for g in genes}
    for seed, lst in ranked_by_seed.items():
        for i, g in enumerate(lst):
            pos[g].append(i)
    core = (pd.DataFrame({"gene": list(pos), "mean_rank": [np.mean(v) for v in pos.values()]})
            .sort_values("mean_rank").reset_index(drop=True))
    core["consensus_rank"] = core.index + 1

    with pd.ExcelWriter(O / "PURE_gene_selection.xlsx", engine="openpyxl") as w:
        pd.DataFrame({"item": ["Question", "Method", "What the curve means", "What it excludes"],
                      "detail": [
            "How many genes, and which, are needed to NAME the cell type of a cell in "
            "ORBm/BMAp. No platform assumptions - not a Xenium panel, just genes.",
            "Genes ranked by max |coefficient| of a multinomial logistic classifier fitted on "
            "the TRAINING split only; cumulative top-K subsets then scored on held-out cells. "
            "3 seeds, class-capped at 1200 cells, 75 subclasses.",
            "Where the curve flattens is the number of cell-type genes that are actually "
            "needed. Beyond it, extra genes do not improve naming the cell type.",
            "JOB 3 genes (GPCR, TF, plasticity, IEG, morphine) are NOT selected by this curve. "
            "They are read as levels inside a named cell type, so a low classifier weight is "
            "expected and is not evidence against them.",
        ]}).to_excel(w, "READ_ME", index=False)
        curve.to_excel(w, "saturation_curve", index=False)
        core.to_excel(w, "consensus_ranking", index=False)
        d.to_excel(w, "raw", index=False)
    print(f"\nwrote {O / 'PURE_gene_selection.xlsx'}")


if __name__ == "__main__":
    main()
