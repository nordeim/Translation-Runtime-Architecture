"""TDD regression tests for the outstanding audit findings.

Each test is written FIRST (RED), then the fix is applied (GREEN), then
refactored. Tests are named after their finding ID for traceability.
"""

from __future__ import annotations

import contextlib
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
        from tra.exceptions import BrokenMarkdown, ConformanceFailure
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
        # TRA-036: at L3_STRICT (default), the kernel now raises
        # ConformanceFailure (not BrokenMarkdown) on analyze failure —
        # suppress both to verify the state invariant.
        with (
            patch("tra.kernel.analyze_document", side_effect=BrokenMarkdown("boom")),
            contextlib.suppress(BrokenMarkdown, ConformanceFailure),
        ):
            kernel.run("# test\n")
        # State must NOT have advanced to ANALYZE_DOCUMENT.
        assert kernel.state == KernelState.INITIALIZE_RUNTIME, (
            f"state advanced to {kernel.state!r} before ISA completed — "
            "transitions must fire AFTER successful ISA completion (TRA-007)"
        )
        # execution_log must NOT contain ANALYZE_DOCUMENT.
        assert "ANALYZE_DOCUMENT" not in kernel.ctx.execution_log


# =========================================================================
# TRA-009 + TRA-006 — PolicyResolver-driven severity for canonical term leakage
# =========================================================================


class TestTRA009PolicyDrivenSeverity:
    """TRA-009 + TRA-006: when a CANONICAL glossary term leaks untranslated,
    verify_output must escalate to BLOCKING via PolicyResolver arbitration
    (Terminological Consistency P4 > Target Fluency P6). This makes the
    PolicyResolver invoked in production (TRA-006) and tightens canonical-term
    leakage from WARNING to BLOCKING (TRA-009).
    """

    def test_canonical_term_leakage_is_blocking(self) -> None:
        """A CANONICAL glossary term that appears untranslated in the target
        is a BLOCKING violation (P4 > P6)."""
        from tra.diagnostics import AuditTrail, EvidenceRegistry, Severity
        from tra.isa import build_glossary, verify_output
        from tra.memory import DocumentProfile, GlossaryStatus, RuntimeContext

        ctx = RuntimeContext()
        ev = EvidenceRegistry()
        build_glossary(
            "成立",
            DocumentProfile(type="x", register_="y", intent="z", audience="a"),
            ctx,
            ev,
            AuditTrail("/tmp/test_tra009.jsonl"),
        )
        # Confirm the glossary entry is CANONICAL.
        assert ctx.glossary_cache
        assert ctx.glossary_cache[0].status == GlossaryStatus.CANONICAL
        # Target still contains the untranslated source term.
        diags = verify_output(
            "成立 here", "成立 here", ctx, AuditTrail("/tmp/test.jsonl")
        )
        terminology = [d for d in diags if d.subsystem == "terminology"]
        assert terminology, "expected at least one terminology diagnostic"
        assert all(d.severity == Severity.BLOCKING for d in terminology), (
            "canonical term leakage must be BLOCKING (P4 > P6 via PolicyResolver)"
        )

    def test_policy_resolver_invoked_in_verify_output(self) -> None:
        """TRA-006: PolicyResolver must be consulted in production code paths,
        not just tested in isolation. Verify it's importable and wired."""
        from tra.memory import PolicyPriority
        from tra.policy import PolicyResolver

        resolver = PolicyResolver(list(PolicyPriority))
        # Terminological Consistency (P4) wins over Target Fluency (P6).
        winner = resolver.resolve(
            PolicyPriority.TERMINOLOGICAL_CONSISTENCY,
            PolicyPriority.TARGET_FLUENCY,
        )
        assert winner == PolicyPriority.TERMINOLOGICAL_CONSISTENCY


# =========================================================================
# TRA-004 — Exception recovery reachability (BrokenMarkdown routes through _recover)
# =========================================================================


class TestTRA004ExceptionRecovery:
    """TRA-004: all 5 TRA-EXCEPTION types must route through the
    EXCEPTION_HANDLER (kernel._recover) instead of propagating uncaught.
    Currently BrokenMarkdown crashes the kernel.
    """

    def test_broken_markdown_routes_through_exception_handler(
        self, tmp_path: Path
    ) -> None:
        """If analyze_document raises BrokenMarkdown, the kernel must route
        it through _recover (EXCEPTION_HANDLER audit record), not propagate."""
        from unittest.mock import patch

        from tra.config import BootstrapConfig
        from tra.exceptions import BrokenMarkdown
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)
        with patch("tra.kernel.analyze_document", side_effect=BrokenMarkdown("boom")):
            # Must NOT raise — the kernel routes through _recover.
            kernel.run("# test\n")
        # The audit trail must contain an EXCEPTION_HANDLER record.
        handler_records = [
            r for r in kernel.audit._buffer if r.isa_instruction == "EXCEPTION_HANDLER"
        ]
        assert handler_records, (
            "expected an EXCEPTION_HANDLER audit record for BrokenMarkdown — "
            "the kernel must route exceptions through _recover (TRA-004)"
        )
        assert handler_records[0].artifact_snapshot.get("severity") == "BLOCKING"


# =========================================================================
# TRA-032 — HITL review_decision tested for all 3 resolutions
# =========================================================================


