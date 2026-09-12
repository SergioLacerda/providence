"""Copilot governance projection build commands (Soft/Standalone profile)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from providence_cli.services.command_group_output import show_command_group
from providence_cli.utils.providence_authority import resolve_workspace_root

app = typer.Typer(
    help="Copilot governance projection generation", invoke_without_command=True
)
console = Console()


@app.callback(invoke_without_command=True)
def copilot_default(ctx: typer.Context) -> None:
    """Copilot governance projection operations."""
    if ctx.invoked_subcommand is None:
        show_command_group("Copilot", ["build"])
        raise typer.Exit(0)


@app.command("build")
def build(
    dest: Path | None = typer.Option(
        None,
        "--dest",
        help="Output directory. Default: <workspace>/dist/copilot-standalone.",
    ),
) -> None:
    """Build the Soft/Standalone Copilot governance projection using real GitHub Copilot conventions."""
    from providence_adapters.copilot import CopilotStandaloneGenerator

    ws_root = resolve_workspace_root()
    result = CopilotStandaloneGenerator().generate_standalone(
        output_dir=ws_root, dest=dest
    )

    if not result.success:
        console.print(
            f"[red]Copilot standalone build failed:[/red] {'; '.join(result.errors)}"
        )
        raise typer.Exit(1)

    console.print(
        f"[green]Copilot standalone config built[/green] "
        f"({len(result.files_written)} files)"
    )
