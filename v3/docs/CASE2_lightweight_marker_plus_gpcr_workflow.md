# Case 2: Lightweight Published-Marker + GPCR-Only Workflow

## When to use

Use this when the full raw-data/all-gene workflow is too big, or when you need a fast v7 probe-panel correction.

## Core idea

```text
Published/curated marker genes define the cell type.
Allen WMB 10X computes GPCR expression for those cell types.
MERFISH/CCF validates whether the cell type is present in the region.
```

## Steps

```text
1. Fill inputs/curated_marker_template.csv
2. Fill inputs/mouse_gpcr_universe_template.csv
3. Run B01_standardize_published_markers.py
4. Run B02_validate_marker_presence_in_allen.py
5. Run A03_allen_gpcr_expression.py in GPCR-only mode
6. Run D01/D02/D03 to integrate evidence
```

## What this workflow can answer

```text
Does GPCR X appear in Allen expression data for this cell type?
Is GPCR X more expressed than other GPCRs in this cell type?
What fraction of cells express GPCR X?
Should GPCR X be kept, downgraded, or removed from the candidate panel?
```

## What this workflow cannot fully answer

```text
It does not discover all new marker genes.
It does not prove full regional specificity unless MERFISH/CCF mapping is included.
It does not replace paper raw-data validation for BMAp-specific claims.
```

## Best first target

Run this workflow first for:

```text
CP D1/D2 SPNs
BMAp posterior VGLUT1-like populations
RE midline thalamic glutamatergic populations
ORBm/AId cortical excitatory and interneuron subclasses
LM only after region acronym confirmation
```
