"""Jinja2 template renderer for adapters."""

from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateNotFound,
    select_autoescape,
)

# Templates bundled inside the package
_BUNDLED_TEMPLATES = Path(__file__).parent / "templates" / "adapters"


class TemplateRenderer:
    """Renders Jinja2 templates from the providence_adapters package."""

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize TemplateRenderer.

        Args:
            templates_dir: override path to templates directory. Defaults to
                           bundled templates inside the providence_adapters package.
        """
        self.templates_dir = (
            Path(templates_dir) if templates_dir else _BUNDLED_TEMPLATES
        )
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
        )

    def render(self, target: str, template_name: str, **context: Any) -> str:
        """
        Render a template for a target.

        Args:
            target: one of claude, codex, copilot, antigravity
            template_name: template filename (e.g., "skill.prompt.md")
            **context: variables to pass to template

        Returns:
            rendered content
        """
        template_path = f"{target}/{template_name}.tpl"

        try:
            template = self.env.get_template(template_path)
            return str(template.render(**context))
        except TemplateNotFound as e:
            raise TemplateNotFound(
                f"Template not found: {template_path} in {self.templates_dir}"
            ) from e
