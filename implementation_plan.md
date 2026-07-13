TRA Prototype Implementation Plan 
 
> **Repo scope note:** Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is an **implementation plan for `tra-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only.

Executive Summary 
 
This plan builds a Python-based TRA conformant translation engine (tra-prototype) that implements the full TRA v1.0 specification: Kernel state machine, 6 ISA instructions, Memory Model, Policy Engine, ZH-EN Language Module, 
Evidence-based Audit Trail, Deterministic Cache, and Anchor Resolution — targeting L3 Strict conformance. 
 
Estimated Effort: 6-8 person-days (per review-feedback.md realistic assessment) 
 
---
 
Phase 0: Foundation & Architecture (Day 1) 
 
### 0.1 Project Setup 
 
- [x] 0.1.1 Initialize tra-prototype/ repo with pyproject.toml, requirements.txt, virtualenv 
- [x] 0.1.2 Configure linting (ruff), formatting (black), type checking (mypy strict), testing (pytest) 
- [x] 0.1.3 Create directory structure per prototype.md 
- [x] 0.1.4 Add config.yaml schema for tvm_bootstrap (language_pair, domain, conformance_level, model_endpoint, model_version) 
- [x] 0.1.5 Set up CLI entry point skeleton (tra_cli.py with translate, cache-clear, audit subcommands) 
 
### 0.2 Core Data Models (Pydantic v2) — Critical Path 
 
- [x] 0.2.1 Define PolicyPriority enum (6 levels: FACTUAL_INTEGRITY → TARGET_FLUENCY) 
- [x] 0.2.2 Define Severity enum (BLOCKING, WARNING, INFO) 
- [x] 0.2.3 Define DocumentProfile (type, register, intent, audience, evidence_style) — fields per TRA-ISA-REFERENCE.md §ANALYZE_DOCUMENT (evidence_style retained for spec fidelity even though TRA-SPECIFICATION.md §4 omits it) 
- [x] 0.2.4 Define StructuralNode & StructuralMap (AST representation: headings, lists, tables, code_blocks, links, anchors) 
- [x] 0.2.5 Define GlossaryEntry (source, target, status: canonical/context_sensitive, rule_id, confidence_note) 
- [x] 0.2.6 Define Entity (name, type: Product/API/CLI/Version/Acronym, mutable=false, context) 
- [x] 0.2.7 Define StyleProfile (voice, sentence_complexity, epistemic_mapping, punctuation_rules) 
- [x] 0.2.8 Define RuntimeContext (config, document_profile, glossary_cache, entity_table, style_profile, unresolved_ambiguities, execution_log) 
 
### 0.3 Evidence Schema (from EVIDENCE_SCHEMA.md) — Critical for L3 
 
- [x] 0.3.1 Define EvidenceType enum (TERM_MATCH, ENTITY_PRESERVED, POLICY_ARBITRATION, STRUCTURAL_MAPPING, LLM_DECISION, HUMAN_OVERRIDE, CONTEXTUAL_INFERENCE) 
- [x] 0.3.2 Define EvidenceRecord (id, type, rule_id, module, source_span, target_span, rationale, confidence_note) 
- [x] 0.3.3 Define AuditRecord (sequence_id, timestamp, isa_instruction, input_hash, artifact_snapshot, evidence_chain: list[EvidenceRecord.id], flags_raised) 
- [x] 0.3.4 Define Diagnostic (severity, subsystem, issue, evidence, action, repaired) 
- [x] 0.3.5 Implement EvidenceRegistry class (append-only store, JSONL serialization to audit_trace.jsonl) 
 
### 0.4 Deterministic Cache Foundation (from CACHE_STRATEGY.md) 
 
- [x] 0.4.1 Implement CacheKeyGenerator: 
    - Canonical JSON serialization with sorted keys 
    - Components: source_text, glossary_hash, entity_hash, model_endpoint, model_version, policy_stack_hash 
    - SHA-256 output 
- [x] 0.4.2 Implement TranslationCache class (diskcache/SQLite backend): 
    - get(key) -> TranslationResult | None 
    - set(key, result) -> None 
    - invalidate(pattern) -> None (CLI: tra cache-clear) 
    - No TTL (static facts) 
- [x] 0.4.3 Define TranslationResult (translation, evidence_chain, cache_hit: bool) 
 
---
 
Phase 1: Memory & Utilities — Structural Parsing (Day 1-2) 
 
### 1.1 Markdown AST Parser with Anchor Resolution (from ANCHOR_RESOLUTION.md) 
 
- [x] 1.1.1 Integrate markdown-it-py with custom token traversal 
- [x] 1.1.2 Implement StructuralMapBuilder: 
    - Walk AST, produce StructuralNode tree preserving hierarchy 
    - Extract all headings → build AnchorRegistry (original_text → slug → placeholder __HEADER_N__) 
    - Extract all internal links (href starting with #) → register for rewrite pass 
    - Identify code blocks (fenced/inline) → mark as "no-translate" zones 
- [x] 1.1.3 Implement AnchorRegistry: 
    - register_heading(text) -> placeholder 
    - resolve_slug(translated_text, existing_slugs) -> new_slug (GitHub slugify + duplicate handling -1, -2) 
    - rewrite_links(ast) -> ast (post-translation pass) 
 
### 1.2 Entity Extraction 
 
- [x] 1.2.1 Regex-based extractor for: product names (PascalCase/camelCase), versions (v?\d+.\d+.\d+), CLI commands, APIs, acronyms 
- [x] 1.2.2 Heuristic: preserve tokens matching entity patterns in EntityTable 
- [x] 1.2.3 Ambiguity handling: default to Entity (immutable) per ENTITY_AMBIGUITY exception
 
### 1.3 Glossary Builder 
 
- [ ] 1.3.1 Frequency analysis (TF-IDF on technical terms) 
- [x] 1.3.2 ZH-EN Module lookup for canonical mappings 
- [ ] 1.3.3 LLM-assisted candidate generation for unknown terms (prompt with context) 
- [x] 1.3.4 Conflict detection: same source term → multiple targets = GLOSSARY_CONFLICT exception 
 
---
 
Phase 2: ISA Instruction Implementations (Day 2-3) 
 
### 2.1 ANALYZE_DOCUMENT 
 
- [x] 2.1.1 Input: source_markdown, config 
- [x] 2.1.2 Output: DocumentProfile, StructuralMap 
- [x] 2.1.3 Invariant: node_count(StructuralMap) == node_count(source_AST) 
- [x] 2.1.4 Populate DocumentProfile (type detection: RFC/Advisory/Guide, register, intent) 
 
### 2.2 BUILD_GLOSSARY 
 
- [x] 2.2.1 Input: source, DocumentProfile, ZH-EN Module 
- [x] 2.2.2 Output: Glossary (list[GlossaryEntry]), ForbiddenMappings 
- [x] 2.2.3 Invariant: each recurring term → exactly one canonical mapping (unless context_sensitive) 
- [x] 2.2.4 Emit EvidenceRecord for each entry (TERM_MATCH, rule_id from module) 
 
### 2.3 BUILD_ENTITY_TABLE 
 
- [x] 2.3.1 Input: source, StructuralMap 
- [x] 2.3.2 Output: EntityTable 
- [x] 2.3.3 Invariant: all entities marked mutable=false 
- [x] 2.3.4 Emit EvidenceRecord (ENTITY_PRESERVED) 
 
### 2.4 TRANSLATE_SEGMENT — Core LLM Integration 
 
- [x] 2.4.1 Segment source by StructuralNode (leaf nodes: paragraphs, list items, table cells, headings) 
- [x] 2.4.2 For each segment: 
    - Apply AnchorRegistry placeholder protection (headings → __HEADER_N__) 
    - Build prompt with: source_segment, glossary_entries, entities, style_profile, ZH-EN rules 
    - Enforce structured LLM output: {"translation": "...", "decisions": [{"term": "...", "chosen": "...", "basis": "..."}], "structural_notes": "..."} 
    - Check cache first (CacheKeyGenerator); on hit, return cached result 
    - On miss, call LLM (litellm/OpenAI/Anthropic), validate output, store in cache 
    - Convert LLM decisions → EvidenceRecord chain (LLM_DECISION type) 
- [x] 2.4.3 Reassemble translated segments into target markdown using StructuralMap 
- [x] 2.4.4 Run AnchorRegistry rewrite_links pass 
- [x] 2.4.5 Output: target_markdown + per-segment evidence chains 
 
### 2.5 VERIFY_OUTPUT 
 
- [x] 2.5.1 Input: target_markdown, source_markdown, RuntimeContext 
- [x] 2.5.2 Checks (emit Diagnostic per violation): 
    - Structural: node count match, table row/col preservation, code block integrity, anchor resolution (S-06) 
    - Factual: numbers, units, versions exact match (F-01 to F-05) 
    - Terminology: glossary adherence (T-01 to T-05) 
    - Entity: all entities preserved verbatim 
    - Epistemic: certainty markers per ZH-EN lexicon (no strengthening/weakening) 
    - Evidence: every segment has non-empty evidence_chain; all rule_ids valid 
- [x] 2.5.3 Severity assignment per TRA-EXCEPTIONS table 
- [x] 2.5.4 Output: DiagnosticReport (list[Diagnostic]) 
 
### 2.6 REPAIR_SEGMENT 
 
- [x] 2.6.1 Input: target_segment, source_segment, Diagnostic (BLOCKING/WARNING) 
- [x] 2.6.2 Strategy per violation type: 
    - Structural: AST-based surgical fix (e.g., restore table row) 
    - Terminology: replace with glossary term 
    - Entity: restore entity from EntityTable 
    - Epistemic: revert to source certainty marker 
    - Factual: restore exact number/unit 
- [x] 2.6.3 LLM-assisted repair for complex cases (prompt with specific violation + context) 
- [x] 2.6.4 Invariant enforcement: re-verify repaired segment; must not introduce new BLOCKING 
- [x] 2.6.5 Max retries = 3 (configurable); on exhaustion → RAISE_FLAG for human-in-the-loop 
- [x] 2.6.6 Emit EvidenceRecord (HUMAN_OVERRIDE or POLICY_ARBITRATION) 
 
---
 
Phase 3: Kernel, Policy Engine & Orchestration (Day 3-4) 
 
### 3.1 TRA Kernel State Machine 
 
- [x] 3.1.1 Define KernelState enum (BOOTSTRAP → EMIT_PAYLOAD) 
- [x] 3.1.2 Implement TRAKernel class: 
    - transition(next_state) -> bool with precondition checks 
    - run(source_text) -> TranslationResult orchestrates full pipeline 
    - Execution logging to RuntimeContext.execution_log 
- [x] 3.1.3 State transition hooks (pre/post ISA execution) 
 
### 3.2 Policy Engine (Arbitration Stack) 
 
- [x] 3.2.1 Implement PolicyResolver: 
    - Input: conflicting requirements (e.g., fluency vs terminology) 
    - Process: compare PolicyPriority enum values 
    - Output: decision + EvidenceRecord (POLICY_ARBITRATION) 
- [x] 3.2.2 Scope-aware applicability (from review-feedback.md): 
    - Add scope_type to policy context (header_level, code_block_lang, list_nesting) to narrow *which segments* a rule applies to. 
    - **Scope never reorders the immutable stack** (Factual Integrity #1 > Structural Integrity #2 > Entity Preservation #3 > Terminological Consistency #4 > Epistemic Fidelity #5 > Target Fluency #6). 
    - In code blocks/comments: Factual and Entity binding always hold; Terminology preserved verbatim; Fluency is the only relaxable priority. 
    - In headings: Factual and Structural both bind — if a heading contains a number/version, Factual wins over any Structural preference.
 
### 3.3 Pipeline Orchestration 
 
- [x] 3.3.1 Wire ISA instructions in Kernel order: 
      BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS (GLOSSARY+ENTITY) → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED (loop) → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD 
- [x] 3.3.2 Implement VERIFY → REPAIR loop with max_retries=3 
- [x] 3.3.3 Aggregate all AuditRecord into audit_trace.jsonl 
- [x] 3.3.4 Export compilation_artifacts/ (glossary.yaml, entity_table.yaml, structural_map.json, style_profile.yaml) 
 
---
 
Phase 4: ZH-EN Language Module Integration (Day 4) 
 
### 4.1 Module Loader 
 
- [x] 4.1.1 Implement ModuleRegistry (pluggable: language, domain, formatting) 
- [x] 4.1.2 Load zh_en.py with rule implementations: 
 
### 4.2 ZH → EN Rules 
 
- [x] 4.2.1 Parataxis→Hypotaxis: subject insertion, conjunction insertion, topic-comment → subject-predicate 
- [x] 4.2.2 Nominalization verbalization: pattern matching + verb replacement map 
- [x] 4.2.3 Epistemic mapping: exact lexicon enforcement (成立→Confirmed, 高度可信→highly credible, etc.) 
- [x] 4.2.4 Information order preservation (evidence→conclusion for verification reports) 
 
### 4.3 EN → ZH Rules 
 
- [x] 4.3.1 Translationese avoidance: clause breaking, passive reduction 
- [x] 4.3.2 Four-character expressions (四字格) map 
- [x] 4.3.3 Punctuation: full-width/half-width rules with spacing 
- [x] 4.3.4 Entity preservation (official Chinese names where universally accepted) 
 
### 4.4 Module Interface 
 
- [x] 4.4.1 get_glossary_mappings() -> dict 
- [x] 4.4.2 get_style_profile() -> StyleProfile 
- [x] 4.4.3 apply_rules(source: str, direction: str) -> str (pre/post processing hooks) 
 
---
 
Phase 5: CLI, Artifacts & Testing (Day 5) 
 
### 5.1 CLI Commands 
 
- [x] 5.1.1 tra translate input.md --lang zh-en --level L3 --output out.md 
- [x] 5.1.2 tra cache-clear [--pattern] 
- [x] 5.1.3 tra audit audit_trace.jsonl --format summary|json 
- [x] 5.1.4 tra validate input.md out.md --level L3 (standalone verifier) 
 
### 5.2 Artifact Export 
 
- [x] 5.2.1 compilation_artifacts/glossary.yaml 
- [x] 5.2.2 compilation_artifacts/entity_table.yaml 
- [x] 5.2.3 compilation_artifacts/structural_map.json 
- [x] 5.2.4 compilation_artifacts/style_profile.yaml 
- [x] 5.2.5 audit_trace.jsonl (JSON Lines, one AuditRecord per line) 
 
### 5.3 Benchmark Test Suite (TRA-BENCHMARK-SUITE.md) 
 
- [x] 5.3.1 Create test fixtures for all S/F/T/D/E cases 
- [x] 5.3.2 Implement BenchmarkRunner: 
    - Load case, run pipeline, assert success criteria 
    - S-01 to S-06 (Structural), F-01 to F-05 (Factual), T-01 to T-05 (Terminology), D-01 to D-04 (Domain), E-01 to E-03 (Ambiguity) 
- [x] 5.3.3 L3 conformance gate: zero BLOCKING diagnostics on benchmark subset 
- [x] 5.3.4 Regression test: cache hit produces byte-identical output 
 
### 5.4 Example Runs 
 
- [x] 5.4.1 Create examples/security_advisory_zh.md (realistic input) 
- [x] 5.4.2 Document expected outputs for each conformance level 
- [x] 5.4.3 Add README with usage instructions 
 
---
 
Phase 6: Polish, Hardening & L4 Prep (Day 6-7) 
 
### 6.1 Exception Handling (TRA-EXCEPTIONS) 
 
- [x] 6.1.1 Implement all 5 exception types with recovery procedures 
- [x] 6.1.2 UNKNOWN_TERM: log Warning, preserve source, add to ambiguities 
- [x] 6.1.3 BROKEN_MARKDOWN: best-effort parse, Blocking if critical hierarchy lost 
- [x] 6.1.4 CERTAINTY_CONFLICT: prioritize Epistemic Fidelity (Priority 5) 
- [x] 6.1.5 ENTITY_AMBIGUITY: default to Entity (immutable) 
- [x] 6.1.6 GLOSSARY_CONFLICT: Blocking, first occurrence canonical 
 
### 6.2 Human-in-the-Loop Hooks 
 
- [x] 6.2.1 --interactive flag: pause on RAISE_FLAG, show violation + context, accept/edit/skip 
- [x] 6.2.2 Ambiguity review UI (CLI-based): show source, glossary options, let user pick 
 
### 6.3 Logging & Visualization 
 
- [ ] 6.3.1 Structured logging (structlog) with correlation IDs 
- [x] 6.3.2 State transition visualization (Mermaid diagram generation from execution_log) 
- [x] 6.3.3 Audit trace summary report (counts by severity, subsystem, instruction) 
 
### 6.4 L4 Forensic Enhancements (Partial) 
 
- [x] 6.4.1 Line-by-line evidence tracing (map each output line → EvidenceRecord chain) 
- [x] 6.4.2 Repair history: track all REPAIR attempts per segment 
- [x] 6.4.3 Ambiguity register: explicit log of all unresolved ambiguities 
 
### 6.5 Performance & Robustness 
 
- [ ] 6.5.1 Segment-level parallelism (asyncio for independent segments) 
- [ ] 6.5.2 Glossary/entity caching across runs 
- [x] 6.5.3 Input validation & sanitization 
- [x] 6.5.4 Graceful degradation: rule-based fallback when LLM unavailable 
 
---
 
Phase 7: Documentation & Delivery (Day 7-8) 
 
### 7.1 Documentation 
 
- [ ] 7.1.1 Architecture decision records (ADRs) for key choices 
- [ ] 7.1.2 API reference (pdoc/sphinx) 
- [ ] 7.1.3 Module authoring guide (how to add fr-en, security domain, etc.) 
- [ ] 7.1.4 Conformance self-audit checklist (auto-generated from code) 
 
### 7.2 Final Validation 
 
- [ ] 7.2.1 Run full benchmark suite, document results 
- [ ] 7.2.2 Verify L3 certification criteria met 
- [ ] 7.2.3 Cross-reference implementation against TRA-SPECIFICATION.md §1-9 
- [ ] 7.2.4 Verify all 4 review-feedback.md risks addressed 
 
---
 
File Structure Summary 
 
``` 
  tra-prototype/ 
  ├── pyproject.toml 
  ├── requirements.txt 
  ├── config.yaml                 # tvm_bootstrap schema 
  ├── tra_cli.py                  # CLI entry point 
  ├── tra/ 
  │   ├── __init__.py 
  │   ├── kernel.py               # TRAKernel, KernelState 
  │   ├── memory.py               # All Pydantic models (RuntimeContext, etc.) 
  │   ├── isa.py                  # 6 instruction implementations 
  │   ├── policy.py               # PolicyResolver, PolicyPriority 
  │   ├── diagnostics.py          # Diagnostic, EvidenceRegistry, AuditRecord 
  │   ├── cache.py                # CacheKeyGenerator, TranslationCache 
  │   ├── anchor.py               # AnchorRegistry, StructuralMapBuilder 
  │   ├── modules/ 
  │   │   ├── __init__.py 
  │   │   ├── registry.py         # ModuleRegistry 
  │   │   ├── zh_en.py            # ZH-EN Language Module 
  │   │   └── base.py             # Module base class 
  │   ├── utils.py                # Markdown parsing, entity extraction, slugify 
  │   └── exceptions.py           # TRAException subclasses 
  ├── examples/ 
  │   ├── security_advisory_zh.md 
  │   └── expected_outputs/ 
  ├── tests/ 
  │   ├── conftest.py 
  │   ├── test_isa.py 
  │   ├── test_kernel.py 
  │   ├── test_anchor.py 
  │   ├── test_benchmark.py 
  │   ├── test_modules.py 
  │   ├── test_phase0.py 
  │   ├── test_phase6_hardening.py 
  │   ├── test_recovery.py 
  │   ├── test_reporting.py 
  │   ├── test_utils.py 
  │   ├── test_validate.py 
  │   ├── test_outstanding_findings.py 
  │   └── benchmark/ 
  │       └── cases/              # S/F/T/D/E + R test fixtures (JSONL) 
  ├── compilation_artifacts/      # Generated at runtime 
  ├── audit_trace.jsonl           # Generated at runtime 
  └── README.md 
