# Track B3 — Code Quality & Security Re-Audit (Round 3)

**HEAD audited:** `b783745`
**Methodology:** 4 quality gates + 3-run reproducibility probe + OWASP-aware static review
**Baseline:** Round 2 Track B (7 findings: TRA-016, TRA-017, TRA-026, TRA-013 + 4 TRA-B2-* items carried into master register as TRA-043..047)
**Scope:** `tra-prototype/` production code + tests; OWASP top-10 lens added for Round 3.

## Summary

- **Findings: 13 total (0 BLOCKING / 4 WARNING / 9 INFO)**
- **Quality gates: all 4 green** (`ruff format`, `ruff check`, `mypy --strict tra`, `pytest`)
- **Reproducibility: BYTE-IDENTICAL** across 3 cold-cache L4 runs (TRA-013 holds)
- **Carry-over (Round 2):** 7 reviewed — 5 fixed/confirmed-fixed, 2 persist
- **New (OWASP deep-dive):** 6 — 2 WARNING (LLM output not sanitized, diskcache pickle), 4 INFO (audited-safe + 2 low-severity concerns)

The TRA prototype at `b783745` is materially cleaner than at Round 2's `4b8827c`. Two persistent Round-2 INFO findings (TRA-016 dead `count_blocking` stub, TRA-026 dead `cache.expire` config) were **silently remediated** between `4b8827c` and `b783745`; the Track R3 baseline's "STATIC-FAIL" label for both is a **false positive** caused by the baseline script's check expecting the dead code to still be there. The only persistent carry-over of substance is TRA-017 (6 unused deps still listed in `pyproject.toml`).

The new OWASP deep-dive surfaced two real security gaps that Round 2 did not look for: (1) the LLM seam bypasses `sanitize_input`, re-opening the TRA-012 chokepoint for any caller that wires an LLM; (2) `diskcache` serializes `TranslationResult` dicts via `pickle`, creating an OWASP A08:2021 (Software and Data Integrity Failures) vector if an attacker can write to the cache directory.

## Quality gate results

| Gate | Result | Notes |
|---|---|---|
| `ruff format --check .` | PASS | 39 files already formatted |
| `ruff check .` | PASS | All checks passed! |
| `mypy --strict tra` | PASS | Success: no issues found in 20 source files |
| `pytest tests -q` | PASS | 174 passed in 0.86s |

Test count: **174** (up from 141 in Round 2; +33 new regression tests covering TRA-028, TRA-029, TRA-036, TRA-037, TRA-039, TRA-041, TRA-043, TRA-047, TRA-049, TRA-050, TRA-051, TRA-053, TRA-054, TRA-071).

## Reproducibility probe (TRA-013)

Three cold-cache L4 runs of `python -m tra_cli translate examples/security_advisory_zh.md --level L4` with `cache/` + `compilation_artifacts/` + `audit_trace.jsonl` removed between runs:

| Artifact | Run-1 SHA-256 | Run-2 SHA-256 | Run-3 SHA-256 | Byte-identical? |
|---|---|---|---|---|
| `audit_trace.jsonl` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | `263b901e60ce35b7663e537d936cf658a3c3820a28992ccfaca6bc0af8488797` | YES |
| `evidence_trace.jsonl` | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | `f9831523e851f04ae241c7a458a5893a16536bddb96e61b972476ca0d71b88a4` | YES |
| Output `.md` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | `225d5eded0c4a25292081f14387f3b406ad3c5f6a592f61b5cb7d5f66d9e5f1f` | YES |

All three SHA-256 hashes match the Round 2 baseline exactly — TRA-013 fully remediated and stable across the 5 commits between `4b8827c` → `b783745`.

## Carry-over status vs Round 2

| Round 2 ID | Title | Round 3 status |
|---|---|---|
| TRA-016 | `AuditTrail.count_blocking` stub returning 0 | **FIXED (silently remediated)** — see TRA-B3-C1 |
| TRA-017 | 6 unused deps still in `pyproject.toml` | PERSISTS — see TRA-B3-002 |
| TRA-026 | `config.yaml` `cache.expire` parsed but ignored | **FIXED (silently remediated)** — see TRA-B3-C2 |
| TRA-013 | L4 byte-reproducibility | VERIFIED — 3/3 byte-identical |
| TRA-043 (B2-001) | `RuntimeContext.module: Any` | FIXED — Protocol-based; see TRA-B3-C3 |
| TRA-044 (B2-005) | `route_exception` Unrecoverable silent downgrade | FIXED — explicit BLOCKING+HALT branch |
| TRA-045 (B2-008..010) | Dead code (`CONCLUSION_LEADING` / `ModuleBase` / `_HALF_TO_FULL`) | MOSTLY FIXED — `CONCLUSION_LEADING` deleted; `ModuleBase` ABC replaced by `LanguageModuleProtocol`; `_HALF_TO_FULL` intentionally retained for deferred EN→ZH |
| TRA-046 (B2-011) | `_hash_sorted` misleading name | FIXED — renamed `_hash_canonical_json` |
| TRA-047 (B2-012) | `BootstrapConfig.from_yaml` ignores `base_dir`; no `extra="forbid"` | FIXED — `base_dir` read from YAML; `extra="forbid"` set |
| TRA-B2-002 | `TRAKernel.__init__(registry: object \| None)` requires `# type: ignore` | PERSISTS — see TRA-B3-003 |
| TRA-B2-003 | `_collect_headings(nodes: list[Any])` | PERSISTS — see TRA-B3-004 |
| TRA-B2-004 | Stale `# type: ignore[arg-type]` at `tests/test_recovery.py:95` | PERSISTS — see TRA-B3-005 |

