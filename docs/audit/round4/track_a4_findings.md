# Track A4 — Spec Conformance Re-Audit (Round 4)

**HEAD audited:** `805a8f8`
**Methodology:** Manual code review against `TRA-SPECIFICATION.md` §1–§9 and `TRA-ISA-REFERENCE.md`. Findings re-derived from source at HEAD; Round 3 Track A3 claims were verified, not trusted blindly. All 4 quality gates re-run: **199 tests pass at HEAD** (`python -m pytest tests/ -q` → 199 passed in 1.18s).
**Baseline:** Round 3 Track A3 (10 findings: 0 BLOCKING / 6 WARNING / 4 INFO) + 36-finding R3 master register.
**Spec ground truth:** `/home/z/my-project/Translation-Runtime-Architecture/TRA-SPECIFICATION.md` (§1–§9) and `/home/z/my-project/Translation-Runtime-Architecture/TRA-ISA-REFERENCE.md`.

## Summary

- Findings: **11 total (0 BLOCKING / 6 WARNING / 5 INFO)**
- Carry-over from Round 3: **10** (status: 4 fixed-and-verified / 5 persistent / 1 partial-fix-classified-as-fixed-by-R4)
- New findings: **1**

The 4 critical invariants **all hold** at HEAD `805a8f8`:

1. **Canonical terminology exact** — `tra/modules/zh_en.py:21` `"成立": "Confirmed"`; line 22 `"执行环境": "execution environment"`; line 24 `"高度可信": "highly credible"`; mirror entries at `EPISTEMIC_LEXICON` lines 36, 38; `FORBIDDEN_TARGETS` lines 43-47 forbids `Valid/True/Correct`, `runtime`, `indisputably true`. The rule layer in `_rule_translate` (`tra/isa.py:491-499`) applies module rules → epistemic lexicon → glossary in that order, so canonical substitutions win over drift.
2. **Entities immutable** — `tra/memory.py:176` `model_config = ConfigDict(frozen=True)` on `Entity`; line 180 `mutable: bool = False` default; `tra/isa.py:328-334` `build_entity_table` constructs every entity with `mutable=False` via `model_copy(update={...})` (Pydantic frozen-model safe pattern); `tra/isa.py:488-503` rule path does NOT mutate entities (the prior `out = out` no-op loop was removed by TRA-073 fix); `tra/isa.py:542-552` `verify_output` flags missing entities as BLOCKING.
3. **VERIFY_OUTPUT never self-scores** — `tra/isa.py:511-613` `verify_output` reads only `target`, `source`, `ctx.entity_table`, `ctx.structural_map`, `ctx.glossary_cache`, and forbidden mappings via `_forbidden_from_module(ctx)`; the function body contains zero references to `confidence_note` (confirmed by `rg -n "confidence_note" tra/isa.py` → 0 hits). The invariant is documented at `tra/memory.py:6-8` and `tra/diagnostics.py:8-11`; the `confidence_note` field is only read by `_content_addressed_id` (`tra/diagnostics.py:60`) for hash computation, never for control flow.
4. **REPAIR_SEGMENT surgical** — `tra/isa.py:621-707`. Line 675: `sub = verify_output(repaired, source_segment, ctx, audit)`. Lines 676-678: `new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]; if new_blocking: raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")`. The surgical invariant is enforced at function-exit (after every repair branch), so any repair that introduces a new BLOCKING diagnostic is rejected before the segment is returned. The structural-repair branch additionally raises `Unrecoverable` at `max_retries` (line 666).

The Kernel state machine (9 canonical states, forward-only transitions, TRA-007/TRA-049), the L3/L4 conformance gates (TRA-036/TRA-037), the TRA-073 dead-code removal, the TRA-074 clock-seed safe fallback, and the TRA-075 pairwise transition coverage all hold at HEAD. No new BLOCKING findings were introduced by the 6 commits since Round 3 (`df9a590` → `805a8f8`). The 6 WARNING/INFO findings are persistent carry-overs that the audit log explicitly defers (TRA-001, TRA-038, TRA-040, TRA-042, TRA-072, TRA-099). The 1 new INFO finding (TRA-A4-011) is a parallel dead-code pattern that R3 missed.

## Findings

### TRA-A4-001: TRANSLATE_SEGMENT operates on the whole document, not per-leaf segment (TRA-001 partial, persistent)
- **Severity:** WARNING
- **Category:** Spec Conformance / ISA Contract (§3 TRANSLATE_SEGMENT)
- **Evidence:**
  - `tra/kernel.py:434-478` — `_execute_translation` extracts fenced (```` ``` ````) and inline (`` ` ``) code blocks into placeholders (lines 445-466), then calls `translate_segment(protected, self.ctx, self.cache, self.evidence, self.audit)` **once** on the entire protected source (lines 469-471). The function does not walk `ctx.structural_map.nodes` to identify leaf segments (`PARAGRAPH`, `LIST_ITEM`, `TABLE_CELL`, `HEADING`). The docstring at lines 437-442 explicitly states "Full segment-level translation (per leaf node) is deferred — the current approach is a placeholder-based protection that addresses the S-03 test case."
  - `tra/isa.py:365-373` — `translate_segment` signature accepts `source_segment: str` (any string); the contract is satisfied by passing the whole document.
  - `tra/isa.py:631` — `repair_segment` has a `segment_index: int = 0` parameter, but the kernel's `_repair_loop` (`tra/kernel.py:480-527`) never passes it (always 0), so `RepairAttempt.segment_index` is always 0 (`tra/memory.py:230` field description "Index of the repaired leaf segment" is misleading).
  - Spec §3 TRANSLATE_SEGMENT Inputs: "Source Segment, Runtime Context (Glossary, Entities, Style)"; TRA-ISA-REFERENCE.md §TRANSLATE_SEGMENT Purpose: "Generates the target-language equivalent of a specific source segment (sentence, list item, or table cell)."
