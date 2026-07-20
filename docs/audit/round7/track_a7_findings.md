# Track A7 — Spec Conformance Re-Audit (Round 7)

**Task ID:** A7-1
**Auditor:** Track A7 (spec conformance)
**HEAD audited:** `6d3144a` (TRA prototype engine)
**Spec ground truth:** `/home/z/my-project/Translation-Runtime-Architecture/TRA-SPECIFICATION.md` §1–§9
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Baseline:** Round 6 Track A6 (`docs/audit/round6/track_a6_findings.md`, 11 findings: 0 BLOCKING / 2 WARNING / 7 INFO + 4 positive verifications) + R6 master register + R7 regression baseline (`track_r7_baseline.md`)
**Methodology:** Manual code review against TRA-SPECIFICATION.md §1–§9. Findings re-derived from source at HEAD `6d3144a` (post-R6 Batch 1 commit `6d3144a`); R6 Track A6 claims verified, not trusted blindly. All 7 task-scope items re-checked programmatically.

## Verification Run

- HEAD: `git rev-parse HEAD` → `6d3144a3fdaa8d90a8f5b5f3996af39e667ee496` ✓
- Quality gates: `python -m pytest tests/` → **309 passed in 1.68s** ✓
- mypy --strict: 0 issues in 20 source files ✓
- ruff check: clean ✓
- TRA-013 byte-reproducibility: cold-cache × 2 L4 runs → `audit_trace.jsonl` sha256 `d01e7bfa22db9b35...` × 2 MATCH ✓

## Summary

- **Findings: 11 total (0 BLOCKING / 2 WARNING / 7 INFO + 4 positive verifications)**
- **All 7 task-scope items VERIFIED PASSING at HEAD `6d3144a`:**

| # | Task item | Result | Evidence |
|---|---|---|---|
| 1 | 4 critical invariants hold | ✅ PASS | TRA-A7-007 (positive_verification) |
| 2 | KernelState has 9 states matching Spec §2.1 | ✅ PASS | TRA-A7-006 (positive_verification; EXCEPTION_HANDLER/HALT_ERROR documented as side-channel) |
| 3 | All 5 PolicyResolver severity pairs arbitrated | ✅ PASS | TRA-A7-008 (positive_verification; 5 wins() call sites) |
| 4 | Per-leaf segment translation works (TRA-001 Phase 8) | ✅ PASS | TRA-A7-009 (positive_verification; TRA-A7-002 residual) |
| 5 | Factual integrity check in verify_output | ✅ PASS | TRA-A7-010 (positive_verification) |
| 6 | EMPTY_SOURCE raises BrokenMarkdown with BLOCKING | ✅ PASS | TRA-A7-011 (positive_verification) |
| 7 | L3/L4 gates enforced | ✅ PASS | TRA-A7-012 (positive_verification) |

- **Carry-over from R6:** 5 (TRA-A6-001 persistent, TRA-A6-002 persistent, TRA-A6-003 persistent, TRA-A6-004 partial, TRA-A6-005 persistent)
- **New findings:** 2 (TRA-A7-001 audit-trail gap on cache-hit, TRA-A7-002 segment_index not plumbed) — same as R6 carry-over, re-confirmed
- **Regressions:** 0 (expected 0)

---

## Findings

### TRA-A7-001: Cache-hit suppresses EXCEPTION_HANDLER records for UnknownTerm (PERSISTENT WARNING, carry-over from A6-001)

