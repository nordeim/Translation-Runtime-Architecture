# Track B — Code Quality & Security Re-Audit Findings

**Auditor:** Track B2 agent
**HEAD audited:** 4b8827c
**Scope:** code quality, type safety, error handling, security, cache correctness, dependency hygiene, reproducibility of `tra-prototype/`

## Quality gate results

| Gate | Result | Notes |
|---|---|---|
| ruff check | PASS | `All checks passed!` |
| ruff format --check | PASS | `35 files already formatted` |
| mypy --strict tra | PASS | `Success: no issues found in 20 source files` |
| pytest tests | PASS | `141 passed in 0.63s` |
| ruff check --select F | PASS | `All checks passed!` (no unused imports) |

All 4 production quality gates remain green. Test count grew from 103 (Round 1) to 141 (+38 new regression tests covering TRA-001, TRA-002, TRA-004, TRA-007, TRA-008, TRA-009, TRA-012, TRA-013, TRA-014, TRA-028, TRA-029, TRA-032, TRA-033).

## Reproducibility probe

Two runs of `python -m tra_cli translate examples/security_advisory_zh.md --level L4` with fresh `audit_trace.jsonl` + `compilation_artifacts/` + `cache/` between runs:

| Artifact | Run-1 SHA-256 | Run-2 SHA-256 | Byte-identical? |
|---|---|---|---|
| `audit_trace.jsonl` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | YES |
| `evidence_trace.jsonl` (L4) | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | YES |
| Output `.md` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | YES |

**TRA-013 fully remediated.** Round 1 B-18 reported non-reproducible audit trail (`uuid4()` evidence IDs + `datetime.now(UTC)` timestamps). Both root causes are now fixed:
- `EvidenceRegistry.add()` (diagnostics.py:121-133) assigns content-addressed IDs via `_content_addressed_id(record)` (diagnostics.py:45-63): `ev_{sha256(canonical_record)[:12]}`. Two records with identical content produce the same ID.
- `AuditTrail` (diagnostics.py:157-167) accepts an injectable `clock` callable. `TRAKernel.__init__` (kernel.py:118-121) wires `self._deterministic_clock` when `deterministic=True` (default). The clock (kernel.py:157-171) derives a stable timestamp from the source-hash seed (epoch + `int(seed[:8], 16) % (365*24*3600)` seconds).
- Regression tests `TestTRA013AuditReproducibility` (test_outstanding_findings.py:155-216) assert byte-identity for both `audit_trace.jsonl` and `evidence_trace.jsonl` via `filecmp.cmp`.

## Dependency hygiene

| Dep | Listed? | Imported? | Verdict |
|---|---|---|---|
| `pydantic>=2.8` | runtime | YES — every model in `tra/memory.py`, `cache.py`, `diagnostics.py`, `config.py`, `benchmark.py` | KEEP |
| `pydantic-settings>=2.3` | runtime | **NO** — zero `import pydantic_settings` / `from pydantic_settings` across repo | DROP (TRA-B2-006) |
| `markdown-it-py>=3.0` | runtime | YES — `tra/anchor.py:25,26` | KEEP |
| `mdit-py-plugins>=0.4` | runtime | **NO** — zero imports; codebase uses only `MarkdownIt().enable("table")` (built-in) | DROP (TRA-B2-006) |
| `diskcache>=5.6` | runtime | YES — `tra/cache.py:87` (inside `__init__`) | KEEP |
| `pyyaml>=6.0` | runtime | YES — `tra/kernel.py:20`, `tra/config.py:8` | KEEP |
| `structlog>=24.1` | runtime | **NO** — zero imports across repo | DROP (TRA-B2-006) |
| `click>=8.1` | runtime | YES — `tra_cli.py:16` | KEEP |
| `rich>=13.7` | runtime | YES — `tra/hitl.py:15,16`; `tra_cli.py:17,18` | KEEP |
| `litellm>=1.49` | runtime | **NO** — zero imports; LLM seam is `Callable[[str, RuntimeContext], str] \| None` (`isa.py:322`) | MOVE to optional extra `[llm]` (TRA-B2-006) |
| `pytest>=8.2` (dev) | dev | YES — test runner | KEEP |
| `pytest-asyncio>=0.23` (dev) | dev | **NO** — zero `async def` tests; `asyncio_mode = "auto"` set in `pyproject.toml` but unused | DROP (TRA-B2-007) |
| `ruff>=0.5` (dev) | dev | YES — quality gate | KEEP |
| `black>=24.4` (dev) | dev | **NO** — project uses `ruff format`; `[tool.black]` config in `pyproject.toml` is unused | DROP (TRA-B2-007) |
| `mypy>=1.10` (dev) | dev | YES — quality gate | KEEP |

