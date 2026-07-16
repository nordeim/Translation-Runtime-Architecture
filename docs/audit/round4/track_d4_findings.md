# Track D4 — Test Suite Re-Audit (Round 4)

**HEAD audited:** `805a8f8`
**Methodology:** Test inventory + coverage gap analysis + benchmark completeness + lightweight mutation testing. Findings re-derived from source at HEAD.
**Baseline:** Round 3 Track D3 (11 findings) + 36-finding R3 master register + R4 regression baseline.
**Audit date:** 2026-07-17

## Summary

- Findings: **15 total (0 BLOCKING / 5 WARNING / 10 INFO)**
- Carry-over from Round 3: **11** (TRA-D4-001..011)
- Cross-listed from Track A4/B4: **2** (TRA-D4-012 = TRA-A4-011; TRA-D4-013 = TRA-B4-009)
- New findings: **2** (TRA-D4-014, TRA-D4-015)
- Test count at HEAD: **199** (R3: 174, delta: **+25** — all 25 new tests landed in `test_outstanding_findings.py`, which grew 39 → 64 tests)
- Test files at HEAD: **16** (R3: 16, delta: **+0**) — no new test files added since R3

All four quality gates remain green at HEAD `805a8f8`:
`ruff format --check` ✓ · `ruff check` ✓ · `mypy --strict tra` ✓ · `pytest` (199 passed) ✓

## Findings

### TRA-D4-001: e2e LLM callback ignores `source_segment` (carry-over)

- **Severity:** INFO
- **Category:** Test Coverage
- **Evidence:** `tests/test_e2e_to_translate.py:83-86`; `tests/run_e2e_translation.py:65-68`
- **Detail:** The manual LLM callback `manual_llm(source_segment, ctx)` discards `source_segment` and returns the entire `manual_translation` for every call. This works because the kernel currently translates one segment (the whole document) per `run()`, but it means the e2e test cannot detect per-segment routing bugs (e.g. if the kernel called `llm_translate` twice with different segments and concatenated the results, the test would still pass). The same anti-pattern is duplicated in the new `tests/run_e2e_translation.py:65-68` (added in commit `805a8f8`).
- **Suggested fix:** Either (a) document the single-segment assumption explicitly in the test docstring, or (b) when the kernel supports multi-segment translation, segment-correlate source↔target in the callback.
- **Round 3 status:** persistent (was D3-001)

### TRA-D4-002: e2e LLM hijack uses module-level patching (carry-over = TRA-090)

- **Severity:** WARNING
- **Category:** Test Coverage / Test Hygiene
- **Evidence:** `tests/test_e2e_to_translate.py:90-104`; `tests/run_e2e_translation.py:70-89`; `tra/kernel.py:211` (`def run(self, source: str | Path) -> str:`)
- **Detail:** `TRAKernel.run()` signature at `kernel.py:211` STILL lacks an `llm_translate` parameter — exactly as flagged in R3 (TRA-090 / D3-002). To inject an LLM, both `tests/test_e2e_to_translate.py:90-104` AND the new `tests/run_e2e_translation.py:70-89` mutate `kernel_mod.translate_segment` at module scope, then restore it in a `finally` block. This is fragile: a parallel test run could see the patched function, and the restoration relies on `finally` running cleanly. R3's Batch 4 remediation plan §4.3 said "Add `llm_translate` parameter to `TRAKernel.run()`" — this was NOT implemented; instead a second manual script using the same anti-pattern was added.
- **Suggested fix:** Add an `llm_translate: Callable | None = None` parameter to `TRAKernel.run()` (or `__init__`), defaulting to `None`. Update `_execute_translation` to pass it through. Eliminates module-level patching in all 12 e2e tests + the new script.
- **Round 3 status:** persistent (was D3-002 / TRA-090)

### TRA-D4-003: TRA-048 single-audit-record invariant only PARTIALLY tested (partial fix)

- **Severity:** WARNING
- **Category:** Mutation Testing / Test Coverage
- **Evidence:** `tests/test_outstanding_findings.py:2075-2168` (TestTRA088, 2 tests); `tests/test_outstanding_findings.py:410-507` (TestTRA033, 7 tests with weak assertions); `tests/test_phase6_hardening.py:71-99` (RuntimeError test); `tra/isa.py:411-455` (single-audit-record degradation path)
- **Detail:** R3's D3-004 flagged that the single-`TRANSLATE_SEGMENT`-audit-record invariant (TRA-048) was only asserted for the `RuntimeError` exception path. The R4 fix (TRA-088) added 2 new tests (`test_empty_response_single_audit_record`, `test_type_error_single_audit_record`) — closing the gap for the empty-string (internally `ValueError`) and `TypeError` paths. However, 4 of 7 LLM-seam degradation paths STILL do not assert the invariant:
  - `ValueError` raised directly — NOT asserted (only the empty-string→ValueError path is)
  - `OSError` raised — NOT asserted (TestTRA033 only checks `"Confirmed" in res.translation`)
  - `TimeoutError` raised — NOT asserted
  - `None` returned — NOT asserted (transitively triggers TypeError via `sanitize_input(None)`, but this is an implementation-detail coupling that would break if `sanitize_input` learned to handle `None`)
  
  If a future mutation makes the early `return result` conditional on `isinstance(exc, RuntimeError | ValueError | TypeError)`, the `OSError`/`TimeoutError`/`None` paths would emit a second (non-degraded) audit record — and **no test would catch this**.
