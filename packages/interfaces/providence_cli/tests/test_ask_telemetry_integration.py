"""Integration tests for ask telemetry: degraded reason caching, token source, and dossier context."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from providence_cli.main import app


def _make_fake_ahp(state: str):
    class _FakeAHP:
        def __init__(self, project_root=None):
            self.skill_profile = "default"

        def validate(self, output_mode="silent", force_recheck=False):
            class _R:
                confidence = 90.0

            return state, _R()

        def is_handshake_valid(self, strict=False):
            return True

    return _FakeAHP


def test_ask_runtime_cache_uses_effective_degraded_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

    captured_emit: list[dict] = []
    captured_cache: list[dict] = []

    def _fake_emit(_event_name: str, **kwargs: object) -> None:
        captured_emit.append(kwargs)

    def _fake_cache(
        _workspace_root: Path,
        last_ask: dict[str, object],
        *_args: object,
        **_kwargs: object,
    ) -> None:
        captured_cache.append(last_ask)

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
        patch(
            "providence_cli.commands._ask_backend._write_runtime_cache_and_routing_decision",
            _fake_cache,
        ),
        patch("providence_cli.commands._ask_backend._upsert_ask_session"),
        patch("providence_cli.commands._ask_backend._emit_state_warnings"),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "query_hash": "bed9bd3e",
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": False,
                "degraded": True,
                "degrade_reason": "",
                "trust_source": "none",
                "drift_detected": False,
                "root_seed_drift_detected": False,
                "learning_signals": {},
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light_input", None, 0, "indexed_only", None),
        ),
        patch(
            "providence_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
    ):
        ask_cmd(query="short query")

    assert captured_emit
    assert captured_cache
    emit_reason = captured_emit[0]["extra_details"]["degraded_reason"]
    cache_reason = captured_cache[0]["degraded_reason"]
    assert emit_reason == "artifact_unverified"
    assert cache_reason == emit_reason


def test_ask_telemetry_emits_token_source_estimated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from providence_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)

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
                "root_seed_drift_detected": False,
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light_input", None, 0, "indexed_only", None),
        ),
        patch(
            "providence_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
    ):
        ask_cmd(query="short query")

    assert captured_kwargs
    extra_details = captured_kwargs[0].get("extra_details", {})
    assert isinstance(extra_details, dict)
    assert extra_details.get("token_source") == "estimated"


def test_ask_json_context_prefers_summary_full_when_env_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SDD_ASK_PREFER_FULL_SUMMARY", "true")
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    runner = CliRunner()

    captured_requests: list[object] = []

    class _FakeContextLoader:
        def load_result(self, request):  # noqa: ANN001
            from types import SimpleNamespace

            captured_requests.append(request)
            return SimpleNamespace(
                items=["M001: Rule"],
                source="artifact",
                matched=1,
                truncated=False,
                bytes_loaded=12,
                compression_ratio=None,
            )

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
        patch("providence_cli.commands._ask_backend._emit_ask_telemetry"),
        patch(
            "providence_cli.services.ask_snapshot.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": False,
                "root_seed_drift_detected": False,
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light_input", None, 0, "indexed_only", None),
        ),
        patch(
            "providence_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
        patch("providence_runtime.context.ContextLoader", _FakeContextLoader),
        patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            _make_fake_ahp("HEALTHY"),
        ),
    ):
        result = runner.invoke(app, ["--json", "ask", "--dossier", "status?"])

    assert result.exit_code == 0, result.output

    assert captured_requests, "ContextRequest should be created in --json flow"
    assert bool(getattr(captured_requests[0], "prefer_full_summary", False)) is True
