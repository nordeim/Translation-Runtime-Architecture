"""TRA prototype CLI.

Subcommands:
  translate    Run the full TRA pipeline on a Markdown file.
  validate     Standalone L3/L4 conformance gate (zero BLOCKING = PASS).
  audit        Summarize an audit_trace.jsonl (+ conformance report).
  cache-clear  Invalidate the deterministic cache (glob or full clear).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from tra.cache import TranslationCache
from tra.config import BootstrapConfig
from tra.diagnostics import AuditTrail
from tra.memory import ConformanceLevel
from tra.reporting import mermaid_state_diagram, summarize_audit
from tra.validate import ValidationReport, validate_translation

console = Console()

# Accept either full conformance values (L3_STRICT) or shorthand (L3).
_LEVEL_ALIASES = {
    "l1": "L1_BASIC",
    "l2": "L2_PROFESSIONAL",
    "l3": "L3_STRICT",
    "l4": "L4_FORENSIC",
}


def _resolve_level(value: str) -> ConformanceLevel:
    """Resolve a conformance level from full value or shorthand (L3 / L3_STRICT)."""
    try:
        return ConformanceLevel(value)
    except ValueError:
        canonical = _LEVEL_ALIASES.get(value.strip().lower())
        if canonical is None:
            raise click.BadParameter(
                "unknown conformance level "
                f"{value!r}; use L1-L4 or L1_BASIC..L4_FORENSIC"
            ) from None
        return ConformanceLevel(canonical)


@click.group()
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    show_default=True,
    help="Path to tvm_bootstrap config.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """TRA prototype command-line interface."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@cli.command()
@click.argument("input_md", type=click.Path(exists=True, path_type=Path))
@click.option("--lang", default=None, help="Language pair override, e.g. zh-en.")
@click.option("--level", default=None, help="Conformance level, e.g. L3.")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Pause for human review on UNRECOVERABLE (RAISE_FLAG) decisions.",
)
@click.pass_context
def translate(
    ctx: click.Context,
    input_md: Path,
    lang: str | None,
    level: str | None,
    output: Path | None,
    interactive: bool,
) -> None:
    """Translate INPUT_MD through the full TRA pipeline."""
    cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
    # BootstrapConfig is frozen (TRA-018); use model_copy to apply overrides
    # rather than mutating in place.
    updates: dict[str, Any] = {}
    if lang:
        updates["language_pair"] = lang
    if level:
        updates["conformance_level"] = _resolve_level(level)
    if updates:
        cfg = cfg.model_copy(update=updates)

    console.print(
        f"[bold]TRA[/bold] bootstrap OK — "
        f"pair=[cyan]{cfg.language_pair}[/cyan] "
        f"level=[cyan]{cfg.conformance_level.value}[/cyan]"
    )

    from tra.exceptions import ConformanceFailure
    from tra.kernel import TRAKernel

    kernel = TRAKernel(cfg, interactive=interactive)
    try:
        target = kernel.run(input_md)
    except ConformanceFailure as exc:
        # L3+ gate enforced in-band by the kernel (TRA-005). A non-conformant
        # output must never be silently published as "translated".
        console.print(
            f"[red]CONFORMANCE FAILURE[/red] — {exc}\n"
            f"  Review [cyan]{cfg.audit_trace}[/cyan] and "
            f"[cyan]{cfg.compilation_dir}/[/cyan] before publishing."
        )
        raise SystemExit(1) from exc

    if output is None:
        output = input_md.with_name(f"{input_md.stem}.translated.md")
    output.write_text(target, encoding="utf-8")

    console.print(
        f"[green]Translated[/green] -> [cyan]{output}[/cyan]  "
        f"(audit: {cfg.audit_trace}, "
        f"artifacts: {cfg.compilation_dir})"
    )


