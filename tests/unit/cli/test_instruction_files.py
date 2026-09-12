"""Unit tests for providence_cli.generators._instruction_files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _make_config(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "core_fingerprint": "abc12345678901234567890",
        "client_fingerprint": "def12345678901234567890",
        "items": items
        or [
            {
                "id": "M000",
                "type": "MANDATE",
                "name": "Base",
                "description": "Base",
                "metadata": {},
            }
        ],
    }


class TestGenerateAgentInstructionFiles:
    def test_generates_all_ide_files(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        results = generate_agent_instruction_files(tmp_path, _make_config())
        assert len(results) >= 5  # copilot, vscode, claude, gemini, antigravity, cursor

    def test_creates_github_copilot_instructions(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        generate_agent_instruction_files(tmp_path, _make_config())
        copilot_file = tmp_path / ".github" / "copilot-instructions.md"
        assert copilot_file.exists()

    def test_creates_claude_instructions(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        generate_agent_instruction_files(tmp_path, _make_config())
        claude_file = tmp_path / ".claude" / "claude-instructions.md"
        assert claude_file.exists()

    def test_creates_cursor_rules(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        generate_agent_instruction_files(tmp_path, _make_config())
        cursor_file = tmp_path / ".cursor" / "rules" / "sdd-governance.mdc"
        assert cursor_file.exists()

    def test_returns_label_and_path_tuples(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        results = generate_agent_instruction_files(tmp_path, _make_config())
        for label, path in results:
            assert isinstance(label, str)
            assert isinstance(path, Path)

    def test_claude_file_contains_bootstrap(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        generate_agent_instruction_files(tmp_path, _make_config())
        claude_file = tmp_path / ".claude" / "claude-instructions.md"
        content = claude_file.read_text(encoding="utf-8")
        assert "Agent Entrypoint" in content

    def test_files_contain_governance_content(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_agent_instruction_files,
        )

        items = [
            {
                "id": "M001",
                "type": "MANDATE",
                "name": "Test",
                "description": "desc",
                "metadata": {},
            }
        ]
        generate_agent_instruction_files(tmp_path, _make_config(items))
        copilot_file = tmp_path / ".github" / "copilot-instructions.md"
        content = copilot_file.read_text(encoding="utf-8")
        assert "Governance" in content


class TestGenerateCopilotInstructions:
    def test_generates_copilot_file(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_copilot_instructions,
        )

        path = generate_copilot_instructions(tmp_path, _make_config())
        assert path.exists()
        assert path.name == "copilot-instructions.md"

    def test_returns_path_to_file(self, tmp_path: Path) -> None:
        from providence_cli.generators._instruction_files import (
            generate_copilot_instructions,
        )

        path = generate_copilot_instructions(tmp_path, _make_config())
        assert isinstance(path, Path)
