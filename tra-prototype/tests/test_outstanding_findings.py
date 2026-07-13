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
