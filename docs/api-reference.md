# TRA Prototype Engine — API Reference

**Public API surface of the `tra-prototype` engine.**

This document lists all public classes, functions, and CLI commands
available to callers. Internal helpers (prefixed with `_`) are omitted.

---

## 1. Kernel (`tra.kernel`)

### `TRAKernel`

```python
class TRAKernel:
    def __init__(
        self,
        config: BootstrapConfig,
        *,
        interactive: bool = False,
        deterministic: bool = True,
        registry: ModuleRegistry | None = None,
        force_unrecoverable: bool = False,
    ) -> None

    def run(
        self,
        source: str | Path,
        *,
        llm_translate: Callable[[str, RuntimeContext], str] | None = None,
    ) -> str
```

The main entry point. `run()` executes the full 9-state pipeline
(BOOTSTRAP → EMIT_PAYLOAD) and returns the translated markdown.

**Parameters:**
- `config` — frozen `BootstrapConfig` (tvm_bootstrap)
- `interactive` — if True, pause for HITL review on UNRECOVERABLE
- `deterministic` — if True (default), use content-addressed clock for
  byte-reproducible audit trail (TRA-013)
- `registry` — optional `ModuleRegistry` for plug-in module dispatch
- `force_unrecoverable` — debug flag (TRA-E5-005); injects synthetic
  BLOCKING diagnostic to force the HITL path for e2e testing
- `llm_translate` — optional callback for LLM-based translation (DI seam,
  TRA-D5-002)

### `KernelState`

```python
class KernelState(StrEnum):
    BOOTSTRAP = "BOOTSTRAP"
    INITIALIZE_RUNTIME = "INITIALIZE_RUNTIME"
    ANALYZE_DOCUMENT = "ANALYZE_DOCUMENT"
    BUILD_ARTIFACTS = "BUILD_ARTIFACTS"
    EXECUTE_TRANSLATION = "EXECUTE_TRANSLATION"
    VERIFY_OUTPUT = "VERIFY_OUTPUT"
    REPAIR_IF_NEEDED = "REPAIR_IF_NEEDED"
    AUDIT_DIAGNOSTICS = "AUDIT_DIAGNOSTICS"
    EMIT_PAYLOAD = "EMIT_PAYLOAD"
```

The 9 canonical lifecycle states (Spec §2.1). Forward-only transitions
enforced by `_transition()`.

---

## 2. ISA Instructions (`tra.isa`)

### `analyze_document(source, ctx, audit) -> tuple[DocumentProfile, StructuralMap]`

Extract macro-structure + metadata; initialize RuntimeContext.

### `build_glossary(source, profile, ctx, evidence, audit) -> tuple[list[GlossaryEntry], list[ForbiddenMapping]]`

Establish canonical terminology; flag drift targets.

### `build_entity_table(source, structural_map, ctx, evidence, audit) -> list[Entity]`

Isolate immutable identifiers (product names, APIs, versions). All
`mutable=False`.

### `translate_segment(source_segment, ctx, cache, evidence, audit, *, llm_translate=None) -> TranslationResult`

Generate target-language equivalent of one source segment. Cache-first;
deterministic rule path when no LLM seam is supplied.

### `verify_output(target, source, ctx, audit) -> list[Diagnostic]`

Audit target against source + runtime constraints. Checks: structural
(heading/table/list/blockquote/HR/fence counts), factual (version/date
preservation), entity, terminology, epistemic. Never self-scores.

### `repair_segment(target_segment, source_segment, diagnostic, ctx, evidence, audit, *, attempt=1, max_retries=3, segment_index=0) -> str`

Surgically resolve a single diagnostic. Raises `Unrecoverable` if the
repair would introduce new BLOCKING or violate a higher-priority policy.

---

## 3. Memory Model (`tra.memory`)

### `RuntimeContext`

```python
class RuntimeContext(BaseModel):
    configuration: dict[str, Any]
    document_profile: DocumentProfile | None
    glossary_cache: list[GlossaryEntry]
    entity_table: list[Entity]
    style_profile: StyleProfile
    structural_map: StructuralMap | None
    unresolved_ambiguities: list[str]
    execution_log: list[str]
    repair_history: list[RepairAttempt]
    module: LanguageModuleProtocol | None
    anchor_registry: AnchorRegistry | None
```

The mutable runtime state (Spec §2.2, §4). Read/write per ISA instruction
contracts.

### `StructuralMap`

```python
class StructuralMap(BaseModel):
    nodes: list[StructuralNode]

    @property
    def node_count(self) -> int

    def iter_leaf_segments(self) -> Iterable[tuple[int, StructuralNode]]
```

Hierarchical tree of all Markdown nodes. `iter_leaf_segments()` yields
translatable leaf segments (HEADING, PARAGRAPH, LIST_ITEM, TABLE_CELL)
in document order (TRA-001 Phase 8).

### `PolicyPriority` (enum)

```python
class PolicyPriority(int, Enum):
    FACTUAL_INTEGRITY = 1
    STRUCTURAL_INTEGRITY = 2
    ENTITY_PRESERVATION = 3
    TERMINOLOGICAL_CONSISTENCY = 4
    EPISTEMIC_FIDELITY = 5
    TARGET_FLUENCY = 6
```

Immutable arbitration stack (Spec §5.1). Lower number = higher priority.

### `Severity` (enum)

```python
class Severity(StrEnum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"
```

### `ConformanceLevel` (enum)