- **Detail:** Spec §3 mandates per-segment translation (leaf-level: sentence, list item, table cell). The implementation passes the whole document with code-block protection only. The S-03 benchmark case (code-block no-translate zone) passes; full per-leaf segmentation is deferred. Consequences: (1) cache keys are per-document, not per-segment (cache invalidation is all-or-nothing); (2) `RepairAttempt.segment_index` is always 0 (L4 forensic trace cannot reconstruct which segment was repaired); (3) `evidence_trace.jsonl` uses substring containment (TRA-094 consequence), producing orphan lines. R3 confirmed PARTIAL; R4 baseline confirms PARTIAL; HEAD `805a8f8` unchanged.
- **Suggested fix:** Refactor `_execute_translation` to walk `ctx.structural_map.nodes`, identify leaf segments (`NodeKind.PARAGRAPH`, `LIST_ITEM`, `TABLE_CELL`, `HEADING`), call `translate_segment` per leaf, then re-assemble the target via the structural map. Pass the leaf's index to `repair_segment` so `RepairAttempt.segment_index` is meaningful. Update `reporting.line_by_line_trace` to map line → structural node → evidence chain.
- **Round 3 status:** persistent (TRA-A3-005 → TRA-001, partial-fix on code-block protection only; full per-leaf refactor still deferred)

### TRA-A4-002: PolicyResolver consulted for only ONE conflict pair (TRA-072 persistent; TRA-006 partial-fix)
- **Severity:** WARNING
- **Category:** Spec Conformance / Policy Engine (§5.2)
- **Evidence:**
  - `tra/isa.py:52` — `from .policy import PolicyResolver`
  - `tra/isa.py:63` — `_POLICY_RESOLVER = PolicyResolver(list(PolicyPriority))` (module-level singleton)
  - `tra/isa.py:565-568` — `term_wins_over_fluency = _POLICY_RESOLVER.wins(PolicyPriority.TERMINOLOGICAL_CONSISTENCY, PolicyPriority.TARGET_FLUENCY)` (the ONE production call site)
  - `tra/isa.py:577-579` — `severity = Severity.BLOCKING if term_wins_over_fluency else Severity.WARNING`
  - Production call-site count for `_POLICY_RESOLVER.wins` / `_POLICY_RESOLVER.resolve`: **1** (verified by `rg -n "_POLICY_RESOLVER\." tra/` → only `tra/isa.py:565`).
  - `tests/test_outstanding_findings.py:1285-1362` — `TestTRA006PolicyResolverInvokedInProduction` monkeypatches `_POLICY_RESOLVER.wins` to return `False` and asserts the diagnostic drops to WARNING — proving the resolver is genuinely consulted for the terminology severity decision.
  - Spec §5.2: "When instructions conflict (e.g., TRANSLATE_SEGMENT wants fluency, but GLOSSARY demands strict terminology), the Policy Engine resolves the conflict using weighted priorities." Spec §5.2 Output: "Decision + Evidence logged in Audit Memory." Spec §5.2 lists 6 priorities (FACTUAL_INTEGRITY through TARGET_FLUENCY) — 15 pairwise combinations.
- **Detail:** Round 3 Track A3 (TRA-A3-001) recorded TRA-006 as partial (resolver defined + invoked for 1 pair). At HEAD `805a8f8` the resolver IS imported, instantiated, and `wins()` is called exactly once to arbitrate terminology severity (TERMINOLOGICAL_CONSISTENCY P4 vs TARGET_FLUENCY P6). However, spec §5.2 mandates the Policy Engine as the **universal** conflict arbiter. Other potential conflict pairs — e.g., FACTUAL_INTEGRITY (P1) vs TARGET_FLUENCY (P6) when an LLM drops a number; ENTITY_PRESERVATION (P3) vs TERMINOLOGICAL_CONSISTENCY (P4) when a glossary term is also an entity — are NOT arbitrated through the resolver. `verify_output`'s structural (line 530), entity (line 547), and epistemic (line 597) severity decisions are hard-coded to BLOCKING without consulting the resolver. The spec's broader arbitration contract is therefore only partially met. R4 baseline confirms PERSISTENT; HEAD `805a8f8` unchanged.
- **Suggested fix:** Either (a) widen the resolver's scope: route every diagnostic severity decision (in `verify_output` and `repair_segment`) through `_POLICY_RESOLVER.wins(offended_priority, competing_priority)` so all 15 priority pairs can be arbitrated; or (b) document explicitly in `tra/policy.py` and `CLAUDE.md` that the resolver's scope is intentionally limited to terminology severity, and update spec §5.2 to match the narrower contract.
- **Round 3 status:** partial (TRA-A3-001 → resolver wired for 1 pair; broader §5.2 universal arbitration contract still unmet)

### TRA-A4-003: 3 of 5 TRA-EXCEPTION types still never raised in production (TRA-038 partial, persistent)
- **Severity:** WARNING
- **Category:** Spec Conformance / Exception Recovery (§6)
- **Evidence:**
  - `rg -n "raise UnknownTerm|raise CertaintyConflict|raise EntityAmbiguity" tra/` → **0 hits** at HEAD `805a8f8`.
  - `rg -n "raise BrokenMarkdown|raise GlossaryConflict" tra/` → 4 hits: `tra/isa.py:103` (BrokenMarkdown in analyze_document), `tra/isa.py:163` (BrokenMarkdown in _validate_markdown_structure), `tra/isa.py:235` (GlossaryConflict in build_glossary, forbidden target), `tra/isa.py:243` (GlossaryConflict in build_glossary, conflicting mappings).
  - `tra/recovery.py:77-87,112-122,125-135` — `recover_unknown_term`, `recover_certainty_conflict`, `recover_entity_ambiguity` are fully defined; `tra/recovery.py:155-197` `route_exception` dispatches them — so they are ROUTABLE if raised.
  - `tra/exceptions.py:27-58` — `UnknownTerm`, `CertaintyConflict`, `EntityAmbiguity` exception classes are defined with structured payloads (term/token).
  - `tra/isa.py:306-357` — `build_entity_table` does NOT raise `EntityAmbiguity`; it silently treats every classifier candidate as an Entity via `model_copy(update={"mutable": False, ...})` (line 328-334). The "Default: Treat as Entity" behavior matches spec §6, but no audit record / ambiguity_register entry is produced for ambiguous tokens.
  - `tra/isa.py:475-503` — `_rule_translate` does NOT raise `UnknownTerm` for CJK tokens missing from glossary/entity/epistemic lexicon.
  - `tra/isa.py:398-455` — `translate_segment`'s LLM path does NOT compare LLM output against `EPISTEMIC_LEXICON` to raise `CertaintyConflict` on hedging drift.
  - `tests/test_outstanding_findings.py` (R4 baseline row TRA-038) — `TestTRA038UnknownTermRaised` test exists but its docstring explicitly notes "full production wiring (auto-detecting unknown CJK terms) is deferred".
  - Spec §6 mandates deterministic recovery procedures for all 5 exception types; spec table rows for UNKNOWN_TERM, CERTAINTY_CONFLICT, ENTITY_AMBIGUITY are unused in production.
