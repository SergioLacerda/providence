"""Compiled-governance snapshot cache for `providence ask`.

Split out of `ask_context.py` (T8,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_cli.services.ask_governance_state_cache import (
    _load_governance_state,
    _store_governance_state,
)

logger = logging.getLogger(__name__)

_SNAPSHOT_CACHE_MAX_ENTRIES = 20
_SNAPSHOT_CACHE_TTL_SECONDS = 300


def get_cached_governance_snapshot(
    workspace_root: Path, fingerprint: str
) -> dict[str, Any] | None:
    """Return a cached compiled-governance snapshot for `fingerprint`, if still fresh.

    Keyed by fingerprint only  the cached fields (`context_source`,
    `mandates_count`, `authenticated`, `degraded`, `degrade_reason`,
    `trust_source`) are a pure function of the compiled governance state for a
    given fingerprint, mirroring the in-process `_GOV_CACHE` but persisted to
    disk so it survives across separate `providence ask` processes (design.md D-A).

    Bounded by a TTL (mirroring `ContextLoader`'s own 5-minute TTL) rather than
    relying on fingerprint match alone: the lookup fingerprint here is the
    *last-known* one recorded in `governance-state.json`, not a freshly
    reloaded one  skipping the real compiled-governance load on every hit
    means a recompile would otherwise never be detected. The TTL bounds how
    long a cache hit can go without forcing a fresh load, so staleness after a
    recompile is capped at `_SNAPSHOT_CACHE_TTL_SECONDS`, not unbounded.
    """
    if not fingerprint:
        return None
    entry = (
        _load_governance_state(workspace_root)
        .get("snapshot_cache", {})
        .get(fingerprint)
    )
    if not isinstance(entry, dict):
        return None
    computed_at = entry.get("computed_at")
    if not computed_at:
        return None
    try:
        computed_dt = datetime.fromisoformat(str(computed_at).replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - computed_dt).total_seconds()
    except (ValueError, TypeError):
        return None
    if age_seconds > _SNAPSHOT_CACHE_TTL_SECONDS:
        return None
    snapshot = entry.get("snapshot")
    return snapshot if isinstance(snapshot, dict) else None


def store_governance_snapshot(
    workspace_root: Path, fingerprint: str, snapshot: dict[str, Any]
) -> None:
    """Persist a compiled-governance snapshot, capped to the most recent entries."""
    if not fingerprint:
        return
    try:
        data = _load_governance_state(workspace_root)
        entries = data.get("snapshot_cache")
        if not isinstance(entries, dict):
            entries = {}
        entries[fingerprint] = {
            "snapshot": snapshot,
            "computed_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }
        if len(entries) > _SNAPSHOT_CACHE_MAX_ENTRIES:
            ordered = sorted(
                entries.items(),
                key=lambda item: item[1].get("computed_at", ""),
                reverse=True,
            )
            entries = dict(ordered[:_SNAPSHOT_CACHE_MAX_ENTRIES])
        data["snapshot_cache"] = entries
        _store_governance_state(workspace_root, data, changed_keys={"snapshot_cache"})
    except Exception as exc:
        logger.debug("Failed to update governance snapshot cache: %s", exc)
