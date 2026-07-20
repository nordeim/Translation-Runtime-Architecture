# Track C6 Findings — Doc-vs-Code Consistency Audit (Round 6)

**Track:** C6 (doc-vs-code consistency)
**HEAD audited:** `c4ecd41` (Round 5 Batch I — Phase 7 documentation & delivery complete)
**Scope:** 12 documentation files (CLAUDE.md, README.md, AGENTS.md, status.md, implementation_plan.md, to_translate.md, tra-prototype/SKILL.md, tra-prototype/README.md, TRA-MODULE-AUTHORING.md, TRA-SPECIFICATION.md, TRA-ISA-REFERENCE.md, TRA-CONFORMANCE-GUIDE.md, TRA-BENCHMARK-SUITE.md, TRA-MODULE-ZH-EN.md)
**Methodology:** Each concrete claim (test count, file count, HEAD hash, status word, class count, Phase completion, finding status, code snippet) verified against the live codebase at HEAD `c4ecd41` via `pytest --collect-only`, `git rev-parse HEAD`, source-file reads, and grep verification.

---

## Verified codebase ground truth (at HEAD `c4ecd41`)

| Claim | Actual value | Verification |
|:--|:--|:--|
| HEAD hash | `c4ecd41` (full: `c4ecd4155d1baa0b4b5d6e60d2e9b1da217e8a46`) | `git rev-parse HEAD` |
| Test count (collected) | **309** (309 passed in 2.77s after `rm -rf cache/`) | `pytest tests/ --collect-only` → 309 items |
| Test file count | **16** `tests/test_*.py` files | `ls tests/test_*.py \| wc -l` |
| Benchmark case count | **36** (35 in `sft.jsonl` + 1 in `regression.jsonl`) | `wc -l tests/benchmark/cases/*.jsonl` |
| `test_outstanding_findings.py` test count | **161** | `pytest --collect-only -q` |
| `test_outstanding_findings.py` Test* class count | **71** | `pytest --collect-only \| awk -F'::' '{print $2}' \| sort -u \| grep "^Test" \| wc -l` |
| TRA-001 Phase 8 (per-leaf translation) | **Implemented** in `tra/kernel.py:521-667` + `tra/memory.py:144` (`iter_leaf_segments()`) | Batch H commit `f782043` |
| TRA-079 / TRA-B5-004 (cache HMAC) | **Implemented** in `tra/cache.py:34-50,134-145,164-168` | Batch E commit `57997a8` |
| TRA-094 / TRA-D5-011 (mutation testing) | **Implemented** — `mutmut>=3.0` in `pyproject.toml:26` + `[tool.mutmut]` at `:60` | Batch F commit `6056fc1` |
| Phase 7 (documentation & delivery) | **Complete** per HEAD commit `c4ecd41` message | `git log --oneline -1` |
| `LanguageModuleProtocol` in `tra/modules/base.py` | 7 methods + `name: str` + `kind: str` annotations | source read |

---

## Findings

### TRA-C6-001: CLAUDE.md "Phase 7 has not started" contradicts "Phase 7 COMPLETE" 14 lines later

- **Severity:** BLOCKING
- **Finding type:** issue (internal contradiction / stale claim)
- **Round 5 status:** new (residual from incomplete Batch I doc-refresh)
- **Location:** `CLAUDE.md:15` vs `CLAUDE.md:56`
- **Doc claim (line 15):** "**Phase 7 (documentation & delivery) has not started.** The full per-item state lives in `implementation_plan.md`; open items are 6.3.1 (structlog), 6.5.1 (asyncio parallelism), 6.5.2 (cross-run disk caching), and all of Phase 7."
- **Doc claim (line 56):** "**Phase 7 (documentation & delivery)** COMPLETE: `TRA-MODULE-AUTHORING.md` (TRA-100, R4 Batch 2), `docs/adr/README.md` (8 ADRs, R5 Batch I), `docs/api-reference.md` (10 public modules, R5 Batch I), `docs/conformance-self-audit.md` (L1–L4 checklist with code evidence + benchmark results, R5 Batch I), `docs/spec-cross-reference.md` (§1–§9 mapped to implementation, R5 Batch I). All implementation_plan.md Phase 7 items checked off."
- **Code reality:** HEAD commit `c4ecd41` is titled "docs(tra): Round 5 Batch I — Phase 7 documentation & delivery complete". `implementation_plan.md` Phase 7 items 7.1.1–7.2.4 are all checked off (lines 291–301). All five cited deliverable files exist.
- **Impact:** A reader landing on line 15 will believe Phase 7 is unbuilt and may re-do the work or block downstream tasks; the line-56 paragraph is correct but is 41 lines below the stale status banner.
- **Suggested fix:** Replace line 15's "**Phase 7 (documentation & delivery) has not started.**" with "**Phase 7 (documentation & delivery) is complete** (R5 Batch I, commit `c4ecd41`)." and drop "and all of Phase 7" from the open-items list (the remaining open items 6.3.1 / 6.5.1 / 6.5.2 are still correctly listed as open).

### TRA-C6-002: README.md "Phase 7 has not started" — stale, contradicts HEAD commit