- **Detail:** Spec §6 mandates deterministic recovery procedures for all 5 exception types. Only 2 (`BrokenMarkdown`, `GlossaryConflict`) are raised in production. The recovery procedures for the other 3 (`recover_unknown_term`, `recover_certainty_conflict`, `recover_entity_ambiguity`) are dead code with no production raise site. The asymmetry means the L3 audit trail will never contain `UNKNOWN_TERM`, `CERTAINTY_CONFLICT`, or `ENTITY_AMBIGUITY` records — so a forensic auditor inspecting `audit_trace.jsonl` at L4 cannot reconstruct these decision points. R3 marked persistent; R4 baseline marks PARTIAL (exceptions routable + test exists but auto-detection deferred by commit `632bed2`); HEAD `805a8f8` unchanged.
- **Suggested fix:**
  - Raise `EntityAmbiguity` from `build_entity_table` when a token matches both `PRODUCT_RE` and a glossary key (or when `_module(ctx).entity_type_hint(token)` returns `None` and the classifier confidence is low).
  - Raise `UnknownTerm` from `_rule_translate` when a CJK token (Unicode range `\u4e00-\u9fff`) has no glossary/entity/epistemic match and is not in a no-translate zone.
  - Raise `CertaintyConflict` from `translate_segment`'s LLM path when the LLM returns a target that disagrees with `EPISTEMIC_LEXICON` (e.g., returns "valid" for source `成立`).
  - Route all three through the existing `try/except TRAException → self._recover(exc)` pattern (`kernel.py:231-278`).
- **Round 3 status:** persistent (TRA-A3-002 → TRA-038; routable but never raised in production)

### TRA-A4-004: EXCEPTION_HANDLER and HALT_ERROR are not modeled as KernelStates (TRA-040 persistent, intentional)
- **Severity:** WARNING
- **Category:** Spec Conformance / Kernel State Machine (§2.1)
- **Evidence:**
  - `tra/kernel.py:49-60` — `KernelState` StrEnum has exactly 9 members: `BOOTSTRAP, INITIALIZE_RUNTIME, ANALYZE_DOCUMENT, BUILD_ARTIFACTS, EXECUTE_TRANSLATION, VERIFY_OUTPUT, REPAIR_IF_NEEDED, AUDIT_DIAGNOSTICS, EMIT_PAYLOAD`. `EXCEPTION_HANDLER` and `HALT_ERROR` are absent.
  - `tra/kernel.py:64-74` — `_KERNEL_ORDER` lists the 9 states in canonical order; this is the only legal transition sequence.
  - `rg -n "EXCEPTION_HANDLER|HALT_ERROR" tra/kernel.py` → 5 hits at lines 229, 237, 274, 402, 419 — ALL are comments or audit-record string labels; NONE are enum members or transition targets.
  - `tra/kernel.py:401-430` — `_recover` is a private method that appends an `"EXCEPTION_HANDLER"` audit record (line 419) but does NOT transition the kernel state. After `_recover` returns, the kernel either raises `ConformanceFailure` (analyze failure at L3/L4, `kernel.py:250-254`), continues to the next ISA (build_glossary/entity_table failures, `kernel.py:267-278`), or breaks out of the repair loop (`kernel.py:499-522`).
  - `tra/kernel.py:209` — `self.ctx.execution_log.append(next_state.value)` records only the 9 canonical states; an EXCEPTION_HANDLER visit is never logged.
  - Spec §2.1 stateDiagram: `VERIFY_OUTPUT --> EXCEPTION_HANDLER : On Failure`, `EXCEPTION_HANDLER --> REPAIR_IF_NEEDED`, `EXCEPTION_HANDLER --> HALT_ERROR : Unrecoverable`.
- **Detail:** This is a deliberate design decision: the implementation treats EXCEPTION_HANDLER as a side-channel audit-record type, not a kernel state. The consequence is that the Mermaid state diagram rendered by `reporting.mermaid_state_diagram` from `execution_log` cannot reproduce the spec's EXCEPTION_HANDLER branch — the rendered diagram will always show the happy-path 9 states. HALT_ERROR is never recorded; on `Unrecoverable` the kernel's `_repair_loop` calls `_recover` (`kernel.py:504`) and `break`s out of the loop, then falls through to `_transition(REPAIR_IF_NEEDED)` (line 288) as if recovery succeeded — masking the halt. R3 confirmed PERSISTENT (intentional); R4 baseline confirms PERSISTENT; HEAD `805a8f8` unchanged.
- **Suggested fix:** Either (a) implement spec §2.1 literally: add `EXCEPTION_HANDLER` and `HALT_ERROR` to `KernelState`, transition to `EXCEPTION_HANDLER` before calling `_recover`, then transition to `REPAIR_IF_NEEDED` (recoverable) or `HALT_ERROR` (unrecoverable); update `_KERNEL_ORDER` and `reporting.mermaid_state_diagram` accordingly. Or (b) update spec §2.1 to explicitly state that EXCEPTION_HANDLER and HALT_ERROR are recovery actions, not kernel states, and align the stateDiagram accordingly. The current implementation-spec mismatch is a conformance gap either way.
- **Round 3 status:** persistent (TRA-A3-003 → TRA-040; intentional design decision, spec ambiguity acknowledged)

