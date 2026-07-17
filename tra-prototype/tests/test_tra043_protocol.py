"""Phase 3 Cycle 2 — TRA-043: LanguageModuleProtocol type safety.

TRA-043: RuntimeContext.module was typed as `Any`, a real type-safety hole.
mypy --strict could not catch typos in method names like get_glossary_mappings()
vs get_glossary_mapping(). This test verifies the LanguageModuleProtocol exists
and ZHENModule satisfies it.
"""

from __future__ import annotations


def test_language_module_protocol_exists_and_is_importable() -> None:
    """TRA-043: a LanguageModuleProtocol must be defined in modules/base.py
    and importable."""
    from tra.modules.base import LanguageModuleProtocol

    assert LanguageModuleProtocol is not None


def test_zhen_module_satisfies_protocol() -> None:
    """TRA-043: ZHENModule must satisfy the LanguageModuleProtocol — if it
    doesn't, mypy --strict would catch it (but runtime check here confirms
    the structural shape)."""
    from tra.modules.base import LanguageModuleProtocol
    from tra.modules.zh_en import ZHENModule

    mod = ZHENModule()
    # runtime_checkable protocols support isinstance checks
    assert isinstance(mod, LanguageModuleProtocol), (
        "ZHENModule does not satisfy LanguageModuleProtocol — missing method(s)"
    )


def test_runtime_context_module_typed_as_protocol() -> None:
    """TRA-043: RuntimeContext.module should be typed as the Protocol (not Any).
    Verify the type annotation is set correctly by inspecting the field."""
    from tra.memory import RuntimeContext

    # Get the type annotation for the 'module' field.
    # In Pydantic v2, field info is accessible via model_fields.
    field_info = RuntimeContext.model_fields.get("module")
    assert field_info is not None, "RuntimeContext has no 'module' field"
    # The annotation should reference the Protocol (not Any).
    annotation = field_info.annotation
    # The annotation may be Optional[Protocol] or Protocol | None.
    # Check that it's not just `Any`.
    annotation_str = str(annotation)
    assert "Any" not in annotation_str or "LanguageModuleProtocol" in annotation_str, (
        f"RuntimeContext.module is typed as {annotation_str}, expected "
        f"LanguageModuleProtocol | None (not Any) — TRA-043"
    )
