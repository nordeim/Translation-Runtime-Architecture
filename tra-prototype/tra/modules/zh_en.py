"""ZH <-> EN linguistic bridge module (Spec §9, TRA-MODULE-ZH-EN.md).

Concrete example of a Language Module. Provides canonical terminology
mappings, epistemic-lexicon enforcement, a StyleProfile, and
pre/post-processing hooks. MUST NOT alter the Kernel or ISA — only
supplies data consumed by the Runtime Context.
"""

from __future__ import annotations

from ..memory import EntityType, StyleProfile

# Canonical source -> target terminology (Spec §3 + TRA-MODULE-ZH-EN §3).
# Keys are Chinese surface forms; values are the binding English target.
GLOSSARY: dict[str, str] = {
    "成立": "Confirmed",
    "执行环境": "execution environment",
    "准确描述": "accurately describes",
    "高度可信": "highly credible",
    "可能": "may",
    "进行验证": "verify",
    "实现优化": "optimize",
    "提供支持": "support",
    "硬件隔离": "Hardware isolation",
    "无缝迁移": "Seamless migration",
    "高可用性": "High availability",
}

# Epistemic-certainty lexicon — exact, never strengthened/weakened.
EPISTEMIC_LEXICON: dict[str, str] = {
    "成立": "Confirmed",
    "准确描述": "accurately describes",
    "高度可信": "highly credible",
    "可能": "may",
}

# Forbidden (drift) targets — mapping to these is a CONFLICTING_MAPPING.
FORBIDDEN_TARGETS: dict[str, str] = {
    "成立": "Valid/True/Correct",
    "执行环境": "runtime",
    "高度可信": "indisputably true",
}


# Suffix/leading forms that may wrap a term (e.g. full-width punct).
_TERM_BOUNDARY = "，。：:；;、, .!?（）()\n "


class ZHENModule:
    """ZH <-> EN Language Module (Spec §9)."""

    name = "zh_en"
    kind = "language"
    direction = "ZH -> EN"

    def get_glossary_mappings(self) -> dict[str, str]:
        """Canonical source-term -> target-term mappings."""
        return dict(GLOSSARY)

    def get_forbidden_targets(self) -> dict[str, str]:
        """Drift targets that must NOT be produced for a given source."""
        return dict(FORBIDDEN_TARGETS)

    def get_style_profile(self) -> StyleProfile:
        """Target style for ZH -> EN technical advisory prose."""
        return StyleProfile(
            voice="Passive/Objective",
            sentence_complexity="High",
            epistemic_mapping=dict(EPISTEMIC_LEXICON),
            punctuation_rules={
                "preserve_fullwidth_for_zh": "true",
                "halfwidth_inside_code": "true",
            },
        )

    def epistemic_target(self, source: str) -> str | None:
        """Exact epistemic-certainty target for `source`, or None."""
        return EPISTEMIC_LEXICON.get(source)

    def is_forbidden(self, source: str, target: str) -> bool:
        """True if `target` is a known drift mapping for `source`."""
        banned = FORBIDDEN_TARGETS.get(source)
        return banned is not None and target in banned.split("/")

    def apply_rules(self, source: str, direction: str) -> str:
        """Pre/post-processing hook. Identity for now; ZH->EN structural
        bridge (parataxis->hypotaxis) is applied by the translator, not here.
        """
        return source

    # --- entity-type hints (Spec §3 ENTITY_AMBIGUITY) -------------

    @staticmethod
    def entity_type_hint(token: str) -> EntityType | None:
        """Optional hint: ZH-EN knows a few stable entity families."""
        if token in ("RustVMM", "Firecracker", "Containerd"):
            return EntityType.PRODUCT
        return None
