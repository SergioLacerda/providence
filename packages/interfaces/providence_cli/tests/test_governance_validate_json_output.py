"""JSON output contract tests for `governance validate` and `governance load`."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from providence_cli.main import app
from providence_cli.services.runtime_preflight import PreflightResult

runner = CliRunner()


class _FakeReport:
    confidence = 87.5
    status = "ok"


class _FakeAHP:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root
        self.skill_profile = "default"

    def validate(
        self, output_mode: str, force_recheck: bool = False
    ) -> tuple[str, _FakeReport]:
        return "HEALTHY", _FakeReport()

    def format_combined_output(self, state: str, report: _FakeReport, mode: str) -> str:
        return f"{state}:{mode}:{report.confidence}"

    def is_handshake_valid(self) -> bool:
        return True


def _parse_result_json(output: str) -> dict:
    """Parse JSON output allowing CI preamble/noise before canonical envelope."""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def _parse_json_output(result) -> dict:
    """Parse structured CLI output robustly when non-JSON lines are present."""
    raw = result.output or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        lines = [line for line in raw.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def test_governance_validate_json_bypasses_rich_tables(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.load_governance_config",
        lambda _: {"core_fingerprint": "a", "client_fingerprint": "b"},
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_files_accessible",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_fingerprints_valid",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_no_conflicts",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_root_seed_drift",
        lambda _: (True, "no root-seed drift detected"),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_preflight.run_runtime_preflight",
        lambda _: PreflightResult(passed=True, reason="", details={"skipped": False}),
    )
    with patch("providence_cli.commands.governance.Table", create=True) as mocked_table:
        result = runner.invoke(app, ["--json", "governance", "validate"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["preflight"]["passed"] is True
    mocked_table.assert_not_called()


def test_governance_validate_json_uses_canonical_data_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.load_governance_config",
        lambda _: {"core_fingerprint": "a", "client_fingerprint": "b"},
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_files_accessible",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_fingerprints_valid",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_no_conflicts",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_root_seed_drift",
        lambda _: (True, "no root-seed drift detected"),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_preflight.run_runtime_preflight",
        lambda _: PreflightResult(passed=True, reason="", details={"skipped": False}),
    )
    result = runner.invoke(app, ["--json", "governance", "validate"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["data"]["exit_code"] == 0
    assert "exit_code" not in payload


def test_governance_load_json_uses_canonical_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.load_governance_config",
        lambda _: {"core_fingerprint": "a"},
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.get_governance_summary",
        lambda _path, config=None: {"items": 1},
    )
    result = runner.invoke(app, ["--json", "governance", "load"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["summary"]["items"] == 1


def test_governance_load_json_error_uses_canonical_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: False
    )
    result = runner.invoke(app, ["--json", "governance", "load"])

    assert result.exit_code == 1, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_governance_path"
    assert isinstance(payload["data"], dict)
