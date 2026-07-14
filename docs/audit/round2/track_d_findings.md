# Track D — Test Suite Re-Audit Findings

**Auditor:** Track D2 agent
**HEAD audited:** 4b8827c
**Methodology:** Re-execution of Round-1 Track D methodology (tra-audit-skills/worklog.md L1031-L1295). All quality gates re-run: `pytest tests` (141 passed in 0.66s) ✓, `coverage run --source=tra -m pytest tests && coverage report -m` ✓. 13 mutations executed against live source (5 from the task spec, 8 supplementary). Each mutation was reverted with `git checkout` between runs.

## Test count and structure

`pytest tests --collect-only` reports **141 tests collected** across **12 test files** + 1 conftest.py (13 .py files total in tests/).

| Test file | Tests | LOC | Status |
|---|---|---|---|
| tests/test_anchor.py | 7 | 121 | passing |
| tests/test_benchmark.py | 25 | 71 | passing (1 case-loading test + 22 parametrized benchmark cases + L3 gate + reproducibility) |
| tests/test_isa.py | 17 | 389 | passing (includes TRA-028, TRA-029, TRA-030 regression tests) |
| tests/test_kernel.py | 7 | 123 | passing |
| tests/test_modules.py | 17 | 147 | passing |
| tests/test_outstanding_findings.py | 26 | 686 | passing (11 `TestTRA0XX` classes) |
| tests/test_phase0.py | 11 | 172 | passing |
| tests/test_phase6_hardening.py | 7 | 169 | passing (some duplicate coverage with test_outstanding_findings — see TRA-D2-012) |
| tests/test_recovery.py | 8 | 96 | passing (1 misleadingly-named test — see TRA-D2-013) |
| tests/test_reporting.py | 5 | 56 | passing |
| tests/test_utils.py | 7 | 57 | passing |
| tests/test_validate.py | 4 | 64 | passing |
| tests/conftest.py | (fixtures) | 99 | 7 fixtures defined; 1 fixture never used (see TRA-D2-011) |
| **Total** | **141** | **2375** | **all passing in 0.66s** |

**SKILL.md §7 claim audit:** "141 tests across 14 test files" — the 141 count is accurate; the "14 test files" count is inflated (only 12 test_*.py files + 1 conftest.py = 13 .py files; e2e_test.py at the parent level is a manual script and is NOT collected by pytest). Track C2 already flagged this as TRA-C2-015.

## Coverage report

`coverage run --source=tra -m pytest tests && coverage report -m` → **94% overall** (1408 stmts, 89 missing).

| Module | Stmts | Miss | Cover | Notes |
|---|---|---|---|---|
| tra/__init__.py | 1 | 0 | 100% | — |
| tra/anchor.py | 245 | 20 | 92% | missing: 195, 213-214, 250, 271-278, 301, 304-307, 330, 333-336, 353 |
| tra/benchmark.py | 70 | 6 | 91% | missing: 93, 96, 109-113 |
| tra/cache.py | 64 | 7 | 89% | **below 90%** — missing 116, 118-124 (the `invalidate(pattern)` fnmatch branch, see TRA-D2-005) |
| tra/config.py | 38 | 0 | 100% | — |
| tra/diagnostics.py | 90 | 2 | 98% | missing: 198, 208 |
| tra/exceptions.py | 41 | 3 | 93% | missing: 94-99 (the `__init_subclass__` registration path for subclasses not used in tests) |
| tra/hitl.py | 31 | 1 | 97% | missing: 57 (the `on_override` callback branch, see TRA-D2-003) |
| tra/isa.py | 200 | 15 | 92% | missing: 81, 94-95, 134, 152, 193, 272, 442, 506, 577-579, 588-591 |
| tra/kernel.py | 220 | 21 | 90% | **at the 90% threshold** — missing: 121 (non-deterministic clock), 145 (registry skip-language), 175 (Illegal state raise), 220, 222 (analyze-failure post-conditions), 255-256 (L3 ConformanceFailure raise — see TRA-D2-008), 289 (rewrite_links early-return when anchor/struct missing), 303 (slugify link helper), 387-389 (inline-code protection branch — see TRA-D2-007), 432-444 (interactive HITL handoff — see TRA-D2-006), 449-451 (repair-loop re-verify), 507 (repair_history export) |
| tra/memory.py | 112 | 0 | 100% | — |
| tra/modules/__init__.py | 0 | 0 | 100% | — |
| tra/modules/base.py | 11 | 11 | **0%** | **below 90%** — `ModuleBase` ABC is defined but never imported anywhere in the repo (see TRA-D2-016) |
| tra/modules/registry.py | 42 | 3 | 93% | missing: 60, 66-67 |
| tra/modules/zh_en.py | 73 | 0 | 100% | — |
| tra/policy.py | 9 | 0 | 100% | — |
| tra/recovery.py | 49 | 0 | 100% | — |
| tra/reporting.py | 40 | 0 | 100% | — |
| tra/utils.py | 37 | 0 | 100% | — |
| tra/validate.py | 35 | 0 | 100% | — |
| **TOTAL** | **1408** | **89** | **94%** | — |

**Files below 90% line coverage (per task criteria):**
1. `tra/modules/base.py` — 0% (ModuleBase ABC unused)
2. `tra/cache.py` — 89% (invalidate(pattern) branch)
3. `tra/kernel.py` — 90% (at threshold; 21 missing lines, mostly the interactive HITL branch and the inline-code branch)

`tra/hitl.py`, `tra/recovery.py`, `tra/reporting.py` (specifically flagged in the task brief as "often under-tested") are at 97% / 100% / 100% respectively — well-covered.

## Mutation testing results

13 mutations executed (5 from the task spec + 8 supplementary). Each was reverted with `git checkout tra/<file>` between mutations. Tests re-run from a clean state each time.

