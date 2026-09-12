"""Shared `app` instance and events-path resolution for the `telemetry` group.

Exists solely to break the import cycle between `telemetry.py` and
`telemetry_query.py` (T13 split): both files need the same Typer `app` to
attach commands to, and both need the events-path resolution helpers below.
If either imported the other directly, one would have to be imported before
it finishes defining `app`  the exact shape flagged by CodeQL's
cyclic-import query, and also flagged by
`tools/architecture/validate_cycles.py`, which does not distinguish deferred
(function-local) imports from module-level ones  any textual
cross-reference between the two files counts as a cycle edge to that
checker. Both files now depend one-way on this module instead of on each
other.
"""

from __future__ import annotations

from pathlib import Path

import click
import typer

from providence_cli.commands._telemetry_command_validation import (
    abort_workspace_resolution,
)
from providence_cli.utils.output import is_json_mode
from providence_cli.utils.providence_authority import resolve_workspace_root
from providence_core.governance.compliance_constants import (
    resolve_compliance_log_override,
)

app = typer.Typer(
    help="Inspect and manage local telemetry events",
    invoke_without_command=True,
)


def _default_events_path() -> Path:
    override = resolve_compliance_log_override()
    if override.path is not None:
        return override.path
    try:
        root = resolve_workspace_root()
    except Exception as exc:
        raise RuntimeError("failed to resolve workspace root for telemetry") from exc
    return root / ".providence" / "runtime" / "compliance-events.jsonl"


def _warn_if_telemetry_paths_diverge() -> None:
    """Soft-warn (stderr only) when the compliance-events path env vars diverge.

    ``SDD_COMPLIANCE_LOG``, ``SDD_COMPLIANCE_EVENTS_PATH`` (read by ``providence ask``
    telemetry, see ``utils/telemetry_paths.resolve_compliance_events_path``),
    and ``SDD_TELEMETRY_PATH`` (read by this module's ``_default_events_path``)
    all resolve the same compliance-events JSONL path independently. If an
    operator sets only one, or sets more than one to the same value, there is
    nothing to compare. Only warn when at least two are explicitly set and
    resolve to different paths  never raise or change exit codes.
    """
    override = resolve_compliance_log_override()
    if not override.diverged_vars:
        return
    conflicts = ", ".join(
        f"{name} ({path})" for name, path in override.diverged_vars.items()
    )
    typer.echo(
        "WARN: telemetry event log paths diverge  "
        f"using {override.winner_var} ({override.path}), ignoring: {conflicts}; "
        "providence ask and providence telemetry may read/write different event logs.",
        err=True,
    )


def _resolve_events_path(command: str) -> Path:
    _warn_if_telemetry_paths_diverge()
    try:
        return _default_events_path()
    except RuntimeError as exc:
        abort_workspace_resolution(command, exc, output_json=_ctx_json())


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))
