"""Skills command output helpers."""

from __future__ import annotations

from typing import Any

from providence_cli.shared.contracts import build_error_result, build_ok_result
from providence_cli.utils.output import emit_json


def emit_skills_json(
    *,
    command: str,
    data: dict[str, Any],
    ok: bool,
    error_code: str | None = None,
    error_message: str | None = None,
    err: bool = False,
) -> None:
    """Emit canonical JSON envelope for skills commands."""
    if ok:
        payload = build_ok_result(command, data)
    else:
        payload = build_error_result(
            command,
            data,
            code=error_code or "skills_error",
            message=error_message or "skills command failed",
        )
    emit_json(payload, err=err)
