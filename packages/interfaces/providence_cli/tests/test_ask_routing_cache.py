"""Tests for the `providence ask` routing-decision cache (T-03).

Covers `ask_context`'s signature/cache primitives directly, plus the
`_run_organize_intake` short-circuit that consumes them  mirrors the two
scenarios `design.md` D3 calls out: a signature hit skips the routing
heuristics, and a governance fingerprint change never reuses a stale
decision.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_cli.services import ask_context_drift as ask_context_drift_mod
from providence_cli.services import ask_context_routing as ask_context_routing_mod


def test_compute_routing_signature_is_stable_for_equivalent_inputs() -> None:
    sig1 = ask_context_drift_mod.compute_routing_signature(
        "  Fix the Bug  ", "diagnose", "fp1"
    )
    sig2 = ask_context_drift_mod.compute_routing_signature(
        "fix the bug", "Diagnose", "fp1"
    )
    assert sig1 == sig2


def test_compute_routing_signature_changes_with_query_skill_or_fingerprint() -> None:
    base = ask_context_drift_mod.compute_routing_signature("query", "skill", "fp1")
    assert base != ask_context_drift_mod.compute_routing_signature(
        "other query", "skill", "fp1"
    )
    assert base != ask_context_drift_mod.compute_routing_signature(
        "query", "other-skill", "fp1"
    )
    assert base != ask_context_drift_mod.compute_routing_signature(
        "query", "skill", "fp2"
    )


def test_compute_routing_signature_is_16_char_cache_key_domain() -> None:
    """SEC-08 regression: this domain's contract is a 16-char truncated
    cache key  distinct from `GovernanceFingerprinter`'s full 64-char
    integrity digest and from `HandshakeCache.compute_spec_fingerprint`'s
    own 16-char (but differently normalized) governance fingerprint. Same
    length does not mean same domain; a length change here would silently
    alter this function's own contract.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` SEC-08.
    """
    sig = ask_context_drift_mod.compute_routing_signature("query", "skill", "fp1")
    assert len(sig) == 16
    int(sig, 16)  # valid hex


def test_resolve_routing_decision_returns_none_on_cold_start(tmp_path: Path) -> None:
    """No prior `providence ask` call recorded -> never cache against an unknown fingerprint."""
    assert (
        ask_context_routing_mod.resolve_routing_decision(tmp_path, "query", None)
        is None
    )


def test_store_then_resolve_routing_decision_hits_on_unchanged_fingerprint(
    tmp_path: Path,
) -> None:
    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp1"}
    )
    ask_context_routing_mod.store_routing_decision(
        tmp_path,
        "query",
        "diagnose",
        "fp1",
        {
            "organize_used": True,
            "organize_reason": "heavy",
            "handbook_task_type": "diagnosis",
        },
    )

    cached = ask_context_routing_mod.resolve_routing_decision(
        tmp_path, "query", "diagnose"
    )

    assert cached == {
        "organize_used": True,
        "organize_reason": "heavy",
        "handbook_task_type": "diagnosis",
        "computed_at": cached["computed_at"],
    }


def test_resolve_routing_decision_misses_after_fingerprint_change(
    tmp_path: Path,
) -> None:
    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp1"}
    )
    ask_context_routing_mod.store_routing_decision(
        tmp_path,
        "query",
        None,
        "fp1",
        {"organize_used": True, "organize_reason": "heavy"},
    )

    # Governance recompiled since the decision was cached; last-known fingerprint moves on.
    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp2"}
    )

    assert (
        ask_context_routing_mod.resolve_routing_decision(tmp_path, "query", None)
        is None
    )


def test_resolve_routing_decision_misses_for_different_skill(tmp_path: Path) -> None:
    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp1"}
    )
    ask_context_routing_mod.store_routing_decision(
        tmp_path,
        "query",
        "diagnose",
        "fp1",
        {"organize_used": True, "organize_reason": "heavy"},
    )

    assert (
        ask_context_routing_mod.resolve_routing_decision(tmp_path, "query", "planning")
        is None
    )


def test_store_routing_decision_caps_entry_count(tmp_path: Path) -> None:
    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp1"}
    )
    for i in range(ask_context_routing_mod._ROUTING_CACHE_MAX_ENTRIES + 5):
        ask_context_routing_mod.store_routing_decision(
            tmp_path, f"query-{i}", None, "fp1", {"organize_used": False}
        )

    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert (
        len(data["last_routing_decisions"])
        == ask_context_routing_mod._ROUTING_CACHE_MAX_ENTRIES
    )


def test_store_routing_decision_is_noop_without_fingerprint(tmp_path: Path) -> None:
    ask_context_routing_mod.store_routing_decision(
        tmp_path, "query", None, "", {"organize_used": True}
    )
    state_path = tmp_path / ".providence" / "runtime" / "governance-state.json"
    assert not state_path.exists()


def test_run_organize_intake_skips_heuristic_on_cache_hit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A signature hit must short-circuit `should_use_organize` entirely."""
    from providence_cli.commands import _ask_backend as _backend

    ask_context_drift_mod.write_runtime_cache(
        tmp_path, {"compiled_fingerprint_used": "fp1"}
    )
    ask_context_routing_mod.store_routing_decision(
        tmp_path,
        "same query",
        "diagnose",
        "fp1",
        {
            "organize_used": True,
            "organize_reason": "heavy",
            "handbook_task_type": "diagnosis",
        },
    )

    calls = {"count": 0}

    def _spy_should_use_organize(text: str) -> tuple[bool, str]:
        calls["count"] += 1
        return False, "light_input"

    monkeypatch.setattr(_backend, "_should_use_organize", _spy_should_use_organize)
    monkeypatch.setattr(
        _backend,
        "run_sdd_organize",
        lambda **kwargs: (
            {"chunks": [], "retrieval_policy": "indexed_only"},
            Path("/tmp/x"),
        ),
    )

    result = _backend._run_organize_intake(tmp_path, "same query", "diagnose")
    (
        organize_used,
        organize_reason,
        _artifact_path,
        _chunks,
        _retrieval,
        cached_handbook_task_type,
    ) = result

    assert calls["count"] == 0, "should_use_organize must be skipped on a cache hit"
    assert organize_used is True
    assert organize_reason == "heavy"
    assert cached_handbook_task_type == "diagnosis"


def test_run_organize_intake_runs_heuristic_on_cache_miss(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from providence_cli.commands import _ask_backend as _backend

    calls = {"count": 0}

    def _spy_should_use_organize(text: str) -> tuple[bool, str]:
        calls["count"] += 1
        return False, "light_input"

    monkeypatch.setattr(_backend, "_should_use_organize", _spy_should_use_organize)

    result = _backend._run_organize_intake(tmp_path, "new query", None)

    assert calls["count"] == 1
    assert result[0] is False
    assert result[1] == "light_input"
    assert result[5] is None
