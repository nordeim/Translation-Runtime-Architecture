# TRA Audit Round 5 — Independent Re-Audit

This folder contains the deliverables, scripts, and evidence from the **Round 5
independent re-audit** of the TRA prototype engine at HEAD `5476faf`.

## What changed since Round 4

Round 4 (in `docs/audit/round4/`) found 47 issues + 19 positive verifications
(66 total) at HEAD `805a8f8` and produced a 5-batch TDD remediation plan. Nine
commits later (`f226582` through `5476faf`), R4 remediation Batches 1+2 were
executed. Round 5 treats the 66 Round-4 entries as the regression baseline and
additionally hunts for new issues introduced by the remediation commits AND for
any residual documentation drift.

## Headline results

- **68 deduplicated findings: 46 issues + 22 positive verifications**
- **0 BLOCKING / 7 WARNING / 39 INFO** (issues only)
- **0 regressions** — every R4 fix that landed is still present
- **R4 BLOCKING finding (TRA-C4-013) verified FIXED** (tra-prototype/README.md CLI examples)
- **All 4 critical invariants hold** at HEAD with code-level evidence
- **TRA-013 byte-reproducibility HOLDS within HEAD** — `audit_trace.jsonl` sha256 `902298b3...` x2 (matches R5 baseline; differs from R4's `263b901e...` because R4 Batch 2 enriched audit-trail content via TRA-038/042/072)
- **3 OWASP security fixes (TRA-076/077/078) verified holding**, mutation-tested
- **All 4 quality gates green** — ruff, mypy --strict (0 issues, 20 source files), pytest (228 passed in 1.16s)
- **R4 Batch 2 spec-conformance fixes verified holding**: TRA-038 (3 exception types wired), TRA-042 (6 structural check categories), TRA-072 (4 PolicyResolver call sites), TRA-092 (24/24 benchmark cases), TRA-099 (CLI registry wiring), TRA-100 (module authoring guide)

## The 7 WARNING findings (priority for Batch 1–3 remediation)

1. **TRA-C5-001** — "228 tests across 18 test files" wrong in 4 docs (actual: 16 test files). Persistent from R4 typo.
2. **TRA-C5-003** — `implementation_plan.md:346` "34 classes, 139 tests" stale (actual: 46 classes, 91 tests).
3. **TRA-C5-004** — `tra-prototype/README.md:90-95` "Known gaps" TRA-099 entry misleading (FIXED in R4 Batch 1).
4. **TRA-C5-007** (new-regression) — `tra-prototype/README.md:117-118` "22 of 24 spec cases" stale (now 24/24 after R4 Batch 2).
5. **TRA-A5-005** — TRA-042 structural verification regex gaps (ordered-list missing; `>text` blockquote too narrow).
6. **TRA-A5-013** (new) — No factual-integrity check in `verify_output`; `FACTUAL_INTEGRITY` (P1) never arbitrated.
7. **TRA-D5-002** — e2e LLM hijack uses module-level patching (TRA-090 persistent).
8. **TRA-D5-007** — `interactive=True` kernel path untested e2e (TRA-091 persistent).

(Six WARNINGs above + TRA-E5-016 = 7 total. TRA-E5-016 is a new WARNING about `ambiguity_register.json` non-determinism across cache states — deferred, see remediation_plan_r5.md.)

## Audit structure

7-track parallel re-audit using Round 4's methodology template:

| Track | Scope | Findings |
|---|---|---|
| R5 | Regression baseline (66 Round-4 entries) | 21 fixed-and-verified / 19 persistent / 4 partial / 0 new-regression / 22 verified-holding |
| A5 | Spec conformance (Kernel, ISA, Policy, Memory, Exceptions, L3/L4) | 15 (0/6/9) |
| B5 | Code quality & security (types, errors, cache, deps, reproducibility, OWASP) | 22 (0/0/22) |
| C5 | Doc-vs-code consistency (12 docs) | 22 (0/9/13) |
| D5 | Test suite (coverage, mutation, benchmark, HITL, LLM seam) | 20 (0/3/17) |
| E5 | Forensic L4 end-to-end (artifact structure, byte-reproducibility, probes) | 20 (0/2/18) |
| F5 | Stub-module conformance (TRA-096/099 + edge cases) | 13 (0/1/12) |

Note: per-track counts include positive verifications; the deduplicated master register has 68 entries total (46 issues + 22 positive verifications).

## Files

### Deliverables

| File | Description |
|---|---|
| `TRA_Prototype_Audit_Report_r5.docx` | Formal narrative report (cover, exec summary, methodology, track summaries, all findings, conclusion) |
| `TRA_audit_findings_register_r5.xlsx` | 10-sheet register (Summary, Findings, Track A5-F5, R4 Status, Remediation Backlog) |
| `TRA_audit_severity_heatmap_r5.png` | Severity-by-track matrix (issues only) |
| `master_findings_register_r5.json` | Machine-readable 68-finding register (46 issues + 22 positive verifications) |
| `summary.json` / `summary.txt` | Counts by severity, track, category, Round 4 status |
| `remediation_plan_r5.md` | 5-batch TDD remediation plan (~72.5 hours est.) |

### Per-track evidence

| File | Track | Findings |
|---|---|---|
| `track_r5_baseline.md` | R5 | 66-row regression baseline table |
| `track_a5_findings.md` | A5 | 15 spec-conformance findings |
| `track_b5_findings.md` | B5 | 22 code-quality & security findings |
| `track_c5_findings.md` | C5 | 22 doc-consistency findings |
| `track_d5_findings.md` | D5 | 20 test-suite findings |
| `track_e5_findings.md` | E5 | 20 forensic L4 findings |
| `track_f5_findings.md` | F5 | 13 stub-module findings |

### Generator scripts (in `tra-audit-skills/round5/scripts/`)

| Script | Purpose |
|---|---|
| `synthesize_findings_r5.py` | Reads 7 per-track Markdown files, dedupes by root finding ID, writes master JSON |
| `normalize_r5_register.py` | Normalizes severity values (collapses parenthetical qualifiers), rebuilds summary |
| `generate_heatmap_r5.py` | matplotlib heatmap PNG (issues only, 6 tracks × 3 severities) |
| `generate_xlsx_r5.py` | 10-sheet XLSX workbook via openpyxl |
| `generate_docx_r5.py` | Formal DOCX report via python-docx |

## Regenerating the deliverables

```bash
cd /home/z/my-project/Translation-Runtime-Architecture

# Re-run synthesis (reads per-track .md files, writes master JSON)
python3 tra-audit-skills/round5/scripts/synthesize_findings_r5.py
python3 tra-audit-skills/round5/scripts/normalize_r5_register.py

# Regenerate the chart / XLSX / DOCX
python3 tra-audit-skills/round5/scripts/generate_heatmap_r5.py
python3 tra-audit-skills/round5/scripts/generate_xlsx_r5.py
python3 tra-audit-skills/round5/scripts/generate_docx_r5.py
```

The master register (`master_findings_register_r5.json`) is the single source
of truth consumed by the three generators.

## Methodology

Round 5 followed the same 7-track parallel structure as Rounds 3 and 4. Each
track's draft findings were re-checked against the cited code at HEAD before
synthesis. Severity lexicon mirrors the TRA spec: BLOCKING / WARNING / INFO. No
escalation or de-escalation from Round 4 without explicit justification.

The audit was executed in 4 batches:
- **Batch 1**: Track R5 (regression baseline) — committed.
- **Batch 2**: Tracks A5 + B5 (parallel).
- **Batch 3**: Tracks C5 + D5 + E5 (parallel).
- **Batch 4**: Track F5 + synthesis + deliverables.

## See also

- `../round4/` — Round 4 audit (66 findings at HEAD `805a8f8`)
- `../round3/` — Round 3 audit (36 findings at HEAD `b783745`)
- `../round2/` — Round 2 audit (41 findings at HEAD `4b8827c`)
- `../` (top level) — Round 1 audit (35 findings)
- `../../tra-audit-skills/` — reusable skills bundle (SSH wrapper, generator templates)
