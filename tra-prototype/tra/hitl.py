"""Human-in-the-loop review hooks (Spec §6.2 / implementation_plan §6.2).

When the Kernel reaches an UNRECOVERABLE decision (repair loop exhausted, or
structural repair needs manual intervention), it hands off to a human instead
of silently publishing a non-conformant candidate. The review surface is a
minimal, accessible CLI: show the violation + source context, and let the
reviewer accept the machine output, supply an override, or skip (leave the
awaiting-flag in the ambiguity register for downstream resolution).
"""

from __future__ import annotations

from collections.abc import Callable

from rich.console import Console
from rich.prompt import Prompt

from .diagnostics import Diagnostic
from .memory import RuntimeContext

console = Console()


def review_decision(
    uncertainty: str,
    source_context: str,
    candidate: str,
    glossary_options: list[str] | None = None,
    *,
    on_override: Callable[[str, str], str] | None = None,
) -> tuple[str, str]:
    """Pause for human review of an unresolved ambiguity / unrecoverable.

    Returns (resolution, text) where `resolution` is one of
    {"accept", "override", "skip"} and `text` is the adopted target text
    (unchanged candidate for accept/skip; reviewer-supplied for override).

    `on_override` lets the caller re-run translation on the supplied text
    (e.g. re-verify the human text). If omitted, override text is returned
    verbatim.
    """
    console.rule("[bold yellow]HUMAN-IN-THE-LOOP[/bold yellow]")
    console.print(f"[yellow]Ambiguity:[/yellow] {uncertainty}")
    console.print(f"[dim]Source context:[/dim] {source_context}")
    console.print(f"[dim]Candidate:[/dim] {candidate}")
    if glossary_options:
        console.print(f"[dim]Glossary options:[/dim] {', '.join(glossary_options)}")

    choice = Prompt.ask(
        "Resolution", choices=["accept", "override", "skip"], default="skip"
    )
    if choice == "accept":
        return "accept", candidate
    if choice == "override":
        edited = Prompt.ask("Override text")
        if on_override is not None:
            return "override", on_override(source_context, edited)
        return "override", edited
    return "skip", candidate


def format_unrecoverable(
    ctx: RuntimeContext, diagnostic: Diagnostic, source: str
) -> tuple[str, str]:
    """Build the (uncertainty, source_context) shown for an UNRECOVERABLE.

    `uncertainty` is a human-readable summary; `source_context` is the
    offending source excerpt (best-effort) for reviewer grounding.
    """
    uncertainty = (
        f"UNRECOVERABLE: {diagnostic.issue} "
        f"[{diagnostic.subsystem}] — manual intervention required"
    )
    src_excerpt = source
    if diagnostic.evidence and diagnostic.evidence in source:
        start = max(0, source.index(diagnostic.evidence) - 40)
        end = min(len(source), source.index(diagnostic.evidence) + 40)
        src_excerpt = "…" + source[start:end] + "…"
    return uncertainty, src_excerpt
