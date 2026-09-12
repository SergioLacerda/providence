from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from tests.helpers.text_io import read_text_utf8

from providence_cli.main import app

runner = CliRunner()
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _load_json_output(raw: str) -> dict:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _normalize_ask_payload(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


def _assert_json_snapshot(name: str, payload: dict) -> None:
    expected = json.loads(read_text_utf8(SNAPSHOT_DIR / name))
    assert _normalize_ask_payload(payload) == expected


def test_ask_run_json_snapshot(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light", "", 0, "indexed_only", None),
        ),
        patch(
            "providence_cli.commands._ask_backend._get_profile_state",
            return_value=("master", "HEALTHY"),
        ),
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend._write_runtime_cache",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend._store_routing_decision",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend._upsert_ask_session",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "fp-1",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "verified",
                "drift_detected": False,
                "root_seed_drift_detected": False,
                "learning_signals": {
                    "diagnosis_inconclusive": 0,
                    "evidence_insufficient": 0,
                    "scope_violation": 0,
                    "drift_recent_failures": 0,
                    "observed_events": 0,
                    "window_days": 7,
                },
            },
        ),
    ):
        result = runner.invoke(app, ["--json", "ask", "status?"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    _assert_json_snapshot("ask_run.json", payload)


def test_ask_run_json_with_learning_snapshot(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light", "", 0, "indexed_only", None),
        ),
        patch(
            "providence_cli.commands._ask_backend._get_profile_state",
            return_value=("master", "HEALTHY"),
        ),
        patch(
            "providence_cli.commands._ask_backend._emit_ask_telemetry",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend._write_runtime_cache",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend._store_routing_decision",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend._upsert_ask_session",
            return_value=None,
        ),
        patch(
            "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "fp-1",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "verified",
                "drift_detected": False,
                "root_seed_drift_detected": False,
                "learning_signals": {
                    "diagnosis_inconclusive": 2,
                    "evidence_insufficient": 1,
                    "scope_violation": 0,
                    "drift_recent_failures": 0,
                    "observed_events": 3,
                    "window_days": 7,
                },
            },
        ),
    ):
        result = runner.invoke(app, ["--json", "ask", "status?"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    _assert_json_snapshot("ask_run_with_learning.json", payload)