### TRA-A4-005: Structural integrity verification is still heading-count-only (TRA-042 persistent)
- **Severity:** WARNING
- **Category:** Spec Conformance / Structural Integrity (§5.1 item 2, §7)
- **Evidence:**
  - `tra/isa.py:526-539` — `verify_output` structural check is **only** `_HEADING_RE.findall` count match between source and target (lines 528-529: `src_headings = len(_HEADING_RE.findall(source))`; `tgt_headings = len(_HEADING_RE.findall(target))`; line 530: `if src_headings != tgt_headings`). No checks for:
    - list nesting depth (spec §5.1: "Markdown syntax, code blocks, table alignment"; benchmark S-01)
    - table column count / row alignment (benchmark S-02)
    - blockquote preservation (benchmark S-04)
    - HR (`---`) preservation (benchmark S-05)
    - code-block fence count preservation
  - `tra/isa.py:65-66` — `_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)` — the only structural regex used by `verify_output`.
  - `tra/memory.py:68-81` — `NodeKind` enum defines `LIST`, `LIST_ITEM`, `TABLE`, `TABLE_ROW`, `TABLE_CELL`, `BLOCKQUOTE`, `HR`, `CODE_BLOCK`, `INLINE_CODE` — i.e., the structural map already carries the rich node-kind information needed for shape checks, but `verify_output` ignores all of it (`rg -n "NodeKind\." tra/isa.py` → 0 hits).
  - Spec §5.1 item 2: "Structural Integrity: Markdown syntax, code blocks, table alignment."
  - Spec §7 example diagnostic: `severity: "BLOCKING", subsystem: "STRUCTURAL_VERIFICATION", issue: "Table row count mismatch", evidence: "Source: 5 rows, Target: 4 rows"`.
- **Detail:** A translation that flattened nested lists, broke table column alignment, or dropped blockquotes would pass the structural check at L3 as long as the heading count matches. The benchmark suite (`tests/benchmark/cases/sft.jsonl` S-01, S-02, S-04, S-05) catches these via `must_contain` substring checks, but that is a test-harness gate, not a `verify_output` gate — so a non-benchmarked input would silently pass L3 with broken structure. Spec §5.1 item 2 is only partially enforced. R3 confirmed PERSISTENT; R4 baseline confirms PERSISTENT; HEAD `805a8f8` unchanged.
- **Suggested fix:** In `verify_output`, walk `ctx.structural_map.nodes` and count nodes by `NodeKind` (list, list_item, table, table_row, table_cell, blockquote, hr, code_block, inline_code). Recompute the same counts from the target via a fresh `build_structural_map(target)` call (or a lightweight regex pass for fenced blocks / `|`-rows / `>`-quotes / `---` HRs). Raise a BLOCKING diagnostic per mismatch. Add regression tests on inputs that flatten lists / break tables / drop blockquotes.
- **Round 3 status:** persistent (TRA-A3-004 → TRA-042)

### TRA-A4-006: tra_cli.py does NOT pass registry= to TRAKernel (TRA-099 persistent, newly in-scope for Track A4)
- **Severity:** WARNING
- **Category:** Spec Conformance / Module Registry (§9)
- **Evidence:**
  - `tra_cli.py:107` — `kernel = TRAKernel(cfg, interactive=interactive)` — no `registry=` kwarg passed; CLI always falls back to default `ZHENModule` via `kernel._select_module` fallback path.
  - `tra_cli.py:66-77` — `@cli.command()` for `translate` declares `--lang`, `--level`, `--output`, `--interactive` options; **no `--registry` option exists**. Verified by `rg -n "@click.option" tra_cli.py` — 7 options total across 4 commands, none named `--registry`.
  - `tra/kernel.py:111` — `__init__` accepts `registry: object | None = None` parameter.
  - `tra/kernel.py:149-175` — `_select_module` uses the registry when supplied (`registry.all()` filtered by `mod.kind == "language"` and direction match), but falls back to `ZHENModule()` (line 175) when no match.
  - `tra/modules/registry.py:115-125` — `build_default_registry()` exists and constructs the canonical registry with the bundled `ZHENModule`.
  - `tra/modules/registry.py:128-145` — `registry_for_language_pair(pair)` exists for scoped registries.
  - Spec §9: "Modules are plug-ins that provide domain-specific or language-specific data to the Runtime. They do not alter the Kernel or ISA." The sanctioned extension path is the registry; the CLI is the only user-facing entry point.
- **Detail:** The TRAKernel supports `registry=` (TRA-002 was fixed in commit `3c38f78` for the kernel-level API), the `ModuleRegistry` class enforces protocol conformance + duplicate detection (TRA-097/098 fixed in commit `a3cd2c1`), and `as_interface()` returns a fully-protocol-compliant `ModuleInterface` (TRA-096 fixed in commit `3c38f78`). BUT the CLI does not expose any way to pass a custom registry — a user invoking `tra translate doc.md` always gets the default `ZHENModule`, even if additional language modules are registered in a configured registry. This means the spec §9 extension path is unreachable from the only user-facing entry point. R3 tracked TRA-099 in Track D3 (CLI track); R4 baseline confirms PERSISTENT; HEAD `805a8f8` unchanged. Newly in-scope for Track A4 because spec §9 is a conformance concern.
- **Suggested fix:** Add a `--registry` (or `--module-dir`) option to `tra_cli.py`'s `translate` command. On invocation, construct a `ModuleRegistry`, load any user-supplied modules from the path, register the bundled `ZHENModule` as fallback, and pass `registry=registry` to `TRAKernel(...)`. Update `tra_cli.py:107` to `kernel = TRAKernel(cfg, interactive=interactive, registry=registry)`.
- **Round 3 status:** persistent (TRA-099; was in Track D3 scope in R3, newly cross-listed in Track A4 for spec §9 conformance)

