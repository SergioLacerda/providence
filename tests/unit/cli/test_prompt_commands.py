"""Unit tests for providence_cli.generators._prompt_commands."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from providence_cli.generators._prompt_commands import generate_agent_prompt_commands

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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "adapter_relative_path",
    [
        ".claude/settings.json",
        ".codex/config.toml",
        ".gemini/settings.json",
        "generated/client/build/final-template/.claude/settings.json",
        "generated/client/build/final-template/.codex/config.toml",
        "generated/client/build/final-template/.gemini/settings.json",
    ],
)
def test_deployed_prompt_submit_adapters_do_not_reference_stale_compiled_path(
    adapter_relative_path: str,
) -> None:
    """Regression (20260913-governance-hooks-dogfood, F002/F003): this
    repository's own checked-in/deployed prompt-submit hook adapters must
    reference a hook file that actually exists on disk, never the stale
    `generated/client/compiled` staging path a prior generation run left
    behind."""
    adapter_path = _repo_root() / adapter_relative_path
    if not adapter_path.exists():
        pytest.skip(f"{adapter_relative_path} not present in this checkout")

    content = adapter_path.read_text(encoding="utf-8")
    assert "generated/client/compiled" not in content

    match = re.search(r"exit 0'\s+sh\s+([^\"]+)\"", content)
    assert match, f"no prompt-submit hook command found in {adapter_relative_path}"
    hook_path = Path(match.group(1))
    assert hook_path.is_absolute(), (
        f"hook path in {adapter_relative_path} must be cwd-independent"
    )
    assert hook_path.exists(), (
        f"{adapter_relative_path} points at a hook file that does not exist: "
        f"{hook_path}"
    )
