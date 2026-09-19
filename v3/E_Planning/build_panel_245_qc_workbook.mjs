import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "file:///C:/Users/hsollim/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const payloadPath = process.argv[2];
const outputPath = process.argv[3];
const previewDir = process.argv[4];
if (!payloadPath || !outputPath || !previewDir) {
  throw new Error("Usage: node build_panel_245_qc_workbook.mjs <payload.json> <output.xlsx> <preview-dir>");
}

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const wb = Workbook.create();
const COLORS = {
  navy: "#17365D",
  teal: "#0F766E",
  blue: "#2563EB",
  paleBlue: "#EAF2F8",
  paleTeal: "#E8F5F2",
  green: "#DCFCE7",
  greenText: "#166534",
  amber: "#FEF3C7",
  amberText: "#92400E",
  red: "#FEE2E2",
  redText: "#991B1B",
  gray: "#F1F5F9",
  border: "#CBD5E1",
  text: "#0F172A",
  white: "#FFFFFF",
};
const FONT = "Aptos";

function colName(oneBased) {
  let n = oneBased;
  let out = "";
  while (n > 0) {
    n -= 1;
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26);
  }
  return out;
}

function tableAddress(startRowZero, startColZero, rowCount, colCount) {
  const start = `${colName(startColZero + 1)}${startRowZero + 1}`;
  const end = `${colName(startColZero + colCount)}${startRowZero + rowCount}`;
  return `${start}:${end}`;
}

function baseSheet(sheet, tabColor) {
  sheet.showGridLines = false;
  sheet.tabColor = tabColor;
}

function titleBlock(sheet, endColumn, title, subtitle) {
  sheet.mergeCells(`A1:${endColumn}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${endColumn}1`).format = {
    fill: COLORS.navy,
    font: { name: FONT, size: 18, bold: true, color: COLORS.white },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${endColumn}1`).format.rowHeight = 30;
  sheet.mergeCells(`A2:${endColumn}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endColumn}2`).format = {
    fill: COLORS.paleBlue,
    font: { name: FONT, size: 10, italic: true, color: COLORS.text },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endColumn}2`).format.rowHeight = 34;
}

function styleHeader(range) {
  range.format = {
    fill: COLORS.teal,
    font: { name: FONT, size: 10, bold: true, color: COLORS.white },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: COLORS.border },
  };
  range.format.rowHeight = 34;
}

function writeDataTable(sheet, headerRowZero, headers, rows, tableName) {
  const width = headers.length;
  sheet.getRangeByIndexes(headerRowZero, 0, 1, width).values = [headers];
  if (rows.length) sheet.getRangeByIndexes(headerRowZero + 1, 0, rows.length, width).values = rows;
  const address = tableAddress(headerRowZero, 0, rows.length + 1, width);
  const table = sheet.tables.add(address, true, tableName);
  table.showFilterButton = true;
  const used = sheet.getRange(address);
  used.format.font = { name: FONT, size: 9, color: COLORS.text };
  used.format.verticalAlignment = "top";
  used.format.borders = { preset: "all", style: "thin", color: COLORS.border };
  styleHeader(sheet.getRangeByIndexes(headerRowZero, 0, 1, width));
  return { address, firstDataRow: headerRowZero + 2, lastDataRow: headerRowZero + rows.length + 1 };
}

function setWidths(sheet, widths, lastRow) {
  for (let i = 0; i < widths.length; i += 1) {
    sheet.getRange(`${colName(i + 1)}1:${colName(i + 1)}${lastRow}`).format.columnWidth = widths[i];
  }
}

