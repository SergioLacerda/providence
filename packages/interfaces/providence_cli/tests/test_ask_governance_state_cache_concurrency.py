"""RUN-01 regression tests for `ask_governance_state_cache`'s write safety.

`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` RUN-01:
`governance-state.json` was rewritten wholesale with a plain `write_text`,
with no atomic write and no protection against a concurrent process's
in-between write to a *different* top-level key being silently clobbered.
"""

from __future__ import annotations

import json
from pathlib import Path

from providence_cli.services import ask_governance_state_cache as cache_mod


def _reset_module_caches() -> None:
    cache_mod._STATE_CACHE.clear()
    cache_mod._STATE_MTIME_CACHE.clear()


def test_concurrent_writers_to_different_keys_both_preserved(tmp_path: Path) -> None:
    """Two separate 'processes' (simulated by clearing the module-level
    caches in between, since the real cache is per-process) each load state,
    then each write a *different* top-level key  both must survive."""
    _reset_module_caches()

    data_a = cache_mod._load_governance_state(tmp_path)
    data_a["last_ask"] = {"compiled_fingerprint_used": "fp-a"}
    cache_mod._store_governance_state(tmp_path, data_a, changed_keys={"last_ask"})

    # Simulate a second process: fresh caches, loads state written by "A".
    _reset_module_caches()
    data_b = cache_mod._load_governance_state(tmp_path)
    assert data_b["last_ask"]["compiled_fingerprint_used"] == "fp-a"

    # "A" (in reality, could be a still-running process) writes again to a
    # DIFFERENT key without "B" knowing  simulated by mutating the file
    # directly, out from under B's already-loaded (now stale) `data_b`.
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    on_disk = json.loads(state_path.read_text(encoding="utf-8"))
    on_disk["last_routing_decisions"] = {"sig-1": {"organize_used": True}}
    state_path.write_text(json.dumps(on_disk), encoding="utf-8")

    # "B" now writes its own key. Its `data_b` dict does not know about
    # `last_routing_decisions` at all (it wasn't present when B loaded), so
    # the on-disk write must not lose it.
    data_b["snapshot_cache"] = {"fp-x": {"snapshot": {}}}
    cache_mod._store_governance_state(tmp_path, data_b, changed_keys={"snapshot_cache"})

    _reset_module_caches()
    final = cache_mod._load_governance_state(tmp_path)
    assert final["last_ask"]["compiled_fingerprint_used"] == "fp-a"
    assert final["last_routing_decisions"] == {"sig-1": {"organize_used": True}}
    assert final["snapshot_cache"] == {"fp-x": {"snapshot": {}}}


def test_uncontended_write_does_not_reread_file(tmp_path: Path) -> None:
    """When nothing else has written since the load, the write must use the
    already-loaded `data` directly  no extra `read_text` (design.md D-01's
    one-read-per-call guarantee must survive the RUN-01 fix)."""
    _reset_module_caches()
    data = cache_mod._load_governance_state(tmp_path)
    data["last_ask"] = {"compiled_fingerprint_used": "fp1"}

    real_read_text = Path.read_text
    calls = {"count": 0}

    def _spy(self: Path, *args: object, **kwargs: object) -> str:
        calls["count"] += 1
        return real_read_text(self, *args, **kwargs)

    import unittest.mock as mock

    with mock.patch.object(Path, "read_text", _spy):
        cache_mod._store_governance_state(tmp_path, data, changed_keys={"last_ask"})

    assert calls["count"] == 0


def test_write_is_atomic_no_partial_file_and_no_leftover_temp(tmp_path: Path) -> None:
    _reset_module_caches()
    data = cache_mod._load_governance_state(tmp_path)
    data["last_ask"] = {"compiled_fingerprint_used": "fp1"}
    cache_mod._store_governance_state(tmp_path, data, changed_keys={"last_ask"})

    state_dir = tmp_path / ".providence" / "runtime"
    state_path = state_dir / "governance-state.json"
    assert state_path.exists()
    json.loads(state_path.read_text(encoding="utf-8"))  # must be valid, complete JSON
    assert list(state_dir.glob("governance-state.json.tmp-*")) == []
