"""Rule registry mixin — decisions, active rules and impact-driven rollback."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class _RuleRegistryMixin:
    """Rule decision, activation and impact tracking for SupervisedLearningStore."""

    _candidates_path: Path
    _registry_path: Path
    _impact_path: Path

    def _read_json(self, path: Path, default: Any) -> Any:
        pass

    def _write_json(self, path: Path, payload: Any) -> None:
        pass

    def decide_rule(
        self,
        *,
        candidate_id: str,
        approved: bool,
        reviewer: str,
        rationale: str,
        ttl_days: int = 30,
    ) -> dict[str, Any]:
        """Record an approval/rejection decision for a rule candidate."""
        candidates_payload = self._read_json(self._candidates_path, {"candidates": []})
        candidate = next(
            (
                c
                for c in candidates_payload.get("candidates", [])
                if c.get("candidate_id") == candidate_id
            ),
            None,
        )
        if candidate is None:
            return {"status": "missing_candidate", "candidate_id": candidate_id}

        registry = self._read_json(self._registry_path, {"rules": []})
        decision = {
            "candidate_id": candidate_id,
            "approved": approved,
            "reviewer": reviewer,
            "rationale": rationale,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "ttl_days": ttl_days,
        }
        if approved:
            registry["rules"].append(
                {
                    "rule_id": f"rr-{uuid4().hex[:12]}",
                    "candidate_id": candidate_id,
                    "pattern": candidate["pattern"],
                    "proposed_guardrail": candidate["proposed_guardrail"],
                    "active_from": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (
                        datetime.now(timezone.utc) + timedelta(days=ttl_days)
                    ).isoformat(),
                    "status": "active",
                    "decision": decision,
                }
            )
            self._write_json(self._registry_path, registry)
        return {"status": "ok", "decision": decision}

    def list_active_rules(self) -> list[dict[str, Any]]:
        """List Active Rules."""
        now = datetime.now(timezone.utc)
        registry = self._read_json(self._registry_path, {"rules": []})
        active: list[dict[str, Any]] = []
        changed = False
        for rule in registry.get("rules", []):
            expires_at = datetime.fromisoformat(str(rule.get("expires_at")))
            if expires_at <= now and rule.get("status") == "active":
                rule["status"] = "expired"
                changed = True
            if rule.get("status") == "active":
                active.append(rule)
        if changed:
            self._write_json(self._registry_path, registry)
        return active

    def record_rule_impact(
        self,
        *,
        rule_id: str,
        rework_delta: float,
        false_block_rate: float,
        escalation_delta: float,
        rollback_flag: bool,
    ) -> None:
        """Record rule impact metrics and optionally rollback active rules."""
        payload = {
            "rule_id": rule_id,
            "rework_delta": rework_delta,
            "false_block_rate": false_block_rate,
            "escalation_delta": escalation_delta,
            "rollback_flag": rollback_flag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._impact_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        if rollback_flag:
            self._rollback_rule(rule_id)

    def _rollback_rule(self, rule_id: str) -> None:
        registry = self._read_json(self._registry_path, {"rules": []})
        changed = False
        for rule in registry.get("rules", []):
            if rule.get("rule_id") == rule_id and rule.get("status") == "active":
                rule["status"] = "rolled_back"
                rule["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
                changed = True
        if changed:
            self._write_json(self._registry_path, registry)
