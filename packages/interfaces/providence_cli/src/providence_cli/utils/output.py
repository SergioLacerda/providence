"""CLI output helpers for global flags and structured output."""

from __future__ import annotations

import json
from typing import Any

import click
import typer


def is_json_mode(ctx: click.Context | typer.Context | None) -> bool:
    """Is Json Mode."""
    if ctx is None or ctx.obj is None:
        return False
    return bool(ctx.obj.get("output_json", False))


def is_verbose_mode(ctx: click.Context | typer.Context | None) -> bool:
    """Is Verbose Mode."""
    if ctx is None or ctx.obj is None:
        return False
    return bool(ctx.obj.get("verbose", False))


def emit_json(payload: dict[str, Any], *, err: bool = False) -> None:
    """Emit Json."""
    typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True), err=err)
