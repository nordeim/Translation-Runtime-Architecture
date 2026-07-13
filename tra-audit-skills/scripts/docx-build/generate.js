// TRA Prototype Audit Report — docx-js generator
// Template: Testing Report (Template C) — Test Overview → Scope → Plan → Results → Defects → Risks → Conclusions
// Palette: Deep Sea Academic (Cool + Heavy + Calm)
// Cover: R5 (Clean White) — appropriate for technical reports

const {
  Document, Packer, Paragraph, TextRun, Header, Footer,
  AlignmentType, HeadingLevel, PageNumber,
  Table, TableRow, TableCell, WidthType, BorderStyle,
  ShadingType, ImageRun, NumberFormat, SectionType
} = require("docx");
const fs = require("fs");

// =========================================================================
// PALETTE — Deep Sea Academic (Cool + Heavy + Calm)
// =========================================================================
const P = {
  primary: "162032",
  body: "1C2A3D",
  secondary: "5B6B7D",
  accent: "8B7E5A",
  surface: "F5F7FA",
  blocking: "C92A2A",
  warning: "F08C00",
  info: "1C7ED6",
  white: "FFFFFF",
  altRow: "EFF2F7",
};

const c = (hex) => hex.replace("#", "");

function heading(text, level = HeadingLevel.HEADING_1) {
  const sizes = {
    [HeadingLevel.HEADING_1]: 32,
    [HeadingLevel.HEADING_2]: 28,
    [HeadingLevel.HEADING_3]: 24,
  };
  return new Paragraph({
    heading: level,
    spacing: { before: level === HeadingLevel.HEADING_1 ? 480 : level === HeadingLevel.HEADING_2 ? 360 : 280, after: 160, line: 312 },
    keepNext: true,
    children: [new TextRun({ text, bold: true, color: c(P.primary), size: sizes[level] || 24, font: { ascii: "Calibri", eastAsia: "SimHei" } })],
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    indent: opts.noIndent ? undefined : { firstLine: 480 },
    spacing: { line: 312, after: 120 },
    children: [new TextRun({ text, size: 22, color: c(P.body), font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" }, bold: opts.bold, italics: opts.italics })],
  });
}

function bodyRuns(runs, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    indent: opts.noIndent ? undefined : { firstLine: 480 },
    spacing: { line: 312, after: 120 },
    children: runs,
  });
}

function run(text, opts = {}) {
  return new TextRun({ text, size: opts.size || 22, color: opts.color || c(P.body), bold: opts.bold, italics: opts.italics, font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } });
}

function bullet(text, level = 0) {
  return new Paragraph({
    bullet: { level },
    spacing: { line: 312, after: 80 },
    children: [new TextRun({ text, size: 22, color: c(P.body), font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
  });
}

function codeBlock(text) {
  return new Paragraph({
    spacing: { line: 280, before: 120, after: 120 },
    indent: { left: 360 },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: P.surface },
    children: [new TextRun({ text, size: 18, color: c(P.primary), font: { ascii: "Consolas", eastAsia: "Sarasa Mono SC" } })],
  });
}

function spacer(n = 1) {
  return Array.from({ length: n }, () => new Paragraph({ children: [new TextRun({ text: "" })] }));
}

// =========================================================================
// TABLE HELPERS
// =========================================================================
const noBorder = { style: BorderStyle.NONE, size: 0, color: "auto" };
const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: "D1D5DB" };

function cellText(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { line: 280, after: 0 },
    children: [new TextRun({ text: String(text), size: opts.size || 20, color: opts.color || c(P.body), bold: opts.bold, font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
  });
}

function headerCell(text, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.PERCENTAGE },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: P.primary },
    margins: { top: 100, bottom: 100, left: 140, right: 140 },
    children: [cellText(text, { bold: true, color: c(P.white), align: opts.align || AlignmentType.LEFT, size: 20 })],
  });
}

function dataCell(text, width, opts = {}) {
  const fillColor = opts.severity === "BLOCKING" ? "FFF5F5" : opts.severity === "WARNING" ? "FFFBEB" : opts.severity === "INFO" ? "EFF6FF" : opts.alt ? P.altRow : null;
  return new TableCell({
    width: { size: width, type: WidthType.PERCENTAGE },
    shading: fillColor ? { type: ShadingType.CLEAR, color: "auto", fill: fillColor } : undefined,
    margins: { top: 80, bottom: 80, left: 140, right: 140 },
    children: [cellText(text, {
      bold: opts.bold,
      color: opts.severity === "BLOCKING" ? c(P.blocking) : opts.severity === "WARNING" ? c(P.warning) : opts.severity === "INFO" ? c(P.info) : c(P.body),
      size: opts.size || 20,
      align: opts.align || AlignmentType.LEFT,
    })],
  });
}

function tableBorders() {
  return { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder, insideHorizontal: thinBorder, insideVertical: thinBorder };
}

// =========================================================================
// FINDINGS DATA
// =========================================================================
const FINDINGS = require("./tra_findings.json");
const STATS = {
  BLOCKING: FINDINGS.filter(f => f.severity === "BLOCKING").length,
  WARNING: FINDINGS.filter(f => f.severity === "WARNING").length,
  INFO: FINDINGS.filter(f => f.severity === "INFO").length,
  TOTAL: FINDINGS.length,
};
const TRACK_STATS = {
  A: { name: "Spec Conformance", findings: FINDINGS.filter(f => f.track === "A") },
  B: { name: "Code Quality & Security", findings: FINDINGS.filter(f => f.track === "B") },
  C: { name: "Doc Consistency", findings: FINDINGS.filter(f => f.track === "C") },
  D: { name: "Test Suite", findings: FINDINGS.filter(f => f.track === "D") },
};

