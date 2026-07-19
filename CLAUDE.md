# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is primarily a **specification repository** — TRA = **Translation Runtime Architecture** (v1.0), a normative design for high-fidelity technical translation engines (human-in-the-loop or automated). The **five Spec files** are the normative product; meta-docs (`README.md`, `AGENTS.md`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md` accompany them.

A **Phase 0 prototype engine** now lives in `tra-prototype/` as a subdirectory of this repo (the original boundary rule put conformant engines in a separate repository; this was overridden so the prototype and spec evolve together). Treat `tra-prototype/` as the one code area here: it has its own `pyproject.toml`, `requirements.txt`, and `tests/`, and its own tooling — `ruff`, `mypy --strict`, and `pytest` run from inside that directory. The Spec files themselves remain the normative product and are never "built".

There are **no build / lint / test commands for the specification documents**. "Working" in this repo means authoring, refining, and cross-checking the specification documents (use standard git for versioning). For the `tra-prototype/` engine, use its own toolchain (see `tra-prototype/pyproject.toml`).

## Prototype engine status (`tra-prototype/`)

**Status (as of the current HEAD):** Phases 0–6 are complete — foundation (Phase 0), structural parsing/anchor resolution (Phase 1), the six ISA instructions (Phase 2), Kernel + Policy Engine orchestration (Phase 3), ZH-EN Language Module integration (Phase 4), CLI + artifacts + benchmark suite + L3 `validate` gate (Phase 5), and hardening: TRA-EXCEPTION recovery, human-in-the-loop hooks, L4 forensic artifacts, input sanitization, and LLM graceful degradation (Phase 6). **Phase 7 (documentation & delivery) has not started.** The full per-item state lives in `implementation_plan.md`; open items are 6.3.1 (structlog), 6.5.1 (asyncio parallelism), 6.5.2 (cross-run disk caching), and all of Phase 7.

**Layout (where behavior lives):**

- `kernel.py` — the immutable 9-state sequential machine (`BOOTSTRAP → … → EMIT_PAYLOAD`); transitions only on successful ISA completion.
- `isa.py` — the six ISA instructions (`ANALYZE_DOCUMENT`, `BUILD_GLOSSARY`, `BUILD_ENTITY_TABLE`, `TRANSLATE_SEGMENT`, `VERIFY_OUTPUT`, `REPAIR_SEGMENT`), each with a strict Inputs/Preconditions/Outputs/Invariants/Failure contract.
- `memory.py` — `RuntimeContext` (Pydantic) + the immutable-segment model.
- `policy.py` — the `PolicyResolver` over the non-negotiable 6-priority stack.
- `cache.py` — deterministic `TranslationCache` (SHA-256 over canonical context; cache-first in `TRANSLATE_SEGMENT`).
- `diagnostics.py` — append-only `AuditTrail` + `EvidenceRegistry`.
- `anchor.py` / `utils.py` — markdown structural parsing + entity extraction.
- `recovery.py` — maps the 5 `TRA-EXCEPTION` types to spec-mandated recoveries.
- `hitl.py` — interactive review hooks (`--interactive` CLI flag).
- `reporting.py` — audit summary, Mermaid state diagram, L4 line-by-line trace.
- `validate.py` — standalone L3/L4 pass-gate verifier.
- `benchmark.py` + `tests/benchmark/cases/*.jsonl` — declarative S/F/T/D/E/R cases; L3 gate = zero `BLOCKING`.
- `modules/{registry,base,zh_en}.py` — the plug-in registry and the bundled ZH↔EN module.

**Run / test from inside `tra-prototype/`:**

```bash
cd tra-prototype
ruff format . && ruff check . && mypy --strict tra && pytest tests
```

**Extension rule (reinforces the §9 note):** new language bridges (e.g. `fr-en`) register through `build_default_registry()` in `modules/registry.py` as a `ModuleInterface`. They must not touch the Kernel or ISA — that separation is load-bearing.

**Known gaps (not yet addressed):**

