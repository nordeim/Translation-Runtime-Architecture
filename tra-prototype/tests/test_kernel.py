"""Phase 3 tests: TRAKernel orchestration + full pipeline."""

from __future__ import annotations

from pathlib import Path

from tra.config import BootstrapConfig
from tra.exceptions import TRAException
from tra.kernel import KernelState, TRAKernel


def _kernel(tmp_path: Path) -> TRAKernel:
    # Resolve config.yaml relative to the repo so the suite is cwd-independent.
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    cfg = BootstrapConfig.from_yaml(str(config_path))
    # BootstrapConfig is frozen (TRA-018); use model_copy for path overrides.
    cfg = cfg.model_copy(
        update={
            "cache_directory": str(tmp_path / "cache"),
            "compilation_dir": str(tmp_path / "compilation_artifacts"),
            "audit_trace": str(tmp_path / "audit_trace.jsonl"),
        }
    )
    return TRAKernel(cfg)


EXAMPLE = """# Security Advisory

This system may 成立 under heavy load. The 执行环境 must
accurately describe the 高度可信 configuration. We should 提供支持
for the RustVMM v0.5.0 release.
"""


def test_kernel_runs_full_pipeline(tmp_path: Path):
    k = _kernel(tmp_path)
    out = k.run(EXAMPLE)
    assert "Confirmed" in out
    assert "execution environment" in out
    assert "highly credible" in out
    assert "RustVMM" in out  # entity preserved verbatim
    assert "v0.5.0" in out


def test_kernel_emits_audit_trace(tmp_path: Path):
    k = _kernel(tmp_path)
    k.run(EXAMPLE)
    assert len(k.audit._buffer) >= 5  # one record per ISA instruction
    instructions = {r.isa_instruction for r in k.audit._buffer}
    assert "ANALYZE_DOCUMENT" in instructions
    assert "BUILD_GLOSSARY" in instructions
    assert "BUILD_ENTITY_TABLE" in instructions
    assert "TRANSLATE_SEGMENT" in instructions
    assert "VERIFY_OUTPUT" in instructions


def test_kernel_exports_artifacts(tmp_path: Path):
    k = _kernel(tmp_path)
    k.run(EXAMPLE)
    arts = tmp_path / "compilation_artifacts"
    assert (arts / "glossary.yaml").exists()
    assert (arts / "entity_table.yaml").exists()
    assert (arts / "structural_map.json").exists()
    assert (arts / "style_profile.yaml").exists()


def test_kernel_state_machine_is_sequential():
    k = _kernel(Path("/tmp"))
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


def test_kernel_illegal_backward_transition():
    k = _kernel(Path("/tmp"))
    k._transition(KernelState.INITIALIZE_RUNTIME)
    k._transition(KernelState.ANALYZE_DOCUMENT)
    try:
        k._transition(KernelState.INITIALIZE_RUNTIME)
        raise AssertionError("expected illegal transition")
    except TRAException:
        pass


def test_kernel_audit_trail_on_disk(tmp_path: Path):
    k = _kernel(tmp_path)
    k.run(EXAMPLE)
    trace = Path(k.config.audit_trace)
    assert trace.exists()
    lines = trace.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(k.audit._buffer)


def test_kernel_records_exception_recovery(tmp_path: Path):
    from tra import isa

    # Force a GLOSSARY_CONFLICT during BUILD_GLOSSARY to exercise the
    # EXCEPTION_HANDLER recovery path.
    orig = isa._MODULE.get_glossary_mappings
    isa._MODULE.get_glossary_mappings = lambda: {"成立": "Valid"}  # drift target
    try:
        k = _kernel(tmp_path)
        k.run(EXAMPLE)
    finally:
        isa._MODULE.get_glossary_mappings = orig

    instructions = {r.isa_instruction for r in k.audit._buffer}
    assert "EXCEPTION_HANDLER" in instructions
    rec = next(r for r in k.audit._buffer if r.isa_instruction == "EXCEPTION_HANDLER")
    assert rec.artifact_snapshot.get("source_term") == "成立"
    assert k.ctx.unresolved_ambiguities
