# 10x Xenium downstream tools and the four-mouse analysis plan

## Scientific objective

The primary questions are:

1. Are Ai14 `tdTomato+` cells a new transcriptional cell type or a state/subset of an existing type?
2. In which established ORBm or BMAp cell types are `tdTomato+` cells enriched?
3. Within the same cell type, which measured GPCR, TF, activity, and plasticity genes differ between
   `tdTomato+` and `tdTomato-` cells?
4. How do these effects differ between Active and Passive animals?

The experimental unit for Active versus Passive is the **mouse**. Sections, ROIs, and cells are
nested observations and do not increase the biological sample size.

## What 10x recommends after Xenium Analyzer

The five 10x guides describe a common sequence rather than one mandatory software package:

1. **Inspect XOA quality first.** Review `analysis_summary.html` and `metrics_summary.csv`, including
   cell yield, transcript assignment, Q20 decoding, negative controls, segmentation, and expression
   depth.
2. **Use Xenium Explorer for spatial inspection.** Check morphology, transcript placement, cell
   boundaries, marker genes, and anatomical ROIs. Export ROI cell IDs and coordinates. Import final
   cell groups back into Explorer.
3. **Load open-format outputs into R or Python.** Use the cell-feature matrix, cells, transcripts,
   boundaries, and morphology images.
4. **Perform single-cell analysis.** QC, normalization, PCA, neighbors, UMAP, clustering, marker
   detection, and biological annotation.
5. **Integrate multiple samples if needed.** Both 10x tutorials demonstrate sketching and Harmony.
   Integration is for a common embedding and annotation; it is not the statistical test for a
   biological condition.
6. **Add spatial analyses.** Neighborhood enrichment, centrality, Moran's I/spatially variable genes,
   and spatially informed clustering such as Banksy are optional analyses tied to a specific question.
7. **Revisit segmentation only if QC shows a problem.** Xenium Ranger can resegment or import
   third-party segmentation; Baysor and Cellpose are alternatives. Do not resegment merely because
   another method exists.

### Tools named by 10x

- **10x tools:** Xenium Onboard Analysis, Xenium Explorer, Xenium Ranger `resegment`, and Xenium
  Ranger `import-segmentation`.
- **Python:** SpatialData, spatialdata-io, spatialdata-plot, Scanpy, Squidpy, Napari/napari-spatialdata,
  stLearn, and SCIMAP. Python is strongest for scalable spatial/image analysis and custom workflows.
- **R:** Seurat v5, BPCells, sketching, Harmony, Banksy, Giotto, Voyager, RCTD, and MERINGUE. R is
  especially convenient for differential-expression models and familiar single-cell plotting.
- **Segmentation/image utilities:** Baysor, Cellpose, Fiji, QuPath, and Napari.

10x explicitly notes that community tools are not supported by 10x. The practical choice should be
the smallest set that answers the biological question reproducibly.

Source guides:

- <https://www.10xgenomics.com/analysis-guides/xenium-downstream-analysis-in-python-tutorial>
- <https://www.10xgenomics.com/analysis-guides/xenium-downstream-analysis-in-r-tutorial>
- <https://www.10xgenomics.com/analysis-guides/choosing-r-or-python-xenium-analysis-blog>
- <https://www.10xgenomics.com/analysis-guides/workshop-xenium-in-situ-analysis>
- <https://www.10xgenomics.com/analysis-guides/continuing-your-journey-after-xenium-analyzer>

## Recommended approach for this project

Three reasonable approaches were considered:

1. **Independent section analysis plus fixed biological labels.** This is the simplest baseline and
   preserves real differences. It is easiest to audit but may split the same type differently between
   sections.
2. **Joint embedding with Harmony.** This improves cross-section visualization and common clustering
   when technical separation is visible. It can erase biology if batch and condition are correlated.
3. **Spatially informed clustering with Banksy or a similar method.** This may resolve anatomical
   niches, but a spatial niche is not automatically a new cell type and the added complexity is not
   required for the primary question.

Use approach 1 as the primary analysis and approach 2 as a sensitivity analysis. Use approach 3 only
if marker-consistent populations are spatially split in a way that the ordinary identity analysis
cannot explain.

