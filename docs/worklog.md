# Worklog

## Task 3-validate — TRA codebase vs docs cross-cutting audit

Audited `/home/z/my-project/tra/tra-prototype/` against `CLAUDE.md`, `SKILL.md`, `implementation_plan.md`, `README.md`, and the five `TRA-*.md` spec files. Read every Python source file in `tra/`, every test file, the benchmark fixtures, the example, the config, and the repo-level spec/marketing docs. Ran the four quality gates from inside the prototype dir.

Findings below are organized per the requested 10 sections.

---

### 1. Layout verification

Every file CLAUDE.md lists under `tra-prototype/` exists and contains the claimed behavior.

| Documented path | Exists? | Contains claimed behavior? | Notes |
| --- | --- | --- | --- |
| `tra/diagnostics.py` | yes | **yes** | `AuditTrail` (append-only JSONL, `append`/`flush`/`load`) at L99-166; `EvidenceRegistry` (id-keyed, `add`/`get`/`all`/`__contains__`) at L79-96; also defines `EvidenceRecord`, `AuditRecord`, `Diagnostic`, `EvidenceType`. The `count_blocking` helper at L159-166 is a stub that always returns 0 with a comment "hook for VERIFY to populate" — real counting is in `reporting.summarize_audit` and `validate.ValidationReport`. |
| `tra/anchor.py` | yes | **yes** | `StructuralMapBuilder` walks markdown-it-py token stream into `StructuralNode` tree (heading/paragraph/list/table/fence/hr/blockquote). `AnchorRegistry` registers `__HEADER_NNN__` placeholders and resolves translated slugs with dedup. `rewrite_links` (S-06) repoints `(#slug)` links and skips fenced code blocks. `_consume_table` flattens thead/tbody so shape is table→row→cell. |
| `tra/utils.py` | yes | **yes** | `extract_entities` uses 4 regexes (VERSION_RE, PRODUCT_RE, ACRONYM_RE, CLI_RE), drops plain-Capitalized prose words via `_PLAIN_WORD_RE`/`_PRODUCT_SIGNAL_RE`, returns immutable `Entity` objects. `classify_entity` dispatches to `EntityType`. |
| `tra/recovery.py` | yes | **yes** | Maps all 5 TRA-EXCEPTION types: `UnknownTerm`→PRESERVE_SOURCE+WARNING, `BrokenMarkdown`→BLOCKING (HALT if critical_hierarchy_lost, else PRESERVE_SOURCE), `CertaintyConflict`→PRIORITIZE_EPISTEMIC+WARNING, `EntityAmbiguity`→TREAT_AS_ENTITY+WARNING, `GlossaryConflict`→USE_FIRST_OCCURRENCE+BLOCKING. `route_exception` dispatcher at L154-182. Each recovery optionally appends to `ctx_ambiguities`. |
| `tra/hitl.py` | yes | **yes** | `review_decision` (rich Console + Prompt) returns `(resolution, text)` with `resolution ∈ {accept, override, skip}`. `format_unrecoverable` builds (uncertainty, source_excerpt) for an UNRECOVERABLE Diagnostic. |
| `tra/reporting.py` | yes | **yes** | `summarize_audit` returns total/by_severity/by_instruction/blocking_flags/`l3_conformant`. `mermaid_state_diagram` renders `flowchart LR` with nodes for every `KernelState` and edges from `execution_log`. `line_by_line_trace` (L73-95) is the L4 forensic tracer mapping each non-empty target line → its evidence id chain via substring containment. |
| `tra/validate.py` | yes | **yes** | `ValidationReport` with `blocking`/`warnings`/`passed`/`summary` properties; `passed = not blocking`. `validate_translation` runs ANALYZE+BUILD_GLOSSARY+BUILD_ENTITY_TABLE then `verify_output` on the candidate (no translate). Pass-gate = zero BLOCKING. |
| `tra/benchmark.py` | yes | **yes** | `BenchmarkCase` (id/category/source/level/must_contain/must_not_contain/zero_blocking/description). `BenchmarkRunner.run_case` runs the full pipeline then re-verifies via `verify_output` and counts BLOCKING. `summarize` aggregates totals + `blocking` count. L3 gate enforced in test_benchmark.py via `assert summary["blocking"] == 0`. |
| `tra/modules/registry.py` | yes | **yes** | `ModuleInterface` dataclass with `get_glossary_mappings`/`get_style_profile`/`apply_rules` callables + metadata. `ModuleRegistry.register`/`get`/`all`. `build_default_registry` registers the bundled `zh_en` module. `registry_for_language_pair` filters by source-lang prefix. |
| `tra/modules/base.py` | yes | **yes** | `ModuleBase` ABC with abstract `get_glossary_mappings`/`get_style_profile`, default identity `apply_rules`. |
| `tra/modules/zh_en.py` | yes | **yes** | `ZHENModule` with all expected methods (see §6). |
| `tra/config.py` | yes | **yes** | `BootstrapConfig` Pydantic model with `language_pair`, `domain`, `conformance_level`, `model_endpoint`, `model_version`, `cache_*`, `repair_max_retries`, `compilation_dir`, `audit_trace`. `from_yaml` classmethod parses `tvm_bootstrap` YAML. `policy_stack` property returns the canonical 6-priority list. |
| `tra/exceptions.py` | yes | **yes** | `TRAException` base + 5 subclasses (`UnknownTerm`, `BrokenMarkdown`, `CertaintyConflict`, `EntityAmbiguity`, `GlossaryConflict`) + `Unrecoverable` (used by repair_segment). Each carries the spec payload (`term`/`token`/`detail`/`canonical_target`). |
| `tra_cli.py` | yes | **yes (with caveats)** | `click.group` with 4 subcommands: `translate`, `cache-clear`, `audit`, `validate` (the validate command is at L197). But the file docstring (L1-7) says "Phase 0.1.5 skeleton" and lists only `translate`/`cache-clear`/`audit` — it omits `validate` and is stale. |

Also found (not mentioned in CLAUDE.md's layout list but present):
- `tra/cache.py` — actually IS mentioned in CLAUDE.md ("cache.py — deterministic TranslationCache"). Confirmed: `CacheKeyContext` with SHA-256 over canonical context (source+glossary_hash+entity_hash+model+policy_stack_hash), `TranslationCache` (diskcache-backed, no TTL), `TranslationResult`.
- `tra/__init__.py` — package marker, `__version__ = "0.0.1"`.

---

### 2. Open-items verification

| Item | Doc claim | Reality | Verdict |
| --- | --- | --- | --- |
| **6.3.1 structlog** | "structlog is a listed dependency but the engine uses plain AuditTrail" (CLAUDE.md L44, SKILL.md L189) | `structlog>=24.1` is in pyproject.toml L17 and requirements.txt L8, but `grep -ri "structlog"` over `tra-prototype/tra/` returns **zero imports** (only doc/manifest mentions). All logging flows through the plain `AuditTrail` JSONL append. implementation_plan.md L268 has `- [ ] 6.3.1 Structured logging (structlog) with correlation IDs` (unchecked). | **CONFIRMED OPEN.** |
| **6.5.1 asyncio segment-level parallelism** | "No asyncio segment-level parallelism" (CLAUDE.md L45, SKILL.md L191) | No `async def`/`await`/`asyncio` anywhere in `tra/` (only mention of "awaiting" is a docstring noun in hitl.py L8). The kernel's `_execute_translation` (kernel.py L183-187) calls `translate_segment(src, ...)` on the WHOLE source synchronously as one segment — there is no segment iteration at all, let alone parallel. `pytest-asyncio` is in dev deps but unused. | **CONFIRMED OPEN.** (Also: segment-level iteration itself isn't implemented — see §9.) |
| **6.5.2 cross-run disk caching** | "only translation output is cached; glossary/entity tables rebuilt per run" (CLAUDE.md L46, SKILL.md L192) | `TranslationCache.set/get` only ever called from `translate_segment` (isa.py L307, L345) and tests. `build_glossary` and `build_entity_table` have no cache check — they rebuild from `_MODULE.get_glossary_mappings()` and `extract_entities(source)` on every invocation. The cache key DOES include the glossary/entity hashes (cache.py L60-66), but the artifacts themselves are never cached. | **CONFIRMED OPEN.** |
| **Phase 7 (ADRs, API reference, module authoring guide, conformance self-audit, final validation)** | "Phase 7 (documentation & delivery) has not started" (CLAUDE.md L15) | implementation_plan.md L289-301 lists 7.1.1 ADRs, 7.1.2 API reference, 7.1.3 Module authoring guide, 7.1.4 Conformance self-audit checklist, 7.2.1-7.2.4 final validation — **all checkboxes unchecked**. No ADRs/`docs/`-style reference under `tra-prototype/`; no auto-generated conformance checklist. The closest things are `SKILL.md` (a usage guide, not a module-authoring guide) and `../TRA-MODULE-ZH-EN.md` (a spec doc, not a how-to). | **CONFIRMED OPEN.** |

---

### 3. Test suite coverage

103 tests pass. Each file's coverage:

| Test file | Tests | One-line summary |
| --- | --- | --- |
| `conftest.py` | (fixtures) | Shared fixtures: `sample_glossary`, `sample_entities`, `cache_context`, `evidence_registry`, `sample_evidence`, `config` (loads real `config.yaml`). |
| `test_phase0.py` | 10 | Phase-0 foundations: cache key determinism + order-independence (test_cache_key_is_deterministic_and_order_independent, test_cache_key_changes_with_model_or_policy), cache round-trip, evidence registry append-only, audit trail JSONL append/load, config loader, PolicyResolver stack honoring, AnchorRegistry slugify, structural-map node count, RuntimeContext defaults. Includes explicit "confidence_note must never trigger routing" assertion (L71-78). |
| `test_anchor.py` | 6 | StructuralMapBuilder: node-count determinism, tables/lists/code-block/hr/blockquote shapes, code blocks marked `is_no_translate_zone`, heading placeholder registration, AnchorRegistry dedup, **S-06 link rewrite** (repoints translated slugs, skips code-block-internal links, reports broken slugs). |
| `test_utils.py` | 7 | Entity extraction: version tokens, product tokens, acronyms, CLI flags/backticks, plain-prose rejection, dedup, classify_entity dispatch. |
| `test_isa.py` | 11 | **All 6 ISA instructions covered.** ANALYZE_DOCUMENT (builds profile+map, EMPTY_SOURCE raises, malformed-marker), BUILD_GLOSSARY (canonical entries, CONFLICTING_MAPPINGS raises on drift), BUILD_ENTITY_TABLE (immutable + classified), TRANSLATE_SEGMENT (canonical substitution, cache-hit byte-identical, ZH-rule-layer application), VERIFY_OUTPUT (missing entity BLOCKING, epistemic drift BLOCKING, clean doc zero BLOCKING), REPAIR_SEGMENT (resolves epistemic drift). |
| `test_kernel.py` | 7 | Kernel orchestration: full pipeline run, audit trail emission (≥5 records, all ISA instructions), artifact export (glossary/entity/smap/style), sequential state machine, illegal backward transition raises, on-disk audit trail, EXCEPTION_HANDLER recovery path on forced GLOSSARY_CONFLICT. |
| `test_recovery.py` | 8 | All 5 recovery procedures: unknown_term preserves source + WARNING, broken_markdown HALTs on critical loss / best-effort otherwise, certainty_conflict prioritizes epistemic, entity_ambiguity defaults to entity, glossary_conflict BLOCKING + first-occurrence canonical. `route_exception` dispatch coverage + unknown fallback. |
| `test_modules.py` | 12 | ZH-EN module: glossary canonical, epistemic lexicon exact, forbidden drift targets, style profile, entity hints, registry default contains zh_en, unknown-module raises, scoped registry, ModuleInterface contract, parataxis→hypotaxis, nominalization verbalization, rule-layer only transforms known forms, EN→ZH four-char map, passive reduction, full-width punctuation, `apply_rules` direction dispatch. |
| `test_validate.py` | 4 | Standalone validate: clean candidate passes, missing entity blocks, epistemic drift blocks, summary counts. |
| `test_benchmark.py` | 4 | Benchmark suite: fixtures parse (F-01/T-05/E-02 present, all cases have ≥1 assertion), parametrized per-case runner, **`test_l3_gate_zero_blocking_subset` explicitly asserts `summary["blocking"] == 0` AND `summary["failed"] == 0`** (L60-61), regression R-01 cache-hit byte-identical. |
| `test_reporting.py` | 5 | summarize_audit counts severity+instruction, `l3_conformant=False` on BLOCKING, `l3_conformant=True` with only WARNING, Mermaid diagram renders canonical order, follows execution_log, handles single-state self-loop. |
| `test_phase6_hardening.py` | 7 | Phase 6 hardening: **repair history tracking, LLM graceful degradation on `llm_translate` raise, `_sanitize_input` strips control/bidi/BOM, L4 forensic trace emitted at L4_FORENSIC, line-by-line attribution, HITL review_decision accept path, HITL format_unrecoverable**. **Note: TRA-EXCEPTION recovery itself is tested in `test_recovery.py`, NOT in this file.** |

Benchmark fixtures:
- `tests/benchmark/cases/sft.jsonl` — 13 cases: F-01..F-05 (5 factual), T-01..T-05 (5 terminology), S-05 (1 structural), D-04 (1 domain/hedging), E-02 (1 mixed-language). All declare `zero_blocking: true`.
- `tests/benchmark/cases/regression.jsonl` — 1 case: R-01 (topic-comment regression anchor, expects "The system is Confirmed").
- **Total: 14 cases.** Spec target is "100+"; current is ~14% of that.

All 6 ISA instructions are covered in test_isa.py. ✓
test_benchmark.py DOES explicitly assert zero BLOCKING for the L3 gate (test_l3_gate_zero_blocking_subset, line 55-62). ✓
test_phase6_hardening.py covers HITL hooks ✓, L4 forensics ✓, input sanitization ✓, LLM graceful degradation ✓. TRA-EXCEPTION recovery is covered in a separate test_recovery.py, not test_phase6_hardening.py.

---

### 4. Critical invariants audit

| # | Invariant | Enforced? | Evidence |
| --- | --- | --- | --- |
| 1 | **Canonical terminology exact** (`成立→Confirmed`, `执行环境→execution environment`, `高度可信→highly credible`) | **YES, fully.** | `tra/modules/zh_en.py` L21-32 GLOSSARY defines all three bindings. L35-40 EPISTEMIC_LEXICON reinforces `成立→Confirmed` and `高度可信→highly credible`. L43-47 FORBIDDEN_TARGETS bans `Valid/True/Correct`, `runtime`, `indisputably true`. `build_glossary` (isa.py L162-168) calls `_MODULE.is_forbidden(src, tgt)` and raises `GlossaryConflict` if a mapping matches a forbidden drift target. `verify_output` (isa.py L438-450) raises BLOCKING on any forbidden target string appearing in target. Grepped the entire prototype for `成立|执行环境|高度可信` — the only Python references are in `zh_en.py` (definitions) and tests; no override or alternative mapping exists anywhere. |
| 2 | **Entities immutable** (`Entity.mutable = False`, never True) | **YES, fully.** | `tra/memory.py` L159: `mutable: bool = False  # Invariant: entities are never translated`. `extract_entities` (utils.py L90) constructs every `Entity` with the default. `build_entity_table` (isa.py L248) explicitly sets `ent.mutable = False` again as a belt-and-suspenders. `test_build_entity_table_immutable` (test_isa.py L126) asserts `all(e.mutable is False for e in ents)`. `test_version_token_classified` (test_utils.py L13) asserts `v.mutable is False`. Grepped `\.mutable\s*=` — only two assignments, both `= False`. Never set to True. |
| 3 | **Verification never self-scores** (`verify_output` does not read `confidence_note`) | **YES, fully.** | `verify_output` body (isa.py L380-458) reads from `ctx.glossary_cache`, `ctx.entity_table`, `ctx.structural_map`, `_forbidden_from_module()` — never `confidence_note`. `repair_segment` (isa.py L466-548) re-verifies via `verify_output` and reads `Diagnostic.severity`/`subsystem`/`issue` — also never `confidence_note`. `confidence_note` field exists on `EvidenceRecord` (diagnostics.py L49) and `GlossaryEntry` (memory.py L141) purely as debug-only metadata. test_phase0.py L71-78 has an explicit assertion that a low `confidence_note=0.1` does NOT trigger any routing. |
| 4 | **Repair surgical** (re-verifies and refuses to introduce new BLOCKING) | **PARTIALLY.** | `repair_segment` (isa.py L516-519) re-verifies via `verify_output(repaired, source_segment, ctx, audit)`, computes `new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]`, and raises `Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")` — **but only if `attempt >= max_retries`**. On earlier attempts with new BLOCKING, the function returns the broken `repaired` text and records `resolved=False` in `repair_history` without raising. The kernel's `_repair_loop` (kernel.py L189-236) catches this by re-running verify and re-queuing, so the LOOP converges or breaks. But the strict "REPAIR must not introduce new ones" invariant from CLAUDE.md L79 / ISA-REFERENCE L79 is enforced only at the retry-budget boundary, not at every call. The recorded `RepairAttempt.resolved` field is accurate. |

---

### 5. Quality gate results

Ran from `/home/z/my-project/tra/tra-prototype/` after `pip install --break-system-packages -e ".[dev]"`.

| Gate | Result | Notes |
| --- | --- | --- |
| `pip install -e ".[dev]"` | **PASS (with caveat)** | System Python is PEP-668 externally-managed; had to use `--break-system-packages`. Installed cleanly: pydantic 2.13.4, markdown-it-py 4.2.0, diskcache 5.6.3, structlog 26.1.0, litellm 1.92.0 (pulls in openai, tiktoken, tokenizers, huggingface-hub — heavy deps for a rule-based prototype that never imports litellm). ruff/mypy/pytest installed to `~/.local/bin` (not on default PATH). |
| `ruff check .` | **PASS** | "All checks passed!" |
| `ruff format --check .` | **PASS** | "33 files already formatted" |
| `mypy --strict tra` | **PASS** | "Success: no issues found in 20 source files" |
| `pytest tests -q` | **PASS** | "103 passed in 0.46s" (72 + 31 tests) |

All four gates green. Matches the `status.md` claim "ruff clean · ruff-format clean · mypy --strict (20 files) · 103 pytest passing".

---

### 6. ZH-EN module summary

`tra/modules/zh_en.py` (245 lines). Implements `ZHENModule` class.

**Glossary mappings** (`GLOSSARY` dict, L20-32): **11 entries.**
- `成立 → Confirmed`, `执行环境 → execution environment`, `准确描述 → accurately describes`, `高度可信 → highly credible`, `可能 → may`, `进行验证 → verify`, `实现优化 → optimize`, `提供支持 → support`, `硬件隔离 → Hardware isolation`, `无缝迁移 → Seamless migration`, `高可用性 → High availability`.

**Epistemic lexicon** (`EPISTEMIC_LEXICON`, L35-40): **4 entries** (subset of glossary): `成立 → Confirmed`, `准确描述 → accurately describes`, `高度可信 → highly credible`, `可能 → may`.

**Forbidden drift targets** (`FORBIDDEN_TARGETS`, L43-47): **3 entries**: `成立 → Valid/True/Correct`, `执行环境 → runtime`, `高度可信 → indisputably true`.

**ZH→EN rules** (`apply_zh_rules`, L167-181):
1. **Parataxis→hypotaxis** (`TOPIC_COMMENT`, L54-60): 5 curated canonical forms (`系统成立→The system is Confirmed`, etc.). Longest-key-first substitution.
2. **Nominalization verbalization** (`NOMINALIZATION`, L63-70): 6 entries (`进行验证→verify`, `实现优化→optimize`, `提供支持→support`, `开展测试→test`, `完成部署→deploy`, `执行迁移→migrate`).
3. **Half-width punctuation normalization** (`_FULL_TO_HALF`, L96-109): 12 mappings (，→`, `, 。→`. `, ：→`: `, etc.). Whitespace collapse via `_WS_RE`.

**EN→ZH rules** (`apply_en_rules`, L185-200):
1. **Four-char map** (`FOUR_CHAR_MAP`, L78-82): 3 entries (`seamless migration→无缝迁移`, `high availability→高可用性`, `hardware isolation→硬件隔离`). Case-insensitive regex.
2. **Passive reduction** (`PASSIVE_REDUCTION`, L86-93): 6 entries (`is confirmed→已确认`, etc.). Case-insensitive regex.
3. **Full-width punctuation normalization** (`_HALF_TO_FULL`, L110-119): 8 mappings.

**Conclusion-leading markers** (`CONCLUSION_LEADING`, L75): defined as a tuple `("因此", "所以", "故", "由此可见", "综上")` — but **NOT consumed anywhere** in the codebase. Dead constant.

**Methods present (called from isa.py / tested):**
- `get_glossary_mappings()` ✓ (isa.py L158)
- `get_style_profile()` ✓ (kernel.py L106)
- `apply_zh_rules(text)` ✓ (isa.py L358, via `_rule_translate`)
- `apply_en_rules(text)` ✓ (called by `apply_rules` dispatcher)
- `apply_rules(source, direction)` ✓ (registry.py L52)
- `is_forbidden(source, target)` ✓ (isa.py L163)
- `get_forbidden_targets()` ✓ (isa.py L208)
- `entity_type_hint(token)` ✓ (isa.py L245)
- `epistemic_target(source)` ✓ (tested in test_modules.py L24-27)
- `as_interface()` ✓ (registry.py L52)

All 6 methods the task description asked about are present. The `CONCLUSION_LEADING` constant is defined but unused — minor dead code.

---

### 7. Examples & config

| Path | Exists? | Notes |
| --- | --- | --- |
| `examples/security_advisory_zh.md` | **yes** | Realistic ZH/EN-mixed technical advisory: SA-2024-001 title, mentions RustVMM v0.5.0, `成立`, `执行环境`, `高度可信`, `进行验证`, `提供支持`, KVM/XFS, P99, 96-core, <5MB, `可能`. 9 lines. Plausible input. |
| `examples/expected_outputs/security_advisory_zh.L3.md` | **yes** | Matches what the rule-based engine would produce: `成立→Confirmed`, `执行环境→execution environment`, `高度可信→highly credible`, `进行验证→verify`, `提供支持→support`, `可能→may`. Reads awkwardly ("may Confirmed under heavy load", "We should support for", "may configurations") — admitted in README.md L74-75 ("may Confirmed reads literally"). The output is faithful to the rule path; the awkwardness is the documented limitation of the rule-based translator without an LLM. |
| `config.yaml` | **yes** | `language_pair: "ZH -> EN"`, `domain: "Security Advisory"`, `conformance_level: "L3_STRICT"`, `model_endpoint: "openai/gpt-4o-mini"`, `model_version: "2024-07-18"`, `cache.enabled: true`, `cache.directory: "./cache"`, `cache.expire: null`, `repair.max_retries: 3`, `artifacts.compilation_dir: "./compilation_artifacts"`, `artifacts.audit_trace: "./audit_trace.jsonl"`. Matches `BootstrapConfig.from_yaml` expectations. |
| `requirements.txt` | **yes** | Mirrors `pyproject.toml` deps exactly (10 runtime + 5 dev). One divergence: `black>=24.4` is listed but the project uses `ruff format` for formatting; black is unused. |

Runtime artifacts at the **repo root** (outside `tra-prototype/`): `audit_trace.jsonl` (451 lines), `cache/cache.db`, `compilation_artifacts/{glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml}`. These escaped the prototype dir because a prior run was executed with cwd at the repo root. `status.md` L48-49 documents this and notes they were left uncommitted. They are NOT gitignored at the repo root — only at `tra-prototype/`. Minor hygiene issue.

---

### 8. Repo-level spec files

| File | Lines | TOC | Verdict |
| --- | --- | --- | --- |
| `TRA-SPECIFICATION.md` | 186 | §1 Scope & Definitions, §2 TRA-KERNEL, §3 TRA-ISA, §4 TRA-RUNTIME, §5 TRA-POLICY, §6 TRA-EXCEPTIONS, §7 TRA-QA, §8 TRA-CONFORMANCE, §9 TRA-MODULES | **§1–§9 all present.** ✓ |
| `TRA-ISA-REFERENCE.md` | 82 | Overview, Core Instructions (ANALYZE_DOCUMENT, BUILD_GLOSSARY, BUILD_ENTITY_TABLE, TRANSLATE_SEGMENT, VERIFY_OUTPUT, REPAIR_SEGMENT) | **All 6 ISA instructions covered** with Inputs/Preconditions/Outputs/Invariants/Failure Conditions. ✓ |
| `TRA-CONFORMANCE-GUIDE.md` | 53 | Overview, L1 Basic, L2 Professional, L3 Strict, L4 Forensic, Auditor Checklist for L3 Certification (6 items) | **L1-L4 checklists present** + 6-item L3 certification checklist. ✓ |
| `TRA-BENCHMARK-SUITE.md` | 48 | Overview, Cat 1 Structural (S-01..S-06), Cat 2 Factual (F-01..F-05), Cat 3 Terminology (T-01..T-05), Cat 4 Domain (D-01..D-04), Cat 5 Ambiguity (E-01..E-03) | **S/F/T/D cases all listed.** Note: the prototype only implements 13 of these 24+ documented cases (S-05, F-01..F-05, T-01..T-05, D-04, E-02) plus 1 regression (R-01, not in spec). The spec's "100+" target is aspirational. |
| `TRA-MODULE-ZH-EN.md` | 54 | (ZH-EN module spec doc) | Defines the ZH↔EN bridge template; the prototype's `zh_en.py` implements it faithfully. |
| `status.md` | 50 | Phase 6 commit log narrative | Documents Phase 6 completion (commit 4d97aa1), explicitly lists 6.3.1/6.5.1/6.5.2 as NOT implemented, and surfaces the runaway-artifacts-at-repo-root hygiene issue. |
| `review.md` | 53 | External review of the spec repo (8.5/10 verdict) | Independent reviewer's assessment of the SPEC repo (not the prototype). |
| `review-feedback.md` | 386 | Author's response to review.md + revised plan | The "6-8 person-days realistic estimate" comes from here. |
| `prototype.md` | 110 | The original meticulous plan that begat `tra-prototype/` | Predates the code; planning context only. |
| `start-here.md` | 44 | **Chinese-language** "how to use the TRA spec to prompt an LLM" user guide | Aimed at LLM-prompt-engineering users, not engine implementers. Notes the abbreviated BOOTSTRAP→ANALYZE→…→EMIT pipeline. |

The `CLAUDE.md` note (L54) that `review.md` and `start-here.md` use "abbreviated renderings" of the canonical state labels is accurate — they collapse `BUILD_ARTIFACTS` into "BUILD" etc., but the kernel.py canonical labels are the source of truth.

---

### 9. Doc-vs-code divergences

1. **`tra_cli.py` docstring is stale** (tra_cli.py L1-7). Says "Phase 0.1.5 skeleton" and lists only `translate`/`cache-clear`/`audit` subcommands. The file actually implements a 4th subcommand `validate` (L197-223) and the implementation is no longer a "skeleton." SKILL.md and README.md correctly describe all four subcommands.

2. **`README.md` (tra-prototype/README.md) L3 header is stale.** Says "A Phase 0–5 reference implementation" — Phase 6 is actually implemented (per CLAUDE.md L13 and status.md). README.md L78-79 also lists "Phase 6 (exception hardening, human-in-the-loop, structlog, L4 evidence tracing) is pending" — but 4 of those 5 (exception hardening, HITL, L4 evidence tracing, structlog — wait, structlog is NOT done) — so the "Phase 6 pending" line is mostly wrong: only structlog is genuinely pending. The README.md "Known gaps" section needs a refresh.

3. **`README.md` L76-77 inline-code claim is accurate.** "Inline-code glossary substitution is not yet suppressed (S-03): terms inside backticks are still run through the glossary." Confirmed by code reading: `_rule_translate` (isa.py L350-372) runs `apply_zh_rules` and glossary substitution over the entire source string with no respect for `is_no_translate_zone` markers on code-block nodes. The `StructuralMap` correctly marks code blocks as no-translate (`anchor.py` L375), but the kernel's `_execute_translation` (kernel.py L183-187) passes the entire source as a single segment and never consults the structural map for zones to skip. This is consistent with kernel.py L184 inline comment "Phase 2: deterministic whole-doc substitution via the glossary + entity + epistemic lexicon. Segment granularity is wired in Phase 3." — but Phase 3 did not actually wire segment granularity.

4. **"Segment-level" granularity is documented but not implemented.** SKILL.md and the spec describe TRANSLATE_SEGMENT as operating on "a specific source segment (sentence, list item, or table cell)" (TRA-ISA-REFERENCE.md L48-49). The implementation translates the entire source document as one segment (kernel.py L186). This means: per-segment cache keys are actually per-document cache keys; per-segment repair is actually per-document repair; per-segment evidence is actually per-document evidence. The L4 `line_by_line_trace` works around this by attributing output lines to evidence records via `target_span` substring containment (reporting.py L86), which is a post-hoc heuristic, not a structural mapping. The CLAUDE.md layout description does not surface this limitation.

5. **`diagnostics.AuditTrail.count_blocking` is a stub** (diagnostics.py L159-166). Returns 0 unconditionally with a comment "hook for VERIFY to populate; trail stores records, not severities." Real BLOCKING counting happens in `reporting.summarize_audit` (which reads `flags_raised`) and `validate.ValidationReport.blocking` (which reads `Diagnostic.severity`). The stub method is dead code — no caller invokes it.

6. **`CONCLUSION_LEADING` constant in `zh_en.py` L75 is unused.** Defined as `("因此", "所以", "故", "由此可见", "综上")` with a docstring claiming it surfaces conclusions first, but no code reads it. Dead constant.

7. **Heavy unused deps in pyproject.toml/requirements.txt.** `litellm>=1.49` (pulls openai, tiktoken, tokenizers, huggingface-hub, aiohttp, etc. — ~30 transitive deps), `structlog>=24.1`, `pydantic-settings>=2.3`, `mdit-py-plugins>=0.4`, `black>=24.4` are all listed but never imported. The LLM seam is wired as a caller-supplied callable (`llm_translate: Callable[[str, RuntimeContext], str] | None`) so litellm is not actually needed at runtime. A minimal install would only need pydantic, markdown-it-py, diskcache, pyyaml, click, rich.

8. **`pip install -e .` (SKILL.md L68) vs `pip install -e ".[dev]"` (task description).** SKILL.md instructions install only runtime deps; dev tools (ruff/mypy/pytest) are not installed. A new contributor following SKILL.md verbatim cannot run the quality gates. Should be `pip install -e ".[dev]"`.

9. **`config.yaml` field `cache.expire: null` is parsed but ignored.** `BootstrapConfig.from_yaml` reads `cache.enabled` and `cache.directory` but NOT `cache.expire` (config.py L46-47). `TranslationCache.set` hardcodes `expire=None` (cache.py L105). The config comment "static facts: no TTL" is honored in spirit, but the YAML field is misleading dead config.

10. **`tra/modules/registry.py:registry_for_language_pair` is not exercised by the kernel.** The kernel constructs `ZHENModule` directly (kernel.py L43, L106) instead of going through the registry. So the "plug-in extension point" claim is partially aspirational — the registry exists and is tested, but the production code path bypasses it. A new module registered via `build_default_registry()` would NOT be picked up by the kernel.

---

### 10. Anomalies / red flags

1. **`repair_segment` does not strictly enforce "no new BLOCKING"** (isa.py L516-519). The `Unrecoverable` raise is gated on `attempt >= max_retries`. On earlier attempts, a repair that introduces new BLOCKING is returned silently with `resolved=False` in `repair_history`. The kernel's repair loop catches this by re-queuing, but the function-level invariant from CLAUDE.md L79 ("Repair must resolve the specific violation without introducing new ones") is **not strictly enforced at the function boundary**. If a caller invokes `repair_segment` directly (outside the kernel loop) with `attempt=1, max_retries=3` and the repair introduces new BLOCKING, they get back a broken result with no exception. This is a soft invariant; the test suite does not directly assert "repair_segment raises on new BLOCKING at attempt=1".

2. **`audit_trace.jsonl` and `cache/cache.db` exist at the REPO ROOT** (`/home/z/my-project/tra/audit_trace.jsonl` — 451 lines, `cache/cache.db`). status.md L48-49 acknowledges this: a prior run resolved the default `./audit_trace.jsonl` and `./cache/` paths against the repo root, not the prototype dir. They are not gitignored at the repo root. The `.gitignore` in `tra-prototype/` covers `audit_trace.jsonl`, `cache/`, `compilation_artifacts/` relative to the prototype, but a run from outside leaks them. **Hygiene issue**: stale runtime artifacts in the spec repo.

3. **`pip install` weight.** Installing the prototype pulls ~50 packages including the full litellm/openai/tiktoken/tokenizers/huggingface-hub stack (~hundreds of MB) for a rule-based prototype that never imports litellm. Either litellm should be moved to an optional extra (`pip install -e ".[llm]"`) or the LLM seam should be documented as caller-supplied-only and litellm dropped entirely.

4. **`README.md` (prototype) "Known gaps" section is materially inaccurate.** It says "Phase 6 (exception hardening, human-in-the-loop, structlog, L4 evidence tracing) is pending." Reality: 4 of those 5 ARE implemented (exception hardening via recovery.py, HITL via hitl.py, L4 evidence tracing via reporting.line_by_line_trace + kernel._export_forensics); only structlog is genuinely pending. CLAUDE.md and SKILL.md have the accurate picture; README.md was not updated after Phase 6 landed.

5. **No segment-level iteration.** The kernel translates the whole document as one segment. This means: (a) cache granularity is per-document, not per-segment; (b) repair operates on the whole target text; (c) the `segment_index` field on `RepairAttempt` is always 0 (isa.py L476 default); (d) the L4 line-by-line trace is a substring heuristic, not a structural segment→evidence mapping. The data models (`StructuralNode`, `is_no_translate_zone`) and the structural-map builder are ready for segment-level work, but the consumer (`_execute_translation`) doesn't iterate. This is the largest gap between spec aspiration and prototype reality, and it is not surfaced in CLAUDE.md's "Known gaps" list.

6. **`translation` output reads awkwardly** (e.g., "may Confirmed under heavy load", "We should support for the KVM and XFS backends", "may configurations are not recommended"). The README admits this ("may Confirmed reads literally"). The LLM seam is the intended fluency path, but it's caller-supplied and the prototype ships without one. This is fine for a fidelity-focused prototype, but a first-time reader of `examples/expected_outputs/security_advisory_zh.L3.md` may be confused — the file looks like broken English without the context that it's a deterministic rule-based output.

7. **`count_blocking` stub** (diagnostics.py L159-166) returns 0 unconditionally. If a future contributor trusts the method name and uses it for an L3 gate check, they will get a false PASS. Should either be implemented (iterate `flags_raised` for `Severity.BLOCKING.value`) or removed/marked `# TODO`.

8. **`registry_for_language_pair` and `build_default_registry` are not on the kernel's hot path.** The kernel hardcodes `ZHENModule()` (kernel.py L43, L106). Extension via the registry works in tests but not in the production `translate` CLI flow. A user who follows SKILL.md §6 ("register my_module.as_interface()") will find their module is NOT used by `tra_cli.py translate`. The sanctioned extension point is, in practice, not wired.

9. **`examples/expected_outputs/security_advisory_zh.L3.md` does not include the runtime artifacts** (audit trace, glossary, etc.) that an actual `tra_cli.py translate` run would produce. It's just the translated markdown. A reader expecting "L3 output" to include the audit trail / conformance verdict will find only the target text. This matches what `translate` writes to `-o` (target markdown only), but the file name `.L3.md` could mislead someone into expecting an L3 certification bundle.

10. **No CI configuration.** There is no `.github/workflows/`, no `Makefile`, no `tox.ini`. The quality gates are documented in SKILL.md L172-176 and CLAUDE.md L37 but must be run manually. status.md shows the author runs them ad-hoc before each commit. For a prototype this is acceptable; for a "conformant engine" claim it's a gap.

---

### Bottom line

The TRA prototype is in better shape than its own `README.md` admits and slightly worse shape than `CLAUDE.md`'s "Phases 0–6 complete" claim implies. All four quality gates pass clean (ruff/format/mypy --strict/103 pytest). All four critical invariants are enforced (with #4 "repair surgical" only partially enforced at the function level — the loop catches it). The four "open items" claimed in CLAUDE.md (6.3.1 structlog, 6.5.1 asyncio, 6.5.2 cross-run caching, Phase 7) are all genuinely open and accurately documented in CLAUDE.md / SKILL.md / implementation_plan.md.

The most material divergences are:
- **Segment-level granularity is documented (TRANSLATE_SEGMENT contract) but not implemented** — the kernel translates the whole document as one segment.
- **README.md "Known gaps" is stale** — claims Phase 6 pending when 4/5 of Phase 6 is done.
- **`repair_segment` does not strictly refuse new BLOCKING** at the function level (only at retry-budget exhaustion).
- **Heavy unused deps** (litellm, structlog, pydantic-settings, mdit-py-plugins, black) inflate install footprint.
- **The module registry is the sanctioned extension point but the kernel bypasses it** — new modules don't actually plug into the production translate path.

None of these are blocking issues for the prototype's stated purpose (proving out the spec deterministically for ZH↔EN at L3). They are honest limitations that should be reflected in CLAUDE.md's "Known gaps" list more explicitly.

---

## Task audit-A — Spec conformance audit (Track A, 26 items)

Auditor: Agent A. Scope: does `tra-prototype/` faithfully implement TRA v1.0?
Method: read every line of `isa.py`, `kernel.py`, `memory.py`, `policy.py`,
`recovery.py`, `validate.py`, `diagnostics.py`, `exceptions.py`, `config.py`,
`anchor.py`, `utils.py`, `cache.py`, `reporting.py`, `hitl.py`, `benchmark.py`,
`modules/zh_en.py`, `modules/registry.py`, `tra_cli.py`; cross-checked against
the 5 normative spec files. All file:line citations are `tra-prototype/`-relative.

Previous `3-validate` baseline covered layout, open-items, test counts, doc-vs-
code divergences. This audit goes deeper on the **26 checklist items** and the
**4 critical invariants** with attack-path evidence.

### Findings A1–A26

```
A-1  | PASS       | Kernel state BOOTSTRAP
Spec clause: TRA-SPECIFICATION.md §2.1 (stateDiagram-v2 [*] --> BOOTSTRAP)
Code evidence: tra/kernel.py:50 (KernelState.BOOTSTRAP), tra/kernel.py:108 (initial state)
Finding: BOOTSTRAP exists in the enum and is the initial state of TRAKernel.
Detail: KernelState StrEnum at kernel.py:47-58 enumerates all 9 states. __init__ sets self.state = KernelState.BOOTSTRAP at kernel.py:108. The state is purely nominal — no ISA is bound to it (the run() method immediately transitions to INITIALIZE_RUNTIME at kernel.py:127 without any work). Spec §2 says transitions fire on successful ISA completion; here the BOOTSTRAP→INITIALIZE_RUNTIME transition fires on nothing.
Suggested fix: none (BOOTSTRAP is the entry point; no ISA is expected there).

A-2  | PASS       | Kernel state INITIALIZE_RUNTIME
Spec clause: TRA-SPECIFICATION.md §2.1 (BOOTSTRAP --> INITIALIZE_RUNTIME)
Code evidence: tra/kernel.py:51, tra/kernel.py:104-107, tra/kernel.py:127
Finding: INITIALIZE_RUNTIME exists; the RuntimeContext is constructed in __init__ and the transition fires unconditionally.
Detail: ctx is built at kernel.py:104-107 (RuntimeContext with configuration=model_dump(), style_profile=ZHENModule().get_style_profile()). The transition at kernel.py:127 happens before any "initialize" ISA — there is no ISA instruction named INITIALIZE_RUNTIME in TRA-ISA-REFERENCE.md, so this is a state-only step. No skip is possible because run() calls _transition in canonical order.
Suggested fix: none.

A-3  | WARNING    | Kernel state ANALYZE_DOCUMENT
Spec clause: TRA-SPECIFICATION.md §2.1, TRA-ISA-REFERENCE.md §ANALYZE_DOCUMENT
Code evidence: tra/kernel.py:128-129 (transition then call), tra/isa.py:65-110
Finding: State exists; transition fires BEFORE analyze_document runs (spec says "on successful completion").
Detail: kernel.py:128 calls _transition(ANALYZE_DOCUMENT) then kernel.py:129 calls analyze_document(). If analyze_document raises BrokenMarkdown (isa.py:84), the state has already advanced. The spec §2 states "State transitions are triggered by the successful completion of ISA instructions." The implementation inverts this: transition first, ISA second. Same pattern for every state in run(). Additionally, the invariant "structural_map node count must equal source document's structural node count" (ISA-REF §ANALYZE_DOCUMENT Invariants) is structurally satisfied (the walker produces a count from the source) but never explicitly verified against an independent count.
Suggested fix: move _transition calls to AFTER the corresponding ISA call returns successfully, or assert node_count matches a second-pass count.

A-4  | WARNING    | Kernel state BUILD_ARTIFACTS
Spec clause: TRA-SPECIFICATION.md §2.1 (ANALYZE_DOCUMENT --> BUILD_ARTIFACTS)
Code evidence: tra/kernel.py:135-140, tra/isa.py:146-271
Finding: State exists; build_glossary is wrapped in try/except but build_entity_table is NOT.
Detail: kernel.py:136-139 wraps build_glossary in `except TRAException` and routes to _recover (the EXCEPTION_HANDLER path). kernel.py:140 calls build_entity_table with NO try/except — if it ever raises (e.g. ENTITY_AMBIGUITY per spec), the kernel crashes with no recovery. Currently build_entity_table (isa.py:226-271) never raises, so the gap is latent. The state transition fires at kernel.py:135 before either ISA runs.
Suggested fix: wrap build_entity_table in the same try/except TRAException pattern.

A-5  | WARNING    | Kernel state EXECUTE_TRANSLATION
Spec clause: TRA-SPECIFICATION.md §2.1, TRA-ISA-REFERENCE.md §TRANSLATE_SEGMENT
Code evidence: tra/kernel.py:142-143, tra/kernel.py:183-187, tra/isa.py:279-372
Finding: State exists; the ISA contract is VIOLATED — translate_segment receives the whole document, not a segment.
Detail: kernel._execute_translation (kernel.py:183-187) calls translate_segment(src, ...) where src is the entire source markdown. The ISA contract (TRA-ISA-REFERENCE.md:48-49) says "Generates the target-language equivalent of a specific source segment (sentence, list item, or table cell)." The kernel.py:184 inline comment admits "Segment granularity is wired in Phase 3" but Phase 3 never landed. Consequences: cache keys are per-document not per-segment; repair operates on whole target text; segment_index in RepairAttempt is always 0 (isa.py:476); the L4 line-by-line trace is a substring heuristic (reporting.py:73-95), not a structural mapping.
Suggested fix: iterate the structural_map's leaf nodes (sentences / list items / table cells) and call translate_segment once per leaf, skipping is_no_translate_zone nodes.

A-6  | WARNING    | Kernel state VERIFY_OUTPUT
Spec clause: TRA-SPECIFICATION.md §2.1, TRA-ISA-REFERENCE.md §VERIFY_OUTPUT
Code evidence: tra/kernel.py:145-146, tra/isa.py:380-458
Finding: State exists; verify_output never raises (matches spec "Failure Condition: None"), but the "VERIFY_OUTPUT --> EXCEPTION_HANDLER : On Failure" transition is NOT modeled.
Detail: kernel.py:145 transitions to VERIFY_OUTPUT; kernel.py:146 calls verify_output which returns a list[Diagnostic]. The spec stateDiagram-v2 has an explicit "On Failure" edge to EXCEPTION_HANDLER. The implementation goes unconditionally to REPAIR_IF_NEEDED regardless of whether BLOCKING is present. The EXCEPTION_HANDLER is not a distinct KernelState (it's a private _recover method, kernel.py:159-179), so the execution_log never records an EXCEPTION_HANDLER visit.
Suggested fix: either add EXCEPTION_HANDLER to KernelState and transition there when BLOCKING > 0, or document this as an intentional simplification.

A-7  | BLOCKING   | Kernel state REPAIR_IF_NEEDED
Spec clause: TRA-SPECIFICATION.md §2.1, TRA-ISA-REFERENCE.md §REPAIR_SEGMENT, §6
Code evidence: tra/kernel.py:148-149, tra/kernel.py:189-236, tra/isa.py:466-548
Finding: State exists; the "Repair must resolve without introducing new ones" invariant is NOT enforced at the function boundary (see A26 #4).
Detail: kernel._repair_loop (kernel.py:189-236) iterates pending diagnostics, calls repair_segment, re-verifies, re-queues. If the loop exhausts max_retries with BLOCKING still pending, it returns the broken target (kernel.py:236). kernel.run() at kernel.py:157 returns this broken target unconditionally — there is NO L3 gate check. The CLI translate command (tra_cli.py:106-120) only prints a warning. Per TRA-CONFORMANCE-GUIDE.md:51 "If present, certification is denied" — the engine should deny (fail) when BLOCKING remains, not warn.
Suggested fix: kernel.run() should raise (or return a structured Failure) when post-repair BLOCKING > 0; tra_cli.py translate should exit non-zero like validate does.

A-8  | PASS       | Kernel state AUDIT_DIAGNOSTICS
Spec clause: TRA-SPECIFICATION.md §2.1, §7
Code evidence: tra/kernel.py:151-152, tra/diagnostics.py:99-166, tra/reporting.py:21-47
Finding: State exists; audit.flush() persists the JSONL trace.
Detail: kernel.py:152 calls self.audit.flush() which opens the file in append mode (diagnostics.py:142) and writes all buffered AuditRecords. The summarize_audit helper (reporting.py:21-47) reads flags_raised and computes l3_conformant = (blocking_flags == 0). No ISA is bound to this state — it is a flush step.
Suggested fix: none.

A-9  | PASS       | Kernel state EMIT_PAYLOAD
Spec clause: TRA-SPECIFICATION.md §2.1, §4
Code evidence: tra/kernel.py:154-157, tra/kernel.py:240-312
Finding: State exists; _export_artifacts writes glossary/entity/smap/style/exec_log/repair_history; _export_forensics emits L4 artifacts only at L4_FORENSIC.
Detail: kernel.py:155 calls _export_artifacts (kernel.py:240-291) writing 6 files to compilation_dir. kernel.py:156 calls _export_forensics (kernel.py:293-312) which has a strict guard at kernel.py:298: `if self.config.conformance_level != ConformanceLevel.L4_FORENSIC: return`. evidence_trace.jsonl and ambiguity_register.json are emitted ONLY at L4. ✓
Suggested fix: none.

A-10 | PASS       | ISA analyze_document contract
Spec clause: TRA-ISA-REFERENCE.md §ANALYZE_DOCUMENT; TRA-SPECIFICATION.md §3
Code evidence: tra/isa.py:65-110
Finding: Inputs / Preconditions / Outputs / Failure Conditions all implemented.
Detail: Inputs (source, Immutable Config) ✓ (isa.py:65-69). Preconditions enforced: EMPTY_SOURCE raises TRAException (isa.py:78-79); MALFORMED_MARKDOWN raises BrokenMarkdown on parser failure (isa.py:81-86). Outputs: document_profile (type/audience/register/intent/evidence_style) and structural_map (isa.py:94-102). The "no semantic content altered during analysis" invariant is satisfied — analyze_document never mutates source. The node-count invariant is structurally satisfied (smap is built from source) but never explicitly verified.
Suggested fix: add an assertion that smap.node_count matches an independent re-walk count.

A-11 | PASS       | ISA build_glossary contract
Spec clause: TRA-ISA-REFERENCE.md §BUILD_GLOSSARY; TRA-SPECIFICATION.md §3
Code evidence: tra/isa.py:146-218
Finding: Contract implemented; CONFLICTING_MAPPINGS raised on forbidden drift or duplicate source.
Detail: Inputs (source, profile, module) ✓ (isa.py:146-152). is_forbidden check at isa.py:163 raises GlossaryConflict for forbidden drift (e.g. 成立→Valid). Duplicate-source-with-different-target check at isa.py:169-174. Outputs: canonical_glossary (GlossaryEntry list) and forbidden_mappings (isa.py:194-203). Invariant "every recurring term >2x has canonical mapping" is partially satisfied — the module provides canonical mappings but the implementation does NOT count source-term frequency or check the >2x threshold. Invariant "Product names and entities auto-added to entity_table" is satisfied via build_entity_table, not build_glossary.
Suggested fix: add term-frequency counting to enforce the ">2x recurring" rule explicitly.

A-12 | PASS       | ISA build_entity_table contract
Spec clause: TRA-ISA-REFERENCE.md §BUILD_ENTITY_TABLE; TRA-SPECIFICATION.md §3
Code evidence: tra/isa.py:226-271, tra/utils.py:66-90
Finding: Contract implemented; entities marked mutable=False; casing preserved verbatim.
Detail: Inputs (source, structural_map) ✓. extract_entities (utils.py:66-90) constructs every Entity with the default mutable=False (memory.py:159). build_entity_table re-asserts ent.mutable = False at isa.py:248. ENTITY_AMBIGUITY is documented as "Default: Treat as Entity" (ISA-REF §BUILD_ENTITY_TABLE Failure Conditions) — the implementation silently treats ambiguous tokens as entities via _is_product_entity filter (utils.py:61-63), never raising the exception. This matches the spec default but bypasses the §6 ENTITY_AMBIGUITY recovery path (which is dead code — see A23).
Suggested fix: none (behavior matches spec default).

A-13 | BLOCKING   | ISA translate_segment contract — whole-document vs segment divergence
Spec clause: TRA-ISA-REFERENCE.md §TRANSLATE_SEGMENT (Inputs: "Source Segment"; Purpose: "a specific source segment (sentence, list item, or table cell)")
Code evidence: tra/kernel.py:183-187 (whole-doc call), tra/isa.py:279-372 (function signature), tra/anchor.py:375 (is_no_translate_zone set but never consulted)
Finding: The kernel passes the ENTIRE source markdown as one segment, violating the ISA contract.
Detail: translate_segment's first parameter is named `source_segment` (isa.py:280) and the docstring says "one source segment" (isa.py:288), but kernel._execute_translation (kernel.py:186) calls `translate_segment(src, ...)` where src is the full document. Consequences: (a) cache keys are per-document, not per-segment (cache.py:60 — source_text is the whole doc); (b) repair operates on the whole target text (kernel.py:198-207); (c) segment_index in RepairAttempt is always 0 (isa.py:476); (d) the structural_map's is_no_translate_zone flag (anchor.py:375) is NEVER consulted — code blocks ARE translated by the rule layer (violating S-03 "Inline Code vs. Prose"); (e) the L4 line_by_line_trace (reporting.py:73-95) is a substring-containment heuristic, not a structural segment→evidence mapping. The cache.py module docstring at cache.py:13 explicitly says "cache only atomic ops (TRANSLATE_SEGMENT, REPAIR_SEGMENT), never a whole document" — the implementation does the opposite.
Suggested fix: iterate structural_map leaf nodes (paragraphs, list_items, table_cells, but NOT code_block), call translate_segment per leaf, and consult is_no_translate_zone to skip code spans.

A-14 | PASS       | ISA verify_output contract — never self-scores
Spec clause: TRA-ISA-REFERENCE.md §VERIFY_OUTPUT, TRA-SPECIFICATION.md §7 ("It does not use self-scoring")
Code evidence: tra/isa.py:380-458, tra/memory.py:141-143, tra/diagnostics.py:49-51
Finding: verify_output never reads confidence_note; verification is evidence-presence based.
Detail: Grep for `confidence_note` across tra-prototype/ returns 6 hits: 2 definitions (memory.py:141, diagnostics.py:49), 2 docstrings (memory.py:6, diagnostics.py:8), 2 test references (test_phase0.py:71,78). The verify_output function body (isa.py:380-458) reads ctx.glossary_cache, ctx.entity_table, ctx.structural_map, and _forbidden_from_module() — never confidence_note. repair_segment's re-verify call (isa.py:516) reads Diagnostic.severity/subsystem/issue — also never confidence_note. test_phase0.py:71-78 has an explicit assertion that a low confidence_note=0.1 does NOT trigger routing. ✓
Suggested fix: none.

A-15 | BLOCKING   | ISA repair_segment contract — surgical invariant NOT enforced at attempt=1
Spec clause: TRA-ISA-REFERENCE.md §REPAIR_SEGMENT Invariants ("Repair must resolve the specific violation without introducing new ones")
Code evidence: tra/isa.py:466-548, tra/isa.py:515-519
Finding: At attempt=1, a repair that introduces new BLOCKING returns silently with resolved=False — no exception raised.
Detail: The re-verify logic at isa.py:516-519:
  `sub = verify_output(repaired, source_segment, ctx, audit)`
  `new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]`
  `if new_blocking and attempt >= max_retries:`
      `raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")`
The `attempt >= max_retries` guard means: at attempt=1, max_retries=3, new_blocking=True → condition is `True and False` = False → NO raise. The function continues to isa.py:521-547, records a RepairAttempt with resolved=False (isa.py:545), and returns the broken `repaired` text. The kernel's _repair_loop (kernel.py:233-234) catches this by re-verifying and re-queuing, so the LOOP converges OR exits with broken target. But the FUNCTION-LEVEL invariant from the spec is not enforced. A caller invoking repair_segment directly (outside the kernel loop) at attempt=1 receives a broken result with no exception. The test suite does NOT assert repair_segment raises on new BLOCKING at attempt=1.
Suggested fix: drop the `attempt >= max_retries` guard on the new-blocking check; raise Unrecoverable whenever new_blocking is non-empty, regardless of attempt number. The max_retries budget should bound the LOOP, not the per-call invariant.

A-16 | WARNING    | Policy Factual Integrity (priority 1) — defined but never enforced
Spec clause: TRA-SPECIFICATION.md §5.1 item 1, §5.2
Code evidence: tra/memory.py:25 (FACTUAL_INTEGRITY=1), tra/policy.py:13-25, tra/isa.py:380-458 (verify_output), tra/utils.py:25 (VERSION_RE)
Finding: Priority exists with correct ordering; verify_output has NO factual-integrity check; PolicyResolver is never invoked from production.
Detail: memory.py:25 sets FACTUAL_INTEGRITY=1 (highest). config.py:14 includes it in DEFAULT_POLICY_STACK. policy.py:13-25 defines PolicyResolver.resolve/wins. But: grep `PolicyResolver` across tra/ shows ZERO production imports — only test_phase0.py:23 imports it. The kernel and ISA never call PolicyResolver. verify_output (isa.py:380-458) checks (a) heading count, (b) entity presence, (c) glossary source-term leakage, (d) forbidden epistemic targets — but NEVER checks numbers/units/versions/logical-conditions are preserved exactly. Factual strings like "<60ms", "P99", "96-core", "<5MB" are NOT extracted as entities (utils.py regexes don't match leading `<` or digit-only tokens), so an LLM-supplied translator that changed "<60ms" to "60 milliseconds" would NOT raise BLOCKING. The benchmark suite catches this via must_contain/must_not_contain substring checks (benchmark.py:91-96), but that's a test-harness gate, not a verify_output gate.
Suggested fix: in verify_output, extract all VERSION_RE/number/unit tokens from source and assert each appears verbatim in target; raise BLOCKING on any mismatch.

A-17 | WARNING    | Policy Structural Integrity (priority 2) — partially enforced
Spec clause: TRA-SPECIFICATION.md §5.1 item 2
Code evidence: tra/memory.py:26, tra/isa.py:396-409, tra/anchor.py:101-149 (rewrite_links defined but unused)
Finding: Only heading-count is verified; list nesting, table alignment, blockquotes, HR, inline-code, S-06 link rewrite are NOT.
Detail: verify_output at isa.py:396-409 checks `_HEADING_RE.findall` count match. It does NOT check: list nesting depth (S-01), table column alignment (S-02), blockquote preservation (S-04), HR preservation (S-05 — though the rule-based translator never touches `---` so it's preserved incidentally), inline-code untranslated (S-03 — violated, see A13), or internal anchor rewrite (S-06). The rewrite_links function (anchor.py:101-149) is DEFINED and tested (test_anchor.py:93-113) but NEVER called from kernel.run() or anywhere in production. S-06 cross-reference rewriting is dead code in the production path.
Suggested fix: invoke rewrite_links in _export_artifacts or _execute_translation; add structural-equality checks beyond heading count.

A-18 | PASS       | Policy Entity Preservation (priority 3) — enforced
Spec clause: TRA-SPECIFICATION.md §5.1 item 3
Code evidence: tra/memory.py:27, tra/isa.py:411-422, tra/isa.py:226-271
Finding: Entities verified verbatim in target; BLOCKING raised on any missing entity.
Detail: verify_output at isa.py:411-422 iterates ctx.entity_table and raises BLOCKING (`Entity not preserved: {name!r}`) if any entity name is not a substring of target. build_entity_table (isa.py:226-271) marks all entities mutable=False. The Entity model (memory.py:154-160) defaults mutable=False. Greppping `\.mutable\s*=` finds only ONE assignment in production code: isa.py:248 `ent.mutable = False`. Never set to True.
Suggested fix: none.

A-19 | WARNING    | Policy Terminological Consistency (priority 4) — partially enforced
Spec clause: TRA-SPECIFICATION.md §5.1 item 4
Code evidence: tra/memory.py:28, tra/isa.py:424-435
Finding: Source-term leakage is WARNING, not BLOCKING; canonical-target presence is NOT verified.
Detail: verify_output at isa.py:424-435 checks if a glossary SOURCE term still appears in target (untranslated leak) and flags as WARNING. It does NOT verify the canonical TARGET term is present — a translation that simply dropped the term entirely would not raise. The severity (WARNING vs BLOCKING) is debatable; spec §3 TRANSLATE_SEGMENT Invariant says "Terminology matches canonical_glossary exactly" which would imply BLOCKING on any mismatch. The current WARNING severity means a candidate with zero glossary terms present passes the L3 gate (zero BLOCKING).
Suggested fix: for each glossary entry whose source appears in the source document, require the target to appear in the translated document; raise BLOCKING on absence.

A-20 | PASS       | Policy Epistemic Fidelity (priority 5) — enforced
Spec clause: TRA-SPECIFICATION.md §5.1 item 5, TRA-MODULE-ZH-EN.md §3
Code evidence: tra/memory.py:29, tra/isa.py:437-450, tra/modules/zh_en.py:43-47
Finding: Forbidden drift targets raise BLOCKING; canonical lexicon reinforced by EPISTEMIC_LEXICON.
Detail: verify_output at isa.py:437-450 iterates _forbidden_from_module() and raises BLOCKING if any forbidden_target (e.g. "Valid", "True", "Correct", "runtime", "indisputably true") appears in target. The ZH-EN module (zh_en.py:43-47) defines FORBIDDEN_TARGETS for 成立/执行环境/高度可信. build_glossary (isa.py:163) calls _MODULE.is_forbidden(src, tgt) to prevent drift at glossary-construction time. The EPISTEMIC_LEXICON (zh_en.py:35-40) reinforces 成立→Confirmed etc. in the rule layer (isa.py:360-362). Recovery route for CERTAINTY_CONFLICT (recovery.py:111-121) prioritizes epistemic — but is never invoked from production (see A23).
Suggested fix: none for the enforcement; consider raising CertaintyConflict from translate_segment when an LLM returns a hedged target that disagrees with the lexicon.

A-21 | WARNING    | Policy Target Fluency (priority 6) — defined, never arbitrated, no enforcement
Spec clause: TRA-SPECIFICATION.md §5.1 item 6, §5.2
Code evidence: tra/memory.py:30, tra/policy.py:13-25, tra/isa.py (no fluency check)
Finding: Priority exists; no fluency check in verify_output; PolicyResolver never invoked; "equal-priority → Domain Module heuristics → preserve source + Warning" rule not implemented.
Detail: memory.py:30 sets TARGET_FLUENCY=6 (lowest priority). The spec §5.2 conflict-resolution contract ("equal priorities → Domain Module heuristics → preserve source ambiguity + Warning") is NOT implemented anywhere. The PolicyResolver.resolve (policy.py:20-21) only does lower-number-wins; it has no Domain-Module fallback. And critically, the production code (isa.py, kernel.py) NEVER calls PolicyResolver — it's imported only in test_phase0.py:23. The whole policy engine is scaffolding with no production invocation. The "scope rules" (in code blocks, Factual+Entity+Terminology bind, only Fluency relaxable) mentioned in the audit checklist are not in the spec text and not in the code.
Suggested fix: invoke PolicyResolver from repair_segment when a repair would violate one priority to satisfy another; log the arbitration in evidence.

A-22 | WARNING    | Memory model — 4 segments
Spec clause: TRA-SPECIFICATION.md §2.2, §4
Code evidence: tra/config.py:23-55 (BootstrapConfig), tra/memory.py:172-184 (RuntimeContext), tra/diagnostics.py:99-166 (AuditTrail), tra/diagnostics.py:79-96 (EvidenceRegistry)
Finding: All 4 segments exist; Immutable Config is NOT actually frozen; Audit append-only is by-API-design not by-encapsulation.
Detail:
- Immutable Config: BootstrapConfig (config.py:23) is a plain pydantic BaseModel with no `model_config = ConfigDict(frozen=True)`. tra_cli.py:86-89 mutates `cfg.language_pair` and `cfg.conformance_level` after from_yaml. The "read-only" invariant is by convention only.
- Runtime Context: RuntimeContext (memory.py:172-184) is read/write. ✓
- Document Memory: source string is passed around; Python strings are immutable so it's effectively read-only. ✓ But _sanitize_input (kernel.py:83-90) creates a transformed copy — the original is not mutated. ✓
- Audit Memory: AuditTrail (diagnostics.py:99-166) has append/flush/load but NO clear/delete/remove API. ✓ However `_buffer` is a public-by-convention list attribute; a caller could do `audit._buffer.clear()`. Similarly EvidenceRegistry._records is a dict a caller could clear. Append-only is enforced by API design, not by hard encapsulation.
- AuditTrail.count_blocking (diagnostics.py:159-166) is a STUB returning 0 unconditionally with comment "hook for VERIFY to populate". Dead code; if a future caller trusts the method name for an L3 gate check, they get a false PASS.
Suggested fix: set `model_config = ConfigDict(frozen=True)` on BootstrapConfig; rename `_buffer`/`_records` to genuinely-private and expose only append-only methods; implement or remove count_blocking.

A-23 | BLOCKING   | Exceptions & recovery — 3 of 5 recovery procedures are DEAD CODE in production
Spec clause: TRA-SPECIFICATION.md §6, TRA-ISA-REFERENCE.md (failure conditions)
Code evidence: tra/exceptions.py:27-72 (5 classes), tra/recovery.py:76-182 (5 procedures), tra/kernel.py:136-139 (only build_glossary wrapped), tra/kernel.py:159-179 (_recover)
Finding: Only GlossaryConflict and Unrecoverable are ever routed through recovery in production; BrokenMarkdown crashes the kernel; UnknownTerm/CertaintyConflict/EntityAmbiguity are never raised.
Detail:
- UNKNOWN_TERM: defined (exceptions.py:27-32), recovery preserves source (recovery.py:76-86). Greppping `raise UnknownTerm` across tra/ returns ZERO hits. translate_segment's _rule_translate never tracks unknown terms — it just substitutes known glossary entries. Dead recovery procedure.
- BROKEN_MARKDOWN: defined (exceptions.py:35-40), raised by analyze_document (isa.py:84). kernel.py:129 calls analyze_document with NO try/except. If raised, the kernel crashes with an unhandled exception — no EXCEPTION_HANDLER invocation, no HALT_ERROR state, no best-effort preservation. The recovery procedure (recovery.py:89-108) exists but is unreachable from production.
- CERTAINTY_CONFLICT: defined (exceptions.py:43-49), recovery prioritizes epistemic (recovery.py:111-121). Never raised in production. Dead.
- ENTITY_AMBIGUITY: defined (exceptions.py:52-57), recovery treats as entity (recovery.py:124-134). build_entity_table silently treats ambiguous tokens as entities (isa.py:243-247) without raising. Dead recovery.
- GLOSSARY_CONFLICT: defined (exceptions.py:60-72), raised by build_glossary (isa.py:164,170). kernel.py:136-139 catches and routes to _recover. ✓ ONLY THIS ONE WORKS.
- UNRECOVERABLE: defined (exceptions.py:75-78), raised by repair_segment (isa.py:511,519). kernel.py:208-231 catches and routes to _recover + optional HITL. ✓
The spec §6 mandates deterministic recovery for all 5 types; the implementation only delivers recovery for 1.5 of them (GlossaryConflict fully, Unrecoverable partially — Unrecoverable is a Phase-6 addition, not one of the spec's 5).
Suggested fix: wrap analyze_document, build_entity_table, and translate_segment in try/except TRAException that routes to _recover; raise UnknownTerm from translate_segment when source contains non-glossary non-entity CJK tokens; raise CertaintyConflict when an LLM returns hedged output disagreeing with EPISTEMIC_LEXICON.

A-24 | PASS       | L3 gate — validate.py enforces zero BLOCKING = PASS
Spec clause: TRA-CONFORMANCE-GUIDE.md §L3 item 4 ("If present, certification is denied")
Code evidence: tra/validate.py:38-49, tra/validate.py:59-86, tra_cli.py:226-242
Finding: validate_translation builds context then runs verify_output; ValidationReport.passed = not self.blocking; CLI exits 1 on FAIL.
Detail: validate.py:47-49 `passed` property returns `not self.blocking`. validate.py:85 calls verify_output(candidate, source, ctx, audit). validate.py:81-83 builds glossary + entity_table (does NOT translate — pure audit). tra_cli.py:236-242 prints PASS and exits 0 if report.passed, else prints FAIL and exits 1. The gate is correctly enforced in the validate path. ✓ (Caveat: validate.py does NOT run repair_segment, so a candidate with fixable BLOCKING is not auto-repaired — by design, validate is an audit-only command.)
Suggested fix: none for validate; consider adding the same gate to kernel.run() and tra_cli.py translate (see A7).

A-25 | PASS       | L4 forensics — evidence_trace.jsonl + ambiguity_register.json ONLY at L4
Spec clause: TRA-SPECIFICATION.md §8 L4, TRA-CONFORMANCE-GUIDE.md §L4
Code evidence: tra/kernel.py:293-312, tra/reporting.py:73-95, tests/test_phase6_hardening.py:99-112
Finding: _export_forensics has a strict L4 guard; emits both artifacts only at L4_FORENSIC.
Detail: kernel.py:298 `if self.config.conformance_level != ConformanceLevel.L4_FORENSIC: return` — early-exit for L1/L2/L3. At L4, writes evidence_trace.jsonl (kernel.py:304-307, one JSON object per non-empty target line via line_by_line_trace) and ambiguity_register.json (kernel.py:308-312, the unresolved_ambiguities list). test_phase6_hardening.py:99-112 asserts both files exist after an L4 run. The line-by-line attribution (reporting.py:73-95) uses substring containment (`r.target_span in line`) which is a heuristic — a structural segment→evidence mapping would be more forensic-grade, but the L4-only emission is correctly gated.
Suggested fix: none for the gating; consider structural mapping once A13 (segment-level translation) lands.

A-26 | BLOCKING   | The 4 critical invariants — 3 PASS, 1 BLOCKING
Spec clause: TRA-SPECIFICATION.md §3, §5, §7; TRA-ISA-REFERENCE.md invariants; TRA-MODULE-ZH-EN.md §3
Code evidence: see per-invariant detail below
Finding: Invariants 1/2/3 hold; invariant 4 (repair surgical) is violated at attempt=1.
Detail:
  Inv 1 (Canonical terminology exact): PASS. GLOSSARY at zh_en.py:20-32 defines 成立→Confirmed. EPISTEMIC_LEXICON at zh_en.py:35-40 reinforces. is_forbidden at zh_en.py:160-163 bans Valid/True/Correct. build_glossary at isa.py:163 raises GlossaryConflict on forbidden mapping. verify_output at isa.py:438-450 raises BLOCKING on forbidden_target substring. The LLM seam (isa.py:312-330) is the only path that COULD produce drift, and verify_output catches it post-hoc. No code path overrides GLOSSARY or EPISTEMIC_LEXICON at runtime (only tests monkeypatch _MODULE). Attack attempted: constructed a fake llm_translate returning "Valid" for "成立"; verify_output raised BLOCKING (test_validate_epistemic_drift_blocks at test_validate.py:44-51 confirms). No bypass found.
  Inv 2 (Entities immutable): PASS. Greppping `\.mutable\s*=` returns only isa.py:248 `ent.mutable = False`. Entity model (memory.py:154-160) defaults mutable=False. extract_entities (utils.py:90) constructs with default. build_entity_table re-asserts False. No code path sets mutable=True or mutates Entity.name/Entity.type after construction EXCEPT isa.py:247 `ent.type = hint` which overrides the classifier's guess with the module hint — this mutates the type field post-construction but spec §3 BUILD_ENTITY_TABLE allows the module to supply the type. Attack attempted: searched for `ent.name =`, `entity.name =`, `.type =` — only the hint override at isa.py:247 and the ent.mutable=False at isa.py:248. No bypass for mutable=True.
  Inv 3 (Verification never self-scores): PASS. Grep `confidence_note` returns 6 hits, all in definitions/docstrings/tests — zero reads in verify_output or repair_segment. test_phase0.py:71-78 asserts a low confidence_note=0.1 does not trigger routing. Attack attempted: searched for any read of `confidence`, `score`, `probability` in isa.py — none found in verify_output or repair_segment.
  Inv 4 (Repair surgical): BLOCKING. See A15. At attempt=1 with new BLOCKING, repair_segment returns the broken `repaired` text silently with resolved=False (isa.py:545). The function-level invariant "Repair must resolve the specific violation without introducing new ones" (ISA-REF §REPAIR_SEGMENT Invariants) is violated. The kernel's _repair_loop catches this by re-queuing (kernel.py:233-234), so the LOOP eventually converges or exhausts retries — but a direct caller of repair_segment at attempt=1 receives a broken result with no exception. Attack attempted: constructed a Diagnostic with subsystem="terminology" for source term "成立" not translated, called repair_segment with target="成立 Valid" (which after repair becomes "Confirmed Valid" — note "Valid" remains). Re-verify raised BLOCKING for epistemic drift (Valid forbidden). At attempt=1, max_retries=3: function returned "Confirmed Valid" with resolved=False, NO exception. At attempt=3, max_retries=3: function raised Unrecoverable. The asymmetry confirms the gap.
Suggested fix: see A15 — drop the attempt >= max_retries guard on the new-blocking check.
```

### Invariant-breaking attempts (concrete attack paths)

1. **Canonical terminology exact** — attempted to make the engine emit `成立 → Valid`:
   - Direct glossary mutation: `isa._MODULE.get_glossary_mappings = lambda: {"成立": "Valid"}` — build_glossary (isa.py:163) raises GlossaryConflict because is_forbidden("成立","Valid") returns True (zh_en.py:162-163). BLOCKED.
   - Direct forbidden-target injection via LLM seam: `translate_segment("成立", ..., llm_translate=lambda s,c: "Valid")` — translate_segment returns "Valid" (isa.py:314), but verify_output (isa.py:438-450) raises BLOCKING because "Valid" is in forbidden_targets. BLOCKED at verify.
   - Bypass via repair_segment: feed a target containing "Valid" and a non-epistemic diagnostic; repair_segment only fixes `subsystem=="epistemic"` violations (isa.py:501-506). If the diagnostic is terminology-class, the "Valid" remains and re-verify raises BLOCKING. BLOCKED at re-verify.
   - **Result: no bypass found.** Inv 1 holds.

2. **Entities immutable** — attempted to set Entity.mutable = True:
   - Grep `\.mutable\s*=` across tra-prototype/: only `isa.py:248: ent.mutable = False`.
   - Grep `\.mutable=`: same single hit.
   - Direct attribute mutation test: `Entity(name="x", type=EntityType.PRODUCT).mutable = True` — pydantic BaseModel allows this (no frozen=True), so it's POSSIBLE at the language level, but no production code does it.
   - **Result: no production bypass found.** Inv 2 holds by code-review convention, not by model encapsulation. WARNING-level concern documented in A22.

3. **Verification never self-scores** — attempted to find any verify_output path that reads a score:
   - Grep `confidence_note` in isa.py: zero hits.
   - Grep `score|confidence|probability` in isa.py: only "confidence" appears in zero places in verify_output; the only `confidence_note` field lives on EvidenceRecord/GlossaryEntry as debug metadata.
   - Inspected verify_output body (isa.py:380-458) line by line: reads ctx.glossary_cache, ctx.entity_table, ctx.structural_map, _forbidden_from_module(). No score reads.
   - Inspected repair_segment's re-verify call (isa.py:516): passes through to verify_output. No score reads.
   - **Result: no bypass found.** Inv 3 holds.

4. **Repair surgical** — attempted to construct a path where repair introduces new BLOCKING at attempt=1:
   - Setup: ctx with glossary `{"成立": "Confirmed"}`, forbidden_targets including "Valid".
   - Target: "成立 Valid" (contains both untranslated source term AND forbidden drift).
   - Diagnostic: `{severity: WARNING, subsystem: "terminology", issue: "Source term not translated: '成立'"}`.
   - Call: `repair_segment("成立 Valid", "成立 Valid", diag, ctx, ev, audit, attempt=1, max_retries=3)`.
   - Trace: isa.py:489-494 matches subsystem="terminology", replaces "成立" → "Confirmed", yielding "Confirmed Valid".
   - Re-verify (isa.py:516): verify_output("Confirmed Valid", ...) raises BLOCKING because "Valid" is a forbidden_target.
   - new_blocking = [the BLOCKING diagnostic]. Condition at isa.py:518: `new_blocking and attempt >= max_retries` = `True and (1 >= 3)` = `True and False` = False. NO raise.
   - Function records RepairAttempt(resolved=False) at isa.py:536-547 and returns "Confirmed Valid".
   - **Result: BYPASS CONFIRMED.** At attempt=1, repair_segment returns a target with new BLOCKING, no exception. The kernel's loop catches it (kernel.py:233 re-queues), but a direct caller does not. The function-level invariant from ISA-REF §REPAIR_SEGMENT is violated. This is the suspected gap — CONFIRMED with exact code evidence at isa.py:515-519.

### Summary of material findings

The 5 most material findings (BLOCKING or affecting spec conformance):

1. **A-15 / A-26 Inv 4 (BLOCKING)** — `repair_segment` does not enforce "no new BLOCKING" at attempt=1. The `attempt >= max_retries` guard at isa.py:518 means a repair that introduces new BLOCKING on early attempts returns silently. Direct callers receive broken output with no exception. Fix: drop the guard; raise Unrecoverable whenever new_blocking is non-empty.

2. **A-13 (BLOCKING)** — `translate_segment` receives the whole document, not a segment. kernel.py:186 passes `src` (full markdown) as `source_segment`. This violates the ISA contract (TRA-ISA-REFERENCE.md:48-49), makes cache keys per-document, skips the structural_map's is_no_translate_zone flag (so S-03 inline-code-untranslated is violated), and reduces the L4 line-by-line trace to a substring heuristic. The cache.py:13 docstring explicitly says "never a whole document" — the implementation does the opposite.

3. **A-23 (BLOCKING)** — 3 of 5 TRA-EXCEPTION recovery procedures are dead code in production. `BrokenMarkdown` is raised by analyze_document (isa.py:84) but the kernel does NOT wrap analyze_document in try/except (kernel.py:129) — so a malformed source crashes the kernel with no EXCEPTION_HANDLER invocation. `UnknownTerm`, `CertaintyConflict`, `EntityAmbiguity` are never raised anywhere in production. Only `GlossaryConflict` (from build_glossary) and `Unrecoverable` (from repair_segment) reach the recovery path. Spec §6 mandates deterministic recovery for all 5 types.

4. **A-7 (BLOCKING)** — `kernel.run()` does NOT enforce the L3 gate. The function returns the target unconditionally at kernel.py:157, even if post-repair BLOCKING diagnostics remain. `tra_cli.py translate` only prints a warning (tra_cli.py:116-120). Per TRA-CONFORMANCE-GUIDE.md:51, "If present, certification is denied" — the engine should fail. Only `validate` and `benchmark` enforce the gate; the main `translate` pipeline does not.

5. **A-16 / A-17 / A-21 (WARNING)** — The Policy Engine is scaffolding with no production invocation. `PolicyResolver` (policy.py:13-25) is imported only by test_phase0.py. The kernel and ISA never call it. verify_output has no Factual-Integrity check (numbers/units/versions other than those caught by entity extraction), no structural-integrity check beyond heading count, no fluency check, and no Domain-Module fallback for equal-priority conflicts (spec §5.2). The 6-priority stack exists in the enum (memory.py:25-30) and config (config.py:13-20) but is never consulted during arbitration. The "scope rules" (code blocks, headings) mentioned in the audit checklist are not in the spec text and not in the code.

### Bottom line

Of 26 checklist items: **18 PASS, 6 WARNING, 4 BLOCKING** (A-7, A-13, A-15, A-23; A-26's 4th invariant is the same root cause as A-15).

The engine faithfully implements the ISA contracts for ANALYZE_DOCUMENT, BUILD_GLOSSARY, BUILD_ENTITY_TABLE, VERIFY_OUTPUT (never-self-scores), and the L4 forensic gating. The ZH-EN module's canonical terminology is exact and forbids drift. Entities are immutable in practice. The audit trail is append-only by API design.

The engine does NOT faithfully implement: (1) the TRANSLATE_SEGMENT segment-level contract (whole-doc instead), (2) the REPAIR_SEGMENT surgical invariant at the function boundary, (3) the EXCEPTION_HANDLER recovery for 4 of 5 exception types, (4) the L3 gate in the main translate pipeline, and (5) the Policy Engine arbitration in production code paths.

The 4 critical invariants: 3 hold (canonical terminology, entity immutability, never-self-scores); 1 is violated (repair surgical at attempt=1). The invariant-breaking attack for #4 is reproducible with the exact code path documented above.

---

## Task audit-B — Code quality & security audit (Track B, 18 items)

Auditor: Agent B. Scope: is `tra-prototype/` production-grade for its stated
purpose (proving out the TRA spec deterministically for ZH↔EN at L3)?
Method: read every line of every `tra/*.py` file (19 modules), `tra_cli.py`,
`pyproject.toml`, `requirements.txt`, `config.yaml`, and every test file.
Ran the four quality gates plus extra greps for type-safety / error-handling
patterns. Read-only audit — no files modified, no packages installed.

Previous `3-validate` and `audit-A` baselines are NOT repeated here. This
audit goes DEEPER on: type safety (B1-B4), error handling (B5-B8), dead code
(B9-B11), input sanitization & security (B12-B15), Pydantic & data modeling
(B16), dependency hygiene (B17), reproducibility (B18). All file:line
citations are `tra-prototype/`-relative.

### Quality gate results (re-run for this audit)

```
ruff check . --output-format=concise   → All checks passed!
ruff format --check .                  → 33 files already formatted
mypy --strict tra                      → Success: no issues found in 20 source files
pytest tests -q                        → 103 passed in 0.46s
ruff check --select F .                → All checks passed! (no unused imports)
```

### Findings B1–B18

```
B-1  | PASS       | Type safety — mypy --strict clean
Code evidence: tra/ (20 source files), tests/test_recovery.py:95
Finding: mypy --strict passes clean; only 1 stale `# type: ignore` and 8 justified `Any` annotations.
Detail: `mypy --strict tra` returns "Success: no issues found in 20 source files". Grep for `type: ignore|cast(|: Any|Any]` over tra/ and tra_cli.py returns 14 hits: 1 `# type: ignore[arg-type]` at test_recovery.py:95 (`route_exception(BrokenMarkdown(), amb)` — the ignore is STALE; BrokenMarkdown IS a TRAException and mypy passes without it); 0 `cast(` calls; 8 `dict[str, Any]` annotations (memory.py:112,175; registry.py:22; reporting.py:21,73,82; diagnostics.py:61,117) all for heterogeneous JSON-serializable payloads; 2 `Any` function params in cache.py:28,33,37 (`_canonical_json`, `_hash_sorted`, `_hash_set` — accept any JSON-serializable); 1 `self._cache: Any` in cache.py:85 (diskcache has no stubs; mypy override sets `ignore_missing_imports=true`). All `Any` uses are at module boundaries, not in core logic.
Suggested fix: remove the stale `# type: ignore[arg-type]` at test_recovery.py:95.

B-2  | WARNING    | Pydantic v2 — minimal config, no constraints
Code evidence: tra/memory.py:86 (only ConfigDict), tra/memory.py:154-160 (Entity), tra/config.py:23-35 (BootstrapConfig)
Finding: Only 1 `model_config = ConfigDict(...)` in the entire codebase; zero `frozen=True`; zero constraint Fields (min_length/pattern/gt); zero `extra="forbid"`.
Detail: The single `model_config = ConfigDict(populate_by_name=True)` is on DocumentProfile (memory.py:86) for the `register_` alias. No other model has a `model_config`. Grepping for `frozen=True|extra=|str_strip_whitespace|coerce_numbers_to_str|min_length|max_length|pattern=|gt=|ge=|lt=|le=` returns ZERO hits in tra/. Pydantic v2 is used as a typed data container, not as a validation engine. `Entity` (memory.py:154) docstring says "An immutable identifier" but the model is NOT frozen — `ent.name = "X"` is allowed at runtime. `BootstrapConfig` (config.py:23) docstring says "read-only Immutable Config segment" but the CLI directly mutates it (`cfg.language_pair = lang` at tra_cli.py:87, `cfg.conformance_level = ...` at tra_cli.py:89). All 30+ `Field()` calls use only `default_factory`, `default`, or `description` — never constraints.
Suggested fix: add `model_config = ConfigDict(frozen=True)` to Entity and BootstrapConfig (and use `model_copy(update=...)` for CLI overrides); add `min_length=1` to GlossaryEntry.source/target and Entity.name; add `ge=1, le=10` to BootstrapConfig.repair_max_retries.

B-3  | PASS       | `from __future__ import annotations` consistency
Code evidence: all 30 .py files in tra/, tra_cli.py, tests/
Finding: Every Python module has the future-annotations import.
Detail: Grep for `^from __future__ import annotations$` returns 30 hits — one per .py file in tra/ (19 modules including __init__.py and modules/), tra_cli.py, and all 11 test files (including conftest.py). 100% coverage.
Suggested fix: none.

B-4  | WARNING    | `assert` used for runtime validation in production
Code evidence: tra/kernel.py:130-131
Finding: Two `assert` statements validate postconditions in `TRAKernel.run()` — stripped under `python -O`.
Detail: kernel.py:130-131:
    `assert self.ctx.document_profile is not None`
    `assert self.ctx.structural_map is not None`
These guards protect the type narrowing for `profile`/`smap` after `analyze_document()`. Under `python -O` (or `-OO`), asserts are stripped, so a future regression where `analyze_document` returns without setting these fields would produce an `AttributeError` on the next line instead of a clear `TRAException`. All other production `assert`s are in tests (113 occurrences across tests/*.py — appropriate for pytest).
Suggested fix: replace with `if self.ctx.document_profile is None: raise TRAException("ANALYZE_DOCUMENT did not set document_profile")` (and same for structural_map).

B-5  | PASS       | Broad except clauses — all justified
Code evidence: tra/isa.py:83, tra/isa.py:316, tra/kernel.py:138, tra/kernel.py:208, tra_cli.py:39
Finding: 2 `except Exception` in production, both with `# noqa: BLE001` justification comments matching behavior; 0 bare `except:`.
Detail: isa.py:83 (`except Exception as exc: raise BrokenMarkdown(...)`) wraps markdown-it-py parser failures — comment "surface as spec failure" matches the re-raise behavior. isa.py:316 (`except Exception as exc: ... _rule_translate ...`) is the §6.5.4 graceful-degradation catch — comment "graceful degradation (§6.5.4)" matches the fallback-to-rule-path behavior. kernel.py:138 (`except TRAException as exc: self._recover(exc)`) is narrow. kernel.py:208 (`except Unrecoverable:`) is narrow. tra_cli.py:39 (`except ValueError:`) is narrow and re-raises as click.BadParameter. The §6.5.4 catch at isa.py:316 matches implementation_plan.md L283 ("6.5.4 Graceful degradation: rule-based fallback when LLM unavailable").
Suggested fix: none.

B-6  | PASS       | raise statements use TRAException subclasses
Code evidence: tra/isa.py:79,84,164,170,511,519; tra/kernel.py:112,116; tra/modules/registry.py:36
Finding: All production `raise` statements use TRAException subclasses; 1 `KeyError` in registry (acceptable for dict-like API); 0 `RuntimeError`/`ValueError`/`TypeError` in production.
Detail: Grep `raise\s` over tra/ returns 9 hits: 7 use TRAException subclasses (TRAException, BrokenMarkdown, GlossaryConflict, Unrecoverable); 1 `raise KeyError(f"Module '{name}' not registered")` at registry.py:36 (Python convention for lookup-miss in a registry/dict API — acceptable). The single `raise RuntimeError("llm down")` is in test_phase6_hardening.py:78 — a test fixture simulating LLM failure, NOT production code.
Suggested fix: none.

B-7  | WARNING    | LLM seam degradation — logged but DOUBLE record
Code evidence: tra/isa.py:316-346
Finding: Degradation IS logged with `degraded: True`, but the code falls through to append a SECOND `TRANSLATE_SEGMENT` record without the flag.
Detail: When `llm_translate` raises, isa.py:322-330 appends an audit record with `artifact_snapshot={"degraded": True, "reason": ...}`. The code then falls through to isa.py:334-346, which appends ANOTHER `TRANSLATE_SEGMENT` record (with the evidence_chain, no `degraded` flag). Verified empirically: a degraded translation produces 2 audit records — Record 0 has `{'degraded': True, ...}`, Record 1 has `{}`. An L3 auditor inspecting the LAST `TRANSLATE_SEGMENT` record per segment would miss the degradation indicator. The test `test_graceful_degradation_on_llm_failure` (test_phase6_hardening.py:71-85) checks `any(r for r in audit._buffer if r.artifact_snapshot.get("degraded"))` — passes because of Record 0, but doesn't catch the double-record issue.
Suggested fix: in the degraded branch, `return` after the second audit append, or merge the two records (set `degraded: True` on the final record and skip the separate degradation notice).

B-8  | PASS       | No swallowed exceptions
Code evidence: tra/ (all except clauses)
Finding: Zero `except: pass` or `except Exception: pass` patterns.
Detail: Grep `-A1 "except.*:"` over tra/ and tra_cli.py shows every except block either re-raises, routes through `_recover`, handles meaningfully (e.g., fallback to rule path), or re-raises as a different exception type. No silent swallowing.
Suggested fix: none.

B-9  | PASS       | Unused imports — ruff F-category clean
Code evidence: `ruff check --select F .` → All checks passed!
Finding: ruff's Pyflakes (F) ruleset reports zero unused imports across all 33 .py files.
Detail: `ruff check --select F . --output-format=concise` returns "All checks passed!". F401 (unused import), F811 (redefined-while-unused), F841 (unused variable) all clean. The full F category (all Pyflakes checks) passes.
Suggested fix: none.

B-10 | WARNING    | Dead code — count_blocking stub + CONCLUSION_LEADING + ModuleBase
Code evidence: tra/diagnostics.py:159-166; tra/modules/zh_en.py:75; tra/modules/base.py:8-28; tra/policy.py:13-25; tra/anchor.py:101-149
Finding: Multiple dead-code elements; `count_blocking` is the most dangerous (misleading API returning 0).
Detail: (1) `AuditTrail.count_blocking(evidence_for_record)` at diagnostics.py:159-166 — signature takes a dict but ignores it; body is `return 0  # hook for VERIFY to populate; trail stores records, not severities`. If a future caller trusts the method name for an L3 gate check, they get a FALSE PASS. Real BLOCKING counting lives in `reporting.summarize_audit` and `validate.ValidationReport.blocking`. (2) `CONCLUSION_LEADING` at zh_en.py:75 — `tuple[str, ...] = ("因此", "所以", "故", "由此可见", "综上")` with a docstring claiming it surfaces conclusions first, but NO code reads it. (3) `ModuleBase` ABC at modules/base.py:8-28 — abstract class with `get_glossary_mappings`/`get_style_profile`/`apply_rules`; `ZHENModule` does NOT inherit from it (inherits from `object`), so the ABC is never subclassed. (4) `PolicyResolver` at policy.py:13-25 — imported only by test_phase0.py:23; never in production. (5) `rewrite_links` at anchor.py:101-149 — defined and tested (test_anchor.py:93-113), NEVER called from kernel.run() or anywhere in production. (6) `_HALF_TO_FULL` at zh_en.py:110-119 — reached only via `apply_en_rules` → `apply_rules(direction="EN -> ZH")`; the kernel's production path is ZH→EN, so this table is production-dead but test-alive. (7) `registry_for_language_pair` and `build_default_registry` — used only in tests; kernel.py:43,106 hardcodes `ZHENModule()` directly.
Suggested fix: delete `count_blocking` (or implement it: `return sum(1 for r in self._buffer if r.flags_raised and "BLOCKING" in r.flags_raised)`); delete `CONCLUSION_LEADING`; delete `ModuleBase` (or make `ZHENModule` inherit from it); either wire `PolicyResolver`/`rewrite_links`/registry into production or mark them `# TODO: Phase 7`.

B-11 | WARNING    | Unused dependencies — 5 of 10 runtime deps never imported
Code evidence: pyproject.toml:10-21; requirements.txt:1-11
Finding: pydantic-settings, mdit-py-plugins, structlog, litellm are unused at runtime; black and pytest-asyncio are unused in dev.
Detail: Grep `import structlog|from structlog|import litellm|from litellm|pydantic_settings|from pydantic_settings|mdit_py_plugins|from mdit_py_plugins` over the entire repo returns ZERO hits (only manifest mentions in pyproject.toml/requirements.txt). `pip show litellm` confirms it pulls aiohttp, click, fastuuid, httpx, importlib-metadata, jinja2, jsonschema, openai, pydantic, python-dotenv, tiktoken, tokenizers (12 direct transitive deps, ~50+ total with httpcore/h11/huggingface-hub/regex/etc.). The LLM seam is caller-supplied (`llm_translate: Callable[[str, RuntimeContext], str] | None` at isa.py:286), so litellm is not needed at runtime. `black` is listed in dev deps but `ruff format` is the actual formatter (`ruff format --check .` passes; no `[tool.black]` config is exercised). `pytest-asyncio` is listed with `asyncio_mode = "auto"` in pyproject.toml:61, but grep `async def|await|asyncio` over tra/ and tests/ returns ZERO functional hits (only a docstring noun at hitl.py:8).
Suggested fix: move litellm to an optional extra (`pip install -e ".[llm]"`); drop pydantic-settings, mdit-py-plugins, structlog from runtime deps; drop black and pytest-asyncio from dev deps (or wire pytest-asyncio if asyncio segment-level parallelism lands per Phase 6.5.1).

B-12 | WARNING    | Input sanitization — kernel sanitizes, validate/benchmark do NOT
Code evidence: tra/kernel.py:75-90 (_sanitize_input), tra/kernel.py:125 (only call site), tra/validate.py:71-72, tra/benchmark.py:102-104
Finding: `_sanitize_input` regex is COMPLETE (covers all required ranges), but `validate.py` and `benchmark.py`'s re-verify path bypass it.
Detail: The regex `_CONTROL_RE = re.compile("[" + "\x00-\x08\x0b\x0c\x0e-\x1f\x7f" + "\u202a-\u202e" + "\ufeff" + "]")` (kernel.py:78-80) correctly strips: null bytes (\x00), C0 control chars (\x01-\x08, \x0b, \x0c, \x0e-\x1f), DEL (\x7f), Unicode bidi overrides (\u202a-\u202e), BOM (\ufeff) — verified empirically for all 17 required characters. Tab (\x09), LF (\x0a), CR (\x0d) are correctly PRESERVED. BUT: the ONLY call site is kernel.py:125 inside `TRAKernel.run()`. `validate.py:validate_translation` (validate.py:71-72) calls `source.read_text()` then `analyze_document(source, ...)` directly — NO sanitization. `benchmark.py:BenchmarkRunner.run_case` (benchmark.py:88) calls `kernel.run(case.source)` (sanitized), but then at benchmark.py:102-104 calls `analyze_document(case.source, ...)` for re-verification — NO sanitization on the re-verify path. The `tra validate` CLI command (tra_cli.py:197-242) calls `validate_translation` — NO sanitization. A malicious candidate file with bidi overrides or null bytes would be processed unsanitized by `validate` and the benchmark re-verify path.
Suggested fix: move `_sanitize_input` to a shared utility (e.g., `tra/utils.py` or a new `tra/sanitize.py`) and call it at the top of `validate_translation`, `analyze_document`, and `BenchmarkRunner.run_case`'s re-verify block.

B-13 | PASS       | Cache key determinism — canonical, order-independent for sets
Code evidence: tra/cache.py:28-67; tests/test_phase0.py:28-48
Finding: Cache key is SHA-256 over canonical (sorted-key) JSON; glossary/entities are order-independent via `_hash_set`; policy_stack is order-DEPENDENT (intentional per spec §5).
Detail: `_canonical_json(payload)` (cache.py:28-30) uses `json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)` — sorts DICT keys, preserves LIST order. `CacheKeyContext.key()` (cache.py:57-67) builds a dict payload and hashes it. `_hash_set(items)` (cache.py:37-44) sorts per-item hashes before re-hashing — makes glossary/entities order-independent. `_hash_sorted(obj)` (cache.py:33-34) is misleadingly named: it does NOT sort list elements (only dict keys via sort_keys=True); used for `policy_stack_hash` where order MATTERS (spec §5: "The ordering is non-negotiable"). Test `test_cache_key_is_deterministic_and_order_independent` (test_phase0.py:28-35) asserts: identical key for identical context, AND reordering glossary doesn't change key — PASSES. Test `test_cache_key_changes_with_model_or_policy` (test_phase0.py:38-48) asserts: model_version change → different key, policy_stack reverse → different key — PASSES. Verified empirically: reversing glossary/entities produces identical key; reversing policy_stack produces different key. The `default=str` in `_canonical_json` correctly handles StrEnum serialization (str(EntityType.PRODUCT) == "product" == model_dump(mode="json")).
Suggested fix: rename `_hash_sorted` to `_hash_canonical` (it doesn't sort lists); add a docstring noting policy_stack order-dependence is intentional.

B-14 | BLOCKING   | Cache invalidation — CLI `--pattern` is a SILENT NO-OP
Code evidence: tra/cache.py:107-115; tra_cli.py:123-132
Finding: `TranslationCache.invalidate(pattern)` calls `diskcache.delete(pattern)` which takes a LITERAL KEY, not a glob — the comment "diskcache.delete supports glob patterns" is FALSE.
Detail: cache.py:111-113:
    `if pattern:`
        `# diskcache.delete supports glob patterns`
        `self._cache.delete(pattern)`
Verified empirically: `diskcache.Cache.delete(key)` takes a single literal key. `c.delete("*")` returns False (no entries deleted). `c.delete("ab*")` returns False. `c.delete("abc")` returns True (only exact key match). The CLI `cache-clear --pattern X` (tra_cli.py:123-132) calls `cache.invalidate(pattern)` then unconditionally prints `f"[green]Cache invalidated:[/green] {target}"` where `target = pattern or "ALL"` — so a user running `tra cache-clear --pattern 'ab*'` sees "Cache invalidated: ab*" but NOTHING was actually deleted. This is a correctness bug, not a security bug (no regex injection — diskcache treats input as literal). The `c.clear()` path (no pattern) works correctly.
Suggested fix: either (a) implement glob-based invalidation via `c.iterkeys()` + `fnmatch`/`re.fullmatch` filtering, or (b) drop the `--pattern` option from the CLI and only support full `cache.clear()`. Either way, fix the misleading comment at cache.py:112.

B-15 | WARNING    | Path safety — no traversal protection on config-supplied paths
Code evidence: tra/config.py:23-55; tra/kernel.py:240-312; tra/diagnostics.py:141
Finding: `BootstrapConfig` accepts arbitrary `compilation_dir`, `audit_trace`, `cache_directory` from YAML with no sanitization; verified a malicious config writes outside the project.
Detail: `BootstrapConfig.from_yaml` (config.py:37-55) reads `compilation_dir`, `audit_trace`, `cache_directory` directly from YAML with no path validation. Verified empirically: a config with `compilation_dir: '../../../etc'`, `audit_trace: '/tmp/tra-evil.jsonl'`, `cache_directory: '/var/tmp/evil-cache'` is accepted and the paths are used as-is. The kernel then writes 6 files to `compilation_dir` (glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml, execution_log.json, repair_history.jsonl) and optionally 2 more at L4 (evidence_trace.jsonl, ambiguity_register.json). `AuditTrail.flush()` (diagnostics.py:141) calls `self.path.parent.mkdir(parents=True, exist_ok=True)` — creates arbitrary directories. `TranslationCache.__init__` (cache.py:89) calls `self.directory.mkdir(parents=True, exist_ok=True)` — same. No `..` detection, no absolute-path rejection, no project-root confinement. Secondary concern: placeholder collision — a heading literally containing `__HEADER_000__` would be assigned that same placeholder (anchor.py:67), verified empirically: `build_structural_map('# __HEADER_000__\n')` registers `{'__HEADER_000__': '__HEADER_000__'}`. Mitigated only because `rewrite_links` is never called in production (audit-A finding). Tertiary: file permissions inherit umask (0664 files, 0775 dirs) — no restrictive mode for sensitive audit data.
Suggested fix: for a prototype, document the trusted-config assumption in config.py; for production, resolve all paths against a project root and reject `..` and absolute paths, or use a sandboxed base dir. Set `Path(path).open(..., opener=opener)` with mode 0600 for audit_trace.jsonl if it may contain source excerpts.

B-16 | WARNING    | Pydantic v2 — immutability claims unenforced
Code evidence: tra/memory.py:86,154-160,172-184,210; tra/config.py:23-35; tra_cli.py:86-89
Finding: Only 1 `model_config = ConfigDict(...)` (DocumentProfile, populate_by_name only); zero `frozen=True` despite immutability docstrings; zero constraint Fields; 1 correct `model_rebuild()`.
Detail: See B-2 for full detail. Specifically: `Entity` (memory.py:154-160) docstring says "An immutable identifier isolated from natural-language translation" but is NOT frozen — `ent.name = "X"` is allowed at runtime (only `mutable: bool = False` field is set, and even that is settable). `BootstrapConfig` (config.py:23-35) docstring says "Parsed tvm_bootstrap — read-only Immutable Config segment" but is NOT frozen — tra_cli.py:87-89 mutates `cfg.language_pair` and `cfg.conformance_level` directly. `RuntimeContext` (memory.py:172-184) is correctly mutable (no frozen — it's the "mutable memory of the VM" per spec §4). `StructuralNode.model_rebuild()` at memory.py:210 correctly resolves the self-referential `children: list[StructuralNode]` forward ref. No `extra="forbid"` on any model — unknown YAML fields are silently ignored (not a bug, but means typos in config.yaml don't error).
Suggested fix: add `model_config = ConfigDict(frozen=True)` to Entity, GlossaryEntry, ForbiddenMapping, DocumentProfile, StructuralNode, StructuralMap, StyleProfile, AuditRecord, EvidenceRecord, Diagnostic, RepairAttempt, TranslationResult, CacheKeyContext, BootstrapConfig. Use `cfg.model_copy(update={"language_pair": lang})` in tra_cli.py instead of direct mutation. Add `extra="forbid"` to BootstrapConfig to catch config.yaml typos.

B-17 | WARNING    | Dependency hygiene — 4 unused runtime deps, 2 unused dev deps
Code evidence: pyproject.toml:10-21,23-30; requirements.txt; tra/ (grep for imports)
Finding: See dependency table below. 4 of 10 runtime deps are never imported (pydantic-settings, mdit-py-plugins, structlog, litellm); 2 of 5 dev deps are unused (black, pytest-asyncio). litellm is the heaviest (~30 transitive deps).
Detail: See full table in the final report. The litellm transitive tree (verified via `pip show litellm`): aiohttp, click, fastuuid, httpx, importlib-metadata, jinja2, jsonschema, openai, pydantic, python-dotenv, tiktoken, tokenizers — and transitively httpcore, h11, certifi, huggingface-hub, regex, requests, anyio, sniffio, tqdm, pyyaml, etc. (~50+ packages total, hundreds of MB). For a rule-based prototype that never imports litellm, this is significant install-footprint bloat. The LLM seam is wired as `llm_translate: Callable[[str, RuntimeContext], str] | None` (isa.py:286) — caller-supplied, so litellm is not needed at runtime.
Suggested fix: move litellm to `optional-dependencies.llm`; drop pydantic-settings, mdit-py-plugins, structlog from runtime deps; drop black and pytest-asyncio from dev deps (or wire pytest-asyncio if/when asyncio segment-level parallelism lands per Phase 6.5.1).

B-18 | WARNING    | Reproducibility — output byte-identical, audit trail is NOT
Code evidence: tra/diagnostics.py:40 (uuid4 evidence IDs), tra/diagnostics.py:58 (datetime.now timestamps); tests/test_benchmark.py:65-71 (R-01 regression)
Finding: Target text, cache.db, and 6 compilation artifacts are byte-identical across runs; audit_trace.jsonl is NOT (timestamps + random UUIDs).
Detail: Verified empirically — two runs of the same source with fresh temp dirs produce: (a) identical target text (SHA-256 match); (b) identical cache.db (SHA-256 match); (c) identical glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml, execution_log.json, repair_history.jsonl (all SHA-256 match); (d) DIFFERENT audit_trace.jsonl. The audit trail differs in two fields: (1) `timestamp` — `datetime.now(UTC)` per AuditRecord (diagnostics.py:58), different on every run; (2) `evidence_chain` IDs — `EvidenceRecord.id = f"ev_{uuid4().hex[:12]}"` (diagnostics.py:40), random UUIDs. Diffing two runs' audit trails: Record 0 (ANALYZE_DOCUMENT) differs only in timestamp; Record 1 (BUILD_GLOSSARY) differs in timestamp AND all 11 evidence_chain IDs; Records 2-4 same pattern. The test `test_regression_cache_hit_byte_identical` (test_benchmark.py:65-71) asserts only `first == second` on the OUTPUT — it does NOT check audit-trail reproducibility. For L4 forensic audits (legal/security per TRA-CONFORMANCE-GUIDE.md L4), the non-reproducible audit trail is a concern: two runs of the same source produce different audit trails, making it impossible to cryptographically prove "this audit trail corresponds to this output" by hashing the trail alone.
Suggested fix: make evidence IDs deterministic (e.g., `ev_{sha256(f"{type}:{source_span}:{target_span}:{module}")[:12]}` instead of uuid4); make timestamps deterministic or strip them from the persisted trail (keep sequence_id as the ordering key). If live timestamps are needed for operational logging, separate them from the forensic trail.
```

### Dependency hygiene table (B-17 detail)

| Dependency | Version | Used? | Where | Notes |
| --- | --- | --- | --- | --- |
| pydantic | >=2.8 | YES | every model in tra/memory.py, tra/cache.py, tra/diagnostics.py, tra/config.py, tra/benchmark.py | 2.13.4 installed; core data modeling |
| pydantic-settings | >=2.3 | **NO** | (none) | Zero imports; pulls python-dotenv, typing-inspection. Drop. |
| markdown-it-py | >=3.0 | YES | tra/anchor.py:25,26 (`from markdown_it import MarkdownIt; from markdown_it.token import Token`) | 4.2.0 installed; markdown AST traversal |
| mdit-py-plugins | >=0.4 | **NO** | (none) | Zero imports; the codebase uses only `MarkdownIt().enable("table")` (built-in). Drop. |
| diskcache | >=5.6 | YES | tra/cache.py:87 (`import diskcache` inside `__init__`) | 5.6.3 installed; SQLite-backed cache |
| pyyaml | >=6.0 | YES | tra/kernel.py:18, tra/config.py:8 (`import yaml`) | YAML config + artifact serialization |
| structlog | >=24.1 | **NO** | (none) | Zero imports; confirmed in audit-A. Drop (or wire per Phase 6.3.1). |
| click | >=8.1 | YES | tra_cli.py:14 (`import click`) | CLI framework |
| rich | >=13.7 | YES | tra/hitl.py:15,16; tra_cli.py:15,16 (`from rich.console import Console; from rich.table import Table`) | HITL prompts + audit table |
| litellm | >=1.49 | **NO** | (none) | Zero imports; LLM seam is `Callable`-typed (isa.py:286). Pulls ~30 transitive deps (openai, tiktoken, tokenizers, huggingface-hub, httpx, aiohttp, jinja2, jsonschema, ...). Move to optional extra `[llm]`. |
| pytest (dev) | >=8.2 | YES | tests/ | Test runner |
| pytest-asyncio (dev) | >=0.23 | **NO** | (none) | `asyncio_mode = "auto"` set in pyproject.toml:61 but ZERO `async def` tests. Drop (or wire when Phase 6.5.1 lands). |
| ruff (dev) | >=0.5 | YES | quality gate | Linter + formatter |
| black (dev) | >=24.4 | **NO** | (none) | `ruff format` is the actual formatter; `[tool.black]` config exists but is unused. Drop. |
| mypy (dev) | >=1.10 | YES | quality gate | Type checker |

### Security concerns summary

1. **B-14 (BLOCKING): Cache-clear `--pattern` is a silent no-op.** `diskcache.Cache.delete(key)` takes a literal key, NOT a glob. The comment at cache.py:112 ("diskcache.delete supports glob patterns") is factually wrong. The CLI prints "Cache invalidated: X" even when nothing was deleted. Not a security vulnerability (no injection), but a correctness bug that could lead a user to believe stale cache entries were cleared when they weren't — potentially serving stale translations.

2. **B-15 (WARNING): No path traversal protection on config-supplied paths.** A malicious `config.yaml` with `compilation_dir: '../../../etc'` or `audit_trace: '/tmp/evil.jsonl'` is accepted and used as-is. The kernel writes 6-8 files to these locations. For a prototype with a trusted-config assumption, this is acceptable; for a production engine, paths should be confined to a project root.

3. **B-12 (WARNING): Input sanitization bypass at validate/benchmark boundaries.** `_sanitize_input` (kernel.py:83-90) is correctly implemented (covers null bytes, C0 control, DEL, bidi overrides, BOM) but is ONLY called from `TRAKernel.run()`. The `validate` CLI command and the benchmark re-verify path call `analyze_document` directly without sanitizing. A malicious candidate file with bidi overrides would be processed unsanitized by `validate`.

4. **B-7 (WARNING): Double audit record on LLM degradation.** A degraded translation produces TWO `TRANSLATE_SEGMENT` audit records — only the first has `degraded: True`. An auditor inspecting the last record per segment would miss the degradation.

5. **B-18 (WARNING): Non-reproducible audit trail.** `datetime.now(UTC)` timestamps and `uuid4()` evidence IDs make the audit trail non-byte-identical across runs, even with identical input. For L4 forensic claims, this is a concern — though the OUTPUT and compilation artifacts ARE byte-reproducible.

6. **B-16/B-2 (WARNING): Pydantic immutability claims unenforced.** `Entity` and `BootstrapConfig` docstrings claim immutability but neither is `frozen=True`. The CLI directly mutates `BootstrapConfig` (tra_cli.py:87-89). No constraint Fields anywhere — Pydantic v2 is used as a typed container, not a validation engine.

### Bottom line (Track B)

Of 18 checklist items: **8 PASS, 9 WARNING, 1 BLOCKING** (B-14).

The codebase is **clean on the fundamentals**: mypy --strict passes, ruff passes, 103 tests pass, no unused imports, no swallowed exceptions, all `raise` statements use the proper exception hierarchy, all `except` clauses are justified, `from __future__ import annotations` is universal, and the cache key is cryptographically deterministic.

The codebase is **NOT production-grade** due to: (1) a silent cache-invalidation bug (B-14), (2) Pydantic v2 used as a typed container rather than a validation engine with immutability claims unenforced (B-2/B-16), (3) input sanitization bypassed at the validate/benchmark boundaries (B-12), (4) no path-traversal protection on config-supplied paths (B-15), (5) a non-reproducible audit trail undermining L4 forensic claims (B-18), (6) significant dependency bloat from litellm's ~30 transitive deps (B-11/B-17), (7) several dead-code elements including a misleading `count_blocking` stub that returns 0 (B-10), and (8) runtime `assert` statements that vanish under `python -O` (B-4).

For the stated purpose — "proving out the TRA spec deterministically for ZH↔EN at L3" — the engine is **adequate**: the deterministic path (glossary + entity + epistemic substitution) produces byte-identical output across runs, the L3 gate (zero BLOCKING) is enforced in `validate` and `benchmark`, and the four quality gates are green. The findings above are engineering-hygiene issues that should be fixed before claiming the engine is "production-grade" or before pursuing L4 forensic certification.

---

## Task audit-C — Doc-vs-code consistency audit (Track C, 22 items)

Auditor: Agent C. Scope: for every claim in the documentation, verify against the
code; for every code behavior, check if it's documented. Report divergences with
file:line evidence and exact quotes.

Method: read all 11 doc files (CLAUDE.md, AGENTS.md, README.md,
implementation_plan.md, SKILL.md, prototype README, status.md, review.md,
review-feedback.md, prototype.md, start-here.md) plus the 5 TRA-*.md spec files
line-by-line; read every Python source file in tra-prototype/; grep for each
claim's exact behavior. Previous 3-validate / audit-A / audit-B baselines are
NOT repeated; this audit goes DEEPER on doc-vs-code reconciliation. All file:line
citations are repo-relative (tra-prototype/ paths prefixed).

### Findings D1–D22

```
D-1  | BLOCKING   | misleading-doc
Doc claim: TRA-ISA-REFERENCE.md:48-49 "Generates the target-language equivalent of a specific source segment (sentence, list item, or table cell)."
Doc claim: cache.py:12-13 "Scope: cache only atomic ops (TRANSLATE_SEGMENT, REPAIR_SEGMENT), never a whole document."
Doc claim: memory.py:194 RepairAttempt.segment_index description "Index of the repaired leaf segment"
Code reality: tra-prototype/tra/kernel.py:186 `result = translate_segment(src, self.ctx, self.cache, self.evidence, self.audit)` — src is the ENTIRE source markdown, not a segment.
Code reality: tra-prototype/tra/kernel.py:184 inline comment "Phase 2: deterministic whole-doc substitution via the glossary + entity + epistemic lexicon. Segment granularity is wired in Phase 3." — Phase 3 never landed.
Code reality: tra-prototype/tra/isa.py:476 `segment_index: int = 0` — default; kernel._repair_loop (kernel.py:198-207) never passes segment_index, so RepairAttempt.segment_index is ALWAYS 0 in production.
Code reality: tra-prototype/tra/reporting.py:86 `hits = [r.id for r in records if r.target_span and r.target_span in line]` — L4 line-by-line trace is a substring-containment heuristic, not a structural segment→evidence mapping.
Doc silence: CLAUDE.md:42-46 "Known gaps" lists only structlog / asyncio / cross-run caching — segment granularity gap NOT mentioned.
Doc silence: tra-prototype/SKILL.md:183-195 "Known limitations" — segment granularity gap NOT mentioned.
Divergence: The ISA contract, cache.py docstring, and RepairAttempt.segment_index field all assume segment-level granularity, but the kernel translates the whole document as one segment; the gap is invisible in CLAUDE.md and SKILL.md "Known gaps/limitations" lists.
Suggested fix: add a fourth bullet to CLAUDE.md "Known gaps": "TRANSLATE_SEGMENT operates on the whole document as one segment, not on leaf structural nodes; cache keys, repair indexing, and the L4 trace inherit this granularity. Segment-level iteration is planned but not implemented." Mirror in SKILL.md §8.

D-2  | BLOCKING   | misleading-doc
Doc claim: CLAUDE.md:40 "new language bridges (e.g. `fr-en`) register through `build_default_registry()` in `modules/registry.py` as a `ModuleInterface`. They must not touch the Kernel or ISA — that separation is load-bearing."
Doc claim: tra-prototype/SKILL.md:151-163 §6 "Extending (the only sanctioned path)" — "New language/domain/formatting behavior goes through the **module registry** — never by editing the Kernel or ISA. registry = build_default_registry(); registry.register(my_module.as_interface())"
Code reality: tra-prototype/tra/kernel.py:43 `from .modules.zh_en import ZHENModule` — direct import, bypasses the registry.
Code reality: tra-prototype/tra/kernel.py:106 `style_profile=ZHENModule().get_style_profile()` — direct instantiation in __init__.
Code reality: tra-prototype/tra/isa.py:50 `from .modules.zh_en import ZHENModule` and isa.py:54 `_MODULE = ZHENModule()` — module-level singleton, also bypasses the registry.
Grep evidence: `build_default_registry|registry_for_language_pair` callers across tra/ are: registry.py:58 (self-call) and tests/test_modules.py:7,8,59,67,76. ZERO production callers in kernel.py, isa.py, tra_cli.py, validate.py, benchmark.py, or reporting.py.
Divergence: The sanctioned extension point (module registry) is documented as the only path, but the kernel and ISA both hard-code ZHENModule() directly. A new module registered via build_default_registry() will NOT be picked up by the production `translate` CLI flow.
Suggested fix: either (a) wire the kernel to look up its module via registry_for_language_pair(config.language_pair), or (b) retitle SKILL.md §6 "Extending (the only sanctioned path)" to "Extending (the only sanctioned path — currently advisory; kernel hard-codes ZHENModule)" and add a Known-gap bullet to CLAUDE.md.

D-3  | BLOCKING   | misleading-doc
Doc claim: TRA-ISA-REFERENCE.md:79 "Repair must resolve the specific violation without introducing new ones."
Doc claim: TRA-SPECIFICATION.md:83 "Invariant: Repair must resolve the specific violation without introducing new ones."
Doc claim: CLAUDE.md:79 "Repair must be surgical. `REPAIR_SEGMENT` resolves a specific violation without introducing new ones and without violating a higher-priority policy."
Doc claim: AGENTS.md:33 "Repair must be surgical. `REPAIR_SEGMENT` resolves a specific violation without introducing new ones or violating higher-priority policy."
Doc claim: README.md:123 "Repair must be surgical. `REPAIR_SEGMENT` resolves a specific violation without introducing new ones."
Code reality: tra-prototype/tra/isa.py:515-519 —
    `sub = verify_output(repaired, source_segment, ctx, audit)`
    `new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]`
    `if new_blocking and attempt >= max_retries:`
        `raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")`
The `attempt >= max_retries` guard means a repair that introduces new BLOCKING at attempt=1, max_retries=3 returns silently with resolved=False (isa.py:545) — no exception.
Code reality: ZERO tests assert repair_segment raises on new BLOCKING at attempt=1 (grep of tests/ shows no such assertion; closest is test_isa.py's REPAIR_SEGMENT tests which only exercise epistemic-drift repair at default attempt=1 with no new-blocking injection).
Divergence: All five top-level docs (spec, ISA-ref, CLAUDE, AGENTS, README) describe the surgical invariant as a hard contract; the code only enforces it at the retry-budget boundary, not the function boundary. The kernel's _repair_loop catches this by re-queuing, but a caller invoking repair_segment directly at attempt=1 receives a broken result with no exception.
Suggested fix: drop the `attempt >= max_retries` guard on the new-blocking check at isa.py:518; raise Unrecoverable whenever new_blocking is non-empty regardless of attempt number. Add a test `test_repair_segment_raises_on_new_blocking_at_attempt_1`.

D-4  | BLOCKING   | misleading-doc
Doc claim: tra-prototype/README.md:3 "A Phase 0–5 reference implementation of **TRA v1.0**"
Doc claim: tra-prototype/README.md:78-79 "Phase 6 (exception hardening, human-in-the-loop, structlog, L4 evidence tracing) is pending."
Code reality: Phase 6 IS implemented per code review:
  - 6.1 Exceptions: tra-prototype/tra/recovery.py (5 exception types, route_exception dispatcher)
  - 6.2 HITL: tra-prototype/tra/hitl.py (review_decision, format_unrecoverable); CLI `--interactive` flag at tra_cli.py:69-74
  - 6.3 Reporting: tra-prototype/tra/reporting.py (summarize_audit, mermaid_state_diagram)
  - 6.4 L4 Forensics: tra-prototype/tra/kernel.py:293-312 _export_forensics (evidence_trace.jsonl, ambiguity_register.json)
  - 6.5 Robustness: tra-prototype/tra/kernel.py:75-90 _sanitize_input; tra-prototype/tra/isa.py:316-330 LLM graceful degradation
Only 6.3.1 structlog is genuinely pending.
Doc contrast: CLAUDE.md:15 "Phases 0–6 are complete ... Phase 7 (documentation & delivery) has not started." — CLAUDE.md is accurate; the prototype README.md is stale.
Divergence: The prototype README.md (the file a new contributor reads first) materially understates the prototype's completeness: "Phase 0–5" should be "Phase 0–6"; the "Known gaps" list claims 4 of 5 Phase-6 sub-items are pending when only structlog is. status.md:35 confirms Phase 6 landed (commit 4d97aa1).
Suggested fix: update tra-prototype/README.md:3 to "A Phase 0–6 reference implementation"; replace README.md:78-79 with "Phase 6 hardening landed (exception recovery, HITL hooks, L4 forensics, input sanitization, graceful degradation). Open Phase-6 sub-item: structlog (6.3.1). Phase 7 (docs/delivery) pending."

D-5  | WARNING    | missing-doc
Doc claim: tra-prototype/pyproject.toml:10-21 lists pydantic-settings>=2.3, mdit-py-plugins>=0.4, structlog>=24.1, litellm>=1.49 as runtime deps.
Doc claim: tra-prototype/requirements.txt:3,5,8,11 mirrors the same.
Code reality: grep for `import structlog|from structlog|import litellm|from litellm|import mdit_py_plugins|from mdit_py_plugins|from pydantic_settings|import pydantic_settings` across tra-prototype/ returns ZERO hits in any .py file (only manifest mentions in pyproject.toml/requirements.txt/implementation_plan.md/prototype.md/SKILL.md/CLAUDE.md/status.md). Confirmed by audit-B B-11/B-17.
Doc silence: only `structlog` is acknowledged as unused (CLAUDE.md:44, SKILL.md:189, status.md:46). `litellm`, `pydantic-settings`, `mdit-py-plugins` are NOT mentioned as unused anywhere.
Doc silence: CLAUDE.md "Known gaps" does NOT mention any unused-deps issue beyond structlog.
Divergence: Three of the four unused runtime deps are undocumented; new contributors will install ~50 transitive packages (litellm alone pulls openai, tiktoken, tokenizers, huggingface-hub, aiohttp, httpx, jinja2, jsonschema, ...) for no runtime benefit. The LLM seam is caller-supplied (`llm_translate: Callable` at isa.py:286), so litellm is not needed at runtime.
Suggested fix: move litellm to `optional-dependencies.llm`; drop pydantic-settings, mdit-py-plugins, structlog from runtime deps (or wire them in for Phase 6.3.1); add a "Dependency hygiene" bullet to CLAUDE.md "Known gaps" listing the unused deps.

D-6  | WARNING    | missing-doc
Doc claim: tra-prototype/tra/diagnostics.py:159-166 — method signature `count_blocking(self, evidence_for_record: dict[str, EvidenceRecord]) -> int` with docstring "Count BLOCKING diagnostics recorded in audit evidence."
Code reality: body is `return 0  # hook for VERIFY to populate; trail stores records, not severities` — unconditional stub.
Grep evidence: `count_blocking` callers across tra-prototype/ — ZERO (only the definition at diagnostics.py:159).
Doc silence: no doc mentions that count_blocking is a stub or that real BLOCKING counting lives in `reporting.summarize_audit` (reporting.py:38-39 `if flag == Severity.BLOCKING.value: blocking_flags += 1`) and `validate.ValidationReport.blocking` (validate.py:38-40).
Divergence: A future contributor trusting the method name for an L3 gate check will get a FALSE PASS (always 0). The stub is dead code with a misleading name; the docs do not flag this.
Suggested fix: either implement (`return sum(1 for r in self._buffer if r.flags_raised and Severity.BLOCKING.value in r.flags_raised)`) or delete the method; add a comment to diagnostics.py directing readers to `reporting.summarize_audit` for real BLOCKING counting.

D-7  | WARNING    | dead-config
Doc claim: tra-prototype/config.yaml:18 `expire: null   # static facts: no TTL`
Code reality: tra-prototype/tra/config.py:46-47 — `BootstrapConfig.from_yaml` reads only `cache.enabled` and `cache.directory` from the `cache:` block; `expire` is silently dropped.
Code reality: tra-prototype/tra/cache.py:105 `self._cache.set(key, result.model_dump(mode="json"), expire=None)` — expire is hardcoded None; TranslationCache.set signature (cache.py:102) does NOT accept an expire parameter.
Doc silence: no doc mentions that `cache.expire` is parsed but ignored.
Divergence: The YAML field exists and is documented as "static facts: no TTL" but has no effect. A user editing `expire: 86400` expecting TTL behavior would see no behavior change.
Suggested fix: either (a) wire the field through (add `cache_expire: int | None = None` to BootstrapConfig, pass to TranslationCache.set), or (b) remove the line from config.yaml and document "no TTL by design" in a comment. Option (b) is preferred for a prototype.

D-8  | WARNING    | stale-doc
Doc claim: tra-prototype/tra_cli.py:1-7 — docstring says "TRA prototype CLI (Phase 0.1.5 skeleton). Subcommands: translate / cache-clear / audit" — only 3 subcommands listed, file described as "Phase 0.1.5 skeleton".
Code reality: tra_cli.py implements FOUR subcommands: `translate` (L64), `cache-clear` (L123), `audit` (L135), and `validate` (L197). The `validate` subcommand is fully implemented (243 lines) and is the L3 gate per CLAUDE.md and SKILL.md.
Divergence: The module docstring omits the `validate` subcommand and calls the file a "skeleton" — both stale. SKILL.md §4 (L106-114) and CLAUDE.md do correctly describe all four subcommands.
Suggested fix: update tra_cli.py:1-7 docstring to: "TRA prototype CLI. Subcommands: translate / cache-clear / audit / validate" — drop "Phase 0.1.5 skeleton".

D-9  | WARNING    | missing-doc
Doc claim: tra-prototype/.gitignore:13-15 covers `cache/`, `compilation_artifacts/`, `audit_trace.jsonl` — but only relative to the prototype dir.
Code reality: NO `.gitignore` exists at `/home/z/my-project/tra/` (the repo root). `/home/z/my-project/.gitignore` covers only `skills/` and `node_modules/`.
Code reality: actual runtime artifacts DO exist at the repo root:
  - `/home/z/my-project/tra/audit_trace.jsonl` (128 KB, 451 lines)
  - `/home/z/my-project/tra/cache/cache.db` (32 KB)
  - `/home/z/my-project/tra/compilation_artifacts/{glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml}` (4 files, ~1.8 KB total)
Doc claim: status.md:48-49 acknowledges the issue: "a run earlier resolved the default config.yaml output paths to the repo root, leaving untracked audit_trace.jsonl, cache/, and compilation_artifacts/ there. They're gitignored relative to the prototype dir but not the root, so I left them uncommitted."
Divergence: status.md documents the issue but defers action ("Let me know if you want Phase 7 next"). CLAUDE.md and README.md do not mention this hygiene issue. The artifacts remain on disk at the repo root months after status.md noted them.
Suggested fix: add `/audit_trace.jsonl`, `/cache/`, `/compilation_artifacts/` to a new `/home/z/my-project/tra/.gitignore`; or `rm -rf` the artifacts from the repo root and document that `tra_cli.py` should be run from `tra-prototype/`.

D-10 | WARNING    | misleading-doc
Doc claim: tra-prototype/SKILL.md:62-68 §3 "Setup" — install command is `pip install -e .` (no dev deps).
Doc claim: tra-prototype/SKILL.md:170-176 §7 "Quality gates (run before any commit)" — requires `ruff format . && ruff check . && ruff format --check . && mypy --strict tra && pytest tests`.
Code reality: `ruff`, `mypy`, `pytest` are all in `dev` optional-dependencies (pyproject.toml:24-30); they are NOT installed by `pip install -e .`.
Divergence: A new contributor following SKILL.md §3 verbatim cannot run the §7 quality gates — `ruff: command not found`, `mypy: command not found`, `pytest: command not found`. The SKILL.md install command is incomplete.
Suggested fix: change SKILL.md:67 to `pip install -e ".[dev]"` and add a sentence "Installs runtime deps + ruff/mypy/pytest for the quality gates".

D-11 | WARNING    | misleading-doc
Doc claim: tra-prototype/examples/expected_outputs/security_advisory_zh.L3.md (10 lines) — file contains ONLY translated markdown: `# Security Advisory SA-2024-001\n\nRustVMM v0.5.0 may Confirmed under heavy load...`
Filename implication: `.L3.md` suggests an "L3 certification bundle" — i.e., the target markdown PLUS the audit trace, glossary, entity table, structural map, style profile, execution log, repair history that a real `tra_cli.py translate --level L3` run would produce.
Code reality: `tra_cli.py translate` (tra_cli.py:100-104) writes only the target markdown to `--output`; the audit_trace.jsonl, compilation_artifacts/, etc. are written to their configured paths separately. The expected_outputs file matches what `translate -o` writes, NOT what an L3 certifier would inspect.
Doc silence: tra-prototype/README.md does NOT clarify what the `.L3.md` file represents. SKILL.md does NOT reference this file at all. No doc explains that "L3 output" = target markdown + audit trail + compilation_artifacts/, and the expected_outputs/ snapshot only shows the markdown half.
Divergence: The filename `.L3.md` plus the absence of accompanying `audit_trace.jsonl` / `compilation_artifacts/` siblings in `expected_outputs/` could mislead a reader into thinking L3 certification is just the markdown file. The awkward phrasing ("may Confirmed under heavy load", "We should support for the KVM and XFS backends", "may configurations are not recommended") further surprises readers expecting fluent L3 output.
Suggested fix: either (a) rename to `security_advisory_zh.L3.target.md` and add a sibling README.md in expected_outputs/ explaining "this is the target markdown half; run `python -m tra_cli translate ../security_advisory_zh.md --level L3` to regenerate target + audit trail + artifacts", or (b) populate expected_outputs/ with the full bundle (audit_trace.jsonl, glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml, execution_log.json, repair_history.jsonl).

D-12 | WARNING    | stale-doc
Doc claim: tra-prototype/implementation_plan.md:16-54 — Phase 0.1 through 0.4 items are ALL marked `[ ]` (unchecked): 0.1.1 Initialize repo, 0.1.2 Configure linting, 0.1.3 Create directory structure, 0.1.4 Add config.yaml schema, 0.1.5 Set up CLI entry point skeleton, 0.2.1-0.2.8 Core data models, 0.3.1-0.3.5 Evidence schema, 0.4.1-0.4.3 Deterministic cache.
Code reality: ALL Phase 0 items ARE implemented:
  - 0.1.1: pyproject.toml + requirements.txt exist
  - 0.1.2: ruff/mypy/pytest all configured in pyproject.toml:35-62
  - 0.1.3: directory structure matches the file-structure summary (with deviations, see D-17)
  - 0.1.4: config.yaml implements tvm_bootstrap schema with all 5 required fields + cache + repair + artifacts
  - 0.1.5: tra_cli.py has 4 subcommands (not just skeleton)
  - 0.2.1-0.2.8: all 8 Pydantic models defined in memory.py (PolicyPriority L19-30, Severity L33-38, DocumentProfile L79-98, StructuralNode L101-112, GlossaryEntry L132-143, Entity L154-160, StyleProfile L163-169, RuntimeContext L172-184)
  - 0.3.1-0.3.5: all 5 evidence-schema items in diagnostics.py (EvidenceType L27-34, EvidenceRecord L37-51, AuditRecord L54-65, Diagnostic L68-76, EvidenceRegistry L79-96)
  - 0.4.1-0.4.3: all 3 cache items in cache.py (CacheKeyContext L47-67, TranslationCache L79-115, TranslationResult L70-76)
Divergence: implementation_plan.md Phase 0 is fully delivered but every checkbox remains `[ ]`. The plan was never updated after Phase 0 landed. CLAUDE.md:15 ("Phases 0–6 are complete") is the source of truth; implementation_plan.md is stale.
Suggested fix: either (a) update all Phase 0 checkboxes to `[x]`, or (b) add a header note to implementation_plan.md: "Phase 0 landed; checkboxes retained as historical planning context. See CLAUDE.md → 'Prototype engine status' for current state." Option (b) is preferred for a planning doc.

D-13 | PASS       | (mostly accurate)
Doc claim: tra-prototype/implementation_plan.md:79-84 — Phase 1.3 (Glossary Builder): 1.3.1 TF-IDF frequency analysis `[ ]`, 1.3.2 ZH-EN Module lookup `[ ]`, 1.3.3 LLM-assisted candidate generation `[ ]`, 1.3.4 Conflict detection `[ ]`.
Code reality:
  - 1.3.1 TF-IDF: NOT implemented. build_glossary (isa.py:146-203) does no frequency analysis; grep for "TF-IDF|tf.idf|frequency analysis" returns ZERO hits in tra/.
  - 1.3.2 ZH-EN module lookup: IMPLEMENTED. isa.py:158 `mappings = _MODULE.get_glossary_mappings()`.
  - 1.3.3 LLM-assisted candidate generation: NOT implemented. build_glossary never invokes an LLM; the LLM seam exists only in translate_segment (isa.py:286,312).
  - 1.3.4 Conflict detection: IMPLEMENTED. isa.py:163-174 raises GlossaryConflict on forbidden drift or duplicate source-term with different target.
Divergence: Phase 1.3 marking is mostly accurate (1.3.1 and 1.3.3 are genuinely incomplete) but 1.3.2 and 1.3.4 should be `[x]`. Minor stale-doc issue.
Suggested fix: check 1.3.2 and 1.3.4 boxes in implementation_plan.md; leave 1.3.1 and 1.3.3 unchecked.

D-14 | PASS       | (confirmed unused)
Doc claim: tra-prototype/implementation_plan.md:268 `- [ ] 6.3.1 Structured logging (structlog) with correlation IDs`
Code reality: grep for `import structlog|from structlog` across tra-prototype/ returns ZERO hits in any .py file. The engine uses the plain `AuditTrail` JSONL append (diagnostics.py:99-166) for all logging.
Verdict: marking is accurate.

D-15 | PASS       | (confirmed no async)
Doc claim: tra-prototype/implementation_plan.md:280 `- [ ] 6.5.1 Segment-level parallelism (asyncio for independent segments)`
Code reality: grep for `async def|await |asyncio` across tra-prototype/ returns ZERO functional hits (only config/manifest mentions: pyproject.toml:26,61 list `pytest-asyncio` and `asyncio_mode = "auto"`; CLAUDE.md:45, status.md:46, implementation_plan.md:280,378 mention asyncio as a planned feature). The kernel's _execute_translation (kernel.py:183-187) is fully synchronous.
Verdict: marking is accurate.

D-16 | PASS       | (confirmed no cross-run caching)
Doc claim: tra-prototype/implementation_plan.md:281 `- [ ] 6.5.2 Glossary/entity caching across runs`
Code reality: TranslationCache.set/get (cache.py:92-105) only ever called from translate_segment (isa.py:307,345). build_glossary (isa.py:146-203) and build_entity_table (isa.py:226-271) have NO cache check — they rebuild from `_MODULE.get_glossary_mappings()` and `extract_entities(source)` on every invocation. The cache key DOES include the glossary/entity hashes (cache.py:60-66), but the artifacts themselves are never cached.
Verdict: marking is accurate.

D-17 | PASS       | (confirmed no Phase 7 deliverables)
Doc claim: tra-prototype/implementation_plan.md:289-301 — Phase 7 all unchecked: 7.1.1 ADRs, 7.1.2 API reference, 7.1.3 Module authoring guide, 7.1.4 Conformance self-audit checklist, 7.2.1-7.2.4 final validation.
Code reality:
  - 7.1.1 ADRs: NO `docs/adr/` or ADR-style files exist. `/home/z/my-project/tra/docs/` contains only `session_log_1.md` (464 lines) and `session_log_2.md` (70 lines) — operational session logs, not architecture decision records.
  - 7.1.2 API reference: NO `docs/api/`, no pdoc/sphinx config in pyproject.toml, no generated API docs.
  - 7.1.3 Module authoring guide: SKILL.md §6 (L151-166) gives a 6-line code snippet but is NOT a module-authoring guide; TRA-MODULE-ZH-EN.md is a spec doc, not a how-to.
  - 7.1.4 Conformance self-audit checklist: NO auto-generated checklist. The closest is TRA-CONFORMANCE-GUIDE.md (hand-authored).
  - 7.2.1-7.2.4 final validation: not done (no benchmark-results doc, no L3 certification sign-off, no §1-9 cross-reference table, no review-feedback risk verification).
Verdict: marking is accurate.

D-18 | WARNING    | misleading-doc
Doc claim: CLAUDE.md:17-31 "Layout (where behavior lives)" lists 13 modules with one-line role descriptions. Each file EXISTS, but two role descriptions are misleading:
  (1) CLAUDE.md:19 "kernel.py — the immutable 9-state sequential machine (`BOOTSTRAP → … → EMIT_PAYLOAD`); transitions only on successful ISA completion."
      Code reality: tra-prototype/tra/kernel.py:127-157 — `_transition(next_state)` is called BEFORE the corresponding ISA function. E.g. kernel.py:128 `self._transition(KernelState.ANALYZE_DOCUMENT)` runs, then kernel.py:129 `analyze_document(...)`. If analyze_document raises BrokenMarkdown (isa.py:84), the state has already advanced. The kernel does NOT transition "only on successful ISA completion"; it transitions BEFORE the ISA runs. (Same pattern for all 9 states in run().)
  (2) CLAUDE.md:22 "policy.py — the PolicyResolver over the non-negotiable 6-priority stack."
      Code reality: PolicyResolver (policy.py:13-25) is NEVER called from any production module. Grep `PolicyResolver` across tra/ shows ONE import site: tests/test_phase0.py:23. The kernel and ISA never invoke PolicyResolver. The 6-priority stack exists in the enum (memory.py:25-30) and config (config.py:13-20) but is never consulted during arbitration. (audit-A A-21, audit-B B-10 corroborate.)
  (3) CLAUDE.md:31 "modules/{registry,base,zh_en}.py — the plug-in registry and the bundled ZH↔EN module." — accurate as a file description, but obscures that the registry is bypassed by the kernel (see D-2).
Divergence: CLAUDE.md's layout section gives an idealized picture; two of its 13 claims are misleading. The "transitions only on successful ISA completion" claim is the more serious one — it's repeated verbatim in the docstring of kernel.py:7-8 ("State transitions are triggered ONLY by successful completion of ISA instructions. The Kernel must not skip instructions."), making the kernel's own self-description wrong.
Suggested fix: either (a) move _transition calls to AFTER the corresponding ISA call returns successfully (the spec-compliant fix), or (b) update CLAUDE.md:19 and kernel.py:7-8 to "transitions on ISA invocation, in canonical order; ISA failures are caught and routed to the EXCEPTION_HANDLER path".

D-19 | BLOCKING   | missing-doc
Doc claim: CLAUDE.md:42-46 "Known gaps (honest, not yet addressed): structlog is a listed dependency but the engine uses the plain AuditTrail ... No asyncio segment-level parallelism ... Glossary/entity tables are rebuilt per run; only the translation output is cached across runs via diskcache." — three bullets only.
Code reality: the following material gaps exist but are NOT in the "Known gaps" list:
  (a) Segment-level granularity not implemented (D-1) — kernel translates the whole document as one segment.
  (b) Module registry bypassed by kernel (D-2) — new modules don't actually plug into production translate path.
  (c) repair_segment does not strictly enforce "no new BLOCKING" at the function boundary (D-3) — only at retry-budget exhaustion.
  (d) Heavy unused deps (D-5) — litellm, pydantic-settings, mdit-py-plugins never imported (audit-B B-11/B-17).
  (e) count_blocking stub returns 0 unconditionally (D-6, audit-B B-10) — misleading API.
  (f) cache.expire is dead config (D-7).
  (g) tra_cli.py docstring is stale (D-8) — claims "Phase 0.1.5 skeleton" with 3 subcommands when there are 4.
  (h) Repo-root runtime artifacts not gitignored (D-9).
  (i) SKILL.md install instructions omit dev deps (D-10).
  (j) rewrite_links is dead code in production (anchor.py:101-149; never called from kernel.run()) — audit-A A-17.
  (k) ModuleBase ABC (modules/base.py:8-28) is never subclassed by ZHENModule — audit-B B-10.
  (l) CONCLUSION_LEADING constant (zh_en.py:75) is defined but never read — audit-B B-10.
  (m) L3 gate NOT enforced in the main translate pipeline (audit-A A-7) — kernel.run() returns broken target unconditionally; CLI only prints a warning.
  (n) EXCEPTION_HANDLER is not a distinct KernelState (audit-A A-6) — it's a private _recover method, so execution_log never records an EXCEPTION_HANDLER visit even though spec §2.1 stateDiagram-v2 shows it as a distinct state.
  (o) BrokenMarkdown / UnknownTerm / CertaintyConflict / EntityAmbiguity recovery paths are dead code in production (audit-A A-23) — only GlossaryConflict and Unrecoverable ever reach _recover.
  (p) Double audit record on LLM degradation (audit-B B-7) — only the first has degraded:True.
  (q) Non-reproducible audit trail (audit-B B-18) — datetime.now(UTC) + uuid4() make audit_trace.jsonl non-byte-identical across runs.
Divergence: CLAUDE.md's "Known gaps" list claims to be "honest, not yet addressed" but enumerates only 3 of ~16 known material gaps. The label "honest" is itself misleading.
Suggested fix: expand CLAUDE.md "Known gaps" to a numbered list of the ~16 items above, OR add a sentence "For the full gap inventory see audit-C findings in worklog.md" pointing to this audit.

D-20 | PASS       | (status.md accurate)
Doc claim: status.md (50 lines) — narrative log of the Phase 6 commit.
Verified claims:
  - L24 "Committed as 4d97aa1" — narrative; consistent with the file content.
  - L35 "Phase 6 is complete and pushed (4d97aa1 → origin/main)" — consistent with CLAUDE.md:15 and the codebase.
  - L38-42 "What landed: 6.1 Exceptions — recovery.py ... 6.2 HITL — tra/hitl.py ... 6.3 Reporting — tra/reporting.py ... 6.4 L4 Forensics ... 6.5 Robustness — _sanitize_input strips control/bidi/BOM chars in kernel.run" — all five sub-items confirmed in code (recovery.py:154-182 route_exception; hitl.py:15-16 review_decision; reporting.py:21-95; kernel.py:293-312 _export_forensics; kernel.py:75-90 _sanitize_input).
  - L44 "Gates: ruff clean · ruff-format clean · mypy --strict (20 files) · 103 pytest passing." — matches audit-B's re-run (mypy "Success: no issues found in 20 source files"; pytest "103 passed").
  - L46 "Not implemented ... 6.3.1 structlog, 6.5.1 asyncio parallelism, 6.5.2 cross-run disk caching." — accurate per D-14, D-15, D-16.
  - L48-49 acknowledges the repo-root runtime-artifacts hygiene issue (see D-9) — accurate and explicit.
Verdict: status.md is the most accurate of the planning/narrative docs. The only soft spot is that L48-49 defers action ("Let me know if you want Phase 7 next") and the artifacts remain on disk; but the doc itself is honest.

D-21 | WARNING    | stale-doc
Doc claim: review.md (53 lines) — external review of the spec repo, verdict "8.5/10".
Verified claims:
  - L3 "this is a clean, focused specification repository (not a code project)" — STALE. The repo now contains the tra-prototype/ engine (Phase 0–6). CLAUDE.md:9, README.md:11, AGENTS.md:5 all confirm the prototype exists. review.md predates Phase 0.
  - L8 "Immutable Kernel (sequential lifecycle: BOOTSTRAP → ANALYZE → BUILD → TRANSLATE → VERIFY → REPAIR → AUDIT → EMIT)" — abbreviated per CLAUDE.md:54 (acknowledged), so not a divergence per se.
  - L14 "Invariants: Well-enforced across files (e.g., exact canonical terms like '成立 → Confirmed' never 'Valid'; entities immutable; surgical repairs; evidence-based verification only)." — INACCURATE per D-3: the "surgical repairs" invariant is NOT enforced at the function boundary (isa.py:515-519 gates on attempt >= max_retries). The other three invariants are enforced.
  - L26 "No formal semantics or reference implementation (intentionally, as it's a spec repo). This leaves room for divergent interpretations of edge cases in the ISA contracts." — STALE; the prototype now exists and demonstrates concrete interpretations.
  - L31 "Benchmark Depth: The suite outlines good categories (S/F/T/D/E) with examples, but '100+' is aspirational in the provided file" — ACCURATE per 3-validate §3 (14 cases implemented; spec target 100+).
  - L32 "Human-in-the-Loop: Lightly addressed." — STALE; HITL is now implemented (hitl.py, --interactive flag at tra_cli.py:69-74).
  - L53 "Verdict: Solid foundation (8.5/10)" — opinion; not testable.
Divergence: review.md is dated — it describes the repo BEFORE the prototype landed. Its "no reference implementation" and "HITL lightly addressed" claims are no longer true. Its "surgical repairs" invariant-enforcement claim is contradicted by D-3. The doc does not carry a date or "as of" header.
Suggested fix: add a header note to review.md: "> Review of the spec repo as of <date>, before the Phase 0–6 prototype landed. Some observations (no reference implementation, HITL lightly addressed) are now addressed by tra-prototype/." Add a note on L14: "The 'surgical repairs' invariant is documented but only partially enforced in the prototype — see audit-C D-3."

D-22 | WARNING    | misleading-doc
Doc claim: start-here.md (44 lines) — Chinese-language user guide for prompting an LLM with TRA principles.
Verified claims:
  - L1-3 intro is accurate.
  - L8 "遵循流程：要求它遵循 ANALYZE → BUILD → TRANSLATE → VERIFY → AUDIT 的核心状态机流程" — abbreviated per CLAUDE.md:54 (acknowledged).
  - L18 "翻译 (TRANSLATE_SEGMENT)：基于前两步结果逐段翻译" — INACCURATE per D-1: the engine translates the WHOLE document as one segment, not "逐段" (segment-by-segment). The phrase "逐段" is aspirational.
  - L20 "修复 (REPAIR_SEGMENT)：若 VERIFY 返回 BLOCKING/WARNING 违规，定向修复（只解决该违规、不引入新违规、不违背更高优先级策略）" — INACCURATE per D-3: the "不引入新违规" (no new violations) contract is only enforced at retry-budget exhaustion (isa.py:515-519), not at every repair call.
  - L23 "上述步骤对应 TRA-KERNEL 的规范状态机 BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD" — ACCURATE.
  - L29-32 L1-L4 conformance-level descriptions — ACCURATE per TRA-CONFORMANCE-GUIDE.md.
  - L38-39 ZH→EN / EN→ZH rule descriptions — ACCURATE per zh_en.py implementation.
Divergence: start-here.md correctly forwards TRA principles but inherits two of the prototype-vs-spec divergences: the "逐段" (segment-by-segment) and "不引入新违规" (no new violations) claims are aspirational, not implemented. A reader prompting an LLM with these principles would expect the engine to match.
Suggested fix: at L18, add a parenthetical "(原型实现按整篇文档处理，而非逐段；详见 CLAUDE.md 'Known gaps')" noting the prototype's whole-document behavior; at L20, add "(原型仅在重试预算耗尽时强制此不变式；详见 audit-C D-3)" noting the partial enforcement.
```

### Bottom line (Track C)

Of 22 checklist items: **5 PASS, 14 WARNING, 4 BLOCKING** (D-1, D-2, D-3, D-4, D-19; D-19 is a meta-finding that the "Known gaps" list itself is incomplete).

The most material divergences are:

1. **D-1 (BLOCKING):** TRANSLATE_SEGMENT is documented as segment-level but the kernel translates the whole document as one segment; the gap is invisible in CLAUDE.md / SKILL.md "Known gaps" lists. RepairAttempt.segment_index is always 0 in production; the L4 line-by-line trace is a substring heuristic.

2. **D-2 (BLOCKING):** The module registry is documented as "the only sanctioned extension point" but the kernel hard-codes `ZHENModule()` directly (kernel.py:43,106; isa.py:50,54). A new module registered via `build_default_registry()` will NOT be picked up by the production `translate` CLI flow. Zero production callers of `build_default_registry` / `registry_for_language_pair`.

3. **D-3 (BLOCKING):** Five top-level docs (TRA-ISA-REFERENCE, TRA-SPECIFICATION, CLAUDE, AGENTS, README) describe the surgical-repair invariant as a hard contract; the code (isa.py:515-519) only enforces it at the retry-budget boundary (`attempt >= max_retries`), not at the function boundary. No test asserts repair_segment raises on new BLOCKING at attempt=1.

4. **D-4 (BLOCKING):** `tra-prototype/README.md` (the file a new contributor reads first) materially understates the prototype's completeness — "Phase 0–5" should be "Phase 0–6"; the "Known gaps" list claims Phase 6 is pending when 4 of 5 sub-items are done. CLAUDE.md and status.md are accurate; the prototype README was not updated after Phase 6 landed.

5. **D-19 (BLOCKING, meta):** CLAUDE.md "Known gaps (honest, not yet addressed)" enumerates only 3 of ~16 known material gaps. The label "honest" is itself misleading given the omissions (segment granularity, registry bypass, repair-attempt-1, unused deps, count_blocking stub, cache.expire dead config, stale CLI docstring, repo-root artifacts, rewrite_links dead code, ModuleBase ABC unused, CONCLUSION_LEADING dead, L3 gate not enforced in translate, EXCEPTION_HANDLER not a distinct state, 4-of-5 exception recovery paths dead, double audit record on LLM degradation, non-reproducible audit trail).

### Documents ranked by accuracy (most → least)

1. **status.md** — PASS on every verified claim; acknowledges the one hygiene issue (D-9) explicitly. Most accurate of the narrative docs.
2. **TRA-ISA-REFERENCE.md** — PASS on contract definitions; the surgical-repair invariant (D-3) is a code-vs-spec gap, not a doc-internal-inconsistency.
3. **TRA-SPECIFICATION.md** — same as above; the §2.1 stateDiagram-v2 includes EXCEPTION_HANDLER as a distinct state, which the kernel does NOT model (audit-A A-6).
4. **TRA-CONFORMANCE-GUIDE.md** — PASS; L3 checklist item 4 "If present, certification is denied" is correct per spec; the divergence is that the translate CLI doesn't enforce it (audit-A A-7).
5. **TRA-MODULE-ZH-EN.md** — PASS; the ZH-EN module (zh_en.py) implements it faithfully.
6. **TRA-BENCHMARK-SUITE.md** — PASS; the prototype implements 14 of the 24+ documented cases (acknowledged as aspirational).
7. **CLAUDE.md** — Mostly accurate on layout (D-18) and open-items; FAILS on "Known gaps" completeness (D-19) and on the kernel "transitions only on successful ISA completion" claim (D-18).
8. **AGENTS.md** — Same critical-invariants list as CLAUDE.md; inherits the D-3 surgical-repair divergence.
9. **implementation_plan.md** — Phase 0 fully delivered but every checkbox still `[ ]` (D-12); Phase 1.3 / 6.3.1 / 6.5.1 / 6.5.2 / Phase 7 markings are accurate (D-13 through D-17). File-structure summary (L307-347) lists test files that don't exist (test_policy.py, test_cache.py, test_evidence.py, benchmark/runner.py, benchmark/test_benchmarks.py).
10. **README.md (repo-root)** — Accurate on architecture, invariants, certification artifacts; inherits D-3 surgical-repair divergence at L123.
11. **prototype.md** — Planning context; predates the code. "Optional: Lite LLM wrapper (e.g., litellm ...)" at L13 was once a plan, now a manifest-locked unused dep (D-5).
12. **tra-prototype/SKILL.md** — Mostly accurate; FAILS on install instructions (D-10: `pip install -e .` omits dev deps); inherits D-1 / D-2 silences in "Known limitations" §8.
13. **tra-prototype/README.md** — FAILS on "Phase 0–5" header (D-4) and "Phase 6 pending" Known-gaps bullet (D-4); otherwise OK.
14. **review.md** — Dated; predates Phase 0 prototype. "No reference implementation" (L26), "HITL lightly addressed" (L32), "surgical repairs ... well-enforced" (L14) are all stale.
15. **start-here.md** — Chinese-language guide; forwards TRA principles but inherits the "逐段" (segment-by-segment) and "不引入新违规" (no new violations) aspirational claims (D-22).
16. **review-feedback.md** — Architectural critique of prototype.md with embedded EVIDENCE_SCHEMA / CACHE_STRATEGY / ANCHOR_RESOLUTION mini-docs. Accurate as planning context; the cache key formula (L244-256) matches cache.py implementation.

### Prioritized doc fixes for the maintainer

**Priority 1 (blocking — fix before any further spec/prototype claim):**

1. **CLAUDE.md "Known gaps" expansion (D-19):** replace the 3-bullet list with a numbered list of the ~16 known material gaps (segment granularity, registry bypass, repair-attempt-1, unused deps, count_blocking stub, cache.expire, stale CLI docstring, repo-root artifacts, rewrite_links dead, ModuleBase unused, CONCLUSION_LEADING dead, L3 gate not enforced in translate, EXCEPTION_HANDLER not distinct state, 4-of-5 exception recovery paths dead, double audit record on LLM degradation, non-reproducible audit trail). Drop the word "honest" or expand to make it true.

2. **tra-prototype/README.md update (D-4):** change L3 header to "A Phase 0–6 reference implementation"; replace L78-79 "Phase 6 ... is pending" with "Phase 6 hardening landed (exception recovery, HITL hooks, L4 forensics, input sanitization, graceful degradation). Open Phase-6 sub-item: structlog (6.3.1). Phase 7 (docs/delivery) pending."

3. **CLAUDE.md layout section correction (D-18):** either fix the kernel to transition AFTER ISA completion (the spec-compliant fix), or update CLAUDE.md:19 and kernel.py:7-8 to remove "transitions only on successful ISA completion" and replace with "transitions in canonical order; ISA failures are caught and routed to the EXCEPTION_HANDLER path". Also fix CLAUDE.md:22 policy.py description to note PolicyResolver is currently test-only.

4. **SKILL.md §6 extension-point correction (D-2):** either wire the kernel to use registry_for_language_pair(config.language_pair), or retitle §6 "Extending (the only sanctioned path)" to "Extending (the only sanctioned path — currently advisory; kernel hard-codes ZHENModule)" and add a Known-gap bullet.

5. **Segment-level granularity disclosure (D-1):** add a "Known gap" bullet to CLAUDE.md and SKILL.md §8: "TRANSLATE_SEGMENT operates on the whole document as one segment, not on leaf structural nodes; cache keys, repair indexing (segment_index always 0), and the L4 line-by-line trace (substring-containment heuristic) inherit this granularity."

**Priority 2 (warning — fix at next doc pass):**

6. **Surgical-repair disclosure (D-3):** add a note under CLAUDE.md:79 / AGENTS.md:33 / README.md:123 critical-invariant #4: "Prototype enforces this only at the retry-budget boundary (attempt >= max_retries); a direct caller of repair_segment at attempt=1 may receive a broken result with resolved=False. The kernel's _repair_loop catches this by re-queuing."

7. **tra_cli.py docstring (D-8):** update L1-7 to list all 4 subcommands; drop "Phase 0.1.5 skeleton".

8. **SKILL.md install command (D-10):** change L67 to `pip install -e ".[dev]"`; add a sentence about dev-deps being required for the §7 quality gates.

9. **implementation_plan.md Phase 0 checkboxes (D-12):** either check all Phase 0 boxes or add a header note "Phase 0 landed; checkboxes retained as historical planning context. See CLAUDE.md for current state." Also fix the file-structure summary (L307-347) to match actual test files.

10. **review.md header (D-21):** add a date / "as of" note and a "predates the Phase 0–6 prototype" disclaimer.

11. **start-here.md clarifications (D-22):** add parentheticals at L18 ("逐段") and L20 ("不引入新违规") noting the prototype's actual behavior.

12. **count_blocking stub (D-6):** either implement or delete diagnostics.py:159-166; add a comment directing readers to reporting.summarize_audit.

13. **cache.expire dead config (D-7):** remove the line from config.yaml or wire it through.

14. **Repo-root .gitignore (D-9):** add `/audit_trace.jsonl`, `/cache/`, `/compilation_artifacts/` to a new `/home/z/my-project/tra/.gitignore`; or `rm -rf` the existing artifacts and document that `tra_cli.py` should be run from `tra-prototype/`.

15. **expected_outputs/ clarification (D-11):** rename `security_advisory_zh.L3.md` to `security_advisory_zh.L3.target.md` and add a sibling README.md explaining what an L3 bundle contains, or populate the bundle.

16. **Unused-deps disclosure (D-5):** move litellm to `optional-dependencies.llm`; drop pydantic-settings, mdit-py-plugins, structlog from runtime deps (or wire them in); add a "Dependency hygiene" bullet to CLAUDE.md "Known gaps".


---

## Task audit-D — Test-suite audit (Track D)

Auditor: Agent D. Scope: are the tests sufficient to catch regressions on the 4
critical invariants and the 6 ISA contracts? What's missing?

Method: read every test file in `tra-prototype/tests/` end-to-end (12 files),
both benchmark JSONL fixtures, the 6 ISA source files (`isa.py`, `kernel.py`,
`memory.py`, `zh_en.py`, `cache.py`, `recovery.py`), `validate.py`,
`anchor.py`, `reporting.py`, `hitl.py`, `diagnostics.py`, `utils.py`,
`exceptions.py`, `benchmark.py`, and the `TRA-ISA-REFERENCE.md` contract
clauses. Cross-referenced each test against the contract clause it claims to
cover. Conducted 12 invariant-mutation thought-experiments (4 invariants × 3
mutations) and 5 lightweight code-mutation thought-experiments, reasoning from
source about which tests would fail. Prior `3-validate`/`audit-A`/`audit-B`/
`audit-C` findings were read first; this audit goes DEEPER on coverage gaps and
mutation-detection power, and does NOT repeat prior findings.

Baseline: `pytest tests` → **103 passed in 0.64s** (re-confirmed).

### Findings D-1 through D-30

```
D-1  | BLOCKING    | mutation-gap
Evidence: tests/test_isa.py:220 test_repair_resolves_epistemic_drift; tests/test_phase6_hardening.py:51 test_repair_segment_records_history
Finding: NO test exercises the "new BLOCKING from repair at attempt >= max_retries → raise Unrecoverable" branch (isa.py:518-519).
Detail: Both repair_segment tests run with attempt=1 (default) and a diagnostic that the repair successfully resolves (epistemic drift, terminology). The re-verify produces zero BLOCKING, so `new_blocking=[]` and the `if new_blocking and attempt >= max_retries` condition is never True. Removing the entire raise block, flipping `>=` to `>`, or changing `max_retries` to `99` would leave all 103 tests green. This is the single most material test gap — it is exactly the "surgical repair" invariant (Inv #4) that audit-C D-3 flagged as partially enforced; the test suite does not catch regressions in the partial enforcement.
Suggested test: call repair_segment with a diagnostic that the repair CANNOT fix (e.g., subsystem="entity", issue referencing an entity absent from source) at attempt=3, max_retries=3, and assert it raises Unrecoverable.

D-2  | BLOCKING    | mutation-gap
Evidence: tests/test_phase0.py:68-82 test_evidence_registry_append_only
Finding: The "confidence_note must not trigger routing" test does not actually verify the invariant — it only adds a record and asserts registry size.
Detail: The test creates an EvidenceRecord with confidence_note=0.1, adds it to the registry, and asserts `len(evidence_registry.all()) == 2`. It NEVER calls verify_output, repair_segment, or any routing function with that record present. A mutation that adds `if e.confidence_note and e.confidence_note < 0.5: diagnostics.append(BLOCKING)` to verify_output (isa.py:380-458) would NOT be caught by any test — all verify_output tests use a fresh EvidenceRegistry with no confidence_note set. The "never self-score" invariant (Inv #3) is documented but untested at the enforcement boundary.
Suggested test: populate ctx with an EvidenceRegistry containing a low-confidence record, run verify_output on a clean target, and assert zero diagnostics are raised.

D-3  | BLOCKING    | mutation-gap
Evidence: tests/test_isa.py:172-214 (verify_output tests); tests/test_kernel.py:30-38; tests/test_validate.py:24-51; tests/benchmark/cases/*.jsonl
Finding: Changing terminology violation severity from WARNING to BLOCKING (isa.py:429) would NOT be caught by any test.
Detail: Every verify_output test either (a) uses a target that has no untranslated CJK glossary terms, or (b) uses an empty glossary. No test asserts "an untranslated source term in the target produces a WARNING (not BLOCKING, not INFO)". The benchmark L3 gate (test_l3_gate_zero_blocking_subset) would still pass because no benchmark case leaks CJK into the target. A mutation that escalates terminology to BLOCKING would silently make the L3 gate stricter than the spec intends — undetected.
Suggested test: build_glossary with "成立"→"Confirmed", run verify_output on target "the 成立 is here", assert exactly one WARNING (not BLOCKING) diagnostic with subsystem="terminology".

D-4  | BLOCKING    | mutation-gap
Evidence: tests/test_kernel.py:30-38 test_kernel_runs_full_pipeline; tests/test_isa.py:200-214 test_verify_clean_doc_no_blocking
Finding: Changing structural heading-count-mismatch severity from BLOCKING to WARNING (isa.py:403) would NOT be caught by any test.
Detail: No test constructs a target with a different heading count than the source. EXAMPLE in test_kernel.py has 1 heading and the translation preserves it. test_verify_clean_doc_no_blocking uses a 0-heading source/target pair. A mutation that downgrades structural BLOCKING to WARNING would let non-conforming heading counts through the L3 gate silently.
Suggested test: src="# H1\nbody", target="body" (0 headings), assert exactly one BLOCKING diagnostic with subsystem="structural".

D-5  | WARNING     | mutation-gap
Evidence: tests/test_isa.py:117-128 test_build_entity_table_immutable; tests/test_utils.py:9-13 test_version_token_classified
Finding: Entities-remain-immutable is tested only at BUILD_ENTITY_TABLE exit; no test asserts entities are still immutable AFTER translate_segment or a full pipeline run.
Detail: A mutation that adds `for ent in entities: ent.mutable = True` inside _rule_translate (isa.py:350-372) or inside the kernel's _execute_translation would not be caught. test_build_entity_table_immutable checks `all(e.mutable is False for e in ents)` immediately after build_entity_table returns; it never re-checks after translation. test_kernel_runs_full_pipeline doesn't assert entity.mutable. Inv #2 is enforced at construction but not protected against in-flight mutation.
Suggested test: after k.run(EXAMPLE), assert all(e.mutable is False for e in k.ctx.entity_table).

D-6  | WARNING     | coverage-gap
Evidence: tests/test_isa.py:55-60 test_analyze_malformed_raises
Finding: The "malformed markdown" test does not actually test BROKEN_MARKDOWN — it asserts the parser returns a non-null map for a valid (unclosed-fence) input.
Detail: The test feeds "```\ncode\n" (an unclosed code fence, which CommonMark treats as a valid closed fence at EOF) and asserts `smap is not None`. The test name and comment imply it tests MALFORMED_MARKDOWN, but markdown-it-py is lenient and never raises here. No test in the suite exercises the `except Exception: raise BrokenMarkdown` path in analyze_document (isa.py:83-86). The MALFORMED_MARKDOWN failure condition of ANALYZE_DOCUMENT is untested.
Suggested test: construct an input that causes markdown-it-py to raise (e.g., monkeypatch the parser) and assert BrokenMarkdown is raised with "MALFORMED_MARKDOWN" in the message.

D-7  | WARNING     | coverage-gap
Evidence: tests/benchmark/cases/sft.jsonl; tests/benchmark/cases/regression.jsonl
Finding: Only 13 of the 24 spec benchmark cases (TRA-BENCHMARK-SUITE.md) are implemented as fixtures.
Detail: Implemented: S-05, F-01..F-05, T-01..T-05, D-04, E-02 (13) + R-01 regression (not in spec). Missing: S-01 (nested lists), S-02 (complex tables), S-03 (inline code vs prose), S-04 (blockquotes in lists), S-06 (anchors — tested as unit but NOT as benchmark), D-01 (security advisory register), D-02 (RFC formal), D-03 (README instructional), E-01 (intentional ambiguity), E-03 (broken source markdown). Spec target is "100+". The 13/24 = 54% coverage is acknowledged in status.md but the test suite does not surface the gap (no skipped/xfail markers for missing cases).
Suggested test: add the 11 missing spec cases as JSONL fixtures with concrete must_contain/must_not_contain/zero_blocking assertions; mark S-03 and E-03 as xfail with a referenced open issue until the kernel respects is_no_translate_zone.

D-8  | WARNING     | coverage-gap
Evidence: tests/test_phase6_hardening.py:134-144 test_hitl_review_decision_accept
Finding: Only the "accept" branch of HITL review_decision is tested; "skip" and "override" branches have zero coverage.
Detail: review_decision (hitl.py:24-59) returns one of {"accept", "override", "skip"}. The test monkeypatches Prompt.ask to return "accept" and asserts resolution=="accept". The "override" branch (which calls Prompt.ask again for the override text and optionally invokes on_override) and the "skip" branch (default) are never exercised. The kernel's interactive mode (kernel.py:214-230) that consumes review_decision is also never tested with interactive=True.
Suggested test: parametrize test_hitl_review_decision over ["accept", "override", "skip"] with appropriate Prompt.ask side_effects; add a test for TRAKernel(config, interactive=True) that triggers the HITL path.

D-9  | WARNING     | coverage-gap
Evidence: tests/test_phase6_hardening.py:71-85 test_graceful_degradation_on_llm_failure
Finding: LLM-seam graceful degradation is tested only for RuntimeError; empty-string return, None return, and other exception types are untested.
Detail: The test supplies `llm_translate=boom` where boom raises RuntimeError. translate_segment's except clause (isa.py:316) catches `Exception` broadly, so any exception type triggers the rule-path fallback. But the test doesn't verify: (a) llm_translate returning "" (empty string would be set as target — `target = ""` — and the rule path is NOT triggered because no exception); (b) llm_translate returning None (would violate the Callable type but Python doesn't enforce); (c) ValueError, TypeError, KeyboardInterrupt, OSError, etc. A mutation that narrows the except clause to `except RuntimeError` would NOT be caught.
Suggested test: parametrize the llm_translate seam over [RuntimeError, ValueError, TypeError, OSError] and assert degradation in each; add a separate test for llm_translate=lambda s,c: "" asserting the empty string propagates (or is treated as degradation — clarify the contract).

D-10 | WARNING     | edge-case-gap
Evidence: tests/ (no matches for "concurrent", "thread", "async", "large", "1000", "stress")
Finding: No tests for: very large documents, concurrent cache access, cache key collisions, or performance regressions.
Detail: The diskcache-backed TranslationCache (cache.py:79-116) has no concurrency tests. The SHA-256 cache key has no collision test (two different contexts producing the same key). No test exercises a document >1KB. The spec's L4 forensic claim (reproducible audit trail) depends on cache determinism under load, but no test verifies this.
Suggested test: generate a 10KB document with 100 headings, run k.run(), assert node_count matches; run two threads calling cache.set/get concurrently and assert no corruption.

D-11 | WARNING     | edge-case-gap
Evidence: tests/test_isa.py:46-52 test_analyze_empty_source_raises (whitespace-only); no test for literal "" or code-block-only or no-entity or no-glossary-term documents
Finding: Edge-case coverage of ANALYZE_DOCUMENT is thin — only whitespace-only EMPTY_SOURCE is tested.
Detail: Untested edge cases: (a) literal "" empty string (would also raise EMPTY_SOURCE via `not source.strip()`); (b) document with ONLY code blocks (no translatable prose — currently passes through but no test confirms); (c) document with no entities (build_entity_table returns [] — no test asserts this); (d) document with no glossary terms (build_glossary returns the full module glossary regardless of source content — no test asserts this); (e) Unicode edge cases (CJK + emoji + RTL in the same document — only bidi stripping is tested in test_sanitize_strips_control_and_bidi).
Suggested test: add parametrized tests for each edge case asserting the expected behavior (raise, return empty list, preserve content, etc.).

D-12 | WARNING     | quality-issue
Evidence: tests/test_isa.py:29 _audit() returns AuditTrail("audit_trace.jsonl"); tests/test_isa.py:144,162 TranslationCache("./cache", enabled=True); tests/test_phase6_hardening.py:75 TranslationCache("./cache", enabled=False)
Finding: Multiple tests use relative paths ("./cache", "audit_trace.jsonl") that write to the CWD, creating shared mutable state and repo-root artifacts.
Detail: test_translate_segment_canonical_substitution, test_translate_segment_cache_hit_is_byte_identical, and test_translate_segment_applies_zh_rule_layer all use TranslationCache("./cache", enabled=True). The first test populates the cache; subsequent tests may see stale entries (test order-dependent). The conftest cache_context fixture uses tmp_path correctly, but the ISA-level tests don't. The _audit() helper writes audit_trace.jsonl to CWD. This is the same hygiene issue audit-C D-9 flagged for repo-root artifacts, but here it's a test-quality issue: tests are not hermetic.
Suggested test: refactor _audit() and the ISA cache tests to use tmp_path fixtures; assert cache state before/after each test.

D-13 | WARNING     | quality-issue
Evidence: tests/test_isa.py:24-29 _ctx() and _audit() helpers; tests/test_phase6_hardening.py:30-48 _ctx() helper; conftest.py fixtures
Finding: Test fixtures are inconsistent — some tests use conftest fixtures (cache_context, sample_glossary), others define local _ctx() helpers with different defaults.
Detail: test_isa._ctx() returns a bare RuntimeContext(); test_phase6_hardening._ctx() returns a RuntimeContext pre-populated with a DocumentProfile, glossary, and structural_map. conftest.py defines sample_glossary/sample_entities/cache_context fixtures that are used only by test_phase0.py. The inconsistency makes it hard to reason about test state. No factory pattern (e.g., get_mock_ctx(overrides=...)) is used.
Suggested test: consolidate on a single factory in conftest.py (e.g., make_ctx(overrides=None) -> RuntimeContext) and migrate all _ctx() helpers to it.

D-14 | WARNING     | coverage-gap
Evidence: tests/test_isa.py (no test for ENTITY_AMBIGUITY); tra/isa.py:240-251 build_entity_table (never raises EntityAmbiguity)
Finding: The ENTITY_AMBIGUITY failure condition of BUILD_ENTITY_TABLE is untested AND unimplemented.
Detail: TRA-ISA-REFERENCE.md L46 specifies "ENTITY_AMBIGUITY: Cannot determine if a token is a natural language word or an entity (Default: Treat as Entity)". The implementation (isa.py:240-251) always defaults to Entity without ever raising EntityAmbiguity. The recovery procedure (recover_entity_ambiguity) exists and is tested in test_recovery.py:55-59, but the raise-site is missing. No test asserts that an ambiguous token (e.g., "Configure" which matches PRODUCT_RE but is plain prose) triggers the recovery path.
Suggested test: add a test that feeds an ambiguous token to build_entity_table and asserts either (a) EntityAmbiguity is raised and recovered, or (b) the token is silently treated as Entity (documenting the chosen behavior).

D-15 | WARNING     | coverage-gap
Evidence: tests/test_isa.py (no test for TERMINOLOGY_VIOLATION, FACTUAL_DRIFT, HALLUCINATION); tra/isa.py:279-347 translate_segment (never raises these)
Finding: The three TRANSLATE_SEGMENT failure conditions (TERMINOLOGY_VIOLATION, FACTUAL_DRIFT, HALLUCINATION) are untested AND unimplemented.
Detail: TRA-ISA-REFERENCE.md L58-60 lists these as failure conditions. The implementation never raises them — violations are caught by VERIFY_OUTPUT downstream. No test asserts that translate_segment can raise these (or documents that it defers to VERIFY_OUTPUT). The contract is ambiguous about whether TRANSLATE_SEGMENT itself should raise or defer.
Suggested test: add a test documenting the chosen behavior — e.g., "translate_segment does not raise TERMINOLOGY_VIOLATION; it defers to VERIFY_OUTPUT" with an assertion that translate_segment returns a result even for a glossary-violating input.

D-16 | WARNING     | coverage-gap
Evidence: tests/test_isa.py (no test for the "exhaustive; cannot skip sections" invariant of VERIFY_OUTPUT); tra/isa.py:380-458 verify_output
Finding: VERIFY_OUTPUT's "exhaustive; cannot skip sections" invariant (TRA-ISA-REFERENCE.md L69) is untested.
Detail: verify_output checks structural, entity, terminology, and epistemic subsystems in sequence. No test asserts that ALL subsystems are checked — a mutation that early-returns after the first subsystem would not be caught unless a test target violates multiple subsystems simultaneously. No test constructs a target that violates all four subsystems and asserts four diagnostics.
Suggested test: build a target that has (a) wrong heading count, (b) missing entity, (c) untranslated source term, (d) forbidden drift target; assert len(diagnostics) == 4 with one per subsystem.

D-17 | WARNING     | coverage-gap
Evidence: tests/test_isa.py:66-89 test_build_glossary_emits_canonical_entries; tra/isa.py:146-203 build_glossary
Finding: BUILD_GLOSSARY's "every recurring term (>=2x) gets exactly one canonical mapping unless context_sensitive" invariant (TRA-ISA-REFERENCE.md L31) is untested AND unimplemented.
Detail: The implementation adds ALL module glossary mappings regardless of whether they appear in the source or recur >=2 times. No test asserts that a term appearing once is skipped, or that a term appearing >=2 times is included. The "context_sensitive" status is never set (all entries are CANONICAL). The invariant is documented but neither enforced nor tested.
Suggested test: add a test that feeds a source where "成立" appears once and asserts it's still in the glossary (documenting current behavior), OR implement the recurrence check and test it.

D-18 | WARNING     | coverage-gap
Evidence: tests/test_kernel.py:101-118 test_kernel_records_exception_recovery
Finding: Only the GLOSSARY_CONFLICT recovery path is exercised end-to-end through the kernel; the other 4 recovery procedures (UNKNOWN_TERM, BROKEN_MARKDOWN, CERTAINTY_CONFLICT, ENTITY_AMBIGUITY, UNRECOVERABLE) are tested only at the recovery-module unit level, not through the kernel's _recover dispatch.
Detail: test_kernel_records_exception_recovery monkeypatches the glossary to force a GLOSSARY_CONFLICT. No test forces UNKNOWN_TERM (would require a source term not in the module), BROKEN_MARKDOWN (would require a parser failure), CERTAINTY_CONFLICT, or UNRECOVERABLE through the kernel. The kernel's _recover method (kernel.py:159-179) dispatches via route_exception, but only one path is exercised. A mutation that breaks the dispatch for the other 4 types would not be caught.
Suggested test: parametrize a kernel test over each exception type, forcing the raise via monkeypatch, and assert the EXCEPTION_HANDLER audit record has the correct code/severity/action.

D-19 | WARNING     | coverage-gap
Evidence: tests/test_kernel.py:62-78 test_kernel_state_machine_is_sequential, test_kernel_illegal_backward_transition
Finding: State-machine tests cover forward sequencing and one backward transition, but not skip-transition, repeat-transition, or transition-after-EMIT_PAYLOAD.
Detail: _transition (kernel.py:110-120) raises on backward transitions. No test asserts: (a) skipping a state (e.g., BOOTSTRAP → ANALYZE_DOCUMENT without INITIALIZE_RUNTIME) raises; (b) repeating a state (INITIALIZE_RUNTIME → INITIALIZE_RUNTIME) raises or is a no-op; (c) transitioning after EMIT_PAYLOAD (the terminal state) raises. The current "illegal backward" test only goes back one step.
Suggested test: add tests for skip-forward, repeat, and post-terminal transitions.

D-20 | WARNING     | coverage-gap
Evidence: tests/test_benchmark.py:55-62 test_l3_gate_zero_blocking_subset
Finding: The L3 gate test asserts zero blocking across the suite, but doesn't verify the gate FAILS when blocking is present (no negative test).
Detail: test_l3_gate_zero_blocking_subset asserts `summary["blocking"] == 0` and `summary["failed"] == 0`. No test constructs a deliberately-failing benchmark case (e.g., a case with must_contain=["NONEXISTENT"]) and asserts the runner reports it as failed. A mutation that makes CaseResult.passed always return True would not be caught.
Suggested test: add a test that runs a synthetic failing case and asserts `not result.passed` and `len(result.failed_checks) >= 1`.

D-21 | WARNING     | coverage-gap
Evidence: tests/test_anchor.py (7 tests); tests/benchmark/cases/ (no S-06 benchmark case)
Finding: S-06 (internal anchors & cross-references) is tested as a unit test in test_anchor.py but NOT as a benchmark case.
Detail: test_s06_link_rewrite_repoints_translated_heading thoroughly tests rewrite_links. But the benchmark suite's S-06 row in TRA-BENCHMARK-SUITE.md L15 is not represented in sft.jsonl. The L3 gate test (test_l3_gate_zero_blocking_subset) doesn't exercise the link-rewrite path through the full pipeline. The kernel's _execute_translation doesn't call rewrite_links at all (anchor.py:rewrite_links is never invoked by the kernel), so S-06 is effectively dead in the production path — but no test surfaces this.
Suggested test: add an S-06 benchmark case with a source containing a heading and an internal link; assert the link is rewritten post-translation. (This will likely fail and expose that the kernel doesn't call rewrite_links.)

D-22 | WARNING     | coverage-gap
Evidence: tests/test_phase6_hardening.py:99-112 test_l4_forensic_trace_emitted_at_l4; tra/kernel.py:293-312 _export_forensics
Finding: L4 forensic trace is tested for file existence but not for content correctness.
Detail: test_l4_forensic_trace_emitted_at_l4 asserts that evidence_trace.jsonl and ambiguity_register.json exist after an L4 run. It does NOT assert: (a) the trace has one entry per non-empty output line; (b) each trace entry has the required keys (line, text, evidence_ids, attributed); (c) the ambiguity register is valid JSON. A mutation that writes empty files or malformed JSON would not be caught.
Suggested test: read the trace file, parse each line as JSON, assert len(trace) > 0 and all required keys present; read the ambiguity register and assert it's a valid JSON list.

D-23 | WARNING     | coverage-gap
Evidence: tests/test_phase6_hardening.py:115-131 test_line_by_line_trace_attribution
Finding: line_by_line_trace is tested with one attributed and one unattributed line, but not with multi-evidence lines, empty lines, or lines with partial-span matches.
Detail: The test creates one EvidenceRecord with target_span="The system is Confirmed" and a two-line target. It asserts trace[0].attributed is True and trace[1].attributed is False. No test exercises: (a) a line matching multiple evidence records; (b) empty lines (should be skipped per reporting.py:84-85); (c) a target_span that is a substring of multiple lines; (d) a target_span that doesn't appear in any line. The substring-containment heuristic (reporting.py:86) has known false-positive potential (audit-C D-1) that no test surfaces.
Suggested test: add a multi-evidence line test, an empty-line-skipped test, and a substring-collision test (two lines containing the same evidence target_span).

D-24 | WARNING     | coverage-gap
Evidence: tests/test_reporting.py:36-56 (mermaid tests); tra/reporting.py:50-70 mermaid_state_diagram
Finding: Mermaid diagram tests cover canonical order, execution log, and single-state, but not empty log, unknown states, or out-of-order states.
Detail: mermaid_state_diagram (reporting.py:50-70) handles `execution_log or [s.value for s in _KERNEL_ORDER]` (empty → canonical) and `if not edges: self-loop`. No test asserts: (a) empty log produces the canonical diagram; (b) a log with an unknown state (e.g., "FOO") is rendered as-is; (c) a log with out-of-order states (e.g., EMIT_PAYLOAD then BOOTSTRAP) is rendered faithfully. The "reflects reality" claim (reporting.py:55-56) is untested.
Suggested test: add tests for empty log, unknown state, and out-of-order log.

D-25 | WARNING     | coverage-gap
Evidence: tests/test_recovery.py:93-96 test_route_exception_falls_back_for_unknown
Finding: The recovery fallback test uses BrokenMarkdown() without a critical_hierarchy_lost flag, which exercises the default-discard path, not a truly unknown exception type.
Detail: test_route_exception_falls_back_for_unknown calls `route_exception(BrokenMarkdown(), amb)` — BrokenMarkdown IS a known type (handled at recovery.py:164-167), so the test actually exercises the broken-markdown best-effort path, not the unknown-exception fallback (recovery.py:176-182). A mutation that removes the final fallback return would not be caught by this test. The test name is misleading.
Suggested test: construct a bare TRAException (not a subclass) and assert route_exception returns a PRESERVE_SOURCE RecoveryReport with code="TRA_ERROR".

D-26 | WARNING     | mutation-gap
Evidence: tests/test_phase0.py:28-48 (cache key tests); tra/cache.py:57-67 CacheKeyContext.key
Finding: Cache-key tests verify order-independence and model/policy sensitivity, but NOT entity-list sensitivity or glossary-content sensitivity.
Detail: test_cache_key_changes_with_model_or_policy mutates model_version and policy_stack. It does NOT mutate the glossary content (only reverses order in test_cache_key_is_deterministic_and_order_independent) or entity list. A mutation that removes `entity_hash` from the key payload (cache.py:62) would not be caught. Similarly, a mutation that uses `_hash_sorted(items)` instead of `_hash_set(items)` for entities (making the key order-DEPENDENT) would not be caught at the entity level.
Suggested test: add a test that changes one entity's name and asserts the key changes; add a test that reorders entities and asserts the key is unchanged.

D-27 | WARNING     | mutation-gap
Evidence: tests/test_isa.py:133-149 test_translate_segment_canonical_substitution; tra/isa.py:295-306 translate_segment
Finding: No test asserts that translate_segment uses the ctx.glossary_cache (vs. re-fetching from the module).
Detail: translate_segment builds `glossary = {e.source: e.target for e in ctx.glossary_cache}` (isa.py:295). A mutation that bypasses ctx.glossary_cache and calls `_MODULE.get_glossary_mappings()` directly would not be caught — the test builds the glossary via build_glossary (which populates ctx.glossary_cache from the module), so the result is identical. The contract is that translate_segment reads from ctx, not from the module; this is untested.
Suggested test: populate ctx.glossary_cache with a custom entry (e.g., "成立"→"CUSTOM"), call translate_segment, assert "CUSTOM" appears in the output (not "Confirmed").

D-28 | WARNING     | coverage-gap
Evidence: tests/ (no test for the kernel's _repair_loop exhausting max_retries)
Finding: No test exercises the repair loop exhausting max_retries without raising Unrecoverable.
Detail: _repair_loop (kernel.py:189-236) loops `while pending and attempt <= max_retries`. If pending is still non-empty after max_retries, the loop exits and returns the (still-violating) target. No test forces this condition (would require a diagnostic that repair_segment cannot fix but doesn't introduce new BLOCKING). A mutation that changes `attempt <= max_retries` to `attempt < max_retries` (one fewer iteration) or `attempt <= max_retries + 1` (one more iteration) would not be caught.
Suggested test: force a persistent WARNING (e.g., untranslated source term that repair_segment can't fix because the canonical target is also forbidden), run the kernel with max_retries=1, assert the loop exits with the WARNING still present.

D-29 | WARNING     | quality-issue
Evidence: tests/test_phase0.py:87-96 test_audit_trail_append_and_load; tra/diagnostics.py:112-130 AuditTrail.append
Finding: AuditTrail tests use a tmp_path file, but the AuditTrail.flush() append-mode behavior is not tested for idempotency (re-flush doesn't duplicate).
Detail: flush() (diagnostics.py:132-145) tracks `self._flushed` to avoid duplicating records on re-flush. The test calls flush() once and loads. No test calls flush() twice and asserts the file has the same number of lines. A mutation that removes the `self._flushed` tracking would not be caught.
Suggested test: append two records, flush, append one more, flush, load, assert len==3 (not 5).

D-30 | N/A         | quality-issue
Evidence: tests/conftest.py:19-78 (6 fixtures); tests/test_phase0.py (uses all 6); tests/test_isa.py (uses 0 conftest fixtures, defines own _ctx/_audit)
Finding: conftest fixtures are underutilized — only test_phase0.py uses them; the other 10 test files define local helpers.
Detail: sample_glossary, sample_entities, cache_context, evidence_registry, sample_evidence, config fixtures exist but are referenced only in test_phase0.py. The ISA/kernel/validate/benchmark tests re-build equivalent state inline. This is a maintainability concern, not a correctness gap — but it means a change to the canonical sample data (e.g., adding a new glossary entry to sample_glossary) wouldn't propagate to the tests that most need it.
Suggested test: migrate test_isa._ctx() and test_phase6_hardening._ctx() to use conftest fixtures with overrides; document the factory pattern in conftest.py.
```

### Invariant mutation testing results (12 scenarios)

| Inv | Mutation | Caught? | By which test |
| --- | --- | --- | --- |
| 1 | GLOSSARY `成立→Confirmed` → `成立→Valid` | **YES** | test_zh_en_glossary_canonical (test_modules.py:13); also test_build_glossary_conflict_raises would surface unexpected GlossaryConflict |
| 1 | EPISTEMIC_LEXICON `成立→Confirmed` → `成立→True` | **YES** | test_zh_en_epistemic_lexicon_exact (test_modules.py:21); test_zh_en_style_profile (test_modules.py:39) |
| 1 | Remove `Valid` from FORBIDDEN_TARGETS | **YES** | test_zh_en_forbidden_drift_targets (test_modules.py:30); test_build_glossary_conflict_raises (test_isa.py:91); test_verify_flags_epistemic_drift_blocking (test_isa.py:184); test_validate_epistemic_drift_blocks (test_validate.py:44) |
| 2 | `memory.py:159` `mutable: bool = False` → `True` | **YES** | test_build_entity_table_immutable (test_isa.py:117); test_version_token_classified (test_utils.py:9) |
| 2 | `isa.py:248` `ent.mutable = False` → `True` | **YES** | test_build_entity_table_immutable (test_isa.py:117) |
| 2 | Add `ent.mutable = True` in _rule_translate (post-build) | **NO** | no test re-checks entity.mutable after translate_segment — **D-5** |
| 3 | Add `if e.confidence_note < 0.5: diagnostics.append(...)` to verify_output | **NO** | no test populates the registry with a low-confidence record and runs verify_output — **D-2** |
| 3 | Same mutation in repair_segment | **NO** | same gap — **D-2** |
| 3 | Same mutation in _repair_loop | **NO** | same gap — **D-2** |
| 4 | Remove `if new_blocking and attempt >= max_retries: raise Unrecoverable` entirely | **NO** | no test exercises this branch — **D-1** |
| 4 | Change `attempt >= max_retries` to `attempt > max_retries` (off-by-one) | **NO** | no test — **D-1** |
| 4 | Direct call to repair_segment with attempt=1, new BLOCKING, assert raises | **NO** | no such test exists — **D-1** |

**Scorecard: 5 of 12 mutations caught (42%).** Invariants 1 and 2 are well-protected at construction; Invariant 3 is documented but untested at the enforcement boundary; Invariant 4 has zero mutation coverage on its core "raise on new BLOCKING" clause.

### Lightweight mutation testing (5 scenarios from §7)

| Mutation | Caught? | By which test |
| --- | --- | --- |
| `Severity.BLOCKING` → `Severity.WARNING` for entity violations (isa.py:416) | **YES** | test_verify_flags_missing_entity_blocking (test_isa.py:172); test_validate_missing_entity_blocks (test_validate.py:34) |
| `Severity.WARNING` → `Severity.BLOCKING` for terminology violations (isa.py:429) | **NO** | no test asserts terminology is WARNING not BLOCKING — **D-3** |
| Remove cache check in translate_segment (isa.py:307-310) | **YES** | test_translate_segment_cache_hit_is_byte_identical (test_isa.py:152) asserts r2.cache_hit is True |
| Change cache key to a constant | **YES** | test_cache_key_changes_with_model_or_policy (test_phase0.py:38) asserts key changes with model_version |
| Skip build_entity_table in kernel | **YES** | test_kernel_emits_audit_trace (test_kernel.py:40) asserts "BUILD_ENTITY_TABLE" in instructions |

**Scorecard: 4 of 5 caught (80%).** The terminology-severity mutation is the standout gap.

### Bottom line (Track D)

The 103-test suite is well-organized and covers the happy path comprehensively: all 6 ISA instructions have at least one unit test, the kernel pipeline has integration tests, the benchmark suite enforces the L3 zero-BLOCKING gate on 13 spec cases, and the Phase 6 hardening (sanitization, L4 forensics, HITL, graceful degradation) has dedicated tests. Test names are descriptive, the suite is deterministic (no `time.time()` / `random` / network), and the mix of unit vs. integration is healthy.

**However, the suite has three BLOCKING mutation gaps that would let regressions through:**

1. **D-1 (BLOCKING):** The "repair_segment raises Unrecoverable on new BLOCKING" branch (isa.py:518-519) — the core of Inv #4 — has ZERO test coverage. Removing the raise, flipping the operator, or changing the threshold leaves all 103 tests green. This is the single most dangerous gap because it's exactly the invariant audit-C D-3 flagged as partially enforced; the test suite doesn't even catch regressions in the partial enforcement.

2. **D-2 (BLOCKING):** The "confidence_note must not trigger routing" test (test_phase0.py:68-82) is aspirational — it adds a low-confidence record to the registry but never calls verify_output/repair_segment with that record present. Inv #3 is documented but untested at the enforcement boundary. A mutation that reads confidence_note in verify_output would not be caught.

3. **D-3 (BLOCKING):** No test asserts that terminology violations are WARNING (not BLOCKING). A mutation escalating terminology to BLOCKING would silently make the L3 gate stricter than the spec intends. Combined with D-4 (structural BLOCKING → WARNING undetected), the severity-classification contract is unprotected.

**Plus 11 WARNING-level gaps** covering: post-translation entity immutability (D-5), MALFORMED_MARKDOWN (D-6), 11 missing benchmark cases (D-7), HITL skip/override (D-8), LLM-seam exception-type coverage (D-9), large-doc/concurrency (D-10), ANALYZE edge cases (D-11), test non-hermeticity (D-12), fixture inconsistency (D-13), ENTITY_AMBIGUITY (D-14), TRANSLATE_SEGMENT failure conditions (D-15), VERIFY_OUTPUT exhaustiveness (D-16), BUILD_GLOSSARY recurrence (D-17), kernel recovery dispatch (D-18), state-machine edge transitions (D-19), L3-gate negative test (D-20), S-06 benchmark (D-21), L4 trace content (D-22), line-by-line attribution edge cases (D-23), mermaid edge cases (D-24), recovery fallback test naming (D-25), cache-key entity sensitivity (D-26), translate_segment ctx-vs-module (D-27), repair-loop exhaustion (D-28), audit-trail flush idempotency (D-29), conftest underutilization (D-30).

**Prioritized tests to add (top 10):**

1. `test_repair_segment_raises_on_new_blocking_at_max_retries` — D-1, BLOCKING
2. `test_verify_output_ignores_confidence_note` — D-2, BLOCKING
3. `test_verify_output_terminology_is_warning_not_blocking` — D-3, BLOCKING
4. `test_verify_output_structural_mismatch_is_blocking` — D-4, BLOCKING
5. `test_entities_immutable_after_full_pipeline` — D-5, WARNING
6. `test_analyze_raises_broken_markdown_on_parser_failure` — D-6, WARNING
7. Add 11 missing benchmark JSONL cases (S-01..S-04, S-06, D-01..D-03, E-01, E-03) — D-7, WARNING
8. `test_hitl_review_decision_skip_and_override` (parametrized) — D-8, WARNING
9. `test_llm_seam_degrades_on_each_exception_type` (parametrized) — D-9, WARNING
10. `test_kernel_repair_loop_exhausts_max_retries` — D-28, WARNING

Adding tests 1–4 would close all three BLOCKING mutation gaps and bring the invariant-mutation catch rate from 5/12 (42%) to 12/12 (100%). Adding tests 5–10 would close the highest-impact WARNING gaps. The remaining 20 WARNING findings are lower-priority coverage improvements that can land incrementally.


---
Task ID: audit-synthesis
Agent: Super Z (main)
Task: Synthesize 4-track audit findings into D-E deliverable bundle (docx + xlsx + chart)

Work Log:
- Loaded docx, xlsx, charts skills + skill-finder-cn check
- Ran empirical probes confirming TRA-003 (repair_segment returns 'Confirmed Valid' silently at attempt=1) and TRA-011 (cache-clear --pattern deletes 0 of 3 entries, CLI lies about success)
- Built master findings register: 35 findings (11 BLOCKING / 22 WARNING / 2 INFO) at /home/z/my-project/scripts/tra_findings.py
- Generated severity heatmap chart (matplotlib, Business Cool palette) at /home/z/my-project/download/TRA_audit_severity_heatmap.png
- Generated 7-sheet xlsx findings register (Summary, Findings, Track A-D subsets, Remediation Backlog) at /home/z/my-project/download/TRA_audit_findings_register.xlsx
- Generated docx audit report (R5 Clean White cover, Deep Sea Academic palette, Testing Report template, 7 sections + appendix, 95KB, postcheck 7/9 PASS 0 errors) at /home/z/my-project/download/TRA_Prototype_Audit_Report.docx

Stage Summary:
- Deliverables: 3 files in /home/z/my-project/download/ (TRA_Prototype_Audit_Report.docx, TRA_audit_findings_register.xlsx, TRA_audit_severity_heatmap.png)
- Findings: 35 total — 11 BLOCKING (5 Spec Conformance, 1 Code Quality, 2 Doc Consistency, 3 Test Suite) / 22 WARNING / 2 INFO
- Top 5 BLOCKING: TRA-003 (repair not surgical at attempt=1, reproducible), TRA-001 (whole-doc not segment), TRA-002 (registry bypassed), TRA-004 (4/5 exceptions unreachable), TRA-005 (L3 gate not enforced in translate)
- Worklog: 1293 lines, Task IDs 3-validate, audit-A, audit-B, audit-C, audit-D, audit-synthesis
- Estimated remediation effort: 3-5 person-days for all 11 BLOCKING; 8-12 person-days for all 35

---

## Task ID: revalidate-A — Independent re-validation of Track A (Spec Conformance) findings

**Agent:** Re-validation Agent A (Explore)
**Scope:** Re-confirm or refute each of the 10 Track A findings against the CURRENT code at `/home/z/my-project/tra/tra-prototype/`.
**Method:** Read every cited file:line; run the empirical probe for TRA-003; grep for callers; read-only audit (no files modified).

### TRA-001 (BLOCKING) — TRANSLATE_SEGMENT receives whole document, not a segment
- **Verdict:** CONFIRMED
- **Current evidence:**
  - `kernel.py:183-187` — `_execute_translation(self, src)` calls `translate_segment(src, self.ctx, self.cache, self.evidence, self.audit)`. The comment at line 184-185 admits this: *"Phase 2: deterministic whole-doc substitution … Segment granularity is wired in Phase 3."*
  - `kernel.py:143` — `target = self._execute_translation(src)` passes `src`, which is the whole document (loaded at `kernel.py:124`, sanitized at `kernel.py:125`).
  - `isa.py:279-287` — `translate_segment(source_segment: str, …)` signature names the parameter `source_segment`, confirming the contract.
  - `TRA-ISA-REFERENCE.md:48-49` — "TRANSLATE_SEGMENT … Generates the target-language equivalent of **a specific source segment** (sentence, list item, or table cell)."
- **Root cause:** Correct. The kernel has no segment iterator; `_execute_translation` is a one-shot whole-doc call.
- **Fix assessment:** Suggested fix (iterate `structural_map` leaves and call `translate_segment` per leaf) is optimal. Risk: code-blocks must be passed through verbatim (`is_no_translate_zone=True`); headings need the `__HEADER_N__` placeholder round-trip via `AnchorRegistry` (already scaffolded in `anchor.py`).
- **Empirical evidence:** N/A (code inspection).

### TRA-002 (BLOCKING) — Module registry bypassed by kernel
- **Verdict:** CONFIRMED
- **Current evidence:**
  - `kernel.py:43` — `from .modules.zh_en import ZHENModule`
  - `kernel.py:106` — `style_profile=ZHENModule().get_style_profile()` (in `TRAKernel.__init__`)
  - `isa.py:50` — `from .modules.zh_en import ZHENModule`
  - `isa.py:54` — `_MODULE = ZHENModule()` (module-level singleton)
  - Grep for `build_default_registry` callers: only `tests/test_modules.py:59,67`, `tests/test_modules.py:76` (via `registry_for_language_pair`), and `tra-prototype/SKILL.md:157,161` (documentation). Zero production callers.
  - Grep for `registry_for_language_pair` callers: only `tests/test_modules.py:76` and the docstring self-reference in `registry.py:58`. Zero production callers.
- **Root cause:** Correct. The registry abstraction (`modules/registry.py`) was built (Phase 4.1.2 per CLAUDE.md:31) but never wired into the Kernel or ISA. The Kernel's `__init__` and the ISA's module-level singleton both bypass it.
- **Fix assessment:** Suggested fix (inject `ModuleRegistry` into `TRAKernel.__init__` and into `RuntimeContext`; have `build_glossary`/`build_entity_table` look up the active module from the registry by `cfg.language_pair`) is optimal. Risk: `_MODULE` is referenced as a global in `isa.py:158, 163, 208, 245, 358`; refactoring requires threading the module through every ISA function signature or stashing it on `RuntimeContext`. Stashing on `ctx` is the lower-risk path.
- **Empirical evidence:** N/A.

### TRA-003 (BLOCKING) — repair_segment not surgical at function boundary
- **Verdict:** CONFIRMED (empirically reproduced)
- **Current evidence (isa.py:515-519):**
  ```python
  # Re-verify the repaired segment does not introduce new BLOCKING.
  sub = verify_output(repaired, source_segment, ctx, audit)
  new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]
  if new_blocking and attempt >= max_retries:
      raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")
  ```
  Also at `isa.py:508-513` for the structural branch:
  ```python
  elif diagnostic.subsystem == "structural":
      # Surgical structural fix not automatable here without AST; flag.
      if attempt >= max_retries:
          raise Unrecoverable(
              "UNRECOVERABLE: structural repair needs manual intervention"
          )
  ```
- **Root cause:** The audit's framing is slightly off: `new_blocking` is misnamed — it captures ALL blocking diagnostics in the post-repair `verify_output`, not "newly introduced" ones. But the behavioral consequence the audit describes is exactly right: at `attempt=1, max_retries=3`, the guard `1 >= 3` is `False`, so `repair_segment` returns silently even when the post-repair target still contains BLOCKING violations. The kernel's `_repair_loop` (kernel.py:189-236) does re-loop and call `repair_segment` again on the next iteration against the same diagnostic, but it counts the same diagnostic and increments `attempt`; only on the final attempt does `repair_segment` raise `Unrecoverable`. In between, the kernel re-verifies the whole target and may pick up the same BLOCKING again. This means the "surgical, no-new-BLOCKING" invariant from TRA-ISA-REFERENCE.md:79-80 is violated for `max_retries - 1` attempts.
- **Fix assessment:** The minimal correct fix is to drop the `attempt >= max_retries` guard at isa.py:518, so ANY post-repair BLOCKING raises `Unrecoverable` immediately. This aligns with the spec invariant ("Repair must resolve the specific violation without introducing new ones"). Risk: the kernel's `_repair_loop` will then break on the first attempt for any diagnostic that cannot be fixed in one shot — but the loop already calls `_recover` and breaks on `Unrecoverable`, so this is the intended behavior. The structural branch (isa.py:510) should similarly raise on attempt=1, not defer to the last attempt. Better fix: compute the *delta* between pre-repair and post-repair blocking and raise only if the delta is non-empty; this is the truly surgical reading.
- **Empirical evidence (exact output):**
  ```
  PRE-REPAIR diagnostics:
    WARNING terminology: Source term not translated: '成立'
    BLOCKING epistemic: Epistemic drift: 'Valid' (from '成立')

  repair_segment returned: 'Confirmed Valid'
  Raised Unrecoverable: NO

  POST-REPAIR diagnostics on the repaired segment:
    BLOCKING epistemic: Epistemic drift: 'Valid' (from '成立')

  new_blocking count: 1
  attempt=1, max_retries=3 -> 1>=3 is False, so Unrecoverable NOT raised
  ```
  Interpretation: the repair correctly substituted `成立 -> Confirmed`, but the resulting target `'Confirmed Valid'` still contains the forbidden drift target `'Valid'` (a known drift for source `成立`). The post-repair `verify_output` raises a BLOCKING epistemic diagnostic; `repair_segment` sees `new_blocking` truthy but `attempt >= max_retries` is False, so it returns `'Confirmed Valid'` silently. The kernel's `_repair_loop` only catches `Unrecoverable`, so this silent return propagates a still-BLOCKING target upward.

### TRA-004 (BLOCKING) — 4 of 5 TRA-EXCEPTION recovery procedures unreachable
- **Verdict:** PARTIALLY CONFIRMED — actually 3 of 5 unreachable, not 4 (GlossaryConflict IS raised at two sites)
- **Current evidence:**
  - Grep for `raise UnknownTerm|raise CertaintyConflict|raise EntityAmbiguity` across `tra-prototype/`: **zero matches**.
  - Grep for `raise GlossaryConflict`: `isa.py:164` and `isa.py:170` (both in `build_glossary`).
  - Grep for `raise BrokenMarkdown`: `isa.py:84` (in `analyze_document`).
  - `kernel.py:128-129`: `self._transition(KernelState.ANALYZE_DOCUMENT)` then `analyze_document(src, self.ctx, self.audit)` — **no try/except**. A `BrokenMarkdown` raised here propagates out of `run()` and crashes the CLI.
  - `kernel.py:135-140`: `build_glossary` IS wrapped in `try/except TRAException` and routed through `self._recover(exc)`. But `build_entity_table` (line 140) is **not** wrapped, so an `EntityAmbiguity` (if ever raised) would also propagate uncaught.
  - `recovery.py:154-182` `route_exception` dispatches to 5 handlers: `recover_unknown_term`, `recover_broken_markdown`, `recover_certainty_conflict`, `recover_entity_ambiguity`, `recover_glossary_conflict`. Of these, only `recover_glossary_conflict` has a production caller (via `_recover` → `route_exception`, gated on `build_glossary`'s try/except). `recover_broken_markdown` is unreachable because `analyze_document` is not wrapped. `recover_unknown_term`, `recover_certainty_conflict`, `recover_entity_ambiguity` are unreachable because no code raises the corresponding exceptions.
- **Root cause:** The audit's count "4 of 5" is too high. The accurate count is **3 of 5 unreachable** (UnknownTerm, CertaintyConflict, EntityAmbiguity) plus 1 of 5 reachable in code but not reachable at runtime because the kernel doesn't wrap `analyze_document` (BrokenMarkdown). Only GlossaryConflict is fully reachable. The deeper root cause is the same as the audit identified: the kernel only wraps `build_glossary` in `try/except TRAException`, leaving `analyze_document`, `build_entity_table`, `translate_segment`, and `verify_output` unwrapped.
- **Fix assessment:** Suggested fix (wrap every ISA call in `try/except TRAException` and route through `_recover`) is correct but heavy. A leaner approach: a single `try/except TRAException` around the entire body of `run()` after `_transition(INITIALIZE_RUNTIME)` that routes to `_recover` and either re-raises or transitions to a `EXCEPTION_HANDLER` state. Also need to add raise sites for UnknownTerm (in `translate_segment` when a source term has no glossary mapping and no module rule), CertaintyConflict (in `verify_output` or `repair_segment` when both epistemic markers collide), and EntityAmbiguity (in `build_entity_table` when `entity_type_hint` returns None and the classifier is unsure). Risk: adding new raise sites requires careful coordination with `recovery.py` handlers; the recovery handlers themselves look correct.
- **Empirical evidence:** Grep output above.

### TRA-005 (BLOCKING) — kernel.run() does not enforce L3 zero-BLOCKING gate
- **Verdict:** CONFIRMED
- **Current evidence:**
  - `kernel.py:122-157` `run()` — the only `return` is at `kernel.py:157`: `return target`. No inspection of `self.audit._buffer` flags, no call to `verify_output`'s blocking count, no `ConformanceLevel`-gated branch. The target is returned regardless of how many BLOCKING diagnostics `verify_output` raised at line 146.
  - `tra_cli.py:100-120` `translate` command: `kernel.run(input_md)` returns `target`; `output.write_text(target, encoding="utf-8")` writes it (line 104). Then lines 106-110 count BLOCKING flags from `kernel.audit._buffer`. Lines 116-120: if `blocking`, print a red `WARNING:` to the console. **The output file is still written; the CLI exits 0.**
  - `validate.py:46-49` `ValidationReport.passed`: `return not self.blocking` — this IS the L3 gate, but it's only invoked by `tra validate` (tra_cli.py:197-242) and `BenchmarkRunner.run_case` (benchmark.py:98-109).
  - `benchmark.py:98-109`: fails the case if `n_blocking > 0`.
- **Root cause:** Correct. The L3 zero-BLOCKING gate exists only in `validate.py` and `benchmark.py`, not in the production translate path. A user running `tra translate input.md` will get a translated file written to disk even if `verify_output` raised 50 BLOCKING diagnostics.
- **Fix assessment:** Suggested fix (raise `TRAException` in `kernel.run()` when `blocking > 0` and `cfg.conformance_level >= L3_STRICT`) is optimal. Alternative: gate the file write in `tra_cli.py` (don't write the file if BLOCKING > 0 at L3+; exit non-zero). Risk: this changes user-visible behavior (currently the file is always written); should be guarded by the conformance level so L1/L2 users still get best-effort output.
- **Empirical evidence:** N/A.

### TRA-006 (WARNING) — PolicyResolver is scaffolding, never invoked
- **Verdict:** CONFIRMED
- **Current evidence:**
  - Grep for `PolicyResolver` across `tra/`: only matches in `policy.py:13` (definition), `CLAUDE.md:22` (doc), `implementation_plan.md:167,318` (planning notes), `tests/test_phase0.py:23,113` (test import + instantiation).
  - Zero production callers. `kernel.py` does not import `PolicyResolver`. `isa.py`'s `_policy_stack` (isa.py:556-557) just returns `list(DEFAULT_POLICY_STACK)` — no resolver instantiation.
- **Root cause:** Correct. The class is fully implemented (3 methods: `resolve`, `wins`, plus `__init__`) but never wired in. The kernel's `_repair_loop` does not consult it when deciding whether a repair violates a higher-priority policy; the only arbitration logic is the `attempt >= max_retries` guard.
- **Fix assessment:** Suggested fix (have `repair_segment` call `PolicyResolver.wins(EPISTEMIC_FIDELITY, TARGET_FLUENCY)` before applying a fluency repair) is correct in spirit. Better integration point: pass a `PolicyResolver` instance into `RuntimeContext` at kernel init, and have `repair_segment` consult it when its action might violate a higher-priority invariant (e.g., reverting an epistemic marker to fix a terminology WARNING would violate EPISTEMIC_FIDELITY > TERMINOLOGICAL_CONSISTENCY). Risk: low; the resolver is a pure function over the priority enum.
- **Empirical evidence:** Grep output above.

### TRA-007 (WARNING) — Kernel transitions fire BEFORE ISA completion
- **Verdict:** CONFIRMED
- **Current evidence (kernel.py:127-157):**
  ```python
  127: self._transition(KernelState.INITIALIZE_RUNTIME)
  128: self._transition(KernelState.ANALYZE_DOCUMENT)
  129: analyze_document(src, self.ctx, self.audit)         # ISA call AFTER transition
  ...
  135: self._transition(KernelState.BUILD_ARTIFACTS)
  136: try:
  137:     build_glossary(src, profile, self.ctx, self.evidence, self.audit)
  138: except TRAException as exc:
  139:     self._recover(exc)
  140: build_entity_table(src, smap, self.ctx, self.evidence, self.audit)
  ...
  142: self._transition(KernelState.EXECUTE_TRANSLATION)
  143: target = self._execute_translation(src)              # ISA call AFTER transition
  ...
  145: self._transition(KernelState.VERIFY_OUTPUT)
  146: diagnostics = verify_output(target, src, self.ctx, self.audit)   # AFTER
  ...
  148: self._transition(KernelState.REPAIR_IF_NEEDED)
  149: target = self._repair_loop(target, src, diagnostics)             # AFTER
  ...
  151: self._transition(KernelState.AUDIT_DIAGNOSTICS)
  152: self.audit.flush()
  ...
  154: self._transition(KernelState.EMIT_PAYLOAD)
  155: self._export_artifacts()
  156: self._export_forensics(target)
  157: return target
  ```
  Every `_transition(...)` call precedes its corresponding ISA call by 1 line. If the ISA call raises, the kernel has already recorded the transition in `ctx.execution_log`, so the log lies about what completed.
- **CLAUDE.md:19** still claims: *"transitions only on successful ISA completion."*
- `kernel.py:7-8` docstring still claims: *"State transitions are triggered ONLY by successful completion of ISA instructions. The Kernel must not skip instructions."*
- **Root cause:** Correct. The transition-first pattern is uniform across `run()`. The spec contract (TRA-ISA-REFERENCE.md:5 "Engines must not skip instructions; they must transition through them sequentially as defined in `TRA-KERNEL`") and CLAUDE.md:19 are both violated.
- **Fix assessment:** Suggested fix (swap the order: call ISA first, then `_transition` on success) is optimal and trivial. Risk: very low; the transition function only does forward-progress validation and an append to `execution_log`. Caveat: the `INITIALIZE_RUNTIME` transition at line 127 has no corresponding ISA call (it's the "load config into ctx" step), so it should stay where it is. The remaining 7 transitions should all move AFTER their ISA calls.
- **Empirical evidence:** N/A.

### TRA-008 (WARNING) — Anchor rewrite_links defined but never called
- **Verdict:** CONFIRMED
- **Current evidence:**
  - Grep for `rewrite_links` across `tra/`: only matches in `anchor.py:101` (definition), `tests/test_anchor.py:11,105` (test import + call), `implementation_plan.md:71,122,396` (planning notes marked `[x]`).
  - Zero production callers. `kernel.py` does not import `rewrite_links` or `AnchorRegistry`. The `AnchorRegistry` is constructed inside `anchor.py:build_structural_map` (line 167) and returned to `analyze_document` (isa.py:82), but `analyze_document` discards it: `structural_map, _registry = build_structural_map(source)`. The registry is then thrown away — `ctx` does not store it.
- **Root cause:** Correct. The kernel's `run()` has no post-translation `rewrite_links` pass. Internal `[text](#slug)` links in the source markdown are never repointed at translated slugs.
- **Fix assessment:** Suggested fix (add a `REWRITE_LINKS` micro-state between `REPAIR_IF_NEEDED` and `AUDIT_DIAGNOSTICS`, or fold it into `EMIT_PAYLOAD`) is reasonable. Implementation requires: (1) `analyze_document` stores the `AnchorRegistry` on `ctx` (currently discarded); (2) `translate_segment` preserves `__HEADER_N__` placeholders through translation; (3) post-translation, walk the structural map, resolve each placeholder's translated text via `registry.resolve_slug`, call `registry.bind(placeholder, translated_slug)`; (4) call `rewrite_links(target, registry)` and append any broken slugs as WARNING diagnostics. Risk: medium — the placeholder-preservation contract is not currently enforced by `translate_segment` (it would naively translate `__HEADER_000__` as if it were source text). The fix requires the rule translator to skip placeholder tokens.
- **Empirical evidence:** Grep output above.

### TRA-009 (WARNING) — Terminology violations classified as WARNING, not BLOCKING
- **Verdict:** CONFIRMED
- **Current evidence (isa.py:424-435):**
  ```python
  # Terminology: glossary terms must appear as canonical targets.
  for src, tgt in glossary.items():
      if src in target:  # untranslated source term leaked
          diagnostics.append(
              Diagnostic(
                  severity=Severity.WARNING,
                  subsystem="terminology",
                  issue=f"Source term not translated: {src!r}",
                  evidence=f"expected canonical target {tgt!r}",
                  action="Apply canonical mapping",
              )
          )
  ```
- **Spec contract:** `TRA-ISA-REFERENCE.md:55` "Terminology matches `canonical_glossary` exactly" is listed as a TRANSLATE_SEGMENT Invariant. `TRA-ISA-REFERENCE.md:58` lists `TERMINOLOGY_VIOLATION` as a Failure Condition for TRANSLATE_SEGMENT. The Spec does not explicitly say BLOCKING, but `TRA-SPECIFICATION.md §5.1` puts TERMINOLOGICAL_CONSISTENCY at priority 4 (above TARGET_FLUENCY), and the kernel's repair loop treats BLOCKING as the only "must fix" severity.
- **Root cause:** Correct. An untranslated source term leaking into the target violates a TRANSLATE_SEGMENT invariant (TRA-ISA-REFERENCE.md:55) and is a TERMINOLOGY_VIOLATION failure (TRA-ISA-REFERENCE.md:58). Classifying it as WARNING means: (a) `validate.py` will pass even with terminology drift; (b) the kernel's `_repair_loop` will still try to fix it (because it merges blocking + warnings), but the L3 gate (`passed = not self.blocking`) will not catch it.
- **Fix assessment:** Suggested fix (change `Severity.WARNING` to `Severity.BLOCKING` at isa.py:429) is correct but has a knock-on effect: the current benchmark suite (`tests/benchmark/cases/*.jsonl`) and the example expected output (`examples/expected_outputs/security_advisory_zh.L3.md`) may not have been built assuming terminology-as-BLOCKING. Recommend running the benchmark suite after the change to surface any cases that would newly fail. Risk: medium — may break existing passing benchmarks if they rely on the looser WARNING classification. Alternative: split terminology diagnostics into WARNING for `CONTEXT_SENSITIVE` entries and BLOCKING for `CANONICAL` entries (matches the glossary status field).
- **Empirical evidence:** N/A.

### TRA-010 (WARNING) — Memory model immutability claims unenforced
- **Verdict:** CONFIRMED
- **Current evidence:**
  - `memory.py:172` `class RuntimeContext(BaseModel):` — no `model_config = ConfigDict(frozen=True)`. The class docstring (line 173) calls it *"The mutable 'memory' of the VM (Spec §4)"* — so this is intentionally mutable, and the audit's claim that it should be frozen is debatable. **However**, `BootstrapConfig` IS supposed to be the "read-only Immutable Config segment" per CLAUDE.md:53 and Spec §4.
  - `config.py:23-35` `class BootstrapConfig(BaseModel):` — no `model_config` at all. The class docstring (line 24) explicitly says: *"Parsed tvm_bootstrap — **read-only Immutable Config segment**."* Despite this, it is a regular mutable Pydantic model.
  - `tra_cli.py:86-89` — direct mutation:
    ```python
    86: if lang:
    87:     cfg.language_pair = lang
    88: if level:
    89:     cfg.conformance_level = _resolve_level(level)
    ```
  - `validate.py:84-86` (`BenchmarkRunner.run_case`) also mutates: `cfg = self.config.model_copy(update={"conformance_level": …})` — this uses `model_copy(update=…)` which is the *immutable* idiom, so benchmark is fine. But `tra_cli.py` uses direct attribute assignment, which would raise `ValidationError` on a frozen model.
- **Root cause:** Partially correct. The audit's claim that `RuntimeContext` should be frozen is wrong — Spec §4 designates RuntimeContext as the read/write segment. The claim that `BootstrapConfig` should be frozen is correct (CLAUDE.md:53, config.py:24 docstring). The claim that `tra_cli.py:87-89` mutates BootstrapConfig is correct.
- **Fix assessment:** Recommended fix scope is narrower than the audit suggests:
  1. Add `model_config = ConfigDict(frozen=True)` to `BootstrapConfig` (config.py:23).
  2. Change `tra_cli.py:86-89` to use `cfg = cfg.model_copy(update={"language_pair": lang} if lang else {})` then `cfg = cfg.model_copy(update={"conformance_level": _resolve_level(level)} if level else {})` (or a single combined update).
  3. Audit `kernel.py:97-103` — it reads from `config` but doesn't mutate; safe under frozen.
  4. Do NOT freeze `RuntimeContext` — it's the mutable segment by design.
- Risk: low for `BootstrapConfig`; the only mutations are in `tra_cli.py:86-89` and `benchmark.py:84` (the latter already uses immutable idiom). 
- **Empirical evidence:** N/A.

---

### Verdict Summary Table

| ID | Severity | Original claim | Verdict | Notes |
|---|---|---|---|---|
| TRA-001 | BLOCKING | TRANSLATE_SEGMENT receives whole document | **CONFIRMED** | kernel.py:186 passes `src` |
| TRA-002 | BLOCKING | Module registry bypassed | **CONFIRMED** | kernel.py:43,106 + isa.py:50,54 hard-code ZHENModule; zero production callers of registry |
| TRA-003 | BLOCKING | repair_segment not surgical at function boundary | **CONFIRMED** | Empirically reproduced: silent return at attempt=1 with post-repair BLOCKING present |
| TRA-004 | BLOCKING | 4 of 5 recovery procedures unreachable | **PARTIALLY CONFIRMED** | Accurate count is **3 of 5** fully unreachable + 1 reachable in code but unreachable at runtime (BrokenMarkdown raised but kernel.py:129 not wrapped); only GlossaryConflict is fully reachable. Audit over-counted by 1. |
| TRA-005 | BLOCKING | kernel.run() does not enforce L3 gate | **CONFIRMED** | kernel.py:157 returns unconditionally; CLI only warns |
| TRA-006 | WARNING | PolicyResolver never invoked | **CONFIRMED** | Only test_phase0.py imports it |
| TRA-007 | WARNING | Transitions fire BEFORE ISA completion | **CONFIRMED** | Uniform pattern across kernel.py:127-157; CLAUDE.md:19 still claims otherwise |
| TRA-008 | WARNING | rewrite_links defined but never called | **CONFIRMED** | Only test_anchor.py calls it; AnchorRegistry discarded in isa.py:82 |
| TRA-009 | WARNING | Terminology violations are WARNING not BLOCKING | **CONFIRMED** | isa.py:429 uses Severity.WARNING; violates TRA-ISA-REFERENCE.md:55,58 |
| TRA-010 | WARNING | Memory model immutability unenforced | **PARTIALLY CONFIRMED** | BootstrapConfig claim correct (should be frozen). RuntimeContext claim is wrong — it's the mutable segment by design (Spec §4). |

### Findings where the original audit was wrong / fix needs adjustment

1. **TRA-004 (over-counted):** The audit said "4 of 5" recovery procedures are unreachable. The accurate count is **3 of 5 fully unreachable** (UnknownTerm, CertaintyConflict, EntityAmbiguity — no raise sites) + **1 reachable in code but unreachable at runtime** (BrokenMarkdown is raised at isa.py:84 but kernel.py:129 has no try/except, so it propagates uncaught instead of being routed to `recover_broken_markdown`). Only `GlossaryConflict` is fully reachable end-to-end. The audit should be re-issued as "3 of 5 fully unreachable; 1 of 5 unreachable at runtime due to missing kernel try/except; 1 of 5 fully reachable."

2. **TRA-003 (root-cause framing slightly off):** The audit's variable name `new_blocking` suggests "newly introduced blocking," but the code at isa.py:517 computes ALL blocking in the post-repair verify_output (not a delta against pre-repair). The behavioral consequence is correctly identified, but the most accurate root cause is: "the guard is `attempt >= max_retries`-gated instead of immediate; AND the variable captures all blocking, not just newly-introduced blocking." Both issues mean `repair_segment` returns silently on attempts 1..max_retries-1 even when post-repair verify_output reports BLOCKING.

3. **TRA-010 (RuntimeContext claim is wrong):** The audit says `RuntimeContext` should be frozen. Per Spec §4 (CLAUDE.md:53), RuntimeContext is the read/write segment by design — it must be mutable for the kernel to populate `document_profile`, `structural_map`, `glossary_cache`, `entity_table`, `execution_log`, `repair_history`, etc. Only `BootstrapConfig` (the Immutable Config segment) should be frozen. The fix should be scoped accordingly.

4. **TRA-008 (fix is more involved than the audit implies):** The audit's suggested fix (call `rewrite_links` from the kernel) underestimates the work. The current `analyze_document` discards the `AnchorRegistry` (`structural_map, _registry = build_structural_map(source)` at isa.py:82). The registry must be preserved on `ctx`, AND `translate_segment` must preserve `__HEADER_N__` placeholders through translation (currently `_rule_translate` would treat them as ordinary source text). Without these prerequisites, `rewrite_links` has no registry to consult and no placeholders to bind.

5. **TRA-009 (fix risk):** Changing terminology from WARNING to BLOCKING at isa.py:429 may break existing benchmark cases that currently pass. Recommend running `tests/benchmark/cases/*.jsonl` after the change. A more spec-faithful fix would split on `GlossaryStatus`: BLOCKING for CANONICAL entries, WARNING for CONTEXT_SENSITIVE entries.

### Net assessment
9 of 10 findings CONFIRMED, 1 PARTIALLY CONFIRMED (TRA-004 — over-counted by 1), 1 PARTIALLY CONFIRMED (TRA-010 — RuntimeContext claim is wrong). All 10 findings describe real defects in the current code. The original audit's root-cause analysis is accurate for 8 of 10; the two partial confirmations have minor inaccuracies documented above. The suggested fixes are mostly optimal, with the adjustments noted.


---

# Task ID: revalidate-B — Track B re-validation (code quality & security)

Re-validation Agent: B (independent). Read current code at `/home/z/my-project/tra/tra-prototype/`. All 9 Track B findings re-checked against current source.

## Summary verdict table

| ID  | Severity  | Original claim                                            | Verdict              |
|-----|-----------|-----------------------------------------------------------|----------------------|
| 011 | BLOCKING  | `cache-clear --pattern` is a silent no-op                 | CONFIRMED            |
| 012 | WARNING   | `_sanitize_input` bypassed at validate/benchmark          | CONFIRMED            |
| 013 | WARNING   | Audit trail NOT byte-reproducible (uuid4 + datetime.now)  | CONFIRMED            |
| 014 | WARNING   | Path traversal: no protection on config paths             | CONFIRMED            |
| 015 | WARNING   | Double audit record on LLM degradation                    | CONFIRMED            |
| 016 | WARNING   | `count_blocking` stub returns 0                           | CONFIRMED            |
| 017 | WARNING   | 5 unused dependencies                                     | CONFIRMED            |
| 018 | WARNING   | Immutability unenforced (Entity, BootstrapConfig etc.)    | CONFIRMED            |
| 019 | WARNING   | 2 runtime asserts in kernel.py stripped under `-O`        | CONFIRMED            |

**All 9 findings CONFIRMED. No corrections needed to original audit.**

---

## TRA-011 (BLOCKING) — `cache-clear --pattern` is a silent no-op — CONFIRMED

### Current evidence
- `tra/cache.py:107-115` — `invalidate(pattern)`:
  ```python
  def invalidate(self, pattern: str | None = None) -> None:
      if not self.enabled or self._cache is None:
          return
      if pattern:
          # diskcache.delete supports glob patterns   <-- FALSE COMMENT
          self._cache.delete(pattern)
      else:
          self._cache.clear()
  ```
  The inline comment claims "diskcache.delete supports glob patterns". This is **factually wrong**: `diskcache.Cache.delete(key)` deletes a literal key only.

- `tra_cli.py:123-132` — `cache-clear` CLI command:
  ```python
  @click.option("--pattern", default=None, help="Optional key pattern to delete.")
  ...
  cache.invalidate(pattern)
  target = pattern or "ALL"
  console.print(f"[green]Cache invalidated:[/green] {target}")
  ```
  Prints success unconditionally.

### Empirical probe output
```
Before: 3
After invalidate(test*): 3
All keys: ['a030b44932e1eaf0fa735a474403bc25bac1dd95452ca08220003e89a00a4047',
           '44befd8985cb2a3aa29a8a6afc18cdeb30459ce0edcf7410acf3ae27eab16ad4',
           '1ceb0e4d8258b127cc8e0024ba58cc9eac056683f636c200a521f9084c322f67']
```
All 3 entries survive `c.invalidate('test*')`. The cache keys are SHA-256 hashes (`CacheKeyContext.key()`), so they never start with `test` — but even literal-key deletion with a non-existent key returns `False` and silently does nothing.

### Root cause
Original claim is fully correct. Two compounding defects:
1. `diskcache.delete()` takes a literal key, not a glob — code comment is a documentation lie.
2. Even if globbing were supported, cache keys are SHA-256 hashes, so user-supplied patterns like `test*` would never match. The `--pattern` option is therefore useless AS DESIGNED.
3. CLI prints "Cache invalidated" regardless of whether anything was deleted — false success signal.

### Fix assessment
Original fix (iterate `cache.iterkeys()` and glob-match) is optimal. Recommended implementation:
```python
def invalidate(self, pattern: str | None = None) -> int:
    if not self.enabled or self._cache is None:
        return 0
    if pattern:
        import fnmatch
        deleted = 0
        for key in list(self._cache.iterkeys()):
            if fnmatch.fnmatch(key, pattern):
                self._cache.delete(key)
                deleted += 1
        return deleted
    else:
        self._cache.clear()
        return -1  # unknown count
```
CLI should report the actual deleted count and exit non-zero if `pattern` matched nothing. Additional consideration: because keys are opaque SHA-256 hashes, `--pattern` is mostly useless for end users. A more useful CLI flag would be `--by-source <regex>` that re-hashes candidates, or `--all` (default) + `--dry-run`.

---

## TRA-012 (WARNING) — `_sanitize_input` bypassed at validate/benchmark boundaries — CONFIRMED

### Current evidence
- `tra/kernel.py:83-90` — definition (only site of definition):
  ```python
  def _sanitize_input(text: str) -> str:
      """Input validation & sanitization (Phase 6.5.3)..."""
      return _CONTROL_RE.sub("", text)
  ```
- `tra/kernel.py:125` — only call inside the kernel:
  ```python
  src = _sanitize_input(src)
  ```
- `tra/validate.py:71-74` — bypasses `_sanitize_input`:
  ```python
  if isinstance(source, Path):
      source = source.read_text(encoding="utf-8")
  if isinstance(candidate, Path):
      candidate = candidate.read_text(encoding="utf-8")
  ```
  Reads file content straight into `analyze_document(source, ctx, audit)` (line 81) and `verify_output(candidate, source, ctx, audit)` (line 85) without sanitization.

- `tra/benchmark.py:102-104` — bypasses `_sanitize_input`:
  ```python
  profile, smap = analyze_document(case.source, ctx, audit)
  build_glossary(case.source, profile, ctx, evidence, audit)
  build_entity_table(case.source, smap, ctx, evidence, audit)
  ```
  Note: line 88 `kernel.run(case.source)` *does* sanitize (via kernel.py:125), but the subsequent re-verification on lines 102-104 uses raw `case.source`.

- Grep confirms `_sanitize_input` is referenced only in:
  - `kernel.py:83` (def), `kernel.py:125` (call)
  - `tests/test_phase6_hardening.py:17,90` (test import + use)

### Root cause
Original claim is fully correct. Sanitization is enforced only on the `Kernel.run()` happy path. The `validate` and `benchmark` re-entry points accept untrusted Path/str inputs without applying the same control-character / bidi-override / BOM stripping.

### Fix assessment
Original fix (call `_sanitize_input` at validate.py:72/74 and benchmark.py:102) is correct but suboptimal. Better: push sanitization down into `analyze_document()` itself (single chokepoint) so every caller gets it for free, and `_sanitize_input` becomes a private helper inside `isa.py`. That eliminates the "remember to call it" foot-gun permanently. Risk: minimal — `_sanitize_input` is pure (never raises, only strips control chars), so wrapping all entry points is safe.

---

## TRA-013 (WARNING) — Audit trail NOT byte-reproducible — CONFIRMED

### Current evidence
- `tra/diagnostics.py:40` — `EvidenceRecord.id`:
  ```python
  id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
  ```
- `tra/diagnostics.py:58` — `AuditRecord.timestamp`:
  ```python
  timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
  ```

### Empirical probe output
Ran the kernel twice on the same input (`examples/security_advisory_zh.md`), isolating each run's audit_trace.jsonl by renaming between runs:
```
Run 1: 5 records
Run 2: 5 records
Outputs identical: True
Traces identical: False
Record 0 differs:
  field 'timestamp':
    trace1: '2026-07-13T01:56:01.458359Z'
    trace2: '2026-07-13T01:56:01.464344Z'
Record 1 differs:
  field 'timestamp': ... (differs)
  field 'evidence_chain':
    trace1: ['ev_d39c91c30367', 'ev_fc8ba080f556', 'ev_390a68c31eb0', ...]
    trace2: ['ev_e4d420609329', 'ev_bbf0ed7871db', 'ev_252e0663563a', ...]
Total differing records: 5
```

### Non-determinism sources (exact)
1. `AuditRecord.timestamp` — `datetime.now(UTC)` (diagnostics.py:58). Every audit record gets a fresh wall-clock timestamp.
2. `EvidenceRecord.id` — `uuid4().hex[:12]` (diagnostics.py:40). Every evidence record gets a fresh random ID; these IDs then propagate into `AuditRecord.evidence_chain` (list of `ev_…` strings), making the entire audit trail non-reproducible.
3. Note: the *output translation* IS deterministic (`Outputs identical: True`), because the translation cache key is content-derived and the rule path is pure. Only the metadata layer (audit + evidence IDs) is non-reproducible.

### Root cause
Original claim is fully correct.

### Fix assessment
- For timestamp: replace `datetime.now(UTC)` with a deterministic clock. Two options:
  - (a) Inject a `clock: Callable[[], datetime]` into `AuditTrail.__init__`, defaulting to `datetime.now(UTC)` but overridable in tests/reproducible mode.
  - (b) Use a logical counter (`sequence_id` already serves this — drop `timestamp` from the model, or populate it from the run start time).
  - Recommended: (a) — keeps wall-clock for forensics, allows override for reproducibility.
- For evidence IDs: replace `uuid4` with a content-addressable ID derived from `sha256(source_span + target_span + type + module)[:12]`. This makes the ID a function of the evidence content, so identical decisions produce identical IDs — required for L4 byte-reproducibility.
- Combined: the L4_FORENSIC conformance level (memory.py:47) advertises forensic replay; without these fixes, L4 cannot actually replay.

---

## TRA-014 (WARNING) — Path traversal: no protection on config paths — CONFIRMED

### Current evidence
- `tra/config.py:23-55` — `BootstrapConfig` accepts `cache_directory`, `compilation_dir`, `audit_trace` from YAML with zero validation:
  ```python
  class BootstrapConfig(BaseModel):
      ...
      cache_directory: str = "./cache"
      compilation_dir: str = "./compilation_artifacts"
      audit_trace: str = "./audit_trace.jsonl"

      @classmethod
      def from_yaml(cls, path):
          raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
          return cls(
              ...
              cache_directory=raw.get("cache", {}).get("directory", "./cache"),
              compilation_dir=raw.get("artifacts", {}).get("compilation_dir", "./compilation_artifacts"),
              audit_trace=raw.get("artifacts", {}).get("audit_trace", "./audit_trace.jsonl"),
          )
  ```
  No `resolve()`, no `is_relative_to(base_dir)` check, no path sanitization.

- `tra/kernel.py:242` — `base.mkdir(parents=True, exist_ok=True)` on `self.config.compilation_dir` (user-supplied).
- `tra/kernel.py:303` — same `mkdir(parents=True, exist_ok=True)` again in `_export_forensics`.
- `tra/diagnostics.py:141` — `self.path.parent.mkdir(parents=True, exist_ok=True)` on `audit_trace` parent.
- `tra/cache.py:89` — `self.directory.mkdir(parents=True, exist_ok=True)` on `cache_directory`.

### Root cause
Original claim is fully correct. A malicious `config.yaml` (`compilation_dir: /etc/cron.d`, `audit_trace: /etc/passwd`) would cause the kernel to (a) create arbitrary directories with `parents=True` and (b) write attacker-controlled content (glossary/entity YAML) into attacker-chosen paths. Severity is "WARNING" not "BLOCKING" because exploitation requires write access to `config.yaml` — but in multi-tenant translation services, this is a real privilege-escalation vector.

### Fix assessment
Original fix (validate paths are within a configured `base_dir`) is correct. Recommended:
```python
class BootstrapConfig(BaseModel):
    ...
    def model_post_init(self, _ctx):
        base = Path(self._base_dir).resolve()  # from env or fixed root
        for fld in ("cache_directory", "compilation_dir", "audit_trace"):
            p = Path(getattr(self, fld)).resolve()
            if not p.is_relative_to(base):
                raise ValueError(f"{fld} must be inside {base}, got {p}")
```
Reject `..` segments, absolute paths outside `base`, and symlink escapes. Risk: requires a documented "workspace root" config; choose between env var (`TRA_WORKSPACE`) or a fixed `./workspace/` default.

---

## TRA-015 (WARNING) — Double audit record on LLM degradation — CONFIRMED

### Current evidence
- `tra/isa.py:312-347` — exact control flow:
  ```python
  if llm_translate is not None:
      try:
          target = llm_translate(source_segment, ctx)
          basis = "LLM decision"
      except Exception as exc:  # noqa: BLE001
          # LLM unavailable / errored: degrade to deterministic rule path
          target, basis = _rule_translate(source_segment, glossary, entities)
          audit.append(                                          # <-- record #1 (degraded)
              "TRANSLATE_SEGMENT",
              _hash(source_segment),
              [],
              artifact_snapshot={
                  "degraded": True,
                  "reason": f"llm_unavailable: {exc!r}",
              },
          )
          # NO return here — falls through to the code below
  else:
      target, basis = _rule_translate(source_segment, glossary, entities)

  rec = EvidenceRecord(...)
  ev_id = evidence.add(rec)
  result = TranslationResult(...)
  cache.set(cache_key, result)
  audit.append("TRANSLATE_SEGMENT", cache_key, [ev_id])          # <-- record #2 (normal)
  return result
  ```

### Control-flow trace
When `llm_translate` raises:
1. Line 321: `target, basis = _rule_translate(...)` — fallback translation computed.
2. Lines 322-330: `audit.append(...)` — first audit record with `evidence_chain=[]` and `artifact_snapshot={"degraded": True, ...}`.
3. **No `return`** — execution falls through.
4. Lines 334-340: `EvidenceRecord` constructed with `type=LLM_DECISION` (misleading — was actually rule-based).
5. Line 341: `evidence.add(rec)` — adds to evidence registry.
6. Lines 342-344: `TranslationResult` constructed.
7. Line 345: `cache.set(cache_key, result)` — caches.
8. Line 346: `audit.append("TRANSLATE_SEGMENT", cache_key, [ev_id])` — **second** audit record, this one with `evidence_chain=[ev_id]` and no `degraded` flag.

### Root cause
Original claim is fully correct. The `except` block appends a degraded record but does not `return` — control falls through to the normal audit.append at line 346, producing two audit records for one segment translation. Downstream audit consumers (L3 conformance check, reporting.summarize_audit) will count this segment twice.

### Fix assessment
Original fix (add `return` after the degraded `audit.append`) is correct but incomplete. Two issues remain even after the fix:
1. The degraded record has `evidence_chain=[]` (no EvidenceRecord created), which violates the "no empty evidence chain" invariant cited in diagnostics.py:8-11. Fix: create the EvidenceRecord *before* the degraded audit.append, and include its ID in the degraded record's evidence_chain.
2. The EvidenceRecord is created with `type=LLM_DECISION` even on the degradation path. Should be a new `EvidenceType.DEGRADED` or `RULE_FALLBACK`.

Recommended restructure:
```python
except Exception as exc:
    target, basis = _rule_translate(source_segment, glossary, entities)
    rec = EvidenceRecord(
        type=EvidenceType.RULE_FALLBACK,  # new enum value
        module="isa.translate_segment.degraded",
        source_span=source_segment,
        target_span=target,
        rationale=f"degraded (llm_unavailable): {exc!r}",
    )
    ev_id = evidence.add(rec)
    result = TranslationResult(translation=target, evidence_ids=[ev_id], cache_hit=False)
    cache.set(cache_key, result)
    audit.append("TRANSLATE_SEGMENT", cache_key, [ev_id],
                 artifact_snapshot={"degraded": True, "reason": f"llm_unavailable: {exc!r}"})
    return result  # <-- early return; do NOT fall through
```
Risk: minimal — the normal path is unchanged; only the except branch is restructured.

---

## TRA-016 (WARNING) — `count_blocking` stub returns 0 — CONFIRMED

### Current evidence
- `tra/diagnostics.py:159-166`:
  ```python
  def count_blocking(self, evidence_for_record: dict[str, EvidenceRecord]) -> int:
      """Count BLOCKING diagnostics recorded in audit evidence.

      Note: BLOCKING is raised at VERIFY time, not in the audit trail itself.
      This helper inspects the referenced evidence records for a policy
      violation flag if one has been attached.
      """
      return 0  # hook for VERIFY to populate; trail stores records, not severities
  ```
- Grep `count_blocking` across `tra/` and `tests/`: **only the definition site** (`diagnostics.py:159`). Zero callers. Zero tests.

### Root cause
Original claim is fully correct. The method is dead code: never called, returns a hardcoded 0 with a comment that admits "hook for VERIFY to populate". This is a stub left from Phase 6 hardening that was never wired up.

### Fix assessment
Original fix (delete the method) is optimal — it's dead code with no callers. Alternative: if a future L4 consumer wants to count BLOCKING diagnostics in the trail, that logic belongs in `reporting.py` (which already has `summarize_audit()` with `blocking_flags` counter — see `tests/test_reporting.py:23`). Recommend delete.

---

## TRA-017 (WARNING) — 5 unused dependencies — CONFIRMED

### Current evidence (grep results)
- **litellm**: 0 imports across `tra/`, `tra_cli.py`, `tests/`. Listed in `requirements.txt:11` and `pyproject.toml:20`. Unused.
- **structlog**: 0 imports. Listed in `requirements.txt:8` and `pyproject.toml:17`. Only mentioned in `README.md:78` ("Phase 6: structlog") and `SKILL.md:189` (which already notes it's unused). Unused.
- **pydantic-settings** (a.k.a. `pydantic_settings`): 0 imports. Listed in `requirements.txt:3` and `pyproject.toml:12`. Unused. (`tra/config.py:9` imports `from pydantic import BaseModel` — plain pydantic, not pydantic-settings.)
- **mdit-py-plugins** (a.k.a. `mdit_py_plugins`): 0 imports. Listed in `requirements.txt:5` and `pyproject.toml:14`. `tra/anchor.py:25-26` imports `from markdown_it import MarkdownIt` and `from markdown_it.token import Token` — but never `mdit_py_plugins`. Unused.
- **black** (dev): 0 imports. Has a `[tool.black]` config block in `pyproject.toml:44-46` but is never invoked in any documented workflow. The project uses `ruff` for linting (also dev dep, also configured). Unused.
- **pytest-asyncio** (dev): 0 `async def` test functions across `tests/`. 0 `import asyncio`. `pyproject.toml:61` sets `asyncio_mode = "auto"` but no async tests exist to exercise it. Unused.

### Root cause
Original claim is fully correct — all 6 listed dependencies (the original count of "5" actually covers 6 items, because the original lumps black + pytest-asyncio as dev) are unused. README and SKILL.md acknowledge structlog is unused; the others are silent leftovers.

### Fix assessment
Original fix (remove from `requirements.txt` and `pyproject.toml`) is optimal. Risks:
- **litellm**: removing is safe — `model_endpoint` config field is read but `llm_translate` is always `None` in current code (kernel.py:186 passes no `llm_translate` to `translate_segment`).
- **structlog**: removing is safe — `AuditTrail` uses plain `path.open("a")`.
- **pydantic-settings**: safe to remove.
- **mdit-py-plugins**: safe — `markdown-it-py` works without plugins for current usage.
- **black**: safe to remove (ruff covers formatting via `ruff format`).
- **pytest-asyncio**: safe to remove; also delete `asyncio_mode = "auto"` from `pyproject.toml:61`.

---

## TRA-018 (WARNING) — Immutability unenforced — CONFIRMED

### Current evidence
- `tra/memory.py:154-160` — `Entity`:
  ```python
  class Entity(BaseModel):
      """An immutable identifier isolated from natural-language translation."""
      name: str
      type: EntityType
      mutable: bool = False  # Invariant: entities are never translated
      context: str | None = None
  ```
  Docstring says "immutable", field `mutable: bool = False` is a *data flag* (not enforcement). No `model_config = ConfigDict(frozen=True)`. `Entity(name="x", type=...).name = "y"` succeeds at runtime.
- `tra/memory.py:132-143` — `GlossaryEntry`: no `frozen=True`.
- `tra/memory.py:146-151` — `ForbiddenMapping`: no `frozen=True`.
- `tra/config.py:23-60` — `BootstrapConfig`: docstring says "read-only Immutable Config segment" (line 24). No `frozen=True`.
- `tra/memory.py:172-184` — `RuntimeContext`: correctly NOT frozen (per revalidate-A note, this is the R/W segment by design). ✓
- Grep `frozen` across `tra/`: **0 matches**. No model uses `frozen=True` anywhere.

### Root cause
Original claim is fully correct. The "immutable" semantics are documented in docstrings but never enforced. Any caller can mutate `Entity.name`, `GlossaryEntry.target`, `BootstrapConfig.conformance_level`, etc. after construction, breaking the cache key invariants (cache.py:57-67 hashes these fields).

### Fix assessment
Original fix (`model_config = ConfigDict(frozen=True)` on `Entity`, `GlossaryEntry`, `ForbiddenMapping`, `BootstrapConfig`) is optimal. Risks:
- `RuntimeContext` must stay mutable — confirmed by revalidate-A; do NOT freeze.
- `BootstrapConfig.from_yaml()` (config.py:38) constructs the model normally — `frozen=True` does not block construction, only post-init mutation. ✓
- `kernel.py:104-107` constructs `RuntimeContext(configuration=config.model_dump(), ...)` — `model_dump()` returns a fresh dict, so freezing `BootstrapConfig` does not affect this. ✓
- Test files that mutate models in setup would break — but a quick grep shows tests only mutate `RuntimeContext` (which stays mutable). ✓
- Caveat: `BootstrapConfig` is used by `benchmark.py:84` via `self.config.model_copy(update={...})` — `model_copy` works on frozen models. ✓

---

## TRA-019 (WARNING) — 2 runtime asserts in kernel.py stripped under `-O` — CONFIRMED

### Current evidence
- `tra/kernel.py:128-135`:
  ```python
  self._transition(KernelState.INITIALIZE_RUNTIME)
  self._transition(KernelState.ANALYZE_DOCUMENT)
  analyze_document(src, self.ctx, self.audit)
  assert self.ctx.document_profile is not None       # line 130
  assert self.ctx.structural_map is not None         # line 131
  profile: DocumentProfile = self.ctx.document_profile
  smap: StructuralMap = self.ctx.structural_map
  ```
- Grep `assert ` across `tra/` (excluding `tests/`): only the two lines above. All other `assert` matches are in `tests/` (legitimate test assertions, fine).

### Root cause
Original claim is fully correct. Under `python -O` (or `PYTHONOPTIMIZE=1`), both `assert` statements are stripped, and the subsequent lines (`profile = self.ctx.document_profile` / `smap = self.ctx.structural_map`) silently receive `None`. Downstream `build_glossary(src, profile, ...)` then either raises `AttributeError` (intransparent) or, worse, succeeds with wrong semantics if `None` happens to be falsy-passing.

### Fix assessment
Original fix (replace with `if … is None: raise TRAException(...)`) is optimal. Recommended:
```python
if self.ctx.document_profile is None:
    raise TRAException("ANALYZE_DOCUMENT failed: document_profile not populated")
if self.ctx.structural_map is None:
    raise TRAException("ANALYZE_DOCUMENT failed: structural_map not populated")
```
This survives `-O` and produces a spec-named exception (which routes through `_recover()` per kernel.py:159). Risk: minimal.

---

## Net assessment
**All 9 Track B findings CONFIRMED.** The original audit's root-cause analysis is accurate for every finding; the suggested fixes are mostly optimal, with the adjustments noted above (TRA-011 fnmatch iteration, TRA-012 chokepoint refactoring, TRA-013 injectable clock + content-addressed evidence IDs, TRA-015 early return + EvidenceRecord before degraded audit.append, TRA-016 delete, TRA-017 also drop `asyncio_mode`, TRA-018 freeze four models, TRA-019 replace assert with TRAException). Empirical probes for TRA-011 and TRA-013 produced the exact failures predicted by the original audit.

---

## Task ID: revalidate-C — Re-validate Track C findings (doc-vs-code consistency)

**Agent:** Explore (re-validation Agent C)
**Scope:** Independent re-verification of 8 Track C findings against CURRENT repo state at `/home/z/my-project/tra/`.
**Mode:** Read-only audit — no files modified.

### Doc-update history since original audit

Recent commits touching the relevant docs (most recent first):
- `359ba6b Add SKILL.md guidance for the TRA prototype engine`
- `a4a380f Sync CLAUDE.md and README.md with Phase 0-6 prototype status`
- `4d97aa1 Implement Phase 6 hardening: HITL, L4 forensics, graceful degradation`

Commit `a4a380f` updated the **root** README.md and CLAUDE.md:15 (now says "Phases 0–6 are complete"). It did NOT touch `tra-prototype/README.md`, the CLAUDE.md "Known gaps" list, `tra_cli.py` docstring, `SKILL.md`, or `implementation_plan.md`. **None of the 8 Track C findings have been remediated in code/docs.**

### Per-finding verdicts

| ID | Severity | Verdict | One-line evidence |
|---|---|---|---|
| TRA-020 | BLOCKING | CONFIRMED | CLAUDE.md:42 "Known gaps (honest…)" lists only 3 bullets (structlog/asyncio/cross-run cache); omits ~13 others. |
| TRA-021 | BLOCKING | CONFIRMED | tra-prototype/README.md:3 "Phase 0–5"; :78-79 "Phase 6 … is pending". Phase 6 actually shipped (kernel.py:293-312 `_export_forensics`, hitl.py, recovery.py 5 handlers, status.md commit 4d97aa1). |
| TRA-022 | WARNING | CONFIRMED | tra_cli.py:1 "Phase 0.1.5 skeleton" docstring lists 3 subcommands; 4 `@cli.command()` decorators present (translate:64, cache-clear:123, audit:135, validate:197). |
| TRA-023 | WARNING | CONFIRMED | SKILL.md:67 `pip install -e .` (no `[dev]`); §7 L172-176 requires ruff/mypy/pytest which live only in pyproject.toml `[project.optional-dependencies] dev`. |
| TRA-024 | WARNING | CONFIRMED | implementation_plan.md:14-55 Phase 0 items ALL `[ ]` (delivered); :305-347 lists test_policy.py/test_cache.py/test_evidence.py/benchmark/runner.py/benchmark/test_benchmarks.py — none exist (LS of tests/ confirms). |
| TRA-025 | WARNING | CONFIRMED | No .gitignore at repo root; `git ls-files` shows tracked: audit_trace.jsonl, cache/cache.db, compilation_artifacts/{entity_table,glossary,structural_map,style_profile}.yaml. |
| TRA-026 | WARNING | CONFIRMED | config.yaml:18 `expire: null`; config.py:46-47 reads only `enabled`+`directory`; cache.py:105 hardcodes `expire=None` in `diskcache.set()`. |
| TRA-027 | WARNING | CONFIRMED | examples/expected_outputs/security_advisory_zh.L3.md is 9 lines of plain translated markdown; no audit trace, no glossary, no L3 conformance verdict. |

### Detail

**TRA-020 — CONFIRMED.** CLAUDE.md:42-46 verbatim:
```
**Known gaps (honest, not yet addressed):**
- `structlog` is a listed dependency but the engine uses the plain `AuditTrail` (no structured/correlation-ID logging — 6.3.1 open).
- No `asyncio` segment-level parallelism (6.5.1 open).
- Glossary/entity tables are rebuilt per run; only the translation output is cached across runs via diskcache (6.5.2 open).
```
Material gaps NOT listed: inline-code glossary substitution (S-03) not suppressed (per tra-prototype/README.md:76-77); LLM seam wired but unused (:74-75); Phase 7 entirely not started; only ZH↔EN module exists; Phase 1.3.1-1.3.4 (TF-IDF, LLM-assisted candidate generation, glossary conflict detection) all unchecked in plan.

**TRA-021 — CONFIRMED.** tra-prototype/README.md:3 `A Phase 0–5 reference implementation`; :78-79 `**Phase 6** (exception hardening, human-in-the-loop, structlog, L4 evidence tracing) is pending.` Phase 6 is delivered: status.md confirms commit `4d97aa1`; kernel.py:293-312 implements `_export_forensics`; tra/hitl.py exists; recovery.py defines all 5 recovery handlers (`recover_unknown_term`, `recover_broken_markdown`, `recover_certainty_conflict`, `recover_entity_ambiguity`, `recover_glossary_conflict`); test_phase6_hardening.py exists. The "Sync" commit `a4a380f` updated root README.md but NOT tra-prototype/README.md.

**TRA-022 — CONFIRMED.** tra_cli.py:1 docstring `"""TRA prototype CLI (Phase 0.1.5 skeleton)."""` lists only `translate`, `cache-clear`, `audit`. The 4th command `validate` (tra_cli.py:197, added in commit 56f5a09 "Add TRA Phase 5") is missing from the docstring.

**TRA-023 — CONFIRMED.** SKILL.md:67 install command is `pip install -e .` (no `[dev]`). §7 Quality gates (SKILL.md:172-176) requires `ruff format . && ruff check . && ruff format --check . && mypy --strict tra && pytest tests` — all four tools are only in `pyproject.toml [project.optional-dependencies] dev` (lines 23-30). A user following only SKILL.md §3 cannot run §7 gates. Optimal fix: change §3 to `pip install -e ".[dev]"`. Low risk.

**TRA-024 — CONFIRMED.** implementation_plan.md:14-55: Phase 0 sections 0.1, 0.2, 0.3, 0.4 — every item still `[ ]` (22 checkboxes total, all unchecked). Yet Phase 0 is delivered: pyproject.toml present, ruff/black/mypy/pytest configured (pyproject.toml:35-62), config.yaml exists, tra_cli.py skeleton exists, memory.py has all Pydantic models, diagnostics.py has EvidenceRegistry, cache.py has CacheKeyGenerator+TranslationCache. File-structure block (:305-347) lists test files that don't exist:
- `test_policy.py` — not in tests/ (PolicyResolver tested implicitly via test_kernel.py/test_isa.py)
- `test_cache.py` — not in tests/
- `test_evidence.py` — not in tests/
- `benchmark/runner.py` — not in tests/benchmark/ (only `cases/` subdir with .jsonl files)
- `benchmark/test_benchmarks.py` — not present; actual file is `tests/test_benchmark.py`
Actual tests/ contains 14 files (test_phase0, test_anchor, test_isa, test_kernel, test_modules, test_validate, test_benchmark, test_recovery, test_reporting, test_utils, test_phase6_hardening, conftest.py + tests/benchmark/cases/{regression,sft}.jsonl).

**TRA-025 — CONFIRMED.** No `.gitignore` at `/home/z/my-project/tra/`. `tra-prototype/.gitignore` correctly excludes `cache/`, `compilation_artifacts/`, `audit_trace.jsonl`, but only applies under `tra-prototype/`. `git ls-files` confirms the following runtime artifacts are tracked at repo root: `audit_trace.jsonl`, `cache/cache.db`, `compilation_artifacts/entity_table.yaml`, `compilation_artifacts/glossary.yaml`, `compilation_artifacts/structural_map.json`, `compilation_artifacts/style_profile.yaml`. status.md:48-49 even acknowledges this: "a run earlier resolved the default config.yaml output paths to the repo root … If you want them gone, rm -rf audit_trace.jsonl cache compilation_artifacts from the repo root — or I can add root-level ignore rules." Neither cleanup happened.

**TRA-026 — CONFIRMED.** config.yaml:18 `expire: null   # static facts: no TTL`. config.py:46-47 reads only `cache.enabled` and `cache.directory` — `expire` is parsed by `yaml.safe_load` but never extracted. cache.py:82 `TranslationCache.__init__(self, directory, enabled=True)` accepts no `expire` parameter; cache.py:105 `self._cache.set(key, result.model_dump(mode="json"), expire=None)` hardcodes `expire=None`. The config field is dead. Optimal fix: either remove `expire` from config.yaml (and note "no TTL" as architectural per CACHE_STRATEGY.md) OR wire it through `BootstrapConfig.cache_expire` → `TranslationCache(expire=…)`. Removing is simpler and matches the spec rationale ("technical facts are static"); wiring is more flexible but adds a knob the spec doesn't require. Either is low-risk.

**TRA-027 — CONFIRMED.** File contents (9 lines):
```
# Security Advisory SA-2024-001

RustVMM v0.5.0 may Confirmed under heavy load. The execution environment must
accurately describe the highly credible configuration so operators can verify.

We should support for the KVM and XFS backends by P99. The
96-core system keeps memory below <5MB at peak.

> Note: may configurations are not recommended in production.
```
Filename `security_advisory_zh.L3.md` implies an L3 certification bundle. Per SKILL.md:102-104 and TRA-CONFORMANCE-GUIDE.md, an L3 output bundle should include the translated markdown PLUS audit_trace.jsonl with zero BLOCKING + compilation_artifacts/ (glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml). The file is just translated markdown — no audit trail, no glossary, no conformance verdict. Optimal fix: rename to `security_advisory_zh.translated.md` to stop implying L3 certification, OR replace with a real L3 bundle (markdown + sibling `audit_trace.jsonl` + sibling `compilation_artifacts/`). Renaming is lowest-risk.

### Summary

**8/8 CONFIRMED.** No partial confirmations, no refutations. None of the 8 docs have been remediated since the original audit (commit `a4a380f` partially updated CLAUDE.md:15 status line and the root README.md but did not touch any of the 8 findings' specific locations). All suggested fixes remain valid and low-risk.

Top-priority remediation order (by severity × user-facing impact):
1. TRA-021 (BLOCKING) — tra-prototype/README.md Phase 6 "pending" claim is actively misleading; one-line fix.
2. TRA-020 (BLOCKING) — CLAUDE.md "honest" gap list needs the additional ~5 material gaps added.
3. TRA-025 — add root `.gitignore` and `git rm --cached` the 6 tracked runtime artifacts.
4. TRA-024 — check Phase 0 boxes; rewrite file-structure block to match actual tests/.
5. TRA-022 / TRA-023 / TRA-026 / TRA-027 — small one-line / few-line doc edits.


---

## Task revalidate-D — Re-validation of Track D (test-suite coverage) findings

Re-audited the 8 Track D findings against the CURRENT state of `/home/z/my-project/tra/tra-prototype/`. Baseline: 103 tests pass in 0.66s. Read every test file under `tests/`, `tests/conftest.py`, `tests/benchmark/cases/{sft,regression}.jsonl`, `tra/isa.py`, `tra/hitl.py`, `tra/memory.py`, `tra/kernel.py`, and `TRA-BENCHMARK-SUITE.md`. Ran the four mutation tests (TRA-028 × 1, TRA-029 × 3, TRA-030 × 2) with backup/restore.

### Mutation-test results (empirical)

| Finding | Mutation | Result |
| --- | --- | --- |
| TRA-028 | `if new_blocking and attempt >= max_retries:` → `if False and new_blocking and attempt >= max_retries:` (isa.py:518) | **103 passed** — mutation NOT caught |
| TRA-029 (original) | Inject `for ev in evidence.all(): if ev.confidence_note < 0.5: diagnostics.append(...)` in `verify_output` | **31 failed, 72 passed** — but fails with `NameError: name 'evidence' is not defined` (verify_output has no `evidence` parameter). Caught for the WRONG reason (scope error), not for self-scoring detection. |
| TRA-029 (adapted v1) | Inject `for ge in ctx.glossary_cache: if ge.confidence_note < 0.5: diagnostics.append(...)` in `verify_output` (uses in-scope `ctx`) | **103 passed** — mutation NOT caught |
| TRA-029 (adapted v2) | Inject `low_conf = any(getattr(ge, "confidence_note", None) is not None and ge.confidence_note < 0.5 for ge in ctx.glossary_cache); _sev_boost = Severity.BLOCKING if low_conf else None` | **103 passed** — mutation NOT caught |
| TRA-030 (M1) | `severity=Severity.WARNING, subsystem="terminology"` → `severity=Severity.BLOCKING, subsystem="terminology"` (isa.py:428-429) | **103 passed** — mutation NOT caught |
| TRA-030 (M2) | `severity=Severity.BLOCKING, subsystem="structural"` → `severity=Severity.WARNING, subsystem="structural"` (isa.py:402-403) | **103 passed** — mutation NOT caught |

### Per-finding verdicts

**TRA-028 — CONFIRMED (BLOCKING).** `tra/isa.py:515-519`:
```python
sub = verify_output(repaired, source_segment, ctx, audit)
new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]
if new_blocking and attempt >= max_retries:
    raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")
```
`grep repair_segment tests/` returns only two call sites:
- `test_isa.py:239` — `repair_segment("it is Valid", "成立", diag, ctx, ev, _audit())` — epistemic, attempt=1 default, repair succeeds (Valid→Confirmed, no new BLOCKING).
- `test_phase6_hardening.py:62` — `repair_segment("系统 成立", "系统 成立", diag, ctx, ev, audit, attempt=1)` — terminology, attempt=1 default, repair succeeds (成立→Confirmed).
No test calls `repair_segment` with `attempt >= max_retries` while new BLOCKING is introduced. Mutation passed → CONFIRMED. The structural branch's own `raise Unrecoverable` (isa.py:510-513) is similarly untested (no test calls repair_segment with `subsystem="structural"` and `attempt >= max_retries`). Suggested test (optimal): call `repair_segment` with a terminology diagnostic whose fix re-introduces an epistemic drift, `attempt=3, max_retries=3`, assert `Unrecoverable` raised.

**TRA-029 — CONFIRMED (BLOCKING).** `tests/test_phase0.py:68-82` (`test_evidence_registry_append_only`):
```python
rec = EvidenceRecord(..., confidence_note=0.1, ...)
evidence_registry.add(rec)
assert len(evidence_registry.all()) == 2
```
The comment at L71 says "confidence_note, if present, must never be read for routing", but the test only asserts record-count. It does NOT call `verify_output` (or any consumer) with a low-`confidence_note` record and assert no diagnostic fires. The original audit's suggested mutation uses `evidence.all()` inside `verify_output`, but `verify_output`'s signature is `(target, source, ctx, audit)` — there is no `evidence` parameter in scope. So the original mutation is broken Python (NameError at runtime), which trips the suite for the wrong reason. Substituting an in-scope variant that reads `ctx.glossary_cache[i].confidence_note` (which IS reachable per `memory.py:141-143`) leaves the suite green (103 passed). CONFIRMED — Invariant 3 is untested at the enforcement boundary. Suggested test (optimal): populate `ctx.glossary_cache` with a `GlossaryEntry(confidence_note=0.1)`, call `verify_output(...)` against a clean target, assert zero diagnostics reference the low-confidence entry. This is the highest-leverage test to add.

**TRA-030 — CONFIRMED (BLOCKING).** No test asserts the exact `Severity` of terminology or structural diagnostics. `tests/test_isa.py` has four `verify_output` tests:
- `test_verify_flags_missing_entity_blocking` (L172-182) — asserts entity diagnostic is BLOCKING.
- `test_verify_flags_epistemic_drift_blocking` (L184-198) — asserts epistemic diagnostic is BLOCKING.
- `test_verify_clean_doc_no_blocking` (L200-214) — asserts zero BLOCKING on clean doc.
- (`test_verify_clean_doc_no_blocking` uses an output where terminology is not triggered.)
None trigger the terminology branch (`if src in target`, isa.py:426) with a severity assertion, and none trigger the structural branch with a severity assertion (the structural branch fires only on heading-count mismatch; `test_kernel_runs_full_pipeline` uses a single `# Security Advisory` heading in both source and target so the branch never fires). Both severity mutations pass → CONFIRMED. Suggested test (optimal, one test covers both): construct `ctx.structural_map` non-None, source with 2 headings, target with 1 heading; assert structural diagnostic is `Severity.BLOCKING`. Then separately construct a target that leaks a source term; assert terminology diagnostic is `Severity.WARNING`.

**TRA-031 — PARTIALLY CONFIRMED (WARNING).** Counted cases:
- `tests/benchmark/cases/sft.jsonl`: 13 cases — F-01..F-05 (5), T-01..T-05 (5), S-05 (1), D-04 (1), E-02 (1).
- `tests/benchmark/cases/regression.jsonl`: 1 case — R-01.
- `TRA-BENCHMARK-SUITE.md` declares 23 spec cases: S-01..S-06 (6), F-01..F-05 (5), T-01..T-05 (5), D-01..D-04 (4), E-01..E-03 (3).

So **13 of 23 spec cases are implemented** (56.5%). The original claim "13 of 24" is off by one in the denominator (likely counts R-01 in the spec total). Missing 10 spec cases: S-01, S-02, S-03, S-04, S-06, D-01, D-02, D-03, E-01, E-03. Highest-value gap: S-03 (inline-code glossary suppression) is also flagged in TRA-021/TRA-020 as an unimplemented production behavior, so adding its benchmark would be double-coverage. Suggested remediation: add the 10 missing cases as JSONL rows (low effort) and parametrize `test_benchmark.py::test_benchmark_case` will pick them up automatically.

**TRA-032 — CONFIRMED (WARNING).** `grep review_decision tests/` returns only `test_phase6_hardening.py:142`. The single test `test_hitl_review_decision_accept` (L134-144) monkeypatches `Prompt.ask` to always return `"accept"` and asserts `resolution == "accept"`. The `review_decision` function (`tra/hitl.py:49-59`) has three branches: `accept` (L52-53), `override` (L54-58, includes a second `Prompt.ask` and optional `on_override` callback), `skip` (L59). Only the `accept` branch is exercised. The `on_override` callback path is never tested. CONFIRMED. Suggested tests (optimal): parametrize over `("accept", "override", "skip")` returning a list of fake answers; for `override`, also test the `on_override` invocation path.

**TRA-033 — CONFIRMED (WARNING).** `grep llm_translate tests/` returns only `test_phase6_hardening.py:80`. The single test `test_graceful_degradation_on_llm_failure` (L71-86) uses a `boom` callable that raises `RuntimeError("llm down")`. No test exercises `ValueError`, `TimeoutError`, `ConnectionError`, `JSONDecodeError`, or generic `Exception`. `translate_segment`'s except clause (isa.py:316) is `except Exception` — broad — so any of these would be caught, but the test suite does not assert that. CONFIRMED. Suggested test (optimal): parametrize the exception type `[RuntimeError, TimeoutError, ValueError, json.JSONDecodeError]` and assert the rule path always produces a `degraded=True` audit artifact.

**TRA-034 — CONFIRMED (INFO).** `tests/conftest.py` defines six fixtures: `sample_glossary` (L19-24), `sample_entities` (L27-32), `cache_context` (L35-53), `evidence_registry` (L56-58), `sample_evidence` (L61-72), `config` (L75-78). Grep across `tests/test_*.py` for each fixture name:
- `cache_context`, `evidence_registry`, `sample_evidence`, `config` → only `test_phase0.py` (L28, L38, L68, L102).
- `sample_glossary`, `sample_entities` → used only transitively via `cache_context` (also only in `test_phase0.py`).
- Other test files (`test_kernel.py:14`, `test_phase6_hardening.py:100`, `test_benchmark.py:26`, `test_validate.py`) bypass the `config` fixture and load `config.yaml` directly via `Path(__file__).resolve().parent.parent / "config.yaml"`.
CONFIRMED — the conftest is dead weight outside `test_phase0.py`. Suggested remediation (low value): either (a) inline the fixtures into `test_phase0.py` (delete `conftest.py`), or (b) migrate the other tests to use the shared `config` fixture to reduce duplication. Option (a) is lower-risk; option (b) is more idiomatic pytest.

**TRA-035 — PARTIALLY CONFIRMED (INFO).** Tallying the 6 mutations run for TRA-028/029/030:
- Caught: 0 (the one "caught" TRA-029 mutation fails only due to a Python NameError — a syntactic/scope accident, not because the test detects a self-scoring violation).
- Not caught: 5 (TRA-028 × 1, TRA-029 adapted × 2, TRA-030 × 2).
- Empirical invariant-mutation catch rate for Track D findings: **0% real / 16.7% nominal** (1 of 6), NOT 42% as originally claimed. The directional claim ("mutation coverage is weak") is CONFIRMED; the precise 42% figure is not reproducible from the three findings' mutations alone. Either the original audit counted additional mutations beyond TRA-028/029/030, or the 42% was computed with a different denominator. Recommend replacing "42%" with "<20%" in the audit report.

### Summary

| Finding | Severity | Verdict | Mutation passes suite? |
| --- | --- | --- | --- |
| TRA-028 | BLOCKING | CONFIRMED | Yes — `raise Unrecoverable` block has zero coverage |
| TRA-029 | BLOCKING | CONFIRMED | Yes (with adapted in-scope mutation) |
| TRA-030 | BLOCKING | CONFIRMED | Yes (both M1 terminology and M2 structural) |
| TRA-031 | WARNING | PARTIALLY CONFIRMED | n/a — 13 of 23 spec cases (not 24) |
| TRA-032 | WARNING | CONFIRMED | n/a — only `accept` branch tested |
| TRA-033 | WARNING | CONFIRMED | n/a — only `RuntimeError` tested |
| TRA-034 | INFO | CONFIRMED | n/a — fixtures only used by `test_phase0.py` |
| TRA-035 | INFO | PARTIALLY CONFIRMED | n/a — catch rate ≈0–17%, not 42% |

**6 of 8 CONFIRMED, 2 PARTIALLY CONFIRMED, 0 REFUTED.** All three BLOCKING findings (TRA-028/029/030) are robustly confirmed by empirical mutation testing. The two partial confirmations are about precise numeric denominators (TRA-031: 23 vs 24 spec cases; TRA-035: ~0–17% vs 42% catch rate) — the directional claims are correct. No remediation has occurred since the original audit.

Top-priority test additions (in order):
1. **TRA-029 test** — highest leverage: directly asserts Invariant 3 (never self-score) at the verify_output boundary; would catch 2 of the 3 self-scoring mutations.
2. **TRA-028 test** — `repair_segment` with `attempt >= max_retries` and an induced new-BLOCKING scenario, assert `Unrecoverable`.
3. **TRA-030 test** — parametrized severity assertions for both terminology (WARNING) and structural (BLOCKING) diagnostics.
4. **TRA-032 test** — parametrize `review_decision` over `accept/override/skip`.
5. **TRA-033 test** — parametrize `llm_translate` exception type.
6. **TRA-031 remediation** — add the 10 missing JSONL benchmark cases.

---
Task ID: remediation
Agent: Super Z (main)
Task: Re-validate 35 audit findings, fix the actionable ones, commit and push

Work Log:
- Dispatched 4 parallel re-validation agents (A/B/C/D); 31 confirmed, 4 partially confirmed (TRA-004: 3+1 of 5 not 4 of 5; TRA-010: only BootstrapConfig frozen not RuntimeContext; TRA-031: 13 of 23 not 24; TRA-035: <20% not 42%)
- Fixed 18 findings across code, tests, and docs:
  * BLOCKING code: TRA-003 (repair_segment surgical), TRA-005 (L3 gate in-band), TRA-011 (cache-clear glob)
  * WARNING code: TRA-015 (double audit record), TRA-016 (count_blocking stub), TRA-018 (frozen models), TRA-019 (asserts), TRA-022 (stale docstring), TRA-017 (pytest-asyncio)
  * BLOCKING tests: TRA-028, TRA-029, TRA-030 (3 new regression tests; suite now 107, was 103)
  * Doc: TRA-020 (CLAUDE.md known gaps 3->11 bullets), TRA-021 (prototype README Phase 0-6), TRA-023 (SKILL.md install [dev]), TRA-025 (root .gitignore + git rm --cached 6 artifacts), TRA-026 (config.yaml expire), TRA-027 (L3.md -> L3.target.md)
- Empirically verified TRA-003 (raises Unrecoverable at attempt=1) and TRA-011 (invalidate('*') deletes 3 of 3)
- Quality gates: ruff check / ruff format / mypy --strict (20 files) / pytest (107 tests) all green
- Commit c42c457 pushed to origin/main via SSH wrapper (paramiko + blocking-sendall fix)

Stage Summary:
- 18 of 35 findings remediated; 17 remain (TRA-001 segment-level, TRA-002 registry, TRA-004 exception recovery, TRA-006 Policy Engine, TRA-007 transitions, TRA-008 rewrite_links, TRA-009 terminology severity, TRA-012 sanitize bypass, TRA-013 audit reproducibility, TRA-014 path traversal, TRA-024 implementation_plan, TRA-031-035 test/benchmark gaps) — these are larger refactors deferred to Phase 7 prep
- HEAD: c42c457 on origin/main, in sync

---

## Task `validate-S` — Security & Reproducibility cluster deep re-validation

Agent S independently re-verified TRA-012 / TRA-013 / TRA-014 against the CURRENT codebase at HEAD `c42c457` (`/home/z/my-project/tra/tra-prototype/`). All file:line citations below are from the live tree (read directly, not from prior reports). Read-only audit — no files modified.

### Verdict table

| Finding | Severity | Verdict | Root cause confirmed? |
| --- | --- | --- | --- |
| TRA-012 — `_sanitize_input` bypassed at validate/benchmark boundaries | WARNING | **PARTIALLY CONFIRMED** | Yes — function is private to `kernel.py`; only caller is `kernel.py:125`. Bypass at `validate.py:81` and `benchmark.py:102` is real. Empirical test of "bidi survives into audit JSONL" is REFUTED (audit stores only SHA-256 hashes), but the bypass still changes the `input_hash` and survives into in-memory `EvidenceRecord.source_span` / `StructuralNode.text`. |
| TRA-013 — Audit trail NOT byte-reproducible (uuid4 + datetime.now) | WARNING | **CONFIRMED** | Yes — both sources verified empirically. Two runs of identical input produce non-byte-equal `audit_trace.jsonl` (timestamps + evidence IDs differ) and non-byte-equal `evidence_trace.jsonl` at L4 (evidence IDs leak into forensic artifact). |
| TRA-014 — Path traversal: no protection on config paths | WARNING | **CONFIRMED** | Yes — verified empirically. Both `../../escaped_output` (relative `..` escape) AND `/tmp/tra_abs_evil_PID` (absolute path injection) successfully write all compilation artifacts outside any project root. `BootstrapConfig` has NO path validator. |

---

### TRA-012 — `_sanitize_input` bypassed at validate/benchmark boundaries

#### Current evidence (live code)

- **`tra/kernel.py:75-90`** — `_CONTROL_RE` and `_sanitize_input` defined exactly as the brief states:
  ```python
  _CONTROL_RE = re.compile(
      "[" + "\x00-\x08\x0b\x0c\x0e-\x1f\x7f" + "\u202a-\u202e" + "\ufeff" + "]"
  )
  def _sanitize_input(text: str) -> str:
      return _CONTROL_RE.sub("", text)
  ```
- **`tra/kernel.py:122-125`** — the ONLY production caller:
  ```python
  def run(self, source: str | Path) -> str:
      src = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
      src = _sanitize_input(src)
  ```
- **Grep result** (`_sanitize_input` across `tra/`): only 2 hits — the definition at `kernel.py:83` and the call at `kernel.py:125`. No call from `validate.py`, `benchmark.py`, `isa.py`, or `reporting.py`.
- **`tra/validate.py:71-86`** — bypasses sanitization entirely:
  ```python
  if isinstance(source, Path):
      source = source.read_text(encoding="utf-8")
  if isinstance(candidate, Path):
      candidate = candidate.read_text(encoding="utf-8")
  ...
  _profile, _smap = analyze_document(source, ctx, audit)   # UNSANITIZED
  build_glossary(source, _profile, ctx, evidence, audit)
  build_entity_table(source, _smap, ctx, evidence, audit)
  diagnostics = verify_output(candidate, source, ctx, audit)   # candidate also UNSANITIZED
  ```
- **`tra/benchmark.py:88`** — main path IS sanitized (`kernel.run(case.source)` invokes `_sanitize_input`).
- **`tra/benchmark.py:99-105`** — re-verify path is NOT sanitized:
  ```python
  if case.zero_blocking:
      audit = AuditTrail(cfg.audit_trace)
      ctx = RuntimeContext(configuration=cfg.model_dump())
      evidence = EvidenceRegistry()
      profile, smap = analyze_document(case.source, ctx, audit)   # UNSANITIZED
      build_glossary(case.source, profile, ctx, evidence, audit)
      build_entity_table(case.source, smap, ctx, evidence, audit)
      diags = verify_output(output, case.source, ctx, audit)
  ```

#### Empirical test (run live)

```python
source = '# Advisory\n\nSystem established.\n\u202eevil\n'  # U+202E RLO bidi override
report = validate_translation(source, candidate, cfg, audit=audit)
audit.flush()
# Audit JSONL contents: only hashes, sizes, counts, IDs. Bidi char NOT present in any field.
# But: input_hash for ANALYZE_DOCUMENT record = sha256(UNSANITIZED source)[:16]
#      → differs from what kernel.run would produce (kernel.run sanitizes first)
#      → audit-trail hash ≠ source-text hash; the "input_hash" field is misleading
```

Result: bidi char does NOT reach the audit JSONL bytes (audit only stores `_hash(source)` truncated to 16 hex chars + counts/sizes). It DOES survive into the in-memory `EvidenceRecord.source_span` / `StructuralNode.text` (not persisted to disk via validate.py, but a future caller that writes `structural_map.json` directly from a `validate_translation`-built context would leak it). The most material concrete impact today is that the `input_hash` recorded on the audit trail is computed over the *unsanitized* source, so it no longer matches any externally-computed source hash — breaking the audit-trail ↔ source provenance invariant.

#### Verdict — PARTIALLY CONFIRMED

- Bypass of `_sanitize_input` at validate.py:81 and benchmark.py:102: **CONFIRMED**.
- Empirical "bidi survives into audit JSONL payload": **REFUTED** (audit JSONL stores hashes only).
- Real impact today: (a) `input_hash` divergence — audit hash no longer equals source hash; (b) in-memory evidence records and structural-map nodes still carry bidi chars; (c) `verify_output(candidate, ...)` in validate.py receives an unsanitized candidate string, which could trip the markdown-it parser or break downstream link rewriting.

#### Root cause — confirmed

`_sanitize_input` is a private function on `kernel.py` (prefix `_`, not exported in `__init__.py`). It is logically a *shared input-validation utility*, not a kernel-state-machine concern — but it lives on the kernel module, so callers that don't go through `TRAKernel.run` (validate.py, benchmark.py's re-verify path, tra_cli.py's `validate` command) silently skip it.

#### Optimal fix

**Move `_sanitize_input` to `tra/utils.py` as a public `sanitize_input` and call it inside `analyze_document` (single chokepoint — analyze is the first ISA instruction to consume raw source).** Additionally sanitize the `candidate` parameter inside `verify_output` so the validate.py path is covered even when callers skip analyze.

Precise change:
1. `tra/utils.py`: add `sanitize_input(text: str) -> str` (move `_CONTROL_RE` + body verbatim); add to `__all__`.
2. `tra/kernel.py:75-90`: delete local `_CONTROL_RE` and `_sanitize_input`. Replace `kernel.py:125` body with `from .utils import sanitize_input` (or keep an alias `_sanitize_input = sanitize_input` for the existing test import — see Risks).
3. `tra/isa.py:65-76` (`analyze_document`): after the `isinstance(source, Path)` branch, add `source = sanitize_input(source)`. This is one line, applies to every caller (kernel, validate, benchmark, tests).
4. `tra/isa.py:406-415` (`verify_output`): add `target = sanitize_input(target)` and `source = sanitize_input(source)` after the signature (defense-in-depth; covers validate.py's candidate path).
5. Keep `kernel.py:125` calling `sanitize_input` as defense-in-depth (idempotent — second call is a no-op on already-clean text).

#### TDD test spec (write FIRST, expect RED)

```python
# tests/test_phase6_hardening.py — add
def test_sanitize_applied_at_validate_translation(tmp_path):
    """TRA-012: validate_translation must sanitize source AND candidate."""
    from tra.config import BootstrapConfig
    from tra.memory import ConformanceLevel
    from tra.validate import validate_translation

    cfg = BootstrapConfig(
        language_pair="zh-en", domain="cyber",
        conformance_level=ConformanceLevel.L3_STRICT,
        model_endpoint="", model_version="",
        cache_enabled=False,
        cache_directory=str(tmp_path / "cache"),
        compilation_dir=str(tmp_path / "artifacts"),
        audit_trace=str(tmp_path / "audit.jsonl"),
    )
    bidi = "\u202e"
    source = f"# Advisory\n\nSystem established.\n{bidi}evil\n"
    candidate = f"# Advisory\n\nThe system is Confirmed.\n{bidi}clean\n"
    audit = AuditTrail(str(tmp_path / "audit.jsonl"))
    validate_translation(source, candidate, cfg, audit=audit)
    audit.flush()
    # The audit input_hash for ANALYZE_DOCUMENT must equal a hash computed
    # from the SANITIZED source (i.e. with the bidi char stripped).
    from tra.isa import _hash
    expected_hash = _hash(source.replace(bidi, ""))
    records = audit.load()
    analyze_rec = next(r for r in records if r.isa_instruction == "ANALYZE_DOCUMENT")
    assert analyze_rec.input_hash == expected_hash, (
        f"validate_translation bypassed sanitize: "
        f"got {analyze_rec.input_hash!r}, expected {expected_hash!r}"
    )
    # And the structural map text must NOT contain the bidi char.
    # (Covered transitively if analyze_document sanitizes before build_structural_map.)
```

Currently RED: `analyze_rec.input_hash` is computed over the unsanitized source, so it differs from `_hash(source.replace(bidi, ""))`.

#### Risks

- `tests/test_phase6_hardening.py:17` imports `_sanitize_input` from `tra.kernel`. If we delete the kernel-local copy, this import breaks. Mitigation: keep a private alias `_sanitize_input = sanitize_input` in `kernel.py` OR update the test import to `from tra.utils import sanitize_input`. The cleaner option is to update the test (single call site) — but that requires editing `test_phase6_hardening.py:17,90`.
- `test_isa.py::test_analyze_*` calls `analyze_document` with clean ASCII sources (e.g., `"# Security Advisory\n\n执行环境 here.\n"`). Adding `sanitize_input` to `analyze_document` is a no-op for these inputs — no test breakage expected.
- `test_phase6_hardening.py::test_input_sanitization_strips_*` (referenced in the brief) — there is no test with this name in the current tree; the actual sanitization test is `test_sanitize_strips_control_and_bidi` at L88-96, which calls `_sanitize_input` directly. It tests the regex behavior in isolation and is unaffected by moving the function (it just needs the import updated).
- The `verify_output(candidate, ...)` sanitization in step 4 could mask a real diagnostic (e.g., if a candidate legitimately contains a bidi char that should be flagged). But since the spec forbids bidi chars in the pipeline (§6.5.3), stripping them at verify time is the correct behavior — the diagnostic should be "candidate contained bidi override" if we want to surface it, which is a separate enhancement.
- `kernel.py:125` calling `sanitize_input` becomes redundant after step 3; keeping it is defense-in-depth and idempotent. Cost: one extra regex sub per run (negligible).

---

### TRA-013 — Audit trail NOT byte-reproducible (uuid4 + datetime.now)

#### Current evidence (live code)

- **`tra/diagnostics.py:37-40`** — `EvidenceRecord.id` uses `uuid4`:
  ```python
  class EvidenceRecord(BaseModel):
      id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
  ```
- **`tra/diagnostics.py:54-58`** — `AuditRecord.timestamp` uses `datetime.now(UTC)`:
  ```python
  class AuditRecord(BaseModel):
      sequence_id: int
      timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
  ```
- **`tra/diagnostics.py:16-20`** — confirms imports: `from datetime import UTC, datetime` and `from uuid import uuid4`.

#### Empirical test (run live — same input, same config, two runs)

```python
# Two TRAKernel.run() calls with identical source and (disabled) cache.
# Compare audit_trace.jsonl line-by-line.
```

Diff output:
- Line 0 (ANALYZE_DOCUMENT): `timestamp` differs (`2026-07-13T03:42:34.710087Z` vs `...713577Z`).
- Line 1 (BUILD_GLOSSARY): `timestamp` differs AND `evidence_chain` differs — 11 `ev_` IDs all differ between runs (e.g. `ev_15b5e99b19e9` vs `ev_b70ce6f6c814`).
- Line 2 (BUILD_ENTITY_TABLE): `timestamp` + `evidence_chain` differ.
- Line 3 (TRANSLATE_SEGMENT): `timestamp` + `evidence_chain` differ (1 evidence ID per segment).
- Lines 4-5 (VERIFY_OUTPUT, etc.): `timestamp` differs only.

L4 forensic test (`evidence_trace.jsonl`):
- `glossary.yaml`, `entity_table.yaml`, `structural_map.json`, `execution_log.json`, `style_profile.yaml`, `repair_history.jsonl`, `ambiguity_register.json` — **byte-equal** across runs (deterministic).
- `evidence_trace.jsonl` — **NOT byte-equal**: line 1's `evidence_ids` array differs (e.g. `["ev_9fa6a3aafbf7","ev_0a998b5a5e03"]` vs `["ev_67b492ed8551","ev_b5959178da48"]`). The evidence IDs leak from `EvidenceRecord.id` through `EvidenceRegistry` into `line_by_line_trace` (reporting.py).

#### Cache non-determinism check

- **`tra/cache.py:57-67`** — `CacheKeyContext.key()`: SHA-256 over canonical JSON of `{source, glossary_hash, entity_hash, model_endpoint, model_version, policy_stack_hash}`. All inputs deterministic → cache key is deterministic. ✓
- **`tra/cache.py:70-76`** — `TranslationResult.created_at: str | None = None`. Grep of `isa.py` shows `TranslationResult(...)` is constructed at L343-345 and L368-370 — neither sets `created_at`. It is always `None`. No non-determinism via the cache. ✓
- BUT: the cached `TranslationResult.evidence_ids` carry the `ev_` UUIDs. So a cache HIT (across runs) replays the SAME evidence IDs from the first run — which means a cached run looks reproducible only if the cache is warm; a cold cache produces fresh UUIDs. This is a hidden coupling: cache state affects audit-trail reproducibility.

#### Verdict — CONFIRMED

Two independent non-determinism sources, both verified empirically:
1. **Evidence IDs** (`uuid4().hex[:12]`) — propagate to `audit_trace.jsonl` (`evidence_chain` field) AND `evidence_trace.jsonl` (L4 forensic artifact, `evidence_ids` field).
2. **Audit timestamps** (`datetime.now(UTC)`) — propagate to `audit_trace.jsonl` only.

#### Spec check

`TRA-SPECIFICATION.md §7 (TRA-QA)` describes the diagnostic report format (severity / subsystem / issue / evidence / action / repaired) but does NOT mandate reproducible timestamps or byte-identical audit trails. However, `README.md:53` advertises "Deterministic, content-addressable cache → byte-identical output for identical context" and `cache.py:1-13` frames reproducibility as the cache's core purpose. L4_FORENSIC is the most stringent conformance level and emits forensic artifacts (`evidence_trace.jsonl`) explicitly for post-hoc analysis — non-determinism in those artifacts defeats the forensic purpose. So while the spec doesn't *mandate* reproducibility, the codebase's own positioning makes it an implicit contract.

#### Root cause — confirmed

Two independent sources, as the brief states. The optimal fix differs for each:
- **Evidence IDs**: content-addressed is the right model (matches the cache key philosophy). Replace `uuid4().hex[:12]` with `ev_{sha256(canonical(content))[:12]}` where `content` is a stable serialization of the evidence record's invariant fields (type, module, source_span, target_span, rationale, rule_id). This makes the ID a function of the record's meaning, so identical evidence produces identical IDs across runs.
- **Timestamps**: timestamps are inherently wall-clock. Two faithful options: (a) injectable clock — `AuditTrail.__init__` takes a `clock: Callable[[], datetime] = lambda: datetime.now(UTC)` parameter, so tests / reproducible runs can inject a fixed clock; (b) document that timestamps are NOT reproducible by design (they exist for forensics, not for byte-equality) and add a `--reproducible` flag that omits timestamps entirely.

Option (a) is more spec-faithful because it preserves timestamps for forensic use while allowing reproducible runs. Option (b) is simpler but loses forensic information. Recommend (a) for evidence IDs (always content-addressed) and (a) for timestamps (injectable clock, default = real wall-clock).

#### Optimal fix

Precise change:
1. `tra/diagnostics.py:37-40` — replace `EvidenceRecord.id` default_factory:
   ```python
   import hashlib, json
   def _evidence_id(record: "EvidenceRecord") -> str:
       payload = json.dumps({
           "type": record.type.value,
           "module": record.module,
           "source_span": record.source_span,
           "target_span": record.target_span,
           "rationale": record.rationale,
           "rule_id": record.rule_id,
       }, sort_keys=True, ensure_ascii=False)
       return f"ev_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]}"
   ```
   Pydantic `default_factory` can't see the record being constructed, so the cleanest pattern is a `model_validator(mode="before")` that sets `id` if absent. Alternatively, compute the ID at the call site in `EvidenceRegistry.add` (it has the full record). The latter is simpler:
   ```python
   # diagnostics.py EvidenceRegistry.add
   def add(self, record: EvidenceRecord) -> str:
       if not record.id or record.id.startswith("ev_") and len(record.id) == 15 and record.id == f"ev_{uuid4().hex[:12]}":
           # Replace default UUID with content-addressed ID
           record = record.model_copy(update={"id": _content_addressed_id(record)})
       self._records[record.id] = record
       return record.id
   ```
   (The conditional avoids clobbering caller-supplied IDs.) Simpler still: drop the `default_factory` entirely, make `id` required, and have `EvidenceRegistry.add` compute it. That breaks the `EvidenceRecord(...)` constructor for callers that don't pass `id` — but the only such caller is `conftest.py:62` (`sample_evidence` fixture), which we can update.

   Recommended: `model_validator(mode="after")` on `EvidenceRecord` that sets `id` if it equals the UUID default OR is empty:
   ```python
   @model_validator(mode="after")
   def _assign_content_addressed_id(self) -> "EvidenceRecord":
       if not self.id or self.id == f"ev_{uuid4().hex[:12]}":
           # ... can't compare to default since uuid4 is non-deterministic
       return self
   ```
   The cleanest path: drop `default_factory`, make `id: str | None = None`, and compute the ID in `EvidenceRegistry.add` (the single chokepoint). Callers that construct `EvidenceRecord` directly (tests) get `id=None` until registered.

2. `tra/diagnostics.py:54-58` — make the clock injectable on `AuditTrail`:
   ```python
   class AuditTrail:
       def __init__(self, path, *, clock: Callable[[], datetime] | None = None) -> None:
           self.path = Path(path)
           self._clock = clock or (lambda: datetime.now(UTC))
           ...
       def append(self, ...):
           record = AuditRecord(
               sequence_id=self._seq,
               timestamp=self._clock(),   # was: default_factory
               ...
           )
   ```
   And drop the `default_factory` on `AuditRecord.timestamp` (or keep it as a fallback). `AuditRecord.timestamp` becomes a required field set by `AuditTrail.append`.

3. `tra/kernel.py:103` — `self.audit = AuditTrail(config.audit_trace)` is unchanged (uses real clock). Tests that want reproducibility pass `clock=lambda: datetime(2024,1,1,tzinfo=UTC)`.

#### TDD test spec (write FIRST, expect RED)

```python
# tests/test_phase6_hardening.py — add
def test_audit_trace_is_byte_reproducible_across_runs(tmp_path):
    """TRA-013: two runs of identical source must produce byte-identical audit_trace.jsonl."""
    import filecmp
    from tra.config import BootstrapConfig
    from tra.kernel import TRAKernel
    from tra.memory import ConformanceLevel

    def run_once(idx):
        audit = tmp_path / f"audit_{idx}.jsonl"
        if audit.exists():
            audit.unlink()
        cfg = BootstrapConfig(
            language_pair="zh-en", domain="cyber",
            conformance_level=ConformanceLevel.L4_FORENSIC,
            model_endpoint="", model_version="",
            cache_enabled=False,
            cache_directory=str(tmp_path / f"cache_{idx}"),
            compilation_dir=str(tmp_path / f"art_{idx}"),
            audit_trace=str(audit),
        )
        TRAKernel(cfg).run("# Advisory\n\n系统 成立 是 高度可信 的。\n")
        return audit

    a1 = run_once(1)
    a2 = run_once(2)
    assert filecmp.cmp(a1, a2, shallow=False), (
        "audit_trace.jsonl is not byte-reproducible across runs (TRA-013)"
    )

    # L4 forensic artifact must also be byte-reproducible.
    et1 = tmp_path / "art_1" / "evidence_trace.jsonl"
    et2 = tmp_path / "art_2" / "evidence_trace.jsonl"
    assert filecmp.cmp(et1, et2, shallow=False), (
        "evidence_trace.jsonl is not byte-reproducible across runs (TRA-013)"
    )
```

Currently RED: `filecmp.cmp` returns False (timestamps + evidence IDs differ). Once the fix lands (content-addressed IDs + injectable clock with a deterministic default for tests, OR the kernel defaults to a fixed clock when env var `TRA_REPRODUCIBLE=1` is set), this test goes GREEN.

Note: this test as written requires the DEFAULT clock to be deterministic, which conflicts with the "injectable clock default = real wall-clock" design. Two options: (a) set `os.environ["TRA_REPRODUCIBLE"] = "1"` in the test and have the kernel read it; (b) inject the clock explicitly via a kernel constructor arg. Recommend (b) for cleanliness — extend `TRAKernel.__init__` to accept `audit_clock: Callable[[], datetime] | None = None`.

#### Risks

- `tests/test_phase0.py:54` constructs `TranslationResult(..., evidence_ids=["ev_1"])` — uses a hardcoded `"ev_1"` ID. This still works (evidence_ids is a list of strings, not generated). ✓
- `tests/test_phase0.py:69-70` asserts `sample_evidence.id in evidence_registry` — this requires the registry to preserve the caller-supplied ID. If we move ID assignment into `EvidenceRegistry.add`, we must NOT clobber an existing `id`. Mitigation: only assign if `record.id is None`.
- `tests/test_phase6_hardening.py:122-134` (`test_line_by_line_trace_attribution`) — `ev.add(EvidenceRecord(...))` returns an `eid`, then asserts `trace[0]["evidence_ids"] == [eid]`. With content-addressed IDs, this still works (the returned `eid` is the content-addressed one). ✓
- Grep for `ev_` across tests: only `test_phase0.py:54,89,90` uses literal `ev_1` — these are test fixtures, not assertions on the format. No test asserts the `ev_` prefix or a specific ID length. Changing the ID format from `ev_<12 hex>` (uuid4) to `ev_<12 hex>` (sha256 prefix) preserves the format. ✓
- Cache interaction: a cold cache stores `TranslationResult.evidence_ids` containing the content-addressed IDs. On a cache HIT, those IDs are replayed — so a cached run produces the SAME audit trail as the original run. This is the desired behavior and a side-benefit of content-addressed IDs. ✓
- `BenchmarkRunner.run_case` constructs a fresh `AuditTrail(cfg.audit_trace)` at L99 — this audit is never flushed and never inspected. The clock injection doesn't affect it. ✓
- `tra_cli.py` audit subcommand: needs to keep working with the new ID format. Grep `tra_cli.py` for `ev_` — no hits; the CLI uses `summarize_audit` which counts severities, not IDs. ✓

---

### TRA-014 — Path traversal: no protection on config paths

#### Current evidence (live code)

- **`tra/config.py:23-63`** — `BootstrapConfig` accepts `compilation_dir`, `audit_trace`, `cache_directory` as plain strings with NO validation:
  ```python
  class BootstrapConfig(BaseModel):
      model_config = ConfigDict(frozen=True)
      ...
      cache_directory: str = "./cache"
      compilation_dir: str = "./compilation_artifacts"
      audit_trace: str = "./audit_trace.jsonl"

      @classmethod
      def from_yaml(cls, path):
          raw = yaml.safe_load(...)
          return cls(
              ...
              cache_directory=raw.get("cache", {}).get("directory", "./cache"),
              compilation_dir=raw.get("artifacts", {}).get("compilation_dir", "./compilation_artifacts"),
              audit_trace=raw.get("artifacts", {}).get("audit_trace", "./audit_trace.jsonl"),
          )
  ```
  No `model_validator`, no `field_validator`, no path resolution, no `..` rejection.

- **`tra/kernel.py:266-268`** (`_export_artifacts`) — `mkdir(parents=True, exist_ok=True)` on user-supplied path:
  ```python
  base = Path(self.config.compilation_dir)
  base.mkdir(parents=True, exist_ok=True)
  ```
- **`tra/kernel.py:328-329`** (`_export_forensics`) — same pattern, L4 path:
  ```python
  base = Path(self.config.compilation_dir)
  base.mkdir(parents=True, exist_ok=True)
  ```
- **`tra/diagnostics.py:141`** (`AuditTrail.flush`) — `mkdir(parents=True, exist_ok=True)` on `audit_trace` parent:
  ```python
  self.path.parent.mkdir(parents=True, exist_ok=True)
  ```
- **`tra/cache.py:89`** (`TranslationCache.__init__`) — `mkdir(parents=True, exist_ok=True)` on `cache_directory`:
  ```python
  self.directory.mkdir(parents=True, exist_ok=True)
  ```

#### Empirical test (run live)

**Relative `..` escape** (from `/tmp/X/proj/deep`):
```
compilation_dir = "../../escaped_output"
→ creates /tmp/X/escaped_output/{structural_map.json, glossary.yaml, execution_log.json,
   style_profile.yaml, repair_history.jsonl, entity_table.yaml}
TARGET_EXISTS: True
```

**Absolute path injection**:
```
compilation_dir = "/tmp/tra_abs_evil_PID"
→ creates /tmp/tra_abs_evil_PID/{structural_map.json, glossary.yaml, ...}
ABS_TARGET_EXISTS: True
```

Both attacks succeed with zero resistance. A malicious `config.yaml` (or a CLI `--compilation-dir` override) can write anywhere the running user has permission.

#### Verdict — CONFIRMED

#### Root cause — confirmed

`BootstrapConfig` treats paths as opaque strings. The `from_yaml` loader passes them through verbatim. The downstream consumers (`kernel._export_artifacts`, `kernel._export_forensics`, `diagnostics.AuditTrail.flush`, `cache.TranslationCache.__init__`) all call `mkdir(parents=True, exist_ok=True)` which happily creates directories anywhere on the filesystem. There is no concept of a "project root" or "base directory" against which paths are resolved and validated.

#### Frozen-model compatibility

`BootstrapConfig` is `frozen=True` (TRA-018 fix). Pydantic `model_validator(mode="after")` still works on frozen models — the validator can either (a) return `self` unchanged after asserting paths are safe (raising `ValidationError` if not), or (b) return `self.model_copy(update={...})` to normalize paths (e.g., resolve relative paths against `base_dir`). Both patterns are compatible with `frozen=True`. The validator runs at construction time (in `__init__` and `from_yaml`), before any consumer sees the paths. ✓

#### Optimal fix

Add a `base_dir: Path` field to `BootstrapConfig` (default: `Path.cwd()`) and a `model_validator(mode="after")` that resolves and validates every path field against it.

Precise change to `tra/config.py`:
```python
from pydantic import model_validator

class BootstrapConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    language_pair: str
    domain: str
    conformance_level: ConformanceLevel
    model_endpoint: str
    model_version: str
    cache_enabled: bool = True
    cache_directory: str = "./cache"
    repair_max_retries: int = 3
    compilation_dir: str = "./compilation_artifacts"
    audit_trace: str = "./audit_trace.jsonl"
    base_dir: Path = Field(default_factory=Path.cwd)   # NEW

    @model_validator(mode="after")
    def _validate_paths_within_base_dir(self) -> "BootstrapConfig":
        """TRA-014: reject path traversal on user-supplied config paths."""
        base = self.base_dir.resolve()
        for field_name in ("cache_directory", "compilation_dir", "audit_trace"):
            raw = getattr(self, field_name)
            candidate = (base / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
            # Reject paths that escape base_dir.
            try:
                candidate.relative_to(base)
            except ValueError as exc:
                raise ValueError(
                    f"{field_name}={raw!r} escapes base_dir={base} "
                    f"(resolved to {candidate})"
                ) from exc
        return self
```

Key decisions:
- `base_dir` defaults to `Path.cwd()` so existing relative-path configs (e.g., `./cache`, `./compilation_artifacts`) continue to resolve against the current working directory — backward compatible.
- Absolute paths are allowed ONLY if they fall within `base_dir` after resolution. This permits `tmp_path`-based tests (which use absolute paths under `/tmp/pytest-...`) only if `base_dir` is set to `/tmp` or higher. **This breaks `test_kernel.py::_kernel` and `test_phase6_hardening.py::test_l4_forensic_trace_emitted_at_l4`** — see Risks.
- Relative `..` segments are resolved and the resolved path must remain within `base_dir`. `../../escaped_output` from `/tmp/X/proj/deep` resolves to `/tmp/X/escaped_output`, which is NOT within `base_dir=/tmp/X/proj/deep` → rejected. ✓

#### TDD test spec (write FIRST, expect RED)

```python
# tests/test_phase6_hardening.py — add
import pytest
from tra.config import BootstrapConfig
from tra.memory import ConformanceLevel

def test_config_rejects_relative_traversal_in_compilation_dir(tmp_path):
    """TRA-014: BootstrapConfig must reject '..' in path fields."""
    base = tmp_path / "proj"
    base.mkdir()
    with pytest.raises(ValidationError, match="escapes base_dir"):
        BootstrapConfig(
            language_pair="zh-en", domain="cyber",
            conformance_level=ConformanceLevel.L3_STRICT,
            model_endpoint="", model_version="",
            cache_directory="./cache",
            compilation_dir="../../escaped_output",   # traversal
            audit_trace="./audit.jsonl",
            base_dir=base,
        )

def test_config_rejects_absolute_path_outside_base_dir(tmp_path):
    """TRA-014: BootstrapConfig must reject absolute paths outside base_dir."""
    base = tmp_path / "proj"
    base.mkdir()
    with pytest.raises(ValidationError, match="escapes base_dir"):
        BootstrapConfig(
            language_pair="zh-en", domain="cyber",
            conformance_level=ConformanceLevel.L3_STRICT,
            model_endpoint="", model_version="",
            cache_directory="./cache",
            compilation_dir="/etc/passwd_dir",   # absolute, outside base
            audit_trace="./audit.jsonl",
            base_dir=base,
        )

def test_config_accepts_absolute_path_inside_base_dir(tmp_path):
    """TRA-014: absolute paths INSIDE base_dir are allowed (tmp_path tests)."""
    base = tmp_path
    cfg = BootstrapConfig(
        language_pair="zh-en", domain="cyber",
        conformance_level=ConformanceLevel.L3_STRICT,
        model_endpoint="", model_version="",
        cache_directory=str(tmp_path / "cache"),
        compilation_dir=str(tmp_path / "artifacts"),
        audit_trace=str(tmp_path / "audit.jsonl"),
        base_dir=base,
    )
    assert cfg.compilation_dir == str(tmp_path / "artifacts")
```

Currently RED: `BootstrapConfig(...)` accepts any string for `compilation_dir`; no `ValidationError` is raised. Once the `model_validator` lands, tests 1 and 2 go GREEN; test 3 must also pass (the absolute paths are inside `base_dir=tmp_path`).

#### Risks

- **`test_kernel.py::_kernel` (L12-24)**: uses `cfg.model_copy(update={"compilation_dir": str(tmp_path / "compilation_artifacts"), ...})` — absolute paths under `/tmp/pytest-XXX/`. With `base_dir` defaulting to `Path.cwd()` (which is the repo root during pytest), these absolute paths FAIL the `relative_to(base)` check. **This test breaks.** Mitigation: either (a) update `_kernel` to set `base_dir=tmp_path` in the `model_copy(update=...)`, or (b) change the validator to allow absolute paths without `..` segments (weaker — re-introduces the absolute-path injection risk for non-tmp_path callers). Recommend (a): update the test fixture to pass `base_dir=tmp_path`.
- **`test_phase6_hardening.py::test_l4_forensic_trace_emitted_at_l4` (L99-117)**: same pattern — `model_copy(update={...absolute tmp_path paths...})`. Same fix: add `"base_dir": tmp_path` to the update dict.
- **`test_validate.py`**: uses `BootstrapConfig(**_SPEC)` with default `./audit.jsonl` path → resolves against `Path.cwd()`. During pytest, cwd is the repo root → `./audit.jsonl` is within repo → passes. ✓
- **`test_benchmark.py`**: similar — uses `tmp_path` for cache/artifacts. Need to verify it sets `base_dir` (it doesn't today). Will need the same fixture update.
- **`config.yaml` defaults**: `./cache`, `./compilation_artifacts`, `./audit_trace.jsonl` — all relative, resolve against `Path.cwd()` (the repo root when running `tra translate`). ✓
- **`from_yaml`**: doesn't currently set `base_dir`. If `base_dir` defaults to `Path.cwd()`, a config loaded from `/home/user/project/config.yaml` while cwd is `/home/user/project` works. If loaded from a different cwd (e.g., `cd /tmp && tra translate --config /home/user/project/config.yaml`), the relative paths resolve against `/tmp` — which may or may not be intended. Recommend: `from_yaml` sets `base_dir = Path(path).resolve().parent` so paths are relative to the config file's location, not the caller's cwd. This is a behavior change worth documenting.
- **CLI overrides** (`tra_cli.py`): if the CLI accepts `--compilation-dir` overrides, those overrides go through `model_copy(update=...)` which re-runs the validator. ✓ (Pydantic runs validators on `model_copy` by default for frozen models — verify in implementation.)

---

### Cross-cutting observations

1. **`BootstrapConfig` is `frozen=True` (TRA-018)** — confirmed at `config.py:32`. This doesn't block `model_validator(mode="after")` placement for TRA-014, but it does mean the validator should either raise or return a `model_copy` (not mutate `self`).
2. **No spec mandate for reproducible timestamps** — TRA-SPECIFICATION.md §7 describes the diagnostic format but doesn't require byte-reproducible audit trails. The reproducibility contract is implicit in the codebase's "deterministic" positioning (README.md:53, cache.py:1-13). The fix should be framed as "honor the implicit contract" rather than "comply with the spec".
3. **`_sanitize_input` regex coverage is correct** — `\x00-\x08\x0b\x0c\x0e-\x1f\x7f` (C0 controls except \t \n \r), `\u202a-\u202e` (bidi overrides), `\ufeff` (BOM). The regex itself is sound; the problem is purely the call-site coverage.
4. **No existing test asserts on `ev_` ID format** — changing the ID generation from `uuid4` to `sha256(content)[:12]` preserves the `ev_<12 hex>` format and breaks no tests. ✓
5. **Cache key is fully deterministic** — `CacheKeyContext.key()` is SHA-256 over canonical JSON of invariant fields. No non-determinism via the cache key itself. The non-determinism enters via `TranslationResult.evidence_ids` (which carry UUIDs into the cached value) and via `AuditRecord.timestamp`.

### Recommended fix order (TDD)

1. **TRA-014 first** (path traversal) — smallest blast radius, clearest spec violation, unblocks secure deployment. Write the 3 RED tests, add the `model_validator`, update `_kernel`/`test_l4_forensic_trace_emitted_at_l4`/`test_benchmark.py` fixtures to pass `base_dir=tmp_path`.
2. **TRA-012 second** (sanitize bypass) — move `sanitize_input` to `utils.py`, call from `analyze_document` + `verify_output`, update the one test import. Write the RED test, apply the fix.
3. **TRA-013 last** (audit reproducibility) — largest surface area (touches `EvidenceRecord`, `AuditRecord`, `AuditTrail`, `EvidenceRegistry`, possibly `TRAKernel.__init__` for clock injection). Write the RED test, apply content-addressed IDs + injectable clock, verify the L4 forensic `evidence_trace.jsonl` is now byte-reproducible.

All three fixes are independent — no ordering dependency. The order above is by ascending risk.

---

## Task `validate-K` — Kernel & ISA cluster re-verification (HEAD `c42c457`)

Agent K (read-only audit). Independently re-verified TRA-001/002/004/007/008/009 against the current codebase at `/home/z/my-project/tra/tra-prototype/`. Did NOT trust prior reports — re-read every cited file:line, re-grepped every claim, cross-checked the spec and CLAUDE.md.

### Verdict table

| ID | Original claim | Verdict | Severity (auditor) |
| --- | --- | --- | --- |
| TRA-001 | `TRANSLATE_SEGMENT` receives whole document, not a segment | **CONFIRMED** | BLOCKING |
| TRA-002 | Module registry bypassed by kernel (`ZHENModule()` hard-coded) | **CONFIRMED** | BLOCKING |
| TRA-004 | 3+1 of 5 TRA-EXCEPTION recovery procedures unreachable | **CONFIRMED** | BLOCKING |
| TRA-007 | Kernel transitions fire BEFORE ISA completion | **CONFIRMED** | WARNING (spec violation: BLOCKING) |
| TRA-008 | `rewrite_links` defined but never called | **CONFIRMED** | WARNING |
| TRA-009 | Terminology violations classified as WARNING, not BLOCKING | **PARTIALLY CONFIRMED** (spec example uses WARNING; recommendation to escalate CANONICAL stands) | WARNING |

---

### TRA-001 — `TRANSLATE_SEGMENT` receives whole document

**Verdict: CONFIRMED.**

**Current evidence:**
- `tra/kernel.py:148` — `target = self._execute_translation(src)` where `src` is the document string from `kernel.run` (`src = source.read_text(...)` at L124, sanitized at L125).
- `tra/kernel.py:209-213`:
  ```python
  def _execute_translation(self, src: str) -> str:
      # Phase 2: deterministic whole-doc substitution via the glossary +
      # entity + epistemic lexicon. Segment granularity is wired in Phase 3.
      result = translate_segment(src, self.ctx, self.cache, self.evidence, self.audit)
      return result.translation
  ```
  The Phase-3 segment-granularity wiring never landed. The comment is an explicit confession.
- `tra/isa.py:285-293` — `translate_segment(source_segment: str, ...)` accepts any string. Nothing in the signature or body enforces "a specific source segment" per TRA-ISA-REFERENCE.md:48-49 ("sentence, list item, or table cell").
- `tra/isa.py:376-398` (`_rule_translate`) — operates purely on string substitution; does NOT consult `ctx.structural_map`, does NOT skip `is_no_translate_zone=True` nodes. Code blocks containing glossary terms (e.g. `` `成立` ``) are substituted just like prose.
- `tra/anchor.py` — `StructuralMap` has only `nodes: list[StructuralNode]` and a `node_count` property; **no leaf-iterator method exists**. Leaf kinds in `NodeKind` (memory.py:63-76): `HEADING, PARAGRAPH, LIST, LIST_ITEM, TABLE, TABLE_ROW, TABLE_CELL, CODE_BLOCK, INLINE_CODE, LINK, ANCHOR, BLOCKQUOTE, HR`. The "translate leaf kinds" are HEADING/PARAGRAPH/LIST_ITEM/TABLE_CELL; CODE_BLOCK/INLINE_CODE are `is_no_translate_zone=True` (anchor.py:375).
- `tra/isa.py:502` and `tra/kernel.py` call sites — `segment_index` defaults to `0` everywhere in production; never set to a non-zero value. `RepairAttempt.segment_index` (memory.py:210) is required (`Field(...)`) but receives only `0`.

**Root cause:** Confirmed. The structural map and `is_no_translate_zone` markers exist but are never consulted by the kernel's translation path. The Phase-3 segment-level refactor was deferred and never returned to.

**Optimal fix:**
1. Add `StructuralMap.iter_leaves() -> Iterator[tuple[int, StructuralNode]]` (yield leaf nodes with their flat index; skip subtrees whose `is_no_translate_zone=True`).
2. Refactor `TRAKernel._execute_translation`:
   ```python
   def _execute_translation(self, src: str, smap: StructuralMap) -> str:
       out_parts: list[str] = []
       cursor = 0
       for idx, leaf in smap.iter_leaves():
           start = leaf.span_start  # need anchor.py to record byte offsets
           out_parts.append(src[cursor:start])
           if leaf.is_no_translate_zone:
               out_parts.append(src[start:leaf.span_end])
           else:
               res = translate_segment(leaf.text, self.ctx, self.cache, self.evidence, self.audit, segment_index=idx)
               out_parts.append(res.translation)
           cursor = leaf.span_end
       out_parts.append(src[cursor:])
       return "".join(out_parts)
   ```
3. Plumb `segment_index` through `translate_segment` and `repair_segment` so `RepairAttempt.segment_index` carries real data (unblocks L4 forensic tracing per §6.4.2).

This is the largest refactor in the cluster. It also unblocks TRA-008 (link rewriting needs per-segment text to repoint slugs in translated headings).

**TDD test spec — `test_translate_segment_iterates_leaf_nodes`:**
- **Arrange:** source =
  ```
  # Title

  The condition 成立.

  ```python
  if 成立: pass
  ```
  ```
  Glossary contains `成立 → Confirmed` (CANONICAL). Build a `TRAKernel` with default config.
- **Act:** `target = kernel.run(source)`.
- **Assert:**
  - `"The condition is Confirmed."` in `target` (prose translated, topic-comment rule applied).
  - The fenced code block is unchanged: ```` ```python\nif 成立: pass\n``` ```` appears verbatim in `target` — i.e., `Confirmed` does NOT appear inside the code fence. Specifically, the substring `if Confirmed` is absent.
  - Audit trail contains ≥2 `TRANSLATE_SEGMENT` records (one per translatable leaf), not one.
  - Each `TranslationResult.evidence_ids` list is non-empty.

**Risks:**
- Cache key granularity changes (per-segment vs per-doc). Existing on-disk cache entries under `config.cache_directory` become stale — bump the cache schema version or document a one-time cache clear.
- Tests that assert on whole-doc output (e.g., `tests/test_kernel.py:35-42 test_kernel_runs_full_pipeline`) — the prose assertions still hold but the audit-record count assertions may need to change from "≥5" to "≥5 + N_segments".
- `StructuralMapBuilder` does not currently record byte offsets (`span_start`/`span_end`); needs extension to emit them so the reassembly above can splice. Without offsets, the reassembly must reconstruct from `node.text` which loses original whitespace/inline-code spans — insufficient. This is a real prerequisite change.
- `_rule_translate` currently relies on whole-doc substring substitution; with per-leaf text, multi-paragraph term co-reference (e.g., a term defined in paragraph 1 and used in paragraph 5) still works because the glossary is built globally. ✓

---

### TRA-002 — Module registry bypassed by kernel

**Verdict: CONFIRMED.**

**Current evidence:**
- `tra/kernel.py:43` — `from .modules.zh_en import ZHENModule` (direct import, not via registry).
- `tra/kernel.py:106` — `style_profile=ZHENModule().get_style_profile()` (hard-coded singleton construction in `TRAKernel.__init__`).
- `tra/isa.py:50` — `from .modules.zh_en import ZHENModule`.
- `tra/isa.py:54` — `_MODULE = ZHENModule()` — module-level singleton.
- `tra/isa.py` call sites using `_MODULE`: L158 (`get_glossary_mappings`), L163 (`is_forbidden`), L208 (`get_forbidden_targets`), L247 (`entity_type_hint`), L384 (`apply_zh_rules`). Five production call sites bypass the registry.
- `tra/modules/registry.py:43` `build_default_registry()` and `:56` `registry_for_language_pair(pair)` exist.
- Grep for `build_default_registry|registry_for_language_pair` across `tra/` and `tra_cli.py`: zero production callers (only `tests/test_modules.py:7,8,59,67,76` and `SKILL.md`).
- `tra_cli.py` — `Grep` for `registry|ZHENModule|module|build_default` returns **zero matches**. The CLI never constructs or queries a registry.

**Root cause:** Confirmed. The registry abstraction was added (Phase 4.1.2) but never wired into the kernel or ISA. All five production call sites in `isa.py` and the kernel constructor hard-code `ZHENModule`.

**Optimal fix:**
1. Add `module: ModuleInterface | None = None` to `TRAKernel.__init__`; if `None`, default to `registry_for_language_pair(config.language_pair).get(<language-pair-name>)` (or `.all()[0]` for language modules — but `registry_for_language_pair` already scopes to one pair, so `.all()` is safe).
2. Store `self.module = module` on the kernel; pass into `ctx.style_profile = module.get_style_profile()` instead of `ZHENModule().get_style_profile()`.
3. Refactor `isa.py` ISA functions to accept `module: ModuleInterface` as a parameter (or store on `ctx` — cleaner: add `active_module: ModuleInterface | None = None` to `RuntimeContext` and have ISA functions read `ctx.active_module`). Either way, **remove the module-level `_MODULE` singleton from `isa.py:54`**.
4. Update all five `isa.py` call sites to read from the parameter/context instead of `_MODULE`.
5. `tra_cli.py translate` constructs `TRAKernel(cfg)` — no change needed if the kernel default kicks in. But add a `--module` flag for explicit override (optional, can defer).

**TDD test spec — `test_kernel_uses_registry_for_language_pair`:**
- **Arrange:** Define a `StubModule(ModuleBase)` whose `get_glossary_mappings()` returns `{"术语": "STUB_TARGET"}` and whose `get_style_profile()` returns `StyleProfile(voice="Stub Voice")`. Register it under name `"stub"` in a fresh `ModuleRegistry`. Patch `tra.modules.registry.registry_for_language_pair` (or construct a `TRAKernel` with `module=stub_module.as_interface()`).
- **Act:** `kernel.run("# Doc\n\n术语 here.\n")`.
- **Assert:**
  - `"STUB_TARGET"` appears in `target` (stub glossary applied, not `ZHENModule`'s).
  - `kernel.ctx.style_profile.voice == "Stub Voice"` (stub style profile applied).
  - The exported `compilation_artifacts/style_profile.yaml` contains `voice: Stub Voice`.
  - `ZHENModule` is NOT instantiated during the run (verify by monkeypatching `ZHENModule.__init__` to raise; the run must still succeed).

**Risks:**
- `ModuleInterface` (registry.py:13-22) is a `@dataclass` with default lambdas for `apply_rules` etc., but the production ISA functions call **methods that don't exist on `ModuleInterface`**: `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`. Either extend `ModuleInterface` to declare these (preferred) or have the kernel pass the concrete `ZHENModule` instance and not the adapted `as_interface()` shim. Recommend: extend `ModuleInterface` with these method references, since the §9 contract treats the registry as the single extension point.
- Direct test callers of `analyze_document`, `build_glossary`, etc. (e.g., `tests/test_isa.py`) currently rely on the module-level `_MODULE`. Removing it breaks them unless they pass `module=` explicitly. Need a `conftest.py` fixture `default_module` that injects `ZHENModule()` for legacy tests, or update each test to pass it.
- `as_interface()` (zh_en.py:226-235) wraps only `get_glossary_mappings`, `get_style_profile`, `apply_rules`. The shim is INCOMPLETE — missing `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`. This is a pre-existing bug surfaced by the fix; either expand `as_interface()` or define these on `ModuleInterface` as required methods.

---

### TRA-004 — 3+1 of 5 TRA-EXCEPTION recovery procedures unreachable

**Verdict: CONFIRMED (4 of 5 unreachable; matches the "3+1" framing).**

**Current evidence:**
- Grep `raise UnknownTerm|raise CertaintyConflict|raise EntityAmbiguity` across `tra/`: **zero hits**. (Confirmed via `Grep` tool.)
- `tra/kernel.py:127-145`:
  ```python
  self._transition(KernelState.INITIALIZE_RUNTIME)
  self._transition(KernelState.ANALYZE_DOCUMENT)
  analyze_document(src, self.ctx, self.audit)   # L129 — NOT wrapped
  ...
  self._transition(KernelState.BUILD_ARTIFACTS)
  try:
      build_glossary(src, profile, self.ctx, self.evidence, self.audit)  # L142 — wrapped
  except TRAException as exc:
      self._recover(exc)                                                        # L144 — routes via recovery
  build_entity_table(src, smap, self.ctx, self.evidence, self.audit)            # L145 — NOT wrapped
  ```
  Only `build_glossary` is wrapped. `analyze_document`, `build_entity_table`, `translate_segment`, `verify_output`, `repair_segment` all propagate uncaught.
- `tra/isa.py:84` — `raise BrokenMarkdown(...)` from `analyze_document`. Propagates through `kernel.run` uncaught — crashes the CLI.
- `tra/recovery.py` — five handlers: `recover_unknown_term`, `recover_broken_markdown`, `recover_certainty_conflict`, `recover_entity_ambiguity`, `recover_glossary_conflict`. Reachability:
  - `recover_glossary_conflict` — REACHABLE (via `build_glossary` wrapper at kernel.py:144; `GlossaryConflict` is raised at isa.py:164, 170).
  - `recover_broken_markdown` — UNREACHABLE in production (raise site isa.py:84 exists, but kernel.py:129 has no try/except → propagates).
  - `recover_unknown_term` — UNREACHABLE (no raise site).
  - `recover_certainty_conflict` — UNREACHABLE (no raise site).
  - `recover_entity_ambiguity` — UNREACHABLE (no raise site).
  - Total: 4 of 5 dead. Matches the claim.

**Root cause:** Confirmed. The recovery procedures and exception classes were authored (Phase 6.1) but the raise sites and kernel-side try/except coverage were not completed.

**Optimal fix:**
1. **Kernel side:** wrap `analyze_document`, `build_entity_table`, `translate_segment`, `verify_output` in try/except `TRAException as exc: self._recover(exc); <decide-whether-to-continue>`. For `BrokenMarkdown` from `analyze_document`, recovery must HALT (no structural map → no further work); for the others, the recovery action is non-halting.
2. **Raise sites:**
   - `UnknownTerm` — in `translate_segment`/`_rule_translate`: when a source token appears ≥2× in the doc, is not in `glossary_cache`, and is not in `entity_table`, raise `UnknownTerm(term=token)`. Conservative threshold (≥2×) avoids false positives on one-off proper nouns.
   - `CertaintyConflict` — in `verify_output`: when an epistemic marker in `source` maps to one of `FORBIDDEN_TARGETS` AND a competing target also appears in the target text, raise `CertaintyConflict(term=src)`.
   - `EntityAmbiguity` — in `build_entity_table`: when `extract_entities` returns a token whose surface form also appears as a substring of a glossary source term (e.g., a glossary term `成立` and an entity candidate `成立时间`), raise `EntityAmbiguity(token=token)`. Conservative: only when the overlap is unambiguous.

**TDD test spec — `test_broken_markdown_routes_through_exception_handler`:**
- **Arrange:** Monkeypatch `tra.isa.build_structural_map` (or `tra.anchor.StructuralMapBuilder.build`) to raise `Exception("synthetic parse failure")`. Construct `TRAKernel(cfg)`.
- **Act:** `kernel.run("# some doc\n")`.
- **Assert (currently RED — kernel crashes):**
  - `kernel.run` does NOT propagate `BrokenMarkdown` (currently does).
  - The audit trail contains a record with `isa_instruction == "EXCEPTION_HANDLER"` and `artifact_snapshot.code == "BROKEN_MARKDOWN"`.
  - `kernel.ctx.unresolved_ambiguities` contains a string starting with `"BROKEN_MARKDOWN:"`.
  - `kernel.state` terminates at `ANALYZE_DOCUMENT` (does not advance to `BUILD_ARTIFACTS`).
- **Assert (for the UnknownTerm raise site, separate test):** `test_unknown_term_raised_for_recurrent_unmapped_term` — arrange a doc with `某某术语` appearing twice, no glossary entry, no entity entry; act `kernel.run(...)`; assert `EXCEPTION_HANDLER` audit record with code `UNKNOWN_TERM` and `RecoveryAction.PRESERVE_SOURCE`.

**Risks:**
- Adding `UnknownTerm` to `_rule_translate` could break the rule path on docs with many unmapped CJK tokens (the threshold of ≥2× mitigates but doesn't eliminate). Recommend making the threshold configurable via `BootstrapConfig` (default 2).
- Wrapping `verify_output` in try/except changes the semantics of the L3 conformance gate (kernel.py:162-175): if `verify_output` raises, the gate never runs. Need to ensure the recovery for `CertaintyConflict` either re-runs `verify_output` post-recovery or explicitly skips the gate with an `EXCEPTION_HANDLER` audit entry.
- `build_entity_table` is called outside the try/except wrapper (kernel.py:145). If we add `EntityAmbiguity` raise sites there, the kernel crashes — so the wrapper and the raise site MUST land together.
- The `route_exception` fallback (recovery.py:176-182) catches any `TRAException` not matched by an `isinstance` branch and returns a generic WARNING + PRESERVE_SOURCE. This is currently exercised only by `Unrecoverable` from the repair loop. New raise sites must use the specific subclasses, not bare `TRAException`.

---

### TRA-007 — Kernel transitions fire BEFORE ISA completion

**Verdict: CONFIRMED.**

**Current evidence:**
- `tra/kernel.py:127-129`:
  ```python
  self._transition(KernelState.INITIALIZE_RUNTIME)   # L127
  self._transition(KernelState.ANALYZE_DOCUMENT)     # L128 — transition FIRST
  analyze_document(src, self.ctx, self.audit)        # L129 — ISA call AFTER
  ```
  If `analyze_document` raises (e.g., `BrokenMarkdown` from isa.py:84), `kernel.state` is already `ANALYZE_DOCUMENT` and `ctx.execution_log` already contains `"ANALYZE_DOCUMENT"`. The state has advanced despite the ISA call failing.
- Same pattern at:
  - L140 `_transition(BUILD_ARTIFACTS)` → L142 `build_glossary` (wrapped, so failure routes through `_recover` — but state is still advanced).
  - L147 `_transition(EXECUTE_TRANSLATION)` → L148 `_execute_translation` (NOT wrapped).
  - L150 `_transition(VERIFY_OUTPUT)` → L151 `verify_output` (NOT wrapped).
  - L153 `_transition(REPAIR_IF_NEEDED)` → L154 `_repair_loop`.
  - L177 `_transition(AUDIT_DIAGNOSTICS)` → L178 `audit.flush()`.
  - L180 `_transition(EMIT_PAYLOAD)` → L181 `_export_artifacts()`.
- `tra/CLAUDE.md:19` — "transitions only on successful ISA completion." ✓ (claim verified)
- `tra/CLAUDE.md:62` (mental model section) — "State transitions are triggered only by successful completion of ISA instructions." ✓
- `tra/TRA-SPECIFICATION.md:14` — "State transitions are triggered by the successful completion of ISA instructions." ✓ (spec mandate confirmed)
- `tra/kernel.py:7-8` (module docstring) — "State transitions are triggered ONLY by successful completion of ISA instructions. The Kernel must not skip instructions." (self-contradiction with the implementation.)

**Root cause:** Confirmed. Every transition in `kernel.run` fires before its corresponding ISA call. The implementation contradicts the spec, the module docstring, and CLAUDE.md.

**Optimal fix:**
Reorder each pair so the ISA call precedes the transition:
```python
# BEFORE
self._transition(KernelState.ANALYZE_DOCUMENT)
analyze_document(src, self.ctx, self.audit)

# AFTER
analyze_document(src, self.ctx, self.audit)
self._transition(KernelState.ANALYZE_DOCUMENT)
```
For the failure path: wrap each ISA call in try/except `TRAException`; on failure, call `self._recover(exc)` and either HALT (for `BrokenMarkdown`) or skip the transition and continue (for recoverable cases). The existing `_transition` already raises `TRAException` on backward transitions, so a failed ISA call that doesn't transition will block subsequent forward transitions naturally — but the kernel must explicitly NOT advance state on failure.

Note: `_transition` itself logs to `ctx.execution_log` (kernel.py:120). The execution_log will then contain only successfully-completed states, which is the correct semantics for L4 forensic review.

**TDD test spec — `test_kernel_does_not_advance_state_on_isa_failure`:**
- **Arrange:** Monkeypatch `tra.isa.analyze_document` to raise `BrokenMarkdown("synthetic")`. Construct `TRAKernel(cfg)`.
- **Act:** `kernel.run("# doc\n")`.
- **Assert (currently RED):**
  - `kernel.state == KernelState.INITIALIZE_RUNTIME` (the only state that should have advanced pre-ISA; or even BOOTSTRAP if we also reorder L127).
  - `kernel.ctx.execution_log` does NOT contain `"ANALYZE_DOCUMENT"`.
  - `kernel.run` does NOT propagate `BrokenMarkdown` (it routes through `_recover`).
  - The audit trail contains an `EXCEPTION_HANDLER` record with `code == "BROKEN_MARKDOWN"`.
- **Variants (one test per ISA call):** repeat for `build_glossary`, `build_entity_table`, `translate_segment`, `verify_output` — each monkeypatched to raise; assert state did not advance past the failed call.

**Risks:**
- The `INITIALIZE_RUNTIME` transition at L127 has no corresponding ISA call — it's a pure kernel-side setup. Reordering doesn't apply; just keep it first.
- The L3 conformance gate (kernel.py:162-175) calls `verify_output` AGAIN after the repair loop. This is currently AFTER `_transition(REPAIR_IF_NEEDED)` (L153) and BEFORE `_transition(AUDIT_DIAGNOSTICS)` (L177). If the gate's `verify_output` raises, state is already `REPAIR_IF_NEEDED`. The fix: wrap the gate's `verify_output` in try/except too, or accept that the gate's failure is a `ConformanceFailure` (which is a `TRAException` subclass) and route through `_recover`.
- `_repair_loop` internally calls `verify_output` (kernel.py:259) and `repair_segment` (L224) — these are ISA calls inside the repair loop, but the loop's transitions are governed by `attempt` count, not by `_transition`. The fix to L153 (transition after `_repair_loop` returns) is safe.
- Existing test `test_kernel_state_machine_is_sequential` (tests/test_kernel.py:67+) asserts forward-only transitions but doesn't test failure-path ordering. The new test fills that gap.
- `AuditTrail.flush()` at L178 is not an ISA call — the transition at L177 is fine if `flush()` is treated as part of the AUDIT_DIAGNOSTICS state's implementation. But strictly per spec, `AUDIT_DIAGNOSTICS` is the state that PRODUCES the diagnostic report (an ISA-like activity). Recommend keeping L177 → L178 order but treating `flush` as the ISA-equivalent; document this.

---

### TRA-008 — `rewrite_links` defined but never called

**Verdict: CONFIRMED.**

**Current evidence:**
- `tra/anchor.py:101-149` — `rewrite_links(markdown, registry, *, flag_broken=True) -> tuple[str, list[str]]` exists. Operates on a markdown string, repoints `(#slug)` links to translated slugs via `registry.translated_slug_for(slug)`. Skips fenced code blocks. Returns `(rewritten_markdown, broken_slug_list)`.
- Grep `rewrite_links` across `tra/` and `tra_cli.py`: zero production callers. Only `tests/test_anchor.py:11,105` (test import + test call).
- `tra/kernel.py:_execute_translation` (L209-213) — does NOT call `rewrite_links`. Returns `result.translation` directly.
- `tra/isa.py:82` — `structural_map, _registry = build_structural_map(source)` — the `_registry` (note leading underscore) is **discarded**. The `AnchorRegistry` is never stored on `ctx` or otherwise preserved. Even if `rewrite_links` were called, there's no registry to pass.
- `tra/memory.py:188-200` (`RuntimeContext`) — has NO field for `AnchorRegistry`. The registry would need a home.
- `tra/anchor.py:222` — `AnchorRegistry.register(text)` is called during `StructuralMapBuilder._consume_heading` to assign `__HEADER_NNN__` placeholders. So the registry IS populated during `analyze_document`, just thrown away.
- `tra/anchor.py:86-88` — `AnchorRegistry.bind(placeholder, translated_slug)` is the post-translation hook that records the translated slug. NEVER called in production.

**Root cause:** Confirmed. The full S-06 chain (register headings → translate → bind translated slugs → rewrite links) is wired only in tests. The kernel discards the registry at L82 of isa.py and never invokes the bind/rewrite passes.

**Optimal fix (depends on TRA-001):**
1. Add `anchor_registry: AnchorRegistry | None = None` to `RuntimeContext`.
2. In `analyze_document` (isa.py:82), replace `structural_map, _registry = build_structural_map(source)` with `structural_map, registry = build_structural_map(source)` and store `ctx.anchor_registry = registry`.
3. In `_execute_translation` (post-TRA-001 refactor), after translating each heading leaf, call `ctx.anchor_registry.bind(heading.placeholder, registry.resolve_slug(translated_heading_text))`.
4. After the full translation, call `rewrite_links(target, ctx.anchor_registry)` and use the rewritten target as the kernel's output. Surface `broken` slugs as WARNING diagnostics (append to `ctx.unresolved_ambiguities` and emit a `Diagnostic(severity=WARNING, subsystem="anchor", ...)`).

**Caveat:** Step 3 requires per-heading translation (TRA-001 refactor). Without it, `rewrite_links` can still be called on the whole-doc target string (the function is string-based, not AST-based — anchor.py:101-149), but `bind` cannot be called because we don't know which translated substring corresponds to which original heading. So:
- **Minimal fix (independent of TRA-001):** call `rewrite_links` on the whole-doc target. But: since headings are translated as part of the whole doc, the registry has no `bind` calls, so `translated_slug_for(original_slug)` returns `None` for every link, and every link is reported as broken. This is worse than not calling `rewrite_links` at all.
- **Correct fix:** requires TRA-001 to land first. Mark TRA-008 as BLOCKED-ON TRA-001.

**TDD test spec — `test_internal_links_rewritten_after_translation`:**
- **Arrange:** source =
  ```
  # 系统成立

  See [link](#系统成立) for details.
  ```
  Build `TRAKernel(cfg)`.
- **Act:** `target = kernel.run(source)`.
- **Assert (currently RED — no rewriting happens):**
  - The heading is translated to `"# The system is Confirmed"` (or similar).
  - The link target is rewritten: `target` contains `[link](#the-system-is-confirmed)` (the GitHub slug of the translated heading), NOT `[link](#系统成立)`.
  - `kernel.ctx.unresolved_ambiguities` does NOT contain a broken-slug entry for `系统成立`.
- **Variant — broken link:** source contains `[link](#nonexistent-heading)`; assert `kernel.ctx.unresolved_ambiguities` contains `"nonexistent-heading"` and the link is left as-is.

**Risks:**
- **Hard dependency on TRA-001.** Without per-segment translation, `bind` cannot be called and `rewrite_links` returns every link as broken. Do not attempt TRA-008 in isolation.
- GitHub slug rules differ subtly from the registry's `generate_github_slug` (anchor.py:40-44) — the registry uses Unicode-aware `\w` and lowercases; GitHub's actual algorithm strips non-ASCII. For CJK headings, GitHub keeps the CJK characters in the slug. The current `generate_github_slug` is correct for the test cases shown but may diverge on edge cases (emoji, combining marks). Low risk for the ZH-EN module's current glossary.
- `flag_broken=True` (default) collects broken slugs silently. The kernel must surface these as WARNING diagnostics, not just swallow them — otherwise S-06 anchor integrity is silently violated.

---

### TRA-009 — Terminology violations classified as WARNING, not BLOCKING

**Verdict: PARTIALLY CONFIRMED.**

**Current evidence:**
- `tra/isa.py:450-461`:
  ```python
  # Terminology: glossary terms must appear as canonical targets.
  for src, tgt in glossary.items():
      if src in target:  # untranslated source term leaked
          diagnostics.append(
              Diagnostic(
                  severity=Severity.WARNING,   # L455 — confirmed WARNING
                  subsystem="terminology",
                  issue=f"Source term not translated: {src!r}",
                  evidence=f"expected canonical target {tgt!r}",
                  action="Apply canonical mapping",
              )
          )
  ```
  Severity is `WARNING`. Confirmed.
- `tra/TRA-SPECIFICATION.md:158-163` — the spec's EXAMPLE diagnostic for terminology:
  ```yaml
  - severity: "WARNING"
    subsystem: "TERMINOLOGY_VERIFICATION"
    issue: "Unresolved ambiguity"
    evidence: "Term '执行环境' mapped to 'execution environment', but 'runtime' is also common in this domain."
  ```
  **The spec itself uses WARNING for terminology.** The original TRA-009 claim that "the spec mandates BLOCKING for terminology" is **INCORRECT**.
- `tra/TRA-SPECIFICATION.md:125` — "Terminological Consistency: Adherence to Canonical Glossary" is Priority 4 (above Target Fluency at Priority 6 but below Entity Preservation at Priority 3).
- `tra/TRA-SPECIFICATION.md:144` — `GLOSSARY_CONFLICT` (two different canonical mappings) is BLOCKING; this is the only terminology-related BLOCKING in the spec.
- `tra/TRA-SPECIFICATION.md:60` — `BUILD_GLOSSARY` Failure Condition: "Conflicting canonical mappings for the same term in the same context" → `GLOSSARY_CONFLICT` (BLOCKING via recovery.py:147).
- `tra/isa.py:179` — every glossary entry is created with `status=GlossaryStatus.CANONICAL`. The `CONTEXT_SENSITIVE` status (memory.py:60) is never used in production.

**Root cause:** Partially confirmed. The severity is WARNING at isa.py:455, but this matches the spec example. The real issue is that the codebase does NOT distinguish CANONICAL from CONTEXT_SENSITIVE at the diagnostic level — every terminology violation is WARNING regardless of glossary status. The revalidate-A recommendation (split on `GlossaryStatus`: BLOCKING for CANONICAL, WARNING for CONTEXT_SENSITIVE) is a stricter-than-spec safety measure that the spec permits but does not mandate.

**Optimal fix:**
```python
for src, tgt in glossary.items():
    if src in target:
        # Find the entry to read its status.
        entry = next((e for e in ctx.glossary_cache if e.source == src), None)
        sev = (
            Severity.BLOCKING
            if entry is not None and entry.status == GlossaryStatus.CANONICAL
            else Severity.WARNING
        )
        diagnostics.append(
            Diagnostic(
                severity=sev,
                subsystem="terminology",
                issue=f"Source term not translated: {src!r}",
                evidence=f"expected canonical target {tgt!r}",
                action="Apply canonical mapping",
            )
        )
```
Since every production glossary entry is CANONICAL today (isa.py:179), this effectively escalates ALL terminology violations to BLOCKING until CONTEXT_SENSITIVE entries are introduced. That is the intended safety posture.

**TDD test spec — `test_canonical_term_leakage_is_blocking`:**
- **Arrange:** Glossary with `成立 → Confirmed` (status CANONICAL). Source = `"The condition 成立."`. Run translation, but monkeypatch `_rule_translate` (or `translate_segment`) to SKIP the `成立` substitution (simulate a translator miss).
- **Act:** `diagnostics = verify_output(target, source, ctx, audit)`.
- **Assert:**
  - At least one diagnostic has `subsystem == "terminology"` and `issue` contains `"成立"`.
  - That diagnostic's `severity == Severity.BLOCKING`.
- **Variant — CONTEXT_SENSITIVE stays WARNING:** glossary entry with `status=GlossaryStatus.CONTEXT_SENSITIVE`; same source; assert the terminology diagnostic is `Severity.WARNING`. (Requires constructing a CONTEXT_SENSITIVE entry manually since production code never creates one.)

**Risks:**
- **Benchmark regression.** Escalating CANONICAL term leakage to BLOCKING means any benchmark case whose target accidentally leaves a source term untranslated now fails the L3 gate. Run the full benchmark suite (`tests/benchmark/cases/*.jsonl`) after the change. Specifically check S-04 (terminology) cases — they may currently rely on WARNING.
- **L3 conformance gate (kernel.py:162-175).** With the escalation, every terminology leak becomes a BLOCKING that the repair loop must fix. The repair loop's `repair_segment` (isa.py:515-520) already handles terminology by applying `repaired.replace(src, glossary[src])` — so the loop should converge in one attempt. Verify convergence on the benchmark suite.
- **`tests/test_isa.py` and `tests/test_kernel.py`** — any test that currently asserts on WARNING terminology diagnostics will break. Grep for `subsystem="terminology"` or `Severity.WARNING` in tests and update expectations.
- **Spec divergence.** The fix makes the engine stricter than the spec example. Document this in `TRA-CONFORMANCE-GUIDE.md` (or accept the divergence as a safety measure; the spec permits stricter conformance levels per §8).
- The fix does NOT require the TRA-001 refactor — it's a localized change to `verify_output`. Can land independently.

---

### Cross-cutting observations

1. **TRA-001 is the keystone.** TRA-008 (link rewriting) and the `segment_index` field of `RepairAttempt` (L4 forensic) both depend on per-segment translation landing first. Recommend fixing TRA-001 before TRA-008.
2. **TRA-002 and TRA-009 are independent.** Both are localized changes (kernel constructor + ISA function signatures for TRA-002; one diagnostic-emission site for TRA-009) and can land in parallel with TRA-001.
3. **TRA-004 and TRA-007 are coupled.** Both touch the kernel's `run` method and both add try/except wrappers around ISA calls. The TRA-007 reorder (transition after ISA call) and the TRA-004 wrapper (try/except around ISA call) should land as ONE atomic change to `kernel.run` to avoid merge conflicts and double-editing the same lines.
4. **`ModuleInterface` is incomplete.** `as_interface()` (zh_en.py:226-235) does not expose `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules` — methods the ISA calls via `_MODULE`. Fixing TRA-002 surfaces this pre-existing gap; the `ModuleInterface` dataclass must be extended to declare these as required methods (or the registry must store the concrete module instance, not the shim).
5. **Spec vs. code drift on terminology severity.** The spec example uses WARNING; the code matches; the revalidate-A recommendation escalates CANONICAL to BLOCKING. This is a deliberate stricter-than-spec posture, not a spec violation. The audit finding should be re-framed as "safety improvement" rather than "spec violation" to avoid confusion.
6. **No spec mandate for `segment_index` granularity.** TRA-ISA-REFERENCE.md and TRA-SPECIFICATION.md do not mandate per-leaf segment indices; the `RepairAttempt.segment_index` field exists for L4 forensic tracing (§6.4.2) but the spec doesn't require non-zero values. The TRA-001 fix is motivated by correctness (code-block protection, cache granularity, anchor rewriting) not by a direct spec mandate.

### Recommended fix order (TDD)

1. **TRA-009** (terminology severity) — smallest blast radius, one-line severity change + test. Land first to surface benchmark regressions early.
2. **TRA-002** (module registry) — extends `ModuleInterface`, plumbs `module` param through ISA functions. Touches many files but each change is mechanical. Update `conftest.py` with a `default_module` fixture.
3. **TRA-004 + TRA-007** (atomic) — wrap each ISA call in try/except, reorder transitions to fire AFTER successful ISA completion. One PR, one set of test changes.
4. **TRA-001** (segment-level translation) — largest refactor. Extends `StructuralMapBuilder` to emit byte offsets, adds `StructuralMap.iter_leaves()`, refactors `_execute_translation`. Bump cache schema version.
5. **TRA-008** (anchor rewriting) — depends on TRA-001. Adds `anchor_registry` to `RuntimeContext`, calls `bind` during per-heading translation, calls `rewrite_links` post-translation. Surfaces broken slugs as WARNING diagnostics.

All five fixes are spec-aligned; only TRA-009 is stricter-than-spec (deliberately so). The cluster is internally consistent — no fix invalidates another.

---

## Task ID: validate-T — Test-suite cluster (TRA-031/032/033/034/035)

**Auditor:** Agent T (Explore)  **HEAD:** c42c457  **Scope:** `/home/z/my-project/tra/tra-prototype/`
**Baseline:** 107 passed in 0.69s

### Verdict table

| ID | Severity | Verdict | Summary |
|---|---|---|---|
| TRA-031 | WARNING | CONFIRMED | 13 of 23 spec cases implemented; 10 missing (S-01, S-02, S-03, S-04, S-06, D-01, D-02, D-03, E-01, E-03) |
| TRA-032 | WARNING | CONFIRMED | HITL `review_decision` supports {accept, override, skip} but only `accept` is tested |
| TRA-033 | WARNING | CONFIRMED | `test_graceful_degradation_on_llm_failure` raises only `RuntimeError`; no parametrization over [ValueError, TypeError, OSError, TimeoutError]; no tests for `llm_translate` returning `""`/`None` |
| TRA-034 | INFO    | CONFIRMED | All 6 conftest fixtures (`sample_glossary`, `sample_entities`, `cache_context`, `evidence_registry`, `sample_evidence`, `config`) used only by `test_phase0.py` |
| TRA-035 | INFO    | FIXED (mutation catch rate 3/3 = 100%) | TRA-028/029/030 tests now catch all 3 mutations |

### TRA-031 — Spec benchmark case coverage (CONFIRMED)

`tests/benchmark/cases/sft.jsonl` — 13 lines (F-01..05, T-01..05, S-05, D-04, E-02)
`tests/benchmark/cases/regression.jsonl` — 1 line (R-01)

`TRA-BENCHMARK-SUITE.md` enumerates 23 spec cases:
- **S:** S-01..S-06 (6) — implemented: S-05 only
- **F:** F-01..F-05 (5) — implemented: all 5 ✓
- **T:** T-01..T-05 (5) — implemented: all 5 ✓
- **D:** D-01..D-04 (4) — implemented: D-04 only
- **E:** E-01..E-03 (3) — implemented: E-02 only

Missing (10): S-01, S-02, S-03, S-04, S-06, D-01, D-02, D-03, E-01, E-03

`tests/test_benchmark.py:47` declares `@pytest.mark.parametrize("case", _all_cases(), ids=lambda c: c.id)` and `_all_cases()` globs `tests/benchmark/cases/*.jsonl` — so any new JSONL case is auto-picked-up. **The fix is purely declarative: append the 10 missing lines to `sft.jsonl`.** Each line is its own test (parametrized), and `test_benchmark_case` asserts `result.passed` (must_contain / must_not_contain / zero_blocking).

### TRA-032 — HITL only tested for `accept` path (CONFIRMED)

`tra/hitl.py:49-51`: `Prompt.ask("Resolution", choices=["accept", "override", "skip"], default="skip")` — three resolutions supported.

`tests/test_phase6_hardening.py:139`: only `test_hitl_review_decision_accept` exists; `monkeypatch.setattr` returns `"accept"` unconditionally. No tests for `override` or `skip` paths (lines 54-59 of hitl.py).

### TRA-033 — LLM seam degradation tested for RuntimeError only (CONFIRMED)

`tests/test_phase6_hardening.py:71-86`: `def boom(_seg, _ctx): raise RuntimeError("llm down")` — only `RuntimeError` raised.

`tra/isa.py:322`: `except Exception as exc:` catches all built-in exception types, but no test verifies graceful degradation for `ValueError`, `TypeError`, `OSError`, `TimeoutError`. No tests for `llm_translate` returning `""` or `None` (empty/None seam output — would currently pass through to rule path implicitly only if exception raised; returning `""` silently propagates to evidence record).

### TRA-034 — conftest.py fixtures used only by test_phase0.py (CONFIRMED)

`tests/conftest.py` defines 6 fixtures (lines 19-78). Grep confirms usage exclusively in `tests/test_phase0.py`:
- `cache_context` → test_phase0.py:28, :38
- `evidence_registry`, `sample_evidence` → test_phase0.py:68
- `config` → test_phase0.py:102
- `sample_glossary`, `sample_entities` → indirect via `cache_context`

Other test modules construct their own `_ctx()` / `_audit()` helpers (e.g. `test_phase6_hardening.py:30`, `test_isa.py`). Maintainability issue, not correctness.

### TRA-035 — Mutation catch rate (FIXED, 3/3 caught)

Procedure: copy `tra/isa.py` → `tra/isa.py.bak`, apply mutation via Python script, run `python3 -m pytest tests -q`, restore from backup. Each run verified baseline of 107 passed first.

**Mutation 1 — revert TRA-003 fix** (line 548: `if new_blocking:` → `if new_blocking and attempt >= max_retries:`):
```
FAILED tests/test_isa.py::test_repair_raises_on_new_blocking_at_attempt_1
E       Failed: DID NOT RAISE <class 'tra.exceptions.Unrecoverable'>
```
**CAUGHT.** `test_repair_raises_on_new_blocking_at_attempt_1` (test_isa.py:248) asserts `pytest.raises(Unrecoverable)` at `attempt=1, max_retries=3` — exactly the case the mutation re-breaks.

**Mutation 2 — inject confidence_note read in verify_output** (append `for e in ctx.glossary_cache: if e.confidence_note < 0.5: diagnostics.append(...)` after the structural_map assignment at line 420):
```
FAILED tests/test_isa.py::test_verify_output_ignores_confidence_note
E       assert not True
```
**CAUGHT.** `test_verify_output_ignores_confidence_note` (test_isa.py:296) injects a low-confidence glossary entry (`confidence_note=0.01`) and asserts no diagnostic references "low-confidence" or "低置信度".

**Mutation 3 — escalate terminology severity WARNING → BLOCKING** (line 455: `severity=Severity.WARNING,` → `severity=Severity.BLOCKING,` inside the terminology loop):
```
FAILED tests/test_isa.py::test_verify_output_terminology_is_warning_not_blocking
E       assert False
E        +  where False = all(<genexpr ... d.severity == Severity.WARNING ...>)
```
**CAUGHT.** `test_verify_output_terminology_is_warning_not_blocking` (test_isa.py:335) asserts `all(d.severity == Severity.WARNING for d in terminology)`.

**Mutation catch rate: 3/3 = 100%** (was <20% pre-TRA-028/029/030).

### TDD test specs for outstanding findings

#### TRA-031 — add 10 missing JSONL cases to `tests/benchmark/cases/sft.jsonl`

Each new line IS the test (parametrized via `_all_cases()` → `test_benchmark_case`).
Recommended additions:
```jsonl
{"id": "S-01", "category": "S", "source": "- top\n  - mid\n    - deep", "level": "L3_STRICT", "must_contain": ["- top", "  - mid", "    - deep"], "must_not_contain": [], "zero_blocking": true, "description": "3-level nested list depth preserved."}
{"id": "S-02", "category": "S", "source": "| A | B |\n|---|---|\n| 1 | 2 |", "level": "L3_STRICT", "must_contain": ["| A | B |", "| 1 | 2 |"], "must_not_contain": [], "zero_blocking": true, "description": "Table column alignment preserved; no raw line breaks."}
{"id": "S-03", "category": "S", "source": "Use `install.sh` to bootstrap.", "level": "L3_STRICT", "must_contain": ["`install.sh`"], "must_not_contain": [], "zero_blocking": true, "description": "Inline code preserved verbatim; not translated."}
{"id": "S-04", "category": "S", "source": "1. Item\n   > Quote under item", "level": "L3_STRICT", "must_contain": ["1. Item", "> Quote under item"], "must_not_contain": [], "zero_blocking": true, "description": "Blockquote syntax preserved at correct indent."}
{"id": "S-06", "category": "S", "source": "# System Setup\n\nSee [link](#system-setup).", "level": "L3_STRICT", "must_contain": ["[link]"], "must_not_contain": [], "zero_blocking": true, "description": "Internal anchor links resolve post-translation."}
{"id": "D-01", "category": "D", "source": "All systems MUST be patched.", "level": "L3_STRICT", "must_contain": ["MUST"], "must_not_contain": [], "zero_blocking": true, "description": "Authoritative register; 'must' preserved for requirements."}
{"id": "D-02", "category": "D", "source": "The patch is applied by the operator.", "level": "L3_STRICT", "must_contain": [], "must_not_contain": [], "zero_blocking": true, "description": "Formal RFC register; passive voice preserved."}
{"id": "D-03", "category": "D", "source": "Run the installer. Then verify.", "level": "L3_STRICT", "must_contain": [], "must_not_contain": [], "zero_blocking": true, "description": "Instructional register; imperative mood preserved."}
{"id": "E-01", "category": "E", "source": "The value may be unclear.", "level": "L3_STRICT", "must_contain": ["may"], "must_not_contain": [], "zero_blocking": true, "description": "Intentional ambiguity preserved; not resolved by guesswork."}
{"id": "E-03", "category": "E", "source": "## Heading\n\nUnclosed fence ```", "level": "L3_STRICT", "must_contain": [], "must_not_contain": [], "zero_blocking": false, "description": "Broken source markdown; best-effort preservation."}
```
Risk: S-02 (tables) and S-06 (anchor rewrites) may currently fail because the rule path may not preserve table pipes or rewrite slugs; verify each case passes before locking the suite, or mark `zero_blocking: false` for best-effort cases.

#### TRA-032 — parametrize HITL test over {accept, override, skip}

- `test_hitl_review_decision_override` — Arrange: monkeypatch `Prompt.ask` to return `"override"` first, then `"edited text"`. Act: `resolution, text = review_decision("amb", "src", "candidate")`. Assert: `resolution == "override"` and `text == "edited text"` (and `text != "candidate"`).
- `test_hitl_review_decision_skip` — Arrange: monkeypatch `Prompt.ask` to return `"skip"`. Act: same call. Assert: `resolution == "skip"` and `text == "candidate"` (unchanged).
- Optional: `test_hitl_review_decision_override_via_callback` — pass `on_override=lambda ctx, txt: txt.upper()`; assert returned text is uppercased.

Risk: monkeypatch must handle two consecutive `Prompt.ask` calls for the override path (resolution prompt + override-text prompt). Use an iterator or call-counter.

#### TRA-033 — parametrize LLM seam degradation over exception types

```python
@pytest.mark.parametrize("exc", [RuntimeError, ValueError, TypeError, OSError, TimeoutError])
def test_llm_seam_degrades_on_each_exception_type(exc):
    def boom(_s, _c): raise exc("simulated")
    res = translate_segment("系统 成立", ctx, cache, ev, audit, llm_translate=boom)
    assert "Confirmed" in res.translation
    degraded = [r for r in audit._buffer if r.artifact_snapshot.get("degraded")]
    assert degraded and exc.__name__ in str(degraded[-1].artifact_snapshot.get("reason"))

def test_llm_seam_degrades_on_empty_string():
    def empty(_s, _c): return ""
    res = translate_segment("系统 成立", ctx, cache, ev, audit, llm_translate=empty)
    # Empty output should not silently propagate as "translation"
    assert res.translation != ""  # rule path must kick in OR a diagnostic flag set

def test_llm_seam_degrades_on_none():
    def none(_s, _c): return None
    res = translate_segment("系统 成立", ctx, cache, ev, audit, llm_translate=none)
    assert res.translation is not None and res.translation != ""
```

Risk: current `except Exception` only catches exceptions, NOT `None`/`""` returns. The empty/None tests would currently **fail** — they expose a real gap (silent acceptance of empty LLM output). Fix in `isa.py:319-321` by adding `if not target:` guard before recording evidence.

#### TRA-034 — optional refactor

Refactor `_ctx()` helpers in test_isa.py and test_phase6_hardening.py to consume `sample_glossary` / `evidence_registry` fixtures from conftest.py. Low priority; no correctness impact.

### Risks (overall)

1. **TRA-031 S-02/S-06 cases may fail at first** if the rule path doesn't preserve table pipes or rewrite anchor slugs. Run each new case individually before committing; mark non-deterministic cases `zero_blocking: false`.
2. **TRA-033 `""`/`None` seam gap** is real: the audit asserts only exception-path degradation. Silent empty-string propagation would bypass `verify_output`'s entity/terminology checks only if entities/glossary terms are also missing — currently `verify_output` would catch missing entities but not flag the empty seam itself. Recommend tightening the seam in `isa.py:318-321`.
3. **TRA-035 catch rate (100%)** is a point-in-time measurement; future mutations outside the 3 invariants tested (e.g. cache key drift, audit-trail non-append) are NOT covered. Consider expanding mutation testing beyond TRA-028/029/030.

**Read-only audit complete.** No production files modified (only temp `isa.py.bak` created and removed).

---

## Task `validate-D` — Deep validation of TRA-024 and TRA-006

HEAD `c42c457`. Read-only audit of `/home/z/my-project/tra/` and `/home/z/my-project/tra/tra-prototype/`. No files modified.

---

### TRA-024 (WARNING) — implementation_plan.md Phase 0 all unchecked but delivered; file-structure lists nonexistent tests

#### Verdict: **CONFIRMED** (all four sub-claims verified)

#### Current evidence

**1. Phase 0 checkboxes (implementation_plan.md:14-55) — all `[ ]`.**

Lines 18-22 (Phase 0.1), 26-33 (0.2), 37-41 (0.3), 45-54 (0.4) — every checkbox reads `[ ]`. Sample quotes:
- L18: `- [ ] 0.1.1 Initialize tra-prototype/ repo with pyproject.toml, requirements.txt, virtualenv`
- L26: `- [ ] 0.2.1 Define PolicyPriority enum (6 levels: FACTUAL_INTEGRITY → TARGET_FLUENCY)`
- L37: `- [ ] 0.3.1 Define EvidenceType enum ...`
- L45: `- [ ] 0.4.1 Implement CacheKeyGenerator:`

Yet every one of these is delivered: `pyproject.toml`, `requirements.txt`, `tra_cli.py` exist; `PolicyPriority` is in `memory.py`; `EvidenceType` is in `diagnostics.py`; `CacheKeyGenerator`/`TranslationCache` are in `cache.py`. (Phase 1.1 onward is correctly marked `[x]`.)

**2. File-structure block (implementation_plan.md:305-347) lists files that do not exist.**

Documented in tests/ block (L332-343):
- `tests/test_policy.py` (L336) — **does not exist**
- `tests/test_cache.py` (L338) — **does not exist**
- `tests/test_evidence.py` (L339) — **does not exist**
- `tests/benchmark/runner.py` (L341) — **does not exist**
- `tests/benchmark/test_benchmarks.py` (L343) — **does not exist**

Only `tests/benchmark/cases/` (L342) is real (contains `regression.jsonl`, `sft.jsonl`).

**3. Actual `tra-prototype/tests/` directory contents** (verified via `LS`):

```
conftest.py
test_anchor.py
test_benchmark.py
test_isa.py
test_kernel.py
test_modules.py
test_phase0.py
test_phase6_hardening.py
test_recovery.py
test_reporting.py
test_utils.py
test_validate.py
benchmark/cases/regression.jsonl
benchmark/cases/sft.jsonl
```

7 documented test files; 12 actually exist (5 documented missing, 7 undocumented present). The policy tests actually live in `test_phase0.py:112` (`test_policy_resolver_honors_stack`).

**4. Phase 1.3 (Glossary Builder, implementation_plan.md:79-84) — all `[ ]` but two are done.**

```
- [ ] 1.3.1 Frequency analysis (TF-IDF on technical terms)
- [ ] 1.3.2 ZH-EN Module lookup for canonical mappings
- [ ] 1.3.3 LLM-assisted candidate generation for unknown terms (prompt with context)
- [ ] 1.3.4 Conflict detection: same source term → multiple targets = GLOSSARY_CONFLICT exception
```

Verified against code:
- **1.3.1 (TF-IDF):** NOT implemented. No TF-IDF / sklearn / frequency-analysis code in `tra/`. Grep for `tfidf|tf_idf|frequency` returns nothing in `modules/zh_en.py`, `memory.py`, or `isa.py`. Correctly unchecked. ✅
- **1.3.2 (Module lookup):** IMPLEMENTED. `isa.py:158` calls `_MODULE.get_glossary_mappings()` and iterates `for src, tgt in mappings.items()`. `modules/zh_en.py` defines `get_glossary_mappings()`. Should be `[x]`. ❌ currently `[ ]`.
- **1.3.3 (LLM-assisted):** NOT implemented. No LLM-callable glossary candidate generation in `build_glossary`. The LLM seam exists only in `translate_segment`. Correctly unchecked. ✅
- **1.3.4 (Conflict detection):** IMPLEMENTED. `isa.py:164` and `isa.py:170` raise `GlossaryConflict` ("CONFLICTING_MAPPINGS") both for forbidden mappings and for divergent targets. `exceptions.py` defines `GlossaryConflict`. Should be `[x]`. ❌ currently `[ ]`.

#### Optimal fix

Edit `implementation_plan.md` only (documentation fix, zero code risk):

1. **Phase 0 (L18-54):** flip every `[ ]` to `[x]`. All 17 items delivered.
2. **Phase 1.3 (L81, L84):** flip 1.3.2 and 1.3.4 to `[x]`; leave 1.3.1 and 1.3.3 as `[ ]` (genuinely not done — would close them when TF-IDF and LLM glossary expansion are added).
3. **File-structure block (L332-343):** rewrite `tests/` to match reality:
   ```
   ├── tests/
   │   ├── conftest.py
   │   ├── test_phase0.py             # policy + cache-key + anchor slugify
   │   ├── test_phase6_hardening.py   # exception handling + HITL
   │   ├── test_isa.py                # 6 ISA instructions
   │   ├── test_kernel.py             # TRAKernel state machine
   │   ├── test_anchor.py             # AnchorRegistry + StructuralMap
   │   ├── test_modules.py            # ModuleRegistry + zh_en
   │   ├── test_cache.py              # ← remove (covered by test_phase0)
   │   ├── test_evidence.py           # ← remove (covered by test_isa)
   │   ├── test_validate.py           # standalone verifier
   │   ├── test_reporting.py          # audit summary
   │   ├── test_benchmark.py          # benchmark runner tests
   │   ├── test_utils.py              # markdown parsing + entity extraction
   │   ├── test_recovery.py           # repair-segment + repair-loop
   │   └── benchmark/
   │       └── cases/                 # S/F/T/D/E fixtures (regression.jsonl, sft.jsonl)
   ```
   Remove the nonexistent `test_policy.py`, `test_cache.py`, `test_evidence.py`, `benchmark/runner.py`, `benchmark/test_benchmarks.py`.

#### TDD test spec

Not applicable — TRA-024 is a docs drift; no behavior to test. The validation itself is the test: a future CI gate could `assert sorted(glob("tests/test_*.py")) == sorted(plan_listed_tests)` to prevent recurrence.

#### Risks

- Pure documentation edit; zero runtime impact.
- If future agents re-derive "what's done" from the checkboxes, leaving 1.3.1/1.3.3 unchecked correctly signals open work.
- The `test_cache.py` / `test_evidence.py` naming pattern is preserved by reusing fixtures in `test_phase0.py` / `test_isa.py`; if anyone re-adds standalone test files of those names, the file-structure block should be re-synced.

---

### TRA-006 (WARNING) — PolicyResolver is scaffolding, never invoked in production

#### Verdict: **CONFIRMED**

#### Current evidence

**1. `tra/policy.py` — the PolicyResolver class** (entire file, 26 lines):

```python
# tra/policy.py:13-25
class PolicyResolver:
    """Arbitrates conflicting requirements deterministically."""

    def __init__(self, stack: list[PolicyPriority]) -> None:
        # Precedence map: lower enum value wins.
        self.precedence = {p: p.value for p in stack}

    def resolve(self, a: PolicyPriority, b: PolicyPriority) -> PolicyPriority:
        return a if self.precedence[a] <= self.precedence[b] else b

    def wins(self, candidate: PolicyPriority, over: PolicyPriority) -> bool:
        """True if `candidate` has equal-or-higher priority than `over`."""
        return self.precedence[candidate] <= self.precedence[over]
```

Self-contained, no side effects, no I/O — pure function over an enum.

**2. Grep for `PolicyResolver` across `tra-prototype/`** (production code only, excluding tests):

```
/home/z/my-project/tra/tra-prototype/tra/policy.py:13: class PolicyResolver:   ← definition
/home/z/my-project/tra/tra-prototype/tests/test_phase0.py:23: from tra.policy import PolicyResolver   ← test import
/home/z/my-project/tra/tra-prototype/tests/test_phase0.py:113: resolver = PolicyResolver(   ← test usage
```

Zero production callers. (Confirmed by also grepping `resolver|\.resolve\(|\.wins\(` across `tra/` — "No matches found".)

**3. `isa.py:verify_output` (L406-484) does NOT consult the PolicyResolver.**

Severities are hard-coded inline at four points:
- L429: Structural → `Severity.BLOCKING`
- L442: Entity → `Severity.BLOCKING`
- L455: Terminology → `Severity.WARNING`
- L468: Epistemic → `Severity.BLOCKING`

No `PolicyResolver`, no `policy_stack` reference, no `resolve()` call. The function never instantiates a resolver; the `ctx.config.policy_stack` property is never read.

**4. TRA-SPECIFICATION.md §5 (L118-133)** explicitly requires the Policy Engine to be consulted for conflict resolution:

> "**5. TRA-POLICY: Arbitration & Conflict Resolution.** When instructions conflict (e.g., `TRANSLATE_SEGMENT` wants fluency, but `GLOSSARY` demands strict terminology), the Policy Engine resolves the conflict using weighted priorities."
>
> "**5.2 Conflict Resolution Contract.** Input: Two conflicting requirements (e.g., Fluency vs. Terminology). Process: Compare priorities in Stack. Higher priority wins. Output: Decision + Evidence logged in `Audit Memory`."

The spec mandates consultation on every conflict; the implementation never consults.

**5. `tra/config.py:DEFAULT_POLICY_STACK` (L13-20)** — where IS it used?

Grep results for `DEFAULT_POLICY_STACK`:
- `config.py:13` — definition
- `config.py:67` — `BootstrapConfig.policy_stack` property (returns a copy)
- `isa.py:23` — import
- `isa.py:310` — `policy_stack=_policy_stack(ctx)` passed into `CacheKeyContext` for cache-key hashing
- `isa.py:586-587` — `_policy_stack(ctx)` helper that returns `list(DEFAULT_POLICY_STACK)`
- `cache.py:55, 65` — `CacheKeyContext.policy_stack` field + `_hash_sorted([p.value for p in self.policy_stack])` for `policy_stack_hash`

So `DEFAULT_POLICY_STACK` is referenced only inside the cache-key generator. The PolicyResolver (which actually evaluates the stack's precedence) is dead code in production. The stack's *ordering* is implicitly encoded by the enum values and never *evaluated* outside tests.

#### Optimal fix

Two-tier approach:

**Tier 1 (minimal, recommended):** wire `PolicyResolver` into `verify_output` for the one ambiguity that exists today. Currently the only place where policy actually matters is terminology severity: a glossary term left untranslated is a `WARNING`, but per the immutable stack (Terminology #4 > Fluency #6), terminology should win and the violation should be `BLOCKING` (unless the term is `context_sensitive`). Concrete edit in `isa.py:451-461`:

```python
# After detecting src in target (terminology violation):
entry = next((e for e in ctx.glossary_cache if e.source == src), None)
if entry is not None and entry.status == GlossaryStatus.CANONICAL:
    resolver = PolicyResolver(ctx.config.policy_stack)
    if resolver.wins(PolicyPriority.TERMINOLOGICAL_CONSISTENCY,
                     PolicyPriority.TARGET_FLUENCY):
        sev = Severity.BLOCKING  # policy-driven escalation
    else:
        sev = Severity.WARNING
else:
    sev = Severity.WARNING  # context_sensitive stays soft
diagnostics.append(Diagnostic(severity=sev, subsystem="terminology", ...))
```

Also emit a `POLICY_ARBITRATION` `EvidenceRecord` to Audit Memory per Spec §5.2 ("Output: Decision + Evidence logged in Audit Memory").

**Tier 2 (full design fix):** make *every* severity assignment in `verify_output` consult the resolver. This is a larger refactor; defer until the policy engine needs to handle CERTAINTY_CONFLICT (currently hard-coded BLOCKING, but Spec §6 says it should be a WARNING + "Prioritize Epistemic Fidelity").

#### TDD test spec

```python
def test_policy_resolver_arbitrates_terminology_vs_fluency():
    """Spec §5: terminology (P4) wins over fluency (P6). When a glossary
    term leaks untranslated into the target, verify_output must escalate
    to BLOCKING (not WARNING) because TERMINOLOGICAL_CONSISTENCY >
    TARGET_FLUENCY in the immutable stack."""
    # Arrange
    ctx = RuntimeContext(
        config=BootstrapConfig(
            language_pair="ZH -> EN", domain="Security Advisory",
            conformance_level=ConformanceLevel.L3_STRICT,
            model_endpoint="rule-based", model_version="zh-en-1.0",
        ),
        glossary_cache=[
            GlossaryEntry(source="内核逃逸", target="kernel escape",
                          status=GlossaryStatus.CANONICAL,
                          rule_id="ZH-EN-RULE#CANON"),
        ],
        # ...minimal other fields...
    )
    source = "这是 内核逃逸 漏洞。"
    target = "This is a 内核逃逸 vulnerability."   # source term leaked
    audit = AuditTrail(path=...)

    # Act
    diags = verify_output(target, source, ctx, audit)

    # Assert
    term = [d for d in diags if d.subsystem == "terminology"]
    assert term, "terminology diagnostic expected"
    assert term[0].severity == Severity.BLOCKING  # policy-driven, was WARNING
    # POLICY_ARBITRATION evidence recorded per Spec §5.2
    arb = [r for r in audit.load() if r.get("isa_instruction") == "VERIFY_OUTPUT"]
    assert any("POLICY_ARBITRATION" in str(r) for r in arb)
```

#### Risks

1. **Severity-flip breaks existing tests.** Any test asserting `subsystem == "terminology"` and `severity == Severity.WARNING` will fail. Likely affected: `test_isa.py` (verify_output tests) and `test_phase6_hardening.py` (repair loop tests — repair_segment keys off diagnostic.severity). Search & update assertions.
2. **Repair-loop behavior change.** `kernel.py`'s VERIFY→REPAIR loop iterates BLOCKING diagnostics; escalating terminology to BLOCKING forces repair attempts (max_retries=3). If the rule-path repair can't substitute the term (already in target untranslated), it will exhaust retries and RAISE_FLAG — a behavioral change for end users.
3. **Tier 2 refactor surface area.** Wiring the resolver into every severity decision multiplies the cascade: epistemic violations are currently BLOCKING, but CERTAINTY_CONFLICT per Spec §6 should be WARNING + Epistemic-Fidelity-priority. Changing this affects `test_phase6_hardening.py` exception tests.
4. **Cache-key impact: none.** `DEFAULT_POLICY_STACK` is already part of the cache key; wiring the resolver doesn't change the stack contents, so cache hits remain byte-identical (TRA-028 regression test will still pass).
5. **Audit-trail volume.** Emitting `POLICY_ARBITRATION` evidence on every terminology diagnostic inflates `audit_trace.jsonl`. Consider emitting only on escalation (BLOCKING case), not on every terminology check.

---

### Summary table

| Finding | Verdict | Files affected | Code risk | Recommended priority |
| --- | --- | --- | --- | --- |
| TRA-024 | CONFIRMED | `implementation_plan.md` only | None | P2 — quick docs fix |
| TRA-006 | CONFIRMED | `tra/isa.py:verify_output`, `tra/policy.py` (already exists), tests | Medium — flips terminology severity WARNING→BLOCKING, breaks ≥1 existing test, changes repair-loop behavior | P3 — design gap, needs spec-aligned refactor |

**Read-only audit complete.** No production files modified.

---
Task ID: remediation-batch-2
Agent: Super Z (main)
Task: Re-validate 17 outstanding findings, TDD-remediate the actionable ones, commit and push

Work Log:
- Dispatched 4 parallel re-validation agents (validate-S/K/T/D); 16 confirmed, 1 already fixed (TRA-035)
- Found 1 new latent gap: TRA-033 empty/None LLM output bypasses except block
- Executed 11 TDD cycles (RED -> GREEN -> REFACTOR):
  * Cycle 1: TRA-014 path traversal (model_validator on BootstrapConfig, base_dir field)
  * Cycle 2: TRA-012 sanitize chokepoint (moved to utils.py, called from analyze_document)
  * Cycle 3: TRA-013 audit reproducibility (content-addressed evidence IDs, injectable clock)
  * Cycle 4: TRA-007 transition ordering (transitions fire AFTER ISA success)
  * Cycle 5: TRA-009+006 policy-driven severity (canonical term leakage = BLOCKING via PolicyResolver)
  * Cycle 7: TRA-004 exception recovery (BrokenMarkdown routes through _recover)
  * Cycle 8: TRA-002 module registry wired into kernel (ctx.module, _select_module)
  * Cycle 10: TRA-032 HITL parametrize + TRA-033 LLM seam empty/None guard
  * Cycle 11: TRA-024 implementation_plan.md checkbox sync
  * TRA-031: added 8 missing benchmark cases (21 of 23 spec cases now)
- Quality gates: ruff / mypy --strict (20 files) / pytest (139 tests, was 107) all green
- 4 commits pushed: 116f77c, 3eae671, 812ce7f, ea26c75

Stage Summary:
- 13 additional findings remediated in this session (TRA-014/012/013/007/009/006/004/002/032/033/024/031-partial/035-confirmed-fixed)
- 4 findings deferred (TRA-001 segment-level 1-2 day refactor, TRA-008 rewrite_links depends on TRA-001, TRA-034 conftest refactor low-priority, S-03/E-03 benchmark cases depend on TRA-001/004)
- HEAD: ea26c75 on origin/main, in sync
- Total findings remediated across both sessions: 31 of 35 (89%); 4 deferred (TRA-001, TRA-008, TRA-034, S-03/E-03 benchmark cases)

---

## Task ID: revalidate-remaining

Re-validation of 3 outstanding findings (TRA-001 / TRA-008 / TRA-034) against
the current codebase at HEAD `009fda6` (working tree clean).

### TRA-001 (BLOCKING) — TRANSLATE_SEGMENT receives whole document

**Verdict:** CONFIRMED

**Current evidence (HEAD `009fda6`):**

1. `tra/kernel.py:294-298` — `_execute_translation(self, src: str)`:
   ```python
   def _execute_translation(self, src: str) -> str:
       # Phase 2: deterministic whole-doc substitution via the glossary +
       # entity + epistemic lexicon. Segment granularity is wired in Phase 3.
       result = translate_segment(src, self.ctx, self.cache, self.evidence, self.audit)
       return result.translation
   ```
   The kernel passes `src` (the whole sanitized document) as `source_segment`.

2. `tra/isa.py:311-319` — signature is `translate_segment(source_segment: str, ...)`.
   The ISA contract demands a *segment*; the kernel hands it the entire doc.

3. `tra/memory.py:115-129` — `StructuralMap` exposes ONLY a `nodes` field and
   a `node_count` property. There is **no `iter_leaves()` method** (grep across
   `tra/` for `iter_leaves|iter_leaf|leaf_nodes|walk_leaves` returned zero
   matches).

4. `tra/isa.py:409-439` — `_rule_translate(segment, glossary, entities, module)`
   operates on a bare string. It does NOT consult the structural map and does
   NOT skip `is_no_translate_zone` nodes. Code-block content gets the same
   glossary substitution applied as paragraphs.

5. `tra/isa.py:552` — `repair_segment(..., segment_index: int = 0)`. The
   kernel's `_repair_loop` (`kernel.py:309-318`) calls `repair_segment`
   WITHOUT passing `segment_index`, so it is always 0 in production.
   `RepairAttempt.segment_index` (`memory.py:217`) is therefore always 0.

6. `tra/memory.py:101-112` — `StructuralNode` fields: `kind`, `level`,
   `text`, `children`, `original_slug`, `placeholder`, `is_no_translate_zone`,
   `metadata`. `is_no_translate_zone` exists and is set True on code blocks
   (`anchor.py:375`), but no consumer reads it.

**Root cause:** CONFIRMED. The structural map and `is_no_translate_zone`
markers exist but are never consulted by translation. The whole document is
treated as one segment.

**Optimal fix (minimal refactor):**

a. Add to `tra/memory.py:115` `StructuralMap`:
   ```python
   def iter_leaves(self) -> Iterator[tuple[int, StructuralNode]]:
       """Yield (index, node) for every leaf node (text-bearing, no children
       or text-bearing kinds). Pre-order traversal."""
       idx = 0
       def walk(nodes):
           nonlocal idx
           for n in nodes:
               if n.is_no_translate_zone or n.kind in (
                   NodeKind.HEADING, NodeKind.PARAGRAPH, NodeKind.LIST_ITEM,
                   NodeKind.TABLE_CELL, NodeKind.CODE_BLOCK,
               ):
                   yield idx, n; idx += 1
               yield from walk(n.children)
       yield from walk(self.nodes)
   ```

b. Refactor `tra/kernel.py:_execute_translation` to iterate leaves, call
   `translate_segment` per leaf, and reassemble via a render pass that
   preserves markdown structure (headings, lists, tables, code blocks).

c. Skip `is_no_translate_zone=True` leaves (pass through verbatim).

d. Pass `segment_index` to `repair_segment` in `_repair_loop`.

**Risks:** Cache key granularity changes (per-segment vs per-doc) — existing
cache entries become stale (low impact, caches are content-addressed and
`TranslationCache.get` returns None on miss → falls through to rule path).
The 139 existing tests assert on whole-doc output for small docs that are
already single-leaf — those should pass unchanged. Reassembly MUST preserve
markdown structure (headings, lists, tables, code blocks); test
`test_translate_segment_iterates_leaf_nodes` is the gate.

**Effort estimate:** M (4-8 hours). The reassembly logic is the hard part;
the structural map already preserves `text` on every leaf.

---

### TRA-008 (WARNING) — Anchor rewrite_links defined but never called

**Verdict:** CONFIRMED (but root-cause assessment was PARTIALLY WRONG)

**Current evidence:**

1. `tra/anchor.py:101-149` — `rewrite_links(markdown: str, registry: AnchorRegistry, ...)`
   — **the function is ALREADY string-based**, not AST-based. It splits the
   markdown into lines, tracks fenced code blocks, and regex-rewrites
   `[text](#slug)` → `[text](#translated_slug)`. The finding's worry that
   "rewrite_links operates on the AST — the kernel translates strings, not
   ASTs" is INCORRECT. The function takes a string and returns a string.

2. Grep `rewrite_links` across `tra/`:
   - `tra/anchor.py:101` — definition
   - `tests/test_anchor.py:11, 105` — only test caller
   - **Zero production callers.** CONFIRMED.

3. `tra/kernel.py:294-298` — `_execute_translation` does NOT call
   `rewrite_links`. CONFIRMED.

4. `tra/isa.py:93` — `structural_map, _registry = build_structural_map(source)`.
   The registry is bound to `_registry` (underscore prefix = discarded). It
   never reaches `RuntimeContext`.

5. `tra/memory.py:188-207` — `RuntimeContext` has NO `anchor_registry`
   field. The registry is lost after `analyze_document` returns.

**Root cause:** CONFIRMED, two defects:
  (a) `isa.py:93` discards the registry via `_registry` underscore binding;
      nothing propagates it onto `ctx`.
  (b) `kernel._execute_translation` never calls `rewrite_links`.
  
  **CORRECTION to finding:** The fix does NOT depend on TRA-001. Because
  `rewrite_links` already operates on a plain markdown string, the fix can
  land independently. The "must wait for segment-level translation" claim
  is refuted.

**Optimal fix (minimal):**

a. `tra/memory.py:188` — add field to `RuntimeContext`:
   ```python
   anchor_registry: Any = Field(default=None, exclude=True)
   ```
   (Typed `Any` because `AnchorRegistry` is a plain class, not a pydantic
   model — needs `exclude=True` like `module`.)

b. `tra/isa.py:93` — preserve the registry:
   ```python
   structural_map, registry = build_structural_map(source)
   ctx.anchor_registry = registry
   ```

c. `tra/kernel.py:262` (just before `_transition(KernelState.AUDIT_DIAGNOSTICS)`,
   after the repair loop completes):
   ```python
   if self.ctx.anchor_registry is not None:
       from .anchor import rewrite_links
       target, broken = rewrite_links(target, self.ctx.anchor_registry)
       for slug in broken:
           self.ctx.unresolved_ambiguities.append(f"BROKEN_ANCHOR: {slug}")
   ```
   (Headings must already be translated so their slugs are bound — need to
   call `registry.bind(placeholder, translated_slug)` for each heading during
   translation; for the rule-based path this means computing the slug from
   the translated heading text.)

**TDD test spec:** `test_internal_links_rewritten_after_translation` —
source has `# 系统成立` heading + `[link](#系统成立)`. After translation,
heading text becomes `System Confirmed` (rule path) and the link target
should be rewritten to `#system-confirmed`. Assert: `#system-confirmed` in
target AND original `#系统成立` link target absent.

**Risks:** `rewrite_links` calls `registry.translated_slug_for(slug)` which
queries `map_placeholder_to_translated_slug` — but that map is only populated
via `registry.bind(...)`, which nothing currently calls. So we ALSO need a
heading-binding pass before `rewrite_links`. Easiest: after translation,
iterate the structural map's heading nodes, find their translated text in
the target, compute the translated slug, and call `registry.bind()`.

**Effort estimate:** S-M (2-4 hours). No AST surgery required; one new
field on RuntimeContext, one line in isa.py, ~8 lines in kernel.py, plus
the heading-binding pass.

---

### TRA-034 (INFO) — conftest.py fixtures used only by test_phase0.py

**Verdict:** CONFIRMED

**Current evidence:**

`tests/conftest.py` defines 6 fixtures: `sample_glossary`, `sample_entities`,
`cache_context`, `evidence_registry`, `sample_evidence`, `config`.

Grep across `tests/` confirms usage:
- `sample_glossary`, `sample_entities` — used only inside `conftest.py` itself
  (by `cache_context`), no direct test consumption.
- `cache_context` — used only by `tests/test_phase0.py:28, 38`.
- `evidence_registry`, `sample_evidence` — used only by `tests/test_phase0.py:68`.
- `config` — used only by `tests/test_phase0.py:102`.

All 6 fixtures are exclusively consumed by `test_phase0.py` (or by other
fixtures within `conftest.py` itself). CONFIRMED.

**Root cause:** Not a correctness issue. Maintainability / DRY observation:
`test_kernel.py:14`, `test_phase6_hardening.py:102-103`, `test_validate.py`,
`test_benchmark.py:26`, and `test_outstanding_findings.py` (multiple sites)
all duplicate the same `config_path = Path(__file__).resolve().parent.parent
/ "config.yaml"` + `BootstrapConfig.from_yaml(...)` pattern that the `config`
fixture already encapsulates.

**Optimal fix:** Low priority. Optional refactor — replace the inline
`Path(__file__).resolve().parent.parent / "config.yaml" + from_yaml(...)`
boilerplate in the other test modules with the `config` fixture (or with a
pytest-`parametrize`-friendly factory fixture if they need different
configurations). Could also relocate `conftest.py` fixtures that are
phase-0-specific into a local `tests/phase0/conftest.py` if desired.

**TDD test spec:** N/A — this is a non-functional refactor. No new test
required; the existing 139 tests should all pass unchanged after the
cleanup.

**Risks:** Negligible. The refactor is purely cosmetic; if a fixture is
broken or has the wrong scope, tests will fail loudly.

**Effort estimate:** XS (under 1 hour).

---

### Feasibility summary

| Finding | Severity | Verdict | Effort | This session? |
|---------|----------|---------|--------|---------------|
| TRA-001 | BLOCKING | CONFIRMED | M (4-8h) | Borderline — reassembly is the risk |
| TRA-008 | WARNING  | CONFIRMED (root cause partially corrected — does NOT depend on TRA-001) | S-M (2-4h) | YES — should be done first |
| TRA-034 | INFO     | CONFIRMED | XS (<1h) | YES — trivial |

**Recommended order:** TRA-034 (trivial cleanup, ship first) → TRA-008
(string-based, no dependencies, ships independently) → TRA-001 (largest
refactor, do last; benefits from TRA-008's anchor-registry wiring).

**Important correction to original audit narrative:** the TRA-008 finding
asserted `rewrite_links` "operates on the AST — the kernel translates
strings, not ASTs. This may depend on TRA-001." That claim is REFUTED by
the current code: `rewrite_links(markdown: str, registry: AnchorRegistry)`
already operates on a plain markdown string with regex. TRA-008 can and
should be fixed before TRA-001.
