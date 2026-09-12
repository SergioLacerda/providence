"""Install  canonical single entrypoint for activating SDD governance."""

from pathlib import Path

import typer

from providence_cli.commands.wizard import _run_wizard as run_wizard_command
from providence_cli.services.command_group_output import show_command_group

app = typer.Typer()


@app.callback(invoke_without_command=True)
def install(
    ctx: typer.Context,
    wizard: bool = typer.Option(
        False,
        "--wizard",
        help="Run the interactive SDD governance wizard.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for the final generated project template. Defaults to ./generated/client/build/final-template/.",
        show_default=False,
    ),
    only_template: bool = typer.Option(
        False,
        "--only-template",
        help=(
            "Generate the final-template bundle only; do not deploy it into "
            "the project root."
        ),
    ),
    from_file: Path | None = typer.Option(
        None,
        "--from-file",
        help="Path to a custom mandates/guidelines JSON file (Scenario B)  validated and used instead of generating a fresh governance set.",
        show_default=False,
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Resolve preferences/agent selection without prompting  reuses an existing wizard-config.json when present, else canonical defaults.",
    ),
    list_commands: bool = typer.Option(False, "--list", help="List install commands."),
) -> None:
    """Install Providence governance (canonical entrypoint)."""
    if ctx.invoked_subcommand is not None:
        return

    if list_commands:
        show_command_group("Install", ["--wizard"])
        raise typer.Exit(0)

    if not wizard:
        if from_file is not None or non_interactive:
            typer.echo("ERROR: --from-file/--non-interactive require --wizard")
            typer.echo("Run: providence install --wizard --from-file <path>")
            raise typer.Exit(1)
        typer.echo("ERROR: no install target specified")
        typer.echo("Run: providence install --wizard")
        raise typer.Exit(1)

    run_wizard_command(
        output_dir=output_dir,
        from_file=from_file,
        non_interactive=non_interactive,
        only_template=only_template,
    )
