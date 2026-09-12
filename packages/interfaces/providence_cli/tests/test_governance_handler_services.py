from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from providence_cli.services.governance_artifact_handlers import (
    emit_generate_invalid_path_error,
    emit_generate_missing_items_error,
    render_generate_table,
    render_governance_compile_table,
    run_governance_compile_json,
    run_governance_generate_json,
)
from providence_cli.services.governance_runtime_handlers import (
    run_governance_audit,
    run_governance_handshake,
)


@dataclass
class _Issue:
    severity: str
    category: str
    message: str
    remediation: str


@dataclass
class _Report:
    ok: bool
    score: int
    issues: list[_Issue]
    metadata: dict[str, object] | None = None


def test_run_governance_audit_json_ok() -> None:
    report = _Report(ok=True, score=95, issues=[])

    with (
        patch("providence_core.governance.audit.GovernanceAuditor") as auditor_cls,
        patch(
            "providence_cli.services.governance_runtime_handlers.emit_json"
        ) as emit_json,
    ):
        auditor_cls.return_value.perform_audit.return_value = report
        run_governance_audit(verbose=False, output_json=True, console=Console())

    emit_json.assert_called_once()
    payload = emit_json.call_args.args[0]
    assert payload["ok"] is True
    assert payload["command"] == "governance audit"


def test_run_governance_audit_json_error() -> None:
    report = _Report(
        ok=False,
        score=42,
        issues=[_Issue("HIGH", "auth", "bad signature", "fix keyring")],
    )
    with (
        patch("providence_core.governance.audit.GovernanceAuditor") as auditor_cls,
        patch(
            "providence_cli.services.governance_runtime_handlers.emit_json"
        ) as emit_json,
    ):
        auditor_cls.return_value.perform_audit.return_value = report
        run_governance_audit(verbose=False, output_json=True, console=Console())

    payload = emit_json.call_args.args[0]
    assert payload["ok"] is False
    assert payload["error"]["code"] == "governance_audit_failed"


def test_run_governance_audit_text_blocked_exits() -> None:
    report = _Report(
        ok=False,
        score=12,
        issues=[_Issue("CRITICAL", "integrity", "drift", "recompile")],
    )
    with patch("providence_core.governance.audit.GovernanceAuditor") as auditor_cls:
        auditor_cls.return_value.perform_audit.return_value = report
        with pytest.raises(typer.Exit):
            run_governance_audit(verbose=True, output_json=False, console=Console())


def test_run_governance_handshake_init_json() -> None:
    challenge = SimpleNamespace(
        session_id="s1",
        active_mandates=["M001"],
        available_skills=[{"name": "sdd-ask"}],
        signature_status="verified",
        to_dict=lambda: {"session_id": "s1"},
    )
    protocol = SimpleNamespace(generate_challenge=lambda task_description: challenge)
    with (
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            return_value=protocol,
        ),
        patch(
            "providence_cli.services.governance_runtime_handlers.emit_json"
        ) as emit_json,
    ):
        run_governance_handshake(
            response=None,
            init=True,
            task_desc="task",
            output_mode="json",
            output_json=True,
            console=Console(),
        )
    payload = emit_json.call_args.args[0]
    assert payload["ok"] is True
    assert payload["data"]["session_id"] == "s1"


def test_run_governance_handshake_invalid_json_exits() -> None:
    with pytest.raises(typer.Exit):
        run_governance_handshake(
            response="{invalid",
            init=False,
            task_desc="task",
            output_mode="json",
            output_json=False,
            console=Console(),
        )


def test_run_governance_handshake_response_json_mode() -> None:
    result = SimpleNamespace(
        agent_id="a1",
        skills_to_use=["sdd-ask"],
        acknowledged_signature=True,
        compliance_declaration=True,
        timestamp="2026-05-21T00:00:00Z",
    )
    protocol = SimpleNamespace(
        validate=lambda output_mode: None,
        complete_handshake=lambda response_data: result,
    )
    with (
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            return_value=protocol,
        ),
        patch(
            "providence_cli.services.governance_runtime_handlers.emit_json"
        ) as emit_json,
    ):
        run_governance_handshake(
            response='{"agent_id":"a1"}',
            init=False,
            task_desc="task",
            output_mode="silent",
            output_json=False,
            console=Console(),
        )
    payload = emit_json.call_args.args[0]
    assert payload["ok"] is True
    assert payload["command"] == "governance handshake"


def test_compile_json_success_and_error() -> None:
    ok_payload, ok_err = run_governance_compile_json(
        phase_1={"core_item_count": 1, "client_item_count": 2},
        phase_2={"core_msgpack_file": "a", "client_msgpack_file": "b"},
        core_fingerprint="abcd",
        consistency_ok=True,
        consistency_reason="",
    )
    assert ok_err is False
    assert ok_payload["ok"] is True

    err_payload, is_err = run_governance_compile_json(
        phase_1={"core_item_count": 1, "client_item_count": 2},
        phase_2={"core_msgpack_file": "a", "client_msgpack_file": "b"},
        core_fingerprint="abcd",
        consistency_ok=False,
        consistency_reason="hash mismatch",
    )
    assert is_err is True
    assert err_payload["error"]["code"] == "artifact_consistency_failed"


def test_generate_json_payload_shape() -> None:
    payload = run_governance_generate_json(
        resolved_path=".providence/compiled",
        output_base=Path("/tmp"),
        seeds_dir=Path("/tmp/.vscode/agents"),
        rows=[{"agent_template": "copilot", "location": "x", "status": "ok"}],
        skills_generated=True,
        skill_index_generated=True,
        cli_index_generated=True,
    )
    assert payload["ok"] is True
    assert payload["command"] == "governance generate"


def test_generate_error_emitters_exit() -> None:
    with pytest.raises(typer.Exit):
        emit_generate_invalid_path_error(resolved_path="bad", output_dir=".")
    with pytest.raises(typer.Exit):
        emit_generate_missing_items_error(resolved_path="bad", output_dir=".")


def test_render_functions_smoke() -> None:
    console = Console()
    render_governance_compile_table(
        console=console,
        phase_1={"core_item_count": 1, "client_item_count": 2},
        phase_2={"core_msgpack_file": "a", "client_msgpack_file": "b"},
        core_fingerprint="abcd",
    )
    render_generate_table(
        console=console,
        rows=[{"agent_template": "copilot", "location": "x", "status": "ok"}],
        seeds_dir=Path("/tmp/.vscode/agents"),
    )
