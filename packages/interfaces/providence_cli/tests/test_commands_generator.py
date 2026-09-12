"""Tests for providence_cli.generators._commands  generate_commands_registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from tests.helpers.text_io import read_text_utf8

from providence_cli.generators._commands import (
    _CLI_COMMANDS,
    generate_commands_registry,
)


class TestGenerateCommandsRegistry:
    def test_creates_registry_json(self, tmp_path: Path) -> None:
        result = generate_commands_registry(str(tmp_path), {})
        registry_path = Path(result["registry_path"])
        assert registry_path.exists()
        assert registry_path.name == "registry.json"

    def test_registry_in_sdd_commands_dir(self, tmp_path: Path) -> None:
        result = generate_commands_registry(str(tmp_path), {})
        assert ".providence/commands" in result["registry_path"]

    def test_command_count_includes_skills_and_cli_commands(
        self, tmp_path: Path
    ) -> None:
        from providence_runtime.skills import _REGISTRY

        result = generate_commands_registry(str(tmp_path), {})
        cli_ids = {cmd["id"] for cmd in _CLI_COMMANDS}
        expected = len(cli_ids) + sum(1 for name in _REGISTRY if name not in cli_ids)
        assert result["command_count"] == expected

    def test_registry_json_contains_skill_routed_commands(self, tmp_path: Path) -> None:
        from providence_runtime.skills import _REGISTRY

        generate_commands_registry(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "commands" / "registry.json"
        )
        data = json.loads(content)
        assert data["schema_version"] == "1.0.0"
        ids = {cmd["id"] for cmd in data["commands"]}
        for skill_name in _REGISTRY:
            assert skill_name in ids

    def test_registry_json_contains_cli_routed_commands(self, tmp_path: Path) -> None:
        generate_commands_registry(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "commands" / "registry.json"
        )
        data = json.loads(content)
        by_id = {cmd["id"]: cmd for cmd in data["commands"]}
        assert by_id["sdd-ask"]["routes_to"] == {
            "type": "cli",
            "command": "providence ask",
        }
        assert by_id["sdd-ask"]["slash"] == "/sdd-ask"
        assert "claude" in by_id["sdd-ask"]["targets"]

    def test_skill_routed_command_yaml(self, tmp_path: Path) -> None:
        from providence_runtime.skills import _REGISTRY

        generate_commands_registry(str(tmp_path), {})
        cli_ids = {cmd["id"] for cmd in _CLI_COMMANDS}
        skill_name = next(name for name in _REGISTRY if name not in cli_ids)
        cmd_yaml = tmp_path / ".providence" / "commands" / skill_name / "command.yaml"
        assert cmd_yaml.exists()
        content = read_text_utf8(cmd_yaml)
        assert f'id: "{skill_name}"' in content
        assert "type: skill" in content
        assert f"id: {skill_name}" in content
        assert "adapter_targets:" in content

    def test_cli_routed_command_yaml(self, tmp_path: Path) -> None:
        generate_commands_registry(str(tmp_path), {})
        cmd_yaml = tmp_path / ".providence" / "commands" / "sdd-ask" / "command.yaml"
        assert cmd_yaml.exists()
        content = read_text_utf8(cmd_yaml)
        assert 'id: "sdd-ask"' in content
        assert "type: cli" in content
        assert 'command: "providence ask"' in content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = generate_commands_registry(str(nested), {})
        assert Path(result["registry_path"]).exists()

    def test_mapped_skill_has_capability_id_in_registry_and_yaml(
        self, tmp_path: Path
    ) -> None:
        generate_commands_registry(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "commands" / "registry.json"
        )
        data = json.loads(content)
        by_id = {cmd["id"]: cmd for cmd in data["commands"]}
        assert by_id["sdd-diagnose"]["capability_id"] == "diagnose"

        cmd_yaml = (
            tmp_path / ".providence" / "commands" / "sdd-diagnose" / "command.yaml"
        )
        assert "capability_id: diagnose" in read_text_utf8(cmd_yaml)

    def test_unmapped_skill_has_no_capability_id(self, tmp_path: Path) -> None:
        generate_commands_registry(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "commands" / "registry.json"
        )
        data = json.loads(content)
        by_id = {cmd["id"]: cmd for cmd in data["commands"]}
        assert "capability_id" not in by_id["sdd-validate-governance"]

        cmd_yaml = (
            tmp_path
            / ".providence"
            / "commands"
            / "sdd-validate-governance"
            / "command.yaml"
        )
        assert "capability_id" not in read_text_utf8(cmd_yaml)

    def test_cli_routed_command_has_no_capability_id(self, tmp_path: Path) -> None:
        """sdd-ask the skill has capability_id="query", but the /sdd-ask command
        routes to the CLI, not the skill  no SkillDefinition in that path."""
        generate_commands_registry(str(tmp_path), {})
        content = read_text_utf8(
            tmp_path / ".providence" / "commands" / "registry.json"
        )
        data = json.loads(content)
        by_id = {cmd["id"]: cmd for cmd in data["commands"]}
        assert "capability_id" not in by_id["sdd-ask"]

        cmd_yaml = tmp_path / ".providence" / "commands" / "sdd-ask" / "command.yaml"
        assert "capability_id" not in read_text_utf8(cmd_yaml)

    def test_import_error_returns_fallback(self, tmp_path: Path) -> None:
        with patch.dict(sys.modules, {"providence_runtime.skills": None}):
            result = generate_commands_registry(str(tmp_path), {})
        assert result["registry_path"] is None
        assert result["command_count"] == 0
        assert "error" in result


class TestCliCommandsConstant:
    def test_includes_sdd_ask_and_sdd_organize(self) -> None:
        ids = {cmd["id"] for cmd in _CLI_COMMANDS}
        assert "sdd-ask" in ids
        assert "sdd-organize" in ids

    def test_all_entries_have_required_keys(self) -> None:
        for cmd in _CLI_COMMANDS:
            assert {"id", "slash", "routes_to", "description", "targets"} <= set(
                cmd.keys()
            )
            assert cmd["routes_to"]["type"] == "cli"