``` 
 
---
 
Dependencies 
 
┌───────────────────┬───────────────────────────────────┬─────────┐ 
│ Package           │ Purpose                           │ Version │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ pydantic          │ Data models, validation           │ ^2.8    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ pydantic-settings │ Config loading                    │ ^2.3    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ markdown-it-py    │ Markdown AST parsing              │ ^3.0    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ mdit_py_plugins   │ Extended syntax (footnotes, etc.) │ ^0.4    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ diskcache         │ Deterministic cache backend       │ ^5.6    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ litellm           │ Unified LLM interface             │ ^1.49   │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ pyyaml            │ Artifact serialization            │ ^6.0    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ structlog         │ Structured logging                │ ^24.1   │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ click             │ CLI framework                     │ ^8.1    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ rich              │ Terminal output                   │ ^13.7   │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ pytest            │ Testing                           │ ^8.2    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ pytest-asyncio    │ Async test support                │ ^0.23   │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ ruff              │ Linting                           │ ^0.5    │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ black             │ Formatting                        │ ^24.4   │ 
├───────────────────┼───────────────────────────────────┼─────────┤ 
│ mypy              │ Type checking                     │ ^1.10   │ 
└───────────────────┴───────────────────────────────────┴─────────┘ 
 
---
 
Risk Mitigation (from review-feedback.md) 
 
┌─────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────┐ 
│ Risk                            │ Mitigation in Plan                                                                         │ 
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ LLM non-determinism             │ Phase 0.4 Cache + Phase 2.4 cache-check-first; cache key includes policy_stack_hash        │ 
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ Anchor/cross-reference breakage │ Phase 1.1 AnchorRegistry + Phase 2.4 rewrite_links pass + S-06 test                        │ 
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ Evidence chain gaps             │ Phase 0.3 EvidenceSchema + Phase 2.4 structured LLM output + Phase 2.5 evidence validation │ 
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ Infinite repair loops           │ Phase 2.6 max_retries=3 + RAISE_FLAG for human-in-the-loop                                 │ 
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ Policy scope blindness          │ Phase 3.2 scope_type (header_level, code_block_lang)                                       │ 
├─────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ Timeline overrun                │ Phase 5 (polish) downgraded; core L3 features in Phases 0-4                                │ 
└─────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────┘ 
 
---
 
Validation Checkpoints 
 
┌────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────┐ 
│ Checkpoint     │ Criteria                                                                                                  │ 
├────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ End of Phase 1 │ StructuralMap round-trip: parse → serialize → parse = identical AST; AnchorRegistry resolves S-06 fixture │ 
├────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ End of Phase 2 │ All 6 ISA instructions pass unit tests with contract verification (preconditions, invariants, outputs)    │ 
├────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ End of Phase 3 │ Full pipeline runs on example doc; produces audit_trace.jsonl with evidence for every segment             │ 
├────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ End of Phase 5 │ Benchmark suite: 0 BLOCKING on L3 subset; cache hit = byte-identical output                               │ 
├────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
│ End of Phase 7 │ L3 Conformance Checklist (TRA-CONFORMANCE-GUIDE.md) fully satisfied                                       │ 
└────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────┘ 
 
---
 
Next Steps 
 
1. Confirm LLM provider (OpenAI/Anthropic/local) for TRANSLATE_SEGMENT prompt engineering 
2. Select sample input document (security advisory, architecture guide, or benchmark case) 
3. Begin Phase 0.1-0.4 — foundation models, evidence schema, cache key generator 
 
Would you like me to start implementing Phase 0 immediately (core models, evidence schema, cache foundation)