| # | Mutation | Caught? | By which test? |
|---|---|---|---|
| 1 | `memory.py:175` `mutable: bool = False` → `True` | **YES** | `test_utils.py::test_version_token_classified` (asserts `v.mutable is False`) |
| 2 | `isa.py:504` canonical-terminology `Severity.BLOCKING` → `Severity.WARNING` | **YES** | `test_isa.py::test_verify_output_terminology_canonical_is_blocking`; `test_outstanding_findings.py::TestTRA009PolicyDrivenSeverity::test_canonical_term_leakage_is_blocking`; `test_outstanding_findings.py::TestTRA001SegmentLevel::test_code_block_not_translated` (3 tests fail) |
| 3 | `isa.py:502` `if entry.source in target` → `if entry.target in target` | **YES** | 26 tests fail (most kernel/benchmark/integration tests) |
| 4 | `kernel.py:178` `if idx < _KERNEL_ORDER.index(self.state)` → `if idx <= _KERNEL_ORDER.index(self.state)` | **NO** | (no test exercises a same-state transition — Round-1 D-19 "repeat-transition" gap persists) → TRA-D2-001 |
| 5 | `recovery.py:105` BrokenMarkdown `Severity.BLOCKING` → `Severity.WARNING` | **YES** | `test_recovery.py::test_broken_markdown_halts_on_critical_loss`; `test_recovery.py::test_broken_markdown_best_effort_otherwise`; `test_outstanding_findings.py::TestTRA004ExceptionRecovery::test_broken_markdown_routes_through_exception_handler` |
| 6 | `isa.py:600-603` comment out the `raise Unrecoverable` on new BLOCKING | **YES** | `test_isa.py::test_repair_raises_on_new_blocking_at_attempt_1` (TRA-028 regression test — Track R baseline's STATIC-FAIL verdict is now superseded by the test actually existing); `test_outstanding_findings.py::TestTRA001SegmentLevel::test_code_block_not_translated` |
| 7 | `isa.py:357` `except Exception` → `except RuntimeError` (narrow catch) | **YES** | 6 tests in `TestTRA033LLMSeamRobustness` (parametrized over ValueError/TypeError/OSError/TimeoutError + empty + None) |
| 8 | `isa.py:393` removed the early `return result` after LLM degradation | **NO** | (no test asserts ONE audit record per segment after degradation; test_phase6_hardening.py:84 asserts `degraded` is truthy — the first record still has `degraded: True`, the second wouldn't, but the test still passes) → TRA-D2-002 |
| 9 | `hitl.py:58` `return "override", edited` → `return "override", candidate` | **NO** | (TestTRA032HITLResolutions only asserts `result_res == resolution`, not `result_text`; the duplicated `test_hitl_review_decision_accept` in test_phase6_hardening.py only tests "accept") → TRA-D2-003 |
| 10 | `cache.py:65` removed `policy_stack_hash` from cache-key payload | **YES** | `test_phase0.py::test_cache_key_changes_with_model_or_policy` (asserts key changes when policy_stack is reversed) |
| 11 | `cache.py:62` removed `entity_hash` from cache-key payload | **NO** | (no test mutates an entity and asserts the key changes — Round-1 D-26 persists) → TRA-D2-004 |
| 12 | `cache.py:61` removed `glossary_hash` from cache-key payload | **NO** | (no test mutates glossary content — only order; Round-1 D-26 persists) → TRA-D2-004 |
| 13 | `isa.py:355-356` commented out the empty/None output guard `if not target: raise ValueError(...)` | **YES** | `test_outstanding_findings.py::TestTRA033LLMSeamRobustness::test_llm_seam_degrades_on_empty_string`; `::test_llm_seam_degrades_on_none` (2 tests fail — pydantic ValidationError on `target_span=None` propagates) |

**Scorecard: 9 of 13 mutations caught (69%).** The 4 uncaught mutations correspond to findings TRA-D2-001, TRA-D2-002, TRA-D2-003, TRA-D2-004 below.

## Benchmark coverage

`tests/benchmark/cases/sft.jsonl` (21 cases) + `tests/benchmark/cases/regression.jsonl` (1 case) = **22 total cases**. Matches SKILL.md §7 claim ("22 cases implemented, up from 13 in Round 1").

| Spec case | Implemented? | Test file | Notes |
|---|---|---|---|
| S-01 (Nested lists 3 levels) | YES | tests/benchmark/cases/sft.jsonl | "Nested list structure preserved after translation." |
| S-02 (Complex tables) | YES | tests/benchmark/cases/sft.jsonl | "Table structure preserved after translation." |
| **S-03 (Inline code vs prose)** | **NO** | — | Spec case missing — Track C2 also flagged this. Should be marked `xfail` until kernel inline-code branch is exercised (see TRA-D2-007). |
| S-04 (Blockquotes in lists) | YES | tests/benchmark/cases/sft.jsonl | "Blockquote with nested list preserved." |
| S-05 (Horizontal rules) | YES | tests/benchmark/cases/sft.jsonl | "Horizontal rule preserved exactly." |
| S-06 (Internal anchors) | YES | tests/benchmark/cases/sft.jsonl | "Internal anchor links rewritten to match translated heading." (Phase 1 test test_anchor.py also covers this as a unit test) |
| F-01..F-05 (Factual precision) | YES (all 5) | tests/benchmark/cases/sft.jsonl | — |
| T-01..T-05 (Terminology & entity) | YES (all 5) | tests/benchmark/cases/sft.jsonl | — |
| D-01..D-04 (Domain register) | YES (all 4) | tests/benchmark/cases/sft.jsonl | — |
| E-01 (Intentional ambiguity) | YES | tests/benchmark/cases/sft.jsonl | "Intentional ambiguity: 可能 maps to 'may' (epistemic), not 'might'." |
| E-02 (Mixed language) | YES | tests/benchmark/cases/sft.jsonl | "Mixed-language: entities retained, Chinese prose translated." |
| **E-03 (Broken source markdown)** | **NO** | — | Spec case missing — Track C2 also flagged this. Best-effort preservation path is not exercised as a benchmark case. |
| R-01 (Regression anchor) | YES (non-spec) | tests/benchmark/cases/regression.jsonl | "Deterministic regression anchor for the topic-comment rule layer." |

**Spec coverage:** 22 of 24 spec cases implemented (92%). Missing: S-03, E-03.
**Spec target:** 100+ cases per TRA-BENCHMARK-SUITE.md L5. Currently at 22/100+ (22%). Gap of ~78 cases — this is a known scope gap, not a regression.

## HITL coverage (TRA-032)

`tests/test_outstanding_findings.py::TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution` is parametrized over `["accept", "override", "skip"]`. All three branches fire. **However**, the assertion is weak — `assert result_res == resolution` checks only the resolution string, not the returned text. Mutation #9 confirmed this gap.

- `interactive=True` kernel end-to-end: **NOT TESTED**. The `interactive` branch (kernel.py:430-446) has zero coverage (lines 432-444 in coverage report). No test instantiates `TRAKernel(cfg, interactive=True)` and exercises the HITL handoff path through the kernel's repair loop. (See TRA-D2-006.)
- `on_override` callback param on `review_decision`: **NOT TESTED**. The `if on_override is not None:` branch (hitl.py:56-57) is at coverage line 57, listed as missing.
- `format_unrecoverable` (hitl.py:62-79): tested by `test_phase6_hardening.py::test_hitl_format_unrecoverable`.

## LLM seam coverage (TRA-033)

`tests/test_outstanding_findings.py::TestTRA033LLMSeamRobustness` covers:
- Exception types: RuntimeError, ValueError, TypeError, OSError, TimeoutError (parametrized over 5 types) ✓
- Empty string return: `test_llm_seam_degrades_on_empty_string` ✓
- None return: `test_llm_seam_degrades_on_none` ✓

**Early-return-on-degradation path (TRA-015):** the test in `test_phase6_hardening.py::test_graceful_degradation_on_llm_failure` asserts `degraded = [r for r in audit._buffer if r.artifact_snapshot.get("degraded")]` is truthy — but this is a "at least one" assertion, not "exactly one" or "the last record is the degraded one". Mutation #8 (removing the early `return result`) leaves all tests green because the FIRST audit record still has `degraded: True` and the test only checks for the presence of any degraded record. (See TRA-D2-002.)

## Invariant enforcement tests

- **Invariant 1 (canonical terminology exact):** `test_modules.py::test_zh_en_glossary_canonical` asserts `成立 → Confirmed` (never "Valid"/"True"). Also asserted in `test_outstanding_findings.py::TestTRA009PolicyDrivenSeverity::test_canonical_term_leakage_is_blocking`. ✓
- **Invariant 2 (entities immutable):** `test_isa.py::test_build_entity_table_immutable` asserts `all(e.mutable is False for e in ents)` immediately after `build_entity_table` returns. Also `test_utils.py::test_version_token_classified`. **However**, no test re-checks `e.mutable` after `translate_segment` or a full pipeline run (Round-1 D-5 persists — but this is WARNING-level and not in this audit's mutation scope).
- **Invariant 3 (verify never self-scores):** `test_isa.py::test_verify_output_ignores_confidence_note` (TRA-029 test, L293-324) is now present — Track R baseline's STATIC-FAIL verdict is superseded. Test injects a low-confidence glossary entry (`confidence_note=0.01`) into `ctx.glossary_cache`, runs `verify_output` on a clean target, and asserts no diagnostic references the low-confidence entry. ✓
- **Invariant 4 (repair surgical):** `test_isa.py::test_repair_raises_on_new_blocking_at_attempt_1` (TRA-028 test, L245-291) is now present — Track R baseline's STATIC-FAIL verdict is superseded. Test calls `repair_segment` with `attempt=1, max_retries=3` and a target where the repair substitution introduces a forbidden-drift BLOCKING; asserts `Unrecoverable` is raised. ✓

**Net result:** Track R's STATIC-FAIL verdicts on TRA-028 and TRA-029 are **now resolved** — both tests exist and pass. (Track R likely re-ran the audit before these tests were added; the test file at HEAD 4b8827c contains both tests.)

## conftest.py fixture usage (TRA-034)

7 fixtures defined in `tests/conftest.py`:

| Fixture | Defined at | Used in | Notes |
|---|---|---|---|
| `sample_glossary` | conftest.py:20 | test_phase0.py (via `cache_context`) | only used as a transitive dependency |
| `sample_entities` | conftest.py:28 | test_phase0.py (via `cache_context`) | only used as a transitive dependency |
| `cache_context` | conftest.py:36 | test_phase0.py (3 tests) | the workhorse fixture for cache-key tests |
| `evidence_registry` | conftest.py:57 | test_phase0.py (via `sample_evidence`) | transitive |
| `sample_evidence` | conftest.py:62 | test_phase0.py (1 test) | — |
| `config` | conftest.py:76 | (no test functions reference it directly) | **only used as a building block for `kernel_config`** |
| `kernel_config` | conftest.py:82 | **NOT USED — only mentioned in a comment** at test_kernel.py:13 ("Uses the shared kernel_config fixture pattern") | **TRA-D2-011 finding** |

Track R baseline's claim "conftest.py defines 7 fixtures" is correct; the claim "STATIC-PASS" is technically right (the fixtures exist), but TRA-034's intent (sharing fixtures across test files to eliminate boilerplate) is only partially realized — `kernel_config` was added per the Round-1 D-30 finding but the migration of `test_kernel.py::_kernel()`, `test_phase6_hardening.py`, `test_benchmark.py::_cfg()`, and `test_outstanding_findings.py`'s repeated `BootstrapConfig.from_yaml(...).model_copy(...)` boilerplate to use it was never actually completed (Round-1 D-30 persists — see TRA-D2-011).

## TDD discipline

11 test classes named `TestTRA0XX...` in `test_outstanding_findings.py`:
- TestTRA014PathTraversal (5 tests)
- TestTRA012SanitizeChokepoint (2 tests)
- TestTRA013AuditReproducibility (2 tests)
- TestTRA007TransitionOrdering (1 test)
- TestTRA009PolicyDrivenSeverity (2 tests)
- TestTRA004ExceptionRecovery (1 test)
- TestTRA032HITLResolutions (3 tests, parametrized)
- TestTRA033LLMSeamRobustness (7 tests, parametrized)
- TestTRA002RegistryWiring (1 test)
- TestTRA008RewriteLinks (1 test)
- TestTRA001SegmentLevel (1 test)

Plus 3 more regression tests in `test_isa.py` named after findings (in comments, not class names): `test_repair_raises_on_new_blocking_at_attempt_1` (TRA-028), `test_verify_output_ignores_confidence_note` (TRA-029), `test_verify_output_terminology_canonical_is_blocking` (TRA-030/TRA-009), `test_verify_output_structural_mismatch_is_blocking` (TRA-030).

**Tests NOT named after findings:**
- Most tests in `test_anchor.py`, `test_kernel.py`, `test_isa.py`, `test_phase0.py`, `test_phase6_hardening.py`, `test_recovery.py`, `test_reporting.py`, `test_utils.py`, `test_validate.py`, `test_modules.py`, `test_benchmark.py` — these are organized by module (Phase 1-6 structure). They are substantive (not duplicative) but follow the older "test by phase" naming convention rather than the "test by finding ID" convention of test_outstanding_findings.py.

**Duplicates between `test_phase6_hardening.py` and `test_outstanding_findings.py`:**
- `test_phase6_hardening.py::test_hitl_review_decision_accept` (tests only "accept") is fully subsumed by the parametrized `TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution[accept]`.
- `test_phase6_hardening.py::test_graceful_degradation_on_llm_failure` (tests only RuntimeError) is fully subsumed by `TestTRA033LLMSeamRobustness::test_llm_seam_degrades_on_each_exception_type[RuntimeError]`.

These two tests in `test_phase6_hardening.py` are pre-TRA-032/TRA-033 versions that were never deleted after the parametrized versions were added. They are duplicative (see TRA-D2-012).

## Test isolation (special attention)

**Tests write to CWD-relative paths** (Round-1 D-12 finding persists):
- `tests/test_isa.py:30` — `AuditTrail("audit_trace.jsonl")` (relative path; writes to CWD)
- `tests/test_isa.py:145, 163, 384` — `TranslationCache("./cache", enabled=True)` (writes a `cache/` dir to CWD)
- `tests/test_reporting.py:11, 28` — `AuditTrail("x.jsonl")`, `AuditTrail("y.jsonl")` (writes to CWD)
- `tests/test_phase6_hardening.py:53, 73` — `AuditTrail("x.jsonl")` (writes to CWD)

**Tests write to absolute `/tmp/` paths** (related isolation issue):
- `tests/test_outstanding_findings.py:98, 283, 290, 438, 468, 500` — `AuditTrail("/tmp/test_*.jsonl")`
- `tests/test_outstanding_findings.py:428, 458, 490` — `TranslationCache("/tmp/test_cache_*", enabled=False)`

After running `pytest tests` from `tra-prototype/`, the following artifacts are left in the working directory:
- `audit_trace.jsonl` (grew to ~1 MB after one full run)
- `x.jsonl`, `y.jsonl` (small audit-trail files)
- `cache/cache.db` (diskcache file)

All of these are in the prototype's `.gitignore` and the root `.gitignore`, so they don't pollute git, but the tests are not hermetic — they share state via the CWD. (See TRA-D2-009, TRA-D2-010.)

**Random-order test execution:** `pytest tests -p randomly --randomly-seed=<various>` passes on seeds 1, 4242, 99999 (and the default random seed from `pytest-randomly`). Tests appear order-independent, BUT this is partly because the CWD-shared `./cache` and `audit_trace.jsonl` files are deterministic given the same inputs — order-independence is incidental, not by design.

## `test_outstanding_findings.py` size (special attention)

At **686 LOC** it is the largest test file in the suite (29% of all test LOC). Organization is clean — 11 clearly delimited `# === TRA-0XX — <title> ===` sections, each containing one `TestTRA0XX` class. The class-per-finding pattern is consistent. The file is NOT a dumping ground, but its growth trajectory (it accumulates one new `TestTRA0XX` class per remediated finding) means it will become unwieldy as more findings are remediated. (See TRA-D2-019.)

## `test_isa.py` size (special attention)

At **389 LOC** (17 tests), it covers all 6 ISA instructions: `analyze_document`, `build_glossary`, `build_entity_table`, `translate_segment`, `verify_output`, `repair_segment` (each has at least one test). Plus the TRA-028/029/030 regression tests. Coverage is broad but uneven — `translate_segment` has 3 tests (canonical substitution, cache hit, zh-rule layer), while `repair_segment` has 3 tests (resolves epistemic drift, raises on new BLOCKING, plus history-records test in test_phase6_hardening.py). `verify_output` has 5 tests (clean doc, missing entity, epistemic drift, terminology canonical, structural mismatch).

## `e2e_test.py` (special attention)

`/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/e2e_test.py` (103 LOC) is a **module-level script** — no `test_*` functions. Confirmed via `pytest e2e_test.py` → "no tests ran in 0.16s". It's documented in SKILL.md §7 step 6 ("run `python e2e_test.py` to exercise the full pipeline"). The script writes to `e2e_audit_trace.jsonl`, `e2e_artifacts/`, `e2e_cache/` in the prototype dir (all gitignored). (See TRA-D2-015.)

## Benchmark JSONL contents (special attention)

- `tests/benchmark/cases/regression.jsonl` — 1 line, 1 case (R-01). Source: `"系统成立 under heavy load."`. Asserts `must_contain=["The system is Confirmed"]`. Substantive (tests the topic-comment rule layer deterministically).
- `tests/benchmark/cases/sft.jsonl` — 21 lines, 21 cases. Each case has `id`, `category`, `source`, `level`, `must_contain`, `must_not_contain`, `zero_blocking`, `description`. Sources range from 1 sentence (F-01: `"Latency <60ms observed under load."`) to multi-line markdown (S-02, D-01..D-03). Substantive — every case tests a specific spec criterion.

## Summary

- Total findings: **18** (1 BLOCKING, 11 WARNING, 6 INFO)
- BLOCKING: 1 (TRA-D2-002 — LLM degradation single-record invariant unprotected by tests; TRA-015 regression risk)
- WARNING: 11
- INFO: 6

**Carry-over status from Round-1 Track D (30 findings):**
- **3 of 3 BLOCKING (D-1, D-2, D-3) FIXED:** D-1 is now covered by `test_repair_raises_on_new_blocking_at_attempt_1` (TRA-028 test); D-2 is now covered by `test_verify_output_ignores_confidence_note` (TRA-029 test); D-3 is now covered by `test_verify_output_terminology_canonical_is_blocking`.
- **D-4 (structural BLOCKING → WARNING):** FIXED — `test_verify_output_structural_mismatch_is_blocking` exists.
- **D-5 (post-translation entity immutability):** PERSISTS — no test re-checks `e.mutable` after a full pipeline run. Out of this audit's mutation scope.
- **D-6 (MALFORMED_MARKDOWN):** PERSISTS — `test_analyze_malformed_raises` still uses an unclosed fence, which markdown-it-py treats as valid.
- **D-7 (benchmark coverage):** PARTIALLY FIXED — 22/24 spec cases (was 13/24); S-03 and E-03 still missing. Round-1's count of "13 implemented" was already wrong (Track C2 corrected).
- **D-8 (HITL skip/override + interactive kernel):** PARTIALLY FIXED — skip/override paths now parametrized in TestTRA032HITLResolutions; interactive=True kernel mode still untested.
- **D-9 (LLM-seam exception types):** FIXED — parametrized over 5 exception types + empty + None.
- **D-10 through D-30:** largely persist (see individual findings below).

**New findings introduced by the re-audit:**
- TRA-D2-002 (BLOCKING) — single-record-on-degradation assertion gap (latent TRA-015 regression risk)
- TRA-D2-003 (WARNING) — HITL override-text assertion gap
- TRA-D2-005 (WARNING) — cache.invalidate(pattern) branch untested (TRA-011 regression test missing)
- TRA-D2-007 (WARNING) — inline-code protection branch untested
- TRA-D2-008 (WARNING) — L3 ConformanceFailure raise branch untested
- TRA-D2-011 (WARNING) — conftest kernel_config fixture defined but never used
- TRA-D2-012 (INFO) — duplicate tests in test_phase6_hardening.py
- TRA-D2-016 (WARNING) — ModuleBase ABC has 0% coverage (dead code)
- TRA-D2-019 (INFO) — test_outstanding_findings.py is 686 LOC, growth trajectory

## Findings

### TRA-D2-001 — Same-state transition not tested (kernel._transition)
- **Severity:** WARNING
- **Category:** Test Suite / mutation-gap
- **Carry-over or new:** Carry-over (Round-1 D-19 partial)
- **Evidence:** `tra/kernel.py:178`; `tests/test_kernel.py:66-93`
- **Detail:** The `_transition` method's "strictly forward" guard allows same-state transitions (`idx == idx.state` is permitted). Mutation #4 changed `if idx < _KERNEL_ORDER.index(self.state)` to `if idx <= _KERNEL_ORDER.index(self.state)` — this would make same-state transitions raise. All 141 tests pass under this mutation. No test exercises a same-state transition (e.g., `BOOTSTRAP → BOOTSTRAP`), so the spec-permitted same-state behavior is unprotected. If a future change accidentally tightens the guard to `<=`, the tests will not detect the regression.
- **Suggested fix:** Add `test_kernel_same_state_transition_is_allowed` that calls `k._transition(KernelState.INITIALIZE_RUNTIME)` twice and asserts no exception. Also add `test_kernel_skip_forward_transition_raises` (skipping a state should raise per the canonical order — also currently untested).

### TRA-D2-002 — LLM-degradation "single audit record" invariant is unprotected
- **Severity:** BLOCKING
- **Category:** Test Suite / mutation-gap
- **Carry-over or new:** New (latent gap in TRA-015 / Round-1 D-9 partial)
- **Evidence:** `tra/isa.py:384-393` (the early `return result` after degradation); `tests/test_phase6_hardening.py:84-85`
- **Detail:** Mutation #8 removed the `return result` statement at isa.py:393 (the TRA-015 fix). With this mutation, the code falls through and emits a SECOND audit record at isa.py:409 (without the `degraded: True` artifact_snapshot). The test at test_phase6_hardening.py:84-85 asserts `degraded = [r for r in audit._buffer if r.artifact_snapshot.get("degraded")]` is truthy — this passes because the FIRST audit record still has `degraded: True`. The test does NOT assert (a) the count of records per segment, (b) that the LAST record per segment is the degraded one, or (c) that no non-degraded record follows a degraded record. This is the exact TRA-015 regression scenario ("an auditor inspecting the last record per segment would miss the degradation") — and it is not caught. The mutation reverts the TRA-015 fix without any test failing.
- **Suggested fix:** In `TestTRA033LLMSeamRobustness`, after triggering degradation, assert:
  - `len(translate_segment_records) == 1` (exactly one audit record per segment)
  - the single record's `artifact_snapshot.get("degraded") is True`
  - No subsequent non-degraded record for the same `cache_key` exists in the trail.

### TRA-D2-003 — HITL override-text assertion is weak
- **Severity:** WARNING
- **Category:** Test Suite / weak-assertion
- **Carry-over or new:** New (latent gap in TRA-032 remediation)
- **Evidence:** `tests/test_outstanding_findings.py:367-403` (TestTRA032HITLResolutions)
- **Detail:** Mutation #9 changed `hitl.py:58` from `return "override", edited` to `return "override", candidate`. With this mutation, the override path silently returns the original machine candidate instead of the user-supplied edited text — defeating the purpose of HITL. The `TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution[override]` test passes because it only asserts `result_res == resolution` (the resolution string), not `result_text == "edited text"`. The `on_override` callback branch (hitl.py:56-57) is also untested — coverage report lists line 57 as missing.
- **Suggested fix:** In the override branch of the test, additionally assert `result_text == "edited text"`. Also add a parametrized test that exercises the `on_override` callback (e.g., `on_override=lambda src, txt: txt.upper()` and assert the result text is uppercased).

### TRA-D2-004 — Cache-key entity/glossary content sensitivity untested
- **Severity:** WARNING
- **Category:** Test Suite / mutation-gap
- **Carry-over or new:** Carry-over (Round-1 D-26 persists verbatim)
- **Evidence:** `tra/cache.py:60-66` (the cache-key payload); `tests/test_phase0.py:28-50`
- **Detail:** Mutations #11 and #12 removed the `entity_hash` and `glossary_hash` fields from the cache-key payload. All 141 tests pass under both mutations. The existing tests only mutate (a) the ORDER of the glossary (test_cache_key_is_deterministic_and_order_independent, which catches `_hash_sorted` misuse but not omission of the field), (b) the model_version (test_cache_key_changes_with_model_or_policy), and (c) the ORDER of the policy_stack. No test mutates an entity's NAME, a glossary entry's TARGET, or adds a new entity/glossary entry. A mutation that drops `entity_hash` (or `glossary_hash`) entirely from the payload — which would cause collisions across different entity/glossary contents — is not detected.
- **Suggested fix:** Add `test_cache_key_changes_when_entity_name_changes` (mutate one entity's name, assert key differs) and `test_cache_key_changes_when_glossary_target_changes` (mutate one glossary entry's target, assert key differs).

### TRA-D2-005 — `cache.invalidate(pattern)` branch has zero coverage
- **Severity:** WARNING
- **Category:** Test Suite / coverage-gap
- **Carry-over or new:** New (TRA-011 regression-test gap)
- **Evidence:** `tra/cache.py:107-128` (the `invalidate(pattern)` fnmatch branch); `tests/test_phase0.py:61` (only exercises `cache.invalidate()` with no pattern)
- **Detail:** Coverage report shows `tra/cache.py` lines 116, 118-124 as missing — the entire `if pattern: ... fnmatch.fnmatch(...) ... self._cache.delete(key)` branch. The only test that calls `invalidate` is `test_phase0.py:61` which calls `cache.invalidate()` (no pattern argument) — exercising the bulk-clear branch (line 126-128) but NOT the pattern branch. This means TRA-011's remediation (pattern-based invalidation via fnmatch) is empirically verified but NOT encoded as a regression test. A future change that breaks the pattern-based path (e.g., reverts to passing the pattern as a literal key to `diskcache.delete()`, which was the original TRA-011 bug) would not be caught.
- **Suggested fix:** Add `test_cache_invalidate_with_pattern_deletes_matching_keys` — populate the cache with 3 entries (`translation:foo`, `translation:bar`, `other:baz`), call `invalidate("translation:*")`, assert 2 entries deleted and only `other:baz` remains.

### TRA-D2-006 — `interactive=True` kernel mode is untested
- **Severity:** WARNING
- **Category:** Test Suite / coverage-gap
- **Carry-over or new:** Carry-over (Round-1 D-8 partial — skip/override parametrization landed, interactive kernel mode did not)
- **Evidence:** `tra/kernel.py:430-446` (the `if self.interactive:` block); coverage report lists lines 432-444 as missing
- **Detail:** No test instantiates `TRAKernel(cfg, interactive=True)`. The interactive HITL handoff path — which imports `format_unrecoverable` and `review_decision`, builds the uncertainty/source-context, calls `review_decision`, and adopts the reviewer's resolution as the new target — has zero coverage. A mutation that removes the `if self.interactive:` block entirely, or that passes wrong arguments to `review_decision`, or that ignores the returned `text` and keeps the old target — none would be caught. The CLI exposes `--interactive` (tra_cli.py:72) but there is no CLI test for it either.
- **Suggested fix:** Add `test_kernel_interactive_mode_triggers_hitl_on_unrecoverable` — construct a kernel with `interactive=True`, force an UNRECOVERABLE repair (e.g., via a target where the canonical term replacement introduces a forbidden drift), monkeypatch `tra.hitl.review_decision` to return `("override", "manually-repaired-text")`, run the kernel, and assert (a) the override text appears in the final target, (b) the audit trail records the HITL handoff.

### TRA-D2-007 — Inline-code protection branch in `_execute_translation` is untested
- **Severity:** WARNING
- **Category:** Test Suite / coverage-gap
- **Carry-over or new:** New
- **Evidence:** `tra/kernel.py:384-391` (the `_INLINE_RE` + `_stash_inline` block); coverage report lists lines 387-389 as missing
- **Detail:** The kernel's translation path protects both fenced code blocks (lines 376-381, exercised by `TestTRA001SegmentLevel::test_code_block_not_translated`) and inline code (lines 384-391). The inline-code branch is NEVER exercised — no test feeds a source with inline `` `code` `` through `kernel.run()`. The only inline-code test is `tests/test_anchor.py:17` which uses `build_structural_map` directly (not the kernel's translation path). A mutation that removes the inline-code stash (e.g., drops lines 384-391) would translate the contents of inline code, violating the S-03 spec case ("Backticks preserved; content inside backticks untranslated") — but no test catches this.
- **Suggested fix:** Add `test_kernel_inline_code_not_translated` — source = "Inline `成立` here." Run `kernel.run(source)`. Assert the output contains `` `成立` `` (preserved verbatim) AND `Confirmed` is NOT inside the backticks (the paragraph-level "成立" outside backticks would be translated, but the inline one should not).

### TRA-D2-008 — L3 ConformanceFailure raise branch is untested
- **Severity:** WARNING
- **Category:** Test Suite / coverage-gap
- **Carry-over or new:** New (Round-1 D-20 partial — negative-test gap persists at the kernel level)
- **Evidence:** `tra/kernel.py:252-260` (the L3 gate ConformanceFailure raise); coverage report lists lines 255-256 as missing
- **Detail:** The kernel's in-band L3 gate (per Track A2's verification) calls `verify_output` on the final target and raises `ConformanceFailure` if any BLOCKING remains after the repair loop. The negative path (raise) is untested. The existing `test_l3_gate_zero_blocking_subset` in `test_benchmark.py` only asserts the positive path (`summary["blocking"] == 0`). A mutation that removes the `if final_blocking: raise ConformanceFailure(...)` block (silently publishing non-conformant output at L3) would not be caught.
- **Suggested fix:** Add `test_l3_kernel_raises_on_blocking_after_repair` — construct a source where the canonical term substitution introduces a forbidden drift that `repair_segment` cannot fix (e.g., target containing both `成立` and `Valid` where the repair would replace `成立` with `Confirmed` but `Valid` remains as the new BLOCKING). Run `kernel.run(source)` at L3_STRICT. Assert `ConformanceFailure` is raised.

### TRA-D2-009 — Tests write to CWD via relative paths (`audit_trace.jsonl`, `x.jsonl`, `./cache`)
- **Severity:** WARNING
- **Category:** Test Suite / non-hermetic
- **Carry-over or new:** Carry-over (Round-1 D-12 persists)
- **Evidence:** `tests/test_isa.py:30` (`AuditTrail("audit_trace.jsonl")`); `tests/test_isa.py:145, 163, 384` (`TranslationCache("./cache", enabled=True)`); `tests/test_reporting.py:11, 28` (`AuditTrail("x.jsonl")`, `AuditTrail("y.jsonl")`); `tests/test_phase6_hardening.py:53, 73` (`AuditTrail("x.jsonl")`)
- **Detail:** After running `pytest tests` from `tra-prototype/`, the working directory contains a 1 MB `audit_trace.jsonl`, a `cache/cache.db`, and small `x.jsonl`/`y.jsonl` files. These are gitignored so they don't pollute the repo, but the tests are not hermetic — they share state via the CWD. If two tests run in parallel (or if `audit_trace.jsonl` from a prior run is not cleaned), state leaks between runs. Tests pass in random order (verified with `pytest-randomly`), but only because the cache and audit trail are deterministic given the same inputs.
- **Suggested fix:** Migrate `tests/test_isa.py::_audit()` to use `tmp_path` (via a fixture). Migrate `tests/test_isa.py:145, 163, 384` and `tests/test_phase6_hardening.py:75` to use `tmp_path / "cache"`. Migrate `tests/test_reporting.py:11, 28` and `tests/test_phase6_hardening.py:53, 73` to use `tmp_path / "audit.jsonl"`. Use the existing `kernel_config` fixture (TRA-D2-011) for the kernel-level tests.

### TRA-D2-010 — Tests write to absolute `/tmp/` paths
- **Severity:** INFO
- **Category:** Test Suite / non-hermetic
- **Carry-over or new:** Carry-over (variant of Round-1 D-12)
- **Evidence:** `tests/test_outstanding_findings.py:98` (`AuditTrail("/tmp/test_audit_tra012.jsonl")`); `tests/test_outstanding_findings.py:283, 290, 438, 468, 500` (all `/tmp/test_*.jsonl`); `tests/test_outstanding_findings.py:428, 458, 490` (`TranslationCache("/tmp/test_cache_*", enabled=False)`)
- **Detail:** These tests hardcode `/tmp/` paths, which (a) leak state across test runs (the files persist), (b) are not isolated per-test (multiple tests share `/tmp/test.jsonl`), and (c) are not parallelizable. The `TranslationCache` instances use `enabled=False` so they don't actually write to disk, but the `AuditTrail` instances DO write. The `/tmp/test_audit_tra012.jsonl` and `/tmp/test.jsonl` files accumulate across runs.
- **Suggested fix:** Replace all `/tmp/test_*.jsonl` with `tmp_path / "test.jsonl"` (the standard pytest `tmp_path` fixture).

### TRA-D2-011 — `kernel_config` fixture defined but never used
- **Severity:** WARNING
- **Category:** Test Suite / unused-fixture
- **Carry-over or new:** Carry-over (Round-1 D-30 partial — fixture added but migration never completed)
- **Evidence:** `tests/conftest.py:82-99` (the `kernel_config` fixture); `tests/test_kernel.py:13` (only a comment references it: `# Uses the shared kernel_config fixture pattern (TRA-034).`); grep shows zero actual usages
- **Detail:** The `kernel_config` fixture was added (per Round-1 D-30) to eliminate the duplicated `BootstrapConfig.from_yaml(...).model_copy(update={...})` boilerplate across test_kernel.py, test_phase6_hardening.py, test_benchmark.py, and test_outstanding_findings.py. But the migration was never actually performed — every test file still defines its own `_kernel(tmp_path)`, `_cfg()`, or inline `BootstrapConfig.from_yaml(...).model_copy(...)` boilerplate. The comment at test_kernel.py:13 claims to "use the shared kernel_config fixture pattern" but the immediately-following `_kernel()` function does NOT use it. The fixture is dead code.
- **Suggested fix:** Either (a) migrate `test_kernel.py::_kernel()` to use the `kernel_config` fixture (preferred), or (b) delete the `kernel_config` fixture if the migration is not planned. Either way, fix the misleading comment at test_kernel.py:13.

### TRA-D2-012 — Duplicate tests in `test_phase6_hardening.py`
- **Severity:** INFO
- **Category:** Test Suite / duplication
- **Carry-over or new:** New
- **Evidence:** `tests/test_phase6_hardening.py:143-153` (`test_hitl_review_decision_accept` — accept-only); `tests/test_phase6_hardening.py:71-85` (`test_graceful_degradation_on_llm_failure` — RuntimeError-only)
- **Detail:** Both tests are fully subsumed by the parametrized versions in `test_outstanding_findings.py`:
  - `test_hitl_review_decision_accept` ≡ `TestTRA032HITLResolutions::test_review_decision_returns_correct_resolution[accept]`
  - `test_graceful_degradation_on_llm_failure` ≡ `TestTRA033LLMSeamRobustness::test_llm_seam_degrades_on_each_exception_type[RuntimeError]`
  
  The pre-parametrization versions were left in place when the parametrized versions were added. They add maintenance burden (two places to update if the contract changes) and can give false confidence (a future mutation might be caught by one but not the other).
- **Suggested fix:** Delete `test_hitl_review_decision_accept` and `test_graceful_degradation_on_llm_failure` from `test_phase6_hardening.py`. The parametrized versions in `test_outstanding_findings.py` are strictly more thorough.

### TRA-D2-013 — `test_route_exception_falls_back_for_unknown` is misleadingly named
- **Severity:** INFO
- **Category:** Test Suite / misleading-name
- **Carry-over or new:** Carry-over (Round-1 D-25 persists verbatim)
- **Evidence:** `tests/test_recovery.py:93-96`
- **Detail:** The test name claims to exercise "the unknown-exception fallback" (recovery.py:176-182, the bare `TRAException` branch at the end of `route_exception`). But the test body calls `route_exception(BrokenMarkdown(), amb)` — BrokenMarkdown IS a known exception type (handled at recovery.py:164-167). The test actually exercises the BrokenMarkdown best-effort path, not the unknown-exception fallback. A mutation that removes the final `return _emit(ctx_ambiguities, exc.code, Severity.WARNING, RecoveryAction.PRESERVE_SOURCE, str(exc))` at recovery.py:176-182 would NOT be caught by this test. The stale `# type: ignore[arg-type]` at line 95 was already flagged as TRA-B2-004 by Track B2.
- **Suggested fix:** Rename to `test_route_exception_handles_broken_markdown_with_defaults` (accurate) AND add a new `test_route_exception_falls_back_for_unknown` that constructs a bare `TRAException("unknown")` (not a subclass) and asserts `route_exception` returns a `RecoveryReport` with `action == RecoveryAction.PRESERVE_SOURCE` and `code == "TRA_ERROR"`.

### TRA-D2-014 — `tra/modules/base.py` `ModuleBase` ABC has 0% coverage and is dead code
- **Severity:** WARNING
- **Category:** Test Suite / dead-code
- **Carry-over or new:** New (Track B2 did not flag this)
- **Evidence:** `tra/modules/base.py:1-28`; coverage report shows 0/11 lines covered; `grep -r ModuleBase tra-prototype/` returns only the definition (zero imports/uses)
- **Detail:** `ModuleBase` is an abstract base class defined for TRA modules (Spec §9 plug-ins). It declares `get_glossary_mappings`, `get_style_profile`, and `apply_rules` as abstract methods. However, no production code or test code imports `ModuleBase` — `ZHENModule` (the only concrete module) does not inherit from it, the `ModuleRegistry` does not reference it, and the `StubModule` in `TestTRA002RegistryWiring` (test_outstanding_findings.py:516-557) is a duck-typed class without `ModuleBase` as a base. The class is dead code. Because it's never imported, it has 0% coverage. Per the task criteria ("Files below 90% line coverage are findings"), this is a finding — but the deeper issue is the dead code itself, which misleads readers into thinking modules must inherit from `ModuleBase`.
- **Suggested fix:** Either (a) delete `tra/modules/base.py` (preferred — it's unused), or (b) make `ZHENModule` and the `ModuleInterface` dataclass in `registry.py` actually use `ModuleBase` as a base, and add a test that asserts `ZHENModule` is a `ModuleBase` subclass. Option (a) is simpler; option (b) enforces the contract.

### TRA-D2-015 — `e2e_test.py` is a manual script, not collected by pytest
- **Severity:** INFO
- **Category:** Test Suite / out-of-suite
- **Carry-over or new:** New
- **Evidence:** `tra-prototype/e2e_test.py` (103 LOC, module-level script, no `test_*` functions); `pytest e2e_test.py` → "no tests ran in 0.16s"; `SKILL.md:274` ("run `python e2e_test.py`")
- **Detail:** The e2e_test.py file is a top-level script that loads `to_translate.md`, hijacks the `llm_translate` seam with a pre-generated manual translation, runs the kernel at L3, and prints the audit trail summary. It is NOT a pytest test — it has no `test_*` functions and pytest ignores it. SKILL.md §7 step 6 documents it as a manual command. The script writes to `e2e_audit_trace.jsonl`, `e2e_artifacts/`, `e2e_cache/` in the prototype dir (gitignored at the root). The script provides zero regression protection — it only prints, never asserts. If the kernel regressed (e.g., stopped emitting `TRANSLATE_SEGMENT` records), the script would just print different numbers without failing.
- **Suggested fix:** Either (a) convert `e2e_test.py` into a proper pytest test (add `def test_e2e_pipeline_with_llm_seam(tmp_path):` and assert key invariants: zero BLOCKING, audit trail contains all 6 ISA instructions, output length > 0), or (b) document in SKILL.md that `e2e_test.py` is a manual demo script with no regression value (and remove it from any "test suite" claims).

### TRA-D2-016 — `test_outstanding_findings.py` is 686 LOC, growth trajectory concern
- **Severity:** INFO
- **Category:** Test Suite / maintainability
- **Carry-over or new:** New
- **Evidence:** `tests/test_outstanding_findings.py` (686 LOC, 26 tests, 11 test classes — 29% of all test LOC in the suite)
- **Detail:** The file is currently well-organized (clear `# === TRA-0XX — <title> ===` section headers, one class per finding). But its growth model — add a new `TestTRA0XX` class for every remediated finding — means it will grow ~50-80 LOC per remediation. At the current remediation pace (Round-1 had 35 findings; Round-2 has 11+ new findings across Tracks A2/B2/C2/D2), the file is on track to exceed 1000 LOC within 2-3 audit rounds. The other test files (test_kernel.py: 123 LOC, test_isa.py: 389 LOC) are organized by phase, not by finding — creating a structural mismatch.
- **Suggested fix:** Consider splitting `test_outstanding_findings.py` by category (e.g., `test_tra001_segment_level.py`, `test_tra014_path_traversal.py`, etc.) once it exceeds ~800 LOC. Alternatively, document the convention in SKILL.md so future contributors know the growth is intentional.

### TRA-D2-017 — Benchmark spec coverage: 22 of 24 cases implemented; S-03 and E-03 still missing
- **Severity:** INFO
- **Category:** Test Suite / benchmark-coverage
- **Carry-over or new:** Carry-over (Round-1 D-7 partial — was 13/24, now 22/24)
- **Evidence:** `tests/benchmark/cases/sft.jsonl` (21 cases); `tests/benchmark/cases/regression.jsonl` (1 case); spec `TRA-BENCHMARK-SUITE.md` (24 cases S-01..S-06, F-01..F-05, T-01..T-05, D-01..D-04, E-01..E-03)
- **Detail:** 22/24 spec cases (92%) are implemented as JSONL fixtures with concrete `must_contain`/`must_not_contain`/`zero_blocking` assertions. Two spec cases are missing:
  - **S-03 (Inline code vs prose):** "Backticks preserved; content inside backticks untranslated." Track C2 also flagged this. The kernel's inline-code protection branch (kernel.py:384-391) is untested (see TRA-D2-007) — adding S-03 as a benchmark case would exercise it end-to-end. The case can be added now even though the inline-code branch is technically already implemented; if the case passes, it serves as a regression test.
  - **E-03 (Broken source markdown):** "Best-effort preservation; error logged in Audit Trace." The `recover_broken_markdown` path is unit-tested in test_recovery.py but not exercised as a benchmark case. Adding E-03 would require constructing a source that causes `markdown-it-py` to raise (which is non-trivial — markdown-it-py is lenient; Round-1 D-6 noted this).
  
  The spec target is "100+ cases" (TRA-BENCHMARK-SUITE.md L5). At 22 cases, the suite is at 22% of target. This is a known scope gap (acknowledged in SKILL.md §8 "Known limitations") and not a regression — but the gap is not surfaced in the test suite (no skipped/xfail markers for S-03/E-03).
- **Suggested fix:** Add S-03 and E-03 as JSONL fixtures. For S-03, source = "Inline `成立` here." with `must_contain=["`成立`"]` and `must_not_contain=["`Confirmed`"]`. For E-03, construct a source that triggers `BrokenMarkdown` (e.g., monkeypatch `build_structural_map` in a parametrized variant) — this may require extending the benchmark harness to support monkeypatching.

### TRA-D2-018 — SKILL.md §7 "14 test files" claim is inflated
- **Severity:** INFO
- **Category:** Test Suite / doc-vs-code
- **Carry-over or new:** Carry-over (Track C2 already flagged as TRA-C2-015; re-confirmed)
- **Evidence:** `tra-prototype/SKILL.md:222` ("141 tests across 14 test files"); `ls tests/*.py` returns 13 files (12 `test_*.py` + 1 `conftest.py`)
- **Detail:** The "141 tests" count is accurate. The "14 test files" count is inflated — there are 12 actual test files (test_anchor.py, test_benchmark.py, test_isa.py, test_kernel.py, test_modules.py, test_outstanding_findings.py, test_phase0.py, test_phase6_hardening.py, test_recovery.py, test_reporting.py, test_utils.py, test_validate.py) plus conftest.py (which holds fixtures, not tests) = 13. The 14th file is unclear — possibly `e2e_test.py` was counted, but that's outside `tests/` and is not collected by pytest (see TRA-D2-015). Track C2 flagged this as TRA-C2-015; this audit re-confirms.
- **Suggested fix:** Update SKILL.md:222 to "141 tests across 12 test files" (or "13 .py files including conftest.py").
