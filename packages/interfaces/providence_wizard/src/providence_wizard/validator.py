"""
SDD v3.0 Wizard - Phase 1: Validate SOURCE (core/)

Validates that source DSL files have correct syntax and structure
"""

import re
from typing import Any

from ._mandate_spec_validation import (
    MANDATE_BLOCK_PATTERN,
    MANDATE_PATTERN,
    extract_block_field,
    parse_block_format,
    validate_dsl_syntax,
    validate_mandate_spec,
)

GUIDELINE_PATTERN = r"guideline\s+(G\d+)\s*\{"


class SourceValidator:
    """Validate SOURCE files (mandate.spec, guidelines.dsl)"""

    MANDATE_PATTERN = MANDATE_PATTERN
    MANDATE_BLOCK_PATTERN = MANDATE_BLOCK_PATTERN
    GUIDELINE_PATTERN = GUIDELINE_PATTERN

    _extract_block_field = staticmethod(extract_block_field)
    _parse_block_format = staticmethod(parse_block_format)
    validate_dsl_syntax = staticmethod(validate_dsl_syntax)
    validate_mandate_spec = staticmethod(validate_mandate_spec)

    @staticmethod
    def validate_guidelines_dsl(guidelines_text: str) -> dict[str, Any]:
        """Validate guidelines.dsl structure"""
        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {
                "guideline_count": 0,
                "guideline_ids": [],
                "lines": len(guidelines_text.split("\n")),
                "bytes": len(guidelines_text.encode("utf-8")),
            },
        }

        # Syntax validation
        syntax_errors = SourceValidator.validate_dsl_syntax(
            guidelines_text, "guidelines"
        )
        if syntax_errors:
            result["valid"] = False
            result["errors"].extend(syntax_errors)
            return result

        # Find all guidelines
        guidelines = re.findall(r"guideline\s+(G\d+)", guidelines_text)
        result["statistics"]["guideline_count"] = len(guidelines)
        result["statistics"]["guideline_ids"] = list(dict.fromkeys(guidelines))

        # Check for duplicates
        if len(guidelines) != len(set(guidelines)):
            duplicates = [g for g in set(guidelines) if guidelines.count(g) > 1]
            result["errors"].append(f"Duplicate guideline IDs: {duplicates}")
            result["valid"] = False

        # Check for empty guidelines
        empty_guidelines = re.findall(r"guideline\s+G\d+\s*\{\s*\}", guidelines_text)
        if empty_guidelines:
            result["errors"].append(f"Empty guidelines found: {len(empty_guidelines)}")
            result["valid"] = False

        # Warning if no guidelines found (but file exists, might be template)
        if not guidelines:
            result["warnings"].append("No guidelines found in file")

        return result


def validate_source_files(
    mandate_text: str, guidelines_text: str
) -> tuple[bool, dict[str, Any]]:
    """Validate both source files together."""
    mandate_result = SourceValidator.validate_mandate_spec(mandate_text)
    guidelines_result = SourceValidator.validate_guidelines_dsl(guidelines_text)
    combined: dict[str, Any] = {
        "valid": mandate_result["valid"] and guidelines_result["valid"],
        "mandate": mandate_result,
        "guidelines": guidelines_result,
        "errors": mandate_result["errors"] + guidelines_result["errors"],
        "warnings": mandate_result["warnings"] + guidelines_result["warnings"],
    }
    return (combined["valid"], combined)


# Backwards-compat: keep accessible as class method too
SourceValidator.validate_source_files = staticmethod(validate_source_files)  # type: ignore[attr-defined]
