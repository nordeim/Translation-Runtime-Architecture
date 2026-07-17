# TRA Round 4 — Comprehensive TDD Remediation Plan

**Created:** 2026-07-17
**Based on:** Round 4 audit (47 issues: 1 BLOCKING / 11 WARNING / 35 INFO; plus 19 positive verifications)
**Approach:** TDD (Red → Green → Refactor → Commit) per finding
**Codebase:** `/home/z/my-project/Translation-Runtime-Architecture/` at HEAD `805a8f8`

## Remediation Strategy

Findings are grouped into 5 batches by priority and dependency. Each batch is a milestone (commit + push). Within each batch, fixes are independent and can be applied in sequence.

**Batch 1 — BLOCKING doc fix (TRA-C4-013)** — user-facing onboarding break
**Batch 2 — Documentation refresh (Track C4 cluster)** — 17 stale doc claims across 6 files
**Batch 3 — Code quality fixes (TRA-A4-011, TRA-B4-009, TRA-D4-014, TRA-D4-015, TRA-F4-006, TRA-F4-007)** — dead code, redundant scripts, missing tests, edge-case crashes
**Batch 4 — Persistent spec-conformance gaps (TRA-001, TRA-038, TRA-072, TRA-042, TRA-099)** — the Phase 8 sprint
**Batch 5 — Test suite gaps (TRA-D4-006, TRA-D4-007, TRA-D4-011)** — benchmark coverage, mutation testing, e2e gaps
**Deferred** — TRA-040 (EXCEPTION_HANDLER as KernelState — intentional design decision; needs spec change first)

---

## Batch 1: BLOCKING Doc Fix (Milestone 2)

### 1.1 TRA-C4-013: tra-prototype/README.md "Commands" section uses bare `tra_cli.py` invocations

**Root cause:** `tra-prototype/README.md:23-36` shows commands like `tra_cli.py translate doc.md --level L3 -o doc.en.md`. But `tra_cli.py` is mode 664 (not executable), has no shebang line, and there's no `[project.scripts]` entry point in `pyproject.toml`. So the commands fail with "command not found" or "permission denied".

**Optimal fix:** Replace all bare `tra_cli.py <subcommand>` invocations with `python -m tra_cli <subcommand>` (matching the root `README.md` and `SKILL.md`).

**TDD steps:**
1. RED: Shell-test that `tra_cli.py translate --help` fails (exit code != 0) — captures the broken state.
2. GREEN: Edit `tra-prototype/README.md` to use `python -m tra_cli` everywhere (4 invocation sites in §"Commands").
3. GREEN: Shell-test that `python -m tra_cli translate --help` succeeds (exit code 0).
4. COMMIT.

**Files touched:**
- `tra-prototype/README.md` — 4 invocation edits

**Estimated effort:** 30 minutes

---

## Batch 2: Documentation Refresh (Milestone 3)

### 2.1 TRA-C4-001 + TRA-C4-002: CLAUDE.md + tra-prototype/README.md TRA-017 entries

**Root cause:** Both docs claim "TRA-017 persistent: litellm, structlog, pydantic-settings, mdit-py-plugins, black, pytest-asyncio are listed but unused." Commit `a3cd2c1` removed all 6 from `pyproject.toml`. The claim is materially wrong.

**Fix:** Remove or update the TRA-017 entry in both docs to say "FIXED in Round 3 remediation commit `a3cd2c1`."

### 2.2 TRA-C4-003 + TRA-C4-004: SKILL.md §7 test count + test ID list

**Root cause:** SKILL.md §7 says "174 tests across 16 test files." Actual at HEAD `805a8f8` is **199 tests across 18 test files** (14.4% drift). The TDD-regression test ID list (line 245-247) lists 22 IDs but actual is 34; includes phantom `TRA-044` (test was renamed) and omits 13 real test classes added during R3 remediation (`TestTRA047`, `TestTRA048`, `TestTRA049`, `TestTRA050`, `TestTRA051`, `TestTRA053`, `TestTRA054`, `TestTRA071`, `TestTRA073`, `TestTRA075`, `TestTRA076`, `TestTRA077`, `TestTRA078`, `TestTRA093`, `TestTRA096`, `TestTRA097`, `TestTRA098`).

**Fix:** Update §7 to say "199 tests across 18 test files." Regenerate the test ID list by running `rg "^class Test" tests/test_outstanding_findings.py` and pasting the result.

### 2.3 TRA-C4-005: SKILL.md §8 "Audit remediation status" — TRA-016/017/026 listed as unfixed

