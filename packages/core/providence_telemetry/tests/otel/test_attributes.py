from __future__ import annotations

from providence_telemetry.otel.attributes import to_otel_attributes
from providence_telemetry.otel.constants import (
    EVENT_DOMAIN_KEY,
    EVENT_DOMAIN_VALUE,
    EVENT_NAME_KEY,
    EVENT_TIME_KEY,
    LOG_SEVERITY_KEY,
    LOG_SEVERITY_NUMBER_KEY,
    SDD_EVENT_TIMESTAMP_KEY,
    SDD_EVENT_TYPE_KEY,
    SERVICE_NAME_KEY,
    SERVICE_VERSION_KEY,
    SPAN_ID_KEY,
    TRACE_ID_KEY,
)


def test_maps_core_fields() -> None:
    event = {
        "type": "governance.context_load",
        "timestamp": "2026-05-12T12:00:00Z",
        "severity": "warn",
        "tokens_delta": 42,
        "cache_hit": False,
    }
    attrs = to_otel_attributes(
        event,
        service_name="providence-cli",
        service_version="1.2.3",
        trace_id="t-1",
        span_id="s-1",
    )
    assert attrs[SERVICE_NAME_KEY] == "providence-cli"
    assert attrs[SERVICE_VERSION_KEY] == "1.2.3"
    assert attrs[EVENT_NAME_KEY] == "governance.context_load"
    assert attrs[LOG_SEVERITY_KEY] == "WARN"
    assert attrs[LOG_SEVERITY_NUMBER_KEY] == 13
    assert attrs["sdd.tokens_delta"] == 42
    assert attrs["sdd.cache_hit"] is False
    assert attrs[TRACE_ID_KEY] == "t-1"
    assert attrs[SPAN_ID_KEY] == "s-1"


def test_normalizes_non_scalar_values() -> None:
    event = {
        "type": "runtime.error",
        "details": {"kind": "ValueError"},
        "tags": ["a", "b"],
        "nullable": None,
    }
    attrs = to_otel_attributes(event)
    assert attrs["sdd.details"] == "{'kind': 'ValueError'}"
    assert attrs["sdd.tags"] == "['a', 'b']"
    assert attrs["sdd.nullable"] == "null"


def test_generates_timestamp_when_missing() -> None:
    attrs = to_otel_attributes({"type": "runtime.heartbeat"})
    assert isinstance(attrs[EVENT_TIME_KEY], str)
    assert str(attrs[EVENT_TIME_KEY]).endswith("Z")


def test_standard_otel_keys_present() -> None:
    attrs = to_otel_attributes({"type": "test.event"})
    assert EVENT_DOMAIN_KEY in attrs
    assert attrs[EVENT_DOMAIN_KEY] == EVENT_DOMAIN_VALUE
    assert SDD_EVENT_TYPE_KEY in attrs
    assert SDD_EVENT_TIMESTAMP_KEY in attrs


def test_no_trace_span_ids_when_not_provided() -> None:
    attrs = to_otel_attributes({"type": "test.event"})
    assert TRACE_ID_KEY not in attrs
    assert SPAN_ID_KEY not in attrs


def test_excluded_fields_not_duplicated_in_sdd_namespace() -> None:
    event = {"type": "x", "timestamp": "2026-01-01T00:00:00Z", "severity": "INFO"}
    attrs = to_otel_attributes(event)
    assert "sdd.type" not in attrs
    assert "sdd.timestamp" not in attrs
    assert "sdd.severity" not in attrs


def test_default_service_name_and_version() -> None:
    attrs = to_otel_attributes({"type": "test"})
    assert attrs[SERVICE_NAME_KEY] == "providence-runtime"
    assert attrs[SERVICE_VERSION_KEY] == "unknown"


def test_unknown_severity_defaults_to_9() -> None:
    attrs = to_otel_attributes({"type": "test", "severity": "CUSTOM_LEVEL"})
    assert attrs[LOG_SEVERITY_NUMBER_KEY] == 9


def test_double_sdd_prefix_sanitized() -> None:
    attrs = to_otel_attributes({"type": "test", "sdd.already_namespaced": "value"})
    assert "sdd.already_namespaced" in attrs
    assert "sdd.sdd.already_namespaced" not in attrs
    assert attrs["sdd.already_namespaced"] == "value"


def test_trace_id_key_uses_sdd_namespace() -> None:
    assert TRACE_ID_KEY == "sdd.trace_id"


def test_span_id_key_uses_sdd_namespace() -> None:
    assert SPAN_ID_KEY == "sdd.span_id"


def test_trace_span_ids_appear_under_sdd_namespace() -> None:
    attrs = to_otel_attributes({"type": "test"}, trace_id="t-1", span_id="s-1")
    assert attrs["sdd.trace_id"] == "t-1"
    assert attrs["sdd.span_id"] == "s-1"
