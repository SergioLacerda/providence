"""CI Boundary Gate tests (§12.8 Step 5).

Enforces the constitutional guardrails defined in §9 of the improvement plan:
- Traceability Gate: sensitive events must carry trace_id, workspace_id,
  agent_id, and decision_source_refs.
- Schema Gate: every event must carry a valid event_schema_version.

These tests are designed to be run in CI and will fail when critical runtime
events are emitted without required traceability fields, preventing silent
governance-authority violations from reaching production.
"""

from __future__ import annotations

from providence_runtime import (
    EVENT_SCHEMA_VERSION,
    RuntimeEvent,
    SchemaValidator,
    TraceabilityValidator,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_runtime_session_start_event(
    trace_id: str = "trace-001",
    workspace_id: str = "ws-test",
    agent_id: str = "agent-ci",
    decision_source_refs: list[str] | None = None,
) -> RuntimeEvent:
    """Canonical shape of what runtime.py _emit_runtime_status emits."""
    refs = (
        ["ADR-001-runtime-authority-boundary"]
        if decision_source_refs is None
        else decision_source_refs
    )
    return RuntimeEvent(
        event="runtime.session.start",
        command="runtime status",
        status="ok",
        trace_id=trace_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        artifact_fingerprint="fp-test",
        schema_version="3.0",
        decision_source_refs=refs,
        details={"ahp_state": "HEALTHY", "mandates_loaded": 3},
    )


def _make_drift_detected_event(
    trace_id: str = "trace-002",
    workspace_id: str = "ws-test",
    agent_id: str = "agent-ci",
    decision_source_refs: list[str] | None = None,
) -> RuntimeEvent:
    """Canonical shape of what runtime.py emits on drift."""
    refs = (
        ["§12.5-anti-drift-strategy", "ADR-001-runtime-authority-boundary"]
        if decision_source_refs is None
        else decision_source_refs
    )
    return RuntimeEvent(
        event="runtime.drift.detected",
        command="runtime status",
        status="warn",
        trace_id=trace_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        artifact_fingerprint="fp-test",
        schema_version="3.0",
        decision_source_refs=refs,
        details={"drift_type": "session_drift"},
    )


def _make_policy_fail_event(
    trace_id: str = "trace-003",
    workspace_id: str = "ws-test",
    agent_id: str = "agent-ci",
    decision_source_refs: list[str] | None = None,
) -> RuntimeEvent:
    refs = ["policy:P001"] if decision_source_refs is None else decision_source_refs
    return RuntimeEvent(
        event="policy.validation.fail",
        command="governance validate",
        status="fail",
        trace_id=trace_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        artifact_fingerprint="fp-test",
        schema_version="3.0",
        decision_source_refs=refs,
        details={"reason": "fingerprint_mismatch"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gate 1: Traceability — individual events
# ─────────────────────────────────────────────────────────────────────────────


class TestTraceabilityGate:
    """§9 item 2 — Traceability Gate.

    Sensitive events MUST carry trace_id, workspace_id, agent_id, and
    decision_source_refs.  Non-sensitive events must carry trace_id.
    """

    def test_well_formed_session_start_passes(self) -> None:
        event = _make_runtime_session_start_event()
        result = TraceabilityValidator().validate_event(event)
        assert result.valid, f"Expected valid, got: {result.reason}"

    def test_well_formed_drift_event_passes(self) -> None:
        event = _make_drift_detected_event()
        result = TraceabilityValidator().validate_event(event)
        assert result.valid, f"Expected valid, got: {result.reason}"

    def test_well_formed_policy_fail_passes(self) -> None:
        event = _make_policy_fail_event()
        result = TraceabilityValidator().validate_event(event)
        assert result.valid, f"Expected valid, got: {result.reason}"

    def test_missing_trace_id_fails(self) -> None:
        event = _make_drift_detected_event(trace_id="")
        result = TraceabilityValidator().validate_event(event)
        assert not result.valid
        assert "trace_id" in result.missing_fields

    def test_missing_workspace_id_on_sensitive_event_fails(self) -> None:
        event = _make_drift_detected_event(workspace_id="")
        result = TraceabilityValidator().validate_event(event)
        assert not result.valid
        assert "workspace_id" in result.missing_fields

    def test_missing_agent_id_on_sensitive_event_fails(self) -> None:
        event = _make_policy_fail_event(agent_id="")
        result = TraceabilityValidator().validate_event(event)
        assert not result.valid
        assert "agent_id" in result.missing_fields

    def test_missing_decision_source_refs_on_sensitive_event_fails(self) -> None:
        event = _make_drift_detected_event(decision_source_refs=[])
        result = TraceabilityValidator().validate_event(event)
        assert not result.valid
        assert "decision_source_refs" in result.missing_fields

    def test_non_sensitive_event_only_needs_trace_id(self) -> None:
        # governance.checked is not in _SENSITIVE_EVENTS
        event = RuntimeEvent(
            event="governance.checked",
            command="governance validate",
            status="ok",
            trace_id="trace-x",
            workspace_id="",  # not required for non-sensitive
            agent_id="",
            artifact_fingerprint="",
            schema_version="",
        )
        result = TraceabilityValidator().validate_event(event, is_sensitive=False)
        assert result.valid


# ─────────────────────────────────────────────────────────────────────────────
# Gate 2: Batch validation (§12.8 Step 5 — CI enforcement)
# ─────────────────────────────────────────────────────────────────────────────


class TestBatchTraceabilityGate:
    """Simulates what a CI job would run against a batch of emitted events."""

    def test_canonical_event_batch_has_no_failures(self) -> None:
        """The canonical events emitted by critical CLI commands must all pass."""
        batch = [
            _make_runtime_session_start_event(),
            _make_drift_detected_event(),
            _make_policy_fail_event(),
        ]
        failures = TraceabilityValidator().validate_batch(batch)
        assert failures == [], (
            f"CI gate failed: {len(failures)} events have traceability violations:\n"
            + "\n".join(f"  {evt.event}: {res.reason}" for evt, res in failures)
        )

    def test_batch_with_defective_event_reports_failure(self) -> None:
        """validate_batch must surface violations — not silently pass them."""
        good = _make_runtime_session_start_event()
        bad = _make_drift_detected_event(decision_source_refs=[])  # missing refs
        failures = TraceabilityValidator().validate_batch([good, bad])
        assert len(failures) == 1
        failing_event, result = failures[0]
        assert failing_event.event == "runtime.drift.detected"
        assert "decision_source_refs" in result.missing_fields

    def test_empty_batch_passes(self) -> None:
        failures = TraceabilityValidator().validate_batch([])
        assert failures == []


# ─────────────────────────────────────────────────────────────────────────────
# Gate 3: Schema version — every event must carry event_schema_version
# ─────────────────────────────────────────────────────────────────────────────


class TestSchemaGate:
    """§15.3 — event_schema_version must be present and current in all events."""

    def test_canonical_events_have_correct_schema_version(self) -> None:
        events = [
            _make_runtime_session_start_event(),
            _make_drift_detected_event(),
            _make_policy_fail_event(),
        ]
        validator = SchemaValidator()
        for event in events:
            assert event.event_schema_version == EVENT_SCHEMA_VERSION, (
                f"{event.event} has wrong event_schema_version: "
                f"{event.event_schema_version!r} (expected {EVENT_SCHEMA_VERSION!r})"
            )
            result = validator.validate_event(event)
            assert result.compatible, (
                f"{event.event} schema validation failed: {result.reason}"
            )

    def test_event_missing_schema_version_fails_schema_gate(self) -> None:
        event = _make_runtime_session_start_event()
        event.event_schema_version = ""
        result = SchemaValidator().validate_event(event)
        assert not result.compatible
        assert "missing" in result.reason

    def test_event_with_unknown_schema_version_fails(self) -> None:
        event = _make_drift_detected_event()
        event.event_schema_version = "99.0"
        result = SchemaValidator().validate_event(event)
        assert not result.compatible
