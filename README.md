# Translation Runtime Architecture (TRA) v1.0

**A normative specification for high-fidelity technical translation engines.**

TRA defines the execution model, instruction set, state management, and conformance criteria for systems that translate technical documentation with verifiable precision — whether human-in-the-loop or fully automated.

## What This Is

This is a **specification repository**, not a code repository. The five markdown files below are the entire product. There is no source code, no build system, no test runner, and no package manifest.

## Documents

| File | Description |
|:-----|:------------|
| [`TRA-SPECIFICATION.md`](TRA-SPECIFICATION.md) | Authoritative master spec — Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules. **Source of truth.** |
| [`TRA-ISA-REFERENCE.md`](TRA-ISA-REFERENCE.md) | Expanded contracts for the six ISA instructions. Companion to Spec §3. |
| [`TRA-MODULE-ZH-EN.md`](TRA-MODULE-ZH-EN.md) | Language Module example (ZH↔EN bridge). Template for authoring new modules. |
| [`TRA-BENCHMARK-SUITE.md`](TRA-BENCHMARK-SUITE.md) | 100+ test cases (S/F/T/D/E categories) for L3/L4 certification. |
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

## Conformance Levels

| Level | Name | Focus | Use Case |
|:------|:-----|:------|:---------|
| **L1** | Basic | Meaning and formatting preserved | Internal drafts |
| **L2** | Professional | + Terminology consistency, entity preservation | Public docs, READMEs |
| **L3** | Strict | + Explicit glossary, diagnostics, audit trace | Security advisories, architecture guides |
| **L4** | Forensic | + Line-by-line evidence tracing | Legal contracts, regulatory filings |

## Working in This Repo

There are **no build or test commands**. "Working" means authoring, refining, and cross-checking specification documents.

```bash
# Versioning
git add .
git commit -m "Description of change"
git log --oneline
```

Any concrete engine, module, or tool claiming TRA compliance lives in a separate repository.

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

This is a specification repository. Contributions are limited to authoring, refining, and cross-checking the spec documents. See `CLAUDE.md` for architectural context and `AGENTS.md` for agent-specific guidance.
