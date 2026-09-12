from __future__ import annotations

import logging
import subprocess  # nosec B404
import time
from pathlib import Path
from typing import Any

from providence_core.utils._process_auth import AUTHORIZED_BINARIES, ProcessAuthorizer
from providence_core.utils._process_runner_telemetry import (
    emit_telemetry,
    new_trace_id,
    normalize_status,
)
from providence_core.utils._process_types import (
    ProcessAuthorizationError,
    ProcessNonZeroExitError,
    ProcessResult,
    ProcessSpawnError,
    _coerce_output,
)

logger = logging.getLogger(__name__)


class SafeProcessRunner:
    def __init__(
        self,
        authorized_binaries: set[str] | frozenset[str] | None = None,
        telemetry_sink: Any | None = None,
        authorizer: ProcessAuthorizer | None = None,
    ) -> None:
        _bins = (
            authorized_binaries
            if authorized_binaries is not None
            else AUTHORIZED_BINARIES
        )
        self._authorizer = authorizer or ProcessAuthorizer(_bins)
        if telemetry_sink is not None:
            self._sink = telemetry_sink
        else:
            try:
                from providence_runtime.telemetry import TelemetrySink

                self._sink = TelemetrySink()
            except Exception:
                self._sink = None

    _normalize_status = staticmethod(normalize_status)

    def _emit_telemetry(
        self,
        event_type: str,
        args: list[str],
        returncode: int | None = None,
        duration_ms: int | None = None,
        error_kind: str | None = None,
        binary_name: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        emit_telemetry(
            self._sink,
            self._authorizer,
            event_type=event_type,
            args=args,
            returncode=returncode,
            duration_ms=duration_ms,
            error_kind=error_kind,
            binary_name=binary_name,
            trace_id=trace_id,
        )

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | str | None = None,
        input_data: str | bytes | None = None,
        capture_output: bool = True,
        check: bool = False,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        self._authorizer.validate_args(args)
        trace_id = new_trace_id()
        try:
            binary_name = self._authorizer.authorize(args)
        except ProcessAuthorizationError:
            self._emit_telemetry("error", args, 0, error_kind="auth", trace_id=trace_id)
            raise
        self._emit_telemetry("start", args, binary_name=binary_name, trace_id=trace_id)
        started = time.perf_counter()
        text_mode = isinstance(input_data, str) if input_data is not None else True
        try:
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
        except subprocess.TimeoutExpired:
            logger.error("Process timeout: %s", " ".join(args))
            self._emit_telemetry(
                "timeout", args, error_kind="timeout", trace_id=trace_id
            )
            raise
        except Exception as exc:
            logger.error("Process execution error: %s", str(exc))
            self._emit_telemetry("error", args, error_kind="spawn", trace_id=trace_id)
            raise ProcessSpawnError(
                f"Could not execute process: {' '.join(args)} ({exc})"
            ) from exc
        result = ProcessResult(
            command=args,
            returncode=proc.returncode,
            stdout=_coerce_output(proc.stdout),
            stderr=_coerce_output(proc.stderr),
            success=proc.returncode == 0,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status="ok" if proc.returncode == 0 else "error",
            error_kind=None if proc.returncode == 0 else "non_zero",
        )
        self._emit_telemetry(
            "finish",
            args,
            returncode=result.returncode,
            duration_ms=result.duration_ms,
            error_kind=result.error_kind,
            binary_name=binary_name,
            trace_id=trace_id,
        )
        if check and not result.success:
            raise ProcessNonZeroExitError(
                f"Command failed with exit code {result.returncode}: {' '.join(args)}"
            )
        return result

    def run_interactive(
        self,
        args: list[str],
        *,
        cwd: Path | str | None = None,
        stdin_text: str | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        self._authorizer.validate_args(args)
        trace_id = new_trace_id()
        try:
            binary_name = self._authorizer.authorize(args)
        except ProcessAuthorizationError:
            self._emit_telemetry("error", args, 0, error_kind="auth", trace_id=trace_id)
            raise
        self._emit_telemetry("start", args, binary_name=binary_name, trace_id=trace_id)
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
        except subprocess.TimeoutExpired:
            if proc is not None:
                proc.kill()
            logger.error("Process timeout: %s", " ".join(args))
            self._emit_telemetry(
                "timeout", args, error_kind="timeout", trace_id=trace_id
            )
            raise
        except Exception as exc:
            logger.error("Process execution error: %s", str(exc))
            self._emit_telemetry("error", args, error_kind="spawn", trace_id=trace_id)
            raise ProcessSpawnError(
                f"Could not execute interactive process: {' '.join(args)} ({exc})"
            ) from exc
        result = ProcessResult(
            command=args,
            returncode=proc.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
            success=proc.returncode == 0,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status="ok" if proc.returncode == 0 else "error",
            error_kind=None if proc.returncode == 0 else "non_zero",
        )
        self._emit_telemetry(
            "finish",
            args,
            returncode=result.returncode,
            duration_ms=result.duration_ms,
            error_kind=result.error_kind,
            binary_name=binary_name,
            trace_id=trace_id,
        )
        return result