- **Severity:** BLOCKING
- **Finding type:** issue (stale claim)
- **Round 5 status:** new (Batch I missed README.md)
- **Location:** `README.md:114`
- **Doc claim:** "Phases 0–6 are complete (foundation → Kernel/Policy orchestration → ZH-EN module → CLI + benchmark suite → hardening). Phase 7 (documentation & delivery) has not started. See `implementation_plan.md` for the item-by-item state and `CLAUDE.md` → 'Prototype engine status' for layout and run commands."
- **Code reality:** Phase 7 is complete per HEAD commit `c4ecd41` and per `implementation_plan.md` Phase 7 items all checked. The cross-referenced `CLAUDE.md` itself now contains the contradiction noted in TRA-C6-001.
- **Impact:** README is the most-visited doc — every new contributor reads this stale claim first.
- **Suggested fix:** Replace "Phase 7 (documentation & delivery) has not started." with "Phase 7 (documentation & delivery) is complete (R5 Batch I).".

### TRA-C6-003: tra-prototype/README.md multiple stale claims — Phase 7, TRA-001, A5-003, A5-013

- **Severity:** BLOCKING
- **Finding type:** issue (multiple stale claims + internal contradictions with CLAUDE.md)
- **Round 5 status:** carry-over from R5 TRA-C5-004/005/006/007 (partial); residual drift introduced by Batches E/F/G/H/I not back-filled here
- **Location:** `tra-prototype/README.md:3, 76-78, 84-85, 86-89, 97-109, 110-118`
- **Doc claims:**
  - Line 3: "A Phase 0–6 reference implementation of **TRA v1.0**" (should be Phase 0–7; Phase 7 is complete).
  - Lines 76-78: "Full per-leaf segment translation is still deferred." (TRA-001 Phase 8 was implemented in Batch H commit `f782043`; see `tra/kernel.py:521-667` walking `iter_leaf_segments()`.)
  - Lines 84-85: "**Phase 7** (ADRs, API reference, module authoring guide, conformance self-audit) has not started." (Phase 7 is complete per HEAD `c4ecd41`.)
  - Lines 86-89: "**TRANSLATE_SEGMENT** currently operates on the whole document rather than per leaf segment (TRA-001 partial); the kernel passes the full source to `translate_segment`." (Per-leaf translation was implemented in Batch H; CLAUDE.md:47 confirms.)
  - Lines 97-109 "Exception recovery" entry ends with "TRA-A5-003 partial" — but CLAUDE.md:49 says TRA-A5-003 was "fixed in round 5" (UnknownTerm now emits EXCEPTION_HANDLER audit record).
  - Lines 110-118 "Policy Engine" entry ends with "TRA-A5-013 partial (no factual-integrity check exists in `verify_output`)" — but CLAUDE.md:50 says TRA-A5-013 was "fixed in round 5 commit `36246bb`" with the factual-integrity check now implemented.
- **Code reality:** All four cited fixes (TRA-001 Phase 8, Phase 7, TRA-A5-003, TRA-A5-013) are present in the codebase at HEAD `c4ecd41`. The parallel `CLAUDE.md` "Known gaps" section was correctly refreshed in Batch I; the `tra-prototype/README.md` "Known gaps" section was not. This is the same root cause flagged by Round 5 Track C5 (TRA-C5-004/005/006/007) — the Batch I doc-refresh updated CLAUDE.md but missed tra-prototype/README.md.
- **Impact:** Two top-level docs (`CLAUDE.md` and `tra-prototype/README.md`) now describe the *exact opposite* state for 4 findings. A reader consulting tra-prototype/README.md will believe 4 fixes are still pending when they are in fact shipped.
- **Suggested fix:** Mirror the CLAUDE.md "Known gaps" refresh into tra-prototype/README.md:
  1. Line 3: "A Phase 0–7 reference implementation" (was 0–6).
  2. Lines 76-78: replace "Full per-leaf segment translation is still deferred." with the per-leaf translation paragraph from `CLAUDE.md:47`.
  3. Lines 84-89: delete the "Phase 7 has not started" and "TRANSLATE_SEGMENT currently operates on the whole document" entries (both superseded).
  4. Lines 97-109: remove "TRA-A5-003 partial" caveat; mark TRA-A5-003 as fixed (matches CLAUDE.md:49).
  5. Lines 110-118: remove "TRA-A5-013 partial (no factual-integrity check exists)" caveat; mark TRA-A5-013 as fixed (matches CLAUDE.md:50).
  6. Add a new "Cache integrity (TRA-079 fixed in round 5)" entry mirroring `CLAUDE.md:52` (currently absent from tra-prototype/README.md entirely).

### TRA-C6-004: SKILL.md §8 "Known limitations" — TRA-001 partial claim contradicts §8 remediation log