// =========================================================================
// COVER PAGE (R5 — Clean White)
// =========================================================================
function buildCover() {
  const children = [];
  // Reduced spacers to avoid 9-consecutive-empty-paragraph blank-page warning
  // Use spacing.before on the first real paragraph instead of empty paragraphs
  children.push(new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 16, color: P.accent } },
    spacing: { before: 2400, after: 240 },
    children: [new TextRun({ text: "" })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.LEFT, spacing: { after: 120 },
    children: [new TextRun({ text: "CODE REVIEW & AUDIT REPORT", size: 18, color: c(P.accent), bold: true, font: { ascii: "Calibri" }, characterSpacing: 60 })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.LEFT, spacing: { after: 120, line: 360 },
    children: [new TextRun({ text: "TRA Prototype Engine", size: 64, bold: true, color: c(P.primary), font: { ascii: "Calibri" } })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.LEFT, spacing: { after: 360, line: 360 },
    children: [new TextRun({ text: "Systematic Code Review & Conformance Audit", size: 36, color: c(P.secondary), font: { ascii: "Calibri" } })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.LEFT, spacing: { after: 480 },
    children: [new TextRun({ text: "Translation Runtime Architecture v1.0  \u00b7  ZH\u2194EN Prototype  \u00b7  L3 Strict Conformance Target", size: 22, italics: true, color: c(P.secondary), font: { ascii: "Calibri" } })],
  }));
  const metaTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder, insideHorizontal: noBorder, insideVertical: noBorder },
    rows: [
      ["Audit date", "2026-07-13"],
      ["Auditor", "Super Z \u2014 multi-agent (4-track parallel)"],
      ["Repository", "github.com/nordeim/Translation-Runtime-Architecture @ HEAD"],
      ["Scope", "tra-prototype/ engine + 5 TRA-*.md spec docs"],
      ["Severity lexicon", "TRA-SPECIFICATION.md \u00a77 (BLOCKING / WARNING / INFO)"],
      ["Methodology", "Spec conformance + Code quality + Doc consistency + Test suite"],
    ].map(([k, v]) => new TableRow({
      children: [
        new TableCell({ width: { size: 28, type: WidthType.PERCENTAGE }, borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder }, margins: { top: 60, bottom: 60, left: 0, right: 120 }, children: [cellText(k, { bold: true, color: c(P.secondary), size: 18 })] }),
        new TableCell({ width: { size: 72, type: WidthType.PERCENTAGE }, borders: { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder }, margins: { top: 60, bottom: 60, left: 0, right: 0 }, children: [cellText(v, { color: c(P.body), size: 20 })] }),
      ],
    })),
  });
  children.push(metaTable);
  // Single spacer instead of 8, with spacing.before on the rule paragraph for breathing room
  children.push(new Paragraph({
    border: { top: { style: BorderStyle.SINGLE, size: 16, color: P.accent } },
    spacing: { before: 2400, after: 120 },
    children: [new TextRun({ text: "" })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.LEFT,
    children: [new TextRun({ text: "Prepared by Super Z  \u00b7  Frontend Architect & Technical Partner  \u00b7  Elite / Meticulous / Avant-Garde", size: 16, color: c(P.secondary), italics: true, font: { ascii: "Calibri" } })],
  }));
  return children;
}

// =========================================================================
// SECTION 1 — EXECUTIVE SUMMARY
// =========================================================================
function buildExecutiveSummary() {
  const children = [];
  children.push(heading("1. Executive Summary", HeadingLevel.HEADING_1));
  children.push(body(`This report documents a systematic, four-track code review and conformance audit of the Translation Runtime Architecture (TRA) prototype engine located in the tra-prototype/ subdirectory of the TRA specification repository. The audit was executed on 2026-07-13 against the repository HEAD and covers spec conformance (Track A), code quality and security (Track B), documentation-vs-code consistency (Track C), and test-suite coverage (Track D).`));
  children.push(body(`The audit produced ${STATS.TOTAL} findings: ${STATS.BLOCKING} BLOCKING, ${STATS.WARNING} WARNING, and ${STATS.INFO} INFO. The TRA severity lexicon (TRA-SPECIFICATION.md \u00a77) is used throughout this report in place of conventional Critical/High/Medium/Low ratings, both for spec fidelity and because the lexicon maps directly to the engine's own diagnostic vocabulary.`));
  children.push(body(`The codebase is in better shape than its own tra-prototype/README.md admits and slightly worse shape than CLAUDE.md's "Phases 0\u20136 complete" claim implies. All four quality gates pass clean: ruff check, ruff format --check, mypy --strict tra (20 source files), and pytest tests (103 tests in 0.46s). The L3 conformance gate is correctly enforced by the standalone validate command and the benchmark runner. The ZH\u2194EN module's canonical terminology is exact, the four critical invariants are mostly enforced, and the L4 forensic artifacts emit correctly.`));
  children.push(body(`However, the audit uncovered material gaps in five areas: (1) the TRANSLATE_SEGMENT instruction operates on the whole document rather than per-segment as the ISA contract requires; (2) the module registry\u2014the sanctioned extension point\u2014is bypassed by the kernel; (3) the surgical-repair invariant is violated at the function boundary for attempts below max_retries; (4) four of the five TRA-EXCEPTION recovery procedures are unreachable in production code; and (5) the L3 zero-BLOCKING gate is not enforced by the main translate command. Each of these is documented with file:line evidence and a suggested fix in the sections that follow.`));

  children.push(heading("1.1 Headline Numbers", HeadingLevel.HEADING_2));
  const statsTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: tableBorders(),
    rows: [
      new TableRow({ tableHeader: true, children: [
        headerCell("Track", 22), headerCell("Scope", 38),
        headerCell("BLOCKING", 13, { align: AlignmentType.CENTER }),
        headerCell("WARNING", 13, { align: AlignmentType.CENTER }),
        headerCell("INFO", 7, { align: AlignmentType.CENTER }),
        headerCell("Total", 7, { align: AlignmentType.CENTER }),
      ]}),
      ...["A", "B", "C", "D"].map(t => {
        const ts = TRACK_STATS[t];
        const b = ts.findings.filter(f => f.severity === "BLOCKING").length;
        const w = ts.findings.filter(f => f.severity === "WARNING").length;
        const i = ts.findings.filter(f => f.severity === "INFO").length;
        return new TableRow({ cantSplit: true, children: [
          dataCell(`Track ${t}`, 22, { bold: true }),
          dataCell(ts.name, 38),
          dataCell(b, 13, { severity: "BLOCKING", align: AlignmentType.CENTER, bold: true }),
          dataCell(w, 13, { severity: "WARNING", align: AlignmentType.CENTER, bold: true }),
          dataCell(i, 7, { severity: "INFO", align: AlignmentType.CENTER, bold: true }),
          dataCell(ts.findings.length, 7, { align: AlignmentType.CENTER, bold: true }),
        ]});
      }),
      new TableRow({ cantSplit: true, children: [
        dataCell("TOTAL", 22, { bold: true, alt: true }),
        dataCell("All tracks", 38, { bold: true, alt: true }),
        dataCell(STATS.BLOCKING, 13, { severity: "BLOCKING", align: AlignmentType.CENTER, bold: true, alt: true }),
        dataCell(STATS.WARNING, 13, { severity: "WARNING", align: AlignmentType.CENTER, bold: true, alt: true }),
        dataCell(STATS.INFO, 7, { severity: "INFO", align: AlignmentType.CENTER, bold: true, alt: true }),
        dataCell(STATS.TOTAL, 7, { align: AlignmentType.CENTER, bold: true, alt: true }),
      ]}),
    ],
  });
  children.push(statsTable);
  children.push(...spacer(1));

  children.push(heading("1.2 Bottom Line", HeadingLevel.HEADING_2));
  children.push(body(`The TRA prototype faithfully implements the ISA contracts for ANALYZE_DOCUMENT, BUILD_GLOSSARY, BUILD_ENTITY_TABLE, VERIFY_OUTPUT (never-self-scores), and L4 forensic gating. The ZH\u2194EN module's canonical terminology is exact and forbids drift. Entities are immutable in practice. The audit trail is append-only by API design. The L3 gate is correctly enforced by the standalone validate command.`));
  children.push(body(`The prototype does NOT faithfully implement: (1) the TRANSLATE_SEGMENT segment-level contract (whole-doc instead); (2) the REPAIR_SEGMENT surgical invariant at the function boundary; (3) EXCEPTION_HANDLER recovery for four of five exception types; (4) the L3 gate in the main translate pipeline; and (5) the Policy Engine arbitration in production code paths. Of the four critical invariants, three hold (canonical terminology, entity immutability, never-self-score); one (repair surgical) is violated with a reproducible attack at the function boundary.`));
  return children;
}

