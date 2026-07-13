"""Bootstrap configuration loader (tvm_bootstrap, Spec §2.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from .memory import ConformanceLevel, PolicyPriority

DEFAULT_POLICY_STACK: list[PolicyPriority] = [
    PolicyPriority.FACTUAL_INTEGRITY,
    PolicyPriority.STRUCTURAL_INTEGRITY,
    PolicyPriority.ENTITY_PRESERVATION,
    PolicyPriority.TERMINOLOGICAL_CONSISTENCY,
    PolicyPriority.EPISTEMIC_FIDELITY,
    PolicyPriority.TARGET_FLUENCY,
]


class BootstrapConfig(BaseModel):
    """Parsed tvm_bootstrap — read-only Immutable Config segment.

    Frozen (TRA-018): the Immutable Config segment is read-only by spec
    (CLAUDE.md:53 "Memory Model: Immutable Config (read-only)"). CLI
    overrides use `model_copy(update=...)` to produce a new instance
    rather than mutating in place.

    Path safety (TRA-014): all runtime paths (`cache_directory`,
    `compilation_dir`, `audit_trace`) are validated against `base_dir`.
    Paths containing `..` or absolute paths outside `base_dir` are
    rejected at construction. This prevents a malicious config.yaml from
    writing audit traces, compilation artifacts, or cache entries to
    arbitrary filesystem locations.
    """

    model_config = ConfigDict(frozen=True)

    language_pair: str
    domain: str
    conformance_level: ConformanceLevel
    model_endpoint: str
    model_version: str
    cache_enabled: bool = True
    cache_directory: str = "./cache"
    repair_max_retries: int = 3
    compilation_dir: str = "./compilation_artifacts"
    audit_trace: str = "./audit_trace.jsonl"
    # Base directory for path-safety validation (TRA-014). Defaults to CWD.
    # When set, all runtime paths must resolve to a location inside base_dir.
    base_dir: str = "."

    @model_validator(mode="after")
    def _validate_paths_within_base_dir(self) -> BootstrapConfig:
        """Reject paths that escape base_dir via `..` or absolute injection."""
        base = Path(self.base_dir).resolve()
        path_fields = {
            "cache_directory": self.cache_directory,
            "compilation_dir": self.compilation_dir,
            "audit_trace": self.audit_trace,
        }
        for field_name, raw_path in path_fields.items():
            # Resolve the path against base_dir (handles both relative and absolute).
            candidate = (
                (base / raw_path).resolve()
                if not Path(raw_path).is_absolute()
                else Path(raw_path).resolve()
            )
            try:
                candidate.relative_to(base)
            except ValueError as exc:
                raise ValueError(
                    f"{field_name}={raw_path!r} escapes base_dir={self.base_dir!r} "
                    f"(resolves to {candidate!s}, which is outside {base!s}). "
                    f"Path traversal is not allowed."
                ) from exc
        return self

    @classmethod
    def from_yaml(cls, path: str | Path) -> BootstrapConfig:
        raw: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            language_pair=raw["language_pair"],
            domain=raw["domain"],
            conformance_level=ConformanceLevel(raw["conformance_level"]),
            model_endpoint=raw.get("model_endpoint", ""),
            model_version=raw.get("model_version", ""),
            cache_enabled=raw.get("cache", {}).get("enabled", True),
            cache_directory=raw.get("cache", {}).get("directory", "./cache"),
            repair_max_retries=raw.get("repair", {}).get("max_retries", 3),
            compilation_dir=raw.get("artifacts", {}).get(
                "compilation_dir", "./compilation_artifacts"
            ),
            audit_trace=raw.get("artifacts", {}).get(
                "audit_trace", "./audit_trace.jsonl"
            ),
        )

    @property
    def policy_stack(self) -> list[PolicyPriority]:
        return list(DEFAULT_POLICY_STACK)
