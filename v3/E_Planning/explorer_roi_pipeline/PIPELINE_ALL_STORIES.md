# Xenium Explorer ROI pipeline — all analysis stories

**Trigger:** draw an ROI in Xenium Explorer → download the exports listed below → this pipeline starts.
**Do not overwrite** the instrument `D:\output-XETG00…` folders. Write all products under `Xenium_downstream/explorer_roi_pipeline/`.

Instrument panel on the current slides is **mBrain v1.1, 247 genes, 0 custom**. `tdTomato` / `iCre` are **not** on this run. The two current slides are **ORBm vs BMAp**, not mouse A vs mouse B of the same region.

---

## 1. What to download from Explorer (every story)

After lasso/rectangle, export **all** of these into the **same Xenium output folder** (or a sibling folder you point to in the ROI JSON). Names can vary; the JSON maps them.

| File | Why the pipeline needs it |
|------|---------------------------|
| `*_cells_stats.csv` | Cell IDs in the ROI. Column `Cell ID` is the barcode. `Cluster` is onboard graphclust. `Transcripts` and `Area (µm^2)` are Explorer summaries (independent QC check). |
| `*_coordinates.csv` | Polygon vertices in **µm** (same frame as `cells.parquet` centroids). Use this for ROI overlay, **not** the GeoJSON. |
| `*.geojson` | ROI outline in **image pixels**. Keep as an Explorer record. Do **not** overlay on µm centroids without an affine transform. |
| `*_cluster_stats.csv` | Explorer cluster composition inside the ROI (no p-values). |
| `*_transcript_stats.csv` | Explorer gene sums inside the ROI (no DE). |
| `*_combined_stats.csv` | Optional bundle of the above. |

**Rule Explorer uses (read this before interpreting Explorer tables):** a cell is counted only if it is **completely inside** the polygon. The Python path below uses **centroid-in-polygon** (or the exported Cell ID list) so edge cells can differ. Record which rule you used.

**What Explorer cannot do:** user-defined DE (tdTom+ vs −, mouse A vs B, custom groups). It has no p-values on annotation stats. Onboard DE in `analysis/diffexp/` is **graphclust / k-means only**.

**What you put back into Explorer:** `cell_groups.csv` with columns `cell_id,group` after Python/R labeling.

---

## 2. Story map (run now vs wait)

| Story | Scientific question | Current 247-gene pilot | Reporter-aware production experiment |
|-------|---------------------|------------------------|--------------------------|
| **S1** Cell-type–specific genes | Which genes mark clusters **inside one ROI / one region** | **Run now** (`run_from_explorer.py`) | Re-run on the production panel; same steps |
| **S2** tdTom+ vs tdTom− | DEG within a cell class, reporter+ vs − | **Blocked** — no `tdTomato` on panel; DAPI-only morphology | **Wait** — see `PIPELINE_LATER_REAL_DATA.md` |
| **S3** Mouse A vs mouse B | DEG / composition, **same region**, two animals | **Blocked** — slides are different anatomy, not two mice | **Wait** — animal is the experimental unit |
| **S4** Neighborhood | Do labeled types sit next to each other more than chance? | **Run now** (kNN z vs label permutation) | Re-run with production-panel labels / tdTom groups |
| **S5** Composition | Fraction of types in the ROI | **Run now** | Compare animals with a hierarchical model, not a χ² on cells |
| **S6** ROI vs rest of section QC | Did the lasso pick a biased, high-count subset? | **Run now** | Same |
| **S7** tdTom × Active/Passive factorial | Reporter enrichment and five within-type contrasts | **Blocked** — no tdTom / conditions | Run `run_factorial_tdtom_active_passive.py`, then limma-voom |

**Out of scope for these stories:** BMAp **versus** ORBm as a biological contrast. Run each ROI as its own within-region analysis.

---

## 3. Shared QC (pre-registered; do not retune after looking at DE)

| Parameter | Value | Reason |
|-----------|-------|--------|
| Min gene-feature counts / cell | 20 | Drop empty / dying nuclei |
| Min genes detected / cell | 5 | Drop almost-empty barcodes |
| Cell area | Tukey high fence, k = 3 | Drop merged / giant objects |
| Gene filter | Detected in ≥ 3 cells | Drop unused probes |
| Normalization | Counts → 10⁴ / cell → log1p | Standard for Wilcoxon on log data |
| PCA / neighbors / Leiden | 20 PCs, k = 15, resolution 1.0, seed 0 | Fixed; report 0.5 and 1.5 as sensitivity |
| Wilcoxon | On **log-normalized** values (`use_raw=True`), not scaled PCA input | Avoid DE on z-scored matrix |
| Cluster-specific gene call | adj. p < 0.05, logFC > 0.5, fraction in cluster > 0.25 | Stops ubiquitous genes looking “specific” |

