# Track F3 — Module Extension Safety Audit (Round 3, NEW)

**HEAD audited:** `b783745`
**Methodology:** Stub module authoring + registry edge-case testing + Protocol audit
**Baseline:** N/A (new track — no Round 1 / Round 2 equivalent)
**Audit artifacts:**
- Stub module: `/tmp/fren_module.py` (FrENModule)
- Test scripts: `/tmp/test_fren.py`, `/tmp/test_default_registry.py`, `/tmp/test_fren_direct.py`, `/tmp/test_broken_module.py`, `/tmp/test_partial_broken.py`, `/tmp/test_registry_edge.py`, `/tmp/test_protocol_methods.py`

## Summary

- **Findings:** 11 total (2 BLOCKING / 5 WARNING / 4 INFO)
- **Stub module authored:** YES — `FrENModule` satisfies `LanguageModuleProtocol` (`isinstance(FrENModule(), LanguageModuleProtocol) == True`) and provides 5 FR→EN glossary mappings, a minimal `StyleProfile`, a no-op `apply_rules`, `kind = "language"`, `metadata = {"direction": "FR -> EN"}`, and an `as_interface()` adapter returning a `ModuleInterface`.
- **Sanctioned path (`as_interface()` + registry):** **BROKEN** — `TRAKernel(cfg, registry=registry)` raises `pydantic.ValidationError` at construction time. See F3-BLOCKING-1.
- **Bypass path (register full module object directly):** WORKS — `kernel.ctx.module.__class__.__name__ == "FrENModule"` and the kernel produces the expected FR→EN glossary substitution. This is the path the existing `test_outstanding_findings.py::TestTRA002RegistryWiring` actually exercises.
- **Kernel/ISA immutability:** **VERIFIED** — `git diff -- tra-prototype/tra/kernel.py tra-prototype/tra/isa.py` is empty at HEAD `b783745` (and remained empty throughout Track F3; all F3 work was confined to `/tmp/`).
- **Protocol enforcement:** `runtime_checkable` decorator is present on `LanguageModuleProtocol`, but the `ModuleRegistry.register()` API does NOT call `isinstance(...)` — enforcement happens implicitly via Pydantic's `RuntimeContext.module` field validation, which only fires inside `TRAKernel.__init__` (not at `register()` time).

## Findings

---

### F3-BLOCKING-1 — `as_interface()` adapter produces a `ModuleInterface` that fails the `LanguageModuleProtocol` validation

**Severity:** BLOCKING
**Spec claim violated:** SKILL.md §6 "Extending (the only sanctioned path)":
```python
registry = build_default_registry()
registry.register(my_module.as_interface())
kernel = TRAKernel(cfg, registry=registry)   # <-- crashes here
```

**Evidence (reproduced at HEAD `b783745`):**

`/tmp/test_fren.py` step 3:
```
TRAKernel(cfg, registry=registry)
  -> pydantic_core._pydantic_core.ValidationError: 1 validation error for RuntimeContext
     module
       Input should be an instance of LanguageModuleProtocol
       [type=is_instance_of,
        input_value=ModuleInterface(name='fr_en', kind='language', ...),
        input_type=ModuleInterface]
```

The default registry is ALSO broken — `/tmp/test_default_registry.py`:
```
registry.all() = [('zh_en', 'ModuleInterface')]
  RAISED: ValidationError: 1 validation error for RuntimeContext
  module
    Input should be an instance of LanguageModuleProtocol
```

