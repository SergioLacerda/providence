"""Tests for MandateSpecParser and GuidelinesDslParser."""

from providence_wizard.orchestration.wizard.spec_parser import (
    GuidelinesDslParser,
    MandateSpecParser,
)

MANDATE_SPEC = """
mandate M001 {
    type: "MUST"
    title: "All code must be reviewed"
    description: "Peer review is required for all changes"
    category: "quality"
    rationale: "Reduces defects"
}

mandate M002 {
    type: "SHOULD"
    title: "Write tests"
    description: "Unit tests required for new code"
    category: "testing"
    rationale: "Ensures correctness"
}
"""

GUIDELINES_DSL = """
guideline G001 {
    type: "RECOMMENDATION"
    title: "Use descriptive names"
    description: "Variables should be descriptive"
    category: "style"
}

guideline G002 {
    type: "BEST_PRACTICE"
    title: "Keep functions small"
    description: "Functions under 30 lines"
    category: "design"
}
"""

MANDATE_MARKDOWN = """
# M001: All code must be reviewed

Some description here.

## M002: Write tests

More content.
"""

GUIDELINES_MARKDOWN = """
## G001: Use descriptive names

## G002: Keep functions small
"""


class TestMandateSpecParser:
    def test_parse_blocks_returns_mandates(self) -> None:
        parser = MandateSpecParser()
        mandates = parser.parse(MANDATE_SPEC)
        assert len(mandates) == 2

    def test_parse_blocks_fields(self) -> None:
        parser = MandateSpecParser()
        mandates = parser.parse(MANDATE_SPEC)
        m = mandates[0]
        assert m.id == "M001"
        assert m.type == "MUST"
        assert m.title == "All code must be reviewed"
        assert m.category == "quality"
        assert m.rationale == "Reduces defects"

    def test_parse_markdown_returns_mandates(self) -> None:
        parser = MandateSpecParser()
        mandates = parser.parse(MANDATE_MARKDOWN, is_markdown=True)
        assert len(mandates) == 2

    def test_parse_markdown_fields(self) -> None:
        parser = MandateSpecParser()
        mandates = parser.parse(MANDATE_MARKDOWN, is_markdown=True)
        assert mandates[0].id == "M001"
        assert mandates[1].id == "M002"

    def test_parse_empty_returns_empty(self) -> None:
        parser = MandateSpecParser()
        assert parser.parse("") == []

    def test_parse_bullet_list_fallback(self) -> None:
        bullets = "- [M001] **Mandate one**\n- [M002] **Mandate two**"
        parser = MandateSpecParser()
        mandates = parser.parse(bullets)
        assert len(mandates) == 2
        assert mandates[0].id == "M001"


class TestGuidelinesDslParser:
    def test_parse_blocks_returns_guidelines(self) -> None:
        parser = GuidelinesDslParser()
        guidelines = parser.parse(GUIDELINES_DSL)
        assert len(guidelines) == 2

    def test_parse_blocks_fields(self) -> None:
        parser = GuidelinesDslParser()
        guidelines = parser.parse(GUIDELINES_DSL)
        g = guidelines[0]
        assert g.id == "G001"
        assert g.title == "Use descriptive names"
        assert g.category == "style"

    def test_parse_markdown_returns_guidelines(self) -> None:
        parser = GuidelinesDslParser()
        guidelines = parser.parse(GUIDELINES_MARKDOWN, is_markdown=True)
        assert len(guidelines) == 2
        assert guidelines[0].id == "G001"
        assert guidelines[1].id == "G002"

    def test_parse_empty_returns_empty(self) -> None:
        parser = GuidelinesDslParser()
        assert parser.parse("") == []
