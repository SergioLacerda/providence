"""Contract tests for the canonical providence_cli command envelope schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from providence_cli.shared.contracts import build_error_result, build_ok_result

pytestmark = pytest.mark.contract

SCHEMA_PATH = Path(__file__).parent / "schemas" / "cli_command_envelope.schema.json"


def _schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_matches_schema_contract(payload: dict[str, Any]) -> None:
    assert set(payload) == {
        "status",
        "command",
        "ok",
        "error",
        "data",
        "schema_version",
    }
    assert payload["status"] in {"ok", "error"}
    assert isinstance(payload["command"], str)
    assert payload["command"]
    assert isinstance(payload["ok"], bool)
    assert isinstance(payload["data"], dict)
    assert isinstance(payload["schema_version"], str)
    assert payload["schema_version"].count(".") == 2

    if payload["status"] == "ok":
        assert payload["ok"] is True
        assert payload["error"] is None
        return

    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert set(payload["error"]) == {"code", "message", "details"}
    assert isinstance(payload["error"]["code"], str)
    assert payload["error"]["code"]
    assert isinstance(payload["error"]["message"], str)
    assert payload["error"]["message"]
    assert payload["error"]["details"] is None or isinstance(
        payload["error"]["details"], dict
    )


def test_cli_command_envelope_schema_is_valid_json_schema() -> None:
    schema = _schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "status",
        "command",
        "ok",
        "error",
        "data",
        "schema_version",
    ]
    assert "command_error" in schema["$defs"]


def test_ok_result_matches_cli_command_envelope_schema() -> None:
    payload = build_ok_result("runtime status", {"state": "HEALTHY"})

    _assert_matches_schema_contract(payload)


def test_error_result_matches_cli_command_envelope_schema() -> None:
    payload = build_error_result(
        "runtime status",
        {"state": "NOT_CONNECTED"},
        code="runtime_state_not_healthy",
        message="runtime unavailable",
    )

    _assert_matches_schema_contract(payload)


def test_error_envelope_requires_structured_error() -> None:
    payload = build_ok_result("runtime status", {})
    payload["status"] = "error"
    payload["ok"] = False

    with pytest.raises(AssertionError):
        _assert_matches_schema_contract(payload)