// 1) Executive summary and workbook-level decision.
const summary = wb.worksheets.add("QC_SUMMARY");
baseSheet(summary, COLORS.navy);
titleBlock(
  summary,
  "J",
  payload.title,
  `Generated ${payload.generated}. The source 245-gene workbook is unchanged. This workbook documents pre-order technical QC and the remaining reporter-sequence blockers.`
);
summary.mergeCells("A4:J4");
summary.getRange("A4").values = [["BIOLOGICAL PANEL LOCKED AT 245 TARGETS — 243 STANDARD GENES PASS; 2 EXACT REPORTER FASTAs STILL REQUIRED"]];
summary.getRange("A4:J4").format = {
  fill: COLORS.amber,
  font: { name: FONT, size: 12, bold: true, color: COLORS.amberText },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "medium", color: "#D97706" },
};
summary.getRange("A4:J4").format.rowHeight = 38;

summary.getRange("A6:D6").values = [["Evidence area", "QC check", "Result", "Decision / interpretation"]];
summary.getRange("A7:D15").values = payload.summary_rows;
summary.tables.add("A6:D15", true, "SummaryEvidenceTable");
styleHeader(summary.getRange("A6:D6"));
summary.getRange("A7:D15").format = {
  font: { name: FONT, size: 9, color: COLORS.text },
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "all", style: "thin", color: COLORS.border },
};
summary.getRange("A7:D15").format.rowHeight = 54;

summary.getRange("G6:J6").values = [["Verification metric", "Observed", "Expected", "Check"]];
const verifyValues = [
  ["Total targets", null, 245, null],
  ["Standard mouse genes", null, 243, null],
  ["Advanced custom reporters", null, 2, null],
  ["10x standard-designable genes", null, 243, null],
  ["Current NCBI symbols", null, 243, null],
  ["Single-transcript genes", null, 40, null],
  ["Multi-transcript genes", null, 203, null],
  ["Allen high-prevalence genes", null, 185, null],
  ["Allen moderate-prevalence genes", null, 41, null],
  ["Allen low-prevalence genes", null, 14, null],
  ["Allen very-low-prevalence genes", null, 3, null],
  ["Anchors with zero passing genes", null, 0, null],
  ["Exact FASTA blockers", null, 2, null],
];
summary.getRange("G7:J19").values = verifyValues;
summary.getRange("H7:H19").formulas = [
  ["=COUNTA(PROBE_QC_245!$B$5:$B$249)"],
  ["=COUNTIF(PROBE_QC_245!$E$5:$E$249,\"STANDARD_MOUSE_GENE\")"],
  ["=COUNTIF(PROBE_QC_245!$E$5:$E$249,\"ADVANCED_EXOGENOUS\")"],
  ["=COUNTIF(PROBE_QC_245!$F$5:$F$249,\"PASS_V1_STANDARD_DESIGNABLE\")"],
  ["=COUNTIF(PROBE_QC_245!$H$5:$H$249,\"PASS_CURRENT_NCBI_SYMBOL\")"],
  ["=COUNTIF(PROBE_QC_245!$K$5:$K$249,1)"],
  ["=COUNTIF(PROBE_QC_245!$K$5:$K$249,\">1\")"],
  ["=COUNTIF(PROBE_QC_245!$Q$5:$Q$249,\"HIGH_ge50pct\")"],
  ["=COUNTIF(PROBE_QC_245!$Q$5:$Q$249,\"MODERATE_20-50pct\")"],
  ["=COUNTIF(PROBE_QC_245!$Q$5:$Q$249,\"LOW_5-20pct\")"],
  ["=COUNTIF(PROBE_QC_245!$Q$5:$Q$249,\"VERY_LOW_<5pct\")"],
  ["=COUNTIF(ALLEN_ANCHOR_COVERAGE!$C$5:$C$24,0)"],
  ["=COUNTIF(PROBE_QC_245!$S$5:$S$249,\"BLOCKED_EXACT_FASTA_REQUIRED\")"],
];
summary.getRange("J7:J19").formulas = Array.from({ length: 13 }, (_, i) => [`=IF(H${i + 7}=I${i + 7},\"PASS\",\"REVIEW\")`]);
summary.tables.add("G6:J19", true, "SummaryVerificationTable");
styleHeader(summary.getRange("G6:J6"));
summary.getRange("G7:J19").format = {
  font: { name: FONT, size: 9, color: COLORS.text },
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: COLORS.border },
};
summary.getRange("J7:J19").conditionalFormats.add("containsText", { text: "PASS", format: { fill: COLORS.green, font: { color: COLORS.greenText, bold: true } } });
summary.getRange("J7:J19").conditionalFormats.add("containsText", { text: "REVIEW", format: { fill: COLORS.red, font: { color: COLORS.redText, bold: true } } });

