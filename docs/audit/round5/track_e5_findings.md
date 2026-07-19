# Track E5 — Forensic L4 End-to-End Re-Audit (Round 5)

**HEAD audited:** `5476faf1d668b42d2a7b8c9b159ae9ee54c6e4f7`
**Methodology:** Cold-cache L4 translation of `to_translate.md`; 9-artifact inventory; byte-reproducibility probe across 2 cold-cache runs + 1 warm-cache probe; evidence-trace orphan-line inspection; ambiguity-register content audit; TRA-042 structural-verification false-positive probe; TRA-072 PolicyResolver severity-arbitration probe; HITL `--interactive` path inspection; L3 gate BROKEN_LINK probe; hash-chain integrity verification.
**Baseline:** Round 4 Track E4 (15 findings: 0 BLOCKING / 2 WARNING / 13 INFO) + 66-finding R4 master register.
**Auditor:** Track E5 agent
**Audit date:** 2026-07-18

## Summary

- Findings: **20 total** (0 BLOCKING / 2 WARNING / 18 INFO)
- Carry-over from Round 4: **15** (all 15 re-verified — 4 persistent / 1 partial-fixed / 10 positive-verified-holding)
- New findings: **5** (TRA-E5-016 cache-state non-determinism WARNING; TRA-E5-017 audit --report Mermaid+summary positive INFO; TRA-E5-018 TRA-042 false-positive-negative probe positive INFO; TRA-E5-019 TRA-072 severity arbitration positive INFO; TRA-E5-020 L4 ambiguity-register test-coverage gap INFO)
- Regressions: **0** (expected 0)
- TRA-013 byte-reproducibility (within HEAD, cold-cache): **HOLDS** — `audit_trace.jsonl`, `evidence_trace.jsonl`, output.md all byte-identical across 2 cold-cache runs.
- L3 gate (zero BLOCKING): **PASSES** on `to_translate.md` (audit --report verdict: `L3 CONFORMANT`; standalone `validate --level L3` exits 0).
- 9/9 L4 artifacts present: **YES** (all valid YAML/JSON/JSONL).
- New BLOCKING introduced by R4 Batch 2 (TRA-038/042/072): **0**.

## L4 artifact inventory (from cold-cache run on `to_translate.md`)

Command:
```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype
source .venv/bin/activate
rm -rf cache compilation_artifacts audit_trace.jsonl
python -m tra_cli translate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md --level L4 -o /tmp/r5_e5_out.md
ls compilation_artifacts/
```

| Artifact | Present | sha256 | Notes |
|---|---|---|---|
| `audit_trace.jsonl` | YES | `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` | 6 records (ANALYZE_DOCUMENT → BUILD_GLOSSARY → BUILD_ENTITY_TABLE → TRANSLATE_SEGMENT → VERIFY_OUTPUT → VERIFY_OUTPUT). Double VERIFY_OUTPUT at L3+ (TRA-E4-013 carry-over). All flags=None. seq=0..5. |
| `compilation_artifacts/glossary.yaml` | YES | `00e7c06ef9a9cb0732d318100ca2df28a1a029ebb6a7af8f3809326a51a47820` | 11 entries (成立 → Confirmed, 执行环境 → execution environment, 准确描述 → accurately describes, 高度可信 → highly credible, 可能 → may, 进行验证 → verify, 实现优化 → optimize, 提供支持 → support, 硬件隔离 → Hardware isolation, 无缝迁移 → Seamless migration, 高可用性 → High availability). |
| `compilation_artifacts/entity_table.yaml` | YES | `eb6c7f3e768f01e1f3f9133bf954c12e72eae5e1e335cc95007799f309bc63e2` | 13 entities (L1, L2, L3, L4 = product; ISA, BUILD, AUDIT, EMIT, TRA, ZH, EN, SUITE, GUIDE = acronym). All `mutable: false`, `context: source-document`. |
| `compilation_artifacts/structural_map.json` | YES | `8ba042e1ac7d31868ccd9dcdb17555c4d9af3279113e2986fc55e7ad4d8d1f2f` | 15 paragraph nodes; 0 heading nodes (source has no markdown headings — emoji-prefixed Chinese section titles are paragraphs). Matches audit `artifact_snapshot.node_count=15`. |
| `compilation_artifacts/style_profile.yaml` | YES | `a035a2e54efae7bcb736767d1bd5c78d5b1558455cc96152d328ea91bda31d53` | voice=Passive/Objective, sentence_complexity=High, epistemic_mapping (4 entries), punctuation_rules (2 entries). |
| `compilation_artifacts/execution_log.json` | YES (cold-cache) | `d72af58940e348c7c8460f910ed810399748e62325592cd95270709c2c3a96df` | 8 post-BOOTSTRAP states in canonical order. `unresolved_ambiguities`: 99 entries (9 ENTITY_AMBIGUITY + 90 UNKNOWN_TERM) on cold cache. **NOTE: warm-cache hash differs — see TRA-E5-016.** |
| `compilation_artifacts/repair_history.jsonl` | YES | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | Empty (0 bytes — clean run, no repairs triggered). |
| `compilation_artifacts/evidence_trace.jsonl` | YES (L4 only) | `8361d22d55450052089c726b62708c5b02439e154819cfc47d1c00710dd85eea` | 19 entries; 13 attributed + 6 orphans (lines 3, 11, 24, 26, 31, 33 — all emoji-prefixed section heading-like paragraphs). Matches R4 E4 orphan-pattern. |
| `compilation_artifacts/ambiguity_register.json` | YES (L4 only, cold-cache) | `b49af79d57c579c00df73f7827d281bdfe8942e3fa0081dc0adfae0a20c857f5` | 99 entries (9 ENTITY_AMBIGUITY + 90 UNKNOWN_TERM). **NOTE: warm-cache hash differs (`2b1cbb14...`, 9 entries only) — see TRA-E5-016.** |
| `/tmp/r5_e5_out.md` (output target) | YES | `5009f53fc322bb12e4e658d53de7cf46924b819892ecb604cafb127735058b19` | 1226 bytes, 33 lines. Rule path output (no LLM) — Chinese source preserved verbatim with glossary substitutions. |

All 9 expected L4 artifacts exist and parse cleanly (YAML / JSON / JSONL). All cold-cache sha256 hashes match the values reported by Track B5 (independent verification — Track B5 reported `audit_trace.jsonl=902298b3...`, `evidence_trace.jsonl=8361d22d...`, `output.md=5009f53f...`).

## Byte-reproducibility probe

Two cold-cache runs (cache directory wiped between runs):

| Run | audit_trace.jsonl sha256 | evidence_trace.jsonl sha256 | output.md sha256 | ambiguity_register.json sha256 | execution_log.json sha256 |
|---|---|---|---|---|---|
| Run 1 (cold cache) | `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` | `8361d22d55450052089c726b62708c5b02439e154819cfc47d1c00710dd85eea` | `5009f53fc322bb12e4e658d53de7cf46924b819892ecb604cafb127735058b19` | `b49af79d57c579c00df73f7827d281bdfe8942e3fa0081dc0adfae0a20c857f5` | `d72af58940e348c7c8460f910ed810399748e62325592cd95270709c2c3a96df` |
| Run 2 (cold cache) | `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` | `8361d22d55450052089c726b62708c5b02439e154819cfc47d1c00710dd85eea` | `5009f53fc322bb12e4e658d53de7cf46924b819892ecb604cafb127735058b19` | `b49af79d57c579c00df73f7827d281bdfe8942e3fa0081dc0adfae0a20c857f5` | `d72af58940e348c7c8460f910ed810399748e62325592cd95270709c2c3a96df` |
| Identical? | **YES** | **YES** | **YES** | **YES** | **YES** |
| Run 3 (warm cache, probe) | `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` | `8361d22d55450052089c726b62708c5b02439e154819cfc47d1c00710dd85eea` | `5009f53fc322bb12e4e658d53de7cf46924b819892ecb604cafb127735058b19` | `2b1cbb14e807ba5a2e369a0b9671d9bf517305c0ccf0a0a198edec7e882e43dd` | `8ec98c67984f13271dea4388d49e2075dad7d153abeb0deba9ef3ed0a4d79be6` |
| Cold vs Warm identical? | **YES** | **YES** | **YES** | **NO** (cold: 99 entries; warm: 9 entries) | **NO** (cold: 99 unresolved_ambiguities; warm: 9) |

Note: Absolute sha256 differs from R4 baseline `263b901e...` because R4 Batch 2 (TRA-038/042/072) enriched audit-trail content. The TRA-013 invariant (within-HEAD reproducibility across two cold-cache runs) HOLDS for all 5 probed artifacts.

