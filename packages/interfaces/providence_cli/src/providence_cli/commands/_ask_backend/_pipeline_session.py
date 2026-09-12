"""Session and intake helpers for `providence ask` pipeline."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import typer

from providence_cli.services.ask_types import _AskInputs, _AskSessionContext

from ._helpers import _now
from ._helpers_signals import _json_mode
from ._phase_timeouts import DEFAULT_ASK_PHASE_TIMEOUTS_MS, DEFAULT_ASK_TIMEOUT_MS
from ._phase_timer import PhaseTimer

logger = logging.getLogger(__name__)


def _run_organize_intake(
    workspace_root: Any, query: str, skill: str | None
) -> tuple[bool, str, str, int, str, str | None]:
    """Run sdd-organize intake.

    Returns (used, reason, artifact_path, chunks, retrieval,
    cached_handbook_task_type). On a routing-decision cache hit (same
    normalized query + skill + last-known governance fingerprint), the
    `should_use_organize` heuristic is skipped in favor of the cached
    decision; `cached_handbook_task_type` is then non-None so
    `_infer_handbook_task_type` can be skipped downstream too.
    """
    from providence_cli.commands import _ask_backend as _backend

    cached_decision = _backend._resolve_routing_decision(workspace_root, query, skill)
    cached_handbook_task_type: str | None = None
    if cached_decision is not None:
        organize_used = bool(cached_decision.get("organize_used", False))
        organize_reason = str(
            cached_decision.get("organize_reason") or "cached_routing_decision"
        )
        cached_handbook_task_type = cached_decision.get("handbook_task_type") or None
    else:
        organize_used, organize_reason = _backend._should_use_organize(query)
    organize_artifact_path = ""
    organize_chunks = 0
    organize_retrieval = "indexed_only"
    if organize_used:
        try:
            organize_artifact, organize_path = _backend.run_sdd_organize(
                workspace_root=workspace_root,
                query=query,
                source_text=query,
                route_reason=organize_reason,
            )
            organize_artifact_path = str(organize_path)
            organize_chunks = len(organize_artifact.get("chunks", []))
            organize_retrieval = str(
                organize_artifact.get("retrieval_policy", "indexed_only")
            )
        except Exception as exc:
            logger.debug("sdd-organize failed in ask: %s", exc)
            organize_retrieval = "degraded"
    return (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
        cached_handbook_task_type,
    )


def _emit_state_warnings(state: str) -> None:
    if _json_mode():
        return
    if state in ("NOT_INITIALIZED", "MISCONFIGURED"):
        typer.echo(
            f"SOFT [ask]: workspace {state}. Run 'providence governance compile' before using ask.",
            err=True,
        )
    elif state == "PARTIAL":
        typer.echo(
            "SOFT [ask]: workspace PARTIAL  compiled governance may be stale. "
            "Next: 'providence governance compile'",
            err=True,
        )


def _start_ask_session(
    query: str, skill: str | None, *, entry_mono: float | None = None
) -> _AskSessionContext:
    from providence_cli.commands import _ask_backend as _backend

    start_mono = time.monotonic()
    start_ts = _now()
    timer = PhaseTimer(
        thresholds_ms=dict(DEFAULT_ASK_PHASE_TIMEOUTS_MS),
        default_threshold_ms=DEFAULT_ASK_TIMEOUT_MS,
    )

    if entry_mono is not None:
        # Measured locally (not adapter-reported)  record_external is used
        # here only because the timer did not exist yet at the true CLI
        # entry point (_ask_cmd_impl's first line), so phase() (a context
        # manager) could not wrap it.
        timer.record_external(
            "ask.cli.entry",
            latency_domain="local_cli",
            duration_ms=int((start_mono - entry_mono) * 1000),
            measurement_quality="measured",
            observed_by="providence_cli",
        )

    with timer.phase("ask.budget.guard", latency_domain="governance"):
        _backend._guard_budget_breach()

    with timer.phase("ask.workspace.resolve", latency_domain="local_fs"):
        workspace_root = _backend._resolve_workspace_root()

    with timer.phase("ask.organize.intake", latency_domain="local_cli"):
        (
            organize_used,
            organize_reason,
            organize_artifact_path,
            organize_chunks,
            organize_retrieval,
            cached_handbook_task_type,
        ) = _backend._run_organize_intake(workspace_root, query, skill)

    with timer.phase("ask.handshake.guard", latency_domain="governance"):
        _backend._guard_handshake(workspace_root)

    with timer.phase("ask.profile.resolve", latency_domain="governance"):
        profile, state = _backend._get_profile_state()

    _backend._emit_state_warnings(state)
    return _AskSessionContext(
        workspace_root=workspace_root,
        organize_used=organize_used,
        organize_reason=organize_reason,
        organize_artifact_path=organize_artifact_path,
        organize_chunks=organize_chunks,
        organize_retrieval=organize_retrieval,
        cached_handbook_task_type=cached_handbook_task_type,
        profile=profile,
        state=state,
        agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
        trace_id=str(uuid.uuid4()),
        start_mono=start_mono,
        start_ts=start_ts,
        phase_timer=timer,
    )


def _load_ask_snapshot(
    inputs: _AskInputs, session: _AskSessionContext
) -> dict[str, Any]:
    from providence_cli.commands import _ask_backend as _backend

    try:
        # ask.governance.snapshot is measured here (caller side) as a
        # black-box span around the whole call  tests that mock
        # build_governed_ask_snapshot entirely still get a correctly-timed
        # governance.snapshot phase this way. build_governed_ask_snapshot
        # additionally records its own nested ask.runtime.handbook phase
        # (only when it actually runs, i.e. not when mocked) for the
        # handbook-lookup sub-step; that nested span's duration is included
        # a second time in this phase's own duration, a known, documented
        # limitation of PhaseTimer.phase_total_ms()/unattributed_ms() not
        # being nesting-aware. Handbook lookup is a small fraction of this
        # phase's total, so the effect on unattributed_ms() is minor.
        with session.phase_timer.phase(
            "ask.governance.snapshot", latency_domain="governance"
        ):
            return _backend.build_governed_ask_snapshot(
                query=inputs.query,
                skill=inputs.skill,
                organize_used=session.organize_used,
                workspace_root=session.workspace_root,
                require_handshake=True,
                cached_handbook_task_type=session.cached_handbook_task_type,
                phase_timer=session.phase_timer,
            )
    except PermissionError as exc:
        typer.echo(f"BLOCK [ask]: {exc}", err=True)
        raise typer.Exit(3) from None
