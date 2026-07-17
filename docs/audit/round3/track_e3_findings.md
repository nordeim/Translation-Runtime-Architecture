# Track E3 — Forensic L4 End-to-End Re-Verification (Round 3)

**HEAD audited:** `b783745`
**Methodology:** L4 happy-path + 7 deliberate-failure probes + byte-reproducibility + audit-trail state-sequence + evidence-trace orphan inspection
**Baseline:** Round 2 Track E (12 findings; 2 BLOCKING / 4 WARNING / 6 INFO)
**Auditor:** Track E3 agent
**Audit date:** 2026-07-15

## Summary

- Findings: **14 total** (1 BLOCKING / 2 WARNING / 11 INFO)
- L4 happy-path: **PASS** (exit 0, all 9 runtime artifacts present)
- Byte-reproducibility: **BYTE-IDENTICAL** (TRA-013 still remediated)
- Probes: **6/7 passed** (Probe 4 — UnknownTerm — FAIL; TRA-038 PERSISTENT)
- Round 2 escalations: **1** (TRA-E-006 false-positive BROKEN_LINK now BLOCKS publication via TRA-037 gate fix)
- Round 2 fixes confirmed end-to-end: **4** (TRA-036, TRA-037×2 aspects, TRA-071)

## L4 happy-path run

- Command (isolated config to avoid concurrent-test pollution of project-root `audit_trace.jsonl`):
  ```
  python -m tra_cli --config /tmp/e3_work/config.yaml translate examples/security_advisory_zh.md --level L4 -o /tmp/e3_out.md
  ```
  (Config: `base_dir=/tmp/e3_work`, `compilation_dir=/tmp/e3_work/compilation_artifacts`, `audit_trace=/tmp/e3_work/audit_trace.jsonl`.)
- Exit code: **0**
- Output size: 360 bytes
- Canonical substitutions present: YES
  - `成立 → Confirmed` (in "may Confirmed under heavy load")
  - `执行环境 → execution environment` (in "The execution environment must")
  - `高度可信 → highly credible` (in "the highly credible configuration")
- All 9 runtime artifacts present: **YES**
  - `compilation_artifacts/glossary.yaml` (1296 B)
  - `compilation_artifacts/entity_table.yaml` (438 B)
  - `compilation_artifacts/structural_map.json` (1528 B)
  - `compilation_artifacts/style_profile.yaml` (260 B)
  - `compilation_artifacts/execution_log.json` (249 B)
  - `compilation_artifacts/repair_history.jsonl` (0 B — clean run, no repairs)
  - `compilation_artifacts/evidence_trace.jsonl` (974 B, L4-only)
  - `compilation_artifacts/ambiguity_register.json` (2 B = `[]`, L4-only)
  - `audit_trace.jsonl` (1540 B, 6 records — L3+ double VERIFY_OUTPUT expected)

## Audit trail state sequence

- `audit_trace.jsonl` records (ISA instructions, 6 lines):
  ```
  seq=0  ANALYZE_DOCUMENT        hash=f194c2c708adc307  flags=None
  seq=1  BUILD_GLOSSARY          hash=f194c2c708adc307  flags=None
  seq=2  BUILD_ENTITY_TABLE      hash=f194c2c708adc307  flags=None
  seq=3  TRANSLATE_SEGMENT       hash=5a664c2f34c79fa4fd236b954afcb363fd555a84fcc14c165a5edc021c51f0e9  flags=None
  seq=4  VERIFY_OUTPUT           hash=225d5eded0c4a252  flags=None
  seq=5  VERIFY_OUTPUT           hash=225d5eded0c4a252  flags=None
  ```
- `execution_log.json` state-transition sequence:
  ```
  INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD
  ```
- Matches `_KERNEL_ORDER` (`tra/kernel.py:64-74`):
  ```
  BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD
  ```
  (BOOTSTRAP is the initial state, not a transition — not recorded in `execution_log`.)
- Verdict: **PASS** (8 post-BOOTSTRAP states present in correct order; no gaps, no duplicates, no out-of-order transitions; forward-only transition guard respected).
- Caveat: the second `VERIFY_OUTPUT` (seq=5) is from the L3 gate (`kernel.py:291`), not a state duplicate. The `execution_log` records only one VERIFY_OUTPUT state transition. The double record is an ISA-level artifact (TRA-E-010 carry-over, see TRA-E3-014).

## Evidence trace inspection

- `compilation_artifacts/evidence_trace.jsonl` (6 lines):
  | line | text | evidence_ids | attributed |
  |---|---|---|---|
  | 1 | `# Security Advisory SA-2024-001` | 1 | True |
  | 3 | `RustVMM v0.5.0 may Confirmed under heavy load. The execution environment must` | 5 | True |
  | 4 | `accurately describe the highly credible configuration so operators can verify.` | 2 | True |
  | 6 | `We should support for the KVM and XFS backends by P99. The` | 4 | True |
  | **7** | `96-core system keeps memory below <5MB at peak.` | **0** | **False** ← **ORPHAN** |
  | 9 | `> Note: may configurations are not recommended in production.` | 1 | True |
