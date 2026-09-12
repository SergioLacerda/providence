"""Per-model Prometheus metric lines for EconomySnapshot."""

from __future__ import annotations

from collections.abc import Callable

from ._economy_snapshot import EconomySnapshot


def _render_per_model_lines(
    snapshot: EconomySnapshot,
    metric_line: Callable[..., str],
) -> list[str]:
    """Return Prometheus text lines for the per-model metric families.

    Returns an empty list when ``snapshot.per_model`` is empty.
    """
    if not snapshot.per_model:
        return []

    lines: list[str] = []

    lines.append("# HELP sdd_tokens_by_model_input_total Input tokens per model")
    lines.append("# TYPE sdd_tokens_by_model_input_total counter")
    for model, metrics in sorted(snapshot.per_model.items()):
        lines.append(
            metric_line(
                "sdd_tokens_by_model_input_total",
                metrics.tokens_input,
                labels={"model": model},
            )
        )

    lines.append("# HELP sdd_tokens_by_model_output_total Output tokens per model")
    lines.append("# TYPE sdd_tokens_by_model_output_total counter")
    for model, metrics in sorted(snapshot.per_model.items()):
        lines.append(
            metric_line(
                "sdd_tokens_by_model_output_total",
                metrics.tokens_output,
                labels={"model": model},
            )
        )

    lines.append(
        "# HELP sdd_tokens_by_model_total_total Total tokens (input+output) per model"
    )
    lines.append("# TYPE sdd_tokens_by_model_total_total counter")
    for model, metrics in sorted(snapshot.per_model.items()):
        lines.append(
            metric_line(
                "sdd_tokens_by_model_total_total",
                metrics.tokens_total,
                labels={"model": model},
            )
        )

    lines.append("# HELP sdd_cost_usd_by_model_total USD cost per model")
    lines.append("# TYPE sdd_cost_usd_by_model_total counter")
    for model, metrics in sorted(snapshot.per_model.items()):
        lines.append(
            metric_line(
                "sdd_cost_usd_by_model_total",
                round(metrics.cost_usd, 4),
                labels={"model": model},
            )
        )

    lines.append("# HELP sdd_llm_calls_by_model_total Number of LLM calls per model")
    lines.append("# TYPE sdd_llm_calls_by_model_total counter")
    for model, metrics in sorted(snapshot.per_model.items()):
        lines.append(
            metric_line(
                "sdd_llm_calls_by_model_total",
                metrics.call_count,
                labels={"model": model},
            )
        )

    return lines
