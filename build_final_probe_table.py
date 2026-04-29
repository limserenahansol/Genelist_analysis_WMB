"""
Build a single-sheet final workbook: v6 Region / cell populations + marker columns,
with 'GPCRs to prioritize' replaced by top GPCRs from Computed_GPCR_subclass_long
(Allen WMB log2 means), using explicit Allen subclass mapping per row.

Input: mouse_*_WITH_GPCR_COMPUTED.xlsx (must contain v6_Final_CellType_GPCR
and Computed_GPCR_subclass_long).

Output: one worksheet, five columns, no extra audit tabs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# User region label -> Allen ROI acronym in computed sheets
REGION_TO_ROI = {
    "BMAp": "sAMY",
    "LM": "HY",
    "RE": "TH",
    "CP": "STRd",
    "ORBm": "PL-ILA-ORB",
    "AId": "AI",
}

# (Region, "Cell type / population") -> Allen WMB subclass labels in that ROI
# Genes ranked by max(mean_log2) across listed subclasses.
CORTICAL_INH_SUBCLASSES = [
    "046 Vip Gaba",
    "047 Sncg Gaba",
    "049 Lamp5 Gaba",
    "050 Lamp5 Lhx6 Gaba",
    "051 Pvalb chandelier Gaba",
    "052 Pvalb Gaba",
    "053 Sst Gaba",
    "056 Sst Chodl Gaba",
]

ROW_SUBCLASSES: dict[tuple[str, str], list[str]] = {
    ("BMAp", "Posterior BMA glutamatergic / pallial amygdala VGLUT1-like"): [
        "014 LA-BLA-BMA-PA Glut",
        "012 MEA Slc17a7 Glut",
    ],
    ("BMAp", "BMA/MEA VGLUT2-like excitatory"): [
        "113 MEA-COA-BMA Ccdc42 Glut",
        "114 COAa-PAA-MEA Barhl2 Glut",
        "014 LA-BLA-BMA-PA Glut",
    ],
    ("BMAp", "Amygdala GABA / striatal-like inhibitory neighbors"): [
        "073 MEA-BST Sox6 Gaba",
        "054 STR Prox1 Lhx6 Gaba",
    ],
    ("LM", "Lateral mammillary excitatory neurons"): ["144 MM Foxb1 Glut"],
    ("LM", "Nearby hypothalamic exclusion populations"): ["117 LHA Barhl2 Glut"],
    ("RE", "Midline thalamic glutamatergic / reuniens"): ["152 RE-Xi Nox4 Glut"],
    ("RE", "Reticular/inhibitory thalamic exclusion"): ["093 RT-ZI Gnb3 Gaba"],
    ("CP", "D1/direct-pathway SPN"): ["061 STR D1 Gaba"],
    ("CP", "D2/indirect-pathway SPN"): ["062 STR D2 Gaba"],
    ("CP", "Patch/striosome SPN"): ["063 STR D1 Sema5a Gaba"],
    ("CP", "Matrix/exopatch SPN"): ["061 STR D1 Gaba"],
    ("CP", "Cholinergic interneuron"): ["058 PAL-STR Gaba-Chol"],
    ("CP", "PV/SST/NPY interneurons"): [
        "052 Pvalb Gaba",
        "053 Sst Gaba",
        "047 Sncg Gaba",
    ],
    ("ORBm", "L2/3 IT excitatory"): ["007 L2/3 IT CTX Glut"],
    ("ORBm", "L5 IT / L5 ET/PT output neurons"): [
        "005 L5 IT CTX Glut",
        "022 L5 ET CTX Glut",
    ],
    ("ORBm", "L6 CT / L6b"): [
        "030 L6 CT CTX Glut",
        "029 L6b CTX Glut",
    ],
    ("ORBm", "Cortical interneurons"): list(CORTICAL_INH_SUBCLASSES),
    ("AId", "Upper-layer IT excitatory"): ["007 L2/3 IT CTX Glut"],
    ("AId", "Deep-layer output neurons"): [
        "005 L5 IT CTX Glut",
        "022 L5 ET CTX Glut",
        "029 L6b CTX Glut",
        "030 L6 CT CTX Glut",
    ],
    ("AId", "Cortical interneurons"): list(CORTICAL_INH_SUBCLASSES),
}


def _top_gpcrs(
    sub_long: pd.DataFrame,
    roi: str,
    subclasses: list[str],
    top_n: int,
) -> tuple[str, str]:
    s = sub_long[
        (sub_long["region_of_interest_acronym"] == roi)
        & (sub_long["subclass"].isin(subclasses))
    ]
    if s.empty:
        return "", "no_rows"
    agg = s.groupby("gene_symbol", as_index=False)["mean_log2"].max()
    agg = agg.sort_values("mean_log2", ascending=False).head(top_n)
    genes = agg["gene_symbol"].astype(str).tolist()
    return ", ".join(genes), "; ".join(subclasses[:3]) + ("..." if len(subclasses) > 3 else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--computed",
        type=Path,
        required=True,
        help="Path to *_WITH_GPCR_COMPUTED.xlsx",
    )
    ap.add_argument("--output", type=Path, required=True, help="Single-sheet output .xlsx")
    ap.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of GPCR genes to list (ranked by max subclass mean log2)",
    )
    args = ap.parse_args()

    v6 = pd.read_excel(args.computed, sheet_name="v6_Final_CellType_GPCR")
    sub_long = pd.read_excel(
        args.computed, sheet_name="Computed_GPCR_subclass_long"
    )

    col_pop = "Cell type / population"
    col_pri = "Primary cell-type marker genes to add"
    col_sec = "Secondary / exclusion markers"

    rows_out: list[dict[str, str]] = []
    for _, r in v6.iterrows():
        region = str(r["Region"]).strip()
        pop = str(r[col_pop]).strip()
        key = (region, pop)
        if key not in ROW_SUBCLASSES:
            raise KeyError(f"No subclass mapping for row: {key!r}")
        roi = REGION_TO_ROI.get(region)
        if not roi:
            raise KeyError(f"No ROI mapping for region: {region!r}")

        subclasses = ROW_SUBCLASSES[key]
        gpcr_str, _ = _top_gpcrs(sub_long, roi, subclasses, args.top_n)

        rows_out.append(
            {
                "Region": region,
                "Cell type / population": pop,
                "Primary cell-type markers": str(r.get(col_pri, "") or ""),
                "Secondary / exclusion markers": str(r.get(col_sec, "") or ""),
                "GPCRs to prioritize": gpcr_str,
            }
        )

    out = pd.DataFrame(rows_out)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.output, engine="openpyxl") as w:
        out.to_excel(w, sheet_name="Final_probe_panel", index=False)
    print("Wrote", args.output, "rows:", len(out))


if __name__ == "__main__":
    main()
