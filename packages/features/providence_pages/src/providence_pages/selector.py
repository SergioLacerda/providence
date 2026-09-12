"""Document indexing and selector generation for site navigation/search."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from providence_pages.metadata import MetadataExtractor

DEFAULT_GLOB = "**/*.md"
INDEX_SCHEMA_VERSION = "1.0"


@dataclass
class DocumentEntry:
    """A single indexed document."""

    path: str
    title: str
    url: str
    tags: list[str] = field(default_factory=list)
    date: str = ""
    category: str = ""


class SelectorGenerator:
    """Generates a stable DOM/navigation selector id for a document."""

    def generate(self, entry: DocumentEntry) -> str:
        """Return a CSS-id-safe selector derived from the document path."""
        slug = (
            entry.path.strip("/").replace("/", "-").replace(" ", "-").replace(".", "-")
        )
        slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
        return f"doc-{slug.lower()}" if slug else "doc-root"


class DocumentIndexer:
    """Walks a source directory and builds a document index."""

    def __init__(self, extractor: MetadataExtractor | None = None) -> None:
        self._extractor = extractor or MetadataExtractor()

    def index(self, source_dir: Path, glob: str = DEFAULT_GLOB) -> list[DocumentEntry]:
        """Index all matching documents under source_dir."""
        entries: list[DocumentEntry] = []
        for file_path in sorted(source_dir.glob(glob)):
            if not file_path.is_file():
                continue
            metadata = self._extractor.extract(file_path)
            rel_path = file_path.relative_to(source_dir).as_posix()
            title = metadata.title or file_path.stem
            category = str(metadata.raw.get("category", "")) if metadata.raw else ""
            entries.append(
                DocumentEntry(
                    path=rel_path,
                    title=title,
                    url=f"/{rel_path}",
                    tags=metadata.tags,
                    date=metadata.date,
                    category=category,
                )
            )
        return entries

    def to_json(self, entries: list[DocumentEntry], output_path: Path) -> Path:
        """Serialize the index to a JSON file with schema version and timestamp."""
        payload = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "documents": [asdict(e) for e in entries],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path

    def to_search_json(
        self, entries: list[DocumentEntry], source_dir: Path, output_path: Path
    ) -> Path:
        """Serialize an enriched search index that includes document body text."""
        docs = []
        for entry in entries:
            full_path = source_dir / entry.path
            body = ""
            if full_path.is_file():
                metadata = self._extractor.extract(full_path)
                body = metadata.body
            docs.append({**asdict(entry), "body": body})
        payload = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "documents": docs,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path
