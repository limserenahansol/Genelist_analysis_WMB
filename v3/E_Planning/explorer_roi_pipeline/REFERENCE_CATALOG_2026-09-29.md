# ORBm–BMAp–BLA–CEA Xenium Reference Catalog

**Catalog date:** 2026-09-29  
**Scope:** references relevant to panel design, Allen atlas validation, Jesse and Dan evidence, TRAP2/Ai14 interpretation, Xenium processing, reference transfer, spatial analysis, and image/segmentation review.

## Evidence hierarchy

1. **Primary project evidence:** collaborator data, GEO records, raw Xenium outputs, and animal-level metadata.
2. **Independent public evidence:** peer-reviewed papers, official atlas releases, and official software or vendor documentation.
3. **Derived project evidence:** local workbooks, figures, decks, and pipeline outputs. These summarize or analyze primary sources; they are not independent publications.

## Project-specific sources

### Jesse opioid-dependence data

- **Source:** Jesse Niehaus collaborator gene lists, received 2026-09-09.
- **Design recorded locally:** five-day escalating morphine; DESeq2 subclass pseudobulk; adjusted-P threshold `padj <= 0.1`.
- **Local provenance:** `C:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\inputs\Jesse_ORB\README.md`
- **Local input directory:** `C:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\inputs\Jesse_ORB`
- **Project use:** morphine-state, activity/plasticity, transcription-factor, and GPCR candidate prioritization in ORBm.
- **Publication status:** **internal collaborator dataset**. No matching public accession or peer-reviewed publication was identified in the search completed for this catalog. Cite Jesse directly or the eventual publication when available.
- **Related background only:** the Harvard dissertation *Mechanisms of Neuronal Activity-Dependent Transcription* discusses activity-regulated gene classes and includes several overlapping IEGs, but it is not the source of Jesse's dataset: https://dash.harvard.edu/entities/publication/a1be5d7f-fb61-41a5-9b34-19f9d259da84
- **Jesse-authored opioid cell-type review:** Ochandarena N, Niehaus JK, Tassou A, Scherrer G. *Cell-type specific molecular architecture for mu opioid receptor function in pain and addiction circuits.* Neuropharmacology. 2023;238:109597. DOI: 10.1016/j.neuropharm.2023.109597. https://pmc.ncbi.nlm.nih.gov/articles/PMC10494323/ This supports opioid receptor/cell-type rationale, but it does not report the 2026 five-day morphine DEG lists.
- **Related conference abstract:** Niehaus JK et al. *Refined gene annotations increase the accuracy of quantifying mu opioid receptor RNAs and other neuronal genes in single-cell RNA-sequencing data.* WCBR 2024 program, poster M40. https://winterbrain.org/wp-content/uploads/2024/12/2024-Winter-Brain-Program-Book.pdf This is relevant to Oprm1 quantification and isoforms, not the source of the 2026 DEG lists.

### Dan amygdala spatial data

- **Dataset:** Berg D, Scherrer G. *Spatial molecular profiling of amygdalar neurons enables precision pharmacology against pain unpleasantness.* GEO **GSE283418**, public 2025-11-26. https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE283418
- **Platform:** Resolve Biosciences Molecular Cartography Mouse Amygdala custom platform, **GPL35157**, 98 genes. https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL35157
- **Design recorded by GEO:** 10 mouse amygdala sections; 97 biological genes measured by single-molecule FISH; DAPI/Cellpose followed by Baysor segmentation; processed transcript-per-cell files and images are available.
- **Local metadata:** `C:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\inputs\GSE283418\metadata_dump.txt`
- **Local input directory:** `C:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\inputs\GSE283418`
- **Project use:** independent amygdala marker/GPCR candidate evidence, especially BMAp/BLA/CEA.
- **Publication status:** **public GEO dataset; no associated peer-reviewed article or PubMed ID was listed in the GEO record at catalog time.**
- **Conference abstract:** Berg D et al. *Profiling of nociceptive neurons enables synergistic pharmacology against pain unpleasantness.* Conference poster/abstract; useful context, not a peer-reviewed full paper. https://cdn.fourwaves.com/static/media/filecontent/72b3a299-8cf3-4e2d-a342-88583dcfb8c7/71bc5117-19fd-4de0-9019-e88d73b89405.pdf
- **Resolve method reference named by GPL35157:** Guilliams M et al. *Spatial proteogenomics reveals distinct and evolutionarily conserved hepatic macrophage niches.* Cell. 2022;185:379-396.e38. PMID 35021063. https://pmc.ncbi.nlm.nih.gov/articles/PMC8809252/ This supports the Molecular Cartography method, **not Dan's amygdala biology**.

