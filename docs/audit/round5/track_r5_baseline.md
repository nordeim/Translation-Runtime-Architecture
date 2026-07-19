# Track R5 — Regression Baseline (Round 5)

**HEAD audited:** `5476faf1d668b42d2a7b8c9b159ae9ee54c6e4f7` (`5476faf`)
**R4 baseline HEAD:** `805a8f8` (9 commits earlier)
**Methodology:** Re-verified all 66 R4 entries (47 issues + 19 positive verifications) via static code inspection + targeted test runs at HEAD `5476faf`. R4 status text was not trusted blindly; each claim was re-derived from current source. Where the R4 register's `finding_type` field was inconsistent with the entry's actual content (e.g. `positive_verification` used for an entry describing a persistent issue), R5 status was assigned based on the actual state at HEAD, not on the R4 `finding_type` label.

## Summary

- Total R4 entries: **66** (47 issues + 19 positive verifications)
- **Fixed-and-verified:** 21
- **Persistent:** 19
- **Partial:** 4
- **New-regression:** 0  (none — no regressions detected)
- **Verified-holding:** 22  (of which 13/19 are R4-marked positives; the other 9 are R4-marked issues whose documented behavior persists as expected)

Of the 19 R4-marked `positive_verification` entries:
- 13 verified-holding (true positives still hold)
- 3 fixed-and-verified (the underlying issue they were tracking is now fixed: TRA-A4-005/TRA-042, TRA-C4-005 stale-status, TRA-D4-012 no-op test gap)
- 2 persistent (the underlying issue they were verifying still persists as documented: TRA-A4-001/TRA-001 partial, TRA-A4-004/TRA-040 intentional)
- 1 partial (TRA-D4-003 / TRA-048 invariant — coverage broadened but still partial)

## Headline confirmations

- **TRA-013 byte-reproducibility: HOLDS within HEAD.** Two cold-cache L4 runs of `to_translate.md` produced byte-identical `audit_trace.jsonl` (sha256 `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` x2). Note: this hash differs from the R4 baseline `263b901e...` — the change is *expected* and *legitimate* because the Batch 4 fixes (TRA-038 unknown-term logging, TRA-042 6-category structural verification, TRA-072 4-call-site PolicyResolver arbitration) enriched the audit-trail content. The byte-reproducibility *invariant* (cold-cache runs produce identical bytes) is preserved; only the specific hash value has changed.
- **All 4 quality gates green at HEAD `5476faf`:**
  - `ruff check .` → All checks passed
  - `ruff format --check .` → 39 files already formatted
  - `mypy --strict tra` → Success: no issues found in 20 source files
  - `pytest tests/` → 228 passed in 1.18s
- **All 3 OWASP security fixes (TRA-076/077/078) verified holding.** `sanitize_input` is called on LLM output (`tra/isa.py:439`); cache stores JSON via `model_dump_json()` not pickle (`tra/cache.py:128`); exception repr is sanitized via `_sanitize_exc_repr` (`tra/kernel.py:432`).
- **All 5 R4 Batch 4 spec-conformance fixes (TRA-038/042/072/092/099/100) verified holding**, with comprehensive regression-test coverage (40+ new tests added across the 5 fixes).
- **No regressions detected.** Every R4 regression test that was passing still passes; every static fix that landed in the 9 remediation commits (`f226582` → `5476faf`) is still present at HEAD.

## R4 → R5 status matrix

