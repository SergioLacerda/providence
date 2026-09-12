from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SUBPROCESS_PATTERN = re.compile(
    r"^\s*import subprocess|from subprocess|subprocess\.run\(|subprocess\.Popen\(|asyncio\.create_subprocess_exec\(",
    re.MULTILINE,
)

ALLOWED_PACKAGES = {
    # process.py is the public facade; subprocess lives in the private submodules below
    "packages/core/providence_core/src/providence_core/utils/_process_runner.py",
    "packages/core/providence_core/src/providence_core/utils/_process_runner_support.py",
    "packages/core/providence_core/src/providence_core/utils/_process_types.py",
    # PROMPT_SUBMIT_HOOK_SCRIPT is a template string written out as a standalone
    # hook script for external CLIs (Claude/Codex/Gemini hooks) — the subprocess
    # call runs in that generated script's own process, not in providence_wizard's.
    "packages/interfaces/providence_wizard/src/providence_wizard/orchestration/prompt_submit_hooks.py",
}

ALLOWED_TOOLS = {
    "tools/ci/environment_gates.py",
    "tools/ci/check_golden_policy.py",
    "tools/ci/check_core_compiler_runtime_contract.py",
    "tools/ci/check_tdd_diff_coverage.py",
    # Launches `uv run mutmut` for a scoped mutation-testing target — a
    # standalone dev/CI tool, not application code under packages/.
    "tools/testing/run_mutation_python.py",
}

MIGRATED_TOOLS = {
    "tools/testing/run-all-tests.py",
    "tools/health/health_check.py",
    "tools/governance/compliance.py",
    "tools/maintenance/lint_all.py",
    "tools/testing/diagnostics.py",
    "tools/testing/update-golden-snapshots.py",
}


def _find_with_pattern(root: Path) -> set[str]:
    found: set[str] = set()
    for path in root.rglob("*.py"):
        if "tests" in path.parts or "build" in path.parts or "dist" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if SUBPROCESS_PATTERN.search(text):
            found.add(path.relative_to(REPO_ROOT).as_posix())
    return found


def test_packages_have_no_direct_subprocess_outside_runner() -> None:
    package_hits = {
        p
        for p in _find_with_pattern(REPO_ROOT / "packages")
        if p.startswith("packages/")
    }
    assert package_hits == ALLOWED_PACKAGES


def test_migrated_tools_do_not_use_direct_subprocess() -> None:
    for rel in MIGRATED_TOOLS:
        content = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert SUBPROCESS_PATTERN.search(content) is None, rel


def test_tools_subprocess_exceptions_are_explicitly_allowlisted() -> None:
    tool_hits = {
        p for p in _find_with_pattern(REPO_ROOT / "tools") if p.startswith("tools/")
    }
    assert tool_hits == ALLOWED_TOOLS