**Anomaly surfaced by warm-cache probe (TRA-E5-016 below):** The L4-only artifacts `ambiguity_register.json` and `execution_log.json` (which embeds `unresolved_ambiguities`) are NOT stable across cache states. On a cache hit, `translate_segment` returns the cached `TranslationResult` without invoking the rule path, so the `_log_unknown_cjk` side-effect that populates `ctx.unresolved_ambiguities` with `UNKNOWN_TERM` entries is silently skipped. Track B5's TRA-013 verification did not surface this because B5 only compared `audit_trace.jsonl` / `evidence_trace.jsonl` / `output.md` (which are all stable across cache states).

## Probe results (re-running R4 Track E4's probes + new probes)

| # | Probe | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | `evidence_trace.jsonl` exists at L4 | yes | 4399 B, valid JSONL, 19 records | **PASS** |
| 2 | `ambiguity_register.json` exists at L4 | yes | 873 B (cold) / 380 B (warm), valid JSON, 99 / 9 entries | **PASS (with TRA-E5-016 caveat)** |
| 3 | `audit_trace.jsonl` zero BLOCKING | yes | 6 records, all `flags=None`, no BLOCKING | **PASS** |
| 4 | Orphan lines in `evidence_trace.jsonl` (TRA-E4-001) | yes (persistent) | 6 orphans on `to_translate.md` (lines 3, 11, 24, 26, 31, 33 — emoji-prefixed Chinese section titles); 1 orphan on `examples/security_advisory_zh.md` (line 7 — "96-core system keeps memory below <5MB at peak.") | **PERSISTS** (TRA-E5-001) |
| 5 | L3 `validate` exits 0 on conformant output | yes | `Validation level=L3_STRICT — BLOCKING=0 WARNING=0 INFO=0` / `PASS: candidate meets the conformance gate.` / exit 0 | **PASS** |
| 6 | TRA-037 L3 gate raises ConformanceFailure on BROKEN_LINK | yes (positive) | Probe with `[a nonexistent anchor](#does-not-exist)` → `ConformanceFailure: CONFORMANCE_FAILURE: 1 BROKEN_LINK entry/entries in unresolved_ambiguities` / exit 1 | **PASS** (TRA-E5-009) |
| 7 | `_rewrite_anchors` runs BEFORE L3 gate (TRA-037) | yes (positive) | `kernel.py:315` (`target = self._rewrite_anchors(target)`) precedes `kernel.py:323-349` (L3 gate) | **PASS** (TRA-E5-009) |
| 8 | Hash chain integrity (audit_trace VERIFY_OUTPUT input_hash == emitted target sha256[:16]) | yes (positive) | seq=4 VERIFY_OUTPUT `input_hash=5009f53fc322bb12`; seq=5 VERIFY_OUTPUT `input_hash=5009f53fc322bb12`; emitted `/tmp/r5_e5_out.md` `sha256[:16]=5009f53fc322bb12` — **MATCH on both VERIFY_OUTPUT records** | **PASS** (TRA-E5-010) |
| 9 | TRA-042 false-positive probe (table input) | no false-positive BLOCKING | `# H\n\n\| Col1 \| Col2 \|\n\|---\|---\|\n\| a \| b \|\n\nSome text.\n` → exit 0, 6 audit records, no flags | **PASS** (TRA-E5-018) |
| 10 | TRA-042 true-positive probe (list mismatch) | BLOCKING raised + L3 gate rejects | Source `# H\n\n- a\n- b\n- c\n`, target `# H\n\n- a\n- b\n` → 1 BLOCKING diagnostic (`List item count mismatch after translation`); L4 run raises `ConformanceFailure: CONFORMANCE_FAILURE: 1 BLOCKING diagnostic(s) remain after repair loop` | **PASS** (TRA-E5-018) |
| 11 | TRA-072 PolicyResolver structural_severity (STRUCTURAL_INTEGRITY vs TARGET_FLUENCY) | BLOCKING (default policy) | `_POLICY_RESOLVER.wins(STRUCTURAL_INTEGRITY, TARGET_FLUENCY)` returns True → `structural_severity = Severity.BLOCKING` (`isa.py:792-798`) | **PASS** (TRA-E5-019) |
| 12 | HITL `--interactive` flag exists + kernel pauses on Unrecoverable | yes (code intact) | `tra_cli.py:92-97` flag; `tra_cli.py:139` passes `interactive=interactive` to TRAKernel; `kernel.py:521-538` `if self.interactive:` block calls `review_decision` from `tra.hitl` with `choices=["accept", "override", "skip"]`. **BUT** no test exercises this path (`rg "interactive=True" tests/` → 0 hits, confirmed by Track D5 TRA-D5-007); Unrecoverable is unreachable via normal CLI input on canonical ZH-EN glossary. | **PERSISTS** (TRA-E5-005, cross-ref D5-007) |
| 13 | `audit --report` Mermaid state-transition diagram | yes (positive) | `tra_cli.py:234-243` reads `compilation_artifacts/execution_log.json`, calls `mermaid_state_diagram(log)`; output is a valid `flowchart LR` Mermaid diagram with 9 nodes (BOOTSTRAP through EMIT_PAYLOAD) + 7 edges (INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD) | **PASS** (TRA-E5-017) |
| 14 | `audit --report` conformance summary | yes (positive) | `tra_cli.py:222-233` calls `summarize_audit(trail)`; prints `total records: 6`, `by severity: {}` (no flags raised), `by instruction: {ANALYZE_DOCUMENT: 1, BUILD_GLOSSARY: 1, BUILD_ENTITY_TABLE: 1, TRANSLATE_SEGMENT: 1, VERIFY_OUTPUT: 2}`, `verdict: L3 CONFORMANT` | **PASS** (TRA-E5-017) |
| 15 | Manual `e2e_test.py` verdict | L3 CONFORMANT | `VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics` (6 audit records, BLOCKING=0 WARNING=0) | **PASS** |
| 16 | Full pytest suite at HEAD | 228 passed | `228 passed in 1.16s` | **PASS** |
| 17 | e2e pytest suite | 12/12 pass | `12 passed in 0.22s` | **PASS** |

## Findings

### TRA-E5-001 — Evidence trace orphan lines persist (TRA-E4-001 carry-over)
- **Severity:** WARNING
- **Category:** Forensic L4 / Evidence Trace Integrity (§6.4.1)
- **Finding type:** issue
- **Evidence:**
  - `compilation_artifacts/evidence_trace.jsonl` lines 3, 11, 24, 26, 31, 33 from L4 run on `to_translate.md` (cold-cache):
    ```json
    {"line": 3, "text": "🧠 核心架构: 将翻译流程\"虚拟机化\"", "evidence_ids": [], "attributed": false}
    {"line": 11, "text": "🧩 模块化与策略引擎", "evidence_ids": [], "attributed": false}
    {"line": 24, "text": "📊 配套的评估与认证体系", "evidence_ids": [], "attributed": false}
    {"line": 26, "text": "项目提供了完整的配套文档: ", "evidence_ids": [], "attributed": false}
    {"line": 31, "text": "💎 总结与展望", "evidence_ids": [], "attributed": false}
    {"line": 33, "text": "总的来说, Translation-Runtime-Architecture 是一份极具远见和严谨性的", "evidence_ids": [], "attributed": false}
    ```
  - `tra/reporting.py:86`: `hits = [r.id for r in records if r.target_span and r.target_span in line]` — substring-containment heuristic.
  - Cross-verification on `examples/security_advisory_zh.md` (R4 baseline file): orphan line 7 `96-core system keeps memory below <5MB at peak.` persists at HEAD `5476faf` — same as R4 E4.
- **Detail:** The substring-containment heuristic in `line_by_line_trace` cannot match any evidence record's `target_span` to a line containing only emoji + Chinese section title text (no translated glossary terms or entity names appear in those lines). Result: `evidence_ids: []`, `attributed: false` — orphan lines with no evidence attribution. An L4 forensic reviewer cannot trace these output fragments back to any decision. Pending TRA-001 segment-level translation. R4 Batch 2 (TRA-038/042/072) did NOT change this behavior — the orphan pattern is identical to R4.
- **Suggested fix:** Implement structural mapping (output line N → segment M → evidence chain). Until TRA-001 lands, embed evidence ID references as HTML comments during translation, then strip after trace construction.
- **Round 4 status:** persistent (TRA-E4-001 → TRA-E5-001)

### TRA-E5-002 — UnknownTerm now logged to ambiguity register via direct call (TRA-E4-002 carry-over, PARTIAL-FIXED)
- **Severity:** INFO
- **Category:** Forensic L4 / Exception Recovery (§6 UNKNOWN_TERM)
- **Finding type:** issue
- **Evidence:**
  - Cold-cache L4 run on `to_translate.md`: `compilation_artifacts/ambiguity_register.json` contains 90 `UNKNOWN_TERM:` entries (e.g., `"UNKNOWN_TERM: 在详细审阅了 — Term not in glossary or domain module; source preserved."`).
  - `tra/isa.py:572-573`: `if unresolved_ambiguities is not None: _log_unknown_cjk(out, glossary, entities, unresolved_ambiguities)` — wired into the rule path.
  - `tra/isa.py:687-723` (`_log_unknown_cjk`): scans `out` for CJK runs not in glossary/entities/epistemic lexicon, calls `recover_unknown_term(token, unresolved_ambiguities)`.
  - `tra/isa.py:723`: `recover_unknown_term(token, unresolved_ambiguities)` — direct call, NOT a `raise UnknownTerm(...)`.
  - Audit trail: 6 records, **0 EXCEPTION_HANDLER records** — confirmed.
