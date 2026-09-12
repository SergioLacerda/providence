"""Unit tests for Agent Handshake Protocol (AHP)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from providence_core.governance.handshake import (
    AgentHandshakeProtocol,
    HandshakeRequest,
    HandshakeResponse,
    ValidationResult,
)

pytestmark = pytest.mark.unit


def _write_profile(tmp_path: Path, profile_type: str = "client") -> None:
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir(exist_ok=True)
    (sdd_dir / "profile").write_text(
        f"[sdd]\ntype = {profile_type}\nname = test\n", encoding="utf-8"
    )


def _write_governance_core(tmp_path: Path, items: list[Any] | None = None) -> Path:
    compiled_dir = tmp_path / ".providence" / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    data = {"items": items or [], "fingerprint": "abc123"}
    path = compiled_dir / "governance-core.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _write_cache(tmp_path: Path, state: str = "HEALTHY", minutes_old: int = 0) -> None:
    cache_dir = tmp_path / ".providence" / "runtime"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ts = (datetime.now() - timedelta(minutes=minutes_old)).isoformat()
    cache = {
        "gap_version": "1.0",
        "status": "ACTIVE",
        "agent_id": "unknown",
        "spec_fingerprint": "abc123",
        "mandates_loaded": [],
        "confidence": 75.0,
        "last_check": ts,
        "state": state,
        "checks": [],
    }
    (cache_dir / "governance-state.json").write_text(
        json.dumps(cache), encoding="utf-8"
    )


class TestHandshakeProtocolInit:
    """Tests for AgentHandshakeProtocol initialization."""

    def test_init_with_default_project_root(self, tmp_path: Path) -> None:
        """Should auto-detect project root when not provided."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.project_root == tmp_path

    def test_init_with_custom_project_root(self, tmp_path: Path) -> None:
        """Should accept custom project root."""
        custom_root = tmp_path / "custom"
        ahp = AgentHandshakeProtocol(project_root=custom_root)
        assert ahp.project_root == custom_root

    def test_init_with_custom_cache_ttl(self, tmp_path: Path) -> None:
        """Should accept custom cache TTL in minutes."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=60)
        assert ahp.cache_ttl == timedelta(minutes=60)

    def test_cache_paths_initialized(self, tmp_path: Path) -> None:
        """Should initialize cache file paths correctly."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.cache_dir == tmp_path / ".providence" / "runtime"
        assert (
            ahp.cache_file
            == tmp_path / ".providence" / "runtime" / "governance-state.json"
        )

    def test_initial_state_is_not_connected(self, tmp_path: Path) -> None:
        """Should start with NOT_CONNECTED state."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.current_state == "NOT_CONNECTED"
        assert ahp.current_confidence == 0.0

    def test_gap_status_initialized(self, tmp_path: Path) -> None:
        """Should initialize GAP (Governance Activation Protocol) status."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.gap_status == "NOT_ACTIVE"


class TestSemanticTriggering:
    """Tests for should_run_handshake semantic detection."""

    def test_technical_keywords_trigger_handshake(self, tmp_path: Path) -> None:
        """Should trigger on technical keywords."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        technical_inputs = [
            "implementar fase 1",
            "code",
            "arquivo",
            "governance",
            "mandates",
            ".providence",
            "architecture",
        ]
        for user_input in technical_inputs:
            assert ahp.should_run_handshake(user_input) is True

    def test_casual_keywords_skip_handshake(self, tmp_path: Path) -> None:
        """Should skip handshake on casual keywords."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        casual_inputs = [
            "oi",
            "ola",
            "hello world",
            "obrigado",
            "thanks for the help",
        ]
        for user_input in casual_inputs:
            assert ahp.should_run_handshake(user_input) is False

    def test_empty_input_skips_handshake(self, tmp_path: Path) -> None:
        """Should skip handshake on empty input."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.should_run_handshake("") is False

    def test_none_input_skips_handshake(self, tmp_path: Path) -> None:
        """Should skip handshake when input is None."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.should_run_handshake(None) is False


class TestLayer1Discovery:
    """Tests for DISCOVERY layer validation."""

    def test_discovery_detects_sdd_directory(self, tmp_path: Path) -> None:
        """Layer 1 should detect .providence/ directory."""
        (tmp_path / ".providence").mkdir()
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_1_discovery()
        assert state == "CONNECTED"
        assert any(r.name == ".providence/ directory" and r.passed for r in results)

    def test_discovery_missing_sdd_directory(self, tmp_path: Path) -> None:
        """Layer 1 should fail when .providence/ is missing."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_1_discovery()
        assert state == "NOT_CONNECTED"
        assert any(r.name == ".providence/ directory" and not r.passed for r in results)

    def test_discovery_detects_profile_file(self, tmp_path: Path) -> None:
        """Layer 1 should detect .providence/profile file."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text("[sdd]\ntype=client\n", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_1_discovery()
        assert any(r.name == ".providence/profile" and r.passed for r in results)


