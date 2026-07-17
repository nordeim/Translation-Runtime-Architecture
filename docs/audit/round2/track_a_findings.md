# Track A — Spec Conformance Re-Audit Findings

**Auditor:** Track A2 agent
**HEAD audited:** 4b8827c
**Spec ground truth:** TRA-SPECIFICATION.md §1-§9, TRA-ISA-REFERENCE.md

## Summary

- Total findings: 11
- BLOCKING: 0
- WARNING: 7
- INFO: 4
- Carry-over from Round 1: 4 persistent/partial (A-4, A-6, A-16/A-21, A-23-partial); 6 confirmed fixed (A-3, A-7, A-13-partial, A-15, A-17-partial, A-22)
- New findings: 7 (TRA-A2-005, -006, -007, -008, -009, -010, -011)

The 4 critical invariants all hold at HEAD: (1) canonical terminology exact, (2) entities immutable, (3) verification never self-scores, (4) repair surgical. The L3 gate is enforced in-band (kernel.py:248-261) and the forward-only transition guard is correct (kernel.py:173-183). All 141 tests pass.

The findings below are conformance gaps where the implementation deviates from the spec text. None are BLOCKING because the 4 critical invariants hold and the L3 gate functions for the happy path; the gaps are in edge cases (exception recovery, post-rewrite audit integrity, policy arbitration wiring).

## Findings

### TRA-A2-001 — PolicyResolver is scaffolding: never invoked in production code
- **Severity:** WARNING
- **Category:** Spec Conformance / Policy Engine (§5.2)
- **Carry-over or new:** Carry-over A-16 / A-21 (TRA-006 half-fix confirmed persistent)
- **Evidence:** `tra/policy.py:13-25` (PolicyResolver defined); `tra/isa.py:499-515` (verify_output hard-codes severity by GlossaryStatus, no resolver call); grep `PolicyResolver` in `tra/` returns 0 production imports (only `tests/test_phase0.py:23`, `tests/test_outstanding_findings.py:302`).
- **Detail:** The Track R baseline recorded TRA-006 as STATIC-PASS with note "HALF-FIX: severity classification is policy-aware but PolicyResolver.resolve() never invoked in verify_output." Re-verification confirms: `verify_output` (isa.py:499-515) hard-codes `severity = Severity.BLOCKING if entry.status == GlossaryStatus.CANONICAL else Severity.WARNING`. The comment claims "TRA-009 + TRA-006: severity is policy-driven" but no `PolicyResolver` is imported or called. The 6-priority stack (`PolicyPriority` in memory.py:19-30) is referenced ONLY in `cache.py:55,65` for cache-key hashing and in `isa.py:640-641` (`_policy_stack` returns `DEFAULT_POLICY_STACK` fed into the cache key). The test `test_policy_resolver_invoked_in_verify_output` (test_outstanding_findings.py:298-310) is misleadingly named — it only instantiates `PolicyResolver` in isolation and never verifies production invocation. Spec §5.2 mandates "Compare priorities in Stack. Higher priority wins" via the Policy Engine; the implementation achieves the terminology severity by accident (hard-coded CANONICAL→BLOCKING) rather than by arbitration.
- **Suggested fix:** Import `PolicyResolver` in `isa.py`, instantiate it once with `DEFAULT_POLICY_STACK`, and call `resolver.resolve(PolicyPriority.TERMINOLOGICAL_CONSISTENCY, PolicyPriority.TARGET_FLUENCY)` to compute the severity for canonical-term leakage. Add a negative test that monkeypatches `PolicyResolver.resolve` to return `TARGET_FLUENCY` and asserts the diagnostic drops to WARNING (proving the resolver is actually consulted).

