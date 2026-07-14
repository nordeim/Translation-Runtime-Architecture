"""Anchor & cross-reference resolution + structural map builder.

Implements Phase 1.1 of the implementation plan (ANCHOR_RESOLUTION.md /
Spec §4 `structural_map`). The data model in `memory.py` carries the required
fields (`original_slug`, `placeholder`, `is_no_translate_zone`); this module
owns the markdown-it-py AST traversal that populates them.

Design notes:
- `StructuralMapBuilder.build()` walks the markdown-it-py token stream into a
  `StructuralNode` tree. The node count MUST equal the source's structural node
  count (ANALYZE_DOCUMENT invariant, TRA-ISA-REFERENCE.md), so every emitted
  node — including empty `list`/`table` wrappers and `hr` — is counted.
- Headings are registered with the `AnchorRegistry` so the post-translation
  link-rewrite pass (S-06) can repoint `[text](#slug)` at the translated slug.
- Code blocks and inline code are marked `is_no_translate_zone = True`; the
  link-rewrite pass skips links found inside them (S-06: code-block-internal
  links are not rewritten).
"""

from __future__ import annotations

import re
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .memory import (
    NodeKind,
    StructuralMap,
    StructuralNode,
)

_GITHUB_SLUG_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_WS_RE = re.compile(r"\s+", re.UNICODE)

_HEADING_TAG_RE = re.compile(r"h(\d)")


def generate_github_slug(text: str) -> str:
    """GitHub-style slugify: lowercase, trim, spaces -> '-' (Unicode-aware)."""
    lowered = text.strip().lower()
    lowered = _WS_RE.sub("-", lowered)
    return _GITHUB_SLUG_RE.sub("", lowered)


class AnchorRegistry:
    """Maps original heading -> slug -> placeholder token (Phase 1.1 / S-06).

    Two responsibilities:
    1. Assign each heading a stable `__HEADER_N__` placeholder used to shield
       heading text from the translator (so the translator never mangles a slug
       source mid-sentence).
    2. Resolve a translated heading's slug, de-duplicating collisions
       (`system-setup` -> `system-setup-1`) so cross-references stay unique.
    """

    def __init__(self) -> None:
        self.map_original_to_placeholder: dict[str, str] = {}
        self.map_original_slug_to_placeholder: dict[str, str] = {}
        self.map_placeholder_to_translated_slug: dict[str, str] = {}
        self._counter = 0
        self._existing_slugs: set[str] = set()

    def register(self, text: str) -> str:
        """Reserve a placeholder for an original heading; returns the token."""
        placeholder = f"__HEADER_{self._counter:03d}__"
        self.map_original_to_placeholder[text] = placeholder
        self.map_original_slug_to_placeholder[generate_github_slug(text)] = placeholder
        self._counter += 1
        return placeholder

    def resolve_slug(self, translated_text: str) -> str:
        """Resolve the slug for a (translated) heading, de-duplicating."""
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

    def bind(self, placeholder: str, translated_slug: str) -> None:
        """Record the translated slug chosen for a placeholder (post-translation)."""
        self.map_placeholder_to_translated_slug[placeholder] = translated_slug

    def translated_slug_for(self, original_slug: str) -> str | None:
        """Resolve the translated slug for an original heading slug (S-06).

        Returns None if the original slug was never a heading (broken link).
        """
        placeholder = self.map_original_slug_to_placeholder.get(original_slug)
        if placeholder is None:
            return None
        return self.map_placeholder_to_translated_slug.get(placeholder)

    def is_translated_slug(self, slug: str) -> bool:
        """Check if `slug` is already a translated slug value (TRA-093).

        After whole-doc translation, a link target may already be the
        translated slug (e.g. '#the-system-is-confirmed') rather than the
        original CJK slug. rewrite_links must recognize such slugs as
        valid (not broken) to avoid false-positive BROKEN_LINK diagnostics.
        """
        return slug in self.map_placeholder_to_translated_slug.values()


