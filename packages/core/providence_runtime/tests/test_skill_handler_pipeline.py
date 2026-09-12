from __future__ import annotations

from providence_runtime._skill_executor import ContextCarrier, PipelineHandler


def test_context_carrier_prefers_latest_layer() -> None:
    carrier = ContextCarrier({"workspace": "/tmp/project", "shared": "first"})
    carrier.push_layer(
        {"execution_contract": {"task_id": "task-1"}, "shared": "second"},
        source="skill",
        skill_name="sdd-ask",
    )

    assert carrier.get("workspace") == "/tmp/project"
    assert carrier.get("shared") == "second"
    value, source = carrier.get_with_source("execution_contract")
    assert value == {"task_id": "task-1"}
    assert source == "sdd-ask"


def test_pipeline_handler_pre_run_returns_compose_config() -> None:
    handler = PipelineHandler()
    outcome = handler.pre_run(
        {},
        learning=None,
        skill=type("Skill", (), {"name": "sdd-pipeline"})(),
        profile="default",
        footer_fn=lambda d, g: "",
    )

    assert outcome.early_result is None
    assert outcome.compose_config == {
        "stages": [
            "sdd-ask",
            "sdd-diagnose",
            "sdd-correct",
            "sdd-converge",
        ],
        "decision_gates": {"diagnose_to_correct_min_confidence": 0.7},
    }
    assert outcome.artifacts["pipeline_state"]["completed_stages"] == []


def test_context_carrier_audit_trail_preserves_history() -> None:
    carrier = ContextCarrier({"shared": "first"})
    carrier.push_layer({"shared": "second"}, source="skill", skill_name="sdd-ask")
    carrier.push_layer({"shared": "third"}, source="skill", skill_name="sdd-diagnose")

    assert carrier.audit_trail("shared") == [
        ("first", "initial"),
        ("second", "sdd-ask"),
        ("third", "sdd-diagnose"),
    ]


def test_pipeline_handler_pre_run_exposes_default_decision_gate() -> None:
    handler = PipelineHandler()
    outcome = handler.pre_run(
        {},
        learning=None,
        skill=type(
            "Skill",
            (),
            {
                "name": "sdd-pipeline",
                "config": {
                    "pipeline": {
                        "decision_gates": {"diagnose_to_correct_min_confidence": 0.7}
                    }
                },
            },
        )(),
        profile="default",
        footer_fn=lambda d, g: "",
    )

    assert outcome.compose_config is not None
    assert outcome.compose_config["decision_gates"] == {
        "diagnose_to_correct_min_confidence": 0.7
    }


def test_pipeline_handler_prefers_skill_config_and_allows_context_override() -> None:
    handler = PipelineHandler()
    skill = type(
        "Skill",
        (),
        {
            "name": "sdd-pipeline",
            "config": {
                "pipeline": {
                    "stages": ["sdd-ask", "sdd-diagnose"],
                    "decision_gates": {"diagnose_to_correct_min_confidence": 0.65},
                }
            },
        },
    )()

    outcome = handler.pre_run(
        {"pipeline_min_diagnosis_confidence": 0.55},
        learning=None,
        skill=skill,
        profile="default",
        footer_fn=lambda d, g: "",
    )

    assert outcome.compose_config == {
        "stages": ["sdd-ask", "sdd-diagnose"],
        "decision_gates": {"diagnose_to_correct_min_confidence": 0.55},
    }
