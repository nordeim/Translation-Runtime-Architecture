# Translation Runtime Architecture (TRA) v1.0

**A normative specification for high-fidelity technical translation engines.**

TRA defines the execution model, instruction set, state management, and conformance criteria for systems that translate technical documentation with verifiable precision — whether human-in-the-loop or fully automated.

## What This Is

This is primarily a **specification repository** — the five Spec files below are the normative product. Additional meta-docs (`README.md`, `AGENTS.md`, `CLAUDE.md`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md` accompany them.

A **Phase 0 prototype engine** now lives in `tra-prototype/` as a subdirectory of this repo (the original boundary rule put conformant engines in a separate repository; this was overridden so the prototype and spec evolve together). The specification documents remain non-code; the `tra-prototype/` engine has its own `pyproject.toml`, `requirements.txt`, and `tests/`, and its own tooling (`ruff`, `mypy --strict`, `pytest`).

## Documents

| File | Description |
|:-----|:------------|
| [`TRA-SPECIFICATION.md`](TRA-SPECIFICATION.md) | Authoritative master spec — Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules. **Source of truth.** |
| [`TRA-ISA-REFERENCE.md`](TRA-ISA-REFERENCE.md) | Expanded contracts for the six ISA instructions. Companion to Spec §3. |
| [`TRA-MODULE-ZH-EN.md`](TRA-MODULE-ZH-EN.md) | Language Module example (ZH↔EN bridge). Template for authoring new modules. |
| [`TRA-BENCHMARK-SUITE.md`](TRA-BENCHMARK-SUITE.md) | Representative test categories (S/F/T/D/E) seeded with concrete cases, intended to grow toward 100+, for L3/L4 certification. |
| [`TRA-CONFORMANCE-GUIDE.md`](TRA-CONFORMANCE-GUIDE.md) | Auditor checklist for L1–L4 certification. |

**Cross-referencing:** Use document title and section numbers (e.g., "Spec §5.1"), not filename numeric prefixes. The prefix numbers (1–4) do not match section order in the spec.

## Architecture at a Glance

TRA models a translation engine as a virtual machine with an immutable core and plug-in extensions:

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRA-KERNEL                               │
│  BOOTSTRAP → INITIALIZE → ANALYZE → BUILD → TRANSLATE →        │
│  VERIFY → REPAIR → AUDIT → EMIT                                 │
├─────────────────────────────────────────────────────────────────┤
│  Memory Model          │  Policy Engine (Priority Stack)        │
│  ┌──────────────────┐  │  1. Factual Integrity                  │
│  │ Immutable Config  │  │  2. Structural Integrity              │
│  │ Runtime Context   │  │  3. Entity Preservation               │
│  │ Document Memory   │  │  4. Terminological Consistency        │
│  │ Audit Memory      │  │  5. Epistemic Fidelity                │
│  └──────────────────┘  │  6. Target Fluency                     │
├─────────────────────────────────────────────────────────────────┤
│  ISA (6 atomic ops)    │  Conformance Levels: L1 → L2 → L3 → L4 │
├─────────────────────────────────────────────────────────────────┤
│  Modules (plug-ins): Language · Domain · Formatting             │
│  Extend behavior without touching Kernel or ISA                  │
└─────────────────────────────────────────────────────────────────┘
```

> **States vs. instructions:** The KERNEL states above are the lifecycle; the ISA instructions *execute within* those states — e.g., `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`, and `EXECUTE_TRANSLATION` contains `TRANSLATE_SEGMENT`. The canonical state labels (from `TRA-SPECIFICATION.md` §2.1) are `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`.

## Conformance Levels

| Level | Name | Focus | Use Case |
|:------|:-----|:------|:---------|
| **L1** | Basic | Meaning and formatting preserved | Internal drafts |
| **L2** | Professional | + Terminology consistency, entity preservation | Public docs, READMEs |
| **L3** | Strict | + Explicit glossary, diagnostics, audit trace | Security advisories, architecture guides |
| **L4** | Forensic | + Line-by-line evidence tracing | Legal contracts, regulatory filings |

## Working in This Repo

For the **specification documents**, there are no build or test commands — "working" means authoring, refining, and cross-checking the spec. For the **`tra-prototype/` engine** (the one code area in this repo), use its own toolchain:

```bash
# Specification documents — versioning only
git add .
git commit -m "Description of change"
git log --oneline
```

```bash
# tra-prototype/ engine — run gates inside that directory
cd tra-prototype
ruff format . && ruff check . && mypy --strict tra && pytest tests
```

The `tra-prototype/` engine originally would have lived in a separate repository; that boundary was overridden so the prototype and spec evolve together (see note at the top of this README and `CLAUDE.md`).

## Prototype Engine (`tra-prototype/`)

A TRA v1.0-conformant translation engine implementing the immutable core (Kernel + 6 ISA instructions + Policy Engine + Memory Model) with the ZH↔EN Language Module plugged in.

**Capabilities**

- Deterministic, cache-first ZH→EN pipeline: glossary + entity + epistemic substitution over an analyzable markdown structure.
- Conformance levels **L1 → L4**; the spec's canonical terminology and entities are preserved exactly (e.g. `成立 → Confirmed`, never "Valid").
- **L3 gate**: `VERIFY_OUTPUT` must raise zero `BLOCKING` diagnostics; `validate` enforces this out of band.
- **L4 forensics** (gated on `L4_FORENSIC`): line-by-line `evidence_trace.jsonl` + explicit `ambiguity_register.json`.
- **Human-in-the-loop**: `--interactive` pauses the repair loop on `UNRECOVERABLE` for accept / override / skip.
- **Graceful degradation**: if an LLM seam is supplied and raises, the engine falls back to the deterministic rule path rather than failing.
- **LLM-optional**: runs end-to-end with no LLM (rule path), or with a caller-supplied `llm_translate` callback.

**CLI**

```bash
cd tra-prototype

# Translate a markdown document through the full pipeline.
python -m tra_cli translate doc.md --level L3 -o doc.en.md

# Standalone conformance gate: does OUTPUT meet the LEVEL? (zero BLOCKING → PASS)
python -m tra_cli validate doc.md doc.en.md --level L3

# Summarize an audit trace; --report adds the conformance summary + state diagram.
python -m tra_cli audit ./audit_trace.jsonl --report

# Invalidate deterministic-cache entries.
python -m tra_cli cache-clear
```

**Status**

Phases 0–7 are complete (foundation → Kernel/Policy orchestration → ZH-EN module → CLI + benchmark suite → hardening → documentation & delivery). See `implementation_plan.md` for the item-by-item state and `CLAUDE.md` → "Prototype engine status" for layout and run commands.

## Invariants

These are binding contracts across all five documents — easy to break, expensive to fix:

1. **Canonical terminology is exact.** Binding mappings in Spec §3 and ZH-EN module (e.g., `成立 → Confirmed` never "Valid", `执行环境 → execution environment` never "runtime"). No strengthening or weakening of epistemic certainty.
2. **Entities are immutable.** Product names, APIs, CLI commands, versions: never translated, casing preserved verbatim.
3. **Verification never self-scores.** `VERIFY_OUTPUT` produces evidence-based diagnostics — it does not rate its own output.
4. **Repair must be surgical.** `REPAIR_SEGMENT` resolves a specific violation without introducing new ones.

## Certification Artifacts

If authoring or reviewing an engine against TRA (Conformance Guide L3 checklist), expect these interface points:

| Artifact | Contents |
|:---------|:---------|
| `tvm_bootstrap` | Engine configuration |
| `compilation_artifacts` | Glossary + Structural Map |
| `audit_trace` | Diagnostics — must contain zero `BLOCKING` errors for L3+ |

## Contributing

Two kinds of contribution are welcome:

- **Specification documents** — authoring, refining, and cross-checking the spec files (the normative product).
- **`tra-prototype/` engine** — code and tests that advance the prototype against `implementation_plan.md`, keeping every gate green (`ruff`, `ruff format`, `mypy --strict`, `pytest`). New language/domain/formatting behavior goes through the module registry, never by editing the Kernel or ISA.

See `CLAUDE.md` for architectural context and `AGENTS.md` for agent-specific guidance.
