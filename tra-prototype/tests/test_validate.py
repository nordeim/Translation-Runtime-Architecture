"""Phase 5.1.4: standalone validation of a candidate translation."""

from __future__ import annotations

from pathlib import Path

from tra.config import BootstrapConfig
from tra.memory import ConformanceLevel
from tra.validate import ValidationReport, validate_translation

_SPEC = {
    "language_pair": "ZH -> EN",
    "domain": "Security Advisory",
    "conformance_level": "L3_STRICT",
    "model_endpoint": "openai/gpt-4o-mini",
    "model_version": "2024-07-18",
}


def _cfg() -> BootstrapConfig:
    return BootstrapConfig(**_SPEC)


def test_validate_clean_candidate_passes(tmp_path: Path):
    src = tmp_path / "a.md"
    src.write_text("RustVMM v0.5.0 成立", encoding="utf-8")
    cand = tmp_path / "b.md"
    cand.write_text("RustVMM v0.5.0 is Confirmed", encoding="utf-8")
    report = validate_translation(src, cand, _cfg())
    assert report.passed
    assert not report.blocking


def test_validate_missing_entity_blocks(tmp_path: Path):
    src = tmp_path / "a.md"
    src.write_text("RustVMM present", encoding="utf-8")
    cand = tmp_path / "b.md"
    cand.write_text("translated without the name", encoding="utf-8")
    report = validate_translation(src, cand, _cfg())
    assert not report.passed
    assert any("RustVMM" in d.issue for d in report.blocking)


def test_validate_epistemic_drift_blocks(tmp_path: Path):
    src = tmp_path / "a.md"
    src.write_text("成立", encoding="utf-8")
    cand = tmp_path / "b.md"
    cand.write_text("it is Valid now", encoding="utf-8")
    report = validate_translation(src, cand, _cfg())
    assert not report.passed
    assert any("Valid" in d.issue for d in report.blocking)


def test_validate_report_summary_counts(tmp_path: Path):
    src = tmp_path / "a.md"
    src.write_text("成立", encoding="utf-8")
    cand = tmp_path / "b.md"
    cand.write_text("it is Valid now", encoding="utf-8")
    report = ValidationReport([], ConformanceLevel.L3_STRICT)
    assert report.passed
    report2 = validate_translation(src, cand, _cfg())
    s = report2.summary()
    assert s["blocking"] >= 1
    assert s["warnings"] + s["blocking"] == len(report2.diagnostics)
