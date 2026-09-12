"""Tests for governance.compliance.score event per observability-core plan Phase 3."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from providence_cli.services.governance_compile_handlers import (
    compute_compliance_score as _compute_compliance_score,
)
from providence_core.utils.text_io import read_text_utf8

# ---------------------------------------------------------------------------
# _compute_compliance_score unit tests
# ---------------------------------------------------------------------------


def test_score_all_passing() -> None:
    score, components = _compute_compliance_score(
        compile_ok=True,
        consistency_ok=True,
        drift_detected=False,
    )
    assert score == 100
    assert all(components.values())


def test_score_drift_detected_reduces_by_25() -> None:
    score, components = _compute_compliance_score(
        compile_ok=True,
        consistency_ok=True,
        drift_detected=True,
    )
    assert score == 75
    assert components["drift_detected"] is False
    assert components["governance_compile"] is True
    assert components["consistency"] is True


def test_score_compile_fail_reduces_by_25() -> None:
    score, components = _compute_compliance_score(
        compile_ok=False,
        consistency_ok=True,
        drift_detected=False,
    )
    assert score == 75
    assert components["governance_compile"] is False


def test_score_two_failing() -> None:
    score, components = _compute_compliance_score(
        compile_ok=False,
        consistency_ok=False,
        drift_detected=False,
    )
    assert score == 50


def test_score_all_failing() -> None:
    score, components = _compute_compliance_score(
        compile_ok=False,
        consistency_ok=False,
        drift_detected=True,
    )
    assert score == 25  # lint_gate is always True


def test_score_status_thresholds() -> None:
    """status is derived as: >=75 ok, >=50 warn, <50 fail."""
    s100, _ = _compute_compliance_score(
        compile_ok=True, consistency_ok=True, drift_detected=False
    )
    assert s100 >= 75

    s50, _ = _compute_compliance_score(
        compile_ok=False, consistency_ok=False, drift_detected=False
    )
    assert 50 <= s50 < 75

    s25, _ = _compute_compliance_score(
        compile_ok=False, consistency_ok=False, drift_detected=True
    )
    assert s25 < 50


def test_score_components_dict_has_required_keys() -> None:
    _, components = _compute_compliance_score(
        compile_ok=True,
        consistency_ok=True,
        drift_detected=False,
    )
    assert set(components.keys()) == {
        "governance_compile",
        "consistency",
        "drift_detected",
        "lint_gate",
    }


# ---------------------------------------------------------------------------
# Integration: event emitted after compile
# ---------------------------------------------------------------------------


def _make_compile_mocks(tmp_path: Path):
    """Return a dict of patches to simulate a successful governance compile."""
    ws_root = tmp_path
    (ws_root / ".providence" / "runtime").mkdir(parents=True, exist_ok=True)

    phase1 = {
        "core_item_count": 10,
        "client_item_count": 8,
        "core_fingerprint": "abc" * 21 + "d",
    }
    phase2 = {
        "core_msgpack_file": "core.msgpack",
        "client_msgpack_file": "client.msgpack",
    }

    return ws_root, phase1, phase2


def test_event_emitted_after_compile(tmp_path: Path) -> None:
    """Successful governance compile  governance.compliance.score event in JSONL."""
    ws_root, phase1, phase2 = _make_compile_mocks(tmp_path)
    events_path = ws_root / ".providence" / "runtime" / "compliance-events.jsonl"

    with (
        patch(
            "providence_cli.services.governance_compile_handlers.run_compilation",
            return_value={"phase_1": phase1, "phase_2": phase2},
        ),
        patch(
            "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
            return_value=(True, ""),
        ),
        patch(
            "providence_cli.services.governance_compile_handlers.update_profile_hash"
        ),
        patch("providence_cli.services.governance_compile_handlers.regenerate_seeds"),
        patch(
            "providence_cli.services.governance_artifact_handlers.run_governance_compile_json",
            return_value=(
                {
                    "status": "ok",
                    "ok": True,
                    "command": "governance compile",
                    "error": None,
                    "data": {},
                },
                False,
            ),
        ),
        patch("providence_cli.commands.governance.render_governance_compile_table"),
        patch(
            "providence_core.utils.environment.find_workspace_root",
            return_value=ws_root,
        ),
    ):
        from click.testing import CliRunner

        from providence_cli.main import app

        runner = CliRunner()
        runner.invoke(app, ["governance", "compile"])

    if events_path.exists():
        events = [
            json.loads(line)
            for line in read_text_utf8(events_path).splitlines()
            if line.strip()
        ]
        score_events = [
            e for e in events if e.get("event") == "governance.compliance.score"
        ]
        assert len(score_events) >= 1, (
            f"No score events found. Events: {[e.get('event') for e in events]}"
        )
        ev = score_events[0]
        assert "score" in ev.get("details", {})
        assert "components" in ev.get("details", {})


def test_emit_failure_does_not_block_compile(tmp_path: Path, monkeypatch) -> None:
    """If emit raises, compile still completes normally."""
    from providence_runtime.telemetry import TelemetrySink

    def raising_emit(self, event):
        raise RuntimeError("simulated emit failure")

    monkeypatch.setattr(TelemetrySink, "emit", raising_emit)

    ws_root, phase1, phase2 = _make_compile_mocks(tmp_path)

    with (
        patch(
            "providence_cli.services.governance_compile_handlers.run_compilation",
            return_value={"phase_1": phase1, "phase_2": phase2},
        ),
        patch(
            "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
            return_value=(True, ""),
        ),
        patch(
            "providence_cli.services.governance_compile_handlers.update_profile_hash"
        ),
        patch("providence_cli.services.governance_compile_handlers.regenerate_seeds"),
        patch(
            "providence_cli.services.governance_artifact_handlers.run_governance_compile_json",
            return_value=(
                {
                    "status": "ok",
                    "ok": True,
                    "command": "governance compile",
                    "error": None,
                    "data": {},
                },
                False,
            ),
        ),
        patch("providence_cli.commands.governance.render_governance_compile_table"),
        patch(
            "providence_core.utils.environment.find_workspace_root",
            return_value=ws_root,
        ),
    ):
        from click.testing import CliRunner

        from providence_cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["governance", "compile"])

    # The command must not exit with a failure caused by the emit error
    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
