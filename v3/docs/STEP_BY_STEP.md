# Step-by-step playbook (v3 modular pipeline)

This is the complete end-to-end recipe to reproduce `Final_Probe_Panel_v7_modular.xlsx` from scratch.

![v3 pipeline overview](images/v3_pipeline_overview.png)

> Tested on: Windows 11, Python 3.13.3, `abc_atlas_access` 0.2+, manifest `releases/20240330/manifest.json`.

---

## 0. Install & set the cache

```powershell
pip install -r ..\requirements.txt
pip install pyyaml tqdm openpyxl pyarrow
$env:ABC_ATLAS_CACHE = "C:\Users\hsollim\Downloads\abc_atlas_cache"   # or wherever you have ~150 GiB free
```

Disk: the Allen WMB-10X regional log2 `.h5ad` files total ~85 GiB once cached. The full 6-region run touches ~11 of them.

Edit [`config/project_config.yaml`](../config/project_config.yaml) once — paths, manifest pin, thresholds — and every script picks it up automatically.

---

## 1. A00 — preprocess + download

```powershell
$ROOT = "$PWD\v3"; $OUT = "$ROOT\outputs"
python "$ROOT\A_Allen_only_computational_module\A00_preprocess_download.py" `
    --out_dir "$OUT\preprocess"
# optional: also try direct paper raw downloads
#   --paper_manifest "$ROOT\inputs\paper_source_manifest_template.csv" `
#   --paper_download_dir "$OUT\paper_raw"
```

Produces:
- `preprocess_summary.csv` — Python version, free disk, cache size, manifest.
- `allen_metadata_files.csv` — confirmation that the 6 metadata tables loaded.
- `paper_download_status.csv` — per-paper download outcome (only when `--paper_manifest` was passed).

---

## 2. A01 — snapshot Allen WMB-10X & WMB-taxonomy metadata

```powershell
python "$ROOT\A_Allen_only_computational_module\A01_setup_cache_and_metadata.py" `
    --out_dir "$OUT\metadata"
```

Saves a parquet copy of every Allen metadata file we will need downstream so re-runs are fast and reproducible.

---

## 3. A02 — map user labels to Allen ROI acronyms

```powershell
python "$ROOT\A_Allen_only_computational_module\A02_region_mapping_merfish_ccf.py" `
    --out_dir "$OUT\region_mapping"
```

How the matching works:
1. Read `region_of_interest_metadata.csv` (29 ROI rows).
2. For each user label, try **exact acronym** match first (whitelisted in `project_config.yaml -> region_acronym_queries`).
3. If no exact acronym, fall back to **word-boundary regex** on the canonical name field.

Outputs `Region_Mapping_Auto_Draft.csv`. Always open it and confirm before running A03 — for the 6 published-paper regions our defaults are:

| user_label | Allen ROI | confidence |
|---|---|---|
| BMAp | sAMY | high_exact |
| LM | HY | high_exact (LM has no standalone WMB-10X ROI; refine with markers + MERFISH) |
| RE | TH | high_exact |
| CP | STRd | high_exact |
| ORBm | PL-ILA-ORB | high_exact |
| AId | AI | high_exact |

---

## 4. B01 / B02 — published markers

```powershell
python "$ROOT\B_Published_marker_input_module\B01_standardize_published_markers.py" `
    --markers_csv "$ROOT\inputs\curated_marker_template.csv" `
    --out_dir "$OUT\markers"

python "$ROOT\B_Published_marker_input_module\B02_validate_marker_presence_in_allen.py" `
    --cache_dir "$env:ABC_ATLAS_CACHE" `
    --marker_long_csv "$OUT\markers\Published_Cell_Marker_Long.csv" `
    --out_dir "$OUT\markers"
```

`Marker_Presence_In_Allen.csv` flags any genes in your `curated_marker_template.csv` that are not in Allen's gene metadata (typo, alias, etc.). Fix those before A03.

---

## 5. A03 — Allen GPCR expression per region × cell type

```powershell
python "$ROOT\A_Allen_only_computational_module\A03_allen_gpcr_expression.py" `
    --out_dir "$OUT\gpcr_full" `
    --gpcr_csv "$ROOT\inputs\mouse_gpcr_universe_template.csv" `
    --region_mapping_csv "$OUT\region_mapping\Region_Mapping_Auto_Draft.csv" `
    --levels subclass supertype cluster
```

Produces three CSVs (one per taxonomy level), each with:

| column | meaning |
|---|---|
| `region_user` | your label (BMAp, LM, RE, CP, ORBm, AId) |
| `subclass` / `supertype` / `cluster` | Allen WMB taxonomy label |
| `gpcr_gene` | from `mouse_gpcr_universe_template.csv` |
| `n_cells` | number of cells in this group |
| `mean_log2_expr` | average log2 CPM in this group |
| `pct_expr` | % of cells with detectable expression |
| `rank_mean_expr`, `rank_pct_expr`, `rank_combined` | ranks within (region, level) |
| `specificity_log2` | this group's mean − max of other groups' means |

Only the regional `.h5ad` matrices that actually contain the target cells are downloaded — that's the reason A03 is fast on a warm cache.

