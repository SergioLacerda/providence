"""Audit event parsing: loading, filtering, basic predicates, scoring helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from providence_cli.services._audit_models import DriftRow

__all__ = ["DriftRow"]


def _parse_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _event_ts(event: dict[str, Any]) -> str:
    for key in ("end_ts", "start_ts", "timestamp"):
        value = str(event.get(key, "")).strip()
        if value:
            return value
    return ""


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    normalized = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _ts_sort_key(ts: str) -> tuple[int, str]:
    if not ts:
        return (0, "")
    normalized = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        return (1, dt.isoformat())
    except ValueError:
        return (1, ts)


def _load_events(events_file: Path) -> list[dict[str, Any]]:
    if not events_file.exists():
        return []
    events: list[dict[str, Any]] = []
    with events_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                events.append(data)
    return events


def _is_ask_event(event: dict[str, Any]) -> bool:
    command = str(event.get("command", "")).strip()
    if command == "ask":
        return True
    event_name = str(event.get("event", "")).strip()
    return event_name.startswith("governance.ask")


def _is_ask_invocation(event: dict[str, Any]) -> bool:
    """True only for parent ``governance.ask`` events (one per ``providence ask`` run).

    Excludes ``governance.ask.phase`` latency sub-events and non-LLM events
    (compile, lifecycle), which never carry token telemetry. Token metrics must
    use this denominator; drift-rate denominators keep ``_is_ask_event``.
    """
    return str(event.get("event", "")).strip() == "governance.ask"


def _is_ask_phase_event(event: dict[str, Any]) -> bool:
    """True only for ``governance.ask.phase`` sub-events.

    A single drifted ``providence ask`` invocation inherits ``drift_detected`` from its
    parent onto every phase sub-event (~6 per invocation), inflating drift
    *counts* ~7x if phase events are counted alongside their parent. Drift-rate
    numerators must exclude these; drift-rate denominators keep counting them
    (via ``_is_ask_event``), matching the windowed correlation shape.
    """
    return str(event.get("event", "")).strip() == "governance.ask.phase"


def _is_drift_event(event: dict[str, Any]) -> bool:
    if str(event.get("event", "")).strip() == "runtime.drift.detected":
        return True
    details = event.get("details", {})
    if isinstance(details, dict):
        if bool(details.get("drift_detected")):
            return True
        drift_type = str(details.get("drift_type", "")).strip().lower()
        if drift_type and drift_type != "none":
            return True
    return False


def _drift_type(event: dict[str, Any]) -> str:
    details = event.get("details", {})
    if isinstance(details, dict):
        value = str(details.get("drift_type", "")).strip()
        if value:
            return value
    return "missing_drift_type"


def _drift_cause(event: dict[str, Any]) -> str:
    details = event.get("details", {})
    if isinstance(details, dict):
        for key in (
            "drift_cause",
            "reason",
            "remediation_command",
            "degraded_reason",
        ):
            value = str(details.get(key, "")).strip()
            if value:
                return value
    return ""


def _window_events(
    events: list[dict[str, Any]], *, now_utc: datetime, days: int
) -> list[dict[str, Any]]:
    start = now_utc - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for event in events:
        dt = _parse_ts(_event_ts(event))
        if dt is None:
            continue
        if dt >= start:
            out.append(event)
    return out


def _token_totals(events: list[dict[str, Any]]) -> tuple[int, int, int]:
    total_in = 0
    total_out = 0
    with_tokens = 0
    for event in events:
        tokens_in = _parse_int(event.get("tokens_input"))
        tokens_out = _parse_int(event.get("tokens_output"))
        if tokens_in is None or tokens_out is None:
            continue
        with_tokens += 1
        total_in += tokens_in
        total_out += tokens_out
    return total_in, total_out, with_tokens
