"""Tests for providence_core.utils.managed_block.

`.analysis/refined/20260906-root-seed-githook-necessity/design.md` § Test
Changes — the managed-block convention lets sdd regenerate its own content
inside a shared-namespace file (CLAUDE.md/GEMINI.md/AGENTS.md) without
clobbering content another tool, agent, or human added outside the block.
"""

from __future__ import annotations

import pytest

from providence_core.utils.managed_block import (
    MalformedManagedBlockError,
    extract_managed_block,
    merge_managed_block,
)

_BEGIN = "<!-- sdd:managed:begin -->"
_END = "<!-- sdd:managed:end -->"


def test_merge_creates_block_when_no_existing_content() -> None:
    result = merge_managed_block(None, "line1\nline2")
    assert result == f"{_BEGIN}\nline1\nline2\n{_END}\n"


def test_merge_prepends_block_when_existing_content_has_no_markers() -> None:
    result = merge_managed_block("some human note\n", "line1")
    assert result == f"{_BEGIN}\nline1\n{_END}\nsome human note\n"


def test_merge_replaces_only_block_body_preserving_content_around_it() -> None:
    existing = f"before text\n{_BEGIN}\nold body\n{_END}\nafter text\n"
    result = merge_managed_block(existing, "new body")
    assert result == f"before text\n{_BEGIN}\nnew body\n{_END}\nafter text\n"


def test_merge_preserves_unrelated_content_across_two_regenerations() -> None:
    """Simulates two consecutive regenerations with different fingerprints —
    the hand-added content after the block must survive both untouched."""
    first = merge_managed_block(None, "fingerprint: aaa")
    with_human_note = first + "\n<!-- my own notes, unrelated to sdd -->\n"
    second = merge_managed_block(with_human_note, "fingerprint: bbb")
    assert "<!-- my own notes, unrelated to sdd -->" in second
    assert "fingerprint: bbb" in second
    assert "fingerprint: aaa" not in second


def test_merge_raises_on_unbalanced_markers() -> None:
    existing = f"{_BEGIN}\nbody\n"  # missing END
    with pytest.raises(MalformedManagedBlockError):
        merge_managed_block(existing, "new body")


def test_merge_raises_on_duplicate_begin_markers() -> None:
    existing = f"{_BEGIN}\n{_BEGIN}\nbody\n{_END}\n"
    with pytest.raises(MalformedManagedBlockError):
        merge_managed_block(existing, "new body")


def test_extract_returns_block_body() -> None:
    content = f"before\n{_BEGIN}\nthe body\n{_END}\nafter"
    assert extract_managed_block(content) == "the body"


def test_extract_returns_none_when_no_markers() -> None:
    assert extract_managed_block("just plain content, no markers") is None


def test_extract_returns_none_on_malformed_markers_degrades_safely() -> None:
    """Unlike merge, extract never raises — a validator reading an
    arbitrary/hand-edited file must degrade safely, not crash."""
    content = f"{_BEGIN}\nbody\n"  # missing END
    assert extract_managed_block(content) is None