**Root cause:** `LanguageModuleProtocol` (tra/modules/base.py:14) is `@runtime_checkable` and requires 7 callable members (`apply_rules`, `apply_zh_rules`, `entity_type_hint`, `get_forbidden_targets`, `get_glossary_mappings`, `get_style_profile`, `is_forbidden`). `ModuleInterface` (tra/modules/registry.py:13) is a `@dataclass` that carries only 3 of them as `Callable` fields (`get_glossary_mappings`, `get_style_profile`, `apply_rules`) plus `name`, `kind`, `metadata`. `isinstance(ModuleInterface(...), LanguageModuleProtocol)` returns `False` because 4 methods are missing (`apply_zh_rules`, `entity_type_hint`, `get_forbidden_targets`, `is_forbidden`). Pydantic v2 enforces the Protocol via `is_instance_of` validation on the `RuntimeContext.module` field (tra/memory.py:216, typed `LanguageModuleProtocol | None`).

**Impact:** The spec's central design claim — "new language/domain/formatting behavior goes through the module registry — never by editing the Kernel or ISA" — is false at HEAD. The documented example code in SKILL.md §6 cannot run. A user following the spec authoring template will hit this ValidationError on the very first `TRAKernel(cfg, registry=...)` call.

**Fix recommendation (out of scope for audit):** Either
(a) add the four missing `Callable` fields to `ModuleInterface` and wire them in `ZHENModule.as_interface()` / `FrENModule.as_interface()`, OR
(b) make `ModuleRegistry.register()` accept the full module object (not the adapter) and have `_select_module` return the original instance — deprecate `as_interface()` entirely, OR
(c) loosen `RuntimeContext.module` typing back to `Any` (regresses TRA-043).

---

### F3-BLOCKING-2 — `ModuleInterface` does not expose the methods the ISA actually calls

**Severity:** BLOCKING (separate symptom of the F3-BLOCKING-1 root cause)
**Spec claim violated:** SKILL.md §6: "The selected module is stored on `ctx.module` and read by every ISA function via the `_module(ctx)` helper".

**Evidence:** `tra/isa.py` reads from `ctx.module` via `_module(ctx)` (isa.py:203-207) and calls:

| ISA call site | Method called | On `ModuleInterface`? |
|---|---|---|
| `build_glossary` (isa.py:223) | `mod.get_glossary_mappings()` | ✓ present |
| `build_glossary` (isa.py:228) | `mod.is_forbidden(src, tgt)` | ✗ **MISSING** |
| `_forbidden_from_module` (isa.py:288) | `mod.get_forbidden_targets()` | ✗ **MISSING** |
| `build_entity_table` (isa.py:327) | `mod.entity_type_hint(token)` | ✗ **MISSING** |
| `translate_segment` (isa.py:413) | `ctx.module` passed to `_rule_translate` | — passed as object |
| `verify_output` (indirectly) | via `_forbidden_from_module` | ✗ **MISSING** |

`/tmp/test_protocol_methods.py` confirms:
```
LanguageModuleProtocol methods/attrs: ['apply_rules', 'apply_zh_rules',
  'entity_type_hint', 'get_forbidden_targets', 'get_glossary_mappings',
  'get_style_profile', 'is_forbidden']
ModuleInterface (ZHENModule.as_interface) attrs: ['apply_rules',
  'get_glossary_mappings', 'get_style_profile', 'kind', 'metadata', 'name']
isinstance(zh_iface, LanguageModuleProtocol): False
Methods MISSING from ModuleInterface: ['apply_zh_rules', 'entity_type_hint',
  'get_forbidden_targets', 'is_forbidden']
```

**Impact:** Even if Pydantic's `is_instance_of` check were removed, the kernel would crash on the first `build_glossary` call with `AttributeError: 'ModuleInterface' object has no attribute 'is_forbidden'`. The `as_interface()` adapter is structurally incomplete with respect to the actual ISA call surface — it covers only the "happy path" of glossary lookup but omits forbidden-targets / entity-hints / rule-layer dispatch.

**Fix recommendation:** same as F3-BLOCKING-1 — the four missing methods must be carried by `ModuleInterface` (or `as_interface()` must be deprecated in favour of registering the original module object).

---

### F3-WARNING-1 — `ModuleRegistry.register()` does NOT validate against `LanguageModuleProtocol`

