"""providence ask  JSON-mode detection and learning-signal helpers.

Split out of `_helpers.py` (T16,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path

import click

from providence_cli.services.ask_filter import (
    collect_learning_signals as _collect_learning_signals_impl,
)
from providence_cli.services.ask_filter import (
    count_signals_from_tail as _count_signals_from_tail_impl,
)
from providence_cli.shared.constants import (
    LEARNING_WINDOW_DAYS as _LEARNING_WINDOW_DAYS,
)
from providence_cli.utils.output import is_json_mode


def _json_mode() -> bool:
    from providence_cli.commands._ask_backend import _JSON_MODE_OVERRIDE

    override = _JSON_MODE_OVERRIDE.get()
    if override is not None:
        return override
    ctx = click.get_current_context(silent=True)
    while ctx is not None:
        if is_json_mode(ctx):
            return True
        ctx = ctx.parent
    return False


def _count_signals_from_tail(
    path: Path, signals: dict[str, int], cutoff_ts: float, *, from_failures: bool
) -> None:
    _count_signals_from_tail_impl(path, signals, cutoff_ts, from_failures=from_failures)


def _collect_learning_signals(
    workspace_root: Path, *, window_days: int = _LEARNING_WINDOW_DAYS
) -> dict[str, int]:
    return _collect_learning_signals_impl(workspace_root, window_days=window_days)
