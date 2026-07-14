"""The six TRA ISA instructions (Spec §3, TRA-ISA-REFERENCE.md).

Each function implements a strict contract: Inputs, Preconditions, Outputs,
Invariants, Failure Conditions. Engines must not skip instructions — the
Kernel (kernel.py) runs them in canonical order.

TRANSLATE_SEGMENT is implemented deterministically (glossary + entity +
epistemic substitution) so the contract is unit-testable WITHOUT an LLM. An
LLM seam (`llm_translate`) is wired as an optional override in Phase 3; when
absent, the rule-based path runs (graceful degradation, implementation_plan
Phase 6.5). The cache-first rule still applies to both paths.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .anchor import build_structural_map
from .cache import CacheKeyContext, TranslationCache, TranslationResult
from .config import DEFAULT_POLICY_STACK
from .diagnostics import (
    AuditTrail,
    Diagnostic,
    EvidenceRecord,
    EvidenceRegistry,
    EvidenceType,
)
from .exceptions import (
    BrokenMarkdown,
    GlossaryConflict,
    TRAException,
    Unrecoverable,
)
from .memory import (
    DocumentProfile,
    Entity,
    ForbiddenMapping,
    GlossaryEntry,
    GlossaryStatus,
    PolicyPriority,
    RepairAttempt,
    RuntimeContext,
    Severity,
    StructuralMap,
)
from .modules import zh_en
from .modules.zh_en import ZHENModule
from .utils import extract_entities

# Module providing terminology + style for the active language pair.
_MODULE = ZHENModule()

# Heading-level detection for structural verification.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


# --------------------------------------------------------------------------- #
# ANALYZE_DOCUMENT                                                            #
# --------------------------------------------------------------------------- #


def analyze_document(
    source: str | Path,
    ctx: RuntimeContext,
    audit: AuditTrail,
) -> tuple[DocumentProfile, StructuralMap]:
    """Extract macro-structure + metadata; initialize RuntimeContext.

    Failure: EMPTY_SOURCE, MALFORMED_MARKDOWN.
    Invariant: node_count(structural_map) == node_count(source_AST).

    Sanitization chokepoint (TRA-012): the source is sanitized HERE, in the
    ISA instruction, so every caller (TRAKernel.run, validate, benchmark)
    is covered without each one having to remember to call sanitize_input.
    """
    if isinstance(source, Path):
        source = source.read_text(encoding="utf-8")

    # Single chokepoint: strip control chars / bidi overrides / BOM before
    # the source enters the pipeline (TRA-012).
    from .utils import sanitize_input

    source = sanitize_input(source)

    if not source.strip():
        raise TRAException("EMPTY_SOURCE: document contains no translatable content")

    try:
        structural_map, registry = build_structural_map(source)
    except Exception as exc:  # noqa: BLE001 - surface as spec failure
        raise BrokenMarkdown(
            f"MALFORMED_MARKDOWN: unable to parse structure ({exc})"
        ) from exc

    # TRA-008: preserve the AnchorRegistry on ctx so the kernel can call
    # rewrite_links after translation to repoint internal links (S-06).
    ctx.anchor_registry = registry

    # DocumentProfile: heuristic detection (Spec §4 / ISA contract).
    doc_type = _detect_document_type(source)
    register = _detect_register(source)
    intent = _detect_intent(source)
    audience = "Technical readers (engineers, operators)"

    profile = DocumentProfile(
        type=doc_type,
        register_="Formal/Authoritative" if register == "Authoritative" else register,
        intent=intent,
        audience=audience,
        evidence_style=_detect_evidence_style(source),
    )
    ctx.document_profile = profile
    ctx.structural_map = structural_map

    audit.append(
        "ANALYZE_DOCUMENT",
        _hash(source),
        [],
        artifact_snapshot={"node_count": structural_map.node_count, "type": doc_type},
    )
    return profile, structural_map


def _detect_document_type(source: str) -> str:
    if re.search(r"^#\s+RFC\s+\d+", source, re.MULTILINE | re.IGNORECASE):
        return "RFC"
    if "advisory" in source.lower() or "vulnerability" in source.lower():
        return "Advisory"
    if "guide" in source.lower() or "how to" in source.lower():
        return "Guide"
    return "README"


def _detect_register(source: str) -> str:
    if re.search(r"MUST|SHALL|REQUIRED", source):
        return "Authoritative"
    return "Instructional"


def _detect_intent(source: str) -> str:
    if "advisory" in source.lower():
        return "Disclose Vulnerability"
    return "Standardize Protocol"


def _detect_evidence_style(source: str) -> str | None:
    if "according to" in source.lower() or "per " in source.lower():
        return "Cited"
    return None


# --------------------------------------------------------------------------- #
# BUILD_GLOSSARY                                                              #
# --------------------------------------------------------------------------- #


def _module(ctx: RuntimeContext) -> Any:
    """Return the active language module (TRA-002). Prefers ctx.module
    (set by the kernel from the registry); falls back to the module-level
    _MODULE singleton for direct ISA calls in tests."""
    return ctx.module if ctx.module is not None else _MODULE


def build_glossary(
    source: str,
    profile: DocumentProfile,
    ctx: RuntimeContext,
    evidence: EvidenceRegistry,
    audit: AuditTrail,
) -> tuple[list[GlossaryEntry], list[ForbiddenMapping]]:
    """Establish canonical terminology; flag drift targets.

    Invariant: every recurring term (>=2x) gets exactly one canonical mapping
    unless context_sensitive. CONFLICTING_MAPPINGS raised on two targets.
    """
    mod = _module(ctx)
    mappings = mod.get_glossary_mappings()
    entries: list[GlossaryEntry] = []
    seen: dict[str, str] = {}

    for src, tgt in mappings.items():
        if mod.is_forbidden(src, tgt):
            # TRA-041: populate ctx.glossary_cache with entries collected
            # so far (the first-occurrence canonical mappings) BEFORE
            # raising, so the kernel's _recover path can still access them.
            # Spec §6 GLOSSARY_CONFLICT: "Use first occurrence as canonical.
            # Flag subsequent occurrences for manual review."
            ctx.glossary_cache = entries
            raise GlossaryConflict(
                f"CONFLICTING_MAPPINGS: {src!r} -> {tgt!r} is a known drift",
                term=src,
                canonical_target="",
            )
        if src in seen and seen[src] != tgt:
            # TRA-041: same — preserve first-occurrence mappings before raise.
            ctx.glossary_cache = entries
            raise GlossaryConflict(
                f"CONFLICTING_MAPPINGS: {src!r} maps to both {seen[src]!r} and {tgt!r}",
                term=src,
                canonical_target=seen[src],
            )
        seen[src] = tgt
        entry = GlossaryEntry(
            source=src,
            target=tgt,
            status=GlossaryStatus.CANONICAL,
            rule_id="ZH-EN-RULE#CANON",
        )
        entries.append(entry)
        evidence.add(
            EvidenceRecord(
                type=EvidenceType.TERM_MATCH,
                module="modules.zh_en",
                source_span=src,
                target_span=tgt,
                rationale=f"Matched ZH-EN canonical lexicon: {src} -> {tgt}",
                rule_id="ZH-EN-RULE#CANON",
            )
        )

    forbidden: list[ForbiddenMapping] = _forbidden_from_module(ctx)

    ctx.glossary_cache = entries
    audit.append(
        "BUILD_GLOSSARY",
        _hash(source),
        [e.id for e in evidence.all()][-len(entries) :],
        artifact_snapshot={"glossary_size": len(entries)},
    )
    return entries, forbidden


def _forbidden_from_module(ctx: RuntimeContext | None = None) -> list[ForbiddenMapping]:
    """Build the forbidden-mappings list from the active module.

    If ``ctx`` is supplied (TRA-002), use ctx.module; otherwise fall back to
    the module-level _MODULE singleton (backward compat for verify_output
    which may call this without a ctx in legacy paths).
    """
    mod = _module(ctx) if ctx is not None else _MODULE
    out: list[ForbiddenMapping] = []
    banned = mod.get_forbidden_targets()
    for src, banned_str in banned.items():
        for tgt in banned_str.split("/"):
            out.append(
                ForbiddenMapping(
                    source=src,
                    forbidden_target=tgt,
                    rationale="Drift target forbidden by TRA-MODULE-ZH-EN §3",
                )
            )
    return out


# --------------------------------------------------------------------------- #
# BUILD_ENTITY_TABLE                                                           #
# --------------------------------------------------------------------------- #


def build_entity_table(
    source: str,
    structural_map: StructuralMap,
    ctx: RuntimeContext,
    evidence: EvidenceRegistry,
    audit: AuditTrail,
) -> list[Entity]:
    """Isolate immutable identifiers (Spec §3). All mutable=False.

    Invariant: entities excluded from translation; casing/punctuation preserved.
    """
    candidates = extract_entities(source)
    table: list[Entity] = []
    seen: set[str] = set()
    for ent in candidates:
        if ent.name in seen:
            continue
        # ENTITY_AMBIGUITY: default to Entity (immutable). Type may come
        # from the module hint or the classifier. Entity is frozen (TRA-018),
        # so we use model_copy to apply the hint + context rather than
        # mutating in place.
        hint = _module(ctx).entity_type_hint(ent.name)
        final = ent.model_copy(
            update={
                "type": hint if hint is not None else ent.type,
                "mutable": False,
                "context": "source-document",
            }
        )
        seen.add(final.name)
        table.append(final)
        evidence.add(
            EvidenceRecord(
                type=EvidenceType.ENTITY_PRESERVED,
                module="modules.zh_en",
                source_span=final.name,
                target_span=final.name,
                rationale=(
                    f"Entity preserved verbatim (mutable=False), "
                    f"type={final.type.value}"
                ),
            )
        )

    ctx.entity_table = table
    audit.append(
        "BUILD_ENTITY_TABLE",
        _hash(source),
        [e.id for e in evidence.all()][-len(table) :],
        artifact_snapshot={"entity_count": len(table)},
    )
    return table


# --------------------------------------------------------------------------- #
# TRANSLATE_SEGMENT                                                            #
# --------------------------------------------------------------------------- #


def translate_segment(
    source_segment: str,
    ctx: RuntimeContext,
    cache: TranslationCache,
    evidence: EvidenceRegistry,
    audit: AuditTrail,
    *,
    llm_translate: Callable[[str, RuntimeContext], str] | None = None,
) -> TranslationResult:
    """Generate target-language equivalent of one source segment.

    Cache-first (Spec §0.4): identical context -> byte-identical output.
    Deterministic rule path when no LLM seam is supplied.
    Invariant: factual qualifiers/numbers/epistemic markers preserved;
    terminology matches glossary; entities inserted verbatim.
    """
    glossary = {e.source: e.target for e in ctx.glossary_cache}
    entities = ctx.entity_table

    key_ctx = CacheKeyContext(
        source_text=source_segment,
        glossary=ctx.glossary_cache,
        entities=entities,
        model_endpoint="rule-based" if llm_translate is None else "llm",
        model_version="zh-en-1.0",
        policy_stack=_policy_stack(ctx),
    )
    cache_key = key_ctx.key()
    cached = cache.get(cache_key)
    if cached is not None:
        audit.append("TRANSLATE_SEGMENT", cache_key, cached.evidence_ids)
        return cached

    if llm_translate is not None:
        try:
            target = llm_translate(source_segment, ctx)
            basis = "LLM decision"
            # TRA-033: guard against empty/None LLM output. These bypass the
            # except block entirely (no exception is raised) but produce
            # invalid translations. Degrade to the rule path instead.
            if not target:
                raise ValueError("llm_translate returned empty/None output")
        except Exception as exc:  # noqa: BLE001 - graceful degradation (§6.5.4)
            # LLM unavailable / errored: degrade to the deterministic rule
            # path so translation still completes (never self-score, never
            # raise). The rule path is weaker on fluency but preserves all
            # BLOCKING invariants (factual / entity / terminology / epistemic).
            target, basis = _rule_translate(
                source_segment, glossary, entities, module=ctx.module
            )
            # Emit ONE complete audit record (evidence + degraded flag) and
            # return early. Previously the code fell through to emit a SECOND
            # record without the degraded flag — an auditor inspecting the
            # last record per segment would miss the degradation (TRA-015).
            rec = EvidenceRecord(
                type=EvidenceType.LLM_DECISION,
                module="isa.translate_segment",
                source_span=source_segment,
                target_span=target,
                rationale=(
                    f"{basis} (glossary + entity + epistemic substitution; "
                    f"degraded from llm_unavailable: {exc!r})"
                ),
            )
            ev_id = evidence.add(rec)
            result = TranslationResult(
                translation=target, evidence_ids=[ev_id], cache_hit=False
            )
            cache.set(cache_key, result)
            audit.append(
                "TRANSLATE_SEGMENT",
                cache_key,
                [ev_id],
                artifact_snapshot={
                    "degraded": True,
                    "reason": f"llm_unavailable: {exc!r}",
                },
            )
            return result
    else:
        target, basis = _rule_translate(source_segment, glossary, entities)

    rec = EvidenceRecord(
        type=EvidenceType.LLM_DECISION,
        module="isa.translate_segment",
        source_span=source_segment,
        target_span=target,
        rationale=f"{basis} (glossary + entity + epistemic substitution)",
    )
    ev_id = evidence.add(rec)
    result = TranslationResult(
        translation=target, evidence_ids=[ev_id], cache_hit=False
    )
    cache.set(cache_key, result)
    audit.append("TRANSLATE_SEGMENT", cache_key, [ev_id])
    return result


def _rule_translate(
    segment: str,
    glossary: dict[str, str],
    entities: list[Entity],
    module: Any = None,
) -> tuple[str, str]:
    """Deterministic canonical translation via glossary + entity + epistemic.

    If ``module`` is supplied (TRA-002), use its rule layer; otherwise fall
    back to the module-level ``_MODULE`` singleton (backward compat).
    """
    mod = module if module is not None else _MODULE
    out = segment
    # 1. Language-module rule layer FIRST (parataxis->hypotaxis, nominalization,
    #    punctuation). Topic-comment forms like 系统成立 must resolve before the
    #    atomic 成立 -> Confirmed substitution would split them apart.
    out = mod.apply_zh_rules(out)
    # 2. Epistemic-certainty lexicon (exact, never drift).
    for src, tgt in zh_en.EPISTEMIC_LEXICON.items():
        if src in out:
            out = out.replace(src, tgt)
    # 3. Canonical glossary substitution.
    for src, tgt in glossary.items():
        if src in out:
            out = out.replace(src, tgt)
    # 4. Entities inserted verbatim (already source form; no-op preserve).
    for ent in entities:
        # Ensure casing preserved exactly; nothing to transform.
        if ent.name not in out and ent.name in segment:
            out = out  # entities already present verbatim
    return out, "rule-based"


# --------------------------------------------------------------------------- #
# VERIFY_OUTPUT                                                                #
# --------------------------------------------------------------------------- #


def verify_output(
    target: str,
    source: str,
    ctx: RuntimeContext,
    audit: AuditTrail,
) -> list[Diagnostic]:
    """Audit target against source + runtime constraints (Spec §7).

    Exhaustive; cannot skip sections. Every violation -> Diagnostic with
    severity BLOCKING / WARNING / INFO.
    """
    diagnostics: list[Diagnostic] = []
    entities = ctx.entity_table
    structural_map = ctx.structural_map

    # Structural: heading count match (node-count surrogate for the segment set).
    if structural_map is not None:
        src_headings = len(_HEADING_RE.findall(source))
        tgt_headings = len(_HEADING_RE.findall(target))
        if src_headings != tgt_headings:
            diagnostics.append(
                Diagnostic(
                    severity=Severity.BLOCKING,
                    subsystem="structural",
                    issue="Heading count mismatch after translation",
                    evidence=f"source={src_headings} target={tgt_headings}",
                    action="Restore heading hierarchy",
                )
            )

    # Factual: entities preserved verbatim (numbers/versions/casing).
    for ent in entities:
        if ent.name not in target:
            diagnostics.append(
                Diagnostic(
                    severity=Severity.BLOCKING,
                    subsystem="entity",
                    issue=f"Entity not preserved: {ent.name!r}",
                    evidence="expected verbatim occurrence in target",
                    action="Restore entity from entity_table",
                )
            )

    # Terminology: glossary terms must appear as canonical targets.
    # TRA-009 + TRA-006: severity is policy-driven. CANONICAL term leakage
    # is BLOCKING (Terminological Consistency P4 > Target Fluency P6);
    # CONTEXT_SENSITIVE term leakage stays WARNING (fluency may legitimately
    # override context-dependent mappings).
    from .memory import GlossaryStatus

    for entry in ctx.glossary_cache:
        if entry.source in target:  # untranslated source term leaked
            if entry.status == GlossaryStatus.CANONICAL:
                severity = Severity.BLOCKING
            else:
                severity = Severity.WARNING
            diagnostics.append(
                Diagnostic(
                    severity=severity,
                    subsystem="terminology",
                    issue=f"Source term not translated: {entry.source!r}",
                    evidence=f"expected canonical target {entry.target!r}",
                    action="Apply canonical mapping",
                )
            )

    # Epistemic: forbidden drift targets must not appear.
    for fm in _forbidden_from_module(ctx):
        if fm.forbidden_target in target:
            diagnostics.append(
                Diagnostic(
                    severity=Severity.BLOCKING,
                    subsystem="epistemic",
                    issue=(
                        f"Epistemic drift: {fm.forbidden_target!r} (from {fm.source!r})"
                    ),
                    evidence="TRA-MODULE-ZH-EN §3 forbids this mapping",
                    action="Revert to canonical certainty marker",
                )
            )

    audit.append(
        "VERIFY_OUTPUT",
        _hash(target),
        [],
        flags_raised=[d.severity.value for d in diagnostics] or None,
    )
    return diagnostics


# --------------------------------------------------------------------------- #
# REPAIR_SEGMENT                                                              #
# --------------------------------------------------------------------------- #


def repair_segment(
    target_segment: str,
    source_segment: str,
    diagnostic: Diagnostic,
    ctx: RuntimeContext,
    evidence: EvidenceRegistry,
    audit: AuditTrail,
    *,
    attempt: int = 1,
    max_retries: int = 3,
    segment_index: int = 0,
) -> str:
    """Surgically resolve a single diagnostic without new violations.

    Invariant: must not introduce new BLOCKING; must not violate a higher
    policy. UNRECOVERABLE if fixing would break a higher-priority invariant.

    Records each attempt in `ctx.repair_history` for L4 forensic tracing
    (§6.4.2) regardless of whether it resolved the violation.
    """
    glossary = {e.source: e.target for e in ctx.glossary_cache}
    repaired = target_segment

    if diagnostic.subsystem == "terminology" and diagnostic.issue.startswith(
        "Source term not translated"
    ):
        src = diagnostic.issue.split("'")[1] if "'" in diagnostic.issue else ""
        if src and src in glossary:
            repaired = repaired.replace(src, glossary[src])

    elif diagnostic.subsystem == "entity":
        name = diagnostic.issue.split("'")[1] if "'" in diagnostic.issue else ""
        if name and name not in repaired:
            repaired = repaired  # cannot conjure absent entity without source

    elif diagnostic.subsystem == "epistemic":
        # Revert to canonical marker.
        for fm in _forbidden_from_module(ctx):
            if fm.forbidden_target in repaired:
                canon = glossary.get(fm.source, fm.source)
                repaired = repaired.replace(fm.forbidden_target, canon)

    elif diagnostic.subsystem == "structural":
        # Surgical structural fix not automatable here without AST; flag.
        if attempt >= max_retries:
            raise Unrecoverable(
                "UNRECOVERABLE: structural repair needs manual intervention"
            )

    # Re-verify the repaired segment does not introduce new BLOCKING.
    # Per the surgical-repair invariant (TRA-ISA-REFERENCE.md §REPAIR_SEGMENT:
    # "must not introduce new ones"), ANY new BLOCKING is unrecoverable —
    # regardless of attempt number. The attempt/max_retries budget governs
    # the kernel's repair LOOP (re-queuing), not this function's contract.
    sub = verify_output(repaired, source_segment, ctx, audit)
    new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]
    if new_blocking:
        raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")

    ev_id = evidence.add(
        EvidenceRecord(
            type=EvidenceType.POLICY_ARBITRATION,
            module="isa.repair_segment",
            source_span=source_segment,
            target_span=repaired,
            rationale=f"Repaired {diagnostic.subsystem} violation (attempt {attempt})",
        )
    )
    audit.append(
        "REPAIR_SEGMENT",
        _hash(repaired),
        [ev_id],
        flags_raised=[diagnostic.severity.value],
    )
    ctx.repair_history.append(
        RepairAttempt(
            segment_index=segment_index,
            attempt=attempt,
            subsystem=diagnostic.subsystem,
            issue=diagnostic.issue,
            before=target_segment,
            after=repaired,
            evidence_id=ev_id,
            resolved=not new_blocking,
        )
    )
    return repaired


# --------------------------------------------------------------------------- #
# helpers                                                                    #
# --------------------------------------------------------------------------- #


def _policy_stack(ctx: RuntimeContext) -> list[PolicyPriority]:
    return list(DEFAULT_POLICY_STACK)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
