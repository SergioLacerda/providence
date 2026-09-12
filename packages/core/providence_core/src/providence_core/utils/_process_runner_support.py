"""Execution helpers for `SafeProcessRunner`."""

from __future__ import annotations

import subprocess  # nosec B404
import time
from pathlib import Path

from providence_core.utils._process_types import (
    ProcessResult,
    ProcessSpawnError,
    ProcessTimeoutError,
    _coerce_output,
)


def run_process(
    args: list[str],
    *,
    cwd: Path | str | None,
    input_data: str | bytes | None,
    capture_output: bool,
    env: dict[str, str] | None,
    timeout: float | None,
) -> ProcessResult:
    started = time.perf_counter()
    text_mode = isinstance(input_data, str) if input_data is not None else True
    proc = subprocess.run(  # nosec B603
        args,
        shell=False,
        cwd=cwd,
        input=input_data,
        capture_output=capture_output,
        check=False,
        env=env,
        timeout=timeout,
        text=text_mode,
        encoding="utf-8" if text_mode else None,
        errors="replace" if text_mode else None,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    return ProcessResult(
        command=args,
        returncode=proc.returncode,
        stdout=_coerce_output(proc.stdout),
        stderr=_coerce_output(proc.stderr),
        success=proc.returncode == 0,
        duration_ms=duration_ms,
        status="ok" if proc.returncode == 0 else "error",
        error_kind=None if proc.returncode == 0 else "non_zero",
    )


def run_interactive_process(
    args: list[str],
    *,
    cwd: Path | str | None,
    stdin_text: str | None,
    timeout: float | None,
) -> ProcessResult:
    started = time.perf_counter()
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(  # nosec B603
            args,
            shell=False,
            cwd=cwd,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if proc is not None:
            proc.kill()
        raise ProcessTimeoutError(args, timeout) from exc
    except Exception as exc:
        raise ProcessSpawnError(
            f"Could not execute interactive process: {' '.join(args)} ({exc})"
        ) from exc

    duration_ms = int((time.perf_counter() - started) * 1000)
    returncode = proc.returncode
    return ProcessResult(
        command=args,
        returncode=returncode,
        stdout=stdout or "",
        stderr=stderr or "",
        success=returncode == 0,
        duration_ms=duration_ms,
        status="ok" if returncode == 0 else "error",
        error_kind=None if returncode == 0 else "non_zero",
    )
