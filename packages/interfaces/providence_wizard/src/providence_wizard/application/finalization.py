"""Translate internal execution state into public wizard results."""

from __future__ import annotations

from providence_wizard.contracts import WizardResult


def build_wizard_result(success: bool, error: str = "") -> WizardResult:
    """Return the canonical public result."""
    if success:
        return WizardResult(success=True)
    return WizardResult(success=False, errors=[error or "Wizard execution failed."])
