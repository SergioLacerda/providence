from __future__ import annotations

from unittest.mock import MagicMock

from providence_runtime._skill_executor import DiagnoseHandler, _build_diagnosis_report


def test_pre_run_returns_diagnosis_report_artifact() -> None:
    handler = DiagnoseHandler()
    outcome = handler.pre_run(
        {}, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    assert "diagnosis_report" in outcome.artifacts
    assert "diagnosis_attestation" in outcome.artifacts
    assert outcome.early_result is None


def test_pre_run_applies_defaults_when_report_missing() -> None:
    handler = DiagnoseHandler()
    outcome = handler.pre_run(
        {}, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    report = outcome.artifacts["diagnosis_report"]
    assert report["hypothesis"] == "unknown"
    assert report["root_cause"] == "inconclusive"
    assert report["confidence"] == 0.0
    assert report["evidence_refs"] == []


def test_pre_run_merges_provided_report_over_defaults() -> None:
    handler = DiagnoseHandler()
    ctx = {
        "diagnosis_report": {
            "hypothesis": "policy_mismatch",
            "root_cause": "missing_mandate",
            "confidence": 0.9,
        }
    }
    outcome = handler.pre_run(
        ctx, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    report = outcome.artifacts["diagnosis_report"]
    assert report["hypothesis"] == "policy_mismatch"
    assert report["confidence"] == 0.9
    assert report["evidence_refs"] == []


def test_pre_run_treats_non_dict_report_as_empty() -> None:
    handler = DiagnoseHandler()
    ctx = {"diagnosis_report": 42}
    outcome = handler.pre_run(
        ctx, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    assert outcome.artifacts["diagnosis_report"]["hypothesis"] == "unknown"


def test_build_diagnosis_report_standalone() -> None:
    result = _build_diagnosis_report(
        {
            "diagnosis_report": {
                "hypothesis": "h",
                "confidence": 0.8,
                "evidence_refs": ["x"],
            }
        }
    )
    assert result["hypothesis"] == "h"
    assert result["confidence"] == 0.8
    assert result["affected_invariants"] == []


def test_attestation_contains_task_id_and_ttl() -> None:
    handler = DiagnoseHandler()
    ctx = {
        "execution_contract": {"task_id": "task-123"},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.9,
        },
    }
    outcome = handler.pre_run(
        ctx, learning=None, skill=None, profile="default", footer_fn=lambda d, g: ""
    )
    attestation = outcome.artifacts["diagnosis_attestation"]
    assert attestation["task_id"] == "task-123"
    assert attestation["confidence"] == 0.9
    assert attestation["expires_at"] > attestation["issued_at"]


def test_pre_run_calibrates_confidence_from_similar_failures() -> None:
    handler = DiagnoseHandler()
    learning = MagicMock()
    learning.find_similar_failures.return_value = [
        {"symptom": "policy_mismatch", "root_cause": "missing_mandate"},
        {"symptom": "policy_mismatch", "root_cause": "missing_mandate"},
    ]
    ctx = {
        "diagnosis_report": {
            "hypothesis": "policy_mismatch",
            "root_cause": "missing_mandate",
            "confidence": 0.5,
            "evidence_refs": ["e"],
        }
    }

    outcome = handler.pre_run(
        ctx, learning=learning, skill=None, profile="default", footer_fn=lambda d, g: ""
    )

    report = outcome.artifacts["diagnosis_report"]
    assert report["confidence"] == 0.7
    assert report["historical_matches"] == 2


def test_post_run_registers_diagnose_execution() -> None:
    handler = DiagnoseHandler()
    learning = MagicMock()

    result = handler.post_run(
        {},
        learning=learning,
        exit_code=1,
        artifacts={
            "diagnosis_report": {
                "hypothesis": "policy_mismatch",
                "root_cause": "missing_mandate",
                "evidence_refs": ["e1"],
            }
        },
    )

    assert result == {}
    learning.append_failure.assert_called_once()
    entry = learning.append_failure.call_args.args[0]
    assert entry.symptom == "policy_mismatch"
    assert entry.root_cause == "missing_mandate"
    assert entry.tags == ["diagnose", "failed"]
