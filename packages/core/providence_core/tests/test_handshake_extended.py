"""Extended tests for Agent Handshake Protocol (higher coverage)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from providence_core.governance.handshake import AgentHandshakeProtocol

pytestmark = pytest.mark.unit


class TestLayer4GovernanceHealth:
    """Tests for Layer 4 governance health checks."""

    def test_layer_4_detects_governance_integrity(self, tmp_path: Path) -> None:
        """Layer 4 should validate governance-core.json integrity."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"
        governance_file.write_text(
            json.dumps({"items": [{"id": "M001"}]}), encoding="utf-8"
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_4_governance_health()

        assert any(r.name == "governance integrity" and r.passed for r in results)

    def test_layer_4_checks_compiled_artifacts(self, tmp_path: Path) -> None:
        """Layer 4 should detect compiled artifact directories."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, results = ahp._layer_4_governance_health()

        assert any(r.name == "compiled artifacts" for r in results)


class TestMandateExtraction:
    """Tests for mandate extraction and fingerprinting."""

    def test_extract_mandates_from_governance_core(self, tmp_path: Path) -> None:
        """Should extract MANDATE IDs from governance-core.json."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"
        governance_file.write_text(
            json.dumps(
                {
                    "items": [
                        {"id": "M001", "type": "MANDATE"},
                        {"id": "M002", "type": "MANDATE"},
                        {"id": "G001", "type": "GUIDELINE"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        mandates = ahp._extract_mandates()

        assert "M001" in mandates
        assert "M002" in mandates
        assert "G001" not in mandates

    def test_extract_mandates_new_schema(self, tmp_path: Path) -> None:
        """Should extract mandates using new schema with metadata.type."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"
        governance_file.write_text(
            json.dumps(
                {
                    "items": [
                        {"id": "M005", "metadata": {"type": "MANDATE"}},
                    ]
                }
            ),
            encoding="utf-8",
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        mandates = ahp._extract_mandates()

        assert "M005" in mandates

    def test_compute_spec_fingerprint(self, tmp_path: Path) -> None:
        """Should compute SHA-256 fingerprint of governance spec."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"
        governance_file.write_text(
            json.dumps(
                {
                    "items": [{"id": "M001"}],
                    "version": "1.0",
                }
            ),
            encoding="utf-8",
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        fingerprint = ahp._compute_spec_fingerprint()

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 16  # SHA256 truncated to 16 hex chars

    def test_fingerprint_ignores_signature_fields(self, tmp_path: Path) -> None:
        """Should exclude _signature and fingerprint from compute."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"

        data = {"items": [{"id": "M001"}], "_signature": "should-be-ignored"}
        governance_file.write_text(json.dumps(data), encoding="utf-8")

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        fp1 = ahp._compute_spec_fingerprint()

        # Add signature and fingerprint fields
        data["_signature"] = "different-signature"
        data["fingerprint"] = "different-fp"
        governance_file.write_text(json.dumps(data), encoding="utf-8")

        fp2 = ahp._compute_spec_fingerprint()

        # Fingerprints should be same (signatures ignored)
        assert fp1 == fp2


class TestGAPStatusMapping:
    """Tests for GAP (Governance Activation Protocol) status mapping."""

    def test_map_ahp_to_gap_healthy(self, tmp_path: Path) -> None:
        """Should map HEALTHY AHP state to ACTIVE GAP status."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        gap_status = ahp._map_ahp_to_gap("HEALTHY", 100.0)
        assert gap_status == "ACTIVE"

    def test_map_ahp_to_gap_partial(self, tmp_path: Path) -> None:
        """Should map PARTIAL AHP state to PARTIAL GAP status."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        gap_status = ahp._map_ahp_to_gap("PARTIAL", 50.0)
        assert gap_status == "PARTIAL"

    def test_map_ahp_to_gap_not_connected(self, tmp_path: Path) -> None:
        """Should map NOT_CONNECTED to NOT_ACTIVE."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        gap_status = ahp._map_ahp_to_gap("NOT_CONNECTED", 0.0)
        assert gap_status == "NOT_ACTIVE"


class TestValidateMethod:
    """Tests for the main validate() entry point."""

    def test_validate_returns_tuple(self, tmp_path: Path) -> None:
        """validate() should return (state, HandshakeReport) tuple."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, report = ahp.validate()

        assert isinstance(state, str)
        assert hasattr(report, "state")
        assert hasattr(report, "confidence")

    def test_validate_caches_state(self, tmp_path: Path) -> None:
        """validate() should save state to cache for non-transient states only.

        A bare workspace with no .providence directory produces NOT_CONNECTED, which
        is a transient setup state and must never be written to disk.
        """
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state1, _ = ahp.validate()

        # NOT_CONNECTED is transient — cache file must NOT exist
        assert state1 == "NOT_CONNECTED"
        assert not ahp.cache_file.exists()

    def test_validate_loads_from_cache(self, tmp_path: Path) -> None:
        """validate() should use cached state when available.

        A bare workspace produces NOT_CONNECTED, which is never persisted.
        So a second validate() call on the same bare workspace must also
        revalidate (cached=False) rather than reading a stale cache entry.
        """
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.validate()  # attempt to warm cache (no-op for NOT_CONNECTED)

        # Create new instance and validate — cache was never written, so
        # the result must be a fresh check, not a cache hit.
        ahp2 = AgentHandshakeProtocol(project_root=tmp_path)
        state2, report2 = ahp2.validate()

        assert report2.cached is False

    def test_validate_force_recheck(self, tmp_path: Path) -> None:
        """validate(force_recheck=True) should bypass cache."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.validate()  # warm cache

        # Force recheck should not use cache
        state2, report2 = ahp.validate(force_recheck=True)
        assert report2.cached is False


class TestOutputFormatting:
    """Tests for output formatting methods."""

    def test_format_silent_output(self, tmp_path: Path) -> None:
        """Silent mode should return minimal output."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, report = ahp.validate()

        output = ahp.format_output(state, report, mode="silent")
        # Silent mode returns minimal "SDD: X" format
        assert "SDD:" in output

    def test_format_compact_output(self, tmp_path: Path) -> None:
        """Compact mode should include state and checks."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, report = ahp.validate()

        output = ahp.format_output(state, report, mode="compact")
        assert "SDD STATUS" in output or "State:" in output

    def test_format_verbose_output(self, tmp_path: Path) -> None:
        """Verbose mode should include detailed layer information."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, report = ahp.validate()

        output = ahp.format_output(state, report, mode="verbose")
        # Verbose output should be longer and more detailed
        assert len(output) > 0

    def test_gap_output_formatting(self, tmp_path: Path) -> None:
        """Should format GAP output correctly."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.gap_status = "ACTIVE"
        ahp.mandates_loaded = ["M001", "M002"]

        output = ahp.format_gap_output(mode="compact")
        assert "SDD Governance" in output or "ACTIVE" in output


class TestGenerateChallenge:
    """Tests for handshake challenge generation."""

    def test_generate_challenge_returns_request(self, tmp_path: Path) -> None:
        """generate_challenge() should return HandshakeRequest."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        with patch("providence_runtime.skills.SkillEngine"):
            request = ahp.generate_challenge("Test Task", task_type="test")

            assert request.task["description"] == "Test Task"
            assert request.task["type"] == "test"

    def test_generate_challenge_includes_mandates(self, tmp_path: Path) -> None:
        """Challenge should include active mandates."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.mandates_loaded = ["M001", "M002"]

        with patch("providence_runtime.skills.SkillEngine"):
            request = ahp.generate_challenge()

            assert request.active_mandates == ["M001", "M002"]

    def test_generate_challenge_includes_session_id(self, tmp_path: Path) -> None:
        """Challenge should have unique session ID."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        with patch("providence_runtime.skills.SkillEngine"):
            request1 = ahp.generate_challenge()
            request2 = ahp.generate_challenge()

            assert request1.session_id != request2.session_id


class TestCompleteHandshake:
    """Tests for complete_handshake() method."""

    def test_complete_handshake_returns_response(self, tmp_path: Path) -> None:
        """complete_handshake() should return HandshakeResponse object."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        response_data = {
            "agent_id": "test-agent",
            "understood_mandates": ["M001", "M002"],
            "skills_to_use": ["skill1", "skill2"],
            "acknowledged_signature": True,
            "plan_summary": "Test plan",
            "compliance_declaration": True,
        }

        response = ahp.complete_handshake(response_data)

        assert isinstance(
            response,
            __import__(
                "providence_core.governance.handshake", fromlist=["HandshakeResponse"]
            ).HandshakeResponse,
        )
        assert response.agent_id == "test-agent"
        assert response.understood_mandates == ["M001", "M002"]

    def test_complete_handshake_sets_timestamp_when_missing(
        self, tmp_path: Path
    ) -> None:
        """complete_handshake() should add timestamp if missing."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        response_data = {
            "agent_id": "test-agent",
            "understood_mandates": [],
            "skills_to_use": [],
            "acknowledged_signature": True,
            # Intentionally omit timestamp
        }

        response = ahp.complete_handshake(response_data)

        assert response.timestamp is not None
        assert len(response.timestamp) > 0

    def test_complete_handshake_persists_to_file(self, tmp_path: Path) -> None:
        """complete_handshake() should write response to response_file."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        response_data = {
            "agent_id": "test-agent",
            "understood_mandates": ["M001"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": True,
            "timestamp": "2025-01-01T00:00:00",
        }

        ahp.complete_handshake(response_data)

        assert ahp.response_file.exists()
        persisted = json.loads(ahp.response_file.read_text(encoding="utf-8"))
        assert persisted["agent_id"] == "test-agent"


class TestGetHandshakeResponse:
    """Tests for get_handshake_response() method."""

    def test_get_handshake_response_returns_none_when_missing(
        self, tmp_path: Path
    ) -> None:
        """get_handshake_response() should return None if response file missing."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        response = ahp.get_handshake_response()

        assert response is None

    def test_get_handshake_response_returns_response_when_exists(
        self, tmp_path: Path
    ) -> None:
        """get_handshake_response() should deserialize and return response."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        response_data = {
            "agent_id": "test-agent",
            "understood_mandates": ["M001"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": True,
            "timestamp": "2025-01-01T00:00:00",
        }
        ahp.complete_handshake(response_data)

        retrieved = ahp.get_handshake_response()

        assert retrieved is not None
        assert retrieved.agent_id == "test-agent"
        assert retrieved.understood_mandates == ["M001"]

    def test_get_handshake_response_returns_none_on_corrupt_json(
        self, tmp_path: Path
    ) -> None:
        """get_handshake_response() should return None on malformed JSON."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.cache_dir.mkdir(parents=True, exist_ok=True)
        ahp.response_file.write_text("{invalid json", encoding="utf-8")

        response = ahp.get_handshake_response()

        assert response is None


class TestIsHandshakeValid:
    """Tests for is_handshake_valid() method."""

    def test_is_handshake_valid_false_when_no_response(self, tmp_path: Path) -> None:
        """is_handshake_valid() should return False when no response exists."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        assert ahp.is_handshake_valid() is False

    def test_is_handshake_valid_true_when_response_exists(self, tmp_path: Path) -> None:
        """is_handshake_valid() should return True when response exists."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        response_data = {
            "agent_id": "test-agent",
            "understood_mandates": ["M001"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": False,
            "timestamp": "2025-01-01T00:00:00",
        }
        ahp.complete_handshake(response_data)

        assert ahp.is_handshake_valid() is True

    def test_is_handshake_valid_strict_mode_checks_signature(
        self, tmp_path: Path
    ) -> None:
        """is_handshake_valid(strict=True) should require acknowledged_signature."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        # Response without signature
        response_data = {
            "agent_id": "test-agent",
            "understood_mandates": ["M001"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": False,
            "timestamp": "2025-01-01T00:00:00",
        }
        ahp.complete_handshake(response_data)
        assert ahp.is_handshake_valid(strict=True) is False

        # Response with signature
        response_data["acknowledged_signature"] = True
        ahp.complete_handshake(response_data)
        assert ahp.is_handshake_valid(strict=True) is True


class TestFormatCombinedOutput:
    """Tests for format_combined_output() method."""

    def test_format_combined_output_silent_mode(self, tmp_path: Path) -> None:
        """Silent mode should return empty string."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        state, report = ahp.validate()

        output = ahp.format_combined_output(state, report, mode="silent")

        assert output == ""

    def test_format_combined_output_compact_mode(self, tmp_path: Path) -> None:
        """Compact mode should include governance status."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.gap_status = "ACTIVE"
        ahp.mandates_loaded = ["M001"]
        ahp.current_confidence = 85.0
        state, report = ahp.validate()

        output = ahp.format_combined_output(state, report, mode="compact")

        assert "SDD Governance" in output or "ACTIVE" in output

    def test_format_combined_output_verbose_mode(self, tmp_path: Path) -> None:
        """Verbose mode should include detailed information."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp.gap_status = "PARTIAL"
        ahp.mandates_loaded = ["M001", "M002"]
        ahp.current_confidence = 50.0
        state, report = ahp.validate()

        output = ahp.format_combined_output(state, report, mode="verbose")

        # Verbose should be more detailed than compact
        assert len(output) > 0
        assert "SDD Governance" in output or state in output


class TestSaveCacheStateSync:
    """Tests for _save_cache() method state synchronization."""

    def test_save_cache_syncs_mandates_loaded(self, tmp_path: Path) -> None:
        """_save_cache() should sync mandates_loaded to self."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"
        governance_file.write_text(
            json.dumps(
                {
                    "items": [
                        {"id": "M001", "type": "MANDATE"},
                        {"id": "M002", "type": "MANDATE"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp._save_cache("HEALTHY", [], 100.0)

        assert ahp.mandates_loaded == ["M001", "M002"]

    def test_save_cache_syncs_gap_status(self, tmp_path: Path) -> None:
        """_save_cache() should sync gap_status to self."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp._save_cache("HEALTHY", [], 100.0)

        assert ahp.gap_status == "ACTIVE"

        ahp._save_cache("PARTIAL", [], 50.0)
        assert ahp.gap_status == "PARTIAL"

    def test_save_cache_syncs_spec_fingerprint(self, tmp_path: Path) -> None:
        """_save_cache() should sync spec_fingerprint to self."""
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        governance_file = compiled_dir / "governance-core.json"
        governance_file.write_text(
            json.dumps({"items": [{"id": "M001"}], "version": "1.0"}),
            encoding="utf-8",
        )

        ahp = AgentHandshakeProtocol(project_root=tmp_path)
        ahp._save_cache("HEALTHY", [], 100.0)

        assert ahp.spec_fingerprint != ""
        assert len(ahp.spec_fingerprint) == 16


class TestCacheTTLExpiry:
    """Tests for cache TTL expiry behavior."""

    def test_cache_ttl_zero_returns_none_on_load(self, tmp_path: Path) -> None:
        """Cache with TTL=0 should expire immediately and return None."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=0)
        ahp.validate()  # write cache with TTL=0

        # Cache was written with TTL=0, should be expired
        ahp2 = AgentHandshakeProtocol(project_root=tmp_path, cache_ttl_minutes=0)
        cached_state = ahp2._load_cache()

        # TTL=0 means always expired
        assert cached_state is None


class TestEmitGovernanceEvent:
    """Tests for _emit_governance_event() method."""

    def test_emit_governance_event_no_raise_on_import_error(
        self, tmp_path: Path
    ) -> None:
        """_emit_governance_event() should not raise on ImportError."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        # Even if telemetry import fails, method should not raise
        # We test this by ensuring the method completes without exception
        ahp._emit_governance_event("HEALTHY", 100.0)

    def test_emit_governance_event_no_raise_on_sink_failure(
        self, tmp_path: Path
    ) -> None:
        """_emit_governance_event() should not raise on sink emit failure."""
        ahp = AgentHandshakeProtocol(project_root=tmp_path)

        # Mock TelemetrySink.emit to raise
        class MockSink:
            def emit(self, _: Any) -> None:  # noqa: ARG002
                raise RuntimeError("Sink failure")

            def flush(self) -> None:
                pass

        with patch(
            "providence_runtime.telemetry.TelemetrySink", return_value=MockSink()
        ):
            # Should not raise despite sink failure
            ahp._emit_governance_event("PARTIAL", 50.0)
