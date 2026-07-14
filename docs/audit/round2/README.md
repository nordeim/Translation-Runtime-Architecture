# TRA Audit Round 2 — Independent Re-Audit

This folder contains the deliverables, scripts, and evidence from the **Round 2
independent re-audit** of the TRA prototype engine at HEAD `4b8827c`.

## What changed since Round 1

Round 1 (in `docs/audit/` and `tra-audit-skills/`) found 35 findings and
remediated 34 of them via TDD cycles (commits `116f77c` through `419ca31`).
Round 2 treats the 35 Round-1 findings as the regression baseline and
additionally hunts for new issues introduced by the remediation commits.

## Headline results

- **41 findings: 3 BLOCKING / 25 WARNING / 13 INFO**
- **30 of 35 Round-1 findings fully fixed** at HEAD
- **5 carry-overs** (TRA-001 partial, TRA-006 half-fix, TRA-016/017/026 persistent)
- **36 new findings** (TRA-036 through TRA-071)
- **All 4 critical invariants hold** at HEAD
- **TRA-013 fully remediated** — byte-identical L4 runs (sha256sum-verified)
- **All 4 quality gates green** — ruff ✓ · ruff format (35 files) ✓ · mypy --strict (20 files) ✓ · pytest (141 tests) ✓

## Audit structure

5-track parallel re-audit using Round 1's methodology template:

| Track | Scope | Findings |
|---|---|---|
| R | Regression baseline (35 Round-1 findings) | 5 carry-overs |
| A | Spec conformance (Kernel, ISA, Policy, Memory, Exceptions, L3/L4) | 11 (0/7/4) |
| B | Code quality & security (types, errors, cache, deps, reproducibility) | 7 (0/6/1) |
| C | Doc-vs-code consistency (14 docs) | 10 (0/4/6) |
| D | Test suite (coverage, mutation, benchmark, HITL, LLM seam) | 13 (1/8/4) |
| E | Forensic L4 end-to-end (artifact structure, byte-reproducibility, probes) | 6 (2/3/1) |

## The 3 BLOCKING findings (immediate attention)

1. **TRA-036** — Analyze-failure early `return ''` (kernel.py:214) bypasses the L3 gate.
2. **TRA-037** — `_rewrite_anchors` runs AFTER the L3 gate; audit trail hashes pre-rewrite target.
3. **TRA-048** — LLM-degradation "single audit record" invariant (TRA-015) is unprotected by tests.

## Files

### Deliverables

| File | Description |
|---|---|
| `TRA_Prototype_Audit_Report_r2.docx` | Formal narrative report (cover, exec summary, methodology, all findings, recommendations, conclusion) |
| `TRA_audit_findings_register_r2.xlsx` | 9-sheet register (Summary, Findings, Track A-E, Round1 Status, Remediation Backlog) |
| `TRA_audit_severity_heatmap_r2.png` | Severity-by-track matrix |
| `master_findings_register.json` | Machine-readable 41-finding register |
| `audit_worklog_r2.md` | Full multi-agent worklog (Task IDs: audit-R, audit-A2, audit-B2, audit-C2, audit-D2, audit-E, audit-synthesis) |

### Per-track evidence

| File | Track | Findings |
|---|---|---|
| `track_r_baseline.md` | R | 35-row regression baseline table |
| `track_a_findings.md` | A | 11 spec-conformance findings |
| `track_b_findings.md` | B | 13 code-quality & security findings |
| `track_c_findings.md` | C | 16 doc-consistency findings |
| `track_d_findings.md` | D | 18 test-suite findings |
| `track_e_findings.md` | E | 12 forensic L4 findings |

## Regenerating the deliverables

The generator scripts live in `tra-audit-skills/round2/scripts/`:

```bash
# Re-run the Track R regression baseline
python3 tra-audit-skills/round2/scripts/track_r_baseline.py

# Synthesize the master register (dedupe across tracks)
python3 tra-audit-skills/round2/scripts/synthesize_findings.py

# Regenerate the chart / XLSX / DOCX
python3 tra-audit-skills/round2/scripts/generate_heatmap.py
python3 tra-audit-skills/round2/scripts/generate_xlsx.py
python3 tra-audit-skills/round2/scripts/generate_docx.py
```

The master register (`master_findings_register.json`) is the single source of
truth consumed by the three generators.

## Methodology

Round 2 followed the same 4-track parallel structure as Round 1 (extended to
5 tracks with Track R for regression baseline and Track E for forensic L4
end-to-end verification). Each track's draft findings were re-checked against
the cited code at HEAD before synthesis. Severity lexicon mirrors the TRA spec:
BLOCKING / WARNING / INFO.

See `audit_worklog_r2.md` for the full per-task work log and `../worklog.md`
(Round 1's worklog) for the methodology template.
