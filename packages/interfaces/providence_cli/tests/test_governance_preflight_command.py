"""JSON output contract tests for `governance preflight --dry-run` (A10)."""

from __future__ import annotations

import json

from click.testing import CliRunner

from providence_cli.main import app
from providence_cli.services.runtime_preflight import PreflightResult

runner = CliRunner()


class _FakeAHP:
    def __init__(self, project_root=None) -> None:
        self.project_root = project_root

    def is_handshake_valid(self) -> bool:
        return True


def _parse_json_output(result) -> dict:
    raw = result.output or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        lines = [line for line in raw.splitlines() if line.strip()]
        return json.loads(lines[-1])


def _patch_all_checks_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.utils.loader.validate_governance_path", lambda _: True
    )
    monkeypatch.setattr(
        "providence_cli.utils.loader.load_governance_config",
        lambda _: {"core_fingerprint": "a", "client_fingerprint": "b"},
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_files_accessible",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_fingerprints_valid",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_no_conflicts",
        lambda _: True,
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_root_seed_drift",
        lambda _: (True, "no root-seed drift detected"),
    )
    monkeypatch.setattr(
        "providence_cli.services.governance_artifact_handlers.check_artifact_consistency",
        lambda _: (True, ""),
    )
    monkeypatch.setattr(
        "providence_core.governance.handshake.AgentHandshakeProtocol",
        _FakeAHP,
    )
    monkeypatch.setattr(
        "providence_cli.services.runtime_preflight.run_runtime_preflight",
        lambda _: PreflightResult(passed=True, reason="", details={"skipped": False}),
    )


def test_preflight_dry_run_never_mutates_and_exits_zero_even_on_failure(
    monkeypatch,
) -> None:
    _patch_all_checks_pass(monkeypatch)
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_no_conflicts",
        lambda _: False,
    )

    result = runner.invoke(app, ["--json", "governance", "preflight"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    assert payload["status"] == "ok"
    assert payload["data"]["dry_run"] is True
    assert payload["data"]["would_pass"] is False


def test_preflight_dry_run_annotates_checks_with_mandate_ids(monkeypatch) -> None:
    _patch_all_checks_pass(monkeypatch)

    result = runner.invoke(app, ["--json", "governance", "preflight"])

    assert result.exit_code == 0, result.output
    payload = _parse_json_output(result)
    checks = payload["data"]["checks"]
    handshake_check = next(c for c in checks if c["check"] == "Active handshake (M015)")
    assert handshake_check["mandate"] == "M015"
    assert handshake_check["passed"] is True
    assert payload["data"]["would_pass"] is True
