"""Support helpers for runtime status/session emission."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def read_profile_value(
    *, root: Path, profile_active_path_fn: Any, field: str, fallback: str
) -> str:
    import configparser

    profile_path = profile_active_path_fn(root)
    if not profile_path.exists():
        return fallback
    try:
        parser = configparser.ConfigParser()
        parser.read(profile_path)
        return parser.get("sdd", field, fallback=fallback)
    except Exception:
        return fallback


def ask_confidence_payload(*, workspace_root: Path) -> dict[str, Any] | None:
    import json

    state_path = workspace_root / ".providence" / "runtime" / "governance-state.json"
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    last_ask = data.get("last_ask")
    if not last_ask:
        return None
    payload = {
        "last_ask_ts": last_ask.get("ts", "n/a"),
        "context_source": last_ask.get("context_source", "n/a"),
        "fingerprint_used": last_ask.get("compiled_fingerprint_used", "n/a"),
    }
    trace_id = last_ask.get("trace_id")
    if trace_id:
        payload["trace_id"] = trace_id[:8]
    return payload


def runtime_context(
    *,
    root: Path,
    compiled_active_dir_fn: Any,
    read_workspace_id_fn: Any,
    runtime_dir: Path,
) -> dict[str, Any]:
    import os
    import uuid

    agent_id = os.environ.get("SDD_AGENT_ID", "unknown")
    trace_id = str(uuid.uuid4())
    compiled_dir = compiled_active_dir_fn(root)
    if not compiled_dir.exists():
        raise FileNotFoundError(f"compiled governance not found at '{compiled_dir}'")
    return {
        "agent_id": agent_id,
        "workspace_id": read_workspace_id_fn(root),
        "trace_id": trace_id,
        "runtime_dir": root / runtime_dir,
        "compiled_dir": compiled_dir,
    }


def emit_runtime_events(
    *,
    sink: Any,
    runtime_event_cls: Any,
    trace_id: str,
    workspace_id: str,
    agent_id: str,
    artifact_fingerprint: str,
    schema_version: str,
    ahp_state: str,
    mandates_loaded: int,
    drift_detected: bool,
    drift_type: str,
    path_id: str,
) -> None:
    sink.emit(
        runtime_event_cls(
            event="runtime.session.start",
            command="runtime status",
            status="ok" if ahp_state in ("HEALTHY", "PARTIAL") else "warn",
            trace_id=trace_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            artifact_fingerprint=artifact_fingerprint,
            schema_version=schema_version,
            decision_source_refs=["ADR-001-runtime-authority-boundary"],
            path_id=path_id,
            details={
                "ahp_state": ahp_state,
                "mandates_loaded": mandates_loaded,
                "drift_detected": drift_detected,
                "drift_type": drift_type,
            },
        )
    )
    if drift_detected:
        sink.emit(
            runtime_event_cls(
                event="runtime.drift.detected",
                command="runtime status",
                status="warn",
                trace_id=trace_id,
                workspace_id=workspace_id,
                agent_id=agent_id,
                artifact_fingerprint=artifact_fingerprint,
                schema_version=schema_version,
                decision_source_refs=[
                    "12.5-anti-drift-strategy",
                    "ADR-001-runtime-authority-boundary",
                ],
                details={"drift_type": drift_type},
            )
        )
