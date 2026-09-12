"""Skills full-bootstrap orchestration: governance validation, reconciliation, and pipeline execution."""

from __future__ import annotations

import functools
from collections.abc import Callable
from pathlib import Path

import typer

from providence_cli.generators._commands import generate_commands_registry
from providence_cli.generators._indices import (
    generate_cli_commands_index,
    generate_skill_index,
)
from providence_cli.generators._skills import generate_skills_registry
from providence_cli.generators.agent_seeds import (
    generate_agent_instruction_files,
    generate_agent_prompt_commands,
    generate_agent_seeds,
)
from providence_cli.services._skills_resolver_support import (
    bootstrap_summary,
    emit_bootstrap_error,
    emit_bootstrap_text_summary,
    run_bootstrap_generation,
    run_bootstrap_generation_with_fallback,
)
from providence_cli.services.registry_reconciliation import reconcile_registries
from providence_cli.services.skills_bootstrap_validation import (
    handle_adapter_error,
    validate_and_load_governance,
)

__all__ = [
    "handle_adapter_error",
    "validate_and_load_governance",
    "run_reconcile",
    "run_full_bootstrap",
]
from providence_cli.services.skills_resolver import _generate_adapters
from providence_cli.services.skills_seed_reconciler import (
    _reconcile_root_seed_artifacts,
)


def run_reconcile(
    output_base: Path, *, dry_run: bool, output_json: bool, emit_fn: Callable[..., None]
) -> tuple[int, int]:
    """Run seed reconciliation; raises typer.Exit(1) on failure."""
    try:
        reconcile_stats = _reconcile_root_seed_artifacts(output_base, dry_run=dry_run)
        return int(reconcile_stats.get("deleted", 0)), int(
            reconcile_stats.get("would_delete", 0)
        )
    except Exception as exc:
        message = "seed reconciliation failed. Ensure canonical registries are valid and retry."
        if output_json:
            emit_bootstrap_error(
                output_json=output_json,
                emit_fn=emit_fn,
                error_code="seed_reconciliation_failed",
                reason=message,
                error_type=type(exc).__name__,
                error_message=str(exc),
                details={"error": str(exc)},
            )
        else:
            typer.echo(f"ERROR: {message}", err=True)
            typer.echo(f"- reconcile error: {exc}", err=True)
        raise typer.Exit(1) from exc


def run_full_bootstrap(
    ws_root: Path,
    *,
    regenerate_seeds: bool = False,
    dry_run: bool = False,
    output_json: bool,
    emit_fn: Callable[..., None],
) -> None:
    """Execute full bootstrap pipeline and emit output."""
    compiled_path = ws_root / ".providence" / "compiled"
    config = validate_and_load_governance(
        compiled_path, output_json=output_json, emit_fn=emit_fn
    )

    output_base = Path(ws_root)
    (
        seeds_dir,
        seeds_info,
        skills_result,
        commands_result,
        reconciliation_summary,
        skill_index_result,
        cli_index_result,
    ) = run_bootstrap_generation_with_fallback(
        output_base=output_base,
        config=config,
        run_bootstrap_generation_fn=functools.partial(
            run_bootstrap_generation,
            generate_agent_seeds_fn=generate_agent_seeds,
            generate_agent_instruction_files_fn=generate_agent_instruction_files,
            generate_agent_prompt_commands_fn=generate_agent_prompt_commands,
            generate_skills_registry_fn=generate_skills_registry,
            generate_commands_registry_fn=generate_commands_registry,
            reconcile_registries_fn=reconcile_registries,
            generate_skill_index_fn=generate_skill_index,
            generate_cli_commands_index_fn=generate_cli_commands_index,
        ),
    )

    adapter_targets, adapter_error = _generate_adapters(output_base)
    if adapter_error is not None:
        handle_adapter_error(adapter_error, output_json=output_json, emit_fn=emit_fn)

    deleted_count = 0
    would_delete_count = 0
    if regenerate_seeds:
        deleted_count, would_delete_count = run_reconcile(
            output_base, dry_run=dry_run, output_json=output_json, emit_fn=emit_fn
        )

    if output_json:
        emit_fn(
            command="skills full-bootstrap",
            data={
                "state": "ok",
                "policy_result": "skills_full_bootstrap_completed",
                "reason": "generated all available skills/commands/seeds artifacts",
                "exit_code": 0,
                "summary": bootstrap_summary(
                    output_base=output_base,
                    compiled_path=compiled_path,
                    seeds_dir=seeds_dir,
                    seeds_info=seeds_info,
                    skills_result=skills_result,
                    commands_result=commands_result,
                    skill_index_result=skill_index_result,
                    cli_index_result=cli_index_result,
                    adapter_targets=adapter_targets,
                    reconciliation_summary=reconciliation_summary,
                    deleted_count=deleted_count,
                    would_delete_count=would_delete_count,
                    dry_run=dry_run,
                ),
            },
            ok=True,
        )
        return

    emit_bootstrap_text_summary(
        output_base=output_base,
        compiled_path=compiled_path,
        seeds_dir=seeds_dir,
        seeds_info=seeds_info,
        skills_result=skills_result,
        commands_result=commands_result,
        reconciliation_summary=reconciliation_summary,
        regenerate_seeds=regenerate_seeds,
        dry_run=dry_run,
        deleted_count=deleted_count,
        would_delete_count=would_delete_count,
        echo_fn=typer.echo,
    )
