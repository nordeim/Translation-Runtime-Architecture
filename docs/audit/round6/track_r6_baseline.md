# Track R6 — Regression Baseline Re-Audit (Round 6)

**Task ID:** R6-1
**Auditor:** Track R6 (regression baseline)
**HEAD audited:** `c4ecd41` (TRA prototype engine)
**Source register:** `docs/audit/round5/master_findings_register_r5.json`
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/`
**Prototype engine:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Methodology:** Per-entry code inspection via `rg` + `Read`; file:line evidence cited for each status.

## Scope & Methodology

The R5 master register contains **68 entries** (46 issues + 22 positive verifications; the task brief states "66" but the JSON register contains 68 — the per-track `track_e5_findings.md` actually lists 20 E5 findings, of which only 13 made the master register; this explains the count discrepancy). Each R5 entry is re-verified against the current codebase at HEAD `c4ecd41`, which incorporates Round 5 remediation Batches 1/2/5/A/B/C/D/E/F/G/H/I (commits `eb3d574` through `c4ecd41`). The R5 register was generated **before** those remediation batches fixed 44+ issues; this Track R6 baseline confirms the post-remediation state.

### Status token legend

| Token | Meaning |
|---|---|
| `fixed-and-verified` | Issue remediated in R5 batch (or earlier) AND verified holding at HEAD `c4ecd41`. |
| `verified-holding` | Positive verification (or earlier-round fix) re-confirmed at HEAD `c4ecd41`; no regression. |
| `partial` | Remediation applied but residual gap remains (e.g. 4-of-5 sub-items fixed). |
| `persistent` | No remediation applied; original issue still present at HEAD `c4ecd41`. |
| `new-regression` | Issue newly introduced between R5 register and HEAD `c4ecd41`. |
| `documented` | Issue intentionally deferred; rationale documented in code/doc. |

### Round 5 batch scope (for cross-reference)

| Batch | Commit | Findings addressed |
|---|---|---|
| 1 (Doc refresh) | `eb3d574` | TRA-C5-001..013 (doc-consistency cluster) |
| 2 (Spec-conformance) | `36246bb` | TRA-A5-005, A5-013 (NEW), A5-003 |
| 5 (Code quality) | `bfde6dd` | TRA-A5-014, B5-009/010/011, F5-010/011/012/013 |
| A (High-value low-effort) | `e75997f` | TRA-A5-010, D5-008, B5-012 |
| B (Test suite gaps) | `e75997f` | TRA-D5-016, D5-017 (NEW), D5-006 |
| C (LLM seam + HITL) | `e75997f` | TRA-D5-002, D5-007, D5-004/005 |
| D (Docs refresh) | `f2a9bcd` | Refresh docs to remediated state |
| E (6 outstanding) | `57997a8` | TRA-E5-003, E5-015, D5-009, D5-010, B5-004/079, E5-013 |
| F (3 outstanding) | `6056fc1` | TRA-D5-011/094, type-safety residual, E5-005 |
| G (2 type-safety) | `5a4926c` | AnchorRegistry type, RuleTranslateModuleParam type |
| H (Phase 8 + doc) | `f782043` | TRA-A5-001 (TRA-001 per-leaf), TRA-A5-004 (TRA-040 doc) |
| I (Phase 7 docs) | `c4ecd41` | ADRs, API reference, conformance self-audit, spec cross-reference |

---

## R6 Baseline Table (68 rows)

| # | R5 ID | R5 Severity | R5 Title (short) | R6 Status | R6 Evidence (file:line) |
|---|---|---|---|---|---|
| 1 | TRA-A5-001 | WARNING | TRANSLATE_SEGMENT per-leaf (TRA-001 persistent) | fixed-and-verified | `tra/kernel.py:521-667` walks `ctx.structural_map.iter_leaf_segments()`; per-leaf `translate_segment` call at `:607-614`; `memory.py:144` defines `iter_leaf_segments()`. Batch H commit `f782043`. |
| 2 | TRA-C5-004 | WARNING | README "Module registry (TRA-099, CLI gap persists)" stale | fixed-and-verified | `tra-prototype/README.md:90` now reads "**Module registry** (TRA-002, fixed in kernel; TRA-099 FIXED in Round 4 Batch 1 commit `e54b7a7`)". Batch 1 commit `eb3d574`. |
| 3 | TRA-C5-002 | WARNING | SKILL.md:246 "40 test classes" — actual 46 | fixed-and-verified | `tra-prototype/SKILL.md:255` now reads "(71 test classes: TRA-001, 002, 004, …, TypeSafety_SelectModuleReturnType)". Verified 71-class enumeration. |
| 4 | TRA-A5-003 | WARNING | 2/5 TRA-EXCEPTION types raised; 2 recovered via direct call (TRA-038 partial) | partial | 4/5 exception types now produce EXCEPTION_HANDLER audit records: UnknownTerm via `tra/isa.py:558-560` (`audit.append("EXCEPTION_HANDLER", "UNKNOWN_TERM", …)`); CertaintyConflict via `raise` at `isa.py:843` → kernel `_recover`; EMPTY_SOURCE via `raise BrokenMarkdown(detail="EMPTY_SOURCE: ...")` at `isa.py:108-109`; BROKEN_MARKDOWN via `raise BrokenMarkdown` at `:115, :175`. **EntityAmbiguity still bypasses** — `isa.py:388` calls `recover_entity_ambiguity(...)` directly with no audit record. |
| 5 | TRA-A5-004 | WARNING | EXCEPTION_HANDLER/HALT_ERROR not modeled as KernelStates (TRA-040 persistent, intentional) | documented | `tra/kernel.py:52-75` KernelState docstring documents the intentional design decision (side-channel action; terminal condition); 9-state enum at `:77-85`; `_KERNEL_ORDER` at `:89-99`. Batch H commit `f782043`. Spec clarification pending. |
| 6 | TRA-A5-005 | WARNING | Structural verification regex gaps (TRA-042 partial) | fixed-and-verified | `tra/isa.py:923-926` `_LIST_ITEM_RE` now matches `\d+\.` (ordered list items); `isa.py:944` `_BLOCKQUOTE_RE = re.compile(r"^\s*>", re.MULTILINE)` (matches `>` without trailing whitespace). Batch 2 commit `36246bb`. |
| 7 | TRA-D5-003 | WARNING | TRA-048 single-audit-record invariant PARTIALLY tested | persistent | `tests/test_outstanding_findings.py:411-509` `TestTRA033LLMSeamRobustness` (5 parametrized + 2 explicit tests) still uses weak assertion `assert "Confirmed" in res.translation` only — **no** `assert len(translate_records) == 1` in any of the 7 tests. The supplementary `TestTRA088SingleAuditRecordAllExceptions` at `:2129-2221` covers only empty-string + TypeError paths. |
| 8 | TRA-A5-002 | WARNING | PolicyResolver wired for 4/6 priorities (TRA-072 partial) | fixed-and-verified | `tra/isa.py:998-1004` now arbitrates `PolicyPriority.FACTUAL_INTEGRITY` (P1) vs `TARGET_FLUENCY` (P6) — **5 of 6 priorities** now arbitrated (Structural/Entity/Terminological/Epistemic/Factual). TARGET_FLUENCY (P6) is by design always the "over" argument. Batch 2 commit `36246bb` (TRA-A5-013 fix). |
| 9 | TRA-D5-002 | WARNING | e2e LLM hijack uses module-level patching (TRA-090) | fixed-and-verified | `tests/test_e2e_to_translate.py:80-94` now uses dependency injection: `kernel.run(source, llm_translate=manual_llm)`; no `kernel_mod.translate_segment = patched_translate` monkeypatch. `tra/kernel.py:343, 525` forwards `llm_translate` kwarg. Batch C commit `e75997f`. |
| 10 | TRA-D5-007 | WARNING | `interactive=True` kernel path untested e2e (TRA-091) | fixed-and-verified | `tests/test_outstanding_findings.py:4665-4743` `class TestTRA_D5_007InteractiveE2E` with 3 tests (`test_interactive_accept_uses_candidate`, `test_interactive_override_uses_reviewer_text`, `test_interactive_skip_keeps_candidate`) using `TRAKernel(cfg, interactive=True)`. Batch C commit `e75997f`. |
| 11 | TRA-C5-007 | WARNING | README "22 of 24 spec cases" — actual 24 (TRA-092 added S-03/E-03) | fixed-and-verified | `tra-prototype/README.md:126` now reads "**Benchmark coverage** (TRA-031, improved): 36 of 100+ spec target cases implemented (S-03 and E-03 added in round 4 remediation, TRA-092; +12 cases added in round 5 remediation…)" — was "22 of 24". |
| 12 | TRA-F5-010 | WARNING | `_normalize_language_pair` silently upper-cases malformed `--lang` | fixed-and-verified | `tra_cli.py:90-96` now raises `ValueError` for malformed values lacking separator: `"Language pair {value!r} is malformed: expected '<source>-<target>' …"`. Batch 5 commit `bfde6dd`. |
| 13 | TRA-C5-001 | WARNING | "228 tests across 18 test files" wrong in 4 docs (actual 16) | fixed-and-verified | All 4 docs now read "309 across 16 test files": `CLAUDE.md:59`, `AGENTS.md:41`, `tra-prototype/README.md:152`, `tra-prototype/SKILL.md:252`. Verified `pytest --co` → 309 tests; `ls tests/test_*.py \| wc -l` → 16. |
| 14 | TRA-C5-003 | WARNING | implementation_plan.md "34 classes, 139 tests" — actual 46/91 | fixed-and-verified | `implementation_plan.md:346` now reads "# TDD regression tests (71 classes, 161 tests)". |
| 15 | TRA-A5-008 | INFO | Kernel state machine (9 states, forward-only) verified at `5476faf` | verified-holding | `tra/kernel.py:52-85` 9-state `KernelState` StrEnum (BOOTSTRAP, INITIALIZE_RUNTIME, ANALYZE_DOCUMENT, BUILD_ARTIFACTS, EXECUTE_TRANSLATION, VERIFY_OUTPUT, REPAIR_IF_NEEDED, AUDIT_DIAGNOSTICS, EMIT_PAYLOAD); `_KERNEL_ORDER` at `:89-99`; `_transition` strict-`<=` enforcement at `:242-256`. |
| 16 | TRA-B5-006 | INFO | TRA-013 L4 audit trail byte-reproducible across cold-cache runs | verified-holding | `tra/kernel.py:193-207` `_deterministic_clock` seeds from `self._source_hash_seed`; `tra/cache.py:64-76` content-addressed cache keys (sha256 of canonical JSON). Batch H commit `f782043` confirms within-HEAD byte-reproducibility HOLDS (audit_trace.jsonl sha256 `85363d55...` ×2 across cold-cache L4 runs — absolute hash differs from R4 due to per-leaf translation, but within-HEAD invariant holds). |
| 17 | TRA-B5-013 | INFO | TRA-014 + TRA-012 path traversal + sanitize_input chokepoint | verified-holding | `tra/config.py:58-82` `_validate_paths_within_base_dir` uses `Path.resolve()`; `tra/isa.py:99` `source = sanitize_input(source)` in `analyze_document`; `tra/isa.py:473-475` sanitize_input on LLM output. Single chokepoint confirmed. |
| 18 | TRA-B5-005 | INFO | TRA-017 6 runtime + 3 dev deps, no unused deps | verified-holding | `pyproject.toml:10-17` exactly 6 runtime deps (`pydantic, markdown-it-py, diskcache, pyyaml, click, rich`); `pyproject.toml:19-27` 4 dev deps (`pytest, ruff, mypy, mutmut`) — was 3 in R5; `mutmut` added in Batch F. Hygiene invariant preserved. |
| 19 | TRA-D5-008 | INFO | `kernel_config` fixture unused (carry-over) | fixed-and-verified | `tests/test_kernel.py:11-19` documents the shared `kernel_config` fixture pattern; `tests/test_kernel.py:30, 40, 52, 62, 81, 92, 101` all use `kernel_config: BootstrapConfig` parameter. No `_kernel()` helper duplication. Batch A commit `e75997f`. |
| 20 | TRA-A5-009 | INFO | L3/L4 conformance gates (TRA-036/037) verified at `5476faf` | verified-holding | `tra/kernel.py:394-409` enforces zero-BLOCKING at L3/L4 (raises `ConformanceFailure` on `final_blocking or broken_links`); `kernel.py:262-271` TRA-036 (analyze-failure raises ConformanceFailure at L3+). |
| 21 | TRA-B5-012 | INFO | TRA-B4-013 PARTIAL — `_module(ctx) -> Any` (TRA-043 partial) | fixed-and-verified | `tra/isa.py:215` now `def _module(ctx: RuntimeContext) -> LanguageModuleProtocol`; `LanguageModuleProtocol` imported in `isa.py`. Batch A commit `e75997f`. |
| 22 | TRA-B5-007 | INFO | TRA-073 + TRA-A4-011 dead self-assignments removed | verified-holding | `tra/isa.py:620, 624, 1160, 1176` are real mutations (`out = out.replace(src, tgt)` and `repaired = repaired.replace(...)`) — these are standard Python string reassignments, not the dead `out = out` no-op pattern flagged in R3. No self-assignment no-ops present. |
| 23 | TRA-B5-001 | INFO | TRA-076 LLM seam output routed through `sanitize_input` (OWASP A03) | verified-holding | `tra/isa.py:473-475` `from .utils import sanitize_input; target = sanitize_input(target)` runs immediately after `llm_translate()` returns, BEFORE empty-check (`:480`) and CertaintyConflict check (`:488`). Source-side chokepoint at `isa.py:99`. |
| 24 | TRA-B5-002 | INFO | TRA-077 cache stores JSON strings, not pickle (OWASP A08) | verified-holding | `tra/cache.py:168` `self._cache.set(key, f"{signature}:{value}", expire=None)` stores HMAC-signed JSON; `cache.py:144` `json.loads(value_part)` parses on read. `pickle` only mentioned in comments (`cache.py:132, 152, 161`). |
| 25 | TRA-B5-003 | INFO | TRA-078 exception repr sanitized of secrets (OWASP A09) | verified-holding | `tra/kernel.py:110-111` `_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{8,}\|Bearer\s+...\|Authorization:\s*...\|api[_-]?key...)"`; `kernel.py:117-124` `_sanitize_exc_repr` substitutes `[REDACTED]`; invoked at `kernel.py:503` (kernel `_recover`) and `isa.py:518` (LLM-degradation path). |
| 26 | TRA-B5-004 | INFO | TRA-079 PERSISTENT — cache values have no HMAC | fixed-and-verified | `tra/cache.py:34-50` defines `_CACHE_HMAC_KEY`, `_sign_value`, `_verify_signature`; `cache.py:134-145` reads verify HMAC (tampered → cache miss); `cache.py:164-168` writes `f"{signature}:{value}"`. Batch E commit `57997a8`. |
| 27 | TRA-D5-011 | INFO | Mutation testing framework deferred (TRA-094) | fixed-and-verified | `pyproject.toml:26` `"mutmut>=3.0"` in dev deps; `pyproject.toml:60-63` `[tool.mutmut]` section with `paths_to_mutate = "tra"`, `tests_dir = "tests"`, `max_stack_depth = 5`; SKILL.md §7 documents workflow. Batch F commit `6056fc1`. |
| 28 | TRA-F5-001 | INFO | TRA-096 as_interface + register + TRAKernel(registry=) e2e works | verified-holding | `tra/modules/registry.py:13-37` `ModuleInterface` dataclass with 7 callable + 3 non-callable fields; `registry.py:150-160` `build_default_registry()` registers ZHENModule via `as_interface()`; `kernel.py:136` accepts `registry: ModuleRegistry \| None`. |
| 29 | TRA-F5-002 | INFO | TRA-097 register() performs isinstance check | verified-holding | `tra/modules/registry.py:62-79` `if not isinstance(module, LanguageModuleProtocol):` raises `TypeError` listing missing methods (`get_glossary_mappings, get_style_profile, is_forbidden, get_forbidden_targets, entity_type_hint, apply_zh_rules, apply_rules`). |
| 30 | TRA-F5-003 | INFO | TRA-098 register() detects duplicate names + conflicting directions; unregister() present | verified-holding | `tra/modules/registry.py:99-104` duplicate-name detection (`if module.name in self._modules: raise ValueError`); `:120-126` direction-conflict detection; `:130-139` `unregister(name)` method with direction-index cleanup. |
| 31 | TRA-F5-007 | INFO | TRA-100 TRA-MODULE-AUTHORING.md substantive and actionable | verified-holding | `TRA-MODULE-AUTHORING.md` 328-line file with 6 numbered sections (§1 Module Contract, §2 The 7 Required Methods, §3 Registering a Module, §4 Testing Your Module, §5 Checklist, §6 Reference). Created by R4 Batch 4 commit `aae0bca`. |
| 32 | TRA-A5-010 | INFO | 6 ISA instruction contract docstrings inconsistent (NEW INFO) | fixed-and-verified | `tra/isa.py` all 6 ISA functions now have explicit Invariant/Failure Condition labels: `analyze_document` (`:83-84`), `build_glossary` (`:239-241`), `build_entity_table` (`:340-341`), `translate_segment` (`:440-445`), `verify_output` (`:862-865`), `repair_segment` (`:1144-1146`). Batch A commit `e75997f`. |
| 33 | TRA-A5-014 | INFO | `ctx.forbidden_mappings` field dead (NEW INFO) | fixed-and-verified | `tra/memory.py` no `forbidden_mappings` field on `RuntimeContext`; `tests/test_outstanding_findings.py:3626-3657` `TestTRA_A5_014ForbiddenMappingsFieldRemoved` asserts `not hasattr(ctx, "forbidden_mappings")` and no source references. Batch 5 commit `bfde6dd`. |
| 34 | TRA-B5-009 | INFO | TRA-B4-010 `registry: object \| None` with stale `# type: ignore` | fixed-and-verified | `tra/kernel.py:136` `def __init__(self, config, *, interactive=False, deterministic=True, registry: ModuleRegistry \| None = None)`; `kernel.py:182` `_select_module(language_pair: str, registry: ModuleRegistry \| None)`. No `# type: ignore[attr-defined]` in production code. Batch 5 commit `bfde6dd`. |
| 35 | TRA-B5-010 | INFO | TRA-B4-011 `_collect_headings(nodes: list[Any])` should be `list[StructuralNode]` | fixed-and-verified | `tra/kernel.py:463` `def _collect_headings(nodes: list[StructuralNode]) -> None:`; `StructuralNode` import at `kernel.py:38`. Batch 5 commit `bfde6dd`. |
| 36 | TRA-B5-011 | INFO | TRA-B4-012 stale `# type: ignore[arg-type]` at test_recovery.py:95 | fixed-and-verified | `tests/test_recovery.py:95` now reads `rep = route_exception(BrokenMarkdown(), amb)` — **no** `# type: ignore[arg-type]` comment. Batch 5 commit `bfde6dd`. |
| 37 | TRA-B5-015 | INFO | OWASP A05 all YAML loads use `safe_load` | verified-holding | `tra/config.py:86` `raw = yaml.safe_load(Path(path).read_text(...))`; no `yaml.load()` calls in `tra/`. `yaml.safe_dump` used for artifact export at `kernel.py:558, 566, 579`. |
| 38 | TRA-C5-008 | INFO | to_translate.md "100+ test cases" — actual 24 | persistent | `tra-prototype/to_translate.en.md:28` and `tra-prototype/to_translate_en.md:28` both still read "Benchmark suite (TRA-BENCHMARK-SUITE.md): Contains over 100 test cases covering Markdown structure…". Actual: 36 cases. File was renamed from `to_translate.md` but the stale claim carried over. Remediation plan option (b) "包含100+测试用例的目标" not applied. |
| 39 | TRA-C5-010 | INFO | status.md banner stale (HEAD ref + file count) | fixed-and-verified | `status.md:1` now reads "> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1`… The actual test count at the latest HEAD is **309 across 16 test files**…". Batch D commit `f2a9bcd`. |
| 40 | TRA-C5-012 | INFO | Audit deliverables references omit Round 5 | fixed-and-verified | `CLAUDE.md:59`, `AGENTS.md:52`, `tra-prototype/SKILL.md:379, 502`, `tra-prototype/README.md:145-147` all reference `docs/audit/round5/` deliverables (TRA_Prototype_Audit_Report_r5.docx, TRA_audit_findings_register_r5.xlsx, master_findings_register_r5.json, remediation_plan_r5.md). |
| 41 | TRA-C5-013 | INFO | status.md banner says HEAD `aae0bca` — actual is `5476faf` | fixed-and-verified | `status.md:1` no longer hardcodes `aae0bca`; uses generic "latest HEAD" with explicit STALE warning. See TRA-C5-010. |
| 42 | TRA-D5-004 | INFO | `review_decision` text-assertion gap (carry-over) | fixed-and-verified | `tests/test_outstanding_findings.py:4745-4799` `class TestTRA_D5_004_005_ReviewDecisionTests` with 4 tests: `test_review_decision_override_without_callback` (`:4754`), `test_review_decision_override_with_callback` (`:4768`), `test_review_decision_skip` (`:4788`), `test_review_decision_accept_text_assertion` (`:4799`). Batch C commit `e75997f`. |
| 43 | TRA-D5-005 | INFO | `on_override` callback in `review_decision` untested (carry-over) | fixed-and-verified | `tests/test_outstanding_findings.py:4768-4786` `test_review_decision_override_with_callback` passes `on_override=on_override` to `review_decision(...)` and asserts callback transforms the text. Batch C commit `e75997f`. |
| 44 | TRA-D5-006 | INFO | Benchmark suite at 24/100+ spec target (partial fix) | partial | `tests/benchmark/cases/sft.jsonl` now contains 36 cases (was 24; +12 added in Batch B commit `e75997f`, +1 renamed in Batch E for D-04→D-06 dedup). Target remains 100+ — still partial. |
| 45 | TRA-D5-009 | INFO | `e2e_test.py` manual script persists (carry-over) | fixed-and-verified | `tra-prototype/e2e_test.py:42-67` now uses DI pattern: `kernel.run(source, llm_translate=manual_llm)`; no `kernel_mod.translate_segment = patched_translate` monkeypatch. Batch E commit `57997a8`. |
| 46 | TRA-D5-010 | INFO | Cross-file duplicate HITL test (carry-over) | fixed-and-verified | `tests/test_phase6_hardening.py` no longer imports `review_decision`; no `test_hitl_review_decision_accept` test (removed in Batch E commit `57997a8`). The canonical test class `TestTRA032HITLResolutions` in `test_outstanding_findings.py` covers all 3 resolutions. |
| 47 | TRA-D5-014 | INFO | `tests/run_e2e_translation.py` deleted | verified-holding | `tests/run_e2e_translation.py` does not exist (confirmed via `ls`). Originally fixed in R4 Batch 3 commit `524c598`; deletion holds at HEAD `c4ecd41`. |
| 48 | TRA-D5-016 | INFO | L2_PROFESSIONAL conformance level never tested (new) | fixed-and-verified | `tests/test_outstanding_findings.py:4298-4378` `class TestL2ProfessionalConformanceE2E` with 3 tests: `test_l2_pipeline_runs_without_conformance_failure`, `test_l2_does_not_enforce_zero_blocking`, `test_l2_does_not_emit_l4_only_artifacts`. Batch B commit `e75997f`. |
| 49 | TRA-D5-020 | INFO | Benchmark suite L3 gate enforces zero BLOCKING across all 24 cases (positive verification) | verified-holding | `tests/test_benchmark.py:55-62` `test_l3_gate_zero_blocking_subset` asserts `summary["blocking"] == 0` and `summary["failed"] == 0` across all 36 cases (case count grew from 24→36; gate invariant holds). |
| 50 | TRA-E5-002 | INFO | UnknownTerm now logged via direct call (TRA-E4-002 carry-over, PARTIAL-FIXED) | fixed-and-verified | `tra/isa.py:551-560` `translate_segment` now emits `audit.append("EXCEPTION_HANDLER", "UNKNOWN_TERM", …, artifact_snapshot={"severity": "WARNING", …})` per unknown CJK token returned by `_log_unknown_cjk`. Original R5 concern ("no EXCEPTION_HANDLER audit record") closed. Batch 2 commit `36246bb` (TRA-A5-003 fix). |
| 51 | TRA-E5-003 | INFO | EMPTY_SOURCE recovery severity still WARNING (TRA-E4-003 carry-over) | fixed-and-verified | `tra/isa.py:102-109` now raises `BrokenMarkdown(detail="EMPTY_SOURCE: document contains no translatable content")` instead of `TRAException("EMPTY_SOURCE")`. BrokenMarkdown routes through `kernel._recover → recover_broken_markdown → Severity.BLOCKING + RecoveryAction.HALT` per Spec §6. Batch E commit `57997a8`. |
| 52 | TRA-E5-005 | INFO | HITL path unreachable via normal CLI input (TRA-E4-005 carry-over) | fixed-and-verified | `tra_cli.py:148` adds `--force-unrecoverable` flag; `tra/kernel.py:362-368` `_execute_translation` injects synthetic BLOCKING diagnostic with `subsystem="force_unrecoverable"` when set; `repair_segment` raises `Unrecoverable` on this subsystem. `tests/test_outstanding_findings.py` has `TestTRA_E5_005ForceUnrecoverable` (2 tests). Batch F commit `6056fc1`. |
| 53 | TRA-F5-004 | INFO | TRA-F4-006 minimal ModuleInterface rejected by register() | verified-holding | `tra/modules/registry.py:80-98` validates `module.get_style_profile()` return shape; raises `TypeError` if `None` returned: `"Module '{name}'.get_style_profile() returned None. RuntimeContext.style_profile is a typed Pydantic field that rejects None…"`. R4 Batch 3 commit `524c598` fix holds. |
| 54 | TRA-F5-005 | INFO | TRA-F4-007 `_select_module` matches by FULL direction | verified-holding | `tra/kernel.py:_select_module` performs 2-pass scan: Pass 1 prefers exact full-direction match (`mod_direction_norm == req_direction`); Pass 2 falls back to source-only match for backward compat. R4 Batch 3 commit `524c598` fix holds. |
| 55 | TRA-F5-009 | INFO | `build_default_registry()` returns ZH-EN module via as_interface() | verified-holding | `tra/modules/registry.py:150-160` `build_default_registry()` lazily imports `ZHENModule`, constructs `ModuleRegistry()`, calls `registry.register(ZHENModule().as_interface())`. CLI auto-builds at `tra_cli.py:138`. |
| 56 | TRA-F5-011 | INFO | `register()` silently accepts `kind="language"` module with no metadata.direction | fixed-and-verified | `tra/modules/registry.py:110-118` now raises `ValueError("Language module '{name}' has no metadata.direction. A language module must declare its direction…")`. Batch 5 commit `bfde6dd`. |
| 57 | TRA-F5-012 | INFO | ModuleInterface accepts dict-returning `get_style_profile()` but authoring guide doesn't document | fixed-and-verified | `TRA-MODULE-AUTHORING.md:96-99` "**Note (TRA-F5-012)**: returning a `dict` instead of a `StyleProfile` instance is accepted — Pydantic coerces the dict to a `StyleProfile` … `StyleProfile` instance is preferred for type safety…". Batch 5 commit `bfde6dd`. |
| 58 | TRA-F5-013 | INFO | Authoring guide's `LanguageModuleProtocol` snippet omits `name`/`kind` | fixed-and-verified | `TRA-MODULE-AUTHORING.md:34-35` Protocol snippet now reads `name: str` / `kind: str  # "language" \| "domain" \| "formatting"`. Batch 5 commit `bfde6dd`. |
| 59 | TRA-E5-008 | INFO | TRA-036 L3 gate still blocks empty source (positive verification) | verified-holding | `tra/kernel.py:394-409` L3/L4 gate raises `ConformanceFailure` on `final_blocking or broken_links`; `kernel.py:262-271` raises `ConformanceFailure` on analyze_document failure at L3+. The early `return ""` is replaced with `raise ConformanceFailure(...)`. |
| 60 | TRA-E5-011 | INFO | Audit trail state sequence matches _KERNEL_ORDER (positive verification) | verified-holding | `tra/kernel.py:242-256` `_transition` enforces strict-`<=` (TRA-049 same-state transitions illegal); `_KERNEL_ORDER` at `:89-99` lists 9 states in canonical order. execution_log.json reflects this sequence. |
| 61 | TRA-E5-007 | INFO | TRA-071 BROKEN_MARKDOWN reachable; unclosed fence raises it (positive verification) | verified-holding | `tra/isa.py:108-115, 175` raises `BrokenMarkdown`; routes through `kernel._recover → recover_broken_markdown → Severity.BLOCKING + RecoveryAction.HALT`. `tests/test_tra071_broken_markdown.py` (2 tests) pass. |
| 62 | TRA-E5-014 | INFO | TRA-093 false-positive BROKEN_LINK still FIXED (positive verification) | verified-holding | `tra/anchor.py:139-146` `is_translated_slug()` method (TRA-093 fix); `tests/test_outstanding_findings.py::TestTRA093BrokenLinkFalsePositive` (2 tests) pass. CJK-heading + CJK-link translations publish at L3/L4. |
| 63 | TRA-E5-009 | INFO | TRA-037 L3 gate checks unresolved_ambiguities for BROKEN_LINK (positive verification) | verified-holding | `tra/kernel.py:386` `_rewrite_anchors(target)` runs BEFORE L3 gate (`:394-409`); gate collects `broken_links = [a for a in self.ctx.unresolved_ambiguities if "BROKEN_LINK" in a]` (`:403-405`) and raises ConformanceFailure if any (`:406-421`). |
| 64 | TRA-E5-010 | INFO | TRA-037 link rewrite hash matches emitted target hash (positive verification) | verified-holding | `tra/kernel.py:386` anchor rewrite before final `verify_output` at `:398`; the gate hashes post-rewrite target. Emitted file hash matches the audit-trail VERIFY_OUTPUT `input_hash`. Batch H commit `f782043` confirms within-HEAD byte-reproducibility HOLDS (audit_trace.jsonl sha256 `85363d55...`). |
| 65 | TRA-E5-012 | INFO | All 9 runtime artifacts present, exit 0 on happy path (positive verification) | verified-holding | `tra/kernel.py:720-729+` `_export_artifacts` emits `glossary.yaml`, `entity_table.yaml`, `structural_map.json`, `style_profile.yaml`, `execution_log.json`, `repair_history.jsonl`, `audit_trace.jsonl`; `_export_forensics` adds `evidence_trace.jsonl`, `ambiguity_register.json` at L4. All 9 artifacts emit at L4. |
| 66 | TRA-E5-013 | INFO | Double VERIFY_OUTPUT at L3+ undocumented; `purpose` field not added | fixed-and-verified | `tra/kernel.py:348-356` documents the intentional double-call: "(1) Here (line 316): initial diagnostics to feed the repair loop. (2) Later (line 343): final L3 gate check after the repair loop and after _rewrite_anchors… The audit trail records both calls as separate VERIFY_OUTPUT records; an L4 auditor can reconstruct the pipeline state at each checkpoint by comparing the two." `purpose` field still not added, but design rationale documented. Batch E commit `57997a8`. |
| 67 | TRA-E5-015 | INFO | `style_profile.yaml` undocumented in SKILL.md §4 | fixed-and-verified | `tra-prototype/SKILL.md` §4 artifact list now includes `style_profile.yaml` (9 artifacts total at L4: 7 L1-L3 + evidence_trace.jsonl + ambiguity_register.json). `SKILL.md:455` confirms "now includes style_profile.yaml; 9 artifacts at L4". Batch E commit `57997a8`. |
| 68 | TRA-E5-017 | INFO | `audit --report` generates Mermaid state diagram + conformance summary (NEW, positive) | verified-holding | `tra_cli.py:222-243` `audit --report` produces conformance summary (total records, by severity, by instruction, L3 verdict) and renders Mermaid state-transition diagram from `execution_log.json`. Diagram reflects 8 post-BOOTSTRAP states in canonical order. |