- **Severity:** BLOCKING
- **Finding type:** issue (internal contradiction)
- **Round 5 status:** new (residual from Batch H/I doc-refresh)
- **Location:** `tra-prototype/SKILL.md:310-311` vs `tra-prototype/SKILL.md:477-484`
- **Doc claim (line 310-311):** "**Rule-based fidelity, not fluency** — output is structurally correct and terminology-exact but may read awkwardly; the LLM seam is the intended fluency path and is caller-supplied via dependency injection (`TRAKernel.run(source, llm_translate=callback)` — TRA-D5-002 fixed in round 5). Code blocks (fenced and inline) are already protected from glossary substitution (TRA-001 partial); full per-leaf-segment translation is still deferred."
- **Doc claim (line 477-484):** "**Batch H** (latest commit): 2 findings — TRA-001 Phase 8 (per-leaf segment translation: `StructuralMap.iter_leaf_segments()` method added; `_execute_translation` refactored to walk leaf segments and call `translate_segment` per leaf; per-leaf inline-code protection; LLM path uses whole-doc translation for backward compat; +5 tests)…"
- **Code reality:** `tra/memory.py:144` defines `iter_leaf_segments()`. `tra/kernel.py:521-667` walks `ctx.structural_map.iter_leaf_segments()` and calls `translate_segment` per leaf. Batch H commit `f782043` is in HEAD ancestry. TRA-001 Phase 8 IS implemented.
- **Impact:** SKILL.md internally contradicts itself within 170 lines. The §8 "Known limitations" list is what users read first; the Batch H remediation log is what auditors read.
- **Suggested fix:** Replace "TRA-001 partial); full per-leaf-segment translation is still deferred." with "TRA-001 fixed in round 5 Phase 8); per-leaf segment translation is implemented via `StructuralMap.iter_leaf_segments()` (see §8 Batch H).".

### TRA-C6-005: SKILL.md "Remaining persistent findings" lists TRA-001 and TRA-079 as persistent — both were fixed in Round 5

- **Severity:** BLOCKING
- **Finding type:** issue (stale "persistent" label)
- **Round 5 status:** new (residual from Batch H/E doc-refresh)
- **Location:** `tra-prototype/SKILL.md:418-424`
- **Doc claim:** "**Remaining persistent findings** (not yet fixed): TRA-001 (partial, full per-leaf segment translation — Phase 8, ~16h, separate effort), TRA-040 (EXCEPTION_HANDLER/HALT_ERROR not KernelStates — intentional design decision pending spec change), TRA-079 (cache HMAC integrity — INFO, low priority), TRA-094 (mutation testing framework — INFO, deferred)."
- **Code reality:**
  - **TRA-001 Phase 8**: FIXED in Batch H commit `f782043` (per-leaf segment translation via `iter_leaf_segments()`). The same SKILL.md at line 477-484 documents this fix.
  - **TRA-079 / TRA-B5-004**: FIXED in Batch E commit `57997a8` (cache HMAC-SHA256 signing in `tra/cache.py:34-50,134-145,164-168`). The same SKILL.md at line 458 documents this fix under "Batch E".
  - **TRA-094 / TRA-D5-011**: FIXED in Batch F commit `6056fc1` (`mutmut` configured in `pyproject.toml`). SKILL.md §7 line 271-298 documents this fix.
  - **TRA-040**: documented-intentional (Batch H commit `f782043` added the KernelState docstring). This one is legitimately still "documented intentional", not "persistent".
- **Impact:** Three of the four "persistent" entries are in fact fixed and shipped. Auditors reading this paragraph will re-file these findings as regressions.
- **Suggested fix:** Replace the "Remaining persistent findings" paragraph with: "**Remaining open items**: TRA-040 (EXCEPTION_HANDLER/HALT_ERROR not KernelStates — documented as intentional design decision in `kernel.py:52-75` docstring, pending spec clarification). TRA-001 Phase 8, TRA-079/B5-004, and TRA-094/D5-011 were all fixed in Round 5 (see Batches E/F/H above)."

### TRA-C6-006: SKILL.md §8 "Phase 7 not started" contradicts HEAD commit and SKILL.md §8 Batch I log

- **Severity:** BLOCKING
- **Finding type:** issue (internal contradiction + stale claim)
- **Round 5 status:** new (Batch I doc-refresh missed §8 "Known limitations")
- **Location:** `tra-prototype/SKILL.md:320-321`
- **Doc claim:** "**Phase 7 (docs/delivery) not started** — see `implementation_plan.md` for the full per-item state."
- **Code reality:** HEAD commit `c4ecd41` is "docs(tra): Round 5 Batch I — Phase 7 documentation & delivery complete". `implementation_plan.md` Phase 7 items 7.1.1–7.2.4 all checked off. SKILL.md §8 itself (line 502-505) lists the Round 5 audit deliverables, which were generated as part of Phase 7.
- **Impact:** SKILL.md §8 "Known limitations" is the user-facing list of what's not done; "Phase 7 not started" is the most consequential single stale claim in the doc.
- **Suggested fix:** Replace "Phase 7 (docs/delivery) not started" with "Phase 7 (docs/delivery) complete — see `implementation_plan.md` §7 and `docs/adr/`, `docs/api-reference.md`, `docs/conformance-self-audit.md`, `docs/spec-cross-reference.md` (R5 Batch I, commit `c4ecd41`).".

### TRA-C6-007: SKILL.md §7 test-class list has phantom B4-009 entry and missing (×2) annotation on TRA-001