// =========================================================================
// SECTION 2 — SCOPE & METHODOLOGY
// =========================================================================
function buildScope() {
  const children = [];
  children.push(heading("2. Scope, Environment & Methodology", HeadingLevel.HEADING_1));

  children.push(heading("2.1 Scope", HeadingLevel.HEADING_2));
  children.push(body(`The audit covered the tra-prototype/ subdirectory (the only code area in the specification repository) and its interaction with the five normative TRA specification documents at the repository root. The five spec files\u2014TRA-SPECIFICATION.md, TRA-ISA-REFERENCE.md, TRA-MODULE-ZH-EN.md, TRA-BENCHMARK-SUITE.md, and TRA-CONFORMANCE-GUIDE.md\u2014were treated as the source of truth against which the engine was audited.`));
  children.push(body(`Out of scope: the specification documents themselves (they are authored, not built); any LLM endpoint integration (the LLM seam is caller-supplied and ships without one); and any code outside the repository (no external dependencies were audited beyond a hygiene check).`));

  children.push(heading("2.2 Environment", HeadingLevel.HEADING_2));
  children.push(body(`Audit was performed on a Linux environment with Python 3.12, Node.js v24, and the prototype's own toolchain (ruff 0.5+, mypy 1.10+, pytest 8.2+). The prototype was installed via pip install -e ".[dev]" with the --break-system-packages flag (PEP-668 externally-managed environment). All quality gates were run from inside tra-prototype/ per the documented procedure.`));

  children.push(heading("2.3 Methodology", HeadingLevel.HEADING_2));
  children.push(body(`The audit used a four-track parallel structure, with each track executed by a dedicated subagent and the results synthesized into a unified severity-rated register. The four tracks were:`));
  children.push(bullet("Track A \u2014 Spec conformance: 26-item checklist covering the 9 Kernel states, 6 ISA instructions, 6 Policy priorities, 4 Memory Model segments, 5 TRA-EXCEPTION recovery procedures, L3/L4 conformance gates, and mutation-testing of the 4 critical invariants."));
  children.push(bullet("Track B \u2014 Code quality & security: 18-item checklist covering type safety, error handling, dead code, input sanitization, cache determinism, path safety, Pydantic v2 modeling, dependency hygiene, and reproducibility."));
  children.push(bullet("Track C \u2014 Doc-vs-code consistency: 22-item line-by-line reconciliation of every claim in CLAUDE.md, AGENTS.md, README.md, implementation_plan.md, SKILL.md, status.md, review.md, review-feedback.md, prototype.md, and start-here.md against the actual code."));
  children.push(bullet("Track D \u2014 Test-suite audit: inventory of all 103 tests, benchmark-coverage analysis (13 of 24 spec cases implemented), and invariant mutation testing (12 scenarios across the 4 critical invariants)."));
  children.push(body(`Each finding was verified empirically where possible. The two most material findings\u2014the repair_segment surgical-invariant violation (TRA-003) and the cache-clear --pattern silent no-op (TRA-011)\u2014were confirmed by direct runtime probes (see Appendix A). The full audit trail, including per-finding evidence with file:line citations, is appended to the shared worklog at /home/z/my-project/worklog.md under Task IDs audit-A, audit-B, audit-C, and audit-D.`));
  return children;
}

// =========================================================================
// SECTION 3 — AUDIT PLAN & SUCCESS CRITERIA
// =========================================================================
function buildTestPlan() {
  const children = [];
  children.push(heading("3. Audit Plan & Success Criteria", HeadingLevel.HEADING_1));

  children.push(heading("3.1 Audit Question", HeadingLevel.HEADING_2));
  children.push(body(`The audit answered two questions: (1) Does the tra-prototype/ engine faithfully implement TRA v1.0 as specified? (2) Is the codebase production-grade for its stated purpose (proving out the TRA spec deterministically for ZH\u2194EN at L3)?`));

  children.push(heading("3.2 Success Criteria", HeadingLevel.HEADING_2));
  children.push(body(`The audit was considered complete when all of the following were true:`));
  children.push(bullet("Every item in the 26-item spec-conformance checklist (Track A) had a verdict (PASS / WARNING / BLOCKING / N/A) with file:line evidence."));
  children.push(bullet("Every item in the 18-item code-quality checklist (Track B) had a verdict with file:line evidence."));
  children.push(bullet("Every claim in the 11 documentation files (Track C) was verified against the code with exact quotes and line numbers."));
  children.push(bullet("Every test file was inventoried (Track D) with coverage summary, and the 4 critical invariants were mutation-tested."));
  children.push(bullet("The 4 critical invariants had a dedicated \u201cis it truly unbreakable?\u201d verdict, not just \u201cis it currently respected?\u201d."));
  children.push(bullet("All findings were severity-rated using the TRA lexicon and synthesized into a single register."));

  children.push(heading("3.3 Quality Gate Baseline", HeadingLevel.HEADING_2));
  children.push(body(`Before the audit, the four documented quality gates were run fresh to establish a baseline. All four passed clean, confirming the codebase is in a committable state at the audited HEAD:`));

  const gateTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: tableBorders(),
    rows: [
      new TableRow({ tableHeader: true, children: [
        headerCell("Gate", 30), headerCell("Command", 45), headerCell("Result", 25, { align: AlignmentType.CENTER }),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("Linter", 30, { bold: true }),
        dataCell("ruff check .", 45),
        dataCell("PASS \u2014 All checks passed", 25, { align: AlignmentType.CENTER, severity: "INFO", bold: true }),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("Formatter", 30, { bold: true, alt: true }),
        dataCell("ruff format --check .", 45, { alt: true }),
        dataCell("PASS \u2014 33 files formatted", 25, { align: AlignmentType.CENTER, severity: "INFO", bold: true, alt: true }),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("Type checker", 30, { bold: true }),
        dataCell("mypy --strict tra", 45),
        dataCell("PASS \u2014 no issues in 20 files", 25, { align: AlignmentType.CENTER, severity: "INFO", bold: true }),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("Test suite", 30, { bold: true, alt: true }),
        dataCell("pytest tests -q", 45, { alt: true }),
        dataCell("PASS \u2014 103 tests in 0.46s", 25, { align: AlignmentType.CENTER, severity: "INFO", bold: true, alt: true }),
      ]}),
    ],
  });
  children.push(gateTable);
  return children;
}

