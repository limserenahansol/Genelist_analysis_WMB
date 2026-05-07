#!/usr/bin/env python
"""
A04_allen_marker_discovery_template.py

Module A: Allen-only computational module.
Purpose:
- Template for full all-gene marker discovery.

This is intentionally a template because all-gene analysis on Allen WMB can be very large.
Recommended strategies:
1. Start with one region and one subclass/supertype.
2. Use sparse matrices and chunked aggregation.
3. Save summaries as parquet/csv, not Excel.
4. Only export top markers to the final workbook.
"""

print('Template only. Implement full all-gene marker discovery on workstation/HPC after confirming region mapping.')
print('Recommended target vs background comparisons:')
print('1) target region x cell type vs other cell types in same region')
print('2) target region x cell type vs same cell type outside region')
print('3) target region x cell type vs all other cells')
