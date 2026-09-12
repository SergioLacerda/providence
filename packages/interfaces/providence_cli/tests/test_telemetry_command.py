from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def test_telemetry_status_global_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_dir = tmp_path / ".providence" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    events_file = runtime_dir / "compliance-events.jsonl"
    events_file.write_text(
        json.dumps(
            {
                "event": "governance.ask",
                "status": "ok",
                "start_ts": "2026-05-21T10:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )

    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "telemetry status"
    assert payload["ok"] is True
    assert payload["data"]["total_events"] == 1


def test_telemetry_init_json_uses_canonical_data_payload(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )

    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "telemetry init"
    assert payload["data"]["created"] is True
    assert "created" not in payload


def test_telemetry_dump_global_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_dir = tmp_path / ".providence" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    events_file = runtime_dir / "compliance-events.jsonl"
    events_file.write_text(
        json.dumps({"event": "governance.ask", "status": "ok"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )

    result = runner.invoke(app, ["--json", "telemetry", "dump", "--limit", "10"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "telemetry dump"
    assert payload["data"]["returned"] == 1


def test_telemetry_query_invalid_since_still_errors(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--since", "invalid-date"]
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "telemetry query"
    assert payload["error"]["code"] == "invalid_since"


def test_telemetry_query_global_json_uses_canonical_envelope(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_dir = tmp_path / ".providence" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    events_file = runtime_dir / "compliance-events.jsonl"
    events_file.write_text(
        json.dumps(
            {
                "event": "governance.ask",
                "status": "ok",
                "start_ts": "2026-05-21T10:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--event-type", "governance.ask"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "telemetry query"
    assert payload["data"]["matched"] == 1


def test_telemetry_query_json_uses_canonical_data_payload(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_dir = tmp_path / ".providence" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    events_file = runtime_dir / "compliance-events.jsonl"
    events_file.write_text(
        json.dumps({"event": "governance.ask", "status": "ok"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )
    result = runner.invoke(app, ["--json", "telemetry", "query"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "telemetry query"
    assert payload["data"]["matched"] == 1
    assert "matched" not in payload


def test_telemetry_dump_json_uses_canonical_data_payload(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_dir = tmp_path / ".providence" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    events_file = runtime_dir / "compliance-events.jsonl"
    events_file.write_text(
        json.dumps({"event": "governance.ask", "status": "ok"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "providence_cli.commands._telemetry_app.resolve_workspace_root",
        lambda: tmp_path,
    )
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--limit", "5"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "telemetry dump"
    assert payload["data"]["returned"] == 1
    assert "returned" not in payload
