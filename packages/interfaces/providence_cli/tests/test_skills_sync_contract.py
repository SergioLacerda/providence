from __future__ import annotations

import json

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _load_json_output(raw: str) -> dict:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def test_skills_run_json_syncs_runtime_success_payload(monkeypatch) -> None:
    from providence_runtime.skills import SkillRunResult

    runtime_result = SkillRunResult(
        state="ok",
        profile="default",
        skill="validate-governance",
        policy_result="executed",
        reason="runtime execution completed",
        exit_code=0,
        governance_footer="PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=default",
        fallback=["providence governance validate", "providence runtime status"],
        command_results=[
            {
                "command": "providence governance validate",
                "status": "ok",
                "exit_code": 0,
                "error": "",
            },
            {
                "command": "providence runtime status",
                "status": "ok",
                "exit_code": 0,
                "error": "",
            },
        ],
    )

    monkeypatch.setattr(
        "providence_cli.commands.skills.SkillEngine.run_skill",
        lambda *a, **k: runtime_result,
    )

    result = runner.invoke(
        app, ["--json", "skills", "run", "validate-governance", "--execute"]
    )
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    data = _payload_data(payload)

    assert data["state"] == runtime_result.state
    assert data["profile"] == runtime_result.profile
    assert data["skill"] == runtime_result.skill
    assert data["policy_result"] == runtime_result.policy_result
    assert data["reason"] == runtime_result.reason
    assert data["exit_code"] == runtime_result.exit_code
    assert data["governance_footer"] == runtime_result.governance_footer
    assert data["fallback"] == runtime_result.fallback
    assert data["command_results"] == runtime_result.command_results


def test_skills_run_json_syncs_runtime_error_payload(monkeypatch) -> None:
    from providence_runtime.skills import SkillRunResult

    runtime_result = SkillRunResult(
        state="error",
        profile="default",
        skill="review-architecture",
        policy_result="blocked",
        reason="enforcement strict: high-risk skill blocked",
        exit_code=1,
        governance_footer="PROVIDENCE GOVERNANCE: drift=fallback_cli | governance=blocked | profile=default",
        fallback=["providence governance score --verbose"],
        command_results=[
            {
                "command": "providence governance score --verbose",
                "status": "error",
                "exit_code": 1,
                "error": "blocked",
            }
        ],
    )

    monkeypatch.setattr(
        "providence_cli.commands.skills.SkillEngine.run_skill",
        lambda *a, **k: runtime_result,
    )

    result = runner.invoke(app, ["--json", "skills", "run", "review-architecture"])
    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    data = _payload_data(payload)

    for key in (
        "state",
        "profile",
        "skill",
        "policy_result",
        "reason",
        "exit_code",
        "governance_footer",
        "fallback",
        "command_results",
    ):
        assert key in data

    assert data["policy_result"] == "blocked"
    assert data["command_results"][0]["status"] == "error"
