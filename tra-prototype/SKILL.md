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
  EMIT_PAYLOAD`). Transitions fire **after** an ISA instruction completes
  successfully (TRA-007); if an ISA raises, the state does NOT advance.
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
raises or returns empty/None output, the engine degrades to the rule path
instead of failing (TRA-033).

**Code-block protection** (TRA-001 partial): fenced (```` ``` ````) and inline
(`` ` ``) code blocks are no-translate zones — extracted as placeholders before
translation and restored verbatim after, so glossary terms inside backticks
survive untranslated.

**Structural validation** (TRA-071): `analyze_document` performs a structural
validation pass that raises `BrokenMarkdown` for unclosed fenced code blocks.
`markdown-it-py` is too lenient to raise on its own, so without this pass the
`BrokenMarkdown` recovery procedure (spec §6) was dead code. The validation
detects odd fence counts (unclosed ``` or ~~~) and raises with the line number.

**Deterministic audit trail** (TRA-013): evidence IDs are content-addressed
(SHA-256 of the canonical record) and timestamps are derived from the source
hash, so two runs of identical source produce byte-identical `audit_trace.jsonl`
and `evidence_trace.jsonl` — required for L4 forensic hash-chain validation.
Set `deterministic=False` on `TRAKernel` for wall-clock timestamps.

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
- `base_dir` — root for path-safety validation (TRA-014). All runtime paths
  (`cache_directory`, `compilation_dir`, `audit_trace`) must resolve inside
  `base_dir`; paths containing `..` or absolute paths outside it are rejected
  at construction. Default `.` (CWD). `from_yaml` reads this field from YAML
  (TRA-047); `BootstrapConfig` uses `extra='forbid'` so typo'd YAML keys raise
  `ValidationError` instead of being silently ignored.

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

At L3/L4, the kernel enforces the zero-BLOCKING gate **in-band** (TRA-005): if
BLOCKING diagnostics remain after the repair loop, the kernel raises
`ConformanceFailure` and `translate` exits `1` so a non-conformant output is
never silently published. At L1/L2, the gate is not enforced (lower
strictness dials).

Additional L3/L4 gates enforced in-band:
- **Analyze-failure gate** (TRA-036): if `analyze_document` raises (e.g.
  `BrokenMarkdown` from an unclosed fence), the kernel raises
  `ConformanceFailure` at L3/L4 — not silently returns an empty string.
- **Broken-link gate** (TRA-037): `_rewrite_anchors` runs BEFORE the L3 gate
  (not after); if any `BROKEN_LINK` entries appear in `unresolved_ambiguities`,
  the kernel raises `ConformanceFailure`. This also ensures the audit trail's
  `VERIFY_OUTPUT` hash matches the emitted target (L4 hash-chain integrity).

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
python -m tra_cli cache-clear --pattern "..."   # drop matching keys (fnmatch glob)
```

`--pattern GLOB` uses `fnmatch` semantics (e.g. `--pattern "translation:*"`).
The CLI reports the number of entries deleted (TRA-011). Previously the
pattern was passed as a literal key to `diskcache.delete`, which silently
deleted nothing.

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
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.modules.registry import build_default_registry, ModuleInterface

# Register a new bridge (e.g. fr-en) as a ModuleInterface; it must not touch
# kernel.py or isa.py. See tra/modules/zh_en.py for the template.
registry = build_default_registry()
registry.register(my_module.as_interface())

# Wire the registry into the kernel (TRA-002). The kernel selects the module
# from the registry based on config.language_pair; when omitted, falls back
# to ZHENModule.
cfg = BootstrapConfig.from_yaml("config.yaml")
kernel = TRAKernel(cfg, registry=registry)
target = kernel.run(source_md)

# TRA-D5-002 (round 5): supply an LLM via dependency injection (no
# module-level monkeypatching). The callback receives (source_segment,
# ctx) and returns the translated string. If it raises or returns
# empty/None, the engine degrades to the deterministic rule path.
def my_llm(source_segment: str, ctx: object) -> str:
    return "...translation..."
target = kernel.run(source_md, llm_translate=my_llm)
```

