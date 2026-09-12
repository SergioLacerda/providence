"""Audit analytics: window classification, correlation, summary aggregation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from providence_cli.services._audit_runner_support import (
    compute_base_summary,
    default_events_path,
    window_classification,
    window_confidence,
    window_correlation,
)
from providence_cli.services.audit_event_parser import (
    DriftRow,  # noqa: F401  backward-compat re-export
    _drift_cause,  # noqa: F401  backward-compat re-export
    _drift_type,  # noqa: F401  backward-compat re-export
    _event_ts,  # noqa: F401  backward-compat re-export
    _load_events,  # noqa: F401  backward-compat re-export
    _parse_int,  # noqa: F401  backward-compat re-export
    _parse_ts,  # noqa: F401  backward-compat re-export
    _ts_sort_key,  # noqa: F401  backward-compat re-export
)
from providence_cli.services.audit_quality_score import (
    _as_score,  # noqa: F401  backward-compat re-export
    _has_quality_signals,  # noqa: F401  backward-compat re-export
)
from providence_cli.utils.providence_authority import resolve_workspace_root

__all__ = [
    "DriftRow",
    "_as_score",
    "_drift_type",
    "_has_quality_signals",
    "_drift_cause",
    "_event_ts",
    "_load_events",
    "_parse_int",
    "_parse_ts",
    "_ts_sort_key",
]


def _window_confidence(token_coverage: float, drift_classified_coverage: float) -> str:
    return window_confidence(token_coverage, drift_classified_coverage)


def _window_classification(
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
    return window_classification(
        asks_count=asks_count,
        prev_asks_count=prev_asks_count,
        quality_signal_available=quality_signal_available,
        quality_delta=quality_delta,
        drift_delta=drift_delta,
        ratio_delta=ratio_delta,
        token_coverage=token_coverage,
        prev_token_coverage=prev_token_coverage,
        drift_classified_coverage=drift_classified_coverage,
    )


def _window_correlation(
    events: list[dict[str, Any]], *, days: int, now_utc: datetime
) -> dict[str, Any]:
    from providence_cli.services.audit_event_parser import _drift_type as _dt

    return window_correlation(
        events=events,
        days=days,
        now_utc=now_utc,
        drift_type_fn=_dt,
        window_confidence_fn=_window_confidence,
        window_classification_fn=_window_classification,
    )


def _compute_base_summary(events: list[dict[str, Any]], top: int) -> dict[str, Any]:
    from providence_cli.services.audit_event_parser import _drift_cause as _dc
    from providence_cli.services.audit_event_parser import _drift_type as _dt
    from providence_cli.services.audit_event_parser import _event_ts as _ets
    from providence_cli.services.audit_event_parser import _ts_sort_key as _tsk

    return compute_base_summary(
        events=events,
        top=top,
        drift_cause_fn=_dc,
        drift_type_fn=_dt,
        event_ts_fn=_ets,
        ts_sort_key_fn=_tsk,
    )


def _default_events_path() -> Path:
    return default_events_path(resolve_workspace_root_fn=resolve_workspace_root)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def build_audit_summary_data(
    events: list[dict[str, Any]],
    top: int,
    now_utc: datetime,
    include_non_drift: bool,
) -> dict[str, Any]:
    """Build the full audit summary data dict for the main audit command."""
    computed = _compute_base_summary(events, top)
    drifts = computed["drifts"]
    ask_events_count = computed["ask_events"]
    rows: list[DriftRow] = computed["rows"]
    correlation_windows = [
        _window_correlation(events, days=days, now_utc=now_utc) for days in (7, 14, 30)
    ]
    data: dict[str, Any] = {
        "exit_code": 0,
        "total_events": len(events),
        "total_drifts": len(drifts),
        # Denominator is ask-events-only (matching window_correlation's shape
        # in _audit_window_support.py), not the entire raw event stream
        # non-ask events (compile, lifecycle) would otherwise dilute the rate.
        "drift_rate_pct": round((len(drifts) * 100.0 / ask_events_count), 2)
        if ask_events_count
        else 0.0,
        "events_by_command": computed["events_by_command"],
        "drift_by_type": computed["drift_by_type"],
        "drift_unclassified_total": computed["unclassified_drifts"],
        "token_comparison": {
            "total_input_tokens": computed["total_in"],
            "total_output_tokens": computed["total_out"],
            "output_input_ratio": round(computed["ratio"], 4),
            "ask_invocations": computed["ask_invocations"],
            "events_with_tokens": computed["with_tokens"],
            "events_missing_tokens": computed["missing_tokens"],
            "non_token_events": computed["non_token_events"],
        },
        "correlation_windows": correlation_windows,
        "top_drifts": [
            {
                "timestamp": row.ts,
                "drift_type": row.drift_type,
                "command": row.command,
                "status": row.status,
                "fingerprint_short": row.fingerprint_short,
                "cause": row.cause,
            }
            for row in rows
        ],
    }
    if include_non_drift:
        data["non_drift_events"] = len(events) - len(drifts)
    return data
