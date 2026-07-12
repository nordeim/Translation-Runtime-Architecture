⎿  Read start-here.md (41 lines)                                                                
⎿  Read prototype.md (109 lines)                                                                                                                                                                                                          
⎿  Read review.md (54 lines)                                                                                                                                                                                                            
⎿  Read review-feedback.md (385 lines)                                                                                                                                                                                                    
                                                                                                                                                                                                                                          
I'll ground my review by checking the actual state of the repo — what's tracked, what the remote is, and whether the artifacts that review.md references actually exist.                                                                  
                                                                                                                                                                                                                                          
Bash(echo "=== TRACKED FILES ===" && git ls-files && echo "" && echo "=== UNTRACKED (new) FILES ===" && git status --short && echo "" && echo "=== ALL .md ON DISK ==…)                                                                   
⎿  === TRACKED FILES ===                                                                                                                                                                                                                  
   AGENTS.md
   CLAUDE.md                                                                                                                                                                                                                              
   … +32 lines (ctrl+o to expand)                                                                                                                                                                                                       
                                                                                                                                                                                                                                          
There are three more files (AGENTS.md, README.md, to_translate.md) that review.md explicitly references. Let me read those too so my review is grounded in actual content.                                                                
                                            
Read 3 files (ctrl+o to expand)                                                                                                                                                                                                           
                                                                                                                                                                                                                                          
I've now read the full repo (12 tracked files). The four documents you asked me to review are meta-documents layered on top of the 5-file spec — not part of the spec itself. Their relationships, which matter for the review:
                                                                                                                                                                                                                                          
- start-here.md — a Chinese usage guide for applying TRA via prompting.                                                                                                                                                                   
- prototype.md — a plan for a Python engine (tra-prototype) that lives outside this repo.                                                                                                                                                 
- review.md — an external review of the GitHub repo (written before prototype.md/review-feedback.md/to_translate.md existed).                                                                                                             
- review-feedback.md — an architectural critique of prototype.md + three embedded design micro-docs.                                                                                                                                      
                                                                                                                                                                                                                                          
Here is my meticulous review, grounded against the actual spec content.                                                                                                                                                                   
                                                                                                                                                                                                                                          
---                                                                                                                                                                                                                                       
Executive Summary                                         
                                                                                                                                                                                                                                          
The four documents are individually coherent and mostly faithful to the spec, but they introduce two genuinely harmful errors and several consistency rot issues that would mislead a future implementer:
                                                                                                                                                                                                                                          
┌─────┬─────────────┬─────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐                                         
│  #  │  Severity   │                Location                 │                                                              Issue                                                              │                                         
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 1   │ 🔴 Critical │ review-feedback.md                      │ Cites a non-existent benchmark test STRUCTURAL-FIDELITY-005. The real IDs are S-01–S-05; S-05 is Horizontal Rules, not anchors. │
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 2   │ 🔴 Critical │ review-feedback.md → EVIDENCE_SCHEMA.md │ Defines behavior that violates TRA's core "never self-score" invariant (acts on confidence_note < 0.5).                         │                                         
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 3   │ 🟠 Major    │ prototype.md + review-feedback.md       │ Sit in a spec-only repo, contradicting the repo's own rule that engines live elsewhere.                                         │                                         
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 4   │ 🟠 Major    │ README.md / AGENTS.md / CLAUDE.md       │ "Five markdown files are the entire product" is now stale (12 tracked files).                                                   │
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 5   │ 🟠 Major    │ review-feedback.md                      │ Overstates TRA as requiring byte-deterministic output; spec's determinism is about flow/arbitration, not exact text.            │
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 6   │ 🟡 Minor    │ start-here.md                           │ Drops the REPAIR loop — the most novel part of TRA — from the simplified workflow.                                              │
├─────┼─────────────┼─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤                                         
│ 7   │ 🟡 Minor    │ prototype.md vs review-feedback.md      │ Timeline contradiction: 2–4 days vs 6–8 person-days for the same plan.                                                          │
└─────┴─────────────┴─────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘                                         
                                                          
---                                                                                                                                                                                                                                       
Detailed Findings                                         
                                                                                                                                                                                                                                          
1. 🔴 review-feedback.md invents a benchmark test ID that does not exist
                                                                                                                                                                                                                                          
▎ "否则原型无法通过基准测试中的 STRUCTURAL-FIDELITY-005 用例。"                                                                                                                                                                           
                                                                                                                                                                                                                                          
The actual TRA-BENCHMARK-SUITE.md uses these IDs only:                                                                                                                                                                                    
- S-01 Nested Lists · S-02 Complex Tables · S-03 Inline Code · S-04 Blockquotes in Lists · S-05 Horizontal Rules
- F-01–F-05, T-01–T-05, D-01–D-04, E-01–E-03.                                                                                                                                                                                             
                                                          
There is no STRUCTURAL-FIDELITY-005 ID and no anchor/cross-reference test at all. The anchor-resolution concern (heading slugs breaking [#links]) is valid engineering advice, but it is justified with a fabricated citation. An         
implementer trusting this would look for a test that isn't there. Fix: re-justify the anchor work as a gap in the benchmark suite (which it genuinely is — see finding 8) rather than citing a phantom ID.                                
                                                                                                                                                                                                                                          
2. 🔴 EVIDENCE_SCHEMA.md contradicts the "never self-score" invariant                                                                                                                                                                     
                                                          
The spec is explicit and repeated across files:                                                                                                                                                                                           
- CLAUDE.md: "Verification never self-scores."            
- AGENTS.md / README.md: "VERIFY_OUTPUT produces evidence-based diagnostics — it does not rate its own output."                                                                                                                           
- EVIDENCE_SCHEMA.md §4: "confidence_note: Recorded but never used for scoring; for debugging only."           
                                                                                                                                                                                                                                          
Yet the same document's §4 verification rule states:                                                                                                                                                                                      
                                                                                                                                                                                                                                          
▎ "If an EvidenceRecord cites confidence_note < 0.5, the system automatically escalates to REPAIR_SEGMENT."                                                                                                                               
                                                                                                                                                                                                                                          
That is acting on a confidence score — a direct violation of the invariant the schema itself claims to honor. This is the kind of internal contradiction that, if implemented, would make an engine non-conformant at L3. Fix: delete the 
< 0.5 escalation rule; if low-confidence routing is desired, gate it on evidence presence (empty evidence_chain → BLOCKING), never on a numeric confidence score.
                                                                                                                                                                                                                                          
3. 🟠 Prototype planning docs violate the repo's stated boundary                                                                                                                                                                          
 
README.md / AGENTS.md / CLAUDE.md all state: "Any concrete engine, module, or tool claiming TRA compliance lives in a separate repository." prototype.md itself says it will create tra-prototype/ — a separate codebase. Yet prototype.md
 and review-feedback.md (which design that codebase) are committed in this repo's root.
                                                                                                                                                                                                                                          
This isn't harmful in isolation, but it makes the "spec-only, no code" framing self-contradictory and will confuse future readers about what the repo is. Recommendation: move these two into a prototype/ or docs/prototype/ subfolder   
clearly labeled as planning notes for an external repo, or relocate them to the tra-prototype repo.
                                                                                                                                                                                                                                          
4. 🟠 "Five files is the entire product" is stale                                                                                                                                                                                         
 
README.md, AGENTS.md, and CLAUDE.md all assert the five spec files are the whole product. The repo now tracks 12 files: the 5 spec files + README.md + AGENTS.md + CLAUDE.md + start-here.md + prototype.md + review-feedback.md +        
to_translate.md. The statement is no longer accurate and understates the repo's actual contents. Fix: change to "the five spec files are the normative product; the rest are usage/planning meta-docs."
                                                                                                                                                                                                                                          
5. 🟠 review-feedback.md overstates TRA's determinism requirement                                                                                                                                                                         
 
▎ "TRA规范的本质是确定性状态机（给定输入X，必须产出确定的输出Y和审计轨迹）。"                                                                                                                                                             
                                                          
This is a misreading. The spec defines a deterministic lifecycle and deterministic arbitration (sequential kernel states, the fixed priority stack). It is LLM-agnostic and never promises byte-identical output text across runs. The    
deterministic-cache proposal is good engineering (and correctly includes policy_stack_hash in the key), but framing LLM nondeterminism as a "fatal flaw" that "collapses the prototype at L3" overstates the spec. An implementer might
conclude cache is mandatory for conformance when the spec only requires deterministic flow. Fix: soften to "cache is recommended for reproducibility/L4; TRA conformance requires deterministic arbitration, not deterministic prose."    
                                                          
6. 🟡 start-here.md omits the REPAIR loop                                                                                                                                                                                                 
 
The simplified workflow ANALYZE → BUILD → TRANSLATE → VERIFY → AUDIT drops both REPAIR_IF_NEEDED and EMIT_PAYLOAD, and hides the VERIFY → REPAIR loop. Surgical, evidence-bounded repair is TRA's most distinctive contribution (Spec §3, 
§6). For a "start here" guide aimed at practitioners, omitting it understates the framework. Fix: add a REPAIR step and note VERIFY may loop back.
                                                                                                                                                                                                                                          
7. 🟡 Timeline contradiction between the paired docs                                                                                                                                                                                      
 
prototype.md estimates 2–4 days for MVP; review-feedback.md counters with 6–8 person-days. Since review-feedback.md is explicitly a response to prototype.md, the two should be reconciled — at minimum, prototype.md's timeline should   
carry a note that review tightened it.                    
                                                                                                                                                                                                                                          
8. (Corroborated) The benchmark "100+" claim is unsubstantiated                                                                                                                                                                           
 
review.md already flagged this correctly: TRA-BENCHMARK-SUITE.md says "100+ test cases" but lists only 22 concrete cases (S-01–S-05, F-01–F-05, T-01–T-05, D-01–D-04, E-01–E-03). This is why finding #1's anchor concern is real: there  
genuinely is no anchor/cross-reference test in the suite. Either expand the suite toward 100 or change the wording to "representative categories."
                                                                                                                                                                                                                                          
9. State-machine naming drift (cross-document)                                                                                                                                                                                            
 
Different documents render the kernel states differently:                                                                                                                                                                                 
- Spec: BUILD_ARTIFACTS, EXECUTE_TRANSLATION, REPAIR_IF_NEEDED, AUDIT_DIAGNOSTICS, EMIT_PAYLOAD
- README: INITIALIZE, BUILD, REPAIR, AUDIT, EMIT (abbreviated)                                                                                                                                                                            
- start-here: 5-step collapse dropping REPAIR/EMIT            
- prototype.md: uses ISA instruction names (ANALYZE_DOCUMENT, etc.) as the workflow                                                                                                                                                       
                                                                                                                                                                                                                                          
This conflates kernel states (the lifecycle) with ISA instructions (what runs inside BUILD_ARTIFACTS / EXECUTE_TRANSLATION). BUILD_ARTIFACTS contains BUILD_GLOSSARY + BUILD_ENTITY_TABLE. A future implementer reading these three       
renderings will be unsure whether states and instructions are the same thing. Fix: pick one canonical state-label set and reuse it everywhere; explicitly state "ISA instructions execute within kernel states."                          
                                                                                                                                                                                                                                          
---                                                                                                                                                                                                                                       
What's genuinely good (keep it)                           
                                                                                                                                                                                                                                          
- start-here.md's ZH-EN tips faithfully mirror TRA-MODULE-ZH-EN.md (成立 → Confirmed, nominalization verbalization, full-width punctuation). Accurate.
- review-feedback.md's three micro-docs are high-quality where they don't conflict with invariants: the cache-key formula (SHA-256 over sorted JSON, policy_stack_hash included) and the anchor-registry/placeholder/__HEADER_001__       
technique are sound and implementation-ready.                                                                                                                                                                                             
- review.md's verdict (8.5/10) and its call for a reference implementation + broader module guidance are reasonable and match the spec's intent.                                                                                          
- All four correctly preserve the priority stack order (Factual → Structural → Entity → Terminological → Epistemic → Fluency).                                                                                                            
                                                                                                                                                                                                                                          
---                                                                                                                                                                                                                                       
Recommended Actions (prioritized)                                                                                                                                                                                                         
                                                                                                                                                                                                                                          
1. Fix the two Criticals before anything else — remove the phantom STRUCTURAL-FIDELITY-005 citation; delete the confidence_note < 0.5 escalation rule in EVIDENCE_SCHEMA.md.
2. Re-scope the prototype docs out of the spec-only repo (or clearly namespace them) to honor the repo's own boundary rule.                                                                                                               
3. Update the "five files" statement in README/AGENTS/CLAUDE to reflect the current 12-file reality.                                                                                                                                      
4. Soften the determinism framing in review-feedback.md (recommended cache, not mandatory conformance requirement).                                                                                                                       
5. Reconcile the timeline between prototype.md and `review-feedback.md                                                                                                                                                                    
                                                                                                                                                                                                                                          
6. Restore the REPAIR step in start-here.md's workflow and note the VERIFY→REPAIR loop.                                                                                                                                                   
7. Substantiate or soften the benchmark "100+" claim, and (per finding #1/#8) add a real anchor/cross-reference test (S-06) so the valid anchor-resolution work has a traceable target.                                                   
8. Unify state-machine labels across README, start-here, and prototype.md; add one line: "ISA instructions execute within kernel states (BUILD_ARTIFACTS contains BUILD_GLOSSARY + BUILD_ENTITY_TABLE)."                                  
                                                                                                                                                                                                                                          
---                                                                                                                                                                                                                                       
Bottom line                                                                                                                                                                                                                               
                                                                                                                                                                                                                                          
The four documents are useful and mostly accurate, but two of them (the embedded EVIDENCE_SCHEMA.md and the STRUCTURAL-FIDELITY-005 citation in review-feedback.md) contain errors that would actively cause a conformant-by-intent engine
 to be non-conformant — one by acting on a confidence score (forbidden by the "never self-score" invariant), one by citing a test that doesn't exist. Those two must be corrected first. The remaining items are consistency-rot and      
scoping fixes that protect the repo's "spec-only, cross-referenced" integrity, which review.md rightly praised as the spec's strongest feature.
                                                                                                                                                                                                                                          
---                                                                                                                                                                                                                                            
I'll apply the fixes in focused batches. Starting with the two Criticals (fixes 1 & 2) plus the determinism softening (fix 5) in review-feedback.md — the file that holds both errors.                                                    
                                                                                                                                                                                                                                          
Update(review-feedback.md)                                                                                                                                                                                                                
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    13                                              
    14  计划提到“翻译叶子节点，重新组装”，但技术文档中最关键的锚点链接（[跳转](#heading-1)） 是全局依赖的。当 # 系统架构 被译为 # System Architecture 时，所有指向它的 [详见](#系统架构) 链接会全部失效。                                 
    15                                                    
    16 -· 架构建议：不应在Phase 1使用普通Markdown解析器。必须采用AST双向映射（如 markdown-it-py + 自定义Token遍历），在 ANALYZE_DOCUMENT 阶段构建 “Heading-ID映射表”，并在 TRANSLATE_SEGMENT 后强制执行 “锚点重写Pass”。否则原型无        
       -法通过基准测试中的 STRUCTURAL-FIDELITY-005 用例。                                                                                                                                                                          
    16 +· 架构建议：不应在Phase 1使用普通Markdown解析器。必须采用AST双向映射（如 markdown-it-py + 自定义Token遍历），在 ANALYZE_DOCUMENT 阶段构建 “Heading-ID映射表”，并在 TRANSLATE_SEGMENT 后强制执行 “锚点重写Pass”。——当前基准        
       +套件尚无锚点/交叉引用用例（见 TRA-BENCHMARK-SUITE.md 新增的 S-06），但锚点断裂是 L2/L3 结构保真度的真实缺口，原型应主动实现该 Pass。                                                                                       
    17  
    18  📜 3. L3审计的证据链空洞（“证据”不等于“日志”）
    19  

Now fix 2 — the confidence_note < 0.5 escalation rule in the embedded EVIDENCE_SCHEMA.md. Let me also handle fix 5 (determinism softening) in the same file.
                                                                           
Update(review-feedback.md)                           
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    214    1. Every TRANSLATE_SEGMENT must produce exactly one AuditRecord.
    215    2. The evidence_chain cannot be empty. If empty, VERIFY raises a BLOCKING flag.                                                                                                                                                
    216    3. Every EvidenceRecord must cite a valid rule_id or a recognized module. Unknown rules trigger a WARNING.
    217 -  4. If an EvidenceRecord cites confidence_note < 0.5, the system automatically escalates to REPAIR_SEGMENT for disambiguation.                                                                                                  
    217 +  4. Routing MUST NOT use confidence_note for any decision — it is recorded for debugging only, never read by VERIFY or REPAIR (this honors TRA's "never self-score" invariant). Low-evidence routing, if needed, is gated
        + solely on evidence *presence* (empty evidence_chain → RAISE_FLAG), never on a numeric score.                                                                                                                                    
    218                                                   
    219  ```
    220  

Now fix 5 — soften the overstated determinism claim.      
                                                                           
Update(review-feedback.md)                                
⎿  Added 3 lines, removed 3 lines                                                                                                                                                                                                         
     2                                                    
     3  然而，作为一个架构评审，我必须指出：该计划存在三个被严重低估的“架构级”风险。如果不在Phase 0/1予以纠正，原型将在L3验证阶段彻底崩塌。                                                                                               
     4                                                    
     5 -🚨 1. 致命缺陷：LLM的“非确定性”与TRA的“确定性虚拟机”冲突                                                                                                                                                                          
     5 +🚨 1. 风险：LLM的”非确定性”与TRA的”确定性”要求存在张力                                                                                                                                                                     
     6                                                                                                                                                                                                                                    
     7 -TRA规范的本质是确定性状态机（给定输入X，必须产出确定的输出Y和审计轨迹）。而计划中依赖 Temperature=0 的LLM，在数学上无法保证跨运行的一致性（模型升级、浮点误差、API抖动都会改变输出）。                                     
     7 +TRA规范定义的是**确定性的生命周期与确定性的仲裁**（顺序状态机、固定的优先级栈、可复现的冲突裁决）；它是 LLM 无关的，并不要求逐字节相同的译文。但计划的原型依赖 LLM，而即便 Temperature=0 也无法在数学上保证跨运行的一致性（
       +模型升级、浮点误差、API抖动都会改变输出）。这对 L4（取证级可重现性）是真实缺口，对 L3（严格级）主要是工程稳健性考量。                                                                                                      
     8  
     9  · 后果：VERIFY 发现错误 → REPAIR 调用LLM修复 → 修复引入新错误 → 死循环或审计轨迹无限膨胀。
    10 -· 必须补救：在 TRANSLATE_SEGMENT 与 REPAIR_SEGMENT 外层，强制增加 “确定性缓存层”（Cache Key = 输入原文 + 术语表Hash + 模型版本）。若命中缓存，直接返回上次的确定性结果，否则才调用LLM并写入缓存。这是满足L4“可重现性”的唯一
       -出路。                                                                                                                                                                                                                     
    10 +· 建议补救：在 TRANSLATE_SEGMENT 与 REPAIR_SEGMENT 外层，增加 “确定性缓存层”（Cache Key = 输入原文 + 术语表Hash + 模型版本 + 策略栈Hash）。若命中缓存，直接返回上次的确定性结果，否则才调用LLM并写入缓存。这是满足L4”可重现
       +性”的推荐手段；缓存是增强可复现性的工程实践，并非 TRA 一致性等级的强制要求（一致性要求的是确定性的流程与仲裁，而非确定性的译文文本）。                                                                                     
    11  
    12  🧩 2. 结构保真度盲区：Markdown锚点与交叉引用的“隐形断裂”
    13  

Now fix 7 — reconcile the timeline contradiction in prototype.md.
                                                                           
Update(prototype.md)                               
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    81  - Logging/visualization of state machine.  
    82  - Documentation + example run.                                                                                                                                                                                                    
    83                                                    
    84 -**Timeline Estimate**: 2-4 days for MVP (core pipeline working on sample tech docs). Iterative refinement afterward.                                                                                                              
    84 +**Timeline Estimate**: 2-4 days for a naive MVP, but see `review-feedback.md` §"关于时间线（2~4天）的现实性评估" — with the hardened scope (anchor mapping, evidence framework, deterministic cache, termination guards) th
       +e realistic estimate is **6-8 person-days** for a conformant MVP. Plan accordingly.                                                                                                                                               
    85                                                    
    86  ### 3. Key Challenges & Mitigations
    87  - **LLM Reliability**: Use structured prompting + glossary injection + post-verify/repair loop. Temperature=0 where possible. Fallback rules for critical parts.

Fix 3 — re-scope the prototype docs. I'll add a header note to both prototype.md and review-feedback.md clarifying they are planning notes for an external repo.
                                                                           
Update(prototype.md)                               
⎿  Added 2 lines                                                                                                                                                                                                                          
    1 +> **Repo scope note:** Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is a **planning note for `tra
      +-prototype/`** — an external codebase — not part of the normative spec. It is kept here as planning context only.                                                                                                                  
    2 +                                                                                                                                                                                                                            
    3  **Meticulous Plan for a Practical TRA Prototype**                                                                                                                                                                                  
    4                                                     
    5  I have reviewed the TRA specification thoroughly. Below is a **detailed, phased implementation plan** for a practical, minimal-yet-conformant prototype. The goal is a working **Python-based Translation Runtime Engine** (       
       call it `tra-prototype`) that demonstrates the core invariants, Kernel lifecycle, ISA, Memory Model, Policy Engine, and L1–L3 conformance for ZH↔EN technical Markdown translation. It will be **human-in-the-loop friendly*
       * and extensible.

Update(review-feedback.md)                          
⎿  Added 2 lines                                                           
    1 +> **Repo scope note:** Per the repo's own boundary rule (see `README.md` / `AGENTS.md` / `CLAUDE.md`), any concrete engine claiming TRA compliance lives in a *separate* repository. This file is an **architectural critiqu
      +e of `prototype.md`** (an external `tra-prototype/` codebase) plus embedded design micro-docs. It is planning context for that external repo, not part of the normative spec, and is kept here only as planning context.           
    2 +                                                                                                                                                                                                                            
    3  这份计划书扎实、专业且高度忠实于TRA规范，展现了极强的工程落地意识。你对Pydantic模型、不变式断言和ISA指令的拆解几乎无可挑剔。                                                                                                       
    4                                                     
    5  然而，作为一个架构评审，我必须指出：该计划存在三个被严重低估的“架构级”风险。如果不在Phase 0/1予以纠正，原型将在L3验证阶段彻底崩塌。                                                                                                
                                                          
Fix 8 — unify state-machine labels across start-here.md, prototype.md, and add the "ISA executes within kernel states" clarification. Starting with start-here.md (add REPAIR step + loop + naming note).
                                                                           
Update(start-here.md)                               
⎿  Added 5 lines, removed 1 line                                                                                                                                                                                                          
    16  1. 分析 (ANALYZE_DOCUMENT)：让LLM先分析文档，输出结构图谱和文档画像。
    17  2. 构建 (BUILD_ARTIFACTS)：要求提取术语表和实体表。                                                                                                                                                                               
    18  3. 翻译 (TRANSLATE_SEGMENT)：基于前两步结果逐段翻译。
    19 -4. 验证与审计 (VERIFY & AUDIT)：最后根据TRA规则进行自检。                                                                                                                                                                         
    19 +4. 验证 (VERIFY_OUTPUT)：根据TRA规则进行证据式自检。                                                                                                                                                                       
    20 +5. 修复 (REPAIR_SEGMENT)：若 VERIFY 返回 BLOCKING/WARNING 违规，定向修复（只解决该违规、不引入新违规、不违背更高优先级策略）。修复后回到 4 重新验证；设定最大重试次数（如3次），仍失败则升级人工介入。                            
    21 +6. 审计与产出 (AUDIT_DIAGNOSTICS → EMIT_PAYLOAD)：生成审计追踪（audit_trace）并输出译文。                                                                                                                                  
    22  
    23 +> 注：上述步骤对应 TRA-KERNEL 的规范状态机 BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD。ISA 指令运行在 
       +对应的内核状态之内（BUILD_ARTIFACTS 内含 BUILD_GLOSSARY 与 BUILD_ENTITY_TABLE）。                                                                                                                                          
    24 +                                                                                                                                                                                                                           
    25  ✅ 第三步：把关——作为质量检查清单
    26  
    27  TRA的一致性指南和基准测试是绝佳的质量检查清单。翻译完成后，可以对照检查：

Now fix 4 + 8 in README.md and AGENTS.md — update the stale "five files" statement and add the state/ISA clarification. Let me update README's stale claim first.
                                                                           
Update(README.md)                                   
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
     6                                              
     7  ## What This Is                                                                                                                                                                                                                   
     8                                                    
     9 -This is a **specification repository**, not a code repository. The five markdown files below are the entire product. There is no source code, no build system, no test runner, and no package manifest.                           
     9 +This is a **specification repository**, not a code repository. The five Spec files below are the normative product. Additional meta-docs (`README.md`, `AGENTS.md`, `CLAUDE.md`, `start-here.md`), planning notes (`prototy
       +pe.md`, `review-feedback.md`), and `to_translate.md` accompany them. There is no source code, no build system, no test runner, and no package manifest — any conformant engine lives in a separate repository.                    
    10                                                    
    11  ## Documents
    12  

Now add the kernel-state vs ISA-instruction clarification to README's "Architecture at a Glance" and a note that ISA runs within states.
                                                                           
Update(README.md)                                   
⎿  Error editing file                                                                                                                                                                                                                     
                                                    
The stale claim is already fixed. Now I'll add a clarifying note about states vs ISA in README's architecture section.                                                                                                                    
                                                                           
Update(README.md)                                                                                                                                                                                                                         
⎿  Added 2 lines                                                                                                                                                                                                                          
    45  └─────────────────────────────────────────────────────────────────┘                                                                                                                                                               
    46  ```                                                                                                                                                                                                                               
    47                                                    
    48 +> **States vs. instructions:** The KERNEL states above are the lifecycle; the ISA instructions *execute within* those states — e.g., `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`, and `EXECUTE_TRANS       
       +LATION` contains `TRANSLATE_SEGMENT`. The canonical state labels (from `TRA-SPECIFICATION.md` §2.1) are `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR
       +_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`.                                                                                                                                                                                   
    49 +                                                                                                                                                                                                                           
    50  ## Conformance Levels
    51  
    52  | Level | Name | Focus | Use Case |

Now update AGENTS.md — fix the stale claim and add the states-vs-ISA note.
                                                                           
Update(AGENTS.md)                                         
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    2                                                     
    3  ## What this repo is                                                                                                                                                                                                               
    4                                                     
    5 -Specification-only repo. TRA = Translation Runtime Architecture v1.0 — normative spec for high-fidelity technical translation engines. Five markdown files are the entire product. **No source code, no build system, no tes       
      -t runner, no package manifest.**                                                                                                                                                                                            
    5 +Specification-only repo. TRA = Translation Runtime Architecture v1.0 — normative spec for high-fidelity technical translation engines. The **five Spec files** are the normative product; meta-docs (`README.md`, `CLAUDE.md       
      +`, `start-here.md`), planning notes (`prototype.md`, `review-feedback.md`), and `to_translate.md` accompany them. **No source code, no build system, no test runner, no package manifest.** Any conformant engine lives in a
      + separate repository.                                                                                                                                                                                                       
    6  
    7  ## Files and roles
    8  

Now add the states-vs-ISA clarification to AGENTS.md (and update CLAUDE.md's stale claim too). Let me append a note in AGENTS.md's Files section.
                                                                           
Update(AGENTS.md)                                         
⎿  Added 2 lines                                                                                                                                                                                                                          
    16                                                    
    17  **Cross-referencing:** Use document title and section numbers (e.g., "Spec §5.1"), not filename numeric prefixes. The file prefix numbers (1–4) do not match section order in the spec.                                           
    18                                                    
    19 +**States vs. instructions:** The KERNEL states are the lifecycle; the ISA instructions *execute within* those states — `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`. Canonical state labels (Spec §2.       
       +1): `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF_NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`.                                                     
    20 +                                                                                                                                                                                                                                  
    21  ## How to work here                               
    22  
    23  - "Working" = authoring, refining, cross-checking spec documents.

Now update CLAUDE.md's stale "five markdown files are the entire product" line (fix 4) and add the states-vs-ISA note (fix 8). Let me read the relevant part of CLAUDE.md first.
                                                                           
Read 1 file (ctrl+o to expand)    
                                                                                                                                                                                                                                          
Update(CLAUDE.md)                                         
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
     4                                                                     
     5  ## What this repository is                                                                                                                                                                                                        
     6                                                                                                                                                                                                                                    
     7 -This is a **specification repository**, not a code repository. TRA = **Translation Runtime Architecture** (v1.0), a normative design for high-fidelity technical translation engines (human-in-the-loop or automated). Ther       
       -e is no source code, no build system, no test runner, and no package manifest. The four numbered `.md` files plus `TRA-SPECIFICATION.md` are the entire product.                                                                  
     7 +This is a **specification repository**, not a code repository. TRA = **Translation Runtime Architecture** (v1.0), a normative design for high-fidelity technical translation engines (human-in-the-loop or automated). Ther
       +e is no source code, no build system, no test runner, and no package manifest. The **five Spec files** are the normative product; meta-docs (`README.md`, `AGENTS.md`, `start-here.md`), planning notes (`prototype.md`, `r       
       +eview-feedback.md`), and `to_translate.md` accompany them. Any conformant engine lives in a separate repository.                                                                                                           
     8  
     9  There are **no build / lint / test commands**. "Working" in this repo means authoring, refining, and cross-checking the specification documents. Use standard git for versioning (`git add`, `git commit`, `git log`). Any
        concrete engine, module, or tool that claims TRA compliance is out of scope of *this* repo — it would live elsewhere.
    10  

Now update CLAUDE.md's "How the five documents relate" heading (stale) and add the states-vs-ISA note.
                                                                           
Update(CLAUDE.md)                                        
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    19  - **Conformance Levels (L1–L4)** — strictness dial. L1 Basic → L2 Professional → L3 Strict (full TRA + diagnostics) → L4 Forensic (line-by-line evidence tracing). Each level subsumes the one below it.
    20  - **Modules (plug-ins, mutable/extensible)** — Language Modules, Domain Modules, Formatting Modules. **They must not alter the Kernel or ISA.** This separation is the load-bearing design decision: any new module (e.g.,        
        a `fr-en.md` language bridge) extends data/behavior without touching core.
    21                                                                                                                                                                                                                                    
    22 -## How the five documents relate                                                                                                                                                                                           
    22 +## How the five Spec documents relate                                                                                                                                                                                             
    23                                                    
    24  | File | Role | Relationship |
    25  | :--- | :--- | :--- |

Now add the states-vs-ISA note to CLAUDE.md's mental model (after the Kernel bullet).
                                                                           
Update(CLAUDE.md)                                        
⎿  Added 1 line                                                                                                                                                                                                                           
    14                                                   
    15  - **Kernel (immutable)** — the sequential state machine. Every translation request must pass through `BOOTSTRAP → INITIALIZE_RUNTIME → ANALYZE_DOCUMENT → BUILD_ARTIFACTS → EXECUTE_TRANSLATION → VERIFY_OUTPUT → REPAIR_IF       
        _NEEDED → AUDIT_DIAGNOSTICS → EMIT_PAYLOAD`. State transitions are triggered only by successful completion of ISA instructions. See the Mermaid diagram in `TRA-SPECIFICATION.md` §2.1.
    16  - **Memory Model (immutable segments)** — four segments with different mutability: Immutable Config (read-only), Runtime Context (read/write), Document Memory (read-only), Audit Memory (append-only). Instructions read/w       
        rite per their contracts.                         
    17 +- **States vs. instructions (easy to conflate):** The KERNEL states are the lifecycle; the ISA instructions *execute within* those states — e.g., `BUILD_ARTIFACTS` contains `BUILD_GLOSSARY` + `BUILD_ENTITY_TABLE`, and `       
       +EXECUTE_TRANSLATION` contains `TRANSLATE_SEGMENT`. Note that `review.md`'s "BOOTSTRAP → ANALYZE → BUILD → TRANSLATE → VERIFY → REPAIR → AUDIT → EMIT" and `start-here.md`'s collapsed workflow are *abbreviated renderings*
       + of the canonical state labels above; they are not a different state machine.                                                                                                                                              
    18  - **ISA (immutable atomic ops)** — `ANALYZE_DOCUMENT`, `BUILD_GLOSSARY`, `BUILD_ENTITY_TABLE`, `TRANSLATE_SEGMENT`, `VERIFY_OUTPUT`, `REPAIR_SEGMENT`. Each has a strict contract: Inputs, Preconditions, Outputs, Invarian
        ts, Failure Conditions. Engines **must not skip instructions**.
    19  - **Policy Engine (immutable priority stack)** — resolves conflicts deterministically. The stack order is non-negotiable: 1) Factual Integrity, 2) Structural Integrity, 3) Entity Preservation, 4) Terminological Consiste
        ncy, 5) Epistemic Fidelity, 6) Target Fluency. Higher priority always wins; ties defer to Domain Module heuristics, then preserve source ambiguity as `Warning`.
    20  - **Conformance Levels (L1–L4)** — strictness dial. L1 Basic → L2 Professional → L3 Strict (full TRA + diagnostics) → L4 Forensic (line-by-line evidence tracing). Each level subsumes the one below it.

Now the last fixes remaining: fix 6 (start-here REPAIR already done above), and fix 8's benchmark expansion (fix 7/8 in the original list: substantiate "100+" and add S-06 anchor test). Let me read the benchmark file's Category 1
tail.                                                                      

Read 1 file (ctrl+o to expand)                                                                                                                                                                                                            
                         
Add S-06 anchor/cross-reference test after S-05.                                                                                                                                                                                          
                                                                           
Update(TRA-BENCHMARK-SUITE.md)                                             
⎿  Added 1 line                                                                                                                                                                                                                           
    12  | S-03 | Inline Code vs. Prose | Backticks preserved; content inside backticks untranslated. |                                                                                                                                    
    13  | S-04 | Blockquotes within Lists | `>` syntax preserved at correct indentation level. |                                                                                                                                          
    14  | S-05 | Horizontal Rules as Dividers | `---` preserved exactly; not converted to headings. |                                                                                                                                     
    15 +| S-06 | Internal Anchors & Cross-References | Heading translation updates the target slug (e.g., `# System Setup` → `# 系统安装` rewrites `[link](#system-setup)` → new slug). Links must resolve post-translation; broken       
       + links flagged as `WARNING`. Code-block-internal links are not rewritten. |                                                                                                                                                
    16                                                                                                                                                                                                                                    
    17  ## Category 2: Factual & Numerical Precision      
    18  | ID | Test Case | Success Criteria |

Now soften the "100+" claim in the benchmark overview line 5 and in README/AGENTS references. Let me check the exact overview line.
                                                                           
Read 1 file (ctrl+o to expand)    
                                                                                                                                                                                                                                          
Update(TRA-BENCHMARK-SUITE.md)                            
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    2  **Standardized Evaluation Suite v1.0**                              
    3                                                                                                                                                                                                                                     
    4  ## Overview                                                                                                                                                                                                                        
    5 -This suite contains 100+ representative test cases designed to validate TRA conformance across diverse domains and structural complexities. Engines must pass these cases to achieve L3/L4 certification.                          
    5 +This suite defines representative test categories (Structural, Factual, Terminology, Domain, Ambiguity) with concrete seed cases to validate TRA conformance. It is seeded with the cases below and intended to grow toward        
      +100+ cases; engines must pass the relevant cases (per their conformance level) to achieve L3/L4 certification.                                                                                                              
    6                                                                                                                                                                                                                                     
    7  ## Category 1: Structural Integrity (Markdown & Formatting)
    8  | ID | Test Case | Success Criteria |

Now update the "100+" references in README and AGENTS.    
                                                                           
Searched for 1 pattern (ctrl+o to expand)                 
                                                                                                                                                                                                                                          
Update(AGENTS.md)                                         
⎿  Added 1 line, removed 1 line                                                                                                                                                                                                           
    11  | `TRA-SPECIFICATION.md` | Authoritative master spec (Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules). Source of truth. |
    12  | `TRA-ISA-REFERENCE.md` | Expanded contracts for the six ISA instructions. Companion to Spec §3. |                                                                                                                               
    13  | `TRA-MODULE-ZH-EN.md` | Language Module example (ZH↔EN bridge). Template for new modules. |
    14 -| `TRA-BENCHMARK-SUITE.md` | 100+ test cases for L3/L4 certification. |                                                                                                                                                           
    14 +| `TRA-BENCHMARK-SUITE.md` | Representative test categories (S/F/T/D/E) seeded with concrete cases, intended to grow toward 100+, for L3/L4 certification. |                                                               
    15  | `TRA-CONFORMANCE-GUIDE.md` | Auditor checklist for L1–L4 certification. |                                                                                                                                                       
    16                                                    
    17  **Cross-referencing:** Use document title and section numbers (e.g., "Spec §5.1"), not filename numeric prefixes. The file prefix numbers (1–4) do not match section order in the spec.

Update(README.md)                                         
⎿  Added 1 line, removed 1 line                                            
    15  | [`TRA-SPECIFICATION.md`](TRA-SPECIFICATION.md) | Authoritative master spec — Kernel, Memory, ISA, Runtime, Policy, Exceptions, QA, Conformance, Modules. **Source of truth.** |
    16  | [`TRA-ISA-REFERENCE.md`](TRA-ISA-REFERENCE.md) | Expanded contracts for the six ISA instructions. Companion to Spec §3. |                                                                                                       
    17  | [`TRA-MODULE-ZH-EN.md`](TRA-MODULE-ZH-EN.md) | Language Module example (ZH↔EN bridge). Template for authoring new modules. |
    18 -| [`TRA-BENCHMARK-SUITE.md`](TRA-BENCHMARK-SUITE.md) | 100+ test cases (S/F/T/D/E categories) for L3/L4 certification. |                                                                                                          
    18 +| [`TRA-BENCHMARK-SUITE.md`](TRA-BENCHMARK-SUITE.md) | Representative test categories (S/F/T/D/E) seeded with concrete cases, intended to grow toward 100+, for L3/L4 certification. |                                     
    19  | [`TRA-CONFORMANCE-GUIDE.md`](TRA-CONFORMANCE-GUIDE.md) | Auditor checklist for L1–L4 certification. |                                                                                                                           
    20                                                    
    21  **Cross-referencing:** Use document title and section numbers (e.g., "Spec §5.1"), not filename numeric prefixes. The prefix numbers (1–4) do not match section order in the spec.

All 8 fixes applied. Let me verify the edits landed correctly and check there are no remaining contradictions with a quick grep.
                                                                           
Searched for 1 pattern (ctrl+o to expand)                 
                                                                                                                                                                                                                                          
All checks pass. Here's the completed work.               
                                                                                                                                                                                                                                          
Fixes 1–8 applied                                         
                                                                                                                                                                                                                                          
Critical (correctness — would have caused non-conformant engines):                                                                                                                                                                        
- Fix 1 — Removed the fabricated STRUCTURAL-FIDELITY-005 citation in review-feedback.md; re-justified the anchor-resolution work as a real gap (now backed by the new S-06 test).                                                         
- Fix 2 — Removed the confidence_note < 0.5 escalation rule in the embedded EVIDENCE_SCHEMA.md; replaced with an explicit "never read confidence for decisions" rule gated on evidence presence. This now honors TRA's "never self-score" 
invariant.                                                                                                                                                                                                                               
                                                                                                                                                                                                                                          
Major (scoping & staleness):                              
- Fix 3 — Added repo-scope header notes to prototype.md and review-feedback.md clarifying they are planning notes for an external tra-prototype repo, honoring the repo's own boundary rule.                                              
- Fix 4 — Replaced the stale "five markdown files are the entire product" in README.md, AGENTS.md, and CLAUDE.md with accurate descriptions of the current 12-file repo.                                                                  
- Fix 5 — Softened review-feedback.md's overstated determinism claim: cache is recommended for L4 reproducibility, not a mandatory conformance requirement; TRA requires deterministic flow/arbitration, not deterministic prose.         
                                                                                                                                                                                                                                          
Minor (consistency):                                                                                                                                                                                                                      
- Fix 6 — Restored the REPAIR_SEGMENT step and VERIFY→REPAIR loop in start-here.md's workflow, plus a state-machine canon note.                                                                                                           
- Fix 7 — Reconciled the timeline contradiction: prototype.md now points to review-feedback.md's realistic 6–8 person-days estimate.                                                                                                      
- Fix 8 — Added a "States vs. instructions" clarification to README.md, AGENTS.md, CLAUDE.md (ISA executes within kernel states), and expanded the benchmark suite: softened "100+" to "seeded, intended to grow," and added the real S-06
 Internal Anchors test so the valid anchor-resolution work now has a traceable target.                                                                                                                                                    
                                                                                                                                                                                                                                          
Verification grep confirms: no phantom ID, no bad confidence rule, no stale "entire product" claim, and S-06 present.                                                                                                                     
                                                                                                                                                                                                                                          
Note: these are documentation edits only — no code changes, and nothing committed. Want me to commit them as a single lumping commit, or in logical groups (spec corrections vs. meta-doc updates)?                                       
                                                                                                                                                                                                                                          
