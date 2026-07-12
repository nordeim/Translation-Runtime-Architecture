"""Phase 6.3: audit summary + Mermaid state diagram."""

from __future__ import annotations

from tra.diagnostics import AuditTrail, Severity
from tra.kernel import KernelState
from tra.reporting import mermaid_state_diagram, summarize_audit


def _trace_with_blocking() -> AuditTrail:
    audit = AuditTrail("x.jsonl")
    audit.append("ANALYZE_DOCUMENT", "h1", [])
    audit.append("VERIFY_OUTPUT", "h2", [], flags_raised=[Severity.BLOCKING.value])
    return audit


def test_summarize_counts_severity_and_instruction():
    audit = _trace_with_blocking()
    s = summarize_audit(audit)
    assert s["total"] == 2
    assert s["by_instruction"]["VERIFY_OUTPUT"] == 1
    assert s["by_severity"][Severity.BLOCKING.value] == 1
    assert s["blocking_flags"] == 1
    assert s["l3_conformant"] is False


def test_summarize_l3_conformant_when_no_blocking():
    audit = AuditTrail("y.jsonl")
    audit.append("ANALYZE_DOCUMENT", "h", [])
    audit.append("BUILD_GLOSSARY", "h", [], flags_raised=[Severity.WARNING.value])
    s = summarize_audit(audit)
    assert s["l3_conformant"] is True
    assert s["blocking_flags"] == 0


def test_mermaid_diagram_renders_canonical_order():
    diag = mermaid_state_diagram([])
    assert diag.startswith("flowchart LR")
    assert KernelState.BOOTSTRAP.value in diag
    assert KernelState.EMIT_PAYLOAD.value in diag
    # Canonical edges along the order.
    src = KernelState.ANALYZE_DOCUMENT.value
    dst = KernelState.BUILD_ARTIFACTS.value
    assert f"{src} --> {dst}" in diag


def test_mermaid_diagram_follows_execution_log():
    log = ["INITIALIZE_RUNTIME", "ANALYZE_DOCUMENT", "BUILD_ARTIFACTS"]
    diag = mermaid_state_diagram(log)
    assert "INITIALIZE_RUNTIME --> ANALYZE_DOCUMENT" in diag
    assert "ANALYZE_DOCUMENT --> BUILD_ARTIFACTS" in diag


def test_mermaid_diagram_handles_single_state():
    diag = mermaid_state_diagram(["EMIT_PAYLOAD"])
    assert "EMIT_PAYLOAD --> EMIT_PAYLOAD" in diag
