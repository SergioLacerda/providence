"""Tests for the external narrative contract v1 models and helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from providence_integration.contracts.external_contract_v1 import (
    CONTRACT_VERSION_V1,
    ContractVersionMismatchError,
    ModeNotSupportedError,
    NarrativePolicy,
    NarrativeRequestEnvelope,
    NarrativeRequestInput,
    NarrativeResponseEnvelope,
    NarrativeResponseResult,
    NarrativeTelemetry,
    build_request_envelope,
    build_response_envelope,
    choose_execution_path,
    resolve_fallback_outcome,
    validate_request_compatibility,
)


def _request(*, channel: str = "mcp", mode: str = "refine-only"):
    return build_request_envelope(
        channel=channel,  # type: ignore[arg-type]
        mode=mode,  # type: ignore[arg-type]
        domain="coding",
        prompt="Refine the prompt",
        context={"source": "test"},
        token_budget=4000,
        trace_id="trace-123",
    )


def test_request_envelope_validates_and_keeps_required_fields() -> None:
    request = _request()

    assert request.contract_version == CONTRACT_VERSION_V1
    assert request.channel == "mcp"
    assert request.mode == "refine-only"
    assert request.input.prompt == "Refine the prompt"
    assert request.input.token_budget == 4000
    assert request.policy.fallback_on_error is True


def test_request_parity_between_channels() -> None:
    mcp_request = _request(channel="mcp")
    sdk_request = _request(channel="sdk")

    assert mcp_request.model_dump(exclude={"channel"}) == sdk_request.model_dump(
        exclude={"channel"}
    )


def test_request_compatibility_rejects_version_and_mode() -> None:
    request = NarrativeRequestEnvelope.model_construct(
        contract_version="2",
        trace_id="trace-123",
        channel="mcp",
        mode="refine-only",
        domain="coding",
        input=NarrativeRequestInput.model_construct(
            prompt="x", context={}, token_budget=1
        ),
        policy=NarrativePolicy.model_construct(),
        governance_context={},
    )

    with pytest.raises(ContractVersionMismatchError):
        validate_request_compatibility(request)

    request_mode = request.model_copy(update={"contract_version": CONTRACT_VERSION_V1})
    request_mode = request_mode.model_copy(update={"mode": "batch"})  # type: ignore[arg-type]

    with pytest.raises(ModeNotSupportedError):
        validate_request_compatibility(
            request_mode, supported_modes={"refine-only", "delegate"}
        )


def test_response_envelope_requires_fallback_reason_and_aligns_telemetry() -> None:
    request = _request(mode="delegate")
    telemetry = NarrativeTelemetry(
        trace_id=request.trace_id,
        channel=request.channel,
        mode=request.mode,
        latency_ms=42,
        outcome="fallback",
        fallback_reason="SEMANTIC_TIMEOUT",
    )
    response = build_response_envelope(
        request=request,
        outcome="fallback",
        latency_ms=42,
        result={
            "refined_prompt": "Refined prompt",
            "response": "Executor output",
            "compression_ratio": 0.5,
            "warnings": ["degraded"],
        },
        telemetry=telemetry,
        fallback_reason="SEMANTIC_TIMEOUT",
    )

    assert response.outcome == "fallback"
    assert response.fallback_reason == "SEMANTIC_TIMEOUT"
    assert response.telemetry.outcome == "fallback"

    with pytest.raises(ValidationError):
        NarrativeResponseEnvelope(
            contract_version=request.contract_version,
            trace_id=request.trace_id,
            channel=request.channel,
            mode=request.mode,
            outcome="fallback",
            latency_ms=1,
            result=NarrativeResponseResult(
                refined_prompt="Refined prompt",
                response="Executor output",
            ),
            telemetry=NarrativeTelemetry(
                trace_id=request.trace_id,
                channel=request.channel,
                mode=request.mode,
                latency_ms=1,
                outcome="fallback",
                fallback_reason="SEMANTIC_TIMEOUT",
            ),
        )


def test_choose_execution_path_prefers_internal_when_external_disabled() -> None:
    assert (
        choose_execution_path(allow_external_delegation=False, mode="delegate")
        == "internal"
    )
    assert (
        choose_execution_path(allow_external_delegation=True, mode="delegate")
        == "external"
    )
    assert (
        choose_execution_path(allow_external_delegation=True, mode="refine-only")
        == "internal"
    )


def test_fallback_outcome_is_deterministic() -> None:
    assert resolve_fallback_outcome(
        contract_version_supported=False,
        executor_available=True,
        timeout_occurred=False,
        unsafe_response=False,
        fallback_on_error=True,
    ) == ("error", "CONTRACT_VERSION_MISMATCH")

    assert resolve_fallback_outcome(
        contract_version_supported=True,
        executor_available=False,
        timeout_occurred=False,
        unsafe_response=False,
        fallback_on_error=True,
    ) == ("fallback", "LLM_UNAVAILABLE")

    assert resolve_fallback_outcome(
        contract_version_supported=True,
        executor_available=True,
        timeout_occurred=True,
        unsafe_response=False,
        fallback_on_error=False,
    ) == ("error", "SEMANTIC_TIMEOUT")

    assert resolve_fallback_outcome(
        contract_version_supported=True,
        executor_available=True,
        timeout_occurred=False,
        unsafe_response=True,
        fallback_on_error=True,
    ) == ("error", "unsafe_response")
