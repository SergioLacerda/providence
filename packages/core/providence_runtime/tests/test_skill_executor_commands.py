from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from providence_runtime._skill_executor import SkillExecutor
from providence_runtime._skill_executor._executor_commands import execute_skill_commands
from providence_runtime._skill_registry import SkillRegistry
from providence_runtime.skills import _REGISTRY


def _make_executor(tmp_path: Path) -> SkillExecutor:
    return SkillExecutor(SkillRegistry(_REGISTRY, tmp_path))


def test_execute_skill_commands_returns_empty_for_no_fallback(tmp_path: Path) -> None:
    code, errors, results = execute_skill_commands(
        skill=SimpleNamespace(cli_fallback=[], budget_policy={}),
        root=tmp_path,
    )
    assert code == 0
    assert errors == []
    assert results == []


def test_run_skill_executes_fallback_successfully(tmp_path: Path) -> None:
    class _Runner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            return SimpleNamespace(success=True, returncode=0, stderr="")

    with (
        patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=_Runner()
        ),
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-diagnose", execute=True, project_root=tmp_path
        )
    assert result.exit_code == 0
    assert result.command_results[0]["status"] == "ok"


def test_run_skill_retries_transient_failure_then_succeeds(tmp_path: Path) -> None:
    class _Runner:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    success=False, returncode=1, stderr="temporary unavailable"
                )
            return SimpleNamespace(success=True, returncode=0, stderr="")

    with (
        patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=_Runner()
        ),
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
        patch("time.sleep", return_value=None),
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-diagnose", execute=True, project_root=tmp_path
        )
    assert result.exit_code == 0
    assert result.command_results[0]["retry_event"]["skill"] == "sdd-diagnose"


def test_run_skill_timeout_maps_to_124_and_records_timeout(tmp_path: Path) -> None:
    class _Runner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            from providence_core.utils.process import ProcessTimeoutError

            raise ProcessTimeoutError(cmd=args, timeout=1.0)

    with (
        patch(
            "providence_core.utils.process.SafeProcessRunner", return_value=_Runner()
        ),
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
        patch("time.sleep", return_value=None),
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-diagnose", execute=True, project_root=tmp_path
        )
    assert result.exit_code == 124
    assert result.artifacts["timeout_event"]["skill"] == "sdd-diagnose"


def test_run_skill_runner_init_failure_returns_error(tmp_path: Path) -> None:
    with (
        patch(
            "providence_core.utils.process.SafeProcessRunner", side_effect=RuntimeError
        ),
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-diagnose", execute=True, project_root=tmp_path
        )
    assert result.exit_code == 1
    assert result.command_results[0]["status"] == "error"