**litellm transitive footprint** (verified via `pip show`): 12 direct deps — `aiohttp, click, fastuuid, httpx, importlib-metadata, jinja2, jsonschema, openai, pydantic, python-dotenv, tiktoken, tokenizers` — and ~30 transitive packages installed in the sandbox (`aiohappyeyeballs, aiosignal, attrs, certifi, charset_normalizer, distro, filelock, frozenlist, fsspec, h11, hf_xet, httpcore, huggingface_hub, idna, jiter, markupsafe, multidict, pluggy, propcache, pygments, referencing, regex, requests, rpds, sniffio, tqdm, typing_extensions, typing_inspection, urllib3, yarl, zipp`). ~50+ packages and hundreds of MB of install footprint pulled in for a rule-based prototype that never imports `litellm`.

## Summary

- Total findings: **13**
- BLOCKING: **0**
- WARNING: **5** (TRA-B2-002, -005, -006, -007, -012)
- INFO: **8** (TRA-B2-001, -003, -004, -008, -009, -010, -011, -013)

**Carry-over status vs Round 1 Track B:**
- **8 fully remediated:** B-2/B-16 (Pydantic frozen), B-4 (bare `assert`), B-7 (double audit record), B-12 (validate/benchmark sanitization bypass), B-14 (cache-clear `--pattern` silent no-op), B-15 (path traversal), B-18 (audit trail reproducibility), and B-10's `count_blocking` stub (TRA-016).
- **5 persistent:** B-10 dead code (CONCLUSION_LEADING, ModuleBase, `_HALF_TO_FULL`), B-11/B-17 unused deps, B-13 `_hash_sorted` naming.
- **1 new:** silent severity downgrade for `Unrecoverable` in `route_exception` fallback (TRA-B2-005).

## Findings

### TRA-B2-001 — `RuntimeContext.module: Any` is a documented duck-type but a real type-safety hole
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (special-attention item from B-1)
- **Evidence:** `tra/memory.py:201-207`; `tra/isa.py:161-165`
- **Detail:**
  `RuntimeContext.module: Any = Field(default=None, exclude=True)` (memory.py:207) is the active language module. The inline comment (memory.py:204-206) justifies the duck-type ("the module contract is structural"). However, `isa.py:161-165` `_module(ctx) -> Any` then propagates this `Any` to every caller: `mappings = mod.get_glossary_mappings()` (isa.py:181), `mod.is_forbidden(...)` (isa.py:186), `mod.apply_zh_rules(out)` (isa.py:429), `_module(ctx).entity_type_hint(...)` (isa.py:277). A typo like `mod.get_glossary_mapings()` (sic) would NOT be caught by `mypy --strict` because `mod` is `Any`.
  The codebase already has a `ModuleInterface` dataclass (`tra/modules/registry.py:13-22`) and a `ModuleBase` ABC (`tra/modules/base.py:8-28`), but `ZHENModule` inherits from neither — it's a plain class. A `Protocol` (`typing.Protocol`) would let the kernel/ISA layer type-check method names without forcing inheritance.