**Severity:** WARNING
**Spec claim violated:** Implicit — TRA-043 introduced `@runtime_checkable` precisely so structural validation could happen, but the registry never invokes it.

**Evidence:** `/tmp/test_broken_module.py`:
```
BrokenModule isinstance(LanguageModuleProtocol)? False
registry.register() accepted BrokenModule: ['broken_en']
TRAKernel() RAISED AttributeError: 'BrokenModule' object has no attribute 'get_style_profile'
```

`ModuleRegistry.register()` (tra/modules/registry.py:31-32) is a one-liner:
```python
def register(self, module: ModuleInterface) -> None:
    self._modules[module.name] = module
```

No `isinstance(module, LanguageModuleProtocol)` check, no method-presence check, no type check (the `ModuleInterface` type annotation is a hint only — Python does not enforce it). A completely broken module is silently stored.

**Failure mode:** the error surfaces much later, in one of two ways:
- If the module is missing `get_style_profile` → `AttributeError` in `TRAKernel.__init__` (kernel.py:124 calls `module.get_style_profile()` before constructing `RuntimeContext`).
- If the module has `get_style_profile` but is missing other Protocol methods → `pydantic.ValidationError` from `RuntimeContext` construction (tra/memory.py:216 enforces `LanguageModuleProtocol | None`).

Neither error message mentions the Protocol by name or enumerates which methods are missing. A user authoring a new module gets an opaque `AttributeError` or `ValidationError` with no actionable diagnostic.

**Fix recommendation:** add an explicit `isinstance` check in `register()`:
```python
def register(self, module: ModuleInterface) -> None:
    if not isinstance(module, LanguageModuleProtocol):
        missing = sorted(set(_PROTOCOL_METHODS) - set(dir(module)))
        raise TypeError(
            f"Module {module.name!r} does not satisfy LanguageModuleProtocol "
            f"(missing: {missing})"
        )
    self._modules[module.name] = module
```

---

### F3-WARNING-2 — Duplicate registration (same `module.name`) silently overwrites

**Severity:** WARNING

**Evidence:** `/tmp/test_registry_edge.py` step 1:
```
after m1: names = ['fr_en']
after m2 (same name): names = ['fr_en']
reg.get('fr_en') is m2? True
reg.get('fr_en') is m1? False
```

`register()` does `self._modules[module.name] = module` — a plain dict assignment. A second module with the same `name` silently replaces the first. There is no warning, no error, no audit trail.

**Impact:** If a third-party module author accidentally re-uses `"zh_en"` as the `name` (e.g., a fork that extends ZHENModule), their module silently shadows the bundled one. The kernel will pick whichever was registered last, with no signal that the bundled module was displaced.

**Fix recommendation:** raise on duplicate name, or at least log a WARNING; provide a `replace=True` kwarg for the explicit-override case.

---

### F3-WARNING-3 — Conflicting directions are not detected

**Severity:** WARNING

**Evidence:** `/tmp/test_registry_edge.py` step 2:
```
registry modules: [('fr_en_a', 'FR -> EN'), ('fr_en_b', 'FR -> EN')]
FR modules found: ['fr_en_a', 'fr_en_b']
first match (kernel picks this): fr_en_a
```

The kernel's `_select_module` (kernel.py:130-155) iterates `registry.all()` and returns the FIRST module whose `metadata.direction` source-language prefix matches. If two modules both declare `"FR -> EN"`, the first-registered one wins silently. There is no detection of conflicting directions and no warning to the user.

**Impact:** non-deterministic module selection from the user's perspective — if registration order changes (e.g., a plugin loader iterates a directory in filesystem-dependent order), the kernel may pick a different module on different runs.

**Fix recommendation:** either reject duplicate directions at `register()` time, or document the "first-registered wins" rule explicitly in SKILL.md §6.

---

### F3-WARNING-4 — No `unregister()` API

