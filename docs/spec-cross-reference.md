# TRA Spec Cross-Reference

**Maps each TRA-SPECIFICATION.md section to its implementation in the
`tra-prototype` engine at HEAD `f782043`.**

---

## §1 Scope & Definitions

| Spec Requirement | Implementation | File:Line |
|---|---|---|
| Kernel = immutable execution lifecycle | `TRAKernel` class with 9-state machine | `tra/kernel.py:106` |
| ISA = 6 atomic operations | `analyze_document`, `build_glossary`, `build_entity_table`, `translate_segment`, `verify_output`, `repair_segment` | `tra/isa.py` |
| Runtime Context = mutable memory state | `RuntimeContext` (Pydantic model) | `tra/memory.py:207` |
| Policy Engine = deterministic arbitration | `PolicyResolver` over 6-priority stack | `tra/policy.py` |
| Conformance Level = L1–L4 strictness dial | `ConformanceLevel` enum | `tra/memory.py:49` |

---

## §2 TRA-KERNEL: The Execution Model

### §2.1 State Machine

| Spec State | Implementation | Code |
|---|---|---|
| BOOTSTRAP | `KernelState.BOOTSTRAP` | `tra/kernel.py:77` |
| INITIALIZE_RUNTIME | `KernelState.INITIALIZE_RUNTIME` | `tra/kernel.py:78` |
| ANALYZE_DOCUMENT | `KernelState.ANALYZE_DOCUMENT` | `tra/kernel.py:79` |
| BUILD_ARTIFACTS | `KernelState.BUILD_ARTIFACTS` | `tra/kernel.py:80` |
| EXECUTE_TRANSLATION | `KernelState.EXECUTE_TRANSLATION` | `tra/kernel.py:81` |
| VERIFY_OUTPUT | `KernelState.VERIFY_OUTPUT` | `tra/kernel.py:82` |
| REPAIR_IF_NEEDED | `KernelState.REPAIR_IF_NEEDED` | `tra/kernel.py:83` |
| AUDIT_DIAGNOSTICS | `KernelState.AUDIT_DIAGNOSTICS` | `tra/kernel.py:84` |
| EMIT_PAYLOAD | `KernelState.EMIT_PAYLOAD` | `tra/kernel.py:85` |
| EXCEPTION_HANDLER | Audit-record type (TRA-040 design decision) | `tra/kernel.py:52-75` docstring |
| HALT_ERROR | `ConformanceFailure` exception | `tra/kernel.py:380` |

**Forward-only transitions:** `_transition()` enforces strict `<` ordering
(TRA-007, TRA-049). State advances only on ISA success.

### §2.2 Memory Model

| Segment | Mutability | Implementation |
|---|---|---|
| Immutable Config | Read-only | `BootstrapConfig` (frozen Pydantic model, TRA-018) |
| Runtime Context | Read/Write | `RuntimeContext` (Pydantic model with `arbitrary_types_allowed`) |
| Document Memory | Read-only | Source text passed to ISA functions |
| Audit Memory | Append-only | `AuditTrail` (JSONL append, `EvidenceRegistry` content-addressed) |

---

## §3 TRA-ISA: Instruction Set Architecture

### ANALYZE_DOCUMENT
- **Inputs:** Source Document, Immutable Config ✅
- **Outputs:** Document Profile, Structural Map ✅
- **Invariant:** node_count match ✅ (`StructuralMap.node_count` property)
- **Failure:** Malformed Markdown → `BrokenMarkdown` raised ✅ (TRA-E5-003)

### BUILD_GLOSSARY
- **Inputs:** Source, Document Profile, Active Domain Module ✅
- **Outputs:** Canonical Glossary, Forbidden Mappings ✅
- **Invariant:** One canonical mapping per recurring term ✅
- **Failure:** Glossary conflict → `GlossaryConflict` raised ✅

### BUILD_ENTITY_TABLE
- **Inputs:** Source Document ✅
- **Outputs:** Entity Table (all `mutable=False`) ✅
- **Invariant:** Entities immutable ✅ (Pydantic `frozen=True`)
- **Failure:** Entity ambiguity → logged via `recover_entity_ambiguity` ✅

### TRANSLATE_SEGMENT
- **Inputs:** Source Segment (per-leaf), Runtime Context ✅ (TRA-001 Phase 8)
- **Outputs:** Target Segment ✅
- **Invariant:** Factual qualifiers, numbers, epistemic markers preserved ✅
- **Failure:** UnknownTerm, CertaintyConflict raised/recovered ✅ (TRA-038)

### VERIFY_OUTPUT
- **Inputs:** Target, Source, Runtime Context ✅
- **Outputs:** Diagnostic Report ✅
- **Invariant:** All violations categorized by severity ✅
- **Failure:** None (always completes) ✅
- **Never self-scores:** ✅ (zero `confidence_note` references in control flow)

### REPAIR_SEGMENT
- **Inputs:** Target Segment, Source Segment, Diagnostic ✅
- **Outputs:** Repaired Target Segment ✅
- **Invariant:** No new violations introduced ✅ (re-verify after repair)
- **Failure:** `Unrecoverable` if higher-priority policy would be violated ✅

