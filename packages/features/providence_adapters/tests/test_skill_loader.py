"""Tests for SkillLoader."""

import json
from pathlib import Path

import pytest
import yaml

from providence_adapters.skill_loader import SkillLoader, _safe_path


@pytest.fixture
def sdd_dir(tmp_path: Path) -> Path:
    """Create a minimal .providence/ structure for testing."""
    sdd = tmp_path / ".providence"
    skills_dir = sdd / "skills"
    skills_dir.mkdir(parents=True)
    commands_dir = sdd / "commands"
    commands_dir.mkdir(parents=True)

    # Registry
    registry = {
        "schema_version": "1.0.0",
        "skills": [
            {
                "name": "diagnose",
                "version": "1.0.0",
                "category": "analysis",
                "description": "Diagnose workspace problems.",
                "risk_score": "low",
                "status": "active",
                "skill_yaml": ".providence/skills/diagnose/skill.yaml",
            }
        ],
    }
    (skills_dir / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

    # skill.yaml
    skill_yaml_dir = skills_dir / "diagnose"
    skill_yaml_dir.mkdir()
    skill_data = {
        "name": "diagnose",
        "category": "analysis",
        "when_to_use": ["failing checks", "unknown failures"],
        "allowed_tools": ["providence doctor run", "providence runtime status"],
        "cli_fallback": ["providence doctor run"],
        "risk_score": "low",
    }
    (skill_yaml_dir / "skill.yaml").write_text(yaml.dump(skill_data), encoding="utf-8")

    # Commands registry
    cmd_registry = {
        "schema_version": "1.0.0",
        "commands": [
            {
                "id": "diagnose",
                "slash": "/diagnose",
                "routes_to": {"type": "skill", "id": "diagnose"},
                "targets": ["claude", "codex"],
            }
        ],
    }
    (commands_dir / "registry.json").write_text(
        json.dumps(cmd_registry), encoding="utf-8"
    )

    # command.yaml
    cmd_yaml_dir = commands_dir / "diagnose"
    cmd_yaml_dir.mkdir()
    cmd_data = {
        "id": "diagnose",
        "slash": "/diagnose",
        "routes_to": {"type": "skill", "id": "diagnose"},
        "args": [],
    }
    (cmd_yaml_dir / "command.yaml").write_text(yaml.dump(cmd_data), encoding="utf-8")

    return sdd


class TestSkillLoader:
    def test_load_skills_returns_merged_data(self, sdd_dir: Path) -> None:
        loader = SkillLoader()
        skills = loader.load_skills(sdd_dir)

        assert len(skills) == 1
        skill = skills[0]
        assert skill["name"] == "diagnose"
        assert skill["category"] == "analysis"
        assert "allowed_tools" in skill
        assert "providence doctor run" in skill["allowed_tools"]

    def test_load_skills_missing_registry_returns_empty(self, tmp_path: Path) -> None:
        loader = SkillLoader()
        skills = loader.load_skills(tmp_path / ".providence")
        assert skills == []

    def test_load_skills_skips_missing_yaml(self, tmp_path: Path) -> None:
        sdd = tmp_path / ".providence" / "skills"
        sdd.mkdir(parents=True)
        registry = {
            "schema_version": "1.0.0",
            "skills": [{"name": "ghost", "description": "missing yaml"}],
        }
        (sdd / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

        loader = SkillLoader()
        skills = loader.load_skills(tmp_path / ".providence")
        assert skills == []

    def test_load_commands_returns_merged_data(self, sdd_dir: Path) -> None:
        loader = SkillLoader()
        commands = loader.load_commands(sdd_dir)

        assert len(commands) == 1
        cmd = commands[0]
        assert cmd["id"] == "diagnose"
        assert cmd["slash"] == "/diagnose"

    def test_load_commands_missing_registry_returns_empty(self, tmp_path: Path) -> None:
        loader = SkillLoader()
        commands = loader.load_commands(tmp_path / ".providence")
        assert commands == []

    def test_load_commands_skips_missing_yaml(self, tmp_path: Path) -> None:
        commands_dir = tmp_path / ".providence" / "commands"
        commands_dir.mkdir(parents=True)
        registry = {
            "schema_version": "1.0.0",
            "commands": [{"id": "ghost", "slash": "/ghost"}],
        }
        (commands_dir / "registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )

        loader = SkillLoader()
        commands = loader.load_commands(tmp_path / ".providence")
        assert commands == []

    def test_load_skills_reads_skill_md_when_present(self, sdd_dir: Path) -> None:
        skill_dir = sdd_dir / "skills" / "diagnose"
        (skill_dir / "SKILL.md").write_text(
            "# Diagnose\nDetailed docs.", encoding="utf-8"
        )
        loader = SkillLoader()
        skills = loader.load_skills(sdd_dir)
        assert skills[0].get("skill_md") == "# Diagnose\nDetailed docs."

    def test_load_skills_skips_unsafe_yaml_path(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        sdd = tmp_path / ".providence"
        skills_dir = sdd / "skills"
        skills_dir.mkdir(parents=True)
        registry = {"schema_version": "1.0.0", "skills": [{"name": "unsafe"}]}
        (skills_dir / "registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        monkeypatch.setattr(
            "providence_adapters.skill_loader._safe_path", lambda *_args: None
        )

        loader = SkillLoader()
        assert loader.load_skills(sdd) == []

    def test_load_commands_skips_unsafe_yaml_path(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        sdd = tmp_path / ".providence"
        commands_dir = sdd / "commands"
        commands_dir.mkdir(parents=True)
        registry = {"schema_version": "1.0.0", "commands": [{"id": "unsafe"}]}
        (commands_dir / "registry.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        monkeypatch.setattr(
            "providence_adapters.skill_loader._safe_path", lambda *_args: None
        )

        loader = SkillLoader()
        assert loader.load_commands(sdd) == []


class TestSafePath:
    def test_path_outside_root_returns_none(self, tmp_path: Path) -> None:
        outside = Path("/etc/passwd")
        assert _safe_path(outside, tmp_path) is None

    def test_sensitive_path_returns_none(self, tmp_path: Path) -> None:
        sensitive = tmp_path / ".ssh" / "id_rsa"
        assert _safe_path(sensitive, tmp_path) is None

    def test_safe_path_within_root_returns_resolved(self, tmp_path: Path) -> None:
        candidate = tmp_path / "skills" / "diagnose" / "skill.yaml"
        resolved = _safe_path(candidate, tmp_path)
        assert resolved == candidate.resolve()

    def test_safe_path_returns_none_on_resolve_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        candidate = tmp_path / "skills" / "diagnose" / "skill.yaml"

        def _boom() -> Path:
            raise OSError("bad path")

        monkeypatch.setattr(Path, "resolve", lambda self: _boom())  # type: ignore[method-assign]
        assert _safe_path(candidate, tmp_path) is None
