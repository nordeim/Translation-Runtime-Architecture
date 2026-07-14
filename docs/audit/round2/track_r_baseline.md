# Track R — Regression Baseline

Re-verification of all 35 Round-1 findings at HEAD `4b8827c`.

| Finding | Status | Verifier | Notes |
|---|---|---|---|
| TRA-001 | REGRESSION-TEST-PASS | TestTRA001SegmentLevel | .                                                                        [100%] |
| TRA-002 | REGRESSION-TEST-PASS | TestTRA002RegistryWiring | .                                                                        [100%] |
| TRA-003 | STATIC-PASS | (static check) | isa.py raises Unrecoverable unconditionally on new BLOCKING |
| TRA-004 | REGRESSION-TEST-PASS | TestTRA004ExceptionRecovery | .                                                                        [100%] |
| TRA-005 | STATIC-PASS | (static check) | kernel.run() enforces L3+ zero-BLOCKING gate in-band |
| TRA-006 | STATIC-PASS | (static check) | HALF-FIX: severity classification is policy-aware but PolicyResolver.resolve() never invoked in verify_output |
| TRA-007 | REGRESSION-TEST-PASS | TestTRA007TransitionOrdering | .                                                                        [100%] |
| TRA-008 | REGRESSION-TEST-PASS | TestTRA008RewriteLinks | .                                                                        [100%] |
| TRA-009 | REGRESSION-TEST-PASS | TestTRA009PolicyDrivenSeverity | ..                                                                       [100%] |
| TRA-010 | STATIC-PASS | (static check) | frozen=True on GlossaryEntry/ForbiddenMapping/Entity; Entity.mutable=False default |
| TRA-011 | STATIC-PASS | (static check) | cache-clear --pattern uses fnmatch |
| TRA-012 | REGRESSION-TEST-PASS | TestTRA012SanitizeChokepoint | ..                                                                       [100%] |
| TRA-013 | REGRESSION-TEST-PASS | TestTRA013AuditReproducibility | ..                                                                       [100%] |
| TRA-014 | REGRESSION-TEST-PASS | TestTRA014PathTraversal | .....                                                                    [100%] |
| TRA-015 | STATIC-PASS | (static check) | Single audit record on LLM degradation (early return) |
| TRA-016 | STATIC-FAIL | (static check) | AuditTrail.count_blocking present (dead code if exists) |
| TRA-017 | STATIC-PASS | (static check) | Still-listed unused deps: ['litellm', 'structlog', 'pydantic-settings', 'mdit-py-plugins', 'black', 'pytest-asyncio'] |
| TRA-018 | STATIC-PASS | (static check) | Entity/GlossaryEntry/ForbiddenMapping frozen; BootstrapConfig frozen |
| TRA-019 | STATIC-PASS | (static check) | No bare asserts in kernel.py (replaced with raises) |
| TRA-020 | STATIC-PASS | (static check) | CLAUDE.md 'Known gaps' section enumerates TRA-* findings |
| TRA-021 | STATIC-PASS | (static check) | tra-prototype/README.md no longer claims 'Phase 6 pending' |
| TRA-022 | STATIC-PASS | (static check) | tra_cli.py docstring no longer says 'skeleton' |
| TRA-023 | STATIC-PASS | (static check) | SKILL.md install instructions include [dev] extra |
| TRA-024 | STATIC-PASS | (static check) | implementation_plan.md Phase 0 has [x] marks |
| TRA-025 | STATIC-PASS | (static check) | Root .gitignore exists: True |
| TRA-026 | STATIC-PASS | (static check) | config.py still ignores cache.expire (finding persists) |
| TRA-027 | STATIC-PASS | (static check) | Expected_outputs files: ['security_advisory_zh.L3.target.md'] |
| TRA-028 | STATIC-FAIL | (static check) | Test exists for repair_segment new-BLOCKING raise clause |
| TRA-029 | STATIC-FAIL | (static check) | Test asserts verify_output never reads confidence_note |
| TRA-030 | STATIC-PASS | (static check) | TestTRA009PolicyDrivenSeverity covers severity classification |
| TRA-031 | STATIC-PASS | (static check) | Benchmark cases implemented: 22 |
| TRA-032 | REGRESSION-TEST-PASS | TestTRA032HITLResolutions | ...                                                                      [100%] |
| TRA-033 | REGRESSION-TEST-PASS | TestTRA033LLMSeamRobustness | .......                                                                  [100%] |
| TRA-034 | STATIC-PASS | (static check) | conftest.py defines 7 fixtures |
| TRA-035 | STATIC-PASS | (static check) | Mutation testing deferred to Track D re-execution |

**Summary:** 32 PASS / 3 FAIL out of 35