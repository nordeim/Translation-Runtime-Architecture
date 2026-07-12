"""Phase 2.0 / 4 tests: ZH-EN Language Module."""

from __future__ import annotations

from tra.modules.zh_en import ZHENModule


def test_zh_en_glossary_canonical():
    mod = ZHENModule()
    g = mod.get_glossary_mappings()
    assert g["成立"] == "Confirmed"
    assert g["执行环境"] == "execution environment"
    assert g["高度可信"] == "highly credible"


def test_zh_en_epistemic_lexicon_exact():
    mod = ZHENModule()
    # Epistemic certainty preserved exactly — no strengthening/weakening.
    assert mod.epistemic_target("成立") == "Confirmed"
    assert mod.epistemic_target("高度可信") == "highly credible"
    assert mod.epistemic_target("可能") == "may"
    assert mod.epistemic_target("unknown-term") is None


def test_zh_en_forbidden_drift_targets():
    mod = ZHENModule()
    # 成立 -> Valid/True/Correct are drift (must be flagged).
    assert mod.is_forbidden("成立", "Valid")
    assert mod.is_forbidden("成立", "True")
    # canonical target is not forbidden.
    assert not mod.is_forbidden("成立", "Confirmed")


def test_zh_en_style_profile():
    mod = ZHENModule()
    sp = mod.get_style_profile()
    assert sp.voice
    assert (
        "Confirmed" in sp.epistemic_mapping.values()
        or sp.epistemic_mapping.get("成立") == "Confirmed"
    )


def test_zh_en_entity_hints():
    mod = ZHENModule()
    assert mod.entity_type_hint("RustVMM").value == "product"
    assert mod.entity_type_hint("Firecracker").value == "product"
