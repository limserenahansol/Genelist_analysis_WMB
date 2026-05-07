# Case 1: Full Raw-Data Workflow

## When to use

Use this workflow when you need the most defensible final probe panel and you have sufficient storage/RAM/HPC support.

## Source data

| Source | Purpose |
|---|---|
| Allen WMB 10X | Transcriptome-wide expression by cell type |
| Allen WMB taxonomy | Class/subclass/supertype/cluster identity |
| Allen MERFISH + CCF | Region mapping and spatial validation |
| Allen imputed MERFISH | Spatial gene checking for more genes than base MERFISH panel |
| Consensus-WMB | Cross-dataset validation |
| Published paper source datasets | Region-specific validation, especially BMAp/amygdala and CP/striatum |

## Steps

```text
1. Run A01_setup_cache_and_metadata.py
2. Run A02_region_mapping_merfish_ccf.py
3. Run A03_allen_gpcr_expression.py
4. Run A04_allen_marker_discovery_template.py
5. Run C01/C02/C03 for paper datasets with available source data
6. Run D01/D02/D03 to generate the final workbook
```

## Main outputs

```text
Allen_Region_Mapping.csv
Allen_CellTypes_By_Region.csv
Allen_GPCR_Ranking.csv
Allen_Marker_Ranking.csv
Paper_GPCR_Ranking.csv
Paper_Marker_Ranking.csv
Final_Probe_Panel_v7.xlsx
```

## Computational metrics

For each region x cell type x GPCR:

```text
n_cells
mean_log2_expr
pct_expr
mean_expr_background_same_region
mean_expr_same_celltype_other_regions
log2_enrichment_same_region
specificity_score
rank_within_region_celltype
evidence_source
validation_status
```

For each marker gene:

```text
mean_expr_target
pct_expr_target
mean_expr_background
pct_expr_background
log2_fc
specificity_score
marker_rank
adjusted_p_value, if using DE testing
```

## Final interpretation

A gene is final-order-ready only if it passes:

```text
1. Correct region mapping
2. Correct cell-type assignment
3. Computed expression support
4. Reasonable percent-expressing cells
5. Specificity or enrichment support
6. Literature/paper consistency, if available
```
