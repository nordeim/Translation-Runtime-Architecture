"""ZH <-> EN linguistic bridge module (Spec §9, TRA-MODULE-ZH-EN.md).

Concrete example of a Language Module. Provides canonical terminology
mappings, epistemic-lexicon enforcement, a StyleProfile, and pre/post-
processing rule layers (parataxis->hypotaxis, nominalization verbalization,
information-order, punctuation normalization, EN->ZH four-char + passive
reduction). MUST NOT alter the Kernel or ISA — only supplies data/behaviour
consumed by the Runtime Context.
"""

from __future__ import annotations

import re

from ..memory import EntityType, StyleProfile
from .registry import ModuleInterface

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

# --- Rule layers (Spec §9 + implementation_plan.md Phase 4.2 / 4.3) ---------

# Parataxis -> Hypotaxis (ZH topic-comment -> EN subject-predicate).
# Curated canonical forms only; free-form parataxis is an LLM concern — the
# deterministic path covers known patterns without risking mistranslation.
TOPIC_COMMENT: dict[str, str] = {
    "系统成立": "The system is Confirmed",
    "结论成立": "The conclusion is Confirmed",
    "假设成立": "The hypothesis is Confirmed",
    "理论成立": "The theory is Confirmed",
    "条件成立": "The condition is Confirmed",
}

# Nominalization verbalization (nominalized verb-object -> verb, ZH -> EN).
NOMINALIZATION: dict[str, str] = {
    "进行验证": "verify",
    "实现优化": "optimize",
    "提供支持": "support",
    "开展测试": "test",
    "完成部署": "deploy",
    "执行迁移": "migrate",
}

# EN -> ZH four-character expressions (四字格) for translationese handling.
FOUR_CHAR_MAP: dict[str, str] = {
    "seamless migration": "无缝迁移",
    "high availability": "高可用性",
    "hardware isolation": "硬件隔离",
}

# EN -> ZH passive-reduction: passive voice -> active where a stable subject
# exists (translationese avoidance). Curated, lexical rather than syntactic.
PASSIVE_REDUCTION: dict[str, str] = {
    "is confirmed": "已确认",
    "are confirmed": "已确认",
    "was verified": "已验证",
    "were verified": "已验证",
    "is supported": "已支持",
    "are supported": "已支持",
}

# Punctuation normalization tables (full-width CJK <-> half-width).
_FULL_TO_HALF: dict[str, str] = {
    "，": ", ",
    "。": ". ",
    "：": ": ",
    "；": "; ",
    "（": "(",
    "）": ")",
    "！": "! ",
    "？": "? ",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}
_HALF_TO_FULL: dict[str, str] = {
    ",": "，",
    ".": "。",
    ":": "：",
    ";": "；",
    "(": "（",
    ")": "）",
    "!": "！",
    "?": "？",
}

# Convenience: longest-key-first ordering for multi-key substitution.
_ORDERED_TOPIC = sorted(TOPIC_COMMENT, key=len, reverse=True)
_ORDERED_NOM = sorted(NOMINALIZATION, key=len, reverse=True)
_ORDERED_FULL = sorted(_FULL_TO_HALF, key=len, reverse=True)
_ORDERED_HALF = sorted(_HALF_TO_FULL, key=len, reverse=True)
_WS_RE = re.compile(r" {2,}")


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

    # --- ZH -> EN rule layer --------------------------------------------

    def apply_zh_rules(self, text: str) -> str:
        """Parataxis->hypotaxis, nominalization, half-width punctuation.

        Operates only on explicit canonical CJK forms; mixed English text
        passes through unchanged (deterministic, no mistranslation risk).
        """
        out = text
        for key in _ORDERED_TOPIC:
            if key in out:
                out = out.replace(key, TOPIC_COMMENT[key])
        for key in _ORDERED_NOM:
            if key in out:
                out = out.replace(key, NOMINALIZATION[key])
        out = self._normalize_punctuation(out, to="half")
        return out

    # --- EN -> ZH rule layer --------------------------------------------

    def apply_en_rules(self, text: str) -> str:
        """Translationese avoidance, four-char map, full-width punctuation.

        Matching is case-insensitive via regex (re.IGNORECASE) so EN->ZH targets
        such as 'Seamless migration' round-trip into 四字格 forms regardless of
        case. English casing of non-matched spans is preserved.
        """
        out = text
        for key in sorted(FOUR_CHAR_MAP, key=len, reverse=True):
            out = re.sub(re.escape(key), FOUR_CHAR_MAP[key], out, flags=re.IGNORECASE)
        for key in sorted(PASSIVE_REDUCTION, key=len, reverse=True):
            out = re.sub(
                re.escape(key), PASSIVE_REDUCTION[key], out, flags=re.IGNORECASE
            )
        out = self._normalize_punctuation(out, to="full")
        return out

    def _normalize_punctuation(self, text: str, *, to: str) -> str:
        """Convert CJK full-width <-> half-width punctuation, then collapse
        any double spaces introduced by the substitution.
        """
        table = _FULL_TO_HALF if to == "half" else _HALF_TO_FULL
        ordered = _ORDERED_FULL if to == "half" else _ORDERED_HALF
        out = text
        for key in ordered:
            if key in out:
                out = out.replace(key, table[key])
        return _WS_RE.sub(" ", out).strip()

    def apply_rules(self, source: str, direction: str) -> str:
        """Pre/post-processing dispatcher (implementation_plan.md §4.4.3).

        Routes by `direction` (`ZH -> EN` or `EN -> ZH`). Identity for any
        other direction.
        """
        if direction.startswith("ZH"):
            return self.apply_zh_rules(source)
        if direction.startswith("EN"):
            return self.apply_en_rules(source)
        return source

    def as_interface(self) -> ModuleInterface:
        """Adapt this module to the registry contract (Phase 4.1.2)."""
        return ModuleInterface(
            name=self.name,
            kind=self.kind,
            get_glossary_mappings=self.get_glossary_mappings,
            get_style_profile=self.get_style_profile,
            apply_rules=self.apply_rules,
            metadata={"direction": self.direction},
        )

    # --- entity-type hints (Spec §3 ENTITY_AMBIGUITY) -------------

    @staticmethod
    def entity_type_hint(token: str) -> EntityType | None:
        """Optional hint: ZH-EN knows a few stable entity families."""
        if token in ("RustVMM", "Firecracker", "Containerd"):
            return EntityType.PRODUCT
        return None
