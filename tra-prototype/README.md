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
python -m tra_cli translate examples/security_advisory_zh.md -o out.md

# Standalone verifier: audit a candidate OUTPUT against SOURCE (no re-translate).
# Exits 0 if zero BLOCKING diagnostics at the conformance level; else 1.
python -m tra_cli validate examples/security_advisory_zh.md out.md --level L3

# Summarize an audit trace (one AuditRecord per ISA instruction).
python -m tra_cli audit ./audit_trace.jsonl --format summary

# Invalidate the deterministic cache (no TTL by default).
python -m tra_cli cache-clear [--pattern <glob>]
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
| Policy | `tra/policy.py` | Immutable priority stack (Factual → Structural → Entity → Terminological → Epistemic → Fluency). |
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
- **Module registry** (TRA-002, fixed in kernel; TRA-099 FIXED in Round 4
  Batch 1 commit `e54b7a7`): the kernel selects the language module from the
  registry when supplied (`TRAKernel(cfg, registry=)`); `as_interface()`
  satisfies `LanguageModuleProtocol` (TRA-096 fixed in Round 3). The CLI's
  `translate` command now auto-builds the default registry and passes it to
  `TRAKernel` (TRA-099 fixed in round 4). The kernel's `_select_module` matches
  by full direction (TRA-F4-007 fixed in round 4).
- **Exception recovery** (TRA-004, partial; TRA-038 partial-fixed in round 4
  commit `d95c36d`): `BrokenMarkdown` routes through `_recover`;
  `build_entity_table` is wrapped in try/except (TRA-039); `route_exception`
  has an explicit `Unrecoverable` branch returning `BLOCKING + HALT` (TRA-044
  fixed in Round 2). All 3 previously-unreachable exception types are now wired
  in production (TRA-038 fixed in round 4 commit `d95c36d`): `UnknownTerm` is
  logged via `recover_unknown_term` (non-halting) when a CJK token has no
  glossary/entity/epistemic match; `CertaintyConflict` is raised in the LLM
  path when a forbidden drift target is detected; `EntityAmbiguity` is logged
  when a token matches multiple entity patterns and `entity_type_hint` returns
  None. Caveat: UnknownTerm/EntityAmbiguity bypass the kernel's `_recover`
  dispatcher (no EXCEPTION_HANDLER audit record; the L4 ambiguity_register
  still captures the entries) — TRA-A5-003 partial.
- **Policy Engine** (TRA-006 fixed in Round 3; TRA-072 partial-fixed in
  round 4 commit `78c9250`): `PolicyResolver` is now invoked for ALL 4
  severity decision pairs in `verify_output` (TRA-072 fixed in round 4 commit
  `78c9250`): Structural (P2) vs Fluency (P6), Entity (P3) vs Fluency (P6),
  Terminological (P4) vs Fluency (P6), Epistemic (P5) vs Fluency (P6).
  Monkeypatching `_POLICY_RESOLVER.wins` to return False drops ALL severities
  from BLOCKING to WARNING. Spec §5.2 universal arbitration contract is now
  met. Caveat: Factual Integrity (P1) is still never arbitrated — TRA-A5-013
  partial (no factual-integrity check exists in `verify_output`).
- **Dependency hygiene** (TRA-017, FIXED in Round 3 remediation commit
  `a3cd2c1`): the 6 unused dependencies (`litellm`, `structlog`,
  `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) were
  removed from `pyproject.toml`. Install footprint dropped from ~70 packages
  to ~15. (Note: `structlog` is no longer a listed dependency, so the Phase
  6.3.1 structured-logging gap is moot until `structlog` is re-added with a
  concrete integration plan.)
- **Benchmark coverage** (TRA-031, improved): 36 of 100+ spec target cases
  implemented (S-03 and E-03 added in round 4 remediation, TRA-092; +12 cases
  added in round 5 remediation covering tables, nested lists, blockquotes,
  HRs, ISO dates, numeric units, comparison operators, CVE advisories, API
  refs, and acronym ambiguity).
- **LLM seam** (TRA-090 fixed in round 5; TRA-D5-002): `TRAKernel.run()` now
  accepts an optional `llm_translate: Callable[[str, RuntimeContext], str] |
  None` callback (dependency injection). Previously the only way to supply
  an LLM was module-level monkeypatching of `tra.kernel.translate_segment`
  (fragile — any rename broke tests silently).
- **Factual integrity** (TRA-A5-013 fixed in round 5): `verify_output` now
  checks that version-like tokens (v0.5.0, 1.2.3) and ISO dates (2024-01-15)
  in the source appear verbatim in the target. `FACTUAL_INTEGRITY` (P1, the
  highest priority) is now arbitrated through `_POLICY_RESOLVER.wins()` —
  previously the only spec-mandated check with NO implementation.
- **ISA contract docstrings** (TRA-A5-010 fixed in round 5): all 6 ISA
  instruction docstrings now include explicit Spec §3 contract labels
  (Inputs/Outputs/Invariant/Failure Condition).

See `docs/audit/round5/TRA_audit_findings_register_r5.xlsx` for the full
Round 5 audit register (68 findings: 46 issues + 22 positive verifications)
and `docs/audit/round5/TRA_Prototype_Audit_Report_r5.docx` for the narrative
report. Round 4 deliverables (47 issues + 19 positive verifications) are in
`docs/audit/round4/`. Round 3 deliverables (36 findings) are in
`docs/audit/round3/`. Round 2 deliverables (41 findings) are in
`docs/audit/round2/`. Round 1 deliverables are in `docs/audit/` (top level).
Current test count: **304 across 16 test files** (was 228 at Round 5 audit
baseline; +76 from Round 5 remediation commits `eb3d574` through the latest).