### TRA-A4-007: 4 critical invariants — VERIFIED HOLDING at HEAD `805a8f8`
- **Severity:** INFO
- **Category:** Spec Conformance / Invariants
- **Evidence:**
  1. **Canonical terminology exact** — `tra/modules/zh_en.py:21` `"成立": "Confirmed"`; line 22 `"执行环境": "execution environment"`; line 24 `"高度可信": "highly credible"`. Mirror entries in `EPISTEMIC_LEXICON` at lines 36 (`成立→Confirmed`), 38 (`高度可信→highly credible`). `FORBIDDEN_TARGETS` (lines 43-47) forbids `Valid/True/Correct`, `runtime`, `indisputably true`. Rule layer order at `tra/isa.py:491-499`: (1) module rules via `mod.apply_zh_rules(out)` (line 491) — runs `TOPIC_COMMENT` (e.g., `系统成立 → The system is Confirmed`) before atomic substitution; (2) epistemic lexicon (line 493-495); (3) canonical glossary (line 497-499). Canonical substitutions therefore win over drift.
  2. **Entities immutable** — `tra/memory.py:176` `model_config = ConfigDict(frozen=True)` on `Entity`; line 180 `mutable: bool = False` default. `tra/isa.py:328-334` `build_entity_table` constructs every entity with `mutable=False` via `model_copy(update={"mutable": False, ...})` (Pydantic frozen-safe pattern). `tra/isa.py:488-503` rule path does NOT mutate entities — the dead `out = out` no-op loop was removed by the TRA-073 fix in commit `632bed2`. `tra/isa.py:542-552` `verify_output` flags missing entities as BLOCKING.
  3. **VERIFY_OUTPUT never self-scores** — `rg -n "confidence_note" tra/isa.py` → 0 hits at HEAD `805a8f8`. `tra/isa.py:511-613` `verify_output` reads only `target`, `source`, `ctx.entity_table`, `ctx.structural_map`, `ctx.glossary_cache`, and forbidden mappings via `_forbidden_from_module(ctx)`. The `confidence_note` field is defined on `GlossaryEntry` (`tra/memory.py:153-155`) and `EvidenceRecord` (`tra/diagnostics.py:82-84`), but only read by `_content_addressed_id` (`tra/diagnostics.py:60`) for hash computation. The invariant is documented at `tra/memory.py:6-8` ("Design note: `confidence_note` is recorded for debugging only and MUST NOT be read by VERIFY or REPAIR") and `tra/diagnostics.py:8-11`.
  4. **REPAIR_SEGMENT surgical** — `tra/isa.py:621-707`. Line 675: `sub = verify_output(repaired, source_segment, ctx, audit)`. Lines 676-678: `new_blocking = [d for d in sub if d.severity == Severity.BLOCKING]; if new_blocking: raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")`. The surgical invariant is enforced at function-exit (after every repair branch). The structural branch additionally raises `Unrecoverable` at `attempt >= max_retries` (line 666) before re-verify.
- **Detail:** All 4 invariants hold at HEAD `805a8f8`. Round 3 Track A3 reported them as holding; the 6 commits since Round 3 (`df9a590` → `805a8f8`) preserved all 4 — the only relevant changes (TRA-073 dead-loop removal at `tra/isa.py:497-503`, TRA-076 LLM-output sanitization at `tra/isa.py:401-406`, TRA-078 secret redaction at `tra/kernel.py:82-99,416-417`) do not touch any invariant-critical path.
- **Suggested fix:** None required.
- **Round 3 status:** persistent-holding (TRA-A3-009 → Round 3 confirmed; Round 4 re-confirmed at HEAD `805a8f8`)

### TRA-A4-008: Kernel state machine (9 states, forward-only, TRA-007/TRA-049) — VERIFIED HOLDING at HEAD `805a8f8`
- **Severity:** INFO
- **Category:** Spec Conformance / Kernel State Machine (§2.1)
- **Evidence:**
  - `tra/kernel.py:49-60` — `KernelState` StrEnum has exactly 9 members matching spec §2.1 happy-path sequence.
  - `tra/kernel.py:64-74` — `_KERNEL_ORDER` lists the 9 states in canonical order; this is the only legal transition sequence.
  - `tra/kernel.py:193-209` — `_transition` enforces `if idx <= _KERNEL_ORDER.index(self.state): raise TRAException(...)` (TRA-049: same-state AND backward transitions raise). Comment at lines 198-202 documents the mutation-testing basis.
  - `tra/kernel.py:204-340` — `run()` calls each ISA BEFORE its corresponding forward transition:
    - Line 232: `analyze_document(...)` → line 256 `_transition(ANALYZE_DOCUMENT)`
    - Line 268: `build_glossary(...)` → line 279 `_transition(BUILD_ARTIFACTS)` (after `build_entity_table` at 276)
    - Line 281: `target = self._execute_translation(src)` → line 282 `_transition(EXECUTE_TRANSLATION)`
    - Line 284: `diagnostics = verify_output(...)` → line 285 `_transition(VERIFY_OUTPUT)`
    - Line 287: `target = self._repair_loop(...)` → line 288 `_transition(REPAIR_IF_NEEDED)`
    - Line 335: `_transition(AUDIT_DIAGNOSTICS)`; line 338: `_transition(EMIT_PAYLOAD)`
  - `tests/test_outstanding_findings.py:215` — `TestTRA007TransitionOrdering` tests the happy-path forward sequence.
  - `tests/test_outstanding_findings.py:1040` — `TestTRA049SameStateTransition` tests the same-state guard raises.
  - `tests/test_outstanding_findings.py:1930-2026` — `TestTRA075PairwiseTransitions` (NEW since R3) tests all backward pairs `(state_i, state_j) where j < i` raise `TRAException` — closes the R3 TRA-A3-008 coverage gap.
