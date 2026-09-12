"""Helper functions for Phase1Generator: source-file naming, selection filtering, rendering."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from providence_wizard.templates.mandate_templates import phase1_readme

from .guideline_renderer import GuidelineRenderer
from .mandate_renderer import MandateRenderer
from .models import Guideline, Mandate


def candidate_names(filename: str) -> list[str]:
    """Return acceptable source filenames for a governance source file."""
    if filename == "mandate.spec":
        return ["mandate.spec", "mandate.md"]
    if filename == "guidelines.dsl":
        return ["guidelines.dsl", "guidelines.md"]
    return [filename]


def selector_selection_ids(config: dict[str, Any]) -> list[str]:
    """Resolve the selector-selected IDs from a Phase1Generator config dict."""
    selection = config.get("selector_selection", {})
    if isinstance(selection, dict):
        resolved = selection.get("resolved_ids", selection.get("selected_ids"))
        if isinstance(resolved, list) and all(isinstance(i, str) for i in resolved):
            return list(resolved)
    legacy = config.get("selector_selection_ids", [])
    if isinstance(legacy, list) and all(isinstance(i, str) for i in legacy):
        return list(legacy)
    return []


def apply_selector_selection(
    mandates: list[Mandate],
    guidelines: list[Guideline],
    selected_ids: list[str],
) -> tuple[list[Mandate], list[Guideline], str]:
    """Filter mandates/guidelines to the selected IDs.

    Returns the (possibly filtered) mandates and guidelines, plus an error
    message ("" if none) when `selected_ids` references unknown IDs.
    """
    if not selected_ids:
        return mandates, guidelines, ""
    selected = set(selected_ids)
    available = {m.id for m in mandates} | {g.id for g in guidelines}
    unknown = sorted(selected - available)
    if unknown:
        return mandates, guidelines, f"Unknown selected IDs: {', '.join(unknown)}"
    return (
        [m for m in mandates if m.id in selected],
        [g for g in guidelines if g.id in selected],
        "",
    )


def write_markdown_templates(
    output_path: Path,
    mandates: list[Mandate],
    guidelines: list[Guideline],
    language: str,
    adoption_level: str,
    emit: Callable[[str], None],
) -> None:
    """Write per-category mandate and guideline markdown files to output_path."""
    output_path.mkdir(parents=True, exist_ok=True)
    for pattern in ("mandates-*.md", "guidelines-*.md", "README.md"):
        for stale in output_path.glob(pattern):
            if stale.is_file():
                stale.unlink()
    MandateRenderer(output_path, emit).render(mandates)
    GuidelineRenderer(output_path, emit).render(guidelines)
    readme_content = phase1_readme(
        language, adoption_level, len(mandates), len(guidelines)
    )
    (output_path / "README.md").write_text(readme_content, encoding="utf-8")
