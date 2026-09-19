"""Rank Jesse's opioid-dependence DEGs by ORBm relevance and build the add-recommendation deck.

The earlier pass reported a four-gene "morphine layer" (Rxfp1, Per2, Pcsk1, Per1).
That undersold the data: it was picked by eye, not by breadth across the cell types
we actually image. This script ranks every Jesse gene by how many of our 12 ORBm
anchor subclasses it is DE in, crosses that with slot cost (already on panel /
free on the Xenium base panel / costs a custom slot), and emits:

  outputs/Jesse_ORB_priority_ranking.xlsx        ranking + tiered recommendation
  outputs/jesse_priority_figures/*.png           figures
  outputs/ORBm_BMAp_Jesse_priority_recommend.pptx  the deck

Inputs are repo paths only (no Downloads).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
GS = V3 / "inputs" / "Jesse_ORB" / "OpioidDependenceDEG_genesets_forHansol090926"
FIG = OUT / "jesse_priority_figures"
FIG.mkdir(exist_ok=True)

PANEL = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
PRIOR = OUT / "Jesse_ORB_vs_Xenium_panel.xlsx"

NAVY = "#1D4E89"
RUST = "#C44536"
TEAL = "#2A6F97"
TAUPE = "#8C7B6B"
SAGE = "#6B7C6A"
GOLD = "#B08968"
GREY = "#B8B2A8"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

# The 12 ORBm cell types the panel is built to separate (ANCHOR_COVERAGE).
ORBM_ANCHORS = [
    "007 L2/3 IT CTX Glut", "006 L4/5 IT CTX Glut", "005 L5 IT CTX Glut",
    "022 L5 ET CTX Glut", "032 L5 NP CTX Glut", "030 L6 CT CTX Glut",
    "029 L6b CTX Glut", "004 L6 IT CTX Glut",
    "052 Pvalb Gaba", "053 Sst Gaba", "046 Vip Gaba", "049 Lamp5 Gaba",
]
GLUT = {c for c in ORBM_ANCHORS if c.endswith("Glut")}
GABA = {c for c in ORBM_ANCHORS if c.endswith("Gaba")}

LISTS = {
    "mPFC_IEGDEGs.csv": "IEG",
    "mPFC_TFDEGs.csv": "TF",
    "mPFC_SynPlast.csv": "SynPlast",
    "mPFC_GPCRDEGs.csv": "GPCR",
}


def load_ranking() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    for fname, label in LISTS.items():
        d = pd.read_csv(GS / fname)
        d["list"] = label
        frames.append(d)
    raw = pd.concat(frames, ignore_index=True)

    raw["clusters"] = raw.DE_clusters.fillna("").apply(
        lambda s: [c.strip() for c in s.split(";") if c.strip()]
    )
    raw["orbm"] = raw.clusters.apply(lambda cs: [c for c in cs if c in ORBM_ANCHORS])
    raw["n_orbm"] = raw.orbm.apply(len)
    raw["n_glut"] = raw.orbm.apply(lambda cs: len(set(cs) & GLUT))
    raw["n_gaba"] = raw.orbm.apply(lambda cs: len(set(cs) & GABA))

    gene = raw.groupby("gene").agg(
        lists=("list", lambda s: "+".join(sorted(set(s)))),
        n_lists=("list", "nunique"),
        n_DE_clusters=("n_DE_clusters", "max"),
        n_orbm=("n_orbm", "max"),
        n_glut=("n_glut", "max"),
        n_gaba=("n_gaba", "max"),
        direction=("direction", lambda s: "Mixed" if s.nunique() > 1 else s.iloc[0]),
    ).reset_index()

    shared = set(pd.read_excel(PANEL, "SHARED_PANEL_ORDER").gene.astype(str))
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    gene["on_panel"] = gene.gene.isin(shared)
    gene["on_base"] = gene.gene.isin(base)

    egpcr = pd.read_excel(PRIOR, "enriched_GPCRs")
    gene = gene.merge(
        egpcr[["gene", "n_subclass_hits"]].rename(columns={"n_subclass_hits": "orb_gpcr_enrich"}),
        on="gene", how="left",
    )

    def cost(r):
        if r.on_panel:
            return "already on panel"
        return "FREE on base" if r.on_base else "1 custom slot"

    gene["slot_cost"] = gene.apply(cost, axis=1)

    def tier(r):
        if r.on_panel:
            return "0_already_covered"
        if r.on_base:
            return "T0_free_add_now"
        if r.n_orbm >= 8:
            return "T1_core_add"
        if r.n_orbm >= 6:
            return "T2_strong"
        if r.n_orbm >= 4 or r.n_lists >= 2:
            return "T3_optional"
        return "T4_skip"

    gene["tier"] = gene.apply(tier, axis=1)
    gene = gene.sort_values(["n_orbm", "n_lists", "n_DE_clusters"], ascending=False)
    return gene.reset_index(drop=True), egpcr


def fig_top_breadth(gene: pd.DataFrame) -> Path:
    """Top 20 genes by ORBm-anchor breadth, plus the two best free-on-base genes.

    No free-on-base gene reaches the top 20 (Bhlhe40 tops them at 4 anchors), so
    they are appended below a rule rather than left out — otherwise the teal
    legend entry would have no bars and the reader could not see how the
    zero-cost options compare.
    """
    top = gene.nlargest(20, ["n_orbm", "n_lists"])
    free = gene[gene.slot_cost == "FREE on base"].nlargest(2, "n_orbm")
    # barh draws index 0 at the bottom, so both blocks go in ascending order:
    # the free genes sit below the rule and rank 1 (Per2) ends up at the top.
    d = pd.concat([free.iloc[::-1], top.iloc[::-1]]).reset_index(drop=True)
    colours = {"already on panel": SAGE, "FREE on base": TEAL, "1 custom slot": RUST}
    fig, ax = plt.subplots(figsize=(9.4, 6.4))
    y = np.arange(len(d))
    ax.barh(y, d.n_orbm, color=[colours[c] for c in d.slot_cost], height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(
        [f"{g}  ({l})" for g, l in zip(d.gene, d.lists)], fontsize=9
    )
    for i, (n, dr) in enumerate(zip(d.n_orbm, d.direction)):
        ax.text(n + 0.12, i, f"{n}  {dr}", va="center", fontsize=8.5, color="#4A4A4A")
    ax.axhline(len(free) - 0.5, color="#8A8A8A", lw=1.0, ls=(0, (4, 3)))
    # Left of centre: the rule's right side is where the legend sits.
    ax.text(5.4, len(free) - 0.78, "zero-cost options, for scale",
            va="top", ha="left", fontsize=8, color="#6A6A6A", style="italic")
    ax.set_xlim(0, 13.2)
    ax.set_xlabel("ORBm anchor cell types with significant DE  (out of 12)")
    ax.set_title(
        "Jesse opioid-dependence DEGs ranked by breadth across OUR ORBm cell types",
        fontsize=11.5, color=NAVY, pad=12,
    )
    handles = [plt.Rectangle((0, 0), 1, 1, color=v) for v in colours.values()]
    ax.legend(handles, colours.keys(), fontsize=8.5, loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    p = FIG / "top_breadth.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig_coverage(gene: pd.DataFrame) -> Path:
    """Per-list panel coverage, stacked."""
    rows = []
    for fname, label in LISTS.items():
        g = pd.read_csv(GS / fname).gene.astype(str)
        sub = gene[gene.gene.isin(set(g))]
        rows.append({
            "list": f"{label}\n(n={len(set(g))})",
            "on_panel": int(sub.on_panel.sum()),
            "free": int((~sub.on_panel & sub.on_base).sum()),
            "slot": int((~sub.on_panel & ~sub.on_base).sum()),
        })
    d = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8.6, 4.5))
    x = np.arange(len(d))
    ax.bar(x, d.on_panel, color=SAGE, label="already on panel", width=0.62)
    ax.bar(x, d.free, bottom=d.on_panel, color=TEAL, label="FREE on base (not added)", width=0.62)
    ax.bar(x, d.slot, bottom=d.on_panel + d.free, color=GREY, label="off panel, costs a slot", width=0.62)
    for i, r in d.iterrows():
        ax.text(i, r.on_panel / 2, str(r.on_panel), ha="center", va="center",
                color="white", fontsize=10, fontweight="bold")
        tot = r.on_panel + r.free + r.slot
        ax.text(i, tot + 2.5, f"{r.on_panel}/{tot}", ha="center", fontsize=9, color=NAVY)
    ax.set_xticks(x)
    ax.set_xticklabels(d.list, fontsize=9.5)
    ax.set_ylabel("genes")
    ax.set_title("How much of each Jesse list the current panel already reads",
                 fontsize=11.5, color=NAVY, pad=12)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    p = FIG / "list_coverage.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig_glut_gaba(gene: pd.DataFrame) -> Path:
    """Recommended genes: glut vs GABA breadth, shows which generalise."""
    rec = gene[gene.tier.isin(["T0_free_add_now", "T1_core_add", "T2_strong"])].copy()
    rec = rec.nlargest(14, "n_orbm")
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    y = np.arange(len(rec))[::-1]
    ax.barh(y + 0.19, rec.n_glut, height=0.36, color=NAVY, label="Glut anchors (of 8)")
    ax.barh(y - 0.19, rec.n_gaba, height=0.36, color=GOLD, label="GABA anchors (of 4)")
    ax.set_yticks(y)
    ax.set_yticklabels(rec.gene, fontsize=9.5)
    ax.set_xlabel("ORBm anchor cell types with significant DE")
    ax.set_title("Do the recommended genes work in both classes?",
                 fontsize=11.5, color=NAVY, pad=12)
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    p = FIG / "glut_vs_gaba.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


# ----------------------------------------------------------------- deck helpers
BLANK = 6

# Tier 0 is chosen by hand, not by n_orbm: every free-on-base gene ties at 1
# anchor or below, so a nlargest() tie-break would be arbitrary. Bhlhe40 and
# Sema3e lead on breadth; Rxfp1 earns its place on GPCR enrichment (19
# PL-ILA-ORB subclasses) despite 0 ORBm-anchor DE; Gadd45a is the IEG-adjacent
# TF among the remaining 1-anchor genes.
TIER0_PICK = ["Bhlhe40", "Sema3e", "Rxfp1", "Gadd45a"]


def add_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[BLANK])


def textbox(slide, x, y, w, h, text, size=14, bold=False, colour="#1A1A1A",
            align=PP_ALIGN.LEFT, font="Malgun Gothic", space_after=6):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        indent = len(line) - len(line.lstrip(" "))
        p.level = min(4, indent // 2)
        r = p.add_run()
        r.text = line.strip()
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = font
        r.font.color.rgb = RGBColor.from_string(colour.lstrip("#"))
    return tb


def title_bar(slide, title, sub=None):
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
    bar.line.fill.background()
    textbox(slide, 0.55, 0.28, 12.3, 0.6, title, size=25, bold=True, colour=NAVY)
    if sub:
        textbox(slide, 0.55, 0.95, 12.3, 0.45, sub, size=13, colour="#5A5A5A")


def table(slide, df, x, y, w, col_w=None, size=10.5, header_size=10.5, row_h=0.32):
    rows, cols = df.shape[0] + 1, df.shape[1]
    shape = slide.shapes.add_table(rows, cols, Inches(x), Inches(y), Inches(w),
                                   Inches(row_h * rows))
    tbl = shape.table
    if col_w:
        for i, cw in enumerate(col_w):
            tbl.columns[i].width = Inches(cw)
    for j, name in enumerate(df.columns):
        c = tbl.cell(0, j)
        c.text = str(name)
        c.fill.solid()
        c.fill.fore_color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(header_size)
                r.font.bold = True
                r.font.name = "Malgun Gothic"
                r.font.color.rgb = RGBColor.from_string("FFFFFF")
    for i in range(df.shape[0]):
        for j in range(cols):
            c = tbl.cell(i + 1, j)
            c.text = str(df.iat[i, j])
            c.fill.solid()
            c.fill.fore_color.rgb = RGBColor.from_string("FFFFFF" if i % 2 == 0 else "F2F0EC")
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.name = "Malgun Gothic"
                    r.font.color.rgb = RGBColor.from_string("1A1A1A")
    return shape


def build_deck(gene: pd.DataFrame, egpcr: pd.DataFrame, figs: dict) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    off = gene[~gene.on_panel]
    t0 = gene[gene.gene.isin(TIER0_PICK)].set_index("gene").loc[TIER0_PICK].reset_index()
    t1 = gene[gene.tier == "T1_core_add"]
    t2 = gene[gene.tier == "T2_strong"]

    # 1 title
    s = add_slide(prs)
    textbox(s, 0.8, 2.1, 11.7, 1.2,
            "Jesse 모르핀 의존 DEG vs 우리 Xenium 패널", size=34, bold=True, colour=NAVY)
    textbox(s, 0.8, 3.3, 11.7, 1.5,
            "무엇이 가장 중요한 유전자이고, 무엇을 추가해야 하는가\n"
            "5일 점증 모르핀 · DESeq2 subclass pseudobulk · padj ≤ 0.1 · PL-ILA-ORB",
            size=15, colour="#4A4A4A")
    textbox(s, 0.8, 5.5, 11.7, 0.9,
            "Hansol Lim · 2026-09-09 · 주문서 FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx (shared 158)",
            size=11.5, colour="#7A7A7A")

    # 2 Jesse's findings
    s = add_slide(prs)
    title_bar(s, "Jesse가 보낸 것 — 요약", "PL-ILA-ORB, 5일 점증 모르핀, subclass별 pseudobulk DE")
    textbox(s, 0.55, 1.55, 6.1, 5.2,
            "네 개의 DEG 리스트 (총 335행, unique 304개)\n"
            "  IEG 77 · 전사인자 179 · 시냅스 가소성 45 · GPCR 34\n"
            "  각 유전자마다 어느 subclass에서 DE인지 + 방향(Up/Down)\n"
            "\n"
            "추가로 ORB 농축 GPCR 127개\n"
            "  Allen 4M-cell atlas 대비 PL-ILA-ORB에서 농축\n"
            "  Fisher, BH FDR ≤ 0.05, ≥5% 세포, enrichment ≥ 1.5\n"
            "  glut / GABA subclass 별로 따로 계산됨",
            size=13, colour="#1A1A1A")
    textbox(s, 6.95, 1.55, 5.9, 5.2,
            "생물학적으로 무엇을 말하는가\n"
            "  모르핀 의존은 ORBm의 한 세포타입 현상이 아님.\n"
            "  상위 유전자는 L2/3부터 L6b까지, 그리고 Pvalb/Sst/Vip\n"
            "  억제성 뉴런까지 12개 앵커 중 8~11개에서 같이 변함.\n"
            "\n"
            "  방향도 압도적으로 Up (상위 20개 중 15개).\n"
            "  즉 '광범위한 전사 상태 전환'이지, 소수 세포의\n"
            "  국소적 변화가 아님.\n"
            "\n"
            "  가장 강한 축은 circadian(Per1/Per2) + 펩타이드\n"
            "  처리(Pcsk1) + 즉시조기유전자/TF 계열.",
            size=13, colour="#1A1A1A")

    # 3 headline
    s = add_slide(prs)
    title_bar(s, "핵심 결론 3가지")
    box_specs = [
        ("1", "활성 IEG 코어는 이미 있다", f"{int(gene.on_panel.sum())}개가 이미 패널에 있음.\nFos, Arc, Egr1, Junb, Nr4a1/2,\nNpas4, Bdnf — 8/12 앵커급 상위\n유전자가 여기 포함됨.", SAGE),
        ("2", "그런데 1등은 없다", f"off-panel 상위: Per2(11), Pcsk1(9),\nArid5b(8), Per1(8), Tiparp(7).\n전체 {len(off)}개가 패널 밖.\n가장 넓은 유전자가 빠져 있음.", RUST),
        ("3", "공짜로 얻을 게 남았다", "Bhlhe40(4앵커), Sema3e(3앵커)는\nXenium base에 이미 있어 슬롯\n비용 0. 지금 안 넣을 이유가 없음.", TEAL),
    ]
    for i, (num, head, body, col) in enumerate(box_specs):
        x = 0.55 + i * 4.15
        card = s.shapes.add_shape(1, Inches(x), Inches(1.7), Inches(3.85), Inches(4.3))
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor.from_string("F7F5F2")
        card.line.color.rgb = RGBColor.from_string(col.lstrip("#"))
        card.line.width = Pt(1.75)
        card.shadow.inherit = False
        textbox(s, x + 0.25, 1.95, 0.6, 0.5, num, size=26, bold=True, colour=col)
        textbox(s, x + 0.25, 2.55, 3.35, 0.8, head, size=15, bold=True, colour=col)
        textbox(s, x + 0.25, 3.5, 3.35, 2.3, body, size=12.5, colour="#2A2A2A")

    # 4 coverage table
    s = add_slide(prs)
    title_bar(s, "패널 커버리지 — 리스트별", "SHARED_PANEL_ORDER 158개 기준으로 실제 파일에서 재계산")
    rows = []
    for fname, label in LISTS.items():
        g = set(pd.read_csv(GS / fname).gene.astype(str))
        sub = gene[gene.gene.isin(g)]
        free = sub[~sub.on_panel & sub.on_base].gene.tolist()
        rows.append({
            "Jesse 리스트": label, "n": len(g),
            "패널에 있음": int(sub.on_panel.sum()),
            "없음": int((~sub.on_panel).sum()),
            "없지만 base 공짜": f"{len(free)} — {', '.join(free[:3])}" + ("…" if len(free) > 3 else ""),
        })
    eg_on = int(egpcr.on_shared_panel.sum())
    rows.append({"Jesse 리스트": "ORB 농축 GPCR", "n": len(egpcr),
                 "패널에 있음": eg_on, "없음": len(egpcr) - eg_on,
                 "없지만 base 공짜": "2 — Rxfp1, Ntsr2"})
    table(s, pd.DataFrame(rows), 0.55, 1.65, 12.25,
          col_w=[2.5, 0.9, 1.85, 1.4, 5.6], row_h=0.42)
    textbox(s, 0.55, 4.6, 12.25, 1.9,
            "읽는 법\n"
            "  IEG는 13/77로 낮아 보이지만, 빠진 64개는 대부분 1~2개 subclass에서만 DE인 잔가지.\n"
            "  반대로 TF는 14/179 — 넓은 TF(Arid5b, Banp, Klf10, Zbtb40)가 통째로 빠져 있어 실질 손실이 큼.\n"
            "  GPCR DEG 10/34은 오피오이드 수용체(Oprm1/d1/k1)와 세로토닌계를 이미 들고 있어서 나온 숫자.",
            size=12.5, colour="#2A2A2A")

    # 5 the ranking figure
    s = add_slide(prs)
    title_bar(s, "가장 중요한 유전자 — 우리 ORBm 세포타입 기준",
              "'중요하다'의 기준 = 우리가 실제로 이미징하는 12개 ORBm 앵커 중 몇 개에서 DE인가")
    s.shapes.add_picture(str(figs["breadth"]), Inches(0.5), Inches(1.5), height=Inches(5.6))
    # No leading spaces here: textbox() maps indentation onto bullet levels, and
    # a level-1 indent inside a 3.2in box re-wraps these hand-broken lines.
    textbox(s, 9.85, 1.75, 3.25, 5.2,
            "왜 이 기준인가\n"
            "Jesse의 n_DE_clusters는 PL·ILA까지\n"
            "포함한 수입니다. 우리 슬라이드에\n"
            "실제로 찍히는 건 ORBm 앵커 12개\n"
            "뿐이라, 그 교집합으로 다시 셌습니다.\n"
            "\n"
            "초록 = 이미 패널에 있음\n"
            "청록 = base 공짜, 아직 안 넣음\n"
            "빨강 = 커스텀 슬롯 필요\n"
            "\n"
            "제일 긴 막대 두 개가 빨강입니다.\n"
            "가장 넓게 변하는 유전자를 지금\n"
            "못 읽는다는 뜻입니다.",
            size=11.5, colour="#2A2A2A", space_after=3)

    # 6 coverage figure
    s = add_slide(prs)
    title_bar(s, "리스트별 커버리지 — 그림")
    s.shapes.add_picture(str(figs["coverage"]), Inches(1.35), Inches(1.6), height=Inches(4.9))
    textbox(s, 0.55, 6.65, 12.25, 0.7,
            "초록만 우리가 지금 읽을 수 있는 부분입니다. 청록은 비용 0인데 아직 주문서에 없는 부분.",
            size=12.5, colour="#2A2A2A")

    # 7 Tier 0
    s = add_slide(prs)
    title_bar(s, "Tier 0 — 지금 넣으세요 (슬롯 비용 0)",
              "Xenium 마우스 뇌 base 패널에 이미 포함 → 커스텀 슬롯을 쓰지 않음")
    d0 = pd.DataFrame({
        "유전자": t0.gene, "리스트": t0.lists, "ORBm 앵커": t0.n_orbm,
        "방향": t0.direction, "비용": "0 (base 공짜)",
        "근거": ["12개 앵커 중 4개 Up — Tier 0 중 가장 넓음",
                 "3개 앵커 Up — 이전에도 '공짜인데 안 넣음'으로 지적",
                 "ORBm 앵커 DE 0개. ORB 농축 GPCR 19 subclass로만 정당화",
                 "1개 앵커 Up — IEG 인접 TF"],
    })
    table(s, d0, 0.55, 1.65, 12.25, col_w=[1.35, 1.25, 1.4, 1.0, 1.85, 5.4], row_h=0.44)
    textbox(s, 0.55, 4.2, 12.25, 2.6,
            "왜 이게 먼저인가\n"
            "  Bhlhe40 은 12개 앵커 중 4개에서 Up. 대사·circadian 연결 TF로 Per1/Per2 축과 같은 방향을 봅니다.\n"
            "  Sema3e 는 3개 앵커에서 Up. 이전 보고에서 '공짜인데 안 넣음'으로 이미 지적된 유전자.\n"
            "  Rxfp1 은 DEG로는 ORBm 앵커 0개입니다 — 모르핀 상태 마커로는 근거가 약합니다.\n"
            "    다만 PL-ILA-ORB 19개 subclass(glut 15/GABA 4)에 농축된 GPCR이고 공짜라, 회로 표지로만 넣을 값어치가 있습니다.\n"
            "\n"
            "결정: 이 4개는 슬롯 예산과 무관하므로 주문서에 넣는 것이 순손실이 없습니다.",
            size=12.5, colour="#2A2A2A")

    # 8 Tier 1
    s = add_slide(prs)
    title_bar(s, "Tier 1 — 핵심 추가 (커스텀 슬롯 필요)",
              "ORBm 앵커 12개 중 8개 이상에서 DE · 전부 Up · 전부 패널 밖")
    d1 = pd.DataFrame({
        "유전자": t1.gene, "리스트": t1.lists, "ORBm 앵커": t1.n_orbm,
        "Glut/GABA": [f"{a}/{b}" for a, b in zip(t1.n_glut, t1.n_gaba)],
        "방향": t1.direction,
        "무엇을 보는가": [
            {"Per2": "circadian clock — 만성 오피오이드/금단에서 반복 보고되는 축",
             "Pcsk1": "prohormone convertase — proenkephalin/POMC 절단, 오피오이드 펩타이드 처리에 직결",
             "Arid5b": "넓은 TF, 억제성 뉴런까지 커버 (glut 6 / GABA 2)",
             "Per1": "Per2와 같은 clock 축, 독립 확인용"}.get(g, "")
            for g in t1.gene],
    })
    table(s, d1, 0.55, 1.65, 12.25, col_w=[1.35, 1.15, 1.35, 1.35, 0.95, 6.1], row_h=0.5)
    textbox(s, 0.55, 4.5, 12.25, 2.4,
            "이전 '4개 모르핀 레이어'와 무엇이 다른가\n"
            "  이전 목록은 Rxfp1, Per2, Pcsk1, Per1 이었습니다. Rxfp1은 ORBm 앵커 DE가 0이라 이 표에서 빠지고,\n"
            "  대신 Arid5b (앵커 8개, Per1과 동급)가 들어옵니다. 눈으로 고른 4개가 아니라 폭으로 정렬한 결과입니다.\n"
            "\n"
            "비용: 커스텀 슬롯 4개. Tier 0의 공짜 4개와 합치면 8개 추가에 슬롯은 4개만 소모.",
            size=12.5, colour="#2A2A2A")

    # 9 Tier 2
    s = add_slide(prs)
    title_bar(s, "Tier 2 — 여력이 있으면", "ORBm 앵커 6~7개 · 폭은 충분하지만 Tier 1보다 해석이 덜 직접적")
    d2 = pd.DataFrame({
        "유전자": t2.gene, "리스트": t2.lists, "ORBm 앵커": t2.n_orbm,
        "방향": t2.direction,
        "메모": [
            {"Tiparp": "IEG, 7개 앵커 전부 Glut — AHR 경로 TF",
             "Banp": "넓은 TF, 7개 앵커",
             "Fxr1": "가소성, RNA 결합 — 7개 앵커",
             "Maml3": "IEG, Notch 보조활성인자",
             "Vps13a": "가소성, glut 5 + GABA 2",
             "Camk2g": "가장 강한 Down 유전자 (6개 앵커) — 방향이 반대라 대조군으로 유용",
             "Chd2": "크로마틴 리모델러", "Dusp1": "MAPK 음성 피드백, 전형 IEG",
             "Hunk": "Down, 6개 앵커", "Klf10": "TGF-beta 연결 TF",
             "Zbtb25": "Down zinc-finger", "Zbtb40": "Up zinc-finger",
             "Zfp46": "Down zinc-finger", "Zfp641": "Down zinc-finger"}.get(g, "")
            for g in t2.gene],
    }).head(10)
    table(s, d2, 0.55, 1.6, 12.25, col_w=[1.35, 1.3, 1.35, 1.0, 7.25], row_h=0.4)
    textbox(s, 0.55, 5.9, 12.25, 1.2,
            "Camk2g 를 한 개라도 넣는 것을 권합니다. 상위권이 거의 다 Up이라, Down 유전자 하나가 있으면\n"
            "'전체적으로 발현이 올라간 것'이 아니라 '방향성 있는 상태 전환'임을 슬라이드에서 직접 보일 수 있습니다.",
            size=12.5, colour="#2A2A2A")

    # 10 glut vs gaba
    s = add_slide(prs)
    title_bar(s, "추천 유전자가 흥분성·억제성 둘 다에서 작동하는가")
    s.shapes.add_picture(str(figs["glutgaba"]), Inches(1.6), Inches(1.55), height=Inches(4.85))
    textbox(s, 0.55, 6.5, 12.25, 0.9,
            "억제성 뉴런까지 닿는 것은 Per2 (glut 8 / GABA 3), Arid5b (6/2), Vps13a (5/2) 뿐입니다.\n"
            "Tiparp·Camk2g·Chd2·Dusp1·Hunk·Klf10 은 GABA 앵커 0 — Glut 전용입니다.\n"
            "따라서 인터뉴런에서도 의존 상태를 보려면 Per2 와 Arid5b 가 사실상 필수입니다.",
            size=12.5, colour="#2A2A2A")

    # 11 recommendation
    s = add_slide(prs)
    title_bar(s, "최종 추천", "주문서에 아직 반영 안 됨 — 결정 필요")
    rec = pd.DataFrame([
        ["Tier 0 (공짜)", "Bhlhe40, Sema3e, Rxfp1, Gadd45a", "0 슬롯", "넣기 — 비용이 없음"],
        ["Tier 1 (핵심)", "Per2, Pcsk1, Arid5b, Per1", "4 슬롯", "넣기 — 모르핀 상태 레이어의 실체"],
        ["Tier 2 (선택)", "Camk2g, Tiparp, Banp, Fxr1, Maml3, Vps13a", "최대 6 슬롯", "Camk2g만이라도 (Down 대조)"],
        ["Tier 3 (보류)", "Egr3, Egr4, Crem, Nr4a3, Hrh1", "5 슬롯", "IEG+TF 이중 근거지만 앵커 5개 이하"],
    ], columns=["구간", "유전자", "비용", "권고"])
    table(s, rec, 0.55, 1.65, 12.25, col_w=[1.9, 5.5, 1.5, 3.35], row_h=0.52)
    textbox(s, 0.55, 4.2, 12.25, 2.7,
            "제가 권하는 최소안: Tier 0 전부 + Tier 1 전부 + Camk2g = 커스텀 슬롯 5개\n"
            "  이것만으로 '이 ORBm 세포가 모르핀 의존처럼 보이는가'를 흥분성·억제성 양쪽에서 묻고,\n"
            "  Down 유전자 하나로 방향성까지 확인할 수 있습니다.\n"
            "\n"
            "주의: 이 유전자들은 세포타입 마커가 아닙니다. 지금 패널로도 20개 세포타입 분리는 그대로 유지됩니다\n"
            "(ANCHOR_COVERAGE 확인). 추가하면 같은 L5 IT 안에서 '의존 시그니처 켜진 세포 vs 안 켜진 세포'를\n"
            "가를 수 있게 됩니다. 안 넣으면 세포타입 ID와 TRAP 비교는 되지만 모르핀 상태는 공간적으로 못 봅니다.",
            size=12.5, colour="#2A2A2A")

    # 12 status
    s = add_slide(prs)
    title_bar(s, "현재 상태 / 다음 단계")
    textbox(s, 0.55, 1.6, 6.1, 5.2,
            "주문서 (변경 없음)\n"
            "  FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx\n"
            "  shared 158 = 144 curated + 14 (Dan GSE283418)\n"
            "  Jesse 유전자는 아직 한 개도 안 들어감\n"
            "  20개 세포타입 분리 전부 유지 확인됨\n"
            "\n"
            "재현 방법\n"
            "  python v3/E_Planning/rank_jesse_priority_deck.py\n"
            "  입력은 전부 repo 경로 (Downloads 아님)",
            size=13, colour="#1A1A1A")
    textbox(s, 6.95, 1.6, 5.9, 5.2,
            "결정해야 할 것\n"
            "  1. Tier 0 네 개를 넣을까 (비용 0)\n"
            "  2. Tier 1 네 개에 슬롯 4개를 쓸까\n"
            "  3. Camk2g 를 Down 대조로 넣을까\n"
            "\n"
            "결정하면 반영되는 곳\n"
            "  SHARED_PANEL_ORDER · ORBm_ORDER\n"
            "  (BMAp_ORDER는 그대로 — Jesse 데이터는\n"
            "   PL-ILA-ORB, 즉 ORBm 쪽만 해당)",
            size=13, colour="#1A1A1A")

    p = OUT / "ORBm_BMAp_Jesse_priority_recommend.pptx"
    prs.save(p)
    return p


def main() -> None:
    gene, egpcr = load_ranking()

    xl = OUT / "Jesse_ORB_priority_ranking.xlsx"
    with pd.ExcelWriter(xl, engine="openpyxl") as w:
        pd.DataFrame({
            "item": ["What this ranks", "Importance metric", "ORBm anchors", "Slot cost", "Source"],
            "detail": [
                "Every Jesse opioid-dependence DEG (unique 304) against the MSGS111 order sheet.",
                "n_orbm = how many of OUR 12 ORBm anchor subclasses the gene is DE in. "
                "Jesse's own n_DE_clusters also counts PL/ILA subclasses we do not image.",
                "; ".join(ORBM_ANCHORS),
                "already on panel / FREE on base (0 slots) / 1 custom slot.",
                "v3/inputs/Jesse_ORB/. Panel: SHARED_PANEL_ORDER (158 genes).",
            ],
        }).to_excel(w, "READ_ME", index=False)
        gene.drop(columns=["n_lists"]).to_excel(w, "ranking_all", index=False)
        gene[~gene.on_panel].nlargest(40, "n_orbm").to_excel(w, "top40_off_panel", index=False)
        for t in ["T0_free_add_now", "T1_core_add", "T2_strong"]:
            gene[gene.tier == t].to_excel(w, t[:31], index=False)

    figs = {
        "breadth": fig_top_breadth(gene),
        "coverage": fig_coverage(gene),
        "glutgaba": fig_glut_gaba(gene),
    }
    deck = build_deck(gene, egpcr, figs)

    print(f"ranking  -> {xl}")
    for k, v in figs.items():
        print(f"fig {k:9s}-> {v}")
    print(f"deck     -> {deck}")
    print(f"\nTier 0 free : {', '.join(TIER0_PICK)}")
    print(f"Tier 1 core : {', '.join(gene[gene.tier=='T1_core_add'].gene)}")
    print(f"Tier 2      : {', '.join(gene[gene.tier=='T2_strong'].gene)}")


if __name__ == "__main__":
    main()
