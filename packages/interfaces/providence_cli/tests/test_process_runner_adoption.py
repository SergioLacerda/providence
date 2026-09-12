"""Contract tests for process runner adoption in CLI command modules."""

from pathlib import Path


def test_tools_command_uses_safe_process_runner_not_subprocess() -> None:
    # T11 (2026-08-22): tool-execution moved from tools.py into tools_run.py.
    content = Path(
        "packages/interfaces/providence_cli/src/providence_cli/commands/tools_run.py"
    ).read_text(encoding="utf-8")
    assert "SafeProcessRunner" in content
    assert "subprocess.run(" not in content
