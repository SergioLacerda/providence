from __future__ import annotations

import pytest
from providence_runtime.intake import (
    ASK_ENTRYPOINT_ENV,
    build_intake_contract_fields,
    classify_ask_intent,
    resolve_ask_entrypoint,
    resolve_ask_next_action,
    resolve_execution_gate,
)
from providence_runtime.intake.intent import _looks_like_implementation_intent


@pytest.mark.parametrize(
    "query",
    [
        "please implement this feature",
        "corrigir o bug no handler",
        "aplicar a mudança sugerida",
        "make the change described above",
    ],
)
def test_looks_like_implementation_intent_true(query: str) -> None:
    assert _looks_like_implementation_intent(query) is True


def test_looks_like_implementation_intent_false() -> None:
    assert _looks_like_implementation_intent("what does this module do?") is False


def test_classify_ask_intent_implementation_request() -> None:
    assert classify_ask_intent("implement the new endpoint") == "implementation_request"


def test_classify_ask_intent_planning_skill_overrides_query() -> None:
    assert classify_ask_intent("random query", skill="planning") == "planning_request"


@pytest.mark.parametrize(
    "skill",
    ["diagnosis", "diagnose", "debug", "stabilize"],
)
def test_classify_ask_intent_analysis_skill(skill: str) -> None:
    assert classify_ask_intent("random query", skill=skill) == "analysis_request"


def test_classify_ask_intent_analysis_keyword_in_query() -> None:
    assert classify_ask_intent("why did this fail with an error?") == "analysis_request"


def test_classify_ask_intent_planning_keyword_in_query() -> None:
    assert classify_ask_intent("draft a design proposal") == "planning_request"


def test_classify_ask_intent_default_governance_query() -> None:
    assert classify_ask_intent("what mandates are active?") == "governance_query"


def test_resolve_ask_entrypoint_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ASK_ENTRYPOINT_ENV, "hook")
    assert resolve_ask_entrypoint() == ("hook", None)


def test_resolve_ask_entrypoint_explicit_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ASK_ENTRYPOINT_ENV, raising=False)
    assert resolve_ask_entrypoint() == ("explicit_command", "sdd-ask")


def test_resolve_ask_entrypoint_explicit_when_not_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ASK_ENTRYPOINT_ENV, "slash-command")
    assert resolve_ask_entrypoint() == ("explicit_command", "sdd-ask")


def test_resolve_ask_next_action_blocked_gate_wins() -> None:
    assert (
        resolve_ask_next_action("blocked", "implementation_request")
        == "acknowledge_context"
    )


def test_resolve_ask_next_action_implementation_request() -> None:
    assert (
        resolve_ask_next_action("allowed", "implementation_request")
        == "create_execution_contract"
    )


def test_resolve_ask_next_action_default() -> None:
    assert (
        resolve_ask_next_action("allowed", "governance_query")
        == "answer_from_governance"
    )


def test_resolve_execution_gate_blocked_without_organize() -> None:
    assert (
        resolve_execution_gate(organize_used=False, organize_reason="index_missing")
        == "blocked"
    )


def test_resolve_execution_gate_allowed_when_light_input() -> None:
    assert (
        resolve_execution_gate(organize_used=False, organize_reason="light_input")
        == "allowed"
    )


def test_resolve_execution_gate_allowed_when_organize_used() -> None:
    assert (
        resolve_execution_gate(organize_used=True, organize_reason="indexed")
        == "allowed"
    )


def test_build_intake_contract_fields_implementation_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ASK_ENTRYPOINT_ENV, raising=False)
    fields = build_intake_contract_fields(
        execution_gate="allowed", query="implement the fix", skill=None
    )
    assert fields == {
        "schema_version": "1.0",
        "origin": "cli_intake",
        "intent": "implementation_request",
        "entrypoint": "explicit_command",
        "explicit_command": "sdd-ask",
        "next_action": "create_execution_contract",
        "delegation_executed": False,
        "provider_bound": False,
        "handoff_owner": "calling_agent",
        "requires_user_approval": True,
    }


def test_build_intake_contract_fields_governance_query_not_approval_gated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ASK_ENTRYPOINT_ENV, "hook")
    fields = build_intake_contract_fields(
        execution_gate="allowed", query="what mandates are active?", skill=None
    )
    assert fields["intent"] == "governance_query"
    assert fields["entrypoint"] == "hook"
    assert fields["explicit_command"] is None
    assert fields["next_action"] == "answer_from_governance"
    assert fields["requires_user_approval"] is False
    assert fields["schema_version"] == "1.0"
    assert fields["origin"] == "cli_intake"


def test_build_intake_contract_fields_blocked_gate_forces_acknowledge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ASK_ENTRYPOINT_ENV, raising=False)
    fields = build_intake_contract_fields(
        execution_gate="blocked", query="implement the fix", skill=None
    )
    assert fields["next_action"] == "acknowledge_context"
