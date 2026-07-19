# TRA Round 5 — Comprehensive TDD Remediation Plan

**Created:** 2026-07-19
**Based on:** Round 5 audit (68 findings: 46 issues + 22 positive verifications; 0 BLOCKING / 7 WARNING / 39 INFO)
**Approach:** TDD (Red → Green → Refactor → Commit) per finding
**Codebase:** `/home/z/my-project/Translation-Runtime-Architecture/` at HEAD `5476faf`

## Remediation Strategy

Findings are grouped into 5 batches by priority and dependency. Each batch is a milestone (commit + optional push). Within each batch, fixes are independent and can be applied in sequence.

**Batch 1 — Documentation refresh (Track C5 cluster)** — 7 doc-consistency WARNINGs + INFOs; the highest-density cluster this round
**Batch 2 — Spec-conformance partial-fixes (TRA-042 regex gaps, TRA-072 P1 factual)** — 2 WARNINGs from Track A5
**Batch 3 — Persistent Phase 0 prototype gaps (TRA-001 per-leaf, TRA-090 LLM seam, TRA-091 HITL e2e)** — the Phase 8 sprint
**Batch 4 — Test suite gaps (TRA-094 mutation testing, TRA-092 benchmark 24→100+, L2 coverage, CLI CliRunner)** — 4 INFO findings
**Batch 5 — Code quality (dead `forbidden_mappings` field, type-safety residuals, ModuleInterface edge cases)** — 7 INFO findings
**Deferred** — TRA-040 (EXCEPTION_HANDLER as KernelState — intentional; needs spec change), TRA-079 (cache HMAC — INFO, low priority)

---

## Batch 1: Documentation Refresh (Milestone 2 — ~2 hours)

### 1.1 TRA-C5-001: "228 tests across 18 test files" wrong in 4 docs

**Root cause:** `CLAUDE.md:55`, `AGENTS.md:41`, `tra-prototype/README.md:126`, `tra-prototype/SKILL.md:243` all claim "228 tests across 18 test files". Actual at HEAD `5476faf`: **228 tests across 16 test files** (`python -m pytest tests --co` → "228 tests collected"; `ls tests/test_*.py | wc -l` = 16). The "18" typo originated in the R4 remediation plan and was propagated by the R4 Batch 1 doc-refresh commit `929c879`.

**Optimal fix:** Replace "18 test files" with "16 test files" in all 4 docs. Verify with `rg "across 1[68] test files"` returns 0 hits post-fix.

**TDD steps:**
1. RED: `rg "across 18 test files" CLAUDE.md AGENTS.md tra-prototype/README.md tra-prototype/SKILL.md` → 4 matches.
2. GREEN: Edit each file to say "16 test files". Re-run grep → 0 matches.
3. COMMIT.

**Files touched:** `CLAUDE.md`, `AGENTS.md`, `tra-prototype/README.md`, `tra-prototype/SKILL.md`
**Estimated effort:** 15 minutes

### 1.2 TRA-C5-003: implementation_plan.md "34 classes, 139 tests" stale annotation

**Root cause:** `implementation_plan.md:346` inline annotation says `# TDD regression tests (34 classes, 139 tests)`. Actual at HEAD `5476faf`: **46 classes, 91 tests** in `tests/test_outstanding_findings.py` (verified via `rg "^class Test" tests/test_outstanding_findings.py | wc -l` and `pytest tests/test_outstanding_findings.py --co -q | tail -1`).

**Optimal fix:** Update annotation to "46 classes, 91 tests".

**TDD steps:**
1. RED: `rg "34 classes, 139 tests" implementation_plan.md` → 1 match.
2. GREEN: Replace with "46 classes, 91 tests". Re-run grep → 0 matches.
3. COMMIT.

**Files touched:** `implementation_plan.md`
**Estimated effort:** 5 minutes

### 1.3 TRA-C5-004: tra-prototype/README.md "Known gaps" TRA-099 entry misleading

**Root cause:** `tra-prototype/README.md:90-95` "Known gaps" section still describes TRA-099 (CLI `--registry` flag) as persistent, but it was FIXED in R4 Batch 1 commit `e54b7a7`. The CLAUDE.md entry was updated in Batch 2 commit `929c879` but the parallel entry in `tra-prototype/README.md` was not back-filled.

