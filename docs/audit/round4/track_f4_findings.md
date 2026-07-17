# Track F4 — Stub-Module Conformance Re-Audit (Round 4)

**HEAD audited:** `805a8f8`
**Current repo HEAD:** `be123c6` (only doc additions since `805a8f8`; no source-code changes — verified via `git diff 805a8f8..be123c6 --stat -- tra-prototype/tra/ tra-prototype/tra_cli.py` → empty)
**Methodology:** Constructed a stub `fr-en` language module (`StubFREnModule`) implementing all 7 `LanguageModuleProtocol` methods, registered it via `ModuleRegistry.register()`, and verified the kernel + CLI could use it. Static review of `registry.py`, `base.py`, `zh_en.py`, `tra_cli.py`, `kernel.py`, `memory.py`.
**Baseline:** Round 3 Track F3 (`track_f3_findings.md`, 11 findings: 2 BLOCKING / 5 WARNING / 4 INFO) + R4 regression baseline (`track_r4_baseline.md` — TRA-096 FIXED, TRA-097 FIXED, TRA-098 FIXED, TRA-099 PERSISTENT, TRA-100 PERSISTENT).

## Summary

- Findings: **7 total (0 BLOCKING / 2 WARNING / 5 INFO)**
- Carry-over from Round 3: **5** (TRA-096, TRA-097, TRA-098, TRA-099, TRA-100)
- New findings: **2** (TRA-F4-006 default-mismatch crash on minimal `ModuleInterface`; TRA-F4-007 same-source-lang collision in `_select_module`)

## Stub module test results

Audit-only stub script: `/home/z/my-project/scripts/track_f4_stub_test.py` (NOT committed to the repo — lives outside the source tree).

| Step | Expected | Actual | Pass? |
|---|---|---|---|
| Stub class implements all 7 protocol methods | yes | all 7 methods present | ✓ |
| `as_interface()` returns valid ModuleInterface | yes | instanceof ModuleInterface: True (type=ModuleInterface) | ✓ |
| `isinstance(stub, LanguageModuleProtocol)` is True | True | True (both for `iface` and `stub`) | ✓ |
| `registry.register(stub)` succeeds | yes | registered names: `['fr_en']` | ✓ |
| `TRAKernel(cfg, registry=registry)` does NOT raise ValidationError | no raise | TRAKernel constructed; `ctx.module=ModuleInterface` | ✓ |
| `kernel.run(...)` uses the stub module | yes | module selected: ModuleInterface; glossary contains 'Bonjour': True; target[:60]=`'Hello le system'` | ✓ |
| `build_default_registry()` + `TRAKernel(registry=)` does NOT crash | no raise | default registry modules: `['zh_en']`; `ctx.module is not None`: True | ✓ |
| `TRA-097`: register() rejects broken module via isinstance check | TypeError mentioning LanguageModuleProtocol | TypeError raised: `Module 'broken' does not satisfy LanguageModuleProtocol. Missing methods: [...]` | ✓ |
| `TRA-098`: register() detects duplicate module names | ValueError mentioning duplicate name | ValueError raised: `Module 'fr_en_dup' is already registered. Use unregister() first if you intend to replace it.` | ✓ |
| `TRA-098`: register() detects conflicting directions | ValueError mentioning direction conflict | ValueError raised: `Direction conflict: module 'fr_en_b' has direction 'FR -> EN' which is already registered by module 'fr_en_a'. Only one module per direction is allowed.` | ✓ |
| fr-en + fr-de both register (different directions) | both accepted | both registered; names: `['fr_en', 'fr_de']` | ✓ |
| `_select_module`: first source-lang match wins | first-registered fr-* module selected | `ctx.module.metadata.direction='FR -> EN'` (first-registered wins by source-lang prefix match) | ✓ |
| **NEW probe**: minimal `ModuleInterface` (defaults only) crashes TRAKernel | ValidationError on style_profile (None not accepted) | raised `ValidationError: 1 validation error for RuntimeContext / style_profile / Input should be a valid dictionary or instance of StyleProfile [type=model_type, input_value=None, input_type=NoneType]` | ✓ |
| CLI `translate --lang fr-en` uses the stub | yes (TRA-099 says NO) | exit=0; ZHENModule glossary ('Confirmed') in output; FR stub glossary absent — silent fallback to ZHENModule | ✗ (TRA-099 persistent) |
| CLI `translate --help`: no `--registry` flag | no `--registry`, no `--module` flag | `--registry` in help: False; `--module/--module-path` in help: False | ✓ (flag absent) |

