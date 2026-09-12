"""Unit tests for providence_cli.services.audit_export helper functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from providence_cli.services.audit_export import (
    _event_to_row,
    _resolve_governance_fingerprint,
)


def test_resolve_governance_fingerprint_falls_back_to_cwd_on_error(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir()
    (sdd_dir / "agent-instructions.md").write_text(
        "Fingerprint this version: `abc123`\n", encoding="utf-8"
    )
    with (
        patch(
            "providence_cli.services.audit_export.resolve_workspace_root",
            side_effect=RuntimeError("no workspace"),
        ),
        patch("providence_cli.services.audit_export.Path.cwd", return_value=tmp_path),
    ):
        result = _resolve_governance_fingerprint()
    assert result == "abc123"


def test_resolve_governance_fingerprint_falls_back_to_metadata_json(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_text(
        json.dumps({"fingerprints": {"combined": "deadbeef"}}), encoding="utf-8"
    )
    with patch(
        "providence_cli.services.audit_export.resolve_workspace_root",
        return_value=tmp_path,
    ):
        result = _resolve_governance_fingerprint()
    assert result == "deadbeef"


def test_resolve_governance_fingerprint_returns_empty_when_nothing_found(
    tmp_path: Path,
) -> None:
    with patch(
        "providence_cli.services.audit_export.resolve_workspace_root",
        return_value=tmp_path,
    ):
        result = _resolve_governance_fingerprint()
    assert result == ""


def test_resolve_governance_fingerprint_ignores_malformed_metadata_json(
    tmp_path: Path,
) -> None:
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_text("not valid json", encoding="utf-8")
    with patch(
        "providence_cli.services.audit_export.resolve_workspace_root",
        return_value=tmp_path,
    ):
        result = _resolve_governance_fingerprint()
    assert result == ""


def test_event_to_row_handles_non_dict_details() -> None:
    event = {
        "event": "VIOLATION",
        "command": "ask",
        "status": "warn",
        "start_ts": "2025-06-15T09:00:00Z",
        "details": "not-a-dict",
    }
    row = _event_to_row(event)
    assert row["drift_type"] == ""


def test_event_to_row_handles_missing_details() -> None:
    event = {
        "event": "INFO",
        "command": "runtime status",
        "status": "ok",
        "start_ts": "2025-06-15T10:00:00Z",
    }
    row = _event_to_row(event)
    assert row["drift_type"] == ""