```python
class ConformanceLevel(StrEnum):
    L1_BASIC = "L1_BASIC"
    L2_PROFESSIONAL = "L2_PROFESSIONAL"
    L3_STRICT = "L3_STRICT"
    L4_FORENSIC = "L4_FORENSIC"
```

---

## 4. Policy Engine (`tra.policy`)

### `PolicyResolver`

```python
class PolicyResolver:
    def __init__(self, priorities: list[PolicyPriority]) -> None
    def wins(self, a: PolicyPriority, b: PolicyPriority) -> bool
```

Deterministic arbitration. `wins(a, b)` returns True if `a` has higher
priority (lower number) than `b`. Called for all 5 severity decision pairs
in `verify_output` (TRA-072 + TRA-A5-013).

---

## 5. Cache (`tra.cache`)

### `TranslationCache`

```python
class TranslationCache:
    def __init__(self, directory: str | Path, enabled: bool = True) -> None
    def get(self, key: str) -> TranslationResult | None
    def set(self, key: str, result: TranslationResult) -> None
    def invalidate(self, pattern: str | None = None) -> int
```

SQLite-backed deterministic cache (diskcache). HMAC-SHA256 signed
(TRA-079). No TTL — technical facts are static.

### `TranslationResult`

```python
class TranslationResult(BaseModel):
    translation: str
    evidence_ids: list[str]
    cache_hit: bool
    created_at: str | None
```

---

## 6. Exceptions (`tra.exceptions`)

```python
class TRAException(Exception):           # Base class
class UnknownTerm(TRAException):          # Spec §6 UNKNOWN_TERM
class BrokenMarkdown(TRAException):       # Spec §6 BROKEN_MARKDOWN
class CertaintyConflict(TRAException):    # Spec §6 CERTAINTY_CONFLICT
class EntityAmbiguity(TRAException):      # Spec §6 ENTITY_AMBIGUITY
class GlossaryConflict(TRAException):     # Spec §6 GLOSSARY_CONFLICT
class Unrecoverable(TRAException):        # REPAIR_SEGMENT can't proceed
class ConformanceFailure(TRAException):   # L3+ gate failed
```

---

## 7. Modules (`tra.modules`)

### `ModuleRegistry`

```python
class ModuleRegistry:
    def register(self, module: ModuleInterface) -> None
    def unregister(self, name: str) -> None
    def all(self) -> list[ModuleInterface]
```

### `ModuleInterface` (dataclass)

```python
@dataclass
class ModuleInterface:
    name: str
    kind: str  # "language" | "domain" | "formatting"
    get_glossary_mappings: Callable[[], dict[str, str]]
    get_style_profile: Callable[[], object]
    apply_rules: Callable[[str, str], str]
    is_forbidden: Callable[[str, str], bool]
    get_forbidden_targets: Callable[[], dict[str, str]]
    entity_type_hint: Callable[[str], object | None]
    apply_zh_rules: Callable[[str], str]
    metadata: dict[str, Any]
```

### `build_default_registry() -> ModuleRegistry`

Returns a registry with the bundled ZH-EN module registered.

### `LanguageModuleProtocol` (Protocol)

```python
@runtime_checkable
class LanguageModuleProtocol(Protocol):
    name: str
    kind: str
    def get_glossary_mappings(self) -> dict[str, str]: ...
    def get_style_profile(self) -> object: ...
    def is_forbidden(self, source: str, target: str) -> bool: ...
    def get_forbidden_targets(self) -> dict[str, str]: ...
    def entity_type_hint(self, token: str) -> object | None: ...
    def apply_zh_rules(self, text: str) -> str: ...
    def apply_rules(self, source: str, direction: str) -> str: ...
```

---

## 8. CLI (`tra_cli`)

```bash
# Translate a markdown document through the full pipeline.
python -m tra_cli translate input.md --level L3 -o output.md
  --lang zh-en          # Language pair override
  --level L1|L2|L3|L4   # Conformance level
  --interactive         # Pause for HITL review
  --force-unrecoverable # Debug: force HITL path (TRA-E5-005)

# Standalone conformance gate (zero BLOCKING = PASS).
python -m tra_cli validate input.md output.md --level L3

# Summarize an audit trail (+ conformance report).
python -m tra_cli audit ./audit_trace.jsonl --report

# Invalidate deterministic cache.
python -m tra_cli cache-clear [--pattern "translation:*"]
```

---

## 9. Diagnostics (`tra.diagnostics`)

### `AuditTrail`

```python
class AuditTrail:
    def append(
        self,
        isa_instruction: str,
        input_hash: str,
        evidence_chain: list[str],
        artifact_snapshot: dict[str, Any] | None = None,
        flags_raised: list[str] | None = None,
    ) -> AuditRecord
    def flush(self) -> None
```

Append-only audit memory (Spec §2.2). JSONL serialization to
`audit_trace.jsonl`.

### `EvidenceRegistry`

```python
class EvidenceRegistry:
    def add(self, record: EvidenceRecord) -> str  # returns content-addressed ID
    def all(self) -> list[EvidenceRecord]
```

Content-addressed evidence store. IDs are SHA-256 of the canonical record
(TRA-013).

---

## 10. HITL (`tra.hitl`)

### `review_decision(uncertainty, source_context, candidate, *, on_override=None) -> tuple[str, str]`

Pause for human review. Returns `(resolution, text)` where resolution is
`"accept"`, `"override"`, or `"skip"`.

### `format_unrecoverable(ctx, diagnostic, source) -> tuple[str, str]`

Build the `(uncertainty, source_context)` shown for an UNRECOVERABLE.
