"""Shared utilities (Phase 1): slugify, entity extraction, markdown helpers."""

from __future__ import annotations

import re

from .anchor import generate_github_slug

__all__ = ["generate_github_slug", "extract_entities", "PRODUCT_RE", "VERSION_RE"]

PRODUCT_RE = re.compile(r"\b[A-Z][A-Za-z0-9]+(?:VMM|VM|DB|API|SDK)?\b")
VERSION_RE = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")


def extract_entities(text: str) -> list[str]:
    """Heuristic entity surface forms (Phase 1.2). Returns matched tokens.

    Default-to-Entity on ambiguity (ENTITY_AMBIGUITY exception) is applied by
    the ISA layer, not here.
    """
    found: list[str] = []
    found += VERSION_RE.findall(text)
    found += PRODUCT_RE.findall(text)
    return found
