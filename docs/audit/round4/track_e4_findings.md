# Track E4 — Forensic L4 End-to-End Re-Audit (Round 4)

**HEAD audited:** `805a8f8`
**Methodology:** End-to-end L4 pipeline execution + artifact inspection + byte-reproducibility verification (sha256sum across 2 cold-cache runs) + 6 forensic probes (re-run from R3 Track E3) + new-finding hunt.
**Baseline:** Round 3 Track E3 (14 findings: 1 BLOCKING / 2 WARNING / 11 INFO) + 36-finding R3 master register + R4 regression baseline.
**Auditor:** Track E4 agent
**Audit date:** 2026-07-17

## Summary

- Findings: **15 total** (0 BLOCKING / 2 WARNING / 13 INFO)
- Carry-over from Round 3 Track E3: **14** (all 14 re-verified — 1 BLOCKING resolved to FIXED positive; 2 WARNING persistent; 4 INFO persistent; 7 INFO positive)
- New findings: **1** (TRA-E4-015 — `style_profile.yaml` undocumented in SKILL.md §4)
- L4 pipeline at HEAD: **PASS** — 199 pytest tests pass; e2e suite (`test_e2e_to_translate.py`) 12/12 pass; manual `e2e_test.py` verdict: `L3 CONFORMANT — zero BLOCKING diagnostics`; L4 translate exits 0; L3 `validate` on emitted target exits 0
- Byte-reproducibility (TRA-013): **HOLDS** — all 6 sha256 hashes match across 2 cold-cache runs; `audit_trace.jsonl` sha256 = `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` (matches R3 Track E3 hash exactly — byte-identical to HEAD `b783745` L4 output)
- TRA-093 BLOCKING from R3 (false-positive BROKEN_LINK): **FIXED** — CJK heading + CJK link translation now publishes with exit 0

## L4 artifact inventory at HEAD 805a8f8

| Artifact | Exists? | Size | Valid? | Notes |
|---|---|---|---|---|
| glossary.yaml | yes | 1296 B | yes | 11 entries; canonical mappings (`成立 → Confirmed`, `执行环境 → execution environment`, …) all present |
| entity_table.yaml | yes | 438 B | yes | 6 entities (v0.5.0, RustVMM, KVM, P99, SA, XFS) |
| structural_map.json | yes | 1528 B | yes | 4 top-level nodes (heading + 2 paragraphs + blockquote) + 1 nested child = 5 total nodes (matches audit `artifact_snapshot.node_count=5`) |
| style_profile.yaml | yes | 260 B | yes | voice/sentence_complexity/epistemic_mapping/punctuation_rules; **NOT documented in SKILL.md §4** (TRA-E4-015) |
| execution_log.json | yes | 249 B | yes | 8 post-BOOTSTRAP states in canonical order; `unresolved_ambiguities: []` |
| repair_history.jsonl | yes | 0 B | yes | empty (clean run, no repairs); when repair is triggered (Probe 5), 1 record with `segment_index:0` |
| evidence_trace.jsonl | yes | 974 B | yes | 6 lines; 1 orphan line (line 7: `96-core system keeps memory below <5MB at peak.`) — TRA-E4-001 |
| ambiguity_register.json | yes | 2 B | yes | `[]` (empty array) — clean run |
| audit_trace.jsonl | yes | 1540 B | yes | 6 records: ANALYZE_DOCUMENT → BUILD_GLOSSARY → BUILD_ENTITY_TABLE → TRANSLATE_SEGMENT → VERIFY_OUTPUT → VERIFY_OUTPUT (double VERIFY_OUTPUT at L3+ — TRA-E4-013) |

All 9 expected L4 artifacts exist and parse cleanly (YAML / JSON / JSONL). All byte sizes match R3 Track E3's reported values exactly.

## Byte-reproducibility (TRA-013)

