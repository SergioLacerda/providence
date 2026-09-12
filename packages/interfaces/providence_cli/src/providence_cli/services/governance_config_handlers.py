"""Configuration-oriented governance handlers (load)."""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console

from providence_cli.services._governance_config_support import render_summary_table
from providence_cli.services.governance_payloads import (
    build_governance_load_data,
    governance_error,
    governance_ok,
)
from providence_cli.utils.output import emit_json


def run_governance_load(
    *,
    path: str,
    output_json: bool,
    console: Console,
    validate_path: Any,
    load_config: Any,
    get_summary: Any,
) -> None:
    """Execute governance load flow with JSON/text output modes."""
    if not validate_path(path):
        if output_json:
            data = build_governance_load_data(path=path, summary=None, exit_code=1)
            payload = governance_error(
                "governance load",
                data,
                code="invalid_governance_path",
                message=f"Invalid governance path: {path}",
            )
            emit_json(payload, err=True)
        else:
            console.print(f"[red]ERROR: Invalid governance path: {path}[/red]")
        raise typer.Exit(1)

    config = load_config(path)
    summary = get_summary(path, config=config)

    if output_json:
        data = build_governance_load_data(path=path, summary=summary, exit_code=0)
        payload = governance_ok("governance load", data)
        emit_json(payload)
        return
    render_summary_table(console=console, summary=summary)


def run_governance_load_cmd(*, path: str, output_json: bool, console: Any) -> None:
    """Convenience wrapper for run_governance_load with default dependency injection."""
    from rich.panel import Panel

    from providence_cli.utils.loader import (
        get_governance_summary,
        load_governance_config,
        validate_governance_path,
    )

    if not output_json:
        console.print(
            Panel(
                f"[bold cyan]Governance Configuration Loaded[/bold cyan]\n{path}",
                border_style="cyan",
            )
        )
    run_governance_load(
        path=path,
        output_json=output_json,
        console=console,
        validate_path=validate_governance_path,
        load_config=load_governance_config,
        get_summary=get_governance_summary,
    )
