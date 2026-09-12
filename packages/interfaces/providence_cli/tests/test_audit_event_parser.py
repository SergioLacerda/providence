"""Unit tests for providence_cli.services.audit_event_parser."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from providence_cli.services.audit_event_parser import (
    _drift_cause,
    _drift_type,
    _event_ts,
    _is_ask_invocation,
    _is_ask_phase_event,
    _is_drift_event,
    _load_events,
    _parse_int,
    _parse_ts,
    _ts_sort_key,
    _window_events,
)
from providence_cli.services.audit_quality_score import (
    _as_score,
    _has_quality_signals,
    _quality_score,
)


class TestParseInt:
    def test_returns_none_for_bool(self) -> None:
        assert _parse_int(True) is None
        assert _parse_int(False) is None

    def test_returns_int_from_float(self) -> None:
        assert _parse_int(3.7) == 3

    def test_returns_none_for_non_digit_string(self) -> None:
        assert _parse_int("abc") is None
        assert _parse_int("1.5") is None

    def test_returns_int_from_digit_string(self) -> None:
        assert _parse_int("42") == 42

    def test_returns_none_for_other_types(self) -> None:
        assert _parse_int(None) is None
        assert _parse_int([]) is None


class TestEventTs:
    def test_returns_empty_string_when_no_ts_fields(self) -> None:
        assert _event_ts({}) == ""
        assert _event_ts({"command": "ask"}) == ""


class TestParseTs:
    def test_returns_none_for_empty_string(self) -> None:
        assert _parse_ts("") is None

    def test_returns_none_for_invalid_iso(self) -> None:
        assert _parse_ts("not-a-date") is None

    def test_handles_naive_datetime(self) -> None:
        result = _parse_ts("2026-01-15T10:00:00")
        assert result is not None
        assert result.tzinfo == timezone.utc


class TestTsSortKey:
    def test_empty_string_returns_zero_key(self) -> None:
        assert _ts_sort_key("") == (0, "")

    def test_invalid_ts_returns_one_with_original(self) -> None:
        key = _ts_sort_key("garbage")
        assert key[0] == 1
        assert key[1] == "garbage"


class TestLoadEvents:
    def test_returns_empty_list_for_missing_file(self, tmp_path: Path) -> None:
        assert _load_events(tmp_path / "nonexistent.jsonl") == []

    def test_skips_invalid_json_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\nnot-json\n{"ok": 2}\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 2

    def test_skips_non_dict_json_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\n[1,2,3]\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 1

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "events.jsonl"
        path.write_text('{"ok": 1}\n\n{"ok": 2}\n', encoding="utf-8")
        result = _load_events(path)
        assert len(result) == 2


class TestIsAskInvocation:
    def test_true_for_parent_ask_event(self) -> None:
        event = {"event": "governance.ask", "command": "ask"}
        assert _is_ask_invocation(event) is True

    def test_false_for_phase_sub_event_even_with_ask_command(self) -> None:
        event = {"event": "governance.ask.phase", "command": "ask"}
        assert _is_ask_invocation(event) is False

    def test_false_for_compile_events(self) -> None:
        event = {
            "event": "governance.compile.complete",
            "command": "governance compile",
        }
        assert _is_ask_invocation(event) is False

    def test_false_for_lifecycle_events(self) -> None:
        event = {"event": "runtime.session.start", "command": "runtime status"}
        assert _is_ask_invocation(event) is False

    def test_false_for_missing_event_name(self) -> None:
        assert _is_ask_invocation({"command": "ask"}) is False
        assert _is_ask_invocation({}) is False


class TestIsAskPhaseEvent:
    def test_true_for_phase_sub_event(self) -> None:
        event = {"event": "governance.ask.phase", "command": "ask"}
        assert _is_ask_phase_event(event) is True

    def test_false_for_parent_ask_event(self) -> None:
        event = {"event": "governance.ask", "command": "ask"}
        assert _is_ask_phase_event(event) is False

    def test_false_for_non_ask_events(self) -> None:
        assert _is_ask_phase_event({"event": "governance.compile.complete"}) is False
        assert _is_ask_phase_event({}) is False


class TestIsDriftEvent:
    def test_detects_drift_type_not_none(self) -> None:
        event = {"event": "x", "details": {"drift_type": "profile_drift"}}
        assert _is_drift_event(event) is True

    def test_ignores_drift_type_none(self) -> None:
        event = {"event": "x", "details": {"drift_type": "none"}}
        assert _is_drift_event(event) is False


class TestDriftType:
    def test_returns_missing_when_no_drift_type(self) -> None:
        assert _drift_type({"details": {}}) == "missing_drift_type"
        assert _drift_type({}) == "missing_drift_type"

    def test_returns_drift_type_when_present(self) -> None:
        assert (
            _drift_type({"details": {"drift_type": "profile_drift"}}) == "profile_drift"
        )


class TestDriftCause:
    def test_returns_found_cause(self) -> None:
        event = {"details": {"drift_cause": "config mismatch"}}
        assert _drift_cause(event) == "config mismatch"

    def test_returns_empty_when_no_cause(self) -> None:
        assert _drift_cause({}) == ""


class TestWindowEvents:
    def test_excludes_events_with_unparseable_timestamps(self) -> None:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        recent_ts = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        events = [
            {"event": "x", "start_ts": "not-a-date"},
            {"event": "y", "start_ts": recent_ts},
        ]
        result = _window_events(events, now_utc=now, days=30)
        assert len(result) == 1


class TestHasQualitySignals:
    def test_returns_true_when_tests_passed_present(self) -> None:
        events = [{"details": {"tests_passed": True}}]
        assert _has_quality_signals(events) is True

    def test_returns_false_when_non_dict_details(self) -> None:
        events = [{"details": "string_details"}, {"no_details": True}]
        assert _has_quality_signals(events) is False


class TestAsScore:
    def test_bool_true(self) -> None:
        assert _as_score(True) == 1.0
        assert _as_score(False) == 0.0

    def test_numeric_clamped(self) -> None:
        assert _as_score(0.5) == 0.5
        assert _as_score(2.0) == 1.0
        assert _as_score(-1.0) == 0.0

    def test_string_truthy(self) -> None:
        for val in ("true", "pass", "passed", "ok", "accepted", "yes"):
            assert _as_score(val) == 1.0

    def test_string_falsy(self) -> None:
        for val in ("false", "fail", "failed", "rejected", "no"):
            assert _as_score(val) == 0.0

    def test_unknown_string_returns_zero(self) -> None:
        assert _as_score("maybe") == 0.0


class TestQualityScore:
    def test_returns_none_when_no_signals(self) -> None:
        assert _quality_score([]) is None
        assert _quality_score([{"details": {}}]) is None

    def test_skips_non_dict_details(self) -> None:
        events = [{"details": "not-a-dict"}, {"details": {"tests_passed": True}}]
        result = _quality_score(events)
        assert result is not None

    def test_uses_tests_passed(self) -> None:
        events = [{"details": {"tests_passed": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(60.0)

    def test_uses_human_accepted(self) -> None:
        events = [{"details": {"human_accepted": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(40.0)

    def test_combines_both_signals(self) -> None:
        events = [{"details": {"tests_passed": True, "human_accepted": True}}]
        result = _quality_score(events)
        assert result == pytest.approx(100.0)
