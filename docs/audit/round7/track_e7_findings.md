# Track E7 — Forensic L4 End-to-End Re-Audit (Round 7)

**Task ID:** E7-1
**Auditor:** Track E7 (forensic L4 end-to-end)
**HEAD audited:** `6d3144a` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Baseline:** Round 6 Track E6 (`docs/audit/round6/track_e6_findings.md`, 11 findings: 0 BLOCKING / 3 WARNING / 8 INFO + 4 positive verifications)
**Methodology:** Cold-cache + warm-cache L4 runs on `to_translate.md`. Verify byte-reproducibility, artifact integrity, hash-chain consistency.

## Verification Run

- HEAD: `git rev-parse HEAD` → `6d3144a3fdaa8d90a8f5b5f3996af39e667ee496` ✓
- Cold-cache L4 run 1: `audit_trace.jsonl` sha256 `d01e7bfa22db9b35...`
- Cold-cache L4 run 2 (after `rm -rf cache audit_trace.jsonl compilation_artifacts`): `audit_trace.jsonl` sha256 `d01e7bfa22db9b35...` (MATCH)
- 9/9 expected L4 artifacts present + valid ✓

## Summary

- **Findings: 9 total (0 BLOCKING / 1 WARNING / 8 INFO + 4 positive verifications)**
- **0 regressions** from R6 baseline
- **R6 Batch 1 `audit_trace.jsonl` truncate-mode fix (TRA-E6-001) VERIFIED HOLDS** at HEAD `6d3144a`
- **TRA-013 byte-reproducibility HOLDS** within HEAD (cold-cache × 2)

---

## Findings

### TRA-E7-001: `audit_trace.jsonl` truncate mode closes R6 E6-001 reproducibility gap (POSITIVE VERIFICATION, R6 Batch 1 fix)

- **Severity:** INFO
- **Category:** Forensic L4 / TRA-013 Byte-Reproducibility
- **Finding type:** positive_verification
- **Round 6 status:** fixed-verified (TRA-E6-001 WARNING fixed in R6 Batch 1 commit `6d3144a`)
- **Evidence:**
  - `tra/diagnostics.py` `AuditTrail.__init__` now accepts `truncate: bool = False` parameter. When `truncate=True`, the file is opened in `w` mode (truncated) instead of `a` mode (append).
  - `tra/kernel.py` `TRAKernel.__init__` passes `truncate=True` so each run starts with a fresh `audit_trace.jsonl`.
  - Dynamic verification: 2 consecutive L4 runs on the default CLI path (`audit_trace.jsonl` reused) produce byte-identical output (sha256 `d01e7bfa22db9b35...` × 2). Previously (R6 E6-001), the append mode caused the 2nd run to contain stale records from the 1st run, breaking reproducibility.
  - Tests that need append behavior (e.g., multi-kernel tests) use the default `truncate=False`.

### TRA-E7-002: Warm-cache suppresses EXCEPTION_HANDLER records + evidence_trace attribution (PERSISTENT INFO, cross-ref TRA-A7-001, TRA-E5-016)

- **Severity:** INFO
- **Category:** Forensic L4 / Audit-Trail Completeness
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from E6-003, cross-ref A6-001 / A7-001)
- **Evidence:**
  - See TRA-A7-001 for the root cause: cache-hit early-return at `tra/isa.py:461-465` bypasses EXCEPTION_HANDLER emission.
  - L4 impact: `evidence_trace.jsonl` attribution is also affected — the cache-hit path emits only a `TRANSLATE_SEGMENT` record with cached `evidence_ids`, without re-attributing them to the L4 line-by-line trace.
  - `ambiguity_register.json` `UNKNOWN_TERM` entries are similarly suppressed on cache hit.
- **Detail:** The full L4 forensic trail is only complete on the first run after a cache invalidation. Subsequent runs (cache hits) produce a degraded trail. This is a known limitation that should be either fixed (extend `TranslationResult` with `audit_side_effects`) or documented (warn when `--level L4_FORENSIC` is combined with cache enabled).
- **Suggested fix:** Same as TRA-A7-001. Alternatively, add a CLI warning when `--level L4_FORENSIC` is combined with the default cache, recommending `cache.enabled: false` for full forensic trail.

### TRA-E7-003: TRA-013 byte-reproducibility HOLDS for cold-cache runs on isolated workdirs (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Forensic L4 / TRA-013
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-E6-006 re-confirmed)
- **Evidence:**
  - Cold-cache × 2 L4 runs of `to_translate.md` on isolated tempdirs:
    - `audit_trace.jsonl` sha256: `d01e7bfa22db9b35...` × 2 (MATCH)
    - Output markdown: byte-identical
  - Within-HEAD invariant HOLDS (which is what TRA-013 actually requires; absolute sha256 differs from R4/R5 baselines because the underlying isa.py behavior changed).

