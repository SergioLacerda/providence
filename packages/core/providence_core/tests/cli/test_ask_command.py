"""Unit tests for providence ask command."""

from __future__ import annotations

import json
import typing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from providence_cli.commands._ask_backend import (
    _capture_effective_tokens,
    _check_fingerprint_drift,
    _get_profile_state,
    _hash_query,
    _load_compiled_governance,
    _try_sdd_compiled_dir,
    app,
)
from providence_core.utils.text_io import read_text_utf8, write_text_utf8

pytestmark = pytest.mark.unit

runner = CliRunner()


@pytest.fixture(autouse=True)
def _mock_should_use_organize(tmp_path: Path) -> typing.Iterator[None]:
    dummy_artifact: dict[str, object] = {
        "intake_index_mode": "multi",
        "chunks": [],
        "retrieval_policy": "indexed_only",
    }
    dummy_path = tmp_path / ".providence" / "runtime" / "ask-intake" / "dummy.json"
    with (
        patch(
            "providence_cli.commands._ask_backend._should_use_organize",
            return_value=(True, "test"),
        ),
        patch(
            "providence_cli.commands._ask_backend.run_sdd_organize",
            return_value=(dummy_artifact, dummy_path),
        ),
    ):
        yield


def _load_json_output(raw: str) -> dict[str, object]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    parsed = json.loads(lines[-1])
    return parsed.get("data", parsed)  # type: ignore[return-value]


def _write_compiled_mandates(
    workspace_root: Path,
    mandates: list[dict[str, object]] | None = None,
) -> Path:
    compiled = workspace_root / ".providence" / "compiled"
    compiled.mkdir(parents=True, exist_ok=True)
    payload = {
        "items": mandates if mandates is not None else [{"id": "M001"}],
        "fingerprint": "abc12345ffff",
    }
    target = compiled / "governance-core.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


class TestHashQuery:
    def test_returns_8_chars(self) -> None:
        assert len(_hash_query("hello")) == 8

    def test_deterministic(self) -> None:
        assert _hash_query("test") == _hash_query("test")

    def test_different_queries_differ(self) -> None:
        assert _hash_query("a") != _hash_query("b")


class TestLoadCompiledGovernance:
    def test_returns_none_when_no_files(self, tmp_path: Path) -> None:
        source, fp, count, *_rest = _load_compiled_governance(tmp_path)
        assert source == "none"
        assert fp == ""
        assert count == 0

    def test_loads_governance_core_json(self, tmp_path: Path) -> None:
        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        gc = compiled / "governance-core.json"
        gc.write_text(
            json.dumps(
                {
                    "fingerprint": "abc12345xyz",
                    "items": [{"id": "M001"}, {"id": "M002"}],
                }
            ),
            encoding="utf-8",
        )
        # Mock out runtime path so JSON fallback inside .providence/compiled is exercised
        with patch(
            "providence_cli.services.ask_context._load_governance_via_runtime",
            return_value=None,
        ):
            source, fp, count, *_rest = _load_compiled_governance(tmp_path)
        assert source == "compiled"
        assert fp == "abc12345"
        assert count == 2

    def test_prefers_mandate_compiled_json(self, tmp_path: Path) -> None:
        compiled = tmp_path / ".providence" / "compiled"
        compiled.mkdir(parents=True)
        gc = compiled / "governance-core.json"
        gc.write_text(
            json.dumps(
                {
                    "fingerprint": "aabbccdd",
                    "items": [{"id": "M001"}, {"id": "M002"}, {"id": "M003"}],
                }
            ),
            encoding="utf-8",
        )

        with patch(
            "providence_cli.services.ask_context._load_governance_via_runtime",
            return_value=None,
        ):
            source, fp, count, *_rest = _load_compiled_governance(tmp_path)
        assert source == "compiled"
        assert count == 3


