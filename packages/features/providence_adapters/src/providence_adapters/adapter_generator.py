"""AdapterGenerator: renders Jinja2 templates for multi-agent skills/commands."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .skill_loader import SkillLoader
from .template_renderer import _BUNDLED_TEMPLATES, TemplateRenderer


@dataclass
class AdapterResult:
    """Result of adapter generation."""

    target: str
    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = field(default=True)


class AdapterGenerator:
    """Generates per-skill/per-command adapter files for Claude, Codex, Copilot, Antigravity."""

    TARGETS = ["claude", "codex", "copilot", "antigravity"]
    AGENT_DIRS = {
        "claude": ".claude/commands",
        "codex": ".codex/skills",
        "copilot": ".github/prompts",
        "antigravity": ".gemini/antigravity/skills",
    }
    EXTENSIONS = {
        "claude": ".md",
        "codex": ".prompt.md",
        "copilot": ".prompt.md",
        "antigravity": "/SKILL.md",
    }

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize AdapterGenerator.

        Args:
            templates_dir: optional override for template directory.
                           Defaults to bundled templates inside the package.
        """
        self.templates_dir = (
            Path(templates_dir) if templates_dir else _BUNDLED_TEMPLATES
        )
        self.renderer = TemplateRenderer(self.templates_dir)
        self.skill_loader = SkillLoader()

    def generate(self, output_dir: Path) -> dict[str, AdapterResult]:
        """
        Generate adapters for all targets.

        Args:
            output_dir: path to project root (where .providence/ lives)

        Returns:
            dict of target -> AdapterResult
        """
        results = {}

        for target in self.TARGETS:
            try:
                result = self._generate_for_target(target, output_dir)
                results[target] = result
            except Exception as e:
                results[target] = AdapterResult(
                    target=target,
                    success=False,
                    errors=[str(e)],
                )

        return results

    def _generate_for_target(self, target: str, output_dir: Path) -> AdapterResult:
        """Generate adapters for a single target."""
        result = AdapterResult(target=target)

        sdd_dir = Path(output_dir) / ".providence"
        skills = self.skill_loader.load_skills(sdd_dir)
        commands = self.skill_loader.load_commands(sdd_dir)

        agent_dir = Path(output_dir) / self.AGENT_DIRS[target]
        agent_dir.mkdir(parents=True, exist_ok=True)

        for skill in skills:
            try:
                file_path = self._render_skill_adapter(target, skill, agent_dir)
                result.files_written.append(str(file_path))
            except Exception as e:
                result.errors.append(f"Failed to render skill {skill.get('name')}: {e}")
                result.success = False

        for command in commands:
            targets = command.get("adapter_targets", command.get("targets", []))
            if target not in targets:
                continue
            try:
                file_path = self._render_command_adapter(target, command, agent_dir)
                result.files_written.append(str(file_path))
            except Exception as e:
                result.errors.append(
                    f"Failed to render command {command.get('id')}: {e}"
                )
                result.success = False

        return result

    def _render_command_adapter(
        self, target: str, command: dict[str, Any], output_dir: Path
    ) -> Path:
        """Render a single command adapter for a target."""
        if target == "claude":
            template_name = "command.md"
        elif target == "codex" or target == "copilot":
            template_name = "command.prompt.md"
        else:  # antigravity
            template_name = "skill.md"

        cmd_id = command.get("id", "unknown")

        if target == "antigravity":
            cmd_dir: Path = output_dir / cmd_id
            cmd_dir.mkdir(parents=True, exist_ok=True)
            output_file: Path = cmd_dir / "SKILL.md"
        else:
            output_file = output_dir / f"{cmd_id}{self.EXTENSIONS[target]}"

        if target in {"codex", "copilot"}:
            content = self.renderer.render(target, template_name, command=command)
        else:
            content = self.renderer.render(target, template_name, skill=command)
        output_file.write_text(content, encoding="utf-8")
        return output_file

    def _render_skill_adapter(
        self, target: str, skill: dict[str, Any], output_dir: Path
    ) -> Path:
        """Render a single skill adapter for a target."""
        # Determine template name based on target
        if target == "claude":
            template_name = "command.md"
        elif target == "codex" or target == "copilot":
            template_name = "skill.prompt.md"
        else:  # antigravity
            template_name = "skill.md"

        # For antigravity, create subdirectory per skill
        if target == "antigravity":
            skill_dir: Path = output_dir / skill.get("name", "unknown")
            skill_dir.mkdir(parents=True, exist_ok=True)
            output_file: Path = skill_dir / "SKILL.md"
        else:
            output_file = (
                output_dir / f"{skill.get('name', 'unknown')}{self.EXTENSIONS[target]}"
            )

        # Render template
        content = self.renderer.render(target, template_name, skill=skill)

        # Write file
        output_file.write_text(content, encoding="utf-8")
        return output_file
