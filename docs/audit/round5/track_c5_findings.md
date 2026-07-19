# Track C5 — Doc-vs-Code Consistency Re-Audit (Round 5)

**HEAD audited:** `5476faf1d668b42d2a7b8c9b159ae9ee54c6e4f7`
**Methodology:** Doc-vs-code diff for all 12 documentation files. Each concrete claim (number, file path, command, commit hash, status word) verified against code reality at HEAD.
**Baseline:** Round 4 Track C4 (17 findings: 1 BLOCKING / 9 WARNING / 7 INFO) + 66-finding R4 master register + Track R5 baseline (21 fixed / 19 persistent / 4 partial / 0 regressions / 22 verified-holding).

## Summary

- Findings: **22 total (0 BLOCKING / 9 WARNING / 13 INFO)**
- Carry-over from Round 4: **11** (3 persistent / 4 partial / 4 fixed-and-verified)
- New findings: **6** (TRA-C5-003 stale "34 classes, 139 tests" annotation, TRA-C5-008 stale "22 of 24 spec cases", TRA-C5-010 stale "100+ test cases" in to_translate.md, TRA-C5-011 stale sha256 hash in SKILL.md, TRA-C5-012 missing Round 5 audit references in AGENTS.md/SKILL.md, TRA-C5-013 status.md HEAD ref drift)
- Regressions: **0**
- Positive verifications: **11** (R4 Batch 1/2 fixes holding; CLI examples, deps table, file structure, TRA-017 status, etc.)

The doc-vs-code drift has materially improved since R4 close. **R4 Batch 1+2 remediation commit `929c879` fixed 13 of 17 R4 doc-consistency findings** (including the BLOCKING TRA-C4-013 bare-`tra_cli.py` issue). However, **R4 Batch 2 commit `929c879` left the "18 test files" claim unchanged in 4 docs** (the test count was correctly refreshed 174→199→228 across the remediation commits, but the file count "18" was never corrected to "16"). Additionally, **R4 Batch 2 spec-conformance code fixes (TRA-038, TRA-042, TRA-072, TRA-092, TRA-099 — commits `d95c36d`, `efbc875`, `78c9250`, `d3e5f60`, `e54b7a7`) updated `CLAUDE.md` "Known gaps" but did not back-fill the parallel section in `tra-prototype/README.md`**, leaving 4 stale "Known gaps" entries that are now the *exact opposite* of code reality. This was already flagged as "partial" by Track R5 (TRA-C4-015/016); Track C5 extends the finding to also cover the TRA-099 and TRA-092 entries.

## Findings

### TRA-C5-001: "228 tests across 18 test files" claim is wrong in 4 docs (actual: 228 tests across 16 test files)

- **Severity:** WARNING
- **Category:** Doc Consistency / stale-count
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `CLAUDE.md:55` — "The current test count is **228 across 18 test files**"
  - Doc claim: `AGENTS.md:41` — "228 tests across 18 files"
  - Doc claim: `tra-prototype/README.md:125-126` — "Current test count: **228 across 18 test files**"
  - Doc claim: `tra-prototype/SKILL.md:243-244` — "The full suite is **228 tests** across 18 test files"
  - Code reality: `python -m pytest tests --co 2>&1 | tail -1` → "228 tests collected in 0.41s" (count is accurate); `ls tests/test_*.py | wc -l` → **16** (file count is wrong). Even the most generous interpretation (counting `conftest.py` as a "test file") gives 17 `.py` files in `tests/`; counting the manual `e2e_test.py` at the prototype root (not pytest-collected) gives 18 `.py` files total — but `e2e_test.py` is in `tra-prototype/`, not in `tests/`, and is not collected by pytest.
