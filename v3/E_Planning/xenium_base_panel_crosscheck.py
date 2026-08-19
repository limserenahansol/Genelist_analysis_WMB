#!/usr/bin/env python
"""Cross-check the D07 ordering list against the 10x Xenium Mouse Brain v1 base panel.

A Xenium custom add-on is capped at 100 genes on top of a pre-designed panel, so
the question that gates the October order is not "how many genes do we want" but
"how many of them do we have to pay a custom slot for". Genes already on the base
panel are free.

Writes:
  v3/outputs/xenium_mouse_brain_base_panel.txt   the base panel gene list
  v3/outputs/Xenium_addon_vs_base_panel.csv      per-gene free / add-on verdict
"""
from __future__ import annotations

import json
import sys
import urllib.request as request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
V3 = HERE.parents[1]
OUTDIR = V3 / "outputs"
ORDER_XLSX = OUTDIR / "FINAL_ordering_BMAp_ORBm_TRAP.xlsx"
PANEL_TXT = OUTDIR / "xenium_mouse_brain_base_panel.txt"
OUT_CSV = OUTDIR / "Xenium_addon_vs_base_panel.csv"

ADDON_CAP = 100

# The pre-designed panel content is not published as a standalone download, but the
# public demo dataset for that panel ships the same gene_panel.json.
PANEL_JSON_URL = (
    "https://cf.10xgenomics.com/samples/xenium/1.0.2/"
    "Xenium_V1_FF_Mouse_Brain_MultiSection_1/"
    "Xenium_V1_FF_Mouse_Brain_MultiSection_1_gene_panel.json"
)
CONTROL_PREFIXES = ("NegControl", "BLANK", "Unassigned")

# Not mouse genes, so they can never be on a pre-designed mouse panel and always
# need advanced custom design from a supplied sequence.
TRANSGENES = {"tdtomato", "icre", "egfp", "wpre", "cre"}

REGION_SHEETS = {"BMAp": "BMAp_order_list", "ORBm": "ORBm_order_list"}


def load_base_panel() -> list[str]:
    """Base-panel gene symbols, cached locally after the first fetch."""
    if PANEL_TXT.exists():
        genes = [g.strip() for g in PANEL_TXT.read_text().splitlines() if g.strip()]
        print(f"base panel: {len(genes)} genes (cached {PANEL_TXT.name})")
        return genes

    req = request.Request(PANEL_JSON_URL, headers={"User-Agent": "Mozilla/5.0"})
    payload = json.loads(request.urlopen(req, timeout=60).read())
    targets = payload.get("payload", {}).get("targets", [])
    names = [t.get("type", {}).get("data", {}).get("name") for t in targets]
    genes = sorted({n for n in names if n and not n.startswith(CONTROL_PREFIXES)})
    n_control = len(names) - len(genes)
    print(f"base panel: {len(genes)} genes + {n_control} negative controls (fetched)")

    PANEL_TXT.parent.mkdir(parents=True, exist_ok=True)
    PANEL_TXT.write_text("\n".join(genes))
    return genes


def load_order_list() -> pd.DataFrame:
    frames = []
    for region, sheet in REGION_SHEETS.items():
        d = pd.read_excel(ORDER_XLSX, sheet_name=sheet)
        d["region"] = region
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["gene"] = df["gene"].astype(str).str.strip()
    return df


def annotate(df: pd.DataFrame, base: list[str]) -> pd.DataFrame:
    base_lower = {g.lower() for g in base}
    # A gene can sit in different blocks in BMAp and ORBm. Collapse to the union
    # by strongest (lowest) priority, and take block/category from the row that
    # actually set that priority -- otherwise a gene promoted to priority 1 in one
    # region inherits the other region's weaker block label.
    ranked = df.sort_values(["gene", "order_priority"])
    best = ranked.groupby("gene", as_index=False).first()
    regions = (
        df.groupby("gene")["region"].agg(lambda s: "+".join(sorted(set(s)))).rename("regions")
    )
    uni = best[["gene", "order_priority", "block", "primary_category"]].rename(
        columns={"order_priority": "priority"}
    ).merge(regions, on="gene")
    lower = uni["gene"].str.lower()
    uni["is_transgene"] = lower.isin(TRANSGENES)
    uni["in_base_panel"] = lower.isin(base_lower) & ~uni["is_transgene"]
    uni["needs_addon_slot"] = ~uni["in_base_panel"]
    return uni


def report(uni: pd.DataFrame) -> None:
    p1 = uni[uni["priority"] == 1]
    p2 = uni[uni["priority"] == 2]
    n_addon = int(p1["needs_addon_slot"].sum())
    spare = ADDON_CAP - n_addon

    print("\nPRIORITY 1 — the list we order")
    print(f"  genes                        {len(p1)}")
    print(f"  already on base panel        {int(p1['in_base_panel'].sum())}   (free)")
    print(f"  transgene custom probes      {int(p1['is_transgene'].sum())}")
    print(f"  ADD-ON SLOTS REQUIRED        {n_addon} / {ADDON_CAP}")
    print(f"  slots still free             {spare}")

    print("\n  by block:")
    blocks = p1.groupby("block").agg(genes=("gene", "nunique"), free=("in_base_panel", "sum"))
    blocks["addon"] = blocks["genes"] - blocks["free"]
    print(blocks.to_string().replace("\n", "\n  "))

    print("\nPRIORITY 2 — backups for the spare slots")
    print(f"  genes                        {len(p2)}")
    print(f"  free off the base panel      {int(p2['in_base_panel'].sum())}")
    print(f"  would consume a slot         {int(p2['needs_addon_slot'].sum())}")
    promotable = min(spare, int(p2["needs_addon_slot"].sum()))
    covered = len(p1) + int(p2["in_base_panel"].sum()) + promotable
    print(f"  promotable within the cap    {promotable}")
    print(f"  -> total curated genes on the ordered panel: {covered} of {len(p1) + len(p2)}")

    for label, subset in [("free off the base panel", p1[p1["in_base_panel"]]),
                          ("must be custom add-on", p1[p1["needs_addon_slot"]])]:
        names = sorted(subset["gene"])
        print(f"\nPriority-1 genes {label}  [n={len(names)}]")
        for i in range(0, len(names), 10):
            print("   ", ", ".join(names[i : i + 10]))


def main() -> int:
    if not ORDER_XLSX.exists():
        print(f"[ERROR] missing {ORDER_XLSX}. Run D07_make_trap_ordering_workbook.py first.")
        return 1
    base = load_base_panel()
    uni = annotate(load_order_list(), base)
    report(uni)
    uni.sort_values(["priority", "needs_addon_slot", "gene"]).to_csv(OUT_CSV, index=False)
    print(f"\n[DONE] {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
