# Allen + Published Data Workflow for Mouse Cell-Type Marker and GPCR Probe Lists

![v3 pipeline overview](docs/images/v3_pipeline_overview.png)

> **Want a single-page recipe?** See [`docs/STEP_BY_STEP.md`](docs/STEP_BY_STEP.md).
> **Want to understand the row-level decisions?** See the schematic below.

![v3 decision tree](docs/images/v3_decision_tree.png)

## Project goal

Build a defensible probe-list workbook for six mouse brain regions:

- **BMAp**: basomedial amygdalar nucleus, posterior part
- **LM**: interpreted as lateral mammillary nucleus/body; must be confirmed before probe order
- **RE**: nucleus reuniens / midline thalamus
- **CP**: caudoputamen / dorsal striatum
- **ORBm**: orbital area, medial part
- **AId**: agranular insular area, dorsal part; confirm whether original `Ald` means `AId`

The workflow answers:

1. Which transcriptomic cell types/clusters are present in each region?
2. Which marker genes define those cell types?
3. Which GPCRs are expressed/enriched in each region x cell type?
4. Which candidate genes from the current workbook should be kept, downgraded, removed, or added?
5. Which genes are ready for Xenium/HCR/ISH probe design?

## Why this package is split into four modules

The previous workbook mixed several evidence types: literature-supported cell-type markers, Allen-informed candidates, Cursor-generated candidates, and GPCRs that still need direct expression-matrix validation. This modular package separates the evidence sources.

| Module | Purpose | Main input | Main output |
|---|---|---|---|
| **A. Allen-only computational module** | Directly compute region x cell-type x GPCR expression and marker rankings from Allen ABC/WMB data | Allen WMB 10X, MERFISH/CCF, taxonomy, Consensus-WMB | Allen-computed GPCR and marker tables |
| **B. Published-marker input module** | Use published/curated cell-type markers when all-gene computation is too large | Literature marker CSV | Standardized marker table and Allen presence check |
| **C. Published raw-data extraction module** | Download and compute from paper source datasets when available | Paper source data links/accessions | Paper-computed validation tables |
| **D. Final integration module** | Merge Allen-computed, literature, paper, and current workbook candidates | Outputs from A/B/C and current workbook | Final probe-panel workbook |

## Recommended first run (preprocessing + lightweight)

> **Run this once, in this order.** All paths and thresholds come from
> `config/project_config.yaml`; override only via the documented CLI flags.

```text
A00 -> A01 -> A02 -> B01 -> B02 -> A03 (with the Region_Mapping_Auto_Draft.csv from A02) -> D02
```

```powershell
$ROOT = "c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3"
$OUT  = "$ROOT\outputs"

# 1) Preprocess: env check, manifest pin, Allen metadata download, optional paper download
python "$ROOT\A_Allen_only_computational_module\A00_preprocess_download.py" `
    --out_dir "$OUT\preprocess" `
    --paper_manifest "$ROOT\inputs\paper_source_manifest_template.csv" `
    --paper_download_dir "$OUT\paper_raw"

# 2) Snapshot Allen WMB-10X + WMB-taxonomy metadata to parquet
python "$ROOT\A_Allen_only_computational_module\A01_setup_cache_and_metadata.py" `
    --out_dir "$OUT\metadata"

# 3) Map user labels (BMAp, LM, RE, CP, ORBm, AId) to Allen ROI acronyms
python "$ROOT\A_Allen_only_computational_module\A02_region_mapping_merfish_ccf.py" `
    --out_dir "$OUT\region_mapping"

# 4) Standardize and validate published markers
python "$ROOT\B_Published_marker_input_module\B01_standardize_published_markers.py" `
    --markers_csv "$ROOT\inputs\curated_marker_template.csv" `
    --out_dir "$OUT\markers"
