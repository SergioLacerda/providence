"""Unit tests for ask_context service module."""

from __future__ import annotations

import configparser
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from providence_cli.services.ask_context import get_profile_state
from providence_cli.services.ask_context_drift import (
    check_fingerprint_drift,
    resolve_fingerprint_drift_status,
    write_runtime_cache,
)

pytestmark = pytest.mark.unit


def _write_profile(workspace_root: Path, profile_type: str) -> None:
    sdd_dir = workspace_root / ".providence"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    parser["sdd"] = {"type": profile_type}
    with open(sdd_dir / "profile", "w", encoding="utf-8") as fh:
        parser.write(fh)


class TestGetProfileState:
    def test_reads_profile_type_from_file(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, "client")
        mock_ahp = type(
            "_AHP", (), {"validate": lambda self, **_: ("HEALTHY", object())}
        )()
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            return_value=mock_ahp,
        ):
            profile, state = get_profile_state(tmp_path)
        assert profile == "client"
        assert state == "HEALTHY"

    def test_defaults_to_default_when_no_profile(self, tmp_path: Path) -> None:
        mock_ahp = type(
            "_AHP", (), {"validate": lambda self, **_: ("HEALTHY", object())}
        )()
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            return_value=mock_ahp,
        ):
            profile, state = get_profile_state(tmp_path)
        assert profile == "default"

    def test_returns_unknown_on_exception(self, tmp_path: Path) -> None:
        with patch(
            "providence_core.governance.handshake.AgentHandshakeProtocol",
            side_effect=Exception("boom"),
        ):
            profile, state = get_profile_state(tmp_path)
        assert state == "UNKNOWN"
        assert profile == "default"

    def test_uses_cached_ahp_state(self, tmp_path: Path) -> None:
        _write_profile(tmp_path, "master")
        cached = {"state": "PARTIAL", "valid": True}
        with patch(
            "providence_cli.services.ask_context.get_cached_ahp", return_value=cached
        ):
            profile, state = get_profile_state(tmp_path)
        assert state == "PARTIAL"
        assert profile == "master"


class TestCheckFingerprintDrift:
    def test_no_drift_when_state_file_absent(self, tmp_path: Path) -> None:
        assert check_fingerprint_drift(tmp_path, "abc12345") is False

    def test_no_drift_for_empty_fingerprint(self, tmp_path: Path) -> None:
        assert check_fingerprint_drift(tmp_path, "") is False

    def test_detects_drift(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"last_ask": {"compiled_fingerprint_used": "zzzzzzzz"}}),
            encoding="utf-8",
        )
        assert check_fingerprint_drift(tmp_path, "abc12345") is True

    def test_spec_fingerprint_alone_is_unverifiable_not_drift(
        self, tmp_path: Path
    ) -> None:
        """DRF-02 regression: `spec_fingerprint` (a source-hash domain) must
        never be compared against `loaded_fingerprint` (a compiled-artifact
        domain)  a mismatch there is not evidence of drift, and reporting
        it as one was the exact bug. With no same-domain reference
        (`compiled_fingerprint_used`), the outcome is "unverifiable", which
        `check_fingerprint_drift`'s boolean projects to False."""
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"spec_fingerprint": "zzzzzzzz"}), encoding="utf-8"
        )

        assert check_fingerprint_drift(tmp_path, "abc12345") is False
        assert resolve_fingerprint_drift_status(tmp_path, "abc12345") == "unverifiable"

    def test_no_drift_when_fingerprints_match(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"spec_fingerprint": "abc12345xyz"}), encoding="utf-8"
        )
        assert check_fingerprint_drift(tmp_path, "abc12345") is False

    def test_no_drift_when_no_cached_fingerprint(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({}), encoding="utf-8")
        assert check_fingerprint_drift(tmp_path, "abc12345") is False

    def test_no_drift_when_last_ask_fingerprint_matches(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "spec_fingerprint": "differenthash",
                    "last_ask": {"compiled_fingerprint_used": "abc12345xyz"},
                }
            ),
            encoding="utf-8",
        )
        assert check_fingerprint_drift(tmp_path, "abc12345") is False

    def test_drift_detected_when_last_ask_fingerprint_differs(
        self, tmp_path: Path
    ) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"last_ask": {"compiled_fingerprint_used": "oldoldold"}}),
            encoding="utf-8",
        )
        assert check_fingerprint_drift(tmp_path, "newnewnew") is True

    def test_last_ask_takes_precedence_over_spec_fingerprint(
        self, tmp_path: Path
    ) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "spec_fingerprint": "abc12345xyz",
                    "last_ask": {"compiled_fingerprint_used": "zzzzzzzz"},
                }
            ),
            encoding="utf-8",
        )
        # spec_fingerprint matches but last_ask differs  last_ask wins
        assert check_fingerprint_drift(tmp_path, "abc12345") is True


class TestWriteRuntimeCache:
    def test_creates_state_file(self, tmp_path: Path) -> None:
        write_runtime_cache(
            tmp_path, {"ts": "2026-01-01T00:00:00Z", "context_source": "compiled"}
        )
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["last_ask"]["context_source"] == "compiled"

    def test_preserves_existing_data(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps({"spec_fingerprint": "existing123"}), encoding="utf-8"
        )
        write_runtime_cache(tmp_path, {"ts": "2026-01-01T00:00:00Z"})
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["spec_fingerprint"] == "existing123"
        assert "last_ask" in data

    def test_silently_handles_write_error(self, tmp_path: Path) -> None:
        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            write_runtime_cache(tmp_path, {"ts": "2026-01-01"})
