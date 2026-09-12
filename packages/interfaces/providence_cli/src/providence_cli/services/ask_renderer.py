"""ask_renderer  output formatting for providence ask.

All public functions return strings or dicts. No stdout/stderr writes.
The caller (ask_dispatcher) is responsible for I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from providence_cli.services.ask_hash import _hash_query


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def render_context_header(
    fingerprint: str,
    mandates_count: int,
    *,
    degraded: bool,
    degrade_reason: str,
) -> str:
    """Return compact governance context for LLM input (no I/O). M020 compliant."""
    from providence_core.output.canonical_event import CanonicalGovernanceInput

    gov = CanonicalGovernanceInput(
        governance_state="degraded" if degraded else "active",
        fingerprint=fingerprint or "n/a",
        mandates_count=mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )
    return gov.simple_input()


def render_governance_activation_header(
    *,
    source: str,
    fingerprint: str = "",
    execution_gate: str = "allowed",
    governance_mode: str = "hard",
) -> str:
    """Return the compact SDD-active header for prompt hook context."""
    fp = (fingerprint or "unknown")[:8]
    return "\n".join(
        [
            "PROVIDENCE GOVERNANCE ACTIVE | "
            f"source={source or 'unknown'} | "
            f"governance_mode={governance_mode or 'hard'} | "
            f"execution_gate={execution_gate or 'unknown'} | "
            f"fingerprint={fp}",
            "Instruction: start your response with one short SDD governance "
            "status line when this context is present.",
        ]
    )


def render_governance_footer(
    *,
    state: str,
    profile: str,
    drift_detected: bool,
    root_seed_drift_detected: bool | None = None,
) -> str:
    """Return the governance footer line (no I/O).

    `root_seed_drift_detected` is reported as a separate field from
    `drift_detected`  the two are structurally different checks (in-session
    cached state vs. installed root files against source metadata) and must
    not be merged into one shared boolean.
    """
    from providence_runtime import format_governance_footer

    governance = "ok" if state in {"HEALTHY", "PARTIAL"} else "warn"
    drift = "detected" if drift_detected else "none"
    root_seed_drift = (
        None
        if root_seed_drift_detected is None
        else ("detected" if root_seed_drift_detected else "none")
    )
    return format_governance_footer(
        drift=drift,
        governance=governance,
        profile=profile or "default",
        root_seed_drift=root_seed_drift,
    )


def render_ask_text_output(
    *,
    output_text: str,
    organize_used: bool,
    organize_chunks: int,
    organize_artifact_path: str,
    organize_reason: str = "light_input",
    query_len: int,
    governance_footer: str,
) -> str:
    """Return the full plain-text ask response as a single string (no I/O)."""
    artifact = organize_artifact_path or "n/a"
    gate_blocked = not organize_used and organize_reason != "light_input"
    if organize_used:
        intake_block = (
            f"intake_mode=multi execution_gate=allowed chunks={organize_chunks}\n"
            f"artifact={artifact}"
        )
    elif gate_blocked:
        intake_block = (
            f"intake_mode=none governance_mode=hard execution_gate=blocked\n"
            f"gate_reason=query {query_len} chars < 6000"
            f" (use: sdd-organize --input-file <path> <query>)"
        )
    else:
        intake_block = "intake_mode=none governance_mode=hard execution_gate=allowed"
    return "\n".join(filter(None, [output_text, intake_block, governance_footer]))


def build_ask_json_payload(
    *,
    profile: str,
    query: str,
    context_source: str,
    fingerprint: str,
    mandates_count: int,
    trust_source: str,
    degraded: bool,
    degrade_reason: str,
    drift_detected: bool,
    governance_footer: str,
    root_seed_drift_detected: bool | None = None,
    organize_used: bool,
    organize_reason: str = "light_input",
    organize_chunks: int,
    organize_retrieval: str,
    organize_artifact_path: str,
    ahp_state: str,
    learning_signals: dict[str, int],
    full: bool,
    start_ts: str,
    dossier_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Build the complete JSON response dict for providence ask (no I/O)."""
    from providence_cli.services.ask_payload import build_ask_json_data

    gate_blocked = not organize_used and organize_reason != "light_input"
    execution_gate = "blocked" if gate_blocked else "allowed"
    gate_reason = (
        None
        if execution_gate == "allowed"
        else "intake_index_mode=none: governance context not indexed; agent must not proceed"
    )
    data = build_ask_json_data(
        profile=profile,
        query_hash=_hash_query(query),
        context_source=context_source,
        fingerprint=fingerprint,
        mandates_loaded=mandates_count,
        trust_source=trust_source,
        degraded=degraded,
        degraded_reason=degrade_reason,
        drift_detected=drift_detected,
        root_seed_drift_detected=root_seed_drift_detected,
        governance_footer=governance_footer,
        intake_index_mode="multi" if organize_used else "none",
        intake_chunks=organize_chunks,
        intake_retrieval=organize_retrieval,
        intake_artifact=organize_artifact_path or "n/a",
        governance_mode="hard",
        execution_gate=execution_gate,
        gate_reason=gate_reason,
        ahp_state=ahp_state,
        learning_signals=learning_signals,
        full=full,
        steps=[
            {"step_id": "PARSE", "ok": True, "ts_start": start_ts, "ts_end": _now()},
            {
                "step_id": "CONTEXT_LOAD",
                "ok": True,
                "context_source": context_source,
                "fingerprint": fingerprint,
            },
        ]
        if full
        else None,
        extra={"log_format": "jsonl"} if full else None,
    )
    if dossier_lines:
        data["dossier"] = {"lines": dossier_lines}
    return {"status": "ok", "command": "ask", "ok": True, "error": None, "data": data}
