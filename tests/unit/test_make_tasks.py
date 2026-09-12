from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_tasks_module():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from tools.maintenance import make_tasks

    return make_tasks


pytestmark = pytest.mark.unit


def test_semver_key_sorts_numeric_prefixes() -> None:
    make_tasks = _make_tasks_module()
    tags = ["v1.10.0", "v1.2.9", "v2.0.0", "v1.2.10"]
    assert sorted(tags, key=make_tasks._semver_key) == [
        "v1.2.9",
        "v1.2.10",
        "v1.10.0",
        "v2.0.0",
    ]


def test_clean_removes_build_and_caches(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    (tmp_path / "build").mkdir()
    pycache = tmp_path / "a" / "__pycache__"
    pycache.mkdir(parents=True)
    (tmp_path / "a" / "b.pyc").write_text("x", encoding="utf-8")

    with patch.object(make_tasks, "REPO_ROOT", tmp_path):
        assert make_tasks.run_clean() == 0

    assert not (tmp_path / "build").exists()
    assert not pycache.exists()
    assert not (tmp_path / "a" / "b.pyc").exists()


def test_release_dry_run_runs_tests_wrapper() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_read_project_version", return_value="1.2.3"),
        patch.object(make_tasks, "run_test", return_value=0) as run_test,
        patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run,
    ):
        runner_run.return_value.returncode = 0
        runner_run.return_value.stdout = "v1.0.0\nv1.1.0\n"
        runner_run.return_value.stderr = ""
        assert make_tasks.run_release_dry_run() == 0
        run_test.assert_called_once_with(["--no-coverage"])


def test_version_tuple_parses_numeric_prefixes() -> None:
    make_tasks = _make_tasks_module()
    assert make_tasks._version_tuple("0.26.8") == (0, 26, 8)
    assert make_tasks._version_tuple("1.2") == (1, 2)
    assert make_tasks._version_tuple("0.12.1rc1") == (0, 12, 1)


def test_min_typer_version_reads_pin_from_pyproject(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = ["typer>=1.2.3", "rich>=1.0.0"]\n',
        encoding="utf-8",
    )
    with patch.object(make_tasks, "REPO_ROOT", tmp_path):
        assert make_tasks._min_typer_version() == (1, 2, 3)


def test_min_typer_version_falls_back_when_pin_missing(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = ["rich>=1.0.0"]\n', encoding="utf-8"
    )
    with patch.object(make_tasks, "REPO_ROOT", tmp_path):
        assert make_tasks._min_typer_version() == make_tasks._FALLBACK_MIN_TYPER_VERSION


def test_check_venv_fails_when_venv_missing(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "REPO_ROOT", tmp_path),
        pytest.raises(SystemExit) as excinfo,
    ):
        make_tasks._check_venv()
    assert excinfo.value.code == 1


def test_check_venv_fails_when_typer_outdated(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    venv_python.chmod(0o755)

    with (
        patch.object(make_tasks, "REPO_ROOT", tmp_path),
        patch.object(make_tasks, "_min_typer_version", return_value=(0, 26, 8)),
        patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run,
    ):
        runner_run.return_value.returncode = 0
        runner_run.return_value.stdout = "0.12.1\n"
        with pytest.raises(SystemExit) as excinfo:
            make_tasks._check_venv()
    assert excinfo.value.code == 1


def test_check_venv_succeeds_when_typer_meets_minimum(tmp_path: Path) -> None:
    make_tasks = _make_tasks_module()
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    venv_python.chmod(0o755)

    with (
        patch.object(make_tasks, "REPO_ROOT", tmp_path),
        patch.object(make_tasks, "_min_typer_version", return_value=(0, 26, 8)),
        patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run,
    ):
        runner_run.return_value.returncode = 0
        runner_run.return_value.stdout = "0.26.8\n"
        assert make_tasks._check_venv() == venv_python


def test_run_test_fast_invokes_pytest_with_expected_args() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        assert make_tasks.run_test_fast() == 0
        run.assert_called_once_with(
            ["PYTHON", "-m", "pytest", "-x", "--ff", "packages/", "tests/"]
        )


def test_run_test_perf_stops_on_first_failure() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", return_value=1) as run,
    ):
        assert make_tasks.run_test_perf() == 1
        run.assert_called_once()


def test_run_coverage_strict_stops_on_first_failing_layer() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", side_effect=[0, 1]) as run,
    ):
        assert make_tasks.run_coverage_strict() == 1
        assert run.call_count == 2


def test_run_check_venv_prints_resolved_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_tasks = _make_tasks_module()
    resolved_path = Path("/repo/.venv/bin/python")
    with patch.object(make_tasks, "_check_venv", return_value=resolved_path):
        assert make_tasks.run_check_venv() == 0
    assert capsys.readouterr().out.strip() == str(resolved_path)


def test_run_golden_status_reports_clean_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_tasks = _make_tasks_module()
    with patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run:
        runner_run.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        assert make_tasks.run_golden_status() == 0

    assert "Golden files are in sync with git" in capsys.readouterr().out
    runner_run.assert_called_once_with(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "tests/contract/fixtures/*.golden.json",
        ],
        cwd=make_tasks.REPO_ROOT,
        capture_output=True,
    )


def test_run_golden_status_reports_changed_fixtures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_tasks = _make_tasks_module()
    status = " M tests/contract/fixtures/governance_core.golden.json\n"
    with patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run:
        runner_run.return_value = SimpleNamespace(
            returncode=0, stdout=status, stderr=""
        )
        assert make_tasks.run_golden_status() == 0

    output = capsys.readouterr().out
    assert "Golden files have uncommitted changes" in output
    assert "governance_core.golden.json" in output


