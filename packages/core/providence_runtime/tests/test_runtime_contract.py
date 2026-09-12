"""Contract tests for providence_runtime — Phase 1 DoD.

Each test covers one module's public contract.  Tests use no external
dependencies and verify behaviour that must remain stable across refactors.
"""

from __future__ import annotations

import json
import multiprocessing
import tempfile
from pathlib import Path

import pytest
from providence_runtime import (
    EVENT_SCHEMA_VERSION,
    CompiledArtifact,
    ContextLoader,
    ContextRequest,
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
from providence_runtime.drift import (
    DRIFT_BOOTSTRAP,
    DRIFT_MISMATCH,
    DRIFT_MISSING,
    DRIFT_NONE,
    DRIFT_POLICY,
    DRIFT_PROFILE,
    DRIFT_SESSION,
    check_root_seed_drift,
    extract_seed_fingerprint,
)
from providence_runtime.policy import SEVERITY_HARD, SEVERITY_NONE

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def _make_artifact(
    fingerprint: str = "fp-abc",
    schema_version: str = "3.0",
    profile: str = "master",
    items: list[GovernanceItem] | None = None,
) -> CompiledArtifact:
    return CompiledArtifact(
        artifact_version=schema_version,
        schema_version=schema_version,
        fingerprint=fingerprint,
        generated_at="2026-01-01T00:00:00Z",
        profile=profile,
        items=items
        or [
            GovernanceItem(id="M001", title="Clean Architecture", item_type="MANDATE"),
            GovernanceItem(id="M002", title="TDD", item_type="MANDATE"),
            GovernanceItem(id="P001", title="Human Review", item_type="POLICY"),
        ],
    )


def _make_session(
    fingerprint: str = "fp-abc",
    schema_version: str = "3.0",
) -> SessionState:
    return SessionState(
        workspace_id="ws-1",
        agent_id="agent-1",
        work_item_id="task-1",
        artifact_fingerprint=fingerprint,
        schema_version=schema_version,
        policy_set_version="3.0",
    )


def _upsert_session_in_subprocess(state_dir_str: str, agent_id: str) -> None:
    """Target for a real OS subprocess — module-level so it is
    importable/picklable by `multiprocessing` (fork or spawn)."""
    mgr = SessionManager(state_dir=Path(state_dir_str))
    mgr.upsert(
        SessionState(
            workspace_id="ws-1",
            agent_id=agent_id,
            work_item_id="task-1",
            artifact_fingerprint=f"fp-{agent_id}",
            schema_version="3.0",
            policy_set_version="3.0",
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# artifacts.py
# ─────────────────────────────────────────────────────────────────────────────


class TestCompiledArtifact:
    def test_items_by_type_filters_correctly(self) -> None:
        art = _make_artifact()
        mandates = art.items_by_type("MANDATE")
        assert len(mandates) == 2
        assert all(i.item_type == "MANDATE" for i in mandates)

    def test_find_by_id_case_insensitive(self) -> None:
        art = _make_artifact()
        assert art.find_by_id("m001") is not None
        assert art.find_by_id("M001") is not None
        assert art.find_by_id("X999") is None

    def test_from_governance_json_loads_items(self) -> None:
        governance = {
            "category": "CORE",
            "version": "3.0",
            "fingerprint": "deadbeef",
            "items": [
                {
                    "id": "M001",
                    "title": "Clean Architecture",
                    "metadata": {
                        "type": "MANDATE",
                        "description": "Enforces CA",
                        "rationale": "Separation of concerns",
                    },
                }
            ],
        }
        metadata = {
            "version": "3.0",
            "generated_at": "2026-01-01T00:00:00Z",
            "fingerprint": "deadbeef",
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            items_path = p / "governance-core.json"
            meta_path = p / "metadata-core.json"
            items_path.write_text(json.dumps(governance), encoding="utf-8")
            meta_path.write_text(json.dumps(metadata), encoding="utf-8")

            art = CompiledArtifact.from_governance_json(items_path, meta_path)

        assert art.fingerprint == "deadbeef"
        assert art.schema_version == "3.0"
        assert art.generated_at == "2026-01-01T00:00:00Z"
        assert len(art.items) == 1
        assert art.items[0].id == "M001"
        assert art.items[0].item_type == "MANDATE"


# ─────────────────────────────────────────────────────────────────────────────
# session.py
# ─────────────────────────────────────────────────────────────────────────────


class TestSessionManager:
    def test_upsert_and_get(self) -> None:
        mgr = SessionManager()
        state = _make_session()
        mgr.upsert(state)
        loaded = mgr.get("ws-1", "agent-1", "task-1")
        assert loaded is not None
        assert loaded.artifact_fingerprint == "fp-abc"

    def test_is_bound_to_fingerprint(self) -> None:
        mgr = SessionManager()
        mgr.upsert(_make_session(fingerprint="fp-xyz"))
        assert mgr.is_bound_to_fingerprint("ws-1", "agent-1", "task-1", "fp-xyz")
        assert not mgr.is_bound_to_fingerprint("ws-1", "agent-1", "task-1", "fp-other")

    def test_delete_removes_session(self) -> None:
        mgr = SessionManager()
        mgr.upsert(_make_session())
        deleted = mgr.delete("ws-1", "agent-1", "task-1")
        assert deleted is True
        assert mgr.get("ws-1", "agent-1", "task-1") is None

    def test_persistence_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            mgr = SessionManager(state_dir=state_dir)
            mgr.upsert(_make_session())

            # Load from disk in a new manager instance.
            mgr2 = SessionManager(state_dir=state_dir)
            loaded = mgr2.get("ws-1", "agent-1", "task-1")
            assert loaded is not None
            assert loaded.artifact_fingerprint == "fp-abc"

    def test_corrupt_state_file_starts_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_file = state_dir / SessionManager._STATE_FILENAME
            state_file.write_text("not-json", encoding="utf-8")
            mgr = SessionManager(state_dir=state_dir)
            assert mgr.all_sessions() == []

    def test_state_file_requires_state_dir(self) -> None:
        mgr = SessionManager()
        with pytest.raises(RuntimeError, match="state_dir is required"):
            mgr._state_file()

    def test_concurrent_upserts_from_two_managers_preserve_both(self) -> None:
        """RUN-01 regression: two `SessionManager` instances (simulating two
        processes) each constructed from the same on-disk state, upserting
        *different* session keys, must not clobber one another — the second
        upsert re-reads on-disk state before merging and writing.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` RUN-01.
        """
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            mgr_a = SessionManager(state_dir=state_dir)
            mgr_b = SessionManager(state_dir=state_dir)  # both start from empty disk

            mgr_a.upsert(_make_session(fingerprint="fp-a"))
            mgr_b.upsert(
                SessionState(
                    workspace_id="ws-2",
                    agent_id="agent-2",
                    work_item_id="task-2",
                    artifact_fingerprint="fp-b",
                    schema_version="3.0",
                    policy_set_version="3.0",
                )
            )

            # A fresh manager reading the final on-disk state must see BOTH
            # upserts — the second writer must not have clobbered the first.
            mgr_c = SessionManager(state_dir=state_dir)
            assert mgr_c.get("ws-1", "agent-1", "task-1") is not None
            assert mgr_c.get("ws-2", "agent-2", "task-2") is not None

    def test_upsert_writes_atomically_no_partial_file_on_crash(self) -> None:
        """RUN-01: the state file is written to a temp path and atomically
        renamed into place — a reader can never observe a half-written
        (invalid) JSON file, even if a crash happened mid-write."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            mgr = SessionManager(state_dir=state_dir)
            mgr.upsert(_make_session())

            state_file = state_dir / SessionManager._STATE_FILENAME
            assert state_file.exists()
            # No leftover temp files from the write.
            assert list(state_dir.glob(f"{SessionManager._STATE_FILENAME}.tmp-*")) == []
            # The persisted file is valid, complete JSON.
            json.loads(state_file.read_text(encoding="utf-8"))

    def test_real_multiprocess_upserts_to_different_keys_preserve_both(self) -> None:
        """TST-01 regression: RUN-01's fix was previously only verified by
        reconstructing `SessionManager` instances within a single test
        process, never under real OS-process contention.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TST-01.
        """
        if "fork" not in multiprocessing.get_all_start_methods():
            pytest.skip("requires multiprocessing 'fork' start method")

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            ctx = multiprocessing.get_context("fork")
            procs = [
                ctx.Process(
                    target=_upsert_session_in_subprocess,
                    args=(str(state_dir), f"agent-{i}"),
                )
                for i in range(5)
            ]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=30)
                assert p.exitcode == 0

            final = SessionManager(state_dir=state_dir)
            for i in range(5):
                session = final.get("ws-1", f"agent-{i}", "task-1")
                assert session is not None
                assert session.artifact_fingerprint == f"fp-agent-{i}"

    def test_delete_persists_removal_and_does_not_resurrect_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            mgr = SessionManager(state_dir=state_dir)
            mgr.upsert(_make_session())
            mgr.delete("ws-1", "agent-1", "task-1")

            mgr2 = SessionManager(state_dir=state_dir)
            assert mgr2.get("ws-1", "agent-1", "task-1") is None


# ─────────────────────────────────────────────────────────────────────────────
# policy.py
# ─────────────────────────────────────────────────────────────────────────────


class TestPolicyEngine:
    def test_sensitive_without_artifact_fails_closed(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate(has_artifact=False, is_sensitive=True)
        assert result.allowed is False
        assert result.severity == SEVERITY_HARD

    def test_non_sensitive_without_artifact_warns(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate(has_artifact=False, is_sensitive=False)
        assert result.allowed is True
        assert result.severity == "soft"

    def test_with_artifact_passes(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate(has_artifact=True, is_sensitive=True)
        assert result.allowed is True
        assert result.severity == SEVERITY_NONE

    def test_preflight_passes_when_aligned(self) -> None:
        engine = PolicyEngine()
        art = _make_artifact()
        session = _make_session()
        result = engine.validate_preflight(
            artifact=art, session=session, current_profile="master"
        )
        assert result.allowed is True

    def test_preflight_fails_on_fingerprint_mismatch(self) -> None:
        engine = PolicyEngine()
        art = _make_artifact(fingerprint="fp-abc")
        session = _make_session(fingerprint="fp-different")
        result = engine.validate_preflight(
            artifact=art, session=session, current_profile="master"
        )
        assert result.allowed is False
        assert result.reason == "session_fingerprint_mismatch"

    def test_preflight_fails_on_profile_mismatch(self) -> None:
        engine = PolicyEngine()
        art = _make_artifact(profile="master")
        session = _make_session()
        result = engine.validate_preflight(
            artifact=art, session=session, current_profile="client"
        )
        assert result.allowed is False
        assert result.reason == "profile_mismatch"

    def test_handshake_guard_allows_when_response_missing(self, tmp_path: Path) -> None:
        engine = PolicyEngine()
        result = engine._check_handshake_guard("sdd-diagnose", project_root=tmp_path)
        # Opt-in model: missing handshake blocks execution
        assert result is not None
        assert result.allowed is False
        assert "handshake not established" in result.reason

    def test_handshake_guard_blocks_undeclared_skill(self, tmp_path: Path) -> None:
        engine = PolicyEngine()
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "handshake-response.json").write_text(
            json.dumps(
                {
                    "agent_id": "agent-1",
                    "skills_to_use": ["sdd-review-architecture"],
                    "acknowledged_signature": True,
                }
            ),
            encoding="utf-8",
        )

        result = engine._check_handshake_guard("sdd-diagnose", project_root=tmp_path)
        assert result is not None
        assert result.allowed is False
        assert (
            result.reason
            == "skill 'sdd-diagnose' was not declared in the initial handshake"
        )

    def test_handshake_guard_allows_declared_skill(self, tmp_path: Path) -> None:
        engine = PolicyEngine()
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "handshake-response.json").write_text(
            json.dumps(
                {
                    "agent_id": "agent-1",
                    "skills_to_use": ["sdd-diagnose"],
                    "acknowledged_signature": True,
                }
            ),
            encoding="utf-8",
        )

        result = engine._check_handshake_guard("sdd-diagnose", project_root=tmp_path)
        assert result is None

    def test_handshake_guard_fails_open_on_invalid_json(self, tmp_path: Path) -> None:
        engine = PolicyEngine()
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / "handshake-response.json").write_text(
            "{not-valid-json",
            encoding="utf-8",
        )

        result = engine._check_handshake_guard("sdd-diagnose", project_root=tmp_path)
        # Opt-in model: invalid JSON blocks execution
        assert result is not None
        assert result.allowed is False
        assert "malformed" in result.reason


# ─────────────────────────────────────────────────────────────────────────────
# context.py
# ─────────────────────────────────────────────────────────────────────────────


class TestContextLoader:
    def test_fallback_without_artifact(self) -> None:
        loader = ContextLoader()
        out = loader.load(ContextRequest(query="M003", max_items=3))
        assert out == ["context:M003"]

    def test_empty_query_returns_empty(self) -> None:
        loader = ContextLoader()
        assert loader.load(ContextRequest(query="  ")) == []

    def test_artifact_exact_id_match(self) -> None:
        loader = ContextLoader()
        art = _make_artifact()
        out = loader.load(ContextRequest(query="M001", max_items=5, artifact=art))
        assert len(out) == 1
        assert "M001" in out[0]

    def test_artifact_type_filter(self) -> None:
        loader = ContextLoader()
        art = _make_artifact()
        result = loader.load_result(
            ContextRequest(
                query="M", max_items=10, artifact=art, item_types=["MANDATE"]
            )
        )
        assert result.source == "artifact"
        assert all("P001" not in line for line in result.items)

    def test_artifact_max_items_respected(self) -> None:
        loader = ContextLoader()
        art = _make_artifact()
        # query "M" matches M001 + M002
        result = loader.load_result(
            ContextRequest(query="M", max_items=1, artifact=art)
        )
        assert len(result.items) == 1


# ─────────────────────────────────────────────────────────────────────────────
# drift.py
# ─────────────────────────────────────────────────────────────────────────────


class TestDriftDetector:
    def test_no_drift_when_fingerprints_match(self) -> None:
        detector = DriftDetector()
        report = detector.detect(session_fingerprint="abc", artifact_fingerprint="abc")
        assert report.drift_detected is False
        assert report.drift_type == DRIFT_NONE

    def test_fingerprint_mismatch(self) -> None:
        detector = DriftDetector()
        report = detector.detect(session_fingerprint="a", artifact_fingerprint="b")
        assert report.drift_detected is True
        assert report.drift_type == DRIFT_MISMATCH
        assert report.remediation_command  # must be non-empty

    def test_missing_fingerprint(self) -> None:
        detector = DriftDetector()
        report = detector.detect(session_fingerprint="", artifact_fingerprint="b")
        assert report.drift_detected is True
        assert "missing" in report.drift_type

    def test_classify_no_drift(self) -> None:
        detector = DriftDetector()
        art = _make_artifact()
        session = _make_session()
        report = detector.classify(
            session=session, artifact=art, current_profile="master"
        )
        assert report.drift_detected is False

    def test_classify_profile_drift(self) -> None:
        detector = DriftDetector()
        art = _make_artifact(profile="master")
        session = _make_session()
        report = detector.classify(
            session=session, artifact=art, current_profile="client"
        )
        assert report.drift_type == DRIFT_PROFILE

    def test_classify_session_drift(self) -> None:
        detector = DriftDetector()
        art = _make_artifact(fingerprint="fp-current")
        session = _make_session(fingerprint="fp-stale")
        report = detector.classify(
            session=session, artifact=art, current_profile="master"
        )
        assert report.drift_type == DRIFT_SESSION
        assert report.remediation_command

    def test_classify_policy_drift(self) -> None:
        detector = DriftDetector()
        art = _make_artifact(fingerprint="fp-abc", schema_version="4.0")
        session = _make_session(fingerprint="fp-abc", schema_version="3.0")
        report = detector.classify(
            session=session, artifact=art, current_profile="master"
        )
        assert report.drift_type == DRIFT_POLICY


class TestRootSeedDrift:
    def test_extract_seed_fingerprint_finds_header_comment(self) -> None:
        content = "# Governance fingerprint: 58a087b3c9fb9ce2\n\nBody text."
        assert extract_seed_fingerprint(content) == "58a087b3c9fb9ce2"

    def test_extract_seed_fingerprint_none_when_absent(self) -> None:
        assert extract_seed_fingerprint("# No fingerprint here\n") is None

    def test_no_drift_when_seed_matches_metadata(self) -> None:
        report = check_root_seed_drift(
            seed_name="CLAUDE.md",
            seed_content="# Governance fingerprint: abc123\n",
            metadata_fingerprint="abc123",
        )
        assert report.drift_detected is False
        assert report.drift_type == DRIFT_NONE

    def test_bootstrap_drift_when_seed_mismatches_metadata(self) -> None:
        report = check_root_seed_drift(
            seed_name="CLAUDE.md",
            seed_content="# Governance fingerprint: abc123\n",
            metadata_fingerprint="def456",
        )
        assert report.drift_detected is True
        assert report.drift_type == DRIFT_BOOTSTRAP
        assert report.remediation_command

    def test_missing_when_seed_has_no_fingerprint(self) -> None:
        report = check_root_seed_drift(
            seed_name="AGENTS.md",
            seed_content="No fingerprint comment.",
            metadata_fingerprint="abc123",
        )
        assert report.drift_detected is True
        assert report.drift_type == DRIFT_MISSING

    def test_missing_when_metadata_fingerprint_absent(self) -> None:
        report = check_root_seed_drift(
            seed_name="CLAUDE.md",
            seed_content="# Governance fingerprint: abc123\n",
            metadata_fingerprint=None,
        )
        assert report.drift_detected is True
        assert report.drift_type == DRIFT_MISSING


# ─────────────────────────────────────────────────────────────────────────────
# injection.py
# ─────────────────────────────────────────────────────────────────────────────


class TestGovernanceInjector:
    def test_inject_from_artifact(self) -> None:
        injector = GovernanceInjector()
        art = _make_artifact()
        result = injector.inject_from_artifact(art)
        assert result.loaded is True
        assert result.source == "artifact"
        assert result.mandates_loaded == 2
        assert result.policies_loaded == 1
        assert "M001" in result.item_ids
        assert result.artifact_fingerprint == "fp-abc"

    def test_inject_from_path_missing_dir(self) -> None:
        injector = GovernanceInjector()
        result = injector.inject_from_path(Path("/nonexistent/path"))
        assert result.loaded is False

    def test_inject_from_path_real_json(self) -> None:
        governance = {
            "category": "CORE",
            "version": "3.0",
            "fingerprint": "deadbeef",
            "items": [
                {
                    "id": "M001",
                    "title": "Clean Architecture",
                    "metadata": {"type": "MANDATE", "description": ""},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "governance-core.json").write_text(
                json.dumps(governance), encoding="utf-8"
            )
            result = GovernanceInjector().inject_from_path(p)
        assert result.loaded is True
        assert result.mandates_loaded == 1
        assert "M001" in result.item_ids

    def test_legacy_inject_shim(self) -> None:
        injector = GovernanceInjector()
        result = injector.inject(context_source="compiled", mandates_loaded=3)
        assert result.loaded is True
        assert result.source == "compiled"
        assert result.mandates_loaded == 3


# ─────────────────────────────────────────────────────────────────────────────
# telemetry.py
# ─────────────────────────────────────────────────────────────────────────────


class TestTelemetrySink:
    def test_emit_stores_event(self) -> None:
        sink = TelemetrySink()
        sink.emit(
            RuntimeEvent(
                event="runtime.session.start",
                command="runtime",
                status="ok",
                trace_id="t1",
            )
        )
        events = sink.list_events()
        assert len(events) == 1
        assert events[0].event == "runtime.session.start"

    def test_event_to_json_is_valid(self) -> None:
        evt = RuntimeEvent(
            event="policy.validation.fail",
            command="check",
            status="fail",
            trace_id="t2",
            workspace_id="ws-1",
            agent_id="a-1",
            artifact_fingerprint="fp-abc",
            schema_version="3.0",
        )
        data = json.loads(evt.to_json())
        assert data["event"] == "policy.validation.fail"
        assert data["workspace_id"] == "ws-1"

    def test_passive_mode_only_emits_mandatory_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "events.jsonl"
            sink = TelemetrySink(jsonl_path=jsonl, logging_mode="passive")
            # DEBUG event — should NOT be written to JSONL
            sink.emit(
                RuntimeEvent(
                    event="runtime.debug.trace",
                    command="x",
                    status="ok",
                    trace_id="t0",
                    level="DEBUG",
                )
            )
            # Mandatory event — MUST be written
            sink.emit(
                RuntimeEvent(
                    event="governance.violation",
                    command="check",
                    status="fail",
                    trace_id="t1",
                )
            )

            lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["event"] == "governance.violation"

    def test_active_mode_emits_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "events.jsonl"
            sink = TelemetrySink(jsonl_path=jsonl, logging_mode="active")
            sink.emit(
                RuntimeEvent(
                    event="runtime.debug.trace", command="x", status="ok", trace_id="t0"
                )
            )
            sink.emit(
                RuntimeEvent(
                    event="governance.violation",
                    command="check",
                    status="fail",
                    trace_id="t1",
                )
            )

            lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    @pytest.mark.parametrize("mode", ["passive", "active", "strict"])
    def test_list_events_always_complete(self, mode: str) -> None:
        sink = TelemetrySink(logging_mode=mode)
        for i in range(5):
            sink.emit(
                RuntimeEvent(
                    event=f"event.{i}", command="cmd", status="ok", trace_id=f"t{i}"
                )
            )
        assert len(sink.list_events()) == 5

    def test_event_carries_schema_version(self) -> None:
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="t")
        assert evt.event_schema_version == EVENT_SCHEMA_VERSION

    def test_work_item_segmentation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "events.jsonl"
            sink = TelemetrySink(
                jsonl_path=base, logging_mode="active", segment_by_work_item=True
            )
            sink.emit(
                RuntimeEvent(
                    event="governance.violation",
                    command="c",
                    status="fail",
                    trace_id="t1",
                    details={"work_item_id": "task-42"},
                )
            )
            sink.emit(
                RuntimeEvent(
                    event="governance.violation",
                    command="c",
                    status="fail",
                    trace_id="t2",
                    details={"work_item_id": "task-99"},
                )
            )

            assert (Path(tmp) / "task-42.jsonl").exists()
            assert (Path(tmp) / "task-99.jsonl").exists()
            assert not base.exists()  # base file not used when all events are segmented

    def test_resolve_path_requires_jsonl_path(self) -> None:
        sink = TelemetrySink()
        with pytest.raises(RuntimeError, match="jsonl_path is required"):
            sink._resolve_path(
                RuntimeEvent(event="x", command="c", status="ok", trace_id="t")
            )


# ─────────────────────────────────────────────────────────────────────────────
# validator.py — SchemaValidator
# ─────────────────────────────────────────────────────────────────────────────


class TestSchemaValidator:
    def test_supported_version_passes(self) -> None:
        validator = SchemaValidator()
        art = _make_artifact(schema_version="3.0")
        result = validator.validate_artifact(art)
        assert result.compatible is True

    def test_unsupported_version_fails(self) -> None:
        validator = SchemaValidator()
        art = _make_artifact(schema_version="99.0")
        result = validator.validate_artifact(art)
        assert result.compatible is False
        assert "99.0" in result.reason

    def test_missing_schema_version_fails(self) -> None:
        validator = SchemaValidator()
        art = _make_artifact(schema_version="")
        result = validator.validate_artifact(art)
        assert result.compatible is False

    def test_event_schema_version_valid(self) -> None:
        validator = SchemaValidator()
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="t")
        result = validator.validate_event(evt)
        assert result.compatible is True

    def test_custom_supported_set(self) -> None:
        validator = SchemaValidator(supported_versions=("1.0",))
        art = _make_artifact(schema_version="3.0")
        result = validator.validate_artifact(art)
        assert result.compatible is False


# ─────────────────────────────────────────────────────────────────────────────
# validator.py — TraceabilityValidator
# ─────────────────────────────────────────────────────────────────────────────


class TestTraceabilityValidator:
    def test_non_sensitive_only_needs_trace_id(self) -> None:
        tv = TraceabilityValidator()
        evt = RuntimeEvent(
            event="runtime.info", command="x", status="ok", trace_id="t1"
        )
        result = tv.validate_event(evt, is_sensitive=False)
        assert result.valid is True

    def test_sensitive_requires_all_fields(self) -> None:
        tv = TraceabilityValidator()
        evt = RuntimeEvent(
            event="governance.violation",
            command="check",
            status="fail",
            trace_id="t1",
            workspace_id="ws-1",
            agent_id="a-1",
            decision_source_refs=["M001"],
        )
        result = tv.validate_event(evt)
        assert result.valid is True

    def test_sensitive_missing_refs_fails(self) -> None:
        tv = TraceabilityValidator()
        evt = RuntimeEvent(
            event="governance.violation",
            command="check",
            status="fail",
            trace_id="t1",
            workspace_id="ws-1",
            agent_id="a-1",
            # decision_source_refs intentionally empty
        )
        result = tv.validate_event(evt)
        assert result.valid is False
        assert "decision_source_refs" in result.missing_fields

    def test_missing_trace_id_always_fails(self) -> None:
        tv = TraceabilityValidator()
        evt = RuntimeEvent(event="x", command="y", status="ok", trace_id="")
        result = tv.validate_event(evt, is_sensitive=False)
        assert result.valid is False
        assert "trace_id" in result.missing_fields

    def test_validate_batch_returns_only_failures(self) -> None:
        tv = TraceabilityValidator()
        good = RuntimeEvent(event="x", command="y", status="ok", trace_id="t1")
        bad = RuntimeEvent(event="x", command="y", status="ok", trace_id="")
        failures = tv.validate_batch([good, bad])
        assert len(failures) == 1
        assert failures[0][0] is bad
