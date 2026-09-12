"""Telemetry helpers for `SafeProcessRunner`."""

from __future__ import annotations

import uuid
from typing import Any


def new_trace_id() -> str:
    return str(uuid.uuid4())


def normalize_status(
    *, event_type: str, returncode: int | None, error_kind: str | None
) -> str:
    if event_type == "timeout" or error_kind == "timeout":
        return "timeout"
    if error_kind == "auth":
        return "blocked"
    if event_type == "error":
        return "error"
    if event_type in {"start", "finish"} and returncode in (None, 0):
        return "ok"
    if returncode is not None and returncode != 0:
        return "error"
    return "error"


def emit_telemetry(
    sink: Any,
    authorizer: Any,
    *,
    event_type: str,
    args: list[str],
    returncode: int | None = None,
    duration_ms: int | None = None,
    error_kind: str | None = None,
    binary_name: str | None = None,
    trace_id: str | None = None,
) -> None:
    if not sink:
        return
    try:
        from providence_runtime.telemetry import RuntimeEvent

        event_name = (
            "governance.process.run"
            if event_type == "finish"
            else f"governance.process.{event_type}"
        )
        sink.emit(
            RuntimeEvent(
                event=event_name,
                command=" ".join(args),
                status=normalize_status(
                    event_type=event_type,
                    returncode=returncode,
                    error_kind=error_kind,
                ),
                trace_id=trace_id or new_trace_id(),
                duration_ms=duration_ms,
                details={
                    "binary": binary_name or authorizer.resolve_binary_name(args[0]),
                    "arg_count": len(args) - 1,
                    "returncode": returncode,
                    "error_kind": error_kind,
                },
            )
        )
    except Exception:
        return
