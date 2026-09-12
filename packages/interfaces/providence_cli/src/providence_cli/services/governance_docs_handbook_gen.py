"""Runtime handbook generation from the docs-source registry.

Split out of `governance_docs_sources.py` (T7,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from providence_cli.services.governance_docs_sources import (
    DEFAULT_HANDBOOK_DIR,
    DEFAULT_REGISTRY,
    _active,
    _entry_ids,
    _load_yaml,
    _source_entries,
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else {}


def _heading(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def generate_runtime_handbook(
    root: Path,
    registry_path: Path | None = None,
    output_dir: Path | None = None,
    runtime_root: Path | None = None,
) -> list[Path]:
    """Generate selective runtime handbook entries from docs-source registry."""
    registry_file = root / (registry_path or DEFAULT_REGISTRY)
    if not registry_file.exists():
        return []
    registry = _load_yaml(registry_file)
    target_root = runtime_root or root
    handbook_root = target_root / (output_dir or DEFAULT_HANDBOOK_DIR)
    written: list[Path] = []
    index_items: list[dict[str, Any]] = []

    for entry in _source_entries(registry):
        if str(entry.get("type", "")).lower() != "handbook" or not _active(entry):
            continue
        source_path = root / str(entry["path"])
        metadata = _frontmatter(source_path).get("governance_source", {})
        if not isinstance(metadata, dict):
            metadata = {}
        source_id = _entry_ids(entry)[0]
        outputs = [str(item) for item in entry.get("outputs", [])]
        target = next(
            (
                target_root / item
                for item in outputs
                if item.startswith(".providence/source/handbook/")
            ),
            handbook_root / f"{source_id.lower()}.yaml",
        )
        item = {
            "id": source_id,
            "title": metadata.get("title")
            or entry.get("title")
            or _heading(source_path),
            "kind": entry.get("kind") or metadata.get("kind", "reference"),
            "status": entry.get("status", metadata.get("status", "active")),
            "source_doc": str(entry["path"]),
            "mandate_refs": list(entry.get("refs", metadata.get("refs", []))),
            "task_types": list(entry.get("task_types", metadata.get("task_types", []))),
            "operation_phases": list(
                entry.get("operation_phases", metadata.get("operation_phases", []))
            ),
            # CTX-08 (`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
            # the lookup filters matches by `risk_levels`, but this generator
            # never wrote the field, so any risk_level filter matched
            # nothing. Sourced the same way as the sibling filter fields
            # above (entry override, falling back to frontmatter metadata).
            "risk_levels": list(
                entry.get("risk_levels", metadata.get("risk_levels", []))
            ),
            "load_policy": entry.get("load_policy", metadata.get("load_policy", {})),
            "summary": metadata.get("summary", ""),
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(item, sort_keys=False), encoding="utf-8")
        written.append(target)
        index_items.append(
            {
                "id": item["id"],
                "title": item["title"],
                "source_doc": item["source_doc"],
                "runtime_doc": str(target.relative_to(target_root)),
                "mandate_refs": item["mandate_refs"],
                "task_types": item["task_types"],
                "operation_phases": item["operation_phases"],
                "risk_levels": item["risk_levels"],
            }
        )

    handbook_root.mkdir(parents=True, exist_ok=True)
    index_path = handbook_root / "index.yaml"
    index_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1",
                "generated_from": str(registry_file.relative_to(root)),
                "items": index_items,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    written.append(index_path)
    return written
