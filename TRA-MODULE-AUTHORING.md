# TRA Module Authoring Guide

**How to author a new Language / Domain / Formatting module for the TRA
prototype engine.**

This guide is the companion to `TRA-MODULE-ZH-EN.md` (which is the
linguistic spec for the bundled ZH↔EN module). Here we focus on the
*engineering* contract: what interfaces a module must satisfy, how to
register it, and how to test it.

---

## 1. The Module Contract (Spec §9)

A TRA module is a plug-in that extends runtime behavior **without touching
the Kernel or ISA**. Three kinds of module exist:

| Kind | Purpose | Example |
|:--|:--|:--|
| `language` | Glossary, style profile, rule layer for a language pair | `ZH-EN` (bundled) |
| `domain` | Domain-specific terminology + forbidden mappings | `security-advisory` (future) |
| `formatting` | Output formatting rules (e.g., CJK punctuation) | `halfwidth` (future) |

Every module satisfies the `LanguageModuleProtocol` defined in
`tra/modules/base.py`:

```python
class LanguageModuleProtocol(Protocol):
    def get_glossary_mappings(self) -> dict[str, str]: ...
    def get_style_profile(self) -> StyleProfile: ...
    def apply_rules(self, source: str, direction: str) -> str: ...
    def is_forbidden(self, source: str, target: str) -> bool: ...
    def get_forbidden_targets(self) -> dict[str, str]: ...
    def entity_type_hint(self, token: str) -> EntityType | None: ...
    def apply_zh_rules(self, source: str) -> str: ...
```

The `ModuleInterface` dataclass in `tra/modules/registry.py` is a
runtime wrapper that carries these as `Callable` fields. Use
`as_interface()` on your module class to produce a `ModuleInterface`
that the registry can store.

---

## 2. The 7 Required Methods

### 2.1 `get_glossary_mappings() -> dict[str, str]`

Returns the canonical terminology mappings for this module. Keys are
source-language terms; values are target-language canonical translations.

**Invariant**: mappings are *binding* — `VERIFY_OUTPUT` will flag any
source term that appears untranslated in the target as a BLOCKING
diagnostic (severity arbitrated by the PolicyResolver, TRA-072).

**Example** (from `tra/modules/zh_en.py`):
```python
GLOSSARY: dict[str, str] = {
    "成立": "Confirmed",
    "执行环境": "execution environment",
    "高度可信": "highly credible",
    "可能": "may",
    ...
}

def get_glossary_mappings(self) -> dict[str, str]:
    return dict(GLOSSARY)
```

### 2.2 `get_style_profile() -> StyleProfile`

Returns the `StyleProfile` for this language pair. This is a Pydantic
model with fields: `voice`, `sentence_complexity`, `epistemic_mapping`,
`punctuation_rules`.

**Critical (TRA-F4-006)**: must NOT return `None`. The
`ModuleRegistry.register()` method validates the return shape at
registration time and raises a clear `TypeError` if it's `None`. An
opaque Pydantic `ValidationError` from `RuntimeContext` construction
is the symptom of a `None` return.

**Example**:
```python
def get_style_profile(self) -> StyleProfile:
    return StyleProfile(
        voice="technical",
        sentence_complexity="moderate",
        epistemic_mapping={"成立": "Confirmed", "高度可信": "highly credible"},
        punctuation_rules={"preserve_fullwidth_for_zh": "true"},
    )
```

### 2.3 `apply_rules(source: str, direction: str) -> str`

Pre/post-processing hook for the source text. Called BEFORE the
deterministic substitution passes (glossary + epistemic lexicon).

**Use this for**: parataxis→hypotaxis transformation, nominalization
verbalization, punctuation normalization.

**Example**: see `ZHENModule.apply_zh_rules` for the topic-comment
rule layer (`系统成立` → `The system is Confirmed`).

### 2.4 `is_forbidden(source: str, target: str) -> bool`

