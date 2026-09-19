"""Append the Jesse morphine-state genes to the MSGS111 order sheet and build the PI deck.

Formatting rule: the workbook is opened with openpyxl and only *appended* to, so
column widths, frozen panes, header styling and every existing row survive
untouched. No existing cell is edited and no gene is removed or re-ranked. New
rows inherit the default data-row style (Calibri 11, not bold), which is what
the existing data rows already use.

Adds:
  SHARED_PANEL_ORDER  ranks 159-167   block 13_Jesse_morphine_state
  ORBm_ORDER          ranks 141-149   (Jesse data is PL-ILA-ORB, so ORBm only)
  FOR_MarkGreg        one new summary row, in the style of the Dan-14 row
  SOURCES             two new rows (Jesse list, Dan GSE283418) - both had only
                      "stands in until that arrives" placeholders before

Dan re-check verdict: nothing further to add. See dan_recheck() for the numbers.

Outputs:
  FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v2_167genes.xlsx
  ORBm_BMAp_panel_v2_for_PI.pptx   (4 slides)
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
SRC = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
DST = OUT / "FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v2_167genes.xlsx"
DECK = OUT / "ORBm_BMAp_panel_v2_for_PI.pptx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
DAN = OUT / "GSE283418_vs_BMAp_panel.xlsx"

NAVY = "#1D4E89"
RUST = "#C44536"
TEAL = "#2A6F97"
SAGE = "#6B7C6A"

JESSE_WHY = (
    "Added from Jesse Niehaus PL-ILA-ORB opioid-dependence DEGs (5-day escalating "
    "morphine, DESeq2 subclass pseudobulk, padj<=0.1). Ranked by how many of the 12 "
    "ORBm anchor subclasses show DE. Reports morphine-dependence state, NOT cell "
    "type, so it carries no Allen separator score. No existing gene was removed or "
    "re-ranked."
)
RXFP1_WHY = (
    "Added from Jesse Niehaus PL-ILA-ORB enriched-GPCR list: enriched in 19 "
    "PL-ILA-ORB subclasses (15 glut / 4 GABA) vs the rest of the Allen 4M-cell "
    "atlas. Note it is DE in 0 of the 12 ORBm anchors, so it is a circuit-proximity "
    "marker, not a morphine-state marker. Free on the Xenium base panel."
)

# (gene, n_orbm_anchors, direction, free_on_base, one-line role)
JESSE_ADD = [
    ("Per2",    11, "Up",   False, "Top morphine DEG: 11 of 12 ORBm anchors, glut 8 / GABA 3. Circadian clock."),
    ("Pcsk1",    9, "Up",   False, "9 of 12 anchors. Prohormone convertase 1 (proenkephalin / POMC processing)."),
    ("Arid5b",   8, "Up",   False, "8 of 12 anchors, glut 6 / GABA 2. Broad TF that also reaches interneurons."),
    ("Per1",     8, "Up",   False, "8 of 12 anchors. Second clock gene, independent confirmation of Per2."),
    ("Camk2g",   6, "Down", False, "Strongest DOWN gene, 6 of 12 anchors. Direction control against the Up-heavy set."),
    ("Bhlhe40",  4, "Up",   True,  "4 of 12 anchors. Metabolic/circadian TF. Free on Xenium base."),
    ("Sema3e",   3, "Up",   True,  "3 of 12 anchors. Free on Xenium base; previously flagged as a missed free gene."),
    ("Gadd45a",  1, "Up",   True,  "1 anchor. IEG-adjacent TF. Free on Xenium base, so zero slot cost."),
    ("Rxfp1",    0, "n/a",  True,  "ORB-enriched GPCR (19 subclasses). Free on base. Circuit marker, not state."),
]

SHARED_COLS = ["order_rank", "gene", "block", "serves", "why",
               "max_pct", "max_mean", "max_spec_panel"]
BLOCK = "13_Jesse_morphine_state"


def dan_recheck() -> dict:
    """Re-score all 98 Dan genes against the current 158-gene panel."""
    d = pd.read_excel(DAN, "all_98_genes")
    panel = set(pd.read_excel(SRC, "SHARED_PANEL_ORDER").gene.astype(str))
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    d["ON"] = d.gene.isin(panel)
    off = d[~d.ON].copy()
    added14 = d[d.gene.isin([
        "Col23a1", "Slc29a4", "Cck", "Gfra1", "Sp8", "Abca8a", "Calcrl",
        "Lamb3", "Syndig1l", "Tspan18", "Gabre", "Nos1", "Oprl1", "Dnah5"])]
    return {
        "n_on": int(d.ON.sum()),
        "n_off": int((~d.ON).sum()),
        "off_best": off.nlargest(4, "max_spec")[["gene", "max_spec", "top_BMAp_anchor"]],
        "off_max_spec": float(off.max_spec.max()),
        "added_min_spec": float(added14.max_spec.min()),
        "added_max_spec": float(added14.max_spec.max()),
        "n_unscored": int(off.allen_BMAp.eq("not scored").sum()),
        "free_off": sorted(off[off.gene.isin(base)].gene),
    }


def append_panel() -> dict:
    shutil.copy2(SRC, DST)  # copy first: the original file is never opened for write
    wb = load_workbook(DST)

    sh = wb["SHARED_PANEL_ORDER"]
    orbm = wb["ORBm_ORDER"]
    shared_start = sh.max_row          # 159 header-inclusive -> last data row
    orbm_start = orbm.max_row

    for i, (gene, n, direction, free, role) in enumerate(JESSE_ADD):
        why = (RXFP1_WHY if gene == "Rxfp1" else JESSE_WHY) + f" || {role}"
        serves = (
            "ORB-enriched GPCR :: circuit proximity" if gene == "Rxfp1"
            else f"morphine-dependence state :: {n}/12 ORBm anchors {direction}"
        )
        # SHARED_PANEL_ORDER: 8 columns, numeric specificity columns left empty
        # on purpose (these are state markers, not cell-type separators).
        sh.cell(row=shared_start + 1 + i, column=1, value=shared_start + i)
        sh.cell(row=shared_start + 1 + i, column=2, value=gene)
        sh.cell(row=shared_start + 1 + i, column=3, value=BLOCK)
        sh.cell(row=shared_start + 1 + i, column=4, value=serves)
        sh.cell(row=shared_start + 1 + i, column=5, value=why)
        # ORBm_ORDER: 5 columns
        orbm.cell(row=orbm_start + 1 + i, column=1, value=orbm_start + i)
        orbm.cell(row=orbm_start + 1 + i, column=2, value=gene)
        orbm.cell(row=orbm_start + 1 + i, column=3, value=BLOCK)
        orbm.cell(row=orbm_start + 1 + i, column=4, value=serves)
        orbm.cell(row=orbm_start + 1 + i, column=5, value=why)

    customs = [g for g, _, _, free, _ in JESSE_ADD if not free]
    frees = [g for g, _, _, free, _ in JESSE_ADD if free]

    fg = wb["FOR_MarkGreg"]
    fg.cell(row=fg.max_row + 1, column=1, value="9 genes appended (Jesse ORB, morphine state)")
    fg.cell(row=fg.max_row, column=2, value=(
        f"{', '.join(customs)} ({len(customs)} new custom slots) and "
        f"{', '.join(frees)} (already free on the 10x base panel, 0 slots) were added at the "
        f"bottom of SHARED_PANEL_ORDER and ORBm_ORDER as block {BLOCK}. No existing gene was "
        f"removed or re-ranked, and BMAp_ORDER is unchanged because Jesse's data is PL-ILA-ORB. "
        f"Shared panel is now 167 genes = 48 free on base + 119 custom "
        f"(was 158 = 44 + 114). These genes report morphine-dependence state, not cell type, "
        f"so ANCHOR_COVERAGE is unchanged and all 20 cell types remain separable."
    ))

    src = wb["SOURCES"]
    r = src.max_row + 1
    for row_vals in [
        ["Niehaus2026_ORB", "Jesse Niehaus (personal communication)",
         "Niehaus J. PL-ILA-ORB opioid-dependence DEGs and enriched GPCRs, shared 2026-09-09.",
         2026, "unpublished", None, None, None,
         "Opioid-dependence DEGs (IEG 77, TF 179, synaptic plasticity 45, GPCR 34) from 5-day "
         "escalating morphine, DESeq2 subclass pseudobulk padj<=0.1, plus 127 PL-ILA-ORB "
         "enriched GPCRs. Basis for the 9 genes in block 13_Jesse_morphine_state. "
         "Replaces the Lui2021 stand-in.", "no",
         "Received as per-subclass DEG tables (gene, n_DE_clusters, direction, DE_clusters), not raw counts."],
        ["GSE283418", "Berg & Scherrer (GSE283418)",
         "Spatial molecular profiling of amygdalar neurons enables precision pharmacology "
         "against pain unpleasantness.", 2025, "GEO dataset", None, None,
         "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE283418",
         "Custom 98-gene Resolve Molecular Cartography amygdala panel. 14 genes scored as "
         "BMAp-informative in Allen were appended as block 12_GSE283418_added. Re-checked "
         "2026-09-09: the remaining 46 off-panel genes all score max_spec < 0.9, so nothing "
         "further was added. Replaces the Hochgerner2023 stand-in.", "no",
         "GEO metadata only (family.soft, series matrix); no raw expression matrix downloaded."],
    ]:
        for c, v in enumerate(row_vals, start=1):
            src.cell(row=r, column=c, value=v)
        r += 1

    wb.save(DST)
    return {"customs": customs, "frees": frees}


# ------------------------------------------------------------------ deck
def textbox(slide, x, y, w, h, text, size=13, bold=False, colour="#1A1A1A",
            align=PP_ALIGN.LEFT, space_after=5):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = line.strip()
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = "Malgun Gothic"
        run.font.color.rgb = RGBColor.from_string(colour.lstrip("#"))
    return tb


def title_bar(slide, title, sub=None):
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
    bar.line.fill.background()
    textbox(slide, 0.55, 0.24, 12.3, 0.58, title, size=24, bold=True, colour=NAVY)
    if sub:
        textbox(slide, 0.55, 0.88, 12.3, 0.42, sub, size=12.5, colour="#5A5A5A")


def table(slide, df, x, y, w, col_w, size=10.5, row_h=0.34):
    shape = slide.shapes.add_table(df.shape[0] + 1, df.shape[1], Inches(x), Inches(y),
                                   Inches(w), Inches(row_h * (df.shape[0] + 1)))
    tbl = shape.table
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for j, name in enumerate(df.columns):
        c = tbl.cell(0, j)
        c.text = str(name)
        c.fill.solid()
        c.fill.fore_color.rgb = RGBColor.from_string(NAVY.lstrip("#"))
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold = Pt(size), True
                r.font.name = "Malgun Gothic"
                r.font.color.rgb = RGBColor.from_string("FFFFFF")
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
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


def build_deck(dan: dict, added: dict) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    # --- 1 what changed
    s = prs.slides.add_slide(blank)
    title_bar(s, "ORBm / BMAp Xenium 패널 최종본 — 무엇이 바뀌었나",
              "MSGS111 주문서에 Jesse 유전자 9개 추가. Dan 데이터 재검토 결과 추가 없음.")
    for i, (num, head, body, col) in enumerate([
        ("158 → 167", "유전자 9개 추가",
         "Jesse 모르핀 의존 DEG에서 5개,\nXenium base 공짜에서 4개.\n기존 유전자는 하나도\n삭제·재정렬 안 함.", TEAL),
        ("+5", "커스텀 슬롯만 5개",
         "114 → 119 custom.\n공짜 44 → 48.\n9개 중 4개는 base에 이미\n있어 비용이 없습니다.", RUST),
        ("+0", "Dan 추가 없음",
         f"98개 중 {dan['n_on']}개가 이미 패널.\n남은 {dan['n_off']}개는 전부\nmax_spec < {dan['off_max_spec']:.2f} 로\n기존 유전자를 못 이깁니다.", SAGE),
    ]):
        x = 0.55 + i * 4.15
        card = s.shapes.add_shape(1, Inches(x), Inches(1.5), Inches(3.85), Inches(2.5))
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor.from_string("F7F5F2")
        card.line.color.rgb = RGBColor.from_string(col.lstrip("#"))
        card.line.width = Pt(1.75)
        card.shadow.inherit = False
        textbox(s, x + 0.25, 1.68, 3.4, 0.5, num, size=23, bold=True, colour=col)
        textbox(s, x + 0.25, 2.22, 3.4, 0.4, head, size=13.5, bold=True, colour=col)
        textbox(s, x + 0.25, 2.72, 3.4, 1.2, body, size=11.5, colour="#2A2A2A")

    textbox(s, 0.55, 4.25, 12.3, 2.9,
            "이 패널이 이제 묻는 세 가지 질문\n"
            "  1. 이 세포가 무슨 타입인가 — 세포타입 분리 20종 그대로 유지 (ANCHOR_COVERAGE 변경 없음)\n"
            "  2. 방금 활성화/TRAP+ 인가 — Fos, Arc, Egr1, Junb, Npas4 등 기존 IEG\n"
            "  3. (신규) 이 ORBm 세포가 모르핀 의존 상태인가 — Per2, Pcsk1, Arid5b, Per1 + Camk2g(반대 방향)\n"
            "\n"
            "3번이 이번에 추가된 축입니다. 기존 패널로는 세포타입과 활성만 알 수 있었고,\n"
            "같은 L5 IT 안에서 '의존 시그니처가 켜진 세포 vs 안 켜진 세포'를 가를 수 없었습니다.",
            size=13, colour="#1A1A1A")

    # --- 2 Jesse: what and why
    s = prs.slides.add_slide(blank)
    title_bar(s, "추가한 Jesse 유전자 9개 — 선정 근거",
              "기준 = 우리가 실제로 이미징하는 ORBm 앵커 세포타입 12개 중 몇 개에서 DE인가")
    rank = pd.read_excel(RANK, "ranking_all")
    rows = []
    for gene, n, direction, free, role in JESSE_ADD:
        r = rank[rank.gene == gene]
        gg = f"{int(r.n_glut.iloc[0])}/{int(r.n_gaba.iloc[0])}" if len(r) else "-"
        rows.append({
            "유전자": gene,
            "ORBm 앵커": f"{n}/12" if gene != "Rxfp1" else "0/12",
            "Glut/GABA": gg,
            "방향": direction,
            "슬롯": "공짜(base)" if free else "커스텀 1",
            "왜 넣는가": role,
        })
    table(s, pd.DataFrame(rows), 0.55, 1.5, 12.25,
          col_w=[1.05, 1.05, 1.05, 0.75, 1.15, 7.2], size=10, row_h=0.44)
    textbox(s, 0.55, 6.1, 12.25, 1.2,
            "Per2·Pcsk1 이 Jesse 데이터 전체의 1·2위이고 둘 다 우리 패널에 없었습니다. Arid5b 는 Per1 과 동급(8개 앵커)이면서\n"
            "억제성 뉴런까지 닿아 인터뉴런에서도 의존 상태를 볼 수 있게 합니다. Camk2g 는 유일한 강한 Down 유전자로,\n"
            "'전체가 다 올라간 것'이 아니라 방향성 있는 상태 전환임을 보이는 대조입니다.",
            size=12, colour="#2A2A2A")

    # --- 3 Dan re-check
    s = prs.slides.add_slide(blank)
    title_bar(s, "Dan (GSE283418) 재검토 — 추가할 것 없음",
              "98개 유전자를 현재 158개 패널 기준으로 다시 채점")
    best = dan["off_best"]
    dd = pd.DataFrame({
        "유전자": best.gene,
        "max_spec": [f"{v:.2f}" for v in best.max_spec],
        "top BMAp anchor": best.top_BMAp_anchor.fillna("(Allen 미채점)"),
        "판정": ["기존 패널 유전자를 못 이김 (spec < 1.0)"] * len(best),
    })
    table(s, dd, 0.55, 1.5, 12.25, col_w=[1.4, 1.3, 5.15, 4.4], size=10.5, row_h=0.4)
    textbox(s, 0.55, 3.5, 12.25, 3.6,
            f"숫자\n"
            f"  98개 중 {dan['n_on']}개는 이미 패널에 있습니다. 남은 {dan['n_off']}개 중 최고가 max_spec {dan['off_max_spec']:.2f} 입니다.\n"
            f"  max_spec < 1.0 은 '그 앵커에 대해 이미 패널에 있는 유전자보다 특이적이지 않다'는 뜻입니다.\n"
            f"  {dan['n_unscored']}개는 Allen BMAp에서 아예 채점되지 않아 평가 불가입니다 (그중 Sema3e 는 Jesse 쪽으로 이미 들어감).\n"
            "\n"
            "솔직한 단서 하나\n"
            f"  이미 넣은 14개의 max_spec 범위는 {dan['added_min_spec']:.2f}~{dan['added_max_spec']:.2f} 입니다. 즉 Nos1(0.76),\n"
            "  Oprl1(0.57), Dnah5(0.53) 는 지금 안 넣은 Sfrp1(0.89)·Glipr1(0.88)·Vdr(0.87) 보다 낮습니다.\n"
            "  그 셋은 특이도가 아니라 약리학적 이유로 들어간 것입니다 (Oprl1 = nociceptin 수용체, Nos1 = 인터뉴런 마커).\n"
            "  따라서 '특이도만으로' 고르면 Glipr1 이 유일한 경계선 후보입니다 — 앵커 113 MEA-COA-BMA 가 진짜 BMAp 앵커라서.\n"
            "  다만 0.88 은 여전히 1.0 미만이라, 슬롯 1개를 쓸 근거로는 약하다고 봅니다. 넣지 않았습니다.",
            size=12.5, colour="#2A2A2A")

    # --- 4 final panel + decision
    s = prs.slides.add_slide(blank)
    title_bar(s, "최종 패널 구성 및 확인 요청",
              "FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v2_167genes.xlsx")
    comp = pd.DataFrame([
        ["세포타입 분리 + 백본 + TF/GPCR (기존)", "144", "100 custom + 44 free", "변경 없음"],
        ["Dan GSE283418 (block 12)", "14", "14 custom", "변경 없음"],
        ["Jesse 모르핀 상태 (block 13, 신규)", "9", "5 custom + 4 free", "이번 추가"],
        ["합계", "167", "119 custom + 48 free", "+9 유전자 / +5 슬롯"],
    ], columns=["구성", "유전자 수", "슬롯", "이번 변경"])
    table(s, comp, 0.55, 1.5, 12.25, col_w=[5.6, 1.5, 2.9, 2.25], size=11.5, row_h=0.42)

    textbox(s, 0.55, 3.65, 6.05, 3.4,
            "파일에서 지킨 것\n"
            "  서식·열 너비·고정 창·헤더 스타일 그대로\n"
            "  기존 행은 한 칸도 수정하지 않음\n"
            "  삭제·재정렬 없음, 맨 아래에만 append\n"
            "  BMAp_ORDER 변경 없음 (Jesse는 PL-ILA-ORB)\n"
            "  ANCHOR_COVERAGE 변경 없음 → 20종 분리 유지\n"
            "  FOR_MarkGreg·SOURCES 에 설명 행만 추가",
            size=12.5, colour="#1A1A1A")
    textbox(s, 6.9, 3.65, 5.95, 3.4,
            "확인 부탁드릴 것\n"
            "  1. 커스텀 슬롯 5개 추가를 승인할지\n"
            "     (119 custom — 벤더 상한 확인 필요)\n"
            "  2. Camk2g(Down 대조)를 유지할지\n"
            "  3. Glipr1 을 BMAp용으로 넣을지\n"
            "     (제 권고: 넣지 않음)\n"
            "\n"
            "승인되면 그대로 주문 가능한 상태입니다.",
            size=12.5, colour="#1A1A1A")

    prs.save(DECK)
    return DECK


def main() -> None:
    dan = dan_recheck()
    added = append_panel()
    deck = build_deck(dan, added)

    sh = pd.read_excel(DST, "SHARED_PANEL_ORDER")
    orbm = pd.read_excel(DST, "ORBm_ORDER")
    bmap = pd.read_excel(DST, "BMAp_ORDER")
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    free = sh.gene.isin(base).sum()
    print(f"workbook -> {DST}")
    print(f"  SHARED {len(sh)} genes = {free} free + {len(sh)-free} custom")
    print(f"  ORBm   {len(orbm)} | BMAp {len(bmap)} (unchanged)")
    print(f"  dupes  : {sh.gene.duplicated().sum()}")
    print(f"  ranks  : contiguous={list(sh.order_rank)==list(range(1,len(sh)+1))}")
    print(f"  added  : {', '.join(added['customs'])} (custom) + {', '.join(added['frees'])} (free)")
    print(f"\nDan re-check: {dan['n_on']}/98 on panel, {dan['n_off']} off, "
          f"best off max_spec={dan['off_max_spec']:.2f} -> add nothing")
    print(f"deck     -> {deck}")


if __name__ == "__main__":
    main()
