from pathlib import Path
from typing import Any

import pytest

from providence_integration.assertions.config import ConfigIsValidPathAssertion
from providence_integration.assertions.process import ProcessNotAllSkippedAssertion
from providence_integration.engine.integration_engine import IntegrationEngine

pytestmark = pytest.mark.unit


def test_config_is_valid_path_passes_for_existing_relative_path(tmp_path: Path) -> None:
    assertion = ConfigIsValidPathAssertion(key="spec_path")
    expected = tmp_path / "tests" / "unit" / "specs_ia_units"
    expected.mkdir(parents=True)

    result = assertion.execute(
        {
            "working_dir": tmp_path,
            "config": {"spec_path": "tests/unit/specs_ia_units"},
        }
    )

    assert result.success is True
    assert "valid path" in result.message


def test_config_is_valid_path_fails_for_missing_path(tmp_path: Path) -> None:
    assertion = ConfigIsValidPathAssertion(key="spec_path")

    result = assertion.execute(
        {
            "working_dir": tmp_path,
            "config": {"spec_path": "missing/location"},
        }
    )

    assert result.success is False
    assert "path not found" in result.message


def test_process_not_all_skipped_fails_when_everything_skipped() -> None:
    assertion = ProcessNotAllSkippedAssertion()

    result = assertion.execute(
        {
            "last_stdout": "================== 7 skipped in 0.05s ==================",
            "last_stderr": "",
        }
    )

    assert result.success is False
    assert "all tests skipped" in result.message


def test_process_not_all_skipped_passes_when_any_test_executes() -> None:
    assertion = ProcessNotAllSkippedAssertion()

    result = assertion.execute(
        {
            "last_stdout": "================== 1 passed, 7 skipped in 0.05s ==================",
            "last_stderr": "",
        }
    )

    assert result.success is True


def test_integration_engine_applies_context_overrides(
    tmp_path: Path, monkeypatch: Any
) -> None:
    spec_file = tmp_path / "flow.yaml"
    spec_file.write_text(
        "\n".join(
            [
                "version: 1",
                "context:",
                "  working_dir: temp",
                "  isolation: true",
                "steps: []",
            ]
        ),
        encoding="utf-8",
    )

    captured_context: dict[str, Any] = {}

    class DummyContext:
        def as_dict(self) -> dict[str, Any]:
            return {}

        def cleanup(self) -> None:
            return None

    def fake_from_spec(spec: dict[str, Any], spec_dir: Path) -> DummyContext:
        del spec_dir
        captured_context.update(spec.get("context", {}))
        return DummyContext()

    monkeypatch.setattr(
        "providence_integration.engine.integration_engine.ExecutionContext.from_spec",
        fake_from_spec,
    )

    engine = IntegrationEngine(
        str(spec_file),
        context_overrides={"working_dir": str(tmp_path), "isolation": False},
    )
    engine.run()

    assert captured_context["working_dir"] == str(tmp_path)
    assert captured_context["isolation"] is False
