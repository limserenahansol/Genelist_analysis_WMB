"""Export Jesse ORB gene-list figures + compact JSON for the canvas."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

V3 = Path(__file__).resolve().parents[1]
J = V3 / "inputs" / "Jesse_ORB"
DEG = J / "OpioidDependenceDEG_genesets_forHansol090926"
OUT = V3 / "outputs"
DL = Path.home() / "Downloads"
FIG = OUT / "jesse_orb_figures"
FIG.mkdir(exist_ok=True)

ORBM = {"004", "005", "006", "007", "022", "029", "030", "032", "046", "049", "052", "053"}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": False,
    }
)

UP = "#2A6F97"
DOWN = "#C44536"
MIXED = "#8C7B6B"
GLUT = "#3D5A80"
GABA = "#9A8C7A"


def n_orbm(s: object) -> int:
    if not isinstance(s, str):
        return 0
    n = 0
    for part in s.split(";"):
        tok = part.strip().split()[0] if part.strip() else ""
        if tok in ORBM:
            n += 1
    return n


def load(name: str, path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    d["list"] = name
    d["n_orbm"] = d["DE_clusters"].map(n_orbm)
    return d


ieg = load("IEG", DEG / "mPFC_IEGDEGs.csv")
tf = load("TF", DEG / "mPFC_TFDEGs.csv")
syn = load("SynPlast", DEG / "mPFC_SynPlast.csv")
gp = load("GPCR_DEG", DEG / "mPFC_GPCRDEGs.csv")
degs = pd.concat([ieg, tf, syn, gp], ignore_index=True)

glut = pd.read_csv(J / "PL_ILA_ORB_GlutamatergicNeurons_EnrichedGPCRs.csv")
gaba = pd.read_csv(J / "PL_ILA_ORB_GABAergicNeurons_EnrichedGPCRs.csv")
glut = glut.rename(columns={glut.columns[1]: "gene", glut.columns[2]: "n"})
gaba = gaba.rename(columns={gaba.columns[1]: "gene", gaba.columns[2]: "n"})


def save(fig: plt.Figure, name: str) -> None:
    dests = [FIG] + ([DL] if DL.is_dir() else [])
    for dest in dests:
        fig.savefig(dest / name, dpi=200, bbox_inches="tight")
    print("wrote", name)


# --- Fig 1: gene-set sizes + direction ---
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4))
lists = ["IEG", "TF", "SynPlast", "GPCR_DEG"]
labels = ["IEG DEG", "TF DEG", "Synaptic\nplasticity DEG", "GPCR DEG"]
sizes = [len(ieg), len(tf), len(syn), len(gp)]
axes[0].bar(labels, sizes, color=["#1D4E89", "#3D5A80", "#6B7C6A", "#8B5E3C"])
axes[0].set_ylabel("Number of genes")
axes[0].set_title("A. Morphine-dependence DEGs in PL-ILA-ORB")
for i, v in enumerate(sizes):
    axes[0].text(i, v + 3, str(v), ha="center", va="bottom", fontsize=9)
axes[0].set_ylim(0, max(sizes) * 1.15)

up, down, mixed = [], [], []
for d in (ieg, tf, syn, gp):
    up.append(int((d.direction == "Up").sum()))
    down.append(int((d.direction == "Down").sum()))
    mixed.append(int((d.direction == "Mixed").sum()))
x = np.arange(4)
w = 0.28
axes[1].bar(x - w, up, w, label="Up", color=UP)
axes[1].bar(x, down, w, label="Down", color=DOWN)
axes[1].bar(x + w, mixed, w, label="Mixed", color=MIXED)
axes[1].set_xticks(x)
axes[1].set_xticklabels(labels)
axes[1].set_ylabel("Number of genes")
axes[1].set_title("B. Direction during opioid dependence")
axes[1].legend(frameon=False)
fig.suptitle(
    "Jesse Niehaus  |  5-day escalating morphine  |  DESeq2 padj <= 0.1  |  subclass pseudobulk",
    fontsize=9,
    color="#555",
    y=1.02,
)
fig.tight_layout()
save(fig, "Jesse_Fig1_DEG_overview.png")
plt.close(fig)

# --- Fig 2: top IEG + top plasticity ---
fig, axes = plt.subplots(1, 2, figsize=(11.2, 6.2))


def hbar_dir(ax, df, title, n=16):
    d = df.sort_values("n_DE_clusters", ascending=True).tail(n)
    colors = [UP if x == "Up" else DOWN if x == "Down" else MIXED for x in d.direction]
    ax.barh(d.gene, d.n_DE_clusters, color=colors)
    ax.set_xlabel("Subclass clusters with DE (n)")
    ax.set_title(title)
    ax.legend(
        handles=[
            mpatches.Patch(color=UP, label="Up"),
            mpatches.Patch(color=DOWN, label="Down"),
            mpatches.Patch(color=MIXED, label="Mixed"),
        ],
        frameon=False,
        loc="lower right",
    )


hbar_dir(axes[0], ieg, "A. Top IEG / activity DEGs")
hbar_dir(axes[1], syn, "B. Top synaptic-plasticity DEGs")
fig.suptitle(
    "Genes ranked by number of PL-ILA-ORB subclasses with differential expression",
    fontsize=9,
    color="#555",
    y=1.01,
)
fig.tight_layout()
save(fig, "Jesse_Fig2_top_IEG_plasticity.png")
plt.close(fig)

# --- Fig 3: IEG hits per subclass ---
hits = Counter()
for s in ieg.DE_clusters:
    for part in str(s).split(";"):
        lab = part.strip()
        if lab:
            hits[lab] += 1
labs, vals = zip(*hits.most_common())
short = []
for lab in labs:
    tok = lab.split()[0]
    rest = " ".join(lab.split()[1:]).replace(" CTX", "").replace(" Glut", " glut").replace(" Gaba", " gaba")
    short.append(f"{tok} {rest}")
colors = [GABA if "gaba" in s.lower() else GLUT for s in short]
fig, ax = plt.subplots(figsize=(8.4, 6.4))
ax.barh(list(reversed(short)), list(reversed(vals)), color=list(reversed(colors)))
ax.set_xlabel("IEG DEGs detected in this subclass (count)")
ax.set_title("IEG morphine DEGs by PL-ILA-ORB subclass")
ax.legend(
    handles=[
        mpatches.Patch(color=GLUT, label="Glutamatergic"),
        mpatches.Patch(color=GABA, label="GABAergic"),
    ],
    frameon=False,
    loc="lower right",
)
fig.tight_layout()
save(fig, "Jesse_Fig3_IEG_by_subclass.png")
plt.close(fig)

# --- Fig 4: enriched GPCRs ---
gmerge = glut[["gene", "n"]].merge(gaba[["gene", "n"]], on="gene", how="outer", suffixes=("_glut", "_gaba"))
gmerge["n_glut"] = gmerge["n_glut"].fillna(0)
gmerge["n_gaba"] = gmerge["n_gaba"].fillna(0)
gmerge["tot"] = gmerge["n_glut"] + gmerge["n_gaba"]
top = gmerge.sort_values("tot").tail(18)

fig, ax = plt.subplots(figsize=(8.6, 6.6))
y = np.arange(len(top))
ax.barh(y, top.n_glut, color=GLUT, label="Enriched in Glut subclasses")
ax.barh(y, top.n_gaba, left=top.n_glut, color=GABA, label="Enriched in GABA subclasses")
ax.set_yticks(y)
ax.set_yticklabels(top.gene)
ax.set_xlabel("Number of PL-ILA-ORB subclasses with GPCR enrichment")
ax.set_title("GPCRs enriched in PL-ILA-ORB vs rest of Allen 4M-cell atlas")
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
save(fig, "Jesse_Fig4_enriched_GPCRs.png")
plt.close(fig)

# --- Fig 5: IEG x subclass presence matrix (top 20 genes) ---
top20 = ieg.sort_values("n_DE_clusters", ascending=False).head(20)
clusters = []
for s in ieg.DE_clusters:
    for part in str(s).split(";"):
        lab = part.strip()
        if lab and lab not in clusters:
            clusters.append(lab)
# keep frequent clusters
keep = [k for k, _ in hits.most_common() if hits[k] >= 3]
mat = np.zeros((len(top20), len(keep)))
for i, r in enumerate(top20.itertuples()):
    present = {p.strip() for p in str(r.DE_clusters).split(";") if p.strip()}
    for j, cl in enumerate(keep):
        mat[i, j] = 1 if cl in present else 0
cl_short = []
for lab in keep:
    tok = lab.split()[0]
    rest = " ".join(lab.split()[1:]).replace(" CTX Glut", "").replace(" Gaba", "g").replace(" IT ", " ")
    cl_short.append(f"{tok}\n{rest}")

fig, ax = plt.subplots(figsize=(10.6, 6.8))
im = ax.imshow(mat, cmap="Blues", aspect="auto", vmin=0, vmax=1)
ax.set_yticks(range(len(top20)))
ax.set_yticklabels(top20.gene.tolist())
ax.set_xticks(range(len(keep)))
ax.set_xticklabels(cl_short, fontsize=7)
ax.set_title("Top 20 IEG DEGs × subclass (filled = differentially expressed)")
ax.set_xlabel("Allen subclass in PL-ILA-ORB")
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_color("#ccc")
fig.colorbar(im, ax=ax, shrink=0.4, ticks=[0, 1], label="DE in subclass")
fig.tight_layout()
save(fig, "Jesse_Fig5_IEG_subclass_matrix.png")
plt.close(fig)

# JSON for canvas
payload = {}
for name, d in [("IEG", ieg), ("TF", tf), ("SynPlast", syn), ("GPCR_DEG", gp)]:
    payload[name] = [
        {
            "g": r.gene,
            "set": str(r.gene_set),
            "n": int(r.n_DE_clusters),
            "d": r.direction,
            "o": int(r.n_orbm),
            "c": r.DE_clusters,
        }
        for r in d.itertuples()
    ]
payload["glut"] = [{"g": r.gene, "n": int(r.n)} for r in glut.itertuples()]
payload["gaba"] = [{"g": r.gene, "n": int(r.n)} for r in gaba.itertuples()]
(OUT / "_jesse_canvas_data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
print("json", (OUT / "_jesse_canvas_data.json").stat().st_size)
print("unique DEG genes", degs.gene.nunique())
print("overlap 2+", int((degs.groupby("gene").list.nunique() >= 2).sum()))
