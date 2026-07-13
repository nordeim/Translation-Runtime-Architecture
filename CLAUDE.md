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

- `structlog` is a listed dependency but the engine uses the plain `AuditTrail` (no structured/correlation-ID logging — 6.3.1 open).
- No `asyncio` segment-level parallelism (6.5.1 open).
- Glossary/entity tables are rebuilt per run; only the translation output is cached across runs via diskcache (6.5.2 open).
- **Segment-level granularity (TRA-001):** `TRANSLATE_SEGMENT` currently operates on the whole document rather than per leaf segment; the kernel passes the full source to `translate_segment`. Affects cache granularity, `RepairAttempt.segment_index`, and the L4 line-by-line trace.
- **Module registry bypassed (TRA-002):** the kernel hard-codes `ZHENModule()` instead of routing through `build_default_registry()`; registered modules are not yet picked up by `tra_cli.py translate`.
- **Exception recovery (TRA-004):** only `GlossaryConflict` and `Unrecoverable` reach `route_exception`; `BrokenMarkdown` propagates uncaught through the kernel, and `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are never raised in production code paths.
- **Policy Engine scaffolding (TRA-006):** `PolicyResolver` is defined and tested but never invoked in production; `verify_output` does not consult the 6-priority stack for arbitration.
- **Audit trail reproducibility (TRA-013):** `uuid4` evidence IDs + `datetime.now(UTC)` timestamps make `audit_trace.jsonl` non-byte-reproducible across runs — undermines L4 forensic hashing.
- **Dependency hygiene (TRA-017):** `litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio` are listed but unused.
- **Phase 7 (documentation & delivery)** has not started: no ADRs, no API reference, no module authoring guide, no conformance self-audit.
- **Benchmark coverage (TRA-031):** 13 of 23 spec cases implemented (S-01..S-04, S-06, D-01..D-03, E-01, E-03 missing); spec target is 100+.

The full 35-finding audit register is in `docs/audit/TRA_audit_findings_register.xlsx`; the narrative report is `docs/audit/TRA_Prototype_Audit_Report.docx`.

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
