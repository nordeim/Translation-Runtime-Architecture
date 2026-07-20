# TRA Round 7 — Comprehensive TDD Remediation Plan

**Created:** 2026-07-21
**Based on:** Round 7 audit (75 findings: 39 issues + 36 positive verifications; 4 BLOCKING / 18 WARNING / 53 INFO)
**Approach:** TDD (Red → Green → Refactor → Commit) per finding
**Codebase:** `/home/z/my-project/Translation-Runtime-Architecture/` at HEAD `6d3144a`

## Remediation Strategy

The R7 audit identified **9 outstanding WARNING findings** (the 4 BLOCKING + 6 WARNING from R6 are already fixed in commit `6d3144a`). The remediation is structured into 3 batches:

- **Batch 1 — WARNING Security Fix (TRA-B7-002 Authorization header regex)** — 1 finding, ~1h
- **Batch 2 — WARNING Tooling + Code Quality (TRA-B7-001 mutmut config, TRA-A7-001 cache-hit audit side-effects, TRA-A7-002 segment_index plumbing, TRA-D7-001 hardcoded paths, TRA-D7-002 vacuous entity-ambiguity test, TRA-A7-004 EntityAmbiguity raise)** — 6 findings, ~5h
- **Batch 3 — WARNING Doc-Drift + INFO Cleanup (TRA-C7-001/002/003 doc fixes + opportunistic INFO)** — 2 WARNING + ~10 INFO findings, ~2h

Total estimated effort: **~8 hours**

---

## Batch 1: WARNING Security Fix (1 finding, ~1h)

### 1.1 TRA-B7-002: `Authorization: Bearer <token>` regex leaks the token into audit trail (OWASP A09)

**Root cause:** `tra/kernel.py:110-114` `_SECRET_RE` regex has three alternatives. The `Authorization:\s*[^\s,;]+` alternative matches `Authorization: Bearer` (up to first whitespace) but NOT the token that follows. Because regex alternation tries left-to-right, this alternative wins over the more-correct `Bearer\s+[A-Za-z0-9._-]+` alternative.

**Reproduction (verified):**
```python
_sanitize_exc_repr(FakeException('Authorization: Bearer eyJhbGc.secrettoken123'))
# Output: FakeException('HTTP 401: [REDACTED] eyJhbGc.secrettoken123')
# JWT token LEAKED into audit trail
```

**TDD plan:**
1. **RED:** Add `test_authorization_bearer_token_redacted` in `tests/test_outstanding_findings.py::TestTRA078SecretsRedaction`. Assert that `_sanitize_exc_repr` of an exception containing `Authorization: Bearer <token>` produces output where `<token>` does NOT appear. Test fails at HEAD `6d3144a`.
2. **GREEN:** Fix the regex to consume the scheme AND the credential:
   ```python
   _SECRET_RE = re.compile(
       r"(sk-[A-Za-z0-9]{8,}"
       r"|Bearer\s+[A-Za-z0-9._-]+"
       r"|Authorization:\s*\S+(?:\s+\S+)?"  # consumes scheme + credential
       r"|api[_-]?key['\"]?\s*[:=]\s*['\"]?[^\s'\"]+)",
       re.IGNORECASE,
   )
   ```
   Test passes.
3. **REFACTOR:** Add a second test for `Authorization: Basic <base64>` to verify the fix generalizes beyond Bearer.
4. **COMMIT:** `fix(tra): TRA-B7-002 — Authorization header regex redacts full credential (OWASP A09)`

---

## Batch 2: WARNING Tooling + Code Quality (6 findings, ~5h)

### 2.1 TRA-B7-001: mutmut 3.6+ deprecated config keys (TRA-D5-011 residual)

**Root cause:** `tra-prototype/pyproject.toml:62-64` uses `paths_to_mutate` and `tests_dir` which are deprecated in mutmut 3.6+. R6 Batch 1 fixed the string→list crash but did NOT rename the keys.

**TDD plan:**
1. **RED:** Add `test_mutmut_config_no_deprecation_warnings` in `tests/test_outstanding_findings.py::TestTRA_D5_011_MutationTestingConfig`. Run `mutmut run --help` via `subprocess.run` and assert stderr does NOT contain `DeprecationWarning`. Test fails at HEAD `6d3144a`.
2. **GREEN:** In `pyproject.toml`:
   ```toml
   [tool.mutmut]
   source_paths = ["tra"]    # renamed from paths_to_mutate
   max_stack_depth = 5
   # tests_dir removed — mutmut 3.6+ auto-detects pytest
   ```
   Test passes.
