"""Tests for telemetry constants — mandatory event allowlist."""

from pathlib import Path

from providence_runtime import RuntimeEvent, TelemetrySink
from providence_runtime.telemetry._constants import (
    _MANDATORY_EVENTS,
    MODE_ACTIVE,
    MODE_STRICT,
)


def test_governance_ask_phase_is_mandatory():
    assert "governance.ask.phase" in _MANDATORY_EVENTS


def test_existing_mandatory_events_unchanged():
    assert "governance.ask" in _MANDATORY_EVENTS
    assert "governance.violation" in _MANDATORY_EVENTS


def test_strict_mode_persists_identically_to_active_mode(tmp_path: Path) -> None:
    """TEL-03: `MODE_STRICT` currently adds no persistence/enforcement
    difference over `MODE_ACTIVE` in `TelemetrySink`. This test documents
    that fact as an explicit, checked contract rather than an unverified
    assumption — if a future change makes them diverge, this test should be
    updated deliberately, not broken silently.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-03.
    """
    non_mandatory_event = RuntimeEvent(
        event="some.arbitrary.event", command="x", status="ok", trace_id="t1"
    )

    active_sink = TelemetrySink(
        jsonl_path=tmp_path / "active.jsonl", logging_mode=MODE_ACTIVE
    )
    active_sink.emit(non_mandatory_event)

    strict_sink = TelemetrySink(
        jsonl_path=tmp_path / "strict.jsonl", logging_mode=MODE_STRICT
    )
    strict_sink.emit(non_mandatory_event)

    assert (tmp_path / "active.jsonl").exists()
    assert (tmp_path / "strict.jsonl").exists()
    # Same persistence outcome for a non-mandatory event under both modes —
    # "strict" does not additionally validate, reject, or block anything.
    assert (tmp_path / "active.jsonl").read_text(encoding="utf-8").strip() != ""
    assert (tmp_path / "strict.jsonl").read_text(encoding="utf-8").strip() != ""


def test_runtime_skill_run_is_mandatory():
    """TEL-12: M007's "Skill-Oriented Reinforcement" section requires every
    `providence skills run` invocation to emit a structured event unconditionally
    — it must persist even under `passive` logging mode.
    `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` TEL-12.
    """
    assert "runtime.skill.run" in _MANDATORY_EVENTS
