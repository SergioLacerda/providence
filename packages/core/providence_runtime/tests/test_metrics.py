from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_runtime.metrics import (
    EconomySnapshot,
    ModelMetrics,
    PrometheusTextRenderer,
    TokenEconomyCollector,
    _load_token_budget_config,
)


class _FakeReader:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    def list_events(self) -> list[dict[str, Any]]:
        return self._events


def test_load_token_budget_config_defaults(monkeypatch: Any) -> None:
    monkeypatch.delenv("SDD_TOKEN_BUDGET_CEILING", raising=False)
    monkeypatch.delenv("SDD_CONTEXT_COMPRESSION_THRESHOLD", raising=False)
    monkeypatch.delenv("SDD_CONTEXT_COMPRESSION_TARGET", raising=False)
    cfg = _load_token_budget_config()
    assert cfg["token_budget_ceiling"] == 100000
    assert cfg["context_compression_threshold"] == 70.0
    assert cfg["context_compression_target"] == 50.0


def test_load_token_budget_config_env_override(monkeypatch: Any) -> None:
    monkeypatch.setenv("SDD_TOKEN_BUDGET_CEILING", "999")
    monkeypatch.setenv("SDD_CONTEXT_COMPRESSION_THRESHOLD", "71.5")
    monkeypatch.setenv("SDD_CONTEXT_COMPRESSION_TARGET", "49.0")
    cfg = _load_token_budget_config()
    assert cfg["token_budget_ceiling"] == 999
    assert cfg["context_compression_threshold"] == 71.5
    assert cfg["context_compression_target"] == 49.0


def test_load_token_budget_config_pyproject(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SDD_TOKEN_BUDGET_CEILING", raising=False)
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.sdd.runtime]
token_budget_ceiling = 12345
context_compression_threshold = 66
context_compression_target = 44
""".strip(),
        encoding="utf-8",
    )
    cfg = _load_token_budget_config()
    assert cfg["token_budget_ceiling"] == 12345
    assert cfg["context_compression_threshold"] == 66
    assert cfg["context_compression_target"] == 44


def test_collector_ingest_consume_and_counters(monkeypatch: Any) -> None:
    monkeypatch.setenv("SDD_TOKEN_BUDGET_CEILING", "1000")
    c = TokenEconomyCollector()
    c.ingest(
        {
            "event": "economy.token.consume",
            "tokens_input": 100,
            "tokens_output": 50,
            "tokens_total": 150,
            "details": {"model": 'gpt-"x"', "cost_usd": 0.25},
        }
    )
    c.ingest({"event": "economy.budget.warn"})
    c.ingest({"event": "economy.budget.breach.usd"})
    c.ingest({"event": "economy.retry.cap.reached"})

    snap = c.snapshot()
    assert snap.total_tokens_input == 100
    assert snap.total_tokens_output == 50
    assert snap.total_tokens_total == 150
    assert snap.total_calls == 1
    assert snap.warn_count == 1
    assert snap.breach_count == 1
    assert snap.retry_cap_count == 1
    assert snap.budget_utilization_pct == 15.0
    assert snap.per_model['gpt-"x"'].call_count == 1


def test_collector_ingest_handles_non_dict_details_and_zero_ceiling(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("SDD_TOKEN_BUDGET_CEILING", "0")
    c = TokenEconomyCollector()
    c.ingest(
        {
            "event": "economy.token.consume",
            "tokens_input": 1,
            "tokens_output": 1,
            "tokens_total": 2,
            "details": "not-a-dict",
        }
    )
    snap = c.snapshot()
    assert snap.total_tokens_total == 2
    assert snap.budget_utilization_pct == 0.0


def test_collector_from_reader_filters_relevant_events() -> None:
    reader = _FakeReader(
        [
            {"event": "other.event"},
            {"event": "economy.token.consume", "tokens_total": 3, "details": {}},
            {"event": "economy.budget.warn.tokens"},
            {"event": "economy.retry.cap.reached"},
        ]
    )
    c = TokenEconomyCollector.from_reader(reader)  # type: ignore[arg-type]
    snap = c.snapshot()
    assert snap.total_calls == 1
    assert snap.total_tokens_total == 3
    assert snap.warn_count == 1
    assert snap.retry_cap_count == 1


def test_collector_snapshot_is_copy_and_reset_works() -> None:
    c = TokenEconomyCollector()
    c.ingest({"event": "economy.token.consume", "tokens_total": 1, "details": {}})
    snap1 = c.snapshot()
    snap1.per_model["x"] = ModelMetrics(tokens_total=999)
    snap2 = c.snapshot()
    assert "x" not in snap2.per_model
    c.reset()
    snap3 = c.snapshot()
    assert snap3.total_tokens_total == 0


def test_prometheus_renderer_with_and_without_per_model_labels_escaping() -> None:
    snap = EconomySnapshot(
        total_tokens_input=10,
        total_tokens_output=20,
        total_tokens_total=30,
        total_cost_usd=1.23456,
        total_calls=2,
        budget_utilization_pct=12.345,
        warn_count=1,
        breach_count=0,
        retry_cap_count=1,
        per_model={
            'gpt-"x"\n': ModelMetrics(
                tokens_input=1,
                tokens_output=2,
                tokens_total=3,
                cost_usd=0.5,
                call_count=1,
            )
        },
    )
    text = PrometheusTextRenderer().render(snap)
    assert "sdd_tokens_input_total 10" in text
    assert "sdd_cost_usd_total 1.2346" in text
    assert 'model="gpt-\\"x\\"\\n"' in text
    assert text.endswith("\n")
