"""Jesse lists vs our Allen ORBm / BMAp abundance (already-computed tables)."""
from pathlib import Path

import pandas as pd

V3 = Path(__file__).resolve().parents[1]
LONG = V3 / "outputs/subclass_markers_expanded/Subclass_Discriminating_Markers_long.csv"
TIER = V3 / "outputs/subclass_markers_expanded/GPCR_Specificity_Tiers.csv"
RANK = V3 / "outputs/gpcr_full/Allen_GPCR_Ranking_subclass.csv"
JESSE = V3 / "inputs" / "Jesse_ORB"
DEG = JESSE / "OpioidDependenceDEG_genesets_forHansol090926"

ORBM_GLUT = [
    "004 L6 IT CTX Glut",
    "005 L5 IT CTX Glut",
    "006 L4/5 IT CTX Glut",
    "007 L2/3 IT CTX Glut",
    "022 L5 ET CTX Glut",
    "029 L6b CTX Glut",
    "030 L6 CT CTX Glut",
    "032 L5 NP CTX Glut",
]
ORBM_GABA = [
    "046 Vip Gaba",
    "049 Lamp5 Gaba",
    "052 Pvalb Gaba",
    "053 Sst Gaba",
]
ANCHORS = ORBM_GLUT + ORBM_GABA

long = pd.read_csv(LONG)
rank = pd.read_csv(RANK)
tier = pd.read_csv(TIER)

glut = pd.read_csv(JESSE / "PL_ILA_ORB_GlutamatergicNeurons_EnrichedGPCRs.csv")
gaba = pd.read_csv(JESSE / "PL_ILA_ORB_GABAergicNeurons_EnrichedGPCRs.csv")
glut = glut.rename(columns={glut.columns[1]: "gene", glut.columns[2]: "n_glut"})
gaba = gaba.rename(columns={gaba.columns[1]: "gene", gaba.columns[2]: "n_gaba"})
enr = glut[["gene", "n_glut"]].merge(gaba[["gene", "n_gaba"]], on="gene", how="outer")
enr["n_glut"] = enr["n_glut"].fillna(0).astype(int)
enr["n_gaba"] = enr["n_gaba"].fillna(0).astype(int)
enr["n_tot"] = enr["n_glut"] + enr["n_gaba"]
enr = enr.sort_values("n_tot", ascending=False)

