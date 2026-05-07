# Source Data Tracker

## Allen official sources

| Source | URL | Use in workflow |
|---|---|---|
| ABC Atlas getting started | https://alleninstitute.github.io/abc_atlas_access/notebooks/getting_started.html | `AbcProjectCache`, AWS public data, `.h5ad` format |
| WMB dataset overview | https://alleninstitute.github.io/abc_atlas_access/descriptions/WMB_dataset.html | Main mouse whole-brain source |
| WMB taxonomy | https://alleninstitute.github.io/abc_atlas_access/descriptions/WMB-taxonomy.html | Cell class/subclass/supertype/cluster taxonomy |
| 10X RNA-seq access tutorial | https://alleninstitute.github.io/abc_atlas_access/notebooks/general_accessing_10x_snRNASeq_tutorial.html | Selected-gene extraction using `get_gene_data` |
| Consensus-WMB dataset | https://alleninstitute.github.io/abc_atlas_access/descriptions/Consensus-WMB-dataset.html | Validation against integrated Macosko + Zeng taxonomy |
| Gene lists | https://alleninstitute.github.io/abc_atlas_access/descriptions/gene.html | Gene metadata/reference |

## Published data sources to add

Use the manifest template in `inputs/paper_source_manifest_template.csv`.

| Region | Paper/data type | Required action |
|---|---|---|
| BMAp/amygdala | Mouse amygdala scRNA-seq paper source data, ArrayExpress/figshare/source tables | Download annotated expression + metadata; compute BMAp-related GPCR/marker ranking |
| CP/striatum | Mouse striatum scRNA-seq/spatial data | Validate D1/D2, patch/striosome/matrix/exopatch GPCRs |
| ORBm/AId cortex | Mouse cortical taxonomy and NP-GPCR datasets | Validate cortical subclass-GPCR associations and area specificity |
| LM/mammillary | Mammillary body/hypothalamic datasets | Confirm LM markers and GPCRs; highest caution |
| RE/thalamus | Thalamus/midline atlas or WMB/MERFISH | Validate RE-specific glutamatergic clusters and GPCRs |

## Paper source-data manifest columns

```text
paper_id
title
region_focus
species
data_url
accession
file_type
expected_files
expression_format
metadata_format
cell_type_column
region_column
gene_symbol_column
notes
status
```
