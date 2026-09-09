"""4-slide deck: which genes to add from Dan, Jesse, and Allen ORBm."""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
DL = Path.home() / "Downloads"
FONT = "Malgun Gothic"

NAVY = RGBColor(0x1D, 0x4E, 0x89)
TEAL = RGBColor(0x2A, 0x6F, 0x97)
RUST = RGBColor(0xC4, 0x45, 0x36)
GOLD = RGBColor(0xB0, 0x89, 0x68)
SAGE = RGBColor(0x6B, 0x7C, 0x6A)
INK = RGBColor(0x2C, 0x2C, 0x2C)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = RGBColor(0xF4, 0xF1, 0xEA)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def kr(run):
    rPr = run._r.get_or_add_rPr()
    rPr.append(
        parse_xml(
            f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{FONT}"/>'
        )
    )


def set_run(p, text, size=18, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = FONT
    kr(r)
    return r


def add_bar(slide, color=NAVY):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.1))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()


def add_footer(slide, n):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(7.18), Inches(12.4), Inches(0.26))
    set_run(
        box.text_frame.paragraphs[0],
        f"Xenium ORBm + BMAp  |  Dan GSE283418  ·  Jesse PL-ILA-ORB  ·  Allen WMB-10X  |  {n}/4",
        11,
        False,
        MUTED,
    )


def add_title(slide, text):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(0.22), Inches(12.4), Inches(0.46))
    set_run(box.text_frame.paragraphs[0], text, 24, True, NAVY)


def add_sub(slide, text):
    box = slide.shapes.add_textbox(Inches(0.45), Inches(0.66), Inches(12.4), Inches(0.32))
    set_run(box.text_frame.paragraphs[0], text, 13, False, MUTED)


def card(slide, l, t, w, h, title, body, color=NAVY):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = WHITE
    sh.line.color.rgb = color
    head = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(0.38))
    head.fill.solid()
    head.fill.fore_color.rgb = color
    head.line.fill.background()
    hb = slide.shapes.add_textbox(Inches(l + 0.1), Inches(t + 0.05), Inches(w - 0.18), Inches(0.3))
    set_run(hb.text_frame.paragraphs[0], title, 12, True, WHITE)
    bb = slide.shapes.add_textbox(Inches(l + 0.12), Inches(t + 0.46), Inches(w - 0.24), Inches(h - 0.56))
    tf = bb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(body.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, line, 12, False, INK)


def add_table(slide, rows, left, top, width, height, col_w):
    table = slide.shapes.add_table(len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(height)).table
    for i, w in enumerate(col_w):
        table.columns[i].width = Inches(w)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            set_run(cell.text_frame.paragraphs[0], str(val), 11 if i else 11, i == 0, WHITE if i == 0 else INK)
            cell.text_frame.word_wrap = True
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if i == 0 else (WHITE if i % 2 == 0 else PALE)


# --- 1 take-home ---
s = prs.slides.add_slide(BLANK)
add_bar(s)
add_title(s, "추가할 유전자 — Dan + Jesse + Allen")
add_sub(s, "세포타입 144는 유지. Dan 14는 이미 MSGS111. Jesse는 Allen 절대량으로 걸렀다. 106,122 ORBm 세포.")
card(s, 0.4, 1.1, 4.15, 5.7, "지금 올려라",
     "무료\n  Rxfp1   (베이스 패널)\n\n커스텀  모르핀 상태\n  Per2   Pcsk1   Per1\n\n커스텀  ORBm GPCR\n  Chrm1   Grm8\n\nAllen 최대 %\n  Chrm1 92%  ·  Grm8 99%\n  Per1 63%  ·  Rxfp1 34%\n\n슬롯 +5  (Dan 유지 시 119)", RUST)
card(s, 4.7, 1.1, 4.15, 5.7, "여유 있으면",
     "Gpr26    IT 86%\nMas1     L5 ET 45%\nCamk2g   전역 93%  (Down)\n\nGpr26 / Mas1 = ORB 주소\nCamk2g = 모르핀이 끄는\n가소성 유전자. 전 세포에서\n이미 높다.\n\n슬롯 +3 더", TEAL)
card(s, 9.0, 1.1, 3.9, 5.7, "넣지 말 것 / 이미 있음",
     "이미 있음\n  Fos Arc Egr1 Junb\n  Nr4a1 Oprm1 Cckbr\n  Hcrtr2 Chrm2 Grm5\n\n절대량 약함\n  Mchr1   32%  (2앵커만 ≥20%)\n\n전역이라 정보 적음\n  Fxr1  Vps13a\n\nTF 160개  ·  CEA/glia", GOLD)
add_footer(s, 1)

