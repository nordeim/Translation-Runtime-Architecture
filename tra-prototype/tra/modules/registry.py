"""Module registry — pluggable Language/Domain/Formatting modules (Spec §9).

Modules extend runtime behaviour without touching the Kernel or ISA.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleInterface:
    """Contract a plug-in module must satisfy (implementation_plan.md §4.4)."""

    name: str
    kind: str  # "language" | "domain" | "formatting"
    get_glossary_mappings: Callable[[], dict[str, str]] = lambda: {}
    get_style_profile: Callable[[], object] = lambda: None
    apply_rules: Callable[[str, str], str] = lambda src, _dir: src
    metadata: dict[str, Any] = field(default_factory=dict)


class ModuleRegistry:
    """Loads and dispatches TRA modules (Spec §9, mutable/extensible)."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleInterface] = {}

    def register(self, module: ModuleInterface) -> None:
        self._modules[module.name] = module

    def get(self, name: str) -> ModuleInterface:
        if name not in self._modules:
            raise KeyError(f"Module '{name}' not registered")
        return self._modules[name]

    def all(self) -> list[ModuleInterface]:
        return list(self._modules.values())
