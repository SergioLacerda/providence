"""Tests for sdd analysis commands (M017  Analysis Plugin Compliance)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from providence_cli.commands.analysis import app as analysis_app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analysis_workspace(tmp_path: Path) -> Path:
    """Create a workspace with .providence/analysis/ state dirs and sample missions."""
    import yaml  # type: ignore[import-untyped]  # noqa: F401

    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".providence" / "analysis" / state).mkdir(parents=True)

    (
        tmp_path / ".providence" / "analysis" / "pending" / "mission-2026-06-01-001.md"
    ).write_text("# Mission", encoding="utf-8")
    (tmp_path / ".providence" / "plugins" / "registry.yaml").write_text(
        "schema_version: '1.0.0'\nplugins: []\n", encoding="utf-8"
    )
    return tmp_path


# ---------------------------------------------------------------------------
# 6.3 sdd analysis list  empty workspace returns no error
# ---------------------------------------------------------------------------


def test_analysis_list_empty_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sdd analysis list returns empty list with no error when workspace has no missions."""
    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".providence" / "analysis" / state).mkdir(parents=True)

    from providence_cli.commands import analysis as analysis_mod

    monkeypatch.setattr(analysis_mod, "resolve_workspace_root", lambda: tmp_path)

    result = runner.invoke(analysis_app, ["list"])
    assert result.exit_code == 0
    assert "No analysis missions found." in result.output


# ---------------------------------------------------------------------------
# 6.5 sdd-ask stays query-only until real delegation exists
# ---------------------------------------------------------------------------


def test_sdd_ask_registry_marks_delegation_not_implemented() -> None:
    """sdd-ask skill must not imply executed provider delegation."""
    from providence_runtime.skills import _REGISTRY

    skill = _REGISTRY.get("sdd-ask")
    assert skill is not None
    assert skill.delegation_policy is not None
    assert skill.delegation_policy.get("enabled") is False
    assert skill.delegation_policy.get("runtime_status") == "not_implemented"
    assert skill.delegation_policy.get("current_contract") == "query_only"


# ---------------------------------------------------------------------------
# 6.6 non-analysis request is not delegated (routing unchanged)
# ---------------------------------------------------------------------------


def test_sdd_ask_registry_preserves_future_delegation_target_as_internal() -> None:
    """Future delegation target is documented without being executable."""
    from providence_runtime.skills import _REGISTRY

    skill = _REGISTRY["sdd-ask"]
    assert skill.delegation_policy is not None
    assert skill.delegation_policy.get("future_delegate_to") == "analysis_orchestrator"
    assert "implementation_handoff" in skill.delegation_policy.get(
        "unsupported_intent_response", ""
    )


# ---------------------------------------------------------------------------
# 6.7 skill metadata and runtime ask output must agree on delegation state
# (spike follow-up: 20260714-sdd-ask-single-entrypoint-spike, I-007)
# ---------------------------------------------------------------------------


def test_sdd_ask_registry_declares_delegation_policy_as_declarative_only() -> None:
    """The skill registry must not read as a working delegation pipeline."""
    from providence_runtime.skills import _REGISTRY

    skill = _REGISTRY["sdd-ask"]
    assert skill.delegation_policy is not None
    assert "declarative_only" in skill.delegation_policy.get("metadata_status", "")


def test_sdd_ask_metadata_and_runtime_output_agree_on_delegation_state() -> None:
    """skill.delegation_policy.enabled and the live ask response's
    delegation_executed/provider_bound fields must never drift apart: both
    must report "no delegation happened" until a real provider path exists.
    """
    from providence_runtime.skills import _REGISTRY

    from providence_cli.services.ask_response_intake import build_intake_contract_fields

    skill = _REGISTRY["sdd-ask"]
    assert skill.delegation_policy is not None
    assert skill.delegation_policy.get("enabled") is False

    fields = build_intake_contract_fields(
        execution_gate="allowed", query="implementar X", skill=None
    )
    assert fields["delegation_executed"] is False
    assert fields["provider_bound"] is False