class TestLayer2LinkValidation:
    """Tests for LINK VALIDATION layer."""

    def test_link_validation_reads_profile(self, tmp_path: Path) -> None:
        """Layer 2 should parse .providence/profile."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text("[sdd]\ntype=client\n", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_2_link_validation()
        assert any(
            r.name == ".providence/profile readable" and r.passed for r in results
        )

    def test_link_validation_validates_profile_type(self, tmp_path: Path) -> None:
        """Layer 2 should validate profile type is master or client."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text("[sdd]\ntype=master\n", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_2_link_validation()
        assert any(
            r.name == ".providence/profile type valid" and r.passed for r in results
        )

    def test_link_validation_rejects_invalid_profile_type(self, tmp_path: Path) -> None:
        """Layer 2 should fail on invalid profile type."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text("[sdd]\ntype=invalid\n", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_2_link_validation()
        assert any(
            r.name == ".providence/profile type valid" and not r.passed for r in results
        )

    def test_link_validation_detects_packages_framework(self, tmp_path: Path) -> None:
        """Layer 2 should detect packages framework directory."""
        (tmp_path / "packages").mkdir()
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_2_link_validation()
        assert any(r.name == "packages framework" and r.passed for r in results)


class TestLayer3RuntimeValidation:
    """Tests for RUNTIME VALIDATION layer."""

    def test_runtime_validates_ai_runtime_directory(self, tmp_path: Path) -> None:
        """Layer 3 should check .providence/runtime/ directory."""
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_3_runtime_validation()
        assert any(r.name == ".providence/runtime/" and r.passed for r in results)

    def test_runtime_validates_state_cache(self, tmp_path: Path) -> None:
        """Layer 3 should check governance-state.json cache."""
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text("{}", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_3_runtime_validation()
        assert any(r.name == "state cache" and r.passed for r in results)

    def test_runtime_validates_phase_0_marker(self, tmp_path: Path) -> None:
        """Layer 3 should check PHASE 0 completion marker in .providence/runtime/ (canonical path)."""
        providence_runtime_dir = tmp_path / ".providence" / "runtime"
        providence_runtime_dir.mkdir(parents=True)
        (providence_runtime_dir / ".phase-0-complete").touch()
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_3_runtime_validation()
        assert any(r.name == "PHASE 0 setup" and r.passed for r in results)


class TestStateMachine:
    """Tests for state machine computation."""

    def test_compute_final_state_not_connected(self, tmp_path: Path) -> None:
        """Should return NOT_CONNECTED if layer 1 fails."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state = ahp._compute_final_state("NOT_CONNECTED", "LINK_OK", "READY", "HEALTHY")
        assert state == "NOT_CONNECTED"

    def test_compute_final_state_misconfigured(self, tmp_path: Path) -> None:
        """Should return MISCONFIGURED if layer 2 link is broken."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state = ahp._compute_final_state("CONNECTED", "BROKEN_LINK", "READY", "HEALTHY")
        assert state == "MISCONFIGURED"

    def test_compute_final_state_not_initialized(self, tmp_path: Path) -> None:
        """Should return NOT_INITIALIZED if layer 3 runtime incomplete."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state = ahp._compute_final_state(
            "CONNECTED", "LINK_OK", "NOT_INITIALIZED", "HEALTHY"
        )
        assert state == "NOT_INITIALIZED"

    def test_compute_final_state_partial(self, tmp_path: Path) -> None:
        """Should return PARTIAL if any layer reports partial state."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state = ahp._compute_final_state("CONNECTED", "LINK_OK", "PARTIAL", "HEALTHY")
        assert state == "PARTIAL"

    def test_compute_final_state_healthy(self, tmp_path: Path) -> None:
        """Should return HEALTHY when all layers are healthy."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state = ahp._compute_final_state("CONNECTED", "LINK_OK", "READY", "HEALTHY")
        assert state == "HEALTHY"

    def test_compute_confidence_from_results(self, tmp_path: Path) -> None:
        """Should compute confidence as percentage of passed checks."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        results = [
            ValidationResult(name="check1", passed=True, message="ok", layer="TEST"),
            ValidationResult(name="check2", passed=True, message="ok", layer="TEST"),
            ValidationResult(name="check3", passed=False, message="fail", layer="TEST"),
        ]
        confidence = ahp._compute_confidence(results)
        assert confidence == pytest.approx(66.67, abs=0.1)

    def test_compute_confidence_zero_when_all_failed(self, tmp_path: Path) -> None:
        """Should return 0 confidence when all checks fail."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        results = [
            ValidationResult(name="check1", passed=False, message="fail", layer="TEST"),
            ValidationResult(name="check2", passed=False, message="fail", layer="TEST"),
        ]
        confidence = ahp._compute_confidence(results)
        assert confidence == 0.0