def rewrite_links(
    markdown: str,
    registry: AnchorRegistry,
    *,
    flag_broken: bool = True,
) -> tuple[str, list[str]]:
    """Repoint internal `[text](#slug)` links at translated slugs (S-06).

    - Links that target a known heading are rewritten to the heading's
      translated slug.
    - Links inside fenced code blocks are left untouched (S-06: code-block
      internal links are not rewritten).
    - Links targeting an unknown slug are left as-is and reported (WARNING).

    Returns (rewritten_markdown, broken_slug_list).
    """
    _LINK_RE = re.compile(r"(\[[^\]]*\])\(#([^)\s]+)\)")
    _FENCE_OPEN_RE = re.compile(r"^\s*```")
    _FENCE_CLOSE_RE = re.compile(r"^\s*```\s*$")

    out_lines: list[str] = []
    broken: list[str] = []
    in_fence = False
    for line in markdown.split("\n"):
        if in_fence:
            # A closing fence line also matches the open regex; treat it as
            # a close so we don't re-open a phantom fence (S-06: code-block
            # internal links must stay untouched).
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
            else:
                out_lines.append(line)
            continue
        if _FENCE_OPEN_RE.match(line):
            in_fence = True
            out_lines.append(line)
            continue

        def _sub(m: re.Match[str]) -> str:
            text, slug = m.group(1), m.group(2)
            new_slug = registry.translated_slug_for(slug)
            if new_slug is None:
                # TRA-093: if the slug is already a translated slug value
                # (e.g. after whole-doc translation the link target was
                # translated in-place), it is NOT broken — leave it as-is.
                if registry.is_translated_slug(slug):
                    return m.group(0)
                if flag_broken and slug not in broken:
                    broken.append(slug)
                return m.group(0)
            return f"{text}(#{new_slug})"

        out_lines.append(_LINK_RE.sub(_sub, line))
    return "\n".join(out_lines), broken