# --- 2 Dan ---
s = prs.slides.add_slide(BLANK)
add_bar(s, TEAL)
add_title(s, "Dan  GSE283418 — 이미 시트에 넣은 14개")
add_sub(s, "Resolve 98-gene smFISH. 38개는 원래 패널에 있음. 14개를 MSGS111에 추가 (랭크 145–158).")
add_table(
    s,
    [
        ["유전자", "Allen에서 가장 가까운 타입", "왜 넣었나", "주의"],
        ["Lamb3", "113 BMA Ccdc42", "진짜 BMAp에 가장 가까움", "슬롯 1"],
        ["Cck  Col23a1  Slc29a4", "012 VGLUT1 경계", "BMA/MEA 겹침 공간", "핵 중심은 아님"],
        ["Abca8a  Dnah5", "012 경계", "같은 VGLUT1 블록", ""],
        ["Calcrl  Nos1  Oprl1", "120 MEA Otp Foxp2", "슬라이드에 MEA가 있으면", "BMAp 분리용 아님"],
        ["Gfra1  Sp8", "MEA–BST", "이웃핵", ""],
        ["Syndig1l  Gabre  Tspan18", "CEA / SI 경계", "원하면 유지", "제일 먼저 자를 후보"],
    ],
    0.4,
    1.08,
    12.5,
    4.55,
    [2.6, 3.2, 3.5, 3.2],
)
box = s.shapes.add_textbox(Inches(0.45), Inches(5.75), Inches(12.4), Inches(1.2))
tf = box.text_frame
tf.word_wrap = True
set_run(tf.paragraphs[0], "Dan은 세포타입을 다시 짜는 데이터가 아니다. 편도 공간 패널을 우리 BMAp ROI에 맞춰 본 것이다.", 14, False, INK)
p = tf.add_paragraph()
set_run(p, "14개 전부 유지하면 커스텀 114 (한도 100). 한도를 지키려면 Lamb3 + 012 경계만 남기고 CEA 쪽을 뺀다.", 14, False, INK)
add_footer(s, 2)

# --- 3 Jesse + Allen ---
s = prs.slides.add_slide(BLANK)
add_bar(s)
add_title(s, "Jesse + Allen — 상대 농축이 아니라 절대량")
add_sub(s, "Jesse: 5일 모르핀 DEG + ORB vs 나머지 뇌 GPCR 농축. Allen: 같은 유전자를 ORBm 12앵커에서 % expressing.")
add_table(
    s,
    [
        ["유전자", "Jesse가 말한 것", "Allen ORBm 최대 %", "결정"],
        ["Chrm1", "ORB 흥분성 농축 (7앵커)", "92%  L2/3   ·  9앵커 ≥50%", "추가  1순위 GPCR"],
        ["Grm8", "ORB 억제성 농축 (7앵커)", "99%  L5 ET  ·  8앵커 ≥50%", "추가  1순위 GPCR"],
        ["Gpr26", "ORB IT 농축", "86%  L4/5 IT", "여유 시"],
        ["Cckbr  Hcrtr2", "ORB 농축", "74% / 67%  Lamp5", "이미 패널"],
        ["Rxfp1", "농축 1–2등 (19 서브클래스)", "34%  L5 ET   무료 베이스", "지금 표시"],
        ["Mas1", "흥분성 농축 1등 (17)", "45%  L5 ET  ·  GABA 1–2%", "선택. 흥분성만"],
        ["Gpr68  Mchr1", "농축 3–4등", "40% IT / 32% ET", "Mchr1은 보류"],
        ["Per2  Pcsk1  Per1", "가장 넓은 새 IEG (13/11/8)", "Per1 63%  ·  Per2·Pcsk1은 이번 12유전자에 없음", "상태 패키지"],
        ["Camk2g", "가소성 Down 7클러스터", "93%  전 앵커 ≥50%", "Down을 읽을 때만"],
    ],
    0.35,
    1.05,
    12.6,
    5.85,
    [2.15, 3.35, 4.3, 2.8],
)
add_footer(s, 3)

# --- 4 decision ---
s = prs.slides.add_slide(BLANK)
add_bar(s, RUST)
add_title(s, "권장 주문 — 이 리스트만 시트에 더한다")
add_sub(s, "144 세포타입 + Dan 14는 그대로. 아래는 Jesse를 Allen으로 걸러 낸 추가분.")
add_table(
    s,
    [
        ["순위", "유전자", "근거", "슬롯", "시트"],
        ["0", "Rxfp1", "Jesse ORB GPCR 상위 + 베이스에 있음 + Allen 34%", "0", "지금 올려라"],
        ["1", "Per2", "Jesse 최광역 IEG (13 클러스터). Fos보다 넓다", "1", "지금"],
        ["2", "Pcsk1", "두 번째 광역 IEG. 펩타이드 가공", "1", "지금"],
        ["3", "Per1", "시계 짝. Allen 63%", "1", "지금"],
        ["4", "Chrm1", "Allen 92%. Jesse ORB 농축. Chrm2는 이미 있음", "1", "지금"],
        ["5", "Grm8", "Allen 99%. Jesse ORB 농축. Grm5는 이미 있음", "1", "지금"],
        ["6", "Gpr26", "Allen 86% IT", "1", "여유 시"],
        ["7", "Mas1", "Jesse 1등. Allen 45% ET, GABA 없음", "1", "여유 시"],
        ["8", "Camk2g", "Allen 93%. 모르핀 Down", "1", "상태 읽을 때"],
    ],
    0.35,
    1.05,
    12.6,
    5.15,
    [0.8, 1.4, 6.3, 1.0, 3.1],
)
box = s.shapes.add_textbox(Inches(0.4), Inches(6.28), Inches(12.5), Inches(0.75))
tf = box.text_frame
tf.word_wrap = True
set_run(tf.paragraphs[0], "기본안  슬롯 +5 (Rxfp1 무료 + Per2 Pcsk1 Per1 Chrm1 Grm8).  Dan 14 유지 시 커스텀 119.  한도 100이면 Dan CEA 쪽과 스왑.", 14, True, INK)
add_footer(s, 4)

ppt = OUT / "Add_genes_Jesse_Allen_Dan_4slides.pptx"
prs.save(ppt)
print("saved", ppt.exists(), ppt.stat().st_size)
if DL.is_dir():
    alt = DL / "Add_genes_Jesse_Allen_Dan_4slides.pptx"
    prs.save(alt)
    print("downloads", alt.stat().st_size)
