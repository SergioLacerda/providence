"""CLI behavior for the retired workspace-root variable (RFC-019)."""

from __future__ import annotations

import pytest

from providence_core.utils.environment import workspace_root_from_env


def test_main_reports_a_retired_variable_cleanly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A retired variable exits 2 with the replacement named, not a traceback."""
    from providence_cli import main as main_module

    monkeypatch.delenv("PROVIDENCE_WORKSPACE_ROOT", raising=False)
    monkeypatch.setenv("SDD_WORKSPACE_ROOT", "/somewhere")

    def _app(*_args: object, **_kwargs: object) -> None:
        workspace_root_from_env()

    monkeypatch.setattr(main_module, "app", _app)

    assert main_module.main() == 2

    err = capsys.readouterr().err
    assert "SDD_WORKSPACE_ROOT" in err
    assert "PROVIDENCE_WORKSPACE_ROOT" in err
    assert "Traceback" not in err


def test_output_base_resolution_rejects_the_retired_variable(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    from providence_cli.services._governance_compile_support import (
        resolve_output_base_path,
    )
    from providence_core.utils._environment_workspace import (
        RetiredEnvironmentVariableError,
    )

    monkeypatch.setenv("SDD_WORKSPACE_ROOT", str(tmp_path))

    with pytest.raises(RetiredEnvironmentVariableError):
        resolve_output_base_path(
            Path(tmp_path),
            override=str(tmp_path / "other"),
            resolve_workspace_root_fn=lambda: tmp_path,
        )
