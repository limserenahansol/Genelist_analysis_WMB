import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { FileBlob, Presentation, PresentationFile } from "@oai/artifact-tool";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const workspaceDir = path.resolve(process.env.PIPELINE_WORKSPACE ?? scriptDir);
const userHome = process.env.USERPROFILE ?? process.env.HOME;
if (!userHome) throw new Error("USERPROFILE or HOME is required to locate the Codex runtime");
const SKILL_DIR = process.env.PRESENTATIONS_SKILL_DIR
  ?? path.join(userHome, ".codex", "plugins", "cache", "openai-primary-runtime", "presentations", "26.904.11930", "skills", "presentations");
const RUNTIME_PYTHON = process.env.RUNTIME_PYTHON
  ?? path.join(userHome, ".cache", "codex-runtimes", "codex-primary-runtime", "dependencies", "python", "python.exe");
const version = process.env.DECK_VERSION ?? "v1";
const buildDir = path.join(workspaceDir, ".ppt_build", version);
const outputDir = path.join(workspaceDir, "presentation");
const FINAL_PPTX = path.join(outputDir, `ORBm_BMAp_Xenium_pipeline_results_5slides_EN_${version}.pptx`);

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });

const { applyPresentationChartFont, finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href,
);

const W = 1280;
const H = 720;
const FONT = "Calibri";
const BLUE = "#1F4E79";
const BLUE2 = "#2E75B6";
const RED = "#C74334";
const TEXT = "#303030";
const GRAY = "#666666";
const LIGHT = "#E7E6E6";
const PALE = "#F4F1EB";
const WHITE = "#FFFFFF";

const asset = (...parts) => path.join(workspaceDir, ...parts);
const imageBytes = async (...parts) => new Uint8Array(await fs.readFile(asset(...parts)));

function addText(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: 18,
    color: TEXT,
    autoFit: "shrink",
    ...style,
  };
  return shape;
}

function addFrame(slide, title, subtitle, page, accent = BLUE) {
  slide.background.fill = WHITE;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: W, height: 10 },
    fill: accent,
    line: { fill: "none", width: 0 },
  });
  addText(slide, title, { left: 46, top: 24, width: 1188, height: 42 }, {
    fontSize: 32,
    bold: true,
    color: accent,
  });
  addText(slide, subtitle, { left: 46, top: 65, width: 1188, height: 30 }, {
    fontSize: 17.5,
    color: GRAY,
  });
  addText(slide, `Xenium ORBm + BMAp    Pipeline results    ${page}/5`,
    { left: 46, top: 687, width: 1188, height: 22 },
    { fontSize: 13.5, color: GRAY });
}

function addNumberedQuestion(slide, number, heading, detail, top) {
  addText(slide, number, { left: 48, top, width: 54, height: 38 }, {
    fontSize: 27,
    bold: true,
    color: BLUE2,
  });
  addText(slide, heading, { left: 112, top: top - 1, width: 505, height: 33 }, {
    fontSize: 21,
    bold: true,
    color: TEXT,
  });
  addText(slide, detail, { left: 112, top: top + 31, width: 505, height: 50 }, {
    fontSize: 16.5,
    color: GRAY,
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 48, top: top + 85, width: 570, height: 1 },
    fill: LIGHT,
    line: { fill: "none", width: 0 },
  });
}

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

