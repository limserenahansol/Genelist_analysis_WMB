"""Compare Jesse PL-ILA-ORB gene lists to the current Xenium ORBm / shared panel."""
from pathlib import Path
import shutil

import pandas as pd

JESSE = Path(r"C:\Users\hsollim\Downloads\Gene_lists")
DEG = JESSE / "OpioidDependenceDEG_genesets_forHansol090926"
XLSX = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx")
BASE = Path(
    r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs\xenium_mouse_brain_base_panel.txt"
)
OUT = Path(
    r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs\Jesse_ORB_vs_Xenium_panel.xlsx"
)
DL = Path(r"c:\Users\hsollim\Downloads\Jesse_ORB_vs_Xenium_panel.xlsx")

# Our ORBm anchors, matched by Allen subclass number
ORBM_NUMS = {"004", "005", "006", "007", "022", "029", "030", "032", "046", "049", "052", "053"}

sh = pd.read_excel(XLSX, "SHARED_PANEL_ORDER")
orb = pd.read_excel(XLSX, "ORBm_ORDER")
on_shared = set(sh.gene.astype(str))
on_orbm = set(orb.gene.astype(str))
base = {g.strip() for g in BASE.read_text().splitlines() if g.strip()}


def n_orbm_clusters(s):
    if not isinstance(s, str) or not s.strip():
        return 0
    n = 0
    for part in s.split(";"):
        tok = part.strip().split()[0] if part.strip() else ""
        if tok in ORBM_NUMS:
            n += 1
    return n


def status_row(on_shared_flag, on_base_flag):
    if on_shared_flag:
        return "already on shared panel"
    if on_base_flag:
        return "FREE on Xenium base (not curated yet)"
    return "not on panel (would cost a slot)"


def load_deg(name, path):
    d = pd.read_csv(path)
    d["list"] = name
    d["n_ORBm_DE_clusters"] = d["DE_clusters"].map(n_orbm_clusters)
    d["on_shared_panel"] = d["gene"].isin(on_shared)
    d["on_ORBm_ORDER"] = d["gene"].isin(on_orbm)
    d["on_xenium_base"] = d["gene"].isin(base)
    d["status"] = [
        status_row(a, b) for a, b in zip(d["on_shared_panel"], d["on_xenium_base"])
    ]
    return d.sort_values(["n_ORBm_DE_clusters", "n_DE_clusters"], ascending=False)


ieg = load_deg("IEG_DEG", DEG / "mPFC_IEGDEGs.csv")
tf = load_deg("TF_DEG", DEG / "mPFC_TFDEGs.csv")
syn = load_deg("SynPlast_DEG", DEG / "mPFC_SynPlast.csv")
gpcr_deg = load_deg("GPCR_DEG", DEG / "mPFC_GPCRDEGs.csv")
degs = pd.concat([ieg, tf, syn, gpcr_deg], ignore_index=True)

glut = pd.read_csv(JESSE / "PL_ILA_ORB_GlutamatergicNeurons_EnrichedGPCRs.csv")
gaba = pd.read_csv(JESSE / "PL_ILA_ORB_GABAergicNeurons_EnrichedGPCRs.csv")
glut = glut.rename(
    columns={glut.columns[1]: "gene", glut.columns[2]: "n_glut_subclasses"}
)
gaba = gaba.rename(
    columns={gaba.columns[1]: "gene", gaba.columns[2]: "n_gaba_subclasses"}
)
enr = glut[["gene", "n_glut_subclasses"]].merge(
    gaba[["gene", "n_gaba_subclasses"]], on="gene", how="outer"
)
enr["n_glut_subclasses"] = enr["n_glut_subclasses"].fillna(0).astype(int)
enr["n_gaba_subclasses"] = enr["n_gaba_subclasses"].fillna(0).astype(int)
enr["n_subclass_hits"] = enr["n_glut_subclasses"] + enr["n_gaba_subclasses"]
enr["on_shared_panel"] = enr["gene"].isin(on_shared)
enr["on_ORBm_ORDER"] = enr["gene"].isin(on_orbm)
enr["on_xenium_base"] = enr["gene"].isin(base)
enr["status"] = [
    status_row(a, b) for a, b in zip(enr["on_shared_panel"], enr["on_xenium_base"])
]
enr = enr.sort_values(["n_subclass_hits", "n_glut_subclasses"], ascending=False)


def counts(df):
    u = df.drop_duplicates("gene")
    return {
        "n_genes": int(u.gene.nunique()),
        "already_on_shared": int(u.on_shared_panel.sum()),
        "free_on_base_not_on_panel": int((~u.on_shared_panel & u.on_xenium_base).sum()),
        "would_cost_slot": int((~u.on_shared_panel & ~u.on_xenium_base).sum()),
    }


