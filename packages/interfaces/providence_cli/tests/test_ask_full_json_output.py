"""JSON output contract tests for `ask --full`."""

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


def test_ask_full_mode_json_output_uses_canonical_envelope(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._run_organize_intake",
        lambda workspace_root, query, skill: (
            True,
            "heavy",
            "/tmp/intake.json",
            2,
            "indexed_only",
            None,
        ),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._store_routing_decision",
        lambda workspace_root, query, skill, fingerprint, decision: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        lambda **kwargs: {
            "context_source": "compiled",
            "fingerprint": "fp-1",
            "mandates_count": 1,
            "authenticated": True,
            "degraded": False,
            "degrade_reason": "",
            "trust_source": "verified",
            "drift_detected": False,
            "root_seed_drift_detected": False,
            "learning_signals": {
                "diagnosis_inconclusive": 1,
                "evidence_insufficient": 0,
                "scope_violation": 0,
                "drift_recent_failures": 0,
                "observed_events": 1,
                "window_days": 7,
            },
            "handbook_lookup": {
                "status": "matched",
                "diagnostic": "handbook_match=1",
                "matches": [{"id": "HBK-CONTEXT-LOADING"}],
            },
        },
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask", "--full", "implement status?"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["command"] == "ask"
    assert payload["data"]["execution_gate"] == "allowed"
    assert payload["data"]["implementation_intent"] == {
        "sdd_ask_contract": "governance-context query only",
        "delegation_status": "not_executed",
        "next_valid_path": "implementation_handoff",
    }
    assert payload["data"]["learning_signals"]["diagnosis_inconclusive"] == 1
    assert payload["data"]["runtime_handbook"]["diagnostic"] == "handbook_match=1"
    assert payload["data"]["steps"][0]["step_id"] == "PARSE"


def test_ask_full_mode_global_json_flag_uses_canonical_envelope(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._run_organize_intake",
        lambda workspace_root, query, skill: (
            True,
            "heavy",
            "/tmp/intake.json",
            1,
            "indexed_only",
            None,
        ),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._store_routing_decision",
        lambda workspace_root, query, skill, fingerprint, decision: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        lambda **kwargs: {
            "context_source": "compiled",
            "fingerprint": "fp-1",
            "mandates_count": 1,
            "authenticated": True,
            "degraded": False,
            "degrade_reason": "",
            "trust_source": "verified",
            "drift_detected": False,
            "root_seed_drift_detected": False,
            "learning_signals": {
                "diagnosis_inconclusive": 0,
                "evidence_insufficient": 0,
                "scope_violation": 0,
                "drift_recent_failures": 0,
                "observed_events": 0,
                "window_days": 7,
            },
        },
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask", "--full", "status?"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["command"] == "ask"
    assert payload["data"]["learning_signals"]["observed_events"] == 0


def test_ask_full_mode_json_uses_canonical_data_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._run_organize_intake",
        lambda workspace_root, query, skill: (
            False,
            "light",
            "",
            0,
            "indexed_only",
            None,
        ),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._store_routing_decision",
        lambda workspace_root, query, skill, fingerprint, decision: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        lambda **kwargs: {
            "context_source": "compiled",
            "fingerprint": "fp-1",
            "mandates_count": 1,
            "authenticated": True,
            "degraded": False,
            "degrade_reason": "",
            "trust_source": "verified",
            "drift_detected": False,
            "root_seed_drift_detected": False,
            "learning_signals": {
                "diagnosis_inconclusive": 0,
                "evidence_insufficient": 0,
                "scope_violation": 0,
                "drift_recent_failures": 0,
                "observed_events": 0,
                "window_days": 7,
            },
        },
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask", "--full", "status?"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["data"]["governance_mode"] == "hard"
    assert payload["data"]["execution_gate"] == "blocked"
    assert "governance_mode" not in payload


def test_ask_json_response_includes_additive_intake_contract_fields(
    monkeypatch, tmp_path
) -> None:
    """Spike follow-up (20260714-sdd-ask-single-entrypoint-spike): the
    structured intake contract fields are additive and must never claim
    executed delegation or provider binding.
    """
    monkeypatch.delenv("SDD_ASK_ENTRYPOINT", raising=False)
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._run_organize_intake",
        lambda workspace_root, query, skill: (
            False,
            "light_input",
            "",
            0,
            "indexed_only",
            None,
        ),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._store_routing_decision",
        lambda workspace_root, query, skill, fingerprint, decision: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        lambda **kwargs: {
            "context_source": "compiled",
            "fingerprint": "fp-1",
            "mandates_count": 1,
            "authenticated": True,
            "degraded": False,
            "degrade_reason": "",
            "trust_source": "verified",
            "drift_detected": False,
            "root_seed_drift_detected": False,
            "learning_signals": {
                "diagnosis_inconclusive": 0,
                "evidence_insufficient": 0,
                "scope_violation": 0,
                "drift_recent_failures": 0,
                "observed_events": 0,
                "window_days": 7,
            },
        },
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask", "implement the new feature"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    data = payload["data"]
    assert data["intent"] == "implementation_request"
    assert data["entrypoint"] == "explicit_command"
    assert data["explicit_command"] == "sdd-ask"
    assert data["next_action"] == "create_execution_contract"
    assert data["delegation_executed"] is False
    assert data["provider_bound"] is False
    assert data["handoff_owner"] == "calling_agent"
    assert data["requires_user_approval"] is True
    # Existing fields must remain unchanged by the additive contract.
    assert data["execution_gate"] == "allowed"
    assert data["intake_index_mode"] == "none"


def test_ask_json_response_entrypoint_reflects_hook_env_marker(
    monkeypatch, tmp_path
) -> None:
    """When the prompt-submit hook invokes `providence ask`, it marks
    SDD_ASK_ENTRYPOINT=hook so the response can distinguish hook-originated
    calls from explicit/deliberate invocations."""
    monkeypatch.setenv("SDD_ASK_ENTRYPOINT", "hook")
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_workspace_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._emit_ask_telemetry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._write_runtime_cache",
        lambda workspace_root, last_ask: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._upsert_ask_session",
        lambda workspace_root, agent_id, work_item_id, artifact_fingerprint: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._run_organize_intake",
        lambda workspace_root, query, skill: (
            False,
            "light_input",
            "",
            0,
            "indexed_only",
            None,
        ),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._store_routing_decision",
        lambda workspace_root, query, skill, fingerprint, decision: None,
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._get_profile_state",
        lambda: ("master", "HEALTHY"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend._resolve_tokens",
        lambda query, output_text: (10, 20, "estimated"),
    )
    monkeypatch.setattr(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        lambda **kwargs: {
            "context_source": "compiled",
            "fingerprint": "fp-1",
            "mandates_count": 1,
            "authenticated": True,
            "degraded": False,
            "degrade_reason": "",
            "trust_source": "verified",
            "drift_detected": False,
            "root_seed_drift_detected": False,
            "learning_signals": {
                "diagnosis_inconclusive": 0,
                "evidence_insufficient": 0,
                "scope_violation": 0,
                "drift_recent_failures": 0,
                "observed_events": 0,
                "window_days": 7,
            },
        },
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    result = runner.invoke(app, ["--json", "ask", "status?"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    data = payload["data"]
    assert data["entrypoint"] == "hook"
    assert data["explicit_command"] is None
    assert data["intent"] == "governance_query"
    assert data["delegation_executed"] is False
    assert data["provider_bound"] is False
