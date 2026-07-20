# Track C7 — Doc-vs-Code Consistency Re-Audit (Round 7)

**Task ID:** C7-1
**Auditor:** Track C7 (doc-vs-code consistency)
**HEAD audited:** `6d3144a` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/`
**Baseline:** Round 6 Track C6 (`docs/audit/round6/track_c6_findings.md`, 14 findings: 4 BLOCKING / 4 WARNING / 6 INFO)
**Methodology:** Cross-check every documentation claim against code at HEAD `6d3144a`. All claims verified by reading the cited `file:line`.

## Verification Run

- HEAD: `git rev-parse HEAD` → `6d3144a3fdaa8d90a8f5b5f3996af39e667ee496` ✓
- All R6 Batch 1 doc fixes verified landed in commit `6d3144a`

## Summary

- **Findings: 10 total (0 BLOCKING / 3 WARNING / 7 INFO + 5 positive verifications)**
- **0 regressions** from R6 baseline
- **All 4 R6 BLOCKING doc-staleness findings verified FIXED** (TRA-C6-001/002/006 + the C6-003/004/005/006 cluster)
- **3 new WARNING** doc-drift residuals identified at HEAD `6d3144a`

---

## Findings

### TRA-C7-001: implementation_plan.md dependencies table pinned to stale HEAD `805a8f8` (PERSISTENT WARNING, carry-over from C6-008)

- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / Stale HEAD Reference
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from C6-008; R6 Batch 1 did not touch implementation_plan.md's dependencies table)
- **Evidence:**
  - `implementation_plan.md:367` — `> **Updated at HEAD `805a8f8`** (Round 4 audit). The 6 unused dependencies...`
  - Actual HEAD: `6d3144a` (4 commits past `805a8f8`). The deps table content is still accurate (6 runtime + 4 dev deps), but the HEAD pin is stale.
  - `implementation_plan.md:374-394` — dependencies table content is correct (matches `tra-prototype/pyproject.toml:10-27` at HEAD `6d3144a`).
- **Detail:** The stale HEAD pin misleads readers into thinking the table might be out of date. The content is accurate; only the pin needs updating.
- **Suggested fix:** Replace `Updated at HEAD `805a8f8` (Round 4 audit)` with `Updated at HEAD `6d3144a` (Round 7 audit)`. The dependencies themselves have not changed since R3 remediation commit `a3cd2c1`.

### TRA-C7-002: README.md missing Round 5 and Round 6 audit references (PERSISTENT WARNING, carry-over from C6-009)

- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / Missing Audit Cross-Reference
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from C6-009; R6 Batch 1 did not touch README.md audit references)
- **Evidence:**
  - `README.md` — `rg -n "Round [0-9]" README.md` returns 0 hits. README.md does not mention ANY audit rounds.
  - `AGENTS.md:44-52` — has audit deliverables table mentioning Round 1-5.
  - `CLAUDE.md:59` — mentions Round 1-5 deliverables.
  - `docs/audit/round5/README.md` and `docs/audit/round6/README.md` exist but are not linked from the top-level README.md.
- **Detail:** README.md is the first file a new contributor reads. Missing audit cross-references force them to discover the audit history by browsing `docs/audit/`. R6 added Round 6 deliverables but README.md was not updated.
- **Suggested fix:** Add a "Audit History" section to README.md listing all 7 audit rounds (R1-R7) with one-line summaries and links to each round's README.

### TRA-C7-003: status.md banner does not pin the latest HEAD hash (PERSISTENT WARNING, carry-over from C6-011)

- **Severity:** WARNING
- **Category:** Doc-vs-Code Consistency / Stale Banner
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from C6-011)
- **Evidence:**
  - `status.md:1-3` — banner reads: `> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1` and references "103 pytest passing". The actual test count at the latest HEAD is **309 across 16 test files**...`
  - The banner mentions "309 across 16 test files" (correct at HEAD `6d3144a`) but does NOT pin the specific HEAD hash. A reader cannot tell whether "latest HEAD" means `6d3144a`, `c4ecd41`, or something earlier.
  - The banner also doesn't mention that Round 6 + Round 7 audits have occurred since the file was frozen.
