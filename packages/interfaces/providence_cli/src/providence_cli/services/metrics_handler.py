"""Thread-safe collector state, reload worker, and path helpers for metrics commands."""

from __future__ import annotations

import http.server
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from rich.table import Table

from providence_cli.shared.constants import RUNTIME_DIR as _RUNTIME_DIR

if TYPE_CHECKING:
    from providence_runtime.metrics import EconomySnapshot

_EVENTS_FILENAME = "compliance-events.jsonl"


class _CollectorRef:
    """Thread-safe mutable reference to the active collector."""

    def __init__(self, collector: object) -> None:
        self._lock = threading.RLock()
        self._collector = collector

    def swap(self, collector: object) -> None:
        with self._lock:
            self._collector = collector

    def snapshot(self) -> EconomySnapshot:
        with self._lock:
            return cast("EconomySnapshot", self._collector.snapshot())  # type: ignore[attr-defined]


def _start_reload_worker(
    *,
    jsonl_path: Path,
    refresh: int,
    collector_ref: _CollectorRef,
    stop_event: threading.Event,
) -> threading.Thread:
    """Start periodic collector reload worker with deterministic shutdown."""
    from providence_runtime.metrics import TokenEconomyCollector
    from providence_runtime.reader import TelemetryReader

    def reload_collector() -> None:
        while not stop_event.is_set():
            # Wait with cancellation support instead of sleep(refresh)
            if stop_event.wait(refresh):
                break
            try:
                reader = TelemetryReader(jsonl_path)
                new_collector = TokenEconomyCollector.from_reader(reader)
                collector_ref.swap(new_collector)
            except Exception:  # nosec B110
                # Silently ignore reload errors; keep previous collector active
                pass

    worker = threading.Thread(
        target=reload_collector,
        name="sdd-metrics-reloader",
        # Preserve daemon semantics of caller thread for test harness compatibility.
        daemon=threading.current_thread().daemon,
    )
    worker.start()
    return worker


def _resolve_jsonl_path(jsonl: Path | None) -> Path:
    """Resolve the JSONL events file path.

    Priority:
    1. Explicit --jsonl argument
    2. {cwd}/.providence/runtime/compliance-events.jsonl
    3. Fallback to just the filename (for testing)
    """
    if jsonl:
        return jsonl

    default = _RUNTIME_DIR / _EVENTS_FILENAME
    return default


def build_summary_json_data(snap: EconomySnapshot) -> dict[str, Any]:
    """Build the JSON-mode payload data for `sdd metrics summary`."""
    return {
        "summary": {
            "total_tokens": snap.total_tokens_total,
            "total_cost_usd": round(snap.total_cost_usd, 4),
            "budget_utilization_pct": snap.budget_utilization_pct,
            "total_calls": snap.total_calls,
            "warn_count": snap.warn_count,
            "breach_count": snap.breach_count,
            "retry_cap_count": snap.retry_cap_count,
            "per_model": {
                model: {
                    "tokens_input": m.tokens_input,
                    "tokens_output": m.tokens_output,
                    "tokens_total": m.tokens_total,
                    "cost_usd": round(m.cost_usd, 4),
                    "call_count": m.call_count,
                }
                for model, m in snap.per_model.items()
            },
        },
        "exit_code": 0,
    }


def build_summary_table(snap: EconomySnapshot) -> Table:
    """Build the rich Table for `sdd metrics summary` text output."""
    table = Table(title="Token Economy Summary")
    table.add_column("Model", style="cyan")
    table.add_column("Input Tokens", justify="right", style="magenta")
    table.add_column("Output Tokens", justify="right", style="magenta")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (USD)", justify="right", style="green")
    table.add_column("Calls", justify="right")

    for model in sorted(snap.per_model.keys()):
        m = snap.per_model[model]
        table.add_row(
            model,
            str(m.tokens_input),
            str(m.tokens_output),
            str(m.tokens_total),
            f"${m.cost_usd:.4f}",
            str(m.call_count),
        )

    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{snap.total_tokens_input}[/bold]",
        f"[bold]{snap.total_tokens_output}[/bold]",
        f"[bold]{snap.total_tokens_total}[/bold]",
        f"[bold green]${snap.total_cost_usd:.4f}[/bold green]",
        f"[bold]{snap.total_calls}[/bold]",
    )

    return table


def build_metrics_handler(
    collector_ref: _CollectorRef,
) -> type[http.server.BaseHTTPRequestHandler]:
    """Build the `/metrics` HTTP request handler bound to `collector_ref`."""
    from providence_runtime.metrics import PrometheusTextRenderer

    class MetricsHandler(http.server.BaseHTTPRequestHandler):
        def do_get(self) -> None:
            if self.path == "/metrics":
                snap = collector_ref.snapshot()
                renderer = PrometheusTextRenderer()
                prometheus_text = renderer.render(snap)

                self.send_response(200)
                self.send_header(
                    "Content-Type", "text/plain; version=0.0.4; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(prometheus_text)))
                self.end_headers()
                self.wfile.write(prometheus_text.encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Found\n")

        def log_message(self, format: str, *args: object) -> None:
            # Suppress default logging
            pass

    return MetricsHandler
