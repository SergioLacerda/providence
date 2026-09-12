"""Supervised-learning commands for the skill layer (`providence skills learning-*`)."""

from __future__ import annotations

import click
import typer
from providence_runtime import SupervisedLearningStore

from providence_cli.commands._skills_learning_support import (
    build_learning_status,
    emit_learning_candidates,
    emit_learning_decision,
    emit_learning_impact,
    emit_learning_rules,
    emit_learning_status,
    load_candidates,
)
from providence_cli.services.skills_output import emit_skills_json as _emit_skills_json
from providence_cli.utils.output import is_json_mode
from providence_cli.utils.providence_authority import resolve_workspace_root

app = typer.Typer(help="Supervised learning rule commands")


def _ctx_json() -> bool:
    return is_json_mode(click.get_current_context(silent=True))


@app.command("learning-candidates")
def learning_candidates() -> None:
    """Learning Candidates."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    created = [item.__dict__ for item in store.generate_candidates_from_ledger()]
    candidates_path = ws_root / ".providence" / "runtime" / "rule-candidates.json"
    emit_learning_candidates(
        created=created,
        candidates=load_candidates(candidates_path),
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )


@app.command("learning-approve")
def learning_approve(
    candidate_id: str,
    reviewer: str = typer.Option("human", "--reviewer"),
    rationale: str = typer.Option(..., "--rationale"),
    ttl_days: int = typer.Option(30, "--ttl-days"),
) -> None:
    """Approve a learning rule candidate with human rationale."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    decision = store.decide_rule(
        candidate_id=candidate_id,
        approved=True,
        reviewer=reviewer,
        rationale=rationale,
        ttl_days=ttl_days,
    )
    emit_learning_decision(
        "skills learning-approve",
        decision,
        success_policy="rule_approved",
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )


@app.command("learning-reject")
def learning_reject(
    candidate_id: str,
    reviewer: str = typer.Option("human", "--reviewer"),
    rationale: str = typer.Option(..., "--rationale"),
) -> None:
    """Reject a learning rule candidate with human rationale."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    decision = store.decide_rule(
        candidate_id=candidate_id,
        approved=False,
        reviewer=reviewer,
        rationale=rationale,
        ttl_days=30,
    )
    emit_learning_decision(
        "skills learning-reject",
        decision,
        success_policy="rule_rejected",
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )


@app.command("learning-impact")
def learning_impact(
    rule_id: str,
    rework_delta: float = typer.Option(..., "--rework-delta"),
    false_block_rate: float = typer.Option(..., "--false-block-rate"),
    escalation_delta: float = typer.Option(..., "--escalation-delta"),
    rollback_flag: bool = typer.Option(False, "--rollback-flag"),
) -> None:
    """Record impact telemetry for an active learning rule."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    store.record_rule_impact(
        rule_id=rule_id,
        rework_delta=rework_delta,
        false_block_rate=false_block_rate,
        escalation_delta=escalation_delta,
        rollback_flag=rollback_flag,
    )
    payload = {
        "rule_id": rule_id,
        "rework_delta": rework_delta,
        "false_block_rate": false_block_rate,
        "escalation_delta": escalation_delta,
        "rollback_flag": rollback_flag,
    }
    emit_learning_impact(payload, output_json=_ctx_json(), emit_fn=_emit_skills_json)


@app.command("learning-rules")
def learning_rules() -> None:
    """Learning Rules."""
    ws_root = resolve_workspace_root()
    store = SupervisedLearningStore(ws_root)
    rules = store.list_active_rules()
    emit_learning_rules(rules, output_json=_ctx_json(), emit_fn=_emit_skills_json)


@app.command("learning-status")
def learning_status(
    window_days: int = typer.Option(7, "--window-days", min=1),
) -> None:
    """Show supervised learning status and recent impact metrics."""
    ws_root = resolve_workspace_root()
    emit_learning_status(
        build_learning_status(
            ws_root / ".providence" / "runtime", window_days=window_days
        ),
        output_json=_ctx_json(),
        emit_fn=_emit_skills_json,
    )
