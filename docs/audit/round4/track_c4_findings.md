# Track C4 — Doc-vs-Code Consistency Re-Audit (Round 4)

**HEAD audited:** `805a8f8`
**Methodology:** Systematic diff of every concrete claim in 12 documentation files against source at HEAD. Each claim verified via `rg`/`Read`/`pytest`.
**Baseline:** Round 3 Track C3 (13 findings) + 36-finding R3 master register + R4 regression baseline (`track_r4_baseline.md`).

## Summary

- Findings: **17 total (1 BLOCKING / 9 WARNING / 7 INFO)**
- Carry-over from Round 3 (Track C scope): **13** — 6 FIXED, 5 PERSISTENT, 2 PARTIAL
- New findings: **12**
- Docs audited: 12

The doc-vs-code drift has materially worsened since Round 3 close. The R3 remediation commits (`df9a590` → `805a8f8`) landed 14 source-code fixes but did not back-fill the corresponding documentation; consequently CLAUDE.md, tra-prototype/README.md, and tra-prototype/SKILL.md each carry at least one claim that is now the *exact opposite* of the code reality (TRA-017 "persistent" vs FIXED; TRA-006 "never invoked" vs invoked at `isa.py:565`; "174 tests" vs 199 actual). Round 3's TRA-080 fix updated CLAUDE.md's TRA-006 entry but the parallel entry in tra-prototype/README.md was left stale (TRA-C3-008 carry-over, persistent).

## Findings

### TRA-C4-001: CLAUDE.md "Known gaps" TRA-017 entry claims 6 unused deps are persistent — they were removed in commit `a3cd2c1`
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-status
- **Evidence:**
  - Doc claim: `CLAUDE.md:51` — "**Dependency hygiene (TRA-017, persistent):** `litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio` are listed but unused."
  - Code reality: `tra-prototype/pyproject.toml` at HEAD has exactly **6 runtime deps** (`pydantic>=2.8`, `markdown-it-py>=3.0`, `diskcache>=5.6`, `pyyaml>=6.0`, `click>=8.1`, `rich>=13.7`) + **3 dev deps** (`pytest`, `ruff`, `mypy`). Verified via `python -c "import tomllib; ..."`. None of the 6 listed packages appear in `pyproject.toml`. R4 baseline TRA-017 status: **FIXED**.
- **Detail:** This is the highest-value drift this round (flagged in shared worklog Task `0-setup`). A reader trusting CLAUDE.md would `pip install litellm structlog pydantic-settings ...` expecting them to be needed — they aren't, and installing them adds ~50 transitive packages for no benefit. CLAUDE.md is the primary agent-facing entry doc; the claim is also mirrored in tra-prototype/README.md:103-105 (TRA-C4-002 below) and internally contradicted by tra-prototype/SKILL.md:265 which says "Dependencies trimmed (TRA-017, fixed in Round 3): removed 6 unused deps". So three docs disagree about the same finding.
- **Suggested fix:** Replace CLAUDE.md:51 with: "**Dependency hygiene (TRA-017, fixed in Round 3):** 6 unused deps (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) were removed from `pyproject.toml` in commit `a3cd2c1`. Install footprint dropped from ~70 to ~15 packages. If structured logging (Phase 6.3.1) is later implemented, `structlog` should be re-added at that time."
- **Round 3 status:** New (the R3 close `b783745` was before the `a3cd2c1` dep trim landed in the R3→R4 remediation window; CLAUDE.md was not back-filled).

### TRA-C4-002: tra-prototype/README.md "Known gaps" TRA-017 entry — same staleness as TRA-C4-001
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-status
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:103-105` — "**Dependency hygiene** (TRA-017): `litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio` are listed but unused."
  - Code reality: Same as TRA-C4-001 — `pyproject.toml` has 6 runtime + 3 dev deps; none of the 6 listed packages appear.
- **Detail:** Mirror of TRA-C4-001 in the prototype README. Internally contradicts `tra-prototype/SKILL.md:265` (same prototype, same repo): "Dependencies trimmed (TRA-017, fixed in Round 3): removed 6 unused deps (...) from `pyproject.toml`. Install footprint dropped from ~70 packages to ~15."
- **Suggested fix:** Replace `tra-prototype/README.md:103-105` with: "**Dependency hygiene** (TRA-017, fixed in Round 3): 6 unused deps (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) removed from `pyproject.toml` in commit `a3cd2c1`. Install footprint dropped from ~70 to ~15 packages."
- **Round 3 status:** New (post-R3-close drift).

### TRA-C4-003: tra-prototype/SKILL.md §7 "Quality gates" claims "174 tests across 16 test files" — actual is 199 tests
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-count
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:243-244` — "All four gates must be green. The full suite is **174 tests** across 16 test files, including:"
  - Code reality: `python -m pytest tests/ -q` at HEAD `805a8f8` reports **199 passed in 1.16s** (verified). Round 3 closed at `b783745` with 174 tests; the 6 R3→R4 remediation commits added 25 new tests (TRA-088, TRA-089, TRA-093, TRA-096, TRA-097, TRA-098, TRA-073-078 regression classes plus the e2e runner). Test-file count is still 16 `test_*.py` (technically accurate), but the **174 → 199 test count drift is 14.4%**, well above the 10% materiality threshold.
