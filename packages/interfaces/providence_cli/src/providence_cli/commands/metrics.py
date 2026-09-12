"""sdd metrics  token economy metrics commands.

Subcommands:
  sdd metrics summary    print token economy table (rich formatted)
  sdd metrics serve      start Prometheus scrape endpoint (foreground daemon)
"""

from __future__ import annotations

import http.server
import os
import threading
from pathlib import Path
from typing import Any

import click
import typer
from rich.console import Console

from providence_cli.commands._metrics_command_support import (
    bind_server,
    emit_missing_file,
    emit_serve_load_error,
    emit_summary_load_error,
    emit_summary_output,
    load_collector,
    load_snapshot,
    run_server_loop,
)
from providence_cli.services.command_group_output import show_command_group
from providence_cli.services.metrics_handler import (
    _CollectorRef,
    _resolve_jsonl_path,
    _start_reload_worker,
    build_metrics_handler,
    build_summary_json_data,
    build_summary_table,
)
from providence_cli.utils.output import emit_json, is_json_mode

app = typer.Typer(
    help="Token economy metrics commands",
    invoke_without_command=True,
)
console = Console()

_DEFAULT_METRICS_PORT = 9090


@app.callback(invoke_without_command=True)
def _(
    ctx: typer.Context,
    list_commands: bool = typer.Option(False, "--list", help="List metrics commands."),
) -> None:
    """Token economy metrics and Prometheus exposition."""
    if list_commands or ctx.invoked_subcommand is None:
        show_command_group("Metrics", ["summary", "serve"])
        raise typer.Exit(0)


def _is_json_mode(ctx: typer.Context) -> bool:
    """Check if --json global flag is set via context params."""
    if ctx is not None and isinstance(getattr(ctx, "obj", None), dict):
        return is_json_mode(ctx)
    return is_json_mode(click.get_current_context(silent=True))


def _emit_missing_file(
    command: str, jsonl_path: Path, *, output_json: bool, port: int | None = None
) -> None:
    emit_missing_file(
        command=command,
        jsonl_path=jsonl_path,
        output_json=output_json,
        port=port,
        console=console,
        emit_json_fn=emit_json,
    )


def _emit_summary_load_error(exc: Exception, *, output_json: bool) -> None:
    emit_summary_load_error(
        exc=exc, output_json=output_json, console=console, emit_json_fn=emit_json
    )


def _emit_serve_load_error(
    exc: Exception, *, jsonl_path: Path, port: int, output_json: bool
) -> None:
    emit_serve_load_error(
        exc=exc,
        jsonl_path=jsonl_path,
        port=port,
        output_json=output_json,
        console=console,
        emit_json_fn=emit_json,
    )


def _bind_server(
    *, port: int, handler_cls: Any, jsonl_path: Path, output_json: bool
) -> Any:
    return bind_server(
        port=port,
        handler_cls=handler_cls,
        jsonl_path=jsonl_path,
        output_json=output_json,
        console=console,
        emit_json_fn=emit_json,
        http_server_cls=http.server.HTTPServer,
    )


@app.command()
def summary(
    ctx: typer.Context,
    jsonl: Path = typer.Option(
        None, help="Path to events JSONL (auto-detected if omitted)"
    ),
    last_hours: int = typer.Option(
        None, "--last-hours", "-n", help="Limit to last N hours"
    ),
) -> None:
    """Print token economy summary table."""
    jsonl_path = _resolve_jsonl_path(jsonl)
    output_json = _is_json_mode(ctx)
    if not jsonl_path.exists():
        _emit_missing_file("metrics summary", jsonl_path, output_json=output_json)
    try:
        snap = load_snapshot(jsonl_path)
    except Exception as exc:
        _emit_summary_load_error(exc, output_json=output_json)
    emit_summary_output(
        snap=snap,
        output_json=output_json,
        console=console,
        build_summary_json_data=build_summary_json_data,
        build_summary_table=build_summary_table,
        emit_json_fn=emit_json,
    )


@app.command()
def serve(  # noqa: C901
    port: int = typer.Option(
        int(os.environ.get("SDD_METRICS_PORT", _DEFAULT_METRICS_PORT)),
        "--port",
        "-p",
        help="Port to expose /metrics on (default: SDD_METRICS_PORT or 9090)",
    ),
    jsonl: Path = typer.Option(
        None, help="Path to events JSONL (auto-detected if omitted)"
    ),
    refresh: int = typer.Option(
        30,
        "--refresh",
        "-r",
        help="Seconds between JSONL reload cycles (default: 30)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        help="Emit canonical JSON envelope for startup failures.",
    ),
) -> None:
    """Start Prometheus metrics scrape endpoint (foreground, Ctrl+C to stop)."""
    jsonl_path = _resolve_jsonl_path(jsonl)
    if not jsonl_path.exists():
        _emit_missing_file(
            "metrics serve", jsonl_path, output_json=json_output, port=port
        )
    try:
        collector = load_collector(jsonl_path)
    except Exception as exc:
        _emit_serve_load_error(
            exc, jsonl_path=jsonl_path, port=port, output_json=json_output
        )
    collector_ref = _CollectorRef(collector)
    stop_event = threading.Event()
    MetricsHandler = build_metrics_handler(collector_ref)
    server = _bind_server(
        port=port,
        handler_cls=MetricsHandler,
        jsonl_path=jsonl_path,
        output_json=json_output,
    )
    reload_thread = _start_reload_worker(
        jsonl_path=jsonl_path,
        refresh=refresh,
        collector_ref=collector_ref,
        stop_event=stop_event,
    )
    run_server_loop(
        server=server,
        reload_thread=reload_thread,
        stop_event=stop_event,
        port=port,
        refresh=refresh,
        console=console,
    )
