"""Profile adapters and helpers for SDD CLI commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import click


@dataclass(frozen=True)
class ProfilePolicy:
    """Defines which CLI operations are permitted for a given profile."""

    profile: str
    # Commands fully available in this profile
    allowed_commands: frozenset[str] = field(default_factory=frozenset)
    # Commands available but with a warning message
    warned_commands: dict[str, str] = field(default_factory=dict)
    # Commands blocked with an actionable error
    blocked_commands: dict[str, str] = field(default_factory=dict)


MasterAdapter = ProfilePolicy(
    profile="master",
    allowed_commands=frozenset(
        {
            "bootstrap",
            "governance",
            "doctor",
            "docs",
            "lint",
            "setup",
            "test",
            "release",
            "runtime",
            "version",
            "ask",
        }
    ),
    warned_commands={
        "wizard": "wizard is primarily a client operation; running in master workspace.",
    },
    blocked_commands={},
)

ClientAdapter = ProfilePolicy(
    profile="client",
    allowed_commands=frozenset(
        {
            "bootstrap",
            "governance",
            "doctor",
            "docs",
            "lint",
            "setup",
            "test",
            "wizard",
            "runtime",
            "version",
            "ask",
        }
    ),
    warned_commands={},
    blocked_commands={
        "release": "release is a master-only operation. Switch to the framework repository.",
    },
)

_ADAPTERS: dict[str, ProfilePolicy] = {
    "master": MasterAdapter,
    "client": ClientAdapter,
}


def get_adapter(profile: str) -> ProfilePolicy:
    """Return the policy adapter for the given profile (defaults to client)."""
    return _ADAPTERS.get(profile, ClientAdapter)


def get_active_profile(ctx: click.Context | None = None) -> str:
    """Resolve active profile from Click context or environment."""
    if ctx is not None and isinstance(ctx.obj, dict):
        return str(ctx.obj.get("profile", "client"))
    try:
        from providence_core.utils.environment import detect_profile

        return detect_profile()
    except Exception:
        return "client"


def enforce_profile_policy(command_name: str, ctx: click.Context | None = None) -> None:
    """Check profile policy for a command; print warnings or raise Exit if blocked.

    Call at the start of command callbacks that should be profile-aware.
    """
    profile = get_active_profile(ctx)
    adapter = get_adapter(profile)

    if command_name in adapter.blocked_commands:
        msg = adapter.blocked_commands[command_name]
        click.echo(
            f"ERROR [{profile}]: command '{command_name}' is not available in this context.",
            err=True,
        )
        click.echo(f"   {msg}", err=True)
        raise click.exceptions.Exit(1)

    if command_name in adapter.warned_commands:
        msg = adapter.warned_commands[command_name]
        click.echo(f"WARN [{profile}]: {msg}")


def profile_context_display(obj: Any) -> str:
    """Format profile context for display in command output."""
    if not isinstance(obj, dict):
        return ""
    profile = obj.get("profile", "client")
    icon = " " if profile == "master" else ""
    return f"{icon} profile={profile}"
