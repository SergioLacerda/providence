"""Architecture review comparison and baseline persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _build_architecture_review(context: dict[str, Any]) -> dict[str, Any]:
    current_score = context.get("governance_score", 0)
    baseline_score = context.get("baseline_governance_score", current_score)
    if not isinstance(current_score, int | float):
        current_score = 0
    if not isinstance(baseline_score, int | float):
        baseline_score = current_score

    current_violations = context.get("architecture_violations", [])
    baseline_violations = context.get("baseline_architecture_violations", [])
    if not isinstance(current_violations, list):
        current_violations = []
    if not isinstance(baseline_violations, list):
        baseline_violations = []

    added = [item for item in current_violations if item not in baseline_violations]
    resolved = [item for item in baseline_violations if item not in current_violations]

    remediation_proposals: list[str] = []
    if added:
        remediation_proposals.append(
            "review added architectural violations against active mandates"
        )
    if float(current_score) < float(baseline_score):
        remediation_proposals.append(
            "run providence governance score --verbose and investigate score regression"
        )
    if not remediation_proposals:
        remediation_proposals.append(
            "architecture review is stable; keep current mandate alignment"
        )

    return {
        "governance_score": current_score,
        "baseline_governance_score": baseline_score,
        "architecture_deltas": {
            "score_delta": float(current_score) - float(baseline_score),
            "added_violations": added,
            "resolved_violations": resolved,
        },
        "remediation_proposals": remediation_proposals,
    }


def _baseline_path(project_root: Path) -> Path:
    return project_root / ".providence" / "runtime" / "architecture-baseline.json"


def _load_architecture_baseline(project_root: Path) -> dict[str, Any]:
    baseline_path = _baseline_path(project_root)
    if not baseline_path.exists():
        return {}
    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_architecture_baseline(project_root: Path, payload: dict[str, Any]) -> Path:
    baseline_path = _baseline_path(project_root)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return baseline_path
