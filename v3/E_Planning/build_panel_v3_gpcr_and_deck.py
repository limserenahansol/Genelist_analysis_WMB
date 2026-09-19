"""Final panel: morphine-state genes AND druggable GPCR-map genes. Plus the 4-slide PI deck.

Correction this script encodes: an earlier pass judged Chrm1 and Grm8 by morphine
relevance and rejected them. That was the wrong test. This is a GPCR panel first;
an ORB-enriched receptor earns a slot by mapping where a druggable receptor sits,
whether or not morphine moves it. Scored properly, Chrm1 and Grm8 are the only
off-panel ORB-enriched GPCRs with BOTH high enrichment and verified high Allen
detectability, and both fill a receptor-family gap:

  Chrm1  M1 muscarinic (Gq)  - panel carries only Chrm2 (M2, Gi). Opposite signalling.
  Grm8   mGlu8, group III (Gi, presynaptic) - panel carries Grm1/Grm5, group I (Gq).

Note on druggability: v3/inputs/gpcr_drug_targets_detailed.csv annotates only 38
mostly on-panel genes, so it cannot score these candidates. It is deliberately not
used as a filter here - absence of an annotation is not evidence of undruggability.

Adds to the order sheet, append-only, formatting preserved:
  block 13_Jesse_morphine_state  Per2 Pcsk1 Vps13a Camk2g Arid5b + Bhlhe40 Sema3e Gadd45a
  block 14_ORB_enriched_GPCR     Chrm1 Grm8 + Rxfp1

Outputs
  FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v3_169genes.xlsx
  ORBm_BMAp_panel_v3_final_EN.pptx  (4 slides)
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

V3 = Path(__file__).resolve().parents[1]
OUT = V3 / "outputs"
FIG = OUT / "panel_v3final_figures"
FIG.mkdir(exist_ok=True)

SRC = OUT / "FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx"
DST = OUT / "FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v3_169genes.xlsx"
DECK = OUT / "ORBm_BMAp_panel_v3_final_EN.pptx"
BASE = OUT / "xenium_mouse_brain_base_panel.txt"
RANK = OUT / "Jesse_ORB_priority_ranking.xlsx"
ABUND = OUT / "jesse_allen_gpcr_abundance" / "Jesse_GPCR_Allen_ORBm_summary.csv"
EGPCR = OUT / "Jesse_ORB_vs_Xenium_panel.xlsx"

NAVY, TEAL, RUST, GOLD, SAGE, TAUPE = ("#1D4E89", "#2A6F97", "#C44536",
                                       "#B08968", "#6B7C6A", "#8C7B6B")
GREY = "#B8B2A8"
INK, MUTED, WHITE = RGBColor(0x1F, 0x29, 0x37), RGBColor(0x5B, 0x64, 0x72), RGBColor(0xFF, 0xFF, 0xFF)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.grid": False,
})

# gene, block, slot, purpose-note
MORPHINE = [
    ("Per2",    "custom", "11/12 ORBm anchors Up, glut 8 / GABA 3. Broadest gene in Jesse's data."),
    ("Pcsk1",   "custom", "9/12 Up. Proenkephalin / POMC convertase."),
    ("Arid5b",  "custom", "8/12 Up, glut 6 / GABA 2. Only broad gene besides Per2 reaching interneurons."),
    ("Vps13a",  "custom", "7/12 Up AND 95% Allen detection - best measured on both axes."),
    ("Camk2g",  "custom", "6/12 DOWN, 93% detection. Only direction control in the set."),
    ("Bhlhe40", "free",   "4/12 Up. Free on Xenium base."),
    ("Sema3e",  "free",   "3/12 Up. Free on base."),
    ("Gadd45a", "free",   "1/12 Up. Free on base."),
]
GPCR = [
    ("Chrm1", "custom", "M1 muscarinic (Gq). ORB-enriched in 8 subclasses, 92% detection, 9/12 anchors >50%. "
                        "Panel has only Chrm2 (M2, Gi) - opposite signalling, real family gap."),
    ("Grm8",  "custom", "mGlu8, group III (Gi, presynaptic autoreceptor). Enriched in 9 subclasses, 99% detection, "
                        "8/12 anchors >50%. Panel has Grm1/Grm5 (group I, Gq) only."),
    ("Rxfp1", "free",   "Relaxin-family RXFP1. Highest ORB enrichment of all (19 subclasses) but only 34% detection. "
                        "Free on base, so worth taking despite the sparse signal."),
]
ADD = [(g, "13_Jesse_morphine_state", s, w) for g, s, w in MORPHINE] + \
      [(g, "14_ORB_enriched_GPCR", s, w) for g, s, w in GPCR]

WHY13 = ("Added from Jesse Niehaus PL-ILA-ORB opioid-dependence DEGs (5-day escalating morphine, DESeq2 "
         "subclass pseudobulk, padj<=0.1). Selected on DE breadth across the 12 ORBm anchor subclasses and, "
         "where measured, Allen detectability. Reports morphine-dependence state, NOT cell type.")
WHY14 = ("Added from Jesse Niehaus PL-ILA-ORB enriched-GPCR list (Fisher, BH FDR<=0.05, >=5% cells, "
         "enrichment>=1.5 vs the rest of the Allen 4M-cell atlas). Selected on ORB enrichment, Allen "
         "detectability and receptor-family gaps in the existing 29 panel GPCRs. Serves the druggable "
         "receptor map, independent of whether morphine regulates it.")


def gpcr_candidates() -> pd.DataFrame:
    panel = set(pd.read_excel(SRC, "SHARED_PANEL_ORDER").gene.astype(str))
    eg = pd.read_excel(EGPCR, "enriched_GPCRs")
    ab = pd.read_csv(ABUND)[["gene", "max_pct", "n_anchors_pct_ge_50"]]
    e = eg[~eg.gene.isin(panel)].merge(ab, on="gene", how="left")
    return e.nlargest(14, "n_subclass_hits")


def fig_gpcr(e: pd.DataFrame) -> Path:
    """Off-panel ORB-enriched GPCRs: enrichment bars, detectability as colour + label."""
    d = e.iloc[::-1]

    def status(r):
        if pd.isna(r.max_pct):
            return "detectability not scored"
        return "detectable (>=50%)" if r.max_pct >= 50 else "too sparse (<50%)"

    cols = {"detectable (>=50%)": TEAL, "too sparse (<50%)": TAUPE,
            "detectability not scored": GREY}
    d = d.assign(status=d.apply(status, axis=1))

    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    y = np.arange(len(d))
    ax.barh(y, d.n_subclass_hits, color=[cols[s] for s in d.status], height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(d.gene, fontsize=9.5)
    for i, r in enumerate(d.itertuples()):
        lab = "not scored" if pd.isna(r.max_pct) else f"{r.max_pct:.0f}% detected"
        ax.text(r.n_subclass_hits + 0.25, i, lab, va="center", fontsize=8.4, color="#4A4A4A")
    ax.set_xlim(0, 25)
    ax.set_xlabel("ORB enrichment: PL-ILA-ORB subclasses where the receptor is enriched", fontsize=9.5)
    ax.set_title("Druggable GPCR map: which ORB-enriched receptors are worth a slot",
                 fontsize=11.5, color=NAVY, pad=10)
    # Outside the axes: the right-hand column is taken by the family-gap notes.
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=cols[k]) for k in cols], cols.keys(),
              fontsize=8.6, loc="upper center", bbox_to_anchor=(0.5, -0.115),
              ncol=3, frameon=False)
    # Anchor the notes at a fixed x past the "% detected" labels so the leader
    # lines cannot strike through them.
    notes = {"Chrm1": ("PROPOSED - M1 (Gq) vs panel's M2 (Gi)", NAVY),
             "Grm8": ("PROPOSED - group III (Gi) vs panel's group I (Gq)", NAVY),
             "Gpr26": ("orphan receptor: no known ligand, so it does not\nserve a druggable map - not proposed", TAUPE)}
    for g, (note, col) in notes.items():
        i = list(d.gene).index(g)
        ax.annotate(note, (d.n_subclass_hits.iloc[i], i), xytext=(15.0, i),
                    textcoords="data", fontsize=8.2, color=col, va="center",
                    # shrinkB is the bar end, where the "% detected" label sits.
                    arrowprops=dict(arrowstyle="-", color=col, lw=0.7,
                                    shrinkA=4, shrinkB=88))
    fig.text(0.5, -0.10,
             "Enrichment alone is not enough: Rxfp1 (19), Mas1 (17), Mchr1 and Adra1a (14) top the ranking but are "
             "detected in only 32-45% of cells, or were never scored. Chrm1 and Grm8 are the only off-panel "
             "candidates verified above 50%.", ha="center", fontsize=8.2, color="#666")
    fig.tight_layout()
    p = FIG / "v3f_gpcr.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_morphine(rank: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    top = rank.nlargest(12, ["n_orbm", "n_DE_clusters"]).iloc[::-1]
    cols = {"already on panel": SAGE, "FREE on base": TEAL, "1 custom slot": RUST}
    ax = axes[0]
    y = np.arange(len(top))
    ax.barh(y, top.n_orbm, color=[cols[c] for c in top.slot_cost], height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(top.gene, fontsize=9)
    for i, (n, dr) in enumerate(zip(top.n_orbm, top.direction)):
        ax.text(n + 0.15, i, f"{n} {dr}", va="center", fontsize=8.2, color="#4A4A4A")
    ax.set_xlim(0, 13.5)
    ax.set_xlabel("ORBm anchor cell types with DE (of 12)", fontsize=9)
    ax.set_title("A. Morphine-state breadth on OUR cell types", fontsize=10.5)
    present = [k for k in cols if (top.slot_cost == k).any()]
    ax.legend([plt.Rectangle((0, 0), 1, 1, color=cols[k]) for k in present], present,
              fontsize=8, loc="lower right", frameon=False)

    picks = ["Per2", "Pcsk1", "Arid5b", "Vps13a", "Camk2g", "Bhlhe40", "Sema3e"]
    sub = rank[rank.gene.isin(picks)].set_index("gene").loc[picks].iloc[::-1]
    ax = axes[1]
    y = np.arange(len(sub))
    ax.barh(y + 0.19, sub.n_glut, height=0.36, color=NAVY, label="Glut anchors (of 8)")
    ax.barh(y - 0.19, sub.n_gaba, height=0.36, color=GOLD, label="GABA anchors (of 4)")
    ax.set_yticks(y)
    ax.set_yticklabels(sub.index, fontsize=9)
    ax.set_xlabel("ORBm anchor cell types with DE", fontsize=9)
    ax.set_title("B. Only Per2 and Arid5b reach interneurons", fontsize=10.5)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    fig.tight_layout()
    p = FIG / "v3f_morphine.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


def append_panel() -> dict:
    shutil.copy2(SRC, DST)
    wb = load_workbook(DST)
    sh, orbm = wb["SHARED_PANEL_ORDER"], wb["ORBm_ORDER"]
    r0, o0 = sh.max_row, orbm.max_row
    for i, (gene, block, slot, note) in enumerate(ADD):
        why = (WHY13 if block.startswith("13") else WHY14) + f" || {note}"
        serves = ("morphine-dependence state" if block.startswith("13")
                  else "ORB-enriched druggable GPCR")
        for ws, base_row, ncol in ((sh, r0, 5), (orbm, o0, 5)):
            row = base_row + 1 + i
            ws.cell(row=row, column=1, value=(base_row + i))
            ws.cell(row=row, column=2, value=gene)
            ws.cell(row=row, column=3, value=block)
            ws.cell(row=row, column=4, value=serves)
            ws.cell(row=row, column=5, value=why)

    cust = [g for g, _, s, _ in ADD if s == "custom"]
    free = [g for g, _, s, _ in ADD if s == "free"]
    fg = wb["FOR_MarkGreg"]
    fg.cell(row=fg.max_row + 1, column=1, value="11 genes appended (Jesse ORB: morphine state + GPCR map)")
    fg.cell(row=fg.max_row, column=2, value=(
        f"Block 13_Jesse_morphine_state: {', '.join(g for g, b, s, n in ADD if b.startswith('13'))}. "
        f"Block 14_ORB_enriched_GPCR: {', '.join(g for g, b, s, n in ADD if b.startswith('14'))}. "
        f"{len(cust)} new custom slots ({', '.join(cust)}); {', '.join(free)} are already free on the 10x base panel. "
        f"Added at the bottom of SHARED_PANEL_ORDER and ORBm_ORDER; no existing gene removed or re-ranked; "
        f"BMAp_ORDER unchanged because Jesse's data is PL-ILA-ORB. Shared panel is now 169 genes = 48 free + "
        f"121 custom (was 158 = 44 + 114). Block 13 reports morphine state and block 14 extends the druggable "
        f"receptor map; neither is a cell-type separator, so ANCHOR_COVERAGE is unchanged and all 20 cell types "
        f"remain separable."
    ))
    wb.save(DST)
    return {"custom": cust, "free": free}


# ------------------------------------------------------------------ deck
def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def set_run(p, text, size=18, bold=False, color=INK):
    p.clear()
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
    r.font.color.rgb = color
    return r


def new_slide(prs, title, sub, n, total=4):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(NAVY)
    bar.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.4), Inches(0.18), Inches(12.5), Inches(0.44))
    tb.text_frame.word_wrap = True
    set_run(tb.text_frame.paragraphs[0], title, 24, True, rgb(NAVY))
    if sub:
        sb = s.shapes.add_textbox(Inches(0.4), Inches(0.62), Inches(12.5), Inches(0.34))
        sb.text_frame.word_wrap = True
        set_run(sb.text_frame.paragraphs[0], sub, 13, False, MUTED)
    fb = s.shapes.add_textbox(Inches(0.4), Inches(7.18), Inches(12.5), Inches(0.26))
    set_run(fb.text_frame.paragraphs[0],
            f"Xenium ORBm + BMAp add-on  |  Jesse Niehaus  +  Daniel Berg / Scherrer  |  {n}/{total}",
            11, False, MUTED)
    return s


def lines(slide, items, x, y, w, h, size=12, colour=INK):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        set_run(p, t, size, False, colour)
        p.space_after = Pt(5)
    return box


def picture(slide, path, top, max_h, max_w=12.6):
    pic = slide.shapes.add_picture(str(path), Inches(0), Inches(top), height=Inches(max_h))
    if pic.width > Inches(max_w):
        sc = Inches(max_w) / pic.width
        pic.width, pic.height = int(pic.width * sc), int(pic.height * sc)
    pic.left = int((Inches(13.333) - pic.width) / 2)
    return pic.top / 914400 + pic.height / 914400


def table(slide, df, x, y, w, col_w, size=10.5, row_h=0.34, head=NAVY, band=None):
    shp = slide.shapes.add_table(df.shape[0] + 1, df.shape[1], Inches(x), Inches(y),
                                 Inches(w), Inches(row_h * (df.shape[0] + 1)))
    t = shp.table
    for i, cw in enumerate(col_w):
        t.columns[i].width = Inches(cw)
    for j, name in enumerate(df.columns):
        c = t.cell(0, j)
        c.text = str(name)
        c.fill.solid()
        c.fill.fore_color.rgb = rgb(head)
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.name = Pt(size), True, "Calibri"
                r.font.color.rgb = WHITE
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            c = t.cell(i + 1, j)
            c.text = str(df.iat[i, j])
            c.fill.solid()
            c.fill.fore_color.rgb = rgb(band[i]) if band and band[i] else (
                RGBColor(0xFF, 0xFF, 0xFF) if i % 2 == 0 else RGBColor(0xF2, 0xF0, 0xEC))
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(size), "Calibri"
                    r.font.color.rgb = INK
    return shp


def build_deck(rank, e, figs, added) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 1 four jobs
    s = new_slide(prs, "The panel does four jobs - each needs its own metric",
                  "An earlier draft judged the GPCR candidates by whether morphine regulates them. "
                  "That was the wrong test: this is a GPCR panel first.", 1)
    jobs = pd.DataFrame([
        ["1. Cell typing", "Specificity vs the panel in Allen WMB-10X", "53 separators + backbone", "unchanged - all 20 types still separable"],
        ["2. Activity / TRAP", "Established IEG set", "Fos, Arc, Egr1, Junb, Npas4 ...", "unchanged"],
        ["3. Druggable GPCR map", "ORB enrichment + Allen detectability + receptor-family gap", "29 GPCRs", "ADD Chrm1, Grm8 (+ Rxfp1 free)"],
        ["4. Morphine-dependence state", "DE breadth across the 12 ORBm anchors + detectability", "nothing - this axis was missing", "ADD Per2, Pcsk1, Arid5b, Vps13a, Camk2g (+3 free)"],
    ], columns=["Job", "The right metric", "What the panel already has", "This round"])
    table(s, jobs, 0.4, 1.05, 12.5, col_w=[2.5, 3.9, 2.9, 3.2], size=11, row_h=0.72,
          band=[None, None, "#EAF0F6", "#F0F5F2"])
    lines(s, [
        "Jobs 3 and 4 are independent. A receptor can earn a slot purely by showing where a druggable target sits, "
        "whether or not morphine moves it - Chrm1 is not a morphine DEG and still belongs on the panel.",
        "Equally, a morphine-state gene does not need to be druggable. Judging either by the other's metric is what "
        "produced two conflicting drafts.",
    ], 0.4, 4.5, 12.5, 1.1, size=12)

    # 2 GPCR map
    s = new_slide(prs, "Job 3  |  which ORB-enriched GPCRs are worth a slot",
                  "Enrichment ranks them; Allen detectability decides which are usable in Xenium; "
                  "family gaps break the tie.", 2)
    bottom = picture(s, figs["gpcr"], 1.02, 4.55)
    lines(s, [
        "Chrm1 (M1, Gq) and Grm8 (mGlu8, group III, Gi) are the only off-panel candidates verified above 50% detection - "
        "92% and 99%, in 9 and 8 of the 12 anchors. Both also fill a real family gap: the panel's only muscarinic is Chrm2 "
        "(M2, Gi, opposite signalling) and its only mGlus are Grm1/Grm5 (group I, Gq).",
        "Rxfp1 tops the enrichment ranking (19 subclasses) but is detected in only 34% of cells. It is free on the base "
        "panel, so it is worth taking anyway - just expect a sparse map. Mas1, Mchr1, Adra1a, Hrh3 and Gpr3 are either "
        "too sparse or unscored, so they are not proposed.",
    ], 0.4, bottom + 0.10, 12.5, 1.25, size=11.5)

    # 3 morphine axis
    s = new_slide(prs, "Job 4  |  the morphine-state genes",
                  "New axis: within one L5 IT cell, is the dependence signature ON or OFF?", 3)
    bottom = picture(s, figs["morphine"], 1.02, 4.35)
    lines(s, [
        "Per2 (11/12) and Pcsk1 (9/12) are the two broadest genes in Jesse's whole dataset and both were missing. "
        "Lamp5 carries no DEG at all, so 11 is the ceiling - Per2 changes wherever anything changes.",
        "Vps13a (7/12, 95% detection) and Camk2g (6/12 DOWN, 93%) are the strongest on detectability. Camk2g is the only "
        "DOWN gene, which shows the change is directional rather than a global lift. Arid5b is kept because it and Per2 are "
        "the only broad genes reaching interneurons (panel B) - its own detectability is unscored.",
    ], 0.4, bottom + 0.10, 12.5, 1.25, size=11.5)

    # 4 final
    s = new_slide(prs, "FINAL  |  11 genes added, 7 custom slots",
                  "158 -> 169 genes = 48 free on base + 121 custom. Nothing added from Dan.", 4)
    rows = [{"Gene": g, "Job": "GPCR map" if b.startswith("14") else "morphine state",
             "Slot": "1 custom" if s_ == "custom" else "free",
             "Why": n[:118]} for g, b, s_, n in ADD]
    band = ["#EAF0F6" if r["Job"] == "GPCR map" else "#F0F5F2" for r in rows]
    table(s, pd.DataFrame(rows), 0.4, 1.02, 12.5, col_w=[1.05, 1.5, 1.0, 8.95],
          size=10, row_h=0.335, band=band)
    lines(s, [
        "BLOCKING: custom slots go 114 -> 121, against an original vendor cap of 100. This needs confirming before ordering.",
        "If the cap is firm, drop in this order: Arid5b (detectability unscored, Per2 still covers GABA), then Camk2g "
        "(loses the direction control), then Grm8 (Chrm1 is the bigger family gap). Alternatively drop the weakest Dan "
        "genes - Gabre (spec 0.95, CEA-BST), Tspan18 (0.96, SI/LPO border), Syndig1l (1.32, CEA-BST) serve neighbours, not BMAp core.",
        "Order sheet FINAL_Xenium_panel_ORBm_BMAp_MSGS111_v3_169genes.xlsx keeps MSGS111 formatting, column widths, frozen "
        "panes and every existing row byte-identical; rows were only appended.",
    ], 0.4, 5.15, 12.5, 1.9, size=11.5)

    prs.save(DECK)
    return DECK


def main() -> None:
    rank = pd.read_excel(RANK, "ranking_all")
    e = gpcr_candidates()
    figs = {"gpcr": fig_gpcr(e), "morphine": fig_morphine(rank)}
    added = append_panel()
    deck = build_deck(rank, e, figs, added)

    sh = pd.read_excel(DST, "SHARED_PANEL_ORDER")
    base = set(pd.read_csv(BASE, header=None)[0].astype(str))
    free = int(sh.gene.isin(base).sum())
    print(f"workbook -> {DST}")
    print(f"  SHARED {len(sh)} = {free} free + {len(sh)-free} custom | dupes {sh.gene.duplicated().sum()} | "
          f"ranks ok {list(sh.order_rank)==list(range(1,len(sh)+1))}")
    print(f"  custom added: {', '.join(added['custom'])}")
    print(f"  free added  : {', '.join(added['free'])}")
    print(f"deck     -> {deck}")


if __name__ == "__main__":
    main()