Two cold-cache runs with `rm -rf /tmp/e4_work/{cache,compilation_artifacts,audit_trace.jsonl}` between each run, using an isolated config at `/tmp/e4_work/config.yaml` (mirrors R3 Track E3's isolation pattern):

```bash
# Run 1 sha256 hashes
225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f  /tmp/l4_run1.md
263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797  /tmp/e4_work/audit_trace.jsonl
f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4  /tmp/e4_work/compilation_artifacts/evidence_trace.jsonl
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  /tmp/e4_work/compilation_artifacts/repair_history.jsonl
4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945  /tmp/e4_work/compilation_artifacts/ambiguity_register.json
d24cfc29c46a152f417d6a8f17c606d3b933fa2918ba8c2d39e4b121b50eef6f  /tmp/e4_work/compilation_artifacts/execution_log.json

# Run 2 sha256 hashes
225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f  /tmp/l4_run2.md
263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797  /tmp/e4_work/audit_trace.jsonl
f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4  /tmp/e4_work/compilation_artifacts/evidence_trace.jsonl
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  /tmp/e4_work/compilation_artifacts/repair_history.jsonl
4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945  /tmp/e4_work/compilation_artifacts/ambiguity_register.json
d24cfc29c46a152f417d6a8f17c606d3b933fa2918ba8c2d39e4b121b50eef6f  /tmp/e4_work/compilation_artifacts/execution_log.json

# Diff result
HOLDS: all 6 artifact hashes match across the 2 cold-cache runs.
```

**Independent re-verification of Track B4's claim.** B4 reported `audit_trace` sha256 `263b901e...` and `evidence_trace` sha256 `f9831523...` — both reproduce exactly in this E4 audit. Notably, both hashes also match R3 Track E3's reported values (HEAD `b783745`), meaning the L4 output is byte-identical between R3 close and HEAD `805a8f8`. The deterministic clock (`tra/kernel.py:157-171`) and content-addressed evidence IDs (`tra/diagnostics.py:45-63`) continue to produce stable timestamps and IDs.

## Probe results (re-running R3 Track E3's 6 probes)

| # | Probe | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | `evidence_trace.jsonl` exists at L4 | yes | 974 B, valid JSONL, 6 records | **PASS** |
| 2 | `ambiguity_register.json` exists at L4 | yes | 2 B (`[]`), valid JSON | **PASS** |
| 3 | `audit_trace.jsonl` contains `VERIFY_OUTPUT` with zero BLOCKING | yes (2× VERIFY_OUTPUT, no BLOCKING) | 2 VERIFY_OUTPUT records (seq=4, seq=5); `flags_raised=None` on all 6 records; no BLOCKING | **PASS** |
| 4 | Orphan lines in `evidence_trace.jsonl` (TRA-001 consequence) | yes (persistent) | 1 orphan line (line 7: `96-core system keeps memory below <5MB at peak.`) with `evidence_ids=[]`, `attributed=false` | **PERSISTS** (TRA-E4-001) |
| 5 | `RepairAttempt.segment_index` always 0 (TRA-001 consequence) | yes (persistent) | Triggered repair via `'The system is Valid under heavy load. 执行环境 here.'`; repair_history has 1 record with `segment_index:0`; only distinct value is `[0]` | **PERSISTS** (TRA-E4-004) |
| 6 | L3 `validate` exits 0 on conformant output | yes | `Validation level=L3_STRICT — BLOCKING=0 WARNING=0 INFO=0` / `PASS: candidate meets the conformance gate.` / exit 0 | **PASS** |

## Findings

### TRA-E4-001 — Evidence trace orphan lines persist (TRA-001 / TRA-E-001 / TRA-E3-001 carry-over)
- **Severity:** WARNING
- **Category:** Forensic / Evidence Trace Integrity (§6.4.1)
- **Carry-over or new:** Carry-over from TRA-E-001 / TRA-E3-001 (PERSISTENT at HEAD `805a8f8`)
- **Evidence:** `compilation_artifacts/evidence_trace.jsonl` line 5 from L4 run on `examples/security_advisory_zh.md`:
  ```json
  {"line": 7, "text": "96-core system keeps memory below <5MB at peak.", "evidence_ids": [], "attributed": false}
  ```
  `tra/reporting.py:73-95` (`line_by_line_trace`); `reporting.py:86` (per R3): `hits = [r.id for r in records if r.target_span and r.target_span in line]` — substring-containment heuristic.
- **Detail:** Identical to R3 Track E3. The substring-containment heuristic in `line_by_line_trace` cannot match any evidence record's `target_span` to a line containing only numbers and English text (no translated glossary terms). Result: `evidence_ids: []`, `attributed: false` — an orphan line with no evidence attribution. An L4 forensic reviewer cannot trace this output fragment back to any decision. Pending TRA-001 segment-level translation.
- **Suggested fix:** Implement structural mapping (output line N → segment M → evidence chain). Until TRA-001 lands, embed evidence ID references as HTML comments during translation, then strip after trace construction.
- **Round 3 status:** persistent

### TRA-E4-002 — UnknownTerm still never raised; unknown CJK terms pass through silently (TRA-038 / TRA-E-004 / TRA-E3-002 carry-over)
- **Severity:** WARNING
- **Category:** Forensic / Exception Recovery (§6 UNKNOWN_TERM)
- **Carry-over or new:** Carry-over from TRA-E-004 / TRA-E3-002 (PERSISTENT per Round 4 baseline TRA-038 PARTIAL)
- **Evidence:** Probe — input `The system 未知术语 must be translated. The execution环境 is fine.` run at L4:
  - Exit code: 0
  - Output: `The system 未知术语 must be translated. The execution环境 is fine.` (term passes through verbatim)
  - Audit trail: 6 records (no EXCEPTION_HANDLER)
  - `compilation_artifacts/ambiguity_register.json`: `[]` (empty)
  - `tra/isa.py:413-444` (`_rule_translate`): no code path checks for unknown CJK tokens or raises `UnknownTerm`.
  - `tra/recovery.py:77-87` (`recover_unknown_term`): defined but unreachable.
- **Detail:** Identical to R3 Track E3. The TRA-004 path for `UnknownTerm` is NOT wired in production. An unknown CJK term passes through the rule path untranslated, appears verbatim in the target, and is NOT added to `unresolved_ambiguities`, NOT flagged by `verify_output`, and NOT recorded as an EXCEPTION_HANDLER audit record. The L3 gate passes silently (exit 0) with an untranslated term in the output. For L4 forensics, the ambiguity register is empty despite the unknown term — the forensic trail is incomplete.
- **Suggested fix:** Raise `UnknownTerm` from `_rule_translate` when a CJK token has no glossary/entity/epistemic match. Route through `_recover` → `recover_unknown_term`. Add a regression test that verifies the unknown term appears in `unresolved_ambiguities` and the audit trail has an EXCEPTION_HANDLER record.
- **Round 3 status:** persistent

### TRA-E4-003 — Empty source recovery severity still WARNING (TRA-E-003 / TRA-E3-004 partial carry-over)
- **Severity:** INFO
- **Category:** Forensic / Exception Recovery (§6 EMPTY_SOURCE)
- **Carry-over or new:** Partial carry-over from TRA-E-003 / TRA-E3-004 (the L3-gate bypass is FIXED; the severity classification is still wrong)
- **Evidence:** Probe — empty input file run at L4:
  - `CONFORMANCE FAILURE — BROKEN_MARKDOWN: analyze_document failed (TRA_ERROR)`; exit 1; no output file emitted
  - Audit trail: 1 EXCEPTION_HANDLER record with `flags_raised=['WARNING']`
  - `artifact_snapshot.severity='WARNING'`, `artifact_snapshot.action='PRESERVE_SOURCE'`, `artifact_snapshot.detail='EMPTY_SOURCE: document contains no translatable content'`, `artifact_snapshot.reason="TRAException('EMPTY_SOURCE: document contains no translatable content')"`
  - `tra/kernel.py:226-234` (TRA-036 fix: raises `ConformanceFailure` at L3+ on analyze failure)
  - `tra/recovery.py:191-197` (`route_exception` default fall-through for `TRAException` base class: `Severity.WARNING` + `RecoveryAction.PRESERVE_SOURCE`)
  - `tra/isa.py:89-90` (`EMPTY_SOURCE` raises `TRAException("EMPTY_SOURCE")`, base class — not a dedicated `BrokenMarkdown` or `EmptySource` subclass)
- **Detail:** Identical to R3 Track E3. Behavioral fix correct: empty source now produces exit 1 with ConformanceFailure and no output file. **However**, the EXCEPTION_HANDLER audit record still shows `severity='WARNING'` (not BLOCKING) and `code='TRA_ERROR'` (not `EMPTY_SOURCE`), because `EMPTY_SOURCE` raises the base `TRAException` which falls through to the `route_exception` default. The spec §6 EMPTY_SOURCE recovery procedure mandates BLOCKING severity for empty sources. The L3 gate compensates for the wrong severity by raising ConformanceFailure, so the user-facing behavior is correct, but the L4 forensic trail's severity classification is still wrong.
- **Suggested fix:** Either (a) raise `BrokenMarkdown` directly from `analyze_document` when the source is empty (instead of `TRAException("EMPTY_SOURCE")`), so the recovery procedure produces the spec-correct BLOCKING severity; or (b) add a dedicated `EmptySource` exception subclass with a `route_exception` branch returning `Severity.BLOCKING` + `RecoveryAction.HALT`.
- **Round 3 status:** persistent (partial fix retained)

### TRA-E4-004 — RepairAttempt.segment_index is always 0 (TRA-E-005 / TRA-E3-005 carry-over)
- **Severity:** INFO
- **Category:** Forensic / Repair History (§6.4.2)
- **Carry-over or new:** Carry-over from TRA-E-005 / TRA-E3-005 (consequence of TRA-001 partial)
- **Evidence:** Triggered repair via input `The system is Valid under heavy load. 执行环境 here.\n` at L4. `compilation_artifacts/repair_history.jsonl`:
  ```json
  {"segment_index":0,"attempt":1,"subsystem":"epistemic","issue":"Epistemic drift: 'Valid' (from '成立')","before":"The system is Valid under heavy load. execution environment here.","after":"The system is Confirmed under heavy load. execution environment here.","evidence_id":"ev_be0981231fe5","resolved":true}
  ```
  - `tra/isa.py:621` (`segment_index: int = 0` default in `repair_segment` signature).
  - `tra/kernel.py:460-469` (kernel calls `repair_segment(...)` without passing `segment_index`).
  - Distinct `segment_index` values across all repair records: `[0]`.
- **Detail:** Identical to R3 Track E3. Whole-doc translation model (TRA-001 partial) treats the entire document as one segment. Every `RepairAttempt` in `repair_history.jsonl` has `segment_index: 0` regardless of which part of the document was repaired. An L4 forensic reviewer would expect `segment_index` to identify the leaf-node segment, enabling targeted review.
- **Suggested fix:** When TRA-001 segment-level translation is implemented, pass the actual leaf-node index to `repair_segment`. Until then, document the limitation in the `RepairAttempt.segment_index` docstring.
- **Round 3 status:** persistent

### TRA-E4-005 — HITL path still unreachable through normal CLI input (TRA-E-009 / TRA-E3-006 carry-over)
- **Severity:** INFO
- **Category:** Forensic / HITL (§6.2)
- **Carry-over or new:** Carry-over from TRA-E-009 / TRA-E3-006 (PERSISTENT)
- **Evidence:**
  - `tra_cli.py:72` — `--interactive` flag exists
  - `tra_cli.py:107` — `kernel = TRAKernel(cfg, interactive=interactive)` (no `--force-unrecoverable` debug flag)
  - `rg -rn "raise Unrecoverable" tra/` → only 2 raise sites:
    - `tra/isa.py:666` — structural repair max retries (`attempt >= max_retries`)
    - `tra/isa.py:678` — repair introduces new BLOCKING
  - Both raise paths require pathological input that the rule-based translation path cannot produce on the canonical ZH-EN glossary (all canonical targets are safe English terms that don't trigger forbidden/terminology checks).
  - `rg -n "force_unrecoverable|force-unrecoverable" tra_cli.py tra/ tests/` → no match (debug flag not added).
- **Detail:** Identical to R3 Track E3. The HITL path fires correctly when `Unrecoverable` is raised (R3 Probe 7 confirmed), but `Unrecoverable` cannot be triggered through normal CLI input at L3/L4 with the rule-based translation path. Testability gap.
- **Suggested fix:** Add a `--force-unrecoverable` debug flag that injects a structural BLOCKING to exercise the HITL path in integration tests. Add a CLI integration test that patches `repair_segment` to raise `Unrecoverable`.
- **Round 3 status:** persistent

### TRA-E4-006 — Byte-reproducibility confirmed (TRA-013 still fully remediated; positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Reproducibility (§6.4 / TRA-013)
- **Carry-over or new:** Carry-over from TRA-013 / TRA-E-007 / TRA-E3-007 (still remediated at HEAD `805a8f8`)
- **Evidence:** See "Byte-reproducibility" section above. All 6 artifacts (`audit_trace.jsonl`, `evidence_trace.jsonl`, `repair_history.jsonl`, `ambiguity_register.json`, `execution_log.json`, output target) byte-identical across two cold-cache runs. Hashes match R3 Track E3's reported values exactly:
  - `audit_trace.jsonl` sha256 = `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` (matches R3 — L4 output byte-identical between HEAD `b783745` and HEAD `805a8f8`)
  - `evidence_trace.jsonl` sha256 = `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` (matches R3)
  - target sha256 = `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` (matches R3)
- **Detail:** Deterministic clock (`kernel.py:157-171`, `seed = self._source_hash_seed or "0" * 16`) and content-addressed evidence IDs (`diagnostics.py:45-63`, `ev_{sha256(canonical_record)[:12]}`) produce stable timestamps and IDs. The cache stores translation results with their evidence_ids; the cache-hit path emits the same audit record with the same evidence_ids. The cache does not break reproducibility.
- **Suggested fix:** None. Positive confirmation. **Independent re-verification of Track B4's claim** (B4 reported the same `audit_trace` and `evidence_trace` hashes — reproduced here without relying on B4's result).
- **Round 3 status:** persistent (positive)

### TRA-E4-007 — TRA-071 BROKEN_MARKDOWN still reachable; unclosed fence raises it correctly (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Exception Recovery (§6 BROKEN_MARKDOWN)
- **Carry-over or new:** Carry-over from TRA-E3-008 (still correct at HEAD `805a8f8`)
- **Evidence:** R4 baseline TRA-071 FIXED via `test_outstanding_findings.py::TestTRA071BrokenMarkdown` PASS. `tra/isa.py:92-97` (`BrokenMarkdown` wrapper around `build_structural_map`). End-to-end behavior previously confirmed by R3 Probe 2 (unclosed fence → exit 1, EXCEPTION_HANDLER with BLOCKING flag). R4 test suite (199 tests) all pass.
- **Detail:** TRA-071 added explicit structural validation in `build_structural_map` that raises `BrokenMarkdown` for genuinely broken markdown. The exception is correctly routed through `_recover` → `recover_broken_markdown` → `Severity.BLOCKING` + `RecoveryAction.HALT`. The audit trail records `code='BROKEN_MARKDOWN'` and `severity='BLOCKING'` as the spec mandates.
- **Suggested fix:** None. Positive confirmation.
- **Round 3 status:** persistent (positive)

### TRA-E4-008 — TRA-036 L3 gate still blocks empty source (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / L3 Gate (§8)
- **Carry-over or new:** Carry-over from TRA-E3-009 (still correct at HEAD `805a8f8`)
- **Evidence:** Probe (TRA-E4-003 above) — empty input file run at L4 → `ConformanceFailure` raised, exit 1, no output file written.
  - `tra/kernel.py:226-234` (TRA-036 fix: `if self.config.conformance_level in (L3_STRICT, L4_FORENSIC): raise ConformanceFailure(...)`).
  - `tests/test_outstanding_findings.py::TestTRA036AnalyzeFailureL3Gate` (regression test passes per baseline).
- **Detail:** The early `return ""` at the old `kernel.py:214` is replaced with `raise ConformanceFailure(...)` at L3+. The L3 gate is no longer bypassed on analyze failure. A non-conformant (empty) output is no longer silently published as "translated".
- **Suggested fix:** None (behavioral fix correct). See TRA-E4-003 for the residual severity-classification issue.
- **Round 3 status:** persistent (positive)

### TRA-E4-009 — TRA-037 L3 gate still checks unresolved_ambiguities for BROKEN_LINK (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / L3 Gate (§8)
- **Carry-over or new:** Carry-over from TRA-E3-010 (still correct at HEAD `805a8f8`)
- **Evidence:** R4 baseline TRA-037 FIXED. `tests/test_outstanding_findings.py::TestTRA037RewriteAnchorsBeforeGate` PASS. R3 Probe 5 confirmed end-to-end (input with `#nonexistent` link → `CONFORMANCE FAILURE — CONFORMANCE_FAILURE: 1 BROKEN_LINK entry/entries in unresolved_ambiguities`, exit 1).
  - `tra/kernel.py:293-313` (L3 gate collects `broken_links = [a for a in self.ctx.unresolved_ambiguities if "BROKEN_LINK" in a]` and raises ConformanceFailure if any exist).
- **Detail:** The L3 gate correctly rejects outputs with BROKEN_LINK entries in `unresolved_ambiguities`. Combined with TRA-E4-010 (rewrite moved before the gate), the gate sees the post-rewrite target and its associated ambiguities. Genuine broken internal links now block publication at L3+.
- **Suggested fix:** None (correct behavior for genuine broken links).
- **Round 3 status:** persistent (positive)

### TRA-E4-010 — TRA-037 link rewrite hash still matches emitted target hash (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Audit Trail Hash-Chain Integrity (§6.4)
- **Carry-over or new:** Carry-over from TRA-E3-011 (still correct at HEAD `805a8f8`)
- **Evidence:** L4 happy-path run on `examples/security_advisory_zh.md`:
  - `audit_trace.jsonl` seq=4 VERIFY_OUTPUT `input_hash=225d5eded0c4a252`
  - `audit_trace.jsonl` seq=5 VERIFY_OUTPUT `input_hash=225d5eded0c4a252`
  - Emitted `/tmp/l4_run1.md` `sha256[:16]=225d5eded0c4a252`
  - **MATCH=True** on both VERIFY_OUTPUT records (this doc has no internal links, so initial-verify and L3-gate-verify hash the same target)
  - `tra/kernel.py:270-279` (TRA-037 fix: `_rewrite_anchors(target)` now runs BEFORE the L3 gate, so the gate hashes the post-rewrite target).
- **Detail:** Round 2's TRA-E-002 BLOCKING finding (audit trail's VERIFY_OUTPUT hash was computed on pre-rewrite target while emitted target was post-rewrite) is resolved. The L3 gate's verify_output now hashes the post-rewrite target, which matches the emitted file's hash when the gate passes.
- **Suggested fix:** None. Positive confirmation.
- **Round 3 status:** persistent (positive)

