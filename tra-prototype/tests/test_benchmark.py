"""Phase 5.3: TRA benchmark suite (S/F/T/D/E + regression).

Loads declarative cases from tests/benchmark/cases/*.jsonl, runs each through
the full pipeline, and asserts the spec success criteria. The L3 gate requires
zero BLOCKING diagnostics on every case.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tra.benchmark import (
    BenchmarkCase,
    BenchmarkRunner,
    CaseResult,
    load_cases,
    summarize,
)
from tra.config import BootstrapConfig

CASES_DIR = Path(__file__).parent / "benchmark" / "cases"


def _cfg() -> BootstrapConfig:
    return BootstrapConfig.from_yaml("config.yaml")


def _all_cases() -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for path in sorted(CASES_DIR.glob("*.jsonl")):
        cases.extend(load_cases(path))
    return cases


def test_load_cases_parses_fixtures():
    cases = _all_cases()
    ids = {c.id for c in cases}
    assert "F-01" in ids
    assert "T-05" in ids
    assert "E-02" in ids
    # Every case must declare at least one assertion.
    assert all(c.must_contain or c.must_not_contain or c.zero_blocking for c in cases)


@pytest.mark.parametrize("case", _all_cases(), ids=lambda c: c.id)
def test_benchmark_case(case: BenchmarkCase):
    runner = BenchmarkRunner(_cfg())
    result = runner.run_case(case)
    assert isinstance(result, CaseResult)
    assert result.passed, f"{case.id} failed: {result.failed_checks}"


def test_l3_gate_zero_blocking_subset():
    """L3 conformance: every case in the suite raises zero BLOCKING."""
    runner = BenchmarkRunner(_cfg())
    results = runner.run_all(_all_cases())
    summary = summarize(results)
    assert summary["blocking"] == 0
    assert summary["failed"] == 0
    assert summary["total"] >= len(_all_cases())


def test_regression_cache_hit_byte_identical():
    """Regression: identical source + context yields byte-identical output."""
    runner = BenchmarkRunner(_cfg())
    case = next(c for c in _all_cases() if c.id == "R-01")
    first = runner.run_case(case).output
    second = runner.run_case(case).output
    assert first == second
