# Architecture Decision Records (ADRs)

**TRA Prototype Engine — key architectural decisions and their rationale.**

Each ADR documents a significant architectural choice, the alternatives
considered, and the rationale for the chosen approach. ADRs are immutable
once committed; superseded ADRs are marked with a "Superseded by ADR-XXX"
header.

---

## ADR-001: Immutable Kernel + Plug-in Modules (Spec §2, §9)

**Status:** Accepted (original design, Spec §2 + §9)
**Date:** Phase 0

### Context
The TRA spec defines a Kernel (immutable state machine) and Modules
(mutable/extensible plug-ins). The implementation must enforce this
separation.

### Decision
The Kernel (`tra/kernel.py`) and ISA (`tra/isa.py`) are immutable —
no module code imports or patches them. Modules register through
`ModuleRegistry.register()` and are selected by `_select_module()` based
on `config.language_pair`. The `LanguageModuleProtocol` (Protocol class
in `tra/modules/base.py`) types the structural contract.

### Alternatives Considered
1. **Inheritance** — modules subclass the Kernel. Rejected: breaks
   immutability, couples module lifecycle to kernel lifecycle.
2. **Monkey-patching** — modules patch ISA functions at runtime. Rejected:
   fragile, untestable, violates Spec §9 "must not alter the Kernel or ISA".

### Consequences
- New language/domain/formatting modules extend behavior without touching
  core code.
- The `_module(ctx)` helper (isa.py) provides a singleton fallback for
  direct ISA calls in tests (backward compat).

---

## ADR-002: Deterministic Audit Trail (TRA-013)

**Status:** Accepted
**Date:** Phase 0 (TRA-013 fix in Round 2)

### Context
L4 forensic conformance requires byte-identical `audit_trace.jsonl` across
runs of identical source. Wall-clock timestamps make this impossible.

### Decision
The kernel uses a content-addressed deterministic clock
(`_deterministic_clock`) seeded from the source hash. All audit records
in a single run share the same timestamp. Evidence IDs are content-addressed
(SHA-256 of the canonical record).

### Alternatives Considered
1. **Wall-clock timestamps** — rejected: breaks byte-reproducibility.
2. **Run-counter only** — rejected: loses temporal ordering within a run.

### Consequences
- Two cold-cache L4 runs of the same source produce byte-identical
  `audit_trace.jsonl` and `evidence_trace.jsonl`.
- The absolute sha256 changes when the audit-trail content changes (e.g.,
  new audit records added by remediation), but the within-HEAD invariant
  holds.

---

## ADR-003: Pydantic v2 for Data Models

**Status:** Accepted
**Date:** Phase 0

### Context
The spec defines rich data models (RuntimeContext, GlossaryEntry, Entity,
StructuralMap, Diagnostic, EvidenceRecord, etc.) with validation
requirements.

### Decision
Use Pydantic v2 `BaseModel` for all data models. Frozen models for
immutable segments (Entity, GlossaryEntry). `ConfigDict(arbitrary_types_allowed=True)`
for Protocol fields (LanguageModuleProtocol, AnchorRegistry).

### Alternatives Considered
1. **dataclasses** — rejected: no built-in validation, no JSON schema.
2. **attrs** — rejected: less ecosystem support than Pydantic.

### Consequences
- All models validate at construction time.
- `model_copy(update={...})` for frozen-model updates (Entity.mutable=False).
- `model_rebuild()` needed for circular-import forward references
  (AnchorRegistry in memory.py).

---

## ADR-004: Dependency Injection for LLM Seam (TRA-D5-002)

**Status:** Accepted
**Date:** Round 5 (commit `e75997f`)

### Context
The LLM seam (`llm_translate` callback) was originally injected via
module-level monkeypatching of `tra.kernel.translate_segment`. This was
fragile — any rename broke tests silently.

### Decision
`TRAKernel.run()` accepts an optional `llm_translate: Callable[[str,
RuntimeContext], str] | None` keyword argument. The kernel forwards it
to `translate_segment()` via `_execute_translation(llm_translate=...)`.

### Alternatives Considered
1. **Constructor injection** — `TRAKernel(cfg, llm_translate=callback)`.
   Rejected: the LLM may not be available at kernel construction time.
2. **Global registry** — rejected: global state, not testable.

### Consequences
- The e2e test suite and `e2e_test.py` both use DI (no monkeypatching).
- When an LLM is supplied, whole-doc translation is used (not per-leaf)
  because LLMs typically translate whole documents.

---

