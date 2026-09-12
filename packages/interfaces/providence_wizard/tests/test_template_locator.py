"""Tests for providence_wizard.orchestration.wizard.template_locator.TemplateLocator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_wizard.orchestration.wizard.template_locator import TemplateLocator


def _templates_root(tmp_path: Path) -> Path:
    root = (
        tmp_path
        / "packages"
        / "interfaces"
        / "providence_wizard"
        / "src"
        / "providence_wizard"
        / "templates"
    )
    root.mkdir(parents=True)
    return root


def test_resolve_language_dir_returns_none_when_template_root_missing(
    tmp_path: Path,
) -> None:
    locator = TemplateLocator(tmp_path)

    assert locator.resolve_language_dir("Python") is None
    assert locator.last_error is not None
    assert "Template root not found" in locator.last_error


def test_resolve_language_dir_returns_none_for_unsupported_language(
    tmp_path: Path,
) -> None:
    _templates_root(tmp_path)
    locator = TemplateLocator(tmp_path)

    assert locator.resolve_language_dir("Rust") is None
    assert locator.last_error == "Unsupported language template mapping: Rust"


def test_resolve_language_dir_returns_none_when_language_dir_missing(
    tmp_path: Path,
) -> None:
    templates_root = _templates_root(tmp_path)
    locator = TemplateLocator(tmp_path)

    assert locator.resolve_language_dir("Python") is None
    expected_dir = templates_root / "languages" / "python"
    assert locator.last_error == (
        f"Language template directory missing for Python: {expected_dir}"
    )


def test_resolve_language_dir_returns_path_when_present(tmp_path: Path) -> None:
    templates_root = _templates_root(tmp_path)
    language_dir = templates_root / "languages" / "python"
    language_dir.mkdir(parents=True)
    locator = TemplateLocator(tmp_path)

    assert locator.resolve_language_dir("Python") == language_dir


def test_resolve_language_dir_returns_none_when_templates_root_disappears(
    tmp_path: Path,
) -> None:
    templates_root = _templates_root(tmp_path)
    locator = TemplateLocator(tmp_path)

    with patch(
        "providence_wizard.orchestration.wizard.template_locator._find_templates_dir",
        side_effect=[templates_root, None],
    ):
        assert locator.resolve_language_dir("Python") is None


def test_validate_template_root_emits_error_message(tmp_path: Path) -> None:
    messages: list[str] = []
    locator = TemplateLocator(tmp_path, emitter=messages.append)

    assert locator.validate_template_root() is False
    assert any("Template root not found" in m for m in messages)
