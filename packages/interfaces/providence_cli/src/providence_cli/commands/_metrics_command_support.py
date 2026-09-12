"""Support helpers for metrics command handlers."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import typer

from providence_cli.shared.contracts import build_error_result, build_ok_result


def emit_missing_file(
    *,
    command: str,
    jsonl_path: Path,
    output_json: bool,
    port: int | None = None,
    console: Any,
    emit_json_fn: Any,
) -> None:
    if output_json:
        data: dict[str, Any] = {"events_file": str(jsonl_path), "exit_code": 1}
        if port is not None:
            data["port"] = port
        payload = build_error_result(
            command,
            code="events_file_not_found",
            message=f"Events file not found: {jsonl_path}",
            data=data,
        )
        emit_json_fn(payload, err=True)
    else:
        console.print(
            f"[red]Error:[/red] Events file not found: {jsonl_path}", style="bold"
        )
    raise typer.Exit(1)


def load_snapshot(jsonl_path: Path) -> Any:
    from providence_runtime.metrics import TokenEconomyCollector
    from providence_runtime.reader import TelemetryReader

    return TokenEconomyCollector.from_reader(TelemetryReader(jsonl_path)).snapshot()


def emit_summary_load_error(
    *, exc: Exception, output_json: bool, console: Any, emit_json_fn: Any
) -> None:
    if output_json:
        payload = build_error_result(
            "metrics summary",
            code="metrics_load_failed",
            message=f"Error loading events: {exc}",
            data={"exit_code": 1},
        )
        emit_json_fn(payload, err=True)
    else:
        console.print(f"[red]Error loading events:[/red] {exc}", style="bold")
    raise typer.Exit(1) from None


def emit_summary_output(
    *,
    snap: Any,
    output_json: bool,
    console: Any,
    build_summary_json_data: Any,
    build_summary_table: Any,
    emit_json_fn: Any,
) -> None:
    if output_json:
        emit_json_fn(build_ok_result("metrics summary", build_summary_json_data(snap)))
        return
    console.print(build_summary_table(snap))
    util_pct = snap.budget_utilization_pct
    color, status = (
        ("red", " BREACH")
        if util_pct >= 100
        else (("yellow", " WARNING (>90%)") if util_pct >= 90 else ("green", " OK"))
    )
    console.print(
        f"\nBudget utilization: [{color}]{util_pct:.1f}%[/{color}] {status}",
        style="bold",
    )
    console.print(
        f"\nEvent summary: {snap.warn_count} warns | {snap.breach_count} breaches | {snap.retry_cap_count} retry caps"
    )


def load_collector(jsonl_path: Path) -> Any:
    from providence_runtime.metrics import TokenEconomyCollector
    from providence_runtime.reader import TelemetryReader

    return TokenEconomyCollector.from_reader(TelemetryReader(jsonl_path))


def emit_serve_load_error(
    *,
    exc: Exception,
    jsonl_path: Path,
    port: int,
    output_json: bool,
    console: Any,
    emit_json_fn: Any,
) -> None:
    if output_json:
        payload = build_error_result(
            "metrics serve",
            {"events_file": str(jsonl_path), "port": port, "exit_code": 1},
            code="metrics_load_failed",
            message=f"Error loading events: {exc}",
        )
        emit_json_fn(payload, err=True)
    else:
        console.print(f"[red]Error loading events:[/red] {exc}", style="bold")
    raise typer.Exit(1) from None


def bind_server(
    *,
    port: int,
    handler_cls: Any,
    jsonl_path: Path,
    output_json: bool,
    console: Any,
    emit_json_fn: Any,
    http_server_cls: Any,
) -> Any:
    try:
        return http_server_cls(("", port), handler_cls)
    except OSError as exc:
        if output_json:
            payload = build_error_result(
                "metrics serve",
                {"events_file": str(jsonl_path), "port": port, "exit_code": 1},
                code="metrics_bind_failed",
                message=f"Cannot bind to port {port}: {exc}",
            )
            emit_json_fn(payload, err=True)
        else:
            console.print(
                f"[red]Error starting metrics server:[/red] cannot bind to port {port}: {exc}",
                style="bold",
            )
        raise typer.Exit(1) from None


def run_server_loop(
    *,
    server: Any,
    reload_thread: threading.Thread,
    stop_event: threading.Event,
    port: int,
    refresh: int,
    console: Any,
) -> None:
    server.timeout = 1.0
    console.print(
        f"[green][SDD][/green] Metrics endpoint: [cyan]http://localhost:{port}/metrics[/cyan]"
    )
    console.print(
        f"[yellow]Reloading JSONL every {refresh}s. Press Ctrl+C to stop.[/yellow]"
    )
    try:
        while not stop_event.is_set():
            server.handle_request()
    except KeyboardInterrupt:
        console.print("[yellow]\n[SDD] Metrics server stopped.[/yellow]")
        raise typer.Exit(0) from None
    finally:
        stop_event.set()
        server.server_close()
        reload_thread.join(timeout=max(2, refresh + 1))
