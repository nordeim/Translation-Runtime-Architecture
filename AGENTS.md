# AGENTS.md

## What this repo is

Specification-first repo. TRA = Translation Runtime Architecture v1.0 — normative spec for high-fidelity technical translation engines. The **five Spec files** are the normative product; meta-docs (`README.md`, `CLAUDE.md`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md` accompany them. **No build/test tooling applies to the specification documents themselves.** A Phase 0 prototype engine lives in `tra-prototype/` (a subdirectory, overriding the original "separate repository" boundary rule) and has its own `pyproject.toml`, `requirements.txt`, and `tests/` with `ruff`, `mypy --strict`, and `pytest`.

## Files and roles

### Normative spec files (the 5-file product)

| File | Role |
|:--|:--|
| `TRA-SPECIFICATION.md` | Authoritative master spec (Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules). Source of truth. |
| `TRA-ISA-REFERENCE.md` | Expanded contracts for the six ISA instructions. Companion to Spec §3. |
| `TRA-MODULE-ZH-EN.md` | Language Module example (ZH↔EN bridge). Linguistic spec for the bundled module. |
| `TRA-MODULE-AUTHORING.md` | Module authoring guide — engineering contract for new Language/Domain/Formatting modules (TRA-100). |
| `TRA-BENCHMARK-SUITE.md` | Representative test categories (S/F/T/D/E) seeded with concrete cases, intended to grow toward 100+, for L3/L4 certification. |
| `TRA-CONFORMANCE-GUIDE.md` | Auditor checklist for L1–L4 certification. |

### Meta-docs (orientation, planning, history)

| File | Role |
|:--|:--|
| `README.md` | Repo overview, architecture at a glance, conformance levels, CLI quick-start. |
| `CLAUDE.md` | Mental model + prototype engine status (file layout, run commands, known gaps). Authoritative for "where behavior lives". |
| `AGENTS.md` | This file — agent-specific guidance, critical invariants, certification artifacts. |
| `start-here.md` | Quick-start onboarding for new contributors. |
| `implementation_plan.md` | Phase 0–7 per-item checkbox state + file structure summary + dependencies. |
| `prototype.md` | Original prototype design notes. |
| `review.md` / `review-feedback.md` | Reviewer feedback and risk-mitigation notes that shaped the implementation. |
| `to_translate.md` | Sample source document used by the E2E test suite (`tests/test_e2e_to_translate.py`). |
| `status.md` | Historical session log (frozen at commit `4d97aa1`; retained for context only — see banner). |

### Prototype engine (`tra-prototype/`)

| File | Role |
|:--|:--|
| `tra-prototype/SKILL.md` | User + agent guidance for the prototype engine (setup, CLI, conformance levels, quality gates, known limitations, audit remediation status). |
| `tra-prototype/README.md` | Prototype-specific install + commands + architecture + known gaps. |
| `tra-prototype/tra/` | The engine source — 16 modules (kernel, isa, memory, policy, cache, anchor, config, exceptions, recovery, hitl, reporting, validate, benchmark, diagnostics, utils + modules/ subpackage). |
| `tra-prototype/tests/` | 309 tests across 16 files — see `tra-prototype/SKILL.md` §7 for the full inventory. |
| `tra-prototype/pyproject.toml` | 6 runtime deps + 4 dev deps (ruff, mypy, pytest, mutmut). See `implementation_plan.md` "Dependencies" table. |

### Audit deliverables (`docs/audit/`)

| Path | Round | Findings |
|:--|:--|:--|
| `docs/audit/` (top level) | Round 1 | 35 findings (11 BLOCKING / 22 WARNING / 2 INFO) |
| `docs/audit/round2/` | Round 2 | 41 findings (3 BLOCKING / 25 WARNING / 13 INFO) |
| `docs/audit/round3/` | Round 3 | 36 findings (2 BLOCKING / 18 WARNING / 16 INFO) + `remediation_plan.md` |
| `docs/audit/round4/` | Round 4 | 47 issues + 19 positive verifications (1 BLOCKING / 11 WARNING / 35 INFO) + `remediation_plan_r4.md` |
| `docs/audit/round5/` | Round 5 | 68 findings (46 issues + 22 positive verifications; 0 BLOCKING / 7 WARNING / 39 INFO) + `remediation_plan_r5.md` |

**Cross-referencing:** Use document title and section numbers (e.g., "Spec §5.1"), not filename numeric prefixes. The file prefix numbers (1–4) do not match section order in the spec.

**States vs. instructions:** The KERNEL states are the lifecycle; the ISA instructions *execute within* those states — `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`. Canonical state labels (Spec §2.1): `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`.

## How to work here

- "Working" = authoring, refining, cross-checking spec documents.
- Use standard git: `git add`, `git commit`, `git log`.
- Any concrete engine/module/tool claiming TRA compliance (OTHER THAN the bundled `tra-prototype/` subdirectory) lives in a different repo.
- See `CLAUDE.md` for the full mental model and architectural context.

## Critical invariants (easy to break)

1. **Canonical terminology is exact.** Binding mappings exist in Spec §3 and ZH-EN module (e.g., `成立 → Confirmed` never "Valid", `执行环境 → execution environment` never "runtime"). No strengthening or weakening of epistemic certainty.
2. **Entities are immutable.** Product names, APIs, CLI commands, versions, acronyms: never translated, casing/punctuation preserved. When ambiguous, default to treating token as Entity.
3. **Verification never self-scores.** `VERIFY_OUTPUT` produces evidence-based diagnostics — it does not rate its own output.
4. **Repair must be surgical.** `REPAIR_SEGMENT` resolves a specific violation without introducing new ones or violating higher-priority policy.

## Certification artifacts

If authoring/reviewing an engine against TRA, expect these interface points (referenced in Conformance Guide L3 checklist): `tvm_bootstrap` (config), `compilation_artifacts` (Glossary + Structural Map), `audit_trace` (diagnostics, must contain zero `BLOCKING` errors for L3+).
