"""Seedling selection prompt helpers for interactive wizard."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from providence_wizard.application.prompter import Prompter, _wrap_prompter
from providence_wizard.orchestration.wizard.seedling_catalog import CATALOG

SEEDLINGS: list[tuple[str, str, str]] = [
    (option.key, option.group, option.description) for option in CATALOG
]


def _build_choices() -> list[Any]:
    """Build questionary-compatible choices list with group separators."""
    try:
        from questionary import Choice, Separator

        choices: list[Any] = []
        last_group: str | None = None
        for key, group, desc in SEEDLINGS:
            if group != last_group:
                choices.append(Separator(f" {group} "))
                last_group = group
            choices.append(Choice(f"{key:<18}  {desc}", value=key))
        return choices
    except ImportError:
        return [f"{key}  {desc}" for key, _, desc in SEEDLINGS]


def ask_seedling_selection(
    emitter: Callable[[str], None],
    prompter: Prompter | Callable[[str], str] | None = None,
) -> set[str] | None:
    """Ask the user which seedlings to include. Returns None for all.

    Args:
        emitter: Output callback for display messages.
        prompter: Prompter instance, legacy callable, or None (uses make_prompter).
    """
    _p = _wrap_prompter(prompter)
    emitter("\n Seedlings Selection")
    emitter("-" * 50)

    choices = _build_choices()
    selected_values = _p.checkbox(
        "Select seedlings (empty = recommended default: CORE + IDEs + AGENTS):",
        choices,
    )

    # Backward-compatible textual fallback (tests and non-questionary flows)
    # may return raw comma-separated input instead of list[str].
    if isinstance(selected_values, str):
        raw = selected_values.strip()
        if not raw or raw.lower() == "all":
            selected_values = []
        else:
            known_keys = [s[0] for s in SEEDLINGS]
            by_index = {str(i + 1): key for i, key in enumerate(known_keys)}
            parsed: list[str] = []
            for token in (t.strip().lower() for t in raw.split(",")):
                if not token:
                    continue
                if token in by_index:
                    parsed.append(by_index[token])
                else:
                    parsed.append(token)
            selected_values = parsed

    if not selected_values:
        emitter("   Generating recommended default (CORE + IDEs + AGENTS)")
        return None

    known = {s[0] for s in SEEDLINGS}
    normalized: list[str] = []
    for value in selected_values:
        candidate = value.strip()
        if "  " in candidate:
            candidate = candidate.split("  ", 1)[0].strip()
        normalized.append(candidate)
    valid = {v for v in normalized if v in known}

    if not valid:
        emitter(
            "    No valid selection  generating recommended default "
            "(CORE + IDEs + AGENTS)"
        )
        return None

    emitter(f"   Generating: {', '.join(sorted(valid))}")
    return valid