class TestAskCommand:
    def test_ask_outputs_context_block(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_core.governance.compliance.log_ask_event",
                side_effect=Exception("import fail"),
            ),
        ):
            result = runner.invoke(app, ["what are the mandates?"])

        assert result.exit_code == 0
        # M020 compact format: verbose labels replaced by key=value compact form
        assert "governance=" in result.output
        assert "mandates=" in result.output

    def test_ask_partial_state_shows_soft_directive(self, tmp_path: Path) -> None:
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "PARTIAL"),
            ),
        ):
            result = runner.invoke(app, ["test"])

        assert "SOFT" in result.output or "PARTIAL" in (
            result.output + (result.stderr or "")
        )

    def test_ask_emits_compliance_event(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}, {"id": "M002"}])
        log_path = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch.dict("os.environ", {"SDD_COMPLIANCE_EVENTS_PATH": str(log_path)}),
        ):
            runner.invoke(app, ["test query"])

        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        assert log.exists(), "compliance-events.jsonl must be written"
        events = [json.loads(line) for line in read_text_utf8(log).splitlines() if line]
        ask_events = [e for e in events if e.get("event") == "governance.ask"]
        assert ask_events
        details = ask_events[-1].get("details", {})
        assert "query_hash" in details
        assert details["context_source"] == "compiled"
        assert details["mandates_loaded"] == 2
        # Verify query text was not logged
        assert "test query" not in read_text_utf8(log)

    def test_ask_json_without_strong_signals_keeps_contract(
        self, tmp_path: Path
    ) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["status?"], obj={"output_json": True})

        assert result.exit_code == 0, result.output
        payload = _load_json_output(result.output)
        assert payload["governance_mode"] == "hard"
        assert payload["execution_gate"] in {"allowed", "blocked"}
        assert "learning_signals" in payload
        assert payload["learning_signals"]["observed_events"] == 0

    def test_ask_json_emits_learning_signals_on_recurrence(
        self, tmp_path: Path
    ) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        entries = [
            {
                "symptom": "correction_blocked",
                "root_cause": "diagnosis.inconclusive",
                "fix": "escalate_or_re_diagnose",
                "validation": "human-review",
                "regression": False,
                "tags": ["gate", "correct"],
                "evidence_refs": ["x"],
                "timestamp": now,
            },
            {
                "symptom": "correction_blocked",
                "root_cause": "diagnosis.inconclusive",
                "fix": "escalate_or_re_diagnose",
                "validation": "human-review",
                "regression": False,
                "tags": ["gate", "correct"],
                "evidence_refs": ["y"],
                "timestamp": now,
            },
        ]
        write_text_utf8(
            runtime_dir / "failure-ledger.jsonl",
            "\n".join(json.dumps(entry) for entry in entries),
        )
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["status?"], obj={"output_json": True})

        assert result.exit_code == 0, result.output
        payload = _load_json_output(result.output)
        assert payload["learning_signals"]["diagnosis_inconclusive"] == 2

    def test_ask_telemetry_includes_learning_signal_flags(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        write_text_utf8(
            runtime_dir / "failure-ledger.jsonl",
            "\n".join(
                [
                    json.dumps(
                        {
                            "symptom": "correction_blocked",
                            "root_cause": "evidence.insufficient",
                            "fix": "escalate_or_re_diagnose",
                            "validation": "re-diagnose",
                            "regression": False,
                            "tags": ["gate", "correct"],
                            "evidence_refs": ["x"],
                            "timestamp": now,
                        }
                    ),
                    json.dumps(
                        {
                            "symptom": "correction_blocked",
                            "root_cause": "evidence.insufficient",
                            "fix": "escalate_or_re_diagnose",
                            "validation": "re-diagnose",
                            "regression": False,
                            "tags": ["gate", "correct"],
                            "evidence_refs": ["y"],
                            "timestamp": now,
                        }
                    ),
                ]
            ),
        )
        warn_event_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        write_text_utf8(
            runtime_dir / "compliance-events.jsonl",
            json.dumps(
                {
                    "event": "runtime.skill.run",
                    "status": "warn",
                    "timestamp": warn_event_time,
                    "details": {},
                }
            )
            + "\n",
        )
        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch.dict("os.environ", {"SDD_COMPLIANCE_EVENTS_PATH": str(log)}),
        ):
            runner.invoke(app, ["status?"], obj={"output_json": True})

        events = [json.loads(line) for line in read_text_utf8(log).splitlines() if line]
        ask_events = [e for e in events if e.get("event") == "governance.ask"]
        assert ask_events
        details = ask_events[-1].get("details", {})
        assert "learning_signal_count" in details
        assert details["learning_signal_count"] >= 2

    def test_ask_json_emits_scope_violation_signal(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        write_text_utf8(
            runtime_dir / "failure-ledger.jsonl",
            "\n".join(
                [
                    json.dumps(
                        {
                            "symptom": "correction_blocked",
                            "root_cause": "scope.violation",
                            "fix": "narrow-scope",
                            "validation": "narrow-scope",
                            "regression": False,
                            "tags": ["gate", "correct"],
                            "evidence_refs": ["x"],
                            "timestamp": now,
                        }
                    ),
                    json.dumps(
                        {
                            "symptom": "correction_blocked",
                            "root_cause": "scope.violation",
                            "fix": "narrow-scope",
                            "validation": "narrow-scope",
                            "regression": False,
                            "tags": ["gate", "correct"],
                            "evidence_refs": ["y"],
                            "timestamp": now,
                        }
                    ),
                ]
            ),
        )
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
        ):
            result = runner.invoke(app, ["status?"], obj={"output_json": True})

        payload = _load_json_output(result.output)
        assert payload["learning_signals"]["scope_violation"] == 2

    def test_ask_json_emits_drift_signal(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        runtime_dir = tmp_path / ".providence" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        write_text_utf8(
            runtime_dir / "compliance-events.jsonl",
            json.dumps(
                {
                    "event": "runtime.skill.run",
                    "status": "warn",
                    "timestamp": now,
                    "details": {},
                }
            )
            + "\n",
        )
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch(
                "providence_cli.commands._ask_backend._runtime_drift_check",
                return_value=True,
            ),
        ):
            result = runner.invoke(app, ["status?"], obj={"output_json": True})

        payload = _load_json_output(result.output)
        assert payload["learning_signals"]["drift_recent_failures"] >= 1

    def test_ask_json_dossier_included_when_requested(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch(
                "providence_cli.commands._ask_backend._build_dossier_lines",
                return_value=["line1", "line2"],
            ),
            patch(
                "providence_cli.commands._ask_backend._load_dossier_artifact",
                return_value=None,
            ),
            patch(
                "providence_runtime.context.ContextLoader.load_result",
                return_value=type(
                    "_Result",
                    (),
                    {
                        "matched": 1,
                        "items": ["M001"],
                        "compression_ratio": None,
                        "bytes_loaded": 0,
                    },
                )(),
            ),
        ):
            result = runner.invoke(
                app,
                ["status?", "--dossier"],
                obj={"output_json": True},
            )
        payload = _load_json_output(result.output)
        assert payload["dossier"]["lines"] == ["line1", "line2"]


