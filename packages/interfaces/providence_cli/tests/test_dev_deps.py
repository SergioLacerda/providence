"""Tests for providence_cli.utils.dev_deps.require_dev_module."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer

from providence_cli.utils.dev_deps import require_dev_module

pytestmark = pytest.mark.unit


def test_require_dev_module_passes_when_available() -> None:
    with patch(
        "providence_cli.utils.dev_deps.check_module_available", return_value=True
    ):
        require_dev_module("ruff")


def test_require_dev_module_exits_with_actionable_message(
    capsys: pytest.CaptureFixture,
) -> None:
    with (
        patch(
            "providence_cli.utils.dev_deps.check_module_available", return_value=False
        ),
        pytest.raises(typer.Exit) as exc_info,
    ):
        require_dev_module("ruff")

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    assert "ruff" in output
    assert "not available in this environment" in output
    assert "uv sync --all-groups --extra test" in output


def test_require_dev_module_uses_tool_name_override(
    capsys: pytest.CaptureFixture,
) -> None:
    with (
        patch(
            "providence_cli.utils.dev_deps.check_module_available", return_value=False
        ),
        pytest.raises(typer.Exit),
    ):
        require_dev_module("providence_cli.main", tool="sdd")

    output = capsys.readouterr().out
    assert "sdd" in output
