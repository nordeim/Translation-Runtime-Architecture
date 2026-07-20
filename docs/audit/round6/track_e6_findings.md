# Track E6 — Forensic L4 End-to-End Re-Audit (Round 6)

**Task ID:** E6-1
**Auditor:** Track E6 (forensic L4 end-to-end)
**HEAD audited:** `c4ecd4155d1baa0b4b5d6e60d2e9b1da217e8a46` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Source under test:** `/home/z/my-project/Translation-Runtime-Architecture/to_translate.md`
**Baseline:** Round 5 Track E5 (`docs/audit/round5/track_e5_findings.md`, 20 findings: 0 BLOCKING / 2 WARNING / 18 INFO) + R5 master register + R6 regression baseline (`docs/audit/round6/track_r6_baseline.md`)
**Methodology:** Cold-cache L4 translation of `to_translate.md` on isolated workdirs (separate cache/audit_trace/compilation_dir); 9-artifact inventory; byte-reproducibility probe across 2 cold-cache runs (separate workdirs); audit_trace.jsonl append-mode probe (CLI default paths, two consecutive runs); warm-cache non-determinism probe; L3 gate verification (standalone `validate` + `audit --report`); per-leaf translation audit-record count verification; EXCEPTION_HANDLER audit-record inspection for UnknownTerm; hash-chain integrity verification (VERIFY_OUTPUT `input_hash` vs emitted target `sha256[:16]`); full pytest suite (309 tests) + e2e suite (12 tests).

## Verification Run

- HEAD: `git rev-parse HEAD` → `c4ecd4155d1baa0b4b5d6e60d2e9b1da217e8a46` ✓
- Quality gates: `python -m pytest tests/` → **309 passed in 3.09s** ✓
- e2e suite: `python -m pytest tests/test_e2e_to_translate.py` → **12 passed in 0.35s** ✓
- mypy --strict: 0 issues (per `c4ecd41` commit message)
- ruff: clean

## Summary

- **Findings: 13 total (0 BLOCKING / 3 WARNING / 10 INFO)**
- **All 6 task-scope verification items:**

