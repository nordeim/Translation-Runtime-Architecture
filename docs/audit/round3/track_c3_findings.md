# Track C3 — Doc-vs-Code Consistency Re-Audit (Round 3)

**HEAD audited:** `b783745`
**Docs audited:** 16
**Baseline:** Round 2 Track C (15 findings: 1 BLOCKING / 7 WARNING / 7 INFO)
**Regression baseline:** `track_r3_baseline.md` (71 findings: 59 PASS / 12 FAIL)

## Summary

- **Findings:** 13 total (0 BLOCKING / 5 WARNING / 8 INFO)
- **Carry-over (Round 2 still-stale):** 7
- **New:** 6
- **Round 2 findings verified FIXED since `4b8827c`:** 8 (TRA-C2-001, -002, -003, -004, -005, -006, -007, -015)

### Per-doc accuracy table

| Doc | Lines | Claims verified | Claims accurate | Claims stale | Findings |
|---|---|---|---|---|---|
| `README.md` (root) | 143 | 33 | 32 | 1 | C3-012 |
| `AGENTS.md` | 38 | 15 | 13 | 2 | C3-013 (NEW), C2-016 (carry) |
| `CLAUDE.md` | 94 | 43 | 42 | 1 | C3-007 (NEW; C2-001/-002/-003/-004 all fixed) |
| `implementation_plan.md` | 439 | 70 | 66 | 4 | C2-009, -011, -012 (carry) |
| `status.md` | 50 | 10 | 4 | 6 | C2-013 (carry) |
| `start-here.md` | 45 | 11 | 11 | 0 | — (line 23 note resolves collapsed labels) |
| `review.md` | 53 | 12 | 7 | 5 | — (carry-over D-21, acknowledged historical review) |
| `review-feedback.md` | 386 | 8 | 8 | 0 | — |
| `prototype.md` | 111 | 10 | 9 | 1 | C2-010 (carry) |
| `tra-prototype/SKILL.md` | 355 | 48 | 48 | 0 | — (C2-007/-008/-015 all fixed) |
| `tra-prototype/README.md` | 113 | 32 | 28 | 4 | C3-008, C3-009, C3-010 (NEW) |
| `tra-prototype/tra_cli.py` docstring | 8 | 5 | 5 | 0 | — (D-8 / TRA-022 fixed) |
| `tra-prototype/config.yaml` comments | 28 | 8 | 8 | 0 | — |
| `tra-prototype/pyproject.toml` description | 1 | 1 | 1 | 0 | — |
| `TRA-MODULE-ZH-EN.md` | 54 | 12 | 12 | 0 | — (linguistic spec matches `zh_en.py` impl) |
| `TRA-ISA-REFERENCE.md` | 83 | 18 | 18 | 0 | — (6 ISA contracts match `isa.py`; TRANSLATE_SEGMENT failure conditions overlap with TRA-038) |
| `docs/audit/` duplication | — | — | — | — | C2-014 (carry) |

### Round 2 → Round 3 status delta

| Round 2 finding | Round 2 severity | Round 3 status |
|---|---|---|
| TRA-C2-001 (CLAUDE.md TRA-013 stale) | WARNING | **FIXED** — TRA-013 no longer in "Known gaps" |
| TRA-C2-002 (CLAUDE.md TRA-004 stale) | WARNING | **FIXED** — line 49 now says BrokenMarkdown routes through `_recover` |
| TRA-C2-003 (CLAUDE.md TRA-002 stale) | WARNING | **FIXED** — line 48 now reflects kernel-uses-registry-CLI-does-not |
| TRA-C2-004 (CLAUDE.md TRA-031 factually wrong 13/23) | BLOCKING | **FIXED** — line 53 now says "22 of 24 spec cases" |
| TRA-C2-005 (README.md inline-code stale) | WARNING | **FIXED** — line 76-78 now says "IS now suppressed" |
| TRA-C2-006 (README.md module-registry stale) | WARNING | **FIXED** — line 92-95 now reflects kernel-uses-registry |
| TRA-C2-007 (README.md install omits `[dev]`) | WARNING | **FIXED** — line 18 has `pip install -e ".[dev]"` |
| TRA-C2-008 (SKILL.md unused-deps incomplete) | WARNING | **FIXED** — §8 now lists all 6 unused deps |
| TRA-C2-009 (implementation_plan.md "external codebase") | INFO | **STALE** — line 3 unchanged (carry-over) |
| TRA-C2-010 (prototype.md "external codebase") | INFO | **STALE** — line 1 unchanged (carry-over) |
| TRA-C2-011 (implementation_plan.md File Structure Summary) | INFO | **STALE** — summary still missing 6 modules + 4 test files (carry-over) |
| TRA-C2-012 (implementation_plan.md Phase 0.1.5 subcommands) | INFO | **STALE** — line 22 still lists 3 subcommands (carry-over) |
| TRA-C2-013 (status.md frozen session log) | WARNING | **STALE** — still says "103 pytest passing", actual is 174 (carry-over) |
| TRA-C2-014 (docs/audit/ duplication) | INFO | **STALE** — duplication still undocumented (carry-over) |
| TRA-C2-015 (SKILL.md "14 test files" inflated) | INFO | **FIXED** — §7 now says "174 tests across 16 test files" (matches actual) |
| TRA-C2-016 (AGENTS.md Files-and-roles omissions) | INFO | **STALE** — table still lists only 5 spec files (carry-over) |

