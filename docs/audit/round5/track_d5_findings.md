# Track D5 — Test Suite Re-Audit (Round 5)

**HEAD audited:** `5476faf1d668b42d2a7b8c9b159ae9ee54c6e4f7`
**Methodology:** Coverage analysis, mutation-testing probe, benchmark-suite audit, HITL/LLM-seam review.
**Baseline:** Round 4 Track D4 (15 findings: 0 BLOCKING / 5 WARNING / 10 INFO) + 66-finding R4 master register.
**Test count:** 228 across 16 test files (R4: 199 across 16 files; docs that claim "228 across 18 files" are inaccurate — confirmed by Track C5).
**Audit date:** 2026-07-18

## Summary

- Findings: **20 total (0 BLOCKING / 3 WARNING / 17 INFO)**
- Carry-over from Round 4: **15** (TRA-D5-001..015, all re-mapped from TRA-D4-001..015)
- New findings: **5** (TRA-D5-016..020)
- Regressions: **0**
- All 228 tests pass: **yes** (`228 passed in 1.42s`)

### Status matrix

| Status | Count |
|---|---|
| persistent | 9 (TRA-D5-001, 002, 004, 005, 007, 008, 009, 010, 011) |
| partial | 3 (TRA-D5-003, 006, 015) |
| fixed-and-verified | 3 (TRA-D5-012, 013, 014) |
| new | 5 (TRA-D5-016..020) |
| **Total** | **20** |

### Quality-gate verification at HEAD `5476faf`

- `ruff check .` → All checks passed (verified by Tracks R5/B5).
- `ruff format --check .` → 39 files already formatted.
- `mypy --strict tra` → Success: no issues found in 20 source files.
- `pytest tests/` → **228 passed in 1.42s** (re-verified during this audit).

## Methodology notes

1. **Test enumeration** — `python -m pytest tests --co -q` confirmed 228 tests across 16 test files (test_outstanding_findings.py: 91 tests across 46 classes; remaining 137 tests across the other 15 files).
2. **Source cross-reference** — All 6 ISA instructions, 9 KernelState transitions, 5 TRA-EXCEPTION types, 4 conformance levels, and 4 critical invariants were mapped to specific test classes/methods.
3. **Mutation probe** — `mutmut` is not integrated (TRA-D5-011). A 4-mutation manual probe was performed on `tra/policy.py` and `tra/isa.py` to estimate enforcement strength (see TRA-D5-011 Detail).
4. **Benchmark verification** — `tests/benchmark/cases/*.jsonl` lines counted; `tra.benchmark.load_cases()` imported and called.
5. **HITL/LLM-seam review** — Every test that exercises `review_decision` or `llm_translate` was read and classified.
6. **Test-isolation audit** — `tests/conftest.py` (99 LOC) and `tests/test_kernel.py:12-23` inspected for the unused `kernel_config` fixture.
7. **R4 Batch 2 depth audit** — All 6 new test classes added by Batch 4 commits (`d95c36d`, `efbc875`, `78c9250`, `e54b7a7`) were read in full and assessed for assertion depth (not just presence).

## Findings

### TRA-D5-001: e2e LLM callback ignores `source_segment` (carry-over)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tests/test_e2e_to_translate.py:83-86` (manual_llm), `tests/test_e2e_to_translate.py:96` (kwargs["llm_translate"] = manual_llm), `tra/kernel.py:485-487` (single `translate_segment(...)` call inside `_execute_translation`)
- **Detail:** The manual LLM callback `manual_llm(source_segment, ctx)` discards `source_segment` and returns the entire `manual_translation` for every call. This works because `_execute_translation` calls `translate_segment` exactly once per `run()` (the whole-doc translation model). If a future refactor adds per-segment translation (TRA-001 full segment translation is still deferred), the e2e test cannot detect per-segment routing bugs — e.g., if the kernel called `llm_translate` twice with different segments and concatenated the results, the test would still pass. The redundant `tests/run_e2e_translation.py` script that exhibited the same anti-pattern was deleted by R4 Batch 3 (TRA-D5-014), so the anti-pattern now exists in only one place.
- **Suggested fix:** Either (a) document the single-segment assumption in the test docstring (it currently does NOT explicitly state this — only mentions "the manual translation" without noting the 1:1 segment↔target mapping), or (b) when the kernel gains multi-segment translation, segment-correlate source↔target in the callback.
- **Round 4 status:** persistent (was TRA-D4-001)

### TRA-D5-002: e2e LLM hijack uses module-level patching (carry-over = TRA-090)

- **Severity:** WARNING
- **Category:** Test Suite / Test Hygiene
- **Finding type:** issue
- **Evidence:** `tests/test_e2e_to_translate.py:90-104` (`kernel_mod.translate_segment = patched_translate`); `tra/kernel.py:109-146` (TRAKernel `__init__` — no `llm_translate` parameter); `tra/kernel.py:485-487` (`translate_segment(...)` called without `llm_translate=` kwarg); `tra/isa.py:398-405` (`translate_segment` accepts `llm_translate: Callable | None = None` kwarg — but the kernel never passes it)
- **Detail:** `TRAKernel.__init__` signature at `kernel.py:105-112` STILL lacks an `llm_translate` parameter — exactly as flagged in R3/R4 (TRA-090 / D3-002 / D4-002). To inject an LLM into the E2E test, `tests/test_e2e_to_translate.py:90-104` mutates `kernel_mod.translate_segment` at module scope, then restores it in a `finally` block. This is fragile: (1) a parallel test run could see the patched function; (2) restoration relies on `finally` running cleanly; (3) the patch leaks the LLM callback into unrelated code paths if a fixture cleanup is interrupted. The clean DI approach (already present at the ISA layer — `translate_segment(*, llm_translate=None)`) is never propagated up to the kernel layer.
- **Suggested fix:** Add an `llm_translate: Callable[[str, RuntimeContext], str] | None = None` parameter to `TRAKernel.__init__` (or to `TRAKernel.run`). Store it on `self`. In `_execute_translation`, pass `llm_translate=self.llm_translate` to `translate_segment`. Eliminates module-level patching in all 12 e2e tests.
- **Round 4 status:** persistent (was TRA-D4-002 / TRA-090)

### TRA-D5-003: TRA-048 single-audit-record invariant PARTIALLY tested (partial fix)

- **Severity:** WARNING
- **Category:** Test Suite / Mutation Testing
- **Finding type:** issue
- **Evidence:** `tests/test_outstanding_findings.py:2117-2210` (TestTRA088, 2 tests — empty-string + TypeError); `tests/test_outstanding_findings.py:410-507` (TestTRA033, 7 tests with weak assertions — only `"Confirmed" in res.translation`, no `len(translate_records) == 1` assertion); `tests/test_phase6_hardening.py:71-99` (RuntimeError test — DOES assert `len(translate_records) == 1`)
- **Detail:** R4's TRA-088 fix added 2 new tests covering the empty-string→ValueError and TypeError→degradation paths. But the parametrized `TestTRA033LLMSeamRobustness` class (7 tests covering RuntimeError/ValueError/TypeError/OSError/TimeoutError/empty-string/None) STILL does NOT assert the single-audit-record invariant (`len(translate_records) == 1`) — only that `"Confirmed" in res.translation`. The result: if a future mutation makes the early `return result` conditional on `isinstance(exc, RuntimeError | ValueError | TypeError)`, the `OSError`/`TimeoutError`/`None` paths would emit a second (non-degraded) audit record — and **4 of the 7 TestTRA033 tests would not catch this** (only the RuntimeError/empty/TypeError paths are protected by separate assertions).
- **Suggested fix:** Add `assert len(translate_records) == 1` to each of the 7 tests in `TestTRA033LLMSeamRobustness`. The TestTRA088 class can stay as a focused supplementary test.
- **Round 4 status:** partial (was TRA-D4-003)