### TRA-E4-011 — Audit trail state sequence matches _KERNEL_ORDER (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / State Machine (§2.1)
- **Carry-over or new:** Carry-over from TRA-E-012 / TRA-E3-012 (still correct at HEAD `805a8f8`)
- **Evidence:** `compilation_artifacts/execution_log.json` (12 lines, valid JSON):
  ```
  execution_log: [
    "INITIALIZE_RUNTIME", "ANALYZE_DOCUMENT", "BUILD_ARTIFACTS", "EXECUTE_TRANSLATION",
    "VERIFY_OUTPUT", "REPAIR_IF_NEEDED", "AUDIT_DIAGNOSTICS", "EMIT_PAYLOAD"
  ]
  ```
  - `tra/kernel.py:64-74` (`_KERNEL_ORDER`): BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD.
  - BOOTSTRAP is the initial state, not a transition — not recorded in `execution_log`.
  - 8 post-BOOTSTRAP states present in correct order; no gaps, no duplicates, no out-of-order transitions.
- **Detail:** Forward-only transition guard (`kernel.py:173-183`) respected.
- **Suggested fix:** None. Positive confirmation.
- **Round 3 status:** persistent (positive)

### TRA-E4-012 — All 9 runtime artifacts present, exit 0 on happy path (positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic / Artifact Emission (§6.4)
- **Carry-over or new:** Carry-over from TRA-E-008 / TRA-E3-013 (still correct at HEAD `805a8f8`)
- **Evidence:** See "L4 artifact inventory" table above. All 9 artifacts present with valid JSON/YAML/JSONL. All byte sizes match R3 Track E3's reported values exactly. L4 emits everything L1-L3 emits PLUS `evidence_trace.jsonl` and `ambiguity_register.json`. The L4-only artifacts are gated by `_export_forensics` (`kernel.py:584-603`), which returns early unless `conformance_level == L4_FORENSIC` (verified by L3-only run — neither L4-only artifact present at L3).
- **Suggested fix:** None. Positive confirmation.
- **Round 3 status:** persistent (positive)

