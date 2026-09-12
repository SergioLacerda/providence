"""Comprehensive tests for providence_runtime.validator — schema and traceability validation.

Covers:
- SchemaValidator: artifact schema version validation, event schema version validation
- TraceabilityValidator: trace requirements, sensitive event detection, batch validation
- Edge cases: empty strings, missing attributes, custom supported versions
"""

from __future__ import annotations

from unittest.mock import MagicMock

from providence_runtime.artifacts import CompiledArtifact
from providence_runtime.telemetry import EVENT_SCHEMA_VERSION, RuntimeEvent
from providence_runtime.validator import (
    RUNTIME_SUPPORTED_SCHEMA_VERSIONS,
    SchemaCompatibilityResult,
    SchemaValidator,
    TraceabilityResult,
    TraceabilityValidator,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _artifact(schema_version: str = "3.0") -> CompiledArtifact:
    return CompiledArtifact(
        artifact_version="1.0",
        schema_version=schema_version,
        fingerprint="test-fp",
        generated_at="2026-05-12T00:00:00Z",
        profile="master",
        items=[],
    )


def _event(
    event: str = "governance.compile",
    trace_id: str = "trace-1",
    workspace_id: str = "ws-1",
    agent_id: str = "agent-1",
    decision_source_refs: list[str] | None = None,
    event_schema_version: str = EVENT_SCHEMA_VERSION,
) -> RuntimeEvent:
    return RuntimeEvent(
        event=event,
        command="compile",
        status="ok",
        trace_id=trace_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        artifact_fingerprint="fp",
        schema_version="3.0",
        decision_source_refs=decision_source_refs or [],
        event_schema_version=event_schema_version,
    )


# ---------------------------------------------------------------------------
# SchemaValidator — artifact validation
# ---------------------------------------------------------------------------


class TestSchemaValidatorArtifact:
    def test_supported_version_returns_compatible(self) -> None:
        validator = SchemaValidator()
        result = validator.validate_artifact(_artifact(schema_version="3.0"))
        assert result.compatible is True
        assert result.reason == "ok"
        assert result.artifact_version == "3.0"

    def test_any_supported_version_accepted(self) -> None:
        validator = SchemaValidator()
        for version in RUNTIME_SUPPORTED_SCHEMA_VERSIONS:
            result = validator.validate_artifact(_artifact(schema_version=version))
            assert result.compatible is True

    def test_unsupported_version_returns_incompatible(self) -> None:
        validator = SchemaValidator()
        result = validator.validate_artifact(_artifact(schema_version="9.9"))
        assert result.compatible is False
        assert "not in supported set" in result.reason
        assert result.artifact_version == "9.9"

    def test_empty_version_returns_incompatible(self) -> None:
        validator = SchemaValidator()
        result = validator.validate_artifact(_artifact(schema_version=""))
        assert result.compatible is False
        assert "missing" in result.reason.lower()
        assert result.remediation == "providence governance compile"

    def test_incompatible_version_suggests_force_compile(self) -> None:
        validator = SchemaValidator()
        result = validator.validate_artifact(_artifact(schema_version="99.0"))
        assert result.remediation == "providence governance compile --force"

    def test_custom_supported_versions(self) -> None:
        validator = SchemaValidator(supported_versions=("1.5", "2.0"))
        # Should support custom version
        result = validator.validate_artifact(_artifact(schema_version="1.5"))
        assert result.compatible is True
        # Should reject unsupported version
        result = validator.validate_artifact(_artifact(schema_version="3.0"))
        assert result.compatible is False

    def test_none_version_treated_as_missing(self) -> None:
        # Create artifact with None schema_version by directly constructing
        artifact = MagicMock()
        artifact.schema_version = None
        validator = SchemaValidator()
        result = validator.validate_artifact(artifact)
        assert result.compatible is False
        assert "missing" in result.reason.lower()


# ---------------------------------------------------------------------------
# SchemaValidator — event validation
# ---------------------------------------------------------------------------


class TestSchemaValidatorEvent:
    def test_event_matching_current_schema_is_valid(self) -> None:
        validator = SchemaValidator()
        event = _event(event_schema_version=EVENT_SCHEMA_VERSION)
        result = validator.validate_event(event)
        assert result.compatible is True
        assert result.reason == "ok"
        assert result.artifact_version == EVENT_SCHEMA_VERSION

    def test_event_with_mismatched_schema_is_invalid(self) -> None:
        validator = SchemaValidator()
        event = _event(event_schema_version="0.5")
        result = validator.validate_event(event)
        assert result.compatible is False
        assert "event schema_version" in result.reason

    def test_event_missing_event_schema_version_is_invalid(self) -> None:
        validator = SchemaValidator()
        event = _event()
        event.event_schema_version = ""
        result = validator.validate_event(event)
        assert result.compatible is False
        assert "missing" in result.reason.lower()

    def test_event_without_event_schema_version_attribute(self) -> None:
        validator = SchemaValidator()
        # Create event without the attribute
        event = MagicMock()
        delattr(event, "event_schema_version")
        result = validator.validate_event(event)
        assert result.compatible is False
        assert "missing" in result.reason.lower()

    def test_event_schema_mismatch_suggests_upgrade(self) -> None:
        validator = SchemaValidator()
        event = _event(event_schema_version="99.0")
        result = validator.validate_event(event)
        assert result.remediation == "upgrade providence-runtime"


# ---------------------------------------------------------------------------
# TraceabilityValidator — base requirements
# ---------------------------------------------------------------------------


class TestTraceabilityValidatorBase:
    def test_non_sensitive_requires_only_trace_id(self) -> None:
        validator = TraceabilityValidator()
        event = _event(trace_id="trace-1")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=False)
        assert result.valid is True

    def test_non_sensitive_missing_trace_id_is_invalid(self) -> None:
        validator = TraceabilityValidator()
        event = _event(trace_id="")
        result = validator.validate_event(event, is_sensitive=False)
        assert result.valid is False
        assert "trace_id" in result.missing_fields

    def test_base_result_structure(self) -> None:
        validator = TraceabilityValidator()
        event = _event(trace_id="trace-1")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=False)
        assert isinstance(result, TraceabilityResult)
        assert result.reason == "ok"
        assert result.missing_fields == []