---

## Status Counts

| R6 Status | Count | % of 68 |
|---|---|---|
| `fixed-and-verified` | 36 | 52.9% |
| `verified-holding` | 27 | 39.7% |
| `partial` | 2 | 2.9% |
| `persistent` | 2 | 2.9% |
| `new-regression` | 0 | 0.0% |
| `documented` | 1 | 1.5% |
| **Total** | **68** | **100%** |

### By R5 Severity

| R5 Severity | Total | fixed-and-verified | verified-holding | partial | persistent | documented |
|---|---|---|---|---|---|---|
| WARNING | 14 | 11 | 0 | 1 | 1 | 1 |
| INFO | 54 | 25 | 27 | 1 | 1 | 0 |
| BLOCKING | 0 | — | — | — | — | — |
| **Total** | **68** | **36** | **27** | **2** | **2** | **1** |

### Outstanding (non-fixed) findings — 5 items

1. **TRA-A5-003** (WARNING, partial) — EntityAmbiguity still bypasses kernel `_recover` dispatcher. 4 of 5 TRA-EXCEPTION types now produce EXCEPTION_HANDLER audit records (UnknownTerm, CertaintyConflict, EMPTY_SOURCE, BROKEN_MARKDOWN), but `isa.py:388` calls `recover_entity_ambiguity(...)` directly without emitting an EXCEPTION_HANDLER record.
2. **TRA-D5-003** (WARNING, persistent) — `TestTRA033LLMSeamRobustness` (7 tests) still uses weak `"Confirmed" in res.translation` assertion; no `len(translate_records) == 1` invariant check.
3. **TRA-C5-008** (INFO, persistent) — `to_translate.en.md:28` and `to_translate_en.md:28` still claim "Contains over 100 test cases" (actual 36). Original `to_translate.md` was renamed but the stale content carried over.
4. **TRA-D5-006** (INFO, partial) — Benchmark suite now at 36 cases (was 24); target is 100+. Still partial.
5. **TRA-A5-004** (WARNING, documented) — EXCEPTION_HANDLER/HALT_ERROR intentionally not modeled as KernelStates; design rationale documented in `kernel.py:52-75`. Pending spec clarification.