### TRA-E4-013 — Double VERIFY_OUTPUT at L3+ still undocumented; `purpose` field not added (TRA-E-010 / TRA-E3-014 carry-over)
- **Severity:** INFO (documentation)
- **Category:** Forensic / Audit Trail Structure (§7)
- **Carry-over or new:** Carry-over from TRA-E-010 / TRA-E3-014 (still applies at HEAD `805a8f8`)
- **Evidence:** L4 `audit_trace.jsonl` has 6 records (2× VERIFY_OUTPUT); L1/L2 would have 5 (1× VERIFY_OUTPUT). The 6th record is from the L3 gate (`kernel.py:291`).
  - `audit_trace.jsonl` seq=4 VERIFY_OUTPUT `artifact_snapshot={}`, `purpose=None`
  - `audit_trace.jsonl` seq=5 VERIFY_OUTPUT `artifact_snapshot={}`, `purpose=None`
  - No `purpose` field on either VERIFY_OUTPUT record (R3 Track E3 suggested adding `{"purpose": "L3_gate"}` to seq=5).
- **Detail:** At L3_STRICT and L4_FORENSIC, `verify_output` is called twice:
  1. `kernel.py:264` — initial diagnostics for the repair loop
  2. `kernel.py:291` — final L3 gate check after the repair loop and after `_rewrite_anchors`
  Both calls append a `VERIFY_OUTPUT` audit record. The `execution_log.json` records only one VERIFY_OUTPUT state transition. The double record is an ISA-level artifact and is still undocumented in user-facing SKILL.md.
