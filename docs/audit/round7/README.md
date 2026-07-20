# TRA Audit Round 7 — Independent Re-Audit

This folder contains the deliverables, scripts, and evidence from the **Round 7
independent re-audit** of the TRA prototype engine at HEAD `6d3144a`.

## What changed since Round 6

Round 6 (in `docs/audit/round6/`) found 76 findings at HEAD `c4ecd41` and
produced a 3-batch TDD remediation plan. One remediation commit later
(`6d3144a` — "Round 6 Batch 1 — fix 4 BLOCKING + 6 WARNING findings via TDD"),
ALL 4 R6 BLOCKING findings and 6 of the 10 R6 WARNING findings were resolved.
Round 7 verifies the R6 Batch 1 fixes hold, hunts for NEW issues introduced
by the remediation, and re-confirms the 18 R6 positive verifications.

## Headline results

- **75 deduplicated findings: 39 issues + 36 positive verifications**
- **4 BLOCKING / 18 WARNING / 53 INFO** (all severities normalized)
- **0 regressions** from R6 baseline — every R6 fix still holds
- **All 4 R6 BLOCKING findings verified FIXED** (TRA-C6-001/002/003-006, TRA-D6-001)
- **6 of 10 R6 WARNING findings verified FIXED**; 1 partial (TRA-D6-002/B6-008 mutmut config — string→list fix landed, but deprecated key names not renamed)
- **3 R6 WARNING findings still persistent** (TRA-A6-001, A6-002, D6-003, D6-004)
- **1 new WARNING escalated from R6 INFO** (TRA-B7-002 Authorization header regex leaks token — dynamically reproduced)
- **All 4 critical invariants hold** at HEAD with code-level evidence
- **TRA-013 byte-reproducibility HOLDS** within HEAD (audit_trace.jsonl sha256 `d01e7bfa22db9b35…` ×2)
- **309 tests pass** (unchanged from R6)
- **36/36 benchmark cases pass** (0 BLOCKING, 0 WARNING)
- **L3 CONFORMANT**

## The 9 outstanding WARNING findings (addressed in remediation_plan_r7.md)

1. **TRA-A7-001** — Cache-hit suppresses EXCEPTION_HANDLER records for UnknownTerm (L4 forensic completeness)
2. **TRA-A7-002** — `_repair_loop` doesn't pass `segment_index` to `repair_segment` (Phase 8 residual)
3. **TRA-A7-004** — EntityAmbiguity bypasses EXCEPTION_HANDLER audit-record path (partial-fix from A5-003)
4. **TRA-B7-001** — mutmut 3.6+ deprecated config keys (`paths_to_mutate`, `tests_dir`)
5. **TRA-B7-002** — `Authorization: Bearer <token>` regex leaks the token into audit trail (OWASP A09)
6. **TRA-C7-001** — implementation_plan.md dependencies table pinned to stale HEAD `805a8f8`
7. **TRA-C7-002** — README.md missing Round 5/6/7 audit references
8. **TRA-C7-003** — status.md banner does not pin the latest HEAD hash
9. **TRA-D7-001** — 15 hardcoded absolute paths in `test_outstanding_findings.py`

Plus TRA-D7-002 (vacuous entity-ambiguity test) — same root cause as TRA-A7-004, fixed in the same batch.

## Audit structure

7-track parallel re-audit:

| Track | Scope | Findings |
|---|---|---|
| R7 | Regression baseline (76 R6 entries) | 10 fixed-verified / 18 verified-holding / 4 partial / 44 persistent / 0 new-regression |
| A7 | Spec conformance | 11 (0 BLOCKING / 2 WARNING / 9 INFO) |
| B7 | Code quality & security | 13 (0 BLOCKING / 2 WARNING / 11 INFO) |
| C7 | Doc-vs-code consistency | 10 (0 BLOCKING / 3 WARNING / 7 INFO) |
| D7 | Test suite | 15 (0 BLOCKING / 2 WARNING / 13 INFO) |
| E7 | Forensic L4 end-to-end | 9 (0 BLOCKING / 0 WARNING / 9 INFO) |
| F7 | Stub-module conformance | 8 (0 BLOCKING / 0 WARNING / 8 INFO) |

## Files

### Deliverables

| File | Description |
|---|---|
| `TRA_Prototype_Audit_Report_r7.docx` | Formal narrative report |
| `TRA_audit_findings_register_r7.xlsx` | 10-sheet register |
| `TRA_audit_severity_heatmap_r7.png` | Severity-by-track matrix |
| `master_findings_register_r7.json` | Machine-readable 75-finding register |
| `summary.json` / `summary.txt` | Counts by severity/track/R6 status |
| `remediation_plan_r7.md` | TDD remediation plan (~8 hours est.) |

### Per-track evidence

| File | Track | Findings |
|---|---|---|
| `track_r7_baseline.md` | R7 | 76-row regression baseline |
| `track_a7_findings.md` | A7 | 11 spec-conformance findings |
| `track_b7_findings.md` | B7 | 13 code-quality findings |
| `track_c7_findings.md` | C7 | 10 doc-consistency findings |
| `track_d7_findings.md` | D7 | 15 test-suite findings |
| `track_e7_findings.md` | E7 | 9 forensic L4 findings |
| `track_f7_findings.md` | F7 | 8 stub-module findings |

### Generator scripts (in `tra-audit-skills/round7/scripts/`)

| Script | Purpose |
|---|---|
| `synthesize_findings_r7.py` | Reads 7 per-track .md files, writes master JSON |
| `normalize_r7_register.py` | Normalizes severities, rebuilds summary |
| `generate_heatmap_r7.py` | matplotlib heatmap PNG |
| `generate_xlsx_r7.py` | openpyxl 10-sheet workbook |
| `generate_docx_r7.py` | python-docx formal report |

## Key R6 → R7 progress

| Metric | R6 audit | R7 audit | Delta |
|---|---|---|---|
| HEAD | `c4ecd41` | `6d3144a` | +1 commit |
| Test count | 309 | 309 | 0 (R6 Batch 1 modified tests in place) |
| Benchmark cases | 36 | 36 | 0 |
| BLOCKING issues | 4 | 4 (all R6-fixed, status preserved) | 0 new |
| WARNING issues | 10 | 18 (9 R6-fixed + 9 outstanding) | +8 (status-qualified; 9 still open) |
| Fixed-and-verified | 0 | 10 (R6 Batch 1) | +10 |
| Positive verifications | 18 | 36 | +18 (R6 + R7 re-confirmations) |
| TRA-013 sha256 | `85363d55…` | `d01e7bfa22db9b35…` | changed (truncate-mode fix in R6 Batch 1) |

## See also

- `../round6/` — Round 6 audit (76 findings at HEAD `c4ecd41`)
- `../round5/` — Round 5 audit (68 findings at HEAD `5476faf`)
- `../round4/` — Round 4 audit (66 findings at HEAD `805a8f8`)
- `../round3/` — Round 3 audit (36 findings at HEAD `b783745`)
- `../round2/` — Round 2 audit (41 findings at HEAD `4b8827c`)
- `../` (top level) — Round 1 audit (35 findings)
- `../../tra-audit-skills/` — reusable skills bundle
