"""Tests for providence_cli.generators._indices  skill and CLI command indices."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from tests.helpers.text_io import read_text_utf8

from providence_cli.generators._indices import (
    generate_cli_commands_index,
    generate_skill_index,
)


class TestGenerateSkillIndex:
    def test_creates_index_json(self, tmp_path: Path) -> None:
        result = generate_skill_index(str(tmp_path), {})
        index_path = Path(result["index_path"])
        assert index_path.exists()
        assert index_path.name == "skills.index.json"

    def test_index_in_sdd_indices_dir(self, tmp_path: Path) -> None:
        result = generate_skill_index(str(tmp_path), {})
        assert ".providence/indices" in result["index_path"]

    def test_skill_count_and_indexed_skills(self, tmp_path: Path) -> None:
        from providence_runtime.skills import SkillEngine

        result = generate_skill_index(str(tmp_path), {})
        expected = sorted(s.name for s in SkillEngine().list_skills())
        assert result["skill_count"] == len(expected)
        assert sorted(result["indexed_skills"]) == expected

    def test_index_json_contains_expected_fields(self, tmp_path: Path) -> None:
        generate_skill_index(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "indices" / "skills.index.json"
        )
        data = json.loads(content)
        assert data["schema_version"] == "1.0.0"
        assert data["index_type"] == "skills"
        assert "generated_at" in data
        entry = next(s for s in data["skills"] if s["name"] == "sdd-ask")
        assert entry["yaml_path"] == ".providence/skills/sdd-ask/skill.yaml"
        assert isinstance(entry["executable_via_cli"], bool)
        assert isinstance(entry["required_permissions"], list)
        assert isinstance(entry["budget_policy"], dict)

    def test_skills_sorted_by_name(self, tmp_path: Path) -> None:
        generate_skill_index(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "indices" / "skills.index.json"
        )
        data = json.loads(content)
        names = [s["name"] for s in data["skills"]]
        assert names == sorted(names)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = generate_skill_index(str(nested), {})
        assert Path(result["index_path"]).exists()

    def test_import_error_returns_fallback(self, tmp_path: Path) -> None:
        with patch.dict(sys.modules, {"providence_runtime.skills": None}):
            result = generate_skill_index(str(tmp_path), {})
        assert result["index_path"] is None
        assert result["skill_count"] == 0
        assert result["indexed_skills"] == []
        assert "error" in result


class TestGenerateCliCommandsIndex:
    def test_creates_index_json(self, tmp_path: Path) -> None:
        result = generate_cli_commands_index(str(tmp_path), {})
        index_path = Path(result["index_path"])
        assert index_path.exists()
        assert index_path.name == "cli.commands.json"

    def test_index_in_sdd_indices_dir(self, tmp_path: Path) -> None:
        result = generate_cli_commands_index(str(tmp_path), {})
        assert ".providence/indices" in result["index_path"]

    def test_command_count_and_names(self, tmp_path: Path) -> None:
        result = generate_cli_commands_index(str(tmp_path), {})
        assert result["command_count"] > 0
        assert result["command_count"] == len(result["commands"])
        assert "providence ask" in result["commands"]
        assert "providence governance validate" in result["commands"]

    def test_index_json_contains_expected_fields_and_sorted(
        self, tmp_path: Path
    ) -> None:
        generate_cli_commands_index(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "indices" / "cli.commands.json"
        )
        data = json.loads(content)
        assert data["schema_version"] == "1.0.0"
        assert data["index_type"] == "cli_commands"
        assert "generated_at" in data
        assert data["total_commands"] == len(data["commands"])
        names = [c["name"] for c in data["commands"]]
        assert names == sorted(names)
        entry = next(c for c in data["commands"] if c["name"] == "providence ask")
        assert entry["group"] == "governance"
        assert entry["requires_handshake"] is True

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = generate_cli_commands_index(str(nested), {})
        assert Path(result["index_path"]).exists()

    def test_error_returns_fallback(self, tmp_path: Path) -> None:
        with patch(
            "providence_cli.generators._cli_commands_index.Path.mkdir",
            side_effect=OSError("boom"),
        ):
            result = generate_cli_commands_index(str(tmp_path), {})
        assert result["index_path"] is None
        assert result["command_count"] == 0
        assert result["commands"] == []
        assert "boom" in result["error"]
