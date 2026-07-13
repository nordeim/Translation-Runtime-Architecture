"""TDD regression tests for the outstanding audit findings.

Each test is written FIRST (RED), then the fix is applied (GREEN), then
refactored. Tests are named after their finding ID for traceability.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from tra.config import BootstrapConfig
from tra.memory import ConformanceLevel

# =========================================================================
# TRA-014 — Path traversal protection on BootstrapConfig
# =========================================================================


def _base_cfg_kwargs(tmp_path: Path) -> dict[str, object]:
    """Minimal valid BootstrapConfig kwargs with paths under tmp_path."""
    return {
        "language_pair": "ZH -> EN",
        "domain": "test",
        "conformance_level": ConformanceLevel.L3_STRICT,
        "model_endpoint": "rule-based",
        "model_version": "test",
        "cache_directory": str(tmp_path / "cache"),
        "compilation_dir": str(tmp_path / "artifacts"),
        "audit_trace": str(tmp_path / "audit.jsonl"),
    }


class TestTRA014PathTraversal:
    """TRA-014: BootstrapConfig must reject paths that escape base_dir."""

    def test_rejects_relative_traversal_in_compilation_dir(
        self, tmp_path: Path
    ) -> None:
        cfg_kwargs = _base_cfg_kwargs(tmp_path)
        cfg_kwargs["compilation_dir"] = "../../escaped_output"
        with pytest.raises(ValidationError, match=r"(?i)escape|traversal|outside"):
            BootstrapConfig(**cfg_kwargs)

    def test_rejects_absolute_path_outside_base_dir(self, tmp_path: Path) -> None:
        cfg_kwargs = _base_cfg_kwargs(tmp_path)
        cfg_kwargs["compilation_dir"] = "/etc/evil"
        with pytest.raises(
            ValidationError, match=r"(?i)escape|traversal|outside|absolute"
        ):
            BootstrapConfig(**cfg_kwargs)

    def test_rejects_traversal_in_audit_trace(self, tmp_path: Path) -> None:
        cfg_kwargs = _base_cfg_kwargs(tmp_path)
        cfg_kwargs["audit_trace"] = "../../evil.jsonl"
        with pytest.raises(ValidationError, match=r"(?i)escape|traversal|outside"):
            BootstrapConfig(**cfg_kwargs)

    def test_rejects_traversal_in_cache_directory(self, tmp_path: Path) -> None:
        cfg_kwargs = _base_cfg_kwargs(tmp_path)
        cfg_kwargs["cache_directory"] = "../../evil_cache"
        with pytest.raises(ValidationError, match=r"(?i)escape|traversal|outside"):
            BootstrapConfig(**cfg_kwargs)

    def test_accepts_path_inside_base_dir(self, tmp_path: Path) -> None:
        """A path under base_dir must be accepted — no false positives."""
        cfg_kwargs = _base_cfg_kwargs(tmp_path)
        cfg_kwargs["base_dir"] = str(tmp_path)
        cfg_kwargs["compilation_dir"] = str(tmp_path / "artifacts")
        cfg = BootstrapConfig(**cfg_kwargs)
        assert cfg.compilation_dir == str(tmp_path / "artifacts")


# =========================================================================
# TRA-012 — _sanitize_input applied at every entry point (chokepoint)
# =========================================================================


class TestTRA012SanitizeChokepoint:
    """TRA-012: sanitization must be applied in analyze_document (the single
    chokepoint), not just in TRAKernel.run. This covers validate.py and
    benchmark.py which call analyze_document directly.
    """

    def test_analyze_document_strips_bidi_overrides(self) -> None:
        """analyze_document must strip bidi-override chars from the source
        before computing the input_hash, so the audit trail reflects the
        sanitized source.
        """
        from tra.diagnostics import AuditTrail
        from tra.isa import analyze_document
        from tra.memory import RuntimeContext

        bidi = "\u202e"  # right-to-left override
        source = f"# Heading\n\n成立 {bidi}evil{bidi}\n"
        ctx = RuntimeContext()
        audit = AuditTrail("/tmp/test_audit_tra012.jsonl")
        analyze_document(source, ctx, audit)
        # The structural map's text must NOT contain the bidi char.
        assert ctx.structural_map is not None

        # Walk all nodes and assert no bidi char survived.
        def _walk(nodes):
            for n in nodes:
                if n.text:
                    assert bidi not in n.text, (
                        f"bidi char survived in node {n.kind}: {n.text!r}"
                    )
                yield from _walk(n.children)

        list(_walk(ctx.structural_map.nodes))
        # The audit record's input_hash must be over the SANITIZED source.
        sanitized = source.replace(bidi, "")
        import hashlib

        expected_hash = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()[:16]
        records = audit._buffer
        assert records, "expected at least one audit record"
        assert records[0].input_hash == expected_hash, (
            f"input_hash={records[0].input_hash!r} != expected={expected_hash!r}; "
            "analyze_document is hashing the UNSANITIZED source"
        )

    def test_sanitize_input_is_public_utility(self) -> None:
        """sanitize_input must be importable from tra.utils (not a private
        function on the kernel)."""
        from tra.utils import sanitize_input  # noqa: F401

        bidi = "\u202e"
        assert sanitize_input(f"clean{bidi}text") == "cleantext"


# =========================================================================
# TRA-013 — Audit trail must be byte-reproducible across runs
# =========================================================================


class TestTRA013AuditReproducibility:
    """TRA-013: two runs of identical source must produce byte-identical
    audit_trace.jsonl and evidence_trace.jsonl. Non-determinism sources:
    uuid4 evidence IDs + datetime.now timestamps.
    """

    def test_audit_trace_byte_identical_across_runs(self, tmp_path: Path) -> None:
        import filecmp

        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        source = "# Advisory\n\n系统 成立 是 高度可信 的。\n"

        def _run(label: str) -> Path:
            cfg = BootstrapConfig.from_yaml(
                str(Path(__file__).resolve().parent.parent / "config.yaml")
            ).model_copy(
                update={
                    "base_dir": str(tmp_path),
                    "conformance_level": ConformanceLevel.L4_FORENSIC,
                    "audit_trace": str(tmp_path / label / "audit.jsonl"),
                    "compilation_dir": str(tmp_path / label / "artifacts"),
                    "cache_directory": str(tmp_path / label / "cache"),
                }
            )
            kernel = TRAKernel(cfg)
            kernel.run(source)
            return Path(cfg.audit_trace)

        trace1 = _run("run1")
        trace2 = _run("run2")
        assert filecmp.cmp(trace1, trace2, shallow=False), (
            "audit_trace.jsonl differs across runs — non-deterministic "
            "(uuid4 or datetime.now not fixed)"
        )

    def test_evidence_trace_byte_identical_across_runs(self, tmp_path: Path) -> None:
        import filecmp

        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        source = "# Advisory\n\n系统 成立 是 高度可信 的。\n"

        def _run(label: str) -> Path:
            cfg = BootstrapConfig.from_yaml(
                str(Path(__file__).resolve().parent.parent / "config.yaml")
            ).model_copy(
                update={
                    "base_dir": str(tmp_path),
                    "conformance_level": ConformanceLevel.L4_FORENSIC,
                    "audit_trace": str(tmp_path / label / "audit.jsonl"),
                    "compilation_dir": str(tmp_path / label / "artifacts"),
                    "cache_directory": str(tmp_path / label / "cache"),
                }
            )
            kernel = TRAKernel(cfg)
            kernel.run(source)
            return Path(cfg.compilation_dir) / "evidence_trace.jsonl"

        trace1 = _run("run1")
        trace2 = _run("run2")
        assert filecmp.cmp(trace1, trace2, shallow=False), (
            "evidence_trace.jsonl differs across runs — non-deterministic"
        )


# =========================================================================
# TRA-007 — Kernel transitions must fire AFTER ISA success, not before
# =========================================================================


class TestTRA007TransitionOrdering:
    """TRA-007: per CLAUDE.md:19 and Spec §2.1, state transitions are
    "triggered only by successful completion of ISA instructions". The
    kernel must NOT advance state before the ISA call returns.
    """

    def test_state_does_not_advance_on_analyze_failure(self, tmp_path: Path) -> None:
        """If analyze_document raises, the kernel state must remain at
        INITIALIZE_RUNTIME, not advance to ANALYZE_DOCUMENT."""
        import contextlib
        from unittest.mock import patch

        from tra.config import BootstrapConfig
        from tra.exceptions import BrokenMarkdown
        from tra.kernel import KernelState, TRAKernel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
            }
        )
        kernel = TRAKernel(cfg)
        # Monkeypatch analyze_document to raise BrokenMarkdown.
        with (
            patch("tra.kernel.analyze_document", side_effect=BrokenMarkdown("boom")),
            contextlib.suppress(BrokenMarkdown),
        ):
            kernel.run("# test\n")
        # State must NOT have advanced to ANALYZE_DOCUMENT.
        assert kernel.state == KernelState.INITIALIZE_RUNTIME, (
            f"state advanced to {kernel.state!r} before ISA completed — "
            "transitions must fire AFTER successful ISA completion (TRA-007)"
        )
        # execution_log must NOT contain ANALYZE_DOCUMENT.
        assert "ANALYZE_DOCUMENT" not in kernel.ctx.execution_log
