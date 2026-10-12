"""Unit tests for tools/testing/hook_launcher_probe.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tools.testing import hook_launcher_probe as probe

pytestmark = pytest.mark.unit

_DISCOVER_SHELLS = probe.available_shells


@pytest.fixture(autouse=True)
def _host_shell_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the probe to the host's own shell.

    CI images ship `pwsh`, and PowerShell does not run a command that starts
    with a quoted path (it needs `&`), so one row per installed shell would make
    these tests depend on the machine. Shell discovery has its own test.
    """
    host = _DISCOVER_SHELLS()[:1]
    monkeypatch.setattr(probe, "available_shells", lambda: host)


_ACTIVE = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "PROVIDENCE GOVERNANCE ACTIVE | source=prompt-submit-hook",
    }
}


def _workspace(tmp_path: Path, emitted: str, exit_code: int = 0) -> Path:
    emitter = tmp_path / "emit.py"
    emitter.write_text(
        "import sys\n"
        "sys.stdin.read()\n"
        f"sys.stdout.write({emitted!r})\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    command = f'"{sys.executable}" "{emitter}" prompt-submit.py'
    hooks = tmp_path / ".github" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "providence-prompt-submit.json").write_text(
        json.dumps(
            {"hooks": {"UserPromptSubmit": [{"command": command, "bash": command}]}}
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_find_commands_reads_every_command_key_and_codex_toml(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "")
    (workspace / ".codex").mkdir()
    (workspace / ".codex" / "config.toml").write_text(
        'command = "python3 -c \\"x\\" prompt-submit.py"\ntimeout = 15\n',
        encoding="utf-8",
    )

    labels = [label for label, _ in probe.find_commands(workspace)]

    assert labels == [
        ".github/hooks/providence-prompt-submit.json:command",
        ".github/hooks/providence-prompt-submit.json:bash",
        ".codex/config.toml",
    ]


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "expected"),
    [
        (0, json.dumps(_ACTIVE), "", "injected"),
        (
            0,
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "additionalContext": "PROVIDENCE GOVERNANCE DEGRADED | reason=cli_not_found"
                    }
                }
            ),
            "",
            "degraded:cli_not_found",
        ),
        (0, "", "providence-hook: skipped reason=empty_output", "skipped:empty_output"),
        (0, "", "", "silent"),
        (1, "", "", "error"),
        (0, "not json", "", "error"),
    ],
)
def test_classify(returncode: int, stdout: str, stderr: str, expected: str) -> None:
    assert probe.classify(returncode, stdout, stderr) == expected


def test_probe_runs_each_command_under_the_host_shell(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, json.dumps(_ACTIVE))

    rows = probe.probe(workspace, "implement C")

    assert rows
    assert {row["outcome"] for row in rows} == {"injected"}


def test_available_shells_lists_the_host_shell_first_then_powershell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    found = {"powershell": "/x/powershell", "pwsh": "/x/pwsh"}
    monkeypatch.setattr(probe.shutil, "which", lambda name: found.get(name))

    shells = _DISCOVER_SHELLS()

    assert [name for name, _ in shells] == [
        "cmd" if probe.os.name == "nt" else "sh",
        "powershell",
        "pwsh",
    ]
    assert shells[0][1] is None
    assert shells[1][1][:2] == ["/x/powershell", "-NoProfile"]


def test_available_shells_is_only_the_host_shell_without_powershell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(probe.shutil, "which", lambda name: None)

    assert len(_DISCOVER_SHELLS()) == 1


def test_probe_reports_one_row_per_command_and_installed_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path, json.dumps(_ACTIVE))
    monkeypatch.setattr(
        probe,
        "available_shells",
        lambda: [("sh", None), ("sh-again", None)],
    )

    rows = probe.probe(workspace, "implement C")

    assert [(row["source"], row["shell"]) for row in rows] == [
        (".github/hooks/providence-prompt-submit.json:command", "sh"),
        (".github/hooks/providence-prompt-submit.json:command", "sh-again"),
        (".github/hooks/providence-prompt-submit.json:bash", "sh"),
        (".github/hooks/providence-prompt-submit.json:bash", "sh-again"),
    ]


def test_main_exits_one_when_a_command_errors(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "", exit_code=3)

    assert probe.main(["--workspace", str(workspace)]) == 1


def test_main_exits_one_without_any_adapter(tmp_path: Path) -> None:
    assert probe.main(["--workspace", str(tmp_path)]) == 1


def test_probe_reads_the_devin_file_and_sets_the_project_dir(tmp_path: Path) -> None:
    """Devin sets DEVIN_PROJECT_DIR for its hooks; the probe models that for
    commands read from `.devin/hooks.v1.json` only."""
    emitter = tmp_path / "emit_env.py"
    emitter.write_text(
        "import json, os, sys\n"
        "sys.stdin.read()\n"
        "seen = os.environ.get('DEVIN_PROJECT_DIR', 'absent')\n"
        "print(json.dumps({'hookSpecificOutput': {'additionalContext': "
        "'PROVIDENCE GOVERNANCE DEGRADED | reason=' + ('set' if seen != 'absent' "
        "else 'absent')}}))\n",
        encoding="utf-8",
    )
    command = f'"{sys.executable}" "{emitter}" prompt-submit.py'
    (tmp_path / ".devin").mkdir()
    (tmp_path / ".devin" / "hooks.v1.json").write_text(
        json.dumps({"UserPromptSubmit": [{"hooks": [{"command": command}]}]}),
        encoding="utf-8",
    )

    rows = probe.probe(tmp_path, "implement C")

    assert [row["source"] for row in rows] == [".devin/hooks.v1.json:command"]
    assert rows[0]["outcome"] == "degraded:set"