### TRA-A2-002 — 3 of 5 TRA-EXCEPTION types are never raised in production
- **Severity:** WARNING
- **Category:** Spec Conformance / Exception Recovery (§6)
- **Carry-over or new:** Carry-over A-23 (TRA-004 partial fix)
- **Evidence:** grep `raise (UnknownTerm|CertaintyConflict|EntityAmbiguity)` in `tra/` returns 0 hits. Only `BrokenMarkdown` (isa.py:95), `GlossaryConflict` (isa.py:187,193), `Unrecoverable` (isa.py:591,603), and `ConformanceFailure` (kernel.py:256) are raised. Recovery procedures `recover_unknown_term` (recovery.py:76-86), `recover_certainty_conflict` (recovery.py:111-121), `recover_entity_ambiguity` (recovery.py:124-134) are defined but unreachable.
- **Detail:** The TRA-004 fix wrapped `analyze_document` in try/except (kernel.py:205-214) so `BrokenMarkdown` now routes through `_recover`. However, the other 3 spec-mandated exceptions remain dead. `build_entity_table` (isa.py:256-307) silently treats ambiguous tokens as entities via `extract_entities` (utils.py) without ever raising `EntityAmbiguity` — the spec §6 default ("Treat as Entity") is matched in behavior but the §6 recovery procedure (recovery.py:124-134) is never invoked, so no audit record or ambiguity-register entry is produced. `translate_segment`'s rule path never tracks unknown CJK terms, so `UnknownTerm` is never raised. No code path compares LLM output against `EPISTEMIC_LEXICON` to raise `CertaintyConflict`. Spec §6 mandates deterministic recovery for all 5 types.
- **Suggested fix:** Raise `EntityAmbiguity` from `build_entity_table` when the classifier confidence is low (or when a token matches both entity and glossary patterns); raise `UnknownTerm` from `_rule_translate` when a CJK token has no glossary/entity/epistemic match; raise `CertaintyConflict` from `translate_segment` when an LLM returns a target that disagrees with `EPISTEMIC_LEXICON`. Route all through the existing `_recover` path.

### TRA-A2-003 — `build_entity_table` is not wrapped in try/except (latent crash)
- **Severity:** WARNING
- **Category:** Spec Conformance / Exception Recovery (§6, §3 BUILD_ENTITY_TABLE)
- **Carry-over or new:** Carry-over A-4 (persistent)
- **Evidence:** `tra/kernel.py:226-231`: `build_glossary` is wrapped in `try/except TRAException → self._recover(exc)`, but `build_entity_table` at line 230 is called with NO try/except. Spec §3 BUILD_ENTITY_TABLE Failure Condition: `ENTITY_AMBIGUITY`.
- **Detail:** If `build_entity_table` ever raises `EntityAmbiguity` (e.g., after the TRA-A2-002 fix adds the raise), the kernel would crash with an unhandled exception — no EXCEPTION_HANDLER audit record, no graceful return. Currently `build_entity_table` (isa.py:256-307) never raises, so the gap is latent. The asymmetry with `build_glossary` (which IS wrapped) suggests the wrapper was added for the glossary case only and the entity case was overlooked. The spec §6 ENTITY_AMBIGUITY recovery ("Treat as Entity") should be routed through `_recover` for audit-trail completeness.
- **Suggested fix:** Wrap `build_entity_table` (kernel.py:230) in the same `try/except TRAException → self._recover(exc)` pattern as `build_glossary`. Add a regression test that monkeypatches `build_entity_table` to raise `EntityAmbiguity` and asserts an EXCEPTION_HANDLER audit record is produced.

### TRA-A2-004 — EXCEPTION_HANDLER is not modeled as a KernelState; HALT_ERROR absent
- **Severity:** WARNING
- **Category:** Spec Conformance / Kernel State Machine (§2.1)
- **Carry-over or new:** Carry-over A-6 (persistent)
- **Evidence:** `tra/kernel.py:49-60` (`KernelState` enum has 9 states; EXCEPTION_HANDLER and HALT_ERROR absent). `tra/kernel.py:335-355` (`_recover` is a private method, not a state transition). Spec §2.1 stateDiagram: `VERIFY_OUTPUT --> EXCEPTION_HANDLER : On Failure`, `EXCEPTION_HANDLER --> REPAIR_IF_NEEDED`, `EXCEPTION_HANDLER --> HALT_ERROR : Unrecoverable`.
- **Detail:** The spec stateDiagram models EXCEPTION_HANDLER as a distinct state with two outgoing edges. The implementation treats `_recover` as a side-channel method that appends an `EXCEPTION_HANDLER` audit record (kernel.py:344-355) but does NOT transition the kernel state. After `_recover`, the kernel either (a) returns `""` early (analyze failure, kernel.py:214) — no transition to HALT_ERROR, (b) continues to the next ISA (build_glossary failure, kernel.py:230-231) — no transition to REPAIR_IF_NEEDED, or (c) breaks out of the repair loop (Unrecoverable, kernel.py:429-447) — no transition to HALT_ERROR. The `execution_log` (memory.py:199) never records an EXCEPTION_HANDLER visit. HALT_ERROR is not modeled at all. This means the Mermaid state diagram rendered by `reporting.mermaid_state_diagram` (reporting.py:50-70) from `execution_log` cannot reproduce the spec's EXCEPTION_HANDLER branch.
- **Suggested fix:** Add `EXCEPTION_HANDLER` and `HALT_ERROR` to `KernelState`. Transition to `EXCEPTION_HANDLER` before calling `_recover`, then transition to `REPAIR_IF_NEEDED` (recoverable) or `HALT_ERROR` (unrecoverable) based on the `RecoveryReport.action`. Update `_KERNEL_ORDER` to include the new states in their spec-mandated positions.

