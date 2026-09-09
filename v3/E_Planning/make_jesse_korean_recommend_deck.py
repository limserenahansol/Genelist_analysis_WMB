"""Jesse ORB 모르핀 데이터 — 한국어 추천 PowerPoint."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import nsmap, qn
from pptx.util import Emu, Inches, Pt
from pptx.oxml import parse_xml

V3 = Path(__file__).resolve().parents[1]
J = V3 / "inputs" / "Jesse_ORB"
DEG = J / "OpioidDependenceDEG_genesets_forHansol090926"
OUT = V3 / "outputs"
FIG = OUT / "jesse_korean_figures"
FIG.mkdir(exist_ok=True)
DL = Path.home() / "Downloads"

ORBM = {"004", "005", "006", "007", "022", "029", "030", "032", "046", "049", "052", "053"}
ON_SHARED = {
    "Arc", "Fos", "Egr1", "Junb", "Nr4a1", "Nr4a2", "Bdnf", "Chrm2", "Fosb",
    "Npas4", "Fezf2", "Hcrtr2", "Pou3f1", "Grm5", "Htr1b", "Oprm1", "Ntsr1",
    "Htr1a", "Oprd1", "Oprk1", "Htr2c", "Cckbr",
}

NAVY = "#1D4E89"
TEAL = "#2A6F97"
RUST = "#C44536"
GOLD = "#B08968"
SAGE = "#6B7C6A"
INK = "#2C2C2C"
UP = "#2A6F97"
DOWN = "#C44536"
HAVE = "#6B7C6A"
NEW = "#C44536"
FREE = "#B08968"

plt.rcParams.update(
    {
        "font.family": "Malgun Gothic",
        "axes.unicode_minus": False,
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

NAVY_RGB = RGBColor(0x1D, 0x4E, 0x89)
TEAL_RGB = RGBColor(0x2A, 0x6F, 0x97)
RUST_RGB = RGBColor(0xC4, 0x45, 0x36)
GOLD_RGB = RGBColor(0xB0, 0x89, 0x68)
SAGE_RGB = RGBColor(0x6B, 0x7C, 0x6A)
INK_RGB = RGBColor(0x2C, 0x2C, 0x2C)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = RGBColor(0xF4, 0xF1, 0xEA)


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
    d["on_panel"] = d["gene"].isin(ON_SHARED)
    return d


ieg = load("IEG", DEG / "mPFC_IEGDEGs.csv")
tf = load("TF", DEG / "mPFC_TFDEGs.csv")
syn = load("SynPlast", DEG / "mPFC_SynPlast.csv")
gp = load("GPCR_DEG", DEG / "mPFC_GPCRDEGs.csv")

glut = pd.read_csv(J / "PL_ILA_ORB_GlutamatergicNeurons_EnrichedGPCRs.csv")
gaba = pd.read_csv(J / "PL_ILA_ORB_GABAergicNeurons_EnrichedGPCRs.csv")
glut = glut.rename(columns={glut.columns[1]: "gene", glut.columns[2]: "n_glut"})
gaba = gaba.rename(columns={gaba.columns[1]: "gene", gaba.columns[2]: "n_gaba"})


def save(fig: plt.Figure, name: str) -> Path:
    p = FIG / name
    fig.savefig(p, dpi=200, bbox_inches="tight")
    if DL.is_dir():
        fig.savefig(DL / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig", name)
    return p


# --- figures ---
fig, ax = plt.subplots(figsize=(11.2, 6.4))
d = ieg.sort_values("n_DE_clusters", ascending=True).tail(16)
colors = [HAVE if g in ON_SHARED else NEW for g in d.gene]
ax.barh(d.gene, d.n_DE_clusters, color=colors)
ax.set_xlabel("모르핀 DEG가 나온 PL-ILA-ORB 서브클래스 수")
ax.set_title("Jesse IEG — 가장 넓은 유전자부터")
for y, (g, n, orb) in enumerate(zip(d.gene, d.n_DE_clusters, d.n_orbm)):
    tag = "이미 패널" if g in ON_SHARED else "없음"
    ax.text(n + 0.15, y, f"{n}  (ORBm {orb})  {tag}", va="center", fontsize=9, color="#444")
ax.set_xlim(0, 17)
ax.legend(
    handles=[
        mpatches.Patch(color=HAVE, label="우리 SHARED 패널에 이미 있음"),
        mpatches.Patch(color=NEW, label="패널에 없음 — 후보"),
    ],
    frameon=False,
    loc="lower right",
)
fig.tight_layout()
p_ieg = save(fig, "KR_Fig1_IEG_ranking.png")

fig, ax = plt.subplots(figsize=(11.2, 6.0))
enr = glut[["gene", "n_glut"]].merge(gaba[["gene", "n_gaba"]], on="gene", how="outer").fillna(0)
enr["n"] = enr["n_glut"] + enr["n_gaba"]
enr = enr.sort_values("n", ascending=True).tail(14)
colors = []
for g in enr.gene:
    if g in ON_SHARED:
        colors.append(HAVE)
    elif g == "Rxfp1":
        colors.append(FREE)
    else:
        colors.append(NEW)
ax.barh(enr.gene, enr.n, color=colors)
ax.set_xlabel("PL-ILA-ORB에서 농축된 서브클래스 수 (흥분+억제)")
ax.set_title("Jesse — ORB에 사는 GPCR (모르핀 DEG가 아님, 해부학적 농축)")
ax.legend(
    handles=[
        mpatches.Patch(color=HAVE, label="이미 패널"),
        mpatches.Patch(color=FREE, label="Rxfp1 — Xenium 베이스에 무료"),
        mpatches.Patch(color=NEW, label="없음 — 슬롯 필요, Allen 미확인 많음"),
    ],
    frameon=False,
    loc="lower right",
)
fig.tight_layout()
p_gpcr = save(fig, "KR_Fig2_ORB_GPCR.png")

fig, ax = plt.subplots(figsize=(11.2, 5.6))
d = syn.sort_values("n_DE_clusters", ascending=True).tail(12)
colors = [HAVE if g in ON_SHARED else NEW for g in d.gene]
ax.barh(d.gene, d.n_DE_clusters, color=colors)
ax.set_xlabel("DEG 서브클래스 수")
ax.set_title("Jesse 시냅스 가소성 DEG")
ax.legend(
    handles=[
        mpatches.Patch(color=HAVE, label="이미 패널 (Arc, Egr1, Bdnf, Grm5…)"),
        mpatches.Patch(color=NEW, label="없음 (Camk2g, Fxr1, Vps13a, Vgf…)"),
    ],
    frameon=False,
    loc="lower right",
)
fig.tight_layout()
p_syn = save(fig, "KR_Fig3_plasticity.png")

# --- ppt helpers ---
FONT = "Malgun Gothic"
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 16


def _kr(run):
    rPr = run._r.get_or_add_rPr()
    # east asia font
    ea = rPr.makeelement(qn("a:ea"), {qn("w:typeface") if False else "{http://schemas.openxmlformats.org/drawingml/2006/main}typeface": FONT})
    # simpler: set latin + ea via XML
    rPr.set("dirty", "0")


def set_run(p, text, size=18, bold=False, color=INK_RGB):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = FONT
    rPr = r._r.get_or_add_rPr()
    ea = parse_xml(
        f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{FONT}"/>'
    )
    rPr.append(ea)
    return r


def add_bar(slide, color):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()


def add_footer(slide, n):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(7.18), Inches(12.3), Inches(0.28))
    set_run(box.text_frame.paragraphs[0], f"Jesse Niehaus PL-ILA-ORB 모르핀 DEG  |  Xenium 추가 추천  |  {n}/{TOTAL}", 11, False, MUTED)


def add_title(slide, text, y=0.26):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(12.3), Inches(0.5))
    set_run(box.text_frame.paragraphs[0], text, 26, True, NAVY_RGB)


def add_sub(slide, text, y=0.74):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(y), Inches(12.3), Inches(0.38))
    set_run(box.text_frame.paragraphs[0], text, 13, False, MUTED)


def bullets(slide, items, left=0.55, top=1.25, width=12.2, height=5.6, size=17):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.clear()
        r = p.add_run()
        r.text = "•  " + item
        r.font.size = Pt(size)
        r.font.color.rgb = INK_RGB
        r.font.name = FONT
        rPr = r._r.get_or_add_rPr()
        rPr.append(parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{FONT}"/>'))
        p.space_after = Pt(8)


def card(slide, l, t, w, h, title, body, color=NAVY_RGB):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = WHITE
    sh.line.color.rgb = color
    head = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(0.42))
    head.fill.solid()
    head.fill.fore_color.rgb = color
    head.line.fill.background()
    hb = slide.shapes.add_textbox(Inches(l + 0.12), Inches(t + 0.06), Inches(w - 0.2), Inches(0.32))
    set_run(hb.text_frame.paragraphs[0], title, 13, True, WHITE)
    bb = slide.shapes.add_textbox(Inches(l + 0.14), Inches(t + 0.52), Inches(w - 0.28), Inches(h - 0.62))
    tf = bb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(body.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.clear()
        r = p.add_run()
        r.text = line
        r.font.size = Pt(13)
        r.font.color.rgb = INK_RGB
        r.font.name = FONT
        rPr = r._r.get_or_add_rPr()
        rPr.append(parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{FONT}"/>'))


def add_table(slide, rows, left=0.45, top=1.2, width=12.4, height=5.6, col_w=None):
    n_row, n_col = len(rows), len(rows[0])
    table = slide.shapes.add_table(n_row, n_col, Inches(left), Inches(top), Inches(width), Inches(height)).table
    if col_w:
        for i, w in enumerate(col_w):
            table.columns[i].width = Inches(w)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = str(val)
            r.font.size = Pt(11 if i else 12)
            r.font.bold = i == 0
            r.font.name = FONT
            r.font.color.rgb = WHITE if i == 0 else INK_RGB
            rPr = r._r.get_or_add_rPr()
            rPr.append(parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{FONT}"/>'))
            cell.text_frame.word_wrap = True
            fill = WHITE if i % 2 == 0 else PALE
            if i == 0:
                fill = NAVY_RGB
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill
    return table


# 1 title
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
box = s.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(12), Inches(1.3))
set_run(box.text_frame.paragraphs[0], "Jesse 데이터가 가리키는 유전자", 34, True, NAVY_RGB)
box = s.shapes.add_textbox(Inches(0.7), Inches(3.2), Inches(12), Inches(1.6))
tf = box.text_frame
tf.word_wrap = True
set_run(tf.paragraphs[0], "PL–ILA–ORB 5일 모르핀 의존 DEG + ORB 농축 GPCR", 20, False, INK_RGB)
p = tf.add_paragraph()
set_run(p, "세포 타입 마커가 아니라, 이미 타입된 ORBm 세포가 모르핀 의존처럼 보이는가.", 16, False, MUTED)
box = s.shapes.add_textbox(Inches(0.7), Inches(5.4), Inches(12), Inches(0.9))
set_run(box.text_frame.paragraphs[0], "Hansol Lim  |  Schnitzer + Scherrer  |  Xenium ORBm/BMAp add-on  |  2026-09-09", 14, False, MUTED)
add_footer(s, 1)

# 2 take-home
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "한 장 결론 — 무엇을 넣을 것인가")
add_sub(s, "Jesse가 찾은 가장 중요한 새 유전자는 Per2 이다. 추천은 프로그램 단위로 한다.")
card(s, 0.45, 1.25, 4.05, 5.4, "1순위  반드시",
     "Rxfp1\n\nJesse #1 ORB 농축 GPCR\n(19개 서브클래스)\n\nXenium Mouse Brain v1\n베이스에 이미 있음\n→ 슬롯 0\n\nAllen ORBm에서 확인\n(L5 ET 34%, 11/12 앵커)", GOLD_RGB)
card(s, 4.65, 1.25, 4.05, 5.4, "2순위  강력 추천",
     "Per2   Pcsk1   Per1\n\nJesse가 발견한\n모르핀 의존의 새 축.\n\nPer2 = 가장 넓은 IEG\n(13 클러스터, ORBm 11)\nFos/Arc보다 넓다.\n\n슬롯 3\n이게 핵심 패키지.", RUST_RGB)
card(s, 8.85, 1.25, 4.05, 5.4, "3순위  여유 있으면",
     "Egr3   Dusp1   Nr4a3\n\nJesse DEG + 우리 Allen에서\n이미 풍부함이 확인됨.\n\nEgr3  97%\nDusp1 54%\nNr4a3 63%\n\n슬롯 +3\nXenium에서 잘 잡힘.", TEAL_RGB)
add_footer(s, 2)

# 3 what Jesse did
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "Jesse가 측정한 것")
add_sub(s, "5일 escalating morphine  |  DESeq2 서브클래스 pseudobulk  |  padj ≤ 0.1  |  PL–ILA–ORB")
card(s, 0.45, 1.25, 6.15, 5.4, "모르핀이 바꾼 유전자 (DEG)",
     "IEG / 활성          77개\n전사인자 TF         179개\n시냅스 가소성        45개\nGPCR DEG             34개\n\n질문: 의존 후 어떤 유전자가\nORB 세포에서 켜지거나 꺼지나?\n\n대부분 Up, 흥분성 피질 세포\n(L6 IT, L6 CT, L4/5 IT, L5 ET).", NAVY_RGB)
card(s, 6.8, 1.25, 6.05, 5.4, "ORB에 원래 많은 GPCR (농축)",
     "흥분성 127개 중 상위\n억제성 리스트 별도\n\nAllen 4백만 세포 대비\nFisher, FDR 0.05, ≥5% 세포\n\n질문: 이 세포가 ORB에\n사는 세포인가?\n\n모르핀이 바꿨다는 뜻이 아님.\n해부학적 주소이다.", TEAL_RGB)
add_footer(s, 3)

# 4 most important finding
s = prs.slides.add_slide(BLANK)
add_bar(s, RUST_RGB)
add_title(s, "Jesse가 찾은 가장 중요한 유전자는 Per2")
add_sub(s, "급성 활성 IEG(Fos/Arc)는 이미 있다. Jesse의 새로운 핵심은 지연형 · 일주기 프로그램이다.")
bullets(s, [
    "Per2: 13개 서브클래스에서 Up. 우리 ORBm 앵커만 세면 11개. Fos·Arc(각 10개)보다 넓다.",
    "같은 클러스터에 Vip / Pvalb / Sst 억제성까지 포함. 흥분성만의 신호가 아니다.",
    "Per2는 일주기·의존 시계 유전자. 마우스를 잡은 순간의 활성이 아니라, 수일간의 상태.",
    "우리 기존 패널의 Fos/Arc/Egr1/Junb/Nr4a1은 TRAP·급성 활성을 본다. Per2는 그걸 대체하지 않는다.",
    "그래서 가장 중요한 ‘새’ 유전자는 Per2 하나이고, 같이 가는 짝이 Pcsk1과 Per1이다.",
], top=1.25, size=17)
add_footer(s, 4)

# 5 IEG figure
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "IEG 랭킹 — 이미 있는 것과 없는 것")
add_sub(s, "초록 = 우리 SHARED에 있음. 빨강 = 없음. Per2 / Pcsk1 / Per1 / Nr4a3 / Tiparp 가 비어 있다.")
s.shapes.add_picture(str(p_ieg), Inches(0.7), Inches(1.15), Inches(12.0), Inches(5.7))
add_footer(s, 5)

# 6 the program
s = prs.slides.add_slide(BLANK)
add_bar(s, RUST_RGB)
add_title(s, "한 유전자가 아니라, Jesse의 모르핀 프로그램")
add_sub(s, "네 덩어리로 읽는 것이 맞다. 4개만 외우면 프로그램이 안 보인다.")
card(s, 0.4, 1.25, 3.05, 5.4, "A. 이미 있음",
     "급성 TRAP / IEG\n\nFos  Arc\nEgr1  Junb\nNr4a1  Fosb\nNpas4  Bdnf\n\nJesse도 이걸\n상위 DEG로 봄.\n넣을 필요 없음.", SAGE_RGB)
card(s, 3.55, 1.25, 3.05, 5.4, "B. 새 핵심",
     "지연 · 시계 · 분비\n\nPer2   13 클러스터\nPcsk1  11\nPer1    8\nNr4a3   8\n\n이게 Jesse가\n새로 보여 준 축.\n강력 추천.", RUST_RGB)
card(s, 6.7, 1.25, 3.05, 5.4, "C. 풍부 확인",
     "Allen에서 이미 많음\n\nEgr3   97%\nDusp1  54%\nCrem   64%\nVgf    84%\n\nXenium에서\n잡힐 확률 높음.\n3순위.", TEAL_RGB)
card(s, 9.85, 1.25, 3.05, 5.4, "D. 넣지 말 것",
     "TF 179개 대부분\n\nArid5b Banp\nChd2 아연핑거\n\nJesse도\nMERFISH 풍부함\n먼저 보라고 함.\n슬롯 낭비.", GOLD_RGB)
add_footer(s, 6)

# 7 gene table
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "중요 유전자를 넓게 보면")
add_sub(s, "n = Jesse DEG 서브클래스 수. ORBm = 우리 12개 앵커와 겹친 수.")
add_table(
    s,
    [
        ["유전자", "Jesse가 말한 것", "n / ORBm", "방향", "우리 패널", "Allen ORBm", "추천"],
        ["Per2", "가장 넓은 IEG. 지연·일주기", "13 / 11", "Up", "없음", "우리 표에 없음", "반드시 검토"],
        ["Pcsk1", "펩타이드 가공. 두 번째 IEG", "11 / 9", "Up", "없음", "우리 표에 없음", "강력 추천"],
        ["Arc / Fos", "급성 활성 · TRAP", "10 / 10", "Up", "이미 있음", "높음", "유지"],
        ["Egr1 Junb Nr4a1", "급성 IEG, Jesse도 상위", "8 / 7–8", "Up", "이미 있음", "높음", "유지"],
        ["Per1", "시계 유전자, Per2와 짝", "8 / 8", "Up", "없음", "63% L4/5 IT", "강력 추천"],
        ["Nr4a3", "Nr4a1의 형제, 지연형", "8 / 5", "Up", "없음", "63%", "여유 시"],
        ["Tiparp Maml3", "지연 IEG, 7–8 클러스터", "8 / 7", "Up", "없음", "미계산", "보류"],
        ["Dusp1", "빠른 탈인산화 IEG", "6 / 6", "Up", "없음", "54%", "여유 시"],
        ["Egr3", "Egr 패밀리, 매우 풍부", "5 / 5", "Up", "없음", "97%", "여유 시"],
    ],
    top=1.15,
    height=5.7,
    col_w=[1.55, 3.15, 1.2, 0.7, 1.35, 2.15, 1.3],
)
add_footer(s, 7)

# 8 plasticity
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "시냅스 가소성 — Jesse의 두 번째 축")
add_sub(s, "Arc/Egr1/Bdnf/Grm5는 이미 있다. 없는 것 중 넓은 것은 Camk2g(Down), Fxr1, Vps13a, Vgf.")
s.shapes.add_picture(str(p_syn), Inches(0.65), Inches(1.15), Inches(12.0), Inches(5.7))
add_footer(s, 8)

# 9 plasticity recommend
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "가소성 유전자, 무엇을 넣을까")
add_sub(s, "IEG 프로그램보다 우선순위는 낮다. 슬롯이 남을 때만.")
card(s, 0.45, 1.25, 4.05, 5.4, "이미 커버됨",
     "Arc   Egr1   Bdnf\nGrm5   Ntrk2 일부\n\n가소성 질문의 핵심은\n이미 패널에 있다.\nJesse 리스트와 겹침.", SAGE_RGB)
card(s, 4.65, 1.25, 4.05, 5.4, "넓지만 Allen 미확인",
     "Camk2g  Down 7클러스터\nFxr1    Up 7\nVps13a  Up 7\n\n우리 A06 표에 없음.\nXenium에서 안 잡힐 수\n있다. 지금은 보류.", GOLD_RGB)
card(s, 8.85, 1.25, 4.05, 5.4, "확인된 보조",
     "Vgf  Allen 84%\n(Jesse 4 클러스터)\n\nHrh1 는 GPCR DEG이기도\n하지만 Allen 미확인.\n\nVgf만 4순위로 고려.", TEAL_RGB)
add_footer(s, 9)

# 10 GPCR two kinds
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL_RGB)
add_title(s, "GPCR은 두 종류다 — 섞지 말 것")
add_sub(s, "모르핀이 바꾼 GPCR ≠ ORB에 원래 많은 GPCR")
card(s, 0.45, 1.25, 6.15, 5.4, "모르핀 DEG GPCR (34개)",
     "가장 넓은 것: Hrh1 (4, Up)\n그다음 Grm2 Down, Adra1a Down,\nGrm5 Up, Hrh3 Up (각 3)\n\n이미 패널: Grm5, Chrm2, Htr1b,\nOprm1, Ntsr1, Htr1a, Oprd1,\nOprk1, Htr2c, Hcrtr2\n\n새 후보는 Hrh1, Grm2.\n둘 다 우리 Allen 표에 없음.\nIEG보다 약하다.", NAVY_RGB)
card(s, 6.8, 1.25, 6.05, 5.4, "ORB 농축 GPCR (해부)",
     "Rxfp1  19  ← 1등, 무료\nMas1   17  흥분성만\nMchr1  14\nAdra1a 14\nGpr68  13\n\n이미 패널: Cnr1, Cckbr,\nHcrtr2, Drd1, Oprd1…\n\nMas1/Gpr68/Mchr1는\nAllen 40-GPCR 계산에\n없어서 풍부함 미증명.", TEAL_RGB)
add_footer(s, 10)

# 11 GPCR figure
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL_RGB)
add_title(s, "ORB 농축 GPCR — Rxfp1이 1등")
add_sub(s, "이건 ‘모르핀이 바꿨다’가 아니라 ‘ORB 세포의 주소’다. Rxfp1만 무료 + Allen 확인.")
s.shapes.add_picture(str(p_gpcr), Inches(0.65), Inches(1.15), Inches(12.0), Inches(5.7))
add_footer(s, 11)

# 12 Rxfp1
s = prs.slides.add_slide(BLANK)
add_bar(s, GOLD_RGB)
add_title(s, "Rxfp1 을 리스트에 올리는 이유")
add_sub(s, "슬롯을 안 쓴다. Jesse의 해부 GPCR 1등이고, 우리 Allen ORBm에서도 보인다.")
bullets(s, [
    "Jesse: PL–ILA–ORB 19개 서브클래스에서 농축 (흥분 15 + 억제 4). 리스트 전체 1등.",
    "Xenium Mouse Brain v1 베이스에 이미 있음 → 주문 시트에 표시만 하면 된다.",
    "우리 Allen ORBm 앵커: 최대 34% (L5 ET), 11/12 앵커에서 ≥5%. 폭발적으로 많지는 않다.",
    "Hochgerner 논문에서도 BMA VGLUT2 아형 마커로 나오지만, Jesse 쪽 의미는 ORB 주소.",
    "Mas1(17)은 더 넓어 보이지만 우리 표에 없고, 보통 희귀하다. 지금은 넣지 말 것.",
], top=1.25, size=17)
add_footer(s, 12)

# 13 Allen
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "우리 Allen ORBm으로 다시 본 풍부함")
add_sub(s, "Jesse가 넓다고 한 것과, Xenium에서 잡힐 것인지는 다른 질문이다.")
add_table(
    s,
    [
        ["유전자", "Jesse", "Allen ORBm 최대 %", "해석"],
        ["Egr3", "IEG DEG 5클러스터", "97%  (L4/5 IT)", "넣으면 거의 확실히 보임"],
        ["Vgf", "가소성 4클러스터", "84%", "여유 있으면 좋음"],
        ["Dusp1", "IEG DEG 6", "54%", "중간. 3순위로 충분"],
        ["Per1", "IEG DEG 8", "63%", "시계 짝. 2순위에 포함"],
        ["Nr4a3", "IEG DEG 8", "63%", "Nr4a1이 이미 있음. 보조"],
        ["Crem", "IEG DEG 5", "64%", "3순위 끝자락"],
        ["Rxfp1", "농축 19", "34%  (L5 ET)", "무료라서 올린다"],
        ["Per2 Pcsk1", "가장 넓은 새 IEG", "우리 A06에 없음", "Jesse 근거로 넣는다"],
        ["Mas1 Gpr68 Mchr1", "농축 13–17", "계산 안 함", "지금은 넣지 말 것"],
    ],
    top=1.15,
    height=5.7,
    col_w=[2.2, 3.2, 3.3, 3.7],
)
add_footer(s, 13)

# 14 do not add
s = prs.slides.add_slide(BLANK)
add_bar(s, GOLD_RGB)
add_title(s, "넣지 말 것")
add_sub(s, "Jesse 리스트가 크다고 해서 다 중요한 것이 아니다.")
card(s, 0.45, 1.25, 4.05, 5.4, "TF 165개",
     "Arid5b(8) Banp(7)\nChd2 Klf10\n아연핑거 여러 개\n\n염색질 반응이지\n모르핀 특이 마커가 아님.\nJesse: MERFISH 먼저.", GOLD_RGB)
card(s, 4.65, 1.25, 4.05, 5.4, "해부 GPCR 미확인",
     "Mas1  Gpr68\nMchr1  Grm8\nChrm1  Gpr26\n\nORB vs 나머지 뇌.\n의존 DEG가 아님.\n우리 Allen 40-GPCR에\n없어서 풍부함 모름.", RUST_RGB)
card(s, 8.85, 1.25, 4.05, 5.4, "이미 있는 것을 바꾸지 말 것",
     "Fos Arc Oprm1\nNtsr1 Egr1\n를 Jesse TF로 교체 금지.\n\nTRAP 태그와 세포 타입\n분리가 1순위이다.\n상태 유전자는 그 위.", SAGE_RGB)
add_footer(s, 14)

# 15 recommendation table
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "추천 추가 리스트 (이 순서로)")
add_sub(s, "Dan 14개를 이미 넣으면 커스텀 114. 아래는 그 위에 쌓을지 결정.")
add_table(
    s,
    [
        ["순위", "유전자", "슬롯", "이유", "결정"],
        ["1", "Rxfp1", "무료", "Jesse ORB GPCR 1등 + 베이스에 있음", "지금 올려라"],
        ["2", "Per2", "1", "Jesse 최광역 IEG. Fos보다 넓다", "모르핀 상태를 볼 거면 넣는다"],
        ["3", "Pcsk1", "1", "두 번째 광역 IEG. 펩타이드 가공", "Per2와 세트로"],
        ["4", "Per1", "1", "시계 짝. Allen 63%로 확인", "Per2와 세트로"],
        ["5", "Egr3", "1", "Allen 97%. Xenium에 잘 잡힘", "슬롯 남으면"],
        ["6", "Dusp1", "1", "빠른 IEG, Allen 54%", "슬롯 남으면"],
        ["7", "Nr4a3", "1", "Nr4a1 형제, Allen 63%", "슬롯 남으면"],
        ["8", "Vgf", "1", "가소성+분비, Allen 84%", "더 남으면"],
        ["—", "Mas1 등", "1+", "해부만, 풍부함 미증명", "넣지 말 것"],
        ["—", "TF 다수", "많음", "염색질 반응", "넣지 말 것"],
    ],
    top=1.15,
    height=5.7,
    col_w=[0.9, 1.6, 0.9, 5.6, 3.4],
)
add_footer(s, 15)

# 16 decision
s = prs.slides.add_slide(BLANK)
add_bar(s, NAVY_RGB)
add_title(s, "세 가지 안 — 이렇게 결정하면 된다")
add_sub(s, "세포 타입 144는 건드리지 않는다. Dan 14는 이미 MSGS111에 있다.")
card(s, 0.4, 1.25, 4.1, 5.4, "A안  최소 (추천 기본)",
     "Rxfp1만 표시 (무료)\n+ Per2 Pcsk1 Per1\n\n커스텀 +3\n(Dan 유지 시 117)\n\nJesse의 핵심 프로그램을\n읽는다.\n\n내가 권하는 기본안.", RUST_RGB)
card(s, 4.65, 1.25, 4.1, 5.4, "B안  확장",
     "A안\n+ Egr3 Dusp1 Nr4a3\n\n커스텀 +6\n\nAllen에서 잘 보이는\n보조 IEG까지.\nXenium 신호가 확실.", TEAL_RGB)
card(s, 8.9, 1.25, 4.1, 5.4, "C안  슬롯 고정 100",
     "세포타입 144 유지\nRxfp1만 추가 (무료)\n\nDan 14와 Jesse DEG는\n스왑 없이는 불가.\n\n모르핀 상태는\n이번 슬라이드에서\n포기하는 안.", GOLD_RGB)
add_footer(s, 16)

out = OUT / "Jesse_Xenium_gene_recommend_KR.pptx"
prs.save(out)
print("PPT saved", out.exists(), out.stat().st_size)
if DL.is_dir():
    alt = DL / "Jesse_Xenium_gene_recommend_KR.pptx"
    prs.save(alt)
    print("Downloads copy", alt.exists(), alt.stat().st_size)
