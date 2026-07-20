# Track D7 — Test Suite Re-Audit (Round 7)

**Task ID:** D7-1
**Auditor:** Track D7 (test suite)
**HEAD audited:** `6d3144a` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Baseline:** Round 6 Track D6 (`docs/audit/round6/track_d6_findings.md`, 19 findings: 1 BLOCKING / 5 WARNING / 13 INFO + 1 positive verification)
**Methodology:** Re-run all quality gates at HEAD `6d3144a`. Audit test isolation, coverage, mutation testing, vacuous tests, hardcoded paths. R6 Track D6 claims verified, not trusted blindly.

## Verification Run

- HEAD: `git rev-parse HEAD` → `6d3144a3fdaa8d90a8f5b5f3996af39e667ee496` ✓
- `pytest tests/` → **309 passed in 1.68s** ✓ (cold cache)
- `pytest tests/` → **309 passed in 1.71s** ✓ (2nd consecutive run — R6 D6-001 cache-pollution fix verified)
- `pytest tests/` → **309 passed in 1.68s** ✓ (3rd consecutive run)
- mypy --strict: 0 issues in 20 source files ✓
- ruff: clean ✓
- mutmut config: `mutmut run --help` works (deprecation warnings present, see TRA-B7-001)

## Summary

- **Findings: 16 total (0 BLOCKING / 3 WARNING / 13 INFO + 3 positive verifications)**
- **0 regressions** from R6 baseline
- **All R6 Batch 1 test fixes verified landed:** cache-pollution (D6-001), mutmut config (D6-002), wrong field name (D6-005), vacuous HITL tests (D6-006)
- **3 WARNING findings still outstanding:** TRA-D7-001 hardcoded paths, TRA-D7-002 vacuous entity-ambiguity test, TRA-D7-003 per-leaf + LLM interaction untested

---

## Findings

### TRA-D7-001: 15 hardcoded absolute paths in test_outstanding_findings.py (PERSISTENT WARNING, carry-over from D6-003)

- **Severity:** WARNING
- **Category:** Test Suite / Portability
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-003; R6 Batch 1 did not address)
- **Evidence:**
  - `rg -n "/home/z/my-project" tests/test_outstanding_findings.py` → 15 hits.
  - Sample lines:
    - `:3653` — `cwd="/home/z/my-project/Translation-Runtime-Architecture/tra-prototype"`
    - `:3729` — `"/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/tra/kernel.py"`
    - `:4210` — `"/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/tra/isa.py"`
    - `:5007` — `"/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/pyproject.toml"`
  - These break test portability across containers/checkouts. Tests fail if the repo is cloned to a different path.
  - At HEAD `6d3144a`, tests pass because the repo IS at `/home/z/my-project/Translation-Runtime-Architecture/`. But this is fragile.
- **Detail:** The hardcoded paths are used in tests that verify file:line evidence (e.g., asserting a specific source file path appears in an audit record). The fix is to replace them with `Path(__file__).resolve().parent.parent` (the repo root) or a fixture that computes the path dynamically.
- **Suggested fix:** Replace all 15 hardcoded paths with `Path(__file__).resolve().parent.parent` (or a session-scoped fixture). Add a regression test that asserts no test file contains the literal string `/home/z/my-project/`.

### TRA-D7-002: Vacuous test `test_entity_ambiguity_emits_exception_handler_audit_record` (PERSISTENT WARNING, carry-over from D6-004)

- **Severity:** WARNING
- **Category:** Test Suite / Vacuous Assertion
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-004)
- **Evidence:**
  - `tests/test_outstanding_findings.py:4120-4158` — `test_entity_ambiguity_emits_exception_handler_audit_record`:
    - Test name claims to assert "entity_ambiguity_emits_exception_handler_audit_record".
    - Test body (line 4149): `# We don't strictly require ENTITY_AMBIGUITY on this particular input`. The actual assertion (line 4156) only checks `"direct_call" not in str(snapshot).lower()` — i.e., it asserts the ABSENCE of a marker that the production code never emits.
    - The test passes vacuously regardless of whether EntityAmbiguity is raised, recovered, or emitted as an EXCEPTION_HANDLER record.
  - `tra/isa.py:388` — `recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)` is called directly (never raises), so `route_exception`'s EntityAmbiguity branch is never exercised in production. See also TRA-A7-004.
- **Detail:** The test was intended to verify that EntityAmbiguity emits an EXCEPTION_HANDLER audit record (mirroring the UnknownTerm fix from R5 Batch 2). But the assertion was weakened to "we don't strictly require" — making the test vacuous. The underlying production gap (TRA-A7-004) means the test cannot be strengthened until the production code is fixed.
- **Suggested fix:** First fix TRA-A7-004 (raise EntityAmbiguity instead of direct-calling recover_entity_ambiguity). Then strengthen the test to assert: (a) an EXCEPTION_HANDLER record with `exception_code='ENTITY_AMBIGUITY'` exists in the audit trail, (b) the record's `artifact_snapshot.severity == 'WARNING'`, (c) the record's `artifact_snapshot.action == 'PRESERVE_SOURCE'`.

