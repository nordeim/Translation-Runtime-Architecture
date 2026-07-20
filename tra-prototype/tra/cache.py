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

TRA-079 (round 5): cache values are HMAC-SHA256 signed to detect tampering.
An attacker who can write to the cache directory could otherwise inject
bogus translations. The HMAC key is a fixed app-level secret (defense-in-
depth; the cache directory is assumed trusted per the single-user-dev
threat model).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from .memory import Entity, GlossaryEntry, PolicyPriority

if TYPE_CHECKING:
    # Avoid a hard runtime dependency on diskcache when the cache is
    # disabled (enabled=False). The type annotation is used by mypy --strict
    # to catch typos in self._cache.* method calls (TRA-B7-004).
    import diskcache

# TRA-079 (round 5): fixed app-level HMAC secret. This is NOT cryptographically
# secret (it's in the source code), but it protects against an attacker who
# can write to the cache directory but not read the source code. For a stronger
# threat model, derive the key from an environment variable or a per-install
# secret generated at first run.
_CACHE_HMAC_KEY = b"tra-prototype-cache-integrity-key-v1"


def _sign_value(value: str) -> str:
    """Return the HMAC-SHA256 signature of `value` as a hex string."""
    return hmac.new(_CACHE_HMAC_KEY, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _verify_signature(value: str, expected_hmac: str) -> bool:
    """Return True if the HMAC of `value` matches `expected_hmac`."""
    actual = _sign_value(value)
    return hmac.compare_digest(actual, expected_hmac)


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
    """A cached translation decision with its evidence references.

    TRA-A7-001 (round 7): `audit_side_effects` captures EXCEPTION_HANDLER
    audit records emitted during the cache-miss translation (e.g., UnknownTerm
    records for unrecognized CJK tokens). On cache hit, these records are
    re-emitted via `audit.append(...)` so the L4 audit trail remains complete
    across warm-cache runs. Previously the cache-hit early-return at
    isa.py:461-465 bypassed emission entirely, so the L4 audit trail was
    complete only on the first run after a cache invalidation.
    """

    translation: str
    evidence_ids: list[str] = Field(default_factory=list)
    cache_hit: bool = Field(default=False, description="True if served from cache")
    created_at: str | None = None
    # JSON-serializable audit side-effects. Each entry is a dict with keys:
    #   isa_instruction: str, input_hash: str, evidence_chain: list[str],
    #   artifact_snapshot: dict, flags_raised: list[str] | None
    audit_side_effects: list[dict[str, Any]] = Field(default_factory=list)


class TranslationCache:
    """SQLite-backed deterministic cache (diskcache). No TTL by default."""

    def __init__(self, directory: str | Path, enabled: bool = True) -> None:
        self.directory = Path(directory)
        self.enabled = enabled
        # TRA-B7-004 (round 7): typed as "diskcache.Cache | None" (was Any)
        # so mypy --strict catches typos in self._cache.* method calls.
        # The diskcache import is local to __init__ (runtime) and to
        # TYPE_CHECKING (static analysis) to avoid a hard dependency when
        # enabled=False.
        self._cache: diskcache.Cache | None = None
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
        # insecure deserialization (OWASP A08).
        # TRA-079 (round 5): cache values are HMAC-signed. Format:
        # "{hmac_hex}:{json_value}". Verify the HMAC before parsing; if
        # verification fails (tampered entry), treat as cache miss.
        # TRA-B7-003 (round 7): non-string cache values (e.g. pickle-
        # deserialized dicts from an attacker who can write to the cache
        # directory) must be treated as cache misses, NOT passed to
        # model_validate(). The previous `else` branch accepted any non-
        # string value, re-opening the pickle deserialization path. Removed.
        if not isinstance(raw, str):
            # Non-string value (pickle-deserialized dict, list, int, etc.)
            # — treat as cache miss. The next set() will overwrite with
            # the HMAC-signed JSON format.
            return None
        # Check for HMAC prefix (format: "{hmac}:{value}").
        if ":" not in raw or len(raw.split(":", 1)[0]) != 64:
            # Old-format entry (no HMAC) — treat as cache miss.
            # The next set() will write the HMAC-signed format.
            return None
        hmac_part, _, value_part = raw.partition(":")
        if not _verify_signature(value_part, hmac_part):
            # Tampered entry — treat as cache miss (don't crash).
            return None
        import json

        parsed = json.loads(value_part)
        result = TranslationResult.model_validate(parsed)
        result.cache_hit = True
        return result

    def set(self, key: str, result: TranslationResult) -> None:
        if not self.enabled or self._cache is None:
            return
        # TRA-077: store JSON string, NOT model_dump() dict. diskcache uses
        # pickle by default for non-string values, which allows arbitrary
        # code execution on cache load (OWASP A08). Storing a JSON string
        # makes the cache safe: json.loads() cannot execute code.
        # TRA-079 (round 5): sign the JSON value with HMAC-SHA256 to detect
        # tampering. Format: "{hmac_hex}:{json_value}".
        value = result.model_dump_json()
        signature = _sign_value(value)
        self._cache.set(key, f"{signature}:{value}", expire=None)

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
