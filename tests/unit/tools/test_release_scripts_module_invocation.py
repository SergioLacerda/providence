"""Regression test for the whole class of bug fixed in Part A of the release
pipeline overhaul: any tools/release/*.py script that does a package-relative
import (e.g. `from tools.release.x import y`) must be safely invocable as a
module (`python -m tools.release.<name>`) from the repo root, because that is
how the release workflows call them. This test exercises every script in the
directory the same way CI does, using the repo's governed subprocess runner
instead of raw subprocess."""

from __future__ import annotations

import sys
from pathlib import Path

from providence_core.utils.process import SafeProcessRunner

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_SCRIPTS_DIR = REPO_ROOT / "tools" / "release"

# Each script's minimal argv to reach the import statements without requiring
# real release state (git tags, a populated dist/, etc).
SCRIPT_MODULES_AND_ARGS = {
    "resolve_vcs_version": [],
    "stage_packaged_compiler_assets": ["/nonexistent-dist-dir"],
    "validate_release_assets": ["/nonexistent-dist-dir"],
    "verify_wheel_native_assets": ["/nonexistent-dist-dir"],
    "verify_wheel_dependency_coupling": ["/nonexistent-dist-dir"],
    # An invalid version fails validation before any file is read or written,
    # so this never touches the real repo-root CHANGELOG.md/README.md.
    "prepare_release": ["--version", "not-a-version"],
}


def test_every_release_script_is_discovered() -> None:
    """Guard against this test silently going stale if a script is added."""
    on_disk = {
        path.stem
        for path in RELEASE_SCRIPTS_DIR.glob("*.py")
        if path.stem != "__init__"
    }
    assert on_disk == set(SCRIPT_MODULES_AND_ARGS)


def test_release_scripts_run_as_modules_without_import_errors() -> None:
    runner = SafeProcessRunner()
    for module_name, args in SCRIPT_MODULES_AND_ARGS.items():
        result = runner.run(
            [sys.executable, "-m", f"tools.release.{module_name}", *args],
            cwd=REPO_ROOT,
            capture_output=True,
        )
        combined_output = f"{result.stdout}\n{result.stderr}"
        assert "ModuleNotFoundError" not in combined_output, (
            f"tools.release.{module_name} failed to import when run as a "
            f"module:\n{combined_output}"
        )
