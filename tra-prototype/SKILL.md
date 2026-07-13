# SKILL.md — TRA Prototype Engine

**A guidance document for users and AI agents: what the TRA prototype is, when to
use it, and how to drive it.**

> Scope: this file documents `tra-prototype/`, the one code area in the repo.
> The five `TRA-*.md` files are the normative specification; this engine is a
> prototype that implements them for the ZH↔EN language pair. Authoritative
> architecture context lives in `../CLAUDE.md` and `../README.md`.

---

## 1. What this is

TRA = **Translation Runtime Architecture** v1.0 — a design for high-fidelity
technical-translation engines. This prototype is a runnable engine that proves
out the spec:

- **Kernel** — an immutable 9-state sequential machine
  (`BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS →
  EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS →
  EMIT_PAYLOAD`). Transitions fire only when an ISA instruction completes.
- **ISA** — six atomic instructions (`ANALYZE_DOCUMENT`, `BUILD_GLOSSARY`,
  `BUILD_ENTITY_TABLE`, `TRANSLATE_SEGMENT`, `VERIFY_OUTPUT`, `REPAIR_SEGMENT`),
  each with a strict contract.
- **Policy Engine** — a non-negotiable 6-priority stack (Factual → Structural →
  Entity → Terminological → Epistemic → Fluency). Higher priority always wins.
- **Memory Model** — Immutable Config, Runtime Context, Document Memory,
  append-only Audit Memory.
- **ZH↔EN Module** — the bundled language bridge (glossary, epistemic lexicon,
  bilingual rule layer).

### What "translation" means here

The engine is **deterministic and rule-based**. It does canonical substitution
(glossary + entity + epistemic lexicon) over an analyzed markdown structure. It
is *not* a fluent neural translator. Its value is **verifiable fidelity**, not
prose quality:

- Canonical terminology is exact, never approximate (`成立 → Confirmed`, never
  "Valid"/"True"; `执行环境 → execution environment`, never "runtime").
- Entities (product names, APIs, versions, acronyms) are preserved verbatim.
- Every output carries an evidence trail and a zero-`BLOCKING` conformance gate
  (L3+).

An **optional LLM seam** (`llm_translate`) can be supplied by the caller; if it
raises, the engine degrades to the rule path instead of failing.

---

## 2. When to use it

| Use it for | Do NOT use it for |
| :--- | :--- |
| Translating ZH→EN *technical* docs (advisories, RFCs, guides) where terminology precision matters | General-purpose fluent prose translation |
| Producing an auditable, evidence-backed translation | High-volume localization needing human-quality fluency |
| Enforcing a fixed canonical glossary across a corpus | Languages other than ZH↔EN (no module exists yet) |
| Learning/auditing the TRA execution model | Replacing a production MT system as-is |

---

## 3. Setup

```bash
cd tra-prototype
python -m venv .venv && source .venv/bin/activate   # if not already created
pip install -e ".[dev]"                             # runtime + dev deps (ruff, mypy, pytest)
```

> The `[dev]` extra is required for the quality gates in §7 (ruff, mypy,
> pytest). Without it, `pip install -e .` installs only runtime deps.

Configuration: `config.yaml` (the `tvm_bootstrap` config). Key fields:

- `language_pair` — `"ZH -> EN"` (only the ZH↔EN module is bundled).
- `conformance_level` — `L1_BASIC` / `L2_PROFESSIONAL` / `L3_STRICT` /
  `L4_FORENSIC` (default `L3_STRICT`).
- `artifacts.compilation_dir` / `artifacts.audit_trace` — where runtime
  artifacts are written (default `./compilation_artifacts`, `./audit_trace.jsonl`).
- `cache.directory` — deterministic cache (default `./cache`).

---

## 4. CLI usage

Run the CLI as a module (there is no console-script entry point):

```bash
cd tra-prototype
python -m tra_cli --help
```

### `translate` — run the full pipeline

```bash
python -m tra_cli translate input.md --level L3 -o input.en.md
```

