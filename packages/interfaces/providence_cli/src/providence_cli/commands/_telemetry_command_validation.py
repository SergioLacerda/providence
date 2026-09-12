"""Input validation and abort helpers for telemetry commands."""

from __future__ import annotations

from typing import NoReturn

import typer

from providence_cli.shared.contracts import build_error_result
from providence_cli.utils.output import emit_json


def abort_invalid_time_filter(field: str, value: str, *, output_json: bool) -> None:
    message = f"Invalid --{field} value: {value!r}"
    if output_json:
        emit_json(
            build_error_result(
                "telemetry query",
                code=f"invalid_{field}",
                message=message,
                data={field: value, "exit_code": 1},
            ),
            err=True,
        )
        raise typer.Exit(1)
    typer.echo(message, err=True)
    raise typer.Exit(1)


def abort_invalid_format(fmt: str, *, output_json: bool) -> None:
    message = f"Invalid --format value: {fmt!r}"
    if output_json:
        emit_json(
            build_error_result(
                "telemetry dump",
                code="invalid_format",
                message=message,
                data={"format": fmt, "exit_code": 1},
            ),
            err=True,
        )
    else:
        typer.echo(message, err=True)
    raise typer.Exit(1)


def abort_workspace_resolution(
    command: str, exc: RuntimeError, *, output_json: bool
) -> NoReturn:
    if output_json:
        emit_json(
            build_error_result(
                command,
                code="workspace_resolution_failed",
                message=str(exc),
                data={"exit_code": 1},
            ),
            err=True,
        )
    else:
        typer.echo(f"ERROR: {exc}", err=True)
        typer.echo(
            "Hint: set SDD_TELEMETRY_PATH to an explicit events file path.",
            err=True,
        )
    raise typer.Exit(1) from exc
