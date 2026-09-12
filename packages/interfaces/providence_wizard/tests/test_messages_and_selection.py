"""Tests for wizard messages and seedling_selection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_wizard.orchestration.wizard.messages import (
    phase2_instructions_message,
    phase3_completed_message,
    phase4_consolidation_failed_message,
    phase4_success_message,
    phase6_seedlings_success_message,
)
from providence_wizard.orchestration.wizard.seedling_selection import (
    SEEDLINGS,
    ask_seedling_selection,
)


class TestMessages:
    def test_phase2_instructions_contains_paths(self) -> None:
        msg = phase2_instructions_message(
            phase1_path=Path("/phase1"),
            output_path=Path("/output"),
            copied_files=["a.md", "b.md"],
        )
        assert "/phase1" in msg
        assert "/output" in msg
        assert "a.md" in msg

    def test_phase3_completed_contains_next_steps(self) -> None:
        msg = phase3_completed_message()
        assert "CLAUDE.md" in msg or "governance" in msg.lower()

    def test_phase4_success_contains_stats(self) -> None:
        msg = phase4_success_message(
            mandates=5,
            guidelines=120,
            categories=["security", "testing"],
            final_template_dir=Path("/out"),
        )
        assert "5" in msg
        assert "120" in msg
        assert "security" in msg

    def test_phase4_consolidation_failed_contains_paths(self) -> None:
        msg = phase4_consolidation_failed_message(
            source_dir=Path("/src"), target_dir=Path("/tgt")
        )
        assert "/src" in msg
        assert "/tgt" in msg

    def test_phase6_seedlings_success_contains_output_base(self) -> None:
        msg = phase6_seedlings_success_message(Path("/my-project"))
        assert "/my-project" in msg


class TestSeedlingSelection:
    def test_blank_input_returns_none(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=lambda _: "")
        assert result is None

    def test_all_input_returns_none(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=lambda _: "all")
        assert result is None

    def test_numeric_selection_returns_set(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=lambda _: "1,2")
        assert result is not None
        assert len(result) == 2

    def test_named_selection_returns_set(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(
            messages.append, prompter=lambda _: "governance,compliance"
        )
        assert result == {"governance", "compliance"}

    def test_invalid_index_ignored(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=lambda _: "999")
        # All invalid  returns None (all seedlings)
        assert result is None

    def test_unknown_key_ignored(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(
            messages.append, prompter=lambda _: "unknown-key"
        )
        assert result is None

    def test_mixed_valid_and_invalid(self) -> None:
        messages: list[str] = []
        result = ask_seedling_selection(
            messages.append, prompter=lambda _: "1,999,unknown"
        )
        # Only the valid index-1 is selected
        assert result is not None
        assert len(result) == 1

    def test_seedlings_list_has_expected_entries(self) -> None:
        keys = {s[0] for s in SEEDLINGS}
        assert "governance" in keys
        assert "claude" in keys
        assert "codex" in keys
        assert "compliance" in keys

    def test_no_prompter_uses_input_by_default(self) -> None:
        messages: list[str] = []
        # When prompter=None, falls back to built-in input  just verify the
        # signature doesn't raise when called with the prompter kwarg omitted.
        with patch("builtins.input", return_value="all"):
            result = ask_seedling_selection(messages.append)
        assert result is None

    def test_string_returning_checkbox_blank_returns_none(self) -> None:
        """Covers the isinstance(selected_values, str) textual fallback path."""

        class _StringPrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> str:  # type: ignore[override]
                return ""

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_StringPrompter())
        assert result is None

    def test_string_returning_checkbox_all_returns_none(self) -> None:
        class _StringPrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> str:  # type: ignore[override]
                return "all"

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_StringPrompter())
        assert result is None

    def test_string_returning_checkbox_named_key(self) -> None:
        class _StringPrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> str:  # type: ignore[override]
                return "governance,compliance"

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_StringPrompter())
        assert result == {"governance", "compliance"}

    def test_string_returning_checkbox_named_codex_key(self) -> None:
        class _StringPrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> str:  # type: ignore[override]
                return "codex"

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_StringPrompter())
        assert result == {"codex"}

    def test_string_returning_checkbox_numeric_index(self) -> None:
        class _StringPrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> str:  # type: ignore[override]
                return "1"

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_StringPrompter())
        assert result == {"governance"}

    def test_normalized_value_with_dash_separator(self) -> None:
        """Covers the '  ' normalization branch in ask_seedling_selection."""

        class _RawChoicePrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> list:
                return ["governance            GAP v1.0 auto-activation"]

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_RawChoicePrompter())
        assert result is not None
        assert "governance" in result

    def test_all_invalid_normalized_values_returns_none_with_warning(self) -> None:
        """Covers the 'no valid selection' warning path (lines 93-94)."""

        class _BadPrompter:
            def select(self, q: str, choices: list) -> str:
                return ""

            def checkbox(self, q: str, choices: list) -> list:
                return ["not-a-real-seedling", "also-invalid"]

            def confirm(self, q: str, default: bool = True) -> bool:
                return default

        messages: list[str] = []
        result = ask_seedling_selection(messages.append, prompter=_BadPrompter())
        assert result is None
        assert any("No valid selection" in m for m in messages)


class TestBuildChoices:
    def test_build_choices_without_questionary(self) -> None:
        """Covers the ImportError fallback path in _build_choices."""
        import sys
        from unittest.mock import patch

        from providence_wizard.orchestration.wizard.seedling_selection import (
            _build_choices,
        )

        with patch.dict(sys.modules, {"questionary": None}):
            choices = _build_choices()

        assert isinstance(choices, list)
        assert len(choices) > 0
        assert all(isinstance(c, str) for c in choices)
