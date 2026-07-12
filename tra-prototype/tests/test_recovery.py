"""Phase 6.1: TRA-EXCEPTIONS recovery procedures (Spec §6)."""

from __future__ import annotations

from tra.diagnostics import Severity
from tra.exceptions import (
    BrokenMarkdown,
    CertaintyConflict,
    EntityAmbiguity,
    GlossaryConflict,
    UnknownTerm,
)
from tra.recovery import (
    RecoveryAction,
    RecoveryReport,
    recover_broken_markdown,
    recover_certainty_conflict,
    recover_entity_ambiguity,
    recover_glossary_conflict,
    recover_unknown_term,
    route_exception,
)


def test_unknown_term_preserves_source_and_logs_warning():
    amb: list[str] = []
    rep = recover_unknown_term("神秘术语", amb)
    assert rep.severity == Severity.WARNING
    assert rep.action == RecoveryAction.PRESERVE_SOURCE
    assert rep.source_term == "神秘术语"
    assert rep.added_to_ambiguities
    assert any("神秘术语" in a for a in amb)


def test_broken_markdown_halts_on_critical_loss():
    rep = recover_broken_markdown("missing H1", critical_hierarchy_lost=True)
    assert rep.severity == Severity.BLOCKING
    assert rep.action == RecoveryAction.HALT


def test_broken_markdown_best_effort_otherwise():
    rep = recover_broken_markdown("minor fence issue", critical_hierarchy_lost=False)
    assert rep.severity == Severity.BLOCKING
    assert rep.action == RecoveryAction.PRESERVE_SOURCE


def test_certainty_conflict_prioritizes_epistemic():
    amb: list[str] = []
    rep = recover_certainty_conflict("可能", amb)
    assert rep.action == RecoveryAction.PRIORITIZE_EPISTEMIC
    assert rep.severity == Severity.WARNING
    assert rep.added_to_ambiguities


def test_entity_ambiguity_defaults_to_entity():
    amb: list[str] = []
    rep = recover_entity_ambiguity("Configure", amb)
    assert rep.action == RecoveryAction.TREAT_AS_ENTITY
    assert rep.added_to_ambiguities


def test_glossary_conflict_blocking_first_occurrence_canonical():
    amb: list[str] = []
    rep = recover_glossary_conflict("成立", "Confirmed", amb)
    assert rep.severity == Severity.BLOCKING
    assert rep.action == RecoveryAction.USE_FIRST_OCCURRENCE
    assert rep.added_to_ambiguities


def test_route_exception_dispatches_each_type():
    amb: list[str] = []
    assert route_exception(UnknownTerm(term="x"), amb).code == "UNKNOWN_TERM"
    assert (
        route_exception(
            GlossaryConflict(term="成立", canonical_target="Confirmed"), amb
        ).code
        == "GLOSSARY_CONFLICT"
    )
    assert (
        route_exception(CertaintyConflict(term="可能"), amb).action
        == RecoveryAction.PRIORITIZE_EPISTEMIC
    )
    assert (
        route_exception(EntityAmbiguity(token="C"), amb).action
        == RecoveryAction.TREAT_AS_ENTITY
    )
    halt = route_exception(
        BrokenMarkdown(detail="x"), amb, critical_hierarchy_lost=True
    )
    assert halt.action == RecoveryAction.HALT


def test_route_exception_falls_back_for_unknown():
    amb: list[str] = []
    rep = route_exception(BrokenMarkdown(), amb)  # type: ignore[arg-type]
    assert isinstance(rep, RecoveryReport)
