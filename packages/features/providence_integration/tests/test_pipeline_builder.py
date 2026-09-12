"""Tests for governance pipeline builder and related parsers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_integration.builders.governance.fingerprinter import (
    GovernanceFingerprinter,
)
from providence_integration.builders.governance.legacy_parser import LegacySpecParser
from providence_integration.builders.governance.markdown_parser import MarkdownParser
from providence_integration.builders.governance.pipeline_builder import PipelineBuilder

pytestmark = pytest.mark.unit


class TestGovernanceFingerprinter:
    """Tests for deterministic fingerprinting."""

    def test_empty_items_no_salt_returns_empty(self) -> None:
        """Empty items with no salt should return 'empty'."""
        result = GovernanceFingerprinter.generate([])
        assert result == "empty"

    def test_empty_items_with_salt_returns_hash(self) -> None:
        """Empty items with salt should return hash of salt."""
        result = GovernanceFingerprinter.generate([], salt="some_salt")
        assert result != "empty"
        assert len(result) == 64  # SHA-256 hex is 64 chars

    def test_deterministic_same_input_same_output(self) -> None:
        """Same input should always produce same output."""
        items = [{"id": "M001", "title": "Test"}]
        result1 = GovernanceFingerprinter.generate(items)
        result2 = GovernanceFingerprinter.generate(items)
        assert result1 == result2

    def test_different_items_different_fingerprint(self) -> None:
        """Different items should produce different fingerprints."""
        items1 = [{"id": "M001", "title": "Test1"}]
        items2 = [{"id": "M002", "title": "Test2"}]
        result1 = GovernanceFingerprinter.generate(items1)
        result2 = GovernanceFingerprinter.generate(items2)
        assert result1 != result2

    def test_salt_changes_fingerprint(self) -> None:
        """Salt parameter should change the fingerprint."""
        items = [{"id": "M001", "title": "Test"}]
        result1 = GovernanceFingerprinter.generate(items, salt="salt1")
        result2 = GovernanceFingerprinter.generate(items, salt="salt2")
        assert result1 != result2

    def test_fingerprint_is_valid_hex(self) -> None:
        """Fingerprint should be valid hex string."""
        items = [{"id": "M001", "title": "Test"}]
        result = GovernanceFingerprinter.generate(items)
        # Valid hex string should be decodable
        int(result, 16)  # This raises ValueError if not valid hex

    def test_fingerprint_is_full_64_char_digest_not_truncated(self) -> None:
        """SEC-08 regression: this domain's contract is a full, untruncated
        sha256 digest used for integrity decisions — unlike the codebase's
        other, shorter fingerprint domains (16-char cache/handshake keys,
        8-char query hashes). A silent truncation here would collapse this
        into a different, weaker domain without anyone noticing.
        `.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md` SEC-08.
        """
        result = GovernanceFingerprinter.generate([{"id": "M001", "title": "Test"}])
        assert len(result) == 64


class TestMarkdownParser:
    """Tests for Markdown content parsing."""

    def test_extract_summary_minimal_found(self) -> None:
        """Should extract title from heading."""
        content = "# M001: Test Mandate"
        result = MarkdownParser.extract_summary_minimal(content, "M001")
        assert result == "Test Mandate"

    def test_extract_summary_minimal_with_heading_level_2(self) -> None:
        """Should extract from level 2 heading."""
        content = "## M001 Test Mandate"
        result = MarkdownParser.extract_summary_minimal(content, "M001")
        assert result == "Test Mandate"

    def test_extract_summary_minimal_not_found(self) -> None:
        """Should return None when heading not found."""
        content = "# M002: Test"
        result = MarkdownParser.extract_summary_minimal(content, "M001")
        assert result is None

    def test_extract_summary_minimal_rejects_dash_prefix(self) -> None:
        """Should reject titles starting with dash."""
        content = "# M001: - Status"
        result = MarkdownParser.extract_summary_minimal(content, "M001")
        assert result is None

    def test_extract_summary_minimal_rejects_status_keywords(self) -> None:
        """Should reject single-word status keywords."""
        for keyword in ("accepted", "rejected", "pending", "status"):
            content = f"# M001: {keyword}"
            result = MarkdownParser.extract_summary_minimal(content, "M001")
            assert result is None

    def test_extract_summary_runtime_found(self) -> None:
        """Should extract first paragraph after heading."""
        content = """# M001: Title
