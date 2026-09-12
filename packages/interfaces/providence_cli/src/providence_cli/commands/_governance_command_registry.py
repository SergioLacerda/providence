"""Registration helpers for governance CLI subcommands."""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.console import Console

from providence_cli.services.governance_config_handlers import run_governance_load_cmd
from providence_cli.services.governance_preflight_handlers import (
    run_governance_preflight_cmd,
)
from providence_cli.services.governance_registry_handlers import (
    run_reconcile_registries,
)
from providence_cli.services.governance_runtime_handlers import (
    run_governance_audit,
    run_governance_handshake,
)
from providence_cli.services.governance_scoring_output import (
    run_governance_adherence_cmd,
    run_governance_score_cmd,
)
from providence_cli.services.governance_validate_handlers import (
    run_governance_validate_cmd,
)
from providence_cli.utils.command_errors import handle_cli_errors
from providence_cli.utils.providence_authority import resolve_workspace_root


def register_governance_commands(
    *,
    app: typer.Typer,
    console: Console,
    ctx_json_fn: Callable[[], bool],
) -> None:
    @app.command("reconcile-registries")
    @handle_cli_errors(command_name="governance reconcile-registries")
    def reconcile_registries_cmd(
        json_output: bool = typer.Option(
            False, "--json", help="Emit machine-readable reconciliation summary."
        ),
        check: bool = typer.Option(
            False,
            "--check",
            help="Check drift without rewriting registries. Exits non-zero when drift exists.",
        ),
    ) -> None:
        """Rebuild commands/skills registries from canonical .providence disk artifacts."""
        run_reconcile_registries(
            ws_root=resolve_workspace_root(),
            check=check,
            json_output=bool(json_output or ctx_json_fn()),
            console=console,
        )

    @app.command()
    @handle_cli_errors(command_name="governance load")
    def load(
        path: str = typer.Option(
            ".providence/compiled",
            help="Path to governance configuration (default: .providence/compiled)",
        ),
    ) -> None:
        """Load and display governance configuration summary."""
        run_governance_load_cmd(path=path, output_json=ctx_json_fn(), console=console)

    @app.command()
    @handle_cli_errors(
        command_name="governance validate",
        next_hint="run 'providence governance compile' to rebuild artifacts",
    )
    def validate(
        path: str = typer.Option(
            ".providence/compiled",
            help="Path to governance configuration (default: .providence/compiled)",
        ),
        signature_mode: str = typer.Option(
            "warn", help="Signature enforcement mode: off|warn|strict"
        ),
        skip_handshake: bool = typer.Option(
            False,
            "--skip-handshake",
            help="Skip M015 handshake check (use in CI pipelines)",
        ),
    ) -> None:
        """Validate governance integrity (structure + runtime preflight)."""
        run_governance_validate_cmd(
            path=path,
            signature_mode=signature_mode,
            skip_handshake=skip_handshake,
            output_json=ctx_json_fn(),
            console=console,
        )

    @app.command()
    @handle_cli_errors(command_name="governance preflight")
    def preflight(
        path: str = typer.Option(
            ".providence/compiled",
            help="Path to governance configuration (default: .providence/compiled)",
        ),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--no-dry-run",
            help="Explain which checks would pass per mandate without gating or mutating anything (always read-only).",
        ),
    ) -> None:
        """Explain, per mandate, whether governance checks would pass. Never blocks or mutates."""
        del dry_run  # this command is always a dry run; the flag documents intent
        run_governance_preflight_cmd(
            path=path,
            output_json=ctx_json_fn(),
            console=console,
        )

    @app.command()
    def score(
        verbose: bool = typer.Option(
            False, "--verbose", "-v", help="Show per-check breakdown."
        ),
        threshold: int = typer.Option(
            80, "--threshold", "-t", help="Minimum passing score (0-100)."
        ),
    ) -> None:
        """Compute governance health score (0-100)."""
        run_governance_score_cmd(verbose=verbose, threshold=threshold, console=console)

    @app.command()
    def adherence(
        verbose: bool = typer.Option(
            False, "--verbose", "-v", help="Show per-dimension breakdown."
        ),
        threshold: int = typer.Option(
            80, "--threshold", "-t", help="Minimum passing score (0-100)."
        ),
        window: int = typer.Option(
            24, "--window", "-w", help="Time window in hours for behavioral events."
        ),
    ) -> None:
        """Compute governance adherence score (0-100)."""
        run_governance_adherence_cmd(
            verbose=verbose, threshold=threshold, window=window, console=console
        )

    @app.command()
    @handle_cli_errors(command_name="governance audit")
    def audit(
        verbose: bool = typer.Option(
            False, "--verbose", "-v", help="Show detailed issues and remediations"
        ),
    ) -> None:
        """Perform a Security Audit of the governance runtime."""
        run_governance_audit(
            verbose=verbose, output_json=ctx_json_fn(), console=console
        )

    @app.command()
    @handle_cli_errors(command_name="governance handshake")
    def handshake(
        response: str | None = typer.Option(
            None, "--response", "-r", help="Agent Handshake Response (JSON string)"
        ),
        init: bool = typer.Option(
            False, "--init", help="Generate a Handshake Challenge for the agent"
        ),
        task_desc: str = typer.Option(
            "General Task", "--task", help="Task description for the challenge"
        ),
        output_mode: str = typer.Option(
            "compact", "--mode", help="Output mode: silent, compact, verbose"
        ),
    ) -> None:
        """Bidirectional handshake protocol (M015)."""
        run_governance_handshake(
            response=response,
            init=init,
            task_desc=task_desc,
            output_mode=output_mode,
            output_json=ctx_json_fn(),
            console=console,
        )
