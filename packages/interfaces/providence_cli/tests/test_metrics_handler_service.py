from __future__ import annotations

import io
from types import SimpleNamespace

from providence_cli.services.metrics_handler import (
    _CollectorRef,
    build_metrics_handler,
    build_summary_json_data,
    build_summary_table,
)


def _make_snapshot() -> SimpleNamespace:
    return SimpleNamespace(
        total_tokens_input=10,
        total_tokens_output=5,
        total_tokens_total=15,
        total_cost_usd=0.12345,
        budget_utilization_pct=45.0,
        total_calls=2,
        warn_count=1,
        breach_count=0,
        retry_cap_count=0,
        per_model={
            "gpt-test": SimpleNamespace(
                tokens_input=10,
                tokens_output=5,
                tokens_total=15,
                cost_usd=0.12345,
                call_count=2,
            )
        },
    )


def test_build_summary_json_data_rounds_and_embeds_per_model() -> None:
    payload = build_summary_json_data(_make_snapshot())
    assert payload["exit_code"] == 0
    assert payload["summary"]["total_tokens"] == 15
    assert payload["summary"]["total_cost_usd"] == 0.1235
    assert payload["summary"]["per_model"]["gpt-test"]["call_count"] == 2


def test_build_summary_table_contains_model_and_total_rows() -> None:
    table = build_summary_table(_make_snapshot())
    assert table.title == "Token Economy Summary"
    assert len(table.rows) == 2


def test_build_metrics_handler_serves_metrics(monkeypatch) -> None:
    class _Renderer:
        def render(self, snap) -> str:  # noqa: ANN001
            assert snap.total_tokens_total == 15
            return "metric 1\n"

    monkeypatch.setattr("providence_runtime.metrics.PrometheusTextRenderer", _Renderer)
    handler_cls = build_metrics_handler(
        _CollectorRef(SimpleNamespace(snapshot=_make_snapshot))
    )
    handler = object.__new__(handler_cls)
    sent: list[tuple[str, str | int]] = []
    handler.path = "/metrics"
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: sent.append(("status", code))
    handler.send_header = lambda key, value: sent.append((key, value))
    handler.end_headers = lambda: sent.append(("ended", "yes"))
    handler.do_get()
    handler.log_message("ignored")
    assert ("status", 200) in sent
    assert ("Content-Length", str(len("metric 1\n"))) in sent
    assert handler.wfile.getvalue() == b"metric 1\n"


def test_build_metrics_handler_serves_404(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_runtime.metrics.PrometheusTextRenderer",
        type("_Renderer", (), {"render": lambda self, snap: "unused"}),
    )
    handler_cls = build_metrics_handler(
        _CollectorRef(SimpleNamespace(snapshot=_make_snapshot))
    )
    handler = object.__new__(handler_cls)
    sent: list[tuple[str, str | int]] = []
    handler.path = "/other"
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: sent.append(("status", code))
    handler.send_header = lambda key, value: sent.append((key, value))
    handler.end_headers = lambda: sent.append(("ended", "yes"))
    handler.do_get()
    assert ("status", 404) in sent
    assert handler.wfile.getvalue() == b"Not Found\n"
