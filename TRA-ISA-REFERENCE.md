# 1. TRA-ISA-REFERENCE.md
**Instruction Set Architecture Reference v1.0**

## Overview
The TRA-ISA defines the atomic operations that any compliant translation engine must execute. Each instruction is defined by a strict contract specifying its inputs, preconditions, outputs, invariants, and failure conditions. Engines must not skip instructions; they must transition through them sequentially as defined in `TRA-KERNEL`.

## Core Instructions

### `ANALYZE_DOCUMENT`
*   **Purpose:** Extracts macro-structural and semantic metadata from the source payload to initialize the Runtime Context.
*   **Inputs:** Source Document (Raw Markdown/Text), Immutable Config (`language_pair`, `domain`).
*   **Preconditions:** Source document is non-empty and syntactically valid Markdown (or plain text).
*   **Outputs:** 
    *   `document_profile`: `{ type, audience, register, intent, evidence_style }`
    *   `structural_map`: A hierarchical tree of all Markdown nodes (headings, lists, tables, code blocks).
*   **Invariants:** 
    *   The `structural_map` node count must exactly equal the source document's structural node count.
    *   No semantic content is altered during analysis.
*   **Failure Conditions:** 
    *   `MALFORMED_MARKDOWN`: Unable to parse heading levels or table structures.
    *   `EMPTY_SOURCE`: Source document contains no translatable content.

### `BUILD_GLOSSARY`
*   **Purpose:** Identifies domain-specific terminology and establishes canonical mappings to prevent drift.
*   **Inputs:** Source Document, `document_profile`, Active Domain Module.
*   **Preconditions:** `ANALYZE_DOCUMENT` has completed successfully.
*   **Outputs:** 
    *   `canonical_glossary`: List of `{ source_term, target_term, status: 'canonical' }`.
    *   `forbidden_mappings`: List of `{ source_term, forbidden_target, rationale }`.
*   **Invariants:** 
    *   Every recurring technical term (appearing >2 times) must have exactly one canonical mapping unless marked `context_sensitive`.
    *   Product names and entities are automatically added to `entity_table` with `mutable: false`.
*   **Failure Conditions:** 
    *   `CONFLICTING_MAPPINGS`: Two different canonical targets identified for the same source term in the same context.

### `BUILD_ENTITY_TABLE`
*   **Purpose:** Isolates immutable identifiers (code, APIs, products) from natural language.
*   **Inputs:** Source Document, Structural Map.
*   **Preconditions:** None.
*   **Outputs:** 
    *   `entity_table`: List of `{ name, type: ['product', 'api', 'cli', 'version'], mutable: false }`.
*   **Invariants:** 
    *   Entities are excluded from semantic translation processes.
    *   Original casing and punctuation are preserved exactly.
*   **Failure Conditions:** 
    *   `ENTITY_AMBIGUITY`: Cannot determine if a token is a natural language word or an entity (Default: Treat as Entity).

### `TRANSLATE_SEGMENT`
*   **Purpose:** Generates the target-language equivalent of a specific source segment (sentence, list item, or table cell).
*   **Inputs:** Source Segment, Runtime Context (`glossary`, `entity_table`, `style_profile`, `active_mode`).
*   **Preconditions:** Glossary and Entity Table are built.
*   **Outputs:** Target Segment.
*   **Invariants:** 
    *   All factual qualifiers, numbers, and epistemic markers of the Source Segment are preserved.
    *   Terminology matches `canonical_glossary` exactly.
    *   Entities from `entity_table` are inserted verbatim.
*   **Failure Conditions:** 
    *   `TERMINOLOGY_VIOLATION`: Generated term does not match glossary.
    *   `FACTUAL_DRIFT`: Numbers, units, or logical conditions are altered.
    *   `HALLUCINATION`: Information added that is not present in the source.

### `VERIFY_OUTPUT`
*   **Purpose:** Audits the translated document against the source and runtime constraints.
*   **Inputs:** Target Document, Source Document, Runtime Context.
*   **Preconditions:** Translation phase is complete.
*   **Outputs:** 
    *   `diagnostic_report`: List of `{ severity, subsystem, issue, evidence, action }`.
*   **Invariants:** 
    *   Verification must be exhaustive; it cannot skip sections.
    *   All violations must be categorized by severity (`BLOCKING`, `WARNING`, `INFO`).
*   **Failure Conditions:** None (Verification always completes, but may flag errors).

### `REPAIR_SEGMENT`
*   **Purpose:** Attempts to resolve specific diagnostic violations without re-translating the entire document.
*   **Inputs:** Target Segment, Source Segment, Diagnostic Violation.
*   **Preconditions:** A `BLOCKING` or `WARNING` violation has been identified.
*   **Outputs:** Repaired Target Segment.
*   **Invariants:** 
    *   Repair must resolve the specific violation without introducing new ones.
    *   Repair must not violate a higher-priority policy in the Arbitration Stack.
*   **Failure Conditions:** 
    *   `UNRECOVERABLE`: Resolution requires violating a higher-priority invariant (e.g., fixing fluency would break factual accuracy).