The current pipeline therefore uses **Python/Scanpy for QC, identity and spatial summaries**, then
**animal-level pseudobulk with edgeR/limma-voom in R** for the planned contrasts. This combination
matches the strengths described by 10x while keeping the analysis inspectable.

An optional Seurat single-sample check is implemented in `run_seurat_10x_path.R`. On the original
ORBm-right and BMAp-left pilot ROIs, Seurat Louvain versus Python Leiden gave ARI 0.70 and 0.77,
respectively. This agreement is a method-sensitivity check, not an independent biological validation.

## Should Harmony be used?

Harmony is appropriate for a joint ORBm embedding across mice/sections and a separate joint BMAp
embedding when raw PCA/UMAP is dominated by run or section. It should be run only on identity genes;
`tdTomato`, `iCre`, immediate-early genes, condition labels, and state/plasticity genes must not drive
the identity correction.

Do not use Harmony-adjusted values for differential expression. DE and abundance models use original
counts aggregated to mouse-level samples. Do not correct away `condition`. If slide/run is perfectly
confounded with Active/Passive, Harmony cannot identify which difference is technical and which is
biological; the experimental layout must balance conditions across runs.

Harmony is not needed for the present pilot conclusion because each anatomy comes from only one
animal. The environment also does not currently contain `harmonypy`; no unvalidated Harmony output
was generated.

## Planned design: four mice and three sections

Assuming 2 Active and 2 Passive mice and three ORBm plus three BMAp sections per mouse, the flat
manifest contains 24 anatomical ROI entries:

`4 mice × 2 anatomies × 3 sections = 24 ROI entries`.

Analysis hierarchy:

```text
condition
└── mouse (biological replicate; n=2 per condition)
    ├── ORBm
    │   └── 3 sections
    └── BMAp
        └── 3 sections
            └── cells
```

The three sections improve coverage and allow section-level QC. They remain nested within mouse.
For every cell class and reporter state, counts are summed across sections before the primary
condition model, producing one pseudobulk value per mouse.

### Analyses that are valid with this design

- Per-section XOA QC, ROI yield, segmentation review, and expression-depth checks.
- Cell-type annotation with Allen/reference labels, marker modules, and optional Harmony sensitivity.
- Within each mouse: cell-type enrichment of `tdTomato+` versus `tdTomato-`, reporter threshold
  sensitivity, and spatial distribution.
- Mouse-level cell-type composition and `tdTomato+` fractions.
- Mouse-level pseudobulk effect sizes for GPCR, TF, activity, and plasticity genes within a cell type.
- Five preplanned contrasts: reporter effect in each condition, Active/Passive within each reporter
  state, and the reporter-by-condition interaction.
- Section-to-section reproducibility and spatial neighborhood summaries, aggregated within mouse.

### Statistical limitation of 2 Active versus 2 Passive

Four mice total are sufficient to build and debug the workflow and estimate large effects, but
**2 versus 2 is weak for condition inference**. The three sections do not change that. With only six
possible 2-versus-2 label allocations, an exact two-sided permutation test cannot produce a small
conventional p-value. Report per-mouse values, effect sizes, uncertainty, and consistency across
sections; do not advertise absence of significance as evidence of no effect.

At least 3 mice per condition is the current pipeline's preferred floor. More animals are advisable
if the interaction between Active/Passive and reporter status is a primary claim.

## Current six-bundle findings

- All six XOA bundles were readable: 421,520 cells detected in total.
- Decoded Q20 ranged from 86.1% to 96.5%; transcript assignment ranged from 83.8% to 89.4%.
- Five available ORBm/BMAp ROI selections produced 4,933 QC-passing cells and 11 figures per ROI.
- ORBm marker-module composition was relatively similar across the available comparisons
  (total-variation distance 0.091–0.106).
- BMAp left versus right differed more (total-variation distance 0.215), showing why repeated ROIs
  should be summarized within mouse rather than treated as independent mice.
- 0063817 Region 3 has no top-level Explorer ROI export. Region 2 exports are BLA/CEA, not BMAp.
- 0063814 Region 2 ORBm has a polygon but no cell-ID export. The reproducible centroid fallback found
  975 cells versus 951 in Explorer's combined summary, so it is marked approximate.

These are descriptive pilot observations. ORBm and BMAp are on different animals, `tdTomato` is not
present, and there is no Active/Passive replication.
