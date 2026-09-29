# 10x R tutorial path on the current Explorer ROIs.
# Applies the single-sample steps: load, ROI cell IDs, QC, cluster, markers,
# spatial plot, CSV for Explorer. Does not Harmony-merge ORBm with BMAp.
# Seed 1 is Seurat's convention; Python used seed 0 for Leiden.

suppressPackageStartupMessages({
  library(Seurat)
  library(Matrix)
  library(ggplot2)
})

args_rois <- list(
  list(
    name = "orbm_right",
    xenium = "D:/output-XETG00277__0063814__Region_3__20260923__002559",
    explorer = "orbm_right_cells_stats.csv",
    leiden = "outputs/orbm_right/cells_annotated.csv",
    allen = "C:/Users/hsollim/Desktop/cursor/Xenium_downstream/allen_label_transfer/cell_groups_ORBm_seurat.csv"
  ),
  list(
    name = "bmap_left",
    xenium = "D:/output-XETG00277__0063817__Region_1__20260923__002558",
    explorer = "bmap_left_cells_stats.csv",
    leiden = "outputs/bmap_left/cells_annotated.csv",
    allen = "C:/Users/hsollim/Desktop/cursor/Xenium_downstream/allen_label_transfer/cell_groups_BMAp_seurat.csv"
  )
)

min_counts <- 20
min_genes <- 5
resolution <- 1.0

ari <- function(a, b) {
  a <- as.character(a)
  b <- as.character(b)
  tab <- table(a, b)
  n <- sum(tab)
  sum_comb <- function(v) sum(v * (v - 1) / 2)
  sum_ij <- sum_comb(tab)
  sum_a <- sum_comb(rowSums(tab))
  sum_b <- sum_comb(colSums(tab))
  expected <- sum_a * sum_b / sum_comb(n)
  max_index <- 0.5 * (sum_a + sum_b)
  as.numeric((sum_ij - expected) / (max_index - expected))
}

tukey_hi <- function(x, k = 3) {
  q <- quantile(x, c(0.25, 0.75), na.rm = TRUE)
  unname(q[2] + k * (q[2] - q[1]))
}

