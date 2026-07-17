"""E2E test: run the full TRA pipeline on to_translate.md with a manual
translation hijacking the llm_translate seam.

This simulates an AI-powered translation where the LLM provides the
translation and the TRA engine handles analysis, verification, repair,
and audit. The manual translation is pre-generated and returned by the
llm_translate callback.
"""

from __future__ import annotations

from pathlib import Path

from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel

# Load the source and the manual translation.
repo_root = Path(__file__).resolve().parent.parent
source = (repo_root / "to_translate.md").read_text(encoding="utf-8")
manual_translation = (repo_root / "tra-prototype" / "to_translate.en.md").read_text(
    encoding="utf-8"
)

# Configure the kernel at L3.
cfg = BootstrapConfig.from_yaml(str(repo_root / "tra-prototype" / "config.yaml"))
cfg = cfg.model_copy(
    update={
        "base_dir": str(repo_root / "tra-prototype"),
        "conformance_level": ConformanceLevel.L3_STRICT,
        "audit_trace": str(repo_root / "tra-prototype" / "e2e_audit_trace.jsonl"),
        "compilation_dir": str(repo_root / "tra-prototype" / "e2e_artifacts"),
        "cache_directory": str(repo_root / "tra-prototype" / "e2e_cache"),
    }
)

# Hijack the llm_translate seam: return the manual translation.
# The kernel imports translate_segment directly, so we must patch the
# reference in the kernel's namespace (not isa's).
call_count = 0


def manual_llm(source_segment: str, ctx: object) -> str:
    global call_count
    call_count += 1
    print(f"  llm_translate called #{call_count} (input={len(source_segment)} chars)")
    return manual_translation


import tra.kernel as kernel_mod  # noqa: E402

orig_translate = kernel_mod.translate_segment


def patched_translate(source_segment, ctx, cache, evidence, audit, **kwargs):
    kwargs["llm_translate"] = manual_llm
    return orig_translate(source_segment, ctx, cache, evidence, audit, **kwargs)


kernel_mod.translate_segment = patched_translate

# Run the full pipeline.
print("=" * 70)
print("E2E Test: TRA pipeline with manual LLM translation")
print("=" * 70)
print(
    f"Source: to_translate.md ({len(source)} chars, {source.count(chr(10)) + 1} lines)"
)
print(f"Manual translation: to_translate.en.md ({len(manual_translation)} chars)")
print("Conformance level: L3_STRICT")
print()

kernel = TRAKernel(cfg)
try:
    target = kernel.run(source)
    print()
    print(f"Pipeline completed. Output length: {len(target)} chars")
    print(f"Output matches manual translation: {target == manual_translation}")
except Exception as exc:
    print(f"Pipeline raised: {type(exc).__name__}: {exc}")
    target = ""

# Check the audit trail.
print()
print("--- Audit Trail Summary ---")
records = kernel.audit._buffer
print(f"Total audit records: {len(records)}")
for rec in records:
    flags = ", ".join(rec.flags_raised) if rec.flags_raised else "-"
    print(
        f"  [{rec.sequence_id}] {rec.isa_instruction:25s} "
        f"evidence={len(rec.evidence_chain):2d}  flags={flags}"
    )

# Check the conformance gate.
print()
blocking = sum(1 for r in records if r.flags_raised and "BLOCKING" in r.flags_raised)
warnings = sum(1 for r in records if r.flags_raised and "WARNING" in r.flags_raised)
print(f"Conformance: BLOCKING={blocking} WARNING={warnings}")
if blocking == 0:
    print("VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics")
else:
    print(f"VERDICT: NON-CONFORMANT — {blocking} BLOCKING diagnostic(s)")