---

## §4 TRA-RUNTIME: Execution Context & State

Runtime Context fields match Spec §4 YAML schema:
`configuration`, `document_profile`, `glossary_cache`, `entity_table`,
`style_profile`, `unresolved_ambiguities`, `execution_log` ✅

---

## §5 TRA-POLICY: Arbitration & Conflict Resolution

### §5.1 Priority Stack (Immutable)

| Priority | Spec | Implementation |
|---|---|---|
| 1 | Factual Integrity | `PolicyPriority.FACTUAL_INTEGRITY = 1` ✅ |
| 2 | Structural Integrity | `PolicyPriority.STRUCTURAL_INTEGRITY = 2` ✅ |
| 3 | Entity Preservation | `PolicyPriority.ENTITY_PRESERVATION = 3` ✅ |
| 4 | Terminological Consistency | `PolicyPriority.TERMINOLOGICAL_CONSISTENCY = 4` ✅ |
| 5 | Epistemic Fidelity | `PolicyPriority.EPISTEMIC_FIDELITY = 5` ✅ |
| 6 | Target Fluency | `PolicyPriority.TARGET_FLUENCY = 6` ✅ |

### §5.2 Conflict Resolution Contract

- All 5 severity decision pairs arbitrated via `_POLICY_RESOLVER.wins()` ✅
  (TRA-072 + TRA-A5-013: Factual/Structural/Entity/Terminological/Epistemic
  vs Fluency)
- Decision + Evidence logged in Audit Memory ✅

---

## §6 TRA-EXCEPTIONS: Error Handling & Recovery

| Exception Code | Trigger | Recovery | Implementation |
|---|---|---|---|
| UNKNOWN_TERM | Term not in Glossary | Warning, preserve source | `recover_unknown_term` ✅ + EXCEPTION_HANDLER audit record ✅ |
| BROKEN_MARKDOWN | Source cannot be parsed | Blocking, best-effort, halt if critical | `recover_broken_markdown` ✅ (BLOCKING severity) |
| CERTAINTY_CONFLICT | Hedging conflicts | Warning, prioritize Epistemic Fidelity | `recover_certainty_conflict` ✅ (raised in LLM path) |
| ENTITY_AMBIGUITY | Entity or NL? | Warning, treat as Entity | `recover_entity_ambiguity` ✅ |
| GLOSSARY_CONFLICT | Two canonical mappings | Blocking, first occurrence canonical | `recover_glossary_conflict` ✅ |

---

## §7 TRA-QA: Verification & Diagnostics

- Evidence-based logging ✅ (never self-scores)
- Severity: BLOCKING / WARNING / INFO ✅
- Diagnostic fields: severity, subsystem, issue, evidence, action ✅
- `EXCEPTION_HANDLER` audit records for all exception types ✅

---

## §8 TRA-CONFORMANCE: Compliance Levels

| Level | Spec | Implementation |
|---|---|---|
| L1 Basic | Meaning + formatting | ✅ No zero-BLOCKING gate |
| L2 Professional | + terminology, entity | ✅ No zero-BLOCKING gate |
| L3 Strict | + glossary, diagnostics, audit trace | ✅ Zero-BLOCKING gate enforced in-band |
| L4 Forensic | + line-by-line evidence tracing | ✅ `evidence_trace.jsonl` + `ambiguity_register.json` |

---

## §9 TRA-MODULES: Extension Registry

| Module Type | Spec | Implementation |
|---|---|---|
| Language Modules | `zh-en.md` | `tra/modules/zh_en.py` (ZHENModule) ✅ |
| Domain Modules | `security.md`, `academic.md` | Plug-in via `ModuleRegistry.register()` ✅ |
| Formatting Modules | `markdown_strict.md` | Plug-in via `ModuleRegistry.register()` ✅ |

**Invariant:** Modules must not alter the Kernel or ISA ✅
(`tra/modules/` does not import `tra.kernel` or `tra.isa`)

**Module authoring guide:** `TRA-MODULE-AUTHORING.md` ✅ (TRA-100)

---

## Cross-Reference Summary

| Spec Section | Requirements | Implemented | Status |
|---|---|---|---|
| §1 Scope | 5 definitions | 5 | ✅ |
| §2 Kernel | 9 states + 4 memory segments | 9 + 4 | ✅ |
| §3 ISA | 6 instructions with contracts | 6 | ✅ |
| §4 Runtime | RuntimeContext fields | All present | ✅ |
| §5 Policy | 6 priorities + universal arbitration | 6 + 5 pairs | ✅ |
| §6 Exceptions | 5 exception types with recovery | 5 | ✅ |
| §7 QA | Evidence-based diagnostics | ✅ | ✅ |
| §8 Conformance | L1–L4 levels | 4 | ✅ |
| §9 Modules | Plug-in registry, no Kernel/ISA changes | ✅ | ✅ |

**Overall: TRA-SPECIFICATION.md §1–§9 fully implemented.**