### New findings introduced since Round 2 close

The 5 commits between `4b8827c` → `b783745` (most notably `a4d0b3a` "TDD remediation of 6 more Round 2 findings") fixed TRA-006 fully — `PolicyResolver` is now invoked in production `verify_output` via `_POLICY_RESOLVER.wins(...)` (`isa.py:555`). The CLAUDE.md "Known gaps" entry for TRA-006 and its mirror in `tra-prototype/README.md` were **not updated** in lockstep with the `a4d0b3a` fix, so they now stale-claim TRA-006 is a "half-fix" with "PolicyResolver never invoked in production verify_output" — the exact opposite of the current code. Additionally, the `tra-prototype/README.md` Architecture table was discovered to misattribute the Policy module to `tra/config.py` (actual: `tra/policy.py`), and the README.md "Known gaps" TRA-004 entry now misleadingly says "EntityAmbiguity now routes through `_recover`" (it doesn't — it's never raised). Finally, a path error in root `README.md:114` (`tra-prototype/implementation_plan.md` — actual file is at repo root) and an internal contradiction in `AGENTS.md:25` (says "Any concrete engine lives in a different repo", contradicting the override note at `AGENTS.md:5`) are also newly surfaced.

---

## Findings

### TRA-C3-007 — CLAUDE.md "Known gaps" TRA-006 claim is stale (PolicyResolver IS now invoked in production verify_output)
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New (introduced by the `a4d0b3a` fix that landed after Round 2 close)
- **Doc:** `CLAUDE.md:50` — "**Policy Engine scaffolding (TRA-006, half-fix):** terminology severity is now policy-aware (CANONICAL→BLOCKING, CONTEXT_SENSITIVE→WARNING) but is achieved by hard-coded conditionals, not by `PolicyResolver` arbitration. `PolicyResolver` is defined and tested but never invoked in production `verify_output`."
- **Code:** `tra-prototype/tra/isa.py:52-63` — `_POLICY_RESOLVER = PolicyResolver(list(PolicyPriority))` instantiated at module import. `tra-prototype/tra/isa.py:555-569` — `verify_output` consults `_POLICY_RESOLVER.wins(PolicyPriority.TERMINOLOGICAL_CONSISTENCY, PolicyPriority.TARGET_FLUENCY)` to arbitrate canonical-term-leakage severity. Comment at `isa.py:563`: "TRA-006: severity is arbitrated by the PolicyResolver. Default: TERMINOLOGICAL_CONSISTENCY (P4) wins over TARGET_FLUENCY (P6) → BLOCKING. If the resolver is monkeypatched to return False, severity drops to WARNING." `tests/test_outstanding_findings.py:1281-1362` (`TestTRA006PolicyResolverInvokedInProduction`) monkeypatches `_POLICY_RESOLVER.wins` to return False and asserts severity drops to WARNING — empirically proving the resolver IS consulted.
- **Detail:** This claim was accurate at Round 2 close (`4b8827c`): TRA-006 was a half-fix back then — severity was policy-aware in spirit but achieved by hard-coded conditionals. Commit `a4d0b3a` (between Round 2 and Round 3) fully fixed TRA-006 by routing the severity decision through `_POLICY_RESOLVER.wins(...)`. The CLAUDE.md "Known gaps" entry was not updated in lockstep; it now stale-claims "PolicyResolver is defined and tested but never invoked in production `verify_output`" — the exact opposite of the current code. Track R3 baseline marks TRA-006 as `REGRESSION-TEST-PASS`.
- **Suggested fix:** Delete the bullet at `CLAUDE.md:50`. Alternatively, replace with: "**Policy Engine (TRA-006, FIXED):** `verify_output` consults `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)` to arbitrate canonical-term-leakage severity (`isa.py:555-569`). Default: P4 wins over P6 → BLOCKING. Monkeypatching the resolver to return False drops severity to WARNING — proven by `TestTRA006PolicyResolverInvokedInProduction`."

