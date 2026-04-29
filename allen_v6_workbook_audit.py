"""
Download small Allen ABC Atlas files via AbcProjectCache (getting_started pattern),
then audit mouse_6_region_celltype_GPCR_probe_list_v6_source_audit.xlsx.

Outputs a NEW workbook with extra sheets (does not overwrite the original).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(os.environ.get("ABC_ATLAS_CACHE", r"C:\Users\hsollim\Downloads\abc_atlas_cache"))
INPUT_XLSX = Path(
    r"C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v6_source_audit.xlsx"
)
OUTPUT_XLSX = Path(
    r"C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v6_plus_ALLEN_PYTHON_AUDIT.xlsx"
)

# User six regions -> official WMB-10X region-of-interest rows (acronym from Allen CSV)
REGION_TO_WMB_ROI = [
    ("BMAp", "sAMY", "Striatum-like amygdalar nuclei (includes BMA-related dissection groups in WMB)"),
    ("LM", "HY", "Hypothalamus (lateral mammillary is HY; Allen ROI is whole HY)"),
    ("RE", "TH", "Thalamus (reuniens is midline thalamus)"),
    ("CP", "STRd", "Striatum dorsal region (caudoputamen)"),
    ("ORBm", "PL-ILA-ORB", "Prelimbic / infralimbic / orbital (ORB overlaps this ROI)"),
    ("AId", "AI", "Agranular insular area"),
]


def load_abc_cache():
    from abc_atlas_access.abc_atlas_cache.abc_project_cache import AbcProjectCache

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return AbcProjectCache.from_cache_dir(CACHE_DIR)


def _local_path(result) -> Path:
    if isinstance(result, dict):
        return Path(result["local_path"])
    return Path(result)


def ensure_allen_tables(abc) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for p in abc.get_directory_metadata("WMB-taxonomy"):
        paths[p.name] = p
    paths["gene.csv"] = _local_path(abc.get_file_path("WMB-10X", "gene"))
    paths["region_of_interest_metadata.csv"] = _local_path(
        abc.get_file_path("WMB-10X", "region_of_interest_metadata")
    )
    return paths


def tokenize_gene_like(s: str) -> list[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    return re.findall(r"[A-Za-z][A-Za-z0-9_-]*", s)


def main(input_xlsx: Path | None = None, output_xlsx: Path | None = None) -> None:
    input_path = input_xlsx or INPUT_XLSX
    output_path = output_xlsx or OUTPUT_XLSX
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    abc = load_abc_cache()
    manifest = abc.current_manifest
    version = str(abc.cache.version)
    paths = ensure_allen_tables(abc)

    gene_df = pd.read_csv(paths["gene.csv"])
    valid = set(gene_df["gene_symbol"].dropna().astype(str).str.strip())
    valid_lower = {g.lower(): g for g in valid}

    roi_df = pd.read_csv(paths["region_of_interest_metadata.csv"])

    # Genes mentioned in final sheet
    final = pd.read_excel(input_path, sheet_name="v6_Final_CellType_GPCR")
    gene_cols = [
        c
        for c in final.columns
        if "marker" in c.lower() or "gpcr" in c.lower() or "GPCR" in c
    ]
    mentioned: list[str] = []
    for _, row in final.iterrows():
        blob = " ".join(str(row[c]) for c in gene_cols if c in row.index)
        for tok in tokenize_gene_like(blob):
            canon = valid_lower.get(tok.lower())
            if canon:
                mentioned.append(canon)
    mentioned_unique = sorted(set(mentioned))

    in_allen = [{"gene_symbol": g, "in_WMB_10X_gene_csv": True} for g in mentioned_unique]
    # Also list symbols that looked gene-like but are NOT in table (optional)
    false_hits = []
    for _, row in final.iterrows():
        blob = " ".join(str(row[c]) for c in gene_cols if c in row.index)
        for tok in tokenize_gene_like(blob):
            if len(tok) < 2 or len(tok) > 14:
                continue
            if not re.match(r"^[A-Za-z]", tok):
                continue
            if tok.lower() in {"rna", "dna", "gaba", "wmb", "bma", "mea", "bla"}:
                continue
            if valid_lower.get(tok.lower()):
                continue
            # uppercase-ish gene pattern
            if re.match(r"^[A-Z][A-Za-z0-9]{1,11}$", tok):
                false_hits.append(tok)
    false_hits = sorted(set(false_hits))

    roi_map_rows = []
    for user_r, acronym, note in REGION_TO_WMB_ROI:
        hit = roi_df[roi_df["acronym"] == acronym]
        roi_map_rows.append(
            {
                "user_region": user_r,
                "WMB_ROI_acronym": acronym,
                "matched_ROI_name": hit["name"].iloc[0] if len(hit) else "",
                "note": note,
            }
        )
    roi_map_df = pd.DataFrame(roi_map_rows)

    audit_summary = pd.DataFrame(
        [
            {
                "item": "AbcProjectCache manifest used",
                "value": manifest,
            },
            {
                "item": "Manifest version string",
                "value": version,
            },
            {
                "item": "Files pulled this run (small)",
                "value": "WMB-taxonomy/* ; WMB-10X gene.csv ; WMB-10X region_of_interest_metadata.csv",
            },
            {
                "item": "Expression matrices downloaded?",
                "value": "No — full WMB-10Xv2/v3 h5ad remains large; this audit validates taxonomy/gene symbol/ROI mapping only.",
            },
            {
                "item": "What this proves for v6 workbook",
                "value": "Gene symbols in v6_Final_CellType_GPCR exist in official WMB-10X gene list; six regions align to coarse WMB dissection ROIs (not single-nucleus resolution).",
            },
            {
                "item": "What this does NOT prove",
                "value": "Per-cell-type expression rank of GPCRs; cluster-level enrichment vs Allen — requires targeted get_gene_data / h5ad workflow.",
            },
            {
                "item": "Allen getting_started URL",
                "value": "https://alleninstitute.github.io/abc_atlas_access/notebooks/getting_started.html",
            },
        ]
    )

    gene_check_df = pd.DataFrame(in_allen)
    not_in_allen_df = pd.DataFrame({"token_not_in_gene_csv": false_hits})

    notes = pd.DataFrame(
        [
            {
                "topic": "Dopamine receptors",
                "detail": "Allen WMB-10X gene.csv includes Drd1, Drd2, etc. It does not list Drd1a as a separate symbol; use Drd1 for D1 SPNs.",
            },
            {
                "topic": "v6 vs expression proof",
                "detail": "v6_Summary states GPCR ranking was not computed from raw matrices. This Python run confirms gene symbols and ROI mapping only.",
            },
            {
                "topic": "Next step for true expression audit",
                "detail": "Follow 10x gene expression notebooks (WMB-10Xv2/v3) to subset h5ad or use API gene extraction for your GPCR list per cluster.",
            },
        ]
    )

    # Write full copy of original sheets + new sheets
    xl = pd.ExcelFile(input_path)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet in xl.sheet_names:
            pd.read_excel(input_path, sheet_name=sheet).to_excel(
                writer, sheet_name=sheet, index=False
            )
        audit_summary.to_excel(writer, sheet_name="Python_Allen_Audit_Summary", index=False)
        roi_map_df.to_excel(writer, sheet_name="Python_ROI_Region_Map", index=False)
        gene_check_df.to_excel(writer, sheet_name="Python_Genes_In_Allen_WMB10X", index=False)
        not_in_allen_df.to_excel(
            writer, sheet_name="Python_Tokens_Not_In_GeneCSV", index=False
        )
        notes.to_excel(writer, sheet_name="Python_Symbol_Notes", index=False)

    print("Wrote:", output_path)
    print("Manifest:", manifest, "version:", version)
    print("Unique Allen-valid gene symbols from v6_Final:", len(mentioned_unique))
    print("Tokens resembling genes but not in gene.csv:", len(false_hits))
    if false_hits[:20]:
        print("  sample:", false_hits[:20])


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_XLSX, help="v6 audit workbook")
    ap.add_argument("--output", type=Path, default=OUTPUT_XLSX, help="Workbook + Python audit sheets")
    args = ap.parse_args()
    main(args.input, args.output)
