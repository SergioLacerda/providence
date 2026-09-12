"""ClaudeStandaloneGenerator: zero-SDD-mention Claude Code governance projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = (
    Path(__file__).parent.parent / "templates" / "claude_plugin" / "standalone"
)
_STANDALONE_RULESET_VERSION = "1.0.0"
_STANDALONE_LAST_VERIFIED = "2026-08-19"
_TOPIC_NAMES = (
    "architecture",
    "git-safety",
    "testing",
    "generated-artifacts",
    "go",
    "documentation",
    "token-economy",
)


@dataclass
class ClaudeStandaloneResult:
    """Result of standalone (zero-SDD-mention) Claude Code config generation."""

    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class ClaudeStandaloneGenerator:
    """Generates a zero-SDD-mention Claude Code governance projection (Soft/Standalone)."""

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_standalone(
        self, output_dir: Path, dest: Path | None = None
    ) -> ClaudeStandaloneResult:
        """
        Generate the standalone Claude Code governance projection.

        Content is curated, static text (same approach as
        ``DevinPluginGenerator.generate_standalone()`` and
        ``CopilotStandaloneGenerator.generate_standalone()``) â€” it is not parsed
        from this repository's own ``.providence/`` governance sources. Embedding this
        project's specific mandate/guideline content would tie "standalone"
        output to the Providence's own governance framework, which contradicts
        the zero-SDD-mention, reusable-in-any-project guarantee this mode makes.

        Args:
            output_dir: project root (used only to resolve the default dest).
            dest: output directory. Defaults to {output_dir}/dist/claude-standalone
                â€” a build artifact, never the project's real root CLAUDE.md/.claude/
                files.
        """
        result = ClaudeStandaloneResult()
        context: dict[str, Any] = {
            "standalone_ruleset_version": _STANDALONE_RULESET_VERSION,
            "last_verified": _STANDALONE_LAST_VERIFIED,
        }

        root = Path(dest) if dest else Path(output_dir) / "dist" / "claude-standalone"

        try:
            self._write(root / "CLAUDE.md", "CLAUDE.md", context, result)
            for topic in _TOPIC_NAMES:
                self._write(
                    root / ".claude" / "rules" / f"{topic}.md",
                    f"rules/{topic}.md",
                    context,
                    result,
                )
            self._write(
                root / ".claude" / "settings.json", "settings.json", context, result
            )
        except Exception as e:  # defensive: partial output is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write(
        self,
        path: Path,
        template_name: str,
        context: dict[str, Any],
        result: ClaudeStandaloneResult,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
