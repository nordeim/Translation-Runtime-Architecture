"""TRA Kernel — the immutable sequential state machine (Spec §2 / TRA-KERNEL).

BOOTSTRAP -> INITIALIZE_RUNTIME -> ANALYZE_DOCUMENT -> BUILD_ARTIFACTS
(glossary + entity) -> EXECUTE_TRANSLATION -> VERIFY_OUTPUT ->
REPAIR_IF_NEEDED (loop) -> AUDIT_DIAGNOSTICS -> EMIT_PAYLOAD.

State transitions are triggered ONLY by successful completion of ISA
instructions. The Kernel must not skip instructions.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from .cache import TranslationCache
from .config import BootstrapConfig
from .diagnostics import (
    AuditTrail,
    Diagnostic,
    EvidenceRegistry,
)
from .exceptions import ConformanceFailure, TRAException, Unrecoverable
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


# Note: input sanitization (_sanitize_input) was moved to tra.utils.sanitize_input
# (TRA-012) and is now called from analyze_document as the single chokepoint.
# The kernel no longer needs its own copy.


class TRAKernel:
    """Runs the full TRA pipeline on a source document."""

    def __init__(
        self,
        config: BootstrapConfig,
        *,
        interactive: bool = False,
        deterministic: bool = True,
        registry: object | None = None,
    ) -> None:
        """Initialize the kernel.

        Args:
            config: The frozen BootstrapConfig (tvm_bootstrap).
            interactive: If True, pause for HITL review on UNRECOVERABLE.
            deterministic: If True (default), use a content-addressed clock
                for the audit trail so two runs of identical source produce
                byte-identical audit_trace.jsonl (TRA-013). Set to False for
                production runs that want wall-clock timestamps.
            registry: Optional ModuleRegistry (TRA-002). If supplied, the
                kernel selects the language module from the registry based
                on ``config.language_pair``. If None, falls back to the
                default ZHENModule (backward compat).
        """
        self.config = config
        self.interactive = interactive
        self.cache = TranslationCache(
            config.cache_directory, enabled=config.cache_enabled
        )
        self.evidence = EvidenceRegistry()
        # TRA-002: select the language module from the registry.
        module = self._select_module(config.language_pair, registry)
        # Deterministic clock for audit-trail reproducibility (TRA-013).
        self._deterministic = deterministic
        self._source_hash_seed: str | None = None
        if deterministic:
            self.audit = AuditTrail(config.audit_trace, clock=self._deterministic_clock)
        else:
            self.audit = AuditTrail(config.audit_trace)
        self.ctx = RuntimeContext(
            configuration=config.model_dump(),
            style_profile=module.get_style_profile(),
            module=module,
        )
        self.state = KernelState.BOOTSTRAP

    @staticmethod
    def _select_module(language_pair: str, registry: object | None) -> Any:
        """Select the language module for the configured pair (TRA-002).

        If a registry is supplied, filter it by language_pair and return the
        first matching module. Otherwise fall back to ZHENModule.
        """
        if registry is not None:
            # Filter the PASSED registry (don't rebuild from defaults).
            source_lang = (
                language_pair.split("->", 1)[0].strip().lower()
                if "->" in language_pair
                else ""
            )
            for mod in registry.all():  # type: ignore[attr-defined]
                if getattr(mod, "kind", "") != "language":
                    continue
                mod_direction = str(getattr(mod, "metadata", {}).get("direction", ""))
                mod_source = (
                    mod_direction.split("->", 1)[0].strip().lower()
                    if "->" in mod_direction
                    else ""
                )
                if mod_source == source_lang:
                    return mod
            # No match in registry; fall through to ZHENModule.
        return ZHENModule()

    def _deterministic_clock(self) -> datetime:
        """Return a deterministic timestamp derived from the source hash.

        All audit records in a single run share the same timestamp (the run's
        source hash mapped to a valid datetime). This makes the audit trail
        byte-reproducible across runs of identical source (TRA-013).
        """
        from datetime import UTC, datetime, timedelta

        seed = self._source_hash_seed or "0" * 16
        # Map the first 8 hex chars of the seed to a deterministic datetime
        # in 2024 (a fixed epoch keeps the value stable and valid).
        epoch = datetime(2024, 1, 1, tzinfo=UTC)
        offset_seconds = int(seed[:8], 16) % (365 * 24 * 3600)
        return epoch + timedelta(seconds=offset_seconds)

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
        # Sanitization happens inside analyze_document (TRA-012 single chokepoint).

        # Seed the deterministic clock from the source hash BEFORE any audit
        # records are appended, so every record in this run gets the same
        # deterministic timestamp (TRA-013 reproducibility).
        if self._deterministic:
            import hashlib

            self._source_hash_seed = hashlib.sha256(src.encode("utf-8")).hexdigest()

        self._transition(KernelState.INITIALIZE_RUNTIME)
        # TRA-007: transitions fire AFTER the ISA instruction succeeds, not
        # before. If the ISA raises, the state must NOT advance — this is the
        # spec contract (CLAUDE.md:19 / TRA-SPECIFICATION.md §2.1: "transitions
        # are triggered only by successful completion of ISA instructions").
        # TRA-004: route TRA-EXCEPTION types through _recover (EXCEPTION_HANDLER)
        # instead of propagating uncaught to the caller.
        try:
            analyze_document(src, self.ctx, self.audit)
        except TRAException as exc:
            self._recover(exc)
            # analyze_document failed; cannot continue the pipeline. The
            # state stays at INITIALIZE_RUNTIME (TRA-007). Flush the audit
            # trail so the EXCEPTION_HANDLER record is persisted, then return
            # an empty target — the caller's L3 gate will reject it.
            self.audit.flush()
            return ""
        self._transition(KernelState.ANALYZE_DOCUMENT)
        # Runtime invariant: analyze_document must populate the profile and
        # structural map. Use hard raises (not `assert`) so they survive
        # `python -O` (TRA-019).
        if self.ctx.document_profile is None:
            raise TRAException("ANALYZE_DOCUMENT did not populate document_profile")
        if self.ctx.structural_map is None:
            raise TRAException("ANALYZE_DOCUMENT did not populate structural_map")
        profile: DocumentProfile = self.ctx.document_profile
        smap: StructuralMap = self.ctx.structural_map

        try:
            build_glossary(src, profile, self.ctx, self.evidence, self.audit)
        except TRAException as exc:
            self._recover(exc)
        build_entity_table(src, smap, self.ctx, self.evidence, self.audit)
        self._transition(KernelState.BUILD_ARTIFACTS)

        target = self._execute_translation(src)
        self._transition(KernelState.EXECUTE_TRANSLATION)

        diagnostics = verify_output(target, src, self.ctx, self.audit)
        self._transition(KernelState.VERIFY_OUTPUT)

        target = self._repair_loop(target, src, diagnostics)
        self._transition(KernelState.REPAIR_IF_NEEDED)

        # L3+ conformance gate (Spec §8 / TRA-CONFORMANCE-GUIDE.md:51):
        # if BLOCKING diagnostics remain after the repair loop, the output
        # is NOT conformant. The standalone `validate` command enforces this
        # out-of-band; the kernel enforces it in-band so `translate` cannot
        # silently publish a non-conformant output. L1/L2 do not require
        # zero-BLOCKING (they are lower strictness dials).
        if self.config.conformance_level in (
            ConformanceLevel.L3_STRICT,
            ConformanceLevel.L4_FORENSIC,
        ):
            final_diags = verify_output(target, src, self.ctx, self.audit)
            final_blocking = [d for d in final_diags if d.severity == Severity.BLOCKING]
            if final_blocking:
                self.audit.flush()
                raise ConformanceFailure(
                    f"CONFORMANCE_FAILURE: {len(final_blocking)} BLOCKING "
                    f"diagnostic(s) remain after repair loop — output is not "
                    f"L3-conformant",
                    blocking_count=len(final_blocking),
                )

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