### TRA-D7-003: Per-leaf translation + LLM interaction untested (PERSISTENT INFO, carry-over from D6-011)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-011)
- **Evidence:**
  - `rg "iter_leaf_segments" tests/` → 3 hits, all in `test_outstanding_findings.py` testing the structural map directly. None test the kernel's `_execute_translation` per-leaf walk WITH an LLM callback supplied.
  - `tra/kernel.py:521-667` — `_execute_translation` has two paths: (a) per-leaf rule-path translation (no LLM), (b) whole-doc LLM translation. The interaction between these paths (e.g., what happens when LLM raises on leaf 3 of 10) is untested.
  - `tra/isa.py:467-543` — `translate_segment` LLM graceful-degradation path (degrades to rule path on LLM failure) is tested at the segment level but NOT at the kernel orchestration level.
- **Detail:** The per-leaf translation refactor (TRA-001 Phase 8, R5 Batch H) added new control flow that is only partially tested. An LLM that raises mid-translation could leave the kernel in an inconsistent state (some leaves translated by LLM, others by rule path) — this scenario is not covered.
- **Suggested fix:** Add a test that supplies an LLM callback which raises on the 3rd call and asserts: (a) the kernel completes (doesn't crash), (b) the audit trail records both LLM-decision and degraded records, (c) the final output is structurally valid.

### TRA-D7-004: Test isolation gaps in 4 TestTRA_A5_003 / TestTRA_E5_003 tests (PERSISTENT INFO, carry-over from D6-007)

- **Severity:** INFO
- **Category:** Test Suite / Test Isolation
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-007; R6 Batch 1 fixed 4 of the original sites, but 4 remain)
- **Evidence:**
  - `rg "BootstrapConfig.from_yaml..config\.yaml.." tests/test_outstanding_findings.py | wc -l` → still multiple hits that don't override `cache_directory`.
  - The R6 Batch 1 fix added `cache_directory: tempfile.mkdtemp() + "/cache"` to 4 sites, but other sites in the same file still use the default `./cache` from `config.yaml`.
- **Detail:** Test isolation is improved but not complete. Tests that share the default `./cache` can still pollute each other if run in sequence.
- **Suggested fix:** Audit all `BootstrapConfig.from_yaml("config.yaml")` calls in tests and ensure each one overrides `cache_directory` with a `tempfile.mkdtemp()`.

### TRA-D7-005: 3 tests in `test_isa.py` use shared `./cache` directory (PERSISTENT INFO, carry-over from D6-008)

- **Severity:** INFO
- **Category:** Test Suite / Test Isolation
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-008)
- **Evidence:**
  - `rg "TranslationCache\(..cache..\)" tests/test_isa.py` → 3 hits using a shared `./cache` directory.
  - These tests pass at HEAD `6d3144a` because pytest runs them in order, but they would fail intermittently if run in parallel or in a different order.
- **Suggested fix:** Replace `TranslationCache("./cache")` with `TranslationCache(tempfile.mkdtemp())` in all 3 sites.

### TRA-D7-006: `test_l4_forensic_trace_emitted_at_l4` doesn't override `cache_directory` (PERSISTENT INFO, carry-over from D6-009)

- **Severity:** INFO
- **Category:** Test Suite / Test Isolation
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-009)
- **Evidence:**
  - `tests/test_outstanding_findings.py::TestTRA_E5_016_L4ForensicTrace::test_l4_forensic_trace_emitted_at_l4` — uses `BootstrapConfig.from_yaml("config.yaml")` without `cache_directory` override.
- **Suggested fix:** Add `cache_directory: tempfile.mkdtemp() + "/cache"` to the `model_copy` call.

### TRA-D7-007: `TestTRA033LLMSeamRobustness` weak assertion (PERSISTENT INFO, carry-over from D6-010 / TRA-D5-003)

- **Severity:** INFO
- **Category:** Test Suite / Weak Assertion
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-010 / TRA-D5-003)
- **Evidence:**
  - `tests/test_outstanding_findings.py::TestTRA033LLMSeamRobustness` — asserts `degraded` is truthy but does NOT assert the specific number of `TRANSLATE_SEGMENT` records or the specific content of the degraded audit record.
- **Suggested fix:** Strengthen assertion to: (a) exactly one `TRANSLATE_SEGMENT` audit record with `artifact_snapshot.degraded == True`, (b) the `artifact_snapshot.reason` contains `llm_unavailable:`, (c) no other `TRANSLATE_SEGMENT` records exist.

### TRA-D7-008: Hardcoded `/tmp/test_tra071*.jsonl` paths (PERSISTENT INFO, carry-over from D6-012)

- **Severity:** INFO
- **Category:** Test Suite / Portability
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-012)
- **Evidence:**
  - `rg "/tmp/test_tra071" tests/` → multiple hits in `test_tra071_broken_markdown.py` using hardcoded `/tmp/test_tra071*.jsonl` paths.
  - These can collide if tests run in parallel on the same machine.
- **Suggested fix:** Replace with `tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl").name`.

