"""Integration tests for providence skills learning-* CLI commands."""

from __future__ import annotations

import json
from unittest.mock import patch

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


def test_skills_learning_candidates_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands.skills_learning.resolve_workspace_root",
            return_value=tmp_path,
        ),
    ):
        result = runner.invoke(app, ["--json", "skills", "learning-candidates"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills learning-candidates"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "learning_candidates_listed"
    assert isinstance(data["candidates"], list)


def test_skills_learning_approve_and_rules_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands.skills_learning.resolve_workspace_root",
            return_value=tmp_path,
        ),
    ):
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "rule-candidates.json").write_text(
            json.dumps(
                {
                    "candidates": [
                        {
                            "candidate_id": "rc-1",
                            "pattern": "h|r",
                            "proposed_guardrail": "g",
                            "risk_level": "medium",
                            "expected_impact": "reduce_rework",
                            "evidence_refs": ["e"],
                            "source_count": 2,
                            "created_at": "2026-01-01T00:00:00+00:00",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        approve = runner.invoke(
            app,
            [
                "--json",
                "skills",
                "learning-approve",
                "rc-1",
                "--reviewer",
                "human",
                "--rationale",
                "looks good",
                "--ttl-days",
                "30",
            ],
        )
        assert approve.exit_code == 0, approve.output
        payload = _load_json_output(approve.output)
        assert payload["status"] == "ok"
        assert payload["command"] == "skills learning-approve"
        assert payload["ok"] is True
        assert payload["error"] is None
        assert isinstance(payload["data"], dict)
        data = _payload_data(payload)
        assert data["policy_result"] == "rule_approved"

        rules = runner.invoke(app, ["--json", "skills", "learning-rules"])
        assert rules.exit_code == 0, rules.output
        rules_payload = _load_json_output(rules.output)
        assert rules_payload["status"] == "ok"
        assert rules_payload["command"] == "skills learning-rules"
        assert rules_payload["ok"] is True
        assert rules_payload["error"] is None
        assert isinstance(rules_payload["data"], dict)
        rules_data = _payload_data(rules_payload)
        assert rules_data["policy_result"] == "active_rules_listed"
        assert isinstance(rules_data["rules"], list)


def test_skills_learning_impact_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands.skills_learning.resolve_workspace_root",
            return_value=tmp_path,
        ),
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "skills",
                "learning-impact",
                "rr-1",
                "--rework-delta",
                "-0.1",
                "--false-block-rate",
                "0.2",
                "--escalation-delta",
                "0.05",
            ],
        )
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills learning-impact"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "rule_impact_recorded"


def test_skills_learning_status_json(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands.skills_learning.resolve_workspace_root",
            return_value=tmp_path,
        ),
    ):
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "rule-candidates.json").write_text(
            json.dumps({"candidates": [{"candidate_id": "rc-1"}]}), encoding="utf-8"
        )
        (runtime_dir / "rule-registry.json").write_text(
            json.dumps(
                {
                    "rules": [
                        {"rule_id": "rr-1", "status": "active"},
                        {"rule_id": "rr-2", "status": "rolled_back"},
                        {"rule_id": "rr-3", "status": "expired"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (runtime_dir / "rule-impact.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "rule_id": "rr-1",
                            "rework_delta": -0.2,
                            "false_block_rate": 0.1,
                            "escalation_delta": 0.05,
                            "rollback_flag": False,
                            "timestamp": "2099-01-01T00:00:00+00:00",
                        }
                    ),
                    json.dumps(
                        {
                            "rule_id": "rr-2",
                            "rework_delta": 0.3,
                            "false_block_rate": 0.2,
                            "escalation_delta": 0.1,
                            "rollback_flag": True,
                            "timestamp": "2099-01-01T00:00:00+00:00",
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["--json", "skills", "learning-status"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills learning-status"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "learning_status_loaded"
    status = data["status"]
    assert status["candidates_total"] == 1
    assert status["rules_active"] == 1
    assert status["rules_rolled_back"] == 1
    assert status["rules_expired"] == 1
    assert "kpi_rework_reduction_pct_recent" in status


def test_skills_learning_candidates_text_mode(tmp_path) -> None:
    with (
        patch(
            "providence_cli.commands.skills_learning.resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands.skills_learning.SupervisedLearningStore"
        ) as mock_store_cls,
    ):
        mock_store_cls.return_value.generate_candidates_from_ledger.return_value = []
        result = runner.invoke(app, ["skills", "learning-candidates"])
    assert result.exit_code == 0
    assert "rule candidates:" in result.output


def test_skills_learning_candidates_text_mode_with_existing(tmp_path) -> None:
    candidates_path = tmp_path / ".providence" / "runtime" / "rule-candidates.json"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    candidates_path.write_text(
        json.dumps({"candidates": [{"candidate_id": "c1", "pattern": "foo.*"}]}),
        encoding="utf-8",
    )
    with (
        patch(
            "providence_cli.commands.skills_learning.resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands.skills_learning.SupervisedLearningStore"
        ) as mock_store_cls,
    ):
        mock_store_cls.return_value.generate_candidates_from_ledger.return_value = []
        result = runner.invoke(app, ["skills", "learning-candidates"])
    assert result.exit_code == 0
    assert "c1" in result.output
