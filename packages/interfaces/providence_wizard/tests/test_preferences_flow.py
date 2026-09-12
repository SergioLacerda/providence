"""Tests for the application-level preference flow."""

from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.application._interactive_wizard_constants import (
    _HANDSHAKE_CHOICES,
    _HANDSHAKE_MAP,
)
from providence_wizard.application.preferences_flow import PreferencesFlow
from providence_wizard.application.prompter import _CallablePrompter


def test_collect_preferences_builds_language_context() -> None:
    responses = iter(["2", "2", "3", "1"])
    flow = PreferencesFlow(_CallablePrompter(lambda _: next(responses)))
    config = flow.collect_preferences(
        enforcement_choices=["Sem Alertas", "Alertas", "Bloquear"],
        enforcement_map={
            "Sem Alertas": "silent_mode",
            "Alertas": "warn_mode",
            "Bloquear": "strict_mode",
        },
        interaction_language_choices=["English", "Portugus (Brasil)"],
        local_docs_language_choices=[
            "English",
            "Portugus (Brasil)",
            "Same as interaction",
        ],
        locale_by_language={"English": "en", "Portugus (Brasil)": "pt-BR"},
        handshake_choices=_HANDSHAKE_CHOICES,
        handshake_map=_HANDSHAKE_MAP,
    )
    assert config["enforcement_mode"] == "warn_mode"
    assert config["language"] == "all"
    assert config["locale"] == "pt-BR"
    assert config["docs_language"] == "Portugus (Brasil)"
    assert config["docs_locale"] == "pt-BR"
    assert config["language_context"]["preferred_local_docs_language"] == (
        "Portugus (Brasil)"
    )


def test_collect_preferences_includes_handshake_mode() -> None:
    responses = iter(["1", "1", "1", "2"])
    flow = PreferencesFlow(_CallablePrompter(lambda _: next(responses)))
    config = flow.collect_preferences(
        enforcement_choices=["Sem Alertas", "Alertas", "Bloquear"],
        enforcement_map={
            "Sem Alertas": "silent_mode",
            "Alertas": "warn_mode",
            "Bloquear": "strict_mode",
        },
        interaction_language_choices=["English", "Portugus (Brasil)"],
        local_docs_language_choices=[
            "English",
            "Portugus (Brasil)",
            "Same as interaction",
        ],
        locale_by_language={"English": "en", "Portugus (Brasil)": "pt-BR"},
        handshake_choices=_HANDSHAKE_CHOICES,
        handshake_map=_HANDSHAKE_MAP,
    )
    assert config["handshake_mode"] == "standard"


def test_select_handshake_mode_prompt_mentions_disable_escape_hatch() -> None:
    emitted: list[str] = []
    responses = iter(["1"])
    flow = PreferencesFlow(
        _CallablePrompter(lambda _: next(responses)), emitter=emitted.append
    )
    flow._select_handshake_mode(_HANDSHAKE_CHOICES, _HANDSHAKE_MAP)
    assert any("providence governance hook disable" in message for message in emitted)


class TestResolveNonInteractivePreferences:
    def test_falls_back_to_canonical_defaults_when_no_config_exists(
        self, tmp_path: Path
    ) -> None:
        flow = PreferencesFlow(_CallablePrompter(lambda _: "1"))
        config = flow.resolve_non_interactive_preferences(tmp_path)

        assert config["language"] == "all"
        assert config["enforcement_mode"] == "strict_mode"
        assert config["handshake_mode"] == "hook"
        assert config["docs_language"] == "English"
        assert config["locale"] == "pt-BR"
        assert (
            config["language_context"]["preferred_human_language"]
            == "Portugus (Brasil)"
        )

    def test_reuses_existing_wizard_config_when_present(self, tmp_path: Path) -> None:
        existing = {
            "language": "Python",
            "locale": "en",
            "docs_language": "English",
            "docs_locale": "en",
            "enforcement_mode": "warn_mode",
            "handshake_mode": "standard",
            "language_context": {
                "preferred_human_language": "English",
                "preferred_chat_language": "English",
                "preferred_ui_language": "English",
                "preferred_local_docs_language": "English",
            },
        }
        (tmp_path / "wizard-config.json").write_text(
            json.dumps(existing), encoding="utf-8"
        )
        flow = PreferencesFlow(_CallablePrompter(lambda _: "1"))

        config = flow.resolve_non_interactive_preferences(tmp_path)

        assert config["language"] == "all"
        assert config["enforcement_mode"] == "warn_mode"
        assert config["handshake_mode"] == "standard"
        assert config["locale"] == "en"
        assert config["language_context"]["preferred_human_language"] == "English"

    def test_ignores_malformed_existing_config(self, tmp_path: Path) -> None:
        (tmp_path / "wizard-config.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        flow = PreferencesFlow(_CallablePrompter(lambda _: "1"))

        config = flow.resolve_non_interactive_preferences(tmp_path)

        assert config["enforcement_mode"] == "strict_mode"
        assert config["handshake_mode"] == "hook"