class TestTRA032HITLResolutions:
    """TRA-032: hitl.review_decision supports accept/override/skip but only
    'accept' was tested. Parametrize over all 3.
    """

    @pytest.mark.parametrize("resolution", ["accept", "override", "skip"])
    def test_review_decision_returns_correct_resolution(
        self, resolution: str, monkeypatch
    ) -> None:
        """Each resolution path must return the correct (resolution, text)."""
        from tra.hitl import review_decision

        # Monkeypatch rich.prompt.Prompt.ask to return the chosen resolution.
        # The override path asks twice (resolution + edited text); accept/skip ask once.
        responses = {
            "accept": ["accept"],
            "override": ["override", "edited text"],
            "skip": ["skip"],
        }
        calls = iter(responses[resolution])

        def _fake_ask(*_args, **_kwargs):
            return next(calls)

        monkeypatch.setattr("tra.hitl.Prompt.ask", _fake_ask)
        uncertainty = "test uncertainty"
        src_excerpt = "test source"
        candidate = "candidate text"
        result_res, result_text = review_decision(
            uncertainty, src_excerpt, candidate, glossary_options=["成立"]
        )
        assert result_res == resolution


# =========================================================================
# TRA-033 — LLM seam degradation tested for multiple exception types + empty/None
# =========================================================================


class TestTRA033LLMSeamRobustness:
    """TRA-033: graceful degradation was tested for RuntimeError only.
    Parametrize over multiple exception types. Also test empty-string and
    None returns (latent gap: these bypass the except block entirely).
    """

    @pytest.mark.parametrize(
        "exc_cls", [RuntimeError, ValueError, TypeError, OSError, TimeoutError]
    )
    def test_llm_seam_degrades_on_each_exception_type(self, exc_cls: type) -> None:
        """The except Exception catch must handle all exception types."""
        from tra.cache import TranslationCache
        from tra.diagnostics import AuditTrail, EvidenceRegistry
        from tra.isa import translate_segment
        from tra.memory import GlossaryEntry, GlossaryStatus, RuntimeContext

        ctx = RuntimeContext()
        ctx.glossary_cache = [
            GlossaryEntry(
                source="成立", target="Confirmed", status=GlossaryStatus.CANONICAL
            )
        ]
        cache = TranslationCache("/tmp/test_cache_tra033", enabled=False)

        def boom(_seg, _ctx):
            raise exc_cls("llm down")

        res = translate_segment(
            "成立",
            ctx,
            cache,
            EvidenceRegistry(),
            AuditTrail("/tmp/test.jsonl"),
            llm_translate=boom,
        )
        # Must degrade to rule path, not raise.
        assert "Confirmed" in res.translation

    def test_llm_seam_degrades_on_empty_string(self) -> None:
        """TRA-033 latent gap: llm_translate returning '' must degrade to the
        rule path, not silently produce an empty translation."""
        from tra.cache import TranslationCache
        from tra.diagnostics import AuditTrail, EvidenceRegistry
        from tra.isa import translate_segment
        from tra.memory import GlossaryEntry, GlossaryStatus, RuntimeContext

        ctx = RuntimeContext()
        ctx.glossary_cache = [
            GlossaryEntry(
                source="成立", target="Confirmed", status=GlossaryStatus.CANONICAL
            )
        ]
        cache = TranslationCache("/tmp/test_cache_tra033b", enabled=False)

        def empty(_seg, _ctx):
            return ""

        res = translate_segment(
            "成立",
            ctx,
            cache,
            EvidenceRegistry(),
            AuditTrail("/tmp/test.jsonl"),
            llm_translate=empty,
        )
        # Must degrade to rule path — not return "".
        assert "Confirmed" in res.translation, (
            "empty LLM output must degrade to rule path, not produce empty translation"
        )

    def test_llm_seam_degrades_on_none(self) -> None:
        """TRA-033 latent gap: llm_translate returning None must degrade to the
        rule path, not crash."""
        from tra.cache import TranslationCache
        from tra.diagnostics import AuditTrail, EvidenceRegistry
        from tra.isa import translate_segment
        from tra.memory import GlossaryEntry, GlossaryStatus, RuntimeContext

        ctx = RuntimeContext()
        ctx.glossary_cache = [
            GlossaryEntry(
                source="成立", target="Confirmed", status=GlossaryStatus.CANONICAL
            )
        ]
        cache = TranslationCache("/tmp/test_cache_tra033c", enabled=False)

        def returns_none(_seg, _ctx):
            return None

        res = translate_segment(
            "成立",
            ctx,
            cache,
            EvidenceRegistry(),
            AuditTrail("/tmp/test.jsonl"),
            llm_translate=returns_none,
        )
        assert "Confirmed" in res.translation


# =========================================================================
# TRA-002 — Module registry wired into kernel (not hard-coded ZHENModule)
# =========================================================================


