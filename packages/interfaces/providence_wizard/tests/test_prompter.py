"""Tests for Prompter protocol and adapters."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from providence_wizard.application.prompter import (
    PlainPrompter,
    Prompter,
    RichPrompter,
    _CallablePrompter,
    make_prompter,
)


class TestPrompterProtocol:
    def test_plain_prompter_is_prompter(self) -> None:
        assert isinstance(PlainPrompter(), Prompter)

    def test_callable_prompter_is_prompter(self) -> None:
        assert isinstance(_CallablePrompter(lambda _: ""), Prompter)

    def test_make_prompter_non_tty_returns_plain(self) -> None:
        with patch.object(sys.stdin, "isatty", return_value=False):
            p = make_prompter()
        assert isinstance(p, PlainPrompter)

    def test_make_prompter_tty_returns_rich_when_questionary_available(self) -> None:
        try:
            import questionary  # noqa: F401

            has_questionary = True
        except ImportError:
            has_questionary = False

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.dict("os.environ", {"PROVIDENCE_WIZARD_RICH_PROMPTS": "1"}),
        ):
            p = make_prompter()

        if has_questionary:
            assert isinstance(p, RichPrompter)
        else:
            assert isinstance(p, PlainPrompter)

    def test_make_prompter_windows_defaults_to_plain(self) -> None:
        with (
            patch("os.name", "nt"),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.dict("os.environ", {}, clear=True),
        ):
            p = make_prompter()

        assert isinstance(p, PlainPrompter)


class TestPlainPrompterSelect:
    def test_valid_index_returns_choice(self) -> None:
        with patch("builtins.input", return_value="2"):
            result = PlainPrompter().select("Pick:", ["a", "b", "c"])
        assert result == "b"

    def test_invalid_index_falls_back_to_first(self) -> None:
        with patch("builtins.input", return_value="99"):
            result = PlainPrompter().select("Pick:", ["a", "b", "c"])
        assert result == "a"

    def test_non_digit_input_falls_back_to_first(self) -> None:
        with patch("builtins.input", return_value="x"):
            result = PlainPrompter().select("Pick:", ["a", "b", "c"])
        assert result == "a"

    def test_first_index(self) -> None:
        with patch("builtins.input", return_value="1"):
            result = PlainPrompter().select("Pick:", ["x", "y"])
        assert result == "x"


class TestPlainPrompterCheckbox:
    def test_empty_input_returns_empty_list(self) -> None:
        with patch("builtins.input", return_value=""):
            result = PlainPrompter().checkbox("Pick:", ["a", "b", "c"])
        assert result == []

    def test_all_returns_empty_list(self) -> None:
        with patch("builtins.input", return_value="all"):
            result = PlainPrompter().checkbox("Pick:", ["a", "b", "c"])
        assert result == []

    def test_numeric_selection(self) -> None:
        with patch("builtins.input", return_value="1,3"):
            result = PlainPrompter().checkbox("Pick:", ["a", "b", "c"])
        assert result == ["a", "c"]

    def test_named_selection(self) -> None:
        with patch("builtins.input", return_value="b,c"):
            result = PlainPrompter().checkbox("Pick:", ["a", "b", "c"])
        assert result == ["b", "c"]

    def test_invalid_tokens_ignored(self) -> None:
        with patch("builtins.input", return_value="99,unknown"):
            result = PlainPrompter().checkbox("Pick:", ["a", "b"])
        assert result == []


class TestPlainPrompterConfirm:
    def test_empty_returns_default_true(self) -> None:
        with patch("builtins.input", return_value=""):
            assert PlainPrompter().confirm("Sure?", default=True) is True

    def test_empty_returns_default_false(self) -> None:
        with patch("builtins.input", return_value=""):
            assert PlainPrompter().confirm("Sure?", default=False) is False

    def test_y_returns_true(self) -> None:
        with patch("builtins.input", return_value="y"):
            assert PlainPrompter().confirm("Sure?") is True

    def test_n_returns_false(self) -> None:
        with patch("builtins.input", return_value="n"):
            assert PlainPrompter().confirm("Sure?") is False


class TestCallablePrompterSelect:
    def test_numeric_maps_to_choice(self) -> None:
        p = _CallablePrompter(lambda _: "2")
        assert p.select("Pick:", ["a", "b", "c"]) == "b"

    def test_out_of_bounds_falls_back_to_first(self) -> None:
        p = _CallablePrompter(lambda _: "9")
        assert p.select("Pick:", ["a", "b", "c"]) == "a"

    def test_non_digit_falls_back_to_first(self) -> None:
        p = _CallablePrompter(lambda _: "x")
        assert p.select("Pick:", ["a", "b", "c"]) == "a"

    def test_propagates_keyboard_interrupt(self) -> None:
        def _raise(_: str) -> str:
            raise KeyboardInterrupt

        p = _CallablePrompter(_raise)
        with pytest.raises(KeyboardInterrupt):
            p.select("Pick:", ["a"])

    def test_propagates_runtime_error(self) -> None:
        def _raise(_: str) -> str:
            raise RuntimeError("crash")

        p = _CallablePrompter(_raise)
        with pytest.raises(RuntimeError, match="crash"):
            p.select("Pick:", ["a"])


class TestCallablePrompterCheckbox:
    def test_empty_returns_empty_list(self) -> None:
        p = _CallablePrompter(lambda _: "")
        assert p.checkbox("Pick:", ["a", "b"]) == []

    def test_all_returns_empty_list(self) -> None:
        p = _CallablePrompter(lambda _: "all")
        assert p.checkbox("Pick:", ["a", "b"]) == []

    def test_numeric_selection(self) -> None:
        p = _CallablePrompter(lambda _: "1,2")
        result = p.checkbox("Pick:", ["a", "b", "c"])
        assert result == ["a", "b"]

    def test_named_selection(self) -> None:
        p = _CallablePrompter(lambda _: "governance,compliance")
        result = p.checkbox("Pick:", ["governance", "compliance", "claude"])
        assert result == ["governance", "compliance"]


class TestCallablePrompterConfirm:
    def test_empty_returns_default(self) -> None:
        p = _CallablePrompter(lambda _: "")
        assert p.confirm("Sure?", default=True) is True

    def test_y_returns_true(self) -> None:
        p = _CallablePrompter(lambda _: "y")
        assert p.confirm("Sure?") is True

    def test_n_returns_false(self) -> None:
        p = _CallablePrompter(lambda _: "n")
        assert p.confirm("Sure?") is False


class TestCallablePrompterSelectEmptyChoices:
    def test_empty_choices_returns_empty_string(self) -> None:
        p = _CallablePrompter(lambda _: "1")
        assert p.select("Pick:", []) == ""


class TestMatchTokenValueWithDash:
    def test_key_prefix_matches_value_with_dash(self) -> None:
        from providence_wizard.application.prompter import _match_token_value

        result = _match_token_value(
            "governance", {"governance  GAP v1.0", "compliance  CI"}
        )
        assert result == "governance  GAP v1.0"

    def test_no_match_returns_none(self) -> None:
        from providence_wizard.application.prompter import _match_token_value

        result = _match_token_value("unknown", {"governance  GAP v1.0"})
        assert result is None

    def test_exact_match_short_circuits(self) -> None:
        from providence_wizard.application.prompter import _match_token_value

        result = _match_token_value("foo", {"foo", "bar  baz"})
        assert result == "foo"


class TestWrapPrompterFallback:
    def test_non_callable_non_prompter_returns_make_prompter(self) -> None:
        from providence_wizard.application.prompter import _wrap_prompter

        with patch.object(sys.stdin, "isatty", return_value=False):
            p = _wrap_prompter(42)  # type: ignore[arg-type]
        assert isinstance(p, PlainPrompter)


class TestRichPrompter:
    def test_select_returns_value(self) -> None:
        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = "choice_a"
        with patch.dict(sys.modules, {"questionary": mock_q}):
            p = RichPrompter()
            result = p.select("Pick:", ["choice_a", "choice_b"])
        assert result == "choice_a"

    def test_select_raises_keyboard_interrupt_on_none(self) -> None:
        mock_q = MagicMock()
        mock_q.select.return_value.ask.return_value = None
        with patch.dict(sys.modules, {"questionary": mock_q}):
            p = RichPrompter()
            with pytest.raises(KeyboardInterrupt):
                p.select("Pick:", ["a"])

    def test_checkbox_returns_values(self) -> None:
        mock_q = MagicMock()
        mock_q.checkbox.return_value.ask.return_value = ["a", "b"]
        with patch.dict(sys.modules, {"questionary": mock_q}):
            p = RichPrompter()
            result = p.checkbox("Pick:", ["a", "b", "c"])
        assert result == ["a", "b"]

    def test_checkbox_raises_keyboard_interrupt_on_none(self) -> None:
        mock_q = MagicMock()
        mock_q.checkbox.return_value.ask.return_value = None
        with patch.dict(sys.modules, {"questionary": mock_q}):
            p = RichPrompter()
            with pytest.raises(KeyboardInterrupt):
                p.checkbox("Pick:", ["a"])

    def test_confirm_returns_bool(self) -> None:
        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = True
        with patch.dict(sys.modules, {"questionary": mock_q}):
            p = RichPrompter()
            assert p.confirm("Sure?") is True

    def test_confirm_raises_keyboard_interrupt_on_none(self) -> None:
        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = None
        with patch.dict(sys.modules, {"questionary": mock_q}):
            p = RichPrompter()
            with pytest.raises(KeyboardInterrupt):
                p.confirm("Sure?")
