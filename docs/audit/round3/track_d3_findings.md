# Track D3 — Test Suite Re-Audit (Round 3)

**HEAD audited:** `b783745`
**Methodology:** coverage + 6 mutations + benchmark count + HITL/LLM/e2e audit
**Baseline:** Round 2 Track D (13 findings, HEAD `4b8827c`)
**Auditor:** Track D3 agent (general-purpose)
**Audit date:** 2026-07-15

## Summary

- **Findings:** 11 total (0 BLOCKING / 6 WARNING / 5 INFO)
- **Test count:** 174 (actual, matches Round 2 baseline of 141 + 12 new e2e + 21 from new TDD regression tests)
- **Test files:** 16 `test_*.py` files + 1 `conftest.py` = 17 .py files in `tests/`
- **Coverage:** 96% overall (1434 stmts, 58 missed)
- **Mutation catch rate:** 6/6 (100%) — up from 11/13 in Round 2
- **Benchmark cases:** 22 / 100+ spec target (22%, persistent scope gap)
- **Carry-over:** 5 findings carried forward (TRA-031/052/055/056/057)
- **New:** 6 findings (D3-001 through D3-006)

All four quality gates remain green at HEAD `b783745`:
`ruff format --check` ✓ · `ruff check` ✓ · `mypy --strict tra` ✓ · `pytest` (174 passed) ✓

## Test count and structure

`pytest --collect-only` reports **174 tests collected** across **16 test files** + 1 conftest.py.

| Test file | Tests | Status | Notes |
|---|---|---|---|
| tests/test_anchor.py | 7 | passing | — |
| tests/test_benchmark.py | 25 | passing | 22 parametrized benchmark cases + L3 gate + reproducibility |
| tests/test_e2e_to_translate.py | 12 | passing | **NEW** (commit `354fa94`) — full pipeline e2e on to_translate.md |
| tests/test_isa.py | 17 | passing | TRA-028/029/030 regression tests |
| tests/test_kernel.py | 7 | passing | — |
| tests/test_modules.py | 17 | passing | — |
| tests/test_outstanding_findings.py | 39 | passing | 14 `TestTRA0XX` classes (was 11 / 26 tests in Round 2) |
| tests/test_phase0.py | 11 | passing | — |
| tests/test_phase6_hardening.py | 7 | passing | includes TRA-048 single-audit-record assertion |
| tests/test_recovery.py | 9 | passing | +1 test vs Round 2 (8 → 9), includes TRA-044 unrecoverable halt |
| tests/test_reporting.py | 5 | passing | — |
| tests/test_tra043_protocol.py | 3 | passing | NEW — extracted TRA-043 regression tests |
| tests/test_tra047_config_robustness.py | 2 | passing | NEW — extracted TRA-047 regression tests |
| tests/test_tra071_broken_markdown.py | 2 | passing | NEW — extracted TRA-071 regression tests |
| tests/test_utils.py | 7 | passing | TRA-010 mutable=False assertion here |
| tests/test_validate.py | 4 | passing | — |
| tests/conftest.py | (fixtures) | — | 7 fixtures defined; 1 unused (TRA-055 persists) |
| **Total** | **174** | **all passing in 0.95s** | +33 tests vs Round 2 (141 → 174) |

## Coverage analysis

`pytest --cov=tra --cov-report=term-missing tests` → **96% overall** (1434 statements, 58 missed).

| Module | Stmts | Miss | Cover | Notable missing lines |
|---|---|---|---|---|
| tra/__init__.py | 1 | 0 | 100% | — |
| tra/anchor.py | 245 | 20 | 92% | 195, 213-214, 250, 271-278, 301, 304-307, 330, 333-336, 353 |
| tra/benchmark.py | 70 | 6 | 91% | 93, 96, 109-113 (S-03/E-03 unimplemented) |
| tra/cache.py | 64 | 1 | 98% | 125 |
| tra/config.py | 38 | 0 | 100% | — |
| tra/diagnostics.py | 90 | 2 | 98% | 198, 208 (count_blocking stub — TRA-016/066) |
| tra/exceptions.py | 41 | 0 | 100% | — |
| tra/hitl.py | 31 | 1 | 97% | 57 (`on_override` callback path) |
| tra/isa.py | 213 | 12 | 94% | 89, 102-103, 194, 242-243, 322, 492, 571, 653-656 |
| tra/kernel.py | 228 | 12 | 95% | 121, 145, 175, 241, 243, 335, **478-490 (interactive=True path — TRA-052)**, 553 |
| tra/memory.py | 114 | 0 | 100% | — |
| tra/modules/registry.py | 42 | 3 | 93% | 60, 66-67 |
| tra/policy.py | 9 | 0 | 100% | — |
| tra/recovery.py | 51 | 1 | 98% | 191 |
| tra/reporting.py | 40 | 0 | 100% | — |
| tra/utils.py | 37 | 0 | 100% | — |
| tra/validate.py | 35 | 0 | 100% | — |
| **TOTAL** | **1434** | **58** | **96%** | — |

