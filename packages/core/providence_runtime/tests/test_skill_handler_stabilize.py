from __future__ import annotations

from providence_runtime._skill_executor import (
    StabilizeHandler,
    _build_stabilization_report,
)


def test_build_stabilization_report_blocks_on_test_failure() -> None:
    report = _build_stabilization_report(
        {},
        command_results=[
            {"command": "providence lint run", "status": "ok"},
            {"command": "providence test ci-validate", "status": "error"},
        ],
    )

    assert report["decision"] == "block"
    assert report["test_failures"] == ["providence test ci-validate"]


def test_build_stabilization_report_warns_on_lint_only_failure() -> None:
    report = _build_stabilization_report(
        {"lint_summary": {"failures": ["unused import"]}},
        command_results=[],
    )

    assert report["decision"] == "warn"
    assert report["lint_failures"] == ["unused import"]


def test_stabilize_handler_returns_stabilization_report() -> None:
    handler = StabilizeHandler()
    result = handler.post_run(
        {},
        learning=None,
        exit_code=0,
        artifacts={
            "command_results": [{"command": "providence lint run", "status": "ok"}]
        },
    )

    assert result["stabilization_report"]["decision"] == "ready_to_ship"


def test_build_stabilization_report_parses_text_outputs() -> None:
    report = _build_stabilization_report(
        {
            "lint_output": "warning: unused import\nok",
            "test_output": "FAILED tests/unit/test_x.py::test_case - AssertionError",
        },
        command_results=[],
    )

    assert report["decision"] == "block"
    assert "warning: unused import" in report["lint_failures"]
    assert (
        "FAILED tests/unit/test_x.py::test_case - AssertionError"
        in report["test_failures"]
    )
