"""Tests for providence_cli.generators._skills  generate_skills_registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from tests.helpers.text_io import read_text_utf8

from providence_cli.generators._skills import (
    _generate_skills_documentation,
    generate_skills_registry,
)


class TestGenerateSkillsRegistry:
    def test_creates_registry_json(self, tmp_path: Path) -> None:
        result = generate_skills_registry(str(tmp_path), {})
        registry_path = Path(result["registry_path"])
        assert registry_path.exists()
        assert registry_path.name == "registry.json"

    def test_registry_in_providence_skills_dir(self, tmp_path: Path) -> None:
        result = generate_skills_registry(str(tmp_path), {})
        assert ".providence/skills" in result["registry_path"]

    def test_skill_count_matches_canonical_registry(self, tmp_path: Path) -> None:
        from providence_runtime.skills import _REGISTRY

        result = generate_skills_registry(str(tmp_path), {})
        assert result["skill_count"] == len(_REGISTRY)

    def test_skill_dirs_created(self, tmp_path: Path) -> None:
        result = generate_skills_registry(str(tmp_path), {})
        assert result["skill_dirs"]
        for skill_dir in result["skill_dirs"]:
            assert Path(skill_dir).is_dir()
            assert (Path(skill_dir) / "skill.yaml").exists()

    def test_registry_json_contains_skill_entries(self, tmp_path: Path) -> None:
        generate_skills_registry(str(tmp_path), {})
        content = read_text_utf8(tmp_path / ".providence" / "skills" / "registry.json")
        data = json.loads(content)
        assert data["schema_version"] == "1.1.0"
        assert any(skill["name"] == "sdd-ask" for skill in data["skills"])
        for skill in data["skills"]:
            assert (
                skill["skill_yaml"] == f".providence/skills/{skill['name']}/skill.yaml"
            )

    def test_skill_yaml_round_trips(self, tmp_path: Path) -> None:
        generate_skills_registry(str(tmp_path), {})
        ask_yaml = tmp_path / ".providence" / "skills" / "sdd-ask" / "skill.yaml"
        assert ask_yaml.exists()
        content = read_text_utf8(ask_yaml)
        assert "name: sdd-ask" in content

    def test_skills_md_generated(self, tmp_path: Path) -> None:
        generate_skills_registry(str(tmp_path), {})
        skills_md = tmp_path / ".providence" / "skills" / "SKILLS.md"
        assert skills_md.exists()
        content = read_text_utf8(skills_md)
        assert "# SDD Skills Registry" in content
        assert "sdd-ask" in content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = generate_skills_registry(str(nested), {})
        assert Path(result["registry_path"]).exists()

    def test_import_error_returns_fallback(self, tmp_path: Path) -> None:
        with patch.dict(sys.modules, {"providence_runtime._skill_registry": None}):
            result = generate_skills_registry(str(tmp_path), {})
        assert result["registry_path"] is None
        assert result["skill_count"] == 0
        assert result["skill_dirs"] == []
        assert "error" in result

    def test_unknown_skill_kwargs_are_skipped(self, tmp_path: Path) -> None:
        fake_skills = {
            "skills": [
                {
                    "name": "fake-skill",
                    "version": "1.0.0",
                    "category": "general",
                    "description": "Fake",
                    "when_to_use": ["testing"],
                    "outcomes": ["result"],
                    "allowed_tools": ["providence ask"],
                    "cli_fallback": ["providence ask"],
                    "required_permissions": ["workspace-read"],
                    "unexpected_field": "should be ignored",
                }
            ]
        }
        with patch(
            "providence_runtime._skill_registry.SkillRegistry.export_skills_payload",
            return_value=fake_skills,
        ):
            result = generate_skills_registry(str(tmp_path), {})
        assert result["skill_count"] == 1
        fake_yaml = tmp_path / ".providence" / "skills" / "fake-skill" / "skill.yaml"
        assert fake_yaml.exists()

    def test_skill_write_failure_is_skipped(self, tmp_path: Path) -> None:
        fake_skills = {
            "skills": [
                {"name": "broken-skill"},
                {
                    "name": "ok-skill",
                    "version": "1.0.0",
                    "category": "general",
                    "description": "OK",
                    "when_to_use": ["testing"],
                    "outcomes": ["result"],
                    "allowed_tools": ["providence ask"],
                    "cli_fallback": ["providence ask"],
                    "required_permissions": ["workspace-read"],
                },
            ]
        }
        with patch(
            "providence_runtime._skill_registry.SkillRegistry.export_skills_payload",
            return_value=fake_skills,
        ):
            result = generate_skills_registry(str(tmp_path), {})
        # broken-skill is missing required fields for SkillDefinition and is skipped.
        assert "ok-skill" in result["skill_dirs"][-1]
        assert len(result["skill_dirs"]) == 1
        assert result["skill_count"] == 2


class TestGenerateSkillsDocumentation:
    def test_includes_header(self) -> None:
        doc = _generate_skills_documentation([])
        assert "# SDD Skills Registry" in doc
        assert "Using Skills" in doc

    def test_includes_skill_details_sorted_by_name(self) -> None:
        skills = [
            {
                "name": "z-skill",
                "version": "2.0.0",
                "category": "general",
                "description": "Z skill",
                "risk_score": "low",
                "status": "active",
            },
            {
                "name": "a-skill",
                "version": "1.0.0",
                "category": "orchestrator",
                "description": "A skill",
                "risk_score": "controlled",
                "status": "active",
            },
        ]
        doc = _generate_skills_documentation(skills)
        a_index = doc.index("a-skill")
        z_index = doc.index("z-skill")
        assert a_index < z_index
        assert "**Category:** orchestrator" in doc
        assert "**Risk:** controlled" in doc
        assert ".providence/skills/a-skill/skill.yaml" in doc

    def test_handles_missing_fields_with_defaults(self) -> None:
        doc = _generate_skills_documentation([{}])
        assert "`unknown` v?" in doc
        assert "**Category:** general" in doc
        assert "**Risk:** unknown" in doc
        assert "**Status:** unknown" in doc
        assert "No description" in doc
