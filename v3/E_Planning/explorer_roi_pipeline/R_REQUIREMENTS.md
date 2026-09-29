# R dependency for factorial pseudobulk differential expression

The Python export is self-contained. The final animal-blocked differential-expression model uses
Bioconductor `edgeR` and `limma`.

Install once in R:

```r
if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager")
}
BiocManager::install(c("edgeR", "limma"))
```

Then run:

```text
Rscript run_factorial_limma_voom.R outputs/factorial_tdtom_active_passive
```

The packages were not installed in the environment used for the 2026-09-28 code review, so the
R file was syntax-checked but its model fit could not be executed locally. The Python factorial
export and all contrast-readiness checks were smoke-tested with six synthetic animals.
