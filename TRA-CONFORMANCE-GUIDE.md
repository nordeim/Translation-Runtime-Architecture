# 4. TRA-CONFORMANCE-GUIDE.md
**Auditor’s Guide to TRA Compliance Levels v1.0**

## Overview
This guide defines the four levels of TRA conformance. Auditors should use this checklist to certify translation engines or human-AI workflows.

## Level 1: Basic (L1)
*   **Focus:** Meaning and Basic Formatting.
*   **Requirements:** 
    *   Factual claims are preserved.
    *   Basic Markdown (headings, bold) is intact.
    *   No major hallucinations.
*   **Allowed Failures:** Minor terminology drift; inconsistent formatting of lists/tables; slight strengthening/weakening of tone.
*   **Use Case:** Internal drafts, low-stakes blog posts.

## Level 2: Professional (L2)
*   **Focus:** Terminology and Structural Fidelity.
*   **Requirements:** 
    *   L1 requirements met.
    *   Technical terminology is consistent throughout the document.
    *   Tables and code blocks are structurally perfect.
    *   Product names and entities are untranslated.
*   **Allowed Failures:** Minor fluency issues ("translationese"); occasional missed epistemic nuance.
*   **Use Case:** Public-facing documentation, GitHub READMEs.

## Level 3: Strict (L3)
*   **Focus:** Full TRA Compliance with Diagnostics.
*   **Requirements:** 
    *   L2 requirements met.
    *   Explicit Glossary and Entity Table generated and enforced.
    *   Epistemic certainty mapped exactly (no strengthening/weakening).
    *   Numerical and metric precision is 100% accurate.
    *   Audit Trace provided with evidence-based diagnostics.
*   **Allowed Failures:** None in factual/structural domains; minor stylistic preferences allowed if logged.
*   **Use Case:** Security advisories, architecture guides, benchmark reports.

## Level 4: Forensic (L4)
*   **Focus:** Line-by-Line Evidence Tracing.
*   **Requirements:** 
    *   L3 requirements met.
    *   Every translation decision is logged with its Policy justification.
    *   Ambiguities are explicitly detected and logged.
    *   Repair history is fully traceable.
*   **Allowed Failures:** None.
*   **Use Case:** Legal contracts, regulatory filings, high-stakes security audits.

## Auditor Checklist for L3 Certification
1.  [ ] **Bootstrap:** Verify `tvm_bootstrap` config was parsed correctly.
2.  [ ] **Artifacts:** Check `compilation_artifacts` for complete Glossary and Structural Map.
3.  [ ] **Arbitration:** Verify that no lower-priority rule (e.g., Fluency) compromised a higher one (e.g., Facts).
4.  [ ] **Diagnostics:** Review `audit_trace` for any `BLOCKING` errors. If present, certification is denied.
5.  [ ] **Spot Check:** Randomly select 5 technical terms and verify they match the Glossary exactly.
6.  [ ] **Numerical Audit:** Verify all numbers, units, and version strings against the source.