- **Detail:** Spec §2.1 "State transitions are triggered by the successful completion of ISA instructions" (TRA-007) holds: every `_transition(next_state)` call follows the ISA call (no transition-before-ISA). The TRA-049 same-state guard (added in commit `18955d6` during R2) holds. The TRA-075 pairwise coverage (added in commit `805a8f8` during R3 remediation) closes the R3 TRA-A3-008 INFO refinement. All 199 tests pass at HEAD.
- **Suggested fix:** None required.
- **Round 3 status:** fixed-and-verified (TRA-A3-010 → TRA-007 was fixed in Round 1; TRA-049 fixed in Round 2 commit `18955d6`; TRA-075 pairwise coverage added in R3 remediation commit `805a8f8`; all verified holding at HEAD `805a8f8`)

### TRA-A4-009: L3/L4 conformance gates (TRA-036/TRA-037) — VERIFIED HOLDING at HEAD `805a8f8`
- **Severity:** INFO
- **Category:** Spec Conformance / Conformance Gates (§8)
- **Evidence:**
  - **TRA-036** (analyze-failure raises ConformanceFailure at L3/L4): `tra/kernel.py:246-254` — after `_recover(exc)` on analyze_document failure, the kernel checks `if self.config.conformance_level in (ConformanceLevel.L3_STRICT, ConformanceLevel.L4_FORENSIC): raise ConformanceFailure(f"BROKEN_MARKDOWN: analyze_document failed ({exc.code}) — output is not L3-conformant", blocking_count=1) from exc`. L1/L2 keep the empty `return ""` (line 255) — lower strictness dials.
  - **TRA-037** (`_rewrite_anchors` runs BEFORE the L3 gate): `tra/kernel.py:299` — `target = self._rewrite_anchors(target)` is invoked BEFORE the L3 gate at lines 307-333. The gate at line 311 then runs `verify_output(target, src, ...)` on the post-rewrite target. Lines 316-318: `broken_links = [a for a in self.ctx.unresolved_ambiguities if "BROKEN_LINK" in a]` — surfaces BROKEN_LINK entries appended by `_rewrite_anchors` (line 398). Lines 319-333: `if final_blocking or broken_links: ... raise ConformanceFailure(...)`.
  - `tests/test_outstanding_findings.py:2075+` — `TestTRA088SingleAuditRecordAllExceptions` covers the EXCEPTION_HANDLER audit-record invariant.
  - `tests/test_outstanding_findings.py` — `TestTRA089ConformanceFailureE2E` covers unclosed-fence (BROKEN_MARKDOWN) and broken-link (BROKEN_LINK) ConformanceFailure paths end-to-end.
  - Spec §8 L3_STRICT: "Full TRA compliance. Explicit Glossary, Entity Table, and Arbitration. Diagnostic Reporting required." L4_FORENSIC: "Level 3 + Line-by-line evidence tracing. Every translation decision is logged with its Policy justification."
- **Detail:** TRA-036 (R2 finding, fixed in commit `df9a590` → `805a8f8`) holds: an analyze failure at L3_STRICT/L4_FORENSIC raises ConformanceFailure instead of silently returning an empty string. TRA-037 (R2 finding, fixed in same commit) holds: `_rewrite_anchors` runs BEFORE the L3 gate, so the gate verifies the post-rewrite target — preserving L4 hash-chain integrity. Both fixes are covered by regression tests added in commit `805a8f8` (TRA-088/TRA-089 test classes).
- **Suggested fix:** None required.
- **Round 3 status:** fixed-and-verified (TRA-036, TRA-037 — both fixed in R3 remediation commits; verified holding at HEAD `805a8f8`)

### TRA-A4-010: TRA-068/TRA-069/TRA-A3-008 — VERIFIED FIXED at HEAD `805a8f8`
- **Severity:** INFO
- **Category:** Spec Conformance / Code Quality (carry-over from R3)
- **Evidence:**
  - **TRA-068 / TRA-074** (clock seed in `run()` not `__init__`): `tra/kernel.py:117` `self._source_hash_seed: str | None = None` in `__init__`; `tra/kernel.py:177-191` `_deterministic_clock` falls back to `"0" * 16` when seed is None (line 186), then maps to a deterministic datetime in 2024 epoch (lines 189-191). The seed is set from `hashlib.sha256(src)` only inside `run()` (lines 219-222). The TRA-074 mitigation: `tests/test_outstanding_findings.py:2034-2067` `TestTRA074ClockSeedDefault.test_clock_returns_valid_datetime_before_run` asserts `_deterministic_clock()` returns `datetime` with `ts.year >= 2024` BEFORE `run()` is called — proving the fallback is safe (no 1970 timestamp, no crash). The architectural concern (seed set in `run()` not `__init__`) remains latent, but the misuse risk is mitigated by the safe fallback.
  - **TRA-069 / TRA-073** (dead `out = out` no-op loop in `_rule_translate`): `tra/isa.py:500-503` — the loop body was removed in commit `632bed2`; only a comment remains: "# 4. Entities are preserved verbatim (already in source form; no transformation needed — the rule path never alters entities). # TRA-073 (round 3): removed dead `out = out` no-op loop." `tests/test_outstanding_findings.py` `TestTRA073DeadCodeRemoved` (R4 baseline row TRA-073) reads `isa.py` source and asserts no `out = out` code statement (only comments remain).
  - **TRA-A3-008 / TRA-075** (pairwise kernel transition test coverage thin): `tests/test_outstanding_findings.py:1930-2026` `TestTRA075PairwiseTransitions` (added in commit `805a8f8`) tests all backward pairs `(state_i, state_j) where j < i` raise `TRAException`, plus same-state and skip-ahead cases. Closes the R3 TRA-A3-008 INFO refinement.