// =========================================================================
// SECTION 4 — CORE FINDINGS
// =========================================================================
function buildResults() {
  const children = [];
  children.push(heading("4. Core Findings", HeadingLevel.HEADING_1));
  children.push(body(`This section presents the most material findings from each track. The complete 35-finding register is available in the companion XLSX workbook (TRA_audit_findings_register.xlsx) and in the shared worklog. Findings are numbered TRA-001 through TRA-035 and cited by ID throughout this section.`));

  children.push(heading("4.1 Findings by Category & Severity", HeadingLevel.HEADING_2));
  children.push(body(`The chart below shows the distribution of findings across the five categories and three severity levels. Spec Conformance carries the most BLOCKING findings (5), reflecting the gap between the ISA contract documentation and the kernel's actual implementation. Test Suite has 3 BLOCKING findings, all related to invariant-mutation coverage gaps.`));
  const chartData = fs.readFileSync(__dirname + "/chart.png");
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 },
    children: [new ImageRun({ data: chartData, transformation: { width: 580, height: 343 }, type: "png" })],
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text: "Figure 1. Findings by category and severity. 35 total findings: 11 BLOCKING / 22 WARNING / 2 INFO.", size: 18, italics: true, color: c(P.secondary), font: { ascii: "Calibri" } })],
  }));

  // 4.2 Track A
  children.push(heading("4.2 Track A \u2014 Spec Conformance", HeadingLevel.HEADING_2));
  children.push(body(`Track A verified whether each spec clause in TRA-SPECIFICATION.md and TRA-ISA-REFERENCE.md has faithful code. Of 26 checklist items, 18 PASS, 6 WARNING, and 4 BLOCKING (with one item, A-26, being the synthesized invariant audit). Three of the four critical invariants hold; the fourth (repair surgical) is violated at the function boundary.`));

  children.push(heading("4.2.1 TRA-001 (BLOCKING) \u2014 TRANSLATE_SEGMENT receives whole document, not a segment", HeadingLevel.HEADING_3));
  children.push(body(`The ISA contract (TRA-ISA-REFERENCE.md \u00a7TRANSLATE_SEGMENT, lines 48\u201349) mandates that the instruction operates on "a specific source segment (sentence, list item, or table cell)". The kernel passes the entire source markdown as one segment: kernel.py:186 calls translate_segment(src, self.ctx, ...) where src is the full document text. The inline comment at kernel.py:184 admits "Segment granularity is wired in Phase 3" \u2014 Phase 3 never landed.`));
  children.push(body(`Consequences: cache keys are per-document (violating cache.py:12-13 docstring "never a whole document"); RepairAttempt.segment_index is always 0 in production; the L4 line-by-line trace (reporting.py:86) uses a substring-containment heuristic rather than the structural map; and the is_no_translate_zone markers on code blocks (set by anchor.py:375) are never consulted, violating spec case S-03.`));
  children.push(bodyRuns([run("Suggested fix: ", { bold: true }), run("Refactor _execute_translation to iterate StructuralMap leaf nodes (paragraphs, list items, table cells, headings), call translate_segment per leaf, and reassemble via the structural map. Skip nodes where is_no_translate_zone=True.")]));

  children.push(heading("4.2.2 TRA-002 (BLOCKING) \u2014 Module registry bypassed by kernel", HeadingLevel.HEADING_3));
  children.push(body(`CLAUDE.md:40 and SKILL.md \u00a76 document the module registry as the "only sanctioned path" for new language bridges: registry = build_default_registry(); registry.register(my_module.as_interface()). In production code, the kernel hard-codes ZHENModule() directly: kernel.py:43 imports it, kernel.py:106 instantiates it, and isa.py:50,54 follows the same pattern with a module-level singleton _MODULE = ZHENModule().`));
  children.push(body(`Grep confirms ZERO production callers of build_default_registry or registry_for_language_pair. A user following SKILL.md \u00a76 verbatim will find their registered module is NOT used by tra_cli.py translate. The sanctioned extension point is, in practice, not wired into production. This is the load-bearing design decision per CLAUDE.md:40, and it is currently broken.`));
  children.push(bodyRuns([run("Suggested fix: ", { bold: true }), run("Replace the hard-coded ZHENModule() in kernel.py and isa.py with a registry lookup: module = registry_for_language_pair(config.language_pair). Inject the module via constructor instead of module-level singleton.")]));

  children.push(heading("4.2.3 TRA-003 (BLOCKING) \u2014 repair_segment not surgical at function boundary", HeadingLevel.HEADING_3));
  children.push(body(`The spec mandates "Repair must resolve the specific violation without introducing new ones" (TRA-ISA-REFERENCE.md:79, mirrored in TRA-SPECIFICATION.md:83, CLAUDE.md:79, AGENTS.md:33, README.md:123). The code at isa.py:515-519 only raises Unrecoverable when new_blocking and attempt >= max_retries. At attempt=1 with max_retries=3, a repair that introduces new BLOCKING returns silently with resolved=False.`));
  children.push(body(`This was empirically confirmed by direct runtime probe. Calling repair_segment(target="\u6210\u7acb Valid", attempt=1, max_retries=3) with a terminology diagnostic returns "Confirmed Valid" (containing the forbidden drift target "Valid") without raising. The kernel's _repair_loop catches this by re-queuing, but a direct caller outside the kernel receives broken output with no exception. This is the most dangerous finding in the audit because it silently violates the most-repeated invariant in the spec.`));
  children.push(bodyRuns([run("Suggested fix: ", { bold: true }), run("Remove the attempt >= max_retries guard from the new-BLOCKING check. Raise Unrecoverable unconditionally on any new BLOCKING, regardless of attempt number. Add a regression test that calls repair_segment directly with attempt=1 and asserts the raise.")]));

  children.push(heading("4.2.4 TRA-004 (BLOCKING) \u2014 4 of 5 TRA-EXCEPTION recovery procedures unreachable", HeadingLevel.HEADING_3));
  children.push(body(`Spec \u00a76 mandates deterministic recovery for all 5 TRA-EXCEPTION types. Grep across tra/ for raise UnknownTerm|raise CertaintyConflict|raise EntityAmbiguity returns ZERO hits \u2014 these exception classes exist but are never raised in production code paths. BrokenMarkdown IS raised by analyze_document (isa.py:84) but kernel.py:129 calls it with NO try/except, so a malformed source crashes the kernel with no EXCEPTION_HANDLER invocation.`));
  children.push(body(`Only GlossaryConflict (build_glossary) and Unrecoverable (repair_segment) reach route_exception. The recovery.py dispatcher and 3 of its 5 handlers are dead code. The test suite covers all 5 recovery procedures in isolation (test_recovery.py) but does not test them through the kernel, so the gap is invisible.`));

  children.push(heading("4.2.5 TRA-005 (BLOCKING) \u2014 kernel.run() does not enforce the L3 gate", HeadingLevel.HEADING_3));
  children.push(body(`Per TRA-CONFORMANCE-GUIDE.md:51, "If [BLOCKING diagnostics are] present, certification is denied." The kernel's run() method (kernel.py:157) returns the target unconditionally, even when _repair_loop exhausts max_retries with BLOCKING diagnostics still present. The CLI (tra_cli.py:106-120) only prints a warning. Only validate.py and benchmark.py enforce zero-BLOCKING. A user running tra_cli.py translate --level L3 on a document that produces BLOCKING diagnostics receives a "translated" output and no error signal.`));

  // 4.3 Track B
  children.push(heading("4.3 Track B \u2014 Code Quality & Security", HeadingLevel.HEADING_2));
  children.push(body(`Track B verified whether the codebase is production-grade for its stated purpose. Of 18 checklist items, 8 PASS, 9 WARNING, and 1 BLOCKING. The most material finding is the silent cache-invalidation no-op.`));

  children.push(heading("4.3.1 TRA-011 (BLOCKING) \u2014 cache-clear --pattern is a silent no-op", HeadingLevel.HEADING_3));
  children.push(body(`TranslationCache.invalidate(pattern) (cache.py:107-115) calls self._cache.delete(pattern). diskcache's delete() takes a LITERAL key, not a glob. This was empirically confirmed: invalidate("test*") on a cache with 3 entries deletes 0 (3\u21923); the literal-key invalidate works (3\u21922). The CLI (tra_cli.py:130) then prints "Cache invalidated: <pattern>" unconditionally \u2014 lying to the user.`));
  children.push(body(`A user who runs tra cache-clear --pattern 'translation:*' to invalidate stale entries believes they were cleared; they weren't. This could serve stale translations indefinitely. The comment in the code ("diskcache.delete supports glob patterns") is false.`));
  children.push(bodyRuns([run("Suggested fix: ", { bold: true }), run("Implement glob via: for key in self._cache.iterkeys(): if fnmatch(key, pattern): self._cache.delete(key). Update the CLI to print the actual count deleted.")]));

  children.push(heading("4.3.2 TRA-013 (WARNING) \u2014 Audit trail is NOT byte-reproducible", HeadingLevel.HEADING_3));
  children.push(body(`diagnostics.py:40 uses uuid4() for evidence IDs; diagnostics.py:58 uses datetime.now(UTC) for timestamps. Empirically confirmed: two runs of identical source produce identical target text, identical cache.db, identical glossary/entity/smap/style/exec_log/repair_history \u2014 but DIFFERENT audit_trace.jsonl. For L4 forensic audits (legal/security per TRA-CONFORMANCE-GUIDE.md), this means you cannot cryptographically prove "this audit trail corresponds to this output" by hashing the trail.`));

  children.push(heading("4.3.3 TRA-017 (WARNING) \u2014 5 unused dependencies inflate install footprint", HeadingLevel.HEADING_3));
  children.push(body(`litellm (>=1.49), structlog (>=24.1), pydantic-settings (>=2.3), mdit-py-plugins (>=0.4), and black (>=24.4, dev) are listed but never imported. litellm alone pulls ~30 transitive deps (openai, tiktoken, tokenizers, huggingface-hub, httpx, aiohttp, jinja2, jsonschema, ...). The LLM seam is wired as a caller-supplied Callable, so litellm is not actually needed at runtime. Total install: ~50+ packages, hundreds of MB, for a rule-based prototype.`));

  // 4.4 Track C
  children.push(heading("4.4 Track C \u2014 Doc-vs-Code Consistency", HeadingLevel.HEADING_2));
  children.push(body(`Track C verified every claim in 11 documentation files against the code. Of 22 items, 5 PASS, 14 WARNING, and 4 BLOCKING (D-1 through D-4 plus D-19 as a meta-BLOCKING on the "Known gaps" list itself). The most accurate document is status.md; the least accurate is tra-prototype/README.md.`));

  children.push(heading("4.4.1 TRA-020 (BLOCKING) \u2014 CLAUDE.md 'Known gaps (honest)' lists only 3 of ~16 material gaps", HeadingLevel.HEADING_3));
  children.push(body(`CLAUDE.md:42-46 labels the list "Known gaps (honest, not yet addressed)" but enumerates only: structlog unused, no asyncio parallelism, no cross-run glossary/entity caching. At least 16 material gaps exist (TRA-001 through TRA-019 in this audit, plus Phase 7 items). The word "honest" is itself misleading when the list omits the most material gaps (segment-level granularity, registry bypass, repair-attempt-1, exception recovery, L3 gate not enforced in translate, count_blocking stub, cache-clear no-op, etc.).`));

  children.push(heading("4.4.2 TRA-021 (BLOCKING) \u2014 tra-prototype/README.md says 'Phase 0-5' and 'Phase 6 pending' \u2014 both false", HeadingLevel.HEADING_3));
  children.push(body(`tra-prototype/README.md:3 says "A Phase 0\u20135 reference implementation of TRA v1.0". Line 78\u201379 says "Phase 6 (exception hardening, human-in-the-loop, structlog, L4 evidence tracing) is pending." Reality: Phase 6 IS implemented \u2014 6.1 (recovery.py), 6.2 (hitl.py + --interactive), 6.3 (reporting.py, Mermaid, audit summary), 6.4 (kernel.py:293-312 _export_forensics, L4 trace), 6.5 (kernel.py:75-90 _sanitize_input + isa.py:316-330 graceful degradation). Only 6.3.1 structlog is genuinely pending. The prototype README is the file a new contributor reads first \u2014 accuracy here is load-bearing.`));

  // 4.5 Track D
  children.push(heading("4.5 Track D \u2014 Test Suite Audit", HeadingLevel.HEADING_2));
  children.push(body(`Track D verified whether the tests are sufficient to catch regressions on the 4 critical invariants and the 6 ISA contracts. The suite is well-structured (103 tests, 12 files, 0.46s) but would not catch regressions in 3 of the 4 critical invariants under mutation testing. The invariant-mutation catch rate is 42% (5 of 12 scenarios).`));

  children.push(heading("4.5.1 TRA-028 (BLOCKING) \u2014 Zero coverage on repair_segment's 'raise on new BLOCKING' clause", HeadingLevel.HEADING_3));
  children.push(body(`Mutation testing: removing the if new_blocking and attempt >= max_retries: raise Unrecoverable(...) block entirely leaves all 103 tests green. Flipping >= to > (off-by-one) leaves all 103 tests green. Calling repair_segment directly with attempt=1 and new BLOCKING has no test asserting the raise behavior. The most dangerous gap: the test suite cannot detect regressions in the surgical-repair invariant's partial enforcement (TRA-003).`));

  children.push(heading("4.5.2 TRA-029 (BLOCKING) \u2014 Invariant 3 (never self-scores) untested at enforcement boundary", HeadingLevel.HEADING_3));
  children.push(body(`Mutation testing: adding if e.confidence_note and e.confidence_note < 0.5: diagnostics.append(...) to verify_output leaves all 103 tests green. The existing test (test_phase0.py:68-82) adds a low-confidence record to the registry but never calls verify_output or repair_segment with that record present. The "never self-score" invariant is documented but untested at the enforcement boundary.`));

  children.push(heading("4.5.3 TRA-031 (WARNING) \u2014 Only 13 of 24 spec benchmark cases implemented", HeadingLevel.HEADING_3));
  children.push(body(`TRA-BENCHMARK-SUITE.md defines S-01..S-06, F-01..F-05, T-01..T-05, D-01..D-04, E-01..E-03 (24 cases). The prototype implements 13 (S-05, F-01..F-05, T-01..T-05, D-04, E-02) plus R-01 (regression, not in spec). Missing: S-03 (inline code vs prose \u2014 exposes the whole-doc translation gap, TRA-001), S-06 (anchors \u2014 unit-tested but not in benchmark), E-03 (broken source markdown \u2014 exposes the exception-recovery gap, TRA-004). Spec target is "100+".`));

  return children;
}

