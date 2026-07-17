"""Phase 2.0 / 4 tests: ZH-EN Language Module + registry + rule layers."""

from __future__ import annotations

from tra.modules.registry import (
    ModuleInterface,
    build_default_registry,
    registry_for_language_pair,
)
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


# --- Phase 4.1: ModuleRegistry ---------------------------------------


def test_registry_default_contains_zh_en():
    reg = build_default_registry()
    assert reg.get("zh_en") is not None
    assert reg.get("zh_en").kind == "language"
    names = {m.name for m in reg.all()}
    assert "zh_en" in names


def test_registry_unknown_raises():
    reg = build_default_registry()
    try:
        reg.get("fr_en")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass


def test_registry_scoped_to_language_pair():
    reg = registry_for_language_pair("ZH -> EN")
    langs = {m.name for m in reg.all() if m.kind == "language"}
    assert "zh_en" in langs


def test_module_as_interface_contract():
    iface = ZHENModule().as_interface()
    assert isinstance(iface, ModuleInterface)
    assert iface.name == "zh_en"
    assert iface.get_glossary_mappings()["成立"] == "Confirmed"
    # Direction dispatches correctly through the interface.
    assert iface.apply_rules("系统成立。", "ZH -> EN") == "The system is Confirmed."


# --- Phase 4.2: ZH -> EN rule layers ---------------------------------


def test_zh_en_topic_comment_parataxis():
    mod = ZHENModule()
    # Topic-comment -> subject-predicate (parataxis -> hypotaxis).
    assert mod.apply_zh_rules("系统成立。") == "The system is Confirmed."


def test_zh_en_nominalization_verbalization():
    mod = ZHENModule()
    # Nominalized verb-object -> verb (glossary not applied here; that is the
    # ISA layer's responsibility).
    assert mod.apply_zh_rules("系统进行验证。") == "系统verify."


def test_zh_en_rule_layer_only_transforms_known_forms():
    mod = ZHENModule()
    # Mixed English passes through unchanged (no mistranslation drift).
    assert mod.apply_zh_rules("RustVMM is Confirmed.") == "RustVMM is Confirmed."


def test_zh_en_punctuation_normalization_half_width():
    mod = ZHENModule()
    # Glossary NOT applied here (ISA layer does that); only punctuation +
    # rule-layer forms. Full-width -> half-width.
    assert mod.apply_zh_rules("执行环境：A。") == "执行环境: A."


# --- Phase 4.3: EN -> ZH rule layers ---------------------------------


def test_en_zh_four_char_map():
    mod = ZHENModule()
    # Case-insensitive: the glossary already yields title-case 'Seamless
    # migration', which must round-trip into the 四字格 form.
    assert mod.apply_en_rules("Seamless migration completed") == "无缝迁移 completed"


def test_en_zh_passive_reduction():
    mod = ZHENModule()
    assert mod.apply_en_rules("It is confirmed.") == "It 已确认。"


def test_en_zh_punctuation_normalization_full_width():
    mod = ZHENModule()
    assert "，" in mod.apply_en_rules("Runtime environment, verified.")


# --- Phase 4.4: dispatch via apply_rules -----------------------------


def test_apply_rules_dispatches_by_direction():
    mod = ZHENModule()
    assert mod.apply_rules("系统成立。", "ZH -> EN") == "The system is Confirmed."
    assert "无缝迁移" in mod.apply_rules("Seamless migration", "EN -> ZH")
    # Unknown direction is identity.
    assert mod.apply_rules("系统成立。", "FR -> EN") == "系统成立。"
