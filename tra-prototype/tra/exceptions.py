"""TRA exception hierarchy (Spec §6 TRA-EXCEPTIONS).

Each maps to a recovery procedure (tra/recovery.py). Engine code raises these;
the Kernel routes them to the EXCEPTION_HANDLER state. Subclasses carry the
minimum payload their recovery procedure needs (term, token, canonical target).

`message` stays the first positional arg for backward compatibility with
existing raise sites; structured payloads are keyword args.
"""

from __future__ import annotations


class TRAException(Exception):
    """Base class for all TRA runtime exceptions."""

    code: str = "TRA_ERROR"

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message or self.code


class UnknownTerm(TRAException):
    code = "UNKNOWN_TERM"

    def __init__(self, message: str = "", *, term: str = "") -> None:
        self.term = term
        super().__init__(message or f"UNKNOWN_TERM: {term!r} not in glossary/module")


class BrokenMarkdown(TRAException):
    code = "BROKEN_MARKDOWN"

    def __init__(self, message: str = "", *, detail: str = "") -> None:
        self.detail = detail or message
        super().__init__(message or f"BROKEN_MARKDOWN: {self.detail}")


class CertaintyConflict(TRAException):
    code = "CERTAINTY_CONFLICT"

    def __init__(self, message: str = "", *, term: str = "") -> None:
        self.term = term
        default = f"CERTAINTY_CONFLICT: hedging {term!r} vs target norms"
        super().__init__(message or default)


class EntityAmbiguity(TRAException):
    code = "ENTITY_AMBIGUITY"

    def __init__(self, message: str = "", *, token: str = "") -> None:
        self.token = token
        super().__init__(message or f"ENTITY_AMBIGUITY: {token!r} is entity or NL?")


class GlossaryConflict(TRAException):
    code = "GLOSSARY_CONFLICT"

    def __init__(
        self,
        message: str = "",
        *,
        term: str = "",
        canonical_target: str = "",
    ) -> None:
        self.term = term
        self.canonical_target = canonical_target
        super().__init__(message or f"GLOSSARY_CONFLICT: {term!r} conflicts")


class Unrecoverable(TRAException):
    """REPAIR_SEGMENT cannot resolve without violating a higher policy."""

    code = "UNRECOVERABLE"


class ConformanceFailure(TRAException):
    """Pipeline completed but the output fails the conformance gate.

    Raised by the Kernel when VERIFY_OUTPUT reports BLOCKING diagnostics
    after the repair loop exhausts its budget (Spec §8 / TRA-CONFORMANCE-
    GUIDE.md: "If [BLOCKING diagnostics are] present, certification is
    denied"). The translate CLI catches this and exits 1 so a non-conformant
    output is never silently published as "translated".
    """

    code = "CONFORMANCE_FAILURE"

    def __init__(self, message: str = "", *, blocking_count: int = 0) -> None:
        self.blocking_count = blocking_count
        default = (
            f"CONFORMANCE_FAILURE: {blocking_count} BLOCKING "
            f"diagnostic(s) remain after repair"
        )
        super().__init__(message or default)
