"""File write functions for prompt command generation (Copilot, Cursor, Gemini, Codex)."""

from __future__ import annotations

import contextlib
import json as _json
from pathlib import Path
from typing import Any

from providence_cli.generators._prompt_commands_builders import (
    _AUDIT_JSON_NOTE,
    _COMMANDS_TABLE,
    _HARD_MODE_FIELD_CONTRACT,
    _RUNTIME_STATUS_NOTE,
    _SOFT_GOVERNANCE_CHECK,
    _prompt_spec_for_command,
    _slash_aliases_markdown,
)


def _write_copilot_prompts(
    prompts_dir: Path, command_entries: list[dict[str, Any]]
) -> list[tuple[str, Path]]:
    """Write VS Code Copilot slash-command prompt files."""
    prompts_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, Path]] = []
    for command in command_entries:
        slug, description, mode, body = _prompt_spec_for_command(command)
        target = prompts_dir / f"{slug}.prompt.md"
        content = (
            f"---\ndescription: {description}\nmode: {mode}\n---\n\n"
            f"{body}\n{_SOFT_GOVERNANCE_CHECK}{_AUDIT_JSON_NOTE}\n"
        )
        target.write_text(content, encoding="utf-8")
        written.append((f"Copilot/{slug}", target))
    return written


def _write_cursor_commands(cursor_rules_dir: Path) -> tuple[str, Path]:
    """Write Cursor commands rule file."""
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    cursor_commands = cursor_rules_dir / "sdd-commands.mdc"
    cursor_commands.write_text(
        "---\n"
        "description: SDD CLI commands  invoked when user asks to run tests, lint, governance, etc.\n"
        "globs: ['**/*']\n"
        "alwaysApply: false\n"
        "---\n\n"
        "# SDD CLI Commands\n\n"
        "When the user asks to run tests, lint, check governance, or diagnose the workspace, "
        "use the following SDD CLI commands in the terminal:\n\n"
        + _COMMANDS_TABLE
        + "\n"
        + _RUNTIME_STATUS_NOTE,
        encoding="utf-8",
    )
    cursor_commands.write_text(
        cursor_commands.read_text(encoding="utf-8")
        + _HARD_MODE_FIELD_CONTRACT
        + _SOFT_GOVERNANCE_CHECK
        + _AUDIT_JSON_NOTE,
        encoding="utf-8",
    )
    return ("Cursor/sdd-commands", cursor_commands)


def _write_gemini_files(gemini_dir: Path) -> list[tuple[str, Path]]:
    """Write Gemini CLI commands and settings files."""
    gemini_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, Path]] = []

    gemini_commands = gemini_dir / "commands.md"
    gemini_commands.write_text(
        "# SDD CLI Commands for Gemini\n\n"
        "Use these commands when asked to run tests, lint, or manage governance:\n\n"
        + _COMMANDS_TABLE
        + "\n"
        + _RUNTIME_STATUS_NOTE,
        encoding="utf-8",
    )
    gemini_commands.write_text(
        gemini_commands.read_text(encoding="utf-8")
        + _HARD_MODE_FIELD_CONTRACT
        + _SOFT_GOVERNANCE_CHECK
        + _AUDIT_JSON_NOTE,
        encoding="utf-8",
    )
    written.append(("Gemini/commands.md", gemini_commands))

    gemini_settings = gemini_dir / "settings.json"
    _existing: dict[str, Any] = {}
    if gemini_settings.exists():
        with contextlib.suppress(Exception):
            _existing = _json.loads(gemini_settings.read_text(encoding="utf-8"))
    _existing["promptFiles"] = [".gemini/commands.md"]
    gemini_settings.write_text(_json.dumps(_existing, indent=2), encoding="utf-8")
    written.append(("Gemini/settings.json", gemini_settings))

    return written


def _write_codex_commands(
    codex_dir: Path, aliases: list[tuple[str, str]]
) -> tuple[str, Path]:
    """Write Codex slash aliases manifest."""
    codex_dir.mkdir(parents=True, exist_ok=True)
    codex_commands = codex_dir / "commands.md"
    codex_commands.write_text(
        "# SDD Commands for Codex\n\n"
        "Entrypoint contract:\n"
        "1. You must learn commands and skills from your custom folder path:\n"
        "   - `.codex/commands.md`\n"
        "   - `.codex/skills/`\n"
        "2. You are under governance. Always resolve instructions from `.providence`.\n"
        "   Initial reference: `.providence/agent-instructions.md`\n\n"
        "Use the aliases below as slash commands and route each one to its generated adapter.\n\n"
        + _slash_aliases_markdown(aliases)
        + "\n"
        + "Notes:\n"
        + "- Canonical commands registry: `.providence/commands/registry.json`\n"
        + "- Canonical skills registry: `.providence/skills/registry.json`\n",
        encoding="utf-8",
    )
    codex_commands.write_text(
        codex_commands.read_text(encoding="utf-8")
        + _codex_alias_validation_note(codex_dir, aliases)
        + _HARD_MODE_FIELD_CONTRACT
        + _SOFT_GOVERNANCE_CHECK
        + _AUDIT_JSON_NOTE,
        encoding="utf-8",
    )
    return ("Codex/commands.md", codex_commands)


def _missing_codex_alias_targets(
    codex_dir: Path, aliases: list[tuple[str, str]]
) -> list[str]:
    """Return alias target prompt files missing from an existing Codex skills dir."""
    skills_dir = codex_dir / "skills"
    if not skills_dir.exists():
        return []
    missing: list[str] = []
    for _slash, cmd_id in aliases:
        target = skills_dir / f"{cmd_id}.prompt.md"
        if not target.exists():
            missing.append(target.as_posix())
    return missing


def _codex_alias_validation_note(
    codex_dir: Path, aliases: list[tuple[str, str]]
) -> str:
    """Render Codex alias validation status without requiring skills in seed context."""
    skills_dir = codex_dir / "skills"
    if not skills_dir.exists():
        return (
            "\nCodex alias validation:\n"
            "- `.codex/skills/` is not present; generated-file parity is checked when "
            "adapter prompt files exist.\n"
            "- This validates generated-file parity separately from Codex seed required "
            "context.\n"
        )
    missing = _missing_codex_alias_targets(codex_dir, aliases)
    if not missing:
        return (
            "\nCodex alias validation:\n"
            "- `.codex/commands.md` aliases point to generated "
            "`.codex/skills/*.prompt.md` files.\n"
            "- This validates generated-file parity separately from Codex seed required "
            "context.\n"
        )
    lines = [
        "\nCodex alias validation:",
        "- Missing generated prompt target(s):",
    ]
    lines.extend(f"  - `{path}`" for path in missing)
    lines.append(
        "- This validates generated-file parity separately from Codex seed required context."
    )
    return "\n".join(lines) + "\n"
