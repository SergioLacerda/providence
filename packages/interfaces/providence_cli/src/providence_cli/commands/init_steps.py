"""Telemetry emission and CLI step execution helpers for `providence init`."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import typer

from providence_core.utils.environment import SddProfile, resolve_sdd_child_cmd

logger = logging.getLogger(__name__)


def _emit_workspace_init_telemetry(
    *,
    profile_ctx: Any,
    effective_name: str,
    force: bool,
    profile_type: SddProfile,
) -> None:
    try:
        import uuid

        from providence_runtime.telemetry import RuntimeEvent, TelemetrySink

        sink = TelemetrySink()
        sink.emit(
            RuntimeEvent(
                event="workspace.init",
                command="init",
                status="ok",
                trace_id=str(uuid.uuid4()),
                details={
                    "workspace_id": profile_ctx.workspace_id,
                    "name": effective_name,
                    "forced": bool(force),
                    "phase_0_origin": "bootstrap_init",
                    "profile_type": profile_type,
                },
            )
        )
        sink.flush()
    except Exception:
        logger.debug("Failed to emit workspace init event", exc_info=True)


def _run_cli_step(label: str, args: list[str], cwd: Path) -> bool:
    """Run a CLI subcommand as a subprocess step. Returns True on success."""
    from providence_core.utils.process import SafeProcessRunner

    typer.echo(f"\n[bootstrap] {label}...")
    sdd_cmd = resolve_sdd_child_cmd()
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    runner = SafeProcessRunner()
    result = runner.run(
        [sdd_cmd] + args,
        cwd=cwd,
        env=env,
        capture_output=False,
    )
    ok = result.success
    typer.echo(f"  {'OK' if ok else 'FAIL'}: {label}")
    return ok