- `--lang zh-en` — override the language pair.
- `--level L1|L2|L3|L4` (or `L3_STRICT` form) — conformance level.
- `--output / -o` — output path (default `input.translated.md`).
- `--interactive` — pause for human review on `UNRECOVERABLE` repair decisions
  (accept / override / skip).

Writes the translated markdown **plus** runtime artifacts (glossary, entity
table, structural map, execution log, repair history, audit trace). At L4 it
additionally writes `evidence_trace.jsonl` and `ambiguity_register.json`.

### `validate` — standalone conformance gate

```bash
python -m tra_cli validate input.md output.md --level L3
```

Audits `output.md` against `input.md` **without** re-translating. Exits `0`
(PASS) iff zero `BLOCKING` diagnostics are raised at the level; exits `1`
otherwise. Use this in CI to certify a candidate.

### `audit` — inspect the audit trail

```bash
python -m tra_cli audit ./audit_trace.jsonl --report
```

- Default — a table of audit records (instruction, evidence count, flags).
- `--format json` — raw JSONL records.
- `--report` — adds the conformance summary (totals by severity/instruction,
  L3 verdict) and a Mermaid state-transition diagram built from
  `execution_log.json`.

### `cache-clear` — invalidate the deterministic cache

```bash
python -m tra_cli cache-clear            # drop all
python -m tra_cli cache-clear --pattern "..."   # drop matching keys
```

---

## 5. Conformance levels

| Level | What it adds | Artifact / gate |
| :--- | :--- | :--- |
| **L1** Basic | Meaning + formatting preserved | — |
| **L2** Professional | + terminology consistency, entity preservation | — |
| **L3** Strict | + glossary, diagnostics, audit trace | **zero `BLOCKING` required** |
| **L4** Forensic | + line-by-line evidence tracing | `evidence_trace.jsonl`, `ambiguity_register.json` |

L4 emits the most artifacts but runs the same pipeline; it is the strictest
audit surface.

---

## 6. Extending (the only sanctioned path)

New language/domain/formatting behavior goes through the **module registry** —
never by editing the Kernel or ISA.

```python
from tra.modules.registry import build_default_registry, ModuleInterface

# Register a new bridge (e.g. fr-en) as a ModuleInterface; it must not touch
# kernel.py or isa.py. See tra/modules/zh_en.py for the template.
registry = build_default_registry()
registry.register(my_module.as_interface())
```

See `../TRA-MODULE-ZH-EN.md` for the module-authoring template and
`../CLAUDE.md` → "Prototype engine status" for the file layout.

---

## 7. Quality gates (run before any commit)

```bash
cd tra-prototype
. .venv/bin/activate
ruff format . && ruff check . && ruff format --check . && mypy --strict tra && pytest tests
```

All four must be green. The L3 gate is also covered by tests
(`test_benchmark.py` asserts zero `BLOCKING` across the S/F/T/D/E/R cases).

---

## 8. Known limitations (honest)

- **Single language pair** — only ZH↔EN is bundled.
- **Rule-based fidelity, not fluency** — output is structurally correct and
  terminology-exact but may read awkwardly; the LLM seam is the intended
  fluency path and is caller-supplied.
- **`structlog` is a listed dependency but unused** — logging is via the plain
  `AuditTrail` (no structured/correlation-ID logging).
- **No segment-level parallelism** — translation is sequential.
- **Glossary/entity tables rebuilt per run** — only the translation output is
  cached across runs (diskcache).
- **Phase 7 (docs/delivery) not started** — see `implementation_plan.md` for the
  full per-item state.

---

## 9. Quick mental model for agents

If asked to "translate" or "certify" a doc with this engine:

1. **Translate** with `translate` (pick the level by required strictness).
2. **Certify** with `validate` (CI gate; zero `BLOCKING` = pass).
3. **Audit** with `audit --report` (show the evidence trail + state diagram).
4. **Extend** only via the module registry; never patch the Kernel/ISA.
5. **Keep gates green** before committing.

The spec is the source of truth for *what* the engine must do; this prototype is
one *how*.
