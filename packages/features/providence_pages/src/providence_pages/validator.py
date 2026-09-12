"""Index validation: checks that a docs.index.json is well-formed and consistent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from providence_pages.selector import INDEX_SCHEMA_VERSION

# Compatibility policy: "1.0" is the only currently produced and understood version.
# Indexes with a different schema_version receive a warning (not an error) so
# forward-compatibility is preserved when producers upgrade ahead of consumers.
# If breaking changes are introduced, add the new version here and add a migration
# path before removing the old version from this set.
_SUPPORTED_SCHEMA_VERSIONS = frozenset({INDEX_SCHEMA_VERSION})

_REQUIRED_ENTRY_FIELDS = ("path", "title", "url")


@dataclass
class ValidationResult:
    """Outcome of validating a docs.index.json file."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IndexValidator:
    """Validates a generated docs.index.json against its source directory."""

    def validate(
        self,
        index_path: Path,
        source_dir: Path | None = None,
    ) -> ValidationResult:
        """Validate the index at index_path.

        If source_dir is provided, verify that each indexed document path exists.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not index_path.exists():
            return ValidationResult(
                valid=False, errors=[f"Index file not found: {index_path}"]
            )

        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return ValidationResult(valid=False, errors=[f"Invalid JSON: {exc}"])

        if not isinstance(data, dict):
            return ValidationResult(valid=False, errors=["Index must be a JSON object"])

        schema_version = data.get("schema_version")
        if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            warnings.append(
                f"schema_version '{schema_version}' is not in supported versions "
                f"{sorted(_SUPPORTED_SCHEMA_VERSIONS)}; index may not be readable by this validator"
            )

        documents = data.get("documents")
        if not isinstance(documents, list):
            errors.append("'documents' must be a JSON array")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        for i, entry in enumerate(documents):
            self._validate_entry(i, entry, source_dir, errors, warnings)

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_entry(
        self,
        index: int,
        entry: object,
        source_dir: Path | None,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate a single document entry, appending to errors/warnings in place."""
        if not isinstance(entry, dict):
            errors.append(f"Entry [{index}] is not an object")
            return

        for field_name in _REQUIRED_ENTRY_FIELDS:
            if not entry.get(field_name):
                errors.append(f"Entry [{index}] missing required field: '{field_name}'")

        if source_dir is not None:
            rel_path = entry.get("path", "")
            if rel_path and not (source_dir / rel_path).exists():
                warnings.append(f"Entry [{index}] path not found on disk: {rel_path}")
