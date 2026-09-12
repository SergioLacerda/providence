"""Choice-parsing helpers and the callable-based prompter adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _real_choices(choices: list[Any]) -> list[tuple[int, str, str]]:
    """Return (index, value, label) for non-separator entries.

    Separators are detected by their truthy `disabled` attribute (questionary 2.x
    sets disabled='-' on Separator objects).
    """
    result: list[tuple[int, str, str]] = []
    idx = 0
    for c in choices:
        if getattr(c, "disabled", None):
            # questionary.Separator  skip
            continue
        if isinstance(c, str):
            result.append((idx, c, c))
            idx += 1
        elif hasattr(c, "value") and c.value is not None:
            label = str(getattr(c, "title", c.value))
            result.append((idx, c.value, label))
            idx += 1
    return result


def _match_token_value(token: str, value_set: set[str]) -> str | None:
    """Resolve token to an allowed choice value."""
    if token in value_set:
        return token
    for value in value_set:
        if not isinstance(value, str):
            continue
        if value.startswith(f"{token} "):
            return value
        for separator in (" - ", " -- ", "  "):
            if separator in value:
                key = value.split(separator, 1)[0].strip()
                if token == key:
                    return value
    return None


def _parse_checkbox_tokens(raw: str, real: list[tuple[int, str, str]]) -> list[str]:
    """Parse comma-separated checkbox input into selected values."""
    if not raw or raw.lower() == "all":
        return []
    value_set = {v for _, v, _ in real}
    selected: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(real):
                selected.append(real[idx][1])
            continue
        matched = _match_token_value(token, value_set)
        if matched is not None:
            selected.append(matched)
    return selected


class _CallablePrompter:
    """Backward-compat wrapper: adapts a Callable[[str], str] to the Prompter protocol.

    Used internally so legacy test callables continue to work without changes.
    """

    def __init__(self, fn: Callable[[str], str]) -> None:
        self._fn = fn

    def select(self, question: str, choices: list[Any]) -> str:
        raw = self._fn(question).strip()
        real = _real_choices(choices)
        if not real:
            return ""
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(real):
                return real[idx][1]
        return real[0][1]

    def checkbox(self, question: str, choices: list[Any]) -> list[str]:
        raw = self._fn(question).strip()
        real = _real_choices(choices)
        return _parse_checkbox_tokens(raw, real)

    def confirm(self, question: str, default: bool = True) -> bool:
        raw = self._fn(question).strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes")
