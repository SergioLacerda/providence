"""Startup performance regression tests for the providence_wizard contract boundary.

These tests guard the BigBang refactor invariant: importing the wizard CLI
entrypoint and resolving its `--help` output must not pull heavy orchestration,
application, or interactive-prompt machinery into memory. That keeps
`providence wizard --help` fast regardless of how large the underlying pipeline grows.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.perf]

_PROBE_SCRIPT = """
import sys

from click.testing import CliRunner

from providence_cli.commands.wizard import app

runner = CliRunner()
result = runner.invoke(app, ["run", "--help"])
assert result.exit_code == 0, result.output

loaded_heavy = sorted(
    name
    for name in sys.modules
    if name.startswith(("providence_wizard.application", "providence_wizard.orchestration", "questionary"))
)
print("\\n".join(loaded_heavy))
"""

_CONTRACTS_PROBE_SCRIPT = """
import sys

from providence_wizard.contracts import WizardInvocation, run_wizard

loaded_heavy = sorted(
    name for name in sys.modules
    if name.startswith(("providence_wizard.application", "providence_wizard.orchestration", "questionary"))
)
print("\\n".join(loaded_heavy))
"""


def test_wizard_help_does_not_import_heavy_modules() -> None:
    """`providence wizard run --help` must not import application/orchestration/questionary."""
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE_SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    loaded_heavy = [line for line in proc.stdout.splitlines() if line.strip()]
    assert loaded_heavy == [], (
        f"`providence wizard run --help` imported heavy modules: {loaded_heavy}"
    )


def test_contracts_import_is_lightweight() -> None:
    """`providence_wizard.contracts` must not transitively import orchestration/application."""
    proc = subprocess.run(
        [sys.executable, "-c", _CONTRACTS_PROBE_SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    loaded_heavy = [line for line in proc.stdout.splitlines() if line.strip()]
    assert loaded_heavy == [], (
        f"providence_wizard.contracts imported heavy modules: {loaded_heavy}"
    )
