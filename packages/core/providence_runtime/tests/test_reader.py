from __future__ import annotations

import json
from pathlib import Path

from providence_runtime.reader import BudgetStatus, TelemetryReader, TokenStats


def _write_jsonl(path: Path, events: list[dict]) -> None:
    lines = [json.dumps(e) for e in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_reader_missing_file_graceful(tmp_path: Path) -> None:
    reader = TelemetryReader(tmp_path / "missing.jsonl")
    assert reader.get_event_count() == 0
    assert reader.list_events() == []
    assert reader.get_latest_events() == []


def test_reader_skips_malformed_lines(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    p.write_text('{"event":"ok"}\n{bad-json}\n{"event":"ok2"}\n', encoding="utf-8")
    reader = TelemetryReader(p)
    assert reader.get_event_count() == 2


def test_get_events_by_type_and_time_filter(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    events = [
        {"event": "economy.token.consume", "ts": "2099-01-01T00:00:00Z"},
        {"event": "economy.token.consume", "ts": "2000-01-01T00:00:00Z"},
        {"event": "economy.token.consume", "ts": "bad-ts"},
        {"event": "other", "ts": "2099-01-01T00:00:00Z"},
    ]
    _write_jsonl(p, events)
    reader = TelemetryReader(p)
    all_consume = reader.get_events_by_type("economy.token.consume")
    assert len(all_consume) == 3
    recent = reader.get_events_by_type("economy.token.consume", last_hours=1)
    assert len(recent) == 1


def test_token_stats_and_to_dict(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    events = [
        {
            "event": "economy.token.consume",
            "tokens_input": 10,
            "tokens_output": 5,
            "tokens_total": 15,
            "details": {"model": "m1", "cost_usd": 0.1},
        },
        {
            "event": "economy.token.consume",
            "tokens_input": 2,
            "tokens_output": 3,
            "tokens_total": 5,
            "details": {"model": "m2", "cost_usd": 0.2},
        },
        {"event": "economy.token.consume", "tokens_total": 1, "details": "non-dict"},
    ]
    _write_jsonl(p, events)
    reader = TelemetryReader(p)
    stats = reader.get_token_stats()
    assert isinstance(stats, TokenStats)
    assert stats.total_tokens == 21
    assert stats.total_input_tokens == 12
    assert stats.total_output_tokens == 8
    assert stats.event_count == 3
    assert stats.unique_models == {"m1", "m2"}
    assert stats.avg_tokens_per_event == 7.0
    payload = stats.to_dict()
    assert payload["unique_models"] == ["m1", "m2"]
    assert payload["cost_usd"] == 0.3


def test_error_rate_with_and_without_time_filter(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    events = [
        {"event": "e1", "status": "ok", "ts": "2099-01-01T00:00:00Z"},
        {"event": "e1", "status": "fail", "ts": "2099-01-01T00:00:00Z"},
        {"event": "e2", "status": "fail", "ts": "2000-01-01T00:00:00Z"},
        {"event": "e3", "status": "fail", "ts": "bad"},
    ]
    _write_jsonl(p, events)
    reader = TelemetryReader(p)
    full = reader.get_error_rate()
    assert full["total_events"] == 4
    assert full["error_events"] == 3
    assert full["error_types"]["e1"] == 1
    recent = reader.get_error_rate(last_hours=1)
    assert recent["total_events"] == 2
    assert recent["error_events"] == 1


def test_error_rate_empty() -> None:
    reader = TelemetryReader(Path("/non-existent-events.jsonl"))
    r = reader.get_error_rate()
    assert r["total_events"] == 0
    assert r["error_rate"] == 0.0


def test_budget_status_with_and_without_budget_events(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    _write_jsonl(p, [{"event": "x"}])
    reader = TelemetryReader(p)
    empty_status = reader.get_budget_status()
    assert isinstance(empty_status, BudgetStatus)
    assert empty_status.max_tokens == 0

    _write_jsonl(
        p,
        [
            {"event": "economy.budget.warn", "details": {"consumed": 80, "limit": 100}},
            {
                "event": "economy.budget.breach",
                "details": {"consumed": 120, "limit": 100},
            },
        ],
    )
    reader = TelemetryReader(p)
    status = reader.get_budget_status()
    assert status.consumed_tokens == 120
    assert status.max_tokens == 100
    assert status.utilization_pct == 120.0
    assert status.in_red_zone is True
    assert status.in_breach is True
    payload = status.to_dict()
    assert payload["in_breach"] is True


def test_agent_status_latest_and_clear_cache(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    events = [
        {"event": "e1", "agent_id": "a1", "status": "ok"},
        {"event": "e2", "agent_id": "a2", "status": "fail"},
        {"event": "e3", "agent_id": "a1", "status": "warn"},
    ]
    _write_jsonl(p, events)
    reader = TelemetryReader(p)
    assert len(reader.get_events_by_agent("a1")) == 2
    assert len(reader.get_events_by_status("fail")) == 1
    assert len(reader.get_latest_events(2)) == 2
    _write_jsonl(p, events + [{"event": "e4", "agent_id": "a1", "status": "ok"}])
    reader.clear_cache()
    assert reader.get_event_count() == 4