- **Severity:** WARNING
- **Finding type:** issue (list inaccuracy; count happens to be correct)
- **Round 5 status:** residual from TRA-C5-002 fix (count was corrected 40→71 but the list itself retains the phantom entry)
- **Location:** `tra-prototype/SKILL.md:255-263`
- **Doc claim:** "(71 test classes: TRA-001, 002, 004, …, 099, A4-011, A5-003, A5-005, A5-010, A5-013, A5-014, **B4-009**, B5-004, B5-009, B5-010, B5-011, B5-012, D5-002, D5-004/005, …)"
- **Code reality:**
  - `pytest tests/test_outstanding_findings.py --collect-only | awk -F'::' '{print $2}' | sort -u | grep "^Test" | wc -l` → **71** (count is correct).
  - The list cites **B4-009** as if a `TestTRA_B4_009_*` class existed, but no such class exists. The actual classes added by the B4-009 remediation are `TestTRA016CountBlockingGone`, `TestTRA017UnusedDepsGone`, `TestTRA026CacheExpireGone` — which the list *also* cites separately as TRA-016/017/026. So B4-009 is a phantom entry that double-counts work already attributed to TRA-016/017/026.
  - The list cites TRA-001 as a single entry, but there are **two** TRA-001 classes: `TestTRA001SegmentLevel` (line 657) and `TestTRA001_PerLeafSegmentTranslation` (line 5272, added in Batch H). The (×2) annotation is missing.
  - The two errors cancel out for the total: 1 phantom B4-009 + 1 missing TRA-001 split = net 0, so 71 still matches actual 71.
- **Impact:** A reader trying to find the regression test class for B4-009 will fail (no such class exists). A reader trying to find all TRA-001 tests will miss the second class. The count happens to be right, which masks the list inaccuracy.
- **Suggested fix:** Remove "B4-009" from the list (it is an umbrella finding ID, not a class). Change "TRA-001" to "TRA-001 (×2 — SegmentLevel, PerLeafSegmentTranslation)" mirroring the existing "038 (×4 — …)" annotation pattern. This brings the listed count to 71 (70 after removing B4-009 phantom, +1 after splitting TRA-001) — still 71 total, but now matching the actual class list item-by-item.

### TRA-C6-008: implementation_plan.md dependencies table pinned to stale HEAD `805a8f8`

- **Severity:** WARNING
- **Finding type:** issue (stale HEAD reference + missing mutmut)
- **Round 5 status:** carry-over; mutmut added in Batch F not back-filled here
- **Location:** `implementation_plan.md:367`
- **Doc claim:** "> **Updated at HEAD `805a8f8`** (Round 4 audit). The 6 unused dependencies (`litellm`, `structlog`, `pydantic-settings`, `mdit-py-plugins`, `black`, `pytest-asyncio`) were removed from `pyproject.toml` in Round 3 remediation commit `a3cd2c1` (TRA-017 fixed). The LLM seam is caller-supplied (never imports litellm) and tests are synchronous. Install footprint dropped from ~70 packages to ~15."
- **Code reality:**
  - The dependencies table that follows (lines 374-394) lists 7 runtime deps + 3 dev deps (pytest, ruff, mypy) — but **`mutmut` is missing**. `pyproject.toml:26` adds `mutmut>=3.0` as a dev dep (Batch F commit `6056fc1`).
  - The "Updated at HEAD `805a8f8`" timestamp is from Round 4. The dependencies table has not been refreshed since Round 4 even though mutmut was added in Round 5 Batch F.
  - The 6 unused-deps-removed claim is still accurate.
- **Impact:** A reader following the dependencies table will miss `mutmut` (used for mutation testing per SKILL.md §7). The stale "Updated at HEAD `805a8f8`" timestamp makes the table look current when it is not.
- **Suggested fix:** Update the table to include a `mutmut` row (`^3.0`, "Mutation testing (dev extra)", added in R5 Batch F). Change "Updated at HEAD `805a8f8` (Round 4 audit)" to "Updated at HEAD `c4ecd41` (Round 5 audit)" or "Updated through Round 5 Batch F".

### TRA-C6-009: README.md missing Round 5 audit reference

- **Severity:** WARNING
- **Finding type:** issue (missing cross-reference)
- **Round 5 status:** new (Batch I added Round 5 refs to AGENTS.md and SKILL.md but not README.md)
- **Location:** `README.md` (entire file)
- **Doc claim:** README.md has no mention of "Round 5" audit deliverables anywhere in the file. `grep -i "round 5\|round5\|r5" README.md` → no matches.
- **Code reality:** `docs/audit/round5/` exists with full deliverables (`TRA_Prototype_Audit_Report_r5.docx`, `TRA_audit_findings_register_r5.xlsx`, `TRA_audit_severity_heatmap_r5.png`, `master_findings_register_r5.json`, `remediation_plan_r5.md`, per-track findings). AGENTS.md:52 and SKILL.md:502-505 both reference Round 5; README.md does not.
- **Impact:** README.md is the entry-point doc; readers will not know Round 5 audit exists or that the latest HEAD incorporates Round 5 remediation.
- **Suggested fix:** Add a "Audit history" subsection or a line in the "Prototype Engine (`tra-prototype/`)" section pointing to `docs/audit/round5/` (and the prior rounds). Mirror the audit-deliverables table already in `AGENTS.md:46-52`.

### TRA-C6-010: to_translate.md (root) benchmark count "24" is stale — actual is 36