- `structlog` is no longer a listed dependency (TRA-017 fixed in Round 3 remediation commit `a3cd2c1`). The engine uses the plain `AuditTrail` (no structured/correlation-ID logging — 6.3.1 open, but `structlog` itself is no longer in `pyproject.toml`).
- No `asyncio` segment-level parallelism (6.5.1 open).
- Glossary/entity tables are rebuilt per run; only the translation output is cached across runs via diskcache (6.5.2 open).
- **Segment-level granularity (TRA-001, partial):** `TRANSLATE_SEGMENT` currently operates on the whole document rather than per leaf segment; the kernel passes the full source to `translate_segment`. Code-block (fenced + inline) no-translate zone protection IS implemented, but full per-leaf segment translation is deferred. Affects cache granularity, `RepairAttempt.segment_index`, and the L4 line-by-line trace.
- **Module registry (TRA-002, fixed in kernel; TRA-099 fixed in round 4):** the kernel selects the language module from the registry when supplied (`TRAKernel(cfg, registry=registry)`), and `as_interface()` satisfies `LanguageModuleProtocol` (TRA-096 fixed in Round 3). The CLI's `translate` command now auto-builds the default registry and passes it to `TRAKernel` (TRA-099 fixed in round 4 commit `e54b7a7`). The kernel's `_select_module` matches by full direction (TRA-F4-007 fixed in round 4).
- **Exception recovery (TRA-004, partial; TRA-038 fixed in round 4; TRA-A5-003 fixed in round 5; TRA-E5-003 fixed in round 5):** `BrokenMarkdown` routes through `_recover` (EXCEPTION_HANDLER); `build_entity_table` is wrapped in try/except (TRA-039); `route_exception` has an explicit `Unrecoverable` branch returning `BLOCKING + HALT` (TRA-044 fixed in Round 2). All 3 previously-unreachable exception types are now wired in production (TRA-038 fixed in round 4 commit `d95c36d`): `UnknownTerm` is logged via `recover_unknown_term` (non-halting) when a CJK token has no glossary/entity/epistemic match; `CertaintyConflict` is raised in the LLM path when a forbidden drift target is detected; `EntityAmbiguity` is logged when a token matches multiple entity patterns and `entity_type_hint` returns None. TRA-A5-003 (round 5): `UnknownTerm` now emits an `EXCEPTION_HANDLER` audit record. TRA-E5-003 (round 5): `EMPTY_SOURCE` now raises `BrokenMarkdown` (not base `TRAException`) so `route_exception` dispatches to `recover_broken_markdown` which returns `Severity.BLOCKING` per Spec §6 — previously fell through to the default WARNING.
- **Policy Engine (TRA-006 fixed in Round 3; TRA-072 fixed in round 4; TRA-A5-013 fixed in round 5):** `PolicyResolver` is now invoked for ALL 5 severity decision pairs in `verify_output` (TRA-072 fixed in round 4 commit `78c9250`; TRA-A5-013 fixed in round 5 commit `36246bb`): Factual (P1) vs Fluency (P6), Structural (P2) vs Fluency (P6), Entity (P3) vs Fluency (P6), Terminological (P4) vs Fluency (P6), Epistemic (P5) vs Fluency (P6). Monkeypatching `_POLICY_RESOLVER.wins` to return False drops ALL severities from BLOCKING to WARNING. Spec §5.2 universal arbitration contract is now fully met. TRA-A5-013 added the factual-integrity check (version + date token preservation) that was previously the only spec-mandated check with NO implementation.
- **LLM seam (TRA-090 fixed in round 5; TRA-D5-002):** `TRAKernel.run()` now accepts an optional `llm_translate: Callable[[str, RuntimeContext], str] | None` callback (dependency injection). Previously the only way to supply an LLM was module-level monkeypatching of `tra.kernel.translate_segment` (fragile — any rename broke tests silently). The e2e test suite (`tests/test_e2e_to_translate.py`) and the manual demo script (`e2e_test.py`) now both use DI.
- **Cache integrity (TRA-077 fixed in round 3; TRA-079 fixed in round 5):** cache stores JSON strings (not pickle) to prevent insecure deserialization (OWASP A08). TRA-079 (round 5): cache values are now HMAC-SHA256 signed — each entry is stored as `"{hmac_hex}:{json_value}"`. On read, the HMAC is verified; tampered entries are treated as cache misses (defense-in-depth against an attacker who can write to the cache directory).
- **Dependency hygiene (TRA-017, FIXED in Round 3 remediation commit `a3cd2c1`):** the 6 unused dependencies (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) were removed from `pyproject.toml`. Install footprint dropped from ~70 packages to ~15.
- **Phase 7 (documentation & delivery)** partially started: `TRA-MODULE-AUTHORING.md` created (TRA-100, round 4 remediation). ADRs, API reference, and conformance self-audit still pending.
- **Benchmark coverage (TRA-031, improved):** 36 of 100+ spec target cases implemented (S-03 and E-03 added in round 4 remediation, TRA-092; +12 cases added in round 5 remediation covering tables, nested lists, blockquotes, HRs, ISO dates, numeric units, comparison operators, CVE advisories, API refs, and acronym ambiguity).

The full 41-finding Round 2 audit register is in `docs/audit/round2/TRA_audit_findings_register_r2.xlsx`; the narrative report is `docs/audit/round2/TRA_Prototype_Audit_Report_r2.docx`. Round 1 deliverables are in `docs/audit/` (top level). Round 3 deliverables (36 findings: 2 BLOCKING both fixed, 18 WARNING, 16 INFO) are in `docs/audit/round3/`. Round 4 deliverables (47 issues + 19 positive verifications: 1 BLOCKING, 11 WARNING, 35 INFO) are in `docs/audit/round4/`. Round 5 deliverables (68 findings: 46 issues + 22 positive verifications; 0 BLOCKING / 7 WARNING / 39 INFO) are in `docs/audit/round5/`. The current test count is **294 across 16 test files** (was 228 at Round 5 audit baseline; +66 from Round 5 remediation commits `eb3d574` through the latest).

