"""providence init  operational-error helpers, runtime marker, and bootstrap orchestration.

Split out of `init.py` (T5,
`.analysis/pending/2026-06-15-providence-cli-refactoring-pending-followup.md`):
`init()` itself (151 lines) was the dominant function even after the prior
split (`init_steps.py`). These two blocks are the largest separable phases of
its body beyond the fixed typer option signature.
"""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer

from providence_cli.commands.init_steps import _emit_workspace_init_telemetry
from providence_cli.services.onboarding import OnboardingOrchestrator
from providence_cli.utils.operational_errors import (
    OperationalCliError,
    operational_error_from_exception,
    render_operational_error,
)
from providence_core.utils.environment import ProfileContext, SddProfile

_LANGUAGE_CANONICAL = {"en": "en", "pt-br": "pt-BR"}


def _normalize_language_or_exit(language: str | None) -> str | None:
    """Case-fold --language input to its canonical stored form (en | pt-BR)."""
    if language is None:
        return None
    canonical = _LANGUAGE_CANONICAL.get(language.strip().lower())
    if canonical is None:
        typer.echo("[SDD] ERROR: --language must be 'en' or 'pt-BR'.", err=True)
        raise typer.Exit(2)
    return canonical


def _raise_init_operational_error(
    exc: BaseException,
    *,
    headline: str,
    step: str,
    operation: str,
    path: Path,
    next_hint: str = "check folder permissions, then retry: providence init --force",
) -> NoReturn:
    operational_error = operational_error_from_exception(
        exc,
        headline=headline,
        command="providence init",
        step=step,
        operation=operation,
        path=path,
        next_hint=next_hint,
    )
    if operational_error is None:
        raise exc
    _exit_init_operational_error(operational_error)


def _exit_init_operational_error(error: OperationalCliError) -> NoReturn:
    render_operational_error(error)
    raise typer.Exit(error.exit_code) from None


def _create_runtime_marker_and_telemetry(
    cwd: Path,
    *,
    profile_ctx: ProfileContext,
    effective_name: str,
    force: bool,
    profile_type: SddProfile,
) -> None:
    runtime_dir = cwd / ".providence" / "runtime"
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        (runtime_dir / ".phase-0-complete").touch(exist_ok=True)
    except OSError as exc:
        _raise_init_operational_error(
            exc,
            headline="Could not initialize SDD runtime marker.",
            step="profile",
            operation="create runtime marker",
            path=runtime_dir / ".phase-0-complete",
        )

    _emit_workspace_init_telemetry(
        profile_ctx=profile_ctx,
        effective_name=effective_name,
        force=force,
        profile_type=profile_type,
    )


def _run_init_bootstrap(cwd: Path, *, force: bool) -> None:
    orc = OnboardingOrchestrator(cwd)
    try:
        bootstrap_result = orc.run(force=bool(force))
    except OperationalCliError as exc:
        _exit_init_operational_error(exc)
    except OSError as exc:
        operational_error = operational_error_from_exception(
            exc,
            headline="Governance activation failed because file access was denied.",
            command="providence init",
            step="bootstrap",
            operation="run onboarding",
            next_hint="close programs that may be locking .providence, then retry: providence init --force",
        )
        if operational_error is None:
            raise
        _exit_init_operational_error(operational_error)
    if bootstrap_result.success:
        typer.echo("\n Onboarding complete  workspace is HEALTHY")
    else:
        if bootstrap_result.failed_step:
            typer.echo(f"  Step: {bootstrap_result.failed_step}", err=True)
        for msg in bootstrap_result.messages:
            typer.echo(f"  ERROR: {msg}", err=True)
        raise typer.Exit(bootstrap_result.exit_code)
