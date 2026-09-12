"""Budget circuit breaker guards for the ``providence ask`` command pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import typer

from providence_cli.commands._ask_backend._helpers import (
    _get_cached_ahp,
    _signature_mode,
)
from providence_cli.commands._ask_backend._helpers_signals import _json_mode
from providence_cli.shared.constants import BREACH_EXIT_CODE as _BREACH_EXIT_CODE

logger = logging.getLogger(__name__)


def _guard_budget_breach() -> None:
    """Block context loading if the session budget is in BREACH state.

    Reads ``SDD_BUDGET_UTILIZATION_PCT`` from the environment (set by the
    agent after each context load).  When utilization is  100 the command
    is aborted with exit code 3 and a human checkpoint message is displayed.

    This enforces economy/execution-budget.md Circuit Breaker Rule 3:
    "Agent MUST NOT load additional context once BREACH is reached."
    """
    pct_str = os.environ.get("SDD_BUDGET_UTILIZATION_PCT", "").strip()
    if not pct_str:
        return
    try:
        pct = float(pct_str)
    except ValueError:
        return
    if pct < 100.0:
        return

    typer.echo(
        f"\n[Providence] BUDGET BREACH: context utilization at {pct:.1f}% (>= 100%).\n"
        "Further context loading is blocked (economy/execution-budget.md).\n"
        "Human checkpoint required. Options:\n"
        "  1. Decompose the task into smaller PATH A/B units\n"
        "  2. Clear session context and restart\n"
        "  3. Run: providence runtime status  (inspect workspace state)\n",
        err=True,
    )
    raise typer.Exit(_BREACH_EXIT_CODE)


def _guard_handshake(workspace_root: Path) -> None:
    """Enforce handshake requirement (M015) based on signature mode.

    Resolution of ``is_valid`` is fail-open on unexpected errors (a broken
    cache read or AHP construction failure must not itself block `ask`).
    The *decision* to raise `typer.Exit` for a confirmed-invalid handshake
    in strict mode happens outside that fail-open boundary  `typer.Exit`
    is exception-based (`RuntimeError` subclass), so raising it from inside
    the same `try` that fails open on `Exception` silently swallowed the
    intended hard block. See
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` SEC-07.
    """
    sig_mode = "off"
    is_valid: bool | None = None
    try:
        sig_mode = _signature_mode()
        cached_ahp = _get_cached_ahp()
        is_valid = (
            bool(cached_ahp.get("valid")) if isinstance(cached_ahp, dict) else None
        )
        if is_valid is None:
            from providence_core.governance.handshake import AgentHandshakeProtocol

            ahp = AgentHandshakeProtocol(project_root=workspace_root)
            is_valid = ahp.is_handshake_valid(strict=sig_mode == "strict")
    except Exception as exc:
        logger.debug("Handshake guard resolution failed, failing open: %s", exc)
        return

    if is_valid:
        return

    if sig_mode == "strict":
        typer.echo(
            "BLOCK [ask]: Missing or incomplete handshake. "
            "Run 'providence governance validate' to establish a session contract first.",
            err=True,
        )
        raise typer.Exit(3)

    if not _json_mode():
        typer.echo(
            "SOFT [ask]: No active handshake. "
            "Run 'providence governance handshake --init' to formalize your session.",
            err=True,
        )
