"""Tests for `providence governance hook status|disable|enable`.

Hermetic: every test builds its own project under a fake home
(`hermetic_env`/`governed_project` fixtures) and changes into it, so nothing
depends on the real checkout's `.providence/` or on the developer's home.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()

_CENTRAL_HOOK_REL = Path(".providence") / "runtime" / "hooks" / "prompt-submit.py"
_ADAPTER_COMMAND = 'command = "python3 .providence/runtime/hooks/prompt-submit.py"'


@pytest.fixture
def in_project(governed_project: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the CLI from inside a governed project."""
    monkeypatch.chdir(governed_project)
    return governed_project


def _write_current_central_hook(root: Path) -> Path:
    """Write a central hook containing the current template's markers."""
    central_hook = root / _CENTRAL_HOOK_REL
    central_hook.parent.mkdir(parents=True, exist_ok=True)
    central_hook.write_text(
        "#!/usr/bin/env python3\n"
        "# PROVIDENCE GOVERNANCE ACTIVE\n"
        "def _render_activation_header(context):\n"
        "    return context\n"
        '# {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}\n'
        "def _event_name(payload):\n"
        "    return payload\n",
        encoding="utf-8",
    )
    return central_hook


def _write_adapter(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ADAPTER_COMMAND, encoding="utf-8")


def _status() -> str:
    result = runner.invoke(app, ["governance", "hook", "status"])
    assert result.exit_code == 0, result.output
    return result.output.lower()


def test_hook_disable_creates_sentinel(in_project: Path) -> None:
    result = runner.invoke(app, ["governance", "hook", "disable"])

    assert result.exit_code == 0
    assert (in_project / ".providence" / "runtime" / "hook-disabled").exists()


def test_hook_enable_removes_sentinel(in_project: Path) -> None:
    sentinel = in_project / ".providence" / "runtime" / "hook-disabled"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("", encoding="utf-8")

    result = runner.invoke(app, ["governance", "hook", "enable"])

    assert result.exit_code == 0
    assert not sentinel.exists()


def test_hook_enable_when_already_absent_does_not_error(in_project: Path) -> None:
    result = runner.invoke(app, ["governance", "hook", "enable"])

    assert result.exit_code == 0


def test_hook_status_reports_enabled_when_sentinel_absent(in_project: Path) -> None:
    assert "enabled" in _status()


def test_hook_status_reports_disabled_when_sentinel_present(in_project: Path) -> None:
    sentinel = in_project / ".providence" / "runtime" / "hook-disabled"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("", encoding="utf-8")

    assert "disabled" in _status()


def test_hook_commands_resolve_the_project_root_from_a_subdirectory(
    in_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = in_project / "apps" / "landing"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = runner.invoke(app, ["governance", "hook", "disable"])

    assert result.exit_code == 0
    assert (in_project / ".providence" / "runtime" / "hook-disabled").exists()
    assert not (nested / ".providence").exists()


def test_hook_status_reports_configured_platforms_for_current_central_hook(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".codex/config.toml")

    output = _status()

    assert "codex: configured" in output
    assert "codex: configured (stale)" not in output
    assert "claude: not configured" in output


@pytest.mark.parametrize(
    ("platform", "relative"),
    [
        ("claude", ".claude/settings.json"),
        ("codex", ".codex/config.toml"),
        ("gemini", ".gemini/settings.json"),
        ("copilot", ".github/hooks/providence-prompt-submit.json"),
    ],
)
def test_hook_status_detects_every_supported_platform_adapter(
    in_project: Path, platform: str, relative: str
) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, relative)

    output = _status()

    assert f"{platform}: configured" in output
    for other in {"claude", "codex", "gemini", "copilot"} - {platform}:
        assert f"{other}: not configured" in output


def test_hook_status_reports_broken_when_adapter_references_missing_central_hook(
    in_project: Path,
) -> None:
    _write_adapter(in_project, ".codex/config.toml")

    assert "codex: configured (broken: missing central hook)" in _status()


def test_hook_status_reports_stale_when_central_hook_missing_activation_markers(
    in_project: Path,
) -> None:
    central_hook = in_project / _CENTRAL_HOOK_REL
    central_hook.parent.mkdir(parents=True)
    central_hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    _write_adapter(in_project, ".codex/config.toml")

    output = _status()

    assert "codex: configured (stale)" in output
    assert "central hook: configured but stale" in output


def test_hook_status_reports_stale_for_hook_generated_before_event_name_support(
    in_project: Path,
) -> None:
    """A hook from before the per-platform event-name fix (e.g. Gemini's
    BeforeAgent) still has the header markers but must be flagged stale."""
    central_hook = in_project / _CENTRAL_HOOK_REL
    central_hook.parent.mkdir(parents=True)
    central_hook.write_text(
        "# PROVIDENCE GOVERNANCE ACTIVE\n"
        "def _render_activation_header(context):\n"
        "    return context\n"
        '# "hookEventName": "UserPromptSubmit"\n',
        encoding="utf-8",
    )
    _write_adapter(in_project, ".gemini/settings.json")

    assert "gemini: configured (stale)" in _status()


def test_hook_status_does_not_report_empty_adapter_as_configured(
    in_project: Path,
) -> None:
    central_hook = in_project / _CENTRAL_HOOK_REL
    central_hook.parent.mkdir(parents=True)
    central_hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (in_project / ".codex").mkdir()
    (in_project / ".codex" / "config.toml").write_text("", encoding="utf-8")

    assert "codex: not configured" in _status()


def test_hook_commands_never_treat_the_global_home_cli_as_the_workspace(
    hermetic_env,
    monkeypatch: pytest.MonkeyPatch,  # noqa: ANN001
) -> None:
    """`~/.providence/` holds the global CLI; a project without its own
    `.providence/` must not resolve to it (nor get its sentinel written there)."""
    ungoverned = hermetic_env.projects / "scratch"
    ungoverned.mkdir()
    monkeypatch.chdir(ungoverned)

    result = runner.invoke(app, ["governance", "hook", "disable"])

    assert result.exit_code == 0
    assert not (
        hermetic_env.home / ".providence" / "runtime" / "hook-disabled"
    ).exists()
