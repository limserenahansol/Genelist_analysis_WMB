# Jesse Niehaus — PL-ILA-ORB opioid-dependence lists

Source: Jesse Niehaus (2026-09-09). Five-day escalating morphine. DESeq2 subclass pseudobulk, padj ≤ 0.1.

- `OpioidDependenceDEG_genesets_forHansol090926/` — IEG, TF, synaptic plasticity, and GPCR DEGs (`gene`, `gene_set`, `n_DE_clusters`, `direction`, `DE_clusters`).
- `PL_ILA_ORB_*_EnrichedGPCRs.csv` — GPCRs enriched in PL-ILA-ORB glut or GABA subclasses vs the rest of the Allen 4M-cell atlas (Fisher, BH FDR ≤ 0.05, ≥5% cells, enrichment ≥ 1.5).
- `subclass_gpcr_enriched_lists.csv` — per-subclass excitatory vs inhibitory coupling lists.

Compare to the current Xenium order with:

```powershell
python v3/E_Planning/compare_jesse_orb_panel.py
python v3/E_Planning/compare_jesse_allen_abundance.py
python v3/E_Planning/check_jesse_genes_on_panel.py
```
