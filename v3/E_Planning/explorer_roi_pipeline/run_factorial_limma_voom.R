# Animal-level factorial differential expression for Xenium pseudobulk.
# Run after run_factorial_tdtom_active_passive.py.
missing_packages <- c("edgeR", "limma")[
  !vapply(c("edgeR", "limma"), requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing_packages)) {
  stop(
    "Missing Bioconductor packages: ", paste(missing_packages, collapse = ", "),
    ". Install with: if (!requireNamespace('BiocManager')) install.packages('BiocManager'); ",
    "BiocManager::install(c('edgeR','limma'))"
  )
}
suppressPackageStartupMessages({
  library(edgeR)
  library(limma)
})

args <- commandArgs(trailingOnly = TRUE)
input_dir <- if (length(args) >= 1) args[[1]] else file.path("outputs", "factorial_tdtom_active_passive")
counts_path <- file.path(input_dir, "factorial_pseudobulk_counts_genes_by_sample.csv")
meta_path <- file.path(input_dir, "factorial_sample_metadata.csv")
out_root <- file.path(input_dir, "limma_voom_results")
dir.create(out_root, recursive = TRUE, showWarnings = FALSE)

counts <- read.csv(counts_path, row.names = 1, check.names = FALSE)
meta <- read.csv(meta_path, stringsAsFactors = FALSE, check.names = FALSE)
stopifnot(all(meta$sample_id %in% colnames(counts)))
categories_path <- file.path(input_dir, "gene_categories.csv")
categories <- if (file.exists(categories_path)) read.csv(categories_path, stringsAsFactors = FALSE) else NULL

safe <- function(x) make.names(x)
write_skip <- function(path, reason) writeLines(reason, file.path(path, "SKIPPED.txt"))

for (anatomy in unique(meta$anatomy)) {
  for (cell_class in unique(meta$cell_class[meta$anatomy == anatomy])) {
    sub <- meta[
      meta$anatomy == anatomy &
      meta$cell_class == cell_class &
      meta$eligible_min_cells, ,
      drop = FALSE
    ]
    result_dir <- file.path(out_root, safe(anatomy), safe(cell_class))
    dir.create(result_dir, recursive = TRUE, showWarnings = FALSE)

            conditions <- sort(unique(sub$condition))
            if (all(c("active", "passive") %in% tolower(conditions))) {
              conditions <- c(
                conditions[tolower(conditions) == "passive"][[1]],
                conditions[tolower(conditions) == "active"][[1]]
              )
            }
    if (length(conditions) != 2) {
      write_skip(result_dir, paste("Need exactly two conditions; found", paste(conditions, collapse = ", ")))
      next
    }
    sub$group_status <- factor(paste(sub$condition, sub$tdtom_status, sep = "__"))
    required <- as.vector(outer(conditions, c("negative", "positive"), paste, sep = "__"))
    if (!all(required %in% levels(sub$group_status))) {
      write_skip(result_dir, "One or more condition x tdTom status cells are absent")
      next
    }

    tab <- table(sub$condition, sub$tdtom_status)
    animal_tab <- table(sub$condition, sub$animal_id)
    n_by_condition <- rowSums(animal_tab > 0)
    if (min(n_by_condition) < 2) {
      write_skip(result_dir, "Fewer than two animals in at least one condition")
      next
    }

    y <- DGEList(counts = round(as.matrix(counts[, sub$sample_id, drop = FALSE])))
    design <- model.matrix(~0 + group_status, data = sub)
    colnames(design) <- safe(levels(sub$group_status))
    keep <- filterByExpr(y, design = design)
    if (sum(keep) < 2) {
      write_skip(result_dir, "Fewer than two genes passed pseudobulk expression filtering")
      next
    }
    y <- calcNormFactors(y[keep, , keep.lib.sizes = FALSE])
    v <- voom(y, design, plot = FALSE)

    # tdTom status is repeated within animal, while Active/Passive is between animals.
    corfit <- duplicateCorrelation(v, design, block = sub$animal_id)
    fit <- lmFit(v, design, block = sub$animal_id, correlation = corfit$consensus)

    c0 <- conditions[[1]]
    c1 <- conditions[[2]]
    g <- function(condition, status) safe(paste(condition, status, sep = "__"))
    contrast_strings <- c(
      paste0(g(c0, "positive"), "-", g(c0, "negative")),
      paste0(g(c1, "positive"), "-", g(c1, "negative")),
      paste0(g(c1, "positive"), "-", g(c0, "positive")),
      paste0(g(c1, "negative"), "-", g(c0, "negative")),
      paste0("(", g(c1, "positive"), "-", g(c1, "negative"), ")-(",
             g(c0, "positive"), "-", g(c0, "negative"), ")")
    )
    names(contrast_strings) <- c(
      paste0("tdTom_pos_vs_neg_in_", safe(c0)),
      paste0("tdTom_pos_vs_neg_in_", safe(c1)),
      paste0(safe(c1), "_vs_", safe(c0), "_within_tdTom_pos"),
      paste0(safe(c1), "_vs_", safe(c0), "_within_tdTom_neg"),
      "interaction"
    )
    contrast_matrix <- makeContrasts(contrasts = contrast_strings, levels = design)
    colnames(contrast_matrix) <- names(contrast_strings)
    fit2 <- eBayes(contrasts.fit(fit, contrast_matrix), robust = TRUE)

    for (contrast_name in colnames(contrast_matrix)) {
      result <- topTable(fit2, coef = contrast_name, number = Inf, sort.by = "P")
      result$gene <- rownames(result)
      result$anatomy <- anatomy
      result$cell_class <- cell_class
      result$contrast <- contrast_name
      result$n_animals_condition_1 <- n_by_condition[[1]]
      result$n_animals_condition_2 <- n_by_condition[[2]]
      result$duplicate_correlation <- corfit$consensus
      if (!is.null(categories)) {
        result <- merge(result, categories, by = "gene", all.x = TRUE, sort = FALSE)
      }
      result <- result[order(result$adj.P.Val, -abs(result$logFC)), ]
      write.csv(result, file.path(result_dir, paste0(safe(contrast_name), ".csv")), row.names = FALSE)
    }

    write.csv(sub, file.path(result_dir, "samples_used.csv"), row.names = FALSE)
    write.csv(
      data.frame(
        anatomy = anatomy, cell_class = cell_class,
        condition_1 = c0, condition_2 = c1,
        n_animals_condition_1 = n_by_condition[[1]],
        n_animals_condition_2 = n_by_condition[[2]],
        duplicate_correlation = corfit$consensus,
        genes_tested = sum(keep)
      ),
      file.path(result_dir, "model_summary.csv"), row.names = FALSE
    )
  }
}
