"""Unit tests for providence_cli.generators._prompt_commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_cli.generators._prompt_commands import generate_agent_prompt_commands

pytestmark = pytest.mark.unit


def test_generated_prompts_include_soft_governance_footer(tmp_path: Path) -> None:
    generate_agent_prompt_commands(tmp_path)

    copilot_prompt = tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md"
    cursor_commands = tmp_path / ".cursor" / "rules" / "sdd-commands.mdc"
    codex_commands = tmp_path / ".codex" / "commands.md"
    gemini_commands = tmp_path / ".gemini" / "commands.md"

    for path in [
        copilot_prompt,
        cursor_commands,
        codex_commands,
        gemini_commands,
    ]:
        content = path.read_text(encoding="utf-8")
        assert "PROVIDENCE GOVERNANCE CHECK" in content
        assert (
            "PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}"
            in content
        )
        assert ".providence/compiled/audit/*.json" in content


def test_generated_prompts_do_not_reference_legacy_generated_paths(
    tmp_path: Path,
) -> None:
    generate_agent_prompt_commands(tmp_path)

    prompt_files = [
        tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md",
        tmp_path / ".cursor" / "rules" / "sdd-commands.mdc",
        tmp_path / ".codex" / "commands.md",
        tmp_path / ".gemini" / "commands.md",
    ]

    for path in prompt_files:
        content = path.read_text(encoding="utf-8")
        assert "generated/master/compiled" not in content
        assert "generated/client/compiled" not in content


def test_generated_prompts_do_not_contain_duplicate_ask_invocation(
    tmp_path: Path,
) -> None:
    generate_agent_prompt_commands(tmp_path)

    prompt_files = [
        tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md",
        tmp_path / ".cursor" / "rules" / "sdd-commands.mdc",
        tmp_path / ".codex" / "commands.md",
        tmp_path / ".gemini" / "commands.md",
    ]

    for path in prompt_files:
        content = path.read_text(encoding="utf-8")
        assert "providence ask-full ask-full" not in content
        assert "providence ask ask" not in content


def test_codex_includes_slash_aliases(tmp_path: Path) -> None:
    generate_agent_prompt_commands(tmp_path)

    codex_commands = (tmp_path / ".codex" / "commands.md").read_text(encoding="utf-8")

    assert "/sdd-ask" in codex_commands
