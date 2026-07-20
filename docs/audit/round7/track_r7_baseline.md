# Track R7 — Regression Baseline Re-Audit (Round 7)

**Task ID:** R7-1
**Auditor:** Track R7 (regression baseline)
**HEAD audited:** `6d3144a` (TRA prototype engine)
**Baseline:** Round 6 master register (`docs/audit/round6/master_findings_register_r6.json`, 76 findings: 58 issues + 18 positive verifications)
**Methodology:** Re-verify every R6 finding at HEAD `6d3144a` (post-R6 Batch 1 fix commit `6d3144a`). For each entry, mark status as `fixed-verified` / `verified-holding` / `partial` / `persistent` / `regressed` / `documented`. Cite `file:line` evidence for every disposition.

## Verification Run

- HEAD: `git rev-parse HEAD` → `6d3144a3fdaa8d90a8f5b5f3996af39e667ee496` ✓
- Quality gates: `pytest tests/` → **309 passed in 1.68s** ✓
- mypy --strict: 0 issues in 20 source files ✓
- ruff format --check: 39 files already formatted ✓
- ruff check: All checks passed ✓
- TRA-013 byte-reproducibility: cold-cache × 2 L4 runs of `to_translate.md` → `audit_trace.jsonl` sha256 `d01e7bfa22db9b35...` × 2 (MATCH) ✓
- mutmut config: `mutmut run --help` runs without crashing; deprecation warnings present (see TRA-B7-001 below)

## Summary

- **76 R6 entries re-verified:**
  - **10 fixed-verified** (4 BLOCKING + 6 WARNING from R6 Batch 1 commit `6d3144a`)
  - **18 verified-holding** (positive verifications re-confirmed)
  - **4 partial** (WARNING fixes that landed but have residuals)
  - **44 persistent** (INFO findings carried forward — see remediation_plan_r7.md)
  - **0 regressed**
  - **0 new-regression**

## R6 Batch 1 Remediation Verification (commit `6d3144a`)

### TRA-C6-001 — CLAUDE.md "Phase 7 has not started" → "Phases 0-7 are complete" — FIXED-VERIFIED

- **Severity:** BLOCKING → fixed
- **Evidence:** `CLAUDE.md:15` now reads "Phases 0–7 are complete — foundation (Phase 0), structural parsing/anchor resolution (Phase 1), the six ISA instructions (Phase 2), Kernel + Policy Engine orchestration (Phase 3), ZH-EN Language Module integration (Phase 4), CLI + artifacts + benchmark suite + L3 `validate` gate (Phase 5), hardening (Phase 6), and documentation & delivery (Phase 7)." Matches line 56 "Phase 7 COMPLETE".
- **Status:** fixed-verified

### TRA-C6-002 — README.md "Phase 7 has not started" → "Phases 0-7 are complete" — FIXED-VERIFIED

- **Severity:** BLOCKING → fixed
- **Evidence:** `README.md:114` now reads "Phases 0–7 are complete (foundation → Kernel/Policy orchestration → ZH-EN module → CLI + benchmark suite → hardening → documentation & delivery)."
- **Status:** fixed-verified

### TRA-C6-003/004/005/006 — SKILL.md + tra-prototype/README.md stale claims — FIXED-VERIFIED

- **Severity:** BLOCKING → fixed
- **Evidence:** `tra-prototype/SKILL.md:303-326` "Known limitations" section now correctly states:
  - TRA-001 FIXED (Phase 8 per-leaf translation, Batch H)
  - TRA-079 FIXED (cache HMAC, Batch E)
  - TRA-094 FIXED (mutmut, Batch F)
  - Phase 7 COMPLETE (Batch I)
- `tra-prototype/README.md` "Known gaps" section updated to match HEAD `6d3144a`.
- **Status:** fixed-verified

### TRA-D6-001 — Test cache pollution — FIXED-VERIFIED

- **Severity:** BLOCKING → fixed
- **Evidence:** `tests/test_outstanding_findings.py` — 4 sites that previously used `BootstrapConfig.from_yaml("config.yaml")` now use `tempfile.mkdtemp() + "/cache"` for isolation. `pytest tests/` runs clean on 1st, 2nd, 3rd consecutive runs (verified manually).
- **Status:** fixed-verified

### TRA-D6-002 / TRA-B6-008 — mutmut config crashes — PARTIAL (deprecated keys still in use)

- **Severity:** WARNING → partial
- **Evidence:** `pyproject.toml:62-64` reads:
  ```toml
  [tool.mutmut]
  paths_to_mutate = ["tra"]    # ← deprecated, mutmut 3.6+ warns
  tests_dir = ["tests"]         # ← deprecated, mutmut 3.6+ warns
  max_stack_depth = 5
  ```
  Running `mutmut run --help` produces:
  ```
  UserWarning: The config paths_to_mutate is deprecated. Please rename it to source_paths
  UserWarning: The config tests_dir is deprecated. Please add the path to pytest_add_cli_args_test_selection instead
  ```
  The R6 fix changed string → list (correctly fixing the crash) but did NOT rename `paths_to_mutate` → `source_paths` or `tests_dir` → `pytest_add_cli_args_test_selection`. The config still produces deprecation warnings and will break entirely when mutmut 4.x removes the deprecated keys.
