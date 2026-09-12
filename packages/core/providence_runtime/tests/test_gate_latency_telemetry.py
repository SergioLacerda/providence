"""Tests for guardrail.gate.latency emission (T-IMPL-1).

See `.analysis/refined/20260825-tp4-instrumentation-design/design.md`
§ Gate-Latency Event Shape for the design this implements.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_runtime._skill_executor._executor_run import _emit_gate_latency
from providence_runtime.skills import SkillEngine
from providence_runtime.telemetry import TelemetrySink


class _FakeSink:
    def __init__(self) -> None:
        self.events: list = []

    def emit(self, event) -> None:  # noqa: ANN001
        self.events.append(event)


def test_emit_gate_latency_noops_without_sink() -> None:
    _emit_gate_latency(
        sink=None,
        skill=None,
        gate_decision={"decision": "allow", "rule_id": "default_allow"},
        duration_ms=5,
    )


def test_emit_gate_latency_noops_without_gate_decision() -> None:
    sink = _FakeSink()
    _emit_gate_latency(sink=sink, skill=None, gate_decision=None, duration_ms=5)
    assert sink.events == []


def test_emit_gate_latency_emits_runtime_event() -> None:
    sink = _FakeSink()
    skill = type("Skill", (), {"name": "sdd-correct"})()
    _emit_gate_latency(
        sink=sink,
        skill=skill,
        gate_decision={"decision": "deny", "rule_id": "scope_violation"},
        duration_ms=42,
    )
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event == "guardrail.gate.latency"
    assert event.duration_ms == 42
    assert event.path_id == "sdd-correct"
    assert event.details == {"rule_id": "scope_violation", "outcome": "deny"}


# ---------------------------------------------------------------------------
# End-to-end: SkillEngine.run_skill("sdd-correct", ...) with a real sink
# ---------------------------------------------------------------------------


def _correct_context(task_id: str = "task-1") -> dict:
    return {
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


def test_correct_skill_emits_gate_latency_event(tmp_path: Path) -> None:
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="active")
    engine = SkillEngine(sink=sink, project_root=tmp_path)
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = engine.run_skill(
            "sdd-correct", context=_correct_context(), project_root=tmp_path
        )
    assert result.artifacts["gate_decision"]["decision"] == "allow"
    gate_events = [e for e in sink.list_events() if e.event == "guardrail.gate.latency"]
    assert len(gate_events) == 1
    assert gate_events[0].details["rule_id"] == "default_allow"
    assert gate_events[0].details["outcome"] == "allow"
    assert gate_events[0].duration_ms is not None
    assert gate_events[0].duration_ms >= 0


def test_non_gate_skill_does_not_emit_gate_latency_event(tmp_path: Path) -> None:
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="active")
    engine = SkillEngine(sink=sink, project_root=tmp_path)
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        engine.run_skill(
            "sdd-review-architecture", enforcement_mode="warn", project_root=tmp_path
        )
    gate_events = [e for e in sink.list_events() if e.event == "guardrail.gate.latency"]
    assert gate_events == []
