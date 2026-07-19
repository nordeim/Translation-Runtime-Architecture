# Track F5 — Stub-Module Conformance Re-Audit (Round 5)

**HEAD audited:** `5476faf1d668b42d2a7b8c9b159ae9ee54c6e4f7`
**R4 baseline HEAD:** `805a8f8`
**Methodology:** Stub-module construction tests (61 automated probes in `/home/z/my-project/tmp_f5/r5_f5_stub_test.py`); CLI registry wiring verification; module authoring guide review.
**Baseline:** Round 4 Track F4 (`track_f4_findings.md`, 7 findings: 0 BLOCKING / 2 WARNING / 5 INFO) + 66-finding R4 master register + R5 baseline (TRA-096/097/098 fixed, TRA-099 fixed by Batch 4 commit `e54b7a7`, TRA-100 fixed by Batch 4 commit `aae0bca`, F4-006/007 fixed by Batch 3 commit `524c598`).

## Summary

- Findings: **13 total (0 BLOCKING / 1 WARNING / 12 INFO)**
- Carry-over from Round 4: **7** (all 7 re-verified — 5 fixed-and-verified, 2 verified-holding-positive)
- New findings: **6** (TRA-F5-006 through TRA-F5-011, mostly INFO; 1 WARNING)
- Regressions: **0**
- Stub-module test results: **61 / 61 probes PASS** at HEAD `5476faf`

## Stub-module test results

Audit-only probe script: `/home/z/my-project/tmp_f5/r5_f5_stub_test.py` (NOT committed to the repo — lives outside the source tree). Runs 11 probe groups with 61 individual assertions.

| Probe group | Probes | PASS | FAIL |
|---|---|---|---|
| 1. TRA-096 — `as_interface()` + `register()` + `TRAKernel(registry=)` E2E | 9 | 9 | 0 |
| 2. TRA-097 — `register()` Protocol check | 1 | 1 | 0 |
| 3. TRA-098 — duplicate + direction-conflict detection | 4 | 4 | 0 |
| 4. TRA-F4-006 — minimal `ModuleInterface` defaults rejected | 3 | 3 | 0 |
| 5. TRA-F4-007 — `_select_module` full-direction match | 3 | 3 | 0 |
| 6. TRA-099 — CLI registry wiring + `--lang` normalization | 4 | 4 | 0 |
| 7. `ModuleInterface` contract (dataclass, Protocol, RuntimeContext typing) | 8 | 8 | 0 |
| 8. `build_default_registry()` returns ZH-EN via `as_interface()` | 4 | 4 | 0 |
| 9. Edge cases (missing pair, empty registry, duplicate dirs, singleton fallback) | 8 | 8 | 0 |
| 10. TRA-100 — module authoring guide substantive review | 9 | 9 | 0 |
| 11. Additional F5 checks (backward-compat, dict-coercion, keyword-only `registry=`) | 8 | 8 | 0 |
| **Total** | **61** | **61** | **0** |

### Key empirical confirmations

- **TRA-096 (R3 BLOCKING, R4 fixed, R5 verified-holding):** Stub `StubFREnModule` (with FR↔EN glossary `{"bonjour": "hello", "système": "system", "monde": "world"}`) successfully runs `as_interface()` → `register()` → `TRAKernel(cfg, registry=reg)` → `kernel.run("monde")` produces `world` (a target ZHENModule would never emit). Glossary mapping is consulted end-to-end. (Probe 1.1g, 1.1i.)
- **TRA-F4-006 (R4 new WARNING, R5 fixed-and-verified):** `ModuleInterface(name="minimal", kind="language", metadata={"direction": "XX -> YY"})` (default lambdas, including `get_style_profile=lambda: None`) is rejected by `register()` with `TypeError: Module 'minimal'.get_style_profile() returned None. RuntimeContext.style_profile is a typed Pydantic field that rejects None. Supply a get_style_profile callable that returns a StyleProfile instance (see tra.modules.zh_en.ZHENModule for the template).` — the message is actionable, names the offending field, and points to the template module. (Probe 4.c.)
- **TRA-F4-007 (R4 new INFO, R5 fixed-and-verified):** With two stub modules `fr_en` (direction `FR -> EN`, registered first) and `fr_de` (direction `FR -> DE`, registered second) in the same registry, `TRAKernel._select_module("FR -> DE", reg)` returns `fr_de` (NOT `fr_en`); end-to-end `kernel.run("bonjour")` produces `hallo` (not `hello`). (Probe 5.a, 5.c.)
- **TRA-099 (R3-R4 PERSISTENT WARNING, R5 fixed-and-verified):** `tra_cli.py:138` calls `build_default_registry()`; `tra_cli.py:139` passes `registry=registry` to `TRAKernel`; `tra_cli.py:115` calls `_normalize_language_pair(lang)`. End-to-end CLI test via `CliRunner` with a monkeypatched `build_default_registry` that includes a stub `fr_en` module confirms `python -m tra_cli translate ... --lang fr-en` produces `hello` in the output (the stub's glossary term), NOT the ZHENModule fallback. (Probe 6.a, 6.b, 6.c, 6.d.)
- **TRA-100 (R3-R4 PERSISTENT INFO, R5 fixed-and-verified):** `TRA-MODULE-AUTHORING.md` is 328 LOC, has 6 numbered sections, references all 7 protocol methods, includes an actionable `as_interface()` skeleton, has a CLI usage example (`python -m tra_cli translate input.md --lang fr-en --level L3`), references `tra/modules/zh_en.py` as the template, and lists the 4 critical invariants. (Probe 10.a-i.)

## Findings

### TRA-F5-001: TRA-096 — `as_interface()` + `register()` + `TRAKernel(registry=)` end-to-end works (R3 BLOCKING → R4 FIXED → R5 verified-holding)

- **Severity:** INFO
- **Category:** Stub-Module / Protocol Conformance
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/modules/registry.py:13-37` — `@dataclass ModuleInterface` carries all 7 `Callable` fields (`get_glossary_mappings`, `get_style_profile`, `apply_rules`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`) plus `name`, `kind`, `metadata` (3 non-callable fields); the TRA-096 docstring at lines 17-25 explicitly documents the fix.
  - `tra/modules/zh_en.py:221-239` — `ZHENModule.as_interface()` wires all 7 methods (lines 234-237 pass `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules` — the 4 fields missing in R3) plus `metadata={"direction": self.direction}`.
  - Probe 1.1a-1.1i: stub `StubFREnModule.as_interface()` returns a `ModuleInterface`; `isinstance(iface, LanguageModuleProtocol)` is True; `registry.register(iface)` succeeds; `TRAKernel(cfg, registry=reg)` constructs; `kernel.ctx.module` is the stub (not `None`, not `ZHENModule`); `kernel.ctx.style_profile.voice == 'technical'` (from the stub); `kernel.run("monde")` produces `'world'` (the stub glossary — ZHENModule would never emit this).
  - Probe 1.1h: `build_default_registry() + TRAKernel(cfg, registry=reg)` constructs without raising (R3 F3-BLOCKING-1 affected the default registry too — confirmed closed).
  - Regression test `tests/test_outstanding_findings.py::TestTRA096AsInterfaceProtocol` (3 tests) passes at HEAD.
