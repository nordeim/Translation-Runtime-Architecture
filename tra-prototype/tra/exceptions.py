"""TRA exception hierarchy (Spec §6 TRA-EXCEPTIONS).

Each maps to a recovery procedure. Engine code raises these; the Kernel
routes them to the EXCEPTION_HANDLER state.
"""

from __future__ import annotations


class TRAException(Exception):
    """Base class for all TRA runtime exceptions."""

    code: str = "TRA_ERROR"


class UnknownTerm(TRAException):
    code = "UNKNOWN_TERM"


class BrokenMarkdown(TRAException):
    code = "BROKEN_MARKDOWN"


class CertaintyConflict(TRAException):
    code = "CERTAINTY_CONFLICT"


class EntityAmbiguity(TRAException):
    code = "ENTITY_AMBIGUITY"


class GlossaryConflict(TRAException):
    code = "GLOSSARY_CONFLICT"


class Unrecoverable(TRAException):
    """REPAIR_SEGMENT cannot resolve without violating a higher policy."""

    code = "UNRECOVERABLE"
