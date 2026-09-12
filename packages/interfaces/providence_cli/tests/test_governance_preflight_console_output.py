"""Console (non-JSON) output tests for `providence governance preflight --dry-run`.

The JSON-mode contract is covered by ``test_governance_preflight_command.py``;
this module exercises the rich-console rendering branch (panel, table, and the
pass/fail summary line) that was previously untested.
"""

from __future__ import annotations

import io

from rich.console import Console

from providence_cli.services.governance_preflight_handlers import (
    run_governance_preflight_cmd,
)
from providence_cli.services.runtime_preflight import PreflightResult


class _FakeAHP:
    def __init__(self, project_root=None) -> None:
        self.project_root = project_root

    def is_handshake_valid(self) -> bool:
        return True


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


def _run_and_capture(monkeypatch, path: str = ".providence/compiled") -> str:
    buffer = io.StringIO()
    console = Console(file=buffer, width=200)
    run_governance_preflight_cmd(path=path, output_json=False, console=console)
    return buffer.getvalue()


def test_console_output_reports_all_checks_pass(monkeypatch) -> None:
    _patch_all_checks_pass(monkeypatch)

    output = _run_and_capture(monkeypatch)

    assert "Preflight (dry run" in output
    assert "Preflight Checks" in output
    assert "Active handshake (M015)" in output
    assert "M015" in output
    assert "PASS" in output
    assert "all checks would pass" in output


def test_console_output_reports_failure_without_mutating_or_gating(monkeypatch) -> None:
    _patch_all_checks_pass(monkeypatch)
    monkeypatch.setattr(
        "providence_cli.services.governance_config_reader.check_no_conflicts",
        lambda _: False,
    )

    output = _run_and_capture(monkeypatch)

    assert "FAIL" in output
    assert "one or more checks would fail" in output
    assert "providence governance validate" in output
