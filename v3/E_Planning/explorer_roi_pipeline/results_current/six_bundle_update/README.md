# Six-bundle update

This is a compact, reviewable result snapshot. Raw Xenium bundles, `.h5ad` objects, and per-cell
tables remain local.

- `inventory/`: actual XOA metrics and Explorer-export inventory for all six bundles.
- `target_comparison/`: actual cross-ROI summaries for five available ORBm/BMAp selections.
- `target_rois/`: summary JSON plus the cell-identity and GPCR/state/TF figure for each target ROI.
- `additional_bla_cea/`: exploratory figures produced by the earlier nine-ROI extraction. BLA/CEA
  use the BMAp marker-module baseline and are not a CEA-specific taxonomy.
- `seurat_check/`: compact Seurat-versus-Python method comparison.
- `story3_expanded/`: sections aggregated within animal. It is descriptive because each anatomy
  currently has one pilot animal and no Active/Passive condition replication.

The pilot panel lacks `tdTomato`; no reporter-effect result is claimed.
