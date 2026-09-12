"""Tests for MandateRenderer."""

from pathlib import Path

from providence_core.utils.text_io import read_text_utf8
from providence_wizard.orchestration.wizard.mandate_renderer import MandateRenderer
from providence_wizard.orchestration.wizard.models import Mandate


def _make_mandates() -> list[Mandate]:
    return [
        Mandate(
            id="M001",
            type="MUST",
            title="Review all code",
            description="Peer review required",
            category="quality",
            rationale="",
        ),
        Mandate(
            id="M002",
            type="SHOULD",
            title="Write tests",
            description="Unit tests required",
            category="testing",
            rationale="",
        ),
        Mandate(
            id="M003",
            type="MUST",
            title="Security scan",
            description="Run SAST on every PR",
            category="quality",
            rationale="",
        ),
    ]


class TestMandateRenderer:
    def test_creates_per_category_files(self, tmp_path: Path) -> None:
        MandateRenderer(tmp_path).render(_make_mandates())
        assert (tmp_path / "mandates-quality.md").exists()
        assert (tmp_path / "mandates-testing.md").exists()

    def test_file_contains_mandate_ids(self, tmp_path: Path) -> None:
        MandateRenderer(tmp_path).render(_make_mandates())
        content = read_text_utf8(tmp_path / "mandates-quality.md")
        assert "M001" in content
        assert "M003" in content
        assert "M002" not in content

    def test_empty_list_returns_true_no_files(self, tmp_path: Path) -> None:
        result = MandateRenderer(tmp_path).render([])
        assert result is True
        assert list(tmp_path.glob("mandates-*.md")) == []

    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        result = MandateRenderer(tmp_path).render(_make_mandates())
        assert result is True
