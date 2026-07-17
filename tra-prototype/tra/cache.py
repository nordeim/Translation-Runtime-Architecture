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


def _hash_canonical_json(obj: Any) -> str:
    """SHA-256 of the canonical JSON serialization of `obj`.

    The name reflects what the function actually does: it hashes the
    canonical JSON (sorted keys, UTF-8) of the input. It does NOT sort
    lists — only dict keys are sorted by ``json.dumps(sort_keys=True)``.
    For order-independent hashing of collections, use ``_hash_set``.
    """
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _hash_set(items: list[Any]) -> str:
    """Order-independent hash of a collection.

    Each item is hashed canonically, then the sorted set of hashes is hashed
    again. This makes the cache key independent of list ordering (CACHE_STRATEGY.md).
    """
    per_item = sorted(_hash_canonical_json(item) for item in items)
    return _hash_canonical_json(per_item)


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
            "policy_stack_hash": _hash_canonical_json(
                [p.value for p in self.policy_stack]
            ),
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
        # TRA-077: cache stores JSON strings (not pickle/dict) to prevent
        # insecure deserialization (OWASP A08). Parse the JSON string back
        # into a TranslationResult.
        if isinstance(raw, str):
            import json

            parsed = json.loads(raw)
            result = TranslationResult.model_validate(parsed)
        else:
            # Backward compat: old pickle entries (dict). Migrate on next set.
            result = TranslationResult.model_validate(raw)
        result.cache_hit = True
        return result

    def set(self, key: str, result: TranslationResult) -> None:
        if not self.enabled or self._cache is None:
            return
        # TRA-077: store JSON string, NOT model_dump() dict. diskcache uses
        # pickle by default for non-string values, which allows arbitrary
        # code execution on cache load (OWASP A08). Storing a JSON string
        # makes the cache safe: json.loads() cannot execute code.
        self._cache.set(key, result.model_dump_json(), expire=None)

    def invalidate(self, pattern: str | None = None) -> int:
        """Manual invalidation (CLI: tra cache-clear). No TTL otherwise.

        Returns the number of entries deleted. If `pattern` is supplied it
        is treated as an ``fnmatch`` glob (e.g. ``"translation:*"``); the
        previous implementation passed the pattern to ``diskcache.delete()``
        which takes a LITERAL key — silently deleting nothing (TRA-011).
        """
        if not self.enabled or self._cache is None:
            return 0
        if pattern:
            import fnmatch

            deleted = 0
            for key in list(self._cache.iterkeys()):
                if fnmatch.fnmatch(key, pattern) and self._cache.delete(key):
                    deleted += 1
            return deleted
        # No pattern: clear everything.
        count = len(self._cache)
        self._cache.clear()
        return count