---

## Findings

### TRA-B3-C1 — TRA-016 silently remediated (Track R3 baseline false positive)
- **Severity:** INFO
- **Category:** Code Quality / Dead Code
- **Carry-over or new:** Carry-over (TRA-016, was PERSISTENT in Round 2)
- **Evidence:** `tra/diagnostics.py` (full file, 216 lines); `Grep` for `count_blocking` across `tra-prototype/tra/` → 0 hits
- **Detail:**
  Round 2 reported `AuditTrail.count_blocking` as a stub returning 0 (TRA-016, persistent dead code). At HEAD `b783745`, the stub has been **removed entirely** from `diagnostics.py`. The `AuditTrail` class (diagnostics.py:145-215) now exposes only `__init__`, `append`, `flush`, `load` — no `count_blocking` method exists.
  The Track R3 baseline script (`tra-audit-skills/round3/scripts/track_r3_baseline.py:238-242`) checks `ok = "count_blocking" in diag_src and "return 0" in diag_src`. Since both substrings are now absent, `ok = False`, and the script reports `STATIC-FAIL` — but the message text ("PERSISTENT: AuditTrail.count_blocking still a stub returning 0") is **stale**. The actual state is: finding resolved.
  Real BLOCKING counting continues to live in `reporting.summarize_audit` (reporting.py:32-46, reads `flags_raised`) and `validate.ValidationReport.blocking` (validate.py:39-40, reads `Diagnostic.severity`). The `kernel.py:292` L3 gate also computes `final_blocking = [d for d in final_diags if d.severity == Severity.BLOCKING]` inline.
- **Suggested fix:** Update the Track R3 baseline script's check for TRA-016 to assert `count_blocking NOT in diag_src` (i.e., the finding is resolved when the stub is absent). Update the master register's `round1_status` from `persistent` to `fixed-at-b783745`.

### TRA-B3-C2 — TRA-026 silently remediated (Track R3 baseline false positive)
- **Severity:** INFO
- **Category:** Doc Consistency / Dead Config
- **Carry-over or new:** Carry-over (TRA-026, was PERSISTENT in Round 2)
- **Evidence:** `config.yaml` (full file, 28 lines); `tra/config.py` (full file, 110 lines); `Grep` for `expire` in `tra/config.py` → 0 hits
- **Detail:**
  Round 2 reported `config.yaml`'s `cache.expire` field as parsed-but-ignored dead config (TRA-026, persistent). At HEAD `b783745`:
  - `config.yaml` no longer has a `cache.expire` field. The `cache:` block (config.yaml:16-18) contains only `enabled: true` and `directory: "./cache"`, with a comment "No TTL by design — technical facts are static (CACHE_STRATEGY.md)."
  - `BootstrapConfig.from_yaml` (config.py:84-105) reads only `cache.enabled` and `cache.directory` — `expire` is not read.
  - The only `expire` token in the prototype is `cache.set(key, result.model_dump(mode="json"), expire=None)` at `cache.py:114` — passing `None` to diskcache to disable TTL, which is correct behavior.
  The Track R3 baseline script (`track_r3_baseline.py:286-290`) checks `has_expire = "expire" in cfg_src.lower()`. Since `config.py` no longer contains "expire", `has_expire = False`, and the script reports `STATIC-FAIL` — but the message text ("PERSISTENT: config.py still has cache.expire field (ignored)") is **stale**. The actual state is: finding resolved.
- **Suggested fix:** Update the Track R3 baseline script's check for TRA-026 to assert `expire NOT in cfg_src` (resolved state). Update master register's `round1_status` to `fixed-at-b783745`.

### TRA-B3-C3 — TRA-043 fixed: Protocol-based module typing
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (TRA-043 / Round 2 B2-001)
- **Evidence:** `tra/memory.py:18-21,216`; `tra/modules/base.py:14-56`
- **Detail:**
  `RuntimeContext.module` is now typed as `LanguageModuleProtocol | None = Field(default=None, exclude=True)` (memory.py:216). The Protocol is defined at `modules/base.py:14-56` with `@runtime_checkable`, listing the 7 methods the ISA layer calls (`get_glossary_mappings`, `get_style_profile`, `is_forbidden`, `get_forbidden_targets`, `entity_type_hint`, `apply_zh_rules`, `apply_rules`). `ZHENModule` satisfies it structurally without inheritance. `mypy --strict tra` passes, so a typo like `mod.get_glossary_mapings()` (sic) would now be caught. The previous `Any` typing hole is closed.
  Note: `_module(ctx)` at `isa.py:203` still returns `Any` for backward-compat with the module-level `_MODULE` singleton fallback. The Protocol's `runtime_checkable` decorator means `isinstance` checks pass at runtime, so mypy does not propagate the Protocol type through `_module()`. A future cleanup could change `_module` to return `LanguageModuleProtocol` directly.
