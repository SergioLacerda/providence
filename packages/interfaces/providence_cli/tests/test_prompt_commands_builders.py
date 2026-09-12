"""Tests for prompt command registry loaders and pure string builders."""

from __future__ import annotations

import json
from pathlib import Path

from providence_cli.generators._prompt_commands_builders import (
    _prompt_spec_for_command,
    _slash_aliases_markdown,
)
from providence_cli.generators._prompt_commands_data import (
    _default_command_entries,
    _load_command_entries,
    _load_slash_aliases,
)


def _write_registry(output_dir: Path, commands: object) -> None:
    registry_dir = output_dir / ".providence" / "commands"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "registry.json").write_text(
        json.dumps({"commands": commands}), encoding="utf-8"
    )


def test_load_slash_aliases_reads_canonical_registry(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {"slash": "/sdd-custom", "id": "sdd-custom"},
            {"slash": "/sdd-other", "id": "sdd-other"},
            "not-a-dict",
            {"slash": "", "id": "missing-slash"},
        ],
    )

    aliases = _load_slash_aliases(tmp_path)

    assert ("/sdd-custom", "sdd-custom") in aliases
    assert ("/sdd-other", "sdd-other") in aliases
    assert len(aliases) == 2


def test_load_slash_aliases_falls_back_when_registry_missing(tmp_path: Path) -> None:
    aliases = _load_slash_aliases(tmp_path)

    assert ("/sdd-ask", "sdd-ask") in aliases
    assert ("/sdd-organize", "sdd-organize") in aliases


def test_load_command_entries_reads_canonical_registry(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "id": "sdd-custom",
                "slash": "/sdd-custom",
                "routes_to": {"type": "cli", "command": "sdd custom run"},
            },
            "not-a-dict",
            {"id": "missing-routes", "slash": "/sdd-missing", "routes_to": "bad"},
        ],
    )

    entries = _load_command_entries(tmp_path)

    assert len(entries) == 1
    assert entries[0]["id"] == "sdd-custom"


def test_load_command_entries_falls_back_when_no_valid_entries(
    tmp_path: Path,
) -> None:
    _write_registry(
        tmp_path, [{"id": "no-slash", "slash": "", "routes_to": {"type": "cli"}}]
    )

    entries = _load_command_entries(tmp_path)

    assert entries == _default_command_entries()


def test_load_command_entries_falls_back_when_registry_missing(
    tmp_path: Path,
) -> None:
    entries = _load_command_entries(tmp_path)

    assert entries == _default_command_entries()


def test_prompt_spec_for_cli_command() -> None:
    slug, description, mode, body = _prompt_spec_for_command(
        {
            "id": "sdd-custom",
            "routes_to": {"type": "cli", "command": "sdd custom run"},
        }
    )

    assert slug == "sdd-custom"
    assert description == "Run sdd custom run"
    assert mode == "agent"
    assert "sdd custom run" in body


def test_prompt_spec_for_skill_command() -> None:
    slug, description, mode, body = _prompt_spec_for_command(
        {
            "id": "sdd-skill-cmd",
            "routes_to": {"type": "skill", "id": "my-skill"},
        }
    )

    assert slug == "sdd-skill-cmd"
    assert "my-skill" in description
    assert mode == "agent"
    assert "providence skills run my-skill" in body


def test_prompt_spec_for_sdd_ask() -> None:
    slug, description, mode, body = _prompt_spec_for_command({"id": "sdd-ask"})

    assert slug == "sdd-ask"
    assert description == "Query Providence governance context"
    assert mode == "agent"
    assert 'providence ask --full "$QUERY"' in body
    assert "API Error: 5xx" in body
    assert "execution_gate" in body
    assert "intake_index_mode: none" in body
    assert "delegation_executed" in body


def test_prompt_spec_for_sdd_organize() -> None:
    slug, description, mode, body = _prompt_spec_for_command({"id": "sdd-organize"})

    assert slug == "sdd-organize"
    assert description == "Prepare indexed context for large inputs"
    assert mode == "agent"
    assert "providence organize" in body
    assert ".providence/runtime/ask-intake/" in body
    assert "execution_gate" in body
    assert "intake_index_mode: none" in body


def test_slash_aliases_markdown_renders_table_rows() -> None:
    markdown = _slash_aliases_markdown(
        [("/sdd-ask", "sdd-ask"), ("/sdd-organize", "sdd-organize")]
    )

    assert "## Slash aliases (`/sdd-*`)" in markdown
    assert "| `/sdd-ask` | `.codex/skills/sdd-ask.prompt.md` |" in markdown
    assert "| `/sdd-organize` | `.codex/skills/sdd-organize.prompt.md` |" in markdown


def test_prompt_spec_for_unknown_route_type_falls_back() -> None:
    slug, description, mode, body = _prompt_spec_for_command(
        {"id": "sdd-unknown", "routes_to": {"type": "other"}}
    )

    assert slug == "sdd-unknown"
    assert description == "Run sdd-unknown"
    assert mode == "agent"
    assert ".providence/commands/registry.json" in body
