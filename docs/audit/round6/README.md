# TRA Audit Round 6 — Independent Re-Audit

This folder contains the deliverables, scripts, and evidence from the **Round 6
independent re-audit** of the TRA prototype engine at HEAD `c4ecd41`.

## What changed since Round 5

Round 5 (in `docs/audit/round5/`) found 68 findings at HEAD `5476faf` and
produced a 5-batch TDD remediation plan. Nine remediation commits later
(`eb3d574` through `c4ecd41`), ALL 46 R5 issues were resolved (44 fixed + 2
documented). Round 6 verifies the R5 fixes hold, hunts for NEW issues
introduced by the remediation, and checks Phase 7 documentation deliverables.

## Headline results

- **76 deduplicated findings: 58 issues + 18 positive verifications**
- **4 BLOCKING / 10 WARNING / 44 INFO** (issues only)
- **0 regressions** from R5 baseline — every R5 fix still holds
- **36 of 68 R5 entries now fixed-and-verified** (up from 0 at R5 audit)
- **27 of 68 R5 entries verified-holding** (positive verifications re-confirmed)
- **All 4 critical invariants hold** at HEAD with code-level evidence
- **TRA-013 byte-reproducibility HOLDS** within HEAD (audit_trace.jsonl sha256 `85363d55…` ×2)
- **309 tests pass** (was 228 at R5 audit; +81 from R5 remediation)
- **36/36 benchmark cases pass** (0 BLOCKING, 0 WARNING)
- **L3 CONFORMANT**

## The 4 BLOCKING findings (immediate attention)

All 4 are stale doc claims from incomplete R5 Batch I doc-refresh:

1. **TRA-C6-001** — CLAUDE.md:15 says "Phase 7 has not started" (line 56 says "Phase 7 COMPLETE")
2. **TRA-C6-002** — README.md:114 says "Phase 7 has not started"
3. **TRA-C6-003/004/005/006** — tra-prototype/README.md + SKILL.md stale "Known gaps" entries (TRA-001, TRA-079, TRA-094 all fixed but docs say "deferred"/"persistent")

## The 10 WARNING findings

1. **TRA-A6-001** — Cache-hit suppresses EXCEPTION_HANDLER records for UnknownTerm
2. **TRA-A6-002** — `_repair_loop` doesn't pass `segment_index` to `repair_segment`
3. **TRA-D6-001** — Test fails on 2nd pytest run (cache pollution; test isolation)
4. **TRA-D6-002** — `mutmut run` crashes (deprecated config keys in pyproject.toml)
5. **TRA-D6-003** — 15 hardcoded absolute paths in test_outstanding_findings.py
6. **TRA-D6-004** — Vacuous test (test_entity_ambiguity...)
7. **TRA-D6-005** — Wrong field name `level` instead of `conformance_level` in `model_copy`
8. **TRA-D6-006** — Vacuous HITL e2e tests (don't trigger Unrecoverable)
9. **TRA-E6-001** — `audit_trace.jsonl` append mode breaks reproducibility on reused path
10. **TRA-B6-008** — mutmut 3.6+ config-key deprecation (same as D6-002)

## Audit structure

7-track parallel re-audit:

| Track | Scope | Findings |
|---|---|---|
| R6 | Regression baseline (68 R5 entries) | 36 fixed / 27 verified-holding / 2 partial / 2 persistent / 1 documented / 0 new-regression |
| A6 | Spec conformance | 11 (0 BLOCKING / 2 WARNING / 9 INFO) |
| B6 | Code quality & security | 16 (0 BLOCKING / 1 WARNING / 15 INFO) |
| C6 | Doc-vs-code consistency | 14 (4 BLOCKING / 4 WARNING / 6 INFO) |
| D6 | Test suite | 19 (1 BLOCKING / 5 WARNING / 13 INFO) |
| E6 | Forensic L4 end-to-end | 11 (0 BLOCKING / 3 WARNING / 8 INFO) |
| F6 | Stub-module conformance | 8 (0 BLOCKING / 0 WARNING / 8 INFO) |

## Files

### Deliverables

| File | Description |
|---|---|
| `TRA_Prototype_Audit_Report_r6.docx` | Formal narrative report |
| `TRA_audit_findings_register_r6.xlsx` | 10-sheet register |
| `TRA_audit_severity_heatmap_r6.png` | Severity-by-track matrix |
| `master_findings_register_r6.json` | Machine-readable 76-finding register |
| `summary.json` / `summary.txt` | Counts by severity/track/R5 status |
| `remediation_plan_r6.md` | TDD remediation plan (~6.5 hours est.) |

### Per-track evidence

| File | Track | Findings |
|---|---|---|
| `track_r6_baseline.md` | R6 | 68-row regression baseline |
| `track_a6_findings.md` | A6 | 11 spec-conformance findings |
| `track_b6_findings.md` | B6 | 16 code-quality findings |
| `track_c6_findings.md` | C6 | 14 doc-consistency findings |
| `track_d6_findings.md` | D6 | 19 test-suite findings |
| `track_e6_findings.md` | E6 | 11 forensic L4 findings |
| `track_f6_findings.md` | F6 | 8 stub-module findings |

### Generator scripts (in `tra-audit-skills/round6/scripts/`)

| Script | Purpose |
|---|---|
| `synthesize_findings_r6.py` | Reads 7 per-track .md files, writes master JSON |
| `normalize_r6_register.py` | Normalizes severities, rebuilds summary |
| `generate_heatmap_r6.py` | matplotlib heatmap PNG |
| `generate_xlsx_r6.py` | openpyxl 10-sheet workbook |
| `generate_docx_r6.py` | python-docx formal report |

## Key R5 → R6 progress

| Metric | R5 audit | R6 audit | Delta |
|---|---|---|---|
| HEAD | `5476faf` | `c4ecd41` | +9 commits |
| Test count | 228 | 309 | +81 |
| Benchmark cases | 24 | 36 | +12 |
| BLOCKING issues | 0 | 4 | +4 (all doc-staleness) |
| WARNING issues | 7 | 10 | +3 (new from remediation) |
| Fixed-and-verified | 0 | 36 | +36 |
| Positive verifications | 22 | 18 | -4 (absorbed into fixed) |
| TRA-013 sha256 | `902298b3…` | `85363d55…` | changed (per-leaf translation) |

## See also

- `../round5/` — Round 5 audit (68 findings at HEAD `5476faf`)
- `../round4/` — Round 4 audit (66 findings at HEAD `805a8f8`)
- `../round3/` — Round 3 audit (36 findings at HEAD `b783745`)
- `../round2/` — Round 2 audit (41 findings at HEAD `4b8827c`)
- `../` (top level) — Round 1 audit (35 findings)
- `../../tra-audit-skills/` — reusable skills bundle
