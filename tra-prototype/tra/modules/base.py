"""Base class for TRA modules (Spec §9 plug-ins)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ModuleBase(ABC):
    """Base class for Language/Domain/Formatting modules.

    Modules must NOT alter the Kernel or ISA — only provide data/behaviour
    consumed by the Runtime Context.
    """

    name: str = "base"
    kind: str = "language"

    @abstractmethod
    def get_glossary_mappings(self) -> dict[str, str]:
        """Return canonical source-term -> target-term mappings."""

    @abstractmethod
    def get_style_profile(self) -> object:
        """Return a StyleProfile for the active language pair."""

    def apply_rules(self, source: str, direction: str) -> str:
        """Optional pre/post-processing hook. Default: identity."""
        return source