### Internal project documents

- *Dissection and treatment of the neural circuits underlying volitional opioid seeking.* Internal research plan. Local: `C:\Users\hsollim\Downloads\SOW_MJ Schnitzer and G Scherrer_Final_Science.pdf`
- *UA UNC Scherrer SOW2 v3 Research.* Internal Year-3 plan, revised 2026-09-28. Local: `C:\Users\hsollim\Downloads\UA UNC Scherrer SOW2 v3_Research.pdf`
- *TRAP data ORBm BMAp COA for next step.* Internal analysis deck. Local: `C:\Users\hsollim\Downloads\TRAP_data_ORBm_BMAp_COA_for next step33.pdf`
- *TRAP colleague explanation / figure code.* Internal analysis documentation. Local: `C:\Users\hsollim\Downloads\TRAP_colleague_explain_figure_code.pdf`
- *Dan manuscript GPCRs* and *Amygdala Dan marker genes.* Local one-page R plots, not manuscripts or papers: `C:\Users\hsollim\Downloads\AMY_DanmanuscriptGPCRs.pdf`; `C:\Users\hsollim\Downloads\Amydala_DansMarkergenes.pdf`

## Allen Mouse Whole Brain atlas

- Yao Z et al. *A high-resolution transcriptomic and spatial atlas of cell types in the whole mouse brain.* Nature. 2023;624:317-332. DOI: 10.1038/s41586-023-06812-z. https://www.nature.com/articles/s41586-023-06812-z
- Zhang M et al. *Molecularly defined and spatially resolved cell atlas of the whole mouse brain.* Nature. 2023;624:343-354. DOI: 10.1038/s41586-023-06808-9. https://www.nature.com/articles/s41586-023-06808-9
- Allen Institute. *Whole Mouse Brain Atlas data description and access.* https://alleninstitute.github.io/abc_atlas_access/descriptions/WMB_dataset.html
- **Local raw cache:** `C:\Users\hsollim\Downloads\abc_atlas_cache`
- **Local extracted reference matrices:** `C:\Users\hsollim\Desktop\cursor\Xenium_downstream\allen_label_transfer`
- **Project use:** detection screening, marker specificity, genome-wide GPCR/TF screening, and independent BLA/CEA annotation validation. The current region subsets use PL-ILA-ORB and sAMY labels.

## TRAP2 and Ai14 reporter interpretation

- Guenthner CJ et al. *Permanent genetic access to transiently active neurons via TRAP.* Neuron. 2013;78:773-784. DOI: 10.1016/j.neuron.2013.03.025. https://pmc.ncbi.nlm.nih.gov/articles/PMC3782391/
- DeNardo LA et al. *Temporal evolution of cortical ensembles promoting remote memory retrieval.* Nature Neuroscience. 2019;22:460-469. DOI: 10.1038/s41593-018-0318-7. https://www.nature.com/articles/s41593-018-0318-7
- Madisen L et al. *A robust and high-throughput Cre reporting and characterization system for the whole mouse brain.* Nature Neuroscience. 2010;13:133-140. DOI: 10.1038/nn.2467. https://pmc.ncbi.nlm.nih.gov/articles/PMC2840225/
- Jackson Laboratory. *Comparison of Cre reporter strains*; Ai14 stock 007914, Rosa-CAG-LSL-tdTomato-WPRE. https://www.jax.org/research-and-faculty/resources/cre-repository/comparison-of-cre-reporters
- MGI allele record: Gt(ROSA)26Sortm14(CAG-tdTomato)Hze. https://www.informatics.jax.org/allele/MGI%3A3809524
- **Project interpretation:** tdTomato labels cells with historical CreER recombination during the TRAP window. It is not equivalent to current `Fos` expression. A Xenium reporter probe must target the actual Ai14 transgene sequence rather than assume the endogenous mouse `tdTomato` symbol exists.

## Amygdala and pain-circuit biological context

