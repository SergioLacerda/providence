"""JSON output contract tests for `runtime status`."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from providence_cli.main import app

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


def test_root_json_flag_sets_structured_runtime_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_core.utils.environment.find_workspace_root", lambda: Path(".")
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.commands.runtime._emit_runtime_status",
        lambda **_: {"detected": False, "type": "none", "reason": ""},
    )
    monkeypatch.setattr(
        "providence_cli.commands.runtime._show_ask_confidence",
        lambda workspace_root, emit=True: {"last_ask_ts": "now"},
    )

    result = runner.invoke(app, ["--json", "runtime", "status"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["state"] == "HEALTHY"
    assert payload["data"]["exit_code"] == 0
    assert payload["data"]["drift"]["detected"] is False
    assert payload["data"]["governance_footer"].startswith("PROVIDENCE GOVERNANCE:")


def test_global_verbose_is_accepted_on_runtime_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_core.utils.environment.find_workspace_root", lambda: Path(".")
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.commands.runtime._emit_runtime_status",
        lambda **_: {"detected": False, "type": "none", "reason": ""},
    )
    monkeypatch.setattr(
        "providence_cli.commands.runtime._show_ask_confidence",
        lambda workspace_root, emit=True: None,
    )

    result = runner.invoke(app, ["--verbose", "runtime", "status"])

    assert result.exit_code == 0, result.output
    assert "HEALTHY:verbose" in result.output
    assert "PROVIDENCE GOVERNANCE: drift=none" in result.output


def test_runtime_status_json_uses_canonical_data_payload(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "providence_core.utils.environment.find_workspace_root", lambda: Path(".")
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.commands.runtime._emit_runtime_status",
        lambda **_: {"detected": False, "type": "none", "reason": ""},
    )
    monkeypatch.setattr(
        "providence_cli.commands.runtime._show_ask_confidence",
        lambda workspace_root, emit=True: {"last_ask_ts": "now"},
    )

    result = runner.invoke(app, ["--json", "runtime", "status"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["data"]["state"] == "HEALTHY"
    assert "state" not in payload
