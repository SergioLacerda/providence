"""Registry-oriented governance handlers."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from providence_cli.services.governance_payloads import (
    build_governance_reconcile_data,
    governance_error,
    governance_ok,
)
from providence_cli.services.registry_reconciliation import (
    ReconciliationError,
    reconcile_registries,
)
from providence_cli.utils.output import emit_json


def run_reconcile_registries(
    *,
    ws_root: Path,
    check: bool,
    json_output: bool,
    console: Console,
) -> None:
    """Execute governance registry reconciliation in check/apply modes."""
    try:
        summary = reconcile_registries(ws_root, check_only=check)
    except ReconciliationError as exc:
        if json_output:
            data = build_governance_reconcile_data(
                mode="check" if check else "apply",
                summary={},
                exit_code=1,
            )
            payload = governance_error(
                "governance reconcile-registries",
                data,
                code="reconciliation_error",
                message=str(exc),
            )
            emit_json(payload, err=True)
        else:
            console.print(f"[red]ERROR: {exc}[/red]")
        raise typer.Exit(1) from exc

    data = build_governance_reconcile_data(
        mode="check" if check else "apply",
        summary=summary.as_json(),
        exit_code=1 if (check and summary.drift_detected) else 0,
    )
    if check and summary.drift_detected:
        payload = governance_error(
            "governance reconcile-registries",
            data,
            code="registry_drift_detected",
            message="registry drift detected in check mode",
        )
    else:
        payload = governance_ok("governance reconcile-registries", data)

    if json_output:
        if check and summary.drift_detected:
            emit_json(payload, err=True)
            raise typer.Exit(1)
        emit_json(payload)
        return

    commands = summary.commands
    skills = summary.skills
    if check and summary.drift_detected:
        console.print("[red]Registry drift detected[/red]")
    else:
        console.print("[green]Registry reconciliation completed[/green]")
    console.print(
        "Commands: "
        f"added={commands['added']} removed={commands['removed']} unchanged={commands['unchanged']}"
    )
    console.print(
        "Skills: "
        f"added={skills['added']} removed={skills['removed']} unchanged={skills['unchanged']}"
    )