// Slide 1
{
  const slide = presentation.slides.add();
  addFrame(
    slide,
    "Xenium pipeline: biological questions",
    "ORBm and BMAp pilot validation. Cell identity comes first, followed by reporter and behavior comparisons.",
    1,
  );
  addText(slide, "Primary analysis", { left: 48, top: 112, width: 570, height: 31 }, {
    fontSize: 20,
    bold: true,
    color: BLUE,
  });
  addNumberedQuestion(
    slide,
    "01",
    "Known cell type or reproducible new cluster?",
    "Annotate cells with identity markers while excluding reporter and activity genes from the identity PCA.",
    158,
  );
  addNumberedQuestion(
    slide,
    "02",
    "Which known types contain more tdTom+ cells?",
    "Estimate enrichment per animal before testing whether reporter-positive cells form an unexplained, stable subtype.",
    278,
  );
  addNumberedQuestion(
    slide,
    "03",
    "Which genes differ by reporter status and behavior?",
    "Compare GPCR, TF and plasticity programs within each cell type using animal-level pseudobulk contrasts.",
    398,
  );
  const spatial = await imageBytes("outputs", "orbm_right", "figures", "03_umap.png");
  slide.images.add({
    blob: spatial,
    contentType: "image/png",
    alt: "Real ORBm pilot UMAP by Leiden cluster and marker module",
    fit: "contain",
    position: { left: 642, top: 170, width: 594, height: 252 },
  });
  addText(slide, "REAL PILOT: ORBm UMAP", { left: 858, top: 130, width: 250, height: 28 }, {
    fontSize: 14,
    bold: true,
    color: BLUE,
    alignment: "center",
  });
  addText(slide, "Current pilot: 247 measured genes; tdTomato absent; one animal per anatomy.",
    { left: 48, top: 540, width: 1180, height: 40 },
    { fontSize: 19, bold: true, color: RED });
  addText(slide, "The pilot can validate cell identity and detection. It cannot test tdTom specificity or Active versus Passive effects.",
    { left: 48, top: 582, width: 1180, height: 48 },
    { fontSize: 18, color: TEXT });
  slide.speakerNotes.textFrame.setText(
    "Sources: outputs/orbm_right/summary.json; outputs/orbm_right/figures/03_umap.png; PRIMARY_AIM_ANALYSIS.md. The displayed UMAP is real pilot data.",
  );
}

// Slide 2
{
  const slide = presentation.slides.add();
  addFrame(
    slide,
    "Story 1: cell identity in the real pilot",
    "Reference-aware annotation uses identity genes only. Reporter and activity genes do not drive the cell identity PCA.",
    2,
  );

  const orbmCats = ["L2/3", "Unassigned", "L5", "GABAergic", "Endothelial"];
  const orbmVals = [34.4, 24.6, 9.8, 8.6, 6.5];
  const bmapCats = ["GABAergic", "Unassigned", "Glutamatergic", "Oligo", "OPC"];
  const bmapVals = [29.3, 25.3, 18.9, 6.4, 4.9];

  const chartCommon = {
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 45 },
    hasLegend: false,
    xAxis: {
      textStyle: { typeface: FONT, fontSize: 13, fill: TEXT },
      line: { style: "solid", fill: "#A6A6A6", width: 1 },
    },
    yAxis: {
      min: 0,
      max: 40,
      majorUnit: 10,
      numberFormatCode: "0",
      textStyle: { typeface: FONT, fontSize: 12, fill: GRAY },
      majorGridlines: { style: "solid", fill: "#D9D9D9", width: 1 },
      line: { style: "solid", fill: "#A6A6A6", width: 1 },
    },
    dataLabels: {
      showValue: true,
      position: "outEnd",
      textStyle: { typeface: FONT, fontSize: 13, fill: TEXT, bold: true },
    },
    chartFill: WHITE,
    chartLine: { fill: "none", width: 0 },
    plotAreaFill: WHITE,
    plotAreaLine: { fill: "none", width: 0 },
  };

  const chart1 = slide.charts.add("bar", {
    ...chartCommon,
    position: { left: 44, top: 122, width: 572, height: 400 },
    title: "ORBm composition (n = 914)",
    titleTextStyle: { typeface: FONT, fontSize: 20, bold: true, fill: BLUE },
    categories: orbmCats,
    series: [{ name: "Cells in ROI (%)", values: orbmVals, fill: "#2F75A1", valuesFormatCode: "0.0" }],
  });
  applyPresentationChartFont(chart1, { fontFamily: FONT });

  const chart2 = slide.charts.add("bar", {
    ...chartCommon,
    position: { left: 664, top: 122, width: 572, height: 400 },
    title: "BMAp composition (n = 1,077)",
    titleTextStyle: { typeface: FONT, fontSize: 20, bold: true, fill: BLUE },
    categories: bmapCats,
    series: [{ name: "Cells in ROI (%)", values: bmapVals, fill: "#70AD47", valuesFormatCode: "0.0" }],
  });
  applyPresentationChartFont(chart2, { fontFamily: FONT });

  addText(slide, "Allen/reference concordance", { left: 56, top: 548, width: 300, height: 28 }, {
    fontSize: 18,
    bold: true,
    color: BLUE,
  });
  addText(slide, "NMI 0.738 in ORBm and 0.673 in BMAp. ARI is approximately 0.50 in both regions.",
    { left: 56, top: 578, width: 560, height: 52 }, { fontSize: 17, color: TEXT });
  addText(slide, "Interpretation", { left: 674, top: 548, width: 250, height: 28 }, {
    fontSize: 18,
    bold: true,
    color: BLUE,
  });
  addText(slide, "Broad classes are interpretable, but unassigned cells remain 24.6% in ORBm and 25.3% in BMAp.",
    { left: 674, top: 578, width: 548, height: 52 }, { fontSize: 17, color: TEXT });
  slide.speakerNotes.textFrame.setText(
    "Sources: outputs/orbm_right/summary.json and outputs/bmap_left/summary.json. Composition values are calculated from module_counts divided by n_after_qc. These are real pilot results.",
  );
}