- **Suggested fix:** Add a `purpose` field to the second VERIFY_OUTPUT record (e.g., `{"purpose": "L3_gate"}`) to distinguish it from the initial verify. Document in the audit trail schema that L3+ runs produce two VERIFY_OUTPUT records.
- **Round 3 status:** persistent

### TRA-E4-014 — TRA-093 false-positive BROKEN_LINK now FIXED; CJK heading + CJK link translation publishes with exit 0 (positive)
- **Severity:** INFO (positive confirmation — resolution of R3 BLOCKING)
- **Category:** Forensic / Link Rewriting + L3 Gate Interaction (§6.4 / §8)
- **Carry-over or new:** Resolution of Round 3 TRA-E3-003 BLOCKING via TRA-093 fix (commit `3c38f78`)
- **Evidence:** Probe — input `# 系统成立\n\nSee [the system](#系统成立) for details.\n` run at L4:
  - Exit code: **0** (was exit 1 in R3)
  - Output:
    ```
    # The system is Confirmed

    See [the system](#the-system-is-confirmed) for details.
    ```
  - `compilation_artifacts/ambiguity_register.json`: `[]` (was `["BROKEN_LINK:..."]` in R3)
  - The link IS valid: heading `# 系统成立` translates to `# The system is Confirmed` (slug `the-system-is-confirmed`), and the link target `#系统成立` is correctly rewritten to `#the-system-is-confirmed` — pointing at the translated heading.
  - `tra/anchor.py:139-146` (`is_translated_slug()` method added by TRA-093 fix — the registry now recognizes translated slugs as valid link targets, not just original slugs).
  - `tests/test_outstanding_findings.py::TestTRA093BrokenLinkFalsePositive` PASS (2/2 tests per R4 baseline).
