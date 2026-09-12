from __future__ import annotations

from pathlib import Path

import pytest

from providence_integration.assertions.base import Assertion
from providence_integration.assertions.process import (
    ProcessExitAssertion,
    ProcessNotAllSkippedAssertion,
)
from providence_integration.builders.governance.pipeline_builder import PipelineBuilder
from providence_integration.engine.integration_engine import Report
from providence_integration.engine.step_executor import StepResult


class _DummyAssertion(Assertion):
    def execute(self, context: dict[str, object]) -> None:
        del context
        return None


def test_assertion_base_param_helpers_and_execute_error() -> None:
    a = _DummyAssertion(x="10", y=3, z=object(), bad_int="abc")
    assert a.param_str("x") == "10"
    assert a.param_str("missing", "d") == "d"
    assert a.param_int("x", 0) == 10
    assert a.param_int("bad_int", 11) == 11
    assert a.param_int("y", 0) == 3
    assert a.param_int("z", 7) == 7
    assert a.param_int("missing", 9) == 9
    with pytest.raises(NotImplementedError):
        Assertion().execute({})


def test_process_assertions_branches() -> None:
    ex = ProcessExitAssertion(equals=2)
    assert ex.execute({"last_exit_code": 2}).success is True
    assert ex.execute({"last_exit_code": 1}).success is False

    guard = ProcessNotAllSkippedAssertion()
    # no output -> summary unavailable branch
    r = guard.execute({})
    assert r.success is True
    assert "skip guard not applied" in r.message
    # mixed status should pass
    out = {"last_stdout": "2 passed, 1 skipped", "last_stderr": "1 errors"}
    assert guard.execute(out).success is True
    parsed = guard._parse_pytest_summary("3 errors, 1 xfailed, 2 xpassed")
    assert parsed is not None
    assert parsed["error"] == 3
    assert guard._parse_pytest_summary("") is None


def test_report_pretty_and_score() -> None:
    steps = [
        StepResult(name="a", success=True, messages=["ok"]),
        StepResult(name="b", success=False, messages=["fail"]),
    ]
    report = Report(steps)
    assert report.score() == 50
    text = report.pretty()
    assert "SDD Doctor Report" in text
    assert "Score: 50/100" in text


def test_pipeline_builder_legacy_guideline_branches(tmp_path: Path) -> None:
    # mandate.spec present -> no FileNotFoundError
    (tmp_path / "mandate.spec").write_text("M001: First", encoding="utf-8")
    # guidelines.dsl in compact format
    (tmp_path / "guidelines.dsl").write_text(
        "G01: title one\nG02: title two", encoding="utf-8"
    )
    b = PipelineBuilder(str(tmp_path))
    r = b.build()
    assert len(r["client_items"]) == 2

    # guidelines.dsl in bullet fallback format
    (tmp_path / "guidelines.dsl").write_text("- [G03] x\n- [G04] y", encoding="utf-8")
    b2 = PipelineBuilder(str(tmp_path))
    r2 = b2.build()
    assert {x["id"] for x in r2["client_items"]} == {"G03", "G04"}

    saved = b2.save_outputs(str(tmp_path / "out"))
    assert Path(saved["governance_core"]).exists()
    assert Path(saved["governance_client"]).exists()


def test_pipeline_builder_meta_path_resolution(tmp_path: Path) -> None:
    meta = tmp_path / "meta"
    meta.mkdir()
    (meta / "mandate.spec").write_text("M001: X", encoding="utf-8")
    b = PipelineBuilder(str(tmp_path))
    result = b.build()
    assert len(result["core_items"]) >= 1


def test_report_empty_score_zero() -> None:
    assert Report([]).score() == 0
