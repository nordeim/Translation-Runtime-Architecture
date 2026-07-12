"""Phase 6.3: audit summary + state-transition visualization.

- `summarize_audit`: aggregate an AuditTrail into counts by severity,
  subsystem (derived from ISA instruction + flags), and instruction. The
  L3/L4 conformance gate (zero BLOCKING) reads from this summary.
- `mermaid_state_diagram`: render the Kernel's canonical lifecycle as a
  Mermaid flowchart from `RuntimeContext.execution_log`, so a run's actual
  path is reproducible/visualizable.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .diagnostics import AuditTrail, EvidenceRegistry
from .kernel import _KERNEL_ORDER, KernelState
from .memory import Severity


def summarize_audit(audit: AuditTrail) -> dict[str, Any]:
    """Aggregate an audit trail into conformance-relevant counts.

    Returns keys: total, by_severity, by_instruction, blocking_flags,
    and a `l3_conformant` boolean (zero BLOCKING raised anywhere).

    Reads the in-memory `_buffer` if populated, otherwise the on-disk JSONL.
    """
    records = audit._buffer or audit.load()
    by_severity: Counter[str] = Counter()
    by_instruction: Counter[str] = Counter()
    blocking_flags = 0

    for rec in records:
        by_instruction[rec.isa_instruction] += 1
        for flag in rec.flags_raised or []:
            by_severity[flag] += 1
            if flag == Severity.BLOCKING.value:
                blocking_flags += 1

    return {
        "total": len(records),
        "by_severity": dict(by_severity),
        "by_instruction": dict(by_instruction),
        "blocking_flags": blocking_flags,
        "l3_conformant": blocking_flags == 0,
    }


def mermaid_state_diagram(execution_log: list[str]) -> str:
    """Render the Kernel lifecycle as a Mermaid flowchart.

    Nodes are the canonical states; edges follow the order in which the run
    actually traversed them (from `RuntimeContext.execution_log`). Unknown or
    out-of-order states are still rendered so the diagram reflects reality.
    """
    states = execution_log or [s.value for s in _KERNEL_ORDER]
    lines = ["flowchart LR"]
    for s in KernelState:
        label = s.value.replace("_", " ").title()
        lines.append(f'    {s.value}["{label}"]')

    edges: list[str] = []
    for a, b in zip(states, states[1:], strict=False):
        edges.append(f"    {a} --> {b}")
    if not edges:
        # Single-state or empty log: self-loop placeholder for valid diagram.
        edges.append(f"    {states[0]} --> {states[0]}")
    lines.extend(edges)
    return "\n".join(lines)


def line_by_line_trace(target: str, evidence: EvidenceRegistry) -> list[dict[str, Any]]:
    """L4 forensic tracer: map each output line -> its evidence chain (§6.4.1).

    Every non-empty target line is attributed to the evidence records whose
    `target_span` is contained within that line, so a forensic reviewer can
    trace any output fragment back to the decision(s) that produced it. Lines
    with no attributable evidence are flagged for manual review.
    """
    records = evidence.all()
    trace: list[dict[str, Any]] = []
    for idx, line in enumerate(target.splitlines()):
        if not line.strip():
            continue
        hits = [r.id for r in records if r.target_span and r.target_span in line]
        trace.append(
            {
                "line": idx + 1,
                "text": line,
                "evidence_ids": hits,
                "attributed": bool(hits),
            }
        )
    return trace
