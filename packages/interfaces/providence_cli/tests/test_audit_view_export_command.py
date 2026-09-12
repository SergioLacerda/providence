"""Integration tests for providence audit view/export/legacy-check/bootstrap-check/compliance-pack."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _write_view_events(path: Path) -> None:
    events = [
        {
            "event": "VIOLATION",
            "command": "ask",
            "status": "warn",
            "start_ts": "2025-05-30T09:00:00Z",
            "artifact_fingerprint": "aaaabbbbccccdddd",
            "details": {"drift_type": "policy_drift"},
        },
        {
            "event": "VIOLATION",
            "command": "ask",
            "status": "warn",
            "start_ts": "2025-06-15T09:00:00Z",
            "artifact_fingerprint": "eeeeffff11112222",
            "details": {"drift_type": "session_drift"},
            "tokens_input": 21,
            "tokens_output": 13,
        },
        {
            "event": "INFO",
            "command": "runtime status",
            "status": "ok",
            "start_ts": "2025-06-15T10:00:00Z",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")


def test_audit_view_filters_by_since_and_event_type(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_view_events(events_file)
    result = runner.invoke(
        app,
        [
            "audit",
            "view",
            "--events-file",
            str(events_file),
            "--since",
            "2025-06-01",
            "--event-type",
            "VIOLATION",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "matched events: 1" in result.output
    assert "ask" in result.output
    assert "runtime status" not in result.output


def test_audit_export_csv_and_manifest(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    manifest_file = tmp_path / "manifest.json"
    _write_view_events(events_file)
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--events-file",
            str(events_file),
            "--since",
            "2025-06-01",
            "--event-type",
            "VIOLATION",
            "--format",
            "csv",
            "--manifest-file",
            str(manifest_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (
        "timestamp,event,command,status,drift_type,cause,artifact_fingerprint,tokens_input,tokens_output"
        in result.output
    )
    assert "VIOLATION,ask,warn,session_drift" in result.output
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["format"] == "csv"
    assert manifest["count"] == 1
    assert manifest["filters"]["since"] == "2025-06-01"
    assert manifest["filters"]["event_type"] == "VIOLATION"
    assert len(manifest["sha256"]) == 64


def test_audit_export_rejects_unknown_format(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_view_events(events_file)
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--events-file",
            str(events_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert "Only --format=csv is currently supported." in result.output


def test_audit_legacy_check_blocks_in_q4_with_hits(tmp_path: Path) -> None:
    legacy_doc = tmp_path / "README.md"
    legacy_doc.write_text("use /legacy/path here", encoding="utf-8")
    with patch(
        "providence_cli.commands.audit_export_commands.resolve_workspace_root",
        return_value=tmp_path,
    ):
        result = runner.invoke(
            app,
            ["audit", "legacy-check", "--phase-date", "2026-10-01"],
        )
    assert result.exit_code == 2
    assert "policy mode: block" in result.output


def test_audit_bootstrap_check_ok(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "Initial reference: .providence/agent-instructions.md\nClaude: ./CLAUDE.md\n",
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        "Read .providence/agent-instructions.md", encoding="utf-8"
    )
    with patch(
        "providence_cli.commands.audit_export_commands.resolve_workspace_root",
        return_value=tmp_path,
    ):
        result = runner.invoke(app, ["audit", "bootstrap-check"])
    assert result.exit_code == 0, result.output
    assert "status: OK" in result.output


def test_audit_compliance_pack_generates_files(tmp_path: Path) -> None:
    events_file = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
    _write_view_events(events_file)
    out_dir = tmp_path / "pack"

    with (
        patch(
            "providence_cli.commands.audit_export_commands.resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands.audit_export_commands.SafeProcessRunner.run",
            side_effect=[
                SimpleNamespace(stdout="", stderr="", returncode=0, success=True),
                SimpleNamespace(stdout="runtime ok\n", stderr="", returncode=0),
                SimpleNamespace(stdout="governance ok\n", stderr="", returncode=0),
            ],
        ),
    ):
        result = runner.invoke(
            app,
            [
                "audit",
                "compliance-pack",
                "--out-dir",
                str(out_dir),
                "--since",
                "2025-06-01",
                "--event-type",
                "VIOLATION",
            ],
        )

    assert result.exit_code == 0, result.output
    assert (out_dir / "compliance_report.csv").exists()
    assert (out_dir / "compliance_report.manifest.json").exists()
    assert (out_dir / "runtime_status.txt").exists()
    assert (out_dir / "governance_validation.txt").exists()
    assert (out_dir / "decision_trace.md").exists()
    assert (out_dir / "external_review_checklist.md").exists()


def test_audit_compliance_pack_missing_providence_cli_module_exits_1(
    tmp_path: Path,
) -> None:
    events_file = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
    _write_view_events(events_file)
    out_dir = tmp_path / "pack"

    with (
        patch(
            "providence_cli.commands.audit_export_commands.resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.utils.dev_deps.check_module_available", return_value=False
        ),
    ):
        result = runner.invoke(
            app,
            ["audit", "compliance-pack", "--out-dir", str(out_dir)],
        )

    assert result.exit_code == 1
    assert "not available in this environment" in result.output
