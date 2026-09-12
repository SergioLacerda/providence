"""Repo portability policy: no git symlinks may be tracked.

Git symlinks (mode 120000) are checked out as plain text files containing the
link target on Windows clones without symlink support (`core.symlinks=false`,
the Windows default). Any code that ships or reads such a file — package data,
templates, specs — then silently consumes a path stub instead of the real
content. This broke client onboarding on Windows when the providence_core packaged
mandate.spec/guidelines.dsl were symlinks: the wizard copied the stub and the
governance pipeline parsed zero mandates. Tracked symlinks are therefore
banned repo-wide; ship real files instead.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

_GIT_SYMLINK_MODE = "120000"


def test_repo_tracks_no_git_symlinks() -> None:
    # The sovereign container's shadow repo has no .git (excluded via
    # .dockerignore); the policy is still enforced by the host CI jobs
    # that run on a real checkout.
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout (hermetic container shadow repo)")
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    symlinks = [
        line.split("\t", 1)[-1]
        for line in result.stdout.splitlines()
        if line.split(" ", 1)[0] == _GIT_SYMLINK_MODE
    ]
    assert not symlinks, (
        "Tracked git symlinks break Windows clones (checked out as plain text "
        "stubs with core.symlinks=false). Replace with real files: "
        + ", ".join(symlinks)
    )
