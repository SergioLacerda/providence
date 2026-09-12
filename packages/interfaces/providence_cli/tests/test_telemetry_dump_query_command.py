"""Tests for providence telemetry dump/query commands per observability-core plan."""

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
    # Force workspace-based sink resolution inside tests even if outer
    # environments export telemetry path overrides (e.g. CI container jobs).
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )


# ---------------------------------------------------------------------------
# providence telemetry dump
# ---------------------------------------------------------------------------


def test_dump_trace_id_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "trace_id": "abc123"},
            {"event": "governance.ask", "trace_id": "def456"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--trace-id", "abc123"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["returned"] == 1
    assert payload["data"]["events"][0]["trace_id"] == "abc123"


def test_dump_format_json_array(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "e1"}, {"event": "e2"}])
    result = runner.invoke(app, ["telemetry", "dump", "--format", "json"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert len(parsed) == 2


def test_dump_limit(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": f"e{i}"} for i in range(10)])
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--limit", "3"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["returned"] == 3


def test_dump_invalid_format_errors(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "e1"}])
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--format", "yaml"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_format"


# ---------------------------------------------------------------------------
# providence telemetry query  new filters
# ---------------------------------------------------------------------------


def test_query_trace_id_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "trace_id": "aaa", "start_ts": "2026-05-21T10:00:00Z"},
            {"event": "e2", "trace_id": "bbb", "start_ts": "2026-05-21T10:01:00Z"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "query", "--trace-id", "aaa"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["matched"] == 1
    assert payload["data"]["events"][0]["trace_id"] == "aaa"


def test_query_status_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "status": "ok"},
            {"event": "e2", "status": "fail"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "query", "--status", "ok"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["matched"] == 1


def test_query_level_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "level": "ERROR"},
            {"event": "e2", "level": "INFO"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "query", "--level", "ERROR"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["matched"] == 1


def test_query_until_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "early", "start_ts": "2026-05-01T00:00:00Z"},
            {"event": "late", "start_ts": "2026-05-21T00:00:00Z"},
        ],
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--until", "2026-05-10T00:00:00Z"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["matched"] == 1
    assert payload["data"]["events"][0]["event"] == "early"


def test_query_invalid_until_errors(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--until", "not-a-date"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_until"


def test_query_and_semantics_all_filters(monkeypatch, tmp_path: Path) -> None:
    """All filters are AND  event must satisfy every filter provided."""
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "status": "ok", "trace_id": "aaa"},
            {"event": "governance.ask", "status": "fail", "trace_id": "bbb"},
            {"event": "runtime.drift", "status": "ok", "trace_id": "aaa"},
        ],
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "telemetry",
            "query",
            "--event-type",
            "governance.ask",
            "--status",
            "ok",
            "--trace-id",
            "aaa",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["matched"] == 1


def test_query_no_results_returns_empty_list(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "governance.ask", "trace_id": "xyz"}])
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--trace-id", "nonexistent"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["matched"] == 0
    assert payload["data"]["events"] == []


def test_dump_text_jsonl_output(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "e1"}, {"event": "e2"}])
    result = runner.invoke(app, ["telemetry", "dump", "--limit", "10"])
    assert result.exit_code == 0
    lines = [line for line in result.output.strip().splitlines() if line]
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "e1"


def test_query_text_output_with_results(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "start_ts": "2026-05-21T10:00:00Z"},
        ],
    )
    result = runner.invoke(
        app, ["telemetry", "query", "--event-type", "governance.ask"]
    )
    assert result.exit_code == 0
    assert "governance.ask" in result.output
    assert "1 events matched" in result.output


def test_query_text_since_invalid_non_json(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "query", "--since", "bad-date"])
    assert result.exit_code == 1
    assert "Invalid --since" in result.output


def test_query_text_until_invalid_non_json(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "query", "--until", "bad-date"])
    assert result.exit_code == 1
    assert "Invalid --until" in result.output


def test_query_work_item_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "work_item_id": "ticket-123"},
            {"event": "e2", "work_item_id": "ticket-456"},
        ],
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--work-item", "ticket-123"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["matched"] == 1
