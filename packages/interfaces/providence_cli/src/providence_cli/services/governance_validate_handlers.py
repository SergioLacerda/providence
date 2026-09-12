"""Validation-oriented governance handlers (`providence governance validate`)."""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console

from providence_cli.services._governance_config_support import (
    collect_validation_state,
    emit_validation_outcome,
    normalize_signature_mode,
    render_advisory_table,
    render_validation_table,
)
from providence_cli.services.governance_language_advisories import (
    _build_language_governance_advisories,
    _render_advisory_status,
)
from providence_cli.services.governance_payloads import (
    build_governance_validate_data,
    governance_error,
    governance_ok,
)
from providence_cli.utils.output import emit_json


def run_governance_validate(  # noqa: C901
    *,
    path: str,
    skip_handshake: bool,
    output_json: bool,
    console: Console,
    validate_path: Any,
    load_config: Any,
    check_files_accessible: Any,
    check_fingerprints_valid: Any,
    check_no_conflicts: Any,
    check_artifact_consistency: Any,
    run_runtime_preflight_fn: Any,
    check_root_seed_drift: Any = None,
) -> None:
    """Execute governance validate flow with JSON/text output modes."""
    state = collect_validation_state(
        path=path,
        skip_handshake=skip_handshake,
        validate_path_fn=validate_path,
        load_config_fn=load_config,
        check_files_accessible_fn=check_files_accessible,
        check_fingerprints_valid_fn=check_fingerprints_valid,
        check_no_conflicts_fn=check_no_conflicts,
        check_artifact_consistency_fn=check_artifact_consistency,
        run_runtime_preflight_fn=run_runtime_preflight_fn,
        check_root_seed_drift_fn=check_root_seed_drift,
    )
    advisory_payload = _build_language_governance_advisories(
        path=path, config=state["config"]
    )

    if output_json:
        data = build_governance_validate_data(
            path=path,
            checks=state["check_payload"],
            advisories=advisory_payload,
            preflight={
                "passed": state["preflight_ok"],
                "reason": state["preflight"].reason,
                "details": state["preflight"].details,
            },
            consistency_reason=state["consistency_reason"],
            root_seed_drift_reason=state["root_seed_drift_reason"],
            exit_code=0 if state["all_passed"] else 1,
        )
        if state["all_passed"]:
            payload = governance_ok("governance validate", data)
        else:
            payload = governance_error(
                "governance validate",
                data,
                code="governance_validation_failed",
                message="one or more governance checks failed",
            )
        emit_json(payload, err=not state["all_passed"])
        if not state["all_passed"]:
            raise typer.Exit(1)
        return

    render_validation_table(console=console, check_payload=state["check_payload"])
    if advisory_payload:
        render_advisory_table(
            console=console,
            advisory_payload=advisory_payload,
            render_status_fn=_render_advisory_status,
        )
    emit_validation_outcome(
        console=console,
        all_passed=state["all_passed"],
        handshake_active=state["handshake_active"],
        structure_ok=bool(state["check_payload"][0]["passed"]),
        consistency_ok=state["consistency_ok"],
        consistency_reason=state["consistency_reason"],
        preflight_ok=state["preflight_ok"],
        preflight_reason=state["preflight"].reason,
        root_seed_drift_ok=state["root_seed_drift_ok"],
        root_seed_drift_reason=state["root_seed_drift_reason"],
    )


def run_governance_validate_cmd(
    *,
    path: str,
    signature_mode: str,
    skip_handshake: bool,
    output_json: bool,
    console: Any,
) -> None:
    """Convenience wrapper for run_governance_validate with default dependency injection."""
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

    normalize_signature_mode(signature_mode)
    if not output_json:
        console.print(
            Panel(
                f"[bold cyan]Validating Governance[/bold cyan]\n{path}",
                border_style="cyan",
            )
        )
    run_governance_validate(
        path=path,
        skip_handshake=skip_handshake,
        output_json=output_json,
        console=console,
        validate_path=validate_governance_path,
        load_config=load_governance_config,
        check_files_accessible=check_files_accessible,
        check_fingerprints_valid=check_fingerprints_valid,
        check_no_conflicts=check_no_conflicts,
        check_artifact_consistency=check_artifact_consistency,
        run_runtime_preflight_fn=run_runtime_preflight,
        check_root_seed_drift=check_root_seed_drift,
    )