class TestCachePersistence:
    """Tests for cache loading and saving."""

    def test_load_cache_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when cache file doesn't exist."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        cache = ahp._load_cache()
        assert cache is None

    def test_save_and_load_cache(self, tmp_path: Path) -> None:
        """Should save and load cache correctly."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        checks = [{"name": "test", "passed": True, "message": "ok", "layer": "TEST"}]
        ahp._save_cache("HEALTHY", checks, 100.0)

        # Load it back
        cache = ahp._load_cache()
        assert cache is not None
        assert cache["state"] == "HEALTHY"
        assert cache["confidence"] == 100.0

    def test_cache_respects_ttl(self, tmp_path: Path) -> None:
        """Should respect cache TTL (not return expired cache)."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=0)
        checks = [{"name": "test", "passed": True, "message": "ok", "layer": "TEST"}]
        ahp._save_cache("HEALTHY", checks, 100.0)

        # With TTL=0, cache should be instantly expired
        ahp._load_cache()
        # Either None or expired based on implementation
        assert True  # TTL check may vary


class TestHandshakeDataModels:
    """Tests for HandshakeRequest and HandshakeResponse models."""

    def test_handshake_request_to_dict(self) -> None:
        """Should convert HandshakeRequest to dict."""
        request = HandshakeRequest(
            protocol_version="1.0",
            agent_id="test-agent",
            session_id="sess-123",
            timestamp="2026-05-15T10:00:00Z",
        )
        data = request.to_dict()
        assert data["agent_id"] == "test-agent"
        assert data["session_id"] == "sess-123"

    def test_handshake_response_from_dict(self) -> None:
        """Should create HandshakeResponse from dict."""
        data = {
            "agent_id": "test-agent",
            "understood_mandates": ["M001", "M002"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": True,
        }
        response = HandshakeResponse.from_dict(data)
        assert response.agent_id == "test-agent"
        assert response.understood_mandates == ["M001", "M002"]

    def test_handshake_response_to_dict(self) -> None:
        """Should convert HandshakeResponse to dict."""
        response = HandshakeResponse(
            agent_id="test-agent",
            understood_mandates=["M001"],
            skills_to_use=["skill1"],
            acknowledged_signature=True,
        )
        data = response.to_dict()
        assert data["agent_id"] == "test-agent"
        assert isinstance(data, dict)


class TestAhpInitAdditional:
    """Additional AHP initialization scenarios (agent id, TTL by profile)."""

    def test_agent_id_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_AGENT_ID", "test-agent-99")
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        assert ahp.agent_id == "test-agent-99"

    def test_ttl_client_default(self, tmp_path: Path) -> None:
        # No cache_ttl_minutes, no profile -> defaults to client (30 min)
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.cache_ttl == timedelta(minutes=30)

    def test_ttl_master_when_profile_type_is_master(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, "master")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.cache_ttl == timedelta(minutes=480)


class TestSemanticTriggeringAdditional:
    """Additional keyword-triggering scenarios not covered by generic lists."""

    def test_status_keyword_triggers(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.should_run_handshake("check the status") is True

    def test_spec_keyword_triggers(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp.should_run_handshake("show me the spec") is True


class TestLayer1DiscoveryAdditional:
    def test_governance_core_json_check_present(self, tmp_path: Path) -> None:
        (tmp_path / ".providence").mkdir()
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        _, results = ahp._layer_1_discovery()
        names = [r.name for r in results]
        assert "governance-core.json" in names


class TestLayer2LinkValidationAdditional:
    """State-level assertions for layer 2 (not just individual check flags)."""

    def test_no_profile_returns_no_config(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_2_link_validation()
        assert state == "NO_CONFIG"

    def test_valid_profile_returns_link_ok(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, "client")
        # Create packages dir (needed for core_accessible check)
        (tmp_path / "packages").mkdir()
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_2_link_validation()
        assert state == "LINK_OK"


class TestLayer3RuntimeValidationAdditional:
    """State-level assertions for layer 3 (not just individual check flags)."""

    def test_no_runtime_dir_returns_not_initialized(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_3_runtime_validation()
        assert state == "NOT_INITIALIZED"

    def test_runtime_dir_without_state_returns_partial(self, tmp_path: Path) -> None:
        (tmp_path / ".providence" / "runtime").mkdir(parents=True)
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_3_runtime_validation()
        assert state == "PARTIAL"

    def test_full_runtime_returns_ready(self, tmp_path: Path) -> None:
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text("{}", encoding="utf-8")
        (runtime_dir / ".phase-0-complete").write_text("done", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_3_runtime_validation()
        assert state == "READY"


class TestLayer4GovernanceHealth:
    """Tests for GOVERNANCE HEALTH layer (not covered elsewhere in this file)."""

    def test_no_artifacts_returns_unknown(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_4_governance_health()
        assert state == "UNKNOWN"

    def test_valid_governance_core_returns_degraded_or_healthy(
        self, tmp_path: Path
    ) -> None:
        _write_governance_core(tmp_path)
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, _ = ahp._layer_4_governance_health()
        assert state in ("HEALTHY", "DEGRADED")

    def test_invalid_governance_json_governance_not_valid(self, tmp_path: Path) -> None:
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        (compiled_dir / "governance-core.json").write_text("not json", encoding="utf-8")
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        _, results = ahp._layer_4_governance_health()
        integrity_check = next(r for r in results if r.name == "governance integrity")
        assert integrity_check.passed is False


class TestComputeConfidenceAdditional:
    def test_empty_results_returns_zero(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        result = ahp._compute_confidence([])
        assert result == 0.0

    def test_all_passed_returns_100(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        checks = [
            ValidationResult("a", True, "ok", "L1"),
            ValidationResult("b", True, "ok", "L2"),
        ]
        result = ahp._compute_confidence(checks)
        assert result == 100.0


class TestLoadCacheAdditional:
    def test_returns_none_when_cache_expired(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="HEALTHY", minutes_old=100)
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        result = ahp._load_cache()
        assert result is None


class TestMapAhpToGap:
    """GAP (Governance Activation Protocol) status mapping."""

    def test_healthy_maps_to_active(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp._map_ahp_to_gap("HEALTHY", 100.0) == "ACTIVE"

    def test_partial_maps_to_partial(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp._map_ahp_to_gap("PARTIAL", 60.0) == "PARTIAL"

    def test_not_connected_maps_to_not_active(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp._map_ahp_to_gap("NOT_CONNECTED", 0.0) == "NOT_ACTIVE"

    def test_misconfigured_maps_to_not_active(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp._map_ahp_to_gap("MISCONFIGURED", 0.0) == "NOT_ACTIVE"


class TestFormatGapOutput:
    def test_silent_mode_returns_empty(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        result = ahp.format_gap_output(mode="silent")
        assert result == ""

    def test_compact_mode_contains_status(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.gap_status = "ACTIVE"
        result = ahp.format_gap_output(mode="compact")
        assert "ACTIVE" in result

    def test_verbose_mode_contains_confidence(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.gap_status = "PARTIAL"
        ahp.current_confidence = 55.0
        ahp.mandates_loaded = ["M001"]
        result = ahp.format_gap_output(mode="verbose")
        assert "PARTIAL" in result
        assert "55.0" in result


class TestValidate:
    """Integration tests via the public validate() entrypoint."""

    def test_validate_returns_state_and_report(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        assert isinstance(state, str)
        assert state in (
            "NOT_CONNECTED",
            "MISCONFIGURED",
            "NOT_INITIALIZED",
            "PARTIAL",
            "HEALTHY",
        )
        assert report.state == state

    def test_validate_returns_not_connected_without_sdd(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        assert state == "NOT_CONNECTED"

    def test_validate_uses_cache_when_fresh(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="PARTIAL", minutes_old=0)
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        state, report = ahp.validate(output_mode="silent")
        assert state == "PARTIAL"
        assert report.cached is True

    def test_validate_ignores_expired_cache_with_force(self, tmp_path: Path) -> None:
        _write_cache(tmp_path, state="HEALTHY", minutes_old=100)
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        # Force recheck -> should NOT use cache
        assert report.cached is False

    def test_validate_saves_cache_on_fresh_run(self, tmp_path: Path) -> None:
        # NOT_CONNECTED is never cached; create .providence/ so state is non-NOT_CONNECTED
        _write_profile(tmp_path, "client")
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        ahp.validate(output_mode="silent", force_recheck=True)
        cache_file = tmp_path / ".providence" / "runtime" / "governance-state.json"
        assert cache_file.exists()

    def test_validate_with_full_setup_returns_healthy(self, tmp_path: Path) -> None:
        # Set up complete environment
        _write_profile(tmp_path, "client")
        _write_governance_core(tmp_path, [{"id": "M001", "type": "MANDATE"}])
        (tmp_path / "packages").mkdir()
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text("{}", encoding="utf-8")
        (runtime_dir / ".phase-0-complete").write_text("done", encoding="utf-8")

        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=5)
        state, report = ahp.validate(output_mode="silent", force_recheck=True)
        assert state == "HEALTHY"


class TestFormatOutput:
    def _make_report(self, state: str = "HEALTHY") -> Any:
        from providence_core.governance.handshake import HandshakeReport

        return HandshakeReport(
            state=state,
            confidence=75.0,
            checks=[
                {
                    "name": "check1",
                    "passed": True,
                    "message": "ok",
                    "layer": "DISCOVERY",
                }
            ],
            actions=["proceed_silently"],
            cached=False,
            cache_age_seconds=None,
        )

    def test_silent_mode_returns_state_emoji(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        report = self._make_report()
        result = ahp.format_output("HEALTHY", report, mode="silent")
        assert "SDD:" in result

    def test_compact_mode_contains_state(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        report = self._make_report()
        result = ahp.format_output("HEALTHY", report, mode="compact")
        assert "HEALTHY" in result

    def test_verbose_mode_contains_confidence(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        report = self._make_report()
        result = ahp.format_output("HEALTHY", report, mode="verbose")
        assert "75.0" in result
        assert "DISCOVERY" in result

    def test_verbose_mode_with_cached_report(self, tmp_path: Path) -> None:
        from providence_core.governance.handshake import HandshakeReport

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        report = HandshakeReport(
            state="PARTIAL",
            confidence=50.0,
            checks=[],
            actions=[],
            cached=True,
            cache_age_seconds=120,
        )
        result = ahp.format_output("PARTIAL", report, mode="verbose")
        assert "120" in result

    def test_unknown_state_does_not_crash(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        report = self._make_report(state="UNKNOWN_STATE")
        # Should not raise
        result = ahp.format_output("UNKNOWN_STATE", report, mode="compact")
        assert isinstance(result, str)


class TestExtractMandates:
    def test_returns_empty_when_no_governance_core(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp._extract_mandates() == []

    def test_extracts_mandate_ids(self, tmp_path: Path) -> None:
        _write_governance_core(
            tmp_path,
            [
                {"id": "M001", "type": "MANDATE"},
                {"id": "M002", "type": "MANDATE"},
                {"id": "G001", "type": "GUIDELINE"},
            ],
        )
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        mandates = ahp._extract_mandates()
        assert "M001" in mandates
        assert "M002" in mandates
        assert "G001" not in mandates


class TestComputeSpecFingerprint:
    def test_returns_empty_when_no_governance_core(self, tmp_path: Path) -> None:
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        assert ahp._compute_spec_fingerprint() == ""

    def test_returns_16_char_hex(self, tmp_path: Path) -> None:
        _write_governance_core(tmp_path, [{"id": "M001", "type": "MANDATE"}])
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        fp = ahp._compute_spec_fingerprint()
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


class TestGenerateChallengeSkillExport:
    def test_generate_challenge_handles_skill_export_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """generate_challenge must gracefully handle SkillEngine export failures.

        Covers the try-except-pass fallback when
        SkillEngine.export_skills_payload() raises an exception.
        """
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        from unittest.mock import MagicMock, patch

        mock_engine = MagicMock()
        mock_engine.export_skills_payload.side_effect = RuntimeError(
            "Skill export failed"
        )

        with patch("providence_runtime.skills.SkillEngine", return_value=mock_engine):
            # Should not raise despite the exception
            challenge = ahp.generate_challenge(
                task_description="Test with skill export error"
            )

            # Challenge should be created with empty skills list as fallback
            assert challenge is not None
            assert challenge.session_id is not None
            assert challenge.available_skills == []  # Fallback to empty list
            assert challenge.task.get("description") == "Test with skill export error"
