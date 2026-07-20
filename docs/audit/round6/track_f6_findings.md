# Track F6 — Stub-Module Conformance Re-Audit (Round 6)

**Task ID:** F6-1
**Auditor:** Track F6 (stub-module conformance)
**HEAD audited:** `c4ecd4155d1baa0b4b5d6e60d2e9b1da217e8a46` (TRA prototype engine)
**Codebase root:** `/home/z/my-project/Translation-Runtime-Architecture/tra-prototype/`
**Module-authoring guide:** `/home/z/my-project/Translation-Runtime-Architecture/TRA-MODULE-AUTHORING.md`
**Baseline:** Round 5 Track F5 (`docs/audit/round5/track_f5_findings.md`, 13 findings: 0 BLOCKING / 1 WARNING / 12 INFO) + R5 master register (68 entries) + R6 regression baseline (`docs/audit/round6/track_r6_baseline.md`)
**Methodology:** Direct runtime probes against `tra.modules.registry`, `tra.modules.base`, `tra.modules.zh_en`, `tra_cli._normalize_language_pair`, `tra.kernel.TRAKernel._select_module`; static source inspection via `rg` + `Read`; dataclass introspection via `dataclasses.fields`; cross-check of `TRA-MODULE-AUTHORING.md` Protocol snippet vs. `tra/modules/base.py`; edge-case probes (empty registry, duplicate-name, same-direction conflict, unregister + re-register). Regression test suite filtered to F-scope.

## Verification Run

- HEAD: `git rev-parse HEAD` → `c4ecd4155d1baa0b4b5d6e60d2e9b1da217e8a46` ✓
- Quality gates (F-scope subset): `python -m pytest tests/test_outstanding_findings.py -k "TRA096 or TRA097 or TRA098 or TRA099 or TRA_F4_006 or TRA_F4_007 or TRA_F5_010 or TRA_F5_011 or TRA_F5_012 or TRA_F5_013" -v` → **20 passed in 0.61s** ✓
- Module/protocol/kernel tests: `python -m pytest tests/test_modules.py tests/test_tra043_protocol.py tests/test_kernel.py -v` → **27 passed in 0.27s** ✓
- Full suite (informational only): `python -m pytest tests/` → 308 passed / 1 failed in 2.98s. The single failure (`TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover::test_unknown_term_emits_exception_handler_audit_record`) is **out of Track F6 scope** — it is the cache-hit/EXCEPTION_HANDLER WARNING tracked by Track A6 as TRA-A6-001 and surfaced by Track E6 as TRA-E6-003. It does not affect any stub-module conformance verification in this track.
- mypy --strict: 0 issues (per `c4ecd41` commit message; tracked by Track R6 baseline)
- ruff: clean (per `c4ecd41` commit message; tracked by Track R6 baseline)

## Summary

- **Findings: 8 total (0 BLOCKING / 0 WARNING / 8 INFO)**
- **All 8 task-scope verification items:**

| # | Task item | Result | Evidence |
|---|---|---|---|
| 1 | TRA-096 (`as_interface` + `register` + `TRAKernel(registry=)`) works end-to-end | ✅ PASS | TRA-F6-001 (positive_verification) — stub `FrENModule` glossary term `Bonjour` empirically selected by `_select_module` |
| 2 | TRA-099 (CLI passes registry to TRAKernel) holds | ✅ PASS | TRA-F6-002 (positive_verification) — static regex + dynamic CLI runner test |
| 3 | TRA-F5-010 (`_normalize_language_pair` rejects malformed `--lang`) holds | ✅ PASS | TRA-F6-003 (positive_verification) — 5 malformed values all raise `ValueError` |
| 4 | TRA-F5-011 (`register()` rejects language modules with no `metadata.direction`) holds | ✅ PASS | TRA-F6-004 (positive_verification) — `ValueError` raised with actionable message |
| 5 | `ModuleInterface` contract (7 Callable fields, `LanguageModuleProtocol`) | ✅ PASS | TRA-F6-005 (positive_verification) — 7 method fields exactly match Protocol's 7 method signatures |
| 6 | `build_default_registry()` returns ZH-EN module | ✅ PASS | TRA-F6-006 (positive_verification) — 1 module `zh_en`, direction `ZH -> EN`, 11-entry glossary |
| 7 | Edge cases (empty registry, duplicate modules, same-direction modules) | ✅ PASS | TRA-F6-007 (positive_verification) — 5 edge-case probes all behave correctly |
| 8 | `TRA-MODULE-AUTHORING.md` quality (snippet matches `base.py`, actionable) | ✅ PASS | TRA-F6-008 (positive_verification, with one residual cosmetic drift sub-item tracked as TRA-F6-009) |

- **Carry-over from Round 5 Track F5:** 9 positive verifications re-confirmed (TRA-F5-001/002/003/004/005/006/007/009 + 4 R5-new issues F5-010/011/012/013 — all `fixed-and-verified` per R6 baseline rows 12, 56, 57, 58)
- **New findings:** 1 (TRA-F6-009 INFO — residual cosmetic drift in `TRA-MODULE-AUTHORING.md` §2.7 header parameter name)
- **Regressions:** 0 (expected 0)

---

## Findings

### TRA-F6-001: TRA-096 — `as_interface()` + `register()` + `TRAKernel(registry=)` works end-to-end (R3 BLOCKING → R5 verified-holding → R6 verified-holding)

