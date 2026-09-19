"""Compare Jesse ORB-enriched GPCRs against our Allen ORBm / BMAp stats."""
from pathlib import Path

import pandas as pd

LONG = Path(
    r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs"
    r"\subclass_markers_expanded\Subclass_Discriminating_Markers_long.csv"
)
TIER = Path(
    r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs"
    r"\subclass_markers_expanded\GPCR_Specificity_Tiers.csv"
)
RANK = Path(
    r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs"
    r"\gpcr_full\Allen_GPCR_Ranking_subclass.csv"
)
UNIV = Path(
    r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\inputs\expanded_panel_universe.csv"
)
JESSE = Path(r"C:\Users\hsollim\Downloads\Gene_lists")

ORBM_GLUT = {
    "004 L6 IT CTX Glut",
    "005 L5 IT CTX Glut",
    "006 L4/5 IT CTX Glut",
    "007 L2/3 IT CTX Glut",
    "022 L5 ET CTX Glut",
    "029 L6b CTX Glut",
    "030 L6 CT CTX Glut",
    "032 L5 NP CTX Glut",
}
ORBM_GABA = {
    "046 Vip Gaba",
    "049 Lamp5 Gaba",
    "052 Pvalb Gaba",
    "053 Sst Gaba",
}
# Jesse also counted these PL-ILA-ORB types
JESSE_EXTRA_GLUT = {
    "002 IT EP-CLA Glut",
    "003 L5/6 IT TPE-ENT Glut",
    "010 IT AON-TT-DP Glut",
}
JESSE_EXTRA_GABA = {
    "047 Sncg Gaba",
    "051 Pvalb chandelier Gaba",
    "056 Sst Chodl Gaba",
}

genes = [
    ("Mas1", "glut", 17),
    ("Rxfp1", "glut", 15),
    ("Gpr68", "glut", 11),
    ("Mchr1", "glut", 10),
    ("Grm8", "glut", 9),
    ("Cckbr", "glut", 8),
    ("Chrm1", "glut", 8),
    ("Gpr26", "glut", 8),
    ("Adra1a", "gaba", 8),
    ("Gpr12", "gaba", 8),
    ("Gpr3", "gaba", 6),
    ("Hcrtr2", "gaba", 6),
    ("Hrh3", "gaba", 6),
]

long = pd.read_csv(LONG)
tier = pd.read_csv(TIER)
univ_genes = set()
if UNIV.exists():
    univ = pd.read_csv(UNIV)
    col = "gene_symbol" if "gene_symbol" in univ.columns else univ.columns[0]
    univ_genes = set(univ[col].astype(str))

print("long genes present:", sorted(set(long.gene) & {g for g, _, _ in genes}))
print("long genes MISSING:", sorted({g for g, _, _ in genes} - set(long.gene)))
print("in expanded universe:", sorted({g for g, _, _ in genes} & univ_genes))
print()

rank = pd.read_csv(RANK)
print("in our 40-GPCR ranking:", sorted({g for g, _, _ in genes} & set(rank.gpcr_gene)))
print()


def n_ge(df, names, thresh=5.0):
    sub = df[df.subclass.isin(names)]
    return int((sub.pct_expr >= thresh).sum()), sub


print(
    f"{'gene':<8} {'jesse':<6} {'inAllen':<8} {'ORBm>=5%':<10} "
    f"{'glut>=5':<8} {'gaba>=5':<8} {'max%_glut':<10} {'max%_gaba':<10} "
    f"{'top_ORBm':<28} {'BMAp_max%':<10} {'ORB>BMA?'}"
)

for g, side, n_j in genes:
    d = long[(long.gene == g)]
    if d.empty:
        print(f"{g:<8} {n_j:<6} NO       — not in our A06 expanded Allen pull")
        continue
    orb = d[d.region_user == "ORBm"]
    bma = d[d.region_user == "BMAp"]
    glut_n, glut = n_ge(orb, ORBM_GLUT | JESSE_EXTRA_GLUT)
    gaba_n, gaba = n_ge(orb, ORBM_GABA | JESSE_EXTRA_GABA)
    panel_n, _ = n_ge(orb, ORBM_GLUT | ORBM_GABA)
    wide_n = int((orb[~orb.subclass.str.contains("NN", na=False) & (orb.pct_expr >= 5)].shape[0]))
    max_g = float(glut.pct_expr.max()) if len(glut) else 0
    max_b = float(gaba.pct_expr.max()) if len(gaba) else 0
    top = ""
    if len(orb):
        t = orb.sort_values("pct_expr", ascending=False).iloc[0]
        top = f"{t.subclass} {t.pct_expr:.0f}%"
    bmax = float(bma.pct_expr.max()) if len(bma) else float("nan")
    higher = "yes" if (max(max_g, max_b) > (bmax if bmax == bmax else 0) + 5) else "no/similar"
    print(
        f"{g:<8} {n_j:<6} YES      {panel_n:<10} {glut_n:<8} {gaba_n:<8} "
        f"{max_g:<10.1f} {max_b:<10.1f} {top:<28} {bmax:<10.1f} {higher}"
    )
    # print ORBm anchor pcts
    anchors = orb[orb.subclass.isin(ORBM_GLUT | ORBM_GABA)].sort_values("pct_expr", ascending=False)
    bits = [f"{s.split()[0]}:{p:.0f}%" for s, p in zip(anchors.subclass, anchors.pct_expr) if p >= 5]
    print("         ORBm anchors >=5%:", ", ".join(bits) if bits else "(none)")

print()
print("=== our GPCR tier file (only 40 curated GPCRs) ===")
for g, _, _ in genes:
    t = tier[(tier.region_user == "ORBm") & (tier.gpcr_gene == g)]
    if len(t):
        r = t.iloc[0]
        print(
            f"{g}: panel {int(r.n_panel_detected)}/12 ({r.gpcr_tier_panel}), "
            f"top {r.top_panel_subclass} {r.top_panel_pct:.1f}%"
        )