**Net: 14 of 15 procedural probes pass; 1 (CLI registry wiring) confirms TRA-099 PERSISTENT.**

### CLI test — full output (TRA-099 evidence)

```
cmd: python -m tra_cli --config .../config.yaml translate .../security_advisory_zh.md --lang fr-en --level L3 --output /tmp/.../translated.md
exit: 0
| TRA bootstrap OK — pair=fr-en level=L3_STRICT
| Translated -> /tmp/.../translated.md  (audit: ./audit_trace.jsonl, artifacts: ./compilation_artifacts)
--- translated.md (first 5 lines) ---
> # Security Advisory SA-2024-001
> 
> RustVMM v0.5.0 may Confirmed under heavy load. The execution environment must
> accurately describe the highly credible configuration so operators can verify.
> 
```

The CLI accepted `--lang fr-en`, ignored it for module selection (no `registry=` kwarg at `tra_cli.py:107`), fell back to `ZHENModule` at `kernel.py:175`, translated the ZH source via the ZH→EN glossary (note `Confirmed`, `execution environment`, `highly credible` — ZHENModule canonical terms), and exited 0. The user-requested `fr-en` language pair was effectively silently overridden by the no-registry fallback. A registered FR stub (had one been loaded in some other process) would NEVER be reachable via the CLI.

## Findings

### TRA-F4-001: `as_interface()` + `register()` + `TRAKernel(registry=)` works end-to-end (TRA-096 FIXED)