- **Detail:** This is the highest-frequency stale claim in the doc set — it appears verbatim in 4 different docs (5 if counting `status.md:1` banner, see TRA-C5-013). The test count (228) was correctly refreshed across Batch 1 (`f226582`) and Batch 2 (`929c879` → `aae0bca` → `5476faf`), but the file count ("18") was carried forward from the original R3-era "16 test files + 2 manual scripts" interpretation without verification. R4 Batch 1 remediation plan (`remediation_plan_r4.md:54`) explicitly said to "Update §7 to say '199 tests across 18 test files'" — so the "18" was a typo in the R4 remediation plan that propagated to all 4 docs. Track R5 noted this as a "minor residual inaccuracy" (R5 worklog observation #5) but did not file a formal finding. A reader trusting any of these 4 docs to size the test suite would overestimate the file count by 2 (12.5% drift).
- **Suggested fix:** Replace "18 test files" → "16 test files" in `CLAUDE.md:55`, `AGENTS.md:41`, `tra-prototype/README.md:126`, `tra-prototype/SKILL.md:243`. (Optional: add a parenthetical "(plus `conftest.py` and `e2e_test.py` manual demo)" to SKILL.md for completeness.)
- **Round 4 status:** persistent (TRA-C4-003 carry-over; the test count was fixed but the file count was not — see R5 baseline observation #5)

### TRA-C5-002: tra-prototype/SKILL.md:246 says "(40 test classes: …)" — actual is 46 classes (44 unique TRA IDs); list omits TRA-016, TRA-017, TRA-026, TRA-042

- **Severity:** WARNING
- **Category:** Doc Consistency / stale-file-list
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:246-249` — "(40 test classes: TRA-001, 002, 004, 006, 007, 008, 009, 012, 013, 014, 032, 033, 036, 037, 038, 039, 041, 049, 050, 051, 053, 054, 072, 073, 074, 075, 076, 077, 078, 088, 089, 093, 096, 097, 098, 099, A4-011, B4-009, F4-006, F4-007)"
  - Code reality: `rg "^class Test" tests/test_outstanding_findings.py | wc -l` → **46** classes. The doc's list of 40 unique IDs omits 4 IDs that have actual classes: `TRA-016` (`TestTRA016CountBlockingGone`), `TRA-017` (`TestTRA017UnusedDepsGone`), `TRA-026` (`TestTRA026CacheExpireGone`) — these are the TRA-B4-009 regression tests added in Batch 3 commit `524c598` — and `TRA-042` (`TestTRA042ExtendedStructuralVerification`) added in Batch 2 commit `efbc875`. Additionally, the doc lists TRA-038 as one entry, but the file has 4 TRA-038 classes (`TestTRA038UnknownTermRaised`, `TestTRA038UnknownTermRaisedInProduction`, `TestTRA038CertaintyConflictRaisedInLLMPath`, `TestTRA038EntityAmbiguityRaisedInBuildEntityTable`), 3 of which were added in Batch 2 commit `d95c36d`. Same pattern for TRA-072 (2 classes: `TestTRA006PolicyResolverInvokedInProduction` + `TestTRA072UniversalPolicyArbitration`) and TRA-099 (`TestTRA099CLIPassesRegistry`).
- **Detail:** A reader scanning SKILL.md §7 to find the regression test for TRA-042 (extended structural verification, Batch 2 fix) would conclude no test exists and might re-file the finding. The omission of TRA-016/017/026 is more puzzling — the doc's parenthetical explicitly cites "B4-009" (the umbrella finding that added these 3 regression tests), but then lists zero of the actual classes for it. R4 Batch 2 commit `929c879` regenerated the list per `rg "^class Test" tests/test_outstanding_findings.py` (per R4 remediation plan §B1), but at that moment the file had 40 classes — the subsequent Batch 2 commits (`d95c36d`, `efbc875`, `78c9250`, `d3e5f60`) and Batch 3 commit `524c598` added the 6 missing classes without re-running the regeneration step.
- **Suggested fix:** Replace `tra-prototype/SKILL.md:246-249` with: "(46 test classes covering 44 unique TRA IDs: TRA-001, 002, 004, 006, 007, 008, 009, 012, 013, 014, **016, 017, 026**, 032, 033, 036, 037, 038 (×4 classes), 039, 041, **042**, 049, 050, 051, 053, 054, **072** (×2 classes), 073, 074, 075, 076, 077, 078, 088, 089, 093, 096, 097, 098, 099, A4-011, B4-009, F4-006, F4-007)"
- **Round 4 status:** partial (TRA-C4-004 carry-over; the original 22→40 ID drift was fixed in Batch 2 commit `929c879`, but subsequent Batch 2/3 commits added 6 more classes that weren't back-filled)

### TRA-C5-003: implementation_plan.md:346 "test_outstanding_findings.py # TDD regression tests (34 classes, 139 tests)" — actual is 46 classes, 91 tests

- **Severity:** WARNING
- **Category:** Doc Consistency / stale-count
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `implementation_plan.md:346` — "test_outstanding_findings.py   # TDD regression tests (34 classes, 139 tests)"
  - Code reality: `rg "^class Test" tests/test_outstanding_findings.py | wc -l` → **46 classes**; `python -m pytest tests/test_outstanding_findings.py --co 2>&1 | tail -1` → "91 tests collected in 0.09s". Both numbers in the doc are wrong: classes off by 12 (34→46), tests off by 48 (139→91). The "139 tests" figure was likely accurate at the R3 close (`b783745`) when the file had ~34 classes with ~4 tests per class on average; R3→R4 remediation collapsed some parametrized tests while R4 Batch 2 added 6 new single-purpose classes.
- **Detail:** The implementation_plan.md "File Structure Summary" was largely fixed by Batch 2 commit `929c879` (all 16 modules + 16 test files now listed, see TRA-C5-P-004 below), but the inline annotation for `test_outstanding_findings.py` was not refreshed. A reader counting classes/tests against the doc would be off by 35% and 53% respectively.
- **Suggested fix:** Replace `implementation_plan.md:346` annotation with: "test_outstanding_findings.py   # TDD regression tests (46 classes, 91 tests covering 44 unique TRA IDs)"
- **Round 4 status:** new (the "34 classes, 139 tests" annotation pre-dates R4; R4's TRA-C4-009 fix updated the file structure but missed this inline annotation; subsequent Batch 2 added 6 more classes, widening the drift)

### TRA-C5-004: tra-prototype/README.md:90-95 still says "Module registry (TRA-002, fixed in kernel; CLI gap persists)" — TRA-099 was fixed in Batch 1 commit `e54b7a7`

- **Severity:** WARNING
- **Category:** Doc Consistency / stale-status
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:90-95` — "**Module registry** (TRA-002, fixed in kernel; CLI gap persists): the kernel now selects the language module from the registry when supplied (`TRAKernel(cfg, registry=)`); `as_interface()` satisfies `LanguageModuleProtocol` (TRA-096 fixed in Round 3). However, `python -m tra_cli translate` does not yet pass a registry (TRA-099), so the CLI still falls back to `ZHENModule`."
  - Code reality: `tra_cli.py:138-139` — `registry = build_default_registry()` followed by `kernel = TRAKernel(cfg, registry=registry, interactive=interactive)`. The CLI **does** pass `registry=registry` to `TRAKernel`. TRA-099 was fixed in Batch 1 commit `e54b7a7`. The `TestTRA099CLIPassesRegistry` test class at `tests/test_outstanding_findings.py` enforces this regression.
- **Detail:** Track R5 noted this exact drift in worklog observation #2 (TRA-C4-015 partial — README "Known gaps" went stale again due to Batch 4 fixes). However, R5's note focused on the TRA-006/TRA-072 entry (TRA-C5-005 below); the TRA-099 entry at `README.md:90-95` is a separate stale claim that R5 did not explicitly enumerate. A reader trusting the README would believe the CLI is non-functional for module selection and would not know that `python -m tra_cli translate` works correctly with the default registry.
- **Suggested fix:** Replace `tra-prototype/README.md:90-95` with: "**Module registry** (TRA-002, fixed in kernel; TRA-099 fixed in Round 4 Batch 1 commit `e54b7a7`): the kernel selects the language module from the registry when supplied (`TRAKernel(cfg, registry=registry)`), and `as_interface()` satisfies `LanguageModuleProtocol` (TRA-096 fixed in Round 3). The CLI's `translate` command auto-builds the default registry via `build_default_registry()` and passes it to `TRAKernel` (`tra_cli.py:138-139`)."
- **Round 4 status:** partial (TRA-C4-015 carry-over; R5 baseline noted this as "partial" — the R4 misleading phrasing about TRA-006 was replaced, but Batch 1's TRA-099 fix was not back-filled into the README)

### TRA-C5-005: tra-prototype/README.md:104-109 still says "this is the ONLY conflict pair arbitrated (TRA-072)" — TRA-072 was fixed in Batch 2 commit `78c9250`

- **Severity:** WARNING
- **Category:** Doc Consistency / misleading-doc
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:104-109` — "**Policy Engine** (TRA-006 fixed in Round 3; TRA-072 partial): `verify_output` consults `_POLICY_RESOLVER.wins(TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY)` to arbitrate canonical-term-leakage severity (`isa.py:565`). However, this is the ONLY conflict pair arbitrated by the resolver (TRA-072); all other severity decisions still use hard-coded conditionals."
  - Code reality: `rg "_POLICY_RESOLVER\.wins" tra/isa.py -n` returns **4 call sites**: `isa.py:794` (Structural P2 vs Fluency P6), `isa.py:898` (Entity P3 vs Fluency P6), `isa.py:926` (Terminological P4 vs Fluency P6), `isa.py:959` (Epistemic P5 vs Fluency P6). All 4 severity decision pairs go through `_POLICY_RESOLVER.wins()`. The `TestTRA072UniversalPolicyArbitration` test class at `tests/test_outstanding_findings.py` (added in Batch 2 commit `78c9250`) monkeypatches `_POLICY_RESOLVER.wins` to return `False` and asserts ALL severities drop from BLOCKING to WARNING, empirically proving universal arbitration.
- **Detail:** Track R5 already flagged this exact drift (R5 worklog observation #2 — "README.md 'Known gaps' now claims 'ONLY conflict pair arbitrated' (false — 4 pairs)"). The phrase "this is the ONLY conflict pair arbitrated" is the *exact opposite* of code reality — the resolver is invoked at 4 sites, not 1. CLAUDE.md:50 was correctly updated in Batch 2 to read "TRA-072 fixed in round 4 commit `78c9250`" with the 4-pair enumeration, but the parallel entry in `tra-prototype/README.md` was not back-filled. Internal cross-doc contradiction: CLAUDE.md:50 says "4 severity decision pairs"; tra-prototype/README.md:107 says "ONLY conflict pair arbitrated" — same repo, same engine, opposite claims.
- **Suggested fix:** Replace `tra-prototype/README.md:104-109` with: "**Policy Engine** (TRA-006 fixed in Round 3; TRA-072 fixed in Round 4 Batch 2 commit `78c9250`): `verify_output` now routes ALL 4 severity decisions through `_POLICY_RESOLVER.wins()` — Structural (P2), Entity (P3), Terminological (P4), Epistemic (P5), each vs Fluency (P6) — at `isa.py:794, 898, 926, 959`. Spec §5.2 universal arbitration contract is now met. Monkeypatching `_POLICY_RESOLVER.wins` to return `False` drops ALL severities from BLOCKING to WARNING (proven by `TestTRA072UniversalPolicyArbitration`)."
- **Round 4 status:** partial (TRA-C4-015 carry-over; R5 baseline noted this as "partial" — R4 misleading phrasing replaced but Batch 2's TRA-072 fix made the new phrasing stale)

### TRA-C5-006: tra-prototype/README.md:96-103 still says "UnknownTerm/CertaintyConflict/EntityAmbiguity are still never raised in production code paths (TRA-038 partial)" — TRA-038 was fixed in Batch 2 commit `d95c36d`

- **Severity:** WARNING
- **Category:** Doc Consistency / misleading-doc
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:96-103` — "**Exception recovery** (TRA-004, partial): `BrokenMarkdown` routes through `_recover`; `build_entity_table` is wrapped in try/except (TRA-039); `route_exception` has an explicit `Unrecoverable` branch returning `BLOCKING + HALT` (TRA-044 fixed in Round 2). However, `UnknownTerm`/`CertaintyConflict`/`EntityAmbiguity` are still never raised in production code paths (TRA-038 partial) — their exception classes, recovery procedures, and routing are operational, but no production code path auto-detects the conditions that would raise them."
  - Code reality: 3 empirical contradictions:
    1. `tra/isa.py:761` — `raise CertaintyConflict(term=src_term)` — IS raised in the LLM path when a forbidden drift target is detected (TRA-038 Batch 2 commit `d95c36d`).
    2. `tra/isa.py:723` — `recover_unknown_term(token, unresolved_ambiguities)` — IS auto-invoked in production when a CJK token has no glossary/entity/epistemic match (TRA-038 Batch 2).
    3. `tra/isa.py:360` — `recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)` — IS auto-invoked in `build_entity_table` when a token matches multiple entity patterns and `entity_type_hint` returns None (TRA-038 Batch 2).
  - Test evidence: `TestTRA038UnknownTermRaisedInProduction`, `TestTRA038CertaintyConflictRaisedInLLMPath`, `TestTRA038EntityAmbiguityRaisedInBuildEntityTable` (3 test classes, all added in Batch 2 commit `d95c36d`) — all 3 PASS at HEAD `5476faf`.
- **Detail:** Track R5 already flagged this exact drift (R5 worklog observation #2 — "README.md 'Known gaps' now claims 'still never raised in production' (false — `CertaintyConflict` is raised; `UnknownTerm`/`EntityAmbiguity` recovery procedures are auto-invoked)"). The phrase "still never raised in production code paths" is now false for all 3 exception types. CLAUDE.md:49 was correctly updated in Batch 2 to read "TRA-038 fixed in round 4 commit `d95c36d`" with the 3-raise-site enumeration; the parallel entry in `tra-prototype/README.md` was not back-filled. Internal cross-doc contradiction: CLAUDE.md:49 says "all 3 previously-unreachable exception types are now wired in production"; tra-prototype/README.md:100 says "are still never raised in production code paths" — same repo, same engine, opposite claims.
- **Suggested fix:** Replace `tra-prototype/README.md:96-103` with: "**Exception recovery** (TRA-004, partial; TRA-038 fixed in Round 4 Batch 2 commit `d95c36d`): `BrokenMarkdown` routes through `_recover` (EXCEPTION_HANDLER); `build_entity_table` is wrapped in try/except (TRA-039); `route_exception` has an explicit `Unrecoverable` branch returning `BLOCKING + HALT` (TRA-044 fixed in Round 2). All 3 previously-unreachable exception types are now wired in production: `UnknownTerm` is logged via `recover_unknown_term` (non-halting) when a CJK token has no glossary/entity/epistemic match (`isa.py:723`); `CertaintyConflict` is raised in the LLM path when a forbidden drift target is detected (`isa.py:761`); `EntityAmbiguity` is logged when a token matches multiple entity patterns and `entity_type_hint` returns None (`isa.py:360`)."
- **Round 4 status:** partial (TRA-C4-016 carry-over; R5 baseline noted this as "partial" — R4 qualifying clause "still never raised" was added, but Batch 2's TRA-038 fix made that clause false)

### TRA-C5-007: tra-prototype/README.md:117-118 still says "22 of 24 spec cases implemented (S-03 and E-03 still missing)" — TRA-092 added S-03 and E-03 in Batch 2 commit `d3e5f60`

- **Severity:** WARNING
- **Category:** Doc Consistency / stale-count
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `tra-prototype/README.md:117-118` — "**Benchmark coverage** (TRA-031, improved): 22 of 24 spec cases implemented (S-03 and E-03 still missing); spec target is 100+."
  - Code reality: `cat tests/benchmark/cases/*.jsonl | wc -l` → **24 cases total** (S/F/T/D/E + R-01 regression). `rg '"id": "S-03"' tests/benchmark/cases/` → match in `sft.jsonl`; `rg '"id": "E-03"' tests/benchmark/cases/` → match in `sft.jsonl`. S-03 (inline code vs prose) and E-03 (broken source markdown) were added in Batch 2 commit `d3e5f60` (TRA-092).
  - Cross-doc consistency: `CLAUDE.md:53` correctly says "24 of 24 spec cases implemented (S-03 and E-03 added in round 4 remediation, TRA-092)"; `tra-prototype/SKILL.md:359-360` correctly says "Benchmark suite now at 24/24 spec cases (was 22/24). +2 cases." Only `tra-prototype/README.md:117-118` retains the stale "22 of 24" claim.
- **Detail:** The R4 remediation plan (`remediation_plan_r4.md`) included TRA-092 in Batch 2 — S-03 and E-03 were added in commit `d3e5f60`. CLAUDE.md and SKILL.md were both updated to reflect the new 24/24 count. The parallel entry in `tra-prototype/README.md` was not back-filled. A reader trusting the README would believe 2 spec cases are unimplemented and might re-file TRA-092 as a new gap.
- **Suggested fix:** Replace `tra-prototype/README.md:117-118` with: "**Benchmark coverage** (TRA-031, fixed; TRA-092 fixed in Round 4 Batch 2 commit `d3e5f60`): 24 of 24 spec cases implemented (S-03 and E-03 added); spec target is 100+."
- **Round 4 status:** new-regression (the "22 of 24" claim was accurate at R4 baseline `805a8f8` when S-03/E-03 were missing; Batch 2 commit `d3e5f60` added the cases and updated CLAUDE.md + SKILL.md but not tra-prototype/README.md — drift introduced by incomplete Batch 2 back-fill)

### TRA-C5-008: to_translate.md:28 says "包含100多个测试用例" (more than 100 test cases) — actual is 24 cases (with 100+ being the future target)

- **Severity:** INFO
- **Category:** Doc Consistency / stale-count
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `to_translate.md:28` — "基准测试套件 (TRA-BENCHMARK-SUITE.md)：包含100多个测试用例，覆盖Markdown结构、数值精度、术语一致性等。" ("Benchmark suite: contains more than 100 test cases, covering Markdown structure, numerical precision, terminology consistency, etc.")
  - Code reality: `cat tests/benchmark/cases/*.jsonl | wc -l` → **24 cases** total (S/F/T/D/E + R-01 regression). The TRA-BENCHMARK-SUITE.md spec itself says (line 4): "It is seeded with the cases below and intended to grow toward 100+ cases" — i.e., 100+ is the *aspirational target*, not the current count.
- **Detail:** This is a Chinese-language misrepresentation of the benchmark suite's maturity. The TRA-BENCHMARK-SUITE.md spec clearly states "100+" is the future goal; the current seeded count is 24 (6 S + 5 F + 5 T + 4 D + 3 E + 1 R regression). The to_translate.md claim "包含100多个测试用例" reads as a factual statement about the current state, which is wrong. A Chinese-language reader using to_translate.md as the entry point would overestimate the benchmark coverage by 4×.
- **Suggested fix:** Replace `to_translate.md:28` phrase with: "基准测试套件 (TRA-BENCHMARK-SUITE.md)：当前已播种 24 个测试用例（覆盖 Markdown 结构、数值精度、术语一致性等），旨在增长至 100+ 用例。" ("Currently seeded with 24 test cases (...), intended to grow toward 100+ cases.")
- **Round 4 status:** persistent (the "100+" misrepresentation predates R4; R4 did not audit `to_translate.md` for this claim — it was outside the R4 Track C4 scope which focused on English-language technical docs)

### TRA-C5-009: implementation_plan.md:367 "Updated at HEAD `805a8f8`" — stale commit reference (actual HEAD is `5476faf`)

- **Severity:** INFO
- **Category:** Doc Consistency / stale-commit-ref
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `implementation_plan.md:367` — "> **Updated at HEAD `805a8f8`** (Round 4 audit). The 6 unused dependencies (...) were removed from `pyproject.toml` in Round 3 remediation commit `a3cd2c1` (TRA-017 fixed). ..."
  - Code reality: `git log --oneline -1` → `5476faf docs(audit): update test count 210 → 228 + Round 4 Batch 2 remediation status`. The `805a8f8` reference is the R4 baseline HEAD, which is now 9 commits behind actual HEAD `5476faf`. The table content (6 runtime + 3 dev deps) is still accurate.
- **Detail:** R4 Batch 2 commit `929c879` refreshed the Dependencies table to remove the 6 unused packages (TRA-017 fix) and stamped it with the then-current HEAD `805a8f8`. The HEAD reference was not refreshed when subsequent commits (`524c598`, `e54b7a7`, `d95c36d`, `efbc875`, `78c9250`, `d3e5f60`, `aae0bca`, `5476faf`) advanced HEAD. A reader checking the commit-hash stamp would conclude the table is 9 commits out of date, when in fact the dependency list has not changed since `929c879`. Minor — the content is correct, only the stamp is stale.
- **Suggested fix:** Either (a) update the stamp to `5476faf`, or (b) remove the stamp entirely (the table content is stable; the stamp adds maintenance burden without value).
- **Round 4 status:** new (the stamp was added in Batch 2 commit `929c879`; the stamp itself became stale the moment the next commit landed)

### TRA-C5-010: status.md:1 banner says "actual test count at HEAD `aae0bca` is 228 across 18 test files" — both the HEAD ref and file count are stale

- **Severity:** INFO
- **Category:** Doc Consistency / stale-count + stale-commit-ref
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `status.md:1` — "> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1` and references '103 pytest passing'. The actual test count at HEAD `aae0bca` is **228 across 18 test files** (see `tra-prototype/SKILL.md` §7 for current count). ..."
  - Code reality: `git log --oneline -1` → `5476faf` (1 commit ahead of `aae0bca`). The `aae0bca` reference is now 1 commit behind. `ls tests/test_*.py | wc -l` → **16** (file count is wrong, same as TRA-C5-001). The test count (228) is accurate.
- **Detail:** Track R5 already noted both of these issues (R5 worklog observation #5: "status.md:1 banner mentions commit `aae0bca` (1 commit behind HEAD) — minor staleness in the commit-hash reference"; and observation #5 also flagged the "18 test files" claim as a "minor residual inaccuracy"). The status.md banner exists specifically to warn readers that the body is stale and point them at the current count — by referencing `aae0bca` instead of `5476faf` and claiming "18 test files" instead of "16", the banner itself is now stale in 2 dimensions. The cross-reference to `tra-prototype/SKILL.md §7` is broken in a third way: SKILL.md §7 also says "18 test files" (TRA-C5-001), so the reader is sent in a circle.
- **Suggested fix:** Update `status.md:1` banner: "... The actual test count at HEAD `5476faf` is **228 tests across 16 test files** (see `CLAUDE.md` → 'Prototype engine status' for current state). ..." (Change `aae0bca` → `5476faf`; change "18 test files" → "16 test files"; redirect the cross-reference to `CLAUDE.md` since `CLAUDE.md:55` also says "18" — see TRA-C5-001 — but at least CLAUDE.md is more authoritative.)
- **Round 4 status:** persistent (TRA-C4-008 carry-over; the banner was updated in Batch 2 commit `929c879` to say "228" but the "18 test files" file-count claim was carried forward from the R4 remediation plan typo, and the commit-hash stamp was not refreshed when HEAD advanced to `5476faf`)

### TRA-C5-011: SKILL.md:328 historical claim "audit_trace.jsonl sha256 `263b901e...`, matches R3 exactly" — at HEAD `5476faf` the actual hash is `902298b3...`

- **Severity:** INFO
- **Category:** Doc Consistency / stale-hash-ref
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `tra-prototype/SKILL.md:328` — "TRA-013 byte-reproducibility holds (audit_trace.jsonl sha256 `263b901e...`, matches R3 exactly)."
  - Code reality: Track R5 + Track B5 independently verified via 2 cold-cache L4 runs of `to_translate.md` at HEAD `5476faf`: `audit_trace.jsonl` sha256 = `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` (x2, byte-identical). This differs from R4's `263b901e...` because Batch 4 fixes (TRA-038/042/072) enriched the audit-trail content with new audit records. The byte-reproducibility *invariant* holds (cold-cache runs produce identical bytes); only the specific hash value changed.
- **Detail:** The SKILL.md:328 claim is in the "Round 4" historical section header ("**Round 4** (47 issues + 19 positive verifications at HEAD `805a8f8`)"), so it is *historically accurate* for the R4 baseline state. However, the bare claim "TRA-013 byte-reproducibility holds (audit_trace.jsonl sha256 `263b901e...`)" without temporal qualification could mislead a reader who doesn't read the section header carefully — they might run the reproducibility probe at HEAD, see `902298b3...`, and conclude TRA-013 has regressed. Track R5 explained this carefully (R5 worklog observation #1 + R5 baseline notes #1), but the SKILL.md text was not updated to reflect the legitimate hash change. Minor — the section header provides context, but a one-line clarification would prevent confusion.
- **Suggested fix:** Append to `SKILL.md:328`: "... (Note: at HEAD `5476faf`, the hash is `902298b3...` — changed legitimately by Batch 4 audit-trail enrichment; the byte-reproducibility *invariant* holds, only the specific hash value changed. See `../docs/audit/round5/track_r5_baseline.md`.)"
- **Round 4 status:** new-regression (the claim was true at R4 baseline `805a8f8`; Batch 4 changed the hash without back-filling the historical reference in SKILL.md)

### TRA-C5-012: Audit deliverables references in AGENTS.md, SKILL.md, tra-prototype/README.md omit Round 5

- **Severity:** INFO
- **Category:** Doc Consistency / incomplete-doc
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `AGENTS.md:46-51` — Audit deliverables table lists Round 1, Round 2, Round 3, Round 4 only.
  - Doc claim: `tra-prototype/SKILL.md:372-387` — "Audit artifacts" section lists Round 1, Round 2, Round 3, Round 4 only.
  - Doc claim: `tra-prototype/README.md:120-124` — Mentions Round 1, Round 2, Round 3, Round 4 only.
  - Code reality: `ls docs/audit/round5/` returns 4 files: `track_r5_baseline.md`, `track_a5_findings.md`, `track_b5_findings.md`, `track_c5_findings.md` (this file). Round 5 audit deliverables exist.
- **Detail:** Round 5 audit is in progress (this file is one of the in-progress deliverables). It is expected that the docs don't yet reference Round 5 — but the omission means a reader using AGENTS.md or SKILL.md as the entry point will not know Round 5 exists. Once Round 5 closes, all 3 docs should be updated. Low-priority for now.
- **Suggested fix:** After Round 5 closes, add a "Round 5" row to: `AGENTS.md:51` (table), `tra-prototype/SKILL.md:387` (Audit artifacts list), and a sentence to `tra-prototype/README.md:124`.
- **Round 4 status:** new (the omission is a natural consequence of Round 5 being in progress; not a regression but a documentation gap that should be closed when Round 5 finalizes)

### TRA-C5-013: status.md:1 banner says HEAD `aae0bca` — actual HEAD is `5476faf` (1 commit ahead)

- **Severity:** INFO
- **Category:** Doc Consistency / stale-commit-ref
- **Finding type:** issue
- **Evidence:**
  - Doc claim: `status.md:1` — "The actual test count at HEAD `aae0bca` is **228 across 18 test files**"
  - Code reality: `git log --oneline -1` → `5476faf docs(audit): update test count 210 → 228 + Round 4 Batch 2 remediation status` (1 commit ahead of `aae0bca`). The HEAD `5476faf` is a docs-only commit (didn't change test count), so the "228" number is still accurate, but the commit-hash stamp is 1 commit stale.
- **Detail:** Subset of TRA-C5-010 — called out separately because the commit-hash staleness is a distinct defect from the file-count staleness. The HEAD `aae0bca` reference was correct when the banner was written (Batch 2 close), but the subsequent docs-only commit `5476faf` advanced HEAD without refreshing the banner's stamp. Track R5 noted this exact issue (R5 baseline TRA-C4-008: "Banner mentions commit `aae0bca` (1 commit behind HEAD) — minor staleness in the commit-hash reference").
- **Suggested fix:** Same as TRA-C5-010 — update `aae0bca` → `5476faf` in `status.md:1`.
- **Round 4 status:** persistent (TRA-C4-008 carry-over; R5 baseline noted this as a minor staleness — the banner was not refreshed when HEAD advanced)

### TRA-C5-P-001 (positive): All CLI examples use `python -m tra_cli` form — TRA-C4-013 BLOCKING fix holding

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / CLI invocation form
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `README.md:96-110` (root) — uses `python -m tra_cli translate`, `python -m tra_cli validate`, `python -m tra_cli audit`, `python -m tra_cli cache-clear` (all 4 correct).
  - Doc claim: `tra-prototype/README.md:23-36` — uses `python -m tra_cli translate`, `python -m tra_cli validate`, `python -m tra_cli audit`, `python -m tra_cli cache-clear` (all 4 correct — was the BLOCKING R4 finding TRA-C4-013).
  - Doc claim: `tra-prototype/SKILL.md:113-178` — uses `python -m tra_cli --help`, `python -m tra_cli translate input.md --level L3 -o input.en.md`, `python -m tra_cli validate input.md output.md --level L3`, `python -m tra_cli audit ./audit_trace.jsonl --report`, `python -m tra_cli cache-clear` (all correct).
  - Doc claim: `CLAUDE.md:35-38` — `ruff format . && ruff check . && mypy --strict tra && pytest tests` (correct tooling invocation).
  - Code reality: `tra_cli.py` is NOT executable (`-rw-rw-r--`), has no shebang, and `pyproject.toml` has no `[project.scripts]` entry point. Only `python -m tra_cli <subcommand>` and `python tra_cli.py <subcommand>` work. The bare `tra_cli.py <subcommand>` form (which R4 TRA-C4-013 BLOCKING flagged) does not appear anywhere in the audited doc set.
- **Detail:** The R4 BLOCKING finding TRA-C4-013 was fixed in Batch 1 commit `f226582` (per R4 remediation plan). Track R5 verified this holding (R5 baseline TRA-C4-013: "fixed-and-verified"). Track C5 re-confirms: zero occurrences of bare `tra_cli.py <subcommand>` form in any of the 12 audited docs.
- **Round 4 status:** fixed-and-verified (TRA-C4-013 carry-over; the BLOCKING fix from Batch 1 commit `f226582` is holding)

### TRA-C5-P-002 (positive): CLAUDE.md "Known gaps" section accurately reflects all Batch 4 code fixes (TRA-099, TRA-038, TRA-072, TRA-092)

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / status-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - `CLAUDE.md:48` — "TRA-099 fixed in round 4 commit `e54b7a7`" ✓ (CLI passes `registry=registry` at `tra_cli.py:139`)
  - `CLAUDE.md:49` — "TRA-038 fixed in round 4 commit `d95c36d`" + 3-raise-site enumeration (UnknownTerm at `:723`, CertaintyConflict at `:761`, EntityAmbiguity at `:360`) ✓
  - `CLAUDE.md:50` — "TRA-072 fixed in round 4 commit `78c9250`" + 4-call-site enumeration (Structural at `:794`, Entity at `:898`, Terminological at `:926`, Epistemic at `:959`) ✓
  - `CLAUDE.md:53` — "24 of 24 spec cases implemented (S-03 and E-03 added in round 4 remediation, TRA-092); spec target is 100+." ✓
  - `CLAUDE.md:51` — "Dependency hygiene (TRA-017, FIXED in Round 3 remediation commit `a3cd2c1`)" ✓ (TRA-C4-001 fixed)
- **Detail:** CLAUDE.md was the *only* doc whose "Known gaps" section was fully back-filled after Batch 1+2 code fixes. The parallel entries in `tra-prototype/README.md` were NOT back-filled (see TRA-C5-004/005/006/007). The asymmetry is the root cause of 4 of the 9 WARNING findings this round.
- **Round 4 status:** fixed-and-verified (TRA-C4-001 carry-over; CLAUDE.md "Known gaps" was fully refreshed in Batch 2 commit `929c879`)

### TRA-C5-P-003 (positive): TRA-017 status correctly marked "FIXED" in 3 docs (TRA-C4-001/002 fixed)

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / status-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - `CLAUDE.md:51` — "**Dependency hygiene (TRA-017, FIXED in Round 3 remediation commit `a3cd2c1`):** the 6 unused dependencies (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) were removed from `pyproject.toml`. Install footprint dropped from ~70 packages to ~15."
  - `tra-prototype/README.md:110-116` — "**Dependency hygiene** (TRA-017, FIXED in Round 3 remediation commit `a3cd2c1`): the 6 unused dependencies (...) were removed from `pyproject.toml`. Install footprint dropped from ~70 packages to ~15."
  - `tra-prototype/SKILL.md:267-271` — "**Dependencies trimmed** (TRA-017, fixed in Round 3): removed 6 unused deps (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) from `pyproject.toml`. Install footprint dropped from ~70 packages to ~15. The LLM seam is caller-supplied (never imports litellm) and tests are synchronous."
  - Code reality: `pyproject.toml` has exactly 6 runtime deps (`pydantic>=2.8`, `markdown-it-py>=3.0`, `diskcache>=5.6`, `pyyaml>=6.0`, `click>=8.1`, `rich>=13.7`) + 3 dev deps (`pytest>=8.2`, `ruff>=0.5`, `mypy>=1.10`). None of the 6 removed packages appear.
- **Detail:** R4 found TRA-017 was wrongly marked "persistent" in CLAUDE.md:51 and tra-prototype/README.md:103-105 (TRA-C4-001/002). Batch 2 commit `929c879` fixed both, plus the SKILL.md entry was already correct. All 3 docs now agree: TRA-017 is FIXED.
- **Round 4 status:** fixed-and-verified (TRA-C4-001/002 carry-over; both R4 WARNING findings resolved)

### TRA-C5-P-004 (positive): implementation_plan.md File Structure Summary now lists all 16 source modules + 16 test files (TRA-C4-009 fixed)

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / file-list-completeness
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `implementation_plan.md:305-361` — File Structure Summary now lists 16 source modules under `tra/` (including the 6 previously missing: `benchmark.py`, `config.py`, `hitl.py`, `recovery.py`, `reporting.py`, `validate.py`) + 4 modules under `tra/modules/` + 16 `test_*.py` files + `conftest.py` + `tests/benchmark/cases/` directory.
  - Code reality: `ls tra-prototype/tra/*.py | wc -l` → **16**; `ls tra-prototype/tra/modules/*.py | wc -l` → **4**; `ls tra-prototype/tests/test_*.py | wc -l` → **16**. All listed modules and test files exist as documented.
- **Detail:** R4 found the File Structure Summary was missing 6 modules + 5 test files (TRA-C4-009, INFO). Batch 2 commit `929c879` added all 6 missing modules and all 5 missing test files (the 5th was `tests/run_e2e_translation.py`, which was later deleted in Batch 3 commit `524c598` per TRA-D4-014, so the doc no longer needs to list it). The remaining stale annotation `test_outstanding_findings.py # TDD regression tests (34 classes, 139 tests)` is tracked separately as TRA-C5-003.
- **Round 4 status:** fixed-and-verified (TRA-C4-009 carry-over; the file structure was completed in Batch 2)

### TRA-C5-P-005 (positive): implementation_plan.md Dependencies table now lists only 9 packages (6 runtime + 3 dev) — TRA-C4-010 fixed

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / dep-table-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `implementation_plan.md:374-394` — Dependencies table lists exactly 9 packages: `pydantic`, `markdown-it-py`, `diskcache`, `pyyaml`, `click`, `rich` (6 runtime) + `pytest`, `ruff`, `mypy` (3 dev). No mention of `litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `pytest-asyncio`, or `black`.
  - Code reality: `pyproject.toml` `[project.dependencies]` lists exactly 6 packages; `[project.optional-dependencies.dev]` lists exactly 3. Match: 100%.
- **Detail:** R4 found the Dependencies table listed 15 packages including the 6 unused deps (TRA-C4-010, INFO). Batch 2 commit `929c879` refreshed the table to remove all 6 unused packages. The table now matches `pyproject.toml` exactly.
- **Round 4 status:** fixed-and-verified (TRA-C4-010 carry-over; the table was refreshed in Batch 2)

### TRA-C5-P-006 (positive): implementation_plan.md Phase 0.1.5 now lists 4 subcommands — TRA-C4-011 fixed

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / subcommand-list-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `implementation_plan.md:22` — "[x] 0.1.5 Set up CLI entry point skeleton (tra_cli.py with translate, validate, audit, cache-clear subcommands)"
  - Code reality: `tra_cli.py` defines 4 subcommands: `translate` (`@cli.command()`), `validate` (`@cli.command(name="validate")`), `audit` (`@cli.command()`), `cache-clear` (`@cli.command(name="cache-clear")`). Match: 100%.
- **Detail:** R4 found Phase 0.1.5 listed only 3 subcommands (missing `validate`, TRA-C4-011 INFO). Batch 2 commit `929c879` updated the parenthetical to list all 4. Phase 5.1.1-5.1.4 (`implementation_plan.md:220-223`) all marked `[x]` — consistent with the 4-subcommand reality.
- **Round 4 status:** fixed-and-verified (TRA-C4-011 carry-over)

### TRA-C5-P-007 (positive): implementation_plan.md Phase 0.1.2 correctly notes "black was removed; ruff format handles formatting" — TRA-C4-012 fixed

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / tooling-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `implementation_plan.md:19` — "[x] 0.1.2 Configure linting (ruff), formatting (ruff format), type checking (mypy strict), testing (pytest) *(note: black was removed in Round 3 remediation commit `a3cd2c1`; ruff format handles formatting)*"
  - Code reality: `pyproject.toml` `[project.optional-dependencies.dev]` lists `ruff>=0.5` but not `black`. `ruff format` is the formatter (per `CLAUDE.md:37`, `SKILL.md:236-238`, `tra-prototype/README.md:68`).
- **Detail:** R4 found Phase 0.1.2 mentioned "formatting (black)" (TRA-C4-012, INFO). Batch 2 commit `929c879` updated the line to "(ruff format)" and added the historical note about `a3cd2c1`. The note preserves the audit trail of the dep trim.
- **Round 4 status:** fixed-and-verified (TRA-C4-012 carry-over)

### TRA-C5-P-008 (positive): AGENTS.md "Files and roles" table now includes meta-docs (TRA-C4-017 fixed)

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / doc-inventory-completeness
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `AGENTS.md:9-32` — Now has 3 tables: "Normative spec files (the 5-file product)" (6 entries including the new `TRA-MODULE-AUTHORING.md` from TRA-100), "Meta-docs (orientation, planning, history)" (8 entries: `README.md`, `CLAUDE.md`, `AGENTS.md`, `start-here.md`, `implementation_plan.md`, `prototype.md`, `review.md` / `review-feedback.md`, `to_translate.md`, `status.md`), and "Prototype engine (`tra-prototype/`)" (4 entries: `tra-prototype/SKILL.md`, `tra-prototype/README.md`, `tra-prototype/tra/`, `tra-prototype/tests/`, `tra-prototype/pyproject.toml`).
  - Code reality: All listed docs exist; the inventory matches the actual repo structure.
- **Detail:** R4 found AGENTS.md "Files and roles" table omitted 7+ meta-docs (TRA-C4-017, INFO). Batch 2 commit `929c879` expanded the table to include all meta-docs. The new `TRA-MODULE-AUTHORING.md` (TRA-100 Batch 2 deliverable) is correctly listed.
- **Round 4 status:** fixed-and-verified (TRA-C4-017 carry-over)

### TRA-C5-P-009 (positive): Test count "228" is accurate across all 4 docs

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / test-count-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `CLAUDE.md:55`, `AGENTS.md:41`, `tra-prototype/README.md:125-126`, `tra-prototype/SKILL.md:243` — all 4 docs claim "228 tests".
  - Code reality: `python -m pytest tests --co 2>&1 | tail -1` → "228 tests collected in 0.41s" ✓
- **Detail:** R4 found the test count was stale at 174 (TRA-C4-003, WARNING). The count was correctly refreshed across Batch 1+2 commits to 199 → 210 → 228. The current count (228) is accurate. Only the file-count companion claim ("18 test files") is wrong — see TRA-C5-001.
- **Round 4 status:** fixed-and-verified (TRA-C4-003 carry-over; the test count was correctly refreshed, only the file count remains stale)

### TRA-C5-P-010 (positive): Benchmark cases count "24/24" is accurate in CLAUDE.md and SKILL.md

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / benchmark-count-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `CLAUDE.md:53` — "24 of 24 spec cases implemented (S-03 and E-03 added in round 4 remediation, TRA-092); spec target is 100+."
  - Doc claim: `tra-prototype/SKILL.md:359-360` — "Benchmark suite now at 24/24 spec cases (was 22/24). +2 cases."
  - Code reality: `cat tests/benchmark/cases/*.jsonl | wc -l` → **24 cases** total. S-03 and E-03 are present in `tests/benchmark/cases/sft.jsonl`.
- **Detail:** 2 of 3 docs that mention the benchmark count (CLAUDE.md, SKILL.md) correctly state "24/24". Only `tra-prototype/README.md:117-118` retains the stale "22 of 24" claim (TRA-C5-007). The 2 correctly-refreshed docs were updated in Batch 2 commit `d3e5f60` (TRA-092 fix).
- **Round 4 status:** fixed-and-verified (TRA-031 carry-over; benchmark count was correctly refreshed in CLAUDE.md and SKILL.md, but not in tra-prototype/README.md — see TRA-C5-007)

### TRA-C5-P-011 (positive): Round 1/2/3/4 audit deliverables references are internally consistent

- **Severity:** N/A (positive verification)
- **Category:** Doc Consistency / audit-ref-accuracy
- **Finding type:** positive_verification
- **Evidence:**
  - Doc claim: `AGENTS.md:46-51` — Round 1: 35 findings (11 BLOCKING / 22 WARNING / 2 INFO); Round 2: 41 findings (3 BLOCKING / 25 WARNING / 13 INFO); Round 3: 36 findings (2 BLOCKING / 18 WARNING / 16 INFO); Round 4: 47 issues + 19 positive verifications (1 BLOCKING / 11 WARNING / 35 INFO).
  - Doc claim: `CLAUDE.md:55` — Round 2 (41 findings), Round 3 (36 findings: 2 BLOCKING / 18 WARNING / 16 INFO), Round 4 (47 issues + 19 positive verifications: 1 BLOCKING / 11 WARNING / 35 INFO).
  - Code reality: All counts internally consistent (Round 1: 11+22+2=35 ✓; Round 2: 3+25+13=41 ✓; Round 3: 2+18+16=36 ✓; Round 4: 1+11+35=47 issues + 19 positive verifications = 66 total ✓). The audit deliverable directories `docs/audit/`, `docs/audit/round2/`, `docs/audit/round3/`, `docs/audit/round4/` all exist and contain the referenced files.
- **Detail:** No drift in audit-reference counts across docs. All 4 rounds' finding totals and severity breakdowns are consistent. Only the Round 5 references are missing (TRA-C5-012), which is expected since Round 5 is in progress.
- **Round 4 status:** verified-holding (no drift; the audit-reference counts have been stable since R4 close)

## Per-doc summary table

| Doc | Total claims checked | Stale claims | Findings |
|---|---|---|---|
| `README.md` (root) | 22 | 0 | — (all claims verified accurate; CLI examples all use `python -m tra_cli`) |
| `CLAUDE.md` | 18 | 1 (carry) | TRA-C5-001 (test file count "18" — wrong, should be 16) |
| `AGENTS.md` | 14 | 1 (carry) | TRA-C5-001 (test file count), TRA-C5-012 (missing Round 5 ref) |
| `start-here.md` | 9 | 0 | — (collapsed state labels acknowledged via CLAUDE.md:63 cross-reference) |
| `implementation_plan.md` | 42 | 3 | TRA-C5-001 (test file count not directly claimed but implied via File Structure Summary), TRA-C5-003 (test class/test count annotation "34 classes, 139 tests"), TRA-C5-009 (stale HEAD `805a8f8` stamp on Dependencies table) |
| `prototype.md` | 6 | 0 | — (Phase-0 project sketch; clearly labeled as planning) |
| `review.md` | 8 | 0 | — (historical external review, no current-state claims) |
| `review-feedback.md` | 6 | 0 | — (historical architectural critique, no current-state claims) |
| `status.md` | 4 | 1 | TRA-C5-010 + TRA-C5-013 (banner: "18 test files" wrong + `aae0bca` HEAD ref 1 commit stale) |
| `to_translate.md` | 7 | 1 | TRA-C5-008 (Chinese "100+ test cases" claim — actual is 24, 100+ is future target) |
| `tra-prototype/SKILL.md` | 52 | 4 | TRA-C5-001 (test file count), TRA-C5-002 (test class list omits 4 IDs + says "40 classes" vs actual 46), TRA-C5-011 (stale `263b901e...` hash), TRA-C5-012 (missing Round 5 ref) |
| `tra-prototype/README.md` | 28 | 5 | TRA-C5-001 (test file count), TRA-C5-004 (TRA-099 "CLI gap persists" stale), TRA-C5-005 (TRA-072 "ONLY conflict pair" stale), TRA-C5-006 (TRA-038 "still never raised" stale), TRA-C5-007 ("22 of 24 spec cases" stale) |
| **Totals** | **216** | **17** | **11 issues + 11 positive verifications = 22 findings** |

## Round 4 carry-over status matrix (Track C scope)

| Round 4 ID | Title | Round 5 status |
|---|---|---|
| TRA-C4-001 | CLAUDE.md TRA-017 "persistent" stale | **fixed-and-verified** (TRA-C5-P-003) |
| TRA-C4-002 | tra-prototype/README.md TRA-017 mirror | **fixed-and-verified** (TRA-C5-P-003) |
| TRA-C4-003 | SKILL.md §7 "174 tests" stale | **partial** — count refreshed to 228 ✓, but file count "18" still wrong (TRA-C5-001) |
| TRA-C4-004 | SKILL.md §7 stale TDD-regression test ID list | **partial** — list refreshed to 40 IDs ✓, but 4 IDs (TRA-016/017/026/042) missing; class count "40" wrong (actual 46) (TRA-C5-002) |
| TRA-C4-005 | SKILL.md §8 "remaining 24 Round 2 findings" stale | **fixed-and-verified** (§8 now correctly enumerates "Remaining persistent findings" subset) |
| TRA-C4-006 | SKILL.md "Audit artifacts" omits Round 3 | **fixed-and-verified** (now lists Round 1-4; Round 5 missing — TRA-C5-012) |
| TRA-C4-007 | tra-prototype/README.md R3 deliverables missing | **fixed-and-verified** (now references R1-R4) |
| TRA-C4-008 | status.md banner "174+" stale | **persistent** — banner now says "228" ✓ but file count "18" wrong + HEAD ref `aae0bca` 1 commit stale (TRA-C5-010 + TRA-C5-013) |
| TRA-C4-009 | implementation_plan.md File Structure Summary missing 6 modules + 5 test files | **fixed-and-verified** (TRA-C5-P-004); inline annotation "34 classes, 139 tests" still stale (TRA-C5-003) |
| TRA-C4-010 | implementation_plan.md Dependencies table 15 packages | **fixed-and-verified** (TRA-C5-P-005) |
| TRA-C4-011 | implementation_plan.md Phase 0.1.5 3 subcommands | **fixed-and-verified** (TRA-C5-P-006) |
| TRA-C4-012 | implementation_plan.md Phase 0.1.2 mentions black | **fixed-and-verified** (TRA-C5-P-007) |
| TRA-C4-013 | tra-prototype/README.md bare `tra_cli.py` invocations (BLOCKING) | **fixed-and-verified** (TRA-C5-P-001) |
| TRA-C4-014 | SKILL.md §8 "Round 1 carry over" stale TRA-016/017/026 | **fixed-and-verified** (§8 now correctly says "TRA-016/017/026 fixed in Round 3 remediation commit `a3cd2c1`") |
| TRA-C4-015 | tra-prototype/README.md TRA-006 "never invoked" stale | **partial** — original misleading phrasing replaced, but new phrasing "ONLY conflict pair arbitrated (TRA-072)" made stale by Batch 2 TRA-072 fix (TRA-C5-005) |
| TRA-C4-016 | tra-prototype/README.md TRA-004 "EntityAmbiguity now route" stale | **partial** — original misleading phrasing replaced, but new phrasing "still never raised in production" made stale by Batch 2 TRA-038 fix (TRA-C5-006) |
| TRA-C4-017 | AGENTS.md "Files and roles" omissions | **fixed-and-verified** (TRA-C5-P-008) |

**Net delta vs Round 4:** 11 fixed-and-verified, 4 partial (TRA-C4-003/004/015/016), 1 persistent (TRA-C4-008). 0 regressions. The R4 BLOCKING finding TRA-C4-013 is holding.

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture

# HEAD verification
git log --oneline -1
# → 5476faf docs(audit): update test count 210 → 228 + Round 4 Batch 2 remediation status

# Test count at HEAD (key claim audited)
cd tra-prototype
python -m pytest tests --co 2>&1 | tail -1
# → 228 tests collected in 0.41s  ✓ (matches all 4 docs' "228 tests" claim)

# Test file count at HEAD (key stale claim)
ls tests/test_*.py | wc -l
# → 16  ✗ (docs claim "18 test files" — TRA-C5-001)
ls tests/*.py | wc -l
# → 17  (includes conftest.py)
ls e2e_test.py  # → e2e_test.py  (manual demo at prototype root, NOT in tests/, NOT pytest-collected)

# Test classes in test_outstanding_findings.py (key stale list)
rg "^class Test" tests/test_outstanding_findings.py | wc -l
# → 46  ✗ (SKILL.md:246 claims "40 test classes" — TRA-C5-002)
python -m pytest tests/test_outstanding_findings.py --co 2>&1 | tail -1
# → 91 tests collected  ✗ (implementation_plan.md:346 claims "139 tests" — TRA-C5-003)

# CLI subcommands (TRA-C4-013 BLOCKING fix verification)
rg "add_command\(|@cli\.command" tra_cli.py
# → 4 @cli.command() decorators: translate, validate (named), audit, cache-clear (named)  ✓

# CLI invocation form (TRA-C4-013 BLOCKING fix verification)
rg "tra_cli\.py " tra-prototype/README.md tra-prototype/SKILL.md README.md
# → 0 matches (all use `python -m tra_cli` form)  ✓

# CLI registry= passing (TRA-099 fix verification — TRA-C5-004)
rg "registry=registry|registry=" tra_cli.py
# → tra_cli.py:138: registry = build_default_registry()
# → tra_cli.py:139: kernel = TRAKernel(cfg, registry=registry, interactive=interactive)  ✓

# PolicyResolver call sites (TRA-072 fix verification — TRA-C5-005)
rg "_POLICY_RESOLVER\.wins" tra/isa.py -n
# → tra/isa.py:794  (Structural P2 vs Fluency P6)
# → tra/isa.py:898  (Entity P3 vs Fluency P6)
# → tra/isa.py:926  (Terminological P4 vs Fluency P6)
# → tra/isa.py:959  (Epistemic P5 vs Fluency P6)  ✓ (4 call sites, not 1)

# TRA-038 exception raises/recoveries (TRA-038 fix verification — TRA-C5-006)
rg "raise CertaintyConflict|raise UnknownTerm|raise EntityAmbiguity" tra/ -n
# → tra/isa.py:761: raise CertaintyConflict(term=src_term)  ✓ (raised in LLM path)
rg "recover_unknown_term|recover_entity_ambiguity" tra/isa.py -n
# → tra/isa.py:360: recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)  ✓
# → tra/isa.py:723: recover_unknown_term(token, unresolved_ambiguities)  ✓

# Benchmark cases (TRA-092 fix verification — TRA-C5-007)
cat tests/benchmark/cases/*.jsonl | wc -l
# → 24  ✓ (S-03 and E-03 present)
rg '"id": "S-03"' tests/benchmark/cases/
# → tests/benchmark/cases/sft.jsonl  ✓
rg '"id": "E-03"' tests/benchmark/cases/
# → tests/benchmark/cases/sft.jsonl  ✓

# Dependencies (TRA-017 fix verification — TRA-C5-P-003)
python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('runtime:', len(d['project']['dependencies'])); print('dev:', len(d['project']['optional-dependencies']['dev']))"
# → runtime: 6  dev: 3  ✓

# Source module count (File Structure Summary verification — TRA-C5-P-004)
ls tra/*.py | wc -l
# → 16  ✓ (implementation_plan.md now lists all 16)
ls tra/modules/*.py | wc -l
# → 4  ✓

# Audit deliverables directories (TRA-C5-012 verification — Round 5 missing)
ls ../docs/audit/ ../docs/audit/round2/ ../docs/audit/round3/ ../docs/audit/round4/ ../docs/audit/round5/ -d
# → all 5 directories exist; Round 5 has 4 files (track_r5_baseline.md, track_a5_findings.md, track_b5_findings.md, track_c5_findings.md) but is not yet referenced in AGENTS.md / SKILL.md / tra-prototype/README.md

# Per-doc grep for stale claims
rg "228.*18 test files|18 test files" CLAUDE.md AGENTS.md tra-prototype/README.md tra-prototype/SKILL.md status.md -n
# → CLAUDE.md:55, AGENTS.md:41, tra-prototype/README.md:126, tra-prototype/SKILL.md:243, status.md:1
#   (5 stale "18 test files" claims — TRA-C5-001 + TRA-C5-010)

rg "40 test classes" tra-prototype/SKILL.md -n
# → tra-prototype/SKILL.md:246  (TRA-C5-002)

rg "34 classes, 139 tests" implementation_plan.md -n
# → implementation_plan.md:346  (TRA-C5-003)

rg "CLI gap persists|does not yet pass a registry" tra-prototype/README.md -n
# → tra-prototype/README.md:90  (TRA-C5-004)

rg "ONLY conflict pair arbitrated" tra-prototype/README.md -n
# → tra-prototype/README.md:107  (TRA-C5-005)

rg "still never raised in production" tra-prototype/README.md -n
# → tra-prototype/README.md:100  (TRA-C5-006)

rg "22 of 24 spec cases" tra-prototype/README.md -n
# → tra-prototype/README.md:117  (TRA-C5-007)

rg "100多个测试用例" to_translate.md -n
# → to_translate.md:28  (TRA-C5-008)

rg "Updated at HEAD .805a8f8." implementation_plan.md -n
# → implementation_plan.md:367  (TRA-C5-009)

rg "263b901e" tra-prototype/SKILL.md -n
# → tra-prototype/SKILL.md:328  (TRA-C5-011)
```

## Conclusion

Round 5 confirms that the R4 Batch 1+2 doc-refresh remediation commits (`f226582` + `929c879` + Batch 2/3/4 code-fix commits through `aae0bca`) successfully closed **11 of 17 R4 doc-consistency findings** — including the R4 BLOCKING finding TRA-C4-013 (bare `tra_cli.py` invocations). The CLI examples are now uniformly `python -m tra_cli` across all 12 audited docs; the implementation_plan.md File Structure Summary, Dependencies table, Phase 0.1.5 subcommand list, and Phase 0.1.2 tooling note are all current; AGENTS.md "Files and roles" table now enumerates meta-docs; the TRA-017 status is correctly marked FIXED in CLAUDE.md, tra-prototype/README.md, and SKILL.md.

However, **4 R4 findings remain partial** (TRA-C4-003/004/015/016) and **1 is persistent** (TRA-C4-008): the "228 tests across 18 test files" claim was supposed to be fixed in R4 Batch 2 (commit `929c879`) but the "18" was a typo in the R4 remediation plan that propagated to 5 docs (TRA-C5-001 + TRA-C5-010), and the SKILL.md §7 test class list was refreshed but is now stale again because Batch 2/3 added 6 more test classes that weren't back-filled (TRA-C5-002). Most consequentially, **`tra-prototype/README.md` "Known gaps" section was not back-filled after Batch 1+2 code fixes** — 4 entries (TRA-099, TRA-072, TRA-038, TRA-092) now describe the *exact opposite* of code reality, internally contradicting the parallel CLAUDE.md "Known gaps" section which WAS correctly refreshed (TRA-C5-004/005/006/007). This is the same root cause flagged by Track R5 (TRA-C4-015/016 partial) — the Batch 2 doc-refresh commit `929c879` updated CLAUDE.md but not the parallel tra-prototype/README.md entries, and the subsequent Batch 2 code-fix commits (`d95c36d`, `efbc875`, `78c9250`, `d3e5f60`, `e54b7a7`) widened the gap.

No new BLOCKING findings; no regressions. The codebase at HEAD `5476faf` is in a strictly improved state relative to the R4 baseline from a doc-consistency standpoint — but a focused Batch 5 doc-refresh commit is needed to close the 4 partial findings (TRA-C4-003/004/015/016) and the 5 new drift items introduced by Batch 2 code fixes (TRA-C5-001/002/004/005/006/007). Recommended Batch 5 doc-refresh scope: (1) replace "18 test files" → "16 test files" in 5 docs; (2) regenerate SKILL.md §7 test class list from `rg "^class Test" tests/test_outstanding_findings.py`; (3) update tra-prototype/README.md "Known gaps" TRA-099/038/072/092 entries to mirror CLAUDE.md; (4) update tra-prototype/README.md:117-118 benchmark count "22 of 24" → "24 of 24"; (5) refresh status.md:1 banner HEAD ref `aae0bca` → `5476faf`; (6) update implementation_plan.md:346 annotation; (7) refresh SKILL.md:328 with note about Batch 4 hash change. Estimated effort: ~30 minutes of doc edits, no code changes.
