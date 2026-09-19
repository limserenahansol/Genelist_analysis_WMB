"""Write the Jesse ORB canvas with embedded gene data."""
from pathlib import Path
import json

DATA = json.loads(
    Path(r"c:\Users\hsollim\Desktop\cursor\Genelist_analysis_WMB\v3\outputs\_jesse_canvas_data.json").read_text(
        encoding="utf-8"
    )
)
OUT = Path(
    r"C:\Users\hsollim\.cursor\projects\c-Users-hsollim-Desktop-cursor\canvases\jesse-orb-gene-lists.canvas.tsx"
)

header = r'''import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Select,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasState,
} from "cursor/canvas";

type Deg = { g: string; set: string; n: number; d: string; o: number; c: string };
type Enr = { g: string; n: number };

const DATA: {
  IEG: Deg[];
  TF: Deg[];
  SynPlast: Deg[];
  GPCR_DEG: Deg[];
  glut: Enr[];
  gaba: Enr[];
} = '''

footer = r''';

const LIST_LABEL: Record<string, string> = {
  IEG: "IEG DEG (77)",
  TF: "TF DEG (179)",
  SynPlast: "시냅스 가소성 DEG (45)",
  GPCR_DEG: "GPCR DEG (34)",
  glut: "Glut 농축 GPCR (80)",
  gaba: "GABA 농축 GPCR (99)",
};

function dirTone(d: string): "success" | "danger" | "warning" | "neutral" {
  if (d === "Up") return "success";
  if (d === "Down") return "danger";
  if (d === "Mixed") return "warning";
  return "neutral";
}

function topIeg() {
  return DATA.IEG.slice(0, 12);
}

function iegSubclassHits() {
  const hits: Record<string, number> = {};
  for (const row of DATA.IEG) {
    for (const part of row.c.split(";")) {
      const lab = part.trim();
      if (lab) hits[lab] = (hits[lab] ?? 0) + 1;
    }
  }
  return Object.entries(hits).sort((a, b) => b[1] - a[1]);
}

function shortCluster(lab: string) {
  const tok = lab.split(" ")[0];
  const rest = lab
    .split(" ")
    .slice(1)
    .join(" ")
    .replace(" CTX Glut", "")
    .replace(" Gaba", "g")
    .replace(" IT ", " ");
  return tok + " " + rest;
}

function mergedGpcr(): Array<{ g: string; glut: number; gaba: number; tot: number }> {
  const map = new Map<string, { glut: number; gaba: number }>();
  for (const r of DATA.glut) {
    map.set(r.g, { glut: r.n, gaba: map.get(r.g)?.gaba ?? 0 });
  }
  for (const r of DATA.gaba) {
    const prev = map.get(r.g) ?? { glut: 0, gaba: 0 };
    map.set(r.g, { glut: prev.glut, gaba: r.n });
  }
  return [...map.entries()]
    .map(([g, v]) => ({ g, glut: v.glut, gaba: v.gaba, tot: v.glut + v.gaba }))
    .sort((a, b) => b.tot - a.tot);
}

function degRows(list: Deg[], q: string, dir: string) {
  const qq = q.trim().toLowerCase();
  return list
    .filter((r) => (dir === "all" ? true : r.d === dir))
    .filter((r) =>
      qq === ""
        ? true
        : r.g.toLowerCase().includes(qq) || r.c.toLowerCase().includes(qq) || r.set.toLowerCase().includes(qq),
    )
    .map((r) => [r.g, r.set, String(r.n), r.d, String(r.o), r.c]);
}

export default function JesseOrbGeneLists() {
  const [tab, setTab] = useCanvasState("jesse.tab", "IEG");
  const [q, setQ] = useCanvasState("jesse.q", "");
  const [dir, setDir] = useCanvasState("jesse.dir", "all");

  const iegHits = iegSubclassHits();
  const gpcr = mergedGpcr();
  const iegTop = topIeg();

  const degTab = tab === "IEG" || tab === "TF" || tab === "SynPlast" || tab === "GPCR_DEG";
  const currentDeg = degTab ? DATA[tab as "IEG" | "TF" | "SynPlast" | "GPCR_DEG"] : [];
  const currentEnr = tab === "glut" ? DATA.glut : tab === "gaba" ? DATA.gaba : [];

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Jesse PL–ILA–ORB 모르핀 의존 유전자</H1>
        <Text tone="secondary">
          Jesse Niehaus · 5일 escalating morphine · DESeq2 슈도벌크 padj ≤ 0.1 · Allen subclass
        </Text>
      </Stack>

      <Callout tone="info" title="한 줄 결론">
        이건 세포 타입 마커가 아니라, 모르핀 의존 때 PL–ILA–ORB에서 같이 켜지는 상태 시그니처다.
        핵심은 Fos / Arc / Egr1 / Junb / Nr4a1 같은 고전 IEG가 여러 ORBm 흥분 세포에서 올라가고,
        그 위에 Per2 / Pcsk1 / Per1 같은 delayed IEG가 더 넓게 올라간다.
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value="77" label="IEG DEG" />
        <Stat value="179" label="전사인자 DEG" />
        <Stat value="45" label="시냅스 가소성 DEG" />
        <Stat value="34" label="GPCR DEG" />
      </Grid>
      <Grid columns={4} gap={12}>
        <Stat value="304" label="DEG 고유 유전자" />
        <Stat value="213" label="Up (리스트 합)" tone="success" />
        <Stat value="115" label="Down (리스트 합)" tone="danger" />
        <Stat value="127" label="ORB 농축 GPCR" />
      </Grid>

      <H2>데이터가 말하는 것</H2>
      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>무엇을 측정했나</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                전전두/안와피질(PL–ILA–ORB) subclass를 슈도벌크로 묶어, 5일 모르핀 의존 vs 대조에서
                차등발현 유전자를 뽑았다. 리스트는 기능별로 네 장이다.
              </Text>
              <Text>
                IEG는 빠른/늦은 활성 유전자(rPRG, dPRG, SRG), TF는 마우스 전사인자, 가소성은
                GO:0048167, GPCR은 마우스 GPCR 세트다.
              </Text>
              <Text>
                별도로 Allen 400만 세포 대비 PL–ILA–ORB에 농축된 GPCR을 Fisher exact (BH FDR ≤ 0.05,
                ≥5% 세포, enrichment ≥ 1.5)로 뽑았다. 이건 모르핀 반응이 아니라 ORB에 원래 많은 수용체다.
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>생물학적으로 중요한 패턴</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                IEG 77개 중 58개가 Up이다. 변화가 가장 많은 세포는 004 L6 IT, 030 L6 CT, 006 L4/5 IT,
                022 L5 ET — 즉 ORBm의 주요 흥분 세포다. GABA(Pvalb/Vip/Sst)는 더 적다.
              </Text>
              <Text>
                제일 넓은 IEG는 Per2(13 subclass), Pcsk1(11), Arc/Fos(10), Egr1/Junb/Nr4a1/Per1(8)이다.
                가소성에서는 Arc, Fxr1, Vps13a가 올라가고 Camk2g는 내려간다.
              </Text>
              <Text>
                GPCR DEG는 방향이 갈린다. Hrh1/Grm5는 Up, Grm2/Adra1a/Ntsr1은 Down.
                Oprm1은 Pvalb에서만 Up로 잡혔다. 반대로 농축 GPCR의 1등은 Rxfp1, Mas1, Gpr68, Mchr1이다.
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <H2>그림 1. 리스트 크기와 방향</H2>
      <Text tone="secondary" size="small">
        Source: Jesse DEG CSVs · 5-day morphine · padj ≤ 0.1. 같은 유전자가 여러 리스트에 중복될 수 있음 (28개).
      </Text>
      <Grid columns={2} gap={16}>
        <Stack gap={6}>
          <H3>유전자 수 (리스트별)</H3>
          <BarChart
            categories={["IEG", "TF", "가소성", "GPCR"]}
            series={[{ name: "유전자 수", data: [77, 179, 45, 34] }]}
            height={220}
            showValues
          />
        </Stack>
        <Stack gap={6}>
          <H3>방향 (Up / Down / Mixed)</H3>
          <BarChart
            categories={["IEG", "TF", "가소성", "GPCR"]}
            series={[
              { name: "Up", data: [58, 107, 34, 14], tone: "success" },
              { name: "Down", data: [15, 72, 10, 18], tone: "danger" },
              { name: "Mixed", data: [4, 0, 1, 2], tone: "warning" },
            ]}
            stacked
            height={220}
          />
        </Stack>
      </Grid>

      <H2>그림 2. 가장 넓은 IEG DEG</H2>
      <Text tone="secondary" size="small">
        X축: 차등발현된 Allen subclass 수. Per2·Pcsk1이 Fos/Arc보다 더 많은 세포 타입에서 올라간다.
      </Text>
      <BarChart
        horizontal
        categories={iegTop.map((r) => r.g)}
        series={[{ name: "DE subclass 수", data: iegTop.map((r) => r.n), tone: "info" }]}
        height={360}
        showValues
        valueSuffix=" clusters"
      />

      <H2>그림 3. IEG가 바뀐 세포 타입</H2>
      <Text tone="secondary" size="small">
        각 subclass에서 IEG DEG가 몇 개나 잡혔는지. L6 IT / L6 CT / L4/5 IT가 모르핀 IEG 반응의 중심이다.
      </Text>
      <BarChart
        horizontal
        categories={iegHits.map(([lab]) => shortCluster(lab))}
        series={[{ name: "IEG DEG 수", data: iegHits.map(([, n]) => n) }]}
        height={420}
        showValues
      />

      <H2>그림 4. PL–ILA–ORB 농축 GPCR (상위 16)</H2>
      <Text tone="secondary" size="small">
        Source: Fisher vs rest of 4M-cell atlas · BH FDR ≤ 0.05 · ≥5% cells · enrichment ≥ 1.5.
        막대는 Glut subclass + GABA subclass 농축 횟수의 합.
      </Text>
      <BarChart
        horizontal
        categories={gpcr.slice(0, 16).map((r) => r.g)}
        series={[
          { name: "Glut 농축 subclass", data: gpcr.slice(0, 16).map((r) => r.glut), tone: "info" },
          { name: "GABA 농축 subclass", data: gpcr.slice(0, 16).map((r) => r.gaba), tone: "neutral" },
        ]}
        stacked
        height={420}
      />

      <Divider />

      <H2>전체 유전자 표</H2>
      <Text>
        아래 탭에서 리스트를 고르고 유전자 이름 또는 클러스터로 검색하면 된다. n = DE subclass 수,
        ORBm = 우리 ORBm 앵커(004–007, 022, 029, 030, 032, 046, 049, 052, 053)에서 DE인 수.
      </Text>
      <Row gap={8} wrap>
        {["IEG", "TF", "SynPlast", "GPCR_DEG", "glut", "gaba"].map((k) => (
          <Pill key={k} active={tab === k} onClick={() => setTab(k)}>
            {LIST_LABEL[k]}
          </Pill>
        ))}
      </Row>
      <Row gap={8} align="center">
        <TextInput value={q} onChange={setQ} placeholder="유전자 또는 클러스터 검색" />
        {degTab ? (
          <Select
            value={dir}
            onChange={setDir}
            options={[
              { value: "all", label: "모든 방향" },
              { value: "Up", label: "Up" },
              { value: "Down", label: "Down" },
              { value: "Mixed", label: "Mixed" },
            ]}
          />
        ) : null}
        <Text size="small" tone="tertiary">
          {degTab
            ? `${degRows(currentDeg, q, dir).length} / ${currentDeg.length}`
            : `${currentEnr.filter((r) => r.g.toLowerCase().includes(q.trim().toLowerCase())).length} / ${currentEnr.length}`}
        </Text>
      </Row>

      {degTab ? (
        <Table
          headers={["유전자", "세트", "n DE", "방향", "ORBm", "DE subclass"]}
          rows={degRows(currentDeg, q, dir)}
          rowTone={degRows(currentDeg, q, dir).map((r) => dirTone(String(r[3])))}
          columnAlign={["left", "left", "right", "left", "right", "left"]}
          striped
          stickyHeader
          style={{ maxHeight: 520 }}
        />
      ) : (
        <Table
          headers={["GPCR", "농축 subclass 수"]}
          rows={currentEnr
            .filter((r) => r.g.toLowerCase().includes(q.trim().toLowerCase()))
            .map((r) => [r.g, String(r.n)])}
          columnAlign={["left", "right"]}
          striped
          stickyHeader
          style={{ maxHeight: 520 }}
        />
      )}

      <H2>리스트별 전체 유전자 이름</H2>
      <CollapsibleSection title="IEG DEG" count={DATA.IEG.length} defaultOpen>
        <Text size="small">{DATA.IEG.map((r) => r.g).join(", ")}</Text>
      </CollapsibleSection>
      <CollapsibleSection title="시냅스 가소성 DEG" count={DATA.SynPlast.length}>
        <Text size="small">{DATA.SynPlast.map((r) => r.g).join(", ")}</Text>
      </CollapsibleSection>
      <CollapsibleSection title="GPCR DEG" count={DATA.GPCR_DEG.length}>
        <Text size="small">{DATA.GPCR_DEG.map((r) => r.g).join(", ")}</Text>
      </CollapsibleSection>
      <CollapsibleSection title="전사인자 DEG" count={DATA.TF.length}>
        <Text size="small">{DATA.TF.map((r) => r.g).join(", ")}</Text>
      </CollapsibleSection>
      <CollapsibleSection title="Glut 농축 GPCR" count={DATA.glut.length}>
        <Text size="small">{DATA.glut.map((r) => `${r.g}(${r.n})`).join(", ")}</Text>
      </CollapsibleSection>
      <CollapsibleSection title="GABA 농축 GPCR" count={DATA.gaba.length}>
        <Text size="small">{DATA.gaba.map((r) => `${r.g}(${r.n})`).join(", ")}</Text>
      </CollapsibleSection>

      <Callout tone="neutral" title="패널에 이미 있는 핵심">
        Fos, Arc, Egr1, Junb, Nr4a1, Nr4a2, Fosb, Npas4, Bdnf, Oprm1, Oprd1, Oprk1, Ntsr1, Grm5,
        Htr1b, Chrm2 는 현재 SHARED 패널에 있다. Jesse 데이터는 이 선택을 지지하고,
        추가로 Per2 / Pcsk1 / Per1 / Rxfp1 이 모르핀 상태 레이어가 된다.
      </Callout>
    </Stack>
  );
}
'''

OUT.write_text(header + json.dumps(DATA, ensure_ascii=False) + footer, encoding="utf-8")
print("wrote", OUT, "bytes", OUT.stat().st_size)
