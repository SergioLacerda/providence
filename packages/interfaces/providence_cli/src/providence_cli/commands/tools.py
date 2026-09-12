"""Tools."""

import json
from pathlib import Path

import click
import typer

from providence_cli.commands._tools_app import _find_repo_root, app
from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.tools_registry import (
    ToolEntry,
    ToolsRegistry,
    ToolsRegistryError,
    load_tools_registry,
)

__all__ = ["app", "_find_repo_root", "tools_run"]


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List tool commands."),
) -> None:
    """Developer and maintenance tools."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Tools", ["list", "run"])
        raise typer.Exit(0)


@app.command("list")
def list_tools(
    include_all: bool = typer.Option(
        False, "--all", help="Include every manifest entry."
    ),
    include_internal: bool = typer.Option(
        False, "--include-internal", help="Include internal tools."
    ),
    include_deprecated: bool = typer.Option(
        False, "--include-deprecated", help="Include deprecated tools."
    ),
    include_projects: bool = typer.Option(
        False, "--include-projects", help="Include self-contained tool projects."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """List available developer and maintenance tools."""
    root = _find_repo_root()
    tools_dir = root / "tools"

    if not tools_dir.is_dir():
        typer.echo(f"Error: tools directory not found at {tools_dir}", err=True)
        raise click.exceptions.Exit(1)

    try:
        registry = load_tools_registry(root)
    except ToolsRegistryError as exc:
        typer.echo(f"Error: invalid tools registry: {exc}", err=True)
        raise click.exceptions.Exit(1) from None

    if registry is not None:
        entries = _filter_manifest_entries(
            registry,
            include_all=include_all,
            include_internal=include_internal,
            include_deprecated=include_deprecated,
            include_projects=include_projects,
        )
        if json_output:
            typer.echo(
                json.dumps(
                    {
                        "source": "manifest",
                        "registry_path": str(registry.path.relative_to(root)),
                        "tools": [entry.as_dict() for entry in entries],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        typer.echo("Available tools in tools/registry.yaml:")
        for entry in entries:
            typer.echo(f"  - {_format_manifest_entry(entry)}")
        return

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "source": "legacy",
                    "tools": [
                        {"path": str(script.relative_to(tools_dir))}
                        for script in _legacy_python_scripts(tools_dir)
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    typer.echo("Available tools in tools/:")
    for script in _legacy_python_scripts(tools_dir):
        rel_path = script.relative_to(tools_dir)
        typer.echo(f"  - {rel_path}")


def _legacy_python_scripts(tools_dir: Path) -> list[Path]:
    return sorted(
        script for script in tools_dir.rglob("*.py") if not script.name.startswith("__")
    )


def _filter_manifest_entries(
    registry: ToolsRegistry,
    *,
    include_all: bool,
    include_internal: bool,
    include_deprecated: bool,
    include_projects: bool,
) -> list[ToolEntry]:
    if include_all:
        return list(registry.tools)

    entries = []
    for entry in registry.tools:
        if entry.visibility == "public" and entry.status == "active":
            entries.append(entry)
            continue
        if include_internal and entry.visibility == "internal":
            entries.append(entry)
            continue
        if include_deprecated and (
            entry.visibility == "deprecated" or entry.status == "deprecated"
        ):
            entries.append(entry)
            continue
        if include_projects and entry.visibility == "project":
            entries.append(entry)
    return entries


def _format_manifest_entry(entry: ToolEntry) -> str:
    details = f"{entry.id} ({entry.path}) - {entry.description}"
    labels = []
    if entry.visibility != "public":
        labels.append(entry.visibility)
    if entry.status != "active" and entry.status != entry.visibility:
        labels.append(entry.status)
    if labels:
        details = f"{details} [{' '.join(labels)}]"
    if entry.replacement:
        details = f"{details} replacement: {entry.replacement}"
    return details


# Imported for its @app.command() registration side effect  the `run`
# subcommand lives in tools_run.py (T11 split) but must be imported here so
# lazy command loading (which only imports `providence_cli.commands.tools`) still
# registers it on `app`. Mirrors the existing `_ask_backend/__init__.py`
# pattern for `_ask_cmd_impl`.
from providence_cli.commands import tools_run  # noqa: E402
