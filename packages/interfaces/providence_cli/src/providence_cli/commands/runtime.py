"""providence runtime  workspace runtime state commands."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import typer

from providence_cli.commands._runtime_command_support import (
    do_update_cache as _do_update_cache_impl,
)
from providence_cli.commands._runtime_command_support import (
    format_diagnostic_block as _format_diagnostic_block_impl,
)
from providence_cli.commands._runtime_command_support import (
    render_status_output as _render_status_output_impl,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.runtime_handler import (
    _emit_runtime_status,  # noqa: F401  patchable by tests
    _normalize_report,
    _read_profile,
    _show_ask_confidence,  # noqa: F401  patchable by tests
)
from providence_cli.services.runtime_handler_status import (
    _check_cache_staleness,
    _footer_drift_status,
)
from providence_cli.utils.output import emit_json, is_json_mode, is_verbose_mode
from providence_cli.utils.providence_authority import (
    PathPolicyViolation,
    enforce_path_policy,
    profile_active_path,
    resolve_workspace_root,
)

logger = logging.getLogger(__name__)

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List runtime commands."),
) -> None:
    """Workspace runtime operations."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Runtime", ["status"])
        raise typer.Exit(0)


@app.command()
def status(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full layer-by-layer breakdown."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip cache and run fresh validation."
    ),
    update_cache: bool = typer.Option(
        False,
        "--update-cache",
        help="Print M003 compliance quiz and refresh .providence-cache.md.",
    ),
) -> None:
    """Show current workspace governance state (AHP + GAP + runtime drift)."""

    root = resolve_workspace_root()
    try:
        root = enforce_path_policy(root, workspace_root=root, mode="normal")
    except PathPolicyViolation as exc:
        typer.echo(
            f"[SDD] ERROR: workspace path rejected  {exc.reason}\n  Hint: {exc.hint}",
            err=True,
        )
        raise typer.Exit(2) from exc

    if update_cache:
        _do_update_cache(root)
        raise typer.Exit(0)

    try:
        from providence_runtime import format_governance_footer

        from providence_core.governance.handshake import AgentHandshakeProtocol
    except ImportError as exc:
        typer.echo(f"ERROR: providence_core not installed  {exc}", err=True)
        raise typer.Exit(2) from exc

    effective_verbose = bool(verbose or is_verbose_mode(ctx))
    output_json = is_json_mode(ctx)

    output_mode: Literal["silent", "compact", "verbose"] = (
        "verbose" if effective_verbose else "compact"
    )

    if effective_verbose and not output_json:
        cache_file = root / ".providence" / "runtime" / "governance-state.json"
        typer.echo(_format_diagnostic_block(root, cache_file=cache_file))
        typer.echo("")

    ahp = AgentHandshakeProtocol(project_root=root)
    state, report = ahp.validate(output_mode=output_mode, force_recheck=force)

    _EXIT_CODES = {
        "HEALTHY": 0,
        "PARTIAL": 0,
        "NOT_INITIALIZED": 1,
        "MISCONFIGURED": 2,
        "NOT_CONNECTED": 3,
    }
    code = _EXIT_CODES.get(state, 1)

    workspace_profile = _read_profile(root)
    current_profile = workspace_profile
    if isinstance(ctx.obj, dict):
        current_profile = str(
            ctx.obj.get("profile", workspace_profile) or workspace_profile
        )

    try:
        drift_info = _emit_runtime_status(
            root=root,
            ahp_state=state,
            workspace_profile=workspace_profile,
            current_profile=current_profile,
        )
    except ImportError as exc:
        typer.echo(f"ERROR: providence_runtime not installed  {exc}", err=True)
        raise typer.Exit(2) from exc

    governance_footer = format_governance_footer(
        drift=_footer_drift_status(drift_info),
        governance=state.lower(),
        profile=ahp.skill_profile,
    )

    _render_status_output(
        ahp=ahp,
        state=state,
        report=report,
        code=code,
        drift_info=drift_info,
        governance_footer=governance_footer,
        cache_staleness=_check_cache_staleness(root),
        ask_confidence=_show_ask_confidence(root, emit=not output_json),
        output_json=output_json,
        output_mode=output_mode,
    )

    if code != 0:
        raise typer.Exit(code)


def _do_update_cache(root: Path) -> None:
    _do_update_cache_impl(root)


def _format_diagnostic_block(root: Path, *, cache_file: Path) -> str:
    return _format_diagnostic_block_impl(
        root,
        cache_file=cache_file,
        profile_active_path=profile_active_path,
        read_profile=_read_profile,
    )


def _render_status_output(
    *,
    ahp: Any,
    state: str,
    report: Any,
    code: int,
    drift_info: dict[str, Any],
    governance_footer: str,
    cache_staleness: dict[str, Any],
    ask_confidence: dict[str, Any] | None,
    output_json: bool,
    output_mode: str,
) -> None:
    _render_status_output_impl(
        ahp=ahp,
        state=state,
        report=report,
        code=code,
        drift_info=drift_info,
        governance_footer=governance_footer,
        cache_staleness=cache_staleness,
        ask_confidence=ask_confidence,
        output_json=output_json,
        output_mode=output_mode,
        normalize_report=_normalize_report,
        emit_json_fn=emit_json,
    )
