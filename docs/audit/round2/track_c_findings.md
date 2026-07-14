# Track C — Doc-vs-Code Consistency Re-Audit Findings

**Auditor:** Track C2 agent
**HEAD audited:** 4b8827c
**Methodology template:** `tra-audit-skills/worklog.md` lines 708-1030 (Round-1 Track C, 22 findings D-1…D-22)
**Regression baseline:** `audit-ctx/track_r_baseline.md` (35 Round-1 findings, 32 PASS / 3 FAIL)
**Companion audits:** `track_a_findings.md` (11 findings) + `track_b_findings.md` (13 findings)

## Per-doc accuracy table

| Doc | Lines | Claims verified | Claims accurate | Claims stale | New findings |
|---|---|---|---|---|---|
| `AGENTS.md` | 38 | 14 | 13 | 1 | TRA-C2-016 |
| `CLAUDE.md` | 94 | 42 | 37 | 5 | TRA-C2-001, -002, -003, -004 |
| `README.md` (root) | 143 | 32 | 32 | 0 | — |
| `implementation_plan.md` | 439 | 68 | 64 | 4 | TRA-C2-009, -011, -012 |
| `status.md` | 50 | 10 | 4 | 6 | TRA-C2-013 |
| `tra-prototype/SKILL.md` | 279 | 46 | 43 | 3 | TRA-C2-007, -008 |
| `tra-prototype/README.md` | 98 | 28 | 23 | 5 | TRA-C2-005, -006, -007 |
| `tra-prototype/tra_cli.py` docstring (L1-7) | 7 | 4 | 4 | 0 | — (D-8 fixed) |
| `tra-prototype/config.yaml` | 28 | 8 | 8 | 0 | — (D-7 fixed) |
| `tra-prototype/pyproject.toml` description | 1 | 1 | 1 | 0 | — |
| `tra-prototype/examples/expected_outputs/.L3.target.md` | 10 | 2 | 2 | 0 | — (D-11 fixed via rename) |
| `prototype.md` | 111 | 10 | 9 | 1 | TRA-C2-010 |
| `review.md` | 53 | 12 | 7 | 5 | — (carry-over D-21, historical review) |
| `start-here.md` | 45 | 10 | 9 | 1 | — (carry-over D-22, partial) |
| `review-feedback.md` | 387 | 8 | 8 | 0 | — (scope note updated) |
| `docs/audit/` folder (duplication) | — | — | — | — | TRA-C2-014 |
| Spec spot-checks (`TRA-SPECIFICATION.md` §2.1/§4, `TRA-ISA-REFERENCE.md`, `TRA-CONFORMANCE-GUIDE.md`) | — | 18 | 18 | 0 | — |

## Documents ranked by accuracy (most → least)

1. **`README.md` (root)** — 32/32 claims accurate. Architecture diagram, conformance table, CLI examples, capabilities, status all match code. The single most reliable navigation doc.
2. **`tra-prototype/SKILL.md`** — 43/46. Authoritative for setup, CLI, quality gates. Three stale items: unused-deps list incomplete (TRA-C2-008), "Behaviors added" section incomplete (TRA-C2-007), test-file count slightly inflated.
3. **`TRA-SPECIFICATION.md` / `TRA-ISA-REFERENCE.md` / `TRA-CONFORMANCE-GUIDE.md`** — 18/18 spot-checked claims accurate (ground truth, not audited for change).
4. **`review-feedback.md`** — 8/8. Scope-note header updated to reflect boundary override; embedded design micro-docs remain valid planning context.
5. **`AGENTS.md`** — 13/14. Concise and accurate; only gap is the Files-and-roles table omitting meta-docs (TRA-C2-016).
6. **`prototype.md`** — 9/10. Stale scope note (TRA-C2-010); rest is historical planning context.
7. **`start-here.md`** — 9/10. "逐段" (segment-by-segment) claim is aspirational (carry-over D-22); rest accurate.
8. **`implementation_plan.md`** — 64/68. Phase 0-6 checkboxes mostly accurate; scope note (TRA-C2-009), file-structure summary (TRA-C2-011), and Phase 0.1.5 subcommand list (TRA-C2-012) are stale.
9. **`tra-prototype/README.md`** — 23/28. Five stale "Known gaps" items (TRA-C2-005, -006) and an install command that omits dev deps (TRA-C2-007). Diverges from SKILL.md §3.
10. **`CLAUDE.md`** — 37/42. Layout section accurate; "Known gaps" list has 4 stale entries (TRA-C2-001, -002, -003, -004) — the most stale section in the doc.
11. **`review.md`** — 7/12. Five stale claims (carry-over D-21): "spec repository (not a code project)", "no reference implementation", "HITL lightly addressed", etc. Historical review, not a current-state doc.
12. **`status.md`** — 4/10. Verbatim session log masquerading as a status doc (TRA-C2-013). Says "103 pytest passing" (actual: 141); frozen at the Phase 6 commit (4d97aa1), predates Round-1 remediation.