- **Suggested fix:** Define a `LanguageModule` Protocol in `tra/modules/base.py` listing the 7 methods the ISA layer calls (`get_glossary_mappings`, `get_style_profile`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`, `apply_rules`). Type `RuntimeContext.module: LanguageModule | None = Field(default=None, exclude=True)`. Update `_module(ctx) -> LanguageModule` in `isa.py:161`.

### TRA-B2-002 — `TRAKernel.__init__(registry: object | None = None)` requires `# type: ignore[attr-defined]`
- **Severity:** WARNING
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (special-attention item)
- **Evidence:** `tra/kernel.py:91`; `tra/kernel.py:130`; `tra/kernel.py:143`
- **Detail:**
  `TRAKernel.__init__` accepts `registry: object | None = None` (kernel.py:91). The static method `_select_module(language_pair, registry: object | None)` (kernel.py:130) then calls `registry.all()` (kernel.py:143) with a `# type: ignore[attr-defined]` comment, because `object` has no `.all()` method.
  A concrete `ModuleRegistry` class exists in `tra/modules/registry.py:25-40` with a properly typed `.all() -> list[ModuleInterface]` method. Using `object | None` defeats mypy's ability to catch:
  - Typos in method names (`.all()` → `.items()` would compile silently).
  - Wrong-registry-type calls (any object with an `.all()` attribute would be accepted).
  The test `TestTRA002RegistryWiring` (test_outstanding_findings.py:466-583) passes a `ModuleRegistry` that holds a `StubModule` (not a `ModuleInterface`) — this is why the parameter is currently `object | None` (to accept the test's duck-typed registry). The test itself carries `# type: ignore[arg-type]` at line 568 to register the stub.
- **Suggested fix:** Type the parameter as `ModuleRegistry | None`. Update `TestTRA002RegistryWiring` to register the stub via `StubModule().as_interface()` (the existing adapter at `zh_en.py:226-235`) so the registry holds a proper `ModuleInterface`. Then both `# type: ignore` comments (kernel.py:143 and test_outstanding_findings.py:568) can be removed.

### TRA-B2-003 — `_collect_headings(nodes: list[Any])` should be `list[StructuralNode]`
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** New
- **Evidence:** `tra/kernel.py:310-314`
- **Detail:**
  The nested helper `_collect_headings` inside `_rewrite_anchors` types its parameter as `list[Any]`:
  ```python
  def _collect_headings(nodes: list[Any]) -> None:
      for node in nodes:
          if node.kind.value == "heading" and node.text:
              source_headings.append(node.text)
          _collect_headings(node.children)
  ```
  The actual element type is `StructuralNode` (memory.py:101-112), which has `.kind: NodeKind`, `.text: str | None`, `.children: list[StructuralNode]`. Using `list[Any]` means mypy cannot verify attribute access (e.g., `node.kind.value` vs `node.kinds.value`). `StructuralNode` is not imported in `kernel.py` (only `StructuralMap` is, at kernel.py:43), which is why the helper resorted to `Any`.
- **Suggested fix:** Add `StructuralNode` to the import from `.memory` at kernel.py:38-44, then change the helper signature to `def _collect_headings(nodes: list[StructuralNode]) -> None:`.

### TRA-B2-004 — Stale `# type: ignore[arg-type]` at `tests/test_recovery.py:95`
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (Round 1 B-1)
- **Evidence:** `tests/test_recovery.py:95`
- **Detail:**
  ```python
  def test_route_exception_falls_back_for_unknown():
      amb: list[str] = []
      rep = route_exception(BrokenMarkdown(), amb)  # type: ignore[arg-type]
      assert isinstance(rep, RecoveryReport)
  ```
  The comment is stale. `BrokenMarkdown()` (exceptions.py:35-40) accepts `message: str = ""` and `*, detail: str = ""` — both optional. The call is type-correct. `mypy --strict tests/test_recovery.py` reports `tests/test_recovery.py:95: error: Unused "type: ignore" comment [unused-ignore]`. The production gate `mypy --strict tra` doesn't check tests/, so this doesn't fail the gate, but it's a stale comment that should be cleaned up.
  Note: the same `mypy --strict tests/` run reports 118 other errors (mostly `no-untyped-def` for test functions missing `-> None`), so the test suite is NOT mypy-strict clean overall — only `tra/` is.
- **Suggested fix:** Remove `# type: ignore[arg-type]` from test_recovery.py:95. (Separately, consider adding `tests/` to the `mypy --strict` gate by annotating all test functions with `-> None`.)

### TRA-B2-005 — `route_exception` fallback silently downgrades `Unrecoverable` to WARNING + PRESERVE_SOURCE
- **Severity:** WARNING
- **Category:** Code Quality / Error Handling
- **Carry-over or new:** New (special-attention item)
- **Evidence:** `tra/recovery.py:176-182`; `tra/kernel.py:429`; `tra/exceptions.py:75-78`
- **Detail:**
  `route_exception` (recovery.py:154-182) dispatches 5 known TRAException subclasses (`UnknownTerm`, `BrokenMarkdown`, `CertaintyConflict`, `EntityAmbiguity`, `GlossaryConflict`) and falls through to a default for any other `TRAException` subclass:
  ```python
  return _emit(
      ctx_ambiguities,
      exc.code,
      Severity.WARNING,            # <-- always WARNING
      RecoveryAction.PRESERVE_SOURCE,  # <-- always PRESERVE_SOURCE
      str(exc),
  )
  ```
  Two TRAException subclasses can reach this fallback in production:
  1. `Unrecoverable` (exceptions.py:75-78) — `kernel.py:429` explicitly calls `self._recover(Unrecoverable(f"UNRECOVERABLE: {current.issue}"))` from the repair loop's `except Unrecoverable:` branch (kernel.py:424).
  2. `ConformanceFailure` (exceptions.py:81-99) — would reach `_recover` if any `except TRAException` block in `kernel.py` (lines 207, 228) caught it, though in practice ConformanceFailure is raised only at kernel.py:256 (after the try blocks).

  **Empirically verified:** routing `Unrecoverable("UNRECOVERABLE: structural repair needs manual intervention")` through `route_exception` returns:
  - `code='UNRECOVERABLE'`
  - `severity=<Severity.WARNING: 'WARNING'>` — spec §6 implies UNRECOVERABLE should be BLOCKING (it's the case where REPAIR_SEGMENT cannot resolve without violating a higher policy).
  - `action=<RecoveryAction.PRESERVE_SOURCE: 'PRESERVE_SOURCE'>` — spec §6 implies UNRECOVERABLE should be HALT (handoff to human).

  The kernel's `_recover` (kernel.py:335-355) then writes the audit record with `flags_raised=[report.severity.value]` = `["WARNING"]`. **Verified end-to-end with a mocked repair_segment that raises Unrecoverable**: the audit trail's EXCEPTION_HANDLER record has `severity='WARNING', action='PRESERVE_SOURCE', flags=['WARNING']` instead of the spec-correct `severity='BLOCKING', action='HALT'`.

  **Consequence:** `reporting.summarize_audit` (reporting.py:21-47) counts BLOCKING from `flags_raised`. An audit trail containing only an Unrecoverable EXCEPTION_HANDLER record would report `blocking_flags=0, l3_conformant=True` — **incorrectly indicating L3 conformance for a run that hit an unrecoverable failure.** The L3 in-band gate (kernel.py:252-261) re-runs `verify_output` which would still catch any actual BLOCKING diagnostics, so this is not a gate-bypass — but for L4 forensic audits where the audit trail IS the evidence, this misrepresents severity.

  Existing test `test_route_exception_falls_back_for_unknown` (test_recovery.py:93-96) only asserts the return type is `RecoveryReport` — it does NOT assert the severity/action for `Unrecoverable`.
- **Suggested fix:** Add an explicit branch for `Unrecoverable` in `route_exception`:
  ```python
  if isinstance(exc, Unrecoverable):
      return _emit(
          ctx_ambiguities,
          exc.code,
          Severity.BLOCKING,
          RecoveryAction.HALT,
          f"Unrecoverable: {exc.message}; manual intervention required.",
          add_to_ambiguities=True,
      )
  ```
  Add a regression test asserting `route_exception(Unrecoverable("x"), []).severity == Severity.BLOCKING` and `action == RecoveryAction.HALT`.

### TRA-B2-006 — 4 unused runtime deps still listed (TRA-017 carry-over)
- **Severity:** WARNING
- **Category:** Code Quality / Dependency Hygiene
- **Carry-over or new:** Carry-over (Round 1 B-11 / B-17)
- **Evidence:** `pyproject.toml:10-21`; `requirements.txt:1-11`
- **Detail:**
  `pyproject.toml` lists 4 runtime deps that have ZERO imports across the entire repo (verified via `Grep` for `import structlog|from structlog|import litellm|from litellm|pydantic_settings|from pydantic_settings|mdit_py_plugins|from mdit_py_plugins` → no matches):
  - `pydantic-settings>=2.3` (pyproject.toml:12) — pulls `python-dotenv`, `typing-inspection`.
  - `mdit-py-plugins>=0.4` (pyproject.toml:14) — the codebase uses only `MarkdownIt().enable("table")` which is built-in.
  - `structlog>=24.1` (pyproject.toml:17) — Phase 6.3.1 logging never wired.
  - `litellm>=1.49` (pyproject.toml:20) — LLM seam is `Callable[[str, RuntimeContext], str] | None` (isa.py:322); caller-supplied. Pulls 12 direct deps + ~30 transitive (`openai, tiktoken, tokenizers, huggingface-hub, aiohttp, httpx, jinja2, jsonschema, ...`).

  `litellm` 1.92.0's `Requires` list (from `pip show litellm`) has 82 entries (12 unconditional + 70 under `[proxy]` extra). Even ignoring extras, the 12 unconditional deps cascade to ~50+ packages total in the sandbox. For a rule-based prototype that never imports `litellm`, this is significant install-footprint bloat.

  The CLAUDE.md / SKILL.md / README.md DO acknowledge these as known unused deps, but they remain in `pyproject.toml` and `requirements.txt`.
- **Suggested fix:**
  1. Move `litellm` to `[project.optional-dependencies] llm = ["litellm>=1.49"]` so callers who wire a litellm-based `llm_translate` install it via `pip install -e ".[llm]"`.
  2. Drop `pydantic-settings`, `mdit-py-plugins`, `structlog` from runtime deps entirely (or wire them if Phase 6.3.1 logging lands).
  3. Update `requirements.txt` to match.

### TRA-B2-007 — 2 unused dev deps still listed (TRA-017 carry-over)
- **Severity:** WARNING
- **Category:** Code Quality / Dependency Hygiene
- **Carry-over or new:** Carry-over (Round 1 B-17)
- **Evidence:** `pyproject.toml:24-30`; `requirements.txt:14-18`
- **Detail:**
  `[project.optional-dependencies] dev` lists:
  - `pytest-asyncio>=0.23` (pyproject.toml:26) — `asyncio_mode = "auto"` was previously set in `pyproject.toml` but is NOT present in the current `[tool.pytest.ini_options]` (pyproject.toml:59-61). `Grep` for `async def|await|asyncio` over `tra/` and `tests/` returns ZERO functional hits (only a docstring noun at `hitl.py:8`). The plugin is loaded by pytest (`plugins: asyncio-1.4.0` in test output) but never used.
  - `black>=24.4` (pyproject.toml:28) — the actual formatter is `ruff format` (verified: `ruff format --check .` passes on 35 files; no `[tool.black]` config is exercised in practice even though it's defined at pyproject.toml:44-46). `Grep` for `^import black|^from black` returns no matches.

  Both contribute to install-time cost and pull transitive deps (`black` pulls `blib2to3`, `pytokens`, `pathspec`, `platformdirs`; `pytest-asyncio` pulls nothing extra but is dead weight).
- **Suggested fix:** Drop `black` and `pytest-asyncio` from `[project.optional-dependencies] dev`. If asyncio segment-level parallelism lands per Phase 6.5.1, re-add `pytest-asyncio` at that time. Remove the unused `[tool.black]` config block from `pyproject.toml:44-46`.

### TRA-B2-008 — Dead code: `CONCLUSION_LEADING` defined but never consumed
- **Severity:** INFO
- **Category:** Code Quality / Dead Code
- **Carry-over or new:** Carry-over (Round 1 B-10)
- **Evidence:** `tra/modules/zh_en.py:72-75`
- **Detail:**
  ```python
  # Information-order: conclusion-leading markers (ZH). When a clause opens with
  # evidence and closes on one of these, the conclusion is surfaced first so the
  # target reads evidence -> conclusion (verification-report readability).
  CONCLUSION_LEADING: tuple[str, ...] = ("因此", "所以", "故", "由此可见", "综上")
  ```
  The docstring claims it surfaces conclusions first, but `Grep` for `CONCLUSION_LEADING` across the entire repo returns only this definition site — zero call sites. The information-order rule was never implemented.
- **Suggested fix:** Either delete the constant (and its docstring) or wire it into `apply_zh_rules` (e.g., detect a clause ending with a CONCLUSION_LEADING marker and reorder so the conclusion leads). If deferred, mark with `# TODO: Phase 7 — information-order rule not yet wired`.

### TRA-B2-009 — Dead code: `ModuleBase` ABC defined but never subclassed
- **Severity:** INFO
- **Category:** Code Quality / Dead Code
- **Carry-over or new:** Carry-over (Round 1 B-10)
- **Evidence:** `tra/modules/base.py:8-28`
- **Detail:**
  `ModuleBase(ABC)` declares abstract methods `get_glossary_mappings`, `get_style_profile`, and a default `apply_rules`. `Grep` for `ModuleBase|modules.base` returns only the definition — zero subclasses. `ZHENModule` (zh_en.py:129) inherits from `object`, not `ModuleBase`. The ABC is never instantiated, never subclassed, and provides no enforcement of the module contract.
  The actual module contract is enforced structurally (via duck-typing — see TRA-B2-001) or via the `ModuleInterface` dataclass in `registry.py:13-22`.
- **Suggested fix:** Either delete `ModuleBase` (the `ModuleInterface` dataclass + a `Protocol` per TRA-B2-001 cover the contract) or make `ZHENModule` inherit from it and add the missing abstract methods (`get_forbidden_targets`, `is_forbidden`, `entity_type_hint`, `apply_zh_rules`).

### TRA-B2-010 — Dead code (production): `_HALF_TO_FULL` table only reachable via EN→ZH
- **Severity:** INFO
- **Category:** Code Quality / Dead Code
- **Carry-over or new:** Carry-over (Round 1 B-10)
- **Evidence:** `tra/modules/zh_en.py:110-119`; `tra/modules/zh_en.py:185-200`
- **Detail:**
  `_HALF_TO_FULL` (zh_en.py:110-119) is a full-width CJK punctuation map reachable only via `apply_en_rules` (zh_en.py:185-200, called via `apply_rules(direction="EN -> ZH")` at zh_en.py:222-223). The kernel's production path is ZH→EN: `_rule_translate` (isa.py:429) calls `mod.apply_zh_rules(out)` which uses `_FULL_TO_HALF` (the inverse table). So `_HALF_TO_FULL` and `apply_en_rules` are test-alive (test_modules.py:126,131,136,145) but production-dead.
  `PASSIVE_REDUCTION` (zh_en.py:86-93) and `FOUR_CHAR_MAP` (zh_en.py:78-82) are similarly EN→ZH-only.
  This is acceptable for a bidirectional module library, but the prototype only exercises ZH→EN — so 3 tables and 1 method are dead weight in the production path.
- **Suggested fix:** Either (a) accept as future-ready for EN→ZH support and mark with a comment, or (b) split `zh_en.py` into `zh_to_en.py` (production) and `en_to_zh.py` (deferred) so the production install footprint shrinks.

### TRA-B2-011 — Misleading function name: `_hash_sorted` does not sort lists
- **Severity:** INFO
- **Category:** Code Quality / Naming
- **Carry-over or new:** Carry-over (Round 1 B-13)
- **Evidence:** `tra/cache.py:33-34`
- **Detail:**
  ```python
  def _hash_sorted(obj: Any) -> str:
      return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()
  ```
  The name `_hash_sorted` implies the input is sorted before hashing. In reality, `_canonical_json` (cache.py:28-30) uses `json.dumps(payload, sort_keys=True, ...)` which sorts DICT keys but preserves LIST order. So `_hash_sorted([3, 1, 2])` produces a different hash than `_hash_sorted([1, 2, 3])` — verified empirically.

  This is INTENTIONAL for `policy_stack_hash` (cache.py:65), where the spec (§5.1) mandates that policy-stack ordering is non-negotiable. But the name is misleading: a future maintainer might "fix" the name by adding `sorted(obj)` and break the policy-stack ordering invariant.

  Note: `_hash_set` (cache.py:37-44) DOES sort list elements (per-item hashes are sorted before re-hashing) — that's the order-independent variant for glossary/entities.
- **Suggested fix:** Rename `_hash_sorted` → `_hash_canonical` (it produces a canonical-JSON hash, not a sorted-list hash). Add a docstring: "SHA-256 over canonical JSON (dict keys sorted, list order preserved). Use for ordered collections like policy_stack; use `_hash_set` for unordered collections."

### TRA-B2-012 — `BootstrapConfig.from_yaml` ignores `base_dir`; no `extra="forbid"`
- **Severity:** WARNING
- **Category:** Code Quality / Config Validation
- **Carry-over or new:** New
- **Evidence:** `tra/config.py:81-99`; `tra/config.py:23-37`
- **Detail:**
  `BootstrapConfig` has a `base_dir: str = "."` field (config.py:53) used by the path-safety validator (config.py:55-79). However, `from_yaml` (config.py:81-99) does NOT read `base_dir` from the YAML — it always defaults to `.`. Verified empirically: a YAML config with `base_dir: /tmp/override` produces `cfg.base_dir == "."`.

  This means a user who sets `base_dir` in `config.yaml` to scope path traversal protection to a specific project root would silently have it ignored. They'd have to construct `BootstrapConfig` directly or use `model_copy(update={"base_dir": ...})` after `from_yaml`.

  Separately, `BootstrapConfig` has no `extra="forbid"` in its `ConfigDict(frozen=True)` (config.py:39). This means unknown YAML fields are silently dropped — including `base_dir` if a user puts it at the top level. A typo like `conformence_level:` (sic) would be silently ignored, falling back to the required-field default and raising a confusing "missing conformance_level" error rather than "unknown field conformence_level".

  Note: the path traversal validator (TRA-014) is otherwise correct — verified empirically that relative `..`, absolute paths outside `base_dir`, and traversal in `audit_trace`/`cache_directory`/`compilation_dir` are all rejected with a clear `ValidationError`.
- **Suggested fix:**
  1. Add `base_dir = raw.get("base_dir", ".")` to `from_yaml` so users can scope the validator via YAML.
  2. Add `extra="forbid"` to `BootstrapConfig.model_config` to catch YAML typos. Update `from_yaml` to either pass through unknown fields (letting pydantic reject them) or explicitly list the allowed keys.

### TRA-B2-013 — `TranslationCache._cache: Any` is a workaround for diskcache missing stubs
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (Round 1 B-1)
- **Evidence:** `tra/cache.py:85`; `pyproject.toml:55-57`
- **Detail:**
  `TranslationCache.__init__` types `self._cache: Any = None` (cache.py:85), then assigns `self._cache = diskcache.Cache(...)` (cache.py:90) when enabled. The `Any` annotation is forced because `diskcache` has no type stubs and `pyproject.toml:55-57` sets `ignore_missing_imports = true` for the `diskcache` module, making `diskcache.Cache` resolve to `Any`.

  Consequently, all `self._cache.get(key)`, `self._cache.set(...)`, `self._cache.delete(...)`, `self._cache.iterkeys()`, `self._cache.clear()` calls (cache.py:95, 105, 121-127) bypass mypy's type checking. A typo like `self._cache.gete(key)` would not be caught.

  This is a known trade-off for libraries without stubs. The mypy override is appropriate; the `Any` annotation is the standard workaround.
- **Suggested fix:** Define a minimal `Protocol` for the diskcache subset the cache uses (`get`, `set`, `delete`, `iterkeys`, `clear`, `__len__`), or use `TYPE_CHECKING` with `import diskcache` and type `_cache: "diskcache.Cache | None"`. The Protocol approach is preferred because it doesn't require `diskcache` to ship stubs. Pseudocode:
  ```python
  from typing import Protocol, TYPE_CHECKING
  class _CacheLike(Protocol):
      def get(self, key: str) -> Any | None: ...
      def set(self, key: str, value: Any, expire: float | None = None) -> None: ...
      def delete(self, key: str) -> bool: ...
      def iterkeys(self) -> Any: ...
      def clear(self) -> None: ...
      def __len__(self) -> int: ...
  ```
  Then `self._cache: _CacheLike | None = None`.

---

## Appendix: Round 1 Track B findings — remediation status

| Round 1 ID | Title | Round 2 status |
|---|---|---|
| B-1 | mypy --strict clean; 1 stale `# type: ignore` | PARTIAL — `tra/` still clean; stale comment at `tests/test_recovery.py:95` persists (TRA-B2-004) |
| B-2 | Pydantic v2 — no frozen, no constraints | FIXED — `GlossaryEntry`, `ForbiddenMapping`, `Entity`, `BootstrapConfig` all `frozen=True`; `BootstrapConfig` CLI overrides use `model_copy(update=...)` |
| B-3 | `from __future__ import annotations` consistency | FIXED — universal (30 .py files in Round 1, 35 in Round 2) |
| B-4 | `assert` used for runtime validation | FIXED — replaced with hard `raise TRAException(...)` at kernel.py:219-222; `Grep` for `^\s*assert\s` in `tra/` returns 0 hits |
| B-5 | Broad except clauses justified | STILL VALID — 2 `except Exception` (isa.py:94, isa.py:357) with `# noqa: BLE001` comments matching behavior |
| B-6 | raise statements use TRAException subclasses | STILL VALID — no regressions |
| B-7 | LLM seam double record | FIXED — isa.py:393 `return result` after the degraded audit append; verified `test_graceful_degradation_on_llm_failure` passes |
| B-8 | No swallowed exceptions | STILL VALID — zero `except: pass` patterns |
| B-9 | Unused imports — ruff F clean | STILL VALID — `ruff check --select F .` passes |
| B-10 | Dead code: `count_blocking` + `CONCLUSION_LEADING` + `ModuleBase` + `PolicyResolver` + `rewrite_links` + `_HALF_TO_FULL` | PARTIAL — `count_blocking` deleted (TRA-016 fixed); `PolicyResolver` still test-only but now has a `test_policy_resolver_invoked_in_verify_output` regression test; `rewrite_links` now wired into kernel via `_rewrite_anchors` (TRA-008 fixed); `CONCLUSION_LEADING` (TRA-B2-008), `ModuleBase` (TRA-B2-009), `_HALF_TO_FULL` (TRA-B2-010) still dead |
| B-11 | Unused deps | PERSISTS — see TRA-B2-006, TRA-B2-007 |
| B-12 | Input sanitization bypass at validate/benchmark | FIXED — `sanitize_input` moved to `tra/utils.py`; called from `analyze_document` (isa.py:85-87) as the single chokepoint; `validate.py` and `benchmark.py` both call `analyze_document`. Verified empirically for all 13 required character ranges. |
| B-13 | Cache key determinism | STILL VALID — deterministic; `_hash_sorted` name still misleading (TRA-B2-011) |
| B-14 | Cache-clear `--pattern` silent no-op | FIXED — `cache.invalidate(pattern)` (cache.py:107-128) now uses `fnmatch.fnmatch` over `iterkeys()`; returns count of deleted entries; CLI reports count (tra_cli.py:138-149). Verified empirically: `invalidate("translation:*")` deletes 2 of 3 entries. |
| B-15 | Path traversal | FIXED — `BootstrapConfig._validate_paths_within_base_dir` (config.py:55-79) rejects `..` and absolute paths outside `base_dir` via `Path.relative_to(base)`. 5 regression tests in `TestTRA014PathTraversal`. Verified empirically. (Minor gap: `base_dir` not readable from YAML — see TRA-B2-012.) |
| B-16 | Pydantic immutability unenforced | FIXED — see B-2 |
| B-17 | Dependency hygiene | PERSISTS — see TRA-B2-006, TRA-B2-007 |
| B-18 | Non-reproducible audit trail | FIXED — see Reproducibility probe above |
