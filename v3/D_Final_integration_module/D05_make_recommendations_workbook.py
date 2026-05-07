#!/usr/bin/env python
"""
D05_make_recommendations_workbook.py

Build a STANDALONE recommendations workbook (just the conclusions).
One row per (region x cell type). No metrics, no URLs, no drugbank IDs.
Just: genes to order + drug per gene + what to do.

Reads:  v3/outputs/Final_Probe_Panel_v7_modular.xlsx (FINAL_Recommendations sheet)
Writes: v3/outputs/FINAL_Recommendations.xlsx (canonical, nicely styled)
        outputs/FINAL_Recommendations.xlsx    (top-level mirror)
        v3/outputs/FINAL_Recommendations.csv  (GitHub-renderable preview)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _style(out_xlsx: Path) -> None:
    wb = load_workbook(out_xlsx)
    ws = wb["FINAL_Recommendations"]

    header_fill = PatternFill("solid", fgColor="1F4E79")  # navy
    gene_fill = PatternFill("solid", fgColor="9CC2E5")  # blue
    drug_fill = PatternFill("solid", fgColor="C9A0DC")  # purple
    action_fill = PatternFill("solid", fgColor="A9D08E")  # green
    bold_white = Font(bold=True, color="FFFFFF")
    bold_black = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    column_widths = {
        "region": 8,
        "cell_type": 32,
        "allen_subclass": 28,
        "n_cells_in_anchor": 10,
        "recommended_GPCR_panel": 38,
        "recommended_drugs_per_gene": 70,
        "n_genes_recommended": 10,
        "evidence_tier_per_gene": 60,
        "what_to_do": 35,
    }

    headers = [c.value for c in ws[1]]
    for idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.font = bold_white
        cell.fill = header_fill
        if h == "recommended_GPCR_panel":
            cell.fill = gene_fill
            cell.font = bold_black
        elif h == "recommended_drugs_per_gene":
            cell.fill = drug_fill
            cell.font = bold_black
        elif h == "what_to_do":
            cell.fill = action_fill
            cell.font = bold_black
        ws.column_dimensions[get_column_letter(idx)].width = column_widths.get(h, 18)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.alignment = wrap

    # color-code rows by what_to_do
    action_idx = headers.index("what_to_do") + 1 if "what_to_do" in headers else None
    order_now_fill = PatternFill("solid", fgColor="E2EFDA")  # light green
    spatial_fill = PatternFill("solid", fgColor="FFF2CC")  # light yellow
    review_fill = PatternFill("solid", fgColor="FCE4D6")  # light orange
    if action_idx is not None:
        for r in range(2, ws.max_row + 1):
            v = str(ws.cell(row=r, column=action_idx).value or "")
            row_fill = None
            if v.startswith("ORDER ("):
                row_fill = order_now_fill
            elif v.startswith("ORDER WITH SPATIAL"):
                row_fill = spatial_fill
            elif v.startswith("REVIEW"):
                row_fill = review_fill
            if row_fill is not None:
                for c in range(1, ws.max_column + 1):
                    if ws.cell(row=r, column=c).fill.fgColor.rgb in (None, "00000000", "FFFFFFFF"):
                        ws.cell(row=r, column=c).fill = row_fill

    ws.row_dimensions[1].height = 32
    for r in range(2, ws.max_row + 1):
        ws.row_dimensions[r].height = 60

    ws.freeze_panes = "C2"
    wb.save(out_xlsx)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src_xlsx", default="v3/outputs/Final_Probe_Panel_v7_modular.xlsx")
    p.add_argument("--out_xlsx", default="v3/outputs/FINAL_Recommendations.xlsx")
    p.add_argument("--top_mirror", default="outputs/FINAL_Recommendations.xlsx")
    p.add_argument("--csv_preview", default="v3/outputs/FINAL_Recommendations.csv")
    args = p.parse_args()

    df = pd.read_excel(args.src_xlsx, sheet_name="FINAL_Recommendations")
    print(f"[INFO] recommendations shape: {df.shape}")

    readme = pd.DataFrame(
        [
            {"row": 1, "purpose": "Single-purpose CONCLUSIONS sheet. Each row = one (region x cell type)."},
            {"row": 2, "purpose": "  recommended_GPCR_panel        = comma-separated list of top 5 GPCRs to order probes for."},
            {"row": 3, "purpose": "  recommended_drugs_per_gene    = drug suggestion per gene; '(FDA)' = FDA-approved, '(research)' = preclinical only."},
            {"row": 4, "purpose": "  evidence_tier_per_gene        = paper+allen_keep > allen_only_keep > paper+allen_broadly_detectable > allen_only_broadly_detectable."},
            {"row": 5, "purpose": "  what_to_do                    = green ORDER NOW (cell-type-specific) | yellow ORDER WITH SPATIAL CONSTRAINT (broadly detectable only) | orange REVIEW."},
            {"row": 6, "purpose": "For metrics, sources, DrugBank URLs, PubMed PMIDs -> open Final_Probe_Panel_v7_modular.xlsx (Final_Summary, GPCR_Drug_References)."},
            {"row": 7, "purpose": "For full evidence trace -> Final_Probe_Panel sheet (154,869 rows)."},
        ]
    )

    out_xlsx = Path(args.out_xlsx)
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        readme.to_excel(w, sheet_name="HOW_TO_READ", index=False)
        df.to_excel(w, sheet_name="FINAL_Recommendations", index=False)
    _style(out_xlsx)
    print(f"[OK] {out_xlsx}")

    top = Path(args.top_mirror)
    top.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(top, engine="openpyxl") as w:
        readme.to_excel(w, sheet_name="HOW_TO_READ", index=False)
        df.to_excel(w, sheet_name="FINAL_Recommendations", index=False)
    _style(top)
    print(f"[OK] {top}  (top-level mirror)")

    df.to_csv(args.csv_preview, index=False)
    print(f"[OK] {args.csv_preview}  (GitHub preview)")


if __name__ == "__main__":
    main()