**Coverage gaps that map to findings:**
- `kernel.py:478-490` (interactive=True HITL handoff) — **TRA-052 confirmed via coverage** (carry-over)
- `hitl.py:57` (`on_override` callback path) — exercised only via unit tests of `review_decision` accept/override/skip, but the `on_override` callable branch is never invoked end-to-end
- `diagnostics.py:198,208` — `count_blocking` stub still returning 0 (TRA-016/066, cross-track finding)

## Mutation results

All 6 spec-mandated mutations executed against live source at HEAD `b783745`. Each mutation was applied via `Edit`, validated by `pytest tests -q`, then reverted via `git checkout`. Mutation **caught** = tests fail. Mutation **NOT caught** = tests still pass (a finding).

| # | Mutation | Caught? | Test(s) that caught it | Notes |
|---|---|---|---|---|
| 1 | `memory.py` `mutable: bool = False` → `True` | **YES** | `tests/test_utils.py::test_version_token_classified` | Direct assertion `assert v.mutable is False` (line 13). Strong catch. |
| 2 | `isa.py` canonical-term leakage `Severity.BLOCKING` → `Severity.WARNING` | **YES** | `test_isa.py::test_verify_output_terminology_canonical_is_blocking` + `TestTRA009PolicyDrivenSeverity::test_canonical_term_leakage_is_blocking` + `TestTRA001SegmentLevel::test_code_block_not_translated` + `TestTRA006PolicyResolverInvokedInProduction::test_monkeypatching_resolver_changes_terminology_severity` | 4 tests fail — strong catch. |
| 3 | `kernel.py` `idx <= _KERNEL_ORDER.index(self.state)` → `idx <` (TRA-049 regression) | **YES** | `TestTRA049SameStateTransition::test_same_state_transition_raises` | Direct catch. |
| 4 | `recovery.py` `isinstance(exc, Unrecoverable)` branch commented out (TRA-044 regression) | **YES** | `test_recovery.py::test_route_exception_unrecoverable_is_blocking_halt` | Direct catch — confirms TRA-044 fix holds. |
| 5 | `isa.py` early `return result` in LLM degradation path removed (TRA-048 regression) | **YES** | `test_phase6_hardening.py::test_graceful_degradation_on_llm_failure` | `assert len(translate_records) == 1` fails with 2 records. **However**, only the RuntimeError path is asserted — see D3-004. |
| 6 | `kernel.py` L3+ conformance gate `if self.config.conformance_level in (L3_STRICT, L4_FORENSIC)` → `if False` (TRA-005/036/054 regression) | **YES** | `TestTRA054L3ConformanceFailureRaiseBranch::test_l3_gate_raises_conformance_failure_on_blocking` + `TestTRA037RewriteAnchorsBeforeGate::test_broken_internal_link_raises_conformance_failure_at_l3` + `test_e2e_to_translate.py::TestE2EToTranslateL3::test_audit_trail_has_canonical_isa_sequence` | 3 tests fail — strong catch. The new e2e test catches the mutation via the missing second VERIFY_OUTPUT record (audit trail sequence mismatch). |

**Mutation catch rate: 6/6 (100%).** This is a significant improvement over Round 2 (11/13 = 85%) — the two mutations that escaped detection in Round 2 (the `<` vs `<=` transition and the early-return-on-degradation) are now caught by dedicated regression tests added in commits between `4b8827c` and `b783745`.

## Benchmark coverage

`tests/benchmark/cases/sft.jsonl` contains 21 cases; `tests/benchmark/cases/regression.jsonl` contains 1 case (R-01). **Total: 22 benchmark cases.**

