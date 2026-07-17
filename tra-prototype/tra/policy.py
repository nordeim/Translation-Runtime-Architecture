"""Policy Engine — deterministic arbitration stack (Spec §5).

Resolves conflicts by comparing PolicyPriority values. Higher priority (lower
int value) always wins. Scope (header_level, code_block_lang, list_nesting)
narrows *which* rules apply — it NEVER reorders the immutable stack.
"""

from __future__ import annotations

from .memory import PolicyPriority


class PolicyResolver:
    """Arbitrates conflicting requirements deterministically."""

    def __init__(self, stack: list[PolicyPriority]) -> None:
        # Precedence map: lower enum value wins.
        self.precedence = {p: p.value for p in stack}

    def resolve(self, a: PolicyPriority, b: PolicyPriority) -> PolicyPriority:
        return a if self.precedence[a] <= self.precedence[b] else b

    def wins(self, candidate: PolicyPriority, over: PolicyPriority) -> bool:
        """True if `candidate` has equal-or-higher priority than `over`."""
        return self.precedence[candidate] <= self.precedence[over]
