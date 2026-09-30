# BLA/CEA refined pilot snapshot

These compact outputs come from the Allen-informed rerun of four BLA and two CEA ROIs. The original
BMAp-module results remain the baseline. Processed h5ad objects and per-cell files remain local.

- `summary/`: baseline-versus-refined NMI, assignment coverage, composition, and the main figure.
- `allen_reference/`: top markers regenerated from 15,846 Allen STR-shard cells and the 247 measured
  pilot genes.
- `spatial_context/`: neighborhood-enrichment/Moran summary and representative BLA/CEA figures.
- `reference_validation/`: Allen `sAMY` Seurat transfer, independent-classifier agreement, module
  confusion tables, and compact summary figures.
- `per_roi/`: compact summary JSON for each ROI.
- `story2_novel_subtype/SKIPPED.md`: expected skip because this pilot has no `tdTomato` feature.

All six ROIs are sections or hemispheres from one animal. The results are descriptive and cannot be
used as independent-animal inference.
