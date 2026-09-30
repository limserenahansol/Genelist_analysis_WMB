suppressPackageStartupMessages({
  library(Seurat)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4) {
  stop("usage: Rscript run_seurat_label_transfer_generic.R REF_COUNTS QUERY_COUNTS REF_META OUTPUT")
}

set.seed(0)
ref_counts_path <- args[[1]]
query_counts_path <- args[[2]]
ref_meta_path <- args[[3]]
output_path <- args[[4]]

ref_mat <- as.matrix(read.csv(ref_counts_path, row.names = 1, check.names = FALSE))
query_mat <- as.matrix(read.csv(query_counts_path, row.names = 1, check.names = FALSE))
ref_meta <- read.csv(ref_meta_path, row.names = 1, check.names = FALSE)

common <- intersect(rownames(ref_mat), rownames(query_mat))
if (length(common) < 50) stop("too few shared genes: ", length(common))
ref_mat <- ref_mat[common, , drop = FALSE]
query_mat <- query_mat[common, , drop = FALSE]
ref_meta <- ref_meta[colnames(ref_mat), , drop = FALSE]

ref <- CreateSeuratObject(counts = ref_mat, meta.data = ref_meta, min.cells = 0, min.features = 0)
query <- CreateSeuratObject(counts = query_mat, min.cells = 0, min.features = 0)
ref <- NormalizeData(ref, verbose = FALSE)
query <- NormalizeData(query, verbose = FALSE)
VariableFeatures(ref) <- common
ref <- ScaleData(ref, features = common, verbose = FALSE)
npcs <- min(30, length(common) - 1, ncol(ref) - 1)
ref <- RunPCA(ref, features = common, npcs = npcs, verbose = FALSE)
dims_use <- 1:min(20, npcs)

anchors <- FindTransferAnchors(
  reference = ref,
  query = query,
  dims = dims_use,
  reference.reduction = "pca",
  features = common,
  verbose = FALSE
)
pred <- TransferData(
  anchorset = anchors,
  refdata = ref$subclass,
  dims = dims_use,
  verbose = FALSE
)

out <- data.frame(
  cell_key = colnames(query),
  seurat_subclass = pred$predicted.id,
  seurat_score = pred$prediction.score.max,
  stringsAsFactors = FALSE
)
write.csv(out, output_path, row.names = FALSE)
cat("wrote", output_path, "n=", nrow(out), "shared_genes=", length(common), "\n")
