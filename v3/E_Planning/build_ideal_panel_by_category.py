"""Ideal ORBm+BMAp Xenium panel, organised by the six scientific jobs.

A gene is admitted only if it (i) serves one of those jobs for ORBm or BMAp
and (ii) is detectable in Allen WMB-10X at the 20 anchors, with three
exceptions the threshold cannot see: TRAP tags, IEGs (atlas is resting tissue),
and unique separators / named SOW receptors (Htr2a, Adrb1, Oprk1, Drd2, Mc4r).

Sources: Allen WMB-10X (Yao 2023), Hochgerner 2023, Lui 2021, Pitts 2024,
Jesse Niehaus 5-day morphine DESeq2, Berg/Scherrer GSE283418, UA UNC SOW2.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
SRC197 = OUT / "FINAL_Xenium_panel_ORBm_BMAp_standalone_197genes.xlsx"
DST = OUT / "FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx"
DST_DL = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_IDEAL_by_category.xlsx")
DET = OUT / "allen_detectability_all_candidates.xlsx"
GW = OUT / "allen_genomewide"
RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"
JESSE = V3 / "inputs" / "Jesse_ORB" / "OpioidDependenceDEG_genesets_forHansol090926"

BAR = 50.0
HOLD_MIN = 20.0

# --- scientific sets (primary membership is assigned later) -----------------
TRAP = ["iCre", "tdTomato"]

IEG = [
    "Fos", "Fosb", "Fosl2", "Junb", "Jun", "Arc", "Npas4",
    "Egr1", "Egr3", "Egr4",
    "Nr4a1", "Nr4a2", "Nr4a3",
    "Per1", "Per2",
    "Dusp1", "Dusp4", "Dusp5", "Crem",
]

GPCR = [
    # SOW
    "Htr2a", "Adrb1",
    # opioid / dopamine / melanocortin
    "Oprm1", "Oprk1", "Oprd1", "Oprl1", "Drd1", "Drd2", "Mc4r",
    # Jesse ORB-enriched and actually abundant
    "Chrm1", "Grm8", "Gpr26", "Cckbr",
    # Jesse morphine GPCR DEGs (n_DE >= 2) that survive detection
    "Hrh1", "Hrh3", "Grm5", "Grm2", "Chrm2", "Htr1b", "Htr2c",
    "Adra1a", "Adra1b", "Gpr22", "Chrm3",
    # Allen / published / Dan druggable map in ORBm or BMAp
    "Grm1", "Gabbr1", "Cnr1", "Npy1r", "Npy2r", "Sstr2",
    "Crhr1", "Tacr1", "Oxtr", "Gpr101", "Gpr88", "Adcyap1r1",
    "Htr1f", "Hcrtr2", "Calcrl",
]

PLASTICITY = [
    "Gria1", "Gria2", "Grin1", "Grin2a", "Grin2b",
    "Camk2a", "Camk2g", "Dlg4", "Homer1", "Ntrk2", "Bdnf",
    "Cbln1", "Cbln2", "Nptx2", "Ppp1r1b", "Rgs4", "Rgs9",
    "Fxr1", "Vps13a", "Vgf", "Lrrtm2", "Creb1",
]

TF_IDENTITY = [
    "Satb2", "Fezf2", "Foxp2", "Cux2", "Rorb", "Tbr1", "Bcl11b", "Tle4",
    "Etv1", "Sox5", "Pou3f1", "Isl1", "Dlx1", "Lhx6", "Sox6", "Sp9",
    "Otp", "Zic2", "Zic1", "Meis2", "Foxp1", "Neurod2", "Neurod6",
    "Bhlhe22", "Prox1", "Ebf1", "Skor1", "Nfib", "Nr2e1", "Tcf7l2",
    "Fezf1", "Sim1",
]
TF_MORPHINE = ["Arid5b", "Banp", "Klf10", "Bhlhe40", "Chd2"]  # n_orbm >= 4, interpretable

BACKBONE = [
    "Snap25", "Rbfox3", "Syt1", "Slc17a7", "Slc17a6",
    "Gad1", "Gad2", "Slc32a1", "Mbp",
]

PUBLISHED_IDENTITY = [
    # Lui 2021 OFC/PFC
    "Otof", "Pld5", "Npr3", "Tshz2", "Rbp4", "Cux2", "Rorb",
    # Hochgerner 2023 posterior BMA / MEA boundary
    "Cartpt", "Mpped1", "Calb1", "Calb2", "Fezf1", "Synpr", "Scn5a",
    "Crh", "Tac1", "Ptpru",
]

MORPHINE_STATE = ["Pcsk1", "Sema3e", "Tiparp"]  # not already IEG / TF / plasticity / GPCR
L5IT = ["Maf", "Ptpru", "Rai14", "Sema5a", "Sema5b", "Thsd7b"]  # pairwise L5 IT hole-closers

# 197 genes that are morphine-DEG dump, not a load-bearing identity/GPCR/IEG/plasticity gene
DROP_UNINTERPRETABLE = {
    "Maml3", "Hunk", "Zfp46", "Zfp641", "Etv5", "Omg", "Sox8", "Stk40",
    "Zkscan16", "Mbnl2", "Kitl", "Acsl4", "Ahctf1", "E2f6", "Ep300",
    "Fhl2", "Hivep1", "Hsd17b12", "Hspa5", "Smad5", "Zdbf2", "Zfp933",
    "Zhx2", "Zkscan2",
    "Gabbr2",  # GABA-B heterodimer; Gabbr1 is the ligand-binding subunit
}

CAT_ORDER = [
    "1_cell_type_marker",
    "2_GPCR",
    "3_plasticity",
    "4_TF",
    "5_TRAP_reporter",
    "6_IEG",
    "7_morphine_ORBm_BMAp",
]

HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
THIN = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)
WRAP = Alignment(wrap_text=True, vertical="top")


def genomewide_pct(genes_wanted, anchors_roi):
    acc, axis = {}, None
    for f in sorted(GW.glob("*.npz")):
        z = np.load(f, allow_pickle=True)
        if axis is None:
            axis = [str(x) for x in z["genes"]]
        roi = "sAMY" if "STR" in str(z["shard"][0]) else "PL-ILA-ORB"
        for i, lab in enumerate([str(x) for x in z["subclass_labels"]]):
            k = (lab, roi)
            if k not in acc:
                acc[k] = [np.zeros(len(axis)), 0]
            acc[k][0] += z["subclass_nnz"][i]
            acc[k][1] += int(z["subclass_n"][i])
    gi = {g: i for i, g in enumerate(axis)}
    out = {}
    for g in genes_wanted:
        j = gi.get(g)
        if j is None:
            continue
        v = {a: acc[(a, r)][0][j] / acc[(a, r)][1] * 100
             for a, r in anchors_roi.items() if (a, r) in acc and acc[(a, r)][1] > 0}
        if v:
            b = max(v, key=v.get)
            out[g] = (float(v[b]), b, int(sum(1 for x in v.values() if x >= BAR)))
    return out


def style_header(ws):
    for c in ws[1]:
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def write_df(wb, name, df, widths):
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(list(r))
    style_header(ws)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        for c in row:
            c.alignment = WRAP
            c.border = THIN
            c.font = Font(name="Calibri", size=10)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 30
    return ws


def main() -> None:
    sh197 = pd.read_excel(SRC197, "SHARED_PANEL_ORDER")
    ac = pd.read_excel(SRC197, "ANCHOR_COVERAGE")
    det = pd.read_excel(DET, "summary").set_index("gene")
    rank = pd.read_excel(RANK, "ranking_all").set_index("gene")
    dan = pd.read_excel(DAN, "all_98_genes").set_index("gene")
    ieg_j = pd.read_csv(JESSE / "mPFC_IEGDEGs.csv")
    tf_j = pd.read_csv(JESSE / "mPFC_TFDEGs.csv")
    syn_j = pd.read_csv(JESSE / "mPFC_SynPlast.csv")
    gp_j = pd.read_csv(JESSE / "mPFC_GPCRDEGs.csv")

    roi_of = {r.allen_subclass_anchor: ("PL-ILA-ORB" if r.region == "ORBm" else "sAMY")
              for r in ac.itertuples()}
    sep = set()
    sep_region = {}
    for r in ac.itertuples():
        for g in str(r.unique_separators_on_shared_panel or "").split(","):
            g = g.strip()
            if not g:
                continue
            sep.add(g)
            sep_region.setdefault(g, set()).add(r.region)

    on197 = set(sh197.gene.astype(str))

    # Dan genes that are actually BMAp-informative
    dan_keep = []
    for g, r in dan.iterrows():
        if pd.isna(r.max_spec) or pd.isna(r.max_pct):
            continue
        if r.max_spec >= 1.0 and r.max_pct >= BAR:
            dan_keep.append(g)
    dan_keep = [g for g in dan_keep if g not in DROP_UNINTERPRETABLE]

    candidates = []
    for lst in (TRAP, IEG, GPCR, PLASTICITY, TF_IDENTITY, TF_MORPHINE,
                BACKBONE, PUBLISHED_IDENTITY, MORPHINE_STATE, L5IT, sorted(sep), dan_keep,
                ["Ccdc42",
                 "Nxph4", "Syt6", "Lamp5", "Vip", "Sst", "Pvalb", "Ndnf",
                 "Trhr", "Ccn2", "Coch", "Cnih3", "Baiap3", "Penk", "Pdyn",
                 "Rspo2", "Trh", "Rprm", "Lratd2", "Matn2", "Krt9", "Npy",
                 "Tac2", "Col23a1", "Slc29a4", "Cck", "Gfra1", "Lamb3",
                 "Rbms3", "Pnoc", "Nos1"]):
        candidates.extend(lst)
    # keep 197 genes that are unique separators even if not listed above
    candidates.extend(g for g in on197 if g in sep)
    seen, uniq = set(), []
    for g in candidates:
        if g not in seen:
            seen.add(g)
            uniq.append(g)
    candidates = [g for g in uniq if g not in DROP_UNINTERPRETABLE]

    missing = [g for g in candidates if g not in det.index and g not in TRAP]
    gw = genomewide_pct(missing, roi_of) if missing else {}

    def pct_of(g):
        if g in TRAP:
            return (np.nan, None, np.nan)
        if g in det.index:
            return (float(det.at[g, "max_pct"]),
                    det.at[g, "max_pct_anchor"] if "max_pct_anchor" in det.columns else None,
                    det.at[g, "n_anchors_ge50"])
        if g in gw:
            return gw[g]
        return (np.nan, None, np.nan)

    def jesse_bits(g):
        bits = []
        if g in rank.index:
            r = rank.loc[g]
            bits.append(f"Jesse morphine DEG {int(r.n_orbm)}/12 ORBm {r.direction} ({r.lists})")
        return bits

    def sources_of(g):
        s = []
        if g in TRAP:
            s += ["TRAP2 x tdTomato reporter (DeNardo 2019; Madisen 2010)"]
        if g in IEG:
            s += ["IEG activity axis"]
        if g in ["Htr2a", "Adrb1", "Satb2", "Fos", "Per2", "Arc"]:
            s += ["SOW2"]
        if g in sep:
            s += ["Allen WMB unique separator of a 20-type anchor"]
        if g in BACKBONE:
            s += ["class backbone (Allen + Tasic 2018)"]
        if g in L5IT:
            s += ["Allen pairwise L5 IT separator"]
        if g in PUBLISHED_IDENTITY:
            if g in {"Otof", "Pld5", "Npr3", "Tshz2", "Rbp4", "Cux2", "Rorb"}:
                s += ["Lui 2021 Cell (OFC/PFC)"]
            else:
                s += ["Hochgerner 2023 Nat Neurosci (amygdala)"]
        if g == "Mc4r":
            s += ["Pitts 2024 OFC Mc4r"]
        if g in dan.index and g in dan_keep:
            s += [f"Dan/Scherrer GSE283418 (BMAp spec {dan.at[g,'max_spec']:.2f})"]
        if g in rank.index:
            s += ["Jesse Niehaus 5-day morphine"]
        if g in GPCR:
            s += ["GPCR map"]
        if g in PLASTICITY:
            s += ["synaptic plasticity"]
        if g in TF_IDENTITY:
            s += ["identity TF"]
        if g in TF_MORPHINE:
            s += ["Jesse morphine TF"]
        # unique, preserve order
        out, seen_s = [], set()
        for x in s:
            if x not in seen_s:
                seen_s.add(x)
                out.append(x)
        return out

    def roles_of(g):
        roles = []
        if g in TRAP:
            roles.append("TRAP reporter")
        if g in IEG:
            roles.append("IEG")
        if g in GPCR:
            roles.append("GPCR")
        if g in sep or g in BACKBONE or g in PUBLISHED_IDENTITY or g in L5IT or (g in dan_keep and g not in GPCR):
            roles.append("cell type")
        if g in TF_IDENTITY or g in TF_MORPHINE:
            roles.append("TF")
        if g in PLASTICITY:
            roles.append("plasticity")
        if g in rank.index and int(rank.at[g, "n_orbm"]) >= 3:
            roles.append("morphine")
        if g in MORPHINE_STATE:
            roles.append("morphine")
        out, seen_r = [], set()
        for x in roles:
            if x not in seen_r:
                seen_r.add(x)
                out.append(x)
        return out

    def primary_of(g, roles):
        # one primary block, matching the user's numbered list
        if "TRAP reporter" in roles:
            return "5_TRAP_reporter"
        if "GPCR" in roles:
            return "2_GPCR"
        if "IEG" in roles:
            return "6_IEG"
        if "cell type" in roles:
            return "1_cell_type_marker"
        if "TF" in roles:
            return "4_TF"
        if "plasticity" in roles:
            return "3_plasticity"
        if "morphine" in roles:
            return "7_morphine_ORBm_BMAp"
        return "1_cell_type_marker"

    def region_of(g, roles):
        regs = set()
        if g in sep_region:
            regs |= sep_region[g]
        if g in TRAP or g in IEG or g in PLASTICITY or g in BACKBONE:
            regs |= {"ORBm", "BMAp"}
        if g in GPCR and g not in {"Gpr88", "Gpr101", "Calcrl", "Oxtr"}:
            regs |= {"ORBm", "BMAp"}
        if g in {"Gpr88", "Gpr101", "Calcrl", "Oxtr", "Fezf1", "Cartpt", "Mpped1",
                 "Calb1", "Calb2", "Synpr", "Scn5a", "Crh", "Ccdc42", "Otp",
                 "Zic2", "Skor1", "Lhx6", "Sp9", "Sox6", "Ebf1", "Pdyn",
                 "Col23a1", "Slc29a4", "Cck", "Gfra1", "Pnoc", "Oprl1"}:
            regs.add("BMAp")
        if g in rank.index or g in TF_MORPHINE or g in {"Otof", "Pld5", "Npr3",
                                                        "Tshz2", "Rbp4", "Cux2",
                                                        "Rorb", "Satb2", "Fezf2",
                                                        "Chrm1", "Grm8", "Gpr26"}:
            regs.add("ORBm")
        if g in dan_keep:
            regs.add("BMAp")
        if not regs:
            regs |= {"ORBm", "BMAp"}
        if regs == {"ORBm", "BMAp"}:
            return "both"
        return sorted(regs)[0]

    def fate_of(g, pct, n50, roles):
        if g in TRAP:
            return "KEEP", "TRAP tag — not a mouse gene; Allen % does not apply"
        if pd.isna(pct):
            if g == "Adrb1":
                return "HOLD", "SOW β1 receptor; score missing — keep and drop only if <20% after scoring"
            return "CUT", "no Allen detection score"
        if pct >= BAR:
            return "KEEP", f"max_pct {pct:.0f}% (>=50% in {0 if pd.isna(n50) else int(n50)} of 20 anchors)"
        if "IEG" in roles:
            return "KEEP", f"IEG exception ({pct:.0f}% in resting atlas; induced in activated cells)"
        if g in sep:
            return "KEEP", f"unique separator of a 20-type anchor ({pct:.0f}%)"
        if g in {"Oprk1", "Drd2", "Mc4r", "Adrb1", "Htr2a"}:
            if pct >= HOLD_MIN:
                return "KEEP", f"SOW / central opioid-axis receptor ({pct:.0f}%; below 50% but load-bearing)"
            return "CUT", f"SOW receptor but empty map ({pct:.0f}%)"
        if pct < HOLD_MIN:
            return "CUT", f"empty map: max_pct {pct:.0f}%"
        return "CUT", f"max_pct {pct:.0f}% and not a separator, IEG, or SOW receptor"

    why_primary = {
        "1_cell_type_marker": "Calls one of the 20 ORBm/BMAp types, or the glut/GABA/neuron class.",
        "2_GPCR": "Druggable receptor on ORBm/BMAp types (SOW IT/CT GPCRs, opioid, Jesse ORB, Allen/Dan).",
        "3_plasticity": "Synaptic / AMPA / NMDA / CaMK / BDNF axis in the same cells.",
        "4_TF": "Identity TF for a 20-type call, or a broad morphine-state TF.",
        "5_TRAP_reporter": "Reads the TRAP2 x tdTomato tag.",
        "6_IEG": "Activity at the tagging window (Fos driver + independent IEG axes + Jesse morphine IEGs).",
        "7_morphine_ORBm_BMAp": "Morphine-dependence state in ORBm (Jesse) that is not already an IEG/TF/GPCR.",
    }

    rows = []
    for g in candidates:
        pct, anchor, n50 = pct_of(g)
        roles = roles_of(g)
        if not roles:
            continue
        prim = primary_of(g, roles)
        fate, reason = fate_of(g, pct, n50, roles)
        src = sources_of(g)
        rows.append({
            "gene": g,
            "primary": prim,
            "roles": " + ".join(roles),
            "region": region_of(g, roles),
            "allen_max_pct": None if pd.isna(pct) else round(float(pct), 1),
            "n_anchors_ge50": None if pd.isna(n50) else int(n50),
            "max_pct_anchor": anchor,
            "fate": fate,
            "reason": reason,
            "sources": "; ".join(src),
            "jesse_n_orbm": int(rank.at[g, "n_orbm"]) if g in rank.index else None,
            "jesse_lists": rank.at[g, "lists"] if g in rank.index else None,
            "dan_spec": round(float(dan.at[g, "max_spec"]), 2) if g in dan.index and pd.notna(dan.at[g, "max_spec"]) else None,
            "on_197": g in on197,
        })
    t = pd.DataFrame(rows)

    keep = t[t.fate.isin(["KEEP", "HOLD"])].copy()
    # Dan-only leftovers that failed spec: drop if not separator/GPCR/IEG/TF/plasticity/TRAP
    drop_dan = []
    for g in ["Nos1", "Lamb3", "Rbms3"]:
        if g in keep.gene.values:
            r = keep[keep.gene == g].iloc[0]
            spec = r.dan_spec
            if (spec is None or spec < 1.0) and "cell type" in str(r.roles) and r.primary == "1_cell_type_marker":
                if g not in sep:
                    drop_dan.append(g)
    keep = keep[~keep.gene.isin(drop_dan)].copy()
    cut = t[~t.gene.isin(set(keep.gene))].copy()

    # rebuild primary after GPCR/IEG preference, then sort
    cat_rank = {c: i for i, c in enumerate(CAT_ORDER)}
    keep["cat_i"] = keep.primary.map(cat_rank)
    keep = keep.sort_values(["cat_i", "region", "gene"]).reset_index(drop=True)
    keep["order_rank"] = np.arange(1, len(keep) + 1)

    def serves(r):
        bits = [why_primary[r.primary]]
        if r.roles != r.primary.replace("1_", "").replace("2_", "").replace("3_", "") \
                .replace("4_", "").replace("5_", "").replace("6_", "").replace("7_", ""):
            bits.append("Also: " + r.roles)
        if pd.notna(r.jesse_n_orbm):
            bits.append(f"Jesse {int(r.jesse_n_orbm)}/12 ORBm.")
        if pd.notna(r.dan_spec):
            bits.append(f"Dan BMAp spec {r.dan_spec}.")
        return " ".join(bits)

    keep["block"] = keep.primary
    keep["serves"] = keep.apply(serves, axis=1)
    keep["why"] = keep.apply(
        lambda r: f"{r.reason} Sources: {r.sources}", axis=1)

    # SHARED columns matching prior order sheets, plus QC fields
    shared = keep[["order_rank", "gene", "block", "serves", "why",
                   "region", "allen_max_pct", "n_anchors_ge50", "roles",
                   "sources", "jesse_n_orbm", "dan_spec"]].copy()

    orb = shared[shared.region.isin(["ORBm", "both"])].copy().reset_index(drop=True)
    orb["order_rank"] = np.arange(1, len(orb) + 1)
    bma = shared[shared.region.isin(["BMAp", "both"])].copy().reset_index(drop=True)
    bma["order_rank"] = np.arange(1, len(bma) + 1)

    # BY_CATEGORY: one row per role
    cat_rows = []
    role_to_cat = {
        "cell type": "1_cell_type_marker",
        "GPCR": "2_GPCR",
        "plasticity": "3_plasticity",
        "TF": "4_TF",
        "TRAP reporter": "5_TRAP_reporter",
        "IEG": "6_IEG",
        "morphine": "7_morphine_ORBm_BMAp",
    }
    for r in keep.itertuples():
        for role in str(r.roles).split(" + "):
            cat_rows.append({
                "category": role_to_cat.get(role, r.primary),
                "role": role,
                "gene": r.gene,
                "primary_block": r.primary,
                "is_primary": role_to_cat.get(role, r.primary) == r.primary,
                "region": r.region,
                "allen_max_pct": r.allen_max_pct,
                "sources": r.sources,
            })
    bycat = pd.DataFrame(cat_rows).sort_values(["category", "gene"])

    vs = pd.DataFrame({
        "gene": sorted(on197 | set(keep.gene)),
    })
    vs["on_197"] = vs.gene.isin(on197)
    vs["on_ideal"] = vs.gene.isin(set(keep.gene))
    vs["change"] = np.where(vs.on_197 & vs.on_ideal, "stay",
                            np.where(vs.on_ideal, "ADD", "DROP"))
    vs = vs.merge(t[["gene", "primary", "roles", "allen_max_pct", "reason"]],
                  on="gene", how="left")
    vs = vs.sort_values(["change", "gene"])

    add = keep[~keep.on_197][["gene", "primary", "roles", "allen_max_pct",
                              "reason", "sources"]]
    drop = pd.DataFrame({"gene": sorted(on197 - set(keep.gene))})
    drop = drop.merge(t[["gene", "primary", "roles", "allen_max_pct", "reason"]],
                      on="gene", how="left")
    # drops that were never in `t` (uninterpretable list)
    for g in sorted(on197 - set(keep.gene) - set(drop.gene.dropna())):
        pass
    missing_drop = sorted((on197 - set(keep.gene)) - set(t.gene))
    if missing_drop:
        extra = pd.DataFrame({
            "gene": missing_drop,
            "primary": "uninterpretable_morphine_DEG",
            "roles": "dropped",
            "allen_max_pct": [float(det.at[g, "max_pct"]) if g in det.index else None
                              for g in missing_drop],
            "reason": "Jesse DEG dump: not an IEG, identity TF, GPCR, plasticity gene, or unique separator",
        })
        drop = pd.concat([drop, extra], ignore_index=True)
    drop = drop[drop.gene.isin(on197 - set(keep.gene))].drop_duplicates("gene")

    low = keep[keep.allen_max_pct.notna() & (keep.allen_max_pct < BAR)][
        ["gene", "primary", "allen_max_pct", "reason", "roles"]]

    # counts
    n = len(keep)
    print(f"IDEAL {n} genes")
    print(keep.primary.value_counts().reindex(CAT_ORDER).to_string())
    print("ADD", sorted(add.gene))
    print("DROP n", len(drop), sorted(drop.gene)[:40], "..." if len(drop) > 40 else "")
    print("HOLD", keep[keep.fate == "HOLD"].gene.tolist())
    print("below 50 kept", low.gene.tolist())
    print("separators retained", len(sep & set(keep.gene)), "/", len(sep))
    lost = sep - set(keep.gene)
    print("separators lost", lost)
    def _show(g):
        sub = keep[keep.gene == g][["allen_max_pct", "fate"]]
        return sub.to_string(index=False) if len(sub) else f"{g} NOT KEPT"
    print("Adrb1", _show("Adrb1"))
    print("Creb1", _show("Creb1"))
    print("Grm2", _show("Grm2"))
    print("Vgf", _show("Vgf"))

    assert not lost, lost
    assert keep.gene.duplicated().sum() == 0
    assert list(keep.order_rank) == list(range(1, n + 1))

    # --- workbook
    wb = Workbook()
    # READ_ME
    ws = wb.active
    ws.title = "READ_ME"
    lines = [
        ("Ideal ORBm + BMAp Xenium panel",
         f"{n} genes. Standalone custom. Organised by the six jobs this experiment has to do."),
        ("1. Cell-type markers",
         "Unique Allen separators of the 20 ORBm/BMAp anchors, glut/GABA/neuron backbone, "
         "Lui OFC identity genes, Hochgerner posterior-BMA identity genes, Dan GSE283418 genes "
         "with BMAp specificity ≥1.0 and detection ≥50%."),
        ("2. GPCRs",
         "SOW Htr2a and Adrb1 (IT/CT class), mu/kappa/delta/NOP opioid receptors, Jesse ORB-enriched "
         "receptors that Allen actually detects (Chrm1, Grm8, Gpr26, Cckbr), Jesse morphine GPCR DEGs "
         "with n_DE≥2 that pass detection, plus the Allen/Dan druggable map on these types. "
         "Empty-map GPCRs (Sstr4, Gpr63, Htr6, Vipr2, Mas1, Mchr1, Rxfp1) are out."),
        ("3. Neuron plasticity",
         "AMPA GluA1/GluA2, NMDA Grin1/2a/2b, CaMKII, PSD-95, Homer1, TrkB, BDNF, cerebellins, "
         "Jesse synaptic-plasticity DEGs Fxr1/Vps13a/Vgf/Lrrtm2, and Creb1 (SOW pCREB axis). "
         "GluA1/GluA2 and NR2A/NR2B are kept as pairs because the subunit ratio is the plasticity readout."),
        ("4. Transcription factors",
         "Identity TFs that call the 20 types (Satb2, Fezf2, Foxp2, Cux2, Rorb, Otp, …) plus the "
         "interpretable morphine-state TFs with ≥4/12 ORBm anchors (Arid5b, Banp, Klf10, Bhlhe40, Chd2). "
         "Zinc-finger DEG dump (Zfp46, Zkscan*, …) is out — those are not a TF map."),
        ("5. TRAP reporter",
         "tdTomato (permanent tag) and iCre (TRAP2 driver transcript). No WPRE/mCherry (no AAV)."),
        ("6. IEGs",
         "Fos (driver locus), Arc, Npas4, Fosb, Junb/Jun, Egr1/3/4, Nr4a1/2/3, Per1/Per2, Dusp1/4/5, Crem, Fosl2. "
         "Low resting-atlas % is expected and is not a reason to drop them."),
        ("7. Morphine-related, ORBm/BMAp-specific",
         "Jesse DEGs that report morphine state and are not already an IEG/TF/GPCR/plasticity gene: "
         "Pcsk1, Sema3e, Tiparp. Per2/Camk2g/Bhlhe40/Hrh1 still sit on the panel under IEG/plasticity/TF/GPCR "
         "with morphine as a secondary role (see BY_CATEGORY)."),
        ("Detection rule",
         "Drop if Allen max % of cells in the 20 anchors is <50%, unless IEG, TRAP, unique separator, "
         "or a named SOW/opioid-axis receptor at ≥20% (Oprk1, Drd2, Mc4r, Adrb1). "
         "This is the same rule that cut 246 → 197; the ideal panel also drops genes that pass 50% "
         "but do not serve one of the six jobs (uninterpretable morphine TFs, redundant Gabbr2, "
         "Dan leftovers with spec<1)."),
        ("What this is not",
         "Not ULTIMATE (96-supertype genome-wide screen). Not the 100-slot add-on. "
         "Not all 304 Jesse DEGs. Every remaining gene is there because it answers a named question "
         "in ORBm or BMAp and the instrument will see it."),
    ]
    ws.append(["item", "detail"])
    for a, b in lines:
        ws.append([a, b])
    style_header(ws)
    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 110
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for c in row:
            c.alignment = WRAP
        ws.row_dimensions[row[0].row].height = 48
    ws.row_dimensions[1].height = 22

    write_df(wb, "SHARED_PANEL_ORDER", shared,
             [12, 14, 24, 70, 80, 10, 14, 16, 28, 70, 14, 12])
    write_df(wb, "ORBm_ORDER", orb,
             [12, 14, 24, 70, 80, 10, 14, 16, 28, 70, 14, 12])
    write_df(wb, "BMAp_ORDER", bma,
             [12, 14, 24, 70, 80, 10, 14, 16, 28, 70, 14, 12])
    write_df(wb, "BY_CATEGORY", bycat,
             [24, 16, 14, 24, 12, 10, 14, 70])
    # ANCHOR_COVERAGE copy
    write_df(wb, "ANCHOR_COVERAGE", ac, [10, 36, 36, 12, 40, 40])
    write_df(wb, "DETECTION", keep[["order_rank", "gene", "primary", "allen_max_pct",
                                    "n_anchors_ge50", "fate", "reason"]],
             [12, 14, 24, 14, 16, 8, 70])
    write_df(wb, "BY_CATEGORY_COUNTS",
             bycat.groupby("category").gene.nunique().rename("n_genes").reset_index(),
             [28, 12])
    write_df(wb, "vs_197", vs, [14, 10, 10, 10, 24, 28, 14, 70])
    write_df(wb, "ADD_LIST", add, [14, 24, 28, 14, 50, 70])
    write_df(wb, "DROP_FROM_197", drop, [14, 28, 20, 14, 70])
    write_df(wb, "KEEP_BELOW_50", low, [14, 24, 14, 70, 28])

    fg = wb.create_sheet("FOR_MarkGreg")
    fg.append(["item", "detail"])
    style_header(fg)
    notes = [
        (f"Ideal panel: {n} genes by scientific job, not by 246-block leftovers",
         f"Cell type {int((keep.primary=='1_cell_type_marker').sum())}, "
         f"GPCR {int((keep.primary=='2_GPCR').sum())}, "
         f"plasticity {int((keep.primary=='3_plasticity').sum())}, "
         f"TF {int((keep.primary=='4_TF').sum())}, "
         f"TRAP {int((keep.primary=='5_TRAP_reporter').sum())}, "
         f"IEG {int((keep.primary=='6_IEG').sum())}, "
         f"morphine-state remainder {int((keep.primary=='7_morphine_ORBm_BMAp').sum())}. "
         f"A gene can serve more than one job; BY_CATEGORY lists every role. "
         f"All {len(sep)} unique separators of the 20 types remain, so 20/20 are still separable."),
        (f"{len(add)} genes added vs detectability-pruned 197",
         "Added because they serve a named job and pass detection (or are IEG/SOW): "
         + ", ".join(add.gene.astype(str)) + ". Creb1 closes the pCREB axis the SOW names. "
         "Jun / Dusp4 / Dusp5 / Fosl2 are morphine IEGs. Vgf / Lrrtm2 are Jesse synaptic-plasticity DEGs. "
         "Syt1 is the pan-neuronal backup. Grm2 is a Jesse morphine GPCR DEG that Allen actually sees."),
        (f"{len(drop)} genes dropped from 197 even though they passed 50%",
         "They do not serve the six jobs: zinc-finger / generic TF DEG dump, metabolic Jesse DEGs "
         "(Acsl4, Hsd17b12, Hspa5, Kitl, …), Notch cofactor Maml3, redundant Gabbr2 (Gabbr1 stays), "
         "Dan leftovers with BMAp spec<1 (Nos1). Passing the detection bar is necessary, not sufficient."),
        ("Empty-map custom probes stay out",
         "Sstr4 1%, Gpr63 3%, Htr6 5%, Vipr2 8%, C1ql2 10%, Vdr 11%, Th/Chat/Slc6a3. "
         "Those were the 246 problem. This file does not put them back."),
        ("Adrb1",
         (keep.loc[keep.gene == "Adrb1", "why"].iloc[0]
          if "Adrb1" in set(keep.gene) else "not on panel")),
    ]
    for a, b in notes:
        fg.append([a, b])
    fg.column_dimensions["A"].width = 44
    fg.column_dimensions["B"].width = 110
    for row in fg.iter_rows(min_row=2, max_row=fg.max_row):
        for c in row:
            c.alignment = WRAP
        fg.row_dimensions[row[0].row].height = 64

    # move READ_ME first already; order sheets after
    order = ["READ_ME", "FOR_MarkGreg", "SHARED_PANEL_ORDER", "ORBm_ORDER", "BMAp_ORDER",
             "BY_CATEGORY", "BY_CATEGORY_COUNTS", "ANCHOR_COVERAGE", "DETECTION",
             "KEEP_BELOW_50", "ADD_LIST", "DROP_FROM_197", "vs_197"]
    for i, name in enumerate(order):
        wb.move_sheet(name, offset=i - wb.sheetnames.index(name))

    wb.save(DST)
    shutil.copy2(DST, DST_DL)
    print("wrote", DST)
    print("wrote", DST_DL)

    # category print for the user
    print("\n=== PRIMARY ===")
    for cat in CAT_ORDER:
        genes = keep.loc[keep.primary == cat, "gene"].tolist()
        print(f"{cat} n={len(genes)}")
        print("  " + ", ".join(genes))
    print("\n=== ALL ROLES (BY_CATEGORY n unique) ===")
    print(bycat.groupby("category").gene.nunique().reindex(CAT_ORDER).to_string())


if __name__ == "__main__":
    main()