- **Suggested fix:** Add `assert len(translate_records) == 1` to each of the 7 tests in `TestTRA033LLMSeamRobustness`. The TestTRA088 class can stay as a focused supplementary test, but the parametrized TestTRA033 should also assert the invariant per-path.
- **Round 3 status:** partial (was D3-004 / TRA-088)

### TRA-D4-004: `review_decision` text-assertion gap (carry-over)

- **Severity:** INFO
- **Category:** Test Coverage
- **Evidence:** `tests/test_outstanding_findings.py:371-402` (TestTRA032HITLResolutions); `tests/test_phase6_hardening.py:157-167` (test_hitl_review_decision_accept); `tra/hitl.py:34-36` (contract: "text is the adopted target text")
- **Detail:** `TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution` is parametrized over `["accept", "override", "skip"]` but only asserts `result_res == resolution` (line 402) — NOT the returned `text`. The phase6 duplicate `test_hitl_review_decision_accept` asserts `text == "candidate"` but only for the `accept` path. Together: accept text asserted (phase6 only), override/skip text NOT asserted. Per `tra/hitl.py:34-36`, the contract is: "text is the adopted target text (unchanged candidate for accept/skip; reviewer-supplied for override)". The override (`text == "edited text"`) and skip (`text == candidate`) text contracts are untested.
- **Suggested fix:** Extend the parametrized test to assert `result_text == expected_text` where `expected_text = {"accept": candidate, "override": "edited text", "skip": candidate}[resolution]`.
- **Round 3 status:** persistent (was D3-005)

### TRA-D4-005: `on_override` callback in `review_decision` untested (carry-over)

- **Severity:** INFO
- **Category:** Test Coverage
- **Evidence:** `tra/hitl.py:30,56-57`; `tests/test_outstanding_findings.py:371-402`; `tests/test_phase6_hardening.py:157-167`; coverage report shows `tra/hitl.py:57` MISSED
- **Detail:** `review_decision` accepts an optional `on_override: Callable[[str, str], str] | None = None` parameter. When provided and the user chooses "override", the callback is invoked as `on_override(source_context, edited)` and its return value is used as the override text (`tra/hitl.py:57`). Coverage report at HEAD confirms `tra/hitl.py:57` is MISSED — no test passes `on_override`. Both TestTRA032 and `test_hitl_review_decision_accept` call `review_decision` without the `on_override` argument.
- **Suggested fix:** Add a test that passes a stub `on_override` and asserts it is invoked with `(source_context, edited_text)` and its return value is used as the override text.
- **Round 3 status:** persistent (was D3-006)

### TRA-D4-006: Benchmark suite at 22/100+ spec target (carry-over = TRA-031/092)

- **Severity:** INFO
- **Category:** Benchmark
- **Evidence:** `tests/benchmark/cases/sft.jsonl` (21 cases); `tests/benchmark/cases/regression.jsonl` (1 case); `tra-prototype/TRA-BENCHMARK-SUITE.md` (target: 100+)
- **Detail:** 22 benchmark cases implemented at HEAD (unchanged from R3). Spec target per `TRA-BENCHMARK-SUITE.md` is 100+. 2 of 23 spec cases missing (S-03 inline-code-vs-prose, E-03 broken-source-markdown). Acknowledged in CLAUDE.md "Known gaps" section. Not a regression — same count as R3.
- **Suggested fix:** Grow the suite toward 100+ cases. Add S-03 (inline code vs prose differentiation) and E-03 (broken source markdown recovery) first — these are spec-mandated cases that are currently `# not implemented` stubs in `tra/benchmark.py:93,96,109-113`.
- **Round 3 status:** persistent (was TRA-031 / TRA-092)

### TRA-D4-007: `interactive=True` kernel path untested end-to-end (carry-over = TRA-052/091)

- **Severity:** WARNING
- **Category:** Test Coverage
- **Evidence:** `tra/kernel.py:505-521` (interactive branch); coverage report shows `tra/kernel.py:507-519` MISSED; `rg "interactive=True" tests/` → **no matches**
- **Detail:** The `if self.interactive:` block at `kernel.py:505-521` (HITL handoff with `format_unrecoverable` + `review_decision`) is **never executed** by any test. Coverage report at HEAD confirms lines 507-519 are MISSED. Zero grep matches for `interactive=True` across `tests/` confirms no test runs `TRAKernel(interactive=True).run()` end-to-end. The L3 conformance failure path raises before the UNRECOVERABLE handler is reached, so even the e2e ConformanceFailure tests (TestTRA089) don't trigger this branch.
- **Suggested fix:** Add a test that constructs `TRAKernel(cfg, interactive=True)`, monkeypatches `tra.hitl.review_decision` to return `("accept", candidate)`, feeds input that triggers an UNRECOVERABLE (e.g. an LLM that returns text introducing a new BLOCKING violation), and asserts the audit trail contains `HITL[accept]: ...` in `unresolved_ambiguities`.
- **Round 3 status:** persistent (was TRA-052 / TRA-091)

### TRA-D4-008: `kernel_config` fixture unused (carry-over)

