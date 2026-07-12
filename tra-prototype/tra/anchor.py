"""Anchor & cross-reference resolution (ANCHOR_RESOLUTION.md).

Stub for Phase 1.1: AnchorRegistry + StructuralMapBuilder. The data model in
memory.py already carries the required fields (original_slug, placeholder,
is_no_translate_zone); this module will own the slugify and link-rewrite
logic when Phase 1 begins.
"""

from __future__ import annotations

import re
from pathlib import Path

from .memory import StructuralMap

_GITHUB_SLUG_RE = re.compile(r"[^\w\s-]")
_WS_RE = re.compile(r"\s+", re.UNICODE)


def generate_github_slug(text: str) -> str:
    """GitHub-style slugify: lowercase, trim, spaces -> '-' (Unicode-aware)."""
    lowered = text.strip().lower()
    lowered = _WS_RE.sub("-", lowered)
    return _GITHUB_SLUG_RE.sub("", lowered)


class AnchorRegistry:
    """Maps original heading -> slug -> placeholder token (Phase 1.1)."""

    def __init__(self) -> None:
        self.map_original_to_placeholder: dict[str, str] = {}
        self.map_placeholder_to_translated_slug: dict[str, str] = {}
        self._counter = 0
        self._existing_slugs: set[str] = set()

    def register(self, text: str) -> str:
        placeholder = f"__HEADER_{self._counter:03d}__"
        self.map_original_to_placeholder[text] = placeholder
        self._counter += 1
        return placeholder

    def resolve_slug(self, translated_text: str) -> str:
        base = generate_github_slug(translated_text)
        if base not in self._existing_slugs:
            self._existing_slugs.add(base)
            return base
        counter = 1
        while f"{base}-{counter}" in self._existing_slugs:
            counter += 1
        final = f"{base}-{counter}"
        self._existing_slugs.add(final)
        return final


def build_structural_map(markdown_path: str | Path) -> StructuralMap:
    """Placeholder for Phase 1.1 markdown-it-py AST traversal.

    Returns an empty StructuralMap until the tokenizer walk is wired in.
    """
    _ = Path(markdown_path)  # consumed by real implementation in Phase 1.1
    return StructuralMap(nodes=[])
