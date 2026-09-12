"""Tests for CLI prompt command generator contracts."""

from pathlib import Path

from providence_cli.generators._prompt_commands import generate_agent_prompt_commands


def test_sdd_ask_prompt_includes_preflight_and_500_fallback(tmp_path: Path) -> None:
    """sdd-ask prompt must include HARD preflight contract and 5xx fallback note."""
    generate_agent_prompt_commands(tmp_path, config={})
    ask_prompt = (tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md").read_text(
        encoding="utf-8"
    )
    assert "providence runtime status" in ask_prompt
    assert "providence governance validate" in ask_prompt
    assert 'providence ask --full "$QUERY"' in ask_prompt
    assert "fingerprint`, `context_source`, and `mandates_loaded`" in ask_prompt
    assert "API Error: 5xx" in ask_prompt
    assert "request_id" in ask_prompt
    assert "execution_gate" in ask_prompt
    assert "intake_index_mode: none" in ask_prompt
    assert "delegation_executed" in ask_prompt
    assert (
        "PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | profile=${profile}"
        in ask_prompt
    )


def test_generated_command_surfaces_never_emit_duplicated_ask_full(
    tmp_path: Path,
) -> None:
    """Generated command helper files must not duplicate the full ask variant."""
    generate_agent_prompt_commands(tmp_path, config={})
    files = [
        tmp_path / ".cursor" / "rules" / "sdd-commands.mdc",
        tmp_path / ".gemini" / "commands.md",
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert content.count('providence ask --full "$QUERY"') <= 1
        assert "/sdd-ask-full" not in content


def test_generated_command_surfaces_include_hard_mode_field_contract(
    tmp_path: Path,
) -> None:
    generate_agent_prompt_commands(tmp_path, config={})
    files = [
        tmp_path / ".github" / "prompts" / "sdd-ask.prompt.md",
        tmp_path / ".cursor" / "rules" / "sdd-commands.mdc",
        tmp_path / ".gemini" / "commands.md",
        tmp_path / ".codex" / "commands.md",
    ]

    for path in files:
        content = path.read_text(encoding="utf-8")
        assert "execution_gate" in content
        assert "gate_reason" in content
        assert "intake_index_mode" in content
        assert "intake_chunks" in content
        assert "governance_mode" in content
        assert "intake_index_mode: none" in content
        assert "execution_gate: blocked" in content


def test_codex_commands_reports_missing_alias_targets_when_skills_dir_exists(
    tmp_path: Path,
) -> None:
    skills_dir = tmp_path / ".codex" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "sdd-ask.prompt.md").write_text("ok", encoding="utf-8")

    generate_agent_prompt_commands(tmp_path, config={})

    commands = (tmp_path / ".codex" / "commands.md").read_text(encoding="utf-8")
    assert "Codex alias validation" in commands
    assert ".codex/skills/sdd-organize.prompt.md" in commands
    assert "- `.codex/skills/sdd-ask.prompt.md`" not in commands