- Corder G et al. *An amygdalar neural ensemble that encodes the unpleasantness of pain.* Science. 2019;363:276-281. DOI: 10.1126/science.aap8586. https://pmc.ncbi.nlm.nih.gov/articles/PMC6450685/
- *A nociceptive amygdala-striatal pathway modulating affective-motivational pain.* PubMed PMID 40700496. https://pubmed.ncbi.nlm.nih.gov/40700496/
- **Use:** biological rationale for BLA/CeA pain-affect circuits. These papers do not replace region-matched expression validation in the panel data.

## Xenium official documentation

- 10x Genomics. *Xenium downstream analysis in Python tutorial.* https://www.10xgenomics.com/analysis-guides/xenium-downstream-analysis-in-python-tutorial
- 10x Genomics. *Xenium downstream analysis in R tutorial.* https://www.10xgenomics.com/analysis-guides/xenium-downstream-analysis-in-r-tutorial
- 10x Genomics. *Choosing R or Python for Xenium analysis.* https://www.10xgenomics.com/analysis-guides/choosing-r-or-python-xenium-analysis-blog
- 10x Genomics. *Workshop: Xenium In Situ analysis.* https://www.10xgenomics.com/analysis-guides/workshop-xenium-in-situ-analysis
- 10x Genomics. *Continuing your journey after Xenium Analyzer.* https://www.10xgenomics.com/analysis-guides/continuing-your-journey-after-xenium-analyzer
- **Local guides:** `C:\Users\hsollim\Downloads\10x_CG000582_XeniumInSitu_GeneExpression_UserGuide_RevH.pdf (1).pdf`; `C:\Users\hsollim\Downloads\CG000579_Demonstrated_Protocol_XeniumInSituProtocolsFF_TissuePreparationHandbook_RevF.pdf`; `C:\Users\hsollim\Downloads\CG000584_Xenium_Analyzer_UserGuide_RevK.pdf`

## Analysis methods and software

### Data container, preprocessing, and visualization

- Marconato L et al. *SpatialData: an open and universal data framework for spatial omics.* Nature Methods. 2024. DOI: 10.1038/s41592-024-02212-x. https://www.nature.com/articles/s41592-024-02212-x
- Wolf FA et al. *SCANPY: large-scale single-cell gene expression data analysis.* Genome Biology. 2018;19:15. DOI: 10.1186/s13059-017-1382-0. https://genomebiology.biomedcentral.com/articles/10.1186/s13059-017-1382-0
- Hao Y et al. *Dictionary learning for integrative, multimodal and scalable single-cell analysis.* Nature Biotechnology. 2024. Seurat v5. https://www.nature.com/articles/s41587-023-01767-y
- Palla G et al. *Squidpy: a scalable framework for spatial omics analysis.* Nature Methods. 2022;19:171-178. DOI: 10.1038/s41592-021-01358-2. https://www.nature.com/articles/s41592-021-01358-2
- Nirmal AJ, Sorger PK. *SCIMAP: A Python Toolkit for Integrated Spatial Analysis of Multiplexed Imaging Data.* JOSS. 2024;9:6604. DOI: 10.21105/joss.06604. https://pmc.ncbi.nlm.nih.gov/articles/PMC11173324/
- napari contributors. *napari: a multi-dimensional image viewer for Python.* Zenodo. DOI: 10.5281/zenodo.3555620. https://github.com/napari/napari
- Schindelin J et al. *Fiji: an open-source platform for biological-image analysis.* Nature Methods. 2012;9:676-682. DOI: 10.1038/nmeth.2019. https://www.nature.com/articles/nmeth.2019
- Bankhead P et al. *QuPath: Open source software for digital pathology image analysis.* Scientific Reports. 2017;7:16878. DOI: 10.1038/s41598-017-17204-5. https://www.nature.com/articles/s41598-017-17204-5

### Integration and annotation

- Korsunsky I et al. *Fast, sensitive and accurate integration of single-cell data with Harmony.* Nature Methods. 2019;16:1289-1296. DOI: 10.1038/s41592-019-0619-0. https://www.nature.com/articles/s41592-019-0619-0
- Cable DM et al. *Robust decomposition of cell type mixtures in spatial transcriptomics.* Nature Biotechnology. 2022;40:517-526. RCTD. DOI: 10.1038/s41587-021-00830-w. https://www.nature.com/articles/s41587-021-00830-w
- Seurat. *Analysis of spatial datasets* and reference transfer vignette. https://satijalab.org/seurat/articles/spatial_vignette
- Seurat. *Integrative analysis in Seurat v5.* https://satijalab.org/seurat/articles/seurat5_integration
- **Project rule:** Harmony may support a joint visualization of four mice, but differential expression must use uncorrected counts and mouse-level replication. Reference transfer is independent annotation evidence, not ground truth.

