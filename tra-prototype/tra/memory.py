"""Core data models for the TRA Runtime Context (Spec §4, §9).

All models are Pydantic v2. These define the contract for the Memory Model
segments and the ISA instruction inputs/outputs (TRA-ISA-REFERENCE.md).

Design note: `confidence_note` is recorded for debugging only and MUST NOT be
read by VERIFY or REPAIR (TRA "never self-score" invariant). It is retained on
the models but never influences control flow.
"""

from __future__ import annotations

from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PolicyPriority(int, Enum):
    """Immutable arbitration stack (Spec §5.1). Lower number = higher priority.

    The ordering is non-negotiable; higher priority always wins conflicts.
    """

    FACTUAL_INTEGRITY = 1
    STRUCTURAL_INTEGRITY = 2
    ENTITY_PRESERVATION = 3
    TERMINOLOGICAL_CONSISTENCY = 4
    EPISTEMIC_FIDELITY = 5
    TARGET_FLUENCY = 6


class Severity(StrEnum):
    """Diagnostic severity (Spec §7, TRA-EXCEPTIONS)."""

    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class ConformanceLevel(StrEnum):
    """Conformance dial (Spec §8)."""

    L1_BASIC = "L1_BASIC"
    L2_PROFESSIONAL = "L2_PROFESSIONAL"
    L3_STRICT = "L3_STRICT"
    L4_FORENSIC = "L4_FORENSIC"


class EntityType(StrEnum):
    PRODUCT = "product"
    API = "api"
    CLI = "cli"
    VERSION = "version"
    ACRONYM = "acronym"


class GlossaryStatus(StrEnum):
    CANONICAL = "canonical"
    CONTEXT_SENSITIVE = "context_sensitive"


class NodeKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    LINK = "link"
    ANCHOR = "anchor"
    BLOCKQUOTE = "blockquote"
    HR = "hr"


class DocumentProfile(BaseModel):
    """Output of ANALYZE_DOCUMENT (TRA-ISA-REFERENCE.md §ANALYZE_DOCUMENT).

    Fields match the ISA contract exactly, including `evidence_style`
    retained for spec fidelity (TRA-ISA-REFERENCE.md), though Spec §4 omits it.
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(..., description="RFC | Advisory | Guide | README | ...")
    register_: str = Field(
        ...,
        alias="register",
        description="Formal/Authoritative/Instructional/...",
    )
    intent: str = Field(..., description="Standardize Protocol | ...")
    audience: str = Field(..., description="Intended reader")
    evidence_style: str | None = Field(
        None, description="How evidence is marshalled (per ISA contract)"
    )


class StructuralNode(BaseModel):
    """A single node in the Markdown structural map (AST representation)."""

    kind: NodeKind
    level: int | None = None  # heading/list nesting depth
    text: str | None = None
    children: list[StructuralNode] = Field(default_factory=list)
    # Cross-reference metadata (ANCHOR_RESOLUTION.md):
    original_slug: str | None = None
    placeholder: str | None = None  # __HEADER_N__ token during translation
    is_no_translate_zone: bool = False  # code blocks / inline code
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructuralMap(BaseModel):
    """Hierarchical tree of all Markdown nodes (ANALYZE_DOCUMENT output).

    Invariant: node_count must equal the source document's structural node
    count (TRA-ISA-REFERENCE.md ANALYZE_DOCUMENT invariant).
    """

    nodes: list[StructuralNode] = Field(default_factory=list)

    @property
    def node_count(self) -> int:
        def walk(nodes: list[StructuralNode]) -> int:
            return sum(1 + walk(n.children) for n in nodes)

        return walk(self.nodes)


class GlossaryEntry(BaseModel):
    """A canonical terminology mapping (BUILD_GLOSSARY output).

    Immutable by spec (TRA-ISA-REFERENCE.md §BUILD_GLOSSARY Outputs): once
    emitted, a glossary entry must not be mutated — VERIFY and REPAIR read it
    as a stable contract.
    """

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    status: GlossaryStatus = GlossaryStatus.CANONICAL
    rule_id: str | None = Field(
        None, description="e.g. 'ZH-EN-RULE#042' — provenance for evidence"
    )
    confidence_note: float | None = Field(
        None, description="Recorded for debugging ONLY; never read by VERIFY/REPAIR"
    )


class ForbiddenMapping(BaseModel):
    """A mapping explicitly disallowed (BUILD_GLOSSARY output). Immutable."""

    model_config = ConfigDict(frozen=True)

    source: str
    forbidden_target: str
    rationale: str


class Entity(BaseModel):
    """An immutable identifier isolated from natural-language translation.

    Spec §3 / TRA-ISA-REFERENCE.md §BUILD_ENTITY_TABLE: entities are never
    translated, casing/punctuation preserved verbatim. `frozen=True`
    enforces the immutability claim at the model level (TRA-018).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: EntityType
    mutable: bool = False  # Invariant: entities are never translated
    context: str | None = None


class StyleProfile(BaseModel):
    """Voice / complexity / epistemic preferences for the target (Spec §4)."""

    voice: str = "Passive/Objective"
    sentence_complexity: str = "High"
    epistemic_mapping: dict[str, str] = Field(default_factory=dict)
    punctuation_rules: dict[str, str] = Field(default_factory=dict)


class RuntimeContext(BaseModel):
    """The mutable 'memory' of the VM (Spec §4)."""

    configuration: dict[str, Any] = Field(default_factory=dict)
    document_profile: DocumentProfile | None = None
    glossary_cache: list[GlossaryEntry] = Field(default_factory=list)
    forbidden_mappings: list[ForbiddenMapping] = Field(default_factory=list)
    entity_table: list[Entity] = Field(default_factory=list)
    style_profile: StyleProfile = Field(default_factory=StyleProfile)
    structural_map: StructuralMap | None = None
    unresolved_ambiguities: list[str] = Field(default_factory=list)
    execution_log: list[str] = Field(default_factory=list)
    repair_history: list[RepairAttempt] = Field(default_factory=list)


class RepairAttempt(BaseModel):
    """One surgical REPAIR_SEGMENT iteration (L4 forensic artifact, §6.4.2).

    Recorded per attempt so a forensic review can reconstruct exactly which
    decision was applied, in what order, and whether it resolved the violation.
    """

    segment_index: int = Field(..., description="Index of the repaired leaf segment")
    attempt: int = Field(..., description="1-based retry count within the repair loop")
    subsystem: str = Field(
        ..., description="Diagnostic subsystem that triggered repair"
    )
    issue: str = Field(..., description="Human-readable diagnostic issue")
    before: str = Field(..., description="Target text prior to this repair")
    after: str = Field(..., description="Target text after this repair")
    evidence_id: str | None = Field(
        None, description="EvidenceRecord produced by repair"
    )
    resolved: bool = Field(
        ..., description="True if re-verify reported zero BLOCKING for this segment"
    )


StructuralNode.model_rebuild()
