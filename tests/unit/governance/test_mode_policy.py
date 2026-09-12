"""Unit tests for providence_core.governance.compliance_mode_policy."""

import pytest

from providence_core.governance.compliance_mode_policy import (
    LOGGING_MODE_ACTIVE,
    LOGGING_MODE_PASSIVE,
    LOGGING_MODE_STRICT,
    ComplianceModePolicy,
)

pytestmark = pytest.mark.unit


class TestResolveLoggingMode:
    def test_respects_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "strict")
        assert ComplianceModePolicy.resolve_logging_mode() == LOGGING_MODE_STRICT

    def test_ignores_invalid_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_LOGGING_MODE", "invalid-mode")
        assert ComplianceModePolicy.resolve_logging_mode() == LOGGING_MODE_PASSIVE

    def test_client_profile_defaults_to_passive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert (
            ComplianceModePolicy.resolve_logging_mode("client") == LOGGING_MODE_PASSIVE
        )

    def test_master_profile_defaults_to_active(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert (
            ComplianceModePolicy.resolve_logging_mode("master") == LOGGING_MODE_ACTIVE
        )

    def test_global_default_is_passive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
        assert ComplianceModePolicy.resolve_logging_mode("") == LOGGING_MODE_PASSIVE


class TestShouldPersistEvent:
    def test_active_mode_persists_all(self) -> None:
        assert (
            ComplianceModePolicy.should_persist_event("any_event", LOGGING_MODE_ACTIVE)
            is True
        )

    def test_strict_mode_persists_all(self) -> None:
        assert (
            ComplianceModePolicy.should_persist_event("any_event", LOGGING_MODE_STRICT)
            is True
        )

    def test_passive_mode_filters_non_mandatory(self) -> None:
        assert (
            ComplianceModePolicy.should_persist_event(
                "ask_command", LOGGING_MODE_PASSIVE
            )
            is False
        )

    def test_passive_mode_allows_mandatory(self) -> None:
        assert (
            ComplianceModePolicy.should_persist_event("violation", LOGGING_MODE_PASSIVE)
            is True
        )
        assert (
            ComplianceModePolicy.should_persist_event(
                "workspace_init", LOGGING_MODE_PASSIVE
            )
            is True
        )
        assert (
            ComplianceModePolicy.should_persist_event(
                "compile_complete", LOGGING_MODE_PASSIVE
            )
            is True
        )
        assert (
            ComplianceModePolicy.should_persist_event(
                "governance_checked", LOGGING_MODE_PASSIVE
            )
            is True
        )