| Spec category | Spec cases | Implemented | Missing |
|---|---|---|---|
| S (Structural) | S-01..S-06 (6) | 5 (S-01, S-02, S-04, S-05, S-06) | **S-03** (inline code vs prose) |
| F (Factual) | F-01..F-05 (5) | 5/5 | — |
| T (Terminology) | T-01..T-05 (5) | 5/5 | — |
| D (Domain) | D-01..D-04 (4) | 4/4 | — |
| E (Ambiguity) | E-01..E-03 (3) | 2 (E-01, E-02) | **E-03** (broken source markdown) |
| R (Regression, non-spec) | — | 1 (R-01) | — |
| **Total** | **23 spec cases** | **21 spec (91%)** | **2 missing** |

Spec target per `TRA-BENCHMARK-SUITE.md` L5: "intended to grow toward 100+ cases". Currently at **22/100+ (22%)** — a known scope gap, persistent across rounds (TRA-031 / TRA-058 / CLAUDE.md acknowledgement).

## HITL coverage (TRA-032 / TRA-052 / TRA-048)

### TRA-032 — `review_decision` three resolutions
`tests/test_outstanding_findings.py::TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution` is parametrized over `["accept", "override", "skip"]`. All three branches fire. The test asserts `result_res == resolution` only — it does **not** assert the returned `text` matches the expected candidate/edited text. This is the same weakness flagged in Round 2 (TRA-D2-009) but no follow-up finding raised here since the test does technically exercise all three branches.

A second, partial duplicate exists in `tests/test_phase6_hardening.py::test_hitl_review_decision_accept` (lines 157-167). It tests only the `accept` path but **does** assert `text == "candidate"` — stronger text assertion. Together the two tests cover accept/override/skip resolution strings + accept text, but override/skip text assertions are missing. (See D3-005.)

### TRA-052 — `interactive=True` kernel path
**Still untested.** Grep across `tests/` for `interactive=True`, `interactive = True`, `TRAKernel(...interactive...)` returns **zero matches**. The coverage report confirms `kernel.py:478-490` (the entire `if self.interactive:` block — HITL handoff with `format_unrecoverable` + `review_decision`) is **never executed**. The L3 conformance failure path raises before the UNRECOVERABLE handler is reached, so even the e2e tests don't trigger this branch.

### TRA-048 — single audit record on degradation
`tests/test_phase6_hardening.py::test_graceful_degradation_on_llm_failure` (lines 71-99) asserts `len(translate_records) == 1` for the **RuntimeError** exception path. The other 4 exception types + empty-string + None paths in `TestTRA033LLMSeamRobustness` only assert `"Confirmed" in res.translation` — they do NOT verify the single-audit-record invariant. **Mutation #5 was caught, but only via the RuntimeError path.** (See D3-004.)

### `tra/hitl.py::review_decision` — `on_override` callback coverage
The `on_override` callback parameter (line 30) is a callable that lets the caller re-run translation on the override text. **The callback is never exercised** — both `TestTRA032HITLResolutions` and `test_hitl_review_decision_accept` call `review_decision` without passing `on_override`. Coverage report confirms `hitl.py:57` (`return "override", on_override(source_context, edited)`) is missed. (See D3-006.)

## LLM seam coverage (TRA-033 / TRA-048)

`tests/test_outstanding_findings.py::TestTRA033LLMSeamRobustness` (7 tests):

| Test | What it covers | What it asserts |
|---|---|---|
| `test_llm_seam_degrades_on_each_exception_type` (parametrized × 5) | RuntimeError, ValueError, TypeError, OSError, TimeoutError | `"Confirmed" in res.translation` only |
| `test_llm_seam_degrades_on_empty_string` | Empty string `""` return | `"Confirmed" in res.translation` only |
| `test_llm_seam_degrades_on_none` | `None` return | `"Confirmed" in res.translation` only |

**LLM seam cases covered:**

