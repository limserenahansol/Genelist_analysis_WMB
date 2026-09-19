"""Append the agreed Jesse genes (including optional) to MSGS111.

Formatting rule: openpyxl append-only. No existing cell is edited, no gene is
removed or re-ranked, column widths / freeze panes / styles stay as they are.
New data rows copy Calibri 11 from the last existing data row.

Adds
  SHARED_PANEL_ORDER  ranks 159-168
      13_Jesse_morphine_state  Per2 Pcsk1 Per1 Camk2g Bhlhe40 Sema3e
      14_Jesse_ORB_GPCR        Chrm1 Grm8 Gpr26 Rxfp1
  ORBm_ORDER          same genes except Per1 (already present as 5_IEG)
  BMAp_ORDER          unchanged (Jesse is PL-ILA-ORB)
  ANCHOR_COVERAGE     unchanged
  FOR_MarkGreg        one new summary row (same pattern as the Dan-14 row)
  SOURCES             Jesse + GSE283418 (the 14 Dan genes had no source row yet)

Writes the Downloads order sheet the user named, and the repo copy.
"""
from __future__ import annotations

import shutil
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path.home() / "Downloads" / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
REPO = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"

WHY13 = (
    "Added from Jesse Niehaus PL-ILA-ORB opioid-dependence DEGs (5-day escalating "
    "morphine, DESeq2 subclass pseudobulk, padj<=0.1). Ranked by how many of the 12 "
    "ORBm anchor subclasses show DE. Reports morphine-dependence state, NOT cell type. "
    "No existing gene was removed or re-ranked."
)
WHY14 = (
    "Added from Jesse Niehaus PL-ILA-ORB enriched-GPCR list (vs the rest of the Allen "
    "4M-cell atlas), then filtered by Allen ORBm absolute % expressing (106,122 cells). "
    "Serves the druggable receptor map. No existing gene was removed or re-ranked."
)

# gene, block, free, serves, role, max_pct, max_mean, add_to_orbm
ADD = [
    (
        "Per2",
        "13_Jesse_morphine_state",
        False,
        "morphine-dependence state :: 11/12 ORBm anchors Up",
        "Broadest gene in Jesse's data: 11 of 12 ORBm anchors, glut 8 / GABA 3. Circadian clock.",
        None,
        None,
        True,
    ),
    (
        "Pcsk1",
        "13_Jesse_morphine_state",
        False,
        "morphine-dependence state :: 9/12 ORBm anchors Up",
        "9 of 12 anchors. Prohormone convertase 1 (proenkephalin / POMC processing).",
        None,
        None,
        True,
    ),
    (
        "Per1",
        "13_Jesse_morphine_state",
        False,
        "morphine-dependence state :: 8/12 ORBm anchors Up",
        "8 of 12 anchors. Second clock gene; confirms Per2. Already listed on ORBm_ORDER as a circadian IEG; added here so it is on the shared order list.",
        None,
        None,
        False,
    ),
    (
        "Camk2g",
        "13_Jesse_morphine_state",
        False,
        "morphine-dependence state :: 6/12 ORBm anchors Down",
        "Strongest Down gene (glut only). Direction control. Allen ORBm max 93% (L6 CT).",
        93.1,
        7.05,
        True,
    ),
    (
        "Bhlhe40",
        "13_Jesse_morphine_state",
        True,
        "morphine-dependence state :: 4/12 ORBm anchors Up",
        "Metabolic / circadian TF. Free on the Xenium Mouse Brain v1 base panel (0 slots).",
        None,
        None,
        True,
    ),
    (
        "Sema3e",
        "13_Jesse_morphine_state",
        True,
        "morphine-dependence state :: 3/12 ORBm anchors Up",
        "Free on the Xenium Mouse Brain v1 base panel (0 slots).",
        None,
        None,
        True,
    ),
    (
        "Chrm1",
        "14_Jesse_ORB_GPCR",
        False,
        "ORB-enriched GPCR :: Chrm1 92% Allen ORBm (L2/3 IT)",
        "M1 muscarinic (Gq). Allen 92%, 9/12 anchors >=50%. Panel already has Chrm2 (M2, Gi) — opposite signalling.",
        92.0,
        6.68,
        True,
    ),
    (
        "Grm8",
        "14_Jesse_ORB_GPCR",
        False,
        "ORB-enriched GPCR :: Grm8 99% Allen ORBm (L5 ET)",
        "mGlu8, group III (Gi). Allen 99%, 8/12 anchors >=50%. Panel has Grm1/Grm5 (group I, Gq) only.",
        98.7,
        8.66,
        True,
    ),
    (
        "Gpr26",
        "14_Jesse_ORB_GPCR",
        False,
        "ORB-enriched GPCR :: Gpr26 86% Allen ORBm (L4/5 IT)",
        "Optional high-abundance ORB GPCR. Allen 86%, 7/12 anchors >=50%. Broader than Chrm1/Cckbr; kept because it is actually visible.",
        85.8,
        6.00,
        True,
    ),
    (
        "Rxfp1",
        "14_Jesse_ORB_GPCR",
        True,
        "ORB-enriched GPCR :: Rxfp1 free on base, Allen 34% (L5 ET)",
        "Jesse's #2 ORB-enriched GPCR. Free on the Xenium Mouse Brain v1 base panel (0 slots). Circuit-proximity marker, not a morphine DEG.",
        34.1,
        2.32,
        True,
    ),
]


