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
    """
    if isinstance(source, Path):
        source = source.read_text(encoding="utf-8")

    if not source.strip():
        raise TRAException("EMPTY_SOURCE: document contains no translatable content")

    try:
        structural_map, _registry = build_structural_map(source)
    except Exception as exc:  # noqa: BLE001 - surface as spec failure
        raise BrokenMarkdown(
            f"MALFORMED_MARKDOWN: unable to parse structure ({exc})"
        ) from exc

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
    mappings = _MODULE.get_glossary_mappings()
    entries: list[GlossaryEntry] = []
    seen: dict[str, str] = {}

    for src, tgt in mappings.items():
        if _MODULE.is_forbidden(src, tgt):
            raise GlossaryConflict(
                f"CONFLICTING_MAPPINGS: {src!r} -> {tgt!r} is a known drift"
            )
        if src in seen and seen[src] != tgt:
            raise GlossaryConflict(
                f"CONFLICTING_MAPPINGS: {src!r} maps to both {seen[src]!r} and {tgt!r}"
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

    forbidden: list[ForbiddenMapping] = _forbidden_from_module()

    ctx.glossary_cache = entries
    audit.append(
        "BUILD_GLOSSARY",
        _hash(source),
        [e.id for e in evidence.all()][-len(entries) :],
        artifact_snapshot={"glossary_size": len(entries)},
    )
    return entries, forbidden


def _forbidden_from_module() -> list[ForbiddenMapping]:
    out: list[ForbiddenMapping] = []
    banned = _MODULE.get_forbidden_targets()
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
        # from the module hint or the classifier.
        hint = _MODULE.entity_type_hint(ent.name)
        if hint is not None:
            ent.type = hint
        ent.mutable = False
        ent.context = "source-document"
        seen.add(ent.name)
        table.append(ent)
        evidence.add(
            EvidenceRecord(
                type=EvidenceType.ENTITY_PRESERVED,
                module="modules.zh_en",
                source_span=ent.name,
                target_span=ent.name,
                rationale=(
                    f"Entity preserved verbatim (mutable=False), type={ent.type.value}"
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
        target = llm_translate(source_segment, ctx)
        basis = "LLM decision"
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
    segment: str, glossary: dict[str, str], entities: list[Entity]
) -> tuple[str, str]:
    """Deterministic canonical translation via glossary + entity + epistemic."""
    out = segment
    # 1. Language-module rule layer FIRST (parataxis->hypotaxis, nominalization,
    #    punctuation). Topic-comment forms like 系统成立 must resolve before the
    #    atomic 成立 -> Confirmed substitution would split them apart.
    out = _MODULE.apply_zh_rules(out)
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
    glossary = {e.source: e.target for e in ctx.glossary_cache}
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
    for src, tgt in glossary.items():
        if src in target:  # untranslated source term leaked
            diagnostics.append(
                Diagnostic(
                    severity=Severity.WARNING,
                    subsystem="terminology",
                    issue=f"Source term not translated: {src!r}",
                    evidence=f"expected canonical target {tgt!r}",
                    action="Apply canonical mapping",
                )
            )

    # Epistemic: forbidden drift targets must not appear.
    for fm in _forbidden_from_module():
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
) -> str:
    """Surgically resolve a single diagnostic without new violations.

    Invariant: must not introduce new BLOCKING; must not violate a higher
    policy. UNRECOVERABLE if fixing would break a higher-priority invariant.
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
        for fm in _forbidden_from_module():
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
    sub = verify_output(repaired, source_segment, ctx, audit)
    new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]
    if new_blocking and attempt >= max_retries:
        raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")

    evidence.add(
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
        [],
        flags_raised=[diagnostic.severity.value],
    )
    return repaired


# --------------------------------------------------------------------------- #
# helpers                                                                    #
# --------------------------------------------------------------------------- #


def _policy_stack(ctx: RuntimeContext) -> list[PolicyPriority]:
    return list(DEFAULT_POLICY_STACK)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