## Summary

- Total findings: **15**
- BLOCKING: **1** (TRA-C2-004)
- WARNING: **7** (TRA-C2-001, -002, -003, -005, -006, -007, -013)
- INFO: **7** (TRA-C2-008, -009, -010, -011, -012, -014, -015, -016)

Carry-over status from Round-1 Track C (D-1…D-22):
- **9 fixed**: D-3 (repair surgical), D-4 (README Phase 0-5), D-6 (count_blocking stub), D-7 (cache.expire dead config), D-8 (tra_cli.py docstring), D-9 (root .gitignore), D-11 (.L3.target.md rename), D-12 (Phase 0 checkboxes), D-18 (kernel transitions).
- **4 stale-carry-over**: D-2 (module registry — kernel now supports registry, CLAUDE.md:48 stale), D-5 (unused deps — CLAUDE.md complete, SKILL.md incomplete), D-19 (Known gaps incomplete — now has 10 bullets but 4 are stale), D-20 (status.md accurate — now stale).
- **2 acknowledged-carry-over**: D-21 (review.md historical), D-22 (start-here.md "逐段" aspirational).
- **6 still-accurate**: D-1 (segment granularity, now documented), D-13/14/15/16/17 (Phase 1.3.1, structlog, asyncio, cross-run cache, Phase 7).

## Findings

### TRA-C2-001 — CLAUDE.md "Known gaps" TRA-013 claim is stale (audit reproducibility remediated)
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New (subset of D-19)
- **Doc:** `CLAUDE.md:51` — "Audit trail reproducibility (TRA-013): `uuid4` evidence IDs + `datetime.now(UTC)` timestamps make `audit_trace.jsonl` non-byte-reproducible across runs — undermines L4 forensic hashing."
- **Code:** `tra-prototype/tra/kernel.py:115-121` — `TRAKernel.__init__` now takes a `deterministic: bool = True` flag; when set, uses `self._deterministic_clock` (kernel.py:157-171) which derives the timestamp from `sha256(source)` instead of `datetime.now(UTC)`. The `AuditTrail.append` path uses this clock for every record. `EvidenceRecord.id` is content-addressed (`diagnostics.py` `EvidenceRegistry.add` returns a hash of the canonical record).
- **Detail:** The Track B2 audit empirically verified reproducibility: "two L4 runs … sha256sum matched for `audit_trace.jsonl` (263b901e…8488797), `evidence_trace.jsonl` (f9831523…d71b88a4), and output `.md` (225d5ede…6d9e5f1f). TRA-013 fully remediated." The Track R baseline also marks TRA-013 as REGRESSION-TEST-PASS. The CLAUDE.md "Known gaps" entry is now stale — the issue it describes (`uuid4` + `datetime.now(UTC)`) no longer exists in the default code path.
- **Suggested fix:** Delete the bullet at `CLAUDE.md:51`. Alternatively, replace with: "Audit trail reproducibility (TRA-013): FIXED — `TRAKernel(deterministic=True)` (the default) uses a content-addressed clock derived from `sha256(source)`; evidence IDs are content-addressed hashes. Two runs of identical source produce byte-identical `audit_trace.jsonl` and `evidence_trace.jsonl`. Set `deterministic=False` for wall-clock timestamps."

