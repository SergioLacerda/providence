"""Read-only preflight explanation handler (`providence governance preflight --dry-run`).

Unlike `governance validate`, this command never exits non-zero: it exists to
explain, before a real run, which checks would pass or fail and which mandate
each one enforces. It performs no writes and mutates no state.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from providence_cli.services._governance_config_support import collect_validation_state
from providence_cli.services.governance_payloads import governance_ok
from providence_cli.utils.output import emit_json

# Mandate each read-only check enforces, per docs/../mandates/mandates.md.
CHECK_MANDATE_MAP: dict[str, str] = {
    "Structure validation": "M001",
    "Files accessible": "M003",
    "Fingerprints valid": "M008",
    "No conflicts": "M016",
    "Artifact consistency": "M008",
    "Active handshake (M015)": "M015",
    "Runtime preflight": "M010",
    "Root-seed drift": "M019",
}


def _annotate_checks(check_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**item, "mandate": CHECK_MANDATE_MAP.get(str(item["check"]), "")}
        for item in check_payload
    ]


def run_governance_preflight_cmd(
    *,
    path: str,
    output_json: bool,
    console: Console,
) -> None:
    """Explain, without gating or mutating anything, whether checks would pass."""
    from rich.panel import Panel

    from providence_cli.services.governance_artifact_handlers import (
        check_artifact_consistency,
    )
    from providence_cli.services.governance_config_reader import (
        check_files_accessible,
        check_fingerprints_valid,
        check_no_conflicts,
        check_root_seed_drift,
    )
    from providence_cli.services.runtime_preflight import run_runtime_preflight
    from providence_cli.utils.loader import (
        load_governance_config,
        validate_governance_path,
    )

    state = collect_validation_state(
        path=path,
        skip_handshake=False,
        validate_path_fn=validate_governance_path,
        load_config_fn=load_governance_config,
        check_files_accessible_fn=check_files_accessible,
        check_fingerprints_valid_fn=check_fingerprints_valid,
        check_no_conflicts_fn=check_no_conflicts,
        check_artifact_consistency_fn=check_artifact_consistency,
        run_runtime_preflight_fn=run_runtime_preflight,
        check_root_seed_drift_fn=check_root_seed_drift,
    )
    annotated_checks = _annotate_checks(state["check_payload"])

    if output_json:
        payload = governance_ok(
            "governance preflight",
            {
                "dry_run": True,
                "would_pass": state["all_passed"],
                "checks": annotated_checks,
                "preflight_reason": state["preflight"].reason,
                "consistency_reason": state["consistency_reason"],
                "root_seed_drift_reason": state["root_seed_drift_reason"],
            },
        )
        emit_json(payload)
        return

    console.print(
        Panel(
            f"[bold cyan]Preflight (dry run  nothing executed)[/bold cyan]\n{path}",
            border_style="cyan",
        )
    )
    table = Table(title="Preflight Checks", show_header=True, header_style="bold")
    table.add_column("Check", style="cyan")
    table.add_column("Mandate", style="magenta")
    table.add_column("Would Pass", style="green")
    for item in annotated_checks:
        status = "[green]PASS[/green]" if item["passed"] else "[red]FAIL[/red]"
        table.add_row(str(item["check"]), item["mandate"] or "-", status)
    console.print(table)

    if state["all_passed"]:
        console.print("[green]Dry run: all checks would pass[/green]")
    else:
        console.print(
            "[yellow]Dry run: one or more checks would fail  "
            "no action taken, run 'providence governance validate' for the enforcing gate[/yellow]"
        )