- **Severity:** INFO (positive verification — R3 BLOCKING resolved)
- **Category:** Module System / Protocol Conformance
- **Evidence:**
  - `tra/modules/registry.py:13-37` — `@dataclass ModuleInterface` now carries all 7 `Callable` fields (`get_glossary_mappings`, `get_style_profile`, `apply_rules`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`); the TRA-096 docstring at lines 17-25 explicitly documents the fix.
  - `tra/modules/zh_en.py:221-239` — `ZHENModule.as_interface()` wires all 7 methods (lines 234-237 pass `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules` — the 4 fields missing in R3).
  - Stub test step 5: `TRAKernel(cfg, registry=registry)` constructed without raising `ValidationError`; `ctx.module=ModuleInterface` (not None).
  - Stub test step 6: `kernel.run("Bonjour le système\n")` produced target `Hello le system` (FR stub glossary substitution applied — `Bonjour → Hello`, `système → system`).
  - Stub test step 7: `build_default_registry() + TRAKernel(cfg, registry=)` also does NOT crash (R3 F3-BLOCKING-1 affected the default registry too).
  - Existing regression test `tests/test_outstanding_findings.py::TestTRA096AsInterfaceProtocol` (3 tests) passes at HEAD.
- **Detail:** R3's F3-BLOCKING-1 (Pydantic rejecting `ModuleInterface` as "not an instance of `LanguageModuleProtocol`") is fully resolved by commit `3c38f78`. The 4 added `Callable` fields allow `isinstance(ModuleInterface(...), LanguageModuleProtocol)` to return True structurally, satisfying Pydantic's `RuntimeContext.module: LanguageModuleProtocol | None` validator (`tra/memory.py:216`). The spec's sanctioned extension path now works as documented in SKILL.md §6.
- **Suggested fix:** none — verified fixed.
- **Round 3 status:** **fixed** (was F3-BLOCKING-1, BLOCKING).

---

### TRA-F4-002: `register()` performs `isinstance(mod, LanguageModuleProtocol)` check (TRA-097 FIXED)

- **Severity:** INFO (positive verification — R3 WARNING resolved)
- **Category:** Module System / Protocol Conformance
- **Evidence:**
  - `tra/modules/registry.py:57-74` — `register()` calls `from .base import LanguageModuleProtocol` (line 57) then `if not isinstance(module, LanguageModuleProtocol):` (line 59) and raises a `TypeError` listing the missing methods by name (lines 60-74):
    ```python
    raise TypeError(
        f"Module '{mod_name}' does not satisfy "
        f"LanguageModuleProtocol. Missing methods: {missing}"
    )
    ```
  - Stub test step 8: registering a `BrokenModule` (no methods at all) raised `TypeError: Module 'broken' does not satisfy LanguageModuleProtocol. Missing methods: ['get_glossary_mappings', 'get_style_profile', 'is_forbidden', 'get_forbidden_targets', 'entity_type_hint', 'apply_zh_rules', 'apply_rules']`.
  - Existing regression test `tests/test_outstanding_findings.py::TestTRA097RegisterProtocolCheck` (2 tests) passes at HEAD.
- **Detail:** R3's F3-WARNING-1 (register() accepted broken modules silently, crashing later with opaque `AttributeError`) is resolved by commit `a3cd2c1`. The error message is now actionable: it names the Protocol and enumerates the missing methods. Note that the check is structural (`@runtime_checkable` Protocol via `isinstance`), so it accepts both full module objects and `ModuleInterface` dataclasses (both have all 7 attributes).
- **Suggested fix:** none — verified fixed.
- **Round 3 status:** **fixed** (was F3-WARNING-1, WARNING).

---

### TRA-F4-003: `register()` detects duplicate names AND conflicting directions (TRA-098 FIXED); `unregister()` added (F3-WARNING-4 FIXED)

- **Severity:** INFO (positive verification — R3 WARNINGs resolved)
- **Category:** Module System / Registry Hardening
- **Evidence:**
  - `tra/modules/registry.py:48-49` — `__init__` now maintains a `_directions: dict[str, str]` index alongside `_modules`.
  - `tra/modules/registry.py:75-80` — duplicate-name detection:
    ```python
    if module.name in self._modules:
        raise ValueError(
            f"Module '{module.name}' is already registered. "
            f"Use unregister() first if you intend to replace it."
        )
    ```
  - `tra/modules/registry.py:81-92` — direction-conflict detection (language modules only):
    ```python
    if module.kind == "language":
        direction = str(module.metadata.get("direction", ""))
        if direction and direction in self._directions:
            existing = self._directions[direction]
            raise ValueError(
                f"Direction conflict: module '{module.name}' has direction "
                f"'{direction}' which is already registered by module "
                f"'{existing}'. Only one module per direction is allowed."
            )
    ```
  - `tra/modules/registry.py:95-104` — `unregister(name)` method (NEW since R3; closes F3-WARNING-4) cleans up both `_modules` and `_directions`.
  - Stub test step 9: duplicate-name registration raised `ValueError: Module 'fr_en_dup' is already registered. Use unregister() first if you intend to replace it.`
  - Stub test step 10: conflicting-direction registration raised `ValueError: Direction conflict: module 'fr_en_b' has direction 'FR -> EN' which is already registered by module 'fr_en_a'. Only one module per direction is allowed.`
  - Existing regression test `tests/test_outstanding_findings.py::TestTRA098RegistryDuplicateDetection` (3 tests) passes at HEAD, including `test_unregister_removes_module`.
- **Detail:** R3's F3-WARNING-2 (silent overwrite on duplicate name), F3-WARNING-3 (no direction-conflict detection), and F3-WARNING-4 (no `unregister()` API) are all resolved by commit `a3cd2c1`. The `_directions` index is correctly maintained on both `register()` and `unregister()` — re-registering the same direction after `unregister()` works (verified via direct probe). Note: direction-conflict detection is scoped to `kind == "language"` only; domain/formatting modules can still share metadata freely (intentional — they don't claim a language direction).
- **Suggested fix:** none — verified fixed.
- **Round 3 status:** **fixed** (was F3-WARNING-2 + F3-WARNING-3 + F3-WARNING-4, WARNINGs).

---

### TRA-F4-004: CLI `translate` does NOT pass `registry=` to `TRAKernel` (TRA-099 PERSISTENT)

- **Severity:** WARNING
- **Category:** CLI Wiring / Module System
- **Evidence:**
  - `tra_cli.py:66-77` — `translate` command options are `--lang`, `--level`, `--output`, `--interactive`. No `--registry`, no `--module`, no `--module-path` flag exists:
    ```python
    @click.argument("input_md", ...)
    @click.option("--lang", ...)
    @click.option("--level", ...)
    @click.option("--output", "-o", ...)
    @click.option("--interactive", is_flag=True, ...)
    ```
  - `tra_cli.py:107` — kernel construction:
    ```python
    kernel = TRAKernel(cfg, interactive=interactive)
    ```
    No `registry=` kwarg; `rg -n "registry" tra_cli.py` returns zero matches.
  - `tra/kernel.py:107-112` — `TRAKernel.__init__` signature accepts `registry: object | None = None`, so the CLI *could* pass one but doesn't.
  - `tra/kernel.py:156-175` — when `registry is None`, `_select_module` falls through to `return ZHENModule()` (line 175).
  - `git diff b783745..805a8f8 -- tra_cli.py` → empty (CLI unchanged across the 6 R3→R4 remediation commits).
  - Stub test step 13: CLI invocation `python -m tra_cli --config .../config.yaml translate .../security_advisory_zh.md --lang fr-en --level L3 --output /tmp/.../translated.md` exited 0 with output containing `Confirmed` (ZHENModule's canonical term) — proving the FR stub (had one been registered in some other process) was NEVER consulted. The user's `--lang fr-en` was silently overridden by the ZHENModule fallback.
  - Stub test step 14: `python -m tra_cli translate --help` confirms no `--registry` flag.
- **Detail:** R3's F3-WARNING-5 (CLI never passes registry=) is unchanged. The 6 R3→R4 commits landed 14 source fixes (TRA-073/076/077/078/088/089/093/096/097/098 + partial 001/038) but **did not touch `tra_cli.py` at all** — `git diff b783745..805a8f8 -- tra_cli.py` is empty. The spec's sanctioned module extension path now works end-to-end via the Python API (TRA-F4-001), but the CLI remains the no-registry-attached single entry point, hard-coded to ZHENModule fallback. A user authoring and registering a custom FrENModule has no way to invoke it via the CLI; they must write their own driver script.
- **Suggested fix:** add a `--registry` / `--module` flag to `translate` that accepts a dotted Python path (e.g., `--module my_pkg.fr_en:FrENModule`) and constructs + registers the module before invoking the kernel. Combined with the TRA-F4-001 fix (which already landed), this would close the TRA-002 / TRA-099 loop end-to-end. Estimated effort: ~25 LOC of CLI plumbing + 1 test.
- **Round 3 status:** **persistent** (was F3-WARNING-5, WARNING).

---

### TRA-F4-005: `TRA-MODULE-ZH-EN.md` is still a linguistic spec, not a module-authoring template (TRA-100 PERSISTENT)

- **Severity:** INFO
- **Category:** Documentation / Module System
- **Evidence:**
  - `tra/modules/base.py:14-56` — `LanguageModuleProtocol` defines 7 methods (`get_glossary_mappings`, `get_style_profile`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`, `apply_rules`) plus `name` and `kind` attributes.
  - `TRA-MODULE-ZH-EN.md` — 55-line file covers structural bridge, nominalization, epistemic mapping, information order, translationese avoidance, four-char expressions, punctuation, entity preservation. **Does NOT cover**: `LanguageModuleProtocol`, `as_interface()`, `kind`, `metadata.direction`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`, or how to wire a module into `build_default_registry()` / `TRAKernel(registry=...)`.
  - `tra-prototype/SKILL.md` §6 references `../TRA-MODULE-ZH-EN.md` as the module-authoring template, but the file is purely linguistic.
  - R4 baseline row TRA-100: PERSISTENT (verified by `rg -n "LanguageModuleProtocol|as_interface|metadata.direction|kind" TRA-MODULE-ZH-EN.md` → no match).
- **Detail:** Unchanged since R3 Track F3's F3-INFO-2. A new module author reading `TRA-MODULE-ZH-EN.md` would not learn that they need to define `is_forbidden()`, `get_forbidden_targets()`, `entity_type_hint()`, `apply_zh_rules()` — they would only see the linguistic content. The actual interface contract lives only in `tra/modules/base.py` source code (which the doc never points to).
- **Suggested fix:** either rename `TRA-MODULE-ZH-EN.md` to `TRA-MODULE-ZH-EN-LINGUISTIC.md` and create a new `TRA-MODULE-AUTHORING.md` template that enumerates the Protocol methods and shows a minimal `as_interface()` skeleton, OR augment the existing file with a §0 "Python contract" section that points at `tra/modules/base.py:LanguageModuleProtocol` and reproduces the `StubFREnModule` pattern from this audit.
- **Round 3 status:** **persistent** (was F3-INFO-2, INFO).

---

### TRA-F4-006: Minimal `ModuleInterface` (defaults only) passes `register()` but crashes `TRAKernel` construction

- **Severity:** WARNING
- **Category:** Module System / Protocol Conformance
- **Evidence:**
  - `tra/modules/registry.py:30` — `ModuleInterface.get_style_profile` default is `Callable[[], object] = lambda: None` (returns None).
  - `tra/modules/registry.py:29-36` — all 7 `Callable` fields have defaults (`lambda: {}`, `lambda: None`, `lambda src, _dir: src`, etc.), so a user can construct `ModuleInterface(name="x", kind="language", metadata={"direction": "Y -> Z"})` and pass `register()`'s `isinstance` check at line 59 — the defaults satisfy the Protocol structurally.
  - `tra/kernel.py:144` — `RuntimeContext(..., style_profile=module.get_style_profile(), ...)` calls the default lambda, which returns `None`.
  - `tra/memory.py:205` — `style_profile: StyleProfile = Field(default=StyleProfile)` (RuntimeContext field is typed `StyleProfile`, not `StyleProfile | None`).
  - `tra/memory.py:216` — `module: LanguageModuleProtocol | None` validator rejects `None` for `style_profile`.
  - Stub test step 11b (NEW probe): constructing `ModuleInterface(name="minimal_zh_en", kind="language", metadata={"direction": "ZH -> EN"})`, registering it, then constructing `TRAKernel(cfg, registry=reg)` raised:
    ```
    ValidationError: 1 validation error for RuntimeContext
    style_profile
      Input should be a valid dictionary or instance of StyleProfile
      [type=model_type, input_value=None, input_type=NoneType]
    ```
  - Existing test `tests/test_outstanding_findings.py:1755-1766` (`TestTRA097RegisterProtocolCheck::test_valid_module_accepted`) constructs exactly such a minimal `ModuleInterface` and only calls `registry.register(iface)` — it never constructs a `TRAKernel` with it, so this crash is uncovered.
- **Detail:** The dataclass defaults and the Protocol return-type contract disagree. `LanguageModuleProtocol.get_style_profile` is typed `() -> object` (line 34 of `base.py`), so returning `None` is Protocol-conformant — but `RuntimeContext.style_profile` requires a real `StyleProfile`. A user following the (still-missing — see TRA-F4-005) module-authoring template might naturally write `ModuleInterface(name=..., kind=..., metadata=...)` and trust the defaults, then hit an opaque `ValidationError` mentioning neither `LanguageModuleProtocol` nor `as_interface` — the error message points at `style_profile` and `RuntimeContext`, which are downstream of the actual mistake (using the dataclass defaults instead of providing a real `get_style_profile`). The four other defaults (`get_glossary_mappings=lambda: {}`, `apply_rules=lambda src, _dir: src`, `is_forbidden=lambda _src, _tgt: False`, `get_forbidden_targets=lambda: {}`, `entity_type_hint=lambda _token: None`, `apply_zh_rules=lambda text: text`) are all valid (their return types match what the kernel/ISA expect); only `get_style_profile` is wrong because its default returns `None` but the kernel feeds the return value to a `StyleProfile`-typed Pydantic field.
- **Suggested fix:** change the `get_style_profile` default at `tra/modules/registry.py:30` from `lambda: None` to `lambda: StyleProfile()` (importing `StyleProfile` from `tra.memory`), OR remove the default entirely and require module authors to supply it (making `ModuleInterface` construction fail-fast at the dataclass level). A regression test should also construct a minimal `ModuleInterface` and call `TRAKernel(cfg, registry=reg)` to lock the contract.
- **Round 3 status:** **new** (uncovered by R3 Track F3 — F3 used a full `FrENModule` with real `get_style_profile`, not a minimal `ModuleInterface`).

---

### TRA-F4-007: `_select_module` picks the first source-language match — same-source-lang collisions are silent

- **Severity:** INFO
- **Category:** Module System / Dispatch Semantics
- **Evidence:**
  - `tra/kernel.py:149-175` — `_select_module` iterates `registry.all()` and returns the FIRST module whose `metadata.direction` source-language prefix matches `language_pair`'s source-language prefix:
    ```python
    for mod in registry.all():  # type: ignore[attr-defined]
        if getattr(mod, "kind", "") != "language":
            continue
        mod_direction = str(getattr(mod, "metadata", {}).get("direction", ""))
        mod_source = (
            mod_direction.split("->", 1)[0].strip().lower()
            if "->" in mod_direction
            else ""
        )
        if mod_source == source_lang:
            return mod
    # No match in registry; fall through to ZHENModule.
    return ZHENModule()
    ```
  - `tra/modules/registry.py:81-92` — `register()` only rejects conflicting **full direction strings** (`"FR -> EN"` vs `"FR -> EN"`); it does NOT reject two modules whose `metadata.direction` shares the same source language but differs in target (e.g., `"FR -> EN"` and `"FR -> DE"`).
  - Stub test step 11: registered `fr_en` (direction `FR -> EN`) AND `fr_de` (direction `FR -> DE`) — both accepted by `register()` because the full direction strings differ.
  - Stub test step 12: with `language_pair="FR -> DE"` and a registry containing `[fr_en, fr_de]` (in that order), `_select_module` returned `fr_en` (direction `FR -> EN`), NOT `fr_de` — because both modules' source-lang prefix is `"fr"` and `fr_en` was registered first.
- **Detail:** The `_select_module` filter is **source-language-prefix-only**, not full-direction-match. If a registry contains two modules with the same source language but different targets (e.g., a polyglot FR module that supports both `FR -> EN` and `FR -> DE`), the kernel silently picks whichever was registered first, regardless of the requested target language. This is not a crash, but it is a non-deterministic dispatch (registration order leaks into module selection). The TRA-098 direction-conflict detection (TRA-F4-003) catches same-direction duplicates but explicitly allows same-source-different-target registrations, so this scenario is reachable in practice. The behavior is undocumented — neither `kernel.py:149-175` nor SKILL.md §6 mentions the "first-source-lang-match wins" rule.
- **Suggested fix:** either (a) tighten `_select_module` to match the full `language_pair` string against `metadata.direction` (exact match, not prefix match) — this would correctly select `fr_de` for `language_pair="FR -> DE"`; OR (b) document the "first-source-lang-match wins" rule in SKILL.md §6 and add a WARNING log when multiple modules match the same source language. Option (a) is the cleaner fix and aligns with the spec's intent (the kernel's `language_pair` config field carries both source AND target).
- **Round 3 status:** **new** (R3 Track F3's F3-WARNING-3 only flagged conflicting full-direction duplicates; it did not probe same-source-different-target dispatch).

---

## Round 3 carry-over status matrix (Track F scope)

| Round 3 ID | Title | Round 4 status |
|---|---|---|
| TRA-096 | as_interface crashes with ValidationError | **fixed** (TRA-F4-001) — stub test steps 1-7 all PASS |
| TRA-097 | register() lacks isinstance check | **fixed** (TRA-F4-002) — stub test step 8 PASS |
| TRA-098 | register() lacks duplicate detection | **fixed** (TRA-F4-003) — stub test steps 9, 10 PASS; `unregister()` also added |
| TRA-099 | CLI --registry flag | **persistent** (TRA-F4-004) — stub test step 13 confirms silent fallback to ZHENModule |
| TRA-100 | Module authoring guide | **persistent** (TRA-F4-005) — `TRA-MODULE-ZH-EN.md` unchanged |
| (R3 F3-WARNING-4) | No `unregister()` API | **fixed** (folded into TRA-F4-003) — `tra/modules/registry.py:95-104` |

## Verification commands run (reproducibility)

```bash
# Stub module test (audit-only — script lives OUTSIDE the repo)
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype
PYTHONPATH=/home/z/my-project/scripts python /home/z/my-project/scripts/track_f4_stub_test.py
# → 15/15 procedural probes pass; CLI test confirms TRA-099 persistent