Returns `True` if `target` is a known drift mapping for `source`.
`VERIFY_OUTPUT` checks every forbidden target and raises a BLOCKING
diagnostic (severity arbitrated by the PolicyResolver) if any appears
in the translation.

**Example**:
```python
FORBIDDEN_TARGETS: dict[str, str] = {
    "成立": "Valid/True/Correct",       # never "Valid", "True", "Correct"
    "执行环境": "runtime",              # never "runtime"
    "高度可信": "indisputably true",    # never "indisputably true"
}

def is_forbidden(self, source: str, target: str) -> bool:
    banned = FORBIDDEN_TARGETS.get(source)
    return banned is not None and target in banned.split("/")
```

### 2.5 `get_forbidden_targets() -> dict[str, str]`

Returns the full forbidden-targets map. Used by `VERIFY_OUTPUT` to
scan the target for any drift target.

### 2.6 `entity_type_hint(token: str) -> EntityType | None`

Returns an `EntityType` hint for a token, or `None` if the module has
no authoritative classification.

**TRA-038 (round 4)**: if this returns `None` AND the token matches
multiple entity patterns (e.g., both `ACRONYM_RE` and `PRODUCT_RE`),
`build_entity_table` logs an `ENTITY_AMBIGUITY` entry to
`unresolved_ambiguities`. The token is still treated as an Entity
(immutable) — the ambiguity is surfaced to the L4 audit trail.

**Example**:
```python
def entity_type_hint(self, token: str) -> EntityType | None:
    if token in ("RustVMM", "Firecracker", "Containerd"):
        return EntityType.PRODUCT
    return None  # no authoritative hint
```

### 2.7 `apply_zh_rules(source: str) -> str`

The ZH-specific rule layer. Called by `_rule_translate` BEFORE the
epistemic lexicon and glossary substitution passes. This is where
topic-comment forms (`系统成立` → `The system is Confirmed`) are
resolved so the atomic `成立 → Confirmed` substitution doesn't split
them apart.

For non-ZH modules, this can be a no-op (`return source`).

---

## 3. Registering a Module

### 3.1 The Module Class

Author your module as a class implementing all 7 methods. Use
`ZHENModule` (`tra/modules/zh_en.py`) as the template.

### 3.2 The `as_interface()` Method

Your module class should provide an `as_interface()` method that
returns a `ModuleInterface` wrapping its callables:

```python
from tra.modules.registry import ModuleInterface

class FREnModule:
    ...
    def as_interface(self) -> ModuleInterface:
        return ModuleInterface(
            name="fr_en",
            kind="language",
            get_glossary_mappings=self.get_glossary_mappings,
            get_style_profile=self.get_style_profile,
            apply_rules=self.apply_rules,
            is_forbidden=self.is_forbidden,
            get_forbidden_targets=self.get_forbidden_targets,
            entity_type_hint=self.entity_type_hint,
            apply_zh_rules=lambda text: text,  # no-op for non-ZH
            metadata={"direction": "FR -> EN"},
        )
```

### 3.3 Registering via the Registry

There are two ways to register:

**Option A: Add to `build_default_registry()`** (in
`tra/modules/registry.py`):
```python
def build_default_registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(ZHENModule().as_interface())
    registry.register(FREnModule().as_interface())  # your new module
    return registry
```

**Option B: Register at runtime** (in user code):
```python
from tra.modules.registry import build_default_registry

registry = build_default_registry()
registry.register(FREnModule().as_interface())
kernel = TRAKernel(cfg, registry=registry)
```

### 3.4 Registration Validation (TRA-097, TRA-098, TRA-F4-006)

`register()` performs 3 validations:

1. **Protocol check (TRA-097)**: the module must satisfy
   `LanguageModuleProtocol`. Missing methods raise `TypeError`.
2. **Style profile check (TRA-F4-006)**: `get_style_profile()` must
   return a non-`None` value. `None` raises `TypeError` with an
   actionable message pointing to `ZHENModule` as the template.
3. **Duplicate/conflict check (TRA-098)**: duplicate names raise
   `ValueError`; conflicting directions (two modules with the same
   `FR -> EN`) raise `ValueError`.