3. **REFACTOR:** Update `test_mutmut_config_section_present` to assert the new key names.
4. **COMMIT:** `fix(tra): TRA-B7-001 — rename mutmut config keys (paths_to_mutate → source_paths)`

### 2.2 TRA-A7-001: Cache-hit suppresses EXCEPTION_HANDLER records for UnknownTerm

**Root cause:** `tra/isa.py:461-465` cache-hit early-return bypasses EXCEPTION_HANDLER emission. `TranslationResult` model (`tra/cache.py:104-111`) does not store `audit_side_effects` or unknown-token metadata.

**TDD plan:**
1. **RED:** Add `test_cache_hit_preserves_exception_handler_records` in `tests/test_outstanding_findings.py::TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover`. Translate a source with an unknown CJK token twice using a shared cache. Assert both runs produce identical EXCEPTION_HANDLER record counts. Test fails at HEAD `6d3144a` (Run 2 has 0 EXCEPTION_HANDLER records).
2. **GREEN:** 
   - Add `audit_side_effects: list[dict] = []` field to `TranslationResult` in `tra/cache.py`.
   - In `translate_segment` (cache-miss path), collect EXCEPTION_HANDLER records into `audit_side_effects` before storing in cache.
   - In `translate_segment` (cache-hit path), re-emit the stored `audit_side_effects` via `audit.append(...)`.
   Test passes.
3. **REFACTOR:** Verify TRA-013 byte-reproducibility still holds (cold-cache × 2 L4 runs produce byte-identical audit_trace.jsonl).
4. **COMMIT:** `fix(tra): TRA-A7-001 — cache-hit re-emits EXCEPTION_HANDLER audit records (L4 forensic completeness)`

### 2.3 TRA-A7-002: Kernel's _repair_loop doesn't pass segment_index to repair_segment

**Root cause:** `tra/kernel.py:682-691` calls `repair_segment(...)` without `segment_index`. The leaf index is not naturally available at the repair call site (repair works on whole-doc diagnostics).

**TDD plan:**
1. **RED:** Add `test_repair_segment_index_propagated` in `tests/test_outstanding_findings.py::TestTRA_001_LeafSegmentTranslation`. Run a source with multiple list items that trigger distinct repairs. Assert `RepairAttempt.segment_index` varies (not always 0). Test fails at HEAD `6d3144a`.
2. **GREEN:**
   - Add `segment_index: int | None = None` field to `Diagnostic` in `tra/memory.py`.
   - In `verify_output`, when emitting a diagnostic, match the diagnostic's evidence against `ctx.structural_map.iter_leaf_segments()` leaf texts and set `segment_index` to the matched leaf's index.
   - In `_repair_loop`, pass `segment_index=current.segment_index or 0` to `repair_segment`.
   Test passes.
3. **REFACTOR:** Verify L4 forensic trace now correlates repairs to specific leaves.
4. **COMMIT:** `fix(tra): TRA-A7-002 — plumb segment_index from verify_output through _repair_loop (L4 traceability)`

### 2.4 TRA-A7-004: EntityAmbiguity still bypasses EXCEPTION_HANDLER audit-record path

**Root cause:** `tra/isa.py:388` calls `recover_entity_ambiguity(...)` directly instead of raising `EntityAmbiguity`. The kernel's `_recover` never fires for this exception type, so no EXCEPTION_HANDLER audit record is emitted.

**TDD plan:**
1. **RED:** Strengthen the existing vacuous test `test_entity_ambiguity_emits_exception_handler_audit_record` (TRA-D7-002). Assert: (a) an EXCEPTION_HANDLER record with `exception_code='ENTITY_AMBIGUITY'` exists, (b) `artifact_snapshot.severity == 'WARNING'`, (c) `artifact_snapshot.action == 'PRESERVE_SOURCE'`. Test fails at HEAD `6d3144a`.
2. **GREEN:**
   - In `build_entity_table` (`tra/isa.py:388`), replace `recover_entity_ambiguity(ent.name, ctx.unresolved_ambiguities)` with `raise EntityAmbiguity(ent.name)`.
   - Verify the kernel's `_recover` correctly routes it via `route_exception` → `recover_entity_ambiguity` and emits an EXCEPTION_HANDLER audit record.
   Test passes.
