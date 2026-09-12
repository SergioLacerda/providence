"""Routing-decision cache for `providence ask`.

Split out of `ask_context.py` (T8,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providence_cli.services.ask_context_drift import (
    _read_runtime_state,
    compute_routing_signature,
)
from providence_cli.services.ask_context_snapshot import _SNAPSHOT_CACHE_MAX_ENTRIES
from providence_cli.services.ask_governance_state_cache import (
    _load_governance_state,
    _store_governance_state,
)

logger = logging.getLogger(__name__)

_ROUTING_CACHE_MAX_ENTRIES = 20


def get_cached_routing_decision(
    workspace_root: Path, signature: str
) -> dict[str, Any] | None:
    """Return a previously cached routing decision for `signature`, if present."""
    decisions = _read_runtime_state(workspace_root).get("last_routing_decisions") or {}
    cached = decisions.get(signature)
    return cached if isinstance(cached, dict) else None


def resolve_routing_decision(
    workspace_root: Path, query: str, skill: str | None
) -> dict[str, Any] | None:
    """Return a cached routing decision for `query`/`skill`, if one applies.

    Keyed by the fingerprint recorded by the previous `providence ask` call. Returns
    None on cold start (no prior call recorded), so a decision is never
    cached against an empty/unknown fingerprint  the first call for a
    workspace always runs the routing heuristics for real.

    Reads `governance-state.json` once (not via `get_last_known_fingerprint`
    + `get_cached_routing_decision` separately, which would each re-read the
    file)  design.md D4 flags redundant reads of this file as an
    inefficiency to avoid, and this lookup previously did two on every call.
    """
    state = _read_runtime_state(workspace_root)
    last_ask = state.get("last_ask") or {}
    fingerprint = str(last_ask.get("compiled_fingerprint_used", "")).strip()
    if not fingerprint:
        return None
    signature = compute_routing_signature(query, skill, fingerprint)
    decisions = state.get("last_routing_decisions") or {}
    cached = decisions.get(signature)
    return cached if isinstance(cached, dict) else None


def store_routing_decision(
    workspace_root: Path,
    query: str,
    skill: str | None,
    fingerprint: str,
    decision: dict[str, Any],
) -> None:
    """Persist a routing decision, capped to the most recent entries.

    Keyed by the fingerprint actually loaded for this call (not the
    last-known one used for lookup), so the cache self-heals on the next
    call after a governance change instead of perpetuating a stale entry.
    """
    if not fingerprint:
        return
    signature = compute_routing_signature(query, skill, fingerprint)
    try:
        data = _load_governance_state(workspace_root)
        decisions = data.get("last_routing_decisions")
        if not isinstance(decisions, dict):
            decisions = {}
        decisions[signature] = {
            **decision,
            "computed_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }
        if len(decisions) > _ROUTING_CACHE_MAX_ENTRIES:
            ordered = sorted(
                decisions.items(),
                key=lambda item: item[1].get("computed_at", ""),
                reverse=True,
            )
            decisions = dict(ordered[:_ROUTING_CACHE_MAX_ENTRIES])
        data["last_routing_decisions"] = decisions
        _store_governance_state(
            workspace_root, data, changed_keys={"last_routing_decisions"}
        )
    except Exception as exc:
        logger.debug("Failed to update routing decision cache: %s", exc)


def write_runtime_cache_and_routing_decision(
    workspace_root: Path,
    last_ask: dict[str, Any],
    query: str,
    skill: str | None,
    fingerprint: str,
    routing_decision: dict[str, Any],
    governance_snapshot: dict[str, Any] | None = None,
) -> None:
    """Persist `last_ask`, a routing decision, and a governance snapshot in one write.

    `write_runtime_cache` + `store_routing_decision` always run back-to-back
    at the end of a `providence ask` call and each independently reads/writes
    `governance-state.json`  two reads and two writes for state that is
    always updated together. This combines them into one read + one write
    (design.md D4). `write_runtime_cache` and `store_routing_decision` are
    kept as-is for other callers/tests  they now share the same
    per-process `_load_governance_state`/`_store_governance_state` cache
    (design.md D-01), so calling them elsewhere in the same process no
    longer reintroduces a redundant disk read either.

    `governance_snapshot`, when supplied, is persisted under `snapshot_cache`
    the same way `store_governance_snapshot` does standalone (design.md D-A)
    folded into this same write rather than opening a third read/write path.
    """
    try:
        data = _load_governance_state(workspace_root)
        data["last_ask"] = last_ask
        changed_keys = {"last_ask"}
        if fingerprint:
            signature = compute_routing_signature(query, skill, fingerprint)
            decisions = data.get("last_routing_decisions")
            if not isinstance(decisions, dict):
                decisions = {}
            decisions[signature] = {
                **routing_decision,
                "computed_at": datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
            }
            if len(decisions) > _ROUTING_CACHE_MAX_ENTRIES:
                ordered = sorted(
                    decisions.items(),
                    key=lambda item: item[1].get("computed_at", ""),
                    reverse=True,
                )
                decisions = dict(ordered[:_ROUTING_CACHE_MAX_ENTRIES])
            data["last_routing_decisions"] = decisions
            changed_keys.add("last_routing_decisions")
            if governance_snapshot is not None:
                snapshots = data.get("snapshot_cache")
                if not isinstance(snapshots, dict):
                    snapshots = {}
                snapshots[fingerprint] = {
                    "snapshot": governance_snapshot,
                    "computed_at": datetime.now(timezone.utc)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z"),
                }
                if len(snapshots) > _SNAPSHOT_CACHE_MAX_ENTRIES:
                    ordered_snapshots = sorted(
                        snapshots.items(),
                        key=lambda item: item[1].get("computed_at", ""),
                        reverse=True,
                    )
                    snapshots = dict(ordered_snapshots[:_SNAPSHOT_CACHE_MAX_ENTRIES])
                data["snapshot_cache"] = snapshots
                changed_keys.add("snapshot_cache")
        _store_governance_state(workspace_root, data, changed_keys=changed_keys)
    except Exception as exc:
        logger.debug("Failed to update runtime cache/routing decision: %s", exc)
