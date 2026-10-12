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
from providence_wizard.orchestration.prompt_submit_hook_script import (
    PROMPT_SUBMIT_HOOK_SCRIPT,
)

runner = CliRunner()

_CENTRAL_HOOK_REL = Path(".providence") / "runtime" / "hooks" / "prompt-submit.py"
_ADAPTER_COMMAND = 'command = "python3 .providence/runtime/hooks/prompt-submit.py"'


@pytest.fixture
def in_project(governed_project: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the CLI from inside a governed project."""
    monkeypatch.chdir(governed_project)
    return governed_project


def _write_current_central_hook(root: Path) -> Path:
    """Write the central hook exactly as the current generator template."""
    central_hook = root / _CENTRAL_HOOK_REL
    central_hook.parent.mkdir(parents=True, exist_ok=True)
    central_hook.write_text(PROMPT_SUBMIT_HOOK_SCRIPT, encoding="utf-8")
    return central_hook


def _write_adapter(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ADAPTER_COMMAND, encoding="utf-8")


def _status(expected_exit: int = 0) -> str:
    """Run `hook status`; healthy or intentional states exit 0, any broken,
    stale or legacy adapter exits 1 (the command is a gate-quality signal)."""
    result = runner.invoke(app, ["governance", "hook", "status"])
    assert result.exit_code == expected_exit, result.output
    return result.output.lower()


def _flat(output: str) -> str:
    """Collapse the terminal wrapping Rich applies to long status lines."""
    return " ".join(output.split())


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
        ("devin", ".devin/hooks.v1.json"),
    ],
)
def test_hook_status_detects_every_supported_platform_adapter(
    in_project: Path, platform: str, relative: str
) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, relative)

    output = _status()

    assert f"{platform}: configured" in output
    for other in {"claude", "codex", "gemini", "copilot", "devin"} - {platform}:
        if platform == "claude" and other == "devin":
            continue  # Devin loads .claude/settings.json by default
        assert f"{other}: not configured" in output


def test_hook_status_reports_broken_when_adapter_references_missing_central_hook(
    in_project: Path,
) -> None:
    _write_adapter(in_project, ".codex/config.toml")

    assert "codex: configured (broken: missing central hook)" in _status(1)


def test_hook_status_reports_stale_when_central_hook_missing_activation_markers(
    in_project: Path,
) -> None:
    central_hook = in_project / _CENTRAL_HOOK_REL
    central_hook.parent.mkdir(parents=True)
    central_hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    _write_adapter(in_project, ".codex/config.toml")

    output = _status(1)

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

    assert "gemini: configured (stale)" in _status(1)


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


_LEGACY_SHAPE = (
    'sh -c \'hook=$1; if [ -f "$hook" ]; then exec python3 "$hook"; fi; '
    "exit 0' sh {target}"
)


def _write_command_adapter(root: Path, relative: str, command: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'command = "{command}"\n', encoding="utf-8")


def test_hook_status_exits_zero_when_every_configured_adapter_is_healthy(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".codex/config.toml")
    _write_adapter(in_project, ".gemini/settings.json")

    output = _status(0)

    assert "codex: configured" in output
    assert "gemini: configured" in output


def test_hook_status_rejects_the_retired_absolute_path_command_shape(
    in_project: Path,
) -> None:
    """The `hook=$1` launcher with an absolute path is the dead command shape
    generated by providence-cli 1.0.14 to 1.0.16: rejected, never `configured`,
    even when the central hook of this workspace exists."""
    _write_current_central_hook(in_project)
    missing = in_project / "generated" / "client" / "compiled" / _CENTRAL_HOOK_REL
    _write_command_adapter(
        in_project,
        ".claude/settings.json",
        _LEGACY_SHAPE.format(target=missing.as_posix()),
    )

    output = _status(1)

    assert "claude: legacy (rejected" in _flat(output)
    assert "providence governance generate" in _flat(output)


def test_hook_status_rejects_the_pre_rebrand_central_hook_reference(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)
    _write_command_adapter(
        in_project,
        ".gemini/settings.json",
        "python3 .providence/runtime/hooks/sdd-governance-inject.py",
    )

    output = _status(1)

    assert "gemini: legacy (rejected" in output


def test_hook_status_reports_missing_absolute_target(in_project: Path) -> None:
    """An adapter must be judged by the path it really runs, not by the
    workspace hook next to it."""
    _write_current_central_hook(in_project)
    missing = in_project / "elsewhere" / _CENTRAL_HOOK_REL
    _write_command_adapter(
        in_project,
        ".codex/config.toml",
        f"python3 {missing.as_posix()}",
    )

    output = _status(1)

    assert "codex: broken (target missing" in _flat(output)
    assert missing.as_posix().lower() in "".join(output.split())


def test_hook_status_reports_target_outside_the_workspace(
    in_project: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    _write_current_central_hook(in_project)
    other = tmp_path_factory.mktemp("other-project")
    foreign = _write_current_central_hook(other)
    _write_command_adapter(
        in_project, ".codex/config.toml", f"python3 {foreign.as_posix()}"
    )

    output = _status(1)

    assert "codex: broken (target outside workspace" in output


def test_hook_status_accepts_an_absolute_target_inside_the_workspace(
    in_project: Path,
) -> None:
    central = _write_current_central_hook(in_project)
    _write_command_adapter(
        in_project, ".codex/config.toml", f"python3 {central.as_posix()}"
    )

    assert "codex: configured" in _status(0)


def test_hook_status_flags_a_hook_that_differs_from_the_template_by_digest(
    in_project: Path,
) -> None:
    """Markers alone are not proof of currency: a hook that keeps every marker
    but differs from the template is stale."""
    central = _write_current_central_hook(in_project)
    central.write_text(
        central.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8"
    )
    _write_adapter(in_project, ".codex/config.toml")

    output = _status(1)

    assert "codex: configured (stale)" in output
    assert "central hook: configured but stale" in output


def test_hook_status_states_the_codex_trust_requirement(in_project: Path) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".codex/config.toml")

    output = _flat(_status(0))

    assert "codex note:" in output
    assert "trust" in output
    # Documented behavior: trust is per exact definition and reviewed in /hooks.
    assert "/hooks" in output
    assert "hash" in output


def test_hook_status_states_that_copilot_injection_is_not_guaranteed(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".github/hooks/providence-prompt-submit.json")

    output = _flat(_status(0))

    assert "copilot note:" in output
    assert "not guaranteed" in output


def test_hook_status_prints_no_platform_note_for_unconfigured_platforms(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)

    output = _status(0)

    assert "note:" not in output


def test_hook_status_reports_devin_as_covered_by_the_claude_adapter(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".claude/settings.json")

    output = _flat(_status(0))

    assert "claude: configured" in output
    assert "devin: configured, via .claude/settings.json" in output


def test_hook_status_flags_a_double_devin_registration(in_project: Path) -> None:
    """Devin loads both files and documents no merge rule: report, do not guess."""
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".claude/settings.json")
    _write_adapter(in_project, ".devin/hooks.v1.json")

    output = _flat(_status(1))

    assert "devin: broken (registered twice" in output


def test_hook_status_rejects_a_devin_file_with_a_hooks_wrapper(
    in_project: Path,
) -> None:
    _write_current_central_hook(in_project)
    path = in_project / ".devin" / "hooks.v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", '
        '"command": "python3 .providence/runtime/hooks/prompt-submit.py"}]}]}}',
        encoding="utf-8",
    )

    output = _flat(_status(1))

    assert "devin: broken (a 'hooks' wrapper key is not valid" in output


def test_hook_status_states_the_devin_limits(in_project: Path) -> None:
    _write_current_central_hook(in_project)
    _write_adapter(in_project, ".devin/hooks.v1.json")

    output = _flat(_status(0))

    assert "devin note:" in output
    assert "DEVIN_PROJECT_DIR".lower() in output
