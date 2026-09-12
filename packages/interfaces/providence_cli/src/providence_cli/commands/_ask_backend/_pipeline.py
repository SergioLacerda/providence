"""providence ask  command entrypoints."""

from __future__ import annotations

import typer

from providence_cli.commands._ask_backend import app
from providence_cli.services.ask_organize import run_sdd_organize
from providence_cli.services.ask_organize import (
    should_use_organize as _should_use_organize,
)
from providence_cli.utils.output import is_json_mode

__all__ = [
    "_should_use_organize",
    "ask_cmd",
    "run_sdd_organize",
]


# ---------------------------------------------------------------------------
# providence ask
# ---------------------------------------------------------------------------


@app.command("ask")
def _ask_cli_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    dossier: bool = typer.Option(
        False, "--dossier", help="Build comprehensive task dossier with analysis."
    ),
    skill: str | None = typer.Option(  # noqa: UP045
        None, "--skill", help="Skill context (e.g., 'diagnose', 'optimize')."
    ),
    budget: int | None = typer.Option(  # noqa: UP045
        None, "--budget", help="Token budget ceiling for this query."
    ),
    full: bool = typer.Option(
        False, "--full", help="Emit detailed steps and full telemetry payload."
    ),
    log_path: str | None = typer.Option(  # noqa: UP045
        None, "--log-path", help="Custom compliance log path."
    ),
    log_format: str = typer.Option(
        "jsonl", "--log-format", help="Log format: jsonl or compact."
    ),
    tokens_input: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-input",
        help="LLM API input tokens (overrides SDD_TOKENS_INPUT).",
    ),
    tokens_output: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-output",
        help="LLM API output tokens (overrides SDD_TOKENS_OUTPUT).",
    ),
    intake_only: bool = typer.Option(
        False,
        "--intake-only",
        help=(
            "Cheap hook-mode profile: execution_gate/intake_index_mode/intent "
            "with compact runtime handbook hints."
        ),
    ),
) -> None:
    """Query Providence governance context  minimal governed output."""
    from providence_cli.commands import _ask_backend as _backend

    token = _backend._JSON_MODE_OVERRIDE.set(is_json_mode(ctx))
    try:
        ask_cmd(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            intake_only=intake_only,
        )
    finally:
        _backend._JSON_MODE_OVERRIDE.reset(token)


def ask_cmd(
    query: str,
    dossier: bool = False,
    skill: str | None = None,
    budget: int | None = None,
    full: bool = False,
    log_path: str | None = None,
    log_format: str = "jsonl",
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    *,
    intake_only: bool = False,
    output_json: bool | None = None,
) -> None:
    """Query Providence governance context  minimal governed output."""
    from providence_cli.commands import _ask_backend as _backend

    token = (
        _backend._JSON_MODE_OVERRIDE.set(output_json)
        if output_json is not None
        else None
    )
    try:
        _backend._ask_cmd_impl(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            intake_only=intake_only,
        )
    finally:
        if token is not None:
            _backend._JSON_MODE_OVERRIDE.reset(token)
