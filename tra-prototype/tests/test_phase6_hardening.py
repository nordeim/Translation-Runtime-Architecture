"""Phase 6.4 L4 forensics + 6.5 graceful degradation / sanitization."""

from __future__ import annotations

from pathlib import Path

from tra.cache import TranslationCache
from tra.diagnostics import (
    AuditTrail,
    Diagnostic,
    EvidenceRecord,
    EvidenceRegistry,
    EvidenceType,
)
from tra.hitl import format_unrecoverable, review_decision
from tra.isa import repair_segment, translate_segment
from tra.kernel import TRAKernel
from tra.memory import (
    ConformanceLevel,
    DocumentProfile,
    GlossaryEntry,
    GlossaryStatus,
    RuntimeContext,
    Severity,
    StructuralMap,
)
from tra.reporting import line_by_line_trace


def _ctx() -> RuntimeContext:
    return RuntimeContext(
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


def test_repair_segment_records_history():
    ctx = _ctx()
    audit = AuditTrail("x.jsonl")
    ev = EvidenceRegistry()
    diag = Diagnostic(
        severity=Severity.WARNING,
        subsystem="terminology",
        issue="Source term not translated: '成立'",
        evidence="expected canonical target 'Confirmed'",
        action="Apply canonical mapping",
    )
    out = repair_segment("系统 成立", "系统 成立", diag, ctx, ev, audit, attempt=1)
    assert "Confirmed" in out
    assert len(ctx.repair_history) == 1
    rec = ctx.repair_history[0]
    assert rec.attempt == 1
    assert rec.subsystem == "terminology"
    assert rec.resolved is True


def test_graceful_degradation_on_llm_failure():
    ctx = _ctx()
    audit = AuditTrail("x.jsonl")
    ev = EvidenceRegistry()
    cache = TranslationCache("./cache", enabled=False)

    def boom(_seg: str, _ctx: RuntimeContext) -> str:
        raise RuntimeError("llm down")

    res = translate_segment("系统 成立", ctx, cache, ev, audit, llm_translate=boom)
    # Rule path still produced a valid (degraded) output.
    assert "Confirmed" in res.translation
    # Degradation is recorded on the audit trail.
    degraded = [r for r in audit._buffer if r.artifact_snapshot.get("degraded")]
    assert degraded, "expected a degraded artifact snapshot on the audit trail"
    # TRA-048: exactly ONE TRANSLATE_SEGMENT audit record must exist for the
    # degraded segment. The early `return result` in isa.py:393 prevents a
    # second non-degraded record from being emitted. Without that early
    # return, a second record (without the degraded flag) would appear —
    # an auditor inspecting only the last record per segment would miss the
    # degradation. This test catches that mutation.
    translate_records = [
        r for r in audit._buffer if r.isa_instruction == "TRANSLATE_SEGMENT"
    ]
    assert len(translate_records) == 1, (
        f"expected exactly 1 TRANSLATE_SEGMENT audit record on LLM degradation, "
        f"got {len(translate_records)} — the early return in isa.py "
        f"(TRA-015 fix) must prevent a second non-degraded record (TRA-048)"
    )


def test_sanitize_strips_control_and_bidi():
    from tra.utils import sanitize_input

    nasty = "clean\ntext\x00with\x01control‮bidi﻿"
    out = sanitize_input(nasty)
    assert "\x00" not in out
    assert "\x01" not in out
    assert "‮" not in out
    assert "﻿" not in out
    # legitimate whitespace preserved
    assert "\n" in out


def test_l4_forensic_trace_emitted_at_l4(tmp_path: Path):
    cfg = Path(__file__).resolve().parent.parent / "config.yaml"
    from tra.config import BootstrapConfig

    base = BootstrapConfig.from_yaml(cfg)
    # BootstrapConfig is frozen (TRA-018); use model_copy for overrides.
    # Set base_dir=tmp_path for the path-safety validator (TRA-014).
    base = base.model_copy(
        update={
            "base_dir": str(tmp_path),
            "conformance_level": ConformanceLevel.L4_FORENSIC,
            "audit_trace": str(tmp_path / "audit.jsonl"),
            "compilation_dir": str(tmp_path / "artifacts"),
        }
    )
    kernel = TRAKernel(base)
    kernel.run("# Title\n\n系统 成立 是 高度可信 的。\n")
    trace = tmp_path / "artifacts" / "evidence_trace.jsonl"
    ambiguity = tmp_path / "artifacts" / "ambiguity_register.json"
    assert trace.exists()
    assert ambiguity.exists()


def test_line_by_line_trace_attribution():
    ev = EvidenceRegistry()
    eid = ev.add(
        EvidenceRecord(
            type=EvidenceType.LLM_DECISION,
            module="isa",
            source_span="系统 成立",
            target_span="The system is Confirmed",
            rationale="rule",
        )
    )
    target = "The system is Confirmed\nplain prose with no evidence\n"
    trace = line_by_line_trace(target, ev)
    assert trace[0]["attributed"] is True
    assert trace[0]["evidence_ids"] == [eid]
    # Attributed by substring containment; prose line flagged unattributed.
    assert trace[1]["attributed"] is False


def test_hitl_review_decision_accept(monkeypatch):
    calls: dict[str, str] = {}

    def fake_ask(prompt, choices=None, default=None):  # noqa: ANN001
        calls["prompt"] = prompt
        return "accept"

    monkeypatch.setattr("tra.hitl.Prompt.ask", staticmethod(fake_ask))
    resolution, text = review_decision("amb", "src", "candidate")
    assert resolution == "accept"
    assert text == "candidate"


def test_hitl_format_unrecoverable():
    ctx = _ctx()
    from tra.diagnostics import Diagnostic

    diag = Diagnostic(
        severity=Severity.BLOCKING,
        subsystem="structural",
        issue="Heading count mismatch",
        evidence="source=2 target=1",
        action="Restore hierarchy",
    )
    uncertainty, excerpt = format_unrecoverable(ctx, diag, "source=2 target=1 here")
    assert "UNRECOVERABLE" in uncertainty
    assert "source=2" in excerpt