### TRA-A2-005 — Analyze-failure early return bypasses the L3 conformance gate
- **Severity:** WARNING
- **Category:** Spec Conformance / L3 Gate (§8)
- **Carry-over or new:** New (introduced by TRA-004 remediation)
- **Evidence:** `tra/kernel.py:205-214`: on `analyze_document` raising `TRAException`, the kernel calls `self._recover(exc)`, `self.audit.flush()`, and `return ""` at line 214 — BEFORE the L3 gate at lines 248-261. The comment at line 212 claims "the caller's L3 gate will reject it" but there is no caller-side L3 gate; the kernel's own gate is bypassed by the early return.
- **Detail:** For L3_STRICT and L4_FORENSIC runs, a malformed source (triggering `BrokenMarkdown`) produces an empty target `""` with no `ConformanceFailure` raised. The CLI (`tra_cli.py translate`) receives `""` and would print it as the translation — a silent conformance failure. The L3 gate at kernel.py:248-261 is never reached because the early return at line 214 precedes it. `verify_output("")` would return BLOCKING for every entity and glossary term (empty target contains none), so the gate WOULD catch it if reached — but it isn't. The existing test `test_broken_markdown_routes_through_exception_handler` (test_outstanding_findings.py:324-359) uses `ConformanceLevel.L1_BASIC` (line 344), so it doesn't exercise the L3 bypass.
- **Suggested fix:** Replace the `return ""` at kernel.py:214 with `raise ConformanceFailure(f"BROKEN_MARKDOWN: analyze_document failed — output is not L3-conformant", blocking_count=1)` when `self.config.conformance_level in (L3_STRICT, L4_FORENSIC)`. Add a regression test at L3_STRICT that patches `analyze_document` to raise `BrokenMarkdown` and asserts `ConformanceFailure` is raised.

### TRA-A2-006 — `_rewrite_anchors` runs after the L3 gate; audit trail hashes pre-rewrite target
- **Severity:** WARNING
- **Category:** Spec Conformance / L3 Gate + L4 Forensics (§8, §6.4)
- **Carry-over or new:** New (introduced by TRA-008 remediation)
- **Evidence:** `tra/kernel.py:248-261` (L3 gate runs `verify_output(target, ...)` on pre-rewrite target); `tra/kernel.py:263` (transition to AUDIT_DIAGNOSTICS); `tra/kernel.py:264` (`audit.flush()` commits the audit trail); `tra/kernel.py:270` (`target = self._rewrite_anchors(target)` mutates target AFTER audit flush); `tra/kernel.py:274` (`_export_forensics(target)` uses post-rewrite target); `tra/kernel.py:275` (`return target` returns post-rewrite target). `tra/kernel.py:331-332` (`_rewrite_anchors` appends `BROKEN_LINK` entries to `self.ctx.unresolved_ambiguities`).
- **Detail:** Two conformance gaps: (1) The L3 gate at line 252 calls `verify_output(target, ...)` on the PRE-rewrite target, but the emitted/returned target (line 275) is POST-rewrite. The audit record appended by `verify_output` (isa.py:532-537) hashes the pre-rewrite target, so the audit trail's `input_hash` does not match the emitted target's hash — breaking L4 forensic hash-chain integrity. (2) `_rewrite_anchors` appends `BROKEN_LINK: #{slug}` entries to `unresolved_ambiguities` (kernel.py:332) when a link target has no matching heading, but the L3 gate (kernel.py:248-261) only checks `verify_output`'s BLOCKING diagnostics — it never inspects `unresolved_ambiguities`. A run with broken internal links passes L3 silently. The spec §8 L3 requires "Full TRA compliance... Diagnostic Reporting" and §6.4 L4 requires "Line-by-line evidence tracing" — both are compromised when the audited target differs from the emitted target.
- **Suggested fix:** Move `_rewrite_anchors` to BEFORE the L3 gate (between line 240 and line 248), so the gate verifies the post-rewrite target. Add a check in the L3 gate: `if self.ctx.unresolved_ambiguities: raise ConformanceFailure(...)` for L3+ when unresolved_ambiguities is non-empty (or at least when it contains `BROKEN_LINK` entries). Add a regression test with a source containing a link to a non-existent heading at L3_STRICT and assert `ConformanceFailure` is raised.

