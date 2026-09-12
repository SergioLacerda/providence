from __future__ import annotations

from pathlib import Path

import pytest

from providence_wizard.orchestration.wizard.selector_bridge import (
    SelectorBridgeError,
    load_selector_selection,
    validate_selector_selection,
)


def test_validate_selector_selection_returns_resolved_ids() -> None:
    payload = {
        "version": "1.0",
        "selected_ids": ["M001"],
        "resolved_ids": ["M001", "M002"],
    }
    assert validate_selector_selection(payload) == ["M001", "M002"]


def test_validate_selector_selection_rejects_unknown_ids() -> None:
    payload = {"version": "1.0", "selected_ids": ["M001"], "resolved_ids": ["M999"]}
    with pytest.raises(SelectorBridgeError, match="Unknown selector IDs: M999"):
        validate_selector_selection(payload, available_ids={"M001", "M002"})


def test_load_selector_selection_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "selector-selection.json"
    path.write_text("{bad json}", encoding="utf-8")
    with pytest.raises(SelectorBridgeError, match="not valid JSON"):
        load_selector_selection(path)