- **Detail:** Round 3's TRA-E3-003 BLOCKING (false-positive BROKEN_LINK blocked publication of valid CJK-heading + CJK-link translations) is fully resolved. The TRA-093 fix added `is_translated_slug()` to `anchor.py`, allowing the link-rewrite path to recognize translated slugs as valid link targets. Documents containing the pattern `# <CJK glossary term>` followed by `[link](#<same CJK term>)` now publish correctly at L3/L4.
- **Suggested fix:** None. Positive confirmation — R3 BLOCKING resolved.
- **Round 3 status:** fixed (BLOCKING → INFO positive)

### TRA-E4-015 — `style_profile.yaml` undocumented in SKILL.md §4 (NEW finding)
- **Severity:** INFO
- **Category:** Documentation / Artifact Inventory (§4 CLI usage)
- **Carry-over or new:** **NEW** (not flagged by R3 Track E3; present at R3 too but not surfaced)
- **Evidence:**
  - `SKILL.md:145-147` (§4 `translate` — artifact list):
    > Writes the translated markdown **plus** runtime artifacts (glossary, entity table, structural map, execution log, repair history, audit trace). At L4 it additionally writes `evidence_trace.jsonl` and `ambiguity_register.json`.
  - This lists 8 artifacts: glossary, entity table, structural map, execution log, repair history, audit trace + L4 additions (evidence_trace, ambiguity_register).
  - **Missing**: `style_profile.yaml` (the 9th runtime artifact).
  - `tra/kernel.py:537` (`style_path = base / "style_profile.yaml"` — written by `_export_artifacts`).
  - `tra/kernel.py:562-569` (`style_path.write_text(yaml.safe_dump(self.ctx.style_profile.model_dump(), ...))`).
  - `tests/test_e2e_to_translate.py:189-196` — test `expected_files` list correctly includes `"style_profile.yaml"`.
  - `tests/test_e2e_to_translate.py:15-16` — test docstring correctly lists `style_profile` in the runtime artifacts enumeration.
  - `tests/test_kernel.py:63` — `assert (arts / "style_profile.yaml").exists()`.
  - `tests/run_e2e_translation.py:126` — also lists `"style_profile.yaml"`.
