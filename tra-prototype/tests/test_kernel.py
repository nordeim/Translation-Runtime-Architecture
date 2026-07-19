"""Phase 3 tests: TRAKernel orchestration + full pipeline."""

from __future__ import annotations

from pathlib import Path

from tra.config import BootstrapConfig
from tra.exceptions import TRAException
from tra.kernel import KernelState, TRAKernel

# TRA-D5-008 (round 5): the shared `kernel_config` fixture (conftest.py)
# replaces the inline `_kernel(tmp_path)` helper, eliminating duplicated
# config-loading boilerplate across test_kernel.py / test_phase6_hardening.py /
# test_benchmark.py / test_outstanding_findings.py.
#
# Tests that need a TRAKernel instance should accept the `kernel_config`
# fixture and construct TRAKernel(kernel_config). For tests that need a
# TRAKernel without running the pipeline (e.g. state-machine assertions),
# use `kernel_config` directly.


EXAMPLE = """# Security Advisory

This system may 成立 under heavy load. The 执行环境 must
accurately describe the 高度可信 configuration. We should 提供支持
for the RustVMM v0.5.0 release.
"""


def test_kernel_runs_full_pipeline(kernel_config: BootstrapConfig):
    k = TRAKernel(kernel_config)
    out = k.run(EXAMPLE)
    assert "Confirmed" in out
    assert "execution environment" in out
    assert "highly credible" in out
    assert "RustVMM" in out  # entity preserved verbatim
    assert "v0.5.0" in out


def test_kernel_emits_audit_trace(kernel_config: BootstrapConfig):
    k = TRAKernel(kernel_config)
    k.run(EXAMPLE)
    assert len(k.audit._buffer) >= 5  # one record per ISA instruction
    instructions = {r.isa_instruction for r in k.audit._buffer}
    assert "ANALYZE_DOCUMENT" in instructions
    assert "BUILD_GLOSSARY" in instructions
    assert "BUILD_ENTITY_TABLE" in instructions
    assert "TRANSLATE_SEGMENT" in instructions
    assert "VERIFY_OUTPUT" in instructions


def test_kernel_exports_artifacts(kernel_config: BootstrapConfig, tmp_path: Path):
    k = TRAKernel(kernel_config)
    k.run(EXAMPLE)
    arts = tmp_path / "compilation_artifacts"
    assert (arts / "glossary.yaml").exists()
    assert (arts / "entity_table.yaml").exists()
    assert (arts / "structural_map.json").exists()
    assert (arts / "style_profile.yaml").exists()


def test_kernel_state_machine_is_sequential(kernel_config: BootstrapConfig):
    k = TRAKernel(kernel_config)
    # Cannot jump to EMIT before BOOTSTRAP-style ordering enforced by run().
    seq = [
        KernelState.INITIALIZE_RUNTIME,
        KernelState.ANALYZE_DOCUMENT,
        KernelState.BUILD_ARTIFACTS,
        KernelState.EXECUTE_TRANSLATION,
        KernelState.VERIFY_OUTPUT,
        KernelState.REPAIR_IF_NEEDED,
        KernelState.AUDIT_DIAGNOSTICS,
        KernelState.EMIT_PAYLOAD,
    ]
    for s in seq:
        k._transition(s)
    assert k.state == KernelState.EMIT_PAYLOAD
    assert k.ctx.execution_log[-1] == "EMIT_PAYLOAD"


def test_kernel_illegal_backward_transition(kernel_config: BootstrapConfig):
    k = TRAKernel(kernel_config)
    k._transition(KernelState.INITIALIZE_RUNTIME)
    k._transition(KernelState.ANALYZE_DOCUMENT)
    try:
        k._transition(KernelState.INITIALIZE_RUNTIME)
        raise AssertionError("expected illegal transition")
    except TRAException:
        pass


def test_kernel_audit_trail_on_disk(kernel_config: BootstrapConfig):
    k = TRAKernel(kernel_config)
    k.run(EXAMPLE)
    trace = Path(k.config.audit_trace)
    assert trace.exists()
    lines = trace.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(k.audit._buffer)


def test_kernel_records_exception_recovery(kernel_config: BootstrapConfig):
    from tra.modules.zh_en import ZHENModule

    # Force a GLOSSARY_CONFLICT during BUILD_GLOSSARY to exercise the
    # EXCEPTION_HANDLER recovery path. Patch the ZHENModule class so all
    # instances (including the one the kernel constructs) return the drift.
    orig = ZHENModule.get_glossary_mappings
    ZHENModule.get_glossary_mappings = lambda self: {"成立": "Valid"}  # type: ignore[method-assign]
    try:
        k = TRAKernel(kernel_config)
        k.run(EXAMPLE)
    finally:
        ZHENModule.get_glossary_mappings = orig  # type: ignore[method-assign]

    instructions = {r.isa_instruction for r in k.audit._buffer}
    assert "EXCEPTION_HANDLER" in instructions
    rec = next(r for r in k.audit._buffer if r.isa_instruction == "EXCEPTION_HANDLER")
    assert rec.artifact_snapshot.get("source_term") == "成立"
    assert k.ctx.unresolved_ambiguities
