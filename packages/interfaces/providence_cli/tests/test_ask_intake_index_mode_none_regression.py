"""Lock-in regression tests: ``intake_index_mode: none`` semantics must not
change while adding phase-level trace-route instrumentation (design doc
SQ-001, plan Task 9).

These tests do not exercise new behavior. They pin down the exact gating
rule implemented in ``providence_cli.services.ask_response.emit_ask_text_response``
and ``providence_cli.services.ask_response_json`` (both derive
``gate_blocked = not session.organize_used and session.organize_reason !=
"light_input"``):

- A ``light_input`` intake (short query, organize skipped on purpose) must
  still resolve to ``execution_gate == "allowed"``.
- A non-light-input query where organize/indexing did not run must still
  resolve to ``execution_gate == "blocked"``, exactly as before.

Pattern follows ``test_ask_telemetry_path_id.py``: mock the ask pipeline's
side-effecting dependencies (telemetry, profile resolution, runtime cache,
session upsert, budget/handshake guards) and drive the real ``ask_cmd``
entrypoint, then inspect the plain-text stdout it emits (the same surface a
human running ``providence ask`` sees, as verified live before writing this test).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _run_ask_capture_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    query: str,
    *,
    organize_used: bool,
    organize_reason: str,
) -> str:
    """Invoke ask_cmd with key dependencies mocked; return captured stdout."""
    from providence_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.delenv("SDD_PATH_ID", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

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

    with (
        patch("providence_cli.commands._ask_backend._emit_ask_telemetry"),
        patch(
            "providence_core.utils.environment.resolve_profile",
            return_value=fake_profile,
        ),
        patch(
            "providence_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands._ask_backend._get_profile_state",
            return_value=("client", "HEALTHY"),
        ),
        patch("providence_cli.commands._ask_backend._guard_budget_breach"),
        patch("providence_cli.commands._ask_backend._guard_handshake"),
        patch("providence_cli.commands._ask_backend._write_runtime_cache"),
        patch("providence_cli.commands._ask_backend._store_routing_decision"),
        patch("providence_cli.commands._ask_backend._upsert_ask_session"),
        patch("providence_cli.commands._ask_backend._emit_state_warnings"),
        patch(
            "providence_cli.services.ask_snapshot.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": False,
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(
                organize_used,
                organize_reason,
                None,
                0,
                "indexed_only",
                None,
            ),
        ),
        patch(
            "providence_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
    ):
        ask_cmd(query=query)

    return capsys.readouterr().out


def test_light_input_with_execution_gate_allowed_is_not_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A short query that organize legitimately skipped (``light_input``)
    must resolve to ``intake_index_mode: none`` + ``execution_gate:
    allowed``  not blocked. This mirrors the real ``providence ask "test"``
    behavior observed on the live CLI.
    """
    stdout = _run_ask_capture_stdout(
        tmp_path,
        monkeypatch,
        capsys,
        "short query",
        organize_used=False,
        organize_reason="light_input",
    )

    assert "intake_index_mode : none" in stdout
    assert "execution_gate    : allowed" in stdout
    assert "gate_reason" not in stdout
    assert "intake_skipped" not in stdout


def test_implementation_intent_reports_query_only_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Implementation intent must not look like executed provider delegation."""
    stdout = _run_ask_capture_stdout(
        tmp_path,
        monkeypatch,
        capsys,
        "implementar demanda .analysis/refined/example/tasks.md",
        organize_used=False,
        organize_reason="light_input",
    )

    assert "execution_gate    : allowed" in stdout
    assert "providence ask contract  : governance-context query only" in stdout
    assert "delegation_status : not_executed" in stdout
    assert "implementation_handoff" in stdout


def test_non_light_input_missing_organize_index_remains_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-light-input query where organize/indexing did not run must
    remain blocked, exactly as before trace-route instrumentation was
    added. Uses a non-``light_input`` skip reason (e.g. an indexing
    failure) with ``organize_used=False`` to reproduce the missing-index
    scenario without depending on the 6000-char heavy-intake threshold.
    """
    stdout = _run_ask_capture_stdout(
        tmp_path,
        monkeypatch,
        capsys,
        "a query that should have been indexed but was not",
        organize_used=False,
        organize_reason="index_unavailable",
    )

    assert "intake_index_mode : none" in stdout
    assert "execution_gate    : blocked" in stdout
    assert "gate_reason       : intake_index_mode=none" in stdout
    assert "intake_skipped    : index_unavailable" in stdout


def test_implementation_intent_text_output_states_no_provider_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Spike follow-up (20260714-sdd-ask-single-entrypoint-spike): text output
    must state explicitly that delegation was not executed and no provider is
    bound, alongside the existing implementation_handoff signal."""
    monkeypatch.delenv("SDD_ASK_ENTRYPOINT", raising=False)
    stdout = _run_ask_capture_stdout(
        tmp_path,
        monkeypatch,
        capsys,
        "implementar demanda .analysis/refined/example/tasks.md",
        organize_used=False,
        organize_reason="light_input",
    )

    assert "providence ask contract  : governance-context query only" in stdout
    assert "delegation_status : not_executed" in stdout
    assert "implementation_handoff" in stdout
    assert "delegation_executed : false" in stdout
    assert "provider_bound    : false" in stdout
    assert "intent            : implementation_request" in stdout
    assert "entrypoint        : explicit_command" in stdout
    assert "next_action       : create_execution_contract" in stdout


def test_governance_query_text_output_reports_hook_entrypoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When SDD_ASK_ENTRYPOINT=hook, text output reflects the hook origin
    without implying a separate/duplicate semantic action."""
    monkeypatch.setenv("SDD_ASK_ENTRYPOINT", "hook")
    stdout = _run_ask_capture_stdout(
        tmp_path,
        monkeypatch,
        capsys,
        "short query",
        organize_used=False,
        organize_reason="light_input",
    )

    assert "entrypoint        : hook" in stdout
    assert "intent            : governance_query" in stdout
    assert "next_action       : answer_from_governance" in stdout
