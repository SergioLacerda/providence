"""Tests for HandshakeChallenge module (M015 bidirectional protocol)."""

import json
from unittest.mock import patch

from providence_core.governance.handshake_challenge import HandshakeChallenge
from providence_core.governance.handshake_models import HandshakeRequest


class TestGenerateChallenge:
    """Test HandshakeChallenge.generate_challenge() method."""

    def test_generate_challenge_returns_handshake_request(self, tmp_path):
        """Verify generate_challenge returns a HandshakeRequest object."""
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        request = challenge.generate_challenge(
            task_description="Test Task",
            task_type="test",
            mandates_loaded=["mandate1", "mandate2"],
        )

        assert isinstance(request, HandshakeRequest)
        assert request.session_id.startswith("sess_")
        assert request.challenge_id.startswith("chal_")
        assert request.task["description"] == "Test Task"
        assert request.task["type"] == "test"
        assert request.active_mandates == ["mandate1", "mandate2"]

    def test_generate_challenge_reports_unknown_budget_when_unconfigured(
        self, tmp_path
    ):
        """SEC-06: without a configured ceiling, the challenge must report
        'unknown', not a fabricated placeholder limit."""
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        request = challenge.generate_challenge()

        assert request.budget == {
            "remaining_tokens": "unknown",
            "remaining_usd": "unknown",
        }

    def test_generate_challenge_reports_configured_budget(self, tmp_path):
        """SEC-06: a real ceiling configured via pyproject.toml is used
        instead of the 'unknown' default."""
        (tmp_path / "pyproject.toml").write_text(
            "[tool.sdd.runtime]\n"
            "max_tokens_per_session = 50000\n"
            "max_cost_usd_per_session = 2.5\n",
            encoding="utf-8",
        )
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        request = challenge.generate_challenge()

        assert request.budget == {"remaining_tokens": 50000, "remaining_usd": 2.5}

    def test_generate_challenge_includes_signature_status(self, tmp_path, monkeypatch):
        """Verify generate_challenge includes signature_status field."""
        monkeypatch.delenv("SDD_SIGNATURE_MODE", raising=False)
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        request = challenge.generate_challenge()

        assert hasattr(request, "signature_status")
        assert request.signature_status == "unavailable"

    def test_generate_challenge_skill_engine_import_failure_non_fatal(self, tmp_path):
        """Verify generate_challenge handles missing SkillEngine gracefully."""
        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        with patch(
            "providence_runtime.skills.SkillEngine",
            side_effect=ImportError("No module"),
        ):
            request = challenge.generate_challenge()

        assert isinstance(request, HandshakeRequest)
        assert request.available_skills == []  # Empty when SkillEngine fails


class TestCompleteHandshake:
    """Test HandshakeChallenge.complete_handshake() method."""

    def test_complete_handshake_writes_response_file(self, tmp_path):
        """Verify complete_handshake persists response to file."""
        cache_dir = tmp_path / ".providence" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        response_data = {
            "agent_id": "claude-agent",
            "understood_mandates": ["m1", "m2"],
            "skills_to_use": ["skill1"],
            "acknowledged_signature": True,
        }
        challenge.complete_handshake(response_data)

        assert response_file.exists()
        written_data = json.loads(response_file.read_text(encoding="utf-8"))
        assert written_data["agent_id"] == "claude-agent"
        assert written_data["skills_to_use"] == ["skill1"]

    def test_complete_handshake_fills_missing_timestamp(self, tmp_path):
        """Verify complete_handshake adds timestamp if missing."""
        cache_dir = tmp_path / ".providence" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        response_data = {
            "agent_id": "claude-agent",
            "understood_mandates": [],
            "skills_to_use": [],
            "acknowledged_signature": False,
            "timestamp": "",
        }

        result = challenge.complete_handshake(response_data)

        assert result.timestamp != ""
        written_data = json.loads(response_file.read_text(encoding="utf-8"))
        assert written_data["timestamp"] != ""


class TestHandshakeResponse:
    """Test HandshakeChallenge.get_handshake_response() and is_handshake_valid()."""

    def test_get_handshake_response_returns_none_when_missing(self, tmp_path):
        """Verify get_handshake_response returns None when response file doesn't exist."""
        cache_dir = tmp_path / ".providence" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        result = challenge.get_handshake_response()

        assert result is None

    def test_is_handshake_valid_returns_false_when_missing(self, tmp_path):
        """Verify is_handshake_valid returns False when response file doesn't exist."""
        cache_dir = tmp_path / ".providence" / "runtime"
        response_file = cache_dir / "response.json"

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=cache_dir,
            response_file=response_file,
        )

        result = challenge.is_handshake_valid()

        assert result is False


