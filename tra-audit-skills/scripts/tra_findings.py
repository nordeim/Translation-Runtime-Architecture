"""TRA Prototype Audit — Master Findings Register.

Single source of truth consumed by the .xlsx, .docx, and chart generators.
Severity lexicon mirrors the TRA spec: BLOCKING / WARNING / INFO.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Master findings table — one row per finding, de-duplicated across tracks.
# Columns: id, severity, category, track, title, evidence, detail, suggested_fix
# ---------------------------------------------------------------------------

FINDINGS: list[dict[str, str]] = [
    # ===== TRACK A — SPEC CONFORMANCE =====
    {
        "id": "TRA-001",
        "severity": "BLOCKING",
        "category": "Spec Conformance / ISA Contract",
        "track": "A",
        "title": "TRANSLATE_SEGMENT receives whole document, not a segment",
        "evidence": "kernel.py:186; TRA-ISA-REFERENCE.md:48-49; cache.py:12-13",
        "detail": (
            "The ISA contract (TRA-ISA-REFERENCE.md §TRANSLATE_SEGMENT) mandates that the instruction "
            "operates on 'a specific source segment (sentence, list item, or table cell)'. The kernel "
            "passes the entire source markdown as one segment (kernel.py:186 `translate_segment(src, ...)`). "
            "Consequences: cache keys are per-document (violating cache.py:12-13 'never a whole document'), "
            "RepairAttempt.segment_index is always 0, L4 line-by-line trace uses substring heuristic "
            "rather than structural mapping, and is_no_translate_zone markers on code blocks are never "
            "consulted (S-03 violated). The kernel.py:184 inline comment admits 'Segment granularity is "
            "wired in Phase 3' — Phase 3 never landed."
        ),
        "suggested_fix": (
            "Refactor _execute_translation to iterate StructuralMap leaf nodes (paragraphs, list items, "
            "table cells, headings), call translate_segment per leaf, and reassemble via the structural map. "
            "Skip nodes where is_no_translate_zone=True."
        ),
    },
    {
        "id": "TRA-002",
        "severity": "BLOCKING",
        "category": "Spec Conformance / Module Extension",
        "track": "A",
        "title": "Module registry is the sanctioned extension point but kernel bypasses it",
        "evidence": "kernel.py:43,106; isa.py:50,54; CLAUDE.md:40; SKILL.md:151-163",
        "detail": (
            "CLAUDE.md and SKILL.md §6 document the module registry as the 'only sanctioned path' for new "
            "language bridges: `registry = build_default_registry(); registry.register(my_module.as_interface())`. "
            "In production code, the kernel hard-codes `ZHENModule()` directly (kernel.py:43 import, "
            "kernel.py:106 instantiation; isa.py:50,54 same pattern). Grep confirms ZERO production callers "
            "of build_default_registry or registry_for_language_pair. A user following SKILL.md §6 verbatim "
            "will find their registered module is NOT used by `tra_cli.py translate`."
        ),
        "suggested_fix": (
            "Replace the hard-coded `ZHENModule()` in kernel.py and isa.py with a registry lookup: "
            "`module = registry_for_language_pair(config.language_pair)`. Inject the module via constructor "
            "instead of module-level singleton."
        ),
    },
    {
        "id": "TRA-003",
        "severity": "BLOCKING",
        "category": "Spec Conformance / Critical Invariant",
        "track": "A",
        "title": "repair_segment does not enforce surgical invariant at function boundary",
        "evidence": "isa.py:515-519; TRA-ISA-REFERENCE.md:79; TRA-SPECIFICATION.md:83",
        "detail": (
            "The spec mandates 'Repair must resolve the specific violation without introducing new ones' "
            "(TRA-ISA-REFERENCE.md:79, mirrored in TRA-SPECIFICATION.md:83, CLAUDE.md:79, AGENTS.md:33, "
            "README.md:123). The code (isa.py:515-519) only raises Unrecoverable when "
            "`new_blocking and attempt >= max_retries`. At attempt=1 with max_retries=3, a repair that "
            "introduces new BLOCKING returns silently with resolved=False. Empirically confirmed: "
            "calling repair_segment(target='成立 Valid', attempt=1, max_retries=3) returns 'Confirmed Valid' "
            "(containing the forbidden drift target 'Valid') without raising. The kernel's _repair_loop "
            "catches this by re-queuing, but a direct caller receives broken output with no exception."
        ),
        "suggested_fix": (
            "Remove the `attempt >= max_retries` guard from the new-BLOCKING check. Raise Unrecoverable "
            "unconditionally on any new BLOCKING, regardless of attempt number. Add a regression test "
            "that calls repair_segment directly with attempt=1 and asserts the raise."
        ),
    },
    {
        "id": "TRA-004",
        "severity": "BLOCKING",
        "category": "Spec Conformance / Exception Recovery",
        "track": "A",
        "title": "4 of 5 TRA-EXCEPTION recovery procedures are unreachable",
        "evidence": "isa.py:84 (BrokenMarkdown raised, kernel.py:129 not caught); recovery.py:154",
        "detail": (
            "Spec §6 mandates deterministic recovery for all 5 TRA-EXCEPTION types. Grep across tra/ for "
            "`raise UnknownTerm|raise CertaintyConflict|raise EntityAmbiguity` returns ZERO hits — these "
            "exception classes exist but are never raised in production code paths. BrokenMarkdown IS "
            "raised by analyze_document (isa.py:84) but kernel.py:129 calls analyze_document with NO "
            "try/except, so a malformed source crashes the kernel with no EXCEPTION_HANDLER invocation. "
            "Only GlossaryConflict (build_glossary) and Unrecoverable (repair_segment) reach "
            "route_exception. The recovery.py dispatcher and 3 of its 5 handlers are dead code."
        ),
        "suggested_fix": (
            "Wrap each ISA call in kernel.run() with try/except TRAException and route through "
            "self._recover(). Add UNKNOWN_TERM / CERTAINTY_CONFLICT / ENTITY_AMBIGUITY raise sites in "
            "the relevant ISA instructions (translate_segment for UNKNOWN_TERM, verify_output for "
            "CERTAINTY_CONFLICT, build_entity_table for ENTITY_AMBIGUITY)."
        ),
    },
    {
        "id": "TRA-005",
        "severity": "BLOCKING",
        "category": "Spec Conformance / L3 Gate",
        "track": "A",
        "title": "kernel.run() does not enforce the L3 zero-BLOCKING gate",
        "evidence": "kernel.py:157; tra_cli.py:106-120; TRA-CONFORMANCE-GUIDE.md:51",
        "detail": (
            "Per TRA-CONFORMANCE-GUIDE.md:51, 'If [BLOCKING diagnostics are] present, certification is "
            "denied.' The kernel's run() method (kernel.py:157) returns the target unconditionally, even "
            "when _repair_loop exhausts max_retries with BLOCKING diagnostics still present. The CLI "
            "(tra_cli.py:106-120) only prints a warning. Only validate.py and benchmark.py enforce "
            "zero-BLOCKING. A user running `tra_cli.py translate --level L3` on a document that produces "
            "BLOCKING diagnostics receives a 'translated' output and no error signal."
        ),
        "suggested_fix": (
            "After _repair_loop, re-run verify_output. If any BLOCKING remains, raise a TRAException "
            "(e.g., ConformanceFailure) that the CLI catches and exits 1 with a clear message. Document "
            "that `translate` is a best-effort runner and `validate` is the certification gate."
        ),
    },
    {
        "id": "TRA-006",
        "severity": "WARNING",
        "category": "Spec Conformance / Policy Engine",
        "track": "A",
        "title": "PolicyResolver is scaffolding — never invoked in production",
        "evidence": "policy.py:13 (definition); test_phase0.py:23 (only test import)",
        "detail": (
            "The 6-priority PolicyResolver exists but is never called by the kernel or ISA. Grep confirms "
            "only the definition and a test import. The policy_stack is consulted only for cache-key "
            "hashing (cache.py:65), never for arbitration. verify_output has no Factual-Integrity check "
            "(strings like '<60ms', '96-core', '<5MB' aren't entities and aren't verified), no structural "
            "check beyond heading count, no fluency check. The spec's scope rules (code blocks: only "
            "Fluency relaxable; headings: Factual beats Structural) are not implemented."
        ),
        "suggested_fix": (
            "Wire PolicyResolver into verify_output and repair_segment. At minimum, implement the Factual "
            "Integrity check (numbers/units/versions preservation beyond entity extraction) and the scope "
            "rules for code blocks vs headings."
        ),
    },
    {
        "id": "TRA-007",
        "severity": "WARNING",
        "category": "Spec Conformance / Kernel Transitions",
        "track": "A",
        "title": "Kernel transitions fire BEFORE ISA completion, not after",
        "evidence": "kernel.py:127-157; CLAUDE.md:19; TRA-SPECIFICATION.md §2.1",
        "detail": (
            "CLAUDE.md:19 claims 'transitions only on successful ISA completion'. The kernel calls "
            "`self._transition(KernelState.ANALYZE_DOCUMENT)` at kernel.py:128 BEFORE calling "
            "`analyze_document(...)` at kernel.py:129. If the ISA raises, the state has already advanced. "
            "The spec §2.1 state diagram includes an EXCEPTION_HANDLER state for failed ISA calls — "
            "the kernel does not model this state at all."
        ),
        "suggested_fix": (
            "Move each `self._transition(...)` call to AFTER the corresponding ISA call returns "
            "successfully. Add a KernelState.EXCEPTION_HANDLER state (or route via _recover) for the "
            "failure path. Update CLAUDE.md:19 to match the implementation if you choose not to fix "
            "the code."
        ),
    },
    {
        "id": "TRA-008",
        "severity": "WARNING",
        "category": "Spec Conformance / Structural Integrity",
        "track": "A",
        "title": "Anchor rewrite_links defined but never called — S-06 dead in production",
        "evidence": "anchor.py:rewrite_links; kernel.py:142-156 (no rewrite call)",
        "detail": (
            "AnchorRegistry.rewrite_links is implemented and unit-tested (test_anchor.py S-06 case), "
            "but the kernel's _execute_translation never calls it. Translated headings produce new slugs "
            "that don't match internal `#anchor` links in the rest of the document. The structural "
            "integrity check in verify_output only counts headings — it does not verify link integrity."
        ),
        "suggested_fix": (
            "After reassembling translated segments, call `registry.rewrite_links(translated_ast)` before "
            "returning the target. Add a verify_output check that every internal `#link` resolves to a "
            "heading slug in the target."
        ),
    },
    {
        "id": "TRA-009",
        "severity": "WARNING",
        "category": "Spec Conformance / Terminological Consistency",
        "track": "A",
        "title": "Terminology violations classified as WARNING, not BLOCKING",
        "evidence": "isa.py:429",
        "detail": (
            "When a source glossary term leaks into the target untranslated, verify_output (isa.py:429) "
            "emits a WARNING. Per Spec §5, Terminological Consistency is Priority 4 — higher than "
            "Fluency (6) but lower than Entity (3). The spec does not mandate BLOCKING for terminology "
            "drift, but the L3 gate's 'zero BLOCKING' criterion means terminology drift alone never "
            "blocks certification. This may be intentional but should be documented."
        ),
        "suggested_fix": (
            "Either escalate terminology violations to BLOCKING at L3+ (stricter than spec, but safer), "
            "or document the WARNING classification explicitly in CLAUDE.md and TRA-CONFORMANCE-GUIDE.md."
        ),
    },
    {
        "id": "TRA-010",
        "severity": "WARNING",
        "category": "Spec Conformance / Memory Model",
        "track": "A",
        "title": "Memory model immutability claims unenforced",
        "evidence": "memory.py:172 (RuntimeContext not frozen); config.py:23 (BootstrapConfig not frozen)",
        "detail": (
            "Spec §4 describes Immutable Config (read-only) and Audit Memory (append-only). In code, "
            "BootstrapConfig is a plain Pydantic BaseModel (not frozen=True). The CLI directly mutates "
            "it (tra_cli.py:87-89 sets level/lang on the config object). AuditTrail is append-only by "
            "API convention but nothing prevents a stray `.records.clear()` call. count_blocking is a "
            "stub returning 0 (see TRA-016)."
        ),
        "suggested_fix": (
            "Add `model_config = ConfigDict(frozen=True)` to BootstrapConfig. Make AuditTrail.records "
            "a tuple or use a frozen list wrapper. Implement or remove count_blocking."
        ),
    },

    # ===== TRACK B — CODE QUALITY & SECURITY =====
    {
        "id": "TRA-011",
        "severity": "BLOCKING",
        "category": "Code Quality / Cache Invalidation",
        "track": "B",
        "title": "cache-clear --pattern is a silent no-op (diskcache.delete takes literal key)",
        "evidence": "cache.py:107-115; tra_cli.py:123-132",
        "detail": (
            "TranslationCache.invalidate(pattern) calls `self._cache.delete(pattern)`. diskcache's "
            "delete() takes a LITERAL key, not a glob. Empirically confirmed: invalidate('test*') on a "
            "cache with 3 entries deletes 0 (3→3); the literal-key invalidate works (3→2). The CLI "
            "(tra_cli.py:130) then prints 'Cache invalidated: <pattern>' unconditionally — lying to "
            "the user. A user who runs `tra cache-clear --pattern 'translation:*'` to invalidate stale "
            "entries believes they were cleared; they weren't. This could serve stale translations "
            "indefinitely."
        ),
        "suggested_fix": (
            "Implement glob via `for key in self._cache.iterkeys(): if fnmatch(key, pattern): "
            "self._cache.delete(key)`. Alternatively, drop --pattern and only support `cache-clear` "
            "(full clear). Update the CLI to print the actual count deleted."
        ),
    },
    {
        "id": "TRA-012",
        "severity": "WARNING",
        "category": "Code Quality / Input Sanitization",
        "track": "B",
        "title": "_sanitize_input bypassed at validate and benchmark boundaries",
        "evidence": "kernel.py:75-90 (regex); validate.py:71-72; benchmark.py:102-104",
        "detail": (
            "The _sanitize_input regex (kernel.py:78-80) correctly strips null bytes, C0 control chars, "
            "DEL, Unicode bidi overrides (\\u202a-\\u202e), and BOM (\\ufeff). It is only called from "
            "TRAKernel.run() (kernel.py:125). validate_translation (validate.py:71-72) calls "
            "analyze_document(source) directly with no sanitization. BenchmarkRunner.run_case "
            "(benchmark.py:102-104) re-verifies via analyze_document(case.source) unsanitized. A "
            "malicious candidate file with bidi-override characters could be processed by `tra validate` "
            "without sanitization, potentially confusing auditors who inspect the rendered output."
        ),
        "suggested_fix": (
            "Move _sanitize_input to a shared utility (e.g., utils.py or a new security.py). Call it "
            "at the top of validate_translation, analyze_document, and the benchmark re-verify block. "
            "Add a test that confirms bidi-override characters are stripped at every entry point."
        ),
    },
    {
        "id": "TRA-013",
        "severity": "WARNING",
        "category": "Code Quality / Reproducibility",
        "track": "B",
        "title": "Audit trail is NOT byte-reproducible (uuid4 + datetime.now)",
        "evidence": "diagnostics.py:40 (uuid4); diagnostics.py:58 (datetime.now(UTC))",
        "detail": (
            "Empirically confirmed: two runs of identical source produce identical target text, identical "
            "cache.db, identical glossary/entity/smap/style/exec_log/repair_history — but DIFFERENT "
            "audit_trace.jsonl. Diff shows every record differs in `timestamp`, and records 1-3 also "
            "differ in all evidence_chain IDs (random ev_<uuid4.hex[:12]>). For L4 forensic audits "
            "(legal/security per TRA-CONFORMANCE-GUIDE.md), this means you cannot cryptographically "
            "prove 'this audit trail corresponds to this output' by hashing the trail. The R-01 "
            "regression test (test_benchmark.py:65-71) only checks output equality, not audit-trail "
            "equality."
        ),
        "suggested_fix": (
            "Make evidence IDs deterministic: `ev_{sha256(content)[:12]}` instead of uuid4. Replace "
            "datetime.now(UTC) with a deterministic timestamp derived from the source hash, or accept "
            "an optional `timestamp` parameter. Add a test asserting audit-trail byte-equality across "
            "two runs of the same input."
        ),
    },
    {
        "id": "TRA-014",
        "severity": "WARNING",
        "category": "Security / Path Traversal",
        "track": "B",
        "title": "No path-traversal protection on config-supplied paths",
        "evidence": "config.py:23-55; kernel.py:240-312 (mkdir + write)",
        "detail": (
            "BootstrapConfig.from_yaml accepts compilation_dir, audit_trace, cache_directory from "
            "config.yaml with no sanitization. A malicious config with `compilation_dir: '../../../etc'`, "
            "`audit_trace: '/tmp/evil.jsonl'`, `cache_directory: '/var/tmp/evil-cache'` is accepted and "
            "the kernel writes 6-8 files there. AuditTrail.flush() calls mkdir(parents=True) on arbitrary "
            "paths. Acceptable for a trusted-config prototype; unacceptable for production."
        ),
        "suggested_fix": (
            "Resolve all config paths against a project root. Reject paths containing `..` or absolute "
            "paths outside the project root. Add a test that confirms a malicious config is rejected."
        ),
    },
    {
        "id": "TRA-015",
        "severity": "WARNING",
        "category": "Code Quality / Audit Trail",
        "track": "B",
        "title": "Double audit record on LLM graceful degradation",
        "evidence": "isa.py:316-346",
        "detail": (
            "When llm_translate raises, isa.py:322-330 appends a TRANSLATE_SEGMENT record with "
            "artifact_snapshot={'degraded': True, 'reason': ...}. The code then FALLS THROUGH to "
            "isa.py:334-346, appending ANOTHER TRANSLATE_SEGMENT record (with evidence_chain, no "
            "degraded flag). Empirically verified: degraded translation produces 2 records — Record 0 "
            "{'degraded': True, ...}, Record 1 {}. An L3 auditor inspecting the LAST TRANSLATE_SEGMENT "
            "per segment misses the degradation. The existing test test_graceful_degradation_on_llm_failure "
            "uses any(...) so it passes but doesn't catch the double-record issue."
        ),
        "suggested_fix": (
            "Add a `return` statement after the degradation-notice audit.append, OR merge the degraded "
            "flag into the single normal-path record. Update the test to assert exactly one "
            "TRANSLATE_SEGMENT record per segment."
        ),
    },
    {
        "id": "TRA-016",
        "severity": "WARNING",
        "category": "Code Quality / Dead Code",
        "track": "B",
        "title": "AuditTrail.count_blocking is a stub returning 0 unconditionally",
        "evidence": "diagnostics.py:159-166",
        "detail": (
            "The method name suggests it counts BLOCKING diagnostics in the audit trail. The "
            "implementation returns 0 unconditionally with a comment 'hook for VERIFY to populate'. "
            "Zero callers in production or tests. If a future contributor trusts the method name, they "
            "will get a false L3 PASS. Real counting lives in reporting.summarize_audit and "
            "validate.ValidationReport."
        ),
        "suggested_fix": (
            "Either implement count_blocking by scanning the audit trail for records with "
            "'BLOCKING' in flags_raised, or delete the method and direct readers to "
            "reporting.summarize_audit."
        ),
    },
    {
        "id": "TRA-017",
        "severity": "WARNING",
        "category": "Code Quality / Dependency Hygiene",
        "track": "B",
        "title": "5 unused dependencies inflate install footprint (~50+ transitive packages)",
        "evidence": "pyproject.toml:10-21; grep across tra/ for imports",
        "detail": (
            "litellm (>=1.49), structlog (>=24.1), pydantic-settings (>=2.3), mdit-py-plugins (>=0.4), "
            "and black (>=24.4, dev) are listed but never imported. litellm alone pulls ~30 transitive "
            "deps (openai, tiktoken, tokenizers, huggingface-hub, httpx, aiohttp, jinja2, jsonschema, ...). "
            "The LLM seam is wired as a caller-supplied Callable, so litellm is not actually needed at "
            "runtime. pytest-asyncio (dev) is also unused (asyncio_mode=auto set but zero async tests). "
            "Total install: ~50+ packages, hundreds of MB, for a rule-based prototype."
        ),
        "suggested_fix": (
            "Move litellm to optional-dependencies.llm. Drop pydantic-settings, mdit-py-plugins, "
            "structlog, black, pytest-asyncio from the manifest. Add a 'Dependency hygiene' bullet to "
            "CLAUDE.md Known gaps."
        ),
    },
    {
        "id": "TRA-018",
        "severity": "WARNING",
        "category": "Code Quality / Pydantic v2",
        "track": "B",
        "title": "Immutability claims on Entity and BootstrapConfig unenforced (no frozen=True)",
        "evidence": "memory.py:154 (Entity); config.py:23 (BootstrapConfig)",
        "detail": (
            "Entity is documented as 'an immutable identifier isolated from natural-language translation' "
            "but is a plain BaseModel with mutable=True default. BootstrapConfig is described as the "
            "'Immutable Config (read-only)' memory segment but is also a plain BaseModel. The CLI "
            "(tra_cli.py:87-89) directly mutates BootstrapConfig. Zero ConfigDict(frozen=True) anywhere "
            "in the codebase. Zero Field constraints (min_length, pattern, ge, le) on any model."
        ),
        "suggested_fix": (
            "Add `model_config = ConfigDict(frozen=True)` to Entity, GlossaryEntry, ForbiddenMapping, "
            "and BootstrapConfig. For RuntimeContext (which must be mutable), leave unfrozen but "
            "document why. Add Field constraints where applicable (e.g., ConformanceLevel enum, "
            "non-empty source strings)."
        ),
    },
    {
        "id": "TRA-019",
        "severity": "WARNING",
        "category": "Code Quality / Assert Usage",
        "track": "B",
        "title": "2 runtime asserts in kernel.py stripped under python -O",
        "evidence": "kernel.py:130-131",
        "detail": (
            "kernel.py:130-131 uses `assert self.ctx.document_profile is not None` and "
            "`assert self.ctx.structural_map is not None` for runtime validation. Python asserts are "
            "stripped when the interpreter runs with -O (optimized mode). A production deployment using "
            "-O would silently skip these checks. The spec's 'never skip instructions' principle "
            "suggests these should be hard raises."
        ),
        "suggested_fix": (
            "Replace `assert x is not None` with `if x is None: raise TRAException(...)`. Reserve "
            "assert for invariants that are truly impossible to violate."
        ),
    },

    # ===== TRACK C — DOC-VS-CODE CONSISTENCY =====
    {
        "id": "TRA-020",
        "severity": "BLOCKING",
        "category": "Doc Consistency / Known Gaps",
        "track": "C",
        "title": "CLAUDE.md 'Known gaps (honest, not yet addressed)' lists only 3 of ~16 material gaps",
        "evidence": "CLAUDE.md:42-46",
        "detail": (
            "CLAUDE.md:42-46 labels the list 'Known gaps (honest, not yet addressed)' but enumerates "
            "only: structlog unused, no asyncio parallelism, no cross-run glossary/entity caching. "
            "At least 16 material gaps exist (TRA-001 through TRA-019 in this audit, plus Phase 7 "
            "items). The word 'honest' is itself misleading when the list omits the most material "
            "gaps (segment-level granularity, registry bypass, repair-attempt-1, exception recovery, "
            "L3 gate not enforced in translate, count_blocking stub, cache-clear no-op, etc.)."
        ),
        "suggested_fix": (
            "Replace the 3-bullet list with a numbered list of all known material gaps (this audit's "
            "TRA-001 through TRA-019 is a starting point). Drop the word 'honest' or make it true. "
            "Cross-reference each gap to its finding ID for traceability."
        ),
    },
    {
        "id": "TRA-021",
        "severity": "BLOCKING",
        "category": "Doc Consistency / Status Header",
        "track": "C",
        "title": "tra-prototype/README.md says 'Phase 0-5' and 'Phase 6 pending' — both false",
        "evidence": "tra-prototype/README.md:3, 78-79",
        "detail": (
            "tra-prototype/README.md:3 says 'A Phase 0-5 reference implementation of TRA v1.0'. "
            "Line 78-79 says 'Phase 6 (exception hardening, human-in-the-loop, structlog, L4 evidence "
            "tracing) is pending.' Reality: Phase 6 IS implemented — 6.1 (recovery.py), 6.2 (hitl.py + "
            "--interactive), 6.3 (reporting.py, Mermaid, audit summary), 6.4 (kernel.py:293-312 "
            "_export_forensics, L4 trace), 6.5 (kernel.py:75-90 _sanitize_input + isa.py:316-330 "
            "graceful degradation). Only 6.3.1 structlog is genuinely pending. CLAUDE.md:15 and "
            "status.md:35 corroborate that Phase 6 landed in commit 4d97aa1."
        ),
        "suggested_fix": (
            "Update tra-prototype/README.md:3 to 'Phase 0-6 reference implementation'. Update L78-79 "
            "to reflect that only structlog (6.3.1) is pending. The prototype README is the file a new "
            "contributor reads first — accuracy here is load-bearing."
        ),
    },
    {
        "id": "TRA-022",
        "severity": "WARNING",
        "category": "Doc Consistency / Stale Docstring",
        "track": "C",
        "title": "tra_cli.py docstring says 'Phase 0.1.5 skeleton' with 3 subcommands — file has 4",
        "evidence": "tra_cli.py:1-7",
        "detail": (
            "tra_cli.py:1-7 docstring: 'Phase 0.1.5 skeleton ... subcommands: translate, cache-clear, "
            "audit.' The file actually implements 4 subcommands (validate at L197) and is no longer a "
            "skeleton. Stale docstrings mislead contributors and AI agents reading the file."
        ),
        "suggested_fix": (
            "Update tra_cli.py:1-7 to list all 4 subcommands (translate, validate, audit, cache-clear) "
            "and drop the 'Phase 0.1.5 skeleton' label."
        ),
    },
    {
        "id": "TRA-023",
        "severity": "WARNING",
        "category": "Doc Consistency / Setup Instructions",
        "track": "C",
        "title": "SKILL.md install instructions omit dev deps — contributor cannot run quality gates",
        "evidence": "SKILL.md:67-68",
        "detail": (
            "SKILL.md:67-68 says `pip install -e .` (no [dev] extra). Section 7 'Quality gates' "
            "(SKILL.md:172-176) requires ruff, mypy, pytest — all dev deps. A new contributor "
            "following SKILL.md verbatim installs only runtime deps and cannot run the gates. They "
            "either abandon the gates or sudo-install tools globally."
        ),
        "suggested_fix": (
            "Change SKILL.md:67 to `pip install -e .[dev]` (or `pip install -e '.[dev]'` for zsh). "
            "Add a note that the dev extra is required for the quality gates in §7."
        ),
    },
    {
        "id": "TRA-024",
        "severity": "WARNING",
        "category": "Doc Consistency / Implementation Plan",
        "track": "C",
        "title": "implementation_plan.md Phase 0 all unchecked but fully delivered; file-structure lists nonexistent tests",
        "evidence": "implementation_plan.md:14-55 (Phase 0 checkboxes); :305-347 (file structure)",
        "detail": (
            "Every Phase 0 item (0.1.1 through 0.4.3) is marked `[ ]` but all are implemented per "
            "the codebase. The file-structure summary (L305-347) lists test files that don't exist: "
            "test_policy.py, test_cache.py, test_evidence.py, benchmark/runner.py, benchmark/test_benchmarks.py. "
            "Actual tests: test_phase0.py, test_isa.py, test_kernel.py, test_recovery.py, test_validate.py, "
            "test_modules.py, test_benchmark.py, test_anchor.py, test_reporting.py, "
            "test_phase6_hardening.py, test_utils.py. Phase 1.3, 6.3.1, 6.5.1, 6.5.2, Phase 7 markings "
            "ARE accurate."
        ),
        "suggested_fix": (
            "Either check the Phase 0 boxes (`[x]`) or add a header note 'Phase 0 was delivered before "
            "this plan was last updated; checkboxes are stale.' Update the file-structure summary to "
            "match the actual test files."
        ),
    },
    {
        "id": "TRA-025",
        "severity": "WARNING",
        "category": "Doc Consistency / Repo Hygiene",
        "track": "C",
        "title": "No .gitignore at repo root — runtime artifacts (audit_trace.jsonl, cache/, compilation_artifacts/) committed",
        "evidence": "repo root LS; status.md:48-49 acknowledges",
        "detail": (
            "audit_trace.jsonl (451 lines), cache/cache.db, compilation_artifacts/{glossary,entity_table,"
            "structural_map,style_profile}.{yaml,json} exist at the REPO ROOT (outside tra-prototype/) "
            "from a prior run with cwd at the repo root. The tra-prototype/.gitignore covers them "
            "locally but the repo root has no .gitignore. status.md:48-49 acknowledges the issue but "
            "defers the fix. These artifacts pollute the spec repo and could be accidentally committed."
        ),
        "suggested_fix": (
            "Add a repo-root .gitignore covering /audit_trace.jsonl, /cache/, /compilation_artifacts/. "
            "Run `git rm --cached` on any tracked artifacts. Optionally `rm -rf` the existing root-level "
            "artifacts."
        ),
    },
    {
        "id": "TRA-026",
        "severity": "WARNING",
        "category": "Doc Consistency / Dead Config",
        "track": "C",
        "title": "config.yaml cache.expire field parsed by YAML but ignored by code",
        "evidence": "config.yaml:18; config.py:46-47; cache.py:105",
        "detail": (
            "config.yaml:18 sets `cache.expire: null`. BootstrapConfig.from_yaml (config.py:46-47) "
            "reads only `cache.enabled` and `cache.directory`. TranslationCache.set (cache.py:105) "
            "hardcodes `expire=None`. The field is misleading dead config — a user who sets "
            "`cache.expire: 3600` expects TTL-based eviction and gets none."
        ),
        "suggested_fix": (
            "Either wire cache.expire through to TranslationCache.set (and diskcache's expire parameter), "
            "or remove the field from config.yaml and document that the cache has no TTL by design "
            "(static facts, per implementation_plan.md §0.4.2)."
        ),
    },
    {
        "id": "TRA-027",
        "severity": "WARNING",
        "category": "Doc Consistency / Misleading Filename",
        "track": "C",
        "title": "examples/expected_outputs/security_advisory_zh.L3.md is just translated markdown, not an L3 bundle",
        "evidence": "examples/expected_outputs/security_advisory_zh.L3.md (file content)",
        "detail": (
            "The filename implies an L3 certification bundle (target + audit trace + glossary + "
            "conformance verdict). The file contains only the translated markdown. A reader expecting "
            "the full L3 evidence package will be confused. The audit trace, glossary, entity table, "
            "and conformance summary are not present."
        ),
        "suggested_fix": (
            "Rename to security_advisory_zh.L3.target.md (clarifying it's just the target text). "
            "Optionally populate a sibling security_advisory_zh.L3.bundle/ directory with the audit "
            "trace + artifacts + conformance verdict, OR add a README explaining the bundle structure."
        ),
    },

    # ===== TRACK D — TEST SUITE =====
    {
        "id": "TRA-028",
        "severity": "BLOCKING",
        "category": "Test Suite / Invariant Coverage",
        "track": "D",
        "title": "Zero test coverage on repair_segment's 'raise on new BLOCKING' clause",
        "evidence": "isa.py:515-519; test_isa.py (no such test); test_kernel.py (no such test)",
        "detail": (
            "Mutation testing: removing the `if new_blocking and attempt >= max_retries: raise "
            "Unrecoverable(...)` block entirely leaves all 103 tests green. Flipping `>=` to `>` "
            "(off-by-one) leaves all 103 tests green. Calling repair_segment directly with attempt=1 "
            "and new BLOCKING has no test asserting the raise behavior. The most dangerous gap: the "
            "test suite cannot detect regressions in the surgical-repair invariant's partial enforcement."
        ),
        "suggested_fix": (
            "Add test_repair_segment_raises_on_new_blocking: call repair_segment with a diagnostic it "
            "cannot fix (e.g., subsystem='entity', entity absent from source) at attempt=max_retries, "
            "assert Unrecoverable raised. Also add test_repair_segment_returns_silently_at_attempt_1 "
            "documenting the current (buggy) behavior, marked xfail, to be flipped when TRA-003 is fixed."
        ),
    },
    {
        "id": "TRA-029",
        "severity": "BLOCKING",
        "category": "Test Suite / Invariant Coverage",
        "track": "D",
        "title": "Invariant 3 (verify_output never self-scores) untested at enforcement boundary",
        "evidence": "test_phase0.py:68-82 (comment-only assertion)",
        "detail": (
            "Mutation testing: adding `if e.confidence_note and e.confidence_note < 0.5: "
            "diagnostics.append(...)` to verify_output leaves all 103 tests green. The existing "
            "test (test_phase0.py:68-82) adds a low-confidence record to the registry but never calls "
            "verify_output or repair_segment with that record present. It only asserts the record was "
            "added, not that it was ignored. The 'never self-score' invariant is documented but "
            "untested at the enforcement boundary."
        ),
        "suggested_fix": (
            "Add test_verify_output_ignores_confidence_note: populate ctx with an EvidenceRegistry "
            "containing a low-confidence record, run verify_output on a clean target, assert zero "
            "diagnostics. Repeat for repair_segment."
        ),
    },
    {
        "id": "TRA-030",
        "severity": "BLOCKING",
        "category": "Test Suite / Severity Classification",
        "track": "D",
        "title": "No test asserts terminology=WARNING and structural=BLOCKING severity classification",
        "evidence": "isa.py:429 (terminology=WARNING), :401-409 (structural=BLOCKING); test_isa.py",
        "detail": (
            "Mutation testing: changing Severity.WARNING to Severity.BLOCKING for terminology violations "
            "(isa.py:429) leaves all 103 tests green. Changing Severity.BLOCKING to Severity.WARNING for "
            "structural violations (isa.py:403) leaves all 103 tests green. The severity-classification "
            "contract is unprotected. A mutation escalating terminology to BLOCKING would silently make "
            "the L3 gate stricter than the spec intends; a mutation demoting structural to WARNING would "
            "silently make the L3 gate more permissive."
        ),
        "suggested_fix": (
            "Add test_verify_output_terminology_is_warning_not_blocking and "
            "test_verify_output_structural_mismatch_is_blocking. Each should construct a minimal "
            "source/target pair, run verify_output, and assert exactly one diagnostic with the expected "
            "severity and subsystem."
        ),
    },
    {
        "id": "TRA-031",
        "severity": "WARNING",
        "category": "Test Suite / Benchmark Coverage",
        "track": "D",
        "title": "Only 13 of 24 spec benchmark cases implemented (54%)",
        "evidence": "tests/benchmark/cases/sft.jsonl (13 cases); TRA-BENCHMARK-SUITE.md (24+ cases)",
        "detail": (
            "TRA-BENCHMARK-SUITE.md defines S-01..S-06, F-01..F-05, T-01..T-05, D-01..D-04, E-01..E-03 "
            "(24 cases). The prototype implements 13 (S-05, F-01..F-05, T-01..T-05, D-04, E-02) plus "
            "R-01 (regression, not in spec). Missing: S-01 (nested lists), S-02 (complex tables), "
            "S-03 (inline code vs prose — exposes the whole-doc translation gap), S-04 (blockquotes "
            "in lists), S-06 (anchors — unit-tested but not in benchmark), D-01/D-02/D-03 (domain "
            "cases), E-01 (intentional ambiguity), E-03 (broken source markdown — exposes the "
            "exception-recovery gap). Spec target is '100+'."
        ),
        "suggested_fix": (
            "Add the 11 missing JSONL cases. Mark S-03 and E-03 as xfail with referenced open issues "
            "(TRA-001 and TRA-004 respectively). Document the 13/24 coverage in CLAUDE.md Known gaps."
        ),
    },
    {
        "id": "TRA-032",
        "severity": "WARNING",
        "category": "Test Suite / HITL Coverage",
        "track": "D",
        "title": "HITL only tested for 'accept' path; 'override' and 'skip' untested; interactive=True kernel untested",
        "evidence": "test_phase6_hardening.py (only accept tested); kernel.py:214-231 (interactive branch)",
        "detail": (
            "test_phase6_hardening.py tests HITL review_decision with the 'accept' resolution only. "
            "The 'override' and 'skip' resolutions have no test. The kernel's interactive=True branch "
            "(kernel.py:214-231) is never exercised in tests. A mutation breaking the override or skip "
            "path would go undetected."
        ),
        "suggested_fix": (
            "Parametrize test_hitl_review_decision over ['accept', 'override', 'skip']. Add "
            "test_kernel_interactive_mode: construct TRAKernel(config, interactive=True), force an "
            "UNRECOVERABLE repair, mock stdin to provide each resolution, assert the target is updated "
            "correctly."
        ),
    },
    {
        "id": "TRA-033",
        "severity": "WARNING",
        "category": "Test Suite / LLM Seam",
        "track": "D",
        "title": "LLM seam degradation tested for RuntimeError only; other exception types untested",
        "evidence": "test_phase6_hardening.py:test_graceful_degradation_on_llm_failure",
        "detail": (
            "The graceful-degradation test supplies an llm_translate that raises RuntimeError. The "
            "catch at isa.py:316 is `except Exception` which covers all exception types, but only "
            "RuntimeError is tested. A mutation narrowing the catch to `except RuntimeError` would "
            "leave 102 of 103 tests green. Empty-string returns and None returns from llm_translate "
            "are also untested."
        ),
        "suggested_fix": (
            "Parametrize the test over [RuntimeError, ValueError, TypeError, OSError, "
            "KeyboardInterrupt]. Add tests for llm_translate returning '' and None."
        ),
    },
    {
        "id": "TRA-034",
        "severity": "INFO",
        "category": "Test Suite / Quality",
        "track": "D",
        "title": "conftest.py fixtures used only by test_phase0.py — 10 other test files ignore it",
        "evidence": "tests/conftest.py; grep for fixture usage",
        "detail": (
            "conftest.py defines 6 fixtures (sample_glossary, sample_entities, cache_context, "
            "evidence_registry, sample_evidence, config). Only test_phase0.py imports them. The other "
            "10 test files build fixtures inline, leading to duplication. Not a correctness issue but "
            "a maintainability one — fixture changes don't propagate."
        ),
        "suggested_fix": (
            "Refactor test_isa.py, test_kernel.py, test_validate.py, test_benchmark.py to use the "
            "shared fixtures. Add new fixtures for common patterns (e.g., a minimal source markdown, "
            "a fully-built RuntimeContext)."
        ),
    },
    {
        "id": "TRA-035",
        "severity": "INFO",
        "category": "Test Suite / Mutation Coverage",
        "track": "D",
        "title": "Invariant mutation catch rate: 5 of 12 scenarios (42%)",
        "evidence": "Track D mutation testing (4 invariants × 3 mutations)",
        "detail": (
            "Across the 4 critical invariants, 12 mutation scenarios were tested. 5 caught (42%): all "
            "3 mutations on Invariant 1 (canonical terminology), 2 of 3 on Invariant 2 (entity "
            "immutability at construction). 7 missed: 1 on Invariant 2 (post-construction mutation), "
            "3 on Invariant 3 (confidence_note reads in verify/repair/loop), 3 on Invariant 4 "
            "(repair-segment raise behavior). The test suite protects the data-model invariants well "
            "but the behavioral invariants poorly."
        ),
        "suggested_fix": (
            "Close the 3 BLOCKING gaps (TRA-028, TRA-029, TRA-030) to bring the catch rate from 42% "
            "to 100% on the critical invariants. Consider adding a CI mutation-testing step "
            "(mutmut or cosmic-ray) to prevent future regressions."
        ),
    },
]


# ---------------------------------------------------------------------------
# Aggregate stats
# ---------------------------------------------------------------------------

def stats() -> dict[str, int]:
    out = {"BLOCKING": 0, "WARNING": 0, "INFO": 0, "TOTAL": 0}
    for f in FINDINGS:
        out[f["severity"]] += 1
        out["TOTAL"] += 1
    return out


def by_track() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for f in FINDINGS:
        out.setdefault(f["track"], {"BLOCKING": 0, "WARNING": 0, "INFO": 0, "TOTAL": 0})
        out[f["track"]][f["severity"]] += 1
        out[f["track"]]["TOTAL"] += 1
    return out


def by_category() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for f in FINDINGS:
        cat = f["category"].split(" / ")[0]
        out.setdefault(cat, {"BLOCKING": 0, "WARNING": 0, "INFO": 0, "TOTAL": 0})
        out[cat][f["severity"]] += 1
        out[cat]["TOTAL"] += 1
    return out


if __name__ == "__main__":
    s = stats()
    print(f"Total findings: {s['TOTAL']}")
    print(f"  BLOCKING: {s['BLOCKING']}")
    print(f"  WARNING:  {s['WARNING']}")
    print(f"  INFO:     {s['INFO']}")
    print()
    print("By track:")
    for t, c in by_track().items():
        print(f"  Track {t}: {c['TOTAL']} total ({c['BLOCKING']}B/{c['WARNING']}W/{c['INFO']}I)")
    print()
    print("By category:")
    for c, n in by_category().items():
        print(f"  {c}: {n['TOTAL']} total ({n['BLOCKING']}B/{n['WARNING']}W/{n['INFO']}I)")
