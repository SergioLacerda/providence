"""Version command for SDD CLI."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

import typer

from providence_cli.services.command_group_output import show_command_group

app = typer.Typer()


def _resolve_version() -> str:
    try:
        return _pkg_version("providence-cli")
    except PackageNotFoundError:
        return "unknown (not installed as a package)"


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List version commands."),
) -> None:
    """Show version information."""
    if list_commands:
        show_command_group("Version", ["show"])
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(f"SDD Version: {_resolve_version()}")


@app.command()
def show() -> None:
    """Show SDD version."""
    typer.echo(f"SDD Version: {_resolve_version()}")