run_one <- function(cfg) {
  message("ROI ", cfg$name)
  out <- file.path("outputs", cfg$name, "seurat_10x")
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  fig <- file.path(out, "figures")
  dir.create(fig, recursive = TRUE, showWarnings = FALSE)

  expl <- read.csv(file.path(cfg$xenium, cfg$explorer), comment.char = "#", check.names = FALSE)
  ids <- unique(as.character(expl[["Cell ID"]]))
  mat <- Read10X(file.path(cfg$xenium, "cell_feature_matrix"))
  if (is.list(mat)) mat <- mat[["Gene Expression"]]
  missing <- setdiff(ids, colnames(mat))
  if (length(missing)) stop(length(missing), " Explorer IDs missing from h5")
  meta <- read.csv(gzfile(file.path(cfg$xenium, "cells.csv.gz")), check.names = FALSE)
  meta$cell_id <- as.character(meta$cell_id)
  meta <- meta[match(ids, meta$cell_id), , drop = FALSE]
  rownames(meta) <- meta$cell_id

  obj <- CreateSeuratObject(counts = mat[, ids, drop = FALSE], meta.data = meta)
  area_cut <- tukey_hi(obj$cell_area)
  keep <- obj$nCount_RNA >= min_counts & obj$nFeature_RNA >= min_genes & obj$cell_area <= area_cut
  obj <- subset(obj, cells = colnames(obj)[keep])

  obj <- NormalizeData(obj, verbose = FALSE)
  obj <- FindVariableFeatures(obj, nfeatures = min(2000, nrow(obj)), verbose = FALSE)
  obj <- ScaleData(obj, verbose = FALSE)
  obj <- RunPCA(obj, npcs = 20, verbose = FALSE, seed.use = 1)
  obj <- FindNeighbors(obj, dims = 1:20, verbose = FALSE)
  algo <- 1
  algo_name <- "louvain"
  leiden_try <- tryCatch({
    obj <- FindClusters(obj, resolution = resolution, algorithm = 4, random.seed = 1, verbose = FALSE)
    algo <<- 4
    algo_name <<- "leiden"
    TRUE
  }, error = function(e) FALSE)
  if (!isTRUE(leiden_try)) {
    obj <- FindClusters(obj, resolution = resolution, algorithm = 1, random.seed = 1, verbose = FALSE)
  }
  obj <- RunUMAP(obj, dims = 1:20, seed.use = 1, verbose = FALSE)

  markers <- FindAllMarkers(
    obj, only.pos = TRUE, min.pct = 0.25, logfc.threshold = 0.5,
    test.use = "wilcox", verbose = FALSE
  )
  write.csv(markers, file.path(out, "seurat_markers.csv"), row.names = FALSE)
  groups <- data.frame(
    cell_id = colnames(obj),
    group = paste0("seurat_", as.character(Idents(obj))),
    stringsAsFactors = FALSE
  )
  write.csv(groups, file.path(out, "cell_groups_seurat_cluster.csv"), row.names = FALSE)

  py <- read.csv(cfg$leiden, check.names = FALSE, row.names = 1)
  py$cell_id <- rownames(py)
  both <- merge(groups, py[, c("cell_id", "leiden")], by = "cell_id")
  allen <- read.csv(cfg$allen, check.names = FALSE)
  allen$cell_id <- as.character(allen$cell_id)
  names(allen)[names(allen) == "group"] <- "allen_coarse"
  both <- merge(both, allen[, c("cell_id", "allen_coarse")], by = "cell_id")

  p1 <- ggplot(obj@meta.data, aes(x_centroid, y_centroid, color = seurat_clusters)) +
    geom_point(size = 0.7) +
    scale_y_reverse() +
    coord_equal() +
    labs(
      title = paste0(cfg$name, " Seurat clusters (resolution ", resolution, ", ", algo_name, ")"),
      x = "x centroid (um)", y = "y centroid (um)", color = "Seurat"
    ) +
    theme_classic(base_size = 11) +
    theme(legend.position = "right")
  ggsave(file.path(fig, "01_spatial_seurat.png"), p1, width = 7, height = 5.5, dpi = 160)

  um <- as.data.frame(Embeddings(obj, "umap"))
  um$cluster <- as.character(Idents(obj))
  p2 <- ggplot(um, aes(umap_1, umap_2, color = cluster)) +
    geom_point(size = 0.7) +
    labs(title = paste0(cfg$name, " UMAP by Seurat cluster"), x = "UMAP-1", y = "UMAP-2", color = "Seurat") +
    theme_classic(base_size = 11)
  ggsave(file.path(fig, "02_umap_seurat.png"), p2, width = 6.2, height = 5, dpi = 160)

  summary <- data.frame(
    roi = cfg$name,
    n_explorer = length(ids),
    n_after_qc = ncol(obj),
    algorithm = algo_name,
    n_clusters = length(unique(as.character(Idents(obj)))),
    ari_vs_python_leiden = ari(both$group, both$leiden),
    ari_vs_allen_coarse = ari(both$group, both$allen_coarse),
    stringsAsFactors = FALSE
  )
  # group.y is Allen group after the second merge
  names(summary)[names(summary) == "ari_vs_allen_coarse"] <- "ari_vs_allen_coarse"
  write.csv(summary, file.path(out, "summary.csv"), row.names = FALSE)
  print(summary)
  invisible(summary)
}

results <- do.call(rbind, lapply(args_rois, run_one))
dir.create("outputs/seurat_10x", showWarnings = FALSE)
write.csv(results, "outputs/seurat_10x/summary.csv", row.names = FALSE)
message("DONE")
