"""PI-readable version of the final panel, laid out like the earlier MSGS workbook.

The detailed build workbook (PANEL_FINAL_v9_ORBm_BMAp.xlsx) keeps every metric and
audit trail. This one keeps five columns and a one-screen summary.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
SRC = OUT / "PANEL_FINAL_v9_ORBm_BMAp.xlsx"
REF = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_for_MSGS11122.xlsx")
DST = OUT / "PANEL_FINAL_for_PI.xlsx"

NAVY, BLUE, CREAM, GREY = "1D4E89", "2A6F97", "F4F1EA", "5B6472"

CATEGORY = {
    "01_TRAP_reporter": "TRAP reporter",
    "03_class_EI_backbone": "Cell class (excitatory / inhibitory)",
    "03b_taxonomy_backbone": "Cell type marker",
    "04_nonneuronal_counterstain": "Non-neuronal (glia / vascular)",
    "05_celltype_separator": "Cell type marker",
    "06_subtype_separator": "Sub-type marker",
    "07_IEG_pCREB_target": "Activity (IEG / pCREB)",
    "08_clock_module": "Circadian",
    "09_plasticity": "Synaptic plasticity",
    "10_morphine_state": "Morphine state",
    "11_GPCR_map": "GPCR (receptor map)",
}
ORDER = ["Cell type marker", "Sub-type marker", "Cell class (excitatory / inhibitory)",
         "Non-neuronal (glia / vascular)", "GPCR (receptor map)", "Activity (IEG / pCREB)",
         "TRAP reporter", "Synaptic plasticity", "Circadian", "Morphine state"]


def short(why: str) -> str:
    """One clause, no metric tail - the metrics live in their own column."""
    w = str(why)
    for cut in (" - ", "; ", ": "):
        if cut in w and len(w) > 95:
            w = w.split(cut)[0] if cut != ": " else w
    return w[:150]


def main() -> None:
    d = pd.read_excel(SRC, None)
    m = d["PANEL_ORDER"].copy()
    m["category"] = m.block.map(CATEGORY)
    m["detected_in_pct_of_cells"] = m.anchor_max_pct
    m["what_it_does"] = m.why.map(short)
    m["also_serves"] = (m.roles.str.replace(r"\d_", "", regex=True)
                        .str.replace("_", " ").str.replace("cell type marker, ", ""))
    m["from_Jesse_or_Dan_data"] = (
        m.source_Jesse_morphine_DEG.map({True: "Jesse", False: ""})
        + m.source_Dan_GSE283418.map({True: " Dan", False: ""})).str.strip()

    # 'serves' matches the earlier MSGS workbook: which population or job the gene is
    # bought for, so the sheet reads the same way Mark and Greg are used to.
    def serves(r):
        if r.block == "05_celltype_separator":
            return str(r.subclass_gap_at)
        if r.block == "06_subtype_separator":
            return f"{r.supertype} (inside {r.supertype_parent})"
        if r.block == "04_nonneuronal_counterstain":
            return "non-neuronal exclusion"
        if r.block == "01_TRAP_reporter":
            return "TRAP POST ensemble"
        return r.category
    m["serves"] = m.apply(serves, axis=1)
    m["block"] = m.block.str.replace(r"^\d+b?_", "", regex=True)

    m["_o"] = m.category.map({c: i for i, c in enumerate(ORDER)})
    m = m.sort_values(["_o", "gene"]).reset_index(drop=True)
    m["order_rank"] = range(1, len(m) + 1)
    cols = ["order_rank", "gene", "category", "block", "serves", "what_it_does",
            "detected_in_pct_of_cells", "from_Jesse_or_Dan_data"]
    panel = m[cols]

    TRAP = ["tdTomato", "iCre"]
    orbm = m[(m.max_pct_ORBm.fillna(100) >= 20) | m.gene.isin(TRAP)][cols].copy()
    bmap = m[(m.max_pct_BMAp.fillna(100) >= 20) | m.gene.isin(TRAP)][cols].copy()
    for t in (orbm, bmap):
        t["order_rank"] = range(1, len(t) + 1)

    ac = d["ANCHOR_COVERAGE_20types"]
    types20 = ac.rename(columns={"allen_subclass_anchor": "cell_population",
                                 "n_cells": "Allen_cells",
                                 "n_markers": "markers_on_panel",
                                 "n_unique_vs_all19": "unique_vs_other19",
                                 "n_vs_closest_neighbour": "vs_closest_neighbour",
                                 "closest_neighbour": "closest_neighbour",
                                 "markers": "top_markers",
                                 "neighbour_markers": "markers_vs_closest_neighbour",
                                 "callable": "separable"})
    keep20 = [c for c in [
        "region", "cell_population", "Allen_cells", "unique_vs_other19",
        "vs_closest_neighbour", "closest_neighbour", "top_markers",
        "markers_vs_closest_neighbour", "separable"] if c in types20.columns]
    types20 = types20[keep20]

    cov = d["SUBTYPE_COVERAGE"]
    counts = (m.groupby("category").gene.count().reindex(ORDER)
              .rename("n_genes").reset_index())

    summary = pd.DataFrame([
        ("What to order",
         f"SHARED_PANEL_ORDER - {len(panel)} genes, one shared Xenium panel read from the same "
         f"section for both ORBm and BMAp. tdTomato and iCre are transgene targets and "
         f"need 10x's Advanced Panel Upgrade."),
        ("What the panel does",
         "Calls all 20 Allen cell populations - measured, not assumed. On held-out "
         "cells (125,313 cells, 3 seeds) a classifier using only these genes reaches "
         "0.948 balanced accuracy over the 20 populations, with 18 of 20 above 0.90 "
         "recall. It then resolves all "
         f"{int(cov.n_markers_on_panel.gt(0).sum())} of their {len(cov)} "
         "sub-populations, and on each cell reads out activity, receptors, plasticity "
         "and the morphine state."),
        ("The two populations under 0.90, and why adding genes will not fix them",
         "005 L5 IT (0.72) and 029 L6b (0.76) lose cells to their immediate neighbour, "
         "004 L6 IT and 030 L6 CT. Asked the question that matters - tell this "
         "population apart from the one it is confused with - the panel scores 0.87 "
         "and 0.88. Tripling the gene set from 211 to 608 moves those to 0.89 and "
         "0.89, so the panel is at the ceiling: L5 IT and L6 IT are a transcriptomic "
         "gradient in cortex, not two discrete clusters. Eight pairwise genes "
         "(Kcnk2/Sulf1, Cntn6/Inpp4b, Nxph4/Rprm, Tmem163, Mpped1) were added to "
         "capture what headroom there is."),
        ("How genes were chosen",
         "Every one of 32,245 genes in the Allen whole-mouse-brain atlas was re-scored "
         "in ORBm and BMAp only, on two separate measures: can it SEPARATE a population "
         "from its neighbours, and is it DETECTED in enough cells to be usable. A gene "
         "is on the panel only if it passes one of those for a stated job."),
        ("Why it is not bigger",
         "Caps were set before looking at the result: at most 4 markers per cell "
         "population, 2 per sub-population, one gene per plasticity mechanism, one per "
         "IEG kinetic wave. Genes detected in ~100% of every population with no "
         "contrast were removed - they consume instrument capacity and add nothing."),
        ("Evidence base",
         "Allen WMB-10X, 226,886 ORBm/BMAp cells (124,115 of them inside the 20 target "
         "populations), plus Jesse Niehaus's 5-day escalating-morphine DESeq2 lists for "
         "PL-ILA-ORB and Dan Berg's amygdala spatial panel (GSE283418). Citations in "
         "SOURCES."),
        ("Why 5 glia / vascular genes, and only 5",
         "28.0% of the ORBm/BMAp cells in the Allen atlas are non-neuronal (63,618 of "
         "226,886), and Xenium calls every nucleus on the section, so they cannot be "
         "ignored. But a held-out test on 188,849 cells showed that EXCLUDING them "
         "does not need dedicated probes: neuron-vs-glia balanced accuracy is 0.9998 "
         "with the glial probes and 0.9998 without, because a glial cell is negative "
         "for the ~40 pan-neuronal genes already on the panel. What the probes buy is "
         "NAMING a cluster once found, which needs one marker per population worth "
         "naming. So the set was cut from 8 to 5: Aqp4 astrocyte, Mog "
         "oligodendrocyte, Pdgfra OPC, Csf1r microglia, Cldn5 vessels."),
        ("Two deliberately weak probes",
         "Htr1a (28% of cells) and Nfil3 (20%) were included on request. Htr1a still "
         "separates a 1,330-cell sub-population; Nfil3 is the weakest probe here and "
         "the first to cut if a slot is needed."),
        ("Other sheets",
         "ORBm_ORDER / BMAp_ORDER are the same list filtered to genes visible in that "
         "region. ANCHOR_COVERAGE is the check that every target population is still "
         "callable. CATEGORY_COUNTS is the one-line breakdown."),
    ], columns=["item", "detail"])

    with pd.ExcelWriter(DST, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="FOR_MarkGreg", index=False)
        counts.to_excel(xw, sheet_name="CATEGORY_COUNTS", index=False)
        panel.to_excel(xw, sheet_name="SHARED_PANEL_ORDER", index=False)
        orbm.to_excel(xw, sheet_name="ORBm_ORDER", index=False)
        bmap.to_excel(xw, sheet_name="BMAp_ORDER", index=False)
        types20.to_excel(xw, sheet_name="ANCHOR_COVERAGE", index=False)
        pd.read_excel(REF, "SOURCES").to_excel(xw, sheet_name="SOURCES", index=False)

        wb = xw.book
        hdr = PatternFill("solid", fgColor=NAVY)
        band = PatternFill("solid", fgColor=CREAM)
        thin = Border(bottom=Side("thin", color="D6D3CC"))
        widths = {"FOR_MarkGreg": [30, 118], "CATEGORY_COUNTS": [40, 10],
                  "SHARED_PANEL_ORDER": [10, 13, 33, 24, 34, 82, 12, 20],
                  "ORBm_ORDER": [10, 13, 33, 24, 34, 82, 12, 20],
                  "BMAp_ORDER": [10, 13, 33, 24, 34, 82, 12, 20],
                  "ANCHOR_COVERAGE": [9, 32, 12, 12, 14, 28, 55, 55, 12],
                  "SOURCES": [18, 38, 70, 7, 24, 32, 12, 40, 50, 14, 40]}
        for name, ws in ((n, wb[n]) for n in wb.sheetnames):
            for i, w in enumerate(widths.get(name, []), 1):
                ws.column_dimensions[get_column_letter(i)].width = w
            for c in ws[1]:
                c.fill, c.font = hdr, Font(bold=True, color="FFFFFF", size=11)
                c.alignment = Alignment(vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 26
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    c.border = thin
                    c.alignment = Alignment(
                        vertical="top",
                        wrap_text=name in ("FOR_MarkGreg", "ANCHOR_COVERAGE", "SOURCES"))
            if name == "FOR_MarkGreg":
                for row in ws.iter_rows(min_row=2, max_col=1):
                    row[0].font = Font(bold=True, color=NAVY, size=11)
                for row in ws.iter_rows(min_row=2):
                    ws.row_dimensions[row[0].row].height = 58
            if name in ("SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER"):
                last = None
                shade = False
                for row in ws.iter_rows(min_row=2):
                    cat = row[2].value
                    if cat != last:
                        shade, last = not shade, cat
                    if shade:
                        for c in row:
                            c.fill = band
                    row[1].font = Font(bold=True, color=BLUE, size=11)
                    if isinstance(row[6].value, (int, float)) and row[6].value < 35:
                        row[6].font = Font(color="C44536", size=11)

    print("wrote", DST, len(panel), "genes")
    print(counts.to_string(index=False))
    print(f"\nORBm_ORDER {len(orbm)} | BMAp_ORDER {len(bmap)} | "
          f"types callable {int((ac.callable == 'yes').sum() if 'callable' in ac.columns else (ac.n_markers >= 2).sum())}/20")


if __name__ == "__main__":
    main()