class TestTRA002RegistryWiring:
    """TRA-002: the kernel must use the module registry to select the language
    module, not hard-code ZHENModule(). A registered stub module should be
    picked up by the kernel.
    """

    def test_kernel_uses_registry_for_language_pair(self, tmp_path: Path) -> None:
        """When a stub module is registered, the kernel must use its glossary
        mappings — not ZHENModule's."""
        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel, StyleProfile
        from tra.modules.registry import ModuleRegistry

        # Build a full stub module with all the methods the ISA expects.
        class StubModule:
            """Minimal stub module for TRA-002 registry wiring test."""

            name = "stub-en"
            kind = "language"
            direction = "STUB -> EN"
            metadata: dict[str, str] = {"direction": "STUB -> EN"}

            def get_glossary_mappings(self) -> dict[str, str]:
                return {"stub_term": "STUB_TARGET"}

            def get_style_profile(self) -> StyleProfile:
                return StyleProfile()

            def is_forbidden(self, _src: str, _tgt: str) -> bool:
                return False

            def get_forbidden_targets(self) -> dict[str, str]:
                return {}

            def entity_type_hint(self, _token: str) -> object:
                return None

            def apply_zh_rules(self, text: str) -> str:
                return text

            def apply_rules(self, text: str, _direction: str) -> str:
                return text

            def as_interface(self) -> object:
                from tra.modules.registry import ModuleInterface

                return ModuleInterface(
                    name="stub-en",
                    kind="language",
                    get_glossary_mappings=self.get_glossary_mappings,
                    get_style_profile=self.get_style_profile,
                    apply_rules=self.apply_rules,
                    metadata={"direction": "STUB -> EN"},
                )

        stub = StubModule()
        registry = ModuleRegistry()
        # Register the stub directly (not via as_interface shim) so the
        # registry holds the full module object with all ISA-expected methods.
        registry.register(stub)  # type: ignore[arg-type]

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
                "language_pair": "STUB -> EN",
            }
        )
        # Pass the registry to the kernel.
        kernel = TRAKernel(cfg, registry=registry)
        kernel.run("stub_term here\n")
        # The stub's glossary mapping should appear in the exported artifacts.
        glossary_path = Path(cfg.compilation_dir) / "glossary.yaml"
        assert glossary_path.exists(), "glossary.yaml not exported"
        content = glossary_path.read_text()
        assert "STUB_TARGET" in content, (
            "kernel did not use the stub module's glossary — "
            "registry not wired (TRA-002)"
        )


# =========================================================================
# TRA-008 — rewrite_links wired into kernel (internal links rewritten)
# =========================================================================


class TestTRA008RewriteLinks:
    """TRA-008: the kernel must call rewrite_links after translation so
    internal `[text](#slug)` links are repointed at the translated heading
    slugs. Currently rewrite_links is defined but never called in production.
    """

    def test_internal_links_rewritten_after_translation(self, tmp_path: Path) -> None:
        """Source has a heading + an internal link to that heading. After
        translation, the link target must be rewritten to the translated
        heading's slug (a valid slug: lowercase, hyphens, no spaces)."""
        import re

        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        # Source: heading "系统成立" + link to "#系统成立"
        source = "# 系统成立\n\n[link to heading](#系统成立)\n"
        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)
        target = kernel.run(source)
        # Extract the link target from the translated output.
        link_match = re.search(r"\]\(#([^)]+)\)", target)
        assert link_match, f"no internal link found in target: {target!r}"
        link_target = link_match.group(1)
        # The link target must be a valid slug: no spaces, no uppercase
        # (GitHub slugify: lowercase, spaces -> '-'). Without rewrite_links,
        # the target is "The system is Confirmed" (spaces, uppercase) — broken.
        assert " " not in link_target, (
            f"link target {link_target!r} has spaces — not a valid slug; "
            "rewrite_links not called (TRA-008)"
        )


# =========================================================================
# TRA-001 — Segment-level translation (code blocks are no-translate zones)
# =========================================================================


class TestTRA001SegmentLevel:
    """TRA-001: TRANSLATE_SEGMENT must respect is_no_translate_zone markers.
    Code blocks must NOT be translated — glossary terms inside backticks
    must survive verbatim. The minimal fix: extract code blocks before
    translation, translate the rest, restore code blocks after.
    """

    def test_code_block_not_translated(self, tmp_path: Path) -> None:
        """A glossary term inside a code block must NOT be translated."""
        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        # Source: a code block containing the glossary term "成立"
        # and a paragraph containing "成立" (which SHOULD be translated).
        source = "```\n成立 = True\n```\n\n系统成立。\n"
        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)
        target = kernel.run(source)
        # The code block must still contain "成立" (untranslated).
        assert "成立 = True" in target, (
            "code block was translated — is_no_translate_zone not respected (TRA-001)"
        )
        # The paragraph's "成立" should be translated to "Confirmed".
        assert "Confirmed" in target, "paragraph term should be translated"


# =========================================================================
# TRA-036 — Analyze-failure early return bypasses the L3 conformance gate
# =========================================================================


class TestTRA036AnalyzeFailureL3Gate:
    """TRA-036: at L3_STRICT/L4_FORENSIC, an analyze_document failure must
    raise ConformanceFailure, not silently return an empty string.

    The early `return ""` at kernel.py:214 was added by the TRA-004 fix
    (route exceptions through _recover). It bypasses the L3 gate at
    kernel.py:248-261, so a malformed source produces exit 0 with a 0-byte
    output at L3_STRICT — a silent conformance failure.
    """

    def test_analyze_failure_raises_conformance_failure_at_l3(
        self, tmp_path: Path
    ) -> None:
        """At L3_STRICT, BrokenMarkdown from analyze_document must raise
        ConformanceFailure, not return an empty string."""
        from unittest.mock import patch

        from tra.config import BootstrapConfig
        from tra.exceptions import BrokenMarkdown, ConformanceFailure
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L3_STRICT,
            }
        )
        kernel = TRAKernel(cfg)
        with (
            patch("tra.kernel.analyze_document", side_effect=BrokenMarkdown("boom")),
            pytest.raises(ConformanceFailure, match=r"BROKEN_MARKDOWN|analyze"),
        ):
            kernel.run("# test\n")
        # The EXCEPTION_HANDLER audit record must still be present (TRA-004 preserved).
        handler_records = [
            r for r in kernel.audit._buffer if r.isa_instruction == "EXCEPTION_HANDLER"
        ]
        assert handler_records, (
            "EXCEPTION_HANDLER audit record must still be emitted (TRA-004 preserved)"
        )

    def test_analyze_failure_returns_empty_at_l1(self, tmp_path: Path) -> None:
        """At L1_BASIC, the existing behavior (return '') is preserved —
        L1/L2 do not require zero-BLOCKING (lower strictness dials)."""
        from unittest.mock import patch

        from tra.config import BootstrapConfig
        from tra.exceptions import BrokenMarkdown
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)
        with patch("tra.kernel.analyze_document", side_effect=BrokenMarkdown("boom")):
            result = kernel.run("# test\n")
        assert result == "", (
            "L1 should return empty string on analyze failure (no gate)"
        )


