"""Tests for generators/_shared_renderers.py."""

from providence_cli.generators._shared_renderers import (
    _render_claude_bootstrap_sections,
)


def test_render_claude_bootstrap_sections_includes_bootstrap_sequence() -> None:
    lines = _render_claude_bootstrap_sections()
    content = "\n".join(lines)
    assert "Agent Entrypoint (Bootstrap)" in content
    assert "1. DISCOVERY" in content
    assert "Two-Question Quiz" in content
    assert "Git & Commit Protocol (P003 Enforcement)" in content


def test_render_claude_bootstrap_sections_returns_list_of_str() -> None:
    lines = _render_claude_bootstrap_sections()
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)