- **Suggested fix:** Optional: tighten `_module(ctx) -> LanguageModuleProtocol` in `isa.py:203` and have `_MODULE = ZHENModule()` typed as `LanguageModuleProtocol` to close the last `Any` propagation path.

### TRA-B3-001 — TRA-017 persists: 6 unused dependencies still listed
- **Severity:** WARNING
- **Category:** Code Quality / Dependency Hygiene
- **Carry-over or new:** Carry-over (TRA-017, persistent)
- **Evidence:** `pyproject.toml:12,14,17,20,26,28`; `requirements.txt:5,8,11,15`; `Grep` for `import litellm|from litellm|import structlog|from structlog|pydantic_settings|from pydantic_settings|mdit_py_plugins|from mdit_py_plugins|^import black|^from black|pytest_asyncio` across `tra-prototype/` → 0 hits (only doc references in `SKILL.md` and `README.md`).
- **Detail:**
  All 6 unused deps remain listed in `pyproject.toml`:
  | Dep | Type | Line | Status |
  |---|---|---|---|
  | `pydantic-settings>=2.3` | runtime | 12 | 0 imports |
  | `mdit-py-plugins>=0.4` | runtime | 14 | 0 imports (codebase uses built-in `MarkdownIt().enable("table")`) |
  | `structlog>=24.1` | runtime | 17 | 0 imports |
  | `litellm>=1.49` | runtime | 20 | 0 imports (LLM seam is `Callable[[str, RuntimeContext], str] \| None`); litellm 1.92.0 installed in sandbox pulls 12 unconditional + ~50 transitive packages |
  | `pytest-asyncio>=0.23` | dev | 26 | 0 `async def` / `await` / `asyncio` in `tra/` or `tests/`; plugin loaded but unused |
  | `black>=24.4` | dev | 28 | 0 imports; actual formatter is `ruff format` |
  Same suggested fix as Round 2: move `litellm` to `[project.optional-dependencies] llm = [...]`; drop the other 5 outright. The `[tool.black]` block (pyproject.toml:44-46) should also be removed.
- **Suggested fix:** Unchanged from Round 2. See TRA-017 in master register.

### TRA-B3-002 — OWASP A03:2021 (Injection): LLM seam output bypasses `sanitize_input`
- **Severity:** WARNING
- **Category:** Security / Input Validation (OWASP A03:2021 Injection)
- **Carry-over or new:** New (Round 3 OWASP deep-dive)
- **Evidence:** `tra/isa.py:398-414`; `tra/utils.py:31-42`; `tra/isa.py:85-95` (source-side chokepoint)
- **Detail:**
  `sanitize_input` (utils.py:31-42) is the single chokepoint for stripping dangerous characters — null bytes (`\x00`), C0 control chars (`\x01-\x08\x0b\x0c\x0e-\x1f\x7f`), Unicode bidi overrides (`\u202a-\u202e`, the "Trojan Source" attack range), and BOM (`\ufeff`). It is correctly invoked once on the source at `analyze_document` (isa.py:95), covering every kernel entry point (TRA-012).
  However, when a caller wires the optional `llm_translate` callback, the LLM's response is **not** routed through `sanitize_input`:
  ```python
  # isa.py:398-406
  if llm_translate is not None:
      try:
          target = llm_translate(source_segment, ctx)
          basis = "LLM decision"
          if not target:
              raise ValueError("llm_translate returned empty/None output")
  ```
  The only validation is an empty/None check (`if not target`). The `target` string is then:
  1. Stored in `TranslationResult.translation` and cached to disk via pickle (see TRA-B3-003).
  2. Captured in `EvidenceRecord.target_span` and persisted to `audit_trace.jsonl` + `evidence_trace.jsonl`.
  3. Returned to the kernel as the emitted target markdown.
  A malicious, compromised, or hallucinating LLM could inject control characters / bidi overrides / BOM into the translation, re-opening the TRA-012 chokepoint that was carefully closed on the source side. The injected characters would then propagate into every artifact the L4 forensic trail records.
  The kernel's `verify_output` (isa.py:502-604) does NOT re-check for control characters — it only checks heading count, entity preservation, glossary term leakage, and forbidden drift targets. So injected control chars would not be caught downstream.
  **Empirically verified:** `sanitize_input('Hello\u202eWorld\x00')` returns `'HelloWorld'` (correctly stripped). The LLM path does not invoke this function.
