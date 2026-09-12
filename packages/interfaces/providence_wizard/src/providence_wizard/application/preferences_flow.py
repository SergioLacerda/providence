"""Prompt and preference collection boundary for the wizard shell."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from providence_wizard.application.prompter import Prompter, make_prompter

# User-confirmed canonical defaults for non-interactive bootstrap when no
# prior wizard-config.json exists to reuse (see
# wizard-interactive-flow-redesign-20260705 design.md).
_NON_INTERACTIVE_DEFAULT_INTERACTION_LANGUAGE = "Portugus (Brasil)"
_NON_INTERACTIVE_DEFAULT_DOCS_LANGUAGE = "English"
_NON_INTERACTIVE_DEFAULT_ENFORCEMENT_MODE = "strict_mode"
_NON_INTERACTIVE_DEFAULT_HANDSHAKE_MODE = "hook"


class PreferencesFlow:
    """Encapsulate shell prompts behind the application layer."""

    def __init__(
        self,
        prompter: Prompter | None = None,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._prompter = prompter or make_prompter()
        self._emit = emitter or (lambda _: None)

    def build_prompter(self) -> Prompter:
        """Return the active prompter instance."""
        return self._prompter

    def resolve_non_interactive_preferences(
        self, client_build_dir: Path
    ) -> dict[str, Any]:
        """Resolve preferences without prompting.

        Reuses an existing `wizard-config.json` under `client_build_dir` when
        present (avoids new per-preference CLI flags); otherwise falls back
        to user-confirmed canonical defaults matching this workspace's own
        established values.
        """
        existing = self._load_existing_config(client_build_dir)
        if existing is not None:
            language_context = existing.get("language_context") or {}
            interaction_language = language_context.get(
                "preferred_human_language",
                _NON_INTERACTIVE_DEFAULT_INTERACTION_LANGUAGE,
            )
            docs_language = existing.get(
                "docs_language", _NON_INTERACTIVE_DEFAULT_DOCS_LANGUAGE
            )
            return {
                "language": "all",
                "locale": existing.get("locale", "en"),
                "docs_language": docs_language,
                "docs_locale": existing.get("docs_locale", "en"),
                "enforcement_mode": existing.get(
                    "enforcement_mode", _NON_INTERACTIVE_DEFAULT_ENFORCEMENT_MODE
                ),
                "handshake_mode": existing.get(
                    "handshake_mode", _NON_INTERACTIVE_DEFAULT_HANDSHAKE_MODE
                ),
                "language_context": language_context
                or self._build_language_context(interaction_language, docs_language),
                "generated_at": datetime.now().isoformat(),
            }

        return self._build_config(
            enforcement_mode=_NON_INTERACTIVE_DEFAULT_ENFORCEMENT_MODE,
            interaction_language=_NON_INTERACTIVE_DEFAULT_INTERACTION_LANGUAGE,
            docs_language=_NON_INTERACTIVE_DEFAULT_DOCS_LANGUAGE,
            locale_by_language={
                "English": "en",
                "Portugus (Brasil)": "pt-BR",
            },
            handshake_mode=_NON_INTERACTIVE_DEFAULT_HANDSHAKE_MODE,
        )

    @staticmethod
    def _load_existing_config(client_build_dir: Path) -> dict[str, Any] | None:
        config_path = client_build_dir / "wizard-config.json"
        if not config_path.exists():
            return None
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def collect_preferences(
        self,
        *,
        enforcement_choices: list[str],
        enforcement_map: dict[str, str],
        interaction_language_choices: list[str],
        local_docs_language_choices: list[str],
        locale_by_language: dict[str, str],
        handshake_choices: list[str],
        handshake_map: dict[str, str],
    ) -> dict[str, Any]:
        """Collect wizard preferences and return the persisted config payload."""
        enforcement = self._select_enforcement(enforcement_choices, enforcement_map)
        interaction_language = self._select_interaction_language(
            interaction_language_choices
        )
        docs_language = self._select_docs_language(
            interaction_language, local_docs_language_choices
        )
        handshake = self._select_handshake_mode(handshake_choices, handshake_map)
        return self._build_config(
            enforcement_mode=enforcement,
            interaction_language=interaction_language,
            docs_language=docs_language,
            locale_by_language=locale_by_language,
            handshake_mode=handshake,
        )

    def _select_enforcement(
        self, enforcement_choices: list[str], enforcement_map: dict[str, str]
    ) -> str:
        self._emit("\n1  How should governance violations be handled?")
        selected = self._prompter.select("Select enforcement:", enforcement_choices)
        self._emit(f"    Selected: {selected}")
        return enforcement_map.get(selected, "warn_mode")

    def _select_interaction_language(
        self, interaction_language_choices: list[str]
    ) -> str:
        self._emit(
            "\n2  Which language should the wizard prefer for chat and operational prompts?"
        )
        selected = self._prompter.select(
            "Select interaction language:", interaction_language_choices
        )
        self._emit(f"    Selected: {selected}")
        return selected

    def _select_docs_language(
        self, interaction_language: str, local_docs_language_choices: list[str]
    ) -> str:
        self._emit(
            "\n3  Which language should local workspace notes prefer when the workspace allows it?"
        )
        selected = self._prompter.select(
            "Select local docs preference:", local_docs_language_choices
        )
        self._emit(f"    Selected: {selected}")
        if selected == "Same as interaction":
            return interaction_language
        return selected

    def _select_handshake_mode(
        self, handshake_choices: list[str], handshake_map: dict[str, str]
    ) -> str:
        self._emit(
            "\n4  Prefere que todo prompt seja filtrado pela governana (hook) OU"
            " invocar a governana seletivamente (slash commands, CLI)?"
            "\n   (modo hook pode ser desativado a qualquer momento com"
            " 'providence governance hook disable')"
        )
        selected = self._prompter.select("Selecione o handshake:", handshake_choices)
        self._emit(f"    Selecionado: {selected}")
        return handshake_map.get(selected, "standard")

    def _build_config(
        self,
        *,
        enforcement_mode: str,
        interaction_language: str,
        docs_language: str,
        locale_by_language: dict[str, str],
        handshake_mode: str,
    ) -> dict[str, Any]:
        return {
            "language": "all",
            "locale": locale_by_language.get(interaction_language, "en"),
            "docs_language": docs_language,
            "docs_locale": locale_by_language.get(docs_language, "en"),
            "enforcement_mode": enforcement_mode,
            "handshake_mode": handshake_mode,
            "language_context": self._build_language_context(
                interaction_language, docs_language
            ),
            "generated_at": datetime.now().isoformat(),
        }

    def _build_language_context(
        self, interaction_language: str, docs_language: str
    ) -> dict[str, str]:
        return {
            "preferred_human_language": interaction_language,
            "preferred_chat_language": interaction_language,
            "preferred_ui_language": interaction_language,
            "preferred_local_docs_language": docs_language,
        }
