"""Fallback CLI execution helpers for the skill executor."""

from __future__ import annotations

import logging
import shlex
import time
from pathlib import Path
from typing import Any

from ._stabilization import _is_retryable_error

logger = logging.getLogger(__name__)


def execute_skill_commands(
    *,
    skill: Any,
    root: Path,
    handler: Any = None,
    learning: Any = None,
    context: dict[str, Any] | None = None,
) -> tuple[int, list[str], list[dict[str, Any]]]:
    if not skill.cli_fallback:
        return 0, [], []
    from providence_core.utils.process import SafeProcessRunner

    timeout_seconds = int(skill.budget_policy.get("timeout_seconds", 120))
    max_retries = int(skill.budget_policy.get("max_retries", 0))
    try:
        safe_runner: SafeProcessRunner = SafeProcessRunner()
    except Exception as exc:
        return _runner_init_failure(skill.cli_fallback, exc)
    exit_code = 0
    execution_errors: list[str] = []
    command_results: list[dict[str, Any]] = []
    for cmd in skill.cli_fallback:
        exit_code = _run_command_with_retries(
            safe_runner=safe_runner,
            cmd=cmd,
            root=root,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            command_results=command_results,
            execution_errors=execution_errors,
            handler=handler,
            learning=learning,
            skill=skill,
            context=context,
        )
        if exit_code != 0:
            break
    return exit_code, execution_errors, command_results


def _runner_init_failure(
    cli_fallback: list[str], exc: Exception
) -> tuple[int, list[str], list[dict[str, Any]]]:
    error = f"runner_init_failed: {exc}"
    return (
        1,
        [f"SafeProcessRunner init failed: {exc}"],
        [
            {"command": cmd, "status": "error", "exit_code": 1, "error": error}
            for cmd in cli_fallback
        ],
    )


def _run_command_with_retries(**kwargs: Any) -> int:
    attempt = 0
    while True:
        cmd_result = _run_command_attempt(
            kwargs["safe_runner"],
            kwargs["cmd"],
            kwargs["root"],
            kwargs["timeout_seconds"],
            attempt,
        )
        kwargs["command_results"].append(cmd_result)
        if cmd_result["status"] == "ok":
            return 0
        if not _handle_command_retry(cmd_result=cmd_result, attempt=attempt, **kwargs):
            exit_code = int(cmd_result["exit_code"])
            error = (
                "timed out" if exit_code == 124 else f"failed: {cmd_result['error']}"
            )
            kwargs["execution_errors"].append(f"Command '{kwargs['cmd']}' {error}")
            return exit_code
        attempt += 1


def _run_command_attempt(
    safe_runner: Any,
    cmd: str,
    root: Path,
    timeout_seconds: int,
    attempt: int,
) -> dict[str, Any]:
    from providence_core.utils.process import ProcessTimeoutError

    cmd_result: dict[str, Any] = {
        "command": cmd,
        "status": "ok",
        "exit_code": 0,
        "error": "",
        "attempt": attempt,
    }
    try:
        safe_proc = safe_runner.run(
            shlex.split(cmd), cwd=root, capture_output=False, timeout=timeout_seconds
        )
        if not safe_proc.success:
            cmd_result.update(
                status="error",
                exit_code=safe_proc.returncode or 1,
                error=safe_proc.stderr or f"command returned {safe_proc.returncode}",
            )
    except ProcessTimeoutError:
        cmd_result.update(status="error", exit_code=124, error="timeout")
    except Exception as exc:
        cmd_result.update(status="error", exit_code=1, error=str(exc))
    return cmd_result


def _handle_command_retry(
    *, cmd_result: dict[str, Any], attempt: int, **kwargs: Any
) -> bool:
    handler = kwargs["handler"]
    context = kwargs["context"] or {}
    can_retry = (
        handler.can_retry(
            context,
            exit_code=int(cmd_result["exit_code"]),
            error=str(cmd_result["error"]),
            attempt_count=attempt,
        )
        if handler is not None and hasattr(handler, "can_retry")
        else _is_retryable_error(
            exit_code=int(cmd_result["exit_code"]),
            error=str(cmd_result["error"]),
        )
    )
    if not (attempt < kwargs["max_retries"] and can_retry):
        return False
    if handler is not None and hasattr(handler, "retry_hook"):
        retry_artifact = handler.retry_hook(
            context,
            learning=kwargs["learning"],
            skill=kwargs["skill"],
            command=kwargs["cmd"],
            exit_code=int(cmd_result["exit_code"]),
            error=str(cmd_result["error"]),
            attempt_count=attempt + 1,
        )
        if isinstance(retry_artifact, dict) and retry_artifact:
            cmd_result["retry_event"] = retry_artifact.get(
                "retry_event", retry_artifact
            )
    wait_seconds = min(0.01 * (2**attempt), 0.05)
    logger.info(
        "Retrying skill command '%s' in %.2fs (attempt %s/%s)",
        kwargs["cmd"],
        wait_seconds,
        attempt + 1,
        kwargs["max_retries"],
    )
    time.sleep(wait_seconds)
    return True
