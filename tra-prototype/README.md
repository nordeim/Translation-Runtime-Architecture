# TRA Prototype Engine

A Phase 0–6 reference implementation of **TRA v1.0** (Translation Runtime
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
pip install -e ".[dev]"   # [dev] required for ruff/mypy/pytest quality gates
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
- **Inline-code glossary substitution** IS now suppressed (TRA-001 partial):
  fenced and inline code blocks are protected as no-translate zones. Full
  per-leaf segment translation is still deferred.
- **`structlog`** is a listed dependency but the engine uses the plain
  `AuditTrail` (no structured/correlation-ID logging) — Phase 6.3.1 open.
- **Segment-level parallelism** (`asyncio`) is not implemented — Phase 6.5.1
  open.
- **Cross-run glossary/entity caching** — only the translation output is
  cached across runs; glossary/entity tables are rebuilt per run (Phase 6.5.2
  open).
- **Phase 7** (ADRs, API reference, module authoring guide, conformance
  self-audit) has not started.
- **TRANSLATE_SEGMENT** currently operates on the whole document rather than
  per leaf segment (TRA-001 partial); the kernel passes the full source to
  `translate_segment`. This affects cache granularity,
  `RepairAttempt.segment_index`, and the L4 line-by-line trace.
- **Module registry** (TRA-002, fixed in kernel): the kernel now selects the
  language module from the registry when supplied (`TRAKernel(cfg, registry=)`);
  however, `tra_cli.py translate` does not yet pass a registry, so the CLI
  still falls back to `ZHENModule`.
- **Exception recovery** (TRA-004, partial): `BrokenMarkdown` and
  `EntityAmbiguity` now route through `_recover`; however,
  `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are still never raised
  in production code paths (TRA-038).
- **Policy Engine scaffolding** (TRA-006, half-fix): terminology severity is
  now policy-aware but `PolicyResolver` is never invoked in production
  `verify_output`.
- **Dependency hygiene** (TRA-017): `litellm`, `structlog`,
  `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio` are listed
  but unused.
- **Benchmark coverage** (TRA-031, improved): 22 of 24 spec cases implemented
  (S-03 and E-03 still missing); spec target is 100+.

See `docs/audit/round2/TRA_audit_findings_register_r2.xlsx` for the full
41-finding Round 2 audit register and
`docs/audit/round2/TRA_Prototype_Audit_Report_r2.docx` for the narrative
report. Round 1 deliverables are in `docs/audit/` (top level).