summary.mergeCells("A18:D18");
summary.getRange("A18").values = [["Required steps before purchase"]];
summary.getRange("A18:D18").format = { fill: COLORS.navy, font: { name: FONT, size: 11, bold: true, color: COLORS.white } };
summary.getRange("A19:D23").values = [
  [1, "Confirm colony records", "Verify Ai14 JAX 007914 and TRAP2 JAX 030323 are the actual alleles used.", "Strain IDs documented"],
  [2, "Obtain exact reporter sequences", "Get the exact Ai14 tdTomato and TRAP2 iCreERT2 sense-strand coding sequences.", "Two FASTA records, each >=80 bp"],
  [3, "Run Xenium Panel Designer", "Submit 243 standard genes plus the two exact custom sequences.", "All targets return a reviewable design result"],
  [4, "Review vendor output", "Check probe counts, warnings, transcript coverage, and optical-crowding guidance.", "No unresolved critical warning"],
  [5, "Freeze procurement version", "Record the final XPD export and order version; do not restart biological gene discovery.", "Order-ready file archived"],
];
summary.getRange("A19:D23").format = { font: { name: FONT, size: 9, color: COLORS.text }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: COLORS.border } };
summary.getRange("A19:A23").format.fill = COLORS.paleTeal;
summary.getRange("A19:A23").format.font = { name: FONT, size: 11, bold: true, color: COLORS.teal };
summary.getRange("A19:D23").format.rowHeight = 46;

summary.mergeCells("G22:J22");
summary.getRange("G22").values = [["Interpretation limits"]];
summary.getRange("G22:J22").format = { fill: COLORS.navy, font: { name: FONT, size: 11, bold: true, color: COLORS.white } };
summary.getRange("G23:J27").merge(true);
summary.getRange("G23:G27").values = [
  ["Allen expression prevalence is a biological reference proxy; it is not a probability that Xenium will detect a transcript."],
  ["A multi-transcript gene is acceptable for gene-level design. It does not prove that every isoform will be measured equally."],
  ["A stronger omitted marker does not require addition when the anchor already has several passing panel genes and the current biological scope is covered."],
  ["Reporter performance cannot be estimated until the exact construct sequences are supplied and evaluated in Xenium Panel Designer."],
  ["The final order still requires review of the vendor design report; 10x does not experimentally validate custom reporters before purchase."],
];
summary.getRange("G23:J27").format = { fill: COLORS.gray, font: { name: FONT, size: 9, color: COLORS.text }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: COLORS.border } };
summary.getRange("G23:J27").format.rowHeight = 40;
setWidths(summary, [15, 27, 27, 62, 3, 3, 31, 13, 12, 13], 30);
summary.freezePanes.freezeRows(4);