- **Detail:** Round 4 TRA-E4-002 (WARNING: "UnknownTerm still never raised; unknown CJK terms pass through silently") is **partially remediated** by R4 Batch 2 commit `d95c36d`. Unknown CJK tokens ARE now logged to `unresolved_ambiguities` (and therefore appear in `ambiguity_register.json` at L4). The terms still pass through the rule path untranslated and `verify_output` does not flag them (non-halting), but the L4 forensic trail DOES capture the decision points — addressing the original "register is empty despite the unknown term" concern. **However**, the logging bypasses the kernel's `_recover` path (no `EXCEPTION_HANDLER` audit record is emitted — see TRA-B5-018 cross-listing), and the side-effect is cache-state-dependent (see TRA-E5-016). Downgraded WARNING → INFO because the primary L4 forensic gap (silent pass-through with no register entry) is closed on cold-cache runs.
- **Suggested fix:** Route UnknownTerm through `raise UnknownTerm(...)` → `_recover` so an `EXCEPTION_HANDLER` audit record is emitted (closes TRA-B5-018). Decouple `_log_unknown_cjk` from `translate_segment`'s rule-path execution so it runs on cache hits too (closes TRA-E5-016).
- **Round 4 status:** partial-fixed (TRA-E4-002 → TRA-E5-002)

### TRA-E5-003 — Empty source recovery severity still WARNING (TRA-E4-003 carry-over)
- **Severity:** INFO
- **Category:** Forensic L4 / Exception Recovery (§6 EMPTY_SOURCE)
- **Finding type:** issue
- **Evidence:**
  - `tra/kernel.py:262-271`: raises `ConformanceFailure` at L3+ on analyze failure (behavioral fix correct).
  - `tra/recovery.py:191-197`: `route_exception` default fall-through for `TRAException` base class: `Severity.WARNING` + `RecoveryAction.PRESERVE_SOURCE`.
  - `tra/isa.py:89-90`: `EMPTY_SOURCE` raises `TRAException("EMPTY_SOURCE")`, base class — not a dedicated `BrokenMarkdown` or `EmptySource` subclass.
- **Detail:** Identical to R4. Behavioral fix correct (L3 gate compensates by raising ConformanceFailure), but the EXCEPTION_HANDLER audit record's `severity` field is still `WARNING` (not BLOCKING) and `code` is still `TRA_ERROR` (not `EMPTY_SOURCE`), because `EMPTY_SOURCE` raises the base `TRAException` which falls through to the `route_exception` default. The spec §6 EMPTY_SOURCE recovery procedure mandates BLOCKING severity. R4 Batch 2 did not touch this code path.
- **Suggested fix:** Either (a) raise `BrokenMarkdown` directly from `analyze_document` when source is empty, or (b) add a dedicated `EmptySource` exception subclass with a `route_exception` branch returning `Severity.BLOCKING` + `RecoveryAction.HALT`.
- **Round 4 status:** persistent (TRA-E4-003 → TRA-E5-003)

### TRA-E5-004 — RepairAttempt.segment_index is always 0 (TRA-E4-004 carry-over)
- **Severity:** INFO
- **Category:** Forensic L4 / Repair History (§6.4.2)
- **Finding type:** issue
- **Evidence:**
  - `tra/isa.py:621` (`segment_index: int = 0` default in `repair_segment` signature).
  - `tra/kernel.py:505-514`: kernel calls `repair_segment(...)` without passing `segment_index`.
  - L4 cold-cache run on `to_translate.md`: `repair_history.jsonl` is empty (0 bytes — clean run, no repairs triggered).
- **Detail:** Identical to R4. Whole-doc translation model (TRA-001 partial) treats the entire document as one segment. Every `RepairAttempt` in `repair_history.jsonl` has `segment_index: 0` regardless of which part of the document was repaired. An L4 forensic reviewer would expect `segment_index` to identify the leaf-node segment, enabling targeted review. R4 Batch 2 did not touch this code path.
- **Suggested fix:** When TRA-001 segment-level translation is implemented, pass the actual leaf-node index to `repair_segment`. Until then, document the limitation in the `RepairAttempt.segment_index` docstring.
- **Round 4 status:** persistent (TRA-E4-004 → TRA-E5-004)

### TRA-E5-005 — HITL path still unreachable through normal CLI input (TRA-E4-005 carry-over)
- **Severity:** INFO
- **Category:** Forensic L4 / HITL (§6.2)
- **Finding type:** issue
- **Evidence:**
  - `tra_cli.py:92-97`: `--interactive` flag exists.
  - `tra_cli.py:139`: `kernel = TRAKernel(cfg, registry=registry, interactive=interactive)` (correctly threaded).
  - `kernel.py:521-538`: `if self.interactive:` block calls `format_unrecoverable` + `review_decision` from `tra.hitl`.
  - `tra/hitl.py:24-59` (`review_decision`): `Prompt.ask("Resolution", choices=["accept", "override", "skip"], default="skip")`.
  - `rg "raise Unrecoverable" tra/` → only 2 raise sites:
    - `tra/isa.py:666` — structural repair max retries (`attempt >= max_retries`)
    - `tra/isa.py:678` — repair introduces new BLOCKING
  - Both raise paths require pathological input that the rule-based translation path cannot produce on the canonical ZH-EN glossary (all canonical targets are safe English terms that don't trigger forbidden/terminology checks).
  - Cross-ref Track D5 TRA-D5-007 (persistent): `rg "interactive=True" tests/` → 0 matches. CLI `--interactive` flag NOT tested via CliRunner.
- **Detail:** Identical to R4. The HITL path fires correctly when `Unrecoverable` is raised (R3 Probe 7 confirmed), but `Unrecoverable` cannot be triggered through normal CLI input at L3/L4 with the rule-based translation path. Testability gap. R4 Batch 2 did not add a `--force-unrecoverable` debug flag or a CLI integration test.
- **Suggested fix:** Add a `--force-unrecoverable` debug flag that injects a structural BLOCKING to exercise the HITL path in integration tests. Add a CLI integration test that patches `repair_segment` to raise `Unrecoverable` and feeds `--interactive` input via stdin (CliRunner).
- **Round 4 status:** persistent (TRA-E4-005 → TRA-E5-005, cross-ref D5-007)

### TRA-E5-006 — Byte-reproducibility confirmed (TRA-E4-006 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Reproducibility (§6.4 / TRA-013)
- **Finding type:** positive_verification
- **Evidence:** See "Byte-reproducibility probe" table above. All 5 probed artifacts byte-identical across 2 cold-cache runs:
  - `audit_trace.jsonl` sha256 = `902298b38cf854e71f21ed3bcb6c4c21bd0e0b44fae05b03cef3eacfbd3ed142` × 2 runs
  - `evidence_trace.jsonl` sha256 = `8361d22d55450052089c726b62708c5b02439e154819cfc47d1c00710dd85eea` × 2 runs
  - output.md sha256 = `5009f53fc322bb12e4e658d53de7cf46924b819892ecb604cafb127735058b19` × 2 runs
  - `ambiguity_register.json` sha256 = `b49af79d57c579c00df73f7827d281bdfe8942e3fa0081dc0adfae0a20c857f5` × 2 runs (cold-cache only — see TRA-E5-016 for warm-cache caveat)
  - `execution_log.json` sha256 = `d72af58940e348c7c8460f910ed810399748e62325592cd95270709c2c3a96df` × 2 runs (cold-cache only — see TRA-E5-016)
- **Detail:** Deterministic clock (`kernel.py:193-207`, `seed = self._source_hash_seed or "0" * 16`) and content-addressed evidence IDs (`diagnostics.py:45-63`, `ev_{sha256(canonical_record)[:12]}`) produce stable timestamps and IDs. The cache stores translation results with their evidence_ids; the cache-hit path emits the same audit record with the same evidence_ids. Absolute sha256 differs from R4 baseline `263b901e...` because R4 Batch 2 (TRA-038/042/072) enriched audit-trail content; the TRA-013 invariant (within-HEAD reproducibility) HOLDS. **Independent re-verification of Track B5's TRA-013 claim** — Track B5 reported the same `audit_trace` / `evidence_trace` / `output.md` hashes (reproduced here without relying on B5's result).
- **Suggested fix:** None. Positive confirmation. (Note: the warm-cache non-determinism in `ambiguity_register.json` and `execution_log.json` is a separate issue — TRA-E5-016 — and does not affect the cold-cache TRA-013 invariant.)
- **Round 4 status:** persistent (positive) (TRA-E4-006 → TRA-E5-006)

