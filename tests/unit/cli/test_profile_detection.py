"""Tests for SDD profile detection and precedence resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_sdd_profile_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure SDD_PROFILE env var does not leak between tests."""
    monkeypatch.delenv("SDD_PROFILE", raising=False)
    return


class TestDetectProfile:
    def test_defaults_to_client_when_no_markers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bare workspace with no markers resolves to 'client'."""
        from providence_core.utils.environment import detect_profile

        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_detects_master_from_sdd_profile(self, tmp_path: Path) -> None:
        """Presence of .providence/profile with type=master triggers master profile."""
        from providence_core.utils.environment import detect_profile

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text(
            "[sdd]\nversion = 1\ntype = master\nname = test\nworkspace_id = abc\ncore_hash =\n",
            encoding="utf-8",
        )
        result = detect_profile(root=tmp_path)
        assert result == "master"

    def test_env_var_overrides_filesystem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SDD_PROFILE env var takes highest priority."""
        from providence_core.utils.environment import detect_profile

        # .providence/profile says master
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text(
            "[sdd]\nversion = 1\ntype = master\nname = test\nworkspace_id = abc\ncore_hash =\n",
            encoding="utf-8",
        )
        # Env says client
        monkeypatch.setenv("SDD_PROFILE", "client")

        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_env_var_master_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SDD_PROFILE=master overrides even when workspace lacks markers."""
        from providence_core.utils.environment import detect_profile

        monkeypatch.setenv("SDD_PROFILE", "master")
        result = detect_profile(root=tmp_path)
        assert result == "master"

    def test_sdd_profile_client_explicit(self, tmp_path: Path) -> None:
        """.providence/profile with type=client is respected."""
        from providence_core.utils.environment import detect_profile

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text(
            "[sdd]\nversion = 1\ntype = client\nname = test\nworkspace_id = abc\ncore_hash =\n",
            encoding="utf-8",
        )

        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_sdd_profile_master_explicit(self, tmp_path: Path) -> None:
        """Explicit master in .providence/profile is respected."""
        from providence_core.utils.environment import detect_profile

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text(
            "[sdd]\nversion = 1\ntype = master\nname = test\nworkspace_id = abc\ncore_hash =\n",
            encoding="utf-8",
        )
        result = detect_profile(root=tmp_path)
        assert result == "master"

    def test_sdd_profile_invalid_type_falls_through(self, tmp_path: Path) -> None:
        """Invalid type in .providence/profile causes fallback to client via WorkspaceNotInitializedError."""
        from providence_core.utils.environment import detect_profile

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text(
            "[sdd]\nversion = 1\ntype = unknown_value\n", encoding="utf-8"
        )
        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_env_var_invalid_value_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid SDD_PROFILE env var falls through to lower priority sources."""
        from providence_core.utils.environment import detect_profile

        monkeypatch.setenv("SDD_PROFILE", "invalid")
        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_resolution_priority_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify full priority chain: env > filesystem > fallback."""
        from providence_core.utils.environment import detect_profile

        # Filesystem (.providence/profile) -> master
        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir()
        (sdd_dir / "profile").write_text(
            "[sdd]\nversion = 1\ntype = master\nname = test\nworkspace_id = abc\ncore_hash =\n",
            encoding="utf-8",
        )

        # Without env: filesystem wins over fallback
        assert detect_profile(root=tmp_path) == "master"

        # With env: env wins over all
        monkeypatch.setenv("SDD_PROFILE", "client")
        assert detect_profile(root=tmp_path) == "client"


class TestGetProfileContext:
    def test_returns_dict_with_required_keys(self, tmp_path: Path) -> None:
        from providence_core.utils.environment import get_profile_context

        ctx = get_profile_context(profile="client")
        assert "profile" in ctx
        assert "is_master" in ctx
        assert "is_client" in ctx
        assert "paths" in ctx

    def test_master_flags(self) -> None:
        from providence_core.utils.environment import get_profile_context

        ctx = get_profile_context(profile="master")
        assert ctx["profile"] == "master"
        assert ctx["is_master"] is True
        assert ctx["is_client"] is False

    def test_client_flags(self) -> None:
        from providence_core.utils.environment import get_profile_context

        ctx = get_profile_context(profile="client")
        assert ctx["profile"] == "client"
        assert ctx["is_master"] is False
        assert ctx["is_client"] is True


class TestProfilePolicy:
    def test_release_blocked_in_client(self) -> None:
        from providence_cli.utils.profile import get_adapter

        adapter = get_adapter("client")
        assert "release" in adapter.blocked_commands

    def test_release_allowed_in_master(self) -> None:
        from providence_cli.utils.profile import get_adapter

        adapter = get_adapter("master")
        assert "release" in adapter.allowed_commands
        assert "release" not in adapter.blocked_commands

    def test_wizard_warns_in_master(self) -> None:
        from providence_cli.utils.profile import get_adapter

        adapter = get_adapter("master")
        assert "wizard" in adapter.warned_commands

    def test_wizard_allowed_in_client(self) -> None:
        from providence_cli.utils.profile import get_adapter

        adapter = get_adapter("client")
        assert "wizard" in adapter.allowed_commands
        assert "wizard" not in adapter.warned_commands

    def test_unknown_profile_falls_back_to_client(self) -> None:
        from providence_cli.utils.profile import get_adapter

        adapter = get_adapter("unknown_profile")
        assert adapter.profile == "client"

    def test_enforce_blocks_and_raises_exit(self) -> None:
        import unittest.mock as mock

        import click

        from providence_cli.utils.profile import enforce_profile_policy

        with (
            mock.patch(
                "providence_core.utils.environment.detect_profile",
                return_value="client",
            ),
            pytest.raises((SystemExit, click.exceptions.Exit)),
        ):
            enforce_profile_policy("release", ctx=None)

    def test_enforce_warns_but_does_not_exit(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import unittest.mock as mock

        from providence_cli.utils.profile import enforce_profile_policy

        with mock.patch(
            "providence_core.utils.environment.detect_profile", return_value="master"
        ):
            enforce_profile_policy("wizard", ctx=None)  # should not raise

        captured = capsys.readouterr()
        assert "WARN" in captured.out
        assert "wizard" in captured.out
