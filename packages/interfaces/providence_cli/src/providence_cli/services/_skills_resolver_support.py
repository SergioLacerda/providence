"""Support helpers for skills bootstrap orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def emit_bootstrap_error(
    *,
    output_json: bool,
    emit_fn: Any,
    error_code: str,
    reason: str,
    error_type: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> None:
    if output_json:
        payload = {
            "state": "error",
            "policy_result": error_code,
            "reason": reason,
            "error": {"type": error_type, "message": error_message},
            "exit_code": 1,
        }
        if details:
            payload["details"] = details
        emit_fn(
            command="skills full-bootstrap",
            data=payload,
            ok=False,
            error_code=error_code,
            error_message=error_message,
            err=True,
        )


def bootstrap_summary(
    *,
    output_base: Path,
    compiled_path: Path,
    seeds_dir: Path,
    seeds_info: list[Any],
    skills_result: dict[str, Any],
    commands_result: dict[str, Any],
    skill_index_result: dict[str, Any],
    cli_index_result: dict[str, Any],
    adapter_targets: int,
    reconciliation_summary: Any,
    deleted_count: int,
    would_delete_count: int,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "workspace": str(output_base),
        "compiled_path": str(compiled_path),
        "seeds_dir": str(seeds_dir),
        "seed_files": len(seeds_info),
        "skills_count": int(skills_result.get("skill_count", 0)),
        "commands_count": int(commands_result.get("command_count", 0)),
        "skill_index_count": int(skill_index_result.get("skill_count", 0)),
        "cli_index_count": int(cli_index_result.get("command_count", 0)),
        "adapter_targets": adapter_targets,
        "registry_reconciliation": reconciliation_summary.as_json(),
        "seeds_deleted": deleted_count,
        "seeds_would_delete": would_delete_count,
        "dry_run": dry_run,
    }


def run_bootstrap_generation(
    *,
    output_base: Path,
    seeds_dir: Path,
    config: dict[str, Any],
    generate_agent_seeds_fn: Any,
    generate_agent_instruction_files_fn: Any,
    generate_agent_prompt_commands_fn: Any,
    generate_skills_registry_fn: Any,
    generate_commands_registry_fn: Any,
    reconcile_registries_fn: Any,
    generate_skill_index_fn: Any,
    generate_cli_commands_index_fn: Any,
) -> tuple[
    list[Any], dict[str, Any], dict[str, Any], Any, dict[str, Any], dict[str, Any]
]:
    seeds_info = generate_agent_seeds_fn(seeds_dir, config)
    generate_agent_instruction_files_fn(output_base, config)
    generate_agent_prompt_commands_fn(output_base, config)
    skills_result = generate_skills_registry_fn(str(output_base), config)
    commands_result = generate_commands_registry_fn(str(output_base), config)
    reconciliation_summary = reconcile_registries_fn(output_base)
    skill_index_result = generate_skill_index_fn(str(output_base), config)
    cli_index_result = generate_cli_commands_index_fn(str(output_base), config)
    return (
        seeds_info,
        skills_result,
        commands_result,
        reconciliation_summary,
        skill_index_result,
        cli_index_result,
    )


def run_bootstrap_generation_with_fallback(
    *, output_base: Path, config: dict[str, Any], run_bootstrap_generation_fn: Any
) -> tuple[
    Path, list[Any], dict[str, Any], dict[str, Any], Any, dict[str, Any], dict[str, Any]
]:
    seeds_dir = output_base / ".vscode" / "agents"
    try:
        (
            seeds_info,
            skills_result,
            commands_result,
            reconciliation_summary,
            skill_index_result,
            cli_index_result,
        ) = run_bootstrap_generation_fn(
            output_base=output_base, seeds_dir=seeds_dir, config=config
        )
    except OSError:
        seeds_dir = output_base / ".providence" / "agents"
        (
            seeds_info,
            skills_result,
            commands_result,
            reconciliation_summary,
            skill_index_result,
            cli_index_result,
        ) = run_bootstrap_generation_fn(
            output_base=output_base, seeds_dir=seeds_dir, config=config
        )
    return (
        seeds_dir,
        seeds_info,
        skills_result,
        commands_result,
        reconciliation_summary,
        skill_index_result,
        cli_index_result,
    )


def emit_bootstrap_text_summary(
    *,
    output_base: Path,
    compiled_path: Path,
    seeds_dir: Path,
    seeds_info: list[Any],
    skills_result: dict[str, Any],
    commands_result: dict[str, Any],
    reconciliation_summary: Any,
    regenerate_seeds: bool,
    dry_run: bool,
    deleted_count: int,
    would_delete_count: int,
    echo_fn: Any,
) -> None:
    echo_fn("skills full bootstrap completed")
    echo_fn(f"- workspace: {output_base}")
    echo_fn(f"- compiled: {compiled_path}")
    echo_fn(f"- seeds dir: {seeds_dir}")
    echo_fn(f"- seed files: {len(seeds_info)}")
    echo_fn(f"- skills: {int(skills_result.get('skill_count', 0))}")
    echo_fn(f"- commands: {int(commands_result.get('command_count', 0))}")
    echo_fn(
        "- registries reconciled: "
        f"commands(+{reconciliation_summary.commands['added']}/-{reconciliation_summary.commands['removed']}), "
        f"skills(+{reconciliation_summary.skills['added']}/-{reconciliation_summary.skills['removed']})"
    )
    if regenerate_seeds:
        echo_fn(
            f"- stale seeds to delete (dry-run): {would_delete_count}"
            if dry_run
            else f"- stale seeds deleted: {deleted_count}"
        )