- **Detail:** The user-facing SKILL.md §4 docs enumerate 8 artifacts but the engine emits 9 at L4. The missing `style_profile.yaml` is correctly tested (3 test files reference it) but is invisible to a user reading SKILL.md §4 — they would be surprised when an unlisted file appears in `compilation_artifacts/`. This documentation gap was present at R3 too but R3 Track E3 did not flag it.
- **Suggested fix:** Add `style profile` to the parenthetical artifact list in `SKILL.md:145-147`:
  > Writes the translated markdown **plus** runtime artifacts (glossary, entity table, structural map, **style profile**, execution log, repair history, audit trace). At L4 it additionally writes `evidence_trace.jsonl` and `ambiguity_register.json`.
- **Round 3 status:** new

## Round 3 Track E3 carry-over status matrix

| Round 3 ID | Title | Round 4 status |
|---|---|---|
| TRA-E3-001 | Evidence trace orphan lines persist | **persistent** (TRA-E4-001) |
| TRA-E3-002 | UnknownTerm still never raised | **persistent** (TRA-E4-002) |
| TRA-E3-003 | False-positive BROKEN_LINK BLOCKS publication (BLOCKING) | **fixed** (TRA-E4-014) |
| TRA-E3-004 | Empty source recovery severity still WARNING | **persistent** (TRA-E4-003) |
| TRA-E3-005 | RepairAttempt.segment_index always 0 | **persistent** (TRA-E4-004) |
| TRA-E3-006 | HITL path still unreachable through CLI | **persistent** (TRA-E4-005) |
| TRA-E3-007 | Byte-reproducibility confirmed (positive) | **persistent** (TRA-E4-006) |
| TRA-E3-008 | TRA-071 BROKEN_MARKDOWN reachable (positive) | **persistent** (TRA-E4-007) |
| TRA-E3-009 | TRA-036 L3 gate blocks empty source (positive) | **persistent** (TRA-E4-008) |
| TRA-E3-010 | TRA-037 L3 gate checks unresolved_ambiguities (positive) | **persistent** (TRA-E4-009) |
| TRA-E3-011 | TRA-037 link rewrite hash matches emitted (positive) | **persistent** (TRA-E4-010) |
| TRA-E3-012 | Audit trail state sequence matches _KERNEL_ORDER (positive) | **persistent** (TRA-E4-011) |
| TRA-E3-013 | All 9 artifacts present, exit 0 (positive) | **persistent** (TRA-E4-012) |
| TRA-E3-014 | Double VERIFY_OUTPUT at L3+ (documentation) | **persistent** (TRA-E4-013) |

**Round 4 net delta vs R3 Track E3:** 1 BLOCKING resolved (TRA-E3-003 → TRA-E4-014 positive); 1 new INFO finding (TRA-E4-015). No new BLOCKING. No new WARNING. No regressions.

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# 1. e2e pytest suite (12 tests)
python -m pytest tests/test_e2e_to_translate.py -v
# → 12 passed in 0.32s

# 2. Manual e2e script
python e2e_test.py
# → VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics (6 audit records, BLOCKING=0 WARNING=0)

# 3. Full test suite (sanity check, matches Track D4's count)
python -m pytest tests/
# → 199 passed in 1.25s

# 4. L4 happy-path translation (isolated config)
mkdir -p /tmp/e4_work
cat > /tmp/e4_work/config.yaml <<'EOF'
language_pair: "ZH -> EN"
domain: "Security Advisory"
conformance_level: "L4_FORENSIC"
model_endpoint: "openai/gpt-4o-mini"
model_version: "2024-07-18"
base_dir: "/tmp/e4_work"
cache: {enabled: true, directory: "/tmp/e4_work/cache"}
repair: {max_retries: 3}
artifacts:
  compilation_dir: "/tmp/e4_work/compilation_artifacts"
  audit_trace: "/tmp/e4_work/audit_trace.jsonl"
EOF

rm -rf /tmp/e4_work/cache /tmp/e4_work/compilation_artifacts /tmp/e4_work/audit_trace.jsonl
python -m tra_cli --config /tmp/e4_work/config.yaml translate examples/security_advisory_zh.md --level L4 -o /tmp/l4_run1.md
# → exit 0; 8 artifacts in compilation_artifacts/ + 1 audit_trace.jsonl at base_dir = 9 total

# 5. Byte-reproducibility (TRA-013) — 2 cold-cache runs
rm -rf /tmp/e4_work/cache /tmp/e4_work/compilation_artifacts /tmp/e4_work/audit_trace.jsonl
python -m tra_cli --config /tmp/e4_work/config.yaml translate examples/security_advisory_zh.md --level L4 -o /tmp/l4_run1.md
sha256sum /tmp/l4_run1.md /tmp/e4_work/audit_trace.jsonl /tmp/e4_work/compilation_artifacts/evidence_trace.jsonl /tmp/e4_work/compilation_artifacts/repair_history.jsonl /tmp/e4_work/compilation_artifacts/ambiguity_register.json /tmp/e4_work/compilation_artifacts/execution_log.json > /tmp/run1_hashes.txt

rm -rf /tmp/e4_work/cache /tmp/e4_work/compilation_artifacts /tmp/e4_work/audit_trace.jsonl
python -m tra_cli --config /tmp/e4_work/config.yaml translate examples/security_advisory_zh.md --level L4 -o /tmp/l4_run2.md
sha256sum /tmp/l4_run2.md /tmp/e4_work/audit_trace.jsonl /tmp/e4_work/compilation_artifacts/evidence_trace.jsonl /tmp/e4_work/compilation_artifacts/repair_history.jsonl /tmp/e4_work/compilation_artifacts/ambiguity_register.json /tmp/e4_work/compilation_artifacts/execution_log.json > /tmp/run2_hashes.txt