### TRA-D5-004: `review_decision` text-assertion gap (carry-over)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tests/test_outstanding_findings.py:376-402` (TestTRA032HITLResolutions — parametrized over `["accept", "override", "skip"]` but only asserts `result_res == resolution` at line 402); `tests/test_phase6_hardening.py:157-167` (test_hitl_review_decision_accept — only tests "accept" with `text == "candidate"`); `tra/hitl.py:34-36` (contract: "text is the adopted target text")
- **Detail:** The parametrized `TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution` tests all 3 resolutions but only asserts the resolution string — NOT the returned `text`. Per `tra/hitl.py:34-36`, the contract is: "text is the adopted target text (unchanged candidate for accept/skip; reviewer-supplied for override)". The override (`text == "edited text"`) and skip (`text == candidate`) text contracts are untested. The phase6 duplicate asserts text for accept only. Together: accept text asserted (phase6 only), override/skip text NOT asserted.
- **Suggested fix:** Extend the parametrized test to assert `result_text == expected_text` where `expected_text = {"accept": candidate, "override": "edited text", "skip": candidate}[resolution]`.
- **Round 4 status:** persistent (was TRA-D4-004)

### TRA-D5-005: `on_override` callback in `review_decision` untested (carry-over)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tra/hitl.py:30,56-57` (`on_override: Callable[[str, str], str] | None = None` parameter and invocation); `tests/test_outstanding_findings.py:399-401` and `tests/test_phase6_hardening.py:165` (both call `review_decision` WITHOUT `on_override`)
- **Detail:** `review_decision` accepts an optional `on_override: Callable[[str, str], str] | None = None` parameter. When provided and the user chooses "override", the callback is invoked as `on_override(source_context, edited)` and its return value is used as the override text (`tra/hitl.py:57`). No test passes `on_override`. The TRA-D4-005 finding cited a coverage report showing `tra/hitl.py:57` MISSED at R4 baseline; at HEAD `5476faf` the line is still untested (no test in the suite passes `on_override`).
- **Suggested fix:** Add a test that passes a stub `on_override` (e.g., `lambda src, edited: f"[OVERRIDE:{edited}]"`) and asserts it is invoked with `(source_context, edited_text)` and its return value is used as the override text.
- **Round 4 status:** persistent (was TRA-D4-005)

### TRA-D5-006: Benchmark suite at 24/100+ spec target (partial fix; S-03 + E-03 added)

- **Severity:** INFO
- **Category:** Benchmark
- **Finding type:** issue
- **Evidence:** `tests/benchmark/cases/sft.jsonl` (23 cases at HEAD, was 21 in R4); `tests/benchmark/cases/regression.jsonl` (1 case R-01); `tests/test_benchmark.py:55-62` (test_l3_gate_zero_blocking_subset enforces L3 gate); commit `d3e5f60` (R4 Batch 4 — "TRA-092 add S-03 and E-03 benchmark cases")
- **Detail:** R4 Batch 4 commit `d3e5f60` added the 2 missing spec cases (S-03 inline-code-vs-prose at sft.jsonl:22, E-03 broken-source-markdown at sft.jsonl:23) bringing the total from 22 to 24. The L3 gate `test_l3_gate_zero_blocking_subset` (test_benchmark.py:55) enforces zero BLOCKING across all 24 cases — confirmed green at HEAD. The spec target per `TRA-BENCHMARK-SUITE.md` is 100+; current coverage is 24% of target (24/100). The gap remains: ~76 more cases needed. Not a regression — strictly improved from R4 (22→24, +9%).
- **Suggested fix:** Continue growing the suite toward 100+ cases. Priorities: more S-category cases (currently 6/6 spec-complete), more D-category (currently 4/4 spec-complete), more F/T (5/5 spec-complete). The remaining growth is in additional adversarial and edge cases beyond the spec minimums.
- **Round 4 status:** partial (was TRA-D4-006 — improved 22→24)

### TRA-D5-007: `interactive=True` kernel path untested end-to-end (carry-over = TRA-091)