// Slide 3
{
  const slide = presentation.slides.add();
  addFrame(
    slide,
    "Story 2: tdTom enrichment within existing cell types",
    "Simulated demonstration because tdTomato is absent from the pilot matrix. The real analysis will use the same outputs.",
    3,
  );
  const overlap = await imageBytes("toy_demo_results", "story2_toy_reporter_overlap.png");
  const enrichment = await imageBytes("toy_demo_results", "story2_toy_celltype_enrichment.png");
  slide.images.add({
    blob: overlap,
    contentType: "image/png",
    alt: "Simulated tdTom spatial overlap and reporter rate by known cell type",
    fit: "contain",
    position: { left: 34, top: 108, width: 724, height: 380 },
  });
  slide.images.add({
    blob: enrichment,
    contentType: "image/png",
    alt: "Simulated animal-level cell type enrichment in tdTom positive versus negative cells",
    fit: "contain",
    position: { left: 770, top: 108, width: 476, height: 438 },
  });
  addText(slide, "Expected real interpretation", { left: 48, top: 508, width: 300, height: 29 }, {
    fontSize: 19,
    bold: true,
    color: BLUE,
  });
  addText(slide,
    "Calibrate the reporter threshold with controls. Estimate enrichment for each animal. Claim a new type only when a stable tdTom-associated cluster remains unexplained by reference subtypes and reproduces across animals.",
    { left: 48, top: 542, width: 700, height: 98 },
    { fontSize: 17, color: TEXT });
  addText(slide, "SIMULATED OUTPUT", { left: 916, top: 567, width: 220, height: 30 }, {
    fontSize: 17,
    bold: true,
    color: RED,
    alignment: "center",
  });
  addText(slide, "Toy data were designed to enrich tdTom+ cells in L5 and GABA classes.",
    { left: 806, top: 603, width: 404, height: 42 }, { fontSize: 15.5, color: GRAY, alignment: "center" });
  slide.speakerNotes.textFrame.setText(
    "Sources: toy_demo_results/story2_toy_reporter_overlap.png and toy_demo_results/story2_toy_celltype_enrichment.png. These are simulated toy data and are not biological results. Real pilot status: outputs/story2_tdtom/SKIPPED.md.",
  );
}

// Slide 4
{
  const slide = presentation.slides.add();
  addFrame(
    slide,
    "Story 3: reporter and condition effects",
    "Simulated animal-level pseudobulk output. Five planned contrasts separate reporter, condition and interaction effects.",
    4,
  );
  const heatmap = await imageBytes("toy_demo_results", "factorial_toy_gene_effects.png");
  slide.images.add({
    blob: heatmap,
    contentType: "image/png",
    alt: "Simulated animal-level pseudobulk effects for GPCR, activity and transcription factor genes",
    fit: "contain",
    position: { left: 28, top: 105, width: 790, height: 555 },
  });
  addText(slide, "Planned contrasts", { left: 844, top: 125, width: 355, height: 35 }, {
    fontSize: 22,
    bold: true,
    color: BLUE,
  });
  const contrasts = [
    ["01", "tdTom+ vs tdTom− within Active"],
    ["02", "tdTom+ vs tdTom− within Passive"],
    ["03", "Active vs Passive within tdTom+"],
    ["04", "Active vs Passive within tdTom−"],
    ["05", "Reporter-by-condition interaction"],
  ];
  contrasts.forEach(([n, label], index) => {
    const top = 177 + index * 70;
    addText(slide, n, { left: 844, top, width: 42, height: 30 }, {
      fontSize: 18,
      bold: true,
      color: RED,
    });
    addText(slide, label, { left: 894, top: top - 1, width: 330, height: 48 }, {
      fontSize: 17,
      color: TEXT,
    });
  });
  addText(slide, "Animal is the experimental unit", { left: 844, top: 550, width: 360, height: 32 }, {
    fontSize: 19,
    bold: true,
    color: BLUE,
  });
  addText(slide, "Toy values show effect size only. Real output adds confidence intervals and FDR.",
    { left: 844, top: 590, width: 366, height: 58 }, { fontSize: 16.5, color: RED });
  slide.speakerNotes.textFrame.setText(
    "Source: toy_demo_results/factorial_toy_gene_effects.png. The figure contains simulated toy data and is not a biological result. Real design requirement is described in outputs/story3_mouse_ab/DESCRIPTIVE_ONLY.md and design_status.json.",
  );
}

