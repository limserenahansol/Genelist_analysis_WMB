"""Order workbook in the MSGS11122 house format, built from the 297-gene all-20 panel.

Same six sheets, same names, same column order as
FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx:

  FOR_MarkGreg        front page - what to order and the decisions
  SHARED_PANEL_ORDER  order_rank | gene | block | serves | why | max_pct | max_mean | max_spec_panel
  ORBm_ORDER          the same genes, ORBm view
  BMAp_ORDER          the same genes, BMAp view
  ANCHOR_COVERAGE     the 20 target cell types and their markers
  SOURCES             every data source with DOI

Three columns are appended after the reference ones because they carry the argument:
category, what_it_tells_you, named_in_the_SOW. ANCHOR_COVERAGE keeps the reference
columns and appends the measured marker, its detection and its margin.

Output: Downloads/FINAL_Xenium_panel_ORBm_BMAp_297genes.xlsx
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

V3 = Path(__file__).resolve().parents[1]
O = V3 / "outputs"
DL = Path(r"C:\Users\hsollim\Downloads")
SRC = DL / os.environ.get("PANEL_SRC", "PANEL_FINAL_297_ORBm_BMAp_all20.xlsx")
DST = DL / os.environ.get("XLSX_NAME", "FINAL_Xenium_panel_ORBm_BMAp_297genes.xlsx")
NAVY, ICE, INK = "1D4E89", "EAF2F8", "1F2937"

TELLS = {
    "1 cell type": "which of the 20 target cell types this cell is",
    "2 subtype marker": "which sub-population inside that cell type",
    "3 GPCR": "which druggable receptor sits on that cell type",
    "4 plasticity": "synaptic remodelling state of that cell",
    "5 TF": "the identity programme behind the cell type",
    "6 TRAP reporter": "was this cell active during volitional opioid seeking",
    "7 IEG": "how recently the cell fired",
    "8 morphine": "does it carry the morphine-dependence signature (Jesse DEGs)",
    "9 circadian": "circadian clock state - the axis the SOW names with PER2",
}
REF_COLS = ["order_rank", "gene", "block", "serves", "why", "max_pct", "max_mean", "max_spec_panel"]


def main() -> None:
    x = pd.ExcelFile(SRC)
    panel = x.parse("FINAL_GENE_LIST")
    orb, bma = x.parse("ORBm_LIST"), x.parse("BMAp_LIST")
    srcs = x.parse("SOURCES")
    ct = pd.read_csv(O / "_CELL_TYPE_MARKERS_297.csv")
    nn = panel[panel.block == "30_nonneuronal_class"]
    cats = panel.groupby("category").gene.count()
    n20 = int((ct.pct_of_that_type >= 50).sum())
    n20_strict = int((ct.gap_vs_next_target_type_pp >= 20).sum())

    front = pd.DataFrame({"item": [
        "Please look at",
        "What this file is",
        "All 20 target cell types",
        "Sub-populations inside those types",
        "What one cell will tell us",
        "Circadian genes",
        "Non-neuronal probes - kept to the minimum",
        "What was left out, and why",
        "Full evidence",
    ], "detail": [
        "1) SHARED_PANEL_ORDER (the list to order)  2) ORBm_ORDER / BMAp_ORDER  "
        "3) ANCHOR_COVERAGE (every one of the 20 target cell types and the gene that names it)",
        f"Finalised Xenium gene list for ORBm and BMAp: {len(panel)} genes on one shared STANDALONE "
        f"custom panel, read from the same mouse on the same slide. The 10x Mouse Brain base panel is "
        f"not included, so every gene here is a designed probe. "
        + ", ".join(f"{c[2:]} {n}" for c, n in cats.items()) + ".",
        f"{n20} of 20 now have their own positive marker at >=50 pct of that cell type "
        f"({n20_strict} of them also clear a 20 pp margin over the next cell type). The two that do not "
        f"reach 20 pp - 005 L5 IT (Adam19, +17.1 pp) and 073 MEA-BST Sox6 Gaba (Chn2, +14.8 pp) - are at "
        f"the ceiling: no gene in the whole 32,285-gene atlas does better for them. Six markers were "
        f"added for exactly this: Tnnc1, Adam19, Man2a1, Chn2, Frem3, Blnk.",
        "96 of 96 sub-populations that are markable at all have a dedicated marker. This is the level at "
        "which a new TRAP+ population would appear.",
        "Identity, sub-type, which druggable receptors it carries, whether it fired recently (TRAP tag + "
        "IEGs), and whether it carries the morphine-dependence signature - so active and yoked-passive "
        "animals can be compared inside one cell type at the 24 h post-test window.",
        f"{int(cats.get('9 circadian', 0))} core circadian clock genes (Clock, Arntl, Npas2, Cry1, Cry2, "
        f"Per3, Nr1d1, Nr1d2, Dbp, Bhlhe41) on top of Per1/Per2, because the SOW names clock genes as one "
        f"of the three reprogramming readouts. The SOW de-scoped the ZT cohort, so this block is an "
        f"exploratory secondary - it is one block and can be deleted.",
        f"{len(nn)} probes only: {', '.join(sorted(nn.gene))}. Measured: with no glial or vascular probe "
        f"at all, non-neuronal cells are still never called neurons (0.0 pct) and contamination of the 20 "
        f"target types stays at 0.01 pct, because every neuronal gene on the panel reads ~zero in them. "
        f"Dropping all eight cost 0.1-3.4 pp of per-class recall, so only these two positive markers for "
        f"the two largest non-neuronal classes were kept.",
        "103 candidates were rejected with their measured numbers: 65 detected in under half the cells of "
        "any population we image, 30 redundant with a gene already on the list, 10 of 10 published "
        "markers that failed when re-tested in the Allen cells, 4 sex-determination genes (excluded on "
        "request).",
        f"{SRC.name} - per-gene numbers, GPCR-by-cell-type map with drug annotation, published-claim "
        f"audit, sub-population coverage, benchmarks, optical-load and capture-rate tests, and this panel "
        f"scored against all earlier versions.",
    ]})

    def order_sheet(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        if "category" not in d.columns:
            d = d.merge(panel[["gene", "category", "allen_pct_own_population", "allen_own_population",
                               "allen_mean_log2_own_population", "sow_named"]], on="gene", how="left")
        out = pd.DataFrame({
            "order_rank": range(1, len(d) + 1),
            "gene": d.gene.values,
            "block": d.block.values,
            "serves": d.serves.values,
            "why": d.why.values,
            "max_pct": d.allen_pct_own_population.values,
            "max_mean": d.allen_mean_log2_own_population.values,
            "max_spec_panel": d.allen_own_population.values,
            "category": d.category.values,
            "what_it_tells_you": d.category.map(TELLS).values,
            "named_in_the_SOW": d.sow_named.values,
        })
        return out

    anchor = pd.DataFrame({
        "region": ct.region,
        "cell_type_label": ct.cell_type_label,
        "allen_subclass_anchor": ct.allen_subclass_anchor,
        "n_cells": ct.n_cells,
        "unique_separators_on_region_panel": ct.backup_markers_on_panel,
        "unique_separators_on_shared_panel": ct.best_marker_on_panel,
        "marker_detection_pct_in_that_type": ct.pct_of_that_type,
        "margin_over_next_cell_type_pp": ct.gap_vs_next_target_type_pp,
        "callable": ["yes" if p >= 50 else "combination only" for p in ct.pct_of_that_type],
    })

    sheets = {"FOR_MarkGreg": front, "SHARED_PANEL_ORDER": order_sheet(panel),
              "ORBm_ORDER": order_sheet(orb), "BMAp_ORDER": order_sheet(bma),
              "ANCHOR_COVERAGE": anchor, "SOURCES": srcs}
    with pd.ExcelWriter(DST, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, name, index=False)

    wb = load_workbook(DST)
    thin = Side(style="thin", color="D5D9DE")
    for name in sheets:
        ws = wb[name]
        ws.freeze_panes = "A2"
        ws.sheet_view.showGridLines = False
        for c in ws[1]:
            c.font = Font(name="Calibri", size=10.5, bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=NAVY)
            c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = 28
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.font = Font(name="Calibri", size=10, color=INK)
                c.alignment = Alignment(vertical="top", wrap_text=True)
                c.border = Border(bottom=thin)
    f = wb["FOR_MarkGreg"]
    f.column_dimensions["A"].width = 36
    f.column_dimensions["B"].width = 122
    for r in range(2, f.max_row + 1):
        f.cell(r, 1).font = Font(name="Calibri", size=10, bold=True, color=NAVY)
    for c in (1, 2):
        f.cell(2, c).fill = PatternFill("solid", fgColor=ICE)
    for name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
        ws = wb[name]
        for i, wd in enumerate((7, 12, 26, 42, 74, 9, 10, 28, 18, 44, 11), start=1):
            ws.column_dimensions[get_column_letter(i)].width = wd
        for r in range(2, ws.max_row + 1):
            v = ws.cell(r, 6).value
            if isinstance(v, (int, float)):
                ws.cell(r, 6).number_format = "0.0"
                ws.cell(r, 6).fill = PatternFill(
                    "solid", fgColor="E8F0E6" if v >= 70 else ("FDF3E7" if v >= 50 else "FBE9E7"))
            if isinstance(ws.cell(r, 7).value, (int, float)):
                ws.cell(r, 7).number_format = "0.00"
    ws = wb["ANCHOR_COVERAGE"]
    for i, wd in enumerate((9, 34, 30, 9, 54, 22, 14, 14, 16), start=1):
        ws.column_dimensions[get_column_letter(i)].width = wd
    for r in range(2, ws.max_row + 1):
        ws.cell(r, 7).number_format = "0.0"
        ws.cell(r, 8).number_format = "0.0"
        ws.cell(r, 6).font = Font(name="Calibri", size=10, bold=True, color=NAVY)
        g = ws.cell(r, 8).value
        ws.cell(r, 8).fill = PatternFill("solid", fgColor="E8F0E6" if g >= 20 else "FDF3E7")
    ws = wb["SOURCES"]
    for i, wd in enumerate((18, 24, 60, 8, 20, 26, 12, 30, 70, 14, 60), start=1):
        ws.column_dimensions[get_column_letter(i)].width = wd
    wb.save(DST)
    print(f"wrote {DST}")
    for n, d in sheets.items():
        print(f"  {n:20s} {d.shape}")
    print(f"  cell types with their own marker: {n20}/20  ({n20_strict} at >=20pp)")


if __name__ == "__main__":
    main()
