"""Tests for transport activation rules."""

from __future__ import annotations

import pytest

from providence_integration.contracts.transport_resolution import (
    TransportResolutionError,
    build_transport_aware_request_envelope,
    is_claude_code_context,
    resolve_transport_activation_summary,
    resolve_transport_channel,
)


def test_resolve_transport_channel_explicit_modes() -> None:
    assert resolve_transport_channel("mcp") == "mcp"
    assert resolve_transport_channel("sdk") == "sdk"


def test_resolve_transport_channel_auto_prefers_mcp_in_claude_context() -> None:
    env = {"CLAUDE_SESSION_ID": "abc123"}
    assert is_claude_code_context(env) is True
    assert resolve_transport_channel("auto", env=env) == "mcp"


def test_resolve_transport_channel_auto_defaults_to_sdk_in_python_runtime() -> None:
    assert resolve_transport_channel("auto", env={}) == "sdk"


def test_resolve_transport_summary_includes_context_and_channel() -> None:
    summary = resolve_transport_activation_summary(
        "auto",
        env={"CLAUDE_CODE": "1"},
    )

    assert summary == {
        "activation_mode": "auto",
        "resolved_channel": "mcp",
        "context": "claude-code",
    }


def test_resolve_transport_channel_rejects_invalid_mode() -> None:
    with pytest.raises(TransportResolutionError):
        resolve_transport_channel("invalid")  # type: ignore[arg-type]


def test_build_transport_aware_request_envelope_resolves_channel() -> None:
    request = build_transport_aware_request_envelope(
        activation_mode="auto",
        mode="delegate",
        domain="generic",
        prompt="Delegate this task.",
        trace_id="trace-transport-001",
        env={"CLAUDE_SESSION_ID": "abc123"},
    )

    assert request.channel == "mcp"
    assert request.trace_id == "trace-transport-001"
    assert request.mode == "delegate"
