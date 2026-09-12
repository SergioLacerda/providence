"""Shared `governance-state.json` read/write cache for `providence ask` runtime modules.

Split out of `ask_context.py`: `ask_context_drift`, `ask_context_routing`, and
`ask_context_snapshot` all need this cache but `ask_context` itself does not,
and `ask_context_drift` importing it from `ask_context` created a cycle once
`ask_context` needed `ask_context_drift` in turn.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover  fcntl is POSIX-only (no Windows)
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_STATE_CACHE: dict[str, dict[str, Any]] = {}
# mtime_ns of the file as of the last `_load_governance_state` disk read, per
# workspace  lets `_store_governance_state` detect a concurrent writer with
# a cheap `stat()` instead of unconditionally re-reading (see RUN-01 note
# on `_store_governance_state` below).
_STATE_MTIME_CACHE: dict[str, tuple[int, int]] = {}


def _load_governance_state(workspace_root: Path) -> dict[str, Any]:
    """Read+parse `governance-state.json` at most once per process per workspace.

    `check_fingerprint_drift`, `write_runtime_cache`, `_read_runtime_state`,
    `store_routing_decision`, and `write_runtime_cache_and_routing_decision`
    all share this cache so a single `providence ask` call does one disk read of
    this file instead of one per call site (design.md D-01). Only a
    successful write via `_store_governance_state` may refresh a cache entry.
    """
    key = str(workspace_root.resolve())
    cached = _STATE_CACHE.get(key)
    if cached is not None:
        return cached
    state_path = workspace_root / ".providence" / "runtime" / "governance-state.json"
    data: dict[str, Any] = {}
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            stat = state_path.stat()
            _STATE_MTIME_CACHE[key] = (stat.st_mtime_ns, stat.st_size)
        except Exception:
            data = {}
    else:
        _STATE_MTIME_CACHE[key] = (0, 0)
    _STATE_CACHE[key] = data
    return data


def _store_governance_state(
    workspace_root: Path,
    data: dict[str, Any],
    *,
    changed_keys: set[str] | None = None,
) -> None:
    """Write `governance-state.json` and refresh the shared in-process cache.

    RUN-01 (`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
    the write is now atomic (temp file + `os.replace`) so an interrupted
    write never leaves a partially written JSON file for the next reader.

    When `changed_keys` is given, the write is also concurrency-safe across
    processes, held under an exclusive interprocess lock, using an
    optimistic-concurrency check (the finding's own "comparao de verso"
    option) rather than an unconditional re-read: if the file's mtime still
    matches what `_load_governance_state` observed, nothing else has
    written since, so `data` is still accurate and is written as-is  no
    extra disk read, preserving design.md D-01's one-read-per-call
    guarantee in the common (uncontended) case. Only when the mtime has
    moved (a concurrent process wrote in between) does this re-read the
    file fresh and merge just the named top-level keys from `data` onto
    it  every other top-level key then comes from that fresh read, not
    from `data`'s stale copy. Without `changed_keys` (back-compat default),
    the full `data` dict is written as-is unconditionally  callers that
    read-mutate-write the whole blob without declaring which keys they
    actually changed keep the pre-existing behavior, still gaining the
    atomic-write guarantee.
    """
    state_path = workspace_root / ".providence" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    key = str(workspace_root.resolve())

    if changed_keys is None:
        _write_json_atomically(state_path, data)
        _STATE_CACHE[key] = data
        stat = state_path.stat()
        _STATE_MTIME_CACHE[key] = (stat.st_mtime_ns, stat.st_size)
        return

    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    with open(lock_path, "a+", encoding="utf-8") as lock_fh:
        if fcntl is not None:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            observed_mtime = _STATE_MTIME_CACHE.get(key)
            if state_path.exists():
                stat = state_path.stat()
                current_mtime = (stat.st_mtime_ns, stat.st_size)
            else:
                current_mtime = (0, 0)
            if observed_mtime is not None and observed_mtime == current_mtime:
                to_write = data
            else:
                to_write = _read_json_best_effort(state_path)
                for changed_key in changed_keys:
                    if changed_key in data:
                        to_write[changed_key] = data[changed_key]
            _write_json_atomically(state_path, to_write)
            _STATE_CACHE[key] = to_write
            stat = state_path.stat()
            _STATE_MTIME_CACHE[key] = (stat.st_mtime_ns, stat.st_size)
        finally:
            if fcntl is not None:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def _read_json_best_effort(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return {}


def _write_json_atomically(path: Path, data: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    tmp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(tmp_path, path)
