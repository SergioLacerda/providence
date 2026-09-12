"""Shared fixtures for providence_cli tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from providence_runtime import RuntimeEvent


@pytest.fixture(autouse=True)
def _clear_compliance_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no compliance-events path override leaks in from the session.

    The root `tests/conftest.py` sets `SDD_COMPLIANCE_EVENTS_PATH` for the
    whole pytest session as a safety net (so tests never write into the real
    repo's `.providence/runtime/`). Unit tests in this package that mock
    `resolve_workspace_root` or use their own `tmp_path` fixtures need a clean
    slate instead, since `SDD_COMPLIANCE_LOG`/`SDD_COMPLIANCE_EVENTS_PATH`/
    `SDD_TELEMETRY_PATH` all resolve the same compliance-events path (see
    `providence_core.governance.compliance_constants.resolve_compliance_log_override`)
    and would otherwise short-circuit those tests' own resolution logic. Tests
    that want to exercise a specific override still call `monkeypatch.setenv`
    themselves  that always wins over this autouse cleanup, since it runs
    within the same test after this fixture's setup.
    """
    monkeypatch.delenv("SDD_COMPLIANCE_LOG", raising=False)
    monkeypatch.delenv("SDD_COMPLIANCE_EVENTS_PATH", raising=False)
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)


@pytest.fixture
def metrics_events_path(tmp_path: Path) -> Path:
    """Fixture that provides isolated JSONL path with synthetic metrics events.

    Events are written to tmp_path/generated/metrics-events.jsonl to avoid
    reading from production .providence/runtime/ directory.
    """
    events_path = tmp_path / "generated" / "metrics-events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)

    # Write synthetic events for testing
    events = [
        # Session startup events
        RuntimeEvent(
            event="runtime.session.start",
            command="runtime status",
            status="ok",
            trace_id="trace-synthetic-1",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
        ),
        # Token consumption events (required for TokenEconomyCollector aggregation)
        RuntimeEvent(
            event="economy.token.consume",
            command="ask",
            status="ok",
            trace_id="trace-synthetic-2",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
            tokens_input=100,
            tokens_output=50,
            tokens_total=150,
            details={"model": "claude-test", "cost_usd": 0.0012},
        ),
        RuntimeEvent(
            event="economy.token.consume",
            command="ask",
            status="ok",
            trace_id="trace-synthetic-3",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
            tokens_input=200,
            tokens_output=100,
            tokens_total=300,
            details={"model": "claude-test", "cost_usd": 0.0024},
        ),
        RuntimeEvent(
            event="economy.token.consume",
            command="ask",
            status="ok",
            trace_id="trace-synthetic-4",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
            tokens_input=150,
            tokens_output=75,
            tokens_total=225,
            details={"model": "claude-test", "cost_usd": 0.0018},
        ),
    ]

    with events_path.open("w", encoding="utf-8") as fh:
        for evt in events:
            fh.write(evt.to_json() + "\n")

    return events_path
