"""Phase 2 tests: the six ISA instructions + contract invariants."""

from __future__ import annotations

import pytest
from tra.cache import TranslationCache, TranslationResult
from tra.diagnostics import (
    AuditTrail,
    EvidenceRegistry,
    EvidenceType,
    Severity,
)
from tra.exceptions import GlossaryConflict, TRAException
from tra.isa import (
    analyze_document,
    build_entity_table,
    build_glossary,
    repair_segment,
    translate_segment,
    verify_output,
)
from tra.memory import DocumentProfile, RuntimeContext


def _ctx() -> RuntimeContext:
    return RuntimeContext()


def _audit() -> AuditTrail:
    return AuditTrail("audit_trace.jsonl")


# --- ANALYZE_DOCUMENT ---


def test_analyze_builds_profile_and_map():
    ctx = _ctx()
    profile, smap = analyze_document(
        "# Security Advisory\n\n执行环境 here.\n", ctx, _audit()
    )
    assert isinstance(profile, DocumentProfile)
    assert smap.node_count > 0
    assert ctx.document_profile is profile
    assert ctx.structural_map is smap


def test_analyze_empty_source_raises():
    ctx = _ctx()
    try:
        analyze_document("   \n\n", ctx, _audit())
        raise AssertionError("expected EMPTY_SOURCE")
    except TRAException as exc:
        assert "EMPTY_SOURCE" in str(exc)


def test_analyze_malformed_raises():
    ctx = _ctx()
    # TRA-071: an unclosed fenced code block now raises BrokenMarkdown
    # (previously markdown-it-py parsed it leniently and the BrokenMarkdown
    # recovery procedure was dead code). The structural validation pass in
    # analyze_document detects the unclosed fence and raises.
    from tra.exceptions import BrokenMarkdown

    with pytest.raises(BrokenMarkdown, match=r"unclosed|fence|malformed"):
        analyze_document("```\ncode\n", ctx, _audit())


# --- BUILD_GLOSSARY ---


def test_build_glossary_emits_canonical_entries():
    ctx = _ctx()
    ev = EvidenceRegistry()
    entries, forbidden = build_glossary(
        "成立 执行环境",
        DocumentProfile(
            type="Advisory", register_="Authoritative", intent="x", audience="y"
        ),
        ctx,
        ev,
        _audit(),
    )
    sources = {e.source for e in entries}
    assert "成立" in sources
    assert "执行环境" in sources
    assert all(e.status.value == "canonical" for e in entries)
    # Evidence emitted for each entry.
    assert len([e for e in ev.all() if e.type == EvidenceType.TERM_MATCH]) == len(
        entries
    )
    # Forbidden drift targets captured.
    banned = {f.forbidden_target for f in forbidden}
    assert "runtime" in banned  # 执行环境 -> runtime is drift


def test_build_glossary_conflict_raises():
    ctx = _ctx()
    ev = EvidenceRegistry()
    # Monkeypatch the module mapping to force a conflict.
    from tra import isa

    orig = isa._MODULE.get_glossary_mappings
    isa._MODULE.get_glossary_mappings = lambda: {"成立": "Valid"}  # drift target
    try:
        build_glossary(
            "成立",
            DocumentProfile(type="x", register_="y", intent="z", audience="a"),
            ctx,
            ev,
            _audit(),
        )
        raise AssertionError("expected CONFLICTING_MAPPINGS")
    except GlossaryConflict:
        pass
    finally:
        isa._MODULE.get_glossary_mappings = orig


# --- BUILD_ENTITY_TABLE ---


def test_build_entity_table_immutable():
    ctx = _ctx()
    ev = EvidenceRegistry()
    ents = build_entity_table(
        "RustVMM v0.5.0 released", ctx.structural_map, ctx, ev, _audit()
    )
    names = {e.name for e in ents}
    assert "RustVMM" in names
    assert "v0.5.0" in names
    assert all(e.mutable is False for e in ents)
    assert all(e.type.value in ("product", "version") for e in ents)


# --- TRANSLATE_SEGMENT ---


def test_translate_segment_canonical_substitution(tmp_path):
    ctx = _ctx()
    # Build glossary via the real instruction to populate ctx.
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    cache = TranslationCache(str(tmp_path / "cache"), enabled=True)
    res = translate_segment("系统 成立。", ctx, cache, ev, _audit())
    assert isinstance(res, TranslationResult)
    assert "Confirmed" in res.translation
    # Cache-hit semantics are covered by
    # test_translate_segment_cache_hit_is_byte_identical.


def test_translate_segment_cache_hit_is_byte_identical(tmp_path):
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    cache = TranslationCache(str(tmp_path / "cache"), enabled=True)
    r1 = translate_segment("成立 here", ctx, cache, ev, _audit())
    r2 = translate_segment("成立 here", ctx, cache, ev, _audit())
    assert r2.cache_hit is True
    assert r1.translation == r2.translation


# --- VERIFY_OUTPUT ---


def test_verify_flags_missing_entity_blocking():
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_entity_table("RustVMM present", ctx.structural_map, ctx, ev, _audit())
    diags = verify_output(
        "translated without the name", "RustVMM present", ctx, _audit()
    )
    blocking = [d for d in diags if d.severity == Severity.BLOCKING]
    assert blocking
    assert any("RustVMM" in d.issue for d in blocking)


def test_verify_flags_epistemic_drift_blocking():
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    diags = verify_output("it is Valid now", "成立", ctx, _audit())
    blocking = [d for d in diags if d.severity == Severity.BLOCKING]
    assert blocking
    assert any("Valid" in d.issue for d in blocking)


