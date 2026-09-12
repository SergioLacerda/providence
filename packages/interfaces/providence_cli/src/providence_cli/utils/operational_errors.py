"""Operational CLI error classification and rendering."""

from __future__ import annotations

import errno
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import typer

from providence_cli.utils.output import emit_json, is_json_mode

try:
    from providence_core.utils.process import (
        ProcessAuthorizationError,
        ProcessSpawnError,
        ProcessTimeoutError,
    )
except ImportError:  # pragma: no cover - minimal bootstrap environments

    class ProcessAuthorizationError(Exception):  # type: ignore[no-redef]
        """Raised when process execution is blocked by policy."""

    class ProcessSpawnError(Exception):  # type: ignore[no-redef]
        """Raised when a required process could not be started."""

    class ProcessTimeoutError(Exception):  # type: ignore[no-redef]
        """Raised when a required process exceeds its allotted time."""


_OPERATIONAL_ERRNOS = {
    errno.EACCES,
    errno.EPERM,
    errno.ENOENT,
    errno.ENOTDIR,
    errno.EISDIR,
}
if hasattr(errno, "EBUSY"):
    _OPERATIONAL_ERRNOS.add(errno.EBUSY)
_OPERATIONAL_WINERRORS = {
    5,  # Access is denied.
    32,  # File is being used by another process.
    33,  # File is locked by another process.
}


@dataclass(frozen=True)
class OperationalCliError(Exception):
    """Expected environment/runtime error with CLI presentation context."""

    headline: str
    cause: BaseException | None = None
    command: str | None = None
    step: str | None = None
    operation: str | None = None
    path: str | Path | None = None
    next_hint: str | None = None
    exit_code: int = 1

    def __str__(self) -> str:
        return self.headline


def _path_from_exception(exc: BaseException) -> str | None:
    filename = getattr(exc, "filename", None) or getattr(exc, "filename2", None)
    if filename:
        return str(filename)
    return None


def is_operational_exception(exc: BaseException) -> bool:
    """Return True for expected OS/process failures that should not traceback."""
    if isinstance(exc, OperationalCliError):
        return True
    if isinstance(exc, ProcessAuthorizationError):
        return True
    if isinstance(exc, ProcessSpawnError):
        return True
    if isinstance(exc, ProcessTimeoutError):
        return True
    if isinstance(
        exc,
        (
            PermissionError,
            FileExistsError,
            FileNotFoundError,
            IsADirectoryError,
            NotADirectoryError,
        ),
    ):
        return True
    if isinstance(exc, OSError):
        return (
            getattr(exc, "errno", None) in _OPERATIONAL_ERRNOS
            or getattr(exc, "winerror", None) in _OPERATIONAL_WINERRORS
        )
    return False


def operational_error_from_exception(
    exc: BaseException,
    *,
    headline: str | None = None,
    command: str | None = None,
    step: str | None = None,
    operation: str | None = None,
    path: str | Path | None = None,
    next_hint: str | None = None,
    exit_code: int = 1,
) -> OperationalCliError | None:
    """Convert a classified exception into a renderable operational error."""
    if isinstance(exc, OperationalCliError):
        return exc
    if not is_operational_exception(exc):
        return None

    if headline is None:
        if isinstance(exc, PermissionError):
            headline = "Permission denied while running the CLI command."
        elif isinstance(exc, ProcessAuthorizationError):
            headline = "Command execution was blocked by policy."
        elif isinstance(exc, ProcessSpawnError):
            headline = "Could not start a required process."
        elif isinstance(exc, ProcessTimeoutError):
            headline = "A required process timed out."
        else:
            headline = "The CLI command failed because of an environment error."

    return OperationalCliError(
        headline=headline,
        cause=exc,
        command=command,
        step=step,
        operation=operation,
        path=path or _path_from_exception(exc),
        next_hint=next_hint,
        exit_code=exit_code,
    )


def operational_error_payload(error: OperationalCliError) -> dict[str, Any]:
    """Return the structured output payload for an operational error."""
    payload: dict[str, Any] = {
        "state": "error",
        "error": {
            "type": type(error.cause).__name__
            if error.cause is not None
            else type(error).__name__,
            "message": str(error.cause or error),
        },
        "exit_code": error.exit_code,
    }
    optional_fields = {
        "command": error.command,
        "step": error.step,
        "operation": error.operation,
        "path": str(error.path) if error.path else None,
        "next": error.next_hint,
    }
    payload.update({key: value for key, value in optional_fields.items() if value})
    return payload


def render_operational_error(error: OperationalCliError) -> None:
    """Render a concise, actionable operational error."""
    ctx = click.get_current_context(silent=True)
    if is_json_mode(ctx):
        emit_json(operational_error_payload(error), err=True)
        return
    typer.echo(f"ERROR: {error.headline}", err=True)
    if error.command:
        typer.echo(f"  Command: {error.command}", err=True)
    if error.step:
        typer.echo(f"  Step: {error.step}", err=True)
    if error.operation:
        typer.echo(f"  Operation: {error.operation}", err=True)
    if error.path:
        typer.echo(f"  Path: {error.path}", err=True)
    if error.cause is not None and str(error.cause):
        typer.echo(f"  Cause: {error.cause}", err=True)
    if error.next_hint:
        typer.echo(f"  Next: {error.next_hint}", err=True)
