"""Window-based analytics helpers for audit correlation and classification."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from providence_cli.services.audit_event_parser import (
    _is_ask_event,
    _is_ask_invocation,
    _is_ask_phase_event,
    _is_drift_event,
    _token_totals,
    _window_events,
)
from providence_cli.services.audit_quality_score import _quality_score


def window_confidence(token_coverage: float, drift_classified_coverage: float) -> str:
    if token_coverage >= 0.7 and drift_classified_coverage >= 0.8:
        return "HIGH"
    if token_coverage >= 0.7 or drift_classified_coverage >= 0.8:
        return "MEDIUM"
    return "LOW"


def window_classification(
    *,
    asks_count: int,
    prev_asks_count: int,
    quality_signal_available: bool,
    quality_delta: float | None,
    drift_delta: float,
    ratio_delta: float,
    token_coverage: float,
    prev_token_coverage: float,
    drift_classified_coverage: float,
) -> tuple[str, str]:
    classification = "INCONCLUSIVO"
    if asks_count == 0 or prev_asks_count == 0:
        return classification, "Insufficient ask events in current/previous window."
    if not quality_signal_available:
        return classification, "No quality signals (tests_passed/human_accepted)."
    if token_coverage < 0.7 or prev_token_coverage < 0.7:
        return classification, "Token coverage below threshold in one window."
    if drift_classified_coverage < 0.8:
        return classification, "Drift classification coverage below threshold."
    assert quality_delta is not None
    q_sig = 5.0
    d_sig = 2.0
    t_sig = 0.20
    if quality_delta >= q_sig and drift_delta <= d_sig:
        return "ENRIQUECIMENTO_POSITIVO", "Scale current strategy with monitoring."
    if ratio_delta <= -t_sig and quality_delta >= -2.0 and drift_delta <= d_sig:
        return "ECONOMIA_SAUDAVEL", "Preserve optimization and monitor drift."
    if ratio_delta <= -t_sig and quality_delta <= -q_sig and drift_delta >= d_sig:
        return "ECONOMIA_FALSA", "Restore context depth and review prompt strategy."
    if ratio_delta >= t_sig and (quality_delta < q_sig or drift_delta > d_sig):
        return "INFLACAO_IMPRODUTIVA", "Constrain output and tighten scope."
    return classification, "No significant delta pattern yet; continue collecting data."


def window_correlation(
    *,
    events: list[dict[str, Any]],
    days: int,
    now_utc: datetime,
    drift_type_fn: Any,
    window_confidence_fn: Any,
    window_classification_fn: Any,
) -> dict[str, Any]:
    window = _window_events(events, now_utc=now_utc, days=days)
    previous_window = _window_events(
        events, now_utc=now_utc - timedelta(days=days), days=days
    )
    asks = [event for event in window if _is_ask_event(event)]
    prev_asks = [event for event in previous_window if _is_ask_event(event)]
    # governance.ask.phase sub-events inherit drift_detected from their parent
    # invocation; excluded from the drift-rate numerator to avoid ~7x inflation
    # (one parent + ~6 phase events per drifted invocation). The denominator
    # (asks/prev_asks) intentionally keeps counting phase events.
    drifts = [
        event
        for event in asks
        if _is_drift_event(event) and not _is_ask_phase_event(event)
    ]
    prev_drifts = [
        event
        for event in prev_asks
        if _is_drift_event(event) and not _is_ask_phase_event(event)
    ]
    # Token coverage is measured over parent governance.ask invocations only;
    # phase sub-events never carry tokens and would pin coverage below the
    # confidence gate no matter how healthy the telemetry is.
    invocations = [event for event in asks if _is_ask_invocation(event)]
    prev_invocations = [event for event in prev_asks if _is_ask_invocation(event)]
    total_in, total_out, with_tokens = _token_totals(invocations)
    prev_in, prev_out, prev_with_tokens = _token_totals(prev_invocations)
    token_coverage = (with_tokens / len(invocations)) if invocations else 0.0
    prev_token_coverage = (
        (prev_with_tokens / len(prev_invocations)) if prev_invocations else 0.0
    )
    ratio = (total_out / total_in) if total_in > 0 else 0.0
    prev_ratio = (prev_out / prev_in) if prev_in > 0 else 0.0
    classified = sum(
        1 for event in drifts if drift_type_fn(event) != "missing_drift_type"
    )
    drift_classified_coverage = (classified / len(drifts)) if drifts else 1.0
    current_drift_rate = (len(drifts) * 100.0 / len(asks)) if asks else 0.0
    prev_drift_rate = (len(prev_drifts) * 100.0 / len(prev_asks)) if prev_asks else 0.0
    quality_score = _quality_score(asks)
    prev_quality_score = _quality_score(prev_asks)
    quality_signal_available = (
        quality_score is not None and prev_quality_score is not None
    )
    quality_delta = (
        quality_score - prev_quality_score
        if quality_score is not None and prev_quality_score is not None
        else None
    )
    classification, recommended_action = window_classification_fn(
        asks_count=len(asks),
        prev_asks_count=len(prev_asks),
        quality_signal_available=quality_signal_available,
        quality_delta=quality_delta,
        drift_delta=(current_drift_rate - prev_drift_rate),
        ratio_delta=(ratio - prev_ratio),
        token_coverage=token_coverage,
        prev_token_coverage=prev_token_coverage,
        drift_classified_coverage=drift_classified_coverage,
    )
    return {
        "window_days": days,
        "window_start": (now_utc - timedelta(days=days)).isoformat(),
        "window_end": now_utc.isoformat(),
        "ask_events": len(asks),
        "drift_events": len(drifts),
        "drift_rate_pct": round(current_drift_rate, 2),
        "tokens": {
            "input": total_in,
            "output": total_out,
            "output_input_ratio": round(ratio, 4),
            "coverage": round(token_coverage, 4),
        },
        "previous_window": {
            "ask_events": len(prev_asks),
            "drift_rate_pct": round(prev_drift_rate, 2),
            "tokens": {
                "input": prev_in,
                "output": prev_out,
                "output_input_ratio": round(prev_ratio, 4),
                "coverage": round(prev_token_coverage, 4),
            },
            "quality_score": prev_quality_score,
        },
        "quality_score": quality_score,
        "drift_classified_coverage": round(drift_classified_coverage, 4),
        "quality_signal_available": quality_signal_available,
        "classification": classification,
        "confidence": window_confidence_fn(token_coverage, drift_classified_coverage),
        "recommended_action": recommended_action,
    }
