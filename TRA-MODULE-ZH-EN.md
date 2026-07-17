# 2. TRA-MODULE-ZH-EN.md
**Linguistic Bridge Module: Chinese ↔ English v1.0**

## Overview
This module provides the linguistic rules and stylistic conventions required to bridge the structural and rhetorical gaps between Chinese (ZH) and English (EN) technical documentation. It is injected into the Runtime Context when `language_pair` is set to `ZH -> EN` or `EN -> ZH`.

## Direction: Chinese → English (ZH → EN)

### 1. Structural Bridge: Parataxis to Hypotaxis
*   **Rule:** Chinese relies on logical flow and context (Parataxis), often omitting subjects and conjunctions. English requires explicit grammatical structures (Hypotaxis).
*   **Execution:** 
    *   Supply missing subjects (e.g., "the system", "developers", "it").
    *   Insert explicit conjunctions (e.g., "because", "although", "which") where logical relationships are implied in Chinese.
    *   Convert topic-comment structures into subject-predicate sentences.

### 2. Verbalization of Nominalizations
*   **Rule:** Chinese technical writing frequently uses noun-heavy bureaucratic phrases. English prefers strong, direct verbs.
*   **Mapping:** 
    *   "进行验证" → `verify` (NOT "conduct verification")
    *   "实现优化" → `optimize` (NOT "achieve optimization")
    *   "提供支持" → `support` (NOT "provide support for")

### 3. Epistemic Certainty Mapping
*   **Rule:** Preserve the exact degree of confidence. Do not strengthen or weaken.
*   **Lexicon:** 
    *   "成立" → `Confirmed` (NOT "Valid", "True", "Correct")
    *   "准确描述" → `accurately describes` (NOT "perfectly describes")
    *   "高度可信" → `highly credible` (NOT "indisputably true")
    *   "可能" → `may` / `possibly` (NOT "will")

### 4. Information Order
*   **Rule:** Preserve the source's logical flow (Evidence → Conclusion) in verification reports to maintain rhetorical build-up. In general prose, adapt to English preference for Conclusion → Evidence only if clarity demands it.

## Direction: English → Chinese (EN → ZH)

### 1. Avoidance of Translationese
*   **Rule:** Do not mechanically copy English syntax. Use natural Chinese technical writing conventions.
*   **Execution:** 
    *   Break long attributive clauses ("which/that" chains) into concise, logical Chinese clauses.
    *   Avoid excessive use of the passive marker "被" (bèi); prefer active or subjectless structures.

### 2. Four-Character Expressions (四字格)
*   **Rule:** Use natural four-character technical expressions where appropriate for conciseness and rhythm.
*   **Mapping:** 
    *   "Hardware isolation" → `硬件隔离`
    *   "Seamless migration" → `无缝迁移`
    *   "High availability" → `高可用性`

### 3. Punctuation Conventions
*   **Rule:** Use full-width punctuation (，。：) for Chinese prose. Use half-width ASCII punctuation (, . :) inside code blocks, inline code, URLs, and when adjacent to English product names/numbers.
*   **Spacing:** Maintain a single space between Chinese characters and English words/numbers (e.g., `版本 v0.5.0`).

### 4. Entity Preservation
*   **Rule:** Retain English product names, APIs, and protocols unless a universally accepted official Chinese name exists (e.g., "Kubernetes" stays "Kubernetes", not "库伯内提斯").
