"""Pure and output-only helpers extracted from commands/runtime.py.

Functions with typer.Exit remain in the command entry point.
ImportError from providence_runtime propagates to the command for typer.Exit handling.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from providence_cli.services._runtime_handler_support import (
    ask_confidence_payload,
    emit_runtime_events,
    read_profile_value,
    runtime_context,
)
from providence_cli.shared.constants import RUNTIME_DIR as _RUNTIME_DIR
from providence_cli.utils.providence_authority import (
    compiled_active_dir,
    profile_active_path,
)
from providence_cli.utils.telemetry_paths import resolve_compliance_events_path

logger = logging.getLogger(__name__)


def _read_workspace_id(root: Path) -> str:
    """Extract workspace_id from .providence/profile, best-effort."""
    return read_profile_value(
        root=root,
        profile_active_path_fn=profile_active_path,
        field="workspace_id",
        fallback="unknown",
    )


def _read_profile(root: Path) -> str:
    """Extract profile type from .providence/profile, best-effort."""
    return read_profile_value(
        root=root,
        profile_active_path_fn=profile_active_path,
        field="type",
        fallback="",
    )


def _normalize_report(report: Any) -> dict[str, Any]:
    """Best-effort conversion of handshake report object to JSON-safe dict."""
    data = dict(report.__dict__) if hasattr(report, "__dict__") else {}
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str | int | float | bool | list | dict) or value is None:
            normalized[key] = value
        elif isinstance(value, Path):
            normalized[key] = value.as_posix()
        else:
            normalized[key] = str(value)
    return normalized


def _show_ask_confidence(
    workspace_root: Path, *, emit: bool = True
) -> dict[str, Any] | None:
    """Display ask_confidence block derived from last_ask in governance-state.json."""
    payload = ask_confidence_payload(workspace_root=Path(workspace_root))
    if payload is None:
        return None

    if emit:
        typer.echo("")
        typer.echo("=== ask_confidence ===")
        typer.echo(f"  last_ask_ts        : {payload['last_ask_ts']}")
        typer.echo(f"  context_source     : {payload['context_source']}")
        typer.echo(f"  fingerprint_used   : {payload['fingerprint_used']}")
        if "trace_id" in payload:
            typer.echo(f"  trace_id           : {payload['trace_id']}")
    return payload


def _emit_runtime_status(
    *,
    root: Path,
    ahp_state: str,
    workspace_profile: str,
    current_profile: str,
    emit_fn: Callable[..., None] = typer.echo,
) -> dict[str, Any]:
    """Load compiled artifact, classify drift, upsert session, emit telemetry.

    All providence_runtime calls are best-effort  a failure here must never crash
    the status command. Raises ImportError if providence_runtime is unavailable (let
    the command handle typer.Exit).
    """
    drift_info: dict[str, Any] = {"detected": False, "type": "none", "reason": ""}

    from providence_runtime import (
        CompiledArtifact,
        DriftDetector,
        GovernanceInjector,
        RuntimeEvent,
        SessionManager,
        SessionState,
        TelemetrySink,
    )

    try:
        context = runtime_context(
            root=root,
            compiled_active_dir_fn=compiled_active_dir,
            read_workspace_id_fn=_read_workspace_id,
            runtime_dir=_RUNTIME_DIR,
        )

        injection = GovernanceInjector().inject_from_path(context["compiled_dir"])
        has_artifact = injection.loaded
        artifact: CompiledArtifact | None = None
        if has_artifact:
            artifact = CompiledArtifact.from_sdd_compiled_dir(
                context["compiled_dir"], profile=workspace_profile
            )

        session_manager = SessionManager(state_dir=context["runtime_dir"])
        # Read the prior session BEFORE upserting the new one  classify()
        # must compare the artifact against the baseline recorded on the
        # *previous* run, not against a session that was just built from
        # (and therefore trivially matches) the current artifact. Upserting
        # first made every classification compare the artifact to itself,
        # so fingerprint/profile drift could never be detected via this
        # path. See DRF-03,
        # `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`.
        previous_session = session_manager.get(
            context["workspace_id"], context["agent_id"], "runtime-status"
        )
        session = SessionState(
            workspace_id=context["workspace_id"],
            agent_id=context["agent_id"],
            work_item_id="runtime-status",
            artifact_fingerprint=injection.artifact_fingerprint,
            schema_version=injection.schema_version,
            policy_set_version=injection.schema_version,
        )

        drift_type = "none"
        drift_detected = False
        if artifact is not None:
            if previous_session is None:
                # First session for this (workspace, agent, work item) key
                # there is no prior baseline to classify against.
                drift_info = {
                    "detected": False,
                    "type": "none",
                    "reason": "first session recorded for this workspace/agent",
                }
            else:
                drift_report = DriftDetector().classify(
                    session=previous_session,
                    artifact=artifact,
                    current_profile=current_profile,
                )
                drift_detected = drift_report.drift_detected
                drift_type = drift_report.drift_type
                if drift_detected:
                    drift_info = {
                        "detected": True,
                        "type": drift_type,
                        "remediation_command": drift_report.remediation_command,
                    }
                    emit_fn(
                        f"\n[runtime] drift detected: {drift_type}"
                        f"    {drift_report.remediation_command}",
                    )
                else:
                    drift_info = {"detected": False, "type": drift_type, "reason": ""}

        session_manager.upsert(session)

        sink = TelemetrySink(
            jsonl_path=resolve_compliance_events_path(workspace_root=root),
            logging_mode="passive",
        )
        emit_runtime_events(
            sink=sink,
            runtime_event_cls=RuntimeEvent,
            trace_id=context["trace_id"],
            workspace_id=context["workspace_id"],
            agent_id=context["agent_id"],
            artifact_fingerprint=injection.artifact_fingerprint,
            schema_version=injection.schema_version,
            ahp_state=ahp_state,
            mandates_loaded=injection.mandates_loaded,
            drift_detected=drift_detected,
            drift_type=drift_type,
            path_id=os.environ.get("SDD_PATH_ID", ""),
        )

    except FileNotFoundError as exc:
        logger.debug("providence_runtime: compiled artifact not found  %s", exc)

    except Exception as exc:  # noqa: BLE001
        logger.debug("providence_runtime: non-critical failure in status emit  %s", exc)

    return drift_info
