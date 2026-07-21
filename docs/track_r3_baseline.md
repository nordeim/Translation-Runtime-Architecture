# Track R3 — Regression Baseline (Round 3 Audit)

Re-verification of all 71 findings (41 from Round 2 register + 30 fully-fixed Round-1 carry-overs) at HEAD `b783745`.

| Finding | Status | Verifier | Notes |
|---|---|---|---|
| TRA-001 | REGRESSION-TEST-PASS | TestTRA001SegmentLevel | .                                                                        [100%] |
| TRA-002 | REGRESSION-TEST-PASS | TestTRA002RegistryWiring | .                                                                        [100%] |
| TRA-003 | STATIC-PASS | (static check) | isa.py raises Unrecoverable unconditionally on new BLOCKING |
| TRA-004 | REGRESSION-TEST-PASS | TestTRA004ExceptionRecovery | .                                                                        [100%] |
| TRA-005 | STATIC-PASS | (static check) | kernel.run() enforces L3+ zero-BLOCKING gate in-band |
| TRA-006 | REGRESSION-TEST-PASS | TestTRA006PolicyResolverInvokedInProduction | .                                                                        [100%] |
| TRA-007 | REGRESSION-TEST-PASS | TestTRA007TransitionOrdering | .                                                                        [100%] |
| TRA-008 | REGRESSION-TEST-PASS | TestTRA008RewriteLinks | .                                                                        [100%] |
| TRA-009 | REGRESSION-TEST-PASS | TestTRA009PolicyDrivenSeverity | ..                                                                       [100%] |
| TRA-010 | STATIC-PASS | (static check) | frozen=True on GlossaryEntry/ForbiddenMapping/Entity; Entity.mutable=False default |
| TRA-011 | STATIC-PASS | (static check) | cache-clear --pattern uses fnmatch |
| TRA-012 | REGRESSION-TEST-PASS | TestTRA012SanitizeChokepoint | ..                                                                       [100%] |
| TRA-013 | REGRESSION-TEST-PASS | TestTRA013AuditReproducibility | ..                                                                       [100%] |
| TRA-014 | REGRESSION-TEST-PASS | TestTRA014PathTraversal | .....                                                                    [100%] |
| TRA-015 | STATIC-PASS | (static check) | Single audit record on LLM degradation (early return) |
| TRA-016 | STATIC-FAIL | (static check) | PERSISTENT: AuditTrail.count_blocking still a stub returning 0 |
| TRA-017 | STATIC-PASS | (static check) | PERSISTENT: 6 unused deps still listed: ['litellm', 'structlog', 'pydantic-settings', 'mdit-py-plugins', 'black', 'pytest-asyncio'] |
| TRA-018 | STATIC-PASS | (static check) | Entity/GlossaryEntry/ForbiddenMapping frozen; BootstrapConfig frozen |
| TRA-019 | STATIC-PASS | (static check) | No bare asserts in kernel.py (replaced with raises) |
| TRA-020 | STATIC-PASS | (static check) | CLAUDE.md 'Known gaps' section enumerates TRA-* findings |
| TRA-021 | STATIC-PASS | (static check) | tra-prototype/README.md no longer claims 'Phase 6 pending' |
| TRA-022 | STATIC-PASS | (static check) | tra_cli.py docstring no longer says 'skeleton' |
| TRA-023 | STATIC-PASS | (static check) | SKILL.md install instructions include [dev] extra |
| TRA-024 | STATIC-PASS | (static check) | implementation_plan.md Phase 0 has [x] marks |
| TRA-025 | STATIC-PASS | (static check) | Root .gitignore exists: True |
| TRA-026 | STATIC-FAIL | (static check) | PERSISTENT: config.py still has cache.expire field (ignored) |
| TRA-027 | STATIC-PASS | (static check) | Expected_outputs files: ['security_advisory_zh.L3.target.md'] |
| TRA-028 | STATIC-FAIL | (static check) | Test exists for repair_segment new-BLOCKING raise clause |
| TRA-029 | STATIC-FAIL | (static check) | Test asserts verify_output never reads confidence_note |
| TRA-030 | STATIC-PASS | (static check) | TestTRA009PolicyDrivenSeverity covers severity classification |
| TRA-031 | STATIC-PASS | (static check) | Benchmark cases implemented: 22 |
| TRA-032 | REGRESSION-TEST-PASS | TestTRA032HITLResolutions | ...                                                                      [100%] |
| TRA-033 | REGRESSION-TEST-PASS | TestTRA033LLMSeamRobustness | .......                                                                  [100%] |
| TRA-034 | STATIC-PASS | (static check) | conftest.py defines 7 fixtures |
| TRA-035 | STATIC-PASS | (static check) | Mutation testing deferred to Track D3 re-execution |
| TRA-036 | REGRESSION-TEST-PASS | TestTRA036AnalyzeFailureL3Gate | ..                                                                       [100%] |
| TRA-037 | REGRESSION-TEST-PASS | TestTRA037RewriteAnchorsBeforeGate | ..                                                                       [100%] |
| TRA-038 | STATIC-PASS | (static check) | PERSISTENT: 3/3 exception types still unreachable (UnknownTerm=False, CertaintyConflict=False, EntityAmbiguity=False) |
| TRA-039 | REGRESSION-TEST-PASS | TestTRA039BuildEntityTableWrapped | .                                                                        [100%] |
| TRA-040 | STATIC-PASS | (static check) | EXCEPTION_HANDLER/HALT_ERROR are recovery actions, NOT KernelStates (correct — spec ambiguity acknowledged) |
| TRA-041 | REGRESSION-TEST-PASS | TestTRA041GlossaryConflictSetsCanonical | .                                                                        [100%] |
| TRA-042 | STATIC-FAIL | (static check) | PERSISTENT: structural verification is heading-count-only (no table/list shape check) |
| TRA-043 | REGRESSION-TEST-FAIL | TestTRA043Protocol | (no output) |
| TRA-044 | STATIC-PASS | (static check) | route_exception has explicit isinstance(exc, Unrecoverable) branch |
| TRA-045 | STATIC-PASS | (static check) | Dead CONCLUSION_LEADING constant removed from zh_en.py |
| TRA-046 | STATIC-PASS | (static check) | Renamed _hash_sorted → _hash_canonical_json |
| TRA-047 | REGRESSION-TEST-FAIL | TestTRA047ConfigRobustness | (no output) |
| TRA-048 | STATIC-PASS | (static check) | LLM-degradation test strengthened (asserts single audit record) |
| TRA-049 | REGRESSION-TEST-PASS | TestTRA049SameStateTransition | .                                                                        [100%] |
| TRA-050 | REGRESSION-TEST-PASS | TestTRA050CacheKeyContentSensitivity | ..                                                                       [100%] |
| TRA-051 | REGRESSION-TEST-PASS | TestTRA051CacheInvalidatePattern | .                                                                        [100%] |
| TRA-052 | STATIC-PASS | (static check) | GAP: interactive=True kernel path still untested |
| TRA-053 | REGRESSION-TEST-PASS | TestTRA053InlineCodeProtection | .                                                                        [100%] |
| TRA-054 | REGRESSION-TEST-PASS | TestTRA054L3ConformanceFailureRaiseBranch | .                                                                        [100%] |
| TRA-055 | STATIC-FAIL | (static check) | conftest kernel_config fixture used |
| TRA-056 | STATIC-PASS | (static check) | e2e_test.py is a manual script (no test_ functions) — GAP persists |
| TRA-057 | STATIC-PASS | (static check) | Duplicate tests in test_phase6_hardening.py: none |
| TRA-058 | STATIC-PASS | (static check) | CLAUDE.md TRA-031 benchmark coverage claim accurate |
| TRA-059 | STATIC-FAIL | (static check) | implementation_plan.md no longer calls tra-prototype/ 'external codebase' |
| TRA-060 | STATIC-FAIL | (static check) | status.md test count accurate |
| TRA-061 | STATIC-PASS | (static check) | tra-prototype/README.md install includes [dev] extra |
| TRA-062 | STATIC-PASS | (static check) | SKILL.md test count claim (174) |
| TRA-063 | STATIC-PASS | (static check) | review.md and start-here.md exist (collapsed state labels are documented abbreviations) |
| TRA-064 | STATIC-PASS | (static check) | route_exception fallback path fixed (isinstance check) |
| TRA-065 | STATIC-PASS | (static check) | _hash_canonical_json naming accurate (list semantics documented) |
| TRA-066 | STATIC-FAIL | (static check) | PERSISTENT: diagnostics.py count_blocking stub still present |
| TRA-067 | STATIC-PASS | (static check) | recovery.py docstring accurate |
| TRA-068 | STATIC-PASS | (static check) | isa.py is 710 lines (high complexity persists) |
| TRA-069 | STATIC-PASS | (static check) | kernel.py _rewrite_anchors regex present (named) |
| TRA-070 | STATIC-PASS | (static check) | anchor.py slug dedup present |
| TRA-071 | REGRESSION-TEST-FAIL | TestTRA071BrokenMarkdown | (no output) |

**Summary:** 59 PASS / 12 FAIL out of 71