- Verdict: **ORPHAN LINE PERSISTS** (TRA-E-001 / TRA-001 consequence). Line 7 has `evidence_ids: []` and `attributed: false` because the substring-containment heuristic in `reporting.py:73-95` cannot match any evidence record's `target_span` to a line containing only numbers and English text (no translated glossary terms). See TRA-E3-001.

## Probe results

| # | Probe | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | Forbidden epistemic drift (`成立`) | "Valid" absent, "Confirmed" present | "Valid" absent (0 matches), "Confirmed" present (1 match); exit 0; rule path substitutes `成立 → Confirmed` directly, no repair needed | **PASS** |
| 2 | Unclosed fence (TRA-071 — should be FIXED) | `ConformanceFailure`, exit 1, BROKEN_MARKDOWN raised | `CONFORMANCE FAILURE — BROKEN_MARKDOWN: analyze_document failed (BROKEN_MARKDOWN)`; exit 1; no output file; EXCEPTION_HANDLER audit record with BLOCKING flag | **PASS** (TRA-071 FIXED) |
| 3 | Empty source (TRA-036 — should be FIXED) | `ConformanceFailure`, exit 1 | `CONFORMANCE FAILURE — BROKEN_MARKDOWN: analyze_document failed (TRA_ERROR)`; exit 1; no output file; EXCEPTION_HANDLER audit record with WARNING flag (severity classification nuance — see TRA-E3-004) | **PASS** (behavioral; TRA-036 FIXED) |
| 4 | Unknown CJK term (TRA-038 — still PERSISTENT) | `UnknownTerm` exception raised and routed | exit 0; "未知术语" passes through untranslated; no EXCEPTION_HANDLER record; `unresolved_ambiguities: []` | **FAIL** (TRA-038 PERSISTENT; see TRA-E3-002) |
| 5 | Broken internal link (TRA-037 — should be FIXED) | `ConformanceFailure`, BROKEN_LINK in unresolved_ambiguities | `CONFORMANCE FAILURE — 1 BROKEN_LINK entry/entries in unresolved_ambiguities`; exit 1; no output file; L3 gate checks `unresolved_ambiguities` (kernel.py:296-313) | **PASS** (TRA-037 FIXED) |
| 6 | Link rewrite hash discrepancy (TRA-037 — should be FIXED) | Audit-trail VERIFY_OUTPUT hash == emitted file hash | L3-gate VERIFY_OUTPUT `input_hash=225d5eded0c4a252` == emitted `sha256[:16]=225d5eded0c4a252`; MATCH=True on happy-path doc and on probe6b (valid English link). On probe6_link.md (CJK heading + CJK link), L3 gate now hashes post-rewrite target, but the false-positive BROKEN_LINK blocks publication — see TRA-E3-003 | **PASS** (TRA-037 hash fix confirmed) |
| 7 | HITL path | `--interactive` pauses for review | HUMAN-IN-THE-LOOP banner printed; `review_decision` called; default "skip" resolution taken (non-interactive stdin); `unresolved_ambiguities` contains both `UNRECOVERABLE:...` and `HITL[skip]:...`; ConformanceFailure raised; exit 1 (non-zero via exception); required Python monkey-patch of `repair_segment` (still unreachable through normal CLI — see TRA-E3-006) | **PASS** (HITL fires when triggered) |

## Byte-reproducibility probe (TRA-013 regression)

Two cold-cache runs of `python -m tra_cli --config /tmp/e3_work/config.yaml translate examples/security_advisory_zh.md --level L4` with `rm -rf` of cache/compilation_artifacts/audit_trace.jsonl between runs:

| Artifact | Run 1 sha256 | Run 2 sha256 | Match? |
|---|---|---|---|
| `audit_trace.jsonl` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | **YES** |
| `evidence_trace.jsonl` | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | **YES** |
| `output.md` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | **YES** |

**TRA-013 still fully remediated.** All three artifacts byte-identical across cold-cache runs. The deterministic clock (`kernel.py:157-171`) and content-addressed evidence IDs (`diagnostics.py:45-63`) produce stable timestamps and IDs.

## Round 2 carry-over status