// 2) Full per-target QC.
const probe = wb.worksheets.add("PROBE_QC_245");
baseSheet(probe, COLORS.teal);
titleBlock(probe, "T", "Per-Target Probe, Symbol, Isoform, and Detectability QC", "Allen percentages are reference prevalence measures, not Xenium detection probabilities. Filter this table by status, tier, or selection block.");
writeDataTable(probe, 3, payload.qc_headers, payload.qc_rows, "ProbeQC245Table");
probe.freezePanes.freezeRows(4);
probe.freezePanes.freezeColumns(2);
setWidths(probe, [8, 12, 27, 42, 21, 28, 25, 25, 13, 16, 15, 33, 33, 17, 31, 17, 24, 53, 30, 48], 249);
probe.getRange("C5:D249").format.wrapText = true;
probe.getRange("L5:M249").format.wrapText = true;
probe.getRange("R5:T249").format.wrapText = true;
probe.getRange("N5:N249").format.numberFormat = "0.00";
probe.getRange("P5:P249").format.numberFormat = "0.00";
probe.getRange("N5:N249").conditionalFormats.add("dataBar", { color: COLORS.teal, thresholds: ["min", "max"], gradient: true });
probe.getRange("Q5:Q249").conditionalFormats.add("containsText", { text: "VERY_LOW", format: { fill: COLORS.red, font: { color: COLORS.redText, bold: true } } });
probe.getRange("Q5:Q249").conditionalFormats.add("containsText", { text: "LOW_5", format: { fill: COLORS.amber, font: { color: COLORS.amberText, bold: true } } });
probe.getRange("S5:S249").conditionalFormats.add("containsText", { text: "BLOCKED", format: { fill: COLORS.red, font: { color: COLORS.redText, bold: true } } });
probe.getRange("S5:S249").conditionalFormats.add("containsText", { text: "SPARSE", format: { fill: COLORS.amber, font: { color: COLORS.amberText, bold: true } } });

// 3) Focused sparse-signal review.
const low = wb.worksheets.add("LOW_SIGNAL_REVIEW");
baseSheet(low, "#D97706");
titleBlock(low, "I", "Low-Signal Targets Retained in the Locked Panel", "These 17 genes have <20% maximum Allen reference prevalence. Sparse reference expression is a sensitivity warning, not a reason to reopen biological selection.");
writeDataTable(low, 3, payload.low_headers, payload.low_rows, "LowSignalReviewTable");
low.freezePanes.freezeRows(4);
setWidths(low, [13, 27, 42, 18, 31, 20, 14, 58, 52], 24);
low.getRange("B5:C21").format.wrapText = true;
low.getRange("H5:I21").format.wrapText = true;
low.getRange("D5:D21").format.numberFormat = "0.00";
low.getRange("D5:D21").conditionalFormats.add("colorScale", { colors: ["#FECACA", "#FEF3C7", "#DCFCE7"], thresholds: ["min", { type: "percentile", value: 50 }, "max"] });
low.mergeCells("A23:I23");
low.getRange("A23").values = [["Locked-panel decision: keep all 17. For Sstr4, Gpr63, and Slc6a3 (<5%), treat a zero count as inconclusive and rely on orthogonal identity/state markers for interpretation."]];
low.getRange("A23:I23").format = { fill: COLORS.amber, font: { name: FONT, size: 10, bold: true, color: COLORS.amberText }, wrapText: true, verticalAlignment: "center" };
low.getRange("A23:I23").format.rowHeight = 34;

// 4) Reporter sequence blockers and expected detection.
const reporter = wb.worksheets.add("REPORTER_SEQUENCE");
baseSheet(reporter, "#B91C1C");
titleBlock(reporter, "I", "Reporter / Recombinase Sequence QC", "Both custom targets remain in the 245-gene panel. Exact construct sequences are required before a valid probe design can be evaluated.");
writeDataTable(reporter, 3, payload.reporter_headers, payload.reporter_rows, "ReporterSequenceTable");
setWidths(reporter, [13, 31, 31, 35, 55, 55, 45, 55, 34], 16);
reporter.getRange("A5:I6").format.wrapText = true;
reporter.getRange("A5:I6").format.rowHeight = 105;
reporter.getRange("D5:D6").format.fill = COLORS.red;
reporter.getRange("D5:D6").format.font = { name: FONT, size: 9, bold: true, color: COLORS.redText };
reporter.mergeCells("A9:I9");
reporter.getRange("A9").values = [["Submission checklist"]];
reporter.getRange("A9:I9").format = { fill: COLORS.navy, font: { name: FONT, size: 11, bold: true, color: COLORS.white } };
reporter.getRange("A10:C14").values = [
  [1, "Allele confirmation", "Confirm the actual colony line and construct identity for Ai14 and TRAP2."],
  [2, "Sequence provenance", "Use the exact line/construct coding sequence; record its source and version."],
  [3, "FASTA format", "Sense strand, 5'→3', valid DNA alphabet, one target record per sequence, >=80 bp."],
  [4, "Identity check", "Verify that tdTomato is not a generic RFP and iCre is the exact iCreERT2 variant."],
  [5, "Vendor review", "Run Advanced Custom Design and archive the returned probe/design status before ordering."],
];
reporter.getRange("A10:C14").format = { font: { name: FONT, size: 9, color: COLORS.text }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: COLORS.border } };
reporter.getRange("A10:C14").format.rowHeight = 40;
reporter.getRange("A10:A14").format.fill = COLORS.paleTeal;
reporter.freezePanes.freezeRows(4);