**Root cause:** SKILL.md §8 "Remaining 24 Round 2 findings (not yet fixed)" lists TRA-016, TRA-017, TRA-026 — but all 3 are FIXED at HEAD. The same file internally contradicts itself at line 265 ("TRA-017 fixed in Round 3").

**Fix:** Move TRA-016/017/026 out of the "Remaining" list and into the "Fixed" list. Update the "Remaining" count (was 24, now 21).

### 2.4 TRA-C4-006 + TRA-C4-007: SKILL.md + tra-prototype/README.md "Audit artifacts" sections

**Root cause:** Both sections reference only Round 1 and Round 2 audit deliverables. Round 3 deliverables (landed after these docs were last revised) are omitted. Round 4 deliverables don't exist yet at audit time.

**Fix:** Add Round 3 references (`docs/audit/round3/` — `TRA_Prototype_Audit_Report_r3.docx`, `TRA_audit_findings_register_r3.xlsx`, `TRA_audit_severity_heatmap_r3.png`, `master_findings_register_r3.json`, `remediation_plan.md`). After Batch 2 lands, also add Round 4 references.

### 2.5 TRA-C4-008: status.md STALE banner itself is stale

**Root cause:** `status.md:1` banner says "actual test count at HEAD is 174+ (see `tra-prototype/SKILL.md` §7 for current count)". Actual is 199. The banner's "174+" claim is itself stale.

**Fix:** Either (a) update the banner to "199+", or (b) delete `status.md` entirely (it's a frozen historical session log; the banner is the only useful content; the body below is a commit log from commit `4d97aa1` that has no current value).

### 2.6 TRA-C4-009 + TRA-C4-010 + TRA-C4-011 + TRA-C4-012: implementation_plan.md staleness

**Root cause:**
- "File Structure Summary" missing 6 modules (`benchmark.py`, `hitl.py`, `validate.py`, `config.py`, `recovery.py`, `reporting.py`) and 5 test files (`test_tra043_protocol.py`, `test_tra047_config_robustness.py`, `test_tra071_broken_markdown.py`, `test_e2e_to_translate.py`, `run_e2e_translation.py`).
- "Dependencies" table lists 15 packages — 6 of them (`litellm`, `structlog`, `pydantic-settings`, `mdit_py_plugins`, `pytest-asyncio`, `black`) were removed from `pyproject.toml`.
- Phase 0.1.5 subcommand parenthetical lists 3 subcommands — actual CLI has 4 (missing `validate`).
- Phase 0.1.2 mentions "formatting (black)" — black was removed; ruff handles formatting.

**Fix:** Regenerate the "File Structure Summary" by `find tra-prototype -name '*.py' | sort`. Update the "Dependencies" table to match `pyproject.toml`. Update Phase 0.1.5 to list 4 subcommands. Update Phase 0.1.2 to say "formatting (ruff format)".

### 2.7 TRA-C4-013 (BLOCKING) — already in Batch 1

### 2.8 TRA-C4-014: SKILL.md §8 "Round 1 carry over" claim

**Root cause:** SKILL.md §8 "Round 1 carry over" still lists "TRA-016 persistent dead code, TRA-017 persistent unused deps, TRA-026 persistent dead config" — all 3 are now FIXED.

**Fix:** Update the "Round 1 carry over" line to reflect current status.

### 2.9 TRA-C4-015 + TRA-C4-016 + TRA-C4-017: residual staleness

- TRA-C4-015: tra-prototype/README.md "Known gaps" TRA-006 entry — exact opposite of code reality (carry-over from R3).
- TRA-C4-016: tra-prototype/README.md "Known gaps" TRA-004 entry retains misleading "EntityAmbiguity now routes through `_recover`" phrase (carry-over from R3).
- TRA-C4-017: AGENTS.md "Files and roles" table omits 7+ meta-docs and the prototype's own SKILL.md/README.md (carry-over from R2).

**Fix:** Update each to match code reality. For TRA-006, change "not invoked" to "invoked for 1 conflict pair (TRA-072 partial)". For TRA-004, soften "EntityAmbiguity now routes through `_recover`" to "EntityAmbiguity exception class + recovery procedure defined; not yet raised in production (TRA-038 partial)". For AGENTS.md, add the missing meta-docs to the "Files and roles" table.

**Estimated effort (Batch 2 total):** 4 hours

---

## Batch 3: Code Quality Fixes (Milestone 4)

### 3.1 TRA-A4-011 + TRA-B4-007 + TRA-D4-012: Dead `repaired = repaired` no-op at `isa.py:654`

**Root cause:** In `repair_segment`'s entity branch, `repaired = repaired` is a no-op self-assignment (parallel to TRA-073's `out = out` in `_rule_translate`). R3's TRA-073 fix was scoped to `_rule_translate` only, missing the same pattern in `repair_segment`. Pre-existed since initial commit `84753ad`. No test would have caught it.