| Round 2 finding | Round 2 severity | Round 3 status |
|---|---|---|
| TRA-E-001 (orphan lines / substring heuristic) | WARNING | **PERSISTS** (TRA-E3-001) |
| TRA-E-002 (audit hash ≠ emitted hash) | BLOCKING | **FIXED** (TRA-037; see TRA-E3-011) |
| TRA-E-003 (analyze-failure L3 gate bypass) | BLOCKING | **FIXED behaviorally** (TRA-036; severity classification still partial — see TRA-E3-004) |
| TRA-E-004 (UnknownTerm dead code) | WARNING | **PERSISTS** (TRA-038 / TRA-E3-002) |
| TRA-E-005 (segment_index always 0) | INFO | **PERSISTS** (TRA-E3-005) |
| TRA-E-006 (false-positive BROKEN_LINK on CJK headings) | WARNING | **ESCALATED TO BLOCKING** (TRA-037 gate fix now blocks valid translations — see TRA-E3-003) |
| TRA-E-007 (byte-reproducibility) | INFO positive | **PERSISTS** (TRA-E3-007) |
| TRA-E-008 (L4 vs L3 artifact diff) | INFO positive | **PERSISTS** (correct) |
| TRA-E-009 (HITL unreachable through CLI) | INFO | **PERSISTS** (TRA-E3-006) |
| TRA-E-010 (double VERIFY_OUTPUT at L3+) | INFO doc | **PERSISTS** (TRA-E3-014, documentation) |
| TRA-E-011 (BrokenMarkdown unreachable) | WARNING | **FIXED** (TRA-071; see TRA-E3-008) |
| TRA-E-012 (state sequence matches _KERNEL_ORDER) | INFO positive | **PERSISTS** (TRA-E3-012) |

## Findings

### TRA-E3-001 — Evidence trace orphan lines persist (TRA-001 / TRA-E-001 carry-over)
- **Severity:** WARNING
- **Category:** Forensic / Evidence Trace Integrity (§6.4.1)
- **Carry-over or new:** Carry-over from TRA-001 / TRA-E-001 (confirmed end-to-end at HEAD `b783745`)
- **Evidence:** `compilation_artifacts/evidence_trace.jsonl` line 7 from L4 run on `examples/security_advisory_zh.md`:
  ```json
  {"line": 7, "text": "96-core system keeps memory below <5MB at peak.", "evidence_ids": [], "attributed": false}
  ```
  `tra/reporting.py:73-95` (`line_by_line_trace`); `reporting.py:86`: `hits = [r.id for r in records if r.target_span and r.target_span in line]`.
- **Detail:** Substring-containment heuristic unchanged from Round 2. Line 7 contains only numbers and English text with no translated glossary terms, so no evidence record's `target_span` is a substring of this line. Result: `evidence_ids: []`, `attributed: false` — an orphan line with no evidence attribution. An L4 forensic reviewer cannot trace this output fragment back to any decision.
- **Suggested fix:** Implement a structural mapping (output line N → segment M → evidence chain) instead of post-hoc substring matching. Until TRA-001 segment-level translation lands, embed evidence ID references as HTML comments during translation, then strip after trace construction.

### TRA-E3-002 — UnknownTerm still never raised; unknown CJK terms pass through silently (TRA-038 / TRA-E-004 carry-over)
- **Severity:** WARNING
- **Category:** Forensic / Exception Recovery (§6 UNKNOWN_TERM)
- **Carry-over or new:** Carry-over from TRA-A2-002 / TRA-E-004 (PERSISTENT per Round 3 baseline TRA-038)
- **Evidence:** Probe 4 — input `The system 未知术语 must be translated. The execution环境 is fine.` run at L3:
  - Exit code: 0
  - Output: `The system 未知术语 must be translated. The execution环境 is fine.` (term passes through verbatim)
  - Audit trail: 6 records (no EXCEPTION_HANDLER); `unresolved_ambiguities: []`
  - `tra/isa.py:413-444` (`_rule_translate`): no code path checks for unknown CJK tokens or raises `UnknownTerm`.
  - `tra/recovery.py:77-87` (`recover_unknown_term`): defined but unreachable.
- **Detail:** Identical to Round 2. The TRA-004 path for `UnknownTerm` is NOT wired in production. An unknown CJK term passes through the rule path untranslated, appears verbatim in the target, and is NOT added to `unresolved_ambiguities`, NOT flagged by `verify_output`, and NOT recorded as an EXCEPTION_HANDLER audit record. The L3 gate passes silently (exit 0) with an untranslated term in the output. For L4 forensics, the ambiguity register is empty despite the unknown term — the forensic trail is incomplete.
- **Suggested fix:** Raise `UnknownTerm` from `_rule_translate` when a CJK token has no glossary/entity/epistemic match. Route through `_recover` → `recover_unknown_term`. Add a regression test that verifies the unknown term appears in `unresolved_ambiguities` and the audit trail has an EXCEPTION_HANDLER record.

