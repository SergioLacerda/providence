"""Integration tests for SkillEngine (facade over SkillRegistry + SkillExecutor)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from providence_runtime import (
    SkillContractError,
    SkillEngine,
    format_governance_footer,
    validate_awakening_profile,
    validate_skill_definition,
)

# ---------------------------------------------------------------------------
# Contract validation (stateless — no engine needed)
# ---------------------------------------------------------------------------


def test_validate_skill_definition_rejects_missing_fields() -> None:
    with pytest.raises(SkillContractError, match="missing_fields"):
        validate_skill_definition({"name": "x"})


def test_validate_awakening_profile_rejects_missing_fields() -> None:
    with pytest.raises(SkillContractError, match="missing_fields"):
        validate_awakening_profile({"activation_profile": "executor"})


def test_validate_skill_definition_rejects_invalid_contract_types() -> None:
    payload = {
        "name": "sdd-validate-governance",
        "version": "1.0.0",
        "category": "governance",
        "description": "desc",
        "outcomes": "policy_result",
        "execution_path": "PATH_A",
        "allowed_tools": ["providence governance validate"],
        "cli_fallback": ["providence governance validate"],
        "required_permissions": ["workspace-read"],
        "budget_policy": {"token_budget": "medium"},
        "escalation_policy": {"mode": "warn"},
        "telemetry_policy": {"emit_runtime_event": True},
        "validation_policy": {"require_preflight": True},
        "risk_score": "medium",
    }
    with pytest.raises(SkillContractError, match="invalid_type:outcomes"):
        validate_skill_definition(payload)


def test_format_governance_footer_contract() -> None:
    footer = format_governance_footer(drift="none", governance="ok", profile="executor")
    assert (
        footer == "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=executor"
    )


# ---------------------------------------------------------------------------
# SkillEngine facade — basic wiring
# ---------------------------------------------------------------------------


def test_engine_list_skills_delegates_to_registry(tmp_path: Path) -> None:
    engine = SkillEngine(project_root=tmp_path)
    skills = engine.list_skills()
    assert skills
    assert all(s.name.startswith("sdd-") for s in skills)


def test_engine_get_skill_by_short_name(tmp_path: Path) -> None:
    engine = SkillEngine(project_root=tmp_path)
    skill = engine.get_skill("diagnose")
    assert skill is not None
    assert skill.name == "sdd-diagnose"


def test_engine_export_payload_excludes_aliases(tmp_path: Path) -> None:
    payload = SkillEngine(project_root=tmp_path).export_skills_payload("json")
    names = {item["name"] for item in payload["skills"]}
    assert "sdd-diagnose" in names
    assert "diagnose" not in names


def test_engine_run_skill_returns_missing_skill(tmp_path: Path) -> None:
    engine = SkillEngine(project_root=tmp_path)
    result = engine.run_skill("does-not-exist")
    assert result.exit_code == 1
    assert result.policy_result == "missing_skill"
    assert result.governance_footer


# ---------------------------------------------------------------------------
# Disk loading integration
# ---------------------------------------------------------------------------


def test_load_skills_from_disk_ignores_non_canonical_names(tmp_path: Path) -> None:
    from providence_runtime import _skill_registry as registry_module

    if registry_module.yaml is None:
        pytest.skip("PyYAML is required for disk skill loading test")

    skills_dir = tmp_path / ".providence" / "skills"
    (skills_dir / "diagnose").mkdir(parents=True)
    (skills_dir / "sdd-diagnose").mkdir(parents=True)
    (skills_dir / "registry.json").write_text(
        json.dumps({"skills": [{"name": "diagnose"}, {"name": "sdd-diagnose"}]}),
        encoding="utf-8",
    )
    skill_yaml = """name: sdd-diagnose
version: "1.0.0"
category: analysis
description: Canonical diagnose
when_to_use:
  - failing checks
outcomes:
  - policy_result
allowed_tools:
  - providence doctor run
cli_fallback:
  - providence doctor run
required_permissions:
  - workspace-read