class TestAskFullCommand:
    def test_ask_full_outputs_context_and_compact(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_core.governance.compliance.log_ask_event", return_value=None
            ),
        ):
            result = runner.invoke(app, ["query", "--full", "--log-format", "compact"])

        assert result.exit_code == 0
        assert "execution_gate" in result.output
        assert "PROVIDENCE GOVERNANCE:" in result.output

    def test_ask_full_event_contains_trace_id_and_steps(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch.dict("os.environ", {"SDD_COMPLIANCE_EVENTS_PATH": str(log)}),
        ):
            runner.invoke(app, ["test", "--full"])

        assert log.exists()
        events = [json.loads(line) for line in read_text_utf8(log).splitlines() if line]
        full_events = [
            e
            for e in events
            if e.get("event") == "governance.ask"
            and e.get("details", {}).get("full_mode") is True
        ]
        assert full_events
        record = full_events[-1]
        assert "trace_id" in record
        details = record["details"]
        assert details["full_mode"] is True
        assert record["event"] == "governance.ask"

    def test_ask_full_custom_log_path(self, tmp_path: Path) -> None:
        log_file = tmp_path / "custom.jsonl"
        _write_compiled_mandates(tmp_path, [])

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
        ):
            result = runner.invoke(app, ["q", "--full", "--log-path", str(log_file)])

        assert result.exit_code == 0

    def test_ask_full_uses_sdd_profile_and_compiled_artifacts(
        self, tmp_path: Path
    ) -> None:
        import configparser

        sdd_compiled = tmp_path / ".providence" / "compiled"
        sdd_compiled.mkdir(parents=True)
        (sdd_compiled / "governance-core.json").write_text(
            json.dumps(
                {
                    "fingerprint": "abc12345ffff",
                    "items": [{"id": "M001"}, {"id": "M002"}],
                }
            ),
            encoding="utf-8",
        )
        (sdd_compiled / "governance-client.json").write_text(
            json.dumps(
                {
                    "fingerprint": "def67890ffff",
                    "fingerprint_core_salt": "abc12345ffff",
                    "items": [{"id": "G001"}],
                }
            ),
            encoding="utf-8",
        )

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir(exist_ok=True)
        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "client", "workspace_id": "ws-1"}
        with open(sdd_dir / "profile", "w", encoding="utf-8") as f:
            parser.write(f)

        mock_ahp = type(
            "_AHP",
            (),
            {"validate": lambda self, **_: ("HEALTHY", object())},
        )()

        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=mock_ahp,
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch.dict("os.environ", {"SDD_COMPLIANCE_EVENTS_PATH": str(log)}),
        ):
            result = runner.invoke(app, ["runtime check", "--full"])

        assert result.exit_code == 0
        events = [json.loads(line) for line in read_text_utf8(log).splitlines() if line]
        full_events = [
            e
            for e in events
            if e.get("event") == "governance.ask"
            and e.get("details", {}).get("full_mode") is True
        ]
        assert full_events
        details = full_events[-1]["details"]
        assert details["mandates_loaded"] == 2
        assert details["profile"] == "client"


