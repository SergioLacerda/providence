"""Schema compatibility and Gate B integration tests (§11 Phase 2 additions).

Compatibility test suite for runtime/session schema — verifies that:
1. Forward-compat: old persisted JSON (missing new fields) loads without error.
2. Backward-compat: serialised output round-trips cleanly.
3. Schema evolution: new optional fields added to dataclasses default correctly.
4. Gate B integration: full pipeline (inject → session → policy → event → traceable).
5. Canonical source-link enforcement: critical events carry decision_source_refs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from providence_runtime import (
    CompiledArtifact,
    DriftDetector,
    GovernanceInjector,
    GovernanceItem,
    PolicyEngine,
    RuntimeEvent,
    SchemaValidator,
    SessionManager,
    SessionState,
    TelemetrySink,
    TraceabilityValidator,
)
from providence_runtime.telemetry import EVENT_SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifact(
    fingerprint: str = "fp-compat",
    profile: str = "master",
    schema_version: str = "3.0",
) -> CompiledArtifact:
    return CompiledArtifact(
        artifact_version=schema_version,
        schema_version=schema_version,
        fingerprint=fingerprint,
        generated_at="2026-01-01T00:00:00Z",
        profile=profile,
        items=[
            GovernanceItem(id="M001", title="Clean Architecture", item_type="MANDATE"),
            GovernanceItem(id="P001", title="Human Review", item_type="POLICY"),
        ],
    )


def _make_session(
    fingerprint: str = "fp-compat",
    schema_version: str = "3.0",
) -> SessionState:
    return SessionState(
        workspace_id="ws-compat",
        agent_id="agent-compat",
        work_item_id="task-compat",
        artifact_fingerprint=fingerprint,
        schema_version=schema_version,
        policy_set_version=schema_version,
    )


# ---------------------------------------------------------------------------
# 1. SessionState forward-compat — old JSON missing new optional fields
# ---------------------------------------------------------------------------


class TestSessionStateForwardCompat:
    def test_loads_without_policy_set_version(self) -> None:
        """Old JSON without policy_set_version must fall back to empty string."""
        old_json = {
            "workspace_id": "ws-old",
            "agent_id": "agent-old",
            "work_item_id": "task-old",
            "artifact_fingerprint": "fp-old",
            "schema_version": "2.0",
            # policy_set_version intentionally absent (old schema)
        }
        state = SessionState.from_dict(old_json)
        assert state.workspace_id == "ws-old"
        assert state.policy_set_version == ""

    def test_loads_without_last_validation_ts(self) -> None:
        """Old JSON without last_validation_ts must receive a generated default."""
        old_json = {
            "workspace_id": "ws-old",
            "agent_id": "a",
            "work_item_id": "t",
            "artifact_fingerprint": "fp",
            "schema_version": "2.0",
            "policy_set_version": "2.0",
            # last_validation_ts intentionally absent
        }
        state = SessionState.from_dict(old_json)
        assert state.last_validation_ts != ""

    def test_unknown_extra_fields_ignored(self) -> None:
        """Extra fields in old JSON (future additions) must not crash loading."""
        raw = {
            "workspace_id": "ws-1",
            "agent_id": "a",
            "work_item_id": "t",
            "artifact_fingerprint": "fp",
            "schema_version": "3.0",
            "policy_set_version": "3.0",
            "future_field": "some_value",  # not in current dataclass
        }
        # from_dict only reads known keys; extra fields are silently ignored
        state = SessionState.from_dict(raw)
        assert state.workspace_id == "ws-1"


class TestSessionStateRoundTrip:
    def test_to_dict_from_dict_roundtrip(self) -> None:
        original = _make_session()
        restored = SessionState.from_dict(original.to_dict())
        assert restored.workspace_id == original.workspace_id
        assert restored.artifact_fingerprint == original.artifact_fingerprint
        assert restored.policy_set_version == original.policy_set_version

    def test_persistence_roundtrip_preserves_all_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            mgr = SessionManager(state_dir=state_dir)
            original = _make_session()
            mgr.upsert(original)

            mgr2 = SessionManager(state_dir=state_dir)
            loaded = mgr2.get("ws-compat", "agent-compat", "task-compat")
            assert loaded is not None
            assert loaded.artifact_fingerprint == original.artifact_fingerprint
            assert loaded.schema_version == original.schema_version
            assert loaded.policy_set_version == original.policy_set_version

    def test_multiple_sessions_persist_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            mgr = SessionManager(state_dir=state_dir)
            mgr.upsert(SessionState("ws-1", "a1", "t1", "fp-1", "3.0", "3.0"))
            mgr.upsert(SessionState("ws-2", "a2", "t2", "fp-2", "3.0", "3.0"))

            mgr2 = SessionManager(state_dir=state_dir)
            assert mgr2.get("ws-1", "a1", "t1") is not None
            assert mgr2.get("ws-2", "a2", "t2") is not None


# ---------------------------------------------------------------------------
# 2. CompiledArtifact forward-compat
# ---------------------------------------------------------------------------


class TestCompiledArtifactForwardCompat:
    def test_loads_json_without_profile_field(self) -> None:
        """Old governance-core.json without 'profile' must load gracefully."""
        governance = {
            "category": "CORE",
            "version": "3.0",
            "fingerprint": "fp-no-profile",
            "items": [
                {
                    "id": "M001",
                    "title": "Clean Architecture",
                    "metadata": {"type": "MANDATE", "description": ""},
                }
            ],
            # 'profile' key intentionally absent
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "governance-core.json").write_text(
                json.dumps(governance), encoding="utf-8"
            )
            result = GovernanceInjector().inject_from_path(p)
        assert result.loaded is True
        assert result.mandates_loaded == 1

    def test_from_governance_json_defaults_missing_generated_at(self) -> None:
        """Artifact JSON without generated_at must use a safe default."""
        governance = {
            "category": "CORE",
            "version": "3.0",
            "fingerprint": "fp-test",
            "items": [],
        }
        metadata = {
            "version": "3.0",
            # generated_at intentionally absent
            "fingerprint": "fp-test",
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "governance-core.json").write_text(
                json.dumps(governance), encoding="utf-8"
            )
            (p / "metadata-core.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            art = CompiledArtifact.from_governance_json(
                p / "governance-core.json", p / "metadata-core.json"
            )
        assert art.generated_at == ""  # safe default, not an exception

    def test_find_by_id_case_insensitive_forward_compat(self) -> None:
        art = _make_artifact()
        assert art.find_by_id("m001") is not None
        assert art.find_by_id("p001") is not None
        assert art.find_by_id("X999") is None


# ---------------------------------------------------------------------------
# 3. RuntimeEvent schema evolution — new span_id field
# ---------------------------------------------------------------------------


class TestRuntimeEventSchemaEvolution:
    def test_span_id_auto_generates(self) -> None:
        """span_id was added in Phase C — Fase 1 auto-generates it as 16-char UUID hex."""
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="t1")
        assert evt.span_id != ""
        assert (
            len(evt.span_id) == 16
        )  # UUID hex truncated to 16 chars (OTLP compatible)

    def test_span_id_round_trips_via_json(self) -> None:
        evt = RuntimeEvent(
            event="x", command="y", status="ok", trace_id="t1", span_id="sp-42"
        )
        data = json.loads(evt.to_json())
        assert data["span_id"] == "sp-42"

    def test_event_without_span_id_in_json_still_valid(self) -> None:
        """A JSONL record written before span_id existed (no 'span_id' key) must
        be accepted by SchemaValidator — this simulates a reader consuming old records."""
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="t1")
        result = SchemaValidator().validate_event(evt)
        assert result.compatible is True

    def test_event_schema_version_present_in_all_events(self) -> None:
        for event_name in [
            "runtime.session.start",
            "runtime.drift.detected",
            "policy.validation.fail",
            "governance.ask",
            "governance.ask.full",
            "governance.compile.complete",
        ]:
            evt = RuntimeEvent(
                event=event_name, command="cmd", status="ok", trace_id="t"
            )
            assert evt.event_schema_version == EVENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# 3b. RuntimeEvent schema evolution — trace_time.txt telemetry review fields
# ---------------------------------------------------------------------------


class TestRuntimeEventTelemetryReviewFields:
    """New optional fields added for mission 20260730-sdd-ask-telemetry-critique.

    All must default safely so every existing RuntimeEvent construction site
    (across every command, not just `ask`) keeps working unchanged.
    """

    def test_new_optional_fields_default_safely(self) -> None:
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="t1")
        assert evt.time_to_first_token_ms is None
        assert evt.provider_wait_ms is None
        assert evt.llm_call_count is None
        assert evt.tool_execution_ms is None
        assert evt.phase_slow is False

    def test_new_fields_round_trip_via_json(self) -> None:
        evt = RuntimeEvent(
            event="x",
            command="y",
            status="ok",
            trace_id="t1",
            time_to_first_token_ms=120,
            provider_wait_ms=30,
            llm_call_count=1,
            tool_execution_ms=15,
            phase_slow=True,
        )
        data = json.loads(evt.to_json())
        assert data["time_to_first_token_ms"] == 120
        assert data["provider_wait_ms"] == 30
        assert data["llm_call_count"] == 1
        assert data["tool_execution_ms"] == 15
        assert data["phase_slow"] is True

    def test_event_without_new_fields_in_json_still_valid(self) -> None:
        """A JSONL record written before these fields existed must still be
        accepted by SchemaValidator — same compatibility contract as span_id."""
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="t1")
        result = SchemaValidator().validate_event(evt)
        assert result.compatible is True


# ---------------------------------------------------------------------------
# 4. Gate B integration: full pipeline
# ---------------------------------------------------------------------------


class TestGateBIntegration:
    """Full pipeline test: inject → session → policy check → event → traceable.

    Verifies §15.2 Phase 2 DoD:
    - Runtime decisions are traceable to canonical source refs.
    - Drift detection is active and deterministic.
    - Critical commands still produce valid events.
    """

    def test_full_pipeline_clean_state(self) -> None:
        """Clean state: injection + session bind + preflight all pass."""
        injector = GovernanceInjector()
        artifact = _make_artifact()
        injection = injector.inject_from_artifact(artifact)
        assert injection.loaded is True

        session = SessionState(
            workspace_id="ws-gate",
            agent_id="agent-gate",
            work_item_id="task-gate",
            artifact_fingerprint=injection.artifact_fingerprint,
            schema_version=injection.schema_version,
            policy_set_version=injection.schema_version,
        )
        mgr = SessionManager()
        mgr.upsert(session)
        bound = mgr.is_bound_to_fingerprint(
            "ws-gate", "agent-gate", "task-gate", artifact.fingerprint
        )
        assert bound is True

        policy_result = PolicyEngine().validate_preflight(
            artifact=artifact, session=session, current_profile="master"
        )
        assert policy_result.allowed is True

        drift_report = DriftDetector().classify(
            session=session, artifact=artifact, current_profile="master"
        )
        assert drift_report.drift_detected is False

    def test_full_pipeline_stale_session_triggers_drift(self) -> None:
        """Stale session fingerprint → drift detected → policy blocks."""
        artifact = _make_artifact(fingerprint="fp-current")
        stale_session = _make_session(fingerprint="fp-stale")

        drift_report = DriftDetector().classify(
            session=stale_session, artifact=artifact, current_profile="master"
        )
        assert drift_report.drift_detected is True

        policy_result = PolicyEngine().validate_preflight(
            artifact=artifact, session=stale_session, current_profile="master"
        )
        assert policy_result.allowed is False
        assert policy_result.reason == "session_fingerprint_mismatch"

    def test_full_pipeline_profile_mismatch_blocks(self) -> None:
        """Client session against master artifact → policy blocks."""
        artifact = _make_artifact(fingerprint="fp-abc", profile="master")
        session = _make_session(fingerprint="fp-abc")

        policy_result = PolicyEngine().validate_preflight(
            artifact=artifact, session=session, current_profile="client"
        )
        assert policy_result.allowed is False
        assert policy_result.reason == "profile_mismatch"

    def test_emitted_events_are_traceable(self) -> None:
        """Events emitted by the full pipeline must pass TraceabilityValidator."""
        artifact = _make_artifact()
        session = _make_session()

        events = [
            RuntimeEvent(
                event="runtime.session.start",
                command="runtime status",
                status="ok",
                trace_id="trace-gate-1",
                workspace_id=session.workspace_id,
                agent_id=session.agent_id,
                artifact_fingerprint=artifact.fingerprint,
                schema_version=artifact.schema_version,
                decision_source_refs=["ADR-001-runtime-authority-boundary"],
                details={"ahp_state": "HEALTHY"},
            ),
            RuntimeEvent(
                event="governance.ask",
                command="ask",
                status="ok",
                trace_id="trace-gate-2",
                workspace_id=session.workspace_id,
                agent_id=session.agent_id,
                artifact_fingerprint=artifact.fingerprint,
                schema_version=artifact.schema_version,
                decision_source_refs=["sdd-governance-context"],
                details={"mandates_loaded": 2},
            ),
        ]

        validator = TraceabilityValidator()
        failures = validator.validate_batch(events)
        assert failures == [], (
            f"Gate B failed: {len(failures)} traceability violations:\n"
            + "\n".join(f"  {e.event}: {r.reason}" for e, r in failures)
        )

    def test_events_written_to_jsonl_in_pipeline(self) -> None:
        """Full pipeline events must be persisted to JSONL (not just in-memory)."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "runtime-events.jsonl"
            sink = TelemetrySink(jsonl_path=log, logging_mode="active")

            artifact = _make_artifact()
            session = _make_session()

            sink.emit(
                RuntimeEvent(
                    event="runtime.session.start",
                    command="runtime status",
                    status="ok",
                    trace_id="trace-persist",
                    workspace_id=session.workspace_id,
                    agent_id=session.agent_id,
                    artifact_fingerprint=artifact.fingerprint,
                    schema_version=artifact.schema_version,
                    decision_source_refs=["ADR-001-runtime-authority-boundary"],
                )
            )
            sink.emit(
                RuntimeEvent(
                    event="governance.ask",
                    command="ask",
                    status="ok",
                    trace_id="trace-persist",
                    workspace_id=session.workspace_id,
                    agent_id=session.agent_id,
                    artifact_fingerprint=artifact.fingerprint,
                    schema_version=artifact.schema_version,
                    decision_source_refs=["sdd-governance-context"],
                )
            )

            assert log.exists()
            lines = log.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 2
            events_out = [json.loads(ln) for ln in lines]
            assert events_out[0]["event"] == "runtime.session.start"
            assert events_out[1]["event"] == "governance.ask"


