"""Delta indexing: change detection via git diff and hash-based cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

from providence_core.utils.process import SafeProcessRunner
from providence_pages.selector import DocumentEntry, DocumentIndexer


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_cache(cache_path: Path) -> dict[str, str]:
    if not cache_path.exists():
        return {}
    try:
        return cast(dict[str, str], json.loads(cache_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, str], cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


class DeltaIndexer:
    """Indexes only changed files by comparing git diff or file hashes."""

    def __init__(self, indexer: DocumentIndexer | None = None) -> None:
        self._indexer = indexer or DocumentIndexer()

    def changed_files(self, source_dir: Path, base_ref: str = "HEAD~1") -> list[Path]:
        """Return paths under source_dir that changed since base_ref (git diff)."""
        try:
            runner = SafeProcessRunner()
            result = runner.run(
                ["git", "diff", "--name-only", base_ref, "HEAD", "--", str(source_dir)],
                capture_output=True,
            )
            if not result.success:
                return []
            changed: list[Path] = []
            for line in result.stdout.splitlines():
                path = Path(line.strip())
                if path.is_file():
                    changed.append(path)
            return changed
        except Exception:
            return []

    def incremental_index(
        self,
        source_dir: Path,
        existing_entries: list[DocumentEntry],
        base_ref: str = "HEAD~1",
        glob: str = "**/*.md",
    ) -> list[DocumentEntry]:
        """Return a merged index: re-index changed files, keep the rest unchanged."""
        changed = {p.as_posix() for p in self.changed_files(source_dir, base_ref)}
        if not changed:
            return existing_entries

        existing_by_path = {e.path: e for e in existing_entries}

        updated_paths = {
            file_path.relative_to(source_dir).as_posix()
            for file_path in source_dir.glob(glob)
            if file_path.is_file()
            and any(
                str(file_path).endswith(c) or c.endswith(str(file_path))
                for c in changed
            )
        }

        fresh = self._indexer.index(source_dir, glob=glob)
        fresh_by_path = {e.path: e for e in fresh}

        merged: dict[str, DocumentEntry] = {}
        for path, entry in existing_by_path.items():
            merged[path] = (
                fresh_by_path.get(path, entry) if path in updated_paths else entry
            )
        for path, entry in fresh_by_path.items():
            if path not in merged:
                merged[path] = entry

        return sorted(merged.values(), key=lambda e: e.path)

    def cached_index(
        self,
        source_dir: Path,
        output_path: Path,
        cache_path: Path,
        glob: str = "**/*.md",
    ) -> tuple[list[DocumentEntry], bool]:
        """Return (entries, was_cached).

        If no files changed since last run (per hash cache), reload the
        existing output_path without re-indexing. Otherwise re-index and
        update the cache.
        """
        cache = _load_cache(cache_path)
        current_hashes: dict[str, str] = {}
        for file_path in sorted(source_dir.glob(glob)):
            if file_path.is_file():
                rel = file_path.relative_to(source_dir).as_posix()
                current_hashes[rel] = _sha256(file_path)

        if cache == current_hashes and output_path.exists():
            try:
                data = json.loads(output_path.read_text(encoding="utf-8"))
                entries = [DocumentEntry(**d) for d in data.get("documents", [])]
                return entries, True
            except (json.JSONDecodeError, TypeError, OSError):
                pass

        entries = self._indexer.index(source_dir, glob=glob)
        _save_cache(current_hashes, cache_path)
        return entries, False
