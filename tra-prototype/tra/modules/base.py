"""Base class for TRA modules (Spec §9 plug-ins).

TRA-043: defines a `LanguageModuleProtocol` that types the structural contract
of a language module. This closes the type-safety hole where
`RuntimeContext.module: Any` allowed mypy --strict to miss typos in method
names (e.g. get_glossary_mappings vs get_glossary_mapping).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LanguageModuleProtocol(Protocol):
    """Structural contract for a Language Module (Spec §9).

    A language module provides canonical terminology mappings, a style
    profile, forbidden-target checks, entity-type hints, and bilingual
    rule layers. The ZHENModule is the bundled reference implementation.

    Modules must NOT alter the Kernel or ISA — only provide data/behaviour
    consumed by the Runtime Context.
    """

    # Module metadata (used by the registry for dispatch).
    name: str
    kind: str

    def get_glossary_mappings(self) -> dict[str, str]:
        """Return canonical source-term -> target-term mappings."""
        ...

    def get_style_profile(self) -> object:
        """Return a StyleProfile for the active language pair."""
        ...

    def is_forbidden(self, source: str, target: str) -> bool:
        """True if `source -> target` is a known forbidden drift mapping."""
        ...

    def get_forbidden_targets(self) -> dict[str, str]:
        """Return the forbidden-target mappings (source -> 'tgt1/tgt2/...')."""
        ...

    def entity_type_hint(self, token: str) -> object | None:
        """Return an EntityType hint for `token`, or None if no hint."""
        ...

    def apply_zh_rules(self, text: str) -> str:
        """Apply ZH→EN rule layer (parataxis→hypotaxis, nominalization, etc.)."""
        ...

    def apply_rules(self, source: str, direction: str) -> str:
        """Dispatch to apply_zh_rules or apply_en_rules based on direction."""
        ...
