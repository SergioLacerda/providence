"""CLI prompt/command file generators for all supported AI tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_cli.generators._prompt_commands_data import (
    _load_command_entries,
    _load_slash_aliases,
)
from providence_cli.generators._prompt_commands_writers import (
    _write_codex_commands,
    _write_copilot_prompts,
    _write_cursor_commands,
    _write_gemini_files,
)


def generate_agent_prompt_commands(
    output_dir: Path,
    config: dict[str, Any] | None = None,  # noqa: ARG001
) -> list[tuple[str, Path]]:
    """Generate CLI prompt/command files for all supported AI tools.

    These files let users invoke SDD CLI commands natively from each tool:
    - VS Code Copilot: .github/prompts/*.prompt.md  (slash commands /sdd-*)
    - Cursor:          .cursor/rules/sdd-commands.mdc
    - Gemini CLI:      .gemini/commands.md + .gemini/settings.json

    NOTE: CLAUDE.md is generated exclusively by ai_seeds.py:generate_claude_seed()
    to ensure single source of truth.

    Args:
        output_dir: Workspace root directory.
        config: Unused (kept for API compatibility).

    Returns:
        List of (label, path) for each written file.
    """
    written: list[tuple[str, Path]] = []

    command_entries = _load_command_entries(output_dir)
    aliases = _load_slash_aliases(output_dir)
    written += _write_copilot_prompts(
        output_dir / ".github" / "prompts", command_entries
    )
    written.append(_write_cursor_commands(output_dir / ".cursor" / "rules"))
    written.append(_write_codex_commands(output_dir / ".codex", aliases))
    # NOTE: CLAUDE.md is now generated exclusively by ai_seeds.py:generate_claude_seed()
    # to ensure single source of truth and prevent duplication.
    written += _write_gemini_files(output_dir / ".gemini")
    return written
