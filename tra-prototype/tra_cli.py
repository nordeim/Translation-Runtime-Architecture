"""TRA prototype CLI (Phase 0.1.5 skeleton).

Subcommands:
  translate    Run the TRA pipeline on a Markdown file (Phase 2+; stubbed).
  cache-clear  Invalidate the deterministic cache (CACHE_STRATEGY.md).
  audit        Summarize an audit_trace.jsonl (EVIDENCE_SCHEMA.md).
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from tra.cache import TranslationCache
from tra.config import BootstrapConfig
from tra.diagnostics import AuditTrail

console = Console()


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
@click.pass_context
def translate(
    ctx: click.Context,
    input_md: Path,
    lang: str | None,
    level: str | None,
    output: Path | None,
) -> None:
    """Translate INPUT_MD through the full TRA pipeline."""
    cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
    if lang:
        cfg.language_pair = lang
    if level:
        cfg.conformance_level = level  # type: ignore[assignment]

    console.print(
        f"[bold]TRA[/bold] bootstrap OK — "
        f"pair=[cyan]{cfg.language_pair}[/cyan] "
        f"level=[cyan]{cfg.conformance_level.value}[/cyan]"
    )

    from tra.kernel import TRAKernel

    kernel = TRAKernel(cfg)
    target = kernel.run(input_md)

    if output is None:
        output = input_md.with_name(f"{input_md.stem}.translated.md")
    output.write_text(target, encoding="utf-8")

    blocking = sum(
        1
        for rec in kernel.audit._buffer
        if rec.flags_raised and "BLOCKING" in rec.flags_raised
    )
    console.print(
        f"[green]Translated[/green] -> [cyan]{output}[/cyan]  "
        f"(audit: {cfg.audit_trace}, "
        f"artifacts: {cfg.compilation_dir})"
    )
    if blocking:
        console.print(
            f"[red]WARNING:[/red] {blocking} BLOCKING flag(s) raised — "
            "review audit_trace.jsonl before publishing."
        )


@cli.command(name="cache-clear")
@click.option("--pattern", default=None, help="Optional key pattern to delete.")
@click.pass_context
def cache_clear(ctx: click.Context, pattern: str | None) -> None:
    """Invalidate cache entries (manual; no TTL)."""
    cfg = BootstrapConfig.from_yaml(ctx.obj["config_path"])
    cache = TranslationCache(cfg.cache_directory, enabled=cfg.cache_enabled)
    cache.invalidate(pattern)
    target = pattern or "ALL"
    console.print(f"[green]Cache invalidated:[/green] {target}")


@cli.command()
@click.argument("trace", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["summary", "json"]),
    default="summary",
)
def audit(trace: Path, fmt: str) -> None:
    """Summarize an audit_trace.jsonl file."""
    trail = AuditTrail(trace)
    records = trail.load()
    if fmt == "json":
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


if __name__ == "__main__":
    cli()
