"""Unit tests for providence_cli.utils.loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_required_files(compiled_dir: Path) -> None:
    """Create all required governance files in compiled_dir."""
    compiled_dir.mkdir(parents=True, exist_ok=True)
    empty = json.dumps({"items": [], "fingerprint": "abc123"})
    (compiled_dir / "governance-core.compiled.msgpack").write_bytes(b"mock_msgpack")
    (compiled_dir / "governance-client-template.compiled.msgpack").write_bytes(
        b"mock_msgpack"
    )
    (compiled_dir / "metadata-core.json").write_text(empty, encoding="utf-8")
    (compiled_dir / "metadata-client-template.json").write_text(empty, encoding="utf-8")


class TestRequiredFiles:
    def test_all_four_files_in_list(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _required_files

        result = _required_files(tmp_path)
        assert len(result) == 4
        names = [f.name for f in result]
        assert "governance-core.compiled.msgpack" in names
        assert "governance-client-template.compiled.msgpack" in names
        assert "metadata-core.json" in names
        assert "metadata-client-template.json" in names


class TestAllExist:
    def test_returns_true_when_all_files_exist(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _all_exist

        files = [tmp_path / "a.txt", tmp_path / "b.txt"]
        for f in files:
            f.write_text("x", encoding="utf-8")
        assert _all_exist(files) is True

    def test_returns_false_when_any_file_missing(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _all_exist

        files = [tmp_path / "a.txt", tmp_path / "missing.txt"]
        (tmp_path / "a.txt").write_text("x", encoding="utf-8")
        assert _all_exist(files) is False

    def test_returns_true_for_empty_list(self) -> None:
        from providence_cli.utils.loader import _all_exist

        assert _all_exist([]) is True


class TestResolveCompiledDir:
    def test_returns_none_when_no_valid_path(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = _resolve_compiled_dir(str(tmp_path / "nonexistent"))
        assert result is None

    def test_returns_direct_path_when_files_present(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        _make_required_files(tmp_path)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = _resolve_compiled_dir(str(tmp_path))
        assert result == tmp_path

    def test_finds_compiled_subdir(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        compiled_subdir = tmp_path / "compiled"
        _make_required_files(compiled_subdir)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = _resolve_compiled_dir(str(tmp_path))
        assert result == compiled_subdir

    def test_finds_sdd_compiled_subdir(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        sdd_compiled = tmp_path / ".providence" / "compiled"
        _make_required_files(sdd_compiled)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = _resolve_compiled_dir(str(tmp_path))
        assert result == sdd_compiled

    def test_rejects_sdd_base_dir_without_compiled_subdir(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        sdd_dir = tmp_path / ".providence"
        _make_required_files(sdd_dir)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = _resolve_compiled_dir(str(tmp_path))
        assert result is None

    def test_does_not_fallback_to_canonical_client_compiled(
        self, tmp_path: Path
    ) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        canonical = tmp_path / "client_compiled"
        _make_required_files(canonical)
        result = _resolve_compiled_dir(str(tmp_path / "no_path"))
        assert result is None

    def test_does_not_fallback_to_canonical_master_compiled(
        self, tmp_path: Path
    ) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        canonical = tmp_path / "master_compiled"
        _make_required_files(canonical)
        result = _resolve_compiled_dir(str(tmp_path / "no_path"))
        assert result is None

    def test_rejects_legacy_generated_path_even_when_files_exist(
        self, tmp_path: Path
    ) -> None:
        from providence_cli.utils.loader import _resolve_compiled_dir

        legacy = tmp_path / "generated" / "master" / "compiled"
        _make_required_files(legacy)
        result = _resolve_compiled_dir(str(tmp_path))
        assert result is None


class TestValidateGovernancePath:
    def test_returns_false_for_invalid_path(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import validate_governance_path

        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = validate_governance_path(str(tmp_path / "nonexistent"))
        assert result is False

    def test_returns_true_for_valid_path(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import validate_governance_path

        _make_required_files(tmp_path)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with patch(
            "providence_core.utils.environment.get_sdd_paths", return_value=mock_paths
        ):
            result = validate_governance_path(str(tmp_path))
        assert result is True


class TestLoadGovernanceConfig:
    def test_raises_value_error_when_path_invalid(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import load_governance_config

        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        with (
            patch(
                "providence_core.utils.environment.get_sdd_paths",
                return_value=mock_paths,
            ),
            pytest.raises(ValueError, match="Invalid governance path"),
        ):
            load_governance_config(str(tmp_path / "nonexistent"))

    def test_raises_value_error_when_loader_fails(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import load_governance_config

        _make_required_files(tmp_path)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        mock_loader = MagicMock()
        mock_loader.load_all.side_effect = RuntimeError("load failed")

        with (
            patch(
                "providence_core.utils.environment.get_sdd_paths",
                return_value=mock_paths,
            ),
            patch(
                "providence_core.utils.loader.GovernanceLoader",
                return_value=mock_loader,
            ),
            pytest.raises(ValueError, match="Failed to load governance config"),
        ):
            load_governance_config(str(tmp_path))

    def test_returns_config_dict_when_loader_succeeds(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import load_governance_config

        _make_required_files(tmp_path)
        mock_paths: dict[str, Any] = {
            "client_compiled": tmp_path / "no_client",
            "master_compiled": tmp_path / "no_master",
            "client_build": tmp_path / "no_build",
        }
        mock_loader = MagicMock()
        mock_loader.load_all.return_value = {
            "core_fingerprint": "fp1",
            "client_fingerprint": "fp2",
        }
        mock_loader.packages_data = {"items": [{"id": "M001"}]}
        mock_loader._client_data = {"items": []}

        with (
            patch(
                "providence_core.utils.environment.get_sdd_paths",
                return_value=mock_paths,
            ),
            patch(
                "providence_core.utils.loader.GovernanceLoader",
                return_value=mock_loader,
            ),
        ):
            result = load_governance_config(str(tmp_path))

        assert "items" in result
        assert "core_items_count" in result
        assert "client_items_count" in result


class TestGetGovernanceSummary:
    def test_returns_summary_dict(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import get_governance_summary

        config = {
            "core_fingerprint": "abcdef1234567890",
            "client_fingerprint": "fedcba9876543210",
            "items": [{"id": "M001"}],
            "core_items_count": 1,
            "client_items_count": 0,
        }
        result = get_governance_summary(str(tmp_path), config)
        assert "Status" in result
        assert result["Status"] == "Ready"
        assert "Core Items" in result
        assert result["Core Items"] == 1

    def test_calls_load_governance_config_when_no_config(self, tmp_path: Path) -> None:
        from providence_cli.utils.loader import get_governance_summary

        mock_config = {
            "core_fingerprint": "abc123def456789012",
            "client_fingerprint": "xyz987uvw654321098",
            "items": [],
            "core_items_count": 0,
            "client_items_count": 0,
        }
        with patch(
            "providence_cli.utils.loader.load_governance_config",
            return_value=mock_config,
        ) as mock_load:
            result = get_governance_summary(str(tmp_path))
            mock_load.assert_called_once_with(str(tmp_path))
        assert "Status" in result