sum_rows = []
for name, df in [
    ("IEG_DEG", ieg),
    ("TF_DEG", tf),
    ("SynPlast_DEG", syn),
    ("GPCR_DEG", gpcr_deg),
    ("Enriched_GPCR_PL_ILA_ORB", enr),
]:
    c = counts(df)
    c["list"] = name
    sum_rows.append(c)
summary = pd.DataFrame(sum_rows)[
    ["list", "n_genes", "already_on_shared", "free_on_base_not_on_panel", "would_cost_slot"]
]

rec_deg = degs[(~degs.on_shared_panel) & (degs.n_ORBm_DE_clusters >= 3)]
rec_gpcr = enr[(~enr.on_shared_panel) & (enr.n_subclass_hits >= 5)]

seen = set()
top = []
for _, r in rec_deg.sort_values("n_ORBm_DE_clusters", ascending=False).iterrows():
    if r.gene in seen:
        continue
    seen.add(r.gene)
    top.append(
        {
            "gene": r.gene,
            "source": r.list,
            "why_jesse": f"DE in {int(r.n_ORBm_DE_clusters)} ORBm-relevant clusters ({r.direction})",
            "n_ORBm_DE_clusters": int(r.n_ORBm_DE_clusters),
            "direction": r.direction,
            "on_xenium_base": "yes" if r.on_xenium_base else "no",
            "slot_cost": "FREE" if r.on_xenium_base else "1 custom slot",
            "priority": 1 if (r.on_xenium_base or r.n_ORBm_DE_clusters >= 6) else 2,
        }
    )
for _, r in rec_gpcr.iterrows():
    if r.gene in seen:
        continue
    seen.add(r.gene)
    top.append(
        {
            "gene": r.gene,
            "source": "Enriched_GPCR",
            "why_jesse": (
                f"enriched in {int(r.n_subclass_hits)} PL-ILA-ORB subclasses "
                f"(glut {int(r.n_glut_subclasses)}, gaba {int(r.n_gaba_subclasses)})"
            ),
            "n_ORBm_DE_clusters": "",
            "direction": "",
            "on_xenium_base": "yes" if r.on_xenium_base else "no",
            "slot_cost": "FREE" if r.on_xenium_base else "1 custom slot",
            "priority": 1 if (r.on_xenium_base or r.n_subclass_hits >= 8) else 2,
        }
    )
rec = pd.DataFrame(top).sort_values(["priority", "slot_cost", "gene"])

readme = pd.DataFrame(
    [
        (
            "What Jesse sent",
            "Opioid-dependence DEGs (5 days escalating morphine) in PL-ILA-ORB: IEG, TF, "
            "synaptic plasticity, GPCR. Plus GPCRs enriched in PL-ILA-ORB vs the rest of "
            "the 4M-cell Allen atlas.",
        ),
        (
            "Vs our current shared panel",
            "Core TRAP/activity genes Fos, Arc, Egr1, Junb, Nr4a1 and several GPCRs "
            "(Oprm1, Ntsr1, Grm5, Htr1b, Chrm2) are already on SHARED_PANEL_ORDER. "
            "See SUMMARY for overlap counts per list.",
        ),
        (
            "What is new and worth considering",
            "See RECOMMEND_add. Highest-value missing DEGs that hit many ORBm subclasses: "
            "Per2, Pcsk1, Nr4a3, Per1, Dusp1, Vgf, Camk2g, Hrh1, Grm2. Highest-value "
            "missing enriched GPCRs: Mas1, Rxfp1, Gpr68, Mchr1, Grm8, Chrm1, Gpr26, "
            "Cckbr, Gpr12, Adra1a.",
        ),
        (
            "Free vs slot",
            "Genes already on the Xenium Mouse Brain v1 base panel are FREE. Everything "
            "else costs a custom slot (cap already full, plus 14 GSE283418 extras). "
            "Prefer FREE first.",
        ),
        (
            "Do we have to change the order list?",
            "Not required for cell-type ID or the TRAP tag. Jesse lists are better for "
            "the morphine-dependence signature (what changes after 5 days morphine). "
            "Add only if that state signature is a primary Xenium readout.",
        ),
    ],
    columns=["item", "detail"],
)

with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    readme.to_excel(w, sheet_name="READ_ME", index=False)
    summary.to_excel(w, sheet_name="SUMMARY", index=False)
    rec.to_excel(w, sheet_name="RECOMMEND_add", index=False)
    degs.to_excel(w, sheet_name="all_DEGs", index=False)
    enr.to_excel(w, sheet_name="enriched_GPCRs", index=False)

shutil.copy2(OUT, DL)
print(summary.to_string(index=False))
print()
print("RECOMMEND n", len(rec))
print(rec.head(30).to_string(index=False))
print("wrote", OUT)
print("wrote", DL)