**Optimal fix:** Remove the dead line. Add a regression test that asserts no `= repaired` self-assignment exists in `isa.py` (static check, parallel to TRA-073's test).

**TDD steps:**
1. RED: `rg "= repaired\b.*= repaired\b" tra/isa.py` — currently matches at line 654.
2. GREEN: Remove the line; re-run the grep — no matches.
3. Add a regression test class `TestTRA_A4_011_RepairedNoop` with a static check.
4. COMMIT.

**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`

### 3.2 TRA-B4-009 + TRA-D4-013: TRA-016/017/026 silently remediated with no regression tests

**Root cause:** R4 baseline verified TRA-016/017/026 are FIXED, but only via static `rg` checks — no automated regression test class. If someone re-introduces `count_blocking`, `cache.expire`, or the 6 unused deps, no test will fail.

**Optimal fix:** Add 3 regression test classes:
- `TestTRA016CountBlockingGone` — asserts `AuditTrail` has no `count_blocking` attribute.
- `TestTRA017UnusedDepsGone` — parses `pyproject.toml` and asserts the 6 packages are NOT in `dependencies`.
- `TestTRA026CacheExpireGone` — asserts `BootstrapConfig` has no `cache_expire` field.

**Files touched:** `tests/test_outstanding_findings.py`

### 3.3 TRA-D4-014: Redundant manual e2e script duplicates `test_e2e_to_translate.py`

**Root cause:** Commit `805a8f8` added `tests/run_e2e_translation.py` (186 LOC) — a manual e2e script that duplicates `tests/test_e2e_to_translate.py` (the pytest-collected version). Worse, it uses the same fragile module-level `monkeypatch` of `tra.isa._rule_translate` that TRA-090 was supposed to eliminate.

**Optimal fix:** Delete `tests/run_e2e_translation.py`. The pytest-collected `test_e2e_to_translate.py` is the canonical e2e test. If a manual demo script is wanted, restore the older `e2e_test.py` at the prototype root (which was the original manual demo, less fragile than the new one).

**Files touched:** `tests/run_e2e_translation.py` (delete)

### 3.4 TRA-D4-015: Structural repair branch is dead code

**Root cause:** `isa.py:663-666` has a branch in `repair_segment` that handles "structural" violations, but `verify_output` (the only producer of `Diagnostic` objects with `subsystem="structural"`) only emits heading-count diagnostics — and `repair_segment`'s structural branch handles table/list/code-block repairs that are never triggered. Coverage report shows 0% on lines 663-666.

**Optimal fix:** Either (a) delete the dead structural branch (simplest), or (b) wire `verify_output` to emit richer structural diagnostics (table row/col, list nesting, etc.) — this is part of the TRA-042 fix in Batch 4. Recommend (a) for now; (b) lands with TRA-042.

**Files touched:** `tra/isa.py`

### 3.5 TRA-F4-006: Minimal `ModuleInterface` (defaults only) crashes `TRAKernel` construction

**Root cause:** `ModuleInterface` (in `registry.py`) is a dataclass with 7 Callable fields. If a caller constructs `ModuleInterface()` with no args (relying on defaults), the defaults are `lambda *a, **kw: {}` etc. — but `TRAKernel.__init__` calls `module.get_style_profile()` and assigns the result to `RuntimeContext.style_profile`, which is a Pydantic model that validates the shape. The lambda default returns `{}`, which fails Pydantic validation.

**Optimal fix:** Make `ModuleInterface` fields required (no defaults), OR validate the return shape in `register()`.

**Files touched:** `tra/modules/registry.py`

### 3.6 TRA-F4-007: `_select_module` silent dispatch on same-source-lang collisions

**Root cause:** `kernel.py:_select_module` filters the registry by source language (e.g., `fr`) and returns the FIRST match. If two modules are registered with `fr -> en` and `fr -> de`, the second is silently unreachable. The user's `--lang fr-de` would silently use the `fr -> en` module.

**Optimal fix:** Filter by FULL direction (e.g., `fr -> en`), not just source language. If no exact match, fall back to source-only match with a WARNING audit record.

**Files touched:** `tra/kernel.py`

**Estimated effort (Batch 3 total):** 6 hours

---

## Batch 4: Persistent Spec-Conformance Gaps (Milestone 5 — Phase 8 Sprint)

### 4.1 TRA-001 / TRA-A4-001: TRANSLATE_SEGMENT operates on whole document

**Root cause:** `_execute_translation` (kernel.py:434-478) extracts fenced/inline code blocks as placeholders, then calls `translate_segment(protected, ...)` ONCE on the entire protected source. Spec §3 TRANSLATE_SEGMENT Inputs say "Source Segment" (leaf-level). Consequences: per-document cache keys (not per-segment); `RepairAttempt.segment_index` always 0; `evidence_trace.jsonl` uses substring containment, producing orphan lines.

**Optimal fix:** Refactor `_execute_translation` to walk `ctx.structural_map.nodes`, identify leaf segments (`NodeKind.PARAGRAPH`, `LIST_ITEM`, `TABLE_CELL`, `HEADING`), call `translate_segment` per leaf, then re-assemble the target via the structural map. Pass the leaf's index to `repair_segment` so `RepairAttempt.segment_index` is meaningful. Update `reporting.line_by_line_trace` to map line → structural node → evidence chain.

**TDD steps:** 5-7 RED-GREEN cycles (one per leaf kind, plus assembly + repair index + line-by-line trace).
**Files touched:** `tra/kernel.py`, `tra/isa.py`, `tra/reporting.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 16 hours

### 4.2 TRA-038 / TRA-A4-003: 3 of 5 TRA-EXCEPTION types never raised in production

**Root cause:** `UnknownTerm`, `CertaintyConflict`, `EntityAmbiguity` are defined + routable, but never raised. The R3 remediation commit `632bed2` honestly deferred auto-detection ("requires careful calibration of what counts as 'unknown' vs common particles").

**Optimal fix:**
- `UnknownTerm`: In `isa.py:_rule_translate`, when a CJK token (Unicode range `\u4e00-\u9fff`) has no glossary/entity/epistemic match and is not in a no-translate zone, raise `UnknownTerm`. Maintain a stop-word list (的/是/在/了/和/与/或/及/etc.) to avoid false positives.
- `CertaintyConflict`: In `translate_segment`'s LLM path, compare LLM output against `EPISTEMIC_LEXICON` and raise if the LLM returns a forbidden target (e.g., "valid" for source `成立`).
- `EntityAmbiguity`: In `anchor.py` entity extraction, when a token matches multiple entity patterns (e.g., both `PRODUCT_RE` and an acronym), raise `EntityAmbiguity`.

**TDD steps:** One RED-GREEN cycle per exception type (3 cycles), plus a stop-word calibration test.
**Files touched:** `tra/isa.py`, `tra/anchor.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 8 hours

### 4.3 TRA-072 / TRA-A4-002: PolicyResolver universal arbitration

**Root cause:** `_POLICY_RESOLVER.wins()` is called exactly ONCE in production (`verify_output`'s TERMINOLOGICAL vs FLUENCY check). Spec §5.2 mandates universal arbitration. All other severity decisions use hard-coded conditionals.

**Optimal fix:** Identify all severity-decision points in `verify_output` and `repair_segment`, route each through `_POLICY_RESOLVER.wins(offended_priority, competing_priority)`. Document the 15 priority pairs.

**TDD steps:** RED test that monkeypatches `_POLICY_RESOLVER.wins` to return different priorities and asserts severity changes for each pair.
**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 6 hours

### 4.4 TRA-042 / TRA-A4-005: Structural verification heading-count-only

**Root cause:** `verify_output` structural check is ONLY `_HEADING_RE.findall` count match. No checks for table row/col, list nesting, blockquote, HR, code-block fence count. `NodeKind` enum already carries the rich node-kind info but `verify_output` ignores it.

**Optimal fix:** In `verify_output`, walk `ctx.structural_map.nodes` and count nodes by `NodeKind`. Recompute the same counts from the target via a fresh `build_structural_map(target)` call. Raise a BLOCKING diagnostic per mismatch.

**TDD steps:** One RED-GREEN cycle per check type (5 cycles: table, list, blockquote, HR, code fence).
**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 8 hours

### 4.5 TRA-099 / TRA-A4-006 / TRA-F4-004: CLI `--registry` flag

**Root cause:** `tra_cli.py translate` constructs `TRAKernel(cfg, interactive=interactive)` with no `registry=` kwarg. The user's `--lang fr-en` is silently overridden by the ZHENModule fallback.

**Optimal fix:** Add `--registry` CLI flag (or auto-build the default registry in the CLI). Construct `TRAKernel(cfg, registry=registry, interactive=interactive)`.

**TDD steps:** RED test that runs `python -m tra_cli translate ... --lang fr-en` with a stub `fr-en` module registered; assert the stub's glossary is used (not ZHENModule's).
**Files touched:** `tra_cli.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 4 hours

**Estimated effort (Batch 4 total):** 42 hours (5.25 person-days)

---

## Batch 5: Test Suite Gaps (Milestone 6)

### 5.1 TRA-D4-006 / TRA-092: Benchmark suite at 22/100+ spec target

**Root cause:** Only 22 benchmark cases (S:5/F:5/T:5/D:4/E:2/R:1) — 22% of spec's 100+ target. S-03 (inline code vs prose) and E-03 (broken source markdown) still missing. No growth across 3 audit rounds.

**Optimal fix:** Add S-03 and E-03 first (closes the spec-required minimum). Then add 78 more cases across S/F/T/D/E categories to reach 100+.

**Files touched:** `tests/benchmark/cases/sft.jsonl`
**Estimated effort:** 12 hours (for 100+ cases)

### 5.2 TRA-D4-007 / TRA-091: `interactive=True` kernel path untested end-to-end

**Root cause:** No e2e test of the `--interactive` CLI flag. The HITL path is exercised only by unit tests of `review_decision`.

**Optimal fix:** Add an e2e test that pipes simulated stdin to `python -m tra_cli translate ... --interactive` and asserts the HITL prompt + accept/override/skip outcomes.

**Files touched:** `tests/test_outstanding_findings.py`
**Estimated effort:** 4 hours

### 5.3 TRA-D4-011 / TRA-094: Mutation testing framework deferred

**Root cause:** No mutation testing in the test suite. R3 deferred this; R4 confirms still deferred.

**Optimal fix:** Integrate `mutmut` or `cosmic-ray`. Run on `tra/` package. Add a CI job that runs mutation testing on every PR and fails if mutation score < 80%.

**Files touched:** `pyproject.toml`, `.github/workflows/mutation.yml` (new)
**Estimated effort:** 8 hours

**Estimated effort (Batch 5 total):** 24 hours (3 person-days)

---

## Deferred

### TRA-040 / TRA-A4-003: EXCEPTION_HANDLER and HALT_ERROR not modeled as KernelStates

**Status:** Intentional design decision. Spec §2.1's stateDiagram shows EXCEPTION_HANDLER as a state, but the implementation treats it as a side-channel audit-record type. The spec is ambiguous; resolving this requires a spec change first (either update spec §2.1 to say EXCEPTION_HANDLER is an action, not a state, or update the implementation to add 2 new KernelStates). Recommend deferring until spec author weighs in.

### TRA-079 / TRA-B4-004: Cache HMAC integrity

**Status:** INFO, deferred from R3. Cache now stores JSON (TRA-077), which is safe from RCE, but an attacker who can write to the cache directory could still inject bogus translations. HMAC would close this. Lower priority because the cache directory is assumed trusted (single-user dev environment).

---

## Validation Plan

After each batch:
1. Run all 4 quality gates: `ruff format --check . && ruff check . && mypy --strict tra && pytest tests -q`
2. All gates must be green.
3. Test count should increase (new regression tests added).
4. Commit + push via SSH wrapper.

After all batches:
1. Re-run Track R5 baseline — confirm all R4 fixes hold.
2. Re-run Track E5 probes — confirm TRA-013 byte-reproducibility still holds.
3. Final commit + push.

---

## Effort Estimate

| Batch | Findings | Est. Hours |
|---|---|---|
| 1 (BLOCKING doc) | 1 | 0.5 |
| 2 (Doc refresh) | 13 | 4 |
| 3 (Code quality) | 6 | 6 |
| 4 (Spec conformance) | 5 | 42 |
| 5 (Test suite) | 3 | 24 |
| **Total** | **28** | **76.5 hours (9.6 person-days)** |

Plus 19 positive verifications (no action needed — they confirm things are working).

The 18 INFO findings not assigned to a batch are either cosmetic (doc typos, minor wording) or are positive verifications already in the "Fixed" state. They can be addressed opportunistically during other batches.
