#!/usr/bin/env python
"""
D04_make_focused_decision_table.py

Build a single-purpose, easy-to-read decision table that contains ONLY the
three columns the user cares about for probe selection, side-by-side:

    paper_suggested_gpcrs   (literature-curated)
    top_GPCRs_to_choose     (Allen-data-validated final pick)
    agreement_paper_vs_allen (paper vs Allen reasoning)

Plus the bare minimum context columns: region, cell type, anchor, n_cells,
cell_type_marker_genes, exclusion_markers.

Reads:  v3/outputs/Final_Probe_Panel_v7_modular.xlsx (sheet=Final_Summary)
Writes: v3/outputs/FINAL_decision_table_paper_vs_allen.xlsx
        outputs/FINAL_decision_table_paper_vs_allen.xlsx (top-level mirror)
        v3/outputs/FINAL_decision_table_paper_vs_allen.csv (preview)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


KEEP_COLUMNS = [
    "region_user",
    "cell_type_label",
    "allen_subclass_anchor",
    "n_cells_in_anchor",
    "cell_type_marker_genes",
    "exclusion_markers",
    "paper_suggested_gpcrs",
    "top_GPCRs_to_choose",
    "agreement_paper_vs_allen",
    "warning",
]


def build_table(src_xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(src_xlsx, sheet_name="Final_Summary")
    cols = [c for c in KEEP_COLUMNS if c in df.columns]
    return df[cols].copy()


def write_focused_xlsx(df: pd.DataFrame, out_xlsx: Path) -> None:
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)

    readme = pd.DataFrame(
        [
            {
                "row": 1,
                "purpose": "Single-purpose decision table that combines paper-suggested vs Allen-validated GPCRs.",
            },
            {
                "row": 2,
                "purpose": "Each row = (region, cell type). Columns to compare side-by-side:",
            },
            {
                "row": 3,
                "purpose": "  paper_suggested_gpcrs   = literature-curated genes for this cell type",
            },
            {
                "row": 4,
                "purpose": "  top_GPCRs_to_choose     = Allen WMB-10X data-validated final pick (status=keep / candidate_to_validate)",
            },
            {
                "row": 5,
                "purpose": "  agreement_paper_vs_allen = both: paper+Allen agree | paper_only: paper said yes Allen downgraded (with reason) | allen_only_keep: Allen found new candidate",
            },
            {
                "row": 6,
                "purpose": "Use top_GPCRs_to_choose as the order list; check paper_only entries with FISH if you really want them.",
            },
            {
                "row": 7,
                "purpose": "Generated from v3/outputs/Final_Probe_Panel_v7_modular.xlsx (Final_Summary sheet) by D04_make_focused_decision_table.py",
            },
        ]
    )

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        readme.to_excel(w, sheet_name="HOW_TO_READ", index=False)
        df.to_excel(w, sheet_name="Decision_Table", index=False)

    # styling: wider columns + wrap text + header bold + colored header for the 3 key cols
    wb = load_workbook(out_xlsx)
    ws = wb["Decision_Table"]
    header_fill = PatternFill("solid", fgColor="1F4E79")
    paper_fill = PatternFill("solid", fgColor="FFD966")
    pick_fill = PatternFill("solid", fgColor="A9D08E")
    agree_fill = PatternFill("solid", fgColor="F4B084")
    bold_white = Font(bold=True, color="FFFFFF")
    wrap = Alignment(wrap_text=True, vertical="top")

    column_widths = {
        "region_user": 8,
        "cell_type_label": 30,
        "allen_subclass_anchor": 22,
        "n_cells_in_anchor": 8,
        "cell_type_marker_genes": 32,
        "exclusion_markers": 22,
        "paper_suggested_gpcrs": 50,
        "top_GPCRs_to_choose": 70,
        "agreement_paper_vs_allen": 90,
        "warning": 30,
    }

    headers = [c.value for c in ws[1]]
    for idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.font = bold_white
        cell.fill = header_fill
        if h == "paper_suggested_gpcrs":
            cell.fill = paper_fill
            cell.font = Font(bold=True)
        elif h == "top_GPCRs_to_choose":
            cell.fill = pick_fill
            cell.font = Font(bold=True)
        elif h == "agreement_paper_vs_allen":
            cell.fill = agree_fill
            cell.font = Font(bold=True)
        ws.column_dimensions[get_column_letter(idx)].width = column_widths.get(h, 20)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.alignment = wrap

    ws.row_dimensions[1].height = 30
    for r in range(2, ws.max_row + 1):
        ws.row_dimensions[r].height = 90

    ws.freeze_panes = "C2"
    wb.save(out_xlsx)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src_xlsx", default="v3/outputs/Final_Probe_Panel_v7_modular.xlsx")
    p.add_argument("--out_xlsx", default="v3/outputs/FINAL_decision_table_paper_vs_allen.xlsx")
    p.add_argument("--top_mirror", default="outputs/FINAL_decision_table_paper_vs_allen.xlsx")
    p.add_argument("--csv_preview", default="v3/outputs/FINAL_decision_table_paper_vs_allen.csv")
    args = p.parse_args()

    df = build_table(Path(args.src_xlsx))
    print(f"[INFO] decision table shape: {df.shape}")
    write_focused_xlsx(df, Path(args.out_xlsx))
    print(f"[OK] {args.out_xlsx}")
    write_focused_xlsx(df, Path(args.top_mirror))
    print(f"[OK] {args.top_mirror}  (top-level mirror)")
    df.to_csv(args.csv_preview, index=False)
    print(f"[OK] {args.csv_preview}  (GitHub-renderable preview)")


if __name__ == "__main__":
    main()
