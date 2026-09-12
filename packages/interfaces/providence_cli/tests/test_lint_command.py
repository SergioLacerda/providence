"""Integration tests for providence_cli.commands.lint CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from click.testing import CliRunner

from providence_cli.commands import lint
from providence_cli.commands.lint import _run_step
from providence_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _run_step
# ---------------------------------------------------------------------------


class TestRunStep:
    def test_returns_0_on_success(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True, returncode=0)
        with patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_step("mycheck", ["echo", "ok"], fix=False)
        assert result == 0

    def test_returns_nonzero_on_failure(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=False, returncode=1)
        with patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            result = _run_step("mycheck", ["false"], fix=False)
        assert result == 1

    def test_fix_mode_prints_warn_not_error(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=False, returncode=1)
        with patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=mock_runner
        ):
            _run_step("mycheck", ["false"], fix=True)


# ---------------------------------------------------------------------------
# spec command
# ---------------------------------------------------------------------------


class TestSpecCommand:
    def test_no_canonical_dir_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "providence_cli.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["lint", "spec"])
        assert result.exit_code == 1
        assert "Canonical directory not found" in result.output

    def test_clean_canonical_dir_exits_0(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        with patch(
            "providence_cli.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["lint", "spec", "--no-strict-anchor-style"])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_legacy_pattern_in_canonical_exits_1(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        (canonical / "doc.md").write_text("docs/specs/something\n", encoding="utf-8")
        with patch(
            "providence_cli.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["lint", "spec"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# validate markdown anchors  empty fragment edge case
# ---------------------------------------------------------------------------


class TestValidateMarkdownAnchorsEmptyFragment:
    def test_empty_fragment_skipped(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        doc = canonical / "doc.md"
        doc.write_text("[link](other.md#)\n", encoding="utf-8")
        (tmp_path / "other.md").write_text("", encoding="utf-8")
        with patch(
            "providence_cli.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            result = runner.invoke(app, ["lint", "spec", "--no-strict-anchor-style"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# _run_ruff
# ---------------------------------------------------------------------------


class TestRunRuff:
    def test_run_ruff_no_fix_all_pass(self) -> None:
        from providence_cli.commands.lint import _run_ruff

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True, returncode=0)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
        ):
            result = _run_ruff(fix=False)
        assert result is False

    def test_run_ruff_no_fix_check_fails(self) -> None:
        from providence_cli.commands.lint import _run_ruff

        call_count = [0]

        mock_runner = MagicMock()

        def alternate_results(cmd, **kwargs):  # noqa: ANN001
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(success=False, returncode=1)
            return MagicMock(success=True, returncode=0)

        mock_runner.run.side_effect = alternate_results
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
        ):
            result = _run_ruff(fix=False)
        assert result is True

    def test_run_ruff_fix_mode(self) -> None:
        from providence_cli.commands.lint import _run_ruff

        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True, returncode=0)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=True,
            ),
        ):
            result = _run_ruff(fix=True)
        assert result is False
        calls = mock_runner.run.call_args_list
        assert any("--fix" in str(c) for c in calls)


class TestRequireDevModuleGuard:
    def test_run_ruff_missing_module_exits(self) -> None:
        from providence_cli.commands.lint import _run_ruff

        with (
            patch(
                "providence_cli.utils.dev_deps.check_module_available",
                return_value=False,
            ),
            pytest.raises(typer.Exit),
        ):
            _run_ruff(fix=False)


# ---------------------------------------------------------------------------
# lint run command
# ---------------------------------------------------------------------------


class TestLintRunCommand:
    def _make_mock_runner(self, returncode: int = 0) -> MagicMock:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(
            success=(returncode == 0), returncode=returncode
        )
        return mock_runner

    def test_run_all_pass_exits_0(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "run",
                    "--skip-mypy",
                    "--skip-bandit",
                ],
            )
        assert result.exit_code == 0

    def test_run_step_failure_exits_1(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(1)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "run",
                    "--skip-mypy",
                    "--skip-bandit",
                    "--skip-spec",
                ],
            )
        assert result.exit_code == 1

    def test_run_with_fix_flag(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "lint",
                    "run",
                    "--fix",
                    "--skip-mypy",
                    "--skip-bandit",
                    "--skip-spec",
                ],
            )
        assert result.exit_code == 0

    def test_run_includes_mypy_by_default(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            result = runner.invoke(
                app,
                ["lint", "run", "--skip-bandit", "--skip-spec"],
            )
        assert result.exit_code == 0
        calls_str = str(mock_runner.run.call_args_list)
        assert "mypy" in calls_str

    def test_run_includes_bandit_by_default(self, tmp_path: Path) -> None:
        canonical = tmp_path / "docs" / "spec" / "canonical"
        canonical.mkdir(parents=True)
        mock_runner = self._make_mock_runner(0)
        with (
            patch(
                "providence_core.utils.process.SafeProcessRunner",
                return_value=mock_runner,
            ),
            patch(
                "providence_cli.utils.environment.detect_repo_root",
                return_value=tmp_path,
            ),
        ):
            result = runner.invoke(
                app,
                ["lint", "run", "--skip-mypy", "--skip-spec"],
            )
        assert result.exit_code == 0
        calls_str = str(mock_runner.run.call_args_list)
        assert "bandit" in calls_str


# ---------------------------------------------------------------------------
# lint.run step ordering (merged from tests/unit/cli/test_lint_command.py)
# ---------------------------------------------------------------------------


class TestLintRunStepOrdering:
    def test_run_executes_architecture_checks_before_mypy_and_bandit(self) -> None:
        calls: list[str] = []

        def _fake_run_step(label: str, cmd: list[str], *, fix: bool) -> int:
            calls.append(label)
            return 0

        with (
            patch("providence_cli.commands.lint._run_ruff", return_value=False),
            patch("providence_cli.commands.lint._run_step", side_effect=_fake_run_step),
            patch("providence_cli.commands.lint.spec"),
        ):
            lint.run(fix=False, skip_mypy=False, skip_bandit=False, skip_spec=False)

        assert calls[:6] == [
            "architecture imports",
            "architecture cycles",
            "architecture class-size",
            "cognitive governance",
            "mypy",
            "bandit",
        ]

    def test_run_exits_nonzero_when_architecture_check_fails(self) -> None:
        with (
            patch("providence_cli.commands.lint._run_ruff", return_value=False),
            patch(
                "providence_cli.commands.lint._run_step",
                side_effect=[1, 0, 0, 0, 0],
            ),
            patch("providence_cli.commands.lint.spec"),
            pytest.raises(typer.Exit) as exc,
        ):
            lint.run(fix=False, skip_mypy=False, skip_bandit=False, skip_spec=False)

        assert exc.value.exit_code == 1