- **Suggested fix:**
  Add `target = sanitize_input(target)` immediately after `target = llm_translate(source_segment, ctx)` in `isa.py:400`, before the empty-check. Import `sanitize_input` from `.utils` (it's already imported in `analyze_document` via a local import — promote it to a module-level import for reuse). Add a regression test:
  ```python
  def test_llm_output_is_sanitized():
      """An LLM returning bidi-override/control chars must have them stripped."""
      def malicious_llm(segment, ctx):
          return "Translated\u202eText\x00"
      result = translate_segment("源", ctx, cache, evidence, audit, llm_translate=malicious_llm)
      assert "\u202e" not in result.translation
      assert "\x00" not in result.translation
  ```

### TRA-B3-003 — OWASP A08:2021 (Insecure Deserialization): diskcache uses pickle for `TranslationResult`
- **Severity:** WARNING
- **Category:** Security / Insecure Deserialization (OWASP A08:2021 Software and Data Integrity Failures)
- **Carry-over or new:** New (Round 3 OWASP deep-dive)
- **Evidence:** `tra/cache.py:101-114`; `diskcache.Disk.put` (uses `pickle.dumps`); `diskcache.Disk.get` (uses `pickle.load`)
- **Detail:**
  `TranslationCache.set` (cache.py:111-114) calls `self._cache.set(key, result.model_dump(mode="json"), expire=None)`. The argument `result.model_dump(mode="json")` is a Python `dict` with JSON-compatible values (str, int, list, dict). However, `diskcache.Cache` uses the default `Disk` class (verified: `diskcache.Cache.__init__` defaults `disk=Disk`), which serializes non-primitive types via `pickle.dumps` and deserializes via `pickle.load`.
  **Verified empirically:** Storing `{'translation': 'hello', 'evidence_ids': ['ev1']}` in diskcache produces a SQLite BLOB starting with `\x80\x05\x95...` — the pickle protocol-5 marker. On `cache.get`, `pickle.load(io.BytesIO(key))` deserializes it back to a dict.
  **Threat model:** The cache directory defaults to `./cache` (config.yaml:18) and is created with `mkdir(parents=True, exist_ok=True)` (cache.py:98) without restrictive permissions. Anyone with write access to `./cache/cache.db` (or who can replace it) can inject a pickle payload with a `__reduce__` method that executes arbitrary code on the next `cache.get()` call — BEFORE `TranslationResult.model_validate(raw)` runs. This is a classic OWASP A08:2021 vector.
  The path-traversal protection in `BootstrapConfig._validate_paths_within_base_dir` (TRA-014) prevents the cache *directory* from being moved outside `base_dir`, but it does NOT protect the cache *file* contents from tampering. A multi-user system where `./cache/` is world-writable, or a CI runner where the cache is restored from an untrusted source, would be vulnerable.
  **Proof of concept:** A 72-byte pickle payload `pickle.dumps(Evil())` where `Evil.__reduce__` returns `(print, ('PWNED',))` would execute `print('PWNED')` on the next `cache.get` call. Real-world exploits use `os.system` or `subprocess.check_call` instead of `print`.
- **Suggested fix:**
  Store the JSON-encoded string instead of the dict. Pickling a `str` is safe (strings have no `__reduce__`):
  ```python
  # cache.py:111-114
  def set(self, key: str, result: TranslationResult) -> None:
      if not self.enabled or self._cache is None:
          return
      self._cache.set(key, result.model_dump_json(), expire=None)  # str, not dict

  # cache.py:101-109
  def get(self, key: str) -> TranslationResult | None:
      if not self.enabled or self._cache is None:
          return None
      raw = self._cache.get(key)
      if raw is None:
          return None
      result = TranslationResult.model_validate_json(raw)  # JSON parse, not pickle
      result.cache_hit = True
      return result
  ```
  Alternatively, instantiate `diskcache.Cache(directory, disk=diskcache.JSONDisk)` to use diskcache's built-in JSON serializer. The string approach is preferred because it makes the cache file human-readable for forensic inspection (L4).
  Add a regression test asserting that `cache.set` then `cache.get` round-trips a `TranslationResult`, and that manually editing the cache file to inject a pickle payload does NOT execute code (the JSON parse path would raise a `ValueError` instead).

### TRA-B3-004 — OWASP A09:2021 (Logging Failures): `exc!r` in audit trail may leak secrets
- **Severity:** INFO
- **Category:** Security / Information Disclosure (OWASP A09:2021 Security Logging and Monitoring Failures)
- **Carry-over or new:** New (Round 3 OWASP deep-dive)
- **Evidence:** `tra/isa.py:434-442`
- **Detail:**
  When the LLM seam degrades to the rule path, `translate_segment` writes the exception repr into the audit trail:
  ```python
  audit.append(
      "TRANSLATE_SEGMENT",
      cache_key,
      [ev_id],
      artifact_snapshot={
          "degraded": True,
          "reason": f"llm_unavailable: {exc!r}",
      },
  )
  ```
  Some LLM client libraries include the prompt, the API key fragment, or the full HTTP response body in their exception messages. For example, `openai.AuthenticationError` includes the request URL and sometimes the Authorization header; `litellm` exceptions include the model name and the failed prompt. Persisting `exc!r` to `audit_trace.jsonl` (which is meant to be shareable for L4 forensic review) could leak these secrets.
  The source-side `exc` is a Python exception object; its `repr` is library-specific and not sanitized. The audit trail is written to `audit_trace.jsonl` in the project's `base_dir` (config-validated, but the file itself has default umask permissions).
  This is a low-severity concern because (a) the LLM seam is caller-supplied and currently no caller is wired in the prototype, (b) the audit trail is intended to be inspectable, and (c) the threat model assumes the operator controls the LLM client. But if a future caller wires `litellm.completion` and the API key is logged, this would be a real secret leak.
- **Suggested fix:**
  Sanitize the exception repr before persisting. Either:
  ```python
  reason = f"llm_unavailable: {type(exc).__name__}: {str(exc)[:200]}"
  ```
  (truncate to 200 chars and use `type(exc).__name__` rather than full `repr`), or scrub known-secret patterns (Authorization headers, Bearer tokens, sk-... OpenAI keys) via a regex before persisting. Document the scrubbing in the `AuditRecord` schema.

### TRA-B3-005 — TRA-B2-002 persists: `TRAKernel.__init__(registry: object | None)` still uses `# type: ignore`
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (Round 2 TRA-B2-002 — note: not separately tracked in master register but reported in Round 2 Track B)
- **Evidence:** `tra/kernel.py:91,130,143`
- **Detail:**
  `TRAKernel.__init__` accepts `registry: object | None = None` (kernel.py:91). The static method `_select_module(language_pair, registry: object | None) -> Any` (kernel.py:130) calls `registry.all()` (kernel.py:143) with `# type: ignore[attr-defined]`, because `object` has no `.all()` method.
  A concrete `ModuleRegistry` class exists in `tra/modules/registry.py:25-40` with a properly typed `.all() -> list[ModuleInterface]` method. Using `object | None` defeats mypy's ability to catch typos (`.all()` → `.items()` would compile silently) and wrong-registry-type calls.
  This was reported in Round 2 (TRA-B2-002) but was NOT carried into the master register as a separate TRA-* finding, so it has no Round-3 baseline check. It persists unchanged at `b783745`.
- **Suggested fix:**
  Type the parameter as `ModuleRegistry | None`. Update `tests/test_outstanding_findings.py:575` (which passes a `StubModule` to the registry with `# type: ignore[arg-type]`) to register via `StubModule().as_interface()` (the existing adapter at `zh_en.py:226-235`) so the registry holds a proper `ModuleInterface`. Then both `# type: ignore` comments can be removed.

### TRA-B3-006 — TRA-B2-003 persists: `_collect_headings(nodes: list[Any])` should be `list[StructuralNode]`
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (Round 2 TRA-B2-003 — not separately tracked in master register)
- **Evidence:** `tra/kernel.py:356-362`; `tra/memory.py:106-117` (StructuralNode definition)
- **Detail:**
  The nested helper `_collect_headings` inside `_rewrite_anchors` types its parameter as `list[Any]`:
  ```python
  def _collect_headings(nodes: list[Any]) -> None:
      for node in nodes:
          if node.kind.value == "heading" and node.text:
              source_headings.append(node.text)
          _collect_headings(node.children)
  ```
  The actual element type is `StructuralNode` (memory.py:106-117), which has `.kind: NodeKind`, `.text: str | None`, `.children: list[StructuralNode]`. `StructuralNode` is not imported in `kernel.py` (only `StructuralMap` is, at kernel.py:43). Using `list[Any]` means mypy cannot verify `node.kind.value` vs `node.kinds.value` (typo).
  Not separately tracked in master register; persists unchanged at `b783745`.
- **Suggested fix:** Add `StructuralNode` to the import from `.memory` at kernel.py:38-44, then change the helper signature to `def _collect_headings(nodes: list[StructuralNode]) -> None:`.

### TRA-B3-007 — TRA-B2-004 persists: stale `# type: ignore[arg-type]` at `tests/test_recovery.py:95`
- **Severity:** INFO
- **Category:** Code Quality / Type Safety
- **Carry-over or new:** Carry-over (Round 2 TRA-B2-004)
- **Evidence:** `tests/test_recovery.py:93-96`
- **Detail:**
  ```python
  def test_route_exception_falls_back_for_unknown():
      amb: list[str] = []
      rep = route_exception(BrokenMarkdown(), amb)  # type: ignore[arg-type]
      assert isinstance(rep, RecoveryReport)
  ```
  The `# type: ignore[arg-type]` is stale. `BrokenMarkdown()` (exceptions.py) accepts `message: str = ""` and `*, detail: str = ""` — both optional. The call is type-correct. `mypy --strict tests/test_recovery.py` reports `Unused "type: ignore" comment [unused-ignore]` (per Round 2 report). The production gate `mypy --strict tra` doesn't check `tests/`, so this doesn't fail the gate.
- **Suggested fix:** Remove the `# type: ignore[arg-type]` comment. Optionally, add `tests/` to the `mypy --strict` gate by annotating all test functions with `-> None`.

### TRA-B3-008 — OWASP A01:2021 (Broken Access Control): Path traversal protection verified safe (symlinks covered)
- **Severity:** INFO
- **Category:** Security / Path Traversal (OWASP A01:2021)
- **Carry-over or new:** New (Round 3 OWASP deep-dive, confirmed-safe)
- **Evidence:** `tra/config.py:58-82`; empirical verification
- **Detail:**
  `BootstrapConfig._validate_paths_within_base_dir` (config.py:58-82) uses `Path.resolve()` to canonicalize both `base_dir` and each runtime path (`cache_directory`, `compilation_dir`, `audit_trace`) before checking `relative_to(base)`. `Path.resolve()` follows symlinks, so a symlinked `cache_directory` that escapes `base_dir` would be resolved to its target and rejected by `relative_to`.
  **Verified empirically:**
  - `cache_directory="/etc"` with `base_dir="/tmp/test_base"` → `ValidationError` (rejected).
  - `cache_directory="../../etc"` with `base_dir="/tmp/test_base"` → `ValidationError` (rejected).
  - `cache_directory="./cache"` with `base_dir="/tmp/test_base"` → accepted.
  Note (low severity): there is a TOCTOU window between config validation (which resolves the path) and the actual file write in `_export_artifacts` (kernel.py:509-573). The kernel writes via `Path(self.config.compilation_dir) / "glossary.yaml"` without re-resolving. If an attacker can replace `compilation_dir` with a symlink between config load and kernel run, the write would follow the symlink. In practice this requires filesystem access during the run window, which is unusual for the prototype's threat model. Mitigation: re-resolve and re-validate paths in `_export_artifacts` before each write, or open files with `O_NOFOLLOW`.
  All `Path.read_text()` / `Path.write_text()` / `open()` calls in `tra/` operate on either (a) config-validated paths, (b) CLI-supplied source paths (trusted — the user is on the CLI), or (c) `tmp_path` in tests. No unvalidated user input reaches a file operation.
- **Suggested fix:** Optional hardening: re-resolve `compilation_dir` / `audit_trace` / `cache_directory` immediately before each write in `_export_artifacts` and `AuditTrail.flush` to close the TOCTOU window.

### TRA-B3-009 — OWASP A03:2021 (Injection): `sanitize_input` covers all required character ranges (verified safe)
- **Severity:** INFO
- **Category:** Security / Input Validation (OWASP A03:2021)
- **Carry-over or new:** New (Round 3 OWASP deep-dive, confirmed-safe)
- **Evidence:** `tra/utils.py:26-42`
- **Detail:**
  `sanitize_input` uses a single regex `_CONTROL_RE = re.compile("[" + "\x00-\x08\x0b\x0c\x0e-\x1f\x7f" + "\u202a-\u202e" + "\ufeff" + "]")` to strip:
  - Null byte (`\x00`) — would truncate strings in C-backed libraries.
  - C0 control chars (`\x01-\x08`, `\x0b`, `\x0c`, `\x0e-\x1f`, `\x7f` DEL) — terminal escape sequences, BEL, BS, etc.
  - Unicode bidi overrides (`\u202a-\u202e`: LRE, RLE, PDF, LRO, RLO) — the "Trojan Source" attack range (CVE-2021-42574).
  - BOM (`\ufeff`).
  Legitimate whitespace (`\n`, `\t`, `\r`, space) is preserved (markdown needs them).
  **Verified empirically:**
  - `sanitize_input('hello\x00world')` → `'helloworld'`
  - `sanitize_input('hello\u202eworld')` → `'helloworld'` (RLO stripped)
  - `sanitize_input('hello\u202aworld')` → `'helloworld'` (LRE stripped)
  - `sanitize_input('\ufeffhello')` → `'hello'` (BOM stripped)
  - `sanitize_input('hello\n\tworld')` → `'hello\n\tworld'` (preserved)
  This is a solid implementation of the TRA-012 chokepoint on the source side. The gap is on the LLM-output side (see TRA-B3-002).
- **Suggested fix:** None — source-side sanitization is correct. Apply the same chokepoint to LLM output per TRA-B3-002.

### TRA-B3-010 — OWASP A05:2021 (Security Misconfiguration): All YAML loads use `safe_load` (verified safe)
- **Severity:** INFO
- **Category:** Security / YAML Deserialization (OWASP A05 / A08)
- **Carry-over or new:** New (Round 3 OWASP deep-dive, confirmed-safe)
- **Evidence:** `Grep` for `yaml\.(load|safe_load|full_load|unsafe_load)` across `tra-prototype/` → 3 hits, all `yaml.safe_load`:
  - `tra/config.py:86` — `yaml.safe_load(Path(path).read_text(encoding="utf-8"))`
  - `tests/test_e2e_to_translate.py:217` — `yaml.safe_load(glossary_path.read_text(encoding="utf-8"))`
  - `tests/test_e2e_to_translate.py:237` — `yaml.safe_load(entity_path.read_text(encoding="utf-8"))`
- **Detail:**
  Zero `yaml.load(...)` calls without `Loader=`. Zero `yaml.full_load` / `yaml.unsafe_load` / `yaml.unsafe_load_all`. The codebase uses `yaml.safe_load` exclusively, which only constructs simple Python objects (str, int, list, dict) and rejects arbitrary Python object construction (no `!!python/object` tags). This is the correct mitigation for the CVE-2017-18342-style YAML deserialization vulnerability.
  The kernel's `_export_artifacts` (kernel.py:509-573) uses `yaml.safe_dump` to write glossary/entity/style artifacts, ensuring the round-trip is safe.
- **Suggested fix:** None.

### TRA-B3-011 — OWASP A04:2021 (Insecure Design): No ReDoS in kernel.py / anchor.py regex patterns (verified safe)
- **Severity:** INFO
- **Category:** Security / ReDoS (OWASP A04 Insecure Design)
- **Carry-over or new:** New (Round 3 OWASP deep-dive, confirmed-safe)
- **Evidence:** `tra/kernel.py:343,364,420,430`; `tra/anchor.py:34-37,117-119`; `tra/isa.py:66,145`; `tra/utils.py:26,47,50,53,56,61,64`
- **Detail:**
  All regex patterns in the production code path were reviewed for catastrophic backtracking:
  | Pattern | Location | Verdict |
  |---|---|---|
  | `\]\(#([^)]+)\)` | kernel.py:343 | Bounded `[^)]+` — no nested quantifier. Safe. |
  | `^(#{1,6})\s+(.*)$` (MULTILINE) | kernel.py:364 | `.*` doesn't match newline (no DOTALL). Safe. |
  | ` ```[^\n]*\n.*?``` ` (DOTALL) | kernel.py:420 | `[^\n]*` bounded by newline; `.*?` lazy. Worst case linear scan of document. Safe. |
  | `` `[^`\n]+` `` | kernel.py:430 | Bounded `[^`\n]+`. Safe. |
  | `[^\w\s-]` (UNICODE) | anchor.py:34 | Character class, no quantifier. Safe. |
  | `\s+` (UNICODE) | anchor.py:35 | Greedy but no nested quantifier. Safe. |
  | `h(\d)` | anchor.py:37 | Fixed pattern. Safe. |
  | `(\[[^\]]*\])\(#([^)\s]+)\)` | anchor.py:117 | Both character classes bounded. Safe. |
  | `^\s*``` ` | anchor.py:118 | `\s*` then fixed. Safe. |
  | `^\s*```\s*$` | anchor.py:119 | `\s*` bounded by `$`. Safe. |
  | `^(#{1,6})\s+(.*)$` (MULTILINE) | isa.py:66 | Same as kernel.py:364. Safe. |
  | `^[ \t]*(`{3,}\|~{3,})[^\n]*$` (MULTILINE) | isa.py:145 | Bounded. Safe. |
  | Character class | utils.py:26 | `_CONTROL_RE` — character class, no quantifier. Safe. |
  | `\b[A-Z][A-Za-z0-9]*...\b` | utils.py:47,50,53,56 | Standard token patterns, no nested quantifiers. Safe. |
  | `^[A-Z][a-z]{2,}$` | utils.py:61 | Bounded. Safe. |
  | `(?:\d\|[a-z][A-Z]\|VMM\|VM\|DB\|API\|SDK\|Kit\|Engine)` | utils.py:64 | Alternation, no quantifier. Safe. |
  No pattern uses nested quantifiers (e.g., `(a+)+`), overlapping alternations (e.g., `(a\|a)*`), or unbounded greedy matches with backtracking potential. The codebase is not vulnerable to ReDoS on adversarial input.
- **Suggested fix:** None.

### TRA-B3-012 — OWASP A02:2021 (Cryptographic Failures): `TranslationResult` cache entries are not integrity-protected
- **Severity:** INFO
- **Category:** Security / Integrity (OWASP A02 / A08 hybrid)
- **Carry-over or new:** New (Round 3 OWASP deep-dive)
- **Evidence:** `tra/cache.py:101-114`; `tra/diagnostics.py:45-63` (content-addressed evidence IDs)
- **Detail:**
  The audit trail uses content-addressed evidence IDs (`ev_{sha256(canonical_record)[:12]}`, diagnostics.py:45-63) and content-addressed cache keys (`CacheKeyContext.key()` = SHA-256 of canonical context, cache.py:64-76). Both are reproducibility measures, not integrity measures.
  The cache *value* (`TranslationResult.model_dump(mode="json")`) is stored as a pickled blob in `cache.db` with no signature, MAC, or hash. A tampered cache entry (e.g., one where the translation text is changed but the cache key is preserved) would be served transparently on the next `cache.get`, because `TranslationResult.model_validate(raw)` only checks schema, not content.
  This compounds with TRA-B3-003 (pickle deserialization): an attacker who can write to the cache can either (a) execute code via pickle, or (b) silently substitute a different `TranslationResult.translation` for the same cache key. Option (b) is a translation-integrity attack — the L4 audit trail would still record the original `cache_key` (derived from source + glossary + entity + model + policy), but the emitted target would be the attacker's substituted text.
  In the prototype's threat model (single-user dev sandbox, no untrusted cache source), this is low-severity. For a CI-shared cache or a multi-tenant deployment, it would be BLOCKING.
- **Suggested fix:**
  Add a HMAC-SHA256 over the cache value, keyed by a per-run secret derived from `BootstrapConfig` (e.g., `hmac.new(key=cfg.model_endpoint.encode(), msg=value_bytes, digestmod=hashlib.sha256).hexdigest()`). Store `{value: ..., mac: ...}` as the cached object. On `cache.get`, verify the MAC before deserializing. This closes both the integrity gap (TRT-B3-012) and partially mitigates the pickle RCE (TRA-B3-003) — a tampered pickle without a valid MAC would be rejected before `pickle.load`.

---

## Appendix: Test-suite `# type: ignore` and `# noqa` audit

