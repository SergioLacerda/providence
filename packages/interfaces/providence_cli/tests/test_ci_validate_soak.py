from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from providence_cli.commands import test as test_cmd

pytestmark = pytest.mark.unit


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")


def test_ci_validate_runs_soak_when_enabled(tmp_path: Path) -> None:
    _touch(tmp_path / "tools" / "health" / "health_check.py")
    _touch(tmp_path / "tools" / "governance" / "compliance.py")
    _touch(tmp_path / "tools" / "testing" / "run-all-tests.py")

    with (
        patch.object(test_cmd, "detect_repo_root", return_value=tmp_path),
        patch.object(test_cmd, "_check_import", return_value=True),
        patch.object(test_cmd, "_run_script", return_value=0),
        patch.object(test_cmd, "_run_cli", return_value=0),
        patch.object(test_cmd, "_run_pytest", return_value=0) as run_pytest,
    ):
        test_cmd.ci_validate(
            health=True, governance=True, tests=True, soak_threads=True
        )
        run_pytest.assert_called_once()
        args, _kwargs = run_pytest.call_args
        assert "soak_restart_cycles" in args[0]


def test_ci_validate_skips_soak_by_default(tmp_path: Path) -> None:
    _touch(tmp_path / "tools" / "health" / "health_check.py")
    _touch(tmp_path / "tools" / "governance" / "compliance.py")
    _touch(tmp_path / "tools" / "testing" / "run-all-tests.py")

    with (
        patch.object(test_cmd, "detect_repo_root", return_value=tmp_path),
        patch.object(test_cmd, "_check_import", return_value=True),
        patch.object(test_cmd, "_run_script", return_value=0),
        patch.object(test_cmd, "_run_cli", return_value=0),
        patch.object(test_cmd, "_run_pytest", return_value=0) as run_pytest,
    ):
        test_cmd.ci_validate(
            health=True, governance=True, tests=True, soak_threads=False
        )
        run_pytest.assert_not_called()
