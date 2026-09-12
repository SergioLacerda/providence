"""Tests for InteractiveWizard B110 exception handling.

This module validates that _get_enforcement_label() correctly handles exceptions
when reading the wizard configuration file (B110 nosec annotation at interactive_mode.py:769).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from providence_wizard.application.interactive_wizard import InteractiveWizard


class TestInteractiveWizardEnforcementLabel:
    """Test InteractiveWizard._get_enforcement_label exception handling."""

    @staticmethod
    def _make_wizard_with_config_path(config_path: Path) -> InteractiveWizard:
        """Create an InteractiveWizard instance with a specific config_path.

        Uses object.__setattr__ to bypass __init__ and set only the required attribute.
        """
        wizard = object.__new__(InteractiveWizard)
        object.__setattr__(wizard, "wizard_config_path", config_path)
        return wizard

    def test_get_enforcement_label_fallback_on_corrupt_json(
        self, tmp_path: Path
    ) -> None:
        """Test that _get_enforcement_label returns default when JSON is corrupted.

        This covers the try-except-pass fallback at interactive_mode.py:769
        when the config file contains invalid JSON.

        Expected behavior: return "Alertas" (warn_mode default) when parsing fails.
        """
        config_file = tmp_path / "wizard-config.json"
        config_file.write_text("{invalid json}", encoding="utf-8")

        wizard = self._make_wizard_with_config_path(config_file)
        label = wizard._get_enforcement_label()

        assert label == "Alertas"

    def test_get_enforcement_label_returns_correct_label(self, tmp_path: Path) -> None:
        """Test that _get_enforcement_label returns the correct mode label.

        Validates the happy path: when config file is valid and exists,
        the correct label is returned for each enforcement mode.
        """
        config_file = tmp_path / "wizard-config.json"

        # Test each enforcement mode
        test_cases = [
            ("silent_mode", "Sem Alertas"),
            ("warn_mode", "Alertas"),
            ("strict_mode", "Bloquear"),
        ]

        for mode, expected_label in test_cases:
            config_file.write_text(
                json.dumps({"enforcement_mode": mode}), encoding="utf-8"
            )

            wizard = self._make_wizard_with_config_path(config_file)
            label = wizard._get_enforcement_label()

            assert label == expected_label, (
                f"Mode {mode} should return {expected_label}"
            )

    def test_get_enforcement_label_fallback_on_missing_file(
        self, tmp_path: Path
    ) -> None:
        """Test that _get_enforcement_label returns default when config file is missing.

        This covers the try-except-pass fallback at interactive_mode.py:769
        when wizard_config_path does not exist.

        Expected behavior: return "Alertas" (warn_mode default) when file is missing.
        """
        missing_file = tmp_path / "nonexistent.json"

        wizard = self._make_wizard_with_config_path(missing_file)
        label = wizard._get_enforcement_label()

        assert label == "Alertas"

    def test_get_enforcement_label_fallback_on_unknown_mode(
        self, tmp_path: Path
    ) -> None:
        """Test that _get_enforcement_label returns default for unknown enforcement mode.

        Validates the fallback behavior when enforcement_mode has an unexpected value
        that doesn't map to the labels dict.

        Expected behavior: return "Alertas" (the default in labels.get).
        """
        config_file = tmp_path / "wizard-config.json"
        config_file.write_text(
            json.dumps({"enforcement_mode": "unknown_mode"}), encoding="utf-8"
        )

        wizard = self._make_wizard_with_config_path(config_file)
        label = wizard._get_enforcement_label()

        assert label == "Alertas"

    def test_get_enforcement_label_fallback_on_permission_error(
        self, tmp_path: Path
    ) -> None:
        """Test that _get_enforcement_label returns default on permission errors.

        This validates the broad Exception handler catches PermissionError
        and returns the default fallback.

        Expected behavior: return "Alertas" when file cannot be read.
        """
        config_file = tmp_path / "wizard-config.json"
        config_file.write_text(
            json.dumps({"enforcement_mode": "strict_mode"}), encoding="utf-8"
        )

        wizard = self._make_wizard_with_config_path(config_file)

        # Patch the open() call to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            label = wizard._get_enforcement_label()

            assert label == "Alertas"


class TestInteractiveWizardSelectorSelection:
    @staticmethod
    def _make_wizard_with_selector_path(selector_path: Path) -> InteractiveWizard:
        wizard = object.__new__(InteractiveWizard)
        object.__setattr__(wizard, "selector_output_path", selector_path)
        return wizard

    def test_load_selector_selection_ids_returns_empty_when_missing(
        self, tmp_path: Path
    ) -> None:
        wizard = self._make_wizard_with_selector_path(tmp_path / "missing.json")
        assert wizard.load_selector_selection_ids() == []

    def test_load_selector_selection_ids_returns_resolved_ids(
        self, tmp_path: Path
    ) -> None:
        selection_path = tmp_path / "selector-selection.json"
        selection_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "selected_ids": ["M001"],
                    "resolved_ids": ["M001", "M002"],
                }
            ),
            encoding="utf-8",
        )
        wizard = self._make_wizard_with_selector_path(selection_path)
        ids = wizard.load_selector_selection_ids(available_ids={"M001", "M002"})
        assert ids == ["M001", "M002"]
