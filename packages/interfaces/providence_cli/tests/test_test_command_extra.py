from __future__ import annotations

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from providence_cli.commands.test import TestCommand
from providence_cli.commands.test import app as test_app

runner = CliRunner()


def test_test_command_reports_missing_script(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.commands.test.require_dev_module", lambda module: None
    )
    with pytest.raises(typer.Exit):
        TestCommand().run(
            verbose=False, fail_fast=False, coverage=True, cov_fail_under=None
        )


def test_test_command_builds_expected_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "tools" / "testing" / "run-all-tests.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')", encoding="utf-8")
    seen: dict[str, object] = {}

    class _Runner:
        def run(self, cmd, cwd=None, check=None, capture_output=None):  # noqa: ANN001
            seen["cmd"] = cmd
            return None

    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.commands.test.require_dev_module", lambda module: None
    )
    monkeypatch.setattr(
        "providence_core.utils.process.SafeProcessRunner", lambda: _Runner()
    )
    TestCommand().run(verbose=True, fail_fast=True, coverage=False, cov_fail_under=91)
    cmd = seen["cmd"]
    assert "--verbose" in cmd
    assert "--fail-fast" in cmd
    assert "--no-coverage" in cmd
    assert "--cov-fail-under" in cmd


@pytest.mark.parametrize(
    ("error_factory", "expected_exit_code"),
    [
        (lambda process_mod: process_mod.ProcessNonZeroExitError("boom"), 1),
        (lambda process_mod: process_mod.ProcessAuthorizationError("blocked"), 2),
        (lambda process_mod: process_mod.ProcessTimeoutError(["python"], 1), 124),
        (lambda process_mod: process_mod.ProcessSpawnError("spawn"), 127),
    ],
)
def test_test_command_maps_process_errors_to_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_factory,
    expected_exit_code: int,
) -> None:
    script = tmp_path / "tools" / "testing" / "run-all-tests.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')", encoding="utf-8")

    from providence_core.utils import process as process_mod

    class _Runner:
        def run(self, cmd, cwd=None, check=None, capture_output=None):  # noqa: ANN001
            raise error_factory(process_mod)

    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.commands.test.require_dev_module", lambda module: None
    )
    monkeypatch.setattr(
        "providence_core.utils.process.SafeProcessRunner", lambda: _Runner()
    )
    with pytest.raises(typer.Exit) as excinfo:
        TestCommand().run(
            verbose=False, fail_fast=False, coverage=True, cov_fail_under=None
        )
    assert excinfo.value.exit_code == expected_exit_code


def test_ci_validate_pass_and_fail_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for rel in (
        "tools/health/health_check.py",
        "tools/governance/compliance.py",
        "tools/testing/run-all-tests.py",
    ):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")

    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.commands.test.require_dev_module", lambda module: None
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._check_import", lambda module: True
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._run_script", lambda script, args, cwd: 0
    )
    monkeypatch.setattr("providence_cli.commands.test._run_pytest", lambda args, cwd: 0)
    monkeypatch.setattr(
        "providence_cli.commands.test._run_cli",
        lambda args, cwd: 0 if args[:2] != ["runtime", "status"] else 3,
    )
    result = runner.invoke(test_app, ["ci-validate", "--soak-threads"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output

    monkeypatch.setattr(
        "providence_cli.commands.test._check_import", lambda module: module != "yaml"
    )
    result = runner.invoke(
        test_app, ["ci-validate", "--no-health", "--no-governance", "--no-tests"]
    )
    assert result.exit_code == 1
    assert "ERROR: One or more checks failed" in result.output


def test_ci_validate_marks_missing_scripts_and_soak_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.commands.test.require_dev_module", lambda module: None
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._check_import", lambda module: True
    )
    monkeypatch.setattr("providence_cli.commands.test._run_cli", lambda args, cwd: 0)
    monkeypatch.setattr("providence_cli.commands.test._run_pytest", lambda args, cwd: 2)
    result = runner.invoke(test_app, ["ci-validate", "--soak-threads"])
    assert result.exit_code == 1
    assert "FAIL: not found at" in result.output
    assert "=== Thread soak ===" in result.output


def test_ci_validate_rejects_unexpected_runtime_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for rel in (
        "tools/health/health_check.py",
        "tools/governance/compliance.py",
        "tools/testing/run-all-tests.py",
    ):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")

    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.commands.test.require_dev_module", lambda module: None
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._check_import", lambda module: True
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._run_script", lambda script, args, cwd: 0
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._run_cli",
        lambda args, cwd: 9 if args[:2] == ["runtime", "status"] else 0,
    )
    result = runner.invoke(test_app, ["ci-validate", "--no-tests"])
    assert result.exit_code == 1
    assert "ERROR: One or more checks failed" in result.output


def test_test_command_exits_with_actionable_message_when_pytest_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.dev_deps.check_module_available",
        lambda executable, module: False,
    )

    with pytest.raises(typer.Exit) as excinfo:
        TestCommand().run(
            verbose=False, fail_fast=False, coverage=True, cov_fail_under=None
        )

    assert excinfo.value.exit_code == 1
    output = capsys.readouterr().out
    assert "pytest" in output
    assert "not available in this environment" in output


def test_ci_validate_exits_early_with_actionable_message_when_pytest_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "providence_cli.commands.test.detect_repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "providence_cli.utils.dev_deps.check_module_available",
        lambda executable, module: False,
    )
    monkeypatch.setattr(
        "providence_cli.commands.test._check_import", lambda module: True
    )

    result = runner.invoke(test_app, ["ci-validate"])

    assert result.exit_code == 1
    assert "pytest" in result.output
    assert "not available in this environment" in result.output
