"""Tests for `providence governance hook status|disable|enable`."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def test_hook_disable_creates_sentinel(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        (root / ".providence").mkdir()

        result = runner.invoke(app, ["governance", "hook", "disable"])

        assert result.exit_code == 0
        assert (root / ".providence" / "runtime" / "hook-disabled").exists()


def test_hook_enable_removes_sentinel(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        sentinel = root / ".providence" / "runtime" / "hook-disabled"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        result = runner.invoke(app, ["governance", "hook", "enable"])

        assert result.exit_code == 0
        assert not sentinel.exists()


def test_hook_enable_when_already_absent_does_not_error(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        (root / ".providence").mkdir()

        result = runner.invoke(app, ["governance", "hook", "enable"])

        assert result.exit_code == 0


def test_hook_status_reports_enabled_when_sentinel_absent(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        (root / ".providence").mkdir()

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "enabled" in result.output.lower()


def _write_current_central_hook(root: Path) -> Path:
    """Write a central hook containing the current template's activation markers."""
    central_hook = root / ".providence" / "runtime" / "hooks" / "prompt-submit.py"
    central_hook.parent.mkdir(parents=True, exist_ok=True)
    central_hook.write_text(
        "#!/usr/bin/env python3\n"
        "# PROVIDENCE GOVERNANCE ACTIVE\n"
        "def _render_activation_header(context):\n"
        "    return context\n"
        '# {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}\n',
        encoding="utf-8",
    )
    return central_hook


def test_hook_status_reports_configured_platforms_for_current_central_hook(
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        _write_current_central_hook(root)
        (root / ".codex").mkdir()
        (root / ".codex" / "config.toml").write_text(
            'command = "python3 .providence/runtime/hooks/prompt-submit.py"',
            encoding="utf-8",
        )

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "codex: configured" in result.output.lower()
        assert "codex: configured (stale)" not in result.output.lower()
        assert "claude: not configured" in result.output.lower()


def test_hook_status_reports_stale_when_central_hook_missing_activation_markers(
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        central_hook = root / ".providence" / "runtime" / "hooks" / "prompt-submit.py"
        central_hook.parent.mkdir(parents=True)
        central_hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (root / ".codex").mkdir()
        (root / ".codex" / "config.toml").write_text(
            'command = "python3 .providence/runtime/hooks/prompt-submit.py"',
            encoding="utf-8",
        )

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "codex: configured (stale)" in result.output.lower()
        assert "central hook: configured but stale" in result.output.lower()


def test_hook_status_does_not_report_empty_adapter_as_configured(
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        central_hook = root / ".providence" / "runtime" / "hooks" / "prompt-submit.py"
        central_hook.parent.mkdir(parents=True)
        central_hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (root / ".codex").mkdir()
        (root / ".codex" / "config.toml").write_text("", encoding="utf-8")

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "codex: not configured" in result.output.lower()


def test_hook_status_reports_disabled_when_sentinel_present(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        sentinel = root / ".providence" / "runtime" / "hook-disabled"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "disabled" in result.output.lower()