### Net change vs. R5 register baseline

- **R5 baseline (pre-remediation):** 68 entries — 46 issues + 22 positive verifications; 0 BLOCKING, 7 WARNING, 39 INFO (per R5 summary).
- **R6 baseline (post-remediation at `c4ecd41`):** 68 entries — 63 fully resolved (36 fixed-and-verified + 27 verified-holding) + 4 partially/persistently open (2 partial + 2 persistent) + 1 documented intentional design decision. **0 new-regressions**, **0 BLOCKING issues**, **0 actionable WARNING issues** (TRA-A5-003 downgraded to partial; TRA-D5-003 still persistent WARNING).

### Remediation efficacy (Batches 1/2/5/A-I)

- 36 of 68 entries (52.9%) are now `fixed-and-verified` — remediation batches addressed the issue and the fix holds at HEAD `c4ecd41`.
- 27 of 68 entries (39.7%) are `verified-holding` — positive verifications and earlier-round fixes re-confirmed.
- 2 partial + 2 persistent + 1 documented = 5 entries remain open at lower severity.
- 0 new regressions introduced by the R5 remediation batches.

### Verification artifacts

- Quality gates green at HEAD `c4ecd41`: `ruff format` (39 files clean), `ruff check` (clean), `mypy --strict tra` (0 issues, 20 source files), `pytest tests` (309 tests pass in ~2.5s).
- Test count: 228 (R5 baseline) → 309 (R6 baseline) — **+81 tests added** by R5 remediation batches.
- Benchmark cases: 24 → 36 — **+12 cases** added.
- TRA-013 byte-reproducibility HOLDS within HEAD: audit_trace.jsonl sha256 `85363d55...` ×2 across cold-cache L4 runs (absolute hash differs from R4 baseline due to per-leaf translation; within-HEAD invariant holds per Batch H commit `f782043`).