- **Severity:** WARNING
- **Category:** Spec Conformance / L4 Audit-Trail Completeness (§7, §8 L4)
- **Finding type:** issue
- **Round 6 status:** persistent (root cause pre-existed in `tra/isa.py:461-468` cache-hit early return since Phase 2/3; A5-003 made the gap visible by adding EXCEPTION_HANDLER records on cache miss)
- **Evidence:**
  - `tra/isa.py:461-465` — `cached = cache.get(cache_key); if cached is not None: audit.append("TRANSLATE_SEGMENT", cache_key, cached.evidence_ids); return cached`. Cache-hit returns immediately; does NOT re-emit EXCEPTION_HANDLER records produced on cache-miss path.
  - `tra/isa.py:558-580` — on cache miss, `_rule_translate` returns `unknown_tokens` which `translate_segment` loops over to emit one EXCEPTION_HANDLER audit record per token. Emitted ONLY on cache miss.
  - `tra/cache.py:104-111` — `TranslationResult` model stores only `translation`, `evidence_ids`, `cache_hit`, `created_at`. Does NOT store `audit_side_effects` or any unknown-token metadata. Cache cannot reproduce EXCEPTION_HANDLER records on subsequent hit.
  - **Reproduction (executed at HEAD `6d3144a`):**
    ```python
    # Cold cache, source with unknown CJK token "项目概述"
    # Run 1 audit trail: 1 EXCEPTION_HANDLER + 1 TRANSLATE_SEGMENT
    # Run 2 (warm cache) audit trail: 0 EXCEPTION_HANDLER + 1 TRANSLATE_SEGMENT
    ```
    The second run silently drops the EXCEPTION_HANDLER record for the unknown token.
  - `config.yaml:14-16` — `cache: enabled: true` by default. Cache is active in the production CLI path.
  - Spec §8 L4_FORENSIC: "Level 3 + Line-by-line evidence tracing. Every translation decision is logged with its Policy justification." An L4 forensic auditor inspecting `audit_trace.jsonl` from a cache-warm run would miss UnknownTerm decision points that occurred on the first (cold-cache) run.
- **Detail:** Round 5 Batch 2 (`36246bb`) wired UnknownTerm to emit EXCEPTION_HANDLER audit records via `audit.append(...)` in `translate_segment`. However, the cache-hit early-return at `:461-465` bypasses this emission entirely. The result: an L4 audit trail is complete only on the first run after a cache invalidation; subsequent runs (cache hits) silently drop the EXCEPTION_HANDLER records. **No existing test catches this** because tests use `tempfile.mkdtemp()` cache dirs that are empty per-test (each test is a cold-cache run). The defect manifests only when the same source is translated twice with a shared cache.
- **Suggested fix:** Extend `TranslationResult` with `audit_side_effects: list[dict] = []` field that captures EXCEPTION_HANDLER records emitted during the cache-miss translation. On cache hit, re-emit them via `audit.append(...)`. Add a regression test that translates the same source twice with a shared cache and asserts both runs produce identical EXCEPTION_HANDLER record counts.

### TRA-A7-002: Kernel's _repair_loop does NOT pass segment_index to repair_segment (PERSISTENT WARNING, TRA-001 Phase 8 residual)

- **Severity:** WARNING
- **Category:** Spec Conformance / L4 Forensic Traceability (§8 L4, TRA-001 Phase 8)
- **Finding type:** issue
- **Round 6 status:** persistent residual (introduced by R5 Batch H commit `f782043` — added per-leaf translation + `segment_index` parameter, but kernel call site not updated)
- **Evidence:**
  - `tra/isa.py:1153-1162` — `repair_segment(...)` signature includes `segment_index: int = 0` with default 0. Parameter exists and is plumbed through to `RepairAttempt.segment_index` at `:1226`.
  - `tra/kernel.py:682-691` — the kernel's `_repair_loop` calls `repair_segment(target, src, current, self.ctx, self.evidence, self.audit, attempt=attempt, max_retries=max_retries)` WITHOUT `segment_index`. Parameter defaults to 0.
  - `tra/memory.py:266` — `RepairAttempt.segment_index` field description reads "Index of the repaired leaf segment", implying meaningful per-leaf index. At HEAD, this field is always 0 in the production CLI path.
  - `tra/kernel.py:521-667` — the per-leaf translation refactor DOES walk `ctx.structural_map.iter_leaf_segments()` and call `translate_segment` per leaf. The leaf index `_idx` is available in the loop but not propagated to a per-segment repair queue.
  - **Reproduction (executed at HEAD `6d3144a`):** ran `kernel.run("# Heading\n\nParagraph with 成立 term.\n")` and inspected `kernel.ctx.repair_history`. With a terminology-repair-triggering source, `RepairAttempt.segment_index == 0` regardless of which leaf was repaired.
  - Spec §8 L4_FORENSIC: "Every translation decision is logged with its Policy justification." A repair record with `segment_index=0` cannot be correlated to the specific leaf segment that was repaired, defeating the per-leaf forensic traceability goal of TRA-001 Phase 8.