| File:Line | Comment | Justified? |
|---|---|---|
| `tra/kernel.py:143` | `# type: ignore[attr-defined]` on `registry.all()` | No — see TRA-B3-005 (TRA-B2-002 carry-over) |
| `tra/isa.py:102` | `# noqa: BLE001 - surface as spec failure` | Yes — broad except wrapping markdown-it-py parse to surface as `BrokenMarkdown` |
| `tra/isa.py:407` | `# noqa: BLE001 - graceful degradation (§6.5.4)` | Yes — broad except wrapping LLM call for graceful degradation to rule path |
| `tests/test_recovery.py:95` | `# type: ignore[arg-type]` | No — stale; see TRA-B3-007 (TRA-B2-004 carry-over) |
| `tests/test_outstanding_findings.py:129` | `# noqa: F401` on `sanitize_input` import | Yes — test asserts the symbol is importable from `tra.utils` |
| `tests/test_outstanding_findings.py:575` | `# type: ignore[arg-type]` on `registry.register(stub)` | No — see TRA-B3-005 fix (use `StubModule().as_interface()`) |
| `tests/test_kernel.py:112,117` | `# type: ignore[method-assign]` on `ZHENModule.get_glossary_mappings = lambda ...` | Yes — test monkey-patches a class method, then restores |
| `tests/test_phase6_hardening.py:160` | `# noqa: ANN001` on `fake_ask` param | Yes — test stub matching `rich.prompt.Prompt.ask` signature |
| `tests/test_tra047_config_robustness.py:87` | `# type: ignore[call-arg]` on `typoed_field=...` | Yes — negative test asserting `extra="forbid"` rejects unknown fields |