## The mental model (requires reading multiple files)

TRA is best understood as a virtual machine with an immutable core and plug-in extensions:

- **Kernel (immutable)** — the sequential state machine. Every translation request must pass through `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`. State transitions are triggered only by successful completion of ISA instructions. See the Mermaid diagram in `TRA-SPECIFICATION.md` §2.1.
- **Memory Model (immutable segments)** — four segments with different mutability: Immutable Config (read-only), Runtime Context (read/write), Document Memory (read-only), Audit Memory (append-only). Instructions read/write per their contracts.
- **States vs. instructions (easy to conflate):** The KERNEL states are the lifecycle; the ISA instructions *execute within* those states — e.g., `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`, and `EXECUTE_TRANSLATION` contains `TRANSLATE_SEGMENT`. Note that `review.md`'s "BOOTSTRAP → ANALYZE → BUILD → TRANSLATE → VERIFY → REPAIR → AUDIT → EMIT" and `start-here.md`'s collapsed workflow are *abbreviated renderings* of the canonical state labels above; they are not a different state machine.
- **ISA (immutable atomic ops)** — `ANALYZE_DOCUMENT`, `BUILD_GLOSSARY`, `BUILD_ENTITY_TABLE`, `TRANSLATE_SEGMENT`, `VERIFY_OUTPUT`, `REPAIR_SEGMENT`. Each has a strict contract: Inputs, Preconditions, Outputs, Invariants, Failure Conditions. Engines **must not skip instructions**.
- **Policy Engine (immutable priority stack)** — resolves conflicts deterministically. The stack order is non-negotiable: 1) Factual Integrity, 2) Structural Integrity, 3) Entity Preservation, 4) Terminological Consistency, 5) Epistemic Fidelity, 6) Target Fluency. Higher priority always wins; ties defer to Domain Module heuristics, then preserve source ambiguity as `Warning`.
- **Conformance Levels (L1–L4)** — strictness dial. L1 Basic → L2 Professional → L3 Strict (full TRA + diagnostics) → L4 Forensic (line-by-line evidence tracing). Each level subsumes the one below it.
- **Modules (plug-ins, mutable/extensible)** — Language Modules, Domain Modules, Formatting Modules. **They must not alter the Kernel or ISA.** This separation is the load-bearing design decision: any new module (e.g., a `fr-en.md` language bridge) extends data/behavior without touching core.

## How the five Spec documents relate

| File | Role | Relationship |
| :--- | :--- | :--- |
| `TRA-SPECIFICATION.md` | **Authoritative master spec.** Self-contained: Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules. | Source of truth. Other files are deeper dives that must agree with it. |
| `TRA-ISA-REFERENCE.md` (numbered "1") | Expanded contracts for the six ISA instructions. | Detailed companion to Spec §3. |
| `TRA-MODULE-ZH-EN.md` (numbered "2") | Concrete example of a Language Module (ZH↔EN bridge). | Exemplifies the Module registry in Spec §9 — a template for new modules. |
| `TRA-BENCHMARK-SUITE.md` (numbered "3") | 100+ test cases (S/F/T/D/E categories) for L3/L4 certification. | The acceptance test surface referenced by the Conformance Guide. |
| `TRA-CONFORMANCE-GUIDE.md` (numbered "4") | Auditor checklist for L1–L4 certification. | Operationalizes Spec §8; uses artifact names below. |

Note the numeric file prefixes (1–4) do **not** match the section order inside `TRA-SPECIFICATION.md`. When cross-referencing, use the document's title and section numbers (e.g., "Spec §5.1"), not the filename number.

## Invariants a future instance must not violate

These appear across files but are easy to break when editing or when authoring a new module/engine:

- **Canonical terminology is exact, not approximate.** Spec §3 and the ZH-EN module give binding mappings: `成立 → Confirmed` (never "Valid"/"True"), `执行环境 → execution environment` (never "runtime"), `高度可信 → highly credible` (never "indisputably true"). Epistemic certainty must be preserved exactly — no strengthening or weakening.
- **Entities are immutable.** Product names, APIs, CLI commands, versions, acronyms are never translated; casing/punctuation preserved verbatim. On ambiguity, default to treating the token as an Entity (Spec §3 `ENTITY_AMBIGUITY`, `BUILD_ENTITY_TABLE` invariant).
- **Verification never self-scores.** `VERIFY_OUTPUT` produces evidence-based diagnostics (`severity`, `subsystem`, `issue`, `evidence`, `action`) — it does not rate its own output.
- **Repair must be surgical.** `REPAIR_SEGMENT` resolves a specific violation without introducing new ones and without violating a higher-priority policy.

## Concrete artifact names used in certification

The Conformance Guide (§"Auditor Checklist for L3") references runtime artifacts an engine must surface for audit. If you author or review an engine/tool against TRA, expect these interface points: `tvm_bootstrap` (config), `compilation_artifacts` (Glossary + Structural Map), and `audit_trace` (diagnostics, must contain zero `BLOCKING` errors for L3+ certification).
