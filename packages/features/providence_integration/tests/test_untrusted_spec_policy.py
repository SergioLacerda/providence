"""Tests for the trusted-spec provenance policy on privileged step types."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from providence_integration.engine.integration_engine import IntegrationEngine
from providence_integration.engine.step_executor import StepExecutor


def _write_spec(tmp_path: Path, spec: dict[str, Any]) -> Path:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return spec_path


def test_command_exec_blocked_when_spec_not_trusted(tmp_path: Path) -> None:
    called = {"runner": False}

    def runner(inputs: Any, context: Any, spec_dir: Path) -> None:
        del inputs, context, spec_dir
        called["runner"] = True

    spec = {
        "steps": [
            {
                "id": "run_cmd",
                "type": "command.exec",
                "inputs": {"command": "echo hi"},
                "asserts": [],
            }
        ]
    }
    engine = IntegrationEngine(str(_write_spec(tmp_path, spec)))
    engine.executor = StepExecutor(
        runner_registry={"command.exec": runner}, assertion_registry={}
    )

    report = engine.run()

    assert called["runner"] is False
    step = report.steps[0]
    assert step.success is False
    assert step.error_code == "untrusted_spec"
    assert step.runner_status == "untrusted_spec"


def test_git_commit_blocked_when_spec_not_trusted(tmp_path: Path) -> None:
    called = {"runner": False}

    def runner(inputs: Any, context: Any, spec_dir: Path) -> None:
        del inputs, context, spec_dir
        called["runner"] = True

    spec = {
        "steps": [
            {
                "id": "commit",
                "type": "git.commit",
                "inputs": {"message": "x"},
                "asserts": [],
            }
        ]
    }
    engine = IntegrationEngine(str(_write_spec(tmp_path, spec)))
    engine.executor = StepExecutor(
        runner_registry={"git.commit": runner}, assertion_registry={}
    )

    report = engine.run()

    assert called["runner"] is False
    assert report.steps[0].error_code == "untrusted_spec"


def test_command_exec_runs_when_spec_trusted(tmp_path: Path) -> None:
    called = {"runner": False}

    def runner(inputs: Any, context: Any, spec_dir: Path) -> None:
        del inputs, context, spec_dir
        called["runner"] = True

    spec = {
        "trusted": True,
        "steps": [
            {
                "id": "run_cmd",
                "type": "command.exec",
                "inputs": {"command": "echo hi"},
                "asserts": [],
            }
        ],
    }
    engine = IntegrationEngine(str(_write_spec(tmp_path, spec)))
    engine.executor = StepExecutor(
        runner_registry={"command.exec": runner}, assertion_registry={}
    )

    report = engine.run()

    assert called["runner"] is True
    assert report.steps[0].success is True


def test_non_privileged_steps_run_regardless_of_trust(tmp_path: Path) -> None:
    called = {"runner": False}

    def runner(inputs: Any, context: Any, spec_dir: Path) -> None:
        del inputs, context, spec_dir
        called["runner"] = True

    spec = {
        "steps": [
            {
                "id": "mk_dirs",
                "type": "filesystem.create_structure",
                "inputs": {"directories": ["a"]},
                "asserts": [],
            }
        ]
    }
    engine = IntegrationEngine(str(_write_spec(tmp_path, spec)))
    engine.executor = StepExecutor(
        runner_registry={"filesystem.create_structure": runner}, assertion_registry={}
    )

    report = engine.run()

    assert called["runner"] is True
    assert report.steps[0].success is True
