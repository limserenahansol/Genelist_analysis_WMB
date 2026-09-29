# ORBm/BMAp Xenium Explorer ROI pipeline

This folder contains the reviewed processing workflow for the ORBm and BMAp Xenium pilot and
the planned Ai14 tdTomato by Active/Passive experiment.

## Current evidence

- The real 247-feature pilot contains 914 QC-passing ORBm cells and 1,077 QC-passing BMAp cells.
- Broad cell classes are recoverable and moderately concordant with Allen reference labels.
- tdTomato is absent from the pilot matrix, so Story 2 correctly writes `SKIPPED.md`.
- There is one animal per anatomy with no condition field, so Story 3 remains descriptive.

## Main files

- `run_from_explorer.py`: QC, identity-only clustering, marker summaries and spatial analysis.
- `run_story2_tdtom.py`: reporter gating, cell-type enrichment and threshold sensitivity.
- `run_story3_mouse_ab.py`: animal-level composition and pseudobulk export.
- `run_factorial_tdtom_active_passive.py`: factorial reporter-by-condition export.
- `run_factorial_limma_voom.R`: animal-level gene models and five planned contrasts.
- `PRIMARY_AIM_ANALYSIS.md`: scientific decision logic.
- `RESULTS_CURRENT_RUN.md`: verified pilot results and limitations.
- `presentation/ORBm_BMAp_Xenium_pipeline_results_5slides_EN.pptx`: five-slide English PI deck.

## Real and simulated outputs

`results_current/real/` contains the compact, verified pilot summaries and selected figures.
`results_current/toy/` contains figures explicitly labeled simulated data that demonstrate the
expected output when reporter-aware, replicated data arrive. Full local runs write to `outputs/`
and `toy_demo_results/` as documented in `HOW_TO_RUN.md`.

The GitHub package intentionally excludes processed `.h5ad` files, per-cell tables and raw
Xenium folders. Those files remain local and can be regenerated from the documented config.