- **Severity:** INFO
- **Category:** Test Hygiene
- **Evidence:** `tests/conftest.py:82-99` (fixture definition); `tests/test_kernel.py:12-23` (`_kernel()` helper duplicating the boilerplate); `rg "kernel_config" tests/` → only 1 hit in `test_kernel.py:13` (comment)
- **Detail:** `kernel_config(tmp_path) -> BootstrapConfig` is defined in `conftest.py:82-99` with a docstring claiming it "Eliminates the duplicated config-loading + path-override boilerplate that was copy-pasted across test_kernel.py, test_phase6_hardening.py, test_benchmark.py, and test_outstanding_findings.py". Grep across `tests/` for `kernel_config` as a fixture parameter returns ZERO matches. `test_kernel.py:13` has a comment "Uses the shared kernel_config fixture pattern (TRA-034)" but then defines its own `_kernel(tmp_path)` helper (lines 12-23) that duplicates the exact boilerplate the fixture was meant to eliminate. The Round 2 fix for TRA-034 (add the fixture) was merged but the fixture was never wired into tests.
- **Suggested fix:** Either (a) replace `_kernel()` in `test_kernel.py` with the `kernel_config` fixture, or (b) delete the unused fixture and the misleading comment.
- **Round 3 status:** persistent (was TRA-055)

### TRA-D4-009: `e2e_test.py` manual script persists (carry-over)

- **Severity:** INFO
- **Category:** Test Hygiene
- **Evidence:** `tra-prototype/e2e_test.py` (103 LOC, 0 `assert` statements, 0 `def test_*`); `tests/test_e2e_to_translate.py` (12 proper pytest tests that supersede it); `rg "assert|def test_" e2e_test.py` → **no matches**
- **Detail:** The manual script `e2e_test.py` (103 LOC) is still present at the tra-prototype root and is NOT pytest-collectible (no `test_*` functions, no `assert` statements — just `print()` output). Commit `354fa94` added `tests/test_e2e_to_translate.py` (12 proper pytest tests) that fully supersede the manual script's coverage. The manual script is now dead code.
- **Suggested fix:** Delete `e2e_test.py`. Update CLAUDE.md / SKILL.md if either references it.
- **Round 3 status:** persistent (was TRA-056)

### TRA-D4-010: Cross-file duplicate HITL test (carry-over)

- **Severity:** INFO
- **Category:** Test Hygiene
- **Evidence:** `tests/test_phase6_hardening.py:157-167` (`test_hitl_review_decision_accept`); `tests/test_outstanding_findings.py:371-402` (TestTRA032HITLResolutions parametrized over accept/override/skip)
- **Detail:** `test_phase6_hardening.py::test_hitl_review_decision_accept` (lines 157-167) duplicates `TestTRA032HITLResolutions["accept"]` (parametrized). Both test the same `review_decision("amb", "src", "candidate")` → `"accept"` path with the same monkeypatch strategy (`monkeypatch.setattr("tra.hitl.Prompt.ask", ...)`). The phase6 version additionally asserts `text == "candidate"`; the parametrized version does not.
- **Suggested fix:** Delete `test_hitl_review_decision_accept` from `test_phase6_hardening.py` after extending the parametrized `TestTRA032HITLResolutions` test to assert the text (TRA-D4-004 fix). Consolidates HITL coverage in one place.
- **Round 3 status:** persistent (was TRA-057)

### TRA-D4-011: Mutation testing framework deferred (carry-over = TRA-094)

- **Severity:** INFO
- **Category:** Mutation Testing
- **Evidence:** `pyproject.toml` (no `mutmut` / `cosmic-ray` / `hypofuzz` / `pytest-mutation` deps); `rg "mutmut|cosmic-ray|hypofuzz" tra-prototype/` → no matches
- **Detail:** R3's TRA-094 deferred mutation testing as a future investment. No mutation testing framework has been added. The R3 D3 audit performed 6 ad-hoc mutations manually (6/6 caught); the R4 B4 audit performed 4 more (TRA-073/076/077/078 — all caught). Without an automated mutation runner, future regressions in test enforcement quality will go undetected.
- **Suggested fix:** Add `mutmut` or `cosmic-ray` to dev deps. Configure to run on `tra/` (skip tests). Wire into CI as a weekly job.
- **Round 3 status:** persistent (was TRA-094)

### TRA-D4-012: `repaired = repaired` no-op has no test that would catch it (cross-listed from TRA-A4-011)