### TRA-D7-009: Coverage 96% (58 missing lines, mostly fallback paths) (PERSISTENT INFO, carry-over from D6-013)

- **Severity:** INFO
- **Category:** Test Suite / Coverage
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-013)
- **Evidence:**
  - `pytest --cov=tra tests/` → 96% coverage, 58 missing lines.
  - Missing lines are mostly fallback/error paths that are difficult to trigger in tests (e.g., diskcache.Corrupt exception, YAML parse errors).
- **Suggested fix:** Add targeted tests for the missing paths where feasible. Some paths (e.g., diskcache internal errors) may be impractical to test.

### TRA-D7-010: Benchmark suite verified at 36 cases (TRA-D5-006 partial: target 100+) (POSITIVE VERIFICATION, partial)

- **Severity:** INFO
- **Category:** Test Suite / Benchmark Coverage
- **Finding type:** positive_verification (partial)
- **Round 6 status:** verified-holding (TRA-D6-014 re-confirmed)
- **Evidence:**
  - `tests/benchmark/cases/sft.jsonl` + `tests/benchmark/cases/regression.jsonl` → 36 cases total.
  - `pytest tests/test_benchmark.py` → all 36 cases pass, 0 BLOCKING, 0 WARNING.
  - Target: 100+ per `TRA-BENCHMARK-SUITE.md`. Current: 36/100 (36%).

### TRA-D7-011: Per-leaf translation tests verified holding (TRA-001 / TRA-A5-001) (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Test Suite / Per-Leaf Translation
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-D6-015 re-confirmed)
- **Evidence:**
  - `tests/test_outstanding_findings.py::TestTRA_001_LeafSegmentTranslation` — tests pass at HEAD `6d3144a`.
  - Per-leaf translation works for HEADING, PARAGRAPH, LIST_ITEM, TABLE_CELL leaf kinds.

### TRA-D7-012: LLM seam DI tests verified holding (TRA-D5-002) (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Test Suite / LLM Seam DI
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-D6-016 re-confirmed)
- **Evidence:**
  - `tests/test_outstanding_findings.py::TestTRA_D5_002_LLMSeamDI` — tests pass.
  - `TRAKernel.run(source, llm_translate=callback)` works as documented.

### TRA-D7-013: Cache HMAC tests verified holding (TRA-B5-004 / TRA-079) (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Test Suite / Cache HMAC
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-D6-017 re-confirmed)
- **Evidence:**
  - `tests/test_outstanding_findings.py::TestTRA_B5_004_CacheHmacTamperedEntryRejected` — tests pass.
  - HMAC-SHA256 verification on every cache read.

### TRA-D7-014: Mutation testing config tests present but superficial (PERSISTENT INFO, carry-over from D6-018 / TRA-D5-011)

- **Severity:** INFO
- **Category:** Test Suite / Mutation Testing
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-018)
- **Evidence:**
  - `tests/test_outstanding_findings.py::TestTRA_D5_011_MutationTestingConfig` — only checks that `[tool.mutmut]` section exists in `pyproject.toml`. Does NOT verify the keys are non-deprecated (see TRA-B7-001) or that `mutmut run` actually executes without crashing.
- **Suggested fix:** Strengthen the test to run `mutmut run --help` and assert zero `DeprecationWarning` output (once TRA-B7-001 is fixed).

### TRA-D7-015: `e2e_test.py` is a standalone script, not a pytest test (PERSISTENT INFO, carry-over from D6-019 / TRA-D5-009)

- **Severity:** INFO
- **Category:** Test Suite / E2E Test Coverage
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from D6-019)
- **Evidence:**
  - `tra-prototype/e2e_test.py` — standalone script (`python e2e_test.py`), not collected by pytest.
  - `tests/test_e2e_to_translate.py` — 12 pytest tests cover the same ground, so the standalone script is redundant but not harmful.
- **Suggested fix:** Either delete `e2e_test.py` (the pytest suite covers it) or convert it to a pytest test. Low priority.

### TRA-D7-016: Test count 309/16 verified (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Test Suite / Test Count
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-D6-020 re-confirmed)
- **Evidence:**
  - `pytest tests/ --co -q | wc -l` → 309 tests collected.
  - `find tests -name 'test_*.py' | wc -l` → 16 test files.
  - Matches `CLAUDE.md`, `AGENTS.md`, `tra-prototype/SKILL.md` claims.

---

## Conclusion

- **0 BLOCKING** findings at HEAD `6d3144a` ✓ (R6 D6-001 BLOCKING cache-pollution fixed)
- **2 WARNING** findings persistent (TRA-D7-001 hardcoded paths, TRA-D7-002 vacuous entity-ambiguity test) — addressed in `remediation_plan_r7.md`
- **1 INFO** finding escalated to WARNING priority (TRA-D7-003 per-leaf + LLM interaction untested) — addressed in `remediation_plan_r7.md`
- **12 INFO** findings persistent (TRA-D7-004 through D7-015) — addressed opportunistically
- **3 positive verifications** re-confirmed
- **0 regressions** from R6 baseline ✓
- **All R6 Batch 1 test fixes verified landed** ✓