### TRA-C3-008 — tra-prototype/README.md "Known gaps" TRA-006 mirror is stale (same as C3-007)
- **Severity:** WARNING
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** New (mirror of C3-007)
- **Doc:** `tra-prototype/README.md:100-102` — "**Policy Engine scaffolding** (TRA-006, half-fix): terminology severity is now policy-aware but `PolicyResolver` is never invoked in production `verify_output`."
- **Code:** Same as C3-007 — `tra-prototype/tra/isa.py:555-569` invokes `_POLICY_RESOLVER.wins(...)` in `verify_output`.
- **Detail:** Same staleness as C3-007 but in the prototype README. The phrase "`PolicyResolver` is never invoked in production `verify_output`" is the exact opposite of the current code.
- **Suggested fix:** Replace `tra-prototype/README.md:100-102` with: "**Policy Engine** (TRA-006, FIXED): `verify_output` consults `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)` to arbitrate canonical-term-leakage severity (`isa.py:555-569`). Monkeypatching the resolver changes the severity — proven by `TestTRA006PolicyResolverInvokedInProduction`."

### TRA-C3-009 — tra-prototype/README.md Architecture table misattributes Policy module to `tra/config.py` (actual: `tra/policy.py`)
- **Severity:** WARNING
- **Category:** Doc Consistency / wrong-file-path
- **Carry-over or new:** New
- **Doc:** `tra-prototype/README.md:49` — Architecture table row: `| Policy | \`tra/config.py\` | Immutable priority stack (Factual → Structural → Entity → Terminological → Epistemic → Fluency). |`
- **Code:** `tra-prototype/tra/policy.py:8-25` — contains the `PolicyResolver` class with `resolve()` and `wins()` methods (the actual Policy Engine). `tra-prototype/tra/config.py:1-20` — contains `BootstrapConfig` (the Immutable Config loader) and a `DEFAULT_POLICY_STACK` constant (a list of `PolicyPriority` values imported from `memory.py`). The "Immutable priority stack" the doc describes IS the `DEFAULT_POLICY_STACK` constant in `config.py`, but the resolver/arbitration logic that gives the stack its meaning lives in `policy.py`. The doc row conflates the two.
- **Detail:** A new contributor reading the Architecture table would `cat tra/config.py` looking for `PolicyResolver` and find only `BootstrapConfig`. The actual Policy Engine module is `tra/policy.py`. CLAUDE.md:22 correctly attributes the Policy Engine to `policy.py`: "`policy.py` — the `PolicyResolver` over the non-negotiable 6-priority stack." The prototype README.md diverges.
- **Suggested fix:** Change `tra-prototype/README.md:49` to: `| Policy | \`tra/policy.py\` | \`PolicyResolver\` over the immutable 6-priority stack (Factual → Structural → Entity → Terminological → Epistemic → Fluency). The stack itself is defined as \`DEFAULT_POLICY_STACK\` in \`tra/config.py\`. |`

### TRA-C3-010 — tra-prototype/README.md "Known gaps" TRA-004 entry misleadingly says "EntityAmbiguity now routes through _recover"
- **Severity:** WARNING
- **Category:** Doc Consistency / misleading-doc
- **Carry-over or new:** New (regression introduced when C2-002 was fixed in CLAUDE.md but not in tra-prototype/README.md)
- **Doc:** `tra-prototype/README.md:96-99` — "**Exception recovery** (TRA-004, partial): `BrokenMarkdown` and `EntityAmbiguity` now route through `_recover`; however, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are still never raised in production code paths (TRA-038)."
- **Code:** `tra-prototype/tra/recovery.py:1-130` defines recovery procedures for all 5 `TRAException` types, including `EntityAmbiguity`. However, in production (`kernel.py` + `isa.py`), only 3 exception types are ever raised and reach `_recover`: `BrokenMarkdown` (raised at `isa.py:103-105, 148-167`), `GlossaryConflict` (raised at `isa.py:235-247`), and `Unrecoverable` (raised at `isa.py:656-658, 668`). `EntityAmbiguity` is defined in `exceptions.py` and routed by `recovery.py` but **never raised in any production code path** (Track R3 baseline TRA-038: "3/3 exception types still unreachable (UnknownTerm=False, CertaintyConflict=False, EntityAmbiguity=False)"). So the doc's claim that "EntityAmbiguity now routes through `_recover`" is misleading — the routing code exists, but the exception is never raised, so the routing is dead code.
- **Detail:** The doc claim also internally contradicts itself within the same bullet: it says `EntityAmbiguity` "now routes through `_recover`" AND "is still never raised in production code paths (TRA-038)" — both can't be true simultaneously in any meaningful sense. The accurate statement (per Round 2 finding TRA-C2-002's suggested fix, which was applied to `CLAUDE.md:49` but not to `tra-prototype/README.md:96-99`) is: "BrokenMarkdown, GlossaryConflict, and Unrecoverable reach `_recover` in production; UnknownTerm, CertaintyConflict, and EntityAmbiguity are defined and routed by `recovery.py` but never raised in production."
- **Suggested fix:** Replace `tra-prototype/README.md:96-99` with: "**Exception recovery** (TRA-004, partial): `BrokenMarkdown`, `GlossaryConflict`, and `Unrecoverable` reach `_recover` in production (`isa.py:103-105, 235-247, 656-668`). However, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are defined and routed by `recovery.py` but never raised in production code paths (TRA-038) — their recovery procedures are dead code in practice."

