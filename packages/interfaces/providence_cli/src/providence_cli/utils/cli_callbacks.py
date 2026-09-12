"""Eager option callbacks for the root `sdd` Click group."""

from __future__ import annotations

import click


def profile_option_callback(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> str | None:
    """Profile Option Callback."""
    del param
    if ctx.obj is None:
        ctx.obj = {}
    if value:
        ctx.obj["profile"] = value
        ctx.obj["is_master"] = value == "master"
        ctx.obj["is_client"] = value == "client"
    return value


def json_option_callback(
    ctx: click.Context, param: click.Parameter, value: bool
) -> bool:
    """Json Option Callback."""
    del param
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["output_json"] = bool(value)
    return value


def verbose_option_callback(
    ctx: click.Context, param: click.Parameter, value: bool
) -> bool:
    """Verbose Option Callback."""
    del param
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["verbose"] = bool(value)
    return value


def version_option_callback(
    ctx: click.Context, param: click.Parameter, value: bool
) -> bool:
    """Version Option Callback. Prints the installed providence-cli version and exits."""
    del param
    if not value:
        return value
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    try:
        click.echo(_pkg_version("providence-cli"))
    except PackageNotFoundError:
        click.echo("providence-cli version unknown (not installed as a package)")
    ctx.exit(0)
    return value
