"""Project root resolution and context archival helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _resolve_project_root_from_context(context: dict[str, Any]) -> Path:
    project_root_raw = context.get("_project_root", Path.cwd())
    return Path(project_root_raw)


def _safe_slug(value: str) -> str:
    normalized = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value
    )
    return normalized.strip("-") or "item"


def _archive_context_candidates(
    *,
    project_root: Path,
    context: dict[str, Any],
    archival_candidates: list[str],
) -> dict[str, Any]:
    archive_root = project_root / ".providence" / "runtime" / "context-archive"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_dir = archive_root / timestamp
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_items: list[dict[str, Any]] = []
    for key in archival_candidates:
        if key not in context:
            continue
        file_name = f"{_safe_slug(key)}.json"
        target = archive_dir / file_name
        payload = {"key": key, "value": context[key]}
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        archived_items.append(
            {"key": key, "path": target.relative_to(project_root).as_posix()}
        )

    ledger_summary = {
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "count": len(archived_items),
        "items": archived_items,
    }
    summary_path = archive_dir / "compression-summary.json"
    summary_path.write_text(
        json.dumps(ledger_summary, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return {
        "archive_dir": archive_dir.relative_to(project_root).as_posix(),
        "summary_path": summary_path.relative_to(project_root).as_posix(),
        "archived_items": archived_items,
    }