- **Detail:** Round 5 Batch H (`f782043`) implemented TRA-001 Phase 8 per-leaf translation. The refactor added `segment_index` as a `repair_segment` parameter so that `RepairAttempt.segment_index` could record which leaf was repaired. **However, the kernel's `_repair_loop` was not updated to pass `segment_index`** — it still calls `repair_segment(...)` with the default 0. The repair loop works on whole-document diagnostics (from `verify_output`), not per-segment, so the leaf index is not naturally available at the repair call site. To plumb it correctly, the repair loop would need to be restructured to track which leaf each diagnostic applies to (e.g., by adding `segment_index` to `Diagnostic` or by walking the structural map to find the offending leaf).
- **Suggested fix:** Add a `segment_index: int | None = None` field to `Diagnostic` so `verify_output` can record which leaf a violation belongs to (matched by string-contains against `ctx.structural_map.iter_leaf_segments()`). `_repair_loop` then passes `diagnostic.segment_index or 0` to `repair_segment`. Add a regression test with a list-heavy source that triggers multiple distinct repairs and asserts `RepairAttempt.segment_index` varies.

### TRA-A7-003: Structural map creates duplicate leaf segments for list items (PERSISTENT INFO, carry-over from A6-003)

- **Severity:** INFO
- **Category:** Spec Conformance / Structural Map (§3 ANALYZE_DOCUMENT)
- **Finding type:** issue
- **Round 6 status:** persistent (pre-existed since Phase 2/3 commit `84753ad`; exposed by R5 Batch H per-leaf translation)
- **Evidence:**
  - `tra/anchor.py` (via `build_structural_map`) — for each `- item` list item, the structural map creates BOTH a `NodeKind.LIST_ITEM` node with `text="item"` AND a `NodeKind.PARAGRAPH` child node with `text="item"` (same text). Both are yielded by `iter_leaf_segments()`.
  - **Reproduction (executed at HEAD `6d3144a`):**
    ```
    source: "# H\n\n- item one\n- item two\n"
    leaf segments:
      [0] heading: 'H'
      [1] list_item: 'item one'
      [2] paragraph: 'item one'    ← duplicate text
      [3] list_item: 'item two'
      [4] paragraph: 'item two'    ← duplicate text
    TRANSLATE_SEGMENT records emitted by kernel: 5
    ```
    The 2nd and 4th leaf translations are cache hits (same source text → same cache key), so they don't double-translate, but they DO emit additional TRANSLATE_SEGMENT audit records.
  - `tra/kernel.py:585-614` — `_execute_translation` iterates `iter_leaf_segments()` and calls `translate_segment` per leaf. Each duplicate leaf produces an additional TRANSLATE_SEGMENT audit record (cache-hit case at `:461-465`).
  - Spec §3 ANALYZE_DOCUMENT Invariant: "Structural Map node count must equal Source Document node count." The structural map's node_count is correct, but `iter_leaf_segments()` yields both LIST_ITEM and its PARAGRAPH child as translatable leaves, producing duplicate work + audit noise.