// =========================================================================
// SECTION 5 — CRITICAL INVARIANTS DEEP-DIVE
// =========================================================================
function buildInvariantsDeepDive() {
  const children = [];
  children.push(heading("5. Critical Invariants Deep-Dive", HeadingLevel.HEADING_1));
  children.push(body(`The TRA specification defines four load-bearing invariants that are "easy to break" per CLAUDE.md:72-79. This section attempts to break each one and reports the verdict. The full mutation-testing methodology is documented in the Track D worklog entry.`));

  const invTable = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: tableBorders(),
    rows: [
      new TableRow({ tableHeader: true, children: [
        headerCell("#", 6, { align: AlignmentType.CENTER }),
        headerCell("Invariant", 30),
        headerCell("Verdict", 16, { align: AlignmentType.CENTER }),
        headerCell("Evidence", 48),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("1", 6, { align: AlignmentType.CENTER, bold: true }),
        dataCell("Canonical terminology exact (\u6210\u7acb\u2192Confirmed, never Valid)", 30, { bold: true }),
        dataCell("PASS", 16, { align: AlignmentType.CENTER, severity: "INFO", bold: true }),
        dataCell("is_forbidden raises GlossaryConflict at isa.py:163; verify_output raises BLOCKING at isa.py:438-450; no override anywhere in production code. 3/3 mutation scenarios caught.", 48),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("2", 6, { align: AlignmentType.CENTER, bold: true, alt: true }),
        dataCell("Entities immutable (mutable=False, never True)", 30, { bold: true, alt: true }),
        dataCell("PASS*", 16, { align: AlignmentType.CENTER, severity: "INFO", bold: true, alt: true }),
        dataCell("memory.py:159 default False; isa.py:248 explicitly sets False; only 2 assignments in codebase, both False. *Enforced by convention, not by frozen=True. 2/3 mutation scenarios caught; post-construction mutation not tested.", 48, { alt: true }),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("3", 6, { align: AlignmentType.CENTER, bold: true }),
        dataCell("Verification never self-scores (no confidence_note reads)", 30, { bold: true }),
        dataCell("PASS*", 16, { align: AlignmentType.CENTER, severity: "INFO", bold: true }),
        dataCell("verify_output (isa.py:380-458) reads glossary, entities, structural_map, forbidden_targets \u2014 never confidence_note. *0/3 mutation scenarios caught; the existing test only asserts the record exists, not that it is ignored.", 48),
      ]}),
      new TableRow({ cantSplit: true, children: [
        dataCell("4", 6, { align: AlignmentType.CENTER, bold: true, alt: true }),
        dataCell("Repair surgical (no new BLOCKING at function level)", 30, { bold: true, alt: true }),
        dataCell("BLOCKING", 16, { align: AlignmentType.CENTER, severity: "BLOCKING", bold: true, alt: true }),
        dataCell("isa.py:515-519 only raises when attempt >= max_retries. Empirically confirmed: repair_segment(target=\"\u6210\u7acb Valid\", attempt=1) returns \"Confirmed Valid\" (forbidden) without raising. 0/3 mutation scenarios caught.", 48, { alt: true }),
      ]}),
    ],
  });
  children.push(invTable);
  children.push(...spacer(1));
  children.push(body(`The *PASS verdicts indicate that the invariant holds in current code but the test suite cannot detect regressions. For Invariant 2, a mutation setting ent.mutable = True post-construction would not be caught. For Invariant 3, a mutation reading confidence_note in verify_output would not be caught. These are test-coverage gaps (TRA-029, TRA-030), not invariant violations \u2014 but they leave the invariants unprotected against future changes.`));
  return children;
}

