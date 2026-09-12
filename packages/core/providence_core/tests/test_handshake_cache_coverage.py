"""Extended test coverage for handshake_cache.py edge cases and error paths."""

import configparser
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from providence_core.governance.handshake_cache import (
    HandshakeCache,
)


class TestLoadCache:
    """Test cache loading with various error conditions."""

    def test_load_cache_returns_none_on_invalid_json(self, tmp_path):
        """Verify load_cache returns None when cache file contains invalid JSON."""
        cache_dir = tmp_path / ".providence" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"
        cache_file.write_text("not valid json", encoding="utf-8")

        cache = HandshakeCache(
            cache_file=cache_file,
            cache_dir=cache_dir,
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.load_cache()

        assert result is None

    def test_load_cache_returns_none_on_expired_ttl(self, tmp_path):
        """Verify load_cache returns None when cache has expired."""
        cache_dir = tmp_path / ".providence" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"

        # Create a cache with a timestamp in the past (beyond TTL)
        past_time = (datetime.now() - timedelta(minutes=60)).isoformat()
        cache_data = {
            "state": "HEALTHY",
            "confidence": 0.95,
            "last_check": past_time,
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        cache = HandshakeCache(
            cache_file=cache_file,
            cache_dir=cache_dir,
            cache_ttl=timedelta(minutes=30),  # TTL is 30 minutes
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.load_cache()

        assert result is None

    def test_load_cache_returns_none_on_bad_timestamp(self, tmp_path):
        """Verify load_cache returns None when last_check timestamp is invalid."""
        cache_dir = tmp_path / ".providence" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"

        cache_data = {
            "state": "HEALTHY",
            "confidence": 0.95,
            "last_check": "invalid-timestamp",
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        cache = HandshakeCache(
            cache_file=cache_file,
            cache_dir=cache_dir,
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.load_cache()

        assert result is None


class TestSaveCache:
    """Test cache saving with various error conditions."""

    def test_save_cache_recovers_from_corrupt_existing_cache(self, tmp_path):
        """Verify save_cache succeeds even when existing cache is corrupted."""
        cache_dir = tmp_path / ".providence" / "runtime"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "governance-state.json"

        # Write corrupt JSON to existing cache file
        cache_file.write_text("{broken json", encoding="utf-8")

        cache = HandshakeCache(
            cache_file=cache_file,
            cache_dir=cache_dir,
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        # This should not raise even though existing cache is corrupt
        cache.save_cache(
            state="HEALTHY", checks=[], confidence=0.95, skill_profile="default"
        )

        # Verify new cache file was written
        assert cache_file.exists()
        saved_data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert saved_data["state"] == "HEALTHY"

    def test_save_cache_silent_on_permission_error(self, tmp_path):
        """Verify save_cache handles permission errors gracefully."""
        cache_dir = tmp_path / ".providence" / "runtime"
        cache_file = cache_dir / "governance-state.json"

        cache = HandshakeCache(
            cache_file=cache_file,
            cache_dir=cache_dir,
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        with patch.object(Path, "mkdir", side_effect=PermissionError("Access denied")):
            # Should not raise
            cache.save_cache(
                state="HEALTHY", checks=[], confidence=0.95, skill_profile="default"
            )


class TestExtractSkillProfile:
    """Test skill profile extraction from canonical .providence/profile."""

    def test_extract_skill_profile_missing_profile(self, tmp_path):
        """Verify extract_skill_profile returns 'default' when .providence/profile is absent."""

        cache = HandshakeCache(
            cache_file=tmp_path / ".providence" / "runtime" / "governance-state.json",
            cache_dir=tmp_path / ".providence" / "runtime",
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.extract_skill_profile()

        assert result == "default"

    def test_extract_skill_profile_invalid_profile_file(self, tmp_path):
        """Verify extract_skill_profile returns 'default' when .providence/profile is invalid."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir(parents=True)
        (sdd_dir / "profile").write_text("not-an-ini", encoding="utf-8")

        cache = HandshakeCache(
            cache_file=tmp_path / ".providence" / "runtime" / "governance-state.json",
            cache_dir=tmp_path / ".providence" / "runtime",
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.extract_skill_profile()

        assert result == "default"

    def test_extract_skill_profile_reads_profile_type(self, tmp_path):
        """Verify extract_skill_profile resolves type from canonical .providence/profile."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir(parents=True)
        (sdd_dir / "profile").write_text("[sdd]\ntype = master\n", encoding="utf-8")

        cache = HandshakeCache(
            cache_file=tmp_path / ".providence" / "runtime" / "governance-state.json",
            cache_dir=tmp_path / ".providence" / "runtime",
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.extract_skill_profile()

        assert result == "master"


class TestResolveTTLMinutes:
    """Test TTL minutes resolution from profile and config."""

    def test_resolve_ttl_master_profile(self, tmp_path):
        """Verify resolve_ttl_minutes returns 480 for master profile."""
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()

        profile_file = sdd_dir / "profile"
        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "master"}
        with open(profile_file, "w", encoding="utf-8") as f:
            parser.write(f)

        cache = HandshakeCache(
            cache_file=tmp_path / ".providence" / "runtime" / "governance-state.json",
            cache_dir=tmp_path / ".providence" / "runtime",
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.resolve_ttl_minutes()

        assert result == 480

    def test_resolve_ttl_corrupt_pyproject(self, tmp_path):
        """Verify resolve_ttl_minutes returns default when pyproject.toml is corrupt."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("{invalid toml", encoding="utf-8")

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        profile_file = sdd_dir / "profile"
        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "client"}
        with open(profile_file, "w", encoding="utf-8") as f:
            parser.write(f)

        cache = HandshakeCache(
            cache_file=tmp_path / ".providence" / "runtime" / "governance-state.json",
            cache_dir=tmp_path / ".providence" / "runtime",
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.resolve_ttl_minutes()

        # Should fall back to client default (30 minutes)
        assert result == 30

    def test_resolve_ttl_from_pyproject_config(self, tmp_path):
        """Verify resolve_ttl_minutes reads from pyproject.toml when available."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.sdd.runtime]\nhandshake_ttl_minutes = 120\n", encoding="utf-8"
        )

        cache = HandshakeCache(
            cache_file=tmp_path / ".providence" / "runtime" / "governance-state.json",
            cache_dir=tmp_path / ".providence" / "runtime",
            cache_ttl=timedelta(minutes=30),
            project_root=tmp_path,
            agent_id="test-agent",
        )

        result = cache.resolve_ttl_minutes()

        assert result == 120
