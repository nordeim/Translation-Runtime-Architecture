# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a **specification repository**, not a code repository. TRA = **Translation Runtime Architecture** (v1.0), a normative design for high-fidelity technical translation engines (human-in-the-loop or automated). There is no source code, no build system, no test runner, and no package manifest. The four numbered `.md` files plus `TRA-SPECIFICATION.md` are the entire product.

There are **no build / lint / test commands**. "Working" in this repo means authoring, refining, and cross-checking the specification documents. Use standard git for versioning (`git add`, `git commit`, `git log`). Any concrete engine, module, or tool that claims TRA compliance is out of scope of *this* repo — it would live elsewhere.

## The mental model (requires reading multiple files)

TRA is best understood as a virtual machine with an immutable core and plug-in extensions:

- **Kernel (immutable)** — the sequential state machine. Every translation request must pass through `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`. State transitions are triggered only by successful completion of ISA instructions. See the Mermaid diagram in `TRA-SPECIFICATION.md` §2.1.
- **Memory Model (immutable segments)** — four segments with different mutability: Immutable Config (read-only), Runtime Context (read/write), Document Memory (read-only), Audit Memory (append-only). Instructions read/write per their contracts.
- **ISA (immutable atomic ops)** — `ANALYZE_DOCUMENT`, `BUILD_GLOSSARY`, `BUILD_ENTITY_TABLE`, `TRANSLATE_SEGMENT`, `VERIFY_OUTPUT`, `REPAIR_SEGMENT`. Each has a strict contract: Inputs, Preconditions, Outputs, Invariants, Failure Conditions. Engines **must not skip instructions**.
- **Policy Engine (immutable priority stack)** — resolves conflicts deterministically. The stack order is non-negotiable: 1) Factual Integrity, 2) Structural Integrity, 3) Entity Preservation, 4) Terminological Consistency, 5) Epistemic Fidelity, 6) Target Fluency. Higher priority always wins; ties defer to Domain Module heuristics, then preserve source ambiguity as `Warning`.
- **Conformance Levels (L1–L4)** — strictness dial. L1 Basic → L2 Professional → L3 Strict (full TRA + diagnostics) → L4 Forensic (line-by-line evidence tracing). Each level subsumes the one below it.
- **Modules (plug-ins, mutable/extensible)** — Language Modules, Domain Modules, Formatting Modules. **They must not alter the Kernel or ISA.** This separation is the load-bearing design decision: any new module (e.g., a `fr-en.md` language bridge) extends data/behavior without touching core.

## How the five documents relate

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
