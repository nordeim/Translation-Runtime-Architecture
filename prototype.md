> **Repo scope note:** Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is a **planning note for `tra-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only.

**Meticulous Plan for a Practical TRA Prototype**

I have reviewed the TRA specification thoroughly. Below is a **detailed, phased implementation plan** for a practical, minimal-yet-conformant prototype. The goal is a working **Python-based Translation Runtime Engine** (call it `tra-prototype`) that demonstrates the core invariants, Kernel lifecycle, ISA, Memory Model, Policy Engine, and L1–L3 conformance for ZH↔EN technical Markdown translation. It will be **human-in-the-loop friendly** and extensible.

### 1. High-Level Design Decisions (Grounded in Spec)
- **Language**: Python 3.11+ (easy prototyping, rich ecosystem for Markdown/LLMs).
- **Core Dependencies** (install via pip in sandbox):
  - `markdown` or `mistletoe` / `markdown-it-py` for structural parsing (structural map).
  - `pydantic` for strict data models (Runtime Context, diagnostics, etc.).
  - `ruamel.yaml` or `PyYAML` for config/artifacts.
  - Optional: Lite LLM wrapper (e.g., `litellm` or direct OpenAI/Anthropic) for `TRANSLATE_SEGMENT` (configurable; fallback to rule-based for demo).
- **Scope of Prototype**:
  - Full **Kernel state machine** (with Mermaid-like logging).
  - All **6 ISA instructions** with contracts enforced (preconditions, invariants, failures).
  - **Memory Model** + **Policy Engine** (priority stack arbitration).
  - **ZH-EN Module** integration.
  - **Diagnostics/Audit Trace** and basic repair.
  - **Conformance**: L2/L3 focus (glossary, entities, audit). L4 partial (traceable decisions).
  - Input: Markdown file or string. Output: Translated MD + `audit_trace.json` + artifacts.
  - Non-goals: Full production UI, massive scale, all languages/domains.
- **Invariants Strictly Enforced** (code-level assertions):
  - Canonical terms, entity immutability, surgical repairs, no self-scoring in VERIFY, priority stack.
- **Project Structure** (to be created):
  ```
  tra-prototype/
  ├── tra/
  │   ├── __init__.py
  │   ├── kernel.py          # State machine
  │   ├── memory.py          # Models for segments + RuntimeContext
  │   ├── isa.py             # Instruction implementations
  │   ├── policy.py          # Arbitration stack
  │   ├── modules/           # zh_en.py
  │   ├── diagnostics.py
  │   └── utils.py           # Markdown parsing, entity extraction
  ├── examples/              # test inputs/outputs
  ├── tests/                 # Benchmark subset + unit tests
  ├── tra_cli.py             # Entry point
  ├── config.yaml            # Bootstrap
  └── README.md
  ```

### 2. Phased Implementation Plan
#### Phase 0: Setup (1-2 hours)
- Initialize repo structure, `requirements.txt`, virtualenv.
- Define core Pydantic models:
  - `DocumentProfile`, `StructuralNode`, `GlossaryEntry`, `Entity`, `Diagnostic`, `RuntimeContext`.
  - `PolicyPriority` enum with the exact stack.
- Load ZH-EN module rules as data/classes.

#### Phase 1: Memory & Utils (Core Foundations)
- Markdown parser → `StructuralMap` (tree of headings, lists, tables, code blocks, etc.).
- Entity extractor (regex + heuristics for products, versions, CLI, APIs).
- Glossary builder (simple TF-IDF + module lookups + LLM-assisted for candidates).

#### Phase 2: ISA Instructions (One-by-One with Contracts)
Implement each as a class/method with:
- `__call__(inputs) -> outputs`
- Preconditions checks + exceptions.
- Invariant assertions post-execution.
1. `ANALYZE_DOCUMENT`
2. `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`
3. `TRANSLATE_SEGMENT` (segment-by-segment; use LLM with strict prompt including glossary/entities/style)
4. `VERIFY_OUTPUT` (diff-based + rule checks; evidence only)
5. `REPAIR_SEGMENT` (targeted fixes via rules or LLM)

#### Phase 3: Kernel & Policy Engine
- `TRAKernel` class with state enum and transition method.
- Policy resolver: Given conflicts, return winner + evidence.
- Full pipeline orchestration with logging to Audit Memory.

#### Phase 4: Modules, CLI, Artifacts & Testing
- Loadable modules.
- CLI: `tra translate input.md --lang zh-en --level L3 --output out.md`
- Export: `compilation_artifacts/`, `audit_trace.json`
- Tests: Run benchmark subset (S/F/T cases); assert zero BLOCKING for L3.
- Conformance self-audit.

#### Phase 5: Polish & Extensibility
- Error handling per spec exceptions.
- Human review hooks (e.g., pause on ambiguities).
- Logging/visualization of state machine.
- Documentation + example run.

**Timeline Estimate**: 2-4 days for a naive MVP, but see `review-feedback.md` §"关于时间线（2~4天）的现实性评估" — with the hardened scope (anchor mapping, evidence framework, deterministic cache, termination guards) the realistic estimate is **6-8 person-days** for a conformant MVP. Plan accordingly.

### 3. Key Challenges & Mitigations
- **LLM Reliability**: Use structured prompting + glossary injection + post-verify/repair loop. Temperature=0 where possible. Fallback rules for critical parts.
- **Structural Fidelity**: Preserve AST-like structure during translation (translate leaves, re-assemble).
- **Performance**: Segment-level processing; cache glossary.
- **Test Data**: Use/expand TRA-BENCHMARK-SUITE.md examples + real security advisories.
- **Edge Cases**: Ambiguities, broken MD, conflicting terms → logged as per spec.

### 4. Success Criteria for Prototype
- Passes L3 checklist on sample docs (explicit glossary, no BLOCKING errors, entities preserved, epistemic fidelity).
- Audit trace is human-readable and evidences every decision.
- Modular: Easy to swap LLM backend or add new language module.
- Runs end-to-end in < few seconds for typical README-sized input.

---

**Next Steps: Execute the Plan**
I am ready to **build this prototype in the sandbox** right now. I can:
1. Create the directory structure and core files.
2. Implement iteratively (starting with models + kernel skeleton).
3. Test with examples.

Would you like me to **start coding Phase 0/1 immediately** (and show progress), focus on a specific phase, generate the full prompt template for the TRANSLATE_SEGMENT, or adjust the plan (e.g., use a different language like TypeScript, or make it more LLM-orchestration focused without heavy parsing)? 

Provide any preferences (e.g., target LLM provider, sample input doc, or additional features) and I'll proceed meticulously. This will be a faithful, working embodiment of the TRA spec.