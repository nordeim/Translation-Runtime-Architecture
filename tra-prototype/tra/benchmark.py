"""TRA benchmark suite runner (implementation_plan.md §5.3).

Loads declarative benchmark cases (the S/F/T/D/E categories from
TRA-BENCHMARK-SUITE.md), runs each through the full TRA pipeline, and asserts
the spec's success criteria deterministically:

  - `must_contain`    substrings that MUST appear in the target (terminology,
                      factual strings, preserved entities).
  - `must_not_contain` forbidden substrings (drift targets, e.g. 'runtime').
  - `zero_blocking`   the L3/L4 gate: VERIFY_OUTPUT raises no BLOCKING
                      diagnostic on the produced target.

Cases are data (JSONL fixtures) so the suite grows toward 100+ without code
changes. The runner reuses the exact ISA instructions the Kernel uses.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from .config import BootstrapConfig
from .diagnostics import (
    AuditTrail,
    EvidenceRegistry,
)
from .isa import (
    analyze_document,
    build_entity_table,
    build_glossary,
    verify_output,
)
from .kernel import TRAKernel
from .memory import ConformanceLevel, RuntimeContext, Severity


class BenchmarkCase(BaseModel):
    """A single declarative benchmark case (one JSONL line)."""

    id: str
    category: str  # S | F | T | D | E
    source: str
    level: str = "L3_STRICT"
    must_contain: list[str] = Field(default_factory=list)
    must_not_contain: list[str] = Field(default_factory=list)
    zero_blocking: bool = True
    description: str | None = None


class CaseResult(BaseModel):
    """Outcome of running one BenchmarkCase."""

    case_id: str
    category: str
    output: str
    blocking: int
    warnings: int
    failed_checks: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failed_checks


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    """Load benchmark cases from a JSONL fixture (one JSON object per line)."""
    p = Path(path)
    cases: list[BenchmarkCase] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(BenchmarkCase.model_validate_json(line))
    return cases


class BenchmarkRunner:
    """Runs benchmark cases through the TRA pipeline and asserts criteria."""

    def __init__(self, config: BootstrapConfig) -> None:
        self.config = config

    def run_case(self, case: BenchmarkCase) -> CaseResult:
        cfg = self.config.model_copy(
            update={"conformance_level": ConformanceLevel(case.level)}
        )
        kernel = TRAKernel(cfg)
        output = kernel.run(case.source)

        failed: list[str] = []
        for sub in case.must_contain:
            if sub not in output:
                failed.append(f"missing expected substring {sub!r}")
        for sub in case.must_not_contain:
            if sub in output:
                failed.append(f"forbidden substring present {sub!r}")

        if case.zero_blocking:
            audit = AuditTrail(cfg.audit_trace)
            ctx = RuntimeContext(configuration=cfg.model_dump())
            evidence = EvidenceRegistry()
            profile, smap = analyze_document(case.source, ctx, audit)
            build_glossary(case.source, profile, ctx, evidence, audit)
            build_entity_table(case.source, smap, ctx, evidence, audit)
            diags = verify_output(output, case.source, ctx, audit)
            n_blocking = sum(1 for d in diags if d.severity == Severity.BLOCKING)
            n_warnings = sum(1 for d in diags if d.severity == Severity.WARNING)
            if n_blocking:
                failed.append(f"{n_blocking} BLOCKING diagnostic(s) raised")
        else:
            diags = []
            n_blocking = 0
            n_warnings = 0

        return CaseResult(
            case_id=case.id,
            category=case.category,
            output=output,
            blocking=n_blocking,
            warnings=n_warnings,
            failed_checks=failed,
        )

    def run_all(self, cases: list[BenchmarkCase]) -> list[CaseResult]:
        return [self.run_case(c) for c in cases]


def summarize(results: list[CaseResult]) -> dict[str, int]:
    passed = sum(1 for r in results if r.passed)
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "blocking": sum(r.blocking for r in results),
    }