def test_run_golden_status_is_informational_when_git_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-git checkout (e.g. CI's shadow-repo copy) must not fail `check`."""
    make_tasks = _make_tasks_module()
    with patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run:
        runner_run.return_value = SimpleNamespace(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository (or any of the parent directories): .git",
        )
        assert make_tasks.run_golden_status() == 0

    err = capsys.readouterr().err
    assert "WARN: could not check golden file status." in err
    assert "not a git repository" in err


def test_run_ci_pr_stops_on_first_failure() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", side_effect=[1]) as run,
    ):
        assert make_tasks.run_ci_pr() == 1
        run.assert_called_once()


def test_run_golden_policy_check_modes() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        make_tasks.run_golden_policy_check(strict=False)
        run.assert_called_with(
            ["PYTHON", "tools/ci/check_golden_policy.py", "--mode", "block"]
        )
        make_tasks.run_golden_policy_check(strict=True)
        run.assert_called_with(
            ["PYTHON", "tools/ci/check_golden_policy.py", "--mode", "strict"]
        )


def test_run_help_lists_targets_with_dependencies(
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_tasks = _make_tasks_module()
    assert make_tasks.run_help() == 0
    output = capsys.readouterr().out
    assert "docs-build" in output
    assert "build-web" in output
    assert "release-prepare" in output


def test_web_wrappers_use_npm_prefix() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_npm_cmd", return_value="npm") as npm_cmd,
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        assert make_tasks.run_install_web() == 0
        run.assert_called_with(["npm", "--prefix", "apps/landing", "ci"])
        assert make_tasks.run_npm_script("lint") == 0
        run.assert_called_with(["npm", "--prefix", "apps/landing", "run", "lint"])
        assert npm_cmd.call_count == 2


def test_npm_audit_fix_uses_npm_prefix() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_npm_cmd", return_value="npm"),
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        assert make_tasks.run_npm_audit_fix() == 0
        run.assert_called_with(["npm", "--prefix", "apps/landing", "audit", "fix"])


def test_npm_audit_fix_swallows_unresolved_vulnerabilities(
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_npm_cmd", return_value="npm"),
        patch.object(make_tasks, "_run", return_value=1),
    ):
        assert make_tasks.run_npm_audit_fix() == 0
    assert "unresolved vulnerabilities" in capsys.readouterr().out


def test_lint_web_runs_audit_fix_then_lint_script() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "run_npm_audit_fix", return_value=0) as audit_fix,
        patch.object(make_tasks, "run_npm_script", return_value=0) as npm_script,
    ):
        assert make_tasks.run_lint_web() == 0
        audit_fix.assert_called_once_with()
        npm_script.assert_called_once_with("lint")


def test_lint_web_ignores_audit_fix_result() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "run_npm_audit_fix", return_value=1),
        patch.object(make_tasks, "run_npm_script", return_value=0),
    ):
        assert make_tasks.run_lint_web() == 0


def test_lint_go_skips_when_tool_missing() -> None:
    make_tasks = _make_tasks_module()
    with patch.object(make_tasks.shutil, "which", return_value=None):
        assert make_tasks.run_lint_go(fix=False) == 0


def test_build_compiler_uses_goexe_suffix() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch("providence_core.utils.process.SafeProcessRunner.run") as runner_run,
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        runner_run.return_value = SimpleNamespace(
            returncode=0, stdout=".exe\n", stderr=""
        )
        assert make_tasks.run_build_compiler() == 0
        run.assert_called_once_with(
            [
                "go",
                "build",
                "-C",
                "tools/sdd-compile",
                "-o",
                "bin/sdd-compile.exe",
                ".",
            ]
        )


def test_run_release_prepare_invokes_prepare_release_module() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        assert make_tasks.run_release_prepare("1.0.11") == 0
        run.assert_called_once_with(
            ["PYTHON", "-m", "tools.release.prepare_release", "--version", "1.0.11"]
        )


def test_main_dispatches_release_prepare_with_version_arg() -> None:
    make_tasks = _make_tasks_module()
    with patch.object(
        make_tasks, "run_release_prepare", return_value=0
    ) as run_release_prepare:
        assert make_tasks.main(["release-prepare", "--version", "1.0.11"]) == 0
        run_release_prepare.assert_called_once_with("1.0.11")


def test_run_governance_bootstrap_invokes_providence_cli_module() -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]),
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        assert make_tasks.run_governance_bootstrap() == 0
        run.assert_called_once_with(
            [
                "PYTHON",
                "-m",
                "providence_cli",
                "governance",
                "generate",
                "--full-bootstrap",
            ]
        )


@pytest.mark.parametrize(
    "runner_name",
    [
        "run_enforcement_ladder_consistency",
        "run_enforcement_ladder_digest",
        "run_enforcement_threshold_signoff",
        "run_core_compiler_runtime_contract",
        "run_observability_contract_check",
        "run_release_readiness_v1_check",
        "run_runbook_hardening_check",
        "run_update_golden_snapshots",
        "run_generate_schemas",
        "run_docs_link_check",
        "run_docs_link_fix",
    ],
)
def test_simple_wrappers_delegate_to_run_with_guarded_python(runner_name: str) -> None:
    make_tasks = _make_tasks_module()
    with (
        patch.object(make_tasks, "_python_cmd", return_value=["PYTHON"]) as python_cmd,
        patch.object(make_tasks, "_run", return_value=0) as run,
    ):
        runner = getattr(make_tasks, runner_name)
        assert runner() == 0
        python_cmd.assert_called()
        run.assert_called_once()
        assert run.call_args[0][0][0] == "PYTHON"
