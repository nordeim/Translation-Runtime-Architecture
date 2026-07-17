# TRA Round 3 — Comprehensive TDD Remediation Plan

**Created:** 2026-07-15
**Based on:** Round 3 audit (36 findings: 2 BLOCKING / 18 WARNING / 16 INFO)
**Approach:** TDD (Red → Green → Refactor → Commit) per finding
**Codebase:** `/home/z/my-project/Translation-Runtime-Architecture/` at HEAD `243592a`

## Remediation Strategy

Findings are grouped into 5 batches by priority and dependency. Each batch is a milestone (commit + push). Within each batch, fixes are independent and can be applied in sequence.

**Batch 1 — BLOCKING fixes (TRA-093, TRA-096)** — highest priority, blocks L3/L4 production use
**Batch 2 — Security fixes (TRA-076, TRA-077, TRA-078, TRA-079)** — OWASP findings
**Batch 3 — Spec conformance fixes (TRA-038, TRA-042, TRA-072, TRA-073, TRA-074, TRA-075)** — exception reachability, structural verification, Policy Engine
**Batch 4 — Test suite fixes (TRA-088, TRA-089, TRA-090, TRA-091, TRA-092)** — coverage gaps
**Batch 5 — Doc + hygiene fixes (TRA-017, TRA-080, TRA-081, TRA-082, TRA-083, TRA-084, TRA-085, TRA-086, TRA-087, TRA-097, TRA-098, TRA-099, TRA-100)** — staleness, registry hardening
**Deferred** — TRA-001 (per-leaf segment translation, ~16 hours, separate effort)

---

## Batch 1: BLOCKING Fixes (Milestone 2)

### 1.1 TRA-096: as_interface() crashes with Pydantic ValidationError

**Root cause:** `ModuleInterface` dataclass (registry.py:13-22) only has 3 Callable fields (`get_glossary_mappings`, `get_style_profile`, `apply_rules`), but `LanguageModuleProtocol` (base.py:14-56) requires 7 methods. When `as_interface()` returns a `ModuleInterface`, it's missing `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`. Pydantic's `RuntimeContext.module: LanguageModuleProtocol` validation then rejects it.

**Optimal fix:** Add the 4 missing Callable fields to `ModuleInterface` and wire them in `ZHENModule.as_interface()`.

**TDD steps:**
1. RED: Write test `test_as_interface_satisfies_protocol` — asserts `isinstance(ZHENModule().as_interface(), LanguageModuleProtocol)` is True. Fails.
2. RED: Write test `test_registry_register_default_does_not_crash` — calls `build_default_registry()` and constructs `TRAKernel(cfg, registry=registry)`. Fails with ValidationError.
3. GREEN: Add 4 Callable fields to `ModuleInterface` (`is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`). Wire them in `as_interface()`.
4. GREEN: Run tests — pass.
5. REFACTOR: No refactor needed.
6. COMMIT.

**Files touched:**
- `tra/modules/registry.py` — add 4 fields to `ModuleInterface`
- `tra/modules/zh_en.py` — wire 4 fields in `as_interface()`
- `tests/test_outstanding_findings.py` — add `TestTRA096AsInterfaceProtocol` class

### 1.2 TRA-093: False-positive BROKEN_LINK blocks valid CJK translations

**Root cause:** In `kernel.py:376`, `rewrite_links(target, registry)` calls `registry.translated_slug_for(slug)` (anchor.py:90-98). This looks up `slug` in `map_original_slug_to_placeholder`. But after whole-doc translation, the link target may already be a TRANSLATED slug (e.g., `#the-system-is-confirmed`), which is NOT in `map_original_slug_to_placeholder` (only original CJK slugs are). So it returns None → false-positive BROKEN_LINK.

**Optimal fix:** In `rewrite_links`'s `_sub` function, before flagging as broken, check if the slug already matches a translated slug value in `map_placeholder_to_translated_slug`. If it does, the link is already correct — leave it as-is (not broken).

