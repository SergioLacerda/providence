from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from providence_cli.commands import setup

pytestmark = pytest.mark.unit


def test_validate_module_import_uses_script_not_python_c(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    class _Runner:
        def run(self, args, capture_output=True):  # noqa: ANN001
            calls.append(args)
            return type("R", (), {"success": True})()

    with patch(
        "providence_core.utils._process_runner.SafeProcessRunner",
        return_value=_Runner(),
    ):
        assert setup._validate_module_import("/tmp/venv/bin/python", "providence_core")

    assert calls
    assert "-c" not in calls[0]
    assert calls[0][0] == "/tmp/venv/bin/python"
    assert Path(calls[0][1]).suffix == ".py"