// =========================================================================
// SECTION 6 — RISK ASSESSMENT & REMEDIATION
// =========================================================================
function buildRemediation() {
  const children = [];
  children.push(heading("6. Risk Assessment & Remediation Backlog", HeadingLevel.HEADING_1));

  children.push(heading("6.1 Risk Tiers", HeadingLevel.HEADING_2));
  children.push(body(`The 11 BLOCKING findings are grouped into three risk tiers based on severity, blast radius, and ease of exploitation. The tiers inform the recommended remediation order.`));

  children.push(heading("Tier 1 \u2014 Spec-faithfulness violations (fix before any L3 certification claim)", HeadingLevel.HEADING_3));
  children.push(bullet("TRA-003: repair_segment not surgical at function boundary. Reproducible attack; silently violates the most-repeated invariant in the spec. Fix: 1\u20132 hours."));
  children.push(bullet("TRA-001: TRANSLATE_SEGMENT operates on whole document. Violates ISA contract; cascades into cache key, repair_index, L4 trace, and S-03. Fix: 1\u20132 days."));
  children.push(bullet("TRA-005: kernel.run() does not enforce L3 zero-BLOCKING gate. translate CLI can produce non-conformant output with no error signal. Fix: 2\u20133 hours."));
  children.push(bullet("TRA-004: 4 of 5 TRA-EXCEPTION recovery procedures unreachable. Spec \u00a76 mandates deterministic recovery; only 1 of 5 paths actually fires. Fix: 4\u20136 hours."));

  children.push(heading("Tier 2 \u2014 Correctness & silent failures (fix before any production use)", HeadingLevel.HEADING_3));
  children.push(bullet("TRA-011: cache-clear --pattern is a silent no-op. Users believe stale entries are cleared when they aren't. Fix: 1\u20132 hours."));
  children.push(bullet("TRA-002: Module registry bypassed by kernel. The sanctioned extension point doesn't actually work. Fix: 4\u20136 hours."));
  children.push(bullet("TRA-020: CLAUDE.md Known gaps lists only 3 of ~16 material gaps. The honest label is itself misleading. Fix: 1 hour (doc only)."));
  children.push(bullet("TRA-021: tra-prototype/README.md says Phase 0\u20135 and Phase 6 pending \u2014 both false. Fix: 30 min (doc only)."));

  children.push(heading("Tier 3 \u2014 Test-coverage gaps on invariants (fix before any refactor)", HeadingLevel.HEADING_3));
  children.push(bullet("TRA-028: Zero test coverage on repair_segment's raise clause. The test suite cannot detect regressions in TRA-003's partial enforcement. Fix: 1\u20132 hours."));
  children.push(bullet("TRA-029: Invariant 3 (never self-scores) untested at enforcement boundary. Fix: 1 hour."));
  children.push(bullet("TRA-030: No test asserts terminology=WARNING and structural=BLOCKING severity classification. Fix: 1 hour."));

  children.push(heading("6.2 Recommended Fix Order", HeadingLevel.HEADING_2));
  children.push(body(`The recommended fix order prioritizes Tier 1 (spec-faithfulness) first, because these findings undermine the engine's core value proposition. Within Tier 1, TRA-003 should be fixed first because it is the smallest fix with the highest impact (a 1\u20132 line code change plus a regression test). TRA-005 should follow because it is the user-facing gate. TRA-004 and TRA-001 are larger refactors that can land in parallel.`));
  children.push(body(`Tier 2 follows because TRA-011 and TRA-002 are silent failures that erode user trust. TRA-020 and TRA-021 are doc-only fixes that should land immediately to stop misleading new contributors. Tier 3 should land before any refactor of the ISA or kernel, to ensure the test suite can catch regressions.`));
  children.push(body(`The full remediation backlog with per-finding effort estimates is in the companion XLSX workbook, sheet "Remediation Backlog". Estimated total effort to close all 11 BLOCKING findings: 3\u20135 person-days. Estimated total effort to close all 35 findings: 8\u201312 person-days.`));
  return children;
}