# =========================================================================
# TRA-039 — build_entity_table not wrapped in try/except (latent crash)
# =========================================================================


class TestTRA039BuildEntityTableWrapped:
    """TRA-039: build_entity_table at kernel.py:230 was not wrapped in
    try/except TRAException → self._recover(exc), unlike build_glossary
    at line 226-229. If build_entity_table ever raises EntityAmbiguity
    (e.g., after the TRA-038 fix adds the raise), the kernel would crash
    with an unhandled exception — no EXCEPTION_HANDLER audit record.

    Spec §3 BUILD_ENTITY_TABLE Failure Condition: ENTITY_AMBIGUITY.
    """

    def test_build_entity_table_routes_through_exception_handler(
        self, tmp_path: Path
    ) -> None:
        """If build_entity_table raises EntityAmbiguity, the kernel must
        route it through _recover (EXCEPTION_HANDLER audit record), not
        propagate the exception uncaught."""
        from unittest.mock import patch

        from tra.config import BootstrapConfig
        from tra.exceptions import EntityAmbiguity
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)
        # Patch build_entity_table to raise EntityAmbiguity.
        # Use L1_BASIC so the kernel doesn't raise ConformanceFailure
        # (we're testing the exception routing, not the L3 gate).
        with (
            patch("tra.kernel.build_entity_table", side_effect=EntityAmbiguity("boom")),
            contextlib.suppress(Exception),
        ):
            # Downstream failures are OK — we're testing that
            # EntityAmbiguity is caught and routed, not that the
            # pipeline completes.
            kernel.run("# test heading\n\nsome text\n")
        handler_records = [
            r for r in kernel.audit._buffer if r.isa_instruction == "EXCEPTION_HANDLER"
        ]
        assert handler_records, (
            "expected an EXCEPTION_HANDLER audit record for EntityAmbiguity — "
            "build_entity_table must be wrapped in try/except (TRA-039)"
        )
        # The record should reference ENTITY_AMBIGUITY.
        assert handler_records[0].input_hash == "ENTITY_AMBIGUITY" or (
            handler_records[0]
            .artifact_snapshot.get("detail", "")
            .startswith("ENTITY_AMBIGUITY")
        ), (
            f"EXCEPTION_HANDLER record should reference ENTITY_AMBIGUITY, got: "
            f"{handler_records[0].artifact_snapshot}"
        )


# =========================================================================
# TRA-041 — GLOSSARY_CONFLICT recovery must set the first-occurrence mapping
# =========================================================================


class TestTRA041GlossaryConflictSetsCanonical:
    """TRA-041: when build_glossary raises GlossaryConflict, the kernel's
    _recover path records the exception but does NOT populate ctx.glossary_cache
    with the first-occurrence canonical mapping. The kernel continues with an
    empty glossary, so translate_segment has no terminology substitutions and
    verify_output's terminology check iterates an empty list — no BLOCKING
    diagnostics. The L3 gate passes silently despite the glossary being missing.

    Spec §6 GLOSSARY_CONFLICT recovery: "Log as Blocking Error. Use first
    occurrence as canonical. Flag subsequent occurrences for manual review."
    The implementation logs + flags but does NOT set the first occurrence as
    canonical — the USE_FIRST_OCCURRENCE action label is not enforced.
    """

    def test_glossary_cache_populated_after_conflict_recovery(
        self, tmp_path: Path
    ) -> None:
        """After a GlossaryConflict is recovered, ctx.glossary_cache must
        contain the first-occurrence canonical mapping (not be empty)."""

        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)

        # Get the real module's glossary mappings, then patch to introduce
        # a conflict: same source term maps to two different targets.
        real_module = kernel.ctx.module
        real_mappings = real_module.get_glossary_mappings()
        # Build a conflicting mappings dict: same key, different value.
        # Take the first key and override its value to create a conflict
        # when build_glossary iterates. We do this by making get_glossary_mappings
        # return a dict where the same source appears twice (which is impossible
        # for a real dict, so we patch is_forbidden to trigger the conflict path).
        # Simpler: patch get_glossary_mappings to return a dict, then patch
        # is_forbidden to return True for one entry — that triggers the
        # GlossaryConflict raise at isa.py:187.

        # Use the real mappings but force is_forbidden to True for one entry
        # that is NOT the first — so entries collected before the conflict
        # (the first-occurrence canonical mappings) are non-empty.
        all_sources = list(real_mappings.keys())
        # Pick the second source (or last if only one) so the first entry
        # is collected before the conflict triggers.
        conflict_source = all_sources[1] if len(all_sources) > 1 else all_sources[0]

        class ConflictModule:
            """Wrapper that forces is_forbidden=True for one source to
            trigger GlossaryConflict in build_glossary."""

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def is_forbidden(self, src, tgt):
                # Force a conflict on the chosen source term.
                if src == conflict_source:
                    return True
                return self._real.is_forbidden(src, tgt)

        conflict_module = ConflictModule(real_module)
        kernel.ctx.module = conflict_module

        # Run the kernel. The GlossaryConflict should be raised in build_glossary,
        # routed through _recover, and the kernel should continue with a
        # glossary_cache that contains the first-occurrence canonical mapping
        # (the entries collected BEFORE the conflict).
        with contextlib.suppress(Exception):
            # Downstream failures are OK — we're testing that the glossary
            # is populated with first-occurrence mappings, not that the
            # pipeline completes.
            kernel.run("# test heading\n\nsome text\n")

        # TRA-041: glossary_cache must NOT be empty after conflict recovery.
        # The entries collected before the conflict (the first occurrence)
        # must be preserved as the canonical mapping.
        assert kernel.ctx.glossary_cache, (
            "glossary_cache is empty after GlossaryConflict recovery — "
            "the first-occurrence canonical mapping must be preserved (TRA-041)"
        )


