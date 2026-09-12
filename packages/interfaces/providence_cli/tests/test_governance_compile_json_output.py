"""JSON output contract tests for `governance generate`, `compile`, `audit`, and `handshake`."""

from __future__ import annotations

import json

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _parse_result_json(output: str) -> dict:
    """Parse JSON output allowing CI preamble/noise before canonical envelope."""
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def test_governance_generate_json_uses_canonical_envelope(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "providence_cli.services.governance_generate_handlers.validate_governance_path",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_generate_handlers.load_governance_config",
        lambda _: {"items": [{"id": "M001"}]},
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_generate_handlers.resolve_output_base",
        lambda _output_dir: tmp_path,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_generate_handlers.generate_seeds",
        lambda output_dir, config: ([("copilot", tmp_path / "a.md", "ok")], tmp_path),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_generate_handlers.run_generate_phases",
        lambda output_base, config: (True, True, True),
    )
    result = runner.invoke(app, ["--json", "governance", "generate"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["command"] == "governance generate"


def test_governance_generate_json_error_uses_canonical_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.services.governance_generate_handlers.validate_governance_path",
        lambda _: False,
    )
    result = runner.invoke(app, ["--json", "governance", "generate"])

    assert result.exit_code == 1, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_governance_path"
    assert isinstance(payload["data"], dict)


def test_governance_compile_json_uses_canonical_envelope(monkeypatch) -> None:
    mock_result = {
        "full_pipeline_success": True,
        "phase_1": {
            "core_fingerprint": "a" * 64,
            "core_item_count": 2,
            "client_item_count": 1,
        },
        "phase_2": {
            "core_msgpack_file": "/out/core.msgpack",
            "client_msgpack_file": "/out/client.msgpack",
        },
    }
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.run_compilation",
        lambda profile=None, *, console: mock_result,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.update_profile_hash",
        lambda core_fingerprint, *, console: None,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda path: (True, "ok"),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.emit_compile_telemetry",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.regenerate_seeds",
        lambda *, console: None,
    )
    result = runner.invoke(app, ["--json", "governance", "compile"])

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    assert payload["data"]["summary"]["core_items"] == 2


def test_governance_compile_json_error_uses_canonical_envelope(monkeypatch) -> None:
    mock_result = {
        "full_pipeline_success": True,
        "phase_1": {"core_fingerprint": "a" * 64},
        "phase_2": {},
    }
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.run_compilation",
        lambda profile=None, *, console: mock_result,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.update_profile_hash",
        lambda core_fingerprint, *, console: None,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda path: (False, "bad metadata"),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_compile_handlers.emit_compile_telemetry",
        lambda **_: None,
    )
    result = runner.invoke(app, ["--json", "governance", "compile"])

    assert result.exit_code == 1, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "error"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "artifact_consistency_failed"
    assert isinstance(payload["data"], dict)


def test_governance_audit_json_uses_canonical_envelope(monkeypatch) -> None:
    class _Issue:
        severity = "LOW"
        category = "config"
        message = "ok"
        remediation = "none"

    class _Report:
        ok = True
        score = 95
        issues = [_Issue()]
        metadata = {"runtime": "ok"}

    class _Auditor:
        def perform_audit(self):
            return _Report()

    monkeypatch.setattr("providence_core.governance.audit.GovernanceAuditor", _Auditor)
    result = runner.invoke(app, ["--json", "governance", "audit"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance audit"
    assert payload["ok"] is True
    assert payload["data"]["score"] == 95


def test_governance_handshake_init_json_uses_canonical_envelope(monkeypatch) -> None:
    class _Challenge:
        def to_dict(self):
            return {"session_id": "sess-1", "signature_status": "verified"}

    class _AHP:
        def generate_challenge(self, task_description: str):
            return _Challenge()

    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol", _AHP
    )
    result = runner.invoke(app, ["--json", "governance", "handshake", "--init"])
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance handshake"
    assert payload["ok"] is True
    assert payload["data"]["session_id"] == "sess-1"


def test_governance_handshake_response_json_uses_canonical_envelope(
    monkeypatch,
) -> None:
    class _Result:
        agent_id = "agent-1"
        timestamp = "2026-05-21T10:00:00Z"
        skills_to_use = ["sdd-ask"]

    class _AHP:
        def validate(self, output_mode: str = "silent"):
            return ("HEALTHY", None)

        def complete_handshake(self, response_data):
            return _Result()

    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol", _AHP
    )
    result = runner.invoke(
        app,
        ["--json", "governance", "handshake", "--response", '{"ack":true}'],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance handshake"
    assert payload["ok"] is True
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["agent_id"] == "agent-1"


def test_governance_handshake_response_json_uses_canonical_data_payload(
    monkeypatch,
) -> None:
    class _Result:
        agent_id = "agent-1"
        timestamp = "2026-05-21T10:00:00Z"
        skills_to_use = ["sdd-ask"]

    class _AHP:
        def validate(self, output_mode: str = "silent"):
            return ("HEALTHY", None)

        def complete_handshake(self, response_data):
            return _Result()

    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol", _AHP
    )
    result = runner.invoke(
        app,
        ["--json", "governance", "handshake", "--response", '{"ack":true}'],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "governance handshake"
    assert payload["ok"] is True
    assert payload["data"]["agent_id"] == "agent-1"
