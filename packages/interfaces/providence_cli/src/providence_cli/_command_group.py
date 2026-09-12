"""Lazy command group machinery for the SDD CLI entrypoint.

Provides the command registry (`CommandSpec`, `COMMAND_SPECS`) and the
`LazyCommandGroup` Click group that imports each subcommand module on demand,
keeping `sdd --help` available even when optional command dependencies are not
installed yet (for example during minimal bootstrap in CI).
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast

import click
import typer
from typer.main import get_command as typer_get_command

from providence_cli._command_specs import (
    _WORKSPACE_REQUIRED_COMMANDS,
    COMMAND_SPECS,
    CommandSpec,
    _build_unavailable_command,
    _requested_top_level_command,
)

__all__ = [
    "COMMAND_SPECS",
    "CommandSpec",
    "LazyCommandGroup",
    "_WORKSPACE_REQUIRED_COMMANDS",
    "_build_unavailable_command",
    "_requested_top_level_command",
    "typer_get_command",
]


class LazyCommandGroup(click.Group):
    """Click group that imports each subcommand module only on demand."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List Commands."""
        del ctx
        return sorted(COMMAND_SPECS.keys())

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get Command."""
        del ctx
        spec = COMMAND_SPECS.get(cmd_name)
        if spec is None:
            return None

        try:
            module = importlib.import_module(spec.module_path)
            module_app = module.app
            if isinstance(module_app, click.Command):
                return module_app
            if not isinstance(module_app, typer.Typer):
                raise TypeError(
                    f"{spec.module_path}.app is not a typer.Typer or click.Command instance"
                )
            return cast(click.Command, typer_get_command(module_app))
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via CLI integration tests.
            return _build_unavailable_command(cmd_name, spec.module_path, exc)

    def invoke(self, ctx: click.Context) -> object:
        """Inject profile context before command execution."""
        requested_command = _requested_top_level_command(ctx)

        if ctx.obj is None:
            if requested_command in _WORKSPACE_REQUIRED_COMMANDS:
                try:
                    from providence_core.utils.environment import (
                        WorkspaceNotInitializedError,
                        resolve_profile,
                    )

                    explicit_profile: str | None = ctx.params.get("profile")
                    profile_ctx = resolve_profile(override=explicit_profile)
                    ctx.obj = profile_ctx.as_dict()
                except WorkspaceNotInitializedError as exc:
                    raise click.UsageError(str(exc)) from exc
            else:
                ctx.obj = {}

        if requested_command in _WORKSPACE_REQUIRED_COMMANDS and isinstance(
            ctx.obj, dict
        ):
            try:
                from providence_core.governance.handshake import AgentHandshakeProtocol

                workspace_root = ctx.obj.get("root")
                ahp = AgentHandshakeProtocol(
                    project_root=Path(workspace_root) if workspace_root else None
                )
                state, report = ahp.validate(output_mode="silent")
                ctx.obj["_ahp"] = {
                    "state": state,
                    "report": report,
                    "valid": ahp.is_handshake_valid(),
                }
            except Exception:
                ctx.obj["_ahp"] = {
                    "state": "UNKNOWN",
                    "report": None,
                    "valid": False,
                }

        from providence_cli.utils.profile import governance_gate

        governance_gate(ctx)
        try:
            return super().invoke(ctx)
        except click.exceptions.Exit as exc:
            raise click.exceptions.Exit(int(exc.exit_code)) from None
        except typer.Exit as exc:
            raise click.exceptions.Exit(exc.exit_code) from None
