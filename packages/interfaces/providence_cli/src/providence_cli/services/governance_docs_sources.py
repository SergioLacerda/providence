"""Docs-source registry validation and runtime handbook generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY = Path("docs/spec/canonical/governance-sources.yaml")
DEFAULT_HANDBOOK_DIR = Path(".providence/source/handbook")
RUNTIME_TYPES = {"mandate", "guideline"}
ALLOWED_TYPES = RUNTIME_TYPES | {
    "policy",
    "rule",
    "handbook",
    "feature",
    "docs_only",
    "mirror",
}


@dataclass(frozen=True)
class DocsSourceReport:
    """Structured result for docs governance source validation."""

    ok: bool
    errors: list[str]
    warnings: list[str]
    mandate_ids: list[str]
    guideline_ids: list[str]
    handbook_ids: list[str]


@dataclass(frozen=True)
class HandbookLookupReport:
    """Runtime handbook lookup result for consultive guidance."""

    status: str
    diagnostic: str
    matches: list[dict[str, Any]]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _source_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("sources", [])
    return [entry for entry in entries if isinstance(entry, dict)]


def _entry_ids(entry: dict[str, Any]) -> list[str]:
    raw_ids = entry.get("ids", entry.get("id"))
    if isinstance(raw_ids, str):
        return [raw_ids]
    if isinstance(raw_ids, list):
        return [str(item) for item in raw_ids if str(item).strip()]
    return []


def _active(entry: dict[str, Any]) -> bool:
    return str(entry.get("status", "active")).lower() == "active"


def _load_runtime_ids(root: Path, relative_path: str, item_type: str) -> set[str]:
    path = root / relative_path
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("id"))
        for item in items
        if isinstance(item, dict) and str(item.get("type", "")).upper() == item_type
    }


def _metadata_mandate_ids(root: Path) -> set[str]:
    path = root / ".providence/metadata.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    mandates = data.get("mandates", {})
    if isinstance(mandates, dict):
        return set(str(key) for key in mandates)
    return set()


def _add_duplicate_errors(
    errors: list[str], seen: dict[str, str], entry: dict[str, Any], source_type: str
) -> None:
    path = str(entry.get("path", ""))
    for source_id in _entry_ids(entry):
        previous = seen.get(source_id)
        if previous is not None:
            errors.append(
                f"duplicate active {source_type} id {source_id}: {previous} and {path}"
            )
        seen[source_id] = path


def _validate_entry_shape(
    root: Path, entry: dict[str, Any], errors: list[str], warnings: list[str]
) -> None:
    source_type = str(entry.get("type", "")).lower()
    if source_type not in ALLOWED_TYPES:
        errors.append(f"unsupported source type {source_type!r} for {entry.get('id')}")
    ids = _entry_ids(entry)
    if not ids:
        errors.append(f"source entry missing id/ids for path {entry.get('path')}")
    _validate_entry_path(root, entry, ids, errors)
    _validate_entry_type_contract(entry, ids, source_type, errors, warnings)


def _validate_entry_path(
    root: Path, entry: dict[str, Any], ids: list[str], errors: list[str]
) -> None:
    relative_path = str(entry.get("path", "")).strip()
    if not relative_path:
        errors.append(f"source entry {ids or ['<unknown>']} missing path")
    elif not (root / relative_path).exists():
        errors.append(f"source path does not exist: {relative_path}")


def _validate_entry_type_contract(
    entry: dict[str, Any],
    ids: list[str],
    source_type: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not ids:
        return
    if source_type == "docs_only" and entry.get("outputs"):
        outputs = [str(item) for item in entry.get("outputs", [])]
        runtime_outputs = [item for item in outputs if item.startswith(".providence/")]
        if runtime_outputs:
            errors.append(f"docs_only source {ids[0]} declares runtime outputs")
    if source_type == "mirror" and not entry.get("source_doc"):
        errors.append(f"mirror source {ids[0]} must declare source_doc")
    if source_type == "handbook" and _active(entry):
        has_refs = bool(
            entry.get("refs")
            or entry.get("task_types")
            or entry.get("operation_phases")
        )
        if not has_refs:
            errors.append(f"handbook source {ids[0]} needs refs, task_types, or phases")
        load_policy = entry.get("load_policy", {})
        if not isinstance(load_policy, dict) or "max_tokens" not in load_policy:
            errors.append(f"handbook source {ids[0]} needs load_policy.max_tokens")
    if source_type in RUNTIME_TYPES and not entry.get("outputs"):
        warnings.append(f"runtime source {ids[0]} has no declared outputs")


def _collect_active_source_ids(
    root: Path,
    entries: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    mandate_seen: dict[str, str] = {}
    guideline_seen: dict[str, str] = {}
    handbook_ids: list[str] = []

    for entry in entries:
        _validate_entry_shape(root, entry, errors, warnings)
        source_type = str(entry.get("type", "")).lower()
        if not _active(entry):
            continue
        if source_type == "mandate":
            _add_duplicate_errors(errors, mandate_seen, entry, source_type)
        elif source_type == "guideline":
            _add_duplicate_errors(errors, guideline_seen, entry, source_type)
        elif source_type == "handbook":
            handbook_ids.extend(_entry_ids(entry))

    return mandate_seen, guideline_seen, handbook_ids
