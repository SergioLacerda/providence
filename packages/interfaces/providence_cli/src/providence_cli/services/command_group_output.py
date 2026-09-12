"""Shared presentation helpers for CLI command groups."""

from __future__ import annotations

from collections.abc import Sequence

import typer


def show_command_group(title: str, commands: Sequence[str]) -> None:
    """Print a concise command list for a CLI group."""
    typer.echo(f"{title} commands:")
    for command in commands:
        typer.echo(f"  {command}")
