"""Unit tests for tools/ci/hook_launcher_gate.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ci import hook_launcher_gate as gate
from tools.testing import hook_launcher_probe as probe

pytestmark = pytest.mark.unit

_COPILOT = ".github/hooks/providence-prompt-submit.json"


def _row(source: str, shell: str = "sh", outcome: str = "injected") -> dict:
    return {"source": source, "shell": shell, "outcome": outcome}


@pytest.fixture
def host_shell_only(monkeypatch: pytest.MonkeyPatch) -> None:
    host = probe.available_shells()[:1]
    monkeypatch.setattr(probe, "available_shells", lambda: host)


@pytest.mark.parametrize(
    ("source", "shell", "enforced"),
    [
        (".claude/settings.json:command", "cmd", True),
        (".codex/config.toml", "pwsh", True),
        (".devin/hooks.v1.json:command", "powershell", True),
        (f"{_COPILOT}:bash", "sh", True),
        (f"{_COPILOT}:bash", "cmd", False),
        (f"{_COPILOT}:powershell", "powershell", True),
        (f"{_COPILOT}:powershell", "pwsh", True),
        (f"{_COPILOT}:powershell", "sh", False),
        (f"{_COPILOT}:command", "sh", True),
        (f"{_COPILOT}:command", "cmd", False),
    ],
)
def test_is_enforced_keeps_only_the_native_copilot_pairings(
    source: str, shell: str, enforced: bool
) -> None:
    assert gate.is_enforced(_row(source, shell)) is enforced


@pytest.mark.parametrize(
    ("outcome", "governed", "source", "ok"),
    [
        ("injected", True, ".claude/settings.json:command", True),
        ("degraded:cli_not_found", True, ".claude/settings.json:command", True),
        ("skipped:empty_output", True, ".claude/settings.json:command", True),
        ("silent", True, ".claude/settings.json:command", False),
        ("error", True, ".claude/settings.json:command", False),
        ("timeout", True, ".claude/settings.json:command", False),
        ("silent", False, ".claude/settings.json:command", True),
        ("degraded:cli_not_found", False, ".claude/settings.json:command", False),
        # Devin anchors on DEVIN_PROJECT_DIR, so it reaches the hook from anywhere.
        ("degraded:cli_not_found", False, ".devin/hooks.v1.json:command", True),
        ("silent", False, ".devin/hooks.v1.json:command", False),
    ],
)
def test_judge(outcome: str, governed: bool, source: str, ok: bool) -> None:
    assert gate.judge(_row(source, outcome=outcome), governed=governed) is ok


def test_run_gate_passes_for_the_source_generator_on_this_host(
    tmp_path: Path, host_shell_only: None
) -> None:
    rows = gate.run_gate(tmp_path)

    assert {row["scenario"] for row in rows} == {
        "governed",
        "subdirectory",
        "ungoverned",
        "devin governed",
        "devin ungoverned",
    }
    assert [row for row in rows if not row["ok"]] == []
    assert any(row["source"].startswith(".devin/") for row in rows)


def test_main_writes_reports_and_exits_zero(
    tmp_path: Path, host_shell_only: None
) -> None:
    json_out = tmp_path / "out" / "gate.json"
    md_out = tmp_path / "out" / "gate.md"

    code = gate.main(["--json-out", str(json_out), "--md-out", str(md_out)])

    assert code == 0
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["rows"]
    assert "Hook launcher gate" in md_out.read_text(encoding="utf-8")


def test_main_fails_when_a_run_does_not_reach_the_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad = {
        **_row(".claude/settings.json:command", outcome="silent"),
        "scenario": "governed",
        "enforced": True,
        "ok": False,
    }
    monkeypatch.setattr(gate, "run_gate", lambda _scratch: [bad])

    assert gate.main([]) == 1


def test_main_fails_when_no_adapter_command_was_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gate, "run_gate", lambda _scratch: [])

    assert gate.main([]) == 1


def test_markdown_marks_failures_and_report_only_rows() -> None:
    rows = [
        {
            **_row("a:command", outcome="silent"),
            "scenario": "governed",
            "enforced": True,
            "ok": False,
        },
        {
            **_row(f"{_COPILOT}:bash", "cmd"),
            "scenario": "governed",
            "enforced": False,
            "ok": True,
        },
    ]

    text = gate.render_markdown(rows, "win32")

    assert "**FAIL**" in text
    assert "1 failed (1 reported only)" in text