**TDD steps:**
1. RED: Write test `test_cjk_heading_with_cjk_link_not_broken` — input has `# 系统成立` heading + `[link](#系统成立)` link. At L3, should NOT raise ConformanceFailure. Currently fails.
2. RED: Write test `test_translated_slug_link_not_broken` — after translation, link target is `#the-system-is-confirmed` which matches a translated slug. Should NOT be flagged broken.
3. GREEN: In `anchor.py:rewrite_links._sub`, add check: if `slug` is in `registry.map_placeholder_to_translated_slug.values()`, return `m.group(0)` (leave as-is, not broken).
4. GREEN: Run tests — pass.
5. REFACTOR: Extract the check into a helper method `is_translated_slug(slug)` on `AnchorRegistry`.
6. COMMIT.

**Files touched:**
- `tra/anchor.py` — add `is_translated_slug()` method + use in `rewrite_links._sub`
- `tests/test_outstanding_findings.py` — add `TestTRA093BrokenLinkFalsePositive` class

---

## Batch 2: Security Fixes (Milestone 3)

### 2.1 TRA-077: diskcache pickle deserialization (OWASP A08)

**Root cause:** `TranslationCache.set` stores `model_dump()` dict; diskcache uses pickle by default. RCE on cache load.

**Optimal fix:** Store `model_dump_json()` (string) instead. On `get`, `json.loads()` + reconstruct.

**TDD steps:**
1. RED: Write test `test_cache_stores_json_not_pickle` — set a translation, read the raw cache blob, assert it does NOT start with `\x80` (pickle marker) and IS valid JSON.
2. RED: Write test `test_cache_get_returns_correct_result` — set + get round-trip.
3. GREEN: Change `cache.set` to store `result.model_dump_json()`. Change `cache.get` to `json.loads()` + `TranslationResult(**parsed)`.
4. COMMIT.

**Files touched:** `tra/cache.py`, `tests/test_outstanding_findings.py`

### 2.2 TRA-076: LLM seam output bypasses sanitize_input (OWASP A03)

**Root cause:** `isa.py:translate_segment` accepts `llm_translate` response and uses it directly without sanitization.

**Optimal fix:** Route LLM response through `sanitize_input` before use.

**TDD steps:**
1. RED: Write test `test_llm_response_sanitized` — supply `llm_translate` returning a string with bidi overrides / null bytes. Assert they are stripped in the result.
2. GREEN: Import `sanitize_input` in `isa.py`, apply to LLM response.
3. COMMIT.