**Optimal fix:** Update `tra-prototype/README.md:90-95` to say "FIXED in R4 Batch 1 commit `e54b7a7`" (matching CLAUDE.md).

**Files touched:** `tra-prototype/README.md`
**Estimated effort:** 10 minutes

### 1.4 TRA-C5-007 (WARNING, new-regression): tra-prototype/README.md "22 of 24 spec cases" stale

**Root cause:** `tra-prototype/README.md:117-118` says "22 of 24 spec cases implemented (S-03 and E-03 added in round 4 remediation, TRA-092)". This was accurate at R4 baseline `805a8f8` when S-03/E-03 were missing. R4 Batch 2 commit `d3e5f60` added the cases and updated CLAUDE.md + SKILL.md but NOT `tra-prototype/README.md` — drift introduced by incomplete Batch 2 back-fill. Actual at HEAD: **24 of 24 spec cases**.

**Optimal fix:** Update to "24 of 24 spec cases implemented (S-03 and E-03 added in R4 Batch 2 commit `d3e5f60`)".

**Files touched:** `tra-prototype/README.md`
**Estimated effort:** 5 minutes

### 1.5 TRA-C5-005 + TRA-C5-006: tra-prototype/README.md "Known gaps" TRA-072 + TRA-038 entries

**Root cause:** `tra-prototype/README.md:96-103` describes TRA-038 (3 unreachable exceptions) and TRA-072 (PolicyResolver 1 pair) as persistent. Both were partially fixed in R4 Batch 2 (commits `d95c36d` and `78c9250`). The "Known gaps" entry was not back-filled.

**Optimal fix:** Update TRA-038 entry to "partial-fixed (R4 Batch 2 commit `d95c36d` wired 3 exception types via direct recovery calls; full exception-flow with EXCEPTION_HANDLER audit records still pending)". Update TRA-072 entry to "partial-fixed (R4 Batch 2 commit `78c9250` routed all 4 severity decisions through PolicyResolver; P1 factual-integrity arbitration still pending — see TRA-A5-013)".

**Files touched:** `tra-prototype/README.md`
**Estimated effort:** 15 minutes

### 1.6 TRA-C5-010 + TRA-C5-013: status.md banner stale

**Root cause:** `status.md:1` banner says "actual test count at HEAD `aae0bca` is 228 across 18 test files". HEAD is now `5476faf`; file count is 16. Also, the banner is the only useful content of `status.md` (the body is a frozen commit log from `4d97aa1`).

