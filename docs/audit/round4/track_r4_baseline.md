# Track R4 — Regression Baseline (Round 4)

**HEAD audited:** `805a8f8`
**Methodology:** Re-verification of all 36 Round 3 findings via regression test or static check.
**Baseline:** Round 3 master register (36 findings: 2 BLOCKING / 18 WARNING / 16 INFO).
**Carry-over:** 8 findings already validated by Task `0-setup` (TRA-001, 002/096, 017, 038, 073, 077, 093, 099) — results incorporated directly.

## Summary

- **FIXED:** 20
- **PERSISTENT:** 12
- **PARTIAL:** 4
- **REGRESSED:** 0

Net change vs Round 3 baseline (which had 12 FAIL/PERSISTENT): 14 findings transitioned from PERSISTENT → FIXED/PARTIAL across the 6 remediation commits (`df9a590` → `805a8f8`).

## 36-finding regression table

| ID | R3 Severity | Title | R4 Status | Verification |
|---|---|---|---|---|
| TRA-001 | WARNING | TRANSLATE_SEGMENT operates on whole document, not per-leaf segment (partial fix, persistent) | PARTIAL | test `TestTRA001SegmentLevel` PASS (1/1); test verifies only code-block no-translate zone protection — per-leaf segment refactor still deferred |
| TRA-016 | INFO | AuditTrail.count_blocking stub — REMEDIATED since Round 2 (Track R3 baseline false positive) | FIXED | static: `grep -n "count_blocking" tra/diagnostics.py` → no match (method removed) |
| TRA-017 | WARNING | 6 unused dependencies still listed in pyproject.toml (persistent) | FIXED | static: `python -c "import tomllib; ..."` → 6 runtime deps (pydantic, markdown-it-py, diskcache, pyyaml, click, rich) — unused deps trimmed in `a3cd2c1` |
| TRA-026 | INFO | cache.expire field — REMEDIATED since Round 2 (Track R3 baseline false positive) | FIXED | static: `grep -n "expire" config.yaml tra/config.py` → no match (field removed) |
| TRA-038 | WARNING | 3 of 5 TRA-EXCEPTION types never raised in production (persistent) | PARTIAL | test `TestTRA038UnknownTermRaised` PASS (2/2); test docstring explicitly notes "full production wiring (auto-detecting unknown CJK terms) is deferred" — UnknownTerm/CertaintyConflict/EntityAmbiguity routable but not auto-raised |
| TRA-040 | INFO | EXCEPTION_HANDLER/HALT_ERROR are recovery actions, not KernelStates (intentional, persistent) | PERSISTENT | static: `grep -n "EXCEPTION_HANDLER\|HALT_ERROR" tra/kernel.py` → EXCEPTION_HANDLER appears only as audit-record string (lines 229,237,274,402,419), NOT in `KernelState` enum (lines 49-60: 9 canonical states) — intentional per spec |
| TRA-042 | WARNING | Structural verification is heading-count-only (persistent) | PERSISTENT | static: `sed -n '524,535p' tra/isa.py` → verify_output compares only `src_headings != tgt_headings`; no table/list/code-block shape check |
| TRA-072 | WARNING | PolicyResolver consulted for only ONE conflict pair (TERMINOLOGICAL vs FLUENCY) | PERSISTENT | static: `grep -n "_POLICY_RESOLVER.wins\|_POLICY_RESOLVER.resolve" tra/ -r` → only one call site at tra/isa.py:565 (TERMINOLOGICAL_CONSISTENCY, TARGET_FLUENCY) |
| TRA-073 | INFO | Dead 'out = out' no-op loop in isa.py _rule_translate | FIXED | test `TestTRA073DeadCodeRemoved` PASS (1/1); test reads isa.py source and asserts no `out = out` code statement (only comments remain) |
| TRA-074 | INFO | _deterministic_clock seed set in run() not __init__ (latent misuse risk) | FIXED | test `TestTRA074ClockSeedDefault` PASS (1/1); asserts `_deterministic_clock()` returns datetime with year ≥ 2024 before run() is called |
| TRA-075 | INFO | Pairwise kernel transition test coverage thin (1 of 81 pairs tested) | FIXED | test `TestTRA075PairwiseTransitions` PASS (3/3); tests all backward pairs (i,j with j<i) raise TRAException |
| TRA-076 | WARNING | LLM seam output bypasses sanitize_input chokepoint | FIXED | test `TestTRA076LLMOutputSanitized` PASS (1/1); asserts bidi overrides, null bytes, BOM stripped from LLM response |
| TRA-077 | WARNING | diskcache serializes TranslationResult via pickle (RCE on cache load) | FIXED | test `TestTRA077CacheJsonNotPickle` PASS (2/2); asserts raw cache blob starts with `{` (JSON) not `\x80` (pickle); cache.py:115 uses `model_dump_json()` + `json.loads()` |
| TRA-078 | INFO | exc!r in audit trail could leak LLM client secrets | FIXED | test `TestTRA078SecretRedaction` PASS (1/1); asserts "sk-abc123secret456" and "Bearer xyz789" do NOT appear in audit trail; "[REDACTED" marker present |
| TRA-079 | INFO | TranslationResult cache values have no integrity protection (no MAC/signature) | PERSISTENT | static: `grep -n "hmac\|signature\|verify_integrity" tra/cache.py` → no match; cache.py only enforces JSON-not-pickle (TRA-077), no tamper detection |
| TRA-080 | WARNING | CLAUDE.md TRA-006 'half-fix' entry is now stale (a4d0b3a fully fixed it) | FIXED | static: `grep -n "TRA-006\|PolicyResolver" CLAUDE.md` → line 50 now reads "Policy Engine (TRA-006, fixed in Round 3; TRA-072 partial)" — accurate |
| TRA-081 | WARNING | tra-prototype/README.md Architecture table misattributes Policy module to tra/config.py | FIXED | static: `grep -n "Policy" tra-prototype/README.md` → line 49 Architecture table shows `tra/policy.py` (correct) |
| TRA-082 | WARNING | tra-prototype/README.md TRA-004 entry misleadingly says EntityAmbiguity routes through _recover | PARTIAL | static: `grep -n "TRA-004\|EntityAmbiguity" tra-prototype/README.md` → lines 96-99 still say "EntityAmbiguity now route through _recover" BUT add qualifying clause "however, UnknownTerm/CertaintyConflict/EntityAmbiguity are still never raised in production code paths (TRA-038)" — misleading phrase retained, mitigation added |
| TRA-083 | INFO | README.md path error: 'tra-prototype/implementation_plan.md' (actual: repo root) | FIXED | static: `grep -n "tra-prototype/implementation_plan" README.md tra-prototype/README.md` → no match (path corrected) |
| TRA-084 | INFO | AGENTS.md internal contradiction — 'separate repo' vs 'overridden to subdirectory' | FIXED | static: `grep -n "different repo\|subdirectory" AGENTS.md` → lines 5 and 25 now both acknowledge the override ("overriding the original 'separate repository' boundary rule" + "OTHER THAN the bundled tra-prototype/ subdirectory") — reconciled |
| TRA-085 | WARNING | status.md frozen session log says '103 tests' (actual: 174) | PARTIAL | static: `head -1 status.md` → line 1 has STALE banner ("⚠️ STALE — historical session log... actual test count at HEAD is 174+"); `sed -n '46p' status.md` → line 46 body still says "103 pytest passing" — banner mitigates but inaccurate count remains in body |
| TRA-086 | INFO | implementation_plan.md still calls tra-prototype/ 'external codebase' (persistent) | FIXED | static: `grep -n "external codebase" implementation_plan.md` → no match (phrase removed) |
| TRA-087 | INFO | implementation_plan.md File Structure Summary missing 6 modules + 4 test files | PERSISTENT | static: `sed -n '305,351p' implementation_plan.md` → File Structure Summary lists 11 modules but actual tra/ has 17 (missing: benchmark.py, hitl.py, validate.py, config.py, recovery.py, reporting.py — 6 modules); lists 12 test files but tests/ has 17 (missing: test_e2e_to_translate.py, test_tra043_protocol.py, test_tra047_config_robustness.py, test_tra071_broken_markdown.py, run_e2e_translation.py — 5 files) |
| TRA-088 | WARNING | TRA-048 single-audit-record invariant only tested for RuntimeError path | FIXED | test `TestTRA088SingleAuditRecordAllExceptions` PASS (2/2); tests empty-response (ValueError) and TypeError paths — both produce exactly 1 TRANSLATE_SEGMENT audit record |
| TRA-089 | WARNING | No e2e test exercises the ConformanceFailure path | FIXED | test `TestTRA089ConformanceFailureE2E` PASS (2/2); tests unclosed-fence (BROKEN_MARKDOWN) and broken-link (BROKEN_LINK) ConformanceFailure paths |
| TRA-090 | WARNING | LLM hijack in e2e tests uses fragile module-level patching | PERSISTENT | static: `grep -n "kernel_mod.translate_segment" tests/` → both tests/test_e2e_to_translate.py:98 and tests/run_e2e_translation.py:78 still assign `kernel_mod.translate_segment = patched_translate` (module attribute mutation, not monkeypatch context manager) |
| TRA-091 | WARNING | interactive=True kernel path still untested end-to-end (TRA-052 persistent) | PERSISTENT | static: `grep -rn "interactive=True" tests/ tra/` → no match; no test runs `TRAKernel(interactive=True).run()` end-to-end |
| TRA-092 | INFO | Benchmark coverage at 22/100+ spec target (S-03 and E-03 still missing) | PERSISTENT | static: `cat tests/benchmark/cases/*.jsonl \| wc -l` → 22 cases (unchanged from R3); spec target 100+ |
| TRA-093 | BLOCKING | False-positive BROKEN_LINK blocks valid CJK heading + CJK link translations at L3/L4 | FIXED | test `TestTRA093BrokenLinkFalsePositive` PASS (2/2); `is_translated_slug()` method added to anchor.py |
| TRA-094 | INFO | evidence_trace.jsonl still produces orphan lines (TRA-001 consequence) | PERSISTENT | static: `sed -n '86p' tra/reporting.py` → line_by_line_trace still uses substring heuristic `r.target_span and r.target_span in line` — orphan lines (empty evidence_ids) persist as long as TRA-001 is partial |
| TRA-095 | INFO | HITL path unreachable through CLI (TRA-E-009 persistent) | PERSISTENT | static: `grep -n "interactive\|Unrecoverable" tra_cli.py` → CLI has `--interactive` flag (line 72) but no flag to FORCE Unrecoverable for testing; `grep -rn "raise Unrecoverable" tra/` → raised only at isa.py:666 (structural repair max retries) and isa.py:678 (new BLOCKING in repair) — both require pathological input to trigger via normal CLI flow |
| TRA-096 | BLOCKING | as_interface() crashes with Pydantic ValidationError (spec's sanctioned extension path is broken) | FIXED | test `TestTRA096AsInterfaceProtocol` PASS (3/3); ModuleInterface has all 7 fields (Callable + 4 protocol methods); default registry kernel works end-to-end; stub FR→EN module via registry works |
| TRA-097 | WARNING | ModuleRegistry.register() does NOT call isinstance(mod, LanguageModuleProtocol) | FIXED | test `TestTRA097RegisterProtocolCheck` PASS (2/2); broken module missing methods raises TypeError mentioning "LanguageModuleProtocol"; valid module accepted |
| TRA-098 | WARNING | Duplicate module.name silently overwrites; conflicting directions not detected | FIXED | test `TestTRA098RegistryDuplicateDetection` PASS (3/3); duplicate name raises ValueError; direction conflict detected |
| TRA-099 | WARNING | tra_cli.py translate does NOT pass registry= to TRAKernel (TRA-002 follow-up) | PERSISTENT | static: `grep -n "TRAKernel\|registry=" tra_cli.py` → line 107 `kernel = TRAKernel(cfg, interactive=interactive)` — no registry= kwarg; CLI still falls back to ZHENModule |
| TRA-100 | INFO | TRA-MODULE-ZH-EN.md is a linguistic spec, not a module-authoring template | PERSISTENT | static: `grep -n "LanguageModuleProtocol\|as_interface\|metadata.direction\|kind" TRA-MODULE-ZH-EN.md` → no match; 54-line file is purely linguistic rules (parataxis→hypotaxis, epistemic mapping, etc.), no module-authoring guidance |

## Notable status changes vs Round 3

- **TRA-001**: Round 3 = partial/persistent → Round 4 = **PARTIAL** (test verifies code-block protection; full per-leaf segment refactor still deferred — commit messages do not claim otherwise).
- **TRA-017**: Round 3 = PERSISTENT → Round 4 = **FIXED** (deps trimmed from 12 to 6 in commit `a3cd2c1`).
- **TRA-038**: Round 3 = PERSISTENT → Round 4 = **PARTIAL** (UnknownTerm/CertaintyConflict/EntityAmbiguity now routable; commit `632bed2` honestly defers auto-detection in build_glossary).
- **TRA-073**: Round 3 = PERSISTENT → Round 4 = **FIXED** (dead `out = out` loop removed in commit `632bed2`).
- **TRA-076/077/078**: Round 3 = PERSISTENT → Round 4 = **FIXED** (security remediation in commit `32c31ca`).
- **TRA-080**: Round 3 = PERSISTENT → Round 4 = **FIXED** (CLAUDE.md TRA-006 entry updated to "fixed in Round 3; TRA-072 partial" in commit `a3cd2c1`).
- **TRA-081**: Round 3 = PERSISTENT → Round 4 = **FIXED** (Architecture table now correctly shows `tra/policy.py`).
- **TRA-082**: Round 3 = PERSISTENT → Round 4 = **PARTIAL** (misleading phrase "EntityAmbiguity now routes through _recover" retained, but qualifying clause "still never raised in production" added — partially mitigated).
- **TRA-083**: Round 3 = PERSISTENT → Round 4 = **FIXED** (path error corrected; no `tra-prototype/implementation_plan.md` reference remains).
- **TRA-084**: Round 3 = PERSISTENT → Round 4 = **FIXED** (AGENTS.md contradiction reconciled — both lines now acknowledge the subdirectory override).
- **TRA-085**: Round 3 = PERSISTENT → Round 4 = **PARTIAL** (STALE banner added at line 1, but body still says "103 pytest passing" at line 46).
- **TRA-086**: Round 3 = PERSISTENT → Round 4 = **FIXED** ("external codebase" phrase removed from implementation_plan.md in commit `a3cd2c1`).
- **TRA-088/089**: Round 3 = PERSISTENT → Round 4 = **FIXED** (e2e test gaps closed in commit `805a8f8`).
- **TRA-093/096/097/098**: Round 3 = PERSISTENT → Round 4 = **FIXED** (BLOCKING + registry hardening in commits `3c38f78` and `a3cd2c1`).
- **TRA-099**: Round 3 = PERSISTENT → Round 4 = **PERSISTENT** (CLI still does not pass registry= — no commit claims to fix this).

### Surprising / noteworthy observations

1. **TRA-082 is only PARTIAL, not FIXED**: commit `a3cd2c1` added the qualifying clause but did not rewrite the misleading phrase "EntityAmbiguity now routes through _recover" — the wording still implies the routing is functional when in fact the exception is never raised in production (TRA-038 deferred).
2. **TRA-085 is only PARTIAL, not FIXED**: status.md has a STALE banner at the top but the body still contains the inaccurate "103 pytest passing" claim (and the actual count at HEAD is now 199, not the 174 the banner claims).
3. **TRA-087 is PERSISTENT and slightly worse than R3**: the File Structure Summary is still missing 6 modules (benchmark, hitl, validate, config, recovery, reporting) AND now missing 5 test files (4 new test files added in R3 remediation — test_tra043_protocol.py, test_tra047_config_robustness.py, test_tra071_broken_markdown.py, test_e2e_to_translate.py, run_e2e_translation.py — were never added to the plan doc).
4. **TRA-090/091/092/094/095/100 untouched**: no commit addressed the test-infrastructure and doc-template findings; they remain exactly as in Round 3.
5. **TRA-072/079 untouched**: core architectural warnings (universal PolicyResolver arbitration, cache integrity protection) were not addressed.
6. **No REGRESSED findings**: every R3 regression test that was passing still passes; every static fix that landed in the 6 remediation commits is still present at HEAD `805a8f8`.

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# Run all 64 outstanding-finding regression tests (14 cover R3-register findings)
python -m pytest tests/test_outstanding_findings.py -q
# → 64 passed in 0.55s

# Per-class runs for the 14 R3-relevant test classes
for tc in TestTRA001SegmentLevel TestTRA038UnknownTermRaised TestTRA073DeadCodeRemoved \
          TestTRA074ClockSeedDefault TestTRA075PairwiseTransitions TestTRA076LLMOutputSanitized \
          TestTRA077CacheJsonNotPickle TestTRA078SecretRedaction TestTRA088SingleAuditRecordAllExceptions \
          TestTRA089ConformanceFailureE2E TestTRA093BrokenLinkFalsePositive TestTRA096AsInterfaceProtocol \
          TestTRA097RegisterProtocolCheck TestTRA098RegistryDuplicateDetection; do
  python -m pytest tests/test_outstanding_findings.py -k "$tc" -q
done
# → all 14 classes PASS (25 tests total)

# Static checks for the 22 findings without regression tests
grep -n "count_blocking" tra/diagnostics.py                    # TRA-016 → no match (FIXED)
python -c "import tomllib; ..." pyproject.toml                  # TRA-017 → 6 runtime deps (FIXED)
grep -n "expire" config.yaml tra/config.py                      # TRA-026 → no match (FIXED)
grep -n "EXCEPTION_HANDLER\|HALT_ERROR" tra/kernel.py           # TRA-040 → string-only, not enum (PERSISTENT)
sed -n '524,535p' tra/isa.py                                    # TRA-042 → heading-count-only (PERSISTENT)
grep -rn "_POLICY_RESOLVER.wins" tra/                            # TRA-072 → 1 call site (PERSISTENT)
grep -n "hmac\|signature\|integrity" tra/cache.py               # TRA-079 → no match (PERSISTENT)
grep -n "TRA-006\|PolicyResolver" CLAUDE.md                     # TRA-080 → "fixed in Round 3" (FIXED)
grep -n "Policy" tra-prototype/README.md                        # TRA-081 → tra/policy.py (FIXED)
grep -n "TRA-004\|EntityAmbiguity" tra-prototype/README.md      # TRA-082 → misleading phrase retained (PARTIAL)
grep -n "tra-prototype/implementation_plan" README.md tra-prototype/README.md  # TRA-083 → no match (FIXED)
grep -n "different repo\|subdirectory" AGENTS.md                # TRA-084 → reconciled (FIXED)
head -1 status.md; sed -n '46p' status.md                       # TRA-085 → banner + body mismatch (PARTIAL)
grep -n "external codebase" implementation_plan.md              # TRA-086 → no match (FIXED)
sed -n '305,351p' implementation_plan.md                        # TRA-087 → 6 modules + 5 tests still missing (PERSISTENT)
grep -n "kernel_mod.translate_segment" tests/                   # TRA-090 → module-level patching (PERSISTENT)
grep -rn "interactive=True" tests/ tra/                         # TRA-091 → no match (PERSISTENT)
cat tests/benchmark/cases/*.jsonl | wc -l                       # TRA-092 → 22 cases (PERSISTENT)
sed -n '86p' tra/reporting.py                                   # TRA-094 → substring heuristic (PERSISTENT)
grep -n "interactive\|Unrecoverable" tra_cli.py                 # TRA-095 → flag exists, path still hard to trigger (PERSISTENT)
grep -n "TRAKernel\|registry=" tra_cli.py                       # TRA-099 → no registry= kwarg (PERSISTENT)
grep -n "LanguageModuleProtocol\|as_interface" TRA-MODULE-ZH-EN.md  # TRA-100 → no match (PERSISTENT)

# Total test count at HEAD (for context vs TRA-085's stale "174+" banner)
python -m pytest tests/                                         # → 199 passed
```
