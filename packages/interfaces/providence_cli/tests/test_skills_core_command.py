"""Integration tests for providence skills list/describe/export CLI commands."""

from __future__ import annotations

import json

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _load_json_output(raw: str) -> dict:
    # Some environments emit a governance soft preface line before JSON output.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def test_skills_list_json_contract() -> None:
    result = runner.invoke(app, ["--json", "skills", "list"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills list"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["state"] == "ok"
    assert data["policy_result"] == "listed"
    assert data["exit_code"] == 0
    assert isinstance(data["skills"], list)


def test_skills_describe_existing() -> None:
    result = runner.invoke(app, ["--json", "skills", "describe", "diagnose"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills describe"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["skill"] == "diagnose"
    assert data["definition"]["schema_version"] == "1.1.0"


def test_skills_describe_missing() -> None:
    result = runner.invoke(app, ["--json", "skills", "describe", "does-not-exist"])
    assert result.exit_code == 1
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "skills describe"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "missing_skill"


def test_skills_export_openai_json() -> None:
    result = runner.invoke(app, ["--json", "skills", "export", "--format", "openai"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills export"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "exported"
    assert data["payload"]["format"] == "openai"
    assert isinstance(data["payload"]["tools"], list)


def test_skills_list_json_uses_canonical_data_payload() -> None:
    result = runner.invoke(app, ["--json", "skills", "list"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills list"
    assert payload["ok"] is True
    assert payload["data"]["policy_result"] == "listed"
    assert "policy_result" not in payload


def test_skills_export_text_mode_langchain() -> None:
    result = runner.invoke(app, ["skills", "export", "--format", "langchain"])
    assert result.exit_code == 0
    assert "{" in result.output


def test_skills_list_text_mode() -> None:
    result = runner.invoke(app, ["skills", "list"])
    assert result.exit_code == 0, result.output
    assert "Available skills:" in result.output


def test_skills_describe_existing_text_mode() -> None:
    result = runner.invoke(app, ["skills", "describe", "diagnose"])
    assert result.exit_code == 0, result.output
    assert "diagnose" in result.output


def test_skills_describe_missing_text_mode() -> None:
    result = runner.invoke(app, ["skills", "describe", "does-not-exist"])
    assert result.exit_code == 1
    assert (
        "not found" in result.output.lower()
        or "not found" in result.stderr_bytes.decode("utf-8", errors="replace").lower()
        if hasattr(result, "stderr_bytes")
        else True
    )
