"""Unit tests for providence_integration.builders.governance.compile.GovernanceCompiler."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from tests.helpers.text_io import read_text_utf8

pytestmark = pytest.mark.unit


def _make_compiler(tmp_path: Path) -> Any:
    from providence_integration.builders.governance.compile import GovernanceCompiler

    return GovernanceCompiler(str(tmp_path / "core"))


def _write_mandate_md(
    dir: Path,
    item_id: str = "M001",
    title: str = "Test Mandate",
    criticality: str = "OBRIGATÓRIO",
    customizable: bool = False,
) -> None:
    dir.mkdir(parents=True, exist_ok=True)
    content = f"""---
id: {item_id}
title: "{title}"
type: MANDATE
criticality: {criticality}
customizable: {str(customizable).lower()}
optional: false
category: governance
---

# {title}

Description of {item_id}.
"""
    (dir / f"{item_id.lower()}.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# calculate_fingerprint
# ---------------------------------------------------------------------------


class TestCalculateFingerprint:
    def test_returns_64_char_hex(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        fp = c.calculate_fingerprint({"items": [], "version": "3.0"})
        assert len(fp) == 64
        assert all(ch in "0123456789abcdef" for ch in fp)

    def test_excludes_fingerprint_key_from_hash(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        d1 = {"items": [], "version": "3.0"}
        d2 = {"items": [], "version": "3.0", "fingerprint": "previous_fp"}
        assert c.calculate_fingerprint(d1) == c.calculate_fingerprint(d2)

    def test_different_data_gives_different_fingerprint(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        fp1 = c.calculate_fingerprint({"items": [], "version": "3.0"})
        fp2 = c.calculate_fingerprint({"items": [{"id": "M001"}], "version": "3.0"})
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# load_selections
# ---------------------------------------------------------------------------


class TestLoadSelections:
    def test_no_selections_file_is_noop(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        c.load_selections(str(tmp_path / "nonexistent.json"))
        assert c.selections == {}

    def test_loads_selections_from_file(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        selections_file = tmp_path / "selections.json"
        selections_data = {
            "selections": {
                "M001": {"choice": "CORE"},
                "G001": {"choice": "CLIENT"},
            }
        }
        selections_file.write_text(json.dumps(selections_data), encoding="utf-8")
        c.load_selections(str(selections_file))
        assert c.selections["M001"]["choice"] == "CORE"
        assert c.selections["G001"]["choice"] == "CLIENT"


# ---------------------------------------------------------------------------
# extract_markdown_items
# ---------------------------------------------------------------------------


class TestExtractMarkdownItems:
    def test_empty_source_dir_extracts_nothing(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        c.extract_markdown_items()
        assert c.all_items == []

    def test_extracts_mandate_from_markdown(self, tmp_path: Path) -> None:
        source_mandates = tmp_path / "core" / "source" / "mandates"
        _write_mandate_md(source_mandates, "M001", "Test Mandate")
        c = _make_compiler(tmp_path)
        c.extract_markdown_items()
        assert len(c.all_items) == 1
        assert c.all_items[0]["id"] == "M001"

    def test_skips_file_without_yaml_frontmatter(self, tmp_path: Path) -> None:
        source_mandates = tmp_path / "core" / "source" / "mandates"
        source_mandates.mkdir(parents=True)
        (source_mandates / "bad.md").write_text("# No YAML here\n", encoding="utf-8")
        c = _make_compiler(tmp_path)
        c.extract_markdown_items()
        assert len(c.all_items) == 0


# ---------------------------------------------------------------------------
# _parse_markdown_item
# ---------------------------------------------------------------------------


class TestParseMarkdownItem:
    def test_parses_valid_item(self, tmp_path: Path) -> None:
        source_mandates = tmp_path / "core" / "source" / "mandates"
        _write_mandate_md(source_mandates, "M001")
        md_file = source_mandates / "m001.md"
        c = _make_compiler(tmp_path)
        result = c._parse_markdown_item(md_file, "MANDATE")
        assert result is not None
        assert result["id"] == "M001"
        assert result["type"] == "MANDATE"

    def test_returns_none_when_no_yaml(self, tmp_path: Path) -> None:
        md_file = tmp_path / "bad.md"
        md_file.write_text("# No YAML here", encoding="utf-8")
        c = _make_compiler(tmp_path)
        result = c._parse_markdown_item(md_file, "MANDATE")
        assert result is None

    def test_returns_none_when_yaml_invalid(self, tmp_path: Path) -> None:
        md_file = tmp_path / "bad.md"
        # Malformed YAML (tab in content)
        md_file.write_text(
            "---\nid: M001\n\tinvalid: yaml: here\n---\n", encoding="utf-8"
        )
        c = _make_compiler(tmp_path)
        result = c._parse_markdown_item(md_file, "MANDATE")
        assert result is None


# ---------------------------------------------------------------------------
# separate_core_client
# ---------------------------------------------------------------------------


class TestSeparateCoreClient:
    def test_obrigatorio_without_selection_goes_to_core(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        c.all_items = [
            {"id": "M001", "criticality": "OBRIGATÓRIO", "customizable": False}
        ]
        c.separatepackages_client()
        assert len(c.core_items) == 1
        assert len(c.client_items) == 0

    def test_customizable_without_selection_goes_to_client(
        self, tmp_path: Path
    ) -> None:
        c = _make_compiler(tmp_path)
        c.all_items = [{"id": "G001", "criticality": "OPCIONAL", "customizable": True}]
        c.separatepackages_client()
        assert len(c.client_items) == 1

    def test_selection_overrides_default(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        c.all_items = [
            {"id": "M001", "criticality": "OBRIGATÓRIO", "customizable": False}
        ]
        c.selections = {"M001": {"choice": "CLIENT"}}
        c.separatepackages_client()
        assert len(c.client_items) == 1
        assert len(c.core_items) == 0

    def test_non_customizable_non_obrigatorio_goes_to_core(
        self, tmp_path: Path
    ) -> None:
        c = _make_compiler(tmp_path)
        c.all_items = [{"id": "X001", "criticality": "OPCIONAL", "customizable": False}]
        c.separatepackages_client()
        assert len(c.core_items) == 1


# ---------------------------------------------------------------------------
# generate_governance_files
# ---------------------------------------------------------------------------


class TestGenerateGovernanceFiles:
    def test_generates_all_four_files(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        c.core_items = [{"id": "M001", "title": "Test", "type": "MANDATE"}]
        c.client_items = [{"id": "G001", "title": "Guide", "type": "GUIDELINE"}]
        c.generate_governance_files()
        output_dir = tmp_path / "compiler" / "compiled"
        assert (output_dir / "governance-core.json").exists()
        assert (output_dir / "governance-client.json").exists()
        assert (output_dir / "metadata-core.json").exists()
        assert (output_dir / "metadata-client.json").exists()

    def test_core_json_has_fingerprint(self, tmp_path: Path) -> None:
        c = _make_compiler(tmp_path)
        c.core_items = [{"id": "M001"}]
        c.client_items = []
        c.generate_governance_files()
        output_dir = tmp_path / "compiler" / "compiled"
        core_data = json.loads(read_text_utf8(output_dir / "governance-core.json"))
        assert "fingerprint" in core_data
        assert len(core_data["fingerprint"]) == 64

    def test_client_fingerprint_salt_matches_core_fingerprint(
        self, tmp_path: Path
    ) -> None:
        c = _make_compiler(tmp_path)
        c.core_items = [{"id": "M001"}]
        c.client_items = [{"id": "G001"}]
        c.generate_governance_files()
        output_dir = tmp_path / "compiler" / "compiled"
        core_data = json.loads(read_text_utf8(output_dir / "governance-core.json"))
        client_data = json.loads(read_text_utf8(output_dir / "governance-client.json"))
        assert client_data["fingerprint_core_salt"] == core_data["fingerprint"]


# ---------------------------------------------------------------------------
# print_summary
# ---------------------------------------------------------------------------


class TestPrintSummary:
    def test_does_not_raise(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        c = _make_compiler(tmp_path)
        c.core_items = [{"id": "M001", "title": "Test"}]
        c.client_items = []
        c.all_items = c.core_items.copy()
        with caplog.at_level(
            logging.DEBUG, logger="providence_integration.builders.governance.compile"
        ):
            c.print_summary()
        assert "M001" in caplog.text

    def test_truncates_long_item_list(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        c = _make_compiler(tmp_path)
        c.core_items = [{"id": f"M{i:03d}", "title": f"Title {i}"} for i in range(10)]
        c.client_items = []
        c.all_items = c.core_items.copy()
        with caplog.at_level(
            logging.DEBUG, logger="providence_integration.builders.governance.compile"
        ):
            c.print_summary()
        assert "more" in caplog.text
