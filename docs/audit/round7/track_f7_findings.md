# Track F7 — Stub-Module Conformance Re-Audit (Round 7)

**Task ID:** F7-1
**Auditor:** Track F7 (stub-module conformance)
**HEAD audited:** `6d3144a` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Baseline:** Round 6 Track F6 (`docs/audit/round6/track_f6_findings.md`, 8 findings: 0 BLOCKING / 0 WARNING / 8 INFO)
**Methodology:** Verify the module registry contract, the LanguageModuleProtocol, and the end-to-end flow from CLI → kernel → registry → module selection. Test with a stub module to ensure third-party modules can be registered and selected correctly.

## Verification Run

- HEAD: `git rev-parse HEAD` → `6d3144a3fdaa8d90a8f5b5f3996af39e667ee496` ✓
- `pytest tests/test_modules.py tests/test_tra043_protocol.py` → all pass ✓

## Summary

- **Findings: 8 total (0 BLOCKING / 0 WARNING / 8 INFO + 4 positive verifications)**
- **0 regressions** from R6 baseline
- **All R6 F6 findings verified holding**

---

## Findings

### TRA-F7-001: TRA-096 — `as_interface()` + `register()` + `TRAKernel(registry=)` works end-to-end (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Module Registry
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-001 re-confirmed)
- **Evidence:**
  - `tra/modules/registry.py` `ModuleRegistry.register()` accepts a `ModuleInterface` and validates its 7 `Callable` fields.
  - `tra/modules/base.py` `LanguageModuleProtocol` defines the Protocol.
  - `tra/modules/zh_en.py` `ZHENModule.as_interface()` returns a `ModuleInterface` that satisfies the Protocol.
  - `tra/kernel.py` `TRAKernel(cfg, registry=registry)` selects the module from the registry based on `config.language_pair`.
  - End-to-end test: `tests/test_modules.py::test_registry_end_to_end` passes.

### TRA-F7-002: TRA-099 — CLI `translate` auto-builds the default registry and passes `registry=registry` to `TRAKernel` (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / CLI Integration
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-002 re-confirmed)
- **Evidence:**
  - `tra_cli.py` `translate` command calls `build_default_registry()` and passes the result to `TRAKernel(cfg, registry=registry)`.
  - CLI test: `tests/test_outstanding_findings.py::TestTRA_D5_017_CLIRunnerTests` passes.

### TRA-F7-003: TRA-F5-010 — `_normalize_language_pair` rejects malformed `--lang` values (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Input Validation
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-003 re-confirmed)
- **Evidence:**
  - `tra_cli.py` `_normalize_language_pair` rejects malformed `--lang` values (e.g., `zh_en`, `ZH-EN`, `zh->en` → all normalized to `zh-en`; invalid formats raise `click.BadParameter`).
  - Test: `tests/test_outstanding_findings.py::TestTRA_F5_010_NormalizeLanguagePair` passes.

### TRA-F7-004: TRA-F5-011 — `register()` rejects language modules with no `metadata.direction` (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Registration Validation
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-004 re-confirmed)
- **Evidence:**
  - `tra/modules/registry.py` `register()` raises `ValueError` if the module's `metadata.direction` is `None` or empty.
  - Test: `tests/test_outstanding_findings.py::TestTRA_F5_011_RegisterRejectsNoDirection` passes.

### TRA-F7-005: `ModuleInterface` contract — 7 `Callable` fields exactly match `LanguageModuleProtocol`'s 7 method signatures (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Protocol Compliance
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-005 re-confirmed)
- **Evidence:**
  - `tra/modules/registry.py` `ModuleInterface` is a `dataclass` with 7 `Callable` fields: `metadata`, `get_glossary_mappings`, `get_style_profile`, `apply_rules`, `entity_type_hint`, `analyze_special_terms`, `translate_special_constructs`.
  - `tra/modules/base.py` `LanguageModuleProtocol` defines the same 7 methods with matching signatures.
  - `tests/test_tra043_protocol.py` verifies the Protocol satisfaction.

### TRA-F7-006: `build_default_registry()` returns a registry containing the ZH-EN module registered via `as_interface()` (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Default Registry
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-006 re-confirmed)
- **Evidence:**
  - `tra/modules/registry.py` `build_default_registry()` creates a `ModuleRegistry`, instantiates `ZHENModule`, calls `as_interface()`, and registers it.
  - The registry contains exactly 1 module (ZH-EN) at HEAD `6d3144a`.

### TRA-F7-007: Edge cases — empty registry, duplicate modules, same-direction modules, unregister + re-register all behave correctly (POSITIVE VERIFICATION)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Edge Cases
- **Finding type:** positive_verification
- **Round 6 status:** verified-holding (TRA-F6-007 re-confirmed)
- **Evidence:**
  - `tests/test_modules.py` covers: empty registry (kernel falls back to ZHENModule singleton), duplicate registration (raises), same-direction modules (last one wins), unregister + re-register (works).
  - All edge case tests pass at HEAD `6d3144a`.

### TRA-F7-008: `TRA-MODULE-AUTHORING.md` §2.7 section header uses parameter name `source` while actual Protocol uses `text` (PERSISTENT INFO, carry-over from F6-009)

- **Severity:** INFO
- **Category:** Stub-Module Conformance / Authoring Guide Drift
- **Finding type:** issue
- **Round 6 status:** persistent (carry-over from F6-009)
- **Evidence:**
  - `TRA-MODULE-AUTHORING.md` §2.7 — section header references parameter name `source`.
  - `tra/modules/base.py` `LanguageModuleProtocol` — actual parameter name is `text`.
  - `TRA-MODULE-AUTHORING.md` §1 — snippet uses `text` (correct).
- **Detail:** Same as TRA-C7-005. Cosmetic drift between §1 and §2.7 of the same document.
- **Suggested fix:** Rename §2.7 section header parameter from `source` to `text`.

---

## Conclusion

- **0 BLOCKING** findings at HEAD `6d3144a` ✓
- **0 WARNING** findings ✓
- **1 INFO** finding persistent (TRA-F7-008) — addressed in `remediation_plan_r7.md`
- **7 positive verifications** re-confirmed
- **0 regressions** from R6 baseline ✓
