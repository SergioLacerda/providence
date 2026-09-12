"""Prometheus text-format rendering for EconomySnapshot."""

from __future__ import annotations

from ._economy_snapshot import EconomySnapshot
from ._metric_line import _metric_line as _metric_line_impl
from ._per_model_render import _render_per_model_lines


class PrometheusTextRenderer:
    """Render an EconomySnapshot as Prometheus text exposition format.

    Produces the canonical text format (version 0.0.4) as a UTF-8 string.
    No external dependencies. Complies with OpenMetrics specification.

    Metric families:
      - sdd_tokens_input_total (counter)
      - sdd_tokens_output_total (counter)
      - sdd_tokens_total_total (counter)
      - sdd_cost_usd_total (counter)
      - sdd_llm_calls_total (counter)
      - sdd_budget_utilization_pct (gauge)
      - sdd_budget_warn_total (counter)
      - sdd_budget_breach_total (counter)
      - sdd_retry_cap_total (counter)
      - sdd_tokens_by_model_input_total (counter with model label)
      - sdd_tokens_by_model_output_total (counter with model label)

    Usage::

        renderer = PrometheusTextRenderer()
        prometheus_text = renderer.render(snapshot)
        # Use as HTTP response body with Content-Type: text/plain; version=0.0.4
    """

    _metric_line = staticmethod(_metric_line_impl)

    def render(self, snapshot: EconomySnapshot) -> str:
        """Return the full Prometheus text exposition payload as a str.

        Parameters
        ----------
        snapshot:
            An EconomySnapshot to render.

        Returns
        -------
        Complete Prometheus text format (version 0.0.4) as UTF-8 string.
        """
        lines: list[str] = []

        # Helper: add metric line
        def add_metric(
            name: str,
            value: float | int,
            help_text: str = "",
            metric_type: str = "gauge",
            labels: dict[str, str] | None = None,
        ) -> None:
            if help_text:
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {metric_type}")
            lines.append(self._metric_line(name, value, labels))

        # Global counters
        add_metric(
            "sdd_tokens_input_total",
            snapshot.total_tokens_input,
            help_text="Total input tokens consumed across all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_tokens_output_total",
            snapshot.total_tokens_output,
            help_text="Total output tokens consumed across all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_tokens_total_total",
            snapshot.total_tokens_total,
            help_text="Total tokens (input + output) across all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_cost_usd_total",
            round(snapshot.total_cost_usd, 4),
            help_text="Estimated USD cost of all LLM calls",
            metric_type="counter",
        )
        add_metric(
            "sdd_llm_calls_total",
            snapshot.total_calls,
            help_text="Total number of LLM calls recorded",
            metric_type="counter",
        )
        add_metric(
            "sdd_budget_utilization_pct",
            round(snapshot.budget_utilization_pct, 2),
            help_text="Current budget utilization percentage (latest observed)",
            metric_type="gauge",
        )
        add_metric(
            "sdd_budget_warn_total",
            snapshot.warn_count,
            help_text="Number of budget warn events (>90% utilization)",
            metric_type="counter",
        )
        add_metric(
            "sdd_budget_breach_total",
            snapshot.breach_count,
            help_text="Number of budget breach events (>=100% utilization)",
            metric_type="counter",
        )
        add_metric(
            "sdd_retry_cap_total",
            snapshot.retry_cap_count,
            help_text="Number of retry ceiling breach events",
            metric_type="counter",
        )

        lines.extend(_render_per_model_lines(snapshot, self._metric_line))

        return "\n".join(lines) + "\n"
