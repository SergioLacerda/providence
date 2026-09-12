from __future__ import annotations

import click
import pytest

from providence_cli.utils import profile_loader as profile_loader_mod


def test_get_adapter_returns_expected_policy() -> None:
    assert profile_loader_mod.get_adapter("master") is profile_loader_mod.MasterAdapter
    assert profile_loader_mod.get_adapter("unknown") is profile_loader_mod.ClientAdapter


def test_get_active_profile_reads_context_obj() -> None:
    ctx = click.Context(click.Command("test"))
    ctx.obj = {"profile": "master"}
    assert profile_loader_mod.get_active_profile(ctx) == "master"


def test_get_active_profile_falls_back_to_client_on_detection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "providence_core.utils.environment.detect_profile",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert profile_loader_mod.get_active_profile() == "client"


def test_enforce_profile_policy_raises_for_blocked_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = click.Context(click.Command("test"))
    ctx.obj = {"profile": "client"}
    with pytest.raises(click.exceptions.Exit) as excinfo:
        profile_loader_mod.enforce_profile_policy("release", ctx)
    assert excinfo.value.exit_code == 1
    stderr = capsys.readouterr().err
    assert "command 'release' is not available" in stderr
    assert "master-only operation" in stderr


def test_enforce_profile_policy_warns_for_master_wizard(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = click.Context(click.Command("test"))
    ctx.obj = {"profile": "master"}
    profile_loader_mod.enforce_profile_policy("wizard", ctx)
    assert "WARN [master]" in capsys.readouterr().out


def test_profile_context_display_handles_supported_shapes() -> None:
    assert profile_loader_mod.profile_context_display(None) == ""
    assert (
        profile_loader_mod.profile_context_display({"profile": "master"})
        == "  profile=master"
    )
    assert (
        profile_loader_mod.profile_context_display({"profile": "client"})
        == " profile=client"
    )
