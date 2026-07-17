"""TRA-EXCEPTIONS recovery procedures (Spec §6).

Each exception maps to a deterministic recovery procedure. The procedures are
pure: they take the context, append the mandated diagnostic/report, and update
`unresolved_ambiguities` where the spec requires. They do NOT mutate the target
text except where the spec says so (preserve source term; use first occurrence
as canonical for GLOSSARY_CONFLICT).

The Kernel calls `route_exception` from its EXCEPTION_HANDLER path; each
procedure returns a `RecoveryReport` so the audit trail and the L4 ambiguity
register can capture it atomically.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .exceptions import (
    BrokenMarkdown,
    CertaintyConflict,
    EntityAmbiguity,
    GlossaryConflict,
    TRAException,
    UnknownTerm,
    Unrecoverable,
)
from .memory import Severity


class RecoveryAction(StrEnum):
    """Spec-mandated recovery outcome for each exception."""

    PRESERVE_SOURCE = "PRESERVE_SOURCE"
    USE_FIRST_OCCURRENCE = "USE_FIRST_OCCURRENCE"
    TREAT_AS_ENTITY = "TREAT_AS_ENTITY"
    PRIORITIZE_EPISTEMIC = "PRIORITIZE_EPISTEMIC"
    HALT = "HALT"


@dataclass
class RecoveryReport:
    """Atomic record of one exception's recovery (feeds audit + L4 register)."""

    code: str
    severity: Severity
    action: RecoveryAction
    detail: str
    source_term: str | None = None
    added_to_ambiguities: bool = False


def _emit(
    ctx_ambiguities: list[str],
    code: str,
    severity: Severity,
    action: RecoveryAction,
    detail: str,
    source_term: str | None = None,
    *,
    add_to_ambiguities: bool = False,
) -> RecoveryReport:
    if add_to_ambiguities and source_term:
        note = f"{code}: {source_term} — {detail}"
        if note not in ctx_ambiguities:
            ctx_ambiguities.append(note)
    return RecoveryReport(
        code=code,
        severity=severity,
        action=action,
        detail=detail,
        source_term=source_term,
        added_to_ambiguities=add_to_ambiguities,
    )


def recover_unknown_term(term: str, ctx_ambiguities: list[str]) -> RecoveryReport:
    """UNKNOWN_TERM: log Warning, preserve source, add to ambiguities."""
    return _emit(
        ctx_ambiguities,
        UnknownTerm.code,
        Severity.WARNING,
        RecoveryAction.PRESERVE_SOURCE,
        "Term not in glossary or domain module; source preserved.",
        source_term=term,
        add_to_ambiguities=True,
    )


def recover_broken_markdown(
    detail: str, *, critical_hierarchy_lost: bool
) -> RecoveryReport:
    """BROKEN_MARKDOWN: Blocking; best-effort; halt if critical hierarchy lost."""
    action = (
        RecoveryAction.HALT
        if critical_hierarchy_lost
        else RecoveryAction.PRESERVE_SOURCE
    )
    detail_text = (
        "Critical hierarchy lost; halting."
        if critical_hierarchy_lost
        else f"Best-effort preservation. {detail}"
    )
    return RecoveryReport(
        code="BROKEN_MARKDOWN",
        severity=Severity.BLOCKING,
        action=action,
        detail=detail_text,
    )


def recover_certainty_conflict(term: str, ctx_ambiguities: list[str]) -> RecoveryReport:
    """CERTAINTY_CONFLICT: Warning; prioritize Epistemic Fidelity (Pri 5)."""
    return _emit(
        ctx_ambiguities,
        CertaintyConflict.code,
        Severity.WARNING,
        RecoveryAction.PRIORITIZE_EPISTEMIC,
        "Source hedging preserved; Epistemic Fidelity (Priority 5) wins.",
        source_term=term,
        add_to_ambiguities=True,
    )


def recover_entity_ambiguity(token: str, ctx_ambiguities: list[str]) -> RecoveryReport:
    """ENTITY_AMBIGUITY: Warning; default to Entity (immutable)."""
    return _emit(
        ctx_ambiguities,
        EntityAmbiguity.code,
        Severity.WARNING,
        RecoveryAction.TREAT_AS_ENTITY,
        "Treated as Entity (immutable) to prevent accidental translation.",
        source_term=token,
        add_to_ambiguities=True,
    )


def recover_glossary_conflict(
    term: str,
    canonical_target: str,
    ctx_ambiguities: list[str],
) -> RecoveryReport:
    """GLOSSARY_CONFLICT: Blocking; first occurrence canonical; flag rest."""
    return _emit(
        ctx_ambiguities,
        GlossaryConflict.code,
        Severity.BLOCKING,
        RecoveryAction.USE_FIRST_OCCURRENCE,
        f"First occurrence canonical ({canonical_target}); rest flagged for review.",
        source_term=term,
        add_to_ambiguities=True,
    )


def route_exception(
    exc: TRAException,
    ctx_ambiguities: list[str],
    *,
    critical_hierarchy_lost: bool = False,
    canonical_target: str | None = None,
) -> RecoveryReport:
    """Dispatch an exception to its spec-mandated recovery procedure."""
    if isinstance(exc, UnknownTerm):
        return recover_unknown_term(exc.term, ctx_ambiguities)
    if isinstance(exc, BrokenMarkdown):
        return recover_broken_markdown(
            exc.detail, critical_hierarchy_lost=critical_hierarchy_lost
        )
    if isinstance(exc, CertaintyConflict):
        return recover_certainty_conflict(exc.term, ctx_ambiguities)
    if isinstance(exc, EntityAmbiguity):
        return recover_entity_ambiguity(exc.token, ctx_ambiguities)
    if isinstance(exc, GlossaryConflict):
        return recover_glossary_conflict(
            exc.term, canonical_target or exc.canonical_target, ctx_ambiguities
        )
    # TRA-044: Unrecoverable must HALT with BLOCKING severity. Previously it
    # fell through to the generic WARNING + PRESERVE_SOURCE fallback, which
    # silently downgraded an unrecoverable failure — an L4 audit trail with
    # only an Unrecoverable would incorrectly report l3_conformant=True.
    # Spec §6 mandates UNRECOVERABLE halts the pipeline with BLOCKING.
    if isinstance(exc, Unrecoverable):
        return RecoveryReport(
            code=Unrecoverable.code,
            severity=Severity.BLOCKING,
            action=RecoveryAction.HALT,
            detail=str(exc)
            or "Unrecoverable: repair cannot proceed without "
            "violating a higher-priority policy.",
        )
    return _emit(
        ctx_ambiguities,
        exc.code,
        Severity.WARNING,
        RecoveryAction.PRESERVE_SOURCE,
        str(exc),
    )