- **Detail:** This is the second-most-cited test-count claim in the repo (the first is status.md's banner, TRA-C4-008 below). A user reading SKILL.md to gauge the engine's test coverage would underestimate by 25 tests (14%). The "16 test files" half of the claim is technically accurate for `test_*.py` files (16 collected by pytest) but misleading if the reader counts `conftest.py` and `run_e2e_translation.py` (total 18 `.py` files in `tests/`).
- **Suggested fix:** Update `tra-prototype/SKILL.md:243-244` to: "All four gates must be green. The full suite is **199 tests** across 16 test files (`test_*.py`) plus `conftest.py` and `tests/run_e2e_translation.py`, including:"
- **Round 3 status:** New (drift introduced by R3→R4 remediation commits adding 25 tests).

### TRA-C4-004: tra-prototype/SKILL.md §7 list of TDD-regression test IDs in `test_outstanding_findings.py` is materially stale (lists 22 IDs, actual 34; phantom TRA-044; omits 13 real test classes)
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-file-list
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:245-247` — "`test_outstanding_findings.py` — TDD regression tests named after finding IDs (TRA-001, 002, 004, 006, 007, 008, 009, 012, 013, 014, 032, 033, 036, 037, 039, 041, 044, 049, 050, 051, 053, 054)"
  - Code reality: `grep -E "^class TestTRA[0-9]+" tests/test_outstanding_findings.py` returns **34 test classes** at HEAD: TRA-001, 002, 004, 006, 007, 008, 009, 012, 013, 014, 032, 033, 036, 037, **038**, 039, 041, 049, 050, 051, 053, 054, **073, 074, 075, 076, 077, 078, 088, 089, 093, 096, 097, 098**.
    - The list includes **TRA-044** — but `grep -n "TRA.044\|TRA044" tests/test_outstanding_findings.py` returns **no match**. There is no `TestTRA044*` class. The doc claim is a phantom.
    - The list omits **13 real test classes** added during R3 remediation: TRA-038, 073, 074, 075, 076, 077, 078, 088, 089, 093, 096, 097, 098. All 13 are the test classes that enforce the R3 fixes — the most important classes in the file.
- **Detail:** A user reading SKILL.md to find the regression test for (say) TRA-093 would conclude no test exists and might re-file the finding. The phantom TRA-044 entry is the more pernicious bug: it implies a test exists for a finding whose fix was never TDD-enforced (TRA-044 was a Track E2 finding; per the R3 register, the `isinstance(exc, Unrecoverable)` branch fix has no regression test of its own — it's only covered incidentally). The list also omits TRA-038, which IS the test class that defines the current PARTIAL status of TRA-038 (its docstring explicitly notes "full production wiring deferred") — readers consulting SKILL.md miss this important nuance.
- **Suggested fix:** Replace `tra-prototype/SKILL.md:245-247` with: "`test_outstanding_findings.py` — TDD regression tests named after finding IDs (34 classes): TRA-001, 002, 004, 006, 007, 008, 009, 012, 013, 014, 032, 033, 036, 037, 038, 039, 041, 049, 050, 051, 053, 054, 073, 074, 075, 076, 077, 078, 088, 089, 093, 096, 097, 098."
- **Round 3 status:** New (drift introduced by R3 remediation adding 13 new test classes).

### TRA-C4-005: tra-prototype/SKILL.md §8 "Audit remediation status" claims "Remaining 24 Round 2 findings (not yet fixed): TRA-016 ... TRA-017 ... TRA-026 ..." — but TRA-016/017/026 are all FIXED; internally contradicts SKILL.md:265
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-status + internal contradiction
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:316-323` — "**Remaining 24 Round 2 findings** (not yet fixed): TRA-001 (partial, full per-leaf segment translation), TRA-016 (dead `count_blocking` stub), TRA-017 (unused deps), TRA-026 (dead `cache.expire` config), TRA-038 (3 of 5 exception types never raised), TRA-040 (EXCEPTION_HANDLER/HALT_ERROR not KernelStates), TRA-042 (structural verification heading-count-only), TRA-052/055/056/057/058 (test coverage gaps), TRA-059/060/061/062/063/064/065/066/067/068/069/070 (doc staleness + minor code quality). See `../docs/audit/round2/master_findings_register.json` for the full machine-readable register."
  - Code reality (cross-checked vs R4 baseline + HEAD source):
    - TRA-016: **FIXED** — `grep -n "count_blocking" tra/diagnostics.py` returns no match. Method removed.
    - TRA-017: **FIXED** — `pyproject.toml` has 6 runtime + 3 dev deps; the 6 listed unused deps are gone (commit `a3cd2c1`).
    - TRA-026: **FIXED** — `grep -n "expire" tra/config.py tra-prototype/config.yaml` returns no `cache.expire` config field (only `expire=None` in `cache.py:128`, the correct diskcache API).
    - TRA-038: **PARTIAL** (was PERSISTENT) — exceptions are now routable via `recovery.py:155-197` but still never raised in production (commit `632bed2`).
  - Internal contradiction: SKILL.md:265 says "Dependencies trimmed (TRA-017, fixed in Round 3)" while SKILL.md:317 lists TRA-017 as "not yet fixed". Same file, opposite claims, 52 lines apart.
- **Detail:** A reader scanning §8's "Remaining ... not yet fixed" list to triage Round 4 work would re-prioritize 3 already-fixed findings (TRA-016/017/026), wasting cycles. The internal contradiction (TRA-017 listed as both "fixed" and "not yet fixed" in the same file) is the most damaging aspect — it erodes trust in the entire §8 section. The "Round 1 carry over" preamble at SKILL.md:278-280 has the same staleness: "TRA-016 persistent dead code, TRA-017 persistent unused deps, TRA-026 persistent dead config" — all three are no longer persistent.
- **Suggested fix:** Replace SKILL.md:316-323 with an updated summary: "**Remaining Round 1+2 findings not yet fixed at HEAD `805a8f8`** (per Round 4 baseline): TRA-001 (partial), TRA-038 (partial — routable but not raised), TRA-040 (PERSISTENT, intentional), TRA-042 (PERSISTENT), TRA-072 (PERSISTENT — only one conflict pair arbitrated), TRA-079 (PERSISTENT — cache HMAC deferred), TRA-099 (PERSISTENT — CLI does not pass `registry=`). TRA-016, TRA-017, TRA-026 are **FIXED**. TRA-052–058 + TRA-059–070 were collapsed into the Round 3 master register (see `../docs/audit/round3/master_findings_register_r3.json`)."
- **Round 3 status:** New (post-R3-close drift; the R3 remediation commits changed the status of TRA-016/017/026/038 without back-filling §8).

### TRA-C4-006: tra-prototype/SKILL.md "Audit artifacts" section omits Round 3 deliverables (and Round 4 in-progress)
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / incomplete-doc
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:327-332` — "**Round 1**: `../docs/audit/` — `TRA_Prototype_Audit_Report.docx`, ... **Round 2**: `../docs/audit/round2/` — `TRA_Prototype_Audit_Report_r2.docx`, ..."
  - Code reality: `ls /home/z/my-project/Translation-Runtime-Architecture/docs/audit/round3/` returns 13 files including `TRA_Prototype_Audit_Report_r3.docx`, `TRA_audit_findings_register_r3.xlsx`, `TRA_audit_severity_heatmap_r3.png`, `master_findings_register_r3.json`, `remediation_plan.md`, `track_{r3,a3,b3,c3,d3,e3,f3}_findings.md`. `ls docs/audit/round4/` returns 4 files (R4 audit in progress: `track_r4_baseline.md`, `track_a4_findings.md`, `track_b4_findings.md`).
- **Detail:** Round 3 closed before this SKILL.md revision; the §"Audit artifacts" list was not updated. Minor — the section is a navigational aid, not a status claim. But the doc claims to enumerate audit artifacts and is now incomplete.
- **Suggested fix:** Add to SKILL.md:332: "- **Round 3**: `../docs/audit/round3/` — `TRA_Prototype_Audit_Report_r3.docx`, `TRA_audit_findings_register_r3.xlsx`, `master_findings_register_r3.json`, `remediation_plan.md`, per-track findings (`track_{r3,a3,b3,c3,d3,e3,f3}_findings.md`)\n- **Round 4** (in progress): `../docs/audit/round4/` — `track_r4_baseline.md`, `track_{a4,b4,c4,d4,e4,f4}_findings.md`"
- **Round 3 status:** New (R3 deliverables landed after the SKILL.md §"Audit artifacts" revision).

### TRA-C4-007: tra-prototype/README.md:109-112 same omission — references only Round 1 + Round 2 audit artifacts
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / incomplete-doc
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:109-112` — "See `docs/audit/round2/TRA_audit_findings_register_r2.xlsx` for the full 41-finding Round 2 audit register and `docs/audit/round2/TRA_Prototype_Audit_Report_r2.docx` for the narrative report. Round 1 deliverables are in `docs/audit/` (top level)."
  - Code reality: `docs/audit/round3/` contains the 36-finding R3 register + report + per-track findings + remediation plan (13 files). `docs/audit/round4/` is in progress.
- **Detail:** Mirror of TRA-C4-006. tra-prototype/README.md is the prototype's landing README; pointing readers only at R1+R2 artifacts misses the most recent (and most action-relevant) R3 register.
- **Suggested fix:** Append to `tra-prototype/README.md:112`: "Round 3 deliverables (36 findings: 2 BLOCKING both fixed, 18 WARNING, 16 INFO) are in `docs/audit/round3/`; Round 4 audit is in progress in `docs/audit/round4/`."
- **Round 3 status:** New.

### TRA-C4-008: status.md STALE banner itself is stale — says "174+" but actual test count at HEAD is 199
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-count
- **Evidence:**
  - Doc claim: `status.md:1` — "> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1` and references '103 pytest passing'. The actual test count at HEAD is **174+** (see `tra-prototype/SKILL.md` §7 for current count). ..."
  - Code reality: `python -m pytest tests/ -q` at HEAD `805a8f8` returns **199 passed**. The banner's "174+" was accurate at the moment the banner was written (R3 close `b783745`) but is now itself 25 tests (14%) behind. The body's "103 pytest passing" at `status.md:46` remains frozen at the `4d97aa1` session and is acknowledged by the banner; the banner is the part that has now drifted.
- **Detail:** The banner's purpose was to warn readers that the body is stale and point them at the current count. By claiming "174+" when the actual is 199, the banner now understates the drift by 25 tests — a reader sees "174+" and concludes the body is ~70 tests out of date (174 − 103), when in fact it's ~96 tests out of date (199 − 103). R4 baseline TRA-085 marks this PARTIAL. The banner's reference to "see `tra-prototype/SKILL.md` §7 for current count" sends readers to a §7 that *also* says 174 (TRA-C4-003) — so the cross-reference is broken too.
- **Suggested fix:** Update `status.md:1` banner: "... The actual test count at HEAD is **199** (see `CLAUDE.md` → 'Prototype engine status' for current state). ..." (Change "174+" → "199"; redirect the cross-reference to CLAUDE.md since SKILL.md §7 is also stale.)
- **Round 3 status:** Carry-over / partial (TRA-085 was PARTIAL in R4 baseline — banner exists but is itself stale).

### TRA-C4-009: implementation_plan.md "File Structure Summary" missing 6 modules + 5 test files (carry-over, unchanged)
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / stale-file-list
- **Evidence:**
  - Doc claim: `implementation_plan.md:305-351` — File Structure Summary lists 10 modules under `tra/` (`__init__.py`, `kernel.py`, `memory.py`, `isa.py`, `policy.py`, `diagnostics.py`, `cache.py`, `anchor.py`, `utils.py`, `exceptions.py`) + `modules/{__init__,registry,zh_en,base}.py`; lists 13 files under `tests/` (`conftest.py` + 12 `test_*.py`).
  - Code reality: `ls tra-prototype/tra/*.py` returns **16** `.py` files (the 10 listed + `benchmark.py`, `config.py`, `hitl.py`, `recovery.py`, `reporting.py`, `validate.py` — 6 unlisted). `ls tra-prototype/tests/*.py` returns **18** `.py` files (`conftest.py` + 16 `test_*.py` + `run_e2e_translation.py`); the plan omits `test_e2e_to_translate.py`, `test_tra043_protocol.py`, `test_tra047_config_robustness.py`, `test_tra071_broken_markdown.py`, and `run_e2e_translation.py` (5 unlisted).
- **Detail:** Carry-over from R3 (TRA-C2-011 / R4 TRA-087). The R4 baseline noted this is "PERSISTENT and slightly worse" — R3 remediation added 4 new test files (`test_e2e_to_translate.py`, `test_tra043_protocol.py`, `test_tra047_config_robustness.py`, `test_tra071_broken_markdown.py`) and commit `805a8f8` added `run_e2e_translation.py`, none of which were back-filled into the plan doc. The plan is a Phase-0 planning snapshot; `CLAUDE.md:17-31` "Layout" section is the authoritative current file inventory and lists all 16 modules accurately. Readers should prefer CLAUDE.md.
- **Suggested fix:** Either (a) add a header note at `implementation_plan.md:305`: "> File structure below is the Phase-0 planning snapshot; for the current file inventory see `CLAUDE.md` → 'Layout (where behavior lives)'." (preferred for a historical planning doc), or (b) update the snapshot to include the 6 missing modules + 5 missing test files.
- **Round 3 status:** Carry-over (TRA-C2-011; TRA-087 PERSISTENT).

### TRA-C4-010: implementation_plan.md "Dependencies" table lists 15 packages — 6 of them (`litellm`, `structlog`, `pydantic-settings`, `mdit_py_plugins`, `pytest-asyncio`, `black`) were removed from `pyproject.toml`
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / stale-file-list
- **Evidence:**
  - Doc claim: `implementation_plan.md:357-389` — Dependencies table lists 15 packages: `pydantic`, `pydantic-settings`, `markdown-it-py`, `mdit_py_plugins`, `diskcache`, `litellm`, `pyyaml`, `structlog`, `click`, `rich`, `pytest`, `pytest-asyncio`, `ruff`, `black`, `mypy`.
  - Code reality: `pyproject.toml` at HEAD has **9** packages: 6 runtime (`pydantic`, `markdown-it-py`, `diskcache`, `pyyaml`, `click`, `rich`) + 3 dev (`pytest`, `ruff`, `mypy`). The 6 packages `litellm`, `structlog`, `pydantic-settings`, `mdit_py_plugins`, `pytest-asyncio`, `black` were removed in commit `a3cd2c1` (TRA-017 fix).
- **Detail:** Same root cause as TRA-C4-001/002 — the `a3cd2c1` dep trim was not back-filled into the planning doc. The Dependencies table is a planning artifact (the doc dates from Phase 0), so the staleness is less material than in CLAUDE.md, but a new contributor copying the table into a fresh install would pull 6 unnecessary packages.
- **Suggested fix:** Add a header note at `implementation_plan.md:355`: "> Dependencies below are the Phase-0 planning list; the current `pyproject.toml` has 6 runtime + 3 dev deps (see TRA-017 fix in `a3cd2c1`). The 6 packages marked removed (`litellm`, `structlog`, `pydantic-settings`, `mdit_py_plugins`, `pytest-asyncio`, `black`) are no longer installed."
- **Round 3 status:** New (drift introduced by `a3cd2c1` dep trim).

### TRA-C4-011: implementation_plan.md Phase 0.1.5 subcommand parenthetical lists 3 subcommands — actual CLI has 4 (missing `validate`) (carry-over)
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / stale-count
- **Evidence:**
  - Doc claim: `implementation_plan.md:22` — "[x] 0.1.5 Set up CLI entry point skeleton (tra_cli.py with translate, cache-clear, audit subcommands)"
  - Code reality: `tra_cli.py` implements **4** subcommands: `translate` (line 66), `cache-clear` (line 131), `audit` (line 152), `validate` (line 214). The `validate` subcommand was added in Phase 5 (item 5.1.4 at `implementation_plan.md:223` is also marked `[x]`). `tra_cli.py:1-7` docstring lists all 4.
- **Detail:** Carry-over from R2/R3 (TRA-C2-012). Phase 0.1.5 was authored when only 3 subcommands were planned; `validate` was added later (Phase 5). The checkbox is correctly `[x]` (the skeleton IS set up), but the parenthetical "with translate, cache-clear, audit subcommands" understates the actual CLI. A reader scanning the plan would miss that `validate` exists. Minor.
- **Suggested fix:** Update `implementation_plan.md:22` parenthetical to: "(tra_cli.py with translate, validate, audit, cache-clear subcommands)".
- **Round 3 status:** Carry-over (TRA-C2-012; PERSISTENT across R3 and R4).

### TRA-C4-012: implementation_plan.md Phase 0.1.2 mentions "formatting (black)" — black was removed; ruff handles formatting
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / stale-tooling
- **Evidence:**
  - Doc claim: `implementation_plan.md:19` — "[x] 0.1.2 Configure linting (ruff), formatting (black), type checking (mypy strict), testing (pytest)"
  - Code reality: `pyproject.toml` dev deps list only `pytest`, `ruff`, `mypy` (no `black`). `ruff format` is the formatter (per `CLAUDE.md:37`, `SKILL.md:236-238`, and `tra-prototype/README.md:68`). `black` was removed in commit `a3cd2c1` as part of TRA-017.
- **Detail:** Same root cause as TRA-C4-010. Phase 0.1.2 was authored when the plan called for `black`; the project later consolidated on `ruff format`. Minor — the checkbox is correctly `[x]` and the actual tooling is well-documented elsewhere.
- **Suggested fix:** Update `implementation_plan.md:19` to: "[x] 0.1.2 Configure linting + formatting (ruff), type checking (mypy strict), testing (pytest)".
- **Round 3 status:** New (drift introduced by `a3cd2c1` dep trim).

### TRA-C4-013 (BLOCKING): tra-prototype/README.md "Commands" section uses bare `tra_cli.py` invocations — file is not executable, has no shebang, and is not on PATH; commands fail as written
- **Severity:** BLOCKING
- **Category:** Doc-vs-Code Consistency / stale-commands
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:23-36` — "```bash\n# Run the full TRA pipeline (Kernel state machine) on a document.\ntra_cli.py translate examples/security_advisory_zh.md -o out.md\n\n# Standalone verifier: ...\ntra_cli.py validate examples/security_advisory_zh.md out.md --level L3\n\n# Summarize an audit trace ...\ntra_cli.py audit ./audit_trace.jsonl --format summary\n\n# Invalidate the deterministic cache ...\ntra_cli.py cache-clear [--pattern <glob>]\n```"
  - Code reality: `ls -la tra-prototype/tra_cli.py` returns mode `-rw-rw-r--` (NOT executable; needs `+x`). `head -1 tra_cli.py` returns `"""TRA prototype CLI.` — **no shebang line**. `pyproject.toml` has **no `[project.scripts]` entry point** (verified: `grep -A5 "scripts\|entry" pyproject.toml` returns nothing relevant). Trying `tra_cli.py --help` from inside `tra-prototype/` returns `bash: tra_cli.py: command not found`. Trying `./tra_cli.py --help` returns `bash: ./tra_cli.py: Permission denied`. Only `python -m tra_cli --help` and `python tra_cli.py --help` work.
  - Cross-doc inconsistency: `README.md:96-110` (root) uses `python -m tra_cli translate ...` (correct). `tra-prototype/SKILL.md:113-178` uses `python -m tra_cli --help`, `python -m tra_cli translate ...`, etc. (correct). Only `tra-prototype/README.md` uses bare `tra_cli.py` (incorrect).
- **Detail:** A user following the tra-prototype/README.md "Commands" section literally will get `command not found` or `Permission denied` on every CLI example. This is the most actively misleading doc issue this round — the README is the prototype's landing README, the first place a new user looks for usage. The 4 commands cover the entire CLI surface (translate, validate, audit, cache-clear), so all 4 are broken. Root cause: the README was authored before the project decided on `python -m tra_cli` as the canonical invocation form, and was not updated when the decision landed.
- **Suggested fix:** Replace all 4 occurrences of `tra_cli.py <subcommand>` in `tra-prototype/README.md:25, 29, 32, 35` with `python -m tra_cli <subcommand>` (or `python tra_cli.py <subcommand>` — both work; `python -m tra_cli` is the form used in root README.md and SKILL.md, so prefer that for consistency).
- **Round 3 status:** New (not flagged in R3 Track C3; the C3 spot-check verified the `tra_cli.py` *docstring* lists 4 subcommands correctly but did not exercise the README's *invocation form*).

### TRA-C4-014: tra-prototype/SKILL.md §8 "Round 1 carry over" claim — "TRA-016 persistent dead code, TRA-017 persistent unused deps, TRA-026 persistent dead config" all 3 are now FIXED
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / stale-status
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:278-280` — "**Round 1** (35 findings): 30 fixed, 5 carry over (TRA-001 partial, TRA-006 fixed in Round 2, **TRA-016 persistent dead code, TRA-017 persistent unused deps, TRA-026 persistent dead config**)."
  - Code reality: All 3 are FIXED at HEAD `805a8f8` (per R4 baseline + verified above in TRA-C4-001, TRA-C4-005). `count_blocking` removed from `diagnostics.py`; 6 unused deps removed from `pyproject.toml`; `cache.expire` field removed from `config.py` and `config.yaml`.
- **Detail:** Subset of the broader TRA-C4-005 staleness, called out separately because the phrase "persistent dead code" / "persistent unused deps" / "persistent dead config" is exactly the wording a reader will scan-search for. Same root cause: R3 remediation commits changed the status without back-filling §8.
- **Suggested fix:** Replace `tra-prototype/SKILL.md:278-280` with: "**Round 1** (35 findings): 30 fixed in Round 1, 5 carried into Round 2 — of those 5, TRA-006 was fixed in Round 2, TRA-016/017/026 were fixed in the Round 3 → Round 4 remediation commits (`a3cd2c1`), and TRA-001 remains partial."
- **Round 3 status:** New (drift from R3→R4 remediation).

### TRA-C4-015: tra-prototype/README.md "Known gaps" TRA-006 entry — exact opposite of code reality (carry-over, PERSISTENT from R3)
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / misleading-doc + cross-doc contradiction
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:100-102` — "**Policy Engine scaffolding** (TRA-006, half-fix): terminology severity is now policy-aware but `PolicyResolver` is never invoked in production `verify_output`."
  - Code reality: `tra-prototype/tra/isa.py:565` — `term_wins_over_fluency = _POLICY_RESOLVER.wins(PolicyPriority.TERMINOLOGICAL_CONSISTENCY, PolicyPriority.TARGET_FLUENCY)` is invoked inside `verify_output`. Test `TestTRA006PolicyResolverInvokedInProduction` at `tests/test_outstanding_findings.py` monkeypatches `_POLICY_RESOLVER.wins` to return `False` and asserts severity drops to `WARNING` — empirically proving the resolver IS consulted. R4 baseline TRA-080 status: **FIXED** (CLAUDE.md:50 was updated to "fixed in Round 3" in commit `a3cd2c1`; tra-prototype/README.md:100-102 was NOT updated).
  - Cross-doc contradiction: `CLAUDE.md:50` says "PolicyResolver is now invoked in verify_output via `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)`" — the exact opposite of tra-prototype/README.md:100-102.
- **Detail:** Carry-over from R3 Track C3 (TRA-C3-008, PERSISTENT). The Round 3 remediation commit `a4d0b3a` fixed the CLAUDE.md mirror but not the tra-prototype/README.md mirror. R4 baseline TRA-082 marks the parallel TRA-004 entry as PARTIAL (qualifying clause added); the TRA-006 entry in tra-prototype/README.md received no such mitigation. The claim is the exact opposite of code reality and misleads readers about whether the Policy Engine is functional.
- **Suggested fix:** Replace `tra-prototype/README.md:100-102` with: "**Policy Engine** (TRA-006, fixed in Round 3; TRA-072 partial): `verify_output` consults `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)` to arbitrate canonical-term-leakage severity (`isa.py:565`). However, this is the ONLY conflict pair arbitrated by the resolver (TRA-072); all other severity decisions still use hard-coded conditionals."
- **Round 3 status:** Carry-over (TRA-C3-008; PERSISTENT — same finding, same evidence, no change since R3 close).

### TRA-C4-016: tra-prototype/README.md "Known gaps" TRA-004 entry retains misleading "EntityAmbiguity now route through _recover" phrase (carry-over, PARTIAL from R3)
- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / misleading-doc
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:96-99` — "**Exception recovery** (TRA-004, partial): `BrokenMarkdown` and `EntityAmbiguity` now route through `_recover`; however, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are still never raised in production code paths (TRA-038)."
  - Code reality: `grep -rn "raise EntityAmbiguity" tra/` returns **no match** — `EntityAmbiguity` is never raised in production. Only `BrokenMarkdown` (raised at `isa.py:103, 163`), `GlossaryConflict` (`isa.py:235, 243`), and `Unrecoverable` (`isa.py:666, 678`) reach `_recover` in production. The doc claim is internally contradictory: it says both "EntityAmbiguity now routes through _recover" AND "EntityAmbiguity are still never raised in production code paths" — both can't be true simultaneously in any meaningful sense (routing code exists but is dead).
- **Detail:** Carry-over from R3 (TRA-C3-010 / R4 TRA-082 PARTIAL). R3 remediation commit `a3cd2c1` added the qualifying clause ("however, ... still never raised in production code paths (TRA-038)") but did NOT rewrite the misleading phrase "EntityAmbiguity now route through `_recover`". The phrase still implies the routing is functional. R4 baseline TRA-082 marks this PARTIAL (mitigation added, root phrase retained).
- **Suggested fix:** Replace `tra-prototype/README.md:96-99` with: "**Exception recovery** (TRA-004, partial): `BrokenMarkdown`, `GlossaryConflict`, and `Unrecoverable` reach `_recover` in production (`isa.py:103-105, 235-247, 656-678`). However, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are defined and routed by `recovery.py` but never raised in production code paths (TRA-038) — their recovery procedures are dead code in practice."
- **Round 3 status:** Carry-over (TRA-C3-010 / TRA-082 PARTIAL — same as R3 close, no change).

### TRA-C4-017: AGENTS.md "Files and roles" table omits 7+ meta-docs and the prototype's own SKILL.md/README.md (carry-over, PERSISTENT from R2)
- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / incomplete-doc
- **Evidence:**
  - Doc claim: `AGENTS.md:9-15` — "Files and roles" table lists only the 5 spec files (`TRA-SPECIFICATION.md`, `TRA-ISA-REFERENCE.md`, `TRA-MODULE-ZH-EN.md`, `TRA-BENCHMARK-SUITE.md`, `TRA-CONFORMANCE-GUIDE.md`).
  - Code reality: The repo root contains 10 meta/planning docs (`AGENTS.md`, `CLAUDE.md`, `README.md`, `start-here.md`, `prototype.md`, `review-feedback.md`, `review.md`, `status.md`, `implementation_plan.md`, `to_translate.md`) plus the `tra-prototype/` subdirectory with its own `SKILL.md` + `README.md`. AGENTS.md surfaces only 5 spec files in the table (and mentions 5 meta-docs in prose at line 5), leaving 5+ docs unmentioned — including `implementation_plan.md` (the per-item Phase 0-7 state) and `tra-prototype/SKILL.md` (the prototype usage guide).
- **Detail:** Carry-over from R2 (TRA-C2-016). AGENTS.md is the agent-facing entry doc — the file an AI agent reads first. A new agent won't know `implementation_plan.md` or `tra-prototype/SKILL.md` exist. R3 and R4 did not address this.
- **Suggested fix:** Either expand the "Files and roles" table to include meta-docs, OR add a second short table "Meta-docs & planning" listing `CLAUDE.md`, `AGENTS.md`, `README.md`, `start-here.md`, `prototype.md`, `review.md`, `review-feedback.md`, `status.md`, `implementation_plan.md`, `to_translate.md`, `tra-prototype/SKILL.md`, `tra-prototype/README.md` with one-line roles.
- **Round 3 status:** Carry-over (TRA-C2-016; PERSISTENT across R2 → R3 → R4).

---

## Round 3 carry-over status matrix (Track C scope)

| Round 3 ID | Title | Round 4 status |
|---|---|---|
| TRA-C2-009 | implementation_plan.md "external codebase" | **FIXED** (TRA-086; phrase removed in `a3cd2c1`) |
| TRA-C2-010 | prototype.md "external codebase" | **FIXED** (TRA-086; phrase removed in `a3cd2c1`) |
| TRA-C2-011 | implementation_plan.md File Structure Summary | **PERSISTENT** (TRA-087; now missing 6 modules + 5 test files — see TRA-C4-009) |
| TRA-C2-012 | implementation_plan.md Phase 0.1.5 subcommands | **PERSISTENT** (still missing `validate` — see TRA-C4-011) |
| TRA-C2-013 | status.md frozen session log | **PARTIAL** (banner added but banner itself is stale — see TRA-C4-008) |
| TRA-C2-014 | docs/audit/ duplication undocumented | **PERSISTENT** (no change; not re-flagged as new finding this round) |
| TRA-C2-016 | AGENTS.md "Files and roles" omissions | **PERSISTENT** (table unchanged — see TRA-C4-017) |
| TRA-C3-007 | CLAUDE.md TRA-006 entry | **FIXED** (TRA-080; CLAUDE.md:50 now says "fixed in Round 3; TRA-072 partial") |
| TRA-C3-008 | tra-prototype/README.md TRA-006 mirror | **PERSISTENT** (still says "never invoked" — see TRA-C4-015) |
| TRA-C3-009 | tra-prototype/README.md Architecture table Policy path | **FIXED** (TRA-081; line 49 now correctly shows `tra/policy.py`) |
| TRA-C3-010 | tra-prototype/README.md TRA-004 EntityAmbiguity phrase | **PARTIAL** (TRA-082; qualifying clause added, misleading phrase retained — see TRA-C4-016) |
| TRA-C3-011 | README.md wrong path `tra-prototype/implementation_plan.md` | **FIXED** (TRA-083; path corrected to `implementation_plan.md`) |
| TRA-C3-012 | AGENTS.md boundary contradiction | **FIXED** (TRA-084; both lines now acknowledge the subdirectory override) |

**Net delta vs Round 3:** 6 FIXED, 5 PERSISTENT, 2 PARTIAL. No REGRESSED findings (every R3 fix that landed in the 6 remediation commits is still present at HEAD).

## Per-doc summary table

| Doc | Total claims checked | Stale claims | New findings |
|---|---|---|---|
| `CLAUDE.md` | 14 | 1 | TRA-C4-001 (TRA-017 "persistent" stale) |
| `AGENTS.md` | 8 | 1 (carry) | TRA-C4-017 (Files-and-roles omissions, carry) |
| `README.md` | 22 | 0 | — (all claims verified accurate at HEAD) |
| `implementation_plan.md` | 38 | 4 | TRA-C4-009 (File Structure Summary, carry), TRA-C4-010 (Dependencies table), TRA-C4-011 (Phase 0.1.5 subcommands, carry), TRA-C4-012 (Phase 0.1.2 black) |
| `status.md` | 4 | 1 | TRA-C4-008 (banner "174+" stale) |
| `prototype.md` | 6 | 0 | — (scope note "external codebase" was FIXED in R3/R4; Phase-0 project sketch is clearly labeled as planning) |
| `review-feedback.md` | 6 | 0 | — (scope note accurate; design micro-docs are historical planning) |
| `review.md` | 8 | 0 | — (collapsed state labels acknowledged via CLAUDE.md:63 cross-reference; historical external review, no current-state claims) |
| `start-here.md` | 9 | 0 | — (line 23 explicitly notes collapsed labels are abbreviated renderings) |
| `to_translate.md` | 7 | 0 | — (describes TRA framework, no prototype-specific count claims; collapsed labels per review.md pattern) |
| `tra-prototype/SKILL.md` | 48 | 5 | TRA-C4-003 (174 tests → 199), TRA-C4-004 (test ID list), TRA-C4-005 (§8 "remaining 24"), TRA-C4-006 (Audit artifacts missing R3), TRA-C4-014 (§8 Round 1 carry-over) |
| `tra-prototype/README.md` | 26 | 5 | TRA-C4-002 (TRA-017), TRA-C4-007 (R3 deliverables missing), TRA-C4-013 (BLOCKING: bare `tra_cli.py`), TRA-C4-015 (TRA-006, carry), TRA-C4-016 (TRA-004, carry) |
| **Totals** | **196** | **25** | **17** (12 new + 5 carry-over re-flagged) |

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture

# HEAD verification
git log --oneline -3
# → fb4cdac docs(audit): Round 4 audit Batch 1 — Tracks R4/A4/B4
# → 805a8f8 feat(tra): E2E translation output + TDD remediation of 5 more Round 3 findings
# → 632bed2 fix(tra): TDD remediation of spec conformance findings (TRA-038, TRA-073)

# File counts at HEAD
cd tra-prototype
ls tra/*.py | wc -l                    # → 16
ls tra/modules/*.py | wc -l            # → 4
find tra -name "*.py" | wc -l          # → 20  (matches SKILL.md §7 "20 source files")
ls tests/*.py | wc -l                  # → 18  (16 test_*.py + conftest.py + run_e2e_translation.py)
ls tests/test_*.py | wc -l             # → 16  (matches SKILL.md §7 "16 test files" by test_* counting)

# Test count at HEAD (key stale claim)
python -m pytest tests/                # → 199 passed in 1.16s

# Test classes in test_outstanding_findings.py (key stale list)
grep -E "^class TestTRA[0-9]+" tests/test_outstanding_findings.py | wc -l   # → 34
grep -E "^class TestTRA[0-9]+" tests/test_outstanding_findings.py
# → 34 classes covering TRA-001,002,004,006,007,008,009,012,013,014,032,033,
#    036,037,038,039,041,049,050,051,053,054,073,074,075,076,077,078,088,089,
#    093,096,097,098

# Phantom TRA-044 check
grep -n "TRA.044\|TRA044" tests/test_outstanding_findings.py   # → no match (phantom in SKILL.md:247)

# Dependency counts at HEAD
python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('runtime:', len(d['project']['dependencies'])); print('dev:', len(d['project']['optional-dependencies']['dev']))"
# → runtime: 6  dev: 3   (CLAUDE.md:51 / tra-prototype/README.md:103-105 claim 6 unused are still listed → STALE)

# Code-level evidence for finding statuses
grep -n "is_translated_slug" tra/anchor.py     # → TRA-093 fix at anchor.py:100,156 (FIXED)
grep -n "out = out" tra/isa.py                   # → only comment at isa.py:502 (TRA-073 FIXED)
grep -n "repaired = repaired" tra/isa.py         # → isa.py:654 (TRA-A4-011 NEW no-op, parallel to TRA-073)
grep -n "_POLICY_RESOLVER.wins\|_POLICY_RESOLVER.resolve" tra/ -r   # → 1 call site at isa.py:565 (TRA-006 FIXED, TRA-072 PERSISTENT)
grep -rn "raise UnknownTerm\|raise CertaintyConflict\|raise EntityAmbiguity" tra/   # → no match (TRA-038 PARTIAL)
grep -rn "raise BrokenMarkdown\|raise GlossaryConflict\|raise Unrecoverable" tra/   # → 6 matches (only 3 exception types raised in production)
grep -n "TRAKernel" tra_cli.py                   # → line 107: `kernel = TRAKernel(cfg, interactive=interactive)` — no registry= (TRA-099 PERSISTENT)
grep -n "model_dump_json\|json.loads" tra/cache.py   # → cache.py:113,128 (TRA-077 FIXED — JSON not pickle)
grep -n "count_blocking" tra/diagnostics.py      # → no match (TRA-016 FIXED)
grep -n "expire" tra/config.py                   # → no match (TRA-026 FIXED — only `expire=None` in cache.py:128)

# CLI invocation form check (TRA-C4-013 BLOCKING)
ls -la tra_cli.py                                 # → -rw-rw-r-- (NOT executable)
head -1 tra_cli.py                                # → """TRA prototype CLI. (NO shebang)
grep -A3 "scripts\|entry_points" pyproject.toml   # → no [project.scripts] entry point
tra_cli.py --help                                 # → bash: tra_cli.py: command not found
./tra_cli.py --help                               # → bash: ./tra_cli.py: Permission denied
python -m tra_cli --help                          # → works (Usage: tra_cli.py [OPTIONS] COMMAND [ARGS]...)

# Benchmark cases (TRA-031 spot-check — accurate)
cat tests/benchmark/cases/*.jsonl | wc -l         # → 22 (matches CLAUDE.md:53 / tra-prototype/README.md:106-107 "22 of 24 spec cases")

# Audit deliverables directory contents
ls /home/z/my-project/Translation-Runtime-Architecture/docs/audit/round3/   # → 13 files (R3 closed; SKILL.md §"Audit artifacts" omits)
ls /home/z/my-project/Translation-Runtime-Architecture/docs/audit/round4/   # → 4 files (R4 in progress)

# Per-doc grep for stale phrases
grep -n "TRA-017, persistent\|TRA-017.*persistent" CLAUDE.md tra-prototype/README.md
# → CLAUDE.md:51 + tra-prototype/README.md:103 (both stale)
grep -n "174" status.md tra-prototype/SKILL.md
# → status.md:1 (banner "174+") + tra-prototype/SKILL.md:243 ("174 tests") — both stale (actual 199)
grep -n "PolicyResolver.*never invoked\|never invoked in production" tra-prototype/README.md
# → line 101 (TRA-C3-008 carry-over, PERSISTENT)
grep -n "EntityAmbiguity now route" tra-prototype/README.md
# → line 97 (TRA-C3-010 carry-over, PARTIAL)
grep -n "external codebase" implementation_plan.md prototype.md
# → no match (TRA-086 FIXED — both scope notes updated)
grep -n "tra-prototype/implementation_plan" README.md tra-prototype/README.md
# → no match (TRA-083 FIXED — path corrected)
grep -n "different repo\|OTHER THAN" AGENTS.md
# → line 5 + line 25 (TRA-084 FIXED — both acknowledge override)
```

## Conclusion

Round 4 confirms the shared worklog's Task `0-setup` observation that CLAUDE.md's "Known gaps" section is materially stale, and extends the finding across the documentation surface. **The R3→R4 remediation commits (`df9a590` → `805a8f8`) landed 14 source-code fixes but did not back-fill the corresponding documentation.** Three docs now contain claims that are the *exact opposite* of code reality: CLAUDE.md:51 and tra-prototype/README.md:103-105 say TRA-017 is "persistent" (it's FIXED); tra-prototype/README.md:100-102 says `PolicyResolver` is "never invoked in production" (it IS invoked at `isa.py:565`); tra-prototype/SKILL.md:243 says "174 tests" (actual is 199). One BLOCKING issue exists: tra-prototype/README.md's "Commands" section uses bare `tra_cli.py` invocations that fail because the file is not executable, has no shebang, and is not on PATH.

The most material drifts a user would actually be misled by are: (1) the TRA-017 "persistent" claim across CLAUDE.md + tra-prototype/README.md (a user would install 6 unnecessary packages adding ~50 transitive deps); (2) the BLOCKING CLI invocation form in tra-prototype/README.md (every CLI example fails as written); (3) the SKILL.md §8 "Remaining 24 Round 2 findings (not yet fixed)" list (3 of the listed findings — TRA-016/017/026 — are now FIXED, and the same file internally contradicts itself 52 lines later about TRA-017's status). The Round 3 carry-over of TRA-C3-008 (tra-prototype/README.md TRA-006 mirror) is the longest-standing unfixed finding — CLAUDE.md's parallel entry was fixed in commit `a3cd2c1` but the prototype README was not.

The 5 PERSISTENT Round-3 carry-overs (TRA-C2-011, -012, -014, -016, TRA-C3-008) plus the 2 PARTIALs (TRA-C2-013/TRA-C4-008, TRA-C3-010/TRA-C4-016) form a backlog of 7 doc fixes that have survived two audit rounds without being addressed; they should be batched into a single doc-hygiene commit alongside the 12 new findings identified here. No source code was modified (audit-only).
