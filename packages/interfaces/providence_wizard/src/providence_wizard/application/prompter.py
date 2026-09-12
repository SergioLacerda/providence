"""Prompter protocol and adapters for interactive wizard."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from importlib import import_module
from typing import Any, Protocol, runtime_checkable

from ._prompter_adapters import (
    _CallablePrompter,
    _match_token_value,
    _parse_checkbox_tokens,
    _real_choices,
)

__all__ = [
    "PlainPrompter",
    "Prompter",
    "RichPrompter",
    "_CallablePrompter",
    "_match_token_value",
    "_parse_checkbox_tokens",
    "_real_choices",
    "make_prompter",
]


@runtime_checkable
class Prompter(Protocol):
    """Protocol for interactive user prompts."""

    def select(self, question: str, choices: list[Any]) -> str:
        """Present a single-choice menu and return the selected value."""
        pass

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        """Present a multi-choice menu and return the selected values."""
        pass

    def confirm(self, question: str, default: bool = True) -> bool:
        """Present a yes/no question and return the boolean answer."""
        pass


class PlainPrompter:
    """Input-based prompter for non-interactive environments (CI, pipe)."""

    def select(self, question: str, choices: list[Any]) -> str:
        """Print numbered choices and return the value at the entered index."""
        real = _real_choices(choices)
        for i, _v, label in real:
            print(f"  [{i + 1}] {label}")
        raw = input(f"{question} (1-{len(real)}): ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(real):
                return real[idx][1]
        return real[0][1] if real else ""

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        """Print numbered choices; return selected values or [] for all."""
        real = _real_choices(choices)
        real_idx = 0
        sep_idx = 0
        for c in choices:
            if getattr(c, "disabled", None):
                line = str(getattr(c, "title", f"-- Group {sep_idx} --"))
                print(f"\n  {line}")
                sep_idx += 1
            else:
                _idx, _value, label = real[real_idx]
                print(f"  [{real_idx + 1}] {label}")
                real_idx += 1
        print("  (empty = all, or comma-separated numbers/names)")
        raw = input(f"{question}: ").strip()
        return _parse_checkbox_tokens(raw, real)

    def confirm(self, question: str, default: bool = True) -> bool:
        """Prompt y/n; empty input returns the default."""
        suffix = " [Y/n]" if default else " [y/N]"
        raw = input(f"{question}{suffix}: ").strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes")


class RichPrompter:
    """questionary-based prompter for interactive terminals."""

    def select(self, question: str, choices: list[Any]) -> str:
        """Render an arrow-key single-choice prompt; raise KeyboardInterrupt on Ctrl-C."""
        result = _load_questionary().select(question, choices=choices).ask()
        if result is None:
            raise KeyboardInterrupt
        return str(result)

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        """Render an arrow-key multi-choice prompt; raise KeyboardInterrupt on Ctrl-C."""
        result = _load_questionary().checkbox(question, choices=choices).ask()
        if result is None:
            raise KeyboardInterrupt
        return [str(v) for v in result]

    def confirm(self, question: str, default: bool = True) -> bool:
        """Render a yes/no prompt; raise KeyboardInterrupt on Ctrl-C."""
        result = _load_questionary().confirm(question, default=default).ask()
        if result is None:
            raise KeyboardInterrupt
        return bool(result)


def make_prompter() -> Prompter:
    """Return RichPrompter when stdin is a TTY and questionary is available."""
    if os.name == "nt" and os.environ.get("PROVIDENCE_WIZARD_RICH_PROMPTS") != "1":
        return PlainPrompter()
    if sys.stdin.isatty() and _questionary_available():
        return RichPrompter()
    return PlainPrompter()


def _wrap_prompter(prompter: Prompter | Callable[[str], str] | None) -> Prompter:
    """Normalise any prompter value into a Prompter instance."""
    if prompter is None:
        return make_prompter()
    if isinstance(prompter, Prompter):
        return prompter
    if callable(prompter):
        return _CallablePrompter(prompter)
    return make_prompter()


def _load_questionary() -> Any:
    """Import questionary lazily for interactive shells only."""
    return import_module("questionary")


def _questionary_available() -> bool:
    """Return True when questionary can be imported."""
    try:
        _load_questionary()
    except ImportError:
        return False
    return True
