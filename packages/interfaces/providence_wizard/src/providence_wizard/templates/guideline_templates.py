"""Markdown template strings for guideline files."""

from __future__ import annotations

from typing import Any


def guideline_block(guideline: Any) -> str:
    """Render a single guideline as a markdown section."""
    lines = [
        f"## {guideline.id}: {guideline.title}",
        "",
        f"**Type:** {guideline.type}",
        "",
    ]
    if guideline.description:
        lines += [f"**Description:** {guideline.description}", ""]
    lines += [
        "**Status:** `required: true` (Default: include)",
        "",
        "**Customizable:** `true` (Change below if needed)",
        "",
        "**Optional:** `false` (Included by default)",
        "",
        "### To Customize This Rule:",
        "",
        "Change the Status line above to ONE of:",
        "- `required: true`  Keep as mandatory",
        "- `optional: true`  Skip this rule",
        "- `custom: true`  Include but customizable",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def guideline_category_header(category: str) -> str:
    """Return the markdown header block for a guideline category file."""
    return (
        f"# Guidelines - {category.upper()}\n\n"
        " SOFT RECOMMENDATIONS - These are optional/customizable\n\n"
    )
