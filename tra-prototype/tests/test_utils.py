"""Phase 1.2 tests: entity extraction heuristics."""

from __future__ import annotations

from tra.memory import EntityType
from tra.utils import classify_entity, extract_entities


def test_version_token_classified():
    ents = extract_entities("Released v0.5.0 today")
    v = next(e for e in ents if e.name == "v0.5.0")
    assert v.type == EntityType.VERSION
    assert v.mutable is False


def test_product_token_classified():
    ents = extract_entities("RustVMM launched")
    prod = next(e for e in ents if e.name == "RustVMM")
    assert prod.type == EntityType.PRODUCT


def test_acronym_token_classified():
    ents = extract_entities("API and SDK support JSON")
    names = {e.name for e in ents}
    assert "API" in names and "SDK" in names and "JSON" in names
    assert all(e.type == EntityType.ACRONYM for e in ents if e.name in names)


def test_cli_flag_and_backtick_classified():
    ents = extract_entities("Run with --verbose or `kubectl apply`")
    names = {e.name for e in ents}
    assert "--verbose" in names
    assert all(e.type == EntityType.CLI for e in ents if e.name == "--verbose")


def test_plain_prose_words_not_entities():
    ents = extract_entities("The System is Stable and Configure runs")
    names = {e.name for e in ents}
    assert "The" not in names
    assert "System" not in names
    assert "Stable" not in names
    assert "Configure" not in names


def test_dedup_across_patterns():
    ents = extract_entities("API API SDK api")
    names = [e.name for e in ents]
    # API appears once; 'api' (lowercase) is not matched by ACRONYM_RE.
    assert names.count("API") == 1
    assert "SDK" in names


def test_classify_entity_dispatch():
    assert classify_entity("v1.2.3") == EntityType.VERSION
    assert classify_entity("P99") == EntityType.PRODUCT
    assert classify_entity("CPU") == EntityType.ACRONYM
    assert classify_entity("--flag") == EntityType.CLI
