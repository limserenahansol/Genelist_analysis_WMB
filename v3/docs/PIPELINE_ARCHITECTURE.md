# Pipeline Architecture

## Overview

This workflow separates source types and evidence types so the final probe panel does not confuse “candidate GPCRs” with “computed high GPCRs.”

```text
                         ┌──────────────────────────┐
                         │  Current v6 workbook      │
                         │  candidate genes          │
                         └────────────┬─────────────┘
                                      │
┌──────────────────────────┐          │          ┌────────────────────────────┐
│ A. Allen-only module      │          │          │ B. Published markers module │
│ WMB 10X, MERFISH, CCF,    │          │          │ literature cell markers      │
│ taxonomy, Consensus-WMB   │          │          └────────────┬───────────────┘
└────────────┬─────────────┘          │                       │
             │                        │                       │
             │                        ▼                       │
             │           ┌────────────────────────────┐        │
             └──────────▶│ D. Final integration module │◀───────┘
                         │ evidence-aware workbook     │
             ┌──────────▶│ keep/downgrade/add/remove   │
             │           └────────────────────────────┘
             │
┌────────────┴─────────────┐
│ C. Published raw-data     │
│ extraction module         │
│ paper datasets            │
└──────────────────────────┘
```

## Module A. Allen-only computational module

### Goal

Compute GPCR expression and marker rankings from Allen data directly.

### Subtasks

1. Set up `AbcProjectCache`.
2. Download/load WMB metadata and taxonomy.
3. Map regions using MERFISH/CCF and taxonomy metadata.
4. Extract selected GPCR genes from WMB 10X.
5. Optionally compute all-gene marker discovery.
6. Validate against Consensus-WMB.

### Output tables

- `Allen_Metadata_Audit.csv`
- `Allen_Region_Mapping.csv`
- `Allen_CellTypes_By_Region.csv`
- `Allen_GPCR_Ranking.csv`
- `Allen_Marker_Ranking.csv`

## Module B. Published-marker input module

### Goal

Use published/curated cell-type markers as a marker backbone when all-gene marker discovery is too large.

### Subtasks

1. Build a standardized marker CSV.
2. Split marker lists into long format.
3. Check whether each marker gene exists in Allen gene metadata.
4. Flag marker evidence level: canonical, paper-supported, candidate, or exclusion marker.

### Output tables

- `Published_Cell_Marker_Backbone.csv`
- `Published_Cell_Marker_Long.csv`
- `Marker_Presence_In_Allen.csv`

## Module C. Published raw-data extraction module

### Goal

When paper source data are available, compute GPCR and marker evidence directly from those datasets.

### Why it is separate

Each paper uses a different format: `.h5ad`, `.rds`, `.mtx`, `.csv`, `.loom`, ArrayExpress raw files, figshare annotated files, or supplementary Excel source-data files. One universal downloader is unsafe, so this module uses a source manifest and per-paper adapters.

### Output tables

- `Paper_Dataset_Manifest_Checked.csv`
- `Paper_CellType_Metadata.csv`
- `Paper_GPCR_Ranking.csv`
- `Paper_Marker_Ranking.csv`
- `Paper_Validation_Summary.csv`

## Module D. Final integration module

### Goal

Create the final evidence-aware workbook.

### Inputs

- A outputs: Allen-computed GPCR/marker evidence
- B outputs: published marker backbone
- C outputs: paper-computed validation
- Current workbook/candidate list

### Output workbook sheets

1. `README`
2. `Region_Mapping_Final`
3. `CellTypes_By_Region`
4. `Computed_GPCR_Ranking`
5. `Computed_Marker_Ranking`
6. `Published_Marker_Backbone`
7. `Paper_Data_Validation`
8. `Candidate_vs_Computed_Audit`
9. `Final_Probe_Panel`
10. `Removed_or_Downgraded`
11. `Source_Audit`
