"""Pure event reading, parsing, and filtering functions for telemetry commands."""

from __future__ import annotations

import contextlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(stripped))
    return events


def _event_ts(event: dict[str, Any]) -> str:
    for key in ("end_ts", "start_ts", "ts", "timestamp"):
        value = str(event.get(key, "")).strip()
        if value:
            return value
    return ""


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def filter_events(
    events: list[dict[str, Any]],
    *,
    event_type: str | None = None,
    status_filter: str | None = None,
    level: str | None = None,
    trace_id: str | None = None,
    work_item: str | None = None,
    phase_id: str | None = None,
    latency_domain: str | None = None,
    path_id: str | None = None,
) -> list[dict[str, Any]]:
    """Apply field-equality filters to an events list (all filters are AND)."""
    if event_type:
        events = [
            e for e in events if str(e.get("event", "")).lower() == event_type.lower()
        ]
    if status_filter:
        events = [
            e
            for e in events
            if str(e.get("status", "")).lower() == status_filter.lower()
        ]
    if level:
        events = [e for e in events if str(e.get("level", "")).upper() == level.upper()]
    if trace_id:
        events = [e for e in events if str(e.get("trace_id", "")) == trace_id]
    if work_item:
        events = [
            e
            for e in events
            if str(e.get("work_item_id", "")).lower() == work_item.lower()
        ]
    if phase_id:
        events = [
            e
            for e in events
            if str(e.get("details", {}).get("phase_id", "")) == phase_id
        ]
    if latency_domain:
        events = [
            e
            for e in events
            if str(e.get("details", {}).get("latency_domain", "")) == latency_domain
        ]
    if path_id:
        events = [e for e in events if str(e.get("path_id", "")) == path_id]
    return events


def apply_time_filter(
    events: list[dict[str, Any]],
    since_str: str | None,
    until_str: str | None,
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Apply since/until time filters.

    Returns (filtered_events, since_error, until_error) where each error is the
    invalid input string if parsing failed, or None if the filter was valid/absent.
    """
    if since_str:
        since_dt = _parse_ts(since_str)
        if since_dt is None:
            return events, since_str, None
        events = [
            e
            for e in events
            if (ts := _event_ts(e))
            and (dt := _parse_ts(ts)) is not None
            and dt >= since_dt
        ]

    if until_str:
        until_dt = _parse_ts(until_str)
        if until_dt is None:
            return events, None, until_str
        events = [
            e
            for e in events
            if (ts := _event_ts(e))
            and (dt := _parse_ts(ts)) is not None
            and dt <= until_dt
        ]

    return events, None, None


def build_status_data(path: Path) -> dict[str, Any]:
    """Build the data payload for `providence telemetry status` (JSON and text modes)."""
    events = _read_events(path)

    if not events:
        hint = (
            None
            if path.exists()
            else "run `providence telemetry init` to create the sink"
        )
        data: dict[str, Any] = {
            "events_file": str(path),
            "total_events": 0,
            "errors": 0,
            "first_event": None,
            "last_event": None,
            "events_by_type": {},
        }
        if hint:
            data["hint"] = hint
        return data

    type_counts: Counter[str] = Counter(str(e.get("event", "unknown")) for e in events)
    error_statuses = {"error", "failed", "failure"}
    errors = sum(
        1 for e in events if str(e.get("status", "")).lower() in error_statuses
    )

    timestamps = [ts for e in events if (ts := _event_ts(e))]
    first_ts = min(timestamps) if timestamps else ""
    last_ts = max(timestamps) if timestamps else ""

    return {
        "events_file": str(path),
        "total_events": len(events),
        "errors": errors,
        "first_event": first_ts,
        "last_event": last_ts,
        "events_by_type": dict(type_counts),
    }


def build_init_result(path: Path) -> dict[str, Any]:
    """Create or validate the telemetry JSONL sink; return a result dict.

    Keys: `created` (bool), `valid` (bool), `invalid_line` (int | None).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
        return {"created": True, "valid": True, "invalid_line": None}

    invalid_line: int | None = None
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
            except json.JSONDecodeError:
                invalid_line = lineno
                break

    return {
        "created": False,
        "valid": invalid_line is None,
        "invalid_line": invalid_line,
    }
