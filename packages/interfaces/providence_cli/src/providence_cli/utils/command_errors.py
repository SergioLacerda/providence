"""Centralized command error handling for Typer commands."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

import click
import typer

from providence_cli.utils.output import emit_json, is_json_mode


def handle_cli_errors(  # noqa: C901
    command_name: str,
    *,
    next_hint: str | None = None,
    error_prefix: str = "ERROR",
    exit_code: int = 1,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap command functions with consistent error formatting.

    `typer.Exit` is always re-raised untouched.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:  # noqa: C901
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except typer.Exit:
                raise
            except Exception as exc:
                ctx: click.Context | typer.Context | None = kwargs.get("ctx")
                if ctx is None:
                    for arg in args:
                        if isinstance(arg, typer.Context):
                            ctx = arg
                            break
                if ctx is None:
                    ctx = click.get_current_context(silent=True)
                if is_json_mode(ctx):
                    payload: dict[str, Any] = {
                        "status": "error",
                        "command": command_name,
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                        "exit_code": exit_code,
                    }
                    if next_hint:
                        payload["next"] = next_hint
                    emit_json(payload, err=True)
                else:
                    typer.echo(f"{error_prefix}: {str(exc)}", err=True)
                    if next_hint:
                        typer.echo(f"  Next: {next_hint}", err=True)
                raise typer.Exit(exit_code) from exc

        return wrapper

    return decorator
