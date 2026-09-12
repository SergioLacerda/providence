"""Unit tests for providence_cli.services.audit_runner analytics and summary."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_cli.services.audit_runner import (
    _compute_base_summary,
    _default_events_path,
    _window_classification,
    _window_confidence,
    _window_correlation,
    build_audit_summary_data,
)


class TestWindowConfidence:
    def test_returns_high_when_both_thresholds_met(self) -> None:
        assert _window_confidence(0.8, 0.9) == "HIGH"

    def test_returns_medium_when_one_threshold_met(self) -> None:
        assert _window_confidence(0.8, 0.5) == "MEDIUM"
        assert _window_confidence(0.5, 0.9) == "MEDIUM"

    def test_returns_low_when_neither_threshold_met(self) -> None:
        assert _window_confidence(0.3, 0.5) == "LOW"


class TestWindowClassification:
    def test_inconclusive_when_no_asks(self) -> None:
        cls, _ = _window_classification(
            asks_count=0,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=None,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"

    def test_inconclusive_when_no_quality_signals(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=False,
            quality_delta=None,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"

    def test_inconclusive_when_low_token_coverage(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.5,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"

    def test_inconclusive_when_low_drift_coverage(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=0.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.5,
        )
        assert cls == "INCONCLUSIVO"

    def test_enriquecimento_positivo(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=10.0,
            drift_delta=1.0,
            ratio_delta=0.0,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "ENRIQUECIMENTO_POSITIVO"

    def test_economia_saudavel(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=-1.0,
            drift_delta=1.0,
            ratio_delta=-0.5,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "ECONOMIA_SAUDAVEL"

    def test_economia_falsa(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=-10.0,
            drift_delta=5.0,
            ratio_delta=-0.5,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "ECONOMIA_FALSA"

    def test_inflacao_improdutiva(self) -> None:
        cls, _ = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=1.0,
            ratio_delta=0.5,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INFLACAO_IMPRODUTIVA"

    def test_returns_inconclusive_when_no_delta_pattern(self) -> None:
        cls, msg = _window_classification(
            asks_count=5,
            prev_asks_count=5,
            quality_signal_available=True,
            quality_delta=1.0,
            drift_delta=0.5,
            ratio_delta=0.05,
            token_coverage=0.8,
            prev_token_coverage=0.8,
            drift_classified_coverage=0.9,
        )
        assert cls == "INCONCLUSIVO"
        assert "No significant delta" in msg


class TestComputeBaseSummaryUnclassified:
    def test_counts_unclassified_drifts(self) -> None:
        events = [
            {
                "event": "runtime.drift.detected",
                "command": "runtime status",
                "start_ts": "2026-05-20T10:00:00Z",
                "artifact_fingerprint": "fp-1",
                "details": {},
            }
        ]
        result = _compute_base_summary(events, top=10)
        assert result["unclassified_drifts"] == 1


def _mixed_token_events(base_ts: str = "2026-05-20T10:00:00Z") -> list[dict]:
    """One tokenized ask invocation, one tokenless invocation, plus phase and
    non-LLM events that never carry tokens."""
    return [
        {
            "event": "governance.ask",
            "command": "ask",
            "start_ts": base_ts,
            "tokens_input": 100,
            "tokens_output": 50,
            "details": {},
        },
        {
            "event": "governance.ask",
            "command": "ask",
            "start_ts": base_ts,
            "tokens_input": None,
            "tokens_output": None,
            "details": {},
        },
        {
            "event": "governance.ask.phase",
            "command": "ask",
            "start_ts": base_ts,
            "tokens_input": None,
            "tokens_output": None,
            "details": {"phase_id": "intake"},
        },
        {
            "event": "governance.ask.phase",
            "command": "ask",
            "start_ts": base_ts,
            "tokens_input": None,
            "tokens_output": None,
            "details": {"phase_id": "routing"},
        },
        {
            "event": "governance.compile.complete",
            "command": "governance compile",
            "start_ts": base_ts,
            "tokens_input": None,
            "tokens_output": None,
            "details": {},
        },
    ]


class TestComputeBaseSummaryTokenScope:
    def test_token_metrics_scoped_to_ask_invocations(self) -> None:
        result = _compute_base_summary(_mixed_token_events(), top=10)
        assert result["ask_invocations"] == 2
        assert result["with_tokens"] == 1
        assert result["missing_tokens"] == 1
        assert result["non_token_events"] == 3
        assert result["total_in"] == 100
        assert result["total_out"] == 50


class TestWindowCorrelationTokenCoverage:
    def test_coverage_ignores_phase_and_non_llm_events(self) -> None:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = _window_correlation(_mixed_token_events(ts), days=7, now_utc=now)
        # 4 ask events in the window (2 invocations + 2 phase sub-events), but
        # coverage counts only the parent invocations: 1 tokenized of 2  0.5.
        assert result["ask_events"] == 4
        assert result["tokens"]["coverage"] == 0.5
        assert result["tokens"]["input"] == 100
        assert result["tokens"]["output"] == 50


def _drifted_ask_invocation_with_phases(
    base_ts: str, phase_count: int = 6
) -> list[dict]:
    """One drifted governance.ask invocation plus N phase sub-events that
    inherit drift_detected from their parent (real production shape)."""
    events = [
        {
            "event": "governance.ask",
            "command": "ask",
            "start_ts": base_ts,
            "details": {"drift_detected": True, "drift_type": "fingerprint_drift"},
        }
    ]
    for _ in range(phase_count):
        events.append(
            {
                "event": "governance.ask.phase",
                "command": "ask",
                "start_ts": base_ts,
                "details": {"drift_detected": True, "drift_type": "fingerprint_drift"},
            }
        )
    return events


class TestComputeBaseSummaryDriftScope:
    """OS-4: governance.ask.phase sub-events must not inflate the drift count."""

    def test_excludes_phase_events_from_drift_numerator(self) -> None:
        events = _drifted_ask_invocation_with_phases(
            "2026-05-20T10:00:00Z", phase_count=6
        )
        result = _compute_base_summary(events, top=10)

        assert len(result["drifts"]) == 1
        assert result["ask_events"] == 7

    def test_non_ask_drift_events_still_counted(self) -> None:
        events = [
            {
                "event": "runtime.drift.detected",
                "command": "governance compile",
                "start_ts": "2026-05-20T10:00:00Z",
                "details": {"drift_detected": True, "drift_type": "fingerprint_drift"},
            }
        ]
        result = _compute_base_summary(events, top=10)

        assert len(result["drifts"]) == 1
        assert result["ask_events"] == 0


class TestWindowCorrelationDriftScope:
    """OS-4: the windowed drift_rate_pct numerator excludes phase sub-events;
    the denominator (ask_events) keeps counting them."""

    def test_excludes_phase_events_from_drift_rate_numerator(self) -> None:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        events = _drifted_ask_invocation_with_phases(ts, phase_count=6)

        result = _window_correlation(events, days=7, now_utc=now)

        assert result["ask_events"] == 7
        assert result["drift_events"] == 1
        assert result["drift_rate_pct"] == round(1 * 100.0 / 7, 2)


class TestBuildAuditSummaryDriftRateDenominator:
    """OS-4: the headline drift_rate_pct denominator is ask-events-only, not
    the entire raw event stream (which would dilute with non-ask events on
    top of the phase-fan-out inflation)."""

    def test_headline_drift_rate_uses_ask_events_denominator(self) -> None:
        from datetime import datetime, timezone

        events = _drifted_ask_invocation_with_phases(
            "2026-05-20T10:00:00Z", phase_count=6
        )
        events.append(
            {
                "event": "governance.compile.complete",
                "command": "governance compile",
                "start_ts": "2026-05-20T10:00:00Z",
                "details": {},
            }
        )

        data = build_audit_summary_data(
            events,
            top=10,
            now_utc=datetime.now(timezone.utc),
            include_non_drift=False,
        )

        assert data["total_events"] == 8
        assert data["total_drifts"] == 1
        assert data["drift_rate_pct"] == round(1 * 100.0 / 7, 2)

    def test_zero_ask_events_yields_zero_drift_rate(self) -> None:
        from datetime import datetime, timezone

        events = [
            {
                "event": "governance.compile.complete",
                "command": "governance compile",
                "start_ts": "2026-05-20T10:00:00Z",
                "details": {},
            }
        ]

        data = build_audit_summary_data(
            events,
            top=10,
            now_utc=datetime.now(timezone.utc),
            include_non_drift=False,
        )

        assert data["drift_rate_pct"] == 0.0


class TestDefaultEventsPath:
    def test_falls_back_to_cwd_on_exception(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.services.audit_runner.resolve_workspace_root",
                side_effect=Exception("no workspace"),
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            result = _default_events_path()

        assert (
            result == tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        )