- **Detail:** The status.md file is intentionally frozen (historical context only), but the banner that warns about its staleness should pin the current HEAD so readers know how stale "stale" is.
- **Suggested fix:** Update banner to: `> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1` and references "103 pytest passing". The actual state at HEAD `6d3144a` (Round 7 audit, 2026-07-21) is **309 tests across 16 test files** + L3 CONFORMANT. See `CLAUDE.md` → "Prototype engine status" for current state and `docs/audit/round7/` for the latest audit.`

### TRA-C7-004: SKILL.md §7 test-class list has phantom B4-009 entry and missing (×2) annotation on TRA-001 (PERSISTENT INFO, carry-over from C6-007)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / Test Inventory Accuracy
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from C6-007)
- **Evidence:**
  - `tra-prototype/SKILL.md:256-264` — test class list includes `B4-009` but `rg "B4-009|TestTRA_B4_009" tests/` returns 0 hits (the class was renamed/merged in R5).
  - `tra-prototype/SKILL.md:258` — `038 (×4 — UnknownTerm, CertaintyConflict, EntityAmbiguity, UnknownTermRaisedInProduction)` correctly notes the ×4 annotation, but `001` (line 256) is missing its `×2` annotation (`TestTRA_001_*` and `TestTRA_001_LeafSegmentTranslation_*`).
- **Detail:** Test inventory drift; cosmetic but misleading for anyone trying to map findings to tests.
- **Suggested fix:** Remove `B4-009` from the list. Add `001 (×2)` annotation. Regenerate the list from `rg "^class Test" tests/test_outstanding_findings.py` to ensure accuracy.

### TRA-C7-005: TRA-MODULE-AUTHORING.md §2.7 section header uses parameter name `source` while actual Protocol uses `text` (PERSISTENT INFO, carry-over from F6-009)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / Module Authoring Guide
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from F6-009)
- **Evidence:**
  - `TRA-MODULE-AUTHORING.md` §2.7 — section header references parameter name `source`.
  - `tra/modules/base.py` `LanguageModuleProtocol` — actual parameter name is `text`.
  - `TRA-MODULE-AUTHORING.md` §1 — snippet uses `text` (correct).
- **Detail:** Cosmetic drift between §1 and §2.7 of the same document. Confusing for module authors.
- **Suggested fix:** Rename §2.7 section header parameter from `source` to `text` to match §1 and the Protocol.

### TRA-C7-006: CLAUDE.md "Phase 7 has not started" claim FIXED — line 15 now reads "Phases 0-7 are complete" (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / R6 Batch 1 Fix Verification
- **Finding type:** positive_verification
- **Round 6 status:** fixed-verified (TRA-C6-001 fixed in commit `6d3144a`)
- **Evidence:**
  - `CLAUDE.md:15` — "Phases 0–7 are complete — foundation (Phase 0), structural parsing/anchor resolution (Phase 1)..."
  - Matches `CLAUDE.md:56` "Phase 7 (documentation & delivery) COMPLETE".
  - No internal contradiction.

### TRA-C7-007: README.md "Phase 7 has not started" claim FIXED — line 114 now reads "Phases 0-7 are complete" (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / R6 Batch 1 Fix Verification
- **Finding type:** positive_verification
- **Round 6 status:** fixed-verified (TRA-C6-002 fixed in commit `6d3144a`)
- **Evidence:**
  - `README.md:114` — "Phases 0–7 are complete (foundation → Kernel/Policy orchestration → ZH-EN module → CLI + benchmark suite → hardening → documentation & delivery)."
  - Matches HEAD `6d3144a` state.

### TRA-C7-008: SKILL.md "Known limitations" + "Remaining persistent findings" sections updated to reflect HEAD `6d3144a` (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / R6 Batch 1 Fix Verification
- **Finding type:** positive_verification
- **Round 6 status:** fixed-verified (TRA-C6-003/004/005/006 fixed in commit `6d3144a`)
- **Evidence:**
  - `tra-prototype/SKILL.md:303-326` — "Known limitations" section now correctly states:
    - TRA-001 FIXED (Phase 8 per-leaf translation, Batch H)
    - TRA-079 FIXED (cache HMAC, Batch E)
    - TRA-094 FIXED (mutmut, Batch F)
    - Phase 7 COMPLETE (Batch I)
  - `tra-prototype/SKILL.md:423-427` — "Remaining persistent findings" section now correctly states only TRA-040 (intentional design decision) as persistent.

### TRA-C7-009: to_translate.md benchmark count "24" → "36" FIXED (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / R6 Batch 1 Fix Verification
- **Finding type:** positive_verification
- **Round 6 status:** fixed-verified (TRA-C6-010 fixed in commit `6d3144a`)
- **Evidence:**
  - `to_translate.md` — now states "目前包含36个测试用例" (currently contains 36 test cases).
  - Matches `tests/benchmark/cases/*.jsonl` count at HEAD `6d3144a`.

### TRA-C7-010: AGENTS.md test count + Round 5 reference are correct (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Doc-vs-Code Consistency / AGENTS.md Accuracy
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-C6-014 re-confirmed)
- **Evidence:**
  - `AGENTS.md:41` — "309 tests across 16 files" — matches `pytest tests/` output at HEAD `6d3144a`.
  - `AGENTS.md:52` — Round 5 audit deliverables table entry is accurate.
  - Note: AGENTS.md does NOT yet reference Round 6 or Round 7 audits (see TRA-C7-002 for the README.md equivalent; AGENTS.md should also be updated).

---

## Conclusion

- **0 BLOCKING** findings at HEAD `6d3144a` ✓ (all 4 R6 BLOCKING doc-staleness findings verified fixed)
- **3 WARNING** findings persistent (TRA-C7-001/002/003) — addressed in `remediation_plan_r7.md`
- **2 INFO** findings persistent (TRA-C7-004/005) — addressed opportunistically
- **5 positive verifications** re-confirmed
- **0 regressions** from R6 baseline ✓
