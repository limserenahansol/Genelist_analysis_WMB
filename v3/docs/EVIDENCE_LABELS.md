# Evidence Labels

Use these labels in every table and workbook sheet.

| Label | Definition | Strength |
|---|---|---|
| `Allen_WMB_10X_computed` | Expression computed from Allen WMB 10X data | Strong |
| `Allen_MERFISH_spatial_computed` | Cell/cluster spatial location computed from MERFISH/CCF data | Strong for region mapping |
| `Allen_imputed_MERFISH_computed` | Gene expression checked in Allen imputed MERFISH | Moderate to strong |
| `Consensus_WMB_validated` | Pattern validated in Consensus-WMB | Strong validation |
| `Paper_dataset_computed` | Expression computed from downloaded paper source dataset | Strong for that paper/context |
| `Paper_source_table_supported` | Supported by paper source table or supplementary file | Moderate |
| `Paper_text_supported` | Supported by paper text/figure, not recomputed | Moderate |
| `Published_marker_canonical` | Canonical cell-type marker from literature | Strong for marker identity; not necessarily region-specific |
| `Literature_candidate_GPCR` | GPCR chosen from known biology, not computed | Candidate only |
| `Unvalidated_candidate` | Included in older workbook but not validated | Weak |
| `Downgrade_or_remove` | Weak, unsupported, ambiguous, or wrong-region after audit | Remove/downgrade |

## Recommended validation status

| Status | Meaning |
|---|---|
| `final_keep` | Strong computed expression + region/cell-type support |
| `keep_validate_spatially` | Expression looks good, region boundary needs spatial check |
| `candidate_to_validate` | Reasonable candidate but no direct computation yet |
| `downgrade_low_expression` | Weak expression in target cell type |
| `downgrade_low_specificity` | Expressed broadly, not useful as target marker |
| `remove_wrong_region_or_celltype` | Conflicts with region/cell-type evidence |
| `too_few_cells` | Not enough cells for reliable computation |
| `ambiguous_acronym` | Region or label is unclear, e.g., LM or Ald/AId |
