"""Learning status computation and emission helpers for `skills learning-status`."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import typer


def load_candidates(candidates_path: Path) -> list[dict[str, Any]]:
    if not candidates_path.exists():
        return []
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    value = payload.get("candidates", [])
    return value if isinstance(value, list) else []


def _load_recent_impacts(impact_path: Path, cutoff: datetime) -> list[dict[str, Any]]:
    recent: list[dict[str, Any]] = []
    if not impact_path.exists():
        return recent
    for line in impact_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            dt = datetime.fromisoformat(str(row.get("timestamp")))
        except ValueError:
            continue
        if dt >= cutoff:
            recent.append(row)
    return recent


def build_learning_status(runtime_dir: Path, *, window_days: int) -> dict[str, Any]:
    candidates = len(load_candidates(runtime_dir / "rule-candidates.json"))
    rules_payload: dict[str, Any] = {"rules": []}
    registry_path = runtime_dir / "rule-registry.json"
    if registry_path.exists():
        rules_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    rules = rules_payload.get("rules", [])
    active_rules = sum(1 for rule in rules if rule.get("status") == "active")
    rolled_back_rules = sum(1 for rule in rules if rule.get("status") == "rolled_back")
    expired_rules = sum(1 for rule in rules if rule.get("status") == "expired")
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    recent_impacts = _load_recent_impacts(runtime_dir / "rule-impact.jsonl", cutoff)
    impact_count = len(recent_impacts)
    avg_false_block_rate = (
        sum(float(item.get("false_block_rate", 0.0)) for item in recent_impacts)
        / impact_count
        if impact_count
        else 0.0
    )
    avg_rework_delta = (
        sum(float(item.get("rework_delta", 0.0)) for item in recent_impacts)
        / impact_count
        if impact_count
        else 0.0
    )
    return {
        "window_days": window_days,
        "candidates_total": candidates,
        "rules_total": len(rules),
        "rules_active": active_rules,
        "rules_rolled_back": rolled_back_rules,
        "rules_expired": expired_rules,
        "impacts_recent": impact_count,
        "avg_false_block_rate_recent": round(avg_false_block_rate, 6),
        "avg_rework_delta_recent": round(avg_rework_delta, 6),
        "kpi_rework_reduction_pct_recent": round(
            max(0.0, -avg_rework_delta * 100.0), 4
        ),
        "rollbacks_recent": sum(
            1 for item in recent_impacts if item.get("rollback_flag") is True
        ),
    }


def emit_learning_status(
    status: dict[str, Any], *, output_json: bool, emit_fn: Any
) -> None:
    if output_json:
        emit_fn(
            command="skills learning-status",
            data={
                "state": "ok",
                "profile": "default",
                "skill": None,
                "policy_result": "learning_status_loaded",
                "reason": "supervised learning status summary",
                "exit_code": 0,
                "status": status,
            },
            ok=True,
        )
        return
    typer.echo(json.dumps(status, indent=2, ensure_ascii=False))
