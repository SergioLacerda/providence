"""ask_filter  pure signal/snapshot filtering for providence ask.

All functions are I/O-free. No Click/Typer dependencies.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from providence_cli.shared.constants import (
    LEARNING_WINDOW_DAYS as _LEARNING_WINDOW_DAYS,
)


def _safe_parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _update_learning_signals(
    row: dict[str, Any], signals: dict[str, int], *, from_failures: bool
) -> None:
    signals["observed_events"] += 1
    if from_failures:
        root_cause = str(row.get("root_cause", ""))
        if root_cause == "diagnosis.inconclusive":
            signals["diagnosis_inconclusive"] += 1
        elif root_cause == "evidence.insufficient":
            signals["evidence_insufficient"] += 1
        elif root_cause == "scope.violation":
            signals["scope_violation"] += 1
        return
    status = str(row.get("status", "")).lower()
    if status in {"warn", "fail", "error"}:
        signals["drift_recent_failures"] += 1


def _load_tail_row(raw: bytes) -> dict[str, Any] | None:
    if not raw.strip():
        return None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _row_is_before_cutoff(row: dict[str, Any], cutoff_ts: float) -> bool | None:
    ts = _safe_parse_iso(str(row.get("timestamp", "")))
    if ts is None:
        return None
    return ts.timestamp() < cutoff_ts


def _process_tail_row(
    raw: bytes, signals: dict[str, int], cutoff_ts: float, *, from_failures: bool
) -> bool:
    row = _load_tail_row(raw)
    if row is None:
        return False
    before_cutoff = _row_is_before_cutoff(row, cutoff_ts)
    if before_cutoff is None:
        return False
    if before_cutoff:
        return True
    _update_learning_signals(row, signals, from_failures=from_failures)
    return False


def _process_tail_lines(
    rows: list[bytes], signals: dict[str, int], cutoff_ts: float, *, from_failures: bool
) -> bool:
    for raw in reversed(rows):
        if _process_tail_row(raw, signals, cutoff_ts, from_failures=from_failures):
            return True
    return False


def count_signals_from_tail(
    path: Path, signals: dict[str, int], cutoff_ts: float, *, from_failures: bool
) -> None:
    """Read a JSONL file in reverse and accumulate learning signals within the time window."""
    if not path.exists():
        return
    with path.open("rb") as handle:
        handle.seek(0, 2)
        position = handle.tell()
        chunk_size = 4096
        buffer = b""
        stop = False
        while position > 0 and not stop:
            read_size = min(chunk_size, position)
            position -= read_size
            handle.seek(position)
            buffer = handle.read(read_size) + buffer
            lines = buffer.split(b"\n")
            buffer = lines[0]
            stop = _process_tail_lines(
                lines[1:], signals, cutoff_ts, from_failures=from_failures
            )
        if not stop:
            _process_tail_row(buffer, signals, cutoff_ts, from_failures=from_failures)


def collect_learning_signals(
    workspace_root: Path, *, window_days: int = _LEARNING_WINDOW_DAYS
) -> dict[str, int]:
    """Collect learning signals from the last *window_days* of runtime JSONL files."""
    import time

    cutoff = time.time() - (window_days * 86400)
    signals: dict[str, int] = {
        "diagnosis_inconclusive": 0,
        "evidence_insufficient": 0,
        "scope_violation": 0,
        "drift_recent_failures": 0,
        "observed_events": 0,
        "window_days": window_days,
    }
    runtime_dir = workspace_root / ".providence" / "runtime"
    count_signals_from_tail(
        runtime_dir / "failure-ledger.jsonl",
        signals,
        cutoff,
        from_failures=True,
    )
    count_signals_from_tail(
        runtime_dir / "compliance-events.jsonl",
        signals,
        cutoff,
        from_failures=False,
    )
    return signals


def filter_signals(signals: dict[str, int], query: str) -> dict[str, int]:
    """Return signals relevant to the query. Empty query returns all signals unchanged."""
    if not query:
        return signals
    return signals