# CLI test (TRA-099 evidence — full output captured in stub test step 13b)
python -m tra_cli --config config.yaml translate examples/security_advisory_zh.md \
    --lang fr-en --level L3 --output /tmp/translated.md
# → exit 0; output uses ZHENModule glossary ('Confirmed'); FR stub glossary absent

# CLI help — confirm no --registry flag
python -m tra_cli translate --help | grep -E "registry|module"
# → no matches

# Static checks
rg "register\(" tra/modules/registry.py
# → lines 51, 95, 124, 138, 144 (register + unregister + build_default_registry + 2 in registry_for_language_pair)

rg "isinstance.*LanguageModuleProtocol" tra/modules/registry.py
# → line 59 (TRA-097 check inside register())

rg "registry" tra_cli.py
# → no matches (TRA-099: CLI never references registry at all)

# Confirm no source-code changes between audit baseline 805a8f8 and current HEAD
git diff 805a8f8..HEAD --stat -- tra-prototype/tra/ tra-prototype/tra_cli.py
# → empty (only doc additions since 805a8f8)

# R3 regression tests for the F-scope findings (still pass at HEAD)
python -m pytest tests/test_outstanding_findings.py -k \
    "TestTRA002 or TestTRA096 or TestTRA097 or TestTRA098" -v
