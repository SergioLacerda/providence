"""Markdown template strings for mandate files."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def mandate_block(mandate: Any) -> str:
    """Render a single mandate as a markdown section."""
    lines = [
        f"## {mandate.id}: {mandate.title}",
        "",
        f"**Type:** {mandate.type}",
        "",
        f"**Description:** {mandate.description}",
        "",
    ]
    if mandate.rationale:
        lines += [f"**Rationale:** {mandate.rationale}", ""]
    lines += [
        "**Status:** `required: true` (Default: mandatory)",
        "",
        "**Customizable:** `false` (Hard rules cannot be modified)",
        "",
        "**Optional:** `false` (Not negotiable)",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def mandate_category_header(category: str) -> str:
    """Return the markdown header block for a mandate category file."""
    return f"# Mandates - {category.upper()}\n\n HARD RULES - These are mandatory by default\n\n"


def phase1_readme(
    language: str,
    adoption_level: str,
    n_mandates: int,
    n_guidelines: int,
) -> str:
    """Return the Phase 1 README.md content with config summary and instructions."""
    return f"""# Phase 1: Governance Rules Templates

**Generated:** {datetime.now().isoformat()}

## Configuration

- **Language:** {language}
- **Adoption Level:** {adoption_level}

## What You Have

Raw templates for all mandates and guidelines, organized by category:
- `mandates-*.md`  Core architectural rules (hard, non-negotiable)
- `guidelines-*.md`  Best practices (soft, customizable)

Total: {n_mandates} mandates + {n_guidelines} guidelines

## Status Field Defaults

Each rule starts with:
```
**Status:** required: true
**Customizable:** true/false
**Optional:** false
```

## Phase 2: What to Do Now

For each `.md` file: open, read each rule, and change the Status line to ONE of:
- `required: true`  Keep as mandatory
- `optional: true`  Skip this rule
- `custom: true`  Include but allow customization

Once edited, run Phase 3 to compile.
"""
