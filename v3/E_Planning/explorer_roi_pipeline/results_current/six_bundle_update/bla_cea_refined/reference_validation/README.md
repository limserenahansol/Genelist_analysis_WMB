# BLA/CEA Allen reference validation

This folder contains a real-data annotation check for the current 247-gene, one-mouse pilot. The
reference is the local Allen WMB `sAMY` dataset. Seurat anchor transfer is the primary external
method; a regularized multinomial classifier trained on the same reference is an independent
algorithmic check. Neither method replaces the primary marker-module labels.

## Verified results

- BLA: 4,246 cells in four ROIs; median Seurat score 0.621; 70.1% had score >=0.5.
- CEA: 1,905 cells in two ROIs; median Seurat score 0.623; 72.7% had score >=0.5.
- Seurat versus independent-classifier coarse-label agreement: 69.5% BLA and 73.9% CEA.
- Primary module versus Seurat coarse-label NMI: 0.451 BLA and 0.441 CEA.
- Among cells for which both methods produced a comparable non-`other`, non-`unassigned` label,
  exact agreement was 87.5% BLA and 84.6% CEA. These comparable cells were 42.5% and 55.7% of all
  cells, respectively, so the conditional agreement must not be reported without its coverage.

The large `other` group is a real limitation. The targeted panel cannot resolve every Allen
subclass, and the local Allen reference contains only a small BLA principal-neuron set. The results
support broad annotation consistency, especially non-neuronal classes and major CEA programs, but
do not validate fine subtype names.

## Files

- `reference_validation_summary.json`: compact quantitative results.
- `BLA_reference_validation.csv`, `CEA_reference_validation.csv`: per-cell predictions and scores.
- `BLA_module_vs_allen_counts.csv`, `CEA_module_vs_allen_counts.csv`: confusion tables.
- `BLA_reference_validation.png`, `CEA_reference_validation.png`: confidence, composition, and
  module-versus-reference summaries.

The current pilot has no tdTomato measurement and only one mouse. It therefore cannot determine
whether tdTom+ cells form a reproducible candidate subtype. That analysis requires the planned
four-mouse data and cross-mouse validation.
