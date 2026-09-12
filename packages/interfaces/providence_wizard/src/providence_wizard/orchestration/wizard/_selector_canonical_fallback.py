"""Fallback selector-item building by scanning docs/spec/canonical/**/*.md directly.

Used when governed .providence artifacts are not yet compiled (see SelectorCompiler).
"""

from __future__ import annotations

import contextlib
import re
from pathlib import Path

from ._selector_models import (
    SelectorItem,
    _bool_or_default,
    _list_or_default,
    _parse_guideline_dsl_block,
    _text_or_default,
    _validate_unique_ids,
)

# Universal guidelines constant  available when providence_core is installed (optional dep).
_BOOTSTRAP_GUIDELINES: str | None = None
with contextlib.suppress(ImportError):
    from providence_core.governance._bootstrap_guidelines import (
        UNIVERSAL_LANGUAGE_GUIDELINES as _BOOTSTRAP_GUIDELINES,
    )

_CANONICAL_ID_PAT = re.compile(r"^\*\*ID:\*\*\s*(M\d+)", re.MULTILINE)
_CANONICAL_TITLE_PAT = re.compile(r"^#\s+(?:Mandate:)?\s*(.+)$", re.MULTILINE)
_CANONICAL_TYPE_PAT = re.compile(
    r"^\*\*Type:\*\*\s*(HARD|SOFT)", re.MULTILINE | re.IGNORECASE
)
_CANONICAL_CATEGORY_PAT = re.compile(r"^\*\*Category:\*\*\s*(.+)$", re.MULTILINE)
_CANONICAL_GOAL_PAT = re.compile(r"##[^\n]*Goal[^\n]*\n+(.*?)(?=\n##|\Z)", re.DOTALL)


def _parse_canonical_mandate(content: str) -> SelectorItem | None:
    """Parse a single canonical doc into a SelectorItem; return None if not a mandate."""
    id_match = _CANONICAL_ID_PAT.search(content)
    title_match = _CANONICAL_TITLE_PAT.search(content)
    if not id_match or not title_match:
        return None

    item_id = id_match.group(1)
    title = title_match.group(1).strip()

    type_match = _CANONICAL_TYPE_PAT.search(content)
    mandatory = type_match.group(1).upper() == "HARD" if type_match else True

    cat_match = _CANONICAL_CATEGORY_PAT.search(content)
    category = "mandate"
    if cat_match:
        raw = cat_match.group(1).strip()
        category = re.split(r"[/,]", raw)[0].strip().lower().replace(" ", "_")

    description = _extract_goal_description(content) or title
    return SelectorItem(
        id=item_id,
        title=title,
        description=description,
        category=category,
        mandatory=mandatory,
        tags=["mandate"],
        depends_on=[],
        item_type="mandate",
    )


def _extract_goal_description(content: str) -> str:
    """Return first substantive paragraph from the Goal section, or empty string."""
    goal_match = _CANONICAL_GOAL_PAT.search(content)
    if not goal_match:
        return ""
    for paragraph in goal_match.group(1).strip().split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph and not paragraph.startswith(("|", "-", "!", "[")):
            return " ".join(paragraph.split())
    return ""


def _build_items_from_canonical_docs(repo_root: Path) -> list[SelectorItem]:
    """Fallback: build mandate items by scanning docs/spec/canonical/**/*.md.

    Mirrors SourceSpecBootstrapper._extract_canonical_titles() but also
    extracts description, category, and mandatory flag so every SelectorItem
    field is populated.
    """
    canonical_root = repo_root / "docs" / "spec" / "canonical"
    if not canonical_root.exists():
        return []

    items: list[SelectorItem] = []
    seen_ids: set[str] = set()

    for md_file in sorted(canonical_root.rglob("*.md")):
        content = None
        with contextlib.suppress(OSError):
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        if content is None:
            continue
        item = _parse_canonical_mandate(content)
        if item is None or item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        items.append(item)

    if not items:
        return []

    guideline_items = _build_guideline_items_from_bootstrap()
    all_items = sorted(items, key=lambda x: x.id) + guideline_items
    _validate_unique_ids(all_items)
    return all_items


def _build_guideline_items_from_bootstrap() -> list[SelectorItem]:
    """Build guideline SelectorItems from the providence_core bootstrap constant."""
    if _BOOTSTRAP_GUIDELINES is None:
        return []
    return _parse_guidelines_dsl_to_items(_BOOTSTRAP_GUIDELINES)


def _parse_guidelines_dsl_to_items(content: str) -> list[SelectorItem]:
    """Parse a guidelines DSL string into a list of SelectorItems."""
    items: list[SelectorItem] = []
    for match in re.finditer(
        r"guideline\s+(\w+)\s*\{([^}]+)\}", content, re.MULTILINE | re.DOTALL
    ):
        gid = match.group(1)
        body = match.group(2)
        fields = _parse_guideline_dsl_block(body)

        title_match = re.search(r'title:\s*"([^"]*)"', body)
        title = title_match.group(1) if title_match else gid

        description = fields.get("description")
        if not isinstance(description, str) or not description:
            description = title

        category = _text_or_default(fields.get("category"), "guideline")
        mandatory = _bool_or_default(fields.get("mandatory"), False)
        tags = _list_or_default(fields.get("tags"), ["guideline"])

        items.append(
            SelectorItem(
                id=gid,
                title=title,
                description=description,
                category=category,
                mandatory=mandatory,
                tags=tags,
                depends_on=[],
                item_type="guideline",
            )
        )
    return items