---

## 6. D02 — assemble the final workbook

```powershell
python "$ROOT\D_Final_integration_module\D02_create_final_probe_workbook.py" `
    --out_xlsx "$OUT\Final_Probe_Panel_v7_modular.xlsx" `
    --allen_subclass_csv  "$OUT\gpcr_full\Allen_GPCR_Ranking_subclass.csv" `
    --allen_supertype_csv "$OUT\gpcr_full\Allen_GPCR_Ranking_supertype.csv" `
    --allen_cluster_csv   "$OUT\gpcr_full\Allen_GPCR_Ranking_cluster.csv" `
    --published_marker_csv "$OUT\markers\Published_Cell_Marker_Long.csv" `
    --region_mapping_csv "$OUT\region_mapping\Region_Mapping_Auto_Draft.csv" `
    --celltype_anchor_csv "$ROOT\inputs\celltype_to_subclass_anchor.csv" `
    --top_n_gpcrs_in_summary 8
```

The workbook has 10 sheets:

| Sheet | What's in it |
|---|---|
| `README` | thresholds + manifest pinned for this run |
| **`Final_Summary`** | **the human-friendly probe planning table** — one row per (region, cell type, anchor subclass), with positive markers, exclusion markers, top GPCRs that pass `keep`/`keep_validate_spatially` thresholds, and a fallback list of top GPCRs by raw expression in case nothing passes. **Open this sheet first.** |
| `Region_Mapping_Final` | exact ROI per user label |
| `CellType_Subclass_Anchors` | the curated user-cell-type → Allen-subclass mapping that drives `Final_Summary` |
| `Computed_GPCR_subclass` | A03 subclass-level long table |
| `Computed_GPCR_supertype` | A03 supertype-level long table |
| `Computed_GPCR_cluster` | A03 cluster-level long table |
| `Published_Marker_Backbone` | curated marker long table |
| `Final_Probe_Panel` | full evidence ledger: 80,652 rows, all the above joined + `validation_status` + `final_recommendation` + `specificity_log2` |
| `Removed_or_Downgraded` | the rows D02 recommends dropping |

---

## 7. Reading `Final_Summary` and `Final_Probe_Panel`

### `Final_Summary` (use this for probe ordering)

One row per (region, cell type, Allen subclass anchor). The columns you actually act on:

| Column | What to do with it |
|---|---|
| `cell_type_marker_genes` | put these on the panel as cell-type-defining markers |
| `exclusion_markers` | use to gate cells that should NOT be the target |
| `top_GPCRs_to_choose` | the ordered shortlist that passed `keep` / `keep_validate_spatially` — these are your best evidence-supported GPCRs |
| `top_GPCRs_by_expression` | fallback list ranked purely by Allen mean log2 — useful when your cell type happens to express only ubiquitous GPCRs |
| `n_cells_in_anchor` | sample-size sanity check (≥ 30 is required for a reliable estimate) |
| `warning` | flags low cell counts and cell types where no GPCR passed thresholds |

### `Final_Probe_Panel` (full evidence ledger)

![v3 decision tree](images/v3_decision_tree.png)

If you need to dig in, filter `Final_Probe_Panel` to that `region_user`, then:

1. Sort by `taxonomy_level == "subclass"` and `final_recommendation == "keep"`.
2. Sort ascending by `combined_rank_score` (smaller = better — combines mean rank and pct rank).
3. Confirm `specificity_log2 > 0` (positive = enriched in this cell type vs other cell types in the same region).
4. Cross-check `marker_role` (if not blank, this gene is also in `curated_marker_template.csv` for that cell type — strong signal).

Example top hits per region (already in the published `Final_Probe_Panel`):

| Region | Subclass | Top GPCR | n_cells | mean_log2 | pct_expr | specificity_log2 |
|---|---|---|---|---|---|---|
| CP | 061 STR D1 Gaba | Gpr88 | 30 | 8.75 | 100% | 4.18 |
| CP | 062 STR D2 Gaba | Grm5 | 18,139 | 11.38 | 100% | 0.02 |
| ORBm | 047 Sncg Gaba | Cnr1 | 1,450 | 12.16 | 100% | 2.64 |
| AId | 047 Sncg Gaba | Cnr1 | 1,662 | 12.07 | 99.94% | 2.39 |
| BMAp | 047 Sncg Gaba | Cnr1 | 111 | 11.50 | 100% | 1.41 |
| RE (TH) | 321 Astroependymal NN | Adcyap1r1 | 322 | 8.15 | 89.75% | 2.42 |
| LM (HY) | 331 Peri NN | Adora2a | 1,540 | 4.31 | 51.36% | 2.01 |

---

## 8. Provenance

Every script appends a JSONL record to `run_log.jsonl` with: timestamp, hostname, Python version, git commit, manifest version, parameters, and counts. That's enough to reconstruct exactly which Allen release and which thresholds produced any given `Final_Probe_Panel.xlsx`.

```powershell
Get-Content "$OUT\gpcr_full\run_log.jsonl"
Get-Content "$OUT\run_log.jsonl"
```
