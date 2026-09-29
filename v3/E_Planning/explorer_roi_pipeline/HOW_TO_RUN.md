# Run the Explorer ROI pipeline

Run from this folder or use the full paths below.

## Current 247-gene pilot

```text
python run_from_explorer.py --config rois_current.json
python run_story2_tdtom.py --config rois_current.json
python run_story3_mouse_ab.py --config rois_current.json
```

Expected behavior:

- `run_from_explorer.py` runs cell identity, marker, composition, spatial, and ROI-QC analyses.
- Story 2 writes `SKIPPED.md` because tdTomato is absent from the 247-gene pilot.
- Story 3 writes descriptive animal-level exports only. ORBm and BMAp are different anatomies
  and cannot be treated as two biological replicates.

Outputs are written under `outputs/<roi_name>/`, `outputs/story2_tdtom/`, and
`outputs/story3_mouse_ab/`.

## Future reporter-aware production experiment

Copy `rois_later_template.json` to a new config. For every ROI provide:

- `roi_name`
- `anatomy`
- `animal_id`
- `condition`
- `section_id`
- `xenium`
- `explorer_cells_csv`
- `explorer_coordinates_csv`
- `module_set`
- optional `reference_labels_csv`, `reference_id_column`, and `reference_label_column`
- optional `tdtom_min_counts` after control-based calibration

Then run all three commands with the new config.

For the planned 4-mouse × 2-anatomy × 3-section experiment, fill
`four_mouse_24roi_manifest_template.csv`, then generate and validate the flat JSON:

```text
python make_config_from_manifest.py --manifest four_mouse_24roi_manifest_template.csv --output rois_four_mouse_generated.json
```

For the primary tdTom × Active/Passive design, also run:

```text
python run_factorial_tdtom_active_passive.py --config YOUR_REAL_CONFIG.json
Rscript run_factorial_limma_voom.R outputs/factorial_tdtom_active_passive
python run_tdtom_novel_subtype.py --config YOUR_REAL_CONFIG.json
```

The factorial export and model implement five planned contrasts: tdTom+ versus tdTom− within
each condition, Active versus Passive within each reporter state, and the condition × reporter
interaction. See `PRIMARY_AIM_ANALYSIS.md` before interpreting a tdTom-enriched cluster as a
new cell type.

`run_tdtom_novel_subtype.py` performs the unbiased subtype search within each known parent type.
It excludes reporter/state genes from clustering, checks tdTom enrichment only afterward, requires
mouse-consistent non-state markers and resolution stability, and performs leave-one-mouse-out marker
validation. Its strongest label is `candidate_novel_subtype_requires_external_validation`; spatial
coherence and reference-atlas novelty still have to be checked before naming a subtype.

New drawings from 2026-09-29 are listed in `NEW_ROIS_2026-09-29.md` and were run with `rois_new_exports.json`.

## Optional Seurat check (does not replace the Python path)

The 10x R tutorial's single-sample steps are in `run_seurat_10x_path.R`. On the current ROIs it uses the same Explorer Cell IDs, then Seurat normalization, PCA, Louvain clustering at resolution 1.0, Wilcoxon markers, and a `cell_groups_seurat_cluster.csv` for Explorer.

```text
Rscript run_seurat_10x_path.R
```

Harmony, sketch, and BPCells are the multi-sample part of that tutorial. They are not run here: each ROI has about 1,000 cells, and ORBm and BMAp are different anatomies, not batches of one experiment. Banksy is the R-only spatial clustering add-on and is not installed. The Python script remains the pipeline that runs after an Explorer download.

Verified on the 247-gene pilot: Seurat Louvain versus the Python Leiden labels had ARI 0.70 (orbm_right, 10 vs 14 clusters) and 0.77 (bmap_left, 10 vs 15 clusters).

## Explorer exports

After drawing an ROI, export the Cell ID stats CSV and coordinate CSV. The coordinate CSV uses
micrometers and can be overlaid with cell centroids. Keep the GeoJSON as an Explorer record; it
uses image pixels and needs an affine transform before overlay.

Do not edit files under `D:\output-XETG00...`. The scripts read raw Xenium files and write
only into this pipeline folder.

## Main PI-facing figures

- `10_cell_identity_overview.png`
- real-data `01_tdtom_overlap_summary.png`
- real-data `02_<anatomy>_tdtom_cell_type_enrichment.png`
- `11_gpcr_state_tf_overview.png`
- `outputs/factorial_tdtom_active_passive/01_<anatomy>_tdtom_positive_composition_active_passive.png`

See `PIPELINE_REVIEW.md` for the scientific interpretation and limitations.
The exact package versions used for the verified rerun are in `environment_versions.json`.

The PI-facing summary deck is
`presentation/ORBm_BMAp_Xenium_pipeline_results_5slides_EN.pptx`.

## Six current bundles and expanded ROI exports

```text
python run_six_bundle_inventory.py --config six_xenium_bundles.json
python run_from_explorer.py --config rois_expanded_available.json
python run_story2_tdtom.py --config rois_expanded_available.json
python run_story3_mouse_ab.py --config rois_expanded_available.json
python summarize_expanded_rois.py --config rois_expanded_available.json
python run_tdtom_novel_subtype.py --config rois_expanded_available.json
```

The Region 2 ORBm entry has no Explorer cell-ID export. The pipeline derives cells whose centroids
fall within `orbm_right_coordinates.csv`, joins XOA graph-cluster labels, and records the source and
count discrepancy in `summary.json`. Replace this fallback with a `*_cells_stats.csv` export when
available.

The current 247-gene pilot writes `outputs/story2_novel_subtype/SKIPPED.md` because `tdTomato`
is absent.