| Case | Covered? | Test |
|---|---|---|
| (a) Empty string response | YES | `test_llm_seam_degrades_on_empty_string` |
| (b) None response | YES | `test_llm_seam_degrades_on_none` |
| (c) Exception | YES (5 types) | `test_llm_seam_degrades_on_each_exception_type` |
| (d) Malformed JSON | **NO** | No test passes a non-JSON / malformed-JSON string to `llm_translate`. The kernel does not parse LLM responses as JSON, so this is a lower-priority gap, but a string like `"{not json"` would be silently adopted as the translation. |
| (e) Valid response | YES | `tests/test_e2e_to_translate.py::TestE2EToTranslateL3::test_pipeline_completes_and_output_matches_manual_translation` |

**TRA-048 invariant ("exactly one TRANSLATE_SEGMENT audit record on degradation"):** Only the **RuntimeError** path asserts this. The empty/None/ValueError/TypeError/OSError/TimeoutError paths do NOT. If someone makes the early `return result` conditional on exception type, only the RuntimeError path would catch the regression. (See D3-004.)

## NEW: e2e test quality audit (commit `354fa94`)

`tests/test_e2e_to_translate.py` (394 LOC, 12 tests across 3 classes) was added in commit `354fa94` ("test(e2e): add pytest-collected E2E test on to_translate.md with manual LLM hijack"). The commit message states this closes TRA-D2-015 (the existing `e2e_test.py` is a manual script not collected by pytest).

### LLM hijack mechanism

The kernel calls `translate_segment(protected, self.ctx, self.cache, self.evidence, self.audit)` at `kernel.py:440` **without** passing `llm_translate`. To inject an LLM, the test patches the module-level reference:

```python
import tra.kernel as kernel_mod
orig_translate = kernel_mod.translate_segment
def patched_translate(source_segment, ctx, cache, evidence, audit, **kwargs):
    kwargs["llm_translate"] = manual_llm
    return orig_translate(source_segment, ctx, cache, evidence, audit, **kwargs)
kernel_mod.translate_segment = patched_translate
```

This works but is **brittle** — it mutates module state, relies on the kernel's `from .isa import translate_segment` binding, and must be restored in a `finally` block. A cleaner design would be for `TRAKernel.__init__` or `run()` to accept an optional `llm_translate` callable. (See D3-002.)

### Per-test analysis

| # | Test | Asserts | Real / Smoke | LLM seam | L3/L4/Repro |
|---|---|---|---|---|---|
| 1 | `test_pipeline_completes_and_output_matches_manual_translation` | `target == manual` (byte-identical) | **Real** (strong equality) | ✓ | L3 |
| 2 | `test_audit_trail_has_canonical_isa_sequence` | `isa_sequence == [ANALYZE_DOCUMENT, BUILD_GLOSSARY, BUILD_ENTITY_TABLE, TRANSLATE_SEGMENT, VERIFY_OUTPUT, VERIFY_OUTPUT]` | **Real** (exact list equality) | ✓ | L3 |
| 3 | `test_zero_blocking_diagnostics_at_l3` | `blocking == 0` after pipeline runs | **Real** | ✓ | L3 |
| 4 | `test_all_runtime_artifacts_written_at_l3` | 7 files exist (glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml, execution_log.json, repair_history.jsonl, audit_trace.jsonl) | **Smoke** (file-existence only, no content check) | ✓ | L3 |
| 5 | `test_glossary_contains_canonical_mappings` | `"成立" in sources` | **Real** (content check) | ✓ | L3 |
| 6 | `test_entity_table_preserves_entities` | `L1, L2, L3, L4, ISA, TRA in names` | **Real** (content check) | ✓ | L3 |
| 7 | `test_execution_log_matches_kernel_state_order` | `execution_log == [INITIALIZE_RUNTIME, ANALYZE_DOCUMENT, BUILD_ARTIFACTS, EXECUTE_TRANSLATION, VERIFY_OUTPUT, REPAIR_IF_NEEDED, AUDIT_DIAGNOSTICS, EMIT_PAYLOAD]` | **Real** (exact list equality) | ✓ | L3 |
| 8 | `test_l4_emits_forensic_artifacts` | `evidence_trace.jsonl` + `ambiguity_register.json` exist | **Smoke** (file-existence only) | ✓ | L4 |
| 9 | `test_evidence_trace_has_one_entry_per_output_line` | Each trace entry has `line`, `text`, `evidence_ids`, `attributed` fields; ≥1 attributed | **Real** (schema + non-empty check) | ✓ | L4 |
| 10 | `test_two_runs_produce_byte_identical_audit_trace` | `sha256(audit1) == sha256(audit2)` | **Real** (byte-identical SHA) | ✓ | Repro (L4) |
| 11 | `test_two_runs_produce_byte_identical_evidence_trace` | `sha256(trace1) == sha256(trace2)` | **Real** (byte-identical SHA) | ✓ | Repro (L4) |
| 12 | `test_two_runs_produce_byte_identical_output` | `t1 == t2` | **Real** (string equality) | ✓ | Repro (L4) |

