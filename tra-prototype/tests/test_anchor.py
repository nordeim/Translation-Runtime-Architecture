"""Phase 1.1 tests: StructuralMapBuilder + AnchorRegistry (S-06)."""

from __future__ import annotations

from pathlib import Path

from tra.anchor import (
    AnchorRegistry,
    build_structural_map,
    generate_github_slug,
    rewrite_links,
)
from tra.memory import NodeKind

SAMPLE = """# System Setup

Intro paragraph with `code`.

## Sub Heading

- item one
- item two
  - nested

> a quote

| Col A | Col B |
| --- | --- |
| x | y |

```python
print("hi")
```

---

[link](#system-setup)
"""


def test_structural_map_node_count_is_positive_and_deterministic():
    sm1, _ = build_structural_map(SAMPLE)
    sm2, _ = build_structural_map(SAMPLE)
    # Invariant (ANALYZE_DOCUMENT): node count stable across parses.
    assert sm1.node_count == sm2.node_count
    assert sm1.node_count > 0


def test_structural_map_shapes_tables_and_lists():
    sm, _ = build_structural_map(SAMPLE)

    def kind_seq(nodes):
        return [n.kind for n in nodes]

    top = kind_seq(sm.nodes)
    assert NodeKind.HEADING in top
    assert NodeKind.CODE_BLOCK in top
    assert NodeKind.HR in top
    assert NodeKind.TABLE in top
    assert NodeKind.LIST in top
    assert NodeKind.BLOCKQUOTE in top

    table = next(n for n in sm.nodes if n.kind == NodeKind.TABLE)
    # table -> row -> cell (no double-nested rows).
    assert table.children and table.children[0].kind == NodeKind.TABLE_ROW
    assert table.children[0].children[0].kind == NodeKind.TABLE_CELL


def test_code_block_is_no_translate_zone():
    sm, _ = build_structural_map(SAMPLE)
    cb = next(n for n in sm.nodes if n.kind == NodeKind.CODE_BLOCK)
    assert cb.is_no_translate_zone is True
    assert cb.metadata.get("lang") == "python"


def test_headings_register_placeholders():
    sm, reg = build_structural_map(SAMPLE)
    headings = [n for n in sm.nodes if n.kind == NodeKind.HEADING]
    assert len(headings) == 2
    for h in headings:
        assert h.placeholder is not None
        assert h.placeholder in reg.map_original_to_placeholder.values()
        assert h.original_slug == generate_github_slug(h.text)


def test_anchor_registry_dedup_on_resolve():
    reg = AnchorRegistry()
    assert reg.resolve_slug("System Setup") == "system-setup"
    assert reg.resolve_slug("System Setup") == "system-setup-1"
    assert reg.resolve_slug("System Setup") == "system-setup-2"


def test_s06_link_rewrite_repoints_translated_heading():
    _, reg = build_structural_map(SAMPLE)
    ph = reg.map_original_slug_to_placeholder["system-setup"]
    reg.bind(ph, reg.resolve_slug("系统安装"))

    translated = (
        "# 系统安装\n\n"
        "See [setup notes](#system-setup).\n\n"
        "```python\n"
        "# code-block link must NOT be rewritten: [x](#system-setup)\n```\n\n"
        "[broken](#does-not-exist)\n"
    )
    out, broken = rewrite_links(translated, reg)
    assert "#系统安装" in out
    assert "[setup notes](#系统安装)" in out
    # code-block-internal link untouched
    assert "[x](#system-setup)" in out
    # broken link reported
    assert broken == ["does-not-exist"]
    # broken link left in place (not silently dropped)
    assert "[broken](#does-not-exist)" in out


def test_build_structural_map_accepts_path(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("# Title\n\nbody\n", encoding="utf-8")
    sm, _ = build_structural_map(p)
    assert sm.nodes[0].kind == NodeKind.HEADING
    assert sm.nodes[0].text == "Title"
