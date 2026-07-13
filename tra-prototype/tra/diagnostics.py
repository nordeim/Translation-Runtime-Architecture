"""Evidence schema, diagnostics, and the append-only audit registry (Spec §7).

Implements the EVIDENCE_SCHEMA.md contract: every translation decision is
atomically traceable to a rule, module directive, or LLM rationale. The
audit trail is append-only JSONL (one AuditRecord per line) so it streams
safely and survives partial runs.

Invariant (TRA "never self-score"): `confidence_note` is recorded for
debugging ONLY and is NEVER used by VERIFY/REPAIR to make decisions. Routing
is gated solely on evidence *presence* (empty evidence_chain -> RAISE_FLAG),
never on a numeric score.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .memory import Severity


class EvidenceType(StrEnum):
    TERM_MATCH = "term_match"
    ENTITY_PRESERVED = "entity_preserved"
    POLICY_ARBITRATION = "policy_arbitration"
    STRUCTURAL_MAPPING = "structural_mapping"
    LLM_DECISION = "llm_decision"
    HUMAN_OVERRIDE = "human_override"
    CONTEXTUAL_INFERENCE = "contextual_inference"


class EvidenceRecord(BaseModel):
    """A single atom of decision provenance (EVIDENCE_SCHEMA.md §2.2)."""

    id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
    type: EvidenceType
    rule_id: str | None = Field(
        None, description="e.g. 'ZH-EN-RULE#042' — must cite a real rule/module"
    )
    module: str = Field(..., description="e.g. 'modules.zh_en'")
    source_span: str = Field(..., description="Original text segment")
    target_span: str = Field(..., description="Translated text segment")
    rationale: str = Field(..., description="Human-readable explanation")
    confidence_note: float | None = Field(
        None, description="Recorded for debugging ONLY; never read by VERIFY/REPAIR"
    )


class AuditRecord(BaseModel):
    """One immutable line in the audit trace (EVIDENCE_SCHEMA.md §2.3)."""

    sequence_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    isa_instruction: str
    input_hash: str
    artifact_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_chain: list[str] = Field(
        default_factory=list, description="List of EvidenceRecord ids"
    )
    flags_raised: list[str] | None = Field(default=None)


class Diagnostic(BaseModel):
    """A VERIFY_OUTPUT violation (Spec §7)."""

    severity: Severity
    subsystem: str
    issue: str
    evidence: str
    action: str
    repaired: bool = False


class EvidenceRegistry:
    """Append-only store for EvidenceRecords, keyed by id."""

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def add(self, record: EvidenceRecord) -> str:
        self._records[record.id] = record
        return record.id

    def get(self, record_id: str) -> EvidenceRecord:
        return self._records[record_id]

    def __contains__(self, record_id: str) -> bool:
        return record_id in self._records

    def all(self) -> list[EvidenceRecord]:
        return list(self._records.values())


class AuditTrail:
    """Append-only JSONL audit trace (EVIDENCE_SCHEMA.md §4 storage).

    Each AuditRecord is serialized as one line. The trace is the artifact the
    L3 conformance checklist inspects for zero BLOCKING errors.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._seq = 0
        self._buffer: list[AuditRecord] = []
        self._flushed = 0

    def append(
        self,
        isa_instruction: str,
        input_hash: str,
        evidence_chain: list[str],
        artifact_snapshot: dict[str, Any] | None = None,
        flags_raised: list[str] | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            sequence_id=self._seq,
            isa_instruction=isa_instruction,
            input_hash=input_hash,
            evidence_chain=evidence_chain,
            artifact_snapshot=artifact_snapshot or {},
            flags_raised=flags_raised,
        )
        self._seq += 1
        self._buffer.append(record)
        return record

    def flush(self) -> None:
        """Persist buffered records to JSONL (append mode).

        The in-memory `_buffer` is NOT cleared — it is the full append-only
        log (load() re-reads from disk). Only records written since the last
        flush are appended, so re-flushing never duplicates.
        """
        if not self._buffer:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            for rec in self._buffer[self._flushed :]:
                fh.write(rec.model_dump_json() + "\n")
        self._flushed = len(self._buffer)

    def load(self) -> list[AuditRecord]:
        """Read all records from the JSONL file (empty if absent)."""
        if not self.path.exists():
            return []
        records: list[AuditRecord] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(AuditRecord.model_validate_json(line))
        return records