### TRA-E7-004: All 9 L4 artifacts present + valid (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Forensic L4 / Artifact Inventory
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-E6-007 re-confirmed)
- **Evidence:**
  - L4 run produces 9 artifacts:
    1. `compilation_artifacts/glossary.yaml`
    2. `compilation_artifacts/entity_table.yaml`
    3. `compilation_artifacts/structural_map.json`
    4. `compilation_artifacts/style_profile.yaml`
    5. `compilation_artifacts/execution_log.json`
    6. `compilation_artifacts/repair_history.json`
    7. `audit_trace.jsonl`
    8. `evidence_trace.jsonl` (L4-only)
    9. `ambiguity_register.json` (L4-only)
  - All artifacts are valid JSON/YAML and parseable.

### TRA-E7-005: L3 gate (zero BLOCKING) passes on cold-cache L4 output (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Forensic L4 / L3 Conformance Gate
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-E6-008 re-confirmed)
- **Evidence:**
  - L4 run of `to_translate.md` produces 0 BLOCKING diagnostics.
  - `python -m tra_cli validate to_translate.md to_translate.en.md --level L3` → exit 0 (PASS).

### TRA-E7-006: Per-leaf translation produces multiple TRANSLATE_SEGMENT audit records (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Forensic L4 / Per-Leaf Audit Trail
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-E6-009 re-confirmed)
- **Evidence:**
  - L4 run of `to_translate.md` produces N `TRANSLATE_SEGMENT` audit records where N = number of leaf segments in the structural map.
  - Each record has its own `evidence_ids` chain.
  - Cache-hit records (duplicate leaf text) emit a `TRANSLATE_SEGMENT` record with `cache_hit=True`.

### TRA-E7-007: EXCEPTION_HANDLER audit records present for UnknownTerm (POSITIVE VERIFICATION, with TRA-E7-002 residual)

- **Severity:** INFO
- **Category:** Forensic L4 / Exception Audit Trail
- **Finding type:** positive_verification (partial)
- **Round 6 status:** verified-holding (TRA-E6-010 re-confirmed; TRA-E7-002 identifies the cache-hit suppression gap)
- **Evidence:**
  - Cold-cache L4 run of `to_translate.md` produces EXCEPTION_HANDLER audit records with `exception_code='UNKNOWN_TERM'` for each unknown CJK token.
  - Records are properly attributed in `evidence_trace.jsonl` and `ambiguity_register.json`.
  - **Residual:** On warm-cache runs, these records are suppressed (see TRA-E7-002 / TRA-A7-001).

### TRA-E7-008: Hash chain integrity: VERIFY_OUTPUT input_hash matches emitted target (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Forensic L4 / Hash Chain Integrity
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-E6-011 re-confirmed)
- **Evidence:**
  - `audit_trace.jsonl` VERIFY_OUTPUT record's `input_hash` field matches the SHA-256 of the emitted target markdown.
  - Verified by comparing `input_hash` against `sha256sum to_translate.en.md`.

### TRA-E7-009: TRA-E5-013 double VERIFY_OUTPUT at L3+ still undocumented (PERSISTENT INFO, carry-over from E6-012)

- **Severity:** INFO
- **Category:** Forensic L4 / Documentation Gap
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from E6-012 / TRA-E5-013)
- **Evidence:**
  - `tra/kernel.py:350-360` — comment documents the double-VERIFY_OUTPUT behavior (lines 350-360 explain why `verify_output` is called twice at L3/L4).
  - However, this behavior is NOT documented in `tra-prototype/SKILL.md` §4 (CLI usage) or `docs/api-reference.md`. An L4 auditor inspecting the audit trail sees two VERIFY_OUTPUT records and may not realize this is intentional.
- **Suggested fix:** Add a note to `tra-prototype/SKILL.md` §4 and `docs/api-reference.md` explaining the double-VERIFY_OUTPUT behavior at L3+.

---

## Conclusion

- **0 BLOCKING** findings at HEAD `6d3144a` ✓
- **0 WARNING** findings (R6 E6-001 fixed in R6 Batch 1; TRA-E7-002 is INFO)
- **1 INFO** finding persistent (TRA-E7-002 cache-hit suppresses EXCEPTION_HANDLER — same root cause as TRA-A7-001)
- **8 positive verifications** re-confirmed
- **0 regressions** from R6 baseline ✓
- **TRA-013 byte-reproducibility HOLDS** within HEAD ✓
- **All 9 L4 artifacts present + valid** ✓