- **Detail:** R3's F3-BLOCKING-1 (Pydantic rejecting `ModuleInterface` as "not an instance of `LanguageModuleProtocol`") is fully resolved by commit `3c38f78`. R4 verified the fix held; R5 confirms it still holds and additionally proves the stub glossary is *consulted during translation* (probe 1.1i — `'monde' -> 'world'`), not just selected.
- **Suggested fix:** none — verified holding.
- **Round 4 status:** **verified-holding** (was R3 BLOCKING, R4 FIXED — Track F4 finding TRA-F4-001).

---

### TRA-F5-002: TRA-097 — `register()` performs `isinstance(mod, LanguageModuleProtocol)` check (R4 fixed → R5 verified-holding)

- **Severity:** INFO
- **Category:** Stub-Module / Protocol Conformance
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/modules/registry.py:62-79` — `register()` imports `LanguageModuleProtocol` lazily (line 62), then `if not isinstance(module, LanguageModuleProtocol):` (line 64) and raises a `TypeError` listing the missing methods by name (lines 65-79):
    ```python
    required = ("get_glossary_mappings", "get_style_profile", "is_forbidden",
                "get_forbidden_targets", "entity_type_hint", "apply_zh_rules", "apply_rules")
    missing = [m for m in required if not hasattr(module, m)]
    mod_name = getattr(module, "name", "?")
    raise TypeError(
        f"Module '{mod_name}' does not satisfy "
        f"LanguageModuleProtocol. Missing methods: {missing}"
    )
    ```
  - Probe 2: registering a `BrokenModule` (only `name` and `kind` attributes, no methods) raised `TypeError: Module 'broken' does not satisfy LanguageModuleProtocol. Missing methods: ['get_glossary_mappings', 'get_style_profile', 'is_forbidden', 'get_forbidden_targets', 'entity_type_hint', 'apply_zh_rules', 'apply_rules']`.
  - Regression test `tests/test_outstanding_findings.py::TestTRA097RegisterProtocolCheck` (2 tests) passes at HEAD.
- **Detail:** R3's F3-WARNING-1 (register() accepted broken modules silently, crashing later with opaque `AttributeError`) is fully resolved by commit `a3cd2c1`. R5 confirms the error message is still actionable: it names the Protocol, enumerates ALL 7 missing methods, and identifies the module by name.
- **Suggested fix:** none — verified holding.
- **Round 4 status:** **verified-holding** (was R3 WARNING, R4 FIXED — Track F4 finding TRA-F4-002).

---

### TRA-F5-003: TRA-098 — `register()` detects duplicate names AND conflicting directions; `unregister()` API present (R4 fixed → R5 verified-holding)

- **Severity:** INFO
- **Category:** Stub-Module / Registry Hardening
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/modules/registry.py:47-49` — `__init__` maintains `_directions: dict[str, str]` index alongside `_modules`.
  - `tra/modules/registry.py:100-104` — duplicate-name detection:
    ```python
    if module.name in self._modules:
        raise ValueError(f"Module '{module.name}' is already registered. "
                         f"Use unregister() first if you intend to replace it.")
    ```
  - `tra/modules/registry.py:106-116` — direction-conflict detection (language modules only):
    ```python
    if module.kind == "language":
        direction = str(module.metadata.get("direction", ""))
        if direction and direction in self._directions:
            existing = self._directions[direction]
            raise ValueError(f"Direction conflict: module '{module.name}' has direction "
                             f"'{direction}' which is already registered by module "
                             f"'{existing}'. Only one module per direction is allowed.")
        if direction:
            self._directions[direction] = module.name
    ```
  - `tra/modules/registry.py:119-128` — `unregister(name)` method cleans up both `_modules` and `_directions`.
  - Probe 3.a: duplicate-name registration raised `ValueError: Module 'fr_en' is already registered. Use unregister() first if you intend to replace it.`
  - Probe 3.b: conflicting-direction registration (different name, same `FR -> EN` direction) raised `ValueError: Direction conflict: module 'fr_en_other' has direction 'FR -> EN' which is already registered by module 'fr_en'. Only one module per direction is allowed.`
  - Probe 3.c: two modules with different directions (`FR -> EN` + `FR -> DE`) both accepted (`len(reg.all()) == 2`).
  - Probe 3.d: `unregister("fr_en")` followed by re-registering the same direction succeeds — direction slot is freed.
  - Regression test `tests/test_outstanding_findings.py::TestTRA098RegistryDuplicateDetection` (3 tests) passes at HEAD, including `test_unregister_removes_module`.
- **Detail:** R3's F3-WARNING-2/3/4 (silent overwrite on duplicate name, no direction-conflict detection, no `unregister()` API) all fully resolved. R5 confirms both detection paths still raise with actionable messages and `unregister()` correctly frees the direction slot for re-registration.
- **Suggested fix:** none — verified holding.
- **Round 4 status:** **verified-holding** (was R3 WARNINGs, R4 FIXED — Track F4 finding TRA-F4-003).

---

### TRA-F5-004: TRA-F4-006 — minimal `ModuleInterface` (defaults only) is now rejected by `register()` with a clear `TypeError` (R4 new WARNING → R5 fixed-and-verified)