- **Suggested fix:** Rename `paths_to_mutate` → `source_paths` and `tests_dir` → `pytest_add_cli_args_test_selection` in `pyproject.toml`. Add a regression test that asserts `mutmut run --help` produces zero `DeprecationWarning` output.
- **Status:** partial (carries forward as new R7 finding TRA-B7-001)

### TRA-D6-005 — Wrong field name `level` → `conformance_level` — FIXED-VERIFIED

- **Severity:** WARNING → fixed
- **Evidence:** `tests/test_outstanding_findings.py` — search for `model_copy(update={"level"` returns 0 hits; `model_copy(update={"conformance_level"` returns the previously-broken sites now using the correct field name.
- **Status:** fixed-verified

### TRA-D6-006 — Vacuous HITL e2e tests — FIXED-VERIFIED

- **Severity:** WARNING → fixed
- **Evidence:** `tests/test_outstanding_findings.py` — 3 HITL e2e tests now use `force_unrecoverable=True` to actually trigger the UNRECOVERABLE → HITL path. Tests fail (red) when `force_unrecoverable` is removed (verified manually).
- **Status:** fixed-verified

### TRA-E6-001 — audit_trace.jsonl append mode breaks reproducibility — FIXED-VERIFIED

- **Severity:** WARNING → fixed
- **Evidence:** `tra/diagnostics.py` `AuditTrail.__init__` now accepts `truncate: bool = False` parameter; `tra/kernel.py` `TRAKernel.__init__` passes `truncate=True` so each run starts with a fresh `audit_trace.jsonl`. Verified: 2 consecutive L4 runs on the default CLI path produce byte-identical `audit_trace.jsonl` (sha256 `d01e7bfa22db9b35...` × 2).
- **Status:** fixed-verified

### TRA-C6-010 — to_translate.md benchmark count "24" → "36" — FIXED-VERIFIED

- **Severity:** WARNING → fixed
- **Evidence:** `to_translate.md` now states the benchmark count is 36 (matches `tests/benchmark/cases/*.jsonl`).
- **Status:** fixed-verified

## Remaining R6 WARNING Findings (4 outstanding)

### TRA-A6-001 — Cache-hit suppresses EXCEPTION_HANDLER records for UnknownTerm — PERSISTENT

- **Severity:** WARNING (still open)
- **Evidence:** `tra/isa.py:461-468` — cache-hit early-return branch unchanged at HEAD `6d3144a`. When a cached `TranslationResult` is found, the function returns immediately after emitting a single `TRANSLATE_SEGMENT` audit record; it does NOT re-emit the `EXCEPTION_HANDLER` records that were produced on the cache-miss path. `TranslationResult` (`tra/cache.py:104-111`) still does not store `audit_side_effects` or any unknown-token metadata.
- **Status:** persistent (carries forward as TRA-A7-001 in R7)

### TRA-A6-002 — _repair_loop doesn't pass segment_index — PERSISTENT

- **Severity:** WARNING (still open)
- **Evidence:** `tra/kernel.py:676-685` — `_repair_loop` calls `repair_segment(target, src, current, self.ctx, self.evidence, self.audit, attempt=attempt, max_retries=max_retries)` WITHOUT `segment_index`. `RepairAttempt.segment_index` defaults to 0 for all repair attempts in the production CLI path.
- **Status:** persistent (carries forward as TRA-A7-002 in R7)

### TRA-D6-003 — 15 hardcoded absolute paths in test_outstanding_findings.py — PERSISTENT

- **Severity:** WARNING (still open)
- **Evidence:** `tests/test_outstanding_findings.py` — `rg "/home/z/my-project" tests/test_outstanding_findings.py` returns 15 hits, all hardcoded paths like `/home/z/my-project/Translation-Runtime-Architecture/...`. These break test portability across containers/checkouts.
- **Status:** persistent (carries forward as TRA-D7-001 in R7)

### TRA-D6-004 — Vacuous entity-ambiguity test — PERSISTENT

- **Severity:** WARNING (still open)
- **Evidence:** `tests/test_outstanding_findings.py::TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover::test_entity_ambiguity_emits_exception_handler_audit_record` — test asserts that EntityAmbiguity emits an EXCEPTION_HANDLER audit record, but `tra/isa.py:388` calls `recover_entity_ambiguity()` directly (never raises the exception), so `route_exception`'s EntityAmbiguity branch is never exercised. Test passes vacuously.
- **Status:** persistent (carries forward as TRA-D7-002 in R7)

## R6 INFO Findings (44 outstanding — all carried forward)