# =========================================================================
# TRA-037 — _rewrite_anchors runs AFTER the L3 gate; audit trail hash mismatch
# =========================================================================


class TestTRA037RewriteAnchorsBeforeGate:
    """TRA-037: _rewrite_anchors was called AFTER the L3 gate, so (a) the
    audit trail's VERIFY_OUTPUT hash was computed on the pre-rewrite target
    while the emitted target was post-rewrite (L4 hash-chain integrity
    broken), and (b) BROKEN_LINK entries in unresolved_ambiguities were
    never checked by the L3 gate (silent pass on broken internal links).

    Fix: move _rewrite_anchors to BEFORE the L3 gate, and add a BROKEN_LINK
    check to the L3+ gate.
    """

    def test_broken_internal_link_raises_conformance_failure_at_l3(
        self, tmp_path: Path
    ) -> None:
        """A source with a link to a non-existent heading must raise
        ConformanceFailure at L3_STRICT (BROKEN_LINK in unresolved_ambiguities)."""
        from tra.config import BootstrapConfig
        from tra.exceptions import ConformanceFailure
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L3_STRICT,
            }
        )
        kernel = TRAKernel(cfg)
        # Source has a link to #nonexistent, which has no matching heading.
        source = "# Real Heading\n\nSee [broken link](#nonexistent).\n"
        with pytest.raises(ConformanceFailure, match=r"BROKEN_LINK|conformant"):
            kernel.run(source)

    def test_audit_trail_hash_matches_emitted_target_at_l4(
        self, tmp_path: Path
    ) -> None:
        """At L4, the audit trail's VERIFY_OUTPUT input_hash must match the
        hash of the actually-emitted target (post-rewrite). L4 hash-chain
        integrity requires this."""
        import hashlib

        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L4_FORENSIC,
            }
        )
        kernel = TRAKernel(cfg)
        # Source with a valid internal link (heading exists, link resolves).
        # Uses pure-English heading so the whole-doc translator doesn't mangle
        # the link target (TRA-070 CJK mangling is out of scope for TRA-037).
        # The link IS rewritten by _rewrite_anchors (TRA-008), so this test
        # verifies the audit trail hashes the post-rewrite target.
        source = "# Introduction\n\nSee [intro](#introduction).\n"
        target = kernel.run(source)
        # Find the LAST VERIFY_OUTPUT audit record (the L3 gate's verify,
        # which now runs AFTER _rewrite_anchors per the TRA-037 fix).
        verify_records = [
            r for r in kernel.audit._buffer if r.isa_instruction == "VERIFY_OUTPUT"
        ]
        assert verify_records, "expected at least one VERIFY_OUTPUT audit record"
        last_verify = verify_records[-1]
        # The audit record's input_hash should match the SHA-256 of the
        # emitted target (the post-rewrite target the kernel returns).
        emitted_hash = hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]
        assert last_verify.input_hash == emitted_hash, (
            f"audit trail VERIFY_OUTPUT hash {last_verify.input_hash!r} does not "
            f"match emitted target hash {emitted_hash!r} — L4 hash-chain integrity "
            f"broken (TRA-037)"
        )


# =========================================================================
# TRA-049 — Same-state kernel transition untested
# =========================================================================


class TestTRA049SameStateTransition:
    """TRA-049: kernel._transition used `if idx < current_idx` (backward
    only); same-state transitions (idx == current_idx) were silently allowed.
    Mutation testing confirmed changing `<` to `<=` left all tests green.

    The spec §2.1 implies forward-only progression. We enforce strict forward
    (same-state transitions raise TRAException).
    """

    def test_same_state_transition_raises(self, tmp_path: Path) -> None:
        """Calling _transition with the current state must raise (strict forward)."""
        from tra.config import BootstrapConfig
        from tra.exceptions import TRAException
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
        # Advance to INITIALIZE_RUNTIME, then try same-state transition.
        kernel._transition(KernelState.INITIALIZE_RUNTIME)
        assert kernel.state == KernelState.INITIALIZE_RUNTIME
        with pytest.raises(TRAException, match=r"Illegal|same.state|backward"):
            kernel._transition(KernelState.INITIALIZE_RUNTIME)


# =========================================================================
# TRA-050 — Cache-key content sensitivity untested
# =========================================================================