diff <(awk '{print $1}' /tmp/run1_hashes.txt) <(awk '{print $1}' /tmp/run2_hashes.txt)
# → no diff (all 6 hashes match)

# 6. Probe 1-6 (per R3 Track E3 methodology):
python -m tra_cli validate examples/security_advisory_zh.md /tmp/l4_run1.md --level L3
# → PASS: candidate meets the conformance gate. (exit 0)

# 7. TRA-093 verification (was BLOCKING in R3):
cat > /tmp/e4_probe/cjk_link.md <<'EOF'
# 系统成立

See [the system](#系统成立) for details.
EOF
python -m tra_cli --config /tmp/e4_work/config.yaml translate /tmp/e4_probe/cjk_link.md --level L4 -o /tmp/e4_probe/cjk_link_out.md
# → exit 0 (was exit 1 in R3); output publishes correctly with translated slug link

# 8. TRA-037 hash-match verification (Probe 14):
python -c "
import hashlib, json
target = open('/tmp/l4_run1.md').read()
print('emitted sha256[:16]:', hashlib.sha256(target.encode()).hexdigest()[:16])
recs = [json.loads(l) for l in open('/tmp/e4_work/audit_trace.jsonl') if l.strip()]
print('seq=4 input_hash:', [r for r in recs if r['isa_instruction']=='VERIFY_OUTPUT'][0]['input_hash'])
print('seq=5 input_hash:', [r for r in recs if r['isa_instruction']=='VERIFY_OUTPUT'][1]['input_hash'])
"
# → emitted sha256[:16]: 225d5eded0c4a252 / seq=4: 225d5eded0c4a252 / seq=5: 225d5eded0c4a252 (MATCH)

# 9. Artifact validity check (Probe 12/13):
python -c "
import json, yaml
for n in ['glossary.yaml','entity_table.yaml','style_profile.yaml']:
    yaml.safe_load(open(f'/tmp/e4_work/compilation_artifacts/{n}'))
for n in ['structural_map.json','execution_log.json','ambiguity_register.json']:
    json.load(open(f'/tmp/e4_work/compilation_artifacts/{n}'))
for n in ['repair_history.jsonl','evidence_trace.jsonl']:
    [json.loads(l) for l in open(f'/tmp/e4_work/compilation_artifacts/{n}') if l.strip()]
[json.loads(l) for l in open('/tmp/e4_work/audit_trace.jsonl') if l.strip()]
print('all 9 artifacts valid (YAML/JSON/JSONL)')
"
# → all 9 artifacts valid (YAML/JSON/JSONL)

# 10. L3-vs-L4 artifact gating check:
python -m tra_cli --config /tmp/e4_work_l3/config.yaml translate examples/security_advisory_zh.md --level L3 -o /tmp/l3_run.md
ls /tmp/e4_work_l3/compilation_artifacts/
# → 6 artifacts (no evidence_trace.jsonl, no ambiguity_register.json) — correct L4-only gating
```

## Conclusion

The L4 forensic pipeline at HEAD `805a8f8` is **healthy and byte-stable**. All 199 tests pass (12 in the e2e suite, matching Track D4's count). The manual `e2e_test.py` reports `L3 CONFORMANT — zero BLOCKING diagnostics`. The L4 translate command exits 0 and produces all 9 expected runtime artifacts with valid YAML/JSON/JSONL content. The 6 R3 Track E3 forensic probes all return their expected verdicts (4 PASS, 2 PERSIST as documented consequences of TRA-001 partial / TRA-038 partial).

**TRA-013 byte-reproducibility HOLDS** — independently re-verified across 2 cold-cache runs, all 6 sha256 hashes match (audit_trace = `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797`; evidence_trace = `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4`; target = `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f`). These hashes reproduce Track B4's reported values exactly (independent verification, not trusting B4's claim) and also match R3 Track E3's reported values exactly — meaning the L4 output is byte-identical between HEAD `b783745` and HEAD `805a8f8`. The TRA-037 hash-chain integrity fix holds: both VERIFY_OUTPUT records' `input_hash` matches the emitted target's `sha256[:16]`.

**The single R3 BLOCKING (TRA-E3-003) is RESOLVED.** TRA-093's `is_translated_slug()` method (commit `3c38f78`) allows the link-rewrite path to recognize translated slugs as valid link targets, so documents containing `# <CJK glossary term>` followed by `[link](#<same CJK term>)` now publish correctly at L3/L4 with exit 0 and an empty `ambiguity_register.json`. The 2 WARNING findings (TRA-E4-001 orphan lines, TRA-E4-002 UnknownTerm) are persistent consequences of TRA-001 / TRA-038 partial fixes already documented in the R4 baseline — no regressions, no escalations. The 1 new INFO finding (TRA-E4-015) is a 1-line documentation gap in `SKILL.md §4` (missing `style profile` in the artifact enumeration). **No new BLOCKING, no new WARNING, no regressions.**
