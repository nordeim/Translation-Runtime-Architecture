"""TRA Kernel — the immutable sequential state machine (Spec §2 / TRA-KERNEL).

BOOTSTRAP -> INITIALIZE_RUNTIME -> ANALYZE_DOCUMENT -> BUILD_ARTIFACTS
(glossary + entity) -> EXECUTE_TRANSLATION -> VERIFY_OUTPUT ->
REPAIR_IF_NEEDED (loop) -> AUDIT_DIAGNOSTICS -> EMIT_PAYLOAD.

State transitions are triggered ONLY by successful completion of ISA
instructions. The Kernel must not skip instructions.
"""

from __future__ import annotations

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
from .memory import DocumentProfile, RuntimeContext, Severity, StructuralMap
from .modules.zh_en import ZHENModule


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


class TRAKernel:
    """Runs the full TRA pipeline on a source document."""

    def __init__(self, config: BootstrapConfig) -> None:
        self.config = config
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

        self._transition(KernelState.INITIALIZE_RUNTIME)
        self._transition(KernelState.ANALYZE_DOCUMENT)
        analyze_document(src, self.ctx, self.audit)
        assert self.ctx.document_profile is not None
        assert self.ctx.structural_map is not None
        profile: DocumentProfile = self.ctx.document_profile
        smap: StructuralMap = self.ctx.structural_map

        self._transition(KernelState.BUILD_ARTIFACTS)
        build_glossary(src, profile, self.ctx, self.evidence, self.audit)
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
        return target

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
