"""Guards for dev-only external tool dependencies."""

from __future__ import annotations

import sys

import typer

from providence_core.utils.process import check_module_available


def require_dev_module(module: str, *, tool: str | None = None) -> None:
    """Exit with an actionable message if `module` is not importable by sys.executable.

    Raises:
        typer.Exit: if the module cannot be imported.
    """
    if check_module_available(sys.executable, module):
        return

    name = tool or module
    typer.echo(
        f"ERROR: '{name}' is not available in this environment.\n"
        "This command is intended for providence contributors (dev environment).\n"
        "Run 'uv sync --all-groups --extra test' from the providence repo root, "
        "then retry with 'uv run sdd <command>'."
    )
    raise typer.Exit(1)