- **Severity:** WARNING
- **Finding type:** issue (stale number, but format is correct)
- **Round 5 status:** partially-fixed (the R4-era "100+ test cases" claim was corrected to the "current/target" format in some prior refresh, but the current count was not bumped from 24→36 after Batch B added +12 cases)
- **Location:** `to_translate.md:28` (repo root)
- **Doc claim:** "· 基准测试套件 (TRA-BENCHMARK-SUITE.md)：目前包含24个测试用例（spec目标为100+），覆盖Markdown结构、数值精度、术语一致性等。" (translates to: "Benchmark suite (TRA-BENCHMARK-SUITE.md): currently contains 24 test cases (spec target 100+), covering Markdown structure, numerical precision, terminology consistency, etc.")
- **Code reality:** `tests/benchmark/cases/sft.jsonl` has 35 lines + `regression.jsonl` has 1 line = **36** cases. Round 5 Batch B commit `e75997f` (TRA-D5-006) added +12 cases bringing the suite from 24 to 36. The to_translate.md "24" reflects the pre-Batch-B state.
- **Format compliance:** The doc correctly separates "current count" (24) from "target" (100+) per the R5 remediation plan option (b) "包含100+测试用例的目标". The format is right; only the number is stale. This is a milder issue than the `to_translate.en.md` / `to_translate_en.md` "Contains over 100 test cases" claim (tracked as TRA-C5-008 in R5 baseline), which still presents 100+ as the current count.
- **Impact:** Minor — the doc is a sample input for E2E tests, not an authoritative current-state doc. But the "24" is factually wrong by 12 cases.
- **Suggested fix:** Change "目前包含24个测试用例" to "目前包含36个测试用例". (Alternatively, accept the existing TRA-C5-008 remediation plan note: the file is a translation sample and the count claim is not load-bearing for the spec.)

### TRA-C6-011: status.md banner does not pin the latest HEAD hash

- **Severity:** INFO
- **Finding type:** issue (imprecise HEAD reference)
- **Round 5 status:** partially-fixed (R5 Batch D commit `f2a9bcd` refreshed the banner from `aae0bca`→`5476faf` and added the "309 across 16 test files" count; the banner has since been further generalized to "the latest HEAD" prose without a hash)
- **Location:** `status.md:1`
- **Doc claim:** "> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1` and references '103 pytest passing'. The actual test count at the latest HEAD is **309 across 16 test files** (see `tra-prototype/SKILL.md` §7 for current count)."
- **Code reality:** The banner says "the latest HEAD" in prose form but does not pin the hash. Current HEAD is `c4ecd41`. The frozen-commit reference `4d97aa1` is correct (status.md body is a frozen Phase 6 session log).
- **Impact:** Minimal — the banner explicitly directs readers to `SKILL.md §7` for current count and to `CLAUDE.md` for current status. The "latest HEAD" prose is sufficient given the redirect.
- **Suggested fix (optional):** Add the hash: "The actual test count at the latest HEAD (`c4ecd41`) is **309 across 16 test files**". This would need to be re-pinned on every HEAD advance, so the current "latest HEAD" prose may actually be more maintainable.

### TRA-C6-012: TRA-MODULE-AUTHORING.md Protocol snippet matches `base.py` semantically (positive verification)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (TRA-F5-013 in R5 noted snippet omitted `name`/`kind` annotations; the snippet was refreshed to include them — current snippet matches)
- **Location:** `TRA-MODULE-AUTHORING.md:27-44` vs `tra-prototype/tra/modules/base.py:14-56`
- **Doc snippet (`TRA-MODULE-AUTHORING.md:27-44`):**
  ```python
  from typing import Protocol, runtime_checkable

  @runtime_checkable
  class LanguageModuleProtocol(Protocol):
      # Module metadata (used by the registry for dispatch).
      name: str
      kind: str  # "language" | "domain" | "formatting"

      def get_glossary_mappings(self) -> dict[str, str]: ...
      def get_style_profile(self) -> object: ...
      def is_forbidden(self, source: str, target: str) -> bool: ...
      def get_forbidden_targets(self) -> dict[str, str]: ...
      def entity_type_hint(self, token: str) -> object | None: ...
      def apply_zh_rules(self, text: str) -> str: ...
      def apply_rules(self, source: str, direction: str) -> str: ...
  ```
- **Actual `base.py:14-56`:** Same decorator (`@runtime_checkable`), same class name, same `name: str` + `kind: str` annotations, same 7 methods in the same order with identical signatures. The actual file adds `from __future__ import annotations`, docstrings, and `...` bodies — all cosmetic differences that the doc snippet legitimately elides for readability.
- **Round 5 TRA-F5-013 closure:** The R5 finding noted the snippet "omits the `name`/`kind` annotations and uses simplified return types". The current snippet (post-R5-Batch-5 fix) includes both `name: str` and `kind: str` annotations and matches the actual return types (`object`, `object | None`, etc.). The fix is verified holding at HEAD `c4ecd41`.
- **Impact:** A new contributor copying the snippet will produce a structurally-valid `LanguageModuleProtocol` implementer.

