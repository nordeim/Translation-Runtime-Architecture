"""TRA Kernel — the immutable sequential state machine (Spec §2 / TRA-KERNEL).

BOOTSTRAP -> INITIALIZE_RUNTIME -> ANALYZE_DOCUMENT -> BUILD_ARTIFACTS
(glossary + entity) -> EXECUTE_TRANSLATION -> VERIFY_OUTPUT ->
REPAIR_IF_NEEDED (loop) -> AUDIT_DIAGNOSTICS -> EMIT_PAYLOAD.

State transitions are triggered ONLY by successful completion of ISA
instructions. The Kernel must not skip instructions.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path

import yaml

from .cache import TranslationCache
from .config import BootstrapConfig
from .diagnostics import (
    AuditTrail,
    Diagnostic,
    EvidenceRegistry,
)
from .exceptions import TRAException, Unrecoverable
from .isa import (
    analyze_document,
    build_entity_table,
    build_glossary,
    repair_segment,
    translate_segment,
    verify_output,
)
from .memory import (
    ConformanceLevel,
    DocumentProfile,
    RuntimeContext,
    Severity,
    StructuralMap,
)
from .modules.zh_en import ZHENModule
from .recovery import route_exception


class KernelState(StrEnum):
    """Canonical lifecycle states (Spec §2.1)."""

    BOOTSTRAP = "BOOTSTRAP"
    INITIALIZE_RUNTIME = "INITIALIZE_RUNTIME"
    ANALYZE_DOCUMENT = "ANALYZE_DOCUMENT"
    BUILD_ARTIFACTS = "BUILD_ARTIFACTS"
    EXECUTE_TRANSLATION = "EXECUTE_TRANSLATION"
    VERIFY_OUTPUT = "VERIFY_OUTPUT"
    REPAIR_IF_NEEDED = "REPAIR_IF_NEEDED"
    AUDIT_DIAGNOSTICS = "AUDIT_DIAGNOSTICS"
    EMIT_PAYLOAD = "EMIT_PAYLOAD"


# Spec order — the only legal transition sequence.
_KERNEL_ORDER: list[KernelState] = [
    KernelState.BOOTSTRAP,
    KernelState.INITIALIZE_RUNTIME,
    KernelState.ANALYZE_DOCUMENT,
    KernelState.BUILD_ARTIFACTS,
    KernelState.EXECUTE_TRANSLATION,
    KernelState.VERIFY_OUTPUT,
    KernelState.REPAIR_IF_NEEDED,
    KernelState.AUDIT_DIAGNOSTICS,
    KernelState.EMIT_PAYLOAD,
]


# Control characters that must never enter the pipeline (§6.5.3). Newlines,
# tabs, and the common Unicode separators are preserved (markdown needs them);
# null / C0 control / Unicode bidi overrides / BOM are stripped.
_CONTROL_RE = re.compile(
    "[" + "\x00-\x08\x0b\x0c\x0e-\x1f\x7f" + "\u202a-\u202e" + "\ufeff" + "]"
)


def _sanitize_input(text: str) -> str:
    """Input validation & sanitization (Phase 6.5.3).

    Strips control characters that could corrupt the markdown stream or
    smuggle bidirectional-override attacks, without touching legitimate
    whitespace. Pure: never raises; returns a safe copy.
    """
    return _CONTROL_RE.sub("", text)


class TRAKernel:
    """Runs the full TRA pipeline on a source document."""

    def __init__(self, config: BootstrapConfig, *, interactive: bool = False) -> None:
        self.config = config
        self.interactive = interactive
        self.cache = TranslationCache(
            config.cache_directory, enabled=config.cache_enabled
        )
        self.evidence = EvidenceRegistry()
        self.audit = AuditTrail(config.audit_trace)
        self.ctx = RuntimeContext(
            configuration=config.model_dump(),
            style_profile=ZHENModule().get_style_profile(),
        )
        self.state = KernelState.BOOTSTRAP

    def _transition(self, next_state: KernelState) -> None:
        if next_state not in _KERNEL_ORDER:
            raise TRAException(f"Illegal state: {next_state}")
        # Strictly forward through the canonical order.
        idx = _KERNEL_ORDER.index(next_state)
        if idx < _KERNEL_ORDER.index(self.state):
            raise TRAException(
                f"Illegal backward transition: {self.state} -> {next_state}"
            )
        self.state = next_state
        self.ctx.execution_log.append(next_state.value)

    def run(self, source: str | Path) -> str:
        """Execute the full pipeline; return the translated target markdown."""
        src = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
        src = _sanitize_input(src)

        self._transition(KernelState.INITIALIZE_RUNTIME)
        self._transition(KernelState.ANALYZE_DOCUMENT)
        analyze_document(src, self.ctx, self.audit)
        assert self.ctx.document_profile is not None
        assert self.ctx.structural_map is not None
        profile: DocumentProfile = self.ctx.document_profile
        smap: StructuralMap = self.ctx.structural_map

        self._transition(KernelState.BUILD_ARTIFACTS)
        try:
            build_glossary(src, profile, self.ctx, self.evidence, self.audit)
        except TRAException as exc:
            self._recover(exc)
        build_entity_table(src, smap, self.ctx, self.evidence, self.audit)

        self._transition(KernelState.EXECUTE_TRANSLATION)
        target = self._execute_translation(src)

        self._transition(KernelState.VERIFY_OUTPUT)
        diagnostics = verify_output(target, src, self.ctx, self.audit)

        self._transition(KernelState.REPAIR_IF_NEEDED)
        target = self._repair_loop(target, src, diagnostics)

        self._transition(KernelState.AUDIT_DIAGNOSTICS)
        self.audit.flush()

        self._transition(KernelState.EMIT_PAYLOAD)
        self._export_artifacts()
        self._export_forensics(target)
        return target

    def _recover(self, exc: TRAException) -> None:
        """EXCEPTION_HANDLER path: apply the spec-mandated recovery procedure
        and record it on the audit trail + L4 ambiguity register.
        """
        report = route_exception(
            exc,
            self.ctx.unresolved_ambiguities,
            canonical_target=getattr(exc, "canonical_target", ""),
        )
        self.audit.append(
            "EXCEPTION_HANDLER",
            report.code,
            [],
            artifact_snapshot={
                "severity": report.severity.value,
                "action": report.action.value,
                "detail": report.detail,
                "source_term": report.source_term,
            },
            flags_raised=[report.severity.value],
        )

    # --- translation (segment-level, rule-based in Phase 2) -----------

    def _execute_translation(self, src: str) -> str:
        # Phase 2: deterministic whole-doc substitution via the glossary +
        # entity + epistemic lexicon. Segment granularity is wired in Phase 3.
        result = translate_segment(src, self.ctx, self.cache, self.evidence, self.audit)
        return result.translation

    def _repair_loop(self, target: str, src: str, diagnostics: list[Diagnostic]) -> str:
        blocking = [d for d in diagnostics if d.severity == Severity.BLOCKING]
        warnings = [d for d in diagnostics if d.severity == Severity.WARNING]
        pending = blocking + warnings
        attempt = 1
        max_retries = self.config.repair_max_retries
        while pending and attempt <= max_retries:
            current, *rest = pending
            try:
                target = repair_segment(
                    target,
                    src,
                    current,
                    self.ctx,
                    self.evidence,
                    self.audit,
                    attempt=attempt,
                    max_retries=max_retries,
                )
            except Unrecoverable:
                # Human-in-the-loop handoff (Phase 6.2); stop looping.
                self.ctx.unresolved_ambiguities.append(
                    f"UNRECOVERABLE: {current.issue}"
                )
                self._recover(Unrecoverable(f"UNRECOVERABLE: {current.issue}"))
                if self.interactive:
                    # Pause for review; adopt the reviewer's resolution.
                    from .hitl import format_unrecoverable, review_decision

                    uncertainty, src_excerpt = format_unrecoverable(
                        self.ctx, current, src
                    )
                    resolution, text = review_decision(
                        uncertainty,
                        src_excerpt,
                        target,
                        glossary_options=[e.source for e in self.ctx.glossary_cache],
                    )
                    target = text
                    self.ctx.unresolved_ambiguities.append(
                        f"HITL[{resolution}]: {current.issue}"
                    )
                break
            # Re-verify; collect any remaining violations.
            rediag = verify_output(target, src, self.ctx, self.audit)
            pending = rediag
            attempt += 1
        return target

    # --- artifact export (Phase 3.3.4) --------------------------------

    def _export_artifacts(self) -> None:
        base = Path(self.config.compilation_dir)
        base.mkdir(parents=True, exist_ok=True)
        glossary_path = base / "glossary.yaml"
        entity_path = base / "entity_table.yaml"
        smap_path = base / "structural_map.json"
        style_path = base / "style_profile.yaml"
        exec_log_path = base / "execution_log.json"
        repair_path = base / "repair_history.jsonl"

        glossary_path.write_text(
            yaml.safe_dump(
                [g.model_dump(mode="json") for g in self.ctx.glossary_cache],
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        entity_path.write_text(
            yaml.safe_dump(
                [e.model_dump(mode="json") for e in self.ctx.entity_table],
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        if self.ctx.structural_map is not None:
            smap_path.write_text(
                self.ctx.structural_map.model_dump_json(indent=2),
                encoding="utf-8",
            )
        style_path.write_text(
            yaml.safe_dump(
                self.ctx.style_profile.model_dump(),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        exec_log_path.write_text(
            json.dumps(
                {
                    "execution_log": self.ctx.execution_log,
                    "unresolved_ambiguities": self.ctx.unresolved_ambiguities,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        with repair_path.open("w", encoding="utf-8") as fh:
            for attempt in self.ctx.repair_history:
                fh.write(attempt.model_dump_json() + "\n")

    def _export_forensics(self, target: str) -> None:
        """L4 forensic artifacts (§6.4): line-by-line evidence trace + the
        explicit ambiguity register. Only emitted at L4_FORENSIC so L1-L3 runs
        stay lean; the data is already captured in execution_log.json otherwise.
        """
        if self.config.conformance_level != ConformanceLevel.L4_FORENSIC:
            return
        from .reporting import line_by_line_trace

        base = Path(self.config.compilation_dir)
        base.mkdir(parents=True, exist_ok=True)
        trace_path = base / "evidence_trace.jsonl"
        with trace_path.open("w", encoding="utf-8") as fh:
            for entry in line_by_line_trace(target, self.evidence):
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        ambiguity_path = base / "ambiguity_register.json"
        ambiguity_path.write_text(
            json.dumps(self.ctx.unresolved_ambiguities, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
