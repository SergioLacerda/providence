"""Selector item model and parsing/validation helpers for SelectorCompiler."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SelectorItem:
    """Structured selector item."""

    id: str
    title: str
    description: str
    category: str
    mandatory: bool
    tags: list[str]
    depends_on: list[str]
    item_type: str = "mandate"

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "mandatory": self.mandatory,
            "tags": self.tags,
            "depends_on": self.depends_on,
            "item_type": self.item_type,
        }


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.lower()
    if normalized in {"true", "yes"}:
        return True
    if normalized in {"false", "no"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _parse_csv(value: str | None) -> list[str] | None:
    if value is None or not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def _extract_field(body: str, field_name: str) -> str | None:
    match = re.search(rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)", body)
    return match.group(1).strip() if match else None


def _extract_description(body: str) -> str:
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
    for paragraph in paragraphs:
        if not paragraph.startswith("**"):
            return " ".join(paragraph.split())
    raise ValueError("Selector item description is missing in mandates.md")


def _parse_section_body(body: str) -> dict[str, object]:
    return {
        "description": _extract_description(body),
        "category": _extract_field(body, "Category"),
        "mandatory": _parse_bool(_extract_field(body, "Mandatory")),
        "tags": _parse_csv(_extract_field(body, "Tags")),
        "depends_on": _parse_csv(_extract_field(body, "Depends on")),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _require_text(value: object, item_id: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"Selector description missing for {item_id}")


def _text_or_default(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _list_or_default(value: object, default: list[str]) -> list[str]:
    if isinstance(value, list) and all(isinstance(i, str) for i in value):
        return list(value)
    return list(default)


def _bool_or_default(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _validate_unique_ids(items: list[SelectorItem]) -> None:
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Selector items contain duplicate ids.")


def _validate_dependencies(items: list[SelectorItem]) -> None:
    item_ids = {item.id for item in items}
    unknown = sorted(
        dep for item in items for dep in item.depends_on if dep not in item_ids
    )
    if unknown:
        raise ValueError(f"Unknown selector dependency ids: {', '.join(unknown)}")


def _parse_guideline_dsl_block(body: str) -> dict[str, object]:
    """Extract fields from a single guideline DSL block body.

    Shared by both the primary .providence/guidelines.dsl parsing path and the
    docs/spec/canonical fallback path (see _selector_canonical_fallback.py).
    """
    desc_match = re.search(r'description:\s*"([^"]*)"', body)
    cat_match = re.search(r"category:\s*(\w+)", body)
    type_match = re.search(r"\btype:\s*(HARD|SOFT)\b", body)
    tags_match = re.search(r"tags:\s*\[([^\]]*)\]", body)

    tags: list[str] | None = None
    if tags_match:
        raw = tags_match.group(1)
        tags = [t.strip().strip('"') for t in raw.split(",") if t.strip().strip('"')]

    return {
        "description": desc_match.group(1) if desc_match else None,
        "category": cat_match.group(1) if cat_match else None,
        "mandatory": (type_match.group(1) == "HARD") if type_match else None,
        "tags": tags,
        "depends_on": None,
    }
