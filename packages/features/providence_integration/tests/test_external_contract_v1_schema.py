"""Tests for the external contract v1 schema files."""

from __future__ import annotations

import json
from pathlib import Path


def _load_schema(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_request_and_response_schema_files_exist_and_match_contract() -> None:
    base = Path(
        "packages/features/providence_integration/src/providence_integration/contracts"
    )
    request_schema = _load_schema(base / "external_contract_v1.request.schema.json")
    response_schema = _load_schema(base / "external_contract_v1.response.schema.json")

    assert request_schema["properties"]["contract_version"]["const"] == "1"
    assert request_schema["properties"]["channel"]["enum"] == ["mcp", "sdk"]
    assert request_schema["properties"]["mode"]["enum"] == [
        "refine-only",
        "delegate",
    ]
    assert request_schema["properties"]["domain"]["enum"] == ["coding", "generic"]
    assert "fallback_reason" in response_schema["properties"]
    assert response_schema["properties"]["telemetry"]["allOf"][0]["then"][
        "required"
    ] == ["fallback_reason"]
