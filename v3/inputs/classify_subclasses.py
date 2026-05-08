#!/usr/bin/env python
"""
classify_subclasses.py

Auto-classify EVERY Allen subclass within each target region as:
  - target              : anatomically belongs to the region's primary tissue
  - exclusion_counterstain : in the ROI but anatomically from an adjacent
                           or different region (boundary contamination /
                           neighboring populations)
  - skip                : non-neuronal (NN suffix) or n_cells < 30

The classification rules are based on Allen WMB subclass-name prefixes
(e.g. '061 STR D1 Gaba' -> striatal -> target for CP, exclusion for everything
else; '030 L6 CT CTX Glut' -> cortical -> target for ORBm/AId, exclusion
for CP/BMAp etc.).

Inputs:
  v3/outputs/gpcr_full/Allen_GPCR_Ranking_subclass.csv
  v3/inputs/celltype_to_subclass_anchor.csv  (hand-curated; preserved)
  v3/inputs/curated_marker_template.csv      (hand-curated; preserved)

Outputs:
  v3/inputs/celltype_to_subclass_anchor.csv  (rewritten with full coverage)
  v3/inputs/curated_marker_template.csv      (rewritten with auto markers)
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
ALLEN_CSV = REPO / "v3/outputs/gpcr_full/Allen_GPCR_Ranking_subclass.csv"
HAND_ANCHOR = REPO / "v3/inputs/celltype_to_subclass_anchor.csv"
HAND_MARKERS = REPO / "v3/inputs/curated_marker_template.csv"
OUT_ANCHOR = REPO / "v3/inputs/celltype_to_subclass_anchor.csv"
OUT_MARKERS = REPO / "v3/inputs/curated_marker_template.csv"

MIN_CELLS = 30

# Non-neuronal class detection. NN suffix is the canonical Allen marker;
# we also exclude IMN (immature) and CR (Cajal-Retzius / migratory) when
# we are looking at adult neuronal probe panels.
NN_PATTERNS = re.compile(
    r"\b(NN|Astro|Oligo|OPC|Micro|Microglia|Endo|Peri|SMC|VLMC|BAM|CHOR|Ependymal|"
    r"Astroependymal|ABC)\b",
    re.IGNORECASE,
)


# STRICT per-region target rules. ONLY subclasses whose Allen name matches
# the user-defined region's anatomical acronym count as targets.
# Everything else in the ROI is exclusion_counterstain.
#
# User instruction (verbatim): "we only need to target cell types or subclass
# in BMAp only not MEA or CEA or AAA ... such as RE we do not care others only RE"
REGION_RULES: dict[str, list[tuple[str, str]]] = {
    "CP": [
        # Striatal (target) - any subclass whose name contains STR.
        (r"\bSTR\b", "target"),
        # Everything else in CP ROI (CTX leak, OB-STR migration, thalamic
        # boundary, cortical IN, NN) = exclusion or skip.
    ],
    "BMAp": [
        # STRICT: only subclasses with BMA in the name (e.g. 113 MEA-COA-BMA,
        # 014 LA-BLA-BMA-PA). MEA-only, CEA, AAA, BST, COA = exclusion.
        (r"\bBMA\b", "target"),
    ],
    "RE": [
        # STRICT: only subclasses with RE in the name (152 RE-Xi).
        # PVT, MH, AV, AD, RT-ZI = exclusion.
        (r"\bRE\b", "target"),
    ],
    "LM": [
        # STRICT: only mammillary "MM" subclasses (143 MM-ant, 144 MM Foxb1).
        # AHN, LHA, DMH, ARH, PVH = exclusion (hypothalamic neighbors).
        (r"\bMM\b", "target"),
    ],
    "ORBm": [
        # Cortical (target). ORBm = orbital cortex medial. Allen does not
        # subdivide cortical subclasses by area, so ALL cortical glutamatergic
        # (L?/CTX) and cortical interneurons (Pvalb/Sst/Vip/Lamp5 Gaba) are
        # treated as ORBm-resident.
        (r"\bL\d", "target"),  # L2/3, L4/5, L5, L6 ...
        (r"\bCTX\b", "target"),
        (r"\bCLA-EPd-CTX\b", "target"),
        # Cortical interneurons (their names don't carry CTX prefix)
        (r"\bPvalb\s+Gaba\b", "target"),
        (r"\bPvalb chandelier\b", "target"),
        (r"\bSst\s+Gaba\b", "target"),
        (r"\bVip\s+Gaba\b", "target"),
        (r"\bLamp5\b", "target"),
        (r"\bSncg\s+Gaba\b", "target"),
    ],
    "AId": [
        (r"\bL\d", "target"),
        (r"\bCTX\b", "target"),
        (r"\bCLA-EPd-CTX\b", "target"),
        (r"\bIT\s+EP-CLA\b", "target"),
        (r"\bIT AON-TT-DP\b", "target"),
        (r"\bIT TPE-ENT\b", "target"),
        (r"\bIT PIR-ENTl\b", "target"),
        (r"\bPvalb\s+Gaba\b", "target"),
        (r"\bPvalb chandelier\b", "target"),
        (r"\bSst\s+Gaba\b", "target"),
        (r"\bVip\s+Gaba\b", "target"),
        (r"\bLamp5\b", "target"),
        (r"\bSncg\s+Gaba\b", "target"),
    ],
    "CA": [
        # Hippocampus + ProSubiculum + Subiculum + DG.
        (r"\bCA1\b", "target"),
        (r"\bCA2\b", "target"),
        (r"\bCA3\b", "target"),
        (r"\bDG\b", "target"),
        (r"\bDG-PIR\b", "target"),
        (r"\bProS\b", "target"),
        (r"\bSUB\b", "target"),
    ],
}


def is_nonneuronal(subclass: str) -> bool:
    """Detect glia/vasculature/IMN/etc. (NN) - skip these for probe panels."""
    return bool(NN_PATTERNS.search(subclass))


def classify(region: str, subclass: str) -> str:
    """Return 'target', 'exclusion_counterstain', or 'skip'."""
    if is_nonneuronal(subclass):
        return "skip"
    rules = REGION_RULES.get(region, [])
    for pattern, role in rules:
        if re.search(pattern, subclass):
            return role
    return "exclusion_counterstain"


def detect_class(subclass: str) -> str:
    """Coarse cell class for marker auto-assignment.

    Returns 'glut_vglut1', 'glut_vglut2', 'glut_other', 'gaba', 'chol', 'mixed', 'other'.
    Allen WMB subclasses tag class with: 'Glut' (glutamatergic), 'Gaba' (GABAergic),
    'Gaba-Chol' (cholinergic-GABA mixed), 'Dopa-Gaba' (dopa-GABA), 'IMN' (immature),
    'CR' (Cajal-Retzius), etc. Slc17a7+ vs Slc17a6+ requires the marker gene
    panel for confidence; use heuristics from the canonical anatomical region.
    """
    s = subclass.lower()
    if "gaba-chol" in s:
        return "chol"
    if "gaba" in s and "glut" in s:
        return "mixed"
    if "gaba" in s:
        return "gaba"
    if "glut" in s:
        # Cortex / hippocampal pyramidal / OB / DG = VGLUT1 (Slc17a7)
        # Subcortical glut (RE, PVT, MH, MM, MEA, BMA Otp+) = VGLUT2 (Slc17a6)
        # We make a best-effort guess from the prefix.
        if re.search(r"\bCTX\b|\bL\d|\bCA[123]\b|\bDG\b|\bSUB\b|\bProS\b|\bENT\b|\bMEA Slc17a7\b|\bBMA\b|\bPIR\b|\bAON\b|\bCLA\b|\bEP-CLA\b|\bHPF CR\b|\bRHP\b", subclass):
            return "glut_vglut1"
        return "glut_vglut2"
    if "imn" in s:
        return "other"
    if "dopa" in s:
        return "other"
    return "other"


CLASS_MARKERS: dict[str, tuple[str, str]] = {
    # class -> (positive, exclusion)
    "glut_vglut1": ("Slc17a7", "Gad1,Gad2,Slc32a1,Slc17a6"),
    "glut_vglut2": ("Slc17a6", "Gad1,Gad2,Slc32a1,Slc17a7"),
    "glut_other": ("Slc17a7,Slc17a6", "Gad1,Gad2,Slc32a1"),
    "gaba": ("Gad1,Gad2,Slc32a1", "Slc17a7,Slc17a6"),
    "chol": ("Chat,Slc18a3,Slc5a7", "Slc17a7,Slc17a6"),
    "mixed": ("Slc17a7,Gad1", "-"),
    "other": ("-", "-"),
}


def main() -> None:
    print(f"[INFO] Reading {ALLEN_CSV}")
    allen = pd.read_csv(ALLEN_CSV)
    if "n_cells" not in allen.columns:
        raise SystemExit("Allen CSV must have n_cells column")

    print(f"[INFO] Reading hand-curated anchor: {HAND_ANCHOR}")
    hand_anchor = pd.read_csv(HAND_ANCHOR)
    print(f"[INFO] Reading hand-curated markers: {HAND_MARKERS}")
    hand_markers = pd.read_csv(HAND_MARKERS)

    # Build hand-curated lookup by (region, subclass)
    hand_pairs = set()
    for _, r in hand_anchor.iterrows():
        hand_pairs.add((r["region_user"], r["allen_subclass_anchor"]))

    # Hand-curated cell_type_labels per region (we PRESERVE these)
    hand_labels = set()
    for _, r in hand_anchor.iterrows():
        hand_labels.add((r["region_user"], r["cell_type_label"]))

    # Per-region subclass roster (max n_cells per subclass)
    sub_per_region = (
        allen.groupby(["region_user", "subclass"])["n_cells"]
        .max()
        .reset_index()
    )

    new_anchor_rows: list[dict] = []
    new_marker_rows: list[dict] = []
    seen_marker = set()  # (region, cell_type_label) — avoid duplicates

    # Pass 1: keep hand-curated anchor rows ONLY if their subclass passes
    # the strict region rule. Drop rows where the subclass is anatomically
    # outside the user-defined region (e.g. v6 hand-curated label
    # "BMA/MEA VGLUT2-like" -> all anchors are MEA-only -> drop).
    dropped_hand: list[tuple[str, str, str]] = []
    kept_labels: dict[tuple[str, str], int] = {}  # (region, cell_type_label) -> count of surviving anchors
    for _, r in hand_anchor.iterrows():
        region = r["region_user"]
        ct_label = r["cell_type_label"]
        sub = r["allen_subclass_anchor"]
        if region not in REGION_RULES:
            continue
        if classify(region, sub) != "target":
            dropped_hand.append((region, ct_label, sub))
            continue
        new_anchor_rows.append(dict(r))
        kept_labels[(region, ct_label)] = kept_labels.get((region, ct_label), 0) + 1

    if dropped_hand:
        print(f"[INFO] dropped {len(dropped_hand)} hand-curated anchor rows that failed strict rule:")
        for region, ct, sub in dropped_hand[:30]:
            print(f"        - {region:<6} '{ct[:48]}' -> {sub}")
        if len(dropped_hand) > 30:
            print(f"        ... and {len(dropped_hand)-30} more")

    # Pass 2: for every (region, subclass) NOT already in hand_pairs, classify
    # and add an auto row.
    skipped_nn = 0
    skipped_lowcells = 0
    auto_target = 0
    auto_excl = 0

    for _, r in sub_per_region.iterrows():
        region = r["region_user"]
        sub = r["subclass"]
        n = int(r["n_cells"])
        if region not in REGION_RULES:
            continue
        if (region, sub) in hand_pairs:
            continue  # hand-curated; preserve
        if n < MIN_CELLS:
            skipped_lowcells += 1
            continue
        if is_nonneuronal(sub):
            skipped_nn += 1
            continue

        role = classify(region, sub)
        # Auto cell_type_label = the Allen subclass itself.
        ct_label = sub  # use the full subclass id as the label
        new_anchor_rows.append(
            {
                "region_user": region,
                "cell_type_label": ct_label,
                "allen_subclass_anchor": sub,
                "confidence": "auto",
                "role": role,
                "notes": (
                    f"Auto-classified {role} (n={n}); class={detect_class(sub)}"
                ),
            }
        )
        if role == "target":
            auto_target += 1
        else:
            auto_excl += 1

        # Generic markers based on cell class
        if (region, ct_label) not in seen_marker:
            seen_marker.add((region, ct_label))
            cls = detect_class(sub)
            pos, neg = CLASS_MARKERS.get(cls, CLASS_MARKERS["other"])
            new_marker_rows.append(
                {
                    "region_user": region,
                    "cell_type_label": ct_label,
                    "marker_genes": pos,
                    "exclusion_markers": neg,
                    "source": "auto_class_inference",
                    "confidence": "auto",
                    "notes": f"Auto class={cls}; from Allen subclass name '{sub}'",
                }
            )

    # Pass 3: keep hand-curated marker rows verbatim
    for _, r in hand_markers.iterrows():
        if (r["region_user"], r["cell_type_label"]) not in seen_marker:
            seen_marker.add((r["region_user"], r["cell_type_label"]))
            new_marker_rows.insert(0, dict(r))

    print()
    print("[STATS]")
    print(f"  hand-curated anchor rows:   {len(hand_anchor)}")
    print(f"  auto target rows added:     {auto_target}")
    print(f"  auto exclusion rows added:  {auto_excl}")
    print(f"  skipped (NN/glia):          {skipped_nn}")
    print(f"  skipped (n_cells < {MIN_CELLS}):       {skipped_lowcells}")
    print(f"  -- total final anchor rows: {len(new_anchor_rows)}")
    print(f"  -- total marker rows:       {len(new_marker_rows)}")

    # Write output
    out_a = pd.DataFrame(new_anchor_rows)
    cols = ["region_user", "cell_type_label", "allen_subclass_anchor", "confidence", "role", "notes"]
    out_a = out_a[cols]
    out_a.to_csv(OUT_ANCHOR, index=False)
    print(f"[OK] wrote {OUT_ANCHOR} ({len(out_a)} rows)")

    out_m = pd.DataFrame(new_marker_rows)
    cols_m = ["region_user", "cell_type_label", "marker_genes", "exclusion_markers", "source", "confidence", "notes"]
    out_m = out_m[cols_m]
    out_m.to_csv(OUT_MARKERS, index=False)
    print(f"[OK] wrote {OUT_MARKERS} ({len(out_m)} rows)")

    # Per-region breakdown of final anchor
    print()
    print("[BREAKDOWN by region]")
    for region in REGION_RULES:
        sub = out_a[out_a["region_user"] == region]
        n_target = (sub["role"] == "target").sum()
        n_excl = (sub["role"] == "exclusion_counterstain").sum()
        print(f"  {region:<6}  total={len(sub):>3d}  target={n_target:>3d}  exclusion={n_excl:>3d}")


if __name__ == "__main__":
    main()