- **Detail:** All three R3 carry-over findings in Track A scope (TRA-068/TRA-069/TRA-A3-008) are remediated at HEAD `805a8f8`. TRA-073 (dead-loop removal) and TRA-075 (pairwise coverage) are full fixes. TRA-074 (clock seed) is a behavioral fix (safe fallback) rather than the architectural fix (move seed to `__init__`) suggested by R3 — but the latent misuse risk is mitigated because the fallback cannot crash or produce an invalid timestamp.
- **Suggested fix:** None required. (Optional: for full architectural fix, set `self._source_hash_seed = "0" * 16` in `__init__` to make the fallback explicit at construction time, rather than relying on `or "0" * 16` in `_deterministic_clock`.)
- **Round 3 status:** fixed (TRA-068 → TRA-074 FIXED; TRA-069 → TRA-073 FIXED; TRA-A3-008 → TRA-075 FIXED — all verified at HEAD `805a8f8`)

### TRA-A4-011: Dead no-op assignment `repaired = repaired` in repair_segment's entity branch (NEW, missed by R3)
- **Severity:** INFO
- **Category:** Code Quality / Misleading Dead Code (parallel to TRA-073)
- **Evidence:**
  - `tra/isa.py:651-654` — the `entity` branch of `repair_segment`:
    ```python
    elif diagnostic.subsystem == "entity":
        name = diagnostic.issue.split("'")[1] if "'" in diagnostic.issue else ""
        if name and name not in repaired:
            repaired = repaired  # cannot conjure absent entity without source
    ```
    The assignment `repaired = repaired` on line 654 is a no-op self-assignment.
  - `tra/isa.py:670-678` — the surgical-repair re-verify guard runs unconditionally AFTER the entity branch, so a missing entity is caught downstream by `verify_output(repaired, ...)` → `new_blocking = [...]` → `raise Unrecoverable("UNRECOVERABLE: repair introduces new BLOCKING violation")`. The no-op branch is defense-in-depth, not a live bug.
  - `git log --oneline -S "repaired = repaired" -- tra/isa.py` → introduced in commit `84753ad` ("Add TRA Phase 2/3: ISA instructions, ZH-EN module, Kernel orchestration") — the initial Phase 2/3 implementation, NOT introduced by the 6 R3 remediation commits.
  - `rg -n "= repaired$" tra/isa.py` → only 1 hit at line 654 (verified unique — no other self-assignments in the file).