## ADR-005: Per-Leaf Segment Translation (TRA-001 Phase 8)

**Status:** Accepted
**Date:** Round 5 (commit `f782043`)

### Context
Spec §3 TRANSLATE_SEGMENT mandates leaf-level translation (sentence, list
item, table cell, heading). The prototype previously translated the whole
document in one call.

### Decision
`StructuralMap.iter_leaf_segments()` yields `(index, StructuralNode)` tuples
for HEADING, PARAGRAPH, LIST_ITEM, TABLE_CELL nodes with non-None text.
`_execute_translation` walks these leaves, calls `translate_segment` per
leaf, and re-assembles via text replacement. Per-leaf inline-code protection
ensures code blocks within paragraphs are protected.

When an LLM callback is supplied, whole-doc translation is used instead
(see ADR-004).

### Alternatives Considered
1. **AST-based reassembly** — reconstruct the markdown from the translated
   structural map. Rejected: too complex, loses formatting fidelity.
2. **Sentence-level splitting** — split paragraphs into sentences.
   Rejected: the spec says "leaf node", not "sentence".

### Consequences
- Per-segment cache keys (better cache granularity).
- Per-segment evidence chains (better L4 forensic trace).
- Multiple TRANSLATE_SEGMENT audit records per document.
- Text replacement approach may fail if the same text appears in multiple
  leaves (mitigated by first-occurrence replacement + document-order walk).

---

## ADR-006: HMAC-SHA256 Cache Integrity (TRA-079)

**Status:** Accepted
**Date:** Round 5 (commit `57997a8`)

### Context
The cache stores JSON strings (TRA-077, OWASP A08 fix). An attacker who
can write to the cache directory could inject bogus translations.

### Decision
Each cache entry is stored as `"{hmac_hex}:{json_value}"` where the HMAC
is SHA-256 over the JSON value using a fixed app-level key. On read, the
HMAC is verified; tampered entries are treated as cache misses.

### Alternatives Considered
1. **Per-install random key** — stronger but breaks cache sharing across
   installs. Rejected: the cache is per-install anyway (diskcache).
2. **Environment-variable key** — rejected: adds configuration burden for
   minimal security gain in the single-user-dev threat model.

### Consequences
- Tampered cache entries are silently rejected (cache miss).
- Old-format entries (no HMAC prefix) are treated as cache misses.
- The HMAC key is in the source code (not cryptographically secret) —
  this is defense-in-depth, not a complete security solution.

---

## ADR-007: EXCEPTION_HANDLER as Audit Record (TRA-040)

**Status:** Accepted (pending spec clarification)
**Date:** Round 5 (commit `f782043`)

### Context
Spec §2.1's stateDiagram shows EXCEPTION_HANDLER and HALT_ERROR as states.
The implementation treats them as audit-record types
(`isa_instruction="EXCEPTION_HANDLER"`).

### Decision
EXCEPTION_HANDLER is a side-channel action (entered from ANY state when a
TRAException is raised, returns to calling state or halts). Modeling it as
a state would require complex transitions (any → EXCEPTION_HANDLER → any)
that break the forward-only invariant. HALT_ERROR is a terminal condition
(kernel raises ConformanceFailure which exits the pipeline).

### Alternatives Considered
1. **Add EXCEPTION_HANDLER/HALT_ERROR to KernelState enum** — rejected:
   breaks forward-only invariant, adds complexity for no behavioral benefit.
2. **Wait for spec clarification** — the design is documented in the
   KernelState docstring; if the spec author confirms they should be
   states, the enum can be extended.

### Consequences
- The audit trail records EXCEPTION_HANDLER as an `isa_instruction` value,
  not a `KernelState` transition.
- L4 auditors can still reconstruct the exception flow from the audit trail.

---

## ADR-008: Mutation Testing via mutmut (TRA-094)

**Status:** Accepted
**Date:** Round 5 (commit `6056fc1`)

### Context
No continuous mutation testing in CI. Manual probes at each audit round
suggested ~80% mutation score but weren't automated.

### Decision
`mutmut>=3.0` added to dev deps. `[tool.mutmut]` configured in
`pyproject.toml` with `paths_to_mutate = "tra"`. Expected mutation
score: ≥80%.

### Alternatives Considered
1. **cosmic-ray** — rejected: less maintained, more complex setup.
2. **Manual probes only** — rejected: not continuous, error-prone.

### Consequences
- `mutmut run` applies mutations to `tra/` and checks if the test suite
  catches each one.
- Mutations that survive indicate test-coverage gaps.