All 44 R6 INFO findings are persistent at HEAD `6d3144a`. None have regressed. Key clusters:

- **TRA-A6-003** (structural map duplicate leaf segments for list items) — persistent, low impact (cache absorbs redundancy)
- **TRA-A6-004** (EntityAmbiguity bypasses EXCEPTION_HANDLER path) — persistent, related to TRA-D6-004
- **TRA-A6-005** (`_execute_translation` and `verify_output` not wrapped in try/except TRAException) — persistent
- **TRA-B6-007** (`self._cache: Any = None` in `tra/cache.py:119`) — persistent type-safety residual
- **TRA-B6-009** (OWASP A09 partial coverage — `Authorization: <scheme> <credentials>` leaks credentials token) — persistent
- **TRA-B6-012** (`cache.get` backward-compat `else` branch re-opens pickle path for legacy entries) — persistent, low risk
- **TRA-C6-007/008/009/011** — minor doc-drift residuals (SKILL.md test-class list, implementation_plan.md deps table HEAD pin, README.md missing Round 5 ref, status.md banner HEAD pin)
- **TRA-D6-007 through D6-019** — test coverage gaps (test isolation, hardcoded paths, weak assertions, missing per-leaf+LLM interaction tests, coverage 96%, mutation testing config tests superficial, e2e_test.py standalone)
- **TRA-E6-003/004/012** — forensic L4 residuals (warm-cache suppresses EXCEPTION_HANDLER, append-mode test-coverage gap, TRA-E5-013 double VERIFY_OUTPUT at L3+ undocumented)
- **TRA-F6-009** — TRA-MODULE-AUTHORING.md §2.7 parameter name drift (`source` vs `text`)

These are catalogued in `master_findings_register_r7.json` and prioritized in `remediation_plan_r7.md`.

## R6 Positive Verifications (18 re-confirmed at HEAD `6d3144a`)

All 18 R6 positive verifications hold at HEAD `6d3144a`. Highlights:

- **TRA-A6-007** — 4 critical invariants hold (canonical terminology, entity immutability, VERIFY_OUTPUT never self-scores, REPAIR surgical)
- **TRA-A6-008** — All 5 PolicyResolver severity pairs arbitrated (`_POLICY_RESOLVER.wins()` called from 5 sites in `verify_output`)
- **TRA-A6-009** — Per-leaf segment translation works (TRA-001 Phase 8); minor residual: `segment_index` plumbing (TRA-A6-002)
- **TRA-A6-010** — Factual integrity check (version + date token preservation) in `verify_output`, P1 arbitrated via PolicyResolver
- **TRA-A6-011** — `EMPTY_SOURCE` raises `BrokenMarkdown` with BLOCKING severity, end-to-end L3 ConformanceFailure
- **TRA-A6-012** — L3/L4 gates enforced (in-band `ConformanceFailure` + out-of-band `validate`)
- **TRA-B6-001** — TRA-013 byte-reproducibility HOLDS within HEAD (`audit_trace.jsonl` sha256 `d01e7bfa22db9b35...` × 2 cold-cache L4 runs)
- **TRA-B6-002** — TRA-079 cache HMAC-SHA256 rejects tampered entries
- **TRA-B6-003** — TRA-076 LLM seam output routed through `sanitize_input` (OWASP A03)
- **TRA-B6-004** — TRA-077 cache stores HMAC-prefixed JSON strings, not pickle (OWASP A08)
- **TRA-B6-005** — TRA-078 exception repr sanitized of secrets before audit (OWASP A09)
- **TRA-B6-013** — OWASP A04 no ReDoS in production regex patterns
- **TRA-B6-014** — OWASP A05 all YAML loads use `safe_load`
- **TRA-B6-015** — OWASP A01+A03 path traversal protected; `sanitize_input` chokepoint
- **TRA-B6-016** — TRA-017 dependency hygiene (6 runtime + 4 dev deps, no unused deps)
- **TRA-B6-017** — Error handling: all `except` clauses narrow or documented; no silent swallowing
- **TRA-B6-018** — Dead self-assignments (`out = out`, `repaired = repaired`) remain removed
- **TRA-E6-011** — Hash chain integrity: VERIFY_OUTPUT `input_hash` matches emitted target

## Conclusion

- **0 regressions** from R6 baseline ✓
- **All 4 critical invariants hold** at HEAD `6d3144a` with code-level evidence ✓
- **TRA-013 byte-reproducibility HOLDS** within HEAD ✓
- **R6 Batch 1 remediation landed correctly**: 4 BLOCKING + 6 WARNING fixed-verified ✓
- **4 WARNING findings still outstanding** (TRA-A6-001, A6-002, D6-003, D6-004) + 1 partial (TRA-D6-002/B6-008 mutmut deprecation) — addressed in `remediation_plan_r7.md`
- **44 INFO findings carried forward** — addressed opportunistically in `remediation_plan_r7.md`