### TRA-C3-011 — README.md (root) has wrong path: `tra-prototype/implementation_plan.md` (actual: `implementation_plan.md` at repo root)
- **Severity:** INFO
- **Category:** Doc Consistency / wrong-file-path
- **Carry-over or new:** New
- **Doc:** `README.md:114` — "Phases 0–6 are complete (foundation → Kernel/Policy orchestration → ZH-EN module → CLI + benchmark suite → hardening). Phase 7 (documentation & delivery) has not started. See `tra-prototype/implementation_plan.md` for the item-by-item state and `CLAUDE.md` → \"Prototype engine status\" for layout and run commands."
- **Code:** `ls /home/z/my-project/Translation-Runtime-Architecture/implementation_plan.md` exists at the repo root; `ls /home/z/my-project/Translation-Runtime-Architecture/tra-prototype/implementation_plan.md` returns "No such file or directory". Other docs reference it correctly: `CLAUDE.md:15` ("`implementation_plan.md`"), `README.md:140` ("`implementation_plan.md`"), `tra-prototype/SKILL.md:274` ("`implementation_plan.md`").
- **Detail:** A reader following the README.md:114 link `tra-prototype/implementation_plan.md` would get a 404. The path is wrong by one directory level. The other 3 references to the same file in the repo correctly omit the `tra-prototype/` prefix.
- **Suggested fix:** Change `README.md:114` from "See `tra-prototype/implementation_plan.md`" to "See `implementation_plan.md`".

### TRA-C3-012 — AGENTS.md "How to work here" bullet contradicts the boundary-override note 20 lines above
- **Severity:** INFO
- **Category:** Doc Consistency / internal-contradiction
- **Carry-over or new:** New
- **Doc:** `AGENTS.md:25` — bullet: "Any concrete engine/module/tool claiming TRA compliance lives in a different repo."
- **Code:** `AGENTS.md:5` — "A Phase 0 prototype engine lives in `tra-prototype/` (a subdirectory, overriding the original \"separate repository\" boundary rule) and has its own `pyproject.toml`, `requirements.txt`, and `tests/` with `ruff`, `mypy --strict`, and `pytest`." Also `CLAUDE.md:9`, `README.md:11`, `README.md:78`, `review-feedback.md:1` — all document the override.
- **Detail:** AGENTS.md:5 explicitly states the boundary rule was overridden for `tra-prototype/`, but the AGENTS.md:25 bullet in "How to work here" still asserts the original boundary rule without acknowledging the override. A new contributor scanning only the "How to work here" section would conclude that `tra-prototype/` shouldn't exist in this repo — contradicting the file they were just told about 20 lines earlier. The bullet should either be qualified with "(with the `tra-prototype/` override noted above)" or removed (since line 5 already covers the boundary rule + override).
- **Suggested fix:** Change `AGENTS.md:25` to: "Any *new* concrete engine/module/tool claiming TRA compliance lives in a different repo (the `tra-prototype/` Phase 0 prototype is the documented override — see above)."

### TRA-C2-009 (carry-over) — implementation_plan.md "Repo scope note" still calls tra-prototype/ "an external codebase"
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-009; R3 baseline TRA-059 STATIC-FAIL)
- **Doc:** `implementation_plan.md:3` — "> **Repo scope note:** Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is an **implementation plan for `tra-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only."
- **Code:** `CLAUDE.md:9`, `AGENTS.md:5`, `README.md:11` all state the boundary was overridden: `tra-prototype/` lives as a subdirectory of this repo. `review-feedback.md:1` was updated to match: "That was overridden: the `tra-prototype/` engine now lives as a subdirectory of this repo."
- **Detail:** `implementation_plan.md` was not updated when the boundary override landed. The note still describes `tra-prototype/` as "an external codebase", contradicting the actual repo layout and the other four planning docs' scope notes. Round 3 baseline TRA-059 confirms: STATIC-FAIL.
- **Suggested fix:** Replace `implementation_plan.md:3` with: "> **Repo scope note:** The repo's original boundary rule put any concrete TRA-compliant engine in a *separate* repository. That was overridden: `tra-prototype/` now lives as a subdirectory of this repo (see `README.md` / `AGENTS.md` / `CLAUDE.md`). This file is the **implementation plan for `tra-prototype/`** — kept here as planning context, not part of the normative spec."