## Appendix: Any-typed sites in production code (`tra/`)

| File:Line | Site | Justified? |
|---|---|---|
| `tra/config.py:86` | `raw: dict[str, Any]` from `yaml.safe_load` | Yes — YAML returns arbitrary dict; `from_yaml` extracts typed fields |
| `tra/memory.py:117` | `StructuralNode.metadata: dict[str, Any]` | Yes — open-ended metadata bag (e.g., `{lang: "python"}` for code blocks) |
| `tra/memory.py:200` | `RuntimeContext.configuration: dict[str, Any]` | Yes — stores `config.model_dump()` (heterogeneous) |
| `tra/memory.py:220` | `RuntimeContext.anchor_registry: Any` | Partially — `AnchorRegistry` is a concrete class; could be typed as `AnchorRegistry \| None`. Low priority. |
| `tra/modules/registry.py:22` | `ModuleInterface.metadata: dict[str, Any]` | Yes — open-ended metadata bag |
| `tra/diagnostics.py:97,174` | `AuditRecord.artifact_snapshot: dict[str, Any]` | Yes — heterogeneous snapshot (e.g., `{node_count: int, type: str}`) |
| `tra/kernel.py:130` | `_select_module(...) -> Any` | No — should return `LanguageModuleProtocol` (see TRA-B3-C3) |
| `tra/kernel.py:356` | `_collect_headings(nodes: list[Any])` | No — should be `list[StructuralNode]` (see TRA-B3-006) |
| `tra/reporting.py:21,73,82` | `dict[str, Any]` returns | Yes — summary/trace are heterogeneous dicts |
| `tra/isa.py:203` | `_module(ctx) -> Any` | Partially — could return `LanguageModuleProtocol` (see TRA-B3-C3) |
| `tra/isa.py:467` | `_rule_translate(..., module: Any = None)` | Partially — could be `LanguageModuleProtocol \| None` |
| `tra/cache.py:28,33,44` | `_canonical_json/_hash_canonical_json/_hash_set` `payload: Any` | Yes — generic hash helpers accept any JSON-serializable |
| `tra/cache.py:94` | `self._cache: Any` | Partially — diskcache has no stubs; could use a `Protocol` (TRA-B2-013 carry-over) |