class TestSignatureStatus:
    """Test HandshakeChallenge._resolve_signature_status() method.

    Regression coverage for SEC-05: a `.sig` file existing next to the
    artifact must NOT be enough to report "verified" — the method must
    reuse the real Ed25519 + trusted-keyring check
    (`providence_runtime.signatures.validate_artifact_signature`). See
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` SEC-05.
    """

    @staticmethod
    def _valid_sig_payload(artifact_name: str, payload_hash: str) -> dict:
        return {
            "schema_version": "1.0",
            "algorithm": "ed25519",
            "key_id": "key-1",
            "artifact_name": artifact_name,
            "profile": "master",
            "payload_hash": payload_hash,
            "signature": "c2ln",  # base64("sig")
            "signed_at": "2026-01-01T00:00:00Z",
        }

    def test_signature_status_returns_unavailable_when_no_env_var(
        self, tmp_path, monkeypatch
    ):
        """Verify status is 'unavailable' when SDD_SIGNATURE_MODE not set."""
        monkeypatch.delenv("SDD_SIGNATURE_MODE", raising=False)

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        assert challenge._resolve_signature_status() == "unavailable"

    def test_signature_status_returns_unsigned_when_artifact_missing(
        self, tmp_path, monkeypatch
    ):
        """Verify status is 'unsigned' when the governance artifact itself is absent."""
        monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        assert challenge._resolve_signature_status() == "unsigned"

    def test_signature_status_returns_unsigned_when_no_sig_file(
        self, tmp_path, monkeypatch
    ):
        """Verify status is 'unsigned' when the artifact exists but has no `.sig`."""
        monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")

        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True, exist_ok=True)
        (compiled_dir / "governance-core.json").write_text("{}", encoding="utf-8")

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        assert challenge._resolve_signature_status() == "unsigned"

    def test_signature_status_does_not_report_verified_for_fake_sig_content(
        self, tmp_path, monkeypatch
    ):
        """A `.sig` file with arbitrary (non-cryptographic) content must not
        be reported as 'verified' — this is the exact SEC-05 regression: the
        old implementation returned 'verified' purely from file presence."""
        monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")

        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True, exist_ok=True)
        gov_file = compiled_dir / "governance-core.json"
        gov_file.write_text("{}", encoding="utf-8")
        sig_file = gov_file.with_suffix(gov_file.suffix + ".sig")
        sig_file.write_text("signature", encoding="utf-8")

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        status = challenge._resolve_signature_status()

        assert status != "verified"
        assert status == "SIG_PARSE_ERROR"

    def test_signature_status_returns_verified_for_real_valid_signature(
        self, tmp_path, monkeypatch
    ):
        """Verify status is 'verified' only after passing the real Ed25519 +
        trusted-keyring check (mirrors
        `test_signatures.py::test_validate_artifact_signature_success_and_failures`)."""
        import hashlib
        import json

        monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")

        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True, exist_ok=True)
        gov_file = compiled_dir / "governance-core.json"
        gov_file.write_text('{"x":1}', encoding="utf-8")
        payload_hash = hashlib.sha256(gov_file.read_bytes()).hexdigest()
        sig_file = gov_file.with_suffix(gov_file.suffix + ".sig")
        sig_file.write_text(
            json.dumps(self._valid_sig_payload(gov_file.name, payload_hash)),
            encoding="utf-8",
        )

        trust_dir = tmp_path / ".providence" / "trust"
        trust_dir.mkdir(parents=True, exist_ok=True)
        (trust_dir / "trusted-keys.json").write_text(
            json.dumps(
                {
                    "keys": [
                        {
                            "key_id": "key-1",
                            "status": "active",
                            "public_key_pem": "pem",
                            "not_before": "2000-01-01T00:00:00Z",
                            "not_after": "2999-01-01T00:00:00Z",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        challenge = HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

        with patch(
            "providence_runtime.signatures._validate._verify_ed25519_signature",
            return_value=True,
        ):
            assert challenge._resolve_signature_status() == "verified"

        with patch(
            "providence_runtime.signatures._validate._verify_ed25519_signature",
            return_value=False,
        ):
            assert challenge._resolve_signature_status() == "SIG_INVALID"


class TestChallengeResponseBinding:
    """Test response-to-challenge binding (SEC-01/SEC-02/SEC-03/SEC-04).

    A `.sig`-file-adjacent bug class of its own: before this fix, any
    persisted response was accepted as valid regardless of which challenge
    (or workspace, or mandate set, or point in time) it actually answered.
    See `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`
    SEC-01 through SEC-04.
    """

    @staticmethod
    def _make_challenge(tmp_path):
        return HandshakeChallenge(
            agent_id="test-agent",
            project_root=tmp_path,
            cache_dir=tmp_path / ".providence" / "runtime",
            response_file=tmp_path / ".providence" / "runtime" / "response.json",
        )

    def test_response_to_generated_challenge_is_valid(self, tmp_path):
        challenge = self._make_challenge(tmp_path)
        request = challenge.generate_challenge(mandates_loaded=["M001", "M002"])

        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": ["M001", "M002"],
                "skills_to_use": [],
                "acknowledged_signature": False,
            }
        )

        assert challenge.is_handshake_valid() is True
        response = challenge.get_handshake_response()
        assert response.challenge_id == request.challenge_id
        assert response.session_id == request.session_id
        assert response.governance_fingerprint == request.governance_fingerprint
        assert response.expires_at != ""

    def test_response_cannot_forge_binding_fields(self, tmp_path):
        """A caller-supplied challenge_id in response_data must be ignored
        and overwritten from server-side state, not trusted (SEC-01)."""
        challenge = self._make_challenge(tmp_path)
        challenge.generate_challenge(mandates_loaded=[])

        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": [],
                "skills_to_use": [],
                "acknowledged_signature": False,
                "challenge_id": "chal_forged",
                "session_id": "sess_forged",
                "governance_fingerprint": "forged",
            }
        )

        response = challenge.get_handshake_response()
        assert response.challenge_id != "chal_forged"
        assert response.session_id != "sess_forged"
        assert response.governance_fingerprint != "forged"

    def test_response_from_stale_challenge_is_rejected(self, tmp_path):
        """A response bound to an older challenge_id must fail once a new
        challenge has been issued for the same workspace (SEC-01/SEC-04:
        no accidental cross-session authorization reuse)."""
        challenge = self._make_challenge(tmp_path)
        challenge.generate_challenge(mandates_loaded=[])
        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": [],
                "skills_to_use": [],
                "acknowledged_signature": False,
            }
        )
        assert challenge.is_handshake_valid() is True

        # A second challenge is issued (e.g. a new/concurrent session).
        challenge.generate_challenge(mandates_loaded=[])

        assert challenge.is_handshake_valid() is False

    def test_response_missing_required_mandate_is_rejected(self, tmp_path):
        challenge = self._make_challenge(tmp_path)
        challenge.generate_challenge(mandates_loaded=["M001", "M002"])

        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": ["M001"],  # M002 missing
                "skills_to_use": [],
                "acknowledged_signature": False,
            }
        )

        assert challenge.is_handshake_valid() is False

    def test_response_expired_is_rejected(self, tmp_path, monkeypatch):
        challenge = self._make_challenge(tmp_path)
        challenge.generate_challenge(mandates_loaded=[])
        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": [],
                "skills_to_use": [],
                "acknowledged_signature": False,
            }
        )
        assert challenge.is_handshake_valid() is True

        response = challenge.get_handshake_response()
        response.expires_at = "2000-01-01T00:00:00"
        challenge.response_file.write_text(
            json.dumps(response.to_dict(), indent=2), encoding="utf-8"
        )

        assert challenge.is_handshake_valid() is False

    def test_response_invalidated_when_governance_changes(self, tmp_path):
        """Authorization must be invalidated by a live governance-fingerprint
        change, not only by comparison against the value captured at
        issuance (SEC-03)."""
        challenge = self._make_challenge(tmp_path)
        challenge.generate_challenge(mandates_loaded=[])
        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": [],
                "skills_to_use": [],
                "acknowledged_signature": False,
            }
        )
        assert challenge.is_handshake_valid() is True

        with patch.object(
            HandshakeChallenge,
            "_compute_governance_fingerprint",
            return_value="changed-fingerprint",
        ):
            assert challenge.is_handshake_valid() is False

    def test_strict_mode_requires_verified_signature_status_not_just_ack(
        self, tmp_path, monkeypatch
    ):
        """acknowledged_signature=True alone must not satisfy strict mode —
        the challenge's independently-verified signature_status (SEC-05)
        must also read 'verified' (SEC-02)."""
        monkeypatch.setenv(
            "SDD_SIGNATURE_MODE", "off"
        )  # signature_status "unavailable"
        challenge = self._make_challenge(tmp_path)
        challenge.generate_challenge(mandates_loaded=[])
        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": [],
                "skills_to_use": [],
                "acknowledged_signature": True,
            }
        )

        assert challenge.is_handshake_valid(strict=True) is False

    def test_legacy_response_without_challenge_falls_back_to_presence_check(
        self, tmp_path
    ):
        """A response persisted without ever calling generate_challenge()
        (out-of-band, or a workspace predating SEC-01) must keep working —
        backward compatibility is required, not merely nice-to-have."""
        challenge = self._make_challenge(tmp_path)
        challenge.complete_handshake(
            {
                "agent_id": "claude-agent",
                "understood_mandates": [],
                "skills_to_use": [],
                "acknowledged_signature": True,
            }
        )

        assert challenge.is_handshake_valid(strict=True) is True
