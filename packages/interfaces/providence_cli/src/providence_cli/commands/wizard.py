"""Wizard command."""

from __future__ import annotations

import tempfile
from pathlib import Path

import click


def _resolve_final_template_dir(
    output_dir: Path | None,
    *,
    staging_root: Path | None = None,
) -> Path:
    if output_dir is not None:
        return output_dir.expanduser().resolve()
    from providence_core.utils.environment import get_sdd_paths

    return get_sdd_paths(generated_root=staging_root)["client_build"] / "final-template"


def _deploy_final_template(
    output_dir: Path | None,
    *,
    staging_root: Path | None = None,
) -> None:
    """Deploy the generated final-template bundle into the project root."""
    from providence_wizard.orchestration.wizard._direct_root_deploy import (
        StaleFinalTemplateError,
        deploy_to_root,
    )

    try:
        result = deploy_to_root(
            target_root=Path.cwd(),
            final_template_dir=_resolve_final_template_dir(
                output_dir, staging_root=staging_root
            ),
        )
    except StaleFinalTemplateError as err:
        click.echo(f"ERROR: {err}")
        raise click.exceptions.Exit(1) from err
    if result.skipped:
        click.echo(
            "deploy...WARN "
            f"created={len(result.created)} updated={len(result.updated)} "
            f"unchanged={len(result.unchanged)} skipped={len(result.skipped)}"
        )
        return
    click.echo(
        "deploy...OK "
        f"created={len(result.created)} updated={len(result.updated)} "
        f"unchanged={len(result.unchanged)}"
    )


def _show_wizard_usage() -> None:
    """Print the public wizard command surface."""
    click.echo("Wizard usage:")
    click.echo(
        "  providence wizard                 install complete governance and agents"
    )
    click.echo("  providence wizard --list          show wizard options")
    click.echo("")
    click.echo("Options:")
    click.echo(
        "  --from-file PATH           use a custom mandates/guidelines JSON file"
    )
    click.echo(
        "  --output-dir PATH          write the final template to another directory"
    )
    click.echo(
        "  --non-interactive          reuse saved preferences or canonical defaults"
    )
    click.echo("  --debug                    show full verbose wizard output")


def _run_wizard(
    output_dir: Path | None,
    from_file: Path | None,
    non_interactive: bool,
    debug: bool = False,
    only_template: bool = False,
) -> None:
    """Run the wizard with the shared public invocation path."""
    from providence_cli.utils.profile import enforce_profile_policy

    enforce_profile_policy("wizard", click.get_current_context(silent=True))

    try:
        from providence_wizard.contracts import WizardInvocation, run_wizard
    except ImportError as err:
        click.echo("ERROR: providence-wizard not installed")
        click.echo("Run: providence setup run")
        raise click.exceptions.Exit(1) from err

    resolved_output = output_dir.expanduser().resolve() if output_dir else None
    resolved_custom_governance_path = (
        from_file.expanduser().resolve() if from_file else None
    )

    temporary_staging = None
    staging_root: Path | None = None
    if output_dir is None and not only_template:
        temporary_staging = tempfile.TemporaryDirectory(prefix="providence-wizard-")
        staging_root = Path(temporary_staging.name)

    try:
        try:
            result = run_wizard(
                WizardInvocation(
                    project_root=Path.cwd(),
                    output_path=resolved_output,
                    non_interactive=non_interactive,
                    custom_governance_path=resolved_custom_governance_path,
                    debug=debug,
                    staging_root=staging_root,
                )
            )
            if not result.success:
                raise click.exceptions.Exit(1)
            if not only_template:
                _deploy_final_template(
                    resolved_output,
                    staging_root=staging_root,
                )
        except RuntimeError as err:
            message = str(err)
            if "SDD Project root not found" in message:
                click.echo(
                    "ERROR: No SDD project context found in the current directory."
                )
                click.echo(
                    "Run from your project root (where you want .providence/ to be created)."
                )
                click.echo("Example:")
                click.echo("  mkdir my-project && cd my-project")
                click.echo("  providence wizard")
                raise click.exceptions.Exit(1) from err
            raise
    finally:
        if temporary_staging is not None:
            temporary_staging.cleanup()


@click.command(
    name="wizard",
    help="Install complete Providence governance and agent bootstrap files.",
    context_settings={"allow_extra_args": True},
)
@click.option("--list", "list_options", is_flag=True, help="List wizard options.")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Directory for the final generated project template. "
        "Direct deployment uses private temporary staging; template-only defaults to ./generated/client/build/final-template/."
    ),
)
@click.option(
    "--from-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to a custom mandates/guidelines JSON file (Scenario B).",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Resolve preferences/agent selection without prompting.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Show full verbose wizard output (default: quiet macro summary).",
)
@click.pass_context
def app(
    ctx: click.Context,
    list_options: bool,
    output_dir: Path | None,
    from_file: Path | None,
    non_interactive: bool,
    debug: bool,
) -> None:
    """Install complete Providence governance and agent bootstrap files."""
    if list_options:
        _show_wizard_usage()
        raise click.exceptions.Exit(0)
    args = tuple(ctx.args)
    if args and args != ("run",):
        click.echo(f"ERROR: Unknown wizard argument: {' '.join(args)}")
        click.echo("Run: providence wizard --list")
        raise click.exceptions.Exit(2)
    _run_wizard(output_dir, from_file, non_interactive, debug)
