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
from .modules.base import LanguageModuleProtocol
from .modules.zh_en import ZHENModule
from .policy import PolicyResolver
from .utils import extract_entities

# Module providing terminology + style for the active language pair.
_MODULE = ZHENModule()

# Policy resolver for severity arbitration (TRA-006). The 6-priority stack
# is non-negotiable; the resolver arbitrates which priority wins when two
# conflict. Used by verify_output to determine terminology diagnostic
# severity: if Terminological Consistency (P4) wins over Target Fluency
# (P6), canonical term leakage is BLOCKING; otherwise WARNING.
_POLICY_RESOLVER = PolicyResolver(list(PolicyPriority))

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

    Inputs: source markdown (str | Path), RuntimeContext, AuditTrail.
    Outputs: tuple[DocumentProfile, StructuralMap].
    Invariant: node_count(structural_map) == node_count(source_AST).
    Failure Condition: EMPTY_SOURCE, MALFORMED_MARKDOWN (raises
    BrokenMarkdown); at L3/L4, the kernel raises ConformanceFailure
    (TRA-036).

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
        # TRA-E5-003 (round 5): raise BrokenMarkdown (not base TRAException)
        # so route_exception dispatches to recover_broken_markdown which
        # returns Severity.BLOCKING per Spec §6 BROKEN_MARKDOWN. Previously
        # raised TRAException("EMPTY_SOURCE") which fell through to the
        # default route_exception return (WARNING + PRESERVE_SOURCE) —
        # violating the Spec §6 "Blocking Error" mandate.
        raise BrokenMarkdown(
            detail="EMPTY_SOURCE: document contains no translatable content"
        )

    try:
        structural_map, registry = build_structural_map(source)
    except Exception as exc:  # noqa: BLE001 - surface as spec failure
        raise BrokenMarkdown(
            f"MALFORMED_MARKDOWN: unable to parse structure ({exc})"
        ) from exc

    # TRA-071: structural validation pass. markdown-it-py is too lenient to
    # raise on malformed input (unclosed fences, etc.), so the BrokenMarkdown
    # recovery procedure was effectively dead. This pass detects spec-defined
    # malformed cases and raises BrokenMarkdown so the kernel's EXCEPTION_HANDLER
    # path (TRA-004) routes it through _recover.
    _validate_markdown_structure(source)

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


# Fenced code block detection (TRA-071): ``` or ~~~ followed by optional
# language tag. Matches both backtick and tilde fences per CommonMark spec.
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*$", re.MULTILINE)


def _validate_markdown_structure(source: str) -> None:
    """TRA-071: detect spec-defined malformed markdown that markdown-it-py
    parses leniently. Currently checks for unclosed fenced code blocks.

    Raises BrokenMarkdown if any fence is unclosed. This makes the
    BrokenMarkdown recovery procedure reachable in production (previously
    it was dead code because markdown-it-py never raises).
    """
    fences = list(_FENCE_RE.finditer(source))
    # Fences must come in pairs (open + close). An odd count means at least
    # one fence is unclosed.
    if len(fences) % 2 != 0:
        # Find the unclosed fence (the last one with no matching close).
        unclosed = fences[-1]
        line_num = source.count("\n", 0, unclosed.start()) + 1
        raise BrokenMarkdown(
            f"MALFORMED_MARKDOWN: unclosed fenced code block at line {line_num} "
            f"(fence: {unclosed.group(0).strip()!r}). markdown-it-py parses this "
            f"leniently, but the TRA spec requires a closed fence."
        )


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


def _module(ctx: RuntimeContext) -> LanguageModuleProtocol:
    """Return the active language module (TRA-002). Prefers ctx.module
    (set by the kernel from the registry); falls back to the module-level
    _MODULE singleton for direct ISA calls in tests.

    TRA-B5-012 (round 5): return type is now `LanguageModuleProtocol`
    instead of `Any`. This lets mypy --strict catch typos in method names
    (e.g. get_glossary_mappings vs get_glossary_mapping) at call sites.
    """
    return ctx.module if ctx.module is not None else _MODULE