def _clone_font(cell, dest):
    dest.font = copy(cell.font)


def _write_row(ws, row, values, template_row):
    for col, val in enumerate(values, start=1):
        dest = ws.cell(row=row, column=col, value=val)
        _clone_font(ws.cell(template_row, column=col), dest)


def append_one(path: Path) -> dict:
    wb = load_workbook(path)
    sh = wb["SHARED_PANEL_ORDER"]
    orbm = wb["ORBm_ORDER"]
    sh_last, orb_last = sh.max_row, orbm.max_row
    # detect a prior Jesse append so re-runs do not duplicate
    existing = {
        sh.cell(r, 2).value
        for r in range(2, sh.max_row + 1)
    }
    to_add = [row for row in ADD if row[0] not in existing]
    if not to_add:
        wb.close()
        return {"skipped": True, "path": str(path)}

    sh_i = orb_i = 0
    for gene, block, _free, serves, role, max_pct, max_mean, add_orbm in to_add:
        why = (WHY13 if block.startswith("13") else WHY14) + f" || {role}"
        sh_i += 1
        rank = sh_last - 1 + sh_i  # header-inclusive: last data rank is sh_last-1
        _write_row(
            sh,
            sh_last + sh_i,
            [rank, gene, block, serves, why, max_pct, max_mean, None],
            sh_last,
        )
        if add_orbm:
            orb_i += 1
            orb_rank = orb_last - 1 + orb_i
            _write_row(
                orbm,
                orb_last + orb_i,
                [orb_rank, gene, block, serves, why],
                orb_last,
            )

    customs = [g for g, _, free, *_ in to_add if not free]
    frees = [g for g, _, free, *_ in to_add if free]
    n_shared = sh_last - 1 + sh_i
    n_custom = 114 + len(customs)
    n_free = 44 + len(frees)

    fg = wb["FOR_MarkGreg"]
    r = fg.max_row + 1
    item = (
        f"{len(to_add)} genes appended (Jesse ORB: morphine state + GPCR map, "
        f"including optional Camk2g / Gpr26)"
    )
    detail = (
        f"Block 13_Jesse_morphine_state: Per2, Pcsk1, Per1, Camk2g, Bhlhe40, Sema3e. "
        f"Block 14_Jesse_ORB_GPCR: Chrm1, Grm8, Gpr26, Rxfp1. "
        f"{len(customs)} new custom slots ({', '.join(customs)}); "
        f"{', '.join(frees)} are already free on the 10x Mouse Brain v1 base panel (0 slots). "
        f"Added at the bottom of SHARED_PANEL_ORDER and ORBm_ORDER. Per1 was already on "
        f"ORBm_ORDER as a circadian IEG and is now also on the shared order list (not duplicated "
        f"on ORBm_ORDER). No existing gene was removed or re-ranked. BMAp_ORDER is unchanged "
        f"because Jesse's data is PL-ILA-ORB. Shared panel is now {n_shared} genes = "
        f"{n_free} free on base + {n_custom} custom (was 158 = 44 + 114). "
        f"These genes report morphine-dependence state or the ORB GPCR map, not cell type, "
        f"so ANCHOR_COVERAGE is unchanged and all 20 cell types remain separable. "
        f"Not added: Mas1, Gpr68, Mchr1, Arid5b, Gadd45a, Sfrp1, Glipr1, Vdr, or the rest of Jesse's 304 DEGs."
    )
    fg.cell(row=r, column=1, value=item)
    fg.cell(row=r, column=2, value=detail)
    fg.cell(row=r, column=1).font = copy(fg.cell(6, 1).font)
    fg.cell(row=r, column=2).font = copy(fg.cell(6, 2).font)

    src = wb["SOURCES"]
    already_src = {src.cell(i, 1).value for i in range(2, src.max_row + 1)}
    new_sources = []
    if "Niehaus2026_ORB" not in already_src:
        new_sources.append(
            [
                "Niehaus2026_ORB",
                "Jesse Niehaus (personal communication)",
                "Niehaus J. PL-ILA-ORB opioid-dependence DEGs and enriched GPCRs, shared 2026-09-09.",
                2026,
                "unpublished",
                None,
                None,
                None,
                "Opioid-dependence DEGs (IEG 77, TF 179, synaptic plasticity 45, GPCR 34) from 5-day "
                "escalating morphine, DESeq2 subclass pseudobulk padj<=0.1, plus PL-ILA-ORB enriched "
                "GPCRs. Basis for blocks 13_Jesse_morphine_state and 14_Jesse_ORB_GPCR. "
                "Replaces the Lui2021 stand-in for Jesse's ORBm list.",
                "NO",
                "Received as per-subclass DEG tables (gene, n_DE_clusters, direction, DE_clusters), not raw counts.",
            ]
        )
    if "GSE283418" not in already_src:
        new_sources.append(
            [
                "GSE283418",
                "Berg & Scherrer (GSE283418)",
                "Spatial molecular profiling of amygdalar neurons enables precision pharmacology against pain unpleasantness.",
                2025,
                "GEO dataset",
                None,
                None,
                "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE283418",
                "Custom 98-gene Resolve Molecular Cartography amygdala panel. 14 genes scored as "
                "BMAp-informative in Allen were appended as block 12_GSE283418_added. Remaining "
                "off-panel genes (including Sfrp1, Glipr1, Vdr) all score max_spec < 1.0, so nothing "
                "further was added. Replaces the Hochgerner2023 stand-in.",
                "NO",
                "GEO metadata only (family.soft, series matrix); no raw expression matrix downloaded.",
            ]
        )
    tmpl = src.max_row
    for i, vals in enumerate(new_sources):
        _write_row(src, tmpl + 1 + i, vals, tmpl)

    wb.save(path)
    wb.close()
    return {
        "skipped": False,
        "path": str(path),
        "n_shared": n_shared,
        "n_custom": n_custom,
        "n_free": n_free,
        "customs": customs,
        "frees": frees,
        "n_orbm_added": orb_i,
    }


def main() -> None:
    targets = []
    for p in (DL, REPO):
        if p.exists():
            targets.append(p)
        else:
            print("missing", p)

    # write Downloads first (the file the user named)
    results = []
    for p in targets:
        try:
            results.append(append_one(p))
            print("wrote", p)
        except PermissionError:
            alt = p.with_name(p.stem + "_Jesse10" + p.suffix)
            shutil.copy2(p, alt)
            results.append(append_one(alt))
            print("locked", p.name, "->", alt.name)

    print(results[-1])


if __name__ == "__main__":
    main()