### TRA-C6-013: CLAUDE.md "Known gaps" entries reflect current state (positive verification)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (TRA-C5-004/005/006/007 from R5 closed)
- **Location:** `CLAUDE.md:42-57`
- **Verified claims:**
  - Line 47: "TRA-001, fixed in round 5 Phase 8" — ✓ matches `tra/kernel.py:521-667` + `tra/memory.py:144`.
  - Line 48: "TRA-099 fixed in round 4" — ✓ matches `tra_cli.py` auto-builds registry + passes to `TRAKernel`.
  - Line 49: "TRA-A5-003 fixed in round 5" — ✓ matches `tra/isa.py:551-560` (`audit.append("EXCEPTION_HANDLER", "UNKNOWN_TERM", …)`).
  - Line 50: "TRA-A5-013 fixed in round 5 commit `36246bb`" — ✓ matches `tra/isa.py` factual-integrity check (version + ISO date tokens).
  - Line 51: "TRA-090 fixed in round 5; TRA-D5-002" — ✓ matches `TRAKernel.run(llm_translate=)` signature.
  - Line 52: "TRA-079 fixed in round 5" — ✓ matches `tra/cache.py:34-50,134-145,164-168` HMAC signing.
  - Line 53: "TRA-094 fixed in round 5; TRA-D5-011" — ✓ matches `pyproject.toml:26,60` (`mutmut>=3.0` + `[tool.mutmut]`).
  - Line 54: "TRA-E5-005 fixed in round 5" — ✓ matches `--force-unrecoverable` CLI flag.
  - Line 55: "TRA-017, FIXED in Round 3 remediation commit `a3cd2c1`" — ✓ matches `pyproject.toml` (no `structlog`/`litellm`/etc.).
  - Line 56: "Phase 7 (documentation & delivery) COMPLETE" — ✓ matches HEAD `c4ecd41` commit message + `implementation_plan.md` Phase 7 items all checked.
  - Line 57: "36 of 100+ spec target cases implemented" — ✓ matches `sft.jsonl` (35) + `regression.jsonl` (1) = 36.
- **Impact:** CLAUDE.md is the authoritative "where behavior lives" doc; its Known Gaps section accurately reflects the codebase. (Note: the stale line 15 status banner — TRA-C6-001 — sits above this correct section, which is why the contradiction is so visible.)

### TRA-C6-014: AGENTS.md test count + Round 5 reference are correct (positive verification)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (TRA-C5-001 + TRA-C5-012 from R5 closed)
- **Location:** `AGENTS.md:41, 52`
- **Verified claims:**
  - Line 41: "`tra-prototype/tests/` | 309 tests across 16 files" — ✓ matches `pytest --collect-only` (309 items) and `ls tests/test_*.py | wc -l` (16 files).
  - Line 52: "`docs/audit/round5/` | Round 5 | 68 findings (46 issues + 22 positive verifications; 0 BLOCKING / 7 WARNING / 39 INFO) + `remediation_plan_r5.md`" — ✓ matches `docs/audit/round5/` directory contents and `master_findings_register_r5.json` summary.
- **Impact:** AGENTS.md is correctly refreshed; no action needed.

### TRA-C6-015: SKILL.md §7 test count + benchmark count + class count are numerically correct (positive verification)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (TRA-C5-001 + TRA-C5-002 + TRA-C5-008 count portion from R5 closed)
- **Location:** `tra-prototype/SKILL.md:252-269`
- **Verified claims:**
  - Line 252-253: "The full suite is **309 tests** across 16 test files" — ✓ matches actual.
  - Line 255: "(71 test classes: …)" — ✓ count matches actual 71 classes (see TRA-C6-007 for list-level inaccuracy that does not affect the count).
  - Line 268: "12 tests: L3 pipeline, L4 forensics, byte-reproducibility" for `test_e2e_to_translate.py` — ✓ matches `pytest tests/test_e2e_to_translate.py --collect-only` (12 items).
  - Line 269: "L3 gate coverage (asserts zero `BLOCKING` across 36 S/F/T/D/E/R cases)" — ✓ matches `sft.jsonl` (35) + `regression.jsonl` (1) = 36 cases.
- **Impact:** The numerical claims in SKILL.md §7 are accurate. Only the itemized list (TRA-C6-007) has a residual inaccuracy.

### TRA-C6-016: implementation_plan.md Phase 7 items all checked off (positive verification)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (Phase 7 items completed by R5 Batch I commit `c4ecd41`)
- **Location:** `implementation_plan.md:287-301`
- **Verified claims:**
  - 7.1.1 [x] ADRs — ✓ `docs/adr/README.md` exists with 8 ADRs.
  - 7.1.2 [x] API reference — ✓ `docs/api-reference.md` exists, covers 10 public modules.
  - 7.1.3 [x] Module authoring guide — ✓ `TRA-MODULE-AUTHORING.md` exists (R4 Batch 2, TRA-100).
  - 7.1.4 [x] Conformance self-audit checklist — ✓ `docs/conformance-self-audit.md` exists.
  - 7.2.1 [x] Full benchmark suite — ✓ "36/36 cases passed, 0 BLOCKING, 0 WARNING" matches actual.
  - 7.2.2 [x] L3 certification criteria met — ✓ verified by `test_benchmark.py::test_l3_gate_zero_blocking_subset`.
  - 7.2.3 [x] Cross-reference §1-9 — ✓ `docs/spec-cross-reference.md` exists.
  - 7.2.4 [x] review-feedback risks addressed — ✓ all 5 risks mitigated.
- **Additional verification:** Line 346 annotation "TDD regression tests (71 classes, 161 tests)" — ✓ matches `pytest tests/test_outstanding_findings.py --collect-only` (161 items, 71 Test* classes).
- **Impact:** implementation_plan.md Phase 7 is fully and accurately checked off. The only residual in this file is the stale dependencies table HEAD reference (TRA-C6-008).