"""
    (skills_dir / "diagnose" / "skill.yaml").write_text(skill_yaml, encoding="utf-8")
    (skills_dir / "sdd-diagnose" / "skill.yaml").write_text(
        skill_yaml, encoding="utf-8"
    )

    engine = SkillEngine(project_root=tmp_path)
    loaded_names = {skill.name for skill in engine.list_skills()}
    assert "sdd-diagnose" in loaded_names
    assert "diagnose" not in loaded_names


def test_load_skills_from_disk_preserves_config_payload(tmp_path: Path) -> None:
    from providence_runtime import _skill_registry as registry_module

    if registry_module.yaml is None:
        pytest.skip("PyYAML is required for disk skill loading test")

    skills_dir = tmp_path / ".providence" / "skills" / "sdd-pipeline"
    skills_dir.mkdir(parents=True)
    (tmp_path / ".providence" / "skills" / "registry.json").write_text(
        json.dumps({"skills": [{"name": "sdd-pipeline"}]}),
        encoding="utf-8",
    )
    (skills_dir / "skill.yaml").write_text(
        """name: sdd-pipeline
version: "1.0.0"
category: orchestrator
description: Pipeline
when_to_use: [pipeline]
outcomes: [policy_result]
allowed_tools: [providence ask]
cli_fallback: [providence ask]
required_permissions: [workspace-read]
config:
  pipeline:
    stages: [sdd-ask, sdd-diagnose]
    decision_gates:
      diagnose_to_correct_min_confidence: 0.61
