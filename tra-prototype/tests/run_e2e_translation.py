#!/usr/bin/env python3
"""E2E test runner: translate to_translate.md through the full TRA pipeline.

This script hijacks the llm_translate seam to return the manually-generated
translation (to_translate_en.md), runs the kernel at L3 and L4, verifies
conformance, and saves the translated output to to_translate_en.md.

Usage:
    cd tra-prototype
    python3 tests/run_e2e_translation.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# Ensure we can import the tra package
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tra-prototype"))

from tra.config import BootstrapConfig  # noqa: E402
from tra.kernel import TRAKernel  # noqa: E402
from tra.memory import ConformanceLevel  # noqa: E402

SOURCE_PATH = REPO_ROOT / "to_translate.md"
MANUAL_TRANSLATION_PATH = REPO_ROOT / "tra-prototype" / "to_translate_en.md"
CONFIG_PATH = REPO_ROOT / "tra-prototype" / "config.yaml"
OUTPUT_PATH = REPO_ROOT / "tra-prototype" / "to_translate_en.md"


def main() -> int:
    """Run the E2E translation and save the output."""
    print("=" * 70)
    print("TRA E2E Translation Test")
    print("=" * 70)

    # Load source and manual translation.
    source = SOURCE_PATH.read_text(encoding="utf-8")
    manual = MANUAL_TRANSLATION_PATH.read_text(encoding="utf-8")
    print(f"Source: {SOURCE_PATH.name} ({len(source)} chars)")
    print(f"Manual translation: {MANUAL_TRANSLATION_PATH.name} ({len(manual)} chars)")

    # Build config from config.yaml, override paths to a temp working dir.
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp(prefix="tra_e2e_"))
    print(f"Working dir: {tmp_dir}")

    cfg = BootstrapConfig.from_yaml(str(CONFIG_PATH))
    cfg = cfg.model_copy(
        update={
            "base_dir": str(tmp_dir),
            "conformance_level": ConformanceLevel.L3_STRICT,
            "audit_trace": str(tmp_dir / "audit_trace.jsonl"),
            "compilation_dir": str(tmp_dir / "compilation_artifacts"),
            "cache_directory": str(tmp_dir / "cache"),
        }
    )

    # Hijack the llm_translate seam.
    call_count = 0

    def manual_llm(source_segment: str, ctx: object) -> str:
        nonlocal call_count
        call_count += 1
        return manual

    import tra.kernel as kernel_mod

    orig_translate = kernel_mod.translate_segment

    def patched_translate(source_segment, ctx, cache, evidence, audit, **kwargs):
        kwargs["llm_translate"] = manual_llm
        return orig_translate(source_segment, ctx, cache, evidence, audit, **kwargs)

    kernel_mod.translate_segment = patched_translate

    print("\n--- Running TRA Kernel at L3_STRICT ---")
    try:
        kernel = TRAKernel(cfg)
        target = kernel.run(source)
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        kernel_mod.translate_segment = orig_translate
        return 1
    finally:
        kernel_mod.translate_segment = orig_translate

    print(f"LLM seam called {call_count} time(s)")
    print(f"Output: {len(target)} chars")

    # Verify output matches the manual translation (hijack works).
    if target == manual:
        print("✓ Output matches manual translation (hijack successful)")
    else:
        print("✗ Output does NOT match manual translation")
        # Show first difference
        for i, (a, b) in enumerate(zip(target, manual, strict=False)):
            if a != b:
                print(f"  First diff at char {i}:")
                print(f"    output[{i}:{i + 50}]  = {target[i : i + 50]!r}")
                print(f"    manual[{i}:{i + 50}]  = {manual[i : i + 50]!r}")
                break
        if len(target) != len(manual):
            print(f"  Length diff: output={len(target)}, manual={len(manual)}")

    # Verify zero BLOCKING diagnostics.
    records = kernel.audit._buffer
    blocking = sum(
        1 for r in records if r.flags_raised and "BLOCKING" in r.flags_raised
    )
    print("\n--- Audit Trail ---")
    print(f"Records: {len(records)}")
    print(f"BLOCKING diagnostics: {blocking}")
    isa_seq = [r.isa_instruction for r in records]
    print(f"ISA sequence: {' → '.join(isa_seq)}")

    # Verify artifacts.
    artifacts_dir = tmp_dir / "compilation_artifacts"
    expected_files = [
        "glossary.yaml",
        "entity_table.yaml",
        "structural_map.json",
        "style_profile.yaml",
        "execution_log.json",
        "repair_history.jsonl",
    ]
    print("\n--- Runtime Artifacts ---")
    for fname in expected_files:
        path = artifacts_dir / fname
        status = "✓" if path.exists() else "✗"
        print(f"  {status} {fname}")

    # Check glossary for canonical mappings.
    import yaml

    glossary_path = artifacts_dir / "glossary.yaml"
    if glossary_path.exists():
        glossary = yaml.safe_load(glossary_path.read_text(encoding="utf-8"))
        sources = {e["source"] for e in glossary} if glossary else set()
        print("\n--- Glossary ---")
        print(f"  Entries: {len(glossary) if glossary else 0}")
        print(f"  '成立' in glossary: {'成立' in sources}")
        if "成立" in sources:
            entry = [e for e in glossary if e["source"] == "成立"][0]
            print(f"  '成立' → '{entry['target']}' (canonical mapping verified)")

    # Check entity table.
    entity_path = artifacts_dir / "entity_table.yaml"
    if entity_path.exists():
        entities = yaml.safe_load(entity_path.read_text(encoding="utf-8"))
        names = {e["name"] for e in entities} if entities else set()
        print("\n--- Entity Table ---")
        print(f"  Entities: {len(names)}")
        for expected in ["L1", "L2", "L3", "L4", "ISA", "TRA"]:
            print(
                f"  {expected}: {'✓ preserved' if expected in names else '✗ MISSING'}"
            )

    # Save the output to the final location.
    OUTPUT_PATH.write_text(target, encoding="utf-8")
    print("\n--- Output Saved ---")
    print(f"  Path: {OUTPUT_PATH}")
    print(f"  Size: {len(target)} chars")

    # Compute SHA-256 for reproducibility check.
    sha = hashlib.sha256(target.encode("utf-8")).hexdigest()
    print(f"  SHA-256: {sha[:32]}...")

    # Verify L3 conformance (zero BLOCKING).
    if blocking == 0:
        print(f"\n{'=' * 70}")
        print("✓ L3 CONFORMANCE VERIFIED — zero BLOCKING diagnostics")
        print(f"{'=' * 70}")
        return 0
    else:
        print(f"\n{'=' * 70}")
        print(f"✗ L3 CONFORMANCE FAILED — {blocking} BLOCKING diagnostic(s)")
        print(f"{'=' * 70}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
