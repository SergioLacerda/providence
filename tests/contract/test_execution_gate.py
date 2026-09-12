"""Contract tests for execution_gate and governance_mode fields in providence ask output."""

from __future__ import annotations

import pytest

from providence_cli.services.ask_payload import build_ask_json_data

pytestmark = pytest.mark.unit


def _base_kwargs(**overrides):
    defaults = dict(
        profile="master",
        query_hash="abc123",
        context_source="compiled",
        fingerprint="deadbeef",
        mandates_loaded=10,
        trust_source="none",
        degraded=False,
        degraded_reason="",
        drift_detected=False,
        governance_footer="PROVIDENCE GOVERNANCE: drift=ok | governance=ok | profile=master",
        intake_index_mode="none",
        intake_chunks=0,
        intake_retrieval="indexed_only",
        intake_artifact="n/a",
    )
    defaults.update(overrides)
    return defaults


class TestExecutionGateBlocked:
    def test_execution_gate_blocked_when_unexpected_intake_failure(self):
        """execution_gate=blocked when indexing was expected but did not run."""
        payload = build_ask_json_data(
            **_base_kwargs(intake_index_mode="none", intake_chunks=0),
            governance_mode="hard",
            execution_gate="blocked",
            gate_reason="organize was expected but did not run; governance context not indexed",
        )
        assert payload["execution_gate"] == "blocked"

    def test_gate_reason_present_when_blocked(self):
        """gate_reason field is present when execution_gate=blocked."""
        payload = build_ask_json_data(
            **_base_kwargs(intake_index_mode="none"),
            governance_mode="hard",
            execution_gate="blocked",
            gate_reason="organize was expected but did not run; governance context not indexed",
        )
        assert "gate_reason" in payload
        assert payload["gate_reason"] is not None


class TestExecutionGateAllowed:
    def test_execution_gate_allowed_when_intake_chunks_present(self):
        """execution_gate=allowed when intake_chunks > 0."""
        payload = build_ask_json_data(
            **_base_kwargs(intake_index_mode="multi", intake_chunks=5),
            governance_mode="hard",
            execution_gate="allowed",
        )
        assert payload["execution_gate"] == "allowed"

    def test_execution_gate_allowed_when_intake_none_light_input(self):
        """execution_gate=allowed when intake_index_mode=none for a short/light query.

        intake_index_mode:none is a disclosure signal — it does not imply a blocked gate.
        Only execution_gate:blocked is the mandatory stop condition (canonical policy).
        """
        payload = build_ask_json_data(
            **_base_kwargs(intake_index_mode="none", intake_chunks=0),
            governance_mode="hard",
            execution_gate="allowed",
        )
        assert payload["execution_gate"] == "allowed"
        assert "gate_reason" not in payload

    def test_gate_reason_absent_when_allowed(self):
        """gate_reason field is absent when execution_gate=allowed."""
        payload = build_ask_json_data(
            **_base_kwargs(intake_index_mode="multi", intake_chunks=5),
            governance_mode="hard",
            execution_gate="allowed",
        )
        assert "gate_reason" not in payload


class TestGovernanceMode:
    def test_governance_mode_hard_present_in_output(self):
        """governance_mode=hard is always present in providence ask output."""
        payload = build_ask_json_data(
            **_base_kwargs(),
            governance_mode="hard",
            execution_gate="blocked",
            gate_reason="intake_index_mode=none: governance context not indexed; agent must not proceed",
        )
        assert "governance_mode" in payload
        assert payload["governance_mode"] == "hard"

    def test_execution_gate_field_always_present(self):
        """execution_gate field is always present regardless of value."""
        for gate in ("allowed", "blocked"):
            payload = build_ask_json_data(
                **_base_kwargs(),
                governance_mode="hard",
                execution_gate=gate,
            )
            assert "execution_gate" in payload
