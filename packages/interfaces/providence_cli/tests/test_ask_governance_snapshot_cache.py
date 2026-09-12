"""Tests for the cross-invocation compiled-governance snapshot cache (T-A1/T-A2/T-A3).

Covers `ask_context.get_cached_governance_snapshot`/`store_governance_snapshot`
(the disk-backed sibling of the in-process `_GOV_CACHE`, keyed by fingerprint
and TTL-bounded  design.md `20260730-sdd-ask-cross-invocation-cache` D-A),
plus `build_governed_ask_snapshot`'s wiring: a hit must skip
`_load_compiled_governance` entirely, and only a fresh (cache-miss) load is
persisted at the end of the call.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from providence_cli.services import ask_context_drift as ask_context_drift_mod
from providence_cli.services import ask_context_routing as ask_context_routing_mod
from providence_cli.services import ask_context_snapshot as ask_context_snapshot_mod


def _iso_now(offset_seconds: float = 0.0) -> str:
    ts = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return ts.isoformat(timespec="seconds").replace("+00:00", "Z")


def test_store_then_get_governance_snapshot_hits_within_ttl(tmp_path: Path) -> None:
    snapshot = {
        "context_source": "compiled",
        "fingerprint": "fp1",
        "mandates_count": 16,
        "authenticated": True,
        "degraded": False,
        "degrade_reason": "",
        "trust_source": "canonical",
    }
    ask_context_snapshot_mod.store_governance_snapshot(tmp_path, "fp1", snapshot)

    cached = ask_context_snapshot_mod.get_cached_governance_snapshot(tmp_path, "fp1")

    assert cached == snapshot


def test_get_governance_snapshot_misses_for_unknown_fingerprint(tmp_path: Path) -> None:
    ask_context_snapshot_mod.store_governance_snapshot(
        tmp_path, "fp1", {"fingerprint": "fp1"}
    )

    assert (
        ask_context_snapshot_mod.get_cached_governance_snapshot(tmp_path, "fp2") is None
    )


def test_get_governance_snapshot_returns_none_without_fingerprint(
    tmp_path: Path,
) -> None:
    assert ask_context_snapshot_mod.get_cached_governance_snapshot(tmp_path, "") is None


def test_get_governance_snapshot_expires_after_ttl(tmp_path: Path) -> None:
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True)
    stale_computed_at = _iso_now(
        -(ask_context_snapshot_mod._SNAPSHOT_CACHE_TTL_SECONDS + 30)
    )
    state_path.write_text(
        json.dumps(
            {
                "snapshot_cache": {
                    "fp1": {
                        "snapshot": {"fingerprint": "fp1"},
                        "computed_at": stale_computed_at,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    assert (
        ask_context_snapshot_mod.get_cached_governance_snapshot(tmp_path, "fp1") is None
    )


def test_get_governance_snapshot_hits_just_inside_ttl(tmp_path: Path) -> None:
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True)
    fresh_computed_at = _iso_now(
        -(ask_context_snapshot_mod._SNAPSHOT_CACHE_TTL_SECONDS - 30)
    )
    state_path.write_text(
        json.dumps(
            {
                "snapshot_cache": {
                    "fp1": {
                        "snapshot": {"fingerprint": "fp1"},
                        "computed_at": fresh_computed_at,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    assert ask_context_snapshot_mod.get_cached_governance_snapshot(tmp_path, "fp1") == {
        "fingerprint": "fp1"
    }


def test_store_governance_snapshot_caps_entry_count(tmp_path: Path) -> None:
    for i in range(ask_context_snapshot_mod._SNAPSHOT_CACHE_MAX_ENTRIES + 5):
        ask_context_snapshot_mod.store_governance_snapshot(
            tmp_path, f"fp{i}", {"fingerprint": f"fp{i}"}
        )

    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert (
        len(data["snapshot_cache"])
        == ask_context_snapshot_mod._SNAPSHOT_CACHE_MAX_ENTRIES
    )


def test_write_runtime_cache_and_routing_decision_persists_governance_snapshot(
    tmp_path: Path,
) -> None:
    ask_context_routing_mod.write_runtime_cache_and_routing_decision(
        tmp_path,
        {"compiled_fingerprint_used": "fp1"},
        "query",
        None,
        "fp1",
        {"organize_used": False},
        {"fingerprint": "fp1", "mandates_count": 16},
    )

    cached = ask_context_snapshot_mod.get_cached_governance_snapshot(tmp_path, "fp1")

    assert cached == {"fingerprint": "fp1", "mandates_count": 16}


def test_write_runtime_cache_and_routing_decision_skips_snapshot_without_fingerprint(
    tmp_path: Path,
) -> None:
    ask_context_routing_mod.write_runtime_cache_and_routing_decision(
        tmp_path,
        {"compiled_fingerprint_used": ""},
        "query",
        None,
        "",
        {"organize_used": False},
        {"fingerprint": "irrelevant"},
    )

    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert "snapshot_cache" not in data


def test_build_governed_ask_snapshot_skips_load_on_cache_hit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A fresh workspace with a recorded `last_ask` fingerprint and a matching
    `snapshot_cache` entry must skip `_load_compiled_governance` entirely."""
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend import _pipeline_snapshot as _pipeline

    ask_context_routing_mod.write_runtime_cache_and_routing_decision(
        tmp_path,
        {"compiled_fingerprint_used": "fp1"},
        "prior query",
        None,
        "fp1",
        {"organize_used": False},
        {
            "context_source": "compiled",
            "fingerprint": "fp1",
            "mandates_count": 16,
            "authenticated": True,
            "degraded": False,
            "degrade_reason": "",
            "trust_source": "canonical",
        },
    )

    load_calls = {"count": 0}

    def _spy_load_compiled_governance(root: Path) -> tuple:
        load_calls["count"] += 1
        return ("compiled", "fp1", 16, True, False, "", "canonical")

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    monkeypatch.setattr(
        _backend, "_load_compiled_governance", _spy_load_compiled_governance
    )
    monkeypatch.setattr(_backend, "_guard_handshake", lambda root: None)
    monkeypatch.setattr(_backend, "_runtime_drift_check", lambda root, fp: False)
    monkeypatch.setattr(_backend, "_root_seed_drift_check", lambda root: False)
    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        lambda root, *, task_type, operation_phase: _FakeReport(),
    )

    snapshot = _pipeline.build_governed_ask_snapshot(
        query="anything",
        skill=None,
        organize_used=False,
        workspace_root=tmp_path,
        require_handshake=True,
    )

    assert load_calls["count"] == 0, "cache hit must skip _load_compiled_governance"
    assert snapshot["fingerprint"] == "fp1"
    assert snapshot["mandates_count"] == 16
    assert snapshot["_governance_snapshot_to_persist"] is None


