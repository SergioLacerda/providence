"""Tests for generators/_redirector_renderers.py."""

from providence_cli.generators._redirector_renderers import (
    _render_instruction_document,
    render_agent_redirector,
)

FINGERPRINT = "21b6f7d81c88d0c0792a262a16f8e344"


def _sample_config() -> dict:
    return {
        "core_fingerprint": "21b6f7d81c88d0c0",
        "client_fingerprint": "792a262a16f8e344",
        "items": [
            {
                "id": "M001",
                "type": "MANDATE",
                "title": "Clean Architecture",
                "description": "Clean architecture mandate",
            },
            {"id": "G001", "type": "GUIDELINE", "title": "Style"},
        ],
    }


def test_render_agent_redirector_includes_fingerprint_and_mandates() -> None:
    content = render_agent_redirector(
        "Gemini",
        ["# gemini-agent.md"],
        FINGERPRINT,
        ["M001", "M002"],
    )
    assert FINGERPRINT[:16] in content
    assert "Active mandates: 2 (M001, M002)" in content
    assert ".providence/agent-instructions.md" in content
    assert "providence governance validate" in content


def test_render_agent_redirector_truncates_long_mandate_list() -> None:
    mandate_ids = [f"M{i:03d}" for i in range(8)]
    content = render_agent_redirector(
        "Cursor", ["# cursor-agent.md"], FINGERPRINT, mandate_ids
    )
    assert "Active mandates: 8" in content
    assert "..." in content


def test_render_instruction_document_includes_mandates_and_validation() -> None:
    config = _sample_config()
    content = _render_instruction_document(
        "Gemini", ["# gemini-instructions.md"], config
    )
    assert "Mandatory Rules (MANDATES)" in content
    assert "M001" in content
    assert "Guidelines (SOFT)" in content
    assert "G001" in content
    assert "providence governance validate" in content


def test_render_instruction_document_claude_includes_bootstrap_sections() -> None:
    config = _sample_config()
    content = _render_instruction_document("Claude", ["# claude-agent.md"], config)
    assert "Agent Entrypoint (Bootstrap)" in content
    assert "Two-Question Quiz" in content


def test_render_instruction_document_no_items_shows_governance_context() -> None:
    config = {"core_fingerprint": "abc", "client_fingerprint": "def", "items": []}
    content = _render_instruction_document("Gemini", ["# header"], config)
    assert "## Governance Context" in content
    assert "providence governance compile" in content