**Verdict:** All 12 tests have real assertions (not pure smoke). 2 tests (#4, #8) are file-existence-only smokes. LLM hijack seam is correctly exercised in all 12 — the `assert call_count >= 1` guard in `_run_kernel_with_manual_llm` ensures the callback is actually invoked. L3, L4, and byte-reproducibility are all covered.

### e2e test gaps

1. **No ConformanceFailure path is exercised.** All 12 tests run on `to_translate.md` with the manual translation that already passes L3+ verification. There is no e2e test that forces an L3+ violation (e.g. an LLM that returns text missing a required entity) to verify the kernel raises `ConformanceFailure`. (See D3-003.)
2. **The LLM callback ignores `source_segment`.** `manual_llm(source_segment, ctx)` returns the **entire** `manual_translation` for **every** segment, regardless of which segment is being translated. The kernel only translates one segment (the whole document), so this happens to work — but it masks any per-segment routing logic. A more realistic test would segment-correlate source↔target. (See D3-001.)
3. **Module-level patching is fragile.** See LLM hijack mechanism above (D3-002).
4. **`tests/test_e2e_to_translate.py` and `e2e_test.py` overlap fully.** The new pytest module makes the manual script obsolete — `e2e_test.py` should be deleted. (See TRA-056 carry-over.)

## Test hygiene

### conftest.py fixtures (TRA-034 / TRA-055)
7 fixtures defined. Usage audit:

| Fixture | Used in | Status |
|---|---|---|
| `sample_glossary` | conftest (by `cache_context`) | Used internally |
| `sample_entities` | conftest (by `cache_context`) | Used internally |
| `cache_context` | `test_phase0.py::test_cache_key_is_deterministic_and_order_independent`, `test_cache_key_changes_with_model_or_policy` | Used |
| `evidence_registry` | `test_phase0.py::test_evidence_registry_append_only` | Used |
| `sample_evidence` | `test_phase0.py::test_evidence_registry_append_only` | Used |
| `config` | `test_phase0.py::test_config_loads` | Used |
| `kernel_config` | **NOWHERE** | **UNUSED** |

**TRA-055 confirmed via grep:** zero matches for `kernel_config` as a fixture parameter in any `test_*.py` file. `test_kernel.py` line 13 contains a comment "Uses the shared kernel_config fixture pattern (TRA-034)" but then defines its own `_kernel(tmp_path)` helper that duplicates the boilerplate. The Round 2 fix for TRA-034 (add the fixture) was merged but the fixture was never wired into tests.

### `e2e_test.py` (TRA-056)
Still present at `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/e2e_test.py` (104 LOC). It's a manual script with no `test_*` functions, no `assert` statements — just `print()` output. NOT pytest-collectible. The new `tests/test_e2e_to_translate.py` (12 tests) makes this script redundant but the script was not deleted.

### `tests/test_phase6_hardening.py` (TRA-057)
7 tests, no duplicates within the file. **One cross-file duplicate:**
- `test_hitl_review_decision_accept` (lines 157-167) duplicates `TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution` parametrized case `resolution="accept"`. Same intent, slightly different monkeypatch signature (`staticmethod(fake_ask)` vs `monkeypatch.setattr("tra.hitl.Prompt.ask", _fake_ask)`). The phase6 version asserts the returned `text`; the parametrized version does not. (See D3-005.)

### Skipped / xfail tests
Grep for `pytest.mark.skip`, `pytest.mark.xfail`, `@skip`, `skipTest` across `tests/` returns **zero matches**. No tests are skipped or marked xfail.

## Findings

### D3-001 — e2e LLM callback ignores `source_segment` (INFO)

**Severity:** INFO
**File:** `tests/test_e2e_to_translate.py:83-86`
**Carry-over:** New in Round 3 (introduced by commit `354fa94`).

```python
def manual_llm(source_segment: str, ctx: object) -> str:
    nonlocal call_count
    call_count += 1
    return manual_translation  # ← returns the WHOLE manual translation regardless of segment
```

The LLM callback discards `source_segment` and returns the entire `manual_translation` for every call. This works because the kernel currently translates one segment (the whole document) per `run()`, but it means the e2e test cannot detect per-segment routing bugs (e.g. if the kernel called `llm_translate` twice with different segments and concatenated the results, the test would still pass).

**Recommendation:** Either (a) document the single-segment assumption explicitly in the test docstring, or (b) when the kernel supports multi-segment translation, segment-correlate source↔target in the callback.

### D3-002 — e2e LLM hijack uses module-level patching (WARNING)

**Severity:** WARNING
**File:** `tests/test_e2e_to_translate.py:90-104`

```python
import tra.kernel as kernel_mod
orig_translate = kernel_mod.translate_segment
def patched_translate(source_segment, ctx, cache, evidence, audit, **kwargs):
    kwargs["llm_translate"] = manual_llm
    return orig_translate(source_segment, ctx, cache, evidence, audit, **kwargs)
kernel_mod.translate_segment = patched_translate
try:
    kernel = TRAKernel(cfg)
    target = kernel.run(source)
finally:
    kernel_mod.translate_segment = orig_translate
```

The kernel calls `translate_segment(...)` at `kernel.py:440` without an `llm_translate` parameter. To inject an LLM, the test mutates `kernel_mod.translate_segment` at module scope. This is fragile: a parallel test run could see the patched function, and the restoration relies on `finally` running cleanly. A cleaner design would be for `TRAKernel.__init__` or `run()` to accept an optional `llm_translate: Callable | None = None` that is threaded through to `translate_segment`.

**Recommendation:** Add an `llm_translate` parameter to `TRAKernel.run()` (or `__init__`), defaulting to `None`. Update `_execute_translation` to pass it through. This eliminates the need for module-level patching in all 12 e2e tests.

### D3-003 — No e2e test for ConformanceFailure path (WARNING)

**Severity:** WARNING
**File:** `tests/test_e2e_to_translate.py` (whole file)

All 12 e2e tests run on `to_translate.md` paired with the **passing** manual translation. No e2e test forces an L3+ violation (e.g. LLM returns text missing a required entity, breaking the structural heading count, or leaking a forbidden target) to verify the kernel raises `ConformanceFailure` end-to-end.

The unit-level coverage of the L3+ raise branch is provided by `TestTRA054L3ConformanceFailureRaiseBranch` and `TestTRA037RewriteAnchorsBeforeGate`, but those use synthetic inputs — not the real `to_translate.md` pipeline.

**Recommendation:** Add `TestE2EConformanceFailure` with 2-3 tests that run the e2e pipeline with a deliberately-broken LLM (e.g. returns text with a leaked canonical term, missing entity, broken heading count) and assert `ConformanceFailure` is raised with the expected diagnostic count.

### D3-004 — TRA-048 single-audit-record invariant only tested for RuntimeError (WARNING)

**Severity:** WARNING
**File:** `tests/test_outstanding_findings.py:410-507` (TestTRA033LLMSeamRobustness)

`TestTRA033LLMSeamRobustness` has 7 tests (5 exception types + empty + None). Each asserts only `"Confirmed" in res.translation` — none asserts the single-`TRANSLATE_SEGMENT`-audit-record invariant (TRA-048). The invariant is asserted only in `test_phase6_hardening.py::test_graceful_degradation_on_llm_failure` for the **RuntimeError** path.

If a future mutation makes the early `return result` conditional on `isinstance(exc, RuntimeError)`, the empty/None/ValueError/TypeError/OSError/TimeoutError paths would emit a second (non-degraded) audit record — and **no test would catch this**. Mutation #5 was caught because the existing test happens to use RuntimeError.

**Recommendation:** Add `assert len(translate_records) == 1` (where `translate_records = [r for r in audit._buffer if r.isa_instruction == "TRANSLATE_SEGMENT"]`) to each of the 7 tests in `TestTRA033LLMSeamRobustness`. Alternatively, factor the assertion into a shared helper.

### D3-005 — `review_decision` text-assertion gap (INFO)

**Severity:** INFO
**Files:** `tests/test_outstanding_findings.py:371-402`, `tests/test_phase6_hardening.py:157-167`

`TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution` is parametrized over `["accept", "override", "skip"]` but only asserts `result_res == resolution` — not the returned `text`. The phase6 duplicate `test_hitl_review_decision_accept` asserts `text == "candidate"` but only for the `accept` path. Together:

| Resolution | Resolution asserted? | Text asserted? |
|---|---|---|
| accept | YES (both tests) | YES (phase6 only) |
| override | YES | **NO** — does not assert `text == "edited text"` |
| skip | YES | **NO** — does not assert `text == candidate` (the skip contract) |

Per `tra/hitl.py:34-36`, the contract is: "text is the adopted target text (unchanged candidate for accept/skip; reviewer-supplied for override)". The override and skip text contracts are untested.

**Recommendation:** Extend the parametrized test to assert `result_text == expected_text` where `expected_text = {"accept": candidate, "override": "edited text", "skip": candidate}[resolution]`.

### D3-006 — `on_override` callback in `review_decision` untested (INFO)

**Severity:** INFO
**File:** `tra/hitl.py:30, 56-57`, `tests/test_outstanding_findings.py:371-402`, `tests/test_phase6_hardening.py:157-167`

`review_decision` accepts an optional `on_override: Callable[[str, str], str] | None = None` parameter. When provided and the user chooses "override", the callback is invoked as `on_override(source_context, edited)` and its return value is used as the override text. The coverage report confirms `hitl.py:57` (`return "override", on_override(source_context, edited)`) is **never executed** — no test passes `on_override`.

**Recommendation:** Add a test that passes a stub `on_override` and asserts it is invoked with `(source_context, edited_text)` and its return value is used as the override text.

### Carry-over: TRA-031 — Benchmark suite at 22/100+ spec target (WARNING)

**Severity:** WARNING (carry-over from Round 1 → Round 2 → Round 3)
**Status:** Persistent scope gap.
**File:** `tests/benchmark/cases/sft.jsonl`, `tests/benchmark/cases/regression.jsonl`

22 benchmark cases implemented; spec target is 100+. 2 of 23 spec cases missing (S-03 inline-code-vs-prose, E-03 broken-source-markdown). Acknowledged in CLAUDE.md "Known gaps" section. Not a regression — same count as Round 2.

### Carry-over: TRA-052 — `interactive=True` kernel path untested (WARNING)

**Severity:** WARNING (carry-over from Round 2)
**Status:** Persistent. Coverage report confirms `kernel.py:478-490` (the entire `if self.interactive:` block) is missed. Zero grep matches for `interactive=True` across `tests/`.

The new e2e tests do NOT exercise this path — they run the pipeline with `interactive=False` (the default). Even if an UNRECOVERABLE were raised, the e2e tests don't trigger one (no ConformanceFailure path → see D3-003).

**Recommendation:** Add a test that constructs `TRAKernel(cfg, interactive=True)`, monkeypatches `tra.hitl.review_decision` to return `("accept", candidate)`, feeds input that triggers an UNRECOVERABLE, and asserts the audit trail contains `HITL[accept]: ...` in `unresolved_ambiguities`.

### Carry-over: TRA-055 — `kernel_config` fixture unused (WARNING)

**Severity:** WARNING (carry-over from Round 2)
**Status:** Persistent. `conftest.py:82-99` defines `kernel_config(tmp_path) -> BootstrapConfig`. Grep across `tests/` for `kernel_config` as a fixture parameter returns **zero matches**. `test_kernel.py:13` has a comment "Uses the shared kernel_config fixture pattern (TRA-034)" but then defines its own `_kernel(tmp_path)` helper (lines 12-23) that duplicates the exact boilerplate the fixture was meant to eliminate.

**Recommendation:** Either (a) replace `_kernel()` in `test_kernel.py` with the `kernel_config` fixture, or (b) delete the unused fixture and the misleading comment.

### Carry-over: TRA-056 — `e2e_test.py` manual script persists (INFO)

**Severity:** INFO (carry-over from Round 2, **partially mitigated**)
**Status:** The manual script `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/e2e_test.py` (104 LOC) is still present and not pytest-collectible. **However**, commit `354fa94` added `tests/test_e2e_to_translate.py` (12 proper pytest tests) that fully supersede the manual script's coverage. The manual script is now dead code.

**Recommendation:** Delete `e2e_test.py`. Update CLAUDE.md / SKILL.md if either references it.

### Carry-over: TRA-057 — Cross-file duplicate test (INFO)

**Severity:** INFO (carry-over from Round 2, refined)
**Status:** Round 2 reported "no duplicates within test_phase6_hardening.py" — confirmed. Round 3 finds **one cross-file duplicate**:

- `test_phase6_hardening.py::test_hitl_review_decision_accept` (lines 157-167)
- vs `test_outstanding_findings.py::TestTRA032HITLResolutions["accept"]` (parametrized)

Both test the same `review_decision("amb", "src", "candidate")` → `"accept"` path with the same monkeypatch strategy. The phase6 version additionally asserts `text == "candidate"`.

**Recommendation:** Delete `test_hitl_review_decision_accept` from `test_phase6_hardening.py` after extending the parametrized `TestTRA032HITLResolutions` test to assert the text (D3-005 fix). This consolidates HITL coverage in one place.

## Comparison to Round 2 Track D baseline

| Round 2 finding | Round 3 status | Notes |
|---|---|---|
| TRA-D2-001 (test count mismatch) | RESOLVED | 174 tests actually collected, matches all doc claims |
| TRA-D2-002 (coverage gap in `kernel.py` interactive path) | PERSISTS as TRA-052 | Same lines (478-490) still missed |
| TRA-D2-003 (mutation testing deferred) | RESOLVED | 6/6 mutations caught in Round 3 |
| TRA-D2-004 (benchmark suite at 22/100+) | PERSISTS as TRA-031 | Same 22 cases |
| TRA-D2-005 (S-03 spec case missing) | PERSISTS | Same gap |
| TRA-D2-006 (E-03 spec case missing) | PERSISTS | Same gap |
| TRA-D2-007 (HITL test weak text assertion) | PERSISTS as D3-005 | Same weakness, refined |
| TRA-D2-008 (interactive=True untested) | PERSISTS as TRA-052 | Same gap |
| TRA-D2-009 (review_decision override text untested) | PERSISTS as D3-005 | Same gap |
| TRA-D2-010 (LLM seam malformed-JSON untested) | NEW as D3-006 (refined to on_override) | The malformed-JSON gap was noted but not raised; on_override is a sharper gap |
| TRA-D2-011 (conftest kernel_config unused) | PERSISTS as TRA-055 | Same gap |
| TRA-D2-012 (test_phase6_hardening duplicates) | REFINED as D3-005 / TRA-057 | Cross-file duplicate identified |
| TRA-D2-013 (e2e_test.py manual script) | PARTIALLY MITIGATED as TRA-056 | New pytest module added; manual script not deleted |

## Remediation priority

| Priority | Finding | Effort |
|---|---|---|
| P1 (high) | D3-002 — Add `llm_translate` parameter to `TRAKernel.run()` | Small — 1 signature change + thread-through in `_execute_translation` |
| P1 (high) | D3-003 — Add e2e ConformanceFailure tests | Small — 2-3 tests in a new `TestE2EConformanceFailure` class |
| P2 (medium) | D3-004 — Add single-audit-record assertion to all 7 LLM-seam tests | Trivial — add 2 lines per test |
| P2 (medium) | TRA-052 — Add `interactive=True` kernel test | Small — 1 test with monkeypatched `review_decision` |
| P3 (low) | D3-001 — Document single-segment assumption in e2e test | Trivial — docstring update |
| P3 (low) | D3-005 — Extend HITL parametrization with text assertion | Trivial — 2 lines |
| P3 (low) | D3-006 — Add `on_override` callback test | Trivial — 1 test |
| P3 (low) | TRA-055 — Wire `kernel_config` fixture into `test_kernel.py` | Trivial — replace `_kernel()` helper |
| P3 (low) | TRA-056 — Delete `e2e_test.py` | Trivial — `git rm` |
| P3 (low) | TRA-057 — Consolidate HITL tests | Trivial — delete after D3-005 fix |
| P4 (scope) | TRA-031 — Grow benchmark suite to 100+ cases | Large — ~78 new cases |