""",
        encoding="utf-8",
    )

    engine = SkillEngine(project_root=tmp_path)
    skill = engine.get_skill("sdd-pipeline")
    assert skill is not None
    assert (
        skill.config["pipeline"]["decision_gates"]["diagnose_to_correct_min_confidence"]
        == 0.61
    )


# ---------------------------------------------------------------------------
# sdd-correct integration
# ---------------------------------------------------------------------------


def test_correct_escalates_on_inconclusive_diagnosis(tmp_path: Path) -> None:
    from unittest.mock import patch

    engine = SkillEngine(project_root=tmp_path)
    task_id = "task-1"
    context = {
        "execution_contract": {
            "allowed_paths": ["packages/core/providence_runtime/src"],
            "task_id": task_id,
        },
        "diagnosis_report": {
            "hypothesis": "policy_mismatch",
            "root_cause": "unknown",
            "evidence_refs": ["log://x"],
            "confidence": 0.2,
        },
        "diagnosis_attestation": {
            "task_id": task_id,
            "hypothesis": "policy_mismatch",
            "root_cause": "unknown",
            "evidence_refs": ["log://x"],
            "confidence": 0.2,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
    }
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = engine.run_skill("sdd-correct", context=context, project_root=tmp_path)
    assert result.policy_result == "escalated"
    assert result.artifacts["gate_decision"]["reason_code"] == "diagnosis.inconclusive"


def test_correct_denies_scope_violation(tmp_path: Path) -> None:
    from unittest.mock import patch

    engine = SkillEngine(project_root=tmp_path)
    task_id = "task-2"
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": task_id},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.9,
        },
        "diagnosis_attestation": {
            "task_id": task_id,
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.9,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["unsafe/path"],
    }
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = engine.run_skill("sdd-correct", context=context, project_root=tmp_path)
    assert result.policy_result == "denied"
    assert result.artifacts["gate_decision"]["reason_code"] == "scope.violation"


def test_correct_allows_with_valid_contract_and_evidence(tmp_path: Path) -> None:
    from unittest.mock import patch

    engine = SkillEngine(project_root=tmp_path)
    task_id = "task-3"
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": task_id},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.91,
        },
        "diagnosis_attestation": {
            "task_id": task_id,
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.91,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["safe/path"],
    }
    with (
        patch(
            "providence_core.utils.process.SafeProcessRunner", side_effect=RuntimeError
        ),
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
    ):
        result = engine.run_skill(
            "sdd-correct", context=context, execute=True, project_root=tmp_path
        )
    assert result.artifacts["gate_decision"]["decision"] == "allow"


# ---------------------------------------------------------------------------
# Learning / convergence integration
# ---------------------------------------------------------------------------


def test_learning_generates_rule_candidate_from_recurrence(tmp_path: Path) -> None:
    from unittest.mock import patch

    engine = SkillEngine(project_root=tmp_path)
    task_id = "task-4"
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": task_id},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e1"],
            "confidence": 0.95,
        },
        "diagnosis_attestation": {
            "task_id": task_id,
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e1"],
            "confidence": 0.95,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["safe/path"],
    }
    with (
        patch(
            "providence_core.utils.process.SafeProcessRunner", side_effect=RuntimeError
        ),
        patch(
            "providence_runtime.policy.PolicyEngine._check_handshake_guard",
            return_value=None,
        ),
    ):
        engine.run_skill(
            "sdd-correct", context=context, execute=True, project_root=tmp_path
        )
        second = engine.run_skill(
            "sdd-correct", context=context, execute=True, project_root=tmp_path
        )
    candidates = second.artifacts.get("rule_candidates", [])
    assert candidates
    assert candidates[0]["pattern"] == "h|r"


def test_converge_rule_approval_and_ttl_expiration(tmp_path: Path) -> None:
    from unittest.mock import patch

    from providence_runtime.learning import SupervisedLearningStore

    engine = SkillEngine(project_root=tmp_path)
    store = SupervisedLearningStore(tmp_path)
    store._write_json(  # type: ignore[attr-defined]
        tmp_path / ".providence" / "runtime" / "rule-candidates.json",
        {
            "candidates": [
                {
                    "candidate_id": "rc-1",
                    "pattern": "h|r",
                    "proposed_guardrail": "g",
                    "risk_level": "medium",
                    "expected_impact": "reduce_rework",
                    "evidence_refs": ["e"],
                    "source_count": 2,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        },
    )
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = engine.run_skill(
            "sdd-converge",
            context={
                "rule_decision": {
                    "candidate_id": "rc-1",
                    "approved": True,
                    "reviewer": "human",
                    "rationale": "ok",
                    "ttl_days": 0,
                }
            },
            project_root=tmp_path,
        )
    assert result.artifacts["rule_decision"]["status"] == "ok"
    assert not store.list_active_rules()


def test_negative_learning_rolls_back_rule(tmp_path: Path) -> None:
    from providence_runtime.learning import SupervisedLearningStore

    store = SupervisedLearningStore(tmp_path)
    store._write_json(  # type: ignore[attr-defined]
        tmp_path / ".providence" / "runtime" / "rule-registry.json",
        {
            "rules": [
                {
                    "rule_id": "rr-1",
                    "candidate_id": "rc-1",
                    "pattern": "h|r",
                    "proposed_guardrail": "g",
                    "active_from": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (
                        datetime.now(timezone.utc) + timedelta(days=30)
                    ).isoformat(),
                    "status": "active",
                    "decision": {},
                }
            ]
        },
    )
    store.record_rule_impact(
        rule_id="rr-1",
        rework_delta=-0.1,
        false_block_rate=0.7,
        escalation_delta=0.4,
        rollback_flag=True,
    )
    registry = json.loads(
        (tmp_path / ".providence" / "runtime" / "rule-registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert registry["rules"][0]["status"] == "rolled_back"


def test_learning_store_lists_recent_and_similar_failures(tmp_path: Path) -> None:
    from providence_runtime.learning import FailureLedgerEntry, SupervisedLearningStore

    store = SupervisedLearningStore(tmp_path)
    store.append_failure(
        FailureLedgerEntry(
            symptom="policy_mismatch",
            root_cause="missing_mandate",
            fix="sdd-diagnose",
            validation="postcheck",
            regression=False,
            tags=["diagnose", "executed"],
            evidence_refs=["e1"],
            timestamp="2026-01-01T00:00:00+00:00",
        )
    )
    store.append_failure(
        FailureLedgerEntry(
            symptom="policy_mismatch",
            root_cause="missing_mandate",
            fix="sdd-correct",
            validation="postcheck",
            regression=False,
            tags=["correct", "executed"],
            evidence_refs=["e2"],
            timestamp="2026-01-01T00:01:00+00:00",
        )
    )

    recent = store.list_failures(limit=1)
    similar = store.find_similar_failures(
        symptom="policy_mismatch", root_cause="missing_mandate", limit=5
    )

    assert len(recent) == 1
    assert recent[0]["fix"] == "sdd-correct"
    assert len(similar) == 2