3. **REFACTOR:** Verify no regressions in existing EntityAmbiguity tests.
4. **COMMIT:** `fix(tra): TRA-A7-004 — raise EntityAmbiguity (not direct-call) so EXCEPTION_HANDLER audit record emits`

### 2.5 TRA-D7-001: 15 hardcoded absolute paths in test_outstanding_findings.py

**Root cause:** 15 sites in `tests/test_outstanding_findings.py` use literal `/home/z/my-project/Translation-Runtime-Architecture/...` paths. These break portability across containers/checkouts.

**TDD plan:**
1. **RED:** Add `test_no_hardcoded_paths_in_test_files` as a meta-test. Scan `tests/test_outstanding_findings.py` for the literal string `/home/z/my-project/` and assert 0 hits. Test fails at HEAD `6d3144a` (15 hits).
2. **GREEN:** Replace all 15 hardcoded paths with `Path(__file__).resolve().parent.parent` (the repo root) or a session-scoped fixture:
   ```python
   @pytest.fixture(scope="session")
   def repo_root() -> Path:
       return Path(__file__).resolve().parent.parent
   ```
   Test passes.
3. **REFACTOR:** Verify all 309 tests still pass.
4. **COMMIT:** `fix(tra): TRA-D7-001 — replace hardcoded paths with Path(__file__) (test portability)`

### 2.6 TRA-D7-002: Vacuous test `test_entity_ambiguity_emits_exception_handler_audit_record`

**Root cause:** Test body says "We don't strictly require ENTITY_AMBIGUITY on this particular input" and only asserts the absence of a `direct_call` marker. The test passes vacuously.

**TDD plan:**
1. **RED:** This is the same fix as 2.4 (TRA-A7-004). Once the production code raises EntityAmbiguity, strengthen the test to assert the EXCEPTION_HANDLER record's presence and content. Test fails at HEAD `6d3144a` (production gap), then passes after fix 2.4.
2. **GREEN:** Same as 2.4.
3. **REFACTOR:** Same as 2.4.
4. **COMMIT:** Same as 2.4 (combined commit).

---

## Batch 3: WARNING Doc-Drift + INFO Cleanup (2 WARNING + ~10 INFO, ~2h)

### 3.1 TRA-C7-001: implementation_plan.md dependencies table pinned to stale HEAD `805a8f8`

**Fix:** Replace `Updated at HEAD `805a8f8` (Round 4 audit)` with `Updated at HEAD `6d3144a` (Round 7 audit)`. The deps table content is unchanged.

### 3.2 TRA-C7-002: README.md missing Round 5/6/7 audit references

**Fix:** Add a new "Audit History" section to `README.md` listing all 7 rounds with one-line summaries and links to each round's README:
```markdown
## Audit History

The TRA prototype has undergone 7 independent re-audits. Each round's deliverables (DOCX report, XLSX register, severity heatmap, master JSON register) live in `docs/audit/roundN/`.

| Round | HEAD | Findings | Status |
|---|---|---|---|
| R1 | (early) | 35 | 34/35 fixed |
| R2 | `4b8827c` | 41 | All fixed |
| R3 | `b783745` | 36 | 20/36 fixed in R3 batches |
| R4 | `805a8f8` | 47+19 | All 4 critical invariants hold |
| R5 | `5476faf` | 68 | All 46 issues fixed in 5 batches |
| R6 | `c4ecd41` | 76 | 4 BLOCKING + 6 WARNING fixed in R6 Batch 1 |
| R7 | `6d3144a` | 75 | This audit — see `docs/audit/round7/` |
```

### 3.3 TRA-C7-003: status.md banner does not pin the latest HEAD hash

**Fix:** Update `status.md` banner to:
```
> **⚠️ STALE — historical session log.** This file is frozen at commit `4d97aa1` and references "103 pytest passing". The actual state at HEAD `6d3144a` (Round 7 audit, 2026-07-21) is **309 tests across 16 test files** + L3 CONFORMANT. See `CLAUDE.md` → "Prototype engine status" for current state and `docs/audit/round7/` for the latest audit.
```

