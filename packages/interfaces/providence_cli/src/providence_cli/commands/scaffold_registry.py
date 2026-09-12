"""Scaffold  registry.json append helper.

Split out of `scaffold.py` (T18,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import json
from pathlib import Path


def _append_to_registry(registry_path: Path, entry: dict[str, object]) -> None:
    data = (
        json.loads(registry_path.read_text(encoding="utf-8"))
        if registry_path.exists()
        else {}
    )
    key = "skills" if "skills" in data else "commands"
    items: list[dict[str, object]] = data.get(key, [])
    if not any(
        i.get("name") == entry.get("name") or i.get("id") == entry.get("id")
        for i in items
    ):
        items.append(entry)
    data[key] = items
    registry_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
