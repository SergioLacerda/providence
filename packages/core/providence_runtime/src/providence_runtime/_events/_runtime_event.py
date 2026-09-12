"""RuntimeEvent — the governance-aware runtime event envelope."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---- Schema version ---------------------------------------------------------
EVENT_SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _generate_span_id() -> str:
    """Generate a unique span ID (UUID hex, truncated to 16 chars for OTLP compat)."""
    return uuid.uuid4().hex[:16]


@dataclass
class RuntimeEvent:
    """A single governance-aware runtime event.

    Mandatory fields per §13.3 envelope:
      event, command, status, trace_id, service, workspace_id, agent_id,
      artifact_fingerprint, schema_version, ts, event_schema_version.

    Operation-timing fields per §15.1 passive-mode minimum:
      start_ts, end_ts, iterations_count.
    """

    # Core identity
    event: str
    command: str
    status: str  # ok | warn | fail
    trace_id: str

    # Observability envelope
    level: str = "INFO"  # DEBUG | INFO | WARN | ERROR
    service: str = "providence-runtime"
    workspace_id: str = ""
    agent_id: str = ""

    # Governance traceability
    artifact_fingerprint: str = ""
    schema_version: str = ""
    decision_source_refs: list[str] = field(default_factory=list)

    # Performance
    duration_ms: int | None = None

    # OTEL span context (§13 Phase C — span_id mandatory once OTEL enabled)
    # Phase 1: Auto-populate with UUID if not explicitly set
    span_id: str = field(default_factory=_generate_span_id)

    # Phase 1: Parent event ID for causality tracking across distributed operations
    parent_event_id: str = ""

    # LLM call tracking (§15.1 passive mode minimum)
    start_ts: str = ""
    end_ts: str = ""
    iterations_count: int | None = None

    # Token Economy fields (§economy/metrics.md)
    tokens_input: int | None = None
    tokens_output: int | None = None
    tokens_total: int | None = None
    context_bytes_loaded: int | None = None
    context_budget_bytes: int | None = None
    budget_utilization_pct: float | None = None
    compression_ratio: float | None = None
    retry_count: int | None = None
    reflection_count: int | None = None
    path_id: str = ""

    # Adapter/provider-facing timing (§ trace_time.txt review, mission
    # 20260730-sdd-ask-telemetry-critique). All three are populated only by
    # an external adapter/IDE report (e.g. `ask.external.llm_exchange`) —
    # providence_cli commands do not call an LLM in-process, so these stay None
    # unless an adapter explicitly reports them.
    time_to_first_token_ms: int | None = None
    provider_wait_ms: int | None = None
    llm_call_count: int | None = None

    # In-process tool/subprocess timing, summed from phases tagged with a
    # "tool" latency_domain. None when a command has no such phases.
    tool_execution_ms: int | None = None

    # Soft-watchdog marker: True when this phase's duration exceeded its
    # configured threshold. See `_ask_backend._phase_timer.PhaseTimer`.
    phase_slow: bool = False

    # Payload
    details: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    ts: str = field(default_factory=_utc_now)
    event_schema_version: str = EVENT_SCHEMA_VERSION  # §15.3 — mandatory in every event

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
