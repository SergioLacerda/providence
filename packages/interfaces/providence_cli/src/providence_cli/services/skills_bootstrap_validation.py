"""Governance validation and adapter error handling for skills bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from providence_cli.services._skills_resolver_support import emit_bootstrap_error
from providence_cli.utils.loader import load_governance_config, validate_governance_path


def validate_and_load_governance(
    compiled_path: Path, *, output_json: bool, emit_fn: Callable[..., None]
) -> dict[str, Any]:
    """Validate governance path and load config; raises typer.Exit(1) on failure."""
    if not validate_governance_path(str(compiled_path)):
        message = (
            "Missing/invalid governance artifacts at .providence/compiled. "
            "Run step 2 first: providence governance generate --full-bootstrap"
        )
        if output_json:
            emit_bootstrap_error(
                output_json=output_json,
                emit_fn=emit_fn,
                error_code="missing_governance_artifacts",
                reason=message,
                error_type="ValueError",
                error_message=message,
            )
        else:
            typer.echo(f"ERROR: {message}", err=True)
        raise typer.Exit(1)
    config = load_governance_config(str(compiled_path))
    items = config.get("items", []) if isinstance(config, dict) else []
    if not isinstance(items, list) or len(items) == 0:
        message = (
            "No governance items found in .providence/compiled. "
            "Run step 2 first: providence governance generate --full-bootstrap"
        )
        if output_json:
            emit_bootstrap_error(
                output_json=output_json,
                emit_fn=emit_fn,
                error_code="missing_governance_items",
                reason=message,
                error_type="ValueError",
                error_message=message,
            )
        else:
            typer.echo(f"ERROR: {message}", err=True)
        raise typer.Exit(1)
    return config


def handle_adapter_error(
    adapter_error: str, *, output_json: bool, emit_fn: Callable[..., None]
) -> None:
    """Emit adapter error and raise typer.Exit(1)."""
    message = (
        "adapter generation failed during skills full bootstrap. "
        "Fix adapters/templates and retry."
    )
    if output_json:
        emit_bootstrap_error(
            output_json=output_json,
            emit_fn=emit_fn,
            error_code="adapter_generation_failed",
            reason=message,
            error_type="RuntimeError",
            error_message=adapter_error,
            details={"error": adapter_error},
        )
    else:
        typer.echo(f"ERROR: {message}", err=True)
        typer.echo(f"- adapter error: {adapter_error}", err=True)
    raise typer.Exit(1)
