"""sdd tools run  execute a manifest or legacy tool script.

Split out of `tools.py` (T11,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path

import click
import typer

from providence_cli.commands._tools_app import _find_repo_root, app
from providence_cli.services.tools_registry import (
    ToolEntry,
    ToolsRegistryError,
    load_tools_registry,
)


@app.command()
def run(
    name: str = typer.Argument(
        ...,
        help="Path to the tool script relative to tools/ (e.g. health/health_check.py)",
    ),
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments to pass to the tool"
    ),
) -> None:
    """Run a tool script using 'uv run'."""
    root = _find_repo_root()
    try:
        registry = load_tools_registry(root)
    except ToolsRegistryError as exc:
        typer.echo(f"Error: invalid tools registry: {exc}", err=True)
        raise click.exceptions.Exit(1) from None

    if registry is not None:
        entry = registry.resolve(name)
        if entry is not None:
            _run_manifest_entry(root, entry, args)
            return

    script_path = _resolve_legacy_script(root, name)

    if not script_path.exists():
        typer.echo(f"Error: tool '{name}' not found at {script_path}", err=True)
        raise click.exceptions.Exit(1)

    _run_command(["uv", "run", str(script_path)], args)


def _resolve_legacy_script(root: Path, name: str) -> Path:
    script_path = root / "tools" / name

    if not script_path.exists() and not name.endswith(".py"):
        # Try adding .py extension if missing
        script_path = root / "tools" / f"{name}.py"
    return script_path


def _run_manifest_entry(root: Path, entry: ToolEntry, args: list[str] | None) -> None:
    if not _manifest_entry_can_run(entry):
        message = (
            f"Error: tool '{entry.id}' is not runnable from manifest "
            f"(visibility: {entry.visibility}, status: {entry.status})"
        )
        if entry.replacement:
            message = f"{message}; replacement: {entry.replacement}"
        typer.echo(message, err=True)
        raise click.exceptions.Exit(1)

    target = root / entry.path
    if not target.exists():
        typer.echo(f"Error: tool '{entry.id}' not found at {target}", err=True)
        raise click.exceptions.Exit(1)

    if entry.runner == "uv-python":
        _run_command(["uv", "run", str(target)], args)
        return

    if entry.runner == "python-module" and entry.module:
        _run_command(["uv", "run", "python", "-m", entry.module], args)
        return

    typer.echo(
        f"Error: runner '{entry.runner}' is not directly executable for tool '{entry.id}'",
        err=True,
    )
    raise click.exceptions.Exit(1)


def _manifest_entry_can_run(entry: ToolEntry) -> bool:
    if entry.visibility == "public" and entry.status in {"active", "experimental"}:
        return True
    return entry.allow_direct_run


def _run_command(cmd: list[str], args: list[str] | None) -> None:
    from providence_core.utils.process import (
        ProcessAuthorizationError,
        ProcessSpawnError,
        SafeProcessRunner,
    )

    if args:
        cmd.extend(args)

    typer.echo(f"Running: {' '.join(cmd)}")
    try:
        # Stream tool output directly to the terminal/CI logs for debuggability.
        result = SafeProcessRunner().run(cmd, check=False, capture_output=False)
        raise click.exceptions.Exit(result.returncode)
    except ProcessAuthorizationError as exc:
        typer.echo(f"Error: execution blocked by policy: {exc}", err=True)
        raise click.exceptions.Exit(2) from None
    except ProcessSpawnError:
        typer.echo(
            "Error: 'uv' not found in path. Please install uv (https://github.com/astral-sh/uv).",
            err=True,
        )
        raise click.exceptions.Exit(127) from None
