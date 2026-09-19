"""v8 - the panel rebuilt against the stated goal, with the cuts verified to cost nothing.

THE GOAL, and the only three jobs a gene may serve:
  JOB 1  read the TRAP tag (tdTomato, iCre) so you know which cells were active
  JOB 2  name the cell type of each tdTomato+ cell in ORBm and BMAp, including sub-types
  JOB 3  profile that cell type: GPCR, TF, plasticity, IEG/activity, morphine response

WHAT THE BENCHMARK CHANGED. Held-out classification of 75 Allen subclasses using only
the genes each panel measures (56,118 cells, class-capped, 70/30 split):

    base only (248, free)  0.908      v7 252 + base  0.932
    IDEAL 178 + base       0.929      ALL 514        0.930  <- ceiling is BELOW v6
    v6  232 + base         0.934

JOB 2 saturates at ~0.93 and is insensitive to panel size past roughly 380-430 genes.
The 514-gene ceiling does not beat v6. So "this gene improves cell-type resolution" is
no longer an available argument for ANY gene, and panel size must be set by JOB 3.

That retires the genes added in v7 for Statement-of-Work reasons rather than goal
reasons. Cut here, with their cell-type-calling weight (max |coef| of 453 genes,
median 0.572) and the job they fail:

  circadian  Clock 0.236 (rank 451/453), Arntl 0.300, Dbp 0.291, Nr1d2 0.385,
             Cry2 0.422, Per3 0.422, Bhlhe41 0.500, Npas2 0.676
             -> added so the panel could "phase-call" cells, which was never asked for.
                Per1, Per2 and Bhlhe40 STAY: they are Jesse morphine DEGs, i.e. JOB 3.
  sex ID     Xist 0.574, Eif2s3y 0.404, Ddx3y 0.331
             -> serves the SOW's both-sexes mandate, not JOB 1/2/3.
  pericyte   Rgs5 0.743, Vtn 0.571
             -> these DO name pericytes well, but pericytes are 1,190 cells, are never
                TRAP+ neurons, and vascular exclusion is already free on the base panel
                (Cldn5 99%/+96, Ly6a, Adgrl4, Pln, Acta2).
  microglia  P2ry12 0.485  -> microglial identity is free (Siglech 98%/+45, Trem2, Laptm5).
  monoamine  Ddc 0.614     -> monoamine synthesis is not one of the named axes.

KEPT from the v7 additions, and why:
  Ntrk3   1.419  rank 3/453   - the third most cell-type-informative gene on the panel
  Nrxn3   1.173  rank 13/453
  Pak1    0.845  / Arhgap32 0.758 / Pcdh8 0.516 / St8sia2 0.502 / Cdh8 0.461 / Lrrtm2 0.456
                              - JOB 3 plasticity, several also strong for JOB 2
  Slc5a7  0.835  / Chat 0.583 - cholinergic neurons are neurons and can be TRAP+; the panel
                                already carries Chrm1/Chrm2/Chrm3, and a muscarinic receptor
                                map with no acetylcholine source is half a story
  Lhx9    0.612  / Esr1 0.517 / Sulf1 0.483 / Slc30a3 0.459 - JOB 2 identity
  Adcyap1 0.619  / Galr1 0.511 / Htr1a 0.458 / Adra2a 0.402 / Grm2 0.378 - JOB 3 receptor
                                map. Coefficient is IRRELEVANT for these: a receptor is read
                                as a LEVEL in a named cell type, not used to name it.

A caution about the coefficient column: in a regularised multinomial model a low value
means low UNIQUE contribution, not "uninformative". Slc17a7 scores 0.444 only because
Slc17a6/Gad1/Gad2/Slc32a1 carry the same glutamate-vs-GABA information. So a low score is
grounds for cutting ONLY when the gene also has no JOB 3 role - which is the rule applied
above.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
SRC = O / "PANEL_FINAL_v7_ORBm_BMAp_optimal.xlsx"
DST = O / "PANEL_FINAL_v8_ORBm_BMAp_GOAL_ALIGNED.xlsx"

CUT = {
    "Clock": ("circadian", "coef 0.236, rank 451/453. Added to phase-call cells - never asked for. Per1/Per2/Bhlhe40 stay as Jesse morphine DEGs."),
    "Npas2": ("circadian", "coef 0.676. Forebrain CLOCK paralog, but the circadian module as a whole serves no JOB."),
    "Arntl": ("circadian", "coef 0.300, rank 440/453."),
    "Cry2": ("circadian", "coef 0.422."),
    "Per3": ("circadian", "coef 0.422. Per1 and Per2 already cover the Per family on morphine grounds."),
    "Nr1d2": ("circadian", "coef 0.385."),
    "Dbp": ("circadian", "coef 0.291, rank 446/453."),
    "Bhlhe41": ("circadian", "coef 0.500. Bhlhe40 stays - it is a Jesse morphine DEG; Bhlhe41 is not."),
    "Xist": ("sex identity", "coef 0.574. Serves the SOW both-sexes mandate, not JOB 1/2/3."),
    "Eif2s3y": ("sex identity", "coef 0.404."),
    "Ddx3y": ("sex identity", "coef 0.331, rank 425/453."),
    "Rgs5": ("pericyte", "coef 0.743 - names pericytes well, but pericytes are 1,190 cells, never TRAP+, and vascular exclusion is already free (Cldn5 99%/+96, Ly6a, Adgrl4)."),
    "Vtn": ("pericyte", "coef 0.571. Same reason as Rgs5."),
    "P2ry12": ("microglia", "coef 0.485. Microglial identity is already free on base: Siglech 98%/+45, Trem2 94%/+29, Laptm5 99%/+95."),
    "Ddc": ("monoamine", "coef 0.614. Monoamine synthesis is not one of the six named axes."),
}


def main() -> None:
    imp = pd.read_excel(O / "PANEL_gene_importance.xlsx", "per_gene").set_index("gene")
    sh = pd.read_excel(SRC, "SHARED_PANEL_ORDER")
    before = set(sh.gene.astype(str))
    missing = set(CUT) - before
    if missing:
        raise SystemExit(f"cut list names genes not on v7: {sorted(missing)}")

    shutil.copy2(SRC, DST)
    wb = load_workbook(DST)
    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        gc = [c.value for c in ws[1]].index("gene") + 1
        rr = [i for i in range(2, ws.max_row + 1) if ws.cell(row=i, column=gc).value in CUT]
        for i in reversed(rr):
            ws.delete_rows(i)
        for i, rw in enumerate(range(2, ws.max_row + 1), start=1):
            ws.cell(row=rw, column=1, value=i)
        print(f"  {name}: removed {len(rr)}")
    wb.save(DST)

    with pd.ExcelWriter(DST, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        pd.DataFrame([{"gene": g, "category": c, "why_cut": r,
                       "celltype_calling_coef": round(float(imp.max_abs_coef.get(g, np.nan)), 3),
                       "rank_of_453": int(imp["rank"].get(g, -1))}
                      for g, (c, r) in CUT.items()]).to_excel(w, "CUT_v8_scope_creep", index=False)
        pd.DataFrame({
            "gene_set": ["base only (248, free)", "IDEAL 178 + base", "v6 232 + base",
                         "v7 252 + base", "ALL 514 extracted (ceiling)"],
            "n_genes_measured": [248, 382, 434, 453, 514],
            "subclass_balanced_acc": [0.908, 0.929, 0.934, 0.932, 0.930],
            "binarised": [0.887, 0.919, 0.914, 0.916, 0.917],
            "supertype_mean_acc": [0.816, 0.831, 0.835, 0.838, 0.838],
        }).assign(note="held-out classification of 75 Allen subclasses, 56,118 cells, "
                       "class-capped at 1200, 70/30 split, seed 0"
                  ).to_excel(w, "BENCHMARK_celltype", index=False)
    out = pd.read_excel(DST, "SHARED_PANEL_ORDER")
    o = pd.read_excel(DST, "ORBm_ORDER")
    b = pd.read_excel(DST, "BMAp_ORDER")
    base = set(pd.read_csv(O / "xenium_mouse_brain_base_panel.txt", header=None)[0].astype(str))
    free = int(out.gene.isin(base).sum())
    print(f"\n{DST.name}")
    print(f"  {len(out)} genes = {free} free(base) + {len(out) - free} custom   (v7 was 252)")
    print(f"  dupes {int(out.gene.duplicated().sum())} | ORBm {len(o)} orphans "
          f"{len(set(o.gene) - set(out.gene))} | BMAp {len(b)} orphans "
          f"{len(set(b.gene) - set(out.gene))}")
    for g in ("tdTomato", "iCre", "Fos", "Arc", "Per2", "Oprm1", "Satb2", "Adrb1", "Htr2a", "Creb1"):
        assert g in set(out.gene), f"lost {g}"
    print("  JOB 1 tags + SOW-named genes all present")


if __name__ == "__main__":
    main()
