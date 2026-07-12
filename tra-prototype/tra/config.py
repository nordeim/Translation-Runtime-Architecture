"""Bootstrap configuration loader (tvm_bootstrap, Spec §2.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

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
    """Parsed tvm_bootstrap — read-only Immutable Config segment."""

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