### TRA-C2-002 — CLAUDE.md "Known gaps" TRA-004 claim is partially stale (BrokenMarkdown IS now caught)
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New (refines D-19)
- **Doc:** `CLAUDE.md:49` — "Exception recovery (TRA-004): only `GlossaryConflict` and `Unrecoverable` reach `route_exception`; `BrokenMarkdown` propagates uncaught through the kernel, and `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are never raised in production code paths."
- **Code:** `tra-prototype/tra/kernel.py:205-214` — `analyze_document` is wrapped in `try: … except TRAException as exc: self._recover(exc)`; `analyze_document` raises `BrokenMarkdown` (`isa.py:95-97`). Therefore `BrokenMarkdown` IS caught and routed to `_recover` → `route_exception`. Same pattern at `kernel.py:226-229` for `build_glossary` (raises `GlossaryConflict`). `Unrecoverable` is routed via `kernel.py:424-429`. Track A2 confirms: "_recover routes all 5 TRA-EXCEPTION types via route_exception; confirmed only BrokenMarkdown and GlossaryConflict ever reach it" (worklog.md:31) — plus Unrecoverable via the repair loop.
- **Detail:** Three exception types now reach `route_exception` in production (`BrokenMarkdown`, `GlossaryConflict`, `Unrecoverable`), not two. The CLAUDE.md claim "BrokenMarkdown propagates uncaught" is wrong. The claim about `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` being never-raised is still accurate (Track A2 confirms).
- **Suggested fix:** Replace `CLAUDE.md:49` with: "Exception recovery (TRA-004): `BrokenMarkdown`, `GlossaryConflict`, and `Unrecoverable` reach `route_exception` in production (`kernel.py:208, 229, 429`). `UnknownTerm`, `CertaintyConflict`, and `EntityAmbiguity` are defined and routed by `recovery.py` but never raised in any production code path — their recovery procedures are dead code in practice."

### TRA-C2-003 — CLAUDE.md "Known gaps" TRA-002 claim is stale (kernel now uses registry when supplied)
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New (refines D-2 / D-19)
- **Doc:** `CLAUDE.md:48` — "Module registry bypassed (TRA-002): the kernel hard-codes `ZHENModule()` instead of routing through `build_default_registry()`; registered modules are not yet picked up by `tra_cli.py translate`."
- **Code:** `tra-prototype/tra/kernel.py:113-155` — `TRAKernel.__init__` calls `self._select_module(config.language_pair, registry)`; the static method (kernel.py:129-155) iterates `registry.all()` and returns the first matching language module; falls back to `ZHENModule()` only when `registry is None` or no match. `tests/test_outstanding_findings.py:511-595` (`TestTRA002RegistryWiring`) asserts a registered stub module's glossary IS used by the kernel. `tra_cli.py:107` constructs `TRAKernel(cfg, interactive=interactive)` without passing a registry — so the CLI uses the ZHENModule fallback.
- **Detail:** The kernel does NOT "hard-code `ZHENModule()`" — it supports the registry path. The accurate gap is narrower: the production `translate` CLI does not construct a registry, so registered modules are not picked up by `tra_cli.py translate`. The doc paints an idealized-then-broken picture when the actual state is "registry wired but CLI not yet using it". SKILL.md §6 (lines 197-203) documents the correct usage pattern `TRAKernel(cfg, registry=registry)`.
- **Suggested fix:** Replace `CLAUDE.md:48` with: "Module registry not wired into CLI (TRA-002): the kernel accepts an optional `registry` parameter and selects the language module from it (`kernel.py:113-155`), but `tra_cli.py translate` constructs `TRAKernel(cfg)` without a registry — so registered modules are not picked up by the production CLI. Direct callers can pass `registry=build_default_registry()` (see `SKILL.md` §6)."

### TRA-C2-004 — CLAUDE.md "Known gaps" TRA-031 benchmark coverage claim is factually wrong
- **Severity:** BLOCKING
- **Category:** Doc Consistency / factually-wrong
- **Carry-over or new:** New
- **Doc:** `CLAUDE.md:54` — "Benchmark coverage (TRA-031): 13 of 23 spec cases implemented (S-01..S-04, S-06, D-01..D-03, E-01, E-03 missing); spec target is 100+."
- **Code:** `tra-prototype/tests/benchmark/cases/sft.jsonl` + `regression.jsonl` — 22 cases total. Per-category breakdown: S={S-01, S-02, S-04, S-05, S-06} (5), F={F-01..F-05} (5), T={T-01..T-05} (5), D={D-01..D-04} (4), E={E-01, E-02} (2), R={R-01} (1 regression). Spec cases implemented: 21 of 23. **Only `S-03` and `E-03` are missing.** The CLAUDE.md parenthetical lists 10 cases as "missing" (S-01..S-04, S-06, D-01..D-03, E-01, E-03); 8 of those 10 are in fact implemented.
- **Detail:** Track R baseline TRA-031 says "Benchmark cases implemented: 22" — consistent with the 22-case count above (21 spec + 1 regression). CLAUDE.md:54 claims 13/23 implemented (i.e., 10 missing), which materially **understates** the prototype's conformance coverage by 8 cases. The Track B2 audit ran `pytest tests/test_benchmark.py` and all 22 cases pass. This is the most impactful stale-doc finding in the audit because it misrepresents the prototype's benchmark status to anyone reading CLAUDE.md as the source of truth.
- **Suggested fix:** Replace `CLAUDE.md:54` with: "Benchmark coverage (TRA-031): 21 of 23 spec cases implemented (S-01, S-02, S-04, S-05, S-06; F-01..F-05; T-01..T-05; D-01..D-04; E-01, E-02). Missing: S-03 (inline-code vs. prose — note: inline-code protection IS implemented per `kernel.py:383-391`; the S-03 fixture itself is not in `tests/benchmark/cases/`), E-03 (broken source markdown). Spec target is 100+."

