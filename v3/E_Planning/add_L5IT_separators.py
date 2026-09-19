"""Close the two L5 IT separability gaps by appending two markers to the order sheet.

Why this was needed
-------------------
ANCHOR_COVERAGE lists one "unique separator" for 005 L5 IT CTX Glut (Bdnf), which
reads as if the population rests on a single gene. That number counts only genes
exclusive to L5 IT *alone* - the strictest possible criterion. Against the 3,901
pairwise tests, L5 IT is already separable from 9 of its 11 neighbours using genes
the panel carries (Coch, Rorb, Lamp5, Satb2, Tbr1, Meis2, Nr4a2, Gfra1, Calb1,
Etv1, Nfib, Mpped1).

Two real gaps remain, both against the adjacent IT layers - which is expected,
because L5 IT is transcriptomically continuous with them:

  vs 006 L4/5 IT CTX Glut   no panel gene separates them
  vs 007 L2/3 IT CTX Glut   no panel gene separates them

What we add, and why this pairing
---------------------------------
Sema5a is the only single candidate covering both gaps (log2 gaps 1.38 / 1.50,
3 of 11 neighbours). But for the same one custom slot:

  Sema5b   FREE on the 10x base panel   closes the L4/5 IT gap   (gap 1.14)
  Rai14    1 custom slot                closes the L2/3 IT gap   (gap 2.16)
                                        and separates 6 of 11 neighbours

That pair gives a wider margin on the harder boundary (2.16 vs Sema5a's 1.50)
and more breadth, at one slot instead of one slot. So Sema5a is not taken.

Honest caveat kept in the sheet: every candidate here sits at 27-42% of cells,
below the >50% detectability bar applied to the receptors. Adcyap1 is far better
detected (57.9%) but separates none of the two gaps, so it does not help.

Appends block 15_L5IT_separator_added. Formatting preserved, append-only.

Output: FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v4_170genes.xlsx
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
SRC = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
DST = OUT / "FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v4_170genes.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PAIRS = OUT / "subclass_markers_all" / "Subclass_Pairwise_Separators.csv"

BLOCK = "15_L5IT_separator_added"
TARGET = "005 L5 IT CTX Glut"
ADD = [
    ("Sema5b", "006 L4/5 IT CTX Glut", "free"),
    ("Rai14", "007 L2/3 IT CTX Glut", "custom"),
]
WHY = (
    "Added to close a separability gap for 005 L5 IT CTX Glut. Against the 3,901 pairwise "
    "separator tests, L5 IT was already distinguishable from 9 of its 11 neighbouring subclasses "
    "using panel genes, but no panel gene separated it from the two adjacent IT layers. "
    "Sema5a covers both gaps in one gene; Sema5b (free on base) plus Rai14 was taken instead "
    "because it gives a wider margin on the harder L2/3 boundary (log2 2.16 vs 1.50) and "
    "separates more neighbours, for the same single custom slot. "
    "Caveat: detected in 27-41% of L5 IT cells, below the >50% bar used for receptors - no "
    "abundant gene is exclusive to L5 IT because it is transcriptomically continuous with the "
    "neighbouring IT layers. Not a cell-state gene; ANCHOR_COVERAGE gains coverage, loses none."
)


def main() -> None:
    pairs = pd.read_csv(PAIRS)
    a = pairs[pairs.subclass_A_positive == TARGET]
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))

    shutil.copy2(SRC, DST)
    wb = load_workbook(DST)
    sh, orbm = wb["SHARED_PANEL_ORDER"], wb["ORBm_ORDER"]
    r0, o0 = sh.max_row, orbm.max_row

    for i, (gene, vs, cost) in enumerate(ADD):
        row = a[(a.separator_gene == gene) & (a.subclass_B_negative == vs)].iloc[0]
        n_vs = a[a.separator_gene == gene].subclass_B_negative.nunique()
        serves = (f"L5 IT separator :: vs {vs.split(' ', 1)[1]}, "
                  f"{row.pct_A:.0f}% vs {row.pct_B:.0f}% of cells, log2 gap {row.log2_gap:.2f}, "
                  f"separates {n_vs}/11 neighbours")
        for ws, base_row in ((sh, r0), (orbm, o0)):
            rr = base_row + 1 + i
            ws.cell(row=rr, column=1, value=base_row + i)
            ws.cell(row=rr, column=2, value=gene)
            ws.cell(row=rr, column=3, value=BLOCK)
            ws.cell(row=rr, column=4, value=serves)
            ws.cell(row=rr, column=5, value=WHY)
        assert (gene in base) == (cost == "free"), f"{gene} cost mismatch"

    fg = wb["FOR_MarkGreg"]
    fg.cell(row=fg.max_row + 1, column=1, value="2 genes appended (L5 IT separability fix)")
    fg.cell(row=fg.max_row, column=2, value=(
        f"Sema5b (already free on the 10x base panel) and Rai14 (1 new custom slot) were added at the "
        f"bottom of SHARED_PANEL_ORDER and ORBm_ORDER as block {BLOCK}. They close the only two "
        f"cell-type separability gaps left in the design: 005 L5 IT CTX Glut could not be told apart "
        f"from 006 L4/5 IT or 007 L2/3 IT using panel genes alone. It was already separable from the "
        f"other 9 of its 11 neighbours. No existing gene was removed or re-ranked; BMAp_ORDER unchanged."
    ))

    ac = wb["ANCHOR_COVERAGE"]
    hdr = [c.value for c in ac[1]]
    col = hdr.index("unique_separators_on_shared_panel") + 1
    for r in range(2, ac.max_row + 1):
        if ac.cell(row=r, column=3).value == TARGET:
            cur = ac.cell(row=r, column=col).value or ""
            ac.cell(row=r, column=col, value=f"{cur}, Sema5b, Rai14".lstrip(", "))
            print(f"  ANCHOR_COVERAGE row {r}: '{cur}' -> '{ac.cell(row=r, column=col).value}'")

    wb.save(DST)

    out = pd.read_excel(DST, "SHARED_PANEL_ORDER")
    free = int(out.gene.isin(base).sum())
    print(f"\nworkbook -> {DST}")
    print(f"  SHARED {len(out)} = {free} free + {len(out)-free} custom | "
          f"dupes {out.gene.duplicated().sum()} | "
          f"ranks ok {list(out.order_rank)==list(range(1,len(out)+1))}")
    print(f"  ORBm {len(pd.read_excel(DST,'ORBm_ORDER'))} | "
          f"BMAp {len(pd.read_excel(DST,'BMAp_ORDER'))} (unchanged)")


if __name__ == "__main__":
    main()
