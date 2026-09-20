"""Entrypoint tests for the generated `.claude/providence-bootstrap.sh`.

Claude's PreToolUse hook runs this script from the project root. It is a POSIX
`sh` script (Claude Code uses Git Bash on Windows), so the tests are skipped
where no `sh` exists. Hermetic: the project and any fake `providence` CLI live
under `tmp_path`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from providence_wizard.orchestration.seedlings._ai_seed_templates import (
    CLAUDE_BOOTSTRAP_SCRIPT,
)

pytestmark = [
    pytest.mark.usefixtures("hermetic_env"),
    pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX sh"),
]


def _run_bootstrap(
    project: Path, path_dirs: list[Path]
) -> subprocess.CompletedProcess[str]:
    script = project / ".claude" / "providence-bootstrap.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(CLAUDE_BOOTSTRAP_SCRIPT, encoding="utf-8", newline="\n")
    sh = shutil.which("sh")
    assert sh is not None
    env = dict(os.environ)
    # sh itself must stay resolvable; a real `providence` must not be.
    env["PATH"] = os.pathsep.join([*(str(p) for p in path_dirs), str(Path(sh).parent)])
    return subprocess.run(
        [sh, ".claude/providence-bootstrap.sh"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_bootstrap_is_a_noop_outside_a_governed_project(tmp_path: Path) -> None:
    result = _run_bootstrap(tmp_path, [])

    assert result.returncode == 0
    assert "missing .providence/metadata.json" in result.stdout


def test_bootstrap_does_not_walk_up_to_a_parent_workspace(
    governed_project: Path,
) -> None:
    """Only the cwd's own `.providence/` counts; a parent workspace must not."""
    nested = governed_project / "apps" / "landing"
    nested.mkdir(parents=True)

    result = _run_bootstrap(nested, [])

    assert result.returncode == 0
    assert "missing .providence/metadata.json" in result.stdout


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="a fake `providence` shell script is not resolvable by Git Bash's "
    "`command -v` without an executable bit on NTFS",
)
def test_bootstrap_invokes_the_cli_with_the_session_guard(
    governed_project: Path, tmp_path: Path
) -> None:
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    marker = tmp_path / "args.marker"
    fake = bin_dir / "providence"
    fake.write_text(f'#!/bin/sh\necho "$@" > "{marker}"\n', encoding="utf-8")
    fake.chmod(0o755)

    result = _run_bootstrap(governed_project, [bin_dir])

    assert result.returncode == 0
    assert marker.read_text(encoding="utf-8").strip() == (
        "bootstrap run --session-guard-hours 4"
    )


def test_bootstrap_tolerates_a_missing_cli(governed_project: Path) -> None:
    result = _run_bootstrap(governed_project, [])

    assert result.returncode == 0
