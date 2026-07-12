# TRA Prototype Engine

A Phase 0–5 reference implementation of **TRA v1.0** (Translation Runtime
Architecture) — a normative design for high-fidelity technical translation
engines. This engine is conformant with the Kernel / Memory Model / ISA / Policy
Engine of the spec, with a deterministic ZH↔EN Language Module wired in.

The translation core is **deterministic** (glossary + entity + epistemic
substitution + curated rule layers). That makes every ISA contract unit-
testable without an LLM. An optional `llm_translate` seam (Phase 6.5) can
override the rule path for fluent phrasing with graceful degradation.

## Install

```bash
cd tra-prototype
python -m venv .venv && . .venv/bin/activate
pip install -e .
```

## Commands

```bash
# Run the full TRA pipeline (Kernel state machine) on a document.
tra_cli.py translate examples/security_advisory_zh.md -o out.md

# Standalone verifier: audit a candidate OUTPUT against SOURCE (no re-translate).
# Exits 0 if zero BLOCKING diagnostics at the conformance level; else 1.
tra_cli.py validate examples/security_advisory_zh.md out.md --level L3

# Summarize an audit trace (one AuditRecord per ISA instruction).
tra_cli.py audit ./audit_trace.jsonl --format summary

# Invalidate the deterministic cache (no TTL by default).
tra_cli.py cache-clear [--pattern <glob>]
```

`config.yaml` is the `tvm_bootstrap` (Immutable Config segment): language
pair, domain, conformance level, model identity (feeds the cache key), cache,
repair retry budget, and artifact output paths.

## Architecture

| Layer | Module | Role |
| :--- | :--- | :--- |
| Kernel | `tra/kernel.py` | Immutable sequential state machine. Runs the six ISA instructions in canonical order. |
| ISA | `tra/isa.py` | `ANALYZE_DOCUMENT`, `BUILD_GLOSSARY`, `BUILD_ENTITY_TABLE`, `TRANSLATE_SEGMENT`, `VERIFY_OUTPUT`, `REPAIR_SEGMENT`. |
| Memory | `tra/memory.py` | Runtime Context + immutable segments (config, structural map, glossary, entities, style). |
| Policy | `tra/config.py` | Immutable priority stack (Factual → Structural → Entity → Terminological → Epistemic → Fluency). |
| Module | `tra/modules/zh_en.py` | ZH↔EN canonical lexicon + rule layers (parataxis→hypotaxis, nominalization, punctuation, 四字格). |
| Registry | `tra/modules/registry.py` | Pluggable extension point — new language pairs register here without touching core. |
| Audit | `tra/diagnostics.py` | Append-only JSONL evidence trail; VERIFY emits evidence-based diagnostics (never self-scores). |
| Cache | `tra/cache.py` | Deterministic, content-addressable cache → byte-identical output for identical context. |

## Conformance gate (L3)

A translation conforms at L3/L4 iff `VERIFY_OUTPUT` raises **zero BLOCKING**
diagnostics. Run the benchmark suite (seed cases from `TRA-BENCHMARK-SUITE.md`):

```bash
pytest tests/test_benchmark.py   # S/F/T/D/E cases + regression; asserts zero BLOCKING
```

## Test + lint

```bash
pytest                    # full suite (anchor, isa, kernel, modules, validate, benchmark)
ruff check . && ruff format --check .
mypy --strict tra
```

## Known gaps (not yet implemented)

- **LLM seam** (`translate_segment(..., llm_translate=...)`) is wired but not
  called — phrasing is rule-based (e.g. "may Confirmed" reads literally).
- **Inline-code glossary substitution** is not yet suppressed (S-03): terms
  inside backticks are still run through the glossary.
- **Phase 6** (exception hardening, human-in-the-loop, structlog, L4 evidence
  tracing) is pending.
