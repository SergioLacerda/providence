"""Tests for reading operator-facing wizard state."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from providence_wizard.application.operator_state import read_enforcement_label


def test_read_enforcement_label_returns_expected_label(tmp_path: Path) -> None:
    config_path = tmp_path / "wizard-config.json"
    config_path.write_text(
        json.dumps({"enforcement_mode": "strict_mode"}), encoding="utf-8"
    )
    assert read_enforcement_label(config_path) == "Bloquear"


def test_read_enforcement_label_returns_default_on_corrupt_json(tmp_path: Path) -> None:
    config_path = tmp_path / "wizard-config.json"
    config_path.write_text("{invalid", encoding="utf-8")
    assert read_enforcement_label(config_path) == "Alertas"


def test_read_enforcement_label_returns_default_on_permission_error(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "wizard-config.json"
    config_path.write_text(
        json.dumps({"enforcement_mode": "strict_mode"}), encoding="utf-8"
    )
    with patch("builtins.open", side_effect=PermissionError("Access denied")):
        assert read_enforcement_label(config_path) == "Alertas"