### TRA-E5-007 — TRA-071 BROKEN_MARKDOWN still reachable; unclosed fence raises it correctly (TRA-E4-007 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Exception Recovery (§6 BROKEN_MARKDOWN)
- **Finding type:** positive_verification
- **Evidence:** R5 baseline TRA-071 verified. `tra/isa.py:92-97` (`BrokenMarkdown` wrapper around `build_structural_map`). R5 test suite: `tests/test_tra071_broken_markdown.py` 2 tests pass (228 total pytest pass). End-to-end behavior previously confirmed by R3 Probe 2 (unclosed fence → exit 1, EXCEPTION_HANDLER with BLOCKING flag).
- **Detail:** TRA-071 added explicit structural validation in `build_structural_map` that raises `BrokenMarkdown` for genuinely broken markdown. The exception is correctly routed through `_recover` → `recover_broken_markdown` → `Severity.BLOCKING` + `RecoveryAction.HALT`. The audit trail records `code='BROKEN_MARKDOWN'` and `severity='BLOCKING'` as the spec mandates.
- **Suggested fix:** None. Positive confirmation.
- **Round 4 status:** persistent (positive) (TRA-E4-007 → TRA-E5-007)

### TRA-E5-008 — TRA-036 L3 gate still blocks empty source (TRA-E4-008 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / L3 Gate (§8)
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/kernel.py:262-271` (TRA-036 fix: `if self.config.conformance_level in (L3_STRICT, L4_FORENSIC): raise ConformanceFailure(...)`).
  - `tests/test_outstanding_findings.py::TestTRA036AnalyzeFailureL3Gate` — regression test passes (228 total pytest pass).
- **Detail:** The early `return ""` (TRA-004 fix) is replaced with `raise ConformanceFailure(...)` at L3+. The L3 gate is no longer bypassed on analyze failure. A non-conformant (empty) output is no longer silently published as "translated".
- **Suggested fix:** None (behavioral fix correct). See TRA-E5-003 for the residual severity-classification issue.
- **Round 4 status:** persistent (positive) (TRA-E4-008 → TRA-E5-008)

### TRA-E5-009 — TRA-037 L3 gate still checks unresolved_ambiguities for BROKEN_LINK; _rewrite_anchors runs BEFORE the gate (TRA-E4-009 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / L3 Gate (§8)
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/kernel.py:315` (`target = self._rewrite_anchors(target)` — runs BEFORE the L3 gate).
  - `tra/kernel.py:323-349` (L3 gate): `final_diags = verify_output(target, src, self.ctx, self.audit)`; `final_blocking = [d for d in final_diags if d.severity == Severity.BLOCKING]`; `broken_links = [a for a in self.ctx.unresolved_ambiguities if "BROKEN_LINK" in a]`; `if final_blocking or broken_links: raise ConformanceFailure(...)`.
  - R5 Probe 6 (this audit): input `# Real Heading\n\nThis paragraph references [a nonexistent anchor](#does-not-exist) which should fail the L3 gate.\n` run at L4 → `ConformanceFailure: CONFORMANCE_FAILURE: 1 BROKEN_LINK entry/entries in unresolved_ambiguities — output is not L3-conformant (internal link target missing)`, exit 1.
  - `tests/test_outstanding_findings.py::TestTRA037RewriteAnchorsBeforeGate` — regression test passes (228 total pytest pass).
- **Detail:** The L3 gate correctly rejects outputs with BROKEN_LINK entries in `unresolved_ambiguities`. `_rewrite_anchors` runs at `kernel.py:315` BEFORE the L3 gate at `kernel.py:323`, so the gate sees the post-rewrite target and its associated ambiguities. Genuine broken internal links block publication at L3+.
- **Suggested fix:** None (correct behavior for genuine broken links).
- **Round 4 status:** persistent (positive) (TRA-E4-009 → TRA-E5-009)

### TRA-E5-010 — TRA-037 link rewrite hash still matches emitted target hash (TRA-E4-010 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Audit Trail Hash-Chain Integrity (§6.4)
- **Finding type:** positive_verification
- **Evidence:** L4 cold-cache run on `to_translate.md`:
  - `audit_trace.jsonl` seq=4 VERIFY_OUTPUT `input_hash=5009f53fc322bb12`
  - `audit_trace.jsonl` seq=5 VERIFY_OUTPUT `input_hash=5009f53fc322bb12`
  - Emitted `/tmp/r5_e5_out.md` `sha256[:16]=5009f53fc322bb12`
  - **MATCH=True** on both VERIFY_OUTPUT records (`to_translate.md` has no internal links, so initial-verify and L3-gate-verify hash the same target).
  - `tra/kernel.py:315` (TRA-037 fix: `_rewrite_anchors(target)` runs BEFORE the L3 gate).
- **Detail:** Round 2's TRA-E-002 BLOCKING finding (audit trail's VERIFY_OUTPUT hash was computed on pre-rewrite target while emitted target was post-rewrite) is resolved. The L3 gate's verify_output now hashes the post-rewrite target, which matches the emitted file's hash when the gate passes. Hash-chain integrity holds at HEAD `5476faf`.
- **Suggested fix:** None. Positive confirmation.
- **Round 4 status:** persistent (positive) (TRA-E4-010 → TRA-E5-010)

### TRA-E5-011 — Audit trail state sequence matches _KERNEL_ORDER (TRA-E4-011 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / State Machine (§2.1)
- **Finding type:** positive_verification
- **Evidence:** `compilation_artifacts/execution_log.json`:
  ```
  execution_log: [
    "INITIALIZE_RUNTIME", "ANALYZE_DOCUMENT", "BUILD_ARTIFACTS", "EXECUTE_TRANSLATION",
    "VERIFY_OUTPUT", "REPAIR_IF_NEEDED", "AUDIT_DIAGNOSTICS", "EMIT_PAYLOAD"
  ]
  ```
  - `tra/kernel.py:64-74` (`_KERNEL_ORDER`): BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD.
  - BOOTSTRAP is the initial state, not a transition — not recorded in `execution_log`.
  - 8 post-BOOTSTRAP states present in correct order; no gaps, no duplicates, no out-of-order transitions.
- **Detail:** Forward-only transition guard (`kernel.py:209-225`, with TRA-049 strict-`<` enforcement) respected.
- **Suggested fix:** None. Positive confirmation.
- **Round 4 status:** persistent (positive) (TRA-E4-011 → TRA-E5-011)

### TRA-E5-012 — All 9 runtime artifacts present, exit 0 on happy path (TRA-E4-012 carry-over, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Artifact Emission (§6.4)
- **Finding type:** positive_verification
- **Evidence:** See "L4 artifact inventory" table above. All 9 artifacts present with valid JSON/YAML/JSONL content. L4 emits everything L1-L3 emits PLUS `evidence_trace.jsonl` and `ambiguity_register.json`. The L4-only artifacts are gated by `_export_forensics` (`kernel.py:600-619`), which returns early unless `conformance_level == L4_FORENSIC`.
- **Detail:** The L4 artifact inventory is complete at HEAD `5476faf`. All byte sizes reasonable; all parse cleanly. The 9 artifacts include the 7 L1-L3 artifacts (`glossary.yaml`, `entity_table.yaml`, `structural_map.json`, `style_profile.yaml`, `execution_log.json`, `repair_history.jsonl`, `audit_trace.jsonl`) plus the 2 L4-only artifacts (`evidence_trace.jsonl`, `ambiguity_register.json`).
- **Suggested fix:** None. Positive confirmation.
- **Round 4 status:** persistent (positive) (TRA-E4-012 → TRA-E5-012)

### TRA-E5-013 — Double VERIFY_OUTPUT at L3+ still undocumented; `purpose` field not added (TRA-E4-013 carry-over)
- **Severity:** INFO (documentation)
- **Category:** Forensic L4 / Audit Trail Structure (§7)
- **Finding type:** issue
- **Evidence:** L4 `audit_trace.jsonl` has 6 records (2× VERIFY_OUTPUT); L1/L2 would have 5 (1× VERIFY_OUTPUT). The 6th record is from the L3 gate (`kernel.py:327`).
  - `audit_trace.jsonl` seq=4 VERIFY_OUTPUT `artifact_snapshot={}`, no `purpose` field
  - `audit_trace.jsonl` seq=5 VERIFY_OUTPUT `artifact_snapshot={}`, no `purpose` field
  - No `purpose` field on either VERIFY_OUTPUT record (R4 Track E4 suggested adding `{"purpose": "L3_gate"}` to seq=5).
- **Detail:** At L3_STRICT and L4_FORENSIC, `verify_output` is called twice:
  1. `kernel.py:300` — initial diagnostics for the repair loop
  2. `kernel.py:327` — final L3 gate check after the repair loop and after `_rewrite_anchors`
  Both calls append a `VERIFY_OUTPUT` audit record. The `execution_log.json` records only one VERIFY_OUTPUT state transition. The double record is an ISA-level artifact and is still undocumented in user-facing SKILL.md. R4 Batch 2 did not add a `purpose` field.
