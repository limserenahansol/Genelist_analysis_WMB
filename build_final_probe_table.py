"""
Build the final probe workbook: (1) Final_probe_panel - v6 Region / cell populations
plus marker columns, with 'GPCRs to prioritize' from Allen Computed_GPCR_subclass_long
(mean log2, explicit subclass mapping per row). (2) Resources_and_protocol - URLs,
cache notes, and reproducible run order for GitHub.

Input: mouse_*_WITH_GPCR_COMPUTED.xlsx (must contain v6_Final_CellType_GPCR
and Computed_GPCR_subclass_long).

Output: Excel with sheets Final_probe_panel and Resources_and_protocol.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

GITHUB_REPO = "https://github.com/limserenahansol/Genelist_analysis_WMB"


def _resources_protocol_rows(computed_xlsx: Path, cache_dir: Path) -> list[dict[str, str]]:
    """Human-readable provenance; sizes are approximate if cache not scanned."""
    rows: list[dict[str, str]] = [
        {
            "Topic": "What 'GPCRs to prioritize' means",
            "Detail": (
                "This column is derived ONLY from Allen Brain Cell Atlas WMB-10X "
                "log2 expression: mean log2 per (ROI, Allen subclass) from sheet "
                "Computed_GPCR_subclass_long in the computed workbook, then top genes "
                "by max(mean_log2) across the subclass(es) mapped in build_final_probe_table.py. "
                "It is NOT an automated fusion with paper-based lists; Primary/Secondary "
                "marker columns still come from your curated v6 workbook text."
            ),
        },
        {
            "Topic": "Allen ABC Atlas / WMB-10X (data & API)",
            "Detail": (
                "https://alleninstitute.github.io/abc_atlas_access/ ; Python package "
                "abc_atlas_access (AbcProjectCache, get_gene_data on official log2 h5ad)."
            ),
        },
        {
            "Topic": "Notebook - cache setup",
            "Detail": "https://alleninstitute.github.io/abc_atlas_access/notebooks/getting_started.html",
        },
        {
            "Topic": "Notebook - cell / matrix selection pattern",
            "Detail": "https://alleninstitute.github.io/abc_atlas_access/notebooks/abc_atlas_selection_example.html",
        },
        {
            "Topic": "This GitHub repository (code)",
            "Detail": GITHUB_REPO,
        },
        {
            "Topic": "Default local cache directory",
            "Detail": str(cache_dir.resolve()),
        },
        {
            "Topic": "Override cache (env)",
            "Detail": "Set ABC_ATLAS_CACHE to a folder with enough free space (tens of GB typical for full WMB matrices).",
        },
        {
            "Topic": "Approximate download / disk for this pipeline",
            "Detail": (
                "gpcr_rank_patch_v6.py loads ~11 regional WMB-10X log2 .h5ad files for cells "
                "in the ROI union (sAMY, HY, TH, STRd, STRv, PL-ILA-ORB, AI). Individual "
                "matrices are often on the order of ~1–8 GB each; total cached expression "
                "data can reach tens of GB depending on manifest version. Exact bytes = sum "
                "of files under expression_matrices/ in your cache after first run."
            ),
        },
        {
            "Topic": "Computed workbook source",
            "Detail": str(computed_xlsx.resolve()),
        },
        {
            "Topic": "Protocol step 1 - dependencies",
            "Detail": "pip install -r requirements.txt (includes abc_atlas_access from Allen GitHub).",
        },
        {
            "Topic": "Protocol step 2 - audit workbook (optional)",
            "Detail": "python allen_v6_workbook_audit.py --input <v6.xlsx> --output <audit.xlsx>",
        },
        {
            "Topic": "Protocol step 3 - cluster census (optional)",
            "Detail": "python wmb_enrich_probe_workbook_v7.py --input <v6.xlsx> --output <v7.xlsx>",
        },
        {
            "Topic": "Protocol step 4 - full GPCR ranks (heavy)",
            "Detail": (
                "python gpcr_rank_patch_v6.py --xlsx <v6.xlsx> --output <WITH_GPCR_COMPUTED.xlsx> "
                "Close Excel; expect long runtime and large downloads on first use."
            ),
        },
        {
            "Topic": "Protocol step 5 - final five-column panel",
            "Detail": (
                "python build_final_probe_table.py --computed <WITH_GPCR_COMPUTED.xlsx> "
                "--output mouse_6_region_GPCR_probe_FINAL_panel.xlsx [--top-n 10]"
            ),
        },
        {
            "Topic": "Windows file-lock note",
            "Detail": (
                "If PermissionError WinError 32 on h5ad, close Excel and other Python "
                "using the cache; gpcr_rank_patch_v6 uses gc.collect() and retries between matrices."
            ),
        },
    ]

    # Optional: report measured h5ad total under cache if present
    h5ads: list[Path] = []
    if cache_dir.is_dir():
        em = cache_dir / "expression_matrices"
        if em.is_dir():
            h5ads = [p for p in em.rglob("*.h5ad") if p.is_file()]
        else:
            h5ads = [p for p in cache_dir.rglob("*.h5ad") if p.is_file()]
    if h5ads:
        total_b = sum(p.stat().st_size for p in h5ads if p.is_file())
        gb = total_b / (1024**3)
        rows.append(
            {
                "Topic": "Measured .h5ad total in cache (this machine)",
                "Detail": f"{len(h5ads)} files, ~{gb:.2f} GiB under {cache_dir}",
            }
        )
    return rows

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
    ap.add_argument("--output", type=Path, required=True, help="Output .xlsx (two sheets)")
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

    cache_dir = Path(os.environ.get("ABC_ATLAS_CACHE", r"C:\Users\hsollim\Downloads\abc_atlas_cache"))
    resources = pd.DataFrame(_resources_protocol_rows(args.computed, cache_dir))

    out = pd.DataFrame(rows_out)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.output, engine="openpyxl") as w:
        out.to_excel(w, sheet_name="Final_probe_panel", index=False)
        resources.to_excel(w, sheet_name="Resources_and_protocol", index=False)
    print("Wrote", args.output, "Final_probe_panel rows:", len(out), "+ Resources_and_protocol")


if __name__ == "__main__":
    main()