First paragraph text here.
More content."""
        result = MarkdownParser.extract_summary_runtime(content, "M001")
        assert result == "First paragraph text here."

    def test_extract_summary_runtime_not_found(self) -> None:
        """Should return None when no content after heading."""
        content = "# M001: Title"
        result = MarkdownParser.extract_summary_runtime(content, "M001")
        assert result is None

    def test_extract_summary_runtime_truncates_at_200_chars(self) -> None:
        """Should truncate runtime summary at 200 chars."""
        long_text = "x" * 300
        content = f"# M001: Title\n{long_text}"
        result = MarkdownParser.extract_summary_runtime(content, "M001")
        assert result.endswith("...")
        assert len(result) == 200

    def test_extract_summary_runtime_with_multiple_paragraphs(self) -> None:
        """Should extract only first paragraph."""
        content = """# M001: Title
First paragraph.

Second paragraph."""
        result = MarkdownParser.extract_summary_runtime(content, "M001")
        assert result == "First paragraph."


class TestLegacySpecParser:
    """Tests for legacy DSL format parsing."""

    def test_parse_mandates_block_format(self) -> None:
        """Should parse block format: `mandate M001 { ... }`."""
        content = "mandate M001 { ... }\nmandate M002 { ... }"
        result = LegacySpecParser.parse_mandates(content)
        assert len(result) == 2
        assert result[0]["id"] == "M001"
        assert result[0]["type"] == "MANDATE"
        assert result[0]["criticality"] == "high"

    def test_parse_mandates_compact_format(self) -> None:
        """Should parse compact format: `M001: Title`."""
        content = "M001: First\nM002: Second"
        result = LegacySpecParser.parse_mandates(content)
        assert len(result) == 2
        assert result[0]["id"] == "M001"

    def test_parse_mandates_bracket_format(self) -> None:
        """Should parse bracket fallback: `- [M001] ...`."""
        content = "- [M001] Something\n- [M002] Other"
        result = LegacySpecParser.parse_mandates(content)
        assert len(result) == 2
        assert result[0]["id"] == "M001"

    def test_parse_mandates_empty_content(self) -> None:
        """Should return empty list for empty content."""
        result = LegacySpecParser.parse_mandates("")
        assert result == []

    def test_parse_mandates_deduplicates(self) -> None:
        """Should deduplicate mandate IDs."""
        content = "mandate M001 { ... }\n[M001] again"
        result = LegacySpecParser.parse_mandates(content)
        assert len(result) == 1

    def test_parse_guidelines_blocks_valid(self) -> None:
        """Should parse `guideline Gxxx { ... }` blocks."""
        content = 'guideline G001 { title: "Test" }'
        result = LegacySpecParser.parse_guidelines_blocks(content)
        assert len(result) == 1
        assert result[0]["id"] == "G001"
        assert result[0]["title"] == "Test"

    def test_parse_guidelines_blocks_with_description(self) -> None:
        """Should extract description field from block."""
        content = 'guideline G001 { description: "Test description" }'
        result = LegacySpecParser.parse_guidelines_blocks(content)
        assert result[0]["description"] == "Test description"

    def test_parse_guidelines_blocks_empty(self) -> None:
        """Should return empty list for no blocks."""
        result = LegacySpecParser.parse_guidelines_blocks("")
        assert result == []

    def test_parse_guidelines_blocks_sorted(self) -> None:
        """Should return blocks sorted by ID."""
        content = "guideline G002 { }\nguideline G001 { }"
        result = LegacySpecParser.parse_guidelines_blocks(content)
        assert result[0]["id"] == "G001"
        assert result[1]["id"] == "G002"

    def test_parse_guidelines_blocks_with_all_fields(self) -> None:
        """Should include all optional fields when present."""
        content = """guideline G001 {
            title: "Test"
            description: "Desc"
            summary_minimal: "Min"
            summary_runtime: "Runtime"
        }"""
        result = LegacySpecParser.parse_guidelines_blocks(content)
        assert result[0]["summary_minimal"] == "Min"
        assert result[0]["summary_runtime"] == "Runtime"

    def test_extract_block_field_double_quoted(self) -> None:
        """Should extract double-quoted values."""
        block = 'title: "Test Value"'
        result = LegacySpecParser._extract_block_field(block, "title")
        assert result == "Test Value"

    def test_extract_block_field_single_quoted(self) -> None:
        """Should extract single-quoted values."""
        block = "title: 'Test Value'"
        result = LegacySpecParser._extract_block_field(block, "title")
        assert result == "Test Value"

    def test_extract_block_field_bare_value(self) -> None:
        """Should extract bare values."""
        block = "title: TestValue"
        result = LegacySpecParser._extract_block_field(block, "title")
        assert result == "TestValue"

    def test_extract_block_field_missing(self) -> None:
        """Should return None for missing field."""
        block = "other: value"
        result = LegacySpecParser._extract_block_field(block, "title")
        assert result is None

    def test_extract_block_field_case_insensitive(self) -> None:
        """Should extract field names case-insensitively."""
        block = 'Title: "Value"'
        result = LegacySpecParser._extract_block_field(block, "title")
        assert result == "Value"


class TestPipelineBuilderParsedItems:
    """Tests for PipelineBuilder with pre-parsed items (fast path)."""

    def test_build_with_parsed_mandates(self, tmp_path: Path) -> None:
        """Should build from pre-parsed mandates."""
        builder = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [
                    {"id": "M001", "title": "First"},
                    {"id": "M002", "title": "Second"},
                ],
                "guidelines": [],
            },
        )
        result = builder.build()

        assert len(result["core_items"]) == 2
        assert result["core_items"][0]["id"] == "M001"
        assert result["core_items"][0]["type"] == "MANDATE"
        assert result["core_items"][0]["criticality"] == "high"

    def test_build_with_parsed_guidelines(self, tmp_path: Path) -> None:
        """Should build from pre-parsed guidelines."""
        builder = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [],
                "guidelines": [
                    {"id": "G001", "title": "Guideline"},
                ],
            },
        )
        result = builder.build()

        assert len(result["client_items"]) == 1
        assert result["client_items"][0]["id"] == "G001"
        assert result["client_items"][0]["type"] == "GUIDELINE"
        assert result["client_items"][0]["criticality"] == "medium"

    def test_build_empty_parsed_items(self, tmp_path: Path) -> None:
        """Should handle empty parsed items."""
        builder = PipelineBuilder(str(tmp_path), parsed_items={})
        # Should not raise and should try to read from filesystem
        with pytest.raises(FileNotFoundError):
            builder.build()

    def test_build_core_fingerprint_stable(self, tmp_path: Path) -> None:
        """Core fingerprint should be stable across rebuilds."""
        builder1 = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [{"id": "M001", "title": "Test"}],
                "guidelines": [],
            },
        )
        result1 = builder1.build()
        fp1 = result1["governance_core"]["fingerprint"]

        builder2 = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [{"id": "M001", "title": "Test"}],
                "guidelines": [],
            },
        )
        result2 = builder2.build()
        fp2 = result2["governance_core"]["fingerprint"]

        assert fp1 == fp2

    def test_build_sorted_by_id(self, tmp_path: Path) -> None:
        """Items should be sorted by ID before fingerprinting."""
        builder = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [
                    {"id": "M002", "title": "Second"},
                    {"id": "M001", "title": "First"},
                ],
                "guidelines": [],
            },
        )
        result = builder.build()
        assert result["core_items"][0]["id"] == "M001"
        assert result["core_items"][1]["id"] == "M002"


class TestPipelineBuilderFilesystem:
    """Tests for PipelineBuilder reading from filesystem."""

    def test_build_from_v3_markdown(self, tmp_path: Path) -> None:
        """Should parse v3.0 Markdown format."""
        mandates_dir = tmp_path / "mandates"
        mandates_dir.mkdir()
        mandate_file = mandates_dir / "mandates.md"
        mandate_file.write_text(
            "# M001: Test Mandate\nFirst paragraph here.", encoding="utf-8"
        )

        guidelines_file = tmp_path / "guidelines.md"
        guidelines_file.write_text(
            "# G001: Test Guideline\nGuideline text.", encoding="utf-8"
        )

        builder = PipelineBuilder(str(tmp_path))
        result = builder.build()

        assert len(result["core_items"]) == 1
        assert result["core_items"][0]["id"] == "M001"
        assert result["core_items"][0]["title"] == "Test Mandate"
        assert len(result["client_items"]) == 1

    def test_build_prefers_v3_mandates_over_legacy_mandate_md(
        self, tmp_path: Path
    ) -> None:
        """Should not let a stale legacy mandate.md shadow v3.0 source."""
        (tmp_path / "mandate.md").write_text(
            "# M001: Legacy Title\nLegacy paragraph.", encoding="utf-8"
        )
        mandates_dir = tmp_path / "mandates"
        mandates_dir.mkdir()
        (mandates_dir / "mandates.md").write_text(
            "# M001: Canonical Title\nCanonical paragraph.", encoding="utf-8"
        )

        builder = PipelineBuilder(str(tmp_path))
        result = builder.build()

        assert result["core_items"][0]["title"] == "Canonical Title"

    def test_build_fails_fast_on_zero_parsed_mandates(self, tmp_path: Path) -> None:
        """A mandate source that parses to zero items must raise, not emit empty artifacts."""
        # Simulates a git symlink checked out as a plain text stub on Windows:
        # the file exists but contains only the link target path.
        (tmp_path / "mandate.spec").write_text(
            "../../_spec/mandate.spec", encoding="utf-8"
        )
        (tmp_path / "guidelines.dsl").write_text(
            'guideline G001 { title: "G" }', encoding="utf-8"
        )

        builder = PipelineBuilder(str(tmp_path))
        with pytest.raises(ValueError, match="Parsed 0 mandates"):
            builder.build()

    def test_build_fails_fast_on_markdown_without_mandate_headings(
        self, tmp_path: Path
    ) -> None:
        """A mandate.md with no M-id headings must raise with the source path."""
        (tmp_path / "mandate.md").write_text(
            "# Overview\nNo mandate headings here.", encoding="utf-8"
        )

        builder = PipelineBuilder(str(tmp_path))
        with pytest.raises(ValueError, match="Parsed 0 mandates"):
            builder.build()

    def test_generate_spec_file_preserves_m017_paragraph_fields(
        self, tmp_path: Path
    ) -> None:
        """Should preserve wrapped paragraph text when generating mandates.json."""
        repo_root = Path(__file__).resolve().parents[4]
        canonical_mandates_dir = (
            repo_root / "docs" / "spec" / "canonical" / "core" / "mandates"
        )
        output_path = tmp_path / "mandates.json"

        result = PipelineBuilder.generate_spec_file(canonical_mandates_dir, output_path)

        assert result["mandates_written"] > 0
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        m017 = next(item for item in payload["mandates"] if item["id"] == "M017")
        assert (
            m017["summary_runtime"]
            == "Ensure that analysis plugins respect SDD-injected base_path, execution_provider, and approval_gate."
        )
        assert (
            m017["rationale"]
            == "Plugins extend SDD with external orchestration capabilities. Without governance over their write scope and execution authority, a plugin could silently corrupt the workspace or bypass approval controls. M017 ensures the plugin contract is enforceable and auditable."
        )
        assert "---" not in m017["rationale"]

    def test_save_outputs_creates_files(self, tmp_path: Path) -> None:
        """Should create JSON output files."""
        builder = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [{"id": "M001", "title": "Test"}],
                "guidelines": [],
            },
        )
        output_dir = tmp_path / "output"
        builder.save_outputs(str(output_dir))

        assert output_dir.exists()
        assert (output_dir / "governance-core.json").exists()
        assert (output_dir / "governance-client.json").exists()

    def test_save_outputs_returns_paths(self, tmp_path: Path) -> None:
        """Should return paths to created files."""
        builder = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [{"id": "M001", "title": "Test"}],
                "guidelines": [],
            },
        )
        output_dir = tmp_path / "output"
        result = builder.save_outputs(str(output_dir))

        assert "governance_core" in result
        assert "governance_client" in result
        assert "core_fingerprint" in result
        assert "client_fingerprint" in result
        assert "governance-core.json" in result["governance_core"]

    def test_save_outputs_calls_build(self, tmp_path: Path) -> None:
        """Should call build() if not yet built."""
        builder = PipelineBuilder(
            str(tmp_path),
            parsed_items={
                "mandates": [{"id": "M001", "title": "Test"}],
                "guidelines": [],
            },
        )
        assert builder.result == {}  # Not built yet

        output_dir = tmp_path / "output"
        builder.save_outputs(str(output_dir))

        assert builder.result != {}  # Now built
