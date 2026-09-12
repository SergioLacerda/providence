"""Rendering helpers for the skills command group."""

from __future__ import annotations

import json
from typing import Any

import typer


def emit_skills_list(skills: list[Any], *, output_json: bool, emit_fn: Any) -> None:
    if output_json:
        emit_fn(
            command="skills list",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "listed",
                "reason": "skills loaded",
                "exit_code": 0,
                "skills": [
                    {
                        "name": skill.name,
                        "version": skill.version,
                        "category": skill.category,
                        "status": skill.status,
                        "risk_score": skill.risk_score,
                    }
                    for skill in skills
                ],
            },
            ok=True,
        )
        return
    typer.echo("Available skills:")
    for skill in skills:
        typer.echo(
            f"- {skill.name} ({skill.version}) [{skill.category}] "
            f"risk={skill.risk_score} status={skill.status}"
        )


def emit_skill_description(
    name: str, skill: Any | None, *, output_json: bool, emit_fn: Any
) -> None:
    if skill is None:
        if output_json:
            emit_fn(
                command="skills describe",
                data={
                    "state": "error",
                    "profile": "default",
                    "skill": name,
                    "policy_result": "missing_skill",
                    "reason": "skill not found",
                    "error": {"type": "LookupError", "message": "skill not found"},
                    "exit_code": 1,
                },
                ok=False,
                error_code="missing_skill",
                error_message="skill not found",
                err=True,
            )
        else:
            typer.echo(f"ERROR: Skill not found: {name}", err=True)
        raise typer.Exit(1)

    payload = skill.to_dict()
    if output_json:
        emit_fn(
            command="skills describe",
            data={
                "state": "ok",
                "profile": "default",
                "skill": name,
                "policy_result": "described",
                "reason": "skill metadata loaded",
                "exit_code": 0,
                "definition": payload,
            },
            ok=True,
        )
        return
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def emit_pipeline_required(name: str, *, output_json: bool, emit_fn: Any) -> None:
    message = "pipeline_required_for_sdd_correct"
    if output_json:
        emit_fn(
            command="skills run",
            data={
                "state": "error",
                "profile": name,
                "skill": name,
                "policy_result": "denied",
                "reason": message,
                "error": {"type": "PermissionError", "message": message},
                "exit_code": 1,
                "next_action": "providence skills run sdd-pipeline",
            },
            ok=False,
            error_code="pipeline_required_for_sdd_correct",
            error_message=message,
            err=True,
        )
    else:
        typer.echo(
            "ERROR: sdd-correct direto bloqueado por poltica. "
            "Use: providence skills run sdd-pipeline",
            err=True,
        )
    raise typer.Exit(1)


def emit_skill_run_result(result: Any, *, output_json: bool, emit_fn: Any) -> None:
    if output_json:
        emit_fn(
            command="skills run",
            data={
                "state": result.state,
                "profile": result.profile,
                "skill": result.skill,
                "policy_result": result.policy_result,
                "reason": result.reason,
                "exit_code": result.exit_code,
                "governance_footer": result.governance_footer,
                "fallback": result.fallback,
                "command_results": result.command_results,
                "artifacts": result.artifacts,
            },
            ok=result.exit_code == 0,
            error_code=result.policy_result if result.exit_code != 0 else None,
            error_message=result.reason if result.exit_code != 0 else None,
        )
    else:
        typer.echo(f"skill={result.skill}")
        typer.echo(f"policy_result={result.policy_result}")
        typer.echo(f"reason={result.reason}")
        typer.echo("fallback commands:")
        for command in result.fallback:
            typer.echo(f"  - {command}")
        typer.echo(result.governance_footer)

    if result.exit_code != 0:
        raise typer.Exit(result.exit_code)


def emit_skills_export(
    format_name: str, payload: dict[str, Any], *, output_json: bool, emit_fn: Any
) -> None:
    if output_json or format_name == "json":
        emit_fn(
            command="skills export",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "exported",
                "reason": f"exported as {format_name}",
                "exit_code": 0,
                "payload": payload,
            },
            ok=True,
        )
        return
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