@cli.command(name="cache-clear")
@click.option("--pattern", default=None, help="Optional fnmatch glob to delete.")
@click.pass_context
def cache_clear(ctx: click.Context, pattern: str | None) -> None:
    """Invalidate cache entries (manual; no TTL)."""
    cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
    cache = TranslationCache(cfg.cache_directory, enabled=cfg.cache_enabled)
    deleted = cache.invalidate(pattern)
    target = pattern or "ALL"
    if deleted:
        console.print(
            f"[green]Cache invalidated:[/green] {target} "
            f"([bold]{deleted}[/bold] entr{'y' if deleted == 1 else 'ies'} deleted)"
        )
    else:
        console.print(
            f"[yellow]Cache invalidated:[/yellow] {target} "
            f"([dim]0 entries matched — nothing deleted[/dim])"
        )


@cli.command()
@click.argument("trace", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["summary", "json"]),
    default="summary",
)
@click.option(
    "--report",
    is_flag=True,
    default=False,
    help="Print the conformance summary + Mermaid state diagram.",
)
@click.pass_context
def audit(ctx: click.Context, trace: Path, fmt: str, report: bool) -> None:
    """Summarize an audit_trace.jsonl file."""
    trail = AuditTrail(trace)
    records = trail.load()
    if fmt == "json" and not report:
        for rec in records:
            console.print_json(rec.model_dump_json())
        return
    table = Table(title=f"Audit trace: {trace}")
    table.add_column("Seq", justify="right")
    table.add_column("Instruction")
    table.add_column("Evidence", justify="right")
    table.add_column("Flags")
    for rec in records:
        table.add_row(
            str(rec.sequence_id),
            rec.isa_instruction,
            str(len(rec.evidence_chain)),
            ", ".join(rec.flags_raised or []) or "-",
        )
    console.print(table)
    console.print(f"[bold]{len(records)}[/bold] records")

    if report:
        summary = summarize_audit(trail)
        console.print("\n[bold]Conformance summary[/bold]")
        console.print(f"  total records: {summary['total']}")
        console.print(f"  by severity:   {summary['by_severity']}")
        console.print(f"  by instruction: {summary['by_instruction']}")
        verdict = (
            "[green]L3 CONFORMANT[/green]"
            if summary["l3_conformant"]
            else "[red]NON-CONFORMANT (BLOCKING raised)[/red]"
        )
        console.print(f"  verdict: {verdict}")
        console.print("\n[bold]State-transition diagram[/bold]")
        # Prefer the actual run path from execution_log.json if exported.
        cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
        exec_log = Path(cfg.compilation_dir) / "execution_log.json"
        log: list[str] = []
        if exec_log.exists():
            log = json.loads(exec_log.read_text(encoding="utf-8")).get(
                "execution_log", []
            )
        console.print(mermaid_state_diagram(log))


@cli.command(name="validate")
@click.argument("input_md", type=click.Path(exists=True, path_type=Path))
@click.argument("output_md", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--level",
    default=None,
    help="Conformance level for the pass gate, e.g. L3 or L3_STRICT. "
    "Defaults to config.",
)
@click.pass_context
def validate(
    ctx: click.Context,
    input_md: Path,
    output_md: Path,
    level: str | None,
) -> None:
    """Standalone verifier: audit OUTPUT_MD against INPUT_MD (no re-translate).

    Passes iff zero BLOCKING diagnostics are raised at the conformance LEVEL.
    """
    cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
    if level:
        cfg.conformance_level = _resolve_level(level)

    report = validate_translation(input_md, output_md, cfg)

    _print_validation(report)


def _print_validation(report: ValidationReport) -> None:
    s = report.summary()
    console.print(
        f"[bold]Validation[/bold] level=[cyan]{report.level.value}[/cyan] "
        f"— BLOCKING={s['blocking']} WARNING={s['warnings']} INFO={s['info']}"
    )
    for d in report.blocking:
        console.print(f"  [red]BLOCKING[/red] [{d.subsystem}] {d.issue}")
    for d in report.warnings:
        console.print(f"  [yellow]WARNING[/yellow] [{d.subsystem}] {d.issue}")
    if report.passed:
        console.print("[green]PASS[/green]: candidate meets the conformance gate.")
        raise SystemExit(0)
    console.print(
        "[red]FAIL[/red]: candidate raised BLOCKING diagnostics; not conformant."
    )
    raise SystemExit(1)


if __name__ == "__main__":
    cli()