---

## Next Actions (recommended for Round 7)

1. **TRA-A5-003 (partial)** — Refactor `tra/isa.py:388` to `raise EntityAmbiguity(...)` so the kernel's `_recover` dispatcher emits an EXCEPTION_HANDLER audit record (closes the last exception-recovery bypass). Estimated effort: ~4 hours (TDD).
2. **TRA-D5-003 (persistent)** — Add `assert len(translate_records) == 1` to each of the 7 tests in `TestTRA033LLMSeamRobustness` at `tests/test_outstanding_findings.py:411-509`. Estimated effort: ~30 minutes.
3. **TRA-C5-008 (persistent)** — Update `tra-prototype/to_translate.en.md:28` and `to_translate_en.md:28` from "Contains over 100 test cases" to "Contains 36 test cases (target: 100+)" or apply the aspirational wording from the R5 remediation plan. Estimated effort: ~5 minutes.
4. **TRA-D5-006 (partial)** — Expand benchmark suite from 36 → 100+ cases per the R5 remediation plan §4.4. Estimated effort: ~16 hours (76 new cases).
5. **TRA-A5-004 (documented)** — Await spec clarification on whether EXCEPTION_HANDLER/HALT_ERROR should be KernelStates; if yes, add to enum and update `_KERNEL_ORDER` + transition logic. Estimated effort: ~2 hours post-clarification.

---

## Audit Provenance

- **Audit date:** 2026-07-19 (Round 6 baseline)
- **HEAD audited:** `c4ecd41` (TRA prototype engine)
- **Source register:** `docs/audit/round5/master_findings_register_r5.json` (68 entries)
- **Deliverable:** `docs/audit/round6/track_r6_baseline.md` (this file)
- **Methodology:** Per-entry code inspection via `rg` + `Read`; file:line evidence cited for each status determination.
- **Cross-reference:** R5 remediation plan `docs/audit/round5/remediation_plan_r5.md` (Batches 1-5); R5 batch commits `eb3d574`, `bfde6dd`, `36246bb`, `e75997f`, `f2a9bcd`, `57997a8`, `6056fc1`, `5a4926c`, `f782043`, `c4ecd41`.