**Severity:** WARNING (testability / hot-reload gap)

**Evidence:** `/tmp/test_registry_edge.py` step 3:
```
hasattr(reg, 'unregister'): False
hasattr(reg, 'remove'):     False
dir(reg) public methods: ['all', 'get', 'register']
```

`ModuleRegistry` exposes only `register`, `get`, `all`. There is no way to remove a module from a registry without directly mutating `reg._modules` (a private attribute). This makes test isolation harder — a test that registers a stub module pollutes the registry for any subsequent code that holds the same registry instance.

**Mitigation:** `build_default_registry()` returns a fresh instance per call (see F3-INFO-1), so test fixtures that call it are isolated. But test code that builds a single `ModuleRegistry()` and shares it across tests cannot easily undo a registration.

**Fix recommendation:** add `unregister(name: str) -> ModuleInterface | None` mirroring the standard dict-pop pattern.

---

### F3-WARNING-5 (TRA-002 follow-up) — CLI does not pass a registry to `TRAKernel`

**Severity:** WARNING
**Spec claim violated:** SKILL.md §6 implies the registry is the user-facing extension point, but the user-facing CLI does not use it.

**Evidence:** `tra_cli.py:107`:
```python
kernel = TRAKernel(cfg, interactive=interactive)
```

No `registry=` argument. Grep of `tra_cli.py` for `registry|build_default|ModuleRegistry` returns **no matches**. The `translate` command accepts `--lang`, `--level`, `--output`, `--interactive` — there is no `--registry` flag, no `--module-path` flag, no plugin-discovery hook.

**Impact:** A user who authors and registers a custom FrENModule via the Python API has no way to invoke it via the CLI. The CLI always falls back to `ZHENModule()` (the no-registry path). Combined with F3-BLOCKING-1 (which makes the registry path crash anyway), this means **the only working entry point at HEAD is the no-registry CLI path, which is hard-coded to ZHENModule.**

**Fix recommendation:** add a `--module` / `--registry` flag to `translate` that accepts a dotted Python path (e.g., `--module my_pkg.fr_en:FrENModule`) and constructs + registers the module before invoking the kernel. Combined with the F3-BLOCKING-1 fix, this would close the TRA-002 loop end-to-end.

---

### F3-INFO-1 — `build_default_registry()` returns a fresh instance per call (not a singleton)

**Severity:** INFO (positive observation)

**Evidence:** `/tmp/test_registry_edge.py` step 4:
```
r1 is r2? False
r1.get('zh_en') is r2.get('zh_en')? False
after r1.register(fr_en):
  r1 module names: ['zh_en', 'fr_en']
  r2 module names: ['zh_en']
```

Each call constructs a new `ModuleRegistry()` and re-instantiates `ZHENModule()`. This is correct for caller isolation — mutations to one registry do not leak into another. The cost (re-instantiating ZHENModule, which has no expensive state) is negligible.

---

### F3-INFO-2 — `TRA-MODULE-ZH-EN.md` is a linguistic spec, not a module-authoring template

**Severity:** INFO (documentation gap)

**Evidence:** Reading `/home/z/my-project/Translation-Runtime-Architecture/TRA-MODULE-ZH-EN.md` (55 lines):

The file covers:
- Structural bridge (parataxis → hypotaxis)
- Verbalization of nominalizations (mapping table)
- Epistemic certainty mapping (lexicon)
- Information order
- Avoidance of translationese
- Four-character expressions
- Punctuation conventions
- Entity preservation

The file does NOT cover:
- The `LanguageModuleProtocol` interface (no mention)
- The `as_interface()` adapter (no mention)
- The `kind` field (no mention)
- The `metadata.direction` field (no mention)
- The full method surface a module must implement (`is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`)
- How to wire the module into `build_default_registry()` or pass it to `TRAKernel(registry=...)`
- That `as_interface()` is required (or, per F3-BLOCKING-1, currently BROKEN)

