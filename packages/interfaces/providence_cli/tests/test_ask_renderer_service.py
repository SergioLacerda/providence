"""Unit tests for ask_renderer service module."""

from __future__ import annotations

import pytest

from providence_cli.services.ask_renderer import (
    build_ask_json_payload,
    render_ask_text_output,
    render_context_header,
    render_governance_activation_header,
    render_governance_footer,
)

pytestmark = pytest.mark.unit


class TestRenderContextHeader:
    def test_healthy_is_single_line(self) -> None:
        output = render_context_header(
            "abc12345",
            12,
            degraded=False,
            degrade_reason="",
        )
        assert "\n" not in output

    def test_healthy_contains_active_and_fingerprint(self) -> None:
        output = render_context_header(
            "abc12345",
            12,
            degraded=False,
            degrade_reason="",
        )
        assert "governance=active" in output
        assert "abc12345" in output
        assert "12" in output

    def test_degraded_contains_warning(self) -> None:
        output = render_context_header(
            "",
            0,
            degraded=True,
            degrade_reason="artifact_unverified",
        )
        assert "DEGRADED" in output
        assert "artifact_unverified" in output

    def test_degraded_adds_second_line(self) -> None:
        output = render_context_header(
            "fp123456",
            5,
            degraded=True,
            degrade_reason="artifact_unverified",
        )
        assert len(output.splitlines()) == 2


class TestRenderGovernanceActivationHeader:
    def test_header_is_compact_and_contains_status_fields(self) -> None:
        output = render_governance_activation_header(
            source="prompt-submit-hook",
            fingerprint="58a087b3c9fb9ce2",
            execution_gate="allowed",
        )

        assert output.startswith("PROVIDENCE GOVERNANCE ACTIVE")
        assert "source=prompt-submit-hook" in output
        assert "governance_mode=hard" in output
        assert "execution_gate=allowed" in output
        assert "fingerprint=58a087b3" in output

    def test_header_instructs_visible_response_status(self) -> None:
        output = render_governance_activation_header(source="sdd-ask")

        assert "start your response" in output
        assert "SDD governance status" in output


class TestRenderGovernanceFooter:
    def test_healthy_state_shows_ok(self) -> None:
        footer = render_governance_footer(
            state="HEALTHY", profile="master", drift_detected=False
        )
        assert "ok" in footer or "governance=ok" in footer

    def test_partial_state_shows_ok(self) -> None:
        footer = render_governance_footer(
            state="PARTIAL", profile="master", drift_detected=False
        )
        assert "ok" in footer or "governance=ok" in footer

    def test_warn_state_for_misconfigured(self) -> None:
        footer = render_governance_footer(
            state="MISCONFIGURED", profile="master", drift_detected=False
        )
        assert "warn" in footer or "governance=warn" in footer

    def test_drift_detected_shows_detected(self) -> None:
        footer = render_governance_footer(
            state="HEALTHY", profile="master", drift_detected=True
        )
        assert "detected" in footer

    def test_no_drift_shows_none(self) -> None:
        footer = render_governance_footer(
            state="HEALTHY", profile="master", drift_detected=False
        )
        assert "none" in footer or "drift=none" in footer

    def test_profile_in_footer(self) -> None:
        footer = render_governance_footer(
            state="HEALTHY", profile="client", drift_detected=False
        )
        assert "client" in footer


class TestRenderAskTextOutput:
    def _make_output(self, **kwargs: object) -> str:
        defaults = {
            "output_text": "context header text",
            "organize_used": False,
            "organize_reason": "light_input",
            "organize_chunks": 0,
            "organize_artifact_path": "",
            "query_len": 10,
            "governance_footer": "PROVIDENCE GOVERNANCE: drift=none",
        }
        defaults.update(kwargs)
        return render_ask_text_output(**defaults)  # type: ignore[arg-type]

    def test_contains_context_text(self) -> None:
        output = self._make_output(output_text="my context text")
        assert "my context text" in output

    def test_light_input_shows_allowed(self) -> None:
        # light_input is too small to need indexing  gate should pass through
        output = self._make_output(organize_used=False)
        assert "allowed" in output

    def test_heavy_input_not_organized_shows_blocked(self) -> None:
        output = self._make_output(
            organize_used=False, organize_reason="char_count>=6000"
        )
        assert "blocked" in output

    def test_no_organize_max_two_intake_lines(self) -> None:
        output = self._make_output(organize_used=False, query_len=100)
        intake_lines = [
            line
            for line in output.splitlines()
            if "intake" in line or "gate" in line or "governance_mode" in line
        ]
        assert len(intake_lines) <= 2

    def test_organize_used_shows_allowed(self) -> None:
        output = self._make_output(organize_used=True, organize_chunks=3)
        assert "allowed" in output
        assert "3" in output

    def test_organize_used_max_two_intake_lines(self) -> None:
        output = self._make_output(
            organize_used=True,
            organize_chunks=3,
            organize_artifact_path=".analysis/pending/foo.md",
        )
        intake_lines = [
            line
            for line in output.splitlines()
            if "intake" in line or "artifact" in line
        ]
        assert len(intake_lines) <= 2

    def test_footer_included(self) -> None:
        output = self._make_output(
            governance_footer="PROVIDENCE GOVERNANCE: test-footer"
        )
        assert "test-footer" in output


class TestBuildAskJsonPayload:
    def _make_payload(self, **kwargs: object) -> dict:  # type: ignore[type-arg]
        defaults = {
            "profile": "master",
            "query": "test query",
            "context_source": "compiled",
            "fingerprint": "abc12345",
            "mandates_count": 10,
            "trust_source": "canonical",
            "degraded": False,
            "degrade_reason": "",
            "drift_detected": False,
            "governance_footer": "PROVIDENCE GOVERNANCE: ok",
            "organize_used": False,
            "organize_chunks": 0,
            "organize_retrieval": "indexed_only",
            "organize_artifact_path": "",
            "ahp_state": "HEALTHY",
            "learning_signals": {
                "diagnosis_inconclusive": 0,
                "evidence_insufficient": 0,
                "scope_violation": 0,
                "drift_recent_failures": 0,
                "observed_events": 0,
                "window_days": 7,
            },
            "full": False,
            "start_ts": "2026-01-01T00:00:00Z",
        }
        defaults.update(kwargs)
        return build_ask_json_payload(**defaults)  # type: ignore[arg-type]

    def test_status_is_ok(self) -> None:
        payload = self._make_payload()
        assert payload["status"] == "ok"
        assert payload["ok"] is True
        assert payload["error"] is None

    def test_command_is_ask(self) -> None:
        assert self._make_payload()["command"] == "ask"

    def test_data_has_profile(self) -> None:
        payload = self._make_payload(profile="client")
        assert payload["data"]["profile"] == "client"

    def test_full_false_has_no_steps(self) -> None:
        payload = self._make_payload(full=False)
        assert payload["data"].get("steps") is None

    def test_full_true_has_steps(self) -> None:
        payload = self._make_payload(full=True)
        assert payload["data"].get("steps") is not None

    def test_dossier_lines_included(self) -> None:
        payload = self._make_payload(dossier_lines=["line one", "line two"])
        assert payload["data"]["dossier"]["lines"] == ["line one", "line two"]

    def test_no_dossier_lines_by_default(self) -> None:
        payload = self._make_payload()
        assert "dossier" not in payload["data"]
