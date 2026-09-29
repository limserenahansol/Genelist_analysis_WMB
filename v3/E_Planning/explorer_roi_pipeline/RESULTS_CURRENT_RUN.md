# Current run — revised Explorer ROI pipeline (247-gene pilot)

Date: 2026-09-29. Seed 0. Raw Xenium folders were not modified.

## Conclusion

The revised pipeline completed for the ORBm and BMAp Explorer ROIs. It recovers broad
cell-class structure with moderate agreement to Allen reference-transfer labels and good
stability across Leiden resolutions. The current run cannot evaluate Ai14 overlap because
tdTomato is absent, and it cannot compare animals because the two slides are different
anatomies.

## Validation

| Check | ORBm right | BMAp left |
|---|---:|---:|
| Explorer cells / after QC | 915 / 914 | 1,145 / 1,077 |
| Leiden clusters at resolution 1.0 | 15 | 15 |
| ARI: resolution 1.0 vs 0.5 | 0.776 | 0.880 |
| ARI: resolution 1.0 vs 1.5 | 0.793 | 0.838 |
| Allen coarse-label ARI | 0.500 | 0.503 |
| Allen coarse-label NMI | 0.738 | 0.673 |
| Same-Leiden neighbor fraction | 0.294 | 0.269 |
| Permuted neighbor fraction | 0.097 | 0.089 |
| tdTomato on panel | no | no |

The marker-module baseline leaves 225/914 ORBm cells and 273/1,077 BMAp cells unassigned.
Module and onboard-cluster agreement are same-matrix concordance checks. Allen reference
transfer is reported separately.

## Changes in this revision

- tdTomato, iCre, and predefined activity/state genes are excluded from identity PCA but retained
  for downstream expression analysis.
- kNN indexing now uses exactly k neighbors and retains the closest nonself neighbor.
- Marker outputs include fraction in, fraction out, and detection difference.
- Neighborhood output uses 499 label permutations and reports log2 observed/expected.
- Spatial expression maps use raw transcripts per cell.
- Added concise cell-identity and GPCR/state/TF figures.
- Story 2 now implements Ai14 overlap and threshold sensitivity when tdTomato is available.
- Story 3 now exports animal-level composition and pseudobulk matrices.

## Interpretation limits

- This is one pilot specimen per anatomy.
- ORBm and BMAp are separate questions, not a valid contrast.
- The 247-gene pilot cannot validate custom-panel genes it did not measure.
- Cluster marker p-values are exploratory because clustering and marker ranking use the same
  cells. New cell types require independent-animal replication and multiple coherent markers.

See `PIPELINE_REVIEW.md` for the recommended real-data workflow.

## Expanded six-bundle update

All three regions for slide 0063814 (ORBm) and all three regions for slide 0063817 (BMAp) were
inventoried. XOA reported 421,520 cells in total, decoded Q20 of 86.1%–96.5%, and transcript
assignment of 83.8%–89.4%.

Five target ORBm/BMAp ROI selections were analyzable and produced 4,933 QC-passing cells:

- ORBm 0063814 Region 2 right: 929 QC cells; polygon-derived and approximate.
- ORBm 0063814 Region 3 right: 914 QC cells.
- ORBm 0063814 Region 3 left: 1,013 QC cells.
- BMAp 0063817 Region 1 left: 1,077 QC cells.
- BMAp 0063817 Region 1 right: 1,000 QC cells.

Marker-module composition total-variation distances were 0.106 for ORBm Region 3 left/right,
0.091 for ORBm right Region 2/3, and 0.215 for BMAp Region 1 left/right. These quantify
within-mouse ROI variability and are not treatment effects.

See `outputs/six_bundle_inventory/`, `outputs/expanded_roi_comparison/`, and
`TENX_GUIDE_AND_FOUR_MOUSE_PLAN.md`.

## PI presentation and simulated demonstrations

- `presentation/ORBm_BMAp_Xenium_pipeline_results_5slides_EN.pptx` is the validated
  five-slide English PI deck.
- `toy_demo_results/` shows the expected Story 2 and Story 3 outputs using explicitly
  labeled simulated data.
- Simulated figures demonstrate output structure only and are not biological results.
