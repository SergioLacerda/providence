"""Tests for per-platform agent seed renderers in generators/_seeds_platforms.py."""

from providence_cli.generators._seeds_platforms import (
    _generate_antigravity_seed,
    _generate_claude_seed,
    _generate_copilot_seed,
    _generate_cursor_seed,
    _generate_gemini_seed,
    _generate_generic_seed,
)

CORE_FP = "21b6f7d81c88d0c0"
CLIENT_FP = "792a262a16f8e344"


def _sample_config() -> dict:
    return {
        "core_fingerprint": CORE_FP,
        "client_fingerprint": CLIENT_FP,
        "items": [
            {
                "id": "M001",
                "type": "MANDATE",
                "title": "Clean Architecture",
                "description": "Clean architecture mandate",
            },
            {
                "id": "G001",
                "type": "GUIDELINE",
                "title": "Style",
                "is_immutable": False,
            },
        ],
    }


def _mandatory_and_customizable(config: dict) -> tuple[list[dict], list[dict]]:
    items = config["items"]
    mandatory = [i for i in items if str(i.get("type", "")).upper() == "MANDATE"]
    customizable = [i for i in items if not i.get("is_immutable")]
    return mandatory, customizable


def test_generate_cursor_seed_includes_fingerprint_and_rules() -> None:
    config = _sample_config()
    mandatory, customizable = _mandatory_and_customizable(config)
    content = _generate_cursor_seed(config, mandatory, customizable)
    assert CORE_FP[:8] in content
    assert "Cursor Agent Configuration" in content
    assert "providence ask --full" in content


def test_generate_copilot_seed_includes_both_fingerprints() -> None:
    config = _sample_config()
    mandatory, customizable = _mandatory_and_customizable(config)
    content = _generate_copilot_seed(config, mandatory, customizable)
    assert CORE_FP[:8] in content
    assert CLIENT_FP[:8] in content
    assert "GitHub Copilot Governance Context" in content


def test_generate_generic_seed_includes_full_fingerprints() -> None:
    config = _sample_config()
    mandatory, customizable = _mandatory_and_customizable(config)
    content = _generate_generic_seed(config, mandatory, customizable)
    assert CORE_FP in content
    assert CLIENT_FP in content
    assert "AI Agent Governance Configuration" in content


def test_generate_claude_seed_uses_instruction_document_renderer() -> None:
    config = _sample_config()
    mandatory, customizable = _mandatory_and_customizable(config)
    content = _generate_claude_seed(config, mandatory, customizable)
    assert "claude-agent.md" in content
    assert "Claude Agent Seed" in content


def test_generate_gemini_seed_includes_client_fingerprint() -> None:
    config = _sample_config()
    mandatory, customizable = _mandatory_and_customizable(config)
    content = _generate_gemini_seed(config, mandatory, customizable)
    assert CLIENT_FP[:8] in content
    assert "Gemini Governance Context" in content


def test_generate_antigravity_seed_includes_both_fingerprints() -> None:
    config = _sample_config()
    mandatory, customizable = _mandatory_and_customizable(config)
    content = _generate_antigravity_seed(config, mandatory, customizable)
    assert CORE_FP[:8] in content
    assert CLIENT_FP[:8] in content
    assert "Antigravity Governance Context" in content
