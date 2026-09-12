"""Output/render helpers for governance score and adherence commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from providence_cli.services._governance_scoring_support import (
    ahp_check,
    artifact_candidates,
    core_hash_matches,
    render_adherence_breakdown,
    render_score_breakdown,
    resolve_profile_check,
)


def render_governance_score_output(
    *,
    checks: list[tuple[str, bool, int]],
    final_score: int,
    threshold: int,
    verbose: bool,
    console: Console,
) -> None:
    """Render governance score output and enforce threshold exit policy."""
    render_score_breakdown(
        checks=checks,
        final_score=final_score,
        threshold=threshold,
        verbose=verbose,
        console=console,
    )
    if final_score < threshold:
        raise typer.Exit(1)


def render_governance_adherence_output(
    *,
    result: dict[str, Any],
    threshold: int,
    window: int,
    verbose: bool,
    console: Console,
) -> None:
    """Render governance adherence output and enforce threshold exit policy."""
    score = render_adherence_breakdown(
        result=result,
        threshold=threshold,
        window=window,
        verbose=verbose,
        console=console,
    )
    if score < threshold:
        raise typer.Exit(1)


def run_governance_score(
    *,
    ws_root: Path,
    verbose: bool,
    threshold: int,
    console: Console,
) -> None:
    """Execute governance score checks and render output."""
    from providence_cli.utils.providence_authority import compiled_active_dir
    from providence_core.governance.handshake import AgentHandshakeProtocol
    from providence_core.governance.scoring import compute_governance_score
    from providence_core.utils.environment import (
        WorkspaceNotInitializedError,
        resolve_profile,
    )

    checks, profile_ctx = resolve_profile_check(
        ws_root=ws_root,
        resolve_profile_fn=resolve_profile,
        workspace_error_cls=WorkspaceNotInitializedError,
    )
    candidates = artifact_candidates(
        ws_root=ws_root, compiled_active_dir_fn=compiled_active_dir
    )
    artifacts_ok = any(path.exists() for path in candidates)
    checks.append(("governance artifacts compiled", artifacts_ok, 30))
    ahp_result, _ = ahp_check(ws_root=ws_root, handshake_cls=AgentHandshakeProtocol)
    checks.append(ahp_result)
    hash_ok = core_hash_matches(profile_ctx=profile_ctx, candidates=candidates)
    checks.append(("core_hash matches artifact", hash_ok, 20))

    final_score = compute_governance_score(checks)
    render_governance_score_output(
        checks=checks,
        final_score=final_score,
        threshold=threshold,
        verbose=verbose,
        console=console,
    )


def run_governance_score_cmd(
    *, verbose: bool, threshold: int, console: Console
) -> None:
    """Resolve workspace root and run governance score."""
    from providence_cli.utils.providence_authority import (
        enforce_path_policy,
        resolve_workspace_root,
    )

    ws_root = resolve_workspace_root()
    if ws_root is None:
        Console(stderr=True).print("[red]ERROR: No workspace found.[/red]")
        import typer

        raise typer.Exit(1)
    ws_root = enforce_path_policy(ws_root, workspace_root=ws_root, mode="normal")
    run_governance_score(
        ws_root=ws_root, verbose=verbose, threshold=threshold, console=console
    )


def run_governance_adherence_cmd(
    *, verbose: bool, threshold: int, window: int, console: Console
) -> None:
    """Compute and render governance adherence score."""
    from providence_cli.utils.providence_authority import resolve_workspace_root
    from providence_core.governance.compliance import compute_governance_adherence

    ws_root = resolve_workspace_root()
    try:
        result = compute_governance_adherence(
            workspace_root=ws_root, window_hours=window
        )
    except Exception as exc:
        Console(stderr=True).print(
            f"[red]ERROR computing governance adherence: {exc}[/red]"
        )
        import typer

        raise typer.Exit(1) from exc
    render_governance_adherence_output(
        result=result,
        threshold=threshold,
        window=window,
        verbose=verbose,
        console=console,
    )
