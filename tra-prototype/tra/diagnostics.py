"""Evidence schema, diagnostics, and the append-only audit registry (Spec §7).

Implements the EVIDENCE_SCHEMA.md contract: every translation decision is
atomically traceable to a rule, module directive, or LLM rationale. The
audit trail is append-only JSONL (one AuditRecord per line) so it streams
safely and survives partial runs.

Invariant (TRA "never self-score"): `confidence_note` is recorded for
debugging ONLY and is NEVER used by VERIFY/REPAIR to make decisions. Routing
is gated solely on evidence *presence* (empty evidence_chain -> RAISE_FLAG),
never on a numeric score.

Reproducibility (TRA-013): evidence IDs are content-addressed
(``ev_{sha256(canonical_record)[:12]}``) and timestamps are injectable via
``AuditTrail(clock=...)``. Two runs of identical source produce byte-identical
``audit_trace.jsonl`` and ``evidence_trace.jsonl`` — required for L4 forensic
hash-chain validation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

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


def _content_addressed_id(record: EvidenceRecord) -> str:
    """Deterministic evidence ID: SHA-256 over the canonical record content.

    Two records with identical content produce the same ID. This makes the
    audit trail byte-reproducible across runs (TRA-013) — required for L4
    forensic hash-chain validation. The ``id`` field itself is excluded from
    the hash (it's the output).
    """
    payload = {
        "type": record.type.value,
        "rule_id": record.rule_id,
        "module": record.module,
        "source_span": record.source_span,
        "target_span": record.target_span,
        "rationale": record.rationale,
        "confidence_note": record.confidence_note,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return f"ev_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]}"


class EvidenceRecord(BaseModel):
    """A single atom of decision provenance (EVIDENCE_SCHEMA.md §2.2)."""

    # ID is assigned by EvidenceRegistry.add (content-addressed, TRA-013).
    # The default_factory is a fallback for direct construction outside the
    # registry (e.g., tests); production code goes through registry.add which
    # overwrites the ID with the content-addressed value.
    id: str = Field(default="")
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
    # Timestamp is injected by AuditTrail.append (TRA-013) to make the trail
    # byte-reproducible. The default_factory is a fallback for direct
    # construction (e.g., loading from disk).
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    isa_instruction: str
    input_hash: str
    artifact_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_chain: list[str] = Field(
        default_factory=list, description="List of EvidenceRecord ids"
    )
    flags_raised: list[str] | None = Field(default=None)


class Diagnostic(BaseModel):
    """A VERIFY_OUTPUT violation (Spec §7).

    TRA-A7-002 (round 7): `segment_index` is the index of the leaf segment
    the violation applies to, or None for whole-document diagnostics
    (structural, factual). Per-segment diagnostics (terminology, entity,
    epistemic) set it to the matched leaf's index so _repair_loop can plumb
    it to repair_segment -> RepairAttempt.segment_index for L4 forensic
    traceability.
    """

    severity: Severity
    subsystem: str
    issue: str
    evidence: str
    action: str
    repaired: bool = False
    segment_index: int | None = None


class EvidenceRegistry:
    """Append-only store for EvidenceRecords, keyed by content-addressed id."""

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def add(self, record: EvidenceRecord) -> str:
        """Assign a content-addressed ID and store the record.

        Returns the ID. Two records with identical content produce the same
        ID (TRA-013 reproducibility). If the record already has a non-empty
        ``id`` (e.g., loaded from disk), it is preserved.
        """
        if not record.id:
            # EvidenceRecord is not frozen, so mutate in place — this keeps
            # existing caller references (e.g., fixtures) valid after add().
            record.id = _content_addressed_id(record)
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

    Reproducibility (TRA-013): the ``clock`` callable is injected at
    construction. Production code uses the default ``datetime.now(UTC)``;
    tests can inject a deterministic clock (e.g., a fixed timestamp derived
    from the source hash) to produce byte-identical trails across runs.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
        truncate: bool = False,
    ) -> None:
        self.path = Path(path)
        self._seq = 0
        self._buffer: list[AuditRecord] = []
        self._flushed = 0
        self._clock = clock or (lambda: datetime.now(UTC))
        # TRA-E6-001 (round 6): truncate the audit trace file at construction
        # so each CLI run starts fresh. Previously, the file was opened in
        # append mode, so reusing the default CLI path across runs accumulated
        # records from prior runs — breaking TRA-013 byte-reproducibility.
        # `truncate=True` is opt-in (used by the kernel); tests that need
        # append behavior (e.g., test_audit_trail_append_and_load) use the
        # default `truncate=False`.
        if truncate and self.path.exists():
            self.path.unlink()

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
            timestamp=self._clock(),
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
