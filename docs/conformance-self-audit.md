# TRA Prototype Engine — Conformance Self-Audit Checklist

**Auto-generated from code at HEAD `f782043`.**

This checklist operationalizes `TRA-CONFORMANCE-GUIDE.md` against the
actual implementation. Each item cites the code location that satisfies
the requirement.

---

## L1 Basic

| Requirement | Status | Code Evidence |
|---|---|---|
| Preserves meaning and formatting | ✅ | `tra/isa.py:translate_segment` — rule path applies glossary + entity + epistemic substitution |
| Allows minor terminology drift | ✅ | L1 does not enforce zero-BLOCKING (`tra/kernel.py:356-364`) |
| Pipeline does not crash on malformed input | ✅ | `tra/isa.py:103` raises `BrokenMarkdown` → `_recover` dispatches |
| Output is non-empty for non-empty input | ✅ | L1 returns best-effort output (no ConformanceFailure) |

---

## L2 Professional

| Requirement | Status | Code Evidence |
|---|---|---|
| All L1 requirements | ✅ | L2 subsumes L1 |
| Terminology consistency | ✅ | `build_glossary` produces canonical mappings; `verify_output` checks adherence |
| Entity preservation | ✅ | `build_entity_table` marks all entities `mutable=False`; `verify_output` checks verbatim presence |
| Basic QA | ✅ | `verify_output` runs structural + entity + terminology + epistemic checks |
| L2 does NOT enforce zero-BLOCKING | ✅ | `tra/kernel.py:356-364` — L3/L4 only |
| L2 does NOT emit L4 artifacts | ✅ | `evidence_trace.jsonl` + `ambiguity_register.json` are L4-only (`tra/kernel.py:629`) |

---

## L3 Strict

| Requirement | Status | Code Evidence |
|---|---|---|
| All L2 requirements | ✅ | L3 subsumes L2 |
| Explicit glossary | ✅ | `compilation_artifacts/glossary.yaml` exported |
| Explicit entity table | ✅ | `compilation_artifacts/entity_table.yaml` exported |
| Diagnostic reporting | ✅ | `audit_trace.jsonl` (JSONL, one AuditRecord per line) |
| Structural map | ✅ | `compilation_artifacts/structural_map.json` exported |
| Style profile | ✅ | `compilation_artifacts/style_profile.yaml` exported |
| Execution log | ✅ | `compilation_artifacts/execution_log.json` exported |
| Repair history | ✅ | `compilation_artifacts/repair_history.jsonl` exported |
| Zero BLOCKING required | ✅ | `tra/kernel.py:356-364` — ConformanceFailure raised if BLOCKING remain |
| Analyze-failure gate (TRA-036) | ✅ | `tra/kernel.py:267-280` — raises ConformanceFailure at L3/L4 |
| Broken-link gate (TRA-037) | ✅ | `tra/kernel.py:356-364` — BROKEN_LINK entries raise ConformanceFailure |
| PolicyResolver universal arbitration (TRA-072) | ✅ | `tra/isa.py:verify_output` — all 5 severity pairs arbitrated |
| Factual integrity check (TRA-A5-013) | ✅ | `tra/isa.py:verify_output` — version + date token preservation |
| Structural verification extended (TRA-042) | ✅ | 6 categories: heading, table, list, blockquote, HR, code fence |
| Exception recovery wired (TRA-038) | ✅ | UnknownTerm, CertaintyConflict, EntityAmbiguity all wired |
| EMPTY_SOURCE raises BrokenMarkdown (TRA-E5-003) | ✅ | `tra/isa.py:103` — BLOCKING severity per Spec §6 |
| Per-leaf segment translation (TRA-001) | ✅ | `StructuralMap.iter_leaf_segments()` + per-leaf `translate_segment` |
| LLM seam via DI (TRA-D5-002) | ✅ | `TRAKernel.run(llm_translate=callback)` |
| Cache HMAC integrity (TRA-079) | ✅ | `tra/cache.py` — HMAC-SHA256 signed entries |
| Cache JSON not pickle (TRA-077) | ✅ | `tra/cache.py:set` — `model_dump_json()` |
| LLM output sanitized (TRA-076) | ✅ | `tra/isa.py:translate_segment` — `sanitize_input` on LLM output |
| Exception repr sanitized (TRA-078) | ✅ | `tra/kernel.py:_sanitize_exc_repr` |
| Path traversal protected (TRA-014) | ✅ | `tra/config.py:_validate_paths_within_base_dir` |

---

## L4 Forensic

| Requirement | Status | Code Evidence |
|---|---|---|
| All L3 requirements | ✅ | L4 subsumes L3 |
| Line-by-line evidence tracing | ✅ | `compilation_artifacts/evidence_trace.jsonl` emitted at L4 |
| Ambiguity register | ✅ | `compilation_artifacts/ambiguity_register.json` emitted at L4 |
| Byte-reproducibility (TRA-013) | ✅ | `audit_trace.jsonl` sha256 identical across cold-cache runs |
| Deterministic clock | ✅ | `tra/kernel.py:_deterministic_clock` seeded from source hash |
| Content-addressed evidence IDs | ✅ | `tra/diagnostics.py:EvidenceRegistry.add` — SHA-256 of canonical record |
| EXCEPTION_HANDLER audit records | ✅ | UnknownTerm emits EXCEPTION_HANDLER record (TRA-A5-003) |
| 9/9 L4 artifacts present | ✅ | glossary + entity + structural_map + style_profile + execution_log + repair_history + audit_trace + evidence_trace + ambiguity_register |

---

## Conformance Artifacts (L3+ checklist per TRA-CONFORMANCE-GUIDE.md)

| Artifact | Contents | Status |
|---|---|---|
| `tvm_bootstrap` | Engine configuration | ✅ `config.yaml` (BootstrapConfig) |
| `compilation_artifacts` | Glossary + Structural Map | ✅ `glossary.yaml`, `entity_table.yaml`, `structural_map.json`, `style_profile.yaml`, `execution_log.json`, `repair_history.jsonl` |
| `audit_trace` | Diagnostics — zero BLOCKING for L3+ | ✅ `audit_trace.jsonl` (JSONL, one AuditRecord per line) |

---

## Quality Gates

| Gate | Command | Status |
|---|---|---|
| Format | `ruff format --check .` | ✅ 39 files already formatted |
| Lint | `ruff check .` | ✅ All checks passed! |
| Type check | `mypy --strict tra` | ✅ 0 issues, 20 source files |
| Test suite | `pytest tests` | ✅ 309 passed |

---

## Benchmark Suite Results

| Category | Cases | Passed | BLOCKING |
|---|---|---|---|
| S (Structural) | 10 | 10 | 0 |
| F (Factual) | 8 | 8 | 0 |
| T (Terminology) | 7 | 7 | 0 |
| D (Domain) | 6 | 6 | 0 |
| E (Ambiguity) | 4 | 4 | 0 |
| R (Regression) | 1 | 1 | 0 |
| **Total** | **36** | **36** | **0** |

**L3 verdict: CONFORMANT** — zero BLOCKING diagnostics across all 36
benchmark cases.

---

## Test Suite Summary

| Metric | Value |
|---|---|
| Total tests | 309 |
| Test files | 16 |
| Test classes in `test_outstanding_findings.py` | 71 |
| Benchmark cases | 36 |
| Mutation testing | Configured (`mutmut`, `pyproject.toml [tool.mutmut]`) |
