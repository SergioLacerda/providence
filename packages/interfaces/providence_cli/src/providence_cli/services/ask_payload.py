"""Shared payload builders for ask-derived JSON contracts."""

from __future__ import annotations

from typing import Any


def build_ask_json_data(
    *,
    profile: str,
    query_hash: str,
    context_source: str,
    fingerprint: str | None,
    mandates_loaded: int,
    trust_source: str,
    degraded: bool,
    degraded_reason: str,
    drift_detected: bool,
    governance_footer: str,
    root_seed_drift_detected: bool | None = None,
    intake_index_mode: str,
    intake_chunks: int,
    intake_retrieval: str,
    intake_artifact: str,
    governance_mode: str = "hard",
    execution_gate: str = "allowed",
    gate_reason: str | None = None,
    ahp_state: str = "UNKNOWN",
    learning_signals: dict[str, int] | None = None,
    full: bool = False,
    steps: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build base canonical `data` payload for `providence ask --json`."""
    payload: dict[str, Any] = {
        "profile": profile,
        "query_hash": query_hash,
        "context_source": context_source,
        "fingerprint": fingerprint or "n/a",
        "mandates_loaded": mandates_loaded,
        "trust_source": trust_source,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "drift_detected": drift_detected,
        "root_seed_drift_detected": root_seed_drift_detected,
        "governance_footer": governance_footer,
        "intake_index_mode": intake_index_mode,
        "intake_chunks": intake_chunks,
        "intake_retrieval": intake_retrieval,
        "intake_artifact": intake_artifact,
        "governance_mode": governance_mode,
        "execution_gate": execution_gate,
        "ahp_state": ahp_state,
        "learning_signals": learning_signals
        or {
            "diagnosis_inconclusive": 0,
            "evidence_insufficient": 0,
            "scope_violation": 0,
            "drift_recent_failures": 0,
            "observed_events": 0,
            "window_days": 7,
        },
    }
    if gate_reason is not None:
        payload["gate_reason"] = gate_reason
    if full and steps is not None:
        payload["steps"] = steps
    if extra:
        payload.update(extra)
    return payload
