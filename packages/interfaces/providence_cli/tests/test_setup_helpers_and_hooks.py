"""Tests for providence_cli.commands.setup module-import/marker/run helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from providence_cli.commands import setup as setup_mod

runner = CliRunner()
pytestmark = pytest.mark.unit


class TestModuleImportRepoRootGuard:
    def test_import_does_not_crash_when_detect_repo_root_raises(self) -> None:
        """Regression test: a real standalone install has no repo markers,
        so `detect_repo_root()` correctly raises RuntimeError  importing
        this module must not propagate that (see
        .analysis/pending/20260906-detect-repo-root-callsite-audit.md)."""
        import importlib.util

        module_path = Path(setup_mod.__file__)
        spec = importlib.util.spec_from_file_location(
            "test_setup_no_repo_root", module_path
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)

        with patch(
            "providence_cli.utils.environment.detect_repo_root",
            side_effect=RuntimeError("SDD Project root not found"),
        ):
            spec.loader.exec_module(module)  # must not raise

        assert module._REPO_ROOT is None


class TestValidateModuleImport:
    def test_returns_true_on_success(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with patch(
            "providence_core.utils._process_runner.SafeProcessRunner",
            return_value=mock_runner,
        ):
            result = setup_mod._validate_module_import(
                "/usr/bin/python", "providence_core"
            )
        assert result is True

    def test_returns_false_on_failure(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=False)
        with patch(
            "providence_core.utils._process_runner.SafeProcessRunner",
            return_value=mock_runner,
        ):
            result = setup_mod._validate_module_import("/usr/bin/python", "missing_mod")
        assert result is False

    def test_uses_temp_script_not_python_c(self) -> None:
        calls: list[list[str]] = []

        class _Runner:
            def run(self, args, **kwargs):  # noqa: ANN001
                calls.append(list(args))
                return MagicMock(success=True)

        with patch(
            "providence_core.utils._process_runner.SafeProcessRunner",
            return_value=_Runner(),
        ):
            setup_mod._validate_module_import("/venv/bin/python", "providence_core")

        assert calls
        assert "-c" not in calls[0]
        assert Path(calls[0][1]).suffix == ".py"


class TestEnsurePhase0Marker:
    def test_creates_marker_file(self, tmp_path: Path) -> None:
        with patch.object(setup_mod, "_REPO_ROOT", tmp_path):
            setup_mod._ensure_phase_0_marker()
        marker = tmp_path / ".providence" / "runtime" / ".phase-0-complete"
        assert marker.exists()

    def test_idempotent_if_already_exists(self, tmp_path: Path) -> None:
        with patch.object(setup_mod, "_REPO_ROOT", tmp_path):
            setup_mod._ensure_phase_0_marker()
            setup_mod._ensure_phase_0_marker()
        marker = tmp_path / ".providence" / "runtime" / ".phase-0-complete"
        assert marker.exists()


class TestRunHelper:
    def test_run_success(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            setup_mod._run(["echo", "hello"])

    def test_run_failure_raises_exit(self) -> None:
        from typer import Exit

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=False)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            pytest.raises(Exit),
        ):
            setup_mod._run(["false"])
