# Genelist analysis (Allen WMB-10X)

Python tools to validate a mouse six-region GPCR / probe workbook against [Allen Brain Cell Atlas](https://alleninstitute.github.io/abc_atlas_access/) WMB-10X metadata and optional expression matrices (`get_gene_data` on official **log2** `.h5ad` files).

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`
- Disk: cache grows to **many GB** when expression matrices are downloaded (full GPCR run touches ~11 regional log2 h5ads).

## Cache directory

By default scripts use `C:\Users\hsollim\Downloads\abc_atlas_cache`. Override with environment variable:

```powershell
$env:ABC_ATLAS_CACHE = "D:\abc_atlas_cache"
```

## Input workbook

Place your v6 audit workbook (or adjust paths in each script / CLI flags). Default path in scripts:

`mouse_6_region_celltype_GPCR_probe_list_v6_source_audit.xlsx`

## Scripts

| Script | Purpose |
|--------|---------|
| `allen_v6_workbook_audit.py` | Small-file download + symbol audit; writes `*_plus_ALLEN_PYTHON_AUDIT.xlsx`. |
| `wmb_enrich_probe_workbook_v7.py` | Cluster census from cell metadata; optional `--compute-th-gpcr` for TH matrix. |
| `gpcr_rank_patch_v6.py` | Full pipeline: ROI cells → per-matrix `get_gene_data` → mean log2 + rank within cluster/subclass; adds `Computed_GPCR_*` sheets. |

**Important:** For `gpcr_rank_patch_v6.py`, use `--output path\to\result.xlsx` so Excel does not lock the input file. Close Excel while running.

## Run all (Windows)

From this repo folder, after editing paths inside `run_all.ps1` if needed:

```powershell
.\run_all.ps1
```

Audit and v7 outputs go under `outputs\` by default. The GPCR workbook can be 100MB+; set `$GpcrOutput` in the script.

## References

- [ABC Atlas access – getting started](https://alleninstitute.github.io/abc_atlas_access/notebooks/getting_started.html)
- [Selection example](https://alleninstitute.github.io/abc_atlas_access/notebooks/abc_atlas_selection_example.html)

## License

Use and attribution follow Allen Institute / ABC Atlas terms for downloaded data.
