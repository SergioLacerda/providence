"""providence ask  budget zone resolution and runtime token metric helpers."""

from __future__ import annotations

import logging
import os
import time

from providence_cli.services.ask_types import _AskInputs
from providence_cli.utils.providence_console import format_sdd_phase_line

from ._phase_timer import PhaseTimer
from ._telemetry import _capture_effective_tokens_with_source

logger = logging.getLogger(__name__)


def _maybe_record_llm_exchange_phase(timer: PhaseTimer) -> None:
    """Record `ask.external.llm_exchange` only when adapter-reported.

    Reads the optional `SDD_ADAPTER_LLM_EXCHANGE_MS` env var, the minimal
    viable channel for an IDE/adapter to report externally-observed LLM
    exchange latency that `providence_cli` cannot measure locally. If unset or not
    a valid non-negative integer, no phase is recorded  never fabricate a
    `0ms` measurement.
    """
    raw = os.environ.get("SDD_ADAPTER_LLM_EXCHANGE_MS", "").strip()
    if not raw:
        return
    try:
        duration_ms = int(raw)
    except ValueError:
        return
    if duration_ms < 0:
        return
    timer.record_external(
        "ask.external.llm_exchange",
        latency_domain="external_llm",
        duration_ms=duration_ms,
        measurement_quality="adapter_reported",
        observed_by="adapter",
    )


def print_ask_console_summary(timer: PhaseTimer, *, entry_mono: float) -> None:
    """Print the default-on compact `[SDD] <phase>  <Xs>` timing summary.

    Replaces the previous `--full`-only raw dump as the default,
    human-readable view (design.md 4). The raw `--full` dump remains
    available unchanged for deep debugging (`ask_response.py`). Callers must
    check `_json_mode()` first  this always prints to stdout via
    `typer.echo`, machine (JSON) output has no use for it.
    """
    import typer

    for record in timer.records():
        if record.duration_ms <= 0:
            continue
        typer.echo(format_sdd_phase_line(record.phase_id, record.duration_ms))
    total_ms = int((time.monotonic() - entry_mono) * 1000)
    typer.echo(format_sdd_phase_line("Total", total_ms))
    # Soft, non-blocking watchdog warnings (design.md 3)  never raised,
    # never affects the command's exit code or duration.
    for record in timer.slow_records():
        threshold_ms = timer.threshold_for(record.phase_id)
        typer.echo(
            f"[SDD] {record.phase_id} is slow\n"
            f"      elapsed={record.duration_ms / 1000:.2f}s"
            f"  threshold={(threshold_ms or 0) / 1000:.2f}s",
            err=True,
        )


def _resolve_runtime_token_metrics(
    inputs: _AskInputs, output_text: str
) -> tuple[int | None, int | None, str]:
    from providence_cli.commands import _ask_backend as _backend

    tokens_in, tokens_out, token_source = _capture_effective_tokens_with_source(
        inputs.tokens_input, inputs.tokens_output
    )
    if tokens_in is None or tokens_out is None:
        est_in, est_out, est_source = _backend._resolve_tokens(
            inputs.query, output_text
        )
        if tokens_in is None:
            tokens_in = est_in
        if tokens_out is None:
            tokens_out = est_out
        if token_source in {"", "unknown"}:
            token_source = est_source
    return tokens_in, tokens_out, token_source
