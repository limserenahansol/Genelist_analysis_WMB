import pandas as pd
from pathlib import Path

x = Path(r"c:\Users\hsollim\Downloads\FINAL_Xenium_panel_ORBm_BMAp_for_MSGS111.xlsx")
sh = set(pd.read_excel(x, "SHARED_PANEL_ORDER").gene.astype(str))
orb = set(pd.read_excel(x, "ORBm_ORDER").gene.astype(str))
bm = set(pd.read_excel(x, "BMAp_ORDER").gene.astype(str))
base = {
    g.strip()
    for g in open(
        r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs\xenium_mouse_brain_base_panel.txt"
    )
    if g.strip()
}

ieg = """Per2 Pcsk1 Arc Fos Egr1 Junb Nr4a1 Nr4a3 Per1 Tiparp Maml3 Dusp1 Hunk Nr4a2 Bdnf Chrm2 Crem Egr3 Egr4 Kitl Omg Stk40 Acsl4 Dusp4 Dusp5 Fosb Fosl2 Gpr63 Hsd17b12 Mbnl2 Sema3e Zdbf2 Gpr22 Ier2 Osgin2 Rel Rnf128 Scg2 Btg2 Cdkn1a Chst8 Coq10b Csrnp1 Gadd45g Herpud1 Kcna1 Kcnf1 Mpp7 Npas4 Nppc Palmd Ptger4 Sertad1 Spty2d1 Sv2c Tbc1d8b Wdr90 Adcyap1 Bmp3 Ccdc184 Chac1 Dusp14 Egr2 Ell2 Fezf2 Hcrtr2 Kcnj4 Kcns2 Lipg Pam Plagl1 Pnoc Pou3f1 Ptgs2 Sowahb Stac Tll1""".split()
syn = """Arc Camk2g Fxr1 Vps13a Chrd Egr1 Bdnf Hrh1 Pak1 Vgf Grm2 Lrrtm2 Rapgef2 Grm5 Lzts1 Mgll Npas4 Shisa6 Sipa1l1 Sorcs2 Adcy8 Adrb1 Akap5 Apoe Bcl2l1 Cd2ap Creb1 Egr2 Grin2a Htr6 Kmt2a Mapt Mir124a-1hg Neto1 Neurod2 Nr3c1 Ntrk2 Pde9a Ptgs2 Rasgrf2 Reln Slc1a1 Sorcs3 Synpo Unc13c""".split()
gpcr = """Hrh1 Grm5 Hrh3 Chrm2 Htr1b Adgrd1 Adrb1 Gpr68 Hcrtr2 Htr7 Oprm1 Ptger4 S1pr3 Sstr4 Adra1a Grm2 Adra1b Gpr12 Ntsr1 Sstr1 Adra2a Adra2c Gpr27 Grm8 Htr1a Htr6 Lpar1 Mas1 Npy5r Oprd1 Oprk1 Rxfp1 Htr2c Pth2r""".split()
tf_wide = """Arid5b Junb Banp Fos Chd2 Klf10 Zbtb25 Zbtb40 Zfp46 Zfp641 Egr1 Etv5 Hsf5 Nr4a3 Sox8""".split()
enr = """Mas1 Rxfp1 Gpr68 Mchr1 Grm8 Cckbr Chrm1 Gpr26 Adra1a Gpr12 Gpr3 Hcrtr2 Hrh3""".split()

# full TF list from jesse file
tf = pd.read_csv(
    Path(r"C:\Users\hsollim\Downloads\Gene_lists\OpioidDependenceDEG_genesets_forHansol090926\mPFC_TFDEGs.csv")
).gene.astype(str).tolist()


def report(name, genes):
    on, off, free = [], [], []
    seen = set()
    for g in genes:
        if g in seen:
            continue
        seen.add(g)
        if g in sh:
            on.append(g)
        elif g in base:
            free.append(g)
            off.append(g)
        else:
            off.append(g)
    print(f"\n==== {name}  n={len(seen)}  ON={len(on)}  OFF={len(off)}  (off but FREE on base={len(free)})")
    print("ON SHARED:", ", ".join(on) if on else "(none)")
    print("OFF:", ", ".join(off) if off else "(none)")
    if free:
        print("  among OFF, FREE on Xenium base:", ", ".join(free))


report("IEG DEG", ieg)
report("Synaptic plasticity", syn)
report("GPCR DEG", gpcr)
report("TF wide only", tf_wide)
report("TF all 179", tf)
report("ORB enriched GPCR top", enr)

# unique across IEG+syn+gpcr+enr
allg = []
for lst in (ieg, syn, gpcr, enr, tf):
    allg.extend(lst)
print("\n==== unique across all listed ====")
u = list(dict.fromkeys(allg))
on = [g for g in u if g in sh]
print(f"unique genes {len(u)}  on shared {len(on)}  off {len(u)-len(on)}")