# → 9 passed in 0.23s

# Full test suite sanity
python -m pytest tests/
# → 199 passed in 1.27s

# Default-mismatch probe (TRA-F4-006)
python -c "
from tra.modules.registry import ModuleInterface, ModuleRegistry
from tra.config import BootstrapConfig
from tra.kernel import TRAKernel
from tra.memory import ConformanceLevel
import tempfile, pathlib
with tempfile.TemporaryDirectory() as d:
    cfg = BootstrapConfig(language_pair='ZH -> EN', domain='t',
        conformance_level=ConformanceLevel.L1_BASIC, model_endpoint='r',
        model_version='t', base_dir=d,
        cache_directory=f'{d}/c', compilation_dir=f'{d}/a', audit_trace=f'{d}/a.jsonl')
    reg = ModuleRegistry()
    reg.register(ModuleInterface(name='m', kind='language', metadata={'direction': 'ZH -> EN'}))
    TRAKernel(cfg, registry=reg)
"
# → raises ValidationError on style_profile (input_value=None)
```

## Conclusion

HEAD `805a8f8` resolves all 3 of R3 Track F3's BLOCKING/WARNING module-system findings (TRA-096/097/098) and adds the missing `unregister()` API (R3 F3-WARNING-4). The spec's sanctioned extension path — `as_interface()` → `register()` → `TRAKernel(registry=)` — now works end-to-end via the Python API, verified by the `StubFREnModule` test which successfully translates `Bonjour le système` to `Hello le system` using the stub's FR→EN glossary. The `register()` function performs an `isinstance(mod, LanguageModuleProtocol)` check at `tra/modules/registry.py:59` with an actionable error message naming the missing methods, and detects both duplicate names (line 76) and conflicting directions (line 82). All 9 existing R3 regression tests for TRA-002/096/097/098 still pass.

The 1 persistent WARNING (TRA-099) and 1 persistent INFO (TRA-100) carry over unchanged from R3. TRA-099 is the more material of the two: `tra_cli.py` was not touched by any of the 6 R3→R4 remediation commits (`git diff b783745..805a8f8 -- tra_cli.py` is empty), so the CLI still constructs `TRAKernel(cfg, interactive=interactive)` at line 107 with no `registry=` kwarg. The CLI test (step 13) proves this empirically — `python -m tra_cli translate .../security_advisory_zh.md --lang fr-en --level L3` exited 0 with output containing `Confirmed` (ZHENModule's canonical term) and no FR stub glossary, demonstrating that the user's `--lang fr-en` request was silently overridden by the ZHENModule fallback at `kernel.py:175`. A user authoring and registering a custom FrENModule has no way to invoke it via the CLI; they must write their own driver script.

The 2 new findings (TRA-F4-006 default-mismatch crash on minimal `ModuleInterface`; TRA-F4-007 same-source-lang silent dispatch collision) are both WARNING/INFO edge cases that R3 Track F3 did not probe — F3 used a fully-implemented `FrENModule` and tested same-direction duplicates only. Neither blocks the sanctioned extension path, but both warrant follow-up: TRA-F4-006 is a 1-line default-change in `tra/modules/registry.py:30`, and TRA-F4-007 is a 5-line tightening of `_select_module` to match the full `language_pair` string instead of just the source-language prefix. Combined with the existing TRA-099 CLI fix recommendation (~25 LOC), all 3 open F4 findings could be closed in a single follow-up commit.

No source code modified (audit-only). The stub test script lives at `/home/z/my-project/scripts/track_f4_stub_test.py` (outside the repo) and is the primary evidence for TRA-F4-001 through TRA-F4-004 and TRA-F4-006/007.