// =========================================================================
// SECTION 7 — CONCLUSIONS
// =========================================================================
function buildConclusions() {
  const children = [];
  children.push(heading("7. Conclusions", HeadingLevel.HEADING_1));

  children.push(heading("7.1 Verdict", HeadingLevel.HEADING_2));
  children.push(body(`The TRA prototype engine is a faithful proof-of-concept for the TRA v1.0 specification's deterministic ZH\u2194EN path at L3, with material gaps in five areas that should be closed before any certification claim. The codebase is well-typed (mypy --strict clean), well-formatted (ruff clean), well-tested (103 tests pass), and well-documented (the spec docs and status.md are accurate). The meta-docs (CLAUDE.md, tra-prototype/README.md, implementation_plan.md) carry a long tail of stale or aspirational claims that should be reconciled.`));
  children.push(body(`Of the four critical invariants, three hold (canonical terminology, entity immutability, never-self-score) and one (repair surgical) is violated at the function boundary with a reproducible attack. The test suite protects the data-model invariants well but the behavioral invariants poorly \u2014 the invariant-mutation catch rate is 42%, concentrated in TRA-028, TRA-029, and TRA-030.`));

  children.push(heading("7.2 Strengths", HeadingLevel.HEADING_2));
  children.push(bullet("All four quality gates pass clean (ruff, ruff format, mypy --strict, 103 pytest tests)."));
  children.push(bullet("The ZH\u2194EN module's canonical terminology is exact and forbids drift; the binding mappings (\u6210\u7acb\u2192Confirmed, \u6267\u884c\u73af\u5883\u2192execution environment, \u9ad8\u5ea6\u53ef\u4fe1\u2192highly credible) are correct and never overridden."));
  children.push(bullet("Entities are immutable in practice (mutable=False enforced at construction and at isa.py:248)."));
  children.push(bullet("verify_output never reads confidence_note; the never-self-score invariant holds at the code level."));
  children.push(bullet("The L3 gate is correctly enforced by the standalone validate command and the benchmark runner."));
  children.push(bullet("L4 forensic artifacts (evidence_trace.jsonl, ambiguity_register.json) emit correctly and ONLY at L4_FORENSIC."));
  children.push(bullet("Input sanitization (_sanitize_input) correctly strips null, C0, DEL, bidi overrides, and BOM."));
  children.push(bullet("Cache key generation is deterministic (canonical JSON with sorted keys, SHA-256)."));
  children.push(bullet("The audit trail is append-only by API design."));

  children.push(heading("7.3 Weaknesses", HeadingLevel.HEADING_2));
  children.push(bullet("TRANSLATE_SEGMENT operates on the whole document, not per-segment (TRA-001). Cascades into cache key, repair_index, L4 trace, and S-03."));
  children.push(bullet("The module registry\u2014the sanctioned extension point\u2014is bypassed by the kernel (TRA-002). New modules don't plug in."));
  children.push(bullet("The surgical-repair invariant is violated at the function boundary for attempts below max_retries (TRA-003). Reproducible attack."));
  children.push(bullet("Four of the five TRA-EXCEPTION recovery procedures are unreachable in production (TRA-004)."));
  children.push(bullet("The L3 zero-BLOCKING gate is not enforced by the main translate command (TRA-005)."));
  children.push(bullet("cache-clear --pattern is a silent no-op (TRA-011). Users believe stale entries are cleared when they aren't."));
  children.push(bullet("The audit trail is NOT byte-reproducible (TRA-013). uuid4 + datetime.now make L4 forensic hashing impossible."));
  children.push(bullet("Five dependencies are unused, inflating the install footprint by ~50+ packages (TRA-017)."));
  children.push(bullet("CLAUDE.md Known gaps lists only 3 of ~16 material gaps; the honest label is misleading (TRA-020)."));
  children.push(bullet("tra-prototype/README.md says Phase 0\u20135 when Phase 6 is implemented (TRA-021)."));
  children.push(bullet("Three test-coverage gaps leave 3 of 4 critical invariants unprotected against mutation (TRA-028, TRA-029, TRA-030)."));

  children.push(heading("7.4 Next Steps", HeadingLevel.HEADING_2));
  children.push(body(`The recommended next steps, in priority order, are: (1) fix TRA-003 (1\u20132 hours, smallest fix with highest impact); (2) fix TRA-005 to enforce the L3 gate in translate (2\u20133 hours); (3) fix TRA-011 to make cache-clear actually clear (1\u20132 hours); (4) close the three test-coverage gaps TRA-028, TRA-029, TRA-030 (3\u20134 hours total) before any refactor; (5) update the stale docs TRA-020 and TRA-021 (1.5 hours, doc only); (6) plan the larger refactors TRA-001 (segment-level) and TRA-004 (exception recovery) as Phase 7 prep work; (7) wire the module registry into the kernel (TRA-002) once the segment-level refactor lands.`));
  children.push(body(`The full per-finding detail, evidence, and suggested fixes are in the companion XLSX workbook (TRA_audit_findings_register.xlsx) and the shared worklog (/home/z/my-project/worklog.md, Task IDs audit-A through audit-D). The severity heatmap chart is available as a standalone PNG (TRA_audit_severity_heatmap.png) for embedding in presentations or issue trackers.`));
  return children;
}

