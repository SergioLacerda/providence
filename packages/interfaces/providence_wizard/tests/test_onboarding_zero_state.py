"""Zero-state onboarding behavior for InteractiveWizard."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from providence_wizard.application.interactive_wizard import InteractiveWizard


def _make_wizard(tmp_path: Path) -> InteractiveWizard:
    paths = {
        "root": tmp_path,
        "client_build": tmp_path / "generated" / "client" / "build",
        "client_compiled": tmp_path / "generated" / "client" / "compiled",
        "master_compiled": tmp_path / "generated" / "master" / "compiled",
        "packages": tmp_path / "packages",
    }
    with patch(
        "providence_wizard.application.interactive_wizard.get_sdd_paths",
        return_value=paths,
    ):
        return InteractiveWizard(repo_root=tmp_path, prompter=lambda _: "1")


def test_phase1_bootstraps_scaffold_on_zero_state(tmp_path: Path) -> None:
    """With no bundled canonical spec available, the wizard falls back to the
    placeholder stub for a genuine zero-state (nothing on disk, nothing packaged)."""
    wizard = _make_wizard(tmp_path)
    mock_generator = MagicMock()
    mock_generator.run.return_value = {"success": True}

    with (
        patch("builtins.input", side_effect=["1", "1"]),
        patch(
            "providence_wizard.orchestration.wizard.phase1_generator.Phase1Generator",
            return_value=mock_generator,
        ),
        patch(
            "providence_wizard.application.workspace_runtime._bundled_spec_dir",
            return_value=None,
        ),
    ):
        result = wizard.phase_1_generate_templates()

    assert result["success"] is True
    assert (wizard.client_build_dir / "docs-meta").exists()
    assert wizard.phase1_choices_dir.exists()
    assert wizard.phase2_input_dir.exists()
    assert (wizard.client_build_dir / "docs-meta" / "mandate.md").exists()
    assert (wizard.client_build_dir / "docs-meta" / "guidelines.dsl").exists()
