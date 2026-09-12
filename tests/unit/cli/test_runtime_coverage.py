"""Coverage tests for runtime helpers and branches."""

from __future__ import annotations

import builtins
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer

from providence_cli.commands import runtime as runtime_mod
from providence_cli.services.runtime_handler import _read_workspace_id


def _install_fake_providence_runtime(  # noqa: C901
    monkeypatch: pytest.MonkeyPatch,
    *,
    drift: bool = False,
    raise_on_inject: bool = False,
) -> None:
    root_mod = types.ModuleType("providence_runtime")

    def format_governance_footer(*, drift: str, governance: str, profile: str) -> str:
        return f"footer:{drift}:{governance}:{profile}"

    class _CompiledArtifact:
        @classmethod
        def from_sdd_compiled_dir(cls, compiled_dir: Path, profile: str):
            return types.SimpleNamespace(compiled_dir=compiled_dir, profile=profile)

    class _Injection:
        loaded = True
        artifact_fingerprint = "fp-123"
        schema_version = "3.0"
        mandates_loaded = 2

    class _GovernanceInjector:
        def inject_from_path(self, compiled_dir: Path):
            if raise_on_inject:
                raise RuntimeError("inject failure")
            return _Injection()

    class _SessionState:
        def __init__(self, **kwargs: object) -> None:
            self.__dict__.update(kwargs)

    class _SessionManager:
        def __init__(self, state_dir: Path) -> None:
            self.state_dir = state_dir

        def get(self, workspace_id: str, agent_id: str, work_item_id: str) -> object:
            # DRF-03 fix: `_emit_runtime_status` now classifies drift
            # against the *previous* session, read before the new one is
            # upserted — see `runtime_handler.py`. Returning a non-None
            # stand-in here (any object; `_DriftDetector.classify` below
            # ignores its contents) exercises that "previous session
            # exists" branch instead of the "first session" one.
            return types.SimpleNamespace(artifact_fingerprint="fp-previous")

        def upsert(self, session: object) -> None:
            self.session = session

    class _DriftReport:
        drift_detected = drift
        drift_type = "fingerprint"
        remediation_command = "providence runtime status --force"

    class _DriftDetector:
        def classify(self, session: object, artifact: object, current_profile: str):
            return _DriftReport()

    class _TelemetrySink:
        def __init__(self, jsonl_path: Path, logging_mode: str) -> None:
            self.jsonl_path = jsonl_path
            self.logging_mode = logging_mode
            self.emitted: list[object] = []

        def emit(self, event: object) -> None:
            self.emitted.append(event)

    class _RuntimeEvent(dict):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)

    root_mod.format_governance_footer = format_governance_footer
    root_mod.CompiledArtifact = _CompiledArtifact
    root_mod.DriftDetector = _DriftDetector
    root_mod.GovernanceInjector = _GovernanceInjector
    root_mod.RuntimeEvent = _RuntimeEvent
    root_mod.SessionManager = _SessionManager
    root_mod.SessionState = _SessionState
    root_mod.TelemetrySink = _TelemetrySink

    monkeypatch.setitem(sys.modules, "providence_runtime", root_mod)


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path
    (root / ".providence" / "runtime").mkdir(parents=True, exist_ok=True)
    (root / ".providence" / "compiled").mkdir(parents=True, exist_ok=True)
    (root / ".providence" / "profile").write_text(
        "[sdd]\nworkspace_id = ws-1\ntype = client\n",
        encoding="utf-8",
    )
    (root / ".providence" / "compiled" / "governance-core.json").write_text(
        json.dumps({"fingerprint": "fp-123"}),
        encoding="utf-8",
    )
    return root


def test_status_update_cache_missing_gov_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime_mod, "resolve_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(runtime_mod, "enforce_path_policy", lambda root, **kwargs: root)
    with pytest.raises(typer.Exit):
        runtime_mod.status(
            ctx=MagicMock(obj={}), verbose=False, force=False, update_cache=True
        )


def test_status_update_cache_success_and_import_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_root(tmp_path)
    monkeypatch.setattr(runtime_mod, "resolve_workspace_root", lambda: root)
    monkeypatch.setattr(runtime_mod, "enforce_path_policy", lambda root, **kwargs: root)
    monkeypatch.setattr(runtime_mod, "_do_update_cache", lambda root: None)
    with pytest.raises(typer.Exit) as exc_info:
        runtime_mod.status(
            ctx=MagicMock(obj={}), verbose=False, force=False, update_cache=True
        )
    assert exc_info.value.exit_code == 0


