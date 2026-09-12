"""YAML frontmatter metadata extraction for Markdown/HTML documents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class DocumentMetadata:
    """Structured metadata extracted from a document's YAML frontmatter."""

    title: str = ""
    description: str = ""
    date: str = ""
    tags: list[str] = field(default_factory=list)
    author: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    body: str = ""


class MetadataExtractor:
    """Extracts YAML frontmatter metadata from Markdown/HTML files."""

    def extract(self, path: Path) -> DocumentMetadata:
        """Extract metadata from a file on disk."""
        text = path.read_text(encoding="utf-8")
        return self.extract_from_text(text)

    def extract_from_text(self, text: str) -> DocumentMetadata:
        """Extract metadata from raw document text."""
        match = _FRONTMATTER_RE.match(text)
        if not match:
            return DocumentMetadata(body=text)

        frontmatter_raw = match.group(1)
        body = text[match.end() :]

        try:
            parsed = yaml.safe_load(frontmatter_raw)
        except yaml.YAMLError:
            return DocumentMetadata(body=body)

        if not isinstance(parsed, dict):
            return DocumentMetadata(body=body)

        tags = parsed.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = []

        return DocumentMetadata(
            title=str(parsed.get("title", "")),
            description=str(parsed.get("description", "")),
            date=str(parsed.get("date", "")),
            tags=[str(tag) for tag in tags],
            author=str(parsed.get("author", "")),
            raw=parsed,
            body=body,
        )
