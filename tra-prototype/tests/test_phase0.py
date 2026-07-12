"""Phase 0 smoke tests: cache determinism, evidence registry, config, policy.

These validate the foundation the plan's end-of-Phase-0 / Phase-1 checkpoints
depend on. No LLM calls; pure deterministic logic.
"""

from __future__ import annotations

from tra.anchor import AnchorRegistry, generate_github_slug
from tra.cache import TranslationCache, TranslationResult
from tra.diagnostics import (
    AuditTrail,
    EvidenceRecord,
    EvidenceType,
)
from tra.memory import (
    NodeKind,
    PolicyPriority,
    RuntimeContext,
    StructuralMap,
    StructuralNode,
)
from tra.policy import PolicyResolver

# --- Cache determinism (CACHE_STRATEGY.md / Phase 5.3.4) ---


def test_cache_key_is_deterministic_and_order_independent(cache_context):
    k1 = cache_context.key()
    k2 = cache_context.key()
    assert k1 == k2  # identical context -> identical key

    # Reordering glossary entries must NOT change the key (sorted-hash).
    cache_context.glossary.reverse()
    assert k1 == cache_context.key()


def test_cache_key_changes_with_model_or_policy(cache_context):
    base = cache_context.key()
    cache_context.model_version = "2025-01-01"
    assert cache_context.key() != base

    cache_context.model_version = "2024-07-18"
    assert cache_context.key() == base

    # Policy stack reorder -> different hash (automatic invalidation).
    cache_context.policy_stack.reverse()
    assert cache_context.key() != base


def test_cache_round_trip(tmp_path):
    cache = TranslationCache(tmp_path / "cache", enabled=True)
    key = "abc123"
    result = TranslationResult(translation="Confirmed.", evidence_ids=["ev_1"])
    cache.set(key, result)
    got = cache.get(key)
    assert got is not None
    assert got.translation == "Confirmed."
    assert got.cache_hit is True

    cache.invalidate()
    assert cache.get(key) is None


# --- Evidence registry & "never self-score" invariant ---


def test_evidence_registry_append_only(evidence_registry, sample_evidence):
    assert sample_evidence.id in evidence_registry
    assert evidence_registry.get(sample_evidence.id) is sample_evidence
    # confidence_note, if present, must never be read for routing:
    rec = EvidenceRecord(
        type=EvidenceType.LLM_DECISION,
        module="modules.zh_en",
        source_span="x",
        target_span="y",
        rationale="test",
        confidence_note=0.1,  # low score, but MUST NOT trigger any routing
    )
    evidence_registry.add(rec)
    assert len(evidence_registry.all()) == 2


# --- Audit trail JSONL append-only ---


def test_audit_trail_append_and_load(tmp_path):
    trail = AuditTrail(tmp_path / "audit_trace.jsonl")
    trail.append("TRANSLATE_SEGMENT", "hash1", ["ev_1"], {"seg": 1})
    trail.append("VERIFY_OUTPUT", "hash1", ["ev_1"], flags_raised=["BLOCKING"])
    trail.flush()

    loaded = AuditTrail(tmp_path / "audit_trace.jsonl").load()
    assert len(loaded) == 2
    assert loaded[1].flags_raised == ["BLOCKING"]
    assert loaded[0].sequence_id == 0


# --- Config (tvm_bootstrap) ---


def test_config_loads(config):
    assert config.conformance_level.value == "L3_STRICT"
    assert config.language_pair == "ZH -> EN"
    assert len(config.policy_stack) == 6
    assert config.policy_stack[0] == PolicyPriority.FACTUAL_INTEGRITY


# --- Policy engine (immutable stack, scope never reorders) ---


def test_policy_resolver_honors_stack():
    resolver = PolicyResolver(
        [
            PolicyPriority.FACTUAL_INTEGRITY,
            PolicyPriority.STRUCTURAL_INTEGRITY,
            PolicyPriority.ENTITY_PRESERVATION,
            PolicyPriority.TERMINOLOGICAL_CONSISTENCY,
            PolicyPriority.EPISTEMIC_FIDELITY,
            PolicyPriority.TARGET_FLUENCY,
        ]
    )
    # Factual must beat Fluency even "inside a code block" — scope never reorders.
    assert (
        resolver.resolve(
            PolicyPriority.TARGET_FLUENCY, PolicyPriority.FACTUAL_INTEGRITY
        )
        == PolicyPriority.FACTUAL_INTEGRITY
    )
    assert resolver.wins(
        PolicyPriority.ENTITY_PRESERVATION, PolicyPriority.TERMINOLOGICAL_CONSISTENCY
    )
    assert not resolver.wins(
        PolicyPriority.TARGET_FLUENCY, PolicyPriority.ENTITY_PRESERVATION
    )


# --- Anchor slugify (ANCHOR_RESOLUTION.md / S-06) ---


def test_slugify_and_duplicate_resolution():
    reg = AnchorRegistry()
    s1 = reg.resolve_slug("System Setup")
    s2 = reg.resolve_slug("System Setup")  # duplicate
    assert s1 == "system-setup"
    assert s2 == "system-setup-1"


def test_github_slugify_unicode():
    assert generate_github_slug("  Hello   World! ") == "hello-world"


# --- Memory-model invariant: structural map node count ---


def test_structural_map_node_count():
    sm = StructuralMap(
        nodes=[
            StructuralNode(
                kind=NodeKind.HEADING,
                children=[StructuralNode(kind=NodeKind.PARAGRAPH)],
            ),
            StructuralNode(kind=NodeKind.PARAGRAPH),
        ]
    )
    assert sm.node_count == 3  # heading + nested paragraph + standalone paragraph


def test_runtime_context_defaults():
    rc = RuntimeContext()
    assert rc.glossary_cache == []
    assert rc.execution_log == []