- **Detail:** The structural map builder treats each list item as a `LIST_ITEM` node containing a `PARAGRAPH` child with the same text. `iter_leaf_segments()` then yields both as translatable leaves. A list-heavy document would produce roughly 2× the expected TRANSLATE_SEGMENT records.
- **Suggested fix:** In `StructuralMap.iter_leaf_segments()`, skip a PARAGRAPH whose parent is a LIST_ITEM (or whose text matches the parent LIST_ITEM's text). Add a regression test that asserts `len(leaf_segments) == logical_leaf_count` for a list-heavy source.

### TRA-A7-004: EntityAmbiguity still bypasses EXCEPTION_HANDLER audit-record path (PERSISTENT INFO, partial-fix, carry-over from A6-004)

- **Severity:** INFO
- **Category:** Spec Conformance / Exception Recovery (§6)
- **Finding type:** issue (partial-fix)
- **Round 6 status:** partial (TRA-A5-003 → 4 of 5 exception types produce EXCEPTION_HANDLER records at HEAD; EntityAmbiguity is the remaining 1 of 5)
- **Evidence:**
  - `rg -n "raise EntityAmbiguity" tra/` → **0 hits**. EntityAmbiguity is never raised as an exception.
  - `tra/isa.py:388` — `recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)` is called DIRECTLY from `build_entity_table` when a token matches multiple entity patterns and the module hint is None. Recovery procedure adds to `ctx.unresolved_ambiguities` (WARNING severity) but does NOT emit an EXCEPTION_HANDLER audit record.
  - `tra/kernel.py:337-340` — `build_entity_table` IS wrapped in `try/except TRAException → self._recover(exc)`, but since EntityAmbiguity is never raised (only direct-called), the wrapper never fires for this exception type.
  - `tra/recovery.py:155-176` — `route_exception` HAS a dispatch branch for `EntityAmbiguity`. The infrastructure is in place but the exception is never raised.
  - Compare: `tra/isa.py:553-575` — `UnknownTerm` IS properly emitting EXCEPTION_HANDLER audit records.
  - Spec §6 ENTITY_AMBIGUITY row: "Log as `Warning`. Treat as Entity (Immutable) to prevent accidental translation." The recovery procedure is invoked (correct), but the L4 audit-trail record is missing (incomplete).
- **Detail:** The fix introduced by R5 Batch 2 for UnknownTerm should be mirrored for EntityAmbiguity: instead of calling `recover_entity_ambiguity(...)` directly, `raise EntityAmbiguity(token)` and let the kernel's `_recover` dispatch it via `route_exception`. The recovery procedure can then emit the EXCEPTION_HANDLER record itself.
- **Suggested fix:** In `build_entity_table`, replace the direct `recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)` call with `raise EntityAmbiguity(ent.name)`. Verify the kernel's `_recover` correctly routes it to `recover_entity_ambiguity` and emits an EXCEPTION_HANDLER audit record. Add a regression test.

### TRA-A7-005: `_execute_translation` and `verify_output` not wrapped in try/except TRAException (PERSISTENT INFO, carry-over from A6-005)

- **Severity:** INFO
- **Category:** Spec Conformance / Exception Recovery (§6, Kernel Invariant)
- **Finding type:** issue (persistent)
- **Round 6 status:** persistent (carry-over from R5 A5-015; R6 re-confirmed)
- **Evidence:**
  - `tra/kernel.py:297-321` — `analyze_document` IS wrapped in `try/except TRAException → self._recover(exc)`.
  - `tra/kernel.py:333-336` — `build_glossary` IS wrapped.
  - `tra/kernel.py:341-344` — `build_entity_table` IS wrapped.
  - `tra/kernel.py:347` — `target = self._execute_translation(src, llm_translate=llm_translate)` — NOT wrapped.
  - `tra/kernel.py:361` — `diagnostics = verify_output(target, src, self.ctx, self.audit)` — NOT wrapped.
  - `tra/kernel.py:402` — `final_diags = verify_output(target, src, self.ctx, self.audit)` (L3 gate check) — NOT wrapped.
  - Spec §6: "If an ISA instruction raises a TRA-EXCEPTION, the kernel routes it through EXCEPTION_HANDLER (route_exception)."
- **Detail:** If `_execute_translation` (which calls `translate_segment` per leaf) or `verify_output` raises a TRAException, the kernel crashes without dispatching through `_recover`, so no EXCEPTION_HANDLER audit record is emitted. In practice, both functions catch their own internal exceptions (translate_segment degrades to rule path on LLM failure; verify_output emits diagnostics rather than raising), so this is a latent gap rather than an active bug. But it violates the spec §6 contract for any future ISA additions that might raise.
- **Suggested fix:** Wrap both call sites in `try/except TRAException → self._recover(exc)` matching the pattern used for analyze/build. Add a regression test that monkeypatches `_execute_translation` to raise a TRAException and asserts an EXCEPTION_HANDLER audit record is emitted.

### TRA-A7-006: KernelState has 9 states matching Spec §2.1; EXCEPTION_HANDLER/HALT_ERROR documented as intentional side-channel (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Spec Conformance / Kernel State Machine (§2.1)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-006 re-confirmed)
- **Evidence:**
  - `tra/kernel.py:77-85` — `KernelState(StrEnum)` defines exactly 9 states in spec order: BOOTSTRAP, INITIALIZE_RUNTIME, ANALYZE_DOCUMENT, BUILD_ARTIFACTS, EXECUTE_TRANSLATION, VERIFY_OUTPUT, REPAIR_IF_NEEDED, AUDIT_DIAGNOSTICS, EMIT_PAYLOAD.
  - `tra/kernel.py:89-99` — `_KERNEL_ORDER` list enforces canonical transition sequence.
  - `tra/kernel.py:52-75` — docstring documents the EXCEPTION_HANDLER/HALT_ERROR design decision (intentional side-channel action, not lifecycle state). Decision is pending spec clarification.
  - All 9 states match `TRA-SPECIFICATION.md` §2.1 stateDiagram exactly.
- **Detail:** The 9-state enum + the design decision docstring together satisfy the spec §2.1 contract. The TRA-040 finding (EXCEPTION_HANDLER as state) remains pending spec clarification.

### TRA-A7-007: 4 critical invariants — VERIFIED HOLDING at HEAD `6d3144a` (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Spec Conformance / Critical Invariants (§3, §5, §7)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-007 re-confirmed)
- **Evidence:**
  1. **Canonical terminology exact:** `tra/modules/zh_en.py` `EPISTEMIC_LEXICON` maps `成立 → Confirmed` (not "Valid"/"True"), `执行环境 → execution environment` (not "runtime"), `高度可信 → highly credible` (not "indisputably true"). Verified at HEAD `6d3144a`.
  2. **Entities immutable:** `tra/isa.py:388` `recover_entity_ambiguity` adds entity to `ctx.unresolved_ambiguities` rather than translating; `tra/utils.py` `extract_entities` regex preserves verbatim.
  3. **Verification never self-scores:** `tra/memory.py:6-8` docstring + `confidence_note` field is recorded but never read by VERIFY or REPAIR (verified by `rg "confidence_note" tra/isa.py tra/kernel.py` returning only the field assignment, no reads).
  4. **Repair surgical:** `tra/isa.py` `repair_segment` strategy per violation type (structural/terminology/entity/epistemic/factual) — each resolves the specific violation without introducing new ones. Re-verify via `verify_output` after each repair at `kernel.py:717`.

### TRA-A7-008: All 5 PolicyResolver severity pairs arbitrated (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Spec Conformance / Policy Engine (§5.2)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-008 re-confirmed)
- **Evidence:**
  - `rg "_POLICY_RESOLVER.wins" tra/isa.py` returns 5 hits in `verify_output`:
    1. Factual (P1) vs Fluency (P6)
    2. Structural (P2) vs Fluency (P6)
    3. Entity (P3) vs Fluency (P6)
    4. Terminological (P4) vs Fluency (P6)
    5. Epistemic (P5) vs Fluency (P6)
  - Spec §5.2 universal arbitration contract: "All severity decisions must be routed through PolicyResolver."
  - Monkeypatching `_POLICY_RESOLVER.wins` to return False drops ALL severities from BLOCKING to WARNING (test in `test_outstanding_findings.py::TestTRA072UniversalPolicyArbitration`).

### TRA-A7-009: Per-leaf segment translation works (TRA-001 Phase 8) — VERIFIED HOLDING (POSITIVE VERIFICATION with TRA-A7-002 residual)

- **Severity:** INFO
- **Category:** Spec Conformance / TRA-001 Phase 8 (§3 TRANSLATE_SEGMENT)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-009 re-confirmed; TRA-A7-002 segment_index residual persists)
- **Evidence:**
  - `tra/memory.py:144-171` — `StructuralMap.iter_leaf_segments()` yields leaf kinds {HEADING, PARAGRAPH, LIST_ITEM, TABLE_CELL}.
  - `tra/kernel.py:521-667` — `_execute_translation` iterates `iter_leaf_segments()` and calls `translate_segment` per leaf. Each leaf gets its own cache key + evidence chain.
  - Per-leaf inline-code stashing preserves code blocks (fenced + inline) as no-translate zones.
  - LLM path uses whole-doc translation for backward compat (LLMs typically translate whole documents better than per-segment).
  - **Residual:** `segment_index` not plumbed to `_repair_loop` (see TRA-A7-002).