### 3.5 CLI Usage (TRA-099)

The CLI's `translate` command auto-builds the default registry and
passes it to `TRAKernel`. The kernel's `_select_module` (TRA-F4-007)
matches by full direction (e.g., `FR -> EN`), falling back to
source-language-only if no exact match exists.

```bash
python -m tra_cli translate input.md --lang fr-en --level L3
```

The `--lang fr-en` is normalized to `FR -> EN` by `_normalize_language_pair`.

---

## 4. Testing Your Module

### 4.1 Unit Tests

Test each method in isolation:

```python
def test_fr_en_glossary():
    mod = FREnModule()
    mappings = mod.get_glossary_mappings()
    assert "bonjour" in mappings
    assert mappings["bonjour"] == "hello"
```

### 4.2 Integration Tests

Test the module through the kernel:

```python
def test_fr_en_translation_via_kernel(tmp_path):
    from tra.config import BootstrapConfig
    from tra.kernel import TRAKernel
    from tra.memory import ConformanceLevel
    from tra.modules.registry import build_default_registry

    cfg = BootstrapConfig(
        language_pair="FR -> EN", domain="test",
        conformance_level=ConformanceLevel.L3_STRICT,
        ...
    )
    registry = build_default_registry()
    kernel = TRAKernel(cfg, registry=registry)
    target = kernel.run("bonjour le monde")
    assert "hello" in target.lower()
```

### 4.3 Benchmark Cases

Add a benchmark case to `tests/benchmark/cases/sft.jsonl`:

```json
{"id": "T-FR-01", "category": "T", "source": "bonjour", "level": "L3_STRICT", "must_contain": ["hello"], "must_not_contain": [], "zero_blocking": true, "description": "FR-EN glossary: bonjour → hello."}
```

### 4.4 The 4 Critical Invariants

Your module must not violate any of the 4 critical invariants:

1. **Canonical terminology is exact** — glossary mappings are binding;
   never weaken epistemic certainty (`成立 → Confirmed`, never "Valid").
2. **Entities are immutable** — `entity_type_hint` should return a
   concrete type for known entities; `None` triggers ambiguity logging.
3. **VERIFY_OUTPUT never self-scores** — `get_style_profile` is for
   debugging only; `VERIFY_OUTPUT` never reads `confidence_note`.
4. **REPAIR_SEGMENT is surgical** — repair must not introduce new
   BLOCKING violations.

---

## 5. Checklist for a New Module

- [ ] Class implements all 7 `LanguageModuleProtocol` methods
- [ ] `get_style_profile()` returns a non-`None` `StyleProfile`
- [ ] `as_interface()` returns a `ModuleInterface` with correct `metadata.direction`
- [ ] `entity_type_hint()` returns concrete types for known entities
- [ ] `is_forbidden()` + `get_forbidden_targets()` enumerate drift targets
- [ ] Unit tests for each method
- [ ] Integration test through `TRAKernel(cfg, registry=registry)`
- [ ] Benchmark case in `tests/benchmark/cases/sft.jsonl`
- [ ] Module added to `build_default_registry()` (if it should be a default)
- [ ] All 4 quality gates green: `ruff format --check . && ruff check . && mypy --strict tra && pytest tests`

---

## 6. Reference

- `TRA-MODULE-ZH-EN.md` — linguistic spec for the bundled ZH↔EN module
- `tra/modules/zh_en.py` — reference implementation (the template)
- `tra/modules/base.py` — `LanguageModuleProtocol` definition
- `tra/modules/registry.py` — `ModuleInterface`, `ModuleRegistry`,
  `build_default_registry()`
- `tra/kernel.py:_select_module` — how the kernel picks a module by
  language pair (TRA-F4-007: full-direction match preferred)
- `tra/isa.py:_module` — how ISA functions access the active module
- `docs/audit/round4/track_f4_findings.md` — Round 4 audit findings
  for the module system (TRA-096/097/098/099/100 + F4-006/F4-007)
