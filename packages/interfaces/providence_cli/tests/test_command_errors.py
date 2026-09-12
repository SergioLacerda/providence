from __future__ import annotations

import typer
from typer.testing import CliRunner

from providence_cli.utils.command_errors import handle_cli_errors

app = typer.Typer()


@app.command()
@handle_cli_errors(command_name="boom", next_hint="do x")
def boom() -> None:
    raise RuntimeError("fail")


@app.command()
@handle_cli_errors(command_name="exit")
def pass_exit() -> None:
    raise typer.Exit(3)


def test_generic_exception_is_standardized() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["boom"])
    assert result.exit_code == 1
    assert "ERROR: fail" in result.output
    assert "Next: do x" in result.output


def test_typer_exit_is_repropagated() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["pass-exit"])
    assert result.exit_code == 3
