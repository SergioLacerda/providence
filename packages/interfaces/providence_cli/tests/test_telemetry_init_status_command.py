"""Tests for providence telemetry init/status commands per observability-core plan."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _make_sink(tmp_path: Path, events: list[dict]) -> Path:
    runtime_dir = tmp_path / ".providence" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    sink = runtime_dir / "compliance-events.jsonl"
    sink.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return sink


def _patch_root(monkeypatch, tmp_path: Path) -> None:
    # Force workspace-based sink resolution inside tests even if outer
    # environments export telemetry path overrides (e.g. CI container jobs).
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )


# ---------------------------------------------------------------------------
# providence telemetry init
# ---------------------------------------------------------------------------


def test_init_creates_directory_and_file(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["created"] is True
    assert payload["data"]["valid"] is True
    assert Path(os.path.realpath(payload["data"]["events_file"])).exists()


def test_init_idempotent(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    runner.invoke(app, ["--json", "telemetry", "init"])
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["created"] is False
    assert payload["data"]["valid"] is True


def test_init_validates_corrupt_jsonl(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    sink = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text('{"event": "ok"}\nNOT JSON\n{"event": "ok"}\n', encoding="utf-8")
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_jsonl"
    assert payload["data"]["invalid_line"] == 2


def test_init_skips_blank_lines(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    sink = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text('{"event": "ok"}\n\n{"event": "ok2"}\n', encoding="utf-8")
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["valid"] is True


# ---------------------------------------------------------------------------
# providence telemetry status
# ---------------------------------------------------------------------------


def test_status_missing_file_includes_hint(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["total_events"] == 0
    assert "hint" in payload["data"]
    assert "init" in payload["data"]["hint"]


def test_status_empty_file_no_hint(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["total_events"] == 0
    assert "hint" not in payload["data"]


def test_status_event_type_breakdown(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "status": "ok"},
            {"event": "governance.ask", "status": "ok"},
            {"event": "runtime.drift.detected", "status": "warn"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["total_events"] == 3
    assert payload["data"]["events_by_type"]["governance.ask"] == 2
    assert payload["data"]["events_by_type"]["runtime.drift.detected"] == 1


# ---------------------------------------------------------------------------
# Plain-text (non-JSON) output paths  coverage for human-readable branches
# ---------------------------------------------------------------------------


def test_status_text_output_with_events(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {
                "event": "governance.ask",
                "status": "ok",
                "start_ts": "2026-05-21T10:00:00Z",
            },
            {
                "event": "governance.ask",
                "status": "ok",
                "start_ts": "2026-05-21T10:01:00Z",
            },
        ],
    )
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "Total events: 2" in result.output
    assert "governance.ask" in result.output


def test_status_text_missing_file_shows_hint(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "init" in result.output.lower()


def test_status_text_empty_file(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "No events" in result.output


def test_init_text_creates_file(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["telemetry", "init"])
    assert result.exit_code == 0
    assert "Created" in result.output


def test_init_text_already_exists(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    runner.invoke(app, ["telemetry", "init"])
    result = runner.invoke(app, ["telemetry", "init"])
    assert result.exit_code == 0
    assert "Already exists" in result.output


def test_init_text_invalid_jsonl(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    sink = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text('{"ok": true}\nBAD JSON\n', encoding="utf-8")
    result = runner.invoke(app, ["telemetry", "init"])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_default_events_path_fallback_on_exception(monkeypatch) -> None:
    """_default_events_path raises when resolve_workspace_root fails."""
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: (_ for _ in ()).throw(RuntimeError("no workspace")),
    )
    from providence_cli.commands._telemetry_app import _default_events_path

    with pytest.raises(RuntimeError):
        _default_events_path()


def test_status_workspace_resolution_failure_json(monkeypatch) -> None:
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: (_ for _ in ()).throw(RuntimeError("no workspace")),
    )
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "workspace_resolution_failed"


def test_status_workspace_resolution_failure_text(monkeypatch) -> None:
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: (_ for _ in ()).throw(RuntimeError("no workspace")),
    )
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 1
    assert "failed to resolve workspace root" in result.output


def test_parse_ts_empty_string_returns_none() -> None:
    from providence_cli.commands.telemetry import _parse_ts

    assert _parse_ts("") is None


def test_telemetry_default_callback_lists_commands(monkeypatch, tmp_path: Path) -> None:
    """providence telemetry (no subcommand) lists telemetry commands."""
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "governance.ask", "status": "ok"}])
    result = runner.invoke(app, ["telemetry"])
    assert result.exit_code == 0
    assert "Telemetry commands:" in result.output
    assert "status" in result.output
