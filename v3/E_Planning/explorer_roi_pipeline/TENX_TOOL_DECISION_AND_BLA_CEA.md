# 10x tool decision and BLA/CEA extension

## Tool decision

The pipeline should not install every tool in the 10x overview. Many packages repeat the same QC,
clustering, differential-expression, or plotting tasks. The simplest adequate stack is:

- **Primary:** Xenium Explorer for ROI/image inspection; direct Xenium H5/parquet reading plus
  Scanpy for reproducible cell-level processing; animal-level pseudobulk for inference.
- **Added now:** Allen-informed BLA/CEA marker modules, neighborhood-enrichment permutation tests,
  and Moran's I for spatial marker coherence.
- **Add with the four-mouse production data:** Harmony for joint visualization only, after anatomy is
  separated and with animal as the batch field. Differential expression remains animal-level and is
  run on uncorrected counts.
- **Add when image alignment is needed:** SpatialData, spatialdata-io, and spatialdata-plot to keep
  images, boundaries, transcripts, and tables in one coordinate system. Napari is an optional viewer.
- **Independent annotation validation now implemented:** Seurat label transfer with the local Allen
  WMB `sAMY` reference, plus a regularized classifier as an independent check. RCTD remains optional
  for boundary cells or documented mixed-cell signals. A cortex reference is not appropriate for
  BLA or CEA.
- **Use only after a documented segmentation failure:** Xenium Ranger resegment/import-segmentation,
  Baysor, or Cellpose. Alternative segmentation must be compared against the onboard result for
  transcript assignment, boundary artifacts, cell size, and preservation of known marker patterns.
- **Optional sensitivity analyses:** Banksy for spatially informed clustering. stLearn, SCIMAP,
  Giotto, Voyager, and MERINGUE are not required for the primary questions because their relevant
  functions overlap the selected stack.

This follows the 10x Python tutorial's sequence: load and QC, select ROI, preprocess, cluster,
annotate, export to Explorer, then optionally test neighborhood enrichment and Moran's I. The 10x R
tutorial presents Seurat sketch/Harmony for large multisample integration and Banksy as an optional
spatial clustering analysis.

Sources:

- https://www.10xgenomics.com/analysis-guides/xenium-downstream-analysis-in-python-tutorial
- https://www.10xgenomics.com/analysis-guides/xenium-downstream-analysis-in-r-tutorial
- https://www.10xgenomics.com/analysis-guides/choosing-r-or-python-xenium-analysis-blog
- https://www.10xgenomics.com/analysis-guides/continuing-your-journey-after-xenium-analyzer

## BLA annotation

The BLA module uses an Allen `014 LA-BLA-BMA-PA Glut` reference for the broad principal-neuron
identity and canonical Pvalb, Sst, and Vip/Lamp5 inhibitory classes. The Allen STR shard contained
only 113 cells from this broad excitatory subclass, with only two supertypes having at least 20 cells.
The current evidence therefore supports a broad `BLA_principal` label, not confident BLA excitatory
supertype names.

Across four pilot BLA ROIs, the mean NMI between marker labels and unbiased Leiden clusters changed
from 0.469 with the BMAp modules to 0.483 with BLA modules. Mean assigned fraction remained 0.78.
`BLA_principal` represented 37.9% of cells on average. These are descriptive sections from one mouse.

## CEA annotation

The CEA modules use Allen subclasses `077`, `079`, `080`, `082`, and `083`. The local Allen reference
contained 195, 4,699, 3,639, 6,981, and 219 cells, respectively. The current 247-gene pilot does not
measure the defining genes `Gal`, `Avp`, `Six3`, `Cyp26b1`, `Sp9`, `Ebf1`, or `Rai14`. Labels are
therefore suffixed `_like` and are based on independently ranked panel genes such as `Rspo1/Calb2`,
`Arhgap6/Penk`, `Foxp2/Nts`, `Plcxd2/Sst`, and `Hs3st2/Pdyn/Crh`.

Across the two pilot CEA ROIs, mean NMI increased from 0.289 to 0.430 and mean assigned fraction from
0.511 to 0.720. `CEA_Six3_Cyp26b1_like` represented 26.2% and
`CEA_Rai14_Pdyn_Crh_like` 8.6% of cells on average. These labels remain provisional until a richer
production panel or region-matched reference transfer confirms them.

The evidence table is reproducible with `derive_bla_cea_allen_markers.py`. The verified run used
15,846 Allen STR-shard cells and all 247 genes measured in the pilot; the regenerated 163-row top
marker table matched the table used to define these modules.

## Spatial validation

`run_spatial_context.py` computes cell-type neighborhood enrichment against label permutations and
Moran's I for region-specific marker genes. It is descriptive within each section. Neighbor edges and
cells are not biological replicates; cross-condition inference still uses animals.

## Allen reference-transfer validation

The current pilot was transferred to the Allen WMB `sAMY` reference with all 247 shared measured
genes. BLA had a median Seurat score of 0.621, with 70.1% of cells at score >=0.5; CEA had a median
score of 0.623, with 72.7% at score >=0.5. Seurat and the independent classifier had coarse-label
agreement of 69.5% for BLA and 73.9% for CEA. Existing marker modules and Allen labels had NMI 0.451
for BLA and 0.441 for CEA. Many cells received `other` because the 247-gene targeted panel does not
resolve every Allen subclass and the BLA Allen reference contains relatively few broad principal
cells. The transfer supports broad identities but does not establish fine BLA/CEA subtypes.

## Candidate novel subtype

`make_tdtom_subtype_toy.py` creates a four-mouse synthetic example and runs the same candidate-subtype
module used for real data. Its summary figure is explicitly labeled simulated. Real BLA/CEA reporter
data will be analyzed within the region-specific parent types, and the strongest automatic output
remains `candidate_novel_subtype_requires_external_validation`.