class StructuralMapBuilder:
    """Walks a markdown-it-py token stream into a `StructuralNode` tree.

    Usage:
        builder = StructuralMapBuilder(MarkdownIt().enable("table"))
        smap, registry = builder.build(markdown_text)
    """

    def __init__(self, parser: MarkdownIt | None = None) -> None:
        self._md = parser or MarkdownIt().enable("table")

    def build(self, source: str | Path) -> tuple[StructuralMap, AnchorRegistry]:
        """Parse `source` and return (StructuralMap, AnchorRegistry)."""
        if isinstance(source, Path):
            source = source.read_text(encoding="utf-8")
        self._registry = AnchorRegistry()
        tokens = self._md.parse(source)
        self._tokens = tokens
        self._pos = 0
        root_nodes = self._walk_top_level()
        return StructuralMap(nodes=root_nodes), self._registry

    # --- token-stream walker -------------------------------------------------

    def _peek(self) -> Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _next(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _walk_top_level(self) -> list[StructuralNode]:
        nodes: list[StructuralNode] = []
        while self._pos < len(self._tokens):
            node = self._consume_top()
            if node is not None:
                nodes.append(node)
        return nodes

    def _consume_top(self) -> StructuralNode | None:
        tok = self._peek()
        if tok is None:
            return None
        ttype = tok.type
        if ttype == "heading_open":
            return self._consume_heading(tok)
        if ttype == "paragraph_open":
            return self._consume_paragraph()
        if ttype in ("bullet_list_open", "ordered_list_open"):
            return self._consume_list(tok)
        if ttype == "blockquote_open":
            return self._consume_blockquote()
        if ttype == "table_open":
            return self._consume_table()
        if ttype == "fence":
            return self._consume_fence(tok)
        if ttype == "hr":
            self._next()
            return StructuralNode(kind=NodeKind.HR)
        # Skip anything else (e.g., stray inline close tokens at top level).
        self._next()
        return None

    def _consume_heading(self, open_tok: Token) -> StructuralNode:
        self._next()  # heading_open
        inline = self._next()  # inline
        text = inline.content or ""
        m = _HEADING_TAG_RE.search(open_tok.tag or "")
        level = int(m.group(1)) if m else 1
        placeholder = self._registry.register(text)
        self._next()  # heading_close
        return StructuralNode(
            kind=NodeKind.HEADING,
            level=level,
            text=text,
            placeholder=placeholder,
            original_slug=generate_github_slug(text),
        )

    def _consume_paragraph(self) -> StructuralNode:
        self._next()  # paragraph_open
        inline = self._next()  # inline
        text = inline.content or ""
        self._next()  # paragraph_close
        return StructuralNode(kind=NodeKind.PARAGRAPH, text=text)

    def _consume_list(self, open_tok: Token) -> StructuralNode:
        self._next()  # list_open
        children: list[StructuralNode] = []
        while True:
            tok = self._peek()
            if tok is None or tok.type in ("bullet_list_close", "ordered_list_close"):
                break
            if tok.type == "list_item_open":
                children.append(self._consume_list_item())
            else:
                # Unexpected token inside list; advance to avoid infinite loop.
                self._next()
        if self._peek() is not None:
            self._next()  # list_close
        return StructuralNode(
            kind=NodeKind.LIST,
            level=open_tok.level,
            children=children,
        )

    def _consume_list_item(self) -> StructuralNode:
        self._next()  # list_item_open
        children: list[StructuralNode] = []
        while True:
            tok = self._peek()
            close = ("list_item_close", "bullet_list_close", "ordered_list_close")
            if tok is None or tok.type in close:
                break
            if tok.type == "paragraph_open":
                children.append(self._consume_paragraph())
            elif tok.type in ("bullet_list_open", "ordered_list_open"):
                children.append(self._consume_list(tok))
            elif tok.type == "blockquote_open":
                children.append(self._consume_blockquote())
            elif tok.type == "heading_open":
                children.append(self._consume_heading(tok))
            elif tok.type == "table_open":
                children.append(self._consume_table())
            else:
                self._next()
        peek = self._peek()
        if peek is not None and peek.type == "list_item_close":
            self._next()  # list_item_close
        kind = NodeKind.LIST_ITEM
        # A list item's first child paragraph carries its text.
        text = (
            children[0].text
            if (children and children[0].kind == NodeKind.PARAGRAPH)
            else None
        )
        return StructuralNode(kind=kind, text=text, children=children)

    def _consume_blockquote(self) -> StructuralNode:
        self._next()  # blockquote_open
        children: list[StructuralNode] = []
        while True:
            tok = self._peek()
            if tok is None or tok.type == "blockquote_close":
                break
            if tok.type == "paragraph_open":
                children.append(self._consume_paragraph())
            elif tok.type == "heading_open":
                children.append(self._consume_heading(tok))
            elif tok.type in ("bullet_list_open", "ordered_list_open"):
                children.append(self._consume_list(tok))
            elif tok.type == "blockquote_open":
                children.append(self._consume_blockquote())
            else:
                self._next()
        if self._peek() is not None:
            self._next()  # blockquote_close
        return StructuralNode(kind=NodeKind.BLOCKQUOTE, children=children)

    def _consume_table(self) -> StructuralNode:
        self._next()  # table_open
        # Flatten thead/tbody wrappers: rows attach directly to the table so
        # the shape is table -> row -> cell (NodeKind has no section node).
        children: list[StructuralNode] = []
        while True:
            tok = self._peek()
            if tok is None or tok.type == "table_close":
                break
            if tok.type in ("thead_open", "tbody_open"):
                self._next()
                while True:
                    inner = self._peek()
                    if inner is None or inner.type in ("thead_close", "tbody_close"):
                        break
                    if inner.type == "tr_open":
                        children.append(self._consume_table_row())
                    else:
                        self._next()
                if self._peek() is not None:
                    self._next()  # thead/tbody close
            elif tok.type == "tr_open":
                children.append(self._consume_table_row())
            else:
                self._next()
        if self._peek() is not None:
            self._next()  # table_close
        return StructuralNode(kind=NodeKind.TABLE, children=children)

    def _consume_table_row(self) -> StructuralNode:
        self._next()  # tr_open
        children: list[StructuralNode] = []
        while True:
            tok = self._peek()
            if tok is None or tok.type == "tr_close":
                break
            if tok.type in ("th_open", "td_open"):
                node = self._consume_table_cell()
                if node is not None:
                    children.append(node)
            else:
                self._next()
        if self._peek() is not None:
            self._next()  # tr_close
        return StructuralNode(kind=NodeKind.TABLE_ROW, children=children)

    def _consume_table_cell(self) -> StructuralNode | None:
        self._next()  # th_open / td_open
        inline = self._peek()
        text = inline.content if inline is not None and inline.type == "inline" else ""
        if inline is not None and inline.type == "inline":
            self._next()
        peek = self._peek()
        if peek is not None and peek.type in ("th_close", "td_close"):
            self._next()  # close
        return StructuralNode(kind=NodeKind.TABLE_CELL, text=text)

    def _consume_fence(self, tok: Token) -> StructuralNode:
        self._next()  # fence
        lang = (tok.info or "").strip() or None
        return StructuralNode(
            kind=NodeKind.CODE_BLOCK,
            text=tok.content or "",
            is_no_translate_zone=True,
            metadata={"lang": lang} if lang else {},
        )


def build_structural_map(
    source: str | Path, parser: MarkdownIt | None = None
) -> tuple[StructuralMap, AnchorRegistry]:
    """Convenience entry point (replaces the Phase 0 stub)."""
    return StructuralMapBuilder(parser).build(source)