- **Suggested fix:** Add a `purpose` field to the second VERIFY_OUTPUT record (e.g., `{"purpose": "L3_gate"}`) to distinguish it from the initial verify. Document in the audit trail schema that L3+ runs produce two VERIFY_OUTPUT records.
- **Round 4 status:** persistent (TRA-E4-013 → TRA-E5-013)

### TRA-E5-014 — TRA-093 false-positive BROKEN_LINK still FIXED; CJK heading + CJK link translation publishes with exit 0 (TRA-E4-014 carry-over, positive)
- **Severity:** INFO (positive confirmation — resolution of R3 BLOCKING)
- **Category:** Forensic L4 / Link Rewriting + L3 Gate Interaction (§6.4 / §8)
- **Finding type:** positive_verification
- **Evidence:** R5 baseline TRA-093 verified. `tests/test_outstanding_findings.py::TestTRA093BrokenLinkFalsePositive` 2 tests pass (228 total pytest pass). `tra/anchor.py:139-146` (`is_translated_slug()` method added by TRA-093 fix).
- **Detail:** Round 3's TRA-E3-003 BLOCKING (false-positive BROKEN_LINK blocked publication of valid CJK-heading + CJK-link translations) is fully resolved. The TRA-093 fix added `is_translated_slug()` to `anchor.py`, allowing the link-rewrite path to recognize translated slugs as valid link targets. Documents containing the pattern `# <CJK glossary term>` followed by `[link](#<same CJK term>)` publish correctly at L3/L4.
- **Suggested fix:** None. Positive confirmation — R3 BLOCKING resolved.
- **Round 4 status:** persistent (positive) (TRA-E4-014 → TRA-E5-014)

### TRA-E5-015 — `style_profile.yaml` still undocumented in SKILL.md §4 (TRA-E4-015 carry-over)
- **Severity:** INFO (documentation)
- **Category:** Documentation / Artifact Inventory (§4 CLI usage)
- **Finding type:** issue
- **Evidence:**
  - `tra-prototype/SKILL.md:145-147` (§4 `translate` — artifact list):
    > Writes the translated markdown **plus** runtime artifacts (glossary, entity table, structural map, execution log, repair history, audit trace). At L4 it additionally writes `evidence_trace.jsonl` and `ambiguity_register.json`.
  - This lists 8 artifacts: glossary, entity table, structural map, execution log, repair history, audit trace + L4 additions (evidence_trace, ambiguity_register).
  - **Missing**: `style_profile.yaml` (the 9th runtime artifact).
  - `tra/kernel.py:553` (`style_path = base / "style_profile.yaml"` — written by `_export_artifacts`).
  - `tra/kernel.py:578-585` (`style_path.write_text(yaml.safe_dump(self.ctx.style_profile.model_dump(), ...))`).
  - `tests/test_e2e_to_translate.py:193` — test `expected_files` list correctly includes `"style_profile.yaml"`.
- **Detail:** The user-facing SKILL.md §4 docs enumerate 8 artifacts but the engine emits 9 at L4. The missing `style_profile.yaml` is correctly tested but is invisible to a user reading SKILL.md §4. Cross-ref Track C5's broader SKILL.md/README.md drift cluster (TRA-C5-001..013). R4 Batch 2 did not touch SKILL.md §4.
- **Suggested fix:** Add `style profile` to the parenthetical artifact list in `SKILL.md:145-147`:
  > Writes the translated markdown **plus** runtime artifacts (glossary, entity table, structural map, **style profile**, execution log, repair history, audit trace). At L4 it additionally writes `evidence_trace.jsonl` and `ambiguity_register.json`.
- **Round 4 status:** persistent (TRA-E4-015 → TRA-E5-015, cross-ref C5 doc-refresh cluster)

### TRA-E5-016 — L4 ambiguity_register.json + execution_log.json unresolved_ambiguities are non-deterministic across cache states (NEW, WARNING)
- **Severity:** WARNING
- **Category:** Forensic L4 / Audit Trail Reproducibility (§6.4 / TRA-013 edge case)
- **Finding type:** issue
- **Evidence:**
  - Cold-cache L4 run on `to_translate.md`: `ambiguity_register.json` has 99 entries (9 `ENTITY_AMBIGUITY` + 90 `UNKNOWN_TERM`), sha256 = `b49af79d57c579c00df73f7827d281bdfe8942e3fa0081dc0adfae0a20c857f5`.
  - Warm-cache L4 run on `to_translate.md` (same source, cache from cold-cache run reused): `ambiguity_register.json` has 9 entries (9 `ENTITY_AMBIGUITY` only, 0 `UNKNOWN_TERM`), sha256 = `2b1cbb14e807ba5a2e369a0b9671d9bf517305c0ccf0a0a198edec7e882e43dd`.
  - Same pattern in `execution_log.json`'s `unresolved_ambiguities` field: cold-cache 99 entries (sha256 `d72af589...`), warm-cache 9 entries (sha256 `8ec98c67...`).
  - `audit_trace.jsonl`, `evidence_trace.jsonl`, output.md: byte-identical across cold and warm cache (sha256 `902298b3...`, `8361d22d...`, `5009f53f...` respectively).
  - `tra/isa.py:426-429` (translate_segment cache-hit path):
    ```python
    cached = cache.get(cache_key)
    if cached is not None:
        audit.append("TRANSLATE_SEGMENT", cache_key, cached.evidence_ids)
        return cached
    ```
    The cache hit returns the cached `TranslationResult` **without** invoking `_rule_translate` → `_log_unknown_cjk`. The side-effect of populating `ctx.unresolved_ambiguities` with `UNKNOWN_TERM` entries is silently skipped.
  - `tra/isa.py:508-514` (rule-path invocation, only on cache miss):
    ```python
    else:
        target, basis = _rule_translate(
            source_segment, glossary, entities,
            unresolved_ambiguities=ctx.unresolved_ambiguities,
        )
    ```
  - `tra/isa.py:572-573` (`_log_unknown_cjk` call inside `_rule_translate`): only fires when `_rule_translate` is invoked (i.e., cache miss).
  - `tra/kernel.py:586-595` (`_export_artifacts` writes `execution_log.json` with `unresolved_ambiguities` field from `ctx.unresolved_ambiguities`).
  - `tra/kernel.py:615-619` (`_export_forensics` writes `ambiguity_register.json` from `ctx.unresolved_ambiguities`).
  - Track B5's TRA-013 verification (worklog lines 142-143) only probed `audit_trace.jsonl`, `evidence_trace.jsonl`, output.md — **did not probe `ambiguity_register.json` or `execution_log.json` across cache states**.
- **Detail:** R4 Batch 2 commit `d95c36d` (TRA-038) wired `_log_unknown_cjk` into `_rule_translate` to populate `ctx.unresolved_ambiguities` with `UNKNOWN_TERM` entries for forensic visibility. **However**, this side-effect is only invoked on cache miss. On cache hit, `translate_segment` returns the cached `TranslationResult` early (line 428-429) without invoking `_rule_translate`, so `_log_unknown_cjk` never runs. The result is that two L4 translations of the same source produce **different L4 forensic artifacts** depending on whether the cache was warm or cold:
  - Cold cache: 99 ambiguity entries → richer forensic trail.
  - Warm cache: 9 ambiguity entries → impoverished forensic trail (missing 90 UNKNOWN_TERM decision points).
  
  The audit trail (`audit_trace.jsonl`) is unaffected because the `TRANSLATE_SEGMENT` audit record's content (evidence_ids) is the same on cache hit and miss — the cache stores the evidence_ids, not the side-effects. But the L4-only artifacts `ambiguity_register.json` and `execution_log.json` (which both serialize `ctx.unresolved_ambiguities`) vary by cache state.
  
  This is a real L4 forensic integrity gap: an auditor running the same translation twice (once cold, once warm) would see different `ambiguity_register.json` content. The L3 gate does NOT catch this because `unresolved_ambiguities` is only consulted for `BROKEN_LINK` entries (TRA-037), not for `UNKNOWN_TERM` entries (which are non-halting).
- **Suggested fix:** Three options (in order of preference):
  1. **Persist `unresolved_ambiguities` in the cache entry.** Extend `TranslationResult` (or the cache value schema) to include the `unresolved_ambiguities` list generated during the rule path. On cache hit, replay these into `ctx.unresolved_ambiguities` so the L4 artifacts are populated identically.
  2. **Move `_log_unknown_cjk` out of `_rule_translate`.** Run it on the cached translation result as a separate step in `translate_segment`, so it fires on both cache hit and miss.
  3. **Document the limitation.** Add a note to `ambiguity_register.json` schema and SKILL.md §4: "The L4 ambiguity register is fully populated on cold-cache runs; warm-cache runs may omit `UNKNOWN_TERM` entries that were captured during the original cold-cache translation. For full L4 forensic coverage, clear the cache before auditing."
  
  Option 1 is preferred because it preserves the cache performance benefit while making the L4 forensic trail cache-state-invariant.
