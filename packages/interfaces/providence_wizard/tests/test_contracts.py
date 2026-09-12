"""Tests for the canonical public wizard contracts."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_wizard.contracts import WizardInvocation, WizardResult, run_wizard


def test_run_wizard_uses_session_bootstrap(tmp_path: Path) -> None:
    expected = WizardResult(success=True)
    with patch(
        "providence_wizard.application.session_bootstrap.SessionBootstrap.run",
        return_value=expected,
    ) as mock_run:
        result = run_wizard(WizardInvocation(project_root=tmp_path))

    assert result == expected
    bootstrap = mock_run.call_args_list[0]
    assert bootstrap