def test_verify_clean_doc_no_blocking():
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    build_entity_table("RustVMM v0.5.0", ctx.structural_map, ctx, ev, _audit())
    target = "RustVMM v0.5.0 is Confirmed."
    src = "RustVMM v0.5.0 成立"
    diags = verify_output(target, src, ctx, _audit())
    assert not [d for d in diags if d.severity == Severity.BLOCKING]


# --- REPAIR_SEGMENT ---


def test_repair_resolves_epistemic_drift():
    from tra.diagnostics import Diagnostic

    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    diag = Diagnostic(
        severity=Severity.BLOCKING,
        subsystem="epistemic",
        issue="Epistemic drift: Valid (from 成立)",
        evidence="TRA-MODULE-ZH-EN §3 forbids this mapping",
        action="Revert to canonical certainty marker",
    )
    repaired = repair_segment("it is Valid", "成立", diag, ctx, ev, _audit())
    assert "Confirmed" in repaired
    assert "Valid" not in repaired


# --- TRA-028: repair_segment must raise on new BLOCKING at ANY attempt ---


def test_repair_raises_on_new_blocking_at_attempt_1():
    """TRA-003 / TRA-028: repair_segment must raise Unrecoverable when the
    repair introduces a new BLOCKING violation — regardless of attempt number.

    The surgical-repair invariant (TRA-ISA-REFERENCE.md §REPAIR_SEGMENT:
    "must not introduce new ones") is unconditional. Previously the code
    only raised when `attempt >= max_retries`, silently returning broken
    output at attempt=1.
    """
    from tra.diagnostics import Diagnostic
    from tra.exceptions import Unrecoverable

    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    # Glossary maps 成立 -> Confirmed. "Valid" is a forbidden drift target.
    # Terminology diagnostic asks the repair to translate the source term.
    diag = Diagnostic(
        severity=Severity.WARNING,
        subsystem="terminology",
        issue="Source term not translated: '成立'",
        evidence="expected canonical target 'Confirmed'",
        action="Apply canonical mapping",
    )
    # target "成立 Valid" — repair substitutes 成立 -> Confirmed, yielding
    # "Confirmed Valid" which contains the forbidden drift target "Valid".
    with pytest.raises(Unrecoverable):
        repair_segment(
            "成立 Valid",
            "成立 Valid",
            diag,
            ctx,
            ev,
            _audit(),
            attempt=1,
            max_retries=3,
        )


# --- TRA-029: verify_output must never read confidence_note -------------


def test_verify_output_ignores_confidence_note():
    """TRA-029: the 'never self-score' invariant (Spec §7) must hold at the
    enforcement boundary. verify_output must NOT read confidence_note even
    when low-confidence records are present in the context's glossary.

    Mutation testing confirmed that adding a confidence_note read to
    verify_output left all prior tests green. This test closes that gap.
    """
    from tra.memory import GlossaryEntry, GlossaryStatus

    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    # Inject a low-confidence glossary entry into the context — verify_output
    # reads ctx.glossary_cache, so if it self-scores it would flag this.
    ctx.glossary_cache.append(
        GlossaryEntry(
            source="低置信度词",
            target="low-confidence-term",
            status=GlossaryStatus.CANONICAL,
            confidence_note=0.01,  # very low — must NOT trigger any diagnostic
        )
    )
    # Clean target: no source terms, no forbidden targets, no missing entities.
    diags = verify_output("clean target text", "clean source text", ctx, _audit())
    # No diagnostic should reference the low-confidence entry.
    assert not any("low-confidence" in d.issue for d in diags)
    assert not any("低置信度" in d.issue for d in diags)


# --- TRA-030: severity classification is part of the spec contract -----


def test_verify_output_terminology_canonical_is_blocking():
    """TRA-009 + TRA-030: untranslated CANONICAL source terms are BLOCKING
    (Terminological Consistency P4 > Target Fluency P6, via PolicyResolver).
    A mutation demoting canonical terminology to WARNING would silently make
    the L3 gate more permissive than the policy stack allows.
    """
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    # Target still contains the untranslated CANONICAL source term "成立".
    diags = verify_output("成立 here", "成立 here", ctx, _audit())
    terminology = [d for d in diags if d.subsystem == "terminology"]
    assert terminology, "expected at least one terminology diagnostic"
    assert all(d.severity == Severity.BLOCKING for d in terminology)


def test_verify_output_structural_mismatch_is_blocking():
    """TRA-030: heading-count mismatch is BLOCKING (Priority 2). A mutation
    demoting structural to WARNING would silently make the L3 gate more
    permissive than the spec intends.
    """
    ctx = _ctx()
    # Source has 1 heading; target has 0 — structural mismatch.
    analyze_document("# Heading\n\nbody", ctx, _audit())
    diags = verify_output("no heading here", "# Heading\n\nbody", ctx, _audit())
    structural = [d for d in diags if d.subsystem == "structural"]
    assert structural, "expected at least one structural diagnostic"
    assert all(d.severity == Severity.BLOCKING for d in structural)


# --- Phase 4 integration: module rule layer fires via ISA ------------


def test_translate_segment_applies_zh_rule_layer(tmp_path):
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    cache = TranslationCache(str(tmp_path / "cache"), enabled=True)
    res = translate_segment("系统成立。", ctx, cache, ev, _audit())
    # Parataxis->hypotaxis rule layer resolves topic-comment to subject-predicate.
    assert "The system is Confirmed" in res.translation
    # Punctuation normalized to half-width.
    assert res.translation.endswith(". ") or res.translation.endswith(".")
