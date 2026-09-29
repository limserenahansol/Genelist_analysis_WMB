# Scientific and implementation review

Date: 2026-09-28

## Conclusion

The primary analysis is a 2 × 2 design within anatomy and existing cell type:
`tdTom+ / tdTom−` × `Active / Passive`. It first tests whether tdTom+ cells are enriched in
known types, then whether an identity-defined and replicated subtype remains after excluding
reporter/state genes, and finally which GPCR/TF/plasticity genes show reporter, condition, or
interaction effects. See `PRIMARY_AIM_ANALYSIS.md`.

The pipeline is now appropriate for **pilot exploration and workflow validation**, with clear
separation between cell identity, Ai14 reporter overlap, gene-state summaries, spatial
description, and animal-level inference. It is not yet evidence for a treatment effect because
the current pilot has one ORBm slide and one BMAp slide, uses a 247-gene panel without
tdTomato, and has no replicated condition within one anatomy.

The recommended order for the real experiment is:

1. QC cells and confirm comparable ROI sampling.
2. Assign cell identity using external Allen reference labels plus curated marker checks.
3. Use identity genes for clustering; keep tdTomato, iCre, IEG, circadian, and morphine-state
   genes out of the cell-identity PCA.
4. Calibrate the Ai14 tdTomato gate with Cre-negative or no-induction controls and report
   sensitivity at 1, 2, and 3 transcripts.
5. Ask which cell types contain tdTom+ cells.
6. Compare GPCR, TF, plasticity, and morphine-state genes **within the same cell type**.
7. Aggregate counts by animal x cell type x reporter/condition for inference. Cells are not
   biological replicates.
8. Use spatial-neighborhood results as within-section descriptions and confirm them across
   animals.

## Approaches considered

### A. Curated marker modules only

This is the simplest baseline and is easy to explain. It recovers broad classes, but it leaves
many cells unassigned and cannot reliably discover a new subtype. It is retained as an
annotation aid and a visual check.

### B. External reference mapping plus identity-only Leiden clustering — selected

Allen/reference-transfer labels provide an external biological anchor. Leiden can reveal finer
structure, while reporter and activity-state genes are excluded from PCA so they cannot create
a false “cell type.” This is the best balance of interpretability and discovery for a targeted
production panel.

### C. Pure de novo spatial clustering

This is useful as a secondary discovery analysis. With a targeted panel and one specimen it is
sensitive to panel composition, expression state, ROI boundaries, and clustering resolution.
A candidate new type must reproduce in independent animals and have multiple coherent markers.

## Important findings from the review

- The research folder documented three scripts but did not contain them. The executable scripts
  are now present.
- Story 2 and Story 3 were placeholders. Story 2 now produces Ai14 overlap, threshold
  sensitivity, neighbor-contamination flags, and within-class descriptive effects when
  tdTomato exists. Story 3 now aggregates multiple ROIs within animal and exports animal-level
  composition and pseudobulk matrices.
- The previous k-nearest-neighbor code removed the closest true neighbor because the fitted-data
  query already excluded self. This is corrected.
- Reporter and state genes previously entered PCA. They are now retained for downstream biology
  but excluded from cell-identity clustering.
- Marker calls previously required expression inside a cluster but did not require specificity
  against cells outside it. The output now includes fraction inside, fraction outside, and a
  minimum detection difference of 0.15.
- Module scores and onboard graph clustering use the same Xenium matrix and are not independent
  validation. They are now labeled same-matrix concordance. Existing Allen transfer labels are
  reported separately as reference validation.
- Spatial-neighborhood z-scores were hard to interpret. The main figure now shows
  log2(observed/permuted expected), excludes unassigned or tiny groups, and explicitly states
  that neighbor edges are not animal replicates.
- Spatial gene maps now use raw transcripts per cell, show zero cells in gray, and cap color at
  the 99th percentile among positive cells.
- iCre is not required to remain expressed in every permanent Ai14-positive cell. It should not
  be used as a strict positive-control concordance rule for a transient iCreER/TRAP system.

## Validation from the rerun

The revised pipeline completed on both pilot ROIs.

- ORBm: 915 exported cells, 914 after QC, 15 Leiden clusters.
- BMAp: 1,145 exported cells, 1,077 after QC, 15 Leiden clusters.
- Resolution stability, ARI comparing resolution 1.0 with 0.5/1.5:
  - ORBm: 0.776 / 0.793
  - BMAp: 0.880 / 0.838
- Allen coarse-label concordance:
  - ORBm: ARI 0.500, NMI 0.738
  - BMAp: ARI 0.503, NMI 0.673
- Same-Leiden spatial-neighbor fraction versus global permutation:
  - ORBm: 0.294 versus 0.097
  - BMAp: 0.269 versus 0.089

These checks show reproducible broad structure, but they do not prove a treatment effect or a
new cell type. ORBm has 225/914 module-unassigned cells and BMAp has 273/1,077, so final labels
should rely on reference mapping and multiple markers rather than the simple module winner.

## Analyses to add when real replicated production-panel data arrive

1. **Reporter calibration**
   - Use Cre-negative or no-induction controls to select a tdTomato count threshold.
   - Show 1/2/3-count sensitivity and transcript-localization examples.
   - Treat one-count cells near many tdTom+ cells as flagged, not automatically discarded.

2. **TRAP overlap**
   - Estimate tdTom+ fraction and binomial uncertainty by cell type for each animal.
   - Plot every animal; do not pool cells across animals for inference.

3. **Within-type biology**
   - Compare GPCR, TF, plasticity, IEG, circadian, and morphine-state genes within one cell type.
   - Report mean transcripts, detection difference, log2 effect, and animal-level uncertainty.
   - Separate identity genes from state genes in interpretation.

4. **Pseudobulk treatment models**
   - Sum counts by animal x anatomy x cell type x reporter status/condition.
   - Analyze each anatomy and cell type with edgeR or DESeq2.
   - Include batch/cassette terms if they are not confounded with condition.
   - Prefer at least three independent animals per condition; two per group is weak.

5. **Composition**
   - Plot cell-type fractions by animal.
   - Use a compositional model only with enough animals; never use a chi-square test on pooled cells.

6. **Spatial confirmation**
   - Compare fixed-radius and kNN results.
   - Repeat across animals and report effect size, not only permutation p-values.
   - Inspect ROI boundaries and white-matter/vascular contamination.

7. **Candidate new subtype**
   - Require more than one marker, separation from known reference types, spatial coherence,
     stability across resolution choices, and replication in another animal.
   - Label a nonreplicated candidate as provisional.

## Recommended concise figures

Use four figures for PI communication:

1. `10_cell_identity_overview.png`: spatial cell classes, composition, and annotation confidence.
2. Real-data `01_tdtom_overlap_summary.png`: tdTom transcript map and tdTom+ fraction by cell type.
3. `11_gpcr_state_tf_overview.png`: GPCR, activity/plasticity, and TF detection by cell class.
4. Animal-level result: composition by animal plus a pseudobulk effect-size plot for selected genes.

UMAP, full marker heatmaps, cluster tables, and neighborhood matrices should stay in the
supplement or QC folder.

## Remaining limitations

- The pilot cannot validate tdTomato because the reporter is absent from its panel.
- The 244 custom-panel genes absent from the 247-gene pilot have no pilot Xenium expression.
- Current ORBm and BMAp slides are different anatomies, not biological replicates.
- External label transfer is reference-guided and still uses the same measured expression;
  validation across independent animals remains necessary.
- A targeted panel cannot establish genome-wide novelty. “New cell type” means a reproducible
  subtype within the measured marker space and should be confirmed with broader data.
