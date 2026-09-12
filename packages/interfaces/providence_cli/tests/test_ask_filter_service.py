"""Unit tests for ask_filter service module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from providence_cli.services.ask_filter import (
    _load_tail_row,
    _process_tail_row,
    _row_is_before_cutoff,
    _safe_parse_iso,
    _update_learning_signals,
    collect_learning_signals,
    count_signals_from_tail,
    filter_signals,
)

pytestmark = pytest.mark.unit


def _make_signals() -> dict[str, int]:
    return {
        "diagnosis_inconclusive": 0,
        "evidence_insufficient": 0,
        "scope_violation": 0,
        "drift_recent_failures": 0,
        "observed_events": 0,
        "window_days": 7,
    }


def _ts(delta_seconds: int = 0) -> str:
    """Return ISO timestamp relative to now."""
    dt = datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


class TestSafeParseIso:
    def test_parses_z_suffix(self) -> None:
        result = _safe_parse_iso("2026-01-01T12:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_parses_offset(self) -> None:
        result = _safe_parse_iso("2026-01-01T12:00:00+00:00")
        assert result is not None

    def test_returns_none_on_invalid(self) -> None:
        assert _safe_parse_iso("not-a-date") is None
        assert _safe_parse_iso("") is None


class TestLoadTailRow:
    def test_parses_valid_json(self) -> None:
        raw = json.dumps({"event": "test", "ts": "2026-01-01"}).encode()
        row = _load_tail_row(raw)
        assert row == {"event": "test", "ts": "2026-01-01"}

    def test_returns_none_for_empty(self) -> None:
        assert _load_tail_row(b"") is None
        assert _load_tail_row(b"   ") is None

    def test_returns_none_for_invalid_json(self) -> None:
        assert _load_tail_row(b"not json") is None

    def test_returns_none_for_non_dict_json(self) -> None:
        assert _load_tail_row(b"[1, 2, 3]") is None


class TestRowIsBeforeCutoff:
    def test_row_before_cutoff_returns_true(self) -> None:
        import time

        past_ts = _ts(-3600)  # 1 hour ago
        cutoff = time.time() - 60  # 1 minute ago
        row = {"timestamp": past_ts}
        assert _row_is_before_cutoff(row, cutoff) is True

    def test_row_after_cutoff_returns_false(self) -> None:
        import time

        recent_ts = _ts(-10)  # 10 seconds ago
        cutoff = time.time() - 3600  # 1 hour ago
        row = {"timestamp": recent_ts}
        assert _row_is_before_cutoff(row, cutoff) is False

    def test_missing_timestamp_returns_none(self) -> None:
        import time

        assert _row_is_before_cutoff({}, time.time()) is None


class TestUpdateLearningSignals:
    def test_failure_root_cause_diagnosis_inconclusive(self) -> None:
        signals = _make_signals()
        _update_learning_signals(
            {"root_cause": "diagnosis.inconclusive"}, signals, from_failures=True
        )
        assert signals["diagnosis_inconclusive"] == 1
        assert signals["observed_events"] == 1

    def test_failure_root_cause_evidence_insufficient(self) -> None:
        signals = _make_signals()
        _update_learning_signals(
            {"root_cause": "evidence.insufficient"}, signals, from_failures=True
        )
        assert signals["evidence_insufficient"] == 1

    def test_failure_root_cause_scope_violation(self) -> None:
        signals = _make_signals()
        _update_learning_signals(
            {"root_cause": "scope.violation"}, signals, from_failures=True
        )
        assert signals["scope_violation"] == 1

    def test_compliance_fail_status(self) -> None:
        signals = _make_signals()
        _update_learning_signals({"status": "fail"}, signals, from_failures=False)
        assert signals["drift_recent_failures"] == 1
        assert signals["observed_events"] == 1

    def test_compliance_warn_status(self) -> None:
        signals = _make_signals()
        _update_learning_signals({"status": "warn"}, signals, from_failures=False)
        assert signals["drift_recent_failures"] == 1

    def test_compliance_ok_status_no_failure(self) -> None:
        signals = _make_signals()
        _update_learning_signals({"status": "ok"}, signals, from_failures=False)
        assert signals["drift_recent_failures"] == 0
        assert signals["observed_events"] == 1


class TestProcessTailRow:
    def test_returns_false_for_empty(self) -> None:
        import time

        signals = _make_signals()
        result = _process_tail_row(b"", signals, time.time(), from_failures=False)
        assert result is False

    def test_returns_true_for_row_before_cutoff(self) -> None:
        import time

        signals = _make_signals()
        row = {"timestamp": _ts(-7200), "status": "fail"}  # 2 hours ago
        raw = json.dumps(row).encode()
        cutoff = time.time() - 3600  # 1 hour ago
        result = _process_tail_row(raw, signals, cutoff, from_failures=False)
        assert result is True
        assert signals["drift_recent_failures"] == 0  # not counted (before cutoff)

    def test_accumulates_signals_for_recent_row(self) -> None:
        import time

        signals = _make_signals()
        row = {"timestamp": _ts(-10), "status": "fail"}  # 10 seconds ago
        raw = json.dumps(row).encode()
        cutoff = time.time() - 3600  # 1 hour ago
        _process_tail_row(raw, signals, cutoff, from_failures=False)
        assert signals["drift_recent_failures"] == 1


class TestCountSignalsFromTail:
    def test_skips_nonexistent_file(self, tmp_path: Path) -> None:
        signals = _make_signals()
        import time

        count_signals_from_tail(
            tmp_path / "nonexistent.jsonl", signals, time.time(), from_failures=False
        )
        assert signals["observed_events"] == 0

    def test_reads_recent_failures(self, tmp_path: Path) -> None:
        import time

        log = tmp_path / "test.jsonl"
        rows = [
            {"timestamp": _ts(-60), "status": "fail"},
            {"timestamp": _ts(-120), "status": "fail"},
        ]
        log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        signals = _make_signals()
        cutoff = time.time() - 3600
        count_signals_from_tail(log, signals, cutoff, from_failures=False)
        assert signals["drift_recent_failures"] == 2
        assert signals["observed_events"] == 2

    def test_ignores_rows_before_cutoff(self, tmp_path: Path) -> None:
        import time

        log = tmp_path / "test.jsonl"
        rows = [
            {"timestamp": _ts(-7200 * 24), "status": "fail"},  # very old
            {"timestamp": _ts(-60), "status": "fail"},  # recent
        ]
        log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        signals = _make_signals()
        cutoff = time.time() - 3600
        count_signals_from_tail(log, signals, cutoff, from_failures=False)
        assert signals["drift_recent_failures"] == 1


class TestCollectLearningSignals:
    def test_returns_zero_signals_for_empty_workspace(self, tmp_path: Path) -> None:
        signals = collect_learning_signals(tmp_path)
        assert signals["observed_events"] == 0
        assert signals["drift_recent_failures"] == 0
        assert signals["window_days"] == 7

    def test_collects_from_failure_ledger(self, tmp_path: Path) -> None:
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        ledger = runtime_dir / "failure-ledger.jsonl"
        ledger.write_text(
            json.dumps({"timestamp": _ts(-60), "root_cause": "diagnosis.inconclusive"})
            + "\n",
            encoding="utf-8",
        )
        signals = collect_learning_signals(tmp_path)
        assert signals["diagnosis_inconclusive"] == 1

    def test_collects_from_compliance_events(self, tmp_path: Path) -> None:
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        events = runtime_dir / "compliance-events.jsonl"
        events.write_text(
            json.dumps({"timestamp": _ts(-60), "status": "fail"}) + "\n",
            encoding="utf-8",
        )
        signals = collect_learning_signals(tmp_path)
        assert signals["drift_recent_failures"] == 1

    def test_custom_window_days(self, tmp_path: Path) -> None:
        signals = collect_learning_signals(tmp_path, window_days=30)
        assert signals["window_days"] == 30


class TestFilterSignals:
    def test_empty_query_returns_all(self) -> None:
        signals = _make_signals()
        signals["drift_recent_failures"] = 3
        result = filter_signals(signals, "")
        assert result == signals

    def test_nonempty_query_returns_all(self) -> None:
        signals = _make_signals()
        signals["drift_recent_failures"] = 1
        result = filter_signals(signals, "some query")
        assert result == signals
