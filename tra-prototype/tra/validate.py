"""Standalone verification of a candidate translation (Phase 5.1.4).

`tra validate` runs the VERIFY_OUTPUT contract against a *candidate* target
markdown (not produced by this run) and reports evidence-based diagnostics.
It reuses the same ISA instructions the Kernel uses, so a human-edited or
LLM-produced output is judged by the identical standard as a pipeline run.

Gate rule (Spec §8 / Conformance Guide): a candidate passes iff it raises
zero BLOCKING diagnostics. WARNINGs are reported but do not fail L3+.
"""

from __future__ import annotations

from pathlib import Path

from .config import BootstrapConfig
from .diagnostics import AuditTrail, Diagnostic, EvidenceRegistry
from .isa import (
    analyze_document,
    build_entity_table,
    build_glossary,
    verify_output,
)
from .memory import ConformanceLevel, RuntimeContext, Severity


class ValidationReport:
    """Result of a standalone validation pass."""

    def __init__(
        self,
        diagnostics: list[Diagnostic],
        level: ConformanceLevel,
    ) -> None:
        self.diagnostics = diagnostics
        self.level = level

    @property
    def blocking(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == Severity.BLOCKING]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        # L3/L4 require zero BLOCKING; BLOCKING always fails at any level.
        return not self.blocking

    def summary(self) -> dict[str, int]:
        return {
            "blocking": len(self.blocking),
            "warnings": len(self.warnings),
            "info": len([d for d in self.diagnostics if d.severity == Severity.INFO]),
        }


def validate_translation(
    source: str | Path,
    candidate: str | Path,
    config: BootstrapConfig,
    audit: AuditTrail | None = None,
) -> ValidationReport:
    """Validate `candidate` against `source` under `config.conformance_level`.

    Builds the RuntimeContext (ANALYZE + BUILD artifacts) then runs
    VERIFY_OUTPUT on the candidate. Does NOT translate — purely an audit of
    the candidate against the source and runtime constraints.
    """
    if isinstance(source, Path):
        source = source.read_text(encoding="utf-8")
    if isinstance(candidate, Path):
        candidate = candidate.read_text(encoding="utf-8")
    if audit is None:
        audit = AuditTrail(config.audit_trace)

    ctx = RuntimeContext(configuration=config.model_dump())
    evidence = EvidenceRegistry()

    _profile, _smap = analyze_document(source, ctx, audit)
    build_glossary(source, _profile, ctx, evidence, audit)
    build_entity_table(source, _smap, ctx, evidence, audit)

    diagnostics = verify_output(candidate, source, ctx, audit)
    return ValidationReport(diagnostics, config.conformance_level)
