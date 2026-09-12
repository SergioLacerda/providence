"""Rendering helpers for telemetry `summary`/`init` command output.

Split out of `_telemetry_command_support.py` (T6,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from providence_runtime.metrics import AskLatencyCollector

from providence_cli.shared.contracts import build_error_result, build_ok_result
from providence_cli.utils.output import emit_json

__all__ = [
    "emit_init",
    "emit_summary",
]


def emit_summary(
    path: Path,
    events: list[dict[str, Any]],
    *,
    phase_id: str | None,
    latency_domain: str | None,
    path_id: str | None,
    output_json: bool,
) -> None:
    collector = AskLatencyCollector()
    for event in events:
        collector.ingest(event)
    snapshot = collector.snapshot()

    groups = [
        {
            "phase_id": key[0],
            "latency_domain": key[1],
            "path_id": key[2],
            "count": group.count,
            "min_ms": group.min_ms,
            "max_ms": group.max_ms,
            "avg_ms": group.avg_ms,
            "p50_ms": group.p50_ms,
            "p95_ms": group.p95_ms,
        }
        for key, group in snapshot.groups.items()
    ]

    if output_json:
        emit_json(
            build_ok_result(
                "telemetry summary",
                {
                    "events_file": str(path),
                    "phase_id": phase_id,
                    "latency_domain": latency_domain,
                    "path_id": path_id,
                    "groups": groups,
                    "exit_code": 0,
                },
            )
        )
        return

    if not groups:
        typer.echo(f"No governance.ask.phase events found at {path}")
        return

    typer.echo(
        f"{'phase_id':<28} {'latency_domain':<16} {'path_id':<10} "
        f"{'count':>6} {'min_ms':>8} {'avg_ms':>8} {'p50_ms':>8} {'p95_ms':>8} {'max_ms':>8}"
    )
    for row in groups:
        typer.echo(
            f"{row['phase_id']:<28} {row['latency_domain']:<16} {row['path_id']:<10} "
            f"{row['count']:>6} {row['min_ms']:>8} {row['avg_ms']:>8.1f} "
            f"{row['p50_ms']:>8} {row['p95_ms']:>8} {row['max_ms']:>8}"
        )


def emit_init(path: Path, result: dict[str, Any], *, output_json: bool) -> None:
    invalid_line = result["invalid_line"]
    if result["created"]:
        if output_json:
            emit_json(
                build_ok_result(
                    "telemetry init",
                    {"events_file": str(path), **result, "exit_code": 0},
                )
            )
            return
        typer.echo(f"Created {path}")
        return

    if invalid_line is not None:
        if output_json:
            emit_json(
                build_error_result(
                    "telemetry init",
                    code="invalid_jsonl",
                    message=f"Invalid JSON at line {invalid_line} in {path}",
                    data={"events_file": str(path), **result, "exit_code": 1},
                ),
                err=True,
            )
            raise typer.Exit(1)
        typer.echo(f"Invalid JSON at line {invalid_line}: {path}", err=True)
        raise typer.Exit(1)

    if output_json:
        emit_json(
            build_ok_result(
                "telemetry init", {"events_file": str(path), **result, "exit_code": 0}
            )
        )
        return
    typer.echo(f"Already exists (valid): {path}")
