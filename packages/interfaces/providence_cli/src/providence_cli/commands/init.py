"""providence init  initialize an SDD workspace."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from providence_cli.commands.init_bootstrap import (
    _create_runtime_marker_and_telemetry,
    _exit_init_operational_error,
    _normalize_language_or_exit,
    _raise_init_operational_error,
    _run_init_bootstrap,
)
from providence_cli.commands.init_workspace_boundary import (
    _find_blocking_parent_workspace,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.utils.operational_errors import OperationalCliError
from providence_cli.utils.providence_console import format_sdd_line
from providence_core.utils.environment import ProfileContext, SddProfile, write_profile

app = typer.Typer()


def _write_profile_or_exit(
    cwd: Path,
    profile_type: SddProfile,
    effective_name: str,
    language: str | None = None,
) -> ProfileContext:
    try:
        return write_profile(cwd, profile_type, effective_name, language)
    except TypeError as exc:
        if language is None or "positional" not in str(exc):
            raise
        _exit_init_operational_error(
            OperationalCliError(
                headline="Installed providence-core is incompatible with this providence-cli release.",
                cause=exc,
                command="providence init",
                step="profile",
                operation="write profile",
                path=cwd / ".providence" / "profile",
                next_hint="upgrade the standalone tool so providence-cli and providence-core come from the same release, then retry: uv tool upgrade providence-cli",
            )
        )
    except OSError as exc:
        _raise_init_operational_error(
            exc,
            headline="Could not write SDD workspace profile.",
            step="profile",
            operation="write profile",
            path=cwd / ".providence" / "profile",
        )
        raise


def _resolve_default_flags(
    ctx: typer.Context,
    type_: str,
    name: str | None,
    force: bool,
    language: str | None,
) -> tuple[str, str | None, bool, str | None]:
    """Apply --default fallbacks for any options left at their CLI defaults."""
    type_source = ctx.get_parameter_source("type")
    if type_source is not None and type_source.name == "DEFAULT":
        type_ = "client"
    name_source = ctx.get_parameter_source("name")
    if name_source is not None and name_source.name == "DEFAULT":
        name = "local-dev"
    force_source = ctx.get_parameter_source("force")
    if force_source is not None and force_source.name == "DEFAULT":
        force = True
    language_source = ctx.get_parameter_source("language")
    if language_source is not None and language_source.name == "DEFAULT":
        language = "en"
    return type_, name, force, language


@app.callback(invoke_without_command=True)
def init(  # noqa: C901
    ctx: typer.Context,
    type: str = typer.Option(  # noqa: A002
        "client",
        "--type",
        "-t",
        help="Workspace type: master (framework) or client (project instance).",
    ),
    name: str | None = typer.Option(  # noqa: UP045
        None,
        "--name",
        "-n",
        help="Human-readable workspace name (e.g. prod-client, dev-master). Defaults to type.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .providence/profile without prompting (safe in CI).",
    ),
    no_bootstrap: bool = typer.Option(
        False,
        "--no-bootstrap",
        help="Skip governance and skills bootstrap (profile only). Default for --type master.",
    ),
    default: bool = typer.Option(
        False,
        "--default",
        help="One-command bootstrap: defaults --type to 'client', --name to 'local-dev', --language to 'en', and --force, for any of those not explicitly set.",
    ),
    language: str | None = typer.Option(  # noqa: UP045
        None,
        "--language",
        "-l",
        help="Client language preference (en|pt-BR), case-insensitive. "
        "Written to .providence/profile and bridged into compiled language_context.",
    ),
    list_commands: bool = typer.Option(False, "--list", help="List init commands."),
) -> None:
    """Initialize a Providence workspace in the current directory (`.providence/profile`; refuses nested workspaces)."""
    cwd = Path.cwd()

    if list_commands:
        show_command_group("Init", ["--type client", "--type master", "--default"])
        raise typer.Exit(0)

    language = _normalize_language_or_exit(language)
    if default:
        type, name, force, language = _resolve_default_flags(  # noqa: A001
            ctx, type, name, force, language
        )
    parent_workspace = _find_blocking_parent_workspace(cwd)
    if parent_workspace is not None:
        typer.echo(
            f"[SDD] ERROR: A workspace already exists at '{parent_workspace}'.\nNested workspaces are not supported. Run 'providence init' from a directory outside the existing workspace.",
            err=True,
        )
        raise typer.Exit(1)

    profile_path = cwd / ".providence" / "profile"
    overwriting_existing = profile_path.exists() and force

    if profile_path.exists() and not force:
        _show_existing_profile(profile_path, cwd)
        typer.echo(
            "\n[SDD] Workspace already initialized.\nUse --force to overwrite, or edit .providence/profile directly.",
            err=True,
        )
        raise typer.Exit(1)

    normalized_type = type.strip().lower()
    if normalized_type not in ("master", "client"):
        typer.echo("[SDD] ERROR: --type must be 'master' or 'client'.", err=True)
        raise typer.Exit(2)

    profile_type = cast(SddProfile, normalized_type)
    effective_name = name or profile_type
    profile_ctx = _write_profile_or_exit(cwd, profile_type, effective_name, language)

    _create_runtime_marker_and_telemetry(
        cwd,
        profile_ctx=profile_ctx,
        effective_name=effective_name,
        force=force,
        profile_type=profile_type,
    )

    typer.echo(format_sdd_line(f"Workspace initialized at '{cwd}'"))
    typer.echo(f"  type:         {profile_ctx.type}")
    typer.echo(f"  name:         {profile_ctx.name}")
    typer.echo(f"  workspace_id: {profile_ctx.workspace_id}")
    if profile_ctx.language:
        typer.echo(f"  language:     {profile_ctx.language}")
    typer.echo(
        "  core_hash:    (empty  run 'providence governance compile' to populate)"
    )
    typer.echo("  phase_0:      completed")
    run_bootstrap = (profile_type == "client") and not no_bootstrap
    if run_bootstrap:
        typer.echo("")
        typer.echo("[1/4] Workspace profile created ")
        _run_init_bootstrap(cwd, force=force)
    else:
        typer.echo("")
        typer.echo("Next steps:")
        typer.echo("  providence governance generate --full-bootstrap")
        typer.echo("  providence skills --full-bootstrap --regenerate-seeds")
        typer.echo("  providence runtime status")
    if overwriting_existing:
        typer.echo(
            "  [SOFT] profile overwritten: re-run 'providence governance compile' to sync core_hash"
        )


def _show_existing_profile(profile_path: Path, root: Path) -> None:
    """Display the current .providence/profile contents."""
    import configparser

    parser = configparser.ConfigParser()
    parser.read(profile_path)

    typer.echo(f"[SDD] Existing workspace at '{root}':")
    for key, value in parser.items("sdd"):
        typer.echo(f"  {key:15} = {value}")
