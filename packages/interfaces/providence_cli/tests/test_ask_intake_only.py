"""Tests for `providence ask --intake-only`  the cheap hook-mode profile.

Spike follow-up: 20260714-sdd-ask-single-entrypoint-spike (A-005/I-005/I-006).
`--intake-only` must compute execution_gate/intake_index_mode/intent without
loading the full compiled-governance snapshot or emitting telemetry, and must
never claim the full `providence ask` behavior changed for callers that omit the flag.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _parse_result_json(output: str) -> dict:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def _patch_cheap_session(tmp_path: Path, *, organize_used: bool, organize_reason: str):
    fake_profile = MagicMock()
    fake_profile.as_dict.return_value = {
        "profile": "client",
        "name": "test",
        "workspace_id": "test-ws",
        "core_hash": "abc",
        "root": tmp_path,
        "is_master": False,
        "is_client": True,
    }
    return (
        patch(
            "providence_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_core.utils.environment.resolve_profile",
            return_value=fake_profile,
        ),
        patch(
            "providence_cli.commands._ask_backend._get_profile_state",
            return_value=("client", "HEALTHY"),
        ),
        patch("providence_cli.commands._ask_backend._guard_budget_breach"),
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(organize_used, organize_reason, "", 0, "indexed_only", None),
        ),
    )


def _write_runtime_handbook(root: Path) -> None:
    handbook_dir = root / ".providence" / "source" / "handbook"
    context_item = handbook_dir / "context-loading" / "context-flow.yaml"
    runbook_item = handbook_dir / "runbooks" / "index.yaml"
    context_item.parent.mkdir(parents=True)
    runbook_item.parent.mkdir(parents=True)
    context_item.write_text(
        """
id: HBK-CONTEXT-LOADING
title: Context Flow
kind: decision_model
status: active
source_doc: docs/cognition/context-loading/context_flow.md
mandate_refs: [M003, M005]
task_types: [planning, implementation, diagnosis]
operation_phases: [context_loading, planning]
load_policy:
  mode: selective
  max_tokens: 700
summary: Context routing.
""".lstrip(),
        encoding="utf-8",
    )
    runbook_item.write_text(
        """
id: HBK-RUNBOOK-CONSULTATION
title: Runbook Consultation
kind: decision_model
status: active
source_doc: docs/runbooks/README.md
mandate_refs: [M003, M005]
task_types: [planning, implementation, diagnosis]
operation_phases: [context_loading, planning]
load_policy:
  mode: selective
  max_tokens: 900
summary: Runtime runbook selector.
""".lstrip(),
        encoding="utf-8",
    )
    (handbook_dir / "index.yaml").write_text(
        """
schema_version: '1'
items:
  - id: HBK-CONTEXT-LOADING
    title: Context Flow
    source_doc: docs/cognition/context-loading/context_flow.md
    runtime_doc: .providence/source/handbook/context-loading/context-flow.yaml
    mandate_refs: [M003, M005]
    task_types: [planning, implementation, diagnosis]
    operation_phases: [context_loading, planning]
  - id: HBK-RUNBOOK-CONSULTATION
    title: Runbook Consultation
    source_doc: docs/runbooks/README.md
    runtime_doc: .providence/source/handbook/runbooks/index.yaml
    mandate_refs: [M003, M005]
    task_types: [planning, implementation, diagnosis]
    operation_phases: [context_loading, planning]
