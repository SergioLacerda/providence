"""Tests for the Scenario B custom-governance-file pre-flight validator."""

from __future__ import annotations

import json
from pathlib import Path

from providence_wizard.orchestration.custom_governance_loader import (
    load_custom_governance_file,
    validate_custom_governance_file,
)


def _write(path: Path, data: dict) -> Path:
    file_path = path / "custom-governance.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")
    return file_path


def test_missing_file_reports_error(tmp_path: Path) -> None:
    ok, errors = validate_custom_governance_file(tmp_path / "missing.json")
    assert ok is False
    assert "not found" in errors[0]


def test_invalid_json_reports_error(tmp_path: Path) -> None:
    file_path = tmp_path / "bad.json"
    file_path.write_text("{not valid json", encoding="utf-8")
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "not valid JSON" in errors[0]


def test_non_object_top_level_reports_error(tmp_path: Path) -> None:
    file_path = tmp_path / "list.json"
    file_path.write_text("[]", encoding="utf-8")
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "top-level JSON value must be an object" in errors[0]


def test_missing_items_array_reports_error(tmp_path: Path) -> None:
    file_path = _write(tmp_path, {"foo": "bar"})
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "items" in errors[0]


def test_empty_items_array_reports_error(tmp_path: Path) -> None:
    file_path = _write(tmp_path, {"items": []})
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "empty" in errors[0]


def test_valid_file_passes(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        {
            "items": [
                {"id": "M001", "type": "MANDATE", "title": "Clean Architecture"},
                {
                    "id": "G001",
                    "type": "GUIDELINE",
                    "title": "Style Guide",
                    "category": "style",
                },
            ]
        },
    )
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is True
    assert errors == []


def test_missing_required_keys_reports_error(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        {"items": [{"id": "M001", "type": "MANDATE"}]},  # missing title
    )
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "missing required key" in errors[0]
    assert "title" in errors[0]


def test_invalid_type_value_reports_error(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        {"items": [{"id": "M001", "type": "RULE", "title": "Something"}]},
    )
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "type must be one of" in errors[0]


def test_duplicate_id_reports_error(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        {
            "items": [
                {"id": "M001", "type": "MANDATE", "title": "First"},
                {"id": "M001", "type": "MANDATE", "title": "Duplicate"},
            ]
        },
    )
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "duplicate id" in errors[0]


def test_non_object_item_reports_error(tmp_path: Path) -> None:
    file_path = _write(tmp_path, {"items": ["not-an-object"]})
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert "expected an object" in errors[0]


def test_multiple_errors_all_reported(tmp_path: Path) -> None:
    file_path = _write(
        tmp_path,
        {
            "items": [
                {"id": "M001", "type": "MANDATE"},  # missing title
                {"id": "M002", "type": "BAD", "title": "X"},  # bad type
            ]
        },
    )
    ok, errors = validate_custom_governance_file(file_path)
    assert ok is False
    assert len(errors) == 2


class TestLoadCustomGovernanceFile:
    def test_valid_file_staged_to_governance_core_json(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "input"
        custom_dir.mkdir()
        custom_file = _write(
            custom_dir,
            {
                "items": [
                    {"id": "M001", "type": "MANDATE", "title": "Clean Architecture"}
                ]
            },
        )
        output_base = tmp_path / "output"

        ok, errors = load_custom_governance_file(custom_file, output_base)

        assert ok is True
        assert errors == []
        staged = output_base / ".providence" / "source" / "governance-core.json"
        assert staged.exists()
        staged_data = json.loads(staged.read_text(encoding="utf-8"))
        assert staged_data["items"][0]["id"] == "M001"

    def test_invalid_file_not_staged(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "input"
        custom_dir.mkdir()
        custom_file = _write(custom_dir, {"items": []})
        output_base = tmp_path / "output"

        ok, errors = load_custom_governance_file(custom_file, output_base)

        assert ok is False
        assert errors
        assert not (
            output_base / ".providence" / "source" / "governance-core.json"
        ).exists()

    def test_staged_file_converges_with_governance_loader(self, tmp_path: Path) -> None:
        """Proves Scenario A/B convergence: GovernanceLoader reads the staged
        custom file exactly as it would read a wizard-generated one  no
        Phase 4-6 code changes needed for Scenario B."""
        from providence_wizard.orchestration.phase4_governance_loader import (
            GovernanceLoader,
        )

        custom_dir = tmp_path / "input"
        custom_dir.mkdir()
        custom_file = _write(
            custom_dir,
            {
                "items": [
                    {"id": "M001", "type": "MANDATE", "title": "Clean Architecture"},
                    {
                        "id": "G001",
                        "type": "GUIDELINE",
                        "title": "Style Guide",
                        "category": "style",
                    },
                ]
            },
        )
        output_base = tmp_path / "output"

        ok, _errors = load_custom_governance_file(custom_file, output_base)
        assert ok is True

        loader = GovernanceLoader(
            governance_core_path=output_base
            / ".providence"
            / "source"
            / "governance-core.json",
            governance_client_path=output_base
            / ".providence"
            / "source"
            / "governance-client.json",
        )
        assert loader.load() is True
        assert len(loader.mandates) == 1
        assert loader.mandates[0]["id"] == "M001"
        assert "G001" in loader.guidelines
        assert "style" in loader.guidelines_by_category
