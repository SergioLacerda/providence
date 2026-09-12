"""Tests for `providence telemetry summary`  phase latency aggregation."""

from __future__ import annotations

import json
from pathlib import Path

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
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )


def test_summary_aggregates_phase_events(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {
                "event": "governance.ask.phase",
                "duration_ms": 10,
                "path_id": "PATH_A",
                "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
            },
            {
                "event": "governance.ask.phase",
                "duration_ms": 20,
                "path_id": "PATH_A",
                "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
            },
            {"event": "governance.ask", "duration_ms": 999},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "summary"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    groups = payload["data"]["groups"]
    assert len(groups) == 1
    assert groups[0]["phase_id"] == "ask.cli.entry"
    assert groups[0]["latency_domain"] == "local_cli"
    assert groups[0]["path_id"] == "PATH_A"
    assert groups[0]["count"] == 2
    assert groups[0]["min_ms"] == 10
    assert groups[0]["max_ms"] == 20
    assert groups[0]["avg_ms"] == 15


def test_summary_filters_by_path_id(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {
                "event": "governance.ask.phase",
                "duration_ms": 10,
                "path_id": "PATH_A",
                "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
            },
            {
                "event": "governance.ask.phase",
                "duration_ms": 30,
                "path_id": "PATH_B",
                "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
            },
        ],
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "summary", "--path-id", "PATH_B"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    groups = payload["data"]["groups"]
    assert len(groups) == 1
    assert groups[0]["path_id"] == "PATH_B"
    assert groups[0]["count"] == 1
    assert groups[0]["min_ms"] == 30


def test_summary_filters_by_phase_id_and_latency_domain(
    monkeypatch, tmp_path: Path
) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {
                "event": "governance.ask.phase",
                "duration_ms": 10,
                "path_id": "PATH_A",
                "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
            },
            {
                "event": "governance.ask.phase",
                "duration_ms": 50,
                "path_id": "PATH_A",
                "details": {
                    "phase_id": "ask.governance.snapshot",
                    "latency_domain": "governance",
                },
            },
        ],
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "telemetry",
            "summary",
            "--phase-id",
            "ask.governance.snapshot",
            "--latency-domain",
            "governance",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    groups = payload["data"]["groups"]
    assert len(groups) == 1
    assert groups[0]["phase_id"] == "ask.governance.snapshot"


def test_summary_empty_file_returns_empty_groups(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["--json", "telemetry", "summary"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["groups"] == []


def test_summary_no_matching_events_returns_empty_groups(
    monkeypatch, tmp_path: Path
) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "duration_ms": 999},
            {"event": "runtime.session.start"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "summary"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["groups"] == []


def test_summary_text_output(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {
                "event": "governance.ask.phase",
                "duration_ms": 10,
                "path_id": "PATH_A",
                "details": {"phase_id": "ask.cli.entry", "latency_domain": "local_cli"},
            },
        ],
    )
    result = runner.invoke(app, ["telemetry", "summary"])
    assert result.exit_code == 0, result.output
    assert "ask.cli.entry" in result.output
    assert "local_cli" in result.output


def test_summary_text_output_no_events(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "summary"])
    assert result.exit_code == 0, result.output
    assert "No governance.ask.phase events" in result.output
