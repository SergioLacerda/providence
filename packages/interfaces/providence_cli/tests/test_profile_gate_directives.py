"""Unit tests for `_collect_gate_directives` branch coverage."""

from __future__ import annotations

from providence_cli.utils.profile_gate_directives import _collect_gate_directives


def test_no_directives_when_healthy_and_not_sensitive() -> None:
    directives = _collect_gate_directives("docs", "", "master", "HEALTHY", False)
    assert directives == []


def test_release_on_client_profile_emits_soft_directive() -> None:
    directives = _collect_gate_directives("release", "", "client", "HEALTHY", True)
    assert len(directives) == 1
    msg, next_step, reason = directives[0]
    assert reason == "profile-release-client"
    assert "SOFT [governance]" in msg
    assert next_step == "use 'sdd --profile master release build'"


def test_wizard_on_master_profile_emits_soft_directive() -> None:
    directives = _collect_gate_directives("wizard", "", "master", "HEALTHY", True)
    assert len(directives) == 1
    msg, _next_step, reason = directives[0]
    assert reason == "profile-wizard-master"
    assert "SOFT [governance]" in msg


def test_ask_not_initialized_emits_hard_directive() -> None:
    directives = _collect_gate_directives("ask", "", "master", "NOT_INITIALIZED", True)
    msg, next_step, reason = directives[0]
    assert reason == "ask-not-initialized"
    assert "HARD [governance]" in msg
    assert (
        next_step
        == "providence governance compile && providence runtime status --force"
    )


def test_ask_partial_emits_soft_directive() -> None:
    directives = _collect_gate_directives("ask", "", "master", "PARTIAL", True)
    reasons = [reason for _msg, _next_step, reason in directives]
    assert "ask-partial" in reasons


def test_misconfigured_state_emits_hard_directive() -> None:
    directives = _collect_gate_directives("docs", "", "master", "MISCONFIGURED", False)
    assert len(directives) == 1
    msg, next_step, reason = directives[0]
    assert reason == "state-misconfigured"
    assert "HARD [governance]" in msg
    assert (
        next_step
        == "run 'providence doctor run' para diagnostico e conserte a governanca"
    )


def test_not_initialized_sensitive_non_wizard_emits_soft_directive() -> None:
    directives = _collect_gate_directives(
        "release", "", "master", "NOT_INITIALIZED", True
    )
    assert len(directives) == 1
    _msg, _next_step, reason = directives[0]
    assert reason == "state-not-initialized"


def test_not_initialized_wizard_command_is_exempt_from_state_directive() -> None:
    directives = _collect_gate_directives(
        "wizard", "", "client", "NOT_INITIALIZED", True
    )
    assert directives == []


def test_not_initialized_non_sensitive_command_emits_no_state_directive() -> None:
    directives = _collect_gate_directives(
        "docs", "", "master", "NOT_INITIALIZED", False
    )
    assert directives == []


def test_partial_sensitive_emits_soft_directive() -> None:
    directives = _collect_gate_directives("release", "", "client", "PARTIAL", True)
    reasons = [reason for _msg, _next_step, reason in directives]
    assert "state-partial-sensitive" in reasons


def test_partial_non_sensitive_emits_no_state_directive() -> None:
    directives = _collect_gate_directives("docs", "", "master", "PARTIAL", False)
    assert directives == []


def test_ask_and_state_directives_can_combine() -> None:
    directives = _collect_gate_directives("ask", "", "master", "PARTIAL", True)
    reasons = [reason for _msg, _next_step, reason in directives]
    assert reasons == ["ask-partial", "state-partial-sensitive"]
