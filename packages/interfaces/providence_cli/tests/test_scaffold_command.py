"""Tests for providence_cli.commands.scaffold  skill and command scaffold coverage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from providence_cli.commands.scaffold import _render
from providence_cli.commands.scaffold_registry import _append_to_registry
from providence_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


def _make_skill_templates(ws_root: Path) -> None:
    tpl_dir = ws_root / ".providence" / "templates" / "skill"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "skill.yaml.tpl").write_text(
        "name: {{ name }}\ncategory: {{ category }}\n", encoding="utf-8"
    )
    (tpl_dir / "SKILL.md.tpl").write_text(
        "# {{ name }}\n{{ description }}\n", encoding="utf-8"
    )


def _make_command_templates(ws_root: Path) -> None:
    tpl_dir = ws_root / ".providence" / "templates" / "command"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "command.yaml.tpl").write_text(
        "name: {{ name }}\nskill_id: {{ skill_id }}\n", encoding="utf-8"
    )


class TestAppendToRegistry:
    def test_creates_registry_when_not_exists(self, tmp_path: Path) -> None:
        registry = tmp_path / "registry.json"
        _append_to_registry(registry, {"name": "my-skill"})
        data = json.loads(registry.read_text(encoding="utf-8"))
        # New registry defaults to 'commands' key (no 'skills' key in empty dict)
        all_items = data.get("skills", data.get("commands", []))
        assert any(i.get("name") == "my-skill" for i in all_items)

    def test_appends_to_existing_registry(self, tmp_path: Path) -> None:
        registry = tmp_path / "registry.json"
        registry.write_text(
            json.dumps({"commands": [{"id": "cmd-a", "name": "existing"}]}),
            encoding="utf-8",
        )
        _append_to_registry(registry, {"id": "cmd-b", "name": "new-cmd"})
        data = json.loads(registry.read_text(encoding="utf-8"))
        ids = [i["id"] for i in data["commands"]]
        assert "cmd-a" in ids
        assert "cmd-b" in ids

    def test_deduplicates_by_name(self, tmp_path: Path) -> None:
        registry = tmp_path / "registry.json"
        registry.write_text(
            json.dumps({"skills": [{"name": "dupe"}]}), encoding="utf-8"
        )
        _append_to_registry(registry, {"name": "dupe"})
        data = json.loads(registry.read_text(encoding="utf-8"))
        assert len(data["skills"]) == 1

    def test_deduplicates_by_id(self, tmp_path: Path) -> None:
        registry = tmp_path / "commands" / "registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            json.dumps({"commands": [{"id": "cmd-x"}]}), encoding="utf-8"
        )
        _append_to_registry(registry, {"id": "cmd-x"})
        data = json.loads(registry.read_text(encoding="utf-8"))
        assert len(data["commands"]) == 1

    def test_uses_commands_key_when_present(self, tmp_path: Path) -> None:
        registry = tmp_path / "registry.json"
        registry.write_text(json.dumps({"commands": []}), encoding="utf-8")
        _append_to_registry(registry, {"id": "my-cmd"})
        data = json.loads(registry.read_text(encoding="utf-8"))
        assert "commands" in data
        assert data["commands"][0]["id"] == "my-cmd"


class TestRender:
    def test_render_produces_output(self, tmp_path: Path) -> None:
        tpl = tmp_path / "test.tpl"
        tpl.write_text("Hello {{ name }}!", encoding="utf-8")
        result = _render(tpl, {"name": "World"})
        assert result == "Hello World!"


class TestScaffoldSkill:
    def test_invalid_risk_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app, ["scaffold", "skill", "my-skill", "--risk", "ultra"]
            )
        assert result.exit_code == 1
        assert "--risk must be one of" in result.output

    def test_no_workspace_exits_1(self) -> None:
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root", return_value=None
        ):
            result = runner.invoke(app, ["scaffold", "skill", "my-skill"])
        assert result.exit_code == 1
        assert "Not inside an SDD workspace" in result.output

    def test_no_templates_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["scaffold", "skill", "my-skill"])
        assert result.exit_code == 1
        assert "Templates not found" in result.output

    def test_skill_already_exists_exits_1(self, tmp_path: Path) -> None:
        _make_skill_templates(tmp_path)
        (tmp_path / ".providence" / "skills" / "my-skill").mkdir(parents=True)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["scaffold", "skill", "my-skill"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_skill_created_successfully(self, tmp_path: Path) -> None:
        _make_skill_templates(tmp_path)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(
                app,
                [
                    "scaffold",
                    "skill",
                    "new-skill",
                    "--category",
                    "analysis",
                    "--risk",
                    "medium",
                    "--description",
                    "Test skill",
                ],
            )
        assert result.exit_code == 0
        assert "new-skill" in result.output
        skill_dir = tmp_path / ".providence" / "skills" / "new-skill"
        assert skill_dir.exists()
        assert (skill_dir / "skill.yaml").exists()
        assert (skill_dir / "SKILL.md").exists()

    def test_skill_registry_updated(self, tmp_path: Path) -> None:
        _make_skill_templates(tmp_path)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["scaffold", "skill", "reg-skill"])
        registry = tmp_path / ".providence" / "skills" / "registry.json"
        assert registry.exists()
        data = json.loads(registry.read_text(encoding="utf-8"))
        all_items = data.get("skills", data.get("commands", []))
        assert any(i.get("name") == "reg-skill" for i in all_items)

    def test_default_description_from_name(self, tmp_path: Path) -> None:
        _make_skill_templates(tmp_path)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["scaffold", "skill", "my-skill"])
        skill_dir = tmp_path / ".providence" / "skills" / "my-skill"
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "My Skill" in content

    def test_critical_risk_uses_high_token_budget(self, tmp_path: Path) -> None:
        _make_skill_templates(tmp_path)
        (
            tmp_path / ".providence" / "templates" / "skill" / "skill.yaml.tpl"
        ).write_text("token_budget: {{ token_budget }}\n", encoding="utf-8")
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            runner.invoke(
                app, ["scaffold", "skill", "crit-skill", "--risk", "critical"]
            )
        content = (
            tmp_path / ".providence" / "skills" / "crit-skill" / "skill.yaml"
        ).read_text(encoding="utf-8")
        assert "high" in content


class TestScaffoldCommand:
    def test_no_workspace_exits_1(self) -> None:
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root", return_value=None
        ):
            result = runner.invoke(app, ["scaffold", "command", "my-cmd"])
        assert result.exit_code == 1
        assert "Not inside an SDD workspace" in result.output

    def test_no_templates_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["scaffold", "command", "my-cmd"])
        assert result.exit_code == 1
        assert "Templates not found" in result.output

    def test_command_already_exists_exits_1(self, tmp_path: Path) -> None:
        _make_command_templates(tmp_path)
        (tmp_path / ".providence" / "commands" / "my-cmd").mkdir(parents=True)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["scaffold", "command", "my-cmd"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_command_created_successfully(self, tmp_path: Path) -> None:
        _make_command_templates(tmp_path)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            result = runner.invoke(app, ["scaffold", "command", "new-cmd"])
        assert result.exit_code == 0
        assert "new-cmd" in result.output
        cmd_dir = tmp_path / ".providence" / "commands" / "new-cmd"
        assert (cmd_dir / "command.yaml").exists()

    def test_command_routes_to_defaults_to_name(self, tmp_path: Path) -> None:
        _make_command_templates(tmp_path)
        (
            tmp_path / ".providence" / "templates" / "command" / "command.yaml.tpl"
        ).write_text("skill_id: {{ skill_id }}\n", encoding="utf-8")
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["scaffold", "command", "auto-cmd"])
        content = (
            tmp_path / ".providence" / "commands" / "auto-cmd" / "command.yaml"
        ).read_text(encoding="utf-8")
        assert "auto-cmd" in content

    def test_command_registry_updated(self, tmp_path: Path) -> None:
        _make_command_templates(tmp_path)
        with patch(
            "providence_cli.commands.scaffold.find_workspace_root",
            return_value=tmp_path,
        ):
            runner.invoke(app, ["scaffold", "command", "reg-cmd"])
        registry = tmp_path / ".providence" / "commands" / "registry.json"
        assert registry.exists()
        data = json.loads(registry.read_text(encoding="utf-8"))
        assert any(i.get("id") == "reg-cmd" for i in data.get("commands", []))