**Optimal fix:** Either (a) update the banner to "HEAD `5476faf` is 228 across 16 test files", or (b) delete `status.md` entirely (it's a frozen historical session log; the banner is the only useful content). Recommend (b) — the file serves no current purpose.

**Files touched:** `status.md` (delete or refresh)
**Estimated effort:** 5 minutes

### 1.7 TRA-C5-011: SKILL.md §8 stale sha256 hash

**Root cause:** `tra-prototype/SKILL.md:328` says "audit_trace.jsonl sha256 `263b901e...`". This was the R4 baseline hash; HEAD `5476faf` produces sha256 `902298b3...` (because R4 Batch 2 enriched the audit trail). The within-HEAD byte-reproducibility invariant (TRA-013) still holds — only the absolute hash changed.

**Optimal fix:** Update SKILL.md §8 to say "audit_trace.jsonl sha256 `902298b3...` (within-HEAD byte-reproducibility holds; absolute hash differs from R4 baseline `263b901e...` because R4 Batch 2 enriched audit-trail content)".

**Files touched:** `tra-prototype/SKILL.md`
**Estimated effort:** 5 minutes

### 1.8 TRA-C5-012: Audit deliverables references omit Round 5

**Root cause:** `AGENTS.md`, `tra-prototype/SKILL.md`, `tra-prototype/README.md` all reference Round 1–4 audit deliverables but not Round 5. This is a natural consequence of Round 5 being in progress at the time of writing; should be closed when Round 5 finalizes.

**Optimal fix:** Add Round 5 references (`docs/audit/round5/` — `TRA_Prototype_Audit_Report_r5.docx`, `TRA_audit_findings_register_r5.xlsx`, `TRA_audit_severity_heatmap_r5.png`, `master_findings_register_r5.json`, `remediation_plan_r5.md`, per-track findings `track_{r5,a5,b5,c5,d5,e5,f5}_*.md`).

**Files touched:** `AGENTS.md`, `tra-prototype/SKILL.md`, `tra-prototype/README.md`
**Estimated effort:** 15 minutes

### 1.9 TRA-C5-008: to_translate.md "100+ test cases" Chinese claim

**Root cause:** `to_translate.md:28` says "包含100多个测试用例" (more than 100 test cases). Actual benchmark count is 24. This misrepresentation predates R4 (R4 Track C4 did not audit `to_translate.md` for this claim).

**Optimal fix:** Either (a) update to "包含24个测试用例" (24 test cases), or (b) update to "包含100+测试用例的目标" (target of 100+ test cases) to reflect the spec's growth target. Recommend (b) — it's accurate and aspirational.

**Files touched:** `to_translate.md`
**Estimated effort:** 5 minutes

**Estimated effort (Batch 1 total):** ~1.5 hours

---

## Batch 2: Spec-Conformance Partial-Fixes (Milestone 3 — ~10 hours)

### 2.1 TRA-A5-005 (WARNING): TRA-042 structural verification regex gaps

**Root cause:** R4 Batch 2 commit `efbc875` extended `verify_output` from 1 structural check (heading count) to 6 (heading, table row, list item, blockquote, HR, code fence). However, two regex gaps remain:
- **Ordered-list regex missing:** `_LIST_ITEM_RE = re.compile(r"^\s*[-*+] |\n\s*[-*+] ", re.MULTILINE)` only matches unordered list items (`-`, `*`, `+`). Ordered list items (`1.`, `2.`, etc.) are not counted — a source with 5 ordered items and a target with 3 would pass the check.
- **Blockquote regex too narrow:** `_BLOCKQUOTE_RE = re.compile(r"^\s*>\s", re.MULTILINE)` requires whitespace after `>`. A blockquote line `>text` (no space) is not matched. CommonMark allows both; the spec target should match.

**Optimal fix:**
- Update `_LIST_ITEM_RE` to also match `^\s*\d+\.\s+` (ordered list items).
- Update `_BLOCKQUOTE_RE` to `r"^\s*>"` (match `>` regardless of trailing whitespace).

**TDD steps:**
1. RED: Write tests that construct source/target pairs with ordered-list and `>text` blockquote mismatches; assert BLOCKING diagnostic is raised. (Currently passes incorrectly.)
2. GREEN: Update the two regexes. Re-run tests — they should now fail (correctly raising BLOCKING) until the target is fixed; with matching target, they pass.
3. Run full benchmark suite — verify no false-positive BLOCKING on conformant inputs.
4. COMMIT.

**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 2 hours

### 2.2 TRA-A5-013 (WARNING, new): No factual-integrity check in `verify_output`

**Root cause:** `verify_output` (`tra/isa.py`) checks structural, terminological, entity, and epistemic invariants, but has **no factual-integrity check**. The `FACTUAL_DRIFT` failure condition from `TRA-ISA-REFERENCE.md` is never raised. `PolicyPriority.FACTUAL_INTEGRITY` (P1, the highest priority) is never arbitrated through `_POLICY_RESOLVER.wins()`. This is the only spec-mandated check with NO implementation at all.

The spec defines factual integrity as: "Numbers, units, logical conditions, empirical claims" (Spec §5.1). The LLM seam is the natural place for factual drift to occur — an LLM might summarize `v0.5.0` as `version 0.5` or `2024-01-15` as `January 2024`.

**Optimal fix:**
- In `verify_output`, add a `_check_factual_integrity(source, target, ctx)` function that:
  1. Extracts all version-like tokens (`v?\d+\.\d+\.\d+`, `\d+\.\d+`) from source via regex.
  2. Extracts the same from target.
  3. For each source token, verifies it appears verbatim in target. If not, emit a BLOCKING diagnostic with `subsystem="FACTUAL_VERIFICATION"`, `issue="Version drift"`, `evidence=f"source={src_token} target=<missing or different>"`.
  4. Repeat for dates (`\d{4}-\d{2}-\d{2}`), numeric quantities (`\d+\s*(?:KB|MB|GB|ms|ns|...)`), and explicit constants (`true`/`false`/`null`).
- Route the severity decision through `_POLICY_RESOLVER.wins(PolicyPriority.FACTUAL_INTEGRITY, PolicyPriority.TARGET_FLUENCY)` (will always return True — P1 beats P6 — but the contract is now explicit).

**TDD steps:**
1. RED: Write a test that constructs a source/target pair where the target dropped a version number; assert a BLOCKING `FACTUAL_VERIFICATION` diagnostic is raised. (Currently passes incorrectly — no check exists.)
2. GREEN: Implement `_check_factual_integrity`. Re-run test — should now pass.
3. Add positive test: conformant target (all versions preserved) → no factual diagnostic.
4. Add PolicyResolver monkeypatch test: patch `_POLICY_RESOLVER.wins` to return False; verify factual severity drops to WARNING.
5. Run full benchmark suite — verify no false-positive BLOCKING.
6. COMMIT.

**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 6 hours

### 2.3 TRA-A5-003 (WARNING, partial): TRA-038 full exception-flow wiring

**Root cause:** R4 Batch 2 commit `d95c36d` wired 3 previously-unreachable exception types via direct `recover_*` calls in `isa.py`:
- `recover_unknown_term` called at `isa.py:723` in `_rule_translate` for CJK tokens with no match.
- `recover_entity_ambiguity` called at `isa.py:360` in `build_entity_table` for tokens matching multiple patterns.
- `CertaintyConflict` raised at `isa.py:761` in the LLM path.

However, the `UnknownTerm` and `EntityAmbiguity` recovery paths **bypass the kernel's `_recover` dispatcher** (`tra/kernel.py:_recover`). Consequences:
- No `EXCEPTION_HANDLER` audit record is emitted for these two exception types (the L4 `ambiguity_register.json` captures the entries via direct list-append, but the `audit_trace.jsonl` does not record the exception event).
- The `CertaintyConflict` path correctly routes through `_recover` (because it's raised, not directly called), so it does emit an `EXCEPTION_HANDLER` audit record.

**Optimal fix:**
- Refactor `isa.py:723` and `isa.py:360` to `raise UnknownTerm(...)` / `raise EntityAmbiguity(...)` instead of directly calling `recover_*`.
- Ensure the kernel's `_recover` dispatcher catches these and routes through `recover_unknown_term` / `recover_entity_ambiguity`.
- Verify the `audit_trace.jsonl` now contains `EXCEPTION_HANDLER` records for these exception types.
- Verify the `ambiguity_register.json` still contains the entries (recovery procedure should still append).

**TDD steps:**
1. RED: Write a test that runs an L4 translation on a source with unknown CJK tokens; assert `audit_trace.jsonl` contains at least one `EXCEPTION_HANDLER` record with `exception_code="UNKNOWN_TERM"`. (Currently fails — no such record.)
2. GREEN: Refactor the two call sites to `raise`. Re-run test — should now pass.
3. Verify `ambiguity_register.json` still contains the entries.
4. Run full benchmark suite — verify no regressions.
5. COMMIT.

**Files touched:** `tra/isa.py`, `tra/kernel.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 4 hours

**Estimated effort (Batch 2 total):** ~12 hours

---

## Batch 3: Persistent Phase 0 Prototype Gaps (Milestone 4 — Phase 8 Sprint, ~24 hours)

### 3.1 TRA-A5-001 (WARNING, persistent): TRA-001 per-leaf segment translation

**Root cause:** `tra/kernel.py:485` calls `translate_segment(protected, self.ctx, ...)` ONCE on the entire protected source (after fenced/inline code-block extraction). Spec §3 `TRANSLATE_SEGMENT` Inputs say "Source Segment" (leaf-level: sentence, list item, table cell, heading). Consequences:
- Per-document cache keys (not per-segment); cache invalidation is all-or-nothing.
- `RepairAttempt.segment_index` always 0 (`tra/memory.py:230` field description is misleading).
- `evidence_trace.jsonl` uses substring containment (TRA-094 consequence), producing orphan lines.

**Optimal fix:** Refactor `_execute_translation` to walk `ctx.structural_map.nodes`, identify leaf segments (`NodeKind.PARAGRAPH`, `LIST_ITEM`, `TABLE_CELL`, `HEADING`), call `translate_segment` per leaf, then re-assemble the target via the structural map. Pass the leaf's index to `repair_segment` so `RepairAttempt.segment_index` is meaningful. Update `reporting.line_by_line_trace` to map line → structural node → evidence chain.

**TDD steps:** 5-7 RED-GREEN cycles (one per leaf kind, plus assembly + repair index + line-by-line trace).
**Files touched:** `tra/kernel.py`, `tra/isa.py`, `tra/reporting.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 16 hours

### 3.2 TRA-D5-002 (WARNING, persistent): e2e LLM hijack uses module-level patching (TRA-090)

**Root cause:** `tests/test_e2e_to_translate.py` patches `tra.isa._rule_translate` at the module level to substitute the LLM seam with the contents of `to_translate.en.md`. This is fragile — any refactor that renames `_rule_translate` breaks the test silently. The proper pattern is dependency injection: pass `llm_translate` as a callback to `TRAKernel.run()`.

**Optimal fix:**
- Add `llm_translate: Callable[[str], str] | None = None` parameter to `TRAKernel.run()`.
- In `_execute_translation`, if `llm_translate` is supplied, call it instead of `_rule_translate`.
- Refactor `test_e2e_to_translate.py` to pass a callback that reads `to_translate.en.md` and returns the matching segment.
- Remove the module-level `monkeypatch`.

**TDD steps:**
1. RED: Write a test that constructs `TRAKernel` with a stub `llm_translate` callback; assert the callback is invoked with the source segment and the return value is used as the translation.
2. GREEN: Implement the `llm_translate` parameter; refactor `_execute_translation` to use it.
3. Refactor `test_e2e_to_translate.py` to use the new pattern.
4. Run full test suite — verify all 228 tests still pass.
5. COMMIT.

**Files touched:** `tra/kernel.py`, `tests/test_e2e_to_translate.py`
**Estimated effort:** 4 hours

### 3.3 TRA-D5-007 (WARNING, persistent): `interactive=True` kernel path untested e2e (TRA-091)

**Root cause:** No e2e test of the `--interactive` CLI flag. The HITL path is exercised only by unit tests of `review_decision`. R4 deferred this; R5 confirms still deferred.

**Optimal fix:** Add an e2e test that pipes simulated stdin to `python -m tra_cli translate ... --interactive` and asserts:
1. The HITL prompt is displayed when `Unrecoverable` is raised.
2. `accept` input → repair is accepted, translation continues.
3. `override` input → user-supplied override is used, `HUMAN_OVERRIDE` evidence record emitted.
4. `skip` input → segment is skipped, `RAISE_FLAG` evidence record emitted.

Use `click.testing.CliRunner` with `input=` parameter for stdin simulation.

**TDD steps:**
1. RED: Write 3 tests (accept/override/skip) — currently fail because no e2e HITL test exists.
2. GREEN: Implement the tests using `CliRunner(input=...)`.
3. Verify all 3 pass.
4. COMMIT.

**Files touched:** `tests/test_outstanding_findings.py` (or new `tests/test_cli_interactive.py`)
**Estimated effort:** 4 hours

**Estimated effort (Batch 3 total):** ~24 hours (3 person-days)

---

## Batch 4: Test Suite Gaps (Milestone 5 — ~16 hours)

### 4.1 TRA-D5-016 (INFO, new): L2_PROFESSIONAL conformance level never tested

**Root cause:** All e2e tests use L3 or L4. The L2_PROFESSIONAL level is never exercised end-to-end. Per Spec §8, L2 = "Meaning, Formatting, Terminology, Entity preservation; basic QA" — distinct from L1 (no terminology enforcement) and L3 (full diagnostics + zero BLOCKING gate).

**Optimal fix:** Add a `test_l2_professional_e2e` test that:
1. Translates `to_translate.md` at `--level L2`.
2. Asserts the L2 gate does NOT enforce zero-BLOCKING (unlike L3).
3. Asserts terminology and entity preservation still apply.

**Files touched:** `tests/test_e2e_to_translate.py`
**Estimated effort:** 2 hours

### 4.2 TRA-D5-017 (INFO, new): CLI subcommands not CliRunner-tested

**Root cause:** The 4 CLI subcommands (`translate`, `validate`, `audit`, `cache-clear`) are exercised end-to-end only via shell-out in `e2e_test.py`. They should be tested via `click.testing.CliRunner` for proper isolation and assertion capability.

**Optimal fix:** Add `tests/test_cli.py` with `CliRunner`-based tests for each subcommand:
1. `translate --help` exits 0 and shows usage.
2. `translate input.md --level L3 -o out.md` produces `out.md`.
3. `validate input.md out.md --level L3` exits 0 (PASS) on conformant output.
4. `validate input.md out.md --level L3` exits 1 (FAIL) on non-conformant output.
5. `audit audit_trace.jsonl --report` produces the conformance summary + Mermaid diagram.
6. `cache-clear` clears the cache and reports the count.

**Files touched:** `tests/test_cli.py` (new)
**Estimated effort:** 4 hours

### 4.3 TRA-D5-011 (INFO, persistent): Mutation testing framework deferred (TRA-094)

**Root cause:** No mutation testing in the test suite. R3 deferred this; R4 confirmed still deferred; R5 confirms again. Track D5's manual mutation probe (5 mutations: 4 killed / 1 survives) suggests ~80% mutation score — above the typical 80% threshold but not measured continuously.

**Optimal fix:** Integrate `mutmut` (preferred — simpler) or `cosmic-ray`. Run on `tra/` package. Add a CI job that runs mutation testing on every PR and fails if mutation score < 80%.

**TDD steps:**
1. Install `mutmut`: `pip install mutmut`.
2. Configure `[tool.mutmut]` in `pyproject.toml` with `paths_to_mutate = "tra"`.
3. Run `mutmut run` — capture baseline mutation score.
4. Add `.github/workflows/mutation.yml` (or equivalent) that runs `mutmut run` on PRs.
5. Document the mutation score in `tra-prototype/SKILL.md` §7.

**Files touched:** `pyproject.toml`, `.github/workflows/mutation.yml` (new), `tra-prototype/SKILL.md`
**Estimated effort:** 8 hours

### 4.4 TRA-D5-006 (INFO, partial): Benchmark suite at 24/100+ spec target

**Root cause:** Only 24 benchmark cases (S:5/F:5/T:5/D:4/E:3/R:1). Spec target is 100+. R4 Batch 2 added S-03 + E-03 (closing the spec-required minimum); 76 more cases needed to reach 100+.

**Optimal fix:** Add 76 more cases across S/F/T/D/E categories:
- S (Structural): +15 cases — tables, nested lists, blockquotes, code blocks, links, anchors.
- F (Factual): +15 cases — version strings, dates, units, numeric quantities, boolean constants.
- T (Terminology): +15 cases — canonical mappings, context-sensitive terms, forbidden targets.
- D (Domain): +15 cases — security advisories, RFCs, API references, architecture guides.
- E (Ambiguity): +16 cases — entity vs natural language, glossary conflicts, epistemic hedging.

Each case is a JSONL entry with `id`, `source`, `expected_target`, `expected_diagnostics`, `expected_evidence`.

**Files touched:** `tests/benchmark/cases/sft.jsonl`
**Estimated effort:** 16 hours (for 76 cases)

**Estimated effort (Batch 4 total):** ~30 hours (3.75 person-days)

---

## Batch 5: Code Quality (Milestone 6 — ~6 hours)

### 5.1 TRA-A5-014 (INFO, new): Dead `ctx.forbidden_mappings` field

**Root cause:** `RuntimeContext.forbidden_mappings` is defined in `tra/memory.py` but never populated or read. `_forbidden_from_module(ctx)` reads from `ctx.module.get_glossary_mappings()` instead. The field is dead weight on the Pydantic model.

**Optimal fix:** Remove `forbidden_mappings` from `RuntimeContext`. Search for any references first (`rg "forbidden_mappings" tra/`) — if 0 hits outside the model definition, delete it.

**TDD steps:**
1. RED: `rg "forbidden_mappings" tra/` → confirm only the model definition reference.
2. GREEN: Remove the field. Run `mypy --strict tra` → 0 issues. Run `pytest tests` → 228 pass.
3. Add a regression test that asserts the field does not exist: `assert not hasattr(RuntimeContext(), 'forbidden_mappings')`.
4. COMMIT.

**Files touched:** `tra/memory.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 30 minutes

### 5.2 TRA-A5-010 (INFO, new): 6 ISA instruction contract docstrings inconsistent

**Root cause:** The 6 ISA instruction functions in `tra/isa.py` have docstrings, but some lack explicit `Invariant:` / `Failure Condition:` labels per the Spec §3 contract template. The labels are present in the spec but inconsistently applied in the docstrings.

**Optimal fix:** Audit each of the 6 ISA functions' docstrings; add explicit `Invariant:` and `Failure Condition:` labels per Spec §3.

**Files touched:** `tra/isa.py`
**Estimated effort:** 1 hour

### 5.3 TRA-B5-009 (INFO, persistent): `registry: object | None` with stale `# type: ignore`

**Root cause:** `tra/kernel.py:111` types `registry: object | None` with a `# type: ignore[arg-type]` comment. This is a carry-over from R3 (TRA-B3-005). The proper type is `ModuleRegistry | None`.

**Optimal fix:** Change `registry: object | None` → `registry: ModuleRegistry | None`. Remove the `# type: ignore` comment. Import `ModuleRegistry` from `tra.modules.registry`.

**TDD steps:**
1. RED: `rg "registry: object" tra/kernel.py` → 1 match.
2. GREEN: Replace with `registry: ModuleRegistry | None`. Remove `# type: ignore`. Run `mypy --strict tra` → 0 issues.
3. Add a regression test that asserts the type annotation is `ModuleRegistry | None`.
4. COMMIT.

**Files touched:** `tra/kernel.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 30 minutes

### 5.4 TRA-B5-010 (INFO, persistent): `_collect_headings(nodes: list[Any])` should be `list[StructuralNode]`

**Root cause:** `tra/anchor.py` (or wherever `_collect_headings` lives) types `nodes: list[Any]`. Should be `list[StructuralNode]`.

**Optimal fix:** Change the annotation. Remove any `# type: ignore` it requires.

**Files touched:** `tra/anchor.py`
**Estimated effort:** 15 minutes

### 5.5 TRA-B5-011 (INFO, persistent): Stale `# type: ignore[arg-type]` at `tests/test_recovery.py`

**Root cause:** `tests/test_recovery.py` has a stale `# type: ignore[arg-type]` comment that's no longer needed (the underlying type issue was fixed in R3).

**Optimal fix:** Remove the comment. Run `mypy --strict tra` to confirm no new issues.

**Files touched:** `tests/test_recovery.py`
**Estimated effort:** 5 minutes

### 5.6 TRA-F5-011 (INFO, new): `register()` silently accepts `kind="language"` module with no `metadata.direction`

**Root cause:** `tra/modules/registry.py:register()` accepts a `ModuleInterface` with `kind="language"` but no `metadata.direction` field. Such a module is silently unreachable — `_select_module` filters by direction.

**Optimal fix:** In `register()`, validate that `kind="language"` modules have a non-empty `metadata.direction`. Raise `ValueError` if missing.

**TDD steps:**
1. RED: Write a test that constructs a `ModuleInterface(kind="language", metadata={})` and calls `register()`; assert `ValueError` is raised. (Currently passes — no validation.)
2. GREEN: Add the validation. Re-run test — should now pass.
3. COMMIT.

**Files touched:** `tra/modules/registry.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 30 minutes

### 5.7 TRA-F5-012 + TRA-F5-013 (INFO, new): Module authoring guide improvements

**Root cause:**
- TRA-F5-012: `ModuleInterface` accepts dict-returning `get_style_profile()` (Pydantic coerces), but this is undocumented in `TRA-MODULE-AUTHORING.md` §2.2.
- TRA-F5-013: The authoring guide's `LanguageModuleProtocol` snippet omits `name`/`kind` annotations and uses simplified return types vs. the actual Protocol in `base.py`.

**Optimal fix:**
- Add a note in §2.2 about dict coercion: "Returning a `dict` is accepted (Pydantic coerces to `StyleProfile`), but returning a `StyleProfile` instance is preferred for type safety."
- Update the Protocol snippet to match `base.py` exactly (include `name`/`kind` annotations and precise return types).

**Files touched:** `TRA-MODULE-AUTHORING.md`
**Estimated effort:** 30 minutes

### 5.8 TRA-F5-010 (WARNING, new): `_normalize_language_pair` silently upper-cases malformed `--lang` values

**Root cause:** `tra_cli.py:_normalize_language_pair` silently upper-cases malformed `--lang` values (e.g., `fr` → `FR`), which then silently fall back to ZHENModule because no `FR` module is registered. This is a UX regression introduced by the TRA-099 fix.

**Optimal fix:** When `--lang` doesn't match `<source>-<target>` pattern (e.g., `fr-en`), emit a WARNING audit record and exit with non-zero status. Alternatively, prompt the user to confirm the fallback to ZHENModule.

**TDD steps:**
1. RED: Write a test that runs `python -m tra_cli translate input.md --lang fr` and asserts a non-zero exit code or a WARNING audit record. (Currently passes — silent fallback.)
2. GREEN: Add the validation in `_normalize_language_pair`. Re-run test — should now pass.
3. COMMIT.

**Files touched:** `tra_cli.py`, `tests/test_outstanding_findings.py`
**Estimated effort:** 1 hour

**Estimated effort (Batch 5 total):** ~5 hours

---

## Deferred

### TRA-A5-004 / TRA-040: EXCEPTION_HANDLER and HALT_ERROR not modeled as KernelStates

**Status:** Intentional design decision. Spec §2.1's stateDiagram shows `EXCEPTION_HANDLER` as a state, but the implementation treats it as a side-channel audit-record type. The spec is ambiguous; resolving this requires a spec change first. Recommend deferring until spec author weighs in.

### TRA-B5-004 / TRA-079: Cache HMAC integrity

**Status:** INFO, deferred from R3. Cache now stores JSON (TRA-077), which is safe from RCE, but an attacker who can write to the cache directory could still inject bogus translations. HMAC would close this. Lower priority because the cache directory is assumed trusted (single-user dev environment).

### TRA-E5-016 (WARNING, new): `ambiguity_register.json` + `execution_log.json` non-deterministic across cache states

**Status:** New WARNING from Track E5. The `_log_unknown_cjk` side-effect is bypassed on cache hit, producing different `ambiguity_register.json` (9 entries warm vs 99 entries cold) and `execution_log.json` hashes. TRA-013's within-HEAD invariant is preserved for cold-cache runs, but warm-cache runs produce different audit trails. This may be acceptable (the cache hit is a performance optimization, not a correctness concern), but it should be documented. If deemed unacceptable, the fix is to log unknown CJK tokens during `BUILD_GLOSSARY` (which always runs) rather than during `TRANSLATE_SEGMENT` (which is cache-bypassed).

**Recommended action:** Document in SKILL.md §8 that warm-cache runs produce different `ambiguity_register.json` content; defer code fix to Batch 6 if needed.

---

## Validation Plan

After each batch:
1. Run all 4 quality gates: `ruff format --check . && ruff check . && mypy --strict tra && pytest tests -q`
2. All gates must be green.
3. Test count should increase (new regression tests added).
4. Commit + optional push.

After all batches:
1. Re-run Track R6 baseline — confirm all R5 fixes hold.
2. Re-run Track E6 probes — confirm TRA-013 byte-reproducibility still holds (within HEAD).
3. Final commit + push.

---

## Effort Estimate

| Batch | Findings | Est. Hours |
|---|---|---|
| 1 (Doc refresh) | 9 | 1.5 |
| 2 (Spec-conformance partial-fixes) | 3 | 12 |
| 3 (Phase 8 sprint) | 3 | 24 |
| 4 (Test suite gaps) | 4 | 30 |
| 5 (Code quality) | 8 | 5 |
| **Total** | **27** | **72.5 hours (9 person-days)** |

Plus 22 positive verifications (no action needed — they confirm things are working).

The 19 INFO findings not assigned to a batch are either cosmetic (doc typos, minor wording) or are positive verifications already in the "Fixed" state. They can be addressed opportunistically during other batches.

---

## Priority Recommendation

1. **Batch 1 (Doc refresh) — DO FIRST.** 1.5 hours, 9 findings, no code changes. Closes the highest-density cluster and clears the audit-trail for future rounds.
2. **Batch 5 (Code quality) — DO SECOND.** 5 hours, 8 findings, low-risk code changes. Closes the type-safety residuals and ModuleInterface edge cases.
3. **Batch 2 (Spec-conformance partial-fixes) — DO THIRD.** 12 hours, 3 findings. The TRA-A5-013 factual-integrity check is the only spec-mandated check with NO implementation — high-value fix.
4. **Batch 4 (Test suite gaps) — DO FOURTH.** 30 hours, 4 findings. The benchmark 24→100+ expansion is the largest single effort.
5. **Batch 3 (Phase 8 sprint) — DO LAST.** 24 hours, 3 findings. The TRA-001 per-leaf refactor is the largest single code change and should be planned carefully.

Total: ~72.5 hours (9 person-days) of remediation effort.