- **Round 4 status:** new (not flagged by R4 Track E4 — TRA-038 was not yet wired at R4 baseline `805a8f8`; this is a side-effect of R4 Batch 2 commit `d95c36d`)

### TRA-E5-017 — `audit --report` generates Mermaid state diagram + conformance summary (NEW, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Audit Reporting (§6.3 / Phase 6.3)
- **Finding type:** positive_verification
- **Evidence:**
  - `tra_cli.py:222-243` (`audit` command `--report` flag):
    ```python
    if report:
        summary = summarize_audit(trail)
        console.print("\n[bold]Conformance summary[/bold]")
        console.print(f"  total records: {summary['total']}")
        console.print(f"  by severity:   {summary['by_severity']}")
        console.print(f"  by instruction: {summary['by_instruction']}")
        verdict = ("[green]L3 CONFORMANT[/green]" if summary["l3_conformant"]
                   else "[red]NON-CONFORMANT (BLOCKING raised)[/red]")
        console.print(f"  verdict: {verdict}")
        console.print("\n[bold]State-transition diagram[/bold]")
        cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
        exec_log = Path(cfg.compilation_dir) / "execution_log.json"
        log = json.loads(exec_log.read_text(...)).get("execution_log", []) if exec_log.exists() else []
        console.print(mermaid_state_diagram(log))
    ```
  - `tra/reporting.py:50-70` (`mermaid_state_diagram`): generates `flowchart LR` Mermaid diagram from `execution_log.json`.
  - R5 Probe 13 (this audit): `python -m tra_cli audit audit_trace.jsonl --report` produced:
    - Conformance summary: `total records: 6`, `by severity: {}`, `by instruction: {ANALYZE_DOCUMENT: 1, BUILD_GLOSSARY: 1, BUILD_ENTITY_TABLE: 1, TRANSLATE_SEGMENT: 1, VERIFY_OUTPUT: 2}`, `verdict: L3 CONFORMANT`.
    - Mermaid diagram: 9 nodes (`BOOTSTRAP` through `EMIT_PAYLOAD`) + 7 edges (`INITIALIZE_RUNTIME --> ANALYZE_DOCUMENT --> BUILD_ARTIFACTS --> EXECUTE_TRANSLATION --> VERIFY_OUTPUT --> REPAIR_IF_NEEDED --> AUDIT_DIAGNOSTICS --> EMIT_PAYLOAD`).
  - `tests/test_reporting.py:36-56` (5 tests): `test_mermaid_diagram_renders_canonical_order`, `test_mermaid_diagram_follows_execution_log`, `test_mermaid_diagram_handles_single_state`, `test_summarize_counts_severity_and_instruction`, `test_summarize_l3_conformant_when_no_blocking` — all pass (228 total pytest pass).
- **Detail:** The Phase 6.3 audit-reporting layer is fully functional at HEAD `5476faf`. The `audit --report` command produces both the conformance summary (counts by severity/instruction, L3 verdict) and the Mermaid state-transition diagram (rendered from `execution_log.json`). The diagram correctly reflects the actual run path (8 post-BOOTSTRAP states in canonical order). R4 Track E4 did not explicitly verify this feature; this is a new positive verification.
- **Suggested fix:** None. Positive confirmation.
- **Round 4 status:** new (positive verification — feature was present at R4 but not explicitly verified by Track E4)

### TRA-E5-018 — TRA-042 extended structural verification works correctly; no false-positive BLOCKING on conformant input (NEW, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Structural Verification (§7 / TRA-042)
- **Finding type:** positive_verification
- **Evidence:**
  - R4 Batch 2 commit `efbc875` added 5 new structural checks: table row count, list item count, blockquote line count, horizontal rule count, fenced code block count.
  - `tra/isa.py:812-890` (5 new regex-based structural checks): `_TABLE_ROW_RE` (line 813), `_LIST_ITEM_RE` (line 829), `_BLOCKQUOTE_RE` (line 844), `_HR_RE` (line 860), `_CODE_FENCE_RE` (line 878).
  - `tests/test_outstanding_findings.py::TestTRA042ExtendedStructuralVerification` (6 tests, commit `efbc875`): 5 mismatch cases (table row, list item, blockquote, HR, code fence) + 1 negative test. All pass (228 total pytest pass).
  - R5 Probe 9 (this audit, false-positive test): input `# Test Heading\n\n| Col1 | Col2 |\n|------|------|\n| a | b |\n\nSome paragraph text.\n` run at L4 → exit 0, 6 audit records, no flags raised. **No false-positive BLOCKING.**
  - R5 Probe 10 (this audit, true-positive test): source `# H\n\n- a\n- b\n- c\n` with rule path monkeypatched to drop `- item A` (creating a list mismatch) → 1 BLOCKING diagnostic (`List item count mismatch after translation`, `evidence="source=3 target=2"`); L4 run raised `ConformanceFailure: CONFORMANCE_FAILURE: 1 BLOCKING diagnostic(s) remain after repair loop — output is not L3-conformant`.
  - L4 happy-path run on `to_translate.md`: zero structural diagnostics fired (audit trail flags=None on all 6 records).
- **Detail:** The TRA-042 extended structural verification does NOT introduce false-positive BLOCKING diagnostics on conformant input. The 5 new regex patterns correctly detect structural mismatches (table row, list item, blockquote, HR, code fence count) when source and target differ, and correctly pass when they match. The L3 gate correctly rejects outputs with BLOCKING structural diagnostics. The TRA-042 + TRA-072 (PolicyResolver severity arbitration) + L3 gate combination is functioning as designed.
  
  **Known regex gaps (cross-ref Track A5 TRA-A5-011/012)**: `_LIST_ITEM_RE` only matches unordered lists (`[-*+]`); ordered lists (`1.`, `2.`, etc.) are not detected. `_BLOCKQUOTE_RE` requires whitespace after `>`; `>text` (no space, valid per CommonMark) is not detected. These gaps reduce the structural verification's coverage but do NOT produce false positives — they produce false negatives (missed mismatches), which is the safe direction for an L3 gate.
- **Suggested fix:** None. Positive confirmation. (Track A5's TRA-A5-011/012 findings cover the regex gaps; resolving those would tighten TRA-042's coverage.)
- **Round 4 status:** new (positive verification — TRA-042 was added by R4 Batch 2 commit `efbc875`; this audit confirms no L4-gate regressions)

### TRA-E5-019 — TRA-072 PolicyResolver severity arbitration works correctly for STRUCTURAL_INTEGRITY (NEW, positive)
- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Policy Arbitration (§4 / TRA-072)
- **Finding type:** positive_verification
- **Evidence:**
  - R4 Batch 2 commit `78c9250` wired `_POLICY_RESOLVER.wins()` into 4 ISA call sites.
  - `tra/isa.py:792-798` (structural severity arbitration):
    ```python
    structural_severity = (
        Severity.BLOCKING
        if _POLICY_RESOLVER.wins(
            PolicyPriority.STRUCTURAL_INTEGRITY, PolicyPriority.TARGET_FLUENCY
        )
        else Severity.WARNING
    )
    ```
  - `tra/policy.py:24-25` (`PolicyResolver.wins`): `return self.priority(a) <= self.priority(b)`.
  - `tra/memory.py:24-35` (PolicyPriority enum): `FACTUAL=1, STRUCTURAL=2, ENTITY=3, TERMINOLOGICAL=4, EPISTEMIC=5, FLUENCY=6` — STRUCTURAL_INTEGRITY (2) < TARGET_FLUENCY (6), so `wins(STRUCTURAL, FLUENCY)` returns True → `structural_severity = BLOCKING`.
  - R5 Probe 10 (this audit): list-item mismatch → BLOCKING diagnostic raised (severity=BLOCKING). Confirms `structural_severity = Severity.BLOCKING` at HEAD.
  - R5 Probe 11 (this audit, structural input that should fire): table input passes (no mismatch → no diagnostic). Confirms arbitration only fires when mismatch is detected.
  - `tests/test_outstanding_findings.py::TestTRA072UniversalPolicyArbitration` (3 tests, commit `78c9250`): structural, entity, epistemic call sites tested. All pass (228 total pytest pass).