- **Severity:** WARNING
- **Category:** Test Coverage / Mutation Testing
- **Evidence:** `tra/isa.py:654` (`repaired = repaired  # cannot conjure absent entity without source`); `tests/test_outstanding_findings.py:1828-1853` (TestTRA073 only greps for literal `out = out`, NOT `repaired = repaired`)
- **Detail:** Track A4 discovered (TRA-A4-011) that `repair_segment`'s entity branch at `tra/isa.py:654` contains `repaired = repaired` — a no-op self-assignment mirroring the TRA-073 pattern that was fixed in commit `632bed2`. The TRA-073 regression test (`TestTRA073DeadCodeRemoved::test_no_dead_out_assign_in_rule_translate`) reads `isa.py` source and greps for the literal pattern `code_part == "out = out"` — it would NOT catch `repaired = repaired` because the variable name is different. Removing the line would not change behavior (it's a no-op), so no behavioral test would catch it either. The TRA-073 fix's enforcement scope is too narrow.
- **Suggested fix:** Either (a) extend `TestTRA073DeadCodeRemoved` to grep for ANY `(\w+) = \1$` self-assignment pattern across `isa.py` (more general — catches `out = out`, `repaired = repaired`, and any future no-op), or (b) add a new `TestTRA_A4_011RepairedNoOpRemoved` class that mirrors the TRA-073 pattern but greps for `repaired = repaired`.
- **Round 3 status:** new (cross-listed from Track A4 finding TRA-A4-011; the no-op pre-existed since initial commit `84753ad` but was missed by R3's narrow TRA-073 scan)

### TRA-D4-013: TRA-016/017/026 silently remediated with no regression tests (cross-listed from TRA-B4-009)

- **Severity:** WARNING
- **Category:** Test Coverage / Mutation Testing
- **Evidence:** `rg "TestTRA016|TestTRA017|TestTRA026|TRA-016|TRA-017|TRA-026" tests/` → **no matches**; `rg "count_blocking" tra/diagnostics.py` → no match (TRA-016 FIXED); `pyproject.toml:10-17` shows 6 runtime deps (TRA-017 FIXED); `rg "expire" tra/config.py config.yaml` → no match (TRA-026 FIXED)
- **Detail:** Track B4 discovered (TRA-B4-009) that TRA-016 (`count_blocking` stub removed from `diagnostics.py`), TRA-017 (6 unused deps trimmed from `pyproject.toml`), and TRA-026 (`cache.expire` config field removed) were silently remediated without adding any regression test that would catch a revert. If any of the 3 fixes were reverted:
  - TRA-016 revert (re-add `count_blocking` stub) → pytest exit code 5 (no tests collected for `count_blocking`)
  - TRA-017 revert (re-add 6 unused deps) → pytest exit code 0 (no test inspects `pyproject.toml` deps)
  - TRA-026 revert (re-add `expire` config field) → pytest exit code 0 (no test inspects `config.py` for `expire` field absence)
  
  By contrast, reverting TRA-073/076/077/078 all cause specific regression test failures (verified by Track B4 mutation testing). The 3 silently-remediated findings lack enforcement-protective tests.
- **Suggested fix:** Add 3 lightweight regression tests:
  - `TestTRA016CountBlockingRemoved::test_no_count_blocking_in_diagnostics` — static grep like TRA-073.
  - `TestTRA017UnusedDepsRemoved::test_pyproject_has_only_6_runtime_deps` — `tomllib.load` + assert exact dep set.
  - `TestTRA026CacheExpireRemoved::test_no_expire_in_config` — static grep.
- **Round 3 status:** new (cross-listed from Track B4 finding TRA-B4-009; the silent remediation happened in commits `df9a590` and `a3cd2c1`)

### TRA-D4-014: NEW redundant manual e2e script added in commit `805a8f8`

- **Severity:** INFO
- **Category:** Test Hygiene
- **Evidence:** `tests/run_e2e_translation.py:1-186` (NEW, 186 LOC, 0 `assert` statements, 0 `def test_*`); `tests/test_e2e_to_translate.py:1-394` (12 proper pytest tests covering same pipeline); `git log --oneline tests/run_e2e_translation.py` → only `805a8f8`
- **Detail:** Commit `805a8f8` ("feat(tra): E2E translation output + TDD remediation of 5 more Round 3 findings") added a NEW manual script `tests/run_e2e_translation.py` (186 LOC) that:
  1. Has NO `assert` statements and NO `def test_*` functions (not pytest-collectible)
  2. Duplicates the functionality of `tests/test_e2e_to_translate.py` (12 proper pytest tests)
  3. Uses the same fragile module-level patching pattern at `tests/run_e2e_translation.py:78` (`kernel_mod.translate_segment = patched_translate`) — exactly the anti-pattern TRA-090 was supposed to eliminate
  4. Was added in the SAME commit that landed the TRA-088/089/090/091/092 fixes — but TRA-090 (which was supposed to ELIMINATE module-level patching) was NOT actually fixed; instead, a new manual script was added that uses the same anti-pattern
  
  This is a regression in test-suite hygiene: R3 had 1 redundant manual script (`e2e_test.py`), R4 has 2 (`e2e_test.py` + `tests/run_e2e_translation.py`). Combined dead code: 289 LOC.
- **Suggested fix:** Delete `tests/run_e2e_translation.py`. If a CLI-runnable E2E demo is desired, add a `python -m tra.e2e_demo` entry point that imports and calls the pytest-collectible `_run_kernel_with_manual_llm` helper from `tests/test_e2e_to_translate.py`, rather than duplicating its logic.
- **Round 3 status:** new (introduced by commit `805a8f8` between R3 baseline `b783745` and HEAD)

### TRA-D4-015: Structural repair branch is dead code with no test coverage

- **Severity:** INFO
- **Category:** Test Coverage / Dead Code
- **Evidence:** `tra/isa.py:663-668` (structural repair branch); coverage report shows `tra/isa.py:663-666` MISSED; `tra/isa.py:530-538` (only structural diagnostic emitted is `Severity.BLOCKING` heading-count mismatch); `rg "subsystem=.structural." tests/` → only `test_phase6_hardening.py:176` (used in `format_unrecoverable`, NOT in `repair_segment`)
- **Detail:** The `elif diagnostic.subsystem == "structural":` branch in `repair_segment` at `tra/isa.py:663-668` is **dead code in production** — `verify_output` only emits structural diagnostics with `Severity.BLOCKING` (heading-count mismatch, `tra/isa.py:534`), which cause `ConformanceFailure` to be raised immediately and never enter the repair loop. Coverage report confirms lines 663-666 are MISSED across the entire 199-test suite. No test exercises this branch.
  
  If the `if attempt >= max_retries: raise Unrecoverable(...)` lines at isa.py:665-668 were reverted (e.g. removed entirely), no test would fail. The branch is also unreachable from any production code path, so it's purely defensive.
- **Suggested fix:** Either (a) add a unit test that calls `repair_segment` directly with a WARNING-level `subsystem="structural"` diagnostic and asserts `Unrecoverable` is raised when `attempt >= max_retries`, or (b) delete the dead branch (and document that structural repairs always raise `ConformanceFailure` upstream).
- **Round 3 status:** new (the dead branch pre-existed since initial commit `84753ad`, but R3's coverage report at `b783745` showed the same missed lines `663-666`; R4 re-verified at HEAD `805a8f8`)

## Round 3 carry-over status matrix (Track D scope)

| Round 3 ID | Title | Round 4 status |
|---|---|---|
| D3-001 | e2e LLM callback ignores `source_segment` | **persistent** (TRA-D4-001) |
| D3-002 / TRA-090 | e2e LLM hijack uses module-level patching | **persistent** (TRA-D4-002) — `run()` signature unchanged at `kernel.py:211` |
| D3-003 / TRA-089 | No e2e test for ConformanceFailure path | **fixed** (TestTRA089ConformanceFailureE2E, 2 tests, both BROKEN_MARKDOWN + BROKEN_LINK paths exercised) |
| D3-004 / TRA-088 | TRA-048 single-audit-record invariant only for RuntimeError | **partial** (TRA-D4-003) — 3 of 7 paths now covered (empty/TypeError/RuntimeError); 4 still uncovered (ValueError-raised/OSError/TimeoutError/None) |
| D3-005 | `review_decision` text-assertion gap | **persistent** (TRA-D4-004) |
| D3-006 | `on_override` callback in `review_decision` untested | **persistent** (TRA-D4-005) |
| TRA-031 / TRA-092 | Benchmark suite at 22/100+ | **persistent** (TRA-D4-006) — same 22 cases, S-03 and E-03 still missing |
| TRA-052 / TRA-091 | `interactive=True` kernel path untested | **persistent** (TRA-D4-007) — coverage report confirms `kernel.py:507-519` MISSED |
| TRA-055 | `kernel_config` fixture unused | **persistent** (TRA-D4-008) |
| TRA-056 | `e2e_test.py` manual script persists | **persistent** (TRA-D4-009) — and a SECOND manual script was added (TRA-D4-014) |
| TRA-057 | Cross-file duplicate HITL test | **persistent** (TRA-D4-010) |
| TRA-094 | Mutation testing framework | **persistent** (TRA-D4-011) — no `mutmut`/`cosmic-ray` added |

**Net carry-over disposition:** 1 fixed (TRA-089), 1 partial (TRA-088), 10 persistent.

## Test inventory at HEAD `805a8f8`

| Test file | Test count | Notes |
|---|---|---|
| tests/test_anchor.py | 7 | unchanged from R3 |
| tests/test_benchmark.py | 25 | unchanged from R3 (22 parametrized cases + L3 gate + reproducibility) |
| tests/test_e2e_to_translate.py | 12 | unchanged from R3 |
| tests/test_isa.py | 17 | unchanged from R3 |
| tests/test_kernel.py | 7 | unchanged from R3 |
| tests/test_modules.py | 17 | unchanged from R3 |
| tests/test_outstanding_findings.py | **64** | **+25 vs R3** (was 39; added TestTRA088, TestTRA089 + 9 other new classes for round-3 fixes) |
| tests/test_phase0.py | 11 | unchanged from R3 |
| tests/test_phase6_hardening.py | 7 | unchanged from R3 |
| tests/test_recovery.py | 9 | unchanged from R3 |
| tests/test_reporting.py | 5 | unchanged from R3 |
| tests/test_tra043_protocol.py | 3 | unchanged from R3 |
| tests/test_tra047_config_robustness.py | 2 | unchanged from R3 |
| tests/test_tra071_broken_markdown.py | 2 | unchanged from R3 |
| tests/test_utils.py | 7 | unchanged from R3 |
| tests/test_validate.py | 4 | unchanged from R3 |
| tests/conftest.py | (fixtures) | 7 fixtures; 1 still unused (TRA-055 / TRA-D4-008) |
| tests/run_e2e_translation.py | (not collectible) | NEW in commit `805a8f8`; 186 LOC manual script, 0 asserts — TRA-D4-014 |
| **Total** | **199** | **+25 vs R3** (R3: 174) |

**Test class inventory in `tests/test_outstanding_findings.py`:** 34 classes (was 22 in R3, +12 classes added during R3 remediation). All 34 class names match their docstring TRA references (no mismatches). New classes added since R3:
- `TestTRA088SingleAuditRecordAllExceptions` (2 tests, partial fix for D3-004)
- `TestTRA089ConformanceFailureE2E` (2 tests, full fix for D3-003)
- `TestTRA073DeadCodeRemoved` (1 test, source-grep enforcement)
- `TestTRA074ClockSeedDefault` (1 test)
- `TestTRA075PairwiseTransitions` (3 tests)
- `TestTRA076LLMOutputSanitized` (1 test, OWASP A03)
- `TestTRA077CacheJsonNotPickle` (2 tests, OWASP A08)
- `TestTRA078SecretRedaction` (1 test, OWASP A09)
- `TestTRA093BrokenLinkFalsePositive` (2 tests, BLOCKING fix)
- `TestTRA096AsInterfaceProtocol` (3 tests, BLOCKING fix)
- `TestTRA097RegisterProtocolCheck` (2 tests)
- `TestTRA098RegistryDuplicateDetection` (3 tests)

## Benchmark case inventory

| Category | Spec target | At HEAD | Missing |
|---|---|---|---|
| S (Structural) | 6 (S-01..S-06) | 5 (S-01, S-02, S-04, S-05, S-06) | **S-03** (inline code vs prose) |
| F (Factual) | 5 (F-01..F-05) | 5 | — |
| T (Terminology) | 5 (T-01..T-05) | 5 | — |
| D (Domain) | 4 (D-01..D-04) | 4 | — |
| E (Ambiguity) | 3 (E-01..E-03) | 2 (E-01, E-02) | **E-03** (broken source markdown) |
| R (Regression, non-spec) | open | 1 (R-01) | — |
| **Total** | **100+** | **22** | **2 spec cases + ~78 scope gap** |

**Trajectory:** R2 = 22 cases, R3 = 22 cases, R4 = 22 cases. The benchmark suite has not grown across 3 audit rounds. Spec target is 100+ — current coverage is 22% of target.

**S-03/E-03 stubs:** `tra/benchmark.py:93,96,109-113` shows the runner IS prepared for S-03/E-03 (the `BenchmarkCase` model accepts any category), but the cases themselves are absent from `tests/benchmark/cases/sft.jsonl`. Adding them is data-only (no code change).

## Lightweight mutation testing analysis (top 5 R4 fixes)

For each "fixed" finding, the question: "if I reverted this fix, would a test fail?" Verification by reading the test that should catch a regression (no source mutations performed — audit-only per workflow rules).

| # | Finding | Fix location | Regression test | Mutation would be caught? |
|---|---|---|---|---|
| 1 | TRA-088 (LLM-seam single-audit-record) | `tra/isa.py:411-455` (early `return result` in except block) | `TestTRA088SingleAuditRecordAllExceptions` (2 tests) + `test_phase6_hardening.py:71-99` (RuntimeError) | **PARTIAL** — caught for empty-string/TypeError/RuntimeError paths; NOT caught for ValueError-raised/OSError/TimeoutError/None paths (TRA-D4-003) |
| 2 | TRA-089 (ConformanceFailure e2e) | `tra/kernel.py:299-333` (L3 gate raise branch) | `TestTRA089ConformanceFailureE2E` (2 tests, both BROKEN_MARKDOWN + BROKEN_LINK paths) | **YES** — both tests use `pytest.raises(ConformanceFailure, match=...)`; revert would cause both to fail |
| 3 | TRA-093 (BROKEN_LINK false positive) | `tra/anchor.py:is_translated_slug()` method + `rewrite_links._sub` check | `TestTRA093BrokenLinkFalsePositive` (2 tests: e2e + unit) | **YES** — e2e test asserts no ConformanceFailure raised; unit test asserts `not broken` |
| 4 | TRA-096 (as_interface protocol) | `tra/modules/registry.py:ModuleInterface` (4 added Callable fields) | `TestTRA096AsInterfaceProtocol` (3 tests: protocol check + default registry + stub FR→EN) | **YES** — `isinstance(iface, LanguageModuleProtocol)` assertion fails if any field is removed |
| 5 | TRA-077 (cache JSON not pickle) | `tra/cache.py:113,128` (`model_dump_json` + `json.loads`) | `TestTRA077CacheJsonNotPickle` (2 tests: JSON-not-pickle + round-trip) | **YES** — raw blob startswith `{` assertion fails if pickle is restored |

**Summary:** 4 of 5 top fixes are enforcement-protected (mutation would be caught). 1 (TRA-088) is PARTIAL — the gap is documented as TRA-D4-003.

Additionally, Track B4 already mutation-tested TRA-073/076/077/078 (all caught) — those results are incorporated by reference. Track B4 also confirmed TRA-016/017/026 are NOT enforcement-protected (no test catches a revert) — cross-listed as TRA-D4-013.

## Coverage report at HEAD `805a8f8`

`pytest --cov=tra --cov-report=term-missing --cov-branch tests` → **93% overall** (1477 statements, 58 missed, 400 branches, 65 partial).

| Module | Stmts | Miss | Branch | BrPart | Cover | Notable missing lines |
|---|---|---|---|---|---|---|
| tra/__init__.py | 1 | 0 | 0 | 0 | 100% | — |
| tra/anchor.py | 249 | 20 | 100 | 20 | 86% | 210, 228-229, 265, 286-293, 316, 319-322, 345, 348-351, 368 |
| tra/benchmark.py | 70 | 6 | 16 | 5 | 87% | 93, 96, 109-113 (S-03/E-03 unimplemented) |
| tra/cache.py | 68 | 2 | 18 | 2 | 95% | 117, 139 |
| tra/config.py | 38 | 0 | 2 | 0 | 100% | — |
| tra/diagnostics.py | 90 | 2 | 12 | 4 | 94% | 198, 208 (count_blocking stub — TRA-016/066) |
| tra/exceptions.py | 41 | 0 | 0 | 0 | 100% | — |
| tra/hitl.py | 31 | 1 | 10 | 2 | 93% | 57 (`on_override` callback path — TRA-D4-005) |
| tra/isa.py | 214 | 11 | 84 | 8 | 92% | 89, 102-103, 194, 242-243, 322, 581, **663-666 (structural repair dead code — TRA-D4-015)** |
| tra/kernel.py | 234 | 12 | 58 | 12 | 92% | 141, 165, 195, 261, 263, 355, **507-519 (interactive=True path — TRA-D4-007)**, 582 |
| tra/memory.py | 114 | 0 | 0 | 0 | 100% | — |
| tra/modules/registry.py | 70 | 4 | 26 | 8 | 88% | 98, 132, 138-139 |
| tra/policy.py | 9 | 0 | 0 | 0 | 100% | — |
| tra/recovery.py | 51 | 0 | 16 | 1 | 99% | — |
| tra/reporting.py | 40 | 0 | 16 | 0 | 100% | — |
| tra/utils.py | 37 | 0 | 14 | 0 | 100% | — |
| tra/validate.py | 35 | 0 | 6 | 3 | 93% | — |
| **TOTAL** | **1477** | **58** | **400** | **65** | **93%** | — |

**Coverage gaps that map to D4 findings:**
- `kernel.py:507-519` (interactive=True HITL handoff) — **TRA-D4-007 confirmed via coverage**
- `hitl.py:57` (`on_override` callback path) — **TRA-D4-005 confirmed via coverage**
- `isa.py:663-666` (structural repair dead branch) — **TRA-D4-015 confirmed via coverage** (NEW finding)
- `diagnostics.py:198,208` (`count_blocking` stub absent) — TRA-016 FIXED but **TRA-D4-013** (no regression test)
- `benchmark.py:93,96,109-113` (S-03/E-03 unimplemented) — **TRA-D4-006 confirmed**

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# Test count at HEAD
python -m pytest tests 2>&1 | tail -3
# → 199 passed in 1.17s

# Test collection summary
python -m pytest tests --co -q 2>&1 | tail -3
# → tests/test_validate.py: 4 (last file listed)

# Per-file test counts
for f in tests/test_*.py; do n=$(python -m pytest "$f" --co 2>&1 | grep -c "::"); echo "$f: $n"; done
# → tests/test_anchor.py: 7
# → tests/test_benchmark.py: 25
# → tests/test_e2e_to_translate.py: 12
# → tests/test_isa.py: 17
# → tests/test_kernel.py: 7
# → tests/test_modules.py: 17
# → tests/test_outstanding_findings.py: 64
# → tests/test_phase0.py: 11
# → tests/test_phase6_hardening.py: 7
# → tests/test_recovery.py: 9
# → tests/test_reporting.py: 5
# → tests/test_tra043_protocol.py: 3
# → tests/test_tra047_config_robustness.py: 2
# → tests/test_tra071_broken_markdown.py: 2
# → tests/test_utils.py: 7
# → tests/test_validate.py: 4
# TOTAL: 199

# Test file count
ls tests/test_*.py | wc -l
# → 16

# Test classes in test_outstanding_findings.py
rg "^class Test" tests/test_outstanding_findings.py | wc -l
# → 34

# Carry-over verification — TRA-088 (partial)
rg "class TestTRA088" tests/test_outstanding_findings.py
# → 2075:class TestTRA088SingleAuditRecordAllExceptions
# Verify: 2 tests (empty-response + TypeError); 4 paths still uncovered

# Carry-over verification — TRA-089 (fixed)
rg "class TestTRA089" tests/test_outstanding_findings.py
# → 2176:class TestTRA089ConformanceFailureE2E
# Verify: 2 tests (unclosed-fence + broken-link ConformanceFailure paths)

# Carry-over verification — TRA-090 (persistent)
rg "def run" tra/kernel.py
# → 211:    def run(self, source: str | Path) -> str:
# Verify: NO llm_translate parameter in run() signature

# Carry-over verification — TRA-091 (persistent)
rg "interactive=True" tests/ tra/
# → (no matches in tests/)
# Verify: kernel.py:505 has `if self.interactive:` but no test sets interactive=True

# Carry-over verification — TRA-092 (persistent)
cat tests/benchmark/cases/*.jsonl | wc -l
# → 22
# Verify: 21 sft + 1 regression = 22 cases; S-03 and E-03 still missing

# Carry-over verification — TRA-094 (persistent)
rg "mutmut|cosmic-ray|hypofuzz|pytest-mutation" pyproject.toml tra/ tests/
# → (no matches)

# Benchmark categories
python -c "
import json
from collections import Counter
with open('tests/benchmark/cases/sft.jsonl') as f:
    cases = [json.loads(line) for line in f if line.strip()]
print(Counter(c['category'] for c in cases))
# → Counter({'F': 5, 'T': 5, 'S': 5, 'D': 4, 'E': 2})
"

# Coverage report with branch coverage
python -m pytest tests --cov=tra --cov-report=term-missing --cov-branch -q 2>&1 | tail -25
# → 93% overall; tra/hitl.py:57 MISSED (on_override), tra/kernel.py:507-519 MISSED (interactive), tra/isa.py:663-666 MISSED (structural repair)

# TRA-A4-011 cross-list verification — `repaired = repaired` no-op
sed -n '651,655p' tra/isa.py
# → elif diagnostic.subsystem == "entity":
# →     name = diagnostic.issue.split("'")[1] if "'" in diagnostic.issue else ""
# →     if name and name not in repaired:
# →         repaired = repaired  # cannot conjure absent entity without source

# Verify TestTRA073 only greps for `out = out` (NOT `repaired = repaired`)
sed -n '1850p' tests/test_outstanding_findings.py
# →             if code_part == "out = out":

# TRA-B4-009 cross-list verification — TRA-016/017/026 have no regression test
rg "TestTRA016|TestTRA017|TestTRA026|TRA-016|TRA-017|TRA-026" tests/
# → (no matches)

# TRA-D4-014 verification — new redundant manual script
ls tests/run_e2e_translation.py && wc -l tests/run_e2e_translation.py
# → tests/run_e2e_translation.py / 186
rg "assert|def test_" tests/run_e2e_translation.py
# → (no matches — not pytest-collectible)
git log --oneline tests/run_e2e_translation.py
# → 805a8f8 feat(tra): E2E translation output + TDD remediation of 5 more Round 3 findings

# TRA-D4-015 verification — structural repair dead branch
sed -n '663,668p' tra/isa.py
# →     elif diagnostic.subsystem == "structural":
# →         # Surgical structural fix not automatable here without AST; flag.
# →         if attempt >= max_retries:
# →             raise Unrecoverable(
# →                 "UNRECOVERABLE: structural repair needs manual intervention"
# →             )
# Coverage: lines 663-666 MISSED across all 199 tests

# Class name vs docstring TRA reference consistency check
python -c "
import re
with open('tests/test_outstanding_findings.py') as f:
    content = f.read()
pattern = r'^class (Test\w+).*?\n\s+\"\"\"(.+?)\"\"\"'
matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
mismatches = 0
for cls, doc in matches:
    tra_refs = re.findall(r'TRA-\d+', doc)
    cls_ref = re.search(r'TRA(\d+)', cls)
    cls_id = f'TRA-{cls_ref.group(1)}' if cls_ref else None
    first_doc_ref = tra_refs[0] if tra_refs else None
    if not (cls_id and first_doc_ref and cls_id == first_doc_ref):
        mismatches += 1
        print(f'MISMATCH: {cls}')
print(f'Total classes: {len(matches)}, mismatches: {mismatches}')
"
# → Total classes: 34, mismatches: 0
```

## Conclusion

HEAD `805a8f8` has **199 tests passing** (up from 174 at R3 close), with 25 new tests landing in `test_outstanding_findings.py` across 12 new `TestTRA0XX` classes. The R3 Batch 4 test-suite remediation plan successfully closed 1 of 5 targeted gaps (TRA-089 fully fixed) and partially closed 1 more (TRA-088 — 3 of 7 LLM-seam degradation paths now assert the single-audit-record invariant; 4 still uncovered). The remaining 3 Batch 4 targets (TRA-090, TRA-091, TRA-092) are PERSISTENT — no source changes were made to address them. The 4 quality gates remain green (ruff format / ruff check / mypy --strict / pytest) and overall branch coverage is 93%.

The most material new test-coverage finding is **TRA-D4-012** (cross-listed from Track A4's TRA-A4-011): the `repaired = repaired` no-op at `isa.py:654` parallels the TRA-073 anti-pattern that was fixed, but the `TestTRA073DeadCodeRemoved` regression test was scoped too narrowly (literal `out = out` grep) to catch it. This means the TRA-073 enforcement-protective test gives false confidence — a future no-op self-assignment in any other variable would slip through. The recommended fix is a 1-line regex generalization.

The second new finding is **TRA-D4-014**: commit `805a8f8` (the SAME commit that landed the TRA-088/089 fixes) ALSO added a 186-LOC redundant manual e2e script (`tests/run_e2e_translation.py`) that duplicates `tests/test_e2e_to_translate.py`'s 12 proper pytest tests AND uses the same fragile module-level patching pattern that TRA-090 was supposed to eliminate. This is a regression in test-suite hygiene — R3 had 1 dead manual script, R4 has 2.

The benchmark suite remains stuck at 22 cases (22% of spec target) across 3 audit rounds. No new benchmark cases have been added since R2. S-03 (inline code vs prose) and E-03 (broken source markdown) are still missing — both are data-only additions (the runner already supports them).

The 5 WARNING findings (TRA-D4-002, 003, 007, 012, 013) form a coherent enforcement-protection backlog: each is a fix that landed without a regression test that would catch its revert. Track B4's mutation testing already confirmed 4 of 5 top R4 fixes ARE enforcement-protected (TRA-073/076/077/078); the WARNING findings here are the gaps where that protection is missing or partial. Addressing them is a small follow-up commit (estimated ~50 LOC of new test code).
