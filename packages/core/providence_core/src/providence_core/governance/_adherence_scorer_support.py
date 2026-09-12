"""Support helpers for governance adherence scoring."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def workspace_root_or_none(workspace_root: Path | None) -> Path | None:
    if workspace_root is not None:
        return workspace_root
    try:
        from providence_core.utils.environment import find_workspace_root

        return find_workspace_root()
    except Exception as exc:
        logger.debug("Could not resolve workspace root: %s", exc)
        return None


def read_all_events(
    *, workspace_root: Path | None = None, log_path: Path | None = None
) -> list[dict[str, Any]]:
    from providence_core.governance.compliance_constants import default_log_path

    target = log_path or default_log_path(workspace_root)
    if target is None or not target.exists():
        return []
    try:
        events: list[dict[str, Any]] = []
        for line in target.read_text(encoding="utf-8").splitlines():
            payload = line.strip()
            if not payload:
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
        return events
    except Exception as exc:
        logger.warning("Failed to read all compliance events: %s", exc)
        return []


def get_compiled_fingerprint(workspace_root: Path | None = None) -> str:
    root = workspace_root_or_none(workspace_root)
    if root is None:
        return ""
    artifact = root / ".providence" / "compiled" / "governance-core.json"
    if not artifact.exists():
        return ""
    try:
        data = json.loads(artifact.read_bytes())
        fingerprint = str(data.get("fingerprint", "")).strip()
        if fingerprint:
            return fingerprint
        clean = {
            key: value
            for key, value in data.items()
            if key not in {"_signature", "fingerprint"}
        }
        return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()
    except Exception:
        return ""


def compute_behavioral(
    all_events: list[dict[str, Any]], cutoff: datetime
) -> dict[str, Any]:
    from providence_core.governance.compliance_constants import (
        GOVERNANCE_CHECKED,
        VIOLATION,
    )

    window_events = []
    for event in all_events:
        try:
            stamp = datetime.fromisoformat(event.get("timestamp", event.get("ts", "")))
            if stamp.tzinfo is not None:
                stamp = stamp.astimezone().replace(tzinfo=None)
            if stamp >= cutoff:
                window_events.append(event)
        except (ValueError, TypeError):
            continue
    allows = sum(
        1 for event in window_events if event.get("event") == GOVERNANCE_CHECKED
    )
    warns = sum(
        1
        for event in window_events
        if event.get("event") == VIOLATION
        and (event.get("details") or {}).get("action") == "warn"
    )
    blocks = sum(
        1
        for event in window_events
        if event.get("event") == VIOLATION
        and (event.get("details") or {}).get("action") == "block"
    )
    total = allows + warns + blocks
    ratio = allows / total if total else 1.0
    return {
        "ratio": ratio,
        "score": round(ratio * 50),
        "allows": allows,
        "warns": warns,
        "blocks": blocks,
        "window_events": len(window_events),
    }


def compute_structural(
    resolved_state: Path | None,
    workspace_root: Path | None,
    fingerprint_loader: Callable[[Path | None], str],
) -> dict[str, Any]:
    match = False
    detail = "no_state_file"
    state_data: dict[str, Any] = {}
    if resolved_state is not None and resolved_state.exists():
        try:
            state_data = json.loads(resolved_state.read_text(encoding="utf-8"))
            cached_fp = str(state_data.get("spec_fingerprint", "")).strip()
            if not cached_fp:
                detail = "no_fingerprint_in_state"
            else:
                artifact_fp = fingerprint_loader(workspace_root)
                if not artifact_fp:
                    detail = "no_artifact"
                else:
                    match = cached_fp[:16] == artifact_fp[:16]
                    detail = "match" if match else "drift_detected"
        except Exception as exc:
            detail = f"error: {exc}"
    return {
        "match": match,
        "score": 30 if match else 0,
        "detail": detail,
        "state_data": state_data,
    }


def compute_freshness(state_data: dict[str, Any], now: datetime) -> dict[str, Any]:
    ratio = 0.0
    detail = "no_state_file"
    if state_data:
        try:
            last_check_str = state_data.get("last_check", "")
            if not last_check_str:
                detail = "no_last_check"
            else:
                elapsed = (now - datetime.fromisoformat(last_check_str)).total_seconds()
                ttl = (
                    1800.0
                    if str(state_data.get("profile", "master")) == "client"
                    else 28800.0
                )
                ratio = max(0.0, 1.0 - elapsed / ttl)
                detail = f"elapsed={int(elapsed)}s ttl={int(ttl)}s"
        except Exception as exc:
            detail = f"error: {exc}"
    return {"ratio": ratio, "score": round(ratio * 20), "detail": detail}
