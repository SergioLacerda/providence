"""Determinism Gate tests (§9 item 4).

Validates that the same input tuple (profile + artifact + session) always
produces identical outcomes.  These tests are the replay harness skeleton
defined in §11 (Phase 1 additions) and §12.8 Step 3.

Property under test:
  For any fixed inputs (profile, artifact, session), repeated invocations of
  the same engine method must return the same result.  Non-determinism here
  would indicate hidden state, environment coupling, or randomness leakage.
"""

from __future__ import annotations

from providence_runtime import (
    CompiledArtifact,
    ContextLoader,
    ContextRequest,
    DriftDetector,
    GovernanceInjector,
    GovernanceItem,
    PolicyEngine,
    SessionManager,
    SessionState,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

_ARTIFACT = CompiledArtifact(
    artifact_version="3.0",
    schema_version="3.0",
    fingerprint="fp-determinism",
    generated_at="2026-01-01T00:00:00Z",
    profile="master",
    items=[
        GovernanceItem(id="M001", title="Clean Architecture", item_type="MANDATE"),
        GovernanceItem(id="M002", title="TDD", item_type="MANDATE"),
        GovernanceItem(id="P001", title="Human Review", item_type="POLICY"),
    ],
)

_SESSION = SessionState(
    workspace_id="ws-replay",
    agent_id="agent-replay",
    work_item_id="task-replay",
    artifact_fingerprint="fp-determinism",
    schema_version="3.0",
    policy_set_version="3.0",
    last_validation_ts="2026-01-01T00:00:00Z",  # fixed timestamp for replay
)

_ITERATIONS = 20  # repeat each case this many times


# ─────────────────────────────────────────────────────────────────────────────
# PolicyEngine determinism
# ─────────────────────────────────────────────────────────────────────────────


class TestPolicyDeterminism:
    def test_evaluate_deterministic(self) -> None:
        engine = PolicyEngine()
        results = [
            engine.evaluate(has_artifact=False, is_sensitive=True)
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.allowed == first.allowed
            assert r.severity == first.severity
            assert r.reason == first.reason

    def test_preflight_deterministic(self) -> None:
        engine = PolicyEngine()
        results = [
            engine.validate_preflight(
                artifact=_ARTIFACT,
                session=_SESSION,
                current_profile="master",
            )
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.allowed == first.allowed
            assert r.severity == first.severity
            assert r.reason == first.reason

    def test_preflight_mismatch_deterministic(self) -> None:
        engine = PolicyEngine()
        bad_session = SessionState(
            workspace_id="ws-1",
            agent_id="a-1",
            work_item_id="t-1",
            artifact_fingerprint="stale-fp",
            schema_version="3.0",
            policy_set_version="3.0",
        )
        results = [
            engine.validate_preflight(
                artifact=_ARTIFACT,
                session=bad_session,
                current_profile="master",
            )
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.allowed == first.allowed
            assert r.reason == first.reason


# ─────────────────────────────────────────────────────────────────────────────
# DriftDetector determinism
# ─────────────────────────────────────────────────────────────────────────────


class TestDriftDeterminism:
    def test_detect_no_drift_deterministic(self) -> None:
        detector = DriftDetector()
        results = [
            detector.detect(session_fingerprint="fp-x", artifact_fingerprint="fp-x")
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.drift_detected == first.drift_detected
            assert r.drift_type == first.drift_type

    def test_detect_mismatch_deterministic(self) -> None:
        detector = DriftDetector()
        results = [
            detector.detect(session_fingerprint="fp-a", artifact_fingerprint="fp-b")
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.drift_detected == first.drift_detected
            assert r.drift_type == first.drift_type
            assert r.remediation_command == first.remediation_command

    def test_classify_deterministic(self) -> None:
        detector = DriftDetector()
        results = [
            detector.classify(
                session=_SESSION,
                artifact=_ARTIFACT,
                current_profile="master",
            )
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.drift_detected == first.drift_detected
            assert r.drift_type == first.drift_type


# ─────────────────────────────────────────────────────────────────────────────
# ContextLoader determinism
# ─────────────────────────────────────────────────────────────────────────────


class TestContextDeterminism:
    def test_fallback_deterministic(self) -> None:
        loader = ContextLoader()
        results = [
            loader.load(ContextRequest(query="M001", max_items=3))
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r == first

    def test_artifact_query_deterministic(self) -> None:
        loader = ContextLoader()
        results = [
            loader.load(ContextRequest(query="M001", max_items=3, artifact=_ARTIFACT))
            for _ in range(_ITERATIONS)
        ]
        first = results[0]
        for r in results[1:]:
            assert r == first


# ─────────────────────────────────────────────────────────────────────────────
# GovernanceInjector determinism
# ─────────────────────────────────────────────────────────────────────────────


class TestInjectionDeterminism:
    def test_inject_from_artifact_deterministic(self) -> None:
        injector = GovernanceInjector()
        results = [injector.inject_from_artifact(_ARTIFACT) for _ in range(_ITERATIONS)]
        first = results[0]
        for r in results[1:]:
            assert r.loaded == first.loaded
            assert r.mandates_loaded == first.mandates_loaded
            assert r.policies_loaded == first.policies_loaded
            assert r.artifact_fingerprint == first.artifact_fingerprint
            assert sorted(r.item_ids) == sorted(first.item_ids)


# ─────────────────────────────────────────────────────────────────────────────
# SessionManager determinism (state isolation)
# ─────────────────────────────────────────────────────────────────────────────


class TestSessionIsolation:
    def test_independent_managers_do_not_share_state(self) -> None:
        """Two SessionManager instances must be fully isolated."""
        mgr_a = SessionManager()
        mgr_b = SessionManager()

        state = SessionState(
            workspace_id="ws-iso",
            agent_id="a-1",
            work_item_id="t-1",
            artifact_fingerprint="fp",
            schema_version="3.0",
            policy_set_version="3.0",
        )
        mgr_a.upsert(state)
        assert mgr_b.get("ws-iso", "a-1", "t-1") is None

    def test_upsert_is_idempotent(self) -> None:
        mgr = SessionManager()
        for _ in range(_ITERATIONS):
            mgr.upsert(_SESSION)
        assert len(mgr.all_sessions()) == 1