def test_status_import_error_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_root(tmp_path)
    monkeypatch.setattr(runtime_mod, "resolve_workspace_root", lambda: root)
    monkeypatch.setattr(runtime_mod, "enforce_path_policy", lambda root, **kwargs: root)
    monkeypatch.setitem(
        sys.modules,
        "providence_runtime",
        types.ModuleType("providence_runtime"),
    )
    real_import = builtins.__import__

    def _blocked_import(name: str, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("providence_core.governance.handshake"):
            raise ImportError("blocked")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    with pytest.raises(typer.Exit) as exc_info:
        runtime_mod.status(
            ctx=MagicMock(obj={}), verbose=False, force=False, update_cache=False
        )
    assert exc_info.value.exit_code == 2


def test_emit_runtime_status_success_and_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_root(tmp_path)
    monkeypatch.setattr(
        "providence_cli.services.runtime_handler.compiled_active_dir",
        lambda root: root / ".providence" / "compiled",
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_handler.resolve_compliance_events_path",
        lambda workspace_root: workspace_root / "events.jsonl",
    )
    monkeypatch.setattr(
        runtime_mod,
        "profile_active_path",
        lambda root: root / ".providence" / "profile",
    )
    monkeypatch.setenv("SDD_AGENT_ID", "agent-1")
    monkeypatch.setenv("SDD_PATH_ID", "path-1")
    _install_fake_providence_runtime(monkeypatch, drift=True)
    drift = runtime_mod._emit_runtime_status(
        root=root,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
    )
    assert drift["detected"] is True


def test_emit_runtime_status_no_drift_and_generic_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_root(tmp_path)
    monkeypatch.setattr(
        "providence_cli.services.runtime_handler.compiled_active_dir",
        lambda root: root / ".providence" / "compiled",
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_handler.resolve_compliance_events_path",
        lambda workspace_root: workspace_root / "events.jsonl",
    )
    monkeypatch.setattr(
        runtime_mod,
        "profile_active_path",
        lambda root: root / ".providence" / "profile",
    )
    _install_fake_providence_runtime(monkeypatch, drift=False)
    assert runtime_mod._emit_runtime_status(
        root=root,
        ahp_state="PARTIAL",
        workspace_profile="client",
        current_profile="client",
    ) == {"detected": False, "type": "fingerprint", "reason": ""}


def test_emit_runtime_status_filenotfound_and_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_root(tmp_path)
    monkeypatch.setattr(
        "providence_cli.services.runtime_handler.compiled_active_dir",
        lambda root: root / ".providence" / "compiled-missing",
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_handler.resolve_compliance_events_path",
        lambda workspace_root: workspace_root / "events.jsonl",
    )
    monkeypatch.setattr(
        runtime_mod,
        "profile_active_path",
        lambda root: root / ".providence" / "profile",
    )
    _install_fake_providence_runtime(monkeypatch, raise_on_inject=True)
    assert runtime_mod._emit_runtime_status(
        root=root,
        ahp_state="HEALTHY",
        workspace_profile="client",
        current_profile="client",
    ) == {"detected": False, "type": "none", "reason": ""}


def test_runtime_helpers_and_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    root = _make_root(tmp_path)
    runtime_dir = root / ".providence" / "runtime"
    cache_file = runtime_dir / ".providence-cache.json"
    cache_file.write_text("not-json", encoding="utf-8")
    (runtime_dir / "governance-state.json").write_text(
        json.dumps(
            {
                "state": "HEALTHY",
                "last_ask": {
                    "ts": "2025-01-01T00:00:00",
                    "context_source": "compiled",
                    "compiled_fingerprint_used": "abc123",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runtime_mod,
        "profile_active_path",
        lambda root: root / ".providence" / "profile",
    )
    assert _read_workspace_id(root) == "ws-1"
    assert runtime_mod._read_profile(root) == "client"
    assert runtime_mod._check_cache_staleness(root)["missing"] is True
    assert (
        runtime_mod._footer_drift_status({"detected": True, "type": "hash"}) == "hash"
    )
    assert (
        runtime_mod._footer_drift_status({"detected": False, "type": "hash"}) == "none"
    )

    block = runtime_mod._format_diagnostic_block(root, cache_file=cache_file)
    assert "workspace root" in block
    assert "cache file" in block

    payload = runtime_mod._show_ask_confidence(root, emit=True)
    assert payload is not None
    captured = capsys.readouterr().out
    assert "ask_confidence" in captured

    class _Report:
        def __init__(self) -> None:
            self.big = object()

    normalized = runtime_mod._normalize_report(_Report())
    assert "big" in normalized


def test_runtime_read_helpers_and_error_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_root(tmp_path)
    profile_path = root / ".providence" / "profile"
    profile_path.write_text(
        "[sdd]\nworkspace_id = ws-2\ntype = client\n", encoding="utf-8"
    )
    monkeypatch.setattr(runtime_mod, "profile_active_path", lambda root: profile_path)
    assert _read_workspace_id(root) == "ws-2"
    assert runtime_mod._read_profile(root) == "client"

    profile_path.write_text("not a config", encoding="utf-8")
    assert _read_workspace_id(root) == "unknown"
    assert runtime_mod._read_profile(root) == ""

    cache = root / ".providence" / "runtime" / ".providence-cache.md"
    cache.write_text("cache", encoding="utf-8")
    assert runtime_mod._check_cache_staleness(root)["missing"] is False
    assert runtime_mod._format_diagnostic_block(root, cache_file=cache)
