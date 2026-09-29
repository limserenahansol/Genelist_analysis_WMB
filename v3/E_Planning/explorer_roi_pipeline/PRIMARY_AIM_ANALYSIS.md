# Primary analysis: tdTom identity, enrichment, and Active/Passive effects

## Primary scientific question

Do Ai14 tdTomato-positive TRAP cells represent:

1. preferential labeling of one or more **existing cell types**,
2. a shared activity or plasticity **state across several existing types**, or
3. a reproducible **candidate new subtype** defined by cell-identity genes?

Reporter enrichment or an IEG signature alone is not evidence for a new cell type.

## Factorial design

Every analysis is stratified by anatomy. Within an anatomy and an existing cell type, the
biological design is:

| Condition | tdTom− | tdTom+ |
|---|---|---|
| Active | Active negative | Active positive |
| Passive | Passive negative | Passive positive |

Animal is the biological replicate. Multiple ROIs or sections from one animal are nested
samples and are aggregated within animal for the primary expression model.

## Question 1: existing type or candidate new type?

### Existing-type assignment

1. Assign every cell to an Allen/reference type using identity genes.
2. Confirm the assignment with multiple curated markers and spatial location.
3. Keep tdTomato, iCre, IEG, plasticity, circadian, and morphine-state genes out of the identity
   PCA and reference assignment.
4. Plot tdTom+ and tdTom− cells on the same reference-type map.

### Evidence for preferential labeling of an existing type

For every animal and existing cell type, calculate:

- percent tdTom+ within the type: P(tdTom+ | type),
- composition among tdTom+ cells: P(type | tdTom+),
- composition among tdTom− cells: P(type | tdTom−),
- log2 composition enrichment: log2[P(type | tdTom+) / P(type | tdTom−)],
- tdTom odds ratio for the type versus all other types.

A type is considered preferentially labeled only when enrichment is consistent across
independent animals. Pooled-cell Fisher or chi-square tests are not biological inference.

### Evidence required for a candidate new subtype

A tdTom-enriched cluster is a candidate new subtype only if all of these hold:

1. It is generated from identity genes, without reporter or state genes.
2. It has poor or ambiguous mapping to known reference types.
3. It has at least two coherent identity markers, not only Fos/Arc/Per1/Per2 or other state genes.
4. It is stable across clustering resolutions and reasonable QC choices.
5. It is spatially coherent.
6. The same identity pattern appears in independent animals.
7. The distinction persists after matching tdTom+ and tdTom− cells for parent cell type.

Until these checks pass, call it a **tdTom-enriched state or provisional subtype**, not a new
cell type.

## Question 2: which genes differ between tdTom+ and tdTom−?

Run differential expression separately within each anatomy and existing cell type. Prioritize
effect size, detection difference, and consistency across animals.

Report all measured genes, with focused summaries for:

- GPCRs,
- transcription factors,
- activity and plasticity genes,
- morphine-state and circadian genes,
- identity markers.

A difference in identity markers supports a subtype hypothesis. A difference restricted to
IEG/plasticity/morphine-state genes supports a state difference.

## Question 3: how does Active versus Passive change the result?

The animal-level factorial analysis has five planned contrasts:

1. tdTom+ versus tdTom− within Active animals.
2. tdTom+ versus tdTom− within Passive animals.
3. Active versus Passive within tdTom+ cells.
4. Active versus Passive within tdTom− cells.
5. Interaction:
   (Active tdTom+ − Active tdTom−) − (Passive tdTom+ − Passive tdTom−).

The interaction is the direct test of whether Active/Passive changes are preferentially
associated with the TRAP-labeled population.

Use animal-level pseudobulk within anatomy and cell type. The supplied limma-voom model blocks
on animal because tdTom+ and tdTom− pseudobulks are paired within each animal. Prefer at least
three animals per condition with enough cells in both reporter states; more animals are strongly
preferred for heterogeneous cell types.

## Main output files

- `outputs/story2_tdtom/cell_type_tdtom_enrichment_by_animal.csv`
- `outputs/story2_tdtom/all_rois_tdtom_enrichment_by_leiden_cluster.csv`
- `outputs/factorial_tdtom_active_passive/factorial_sample_metadata.csv`
- `outputs/factorial_tdtom_active_passive/factorial_pseudobulk_counts_genes_by_sample.csv`
- `outputs/factorial_tdtom_active_passive/contrast_plan.csv`
- `outputs/factorial_tdtom_active_passive/gene_categories.csv`
- `run_factorial_limma_voom.R` writes one result table per anatomy, cell type, and contrast.

## Recommended four primary figures

1. Existing reference-type spatial map with tdTom+ cells highlighted.
2. Per-animal tdTom enrichment by existing cell type, split by Active/Passive.
3. Within-cell-type GPCR/TF/plasticity effect-size plot for tdTom+ versus tdTom−.
4. Active/Passive factorial contrast plot, including the interaction effect.

UMAPs, resolution checks, full heatmaps, and cluster tables belong in QC or supplementary
figures.
