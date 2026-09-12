from __future__ import annotations

import errno
import json

import click

from providence_cli.utils.operational_errors import (
    OperationalCliError,
    is_operational_exception,
    operational_error_from_exception,
    render_operational_error,
)


def test_classifies_permission_error() -> None:
    assert is_operational_exception(PermissionError("denied")) is True


def test_classifies_busy_oserror() -> None:
    exc = OSError(errno.EBUSY, "busy")
    assert is_operational_exception(exc) is True


def test_classifies_windows_file_lock() -> None:
    exc = OSError("locked")
    exc.winerror = 32  # type: ignore[attr-defined]
    assert is_operational_exception(exc) is True


def test_unclassified_oserror_is_not_operational() -> None:
    assert is_operational_exception(OSError(errno.EINVAL, "bad value")) is False


def test_operational_error_preserves_context() -> None:
    error = operational_error_from_exception(
        PermissionError("denied"),
        headline="Could not write profile.",
        command="providence init",
        step="profile",
        operation="write profile",
        path="C:/repo/.providence/profile",
        next_hint="retry: providence init --force",
    )

    assert error is not None
    assert error.command == "providence init"
    assert error.step == "profile"
    assert error.path == "C:/repo/.providence/profile"


def test_render_operational_error(capsys) -> None:
    render_operational_error(
        OperationalCliError(
            "Could not write profile.",
            cause=PermissionError("denied"),
            command="providence init",
            step="profile",
            operation="write profile",
            path="C:/repo/.providence/profile",
            next_hint="retry: providence init --force",
        )
    )

    err = capsys.readouterr().err
    assert "ERROR: Could not write profile." in err
    assert "Command: providence init" in err
    assert "Step: profile" in err
    assert "Path: C:/repo/.providence/profile" in err
    assert "Next: retry: providence init --force" in err
    assert "Traceback" not in err


def test_render_operational_error_json_mode(capsys) -> None:
    error = OperationalCliError(
        "Could not write profile.",
        cause=PermissionError("denied"),
        command="providence init",
        step="profile",
        operation="write profile",
        path="C:/repo/.providence/profile",
        next_hint="retry: providence init --force",
    )

    with click.Context(click.Command("sdd"), obj={"output_json": True}):
        render_operational_error(error)

    payload = json.loads(capsys.readouterr().err)
    assert payload["state"] == "error"
    assert payload["command"] == "providence init"
    assert payload["step"] == "profile"
    assert payload["path"] == "C:/repo/.providence/profile"
    assert payload["next"] == "retry: providence init --force"
    assert payload["error"]["type"] == "PermissionError"
