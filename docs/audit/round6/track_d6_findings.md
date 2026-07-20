# Track D6 — Test Suite Re-Audit (Round 6)

**Task ID:** D6-1
**Auditor:** Track D6 (test suite)
**HEAD audited:** `c4ecd41` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/`
**Prototype engine:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Methodology:** Full-suite run + coverage measurement + per-test-class reading of every R5-added test class + cache-isolation probe + mutmut runtime probe + benchmark-case enumeration + absolute-path grep + assertion-depth audit.
**Audit date:** 2026-07-19

## Scope

Per the task brief, Track D6 audits the test suite at HEAD `c4ecd41` (post-Round-5 remediation, Batches 1/2/5/A–I). Audit dimensions:

1. **Coverage** — line + branch coverage via `coverage.py`
2. **Benchmark suite** — case count, category distribution, L3 gate assertion
3. **Per-leaf translation tests** — `TestTRA001_PerLeafSegmentTranslation` (R5 Batch H, TRA-A5-001)
4. **LLM seam DI tests** — `TestTRA_D5_002_LLMSeamDependencyInjection` (R5 Batch C, TRA-D5-002)
5. **HITL e2e tests** — `TestTRA_D5_007InteractiveE2E` (R5 Batch C, TRA-D5-007) + `TestTRA_D5_004_005_ReviewDecisionCoverage`
6. **Cache HMAC tests** — `TestTRA_B5_004_CacheHmacIntegrity` (R5 Batch E, TRA-B5-004 / TRA-079)
7. **Mutation testing config** — `TestTRA_D5_011_MutationTestingConfigured` (R5 Batch F, TRA-D5-011 / TRA-094)
8. **Test isolation** — `conftest.py` fixtures, `tmp_path` usage, `cache_directory` override, env-var leakage
9. **New R5 test classes** — 23 new classes added in R5 batches (TRA-A5-005, A5-010, A5-013, A5-014, A5-003, B5-009/010/011/012, B5-004, D5-002/007/008/011/016/017, E5-003/005, F5-010/011/012/013, 001-Phase-8, 3 type-safety residuals)

## Baseline verification (task-brief claims)

| Claim | Verified value | Status |
|---|---|---|
| 309 tests | `pytest --collect-only -q` → 309 tests | ✅ confirmed |
| 16 test files | `ls tests/test_*.py \| wc -l` → 16 (excludes `conftest.py`) | ✅ confirmed |
| 36 benchmark cases | `tests/benchmark/cases/*.jsonl` → 35 SFT + 1 regression = 36 | ✅ confirmed |
| All tests pass | Fresh cache: `309 passed in 2.29s` | ⚠️ **conditional** — see D6-001 |

## Quality-gate snapshot at HEAD `c4ecd41` (fresh cache)

- `pytest tests/` → **309 passed in 2.29s** (fresh `./cache` directory only)
- `pytest tests/` (second run, polluted cache) → **1 failed, 308 passed** — see D6-001
- `coverage run --source=tra -m pytest` → **96% line coverage** (1637 stmts, 58 missed)
- `mutmut run` → **CRASHES** with `TypeError: can only concatenate list (not "str") to list` — see D6-002
- `ruff check .` → clean (per Tracks R6/B6)
- `mypy --strict tra` → 0 issues (per Tracks R6/B6)

## Summary

- **Findings: 20 total**
  - BLOCKING: 1 (D6-001 — failing test)
  - WARNING: 5 (D6-002, D6-003, D6-004, D6-005, D6-006)
  - INFO: 14 (D6-007 … D6-020)
- **Carry-over from R5 D5:** 4 (D6-002 ← TRA-D5-011, D6-006 ← TRA-D5-007, D6-010 ← TRA-D5-003, D6-014 ← TRA-D5-006)
- **New R6 findings:** 16
- **R5 test classes verified holding:** 8 of 23 (per-leaf, LLM-seam-DI, cache-HMAC, L2-e2e, CLI-runner, review-decision, type-safety residuals)
- **R5 test classes with defects:** 4 (mutation-config tests are superficial; HITL e2e tests are vacuous; TRA-A5-003 sub-tests have isolation + assertion bugs)

## Findings

### D6-001 — Failing test on polluted cache (test-isolation regression)

- **Severity:** BLOCKING
- **Finding type:** issue (test isolation)
- **Round 5 status:** NEW — latent regression introduced by R5 Batch 2 commit `36246bb` (TRA-A5-003 remediation); test was committed RED and never actually GREEN at HEAD `c4ecd41`. Commit message claims "pytest (250 passed in 1.76s)" but `git checkout 36246bb && pytest` produces 3 failures (test isolation + JSON decode error on stale audit file).

**Evidence:**

```
$ rm -rf cache cache.db && pytest tests/                        # first run
309 passed in 2.29s
$ pytest tests/                                                  # second run (cache polluted)
1 failed, 308 passed in 3.37s
FAILED tests/test_outstanding_findings.py::TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover::test_unknown_term_emits_exception_handler_audit_record
```

Failure message:

```
AssertionError: TRA-A5-003: UnknownTerm should emit an EXCEPTION_HANDLER audit record
with input_hash='UNKNOWN_TERM'. Got 0 EXCEPTION_HANDLER records, 0 with UNKNOWN_TERM code.
All records: ['ANALYZE_DOCUMENT', 'BUILD_GLOSSARY', 'BUILD_ENTITY_TABLE',
'TRANSLATE_SEGMENT', 'VERIFY_OUTPUT', 'VERIFY_OUTPUT']
```

- `tests/test_outstanding_findings.py:4086-4088` — `cfg = BootstrapConfig.from_yaml("config.yaml").model_copy(update={"audit_trace": audit_path})`. **Does NOT override `cache_directory`**, so the kernel uses the default `./cache` directory (a persistent `cache.db` SQLite file).
- `tra/isa.py:462-465` — `cached = cache.get(cache_key); if cached is not None: audit.append("TRANSLATE_SEGMENT", cache_key, cached.evidence_ids); return cached`. Cache hit short-circuits the rule path (lines 545-574) where the EXCEPTION_HANDLER record for `UNKNOWN_TERM` is emitted (line 558-574).
- First run: cache miss → rule path → EXCEPTION_HANDLER record emitted → test passes → cache entry written WITHOUT EXCEPTION_HANDLER record (the cache stores only the `TranslationResult`, not the audit records).
- Second run: cache hit → early return → no EXCEPTION_HANDLER record → test fails.

**Root cause:** The test does not use the shared `kernel_config` fixture (which overrides `cache_directory=str(tmp_path / "cache")`). It bypasses the fixture by calling `BootstrapConfig.from_yaml("config.yaml")` directly.

**Suggested fix:** Replace the inline config construction with the `kernel_config` fixture (or override `cache_directory=str(tmp_path / "cache")` in the `model_copy(update=...)` call). Same fix needed for the three sibling tests in `TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover` (lines 4086, 4124, 4165).

---

### D6-002 — `mutmut run` crashes; TRA-D5-011 / TRA-094 remediation is non-functional

- **Severity:** WARNING
- **Finding type:** issue (mutation-testing infrastructure)
- **Round 5 status:** TRA-D5-011 marked `fixed-and-verified` in `docs/audit/round6/track_r6_baseline.md` row 27 — **regression**: the configuration does not actually work with the installed mutmut 3.6.0.

**Evidence:**

`pyproject.toml:60-63`:
```toml
[tool.mutmut]
paths_to_mutate = "tra"
tests_dir = "tests"
max_stack_depth = 5
```

Runtime probe:

```
$ mutmut run --help
  File "/home/z/.venv/lib/python3.12/site-packages/mutmut/configuration.py", line 110, in _load_config
    pytest_add_cli_args_test_selection = s("pytest_add_cli_args_test_selection", []) + tests_dir
                                         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~
TypeError: can only concatenate list (not "str") to list
```

Both `paths_to_mutate` and `tests_dir` are **deprecated keys** in mutmut 3.6.0 (emits `UserWarning: The config paths_to_mutate is deprecated. Please rename it to source_paths`). Worse, `tests_dir = "tests"` (a string) is concatenated with a list (`s(...) + tests_dir`), which raises `TypeError` at config-load time. **`mutmut run` cannot even start.**

The R5 regression tests for TRA-D5-011 are superficial:
- `tests/test_outstanding_findings.py:4996-5007` `test_mutmut_in_dev_dependencies` — asserts `"mutmut" in pyproject` (string presence only).
- `:5009-5023` `test_mutmut_tool_section_configured` — asserts `"[tool.mutmut]" in pyproject` and `"paths_to_mutate" in pyproject` (string presence only).
- `:5025-5035` `test_mutation_testing_workflow_documented` — asserts `"mutmut" in skill.lower()` (string presence only).

None of the 3 tests actually runs `mutmut run` or otherwise verifies the configuration is functional. The R6 baseline's `fixed-and-verified` assessment is therefore based on the regression tests, which give false confidence.

**Suggested fix:** Update `pyproject.toml:60-63` to use the mutmut 3.x key names:

```toml
[tool.mutmut]
source_paths = ["tra"]
max_stack_depth = 5
```

(Drop `tests_dir` — mutmut 3.x auto-discovers tests via pytest.) Add a regression test that actually invokes `subprocess.run(["mutmut", "run", "--help"])` and asserts `returncode == 0` — that would have caught this regression.

---

### D6-003 — 15 hardcoded absolute paths in test_outstanding_findings.py

- **Severity:** WARNING
- **Finding type:** issue (test portability)
- **Round 5 status:** NEW — paths introduced incrementally across R5 Batches 2/5/A/G/H.

**Evidence:** `rg -n "/home/z/my-project/Translation-Runtime-Architecture" tests/` → 15 hits, all in `tests/test_outstanding_findings.py`:

| Line | Use |
|---|---|
| 3653, 3706, 3770, 5082 | `subprocess.run(..., cwd="/home/z/.../tra-prototype")` |
| 3729, 4202, 4252, 4280, 5001, 5014, 5030, 5055, 5192, 5217, 5246 | `Path("/home/z/.../tra-prototype/{tra,tests,pyproject.toml,SKILL.md}/...").read_text()` |

All 15 tests will FAIL on any other machine, in CI, or if the repo is cloned to a different path. The pattern `Path(__file__).resolve().parent.parent` (the prototype root) is already used by the very same file at lines 158, 233, 904, 1255, 4086's `config.yaml` sibling tests — so the fix is a mechanical search-and-replace.

**Suggested fix:** Replace `Path("/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/<X>")` with `Path(__file__).resolve().parent.parent / "<X>"` in all 15 sites. Replace `subprocess.run(..., cwd="/home/z/...")` with `subprocess.run(..., cwd=str(Path(__file__).resolve().parent.parent))`.

---

### D6-004 — Vacuous test: `test_entity_ambiguity_emits_exception_handler_audit_record`

- **Severity:** WARNING
- **Finding type:** issue (test assertion depth)
- **Round 5 status:** NEW — test added in R5 Batch 2 commit `36246bb` alongside the TRA-A5-003 remediation.

**Evidence:** `tests/test_outstanding_findings.py:4117-4153` — the test name and docstring claim it verifies an EXCEPTION_HANDLER audit record is emitted for `ENTITY_AMBIGUITY`, but the assertion block at lines 4144-4153 reads:

```python
# We don't strictly require ENTITY_AMBIGUITY on this particular input
# (it depends on regex overlap), but if any exception record exists,
# its exception_code should match a routable type.
# The real assertion: no direct recover_* bypass should occur.
# Check that no RECORD has a 'recovered_via_direct_call' marker.
for r in audit_records:
    snapshot = r.get("artifact_snapshot", {})
    assert "direct_call" not in str(snapshot).lower(), ...
```

The production code (`tra/isa.py`, `tra/kernel.py`, `tra/recovery.py`) never writes the literal string `"direct_call"` to any `artifact_snapshot`, so this assertion is **always true** regardless of whether `ENTITY_AMBIGUITY` actually emits an EXCEPTION_HANDLER record. The test passes vacuously — its name and docstring overstate what it verifies.

Cross-reference: R6 baseline row 4 (TRA-A5-003) is marked `partial` because "EntityAmbiguity still bypasses — `isa.py:388` calls `recover_entity_ambiguity(...)` directly with no audit record". The vacuous test makes this look fixed in CI but the underlying issue persists.

**Suggested fix:** Either (a) make the test actually assert `EXCEPTION_HANDLER` records for `ENTITY_AMBIGUITY` (which would require the production fix in `tra/isa.py:388` to emit the record), or (b) rename the test to `test_no_direct_call_markers_in_audit_trail` and update the docstring to match the actual assertion.

---

### D6-005 — Wrong field name `level` instead of `conformance_level` in `model_copy`

- **Severity:** WARNING
- **Finding type:** issue (test correctness)
- **Round 5 status:** NEW — test added in R5 Batch 2 commit `36246bb`.

**Evidence:** `tests/test_outstanding_findings.py:4165-4167`:

```python
cfg = BootstrapConfig.from_yaml("config.yaml").model_copy(
    update={"level": ConformanceLevel.L4_FORENSIC}
)
```

`BootstrapConfig` field is `conformance_level` (see `tra/config.py:46`), not `level`. Pydantic v2 `model_copy(update=...)` does NOT validate keys against the schema — it silently sets a new attribute `level` on the model instance:

```
>>> cfg2 = cfg.model_copy(update={"level": ConformanceLevel.L4_FORENSIC})
>>> cfg2.conformance_level      # the real field
<ConformanceLevel.L3_STRICT: 'L3_STRICT'>            # ← unchanged from default
>>> cfg2.level                  # the bogus attribute
<ConformanceLevel.L4_FORENSIC: 'L4_FORENSIC'>        # ← set but never read
```

So the test thinks it's testing `L4_FORENSIC` but is actually testing `L3_STRICT` (the default in `config.yaml`). The test passes accidentally because `L3_STRICT` also adds unknown terms to the ambiguity register — but if the production code ever introduces an L4-only behavior change for unknown terms, this test would silently miss it.

This is the same anti-pattern that TRA-047 (`tra/config.py:39-42`, `extra="forbid"`) was designed to catch at construction time — but `model_copy(update=...)` bypasses `extra="forbid"` (it's a Pydantic limitation; `extra="forbid"` only applies to `__init__`).

**Suggested fix:** Replace `"level"` with `"conformance_level"` at line 4166. Add a regression test asserting `model_copy(update={"level": ...})` raises (or warn) when given an unknown key — Pydantic v2 supports this via a custom validator on `__pydantic_init_subclass__`, or by always using `model_validate({**self.model_dump(), **update})` instead of `model_copy(update=...)`.

---

### D6-006 — HITL e2e tests use benign source; tests pass whether or not HITL fires

- **Severity:** WARNING
- **Finding type:** issue (test assertion depth)
- **Round 5 status:** TRA-D5-007 marked `fixed-and-verified` in R6 baseline row 10 — **regression**: tests are vacuous.

**Evidence:** `tests/test_outstanding_findings.py:4667-4742` — `TestTRA_D5_007InteractiveE2E` has 3 tests (`test_interactive_accept_uses_candidate`, `test_interactive_override_uses_reviewer_text`, `test_interactive_skip_keeps_candidate`). All 3 use:

```python
source = "# Test\n\nText.\n"
target = kernel.run(source)
assert target, "interactive=True with accept should produce output"
```

The source `"# Test\n\nText.\n"` is benign — it has no CJK tokens, no entity conflicts, no structural issues, so it does NOT trigger `Unrecoverable` in the repair loop. Without `Unrecoverable`, the HITL `review_decision` prompt is never called. The `monkeypatch.setattr("tra.hitl.Prompt.ask", ...)` is dead code in all 3 tests — it would only fire if `review_decision` were invoked, which it isn't.

The test docstrings explicitly acknowledge this:

```
test_interactive_override_uses_reviewer_text docstring (line 4719-4721):
"If HITL didn't fire because no Unrecoverable was raised, the
test still passes — the override path is exercised in the
unit test test_hitl_review_decision_override."
```

So the test name says "uses_candidate" / "uses_reviewer_text" / "keeps_candidate" but the assertions only check `target` is non-empty — they don't verify the HITL resolution path was actually invoked. The actual HITL behavior (accept/override/skip producing different outputs) is exercised only by the unit tests in `TestTRA_D5_004_005_ReviewDecisionCoverage` at lines 4747-4813.

Cross-reference: R6 baseline row 10 cites this class as evidence that TRA-D5-007 is `fixed-and-verified`. The remediation added the test class, but the test class does not actually exercise the e2e HITL path — it only exercises the kernel with `interactive=True` on a source that doesn't trigger HITL.

**Suggested fix:** Use the `--force-unrecoverable` flag (TRA-E5-005, available at the CLI layer) or a source that genuinely triggers `Unrecoverable` (e.g., a heading-count mismatch that survives `max_retries=3` repair attempts). Add `assert hitl_called` (using a counter or `monkeypatch.setattr` spy) to verify `review_decision` was actually invoked.

---

### D6-007 — Test isolation gaps in 4 TestTRA_A5_003 / TestTRA_E5_003 tests

- **Severity:** INFO
- **Finding type:** issue (test isolation)
- **Round 5 status:** NEW — tests added in R5 Batches 2/E commit `36246bb` / `57997a8`.

**Evidence:** Four tests in `tests/test_outstanding_findings.py` call `BootstrapConfig.from_yaml("config.yaml")` and override `audit_trace` but NOT `cache_directory`, polluting the shared `./cache` directory:

| Line | Test | Consequence |
|---|---|---|
| 4086 | `test_unknown_term_emits_exception_handler_audit_record` | **Failing test (D6-001)** |
| 4124 | `test_entity_ambiguity_emits_exception_handler_audit_record` | Pollutes `./cache`; test passes vacuously (see D6-004) |
| 4165 | `test_unknown_term_still_appears_in_ambiguity_register` | Pollutes `./cache`; also has wrong field name (D6-005) |
| 4857 | `test_empty_source_recovery_returns_blocking_severity` | Pollutes `./cache` and `./compilation_artifacts/` (default); test passes |

Cross-reference: `tests/conftest.py:82-99` defines the `kernel_config` fixture that properly isolates `cache_directory`, `compilation_dir`, `audit_trace`, and `base_dir` to `tmp_path`. The fixture is used by `test_kernel.py`, `test_benchmark.py`, `test_outstanding_findings.py:5272+` (per-leaf translation tests), and many other classes — but the 4 tests listed above bypass it. TRA-D5-008 (R6 baseline row 19, `fixed-and-verified`) was the original driver for the fixture; the 4 bypasses are residual inconsistencies.

**Suggested fix:** Convert all 4 tests to use the `kernel_config` fixture (accept it as a parameter, then `model_copy(update={...})` for any test-specific overrides). This also fixes D6-001, the wrong-field-name bug in D6-005, and the compilation_artifacts pollution in D6-009 (sibling).

---

### D6-008 — 3 tests in `test_isa.py` use shared `./cache` directory

- **Severity:** INFO
- **Finding type:** issue (test isolation)
- **Round 5 status:** persistent (not previously tracked in R5 register; pre-existing from earlier rounds).

**Evidence:** `rg -n 'TranslationCache\("./cache"' tests/test_isa.py` → 3 hits:

| Line | Test |
|---|---|
| 149 | `test_translate_segment_returns_translation_result` |
| 167 | `test_translate_segment_cache_hit_is_byte_identical` |
| 388 | `test_translate_segment_applies_zh_rule_layer` |

Each constructs `TranslationCache("./cache", enabled=True)` — the shared `./cache` directory. The tests pass (the cache content is benign — `TranslationResult` objects with `"Confirmed"` translations), but they pollute `./cache.db` and can affect later tests that don't isolate (see D6-001).

The cache-hit test at line 167 is especially fragile: it asserts `r2.cache_hit is True` after two consecutive calls — if the cache was already populated by an earlier test run, `r1.cache_hit` would also be `True` and the assertion would still pass (no behavioral difference), but the test's implicit assumption of a cold cache is violated.

**Suggested fix:** Replace `"./cache"` with `tmp_path / "cache"` in all 3 tests (accept `tmp_path: Path` as a fixture parameter). Also add a `conftest.py` autouse fixture that clears `./cache.db` and `./compilation_artifacts/` before each test session, as a defense-in-depth measure.

---

### D6-009 — `test_l4_forensic_trace_emitted_at_l4` doesn't override `cache_directory`

- **Severity:** INFO
- **Finding type:** issue (test isolation)
- **Round 5 status:** NEW — pre-existing test, not previously tracked.

**Evidence:** `tests/test_phase6_hardening.py:115-135`:

```python
def test_l4_forensic_trace_emitted_at_l4(tmp_path: Path):
    cfg = Path(__file__).resolve().parent.parent / "config.yaml"
    from tra.config import BootstrapConfig
    base = BootstrapConfig.from_yaml(cfg)
    base = base.model_copy(
        update={
            "base_dir": str(tmp_path),
            "conformance_level": ConformanceLevel.L4_FORENSIC,
            "audit_trace": str(tmp_path / "audit.jsonl"),
            "compilation_dir": str(tmp_path / "artifacts"),
        }
    )
    kernel = TRAKernel(base)
    kernel.run("# Title\n\n系统 成立 是 高度可信 的。\n")
```

The `update` dict overrides `base_dir`, `conformance_level`, `audit_trace`, and `compilation_dir` — but NOT `cache_directory`. Since `cache_directory` defaults to `"./cache"` and `base_dir` is now `tmp_path`, the path-safety validator at `tra/config.py:58-82` resolves `./cache` against `tmp_path` — so the cache IS isolated to `tmp_path/cache` (because the path-safety validator resolves relative paths against `base_dir`).

Wait — re-reading `tra/config.py:69-73`:

```python
candidate = (
    (base / raw_path).resolve()
    if not Path(raw_path).is_absolute()
    else Path(raw_path).resolve()
)
```

So `"./cache"` resolves to `tmp_path / "./cache"` = `tmp_path/cache`. The cache IS isolated. But this only works because `base_dir` is overridden — if `base_dir` were left at `"."` (the default), `"./cache"` would resolve to `./cache` (shared). The test accidentally relies on `base_dir` override for cache isolation. This is fragile.

**Suggested fix:** Explicitly override `"cache_directory": str(tmp_path / "cache")` in the `model_copy(update=...)` call (consistent with the `kernel_config` fixture pattern in `conftest.py:82-99`).

---

### D6-010 — `TestTRA033LLMSeamRobustness` weak assertion (TRA-D5-003 persistent)

- **Severity:** INFO
- **Finding type:** issue (test assertion depth — persistent from R5)
- **Round 5 status:** TRA-D5-003 marked `persistent` in R6 baseline row 7 — confirmed.

**Evidence:** `tests/test_outstanding_findings.py:411-509` — `TestTRA033LLMSeamRobustness` has 7 tests (5 parametrized + 2 explicit). Each asserts only `assert "Confirmed" in res.translation` (line 449, 477, 504) — they do NOT assert `len(translate_records) == 1` (the single-audit-record invariant for the degraded LLM path, per TRA-048). If a future mutation makes the early `return result` in `tra/isa.py:543` conditional on `isinstance(exc, RuntimeError | ValueError | TypeError)`, the `OSError`/`TimeoutError`/`None` paths would emit a second (non-degraded) audit record and 4 of the 7 tests would not catch it.

The supplementary `TestTRA088SingleAuditRecordAllExceptions` at `:2129-2221` covers only the empty-string + TypeError paths with the `len(translate_records) == 1` assertion, so the gap remains for the other 5 parametrized cases.

**Suggested fix:** Add `assert len(translate_records) == 1` to each of the 7 tests in `TestTRA033LLMSeamRobustness`. Estimated effort: ~30 minutes (per R6 baseline row 173 recommendation).

---

### D6-011 — Per-leaf translation + LLM interaction untested

- **Severity:** INFO
- **Finding type:** issue (test coverage gap)
- **Round 5 status:** NEW — TRA-001 Phase 8 per-leaf translation added in R5 Batch H commit `f782043`.

**Evidence:** `tra/kernel.py:585`:

```python
if self.ctx.structural_map is not None and llm_translate is None:
    # per-leaf translation path
    leaf_segments = list(self.ctx.structural_map.iter_leaf_segments())
    ...
else:
    # whole-doc translation (LLM or no structural map)
    result = translate_segment(translated, ..., llm_translate=llm_translate)
```

The per-leaf translation path is DISABLED when an LLM callback is supplied (`llm_translate is None` is the gate). This is a documented design decision (kernel.py:580-583 comment: "LLMs typically translate whole documents, and the caller's callback expects to receive the full source").

But no test verifies this design decision. If a future refactor enables per-leaf translation with an LLM (e.g., to improve cache granularity), no test would catch the behavior change. Conversely, if the gate is accidentally inverted (`llm_translate is not None` instead of `is None`), no test would catch the regression.

`TestTRA001_PerLeafSegmentTranslation` at `:5272-5406` exercises per-leaf translation only via the rule path (no `llm_translate=` kwarg). `TestTRA_D5_002_LLMSeamDependencyInjection` at `:4596-4662` exercises the LLM seam but does NOT verify the per-leaf path is bypassed.

Coverage report: `tra/kernel.py:639-650` (the "no leaf segments" fallback) and `:652-661` (the "no structural map" fallback) are both uncovered — these are the `else` branches that fire when the per-leaf path is NOT taken. The LLM + per-leaf gate itself (line 585) is covered (rule path uses it), but the LLM path's bypass of per-leaf is not asserted by any test.

**Suggested fix:** Add a test in `TestTRA_D5_002_LLMSeamDependencyInjection` that verifies: when `llm_translate` is supplied AND the source has multiple leaf segments, the LLM callback is invoked exactly once (whole-doc), not once-per-leaf. Example:

```python
def test_llm_translate_uses_whole_doc_not_per_leaf(self, kernel_config):
    call_count = 0
    def stub_llm(source_segment, ctx):
        nonlocal call_count
        call_count += 1
        return "STUB " + source_segment
    cfg = kernel_config.model_copy(update={"conformance_level": ConformanceLevel.L1_BASIC})
    kernel = TRAKernel(cfg)
    source = "# H\n\nPara 1.\n\nPara 2.\n"  # 3 leaf segments
    kernel.run(source, llm_translate=stub_llm)
    assert call_count == 1, f"LLM should be called once (whole-doc), got {call_count}"
```

---

### D6-012 — Hardcoded `/tmp/test_tra071*.jsonl` paths

- **Severity:** INFO
- **Finding type:** issue (test portability)
- **Round 5 status:** persistent (pre-existing from earlier rounds; not previously tracked).

**Evidence:** `tests/test_tra071_broken_markdown.py:26, 38`:

```python
audit = AuditTrail("/tmp/test_tra071.jsonl")          # line 26
audit = AuditTrail("/tmp/test_tra071_ok.jsonl")        # line 38
```

Hardcoded `/tmp/` paths are collision-prone in concurrent test runs (e.g., CI matrix) and violate the principle of test isolation. In this case the impact is minimal because `analyze_document` doesn't call `audit.flush()`, so the files are never written — but the paths are still fragile.

**Suggested fix:** Replace with `tmp_path / "audit.jsonl"` (accept `tmp_path: Path` as a fixture parameter).

---

### D6-013 — Coverage 96% (58 missing lines, mostly fallback paths)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** TRA-D5-011 / TRA-D5-013 area — verified-holding.

**Evidence:** `coverage run --source=tra -m pytest && coverage report`:

```
TOTAL                      1637     58    96%
```

Per-file breakdown (notable):

| File | Stmts | Miss | Cover | Missing lines (categories) |
|---|---|---|---|---|
| `tra/kernel.py` | 276 | 12 | 96% | 172, 206, 244, 323, 325, 442, 590, 593, **639-650** (per-leaf fallback paths), 771 |
| `tra/anchor.py` | 251 | 20 | 92% | 210, 228-229, 265, 286-293, 316, 319-322, 345, 348-351, 368 |
| `tra/isa.py` | 299 | 13 | 96% | 93, 114-115, 206, 264-265, 362, 793, 797, 800, 839, 1077, 1181 |
| `tra/cache.py` | 82 | 2 | 98% | 153, 179 (HMAC edge cases) |
| `tra/diagnostics.py` | 90 | 2 | 98% | 198, 208 (flush edge cases) |
| `tra/benchmark.py` | 70 | 3 | 96% | 93, 96, 109 (summary edge cases) |
| `tra/modules/registry.py` | 77 | 6 | 92% | 86-87, 133, 167, 173-174 (error paths) |

12 of 20 source files have 100% coverage. The missing lines are concentrated in:
1. Fallback paths (`kernel.py:639-650` — the "no leaf segments" / "no structural map" fallbacks, which are effectively dead code because markdown-it-py always produces at least one paragraph node).
2. Error-handling branches (`registry.py:86-87, 133, 167, 173-174` — duplicate-name and direction-conflict error paths partially uncovered).
3. Edge-case branches in `anchor.py` (table-cell handling, slug generation edge cases).

Coverage is good (96% line, with the gap concentrated in defensive fallback paths) but not 100%. R5 D5-011's target was "≥80% (target: 90%+)" — line coverage exceeds the target.

---

### D6-014 — Benchmark suite verified at 36 cases (TRA-D5-006 partial: target 100+)

- **Severity:** INFO
- **Finding type:** positive_verification (with caveat)
- **Round 5 status:** TRA-D5-006 marked `partial` in R6 baseline row 92 — confirmed (36 of 100+ target).

**Evidence:** `tests/benchmark/cases/*.jsonl`:

```
sft.jsonl: 35 cases        (categories S, F, T, D, E)
regression.jsonl: 1 case   (category R)
Total: 36 cases
```

`tests/test_benchmark.py:47` parametrizes over `_all_cases()` (36 cases) — each runs through the full pipeline and asserts `result.passed`. `test_l3_gate_zero_blocking_subset` at `:55-62` asserts `summary["blocking"] == 0` and `summary["failed"] == 0` across all 36 cases.

Category distribution:

| Category | Description | Count |
|---|---|---|
| S | Structural preservation | (in sft.jsonl) |
| F | Factual preservation | 5+ |
| T | Terminological consistency | 5+ |
| D | Diagnostics | 5+ |
| E | Entity preservation | 5+ |
| R | Regression (deterministic anchor) | 1 |
| **Total** | | **36** |

The suite is well-structured but short of the 100+ spec target. R5 D5-006 remains `partial`.

---

### D6-015 — Per-leaf translation tests verified holding (TRA-001 / TRA-A5-001)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** TRA-A5-001 marked `fixed-and-verified` in R6 baseline row 1 — confirmed.

**Evidence:** `tests/test_outstanding_findings.py:5272-5406` — `TestTRA001_PerLeafSegmentTranslation` (5 tests, all passing with fresh cache):

| Test | What it verifies |
|---|---|
| `test_structural_map_has_iter_leaf_segments_method` | `StructuralMap.iter_leaf_segments()` exists, yields `(int, StructuralNode)` tuples, kind ∈ {HEADING, PARAGRAPH, LIST_ITEM, TABLE_CELL}, text not None |
| `test_per_leaf_translation_preserves_glossary_substitution` | `成立` → `Confirmed` substitution fires per-leaf |
| `test_per_leaf_translation_preserves_entities` | `RustVMM` + `v0.5.0` preserved verbatim per-leaf |
| `test_per_leaf_translation_cache_key_differs_per_segment` | Multiple `TRANSLATE_SEGMENT` audit records emitted (≥2 for heading + 2 paragraphs) — proves per-leaf translation is invoked, not whole-doc |
| `test_per_leaf_translation_preserves_code_blocks` | Inline code `` `执行环境` `` protected from glossary substitution; prose `执行环境` translated to `execution environment` |

All 5 tests use the `kernel_config` fixture (proper `tmp_path` isolation). The tests are well-designed — they cover the API contract (`iter_leaf_segments`), behavioral correctness (glossary/entity preservation), the per-leaf invariant (multiple audit records), and a sanity check (code-block protection). The only gap is the LLM + per-leaf interaction (see D6-011).

---

### D6-016 — LLM seam DI tests verified holding (TRA-D5-002)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** TRA-D5-002 marked `fixed-and-verified` in R6 baseline row 9 — confirmed.

**Evidence:** `tests/test_outstanding_findings.py:4596-4662` — `TestTRA_D5_002_LLMSeamDependencyInjection` (3 tests, all passing):

| Test | What it verifies |
|---|---|
| `test_run_accepts_llm_translate_kwarg` | `inspect.signature(TRAKernel.run)` has `llm_translate` parameter |
| `test_run_uses_supplied_llm_translate` | When `llm_translate` is supplied, callback is invoked ≥1 time and its output appears in the kernel's target |
| `test_run_without_llm_translate_uses_rule_path` | When `llm_translate` is NOT supplied, the deterministic rule path applies the glossary (`成立` → `Confirmed`) |

All 3 tests use the `kernel_config` fixture (proper `tmp_path` isolation). The DI pattern replaces the fragile module-level monkeypatching (`kernel_mod.translate_segment = patched_translate`) that TRA-D5-002 originally flagged. The fix is clean and well-tested.

The only gap is the per-leaf + LLM interaction (D6-011) — but that's a separate concern from the DI pattern itself.

---

### D6-017 — Cache HMAC tests verified holding (TRA-B5-004 / TRA-079)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** TRA-B5-004 marked `fixed-and-verified` in R6 baseline row 26 — confirmed.

**Evidence:** `tests/test_outstanding_findings.py:4889-4981` — `TestTRA_B5_004_CacheHmacIntegrity` (4 tests, all passing):

| Test | What it verifies |
|---|---|
| `test_cache_set_stores_hmac_signature` | Raw stored value is `"{hmac}:{json}"`; HMAC is 64 hex chars (SHA256); JSON parses to the original `TranslationResult` |
| `test_cache_get_rejects_tampered_value` | Tampered JSON (with old HMAC) → `cache.get` returns `None` (cache miss) |
| `test_cache_get_returns_valid_entry` | Untampered entry → returned with `cache_hit=True` and correct `translation` |
| `test_cache_get_handles_old_unauthenticated_entries` | Old-format entry (no HMAC prefix) → treated as cache miss (graceful migration, no crash) |

All 4 tests use `tmp_path` (proper isolation). The test design is excellent — covers the write path, the tamper-detection path, the happy path, and the migration path. The HMAC implementation in `tra/cache.py:34-50, 134-168` is properly tested.

---

### D6-018 — Mutation testing config tests present but superficial (TRA-D5-011)

- **Severity:** INFO
- **Finding type:** issue (test assertion depth)
- **Round 5 status:** TRA-D5-011 marked `fixed-and-verified` in R6 baseline row 27 — **regression**: tests verify string presence only, not functional config.

**Evidence:** `tests/test_outstanding_findings.py:4986-5036` — `TestTRA_D5_011_MutationTestingConfigured` (3 tests, all passing):

| Test | What it verifies | Adequacy |
|---|---|---|
| `test_mutmut_in_dev_dependencies` | `"mutmut" in pyproject_text` | String presence — would pass even if `mutmut` were a comment |
| `test_mutmut_tool_section_configured` | `"[tool.mutmut]" in pyproject_text` AND `"paths_to_mutate" in pyproject_text` | String presence — would pass even with deprecated/broken key names |
| `test_mutation_testing_workflow_documented` | `"mutmut" in skill_text.lower()` | String presence — would pass even with no actual workflow documentation |

None of the 3 tests invoke `subprocess.run(["mutmut", "run", "--help"])` or otherwise verify the configuration is functional. As shown in D6-002, the actual `mutmut run` crashes with `TypeError` because `tests_dir = "tests"` (string) is concatenated with a list internally. The R6 baseline's `fixed-and-verified` assessment for TRA-D5-011 is therefore based on tests that give false confidence.

**Suggested fix:** Add a 4th test:

```python
def test_mutmut_run_is_invokable(self):
    """RED: `mutmut run --help` must exit 0 (config loads without error)."""
    import subprocess
    result = subprocess.run(
        ["mutmut", "run", "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"mutmut run --help failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
```

This test would have caught the broken config in D6-002.

---

### D6-019 — `e2e_test.py` is a standalone script, not a pytest test (TRA-D5-009)

- **Severity:** INFO
- **Finding type:** positive_verification (with caveat)
- **Round 5 status:** TRA-D5-009 marked `fixed-and-verified` in R6 baseline row 93 — confirmed (DI pattern adopted), but script remains as a non-pytest artifact.

**Evidence:** `tra-prototype/e2e_test.py` (95 lines) — uses the DI pattern (`kernel.run(source, llm_translate=manual_llm)` at line 67) but is a standalone Python script with `print()` statements, no `assert` statements, and no pytest integration. It is NOT counted in the 309-test total.

The script is functionally redundant with `tests/test_e2e_to_translate.py::TestE2EToTranslateL3` (which uses the same DI pattern and adds proper assertions). The script's only value is as a manual smoke-test entry point (`python e2e_test.py`).

**Suggested fix:** Either (a) delete `e2e_test.py` (the pytest version covers the same ground with assertions), or (b) document it explicitly as a manual smoke-test script in `README.md` and add a `if __name__ == "__main__":` guard. Option (a) is preferred for hygiene.

---

### D6-020 — Test count 309/16 verified (TRA-C5-001)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** TRA-C5-001 marked `fixed-and-verified` in R6 baseline row 13 — confirmed.

**Evidence:**

```
$ pytest --collect-only -q | tail -20
tests/test_anchor.py: 7
tests/test_benchmark.py: 39
tests/test_e2e_to_translate.py: 12
tests/test_isa.py: 17
tests/test_kernel.py: 7
tests/test_modules.py: 17
tests/test_outstanding_findings.py: 161
tests/test_phase0.py: 11
tests/test_phase6_hardening.py: 6
tests/test_recovery.py: 9
tests/test_reporting.py: 5
tests/test_tra043_protocol.py: 3
tests/test_tra047_config_robustness.py: 2
tests/test_tra071_broken_markdown.py: 2
tests/test_utils.py: 7
tests/test_validate.py: 4
                                                    ← 16 test files (conftest.py excluded)
                                                    ← 309 tests total
```

Per-file distribution:
- `test_outstanding_findings.py` carries the majority (161 tests, 71 classes — up from R5's 46 classes due to R5 Batches A–H adding 25 new classes).
- `test_benchmark.py` has 39 tests (35 parametrized cases + 4 meta-tests — up from R5's 28 due to the 36-case parametrization).
- Remaining 14 files have 2-17 tests each.

The "309 across 16 test files" claim in the task brief is verified. All 4 docs (`CLAUDE.md:59`, `AGENTS.md:41`, `tra-prototype/README.md:152`, `tra-prototype/SKILL.md:252`) agree.

---

## Cross-reference summary

| Finding | R5 origin | R6 baseline status | D6 status |
|---|---|---|---|
| D6-001 | NEW (R5 Batch 2 `36246bb` introduced) | not tracked | BLOCKING — failing test |
| D6-002 | TRA-D5-011 / TRA-094 | fixed-and-verified | WARNING — config broken, mutmut run crashes |
| D6-003 | NEW (R5 Batches 2/5/A/G/H) | not tracked | WARNING — 15 hardcoded paths |
| D6-004 | NEW (R5 Batch 2 `36246bb`) | not tracked | WARNING — vacuous test |
| D6-005 | NEW (R5 Batch 2 `36246bb`) | not tracked | WARNING — wrong field name |
| D6-006 | TRA-D5-007 | fixed-and-verified | WARNING — vacuous tests (benign source) |
| D6-007 | NEW (R5 Batches 2/E) | not tracked | INFO — test isolation gaps |
| D6-008 | pre-existing | not tracked | INFO — test_isa.py shared cache |
| D6-009 | pre-existing | not tracked | INFO — test_phase6 cache_directory gap |
| D6-010 | TRA-D5-003 | persistent | INFO — weak assertion, persistent |
| D6-011 | NEW (R5 Batch H `f782043`) | not tracked | INFO — per-leaf + LLM untested |
| D6-012 | pre-existing | not tracked | INFO — hardcoded /tmp paths |
| D6-013 | TRA-D5-011 area | verified-holding | INFO — 96% coverage verified |
| D6-014 | TRA-D5-006 | partial | INFO — 36 of 100+ cases |
| D6-015 | TRA-A5-001 / TRA-001 | fixed-and-verified | INFO — per-leaf tests verified |
| D6-016 | TRA-D5-002 | fixed-and-verified | INFO — LLM seam DI tests verified |
| D6-017 | TRA-B5-004 / TRA-079 | fixed-and-verified | INFO — cache HMAC tests verified |
| D6-018 | TRA-D5-011 / TRA-094 | fixed-and-verified | INFO — mutation config tests superficial |
| D6-019 | TRA-D5-009 | fixed-and-verified | INFO — e2e_test.py redundant but uses DI |
| D6-020 | TRA-C5-001 | fixed-and-verified | INFO — 309/16 verified |

## Recommended next actions (priority order)

1. **D6-001 (BLOCKING)** — Fix the failing test by adding `"cache_directory": str(tmp_path / "cache")` to the `model_copy(update=...)` call at `tests/test_outstanding_findings.py:4086`. Same fix for the 3 sibling tests at lines 4124, 4165, 4857. Estimated effort: 15 minutes.

2. **D6-002 + D6-018 (WARNING)** — Update `pyproject.toml:60-63` to use mutmut 3.x key names (`source_paths = ["tra"]`, drop `tests_dir`). Add a `test_mutmut_run_is_invokable` regression test that actually runs `mutmut run --help`. Estimated effort: 30 minutes.

3. **D6-005 (WARNING)** — Replace `"level"` with `"conformance_level"` at `tests/test_outstanding_findings.py:4166`. Estimated effort: 5 minutes.

4. **D6-003 (WARNING)** — Replace 15 hardcoded `/home/z/my-project/...` paths with `Path(__file__).resolve().parent.parent / ...`. Estimated effort: 30 minutes (mechanical search-and-replace).

5. **D6-006 (WARNING)** — Rewrite `TestTRA_D5_007InteractiveE2E` tests to use a source that actually triggers `Unrecoverable` (or use the `--force-unrecoverable` CLI flag). Add `assert hitl_called` spy. Estimated effort: 1 hour.

6. **D6-004 (WARNING)** — Either fix the production code (`tra/isa.py:388` to emit EXCEPTION_HANDLER for ENTITY_AMBIGUITY) and tighten the test assertion, OR rename the vacuous test to match what it actually verifies. Estimated effort: 1 hour (production fix) or 15 minutes (test rename).

7. **D6-007 / D6-008 / D6-009 (INFO)** — Convert the 4 + 3 + 1 = 8 tests to use `tmp_path` for `cache_directory`. Estimated effort: 1 hour.

8. **D6-010 (INFO, persistent)** — Add `assert len(translate_records) == 1` to the 7 `TestTRA033LLMSeamRobustness` tests. Estimated effort: 30 minutes.

9. **D6-011 (INFO)** — Add a test verifying LLM + per-leaf interaction (LLM called once for whole-doc, not per-leaf). Estimated effort: 30 minutes.

10. **D6-012 (INFO)** — Replace `/tmp/test_tra071*.jsonl` with `tmp_path / "audit.jsonl"`. Estimated effort: 5 minutes.

11. **D6-014 (INFO, partial)** — Expand benchmark suite from 36 → 100+ cases per the R5 remediation plan §4.4. Estimated effort: ~16 hours (76 new cases).
