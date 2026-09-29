# Pipeline to run later — production-panel real data (Ai14 tdTom and replicated animals)

This document is the **runbook**, not a completed analysis. Do not treat the 247-gene ORBm/BMAp pilot as a substitute.

**Start the same way as the current pipeline:** draw ROI in Xenium Explorer → download `*_cells_stats.csv`, `*_coordinates.csv`, GeoJSON, cluster/transcript stats → point a JSON config at those files → run the scripts below.

The production panel must include a custom `tdTomato` probe. Confirm the ordered panel and
`gene_panel.json` before analysis because the panel gene count may change between revisions.
Nuclear expansion remains **5 µm** unless you change it on the instrument.

---

## 0. Files you still download from Explorer (unchanged)

Same table as `PIPELINE_ALL_STORIES.md` §1.

Additional **instrument** files (already in the Xenium folder, do not export from Explorer):

- `cell_feature_matrix.h5` — must contain `tdTomato`; `iCre` is optional context and may be transient
- `cells.parquet` — centroids µm, area
- `transcripts.parquet` or `transcripts.csv.gz` — optional, for bleed diagnostics
- `experiment.xenium` — panel name / XOA version

**Put back into Explorer:** `cell_groups.csv` (`cell_id,group`) after you define tdTom+ / tdTom− or mouse labels in Python/R.

Explorer still **cannot** compute these DEs. Its cluster DE is onboard clustering only.

---

## 1. Story 2 — DEG tdTom+ vs tdTom−

### 1.1 Question

Within **one region** and **one cell class** (example: ORBm L5 glut, or BMAp GABA), which 298-panel genes differ between reporter-positive and reporter-negative cells?

Do **not** pool all cell types and call genome-wide DE: you will rediscover cell-type composition (tdTom lineage vs the rest).

### 1.2 Explorer

1. Draw the anatomical ROI (same containment rule as Story 1).
2. Download Cell ID list.
3. Optional: create an Explorer annotation named `tdTom_pos` only if you already have a **cell group CSV**. Explorer has no tdTom gate on this DAPI-only morphology run; in the production experiment, gating is from the **tdTomato gene count**, not from Explorer drawings.

### 1.3 Python / R (when data exist)

Script: `run_story2_tdtom.py` (exits SKIPPED until `tdTomato` is in `var_names`).

**Pre-register before looking at p-values:**

| Choice | Default | Why |
|--------|---------|-----|
| tdTom+ call | Calibrate with Cre-negative or no-induction controls; default exploratory gate is `tdTomato` counts ≥ 2 | A permanent Ai14 reporter is zero-inflated and one assigned transcript can reflect spillover |
| Gate sensitivity | Always report gates at ≥1, ≥2, and ≥3 transcripts | Shows whether the biological conclusion depends on one-count cells |
| Bleed diagnostic | Flag, but do not automatically drop, one-count cells whose spatial k=6 neighbors are majority tdTom+ | A true labeled cell can also sit inside a labeled neighborhood |
| Cell class | Restrict DE to one Leiden/module class with n+ and n− both ≥ 20 cells **per animal** | Avoid composition DE |
| Test | Descriptive effects within one animal; paired/animal-level pseudobulk with replicated animals | Cells are not biological replicates |
| Multiple testing | BH within the measured panel genes, within that class | Do not pretend genome-wide |
| Effect | logFC and % expressing, not p-value alone | |

**Independent checks:**

1. Confirm the tdTomato gate in negative controls. `iCre` may be transient in an iCreER/TRAP design and is not required to remain positive in every permanently labeled Ai14 cell.
2. Spatial map of tdTom+ should match the expected lineage, not a random salt-and-pepper unless biology says so.
3. DEGs should not be only the reporter and ubiquitous genes (`Malat1` is not on this panel; still drop pan-glial / pan-neuronal hits unless class-restricted).
4. Repeat DE after dropping 1-count-only tdTom+ cells; if the gene list collapses, the result was bleed.

**Figures to make later:**

- Spatial: tdTom counts, binary call, neighbor-bleed flags
- UMAP: tdTom within one class
- Volcano of measured panel genes **per class**
- Dotplot of significant genes in + vs −
- Optional iCre vs tdTom overlay, interpreted as temporal/technical context rather than required concordance

**Do not run on current 247 data.** The skip script writes `outputs/story2_tdtom/SKIPPED.md` with the missing gene list.

---

## 2. Story 3 — DEG / composition mouse A vs mouse B

### 2.1 Question

For **the same named region** (ORBm with ORBm, BMAp with BMAp), what differs between experimental conditions: type fractions and gene expression **within a type**?

### 2.2 Design (experimental unit)

- Unit = **animal**, not cell.
- Current pilot slides **fail** this: 0063814 is ORBm, 0063817 is BMAp.
- JSON must contain both `animal_id` and `condition`.
- Multiple ROIs from one animal are nested samples and are aggregated within animal.
- Prefer ≥3 independent animals per condition, same anatomy, same Explorer rule, same QC.

### 2.3 Explorer

1. Draw comparable ROIs (same structure, similar area if possible). Record area µm² from the cells_stats header.
2. Download one Cell ID CSV **per ROI**.
3. JSON must include `animal_id` and `anatomy`. Two blocks with different `anatomy` must not enter this story.

### 2.4 Statistics

Script: `run_story3_mouse_ab.py` (exits SKIPPED until ≥2 animals share `anatomy`).

**Composition**

- Counts of cell types **per animal**.
- Test: Dirichlet-multinomial or animal-level proportions + Wilcoxon/t on n_animals.
- **Invalid:** χ² / Fisher on cells pooled across animals (pseudoreplication).

**DEG**

- Pseudobulk: sum counts for (animal × cell type).
- DESeq2 or edgeR on those columns.
- Minimum: 2 vs 2 animals is weakly powered; ≥3 per condition is the preferred floor. Report logFC + uncertainty.
- If only 1 vs 1: **no p-value**. Report descriptive fold changes and a “n = 1 vs 1, not a test” banner on every figure.

**Independent checks**

1. Same-type QC: median gene counts similar across animals (otherwise library / ROI bias).
2. Spatial: A vs B difference is not “one ROI was white matter.”
3. Hold out one gene family you did not optimize (for example, a GPCR already on the production panel) and see if it moves with the rest.

**Figures to make later**

- Side-by-side spatial of the two animals, **shared** color legend
- Stacked composition bars with animal as the x-axis (not cells)
- Pseudobulk heatmap (genes × animal, split by type)
- MA / volcano only if n_animals allows a model

---

## 3. Story 1 on the production panel (re-run, not wait)

When the real zarr/h5 arrives, **re-run** `run_from_explorer.py` with a new JSON. Wilcoxon gene lists will change because the feature space is 298 not 247. Do not copy 247 Leiden “markers” onto 298 without re-testing.

Module gene lists must be rewritten: many ORBm layer genes on 247 are absent from 298, and many 298 GPCRs are absent from 247.

---

## 4. JSON template

See `rois_later_template.json`. Required keys:

```text
roi_name, anatomy, animal_id, xenium, explorer_cells_csv, explorer_coordinates_csv
```

Optional: `explorer_geojson` (archive only).

---

## 5. Stop conditions (do not improvise)

| Situation | Action |
|-----------|--------|
| `tdTomato` missing | Skip Story 2; do not gate on DAPI |
| One animal only | Skip Story 3 tests; descriptive figures only |
| Two slides, different anatomy | Skip Story 3; those are two Story 1 jobs |
| n+ or n− < 20 in a class | Skip DE for that class |
| Explorer cell IDs not in h5 | Fail the run; do not silently drop |
