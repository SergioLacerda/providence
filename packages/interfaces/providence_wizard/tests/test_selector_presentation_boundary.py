from __future__ import annotations

from pathlib import Path


def test_selector_presentation_source_is_externalized() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    template_dir = (
        repository_root
        / "packages/interfaces/providence_wizard/src/providence_wizard/templates/selector"
    )
    assert not template_dir.exists()