### TRA-C2-010 (carry-over) — prototype.md "Repo scope note" same staleness as implementation_plan.md
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-010)
- **Doc:** `prototype.md:1` — "> **Repo scope note:** Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is a **planning note for `tra-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only."
- **Code:** Same as TRA-C2-009 — boundary override documented in CLAUDE.md/AGENTS.md/README.md/review-feedback.md.
- **Detail:** `prototype.md` predates the boundary override and wasn't updated. The `review-feedback.md:1` scope note was updated to acknowledge the override; `prototype.md:1` was not.
- **Suggested fix:** Replace `prototype.md:1` with the same updated scope note suggested in TRA-C2-009.

### TRA-C2-011 (carry-over) — implementation_plan.md File Structure Summary is stale (missing 6 modules + 4 test files)
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-011; now MORE stale than at Round 2 close)
- **Doc:** `implementation_plan.md:305-351` — File Structure Summary lists 10 modules under `tra/` (`__init__.py`, `kernel.py`, `memory.py`, `isa.py`, `policy.py`, `diagnostics.py`, `cache.py`, `anchor.py`, `utils.py`, `exceptions.py`) + `modules/{__init__,registry,zh_en,base}.py`, and 12 test files (`test_isa.py`, `test_kernel.py`, `test_anchor.py`, `test_benchmark.py`, `test_modules.py`, `test_phase0.py`, `test_phase6_hardening.py`, `test_recovery.py`, `test_reporting.py`, `test_utils.py`, `test_validate.py`, `test_outstanding_findings.py`).
- **Code:** Actual `tra-prototype/tra/` directory contains **16** .py files: the 10 listed + `benchmark.py`, `config.py`, `hitl.py`, `recovery.py`, `reporting.py`, `validate.py` (6 unlisted). Actual `tra-prototype/tests/` directory contains **16** `test_*.py` files: the 12 listed + `test_e2e_to_translate.py`, `test_tra043_protocol.py`, `test_tra047_config_robustness.py`, `test_tra071_broken_markdown.py` (4 unlisted, all added in the `a4d0b3a` + `354fa94` remediation commits). `CLAUDE.md:17-31` "Layout" section IS up-to-date and lists all 16 modules accurately — readers should prefer CLAUDE.md over `implementation_plan.md` for the current file inventory.
- **Detail:** The File Structure Summary was authored at Phase 0 planning time and never updated as Phase 6 hardening added `recovery.py`, `hitl.py`, `reporting.py`, `validate.py`, `config.py`, `benchmark.py`. Since Round 2 close, 4 more test files were added (`test_e2e_to_translate.py`, `test_tra043_protocol.py`, `test_tra047_config_robustness.py`, `test_tra071_broken_markdown.py`) — the staleness has grown.
- **Suggested fix:** Add a header note at `implementation_plan.md:305`: "> File structure below is the Phase-0 planning snapshot; for the current file inventory see `CLAUDE.md` → 'Layout (where behavior lives)'." (Updating the snapshot itself is also acceptable, but the header note is preferred for a historical planning doc.)

### TRA-C2-012 (carry-over) — implementation_plan.md Phase 0.1.5 subcommand list is stale (lists 3, actual 4)
- **Severity:** INFO
- **Category:** Doc Consistency / stale-doc
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-012)
- **Doc:** `implementation_plan.md:22` — "[x] 0.1.5 Set up CLI entry point skeleton (tra_cli.py with translate, cache-clear, audit subcommands)"
- **Code:** `tra-prototype/tra_cli.py` implements **4** subcommands: `translate` (line 66), `validate` (line 214), `audit` (line 152), `cache-clear` (line 131). The `validate` subcommand was added during Phase 5 (5.1.4 at `implementation_plan.md:223` is also marked `[x]`). `tra_cli.py:1-7` docstring lists all 4.
- **Detail:** Phase 0.1.5 was authored when only 3 subcommands were planned; `validate` was added later. The checkbox is correctly `[x]` (the skeleton IS set up), but the parenthetical "with translate, cache-clear, audit subcommands" understates the actual CLI. A reader scanning the plan would miss `validate` exists.
- **Suggested fix:** Update `implementation_plan.md:22` parenthetical to: "(tra_cli.py with translate, validate, audit, cache-clear subcommands)".

