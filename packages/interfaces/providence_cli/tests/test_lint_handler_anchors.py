"""Unit tests for providence_cli.services.lint_handler  anchor and link validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from providence_cli.services.lint_handler import (
    _extract_file_anchors,
    _filter_code_blocks,
    _resolve_link_target,
    _slugify_anchor,
    _validate_anchor_style,
    _validate_link_fragment_style,
    _validate_markdown_anchors,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _slugify_anchor
# ---------------------------------------------------------------------------


class TestSlugifyAnchor:
    def test_basic_heading(self) -> None:
        assert _slugify_anchor("Hello World") == "hello-world"

    def test_strips_leading_hash(self) -> None:
        assert _slugify_anchor("# My Section") == "my-section"

    def test_removes_inline_code(self) -> None:
        assert _slugify_anchor("`code`") == "code"

    def test_removes_markdown_link(self) -> None:
        assert _slugify_anchor("[text](url)") == "text"

    def test_removes_html_tags(self) -> None:
        assert _slugify_anchor("<em>bold</em>") == "bold"

    def test_collapses_spaces_to_dashes(self) -> None:
        result = _slugify_anchor("one  two   three")
        assert result == "one-two-three"

    def test_strips_explicit_id_suffix(self) -> None:
        result = _slugify_anchor("My Heading {#custom-id}")
        assert "custom-id" not in result
        assert "my-heading" in result

    def test_empty_string(self) -> None:
        assert _slugify_anchor("") == ""

    def test_special_chars_stripped(self) -> None:
        result = _slugify_anchor("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_removes_asterisks_and_underscores(self) -> None:
        result = _slugify_anchor("**bold** _italic_")
        assert "*" not in result
        assert "_" not in result


# ---------------------------------------------------------------------------
# _filter_code_blocks
# ---------------------------------------------------------------------------


class TestFilterCodeBlocks:
    def test_blanks_fenced_code_content(self) -> None:
        content = "before\n```\ncode line\n```\nafter"
        result = _filter_code_blocks(content)
        assert result[0] == "before"
        assert result[2] == ""
        assert result[4] == "after"

    def test_preserves_fence_markers(self) -> None:
        content = "```\ncode\n```"
        result = _filter_code_blocks(content)
        assert result[0] == "```"
        assert result[2] == "```"

    def test_tilde_fences(self) -> None:
        content = "~~~\nhidden\n~~~"
        result = _filter_code_blocks(content)
        assert result[1] == ""

    def test_normal_lines_unchanged(self) -> None:
        content = "line1\nline2"
        result = _filter_code_blocks(content)
        assert result == ["line1", "line2"]

    def test_nested_code_toggle(self) -> None:
        content = "```\na\n```\nb\n```\nc\n```"
        result = _filter_code_blocks(content)
        assert result[1] == ""
        assert result[3] == "b"
        assert result[5] == ""


# ---------------------------------------------------------------------------
# _extract_file_anchors
# ---------------------------------------------------------------------------


class TestExtractFileAnchors:
    def test_extracts_heading_slugs(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# My Section\n## Another One\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "my-section" in anchors
        assert "another-one" in anchors

    def test_extracts_explicit_id(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# Title {#custom-id}\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "custom-id" in anchors

    def test_ignores_headings_in_code_blocks(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\n# fake heading\n```\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "fake-heading" not in anchors

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        assert _extract_file_anchors(f) == set()

    def test_multiple_explicit_ids(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("{#id-one}\n{#id-two}\n", encoding="utf-8")
        anchors = _extract_file_anchors(f)
        assert "id-one" in anchors
        assert "id-two" in anchors


# ---------------------------------------------------------------------------
# _resolve_link_target
# ---------------------------------------------------------------------------


class TestResolveLinkTarget:
    def test_empty_target_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _resolve_link_target(f, "") is None

    def test_http_link_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _resolve_link_target(f, "https://example.com") is None

    def test_mailto_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _resolve_link_target(f, "mailto:x@y.com") is None

    def test_anchor_only_returns_source_and_fragment(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        result = _resolve_link_target(f, "#my-anchor")
        assert result == (f, "my-anchor")

    def test_relative_with_fragment(self, tmp_path: Path) -> None:
        source = tmp_path / "source.md"
        target = tmp_path / "other.md"
        source.write_text("", encoding="utf-8")
        target.write_text("", encoding="utf-8")
        result = _resolve_link_target(source, "other.md#section")
        assert result is not None
        assert result[1] == "section"

    def test_relative_file_not_exists_returns_none(self, tmp_path: Path) -> None:
        source = tmp_path / "source.md"
        source.write_text("", encoding="utf-8")
        result = _resolve_link_target(source, "nonexistent.md#section")
        assert result is None

    def test_relative_no_fragment(self, tmp_path: Path) -> None:
        source = tmp_path / "source.md"
        target = tmp_path / "other.md"
        source.write_text("", encoding="utf-8")
        target.write_text("", encoding="utf-8")
        result = _resolve_link_target(source, "other.md")
        assert result is not None
        assert result[1] == ""

    def test_angle_bracket_link_stripped(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        result = _resolve_link_target(f, "<#my-anchor>")
        assert result == (f, "my-anchor")


# ---------------------------------------------------------------------------
# _validate_link_fragment_style
# ---------------------------------------------------------------------------


class TestValidateLinkFragmentStyle:
    def test_empty_target_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _validate_link_fragment_style(f, "", tmp_path) == 0

    def test_http_link_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        assert _validate_link_fragment_style(f, "https://example.com#ok", tmp_path) == 0

    def test_no_fragment_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "other.md", tmp_path) == 0

    def test_url_encoded_fragment_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "other.md#my%20section", tmp_path) == 1

    def test_empty_slug_fragment_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "#,,,", tmp_path) == 1

    def test_valid_fragment_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "#valid-anchor", tmp_path) == 0

    def test_anchor_only_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("", encoding="utf-8")
        assert _validate_link_fragment_style(f, "#my-section", tmp_path) == 0


# ---------------------------------------------------------------------------
# _validate_markdown_anchors
# ---------------------------------------------------------------------------


class TestValidateMarkdownAnchors:
    def test_valid_anchor_returns_0(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# My Section\n[link](#my-section)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 0

    def test_missing_anchor_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# My Section\n[link](#missing-anchor)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 1

    def test_cross_file_anchor_valid(self, tmp_path: Path) -> None:
        target = tmp_path / "target.md"
        target.write_text("# Target Section\n", encoding="utf-8")
        source = tmp_path / "source.md"
        source.write_text("[link](target.md#target-section)\n", encoding="utf-8")
        assert _validate_markdown_anchors([source], tmp_path) == 0

    def test_no_fragment_link_skipped(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("[link](other.md)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 0

    def test_http_link_skipped(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("[link](https://example.com#section)\n", encoding="utf-8")
        assert _validate_markdown_anchors([doc], tmp_path) == 0


# ---------------------------------------------------------------------------
# _validate_anchor_style
# ---------------------------------------------------------------------------


class TestValidateAnchorStyle:
    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# Clean Heading\n[link](#clean-heading)\n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 0

    def test_url_encoded_fragment_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("[link](#my%20section)\n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 1

    def test_trailing_whitespace_heading_returns_1(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("# Heading   \n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 1

    def test_heading_in_code_block_not_flagged(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.md"
        doc.write_text("```\n# Heading   \n```\n", encoding="utf-8")
        assert _validate_anchor_style([doc], tmp_path) == 0