class TestAskComplianceIntegration:
    """Integration: ASK_COMMAND event written to JSONL."""

    def test_event_persisted_to_jsonl(self, tmp_path: Path) -> None:
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch.dict("os.environ", {"SDD_COMPLIANCE_EVENTS_PATH": str(log)}),
        ):
            result = runner.invoke(app, ["integration test query"])

        assert result.exit_code == 0
        assert log.exists(), "compliance-events.jsonl must be written"
        events = [json.loads(line) for line in read_text_utf8(log).splitlines() if line]
        assert any(e["event"] == "governance.ask" for e in events)
        # Verify query text was not logged
        raw = read_text_utf8(log)
        assert "integration test query" not in raw


class TestCheckFingerprintDrift:
    """Tests for _check_fingerprint_drift() — B4 drift detection."""

    def _write_state(self, tmp_path: Path, compiled_fingerprint_used: str) -> Path:
        """Write governance-state.json with a same-domain compiled fingerprint.

        `check_fingerprint_drift` only ever compares `loaded_fingerprint`
        (a compiled-artifact hash) against `last_ask.compiled_fingerprint_used`
        — the same domain. `spec_fingerprint` (a source-file hash) is a
        different domain and was previously, incorrectly, used as a
        fallback (DRF-02); it now yields "unverifiable" rather than a
        cross-domain comparison, so tests here must use the same-domain
        field to exercise real drift detection.
        """
        state_dir = tmp_path / ".providence" / "runtime"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "governance-state.json"
        write_text_utf8(
            state_file,
            json.dumps(
                {"last_ask": {"compiled_fingerprint_used": compiled_fingerprint_used}}
            ),
        )
        return state_file

    def test_no_drift_when_fingerprints_match(self, tmp_path: Path) -> None:
        self._write_state(tmp_path, "deadbeef112233")
        assert _check_fingerprint_drift(tmp_path, "deadbeef") is False

    def test_drift_detected_when_fingerprints_differ(self, tmp_path: Path) -> None:
        self._write_state(tmp_path, "aabbccdd")
        assert _check_fingerprint_drift(tmp_path, "11223344") is True

    def test_spec_fingerprint_alone_is_unverifiable_not_drift(
        self, tmp_path: Path
    ) -> None:
        """DRF-02 regression: a `spec_fingerprint`-only state (no same-domain
        `compiled_fingerprint_used`) must never be compared against
        `loaded_fingerprint` — that cross-domain comparison was the bug."""
        state_dir = tmp_path / ".providence" / "runtime"
        state_dir.mkdir(parents=True, exist_ok=True)
        write_text_utf8(
            state_dir / "governance-state.json",
            json.dumps({"spec_fingerprint": "zzzzzzzz"}),
        )
        assert _check_fingerprint_drift(tmp_path, "abc12345") is False

    def test_no_drift_when_state_file_absent(self, tmp_path: Path) -> None:
        # Missing state → cannot determine drift → safe assumption False
        assert _check_fingerprint_drift(tmp_path, "deadbeef") is False

    def test_no_drift_when_loaded_fingerprint_empty(self, tmp_path: Path) -> None:
        self._write_state(tmp_path, "aabbccdd")
        assert _check_fingerprint_drift(tmp_path, "") is False

    def test_no_drift_when_state_has_no_fingerprint(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".providence" / "runtime"
        state_dir.mkdir(parents=True, exist_ok=True)
        write_text_utf8(
            state_dir / "governance-state.json",
            json.dumps({"last_check": "2026-01-01T00:00:00"}),
        )
        assert _check_fingerprint_drift(tmp_path, "deadbeef") is False

    def test_drift_field_present_in_ask_compliance_event(self, tmp_path: Path) -> None:
        """Integration: governance.ask event includes drift_detected=True when stale."""
        _write_compiled_mandates(tmp_path, [{"id": "M001"}])
        # State with a DIFFERENT same-domain compiled fingerprint to trigger drift
        self._write_state(tmp_path, "deadbeef")
        log = tmp_path / ".providence" / "runtime" / "compliance-events.jsonl"

        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_cli.commands._ask_backend._get_profile_state",
                return_value=("master", "HEALTHY"),
            ),
            patch(
                "providence_cli.services.ask_context._load_governance_via_runtime",
                return_value=None,
            ),
            patch.dict("os.environ", {"SDD_COMPLIANCE_EVENTS_PATH": str(log)}),
        ):
            runner.invoke(app, ["drift test"])

        assert log.exists()
        events = [json.loads(line) for line in read_text_utf8(log).splitlines() if line]
        ask_events = [e for e in events if e.get("event") == "governance.ask"]
        assert ask_events
        details = ask_events[-1].get("details", {})
        assert "drift_detected" in details
        assert details["drift_detected"] is True