### 3.4 INFO Cleanup (opportunistic, ~10 findings)

- **TRA-C7-004** — Remove phantom `B4-009` from SKILL.md §7 test-class list; add `001 (×2)` annotation.
- **TRA-C7-005 / TRA-F7-008** — Rename `TRA-MODULE-AUTHORING.md` §2.7 section header parameter from `source` to `text`.
- **TRA-A7-003** — Skip PARAGRAPH whose parent is a LIST_ITEM in `iter_leaf_segments()` (deduplicate list-item leaves).
- **TRA-A7-005** — Wrap `_execute_translation` and `verify_output` in `try/except TRAException` matching the analyze/build pattern.
- **TRA-B7-003** — Remove the `else` branch in `cache.get` that accepts pickle/dict entries; treat non-string cache values as cache misses.
- **TRA-B7-004** — Replace `self._cache: Any = None` with `diskcache.Cache | None` via `TYPE_CHECKING` import.
- **TRA-D7-003** — Add test for per-leaf translation + LLM interaction (LLM raises mid-translation).
- **TRA-D7-004/005/006** — Fix remaining test isolation gaps (override `cache_directory` with `tempfile.mkdtemp()` in all `BootstrapConfig.from_yaml` test sites).
- **TRA-D7-007** — Strengthen `TestTRA033LLMSeamRobustness` assertion (exact record count + degraded flag).
- **TRA-D7-008** — Replace hardcoded `/tmp/test_tra071*.jsonl` with `tempfile.NamedTemporaryFile`.
- **TRA-D7-014** — Strengthen mutation testing config test (run `mutmut run --help`, assert zero `DeprecationWarning`).
- **TRA-E7-009** — Document the double-VERIFY_OUTPUT behavior in SKILL.md §4 and `docs/api-reference.md`.

**COMMIT:** `docs(tra): R7 Batch 3 — doc-drift fixes + INFO cleanup (TRA-C7-001/002/003/004/005, TRA-A7-003/005, TRA-B7-003/004, TRA-D7-003/004/005/006/007/008/014, TRA-E7-009)`

---

## Effort Estimate

| Batch | Findings | Est. Hours |
|---|---|---|
| 1 (Security fix) | 1 | 1.0 |
| 2 (Tooling + Code Quality) | 6 | 5.0 |
| 3 (Doc-drift + INFO cleanup) | 2 WARNING + ~10 INFO | 2.0 |
| **Total** | **9 WARNING + ~10 INFO** | **8.0 hours** |

Plus 36 positive verifications (no action needed).

---

## Success Criteria

- [ ] All 9 WARNING findings fixed via TDD (Red → Green → Refactor → Commit per finding)
- [ ] 0 regressions: all 309 existing tests still pass after each batch
- [ ] TRA-013 byte-reproducibility still holds (cold-cache × 2 L4 runs produce byte-identical audit_trace.jsonl)
- [ ] All 4 quality gates green after each batch: `ruff format --check`, `ruff check`, `mypy --strict`, `pytest`
- [ ] Documentation updated to reflect the remediated state (CLAUDE.md, README.md, SKILL.md, implementation_plan.md)
- [ ] Each batch committed separately with a descriptive message
- [ ] Final commit pushes to `origin/main` via SSH wrapper

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| TRA-A7-001 fix breaks TRA-013 byte-reproducibility (cache stores more data → different cache key) | Medium | High | Cache key does NOT include `audit_side_effects` (only `translation` + `evidence_ids`); verify with cold-cache × 2 L4 runs after fix |
| TRA-A7-002 fix introduces segment_index mismatches (diagnostic evidence doesn't match any leaf text) | Low | Medium | Default `segment_index` to 0 when no match found; add a test for the no-match case |
| TRA-A7-004 fix changes EntityAmbiguity behavior (now raises instead of direct-calls) | Medium | Medium | Verify all existing EntityAmbiguity tests still pass; the recovery procedure is unchanged, only the dispatch path differs |
| TRA-D7-001 path replacement breaks tests that depend on the literal path appearing in audit records | Medium | Low | Audit the 15 sites individually; some may need to assert the path pattern rather than the literal path |
| `mutmut run` still crashes after config rename (mutmut 3.6+ may have other issues) | Low | Low | Test with `mutmut run --help` first; full `mutmut run` is out of scope for this remediation |
