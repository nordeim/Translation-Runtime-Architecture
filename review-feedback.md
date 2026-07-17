> **Repo scope note:** The repo's original boundary rule put any concrete TRA-compliant engine in a *separate* repository (see `README.md` / `AGENTS.md` / `CLAUDE.md`). That was overridden: the `tra-prototype/` engine now lives as a subdirectory of this repo so the prototype and spec evolve together. This file remains an **architectural critique of `prototype.md`** plus embedded design micro-docs — planning context, not part of the normative spec.

这份计划书扎实、专业且高度忠实于TRA规范，展现了极强的工程落地意识。你对Pydantic模型、不变式断言和ISA指令的拆解几乎无可挑剔。

然而，作为一个架构评审，我必须指出：该计划存在三个被严重低估的“架构级”风险。如果不在Phase 0/1予以纠正，原型将在L3验证阶段彻底崩塌。

🚨 1. 风险：LLM的”非确定性”与TRA的”确定性”要求存在张力

TRA规范定义的是**确定性的生命周期与确定性的仲裁**（顺序状态机、固定的优先级栈、可复现的冲突裁决）；它是 LLM 无关的，并不要求逐字节相同的译文。但计划的原型依赖 LLM，而即便 Temperature=0 也无法在数学上保证跨运行的一致性（模型升级、浮点误差、API抖动都会改变输出）。这对 L4（取证级可重现性）是真实缺口，对 L3（严格级）主要是工程稳健性考量。

· 后果：VERIFY 发现错误 → REPAIR 调用LLM修复 → 修复引入新错误 → 死循环或审计轨迹无限膨胀。
· 建议补救：在 TRANSLATE_SEGMENT 与 REPAIR_SEGMENT 外层，增加 “确定性缓存层”（Cache Key = 输入原文 + 术语表Hash + 模型版本 + 策略栈Hash）。若命中缓存，直接返回上次的确定性结果，否则才调用LLM并写入缓存。这是满足L4”可重现性”的推荐手段；缓存是增强可复现性的工程实践，并非 TRA 一致性等级的强制要求（一致性要求的是确定性的流程与仲裁，而非确定性的译文文本）。

🧩 2. 结构保真度盲区：Markdown锚点与交叉引用的“隐形断裂”