- **Severity:** INFO
- **Category:** Stub-Module / End-to-End Wiring
- **Finding type:** positive_verification
- **Round 5 status:** verified-holding (R6 baseline row 28, mapped to TRA-F5-001)
- **Evidence:**
  - `tra/modules/registry.py:13-37` — `ModuleInterface` dataclass with 7 `Callable` fields + 3 non-callable fields (`name`, `kind`, `metadata`).
  - `tra/modules/registry.py:51-128` — `ModuleRegistry.register()` performs TRA-097 protocol check (line 64), TRA-F4-006 `get_style_profile()` shape validation (lines 84-98), TRA-098 duplicate-name + direction-conflict detection (lines 100-127), TRA-F5-011 missing-direction rejection (lines 110-119).
  - `tra/modules/registry.py:150-160` — `build_default_registry()` constructs a `ModuleRegistry`, registers `ZHENModule().as_interface()`, and returns it.
  - `tra/kernel.py:127-177` — `TRAKernel.__init__` accepts `registry: ModuleRegistry | None` keyword arg (line 136); passes it to `_select_module` (line 165); constructs `RuntimeContext(module=module)` at line 173-177 with `module.get_style_profile()` and the selected module.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```python
    >>> from tra.modules.registry import ModuleRegistry, build_default_registry
    >>> from tra.modules.zh_en import ZHENModule
    >>> from tra.modules.base import LanguageModuleProtocol
    >>> iface = ZHENModule().as_interface()
    >>> isinstance(iface, LanguageModuleProtocol)
    True
    >>> reg = ModuleRegistry(); reg.register(iface)
    >>> [m.name for m in reg.all()]
    ['zh_en']
    >>> iface.metadata.get("direction")
    'ZH -> EN'
    # Then via TRAKernel(registry=reg):
    >>> kernel = TRAKernel(cfg, registry=reg)
    >>> kernel.ctx.module.name
    'zh_en'
    >>> '成立' in kernel.ctx.module.get_glossary_mappings()
    True
    ```
  - `tests/test_outstanding_findings.py::TestTRA096AsInterfaceProtocol` (3 tests, including `test_stub_fren_module_via_registry` which builds a stub `FrENModule` with `Bonjour → Hello` glossary and asserts the kernel's selected module produces that glossary) — **3/3 PASS** at HEAD `c4ecd41`.
- **Detail:** The spec's sanctioned module extension path — `as_interface()` → `register()` → `TRAKernel(registry=)` — works end-to-end via both the Python API and the CLI. The Round-3 BLOCKING (ModuleInterface only had 3 Callable fields, Pydantic rejected it as "not a LanguageModuleProtocol") is fully resolved: `ModuleInterface` now carries all 7 Protocol methods, `ZHENModule().as_interface()` returns a fully-wired `ModuleInterface` instance, and `TRAKernel(registry=reg)` constructs `RuntimeContext(module=module)` without `ValidationError`. A stub `FrENModule` registered via `as_interface()` is correctly dispatched by `_select_module("FR -> EN", reg)`.
- **Suggested fix:** none.
- **Round 5 status:** **verified-holding** (R3 fix, R4 verified, R5 re-confirmed, R6 re-confirmed).

---

### TRA-F6-002: TRA-099 — CLI `translate` auto-builds the default registry and passes `registry=registry` to `TRAKernel` (R3-R4 PERSISTENT WARNING → R5 fixed-and-verified → R6 verified-holding)

- **Severity:** INFO
- **Category:** CLI Wiring / Module System
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (R5 commit `e54b7a7`; R6 baseline row 50 confirms via `README.md:90` reference; re-verified at HEAD `c4ecd41`)
- **Evidence:**
  - `tra_cli.py:114-204` — `translate` command body:
    - Lines 151-154: `--lang` override normalized via `_normalize_language_pair(lang)`.
    - Lines 175-177: `from tra.modules.registry import build_default_registry; registry = build_default_registry()`.
    - Lines 178-183: `kernel = TRAKernel(cfg, registry=registry, interactive=interactive, force_unrecoverable=force_unrecoverable)`.
  - **Reproduction (static source inspection, executed at HEAD `c4ecd41`):**
    ```
    'build_default_registry' in cli_src = True
    regex 'TRAKernel\([^)]*registry\s*=' matches cli_src = True
    ```
  - `tests/test_outstanding_findings.py::TestTRA099CLIPassesRegistry` (3 tests):
    1. `test_translate_command_passes_registry` — static source asserts `'build_default_registry' in source or 'registry=' in source`.
    2. `test_translate_command_uses_registry_kwarg` — static source regex asserts `TRAKernel\([^)]*registry\s*=`.
    3. `test_translate_with_non_zh_lang_uses_registry` — end-to-end CliRunner test: monkeypatches `build_default_registry` to include a stub `fr_en` module with glossary `{"bonjour": "hello"}`, runs `cli translate input.md --lang fr-en --level L1`, asserts output contains `"hello"` (a term ZHENModule would never produce).
    - **3/3 PASS** at HEAD `c4ecd41`.
  - `tra_cli.py:160-164` prints `pair={cfg.language_pair}` so the user can confirm the normalized value before the kernel constructs.
- **Detail:** The CLI's `translate` command auto-builds the default registry on every invocation and passes it to `TRAKernel` via the `registry=` keyword arg. This means (a) the bundled `zh_en` module is always available, (b) future modules added to `build_default_registry()` are picked up automatically, (c) `_select_module` (TRA-F4-007 full-direction match) honors the user's `--lang` override rather than silently falling back to ZHENModule. End-to-end CLI runner test empirically confirms a stub FR module's glossary drives translation output.
- **Limitation noted (carry-over from R5):** the CLI does NOT accept a `--registry` / `--module` / `--module-path` flag for runtime-loaded custom modules; users wanting a custom module must either add it to `build_default_registry()` in source or write a driver script that constructs `TRAKernel` directly. This is the simpler of the two design options R4 considered and is not a regression.
- **Suggested fix:** none required for the F-scope contract; a future enhancement could add `--module` / `--module-path` for runtime-loaded modules (low priority — not a regression).
- **Round 5 status:** **fixed-and-verified** (was R3-R4 persistent WARNING, fixed in R4 Batch 4 commit `e54b7a7`; R6 re-confirms at HEAD `c4ecd41`).

---

### TRA-F6-003: TRA-F5-010 — `_normalize_language_pair` rejects malformed `--lang` values (R5 WARNING → R6 fixed-and-verified)

- **Severity:** INFO
- **Category:** CLI / Module System
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (R5 Batch 5 commit `bfde6dd`; R6 baseline row 12)
- **Evidence:**
  - `tra_cli.py:51-96` — `_normalize_language_pair()`:
    - Lines 64-69: empty string raises `ValueError("Language pair is empty. Expected '<source>-<target>' …")`.
    - Lines 70-79: canonical `->` form parses `src`/`tgt`, raises if either is empty.
    - Lines 80-89: hyphen form `xx-yy` parses via `rpartition("-")`, raises if either is empty.
    - Lines 90-96: **no separator** (e.g. `fr`, `fr_de`, `zh en`, `xxx`) raises `ValueError("Language pair {value!r} is malformed: expected '<source>-<target>' … Without a separator, the kernel would silently fall back to the default ZH-EN module, masking the user's intent.")`.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```
    _normalize_language_pair('fr')       -> raises ValueError: Language pair 'fr' is malformed…
    _normalize_language_pair('')         -> raises ValueError: Language pair is empty…
    _normalize_language_pair('fr_de')    -> raises ValueError: Language pair 'fr_de' is malformed…
    _normalize_language_pair('zh en')    -> raises ValueError: Language pair 'zh en' is malformed…
    _normalize_language_pair('xxx')      -> raises ValueError: Language pair 'xxx' is malformed…
    # Sanity: valid forms still pass
    _normalize_language_pair('zh-en')    -> 'ZH -> EN'
    _normalize_language_pair('ZH -> EN') -> 'ZH -> EN'
    ```
  - `tests/test_outstanding_findings.py::TestTRA_F5_010_NormalizeLanguagePairRejectsMalformed` (4 tests: `test_rejects_no_separator`, `test_rejects_empty_string`, `test_accepts_hyphen_form`, `test_accepts_canonical_form`) — **4/4 PASS** at HEAD `c4ecd41`.
- **Detail:** Round 5 Batch 5 (`bfde6dd`) closed the UX gap whereby malformed `--lang` values were silently upper-cased (`fr` → `FR`) and then fell back to ZHENModule because no `FR` module was registered. Now `ValueError` is raised with an actionable message that explains the expected format and explicitly mentions the silent-fallback failure mode the check prevents. The CLI's `--lang` override is honored for well-formed inputs and loudly rejected for malformed inputs.
- **Suggested fix:** none.
- **Round 5 status:** **fixed-and-verified** (was R5 WARNING; R6 re-confirms at HEAD `c4ecd41`).

---

### TRA-F6-004: TRA-F5-011 — `register()` rejects language modules with no `metadata.direction` (R5 INFO → R6 fixed-and-verified)

- **Severity:** INFO
- **Category:** Registry Hardening
- **Finding type:** positive_verification
- **Round 5 status:** fixed-and-verified (R5 Batch 5 commit `bfde6dd`; R6 baseline row 56)
- **Evidence:**
  - `tra/modules/registry.py:110-119` — TRA-F5-011 fix block:
    ```python
    if module.kind == "language":
        direction = str(module.metadata.get("direction", "")).strip()
        if not direction:
            raise ValueError(
                f"Language module '{module.name}' has no metadata.direction. "
                f"A language module must declare its direction "
                f"(e.g. metadata={{'direction': 'ZH -> EN'}}) so the "
                f"kernel's _select_module can dispatch it. Without a "
                f"direction, the module is silently unreachable."
            )
    ```
    The check fires AFTER the TRA-097 protocol check and AFTER the TRA-F4-006 `get_style_profile()` shape validation, but BEFORE the TRA-098 duplicate-name / direction-conflict checks — surfacing the missing-direction error before any state mutation.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```python
    >>> zhen = ZHENModule()
    >>> stub_no_dir = ModuleInterface(
    ...     name='stub-no-direction', kind='language',
    ...     get_glossary_mappings=zhen.get_glossary_mappings,
    ...     get_style_profile=zhen.get_style_profile,    # valid (passes F4-006)
    ...     apply_rules=zhen.apply_rules, is_forbidden=zhen.is_forbidden,
    ...     get_forbidden_targets=zhen.get_forbidden_targets,
    ...     entity_type_hint=zhen.entity_type_hint,
    ...     apply_zh_rules=zhen.apply_zh_rules,
    ...     metadata={},   # ← no "direction" key
    ... )
    >>> reg = ModuleRegistry(); reg.register(stub_no_dir)
    ValueError: Language module 'stub-no-direction' has no metadata.direction.
    A language module must declare its direction (e.g. metadata={'direction': 'ZH -> EN'})
    so the kernel's _select_module can dispatch it. Without a direction, the
    module is silently unreachable.
    # Sanity: build_default_registry still works (ZH-EN has direction):
    >>> def_reg = build_default_registry()
    >>> any(m.kind == 'language' and m.metadata.get('direction') for m in def_reg.all())
    True
    ```
  - `tests/test_outstanding_findings.py::TestTRA_F5_011_RegisterRejectsLanguageModuleWithoutDirection` (2 tests: `test_register_rejects_language_module_without_direction`, `test_register_accepts_language_module_with_direction`) — **2/2 PASS** at HEAD `c4ecd41`.
- **Detail:** Round 5 Batch 5 (`bfde6dd`) closed the silent-unreachability gap whereby a `kind="language"` module with no `metadata.direction` would register successfully but be invisible to `_select_module` (which filters by direction). The error message is actionable: it names the offending module, explains the contract (language modules must declare a direction), and explains the failure mode (silent unreachability) so the contributor knows why the check exists.
- **Suggested fix:** none.
- **Round 5 status:** **fixed-and-verified** (was R5 INFO; R6 re-confirms at HEAD `c4ecd41`).

---

### TRA-F6-005: `ModuleInterface` contract — 7 `Callable` fields exactly match `LanguageModuleProtocol`'s 7 method signatures

- **Severity:** INFO
- **Category:** Stub-Module / Type-Safety Contract
- **Finding type:** positive_verification
- **Round 5 status:** verified-holding (R5 TRA-F5-008; R6 baseline row 28 — mapped to TRA-F5-001 cluster)
- **Evidence:**
  - `tra/modules/registry.py:13-37` — `ModuleInterface` dataclass fields:
    ```python
    @dataclass
    class ModuleInterface:
        name: str
        kind: str
        get_glossary_mappings: Callable[[], dict[str, str]] = lambda: {}
        get_style_profile: Callable[[], object] = lambda: None
        apply_rules: Callable[[str, str], str] = lambda src, _dir: src
        is_forbidden: Callable[[str, str], bool] = lambda _src, _tgt: False
        get_forbidden_targets: Callable[[], dict[str, str]] = lambda: {}
        entity_type_hint: Callable[[str], object | None] = lambda _token: None
        apply_zh_rules: Callable[[str], str] = lambda text: text
        metadata: dict[str, Any] = field(default_factory=dict)
    ```
  - `tra/modules/base.py:14-56` — `LanguageModuleProtocol` declares exactly 7 method signatures + 2 attribute annotations (`name: str`, `kind: str`).
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```python
    >>> import dataclasses
    >>> from tra.modules.registry import ModuleInterface
    >>> from tra.modules.base import LanguageModuleProtocol
    >>> fields = dataclasses.fields(ModuleInterface)
    >>> callable_fields = [f for f in fields if f.name not in ('name', 'kind', 'metadata')]
    >>> len(fields), len(callable_fields)
    (10, 7)
    >>> sorted(f.name for f in callable_fields)
    ['apply_rules', 'apply_zh_rules', 'entity_type_hint',
     'get_forbidden_targets', 'get_glossary_mappings',
     'get_style_profile', 'is_forbidden']
    >>> sorted(m for m in dir(LanguageModuleProtocol) if not m.startswith('_'))
    ['apply_rules', 'apply_zh_rules', 'entity_type_hint',
     'get_forbidden_targets', 'get_glossary_mappings',
     'get_style_profile', 'is_forbidden']
    # ModuleInterface also carries the 2 Protocol attribute annotations:
    >>> 'name' in {f.name for f in fields}, 'kind' in {f.name for f in fields}
    (True, True)
    ```
  - `tests/test_tra043_protocol.py` — verifies `isinstance(ZHENModule(), LanguageModuleProtocol)` returns `True` and `isinstance(ZHENModule().as_interface(), LanguageModuleProtocol)` returns `True` (the latter is the TRA-096 round-3 fix that surfaced the original contract gap). **3/3 PASS** at HEAD `c4ecd41`.
  - `tests/test_outstanding_findings.py::TestTRA043Protocol` — verifies the `LanguageModuleProtocol` is `@runtime_checkable` and structural typing is enforced at runtime by `register()` (TRA-097). **All PASS** at HEAD `c4ecd41`.
- **Detail:** The dataclass-form `ModuleInterface` and the Protocol-form `LanguageModuleProtocol` are kept in lock-step: both declare exactly 7 method names with matching signatures. `as_interface()` (TRA-096) wires all 7 callable fields explicitly, never relying on the dataclass defaults (which exist only for backward-compat with ad-hoc test stubs). Pydantic's `RuntimeContext.module: LanguageModuleProtocol` typing (with `arbitrary_types_allowed=True` at `tra/memory.py:235`) accepts `ModuleInterface` instances because they structurally satisfy the Protocol. The Round-3 BLOCKING (3-vs-7 mismatch) and Round-4 WARNING (TRA-F4-006 minimal-defaults crash) are both fully resolved.
- **Suggested fix:** none.
- **Round 5 status:** **verified-holding** (R3 design, R4 verified, R5 re-confirmed, R6 re-confirmed).

---

### TRA-F6-006: `build_default_registry()` returns a registry containing the ZH-EN module registered via `as_interface()`

- **Severity:** INFO
- **Category:** Stub-Module / Default Registry
- **Finding type:** positive_verification
- **Round 5 status:** verified-holding (R5 TRA-F5-009; R6 baseline row 55)
- **Evidence:**
  - `tra/modules/registry.py:150-160` — `build_default_registry()`:
    ```python
    def build_default_registry() -> ModuleRegistry:
        from .zh_en import ZHENModule
        registry = ModuleRegistry()
        registry.register(ZHENModule().as_interface())
        return registry
    ```
    Lazily imports `ZHENModule` (avoids circular import with `kernel.py`), constructs a `ModuleRegistry`, calls `ZHENModule().as_interface()` to wrap the module in a `ModuleInterface`, and registers it.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```python
    >>> reg = build_default_registry()
    >>> len(reg.all())
    1
    >>> reg.get('zh_en').kind
    'language'
    >>> reg.get('zh_en').metadata.get('direction')
    'ZH -> EN'
    >>> reg.get('zh_en').get_glossary_mappings()['成立']
    'Confirmed'
    >>> reg.get('zh_en').get_glossary_mappings()['执行环境']
    'execution environment'
    >>> # The default registry contains EXACTLY one module (the bundled ZH-EN):
    >>> type(reg.get('zh_en')).__name__
    'ModuleInterface'   # proves as_interface() was called, not the raw ZHENModule
    ```
  - `tra_cli.py:175-177` — CLI auto-builds via `build_default_registry()` on every `translate` invocation.
  - `tests/test_modules.py:58-63` — `test_registry_default_contains_zh_en` asserts `reg.get("zh_en").kind == "language"` and `"zh_en" in {m.name for m in reg.all()}`. **PASS** at HEAD `c4ecd41`.
  - `tests/test_modules.py:66-72` — `test_registry_unknown_raises` asserts `reg.get("fr_en")` raises `KeyError`. **PASS** at HEAD `c4ecd41`.
  - `tests/test_modules.py:75-78` — `test_registry_scoped_to_language_pair` asserts `registry_for_language_pair("ZH -> EN")` returns a scoped registry containing `zh_en`. **PASS** at HEAD `c4ecd41`.
  - `tests/test_modules.py:81-87` — `test_module_as_interface_contract` asserts `ZHENModule().as_interface()` returns a `ModuleInterface` instance with the canonical ZH-EN glossary and that `apply_rules("系统成立。", "ZH -> EN")` dispatches through the wrapper to produce `"The system is Confirmed."`. **PASS** at HEAD `c4ecd41`.
- **Detail:** The default registry contains exactly one module (the bundled ZH-EN), registered through `as_interface()` (not the raw `ZHENModule`), with `metadata.direction = 'ZH -> EN'`. The CLI auto-builds this on every `translate` invocation. Adding a new module to the default registry is a 1-line change in `build_default_registry()` — this is the sanctioned extension point documented in `TRA-MODULE-AUTHORING.md` §3.3 Option A and `SKILL.md` §6.
- **Suggested fix:** none.
- **Round 5 status:** **verified-holding** (R3 design, R4 verified, R5 re-confirmed, R6 re-confirmed).

---

### TRA-F6-007: Edge cases — empty registry, duplicate modules, same-direction modules, unregister + re-register all behave correctly

- **Severity:** INFO
- **Category:** Stub-Module / Registry Hardening (TRA-098 + TRA-F5-011)
- **Finding type:** positive_verification
- **Round 5 status:** verified-holding (R5 TRA-F5-003 + TRA-F5-011; R6 baseline rows 30 + 56)
- **Evidence:**
  - `tra/modules/registry.py:47-49` — `ModuleRegistry.__init__` initializes `self._modules: dict[str, ModuleInterface] = {}` and `self._directions: dict[str, str] = {}` (empty by construction).
  - `tra/modules/registry.py:99-104` — TRA-098 duplicate-name detection:
    ```python
    if module.name in self._modules:
        raise ValueError(
            f"Module '{module.name}' is already registered. "
            f"Use unregister() first if you intend to replace it."
        )
    ```
  - `tra/modules/registry.py:120-127` — TRA-098 direction-conflict detection:
    ```python
    if direction in self._directions:
        existing = self._directions[direction]
        raise ValueError(
            f"Direction conflict: module '{module.name}' has direction "
            f"'{direction}' which is already registered by module "
            f"'{existing}'. Only one module per direction is allowed."
        )
    self._directions[direction] = module.name
    ```
  - `tra/modules/registry.py:130-139` — `unregister(name)` removes the module AND cleans up the direction index (only if the direction is currently owned by the removed module).
  - `tra/kernel.py:180-224` — `_select_module(language_pair, registry)` falls back to `ZHENModule()` when the registry is `None` OR when no module matches the requested direction. This means an empty `ModuleRegistry()` instance still produces a working kernel (backward compat).
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```
    7a. empty registry.all() count: 0
        empty registry.get('zh_en') -> KeyError: "Module 'zh_en' not registered"
    7b. TRAKernel(cfg, registry=empty_reg).ctx.module.name -> 'zh_en'  (ZHENModule fallback)
    7c. duplicate-name 'zh_en' -> ValueError: Module 'zh_en' is already registered.
        Use unregister() first if you intend to replace it.
    7d. same-direction (different name) 'zh_en_v2' with direction 'ZH -> EN'
        -> ValueError: Direction conflict: module 'zh_en_v2' has direction
        'ZH -> EN' which is already registered by module 'zh_en_v1'.
        Only one module per direction is allowed.
    7e. unregister('zh_en_v1') then register('zh_en_v2' with same direction)
        -> succeeds; registry.all() == ['zh_en_v2']
        (unregister correctly freed the direction slot)
    ```
  - `tests/test_outstanding_findings.py::TestTRA098RegistryDuplicateDetection` (3 tests: `test_duplicate_name_raises`, `test_conflicting_direction_warns`, `test_unregister_removes_module`) — **3/3 PASS** at HEAD `c4ecd41`.
  - `tests/test_outstanding_findings.py::TestTRA_F5_011_RegisterRejectsLanguageModuleWithoutDirection` — verifies the missing-direction edge case is rejected (TRA-F5-011). **2/2 PASS** at HEAD `c4ecd41`.
- **Detail:** All four edge cases are handled correctly:
  1. **Empty registry** — `registry.all() == []`, `registry.get(name)` raises `KeyError`, and `TRAKernel(cfg, registry=empty)` falls back to `ZHENModule()` (no crash, no silent misbehavior).
  2. **Duplicate names** — second `register()` with the same `name` raises `ValueError` mentioning the name and pointing to `unregister()` as the replacement path.
  3. **Same-direction conflict** — second `register()` with a different `name` but the same `direction` raises `ValueError` mentioning both modules and the conflicting direction.
  4. **unregister + re-register** — `unregister(name)` removes the module and frees the direction slot, allowing a new module with the same direction to be registered afterward.

  These invariants collectively prevent the silent-overwrite footgun that Round 3's TRA-098 finding originally flagged.
- **Suggested fix:** none.
- **Round 5 status:** **verified-holding** (R3 design, R4 verified, R5 re-confirmed; TRA-F5-011 missing-direction sub-case was R5 INFO → R6 fixed-and-verified).

---

### TRA-F6-008: `TRA-MODULE-AUTHORING.md` quality — substantive, actionable, Protocol snippet matches `base.py` (with one residual cosmetic drift sub-item, see TRA-F6-009)

- **Severity:** INFO
- **Category:** Documentation / Module System
- **Finding type:** positive_verification
- **Round 5 status:** verified-holding (R5 TRA-F5-007 + TRA-F5-012 + TRA-F5-013; R6 baseline rows 31, 57, 58)
- **Evidence:**
  - `TRA-MODULE-AUTHORING.md` — **349-line file** with 6 numbered sections: §1 Module Contract, §2 The 7 Required Methods, §3 Registering a Module, §4 Testing Your Module, §5 Checklist, §6 Reference.
  - **§1 Protocol snippet (lines 27-44) matches `tra/modules/base.py:14-56` exactly:**
    - Both have `@runtime_checkable` decorator ✓
    - Both have `name: str` and `kind: str` class-level annotations ✓
    - Both declare the same 7 methods with matching signatures:
      `get_glossary_mappings() -> dict[str, str]`,
      `get_style_profile() -> object`,
      `is_forbidden(self, source: str, target: str) -> bool`,
      `get_forbidden_targets() -> dict[str, str]`,
      `entity_type_hint(self, token: str) -> object | None`,
      `apply_zh_rules(self, text: str) -> str`,
      `apply_rules(self, source: str, direction: str) -> str`
    - Both use `-> object` (not `-> StyleProfile`) and `-> object | None` (not `-> EntityType | None`) — the permissive typing is intentional (Protocols cannot reference Pydantic models in a different module without circular imports; this is documented in the guide's note at lines 46-50).
  - **§2 documents all 7 methods** with examples drawn from `ZHENModule`:
    - §2.1 `get_glossary_mappings()` — explains binding invariant, references TRA-072 PolicyResolver.
    - §2.2 `get_style_profile()` — explicitly calls out TRA-F4-006 ("must NOT return `None`"); the TRA-F5-012 note (lines 96-101) documents that returning a `dict` is accepted (Pydantic coerces) but a `StyleProfile` instance is preferred.
    - §2.3 `apply_rules(source, direction)` — describes pre/post-processing hook.
    - §2.4 `is_forbidden(source, target)` — describes drift-target detection.
    - §2.5 `get_forbidden_targets()` — describes drift-target enumeration.
    - §2.6 `entity_type_hint(token)` — describes ENTITY_AMBIGUITY logging path (TRA-038).
    - §2.7 `apply_zh_rules(source: str) -> str` — describes ZH-specific rule layer. (Note: §2.7 header still uses the parameter name `source`, whereas the §1 Protocol snippet and `base.py` both use `text` — see TRA-F6-009 below.)
  - **§3 (lines 181-261) — registration guide:**
    - §3.1 Module class skeleton (references `ZHENModule` as the template).
    - §3.2 `as_interface()` skeleton — shows ALL 7 method fields + `metadata={"direction": "FR -> EN"}` (TRA-F5-011 contract).
    - §3.3 Two registration paths: Option A (add to `build_default_registry()`), Option B (runtime registration in user code).
    - §3.4 Registration validation — documents the 3 validations performed by `register()` (TRA-097 protocol check, TRA-F4-006 style-profile check, TRA-098 duplicate/conflict check). **Note:** §3.4 does NOT yet mention the TRA-F5-011 missing-direction check (added in R5 Batch 5); this is a minor doc-lag but the source code does enforce it and `§3.2 as_interface()` skeleton correctly sets `metadata={"direction": ...}`, so a contributor following the guide would not hit it.
    - §3.5 CLI usage (TRA-099) — shows `python -m tra_cli translate input.md --lang fr-en --level L3` and explains `_normalize_language_pair` normalization.
  - **§4 (lines 264-321) — testing guide:** unit-test pattern, integration-test pattern (through `TRAKernel(cfg, registry=registry)`), benchmark-case pattern, 4 critical invariants list.
  - **§5 (lines 323-335) — 10-item new-module checklist:** class implements 7 methods, `get_style_profile` non-None, `as_interface()` carries `metadata.direction`, etc. Ends with "All 4 quality gates green" command.
  - **§6 (lines 338-349) — reference:** links to `TRA-MODULE-ZH-EN.md`, `tra/modules/zh_en.py`, `tra/modules/base.py`, `tra/modules/registry.py`, `kernel.py:_select_module`, `isa.py:_module`, and the R4 audit findings.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```
    8a. Total lines: 349
    8b. Has Protocol snippet: True
    8c. Snippet includes name/kind annotations: True
    8d. Snippet includes all 7 methods: True
    8e. Has as_interface skeleton: True
    8f. Has build_default_registry() reference: True
    8g. Has Checklist section: True
    8h. References TRA-F4-006: True
    8i. References TRA-F4-007: True
    8j. References TRA-099: True
    8k. References TRA-F5-012: True
    8l. Mentions dict-coercion alternative: True
    ```
  - `tests/test_outstanding_findings.py::TestTRA100ModuleAuthoringGuide` — verifies the guide exists, is substantive, and references the F4-006/F4-007/099/097/098 fixes. **All PASS** at HEAD `c4ecd41`.
- **Detail:** The Round-5 Batch-5 fix (`bfde6dd`) closed the TRA-F5-012 (dict-coercion note) and TRA-F5-013 (snippet-vs-base.py drift) gaps: the §1 snippet now includes `name: str` / `kind: str` annotations and uses the permissive `-> object` / `-> object | None` return types matching `base.py`. The §2.2 dict-coercion note documents that returning a plain `dict` is accepted by `register()` (Pydantic coerces) but a `StyleProfile` instance is preferred for type safety. The guide is actionable: a new contributor reading §1-§5 + the §5 checklist can author a `fr-en` module in ~30 minutes by following the patterns. The §3.2 skeleton wires all 7 callable fields + `metadata.direction`, so the TRA-F5-011 contract is satisfied by construction.
- **Suggested fix:** see TRA-F6-009 below for a minor cosmetic drift in §2.7's section header.
- **Round 5 status:** **verified-holding** (R4 design via commit `aae0bca`; R5 re-confirmed with F5-012/F5-013 fixes via commit `bfde6dd`; R6 re-confirms at HEAD `c4ecd41`).

---

### TRA-F6-009: `TRA-MODULE-AUTHORING.md` §2.7 section header uses parameter name `source` while the actual Protocol and §1 snippet use `text` (NEW INFO — residual cosmetic drift from TRA-F5-013 partial fix)

- **Severity:** INFO
- **Category:** Documentation / Module System
- **Finding type:** issue (cosmetic doc-drift)
- **Round 5 status:** new (residual of TRA-F5-013's partial fix in R5 Batch 5 commit `bfde6dd`)
- **Evidence:**
  - `TRA-MODULE-AUTHORING.md` §1 Protocol snippet (lines 27-44) — `apply_zh_rules(self, text: str) -> str: ...` ✓ matches `base.py:50`.
  - `TRA-MODULE-AUTHORING.md` §2.7 section header (line 169):
    ```
    ### 2.7 `apply_zh_rules(source: str) -> str`
    ```
    The header uses parameter name `source`, but the §1 snippet (line 42) and `tra/modules/base.py:50` both use parameter name `text`.
  - `TRA-MODULE-AUTHORING.md` §2.7 body (lines 171-177):
    ```
    The ZH-specific rule layer. Called by `_rule_translate` BEFORE the
    epistemic lexicon and glossary substitution passes. This is where
    topic-comment forms (`系统成立` → `The system is Confirmed`) are
    resolved so the atomic `成立 → Confirmed` substitution doesn't split
    them apart.

    For non-ZH modules, this can be a no-op (`return source`).
    ```
    The body's "no-op (`return source`)" should be `return text` to match the actual signature.
  - `TRA-MODULE-AUTHORING.md` §3.2 `as_interface()` skeleton (lines 198-211):
    ```python
    apply_zh_rules=lambda text: text,  # no-op for non-ZH
    ```
    The skeleton correctly uses `text` ✓ — so a contributor following §3.2 produces a correct module. The drift is confined to the §2.7 section header and body.
  - `tra/modules/zh_en.py:162-176` — `def apply_zh_rules(self, text: str) -> str:` uses parameter name `text` ✓.
  - `tra/modules/base.py:50` — `def apply_zh_rules(self, text: str) -> str:` uses parameter name `text` ✓.
  - **Reproduction (executed at HEAD `c4ecd41`):**
    ```
    base.py apply_zh_rules signature:    def apply_zh_rules(self, text: str)
    §1 snippet apply_zh_rules signature: def apply_zh_rules(self, text: str)
    §3.2 skeleton apply_zh_rules:        apply_zh_rules=lambda text: text,  # no-op for non-ZH
    §2.7 header text:                    ### 2.7 `apply_zh_rules(source: str) -> str`
    §2.7 body text:                      For non-ZH modules, this can be a no-op (`return source`).
    ```
- **Detail:** The Round-5 Batch-5 fix for TRA-F5-013 (commit `bfde6dd`) updated the §1 Protocol snippet to match `base.py` exactly (parameter name `text`, return type `-> str`). However, the same fix did NOT propagate to §2.7's section header and body text, which still use the older parameter name `source`. The drift is purely cosmetic: parameter names are not enforced by `@runtime_checkable` Protocols (only method presence and order are checked), and a contributor following the §3.2 `as_interface()` skeleton would produce a correct module (`lambda text: text`). The drift is also self-consistent within §2.7 (header + body both say `source`), so a reader who only reads §2.7 sees a coherent (if non-canonical) signature. The §1 canonical snippet and §3.2 skeleton both correctly use `text`. **No functional impact** — the contract is enforced by `LanguageModuleProtocol` at the type level and by `register()`'s TRA-097 protocol check at runtime, neither of which inspects parameter names.
- **Severity rationale:** INFO because (a) no functional impact (parameter names are not part of structural typing); (b) the §1 canonical snippet (which the contributor reads first) is correct; (c) the §3.2 skeleton (which the contributor copies) is correct; (d) the drift is confined to one section header + body in §2.7; (e) the bundled `ZHENModule` reference impl uses `text` so a contributor copying from `tra/modules/zh_en.py` would also produce a correct module.
- **Suggested fix:** update §2.7 header from ``### 2.7 `apply_zh_rules(source: str) -> str` `` to ``### 2.7 `apply_zh_rules(text: str) -> str` ``, and update §2.7 body's last line from `For non-ZH modules, this can be a no-op (\`return source\`).` to `For non-ZH modules, this can be a no-op (\`return text\`).` Estimated effort: 2-line diff. Optionally also update §3.4 to add a 4th bullet documenting the TRA-F5-011 missing-direction check (the source code enforces it but §3.4 still lists only 3 validations).
- **Round 5 status:** **new** (residual of TRA-F5-013's partial fix in R5 Batch 5 commit `bfde6dd`; the R5 F5-013 finding's "suggested fix" scope was explicitly limited to §1 snippet — "update the guide's Protocol snippet in §1 to include the `name: str` and `kind: str` annotations" — and §2.7 was not in scope at R5; this R6 finding formally extends the fix scope to §2.7).

---

## Round 5 carry-over status matrix (Track F scope)

| Round 5 ID | Title | Round 6 status |
|---|---|---|
| TRA-F5-001 | TRA-096 as_interface + register + TRAKernel(registry=) e2e works | **verified-holding** (TRA-F6-001) — stub FrENModule glossary term `Bonjour` empirically selected; TRAKernel constructs without `ValidationError` |
| TRA-F5-002 | TRA-097 register() performs isinstance check | **verified-holding** — `tra/modules/registry.py:64-79` `isinstance(module, LanguageModuleProtocol)` raises `TypeError` listing missing methods |
| TRA-F5-003 | TRA-098 register() detects duplicate names + conflicting directions; unregister() present | **verified-holding** (TRA-F6-007) — duplicate-name and direction-conflict both raise `ValueError`; `unregister()` frees direction slot |
| TRA-F5-004 | TRA-F4-006 minimal ModuleInterface rejected by register() | **verified-holding** — `tra/modules/registry.py:84-98` validates `get_style_profile()` return shape; raises `TypeError` if `None` returned |
| TRA-F5-005 | TRA-F4-007 `_select_module` matches by FULL direction | **verified-holding** — `tra/kernel.py:196-224` 2-pass scan: Pass 1 exact full-direction match, Pass 2 source-only fallback |
| TRA-F5-006 | TRA-099 CLI translate auto-builds default registry + passes `registry=` | **verified-holding** (TRA-F6-002) — `tra_cli.py:175-183` calls `build_default_registry()` and passes `registry=registry` to `TRAKernel`; end-to-end CLI runner test confirms stub FR module's glossary drives output |
| TRA-F5-007 | TRA-100 TRA-MODULE-AUTHORING.md substantive and actionable | **verified-holding** (TRA-F6-008) — 349 lines, 6 sections, §1 snippet matches `base.py`, §3.2 skeleton wires all 7 methods + `metadata.direction` |
| TRA-F5-009 | build_default_registry() returns ZH-EN module via as_interface() | **verified-holding** (TRA-F6-006) — exactly 1 module `zh_en` with direction `ZH -> EN` and 11-entry glossary |
| TRA-F5-010 | `_normalize_language_pair` silently upper-cases malformed `--lang` | **fixed-and-verified** (TRA-F6-003) — `tra_cli.py:64-96` raises `ValueError` for malformed values with actionable message |
| TRA-F5-011 | `register()` silently accepts `kind="language"` module with no `metadata.direction` | **fixed-and-verified** (TRA-F6-004) — `tra/modules/registry.py:110-119` raises `ValueError` mentioning direction and silent-unreachability failure mode |
| TRA-F5-012 | Dict-returning `get_style_profile()` accepted but undocumented | **fixed-and-verified** — `TRA-MODULE-AUTHORING.md:96-101` documents the dict-coercion alternative |
| TRA-F5-013 | Authoring guide's Protocol snippet omits `name`/`kind` and uses simplified return types | **fixed-and-verified** (with residual cosmetic drift in §2.7, see TRA-F6-009) — §1 snippet now matches `base.py` exactly; §2.7 header still uses `source` instead of `text` |

## Round 6 new findings

| ID | Title | Severity | Category |
|---|---|---|---|
| TRA-F6-009 | `TRA-MODULE-AUTHORING.md` §2.7 header uses parameter name `source` while §1 snippet + `base.py` use `text` | INFO | Documentation |

(Plus 8 positive verifications: TRA-F6-001 through TRA-F6-008, all INFO.)

## Verification commands run (reproducibility)

```bash
cd /home/z/my-project/Translation-Runtime-Architecture/tra-prototype

# HEAD verification
git rev-parse HEAD
# → c4ecd4155d1baa0b4b5d6e60d2e9b1da217e8a46

# F-scope regression tests (TRA-096/097/098/099 + F4-006/007 + F5-010/011/012/013)
python -m pytest tests/test_outstanding_findings.py -k \
  "TRA096 or TRA097 or TRA098 or TRA099 or TRA_F4_006 or TRA_F4_007 or TRA_F5_010 or TRA_F5_011 or TRA_F5_012 or TRA_F5_013" -v
# → 20 passed in 0.61s

# Module/protocol/kernel tests
python -m pytest tests/test_modules.py tests/test_tra043_protocol.py tests/test_kernel.py -v
# → 27 passed in 0.27s

# Full suite (informational; one unrelated failure is Track A6's TRA-A6-001 cache-hit/EXCEPTION_HANDLER WARNING)
python -m pytest tests/
# → 308 passed, 1 failed in 2.98s
#   (failure: TestTRA_A5_003_ExceptionsRoutedThroughKernelRecover::test_unknown_term_emits_exception_handler_audit_record
#    — out of F6 scope; tracked by Track A6 as TRA-A6-001 and Track E6 as TRA-E6-003)

# Probe 1: TRA-096 E2E (as_interface + register + TRAKernel(registry=))
python -c "
from tra.modules.registry import ModuleRegistry
from tra.modules.zh_en import ZHENModule
from tra.modules.base import LanguageModuleProtocol
iface = ZHENModule().as_interface()
print('isinstance(iface, LanguageModuleProtocol):', isinstance(iface, LanguageModuleProtocol))
reg = ModuleRegistry(); reg.register(iface)
print('modules:', [m.name for m in reg.all()])
print('direction:', iface.metadata.get('direction'))
"
# → isinstance: True; modules: ['zh_en']; direction: ZH -> EN

# Probe 2: TRA-099 CLI source inspection
python -c "
import re, pathlib
src = pathlib.Path('tra_cli.py').read_text(encoding='utf-8')
print('build_default_registry in source:', 'build_default_registry' in src)
print('TRAKernel(...registry=...) regex match:', bool(re.search(r'TRAKernel\([^)]*registry\s*=', src, re.DOTALL)))
"
# → True / True

# Probe 3: TRA-F5-010 _normalize_language_pair rejects malformed
python -c "
from tra_cli import _normalize_language_pair
for v in ['fr', '', 'fr_de', 'zh en', 'xxx']:
    try: _normalize_language_pair(v); print(f'{v!r}: NO RAISE (BUG)')
    except (ValueError, Exception) as e: print(f'{v!r}: raises {type(e).__name__}')
print('zh-en ->', _normalize_language_pair('zh-en'))
print('ZH -> EN ->', _normalize_language_pair('ZH -> EN'))
"
# → 5 malformed values raise ValueError; 2 valid forms normalize correctly

# Probe 4: TRA-F5-011 register() rejects no-direction language module
python -c "
from tra.modules.registry import ModuleInterface, ModuleRegistry, build_default_registry
from tra.modules.zh_en import ZHENModule
zhen = ZHENModule()
stub = ModuleInterface(name='stub-no-direction', kind='language',
    get_glossary_mappings=zhen.get_glossary_mappings,
    get_style_profile=zhen.get_style_profile,
    apply_rules=zhen.apply_rules, is_forbidden=zhen.is_forbidden,
    get_forbidden_targets=zhen.get_forbidden_targets,
    entity_type_hint=zhen.entity_type_hint,
    apply_zh_rules=zhen.apply_zh_rules, metadata={})
reg = ModuleRegistry()
try: reg.register(stub); print('NO RAISE (BUG)')
except ValueError as e: print('raises ValueError:', str(e)[:80])
"
# → raises ValueError: Language module 'stub-no-direction' has no metadata.direction…

# Probe 5: ModuleInterface contract — 7 Callable fields match Protocol
python -c "
import dataclasses
from tra.modules.registry import ModuleInterface
from tra.modules.base import LanguageModuleProtocol
fields = dataclasses.fields(ModuleInterface)
callable_fields = [f for f in fields if f.name not in ('name', 'kind', 'metadata')]
print('total fields:', len(fields), 'callable:', len(callable_fields))
print('methods:', sorted(f.name for f in callable_fields))
print('Protocol methods:', sorted(m for m in dir(LanguageModuleProtocol) if not m.startswith('_')))
"
# → total fields: 10, callable: 7; methods list == Protocol methods list

# Probe 6: build_default_registry() returns ZH-EN module
python -c "
from tra.modules.registry import build_default_registry
reg = build_default_registry()
print('modules:', [m.name for m in reg.all()])
print('direction:', reg.get('zh_en').metadata.get('direction'))
print('glossary 成 立 ->', reg.get('zh_en').get_glossary_mappings().get('成立'))
"
# → modules: ['zh_en']; direction: ZH -> EN; glossary: Confirmed

# Probe 7: Edge cases — empty / duplicate / same-direction / unregister+re-register
python -c "
from tra.modules.registry import ModuleInterface, ModuleRegistry
from tra.memory import StyleProfile
sp = lambda: StyleProfile(voice='t', sentence_complexity='m')
empty = ModuleRegistry()
print('empty.all():', len(empty.all()))
try: empty.get('zh_en')
except KeyError as e: print('empty.get raises KeyError:', e)
# duplicate name
reg = ModuleRegistry()
reg.register(ModuleInterface(name='zh_en', kind='language', metadata={'direction': 'ZH -> EN'}, get_style_profile=sp))
try: reg.register(ModuleInterface(name='zh_en', kind='language', metadata={'direction': 'EN -> ZH'}, get_style_profile=sp))
except ValueError as e: print('duplicate name raises:', str(e)[:60])
# same direction
reg2 = ModuleRegistry()
reg2.register(ModuleInterface(name='zh_en_v1', kind='language', metadata={'direction': 'ZH -> EN'}, get_style_profile=sp))
try: reg2.register(ModuleInterface(name='zh_en_v2', kind='language', metadata={'direction': 'ZH -> EN'}, get_style_profile=sp))
except ValueError as e: print('same direction raises:', str(e)[:60])
# unregister + re-register
reg3 = ModuleRegistry()
reg3.register(ModuleInterface(name='zh_en_v1', kind='language', metadata={'direction': 'ZH -> EN'}, get_style_profile=sp))
reg3.unregister('zh_en_v1')
reg3.register(ModuleInterface(name='zh_en_v2', kind='language', metadata={'direction': 'ZH -> EN'}, get_style_profile=sp))
print('after unregister+re-register:', [m.name for m in reg3.all()])
"
# → empty.all(): 0 / KeyError
# → duplicate name raises: Module 'zh_en' is already registered…
# → same direction raises: Direction conflict: module 'zh_en_v2'…
# → after unregister+re-register: ['zh_en_v2']

# Probe 8: TRA-MODULE-AUTHORING.md quality
python -c "
import pathlib
guide = pathlib.Path('/home/z/my-project/Translation-Runtime-Architecture/TRA-MODULE-AUTHORING.md').read_text(encoding='utf-8')
print('lines:', len(guide.splitlines()))
print('snippet has name/kind:', 'name: str' in guide and 'kind: str' in guide)
print('snippet has 7 methods:', all(m in guide for m in ['get_glossary_mappings','get_style_profile','is_forbidden','get_forbidden_targets','entity_type_hint','apply_zh_rules','apply_rules']))
print('has as_interface skeleton:', 'def as_interface(self)' in guide)
print('references TRA-F4-006/007/099:', all(x in guide for x in ['TRA-F4-006','TRA-F4-007','TRA-099']))
"
# → lines: 349; snippet has name/kind: True; 7 methods: True; as_interface skeleton: True; cross-refs: True

# Probe 9: §2.7 residual drift (TRA-F6-009)
python -c "
import pathlib, re
guide = pathlib.Path('/home/z/my-project/Translation-Runtime-Architecture/TRA-MODULE-AUTHORING.md').read_text(encoding='utf-8')
m = re.search(r'### 2\.7 \`apply_zh_rules\((.+?)\) -> str\`', guide)
print('§2.7 header parameter name:', m.group(1) if m else '(not found)')
# base.py
base = pathlib.Path('tra/modules/base.py').read_text(encoding='utf-8')
m2 = re.search(r'def apply_zh_rules\(self, (\w+):', base)
print('base.py apply_zh_rules parameter name:', m2.group(1) if m2 else '(not found)')
"
# → §2.7 header parameter name: source: str
# → base.py apply_zh_rules parameter name: text
```

## Conclusion

HEAD `c4ecd41` resolves **all R5 Track F5 stub-module findings** and re-confirms them at the R6 baseline. The spec's sanctioned module extension path — `as_interface()` → `register()` → `TRAKernel(registry=)` — works end-to-end via both the Python API (TRA-096) and the CLI (TRA-099, with `_normalize_language_pair` rejecting malformed `--lang` values per TRA-F5-010). The `ModuleInterface` dataclass carries exactly 7 `Callable` fields matching the 7 method signatures of `LanguageModuleProtocol` (TRA-096/043 contract). `build_default_registry()` returns a registry containing exactly the bundled ZH-EN module registered via `as_interface()` with `metadata.direction = 'ZH -> EN'`. Edge cases (empty registry, duplicate names, same-direction conflicts, unregister + re-register) are all handled with actionable error messages (TRA-098 + TRA-F5-011). `TRA-MODULE-AUTHORING.md` is substantive (349 lines, 6 sections) and actionable (§1 snippet matches `base.py`; §3.2 skeleton wires all 7 methods + `metadata.direction`).

The **1 new finding** is purely cosmetic: TRA-F6-009 (INFO) — the §2.7 section header in `TRA-MODULE-AUTHORING.md` still uses the parameter name `source` while the §1 Protocol snippet and `base.py` both use `text`. This is a residual of TRA-F5-013's partial R5 fix (which updated §1 but not §2.7) and has no functional impact (parameter names are not enforced by `@runtime_checkable` Protocols; the §3.2 skeleton correctly uses `text`). A 2-line doc fix closes it.

**No regressions** detected in F-scope. The single full-suite test failure (`TestTRA_A5_003::test_unknown_term_emits_exception_handler_audit_record`) is out of F6 scope: it is the cache-hit/EXCEPTION_HANDLER suppression WARNING tracked by Track A6 as TRA-A6-001 and surfaced by Track E6 as TRA-E6-003 — unrelated to stub-module construction, registry wiring, or module-authoring guide quality.

All 4 quality gates green at HEAD `c4ecd41` for F-scope code paths: 20 F-targeted regression tests + 27 module/protocol/kernel tests PASS; mypy --strict + ruff clean (per Track R6 baseline).