""".lstrip(),
        encoding="utf-8",
    )


def test_intake_only_text_response_skips_governance_snapshot_and_telemetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from providence_cli.commands._ask_backend import ask_cmd

    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot"
        ) as mock_snapshot,
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry"
        ) as mock_telemetry,
        patch(
            "providence_cli.commands._ask_backend._write_runtime_cache"
        ) as mock_cache,
        patch(
            "providence_cli.commands._ask_backend._upsert_ask_session"
        ) as mock_upsert,
    ):
        ask_cmd(query="short query", intake_only=True)

    mock_snapshot.assert_not_called()
    mock_telemetry.assert_not_called()
    mock_cache.assert_not_called()
    mock_upsert.assert_not_called()

    stdout = capsys.readouterr().out
    assert "execution_gate    : allowed" in stdout
    assert "intake_index_mode : none" in stdout
    assert "intake_profile    : cheap" in stdout
    assert "intent            : governance_query" in stdout
    assert "delegation_executed : false" in stdout
    assert "provider_bound    : false" in stdout
    assert "runtime_handbook" not in stdout


def test_intake_only_json_response_matches_full_gate_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_ASK_ENTRYPOINT", raising=False)
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="index_unavailable"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol.validate",
            return_value=("HEALTHY", None),
        ),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot"
        ) as mock_snapshot,
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry"
        ) as mock_telemetry,
        patch("providence_cli.commands._ask_backend._write_runtime_cache"),
        patch("providence_cli.commands._ask_backend._upsert_ask_session"),
    ):
        result = runner.invoke(
            app, ["--json", "ask", "--intake-only", "implementar mudanca"]
        )

    assert result.exit_code == 0, result.output
    mock_snapshot.assert_not_called()
    mock_telemetry.assert_not_called()

    payload = _parse_result_json(result.output)
    data = payload["data"]
    assert data["execution_gate"] == "blocked"
    assert data["intake_index_mode"] == "none"
    assert data["intake_profile"] == "cheap"
    assert data["intent"] == "implementation_request"
    assert data["delegation_executed"] is False
    assert data["provider_bound"] is False
    # The cheap profile must not fabricate governance fields it never loaded.
    assert "fingerprint" not in data
    assert "runtime_handbook" not in data


def test_intake_only_text_response_surfaces_compact_runbook_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from providence_cli.commands._ask_backend import ask_cmd

    _write_runtime_handbook(tmp_path)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot"
        ) as mock_snapshot,
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry"
        ) as mock_telemetry,
    ):
        ask_cmd(query="diagnosticar falha de release asset", intake_only=True)

    mock_snapshot.assert_not_called()
    mock_telemetry.assert_not_called()

    stdout = capsys.readouterr().out
    assert (
        "runtime_handbook : HBK-RUNBOOK-CONSULTATION -> "
        ".providence/source/handbook/runbooks/index.yaml"
    ) in stdout
    assert "runbook_reason   : runtime runbook signal matched:" in stdout
    assert "delegation_executed : false" in stdout
    assert "provider_bound    : false" in stdout


def test_intake_only_json_response_surfaces_runtime_only_runbook_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_runtime_handbook(tmp_path)
    assert not (tmp_path / "docs").exists()
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol.validate",
            return_value=("HEALTHY", None),
        ),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot"
        ) as mock_snapshot,
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry"
        ) as mock_telemetry,
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "ask",
                "--intake-only",
                "diagnosticar runtime drift",
            ],
        )

    assert result.exit_code == 0, result.output
    mock_snapshot.assert_not_called()
    mock_telemetry.assert_not_called()

    payload = _parse_result_json(result.output)
    data = payload["data"]
    hint = data["runtime_handbook_hint"]
    assert hint["status"] == "matched"
    assert hint["diagnostic"] == "handbook_match=2"
    assert hint["id"] == "HBK-RUNBOOK-CONSULTATION"
    assert hint["runtime_doc"] == ".providence/source/handbook/runbooks/index.yaml"
    assert hint["relevance_reason"].startswith("runtime runbook signal matched:")
    assert "source_doc" not in hint
    assert "runtime_handbook" not in data
    assert data["delegation_executed"] is False
    assert data["provider_bound"] is False


def test_intake_only_json_response_reports_missing_handbook_for_runbook_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol.validate",
            return_value=("HEALTHY", None),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "ask",
                "--intake-only",
                "diagnosticar falha operacional",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = _parse_result_json(result.output)
    hint = payload["data"]["runtime_handbook_hint"]
    assert hint == {
        "status": "missing",
        "diagnostic": "handbook_index_missing",
        "relevance_reason": "runtime runbook signal matched: diagnos, falha",
    }


def test_default_ask_without_intake_only_flag_still_loads_full_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full explicit `providence ask` behavior (no --intake-only) is unchanged."""
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol.validate",
            return_value=("HEALTHY", None),
        ),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
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
        ) as mock_snapshot,
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry"
        ) as mock_telemetry,
        patch("providence_cli.commands._ask_backend._write_runtime_cache"),
        patch("providence_cli.commands._ask_backend._store_routing_decision"),
        patch("providence_cli.commands._ask_backend._upsert_ask_session"),
    ):
        result = runner.invoke(app, ["--json", "ask", "status?"])

    assert result.exit_code == 0, result.output
    mock_snapshot.assert_called_once()
    assert mock_telemetry.call_count >= 1
