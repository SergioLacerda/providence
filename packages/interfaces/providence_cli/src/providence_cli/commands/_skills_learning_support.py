"""Support helpers for `skills learning-*` command handlers."""

from __future__ import annotations

import json
from typing import Any

import typer

from providence_cli.commands._skills_learning_status import (
    _load_recent_impacts,
    build_learning_status,
    emit_learning_status,
    load_candidates,
)

__all__ = [
    "_load_recent_impacts",
    "build_learning_status",
    "emit_learning_candidates",
    "emit_learning_decision",
    "emit_learning_impact",
    "emit_learning_rules",
    "emit_learning_status",
    "load_candidates",
]


def emit_learning_candidates(
    *,
    created: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    output_json: bool,
    emit_fn: Any,
) -> None:
    if output_json:
        emit_fn(
            command="skills learning-candidates",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "learning_candidates_listed",
                "reason": "rule candidates loaded",
                "exit_code": 0,
                "created_count": len(created),
                "candidates": candidates,
            },
            ok=True,
        )
        return
    typer.echo(f"rule candidates: {len(candidates)} (newly created: {len(created)})")
    for candidate in candidates:
        typer.echo(
            f"- {candidate.get('candidate_id')} pattern={candidate.get('pattern')}"
        )


def emit_learning_decision(
    command: str,
    decision: dict[str, Any],
    *,
    success_policy: str,
    output_json: bool,
    emit_fn: Any,
) -> None:
    ok = decision.get("status") == "ok"
    if output_json:
        emit_fn(
            command=command,
            data={
                "state": "ok" if ok else "error",
                "profile": "default",
                "skill": None,
                "policy_result": success_policy if ok else "missing_candidate",
                "reason": "rule decision recorded",
                "exit_code": 0 if ok else 1,
                "decision": decision,
            },
            ok=ok,
            error_code="missing_candidate" if not ok else None,
            error_message="candidate not found" if not ok else None,
            err=not ok,
        )
    else:
        typer.echo(json.dumps(decision, indent=2, ensure_ascii=False))
    if not ok:
        raise typer.Exit(1)


def emit_learning_impact(
    payload: dict[str, Any], *, output_json: bool, emit_fn: Any
) -> None:
    if output_json:
        emit_fn(
            command="skills learning-impact",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "rule_impact_recorded",
                "reason": "rule impact recorded",
                "exit_code": 0,
                "impact": payload,
            },
            ok=True,
        )
        return
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def emit_learning_rules(
    rules: list[dict[str, Any]], *, output_json: bool, emit_fn: Any
) -> None:
    if output_json:
        emit_fn(
            command="skills learning-rules",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "active_rules_listed",
                "reason": "active supervised rules loaded",
                "exit_code": 0,
                "rules": rules,
            },
            ok=True,
        )
        return
    typer.echo(f"active rules: {len(rules)}")
    for rule in rules:
        typer.echo(f"- {rule.get('rule_id')} pattern={rule.get('pattern')}")
