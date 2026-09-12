from __future__ import annotations

from pathlib import Path

import pytest

from providence_cli.utils import loader as loader_mod


def _touch_required_files(base: Path) -> None:
    (base / "audit").mkdir(parents=True, exist_ok=True)
    for rel in (
        "governance-core.compiled.msgpack",
        "governance-client-template.compiled.msgpack",
        "audit/metadata-core.json",
        "audit/metadata-client-template.json",
    ):
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}", encoding="utf-8")


def test_resolve_compiled_dir_accepts_direct_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _touch_required_files(tmp_path)
    monkeypatch.setattr(loader_mod, "resolve_workspace_root", lambda path: tmp_path)
    monkeypatch.setattr(
        loader_mod, "enforce_path_policy", lambda path, workspace_root, mode: path
    )
    assert loader_mod.resolve_governance_compiled_dir(str(tmp_path)) == tmp_path


def test_resolve_compiled_dir_accepts_compiled_subdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    compiled = tmp_path / "compiled"
    _touch_required_files(compiled)
    monkeypatch.setattr(loader_mod, "resolve_workspace_root", lambda path: tmp_path)
    monkeypatch.setattr(
        loader_mod, "enforce_path_policy", lambda path, workspace_root, mode: path
    )
    assert loader_mod.resolve_governance_compiled_dir(str(tmp_path)) == compiled


def test_resolve_compiled_dir_accepts_nested_sdd_compiled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    compiled = tmp_path / ".providence" / "compiled"
    _touch_required_files(compiled)
    monkeypatch.setattr(loader_mod, "resolve_workspace_root", lambda path: tmp_path)
    monkeypatch.setattr(
        loader_mod, "enforce_path_policy", lambda path, workspace_root, mode: path
    )
    assert loader_mod.resolve_governance_compiled_dir(str(tmp_path)) == compiled


def test_resolve_compiled_dir_returns_none_on_policy_violation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _raise(path, workspace_root, mode):  # noqa: ANN001
        raise loader_mod.PathPolicyViolation(Path(path), "blocked", "hint")

    monkeypatch.setattr(loader_mod, "resolve_workspace_root", lambda path: tmp_path)
    monkeypatch.setattr(loader_mod, "enforce_path_policy", _raise)
    assert loader_mod.resolve_governance_compiled_dir(str(tmp_path)) is None


def test_load_governance_config_returns_combined_items(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _touch_required_files(tmp_path)
    monkeypatch.setattr(loader_mod, "_resolve_compiled_dir", lambda path: tmp_path)

    class _FakeGovernanceLoader:
        def __init__(self, path: str) -> None:
            assert path == str(tmp_path)
            self.packages_data = {"items": [{"id": "M001"}]}
            self._client_data = {"items": [{"id": "C001"}]}

        def load_all(self) -> dict[str, str]:
            return {"core_fingerprint": "core", "client_fingerprint": "client"}

    import providence_core.utils.loader as core_loader

    monkeypatch.setattr(core_loader, "GovernanceLoader", _FakeGovernanceLoader)
    config = loader_mod.load_governance_config(str(tmp_path))
    assert config["core_items_count"] == 1
    assert config["client_items_count"] == 1
    assert len(config["items"]) == 2


def test_load_governance_config_raises_value_error_when_invalid_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(loader_mod, "_resolve_compiled_dir", lambda path: None)
    with pytest.raises(
        ValueError, match="Invalid governance path or blocked by path policy"
    ):
        loader_mod.load_governance_config("missing")


def test_validate_governance_path_and_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(loader_mod, "_resolve_compiled_dir", lambda path: tmp_path)
    assert loader_mod.validate_governance_path("ok") is True
    summary = loader_mod.get_governance_summary(
        "ok",
        config={
            "items": [{"id": "a"}],
            "core_items_count": 1,
            "client_items_count": 2,
            "core_fingerprint": "abcdef0123456789",
            "client_fingerprint": "0123456789abcdef",
        },
    )
    assert summary["Status"] == "Ready"
    assert summary["Core Items"] == 1
