"""Parity fixtures for the external narrative contract v1."""

from __future__ import annotations

import json
from pathlib import Path

from providence_integration.contracts.external_contract_v1 import (
    NarrativeRequestEnvelope,
    NarrativeResponseEnvelope,
)

FIXTURE_DIR = Path(
    "packages/features/providence_integration/tests/fixtures/external_contract_v1"
)


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _normalize_parity(
    model: NarrativeRequestEnvelope | NarrativeResponseEnvelope,
) -> dict[str, object]:
    payload = model.model_dump()
    payload.pop("channel", None)
    telemetry = payload.get("telemetry")
    if isinstance(telemetry, dict):
        telemetry.pop("channel", None)
    return payload


def test_success_fixtures_are_channel_parity_pairs() -> None:
    mcp_request = NarrativeRequestEnvelope.model_validate(
        _load("request_success_mcp.json")
    )
    sdk_request = NarrativeRequestEnvelope.model_validate(
        _load("request_success_sdk.json")
    )
    mcp_response = NarrativeResponseEnvelope.model_validate(
        _load("response_success_mcp.json")
    )
    sdk_response = NarrativeResponseEnvelope.model_validate(
        _load("response_success_sdk.json")
    )

    assert _normalize_parity(mcp_request) == _normalize_parity(sdk_request)
    assert _normalize_parity(mcp_response) == _normalize_parity(sdk_response)
    assert mcp_response.outcome == "success"
    assert sdk_response.outcome == "success"


def test_fallback_fixtures_are_channel_parity_pairs() -> None:
    mcp_request = NarrativeRequestEnvelope.model_validate(
        _load("request_fallback_mcp.json")
    )
    sdk_request = NarrativeRequestEnvelope.model_validate(
        _load("request_fallback_sdk.json")
    )
    mcp_response = NarrativeResponseEnvelope.model_validate(
        _load("response_fallback_mcp.json")
    )
    sdk_response = NarrativeResponseEnvelope.model_validate(
        _load("response_fallback_sdk.json")
    )

    assert _normalize_parity(mcp_request) == _normalize_parity(sdk_request)
    assert _normalize_parity(mcp_response) == _normalize_parity(sdk_response)
    assert mcp_response.outcome == "fallback"
    assert mcp_response.fallback_reason == "LLM_UNAVAILABLE"
    assert sdk_response.telemetry.fallback_reason == "LLM_UNAVAILABLE"
