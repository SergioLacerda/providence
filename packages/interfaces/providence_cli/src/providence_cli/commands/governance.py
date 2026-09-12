"""Governance management commands."""

import click
import typer
from rich.console import Console
from rich.table import Table as RichTable

from providence_cli.commands._governance_command_registry import (
    register_governance_commands,
)
from providence_cli.services.governance_artifact_handlers import (
    _has_malformed_titles,  # noqa: F401  backward-compat re-export for unit tests
    render_governance_compile_table,  # noqa: F401 - backward-compat symbol for tests/patches
)
from providence_cli.services.governance_command_output import (
    show_governance_command_list,
    show_hook_command_list,
)
from providence_cli.services.governance_compile_handlers import (
    resolve_output_base,  # noqa: F401  backward-compat re-export for unit tests
    run_compile,
)
from providence_cli.services.governance_generate_handlers import (
    generate_seeds,  # noqa: F401  backward-compat re-export for unit tests
    resolve_generate_path,  # noqa: F401  backward-compat re-export for unit tests
    run_generate,
)
from providence_cli.services.governance_hook_handlers import (
    run_governance_hook_disable,
    run_governance_hook_enable,
    run_governance_hook_status,
)
from providence_cli.services.governance_security_handlers import (
    run_keygen,
    run_sign_cmd,
)
from providence_cli.utils.command_errors import handle_cli_errors
from providence_cli.utils.loader import (
    validate_governance_path,  # noqa: F401  backward-compat re-export for unit tests
)
from providence_cli.utils.output import is_json_mode

# Backward-compat re-exports used by tests/patches.
Table = RichTable
__all__ = [
    "render_governance_compile_table",
    "Table",
    "validate_governance_path",
    "_has_malformed_titles",
    "resolve_output_base",
    "generate_seeds",
    "resolve_generate_path",
]

app = typer.Typer(help="Governance management commands", invoke_without_command=True)
hook_app = typer.Typer(
    help="Manage the prompt-submit governance hook (handshake_mode=hook)",
    invoke_without_command=True,
)
console = Console()


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


@app.callback()
def governance_default(
    ctx: typer.Context,
    list_commands: bool = typer.Option(
        False,
        "--list",
        help="List governance commands and exit.",
    ),
) -> None:
    """Show governance commands when invoked without a subcommand."""
    if list_commands or ctx.invoked_subcommand is None:
        show_governance_command_list()
        raise typer.Exit(0)


@hook_app.callback()
def hook_default(ctx: typer.Context) -> None:
    """Show hook commands when invoked without a subcommand."""
    if ctx.invoked_subcommand is None:
        show_hook_command_list()
        raise typer.Exit(0)


@app.command()
@handle_cli_errors(
    command_name="governance compile",
    next_hint="check .providence/source artifacts or run 'providence governance validate'",
)
def compile(
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to compile for: 'master' or 'client'. Defaults to active workspace profile.",
    ),  # noqa: UP045
) -> None:
    """Compile governance artifacts (phase 1 + phase 2) and validate output."""
    run_compile(profile=profile, output_json=_ctx_json(), console=console)


@app.command()
@handle_cli_errors(command_name="governance generate")
def generate(
    output_dir: str | None = typer.Option(
        None, help="Output directory for generated files (defaults to workspace root)"
    ),  # noqa: UP045
    path: str = typer.Option(
        "", help="Path to governance configuration (defaults to .providence/compiled)"
    ),
    full_bootstrap: bool = typer.Option(
        False,
        "--full-bootstrap",
        help="Run onboarding bootstrap sequence: compile, generate, keygen, sign compiled artifacts and sign source governance.",
    ),
    key_id: str = typer.Option(
        "dev-01", help="Key ID used in full bootstrap signing steps."
    ),
    profile: str = typer.Option(
        "client",
        "--profile",
        "-p",
        help="Profile to compile for: 'master' or 'client'. Defaults to 'client'.",
    ),
) -> None:
    """Generate templates and agent seeds."""
    run_generate(
        output_dir=output_dir,
        path=path,
        full_bootstrap=full_bootstrap,
        key_id=key_id,
        profile=profile,
        output_json=_ctx_json(),
        console=console,
        compile_fn=compile,
        keygen_fn=keygen,
        sign_fn=sign,
    )


@app.command()
@handle_cli_errors(command_name="governance keygen")
def keygen(
    key_id: str = typer.Option(
        "auditor-01", help="Key ID for the new key (e.g. dev-01, prod-01)"
    ),
    output_dir: str = typer.Option(
        ".providence/trust", help="Where to save the keys (should be git-ignored)"
    ),
) -> None:
    """Generate a new Ed25519 key pair for signing governance artifacts."""
    run_keygen(key_id=key_id, output_dir=output_dir, console=console)


@app.command()
@handle_cli_errors(command_name="governance sign")
def sign(
    key_id: str = typer.Option("auditor-01", help="Key ID to use for signing"),
    key_path: str | None = typer.Option(None, help="Path to private key (.key file)"),  # noqa: UP045
    compiled_dir: str | None = typer.Option(
        None,
        help="Directory containing artifacts to sign (default: .providence/compiled)",
    ),  # noqa: UP045
    source: bool = typer.Option(
        False,
        "--source",
        help="Sign the source governance file (.providence/source/governance-core.json)",
    ),
) -> None:
    """Sign governance artifacts (JSON) with an Ed25519 private key."""
    run_sign_cmd(
        key_id=key_id,
        key_path=key_path,
        compiled_dir=compiled_dir,
        source=source,
        console=console,
    )


@hook_app.command("status")
def hook_status() -> None:
    """Report whether the prompt-submit governance hook is enabled."""
    run_governance_hook_status(console=console)


@hook_app.command("disable")
def hook_disable() -> None:
    """Disable the prompt-submit governance hook (kill switch)."""
    run_governance_hook_disable(console=console)


@hook_app.command("enable")
def hook_enable() -> None:
    """Re-enable the prompt-submit governance hook."""
    run_governance_hook_enable(console=console)


app.add_typer(hook_app, name="hook")
register_governance_commands(app=app, console=console, ctx_json_fn=_ctx_json)