- **Detail:** The TRA-072 PolicyResolver correctly arbitrates structural-severity decisions at HEAD `5476faf`. The default policy (`STRUCTURAL_INTEGRITY=2` beats `TARGET_FLUENCY=6`) produces BLOCKING for structural mismatches, which the L3 gate then rejects. The 4 PolicyResolver.wins() call sites verified by Track A5 (isa.py:794 structural, 898 entity, 926 terminology, 959 epistemic — all vs TARGET_FLUENCY) are correctly wired. No false-positive BLOCKING from policy arbitration.
- **Suggested fix:** None. Positive confirmation. (Cross-ref Track D5 TRA-D5-018 for a monkeypatch-specificity gap in the TRA-072 tests, which doesn't affect production behavior.)
- **Round 4 status:** new (positive verification — TRA-072 was added by R4 Batch 2 commit `78c9250`; this audit confirms no L4-gate regressions)

### TRA-E5-020 — L4 ambiguity_register content test-coverage gap (NEW, INFO)
- **Severity:** INFO (test coverage gap)
- **Category:** Forensic L4 / Test Coverage (TRA-038 L4 verification)
- **Finding type:** issue
- **Evidence:**
  - `tests/test_e2e_to_translate.py:281-297` (`test_l4_emits_forensic_artifacts`):
    ```python
    artifacts_dir = tmp_path / "compilation_artifacts"
    assert (artifacts_dir / "evidence_trace.jsonl").exists(), "L4 must emit evidence_trace.jsonl"
    assert (artifacts_dir / "ambiguity_register.json").exists(), "L4 must emit ambiguity_register.json"
    ```
    Only verifies existence — does NOT verify content (entry count, entry types, presence of `UNKNOWN_TERM` / `ENTITY_AMBIGUITY` entries).
  - `tests/test_e2e_to_translate.py:299-325` (`test_evidence_trace_has_one_entry_per_output_line`): verifies evidence_trace.jsonl structure (line, text, evidence_ids, attributed fields) but does NOT verify attributed count or orphan rate.
  - `tests/test_outstanding_findings.py::TestTRA038UnknownTermRaisedInProduction` (3 tests, commit `d95c36d`): verifies that `_log_unknown_cjk` runs on a probe input (`# 测试标题\n\n这是一个未知术语未在词表中出现的文档。\n`) — but does NOT verify the L4 ambiguity register content on the canonical `to_translate.md` source.
  - No test asserts that the L4 `ambiguity_register.json` on `to_translate.md` contains ≥1 `UNKNOWN_TERM` entry on a cold-cache run, or that the entry count is stable across cache states.
- **Detail:** R4 Batch 2 commit `d95c36d` added TRA-038's `_log_unknown_cjk` to populate the L4 ambiguity register, but the test suite does NOT verify the L4 ambiguity register content end-to-end on the canonical source. This means:
  - TRA-E5-016 (cache-state non-determinism) would NOT be caught by the existing test suite — the tests pass on both cold and warm cache because they only check existence.
  - A regression that drops `UNKNOWN_TERM` entries from the register (e.g., if `_log_unknown_cjk` is accidentally removed from `_rule_translate`) would NOT be caught.
  
  Track D5's TRA-D5-019 (positive verification) confirmed that the 6 R4 Batch 2 test classes have meaningful assertions — but they test ISA-level behavior, not L4 artifact content end-to-end.
- **Suggested fix:** Add a test in `tests/test_e2e_to_translate.py` (e.g., `TestE2EToTranslateL4::test_l4_ambiguity_register_contains_unknown_term_entries`) that:
  1. Runs the kernel on `to_translate.md` at L4 with a cleared cache.
  2. Loads `ambiguity_register.json`.
  3. Asserts at least 1 entry starts with `"UNKNOWN_TERM:"` (verifies TRA-038's `_log_unknown_cjk` ran end-to-end).
  4. Asserts at least 1 entry starts with `"ENTITY_AMBIGUITY:"` (verifies TRA-038's `recover_entity_ambiguity` ran end-to-end).
  5. (Optional) Asserts entry count is stable across 2 cold-cache runs (closes TRA-E5-016 regression-test gap).
- **Round 4 status:** new (test coverage gap surfaced by this audit's TRA-E5-016 finding)

## Round 4 Track E4 carry-over status matrix

| Round 4 ID | Title | Round 5 status | Round 5 ID |
|---|---|---|---|
| TRA-E4-001 | Evidence trace orphan lines persist | **persistent** (WARNING) | TRA-E5-001 |
| TRA-E4-002 | UnknownTerm still never raised | **partial-fixed** (INFO) — register now captures UNKNOWN_TERM via direct call (TRA-038); EXCEPTION_HANDLER audit record still absent (TRA-B5-018) | TRA-E5-002 |
| TRA-E4-003 | Empty source recovery severity still WARNING | **persistent** (INFO) | TRA-E5-003 |
| TRA-E4-004 | RepairAttempt.segment_index always 0 | **persistent** (INFO) | TRA-E5-004 |
| TRA-E4-005 | HITL path still unreachable through CLI | **persistent** (INFO, cross-ref D5-007) | TRA-E5-005 |
| TRA-E4-006 | Byte-reproducibility confirmed (positive) | **persistent (positive)** (INFO) | TRA-E5-006 |
| TRA-E4-007 | TRA-071 BROKEN_MARKDOWN reachable (positive) | **persistent (positive)** (INFO) | TRA-E5-007 |
| TRA-E4-008 | TRA-036 L3 gate blocks empty source (positive) | **persistent (positive)** (INFO) | TRA-E5-008 |
| TRA-E4-009 | TRA-037 L3 gate checks unresolved_ambiguities (positive) | **persistent (positive)** (INFO) | TRA-E5-009 |
| TRA-E4-010 | TRA-037 link rewrite hash matches emitted (positive) | **persistent (positive)** (INFO) | TRA-E5-010 |
| TRA-E4-011 | Audit trail state sequence matches _KERNEL_ORDER (positive) | **persistent (positive)** (INFO) | TRA-E5-011 |
| TRA-E4-012 | All 9 artifacts present, exit 0 (positive) | **persistent (positive)** (INFO) | TRA-E5-012 |
| TRA-E4-013 | Double VERIFY_OUTPUT at L3+ (documentation) | **persistent** (INFO) | TRA-E5-013 |
| TRA-E4-014 | TRA-093 false-positive BROKEN_LINK FIXED (positive) | **persistent (positive)** (INFO) | TRA-E5-014 |
| TRA-E4-015 | `style_profile.yaml` undocumented in SKILL.md §4 | **persistent** (INFO, cross-ref C5 doc-refresh cluster) | TRA-E5-015 |

**Round 5 net delta vs R4 Track E4:** 0 BLOCKING; 1 new WARNING (TRA-E5-016 — cache-state non-determinism, side-effect of R4 Batch 2 TRA-038); 4 new INFO (TRA-E5-017/018/019 positive verifications, TRA-E5-020 test-coverage gap); 1 partial-fixed (TRA-E4-002 → TRA-E5-002). No new BLOCKING. No regressions.

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype
source .venv/bin/activate

# 1. Cold-cache L4 Run 1 (clear cache + artifacts)
rm -rf cache compilation_artifacts audit_trace.jsonl
python -m tra_cli translate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md --level L4 -o /tmp/r5_e5_out.md
ls compilation_artifacts/
# → 8 files in compilation_artifacts/ + audit_trace.jsonl = 9 total

sha256sum audit_trace.jsonl compilation_artifacts/ambiguity_register.json \
  compilation_artifacts/evidence_trace.jsonl compilation_artifacts/execution_log.json \
  /tmp/r5_e5_out.md
# → 902298b3...  b49af79d...  8361d22d...  d72af589...  5009f53f...

# 2. Cold-cache L4 Run 2 (byte-reproducibility probe)
rm -rf cache compilation_artifacts audit_trace.jsonl
python -m tra_cli translate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md --level L4 -o /tmp/r5_e5_out2.md
sha256sum audit_trace.jsonl compilation_artifacts/ambiguity_register.json \
  compilation_artifacts/evidence_trace.jsonl compilation_artifacts/execution_log.json \
  /tmp/r5_e5_out2.md
# → 902298b3...  b49af79d...  8361d22d...  d72af589...  5009f53f... (identical to Run 1)

# 3. Warm-cache L4 Run 3 (cache-state non-determinism probe — TRA-E5-016)
rm -rf compilation_artifacts audit_trace.jsonl  # NOTE: cache NOT cleared
python -m tra_cli translate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md --level L4 -o /tmp/r5_e5_warm.md
sha256sum audit_trace.jsonl compilation_artifacts/ambiguity_register.json \
  compilation_artifacts/evidence_trace.jsonl compilation_artifacts/execution_log.json \
  /tmp/r5_e5_warm.md
# → 902298b3...  2b1cbb14...  8361d22d...  8ec98c67...  5009f53f...
# (audit_trace, evidence_trace, output.md identical; ambiguity_register, execution_log DIFFER)

python3 -c "
import json
d = json.load(open('compilation_artifacts/ambiguity_register.json'))
print(f'Warm-cache entries: {len(d)}')"  # → 9 (vs cold-cache 99)

# 4. Audit --report (Mermaid + conformance summary)
python -m tra_cli audit audit_trace.jsonl --report
# → 6-record table + conformance summary + Mermaid flowchart LR

# 5. L3 validate on L4 output (standalone gate)
python -m tra_cli validate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md /tmp/r5_e5_out.md --level L3
# → PASS: candidate meets the conformance gate. (exit 0)

# 6. TRA-037 BROKEN_LINK probe (L3 gate)
mkdir -p /tmp/e5_probe && cat > /tmp/e5_probe/broken_link.md <<'EOF'
# Real Heading
This paragraph references [a nonexistent anchor](#does-not-exist) which should fail the L3 gate.
EOF
python3 -c "
import sys; sys.path.insert(0, '.')
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
from pathlib import Path
cfg = BootstrapConfig.from_yaml('config.yaml').model_copy(update={
    'base_dir': '/tmp/e5_probe', 'conformance_level': ConformanceLevel.L4_FORENSIC,
    'audit_trace': '/tmp/e5_probe/audit_trace.jsonl',
    'compilation_dir': '/tmp/e5_probe/compilation_artifacts',
    'cache_directory': '/tmp/e5_probe/cache',
})
try:
    TRAKernel(cfg).run(Path('/tmp/e5_probe/broken_link.md'))
    print('UNEXPECTED: published')
except Exception as exc:
    print(f'EXPECTED — {type(exc).__name__}: {exc}')"
# → ConformanceFailure: CONFORMANCE_FAILURE: 1 BROKEN_LINK entry/entries in unresolved_ambiguities

# 7. TRA-042 false-positive probe (table input)
cat > /tmp/e5_probe/table.md <<'EOF'
# Test Heading
| Col1 | Col2 |
|------|------|
| a    | b    |
Some paragraph text.
EOF
python3 -c "
import sys; sys.path.insert(0, '.')
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
from pathlib import Path
cfg = BootstrapConfig.from_yaml('config.yaml').model_copy(update={
    'base_dir': '/tmp/e5_probe', 'conformance_level': ConformanceLevel.L4_FORENSIC,
    'audit_trace': '/tmp/e5_probe/audit_table.jsonl',
    'compilation_dir': '/tmp/e5_probe/arts_table',
    'cache_directory': '/tmp/e5_probe/cache_table',
})
k = TRAKernel(cfg)
k.run(Path('/tmp/e5_probe/table.md'))
print('table published OK, flags:', [r.flags_raised for r in k.audit._buffer])"
# → table published OK, flags: [None, None, None, None, None, None] (no false-positive BLOCKING)

# 8. TRA-042 true-positive probe (list mismatch)
python3 -c "
import sys; sys.path.insert(0, '.')
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
import tra.isa as isa_mod
orig = isa_mod._rule_translate
def patched(seg, g, e, module=None, unresolved_ambiguities=None):
    out, b = orig(seg, g, e, module, unresolved_ambiguities)
    return out.replace('- item A\n', ''), b
isa_mod._rule_translate = patched
cfg = BootstrapConfig.from_yaml('config.yaml').model_copy(update={
    'base_dir': '/tmp/e5_probe', 'conformance_level': ConformanceLevel.L4_FORENSIC,
    'audit_trace': '/tmp/e5_probe/audit_struct.jsonl',
    'compilation_dir': '/tmp/e5_probe/arts_struct',
    'cache_directory': '/tmp/e5_probe/cache_struct',
})
from pathlib import Path
Path('/tmp/e5_probe/list_mismatch.md').write_text('# Heading\n\n- item A\n- item B\n- item C\n')
try:
    TRAKernel(cfg).run(Path('/tmp/e5_probe/list_mismatch.md'))
    print('UNEXPECTED: published')
except Exception as exc:
    print(f'EXPECTED — {type(exc).__name__}: {exc}')
isa_mod._rule_translate = orig"
# → ConformanceFailure: CONFORMANCE_FAILURE: 1 BLOCKING diagnostic(s) remain after repair loop

# 9. Hash chain integrity probe (TRA-037)
python3 -c "
import hashlib, json
target = open('/tmp/r5_e5_out.md').read()
print('emitted sha256[:16]:', hashlib.sha256(target.encode()).hexdigest()[:16])
recs = [json.loads(l) for l in open('audit_trace.jsonl') if l.strip()]
for r in [r for r in recs if r['isa_instruction']=='VERIFY_OUTPUT']:
    print(f\"  seq={r['sequence_id']} input_hash={r['input_hash']}\")"
# → emitted: 5009f53fc322bb12 / seq=4: 5009f53fc322bb12 / seq=5: 5009f53fc322bb12 (MATCH)

# 10. Cross-verification on examples/security_advisory_zh.md (R4 baseline file)
python3 -c "
import sys; sys.path.insert(0, '.')
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
from pathlib import Path
cfg = BootstrapConfig.from_yaml('config.yaml').model_copy(update={
    'base_dir': '/tmp/e5_r4p', 'conformance_level': ConformanceLevel.L4_FORENSIC,
    'audit_trace': '/tmp/e5_r4p/audit_trace.jsonl',
    'compilation_dir': '/tmp/e5_r4p/arts',
    'cache_directory': '/tmp/e5_r4p/cache',
})
TRAKernel(cfg).run(Path('examples/security_advisory_zh.md'))
import json
trace = [json.loads(l) for l in open('/tmp/e5_r4p/arts/evidence_trace.jsonl') if l.strip()]
orphans = [e for e in trace if not e['evidence_ids']]
print(f'security_advisory_zh.md: {len(trace)} entries, {len(orphans)} orphans')
for o in orphans: print(f'  orphan line={o[\"line\"]} text={o[\"text\"][:70]!r}')"
# → 6 entries, 1 orphan (line 7: "96-core system keeps memory below <5MB at peak.")

# 11. Full pytest suite at HEAD
python -m pytest tests/ 2>&1 | tail -1
# → 228 passed in 1.16s

# 12. e2e pytest suite
python -m pytest tests/test_e2e_to_translate.py -v 2>&1 | tail -1
# → 12 passed in 0.22s

# 13. Manual e2e_test.py
rm -rf e2e_audit_trace.jsonl e2e_artifacts e2e_cache
python e2e_test.py 2>&1 | tail -1
# → VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics
```

## Conclusion

The L4 forensic pipeline at HEAD `5476faf` is **healthy, byte-stable (cold-cache), and free of new BLOCKING findings**. All 228 pytest tests pass (12 in the e2e suite). The manual `e2e_test.py` reports `L3 CONFORMANT — zero BLOCKING diagnostics`. The L4 translate command exits 0 and produces all 9 expected runtime artifacts with valid YAML/JSON/JSONL content. The 17 forensic probes (re-running R4 E4's 6 probes + 11 new probes) all return their expected verdicts.

**TRA-013 byte-reproducibility HOLDS** for cold-cache runs — `audit_trace.jsonl`, `evidence_trace.jsonl`, output.md, `ambiguity_register.json`, `execution_log.json` all byte-identical across 2 cold-cache runs. Absolute sha256 differs from R4 baseline `263b901e...` because R4 Batch 2 (TRA-038/042/072) enriched audit-trail content; the within-HEAD invariant is what matters.

**R4 Batch 2 (TRA-038/042/072/099) impact on L4 forensics:** TRA-038 (`_log_unknown_cjk` + `recover_entity_ambiguity`) now populates the L4 ambiguity register with `UNKNOWN_TERM` and `ENTITY_AMBIGUITY` entries (was empty `[]` in R4) — addressing the original TRA-E4-002 WARNING (downgraded to INFO partial-fixed). TRA-042 (5 new structural checks) and TRA-072 (PolicyResolver severity arbitration) work correctly together — no false-positive BLOCKING on conformant input, true-positive BLOCKING correctly raised on structural mismatch, L3 gate correctly rejects.

**The one new WARNING (TRA-E5-016)** is a side-effect of TRA-038's wiring: `_log_unknown_cjk` is called inside `_rule_translate`, which is skipped on cache hit. Two L4 translations of the same source produce different `ambiguity_register.json` and `execution_log.json` content depending on whether the cache was warm or cold (cold: 99 entries; warm: 9 entries). The audit trail (`audit_trace.jsonl`) is unaffected because the cache stores evidence_ids, not side-effects. Track B5's TRA-013 verification did not surface this because B5 only compared `audit_trace.jsonl` / `evidence_trace.jsonl` / `output.md`. **Recommended Round 6 remediation:** persist `unresolved_ambiguities` in the cache entry so the L4 forensic trail is cache-state-invariant. The L3 gate does not catch this because `unresolved_ambiguities` is only consulted for `BROKEN_LINK` entries (TRA-037), not for `UNKNOWN_TERM` entries (which are non-halting).

The 2 WARNING findings (TRA-E5-001 orphan lines persistent; TRA-E5-016 cache-state non-determinism new) are both documented consequences of TRA-001 partial (segment-level translation not yet implemented) and TRA-038's wiring choice (direct call inside cache-skipped path). The 1 partial-fixed finding (TRA-E5-002 UnknownTerm) shows R4 Batch 2 progress. The 4 new positive verifications (TRA-E5-017/018/019 + TRA-E5-006 byte-reproducibility) confirm the L4 pipeline at HEAD `5476faf` is functioning as designed. **No new BLOCKING, no regressions.**
