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
from collections.abc import Callable
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
    StructuralNode,
)
from .modules.registry import ModuleRegistry
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


# TRA-078: redact potential secrets from exception repr before storing in
# the audit trail. Matches common LLM-client secret patterns: API keys
# (sk-...), Bearer tokens, Authorization headers, api_key parameters.
_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9._-]+|"
    r"Authorization:\s*[^\s,;]+|api[_-]?key['\"]?\s*[:=]\s*['\"]?[^\s'\"]+)",
    re.IGNORECASE,
)


def _sanitize_exc_repr(exc: BaseException) -> str:
    """Return a sanitized repr of `exc` with secrets redacted (TRA-078).

    Replaces API keys, Bearer tokens, and Authorization headers with
    '[REDACTED]' so the audit trail never persists LLM client secrets.
    """
    raw = repr(exc)
    return _SECRET_RE.sub("[REDACTED]", raw)


class TRAKernel:
    """Runs the full TRA pipeline on a source document."""

    def __init__(
        self,
        config: BootstrapConfig,
        *,
        interactive: bool = False,
        deterministic: bool = True,
        registry: ModuleRegistry | None = None,
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
    def _select_module(language_pair: str, registry: ModuleRegistry | None) -> Any:
        """Select the language module for the configured pair (TRA-002).

        If a registry is supplied, prefer a FULL direction match (e.g.
        'fr -> en' matches a module with direction 'FR -> EN'). If no full
        match exists, fall back to a source-language-only match (e.g. 'fr'
        matches any module whose source is 'fr'). If neither matches, fall
        through to ZHENModule.

        TRA-F4-007 (round 4): previously this matched by source language
        only, so two modules with `fr -> en` and `fr -> de` would silently
        dispatch the first one for `--lang fr-de`, masking the user's intent.
        """
        if registry is not None:
            # Normalize the requested direction for comparison.
            req_direction = language_pair.strip().lower()
            req_source = (
                req_direction.split("->", 1)[0].strip() if "->" in req_direction else ""
            )
            # Pass 1: prefer a full-direction match.
            source_only_match: Any = None
            for mod in registry.all():
                if getattr(mod, "kind", "") != "language":
                    continue
                mod_direction = str(getattr(mod, "metadata", {}).get("direction", ""))
                mod_direction_norm = mod_direction.strip().lower()
                if mod_direction_norm and mod_direction_norm == req_direction:
                    return mod
                # Track the first source-only match as a fallback.
                if source_only_match is None and req_source:
                    mod_source = (
                        mod_direction_norm.split("->", 1)[0].strip()
                        if "->" in mod_direction_norm
                        else ""
                    )
                    if mod_source == req_source:
                        source_only_match = mod
            # Pass 2: no full match — use the source-only fallback if any.
            if source_only_match is not None:
                return source_only_match
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
        # TRA-049: same-state transitions (idx == current) are illegal.
        # The spec §2.1 implies forward-only progression; allowing same-state
        # transitions was a silent no-op that masked bugs. Mutation testing
        # confirmed changing `<` to `<=` left all tests green — this strict
        # forward enforcement closes that gap.
        if idx <= _KERNEL_ORDER.index(self.state):
            raise TRAException(
                f"Illegal backward or same-state transition: "
                f"{self.state} -> {next_state}"
            )
        self.state = next_state
        self.ctx.execution_log.append(next_state.value)

    def run(
        self,
        source: str | Path,
        *,
        llm_translate: Callable[[str, RuntimeContext], str] | None = None,
    ) -> str:
        """Execute the full pipeline; return the translated target markdown.

        TRA-D5-002 (round 5): the optional `llm_translate` callback is the
        dependency-injection seam for the LLM. Previously the only way to
        supply an LLM was to monkeypatch tra.kernel.translate_segment at
        module level (fragile — any rename breaks tests silently). Now
        callers pass the callback here; _execute_translation forwards it
        to translate_segment.
        """
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
            # trail so the EXCEPTION_HANDLER record is persisted.
            self.audit.flush()
            # TRA-036: at L3_STRICT/L4_FORENSIC, an analyze failure is a
            # conformance failure — the empty output is not L3-conformant.
            # The early `return ""` (TRA-004 fix) bypassed the L3 gate at
            # kernel.py:248-261, so a malformed source produced exit 0 with
            # a 0-byte output at L3_STRICT — a silent conformance failure.
            # L1/L2 do not require zero-BLOCKING, so they keep the empty
            # return (lower strictness dials).
            if self.config.conformance_level in (
                ConformanceLevel.L3_STRICT,
                ConformanceLevel.L4_FORENSIC,
            ):
                raise ConformanceFailure(
                    f"BROKEN_MARKDOWN: analyze_document failed ({exc.code}) — "
                    f"output is not L3-conformant",
                    blocking_count=1,
                ) from exc
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
        # TRA-039: wrap build_entity_table in the same try/except pattern as
        # build_glossary. Spec §3 BUILD_ENTITY_TABLE Failure Condition is
        # ENTITY_AMBIGUITY; without this wrapper, an EntityAmbiguity raise
        # would crash the kernel with no EXCEPTION_HANDLER audit record.
        try:
            build_entity_table(src, smap, self.ctx, self.evidence, self.audit)
        except TRAException as exc:
            self._recover(exc)
        self._transition(KernelState.BUILD_ARTIFACTS)

        target = self._execute_translation(src, llm_translate=llm_translate)
        self._transition(KernelState.EXECUTE_TRANSLATION)

        diagnostics = verify_output(target, src, self.ctx, self.audit)
        self._transition(KernelState.VERIFY_OUTPUT)

        target = self._repair_loop(target, src, diagnostics)
        self._transition(KernelState.REPAIR_IF_NEEDED)

        # TRA-037: rewrite internal `[text](#slug)` links BEFORE the L3 gate,
        # so the gate verifies the post-rewrite target (the one actually
        # emitted). Previously _rewrite_anchors ran AFTER the gate, so the
        # audit trail's VERIFY_OUTPUT hash was computed on the pre-rewrite
        # target while the emitted target was post-rewrite — breaking L4
        # hash-chain integrity. Moving this BEFORE the gate also surfaces
        # BROKEN_LINK entries (appended to unresolved_ambiguities by
        # _rewrite_anchors) to the gate's check below.
        # (TRA-008: rewrite links to point at translated heading slugs, S-06.)
        target = self._rewrite_anchors(target)

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
            # TRA-037: also reject if _rewrite_anchors appended BROKEN_LINK
            # entries to unresolved_ambiguities — a broken internal link is
            # a structural conformance failure at L3+.
            broken_links = [
                a for a in self.ctx.unresolved_ambiguities if "BROKEN_LINK" in a
            ]
            if final_blocking or broken_links:
                self.audit.flush()
                if final_blocking:
                    raise ConformanceFailure(
                        f"CONFORMANCE_FAILURE: {len(final_blocking)} BLOCKING "
                        f"diagnostic(s) remain after repair loop — output is not "
                        f"L3-conformant",
                        blocking_count=len(final_blocking),
                    )
                raise ConformanceFailure(
                    f"CONFORMANCE_FAILURE: {len(broken_links)} BROKEN_LINK "
                    f"entry/entries in unresolved_ambiguities — output is not "
                    f"L3-conformant (internal link target missing)",
                    blocking_count=len(broken_links),
                )

        self._transition(KernelState.AUDIT_DIAGNOSTICS)
        self.audit.flush()

        self._transition(KernelState.EMIT_PAYLOAD)
        self._export_artifacts()
        self._export_forensics(target)
        return target

    def _rewrite_anchors(self, target: str) -> str:
        """Rewrite internal links to point at translated heading slugs (TRA-008).

        Two-pass approach for the whole-doc translation model (TRA-001 not yet
        implemented):
        1. Normalize any translated link targets that have spaces (the whole-doc
           translator mangles `#slug` into `#Translated Text With Spaces`).
           Slugify them so they're valid URL fragments.
        2. Bind translated heading slugs on the AnchorRegistry and call
           rewrite_links to repoint links at the canonical translated slugs.
        """
        if self.ctx.anchor_registry is None or self.ctx.structural_map is None:
            return target
        from .anchor import generate_github_slug, rewrite_links

        registry = self.ctx.anchor_registry

        # Pass 1: normalize translated link targets with spaces.
        # The whole-doc translator turns `#系统成立` into `#The system is Confirmed`
        # (spaces, uppercase). Slugify the target so it's a valid URL fragment.
        _LINK_WITH_SPACES_RE = re.compile(r"\]\(#([^)]+)\)")

        def _slugify_link(m: re.Match[str]) -> str:
            slug_text = m.group(1)
            if " " in slug_text or slug_text != slug_text.lower():
                return f"](#{generate_github_slug(slug_text)})"
            return m.group(0)

        target = _LINK_WITH_SPACES_RE.sub(_slugify_link, target)

        # Pass 2: bind translated heading slugs and call rewrite_links.
        source_headings: list[str] = []

        def _collect_headings(nodes: list[StructuralNode]) -> None:
            for node in nodes:
                if node.kind.value == "heading" and node.text:
                    source_headings.append(node.text)
                _collect_headings(node.children)

        _collect_headings(self.ctx.structural_map.nodes)
        if source_headings:
            target_heading_re = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
            target_headings = [
                m.group(2).strip() for m in target_heading_re.finditer(target)
            ]
            for src_heading, tgt_heading in zip(
                source_headings, target_headings, strict=False
            ):
                src_slug = generate_github_slug(src_heading)
                placeholder = registry.map_original_slug_to_placeholder.get(src_slug)
                if placeholder is not None:
                    translated_slug = registry.resolve_slug(tgt_heading)
                    registry.bind(placeholder, translated_slug)
        rewritten, broken = rewrite_links(target, registry)
        for slug in broken:
            self.ctx.unresolved_ambiguities.append(f"BROKEN_LINK: #{slug}")
        return rewritten

    def _recover(self, exc: TRAException) -> None:
        """EXCEPTION_HANDLER path: apply the spec-mandated recovery procedure
        and record it on the audit trail + L4 ambiguity register.

        TRA-078: the exception repr is sanitized to redact potential
        secrets (API keys, Bearer tokens) before storing in the audit
        trail (OWASP A09).
        """
        report = route_exception(
            exc,
            self.ctx.unresolved_ambiguities,
            canonical_target=getattr(exc, "canonical_target", ""),
        )
        # TRA-078: sanitize both the exception repr and the report detail
        # (which may contain str(exc)) to redact potential secrets.
        safe_reason = _sanitize_exc_repr(exc)
        safe_detail = _SECRET_RE.sub("[REDACTED]", report.detail)
        self.audit.append(
            "EXCEPTION_HANDLER",
            report.code,
            [],
            artifact_snapshot={
                "severity": report.severity.value,
                "action": report.action.value,
                "detail": safe_detail,
                "source_term": report.source_term,
                "reason": safe_reason,
            },
            flags_raised=[report.severity.value],
        )

    # --- translation (segment-level, rule-based in Phase 2) -----------

    def _execute_translation(
        self,
        src: str,
        *,
        llm_translate: Callable[[str, RuntimeContext], str] | None = None,
    ) -> str:
        """Execute TRANSLATE_SEGMENT on the source.

        TRA-D5-002 (round 5): the optional llm_translate callback is
        forwarded to translate_segment. Previously the only way to supply
        an LLM was module-level monkeypatching.

        TRA-001 (partial): code blocks are no-translate zones. We extract
        them before translation, translate the rest, then restore them.
        This protects inline code and fenced code blocks from glossary
        substitution. Full segment-level translation (per leaf node) is
        deferred — the current approach is a placeholder-based protection
        that addresses the S-03 test case.
        """
        # Extract code blocks and protect them with placeholders.
        placeholders: dict[str, str] = {}
        protected = src

        # Protect fenced code blocks (```...```).
        _FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)

        def _stash_fence(m: re.Match[str]) -> str:
            key = f"__CODE_BLOCK_{len(placeholders)}__"
            placeholders[key] = m.group(0)
            return key

        protected = _FENCE_RE.sub(_stash_fence, protected)

        # Protect inline code (`...`).
        _INLINE_RE = re.compile(r"`[^`\n]+`")

        def _stash_inline(m: re.Match[str]) -> str:
            key = f"__INLINE_CODE_{len(placeholders)}__"
            placeholders[key] = m.group(0)
            return key

        protected = _INLINE_RE.sub(_stash_inline, protected)

        # Translate the protected source (code blocks are now placeholders).
        # TRA-D5-002 (round 5): forward the llm_translate callback so callers
        # can inject an LLM via dependency injection (no module-level patching).
        result = translate_segment(
            protected,
            self.ctx,
            self.cache,
            self.evidence,
            self.audit,
            llm_translate=llm_translate,
        )
        translated = result.translation

        # Restore code blocks.
        for key, original in placeholders.items():
            translated = translated.replace(key, original)

        return translated

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