**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`

### 2.3 TRA-078: exc!r may leak secrets (OWASP A09)

**Optimal fix:** Sanitize `exc!r` in `_recover` before storing in audit trail. Strip patterns matching `sk-`, `Bearer `, `Authorization:`, `api_key`.

**TDD steps:**
1. RED: Write test `test_recover_redacts_secrets` — supply exception with `sk-abc123` in message. Assert audit trail does NOT contain `sk-abc123`.
2. GREEN: Add `_sanitize_exc_repr()` helper in `kernel.py`, use in `_recover`.
3. COMMIT.

**Files touched:** `tra/kernel.py`, `tests/test_outstanding_findings.py`

### 2.4 TRA-079: Cache integrity (INFO, deferred)

**Note:** After TRA-077 (JSON), add HMAC. This is lower priority — defer to a future batch unless time permits.

---

## Batch 3: Spec Conformance Fixes (Milestone 4)

### 3.1 TRA-038: Wire 3 unreachable exception types

**Root cause:** `UnknownTerm`, `CertaintyConflict`, `EntityAmbiguity` are defined and have recovery procedures, but are never raised in production.

**Optimal fix:**
- `UnknownTerm`: In `isa.py:_rule_translate`, when a CJK token has no glossary match and is not an entity, raise `UnknownTerm`.
- `CertaintyConflict`: In `isa.py:verify_output`, when an epistemic marker is strengthened/weakened, raise `CertaintyConflict`.
- `EntityAmbiguity`: In `anchor.py` entity extraction, when a token matches multiple entity patterns, raise `EntityAmbiguity`.

**TDD steps:** One RED-GREEN cycle per exception type (3 cycles).
**Files touched:** `tra/isa.py`, `tra/anchor.py`, `tests/test_outstanding_findings.py`

### 3.2 TRA-042: Extend structural verification

**Root cause:** `verify_output` only checks heading count. No table/list/code-block shape check.

**Optimal fix:** Add checks for: table row count per table, table column count per row, list item count per list, fenced code block count, heading level preservation.

**TDD steps:** One RED-GREEN cycle per check type (5 cycles).
**Files touched:** `tra/isa.py`, `tests/test_outstanding_findings.py`

### 3.3 TRA-072: Route all severity decisions through PolicyResolver

**Root cause:** Only TERMINOLOGICAL vs FLUENCY is routed through `_POLICY_RESOLVER.wins()`. All other severity decisions are hard-coded.

**Optimal fix:** Identify all severity-decision points in `verify_output` and route each through `PolicyResolver.wins()` with the appropriate priority pair.

**TDD steps:**
1. RED: Write test `test_all_severity_decisions_policy_driven` — monkeypatch resolver to return different priorities, assert severity changes.
2. GREEN: Replace hard-coded conditionals with resolver calls.
3. COMMIT.

### 3.4 TRA-073: Remove dead `out = out` loop

**Trivial fix.** Remove lines 488-492 in `isa.py`.
**TDD:** Existing tests pass after removal (dead code has no effect).

### 3.5 TRA-074: _deterministic_clock seed default

**Fix:** Set a default seed in `__init__` (already fallback-coded as `'0'*16`). Document that `run()` overrides it.

### 3.6 TRA-075: Pairwise transition tests

**Fix:** Add parametrized test for all 81 (state, next_state) pairs, asserting TRAException on illegal transitions.

---

## Batch 4: Test Suite Fixes (Milestone 5)

### 4.1 TRA-088: Extend LLM-seam tests to assert single-audit-record
### 4.2 TRA-089: Add ConformanceFailure e2e tests
### 4.3 TRA-090: Add llm_translate parameter to TRAKernel.run()
### 4.4 TRA-091: Add interactive=True end-to-end test
### 4.5 TRA-092: Add S-03 and E-03 benchmark cases

---

## Batch 5: Doc + Hygiene Fixes (Milestone 6)

### 5.1 TRA-017: Remove 6 unused deps from pyproject.toml
### 5.2 TRA-080: Update CLAUDE.md TRA-006 entry (no longer half-fix)
### 5.3 TRA-081: Fix README.md Policy module path (config.py → policy.py)
### 5.4 TRA-082: Fix README.md EntityAmbiguity claim
### 5.5 TRA-083: Fix README.md implementation_plan.md path
### 5.6 TRA-084: Fix AGENTS.md "separate repo" contradiction
### 5.7 TRA-085: Delete or update status.md
### 5.8 TRA-086: Remove "external codebase" from implementation_plan.md + prototype.md
### 5.9 TRA-087: Update implementation_plan.md File Structure Summary
### 5.10 TRA-097: Add isinstance Protocol check in register()
### 5.11 TRA-098: Add duplicate-name + direction-conflict detection in register()
### 5.12 TRA-099: Add --registry CLI flag
### 5.13 TRA-100: Create TRA-MODULE-AUTHORING.md or add section to TRA-MODULE-ZH-EN.md

---

## Validation Plan

After each batch:
1. Run all 4 quality gates: `ruff format --check . && ruff check . && mypy --strict tra && pytest tests -q`
2. All gates must be green.
3. Test count should increase (new regression tests added).
4. Commit + push via SSH wrapper.

After all batches:
1. Re-run Track R3 baseline — confirm all fixes hold.
2. Re-run Track E3 probes — confirm TRA-093 fixed (Probe 5/6 still pass).
3. Re-run Track F3 stub module test — confirm TRA-096 fixed (as_interface() works).
4. Final commit + push.

---

## Effort Estimate

| Batch | Findings | Est. Hours |
|---|---|---|
| 1 (BLOCKING) | 2 | 6 |
| 2 (Security) | 3 | 5 |
| 3 (Spec conformance) | 6 | 12 |
| 4 (Test suite) | 5 | 6 |
| 5 (Doc + hygiene) | 13 | 8 |
| **Total** | **29** | **37 hours (4.6 person-days)** |

TRA-001 (per-leaf segment translation) deferred: ~16 hours, separate effort.