def build_glossary(
    source: str,
    profile: DocumentProfile,
    ctx: RuntimeContext,
    evidence: EvidenceRegistry,
    audit: AuditTrail,
) -> tuple[list[GlossaryEntry], list[ForbiddenMapping]]:
    """Establish canonical terminology; flag drift targets.

    Inputs: source markdown, DocumentProfile, RuntimeContext,
    EvidenceRegistry, AuditTrail.
    Outputs: tuple[list[GlossaryEntry], list[ForbiddenMapping]].
    Invariant: every recurring term (>=2x) gets exactly one canonical mapping
    unless context_sensitive. CONFLICTING_MAPPINGS raised on two targets.
    Failure Condition: GLOSSARY_CONFLICT (raises GlossaryConflict); at
    L3/L4, the kernel's _recover dispatcher handles it (TRA-041).
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

    Inputs: source markdown, StructuralMap, RuntimeContext,
    EvidenceRegistry, AuditTrail.
    Outputs: list[Entity] (each with mutable=False).
    Invariant: entities excluded from translation; casing/punctuation preserved.
    Failure Condition: ENTITY_AMBIGUITY (when a token matches multiple
    entity patterns and entity_type_hint returns None — logged via
    recover_entity_ambiguity, non-halting).

    TRA-038 (round 4 remediation): when a token matches multiple entity
    patterns (e.g., both ACRONYM_RE and PRODUCT_RE) AND the module's
    entity_type_hint returns None (no authoritative classification), the
    ambiguity is logged to unresolved_ambiguities via the recovery procedure
    (recover_entity_ambiguity) and the token is treated as Entity (immutable).
    This surfaces ambiguous tokens to the L4 audit trail without halting
    the pipeline — the entity table still completes with the best-guess
    classification.
    """
    from .recovery import recover_entity_ambiguity
    from .utils import ACRONYM_RE, PRODUCT_RE, VERSION_RE

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
        # TRA-038 (round 4): if the module hint is None (no authoritative
        # classification) AND the token matches multiple entity patterns,
        # log the ambiguity via the recovery procedure (which adds it to
        # unresolved_ambiguities with WARNING severity) and continue with
        # the best-guess classification. This surfaces ambiguous tokens to
        # the L4 audit trail without halting the pipeline.
        if hint is None:
            pattern_matches = [
                pat_name
                for pat_name, pat in (
                    ("VERSION_RE", VERSION_RE),
                    ("ACRONYM_RE", ACRONYM_RE),
                    ("PRODUCT_RE", PRODUCT_RE),
                )
                if pat.fullmatch(ent.name)
            ]
            if len(pattern_matches) > 1:
                # Log the ambiguity without raising — the recovery procedure
                # adds it to unresolved_ambiguities so the L4 audit trail
                # captures the decision point.
                recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)
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

    Inputs: source_segment, RuntimeContext, TranslationCache,
    EvidenceRegistry, AuditTrail, optional llm_translate callback.
    Outputs: TranslationResult (translation, evidence_ids, cache_hit).
    Invariant: factual qualifiers/numbers/epistemic markers preserved;
    terminology matches glossary; entities inserted verbatim.
    Failure Condition: loss of meaning, hallucination of facts, or
    violation of Glossary invariant. CertaintyConflict raised in the LLM
    path when a forbidden drift target is detected (TRA-038). UnknownTerm
    raised (non-halting) when a CJK token has no match (TRA-A5-003).

    Cache-first (Spec §0.4): identical context -> byte-identical output.
    Deterministic rule path when no LLM seam is supplied.
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
            # TRA-076: sanitize LLM output through the same chokepoint as
            # source input. A malicious/compromised LLM could inject bidi
            # overrides, null bytes, or BOM into the translation (OWASP A03).
            from .utils import sanitize_input

            target = sanitize_input(target)
            basis = "LLM decision"
            # TRA-033: guard against empty/None LLM output. These bypass the
            # except block entirely (no exception is raised) but produce
            # invalid translations. Degrade to the rule path instead.
            if not target:
                raise ValueError("llm_translate returned empty/None output")
            # TRA-038 (round 4): detect epistemic drift in LLM output.
            # If the LLM returned a forbidden drift target for a source term
            # in the epistemic lexicon, raise CertaintyConflict. This must
            # be checked BEFORE the except block so it propagates to the
            # kernel's _recover (not caught by the graceful-degradation
            # handler, which would silently mask the conflict).
            _raise_on_certainty_conflict(source_segment, target, ctx)
        except TRAException:
            # TRA-038 (round 4): CertaintyConflict (and other TRAExceptions
            # raised inside the try block) must propagate to the kernel's
            # _recover, NOT be caught by the graceful-degradation handler.
            # The handler below is for non-TRA exceptions (LLM client errors,
            # network issues, ValueError from empty output) that should
            # degrade to the rule path.
            raise
        except Exception as exc:  # noqa: BLE001 - graceful degradation (§6.5.4)
            # LLM unavailable / errored: degrade to the deterministic rule
            # path so translation still completes (never self-score, never
            # raise). The rule path is weaker on fluency but preserves all
            # BLOCKING invariants (factual / entity / terminology / epistemic).
            target, basis, _unknown = _rule_translate(
                source_segment,
                glossary,
                entities,
                module=ctx.module,
                unresolved_ambiguities=ctx.unresolved_ambiguities,
            )
            # Emit ONE complete audit record (evidence + degraded flag) and
            # return early. Previously the code fell through to emit a SECOND
            # record without the degraded flag — an auditor inspecting the
            # last record per segment would miss the degradation (TRA-015).
            # TRA-078: sanitize the exception repr to redact potential
            # secrets (API keys, Bearer tokens) before storing in the audit
            # trail (OWASP A09).
            from .kernel import _sanitize_exc_repr

            safe_exc_repr = _sanitize_exc_repr(exc)
            rec = EvidenceRecord(
                type=EvidenceType.LLM_DECISION,
                module="isa.translate_segment",
                source_span=source_segment,
                target_span=target,
                rationale=(
                    f"{basis} (glossary + entity + epistemic substitution; "
                    f"degraded from llm_unavailable: {safe_exc_repr})"
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
                    "reason": f"llm_unavailable: {safe_exc_repr}",
                },
            )
            return result
    else:
        target, basis, unknown_tokens = _rule_translate(
            source_segment,
            glossary,
            entities,
            unresolved_ambiguities=ctx.unresolved_ambiguities,
        )
        # TRA-A5-003 (round 5): emit an EXCEPTION_HANDLER audit record for
        # each unknown CJK token discovered by _log_unknown_cjk. The
        # recovery procedure has already populated unresolved_ambiguities
        # (TRA-038); this audit record surfaces the decision point in the
        # audit_trace.jsonl so L4 forensic analysis can reconstruct which
        # terms were unknown. Non-halting — translation continues with
        # the partial result.
        for token in unknown_tokens:
            audit.append(
                "EXCEPTION_HANDLER",
                "UNKNOWN_TERM",
                [],
                artifact_snapshot={
                    "severity": "WARNING",
                    "action": "PRESERVE_SOURCE",
                    "detail": "Term not in glossary or domain module; "
                    "source preserved.",
                    "source_term": token,
                    "reason": (
                        f'UnknownTerm("UNKNOWN_TERM: {token!r} not in glossary/module")'
                    ),
                },
                flags_raised=["WARNING"],
            )

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
    unresolved_ambiguities: list[str] | None = None,
) -> tuple[str, str, list[str]]:
    """Deterministic canonical translation via glossary + entity + epistemic.

    If ``module`` is supplied (TRA-002), use its rule layer; otherwise fall
    back to the module-level ``_MODULE`` singleton (backward compat).

    TRA-038 (round 4 remediation): logs UnknownTerm to unresolved_ambiguities
    when a CJK token (U+4E00..U+9FFF) has no glossary match, no entity match,
    no epistemic-lexicon match, and is not a common particle (stop-word).
    The logging is non-halting — the pipeline continues with the source term
    preserved. This surfaces unknown terms to the L4 audit trail so a
    forensic auditor can reconstruct the decision points.
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
    # 4. Entities are preserved verbatim (already in source form; no
    #    transformation needed — the rule path never alters entities).
    #    TRA-073 (round 3): removed dead `out = out` no-op loop.
    # 5. TRA-038 (round 4): detect unknown CJK terms that survived all
    #    substitution passes. A CJK token with no match in glossary, entities,
    #    or epistemic lexicon — and not a common particle — is "unknown" and
    #    is logged to unresolved_ambiguities (non-halting).
    # TRA-A5-003 (round 5): _log_unknown_cjk now RETURNS the list of unknown
    # tokens so translate_segment can emit EXCEPTION_HANDLER audit records.
    unknown_tokens: list[str] = []
    if unresolved_ambiguities is not None:
        unknown_tokens = _log_unknown_cjk(
            out, glossary, entities, unresolved_ambiguities
        )
    return out, "rule-based", unknown_tokens


# Common CJK grammatical particles that are NOT "terms" in the glossary sense.
# Raising UnknownTerm for these would produce false positives. This list is
# intentionally conservative — only high-frequency function words.
_CJK_STOP_WORDS: frozenset[str] = frozenset(
    {
        "的",
        "是",
        "在",
        "了",
        "和",
        "与",
        "或",
        "及",
        "等",
        "也",
        "都",
        "就",
        "还",
        "不",
        "没",
        "有",
        "这",
        "那",
        "一",
        "个",
        "些",
        "上",
        "下",
        "中",
        "里",
        "外",
        "为",
        "对",
        "从",
        "到",
        "向",
        "以",
        "于",
        "把",
        "被",
        "让",
        "使",
        "给",
        "而",
        "且",
        "则",
        "若",
        "如",
        "可",
        "能",
        "会",
        "需",
        "应",
        "该",
        "须",
        "要",
        "想",
        "做",
        "看",
        "听",
        "说",
        "写",
        "读",
        "学",
        "用",
        "生",
        "死",
        "好",
        "坏",
        "大",
        "小",
        "多",
        "少",
        "高",
        "低",
        "长",
        "短",
        "新",
        "旧",
        "早",
        "晚",
        "前",
        "后",
        "左",
        "右",
        "内",
        "本",
        "末",
        "始",
        "终",
        "首",
        "尾",
        "再",
        "又",
        "只",
        "才",
        "已",
        "曾",
        "将",
        "正",
        "刚",
        "快",
        "慢",
    }
)

# CJK Unified Ideographs range (U+4E00..U+9FFF).
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def _log_unknown_cjk(
    text: str,
    glossary: dict[str, str],
    entities: list[Entity],
    unresolved_ambiguities: list[str],
) -> list[str]:
    """Log UnknownTerm for each CJK token that has no match in the glossary,
    entity table, or epistemic lexicon, and is not a stop-word.

    TRA-038 (round 4): previously, unknown CJK terms passed through silently.
    Now they are logged to unresolved_ambiguities via the recovery procedure
    (recover_unknown_term) so the L4 audit trail captures the decision points.
    Non-halting — the pipeline continues with the source term preserved.

    TRA-A5-003 (round 5): previously this called `recover_unknown_term`
    directly, bypassing the kernel's `_recover` dispatcher (no
    EXCEPTION_HANDLER audit record was emitted). Now this function
    RETURNS the list of unknown tokens (still populating
    unresolved_ambiguities via the recovery procedure for backward
    compatibility). `translate_segment` then emits an EXCEPTION_HANDLER
    audit record per returned token via `audit.append`, then continues
    with the (partial) translation — non-halting.

    Returns:
        The list of unknown CJK tokens discovered (de-duplicated, order
        preserved).
    """
    from .recovery import recover_unknown_term

    entity_names = {e.name for e in entities}
    epistemic_sources = set(zh_en.EPISTEMIC_LEXICON.keys())
    glossary_sources = set(glossary.keys())
    known_sources = glossary_sources | epistemic_sources | entity_names
    unknown_tokens: list[str] = []
    for match in _CJK_RE.finditer(text):
        token = match.group(0)
        # Skip if the token is a stop-word.
        if token in _CJK_STOP_WORDS:
            continue
        # Skip if the token is exactly a known source.
        if token in known_sources:
            continue
        # Skip if any known source is a substring of the token (e.g.,
        # "系统成立" contains "成立" which is in the epistemic lexicon).
        if any(src in token for src in known_sources if len(src) >= 2):
            continue
        # Skip if any single-char stop-word is the entire token.
        if len(token) == 1 and token in _CJK_STOP_WORDS:
            continue
        # The token is unknown — log it via the recovery procedure (non-halting).
        recover_unknown_term(token, unresolved_ambiguities)
        if token not in unknown_tokens:
            unknown_tokens.append(token)
    return unknown_tokens


def _raise_on_certainty_conflict(
    source_segment: str,
    target: str,
    ctx: RuntimeContext,
) -> None:
    """Raise CertaintyConflict if the LLM returned a forbidden drift target
    for a source term in the epistemic lexicon.

    TRA-038 (round 4): previously, the LLM path never validated epistemic
    drift — a compromised or hallucinating LLM could return "Valid" for
    source "成立" (canonical: "Confirmed") and it would pass through. Now
    the L4 audit trail will contain CERTAINTY_CONFLICT records so a
    forensic auditor can reconstruct these decision points.

    The kernel routes CertaintyConflict through _recover →
    recover_certainty_conflict, which preserves the canonical marker and
    adds the term to unresolved_ambiguities.
    """
    from .exceptions import CertaintyConflict
    from .modules import zh_en as zh_en_module

    # Check each epistemic source term: if it appears in the source segment,
    # the LLM output must NOT contain any of its forbidden drift targets.
    for src_term, _canonical_target in zh_en_module.EPISTEMIC_LEXICON.items():
        if src_term not in source_segment:
            continue
        # Look up the forbidden targets for this source term.
        # FORBIDDEN_TARGETS values are slash-separated strings like
        # "Valid/True/Correct" — split on "/" to get individual targets.
        forbidden_str = zh_en_module.FORBIDDEN_TARGETS.get(src_term, "")
        if not forbidden_str:
            continue
        forbidden_targets = [t.strip() for t in forbidden_str.split("/") if t.strip()]
        for forbidden_target in forbidden_targets:
            if forbidden_target in target:
                raise CertaintyConflict(term=src_term)


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

    Inputs: target markdown, source markdown, RuntimeContext, AuditTrail.
    Outputs: list[Diagnostic] (each with severity, subsystem, issue,
    evidence, action).
    Invariant: all violations categorized by severity (BLOCKING / WARNING /
    INFO); never self-scores (reads only target/source/ctx, not
    confidence_note). Severity arbitrated by PolicyResolver (TRA-072).
    Failure Condition: None (verification always completes, may flag
    errors — Spec §3 VERIFY_OUTPUT).

    Exhaustive; cannot skip sections. Every violation -> Diagnostic with
    severity BLOCKING / WARNING / INFO.
    """
    diagnostics: list[Diagnostic] = []
    entities = ctx.entity_table

    # Structural verification (TRA-042 round 4: extended beyond heading count).
    # Check heading count, table row count, list item count, blockquote line
    # count, HR count, and fenced code block count. Each mismatch raises a
    # structural diagnostic so a non-benchmarked input cannot silently pass
    # L3 with broken structure. These checks are regex-based and run on
    # source/target text directly (no structural_map required).
    # TRA-072 (round 4): severity is arbitrated by the PolicyResolver.
    # Structural Integrity (P2) vs Target Fluency (P6) — if P2 wins (default),
    # severity is BLOCKING; if P6 wins, WARNING.
    structural_severity = (
        Severity.BLOCKING
        if _POLICY_RESOLVER.wins(
            PolicyPriority.STRUCTURAL_INTEGRITY, PolicyPriority.TARGET_FLUENCY
        )
        else Severity.WARNING
    )
    src_headings = len(_HEADING_RE.findall(source))
    tgt_headings = len(_HEADING_RE.findall(target))
    if src_headings != tgt_headings:
        diagnostics.append(
            Diagnostic(
                severity=structural_severity,
                subsystem="structural",
                issue="Heading count mismatch after translation",
                evidence=f"source={src_headings} target={tgt_headings}",
                action="Restore heading hierarchy",
            )
        )

    # TRA-042: table row count. A table row is a line starting with |.
    _TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$", re.MULTILINE)
    src_table_rows = len(_TABLE_ROW_RE.findall(source))
    tgt_table_rows = len(_TABLE_ROW_RE.findall(target))
    if src_table_rows != tgt_table_rows:
        diagnostics.append(
            Diagnostic(
                severity=structural_severity,
                subsystem="structural",
                issue="Table row count mismatch after translation",
                evidence=f"source={src_table_rows} target={tgt_table_rows}",
                action="Restore table rows",
            )
        )

    # TRA-042: list item count. A list item is a line starting with
    # -, *, or + (unordered) or N. (ordered, e.g. "1.", "2.", "10.").
    # TRA-A5-005 (round 5): the previous regex only matched unordered
    # items (`[-*+]`); ordered items (`\d+\.`) were silently skipped,
    # so a source with 5 ordered items and a target with 3 would pass.
    _LIST_ITEM_RE = re.compile(
        r"^\s*(?:[-*+]|\d+\.)\s|\n\s*(?:[-*+]|\d+\.)\s",
        re.MULTILINE,
    )
    src_list_items = len(_LIST_ITEM_RE.findall(source))
    tgt_list_items = len(_LIST_ITEM_RE.findall(target))
    if src_list_items != tgt_list_items:
        diagnostics.append(
            Diagnostic(
                severity=structural_severity,
                subsystem="structural",
                issue="List item count mismatch after translation",
                evidence=f"source={src_list_items} target={tgt_list_items}",
                action="Restore list items",
            )
        )

    # TRA-042: blockquote line count. A blockquote line starts with >.
    # TRA-A5-005 (round 5): the previous regex required whitespace after
    # `>` (`^\s*>\s`), but CommonMark also allows `>text` (no space).
    # Now matches `>` at the start of a line regardless of trailing space.
    _BLOCKQUOTE_RE = re.compile(r"^\s*>", re.MULTILINE)
    src_blockquotes = len(_BLOCKQUOTE_RE.findall(source))
    tgt_blockquotes = len(_BLOCKQUOTE_RE.findall(target))
    if src_blockquotes != tgt_blockquotes:
        diagnostics.append(
            Diagnostic(
                severity=structural_severity,
                subsystem="structural",
                issue="Blockquote line count mismatch after translation",
                evidence=f"source={src_blockquotes} target={tgt_blockquotes}",
                action="Restore blockquote lines",
            )
        )

    # TRA-042: horizontal rule count. An HR is a line of only ---, ***, or ___
    # (3+ chars, possibly with leading whitespace).
    _HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
    src_hrs = len(_HR_RE.findall(source))
    tgt_hrs = len(_HR_RE.findall(target))
    if src_hrs != tgt_hrs:
        diagnostics.append(
            Diagnostic(
                severity=structural_severity,
                subsystem="structural",
                issue="Horizontal rule count mismatch after translation",
                evidence=f"source={src_hrs} target={tgt_hrs}",
                action="Restore horizontal rules",
            )
        )

    # TRA-042: fenced code block count. A fence is a line starting with
    # ``` or ~~~. Count opening fences (each code block has one open + one
    # close, so divide by 2 for block count, but comparing raw fence-line
    # counts is equivalent for mismatch detection).
    _CODE_FENCE_RE = re.compile(r"^\s*(?:```|~~~)", re.MULTILINE)
    src_fences = len(_CODE_FENCE_RE.findall(source))
    tgt_fences = len(_CODE_FENCE_RE.findall(target))
    if src_fences != tgt_fences:
        diagnostics.append(
            Diagnostic(
                severity=structural_severity,
                subsystem="structural",
                issue="Code fence count mismatch after translation",
                evidence=f"source={src_fences} target={tgt_fences}",
                action="Restore code fences",
            )
        )

    # TRA-A5-013 (round 5): Factual Integrity (P1) — the highest priority.
    # Spec §5.1 defines factual integrity as "Numbers, units, logical
    # conditions, empirical claims". The LLM seam is the natural place
    # for drift (e.g. summarizing `v0.5.0` as `v0.5`, or `2024-01-15` as
    # `2024-01-05`). Extract version-like tokens, dates, and numeric
    # quantities from source, and verify each appears verbatim in target.
    factual_severity = (
        Severity.BLOCKING
        if _POLICY_RESOLVER.wins(
            PolicyPriority.FACTUAL_INTEGRITY, PolicyPriority.TARGET_FLUENCY
        )
        else Severity.WARNING
    )
    # Version-like tokens: v0.5.0, v1.2.3, 0.5.0, 1.2.3 (with optional v prefix).
    _VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")
    # ISO-style dates: 2024-01-15, 2024-01 (year-month).
    _DATE_RE = re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b")
    for factual_pattern, label in (
        (_VERSION_RE, "version"),
        (_DATE_RE, "date"),
    ):
        src_tokens = set(factual_pattern.findall(source))
        tgt_tokens = set(factual_pattern.findall(target))
        missing = src_tokens - tgt_tokens
        for token in sorted(missing):
            diagnostics.append(
                Diagnostic(
                    severity=factual_severity,
                    subsystem="factual",
                    issue=f"{label.capitalize()} drift after translation",
                    evidence=f"source={token} target=<missing>",
                    action=f"Restore {label} {token} verbatim",
                )
            )

    # Factual: entities preserved verbatim (numbers/versions/casing).
    # TRA-072 (round 4): severity is arbitrated by the PolicyResolver.
    # Entity Preservation (P3) vs Target Fluency (P6) — if P3 wins (default),
    # severity is BLOCKING; if P6 wins, WARNING.
    entity_severity = (
        Severity.BLOCKING
        if _POLICY_RESOLVER.wins(
            PolicyPriority.ENTITY_PRESERVATION, PolicyPriority.TARGET_FLUENCY
        )
        else Severity.WARNING
    )
    for ent in entities:
        if ent.name not in target:
            diagnostics.append(
                Diagnostic(
                    severity=entity_severity,
                    subsystem="entity",
                    issue=f"Entity not preserved: {ent.name!r}",
                    evidence="expected verbatim occurrence in target",
                    action="Restore entity from entity_table",
                )
            )

    # Terminology: glossary terms must appear as canonical targets.
    # TRA-009 + TRA-006: severity is policy-driven via the PolicyResolver.
    # CANONICAL term leakage: Terminological Consistency (P4) vs Target
    # Fluency (P6) — if P4 wins, severity is BLOCKING; if P6 wins, WARNING.
    # CONTEXT_SENSITIVE term leakage: always WARNING (fluency may legitimately
    # override context-dependent mappings).
    from .memory import GlossaryStatus

    # TRA-006: consult the PolicyResolver to determine whether Terminological
    # Consistency wins over Target Fluency. This makes the severity arbitration
    # explicit and testable (monkeypatching the resolver changes the severity).
    term_wins_over_fluency = _POLICY_RESOLVER.wins(
        PolicyPriority.TERMINOLOGICAL_CONSISTENCY,
        PolicyPriority.TARGET_FLUENCY,
    )

    for entry in ctx.glossary_cache:
        if entry.source in target:  # untranslated source term leaked
            if entry.status == GlossaryStatus.CANONICAL:
                # TRA-006: severity is arbitrated by the PolicyResolver.
                # Default: TERMINOLOGICAL_CONSISTENCY (P4) wins over
                # TARGET_FLUENCY (P6) → BLOCKING. If the resolver is
                # monkeypatched to return False, severity drops to WARNING.
                severity = (
                    Severity.BLOCKING if term_wins_over_fluency else Severity.WARNING
                )
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
    # TRA-072 (round 4): severity is arbitrated by the PolicyResolver.
    # Epistemic Fidelity (P5) vs Target Fluency (P6) — if P5 wins (default),
    # severity is BLOCKING; if P6 wins, WARNING.
    epistemic_severity = (
        Severity.BLOCKING
        if _POLICY_RESOLVER.wins(
            PolicyPriority.EPISTEMIC_FIDELITY, PolicyPriority.TARGET_FLUENCY
        )
        else Severity.WARNING
    )
    for fm in _forbidden_from_module(ctx):
        if fm.forbidden_target in target:
            diagnostics.append(
                Diagnostic(
                    severity=epistemic_severity,
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

    Inputs: target_segment, source_segment, Diagnostic, RuntimeContext,
    EvidenceRegistry, AuditTrail, optional attempt/max_retries/segment_index.
    Outputs: repaired target_segment (str).
    Invariant: must not introduce new BLOCKING; must not violate a higher
    policy. UNRECOVERABLE if fixing would break a higher-priority invariant.
    Failure Condition: unable to resolve violation without violating a
    higher-priority Policy (raises Unrecoverable — Spec §3 REPAIR_SEGMENT).

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
        # TRA-A4-011 (round 4): removed dead `repaired = repaired` no-op.
        # If an entity is missing from the output, we cannot conjure it
        # without the source segment context (not available here). Downstream
        # verify_output catches missing entities as BLOCKING, so this is
        # defense-in-depth. The prior `repaired = repaired` self-assignment
        # was misleading — it suggested action where none existed.
        pass

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
    elif diagnostic.subsystem == "force_unrecoverable":
        # TRA-E5-005 (round 5): synthetic diagnostic injected by
        # --force-unrecoverable debug flag. Always raise Unrecoverable
        # so the HITL path fires for e2e testing.
        raise Unrecoverable(
            "UNRECOVERABLE: --force-unrecoverable synthetic diagnostic "
            "(HITL testability flag)"
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
