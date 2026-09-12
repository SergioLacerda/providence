from types import SimpleNamespace

from providence_runtime.validator import (
    SchemaCompatibilityResult,
    SchemaValidator,
    TraceabilityValidator,
)


class DummyArtifact:
    def __init__(self, schema_version):
        self.schema_version = schema_version


class DummyEvent(SimpleNamespace):
    pass


def test_schema_validator_supported():
    validator = SchemaValidator()
    artifact = DummyArtifact(schema_version="3.0")
    result = validator.validate_artifact(artifact)
    assert isinstance(result, SchemaCompatibilityResult)
    assert result.compatible
    assert result.reason == "ok"


def test_schema_validator_missing_version():
    validator = SchemaValidator()
    artifact = DummyArtifact(schema_version=None)
    result = validator.validate_artifact(artifact)
    assert not result.compatible
    assert "missing_schema_version" in result.reason


def test_schema_validator_unsupported_version():
    validator = SchemaValidator()
    artifact = DummyArtifact(schema_version="9.9")
    result = validator.validate_artifact(artifact)
    assert not result.compatible
    assert "not in supported set" in result.reason


def test_schema_validator_event_version_mismatch():
    validator = SchemaValidator()
    # EVENT_SCHEMA_VERSION real
    from providence_runtime.telemetry import EVENT_SCHEMA_VERSION

    class DummyEvent:
        event_schema_version = "X.Y"

    event = DummyEvent()
    result = validator.validate_event(event)
    if EVENT_SCHEMA_VERSION != "X.Y":
        assert not result.compatible
        assert "event schema_version" in result.reason
    else:
        assert result.compatible
        assert result.reason == "ok"


def test_traceability_validator_base():
    validator = TraceabilityValidator()
    event = DummyEvent(event="not_sensitive", trace_id="abc")
    result = validator.validate_event(event, is_sensitive=False)
    assert result.valid


def test_traceability_validator_base_missing():
    validator = TraceabilityValidator()
    event = DummyEvent(event="not_sensitive")
    result = validator.validate_event(event, is_sensitive=False)
    assert not result.valid
    assert "trace_id" in result.missing_fields


def test_traceability_validator_sensitive():
    validator = TraceabilityValidator()
    event = DummyEvent(
        event="governance.violation",
        trace_id="abc",
        workspace_id="ws1",
        agent_id="agent",
        decision_source_refs=["M001"],
    )
    result = validator.validate_event(event, is_sensitive=True)
    assert result.valid


def test_traceability_validator_sensitive_missing():
    validator = TraceabilityValidator()
    event = DummyEvent(
        event="governance.violation",
        trace_id="abc",
        workspace_id="ws1",
        agent_id="agent",
        decision_source_refs=[],
    )
    result = validator.validate_event(event, is_sensitive=True)
    assert not result.valid
    assert "decision_source_refs" in result.missing_fields


def test_traceability_validator_auto_sensitive():
    validator = TraceabilityValidator()
    # Evento sensível detectado automaticamente
    event = DummyEvent(
        event="governance.violation",
        trace_id="abc",
        workspace_id="ws1",
        agent_id="agent",
        decision_source_refs=["M001"],
    )
    result = validator.validate_event(event, is_sensitive=None)
    assert result.valid
    # Evento sensível faltando campos
    event = DummyEvent(event="policy.validation.fail")
    result = validator.validate_event(event, is_sensitive=None)
    assert not result.valid
    assert set(
        ["trace_id", "workspace_id", "agent_id", "decision_source_refs"]
    ).issubset(set(result.missing_fields))


def test_traceability_validator_batch():
    validator = TraceabilityValidator()
    events = [
        DummyEvent(
            event="governance.violation",
            trace_id="abc",
            workspace_id="ws1",
            agent_id="agent",
            decision_source_refs=["M001"],
        ),
        DummyEvent(
            event="governance.violation",
            trace_id="abc",
            workspace_id="ws1",
            agent_id="agent",
            decision_source_refs=[],
        ),
    ]
    results = validator.validate_batch(events)
    assert len(results) == 1
    evt, res = results[0]
    assert not res.valid
    assert "decision_source_refs" in res.missing_fields


def test_traceability_validator_batch_multiple_invalid():
    validator = TraceabilityValidator()
    events = [
        DummyEvent(event="governance.violation"),
        DummyEvent(event="policy.validation.fail"),
        DummyEvent(event="not_sensitive", trace_id="abc"),
    ]
    results = validator.validate_batch(events)
    assert len(results) == 2
    for _evt, res in results:
        assert not res.valid
