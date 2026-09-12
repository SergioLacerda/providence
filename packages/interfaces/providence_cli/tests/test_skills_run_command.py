"""Integration tests for the providence skills run CLI command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _load_json_output(raw: str) -> dict:
    # Some environments emit a governance soft preface line before JSON output.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def test_skills_run_dry_run_json() -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = runner.invoke(app, ["--json", "skills", "run", "validate-governance"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills run"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "planned"
    assert data["exit_code"] == 0
    assert data["governance_footer"].startswith("PROVIDENCE GOVERNANCE:")


def test_skills_run_footer_uses_providence_label_for_skill_id() -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = runner.invoke(app, ["--json", "skills", "run", "sdd-diagnose"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    data = _payload_data(payload)
    assert data["profile"] == "sdd-diagnose"
    assert "profile=providence-diagnose" in data["governance_footer"]


def test_skills_run_text_appends_governance_footer() -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = runner.invoke(app, ["skills", "run", "validate-governance"])
    assert result.exit_code == 0, result.output
    assert "PROVIDENCE GOVERNANCE: drift=" in result.output


def test_skills_run_execute_json_includes_command_results() -> None:
    fake_result = MagicMock()
    fake_result.state = "ok"
    fake_result.profile = "default"
    fake_result.skill = "validate-governance"
    fake_result.policy_result = "executed"
    fake_result.reason = "runtime execution completed"
    fake_result.exit_code = 0
    fake_result.governance_footer = (
        "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=default"
    )
    fake_result.fallback = ["providence governance validate"]
    fake_result.command_results = [
        {
            "command": "providence governance validate",
            "status": "ok",
            "exit_code": 0,
            "error": "",
        }
    ]
    fake_result.artifacts = {"gate_decision": {"decision": "allow"}}

    with patch(
        "providence_cli.commands.skills.SkillEngine.run_skill", return_value=fake_result
    ):
        result = runner.invoke(
            app,
            ["--json", "skills", "run", "validate-governance", "--execute"],
        )
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills run"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "executed"
    assert data["command_results"][0]["command"] == "providence governance validate"
    assert data["artifacts"]["gate_decision"]["decision"] == "allow"


def test_skills_run_correct_denied_when_pipeline_enforcement_enabled() -> None:
    with patch.dict("os.environ", {"SDD_ENFORCE_PIPELINE_CORRECT": "1"}):
        result = runner.invoke(app, ["--json", "skills", "run", "sdd-correct"])
    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "skills run"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "denied"
    assert data["reason"] == "pipeline_required_for_sdd_correct"


def test_skills_run_correct_blocked_text_mode() -> None:
    with patch.dict("os.environ", {"SDD_ENFORCE_PIPELINE_CORRECT": "1"}):
        result = runner.invoke(app, ["skills", "run", "sdd-correct"])
    assert result.exit_code == 1
    assert "bloqueado" in result.output or "blocked" in result.output.lower()


def test_skills_run_exit_nonzero_on_failed_result() -> None:
    fake_result = MagicMock()
    fake_result.state = "error"
    fake_result.profile = "default"
    fake_result.skill = "sdd-diagnose"
    fake_result.policy_result = "error"
    fake_result.reason = "failed"
    fake_result.exit_code = 1
    fake_result.governance_footer = "PROVIDENCE GOVERNANCE: drift=none"
    fake_result.fallback = []
    fake_result.command_results = []
    fake_result.artifacts = {}

    with (
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
        patch("providence_cli.commands.skills.SkillEngine") as mock_engine_cls,
    ):
        mock_engine_cls.return_value.run_skill.return_value = fake_result
        result = runner.invoke(app, ["skills", "run", "sdd-diagnose"])
    assert result.exit_code == 1
