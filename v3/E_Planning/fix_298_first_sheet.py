"""Rewrite the first sheet of the 298-gene workbook - the one the email points at.

The 298 workbook was copied from the original house-format file, so its FOR_MarkGreg
sheet still carried the pre-correction text. Three things in it were wrong or unsafe:

  "297 genes"                 stale after Adora2a.
  "96 of 96 sub-populations"  this is selection-data coverage, not validation: the genes
                              were chosen to maximise that metric and then scored on the
                              same data. Hansol flagged this himself. Replaced with the
                              held-out numbers, which are not circular.
  "18 of 20 clear a 20 pp     true only against the other 19 target types. Against all 74
   margin over the next        other cell types in the section only 4 do. The competitor
   cell type"                  set has to be named or the claim will not survive a
                              question. Now stated both ways.

Also folded in, because they were missing: held-out recall per target type, the 94/94
pairwise separability result, the genome-wide GPCR/TF completeness check, the cell-type-
name trap (Sox6), and the confirmed reporter line (Ai14, so no open question remains).
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

F = Path(r"C:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_298genes_FINAL.xlsx")
NAVY, RED = "1D4E89", "C44536"

ROWS = [
    ("Please look at",
     "This sheet first, then SHARED_PANEL_ORDER - that is the list to order. "
     "ORBm_ORDER / BMAp_ORDER are the same genes annotated per region. ANCHOR_COVERAGE "
     "has each of the 20 target cell types with its held-out recall. MARKERS_PER_TYPE "
     "lists every dedicated marker and its margin. A one-page version of the gene list "
     "is attached separately as a PowerPoint if you just want to scan the names."),
    ("What this file is",
     "Finalised Xenium gene list for ORBm and BMAp: 298 genes on one shared STANDALONE "
     "custom panel, read from the same mouse on the same slide. The 10x Mouse Brain base "
     "panel is not included, so every gene here is a probe we are ordering."),
    ("ONE GENE ADDED SINCE THE 297 VERSION", None),   # filled from the existing row
    ("How well the 20 target cell types are called",
     "Measured on held-out cells, not asserted: all 20 are recovered with a mean recall of "
     "0.922, and 18 of the 20 are at or above 0.85. Per-type recall is in ANCHOR_COVERAGE. "
     "The two below are 004 L6 IT (0.708) and 005 L5 IT (0.694); their errors are almost "
     "entirely internal to the IT family - 99.4% and 99.7% of misassigned cells are still "
     "called an IT type, and only 1 cell in 360 leaves IT. IT neurons form a continuous "
     "gradient across cortical layers, so no gene in the atlas separates them cleanly, but "
     "in Xenium the layer is set by cortical depth rather than by transcript."),
    ("Dedicated markers per cell type - and the competitor set, which matters",
     "Each of the 20 types has 3 to 28 dedicated markers, median 6, measured against the "
     "other target types IN THE SAME REGION: ORBm and BMAp sit at different places on the "
     "slide and are separated by coordinate before any gene is read. Stated against all 74 "
     "other cell types in the section instead, only 4 of 20 clear a 20-point margin - so "
     "always say which comparison you mean. The honest headline is the held-out recall "
     "above, because cell types are called from gene combinations, not one marker at a "
     "time."),
    ("Every pair of target types can be told apart",
     "All 94 same-region pairs of target cell types (66 in ORBm, 28 in BMAp) have at least "
     "one panel gene whose detection differs by 20 percentage points or more. 94 of 94. The "
     "hardest pair is L4/5 IT versus L5 IT, separated by Cux2 at 67% versus 11% - a 56-point "
     "gap, so even the worst case has nearly three times the required margin."),
    ("Receptors and transcription factors are complete, and how we know",
     "All 426 curated mouse GPCRs and all 1,321 transcription factors were scored in these "
     "two regions. No GPCR reaches 50% of cells in one of the 20 target types with a "
     "10-point margin and is absent from this panel, and none of the 50 GPCRs we carry is "
     "an empty map. Only two transcription factors came close (Bcl6, Lhx5) and both are "
     "weaker duplicates of markers those types already have. Note the scope: that sweep "
     "filtered to genes strong inside the 20 targets, which is why a separate cross-check "
     "against the IUPHAR drug table was needed to surface Adora2a."),
    ("A note on cell-type names - they can mislead",
     "An Allen cell-type name says a gene is expressed there, not that it is exclusive to "
     "it. 073 MEA-BST Sox6 Gaba is the clearest case: Sox6 is 58% in that type but 95% in "
     "Pvalb Gaba and 90% in Sst Gaba, because it marks the whole MGE interneuron lineage. "
     "Sox6 is on the panel and useful as a lineage gene, but the dedicated separators for "
     "073 are Prox1 (+35pp), Dlx1 (+31pp) and Chn2 (+24pp)."),
    ("What one cell will tell us",
     "Its identity and sub-type, which druggable receptors it carries, whether it fired "
     "recently (the TRAP tag plus the immediate-early genes), and whether it carries the "
     "morphine-dependence signature - so active and yoked animals can be compared within "
     "the same cell type rather than across whole regions."),
    ("Circadian genes",
     "Ten core clock genes (Clock, Arntl, Npas2, Cry1, Cry2, Per3, Nr1d1, Nr1d2, Dbp, "
     "Bhlhe41) on top of Per1 and Per2, which are also morphine-regulated in the "
     "collaborator data."),
    ("Non-neuronal probes - kept to the minimum",
     "Two only: Aqp4 and Siglech. Measured: with no glial or vascular probe at all, "
     "non-neuronal cells are still never called neurons (0.0%) and contamination of the 20 "
     "target types is 0.01%, so more would be wasted slots."),
    ("What was left out, and why",
     "Candidates were rejected with their measured numbers: detected in under half the "
     "cells of any population we image, or redundant with a gene already on the list. Ten "
     "widely cited published markers were tested here and rejected - Cux1, Scnn1a, Crym, "
     "Tcf4, Reln, Pax6, Tshz1, Cd36, Fst, Whrn. Four of those point the wrong way: Cd36 is "
     "highest in macrophages and only 28% in the BMA type it supposedly marks, Scnn1a is "
     "1.8% in L4/5 and is really ependymal, Cux1 is higher in amygdala GABA (94%) than in "
     "L2/3 (72%), and Tcf4 is expressed in all 75 cell types. No sex-identity genes."),
    ("Tissue and cohort",
     "TRAP mice: Fos2A-iCreER (JAX 030323) crossed to Ai14 (Rosa26-CAG-LSL-tdTomato, JAX "
     "007908 / 007914). Ai14 is a confirmed tdTomato reporter, so the tdTomato probe reads "
     "the TRAP label directly - no open question here. Cohort: 2 active and 2 passive "
     "morphine animals, extending to 3 + 3 if a third per group is needed."),
    ("Full evidence",
     "PANEL_FINAL_297_ORBm_BMAp_all20.xlsx carries the per-gene numbers, the GPCR-by-cell-"
     "type map with drug annotation, the published-claim audit, benchmarks and optical-load "
     "figures. GENOMEWIDE_GPCR_TF_SCREEN.xlsx carries the receptor and factor sweep."),
]


def main() -> None:
    wb = load_workbook(F)
    ws = wb["FOR_MarkGreg"]
    # keep the Adora2a paragraph already written into the sheet
    adora = next((str(ws.cell(row=r, column=2).value)
                  for r in range(1, ws.max_row + 1)
                  if ws.cell(row=r, column=1).value
                  and "ADORA2A" in str(ws.cell(row=r, column=1).value).upper()
                  or (ws.cell(row=r, column=2).value
                      and "Adora2a, bringing the panel to 298"
                      in str(ws.cell(row=r, column=2).value))), None)
    if adora is None:
        raise SystemExit("could not find the Adora2a row to carry over")

    ws.delete_rows(1, ws.max_row)
    ws.cell(row=1, column=1, value="item").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=1, column=2, value="detail").font = Font(bold=True, color="FFFFFF")
    for c in (1, 2):
        ws.cell(row=1, column=c).fill = PatternFill("solid", fgColor=NAVY)
    for i, (item, detail) in enumerate(ROWS, start=2):
        if detail is None:
            detail = adora
        ws.cell(row=i, column=1, value=item).font = Font(
            bold=True, color=RED if "ADDED" in item else NAVY)
        ws.cell(row=i, column=2, value=detail)
        for c in (1, 2):
            ws.cell(row=i, column=c).alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[i].height = 96
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 120
    ws.freeze_panes = "A2"
    wb.save(F)
    print(f"rewrote FOR_MarkGreg: {len(ROWS)} rows")
    import pandas as pd
    d = pd.read_excel(F, "FOR_MarkGreg")
    bad = [str(r.detail)[:60] for r in d.itertuples()
           if "297 genes" in str(r.detail) or "96 of 96" in str(r.detail)
           or "Ai19" in str(r.detail)]
    print(f"stale claims remaining: {len(bad)} {bad}")
    print(f"mentions 298: {sum('298' in str(r.detail) for r in d.itertuples())} rows")


if __name__ == "__main__":
    main()