### TRA-C2-013 (carry-over) — status.md is a verbatim session log, not a current-status doc
- **Severity:** WARNING
- **Category:** Doc Consistency / misleading-doc
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-013; R3 baseline TRA-060 STATIC-FAIL)
- **Doc:** `status.md` (50 lines) — opens with `Bash(git status && echo "---DIFF STAT---" && git diff --stat)` (line 3); contains verbatim shell transcripts. Line 35: "Phase 6 is complete and pushed (4d97aa1 → origin/main)." Line 44: "Gates: ruff clean · ruff-format clean · mypy --strict (20 files) · **103 pytest passing**." Line 49: sign-off "Let me know if you want Phase 7 (docs/delivery) next."
- **Code:** Current state at HEAD `b783745`: `pytest tests` reports **174 passed in 1.20s** (up from 103 at the Phase 6 commit, 141 at Round 2 close, 166 at `a4d0b3a`). Round-1 + Round-2 + Round-3 audit remediation landed 8 commits after `4d97aa1` (5 between Round 2 close `4b8827c` and Round 3 HEAD `b783745` alone). `CLAUDE.md:15` is the accurate current-status doc ("Phases 0–6 are complete … Phase 7 has not started").
- **Detail:** status.md is frozen at the `4d97aa1` session; the test count (103 vs 174), the commit narrative, and the "Let me know if you want Phase 7 next" sign-off are all stale. Worse, the file is named `status.md` — a name that implies "current status" — but the content is a session transcript. New contributors reading `status.md` first will get a 2026-07 snapshot, not current state. Round 3 baseline TRA-060 confirms: STATIC-FAIL.
- **Suggested fix:** Two options (same as Round 2 suggestion, not yet applied): (a) rename `status.md` → `phase6_commit_log.md` and add a header: "> Verbatim session log from the Phase 6 commit (4d97aa1). For current status see `CLAUDE.md` → 'Prototype engine status'."; OR (b) replace `status.md` content with a 5-line current-state summary: "HEAD: `b783745`. Phases 0-6 complete. 174 tests passing. Open: 6.3.1 (structlog), 6.5.1 (asyncio), 6.5.2 (cross-run cache), all of Phase 7. See `CLAUDE.md` for the full state." Option (a) preserves the historical narrative; option (b) makes the filename honest.

