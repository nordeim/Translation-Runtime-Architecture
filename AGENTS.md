# AGENTS.md

## What this repo is

Specification-first repo. TRA = Translation Runtime Architecture v1.0 — normative spec for high-fidelity technical translation engines. The **five Spec files** are the normative product; meta-docs (`README.md`, `CLAUDE.md`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md` accompany them. **No build/test tooling applies to the specification documents themselves.** A Phase 0 prototype engine lives in `tra-prototype/` (a subdirectory, overriding the original "separate repository" boundary rule) and has its own `pyproject.toml`, `requirements.txt`, and `tests/` with `ruff`, `mypy --strict`, and `pytest`.

## Files and roles

| File | Role |
|:--|:--|
| `TRA-SPECIFICATION.md` | Authoritative master spec (Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules). Source of truth. |
| `TRA-ISA-REFERENCE.md` | Expanded contracts for the six ISA instructions. Companion to Spec §3. |
| `TRA-MODULE-ZH-EN.md` | Language Module example (ZH↔EN bridge). Template for new modules. |
| `TRA-BENCHMARK-SUITE.md` | Representative test categories (S/F/T/D/E) seeded with concrete cases, intended to grow toward 100+, for L3/L4 certification. |
| `TRA-CONFORMANCE-GUIDE.md` | Auditor checklist for L1–L4 certification. |

**Cross-referencing:** Use document title and section numbers (e.g., "Spec §5.1"), not filename numeric prefixes. The file prefix numbers (1–4) do not match section order in the spec.

**States vs. instructions:** The KERNEL states are the lifecycle; the ISA instructions *execute within* those states — `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`. Canonical state labels (Spec §2.1): `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`.

## How to work here

- "Working" = authoring, refining, cross-checking spec documents.
- Use standard git: `git add`, `git commit`, `git log`.
- Any concrete engine/module/tool claiming TRA compliance lives in a different repo.
- See `CLAUDE.md` for the full mental model and architectural context.

## Critical invariants (easy to break)

1. **Canonical terminology is exact.** Binding mappings exist in Spec §3 and ZH-EN module (e.g., `成立 → Confirmed` never "Valid", `执行环境 → execution environment` never "runtime"). No strengthening or weakening of epistemic certainty.
2. **Entities are immutable.** Product names, APIs, CLI commands, versions, acronyms: never translated, casing/punctuation preserved. When ambiguous, default to treating token as Entity.
3. **Verification never self-scores.** `VERIFY_OUTPUT` produces evidence-based diagnostics — it does not rate its own output.
4. **Repair must be surgical.** `REPAIR_SEGMENT` resolves a specific violation without introducing new ones or violating higher-priority policy.

## Certification artifacts

If authoring/reviewing an engine against TRA, expect these interface points (referenced in Conformance Guide L3 checklist): `tvm_bootstrap` (config), `compilation_artifacts` (Glossary + Structural Map), `audit_trace` (diagnostics, must contain zero `BLOCKING` errors for L3+).