### TRA-E3-003 — False-positive BROKEN_LINK now BLOCKS publication of valid CJK-heading + CJK-link translations (TRA-E-006 ESCALATED via TRA-037 fix)
- **Severity:** BLOCKING
- **Category:** Forensic / Link Rewriting + L3 Gate Interaction (§6.4 / §8)
- **Carry-over or new:** **Escalation** of Round 2 TRA-E-006 (WARNING → BLOCKING). The TRA-037 fix (L3 gate now checks `unresolved_ambiguities` for BROKEN_LINK entries — `kernel.py:296-313`) interacts with the pre-existing TRA-E-006 false-positive (link-rewrite produces BROKEN_LINK for valid CJK-heading slugs) to BLOCK publication of valid translations.
- **Evidence:** Probe input `# 系统成立\n\nSee [the system](#系统成立) for details.\n` run at L4:
  ```
  TRA bootstrap OK — pair=ZH -> EN level=L4_FORENSIC
  CONFORMANCE FAILURE — CONFORMANCE_FAILURE: 1 BROKEN_LINK entry/entries in
  unresolved_ambiguities — output is not L3-conformant (internal link target
  missing)
  EXIT: 1
  ```
  No output file emitted; no `compilation_artifacts/` directory created (kernel halts before EMIT_PAYLOAD state).
  - The link IS valid: heading `# 系统成立` translates to `# The system is Confirmed` (slug `the-system-is-confirmed`), and the link target `#系统成立` is translated by the rule path to `#The system is Confirmed` then slugified to `#the-system-is-confirmed` — pointing at the translated heading.
  - `tra/kernel.py:340-349` (Pass 1 of `_rewrite_anchors` slugifies the link target).
  - `tra/anchor.py:139-146` (`rewrite_links` calls `registry.translated_slug_for(slug)` — but `slug` is now the TRANSLATED slug `the-system-is-confirmed`, not the original `系统成立`; the registry only knows original→translated mappings, so it returns None → BROKEN_LINK flagged).
  - `tra/kernel.py:296-313` (L3 gate checks `unresolved_ambiguities` for "BROKEN_LINK" entries and raises ConformanceFailure).
