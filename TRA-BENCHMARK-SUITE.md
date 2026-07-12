# 3. TRA-BENCHMARK-SUITE.md
**Standardized Evaluation Suite v1.0**

## Overview
This suite defines representative test categories (Structural, Factual, Terminology, Domain, Ambiguity) with concrete seed cases to validate TRA conformance. It is seeded with the cases below and intended to grow toward 100+ cases; engines must pass the relevant cases (per their conformance level) to achieve L3/L4 certification.

## Category 1: Structural Integrity (Markdown & Formatting)
| ID | Test Case | Success Criteria |
| :--- | :--- | :--- |
| S-01 | Nested Lists (3 levels) | Exact nesting depth preserved; bullet markers consistent. |
| S-02 | Complex Tables (Merged cells) | Column alignment preserved; no raw line breaks in cells. |
| S-03 | Inline Code vs. Prose | Backticks preserved; content inside backticks untranslated. |
| S-04 | Blockquotes within Lists | `>` syntax preserved at correct indentation level. |
| S-05 | Horizontal Rules as Dividers | `---` preserved exactly; not converted to headings. |
| S-06 | Internal Anchors & Cross-References | Heading translation updates the target slug (e.g., `# System Setup` → `# 系统安装` rewrites `[link](#system-setup)` → new slug). Links must resolve post-translation; broken links flagged as `WARNING`. Code-block-internal links are not rewritten. |

## Category 2: Factual & Numerical Precision
| ID | Test Case | Success Criteria |
| :--- | :--- | :--- |
| F-01 | Latency Metrics (`<60ms`) | Exact string `<60ms` preserved; not rounded or expanded. |
| F-02 | Version Strings (`v0.5.0`) | Exact version string preserved; casing intact. |
| F-03 | Statistical Percentiles (`P99`) | `P99` preserved; not translated to "99th percentile". |
| F-04 | Memory Ranges (`<5MB`) | Inequality symbol and unit preserved exactly. |
| F-05 | Hardware Specs (`96-core`) | Hyphenated spec preserved; not split or rephrased. |

## Category 3: Terminology & Entity Consistency
| ID | Test Case | Success Criteria |
| :--- | :--- | :--- |
| T-01 | Product Names (`RustVMM`) | Untranslated; original casing preserved. |
| T-02 | Technical Terms (`执行环境`) | Mapped to `execution environment` consistently; never `runtime`. |
| T-03 | CLI Commands (`install.sh`) | Untranslated; file extension preserved. |
| T-04 | Acronyms (`KVM`, `XFS`) | Untranslated; no invented expansions. |
| T-05 | Epistemic Labels (`成立`) | Mapped to `Confirmed` consistently; never `Valid` or `True`. |

## Category 4: Domain-Specific Register
| ID | Test Case | Success Criteria |
| :--- | :--- | :--- |
| D-01 | Security Advisory (Urgent) | Tone is authoritative; "must" used for requirements. |
| D-02 | RFC (Formal) | Passive voice used where appropriate; objective tone. |
| D-03 | README (Instructional) | Imperative mood used for steps; welcoming but professional. |
| D-04 | Academic Paper (Hedging) | "May", "suggests" preserved; not strengthened to "proves". |

## Category 5: Ambiguity & Edge Cases
| ID | Test Case | Success Criteria |
| :--- | :--- | :--- |
| E-01 | Intentional Ambiguity | Ambiguity preserved in target; not resolved by guesswork. |
| E-02 | Mixed Language Paragraphs | English entities retained; Chinese prose translated naturally. |
| E-03 | Broken Source Markdown | Best-effort preservation; error logged in Audit Trace. |
