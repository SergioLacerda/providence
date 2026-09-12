"""Integration-oriented tests for providence_integration.engine runtime flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import yaml

from providence_integration.assertions.base import Assertion
from providence_integration.assertions.result import AssertionResult
from providence_integration.engine.integration_engine import IntegrationEngine
from providence_integration.engine.step_executor import StepExecutor
from providence_integration.engine.types import RuntimeContext


class OkAssertion(Assertion):
    def execute(self, context: RuntimeContext) -> AssertionResult:
        if context.get("probe") == "ok":
            return AssertionResult(True, "probe ok")
        return AssertionResult(False, "probe missing")


class FailAssertion(Assertion):
    def execute(self, context: RuntimeContext) -> AssertionResult:
        del context
        return AssertionResult(False, "forced failure")


class ExplodeAssertion(Assertion):
    def execute(self, context: RuntimeContext) -> AssertionResult:
        del context
        raise RuntimeError("assertion boom")


def _write_spec(tmp_path: Path, spec: dict[str, Any]) -> Path:
    spec_path = tmp_path / "integration.yaml"
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return spec_path


def test_engine_run_success_path(tmp_path: Path) -> None:
    def runner(inputs: dict[str, Any], context: RuntimeContext, spec_dir: Path) -> None:
        del inputs, spec_dir
        context["probe"] = "ok"

    spec = {
        "steps": [
            {
                "id": "step_ok",
                "type": "custom.runner",
                "inputs": {},
                "asserts": [{"type": "custom.ok"}],
            }
        ]
    }
    spec_path = _write_spec(tmp_path, spec)
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(
        runner_registry={"custom.runner": runner},
        assertion_registry={"custom.ok": OkAssertion},
    )

    report = engine.run()

    assert report.score() == 100
    assert len(report.steps) == 1
    step = report.steps[0]
    assert step.success is True
    assert step.runner_status == "ok"
    assert step.assertion_statuses == {"custom.ok": "ok"}
    assert step.error_code is None


def test_engine_run_runner_not_found(tmp_path: Path) -> None:
    spec = {"steps": [{"id": "missing_runner", "type": "x.y", "asserts": []}]}
    spec_path = _write_spec(tmp_path, spec)
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(runner_registry={}, assertion_registry={})

    report = engine.run()

    assert report.score() == 0
    step = report.steps[0]
    assert step.success is False
    assert step.runner_status == "not_found"
    assert step.error_code == "runner_not_found"
    assert "runner not found" in step.details


def test_engine_run_assertion_failure(tmp_path: Path) -> None:
    def runner(inputs: dict[str, Any], context: RuntimeContext, spec_dir: Path) -> None:
        del inputs, spec_dir
        context["probe"] = "ok"

    spec = {
        "steps": [
            {
                "id": "assertion_fail",
                "type": "custom.runner",
                "asserts": [{"type": "custom.fail"}],
            }
        ]
    }
    spec_path = _write_spec(tmp_path, spec)
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(
        runner_registry={"custom.runner": runner},
        assertion_registry={"custom.fail": FailAssertion},
    )

    report = engine.run()

    assert report.score() == 0
    step = report.steps[0]
    assert step.success is False
    assert step.assertion_statuses == {"custom.fail": "failed"}
    assert step.error_code == "assertion_failed"
    assert "forced failure" in step.details


def test_engine_cleanup_runs_on_runner_exception(tmp_path: Path) -> None:
    cleaned = {"called": False}

    def runner(inputs: dict[str, Any], context: RuntimeContext, spec_dir: Path) -> None:
        del inputs, context, spec_dir
        raise RuntimeError("runner boom")

    spec = {
        "context": {"isolation": True},
        "steps": [{"id": "runner_error", "type": "custom.runner", "asserts": []}],
    }
    spec_path = _write_spec(tmp_path, spec)
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(
        runner_registry={"custom.runner": runner},
        assertion_registry={},
    )

    from providence_integration.engine.context import ExecutionContext

    original_cleanup = ExecutionContext.cleanup

    def tracked_cleanup(self: ExecutionContext) -> None:
        cleaned["called"] = True
        original_cleanup(self)

    with patch.object(ExecutionContext, "cleanup", tracked_cleanup):
        report = engine.run()
        step = report.steps[0]
        assert step.success is False
        assert step.runner_status == "error"
        assert step.error_code == "runner_error"
        assert cleaned["called"] is True


def test_engine_run_assertion_not_found_sets_structured_error(tmp_path: Path) -> None:
    def runner(inputs: dict[str, Any], context: RuntimeContext, spec_dir: Path) -> None:
        del inputs, spec_dir
        context["probe"] = "ok"

    spec = {
        "steps": [
            {
                "id": "assertion_missing",
                "type": "custom.runner",
                "asserts": [{"type": "custom.unknown"}],
            }
        ]
    }
    spec_path = _write_spec(tmp_path, spec)
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(
        runner_registry={"custom.runner": runner},
        assertion_registry={},
    )

    report = engine.run()
    step = report.steps[0]

    assert step.success is False
    assert step.runner_status == "ok"
    assert step.assertion_statuses == {"custom.unknown": "not_found"}
    assert step.error_code == "assertion_not_found"


def test_engine_run_assertion_error_sets_structured_error(tmp_path: Path) -> None:
    def runner(inputs: dict[str, Any], context: RuntimeContext, spec_dir: Path) -> None:
        del inputs, spec_dir
        context["probe"] = "ok"

    spec = {
        "steps": [
            {
                "id": "assertion_error",
                "type": "custom.runner",
                "asserts": [{"type": "custom.explode"}],
            }
        ]
    }
    spec_path = _write_spec(tmp_path, spec)
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(
        runner_registry={"custom.runner": runner},
        assertion_registry={"custom.explode": ExplodeAssertion},
    )

    report = engine.run()
    step = report.steps[0]

    assert step.success is False
    assert step.assertion_statuses == {"custom.explode": "error"}
    assert step.error_code == "assertion_error"
    assert "assertion error (custom.explode): assertion boom" in step.details


def test_engine_run_invalid_inputs_block_runner_execution(tmp_path: Path) -> None:
    called = {"runner": False}

    def runner(inputs: dict[str, Any], context: RuntimeContext, spec_dir: Path) -> None:
        del inputs, context, spec_dir
        called["runner"] = True

    spec = {
        "steps": [
            {
                "id": "invalid_command_inputs",
                "type": "command.exec",
                "inputs": {"command": 123},
                "asserts": [],
            }
        ]
    }
    spec_path = _write_spec(tmp_path, cast(dict[str, Any], spec))
    engine = IntegrationEngine(str(spec_path))
    engine.executor = StepExecutor(
        runner_registry={"command.exec": runner},
        assertion_registry={},
    )

    report = engine.run()
    step = report.steps[0]

    assert step.success is False
    assert step.runner_status == "invalid_inputs"
    assert step.error_code == "invalid_inputs"
    assert called["runner"] is False
    assert "invalid inputs for command.exec" in step.details