class TestTrySddCompiledDir:
    def test_skips_invalid_json_and_uses_next_valid_file(self, tmp_path: Path) -> None:
        sdd_compiled = tmp_path / ".providence" / "compiled"
        sdd_compiled.mkdir(parents=True)
        # Create first canonical file with invalid JSON
        (sdd_compiled / "governance-client.json").write_text(
            "{invalid json", encoding="utf-8"
        )
        # Create second canonical file with valid JSON
        (sdd_compiled / "governance-core.json").write_text(
            json.dumps({"fingerprint": "ffeeddcc", "mandates": [{"id": "M001"}]}),
            encoding="utf-8",
        )

        result = _try_sdd_compiled_dir(sdd_compiled)

        assert result is not None
        source, fp, count = result
        assert source == "compiled"
        assert fp == "ffeeddcc"
        assert count == 1


class TestAuxHelpers:
    def test_get_profile_state_reads_profile_type(self, tmp_path: Path) -> None:
        import configparser

        sdd_dir = tmp_path / ".providence"
        sdd_dir.mkdir(parents=True)
        profile = configparser.ConfigParser()
        profile["sdd"] = {"type": "client"}
        with open(sdd_dir / "profile", "w", encoding="utf-8") as f:
            profile.write(f)

        mock_ahp = type(
            "_AHP",
            (),
            {"validate": lambda self, **_: ("HEALTHY", object())},
        )()
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                return_value=mock_ahp,
            ),
        ):
            prof, state = _get_profile_state()

        assert prof == "client"
        assert state == "HEALTHY"

    def test_get_profile_state_returns_unknown_on_exception(self) -> None:
        with (
            patch(
                "providence_cli.commands._ask_backend._resolve_workspace_root",
                return_value=Path("/tmp/nonexistent-test-workspace"),
            ),
            patch(
                "providence_core.governance.handshake.AgentHandshakeProtocol",
                side_effect=Exception("boom"),
            ),
        ):
            profile, state = _get_profile_state()
        assert profile == "default"
        assert state == "UNKNOWN"

    def test_capture_effective_tokens_prefers_direct_values(self) -> None:
        tokens_in, tokens_out = _capture_effective_tokens(10, 20)
        assert tokens_in == 10
        assert tokens_out == 20
