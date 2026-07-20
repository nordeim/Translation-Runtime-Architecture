"""Phase 3 Cycle 6 — TRA-071: BrokenMarkdown reachability.

TRA-071: markdown-it-py is too lenient to raise on any normal input. The
only way to trigger BrokenMarkdown was to feed input that causes
build_structural_map to raise an Exception, which markdown-it-py essentially
never does. The BrokenMarkdown recovery procedure was effectively dead.

This test verifies that analyze_document now performs a structural
validation pass that raises BrokenMarkdown for spec-defined malformed cases
(unclosed fenced code blocks).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tra.diagnostics import AuditTrail
from tra.exceptions import BrokenMarkdown
from tra.isa import analyze_document
from tra.memory import RuntimeContext


def test_unclosed_code_fence_raises_broken_markdown(tmp_path: Path) -> None:
    """TRA-071: an unclosed fenced code block must raise BrokenMarkdown,
    not be silently parsed leniently by markdown-it-py."""
    ctx = RuntimeContext()
    # TRA-D7-008 (round 7): use tmp_path instead of hardcoded /tmp/test_tra071.jsonl
    audit = AuditTrail(str(tmp_path / "test_tra071.jsonl"))
    # Source with an unclosed code fence — markdown-it-py parses this
    # leniently (treats the rest of the doc as code), but the TRA spec
    # requires BrokenMarkdown for malformed structure.
    source = "# Test\n\n```python\ndef foo():\n    pass\n"
    with pytest.raises(BrokenMarkdown, match=r"unclosed|fence|malformed"):
        analyze_document(source, ctx, audit)


def test_closed_code_fence_does_not_raise(tmp_path: Path) -> None:
    """TRA-071: a properly closed code fence must NOT raise BrokenMarkdown."""
    ctx = RuntimeContext()
    # TRA-D7-008 (round 7): use tmp_path instead of hardcoded /tmp/test_tra071_ok.jsonl
    audit = AuditTrail(str(tmp_path / "test_tra071_ok.jsonl"))
    source = "# Test\n\n```python\ndef foo():\n    pass\n```\n"
    # Must not raise.
    profile, smap = analyze_document(source, ctx, audit)
    assert profile is not None
    assert smap is not None
