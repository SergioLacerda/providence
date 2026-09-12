"""Audit event row mapping, governance fingerprint resolution, and CSV export."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_cli.utils.providence_authority import resolve_workspace_root


def _resolve_governance_fingerprint() -> str:
    try:
        root = resolve_workspace_root()
    except Exception:
        root = Path.cwd()
    agent_instructions = root / ".providence" / "agent-instructions.md"
    if agent_instructions.exists():
        with contextlib.suppress(OSError):
            for line in agent_instructions.read_text(encoding="utf-8").splitlines():
                if "Fingerprint this version:" in line:
                    return line.split(":", 1)[1].strip().strip("`")
    metadata = root / ".providence" / "metadata.json"
    if metadata.exists():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            raw = json.loads(metadata.read_text(encoding="utf-8"))
            fp = raw.get("fingerprints", {}).get("combined", "")
            if isinstance(fp, str) and fp.strip():
                return fp.strip()
    return ""


def _event_to_row(event: dict[str, Any]) -> dict[str, str]:
    from providence_cli.services.audit_runner import _drift_cause, _event_ts, _parse_int

    details = event.get("details", {})
    if not isinstance(details, dict):
        details = {}
    return {
        "timestamp": _event_ts(event),
        "event": str(event.get("event", "")).strip(),
        "command": str(event.get("command", "")).strip(),
        "status": str(event.get("status", "")).strip(),
        "drift_type": str(details.get("drift_type", "")).strip(),
        "cause": _drift_cause(event),
        "artifact_fingerprint": str(event.get("artifact_fingerprint", "")).strip(),
        "tokens_input": str(_parse_int(event.get("tokens_input")) or ""),
        "tokens_output": str(_parse_int(event.get("tokens_output")) or ""),
    }


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    fieldnames = [
        "timestamp",
        "event",
        "command",
        "status",
        "drift_type",
        "cause",
        "artifact_fingerprint",
        "tokens_input",
        "tokens_output",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _build_export_payload(
    *,
    source: Path,
    since: str | None,
    event_type: str | None,
    rows: list[dict[str, str]],
    fmt: str,
) -> tuple[bytes, dict[str, Any]]:
    csv_blob = _csv_bytes(rows)
    sha256 = hashlib.sha256(csv_blob).hexdigest()
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "events_file": str(source),
        "format": fmt,
        "filters": {"since": since, "event_type": event_type},
        "count": len(rows),
        "governance_fingerprint": _resolve_governance_fingerprint(),
        "sha256": sha256,
    }
    return csv_blob, manifest