- **Severity:** INFO
- **Category:** Stub-Module / Protocol Conformance
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/modules/registry.py:30` — `get_style_profile: Callable[[], object] = lambda: None` (default still returns None).
  - `tra/modules/registry.py:80-98` — TRA-F4-006 fix block: `register()` calls `module.get_style_profile()` (line 85) and validates the return shape (lines 91-98):
    ```python
    if style_profile is None:
        raise TypeError(
            f"Module '{module.name}'.get_style_profile() returned None. "
            f"RuntimeContext.style_profile is a typed Pydantic field that "
            f"rejects None. Supply a get_style_profile callable that returns "
            f"a StyleProfile instance (see tra.modules.zh_en.ZHENModule "
            f"for the template)."
        )
    ```
  - Probe 4.a: `ModuleInterface(name="minimal", kind="language", metadata={"direction": "XX -> YY"})` (default lambdas) — all 7 default callables present (sanity check).
  - Probe 4.b: `minimal.get_style_profile()` returns `None` (the default lambda).
  - Probe 4.c: `registry.register(minimal)` raised `TypeError: Module 'minimal'.get_style_profile() returned None. RuntimeContext.style_profile is a typed Pydantic field that rejects None. Supply a get_style_profile callable that returns a StyleProfile instance (see tra.modules.zh_en.ZHENModule for the template).` — error names the offending field, explains *why* None is rejected, and points to the template module.
  - Regression test `tests/test_outstanding_findings.py::TestTRA_F4_006_MinimalModuleInterfaceCrashes::test_minimal_module_interface_register_raises` passes at HEAD; the test asserts the raised exception is a `TypeError` (NOT a Pydantic `ValidationError`) and that the message mentions `style_profile`.
- **Detail:** R4's TRA-F4-006 finding flagged that `ModuleInterface(name=..., kind=..., metadata=...)` with default lambdas constructed successfully but then crashed `TRAKernel.__init__` with an opaque `ValidationError: 1 validation error for RuntimeContext / style_profile / Input should be a valid dictionary or instance of StyleProfile [type=model_type, input_value=None, input_type=NoneType]`. R4 Batch 3 commit `524c598` added the F4-006 fix block in `register()`. R5 confirms the error now surfaces at registration time (not kernel construction) with an actionable message that explicitly references `style_profile`, `RuntimeContext`, and `ZHENModule` as the template.
- **Note on residual contract asymmetry:** the fix validates ONLY `get_style_profile()`. The other 6 default lambdas (`get_glossary_mappings=lambda: {}`, `apply_rules=lambda src, _dir: src`, `is_forbidden=lambda _src, _tgt: False`, `get_forbidden_targets=lambda: {}`, `entity_type_hint=lambda _token: None`, `apply_zh_rules=lambda text: text`) all return values compatible with what the kernel/ISA expects, so they don't need validation. This is intentional — only `get_style_profile` had a None-vs-typed-field mismatch.
- **Suggested fix:** none — verified fixed.
- **Round 4 status:** **fixed-and-verified** (was R4 new WARNING, fixed in R4 Batch 3 commit `524c598`).

---

### TRA-F5-005: TRA-F4-007 — `_select_module` matches by FULL direction (R4 new INFO → R5 fixed-and-verified)

- **Severity:** INFO
- **Category:** Stub-Module / Dispatch Semantics
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/kernel.py:149-191` — `_select_module` performs a 2-pass scan:
    - Pass 1 (lines 169-186): prefer a full-direction match — iterate `registry.all()`, normalize `mod_direction.lower()` and `req_direction.lower()`, return on exact match (line 176-177):
      ```python
      if mod_direction_norm and mod_direction_norm == req_direction:
          return mod
      ```
      While scanning, also track the first source-only match as a fallback (lines 178-186).
    - Pass 2 (lines 187-189): if no full match, use the source-only fallback if any.
    - Pass 3 (line 191): no match in registry — fall through to `ZHENModule()`.
  - `tra/kernel.py:159-161` — TRA-F4-007 docstring explicitly documents the fix:
    ```
    TRA-F4-007 (round 4): previously this matched by source language
    only, so two modules with `fr -> en` and `fr -> de` would silently
    dispatch the first one for `--lang fr-de`, masking the user's intent.
    ```
  - Probe 5.a: registry contains `[fr_en (FR -> EN, registered first), fr_de (FR -> DE, registered second)]`; `TRAKernel._select_module("FR -> DE", reg)` returns `fr_de` (selected.name=`fr_de`, direction=`FR -> DE`) — NOT `fr_en`, despite `fr_en` being registered first AND sharing the same source language.
  - Probe 5.b: `TRAKernel._select_module("FR -> EN", reg)` returns `fr_en` (correct full-direction match).
  - Probe 5.c: end-to-end `TRAKernel(cfg={'language_pair':'FR -> DE'}, registry=reg).run("bonjour")` produces `'hallo'` (fr_de's glossary) and NOT `'hello'` (fr_en's glossary) — the registry dispatch actually drives translation output, not just module selection.
  - Regression test `tests/test_outstanding_findings.py::TestTRA_F4_007_SelectModuleFullDirectionMatch` (2 tests: `test_full_direction_match_preferred_over_source_only`, `test_source_only_fallback_when_no_full_match`) passes at HEAD.
- **Detail:** R4's TRA-F4-007 finding flagged that `_select_module` was source-language-prefix-only, so a registry with `fr_en` and `fr_de` would silently pick `fr_en` for `--lang fr-de`. R4 Batch 3 commit `524c598` added the 2-pass scan. R5 confirms the full-direction match is preferred, the source-only fallback is preserved (backward compat for partial-direction queries), and the end-to-end translation uses the correct module's glossary.
- **Suggested fix:** none — verified fixed.
- **Round 4 status:** **fixed-and-verified** (was R4 new INFO, fixed in R4 Batch 3 commit `524c598`).

---

### TRA-F5-006: TRA-099 — CLI `translate` auto-builds the default registry and passes `registry=registry` to `TRAKernel` (R3-R4 PERSISTENT WARNING → R5 fixed-and-verified)