### TRA-C2-005 — tra-prototype/README.md "Known gaps" inline-code claim is stale (contradicts SKILL.md)
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New
- **Doc:** `tra-prototype/README.md:76-77` — "Inline-code glossary substitution is not yet suppressed (S-03): terms inside backticks are still run through the glossary."
- **Code:** `tra-prototype/tra/kernel.py:383-391` — `_execute_translation` protects inline code via `_INLINE_RE = re.compile(r"`[^`\n]+`")` with a stash-and-restore mechanism (placeholders `__INLINE_CODE_N__`). `tra-prototype/SKILL.md:51-54` directly contradicts the README claim: "Code-block protection (TRA-001 partial): fenced (```` ``` ````) and inline (`` ` ``) code blocks are no-translate zones — extracted as placeholders before translation and restored verbatim after, so glossary terms inside backticks survive untranslated."
- **Detail:** Empirically verified: `TRAKernel(cfg).run("# Test\n\nOutside: 成立.\nInside: \`成立\`.\n")` (at L1) produces `Outside: Confirmed.` / `Inside: \`成立\`.` — the inline-code occurrence is preserved. The README.md "Known gaps" entry is stale and contradicts SKILL.md. (Note: the S-03 benchmark fixture itself is not in `tests/benchmark/cases/`, so the S-03 *case* is technically missing — but the inline-code *behavior* the case tests is implemented.)
- **Suggested fix:** Delete the bullet at `tra-prototype/README.md:76-77`. Alternatively, replace with: "Inline-code glossary substitution IS suppressed (TRA-001 partial): fenced and inline code blocks are stashed as placeholders before translation and restored verbatim after (`kernel.py:374-391`). The S-03 benchmark fixture itself is not yet in `tests/benchmark/cases/` (only S-01, S-02, S-04, S-05, S-06 are)."

### TRA-C2-006 — tra-prototype/README.md "Known gaps" module-registry claim is stale
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New (mirror of TRA-C2-003)
- **Doc:** `tra-prototype/README.md:91-93` — "Module registry is the sanctioned extension point but the kernel currently hard-codes `ZHENModule()` — registered modules are not yet picked up by `tra_cli.py translate`."
- **Code:** Same as TRA-C2-003 — `kernel.py:113-155` supports registry-based selection; `tra_cli.py:107` doesn't pass a registry.
- **Detail:** Same divergence as TRA-C2-003 but in the prototype README. The phrase "the kernel currently hard-codes `ZHENModule()`" is no longer accurate — the kernel uses ZHENModule only as a fallback when no registry is supplied.
- **Suggested fix:** Replace `tra-prototype/README.md:91-93` with: "Module registry is the sanctioned extension point; the kernel accepts an optional `registry` parameter and uses it when supplied (`kernel.py:113-155`). The production `tra_cli.py translate` does not yet construct a registry, so registered modules are not picked up by the CLI. Direct callers: `TRAKernel(cfg, registry=build_default_registry())` (see `SKILL.md` §6)."

### TRA-C2-007 — tra-prototype/README.md install command omits dev deps (diverges from SKILL.md)
- **Severity:** WARNING
- **Category:** Doc Consistency / misleading-doc
- **Carry-over or new:** New (mirror of D-10, now in the opposite direction)
- **Doc:** `tra-prototype/README.md:18` — `pip install -e .`
- **Code:** `tra-prototype/pyproject.toml:23-30` — `dev` optional-dependencies contains `pytest`, `pytest-asyncio`, `ruff`, `black`, `mypy`. `tra-prototype/SKILL.md:80` correctly says `pip install -e ".[dev]"` and adds (SKILL.md:83-84): "The `[dev]` extra is required for the quality gates in §7 (ruff, mypy, pytest). Without it, `pip install -e .` installs only runtime deps."
- **Detail:** D-10 in Round-1 flagged SKILL.md for omitting `[dev]`. SKILL.md §3 has since been fixed. But the prototype README.md install command was not updated in lockstep — a new contributor reading `tra-prototype/README.md` first (the file most likely to be read first) will `pip install -e .` and then hit `ruff: command not found`, `mypy: command not found`, `pytest: command not found` when running the documented "Test + lint" section (README.md:64-70). The two docs now disagree.
- **Suggested fix:** Change `tra-prototype/README.md:18` to `pip install -e ".[dev]"` and add a one-line note: "# runtime + dev deps (ruff, mypy, pytest) — required for the quality gates below".

### TRA-C2-008 — SKILL.md "Known limitations" unused-deps list is incomplete
- **Severity:** WARNING
- **Category:** Doc Consistency / incomplete-doc
- **Carry-over or new:** New (refines D-5 / D-19)
- **Doc:** `tra-prototype/SKILL.md:238-240` — "`structlog`, `litellm`, and `pytest-asyncio` are listed dependencies but unused — the LLM seam is caller-supplied (never imports litellm) and tests are synchronous."
- **Code:** `tra-prototype/pyproject.toml:10-21` lists 4 unused runtime deps (`pydantic-settings`, `mdit-py-plugins`, `structlog`, `litellm`) and `pyproject.toml:24-30` lists 2 unused dev deps (`black`, `pytest-asyncio`). Grep for `^(import|from)\s+(structlog|litellm|pydantic_settings|mdit_py_plugins|black|pytest_asyncio)` across `tra-prototype/` returns **0 .py file hits** (only manifest mentions). `CLAUDE.md:52` correctly lists all 6: "`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio` are listed but unused."
- **Detail:** SKILL.md §8 lists 3 of the 6 unused deps. The 3 it omits (`pydantic-settings`, `mdit-py-plugins`, `black`) are all unused — `pydantic-settings` and `mdit-py-plugins` would pull in transitive deps if installed; `black` is listed as a dev dep but the project uses `ruff format` per SKILL.md §7. The SKILL.md list is out-of-sync with both `CLAUDE.md` and the actual grep evidence.
- **Suggested fix:** Replace `SKILL.md:238-240` with: "`pydantic-settings`, `mdit-py-plugins`, `structlog`, and `litellm` are listed runtime dependencies but unused — the engine uses a hand-rolled `BootstrapConfig.from_yaml` (not pydantic-settings), a vanilla `markdown-it-py` traversal (not mdit-py-plugins), the plain `AuditTrail` (not structlog), and a caller-supplied `llm_translate` seam (never imports litellm). Dev deps `black` and `pytest-asyncio` are also unused — formatting goes through `ruff format`, tests are synchronous."

### TRA-C2-009 — implementation_plan.md "Repo scope note" still calls tra-prototype/ "an external codebase"
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New
- **Doc:** `implementation_plan.md:3` — "Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is an **implementation plan for `tra-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only."
- **Code:** `CLAUDE.md:9`, `AGENTS.md:5`, `README.md:11` all state the boundary was overridden: "A Phase 0 prototype engine now lives in `tra-prototype/` as a subdirectory of this repo (the original boundary rule put conformant engines in a separate repository; this was overridden so the prototype and spec evolve together)." `review-feedback.md:1` was updated to match: "That was overridden: the `tra-prototype/` engine now lives as a subdirectory of this repo."
- **Detail:** `implementation_plan.md` was not updated when the boundary override landed. The note still describes `tra-prototype/` as "an external codebase", contradicting the actual repo layout and the other three planning docs' scope notes.
- **Suggested fix:** Replace `implementation_plan.md:3` with: "> **Repo scope note:** The repo's original boundary rule put any concrete TRA-compliant engine in a *separate* repository. That was overridden: `tra-prototype/` now lives as a subdirectory of this repo (see `README.md` / `AGENTS.md` / `CLAUDE.md`). This file is the **implementation plan for `tra-prototype/`** — kept here as planning context, not part of the normative spec."

### TRA-C2-010 — prototype.md "Repo scope note" same staleness as implementation_plan.md
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New
- **Doc:** `prototype.md:1` — "Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is a **planning note for `tra-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only."
- **Code:** Same as TRA-C2-009 — boundary override documented in CLAUDE.md/AGENTS.md/README.md/review-feedback.md.
- **Detail:** `prototype.md` predates the boundary override and wasn't updated. The `review-feedback.md:1` scope note was updated to acknowledge the override; `prototype.md:1` was not.
- **Suggested fix:** Replace `prototype.md:1` with the same updated scope note suggested in TRA-C2-009.

### TRA-C2-011 — implementation_plan.md File Structure Summary is stale (missing 6+ files)
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New
- **Doc:** `implementation_plan.md:305-351` — File Structure Summary lists 8 modules under `tra/` (`__init__.py`, `kernel.py`, `memory.py`, `isa.py`, `policy.py`, `diagnostics.py`, `cache.py`, `anchor.py`, `utils.py`, `exceptions.py`) and 11 test files. Does not list `recovery.py`, `hitl.py`, `reporting.py`, `validate.py`, `config.py`, `benchmark.py`, `SKILL.md`, `e2e_test.py`, `to_translate.en.md`.
- **Code:** Actual `tra-prototype/tra/` directory contains 17 .py files + `modules/`: `__init__.py`, `anchor.py`, `benchmark.py`, `cache.py`, `config.py`, `diagnostics.py`, `exceptions.py`, `hitl.py`, `isa.py`, `kernel.py`, `memory.py`, `policy.py`, `recovery.py`, `reporting.py`, `utils.py`, `validate.py` (+ `modules/{__init__,base,registry,zh_en}.py`). The actual `tra-prototype/tests/` directory contains 13 .py files (12 `test_*.py` + `conftest.py`); the plan lists 10 test files. The actual `tra-prototype/` root also contains `SKILL.md`, `e2e_test.py`, `to_translate.en.md` — none listed.
- **Detail:** The File Structure Summary was authored at Phase 0 planning time and never updated as Phase 6 hardening added `recovery.py`, `hitl.py`, `reporting.py`, `validate.py`, `config.py`, `benchmark.py`. CLAUDE.md:17-31 "Layout" section IS up-to-date and lists all 13 modules accurately — readers should prefer CLAUDE.md over `implementation_plan.md` for the current file inventory.
- **Suggested fix:** Add a header note at `implementation_plan.md:305`: "> File structure below is the Phase-0 planning snapshot; for the current file inventory see `CLAUDE.md` → 'Layout (where behavior lives)'." (Updating the snapshot itself is also acceptable, but the header note is preferred for a historical planning doc.)

### TRA-C2-012 — implementation_plan.md Phase 0.1.5 subcommand list is stale (lists 3, actual 4)
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New
- **Doc:** `implementation_plan.md:22` — "[x] 0.1.5 Set up CLI entry point skeleton (tra_cli.py with translate, cache-clear, audit subcommands)"
- **Code:** `tra-prototype/tra_cli.py` implements **4** subcommands: `translate` (line 66), `cache-clear` (line 131), `audit` (line 152), `validate` (line 214). The `validate` subcommand was added during Phase 5 (5.1.4 at `implementation_plan.md:223` is also marked `[x]`). `tra_cli.py:1-7` docstring lists all 4.
- **Detail:** Phase 0.1.5 was authored when only 3 subcommands were planned; `validate` was added later. The checkbox is correctly `[x]` (the skeleton IS set up), but the parenthetical "with translate, cache-clear, audit subcommands" understates the actual CLI. A reader scanning the plan would miss `validate` exists.
- **Suggested fix:** Update `implementation_plan.md:22` parenthetical to: "(tra_cli.py with translate, validate, audit, cache-clear subcommands)".

### TRA-C2-013 — status.md is a verbatim session log, not a current-status doc
- **Severity:** WARNING
- **Category:** Doc Consistency / misleading-doc
- **Carry-over or new:** New (D-20 re-found stale)
- **Doc:** `status.md` (50 lines) — opens with `Bash(git status && echo "---DIFF STAT---" && git diff --stat)` (line 3); contains verbatim shell transcripts; line 44: "Gates: ruff clean · ruff-format clean · mypy --strict (20 files) · **103 pytest passing**." Line 35: "Phase 6 is complete and pushed (4d97aa1 → origin/main)."
- **Code:** Current state: `pytest tests` reports **141 passed in 0.87s**; Round-1 audit remediation landed 7 commits (`116f77c`…`419ca31`) after `4d97aa1`; HEAD is `4b8827c`. `CLAUDE.md:15` is the accurate current-status doc ("Phases 0–6 are complete … Phase 7 has not started").
- **Detail:** D-20 in Round-1 marked status.md PASS as "the most accurate of the planning/narrative docs". That verdict was correct *at the time of Phase 6 commit* but is no longer true. status.md is frozen at the `4d97aa1` session; the test count (103 vs 141), the commit narrative, and the "Let me know if you want Phase 7 next" sign-off are all stale. Worse, the file is named `status.md` — a name that implies "current status" — but the content is a session transcript. New contributors reading `status.md` first will get a 2026-07 snapshot, not current state.
- **Suggested fix:** Two options: (a) rename `status.md` → `phase6_commit_log.md` and add a header: "> Verbatim session log from the Phase 6 commit (4d97aa1). For current status see `CLAUDE.md` → 'Prototype engine status'."; OR (b) replace `status.md` content with a 5-line current-state summary: "HEAD: 4b8827c. Phases 0-6 complete. 141 tests passing. Open: 6.3.1 (structlog), 6.5.1 (asyncio), 6.5.2 (cross-run cache), all of Phase 7. See `CLAUDE.md` for the full state." Option (a) preserves the historical narrative; option (b) makes the filename honest.

### TRA-C2-014 — docs/audit/ duplicates tra-audit-skills/deliverables/ (undocumented)
- **Severity:** INFO
- **Category:** Doc Consistency / undocumented-duplication
- **Carry-over or new:** New
- **Doc:** `docs/audit/` contains `TRA_audit_findings_register.xlsx`, `TRA_audit_severity_heatmap.png`, `TRA_Prototype_Audit_Report.docx`, `tra-audit-skills.tar.gz`. Referenced from `CLAUDE.md:56`, `tra-prototype/SKILL.md:258`, `tra-prototype/README.md:90,95-96`. None of these references explain the duplication with `tra-audit-skills/deliverables/`.
- **Code:** `md5sum` confirms byte-identical duplicates: `TRA_audit_findings_register.xlsx` (1daec50f…), `TRA_audit_severity_heatmap.png` (86e9b329…), `TRA_Prototype_Audit_Report.docx` (acd2df5c…) all match between `docs/audit/` and `tra-audit-skills/deliverables/`. `docs/worklog.md` (154fd36d…) also byte-matches `tra-audit-skills/worklog.md`.
- **Detail:** The duplication is intentional (surfacing audit deliverables in `docs/audit/` for repo readers who don't want to dig into `tra-audit-skills/`), but it's not documented anywhere. A future contributor updating the audit report would have to remember to update both copies, or the two will drift. The `tra-audit-skills.tar.gz` in `docs/audit/` is a tarball of the entire `tra-audit-skills/` directory — also undocumented.
- **Suggested fix:** Add a one-line note to `CLAUDE.md:56`: "These artifacts are duplicated from `tra-audit-skills/deliverables/` for visibility; regenerate via `tra-audit-skills/scripts/tra_xlsx.py` + `tra_chart.py` + `scripts/docx-build/generate.js`, then copy to `docs/audit/`." Alternatively, replace `docs/audit/` with symlinks to `tra-audit-skills/deliverables/`.

### TRA-C2-015 — SKILL.md §7 "14 test files" count is slightly inflated
- **Severity:** INFO
- **Category:** Doc Consistency / minor-inaccuracy
- **Carry-over or new:** New
- **Doc:** `tra-prototype/SKILL.md:222` — "The full suite is **141 tests** across 14 test files, including `test_outstanding_findings.py`…"
- **Code:** `pytest tests --collect-only` enumerates 12 `test_*.py` files in `tests/` (test_anchor, test_benchmark, test_isa, test_kernel, test_modules, test_outstanding_findings, test_phase0, test_phase6_hardening, test_recovery, test_reporting, test_utils, test_validate) = 141 tests total. `conftest.py` (fixtures only, no tests) and `e2e_test.py` (at `tra-prototype/` root, not in `tests/`) bring the loose .py count to 14, but neither is a "test file" in the pytest sense.
- **Detail:** The 141-test count is accurate. The "14 test files" count is defensible only if `conftest.py` and `e2e_test.py` are counted, but neither contains pytest-discoverable tests (`conftest.py` has fixtures only; `e2e_test.py` is a script, not collected by `pytest tests`). The accurate count is 12 test files in `tests/`, or 13 if `e2e_test.py` is counted.
- **Suggested fix:** Change `SKILL.md:222` to: "The full suite is **141 tests across 12 test files in `tests/`** (plus `e2e_test.py` at the package root), including `test_outstanding_findings.py`…"

### TRA-C2-016 — AGENTS.md "Files and roles" table omits meta-docs and prototype docs
- **Severity:** INFO
- **Category:** Doc Consistency / incomplete-doc
- **Carry-over or new:** New
- **Doc:** `AGENTS.md:9-15` — "Files and roles" table lists only the 5 spec files. The "What this repo is" paragraph (AGENTS.md:5) mentions "meta-docs (`README.md`, `CLAUDE.md`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md`" — but omits `status.md`, `implementation_plan.md`, `review.md`, and the prototype's own `tra-prototype/SKILL.md` / `tra-prototype/README.md`.
- **Code:** The repo root contains 9 meta/planning docs (`AGENTS.md`, `CLAUDE.md`, `README.md`, `start-here.md`, `prototype.md`, `review-feedback.md`, `review.md`, `status.md`, `implementation_plan.md`, `to_translate.md`) plus the `tra-prototype/` subdirectory with `SKILL.md` + `README.md`. AGENTS.md surfaces only 5 of these.
- **Detail:** AGENTS.md is the agent-facing entry doc — the file an AI agent reads first. A new agent won't know `implementation_plan.md` (the per-item Phase 0-7 state), `status.md` (the Phase 6 commit narrative), `review.md` (the historical review), or `tra-prototype/SKILL.md` (the prototype usage guide) exist. The omission isn't wrong per se (the table is titled "Files and roles" for the 5 spec files), but it's incomplete for agent navigation.
- **Suggested fix:** Either expand the "Files and roles" table to include meta-docs, OR add a second short table "Meta-docs & planning" listing `CLAUDE.md`, `AGENTS.md`, `README.md`, `start-here.md`, `prototype.md`, `review.md`, `review-feedback.md`, `status.md`, `implementation_plan.md`, `to_translate.md`, `tra-prototype/SKILL.md`, `tra-prototype/README.md` with one-line roles.

---

## Spec spot-checks (no findings — ground truth held)

These were spot-checked for internal consistency against the code; all held:

1. **TRA-SPECIFICATION.md §2.1 state machine** (lines 17-33) — 9-state Mermaid `stateDiagram-v2` matches `kernel.py:49-60` `KernelState` enum and `kernel.py:64-74` `_KERNEL_ORDER` exactly: `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`. The spec also defines `EXCEPTION_HANDLER` as a distinct state (lines 30-32); the kernel implements this as a private `_recover` method (not a `KernelState` enum value) — Track A2 finding A2-006, not a Track C doc issue.
2. **TRA-SPECIFICATION.md §4 DocumentProfile** (lines 96-99) — omits `evidence_style` field; `implementation_plan.md:28` correctly notes "evidence_style retained for spec fidelity even though TRA-SPECIFICATION.md §4 omits it." `memory.py:79-98` `DocumentProfile` includes `evidence_style: str | None` matching `TRA-ISA-REFERENCE.md:14` (`document_profile: { type, audience, register, intent, evidence_style }`).
3. **TRA-ISA-REFERENCE.md §REPAIR_SEGMENT invariant** (line 79) — "Repair must resolve the specific violation without introducing new ones." `isa.py:600-603` now enforces this at the function boundary: `if new_blocking: raise Unrecoverable(...)`. D-3 from Round-1 is fully fixed.
4. **TRA-CONFORMANCE-GUIDE.md L3 checklist** (lines 47-53) — references `tvm_bootstrap`, `compilation_artifacts`, `audit_trace` artifact names; `CLAUDE.md:91-93` and `README.md:125-133` use the same names. `config.yaml:1`, `kernel.py:456-464` (`_export_artifacts` writes to `compilation_dir`), and `diagnostics.py` (AuditTrail writes to `audit_trace`) all match.