// Slide 5
{
  const slide = presentation.slides.add();
  addFrame(
    slide,
    "Final decision: pipeline ready, inference awaits the full design",
    "The pilot validates cell identity and detectability. It cannot answer the tdTom or Active and Passive questions.",
    5,
    RED,
  );
  const values = [
    ["Question", "Current pilot", "Real-data criterion", "Primary output"],
    ["Cell identity", "Runnable", "Stable labels across resolution and Allen reference checks", "Cell-type map and confidence"],
    ["tdTom specificity", "Blocked: reporter absent", "Custom tdTomato probe and calibrated control threshold", "Per-animal enrichment with 95% CI"],
    ["Active vs Passive", "Descriptive only", "At least 3 independent animals per condition within each anatomy", "Pseudobulk effect, CI and FDR"],
    ["Novel cell type", "No conclusion", "Reporter-associated cluster persists within known types and reproduces across animals", "New type only with stable subtype markers"],
  ];
  const table = slide.tables.add({
    rows: 5,
    columns: 4,
    left: 34,
    top: 120,
    width: 1212,
    height: 430,
    columnWidths: [220, 245, 430, 317],
    values,
  });
  table.borders.assign({ style: "solid", fill: "#808080", width: 1 });
  table.rows[0].height = 68;
  for (let row = 1; row < 5; row += 1) table.rows[row].height = 90;
  for (let col = 0; col < 4; col += 1) {
    const header = table.getCell(0, col);
    header.fill = RED;
    header.text.style = { typeface: FONT, fontSize: 17, bold: true, color: WHITE };
  }
  for (let row = 1; row < 5; row += 1) {
    for (let col = 0; col < 4; col += 1) {
      const cell = table.getCell(row, col);
      cell.fill = row % 2 === 1 ? PALE : WHITE;
      cell.text.style = { typeface: FONT, fontSize: 15.5, color: TEXT, bold: col === 0 };
    }
  }
  addText(slide, "Current decision: analysis code is ready; biological conclusions remain pending.",
    { left: 48, top: 575, width: 1182, height: 38 }, { fontSize: 23, bold: true, color: RED });
  addText(slide, "Preferred minimum: at least 3 independent animals per condition within each anatomy. Animal is the experimental unit.",
    { left: 48, top: 620, width: 1182, height: 38 }, { fontSize: 16.5, color: TEXT });
  slide.speakerNotes.textFrame.setText(
    "Sources: PRIMARY_AIM_ANALYSIS.md; PIPELINE_REVIEW.md; outputs/story2_tdtom/SKIPPED.md; outputs/story3_mouse_ab/design_status.json. The minimum of three animals per condition is the pipeline readiness criterion, not a power calculation.",
  );
}

const requirements = {
  explicitTotalSlideCount: 5,
  requiredNativeChartOwnerSlides: [2],
  requiredNativeTableOwnerSlides: [5],
  requiredEmbeddedWorkbookChartOwnerSlides: [],
  materializeLiteralChartWorkbooks: true,
};
const fontPolicy = {
  basis: "design",
  families: [FONT],
};

const stagingDir = path.join(buildDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "5",
  ],
  requiredNativeChartOwnerSlides: [2],
  requiredNativeTableOwnerSlides: [5],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
});

const renderedDir = path.join(buildDir, "rendered_final");
await fs.mkdir(renderedDir, { recursive: true });
const finalDeck = await PresentationFile.importPptx(await FileBlob.load(FINAL_PPTX));
for (let i = 0; i < finalDeck.slides.items.length; i += 1) {
  const slide = finalDeck.slides.getItem(i);
  const png = await slide.export({ format: "png", scale: 1.5 });
  await fs.writeFile(path.join(renderedDir, `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderedDir, `slide-${i + 1}.layout.json`), await layout.text(), "utf8");
}
const montage = await finalDeck.export({ format: "webp", montage: true, scale: 0.8 });
await fs.writeFile(path.join(renderedDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));

console.log(JSON.stringify({ finalPath: FINAL_PPTX, validation: result, renderedDir }, null, 2));