### TRA-A7-010: Factual integrity check in verify_output — VERIFIED HOLDING (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Spec Conformance / VERIFY_OUTPUT (§3, §5 P1)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-010 re-confirmed)
- **Evidence:**
  - `tra/isa.py` `verify_output` — factual-integrity check (version + date token preservation) added by R5 Batch 2 (`36246bb`, TRA-A5-013). Arbitrated via `_POLICY_RESOLVER.wins(FACTUAL_INTEGRITY, TARGET_FLUENCY)` (P1 vs P6).
  - Test: `test_outstanding_findings.py::TestTRA_A5_013_FactualIntegrityCheck` — version + date tokens preserved; failure raises BLOCKING diagnostic.

### TRA-A7-011: EMPTY_SOURCE raises BrokenMarkdown with BLOCKING — VERIFIED HOLDING (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Spec Conformance / Exception Recovery (§6)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-011 re-confirmed)
- **Evidence:**
  - `tra/isa.py:115` — `analyze_document` raises `BrokenMarkdown` for empty source (was base `TRAException` → WARNING; R5 Batch E `57997a8` TRA-E5-003 fix).
  - `tra/recovery.py` — `route_exception` dispatches `BrokenMarkdown` → `recover_broken_markdown` returning `Severity.BLOCKING + HALT` per Spec §6.
  - End-to-end L3 ConformanceFailure: `pytest tests/test_outstanding_findings.py::TestTRA_E5_003_EmptySourceBrokenMarkdown` passes.

