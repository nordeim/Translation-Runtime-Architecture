"""Shared utilities (Phase 1): slugify, entity extraction, markdown helpers."""

from __future__ import annotations

import re

from .anchor import generate_github_slug
from .memory import Entity, EntityType

__all__ = [
    "generate_github_slug",
    "extract_entities",
    "classify_entity",
    "PRODUCT_RE",
    "VERSION_RE",
    "ACRONYM_RE",
    "CLI_RE",
]

# PascalCase/camelCase product-ish tokens, optionally ending in a known
# entity suffix (VMM, VM, DB, API, SDK).
PRODUCT_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:VMM|VM|DB|API|SDK)?\b")

# Semantic-version strings: optional 'v' prefix, 2+ dot-separated ints.
VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")

# Acronym: 2-5 uppercase letters (optionally with digits), standalone.
ACRONYM_RE = re.compile(r"\b[A-Z]{2,5}\b")

# CLI surface: long flags (--foo), or backticked tokens.
CLI_RE = re.compile(r"(?:--[a-z][a-z0-9-]*|`[^`\s]+`)")

# A "plain word" is a single capitalized word with no internal case
# transition, digit, or known-suffix signal — these are normal prose, not
# product entities, and must be dropped by extract_entities.
_PLAIN_WORD_RE = re.compile(r"^[A-Z][a-z]{2,}$")
# A product-ish token must carry at least one of: a digit, an internal
# camelCase transition, or a known entity suffix.
_PRODUCT_SIGNAL_RE = re.compile(r"(?:\d|[a-z][A-Z]|VMM|VM|DB|API|SDK|Kit|Engine)")


def classify_entity(token: str) -> EntityType:
    """Best-effort type guess for a candidate entity token.

    Used to pre-populate `Entity.type`; the ISA layer (BUILD_ENTITY_TABLE)
    may override. Ambiguity is resolved by defaulting to Entity (immutable),
    per the ENTITY_AMBIGUITY exception — that policy lives in the ISA layer,
    not here.
    """
    if VERSION_RE.fullmatch(token):
        return EntityType.VERSION
    if ACRONYM_RE.fullmatch(token) and not _PLAIN_WORD_RE.match(token):
        return EntityType.ACRONYM
    if token.startswith("--") or (
        token.startswith("`") and token.endswith("`") and len(token) > 2
    ):
        return EntityType.CLI
    return EntityType.PRODUCT


def _is_product_entity(token: str) -> bool:
    """Reject plain Capitalized prose words that PRODUCT_RE over-matches."""
    return bool(_PRODUCT_SIGNAL_RE.search(token))


def extract_entities(text: str) -> list[Entity]:
    """Surface entity candidates from a text span as immutable `Entity` objects.

    Heuristic only: returns tokens matching product/version/acronym/CLI
    patterns, classified by `classify_entity`, de-duplicated and order-preserving.
    Every candidate is created with `mutable=False` (entities are never
    translated); the ISA layer decides final inclusion.

    Note: this does NOT consume markdown structure. For document-wide
    extraction over a `StructuralMap`, call once per leaf node so code-block
    zones (marked `is_no_translate_zone`) can be skipped by the caller.
    """
    found: list[str] = []
    seen: set[str] = set()
    for pat in (VERSION_RE, PRODUCT_RE, ACRONYM_RE, CLI_RE):
        for m in pat.finditer(text):
            tok = m.group(0).strip("`")
            if not tok or tok in seen:
                continue
            # PRODUCT_RE over-matches plain prose words; drop those.
            if pat is PRODUCT_RE and not _is_product_entity(tok):
                continue
            seen.add(tok)
            found.append(tok)
    return [Entity(name=t, type=classify_entity(t)) for t in found]