| # | Task item | Result | Evidence |
|---|---|---|---|
| 1 | TRA-013 byte-reproducibility (two cold-cache L4 runs, isolated workdirs) | ✅ PASS | TRA-E6-006 (positive_verification) — `audit_trace.jsonl` sha256 `85363d55...` × 2 runs (byte-identical) |
| 2 | 9 L4 artifacts present (glossary, entity_table, structural_map, style_profile, execution_log, repair_history, audit_trace, evidence_trace, ambiguity_register) | ✅ PASS | TRA-E6-007 (positive_verification) — all 9 present + parse cleanly |
| 3 | L3 gate (zero BLOCKING) passes | ✅ PASS | TRA-E6-008 (positive_verification) — `audit --report` verdict `L3 CONFORMANT`; `validate --level L3` exit 0 |
| 4 | Per-leaf translation produces multiple TRANSLATE_SEGMENT audit records | ✅ PASS | TRA-E6-009 (positive_verification) — 15 TRANSLATE_SEGMENT records (matches structural_map's 15 leaf segments) |
| 5 | EXCEPTION_HANDLER audit records present for UnknownTerm | ✅ PASS | TRA-E6-010 (positive_verification) — 93 EXCEPTION_HANDLER records, all `input_hash=UNKNOWN_TERM` |
| 6 | Hash chain integrity (VERIFY_OUTPUT input_hash matches emitted target) | ✅ PASS | TRA-E6-011 (positive_verification) — both VERIFY_OUTPUT `input_hash=de186867cdc60489` matches emitted target `sha256[:16]=de186867cdc60489` |

- **Carry-over from Round 5 Track E5:** 7 findings re-verified (2 fixed, 1 partial-fixed, 1 partial-fixed-positive, 1 persistent, 2 persistent-positive)
- **New findings:** 4 (TRA-E6-001 audit_trace.jsonl append-mode WARNING; TRA-E6-002 evidence_trace orphan-line resolution IMPROVED positive INFO; TRA-E6-003 warm-cache suppresses EXCEPTION_HANDLER records cross-ref A6-001 INFO; TRA-E6-004 audit_trace.jsonl append behavior with reused path test-coverage gap INFO)
- **Regressions:** 0 (expected 0)

---

## L4 artifact inventory (cold-cache L4 run on `to_translate.md`)

Command:
```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype
source .venv/bin/activate
rm -rf /tmp/e6_test
python -c "
import sys; sys.path.insert(0, '.')
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
from pathlib import Path
cfg = BootstrapConfig.from_yaml('config.yaml').model_copy(update={
    'base_dir': '/tmp/e6_test', 'conformance_level': ConformanceLevel.L4_FORENSIC,
    'audit_trace': '/tmp/e6_test/audit_trace.jsonl',
    'compilation_dir': '/tmp/e6_test/compilation_artifacts',
    'cache_directory': '/tmp/e6_test/cache',
})
src = Path('/home/z/my-project/Translation-Runtime-Architecture/to_translate.md').read_text()
kernel = TRAKernel(cfg)
target = kernel.run(src)
Path('/tmp/e6_test/out.md').write_text(target)
"
ls /tmp/e6_test/compilation_artifacts/
```

| Artifact | Present | Size | sha256 (first 16) | Notes |
|---|---|---|---|---|
| `audit_trace.jsonl` | YES | 45516 B | `85363d556ab6dcbc` | 113 records: 1 ANALYZE_DOCUMENT + 1 BUILD_GLOSSARY + 1 BUILD_ENTITY_TABLE + 93 EXCEPTION_HANDLER + 15 TRANSLATE_SEGMENT + 2 VERIFY_OUTPUT. All WARNING flags on EXCEPTION_HANDLER records; 0 BLOCKING. seq=0..112. |
| `compilation_artifacts/glossary.yaml` | YES | 1296 B | `00e7c06ef9a9cb07` | 11 entries (成立 → Confirmed, 执行环境 → execution environment, 准确描述 → accurately describes, 高度可信 → highly credible, 可能 → may, 进行验证 → verify, 实现优化 → optimize, 提供支持 → support, 硬件隔离 → Hardware isolation, 无缝迁移 → Seamless migration, 高可用性 → High availability). |
| `compilation_artifacts/entity_table.yaml` | YES | 939 B | `eb6c7f3e768f01e1` | 13 entities (L1, L2, L3, L4 = product; ISA, BUILD, AUDIT, EMIT, TRA, ZH, EN, SUITE, GUIDE = acronym). All `mutable: false`, `context: source-document`. |
| `compilation_artifacts/structural_map.json` | YES | 6066 B | `be39ae72f1183e5a` | 15 paragraph nodes; 0 heading nodes (source has no markdown headings — emoji-prefixed Chinese section titles are paragraphs). |
| `compilation_artifacts/style_profile.yaml` | YES | 260 B | `a035a2e54efae7bc` | voice=Passive/Objective, sentence_complexity=High, epistemic_mapping (4 entries), punctuation_rules (2 entries). |
| `compilation_artifacts/execution_log.json` | YES (cold-cache) | 12995 B | `24b847239b0b6753` | 8 post-BOOTSTRAP states in canonical order. `unresolved_ambiguities`: 100 entries (9 ENTITY_AMBIGUITY + 91 UNKNOWN_TERM) on cold cache. **Warm-cache hash differs — see TRA-E6-003 / TRA-E5-016.** |
| `compilation_artifacts/repair_history.jsonl` | YES | 0 B | `e3b0c44298fc1c14` | Empty (0 bytes — clean run, no repairs triggered). |
| `compilation_artifacts/evidence_trace.jsonl` | YES (L4 only) | 4641 B | `d74207405c62b370` | 19 entries; **19 attributed + 0 orphans** on cold-cache (IMPROVED vs R5's 6 orphans — see TRA-E6-002). Warm-cache still has 6 orphans (see TRA-E6-003). |
| `compilation_artifacts/ambiguity_register.json` | YES (L4 only, cold-cache) | 10245 B | `c25e7c38ae0c9c12` | 100 entries (9 ENTITY_AMBIGUITY + 91 UNKNOWN_TERM). **Warm-cache hash differs (`2b1cbb14...`, 9 entries only) — see TRA-E6-003.** |
| `out.md` (emitted target) | YES | 2703 B | `de186867cdc60489` | 2703 bytes, 33 lines. Rule path output (no LLM) — Chinese source preserved verbatim with glossary substitutions. |

All 9 expected L4 artifacts exist and parse cleanly (YAML / JSON / JSONL). L3 run produces 7 artifacts (no `evidence_trace.jsonl` or `ambiguity_register.json` — confirmed via separate L3 probe at `/tmp/e6_l3/`).

## Byte-reproducibility probe (TRA-013)

### Probe A: Two cold-cache runs on isolated workdirs (canonical TRA-013 test)

```bash
rm -rf /tmp/e6_rep1 /tmp/e6_rep2
# Run 1: cold cache, /tmp/e6_rep1/{cache,audit_trace.jsonl,compilation_artifacts/}
# Run 2: cold cache, /tmp/e6_rep2/{cache,audit_trace.jsonl,compilation_artifacts/}
```

| Run | audit_trace.jsonl sha256 | evidence_trace.jsonl sha256 | ambiguity_register.json sha256 | execution_log.json sha256 | output.md sha256 |
|---|---|---|---|---|---|
| Run 1 (cold cache, /tmp/e6_rep1) | `85363d556ab6dcbc6b14c5bb028b84e92a322ef1adc59b67f5a07363a67e5ce8` | `d74207405c62b3704718f0e97c2c6c1c2beea7e19bd9875cf7d9ba4537e1e099` | `c25e7c38ae0c9c12d929a8334f5f91d5e8d06c12fc1021a54fcb822fbdc35374` | `24b847239b0b6753ab8711c50299437bb5ea1f02678a280ef7de21597108bc12` | `de186867cdc604892f17da85a1aa7f5f2f702ce4340679a8826d96850bd2b85a` |
| Run 2 (cold cache, /tmp/e6_rep2) | `85363d556ab6dcbc6b14c5bb028b84e92a322ef1adc59b67f5a07363a67e5ce8` | `d74207405c62b3704718f0e97c2c6c1c2beea7e19bd9875cf7d9ba4537e1e099` | `c25e7c38ae0c9c12d929a8334f5f91d5e8d06c12fc1021a54fcb822fbdc35374` | `24b847239b0b6753ab8711c50299437bb5ea1f02678a280ef7de21597108bc12` | `de186867cdc604892f17da85a1aa7f5f2f702ce4340679a8826d96850bd2b85a` |
| Identical? | **YES** | **YES** | **YES** | **YES** | **YES** |

**TRA-013 HOLDS** for two cold-cache L4 runs on isolated workdirs. The deterministic clock (`kernel.py:226-240`, `seed = self._source_hash_seed or "0" * 16`) and content-addressed evidence IDs (`diagnostics.py:45-63`, `ev_{sha256(canonical_record)[:12]}`) produce stable timestamps and IDs.

Note: Absolute sha256 differs from R5 baseline (`audit_trace.jsonl` was `902298b3...` at HEAD `5476faf`) because R5 Batch H (commit `f782043`, TRA-001 Phase 8 per-leaf translation) and R5 Batch 2 (`36246bb`, TRA-A5-003 EXCEPTION_HANDLER audit records) enriched the audit-trail content. The R5 audit trail had 6 records (1 TRANSLATE_SEGMENT, 0 EXCEPTION_HANDLER); HEAD `c4ecd41` produces 113 records (15 TRANSLATE_SEGMENT, 93 EXCEPTION_HANDLER). The within-HEAD invariant (reproducibility across two cold-cache runs) is what TRA-013 mandates.

### Probe B: Two CLI runs on the same `./audit_trace.jsonl` path (CLI default config.yaml) — TRA-E6-001

```bash
mkdir -p /tmp/e6_cli && cd /tmp/e6_cli && cp .../config.yaml .
python -m tra_cli translate .../to_translate.md --level L4 -o out1.md
wc -l audit_trace.jsonl    # → 113
python -m tra_cli translate .../to_translate.md --level L4 -o out2.md
wc -l audit_trace.jsonl    # → 133 (NOT 113!)
```

| Run | audit_trace.jsonl line count | sha256 (first 16) | Notes |
|---|---|---|---|
| Run 1 (cold cache, fresh file) | 113 | `85363d556ab6dcbc` | First kernel run; file created from scratch. |
| Run 2 (warm cache, same file path) | 133 | (different from Run 1) | Second kernel run **appended** 20 records to the existing file. NOT byte-identical to Run 1. |
| Identical? | **NO** | **NO** | **TRA-013 byte-reproducibility FAILS** when the audit_trace path is reused across runs. |

**Root cause:** `tra/diagnostics.py:200` — `AuditTrail.flush()` opens the file in **append mode** (`"a"`) and never truncates:
```python
with self.path.open("a", encoding="utf-8") as fh:
    for rec in self._buffer[self._flushed :]:
        fh.write(rec.model_dump_json() + "\n")
```

The `AuditTrail.__init__` constructor (line 157-167) does NOT truncate the file either. So if the audit_trace.jsonl file already exists when a new kernel run starts, the new run's records are appended to the old ones. The CLI default config.yaml paths (`./audit_trace.jsonl`, `./cache`, `./compilation_artifacts`) are reused across runs, so two consecutive `python -m tra_cli translate ...` invocations produce a corrupted audit trail.

The R5 audit (Track E5) did NOT surface this because their methodology always did `rm -rf cache compilation_artifacts audit_trace.jsonl` before each run — masking the append-mode defect. The `tests/test_e2e_to_translate.py::TestE2EToTranslateReproducibility` tests also use `tmp_path/run1` and `tmp_path/run2` (separate workdirs), so they pass.

### Probe C: Warm-cache non-determinism (TRA-E5-016 carry-over, TRA-E6-003 cross-ref A6-001)

```bash
rm -rf /tmp/e6_cold
# Cold-cache run on /tmp/e6_cold
# Warm-cache run on /tmp/e6_warm2 (reusing /tmp/e6_cold/cache)
```

| Cache state | audit_trace.jsonl records | evidence_trace orphans | ambiguity_register.json entries | execution_log.json sha256 |
|---|---|---|---|---|
| Cold cache | 113 (15 TS + 93 EH + 5 others) | 0 orphans (19/19 attributed) | 100 (9 ENTITY_AMBIGUITY + 91 UNKNOWN_TERM) | `24b847239b0b6753` |
| Warm cache | 20 (15 TS + 0 EH + 5 others) | 6 orphans (13/19 attributed) | 9 (9 ENTITY_AMBIGUITY only) | `8ec98c67984f1327` |
| Identical? | **NO** | **NO** | **NO** | **NO** |

The warm-cache run produces a fundamentally different L4 forensic trail:
- 93 EXCEPTION_HANDLER records for UnknownTerm are silently dropped (cache-hit path at `isa.py:461-468` returns early without invoking `_log_unknown_cjk`).
- 91 UNKNOWN_TERM entries are missing from `ambiguity_register.json`.
- `execution_log.json`'s `unresolved_ambiguities` field is missing 91 entries.
- `evidence_trace.jsonl` has 6 orphan lines that were attributed on cold-cache.

`audit_trace.jsonl`, `evidence_trace.jsonl` (line count), and `output.md` are byte-identical across cold and warm cache — but the L4-only artifacts (`ambiguity_register.json`, `execution_log.json`'s `unresolved_ambiguities`, `evidence_trace.jsonl` attribution) vary by cache state. The R5 Track E5 audit (TRA-E5-016) flagged this for `ambiguity_register.json` + `execution_log.json`; this audit additionally confirms `evidence_trace.jsonl` attribution also varies.

## Probe results

| # | Probe | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | `audit_trace.jsonl` byte-identical across 2 cold-cache runs (isolated workdirs) | yes | sha256 `85363d55...` × 2 runs | **PASS** (TRA-E6-006) |
| 2 | `audit_trace.jsonl` byte-identical across 2 CLI runs on default config path | yes | Run 1=113 records, Run 2=133 records (appended) — NOT identical | **FAIL** (TRA-E6-001) |
| 3 | All 9 L4 artifacts present + valid | yes | 9/9 present; YAML/JSON/JSONL all parse cleanly | **PASS** (TRA-E6-007) |
| 4 | L3 gate (zero BLOCKING) passes on cold-cache L4 output | yes | `validate --level L3` exits 0; `audit --report` verdict `L3 CONFORMANT` | **PASS** (TRA-E6-008) |
| 5 | Per-leaf translation produces multiple TRANSLATE_SEGMENT audit records | yes (≥2) | 15 TRANSLATE_SEGMENT records (matches structural_map's 15 paragraph leaf segments); each with unique `input_hash` (content-addressed per leaf) + per-leaf evidence_chain | **PASS** (TRA-E6-009) |
| 6 | EXCEPTION_HANDLER audit records present for UnknownTerm | yes | 93 EXCEPTION_HANDLER records, all `input_hash=UNKNOWN_TERM`, `severity=WARNING`, `action=PRESERVE_SOURCE`, `source_term=<CJK token>` | **PASS** (TRA-E6-010) |
| 7 | Hash chain integrity: VERIFY_OUTPUT `input_hash` matches emitted target `sha256[:16]` | yes | seq=111 `input_hash=de186867cdc60489`; seq=112 `input_hash=de186867cdc60489`; emitted target `sha256[:16]=de186867cdc60489` — MATCH on both VERIFY_OUTPUT records | **PASS** (TRA-E6-011) |
| 8 | Warm-cache `audit_trace.jsonl` byte-identical to cold-cache | yes (per TRA-013 within HEAD) | Cold=113 records, Warm=20 records appended — different content; cold-cache L4-only artifacts (`ambiguity_register.json`, `execution_log.json`) also differ | **FAIL** (TRA-E6-003 / TRA-E5-016 persistent) |
| 9 | `evidence_trace.jsonl` orphan-line count on cold-cache | 0 (improved from R5's 6) | Cold-cache: 0 orphans (19/19 attributed). **Improvement from R5 (6 orphans) due to Batch H per-leaf translation generating per-leaf evidence records.** | **PASS** (TRA-E6-002) |
| 10 | `evidence_trace.jsonl` orphan-line count on warm-cache | 0 | Warm-cache: 6 orphans (13/19 attributed). Warm-cache regresses to R5 cold-cache behavior. | **PERSISTS** (TRA-E6-003) |
| 11 | TRA-E5-005 `--force-unrecoverable` flag exists + wired | yes (R5 Batch F) | `tra_cli.py:126` flag; `tra_cli.py:182` passes to TRAKernel; `kernel.py:362-371` injects synthetic BLOCKING diagnostic; `isa.py:1184-1191` raises Unrecoverable in repair_segment. HITL path fires when combined with `--interactive`. Without `--interactive`, the L3 gate re-verifies and passes (synthetic diagnostic not in target text). | **PASS** (partial-fix, TRA-E5-005) |
| 12 | TRA-E5-015 `style_profile.yaml` documented in SKILL.md §4 | yes (R5 Batch E) | `SKILL.md:146` lists "style profile" in artifact enumeration. | **PASS** (fixed, TRA-E5-015) |
| 13 | TRA-E5-003 EMPTY_SOURCE raises BrokenMarkdown with BLOCKING severity | yes (R5 Batch E) | `isa.py:108` raises `BrokenMarkdown(detail="EMPTY_SOURCE: ...")` — no longer base TRAException. `recovery.py` routes BrokenMarkdown to BLOCKING severity. | **PASS** (fixed, TRA-E5-003) |
| 14 | Full pytest suite at HEAD | 309 passed | `309 passed in 3.09s` | **PASS** |
| 15 | e2e pytest suite | 12/12 pass | `12 passed in 0.35s` | **PASS** |
| 16 | Manual e2e_test.py verdict | L3 CONFORMANT | `VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics` | **PASS** |

## Findings

### TRA-E6-001 — `audit_trace.jsonl` opened in append mode; CLI default path reused across runs breaks TRA-013 byte-reproducibility (NEW WARNING)

- **Severity:** WARNING
- **Category:** Forensic L4 / Audit Trail Reproducibility (§6.4 / TRA-013)
- **Finding type:** issue
- **Round 5 status:** new (defect pre-existed since Phase 2/3; not surfaced by R5 Track E5 because their methodology always `rm -rf`'d the audit_trace.jsonl before each run)
- **Evidence:**
  - `tra/diagnostics.py:200` — `AuditTrail.flush()` opens the file in **append mode**:
    ```python
    with self.path.open("a", encoding="utf-8") as fh:
        for rec in self._buffer[self._flushed :]:
            fh.write(rec.model_dump_json() + "\n")
    self._flushed = len(self._buffer)
    ```
  - `tra/diagnostics.py:157-167` — `AuditTrail.__init__` does NOT truncate the file on construction; only sets `self.path = Path(path)` and initializes `self._seq = 0`, `self._buffer = []`, `self._flushed = 0`.
  - `tra/config.yaml:27` — default `audit_trace: "./audit_trace.jsonl"` (relative path, resolved against CWD).
  - `tra_cli.py:147` — `translate` command loads `config.yaml` and passes through the default `audit_trace` path. No `--clear-audit` flag exists.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```bash
    mkdir -p /tmp/e6_cli && cd /tmp/e6_cli && cp .../config.yaml .
    python -m tra_cli translate .../to_translate.md --level L4 -o out1.md
    wc -l audit_trace.jsonl    # → 113 records
    python -m tra_cli translate .../to_translate.md --level L4 -o out2.md
    wc -l audit_trace.jsonl    # → 133 records (warm-cache run APPENDED 20 records)
    ```
  - Run 1 file (113 records, sha256 `85363d55...`) ≠ Run 2 file (133 records, sha256 differs). **TRA-013 byte-reproducibility FAILS** when the audit_trace path is reused across runs without explicit `rm`.
  - The CWD `tra-prototype/audit_trace.jsonl` at the start of this audit was 4183 lines (1 MB+) — accumulated across many runs, confirming the append-only behavior in production usage.
- **Detail:** The `AuditTrail.flush()` method was designed as "append-only JSONL" per the docstring at `diagnostics.py:1-6` ("The audit trail is append-only JSONL (one AuditRecord per line) so it streams safely and survives partial runs"). This append-only design is correct WITHIN a single kernel run (so `flush()` can be called multiple times safely — see `kernel.py:300` early-exit flush, `kernel.py:407` ConformanceFailure flush, `kernel.py:423` normal-end flush). However, the design does NOT account for the case where a NEW kernel run reuses the same audit_trace path — the new run's records are silently appended to the previous run's records, producing a corrupted (multi-run) audit trail.

  The R5 Track E5 audit's methodology (`rm -rf cache compilation_artifacts audit_trace.jsonl` before each run) accidentally masked this defect. The `tests/test_e2e_to_translate.py::TestE2EToTranslateReproducibility` tests use `tmp_path/run1` and `tmp_path/run2` (separate workdirs per run), so they pass. But the production CLI default config (`./audit_trace.jsonl`) is reused across runs, so two consecutive CLI invocations produce a non-byte-identical audit trail.

  This is a real L4 forensic integrity gap: an auditor running `python -m tra_cli translate doc.md --level L4` twice (perhaps to verify reproducibility) would see the audit_trace.jsonl grow from 113 records (Run 1) to 133 records (Run 2 = 113 + 20 warm-cache records). The Run 2 file is NOT byte-identical to Run 1 — violating TRA-013. Worse, the Run 2 file is internally inconsistent: it contains TWO complete kernel runs concatenated (Run 1's 113 records with EXCEPTION_HANDLERs, then Run 2's 20 records without EXCEPTION_HANDLERs due to warm-cache TRA-E5-016). An L4 forensic reviewer inspecting the file would see contradictory evidence (some segments with EXCEPTION_HANDLER records, some without) for what was actually two runs of the same source.

  This is closely related to TRA-E5-016 (warm-cache non-determinism): the warm-cache run's audit trail differs from the cold-cache run's audit trail. Combined with the append-mode defect, two consecutive CLI runs produce a 113+20=133-record file that is neither byte-identical to Run 1 nor internally consistent.
- **Suggested fix:** Three options (in order of preference):
  1. **Truncate the audit_trace.jsonl at kernel construction.** In `TRAKernel.__init__` (or `AuditTrail.__init__` when called for a fresh run), if the file exists, truncate it to 0 bytes before the first `flush()`. This matches user expectations: "I ran translate, I get THIS run's audit trail." Document that the audit trail is per-run, not cumulative.
  2. **Add a `--clear-audit` CLI flag** (default True) that truncates the audit_trace.jsonl before the kernel runs. Users who want cumulative audit trails can pass `--no-clear-audit`.
  3. **Document the limitation** in SKILL.md §4 and add a CLI warning when the audit_trace.jsonl file already exists at kernel start: "WARNING: audit_trace.jsonl exists; new records will be appended. Use `rm audit_trace.jsonl` before re-running for a clean per-run audit trail."
- **Round 5 status:** new (root cause pre-existed in `diagnostics.py:200` since Phase 2/3; R5 Track E5 did not surface because methodology always cleared the file before each run)

### TRA-E6-002 — `evidence_trace.jsonl` orphan-line resolution IMPROVED on cold-cache (NEW positive INFO)

- **Severity:** INFO (positive improvement)
- **Category:** Forensic L4 / Evidence Trace Integrity (§6.4.1 / TRA-E5-001 carry-over)
- **Finding type:** positive_verification
- **Round 5 status:** improvement (R5 Batch H commit `f782043` per-leaf translation generated per-leaf evidence records, enabling the substring-containment heuristic in `line_by_line_trace` to match more lines)
- **Evidence:**
  - Cold-cache L4 run on `to_translate.md`: `evidence_trace.jsonl` has 19 entries; **19 attributed + 0 orphans** (vs R5 cold-cache: 19 entries, 13 attributed + 6 orphans).
  - `tra/reporting.py:86`: `hits = [r.id for r in records if r.target_span and r.target_span in line]` — substring-containment heuristic.
  - R5 Batch H (`f782043`) per-leaf translation refactor: `kernel.py:585-614` walks `ctx.structural_map.iter_leaf_segments()` and calls `translate_segment` per leaf, generating per-leaf `EvidenceRecord`s via `_log_unknown_cjk` and the rule-path substitution evidence. Each leaf's evidence record has a `target_span` matching the leaf's translated text, so the substring-containment heuristic in `line_by_line_trace` can match the leaf's text to the corresponding output line.
  - R5 cold-cache had 6 orphan lines (lines 3, 11, 24, 26, 31, 33 — emoji-prefixed Chinese section titles). At HEAD `c4ecd41` cold-cache, these 6 lines are now attributed because per-leaf translation generated evidence records with `target_span` matching each section title's translated text.
  - **Caveat:** warm-cache run still has 6 orphans (see TRA-E6-003) — the per-leaf evidence records are stored in the in-memory `EvidenceRegistry` (not in the cache), so warm-cache runs don't re-populate the registry. The cold-cache improvement is therefore fragile: it only manifests on the first run after cache invalidation.
- **Detail:** R5 Track E5 finding TRA-E5-001 (WARNING: 6 orphan lines persist in evidence_trace.jsonl) is **substantially remediated** on cold-cache at HEAD `c4ecd41`. The per-leaf translation refactor (R5 Batch H) generates per-leaf evidence records that the substring-containment heuristic can match, so all 19 lines are now attributed on cold-cache. The original concern ("an L4 forensic reviewer cannot trace these output fragments back to any decision") is resolved on cold-cache runs.

  **However**, the warm-cache regression (TRA-E6-003) means the orphan lines REAPPEAR when the same source is translated again with a warm cache. The cold-cache improvement is therefore not robust — it depends on the cache being cold.
- **Suggested fix:** None for the cold-cache improvement (positive). For the warm-cache regression, see TRA-E6-003 / TRA-E5-016 (persist evidence records in the cache entry so warm-cache runs reproduce the same evidence registry).
- **Round 5 status:** improvement (TRA-E5-001 → TRA-E6-002; cold-cache orphans 6 → 0; warm-cache orphans 6 → 6, persistent)

### TRA-E6-003 — Warm-cache suppresses EXCEPTION_HANDLER records + evidence_trace attribution + ambiguity_register UNKNOWN_TERM entries (cross-ref TRA-A6-001, TRA-E5-016 persistent, INFO)

- **Severity:** INFO (cross-ref to higher-priority findings in Track A6 and R5)
- **Category:** Forensic L4 / Audit Trail Cache-State Non-Determinism (§6.4 / TRA-013 edge case)
- **Finding type:** issue (persistent — expanded scope from R5)
- **Round 5 status:** persistent (TRA-E5-016 flagged `ambiguity_register.json` + `execution_log.json` non-determinism; TRA-A6-001 in Track A6 flagged the EXCEPTION_HANDLER suppression; this audit confirms both + adds `evidence_trace.jsonl` attribution as a third affected artifact)
- **Evidence:**
  - Cold-cache L4 run on `to_translate.md`: 113 audit records (15 TRANSLATE_SEGMENT + 93 EXCEPTION_HANDLER + 5 others); `evidence_trace.jsonl` 19/19 attributed; `ambiguity_register.json` 100 entries (91 UNKNOWN_TERM + 9 ENTITY_AMBIGUITY); `execution_log.json` `unresolved_ambiguities` 100 entries.
  - Warm-cache L4 run on `to_translate.md` (same source, cache reused): 20 audit records (15 TRANSLATE_SEGMENT + 0 EXCEPTION_HANDLER + 5 others); `evidence_trace.jsonl` 13/19 attributed (6 orphans on lines 3, 11, 24, 26, 31, 33); `ambiguity_register.json` 9 entries (9 ENTITY_AMBIGUITY only, 0 UNKNOWN_TERM); `execution_log.json` `unresolved_ambiguities` 9 entries.
  - `tra/isa.py:461-468` — cache-hit early return:
    ```python
    cached = cache.get(cache_key)
    if cached is not None:
        audit.append("TRANSLATE_SEGMENT", cache_key, cached.evidence_ids)
        return cached
    ```
    The cache hit returns immediately after emitting a single TRANSLATE_SEGMENT record; it does NOT re-emit the EXCEPTION_HANDLER records that were produced on the cache-miss path, does NOT re-populate `ctx.unresolved_ambiguities` with UNKNOWN_TERM entries, and does NOT re-populate the `EvidenceRegistry` with the per-leaf evidence records.
  - `tra/cache.py:104-111` — `TranslationResult` model stores only `translation`, `evidence_ids`, `cache_hit`, `created_at`. It does NOT store the list of unknown tokens, the unresolved_ambiguities side-effects, or the full evidence records.
  - Three L4 forensic artifacts are affected:
    1. `audit_trace.jsonl` — missing 93 EXCEPTION_HANDLER records for UnknownTerm (TRA-A6-001 finding in Track A6).
    2. `ambiguity_register.json` — missing 91 UNKNOWN_TERM entries (TRA-E5-016 finding from R5).
    3. `evidence_trace.jsonl` — 6 orphan lines (NEW — not flagged by R5; surfaced by this audit's comparison of cold vs warm evidence_trace attribution).
- **Detail:** The cache-hit path at `isa.py:461-468` bypasses three side-effects of the rule-path:
  1. `_log_unknown_cjk` (called inside `_rule_translate` at `isa.py:572-573`) — populates `ctx.unresolved_ambiguities` with UNKNOWN_TERM entries AND emits EXCEPTION_HANDLER audit records per token.
  2. Per-leaf `EvidenceRecord` generation (in `_rule_translate`'s substitution loop) — populates the in-memory `EvidenceRegistry` with `target_span` records that `line_by_line_trace` uses for attribution.
  3. The per-leaf evidence IDs are stored in the cache (`cached.evidence_ids`), but the underlying `EvidenceRecord` objects are NOT — so the `EvidenceRegistry` is empty on cache hit, and `line_by_line_trace` cannot attribute lines that depend on those records.

  The result: an L4 forensic auditor inspecting artifacts from a warm-cache run sees a fundamentally impoverished trail — missing 93 EXCEPTION_HANDLER records, missing 91 UNKNOWN_TERM ambiguity entries, and 6 unattributed evidence_trace lines. The cold-cache run is the "ground truth" L4 forensic trail; the warm-cache run is a degraded view.

  This is a real L4 forensic integrity gap. The R5 Track E5 audit flagged this for `ambiguity_register.json` + `execution_log.json` (TRA-E5-016 WARNING). Track A6 (TRA-A6-001 WARNING) flagged the EXCEPTION_HANDLER suppression. This audit confirms both findings and additionally identifies `evidence_trace.jsonl` attribution as a third affected artifact.

  Combined with TRA-E6-001 (audit_trace.jsonl append-mode), the production CLI path produces a particularly confusing audit trail on the second run: the file contains Run 1's 113 records (with EXCEPTION_HANDLERs) followed by Run 2's 20 records (without EXCEPTION_HANDLERs) — internally inconsistent.
- **Suggested fix:** Persist the side-effects in the cache entry. Extend `TranslationResult` (or the cache value schema) to include:
  1. `audit_side_effects: list[dict]` — the EXCEPTION_HANDLER audit records emitted during the cache-miss translation. Re-emit them on cache hit.
  2. `unresolved_ambiguities: list[str]` — the UNKNOWN_TERM entries generated during the cache-miss translation. Replay them into `ctx.unresolved_ambiguities` on cache hit.
  3. `evidence_records: list[EvidenceRecord]` — the per-leaf evidence records generated during the cache-miss translation. Re-add them to the `EvidenceRegistry` on cache hit.

  Alternatively, document that L4 forensic runs MUST run with `cache.enabled: false` to guarantee audit-trail completeness, and add a CLI warning when `--level L4_FORENSIC` is combined with the default cache. This is the cheapest fix but punishes the user with slower re-runs.
- **Round 5 status:** persistent (TRA-E5-016 → TRA-E6-003; scope expanded to include `evidence_trace.jsonl` attribution; cross-ref TRA-A6-001)

### TRA-E6-004 — `audit_trace.jsonl` append-mode behavior test-coverage gap (NEW INFO)

- **Severity:** INFO (test coverage gap)
- **Category:** Forensic L4 / Test Coverage (TRA-013 / TRA-E6-001)
- **Finding type:** issue
- **Round 5 status:** new (test gap surfaced by TRA-E6-001)
- **Evidence:**
  - `tests/test_e2e_to_translate.py:321-343` (`TestE2EToTranslateReproducibility::test_two_runs_produce_byte_identical_audit_trace`): uses `tmp_path/run1` and `tmp_path/run2` (separate workdirs per run). Each run gets a fresh `audit_trace.jsonl` path. **Does NOT test** the case where the same `audit_trace.jsonl` path is reused across runs (which is the CLI default config.yaml behavior).
  - `tests/test_e2e_to_translate.py:345-370` (`test_two_runs_produce_byte_identical_evidence_trace`): same separate-workdir pattern.
  - `tests/test_e2e_to_translate.py:372-383` (`test_two_runs_produce_byte_identical_output`): same pattern.
  - No test asserts that running the kernel twice on the SAME `audit_trace.jsonl` path produces a byte-identical file (or fails loudly). The TRA-E6-001 defect would NOT be caught by the existing test suite.
  - No test asserts that the CLI default config.yaml path (`./audit_trace.jsonl`) is truncated between runs. The CLI integration tests in `test_outstanding_findings.py` use `tmp_path/config.yaml` with `audit_trace: {tmp_path}/audit.jsonl`, which is a fresh path per test invocation — also masking the defect.
- **Detail:** The TRA-E6-001 finding (audit_trace.jsonl append-mode) is a real production defect that the test suite does NOT catch. The reproducibility tests in `test_e2e_to_translate.py` all use isolated workdirs per run, which is the "happy path" but not the "production CLI default" path. The CLI integration tests in `test_outstanding_findings.py` similarly use isolated `tmp_path` per test.

  An auditor relying on the test suite to verify TRA-013 byte-reproducibility would conclude the invariant holds (the tests pass). But the production CLI behavior (default config.yaml paths reused across runs) actually violates TRA-013 — the audit_trace.jsonl grows across runs.
- **Suggested fix:** Add a test in `tests/test_e2e_to_translate.py` (e.g., `TestE2EToTranslateReproducibility::test_two_runs_on_same_audit_trace_path_produce_byte_identical_file`) that:
  1. Runs the kernel on `to_translate.md` at L4 with `audit_trace={tmp_path}/audit_trace.jsonl` and `cache_directory={tmp_path}/cache`.
  2. Reads `audit_trace.jsonl` bytes (Run 1).
  3. Runs the kernel AGAIN on the same source with the SAME `audit_trace` path and SAME `cache_directory`.
  4. Reads `audit_trace.jsonl` bytes (Run 2).
  5. Asserts Run 1 == Run 2 (byte-identical). This test will FAIL until TRA-E6-001 is fixed.
  
  Additionally, add a CLI integration test that runs `tra_cli translate` twice on the same CWD (default config.yaml paths) and asserts the `audit_trace.jsonl` is byte-identical across runs.
- **Round 5 status:** new (test coverage gap surfaced by TRA-E6-001)

### TRA-E6-005 — TRA-E5-005 `--force-unrecoverable` flag wired; HITL path reachable via `--interactive` (R5 carry-over, partial-fixed, positive)

- **Severity:** INFO (positive confirmation — partial fix)
- **Category:** Forensic L4 / HITL (§6.2 / TRA-E5-005 carry-over)
- **Finding type:** positive_verification
- **Round 5 status:** partial-fixed (R5 Batch F commit `bfde6dd` added the `--force-unrecoverable` debug flag; HITL path now reachable via `--force-unrecoverable --interactive` combination)
- **Evidence:**
  - `tra_cli.py:126-135` — `--force-unrecoverable` flag defined with help text.
  - `tra_cli.py:182` — `kernel = TRAKernel(cfg, registry=registry, interactive=interactive, force_unrecoverable=force_unrecoverable)` (correctly threaded to kernel).
  - `tra/kernel.py:159` — `self.force_unrecoverable = force_unrecoverable` stored on kernel.
  - `tra/kernel.py:362-371` — synthetic BLOCKING diagnostic injected into `diagnostics` list when `force_unrecoverable=True`:
    ```python
    if self.force_unrecoverable:
        diagnostics.append(
            Diagnostic(
                severity=Severity.BLOCKING,
                subsystem="force_unrecoverable",
                issue="Synthetic BLOCKING diagnostic for HITL testing",
                evidence="--force-unrecoverable flag was set",
                action="RAISE_FLAG",
            )
        )
    ```
  - `tra/isa.py:1184-1191` — `repair_segment` raises `Unrecoverable` for `subsystem="force_unrecoverable"`:
    ```python
    elif diagnostic.subsystem == "force_unrecoverable":
        raise Unrecoverable(
            "UNRECOVERABLE: --force-unrecoverable synthetic diagnostic "
            "(HITL testability flag)"
        )
    ```
  - `tra/kernel.py:688-711` — `_repair_loop` catches `Unrecoverable`, calls `_recover`, and if `self.interactive`, runs the HITL `review_decision` path.
  - `tests/test_outstanding_findings.py::TestTRA_E5_005_ForceUnrecoverableFlag` (2 tests, commit `bfde6dd`): `test_cli_translate_has_force_unrecoverable_option` + `test_force_unrecoverable_triggers_hitl_path`. Both pass (309 total pytest pass).
  - **Probe (this audit):** `TRAKernel(cfg, force_unrecoverable=True).run(...)` WITHOUT `interactive=True` on `to_translate.md` → returns normally (no ConformanceFailure). The synthetic BLOCKING diagnostic is injected into `diagnostics` (line 362), the repair loop catches `Unrecoverable` (line 688), the loop breaks (line 711 without `interactive`), and the L3 gate at line 394 re-runs `verify_output` which does NOT see the synthetic diagnostic (it was injected into `diagnostics`, not into the target text). The L3 gate passes. **Without `--interactive`, `--force-unrecoverable` is a no-op at L3/L4.**
  - **Probe (this audit):** `--force-unrecoverable --interactive` combination (per the existing test) triggers the HITL `review_decision` path — confirmed by the existing test which monkeypatches `tra.hitl.Prompt.ask`.
- **Detail:** R5 Track E5 finding TRA-E5-005 (INFO: HITL path unreachable through normal CLI input) is **partially remediated** by R5 Batch F. The `--force-unrecoverable` debug flag injects a synthetic BLOCKING diagnostic that the repair loop converts to `Unrecoverable`, which triggers the HITL `review_decision` path WHEN `--interactive` is also set. Without `--interactive`, the synthetic diagnostic is silently swallowed (the repair loop breaks without repairing, but the L3 gate re-verifies the target text — which doesn't contain the synthetic diagnostic — and passes).

  The HITL path is now reachable for e2e testing via `--force-unrecoverable --interactive`. The original concern ("HITL path is dead code without test coverage") is resolved. The residual gap (without `--interactive`, the synthetic diagnostic is silently swallowed) is acceptable because `--force-unrecoverable` is documented as a debug flag for HITL testability, not a production path.
- **Suggested fix:** None (partial-fix is acceptable for the original INFO finding). Optionally, document in `--force-unrecoverable` help text that the flag is a no-op without `--interactive`.
- **Round 5 status:** partial-fixed (TRA-E5-005 → TRA-E6-005; HITL path now reachable via `--force-unrecoverable --interactive`)

### TRA-E6-006 — TRA-013 byte-reproducibility HOLDS for cold-cache runs on isolated workdirs (R5 carry-over, positive)

- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Reproducibility (§6.4 / TRA-013)
- **Finding type:** positive_verification
- **Round 5 status:** persistent (positive) (TRA-E5-006 → TRA-E6-006)
- **Evidence:** See "Probe A" table above. All 5 probed artifacts byte-identical across 2 cold-cache L4 runs on isolated workdirs:
  - `audit_trace.jsonl` sha256 = `85363d556ab6dcbc6b14c5bb028b84e92a322ef1adc59b67f5a07363a67e5ce8` × 2 runs
  - `evidence_trace.jsonl` sha256 = `d74207405c62b3704718f0e97c2c6c1c2beea7e19bd9875cf7d9ba4537e1e099` × 2 runs
  - `ambiguity_register.json` sha256 = `c25e7c38ae0c9c12d929a8334f5f91d5e8d06c12fc1021a54fcb822fbdc35374` × 2 runs
  - `execution_log.json` sha256 = `24b847239b0b6753ab8711c50299437bb5ea1f02678a280ef7de21597108bc12` × 2 runs
  - `output.md` sha256 = `de186867cdc604892f17da85a1aa7f5f2f702ce4340679a8826d96850bd2b85a` × 2 runs
- **Detail:** The deterministic clock (`kernel.py:226-240`, `seed = self._source_hash_seed or "0" * 16`) and content-addressed evidence IDs (`diagnostics.py:45-63`, `ev_{sha256(canonical_record)[:12]}`) produce stable timestamps and IDs. The TRA-013 invariant (within-HEAD reproducibility across two cold-cache runs on isolated workdirs) HOLDS at HEAD `c4ecd41`.

  **Caveat (TRA-E6-001):** The invariant FAILS when the same `audit_trace.jsonl` path is reused across runs (CLI default config.yaml behavior). The TRA-013 invariant should be interpreted as "two cold-cache runs on ISOLATED workdirs produce byte-identical artifacts" — not "two cold-cache runs on the SAME workdir produce byte-identical artifacts" (which fails due to append-mode).
- **Suggested fix:** None for the cold-cache invariant (positive). For the same-path reuse defect, see TRA-E6-001.
- **Round 5 status:** persistent (positive) (TRA-E5-006 → TRA-E6-006; absolute sha256 differs from R5 due to Batch H per-leaf translation + Batch 2 EXCEPTION_HANDLER records enriching the audit trail; within-HEAD invariant HOLDS)

### TRA-E6-007 — All 9 L4 artifacts present + valid (R5 carry-over, positive)

- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Artifact Emission (§6.4)
- **Finding type:** positive_verification
- **Round 5 status:** persistent (positive) (TRA-E5-012 → TRA-E6-007)
- **Evidence:** See "L4 artifact inventory" table above. All 9 artifacts present with valid JSON/YAML/JSONL content:
  1. `glossary.yaml` — 11 entries (成立 → Confirmed, etc.)
  2. `entity_table.yaml` — 13 entities (L1, L2, L3, L4, ISA, BUILD, AUDIT, EMIT, TRA, ZH, EN, SUITE, GUIDE)
  3. `structural_map.json` — 15 paragraph nodes
  4. `style_profile.yaml` — voice, sentence_complexity, epistemic_mapping (4), punctuation_rules (2)
  5. `execution_log.json` — 8 post-BOOTSTRAP states in canonical order
  6. `repair_history.jsonl` — empty (0 bytes, clean run)
  7. `audit_trace.jsonl` — 113 records (15 TRANSLATE_SEGMENT + 93 EXCEPTION_HANDLER + 5 others)
  8. `evidence_trace.jsonl` — 19 entries (19 attributed + 0 orphans on cold-cache)
  9. `ambiguity_register.json` — 100 entries (91 UNKNOWN_TERM + 9 ENTITY_AMBIGUITY)
  
  L4-only artifacts gated by `_export_forensics` (`kernel.py:773-792`), which returns early unless `conformance_level == L4_FORENSIC`. L3 run produces 7 artifacts (no `evidence_trace.jsonl` or `ambiguity_register.json` — confirmed via separate L3 probe).
- **Detail:** The L4 artifact inventory is complete at HEAD `c4ecd41`. All byte sizes reasonable; all parse cleanly. The 9 artifacts include the 7 L1-L3 artifacts plus the 2 L4-only artifacts.
- **Suggested fix:** None. Positive confirmation.
- **Round 5 status:** persistent (positive) (TRA-E5-012 → TRA-E6-007)

### TRA-E6-008 — L3 gate (zero BLOCKING) passes on cold-cache L4 output (R5 carry-over, positive)

- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / L3 Gate (§8)
- **Finding type:** positive_verification
- **Round 5 status:** persistent (positive) (TRA-E5-008 + TRA-E5-009 + TRA-E5-014 → TRA-E6-008)
- **Evidence:**
  - `python -m tra_cli audit /tmp/e6_test/audit_trace.jsonl --report` →
    - `total records: 113`
    - `by severity: {'WARNING': 93}` (all from EXCEPTION_HANDLER for UnknownTerm — non-halting)
    - `by instruction: {'ANALYZE_DOCUMENT': 1, 'BUILD_GLOSSARY': 1, 'BUILD_ENTITY_TABLE': 1, 'EXCEPTION_HANDLER': 93, 'TRANSLATE_SEGMENT': 15, 'VERIFY_OUTPUT': 2}`
    - `verdict: L3 CONFORMANT`
  - `python -m tra_cli validate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md /tmp/e6_test/out.md --level L3` →
    - `Validation level=L3_STRICT — BLOCKING=0 WARNING=0 INFO=0`
    - `PASS: candidate meets the conformance gate.` (exit 0)
  - Manual `e2e_test.py` verdict: `VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics`
- **Detail:** The L3 conformance gate passes on the cold-cache L4 output. Zero BLOCKING diagnostics in the audit trail (the 93 WARNING flags are all from EXCEPTION_HANDLER records for UnknownTerm, which is non-halting per Spec §6). The standalone `validate` command also exits 0. The in-band L3 gate (kernel.py:394-420) and the out-of-band `validate` gate (validate.py) agree.
- **Suggested fix:** None. Positive confirmation.
- **Round 5 status:** persistent (positive) (TRA-E5-008/009/014 → TRA-E6-008)

### TRA-E6-009 — Per-leaf translation produces multiple TRANSLATE_SEGMENT audit records (R5 Batch H, positive)

- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Per-Leaf Translation (§3 / TRA-001 Phase 8)
- **Finding type:** positive_verification
- **Round 5 status:** new positive (R5 Batch H commit `f782043` implemented per-leaf translation; this audit confirms it produces the expected multiple TRANSLATE_SEGMENT records)
- **Evidence:**
  - Cold-cache L4 run on `to_translate.md`: 15 TRANSLATE_SEGMENT records in `audit_trace.jsonl` (seq_ids 22, 26, 33, 36, 46, 48, 58, 61, 67, 76, 78, 80, 92, 94, 110).
  - `compilation_artifacts/structural_map.json` — 15 paragraph nodes (all with non-empty `text`).
  - `tra/memory.py:144-171` (`StructuralMap.iter_leaf_segments`) — yields `(idx, node)` for nodes with `kind in {HEADING, PARAGRAPH, LIST_ITEM, TABLE_CELL}` and `text is not None`.
  - `tra/kernel.py:585-614` (`_execute_translation`) — iterates `iter_leaf_segments()` and calls `translate_segment` per leaf (when `llm_translate is None`).
  - Each TRANSLATE_SEGMENT record has a unique `input_hash` (content-addressed per leaf text):
    - seq=22: `e7e4075b612edcc2...` (leaf 0: "在详细审阅了 nordeim/Translation-Runtime-Architecture...")
    - seq=26: `99e2e518eb568b03...` (leaf 1: "🧠 核心架构：将翻译流程...")
    - ... etc.
  - Each TRANSLATE_SEGMENT record has its own `evidence_chain` (per-leaf evidence records).
  - R5 cold-cache had 1 TRANSLATE_SEGMENT record (whole-doc translation, pre-Batch-H). HEAD `c4ecd41` has 15 (per-leaf translation, post-Batch-H). **15× increase** in per-segment audit granularity.
  - **Caveat (TRA-A6-003):** Track A6 found that the structural map creates duplicate leaf segments for list items (LIST_ITEM + PARAGRAPH child with same text). On `to_translate.md` (no list items), this duplicate-leaf issue does NOT manifest — 15 logical leaves = 15 TRANSLATE_SEGMENT records. On list-heavy sources, the duplicate-leaf issue would inflate the count.
- **Detail:** R5 Batch H (`f782043`) implemented TRA-001 Phase 8 per-leaf translation. The kernel's `_execute_translation` now walks `ctx.structural_map.iter_leaf_segments()` and calls `translate_segment` per leaf segment (when no LLM callback is supplied). This gives per-segment cache keys, per-segment evidence chains, and meaningful per-leaf audit records. The 15 TRANSLATE_SEGMENT records on `to_translate.md` (which has 15 paragraph leaves) confirm per-leaf translation is working correctly in the production CLI path (no LLM).

  **Test coverage gap:** The e2e tests (`tests/test_e2e_to_translate.py`) use the LLM hijack (`llm_translate=manual_llm`), which forces whole-doc translation (1 TRANSLATE_SEGMENT record). The tests assert the canonical 6-record sequence (ANALYZE → BUILD_GLOSSARY → BUILD_ENTITY_TABLE → TRANSLATE_SEGMENT → VERIFY_OUTPUT → VERIFY_OUTPUT). They do NOT exercise the per-leaf translation path. The 15-record production-CLI behavior is therefore not verified by the e2e tests — only by the unit tests for `iter_leaf_segments` and the per-leaf translation code paths.
- **Suggested fix:** None for the per-leaf translation itself (positive). For the test coverage gap, add an e2e test that runs the kernel WITHOUT the LLM hijack (production CLI path) and asserts ≥2 TRANSLATE_SEGMENT records (per-leaf translation working).
- **Round 5 status:** new positive (TRA-E5-004 → TRA-E6-009 partial — per-leaf translation working, but `RepairAttempt.segment_index` still always 0 per TRA-A6-002)

### TRA-E6-010 — EXCEPTION_HANDLER audit records present for UnknownTerm (R5 Batch 2, positive)

- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Exception Recovery (§6 UNKNOWN_TERM / TRA-A5-003)
- **Finding type:** positive_verification
- **Round 5 status:** new positive (R5 Batch 2 commit `36246bb` wired UnknownTerm to emit EXCEPTION_HANDLER audit records via `audit.append(...)` in `translate_segment`; this audit confirms 93 such records are present on cold-cache L4 run)
- **Evidence:**
  - Cold-cache L4 run on `to_translate.md`: 93 EXCEPTION_HANDLER records in `audit_trace.jsonl`.
  - All 93 records have `input_hash=UNKNOWN_TERM`, `artifact_snapshot.severity=WARNING`, `artifact_snapshot.action=PRESERVE_SOURCE`, `artifact_snapshot.source_term=<CJK token>`.
  - Sample first 5 records:
    - seq=3: `source_term=在详细审阅了`
    - seq=4: `source_term=仓库的全部内容后`
    - seq=5: `source_term=我的核心评价是`
    - seq=6: `source_term=这是一个设计严谨`
    - seq=7: `source_term=极具野心的规范性框架`
  - `tra/isa.py:553-575` — per-token `audit.append("EXCEPTION_HANDLER", "UNKNOWN_TERM", ...)` call inside `translate_segment`'s rule path.
  - `tests/test_outstanding_findings.py::TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover::test_unknown_term_emits_exception_handler_audit_record` — regression test passes (309 total pytest pass).
  - **Caveat (TRA-A6-001 / TRA-E6-003):** Warm-cache runs suppress these 93 EXCEPTION_HANDLER records (cache-hit path at `isa.py:461-468` returns early without invoking the rule path). The positive confirmation is for cold-cache runs only.
- **Detail:** R5 Track E5 finding TRA-E5-002 (INFO partial-fixed: UnknownTerm logged to ambiguity register via direct call, but no EXCEPTION_HANDLER audit record) is **fully remediated** on cold-cache at HEAD `c4ecd41`. R5 Batch 2 (`36246bb`, TRA-A5-003) wired UnknownTerm to emit EXCEPTION_HANDLER audit records via `audit.append(...)`. The 93 EXCEPTION_HANDLER records on `to_translate.md` confirm the fix is working end-to-end on cold-cache.

  **Caveat:** The warm-cache regression (TRA-A6-001 / TRA-E6-003) means the EXCEPTION_HANDLER records are silently dropped on subsequent runs. The cold-cache improvement is therefore not robust.
- **Suggested fix:** None for the cold-cache fix (positive). For the warm-cache regression, see TRA-E6-003.
- **Round 5 status:** new positive (TRA-E5-002 → TRA-E6-010; cold-cache EXCEPTION_HANDLER records now present, was 0 in R5)

### TRA-E6-011 — Hash chain integrity: VERIFY_OUTPUT input_hash matches emitted target (R5 carry-over, positive)

- **Severity:** INFO (positive confirmation)
- **Category:** Forensic L4 / Audit Trail Hash-Chain Integrity (§6.4 / TRA-037)
- **Finding type:** positive_verification
- **Round 5 status:** persistent (positive) (TRA-E5-010 → TRA-E6-011)
- **Evidence:** L4 cold-cache run on `to_translate.md`:
  - `audit_trace.jsonl` seq=111 VERIFY_OUTPUT `input_hash=de186867cdc60489`
  - `audit_trace.jsonl` seq=112 VERIFY_OUTPUT `input_hash=de186867cdc60489`
  - Emitted `/tmp/e6_test/out.md` `sha256[:16]=de186867cdc60489`
  - **MATCH=True** on both VERIFY_OUTPUT records (`to_translate.md` has no internal links, so initial-verify and L3-gate-verify hash the same target).
  - `tra/kernel.py:386` (TRA-037 fix: `_rewrite_anchors(target)` runs BEFORE the L3 gate at line 394-420).
- **Detail:** Round 2's TRA-E-002 BLOCKING finding (audit trail's VERIFY_OUTPUT hash was computed on pre-rewrite target while emitted target was post-rewrite) is resolved. The L3 gate's `verify_output` now hashes the post-rewrite target, which matches the emitted file's hash when the gate passes. Hash-chain integrity holds at HEAD `c4ecd41`.
- **Suggested fix:** None. Positive confirmation.
- **Round 5 status:** persistent (positive) (TRA-E5-010 → TRA-E6-011)

### TRA-E6-012 — TRA-E5-013 double VERIFY_OUTPUT at L3+ still undocumented (R5 carry-over, persistent)

- **Severity:** INFO (documentation)
- **Category:** Forensic L4 / Audit Trail Structure (§7)
- **Finding type:** issue
- **Round 5 status:** persistent (TRA-E5-013 → TRA-E6-012)
- **Evidence:**
  - L4 `audit_trace.jsonl` has 2 VERIFY_OUTPUT records (seq 111, 112); L1/L2 would have 1 (no L3 gate).
  - `audit_trace.jsonl` seq=111 VERIFY_OUTPUT `artifact_snapshot={}`, no `purpose` field
  - `audit_trace.jsonl` seq=112 VERIFY_OUTPUT `artifact_snapshot={}`, no `purpose` field
  - No `purpose` field on either VERIFY_OUTPUT record (R4 Track E4 suggested adding `{"purpose": "L3_gate"}` to seq=112).
- **Detail:** At L3_STRICT and L4_FORENSIC, `verify_output` is called twice:
  1. `kernel.py:357` — initial diagnostics for the repair loop
  2. `kernel.py:398` — final L3 gate check after the repair loop and after `_rewrite_anchors`
  Both calls append a `VERIFY_OUTPUT` audit record. The `execution_log.json` records only one VERIFY_OUTPUT state transition. The double record is an ISA-level artifact and is still undocumented in user-facing SKILL.md. R5 did not add a `purpose` field.

  Note: The TRA-E5-013 (R5) docstring at `kernel.py:346-356` (added by R5 Batch E commit `57997a8`) DOES document the double-verify as intentional. But the user-facing SKILL.md §4 still does not mention it.
- **Suggested fix:** Either (a) add a `purpose` field to the second VERIFY_OUTPUT record (e.g., `{"purpose": "L3_gate"}`) to distinguish it from the initial verify; or (b) document in SKILL.md §4 that L3+ runs produce two VERIFY_OUTPUT records (initial + L3 gate).
- **Round 5 status:** persistent (TRA-E5-013 → TRA-E6-012)

### TRA-E6-013 — TRA-E5-003 EMPTY_SOURCE raises BrokenMarkdown with BLOCKING severity (R5 carry-over, fixed, positive)

- **Severity:** INFO (positive confirmation — R5 fix verified holding)
- **Category:** Forensic L4 / Exception Recovery (§6 EMPTY_SOURCE / TRA-E5-003 carry-over)
- **Finding type:** positive_verification
- **Round 5 status:** fixed (R5 Batch E commit `57997a8` changed `raise TRAException("EMPTY_SOURCE")` to `raise BrokenMarkdown(detail="EMPTY_SOURCE: ...")`; this audit confirms the fix is holding at HEAD `c4ecd41`)
- **Evidence:**
  - `tra/isa.py:101-110`:
    ```python
    if not source.strip():
        # TRA-E5-003 (round 5): raise BrokenMarkdown (not base TRAException)
        # so route_exception dispatches to recover_broken_markdown which
        # returns Severity.BLOCKING per Spec §6 BROKEN_MARKDOWN. Previously
        # raised TRAException("EMPTY_SOURCE") which fell through to the
        # default route_exception return (WARNING + PRESERVE_SOURCE) —
        # violating the Spec §6 "Blocking Error" mandate.
        raise BrokenMarkdown(
            detail="EMPTY_SOURCE: document contains no translatable content"
        )
    ```
  - `tra/recovery.py` — `route_exception` dispatches `BrokenMarkdown` to `recover_broken_markdown` which returns `Severity.BLOCKING` + `RecoveryAction.HALT` per Spec §6.
  - `tests/test_outstanding_findings.py::TestTRA_E5_003_EmptySourceRaisesBrokenMarkdown` — regression test passes (309 total pytest pass).
  - Cross-ref: Track A6 TRA-A6-011 also confirms EMPTY_SOURCE raises BrokenMarkdown with BLOCKING severity end-to-end (L3 ConformanceFailure).
- **Detail:** R5 Track E5 finding TRA-E5-003 (INFO: Empty source recovery severity still WARNING) is **fully remediated** at HEAD `c4ecd41`. The code now raises `BrokenMarkdown` (not base `TRAException`) for empty source, which `route_exception` dispatches to `recover_broken_markdown` returning `Severity.BLOCKING`. The EXCEPTION_HANDLER audit record's `severity` field is now `BLOCKING` (not `WARNING`) and `code` is `BROKEN_MARKDOWN` (not `TRA_ERROR`), matching Spec §6 EMPTY_SOURCE/BROKEN_MARKDOWN recovery procedure.
- **Suggested fix:** None. Positive confirmation.
- **Round 5 status:** fixed (TRA-E5-003 → TRA-E6-013)

## Round 5 Track E5 carry-over status matrix

| Round 5 ID | Title | Round 6 status | Round 6 ID |
|---|---|---|---|
| TRA-E5-001 | Evidence trace orphan lines persist | **partial-fixed** (cold-cache orphans 6 → 0; warm-cache 6 → 6 persistent) | TRA-E6-002 + TRA-E6-003 |
| TRA-E5-002 | UnknownTerm still never raised | **fixed** (cold-cache: 93 EXCEPTION_HANDLER records now present; warm-cache: persistent — see TRA-E6-003) | TRA-E6-010 |
| TRA-E5-003 | Empty source recovery severity still WARNING | **fixed** (raises BrokenMarkdown with BLOCKING) | TRA-E6-013 |
| TRA-E5-004 | RepairAttempt.segment_index always 0 | **persistent** (cross-ref TRA-A6-002 — kernel's `_repair_loop` does not pass `segment_index`) | (covered by TRA-A6-002) |
| TRA-E5-005 | HITL path unreachable through CLI | **partial-fixed** (`--force-unrecoverable --interactive` triggers HITL path) | TRA-E6-005 |
| TRA-E5-006 | Byte-reproducibility confirmed (positive) | **persistent (positive)** (cold-cache isolated workdirs: HOLDS; same-path reuse: FAILS — see TRA-E6-001) | TRA-E6-006 + TRA-E6-001 |
| TRA-E5-007 | TRA-071 BROKEN_MARKDOWN reachable (positive) | **persistent (positive)** (cross-ref TRA-A6; verified at HEAD via 309 passing tests) | (covered by Track A6) |
| TRA-E5-008 | TRA-036 L3 gate blocks empty source (positive) | **persistent (positive)** | TRA-E6-008 |
| TRA-E5-009 | TRA-037 L3 gate checks unresolved_ambiguities (positive) | **persistent (positive)** | TRA-E6-008 |
| TRA-E5-010 | TRA-037 link rewrite hash matches emitted (positive) | **persistent (positive)** | TRA-E6-011 |
| TRA-E5-011 | Audit trail state sequence matches _KERNEL_ORDER (positive) | **persistent (positive)** (cross-ref Track A6; verified at HEAD) | (covered by Track A6) |
| TRA-E5-012 | All 9 artifacts present, exit 0 (positive) | **persistent (positive)** | TRA-E6-007 |
| TRA-E5-013 | Double VERIFY_OUTPUT at L3+ (documentation) | **persistent** | TRA-E6-012 |
| TRA-E5-014 | TRA-093 false-positive BROKEN_LINK FIXED (positive) | **persistent (positive)** (cross-ref Track A6; verified at HEAD) | (covered by Track A6) |
| TRA-E5-015 | `style_profile.yaml` undocumented in SKILL.md §4 | **fixed** (SKILL.md:146 now lists "style profile") | (resolved, no Round 6 finding) |
| TRA-E5-016 | L4 ambiguity_register + execution_log non-deterministic across cache states | **persistent** (scope expanded: evidence_trace.jsonl attribution also affected) | TRA-E6-003 |
| TRA-E5-017 | `audit --report` Mermaid + summary (positive) | **persistent (positive)** (verified at HEAD — see Probe 4 in probe table) | (covered by Track A6) |
| TRA-E5-018 | TRA-042 extended structural verification works (positive) | **persistent (positive)** (cross-ref Track A6) | (covered by Track A6) |
| TRA-E5-019 | TRA-072 PolicyResolver severity arbitration works (positive) | **persistent (positive)** (cross-ref Track A6) | (covered by Track A6) |
| TRA-E5-020 | L4 ambiguity_register content test-coverage gap | **persistent** (still no test asserts L4 ambiguity_register content end-to-end on canonical source) | (covered by Track A6 test-coverage findings) |

**Round 6 net delta vs R5 Track E5:** 0 BLOCKING; 1 new WARNING (TRA-E6-001 — audit_trace.jsonl append-mode, pre-existing defect newly surfaced); 1 new positive INFO (TRA-E6-002 — evidence_trace orphan resolution improved on cold-cache); 1 new INFO cross-ref (TRA-E6-003 — warm-cache suppresses EXCEPTION_HANDLER + evidence_trace attribution + ambiguity_register, cross-ref TRA-A6-001); 1 new INFO (TRA-E6-004 — test-coverage gap for TRA-E6-001); 2 R5 findings fixed (TRA-E5-003 EMPTY_SOURCE, TRA-E5-015 SKILL.md style_profile); 1 R5 finding partial-fixed (TRA-E5-005 HITL path); 1 R5 finding substantially remediated on cold-cache (TRA-E5-001 orphan lines). No regressions.

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype
source .venv/bin/activate

# 1. Cold-cache L4 Run 1 (isolated workdir)
rm -rf /tmp/e6_rep1
python -c "
import sys; sys.path.insert(0, '.')
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
from pathlib import Path
cfg = BootstrapConfig.from_yaml('config.yaml').model_copy(update={
    'base_dir': '/tmp/e6_rep1', 'conformance_level': ConformanceLevel.L4_FORENSIC,
    'audit_trace': '/tmp/e6_rep1/audit_trace.jsonl',
    'compilation_dir': '/tmp/e6_rep1/compilation_artifacts',
    'cache_directory': '/tmp/e6_rep1/cache',
})
src = Path('/home/z/my-project/Translation-Runtime-Architecture/to_translate.md').read_text()
kernel = TRAKernel(cfg)
target = kernel.run(src)
Path('/tmp/e6_rep1/out.md').write_text(target)
"
sha256sum /tmp/e6_rep1/audit_trace.jsonl /tmp/e6_rep1/compilation_artifacts/evidence_trace.jsonl \
  /tmp/e6_rep1/compilation_artifacts/ambiguity_register.json /tmp/e6_rep1/out.md
# → 85363d55...  d74207405c62...  c25e7c38...  de186867cdc6...

# 2. Cold-cache L4 Run 2 (separate isolated workdir — TRA-013 probe)
rm -rf /tmp/e6_rep2
# (same script with /tmp/e6_rep2)
sha256sum /tmp/e6_rep2/audit_trace.jsonl /tmp/e6_rep2/compilation_artifacts/evidence_trace.jsonl \
  /tmp/e6_rep2/compilation_artifacts/ambiguity_register.json /tmp/e6_rep2/out.md
# → 85363d55...  d74207405c62...  c25e7c38...  de186867cdc6... (IDENTICAL to Run 1)

# 3. CLI default-path append-mode probe (TRA-E6-001)
rm -rf /tmp/e6_cli && mkdir -p /tmp/e6_cli && cd /tmp/e6_cli
cp /home/z/my-project/Translation-Runtime-Architecture/tra-prototype/config.yaml .
python -m tra_cli translate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md --level L4 -o out1.md
wc -l audit_trace.jsonl    # → 113
python -m tra_cli translate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md --level L4 -o out2.md
wc -l audit_trace.jsonl    # → 133 (NOT 113 — TRA-E6-001 defect)
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# 4. Warm-cache non-determinism probe (TRA-E6-003 / TRA-E5-016 persistent)
rm -rf /tmp/e6_cold /tmp/e6_warm2
# Cold-cache run on /tmp/e6_cold (script above)
# Warm-cache run on /tmp/e6_warm2 (reusing /tmp/e6_cold/cache)
python3 -c "
import json
for label, p in [('cold', '/tmp/e6_cold/compilation_artifacts/ambiguity_register.json'),
                 ('warm', '/tmp/e6_warm2/compilation_artifacts/ambiguity_register.json')]:
    d = json.load(open(p))
    print(f'{label}: {len(d)} entries')
"
# → cold: 100 entries / warm: 9 entries (TRA-E6-003 / TRA-E5-016 persistent)

# 5. L3 validate gate
python -m tra_cli validate /home/z/my-project/Translation-Runtime-Architecture/to_translate.md /tmp/e6_rep1/out.md --level L3
# → PASS: candidate meets the conformance gate. (exit 0)

# 6. Audit --report (Mermaid + conformance summary)
python -m tra_cli audit /tmp/e6_rep1/audit_trace.jsonl --report
# → 113-record table + conformance summary (verdict: L3 CONFORMANT) + Mermaid flowchart LR

# 7. Hash chain integrity probe
python3 -c "
import hashlib, json
target = open('/tmp/e6_rep1/out.md').read()
print('emitted sha256[:16]:', hashlib.sha256(target.encode()).hexdigest()[:16])
recs = [json.loads(l) for l in open('/tmp/e6_rep1/audit_trace.jsonl') if l.strip()]
for r in [r for r in recs if r['isa_instruction']=='VERIFY_OUTPUT']:
    print(f\"  seq={r['sequence_id']} input_hash={r['input_hash']}\")"
# → emitted: de186867cdc60489 / seq=111: de186867cdc60489 / seq=112: de186867cdc60489 (MATCH)

# 8. Per-leaf translation record count
python3 -c "
import json
smap = json.load(open('/tmp/e6_rep1/compilation_artifacts/structural_map.json'))
def count_leaves(nodes):
    leaf_kinds = {'heading', 'paragraph', 'list_item', 'table_cell'}
    n = sum(1 + count_leaves(nd.get('children', [])) for nd in nodes
            if nd['kind'] in leaf_kinds and nd.get('text') is not None)
    # the above double-counts; use the simple walk
    return n
def walk_leaves(nodes):
    leaf_kinds = {'heading', 'paragraph', 'list_item', 'table_cell'}
    n = 0
    for nd in nodes:
        if nd['kind'] in leaf_kinds and nd.get('text') is not None:
            n += 1
        n += walk_leaves(nd.get('children', []))
    return n
print(f'structural_map leaf count: {walk_leaves(smap[\"nodes\"])}')
recs = [json.loads(l) for l in open('/tmp/e6_rep1/audit_trace.jsonl') if l.strip()]
print(f'TRANSLATE_SEGMENT records: {sum(1 for r in recs if r[\"isa_instruction\"]==\"TRANSLATE_SEGMENT\")}')
"
# → structural_map leaf count: 15 / TRANSLATE_SEGMENT records: 15 (MATCH)

# 9. EXCEPTION_HANDLER for UnknownTerm
python3 -c "
import json
recs = [json.loads(l) for l in open('/tmp/e6_rep1/audit_trace.jsonl') if l.strip()]
eh = [r for r in recs if r['isa_instruction']=='EXCEPTION_HANDLER']
print(f'EXCEPTION_HANDLER records: {len(eh)}')
print(f'All UNKNOWN_TERM? {all(r[\"input_hash\"]==\"UNKNOWN_TERM\" for r in eh)}')
print(f'All WARNING severity? {all(r[\"artifact_snapshot\"].get(\"severity\")==\"WARNING\" for r in eh)}')
"
# → EXCEPTION_HANDLER records: 93 / All UNKNOWN_TERM? True / All WARNING severity? True

# 10. Full pytest suite
python -m pytest tests/ 2>&1 | tail -1
# → 309 passed in 3.09s

# 11. e2e pytest suite
python -m pytest tests/test_e2e_to_translate.py -v 2>&1 | tail -1
# → 12 passed in 0.35s

# 12. Manual e2e_test.py
rm -rf e2e_audit_trace.jsonl e2e_artifacts e2e_cache
python e2e_test.py 2>&1 | tail -1
# → VERDICT: L3 CONFORMANT — zero BLOCKING diagnostics
```

## Conclusion

The L4 forensic pipeline at HEAD `c4ecd41` is **healthy on cold-cache isolated runs and free of new BLOCKING findings**. All 309 pytest tests pass (12 in the e2e suite). The manual `e2e_test.py` reports `L3 CONFORMANT — zero BLOCKING diagnostics`. The L4 translate command exits 0 and produces all 9 expected runtime artifacts with valid YAML/JSON/JSONL content. All 6 task-scope verification items PASS:

1. **TRA-013 byte-reproducibility (cold-cache, isolated workdirs):** HOLDS — `audit_trace.jsonl` sha256 `85363d55...` × 2 runs (byte-identical). ✅
2. **9 L4 artifacts present:** YES — all 9 artifacts present + parse cleanly. ✅
3. **L3 gate (zero BLOCKING):** PASSES — `audit --report` verdict `L3 CONFORMANT`; `validate --level L3` exit 0. ✅
4. **Per-leaf translation produces multiple TRANSLATE_SEGMENT records:** YES — 15 records (matches structural_map's 15 leaf segments). ✅
5. **EXCEPTION_HANDLER audit records present for UnknownTerm:** YES — 93 records, all `input_hash=UNKNOWN_TERM`, `severity=WARNING`, `action=PRESERVE_SOURCE`. ✅
6. **Hash chain integrity (VERIFY_OUTPUT input_hash matches emitted target):** YES — both VERIFY_OUTPUT records (`de186867cdc60489`) match emitted target `sha256[:16]` (`de186867cdc60489`). ✅

**The one new WARNING (TRA-E6-001)** is a pre-existing defect newly surfaced by this audit's methodology: `AuditTrail.flush()` opens the audit_trace.jsonl file in append mode ("a") and never truncates. The CLI default config.yaml path (`./audit_trace.jsonl`) is reused across runs, so two consecutive `python -m tra_cli translate` invocations produce a 133-record file (113 cold-cache + 20 warm-cache appended) that is NOT byte-identical to the first run's 113-record file. **TRA-013 byte-reproducibility FAILS when the audit_trace path is reused without explicit `rm`.** The R5 Track E5 audit did not surface this because their methodology always did `rm -rf audit_trace.jsonl` before each run. The `tests/test_e2e_to_translate.py::TestE2EToTranslateReproducibility` tests also use isolated workdirs per run, so they pass.

**Improvement vs R5 (TRA-E6-002):** R5 Batch H (per-leaf translation) generates per-leaf `EvidenceRecord`s with `target_span` matching each leaf's translated text, enabling the `line_by_line_trace` substring-containment heuristic to attribute all 19 lines on cold-cache (was 6 orphans in R5). The original TRA-E5-001 WARNING (orphan lines persist) is **substantially remediated on cold-cache** (downgraded to INFO positive). The warm-cache regression (TRA-E6-003) means the orphans reappear on subsequent runs — the cold-cache improvement is fragile.

**R5 findings fixed at HEAD:** TRA-E5-003 (EMPTY_SOURCE raises BrokenMarkdown with BLOCKING — R5 Batch E), TRA-E5-015 (style_profile.yaml in SKILL.md §4 — R5 Batch E). TRA-E5-005 (HITL path) is partial-fixed via `--force-unrecoverable --interactive` (R5 Batch F). TRA-E5-002 (UnknownTerm EXCEPTION_HANDLER records) is fixed on cold-cache via R5 Batch 2 (TRA-A5-003).

**Persistent R5 findings:** TRA-E5-004 (RepairAttempt.segment_index always 0 — cross-ref TRA-A6-002), TRA-E5-013 (double VERIFY_OUTPUT undocumented), TRA-E5-016 (cache-state non-determinism — expanded scope in TRA-E6-003 to include evidence_trace.jsonl attribution), TRA-E5-020 (L4 ambiguity_register content test-coverage gap). All INFO severity.

**No new BLOCKING. No regressions.** The L4 forensic pipeline at HEAD `c4ecd41` is functioning as designed on cold-cache isolated runs, with one newly-surfaced WARNING (TRA-E6-001) that warrants Round 7 remediation.