- **Severity:** INFO
- **Category:** CLI Wiring / Module System
- **Finding type:** positive_verification
- **Evidence:**
  - `tra_cli.py:51-69` — `_normalize_language_pair()` normalizes the `--lang` flag value:
    - `zh-en` → `ZH -> EN` (hyphen form, lines 65-67)
    - `zh -> en` → `ZH -> EN` (canonical form, lines 60-63)
    - `fr-en` → `FR -> EN`, `FR -> DE` → `FR -> DE` (case-insensitive)
    - No separator → `v.upper()` (returns as-is, falls back to ZHENModule later — see TRA-F5-010)
  - `tra_cli.py:112-115` — `translate` command applies the override:
    ```python
    if lang:
        # TRA-099 (round 4): normalize --lang to canonical 'XX -> YY' form
        # so _select_module can match it against module direction metadata.
        updates["language_pair"] = _normalize_language_pair(lang)
    ```
  - `tra_cli.py:136-139` — TRA-099 fix block:
    ```python
    from tra.modules.registry import build_default_registry
    registry = build_default_registry()
    kernel = TRAKernel(cfg, registry=registry, interactive=interactive)
    ```
    The CLI auto-builds the default registry on every `translate` invocation and passes `registry=registry` (plus `interactive=interactive`) to `TRAKernel`.
  - Probe 6.a: `tra_cli.py` source contains the string `build_default_registry`.
  - Probe 6.b: `tra_cli.py` source matches the regex `TRAKernel\([^)]*registry\s*=` (confirms `registry=` kwarg is passed).
  - Probe 6.c: `_normalize_language_pair()` correctly normalizes all 7 test cases (`zh-en`, `ZH-EN`, `zh-EN`, `fr-en`, `ZH -> EN`, `zh -> en`, `FR -> DE`) to the canonical `XX -> YY` form.
  - Probe 6.d: end-to-end CLI test via `CliRunner` with a monkeypatched `build_default_registry` (returns a registry containing both `zh_en` and a stub `fr_en` module with glossary `{"bonjour": "hello"}`) — `python -m tra_cli translate ... --lang fr-en --level L1 -o output.md` exited 0 and the output file contains `hello` (the stub's glossary term). ZHENModule would never translate `bonjour` to `hello`; the only way `hello` appears in the output is if the stub FR module was selected and its glossary applied — confirming the registry is wired all the way through.
  - Regression test `tests/test_outstanding_findings.py::TestTRA099CLIPassesRegistry` (3 tests: `test_translate_command_passes_registry`, `test_translate_command_uses_registry_kwarg`, `test_translate_with_non_zh_lang_uses_registry`) passes at HEAD.
- **Detail:** R3-R4's persistent TRA-099 WARNING (`tra_cli.py` constructed `TRAKernel(cfg, interactive=interactive)` with no `registry=` kwarg) is fully resolved by R4 Batch 4 commit `e54b7a7`. R5 confirms the CLI now auto-builds the default registry (which always contains `zh_en` and would pick up any future module added to `build_default_registry()`), normalizes the `--lang` flag, and passes both `registry=` and `interactive=` to `TRAKernel`. The end-to-end CLI test empirically proves a registered non-ZH module is selected and its glossary drives translation output.
- **Limitation noted:** the CLI does NOT accept a `--registry` / `--module` / `--module-path` flag for runtime-loaded custom modules. Users wanting a custom module must either (a) add it to `build_default_registry()` in source, or (b) write a driver script that constructs `TRAKernel` directly. This is the simpler of the two design options R4 considered (R4's TRA-F4-004 suggested fix mentioned "~25 LOC of CLI plumbing" for a `--module my_pkg.fr_en:FrENModule` flag). See TRA-F5-009 below for the INFO-level note.
- **Suggested fix:** none required for the F4-004 finding; a future enhancement could add `--module`/`--module-path` for runtime-loaded modules (low priority — not a regression).
- **Round 4 status:** **fixed-and-verified** (was R3-R4 persistent WARNING, fixed in R4 Batch 4 commit `e54b7a7`).

---

### TRA-F5-007: TRA-100 — `TRA-MODULE-AUTHORING.md` is substantive and actionable (R3-R4 PERSISTENT INFO → R5 fixed-and-verified)

- **Severity:** INFO
- **Category:** Documentation / Module System
- **Finding type:** positive_verification
- **Evidence:**
  - `TRA-MODULE-AUTHORING.md` — 328-line file created by R4 Batch 4 commit `aae0bca`.
  - Has 6 numbered sections: §1 Module Contract, §2 The 7 Required Methods, §3 Registering a Module, §4 Testing Your Module, §5 Checklist, §6 Reference.
  - §1 (lines 13-42) introduces the 3 module kinds (`language`, `domain`, `formatting`) and references `tra/modules/base.py`.
  - §2 (lines 45-157) documents all 7 protocol methods with examples drawn from `ZHENModule`:
    - §2.1 `get_glossary_mappings()` — explains binding invariant, references TRA-072 PolicyResolver.
    - §2.2 `get_style_profile()` — **explicitly** calls out TRA-F4-006: "must NOT return `None`. The `ModuleRegistry.register()` method validates the return shape at registration time and raises a clear `TypeError` if it's `None`."
    - §2.3 `apply_rules(source, direction)` — describes pre/post-processing hook.
    - §2.4 `is_forbidden(source, target)` — drift-target check.
    - §2.5 `get_forbidden_targets()` — drift enumeration.
    - §2.6 `entity_type_hint(token)` — references TRA-038 ambiguity logging.
    - §2.7 `apply_zh_rules(source)` — ZH-specific rule layer.
  - §3 (lines 159-239) covers `as_interface()`, `build_default_registry()`, runtime registration, the 3 registration validations (TRA-097, TRA-098, TRA-F4-006), and CLI usage (TRA-099). Includes a complete `FREnModule.as_interface()` skeleton at lines 172-190:
    ```python
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
  - §4 (lines 243-298) covers unit tests, integration tests through `TRAKernel(cfg, registry=registry)`, benchmark cases in `tests/benchmark/cases/sft.jsonl`, and the 4 critical invariants.
  - §5 (lines 302-313) provides a 10-item checklist for new module authors.
  - §6 (lines 317-329) cross-references `TRA-MODULE-ZH-EN.md`, `tra/modules/zh_en.py`, `tra/modules/base.py`, `tra/modules/registry.py`, `tra/kernel.py:_select_module`, `tra/isa.py:_module`, and the Round 4 audit findings.
  - Probe 10.a-i (9 sub-checks): all PASS — file exists, 328 lines (≥ 100), all 17 expected API terms present (`get_glossary_mappings`, `get_style_profile`, `apply_rules`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`, `as_interface`, `ModuleInterface`, `LanguageModuleProtocol`, `register(`, `build_default_registry`, `TRAKernel`, `metadata.direction`, `FR -> EN`, `StyleProfile`, `EntityType`), all 6 sections present, references TRA-F4-006 + TRA-F4-007 + TRA-099 + TRA-097 + TRA-098 fixes, has `as_interface()` skeleton, has CLI usage example, references `zh_en.py` as template, lists 4 critical invariants.
- **Detail:** R3-R4's persistent TRA-100 INFO (`TRA-MODULE-ZH-EN.md` was purely linguistic, no engineering contract) is fully resolved by R4 Batch 4 commit `aae0bca`. R5 confirms the new `TRA-MODULE-AUTHORING.md` is a complete engineering guide: a new contributor reading it could author a `fr-en` module by following the §3 `as_interface()` skeleton + §5 checklist + §4 testing patterns. The guide correctly references the F4-006/007/099/097/098 fixes from R4.
- **Actionability assessment:** a new contributor could:
  1. Copy the `FREnModule.as_interface()` skeleton from §3.2.
  2. Implement the 7 methods per §2.
  3. Add the module to `build_default_registry()` per §3.3 Option A.
  4. Write unit tests per §4.1.
  5. Write an integration test per §4.2 (template provided).
  6. Add a benchmark case per §4.3 (template provided).
  7. Run the §5 checklist.
  This is a complete, actionable onboarding path.
- **Suggested fix:** none — verified fixed.
- **Round 4 status:** **fixed-and-verified** (was R3-R4 persistent INFO, fixed in R4 Batch 4 commit `aae0bca`).

---

### TRA-F5-008: `ModuleInterface` is a properly-typed dataclass; `LanguageModuleProtocol` is a `Protocol`; `RuntimeContext.module` typed as `LanguageModuleProtocol | None` (TRA-043 holds)

- **Severity:** INFO
- **Category:** Stub-Module / Type Safety
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/modules/registry.py:13-37` — `@dataclass ModuleInterface` with 10 fields: `name: str`, `kind: str` (required positional), 7 `Callable` fields with defaults (`get_glossary_mappings`, `get_style_profile`, `apply_rules`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`), and `metadata: dict[str, Any] = field(default_factory=dict)`.
  - `tra/modules/base.py:14-56` — `@runtime_checkable class LanguageModuleProtocol(Protocol)` with `name: str`, `kind: str` annotations and 7 method signatures. MRO confirmed: `['LanguageModuleProtocol', 'Protocol', 'Generic', 'object']` (probe 7.proto-a).
  - `tra/memory.py:18-21` — `LanguageModuleProtocol` imported at runtime (NOT under `TYPE_CHECKING`) so Pydantic can resolve the forward reference: `from .modules.base import LanguageModuleProtocol`.
  - `tra/memory.py:198` — `RuntimeContext.model_config = ConfigDict(arbitrary_types_allowed=True)` so Pydantic accepts the Protocol field.
  - `tra/memory.py:216` — `module: LanguageModuleProtocol | None = Field(default=None, exclude=True)` (typed as the Protocol, NOT `Any`). Probe 7.rtc-a confirms annotation string = `tra.modules.base.LanguageModuleProtocol | None`.
  - Probe 7.iface-a: `dataclasses.is_dataclass(ModuleInterface)` = True.
  - Probe 7.iface-b: all 7 Callable field names present (`get_glossary_mappings`, `get_style_profile`, `apply_rules`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`).
  - Probe 7.iface-c: only `name` and `kind` have no defaults (required positional).
  - Probe 7.proto-b: Protocol declares all 7 methods.
  - Probe 7.proto-c: Protocol declares `name` and `kind` annotations.
  - Probe 7.rtc-b: annotation does NOT contain bare `Any` (only `LanguageModuleProtocol | None`).
  - Test `tests/test_tra043_protocol.py::test_runtime_context_module_typed_as_protocol` passes at HEAD.
- **Detail:** TRA-043 (R3 fix) closes the type-safety hole where `RuntimeContext.module: Any` allowed `mypy --strict` to miss method-name typos. R5 confirms `mypy --strict tra` still passes (no issues in 20 source files) and the Protocol is `@runtime_checkable` so `isinstance(iface, LanguageModuleProtocol)` works structurally — both `ZHENModule` instances and `ModuleInterface` dataclasses pass the check (probe 1.1b, 11.add-b).
- **Note on Protocol return types:** the Protocol's `get_style_profile() -> object` and `entity_type_hint() -> object | None` are permissive (allow any object); the kernel then enforces the concrete type via Pydantic (`StyleProfile` field on `RuntimeContext`) and via `register()`'s F4-006 validation. This is a deliberate trade-off — the Protocol is permissive so any module can pass the isinstance check, then concrete validation happens at registration time.
- **Suggested fix:** none.
- **Round 4 status:** **verified-holding** (TRA-043 from R3, R4 verified — R5 re-confirms).

---

### TRA-F5-009: `build_default_registry()` returns a registry with the ZH-EN module registered via `as_interface()`

- **Severity:** INFO
- **Category:** Stub-Module / Default Registry
- **Finding type:** positive_verification
- **Evidence:**
  - `tra/modules/registry.py:139-149` — `build_default_registry()`:
    ```python
    def build_default_registry() -> ModuleRegistry:
        from .zh_en import ZHENModule
        registry = ModuleRegistry()
        registry.register(ZHENModule().as_interface())
        return registry
    ```
    Lazily imports `ZHENModule` (avoids circular import), constructs a `ModuleRegistry`, and calls `ZHENModule().as_interface()` to register the bundled module.
  - Probe 8.bdr-a: `build_default_registry().all()` returns 1 module with name `zh_en`.
  - Probe 8.bdr-b: `reg.get("zh_en")` returns a `ModuleInterface` instance (proves `as_interface()` was called, not the raw `ZHENModule`).
  - Probe 8.bdr-c: `zh_en_mod.metadata.get("direction")` = `'ZH -> EN'`.
  - Probe 8.bdr-d: `zh_en_mod.get_glossary_mappings()` returns the canonical 11-entry ZH-EN glossary; `成立 -> Confirmed` and `执行环境 -> execution environment` confirmed.
  - `tests/test_modules.py:58-63` — `test_registry_default_contains_zh_en` passes.
- **Detail:** The default registry contains exactly one module (the bundled ZH-EN). The CLI auto-builds this on every `translate` invocation (`tra_cli.py:138`). Adding a new module to the default registry is a 1-line change in `build_default_registry()` — this is the sanctioned extension point documented in `TRA-MODULE-AUTHORING.md` §3.3 Option A.
- **Suggested fix:** none.
- **Round 4 status:** **verified-holding** (R3 design, R4 verified — R5 re-confirms).

---

### TRA-F5-010: `_normalize_language_pair` silently upper-cases malformed `--lang` values (no separator) — minor UX gap

- **Severity:** WARNING
- **Category:** CLI / Module System
- **Finding type:** issue
- **Evidence:**
  - `tra_cli.py:51-69` — `_normalize_language_pair()`:
    ```python
    def _normalize_language_pair(value: str) -> str:
        v = value.strip()
        if "->" in v:
            src, _, tgt = v.partition("->")
            return f"{src.strip().upper()} -> {tgt.strip().upper()}"
        if "-" in v:
            src, _, tgt = v.rpartition("-")
            return f"{src.strip().upper()} -> {tgt.strip().upper()}"
        # No separator; return as-is (will likely fail later).
        return v.upper()
    ```
  - Probe (manual): `_normalize_language_pair('fr')` returns `'FR'`; `_normalize_language_pair('fr_de')` returns `'FR_DE'`; `_normalize_language_pair('')` returns `''`; `_normalize_language_pair('zh en')` returns `'ZH EN'`. None of these contain ` -> `, so `_select_module` (which compares `req_direction.strip().lower()` against `mod_direction.strip().lower()`) finds no match and silently falls back to `ZHENModule` at `kernel.py:191`.
  - The user's `--lang fr` or `--lang zh en` request is silently overridden by the ZHENModule fallback. There is no warning printed and no error raised; the translation proceeds using ZHENModule's glossary, which is wrong if the source isn't Chinese.
  - The CLI prints `pair=FR` (or `pair=ZH EN`) at `tra_cli.py:121-125`, but the user may not notice this is non-canonical. The actual fallback happens silently in `_select_module` inside the kernel.
- **Detail:** This is a UX gap created by the TRA-099 fix. Before TRA-099, the CLI ignored `--lang` entirely (always used ZHENModule). After TRA-099, the CLI normalizes `--lang` — but only well-formed values (`zh-en`, `zh -> en`). Malformed values (no separator, underscore separator, space separator) silently fall back to ZHENModule, which is exactly the bug pattern TRA-099 was meant to fix. The user gets no signal that their `--lang` value was malformed.
- **Severity rationale:** WARNING because (a) the silent fallback is exactly the failure mode TRA-099 was meant to eliminate; (b) the user has no way to detect the misconfiguration except by inspecting the output for ZHENModule canonical terms; (c) it's a regression in UX (R3-R4 the user knew the CLI ignored `--lang`; R5 the user assumes the CLI honors `--lang`, but malformed values silently don't).
- **Suggested fix:** in `_normalize_language_pair`, raise `click.BadParameter` (or a `ValueError` caught by the CLI) when the input has no `->` and no `-` separator. Alternative: print a WARNING to stderr when normalization produces a value that doesn't match any registered module direction. Estimated effort: ~5 LOC in `_normalize_language_pair` + 1 test.
  ```python
  if "-" not in v and "->" not in v:
      raise click.BadParameter(
          f"--lang {value!r} is not in 'XX-YY' or 'XX -> YY' form; "
          f"cannot normalize."
      )
  ```
- **Round 4 status:** **new** (not in R4 Track F4 — R4's TRA-099 finding only flagged the missing `registry=` kwarg; this UX gap was created by the F4-006/099 remediation itself).

---

### TRA-F5-011: `register()` silently accepts a `kind="language"` module with no `metadata.direction`

- **Severity:** INFO
- **Category:** Stub-Module / Registry Hardening
- **Finding type:** issue
- **Evidence:**
  - `tra/modules/registry.py:106-116` — direction-conflict detection is guarded by `if direction and direction in self._directions:` (line 108) and `if direction:` (line 115). If `metadata.get("direction", "")` returns `""` (no direction key in metadata), the module is registered without any direction index entry.
  - Probe (manual): constructed `ModuleInterface(name="no_direction", kind="language", metadata={}, ...)` (no `direction` key); `registry.register(stub)` succeeds with no error. The module is in `registry.all()` but NOT in `registry._directions`.
  - Probe (manual): `TRAKernel._select_module("ZH -> EN", reg_with_no_direction_module)` falls back to `ZHENModule` because the no-direction module never matches the requested direction.
- **Detail:** A `kind="language"` module is supposed to claim a language direction (per `TRA-MODULE-AUTHORING.md` §3.2, the `as_interface()` skeleton always sets `metadata={"direction": "FR -> EN"}`). A module without a direction is effectively unreachable via `_select_module` — it's silently dead weight in the registry. The `register()` method should reject this with a clear error.
- **Severity rationale:** INFO because (a) the module doesn't crash anything; (b) the bundled `ZHENModule` always sets the direction; (c) the authoring guide explicitly tells authors to set `metadata.direction`. A new contributor who forgets `metadata={"direction": ...}` will silently register a dead module and wonder why their translations don't use it.
- **Suggested fix:** in `register()`, after the protocol check and before the duplicate-name check, add:
  ```python
  if module.kind == "language":
      direction = str(module.metadata.get("direction", ""))
      if not direction:
          raise ValueError(
              f"Module '{module.name}' has kind='language' but no "
              f"metadata.direction. Language modules must declare a "
              f"direction (e.g. metadata={{'direction': 'FR -> EN'}})."
          )
  ```
  Estimated effort: ~7 LOC + 1 test.
- **Round 4 status:** **new** (not in R4 Track F4 — R4's TRA-098 finding only flagged duplicate-name and conflicting-direction detection; the missing-direction case was not probed).

---

### TRA-F5-012: `ModuleInterface` accepts dict-returning `get_style_profile()` (Pydantic coerces), but the authoring guide doesn't document this

- **Severity:** INFO
- **Category:** Documentation / Module System
- **Finding type:** issue
- **Evidence:**
  - `tra/modules/registry.py:80-98` — the F4-006 fix block validates `style_profile is None` and raises `TypeError`. It does NOT validate that the return value is a `StyleProfile` instance — only that it's non-None.
  - `tra/memory.py:184-190` — `StyleProfile` is a Pydantic BaseModel with 4 fields: `voice`, `sentence_complexity`, `epistemic_mapping`, `punctuation_rules`. Pydantic v2 will coerce a dict to a `StyleProfile` instance automatically when assigned to a `StyleProfile`-typed field.
  - `tra/memory.py:205` — `style_profile: StyleProfile = Field(default=StyleProfile)` (RuntimeContext field typed `StyleProfile`, NOT `StyleProfile | dict`).
  - `tra/kernel.py:142-146` — `RuntimeContext(..., style_profile=module.get_style_profile(), ...)` — passes whatever the module returns.
  - Probe 11.add-f: a stub module whose `get_style_profile()` returns `{"voice": "technical", "sentence_complexity": "moderate", "epistemic_mapping": {}, "punctuation_rules": {}}` is accepted by `register()` (no exception).
  - Probe 11.add-g: `TRAKernel(cfg, registry=reg_with_dict_style_module)` constructs successfully — Pydantic coerces the dict to `StyleProfile`.
  - `tra/modules/registry.py:56-61` (F4-006 docstring): mentions "a dict that can be coerced to StyleProfile" — so the dict acceptance IS documented in the source docstring.
  - `TRA-MODULE-AUTHORING.md` §2.2 (lines 70-91): the guide shows returning a `StyleProfile(...)` instance. It does NOT mention that returning a dict is also accepted.
- **Detail:** The `register()` docstring at `registry.py:56-61` mentions dict-coercion, but the authoring guide §2.2 only shows the `StyleProfile` instance pattern. A new contributor reading the guide would not know they could return a dict. This is a minor doc-vs-code gap.
- **Severity rationale:** INFO because (a) the guide's recommended pattern (`return StyleProfile(...)`) is correct and works; (b) the dict alternative is a convenience that the source docstring documents; (c) no crash, no incorrect behavior either way.
- **Suggested fix:** add a one-line note to `TRA-MODULE-AUTHORING.md` §2.2: "Alternatively, you may return a plain dict with the same keys; Pydantic will coerce it to a `StyleProfile` at `RuntimeContext` construction time."
- **Round 4 status:** **new** (the dict-coercion behavior was always present, but the F4-006 fix's docstring at `registry.py:56-61` newly mentioned it; the authoring guide created in the same Batch 4 didn't carry the note forward).

---

### TRA-F5-013: Authoring guide's `LanguageModuleProtocol` snippet omits `name`/`kind` annotations and uses simplified return types

- **Severity:** INFO
- **Category:** Documentation / Module System
- **Finding type:** issue
- **Evidence:**
  - `TRA-MODULE-AUTHORING.md` §1 (lines 27-36) — the Protocol snippet:
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
  - `tra/modules/base.py:14-56` — the actual Protocol:
    ```python
    @runtime_checkable
    class LanguageModuleProtocol(Protocol):
        # Module metadata (used by the registry for dispatch).
        name: str
        kind: str

        def get_glossary_mappings(self) -> dict[str, str]: ...
        def get_style_profile(self) -> object: ...    # guide says StyleProfile
        def is_forbidden(self, source: str, target: str) -> bool: ...
        def get_forbidden_targets(self) -> dict[str, str]: ...
        def entity_type_hint(self, token: str) -> object | None: ...  # guide says EntityType | None
        def apply_zh_rules(self, text: str) -> str: ...   # guide param name: source
        def apply_rules(self, source: str, direction: str) -> str: ...
    ```
  - Differences:
    1. The guide's snippet OMITS the `name: str` and `kind: str` class-level annotations (the actual Protocol declares them at `base.py:27-28`).
    2. The guide shows `get_style_profile() -> StyleProfile`; the actual Protocol types it `-> object` (permissive).
    3. The guide shows `entity_type_hint(token: str) -> EntityType | None`; the actual Protocol types it `-> object | None` (permissive).
    4. The guide shows `apply_zh_rules(self, source: str)`; the actual Protocol uses parameter name `text` (`apply_zh_rules(self, text: str)`).
- **Detail:** The guide's snippet is a "didactic" simplification — it shows what the methods SHOULD return (per the ZHENModule reference impl), not what the Protocol strictly allows. This is mostly fine (the guide's recommended patterns are correct), but:
  - Omitting `name` and `kind` from the Protocol snippet means a new contributor might forget to declare them — `register()` would then raise `TypeError: Module 'X' does not satisfy LanguageModuleProtocol. Missing methods: [...]` (which actually checks methods, not attributes, via `hasattr`), but `isinstance(mod, LanguageModuleProtocol)` would pass because `@runtime_checkable` only checks method presence. The registry stores the module, then `register()` at line 100 does `if module.name in self._modules:` — `module.name` would raise `AttributeError` (a different opaque error).
  - Actually, re-checking: `register()` line 75 does `mod_name = getattr(module, "name", "?")` (safe default) — so a missing `name` doesn't crash. And `register()` line 100 does `if module.name in self._modules:` — but this is only reached after the protocol check, and a module without `name`/`kind` would fail the protocol check (since `@runtime_checkable` Protocol with `name: str` annotation... actually, `runtime_checkable` Protocols only check method presence, NOT attribute annotations). So a module without `name`/`kind` would pass the isinstance check but then crash at line 100 with `AttributeError: 'X' object has no attribute 'name'`. The fix's defensive `getattr(module, "name", "?")` at line 75 is only used in the error message; line 100 directly accesses `module.name`.
- **Severity rationale:** INFO because (a) the bundled `ZHENModule` and the guide's `FREnModule` skeleton both correctly declare `name` and `kind`; (b) the omission in the snippet is a documentation simplification, not a code bug; (c) a new contributor following the §3.2 skeleton would not hit this. The doc-vs-code mismatch is minor.
- **Suggested fix:** update the guide's Protocol snippet in §1 to include the `name: str` and `kind: str` annotations (and optionally note the Protocol types `get_style_profile() -> object` and `entity_type_hint() -> object | None` for permissiveness, with the concrete types documented in §2).
- **Round 4 status:** **new** (the guide was created in R4 Batch 4 commit `aae0bca`; the snippet-vs-actual mismatch was introduced at creation time and not detected by R4 Track F4 because R4 F4 only checked the guide existed, not its API accuracy).

---

## Round 4 carry-over status matrix (Track F scope)

| Round 4 ID | Title | Round 5 status |
|---|---|---|
| TRA-096 | as_interface crashes with ValidationError | **verified-holding** (TRA-F5-001) — all 9 E2E probes PASS; stub glossary `monde -> world` empirically confirmed in translation output |
| TRA-097 | register() lacks isinstance check | **verified-holding** (TRA-F5-002) — BrokenModule rejected with actionable `TypeError` listing all 7 missing methods |
| TRA-098 | register() lacks duplicate detection | **verified-holding** (TRA-F5-003) — duplicate-name + direction-conflict both raise `ValueError`; `unregister()` frees direction slot |
| TRA-099 | CLI `--registry` flag | **fixed-and-verified** (TRA-F5-006) — `tra_cli.py:138-139` calls `build_default_registry()` and passes `registry=registry` to `TRAKernel`; CLI test with stub FR module confirms `hello` appears in output |
| TRA-100 | Module authoring guide | **fixed-and-verified** (TRA-F5-007) — `TRA-MODULE-AUTHORING.md` is 328 LOC, 6 sections, complete `as_interface()` skeleton, CLI usage example, 10-item checklist |
| TRA-F4-006 | Minimal `ModuleInterface` defaults crash | **fixed-and-verified** (TRA-F5-004) — `register()` rejects with `TypeError` naming `style_profile` and pointing to `ZHENModule` template |
| TRA-F4-007 | `_select_module` silent dispatch | **fixed-and-verified** (TRA-F5-005) — full-direction match preferred; `fr_de` selected for `--lang fr-de` even when `fr_en` registered first |

## Round 5 new findings

| ID | Title | Severity | Category |
|---|---|---|---|
| TRA-F5-010 | `_normalize_language_pair` silently upper-cases malformed `--lang` values | WARNING | CLI / Module System |
| TRA-F5-011 | `register()` silently accepts `kind="language"` module with no `metadata.direction` | INFO | Registry Hardening |
| TRA-F5-012 | Dict-returning `get_style_profile()` accepted but undocumented in authoring guide | INFO | Documentation |
| TRA-F5-013 | Authoring guide's Protocol snippet omits `name`/`kind` and uses simplified return types | INFO | Documentation |

(Plus 9 positive verifications: TRA-F5-001 through TRA-F5-009, all INFO.)

## Verification commands run (reproducibility)

```bash
# Run the comprehensive 61-probe stub-module test suite
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype
python /home/z/my-project/tmp_f5/r5_f5_stub_test.py
# → Total: 61   PASS: 61   FAIL: 0

# R4 Batch 3/4 regression tests for F-scope findings
python -m pytest tests/test_outstanding_findings.py -k \
    "TRA002 or TRA096 or TRA097 or TRA098 or TRA099 or TRA_F4_006 or TRA_F4_007" -v
# → 17 passed in 0.45s

# Module + protocol tests
python -m pytest tests/test_modules.py tests/test_tra043_protocol.py -v
# → 20 passed in 0.08s

# Full test suite sanity
python -m pytest tests/
# → 228 passed in 1.48s

# All 4 quality gates at HEAD 5476faf (verified by Track R5 baseline)
ruff check .            # All checks passed
ruff format --check .   # 39 files already formatted
mypy --strict tra       # Success: no issues found in 20 source files
pytest tests            # 228 passed

# Static source checks
rg "build_default_registry" tra_cli.py
# → tra_cli.py:136 (import), 138 (call)

rg "registry=" tra_cli.py
# → tra_cli.py:139 (TRAKernel(cfg, registry=registry, interactive=interactive))

rg "_normalize_language_pair" tra_cli.py
# → tra_cli.py:51 (def), 115 (call)

rg "isinstance.*LanguageModuleProtocol" tra/modules/registry.py
# → tra/modules/registry.py:64 (TRA-097 check inside register())

rg "style_profile is None" tra/modules/registry.py
# → tra/modules/registry.py:91 (TRA-F4-006 fix block)

rg "req_direction.*mod_direction_norm" tra/kernel.py
# → tra/kernel.py:176 (TRA-F4-007 full-direction match)

# Confirm Batch 3/4 commits at HEAD 5476faf
git log --oneline 524c598 -1
# → 524c598 fix(tra): Round 4 Batch 3 — code quality fixes (TRA-A4-011, B4-009, D4-014, F4-006, F4-007)
git log --oneline e54b7a7 -1
# → e54b7a7 fix(tra): TRA-099 (round 4) — CLI translate now passes registry to TRAKernel
git log --oneline aae0bca -1
# → aae0bca docs(tra): TRA-100 (round 4) — create TRA-MODULE-AUTHORING.md guide

# Edge case: malformed --lang values
python -c "from tra_cli import _normalize_language_pair as n; print(n('fr'), n('fr_de'), n(''), n('zh en'))"
# → 'FR' 'FR_DE' '' 'ZH EN'   (all silently uppercased; none canonical)

# Edge case: language module with no metadata.direction
python -c "
from tra.modules.registry import ModuleInterface, ModuleRegistry
from tra.memory import StyleProfile
stub = ModuleInterface(name='no_dir', kind='language',
    get_glossary_mappings=lambda: {},
    get_style_profile=lambda: StyleProfile(),
    apply_rules=lambda s,_d: s, is_forbidden=lambda _s,_t: False,
    get_forbidden_targets=lambda: {}, entity_type_hint=lambda _t: None,
    apply_zh_rules=lambda t: t, metadata={})
reg = ModuleRegistry(); reg.register(stub)
print('registered without direction:', stub.name in reg._modules, 'directions:', reg._directions)
"
# → registered without direction: True directions: {}

# Dict-returning get_style_profile
python -c "
from tra.modules.registry import ModuleInterface, ModuleRegistry
stub = ModuleInterface(name='dict_style', kind='language',
    get_glossary_mappings=lambda: {},
    get_style_profile=lambda: {'voice': 't', 'sentence_complexity': 'm',
        'epistemic_mapping': {}, 'punctuation_rules': {}},
    apply_rules=lambda s,_d: s, is_forbidden=lambda _s,_t: False,
    get_forbidden_targets=lambda: {}, entity_type_hint=lambda _t: None,
    apply_zh_rules=lambda t: t, metadata={'direction': 'ZZ -> YY'})
reg = ModuleRegistry(); reg.register(stub); print('dict-style registered:', stub.name in reg._modules)
"
# → dict-style registered: True
```

## Conclusion

HEAD `5476faf` resolves **all 7 R4 Track F4 findings** (5 fixed-and-verified, 2 verified-holding-positive): the spec's sanctioned module extension path — `as_interface()` → `register()` → `TRAKernel(registry=)` — works end-to-end via both the Python API and the CLI, with a stub `fr-en` module's glossary empirically confirmed in translation output (`monde -> world`, `bonjour -> hello`). The R4 Batch 3 (`524c598`) and Batch 4 (`e54b7a7`/`aae0bca`) remediations are all verified at HEAD with both static source-grep checks and dynamic 61-probe stub-module tests. The bundled `TRA-MODULE-AUTHORING.md` guide is substantive (328 LOC), actionable (a new contributor could author a `fr-en` module by following §2-§5), and correctly references the F4-006/007/099/097/098 fixes.

The **4 new findings** are all minor (1 WARNING, 3 INFO): (a) TRA-F5-010 — the `_normalize_language_pair` UX gap silently upper-cases malformed `--lang` values (e.g., `fr` → `FR`), which then silently fall back to ZHENModule — this is a regression in the sense that TRA-099 was meant to eliminate silent fallbacks; (b) TRA-F5-011 — `register()` accepts a `kind="language"` module with no `metadata.direction`, leaving it silently unreachable; (c) TRA-F5-012 — the dict-coercion behavior of `get_style_profile()` is documented in the source docstring but not in the authoring guide; (d) TRA-F5-013 — the authoring guide's Protocol snippet omits the `name`/`kind` annotations and uses simplified return types vs. the actual Protocol in `base.py`. None are BLOCKING; all four are addressable in a single ~20-LOC follow-up commit (estimated 30 minutes). No regressions detected; all 228 tests + 4 quality gates green at HEAD `5476faf`.