// 5) Whole-transcriptome Allen anchor coverage.
const coverage = wb.worksheets.add("ALLEN_ANCHOR_COVERAGE");
baseSheet(coverage, COLORS.blue);
titleBlock(coverage, "K", "Whole-Transcriptome Allen Anchor Coverage", "Passing rule: specificity >=0.5 log2, expressing cells >=25%, and mean log2 expression >=0.5. All 20 planned anchors are covered by the locked panel.");
writeDataTable(coverage, 3, payload.coverage_headers, payload.coverage_rows, "AllenCoverageTable");
coverage.freezePanes.freezeRows(4);
coverage.freezePanes.freezeColumns(2);
setWidths(coverage, [10, 34, 17, 65, 17, 18, 17, 18, 18, 18, 48], 25);
coverage.getRange("D5:D24").format.wrapText = true;
coverage.getRange("K5:K24").format.wrapText = true;
coverage.getRange("F5:F24").format.numberFormat = "0.00";
coverage.getRange("I5:I24").format.numberFormat = "0.00";
coverage.getRange("C5:C24").conditionalFormats.add("dataBar", { color: COLORS.blue, thresholds: ["min", "max"], gradient: true });
coverage.getRange("J5:J24").conditionalFormats.add("containsText", { text: "Yes", format: { fill: COLORS.amber, font: { color: COLORS.amberText, bold: true } } });
coverage.getRange("K5:K24").conditionalFormats.add("containsText", { text: "COVERED", format: { fill: COLORS.green, font: { color: COLORS.greenText, bold: true } } });

// 6) Omitted-marker audit trail.
const omitted = wb.worksheets.add("TOP_OMITTED_AUDIT");
baseSheet(omitted, "#64748B");
titleBlock(omitted, "H", "Top Omitted Allen Markers — Audit Only", "Top three omitted passing markers per anchor are retained for transparency. They do not trigger additions because every anchor already has passing in-panel genes.");
writeDataTable(omitted, 3, payload.omitted_headers, payload.omitted_rows, "TopOmittedAuditTable");
omitted.freezePanes.freezeRows(4);
omitted.freezePanes.freezeColumns(2);
setWidths(omitted, [10, 34, 17, 18, 18, 22, 18, 62], 65);
omitted.getRange("H5:H64").format.wrapText = true;
omitted.getRange("D5:F64").format.numberFormat = "0.00";

