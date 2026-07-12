"""Shared pytest fixtures for the tra-prototype test suite."""

from __future__ import annotations

import pytest
from tra.cache import CacheKeyContext
from tra.config import BootstrapConfig
from tra.diagnostics import EvidenceRecord, EvidenceRegistry, EvidenceType
from tra.memory import (
    Entity,
    EntityType,
    GlossaryEntry,
    PolicyPriority,
)


@pytest.fixture
def sample_glossary() -> list[GlossaryEntry]:
    return [
        GlossaryEntry(source="成立", target="Confirmed", rule_id="ZH-EN-RULE#05"),
        GlossaryEntry(source="执行环境", target="execution environment"),
    ]


@pytest.fixture
def sample_entities() -> list[Entity]:
    return [
        Entity(name="RustVMM", type=EntityType.PRODUCT),
        Entity(name="v0.5.0", type=EntityType.VERSION),
    ]


@pytest.fixture
def cache_context(
    sample_glossary: list[GlossaryEntry], sample_entities: list[Entity]
) -> CacheKeyContext:
    return CacheKeyContext(
        source_text="系统成立。",
        glossary=sample_glossary,
        entities=sample_entities,
        model_endpoint="openai/gpt-4o-mini",
        model_version="2024-07-18",
        policy_stack=[
            PolicyPriority.FACTUAL_INTEGRITY,
            PolicyPriority.STRUCTURAL_INTEGRITY,
            PolicyPriority.ENTITY_PRESERVATION,
            PolicyPriority.TERMINOLOGICAL_CONSISTENCY,
            PolicyPriority.EPISTEMIC_FIDELITY,
            PolicyPriority.TARGET_FLUENCY,
        ],
    )


@pytest.fixture
def evidence_registry() -> EvidenceRegistry:
    return EvidenceRegistry()


@pytest.fixture
def sample_evidence(evidence_registry: EvidenceRegistry) -> EvidenceRecord:
    rec = EvidenceRecord(
        type=EvidenceType.TERM_MATCH,
        module="modules.zh_en",
        source_span="成立",
        target_span="Confirmed",
        rationale="Matched epistemic lexicon: 成立 -> Confirmed (never Valid/True)",
        rule_id="ZH-EN-RULE#05",
    )
    evidence_registry.add(rec)
    return rec


@pytest.fixture
def config() -> BootstrapConfig:
    return BootstrapConfig.from_yaml("config.yaml")