### Spatial clustering and spatial statistics

- Singhal V et al. *BANKSY unifies cell typing and tissue domain segmentation for scalable spatial omics data analysis.* Nature Genetics. 2024;56:431-441. DOI: 10.1038/s41588-024-01664-3. https://www.nature.com/articles/s41588-024-01664-3
- Miller BF et al. *Characterizing spatial gene expression heterogeneity in spatially resolved single-cell transcriptomic data with nonuniform cellular densities.* Genome Research. 2021;31:1843-1855. MERINGUE. DOI: 10.1101/gr.271288.120. https://pmc.ncbi.nlm.nih.gov/articles/PMC8494224/
- Dries R et al. *Giotto: a toolbox for integrative analysis and visualization of spatial expression data.* Genome Biology. 2021;22:78. DOI: 10.1186/s13059-021-02286-2. https://genomebiology.biomedcentral.com/articles/10.1186/s13059-021-02286-2
- Pham D et al. *Robust mapping of spatiotemporal trajectories and cell-cell interactions in healthy and diseased tissues.* Nature Communications. 2023;14:7739. stLearn. DOI: 10.1038/s41467-023-43120-6. https://www.nature.com/articles/s41467-023-43120-6
- **Project rule:** BANKSY or another spatial clustering method is a sensitivity analysis for candidate tdTomato-associated subtypes. A candidate subtype requires reproducible marker effects across animals and stability to reasonable analysis choices.

### Segmentation

- Petukhov V et al. *Cell segmentation in imaging-based spatial transcriptomics.* Nature Biotechnology. 2022;40:345-354. Baysor. DOI: 10.1038/s41587-021-01044-w. https://www.nature.com/articles/s41587-021-01044-w
- Stringer C et al. *Cellpose: a generalist algorithm for cellular segmentation.* Nature Methods. 2021;18:100-106. DOI: 10.1038/s41592-020-01018-x. https://www.nature.com/articles/s41592-020-01018-x
- **Project rule:** alternative segmentation is justified only after measurable failure of Xenium segmentation. Validate boundary quality visually and quantify transcript assignment, cell-size distributions, and marker mixing before and after.

## Derived project artifacts

The following are traceable analysis outputs, not independent references:

- `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\xenium_ORBm_BMAp_2026-09\Jesse_ORB_priority_ranking.xlsx`
- `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\xenium_ORBm_BMAp_2026-09\Jesse_ORB_vs_Xenium_panel.xlsx`
- `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\xenium_ORBm_BMAp_2026-09\GSE283418_vs_BMAp_panel.xlsx`
- `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\xenium_ORBm_BMAp_2026-09\allen_detectability_all_candidates.xlsx`
- `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\xenium_ORBm_BMAp_2026-09\allen_genomewide_marker_search.xlsx`
- `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\panel298_pilot_validation\explorer_roi_pipeline\outputs_bla_cea_refined\reference_validation`
- Pipeline documentation: `C:\Users\hsollim\Research_Projects\03_GPCR_probe_panel\panel298_pilot_validation\explorer_roi_pipeline\README.md`

## Citation and interpretation rules

- Cite **GSE283418/GPL35157** for the Dan panel and spatial dataset. Do not present it as a peer-reviewed publication until one is linked by GEO or confirmed by the authors.
- Cite **Jesse Niehaus, personal communication/internal dataset (2026-09-09)** for the Jesse lists unless a public accession or paper is supplied.
- Cite **Yao 2023 + Zhang 2023 + Allen data access** for Allen WMB-derived detectability, specificity, and reference-transfer analyses.
- Cite **TRAP/TRAP2/Ai14 papers and JAX/MGI** when explaining tdTomato lineage labeling.
- Cite software papers for the method actually used. Keep tools that were merely considered in a separate “considered” list rather than implying they were run.
- The experimental unit for Active-versus-Passive inference is the **mouse**. Sections and cells are nested observations, not independent replicates.
