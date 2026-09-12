"""Pure data/IO helpers for analysis workspace mission collection and pruning."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_STATES = ("todo", "pending", "refined", "done")
_DURATION_RE = re.compile(r"^(\d+)(d|h|m)$")


def _analysis_root(ws_root: Path) -> Path:
    return ws_root / ".providence" / "analysis"


def _parse_duration(value: str) -> timedelta | None:
    m = _DURATION_RE.match(value.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "d":
        return timedelta(days=n)
    if unit == "h":
        return timedelta(hours=n)
    return timedelta(minutes=n)


def _collect_missions(analysis_root: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {s: [] for s in _STATES}
    for state in _STATES:
        state_dir = analysis_root / state
        if not state_dir.exists():
            continue
        for p in sorted(state_dir.iterdir()):
            if p.is_file() and p.suffix == ".md":
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                result[state].append(
                    {
                        "mission_id": p.stem,
                        "file": str(p),
                        "date": mtime.date().isoformat(),
                        "state": state,
                    }
                )
    return result


def _collect_expired(done_dir: Path, cutoff: datetime, dry_run: bool) -> list[str]:
    removed: list[str] = []
    if not done_dir.exists():
        return removed
    for p in sorted(done_dir.iterdir()):
        if not p.is_file():
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            removed.append(str(p))
            if not dry_run:
                p.unlink()
    return removed


def _next_action(state: str) -> str:
    actions = {
        "todo": "move to pending when analysis begins",
        "pending": "discovery in progress  awaiting Ranger artifact",
        "refined": "plan ready  awaiting approval gate",
        "done": "mission complete",
    }
    return actions.get(state, "unknown")
