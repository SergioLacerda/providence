"""Integration tests for providence audit (summary) CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _write_events(path: Path) -> None:
    events = [
        {
            "event": "governance.ask",
            "command": "ask",
            "status": "ok",
            "start_ts": "2026-05-20T10:00:00Z",
            "artifact_fingerprint": "aaaaaaaa11111111",
            "tokens_input": 120,
            "tokens_output": 60,
            "details": {"drift_detected": False},
        },
        {
            "event": "runtime.drift.detected",
            "command": "runtime status",
            "status": "warn",
            "start_ts": "2026-05-20T10:05:00Z",
            "artifact_fingerprint": "bbbbbbbb22222222",
            "details": {
                "drift_type": "profile_drift",
                "reason": "profile mismatch",
                "remediation_command": "providence runtime status --force",
            },
        },
        {
            "event": "governance.ask",
            "command": "ask",
            "status": "warn",
            "start_ts": "2026-05-20T10:10:00Z",
            "artifact_fingerprint": "cccccccc33333333",
            "tokens_input": 80,
            "tokens_output": 40,
            "details": {"drift_detected": True, "drift_type": "session_drift"},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")


def test_audit_default_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    assert "SDD Audit Summary" in result.output
    assert "- total events: 3" in result.output
    assert "- total drifts: 2" in result.output
    assert "Correlation Windows (7/14/30)" in result.output
    assert "Top 10 Drift Events" in result.output
    assert "profile_drift" in result.output


def test_audit_json_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["--json", "audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["command"] == "audit"
    assert payload["ok"] is True
    assert payload["data"]["total_events"] == 3
    assert payload["data"]["total_drifts"] == 2
    assert payload["data"]["token_comparison"]["total_input_tokens"] == 200
    assert payload["data"]["token_comparison"]["total_output_tokens"] == 100
    assert "drift_unclassified_total" in payload["data"]
    assert "correlation_windows" in payload["data"]
    assert [w["window_days"] for w in payload["data"]["correlation_windows"]] == [
        7,
        14,
        30,
    ]
    assert len(payload["data"]["top_drifts"]) == 2


def test_audit_json_output_uses_canonical_data_payload(
    tmp_path: Path, monkeypatch
) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["--json", "audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["command"] == "audit"
    assert payload["data"]["total_events"] == 3
    assert "total_events" not in payload


def test_audit_token_metrics_scoped_to_ask_invocations(tmp_path: Path) -> None:
    """Phase/lifecycle events never carry tokens and must not count as missing."""
    events = [
        {
            "event": "governance.ask",
            "command": "ask",
            "start_ts": "2026-05-20T10:00:00Z",
            "tokens_input": 100,
            "tokens_output": 50,
            "details": {},
        },
        {
            "event": "governance.ask.phase",
            "command": "ask",
            "start_ts": "2026-05-20T10:00:01Z",
            "tokens_input": None,
            "tokens_output": None,
            "details": {"phase_id": "intake"},
        },
        {
            "event": "runtime.session.start",
            "command": "runtime status",
            "start_ts": "2026-05-20T10:00:02Z",
            "tokens_input": None,
            "tokens_output": None,
            "details": {},
        },
    ]
    events_file = tmp_path / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    with events_file.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")

    text_result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert text_result.exit_code == 0, text_result.output
    assert "- ask invocations without tokens: 0 (of 1)" in text_result.output
    assert "- non-token-bearing events: 2" in text_result.output

    json_result = runner.invoke(
        app, ["--json", "audit", "--events-file", str(events_file)]
    )
    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output.strip().splitlines()[-1])
    tc = payload["data"]["token_comparison"]
    assert tc["ask_invocations"] == 1
    assert tc["events_with_tokens"] == 1
    assert tc["events_missing_tokens"] == 0
    assert tc["non_token_events"] == 2


def test_audit_include_non_drift_flag(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(
        app,
        ["--json", "audit", "--events-file", str(events_file), "--include-non-drift"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert "non_drift_events" in payload["data"]


def test_audit_no_drift_events_text_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.write_text(
        json.dumps(
            {
                "event": "governance.ask",
                "command": "ask",
                "start_ts": "2026-05-20T10:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert result.exit_code == 0
    assert "no drift events found" in result.output
