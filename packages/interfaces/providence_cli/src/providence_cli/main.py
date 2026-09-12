"""SDD CLI entrypoint with lazy command loading.

This keeps `sdd --help` available even when optional command dependencies
are not installed yet (for example during minimal bootstrap in CI).
"""

from __future__ import annotations

import logging
import sys

import click
import typer
from dotenv import load_dotenv
from typer._click import exceptions as typer_click_exceptions

from providence_cli._command_group import (
    _WORKSPACE_REQUIRED_COMMANDS,
    COMMAND_SPECS,
    CommandSpec,
    LazyCommandGroup,
    _build_unavailable_command,
    _requested_top_level_command,
    typer_get_command,
)
from providence_cli.utils.cli_callbacks import (
    json_option_callback,
    profile_option_callback,
    verbose_option_callback,
    version_option_callback,
)
from providence_cli.utils.operational_errors import (
    OperationalCliError,
    operational_error_from_exception,
    render_operational_error,
)
from providence_core.utils.process import ProcessRunnerError

__all__ = [
    "COMMAND_SPECS",
    "CommandSpec",
    "LazyCommandGroup",
    "_build_unavailable_command",
    "_requested_top_level_command",
    "_WORKSPACE_REQUIRED_COMMANDS",
    "typer_get_command",
    "app",
    "main",
]

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


_profile_option_callback = profile_option_callback
_json_option_callback = json_option_callback
_verbose_option_callback = verbose_option_callback
_version_option_callback = version_option_callback


app = LazyCommandGroup(
    name="sdd",
    help="Providence CLI - Spec Driven Development Toolkit",
    params=[
        click.Option(
            ["--profile"],
            type=click.Choice(["master", "client"], case_sensitive=False),
            default=None,
            is_eager=True,
            expose_value=True,
            callback=_profile_option_callback,
            help="Override active profile (master|client). Default: auto-detected.",
        ),
        click.Option(
            ["--json"],
            is_flag=True,
            default=False,
            expose_value=True,
            is_eager=True,
            callback=_json_option_callback,
            help="Emit JSON output for commands supporting structured output.",
        ),
        click.Option(
            ["--verbose", "-v"],
            is_flag=True,
            default=False,
            expose_value=True,
            is_eager=True,
            callback=_verbose_option_callback,
            help="Enable verbose output for commands supporting detailed mode.",
        ),
        click.Option(
            ["--version"],
            is_flag=True,
            default=False,
            expose_value=False,
            is_eager=True,
            callback=_version_option_callback,
            help="Show the installed providence-cli version and exit.",
        ),
    ],
)


def main() -> int:
    """Main."""
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        from providence_core.log_config import configure_logging

        configure_logging()
    except ImportError:
        logging.debug(
            "providence_core.log_config not available; using stdlib logging defaults."
        )
    try:
        result = app(standalone_mode=False)
        if isinstance(result, int):
            return result
    except (click.exceptions.Exit, typer.Exit) as exc:
        return int(exc.exit_code)
    except (click.ClickException, typer_click_exceptions.ClickException) as exc:
        exc.show(file=sys.stderr)
        return int(exc.exit_code)
    except OperationalCliError as exc:
        render_operational_error(exc)
        return int(exc.exit_code)
    except ProcessRunnerError as exc:
        operational_error = operational_error_from_exception(exc)
        if operational_error is None:
            raise
        render_operational_error(operational_error)
        return int(operational_error.exit_code)
    except OSError as exc:
        operational_error = operational_error_from_exception(exc)
        if operational_error is None:
            raise
        render_operational_error(operational_error)
        return int(operational_error.exit_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