Nuclear expansion on this instrument is **5 µm**. Neighbor bleed can inflate reporter+ and some DEGs. Treat single-cell tdTom calls as **probabilistic** until you check neighbors (Story 2 later).

---

## 4. Story 1 — cell-type–specific genes (run now)

### Explorer

1. Draw ROI so the polygon **fully contains** the cells you care about (Explorer stats) **or** accept centroid assignment (Python).
2. Download the files in §1.
3. Do not edit `cells.parquet` / `cell_feature_matrix.h5`.

### Python (`run_from_explorer.py`)

1. Read `*_cells_stats.csv` → Cell IDs.
2. Subset `cell_feature_matrix.h5` + `cells.parquet` (x,y µm, area, transcript_counts).
3. QC §3. Write dropped IDs.
4. Marker-module baseline (ORBm layers / BMAp glut–GABA–glia). This uses the same matrix and is an annotation aid, not independent validation.
5. Exclude tdTomato/iCre and predefined activity/state genes from the identity PCA; then PCA → neighbors → UMAP → Leiden.
6. Wilcoxon rank genes per Leiden cluster.
7. Compare Leiden to (a) modules, (b) Explorer onboard `Cluster` (ARI / NMI).
8. Spatial kNN: fraction of neighbors with the same Leiden vs label permutation.
9. Write `cell_groups.csv` for Explorer.

### Validation (must pass before calling a gene a cell-type marker)

1. **Quantitative:** Wilcoxon filters in §3.
2. **Specificity:** require both fraction in the cluster > 0.25 and an in-minus-out detection difference > 0.15.
3. **Reference check:** compare with Allen/reference-transfer labels when available. Module and onboard agreement are same-matrix concordance checks.
4. **Spatial:** expression map is restricted, not section-wide wash.
5. **Failure cases:** clusters with majority module `unassigned` or purity < 0.5 are labeled `_mixed`. Do not publish mixed-cluster “markers” as cell-type genes.

### Figures produced now

Per ROI under `outputs/<roi_name>/figures/`:

- `01_qc` — ROI vs full-region transcripts; gene counts; area fence
- `02_spatial_labels` — Leiden, marker modules, and onboard labels on the same µm axes
- `03_umap` — Leiden and marker-module views
- `04_dotplot_markers` — curated markers
- `05_zscore_heatmap` — top filtered cluster markers
- `06_spatial_marker_genes` — raw transcript maps; zeros gray; positive-cell 99th-percentile cap
- `07_composition_counts` — Leiden × module counts
- `08_neighborhood_z` — log2 observed/permuted-expected neighborhood enrichment
- `09_top_markers_table` — marker effect and detection specificity
- `10_cell_identity_overview` — concise PI-facing spatial, composition, confidence summary
- `11_gpcr_state_tf_overview` — GPCR, state/plasticity, and TF detection by broad class

---

## 5. Story 2 — tdTom+ vs tdTom− (later only)

**Blocked on current data.** Confirm with `gene_panel.json` / `adata.var_names`: no `tdTomato`.

When reporter-aware production runs exist, follow `PIPELINE_LATER_REAL_DATA.md`. Do not substitute DAPI intensity, random cells, or ORBm vs BMAp.

---

## 6. Story 3 — mouse A vs mouse B (later only)

**Blocked on current data.** Slide `0063814` = ORBm cassette; `0063817` = BMAp cassette.

Need: **same named region**, ≥2 animals, ROIs drawn with the same rule. Cells are not independent replicates. Use **pseudobulk** (animal × cell type). Details in `PIPELINE_LATER_REAL_DATA.md`.

---

## 7. How to start after a new Explorer download

1. Copy exports into the Xenium folder (or set paths in JSON).
2. Add a block to `rois_current.json` (or a new JSON): `roi_name`, `anatomy`, `xenium`, `explorer_cells_csv`, `explorer_coordinates_csv`.
3. Run:

```text
python run_from_explorer.py --config rois_current.json
```

4. Load `outputs/<roi>/cell_groups.csv` in Explorer (Cells → groups).
5. For production-panel tdTom / multi-animal stories, use `rois_later_template.json` and the later markdown. Those scripts **exit with SKIPPED** until the required files exist.

---

## 8. Current ROIs already in the JSON

| ROI | Slide | Anatomy | Explorer cells CSV | Status |
|-----|-------|---------|--------------------|--------|
| `orbm_right` | 0063814 Region_3 | ORBm | `orbm_right_cells_stats.csv` | S1/S4/S5/S6 runnable |
| `bmap_left` | 0063817 Region_1 | BMAp | `bmap_left_cells_stats.csv` | S1/S4/S5/S6 runnable |
