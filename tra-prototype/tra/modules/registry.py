"""Module registry — pluggable Language/Domain/Formatting modules (Spec §9).

Modules extend runtime behaviour without touching the Kernel or ISA.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleInterface:
    """Contract a plug-in module must satisfy (implementation_plan.md §4.4).

    TRA-096 (round 3): this dataclass must carry ALL methods required by
    LanguageModuleProtocol (base.py). Previously it only had 3 Callable
    fields (get_glossary_mappings, get_style_profile, apply_rules), which
    caused Pydantic's RuntimeContext.module: LanguageModuleProtocol
    validation to reject ModuleInterface instances as "not an instance of
    LanguageModuleProtocol". The 4 added fields (is_forbidden,
    get_forbidden_targets, entity_type_hint, apply_zh_rules) close that
    gap so as_interface() → register() → TRAKernel(registry=) works.
    """

    name: str
    kind: str  # "language" | "domain" | "formatting"
    get_glossary_mappings: Callable[[], dict[str, str]] = lambda: {}
    get_style_profile: Callable[[], object] = lambda: None
    apply_rules: Callable[[str, str], str] = lambda src, _dir: src
    # TRA-096: the 4 fields below are required by LanguageModuleProtocol.
    is_forbidden: Callable[[str, str], bool] = lambda _src, _tgt: False
    get_forbidden_targets: Callable[[], dict[str, str]] = lambda: {}
    entity_type_hint: Callable[[str], object | None] = lambda _token: None
    apply_zh_rules: Callable[[str], str] = lambda text: text
    metadata: dict[str, Any] = field(default_factory=dict)


class ModuleRegistry:
    """Loads and dispatches TRA modules (Spec §9, mutable/extensible)."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleInterface] = {}

    def register(self, module: ModuleInterface) -> None:
        """Register a module. TRA-097: validate the module satisfies the
        LanguageModuleProtocol at registration time so errors surface with
        an actionable message, not as an opaque AttributeError later.
        """
        from .base import LanguageModuleProtocol

        if not isinstance(module, LanguageModuleProtocol):
            required = (
                "get_glossary_mappings",
                "get_style_profile",
                "is_forbidden",
                "get_forbidden_targets",
                "entity_type_hint",
                "apply_zh_rules",
                "apply_rules",
            )
            missing = [m for m in required if not hasattr(module, m)]
            mod_name = getattr(module, "name", "?")
            raise TypeError(
                f"Module '{mod_name}' does not satisfy "
                f"LanguageModuleProtocol. Missing methods: {missing}"
            )
        self._modules[module.name] = module

    def get(self, name: str) -> ModuleInterface:
        if name not in self._modules:
            raise KeyError(f"Module '{name}' not registered")
        return self._modules[name]

    def all(self) -> list[ModuleInterface]:
        return list(self._modules.values())


def build_default_registry() -> ModuleRegistry:
    """Construct the canonical registry with bundled modules (Phase 4.1.2).

    New modules (e.g. an `fr-en` bridge) register here without touching the
    Kernel or ISA — this is the one sanctioned extension point.
    """
    from .zh_en import ZHENModule

    registry = ModuleRegistry()
    registry.register(ZHENModule().as_interface())
    return registry


def registry_for_language_pair(pair: str) -> ModuleRegistry:
    """Return a registry scoped to one language pair (e.g. 'ZH -> EN')."""
    registry = build_default_registry()
    if "->" not in pair:
        return registry
    source_lang = pair.split("->", 1)[0].strip().lower()
    scoped = ModuleRegistry()

    for mod in registry.all():
        if mod.kind != "language":
            scoped.register(mod)
            continue
        direction = (
            str(mod.metadata.get("direction", "")).split("->", 1)[0].strip().lower()
        )
        if direction == source_lang:
            scoped.register(mod)
    return scoped