The selected module is stored on `ctx.module` and read by every ISA function
via the `_module(ctx)` helper, so direct ISA calls in tests still work via the
singleton fallback when `ctx.module` is None.

See `../TRA-MODULE-ZH-EN.md` for the module-authoring template and
`../CLAUDE.md` → "Prototype engine status" for the file layout.

---

## 7. Quality gates (run before any commit)

```bash
cd tra-prototype
. .venv/bin/activate
ruff format .            # auto-format (pre-step, not a gate)
ruff check .             # gate 1: lint
ruff format --check .    # gate 2: format check
mypy --strict tra        # gate 3: type check (20 source files)
pytest tests             # gate 4: test suite
```

All four gates must be green. The full suite is **289 tests** across 16 test
files, including:
- `test_outstanding_findings.py` — TDD regression tests named after finding IDs
  (63 test classes: TRA-001, 002, 004, 006, 007, 008, 009, 012, 013, 014, 016,
  017, 026, 032, 033, 036, 037, 038 (×4 — UnknownTerm, CertaintyConflict,
  EntityAmbiguity, UnknownTermRaisedInProduction), 039, 041, 042, 049, 050,
  051, 053, 054, 072, 073, 074, 075, 076, 077, 078, 088, 089, 093, 096, 097,
  098, 099, A4-011, A5-003, A5-005, A5-010, A5-013, A5-014, B4-009, B5-009,
  B5-010, B5-011, B5-012, D5-002, D5-004/005, D5-007, D5-008, D5-016, D5-017,
  F4-006, F4-007, F5-010, F5-011)
- `test_tra043_protocol.py` — LanguageModuleProtocol type-safety tests
- `test_tra047_config_robustness.py` — BootstrapConfig `from_yaml`/`extra='forbid'` tests
- `test_tra071_broken_markdown.py` — unclosed-fence structural validation tests
- `test_e2e_to_translate.py` — E2E tests on `to_translate.md` with LLM seam
  via dependency injection (12 tests: L3 pipeline, L4 forensics, byte-reproducibility)
- `test_benchmark.py` — L3 gate coverage (asserts zero `BLOCKING` across 36 S/F/T/D/E/R cases)

---

## 8. Known limitations (honest)

- **Single language pair** — only ZH↔EN is bundled.
- **Rule-based fidelity, not fluency** — output is structurally correct and
  terminology-exact but may read awkwardly; the LLM seam is the intended
  fluency path and is caller-supplied via dependency injection
  (`TRAKernel.run(source, llm_translate=callback)` — TRA-D5-002 fixed in
  round 5). Code blocks (fenced and inline) are already protected from
  glossary substitution (TRA-001 partial); full per-leaf-segment translation
  is still deferred.
