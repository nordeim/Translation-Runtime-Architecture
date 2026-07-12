"""Deterministic cache foundation (CACHE_STRATEGY.md).

Purpose: externalize translation decisions to a content-addressable cache so
that identical translation *context* yields byte-identical output — required
for reproducibility (L4) and recommended for L3 robustness.

Cache key = SHA-256 over canonical (sorted-key) JSON of the FULL translation
context: source text + glossary hash + entity hash + model identity +
policy-stack hash. Changing ANY of these (incl. policy re-ordering, model
upgrade) invalidates prior entries automatically.

Scope: cache only atomic ops (TRANSLATE_SEGMENT, REPAIR_SEGMENT), never a
whole document. No TTL — technical facts are static.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .memory import Entity, GlossaryEntry, PolicyPriority


def _canonical_json(payload: Any) -> str:
    """Deterministic JSON serialization (sorted keys, UTF-8)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _hash_sorted(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _hash_set(items: list[Any]) -> str:
    """Order-independent hash of a collection.

    Each item is hashed canonically, then the sorted set of hashes is hashed
    again. This makes the cache key independent of list ordering (CACHE_STRATEGY.md).
    """
    per_item = sorted(_hash_sorted(item) for item in items)
    return _hash_sorted(per_item)


class CacheKeyContext(BaseModel):
    """The full translation context that defines cache identity (CACHE_STRATEGY.md)."""

    source_text: str
    glossary: list[GlossaryEntry] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    model_endpoint: str = ""
    model_version: str = ""
    policy_stack: list[PolicyPriority] = Field(default_factory=list)

    def key(self) -> str:
        """SHA-256 of the canonical context payload."""
        payload = {
            "source": self.source_text,
            "glossary_hash": _hash_set([g.model_dump() for g in self.glossary]),
            "entity_hash": _hash_set([e.model_dump() for e in self.entities]),
            "model_endpoint": self.model_endpoint,
            "model_version": self.model_version,
            "policy_stack_hash": _hash_sorted([p.value for p in self.policy_stack]),
        }
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


class TranslationResult(BaseModel):
    """A cached translation decision with its evidence references."""

    translation: str
    evidence_ids: list[str] = Field(default_factory=list)
    cache_hit: bool = Field(default=False, description="True if served from cache")
    created_at: str | None = None


class TranslationCache:
    """SQLite-backed deterministic cache (diskcache). No TTL by default."""

    def __init__(self, directory: str | Path, enabled: bool = True) -> None:
        self.directory = Path(directory)
        self.enabled = enabled
        self._cache: Any = None
        if self.enabled:
            import diskcache

            self.directory.mkdir(parents=True, exist_ok=True)
            self._cache = diskcache.Cache(str(self.directory))

    def get(self, key: str) -> TranslationResult | None:
        if not self.enabled or self._cache is None:
            return None
        raw = self._cache.get(key)
        if raw is None:
            return None
        result = TranslationResult.model_validate(raw)
        result.cache_hit = True
        return result

    def set(self, key: str, result: TranslationResult) -> None:
        if not self.enabled or self._cache is None:
            return
        self._cache.set(key, result.model_dump(mode="json"), expire=None)

    def invalidate(self, pattern: str | None = None) -> None:
        """Manual invalidation (CLI: tra cache-clear). No TTL otherwise."""
        if not self.enabled or self._cache is None:
            return
        if pattern:
            # diskcache.delete supports glob patterns
            self._cache.delete(pattern)
        else:
            self._cache.clear()
