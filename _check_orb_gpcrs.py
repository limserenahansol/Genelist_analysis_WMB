import pandas as pd
from pathlib import Path

x = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx")
sh = pd.read_excel(x, "SHARED_PANEL_ORDER")
orb = pd.read_excel(x, "ORBm_ORDER")
bm = pd.read_excel(x, "BMAp_ORDER")
base = {
    g.strip()
    for g in open(
        r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs\xenium_mouse_brain_base_panel.txt"
    )
    if g.strip()
}

genes = [
    "Mas1",
    "Rxfp1",
    "Gpr68",
    "Mchr1",
    "Grm8",
    "Cckbr",
    "Chrm1",
    "Gpr26",
    "Adra1a",
    "Gpr12",
    "Gpr3",
    "Hcrtr2",
    "Hrh3",
]

print("SHARED", len(sh), "ORBm", len(orb), "BMAp", len(bm))
print()
print(
    f"{'gene':<10} {'SHARED':<8} {'ORBm':<8} {'BMAp':<8} {'base':<8} rank  block  why"
)
for g in genes:
    on_s = g in set(sh.gene.astype(str))
    on_o = g in set(orb.gene.astype(str))
    on_b = g in set(bm.gene.astype(str))
    on_base = g in base
    rank = ""
    block = ""
    why = ""
    if on_s:
        row = sh[sh.gene == g].iloc[0]
        rank = int(row.order_rank)
        block = row.block
        why = str(row.why)[:80]
    print(
        f"{g:<10} {str(on_s):<8} {str(on_o):<8} {str(on_b):<8} {str(on_base):<8} {rank}  {block}  {why}"
    )

print()
print("GPCR-block genes on SHARED:")
gpcr_blocks = sh[sh.block.astype(str).str.contains("GPCR", case=False, na=False)]
print(gpcr_blocks[["order_rank", "gene", "block"]].to_string(index=False))
