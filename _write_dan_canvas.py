"""Write combined Jesse + Dan + panel-decision canvas."""
from pathlib import Path
import json

DAN = json.loads(
    Path(r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs\_dan_canvas.json").read_text(
        encoding="utf-8"
    )
)
OUT = Path(
    r"C:\Users\hsollim\.cursor\projects\c-Users-hsollim-Desktop-cursor\canvases\jesse-dan-xenium-panel.canvas.tsx"
)

header = r'''import {
  BarChart,
  Callout,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasState,
} from "cursor/canvas";

type DanGene = {
  g: string;
  on: string;
  pct: number | null;
  spec: number | null;
  top: string;
  fate: string;
};

const DAN: DanGene[] = '''

footer = r''';

const FATE_LABEL: Record<string, string> = {
  on_panel: "Already on panel (38)",
  added_14: "Added from Dan (14)",
  weak: "In BMAp, not specific (23)",
  low_cea: "Low / CEA / glia (20)",
  unscored: "Not scored (3)",
};

function fateTone(f: string): "success" | "info" | "warning" | "danger" | "neutral" {
  if (f === "on_panel") return "success";
  if (f === "added_14") return "info";
  if (f === "weak") return "warning";
  if (f === "low_cea") return "danger";
  return "neutral";
}

const ADDED = DAN.filter((r) => r.fate === "added_14");

export default function JesseDanXeniumPanel() {
  const [tab, setTab] = useCanvasState("jd.tab", "added_14");
  const [q, setQ] = useCanvasState("jd.q", "");

  const filtered = DAN.filter((r) => (tab === "all" ? true : r.fate === tab)).filter((r) => {
    const qq = q.trim().toLowerCase();
    if (!qq) return true;
    return r.g.toLowerCase().includes(qq) || r.top.toLowerCase().includes(qq);
  });

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Jesse + Dan → Xenium panel decision</H1>
        <Text tone="secondary">
          ORBm (Jesse morphine DEGs) and BMAp (Dan GSE283418 spatial 98-gene panel), mapped onto the
          current MSGS111 shared add-on.
        </Text>
      </Stack>

      <Callout tone="info" title="Decision">
        Keep the original 144. Dan 14 are already appended on MSGS111 (158 genes / 114 custom).
        Jesse is not on the order sheet yet — add Rxfp1 (free) plus Per2, Pcsk1, Per1 if the
        experiment should read a morphine-dependence state in ORBm.
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="144" label="Original curated shared" />
        <Stat value="14" label="Dan added (done)" tone="info" />
        <Stat value="38" label="Dan 98 already overlapping" tone="success" />
        <Stat value="6–8" label="Jesse proposed (open)" tone="warning" />
      </Grid>

      <H2>Dan GSE283418 — 98 spatial genes</H2>
      <Text tone="secondary" size="small">
        Source: Berg / Scherrer Resolve Molecular Cartography (GPL35157) vs our shared panel, then
        re-scored in Allen BMAp-mapped subclasses. RAW 8.3 GB images were not downloaded.
      </Text>
      <BarChart
        categories={["On panel", "Added 14", "Not specific", "Low / CEA", "Unscored"]}
        series={[{ name: "Dan 98-gene panel", data: [38, 14, 23, 20, 3] }]}
        height={220}
        showValues
      />

      <H3>14 Dan genes now on MSGS111 (ranks 145–158)</H3>
      <Text size="small" tone="secondary">
        Lamb3 is the closest true BMAp gene (113 Ccdc42). Cck / Col23a1 sit on the 012 VGLUT1 border.
        Several others are MEA or CEA neighbors.
      </Text>
      <BarChart
        horizontal
        categories={ADDED.map((r) => r.g)}
        series={[{ name: "Detection in top BMAp-mapped subclass (%)", data: ADDED.map((r) => r.pct ?? 0) }]}
        height={380}
        showValues
        valueSuffix="%"
      />
      <Table
        headers={["Gene", "% cells", "Spec", "Top Allen subclass in BMAp ROI"]}
        rows={ADDED.map((r) => [r.g, r.pct == null ? "—" : String(r.pct), r.spec == null ? "—" : String(r.spec), r.top])}
        columnAlign={["left", "right", "right", "left"]}
        striped
      />

      <H2>Jesse PL–ILA–ORB — morphine DEGs</H2>
      <Text>
        5-day escalating morphine, DESeq2 padj 0.1. IEG 77 (58 Up), TF 179, plasticity 45, GPCR DEG 34,
        plus 127 ORB-enriched GPCRs. Hottest cells: 004 L6 IT, 030 L6 CT, 006 L4/5 IT, 022 L5 ET.
      </Text>
      <Grid columns={2} gap={16}>
        <Stack gap={6}>
          <H3>Widest missing IEG DEGs (ORBm clusters)</H3>
          <BarChart
            horizontal
            categories={["Per2", "Pcsk1", "Per1", "Nr4a3", "Dusp1", "Egr3", "Crem"]}
            series={[{ name: "ORBm DE clusters", data: [11, 9, 8, 5, 6, 5, 5], tone: "info" }]}
            height={260}
            showValues
          />
        </Stack>
        <Stack gap={6}>
          <H3>Widest missing enriched GPCRs</H3>
          <BarChart
            horizontal
            categories={["Rxfp1", "Mas1", "Mchr1", "Adra1a", "Gpr68", "Grm8"]}
            series={[{ name: "Enriched subclasses", data: [19, 17, 14, 14, 13, 9] }]}
            height={260}
            showValues
          />
        </Stack>
      </Grid>
      <Callout tone="success" title="Already covered from Jesse">
        Fos, Arc, Egr1, Junb, Nr4a1, Nr4a2, Fosb, Npas4, Bdnf, Oprm1, Oprd1, Oprk1, Oprl1, Ntsr1,
        Grm5, Htr1b, Chrm2. His top activity IEGs match the TRAP genes we already chose.
      </Callout>

      <Divider />

      <H2>What goes on the probe panel</H2>
      <Table
        headers={["Status", "Genes", "Source", "Slot"]}
        rows={[
          ["KEEP", "Original 144 (Fos Arc Egr1 Oprm1 Ntsr1 + cell-type separators)", "Allen + literature", "100 custom + 44 free"],
          ["ADDED", "Lamb3, Cck, Col23a1, Slc29a4, Abca8a, Dnah5, Calcrl, Nos1, Oprl1, Gfra1, Sp8, Syndig1l, Gabre, Tspan18", "Dan GSE283418", "14 custom (now on MSGS111)"],
          ["PROPOSED", "Rxfp1", "Jesse enriched GPCR", "FREE on base"],
          ["PROPOSED", "Per2, Pcsk1, Per1", "Jesse IEG DEG", "3 custom"],
          ["PROPOSED", "Nr4a3, Dusp1, Egr3", "Jesse IEG", "3 custom"],
          ["OPTIONAL", "Mas1 or Gpr68; Hrh1; Grm2", "Jesse GPCR / plasticity", "3–4 custom"],
          ["DO NOT ADD", "Dan CEA/glia (Adora2a, Prkcd, Ptprc, S100b) and most Jesse TFs", "Both", "—"],
        ]}
        rowTone={["neutral", "info", "success", "warning", "warning", "warning", "danger"]}
        striped
      />

      <H2>All 98 Dan genes</H2>
      <Row gap={8} wrap>
        <Pill active={tab === "all"} onClick={() => setTab("all")}>
          All 98
        </Pill>
        <Pill active={tab === "added_14"} onClick={() => setTab("added_14")}>
          {FATE_LABEL.added_14}
        </Pill>
        <Pill active={tab === "on_panel"} onClick={() => setTab("on_panel")}>
          {FATE_LABEL.on_panel}
        </Pill>
        <Pill active={tab === "weak"} onClick={() => setTab("weak")}>
          {FATE_LABEL.weak}
        </Pill>
        <Pill active={tab === "low_cea"} onClick={() => setTab("low_cea")}>
          {FATE_LABEL.low_cea}
        </Pill>
      </Row>
      <Row gap={8} align="center">
        <TextInput value={q} onChange={setQ} placeholder="Search gene or subclass" />
        <Text size="small" tone="tertiary">
          {filtered.length} genes
        </Text>
      </Row>
      <Table
        headers={["Gene", "Fate", "% cells", "Spec", "Top BMAp-mapped subclass"]}
        rows={filtered.map((r) => [
          r.g,
          FATE_LABEL[r.fate] ?? r.fate,
          r.pct == null ? "—" : String(r.pct),
          r.spec == null ? "—" : String(r.spec),
          r.top || "—",
        ])}
        rowTone={filtered.map((r) => fateTone(r.fate))}
        columnAlign={["left", "left", "right", "right", "left"]}
        striped
        stickyHeader
        style={{ maxHeight: 480 }}
      />
    </Stack>
  );
}
'''

OUT.write_text(header + json.dumps(DAN, ensure_ascii=False) + footer, encoding="utf-8")
print("wrote", OUT, OUT.stat().st_size)