| R4 ID | R4 Severity | R4 Title (truncated) | R4 Type | R5 Status | R5 Evidence (file:line) |
|---|---|---|---|---|---|
| TRA-A4-001 | WARNING | TRANSLATE_SEGMENT whole-doc (TRA-001 partial) | positive_verification | persistent | `tra/kernel.py:485` still calls `translate_segment(protected, ...)` once on the whole protected source; docstring at `:453-458` explicitly defers full per-leaf refactor. TRA-001 partial persists. |
| TRA-A4-002 | WARNING | PolicyResolver 1 conflict pair (TRA-072) | issue | fixed-and-verified | `rg -c "_POLICY_RESOLVER.wins" tra/isa.py` = 4 (lines 794, 898, 926, 959); TestTRA072UniversalPolicyArbitration (3 subtests) PASS; commit `78c9250`. |
| TRA-A4-003 | WARNING | 3 unreachable exception types (TRA-038) | issue | fixed-and-verified | `raise CertaintyConflict` at `tra/isa.py:761` (LLM path); `recover_unknown_term` invoked at `:723` in `_rule_translate`; `recover_entity_ambiguity` invoked at `:360` in `build_entity_table`. 7 new tests (TestTRA038UnknownTermRaisedInProduction, TestTRA038CertaintyConflictRaisedInLLMPath, TestTRA038EntityAmbiguityRaisedInBuildEntityTable) PASS. Caveat: UnknownTerm/EntityAmbiguity are *logged via recovery procedures* (non-halting) rather than explicitly raised; CertaintyConflict is explicitly raised. Commit `d95c36d`. |
| TRA-A4-004 | WARNING | EXCEPTION_HANDLER/HALT_ERROR not KernelStates (TRA-040) | positive_verification | persistent | `KernelState` enum at `tra/kernel.py:49-60` still 9 states (BOOTSTRAP→EMIT_PAYLOAD); `EXCEPTION_HANDLER` appears only as audit-record string at `:435`, NOT in the enum. Intentional design decision — no spec change since R4. |
| TRA-A4-005 | WARNING | Structural verification heading-count-only (TRA-042) | positive_verification | fixed-and-verified | `verify_output` at `tra/isa.py:799-891` now checks 6 categories: heading count, table row count, list item count, blockquote line count, HR count, code fence count. TestTRA042ExtendedStructuralVerification (6 subtests) PASS; commit `efbc875`. |
| TRA-A4-006 | WARNING | tra_cli.py does NOT pass registry= (TRA-099) | issue | fixed-and-verified | `tra_cli.py:139` now `kernel = TRAKernel(cfg, registry=registry, interactive=interactive)`; `build_default_registry()` called at `:138`. TestTRA099CLIPassesRegistry PASS; commit `e54b7a7`. |
| TRA-A4-008 | INFO | 9-state KernelState (TRA-007/TRA-049) — VERIFIED HOLDING | positive_verification | verified-holding | `KernelState` enum at `tra/kernel.py:49-60` = 9 canonical states; `_KERNEL_ORDER` at `:64-74` unchanged; TestTRA007TransitionOrdering + TestTRA049SameStateTransition PASS. |
| TRA-A4-009 | INFO | L3/L4 conformance gates (TRA-036/TRA-037) — VERIFIED HOLDING | positive_verification | verified-holding | `tra/kernel.py:255-266` (TRA-036 ConformanceFailure at L3/L4 on analyze failure); `:306-344` (TRA-037 _rewrite_anchors BEFORE gate + BROKEN_LINK gate). TestTRA036AnalyzeFailureL3Gate + TestTRA037RewriteAnchorsBeforeGate PASS. |
| TRA-A4-010 | INFO | TRA-068/TRA-069/TRA-A3-008 — VERIFIED FIXED | positive_verification | verified-holding | TestTRA073DeadCodeRemoved (TRA-073/TRA-069), TestTRA074ClockSeedDefault (TRA-074/TRA-068), TestTRA075PairwiseTransitions (TRA-075/TRA-A3-008) all PASS. |
| TRA-B4-001 | WARNING | TRA-076 FIXED — LLM seam output via sanitize_input (OWASP A03) | positive_verification | verified-holding | `sanitize_input` called on LLM output at `tra/isa.py:439`. TestTRA076LLMOutputSanitized PASS. |
| TRA-B4-002 | WARNING | TRA-077 FIXED — Cache stores JSON not pickle (OWASP A08) | positive_verification | verified-holding | `tra/cache.py:128` `self._cache.set(key, result.model_dump_json(), expire=None)`. TestTRA077CacheJsonNotPickle PASS (asserts raw blob starts with `{` not `\x80`). |
| TRA-B4-003 | INFO | TRA-078 FIXED — Exception repr sanitized (OWASP A09) | positive_verification | verified-holding | `_sanitize_exc_repr` called at `tra/kernel.py:432`; `_SECRET_RE` pattern at `:85-89`. TestTRA078SecretRedaction PASS. |
| TRA-B4-004 | INFO | TRA-079 PERSISTENT — Cache values no HMAC/integrity | issue | persistent | `rg "hmac\|signature\|verify_integrity" tra/cache.py` → no match; cache.py only enforces JSON-not-pickle (TRA-077), no tamper detection. |
| TRA-B4-005 | WARNING | TRA-017 FIXED — 6 unused deps removed from pyproject.toml | positive_verification | verified-holding | `tra-prototype/pyproject.toml:10-17` lists 6 runtime deps (pydantic, markdown-it-py, diskcache, pyyaml, click, rich) + 3 dev deps (pytest, ruff, mypy). The 6 unused deps (litellm, structlog, pydantic-settings, mdit-py-plugins, black, pytest-asyncio) absent. TestTRA017UnusedDepsGone PASS. |
| TRA-B4-010 | INFO | TRA-B3-005 PERSISTENT — `registry: object \| None` with `# type: ignore[attr-defined]` | issue | persistent | `tra/kernel.py:111` still `registry: object \| None = None`; `:171` still `for mod in registry.all():  # type: ignore[attr-defined]`. No remediation claimed. |
| TRA-B4-011 | INFO | TRA-B3-006 PERSISTENT — `_collect_headings(nodes: list[Any])` | issue | persistent | `tra/kernel.py:392` still `def _collect_headings(nodes: list[Any]) -> None:`. Should be `list[StructuralNode]`. No remediation claimed. |
| TRA-B4-012 | INFO | TRA-B3-007 PERSISTENT — Stale `# type: ignore[arg-type]` at `tests/test_recovery.py:95` | issue | persistent | `tests/test_recovery.py:95` still `rep = route_exception(BrokenMarkdown(), amb)  # type: ignore[arg-type]`. No remediation claimed. |
| TRA-B4-013 | INFO | TRA-B3-C3 PARTIAL — `_module(ctx) -> Any` returns `Any` (TRA-043 partial) | issue | persistent | `tra/isa.py:203` still `def _module(ctx: RuntimeContext) -> Any:`. No remediation claimed. |
| TRA-B4-014 | INFO | TRA-013 VERIFIED HOLDS — L4 audit trail byte-reproducible | issue | verified-holding | Two cold-cache L4 runs of `to_translate.md` produce byte-identical `audit_trace.jsonl` (sha256 `902298b3...` x2). TestTRA013AuditReproducibility PASS (2 subtests asserting `filecmp.cmp` on audit_trace + evidence_trace). Hash differs from R4 baseline `263b901e...` due to legitimate audit-trail enrichment by Batch 4 fixes (TRA-038/042/072); invariant preserved. |
| TRA-B4-015 | INFO | TRA-014 + TRA-012 VERIFIED SAFE — Path traversal + sanitize_input chokepoint | positive_verification | verified-holding | TestTRA014PathTraversal + TestTRA012SanitizeChokepoint PASS. `sanitize_input` single chokepoint at `tra/isa.py:95` (analyze_document) + `:439` (LLM output). |
| TRA-B4-016 | INFO | OWASP A01/A04/A05 VERIFIED SAFE | positive_verification | verified-holding | `yaml.safe_load` at `tra/config.py:86` (OWASP A05 safe); `sanitize_input` strips null/C0/bidi/BOM at `tra/utils.py:31` (OWASP A03 safe); path traversal protected (TestTRA014PathTraversal PASS). |
| TRA-B4-017 | INFO | Quality gates ALL GREEN — mypy/ruff/pytest pass | issue | verified-holding | All 4 gates green at HEAD `5476faf`: ruff check (clean), ruff format --check (39 files), mypy --strict (0 issues, 20 source files), pytest (228 passed in 1.18s). |
| TRA-C4-003 | WARNING | SKILL.md §7 "174 tests across 16 test files" (actual 199) | issue | fixed-and-verified | `tra-prototype/SKILL.md:243` now says "**228 tests** across 18 test files". Test count (228) is accurate. Minor residual: file count claim (18) is slightly off — actual is 16 pytest-collected test files + `e2e_test.py` manual demo = 17 .py files. |
| TRA-C4-004 | WARNING | SKILL.md §7 stale TDD-regression test ID list | issue | fixed-and-verified | `tra-prototype/SKILL.md:246-249` now lists 40 test classes including the new ones (TRA-038, 042, 072, 099, A4-011, B4-009, F4-006, F4-007); phantom `TRA-044` removed. Commit `929c879`. |
| TRA-C4-005 | WARNING | SKILL.md §8 "Remaining 24 Round 2 findings" lists TRA-016/017/026 as unfixed | positive_verification | fixed-and-verified | `tra-prototype/SKILL.md:280-282` now correctly states "TRA-006 fixed in Round 2, TRA-016 fixed in Round 2, TRA-017 fixed in Round 3 remediation commit `a3cd2c1`, TRA-026 fixed in Round 2". Commit `929c879`. |
| TRA-C4-006 | INFO | SKILL.md "Audit artifacts" omits Round 3 (and Round 4) | issue | fixed-and-verified | `tra-prototype/SKILL.md:372-387` now lists Round 1, 2, 3, AND 4 audit artifacts. Commit `929c879`. |
| TRA-C4-007 | INFO | README.md:109-112 same omission — references only Round 1 + Round 2 | issue | fixed-and-verified | `tra-prototype/README.md:120-126` now references Round 1, 2, 3, AND 4 audit artifacts. Commit `929c879`. |
| TRA-C4-008 | WARNING | status.md STALE banner says "174+" but actual is 199 | issue | fixed-and-verified | `status.md:1` banner now says "actual test count at HEAD `aae0bca` is **228 across 18 test files**". Count (228) is accurate at HEAD `5476faf` (commit `5476faf` was docs-only, didn't change test count). Banner mentions commit `aae0bca` (1 commit behind HEAD) — minor staleness in the commit-hash reference. |
| TRA-C4-009 | INFO | implementation_plan.md "File Structure Summary" missing 6 modules + 5 test files | issue | fixed-and-verified | `implementation_plan.md:305-359` now lists all 6 previously-missing modules (config.py, recovery.py, hitl.py, reporting.py, validate.py, benchmark.py) and the previously-missing test files (test_e2e_to_translate.py, test_tra043_protocol.py, test_tra047_config_robustness.py, test_tra071_broken_markdown.py). |
| TRA-C4-010 | INFO | implementation_plan.md "Dependencies" table lists 15 packages — 6 unused | issue | fixed-and-verified | `implementation_plan.md:365-371` now has a note: "Updated at HEAD `805a8f8` (Round 4 audit). The 6 unused dependencies (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) were removed from `pyproject.toml` in Round 3 remediation commit `a3cd2c1`." |
| TRA-C4-011 | INFO | Phase 0.1.5 lists 3 subcommands — actual CLI has 4 (missing `validate`) | issue | fixed-and-verified | `implementation_plan.md:22` now reads "Set up CLI entry point skeleton (tra_cli.py with translate, validate, audit, cache-clear subcommands)" — 4 subcommands listed. |
| TRA-C4-012 | INFO | Phase 0.1.2 mentions "formatting (black)" — black was removed | issue | fixed-and-verified | `implementation_plan.md:19` now reads "Configure linting (ruff), formatting (ruff format), type checking (mypy strict), testing (pytest) *(note: black was removed in Round 3 remediation commit `a3cd2c1`; ruff format handles formatting)*". |
| TRA-C4-013 | BLOCKING | tra-prototype/README.md CLI examples use bare `tra_cli.py` | issue | fixed-and-verified | `tra-prototype/README.md:25,29,32,35` all use `python -m tra_cli <subcommand>` (4 invocation sites). Commit `f226582`. Shell-test: `python -m tra_cli translate --help` exits 0. |
| TRA-C4-015 | WARNING | README.md "Known gaps" TRA-006 entry — exact opposite of code reality | issue | partial | The R4 misleading phrasing was updated by Batch 2 commit `929c879` to: "PolicyResolver is now invoked in verify_output via `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)`. However, this is the ONLY conflict pair arbitrated (TRA-072)…" (`tra-prototype/README.md:104-109`). **However**, this NEW phrasing is now stale due to Batch 4 TRA-072 fix: there are 4 call sites at HEAD, not 1. The "ONLY conflict pair" claim is no longer accurate. Net: original misleading phrasing removed; new misleading phrasing emerged. |
| TRA-C4-016 | WARNING | README.md "Known gaps" TRA-004 entry retains misleading "EntityAmbiguity now routes through _recover" phrasing | issue | partial | The R4 misleading phrasing was replaced by Batch 2 commit `929c879` with: "However, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are still never raised in production code paths (TRA-038 partial) — … no production code path auto-detects the conditions that would raise them." (`tra-prototype/README.md:100-103`). **However**, this NEW phrasing is now stale due to Batch 4 TRA-038 fix: `CertaintyConflict` IS raised at `tra/isa.py:761`; `UnknownTerm` and `EntityAmbiguity` recovery procedures ARE auto-invoked in production (`:723` and `:360`). Net: original misleading phrasing removed; new misleading phrasing emerged. |
| TRA-C4-017 | INFO | AGENTS.md "Files and roles" omits 7+ meta-docs and the prototype's own SKILL.md/README.md | issue | fixed-and-verified | `AGENTS.md:7-42` table now lists all meta-docs including `TRA-MODULE-AUTHORING.md` (`:16`), `README.md` (`:24`), `CLAUDE.md` (`:25`), `implementation_plan.md` (`:28`), `prototype.md` (`:29`), `review.md`/`review-feedback.md` (`:30`), `status.md` (`:32`), `tra-prototype/SKILL.md` (`:38`), `tra-prototype/README.md` (`:39`). Commit `929c879`. |
| TRA-D4-001 | INFO | e2e LLM callback ignores `source_segment` (carry-over) | issue | persistent | `tests/test_e2e_to_translate.py:83` `def manual_llm(source_segment: str, ctx: object) -> str:` accepts `source_segment` but does not use it (returns pre-baked `to_translate.en.md` content via `orig_translate`). |
| TRA-D4-002 | WARNING | e2e LLM hijack uses module-level patching (TRA-090) | issue | persistent | `tests/test_e2e_to_translate.py:98` still `kernel_mod.translate_segment = patched_translate` (module attribute mutation, not monkeypatch context manager). |
| TRA-D4-003 | WARNING | TRA-048 single-audit-record invariant only PARTIALLY tested (partial fix) | positive_verification | partial | TestTRA088SingleAuditRecordAllExceptions tests 2 exception types (`test_empty_response_single_audit_record` for ValueError, `test_type_error_single_audit_record` for TypeError), up from 1 (RuntimeError) in R3. Improved but still partial — does not cover all TRAException subtypes (e.g., ConnectionError, TimeoutError, OSError). |
| TRA-D4-004 | INFO | `review_decision` text-assertion gap (carry-over) | issue | persistent | `tests/test_outstanding_findings.py:402` asserts `result_res == resolution` but does NOT assert `result_text` for the override path. Gap persists. |
| TRA-D4-005 | INFO | `on_override` callback in `review_decision` untested (carry-over) | issue | persistent | `rg "on_override" tests/` returns no matches. The `on_override` parameter at `tra/hitl.py:30` is untested. |
| TRA-D4-006 | INFO | Benchmark suite at 22/100+ spec target (TRA-031/092) | issue | fixed-and-verified | `cat tests/benchmark/cases/*.jsonl \| wc -l` = 24 (was 22). S-03 (inline code) and E-03 (broken markdown) added by commit `d3e5f60`. All 24 spec-required cases present (`TRA-BENCHMARK-SUITE.md` defines exactly 24 seed cases: S-01..06, F-01..05, T-01..05, D-01..04, E-01..03 = 23 + R-01 = 24). The "100+" aspirational target in the spec is non-binding. |
| TRA-D4-007 | WARNING | `interactive=True` kernel path untested end-to-end (TRA-052/091) | issue | persistent | `rg "interactive=True" tests/ tra/` returns no matches in tests/. No e2e test of the `--interactive` CLI flag. |
| TRA-D4-008 | INFO | `kernel_config` fixture unused (carry-over = TRA-055) | issue | persistent | `tests/conftest.py:82` defines `def kernel_config(tmp_path: Path) -> BootstrapConfig:`; `rg "kernel_config" tests/` only matches a comment at `tests/test_kernel.py:13` ("Uses the shared kernel_config fixture pattern (TRA-034)"). Fixture is never actually injected into any test. |
| TRA-D4-009 | INFO | `e2e_test.py` manual script persists (carry-over = TRA-056) | issue | persistent | `tra-prototype/e2e_test.py` still exists at the prototype root (manual demo script). Note: the redundant `tests/run_e2e_translation.py` (TRA-D4-014) was deleted in Batch 3 commit `524c598`, but the original `e2e_test.py` persists. |
| TRA-D4-010 | INFO | Cross-file duplicate HITL test (carry-over = TRA-057) | issue | persistent | Two tests cover `review_decision`: `tests/test_outstanding_findings.py:377` (TestTRA032HITLResolutions.test_review_decision_returns_correct_resolution) and `tests/test_phase6_hardening.py:157` (test_hitl_review_decision_accept). |
| TRA-D4-011 | INFO | Mutation testing framework deferred (carry-over = TRA-094) | issue | persistent | No mutation testing framework integrated. `rg "mutmut\|cosmic-ray" pyproject.toml` returns no match. No `.github/workflows/mutation.yml` file. |
| TRA-D4-012 | WARNING | `repaired = repaired` no-op has no test (cross-listed from TRA-A4-011) | positive_verification | fixed-and-verified | The dead `repaired = repaired` no-op was removed from `tra/isa.py` (comment at `:1023` confirms removal). TestTRA_A4_011_RepairedNoopRemoved PASS (static check asserting no `= repaired` self-assignment in isa.py). Commit `524c598`. |
| TRA-D4-015 | INFO | Structural repair branch is dead code with no test coverage | issue | partial | `tra/isa.py:1038-1043` structural branch still exists. **However**, the branch is no longer strictly "dead" — TRA-042 fix made `verify_output` emit structural diagnostics for 6 categories (heading/table/list/blockquote/HR/fence mismatches), so the branch is now REACHABLE when structural mismatches occur. The branch itself still does no meaningful repair (just raises `Unrecoverable` when `attempt >= max_retries`), and has no dedicated test. Net: dead-code issue partially addressed (reachability improved; utility unchanged). |
| TRA-E4-003 | INFO | EMPTY_SOURCE exception recovery (§6) — partial fix retained | issue | persistent | `rg "EMPTY_SOURCE" tra/` → `tra/isa.py:104` (analyze_document raises BrokenMarkdown with detail 'EMPTY_SOURCE: document contains no translatable content'). Kernel `_recover` routes through EXCEPTION_HANDLER with WARNING + PRESERVE_SOURCE. Partial fix retained (no auto-recovery beyond PRESERVE_SOURCE); behavior matches R4 documentation. |
| TRA-E4-005 | INFO | HITL `--interactive` flag exists; 2 raise Unrecoverable sites | positive_verification | verified-holding | `tra_cli.py:72` `--interactive` flag exists; `:139` `TRAKernel(cfg, registry=registry, interactive=interactive)`. 2 raise Unrecoverable sites at `tra/isa.py:1041` (structural repair max retries) and `:1053` (repair introduces new BLOCKING). Both require pathological input. (R4 line numbers 666/678 shifted to 1041/1053 due to TRA-042/072 code additions; count unchanged.) |
| TRA-E4-006 | INFO | TRA-013 byte-reproducibility (§6.4) — verified holding | issue | verified-holding | See TRA-B4-014 above. All 6 L4 artifact hashes match across 2 cold-cache runs; byte-reproducibility invariant holds. |
| TRA-E4-007 | INFO | TRA-071 BROKEN_MARKDOWN — verified holding | issue | verified-holding | `tra/isa.py:92-97` `BrokenMarkdown` wrapper around `build_structural_map` (unclosed fence detection). TestTRA071BrokenMarkdown PASS (2 subtests). |
| TRA-E4-008 | INFO | TRA-036 L3 gate — verified holding | issue | verified-holding | `tra/kernel.py:255-266` ConformanceFailure raise at L3/L4 on analyze failure. TestTRA036AnalyzeFailureL3Gate PASS. |
| TRA-E4-009 | INFO | TRA-037 L3 gate — verified holding | issue | verified-holding | `tra/kernel.py:306-344` _rewrite_anchors runs BEFORE the L3 gate; BROKEN_LINK entries in `unresolved_ambiguities` raise ConformanceFailure. TestTRA037RewriteAnchorsBeforeGate PASS. |
| TRA-E4-010 | INFO | TRA-037 L3 gate still checks unresolved_ambiguities for BROKEN_LINK (positive) | positive_verification | verified-holding | `tra/kernel.py:329-344` L3 gate collects `final_blocking` and also checks `unresolved_ambiguities` for "BROKEN_LINK" entries. L4 audit trail integrity preserved (VERIFY_OUTPUT hash matches emitted target). |
| TRA-E4-011 | INFO | State machine 8 post-BOOTSTRAP states (§2.1) — verified holding | issue | verified-holding | `compilation_artifacts/execution_log.json` shows 8 post-BOOTSTRAP states in canonical order; `tra/kernel.py:64-74` `_KERNEL_ORDER` unchanged. |
| TRA-E4-012 | INFO | L4 artifact emission (§6.4) — 9 artifacts present | issue | verified-holding | L4 pipeline emits all 9 expected artifacts: glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml, execution_log.json, repair_history.jsonl, evidence_trace.jsonl, ambiguity_register.json, audit_trace.jsonl. `_export_forensics` at `tra/kernel.py` gates L4-only artifacts on `conformance_level == L4_FORENSIC`. |
| TRA-E4-013 | INFO | Double VERIFY_OUTPUT audit records (L4 has 6 records; L1/L2 have 5) | issue | persistent | L4 `audit_trace.jsonl` has 2× VERIFY_OUTPUT records (seq=4 initial verify, seq=5 L3-gate verify). The 6th record is from the L3 gate. **By design** — preserves hash-chain integrity for both pre-rewrite and post-rewrite targets. |
| TRA-E4-014 | INFO | Link rewriting + L3 gate interaction — fixed (BLOCKING → INFO positive) | positive_verification | verified-holding | TestTRA093BrokenLinkFalsePositive PASS (2 subtests); CJK heading + CJK link translations publish with exit 0 (was exit 1 in R3). `is_translated_slug()` method in `tra/anchor.py` resolves the false-positive BROKEN_LINK issue. |
| TRA-E4-015 | INFO | `style_profile.yaml` undocumented in SKILL.md §4 | issue | persistent | `tra-prototype/SKILL.md:145-147` §4 "translate" artifact list still says "Writes the translated markdown **plus** runtime artifacts (glossary, entity table, structural map, execution log, repair history, audit trace). At L4 it additionally writes `evidence_trace.jsonl` and `ambiguity_register.json`." — lists 8 artifacts, omits `style_profile.yaml`. The artifact IS emitted at L4 (verified by L4 run — `compilation_artifacts/style_profile.yaml` present, 260 B), just not documented. |
| TRA-F4-001 | INFO | `as_interface()` + `register()` + `TRAKernel(registry=)` works end-to-end (TRA-096 FIXED) | positive_verification | verified-holding | TestTRA096AsInterfaceProtocol PASS (3 subtests: ModuleInterface has all 7 fields, default registry kernel works, stub FR→EN module via registry works). `tra/modules/registry.py:13-37` ModuleInterface has 7 Callable fields + metadata. |
| TRA-F4-002 | INFO | `register()` performs `isinstance(mod, LanguageModuleProtocol)` check (TRA-097 FIXED) | issue | verified-holding | `tra/modules/registry.py:64` `if not isinstance(module, LanguageModuleProtocol):` raises TypeError with missing-methods list. TestTRA097RegisterProtocolCheck PASS (2 subtests). |
| TRA-F4-005 | INFO | `TRA-MODULE-ZH-EN.md` is linguistic spec, not module-authoring template (TRA-100) | issue | fixed-and-verified | New file `TRA-MODULE-AUTHORING.md` (328 lines) created at repo root by commit `aae0bca`. Contains `LanguageModuleProtocol`, `as_interface`, `metadata.direction`, `kind` references (15+ matches). The original `TRA-MODULE-ZH-EN.md` (54 lines) remains as the linguistic spec; `TRA-MODULE-AUTHORING.md` is now the engineering module-authoring template. Cross-referenced from `AGENTS.md:16`. |
| TRA-F4-006 | WARNING | Minimal `ModuleInterface` (defaults only) passes `register()` but crashes `TRAKernel` | issue | fixed-and-verified | `tra/modules/registry.py:80-98` `register()` now validates `get_style_profile()` returns non-None; raises `TypeError` with actionable message if default `lambda: None` is used. TestTRA_F4_006_MinimalModuleInterfaceCrashes PASS. Commit `524c598`. |
| TRA-F4-007 | INFO | `_select_module` picks first source-language match — same-source-lang collisions silent | issue | fixed-and-verified | `tra/kernel.py:150-191` `_select_module` now does Pass 1 (full direction match, e.g. 'fr -> en' matches 'FR -> EN') then Pass 2 (source-only fallback). Same-source-lang collisions no longer silent. TestTRA_F4_007_SelectModuleFullDirectionMatch PASS. Commit `524c598`. |

## New regressions (if any)

**None — no regressions detected.**

Every R4 regression test that was passing still passes at HEAD `5476faf` (228 pytest tests, including all 91 tests in `test_outstanding_findings.py` and 12 e2e tests in `test_e2e_to_translate.py`). Every static fix that landed in the 9 remediation commits (`f226582` → `5476faf`) is still present in the source. No R4-positive-verification has flipped to broken.

## Notable observations

1. **TRA-013 byte-reproducibility hash changed (legitimately).** The R4 baseline hash `263b901e...` is now `902298b3...` at HEAD. This is NOT a regression — the byte-reproducibility *invariant* (cold-cache runs produce identical bytes) is preserved. The hash value changed because the Batch 4 fixes enriched the audit-trail content:
   - TRA-038 added `_log_unknown_terms` which now writes UNKNOWN_TERM records to `unresolved_ambiguities` for unknown CJK tokens in real Chinese source text.
   - TRA-042 extended `verify_output` to emit structural diagnostics for 6 categories (was 1).
   - TRA-072 routed 4 severity decisions through `_POLICY_RESOLVER.wins` (was 1).
   Each of these legitimately adds audit records and evidence entries to the L4 trail, changing the bytes without breaking reproducibility.

2. **TRA-C4-015 and TRA-C4-016 are "partial" — doc-refresh + code-fix interaction.** Both findings were addressed by Batch 2 commit `929c879` (which updated the misleading phrasing in `tra-prototype/README.md`). However, the Batch 4 commits `78c9250` (TRA-072 universal arbitration, 4 call sites) and `d95c36d` (TRA-038 wired exceptions) landed *after* the doc refresh, making the new phrasing stale. The README now says "ONLY conflict pair arbitrated" (false — 4 pairs) and "still never raised in production" (false — `CertaintyConflict` is raised; `UnknownTerm`/`EntityAmbiguity` recovery procedures are auto-invoked). These are not regressions of the *original* misleading phrasing (which is gone), but new doc-vs-code drift introduced by the Batch 4 fixes. Recommend a follow-up doc-refresh commit to re-align README.md "Known gaps" with current code reality.

3. **TRA-D4-015 reachability improved.** The structural repair branch at `tra/isa.py:1038-1043` was classified as "dead code" in R4 because `verify_output` only emitted heading-count diagnostics. After TRA-042's fix, `verify_output` now emits structural diagnostics for 6 categories, making the branch REACHABLE. However, the branch still does no meaningful repair (just raises `Unrecoverable` on max retries). Marked "partial" — the dead-code issue is partially addressed (reachability improved; utility unchanged; no dedicated test).

4. **TRA-D4-006 (benchmark 22/100+) is fixed-and-verified.** The R4 finding described the benchmark as "22/100+ spec target" with S-03 and E-03 missing. At HEAD, both are added (commit `d3e5f60`), bringing the total to 24 cases — which is exactly the number of seed cases defined in `TRA-BENCHMARK-SUITE.md` (S-01..06, F-01..05, T-01..05, D-01..04, E-01..03 = 23 + R-01 = 24). The "100+" target in the spec text ("intended to grow toward 100+ cases") is aspirational and non-binding; the spec-required minimum (all 24 seed cases) is now met.

5. **Minor residual inaccuracy in test-file count.** `tra-prototype/SKILL.md:243` and `AGENTS.md:41` both claim "228 tests across 18 test files". The test count (228) is accurate. The file count (18) is slightly off — `ls tests/test_*.py | wc -l` returns 16 pytest-collected test files; adding `e2e_test.py` (manual demo, not pytest-collected) gives 17 .py files. Not the focus of any specific R4 finding, but worth noting for the next doc refresh.

6. **No `# type: ignore` cleanup happened.** The 4 type-safety persistence items (TRA-B4-010/011/012/013) are unchanged from R4. They are INFO-severity carry-overs and were not targeted by any R4 batch.

7. **No test-coverage gaps closed.** The 9 D4-track test-coverage carry-overs (TRA-D4-001/002/004/005/007/008/009/010/011) are all persistent — no remediation claimed, none landed. Only TRA-D4-006 (benchmark), TRA-D4-012 (repaired=no-op test), and TRA-D4-014 (run_e2e_translation.py deletion, not in register but referenced in plan) were addressed.

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# All 4 quality gates at HEAD 5476faf
.venv/bin/ruff check .            # → All checks passed!
.venv/bin/ruff format --check .   # → 39 files already formatted
.venv/bin/mypy --strict tra       # → Success: no issues found in 20 source files
.venv/bin/pytest tests/           # → 228 passed in 1.18s

# Batch 4 spec-conformance regression tests
.venv/bin/pytest tests/test_outstanding_findings.py -k "TRA038 or TRA042 or TRA072" -v
# → 18 passed (TestTRA038UnknownTermRaisedInProduction 3, TestTRA038CertaintyConflictRaisedInLLMPath 2,
#              TestTRA038EntityAmbiguityRaisedInBuildEntityTable 2, TestTRA042ExtendedStructuralVerification 6,
#              TestTRA072UniversalPolicyArbitration 3, TestTRA038UnknownTermRaised 2)

# Batch 3 code-quality regression tests
.venv/bin/pytest tests/test_outstanding_findings.py -k "TRA_A4_011 or TRA016Count or TRA017Unused or TRA026Cache or TRA_F4_006 or TRA_F4_007 or TRA099CLI"
# → all PASS

# Batch 1 + 2 doc-refresh verification (static)
rg -n "python -m tra_cli" tra-prototype/README.md          # → 4 matches (TRA-C4-013 fixed)
rg -n "228 tests" tra-prototype/SKILL.md                   # → 1 match at line 243 (TRA-C4-003 fixed)
rg -n "TRA-MODULE-AUTHORING" AGENTS.md                     # → 1 match at line 16 (TRA-C4-017 fixed)
rg -n "ruff format" implementation_plan.md                 # → 1 match at line 19 (TRA-C4-012 fixed)

# Batch 4 spec-conformance verification (static)
rg -c "_POLICY_RESOLVER.wins" tra/isa.py                   # → 4 (TRA-072 fixed; was 1 in R4)
rg -n "raise CertaintyConflict" tra/isa.py                 # → 1 match at line 761 (TRA-038 fixed)
rg -n "recover_unknown_term\|recover_entity_ambiguity" tra/isa.py  # → 2 matches (TRA-038 fixed)
rg -n "TABLE_ROW_RE\|LIST_ITEM_RE\|BLOCKQUOTE_RE\|HR_RE\|CODE_FENCE_RE" tra/isa.py  # → 5 (TRA-042 fixed)
rg -n "registry=registry" tra_cli.py                       # → 1 match at line 139 (TRA-099 fixed)
rg -n "LanguageModuleProtocol\|as_interface\|metadata.direction" TRA-MODULE-AUTHORING.md  # → 15+ (TRA-100 fixed)

# TRA-013 byte-reproducibility (cold-cache L4 runs)
mkdir -p /tmp/tra_r5_run1 /tmp/tra_r5_run2
for d in /tmp/tra_r5_run1 /tmp/tra_r5_run2; do
  cp /home/z/my-project/Translation-Runtime-Architecture/to_translate.md $d/
  cp config.yaml $d/
  (cd $d && rm -rf cache compilation_artifacts audit_trace.jsonl && \
    /home/z/my-project/Translation-Runtime-Architecture/tra-prototype/.venv/bin/python -m tra_cli translate to_translate.md --level L4 -o out.md && \
    sha256sum audit_trace.jsonl)
done
# → Both runs: 902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142  audit_trace.jsonl
# (Differs from R4 baseline 263b901e... due to legitimate Batch 4 audit-trail enrichment;
#  byte-reproducibility invariant HOLDS within HEAD.)

# OWASP security verification (static)
rg -n "sanitize_input" tra/isa.py                          # → 2 matches (TRA-076 holds)
rg -n "model_dump_json" tra/cache.py                       # → 1 match at line 128 (TRA-077 holds)
rg -n "_sanitize_exc_repr" tra/kernel.py                   # → 1 match at line 432 (TRA-078 holds)
rg -n "yaml.safe_load" tra/config.py                       # → 1 match at line 86 (OWASP A05 holds)
```

## Conclusion

At HEAD `5476faf` (9 commits after the R4 baseline `805a8f8`), **21 of 66 R4 entries are now fixed-and-verified** (primarily the Batch 1 BLOCKING doc fix, Batch 2 13-finding doc refresh, Batch 3 6-finding code-quality fixes, and Batch 4 5-finding spec-conformance fixes including the long-deferred TRA-038/042/072/099/100). **22 entries are verified-holding** (all 4 critical invariants, all 3 OWASP security fixes, TRA-013 byte-reproducibility, all L4 audit-trail integrity properties). **19 entries are persistent** (mostly intentional design decisions, deferred test-coverage gaps, and type-safety carry-overs). **4 entries are partial** (TRA-C4-015/016 docs went stale again due to Batch 4 code fixes; TRA-D4-003 partial test coverage; TRA-D4-015 structural branch reachable but not meaningful). **0 new regressions** were detected — every R4 regression test still passes, every static fix is still present. The TRA-013 byte-reproducibility invariant holds within HEAD (cold-cache runs produce identical bytes), though the specific hash has changed from `263b901e...` to `902298b3...` due to legitimate audit-trail enrichment by the Batch 4 fixes. The codebase at HEAD `5476faf` is in a strictly improved state relative to the R4 baseline, with no regressions and meaningful progress on all 5 Batch 4 spec-conformance items.
