# Quickstart Commands

## 0. Create environment

```bash
conda create -n allen_abc python=3.11 -y
conda activate allen_abc
pip install "abc_atlas_access[notebooks] @ git+https://github.com/alleninstitute/abc_atlas_access.git"
pip install pandas numpy scipy scanpy anndata pyarrow openpyxl tqdm pyyaml
```

## 1. Module A: Allen metadata audit

```bash
python A_Allen_only_computational_module/A01_setup_cache_and_metadata.py \
  --cache_dir F:/Allen_ABC_Atlas \
  --out_dir F:/Allen_ABC_Project/output/A_metadata
```

## 2. Module B: standardize published markers

```bash
python B_Published_marker_input_module/B01_standardize_published_markers.py \
  --markers_csv inputs/curated_marker_template.csv \
  --out_dir F:/Allen_ABC_Project/output/B_markers
```

## 3. Module B: check marker presence in Allen

```bash
python B_Published_marker_input_module/B02_validate_marker_presence_in_allen.py \
  --cache_dir F:/Allen_ABC_Atlas \
  --marker_long_csv F:/Allen_ABC_Project/output/B_markers/Published_Cell_Marker_Long.csv \
  --out_dir F:/Allen_ABC_Project/output/B_markers
```

## 4. Module A: region mapping candidate search

```bash
python A_Allen_only_computational_module/A02_region_mapping_merfish_ccf.py \
  --metadata_parquet F:/Allen_ABC_Project/output/A_metadata/WMB-10X__cell_metadata_with_cluster_annotation.parquet \
  --out_dir F:/Allen_ABC_Project/output/A_region_mapping
```

Manually inspect `Region_Mapping_Manual_Checklist.csv`, then make a final region mapping CSV.

## 5. Module A: GPCR expression extraction

```bash
python A_Allen_only_computational_module/A03_allen_gpcr_expression.py \
  --cache_dir F:/Allen_ABC_Atlas \
  --out_dir F:/Allen_ABC_Project/output/A_gpcr \
  --gpcr_csv inputs/mouse_gpcr_universe_template.csv \
  --region_mapping_csv F:/Allen_ABC_Project/output/A_region_mapping/Region_Mapping_Final.csv \
  --min_cells 30
```

## 6. Module C: paper source-data validation

Only run once you have downloaded/standardized a paper dataset.

```bash
python C_Published_raw_data_extraction_module/C03_compute_paper_gpcr_marker_validation.py \
  --expression_parquet F:/paper_data/Paper_Expression_Standardized.parquet \
  --metadata_parquet F:/paper_data/Paper_Metadata_Standardized.parquet \
  --gpcr_csv inputs/mouse_gpcr_universe_template.csv \
  --cell_type_col cell_type \
  --region_col region \
  --out_dir F:/Allen_ABC_Project/output/C_paper_validation
```

## 7. Module D: final workbook

```bash
python D_Final_integration_module/D02_create_final_probe_workbook.py \
  --out_xlsx F:/Allen_ABC_Project/output/final/Final_Probe_Panel_v7_modular.xlsx \
  --allen_gpcr_csv F:/Allen_ABC_Project/output/A_gpcr/Allen_GPCR_Ranking.csv \
  --published_marker_csv F:/Allen_ABC_Project/output/B_markers/Published_Cell_Marker_Long.csv \
  --paper_gpcr_csv F:/Allen_ABC_Project/output/C_paper_validation/Paper_GPCR_Ranking.csv \
  --region_mapping_csv F:/Allen_ABC_Project/output/A_region_mapping/Region_Mapping_Final.csv
```
