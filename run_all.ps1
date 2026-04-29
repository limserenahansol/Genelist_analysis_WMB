# Run all pipeline steps. Edit paths if your xlsx lives elsewhere.
$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$OutDir = Join-Path $RepoRoot "outputs"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$InputXlsx = "C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v6_source_audit.xlsx"
$AuditOut = Join-Path $OutDir "mouse_6_region_celltype_GPCR_probe_list_v6_plus_ALLEN_PYTHON_AUDIT.xlsx"
$V7Out = Join-Path $OutDir "mouse_6_region_celltype_GPCR_probe_list_v7_allen_clusters.xlsx"
$GpcrOutput = Join-Path $OutDir "mouse_6_region_celltype_GPCR_probe_list_v6_WITH_GPCR_COMPUTED.xlsx"

Set-Location $RepoRoot

Write-Host "== allen_v6_workbook_audit =="
python .\allen_v6_workbook_audit.py
$AuditFixed = "C:\Users\hsollim\Downloads\mouse_6_region_celltype_GPCR_probe_list_v6_plus_ALLEN_PYTHON_AUDIT.xlsx"
if (Test-Path $AuditFixed) { Copy-Item $AuditFixed $AuditOut -Force }

Write-Host "== wmb_enrich (cluster census only) =="
python .\wmb_enrich_probe_workbook_v7.py --input $InputXlsx --output $V7Out

Write-Host "== gpcr_rank_patch_v6 (long; multi-GB downloads) =="
python .\gpcr_rank_patch_v6.py --xlsx $InputXlsx --output $GpcrOutput

Write-Host "Done. Check: $OutDir and Downloads for audit xlsx if not copied."
