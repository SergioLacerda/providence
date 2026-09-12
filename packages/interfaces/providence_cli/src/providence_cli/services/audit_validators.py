"""Audit validation: legacy path policy checks and bootstrap drift detection."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _legacy_policy_mode(today: date) -> str:
    if today >= date(2026, 10, 1):
        return "block"
    if today >= date(2026, 7, 1):
        return "warn"
    return "monitor"


def _scan_legacy_paths(root: Path) -> list[str]:
    patterns = [
        re.compile(r"/legacy/"),
        re.compile(r"\blegacy/"),
        re.compile(r"generated/master/compiled"),
    ]
    hits: list[str] = []
    candidates: list[Path] = []
    candidates.extend(
        [
            root / "AGENTS.md",
            root / "README.md",
            root / "Makefile",
            root / "pyproject.toml",
        ]
    )
    candidates.extend((root / ".providence").rglob("*.md"))
    candidates.extend((root / ".providence").rglob("*.json"))
    candidates.extend((root / ".providence").rglob("*.yaml"))
    candidates.extend((root / ".providence").rglob("*.yml"))
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for pattern in patterns:
            if pattern.search(content):
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    rel = path
                hits.append(str(rel))
                break
    return sorted(hits)


def _bootstrap_drift(root: Path) -> dict[str, Any]:
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    drift: list[str] = []
    if not agents.exists():
        drift.append("AGENTS.md missing")
    else:
        text = agents.read_text(encoding="utf-8")
        if ".providence/agent-instructions.md" not in text:
            drift.append("AGENTS.md missing .providence authority reference")
        if "./CLAUDE.md" not in text:
            drift.append("AGENTS.md missing Claude bootstrap path")
    if not claude.exists():
        drift.append("CLAUDE.md missing")
    else:
        ctext = claude.read_text(encoding="utf-8")
        if ".providence/agent-instructions.md" not in ctext:
            drift.append("CLAUDE.md not pointing to .providence/agent-instructions.md")
    if (root / ".claude" / "agent-instructions.md").exists():
        drift.append("parallel authority file exists at .claude/agent-instructions.md")
    return {"ok": not drift, "issues": drift}


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_legacy_check(root: Path, check_day: date) -> dict[str, Any]:
    """Return legacy check result dict with policy_mode, date, and hits."""
    hits = _scan_legacy_paths(root)
    mode = _legacy_policy_mode(check_day)
    return {"policy_mode": mode, "date": check_day.isoformat(), "hits": hits}


def run_bootstrap_check(root: Path) -> dict[str, Any]:
    """Return bootstrap drift result dict with ok and issues."""
    return _bootstrap_drift(root)


def current_policy_date() -> date:
    """Return today's UTC date for policy evaluation."""
    return datetime.now(timezone.utc).date()
