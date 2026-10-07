# Anja recommendations: pipeline implementation

## Conclusion

The pipeline now records the run-level false-positive estimate without subtracting it, recomputes ROI QC, applies one shared count/gene cutoff across a run, flags genes near negative-control-probe background, quantifies ROI-border sensitivity, and provides a nucleus-only segmentation sensitivity analysis. The final 299-gene panel has adequate Allen marker support for the **12 intended ORBm** and **8 intended BMAp** subclass anchors.

## What changed

1. **False-positive estimate**
   - `run_from_explorer.py` reads `metrics_summary.csv` and writes `run_level_qc_metrics.csv`.
   - The estimate remains a run-level QC value. It is reported as transcripts/cell and as a fraction of the ROI median; it is never subtracted.
   - `gene_background_sanity.csv` compares each gene with the 95th percentile across negative-control probes in the same QC-passing ROI. Flags trigger review, not automatic deletion.

2. **ROI metrics**
   - `qc_cell_metrics.csv` contains recomputed count, detected-gene, area, and pass/fail values for every exported ROI cell.
   - `01_qc.png` compares full-section and ROI counts and shows the count, gene, and area cutoffs.

3. **Shared low-count threshold**
   - The config has one top-level `qc` block. The same `min_gene_counts` and `min_genes` values apply to every ROI in that run.
   - The default remains 20 gene transcripts and 5 detected genes. `qc_threshold_sensitivity.csv` reports retention at 10/15/20 transcripts crossed with 5/10 genes. Inspect the pooled low-end distributions, then freeze one rule before condition comparisons.

4. **Spatial statistics**
   - `run_spatial_context.py` computes neighborhood enrichment and Moran's I with explicit permutation tests. These are the core analyses for which Squidpy was suggested; the current implementation keeps Squidpy optional and avoids adding a required dependency.

5. **Nucleus-expansion sensitivity**
   - `run_segmentation_sensitivity.py` reconstructs all assigned and `overlaps_nucleus == 1` counts from `transcripts.parquet`.
   - It checks input reconstruction, signal retention, marker-module agreement, and identity-only Leiden agreement using the same QC thresholds.
   - This is a sensitivity analysis. It does not replace the primary segmentation or silently resegment data. Baysor, ProSeg, or ovrlpy remain follow-up options if nucleus-only results materially disagree.

6. **ROI border cells**
   - When both Explorer cell IDs and polygon coordinates are available, `roi_boundary_selection_sensitivity.csv` compares the Explorer selection with centroid-in-polygon inclusion.
   - `summary.json` reports the excluded fraction and the total-variation change in onboard-cluster composition. This tests whether the approximately 3% border loss is compositionally important.

7. **Allen subclass markers in the final 299 panel**
   - `validate_panel299_allen_subclasses.py` evaluates the exact 299-gene workbook.
   - Marker coverage is checked independently from donor-held-out classification.
   - The primary classifier excludes reporter, activity/IEG, morphine-state, and circadian blocks. Every donor is held out in turn; a nearest-centroid classifier is the simple baseline.
   - Passing criteria were fixed before interpretation: at least two markers per target with >=50% detection and >=10 percentage-point margin, regional macro-F1 >=0.75, and every target-subclass recall >=0.60.

## Interpretation boundary

This validation supports the intended 20 Allen subclass anchors. It does not claim that 299 genes resolve every subclass in the broader PL-ILA-ORB or sAMY atlas. The panel was partly selected from Allen data, so final validation still requires production Xenium detection, reference-transfer confidence, and reproducibility across mice.

## Verified pilot results

- Run-level false-positive estimates were 0.223 transcripts/cell for the ORBm section and 0.267 for the BMAp section. These were 0.051% and 0.145% of the corresponding ROI medians. No subtraction was applied.
- One stock-panel gene (`Chodl`) was flagged near negative-control-probe background in the ORBm ROI; none was flagged in BMAp. `Chodl` is not in the final standalone 299-gene panel. The check must be rerun on production custom-panel data.
- Complete-containment exports excluded 39/954 centroid-in-polygon ORBm cells (4.09%) and 35/1,180 BMAp cells (2.97%). The onboard-cluster composition total variation was 0.009 and 0.030, respectively, indicating little composition change in this pilot.
- QV>=20 transcript reconstruction matched each processed matrix exactly. Under nucleus-only counts and the same 20-transcript/5-gene thresholds, 94.7% of ORBm and 90.2% of BMAp cells remained. Gene-mean Spearman correlations were 0.992 and 0.985; marker-module agreement was 0.773 and 0.735; Leiden ARI was 0.613 and 0.677. The signal is broadly preserved, but the imperfect label/cluster agreement means nucleus-expansion spillover remains a real limitation rather than a negligible one.
- In the final 299-panel Allen check, every intended anchor had at least two strong markers; the observed range was 4-8 in ORBm and 3-28 in BMAp. Donor-held-out macro-F1 was 0.921 for ORBm and 0.975 for BMAp. Minimum target-subclass recall was 0.740 and 0.943.
- The official 2026-07-11 Allen manifest was compared with the locally cached 2026-04-15 manifest. The `WMB-10X`, `WMB-10Xv2`, and `WMB-10Xv3` entries were identical, so the expression and taxonomy files used here are unchanged in the latest manifest.
