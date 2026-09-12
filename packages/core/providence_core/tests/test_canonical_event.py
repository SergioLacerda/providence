"""Unit tests for providence_core.output.canonical_event (M020 — Simple Governed IO)."""

from __future__ import annotations

import json

import pytest

from providence_core.output.canonical_event import (
    CanonicalGovernanceInput,
    CanonicalLogEvent,
    ProfileRenderer,
)

pytestmark = pytest.mark.unit


class TestCanonicalGovernanceInput:
    def test_healthy_is_single_line(self) -> None:
        gov = CanonicalGovernanceInput(
            governance_state="active", fingerprint="abc12345", mandates_count=12
        )
        result = gov.simple_input()
        assert "\n" not in result

    def test_healthy_contains_required_fields(self) -> None:
        gov = CanonicalGovernanceInput(
            governance_state="active", fingerprint="abc12345", mandates_count=12
        )
        result = gov.simple_input()
        assert "governance=active" in result
        assert "abc12345" in result
        assert "mandates=12" in result

    def test_fingerprint_truncated_to_8_chars(self) -> None:
        gov = CanonicalGovernanceInput(
            governance_state="active",
            fingerprint="abc123456789",
            mandates_count=1,
        )
        result = gov.simple_input()
        assert "abc12345" in result
        assert "6789" not in result

    def test_degraded_adds_second_line(self) -> None:
        gov = CanonicalGovernanceInput(
            governance_state="degraded",
            fingerprint="xyz",
            mandates_count=0,
            degraded=True,
            degrade_reason="artifact_unverified",
        )
        result = gov.simple_input()
        lines = result.splitlines()
        assert len(lines) == 2

    def test_degraded_line_contains_reason(self) -> None:
        gov = CanonicalGovernanceInput(
            governance_state="degraded",
            fingerprint="xyz",
            mandates_count=0,
            degraded=True,
            degrade_reason="artifact_unverified",
        )
        result = gov.simple_input()
        assert "DEGRADED" in result
        assert "artifact_unverified" in result

    def test_degraded_without_reason_uses_fallback(self) -> None:
        gov = CanonicalGovernanceInput(
            governance_state="degraded",
            fingerprint="xyz",
            mandates_count=0,
            degraded=True,
            degrade_reason="",
        )
        result = gov.simple_input()
        assert "DEGRADED" in result


class TestCanonicalLogEvent:
    def test_status_event_single_line(self) -> None:
        event = CanonicalLogEvent(
            level="info", phase="ranger", event_type="phase_start", summary="running"
        )
        result = event.simple_output()
        lines = result.splitlines()
        assert len(lines) == 1
        assert "phase_start" in lines[0]

    def test_decision_and_artifact_on_second_line(self) -> None:
        event = CanonicalLogEvent(
            level="info",
            phase="ranger",
            event_type="phase_done",
            summary="done",
            decision="proceed",
            artifact_path=".analysis/pending/foo.md",
        )
        result = event.simple_output()
        lines = result.splitlines()
        assert len(lines) == 2
        assert "decision=proceed" in lines[1]
        assert "artifact=.analysis/pending/foo.md" in lines[1]

    def test_next_action_on_third_line(self) -> None:
        event = CanonicalLogEvent(
            level="info",
            phase="diagnose",
            event_type="finding",
            summary="detector unreliable",
            decision="block refactor",
            artifact_path=".providence/runtime/diagnosis/foo.md",
            next_action="fix detector",
        )
        result = event.simple_output()
        lines = result.splitlines()
        assert len(lines) == 3
        assert "next=fix detector" in lines[2]

    def test_max_three_lines_enforced(self) -> None:
        event = CanonicalLogEvent(
            level="info",
            phase="p",
            event_type="e",
            summary="s",
            decision="d",
            artifact_path="a",
            next_action="n",
            evidence_ref="e",
            component="c",
        )
        result = event.simple_output()
        assert len(result.splitlines()) <= 3

    def test_line_max_120_chars(self) -> None:
        long_summary = "x" * 200
        event = CanonicalLogEvent(
            level="info", phase="phase", event_type="event", summary=long_summary
        )
        for line in event.simple_output().splitlines():
            assert len(line) <= 120

    def test_to_telemetry_dict_contains_all_set_fields(self) -> None:
        event = CanonicalLogEvent(
            level="debug",
            phase="ranger",
            event_type="phase_done",
            summary="done",
            artifact_path=".analysis/pending/foo.md",
        )
        result = event.to_telemetry_dict()
        assert result["level"] == "debug"
        assert result["artifact_path"] == ".analysis/pending/foo.md"

    def test_to_telemetry_dict_omits_empty_fields(self) -> None:
        event = CanonicalLogEvent(
            level="debug", phase="ranger", event_type="phase_done"
        )
        result = event.to_telemetry_dict()
        assert "decision" not in result
        assert "next_action" not in result


class TestProfileRenderer:
    def test_pragmatic_returns_simple_output(self) -> None:
        renderer = ProfileRenderer(profile="pragmatic")
        event = CanonicalLogEvent(
            level="info", phase="ranger", event_type="phase_done", summary="done"
        )
        result = renderer.render(event)
        assert result == event.simple_output()

    def test_epic_returns_simple_output(self) -> None:
        renderer = ProfileRenderer(profile="epic")
        event = CanonicalLogEvent(
            level="info", phase="ranger", event_type="phase_done", summary="done"
        )
        result = renderer.render(event)
        assert result == event.simple_output()

    def test_debug_bypasses_profile_returns_json(self) -> None:
        renderer = ProfileRenderer(profile="pragmatic")
        event = CanonicalLogEvent(
            level="debug", phase="ranger", event_type="detail", summary="internal"
        )
        result = renderer.render(event)
        parsed = json.loads(result)
        assert parsed["level"] == "debug"

    def test_trace_bypasses_profile_returns_json(self) -> None:
        renderer = ProfileRenderer(profile="epic")
        event = CanonicalLogEvent(
            level="trace", phase="ranger", event_type="trace_event", summary="trace"
        )
        result = renderer.render(event)
        parsed = json.loads(result)
        assert parsed["level"] == "trace"

    def test_render_input_returns_simple_input(self) -> None:
        renderer = ProfileRenderer(profile="pragmatic")
        gov = CanonicalGovernanceInput(
            governance_state="active", fingerprint="abc12345", mandates_count=10
        )
        result = renderer.render_input(gov)
        assert result == gov.simple_input()

    def test_render_does_not_alter_decision_field(self) -> None:
        renderer = ProfileRenderer(profile="epic")
        event = CanonicalLogEvent(
            level="info",
            phase="sniper",
            event_type="execution_done",
            decision="approved",
            artifact_path=".analysis/done/foo.md",
        )
        result = renderer.render(event)
        assert "approved" in result
        assert ".analysis/done/foo.md" in result
