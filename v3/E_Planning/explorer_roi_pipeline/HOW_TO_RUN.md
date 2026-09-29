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
- `xenium`
- `explorer_cells_csv`
- `explorer_coordinates_csv`
- `module_set`
- optional `reference_labels_csv`, `reference_id_column`, and `reference_label_column`
- optional `tdtom_min_counts` after control-based calibration

Then run all three commands with the new config.

For the primary tdTom × Active/Passive design, also run:

```text
python run_factorial_tdtom_active_passive.py --config YOUR_REAL_CONFIG.json
Rscript run_factorial_limma_voom.R outputs/factorial_tdtom_active_passive
```

The factorial export and model implement five planned contrasts: tdTom+ versus tdTom− within
each condition, Active versus Passive within each reporter state, and the condition × reporter
interaction. See `PRIMARY_AIM_ANALYSIS.md` before interpreting a tdTom-enriched cluster as a
new cell type.

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
