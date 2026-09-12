from __future__ import annotations

from pathlib import Path

from providence_runtime import TelemetrySink
from providence_runtime._skill_executor._executor_results import build_execution_result
from providence_runtime._skill_executor._executor_telemetry import emit_skill_telemetry


def test_emit_skill_telemetry_writes_runtime_event(tmp_path: Path) -> None:
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="active")
    emit_skill_telemetry(
        sink,
        build_execution_result(
            skill_name="sdd-diagnose",
            profile="default",
            policy_result="planned",
            reason="ok",
            exit_code=0,
            governance_footer="",
            fallback=[],
            command_results=[],
            artifacts={},
        ),
    )
    assert sink.list_events()[-1].event == "runtime.skill.run"


def test_emit_skill_telemetry_preserves_numeric_exit_code_and_persists_in_passive(
    tmp_path: Path,
) -> None:
    """TEL-12 regression: `runtime.skill.run` must persist even under
    `passive` logging mode (M007's unconditional "every skill run MUST
    emit"), and the raw numeric exit_code must survive in `details` rather
    than being collapsed to the ok/fail `status` string.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-12.
    """
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="passive")
    emit_skill_telemetry(
        sink,
        build_execution_result(
            skill_name="sdd-diagnose",
            profile="default",
            policy_result="blocked",
            reason="unauthorized",
            exit_code=2,
            governance_footer="",
            fallback=[],
            command_results=[],
            artifacts={},
        ),
    )
    event = sink.list_events()[-1]
    assert event.status == "fail"
    assert event.details["exit_code"] == 2
    assert event.details["skill"] == "sdd-diagnose"

    persisted = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "runtime.skill.run" in persisted
    assert '"exit_code": 2' in persisted


def test_emit_skill_telemetry_noops_without_sink() -> None:
    emit_skill_telemetry(
        None,
        build_execution_result(
            skill_name="sdd-diagnose",
            profile="default",
            policy_result="planned",
            reason="ok",
            exit_code=0,
            governance_footer="",
            fallback=[],
            command_results=[],
            artifacts={},
        ),
    )