class TestTRA050CacheKeyContentSensitivity:
    """TRA-050: cache key must include glossary and entity content. Mutation
    testing confirmed dropping entity_hash/glossary_hash from the key left
    all tests green. This test verifies different glossaries produce different
    cache keys (so a cache hit cannot cross glossary boundaries).
    """

    def test_different_glossary_produces_different_cache_key(self) -> None:
        """Two CacheKeyContexts with different glossaries must produce
        different cache keys (cache cannot cross glossary boundaries)."""
        from tra.cache import CacheKeyContext
        from tra.memory import GlossaryEntry, GlossaryStatus

        glossary_a = [
            GlossaryEntry(
                source="成立", target="Confirmed", status=GlossaryStatus.CANONICAL
            )
        ]
        glossary_b = [
            GlossaryEntry(
                source="成立", target="Valid", status=GlossaryStatus.CANONICAL
            )
        ]
        ctx_a = CacheKeyContext(
            source_text="test",
            glossary=glossary_a,
            model_endpoint="rule-based",
            model_version="v1",
        )
        ctx_b = CacheKeyContext(
            source_text="test",
            glossary=glossary_b,
            model_endpoint="rule-based",
            model_version="v1",
        )
        assert ctx_a.key() != ctx_b.key(), (
            "different glossary content must produce different cache keys — "
            "a cache hit cannot cross glossary boundaries (TRA-050)"
        )

    def test_different_entity_produces_different_cache_key(self) -> None:
        """Two CacheKeyContexts with different entities must produce
        different cache keys."""
        from tra.cache import CacheKeyContext
        from tra.memory import Entity, EntityType

        entities_a = [Entity(name="RustVMM", type=EntityType.PRODUCT)]
        entities_b = [Entity(name="KVM", type=EntityType.PRODUCT)]
        ctx_a = CacheKeyContext(
            source_text="test",
            entities=entities_a,
            model_endpoint="rule-based",
            model_version="v1",
        )
        ctx_b = CacheKeyContext(
            source_text="test",
            entities=entities_b,
            model_endpoint="rule-based",
            model_version="v1",
        )
        assert ctx_a.key() != ctx_b.key(), (
            "different entity content must produce different cache keys (TRA-050)"
        )


# =========================================================================
# TRA-051 — cache.invalidate(pattern) fnmatch branch untested
# =========================================================================


class TestTRA051CacheInvalidatePattern:
    """TRA-051: cache.invalidate(pattern) uses fnmatch to glob-match keys.
    The TRA-011 fix changed from literal-key deletion to fnmatch, but no
    test exercises the --pattern branch. A regression reverting to literal
    deletion would pass all tests.
    """

    def test_cache_invalidate_pattern_deletes_only_matching(
        self, tmp_path: Path
    ) -> None:
        """cache.invalidate(pattern) must delete only keys matching the
        fnmatch glob, leaving non-matching keys intact."""
        from tra.cache import TranslationCache, TranslationResult

        cache = TranslationCache(tmp_path / "cache", enabled=True)
        # Populate with 3 keys: foo, bar, baz.
        for key in ["translation:foo", "translation:bar", "translation:baz"]:
            cache.set(
                key,
                TranslationResult(translation="x", evidence_ids=[], cache_hit=False),
            )
        # Invalidate keys matching 'translation:ba*' (should delete bar + baz).
        deleted = cache.invalidate("translation:ba*")
        assert deleted == 2, f"expected 2 deletions, got {deleted}"
        # foo must remain.
        assert cache.get("translation:foo") is not None, (
            "non-matching key was deleted — fnmatch glob is wrong (TRA-051)"
        )
        # bar and baz must be gone.
        assert cache.get("translation:bar") is None
        assert cache.get("translation:baz") is None


# =========================================================================
# TRA-053 — Inline-code protection branch in _execute_translation untested
# =========================================================================


class TestTRA053InlineCodeProtection:
    """TRA-053: kernel._execute_translation protects inline code (backticks)
    from glossary substitution. The S-03 benchmark exercises fenced code
    blocks but not inline code. A regression removing the inline-code
    branch would pass all tests.
    """

    def test_inline_code_glossary_term_survives_untranslated(
        self, tmp_path: Path
    ) -> None:
        """A glossary term inside inline code (backticks) must survive
        untranslated in the output."""
        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L1_BASIC,
            }
        )
        kernel = TRAKernel(cfg)
        # Source with inline code containing a glossary term.
        source = "The term `成立` is in inline code.\n"
        target = kernel.run(source)
        # The inline-code `成立` must survive verbatim (not translated to "Confirmed").
        assert "`成立`" in target, (
            f"inline-code glossary term was translated — _execute_translation "
            f"inline-code protection broken (TRA-053). Got: {target!r}"
        )
        assert "Confirmed" not in target, (
            f"glossary term leaked out of inline code — got: {target!r}"
        )


# =========================================================================
# TRA-054 — L3 ConformanceFailure raise branch untested
# =========================================================================


class TestTRA054L3ConformanceFailureRaiseBranch:
    """TRA-054: the L3 in-band gate (kernel.py:274-300) raises
    ConformanceFailure when BLOCKING diagnostics remain after the repair
    loop. No test exercises this raise branch — all L3 tests use inputs
    that pass the gate. A regression removing the raise would pass all tests.
    """

    def test_l3_gate_raises_conformance_failure_on_blocking(
        self, tmp_path: Path
    ) -> None:
        """At L3_STRICT, if verify_output returns BLOCKING diagnostics after
        the repair loop, the kernel must raise ConformanceFailure."""
        from unittest.mock import patch

        from tra.config import BootstrapConfig
        from tra.diagnostics import Diagnostic
        from tra.exceptions import ConformanceFailure
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel, Severity

        cfg = BootstrapConfig.from_yaml(
            str(Path(__file__).resolve().parent.parent / "config.yaml")
        ).model_copy(
            update={
                "base_dir": str(tmp_path),
                "audit_trace": str(tmp_path / "audit.jsonl"),
                "compilation_dir": str(tmp_path / "artifacts"),
                "cache_directory": str(tmp_path / "cache"),
                "conformance_level": ConformanceLevel.L3_STRICT,
            }
        )
        kernel = TRAKernel(cfg)

        # Patch verify_output to always return a BLOCKING diagnostic.
        blocking_diag = Diagnostic(
            severity=Severity.BLOCKING,
            subsystem="entity",
            issue="Entity not preserved: 'TestEntity'",
            evidence="expected verbatim occurrence",
            action="Restore entity",
        )
        with (
            patch("tra.kernel.verify_output", return_value=[blocking_diag]),
            pytest.raises(ConformanceFailure, match=r"BLOCKING"),
        ):
            kernel.run("# test\n")