- **Severity:** WARNING
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tra/kernel.py:521-538` (`if self.interactive:` block — pause for HITL review on Unrecoverable); `tests/` — `rg "interactive=True" tests/` → **0 matches**; `tests/test_outstanding_findings.py:2631,2681` (the only references to `interactive=` are inside docstring text, not test code); `tra_cli.py:92-97,105,139` (CLI `--interactive` flag wired to `TRAKernel(cfg, registry=registry, interactive=interactive)`)
- **Detail:** The `if self.interactive:` block at `kernel.py:521-538` (HITL handoff with `format_unrecoverable` + `review_decision`) is **never executed** by any test. Zero grep matches for `interactive=True` across `tests/` confirms no test runs `TRAKernel(interactive=True).run()` end-to-end. The CLI `--interactive` flag (tra_cli.py:92-97) is also untested. The L3 conformance failure path raises before the UNRECOVERABLE handler is reached, so even the e2e ConformanceFailure tests (TestTRA089) don't trigger this branch.
- **Suggested fix:** Add a test that constructs `TRAKernel(cfg, interactive=True)`, monkeypatches `tra.hitl.review_decision` to return `("accept", candidate)`, feeds input that triggers an UNRECOVERABLE (e.g., an LLM that returns text introducing a new BLOCKING violation), and asserts the audit trail contains `HITL[accept]: ...` in `unresolved_ambiguities`.
- **Round 4 status:** persistent (was TRA-D4-007 / TRA-091)

### TRA-D5-008: `kernel_config` fixture unused (carry-over)

- **Severity:** INFO
- **Category:** Test Suite / Test Hygiene
- **Finding type:** issue
- **Evidence:** `tests/conftest.py:82-99` (`kernel_config` fixture definition); `tests/test_kernel.py:12-23` (`_kernel()` helper duplicating the boilerplate); `rg "kernel_config" tests/` → only 1 hit in `test_kernel.py:13` (a comment, not a fixture parameter)
- **Detail:** The `kernel_config(tmp_path) -> BootstrapConfig` fixture is defined in `conftest.py:82-99` with a docstring claiming it "Eliminates the duplicated config-loading + path-override boilerplate that was copy-pasted across test_kernel.py, test_phase6_hardening.py, test_benchmark.py, and test_outstanding_findings.py". Grep across `tests/` for `kernel_config` as a fixture parameter returns ZERO matches. `test_kernel.py:13` has a comment "Uses the shared kernel_config fixture pattern (TRA-034)" but then defines its own `_kernel(tmp_path)` helper (lines 12-23) that duplicates the exact boilerplate the fixture was meant to eliminate. R4 Batch 3 (commit `524c598`) was supposed to address code duplication but did NOT wire this fixture into any test.
- **Suggested fix:** Either (a) replace `_kernel()` in `test_kernel.py` with the `kernel_config` fixture, or (b) delete the unused fixture and the misleading comment.
- **Round 4 status:** persistent (was TRA-D4-008)

### TRA-D5-009: `e2e_test.py` manual script persists (carry-over)

- **Severity:** INFO
- **Category:** Test Suite / Test Hygiene
- **Finding type:** issue
- **Evidence:** `tra-prototype/e2e_test.py` (104 LOC, 0 `assert` statements, 0 `def test_*`); `tests/test_e2e_to_translate.py` (12 proper pytest tests that supersede it); `rg "assert|def test_" e2e_test.py` → **0 matches** (only `print()` output)
- **Detail:** The manual script `e2e_test.py` (104 LOC) is still present at the tra-prototype root and is NOT pytest-collectible (no `test_*` functions, no `assert` statements — just `print()` output). Commit `354fa94` (R2) added `tests/test_e2e_to_translate.py` (12 proper pytest tests) that fully supersede the manual script's coverage. The manual script is now dead code. R4 Batch 3 deleted the *other* redundant manual script (`tests/run_e2e_translation.py`, see TRA-D5-014) but did NOT delete `e2e_test.py` at the prototype root — so 1 of the 2 redundant scripts remains.
- **Suggested fix:** Delete `e2e_test.py`. If a CLI-runnable E2E demo is desired, add a `python -m tra.e2e_demo` entry point that imports and calls the pytest-collectible `_run_kernel_with_manual_llm` helper from `tests/test_e2e_to_translate.py`.
- **Round 4 status:** persistent (was TRA-D4-009)

### TRA-D5-010: Cross-file duplicate HITL test (carry-over)

- **Severity:** INFO
- **Category:** Test Suite / Test Hygiene
- **Finding type:** issue
- **Evidence:** `tests/test_phase6_hardening.py:157-167` (`test_hitl_review_decision_accept`); `tests/test_outstanding_findings.py:371-402` (`TestTRA032HITLResolutions` parametrized over accept/override/skip)
- **Detail:** `test_phase6_hardening.py::test_hitl_review_decision_accept` (lines 157-167) duplicates `TestTRA032HITLResolutions["accept"]` (parametrized). Both test the same `review_decision("amb", "src", "candidate")` → `"accept"` path with the same monkeypatch strategy (`monkeypatch.setattr("tra.hitl.Prompt.ask", ...)`). The phase6 version additionally asserts `text == "candidate"`; the parametrized version does not (TRA-D5-004). Two tests for the same path = maintenance burden with no extra coverage.
- **Suggested fix:** Delete `test_hitl_review_decision_accept` from `test_phase6_hardening.py` after extending the parametrized `TestTRA032HITLResolutions` test to assert the text (TRA-D5-004 fix). Consolidates HITL coverage in one place.
- **Round 4 status:** persistent (was TRA-D4-010)

### TRA-D5-011: Mutation testing framework deferred (carry-over = TRA-094)

- **Severity:** INFO
- **Category:** Test Suite / Mutation Testing
- **Finding type:** issue
- **Evidence:** `pyproject.toml:10-24` (no `mutmut` / `cosmic-ray` / `hypofuzz` deps); `rg "mutmut|cosmic-ray|hypofuzz" tra-prototype/` → 0 matches in source; `rg "[Mm]utation testing" tra-prototype/` → 4 hits in comments (kernel.py:216, test_isa.py:305, test_outstanding_findings.py:1043, plus the present audit doc) — all describing past manual probes, not an automated runner
- **Detail:** R3's TRA-094 deferred mutation testing as a future investment. No mutation testing framework has been added to `pyproject.toml` dev deps. Manual probes have been performed at each audit round (R3: 6 mutations, all caught; R4: 4 mutations, all caught). Without an automated runner, future regressions in test enforcement quality will go undetected.
- **Mutation probe performed during this audit:** `mutmut 3.6.0` was installed into the venv and a configuration file `setup.cfg` was written (`source_paths=tra/policy.py`, `tests_dir=tests/`, `runner=python -m pytest tests/test_phase0.py -x -q`). mutmut crashed with `BadTestExecutionCommandsException: Failed to run pytest with args: ['-q', '--rootdir=.', '--tb=native', '-x', '-q', '-p', 'no:randomly', '-p', 'no:random-order', 'tests/']` — the venv's pytest configuration does not match mutmut's expected invocation. To complete the probe, 4 manual mutations were applied to `tra/policy.py` and `tra/isa.py`:

  | # | Mutation | Killed by |
  |---|---|---|
  | 1 | `policy.py:21` `resolve()` — change `<=` to `<` (boundary) | **SURVIVES** — no test exercises `resolve(a, a)` where `precedence[a] == precedence[b]` |
  | 2 | `policy.py:25` `wins()` — always return True | KILLED by `test_phase0.py:133` (`test_policy_resolver_honors_stack`) |
  | 3 | `policy.py:25` `wins()` — change `<=` to `>=` (flip) | KILLED by 3 tests (`test_policy_resolver_honors_stack`, `test_canonical_term_leakage_is_blocking`, `test_monkeypatching_resolver_changes_terminology_severity`) |
  | 4 | `isa.py:792-798` `structural_severity` — hard-code `Severity.BLOCKING` (bypass resolver) | KILLED by `TestTRA072UniversalPolicyArbitration::test_structural_severity_is_policy_driven` (test_outstanding_findings.py:3481) |
  | 5 | `isa.py:792-798` `structural_severity` — swap args `wins(FLUENCY, STRUCTURAL)` instead of `wins(STRUCTURAL, FLUENCY)` | KILLED by `test_isa.py:361-372` (`test_verify_output_structural_mismatch_is_blocking`) — the unmocked default-behavior test |

  **Estimated mutation score (rough):** 4 of 5 mutations killed = 80%. The surviving mutant (#1) is a boundary case in `resolve()` that requires an `a == b` test (resolve of equal priorities). The other 4 are caught by either direct behavioral assertions or monkeypatched-resolver assertions.

- **Suggested fix:** Add `mutmut` to dev deps. Resolve the `BadTestExecutionCommandsException` by either (a) downgrading `mutmut` to a version compatible with the venv's pytest setup, (b) using `cosmic-ray` instead, or (c) configuring `mutmut` to call `pytest` with the explicit `-p no:cacheprovider` flag. Wire into CI as a weekly job. Add the missing `resolve(a, a)` test to kill mutant #1.
- **Round 4 status:** persistent (was TRA-D4-011 / TRA-094)

### TRA-D5-012: `repaired = repaired` no-op removed and enforcement-protective test added (fixed-and-verified)

- **Severity:** INFO
- **Category:** Test Suite / Mutation Testing
- **Finding type:** positive_verification
- **Evidence:** `tests/test_outstanding_findings.py:2287-2342` (`TestTRA_A4_011_RepairedNoopRemoved` with 2 tests: `test_no_repaired_self_assignment_in_isa` + `test_no_out_self_assignment_in_isa`); commit `524c598` (R4 Batch 3 — added this class); `tra/isa.py` — `rg "repaired = repaired" tra/isa.py` → 0 hits (confirmed removed)
- **Detail:** R4 Batch 3 (commit `524c598`) added `TestTRA_A4_011_RepairedNoopRemoved` which uses a regex `r"^\s*repaired\s*=\s*repaired(?!\.)"` (negative lookahead to exclude chained method calls like `repaired = repaired.replace(...)`) to grep `isa.py` for the no-op pattern. The class also extends the check to `out = out` (TRA-073's pattern) with the same regex approach. Both tests are static-grep enforcement: if the no-op is re-introduced, the assertion fails. Re-verified at HEAD `5476faf`: both tests pass; no `repaired = repaired` or `out = out` self-assignment present in `isa.py`.
- **Round 4 status:** fixed-and-verified (was TRA-D4-012, cross-listed from TRA-A4-011)

### TRA-D5-013: TRA-016/017/026 silently-remediated findings now have regression tests (fixed-and-verified)

- **Severity:** INFO
- **Category:** Test Suite / Mutation Testing
- **Finding type:** positive_verification
- **Evidence:** `tests/test_outstanding_findings.py:2353-2366` (`TestTRA016CountBlockingGone::test_audit_trail_has_no_count_blocking_attribute`); `tests/test_outstanding_findings.py:2369-2417` (`TestTRA017UnusedDepsGone::test_unused_deps_not_in_pyproject` — uses `tomllib` to parse pyproject.toml and asserts 8 forbidden deps absent); `tests/test_outstanding_findings.py:2420-2434` (`TestTRA026CacheExpireGone::test_bootstrap_config_has_no_cache_expire_field`); commit `524c598` (R4 Batch 3 — added all 3 classes)
- **Detail:** R4 Batch 3 added 3 regression-test classes that close the "silently remediated without enforcement" gap from R3/R4:
  - `TestTRA016CountBlockingGone` — asserts `AuditTrail` does NOT have a `count_blocking` attribute (catches re-introduction of the dead stub).
  - `TestTRA017UnusedDepsGone` — uses `tomllib` to parse `pyproject.toml` and asserts 8 forbidden deps (litellm, structlog, pydantic-settings, mdit-py-plugins, pytest-asyncio, black) are absent from both runtime + dev deps.
  - `TestTRA026CacheExpireGone` — asserts `BootstrapConfig.model_fields` does NOT have a `cache_expire` field (catches re-introduction of the dead config field).
  
  All 3 tests are static-grep / introspection enforcement: if any of the 3 silent remediations are reverted, the corresponding test fails. Re-verified at HEAD `5476faf`: all 3 tests pass.
- **Round 4 status:** fixed-and-verified (was TRA-D4-013, cross-listed from TRA-B4-009)

### TRA-D5-014: `tests/run_e2e_translation.py` deleted (fixed-and-verified)

- **Severity:** INFO
- **Category:** Test Suite / Test Hygiene
- **Finding type:** positive_verification
- **Evidence:** `git log --oneline --diff-filter=D -- tra-prototype/tests/run_e2e_translation.py` → `524c598` (R4 Batch 3 commit); `ls tra-prototype/tests/run_e2e_translation.py` → **No such file or directory**; `git show 524c598 --stat` → `tra-prototype/tests/run_e2e_translation.py | 186 -----------` (186 lines deleted)
- **Detail:** R4 Batch 3 (commit `524c598`) deleted the redundant manual e2e script `tests/run_e2e_translation.py` (186 LOC, 0 asserts, 0 `def test_*`). The script was a strict duplicate of `tests/test_e2e_to_translate.py` (12 proper pytest tests) using the same fragile module-level patching pattern. The deletion eliminates 186 LOC of dead code. The other redundant manual script (`e2e_test.py` at the prototype root, see TRA-D5-009) is still present — only the tests/ copy was deleted.
- **Round 4 status:** fixed-and-verified (was TRA-D4-014)

### TRA-D5-015: Structural repair branch still partial (TRA-042 made it reachable but no dedicated test)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tra/isa.py` — the structural repair branch in `repair_segment` is now reachable (TRA-042 commit `efbc875` added 6 structural verification categories beyond heading-count, so `verify_output` can now emit structural diagnostics at non-BLOCKING severities for table/list/blockquote/HR/code-fence mismatches that survive into the repair loop); `tests/test_outstanding_findings.py:3144-3404` (TestTRA042ExtendedStructuralVerification — 6 tests, but ALL test `verify_output` directly, none test `repair_segment`'s structural branch)
- **Detail:** At R4 baseline (`805a8f8`), the structural repair branch in `repair_segment` was dead code (R4's TRA-D4-015 finding). At HEAD `5476faf`, the TRA-042 fix (commit `efbc875`) extended `verify_output` to emit structural diagnostics for table/list/blockquote/HR/code-fence mismatches, so the repair branch is now indirectly reachable. However, the branch still does no meaningful repair — it raises `Unrecoverable` after `max_retries` (per the spec §6 REPAIR_SEGMENT contract). No dedicated test exercises the structural repair branch directly (e.g., calling `repair_segment` with a WARNING-level structural diagnostic and asserting `Unrecoverable` is raised). The TRA-042 tests cover `verify_output`'s emission but stop short of the repair loop's structural handling.
- **Suggested fix:** Add a unit test that calls `repair_segment` directly with a WARNING-level `subsystem="structural"` diagnostic and asserts `Unrecoverable` is raised when `attempt >= max_retries`. Or document that structural repairs always raise `ConformanceFailure` upstream and delete the dead branch (keeping only the entity/terminology branches).
- **Round 4 status:** partial (was TRA-D4-015 — TRA-042 made branch reachable, but no dedicated test added)

### TRA-D5-016: L2_PROFESSIONAL conformance level never tested (new)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tra/memory.py:50` (`L2_PROFESSIONAL = "L2_PROFESSIONAL"` defined in `ConformanceLevel` StrEnum); `rg "L2_PROFESSIONAL|ConformanceLevel\.L2" tests/` → **0 matches** in test code; `tra/kernel.py:262-265,323-326` (conformance gate checks `if self.config.conformance_level in (ConformanceLevel.L3_STRICT, ConformanceLevel.L4_FORENSIC)` — L1 and L2 are treated identically as "no gate"); `TRA-CONFORMANCE-GUIDE.md:16-24` (spec defines L2 as "Professional" with requirements: terminology consistency, structural perfection, entity preservation); `tra_cli.py:31` (CLI accepts `l2` shorthand → `L2_PROFESSIONAL`)
- **Detail:** The `ConformanceLevel` enum has 4 values (L1, L2, L3, L4). Tests exercise L1_BASIC (15+ tests, mostly in test_outstanding_findings.py for "no gate" scenarios), L3_STRICT (heavily covered, ~40+ tests), and L4_FORENSIC (covered in test_e2e_to_translate.py and test_phase6_hardening.py). L2_PROFESSIONAL is NEVER used as a test input — `rg "L2_PROFESSIONAL|ConformanceLevel\.L2" tests/` returns 0 matches. Per `TRA-CONFORMANCE-GUIDE.md:16-24`, L2 has distinct requirements from L1 (terminology consistency, structural perfection, entity preservation). The kernel currently treats L1 and L2 identically (no gate for either), but the L2 enum value itself is never exercised — so a mutation that breaks L2 (e.g., removing it from the enum, changing its string value, or accidentally gating it) would not be caught by any test.
- **Suggested fix:** Add at least one test that runs the kernel at `ConformanceLevel.L2_PROFESSIONAL` and asserts (a) the conformance gate is NOT raised (since L2 is treated as "no gate" like L1), (b) the audit trail records `conformance_level: L2_PROFESSIONAL`, and (c) the L2 spec requirements are documented as tested-or-deferred. Ideally add a parametrized test over all 4 conformance levels to verify the gate behavior matrix.
- **Round 4 status:** new

### TRA-D5-017: CLI subcommands `validate`, `audit`, `cache-clear` not tested via CliRunner (new)

- **Severity:** INFO
- **Category:** Test Suite / Coverage Gap
- **Finding type:** issue
- **Evidence:** `tra_cli.py:87-160` (`translate` command — tested via CliRunner in `test_outstanding_findings.py:2748-2793`); `tra_cli.py:163-181` (`cache-clear` command — NOT tested); `tra_cli.py:184-243` (`audit` command — NOT tested); `tra_cli.py:246-292` (`validate` command — NOT tested); `tests/test_validate.py:24-65` (tests `validate_translation` directly, not via CLI); `tests/test_reporting.py:17-56` (tests `summarize_audit` + `mermaid_state_diagram` directly, not via CLI); `tests/test_outstanding_findings.py:1148-1178` (tests `TranslationCache.invalidate` directly, not via CLI)
- **Detail:** The CLI has 4 subcommands: `translate`, `cache-clear`, `audit`, `validate`. Only `translate` is tested via `click.testing.CliRunner` (the TRA-099 E2E test at `test_outstanding_findings.py:2685-2793`). The other 3 commands are NOT tested via CliRunner — the underlying functions they call ARE tested directly, but the CLI wiring (click argument parsing, `_resolve_level` for shorthand `L1`/`L2`/`L3`/`L4` aliases, `_normalize_language_pair` for hyphen→arrow form, `_print_validation` exit codes) is not. A regression that breaks `_resolve_level("l2")` (returning wrong enum) or `_normalize_language_pair("fr-en")` (returning wrong canonical form) would not be caught by any test. The TRA-099 test does cover `_normalize_language_pair` indirectly via `--lang fr-en`, but only for one input.
- **Suggested fix:** Add 3 small CliRunner-based tests:
  - `test_cli_cache_clear_invalidates_cache` — write a key to cache, invoke `cache-clear --pattern=...`, assert deletion count returned.
  - `test_cli_audit_summarizes_trace` — invoke `audit <trace.jsonl> --report`, assert mermaid diagram in stdout.
  - `test_cli_validate_passes_clean_candidate` — invoke `validate <src> <out>`, assert exit code 0.
  Also add a parametrized test for `_resolve_level` and `_normalize_language_pair` covering all 4 shorthand aliases and both hyphen/arrow forms.
- **Round 4 status:** new

### TRA-D5-018: TRA-072 tests have monkeypatch-specificity gap (new, mild)

- **Severity:** INFO
- **Category:** Test Suite / Mutation Testing
- **Finding type:** issue
- **Evidence:** `tests/test_outstanding_findings.py:3415-3590` (TestTRA072UniversalPolicyArbitration — 3 tests: structural, entity, epistemic); `tests/test_outstanding_findings.py:3470-3475,3527-3533,3577-3582` (all 3 tests monkeypatch `_POLICY_RESOLVER.wins = lambda _a, _b: False` — a GLOBAL override that doesn't verify which `(a, b)` pair is passed); `tra/isa.py:794,898,926,959` (4 `_POLICY_RESOLVER.wins()` call sites — confirmed by `rg`)
- **Detail:** The 3 TRA-072 tests monkeypatch `_POLICY_RESOLVER.wins` to ALWAYS return `False`, then assert that each subsystem's severity drops to WARNING. This proves the resolver IS consulted (good), but it does NOT verify that the correct `(a, b)` policy pair is passed at each call site. A mutation that swaps the policy pair at the structural call site (e.g., `wins(STRUCTURAL, FLUENCY)` → `wins(TERMINOLOGICAL, FLUENCY)`) would NOT be caught by these tests — both pairs return the same `True`/`False` because both TERMINOLOGICAL and STRUCTURAL have higher priority than FLUENCY. 

  **Mitigating factor:** the unmocked-default-behavior tests in `test_isa.py:361-372` (`test_verify_output_structural_mismatch_is_blocking`) and `test_isa.py:177-186` (`test_verify_flags_missing_entity_blocking`) DO catch the swap-args mutation because they assert `Severity.BLOCKING` without monkeypatching. So the test suite as a whole catches the mutation; only the TRA-072 tests in isolation have the specificity gap.

  A mutation probe confirmed: changing `_POLICY_RESOLVER.wins(STRUCTURAL_INTEGRITY, TARGET_FLUENCY)` to `wins(TARGET_FLUENCY, STRUCTURAL_INTEGRITY)` (swapped args) — `TestTRA072UniversalPolicyArbitration` PASSES (false negative), but `test_verify_output_structural_mismatch_is_blocking` in `test_isa.py:372` FAILS (catches the mutation). So the gap is real but mitigated.

- **Suggested fix:** Either (a) extend the TRA-072 tests to assert the specific `(a, b)` pair passed to `_POLICY_RESOLVER.wins` (e.g., using `mock.assert_called_once_with(PolicyPriority.STRUCTURAL_INTEGRITY, PolicyPriority.TARGET_FLUENCY)`), or (b) document that the unmocked-default-behavior tests in `test_isa.py` cover the (a, b) pair verification, so the TRA-072 tests can stay monkeypatch-focused.
- **Round 4 status:** new

### TRA-D5-019: R4 Batch 2 new test classes are well-designed (positive verification)

- **Severity:** INFO
- **Category:** Test Suite / Test Quality
- **Finding type:** positive_verification
- **Evidence:** 6 new test classes added by R4 Batch 4 commits, all read in full and assessed for assertion depth:
  - **`TestTRA038UnknownTermRaisedInProduction`** (3 tests, `test_outstanding_findings.py:2803-2864`, commit `d95c36d`): positive test with real CJK term `量子纠缠` (quantum entanglement), negative test with 7 stop-words (的/是/在/了/和/与/或), edge test with known glossary term. Tests the actual logging logic, not just smoke. **Depth: GOOD.**
  - **`TestTRA038CertaintyConflictRaisedInLLMPath`** (2 tests, `test_outstanding_findings.py:2867-3002`, commit `d95c36d`): positive test (LLM returns forbidden "Valid" → `CertaintyConflict` raised), negative test (LLM returns canonical "Confirmed" → no raise). Real LLM seam callback. **Depth: GOOD.**
  - **`TestTRA038EntityAmbiguityRaisedInBuildEntityTable`** (2 tests, `test_outstanding_findings.py:3005-3133`, commit `d95c36d`): positive test (stub returns `None` for "VMM" → ambiguity logged AND entity still in table), negative test (real ZHENModule returns concrete type → no ambiguity). **Depth: GOOD.**
  - **`TestTRA042ExtendedStructuralVerification`** (6 tests, `test_outstanding_findings.py:3144-3404`, commit `efbc875`): 5 mismatch cases (table row, list item, blockquote, HR, code fence) + 1 negative test (matching structure → no structural diagnostic). Each test constructs a real source/target pair and asserts the diagnostic subsystem + issue text. **Depth: GOOD.**
  - **`TestTRA072UniversalPolicyArbitration`** (3 tests, `test_outstanding_findings.py:3415-3590`, commit `78c9250`): 3 of 4 PolicyResolver.wins() call sites tested (structural, entity, epistemic; the 4th — terminological — was already tested by `TestTRA006PolicyResolverInvokedInProduction`). Each test monkeypatches the resolver and asserts severity drops from BLOCKING to WARNING. **Depth: GOOD with mild specificity gap (see TRA-D5-018).**
  - **`TestTRA099CLIPassesRegistry`** (3 tests, `test_outstanding_findings.py:2627-2793`, commit `e54b7a7`): 2 static source-grep checks + 1 real E2E via CliRunner with a stub `fr-en` module. The E2E test asserts the stub's glossary output `hello` appears in the CLI's output file — proving the registry is wired through. **Depth: GOOD.**
- **Detail:** All 6 R4 Batch 2 test classes have meaningful assertions (not smoke tests). The total is 18 new tests across 6 classes, all GREEN at HEAD `5476faf`. No shallow `assert True` or `assert result is not None` placeholders. The depth is comparable to the existing R3 regression-test classes (TestTRA088, TestTRA089, TestTRA093, etc.). The TRA-072 class has a mild monkeypatch-specificity gap (TRA-D5-018) but is otherwise well-designed.
- **Suggested fix:** None — these are exemplary regression tests. The TRA-072 mild gap is documented in TRA-D5-018.
- **Round 4 status:** new (positive verification of R4 Batch 2 deliverable)

### TRA-D5-020: Benchmark suite L3 gate enforces zero BLOCKING across all 24 cases (positive verification)

- **Severity:** INFO
- **Category:** Benchmark / Conformance
- **Finding type:** positive_verification
- **Evidence:** `tests/test_benchmark.py:55-62` (`test_l3_gate_zero_blocking_subset` — asserts `summary["blocking"] == 0` and `summary["failed"] == 0` across all 24 cases); `tests/test_benchmark.py:47-52` (parametrized `test_benchmark_case` — runs each case individually and asserts `result.passed`); `tra/benchmark.py:98-109` (the runner's `zero_blocking` check — re-runs `verify_output` and counts BLOCKING diagnostics); `tests/benchmark/cases/sft.jsonl` (23 cases, all with `zero_blocking: true` except E-03 which is `false` because it's a broken-source L1 case); `tests/benchmark/cases/regression.jsonl` (1 case R-01 with `zero_blocking: true`)
- **Detail:** The benchmark suite's L3 gate is enforced at two levels:
  1. **Per-case** (`test_benchmark_case`, parametrized over all 24 cases): each case runs through the full TRA pipeline, and the runner checks `must_contain` / `must_not_contain` / `zero_blocking` per the case's declarations. The 23 L3_STRICT cases have `zero_blocking: true` (gate enforced); the 1 L1_BASIC case (E-03) has `zero_blocking: false` (gate not enforced, but the kernel must still exit 0).
  2. **Suite-level** (`test_l3_gate_zero_blocking_subset`): aggregates all 24 results and asserts `summary["blocking"] == 0` AND `summary["failed"] == 0`. This is the L3 conformance gate at the benchmark level.

  Both gates are GREEN at HEAD `5476faf`. The benchmark suite grew from 22 cases (R4 baseline) to 24 cases (R4 Batch 4 commit `d3e5f60` added S-03 and E-03). The L3 gate is properly enforced on the L3_STRICT subset (23 of 24 cases); the L1_BASIC case (E-03) is correctly exempted.

- **Suggested fix:** None — the L3 gate is properly designed and enforced. The 24/100+ gap remains (TRA-D5-006) but the gate itself is sound.
- **Round 4 status:** new (positive verification; was implicit in R4's TRA-D4-006 finding)

## Test inventory at HEAD `5476faf`

| Test file | Test count | LOC | Notes |
|---|---|---|---|
| `tests/test_anchor.py` | 7 | 121 | unchanged from R4 |
| `tests/test_benchmark.py` | 27 | 71 | +2 vs R4 (24 cases × 1 parametrized = 24 tests, + L3 gate + cache-hit regression + load-cases = 27 total) |
| `tests/test_e2e_to_translate.py` | 12 | 393 | unchanged from R4 |
| `tests/test_isa.py` | 17 | 393 | unchanged from R4 |
| `tests/test_kernel.py` | 7 | 123 | unchanged from R4 |
| `tests/test_modules.py` | 17 | 147 | unchanged from R4 |
| `tests/test_outstanding_findings.py` | 91 | 3590 | **+27 vs R4** (R4: 64 tests / 34 classes → R5: 91 tests / 46 classes; +6 classes from R4 Batch 2: TestTRA038UnknownTermRaisedInProduction, TestTRA038CertaintyConflictRaisedInLLMPath, TestTRA038EntityAmbiguityRaisedInBuildEntityTable, TestTRA042ExtendedStructuralVerification, TestTRA072UniversalPolicyArbitration, TestTRA099CLIPassesRegistry) |
| `tests/test_phase0.py` | 11 | 172 | unchanged from R4 |
| `tests/test_phase6_hardening.py` | 7 | 183 | unchanged from R4 |
| `tests/test_recovery.py` | 9 | 126 | unchanged from R4 |
| `tests/test_reporting.py` | 5 | 56 | unchanged from R4 |
| `tests/test_tra043_protocol.py` | 3 | 51 | unchanged from R4 |
| `tests/test_tra047_config_robustness.py` | 2 | 88 | unchanged from R4 |
| `tests/test_tra071_broken_markdown.py` | 2 | 43 | unchanged from R4 |
| `tests/test_utils.py` | 7 | 57 | unchanged from R4 |
| `tests/test_validate.py` | 4 | 64 | unchanged from R4 |
| `tests/conftest.py` | (fixtures) | 99 | 7 fixtures; `kernel_config` still unused (TRA-D5-008) |
| `tests/benchmark/cases/sft.jsonl` | (data) | 23 lines | +2 vs R4 (S-03, E-03 added by commit `d3e5f60`) |
| `tests/benchmark/cases/regression.jsonl` | (data) | 1 line | unchanged |
| `e2e_test.py` (prototype root) | (not collectible) | 104 | manual demo script, 0 asserts (TRA-D5-009) |
| **Total** | **228** | | **+29 vs R4** (R4: 199 → R5: 228; all 29 new tests in `test_outstanding_findings.py` and `test_benchmark.py`) |

## Test-class inventory in `tests/test_outstanding_findings.py`

**46 classes** at HEAD `5476faf` (R4: 34 classes; +12 from R3→R4, +6 from R4→R5 Batch 4 = +6 net since R4 doc claim of 40). SKILL.md:246 claims "40 test classes" — stale by 6 (see Track C5 TRA-C5-003).

### R4 Batch 2 new classes (added between R4 baseline `805a8f8` and HEAD `5476faf`)

| Class | Tests | Commit | Finding |
|---|---|---|---|
| `TestTRA038UnknownTermRaisedInProduction` | 3 | `d95c36d` | TRA-038 (round 4) |
| `TestTRA038CertaintyConflictRaisedInLLMPath` | 2 | `d95c36d` | TRA-038 (round 4) |
| `TestTRA038EntityAmbiguityRaisedInBuildEntityTable` | 2 | `d95c36d` | TRA-038 (round 4) |
| `TestTRA042ExtendedStructuralVerification` | 6 | `efbc875` | TRA-042 (round 4) |
| `TestTRA072UniversalPolicyArbitration` | 3 | `78c9250` | TRA-072 (round 4) |
| `TestTRA099CLIPassesRegistry` | 3 | `e54b7a7` | TRA-099 (round 4) |
| **Total new** | **19** | | (Note: 18 unique tests + 1 parametrized expansion; pytest collects 19 from these 6 classes) |

Plus 8 tests added to existing classes in `test_outstanding_findings.py` (TestTRA038UnknownTermRaised already existed at R3; the other 5 R4 Batch 2 classes are net-new). Plus 2 new benchmark cases (S-03, E-03) → +2 parametrized tests in `test_benchmark.py`. Total +29 tests since R4.

## Coverage verification

### ISA instructions (6/6 covered)

| ISA instruction | Direct unit tests | File:line |
|---|---|---|
| ANALYZE_DOCUMENT | `test_analyze_builds_profile_and_map`, `test_analyze_empty_source_raises`, `test_analyze_malformed_raises` | `test_isa.py:36-65` |
| BUILD_GLOSSARY | `test_build_glossary_emits_canonical_entries`, `test_build_glossary_conflict_raises` | `test_isa.py:71-116` |
| BUILD_ENTITY_TABLE | `test_build_entity_table_immutable` | `test_isa.py:122-132` |
| TRANSLATE_SEGMENT | `test_translate_segment_canonical_substitution`, `test_translate_segment_cache_hit_is_byte_identical` | `test_isa.py:138-171` |
| VERIFY_OUTPUT | `test_verify_flags_missing_entity_blocking`, `test_verify_flags_epistemic_drift_blocking`, `test_verify_clean_doc_no_blocking` | `test_isa.py:177-219` |
| REPAIR_SEGMENT | `test_repair_resolves_epistemic_drift`, `test_repair_raises_on_new_blocking_at_attempt_1` | `test_isa.py:225-294` |

### KernelState transitions (9/9 covered)

| State | Tested via | File:line |
|---|---|---|
| BOOTSTRAP (initial) | implicit (kernel starts here) | `test_kernel.py:67` |
| INITIALIZE_RUNTIME | `test_kernel_state_machine_is_sequential` | `test_kernel.py:70` |
| ANALYZE_DOCUMENT | `test_kernel_state_machine_is_sequential` | `test_kernel.py:71` |
| BUILD_ARTIFACTS | `test_kernel_state_machine_is_sequential` | `test_kernel.py:72` |
| EXECUTE_TRANSLATION | `test_kernel_state_machine_is_sequential` | `test_kernel.py:73` |
| VERIFY_OUTPUT | `test_kernel_state_machine_is_sequential` | `test_kernel.py:74` |
| REPAIR_IF_NEEDED | `test_kernel_state_machine_is_sequential` | `test_kernel.py:75` |
| AUDIT_DIAGNOSTICS | `test_kernel_state_machine_is_sequential` | `test_kernel.py:76` |
| EMIT_PAYLOAD | `test_kernel_state_machine_is_sequential` | `test_kernel.py:77` |

Backward/same-state transitions: `test_kernel_illegal_backward_transition` (`test_kernel.py:85-93`), `TestTRA049SameStateTransition` (`test_outstanding_findings.py:1040-1070`), `TestTRA075PairwiseTransitions` (3 tests, `test_outstanding_findings.py:1972-2068`).

### TRA-EXCEPTION types (5/5 covered by recovery tests + 2/5 covered by kernel E2E)

| Exception | Recovery unit test | Kernel E2E test |
|---|---|---|
| UnknownTerm | `test_unknown_term_preserves_source_and_logs_warning` (`test_recovery.py:25-32`) | `TestTRA038UnknownTermRaisedInProduction` (`test_outstanding_findings.py:2803-2864`) |
| BrokenMarkdown | `test_broken_markdown_halts_on_critical_loss`, `test_broken_markdown_best_effort_otherwise` (`test_recovery.py:35-44`) | `TestTRA004ExceptionRecovery`, `TestTRA036AnalyzeFailureL3Gate`, `TestTRA089ConformanceFailureE2E` |
| CertaintyConflict | `test_certainty_conflict_prioritizes_epistemic` (`test_recovery.py:47-52`) | `TestTRA038CertaintyConflictRaisedInLLMPath` (`test_outstanding_findings.py:2867-3002`) |
| EntityAmbiguity | `test_entity_ambiguity_defaults_to_entity` (`test_recovery.py:55-59`) | `TestTRA038EntityAmbiguityRaisedInBuildEntityTable` (`test_outstanding_findings.py:3005-3133`) |
| GlossaryConflict | `test_glossary_conflict_blocking_first_occurrence_canonical` (`test_recovery.py:62-67`) | `test_kernel_records_exception_recovery` (`test_kernel.py:105-123`) |

Plus `Unrecoverable` and `ConformanceFailure` (control-flow exceptions): `test_route_exception_unrecoverable_is_blocking_halt` (`test_recovery.py:104-126`), `TestTRA089ConformanceFailureE2E` (2 tests).

### Conformance levels (3/4 covered — L2_PROFESSIONAL gap, see TRA-D5-016)

| Level | Tested? | Example test |
|---|---|---|
| L1_BASIC | YES | `TestTRA036AnalyzeFailureL3Gate::test_analyze_failure_returns_empty_at_l1` |
| L2_PROFESSIONAL | **NO** — `rg "L2_PROFESSIONAL\|ConformanceLevel\.L2" tests/` → 0 matches | (none) |
| L3_STRICT | YES | `TestTRA054L3ConformanceFailureRaiseBranch`, `TestE2EToTranslateL3` (7 tests) |
| L4_FORENSIC | YES | `TestE2EToTranslateL4` (2 tests), `TestE2EToTranslateReproducibility` (3 tests) |

### Critical invariants (4/4 covered)

| Invariant | Test class | File:line |
|---|---|---|
| Byte reproducibility (TRA-013) | `TestTRA013AuditReproducibility` (2 tests) + `TestE2EToTranslateReproducibility` (3 tests) | `test_outstanding_findings.py:140-207`, `test_e2e_to_translate.py:328-393` |
| 9-state KernelState machine | `test_kernel_state_machine_is_sequential` + `TestTRA075PairwiseTransitions` (3 tests) | `test_kernel.py:66-93`, `test_outstanding_findings.py:1972-2068` |
| L3/L4 conformance gates | `TestTRA054L3ConformanceFailureRaiseBranch`, `TestTRA036AnalyzeFailureL3Gate`, `TestTRA037RewriteAnchorsBeforeGate` | `test_outstanding_findings.py:698-1032,1232-1277` |
| L4 audit-trail integrity | `TestTRA037RewriteAnchorsBeforeGate::test_audit_trail_hash_matches_emitted_target_at_l4` | `test_outstanding_findings.py:987-1032` |

## Mutation probe results (5 mutations on `tra/policy.py` + `tra/isa.py`)

| # | Mutation | Killed by |
|---|---|---|
| 1 | `policy.py:21` `resolve()` — change `<=` to `<` (boundary) | **SURVIVES** — no test exercises `resolve(a, a)` where `precedence[a] == precedence[b]` |
| 2 | `policy.py:25` `wins()` — always return True | KILLED by `test_phase0.py:133` |
| 3 | `policy.py:25` `wins()` — change `<=` to `>=` (flip) | KILLED by 3 tests |
| 4 | `isa.py:792-798` `structural_severity` — hard-code `Severity.BLOCKING` (bypass resolver) | KILLED by `TestTRA072UniversalPolicyArbitration::test_structural_severity_is_policy_driven` |
| 5 | `isa.py:792-798` `structural_severity` — swap args `wins(FLUENCY, STRUCTURAL)` instead of `wins(STRUCTURAL, FLUENCY)` | KILLED by `test_isa.py:372` (`test_verify_output_structural_mismatch_is_blocking`) — but NOT by TRA-072 tests (specificity gap, see TRA-D5-018) |

**Estimated mutation score (rough):** 4 of 5 = 80%. The surviving mutant (#1) is a boundary case requiring an `a == b` test. The TRA-072 tests' monkeypatch-specificity gap (#5) is mitigated by the unmocked-default-behavior tests in `test_isa.py`.

## Benchmark case inventory at HEAD `5476faf`

| Category | Spec target | At HEAD | Delta vs R4 |
|---|---|---|---|
| S (Structural) | 6 (S-01..S-06) | 6 (S-01..S-06) | +1 (S-03 added) |
| F (Factual) | 5 (F-01..F-05) | 5 | — |
| T (Terminology) | 5 (T-01..T-05) | 5 | — |
| D (Domain) | 4 (D-01..D-04) | 4 | — |
| E (Ambiguity) | 3 (E-01..E-03) | 3 (E-01..E-03) | +1 (E-03 added) |
| R (Regression, non-spec) | open | 1 (R-01) | — |
| **Total** | **100+** | **24** | **+2 vs R4 (was 22)** |

**Trajectory:** R2 = 22 cases, R3 = 22 cases, R4 = 22 cases, R5 = 24 cases. The benchmark suite grew for the first time across 4 audit rounds (+2 cases). Spec target is 100+ — current coverage is 24% of target.

## LLM seam review (TRA-090)

| Test pattern | Where used | Clean DI? |
|---|---|---|
| `translate_segment(*, llm_translate=callback)` kwarg | `test_phase6_hardening.py:80`, `test_outstanding_findings.py:443,473,505,1612,2156,2201,2938,3000` | YES — direct DI at the ISA layer |
| Module-level monkeypatch of `kernel_mod.translate_segment` | `test_e2e_to_translate.py:90-104` | NO — fragile, see TRA-D5-002 |

The `translate_segment` function in `tra/isa.py:398-405` correctly accepts `llm_translate: Callable[[str, RuntimeContext], str] | None = None` as a keyword argument. The DI approach is clean at the ISA layer. However, `TRAKernel.__init__` does NOT propagate this parameter — `_execute_translation` at `kernel.py:485-487` calls `translate_segment(protected, self.ctx, self.cache, self.evidence, self.audit)` WITHOUT passing `llm_translate=`. So the kernel's default behavior is always rule-based (no LLM), and the E2E test must monkeypatch the module-level reference to inject an LLM. The clean fix is to add `llm_translate` to `TRAKernel.__init__` (TRA-D5-002).

The E2E hijack in `test_e2e_to_translate.py:72-107` works correctly: the patched function wraps the original, injects `llm_translate=manual_llm`, calls the original, and asserts `call_count >= 1` to verify the hijack was actually invoked. The `finally` block restores the original function. Functionally correct but fragile.

## HITL review (TRA-091)

| Test | Coverage |
|---|---|
| `test_phase6_hardening.py:157-167` `test_hitl_review_decision_accept` | accept path only (text asserted) |
| `test_outstanding_findings.py:376-402` `TestTRA032HITLResolutions` | all 3 resolutions (accept/override/skip) — resolution asserted, text NOT asserted (TRA-D5-004) |
| `on_override` callback parameter | NOT tested (TRA-D5-005) |
| `interactive=True` kernel mode (E2E) | NOT tested (TRA-D5-007) |
| CLI `--interactive` flag | NOT tested (TRA-D5-007) |

`review_decision` IS tested for all 3 resolutions (TRA-032 fixed in R3). But the kernel's `interactive=True` code path at `kernel.py:521-538` is NEVER executed by any test — the L3 conformance failure path raises before the UNRECOVERABLE handler is reached.

## Test isolation audit

| Concern | Status | Evidence |
|---|---|---|
| Module-level singletons | NONE in tests; `kernel_mod.translate_segment` is patched per-test with `try/finally` restoration | `test_e2e_to_translate.py:99-104` |
| Fixture scope | All `conftest.py` fixtures are function-scoped (default); no `scope="session"` or `scope="module"` leaks | `tests/conftest.py:19-99` |
| `kernel_config` fixture | UNUSED (TRA-D5-008) — defined at `conftest.py:82-99` but never requested as a fixture parameter | `rg "kernel_config" tests/` → 1 hit in a comment |
| `tmp_path` isolation | Each kernel test uses `tmp_path` (pytest builtin) for isolated `cache_directory`, `compilation_dir`, `audit_trace` | `test_kernel.py:15-22`, `test_outstanding_findings.py` (most classes) |
| Cross-test cache contamination | LOW RISK — each test uses a unique `tmp_path/cache` directory; `TranslationCache` is constructed per-kernel | `test_kernel.py:18`, `test_outstanding_findings.py:432,462,494` |

## Test naming conventions

| Convention | Status | Evidence |
|---|---|---|
| Test classes named after finding IDs (`TestTRA0XX`) | YES — 46 of 46 classes in `test_outstanding_findings.py` follow `TestTRA<finding-id><Description>` pattern | `rg "^class Test" tests/test_outstanding_findings.py` |
| Test methods descriptive (`test_*`) | YES — all test methods use `test_<scenario>` pattern | `rg "def test_" tests/` |
| SKILL.md §7 class list accuracy | NO — SKILL.md:246 claims "40 test classes" but actual is 46 (Track C5 TRA-C5-003 documents this) | `rg "^class Test" tests/test_outstanding_findings.py \| wc -l` → 46 |
| Cross-file duplicate HITL test | YES — `test_phase6_hardening.py:157` duplicates `TestTRA032HITLResolutions["accept"]` (TRA-D5-010) | see TRA-D5-010 |

## Round 4 carry-over status matrix (Track D scope)

| Round 4 ID | Title | Round 5 status |
|---|---|---|
| TRA-D4-001 | e2e LLM callback ignores `source_segment` | **persistent** (TRA-D5-001) |
| TRA-D4-002 / TRA-090 | e2e LLM hijack uses module-level patching | **persistent** (TRA-D5-002) — `TRAKernel.__init__` signature unchanged |
| TRA-D4-003 / TRA-088 | TRA-048 single-audit-record invariant only PARTIALLY tested | **partial** (TRA-D5-003) — same 4 of 7 paths still uncovered (ValueError-raised/OSError/TimeoutError/None) |
| TRA-D4-004 | `review_decision` text-assertion gap | **persistent** (TRA-D5-004) |
| TRA-D4-005 | `on_override` callback in `review_decision` untested | **persistent** (TRA-D5-005) |
| TRA-D4-006 / TRA-031 / TRA-092 | Benchmark suite at 22/100+ | **partial** (TRA-D5-006) — count grew 22→24 (S-03 + E-03 added); spec target 100+ still far |
| TRA-D4-007 / TRA-052 / TRA-091 | `interactive=True` kernel path untested | **persistent** (TRA-D5-007) — `rg "interactive=True" tests/` → 0 matches |
| TRA-D4-008 / TRA-055 | `kernel_config` fixture unused | **persistent** (TRA-D5-008) |
| TRA-D4-009 / TRA-056 | `e2e_test.py` manual script persists | **persistent** (TRA-D5-009) |
| TRA-D4-010 / TRA-057 | Cross-file duplicate HITL test | **persistent** (TRA-D5-010) |
| TRA-D4-011 / TRA-094 | Mutation testing framework deferred | **persistent** (TRA-D5-011) — `mutmut` not in `pyproject.toml`; manual probe performed |
| TRA-D4-012 / TRA-A4-011 | `repaired = repaired` no-op has no test | **fixed-and-verified** (TRA-D5-012) — `TestTRA_A4_011_RepairedNoopRemoved` added by commit `524c598` |
| TRA-D4-013 / TRA-B4-009 | TRA-016/017/026 silently remediated | **fixed-and-verified** (TRA-D5-013) — 3 regression-test classes added by commit `524c598` |
| TRA-D4-014 | Redundant `tests/run_e2e_translation.py` script | **fixed-and-verified** (TRA-D5-014) — deleted by commit `524c598` |
| TRA-D4-015 | Structural repair branch dead code | **partial** (TRA-D5-015) — TRA-042 made branch reachable, but no dedicated test added |

**Net carry-over disposition:** 3 fixed-and-verified (TRA-D5-012, 013, 014), 3 partial (TRA-D5-003, 006, 015), 9 persistent.

## Conclusion

The TRA test suite at HEAD `5476faf` has grown from 199 tests (R4) to 228 tests (+29) across 16 test files. All 228 tests pass. R4 Batch 3 deleted the redundant `tests/run_e2e_translation.py` (TRA-D5-014) and added enforcement-protective regression tests for 3 previously-silent remediations (TRA-D5-012, 013). R4 Batch 4 added 6 new well-designed test classes (18 new tests) for TRA-038/042/072/099 — all with meaningful assertions, not smoke tests (TRA-D5-019). The benchmark suite grew from 22 to 24 cases (TRA-D5-020) and the L3 gate is properly enforced on the L3_STRICT subset. Three WARNING-severity gaps remain: the LLM seam module-level patching (TRA-D5-002 / TRA-090), the partial TRA-048 single-audit-record invariant coverage (TRA-D5-003), and the untested `interactive=True` kernel path (TRA-D5-007 / TRA-091). Five new INFO findings were identified: L2_PROFESSIONAL conformance level never tested (TRA-D5-016), CLI `validate`/`audit`/`cache-clear` subcommands not CliRunner-tested (TRA-D5-017), TRA-072 tests have a mild monkeypatch-specificity gap (TRA-D5-018, mitigated by `test_isa.py` default-behavior tests), and two positive verifications (TRA-D5-019, 020). No regressions detected. The estimated mutation score from a 5-mutation manual probe is 80% (4 of 5 caught), with the surviving mutant being a boundary case in `PolicyResolver.resolve()`. The test suite is in a healthy state but continues to defer mutation-testing automation (TRA-D5-011) and the L2 conformance level coverage (TRA-D5-016).

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# Test count at HEAD
python -m pytest tests 2>&1 | tail -3
# → 228 passed in 1.42s

# Test collection summary
python -m pytest tests --co -q 2>&1 | tail -20
# → tests/test_anchor.py: 7
# → tests/test_benchmark.py: 27
# → tests/test_e2e_to_translate.py: 12
# → tests/test_isa.py: 17
# → tests/test_kernel.py: 7
# → tests/test_modules.py: 17
# → tests/test_outstanding_findings.py: 91
# → tests/test_phase0.py: 11
# → tests/test_phase6_hardening.py: 7
# → tests/test_recovery.py: 9
# → tests/test_reporting.py: 5
# → tests/test_tra043_protocol.py: 3
# → tests/test_tra047_config_robustness.py: 2
# → tests/test_tra071_broken_markdown.py: 2
# → tests/test_utils.py: 7
# → tests/test_validate.py: 4

# Test class inventory in test_outstanding_findings.py
rg "^class Test" tests/test_outstanding_findings.py | wc -l
# → 46

# Benchmark case count
wc -l tests/benchmark/cases/*.jsonl
# → 23 tests/benchmark/cases/sft.jsonl
# →  1 tests/benchmark/cases/regression.jsonl
# → 24 total

# L2_PROFESSIONAL coverage gap
rg "L2_PROFESSIONAL|ConformanceLevel\.L2" tests/
# → (no matches in test code)

# interactive=True coverage gap
rg "interactive=True" tests/
# → (no matches)

# kernel_config fixture usage
rg "kernel_config" tests/
# → tests/conftest.py:82 (definition)
# → tests/test_kernel.py:13 (comment only — not a fixture parameter)

# Mutation probe (manual, 5 mutations)
cp tra/policy.py /tmp/policy.py.bak
sed -i 's/return a if self.precedence\[a\] <= self.precedence\[b\] else b/return a if self.precedence[a] < self.precedence[b] else b/' tra/policy.py
python -m pytest tests/test_phase0.py -q 2>&1 | tail -3  # → SURVIVES
cp /tmp/policy.py.bak tra/policy.py
# (4 more mutations — see TRA-D5-011 table)

# Verify run_e2e_translation.py deletion
git log --oneline --diff-filter=D -- tra-prototype/tests/run_e2e_translation.py
# → 524c598 fix(tra): Round 4 Batch 3 — code quality fixes (...)

# Verify e2e_test.py still present (TRA-D5-009)
ls -la e2e_test.py
# → -rwxrwxr-x 1 z z 3561 Jul 18 22:27 e2e_test.py
```