def test_build_governed_ask_snapshot_loads_fresh_on_cold_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No prior `providence ask` call recorded -> always runs the real load, and
    marks the result for persistence."""
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend import _pipeline_snapshot as _pipeline

    load_calls = {"count": 0}

    def _spy_load_compiled_governance(root: Path) -> tuple:
        load_calls["count"] += 1
        return ("compiled", "fp1", 16, True, False, "", "canonical")

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    monkeypatch.setattr(
        _backend, "_load_compiled_governance", _spy_load_compiled_governance
    )
    monkeypatch.setattr(_backend, "_guard_handshake", lambda root: None)
    monkeypatch.setattr(_backend, "_runtime_drift_check", lambda root, fp: False)
    monkeypatch.setattr(_backend, "_root_seed_drift_check", lambda root: False)
    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        lambda root, *, task_type, operation_phase: _FakeReport(),
    )

    snapshot = _pipeline.build_governed_ask_snapshot(
        query="anything",
        skill=None,
        organize_used=False,
        workspace_root=tmp_path,
        require_handshake=True,
    )

    assert load_calls["count"] == 1
    assert snapshot["_governance_snapshot_to_persist"] == {
        "context_source": "compiled",
        "fingerprint": "fp1",
        "mandates_count": 16,
        "authenticated": True,
        "degraded": False,
        "degrade_reason": "",
        "trust_source": "canonical",
    }


def test_build_governed_ask_snapshot_reloads_after_fingerprint_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A recorded `last_ask` fingerprint with no matching `snapshot_cache`
    entry (e.g. a governance recompile happened) must fall through to a real
    load, not silently reuse an unrelated cached entry."""
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend import _pipeline_snapshot as _pipeline

    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp1"}
    )

    load_calls = {"count": 0}

    def _spy_load_compiled_governance(root: Path) -> tuple:
        load_calls["count"] += 1
        return ("compiled", "fp2", 17, True, False, "", "canonical")

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    monkeypatch.setattr(
        _backend, "_load_compiled_governance", _spy_load_compiled_governance
    )
    monkeypatch.setattr(_backend, "_guard_handshake", lambda root: None)
    monkeypatch.setattr(_backend, "_runtime_drift_check", lambda root, fp: False)
    monkeypatch.setattr(_backend, "_root_seed_drift_check", lambda root: False)
    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        lambda root, *, task_type, operation_phase: _FakeReport(),
    )

    snapshot = _pipeline.build_governed_ask_snapshot(
        query="anything",
        skill=None,
        organize_used=False,
        workspace_root=tmp_path,
        require_handshake=True,
    )

    assert load_calls["count"] == 1
    assert snapshot["fingerprint"] == "fp2"