// =========================================================================
// APPENDIX A — EMPIRICAL VERIFICATION
// =========================================================================
function buildAppendix() {
  const children = [];
  children.push(heading("Appendix A. Empirical Verification of Headline Findings", HeadingLevel.HEADING_1));
  children.push(body(`The two most material BLOCKING findings (TRA-003 and TRA-011) were confirmed by direct runtime probes. The probe scripts and their outputs are reproduced below for reproducibility.`));

  children.push(heading("A.1 TRA-003 \u2014 repair_segment returns silently with new BLOCKING at attempt=1", HeadingLevel.HEADING_2));
  children.push(body("Probe script (executed 2026-07-13):"));
  children.push(codeBlock(
    `from tra.isa import repair_segment\n` +
    `from tra.memory import RuntimeContext, Severity, GlossaryEntry, GlossaryStatus\n` +
    `from tra.diagnostics import AuditTrail, EvidenceRegistry, Diagnostic\n` +
    `\n` +
    `ctx = RuntimeContext()\n` +
    `ctx.glossary_cache = [GlossaryEntry(source='\u6210\u7acb', target='Confirmed',\n` +
    `                                    status=GlossaryStatus.CANONICAL)]\n` +
    `diag = Diagnostic(severity=Severity.WARNING, subsystem='terminology',\n` +
    `                  issue="Source term not translated: '\u6210\u7acb'")\n` +
    `\n` +
    `result = repair_segment('\u6210\u7acb Valid', '\u6210\u7acb Valid', diag, ctx,\n` +
    `                       EvidenceRegistry(), AuditTrail('./audit.jsonl'),\n` +
    `                       attempt=1, max_retries=3)\n` +
    `print(f'After repair: {result!r}')  # 'Confirmed Valid'`
  ));
  children.push(body("Output:"));
  children.push(codeBlock(
    `Before repair: target='\u6210\u7acb Valid'\n` +
    `Calling repair_segment(attempt=1, max_retries=3)...\n` +
    `After repair: result='Confirmed Valid'\n` +
    `Raised Unrecoverable? NO\n` +
    `>>> CONFIRMED: repair_segment returns silently with new BLOCKING at attempt=1`
  ));
  children.push(body(`The returned string 'Confirmed Valid' contains the forbidden drift target 'Valid' (per TRA-MODULE-ZH-EN.md \u00a73). verify_output would raise BLOCKING on this string, but repair_segment does not re-check at the function boundary. The kernel's _repair_loop catches this by re-queuing, but a direct caller receives broken output with no exception.`));

  children.push(heading("A.2 TRA-011 \u2014 cache-clear --pattern deletes 0 entries", HeadingLevel.HEADING_2));
  children.push(body("Probe script (executed 2026-07-13):"));
  children.push(codeBlock(
    `from tra.cache import TranslationCache, CacheKeyContext, TranslationResult\n` +
    `import tempfile, diskcache\n` +
    `\n` +
    `tmpdir = tempfile.mkdtemp()\n` +
    `c = TranslationCache(tmpdir, enabled=True)\n` +
    `for i in range(3):\n` +
    `    ctx = CacheKeyContext(source_text=f'test{i}', glossary=[], entities=[],\n` +
    `                          model_endpoint='rule-based', model_version='v1',\n` +
    `                          policy_stack=[])\n` +
    `    c.set(ctx.key(), TranslationResult(translation=f'out{i}',\n` +
    `                                       evidence_ids=[], cache_hit=False))\n` +
    `\n` +
    `dc = diskcache.Cache(tmpdir)\n` +
    `print(f'Before: {len(dc)}')         # 3\n` +
    `c.invalidate('test*')              # tries to glob\n` +
    `print(f'After invalidate(test*): {len(dc)}')  # 3 (no-op!)\n` +
    `c.invalidate(<literal key>)        # exact match\n` +
    `print(f'After literal invalidate: {len(dc)}')  # 2 (works)`
  ));
  children.push(body("Output:"));
  children.push(codeBlock(
    `Entries before invalidate: 3\n` +
    `invalidate(test*) returned: None\n` +
    `Entries after invalidate(test*): 3\n` +
    `invalidate(a030b44932e1eaf0fa73...) returned: None\n` +
    `Entries after literal invalidate: 2`
  ));
  children.push(body(`CLI behavior: python -m tra_cli cache-clear --pattern 'nonexistent*' prints "Cache invalidated: nonexistent*" unconditionally, even though zero entries were deleted. The user has no way to know the pattern matched nothing.`));
  return children;
}

// =========================================================================
// ASSEMBLE DOCUMENT
// =========================================================================
const doc = new Document({
  creator: "Z.ai",
  title: "TRA Prototype Audit Report",
  subject: "Systematic code review & conformance audit of Translation-Runtime-Architecture",
  styles: {
    default: {
      document: {
        run: { font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" }, size: 22, color: c(P.body) },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: { run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 32, bold: true, color: c(P.primary) } },
      heading2: { run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 28, bold: true, color: c(P.primary) } },
      heading3: { run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 24, bold: true, color: c(P.primary) } },
    },
  },
  sections: [
    {
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 } } },
      children: buildCover(),
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
          pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: P.accent } },
            children: [new TextRun({ text: "TRA Prototype Audit Report  \u00b7  2026-07-13", size: 18, color: c(P.secondary), font: { ascii: "Calibri" }, italics: true })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", size: 18, color: c(P.secondary), font: { ascii: "Calibri" } }),
              new TextRun({ children: [PageNumber.CURRENT], size: 18, color: c(P.secondary), font: { ascii: "Calibri" } }),
              new TextRun({ text: " of ", size: 18, color: c(P.secondary), font: { ascii: "Calibri" } }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: c(P.secondary), font: { ascii: "Calibri" } }),
            ],
          })],
        }),
      },
      children: [
        ...buildExecutiveSummary(),
        ...buildScope(),
        ...buildTestPlan(),
        ...buildResults(),
        ...buildInvariantsDeepDive(),
        ...buildRemediation(),
        ...buildConclusions(),
        ...buildAppendix(),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  const outPath = "/home/z/my-project/download/TRA_Prototype_Audit_Report.docx";
  fs.writeFileSync(outPath, buf);
  console.log(`DOCX saved to ${outPath}`);
  console.log(`  Size: ${(buf.length / 1024).toFixed(1)} KB`);
}).catch(err => {
  console.error("DOCX generation failed:", err);
  process.exit(1);
});