focus = [
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


def summarize_long(gene: str) -> dict | None:
    d = long[(long.gene == gene) & (long.region_user == "ORBm")]
    if d.empty:
        return None
    a = d[d.subclass.isin(ANCHORS)]
    glut = a[a.subclass.isin(ORBM_GLUT)]
    gaba = a[a.subclass.isin(ORBM_GABA)]
    top = a.sort_values("pct_expr", ascending=False).iloc[0] if len(a) else None
    bma = long[(long.gene == gene) & (long.region_user == "BMAp")]
    return {
        "source": "A06_expanded",
        "n_orbm_anchors_ge5": int((a.pct_expr >= 5).sum()),
        "n_glut_ge5": int((glut.pct_expr >= 5).sum()),
        "n_gaba_ge5": int((gaba.pct_expr >= 5).sum()),
        "max_pct_glut": float(glut.pct_expr.max()) if len(glut) else 0,
        "max_pct_gaba": float(gaba.pct_expr.max()) if len(gaba) else 0,
        "max_mean_glut": float(glut.mean_log2_expr.max()) if len(glut) else 0,
        "top": f"{top.subclass} {top.pct_expr:.1f}%" if top is not None else "",
        "bmap_max_pct": float(bma.pct_expr.max()) if len(bma) else float("nan"),
    }


def summarize_rank(gene: str) -> dict | None:
    d = rank[(rank.gpcr_gene == gene) & (rank.region_user == "ORBm")]
    if d.empty:
        return None
    a = d[d.subclass.isin(ANCHORS)]
    if a.empty:
        a = d[~d.subclass.str.contains(" NN", na=False)]
    glut = a[a.subclass.isin(ORBM_GLUT)]
    gaba = a[a.subclass.isin(ORBM_GABA)]
    top = a.sort_values("pct_expr", ascending=False).iloc[0]
    other = rank[(rank.gpcr_gene == gene) & (rank.region_user != "ORBm")]
    other_max = float(other.groupby("region_user")["pct_expr"].max().max()) if len(other) else float("nan")
    return {
        "source": "A03_40GPCR",
        "n_orbm_anchors_ge5": int((a.pct_expr >= 5).sum()) if len(a) else 0,
        "n_glut_ge5": int((glut.pct_expr >= 5).sum()) if len(glut) else 0,
        "n_gaba_ge5": int((gaba.pct_expr >= 5).sum()) if len(gaba) else 0,
        "max_pct_glut": float(glut.pct_expr.max()) if len(glut) else 0,
        "max_pct_gaba": float(gaba.pct_expr.max()) if len(gaba) else 0,
        "max_mean_glut": float(glut.mean_log2_expr.max()) if len(glut) else 0,
        "top": f"{top.subclass} {top.pct_expr:.1f}%",
        "other_region_max_pct": other_max,
    }


print("=== FOCUS GPCRs (Jesse ORB-enriched top) vs our Allen tables ===")
print(
    f"{'gene':<8} {'j_glut':<7} {'j_gaba':<7} {'have':<12} "
    f"{'ORBm>=5':<8} {'g5':<4} {'b5':<4} {'maxG%':<7} {'maxB%':<7} {'mean':<6} top"
)
for g in focus:
    j = enr[enr.gene == g]
    jg = int(j.n_glut.iloc[0]) if len(j) else 0
    jb = int(j.n_gaba.iloc[0]) if len(j) else 0
    s = summarize_long(g) or summarize_rank(g)
    if s is None:
        print(f"{g:<8} {jg:<7} {jb:<7} NOT_IN_OURS  — no Allen score in our computed tables")
        continue
    print(
        f"{g:<8} {jg:<7} {jb:<7} {s['source']:<12} "
        f"{s['n_orbm_anchors_ge5']:<8} {s['n_glut_ge5']:<4} {s['n_gaba_ge5']:<4} "
        f"{s['max_pct_glut']:<7.1f} {s['max_pct_gaba']:<7.1f} {s['max_mean_glut']:<6.2f} {s['top']}"
    )

print()
print("=== Cckbr / Hcrtr2 ORBm subclass (A03 ranking) ===")
for g in ["Cckbr", "Hcrtr2"]:
    d = rank[(rank.gpcr_gene == g) & (rank.region_user == "ORBm") & rank.subclass.isin(ANCHORS)]
    d = d.sort_values("pct_expr", ascending=False)
    print(g)
    print(d[["subclass", "n_cells", "pct_expr", "mean_log2_expr"]].to_string(index=False))
    print()

print("=== Rxfp1 ORBm anchors (A06) ===")
d = long[(long.gene == "Rxfp1") & (long.region_user == "ORBm") & long.subclass.isin(ANCHORS)]
print(d.sort_values("pct_expr", ascending=False)[["subclass", "n_cells", "pct_expr", "mean_log2_expr"]].to_string(index=False))

# IEG / plast abundance for genes we actually have
print()
print("=== Jesse high-priority DEGs we CAN score in Allen (A06 long) ===")
priority = [
    "Per2",
    "Pcsk1",
    "Per1",
    "Nr4a3",
    "Dusp1",
    "Egr3",
    "Fos",
    "Arc",
    "Egr1",
    "Junb",
    "Nr4a1",
    "Bdnf",
    "Vgf",
    "Camk2g",
    "Hrh1",
    "Grm2",
    "Grm5",
    "Oprm1",
    "Ntsr1",
]
print(f"{'gene':<10} {'have':<5} {'ORBm>=5':<8} {'max%':<7} {'max_mean':<9} top")
for g in priority:
    d = long[(long.gene == g) & (long.region_user == "ORBm") & long.subclass.isin(ANCHORS)]
    if d.empty:
        # try rank
        r = rank[(rank.gpcr_gene == g) & (rank.region_user == "ORBm") & rank.subclass.isin(ANCHORS)]
        if r.empty:
            print(f"{g:<10} no")
            continue
        top = r.sort_values("pct_expr", ascending=False).iloc[0]
        print(
            f"{g:<10} rank  {int((r.pct_expr>=5).sum()):<8} {top.pct_expr:<7.1f} {top.mean_log2_expr:<9.2f} {top.subclass}"
        )
        continue
    top = d.sort_values("pct_expr", ascending=False).iloc[0]
    print(
        f"{g:<10} yes   {int((d.pct_expr>=5).sum()):<8} {top.pct_expr:<7.1f} {top.mean_log2_expr:<9.2f} {top.subclass}"
    )

print()
print("Jesse enriched GPCRs that ARE in our 40-GPCR Allen ranking:")
ours = set(rank.gpcr_gene.unique())
hit = enr[enr.gene.isin(ours)].sort_values("n_tot", ascending=False)
print(hit[["gene", "n_glut", "n_gaba", "n_tot"]].to_string(index=False))
print("n overlap", len(hit), "of", len(enr), "Jesse enriched GPCRs")
