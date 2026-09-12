"""Schema and traceability validators for the runtime boundary contract.

Two validators:
- :class:`SchemaValidator` — checks artifact/event schema version compatibility.
- :class:`TraceabilityValidator` — enforces that governance decisions are
  source-linked (§9 Traceability Gate; §12.8 Step 4+5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import CompiledArtifact
    from .telemetry import RuntimeEvent

# Versions this runtime can consume.  Additive range — new versions are added
# here; removed versions require a migration note.
RUNTIME_SUPPORTED_SCHEMA_VERSIONS: tuple[str, ...] = ("3.0", "2.0", "1.0")

# Events that MUST carry decision_source_refs when they represent a sensitive decision.
_SENSITIVE_EVENTS = frozenset(
    {
        "governance.violation",
        "policy.validation.fail",
        "runtime.drift.detected",
        "policy.override.requested",
    }
)


def is_sensitive_event(event_name: str) -> bool:
    """Return True when *event_name* represents a sensitive governance decision.

    Exposed so callers deciding a fail-open/fail-closed emission policy
    (TEL-02) can classify an event by name alone, before a full
    :class:`RuntimeEvent` (or its traceability fields) is even available —
    e.g. inside an exception handler wrapping event construction itself.
    """
    return event_name in _SENSITIVE_EVENTS


# ─────────────────────────────────────────────────────────────────────────────
# Schema compatibility
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SchemaCompatibilityResult:
    """Result of a schema version compatibility check."""

    compatible: bool
    artifact_version: str
    reason: str
    remediation: str = ""


class SchemaValidator:
    """Validates that a :class:`CompiledArtifact`'s schema_version is within
    the range supported by this runtime.

    The supported version set is intentionally additive: adding a new version
    is non-breaking; removing one requires an explicit migration note.
    """

    def __init__(
        self,
        supported_versions: tuple[str, ...] = RUNTIME_SUPPORTED_SCHEMA_VERSIONS,
    ) -> None:
        self._supported = frozenset(supported_versions)

    def validate_artifact(
        self, artifact: CompiledArtifact
    ) -> SchemaCompatibilityResult:
        """Check that *artifact*.schema_version is supported."""
        version = artifact.schema_version
        if not version:
            return SchemaCompatibilityResult(
                compatible=False,
                artifact_version="",
                reason="artifact_missing_schema_version",
                remediation="providence governance compile",
            )
        if version not in self._supported:
            return SchemaCompatibilityResult(
                compatible=False,
                artifact_version=version,
                reason=f"schema_version '{version}' not in supported set {sorted(self._supported)}",
                remediation="providence governance compile --force",
            )
        return SchemaCompatibilityResult(
            compatible=True,
            artifact_version=version,
            reason="ok",
        )

    def validate_event(self, event: RuntimeEvent) -> SchemaCompatibilityResult:
        """Check that *event*.event_schema_version is recognised."""
        from .telemetry import EVENT_SCHEMA_VERSION

        version = getattr(event, "event_schema_version", "")
        if not version:
            return SchemaCompatibilityResult(
                compatible=False,
                artifact_version="",
                reason="event_missing_event_schema_version",
                remediation="upgrade providence-runtime",
            )
        if version != EVENT_SCHEMA_VERSION:
            return SchemaCompatibilityResult(
                compatible=False,
                artifact_version=version,
                reason=f"event schema_version '{version}' != current '{EVENT_SCHEMA_VERSION}'",
                remediation="upgrade providence-runtime",
            )
        return SchemaCompatibilityResult(
            compatible=True, artifact_version=version, reason="ok"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Traceability enforcement
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class TraceabilityResult:
    """Result of a traceability validation check."""

    valid: bool
    missing_fields: list[str] = field(default_factory=list)
    reason: str = "ok"


class TraceabilityValidator:
    """Enforces that governance decisions are source-linked (§9 item 2).

    Every runtime event that represents a sensitive decision must carry:
    - ``trace_id``          — correlation identifier
    - ``workspace_id``      — scope isolation
    - ``agent_id``          — actor identification
    - ``decision_source_refs`` — canonical mandate/policy/ADR references

    Non-sensitive events only require ``trace_id``.
    """

    _REQUIRED_BASE: frozenset[str] = frozenset({"trace_id"})
    _REQUIRED_SENSITIVE: frozenset[str] = frozenset(
        {"trace_id", "workspace_id", "agent_id", "decision_source_refs"}
    )

    def validate_event(
        self, event: RuntimeEvent, is_sensitive: bool | None = None
    ) -> TraceabilityResult:
        """Validate traceability fields on *event*.

        *is_sensitive* defaults to True when the event name is in the known
        sensitive event set.
        """
        if is_sensitive is None:
            is_sensitive = event.event in _SENSITIVE_EVENTS

        required = self._REQUIRED_SENSITIVE if is_sensitive else self._REQUIRED_BASE
        missing: list[str] = []

        for field_name in sorted(required):
            value = getattr(event, field_name, None)
            # decision_source_refs is valid when non-empty list; others valid when non-empty str
            if field_name == "decision_source_refs":
                if not value:
                    missing.append(field_name)
            else:
                if not value:
                    missing.append(field_name)

        if missing:
            return TraceabilityResult(
                valid=False,
                missing_fields=missing,
                reason=f"missing required traceability fields: {missing}",
            )
        return TraceabilityResult(valid=True)

    def validate_batch(
        self, events: list[RuntimeEvent]
    ) -> list[tuple[RuntimeEvent, TraceabilityResult]]:
        """Validate a list of events.  Returns only the failing ones."""
        return [
            (evt, result)
            for evt in events
            if not (result := self.validate_event(evt)).valid
        ]