### TRA-A2-007 — GLOSSARY_CONFLICT recovery claims USE_FIRST_OCCURRENCE but does not set the canonical mapping
- **Severity:** WARNING
- **Category:** Spec Conformance / Exception Recovery (§6 GLOSSARY_CONFLICT)
- **Carry-over or new:** New (refinement of A-23)
- **Evidence:** `tra/recovery.py:137-151` (`recover_glossary_conflict` returns a `RecoveryReport` with `action=RecoveryAction.USE_FIRST_OCCURRENCE` but does NOT mutate `ctx.glossary_cache`); `tra/isa.py:168-226` (`build_glossary` raises `GlossaryConflict` at line 187 or 193 BEFORE reaching `ctx.glossary_cache = entries` at line 219, so the cache remains the default empty list); `tra/kernel.py:226-231` (kernel catches the exception, calls `_recover`, then continues to `build_entity_table` and transitions to `BUILD_ARTIFACTS` with an empty glossary).
- **Detail:** Spec §6 GLOSSARY_CONFLICT recovery: "Log as Blocking Error. Use first occurrence as canonical. Flag subsequent occurrences for manual review." The implementation logs the error and flags for review (via `unresolved_ambiguities`), but does NOT set the first occurrence as canonical — `ctx.glossary_cache` remains empty `[]` because `build_glossary` raised before populating it. The kernel continues with an empty glossary, so `translate_segment`'s rule path has no terminology substitutions, and `verify_output`'s terminology check (isa.py:501-515) iterates an empty list — no BLOCKING diagnostics. The L3 gate passes silently despite the glossary being missing. The `RecoveryReport.action = USE_FIRST_OCCURRENCE` is a label only, not an enforced action.
- **Suggested fix:** In `build_glossary`, when a conflict is detected on a duplicate source term, keep the first-seen mapping and continue (rather than raising immediately), then raise `GlossaryConflict` with `canonical_target=seen[src]` after the loop. Alternatively, in `_recover`, after routing the exception, populate `ctx.glossary_cache` with the first-occurrence mapping from the `GlossaryConflict.canonical_target` attribute. Add a regression test that forces a conflict and asserts the glossary_cache is non-empty and the L3 gate catches downstream terminology issues.

### TRA-A2-008 — Dead no-op code in `_rule_translate` entity-preservation loop
- **Severity:** INFO
- **Category:** Code Quality / Misleading Dead Code
- **Carry-over or new:** New
- **Evidence:** `tra/isa.py:438-442`:
  ```python
  # 4. Entities inserted verbatim (already source form; no-op preserve).
  for ent in entities:
      # Ensure casing preserved exactly; nothing to transform.
      if ent.name not in out and ent.name in segment:
          out = out  # entities already present verbatim
  ```
- **Detail:** The loop body `out = out` is a no-op assignment. The condition `ent.name not in out and ent.name in segment` checks whether an entity is MISSING from the output but present in the source — the exact scenario where corrective action (re-insertion) would be needed. The comment "Ensure casing preserved exactly; nothing to transform" is contradictory: if the entity is missing, casing is NOT preserved. The branch is entered only if the rule layer (apply_zh_rules + EPISTEMIC_LEXICON + glossary substitution) accidentally removed an entity, which doesn't happen in practice (entities like "RustVMM" don't overlap glossary keys). Downstream `verify_output` (isa.py:482-492) catches missing entities as BLOCKING, so the gap is defense-in-depth, not a live bug. A maintainer reading this code would mistakenly believe entity preservation is enforced here.
- **Suggested fix:** Either remove the loop entirely (the comment "already source form; no-op preserve" suggests the author intended a no-op) or implement actual re-insertion: `out = out.replace(ent.name, ent.name)` is still a no-op; a meaningful implementation would track entity positions before substitution and restore them after. At minimum, delete the misleading "Ensure casing preserved" comment.