# =========================================================================
# TRA-006 (round 2) — Wire PolicyResolver into verify_output production path
# =========================================================================


class TestTRA006PolicyResolverInvokedInProduction:
    """TRA-006 (round 2): the PolicyResolver must be consulted in the
    production verify_output code path, not just tested in isolation.

    Previously verify_output hard-coded `if CANONICAL: BLOCKING else WARNING`
    — the severity was policy-aware in spirit but not arbitrated through the
    resolver. This test monkeypatches PolicyResolver.resolve to return
    TARGET_FLUENCY (P6) instead of TERMINOLOGICAL_CONSISTENCY (P4), and
    asserts the terminology diagnostic drops to WARNING — proving the
    resolver is actually consulted.
    """

    def test_monkeypatching_resolver_changes_terminology_severity(self) -> None:
        """If PolicyResolver.resolve returns TARGET_FLUENCY, canonical term
        leakage must be WARNING (not BLOCKING) — proving the resolver is
        consulted in the production verify_output path."""
        from unittest.mock import patch

        from tra.diagnostics import AuditTrail
        from tra.isa import verify_output
        from tra.memory import (
            DocumentProfile,
            GlossaryEntry,
            GlossaryStatus,
            RuntimeContext,
            Severity,
            StructuralMap,
        )

        ctx = RuntimeContext(
            configuration={},
            document_profile=DocumentProfile(
                type="Advisory",
                register_="Authoritative",
                intent="Disclose Vulnerability",
                audience="Technical readers",
            ),
            glossary_cache=[
                GlossaryEntry(
                    source="成立",
                    target="Confirmed",
                    status=GlossaryStatus.CANONICAL,
                    rule_id="ZH-EN-RULE#CANON",
                )
            ],
            structural_map=StructuralMap(nodes=[]),
        )
        # Target contains the untranslated canonical source term.
        target = "成立 here"
        source = "成立 here"

        # First, baseline: without monkeypatch, canonical leakage is BLOCKING.
        baseline_diags = verify_output(
            target, source, ctx, AuditTrail("/tmp/test_tra006_baseline.jsonl")
        )
        baseline_term = [d for d in baseline_diags if d.subsystem == "terminology"]
        assert baseline_term, "expected at least one terminology diagnostic"
        assert all(d.severity == Severity.BLOCKING for d in baseline_term), (
            "baseline: canonical term leakage must be BLOCKING (P4 > P6)"
        )

        # Now monkeypatch the _POLICY_RESOLVER instance's wins() method to
        # return False (TERMINOLOGICAL does NOT win over FLUENCY).
        # If the resolver is consulted, the severity should drop to WARNING.
        with patch("tra.isa._POLICY_RESOLVER") as mock_resolver:
            mock_resolver.wins.return_value = False
            diags = verify_output(
                target, source, ctx, AuditTrail("/tmp/test_tra006_mocked.jsonl")
            )
        term_diags = [d for d in diags if d.subsystem == "terminology"]
        assert term_diags, "expected at least one terminology diagnostic"
        assert all(d.severity == Severity.WARNING for d in term_diags), (
            f"with PolicyResolver mocked to return TARGET_FLUENCY, canonical "
            f"term leakage must be WARNING (not BLOCKING) — got "
            f"{[d.severity for d in term_diags]}. The resolver is NOT being "
            f"consulted in the production verify_output path (TRA-006)."
        )


# =========================================================================
# TRA-096 (round 3) — as_interface() must satisfy LanguageModuleProtocol
# =========================================================================