### TRA-C6-017: TRA-SPECIFICATION.md, TRA-ISA-REFERENCE.md, TRA-CONFORMANCE-GUIDE.md, TRA-MODULE-ZH-EN.md have no concrete test-count/HEAD claims to drift (positive verification)

- **Severity:** INFO
- **Finding type:** positive_verification
- **Round 5 status:** N/A (these are normative spec docs that intentionally don't reference HEAD or test counts)
- **Location:** `TRA-SPECIFICATION.md`, `TRA-ISA-REFERENCE.md`, `TRA-CONFORMANCE-GUIDE.md`, `TRA-MODULE-ZH-EN.md` (all four files)
- **Verification:** `grep -iE "HEAD|test count|309|228|16 test|36 benchmark|24 benchmark|100\+|5476faf|805a8f8|aae0bca|c4ecd41|round 5|round5"` across all four spec files → no concrete current-state claims that could drift.
- **TRA-BENCHMARK-SUITE.md:5:** "intended to grow toward 100+ cases" — ✓ correctly framed as the spec target (not a current-count claim). The 36 implemented cases live in `tests/benchmark/cases/*.jsonl`, not in the spec doc itself.
- **Impact:** The normative spec docs are insulated from codebase drift by design. No action needed.

---

## Summary table

| ID | Severity | Type | Round 5 status | Location | One-line description |
|:--|:--|:--|:--|:--|:--|
| TRA-C6-001 | BLOCKING | issue | new | `CLAUDE.md:15` | "Phase 7 has not started" contradicts line 56 "Phase 7 COMPLETE" |
| TRA-C6-002 | BLOCKING | issue | new | `README.md:114` | "Phase 7 has not started" — stale, contradicts HEAD `c4ecd41` |
| TRA-C6-003 | BLOCKING | issue | carry-over (TRA-C5-004/005/006/007 partial) | `tra-prototype/README.md:3,76-118` | 6 stale claims: Phase 7 not started, TRA-001 deferred, A5-003 partial, A5-013 partial, missing TRA-079 entry |
| TRA-C6-004 | BLOCKING | issue | new | `tra-prototype/SKILL.md:310-311` | "TRA-001 partial; full per-leaf-segment translation still deferred" contradicts SKILL.md:477-484 Batch H log |
| TRA-C6-005 | BLOCKING | issue | new | `tra-prototype/SKILL.md:418-424` | "Remaining persistent findings" lists TRA-001, TRA-079, TRA-094 as persistent — all 3 were fixed in R5 |
| TRA-C6-006 | BLOCKING | issue | new | `tra-prototype/SKILL.md:320-321` | "Phase 7 (docs/delivery) not started" — stale, contradicts HEAD `c4ecd41` and SKILL.md:502-505 |
| TRA-C6-007 | WARNING | issue | residual from TRA-C5-002 fix | `tra-prototype/SKILL.md:255-263` | §7 class list has phantom B4-009 entry + missing (×2) on TRA-001 (count 71 still correct) |
| TRA-C6-008 | WARNING | issue | carry-over; mutmut not back-filled | `implementation_plan.md:367` | Dependencies table pinned to stale HEAD `805a8f8`, missing `mutmut` dev dep |
| TRA-C6-009 | WARNING | issue | new | `README.md` (whole file) | No Round 5 audit reference (AGENTS.md and SKILL.md have it; README.md does not) |
| TRA-C6-010 | WARNING | issue | partially-fixed | `to_translate.md:28` | Benchmark count "24" is stale (actual 36); format is correct (current + target) |
| TRA-C6-011 | INFO | issue | partially-fixed | `status.md:1` | Banner says "latest HEAD" in prose but does not pin hash `c4ecd41` |
| TRA-C6-012 | INFO | positive_verification | fixed-and-verified (TRA-F5-013) | `TRA-MODULE-AUTHORING.md:27-44` | Protocol snippet matches `base.py` semantically (7 methods, `name`/`kind` annotations present) |
| TRA-C6-013 | INFO | positive_verification | fixed-and-verified (TRA-C5-004/005/006/007) | `CLAUDE.md:42-57` | Known gaps section reflects current state — all 10 cited fixes verified at HEAD |
| TRA-C6-014 | INFO | positive_verification | fixed-and-verified (TRA-C5-001/012) | `AGENTS.md:41,52` | Test count "309 across 16 files" + Round 5 audit reference both correct |
| TRA-C6-015 | INFO | positive_verification | fixed-and-verified (TRA-C5-001/002/008 count) | `tra-prototype/SKILL.md:252-269` | §7 numerical claims (309 tests, 16 files, 71 classes, 36 benchmark cases, 12 e2e tests) all correct |
| TRA-C6-016 | INFO | positive_verification | fixed-and-verified (R5 Batch I) | `implementation_plan.md:287-301,346` | Phase 7 items 7.1.1–7.2.4 all checked off; "71 classes, 161 tests" annotation matches actual |
| TRA-C6-017 | INFO | positive_verification | N/A (normative spec docs) | `TRA-{SPECIFICATION,ISA-REFERENCE,CONFORMANCE-GUIDE,MODULE-ZH-EN}.md` + `TRA-BENCHMARK-SUITE.md` | Normative spec docs have no concrete test-count/HEAD claims to drift; "100+" in TRA-BENCHMARK-SUITE.md:5 correctly framed as target |

---

## Counts

- **Total findings:** 17
- **By severity:**
  - BLOCKING: **6** (TRA-C6-001, 002, 003, 004, 005, 006)
  - WARNING: **4** (TRA-C6-007, 008, 009, 010)
  - INFO: **7** (TRA-C6-011, 012, 013, 014, 015, 016, 017)
- **By finding type:**
  - issue: **11** (TRA-C6-001 through 011)
  - positive_verification: **6** (TRA-C6-012 through 017)
- **By Round 5 status:**
  - new: 7 (TRA-C6-001, 002, 004, 005, 006, 009 + positive_verification TRA-C6-012)
  - carry-over / partial / residual: 4 (TRA-C6-003, 007, 008, 010, 011)
  - fixed-and-verified: 5 (TRA-C6-013, 014, 015, 016 + TRA-C6-012)
  - N/A (normative spec): 1 (TRA-C6-017)

---

## Root-cause analysis

The 6 BLOCKING findings share a single root cause: **Round 5 Batch I (commit `c4ecd41`, "Phase 7 documentation & delivery complete") refreshed CLAUDE.md's "Known gaps" section (lines 42-57) and added the Phase 7 deliverables list (line 56), but did NOT propagate the same refresh to:**

1. **CLAUDE.md:15** — the "Prototype engine status" banner at the top of the same file (TRA-C6-001).
2. **README.md:114** — the parallel "Status" subsection (TRA-C6-002).
3. **tra-prototype/README.md** "Known gaps" section (TRA-C6-003) — same pattern as R5 TRA-C5-004/005/006/007: CLAUDE.md was refreshed but tra-prototype/README.md was not.
4. **tra-prototype/SKILL.md §8 "Known limitations"** (TRA-C6-004, 006) — the "limitations" list and the "Phase 7 not started" line were not updated even though SKILL.md §8 "Round 5 remediation" log (lines 426-484) correctly documents Batches E/F/G/H/I.
5. **tra-prototype/SKILL.md §8 "Remaining persistent findings"** (TRA-C6-005) — the paragraph was not pruned after Batches E/F/H fixed 3 of its 4 entries.

This is the same "Batch I doc-refresh was incomplete" pattern flagged by Round 5 Track C5 (TRA-C5-004/005/006/007) for the Batch 1+2 code fixes. The R5 Batch I commit did the CLAUDE.md refresh but stopped short of propagating to the 4 sibling docs.

---

## Suggested remediation: Round 6 Batch C6 (single doc-refresh commit, ~30 minutes)

A single follow-up commit `docs(tra): Round 6 Batch C6 — close 6 stale doc-state claims` would resolve all 6 BLOCKING findings plus 3 of the 4 WARNING findings (TRA-C6-007, 008, 010) with no code changes:

1. `CLAUDE.md:15` — replace "Phase 7 has not started" with "Phase 7 complete (R5 Batch I, commit `c4ecd41`)"; drop "and all of Phase 7" from open-items list. (Closes TRA-C6-001.)
2. `README.md:114` — replace "Phase 7 (documentation & delivery) has not started." with "Phase 7 (documentation & delivery) is complete (R5 Batch I)."; add an "Audit history" line pointing to `docs/audit/round5/`. (Closes TRA-C6-002 + TRA-C6-009.)
3. `tra-prototype/README.md` — apply the 6 edits listed in TRA-C6-003 (mirror CLAUDE.md:42-57 Known gaps refresh). (Closes TRA-C6-003.)
4. `tra-prototype/SKILL.md:310-311` — replace "TRA-001 partial); full per-leaf-segment translation is still deferred." with "TRA-001 fixed in round 5 Phase 8); per-leaf segment translation is implemented via `StructuralMap.iter_leaf_segments()` (see §8 Batch H).". (Closes TRA-C6-004.)
5. `tra-prototype/SKILL.md:418-424` — replace the "Remaining persistent findings" paragraph with the corrected version in TRA-C6-005 (only TRA-040 remains as documented-intentional). (Closes TRA-C6-005.)
6. `tra-prototype/SKILL.md:320-321` — replace "Phase 7 (docs/delivery) not started" with "Phase 7 (docs/delivery) complete — see `implementation_plan.md` §7 and `docs/adr/`, `docs/api-reference.md`, `docs/conformance-self-audit.md`, `docs/spec-cross-reference.md` (R5 Batch I, commit `c4ecd41`).". (Closes TRA-C6-006.)
7. `tra-prototype/SKILL.md:255-263` — remove phantom "B4-009" entry; add "(×2 — SegmentLevel, PerLeafSegmentTranslation)" annotation to TRA-001. (Closes TRA-C6-007.)
8. `implementation_plan.md:367` — change "Updated at HEAD `805a8f8`" to "Updated at HEAD `c4ecd41`"; add a `mutmut` row to the dependencies table. (Closes TRA-C6-008.)
9. `to_translate.md:28` — change "目前包含24个测试用例" to "目前包含36个测试用例". (Closes TRA-C6-010.)

After this commit, all 6 BLOCKING findings and 3 WARNING findings close; the remaining WARNING (TRA-C6-009 if not addressed in step 2) and 2 INFO findings (TRA-C6-011 banner hash pinning; TRA-C6-007 list inaccuracy if step 7 is deferred) can be tracked separately or accepted as-is.

---

## End
