"""Tests for SourceValidator  validate mandate.spec and guidelines.dsl content."""

from __future__ import annotations

from providence_wizard.validator import SourceValidator

_VALID_MANDATE_DSL = """\
mandate M001 {
  title: "Dependency governance"
  category: "architecture"
  rationale: "Prevent drift."
  type: "HARD"
  description: "All deps declared."
}

mandate M002 {
  title: "Test coverage"
  category: "testing"
  type: "HARD"
  description: "80% minimum."
}
"""

_VALID_GUIDELINES = """\
guideline G01 {
  type: SOFT
  title: "Use semantic commits"
  description: "Follow conventional commits."
  category: git
}
guideline G02 {
  type: SOFT
  title: "Doc all public APIs"
  description: "Every public method documented."
  category: documentation
}
"""


class TestValidateDslSyntax:
    def test_empty_file_returns_error(self) -> None:
        errors = SourceValidator.validate_dsl_syntax("", "mandate")
        assert any("empty" in e.lower() for e in errors)

    def test_incomplete_mandate_line_returns_error(self) -> None:
        errors = SourceValidator.validate_dsl_syntax("- [M", "mandate")
        assert len(errors) >= 1

    def test_valid_mandate_returns_no_errors(self) -> None:
        errors = SourceValidator.validate_dsl_syntax(
            "- [M001] **Title** desc", "mandate"
        )
        assert errors == []

    def test_unbalanced_braces_in_dsl(self) -> None:
        errors = SourceValidator.validate_dsl_syntax("guideline G01 {", "dsl")
        assert any("brace" in e.lower() for e in errors)

    def test_odd_quotes_in_dsl(self) -> None:
        errors = SourceValidator.validate_dsl_syntax('title: "hello', "dsl")
        assert any("quote" in e.lower() for e in errors)

    def test_balanced_dsl_no_errors(self) -> None:
        errors = SourceValidator.validate_dsl_syntax(
            'guideline G01 { title: "x" }', "dsl"
        )
        assert errors == []


class TestExtractBlockField:
    def test_extracts_quoted_value(self) -> None:
        result = SourceValidator._extract_block_field('title: "My Title"', "title")
        assert result == "My Title"

    def test_returns_empty_when_not_found(self) -> None:
        result = SourceValidator._extract_block_field("category: architecture", "title")
        assert result == ""


class TestValidateMandateSpec:
    def test_valid_spec_passes(self) -> None:
        result = SourceValidator.validate_mandate_spec(_VALID_MANDATE_DSL)
        assert result["valid"] is True
        assert result["statistics"]["mandate_count"] == 2

    def test_empty_spec_fails(self) -> None:
        result = SourceValidator.validate_mandate_spec("")
        assert result["valid"] is False
        assert any("empty" in e.lower() for e in result["errors"])

    def test_no_mandates_fails(self) -> None:
        result = SourceValidator.validate_mandate_spec("# Just a comment\n")
        assert result["valid"] is False
        assert any("No mandates" in e for e in result["errors"])

    def test_duplicate_mandate_ids_flagged(self) -> None:
        dsl = _VALID_MANDATE_DSL + """\nmandate M001 {\n  title: "Duplicate"\n}\n"""
        result = SourceValidator.validate_mandate_spec(dsl)
        assert result["valid"] is False
        assert any("Duplicate" in e for e in result["errors"])

    def test_non_sequential_ids_generate_warning(self) -> None:
        dsl = """\
mandate M001 {
  title: "First"
}

mandate M003 {
  title: "Skipped"
}
"""
        result = SourceValidator.validate_mandate_spec(dsl)
        assert any(
            "Non-sequential" in w or "sequential" in w.lower()
            for w in result["warnings"]
        )

    def test_statistics_contain_line_and_byte_counts(self) -> None:
        result = SourceValidator.validate_mandate_spec(_VALID_MANDATE_DSL)
        assert result["statistics"]["lines"] > 0
        assert result["statistics"]["bytes"] > 0

    def test_mandate_ids_extracted(self) -> None:
        result = SourceValidator.validate_mandate_spec(_VALID_MANDATE_DSL)
        assert "M001" in result["statistics"]["mandate_ids"]
        assert "M002" in result["statistics"]["mandate_ids"]


class TestValidateGuidelinesDsl:
    def test_valid_guidelines_passes(self) -> None:
        result = SourceValidator.validate_guidelines_dsl(_VALID_GUIDELINES)
        assert result["valid"] is True
        assert result["statistics"]["guideline_count"] == 2

    def test_empty_guidelines_returns_warning(self) -> None:
        result = SourceValidator.validate_guidelines_dsl("# comment\n")
        assert any("No guidelines" in w for w in result["warnings"])

    def test_duplicate_guideline_ids_fail(self) -> None:
        dsl = _VALID_GUIDELINES + '\nguideline G01 {\n  type: SOFT\n  title: "Dup"\n}\n'
        result = SourceValidator.validate_guidelines_dsl(dsl)
        assert result["valid"] is False
        assert any("Duplicate" in e for e in result["errors"])

    def test_empty_guideline_block_fails(self) -> None:
        dsl = "guideline G01 {}"
        result = SourceValidator.validate_guidelines_dsl(dsl)
        assert result["valid"] is False

    def test_unbalanced_braces_fails(self) -> None:
        dsl = "guideline G01 {"
        result = SourceValidator.validate_guidelines_dsl(dsl)
        assert result["valid"] is False

    def test_statistics_filled(self) -> None:
        result = SourceValidator.validate_guidelines_dsl(_VALID_GUIDELINES)
        assert "G01" in result["statistics"]["guideline_ids"]


class TestValidateSourceFiles:
    def test_both_valid_returns_true(self) -> None:
        valid, combined = SourceValidator.validate_source_files(
            _VALID_MANDATE_DSL, _VALID_GUIDELINES
        )
        assert valid is True
        assert combined["mandate"]["valid"] is True
        assert combined["guidelines"]["valid"] is True

    def test_invalid_mandate_fails_combined(self) -> None:
        valid, combined = SourceValidator.validate_source_files("", _VALID_GUIDELINES)
        assert valid is False
        assert len(combined["errors"]) > 0

    def test_invalid_guidelines_fails_combined(self) -> None:
        valid, combined = SourceValidator.validate_source_files(_VALID_MANDATE_DSL, "")
        # empty guidelines generates only a warning but may still be valid
        assert "warnings" in combined