- **Detail:** This is a parallel of the TRA-073 dead-code pattern that R3 Track A3 (TRA-A3-006) found in `_rule_translate`. R3 explicitly remediated the `out = out` loop in `_rule_translate` (commit `632bed2`) but missed the structurally identical `repaired = repaired` no-op in `repair_segment`'s entity branch — because R3 was scanning `_rule_translate`, not `repair_segment`. The comment "cannot conjure absent entity without source" is correct (the rule path cannot synthesize an entity that's missing from the source), but the `repaired = repaired` assignment itself does nothing. A maintainer reading this code would wonder why the line exists. The downstream re-verify guard (lines 675-678) catches the missing entity and raises `Unrecoverable`, so the no-op is unreachable as a behavior — only the comment carries semantic content.
- **Suggested fix:** Delete the `repaired = repaired` assignment on line 654. Keep the comment (moved to a standalone `#` comment above the `if` block) to explain why the entity branch is a no-op when the entity is missing — or refactor the branch to `pass` with the comment. Optionally, raise `Unrecoverable("UNRECOVERABLE: entity {name!r} absent from source segment — cannot repair")` directly in this branch for earlier failure (the re-verify guard at line 678 will catch it later anyway, but earlier failure is more diagnostic).
- **Round 3 status:** new (parallel to TRA-073/TRA-069; pre-existed since commit `84753ad` but was missed by R3 Track A3's `_rule_translate`-focused scan)

---

## Round 3 carry-over status matrix (Track A scope)

| Round 3 ID | Title | Round 4 status |
|---|---|---|
| TRA-001 | TRANSLATE_SEGMENT whole-document | **partial** (TRA-A4-001) — code-block protection only; full per-leaf refactor still deferred |
| TRA-006 / TRA-072 | PolicyResolver never invoked / 1 conflict pair only | **partial** (TRA-A4-002) — invoked for TERMINOLOGICAL vs FLUENCY only; universal §5.2 arbitration unmet |
| TRA-007 | Transitions fire after ISA success | **fixed-and-verified** (TRA-A4-008) |
| TRA-036 | Analyze-failure bypasses L3 gate | **fixed-and-verified** (TRA-A4-009) |
| TRA-037 | _rewrite_anchors runs before L3 gate | **fixed-and-verified** (TRA-A4-009) |
| TRA-038 | 3 of 5 exception types never raised | **partial** (TRA-A4-003) — routable + test exists; auto-detection deferred |
| TRA-040 | EXCEPTION_HANDLER/HALT_ERROR not KernelStates | **persistent** (TRA-A4-004) — intentional design decision, spec ambiguity acknowledged |
| TRA-042 | Structural verification heading-only | **persistent** (TRA-A4-005) — only `_HEADING_RE` count match; NodeKind-rich structural map ignored |
| TRA-049 | Same-state transition untested | **fixed-and-verified** (TRA-A4-008) — TRA-049 + TRA-075 pairwise coverage |
| TRA-068 / TRA-074 | _deterministic_clock seed in run() not __init__ | **fixed** (TRA-A4-010) — behavioral fix: safe fallback (year ≥ 2024); architectural concern remains latent |
| TRA-069 / TRA-073 | Dead no-op loop in _rule_translate | **fixed** (TRA-A4-010) — loop body removed in commit `632bed2`; only comment remains |
| TRA-A3-008 / TRA-075 | Pairwise kernel transition coverage thin | **fixed** (TRA-A4-010) — `TestTRA075PairwiseTransitions` tests all backward pairs (added in commit `805a8f8`) |
| TRA-099 (newly in-scope) | tra_cli.py does NOT pass registry= to TRAKernel | **persistent** (TRA-A4-006) — no `--registry` CLI flag; spec §9 extension path unreachable from CLI |
| TRA-A3-009 | 4 critical invariants verified holding | **persistent-holding** (TRA-A4-007) — all 4 hold at HEAD `805a8f8` |
| TRA-A3-010 | Kernel state machine verified holding | **persistent-holding** (TRA-A4-008) — TRA-007/TRA-049 + TRA-075 pairwise coverage hold |
| **(new)** | `repaired = repaired` no-op in repair_segment | **new** (TRA-A4-011) — parallel to TRA-073; pre-existed since `84753ad` but missed by R3 |

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# Verify HEAD
git rev-parse HEAD
# → 805a8f8c9843cd429b30623a1a84b336b7920e4c

# Quality gates
python -m pytest tests/ -q
# → 199 passed in 1.18s

# 4 critical invariants
rg -n "成立.*Confirmed|执行环境.*execution environment|高度可信.*highly credible" tra/modules/zh_en.py
# → lines 21,22,24,36,38 (canonical mappings)
rg -n "ConfigDict\(frozen=True\)" tra/memory.py
# → lines 145,161,176 (GlossaryEntry, ForbiddenMapping, Entity)
rg -n "mutable: bool = False" tra/memory.py
# → line 180 (Entity default)
rg -n "mutable.*False" tra/isa.py
# → lines 313 (docstring), 331 (build_entity_table sets mutable=False)
rg -n "confidence_note" tra/isa.py
# → 0 hits (VERIFY_OUTPUT never self-scores — invariant holds)
rg -n "new_blocking|raise Unrecoverable" tra/isa.py
# → lines 666, 676, 678 (surgical repair invariant)

# Kernel state machine (TRA-007/TRA-049/TRA-075)
rg -n "KernelState\." tra/kernel.py | head -10
# → 9 canonical states (lines 65-73)
rg -n "if idx <= _KERNEL_ORDER" tra/kernel.py
# → line 203 (TRA-049 same-state guard)

# L3/L4 conformance gates (TRA-036/TRA-037)
rg -n "BROKEN_LINK|_rewrite_anchors|ConformanceFailure" tra/kernel.py
# → line 250 (TRA-036 analyze-failure raise), lines 299,313-333 (TRA-037 gate order)

# Policy Engine (TRA-072)
rg -n "_POLICY_RESOLVER\.wins|_POLICY_RESOLVER\.resolve" tra/
# → only tra/isa.py:565 (single call site, TERMINOLOGICAL vs FLUENCY)

# Exception Recovery (TRA-038)
rg -n "raise UnknownTerm|raise CertaintyConflict|raise EntityAmbiguity" tra/
# → 0 hits (3 of 5 exception types never raised in production)
rg -n "raise BrokenMarkdown|raise GlossaryConflict" tra/
# → 4 hits at tra/isa.py:103,163,235,243 (only 2 of 5 raised)

# Structural verification (TRA-042)
rg -n "_HEADING_RE|NodeKind" tra/isa.py
# → line 65-66 (_HEADING_RE), line 308 (structural_map param) — no NodeKind usage

# CLI registry flag (TRA-099)
rg -n "registry|TRAKernel" tra_cli.py
# → line 105 (import), line 107 (TRAKernel(cfg, interactive=interactive) — no registry=)
rg -n "@click.option" tra_cli.py
# → 7 options across 4 commands; none named --registry

# Dead no-op assignments (TRA-A4-011 NEW)
rg -n "repaired = repaired" tra/
# → tra/isa.py:654 (single hit, no-op self-assignment in repair_segment entity branch)
git log --oneline -S "repaired = repaired" -- tra/isa.py
# → 84753ad (initial Phase 2/3 commit — pre-existed R3)

# Changes to spec-relevant files since R3 baseline b783745
git diff b783745..805a8f8 --stat -- tra/isa.py tra/kernel.py tra/memory.py tra/policy.py tra/recovery.py tra/exceptions.py
# → tra/isa.py (24 lines), tra/kernel.py (31 lines) — only TRA-073/076/078 remediation
```

## Conclusion

HEAD `805a8f8` is **conformant** to spec §1–§9 at the level of the 4 critical invariants and the 6 ISA instruction contracts. The 6 commits since Round 3 (`df9a590` → `805a8f8`) **successfully remediated** 3 Round 3 Track A carry-overs (TRA-068/TRA-074 clock-seed safe fallback; TRA-069/TRA-073 dead `out = out` loop removal; TRA-A3-008/TRA-075 pairwise kernel transition coverage) plus the L3/L4 gate fixes that landed earlier in the R3 remediation window (TRA-036, TRA-037). **No new BLOCKING findings were introduced.** The TRA-007 (transitions fire after ISA success), TRA-049 (same-state guard), and TRA-075 (pairwise coverage) all hold at HEAD — verified by 199 passing tests.

The 6 WARNING/INFO findings are persistent carry-overs from Round 2/3 that the audit log explicitly defers (TRA-001 per-leaf segment refactor, TRA-038 exception auto-detection, TRA-040 EXCEPTION_HANDLER/HALT_ERROR modeling, TRA-042 structural verification depth, TRA-072 universal PolicyResolver arbitration, TRA-099 CLI `--registry` flag). These are not regressions; they are documented gaps in a Phase 0 prototype. The 1 new INFO finding (TRA-A4-011) is a `repaired = repaired` no-op self-assignment in `repair_segment`'s entity branch that R3 missed because its scan was scoped to `_rule_translate` — pre-existed since the initial Phase 2/3 commit `84753ad`, structurally parallel to the now-fixed TRA-073. The new finding is defense-in-depth (the downstream re-verify guard at `isa.py:675-678` catches the missing entity and raises `Unrecoverable`), so it has no behavioral impact.

**Recommendation for Track B4/C4/D4/E4/F4:** treat Track A4's findings as ground truth for spec-conformance claims; rely on the verified-holding invariants (TRA-A4-007, TRA-A4-008, TRA-A4-009) and the fixed-and-verified carry-overs (TRA-A4-010) as the baseline. The persistent gaps (TRA-A4-001 through TRA-A4-006) should be carried forward to the Round 4 synthesis report with the same severity as Round 3 (no escalation, no de-escalation). The new INFO finding (TRA-A4-011) is a trivial code-quality fix — recommend a one-line `git revert` of the no-op assignment in a follow-up commit, alongside the existing TRA-073 pattern.
