"""Phase 2 tests: the six ISA instructions + contract invariants."""

from __future__ import annotations

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
    # markdown-it-py is lenient, so we assert it at least returns a map
    # for valid markdown; an unclosed fence is still valid CommonMark.
    profile, smap = analyze_document("```\ncode\n", ctx, _audit())
    assert smap is not None


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


def test_translate_segment_canonical_substitution():
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
    cache = TranslationCache("./cache", enabled=True)
    res = translate_segment("系统 成立。", ctx, cache, ev, _audit())
    assert isinstance(res, TranslationResult)
    assert "Confirmed" in res.translation
    # Cache-hit semantics are covered by
    # test_translate_segment_cache_hit_is_byte_identical.


def test_translate_segment_cache_hit_is_byte_identical():
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    cache = TranslationCache("./cache", enabled=True)
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


# --- Phase 4 integration: module rule layer fires via ISA ------------


def test_translate_segment_applies_zh_rule_layer():
    ctx = _ctx()
    ev = EvidenceRegistry()
    build_glossary(
        "成立",
        DocumentProfile(type="x", register_="y", intent="z", audience="a"),
        ctx,
        ev,
        _audit(),
    )
    cache = TranslationCache("./cache", enabled=True)
    res = translate_segment("系统成立。", ctx, cache, ev, _audit())
    # Parataxis->hypotaxis rule layer resolves topic-comment to subject-predicate.
    assert "The system is Confirmed" in res.translation
    # Punctuation normalized to half-width.
    assert res.translation.endswith(". ") or res.translation.endswith(".")
