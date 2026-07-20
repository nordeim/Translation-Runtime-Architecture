# TRA Round 6 — Comprehensive TDD Remediation Plan

**Created:** 2026-07-20
**Based on:** Round 6 audit (76 findings: 58 issues + 18 positive verifications; 4 BLOCKING / 10 WARNING / 44 INFO)
**Approach:** TDD (Red → Green → Refactor → Commit) per finding
**Codebase:** `/home/z/my-project/Translation-Runtime-Architecture/` at HEAD `c4ecd41`

## Remediation Strategy

**Batch 1 — BLOCKING doc-staleness (Track C6 cluster)** — 4 findings, ~30min
**Batch 2 — WARNING fixes (mutmut config, cache-isolation, segment_index, vacuous tests, hardcoded paths, audit_trace append mode)** — 10 findings, ~4h
**Batch 3 — INFO cleanup** — 44 findings, opportunistic

---

## Batch 1: BLOCKING Doc-Staleness (4 findings, ~30min)

### 1.1 TRA-C6-001: CLAUDE.md:15 "Phase 7 has not started" contradicts line 56 "Phase 7 COMPLETE"

Fix: Update CLAUDE.md:15 to say "Phase 7 COMPLETE".

### 1.2 TRA-C6-002: README.md:114 "Phase 7 has not started"

Fix: Update README.md to reflect Phase 7 complete.

### 1.3 TRA-C6-003/004/005/006: tra-prototype/README.md + SKILL.md stale claims

Fix: Update "Known gaps" / "Known limitations" / "Remaining persistent findings" sections to reflect:
- TRA-001 FIXED (Phase 8 per-leaf translation, Batch H)
- TRA-079 FIXED (cache HMAC, Batch E)
- TRA-094 FIXED (mutmut, Batch F)
- Phase 7 COMPLETE (Batch I)

---

## Batch 2: WARNING Fixes (10 findings, ~4h)

### 2.1 TRA-D6-001/D6-002 (WARNING): Cache pollution + mutmut config broken

- **D6-001:** `test_unknown_term_emits_exception_handler_audit_record` fails on 2nd pytest run (cache pollution). Fix: override `cache_directory` in the test's `BootstrapConfig.model_copy`.
- **D6-002:** `mutmut run` crashes (deprecated config keys). Fix: update `[tool.mutmut]` in `pyproject.toml` to use `source_paths` (list) instead of `paths_to_mutate` (string).

### 2.2 TRA-A6-001 (WARNING): Cache-hit suppresses EXCEPTION_HANDLER records

Fix: Document that L4 runs should disable cache for full forensic trail, OR persist audit side-effects in cache entries.

### 2.3 TRA-A6-002 (WARNING): _repair_loop doesn't pass segment_index

Fix: Pass leaf segment index to `repair_segment` in the per-leaf translation loop.

### 2.4 TRA-D6-003 (WARNING): 15 hardcoded absolute paths in tests

Fix: Use `Path(__file__).resolve()` pattern instead of hardcoded `/home/z/my-project/...`.

### 2.5 TRA-D6-006 (WARNING): Vacuous HITL e2e tests

Fix: Use `--force-unrecoverable` flag to actually trigger the HITL path.

### 2.6 TRA-E6-001 (WARNING): audit_trace.jsonl append mode breaks reproducibility

Fix: Truncate `audit_trace.jsonl` at `TRAKernel.__init__` when the file exists.

---

## Batch 3: INFO Cleanup (44 findings, opportunistic)

Mostly doc-drift residuals, minor type-safety notes, and positive verifications. Address opportunistically during other batches.

---

## Effort Estimate

| Batch | Findings | Est. Hours |
|---|---|---|
| 1 (BLOCKING docs) | 4 | 0.5 |
| 2 (WARNING fixes) | 10 | 4 |
| 3 (INFO cleanup) | 44 | 2 |
| **Total** | **58** | **6.5 hours** |

Plus 18 positive verifications (no action needed).