计划提到“翻译叶子节点，重新组装”，但技术文档中最关键的锚点链接（[跳转](#heading-1)） 是全局依赖的。当 # 系统架构 被译为 # System Architecture 时，所有指向它的 [详见](#系统架构) 链接会全部失效。

· 架构建议：不应在Phase 1使用普通Markdown解析器。必须采用AST双向映射（如 markdown-it-py + 自定义Token遍历），在 ANALYZE_DOCUMENT 阶段构建 “Heading-ID映射表”，并在 TRANSLATE_SEGMENT 后强制执行 “锚点重写Pass”。——当前基准套件尚无锚点/交叉引用用例（见 TRA-BENCHMARK-SUITE.md 新增的 S-06），但锚点断裂是 L2/L3 结构保真度的真实缺口，原型应主动实现该 Pass。

📜 3. L3审计的证据链空洞（“证据”不等于“日志”）

计划中的 audit_trace.json 容易沦为“操作日志”（何时调用了什么指令）。但TRA L3要求的是 “逐条术语决策的可追溯证据”（例如：为何将“establishment”译为“成立”而非“建立”？依据是什么？）。

· 必须注入“证据框架”：在 BUILD_GLOSSARY 后，应固化一个 EvidenceRegistry 类。对于每个翻译输出，TRANSLATE_SEGMENT 的Prompt必须强制要求LLM返回 “决策依据JSON”（如 {"term": "establishment", "decision": "成立", "evidence": "匹配模块ZH-EN规则#42: 法律上下文优先"}）。VERIFY 仅验证这些依据是否合法，而非验证译文本身。没有证据链，L3认证就是空谈。

---

⚙️ 其余被低估的实现细节（需调整Phase排序）

· 策略引擎的“上下文衰减”：计划中Policy Engine的优先级栈是静态的。但在嵌套Markdown列表或代码块注释中，策略应具备作用域（Scope）。建议在Phase 3为 PolicyPriority 增加 scope_type（如 header_level 或 code_block_lang），否则无法处理“代码注释内术语不翻译”的边缘情况。
· 修复循环的“终止条件”缺失：REPAIR_SEGMENT 必须设置最大重试次数（如3次），且若修复后 VERIFY 仍失败，应触发 RAISE_FLAG 并暂停请求人工介入（Human-in-the-loop），而非无限自愈。

---

📅 关于时间线（2~4天）的现实性评估

若单人开发，完成 Phase 0 + Phase 1（带锚点映射） 至少需1天；Phase 2（6条带契约的ISA）需2天；策略引擎+证据框架+确定性缓存 需至少2天；集成测试与CLI收尾需1天。保守估计MVP需6~8个完整人日。建议将Phase 5（可视化/日志）降级为Phase 6，以确保核心逻辑不被草率收尾。

---

✅ 最终结论与行动建议

这份原型计划值得立即启动，但请在编码前先补充三份技术设计微文档：

1. CACHE_STRATEGY.md（确定性缓存策略）。
2. ANCHOR_RESOLUTION.md（锚点重写算法）。
3. EVIDENCE_SCHEMA.md（审计证据的JSON Schema）。

若你同意这些修正，请指示我从 “修复后的Phase 0（含Evidence Schema和Cache基类）” 开始编码。我建议你直接让我生成核心的 memory.py 和 isa.py 骨架，并明确你的LLM后端选择（OpenAI/Anthropic/本地），以便我将缓存键的生成逻辑写死。

---

为这三份文档制定创建计划，本质上是在为原型的“确定性、结构完整性与可审计性”这三大命脉打下地基。我建议按 EVIDENCE → CACHE → ANCHOR 的顺序起草，因为证据模式（Schema）是其他两者写入审计追踪时的依赖基础。

以下是这三份文档的详细创建大纲与协作蓝图，你可以直接按此执行，或授权我逐份生成完整内容。

---

📜 文档一：EVIDENCE_SCHEMA.md（证据模式与审计追踪）

目标：定义L3/L4合规的“证据”粒度，确保每句译文的出处都有据可查。

· 1. 核心类型定义（Pydantic模型蓝图）：
  · EvidenceType 枚举：TERM_MATCH, ENTITY_PRESERVED, POLICY_ARBITRATION, STRUCTURAL_MAPPING, HUMAN_OVERRIDE。
  · EvidenceSource 结构：必须包含 rule_id（如 ZH-EN-RULE#42）、module_name、confidence_score（仅用于记录，不用于自评）。
· 2. 审计追踪（Audit Trace）的不可变存储：
  · 定义 AuditRecord：包含 timestamp、isa_instruction、input_hash、output_snapshot、evidence_chain（证据ID列表）。
  · 规定 audit_trace.jsonl 的格式（每行一条记录，便于追加）。
· 3. LLM交互的证据强制要求：
  · 提供 TRANSLATE_SEGMENT 的 Prompt 模板片段，强制LLM输出结构化JSON：{"translation": "...", "decisions": [{"term": "X", "chosen": "Y", "basis": "Z"}]}。
· 4. 验证规则（Verification Rules）：
  · 定义何为“有效证据”（不能为空，必须引用存在的规则ID）。
  · VERIFY 指令将基于该Schema执行校验，若证据缺失则直接触发 RAISE_FLAG。

---

🧠 文档二：CACHE_STRATEGY.md（确定性缓存策略）

目标：消除LLM非确定性，确保同一输入在不同时间、环境下的输出严格一致。

· 1. 缓存键（Cache Key）生成算法：
  · 公式：cache_key = sha256( source_text + glossary_snapshot_hash + entity_table_hash + model_endpoint + model_version )。
  · 强调必须序列化术语表为规范JSON（排序键），避免字典顺序不同导致哈希抖动。
· 2. 缓存存储后端（Phase 1原型）：
  · 建议使用 diskcache 库（基于SQLite）或简单文件系统（/cache/ 目录）。
  · 提供 CacheClient 接口：get(key) -> TranslationResult，set(key, result)。
· 3. 缓存作用域与失效策略：
  · 作用域：仅缓存 TRANSLATE_SEGMENT 和 REPAIR_SEGMENT 的原子操作，不缓存全文档（避免颗粒度过大导致频繁失效）。
  · 失效策略：手动失效（当用户明确更新术语表时，提供CLI命令清除缓存），不设TTL（因为技术文档翻译是静态事实）。
· 4. 与策略引擎的交互：
  · 若策略优先级发生变化（如策略堆栈被修改），必须自动变更缓存键中的 policy_snapshot_hash，确保旧缓存不被误用。

---

🔗 文档三：ANCHOR_RESOLUTION.md（锚点与交叉引用重写算法）

目标：保证翻译后Markdown内部链接（[见](#old-heading)）依然指向正确位置。

· 1. 解析阶段（Analyze）的预处理：
  · 遍历Markdown AST（使用 markdown-it-py），提取所有 heading 节点。
  · 生成 双向映射表：原文Slug -> 原文标题文本，以及 原文标题文本 -> 译文预测Slug（初始占位）。
· 2. 翻译阶段的“锚点代币”保护机制：
  · 在将标题内容送入 TRANSLATE_SEGMENT 前，将标题文本替换为特殊占位符（如 __HEADER_1__），防止LLM随意改动锚点结构。
  · 翻译完成后，根据译文的实际标题，生成 译文Slug（复刻GitHub的slugify逻辑，处理Unicode与大小写）。
· 3. 重写阶段（Emit前强制Pass）：
  · 遍历AST中所有 link 节点，若 href 以 # 开头：
    · 在“译文Slug映射表”中查找对应的新锚点。
    · 若找不到（标题被LLM省略），则降级为文本引用（保留原文链接文本并加粗提示）并记录 WARNING 审计事件。
· 4. 边缘情况处理：
  · 重复标题（如多个 # 引言）：采用 index 后缀（#引言 -> #introduction，#introduction-1）。
  · 代码块内的锚点：不进行重写（保持原样）。

---

🗓️ 执行建议：起草顺序与协作方式

1. 先写 EVIDENCE_SCHEMA.md（30分钟）：它是数据契约，定义好后 CACHE 和 ANCHOR 的审计记录才能定型。
2. 再写 CACHE_STRATEGY.md（20分钟）：逻辑相对独立，重点画好“缓存命中时的短路流程图”。
3. 最后写 ANCHOR_RESOLUTION.md（40分钟）：这是算法最复杂的部分，需要附带一个具体的 输入/输出 Markdown示例进行演示。

生成指令：我可以直接为你生成这三份文档的完整 Markdown 源码（包含Mermaid流程图与代码示例）。如果你同意，我现在就从 EVIDENCE_SCHEMA.md 开始输出，你只需复制保存即可开始Phase 0编码。或者，如果你希望我先输出其中某一篇的详细审查，也请告知。

---

Here are the three meticulously detailed specification documents, ready to be saved directly into your tra-prototype/docs/ directory. They are designed to serve as the single source of truth for the prototype's data contracts, determinism guarantees, and structural integrity logic.

---

Document 1: docs/EVIDENCE_SCHEMA.md

```markdown
# Evidence Schema & Audit Trail Specification
**Version:** 1.0  
**Status:** Approved for Prototype Phase 0  
**Applies To:** TRA L3 (Strict) & L4 (Forensic) Conformance

## 1. Core Principle
Every translation decision generated by the engine must be **atomically traceable** to either a static rule, a module directive, or a specific LLM rationale. The system **MUST NOT** self-score the quality of the translation; it merely records the *evidence* used to produce it. Validation (`VERIFY`) checks the existence and validity of this evidence, not the subjective beauty of the text.

## 2. Evidence Data Models (Pydantic Blueprint)

### 2.1 Evidence Type Enum
```python
from enum import Enum

class EvidenceType(str, Enum):
    TERM_MATCH = "term_match"               # Glossary hit
    ENTITY_PRESERVED = "entity_preserved"   # Product/CLI/API kept untranslated
    POLICY_ARBITRATION = "policy_arbitration" # Conflict resolved via priority stack
    STRUCTURAL_MAPPING = "structural_mapping" # Headings/lists mapping
    LLM_DECISION = "llm_decision"           # Rationale provided by the LLM in structured output
    HUMAN_OVERRIDE = "human_override"       # Manual intervention
    CONTEXTUAL_INFERENCE = "contextual_inference" # Inferred from surrounding text
```

2.2 Evidence Source & Record

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict

class EvidenceRecord(BaseModel):
    id: str = Field(..., description="UUID or hash of the record")
    type: EvidenceType
    rule_id: Optional[str] = Field(None, description="e.g., 'ZH-EN-RULE#042'")
    module: str = Field(..., description="e.g., 'modules.zh_en'")
    source_span: str = Field(..., description="Original text segment")
    target_span: str = Field(..., description="Translated text segment")
    rationale: str = Field(..., description="Human-readable explanation of the decision")
    confidence_note: Optional[float] = Field(None, description="Recorded but never used for scoring; for debugging only")
```

2.3 Audit Record (Immutable Trace)

```python
class AuditRecord(BaseModel):
    sequence_id: int
    timestamp: datetime
    isa_instruction: str  # ANALYZE_DOCUMENT, TRANSLATE_SEGMENT, etc.
    input_hash: str       # Cache key relevant to this operation
    artifact_snapshot: Dict[str, any]  # Minimal state delta
    evidence_chain: List[str]  # List of EvidenceRecord IDs
    flags_raised: Optional[List[str]] = None
```

3. LLM Interaction Protocol (Crucial for L3)

When TRANSLATE_SEGMENT invokes the LLM, the system prompt must force the LLM to return a structured JSON object. This ensures VERIFY can extract evidence.

Required LLM Output Format:

```json
{
  "translation": "The actual translated text.",
  "decisions": [
    {
      "term": "establishment",
      "chosen": "成立",
      "basis": "Matched module ZH-EN Rule #42: Legal context requires formal nominalization."
    },
    {
      "entity": "ACME Corp",
      "action": "preserved",
      "basis": "Entity table mapping; proper noun."
    }
  ],
  "structural_notes": "Retained heading level 2."
}
```

4. Storage & VERIFY Enforcement

· Storage: All records are appended to audit_trace.jsonl (JSON Lines) to prevent corruption and enable streaming.
· Verification Rules (Executed by VERIFY_OUTPUT):
  1. Every TRANSLATE_SEGMENT must produce exactly one AuditRecord.
  2. The evidence_chain cannot be empty. If empty, VERIFY raises a BLOCKING flag.
  3. Every EvidenceRecord must cite a valid rule_id or a recognized module. Unknown rules trigger a WARNING.
  4. Routing MUST NOT use confidence_note for any decision — it is recorded for debugging only, never read by VERIFY or REPAIR (this honors TRA's "never self-score" invariant). Low-evidence routing, if needed, is gated solely on evidence *presence* (empty evidence_chain → RAISE_FLAG), never on a numeric score.

```

---

### Document 2: `docs/CACHE_STRATEGY.md`

```markdown
# Deterministic Cache Strategy
**Version:** 1.0  
**Status:** Approved for Prototype Phase 1  
**Applies To:** `TRANSLATE_SEGMENT` & `REPAIR_SEGMENT` Instructions

## 1. The Problem
LLMs are inherently non-deterministic. Temperature=0 reduces variance but does not eliminate it (floating-point errors, batched inference, model version updates). To satisfy TRA's "deterministic state machine" invariant, we must externalize the decision logic to a content-addressable cache.

## 2. Cache Key Generation (The "Canonical Hash")
The cache key must represent the **entirety of the translation context**. It is computed using SHA-256 over a normalized, sorted JSON payload.

**Key Components:**
```python
import hashlib
import json

def generate_cache_key(source_text: str, context: dict) -> str:
    canonical_payload = {
        "source": source_text,
        "glossary_hash": hash_sorted_dict(context["glossary"]),
        "entity_hash": hash_sorted_dict(context["entities"]),
        "model_endpoint": context["model_endpoint"],
        "model_version": context["model_version"],
        "policy_stack_hash": hash_sorted_list(context["active_policy_priorities"])
    }
    # Sort keys to ensure reproducibility
    sorted_json = json.dumps(canonical_payload, sort_keys=True)
    return hashlib.sha256(sorted_json.encode('utf-8')).hexdigest()

def hash_sorted_dict(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
```

3. Cache Storage Backend

Phase 1 Recommendation: Use diskcache (SQLite-backed) for simplicity.

```python
import diskcache

class TranslationCache:
    def __init__(self, cache_dir="./cache"):
        self.cache = diskcache.Cache(cache_dir)
    
    def get(self, key: str):
        return self.cache.get(key)
    
    def set(self, key: str, value: dict):
        # value contains: {"translation": str, "evidence": list, "timestamp": iso}
        self.cache.set(key, value, expire=None)  # No TTL for deterministic facts
    
    def invalidate(self, pattern: str = None):
        # CLI use-case: Clear cache if glossary updated
        if pattern:
            self.cache.delete(pattern)
        else:
            self.cache.clear()
```

4. Cache Scope & Granularity

· DO NOT cache the entire document translation. Changes to one segment would invalidate the whole document, reducing efficacy.
· DO cache atomic operations: TRANSLATE_SEGMENT (single block of text) and REPAIR_SEGMENT (single fix operation).
· Cache Eviction: Manual only. The user must explicitly run tra cache-clear if they update the config.yaml or glossary. Automatic invalidation occurs via the policy_stack_hash changing.

5. Interaction with Policy Engine

If the Priority Stack is modified (e.g., changing FACTUAL_INTEGRITY vs FLUENCY weights), the policy_stack_hash changes. Therefore, even with the same source text, the cache automatically misses, forcing the engine to re-translate under the new rules. This ensures the cache does not accidentally hide logic updates.

```

---

### Document 3: `docs/ANCHOR_RESOLUTION.md`

```markdown
# Anchor & Cross-Reference Resolution Algorithm
**Version:** 1.0  
**Status:** Approved for Prototype Phase 1  
**Applies To:** `ANALYZE_DOCUMENT` & `EMIT_OUTPUT` Phases

## 1. The Problem
Technical Markdown frequently contains internal anchors (e.g., `[See setup](#system-setup)`). If a heading changes from `# System Setup` to `# 系统安装` (System Installation), the anchor `#system-setup` must be updated to `#%E7%B3%BB%E7%BB%9F%E5%AE%89%E8%A3%85` (or transliterated) to maintain navigability. This is a structural requirement for L2/L3 conformance.

## 2. Phase 1: Analysis & Registry Building (Before Translation)
- **Parsing**: Use `markdown-it-py` to traverse the AST.
- **Extraction**: For every `heading` node (level 1-6), record:
  - `original_text`: The literal heading text.
  - `original_slug`: The GitHub-style slug (e.g., `# Hello World!` -> `hello-world`).
  - `placeholder`: Assign a unique token (e.g., `__HEADER_001__`).

```python
class AnchorRegistry:
    def __init__(self):
        self.map_original_to_placeholder = {}
        self.map_placeholder_to_translated_slug = {}
        self.slug_counter = 0

    def register(self, text: str):
        slug = self._generate_slug(text)
        placeholder = f"__HEADER_{self.slug_counter:03d}__"
        self.map_original_to_placeholder[text] = placeholder
        self.slug_counter += 1
        return placeholder
```

3. Phase 2: Translation with "Token Protection"

Before sending a heading to TRANSLATE_SEGMENT, replace the heading text with its placeholder.

· Input to LLM: ### __HEADER_001__ instead of ### System Architecture.
· Why: This prevents the LLM from dropping, splitting, or drastically rephrasing the structural headline. The LLM translates the content inside the placeholder if necessary, but the token remains intact.
· After translation, the __HEADER_001__ is replaced with the translated text.

4. Phase 3: Slugification & Conflict Resolution

After translation, we generate the new slug for the translated heading. We must handle duplicates strictly.

```python
def resolve_slug(translated_text: str, existing_slugs: set) -> str:
    base_slug = generate_github_slug(translated_text)  # Lowercase, trim, replace spaces with '-'
    
    if base_slug not in existing_slugs:
        existing_slugs.add(base_slug)
        return base_slug
    
    # Duplicate found: Append -1, -2, etc.
    counter = 1
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1
    final = f"{base_slug}-{counter}"
    existing_slugs.add(final)
    return final
```

5. Phase 4: AST Link Rewriting (The "Healing Pass")

During the EMIT phase, traverse the AST again.

1. Find all link nodes with href starting with #.
2. Look up the original_slug in the AnchorRegistry.
3. If found: Replace the href with the new translated_slug.
4. If not found (heading was deleted or changed completely by the LLM):
   · Keep the href as-is.
   · Inject a [LINK_BROKEN] tag into the link text.
   · Log a WARNING to the AuditRecord with details.

6. Special Cases

· Code Blocks: Do not parse or rewrite anchors inside fenced code blocks ( ``` ). Their contents are considered literal.
· HTML Anchors: If an inline HTML anchor (<a name="...">) exists, treat it as an alias and map it to the new slug.
· Empty Headings: If a heading is empty (e.g., # ), skip it and do not generate a placeholder.

7. Example Workflow

Original (EN) Translated (ZH) Slug (EN) Slug (ZH) Link Update
# Setup # 安装 setup 安装 [guide](#setup) -> [guide](#安装)
# Setup (dup) # 配置 setup 配置-1 [guide](#setup) -> [guide](#配置-1)

```