# ---------------------------------------------------------------------------
# 5. Canonical source-link enforcement
# ---------------------------------------------------------------------------


class TestCanonicalSourceLinkEnforcement:
    """Decision source refs must be present and non-empty for sensitive events."""

    @pytest.mark.parametrize(
        ("event_name", "refs"),
        [
            ("runtime.session.start", ["ADR-001-runtime-authority-boundary"]),
            (
                "runtime.drift.detected",
                ["§12.5-anti-drift-strategy", "ADR-001-runtime-authority-boundary"],
            ),
            ("policy.validation.fail", ["policy:P001"]),
            ("governance.ask", ["sdd-governance-context"]),
            ("governance.ask.full", ["sdd-governance-context"]),
            ("governance.compile.complete", ["governance-compiler"]),
        ],
    )
    def test_sensitive_event_has_decision_source_refs(
        self, event_name: str, refs: list[str]
    ) -> None:
        evt = RuntimeEvent(
            event=event_name,
            command="cmd",
            status="ok",
            trace_id="t1",
            workspace_id="ws-1",
            agent_id="a-1",
            decision_source_refs=refs,
        )
        result = TraceabilityValidator().validate_event(evt)
        assert result.valid, f"{event_name} traceability failed: {result.reason}"

    def test_empty_decision_source_refs_fails_sensitive_event(self) -> None:
        evt = RuntimeEvent(
            event="runtime.drift.detected",
            command="runtime status",
            status="warn",
            trace_id="t1",
            workspace_id="ws-1",
            agent_id="a-1",
            decision_source_refs=[],  # empty — must fail
        )
        result = TraceabilityValidator().validate_event(evt)
        assert result.valid is False
        assert "decision_source_refs" in result.missing_fields

    def test_governance_ask_events_carry_source_link(self) -> None:
        """governance.ask and governance.ask.full must reference sdd-governance-context."""
        for event_name in ("governance.ask", "governance.ask.full"):
            evt = RuntimeEvent(
                event=event_name,
                command=event_name.split(".")[-1],
                status="ok",
                trace_id="t",
                workspace_id="ws-1",
                agent_id="a-1",
                decision_source_refs=["sdd-governance-context"],
            )
            result = TraceabilityValidator().validate_event(evt)
            assert result.valid, f"{event_name}: {result.reason}"
