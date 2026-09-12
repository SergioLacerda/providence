"""Transport activation rules for the dual-channel narrative integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from providence_integration.contracts.external_contract_v1 import (
    NarrativeDomain,
    NarrativeMode,
    NarrativePolicy,
    NarrativeRequestEnvelope,
    build_request_envelope,
)

TransportActivationMode = Literal["mcp", "sdk", "auto"]
TransportChannel = Literal["mcp", "sdk"]

_CLAUDE_CONTEXT_MARKERS = (
    "CLAUDECODE",
    "CLAUDE_CODE",
    "CLAUDE_CODE_SANDBOX",
    "CLAUDE_SESSION_ID",
)


class TransportResolutionError(ValueError):
    """Raised when transport activation cannot be resolved."""


def is_claude_code_context(
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return True when the runtime appears to be Claude Code."""

    environment = env or {}
    return any(environment.get(marker) for marker in _CLAUDE_CONTEXT_MARKERS)


def resolve_transport_channel(
    activation_mode: TransportActivationMode,
    *,
    env: Mapping[str, str] | None = None,
) -> TransportChannel:
    """Resolve the concrete transport channel from an activation mode."""

    if activation_mode == "mcp":
        return "mcp"
    if activation_mode == "sdk":
        return "sdk"
    if activation_mode != "auto":
        raise TransportResolutionError(
            f"unsupported activation mode: {activation_mode}"
        )
    return "mcp" if is_claude_code_context(env) else "sdk"


def resolve_transport_activation_summary(
    activation_mode: TransportActivationMode,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a machine-readable summary for diagnostics and logging."""

    channel = resolve_transport_channel(activation_mode, env=env)
    return {
        "activation_mode": activation_mode,
        "resolved_channel": channel,
        "context": "claude-code" if is_claude_code_context(env) else "python-runtime",
    }


def build_transport_aware_request_envelope(
    *,
    activation_mode: TransportActivationMode,
    mode: NarrativeMode,
    domain: NarrativeDomain,
    prompt: str,
    trace_id: str,
    env: Mapping[str, str] | None = None,
    context: dict[str, object] | None = None,
    token_budget: int | None = None,
    contract_version: str = "1",
    policy: NarrativePolicy | None = None,
    governance_context: dict[str, object] | None = None,
) -> NarrativeRequestEnvelope:
    """Build a request envelope after resolving transport activation."""

    return build_request_envelope(
        channel=resolve_transport_channel(activation_mode, env=env),
        mode=mode,
        domain=domain,
        prompt=prompt,
        context=context,
        token_budget=token_budget,
        contract_version=contract_version,
        trace_id=trace_id,
        policy=policy,
        governance_context=governance_context,
    )
