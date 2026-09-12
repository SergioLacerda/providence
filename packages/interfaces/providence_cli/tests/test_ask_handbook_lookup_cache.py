"""Tests for the default `providence ask` snapshot path's handbook-lookup cache (T-01).

Covers `_cached_handbook_lookup` (`_pipeline.py`), which wires the same
in-memory `ContextCache`/`ContextLoader` cache already used by `--dossier`
into the default (non-dossier) snapshot path's runtime-handbook lookup, per
`design.md` D1: reuse existing cache infrastructure instead of re-reading
`index.yaml` on every call with an unchanged query.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from providence_runtime.cache import get_context_cache


@pytest.fixture(autouse=True)
def _clear_shared_context_cache():
    """The `ContextCache` singleton is process-global  isolate each test."""
    get_context_cache().clear()
    yield
    get_context_cache().clear()


def test_cached_handbook_lookup_skips_second_lookup_on_hit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from providence_cli.commands._ask_backend import _pipeline_handbook as _pipeline

    calls = {"count": 0}

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    def _fake_lookup_runtime_handbook(
        root: Path, *, task_type: str, operation_phase: str
    ) -> _FakeReport:
        calls["count"] += 1
        return _FakeReport()

    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        _fake_lookup_runtime_handbook,
    )

    first = _pipeline._cached_handbook_lookup(
        tmp_path,
        query="fix the bug",
        task_type="diagnosis",
        operation_phase="context_loading",
    )
    second = _pipeline._cached_handbook_lookup(
        tmp_path,
        query="fix the bug",
        task_type="diagnosis",
        operation_phase="context_loading",
    )

    assert calls["count"] == 1, "second call with identical args must hit the cache"
    assert first is second


def test_cached_handbook_lookup_misses_for_different_query(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from providence_cli.commands._ask_backend import _pipeline_handbook as _pipeline

    calls = {"count": 0}

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    def _fake_lookup_runtime_handbook(
        root: Path, *, task_type: str, operation_phase: str
    ) -> _FakeReport:
        calls["count"] += 1
        return _FakeReport()

    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        _fake_lookup_runtime_handbook,
    )

    _pipeline._cached_handbook_lookup(
        tmp_path,
        query="fix the bug",
        task_type="diagnosis",
        operation_phase="context_loading",
    )
    _pipeline._cached_handbook_lookup(
        tmp_path,
        query="add a feature",
        task_type="implementation",
        operation_phase="context_loading",
    )

    assert calls["count"] == 2, "a different query/task_type must not reuse the cache"


def test_build_governed_ask_snapshot_uses_cached_task_type_when_provided(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When `_run_organize_intake` already resolved a task_type (from its own
    routing-decision cache, T-03), `build_governed_ask_snapshot` must reuse it
    instead of calling `_infer_handbook_task_type` again."""
    from providence_cli.commands import _ask_backend as _backend
    from providence_cli.commands._ask_backend import _pipeline_handbook as _pipeline

    infer_calls = {"count": 0}

    def _spy_infer(query: str, skill: str | None) -> str:
        infer_calls["count"] += 1
        return "implementation"

    class _FakeReport:
        status = "ok"
        diagnostic = ""
        matches: list[dict] = []

    monkeypatch.setattr(_pipeline, "_infer_handbook_task_type", _spy_infer)
    monkeypatch.setattr(
        _backend,
        "_load_compiled_governance",
        lambda root: ("compiled", "fp1", 5, True, False, "", "canonical"),
    )
    monkeypatch.setattr(_backend, "_guard_handshake", lambda root: None)
    monkeypatch.setattr(_backend, "_runtime_drift_check", lambda root, fp: False)
    monkeypatch.setattr(_backend, "_root_seed_drift_check", lambda root: False)
    monkeypatch.setattr(
        "providence_cli.services.governance_docs_handbook_lookup.lookup_runtime_handbook",
        lambda root, *, task_type, operation_phase: _FakeReport(),
    )

    snapshot = _backend.build_governed_ask_snapshot(
        query="anything",
        skill=None,
        organize_used=False,
        workspace_root=tmp_path,
        require_handshake=True,
        cached_handbook_task_type="diagnosis",
    )

    assert infer_calls["count"] == 0, "cached task_type must skip re-inference"
    assert snapshot["handbook_task_type"] == "diagnosis"
