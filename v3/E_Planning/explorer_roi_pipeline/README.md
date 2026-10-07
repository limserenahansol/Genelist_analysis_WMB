# ORBm/BMAp Xenium Explorer ROI pipeline

This folder contains the reviewed processing workflow for the ORBm and BMAp Xenium pilot and
the planned Ai14 tdTomato by Active/Passive experiment.

## Current evidence

- The real 247-feature pilot contains 914 QC-passing ORBm cells and 1,077 QC-passing BMAp cells.
- Broad cell classes are recoverable and moderately concordant with Allen reference labels.
- tdTomato is absent from the pilot matrix, so Story 2 correctly writes `SKIPPED.md`.
- There is one animal per anatomy with no condition field, so Story 3 remains descriptive.
- The six-bundle inventory found 421,520 XOA cells across three ORBm and three BMAp regions.
- Five available target ROI selections produced 4,933 QC-passing cells and 11 figures per ROI.
- The final 299-gene panel passed the intended Allen-anchor check: donor-held-out macro-F1 was
  0.921 for 12 ORBm subclasses and 0.975 for 8 BMAp subclasses after state/reporter exclusion.

## Main files

- `run_from_explorer.py`: QC, identity-only clustering, marker summaries and spatial analysis.
- `run_story2_tdtom.py`: reporter gating, cell-type enrichment and threshold sensitivity.
- `run_tdtom_novel_subtype.py`: unbiased identity-gene clustering and cross-mouse validation of
  tdTom-associated candidate subtypes within known parent cell types.
- `run_spatial_context.py`: optional neighborhood-enrichment and Moran's I spatial validation.
- `run_segmentation_sensitivity.py`: `overlaps_nucleus` sensitivity check for 5-µm
  nucleus-expansion segmentation.
- `validate_panel299_allen_subclasses.py`: marker coverage plus leave-one-donor-out Allen
  validation of the exact final 299-gene panel.
- `derive_bla_cea_allen_markers.py`: reproducible Allen marker ranking restricted to measured genes.
- `run_bla_cea_reference_transfer.py`: Allen sAMY-to-Xenium Seurat label transfer plus an
  independent regularized-classifier check for BLA and CEA.
- `run_seurat_label_transfer_generic.R`: generic Seurat anchor-transfer helper used by that check.
- `summarize_bla_cea_refined.py`: BLA/CEA baseline-versus-region-specific validation summary.
- `make_tdtom_subtype_toy.py`: reproducible, clearly labeled synthetic candidate-subtype example.
- `run_story3_mouse_ab.py`: animal-level composition and pseudobulk export.
- `run_factorial_tdtom_active_passive.py`: factorial reporter-by-condition export.
- `run_factorial_limma_voom.R`: animal-level gene models and five planned contrasts.
- `run_seurat_10x_path.R`: optional Seurat check of the same Explorer ROIs. It does not replace `run_from_explorer.py`.
- `PRIMARY_AIM_ANALYSIS.md`: scientific decision logic.
- `NOVEL_SUBTYPE_VALIDATION.md`: positive, shuffled-negative, and current-pilot validation results.
- `RESULTS_CURRENT_RUN.md`: verified pilot results and limitations.
- `ANJA_QC_AND_PANEL_VALIDATION.md`: direct mapping from the applied-scientist recommendations
  to pipeline outputs, decision criteria, and interpretation limits.
- `TENX_GUIDE_AND_FOUR_MOUSE_PLAN.md`: 10x tool map, Harmony decision, and the planned
  four-mouse/three-section design.
- `TENX_TOOL_DECISION_AND_BLA_CEA.md`: selected 10x-compatible stack and BLA/CEA evidence limits.
- `REFERENCE_CATALOG_2026-09-29.md` and `.csv`: audited local and web references, with primary,
  public, internal, and derived sources distinguished explicitly.
- `run_six_bundle_inventory.py`: XOA QC and Explorer-export inventory for all six bundles.
- `summarize_expanded_rois.py`: concise yield, composition, and within-mouse ROI comparisons.
- `rois_expanded_available.json`: five analyzable target ROIs currently available.
- `NEW_ROIS_2026-09-29.md`, `prepare_new_rois.py`, and `rois_new_exports.json`: the earlier
  nine-ROI extraction, including exploratory BLA/CEA polygons produced by another agent.
- `run_seurat_10x_path.R`: optional 10x-style Seurat comparison; it does not replace the
  primary Python/animal-level path.
- `four_mouse_24roi_manifest_template.csv` and `make_config_from_manifest.py`: validated
  manifest-to-JSON setup for 2 Active + 2 Passive mice with three sections per anatomy.
- `presentation/ORBm_BMAp_Xenium_pipeline_results_5slides_EN.pptx`: five-slide English PI deck.

## Real and simulated outputs

`outputs/orbm_right/` and `outputs/bmap_left/` contain real pilot results. The figures under
`toy_demo_results/` are explicitly labeled simulated data and demonstrate the output expected
when reporter-aware, replicated data arrive.

The GitHub package intentionally excludes processed `.h5ad` files, per-cell tables and raw
Xenium folders. Those files remain local and can be regenerated from the documented config.

## Expanded pilot outputs

- `outputs/six_bundle_inventory/`: six-bundle XOA metrics, export inventory, and three QC figures.
- `outputs/expanded_roi_comparison/`: cross-ROI summary tables and three concise figures.
- `outputs/<expanded_roi_name>/figures/`: 11 detailed figures for each of five target ROIs.
- `outputs/story3_mouse_ab/`: sections aggregated within animal; descriptive only for this pilot.
- `outputs_bla_cea_refined/`: non-destructive BLA/CEA rerun with region-specific modules, comparison
  summaries, and spatial-context validation.
- `outputs_bla_cea_refined/reference_validation/`: real pilot Allen sAMY reference validation for
  4,246 BLA and 1,905 CEA cells.
- `toy_candidate_subtype/tdtom_candidate_subtype_SIMULATED.png`: synthetic illustration only.