python "$ROOT\B_Published_marker_input_module\B02_validate_marker_presence_in_allen.py" `
    --cache_dir "C:\Users\hsollim\Downloads\abc_atlas_cache" `
    --marker_long_csv "$OUT\markers\Published_Cell_Marker_Long.csv" `
    --out_dir "$OUT\markers"

# 5) Compute Allen GPCR expression for the regions in step 3
python "$ROOT\A_Allen_only_computational_module\A03_allen_gpcr_expression.py" `
    --out_dir "$OUT\gpcr" `
    --gpcr_csv "$ROOT\inputs\mouse_gpcr_universe_template.csv" `
    --region_mapping_csv "$OUT\region_mapping\Region_Mapping_Auto_Draft.csv" `
    --levels subclass supertype cluster

# 6) Final evidence-aware workbook
python "$ROOT\D_Final_integration_module\D02_create_final_probe_workbook.py" `
    --out_xlsx "$OUT\Final_Probe_Panel_v7_modular.xlsx" `
    --allen_subclass_csv  "$OUT\gpcr\Allen_GPCR_Ranking_subclass.csv" `
    --allen_supertype_csv "$OUT\gpcr\Allen_GPCR_Ranking_supertype.csv" `
    --allen_cluster_csv   "$OUT\gpcr\Allen_GPCR_Ranking_cluster.csv" `
    --published_marker_csv "$OUT\markers\Published_Cell_Marker_Long.csv" `
    --region_mapping_csv "$OUT\region_mapping\Region_Mapping_Auto_Draft.csv"
```

Each script appends a JSON record to `<out_dir>/run_log.jsonl` with the manifest version, git commit, parameters, and number of rows produced for full provenance.

### What this fixes vs the original v3 draft

- **A00** (new): explicit preprocessing/download step, prints free disk, captures `paper_download_status.csv`.
- **A02**: uses Allen `region_of_interest_metadata.csv` + word-boundary regex; no more spurious matches against gene/cluster names.
- **A03**: filters cells **before** calling `get_gene_data`; only triggers downloads of regions you actually need. Adds Windows-aware `gc.collect` + retry guard for `PermissionError`. Adds `specificity_log2` and per-level outputs.
- **D02**: thresholds come from `project_config.yaml`; produces a single `Final_Probe_Panel` sheet with Allen + paper + marker columns and a `final_recommendation` column.
- All modules share `common/config.py` for cache, manifest pin, and `run_log.jsonl`.

## Alternative: Case 2 lightweight workflow

Start with **Case 2 lightweight workflow**:

```text
B. Published-marker input module
+ A. Allen-only GPCR-only expression extraction
+ D. Final integration module
```

This gives the highest-value correction quickly: it tells you whether candidate GPCRs are actually expressed in each Allen cell type/region, without running all-gene marker discovery first.

Then run **Case 1 full raw-data workflow** for final probe ordering:

```text
A. Allen all-gene marker discovery
+ A. Allen GPCR expression ranking
+ C. paper source-data validation
+ D. final integration
```

## Critical interpretation rule

Do **not** call a gene “high in a cell type” unless it has computed expression evidence.

Use:

```text
Candidate GPCR to validate = literature/curated/Allen-marker-informed, not yet computed
Computed GPCR = expression matrix was analyzed
Validated GPCR = computed expression plus region/cell-type specificity support
```

## Official Allen resources used by this workflow

- Allen ABC getting started notebook: uses `AbcProjectCache`, AWS public dataset, and local `.h5ad` expression matrices.
- Allen WMB dataset: mouse whole-brain transcriptomic atlas with 10X, taxonomy, MERFISH spatial mapping, CCF coordinates, and imputed MERFISH.
- Allen Consensus-WMB dataset: validation resource integrating Macosko and Zeng datasets.
- Allen 10X RNA-seq tutorial: official route for selected-gene extraction using `get_gene_data`.

Source URLs are listed in `docs/SOURCE_DATA_TRACKER.md`.

## Folder structure

```text
allen_gpcr_probe_workflow_modular_v3/
  README.md
  config/
    project_config.yaml
  inputs/
    mouse_gpcr_universe_template.csv
    curated_marker_template.csv
    paper_source_manifest_template.csv
  docs/
    PIPELINE_ARCHITECTURE.md
    CASE1_full_raw_data_workflow.md
    CASE2_lightweight_marker_plus_gpcr_workflow.md
    EVIDENCE_LABELS.md
    SOURCE_DATA_TRACKER.md
    REGION_MAPPING_GUIDE.md
  A_Allen_only_computational_module/
    A01_setup_cache_and_metadata.py
    A02_region_mapping_merfish_ccf.py
    A03_allen_gpcr_expression.py
    A04_allen_marker_discovery_template.py
  B_Published_marker_input_module/
    B01_standardize_published_markers.py
    B02_validate_marker_presence_in_allen.py
  C_Published_raw_data_extraction_module/
    C01_download_source_data_template.py
    C02_standardize_paper_dataset.py
    C03_compute_paper_gpcr_marker_validation.py
  D_Final_integration_module/
    D01_merge_evidence_tables.py
    D02_create_final_probe_workbook.py
    D03_make_removed_or_downgraded_table.py
  matlab_review/
    review_computed_outputs.m
```