- **Detail:** In Round 2, this false positive was a WARNING that polluted the audit trail but did not block publication (the L3 gate didn't check `unresolved_ambiguities`). The TRA-037 fix correctly added BROKEN_LINK checking to the L3 gate (Probe 5 confirmed genuine broken links are now caught), but this interacts with the TRA-E-006 false positive to BLOCK valid translations of any document containing a CJK heading that is also a CJK link target.

  **Impact:** Any document with the pattern `# <CJK glossary term>` followed by `[link](#<same CJK glossary term>)` will be rejected at L3/L4 with exit 1, even though the translation is structurally valid. This is a regression in user-facing behavior — the TRA-037 fix is correct for the BROKEN_LINK case but exposes the pre-existing TRA-E-006 false positive as a publication blocker.
- **Suggested fix:** In `_rewrite_anchors` Pass 2, after binding translated slugs, also check if any link target in the target text matches a TRANSLATED slug (not just original slugs). If `registry.map_placeholder_to_translated_slug` contains the link's slug as a value, the link is valid — don't flag it as broken. Alternatively, protect `#slug` link targets from translation in `_rule_translate` (extract them before substitution, restore after — similar to the code-block protection in `_execute_translation` at `kernel.py:427-447`).

### TRA-E3-004 — Empty source recovery severity still WARNING (TRA-E-003 partial carry-over)
- **Severity:** INFO
- **Category:** Forensic / Exception Recovery (§6 EMPTY_SOURCE)
- **Carry-over or new:** Partial carry-over from TRA-E-003 (the L3-gate bypass is FIXED; the severity classification is still wrong)
- **Evidence:** Probe 3 — empty input file run at L3:
  ```
  TRA bootstrap OK — pair=ZH -> EN level=L3_STRICT
  CONFORMANCE FAILURE — BROKEN_MARKDOWN: analyze_document failed (TRA_ERROR) —
  output is not L3-conformant
  EXIT: 1
  ```
  - Audit trail: 1 EXCEPTION_HANDLER record with `flags=['WARNING']`.
  - `tra/kernel.py:226-234` (TRA-036 fix: raises `ConformanceFailure` at L3+ on analyze failure).
  - `tra/recovery.py:191-197` (`route_exception` default fall-through for `TRAException` base class: `Severity.WARNING` + `RecoveryAction.PRESERVE_SOURCE`).
  - `tra/isa.py:89-90` (`EMPTY_SOURCE` raises `TRAException("EMPTY_SOURCE")`, base class — not a dedicated `BrokenMarkdown` or `EmptySource` subclass).
- **Detail:** TRA-036 fixed the L3-gate bypass (the early `return ""` at the old kernel.py:214 is replaced with `raise ConformanceFailure(...)` at L3+). Behavioral fix is correct: empty source now produces exit 1 with ConformanceFailure and no output file. **However**, the EXCEPTION_HANDLER audit record still shows `severity='WARNING'` (not BLOCKING) and `code='TRA_ERROR'` (not `EMPTY_SOURCE`), because `EMPTY_SOURCE` raises the base `TRAException` which falls through to the `route_exception` default. The spec §6 EMPTY_SOURCE recovery procedure mandates BLOCKING severity for empty sources (a critical structural failure). The L3 gate compensates for the wrong severity by raising ConformanceFailure, so the user-facing behavior is correct, but the L4 forensic trail's severity classification is still wrong.

  Note: this is a partial fix, not a regression. Round 2's TRA-E-003 was BLOCKING because the gate was bypassed entirely; Round 3's behavioral PASS is real progress.
- **Suggested fix:** Either (a) raise `BrokenMarkdown` directly from `analyze_document` when the source is empty (instead of `TRAException("EMPTY_SOURCE")`), so the recovery procedure produces the spec-correct BLOCKING severity; or (b) add a dedicated `EmptySource` exception subclass with a `route_exception` branch returning `Severity.BLOCKING` + `RecoveryAction.HALT`. Add a regression test asserting `severity=='BLOCKING'` and `code in ('EMPTY_SOURCE', 'BROKEN_MARKDOWN')` in the EXCEPTION_HANDLER audit record for an empty source at L3.

### TRA-E3-005 — RepairAttempt.segment_index is always 0 (TRA-E-005 carry-over)
- **Severity:** INFO
- **Category:** Forensic / Repair History (§6.4.2)
- **Carry-over or new:** Carry-over from TRA-E-005 (consequence of TRA-001 partial)
- **Evidence:** Triggered repair via input `The system is Valid under heavy load. 执行环境 here.\n` at L4. `compilation_artifacts/repair_history.jsonl`:
  ```json
  {"segment_index":0,"attempt":1,"subsystem":"epistemic","issue":"Epistemic drift: 'Valid' (from '成立')","before":"The system is Valid under heavy load. execution environment here.","after":"The system is Confirmed under heavy load. execution environment here.","evidence_id":"ev_be0981231fe5","resolved":true}
  ```
  - `tra/isa.py:621` (`segment_index: int = 0` default in `repair_segment` signature).
  - `tra/kernel.py:460-469` (kernel calls `repair_segment(...)` without passing `segment_index`).
- **Detail:** Whole-doc translation model (TRA-001 partial) treats the entire document as one segment. Every `RepairAttempt` in `repair_history.jsonl` has `segment_index: 0` regardless of which part of the document was repaired. An L4 forensic reviewer would expect `segment_index` to identify the leaf-node segment, enabling targeted review.
- **Suggested fix:** When TRA-001 segment-level translation is implemented, pass the actual leaf-node index to `repair_segment`. Until then, document the limitation in the `RepairAttempt.segment_index` docstring.

### TRA-E3-006 — HITL path fires correctly but still unreachable through normal CLI input (TRA-E-009 carry-over)
- **Severity:** INFO
- **Category:** Forensic / HITL (§6.2)
- **Carry-over or new:** Carry-over from TRA-E-009
- **Evidence:** Probe 7 — Python script patching both `isa.repair_segment` and `kernel.repair_segment` to raise `Unrecoverable`, with `interactive=True` and stdin redirected to `"skip\n"`:
  ```
  === PROBE 7: HITL path (interactive=True) ===
  Source: 'The system is Valid under heavy load. 执行环境 here.'
  Level:  L4_FORENSIC

  ─────────────────────────────── HUMAN-IN-THE-LOOP ───────────────────────────────
  Ambiguity: UNRECOVERABLE: Epistemic drift: 'Valid' (from '成立') — manual
  intervention required
  Source context: The system is Valid under heavy load. 执行环境 here.
  Candidate: The system is Valid under heavy load. execution environment here.
  Glossary options: 成立, 执行环境, 准确描述, 高度可信, 可能, 进行验证, 实现优化, ...
  Resolution [accept/override/skip] (skip): ConformanceFailure raised: CONFORMANCE_FAILURE:
  1 BLOCKING diagnostic(s) remain after repair loop — output is not L3-conformant
  unresolved_ambiguities: ["UNRECOVERABLE: Epistemic drift: 'Valid' (from '成立')",
    "HITL[skip]: Epistemic drift: 'Valid' (from '成立')"]
  repair_segment called: 1 times
  ```
  - `tra/kernel.py:470-493` (interactive HITL path).
  - `tra/hitl.py:24-59` (`review_decision` with `default="skip"`).
- **Detail:** Identical to Round 2. The HITL path fires correctly when `Unrecoverable` is raised: the kernel calls `format_unrecoverable` and `review_decision`, adopts the reviewer's resolution, and appends `HITL[{resolution}]: {issue}` to `unresolved_ambiguities`. With `default="skip"` in `Prompt.ask`, the non-interactive shell auto-resolves to "skip" (adopts candidate unchanged). The L3 gate subsequently raised `ConformanceFailure` because the candidate still contained the forbidden drift "Valid".

  **However**, `Unrecoverable` cannot be triggered through normal CLI input at L3/L4 with the rule-based translation path:
  1. Structural repair raises `Unrecoverable` at `attempt >= max_retries` (isa.py:655-658), but heading-count mismatches can't be triggered by the rule path (it preserves all headings).
  2. Repair introducing new BLOCKING raises `Unrecoverable` (isa.py:667-668), but the current glossary/forbidden mappings never produce a repair that introduces a new BLOCKING (all canonical targets are safe English terms that don't trigger forbidden/terminology checks).
- **Suggested fix:** Add a `--force-unrecoverable` debug flag that injects a structural BLOCKING to exercise the HITL path in integration tests. Add a CLI integration test that patches `repair_segment` to raise `Unrecoverable` (mirroring Probe 7's approach) and verifies the HITL hook fires, the ambiguity register records the HITL entry, and the CLI exits with the correct code based on the reviewer's resolution.

### TRA-E3-007 — Byte-reproducibility confirmed (TRA-013 still fully remediated; positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Reproducibility (§6.4 / TRA-013)
- **Carry-over or new:** Carry-over from TRA-013 / TRA-E-007 (still remediated at HEAD `b783745`)
- **Evidence:** See "Byte-reproducibility probe" table above. All 3 artifacts (audit_trace.jsonl, evidence_trace.jsonl, output.md) byte-identical across two cold-cache runs. Hashes match Round 2's reported values exactly (e.g., `audit_trace.jsonl` sha256 = `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` — identical to Round 2's reported hash).
- **Detail:** Deterministic clock (`kernel.py:157-171`, `seed = self._source_hash_seed or "0" * 16`) and content-addressed evidence IDs (`diagnostics.py:45-63`, `ev_{sha256(canonical_record)[:12]}`) produce stable timestamps and IDs. The cache stores translation results with their evidence_ids; the cache-hit path (`isa.py:345`) emits the same audit record with the same evidence_ids. The cache does not break reproducibility.
- **Suggested fix:** None. Positive confirmation.

### TRA-E3-008 — TRA-071 BROKEN_MARKDOWN now reachable; unclosed fence raises it correctly (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Exception Recovery (§6 BROKEN_MARKDOWN)
- **Carry-over or new:** Resolution of Round 2 TRA-E-011 (BrokenMarkdown unreachable) via TRA-071 fix
- **Evidence:** Probe 2 — input `# Test\n\n```python\ndef foo():\n    pass\n` (unclosed fence) run at L3:
  ```
  CONFORMANCE FAILURE — BROKEN_MARKDOWN: analyze_document failed (BROKEN_MARKDOWN)
  — output is not L3-conformant
  EXIT: 1
  ```
  - Audit trail: 1 EXCEPTION_HANDLER record with `flags=['BLOCKING']`.
  - `tra/isa.py:92-97` (BrokenMarkdown wrapper around `build_structural_map`).
  - `tests/test_tra071_broken_markdown.py` (regression test exists).
- **Detail:** TRA-071 added explicit structural validation in `build_structural_map` that raises `BrokenMarkdown` for genuinely broken markdown (unclosed code fences). The exception is correctly routed through `_recover` → `recover_broken_markdown` → `Severity.BLOCKING` + `RecoveryAction.HALT`. The audit trail records `code='BROKEN_MARKDOWN'` and `severity='BLOCKING'` as the spec mandates. The Round 2 TRA-E-011 finding (BrokenMarkdown was dead code, severity always WARNING via base-class fall-through) is resolved.

  Note: the Round 3 baseline lists TRA-071 as `REGRESSION-TEST-FAIL` (test exists but reported no output during the baseline run). My end-to-end Probe 2 confirms the behavior works correctly through the CLI — the test failure is likely a test-runner issue, not a behavior issue.
- **Suggested fix:** Investigate why `TestTRA071BrokenMarkdown` reported "no output" during the baseline regression run (possibly a fixture issue or test collection problem). The behavior itself is correct.

### TRA-E3-009 — TRA-036 L3 gate now blocks empty source (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / L3 Gate (§8)
- **Carry-over or new:** Resolution of Round 2 TRA-E-003 (L3 gate bypass on analyze failure) via TRA-036 fix
- **Evidence:** Probe 3 — empty input file run at L3 → `ConformanceFailure` raised, exit 1, no output file written (see TRA-E3-004 for the EXCEPTION_HANDLER severity nuance).
  - `tra/kernel.py:226-234` (TRA-036 fix: `if self.config.conformance_level in (L3_STRICT, L4_FORENSIC): raise ConformanceFailure(...)`).
  - `tests/test_outstanding_findings.py::TestTRA036AnalyzeFailureL3Gate` (regression test passes per baseline).
- **Detail:** The early `return ""` at the old `kernel.py:214` is replaced with `raise ConformanceFailure(...)` at L3+. The L3 gate is no longer bypassed on analyze failure. A non-conformant (empty) output is no longer silently published as "translated".
- **Suggested fix:** None (behavioral fix correct). See TRA-E3-004 for the residual severity-classification issue.

### TRA-E3-010 — TRA-037 L3 gate now checks unresolved_ambiguities for BROKEN_LINK (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / L3 Gate (§8)
- **Carry-over or new:** Resolution of Round 2 TRA-A2-006 (L3 gate didn't check unresolved_ambiguities) via TRA-037 fix
- **Evidence:** Probe 5 — input `# Test Heading\n\nSee [this link](#nonexistent) for details.\n` run at L3:
  ```
  CONFORMANCE FAILURE — CONFORMANCE_FAILURE: 1 BROKEN_LINK entry/entries in
  unresolved_ambiguities — output is not L3-conformant (internal link target
  missing)
  EXIT: 1
  ```
  - `tra/kernel.py:293-313` (L3 gate collects `broken_links = [a for a in self.ctx.unresolved_ambiguities if "BROKEN_LINK" in a]` and raises ConformanceFailure if any exist).
  - `tests/test_outstanding_findings.py::TestTRA037RewriteAnchorsBeforeGate` (regression test passes per baseline).
- **Detail:** The L3 gate now correctly rejects outputs with BROKEN_LINK entries in `unresolved_ambiguities`. Combined with TRA-E3-011 (rewrite moved before the gate), the gate sees the post-rewrite target and its associated ambiguities. Genuine broken internal links (Probe 5) now block publication at L3+.
- **Suggested fix:** None (correct behavior for genuine broken links). See TRA-E3-003 for the false-positive escalation that this fix exposes.

### TRA-E3-011 — TRA-037 link rewrite hash now matches emitted target hash (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Audit Trail Hash-Chain Integrity (§6.4)
- **Carry-over or new:** Resolution of Round 2 TRA-E-002 (audit hash ≠ emitted hash) via TRA-037 fix
- **Evidence:** Probe 6 — L4 happy-path run:
  - L3-gate VERIFY_OUTPUT (seq=5) `input_hash=225d5eded0c4a252`
  - Emitted `/tmp/e3_out.md` `sha256[:16]=225d5eded0c4a252`
  - MATCH=True
  Probe 6b — input `# System Overview\n\nSee [overview](#system-overview) for details.\n\n执行环境 is mentioned here.\n` (valid English internal link) at L4:
  - L3-gate VERIFY_OUTPUT (seq=5) `input_hash=298e27e3459e6e48`
  - Emitted file `sha256[:16]=298e27e3459e6e48`
  - MATCH=True; exit 0
  - `tra/kernel.py:270-279` (TRA-037 fix: `_rewrite_anchors(target)` now runs BEFORE the L3 gate, so the gate hashes the post-rewrite target).
- **Detail:** Round 2's TRA-E-002 BLOCKING finding (audit trail's VERIFY_OUTPUT hash was computed on pre-rewrite target while emitted target was post-rewrite) is resolved. The L3 gate's verify_output now hashes the post-rewrite target, which matches the emitted file's hash when the gate passes. The first verify_output (seq=4, for initial diagnostics) still hashes the pre-rewrite target on docs where the rewrite changes something (e.g., probe6_link.md: seq=4 hash `8cf58ec60d4c25c0` ≠ seq=5 hash `5dd98a654c8ce708`), but the L3-gate verify_output (seq=5) is the one that determines conformance and matches the emitted file.
- **Suggested fix:** None. Positive confirmation. (Optionally: add an `artifact_snapshot` field to the first VERIFY_OUTPUT record labeling it `purpose=initial_diagnostics` to distinguish it from the L3-gate verify.)

### TRA-E3-012 — Audit trail state sequence matches _KERNEL_ORDER (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / State Machine (§2.1)
- **Carry-over or new:** Carry-over from TRA-E-012 (still correct at HEAD `b783745`)
- **Evidence:** See "Audit trail state sequence" section above. `execution_log.json` records all 8 post-BOOTSTRAP states in the correct order. `tra/kernel.py:64-74` (`_KERNEL_ORDER`).
- **Detail:** Forward-only transition guard (`kernel.py:173-183`) respected. No gaps, no duplicates, no out-of-order transitions.
- **Suggested fix:** None. Positive confirmation.

### TRA-E3-013 — All 9 runtime artifacts present, exit 0 on happy path (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Artifact Emission (§6.4)
- **Carry-over or new:** Carry-over from TRA-E-008 (still correct at HEAD `b783745`)
- **Evidence:** See "L4 happy-path run" section above. All 9 artifacts present with non-zero sizes (except `repair_history.jsonl` which is 0 B on a clean run, and `ambiguity_register.json` which is 2 B = `[]` on a clean run).
- **Detail:** L4 emits everything L1-L3 emits PLUS `evidence_trace.jsonl` and `ambiguity_register.json`. The L4-only artifacts are gated by `_export_forensics` (`kernel.py:509-528`), which returns early unless `conformance_level == L4_FORENSIC`.
- **Suggested fix:** None. Positive confirmation.

### TRA-E3-014 — Double VERIFY_OUTPUT at L3+ (TRA-E-010 carry-over, documentation)
- **Severity:** INFO (documentation)
- **Category:** Forensic / Audit Trail Structure (§7)
- **Carry-over or new:** Carry-over from TRA-E-010 (still applies at HEAD `b783745`)
- **Evidence:** L4 audit_trace.jsonl has 6 records (2× VERIFY_OUTPUT); L1/L2 would have 5 (1× VERIFY_OUTPUT). The 6th record is from the L3 gate (`kernel.py:291`).
- **Detail:** At L3_STRICT and L4_FORENSIC, `verify_output` is called twice:
  1. `kernel.py:264` — initial diagnostics for the repair loop
  2. `kernel.py:291` — final L3 gate check after the repair loop and after `_rewrite_anchors`
  Both calls append a `VERIFY_OUTPUT` audit record. The `execution_log.json` records only one VERIFY_OUTPUT state transition. The double record is an ISA-level artifact.
- **Suggested fix:** Add an `artifact_snapshot` field to the second VERIFY_OUTPUT record (e.g., `{"purpose": "L3_gate"}`) to distinguish it from the initial verify. Document in the audit trail schema that L3+ runs produce two VERIFY_OUTPUT records.

## Comparison to Round 2 Track E

| Metric | Round 2 (HEAD `4b8827c`) | Round 3 (HEAD `b783745`) | Delta |
|---|---|---|---|
| Total findings | 12 | 14 | +2 (TRA-E3-013, TRA-E3-014 split out from positives; TRA-E3-003 is the same issue escalated) |
| BLOCKING | 2 | 1 | -1 (TRA-E-002 and TRA-E-003 fixed; TRA-E-006 escalated to BLOCKING) |
| WARNING | 4 | 2 | -2 (TRA-E-011 fixed; TRA-E-006 escalated to BLOCKING) |
| INFO | 6 | 11 | +5 (more positive confirmations split out) |
| L4 happy-path PASS | YES | YES | unchanged |
| Byte-reproducibility | BYTE-IDENTICAL | BYTE-IDENTICAL | unchanged |
| Probes passed | 5/7 | 6/7 | +1 (Probe 2 BROKEN_MARKDOWN now raised; Probe 6 hash now matches) |

## Positive confirmations (no fix needed)

1. **TRA-013 byte-reproducibility** — confirmed (TRA-E3-007)
2. **TRA-071 BROKEN_MARKDOWN reachable** — confirmed (TRA-E3-008)
3. **TRA-036 L3 gate blocks empty source** — confirmed (TRA-E3-009)
4. **TRA-037 L3 gate checks unresolved_ambiguities** — confirmed (TRA-E3-010)
5. **TRA-037 link rewrite hash matches emitted** — confirmed (TRA-E3-011)
6. **State sequence matches _KERNEL_ORDER** — confirmed (TRA-E3-012)
7. **All 9 artifacts present, exit 0** — confirmed (TRA-E3-013)
8. **HITL path fires when triggered** — confirmed (TRA-E3-006 / Probe 7)

## Open issues requiring remediation

1. **TRA-E3-003 (BLOCKING)** — False-positive BROKEN_LINK now blocks valid CJK-heading + CJK-link translations. **HIGHEST PRIORITY** — this is a user-facing regression introduced by the TRA-037 fix interacting with the pre-existing TRA-E-006 false positive. Any document with `# <CJK glossary term>` followed by `[link](#<same CJK term>)` will be rejected at L3/L4.
2. **TRA-E3-001 (WARNING)** — Evidence trace orphan lines (TRA-001 consequence). Pending TRA-001 segment-level translation.
3. **TRA-E3-002 (WARNING)** — UnknownTerm not raised (TRA-038 persistent). Affects L4 forensic completeness.
4. **TRA-E3-004 (INFO)** — Empty source severity classification (TRA-E-003 partial). Cosmetic but spec-violating.
5. **TRA-E3-005 (INFO)** — RepairAttempt.segment_index always 0 (TRA-E-005 persistent). Pending TRA-001.
6. **TRA-E3-006 (INFO)** — HITL unreachable through CLI (TRA-E-009 persistent). Testability gap.
7. **TRA-E3-014 (INFO)** — Double VERIFY_OUTPUT at L3+ documentation (TRA-E-010 persistent). Cosmetic.

---

**Audit complete.** Deliverable written to `/home/z/my-project/download/TRA_Round3/track_e3_findings.md`.
