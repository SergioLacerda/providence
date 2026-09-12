"""Tests for GuidelineRenderer."""

from pathlib import Path

from providence_core.utils.text_io import read_text_utf8
from providence_wizard.orchestration.wizard.guideline_renderer import GuidelineRenderer
from providence_wizard.orchestration.wizard.models import Guideline


def _make_guidelines() -> list[Guideline]:
    return [
        Guideline(
            id="G001",
            type="RECOMMENDATION",
            title="Descriptive names",
            description="Use descriptive variable names",
            category="style",
        ),
        Guideline(
            id="G002",
            type="BEST_PRACTICE",
            title="Small functions",
            description="Keep functions under 30 lines",
            category="design",
        ),
        Guideline(
            id="G003",
            type="RECOMMENDATION",
            title="DRY code",
            description="Don't repeat yourself",
            category="style",
        ),
    ]


class TestGuidelineRenderer:
    def test_creates_per_category_files(self, tmp_path: Path) -> None:
        GuidelineRenderer(tmp_path).render(_make_guidelines())
        assert (tmp_path / "guidelines-style.md").exists()
        assert (tmp_path / "guidelines-design.md").exists()

    def test_file_contains_guideline_ids(self, tmp_path: Path) -> None:
        GuidelineRenderer(tmp_path).render(_make_guidelines())
        content = read_text_utf8(tmp_path / "guidelines-style.md")
        assert "G001" in content
        assert "G003" in content
        assert "G002" not in content

    def test_empty_list_returns_true_no_files(self, tmp_path: Path) -> None:
        result = GuidelineRenderer(tmp_path).render([])
        assert result is True
        assert list(tmp_path.glob("guidelines-*.md")) == []

    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        result = GuidelineRenderer(tmp_path).render(_make_guidelines())
        assert result is True
