"""Unit tests for providence_cli.generators._prompt_commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tomllib

from providence_cli.generators._prompt_commands import generate_agent_prompt_commands
from providence_wizard.orchestration.prompt_submit_hooks import (
    PromptSubmitHookGenerator,
)

pytestmark = pytest.mark.unit


def test_generated_prompts_include_soft_governance_footer(tmp_path: Path) -> None:
    generate_agent_prompt_commands(tmp_path)

    copilot_prompt = tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md"
    cursor_commands = tmp_path / ".cursor" / "rules" / "providence-commands.mdc"
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
        tmp_path / ".cursor" / "rules" / "providence-commands.mdc",
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
        tmp_path / ".cursor" / "rules" / "providence-commands.mdc",
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


@pytest.mark.parametrize(
    "adapter_relative_path",
    [
        ".claude/settings.json",
        ".codex/config.toml",
        ".gemini/settings.json",
    ],
)
def test_deployed_prompt_submit_adapters_do_not_reference_stale_compiled_path(
    tmp_path: Path,
    adapter_relative_path: str,
) -> None:
    """Validate generated adapters in an isolated synthetic client.

    This test must not inspect active `.codex`, `.claude`, or `.gemini` files
    from the checkout because those belong to the operator/runtime environment.
    """
    output_base = tmp_path / "generated" / "client" / "build" / "final-template"
    PromptSubmitHookGenerator(output_base, {"claude", "codex", "gemini"}).generate()
    (output_base / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")
    adapter_path = output_base / adapter_relative_path

    content = adapter_path.read_text(encoding="utf-8")
    assert "generated/client/compiled" not in content
    assert "PROVIDENCE_WORKSPACE_ROOT" in content

    if adapter_path.suffix == ".toml":
        payload = tomllib.loads(content)
        command = payload["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    else:
        payload = json.loads(content)
        if adapter_path.parts[-2] == ".claude":
            command = payload["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        else:
            command = payload["hooks"]["BeforeAgent"][0]["hooks"][0]["command"]

    assert "generated/client/compiled" not in command
    assert "PROVIDENCE_WORKSPACE_ROOT" in command
    assert (
        output_base / ".providence" / "runtime" / "hooks" / "prompt-submit.py"
    ).exists()