// 7) Sources, reproducible rules, and limitations.
const sources = wb.worksheets.add("SOURCES_METHODS");
baseSheet(sources, "#475569");
titleBlock(sources, "E", "Sources and Reproducible QC Rules", "Primary vendor/reference sources and the exact decision rules used for this pre-order QC.");
sources.getRange("A4:E4").values = [payload.sources_headers];
sources.getRangeByIndexes(4, 0, payload.sources_rows.length, payload.sources_headers.length).values = payload.sources_rows;
sources.tables.add(`A4:E${4 + payload.sources_rows.length}`, true, "SourcesTable");
styleHeader(sources.getRange("A4:E4"));
sources.getRange(`A5:E${4 + payload.sources_rows.length}`).format = { font: { name: FONT, size: 9, color: COLORS.text }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: COLORS.border } };
sources.getRange(`A5:E${4 + payload.sources_rows.length}`).format.rowHeight = 52;
const methodTitleRow = 6 + payload.sources_rows.length;
sources.mergeCells(`A${methodTitleRow}:E${methodTitleRow}`);
sources.getRange(`A${methodTitleRow}`).values = [["Methods / decision rules"]];
sources.getRange(`A${methodTitleRow}:E${methodTitleRow}`).format = { fill: COLORS.navy, font: { name: FONT, size: 11, bold: true, color: COLORS.white } };
const methodHeaderRow = methodTitleRow + 1;
sources.getRange(`A${methodHeaderRow}:B${methodHeaderRow}`).values = [payload.methods_headers];
sources.getRangeByIndexes(methodHeaderRow, 0, payload.methods_rows.length, 2).values = payload.methods_rows;
sources.tables.add(`A${methodHeaderRow}:B${methodHeaderRow + payload.methods_rows.length}`, true, "MethodsTable");
styleHeader(sources.getRange(`A${methodHeaderRow}:B${methodHeaderRow}`));
sources.getRange(`A${methodHeaderRow + 1}:B${methodHeaderRow + payload.methods_rows.length}`).format = { font: { name: FONT, size: 9, color: COLORS.text }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: COLORS.border } };
sources.getRange(`A${methodHeaderRow + 1}:B${methodHeaderRow + payload.methods_rows.length}`).format.rowHeight = 48;
setWidths(sources, [29, 28, 39, 74, 48], methodHeaderRow + payload.methods_rows.length + 2);
sources.freezePanes.freezeRows(4);

// Export, re-import, inspect, and render every sheet.
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);

const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const inspectParts = [];
inspectParts.push((await reopened.inspect({ kind: "sheet,table", maxChars: 12000, tableMaxRows: 3, tableMaxCols: 8, tableMaxCellChars: 100 })).ndjson);
inspectParts.push((await reopened.inspect({ kind: "table", sheetId: "QC_SUMMARY", range: "A1:J27", maxChars: 9000, tableMaxRows: 30, tableMaxCols: 10, tableMaxCellChars: 120 })).ndjson);
inspectParts.push((await reopened.inspect({ kind: "table", sheetId: "PROBE_QC_245", range: "A240:T249", maxChars: 7000, tableMaxRows: 12, tableMaxCols: 20, tableMaxCellChars: 100 })).ndjson);
inspectParts.push((await reopened.inspect({ searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, matchFormulas: false, maxResults: 100 }, maxChars: 6000 })).ndjson);
await fs.writeFile(path.join(previewDir, "verification_inspect.ndjson"), inspectParts.join("\n"), "utf8");

const renderSpecs = [
  ["QC_SUMMARY", "A1:J27"],
  ["PROBE_QC_245", "A1:T30"],
  ["LOW_SIGNAL_REVIEW", "A1:I23"],
  ["REPORTER_SEQUENCE", "A1:I14"],
  ["ALLEN_ANCHOR_COVERAGE", "A1:K24"],
  ["TOP_OMITTED_AUDIT", "A1:H35"],
  ["SOURCES_METHODS", `A1:E${methodHeaderRow + payload.methods_rows.length}`],
];
for (const [sheetName, range] of renderSpecs) {
  const preview = await reopened.render({ sheetName, range, format: "png", scale: 0.8, headers: false });
  const fileName = `${sheetName.toLowerCase()}.png`;
  await fs.writeFile(path.join(previewDir, fileName), new Uint8Array(await preview.arrayBuffer()));
}

console.log(JSON.stringify({ outputPath, previewDir, sheets: renderSpecs.map(([name]) => name) }, null, 2));
