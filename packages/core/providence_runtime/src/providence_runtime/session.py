"""Session lifecycle — state isolation per (workspace_id, agent_id, work_item_id)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover — fcntl is POSIX-only (no Windows)
    fcntl = None  # type: ignore[assignment]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


@dataclass
class SessionState:
    """Runtime session record.  Mandatory fields per §12.3 of the plan."""

    workspace_id: str
    agent_id: str
    work_item_id: str
    artifact_fingerprint: str
    schema_version: str
    policy_set_version: str
    parent_session_id: str | None = None
    decomposition_level: int = 0
    session_type: str = "long"  # "short" | "long"
    last_validation_ts: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, object]:
        """To Dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SessionState:
        """From Dict."""
        parent_id = data.get("parent_session_id")
        parent_session_id = str(parent_id) if isinstance(parent_id, str) else None

        raw_level = data.get("decomposition_level", 0)
        decomposition_level = int(raw_level) if isinstance(raw_level, int | str) else 0

        return cls(
            workspace_id=str(data.get("workspace_id", "")),
            agent_id=str(data.get("agent_id", "")),
            work_item_id=str(data.get("work_item_id", "")),
            artifact_fingerprint=str(data.get("artifact_fingerprint", "")),
            schema_version=str(data.get("schema_version", "")),
            policy_set_version=str(data.get("policy_set_version", "")),
            parent_session_id=parent_session_id,
            decomposition_level=decomposition_level,
            session_type=str(data.get("session_type", "long")),
            last_validation_ts=str(data.get("last_validation_ts", _utc_now())),
        )


class SessionManager:
    """In-memory session registry with optional file-based persistence.

    Parameters
    ----------
    state_dir:
        If provided, sessions are persisted as JSON under this directory.
        Allows warm-starts across process restarts within a work item.
    """

    _STATE_FILENAME = "providence-runtime-sessions.json"

    def __init__(self, state_dir: Path | None = None) -> None:
        self._sessions: dict[tuple[str, str, str], SessionState] = {}
        self._state_dir = state_dir
        if state_dir is not None:
            self._load_from_disk()

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def upsert(self, state: SessionState) -> SessionState:
        """Insert or replace a session.  Persists to disk if *state_dir* set.

        When persisted, this re-reads the on-disk sessions under an
        exclusive interprocess lock immediately before merging this single
        key and writing back (RUN-01,
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`) —
        `self._sessions` is otherwise only accurate as of construction time
        (or the last write from *this* process), so two processes each
        upserting a different session key would otherwise silently clobber
        one another on the last writer's `write_text()`.
        """
        key = self._key(state)
        self._sessions[key] = state
        if self._state_dir is not None:
            self._persist_key(key, state)
        return state

    def get(
        self, workspace_id: str, agent_id: str, work_item_id: str
    ) -> SessionState | None:
        """Return the session for the given workspace/agent/work item key."""
        return self._sessions.get((workspace_id, agent_id, work_item_id))

    def is_bound_to_fingerprint(
        self,
        workspace_id: str,
        agent_id: str,
        work_item_id: str,
        artifact_fingerprint: str,
    ) -> bool:
        """Return True iff the session exists and is bound to *artifact_fingerprint*."""
        state = self.get(workspace_id, agent_id, work_item_id)
        if state is None:
            return False
        return state.artifact_fingerprint == artifact_fingerprint

    def delete(self, workspace_id: str, agent_id: str, work_item_id: str) -> bool:
        """Remove a session.  Returns True if it existed."""
        key = (workspace_id, agent_id, work_item_id)
        existed = key in self._sessions
        if existed:
            del self._sessions[key]
            if self._state_dir is not None:
                self._persist_key(key, None)
        return existed

    def all_sessions(self) -> list[SessionState]:
        """All Sessions."""
        return list(self._sessions.values())

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def save(self) -> None:
        """Explicitly persist all in-memory sessions to disk, one key at a time.

        No-op when *state_dir* was not provided. Each key is merged under
        the same interprocess lock as `upsert`/`delete`, so this cannot
        silently clobber a concurrent process's update to a session this
        instance never loaded.
        """
        if self._state_dir is None:
            return
        for key, state in list(self._sessions.items()):
            self._persist_key(key, state)

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _key(state: SessionState) -> tuple[str, str, str]:
        return (state.workspace_id, state.agent_id, state.work_item_id)

    def _state_file(self) -> Path:
        if self._state_dir is None:
            raise RuntimeError("SessionManager state_dir is required for persistence")
        return self._state_dir / self._STATE_FILENAME

    def _lock_file(self) -> Path:
        return self._state_file().with_suffix(self._state_file().suffix + ".lock")

    def _persist_key(
        self, key: tuple[str, str, str], state: SessionState | None
    ) -> None:
        """Merge one key's change into the on-disk sessions and write atomically.

        Held under an exclusive advisory lock (POSIX `fcntl.flock`, degrading
        to unlocked best-effort where `fcntl` is unavailable, e.g. Windows)
        for the full read-merge-write cycle, so a concurrent process's write
        to a *different* key is re-read fresh rather than overwritten by
        this process's possibly-stale in-memory view (RUN-01). `state=None`
        deletes the key. The write itself goes to a PID-suffixed temp file
        and is atomically renamed into place, so a crash mid-write never
        leaves a partially written JSON file for the next reader.
        """
        if self._state_dir is None:
            raise RuntimeError("SessionManager state_dir is required for persistence")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self._lock_file()
        with open(lock_path, "a+", encoding="utf-8") as lock_fh:
            if fcntl is not None:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                on_disk = self._read_sessions_dict(self._state_file())
                if state is None:
                    on_disk.pop(key, None)
                else:
                    on_disk[key] = state
                self._sessions = on_disk
                self._write_sessions_atomically(on_disk)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    def _write_sessions_atomically(
        self, sessions: dict[tuple[str, str, str], SessionState]
    ) -> None:
        data = [s.to_dict() for s in sessions.values()]
        target = self._state_file()
        tmp_path = target.with_suffix(target.suffix + f".tmp-{os.getpid()}")
        tmp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(tmp_path, target)

    @staticmethod
    def _read_sessions_dict(path: Path) -> dict[tuple[str, str, str], SessionState]:
        if not path.exists():
            return {}
        try:
            raw: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
            return {
                SessionManager._key(state): state
                for state in (SessionState.from_dict(entry) for entry in raw)
            }
        except (json.JSONDecodeError, KeyError):
            # Corrupt state file — start clean; do not crash.
            return {}

    def _load_from_disk(self) -> None:
        self._sessions = self._read_sessions_dict(self._state_file())