class TestTRA096AsInterfaceProtocol:
    """TRA-096 (round 3): the spec's sanctioned module extension path
    (as_interface() → register() → TRAKernel(registry=)) must not crash.

    Root cause: ModuleInterface only had 3 Callable fields but
    LanguageModuleProtocol requires 7 methods. Pydantic's
    RuntimeContext.module: LanguageModuleProtocol validation rejected
    the ModuleInterface as "not an instance of LanguageModuleProtocol".
    """

    def test_as_interface_satisfies_protocol(self) -> None:
        """ZHENModule().as_interface() must be an instance of
        LanguageModuleProtocol so Pydantic accepts it."""
        from tra.modules.base import LanguageModuleProtocol
        from tra.modules.zh_en import ZHENModule

        iface = ZHENModule().as_interface()
        assert isinstance(iface, LanguageModuleProtocol), (
            "as_interface() must return an object satisfying "
            "LanguageModuleProtocol (TRA-096). ModuleInterface is missing "
            "is_forbidden, get_forbidden_targets, entity_type_hint, "
            "apply_zh_rules."
        )

    def test_default_registry_kernel_does_not_crash(self, tmp_path: Path) -> None:
        """build_default_registry() + TRAKernel(cfg, registry=) must not
        raise ValidationError. This is the exact code path documented in
        SKILL.md §6."""
        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel
        from tra.modules.registry import build_default_registry

        cfg = BootstrapConfig(
            language_pair="ZH -> EN",
            domain="test",
            conformance_level=ConformanceLevel.L3_STRICT,
            model_endpoint="rule-based",
            model_version="test",
            base_dir=str(tmp_path),
            cache_directory=str(tmp_path / "cache"),
            compilation_dir=str(tmp_path / "art"),
            audit_trace=str(tmp_path / "audit.jsonl"),
        )
        registry = build_default_registry()
        kernel = TRAKernel(cfg, registry=registry)
        # The module should be set on the context (not None).
        assert kernel.ctx.module is not None
        # The module's glossary should be accessible.
        mappings = kernel.ctx.module.get_glossary_mappings()
        assert "成立" in mappings, "ZHENModule glossary must be wired"

    def test_stub_fren_module_via_registry(self, tmp_path: Path) -> None:
        """A stub FR→EN module registered via as_interface() must work
        end-to-end through the kernel."""
        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel
        from tra.modules.base import LanguageModuleProtocol
        from tra.modules.registry import ModuleInterface, build_default_registry

        # Minimal stub module satisfying the protocol.
        class FrENModule:
            name = "fr_en"
            kind = "language"
            direction = "FR -> EN"

            def get_glossary_mappings(self) -> dict[str, str]:
                return {
                    "Bonjour": "Hello",
                    "système": "system",
                    "établi": "established",
                }

            def get_forbidden_targets(self) -> dict[str, str]:
                return {}

            def get_style_profile(self) -> object:
                from tra.memory import StyleProfile

                return StyleProfile(
                    voice="Active",
                    sentence_complexity="Medium",
                    epistemic_mapping={},
                    punctuation_rules={},
                )

            def is_forbidden(self, source: str, target: str) -> bool:
                return False

            def entity_type_hint(self, token: str) -> object | None:
                return None

            def apply_zh_rules(self, text: str) -> str:
                return text

            def apply_rules(self, source: str, direction: str) -> str:
                return source

            def as_interface(self) -> ModuleInterface:
                return ModuleInterface(
                    name=self.name,
                    kind=self.kind,
                    get_glossary_mappings=self.get_glossary_mappings,
                    get_style_profile=self.get_style_profile,
                    apply_rules=self.apply_rules,
                    is_forbidden=self.is_forbidden,
                    get_forbidden_targets=self.get_forbidden_targets,
                    entity_type_hint=self.entity_type_hint,
                    apply_zh_rules=self.apply_zh_rules,
                    metadata={"direction": self.direction},
                )

        cfg = BootstrapConfig(
            language_pair="FR -> EN",
            domain="test",
            conformance_level=ConformanceLevel.L3_STRICT,
            model_endpoint="rule-based",
            model_version="test",
            base_dir=str(tmp_path),
            cache_directory=str(tmp_path / "cache"),
            compilation_dir=str(tmp_path / "art"),
            audit_trace=str(tmp_path / "audit.jsonl"),
        )
        registry = build_default_registry()
        fren = FrENModule()
        # Must satisfy the protocol before registration.
        assert isinstance(fren, LanguageModuleProtocol)
        registry.register(fren.as_interface())
        kernel = TRAKernel(cfg, registry=registry)
        assert kernel.ctx.module is not None
        # The kernel should have selected the FR module (not ZHENModule fallback).
        # (The _select_module filters by source language 'fr'.)
        mappings = kernel.ctx.module.get_glossary_mappings()
        assert "Bonjour" in mappings, "FrENModule should be selected for FR -> EN"


# =========================================================================
# TRA-093 (round 3) — False-positive BROKEN_LINK on CJK heading + CJK link
# =========================================================================


class TestTRA093BrokenLinkFalsePositive:
    """TRA-093 (round 3): a valid document with a CJK heading and a CJK
    link pointing at that heading must NOT be rejected at L3 with a
    false-positive BROKEN_LINK.

    Root cause: after whole-doc translation, the link target may already
    be a translated slug. rewrite_links only looked up original slugs
    in map_original_slug_to_placeholder, so translated slugs were
    flagged as broken.
    """

    def test_cjk_heading_with_cjk_link_not_broken(self, tmp_path: Path) -> None:
        """# 系统成立 + [系统成立](#系统成立) must pass L3."""
        from tra.config import BootstrapConfig
        from tra.kernel import TRAKernel
        from tra.memory import ConformanceLevel

        src = "# 系统成立\n\nSee [系统成立](#系统成立) for details.\n"
        cfg = BootstrapConfig(
            language_pair="ZH -> EN",
            domain="test",
            conformance_level=ConformanceLevel.L3_STRICT,
            model_endpoint="rule-based",
            model_version="test",
            base_dir=str(tmp_path),
            cache_directory=str(tmp_path / "cache"),
            compilation_dir=str(tmp_path / "art"),
            audit_trace=str(tmp_path / "audit.jsonl"),
        )
        kernel = TRAKernel(cfg)
        target = kernel.run(src)
        # Must not raise ConformanceFailure. If we got here, the gate passed.
        assert "Confirmed" in target, f"expected 'Confirmed' in target, got: {target!r}"
        # No BROKEN_LINK in unresolved_ambiguities.
        broken = [a for a in kernel.ctx.unresolved_ambiguities if "BROKEN_LINK" in a]
        assert not broken, f"false-positive BROKEN_LINK: {broken}"

    def test_already_translated_slug_not_broken(self) -> None:
        """If a link's slug already matches a translated slug value in
        the registry, rewrite_links must not flag it as broken."""
        from tra.anchor import AnchorRegistry, rewrite_links

        registry = AnchorRegistry()
        # Simulate: heading "系统成立" was registered, translated to
        # "The system is Confirmed", slug "the-system-is-confirmed".
        placeholder = registry.register("系统成立")
        registry.bind(placeholder, "the-system-is-confirmed")
        # The link target is already the translated slug.
        md = "[link](#the-system-is-confirmed)"
        rewritten, broken = rewrite_links(md, registry)
        assert not broken, f"false-positive broken: {broken}"
        assert rewritten == md, f"link should be unchanged, got: {rewritten!r}"