- **Dependencies trimmed** (TRA-017, fixed in Round 3): removed 6 unused
  deps (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`,
  `black`, `pytest-asyncio`) from `pyproject.toml`. Install footprint
  dropped from ~70 packages to ~15. The LLM seam is caller-supplied
  (never imports litellm) and tests are synchronous.
- **No segment-level parallelism** — translation is sequential.
- **Glossary/entity tables rebuilt per run** — only the translation output is
  cached across runs (diskcache).
- **Phase 7 (docs/delivery) not started** — see `implementation_plan.md` for
  the full per-item state.

### Audit remediation status

**Round 1** (35 findings): 30 fixed, 5 carry over (TRA-001 partial, TRA-006
fixed in Round 2, TRA-016 fixed in Round 2, TRA-017 fixed in Round 3
remediation commit `a3cd2c1`, TRA-026 fixed in Round 2).

**Round 2** (41 findings): 17 fixed in this session, 24 remain (most now
fixed in Round 3 remediation). The 17 fixed in-session:
- **TRA-006** — `PolicyResolver` is now consulted in `verify_output` via
  `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)`. Severity
  is no longer hard-coded; monkeypatching the resolver changes the diagnostic
  severity.
- **TRA-036** — analyze-failure at L3/L4 raises `ConformanceFailure` (was
  silently returning `""`).
- **TRA-037** — `_rewrite_anchors` runs BEFORE the L3 gate; `BROKEN_LINK`
  entries in `unresolved_ambiguities` raise `ConformanceFailure`.
- **TRA-039** — `build_entity_table` wrapped in `try/except TRAException →
  _recover(exc)` (was unwrapped, latent crash).
- **TRA-041** — `GLOSSARY_CONFLICT` recovery populates `ctx.glossary_cache`
  with first-occurrence mappings before raising (was leaving it empty).
- **TRA-043** — `LanguageModuleProtocol` defined in `modules/base.py`;
  `RuntimeContext.module` retyped from `Any` to `LanguageModuleProtocol | None`.
- **TRA-044** — `route_exception` has an explicit `isinstance(exc, Unrecoverable)`
  branch returning `BLOCKING + HALT` (was falling through to `WARNING +
  PRESERVE_SOURCE`).
- **TRA-045** — removed dead `CONCLUSION_LEADING` constant from `zh_en.py`.
- **TRA-046** — renamed `_hash_sorted` → `_hash_canonical_json` (was misleadingly
  named; does not sort lists).
- **TRA-047** — `from_yaml` reads `base_dir`; `BootstrapConfig` has
  `extra='forbid'` (was silently ignoring typo'd keys).
- **TRA-048** — strengthened LLM-degradation test to assert exactly one
  `TRANSLATE_SEGMENT` audit record (was only checking `degraded` truthy).
- **TRA-049** — same-state kernel transition now raises (was silently allowed).
- **TRA-050** — cache-key content sensitivity tested (different glossary/entity
  → different key).
- **TRA-051** — `cache.invalidate(pattern)` fnmatch branch tested.
- **TRA-053** — inline-code protection branch tested.
- **TRA-054** — L3 `ConformanceFailure` raise branch tested.
- **TRA-071** — structural validation raises `BrokenMarkdown` for unclosed fences
  (was unreachable because `markdown-it-py` is too lenient).

**Round 3** (36 findings at HEAD `b783745`): 2 BLOCKING both fixed (TRA-093
false-positive BROKEN_LINK, TRA-096 `as_interface()` ValidationError),
18 WARNING, 16 INFO. Round 3 remediation commits `3c38f78` through `805a8f8`
fixed 20 of 36 findings. See `../docs/audit/round3/remediation_plan.md` for
the 5-batch TDD plan.

**Round 4** (47 issues + 19 positive verifications at HEAD `805a8f8`):
1 BLOCKING (TRA-C4-013, doc defect fixed in commit `f226582`), 11 WARNING,
35 INFO. All 4 critical invariants hold. TRA-013 byte-reproducibility holds
(audit_trace.jsonl sha256 `263b901e...`, matches R3 exactly). 3 OWASP
security fixes (TRA-076/077/078) verified holding. See
`../docs/audit/round4/TRA_audit_findings_register_r4.xlsx` for the full
register and `../docs/audit/round4/remediation_plan_r4.md` for the
5-batch TDD remediation plan.

**Round 5** (68 findings: 46 issues + 22 positive verifications at HEAD `5476faf`):
0 BLOCKING / 7 WARNING / 39 INFO. 0 regressions — every R4 fix that landed is
still present. All 4 critical invariants hold. TRA-013 byte-reproducibility
HOLDS within HEAD (audit_trace.jsonl sha256 `902298b3...` x2 across cold-cache
L4 runs; differs from R4 baseline `263b901e...` because R4 Batch 2 enriched
audit-trail content via TRA-038/042/072). 3 OWASP security fixes verified
holding, mutation-tested. See `../docs/audit/round5/TRA_audit_findings_register_r5.xlsx`
for the full register and `../docs/audit/round5/remediation_plan_r5.md` for
the 5-batch TDD remediation plan.

**Round 4 remediation — Batch 1** (commits `f226582` through `e54b7a7`):
7 of 47 issues fixed via TDD. Test count 199 → 210 (+11 new regression tests).
- TRA-C4-013 (BLOCKING): tra-prototype/README.md CLI examples fixed (`f226582`).
- TRA-C4-001..017 (13 doc staleness findings): refreshed across CLAUDE.md,
  tra-prototype/README.md, tra-prototype/SKILL.md, implementation_plan.md,
  AGENTS.md, status.md (`929c879`).
- TRA-A4-011: removed dead `repaired = repaired` no-op in isa.py (`524c598`).
- TRA-B4-009: added regression tests for TRA-016/017/026 (`524c598`).
- TRA-D4-014: deleted redundant tests/run_e2e_translation.py (`524c598`).
- TRA-F4-006: register() now validates get_style_profile() return shape (`524c598`).
- TRA-F4-007: _select_module now matches by full direction, not just source (`524c598`).
- TRA-099: CLI translate now passes registry to TRAKernel + normalizes --lang (`e54b7a7`).

**Round 4 remediation — Batch 2** (commits `d95c36d` through `aae0bca`, HEAD `aae0bca`):
5 more findings fixed via TDD. Test count 210 → 228 (+18 new tests + 2 benchmark cases).
- TRA-038: wired 3 unreachable exception types in production (`d95c36d`).
  UnknownTerm logged via recover_unknown_term (non-halting); CertaintyConflict
  raised in LLM path when forbidden drift target detected; EntityAmbiguity
  logged when token matches multiple patterns + hint is None. +7 tests.
- TRA-042: extended verify_output structural checks beyond heading count (`efbc875`).
  Now checks table row count, list item count, blockquote line count, HR count,
  code fence count. +6 tests.
- TRA-072: routed ALL severity decisions through PolicyResolver (`78c9250`).
  Structural (P2), Entity (P3), Epistemic (P5) vs Fluency (P6) now all
  arbitrated by _POLICY_RESOLVER.wins(). +3 tests.
- TRA-092: added S-03 (inline code) + E-03 (broken markdown) benchmark cases (`d3e5f60`).
  Benchmark suite now at 24/24 spec cases (was 22/24). +2 cases.
- TRA-100: created TRA-MODULE-AUTHORING.md guide (`aae0bca`). Phase 7 deliverable.

**Remaining persistent findings** (not yet fixed): TRA-001 (partial, full
per-leaf segment translation — Phase 8, ~16h, separate effort), TRA-040
(EXCEPTION_HANDLER/HALT_ERROR not KernelStates — intentional design decision
pending spec change), TRA-079 (cache HMAC integrity — INFO, low priority),
TRA-094 (mutation testing framework — INFO, deferred). See
`../docs/audit/round5/master_findings_register_r5.json` for the full
machine-readable register.

**Round 5 remediation** (commits `eb3d574` through `e75997f`, HEAD `e75997f`):
28 of 46 R5 issues fixed via TDD across 4 batches. Test count 228 → 289 (+61).
- **Batch 1** (commit `eb3d574`): 9 doc-consistency fixes (TRA-C5-001..013) —
  "228 across 18 test files" → "16 test files" in 4 docs; "34 classes, 139
  tests" → "46 classes, 91 tests" in implementation_plan.md; README "Known
  gaps" TRA-099/038/072/092 entries refreshed; "22 of 24" → "24/24"; status.md
  banner HEAD `aae0bca` → `5476faf`; Round 5 audit references added.
- **Batch 2** (commit `36246bb`): 3 spec-conformance fixes — TRA-A5-005
  (ordered-list + `>text` blockquote regex gaps), TRA-A5-013 (factual-
  integrity check: version + date token preservation, P1 arbitrated via
  PolicyResolver), TRA-A5-003 (UnknownTerm now emits EXCEPTION_HANDLER audit
  record). +10 tests.
- **Batch 5** (commit `bfde6dd`): 7 code-quality fixes — TRA-A5-014 (dead
  `forbidden_mappings` field removed), TRA-B5-009/010/011 (type-safety
  residuals: `registry: ModuleRegistry | None`, `list[StructuralNode]`,
  stale `type: ignore` removed), TRA-F5-010 (`_normalize_language_pair`
  rejects malformed `--lang`), TRA-F5-011 (`register()` rejects language
  modules with no `metadata.direction`), TRA-F5-012/013 (authoring guide
  Protocol snippet + dict-coercion note). +12 tests.
- **Batches A+B+C** (commit `e75997f`): 9 outstanding findings — TRA-A5-010
  (ISA docstring contract labels), TRA-D5-008 (`kernel_config` fixture used),
  TRA-B5-012 (`_module(ctx) -> LanguageModuleProtocol`), TRA-D5-016 (L2 e2e
  tests), TRA-D5-017 (CLI CliRunner tests for all 4 subcommands), TRA-D5-006
  (benchmark 24 → 36 cases), TRA-D5-002 (LLM seam DI: `TRAKernel.run(llm_translate=)`),
  TRA-D5-007 (HITL e2e tests), TRA-D5-004/005 (review_decision override/skip/
  on_override tests). +39 tests.

### Audit artifacts

- **Round 1**: `../docs/audit/` — `TRA_Prototype_Audit_Report.docx`,
  `TRA_audit_findings_register.xlsx`, `TRA_audit_severity_heatmap.png`
- **Round 2**: `../docs/audit/round2/` — `TRA_Prototype_Audit_Report_r2.docx`,
  `TRA_audit_findings_register_r2.xlsx`, `TRA_audit_severity_heatmap_r2.png`,
  `master_findings_register.json`, per-track findings (`track_{r,a,b,c,d,e}_findings.md`),
  `audit_worklog_r2.md`
- **Round 3**: `../docs/audit/round3/` — `TRA_Prototype_Audit_Report_r3.docx`,
  `TRA_audit_findings_register_r3.xlsx`, `TRA_audit_severity_heatmap_r3.png`,
  `master_findings_register_r3.json`, `remediation_plan.md`, per-track findings
  (`track_{a3,b3,c3,d3,e3,f3,r3}_*.md`)
- **Round 4**: `../docs/audit/round4/` — `TRA_Prototype_Audit_Report_r4.docx`,
  `TRA_audit_findings_register_r4.xlsx`, `TRA_audit_severity_heatmap_r4.png`,
  `master_findings_register_r4.json`, `remediation_plan_r4.md`, per-track findings
  (`track_{a4,b4,c4,d4,e4,f4,r4}_*.md`)
- **Round 5**: `../docs/audit/round5/` — `TRA_Prototype_Audit_Report_r5.docx`,
  `TRA_audit_findings_register_r5.xlsx`, `TRA_audit_severity_heatmap_r5.png`,
  `master_findings_register_r5.json`, `remediation_plan_r5.md`, per-track findings
  (`track_{a5,b5,c5,d5,e5,f5,r5}_*.md`)

---

## 9. Quick mental model for agents

If asked to "translate" or "certify" a doc with this engine:

1. **Translate** with `translate` (pick the level by required strictness).
2. **Certify** with `validate` (CI gate; zero `BLOCKING` = pass).
3. **Audit** with `audit --report` (show the evidence trail + state diagram).
4. **Extend** only via the module registry (`TRAKernel(cfg, registry=registry)`);
   never patch the Kernel/ISA.
5. **Keep gates green** before committing.
6. **E2E tests** — two entry points:
   - `python e2e_test.py` — manual demo script (prints audit trail + verdict)
   - `pytest tests/test_e2e_to_translate.py` — 12 pytest-collected regression
     tests (L3 pipeline, L4 forensics, byte-reproducibility) on `to_translate.md`
   with the `llm_translate` seam hijacked to return `to_translate.en.md`.

The spec is the source of truth for *what* the engine must do; this prototype is
one *how*.