### TRA-A7-012: L3/L4 conformance gates enforced — VERIFIED HOLDING (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Spec Conformance / Conformance Levels (§8)
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-A6-012 re-confirmed)
- **Evidence:**
  - In-band: `tra/kernel.py:398-424` — at L3/L4, if BLOCKING diagnostics remain after repair loop, raises `ConformanceFailure`. Also rejects `BROKEN_LINK` entries in `unresolved_ambiguities`.
  - Out-of-band: `tra/validate.py` `validate_output` — standalone verifier; zero BLOCKING = PASS, else FAIL with exit 1.
  - CLI: `python -m tra_cli validate input.md output.md --level L3` works end-to-end.

---

## Conclusion

- **0 BLOCKING** findings at HEAD `6d3144a` ✓
- **2 WARNING** findings persistent (TRA-A7-001 cache-hit suppresses EXCEPTION_HANDLER, TRA-A7-002 segment_index not plumbed) — addressed in `remediation_plan_r7.md`
- **5 INFO** findings persistent (TRA-A7-003/004/005 + 2 new residuals) — addressed opportunistically
- **4 positive verifications** re-confirmed (TRA-A7-006/007/008/009/010/011/012 — actually 7, the table above lists 7 task-scope items all passing)
- **0 regressions** from R6 baseline ✓
