"""Compatibility and explicit workspace configuration contracts."""

from pathlib import Path

import pytest

from providence_core.governance.compliance_mode_policy import ComplianceModePolicy
from providence_core.utils.environment import resolve_profile, write_profile
from providence_core.utils.workspace_settings import resolve_workspace_settings


@pytest.mark.parametrize(
    ("profile", "mode", "publish"),
    [("master", "active", True), ("client", "passive", False)],
)
def test_legacy_defaults(
    tmp_path: Path, profile: str, mode: str, publish: bool
) -> None:
    settings = resolve_workspace_settings(tmp_path, profile)
    assert settings.artifact_target == profile
    assert settings.audit_mode == mode
    assert ("publish" in settings.capabilities) == publish


def test_independent_settings_and_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SDD_PROFILE", raising=False)
    monkeypatch.delenv("SDD_LOGGING_MODE", raising=False)
    directory = tmp_path / ".providence"
    directory.mkdir()
    (directory / "profile").write_text(
        "[sdd]\ntype=client\n[workspace]\ncapabilities=consume,author,publish\nartifact_target=master\naudit_mode=strict\n",
        encoding="utf-8",
    )
    context = resolve_profile(tmp_path)
    assert context.type == "master"
    assert context.capabilities == frozenset({"consume", "author", "publish"})
    assert resolve_profile(tmp_path, override="client").type == "client"
    assert (
        ComplianceModePolicy.resolve_logging_mode("client", workspace_root=tmp_path)
        == "strict"
    )
    monkeypatch.setenv("SDD_LOGGING_MODE", "active")
    assert (
        ComplianceModePolicy.resolve_logging_mode("client", workspace_root=tmp_path)
        == "active"
    )
    write_profile(tmp_path, "client", "example")
    assert resolve_profile(tmp_path).type == "master"


@pytest.mark.parametrize(
    "setting",
    [
        "capabilities=publish",
        "capabilities=admin",
        "capabilities=",
        "artifact_target=user",
        "audit_mode=off",
        "unknown=yes",
    ],
)
def test_invalid_settings_fail(tmp_path: Path, setting: str) -> None:
    directory = tmp_path / ".providence"
    directory.mkdir()
    (directory / "profile").write_text("[workspace]\n" + setting, encoding="utf-8")
    with pytest.raises(ValueError, match="[Ww]orkspace"):
        resolve_workspace_settings(tmp_path, "client")
