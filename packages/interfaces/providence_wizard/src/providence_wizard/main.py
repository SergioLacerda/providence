"""SDD Wizard public entry point  consumed by providence_cli wizard command."""

from __future__ import annotations

from pathlib import Path

from providence_wizard.contracts import WizardInvocation
from providence_wizard.contracts import run_wizard as run_wizard_contract


def run_wizard(repo_root: Path | None = None, output_dir: Path | None = None) -> None:
    """Launch the interactive SDD wizard."""
    root = repo_root or Path.cwd()
    result = run_wizard_contract(
        WizardInvocation(project_root=root, output_path=output_dir)
    )

    if not result.success:
        import sys

        sys.exit(1)
