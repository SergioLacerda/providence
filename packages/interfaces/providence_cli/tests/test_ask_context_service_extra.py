from __future__ import annotations

from pathlib import Path

import click
import pytest

from providence_cli.services import ask_context as ask_context_mod
from providence_cli.services import ask_context_drift as ask_context_drift_mod


def test_resolve_workspace_root_uses_authority_and_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        ask_context_mod, "_resolve_authority_workspace_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        ask_context_mod,
        "enforce_path_policy",
        lambda path, workspace_root, mode: workspace_root / ".providence",
    )
    assert ask_context_mod.resolve_workspace_root() == tmp_path / ".providence"


def test_get_cached_ahp_reads_click_context(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = click.Context(click.Command("ask"))
    ctx.obj = {"_ahp": {"state": "HEALTHY"}}
    monkeypatch.setattr("click.get_current_context", lambda silent=True: ctx)
    assert ask_context_mod.get_cached_ahp() == {"state": "HEALTHY"}


def test_get_cached_ahp_returns_none_on_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "click.get_current_context",
        lambda silent=True: (_ for _ in ()).throw(RuntimeError("no ctx")),
    )
    assert ask_context_mod.get_cached_ahp() is None


def test_load_compiled_governance_caches_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ask_context_mod._GOV_CACHE.clear()
    calls = {"count": 0}

    def _fake_loader(
        workspace_root, compiled_active_dir_fn, logger, load_via_runtime_fn
    ):  # noqa: ANN001
        calls["count"] += 1
        return ("compiled", "abcdef12", 3, True, False, "", "cache")

    monkeypatch.setattr(ask_context_mod, "_load_compiled_governance_impl", _fake_loader)
    first = ask_context_mod.load_compiled_governance(tmp_path)
    second = ask_context_mod.load_compiled_governance(tmp_path)
    assert first == second
    assert calls["count"] == 1


def test_load_ask_context_raises_when_workspace_missing(tmp_path: Path) -> None:
    with pytest.raises(ask_context_mod.WorkspaceNotFoundError):
        ask_context_mod.load_ask_context(workspace_root=tmp_path / "missing")


def test_load_ask_context_builds_dataclass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        ask_context_mod, "get_profile_state", lambda root: ("client", "HEALTHY")
    )
    monkeypatch.setattr(
        ask_context_mod,
        "load_compiled_governance",
        lambda root: ("compiled", "abcdef12", 16, True, False, "", "runtime"),
    )
    monkeypatch.setattr(
        ask_context_drift_mod, "check_fingerprint_drift", lambda root, fp: True
    )
    result = ask_context_mod.load_ask_context(workspace_root=tmp_path)
    assert result.workspace_root == tmp_path
    assert result.profile == "client"
    assert result.ahp_state == "HEALTHY"
    assert result.context_source == "compiled"
    assert result.drift_detected is True


def test_check_root_seed_drift_detects_stale_root_seed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A stale seed file's fingerprint header must be caught, independent of check_fingerprint_drift.

    The header must live inside the sdd-managed block
    (`.analysis/refined/20260906-root-seed-githook-necessity/design.md`)
    a bare header with no markers is `unmanaged` and never fails the check
    (see `test_governance_config_reader.py`'s dedicated unmanaged-state
    coverage for that case).
    """
    (tmp_path / ".providence").mkdir(parents=True)
    (tmp_path / ".providence" / "metadata.json").write_text(
        '{"governance_fingerprint": "abc123"}', encoding="utf-8"
    )
    (tmp_path / "CLAUDE.md").write_text(
        "<!-- sdd:managed:begin -->\n"
        "# Governance fingerprint: deadbeef99\n"
        "<!-- sdd:managed:end -->\n",
        encoding="utf-8",
    )

    assert ask_context_drift_mod.check_root_seed_drift(tmp_path) is True


def test_check_root_seed_drift_and_check_fingerprint_drift_are_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Root-seed drift and in-session fingerprint drift must never be merged into one signal.

    A stale root seed file (root-seed drift) should not affect
    check_fingerprint_drift's cached-runtime-state comparison, and vice versa.
    """
    (tmp_path / ".providence").mkdir(parents=True)
    (tmp_path / ".providence" / "metadata.json").write_text(
        '{"governance_fingerprint": "abc123"}', encoding="utf-8"
    )
    (tmp_path / "CLAUDE.md").write_text(
        "<!-- sdd:managed:begin -->\n"
        "# Governance fingerprint: deadbeef99\n"
        "<!-- sdd:managed:end -->\n",
        encoding="utf-8",
    )
    # No .providence/runtime/governance-state.json  check_fingerprint_drift must stay
    # False (its own no-cached-state default), unaffected by the root-seed drift above.
    assert ask_context_drift_mod.check_root_seed_drift(tmp_path) is True
    assert ask_context_drift_mod.check_fingerprint_drift(tmp_path, "abc123") is False
