"""Runtime status helpers: cache staleness check and footer drift mapping.

Split out of `runtime_handler.py` (T17,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any


def _check_cache_staleness(root: Path) -> dict[str, Any]:
    """Return staleness info for .providence/runtime/.providence-cache.md."""
    cache_file = root / ".providence" / "runtime" / ".providence-cache.md"
    if not cache_file.exists():
        return {"stale": False, "missing": True, "age_min": None}
    age = int(time.time() - cache_file.stat().st_mtime)
    return {"stale": age > 900, "missing": False, "age_min": age // 60}


def _footer_drift_status(drift_info: dict[str, Any]) -> str:
    """Map runtime drift payload to canonical compact footer drift status."""
    drift_type = str(drift_info.get("type", "none")).strip().lower() or "none"
    if bool(drift_info.get("detected")):
        return drift_type
    return "none"
