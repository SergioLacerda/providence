"""Tests for skills_registry service  workspace root resolution fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestGetWorkspaceRoot:
    def test_returns_cwd_when_find_workspace_root_raises(self, tmp_path) -> None:
        from providence_cli.services.skills_registry import _get_workspace_root

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                side_effect=Exception("env lookup failed"),
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            result = _get_workspace_root()

        assert result == tmp_path

    def test_returns_found_root_when_available(self, tmp_path) -> None:
        from providence_cli.services.skills_registry import _get_workspace_root

        with patch(
            "providence_core.utils.environment.find_workspace_root",
            return_value=tmp_path,
        ):
            result = _get_workspace_root()

        assert result == tmp_path

    def test_returns_cwd_when_find_workspace_root_returns_none(self, tmp_path) -> None:
        from providence_cli.services.skills_registry import _get_workspace_root

        with (
            patch(
                "providence_core.utils.environment.find_workspace_root",
                return_value=None,
            ),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            result = _get_workspace_root()

        assert result == tmp_path


class TestSkillsRegistryAPI:
    def _mock_engine(self, tmp_path: Path) -> MagicMock:
        engine = MagicMock()
        engine.list_skills.return_value = []
        engine.get_skill.return_value = None
        engine.export_skills_payload.return_value = {"skills": []}
        return engine

    def test_list_skills_delegates_to_engine(self, tmp_path) -> None:
        from providence_cli.services.skills_registry import list_skills

        mock_engine = self._mock_engine(tmp_path)
        with (
            patch(
                "providence_cli.services.skills_registry._get_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.skills_registry.SkillEngine",
                return_value=mock_engine,
            ),
        ):
            result = list_skills()

        mock_engine.list_skills.assert_called_once()
        assert result == []

    def test_get_skill_delegates_to_engine(self, tmp_path) -> None:
        from providence_cli.services.skills_registry import get_skill

        mock_engine = self._mock_engine(tmp_path)
        with (
            patch(
                "providence_cli.services.skills_registry._get_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.skills_registry.SkillEngine",
                return_value=mock_engine,
            ),
        ):
            result = get_skill("sdd-diagnose")

        mock_engine.get_skill.assert_called_once_with("sdd-diagnose")
        assert result is None

    def test_export_skills_payload_delegates_to_engine(self, tmp_path) -> None:
        from providence_cli.services.skills_registry import export_skills_payload

        mock_engine = self._mock_engine(tmp_path)
        with (
            patch(
                "providence_cli.services.skills_registry._get_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.services.skills_registry.SkillEngine",
                return_value=mock_engine,
            ),
        ):
            result = export_skills_payload("json")

        mock_engine.export_skills_payload.assert_called_once_with("json")
        assert result == {"skills": []}