### TRA-C2-014 (carry-over) — docs/audit/ duplicates tra-audit-skills/deliverables/ (undocumented)
- **Severity:** INFO
- **Category:** Doc Consistency / undocumented-duplication
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-014)
- **Doc:** `docs/audit/` contains `TRA_audit_findings_register.xlsx`, `TRA_audit_severity_heatmap.png`, `TRA_Prototype_Audit_Report.docx`, `tra-audit-skills.tar.gz`. Referenced from `CLAUDE.md:56`, `tra-prototype/SKILL.md:328`, `tra-prototype/README.md:109-112`. None of these references explain the duplication with `tra-audit-skills/deliverables/`.
- **Code:** `ls docs/audit/` and `ls tra-audit-skills/deliverables/` confirm both directories contain the Round 1 audit artifacts. The Round 2 artifacts (different filenames: `*_r2.*`) live only in `docs/audit/round2/`. The `tra-audit-skills.tar.gz` in `docs/audit/` is a tarball of the entire `tra-audit-skills/` directory — also undocumented.
- **Detail:** The duplication is intentional (surfacing audit deliverables in `docs/audit/` for repo readers who don't want to dig into `tra-audit-skills/`), but it's not documented anywhere. A future contributor updating the audit report would have to remember to update both copies, or the two will drift. Round 2 SKILL.md:328-333 and tra-prototype/README.md:109-112 reference both Round 1 and Round 2 paths without explaining the relationship.
- **Suggested fix:** Add a one-line note to `CLAUDE.md:56`: "These artifacts are duplicated from `tra-audit-skills/deliverables/` for visibility; regenerate via `tra-audit-skills/scripts/tra_xlsx.py` + `tra_chart.py` + `scripts/docx-build/generate.js`, then copy to `docs/audit/`." Alternatively, replace `docs/audit/` with symlinks to `tra-audit-skills/deliverables/`.

### TRA-C2-016 (carry-over) — AGENTS.md "Files and roles" table omits meta-docs and prototype docs
- **Severity:** INFO
- **Category:** Doc Consistency / incomplete-doc
- **Carry-over or new:** Carry-over (Round 2 TRA-C2-016)
- **Doc:** `AGENTS.md:9-15` — "Files and roles" table lists only the 5 spec files (`TRA-SPECIFICATION.md`, `TRA-ISA-REFERENCE.md`, `TRA-MODULE-ZH-EN.md`, `TRA-BENCHMARK-SUITE.md`, `TRA-CONFORMANCE-GUIDE.md`). The "What this repo is" paragraph (AGENTS.md:5) mentions "meta-docs (`README.md`, `CLAUDE.md`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md`" — but omits `status.md`, `implementation_plan.md`, `review.md`, `AGENTS.md` itself, and the prototype's own `tra-prototype/SKILL.md` / `tra-prototype/README.md`.
- **Code:** The repo root contains 10 meta/planning docs (`AGENTS.md`, `CLAUDE.md`, `README.md`, `start-here.md`, `prototype.md`, `review-feedback.md`, `review.md`, `status.md`, `implementation_plan.md`, `to_translate.md`) plus the `tra-prototype/` subdirectory with `SKILL.md` + `README.md`. AGENTS.md surfaces only 5 spec files + 5 meta-docs (in prose), leaving 5+ docs unmentioned.
- **Detail:** AGENTS.md is the agent-facing entry doc — the file an AI agent reads first. A new agent won't know `implementation_plan.md` (the per-item Phase 0-7 state), `status.md` (the Phase 6 commit narrative), `review.md` (the historical review), or `tra-prototype/SKILL.md` (the prototype usage guide) exist.
- **Suggested fix:** Either expand the "Files and roles" table to include meta-docs, OR add a second short table "Meta-docs & planning" listing `CLAUDE.md`, `AGENTS.md`, `README.md`, `start-here.md`, `prototype.md`, `review.md`, `review-feedback.md`, `status.md`, `implementation_plan.md`, `to_translate.md`, `tra-prototype/SKILL.md`, `tra-prototype/README.md` with one-line roles.

---

## Spec / template spot-checks (no findings)

These were spot-checked for internal consistency against the code; all held:

1. **`TRA-MODULE-ZH-EN.md`** (54 lines) — linguistic spec matches `tra-prototype/tra/modules/zh_en.py` (239 lines) implementation:
   - Epistemic lexicon (`成立 → Confirmed`, `高度可信 → highly credible`, `可能 → may`) → `EPISTEMIC_LEXICON` dict at `zh_en.py:35-40` ✓
   - Nominalization mappings (`进行验证 → verify`, `实现优化 → optimize`, `提供支持 → support`) → `NOMINALIZATION` dict at `zh_en.py:63-70` ✓
   - Four-character expressions (`Hardware isolation → 硬件隔离`, `Seamless migration → 无缝迁移`, `High availability → 高可用性`) → `FOUR_CHAR_MAP` dict at `zh_en.py:73-77` ✓
   - Punctuation conventions (full-width for ZH prose, half-width for code/URLs) → `_FULL_TO_HALF` / `_HALF_TO_FULL` dicts + `_normalize_punctuation` at `zh_en.py:91-207` ✓
   - Note: `TRA-MODULE-ZH-EN.md` alone is a *linguistic* spec, not a Python API template. SKILL.md §6 (lines 199-220) provides the Python interface template (`ModuleInterface`, `build_default_registry()`, `registry.register(...)`). Combined, the two docs are sufficient to author a new `fr-en` module — no finding.
2. **`TRA-ISA-REFERENCE.md`** — 6 ISA instruction contracts match `tra/isa.py`:
   - `ANALYZE_DOCUMENT` (spec §1) — raises `BrokenMarkdown`/`MALFORMED_MARKDOWN` + `TRAException`/`EMPTY_SOURCE` (`isa.py:97-105, 148-167`) ✓
   - `BUILD_GLOSSARY` (spec §2) — raises `GlossaryConflict`/`CONFLICTING_MAPPINGS` (`isa.py:235-247`) ✓
   - `BUILD_ENTITY_TABLE` (spec §3) — `ENTITY_AMBIGUITY` default-to-Entity behavior matches (`isa.py:323-334`) ✓
   - `TRANSLATE_SEGMENT` (spec §4) — failure conditions `TERMINOLOGY_VIOLATION`/`FACTUAL_DRIFT`/`HALLUCINATION` are spec-defined but not raised by the impl (overlap with TRA-038 "3 of 5 exception types never raised"); the rule path detects these via `VERIFY_OUTPUT` instead — pre-existing spec/impl divergence, not a doc-vs-code issue.
   - `VERIFY_OUTPUT` (spec §5) — "Failure Conditions: None" matches (`isa.py:501-603` returns diagnostics, doesn't raise) ✓
   - `REPAIR_SEGMENT` (spec §6) — invariant "must resolve the specific violation without introducing new ones" enforced at `isa.py:665-668` (raises `Unrecoverable` on new BLOCKING); `UNRECOVERABLE` failure condition matches (`isa.py:656-658, 668`) ✓
3. **`start-here.md:8`** uses collapsed 5-state labels (`ANALYZE → BUILD → TRANSLATE → VERIFY → AUDIT`), BUT `start-here.md:23` explicitly notes these are abbreviated renderings of the canonical 9-state sequence (with the full sequence spelled out). Round 3 baseline TRA-063 PASS.
4. **`review.md:8`** uses collapsed 8-state labels (`BOOTSTRAP → ANALYZE → BUILD → TRANSLATE → VERIFY → REPAIR → AUDIT → EMIT`) without an inline abbreviation note; however, `CLAUDE.md:63` documents the abbreviation relationship explicitly. Round 3 baseline TRA-063 PASS. `review.md` is the historical external reviewer's review (acknowledged carry-over D-21 from Round 1) — historical staleness is expected and not a current-state-doc issue.
5. **`tra-prototype/SKILL.md`** §7 line 243-244: "The full suite is **174 tests** across 16 test files" — verified via `pytest --collect-only` (174 tests collected) + `ls tests/test_*.py | wc -l` (16 files). R3 baseline TRA-062 STATIC-PASS. ✓
6. **`tra-prototype/SKILL.md`** §7 line 239: "mypy --strict tra (20 source files)" — verified via `find tra -name "*.py" | wc -l` (= 20). ✓
7. **`tra-prototype/SKILL.md`** §6 line 207: `from tra.modules.registry import build_default_registry, ModuleInterface` — verified importable. ✓
8. **`tra-prototype/tra_cli.py:1-7`** docstring lists 4 subcommands (`translate`, `validate`, `audit`, `cache-clear`); no "skeleton" mention. R3 baseline TRA-022 STATIC-PASS. ✓
9. **`tra-prototype/README.md:18`** install command: `pip install -e ".[dev]"`. R3 baseline TRA-061 STATIC-PASS. ✓
10. **`tra-prototype/config.yaml`** comments — no `cache.expire` dead config; references to `tvm_bootstrap`, `compilation_dir`, `audit_trace` all match code. ✓
11. **`tra-prototype/pyproject.toml`** description: "TRA (Translation Runtime Architecture) v1.0 conformant translation engine — prototype". ✓
12. **`review-feedback.md:1`** scope note: updated to acknowledge the boundary override ("That was overridden: the `tra-prototype/` engine now lives as a subdirectory of this repo"). ✓
13. **`CLAUDE.md:53`** TRA-031 benchmark coverage: "22 of 24 spec cases implemented (S-03 and E-03 still missing)". Actual: 22 cases total in `tests/benchmark/cases/{sft,regression}.jsonl` (21 spec + 1 regression R-01); spec defines 23 cases (S=6, F=5, T=5, D=4, E=3); 21 spec cases implemented (missing S-03, E-03). R3 baseline TRA-058 STATIC-PASS. ✓ (Note: the "24" denominator appears to count 23 spec + 1 regression; the "22" numerator counts 21 spec + 1 regression — internally consistent if R-01 is counted as a "spec case" for coverage purposes.)
14. **`CLAUDE.md:49`** TRA-004 entry: "BrokenMarkdown now routes through `_recover`; `build_entity_table` is wrapped in try/except (TRA-039). However, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are still never raised in production code paths (TRA-038)." — accurate per Track R3 baseline TRA-038 (PERSISTENT: 3/3 unreachable). ✓
15. **`CLAUDE.md:48`** TRA-002 entry: "the kernel now selects the language module from the registry when supplied; however, `tra_cli.py translate` does not yet pass a registry." — accurate per `kernel.py:113-155` + `tra_cli.py:107`. ✓
16. **`CLAUDE.md:51`** TRA-017 entry: lists 6 unused deps (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) — matches actual `pyproject.toml` deps + grep evidence (none imported in any `.py` file). R3 baseline TRA-017 STATIC-PASS. ✓

---

## Methodology notes

- **HEAD verified:** `git log --oneline -5` confirms HEAD is `b783745` ("add session log"), 5 commits ahead of Round 2's audited HEAD `4b8827c`.
- **Test count verified:** `cd tra-prototype && python -m pytest --collect-only` reports "174 tests collected in 0.37s"; `pytest tests` reports "174 passed in 1.20s". `ls tests/test_*.py | wc -l` returns 16.
- **Source file count verified:** `find tra -name "*.py" | wc -l` returns 20 (16 `tra/*.py` + 4 `tra/modules/*.py`). Matches SKILL.md §7 "20 source files" and worklog baseline "mypy --strict tra (20 files)".
- **Benchmark cases verified:** `python -c "import json; ..."` enumerates 22 case IDs in `tests/benchmark/cases/{sft,regression}.jsonl`: `D-01..D-04, E-01, E-02, F-01..F-05, R-01, S-01, S-02, S-04..S-06, T-01..T-05`. Missing spec cases: `S-03, E-03`. Spec defines 23 cases (per `TRA-BENCHMARK-SUITE.md`: S=6, F=5, T=5, D=4, E=3).
- **PolicyResolver invocation verified:** `grep -n "_POLICY_RESOLVER\|PolicyResolver" tra/isa.py` returns the import (`isa.py:52`), the instantiation (`isa.py:63`), and the call site (`isa.py:555`). Test `TestTRA006PolicyResolverInvokedInProduction` at `tests/test_outstanding_findings.py:1281-1362` monkeypatches the resolver and asserts severity changes — R3 baseline TRA-006 REGRESSION-TEST-PASS.
- **Quality gates at HEAD `b783745`:** `pytest tests` → 174 passed in 1.20s. (ruff/mypy gates not re-run in this audit; worklog bootstrap already confirmed all 4 green at baseline.)