### TRA-A2-009 — `CONCLUSION_LEADING` constant defined but never consumed
- **Severity:** INFO
- **Category:** Code Quality / Dead Code
- **Carry-over or new:** New
- **Evidence:** `tra/modules/zh_en.py:75` defines `CONCLUSION_LEADING: tuple[str, ...] = ("因此", "所以", "故", "由此可见", "综上")` with a docstring at lines 72-74 explaining its purpose ("information-order: conclusion-leading markers... the conclusion is surfaced first"). grep `CONCLUSION_LEADING` across `tra-prototype/` returns only the definition site — no consumer in `apply_zh_rules`, `apply_en_rules`, `apply_rules`, or any other production code.
- **Detail:** The constant and its docstring describe an unimplemented rule layer (conclusion-leading reordering for ZH→EN readability). The rule is never applied. This is dead code with an aspirational docstring. Round 1 did not flag this.
- **Suggested fix:** Either implement the conclusion-leading reordering in `apply_zh_rules` (surface the conclusion clause first when a clause ends with one of these markers) or remove the constant and its docstring to avoid implying the feature exists.

### TRA-A2-010 — `_deterministic_clock` seed is set in `run()`, not `__init__` (latent misuse risk)
- **Severity:** INFO
- **Category:** Code Quality / API Design
- **Carry-over or new:** New
- **Evidence:** `tra/kernel.py:117` (`self._source_hash_seed: str | None = None` in `__init__`); `tra/kernel.py:118-119` (`AuditTrail` constructed with `clock=self._deterministic_clock` BEFORE the seed is set); `tra/kernel.py:157-171` (`_deterministic_clock` reads `self._source_hash_seed or "0" * 16` — falls back to all-zeros when seed is None); `tra/kernel.py:193-196` (seed is set from `hashlib.sha256(src)` only inside `run()`).
- **Detail:** The clock callback is bound in `__init__` but reads `self._source_hash_seed`, which is `None` until `run()` is called. If any code calls `kernel.audit.append(...)` before `kernel.run(source)` (e.g., a test or external integration that logs a pre-run event), the clock falls back to `"0" * 16`, producing a deterministic-but-wrong timestamp (all such records share the same fallback timestamp, not the source-derived one). The docstring at line 158 says "All audit records in a single run share the same timestamp" — accurate for the intended usage but fragile if the API is used out of order. No production code triggers this; the risk is latent.
- **Suggested fix:** Either (a) require the source as a constructor argument and compute the seed in `__init__` (breaking API change), or (b) document the constraint in the `AuditTrail.clock` parameter docstring, or (c) raise `RuntimeError("call run() before appending to audit")` in `_deterministic_clock` when `self._source_hash_seed is None` to fail fast on misuse.

### TRA-A2-011 — Structural integrity verification is heading-count-only (carry-over from A-17)
- **Severity:** INFO
- **Category:** Spec Conformance / Policy Structural Integrity (§5.1 item 2)
- **Carry-over or new:** Carry-over A-17 (partial; TRA-008 fixed the rewrite_links half)
- **Evidence:** `tra/isa.py:466-479` (`verify_output` structural check: only `_HEADING_RE.findall` count match). No checks for: list nesting depth (S-01), table column alignment (S-02), blockquote preservation (S-04), HR preservation (S-05 — incidentally preserved by the rule layer which never touches `---`).
- **Detail:** Round 1 A-17 flagged two issues: (1) `rewrite_links` was defined but never called, and (2) structural verification was heading-count-only. TRA-008 fixed (1) — `rewrite_links` is now called from `_rewrite_anchors` (kernel.py:330). Issue (2) persists: `verify_output` only checks heading count. A translation that flattened nested lists, broke table alignment, or dropped blockquotes would pass the structural check as long as the heading count matches. The benchmark suite (sft.jsonl S-01, S-02, S-04) catches these via `must_contain` substring checks, but that's a test-harness gate, not a `verify_output` gate. Spec §5.1 item 2 "Structural Integrity: Markdown syntax, code blocks, table alignment" is partially enforced.
- **Suggested fix:** In `verify_output`, add structural checks that walk `ctx.structural_map` and assert each node kind (list, list_item, table, table_row, blockquote, hr) has a corresponding structural element in the target. At minimum, count list items, table rows, and blockquotes in source vs. target and raise BLOCKING on mismatch.