# ---------------------------------------------------------------------------
# TraceabilityValidator — sensitive requirements
# ---------------------------------------------------------------------------


class TestTraceabilityValidatorSensitive:
    def test_sensitive_requires_all_fields(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            trace_id="trace-1",
            workspace_id="ws-1",
            agent_id="agent-1",
            decision_source_refs=["M001"],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is True

    def test_sensitive_missing_trace_id(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            trace_id="",
            workspace_id="ws-1",
            agent_id="agent-1",
            decision_source_refs=["M001"],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is False
        assert "trace_id" in result.missing_fields

    def test_sensitive_missing_workspace_id(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            trace_id="trace-1",
            workspace_id="",
            agent_id="agent-1",
            decision_source_refs=["M001"],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is False
        assert "workspace_id" in result.missing_fields

    def test_sensitive_missing_agent_id(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            trace_id="trace-1",
            workspace_id="ws-1",
            agent_id="",
            decision_source_refs=["M001"],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is False
        assert "agent_id" in result.missing_fields

    def test_sensitive_missing_decision_source_refs(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            trace_id="trace-1",
            workspace_id="ws-1",
            agent_id="agent-1",
            decision_source_refs=[],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is False
        assert "decision_source_refs" in result.missing_fields

    def test_sensitive_missing_multiple_fields(self) -> None:
        validator = TraceabilityValidator()
        event = RuntimeEvent(
            event="governance.violation",
            command="test",
            status="ok",
            trace_id="",
            workspace_id="",
            agent_id="",
            decision_source_refs=[],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is False
        assert len(result.missing_fields) == 4

    def test_sensitive_result_message_includes_missing_fields(self) -> None:
        validator = TraceabilityValidator()
        event = RuntimeEvent(
            event="governance.violation",
            command="test",
            status="ok",
            trace_id="t1",
            workspace_id="",
            agent_id="",
            decision_source_refs=[],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert "missing required traceability fields" in result.reason


# ---------------------------------------------------------------------------
# TraceabilityValidator — auto-sensitive detection
# ---------------------------------------------------------------------------


class TestTraceabilityValidatorAutoSensitive:
    def test_governance_violation_detected_as_sensitive(self) -> None:
        validator = TraceabilityValidator()
        event = _event(event="governance.violation")
        # Empty fields but detected as sensitive
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=None)
        assert result.valid is False
        # Should check all sensitive fields

    def test_policy_validation_fail_detected_as_sensitive(self) -> None:
        validator = TraceabilityValidator()
        event = _event(event="policy.validation.fail")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=None)
        assert result.valid is False

    def test_runtime_drift_detected_detected_as_sensitive(self) -> None:
        validator = TraceabilityValidator()
        event = _event(event="runtime.drift.detected")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=None)
        assert result.valid is False

    def test_policy_override_requested_detected_as_sensitive(self) -> None:
        validator = TraceabilityValidator()
        event = _event(event="policy.override.requested")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=None)
        assert result.valid is False

    def test_unknown_event_detected_as_non_sensitive(self) -> None:
        validator = TraceabilityValidator()
        event = _event(event="custom.event")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        # Should be non-sensitive, only requires trace_id
        result = validator.validate_event(event, is_sensitive=None)
        assert result.valid is True

    def test_explicit_is_sensitive_overrides_auto_detection(self) -> None:
        validator = TraceabilityValidator()
        # governance.violation is sensitive, but we say it's not
        event = _event(event="governance.violation")
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=False)
        # Should only require trace_id
        assert result.valid is True


# ---------------------------------------------------------------------------
# TraceabilityValidator — batch validation
# ---------------------------------------------------------------------------


class TestTraceabilityValidatorBatch:
    def test_batch_returns_empty_when_all_valid(self) -> None:
        validator = TraceabilityValidator()
        events = [
            _event(trace_id="t1"),
            _event(trace_id="t2"),
        ]
        results = validator.validate_batch(events)
        assert len(results) == 0

    def test_batch_returns_only_invalid_events(self) -> None:
        validator = TraceabilityValidator()
        valid_event = _event(trace_id="t1")
        invalid_event = _event(trace_id="")
        events = [valid_event, invalid_event]
        results = validator.validate_batch(events)
        assert len(results) == 1
        evt, result = results[0]
        assert evt is invalid_event
        assert result.valid is False

    def test_batch_with_sensitive_events(self) -> None:
        validator = TraceabilityValidator()
        valid_sensitive = _event(
            event="governance.violation",
            decision_source_refs=["M001"],
        )
        invalid_sensitive = _event(event="policy.validation.fail")
        invalid_sensitive.decision_source_refs = []
        events = [valid_sensitive, invalid_sensitive]
        results = validator.validate_batch(events)
        assert len(results) == 1
        evt, _ = results[0]
        assert evt.event == "policy.validation.fail"

    def test_batch_with_mixed_sensitive_and_non_sensitive(self) -> None:
        validator = TraceabilityValidator()
        non_sensitive_valid = _event(
            event="custom.event", workspace_id="", agent_id="", decision_source_refs=[]
        )
        sensitive_invalid = _event(event="governance.violation")
        sensitive_invalid.workspace_id = ""
        sensitive_invalid.agent_id = ""
        sensitive_invalid.decision_source_refs = []
        events = [non_sensitive_valid, sensitive_invalid]
        results = validator.validate_batch(events)
        assert len(results) == 1

    def test_batch_large_list(self) -> None:
        validator = TraceabilityValidator()
        events = [
            _event(trace_id=f"trace-{i}" if i % 2 == 0 else "") for i in range(100)
        ]
        results = validator.validate_batch(events)
        # Half should be invalid (odd indices)
        assert len(results) == 50


# ---------------------------------------------------------------------------
# Edge cases and special scenarios
# ---------------------------------------------------------------------------


class TestTraceabilityValidatorEdgeCases:
    def test_workspace_id_with_whitespace_only(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            trace_id="t1",
            workspace_id="   ",
            agent_id="a1",
            decision_source_refs=["M001"],
        )
        # Whitespace-only string should be valid (not empty)
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is True

    def test_decision_source_refs_with_single_element(self) -> None:
        validator = TraceabilityValidator()
        event = _event(decision_source_refs=["M001"])
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is True

    def test_decision_source_refs_with_multiple_elements(self) -> None:
        validator = TraceabilityValidator()
        event = _event(decision_source_refs=["M001", "P002", "ADR-003"])
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is True

    def test_decision_source_refs_with_duplicates(self) -> None:
        validator = TraceabilityValidator()
        event = _event(decision_source_refs=["M001", "M001"])
        # Still valid — duplicates are acceptable
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is True

    def test_trace_id_very_long(self) -> None:
        validator = TraceabilityValidator()
        event = _event(trace_id="x" * 10000)
        event.workspace_id = ""
        event.agent_id = ""
        event.decision_source_refs = []
        result = validator.validate_event(event, is_sensitive=False)
        assert result.valid is True

    def test_workspace_id_special_characters(self) -> None:
        validator = TraceabilityValidator()
        event = _event(
            workspace_id="ws-!@#$%",
            agent_id="a1",
            decision_source_refs=["M001"],
        )
        result = validator.validate_event(event, is_sensitive=True)
        assert result.valid is True


# ---------------------------------------------------------------------------
# SchemaCompatibilityResult and TraceabilityResult
# ---------------------------------------------------------------------------


class TestResultDataclasses:
    def test_schema_compatibility_result_defaults(self) -> None:
        result = SchemaCompatibilityResult(
            compatible=True,
            artifact_version="3.0",
            reason="ok",
        )
        assert result.compatible is True
        assert result.artifact_version == "3.0"
        assert result.reason == "ok"
        assert result.remediation == ""

    def test_schema_compatibility_result_with_remediation(self) -> None:
        result = SchemaCompatibilityResult(
            compatible=False,
            artifact_version="9.0",
            reason="unsupported",
            remediation="upgrade",
        )
        assert result.remediation == "upgrade"

    def test_traceability_result_defaults(self) -> None:
        result = TraceabilityResult(valid=True)
        assert result.valid is True
        assert result.missing_fields == []
        assert result.reason == "ok"

    def test_traceability_result_with_missing_fields(self) -> None:
        result = TraceabilityResult(
            valid=False,
            missing_fields=["trace_id", "workspace_id"],
            reason="missing required fields",
        )
        assert result.valid is False
        assert len(result.missing_fields) == 2