**Impact:** SKILL.md §6 says "See `../TRA-MODULE-ZH-EN.md` for the module-authoring template" — but the file is a *linguistic* spec, not a *module-authoring* template. A new module author reading it would not learn that they need to define `is_forbidden()`, `get_forbidden_targets()`, `entity_type_hint()`, `apply_zh_rules()` — they would only see the linguistic content (parataxis, four-char, etc.). The actual interface contract lives only in `tra/modules/base.py` source code.

**Fix recommendation:** either rename the file to `TRA-MODULE-ZH-EN-LINGUISTIC.md` and create a new `TRA-MODULE-AUTHORING.md` template, OR augment the existing file with a §0 "Python contract" section that enumerates the Protocol methods and shows a minimal `as_interface()` skeleton.

---

### F3-INFO-3 — The existing TRA-002 regression test BYPASSES `as_interface()`

**Severity:** INFO (test coverage gap — explains why F3-BLOCKING-1 was not caught)

**Evidence:** `tests/test_outstanding_findings.py:571-575`:
```python
stub = StubModule()
registry = ModuleRegistry()
# Register the stub directly (not via as_interface shim) so the
# registry holds the full module object with all ISA-expected methods.
registry.register(stub)  # type: ignore[arg-type]
```

The comment explicitly says "Register the stub directly (not via as_interface shim)". The test then passes `registry=registry` to `TRAKernel` and verifies that `STUB_TARGET` appears in the exported glossary. This test PASSES at HEAD `b783745` — but it does NOT exercise the documented sanctioned path (which uses `as_interface()`). If the test had used `registry.register(stub.as_interface())`, it would have reproduced F3-BLOCKING-1.

**Impact:** The TRA-002 regression test gives false confidence that the registry path works. The actual sanctioned path (`as_interface()` + register) is untested and broken.

**Fix recommendation:** once F3-BLOCKING-1 is fixed, add a parallel test `test_kernel_uses_registry_via_as_interface()` that exercises the documented path end-to-end.

---

### F3-INFO-4 — Kernel/ISA immutability VERIFIED

**Severity:** INFO (positive observation — the core audit claim of Track F3)

**Evidence:**
```
$ git rev-parse HEAD
b7837457e5d110d4263fd6740ffacd5bbd0920f1

$ git diff --stat -- tra-prototype/tra/kernel.py tra-prototype/tra/isa.py
(empty)
```

- The committed HEAD `b783745` shows no modifications to `tra/kernel.py` or `tra/isa.py` relative to itself.
- Track F3's work was confined entirely to `/tmp/` (`/tmp/fren_module.py`, `/tmp/test_fren.py`, and 5 auxiliary test scripts). No edits were made to any file under `tra-prototype/tra/`.
- The FrENModule was registered purely via the public registry API: `registry.register(FrENModule().as_interface())` (sanctioned path — broken per F3-BLOCKING-1) or `registry.register(FrENModule())` (bypass path — works).
- The kernel's `_select_module` method (kernel.py:130-155) correctly picks `FrENModule` when `language_pair="FR -> EN"` and the registry contains a module with `metadata.direction == "FR -> EN"`. Verified via the bypass-path test: `kernel.ctx.module.__class__.__name__ == "FrENModule"` ✓, and the kernel produces `'# Hello\n\nLe system est established.'` (glossary substitution applied: `Bonjour → Hello`, `système → system`, `établi → established`).

**Note on working-tree state:** during the audit, a concurrent mutation-testing track (likely Track B3 or D3) briefly modified `tra/kernel.py` and `tra/isa.py` in the working tree (with explicit `# MUTATION:` markers). These mutations were reverted before Track F3 completed; the final `git diff --stat` for both files is empty. None of the mutations originated from Track F3.

---

## Appendix A — FrENModule stub (full source)

Saved at `/tmp/fren_module.py`. Reproduced here for the record:

```python
"""Stub FrENModule — Round 3 Track F3 audit (TRA prototype)."""
from __future__ import annotations
from tra.memory import EntityType, StyleProfile
from tra.modules.base import LanguageModuleProtocol
from tra.modules.registry import ModuleInterface

GLOSSARY: dict[str, str] = {
    "système": "system",
    "établi": "established",
    "Bonjour": "Hello",
    "vérification": "verification",
    "logiciel": "software",
}
FORBIDDEN_TARGETS: dict[str, str] = {"système": "software program"}

class FrENModule:
    name = "fr_en"
    kind = "language"
    direction = "FR -> EN"
    metadata: dict[str, str] = {"direction": "FR -> EN"}

    def get_glossary_mappings(self) -> dict[str, str]:
        return dict(GLOSSARY)

    def get_style_profile(self) -> StyleProfile:
        return StyleProfile(
            voice="Passive/Objective",
            sentence_complexity="Medium",
            epistemic_mapping={"établi": "established"},
            punctuation_rules={"halfwidth_inside_code": "true"},
        )

    def is_forbidden(self, source: str, target: str) -> bool:
        banned = FORBIDDEN_TARGETS.get(source)
        return banned is not None and target in banned.split("/")

    def get_forbidden_targets(self) -> dict[str, str]:
        return dict(FORBIDDEN_TARGETS)

    def entity_type_hint(self, token: str) -> EntityType | None:
        return None

    def apply_zh_rules(self, text: str) -> str:
        return text

    def apply_rules(self, source: str, direction: str) -> str:
        return source

    def as_interface(self) -> ModuleInterface:
        return ModuleInterface(
            name=self.name,
            kind=self.kind,
            get_glossary_mappings=self.get_glossary_mappings,
            get_style_profile=self.get_style_profile,
            apply_rules=self.apply_rules,
            metadata={"direction": self.direction},
        )
```

`isinstance(FrENModule(), LanguageModuleProtocol) == True` (self-check passes).

## Appendix B — Test results summary

| Test script | Path exercised | Result |
|---|---|---|
| `/tmp/test_fren.py` | Sanctioned: `as_interface()` + register + `TRAKernel(registry=...)` | **CRASH** — `pydantic.ValidationError: Input should be an instance of LanguageModuleProtocol` (F3-BLOCKING-1) |
| `/tmp/test_default_registry.py` | Default registry (ZHENModule via `as_interface()`) + `TRAKernel(registry=...)` | **CRASH** — same `ValidationError` (F3-BLOCKING-1 affects the default registry too) |
| `/tmp/test_fren_direct.py` | Bypass: register full `FrENModule()` directly + `TRAKernel(registry=...)` | **PASS** — `kernel.ctx.module.__class__.__name__ == "FrENModule"`, target = `'# Hello\n\nLe system est established.'` |
| `/tmp/test_broken_module.py` | Register module missing ALL Protocol methods | `registry.register()` accepts silently; `TRAKernel()` raises `AttributeError: 'BrokenModule' object has no attribute 'get_style_profile'` (F3-WARNING-1) |
| `/tmp/test_partial_broken.py` | Register module missing 4 Protocol methods (mirrors `ModuleInterface`) | `registry.register()` accepts silently; `TRAKernel()` raises `pydantic.ValidationError: Input should be an instance of LanguageModuleProtocol` (F3-WARNING-1) |
| `/tmp/test_registry_edge.py` | Duplicates, conflicts, unregister, singleton | Confirms F3-WARNING-2 (silent overwrite), F3-WARNING-3 (no conflict detection), F3-WARNING-4 (no unregister), F3-INFO-1 (fresh instance per call) |
| `/tmp/test_protocol_methods.py` | `dir()` comparison Protocol vs `ModuleInterface` | Confirms `ModuleInterface` is missing 4 Protocol methods (root cause of F3-BLOCKING-1 / F3-BLOCKING-2) |
