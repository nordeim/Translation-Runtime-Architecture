# TRA Audit Round 4 — Independent Re-Audit

This folder contains the deliverables, scripts, and evidence from the **Round 4
independent re-audit** of the TRA prototype engine at HEAD `805a8f8`.

## What changed since Round 3

Round 3 (in `docs/audit/round3/`) found 36 findings at HEAD `b783745` and
produced a 5-batch TDD remediation plan. Six commits later (`df9a590` through
`805a8f8`), most of the Round 3 remediation plan was executed. Round 4 treats
the 36 Round-3 findings as the regression baseline and additionally hunts for
new issues introduced by the remediation commits AND for documentation drift
caused by the rapid remediation.

## Headline results

- **47 issues: 1 BLOCKING / 11 WARNING / 35 INFO**
- **19 positive verifications** (invariants holding, fixes confirmed)
- **20 of 36 Round-3 findings fully fixed** at HEAD
- **12 persistent + 4 partial** carry-overs
- **0 regressions** — every R3 fix that landed is still present
- **Both Round 3 BLOCKING findings (TRA-093, TRA-096) verified FIXED**
- **All 4 critical invariants hold** at HEAD with code-level evidence
- **TRA-013 byte-reproducibility holds** — audit_trace.jsonl sha256 `263b901e...` (matches R3 exactly)
- **3 OWASP security fixes (TRA-076/077/078) verified holding**, mutation-tested
- **All 4 quality gates green** — ruff, mypy --strict (0 issues), pytest (199 passed)

## The 1 BLOCKING finding (immediate attention)

1. **TRA-C4-013** — `tra-prototype/README.md` "Commands" section uses bare `tra_cli.py` invocations. File is mode 664 (not executable), no shebang, no `[project.scripts]` entry point. All 4 CLI examples fail as written. User-facing onboarding break; 4-line README fix.

## Audit structure

7-track parallel re-audit using Round 3's methodology template:

| Track | Scope | Findings |
|---|---|---|
| R4 | Regression baseline (36 Round-3 findings) | 12 persistent / 4 partial / 20 fixed |
| A4 | Spec conformance (Kernel, ISA, Policy, Memory, Exceptions, L3/L4) | 11 (0/6/5) |
| B4 | Code quality & security (types, errors, cache, deps, reproducibility, OWASP) | 17 (0/3/14) |
| C4 | Doc-vs-code consistency (12 docs) | 17 (1/9/7) |
| D4 | Test suite (coverage, mutation, benchmark, HITL, LLM seam) | 15 (0/5/10) |
| E4 | Forensic L4 end-to-end (artifact structure, byte-reproducibility, probes) | 15 (0/2/13) |
| F4 | Stub-module conformance (TRA-096/099 + edge cases) | 7 (0/2/5) |

## Files

### Deliverables

| File | Description |
|---|---|
| `TRA_Prototype_Audit_Report_r4.docx` | Formal narrative report (cover, exec summary, methodology, track summaries, all findings, conclusion) |
| `TRA_audit_findings_register_r4.xlsx` | 10-sheet register (Summary, Findings, Track A4-F4, R3 Status, Remediation Backlog) |
| `TRA_audit_severity_heatmap_r4.png` | Severity-by-track matrix (issues only) |
| `master_findings_register_r4.json` | Machine-readable 66-finding register (47 issues + 19 positive verifications) |
| `summary.json` / `summary.txt` | Counts by severity, track, category, Round 3 status |
| `remediation_plan_r4.md` | 5-batch TDD remediation plan (76.5 hours est.) |

### Per-track evidence

| File | Track | Findings |
|---|---|---|
| `track_r4_baseline.md` | R4 | 36-row regression baseline table |
| `track_a4_findings.md` | A4 | 11 spec-conformance findings |
| `track_b4_findings.md` | B4 | 17 code-quality & security findings |
| `track_c4_findings.md` | C4 | 17 doc-consistency findings (1 BLOCKING) |
| `track_d4_findings.md` | D4 | 15 test-suite findings |
| `track_e4_findings.md` | E4 | 15 forensic L4 findings |
| `track_f4_findings.md` | F4 | 7 stub-module findings |

### Generator scripts (in `tra-audit-skills/round4/scripts/`)

| Script | Purpose |
|---|---|
| `synthesize_findings_r4.py` | Reads 7 per-track Markdown files, dedupes by root finding ID, writes master JSON |
| `normalize_r4_register.py` | Normalizes severity values (collapses parenthetical qualifiers), rebuilds summary |
| `generate_heatmap_r4.py` | matplotlib heatmap PNG (issues only, 6 tracks × 3 severities) |
| `generate_xlsx_r4.py` | 10-sheet XLSX workbook via openpyxl |
| `generate_docx_r4.py` | Formal DOCX report via python-docx |

## Regenerating the deliverables

```bash
cd /home/z/my-project/Translation-Runtime-Architecture

# Re-run synthesis (reads per-track .md files, writes master JSON)
python3 tra-audit-skills/round4/scripts/synthesize_findings_r4.py
python3 tra-audit-skills/round4/scripts/normalize_r4_register.py

# Regenerate the chart / XLSX / DOCX
python3 tra-audit-skills/round4/scripts/generate_heatmap_r4.py
python3 tra-audit-skills/round4/scripts/generate_xlsx_r4.py
python3 tra-audit-skills/round4/scripts/generate_docx_r4.py
```

The master register (`master_findings_register_r4.json`) is the single source
of truth consumed by the three generators.

## Methodology

Round 4 followed the same 7-track parallel structure as Round 3. Each track's
draft findings were re-checked against the cited code at HEAD before synthesis.
Severity lexicon mirrors the TRA spec: BLOCKING / WARNING / INFO. No
escalation or de-escalation from Round 3 without explicit justification.

The audit was executed in 3 batches:
- **Batch 1**: Tracks R4 + A4 + B4 (parallel) — committed as `fb4cdac`.
- **Batch 2**: Tracks C4 + D4 + E4 (parallel) — committed as `be123c6`.
- **Batch 3**: Track F4 + synthesis + deliverables — this commit.

## See also

- `../round3/` — Round 3 audit (36 findings at HEAD `b783745`)
- `../round2/` — Round 2 audit (41 findings at HEAD `4b8827c`)
- `../` (top level) — Round 1 audit (35 findings)
- `../../tra-audit-skills/` — reusable skills bundle (SSH wrapper, generator templates)
