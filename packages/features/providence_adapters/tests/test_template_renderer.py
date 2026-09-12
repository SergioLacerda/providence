"""Tests for TemplateRenderer."""

from pathlib import Path

import pytest

from providence_adapters.template_renderer import _BUNDLED_TEMPLATES, TemplateRenderer

SAMPLE_SKILL = {
    "name": "diagnose",
    "description": "Diagnose workspace problems.",
    "category": "analysis",
    "risk_score": "low",
    "when_to_use": ["failing checks", "unknown failures"],
    "allowed_tools": ["providence doctor run", "providence runtime status"],
    "cli_fallback": ["providence doctor run"],
    "skill_md": "## Required protocol\n1. Run preflight\n2. Execute skill\n\n## Non-compliance\n- Do not invent commands",
}
SAMPLE_COMMAND_SKILL = {
    "id": "sdd-diagnose",
    "routes_to": {"type": "skill", "id": "sdd-diagnose"},
}
SAMPLE_COMMAND_CLI = {
    "id": "sdd-ask",
    "routes_to": {"type": "cli", "command": "providence ask"},
}


class TestTemplateRenderer:
    def test_bundled_templates_dir_exists(self) -> None:
        assert _BUNDLED_TEMPLATES.exists()
        assert (Path(_BUNDLED_TEMPLATES) / "claude" / "command.md.tpl").exists()
        assert (Path(_BUNDLED_TEMPLATES) / "codex" / "skill.prompt.md.tpl").exists()
        assert (Path(_BUNDLED_TEMPLATES) / "codex" / "command.prompt.md.tpl").exists()
        assert (Path(_BUNDLED_TEMPLATES) / "copilot" / "skill.prompt.md.tpl").exists()
        assert (Path(_BUNDLED_TEMPLATES) / "copilot" / "command.prompt.md.tpl").exists()
        assert (Path(_BUNDLED_TEMPLATES) / "antigravity" / "skill.md.tpl").exists()

    def test_default_renderer_uses_bundled_templates(self) -> None:
        renderer = TemplateRenderer()
        assert renderer.templates_dir == _BUNDLED_TEMPLATES

    def test_render_claude_command(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render("claude", "command.md", skill=SAMPLE_SKILL)

        assert "diagnose" in content
        assert "providence doctor run" in content
        assert ".providence/skills/registry.json" in content
        assert "low" in content
        assert "Protocol" in content  # SKILL.md enrichment present

    def test_render_codex_skill(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render("codex", "skill.prompt.md", skill=SAMPLE_SKILL)

        assert "diagnose" in content
        assert "providence doctor run" in content
        assert "providence organize" in content  # analysis category triggers pre-step
        assert "PROVIDENCE GOVERNANCE" in content
        assert "Non-compliance" in content  # SKILL.md enrichment present
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content
        assert "delegation_executed" in content

    def test_render_copilot_skill(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render("copilot", "skill.prompt.md", skill=SAMPLE_SKILL)

        assert "diagnose" in content
        assert "providence doctor run" in content
        assert "SKILL.md" in content  # references SKILL.md when present
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content

    def test_render_codex_command_skill_route(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render(
            "codex", "command.prompt.md", command=SAMPLE_COMMAND_SKILL
        )
        assert "providence skills run sdd-diagnose" in content
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content

    def test_render_codex_command_cli_route(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render(
            "codex", "command.prompt.md", command=SAMPLE_COMMAND_CLI
        )
        assert "`providence ask`" in content
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content

    def test_render_claude_command_cli_route_omits_note_block_by_default(self) -> None:
        """Spike follow-up (20260714-sdd-ask-single-entrypoint-spike): the
        optional adapter note is additive â€” commands without routes_to.note
        must render unchanged."""
        renderer = TemplateRenderer()
        content = renderer.render("claude", "command.md", skill=SAMPLE_COMMAND_CLI)
        assert "Adapter note" not in content

    def test_render_claude_command_cli_route_includes_note_when_present(self) -> None:
        renderer = TemplateRenderer()
        command_with_note = {
            "id": "sdd-ask",
            "routes_to": {
                "type": "cli",
                "command": "providence ask",
                "note": "providence ask is the single governed source of truth.",
            },
        }
        content = renderer.render("claude", "command.md", skill=command_with_note)
        assert "providence ask is the single governed source of truth." in content

    def test_render_codex_command_cli_route_includes_note_when_present(self) -> None:
        renderer = TemplateRenderer()
        command_with_note = {
            "id": "sdd-ask",
            "routes_to": {
                "type": "cli",
                "command": "providence ask",
                "note": "providence ask is the single governed source of truth.",
            },
        }
        content = renderer.render(
            "codex", "command.prompt.md", command=command_with_note
        )
        assert "providence ask is the single governed source of truth." in content
        assert "Adapter note" in content

    def test_render_copilot_command_skill_route(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render(
            "copilot", "command.prompt.md", command=SAMPLE_COMMAND_SKILL
        )
        assert "providence skills run sdd-diagnose" in content
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content

    def test_render_antigravity_skill(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render("antigravity", "skill.md", skill=SAMPLE_SKILL)

        assert "name: diagnose" in content
        assert "failing checks" in content
        assert "providence doctor run" in content
        assert "SKILL.md" in content  # references SKILL.md when present
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content

    def test_render_antigravity_command_cli_route(self) -> None:
        renderer = TemplateRenderer()
        content = renderer.render("antigravity", "skill.md", skill=SAMPLE_COMMAND_CLI)

        assert "name: sdd-ask" in content
        assert ".providence/commands/sdd-ask/command.yaml" in content
        assert "`providence ask`" in content
        assert "execution_gate" in content
        assert "intake_index_mode: none" in content

    def test_render_missing_template_raises(self) -> None:
        from jinja2 import TemplateNotFound

        renderer = TemplateRenderer()
        with pytest.raises(
            TemplateNotFound, match="Template not found: claude/nonexistent.md.tpl"
        ):
            renderer.render("claude", "nonexistent.md", skill=SAMPLE_SKILL)

    def test_custom_templates_dir_is_respected(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "templates"
        (template_dir / "claude").mkdir(parents=True)
        (template_dir / "claude" / "command.md.tpl").write_text(
            "Hello {{ skill.name }}", encoding="utf-8"
        )

        renderer = TemplateRenderer(template_dir)
        content = renderer.render("claude", "command.md", skill=SAMPLE_SKILL)

        assert renderer.templates_dir == template_dir
        assert content == "Hello diagnose"
