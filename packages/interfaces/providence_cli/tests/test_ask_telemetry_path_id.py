"""Tests for ask telemetry path_id inference (light vs heavy intake).

Approach: mock _emit_ask_telemetry directly to capture the path_id kwarg.
This avoids the CliRunner -> TelemetrySink chain that is fragile across
Python versions and containerised environments.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _run_ask_capture_path_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
) -> str | None:
    """Invoke ask_cmd with key dependencies mocked; return path_id passed to telemetry."""
    from providence_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

    captured_kwargs: list[dict] = []

    def _fake_emit(_event_name: str, **kwargs: object) -> None:
        captured_kwargs.append(kwargs)

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
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry",
            side_effect=_fake_emit,
        ),
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
                len(query) >= 6000,
                "char_count>=6000" if len(query) >= 6000 else "light_input",
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

    if not captured_kwargs:
        return None
    return str(captured_kwargs[0].get("path_id", ""))


def test_path_id_light_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_PATH_ID", raising=False)
    path_id = _run_ask_capture_path_id(tmp_path, monkeypatch, "short query")
    assert path_id == "PATH_A"


def test_path_id_heavy_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_PATH_ID", raising=False)
    path_id = _run_ask_capture_path_id(tmp_path, monkeypatch, "x" * 6001)
    assert path_id == "PATH_B"


def test_path_id_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_PATH_ID", "PATH_CUSTOM")
    path_id = _run_ask_capture_path_id(tmp_path, monkeypatch, "short query")
    assert path_id == "PATH_CUSTOM"
